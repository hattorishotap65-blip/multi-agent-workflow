#!/usr/bin/env python3
"""Render a cycle-log JSONL file (docs/agent-workflow/cycle-log-schema.md)
into a standalone, self-contained HTML dashboard.

Read-only: never writes to the input log file. Standard-library only,
no network access, no subprocess calls.

Usage:
    python tools/render_dashboard.py <cycle-log.jsonl> [-o out.html]
"""
from __future__ import annotations

import argparse
import html
import json
import sys
from pathlib import Path
from typing import Any

STAGE_ORDER: list[tuple[str, str]] = [
    ("task_input_recorded", "Task Input"),
    ("proposal_submitted", "独立提案"),
    ("round1_critique", "Round 1 相互批評"),
    ("round2_critique", "Round 2 (条件付き)"),
    ("anonymous_evaluation", "匿名評価"),
    ("integrated_design", "統合設計"),
    ("implementation_gate", "実装ゲート"),
]

SCORE_LABELS = [
    ("accuracy", "正確性", 30),
    ("evidence_strength", "根拠の強さ", 20),
    ("safety_scope", "安全性と範囲遵守", 20),
    ("simplicity", "単純さ・保守性", 15),
    ("testability_rollback", "テスト可能性・ロールバック性", 15),
]


def load_events(path: Path) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as f:
        for lineno, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{lineno}: invalid JSON: {exc}") from exc
    return events


def compute_cycle(events: list[dict[str, Any]]) -> dict[str, Any]:
    if not events:
        raise ValueError("no events in log")

    cycle_id = events[0].get("cycle_id")
    for e in events:
        if e.get("cycle_id") != cycle_id:
            raise ValueError(
                f"multiple cycle_id values in one log file: "
                f"{cycle_id!r} vs {e.get('cycle_id')!r} (one file must hold exactly one cycle)"
            )

    cycle: dict[str, Any] = {
        "cycle_id": cycle_id,
        "task": None,
        "proposals": [],
        "round1": None,
        "round2": None,
        "evaluation": None,
        "integrated": None,
        "gate": None,
    }

    for e in events:
        ev = e.get("event")
        if ev == "task_input_recorded":
            cycle["task"] = e.get("task", {})
        elif ev == "proposal_submitted":
            cycle["proposals"].append(e)
        elif ev == "round1_critique":
            cycle["round1"] = e
        elif ev == "round2_critique":
            cycle["round2"] = e
        elif ev == "anonymous_evaluation":
            cycle["evaluation"] = e
        elif ev == "integrated_design":
            cycle["integrated"] = e
        elif ev == "implementation_gate":
            cycle["gate"] = e
        # unknown event types are ignored (forward-compatible), not an error

    return cycle


def stage_status(key: str, cycle: dict[str, Any]) -> str:
    """Returns one of: pending, active, done, skipped."""
    if key == "task_input_recorded":
        return "done" if cycle["task"] is not None else "pending"

    if key == "proposal_submitted":
        n = len(cycle["proposals"])
        if n >= 2:
            return "done"
        if n == 1:
            return "active"
        return "pending"

    if key == "round1_critique":
        r = cycle["round1"]
        if r is None:
            return "active" if stage_status("proposal_submitted", cycle) == "done" else "pending"
        return "done" if r.get("status") == "done" else "active"

    if key == "round2_critique":
        r = cycle["round2"]
        if r is not None:
            return "done" if r.get("status") == "done" else "active"
        # round 2 is conditional -- if evaluation already happened without it,
        # it was deliberately skipped, not merely not-yet-reached
        if cycle["evaluation"] is not None:
            return "skipped"
        return "pending"

    if key == "anonymous_evaluation":
        return "done" if cycle["evaluation"] is not None else "pending"

    if key == "integrated_design":
        return "done" if cycle["integrated"] is not None else "pending"

    if key == "implementation_gate":
        return "done" if cycle["gate"] is not None else "pending"

    return "pending"


def agent_class(agent: str) -> str:
    a = (agent or "").lower()
    if "claude" in a:
        return "claude"
    if "codex" in a:
        return "codex"
    return "neutral"


def esc(value: Any) -> str:
    return html.escape(str(value if value is not None else ""), quote=True)


def render_stage_track(cycle: dict[str, Any]) -> str:
    parts = []
    for i, (key, label) in enumerate(STAGE_ORDER):
        status = stage_status(key, cycle)
        dot = {"done": "✓", "active": str(i + 1), "pending": str(i + 1), "skipped": "—"}[status]
        parts.append(
            f'<div class="stage is-{status}"><div class="stage-dot">{esc(dot)}</div>'
            f'<div class="stage-label">{esc(label)}</div></div>'
        )
        if i < len(STAGE_ORDER) - 1:
            line_done = "is-done" if status == "done" else ""
            parts.append(f'<div class="stage-line {line_done}"></div>')
    return "\n".join(parts)


def render_proposal_card(p: dict[str, Any], index: int) -> str:
    cls = agent_class(p.get("agent", ""))
    ev = p.get("evidence", {})
    return f"""
    <div class="proposal-card {cls}">
      <div class="agent-id">
        <span class="agent-chip {cls}">案{index}</span>
        <span class="agent-model">{esc(p.get("agent"))} · {esc(p.get("model_alias"))}</span>
      </div>
      <h3 class="proposal-title">{esc(p.get("title"))}</h3>
      <p class="proposal-body">{esc(p.get("summary"))}</p>
      <div class="evidence-row">
        <span class="ev"><b>Confirmed</b> {esc(ev.get("confirmed", 0))}</span>
        <span class="ev"><b>Inference</b> {esc(ev.get("inference", 0))}</span>
        <span class="ev"><b>Unknown</b> {esc(ev.get("unknown", 0))}</span>
      </div>
    </div>"""


def render_verdict_card(evaluation: dict[str, Any] | None) -> str:
    if evaluation is None:
        return """
    <div class="verdict-card">
      <div class="verdict-score">— <sub>/100</sub></div>
      <div class="verdict-text">
        <span class="verdict-label">design-judge 評価 · 未実施</span>
        <h3>匿名評価は未実施</h3>
      </div>
    </div>"""

    scores = evaluation.get("scores", [])
    rows = []
    for s in scores:
        breakdown = " / ".join(f"{label} {s.get(key, 0)}" for key, label, _max in SCORE_LABELS)
        rows.append(
            f'<div class="score-row"><span class="score-label-chip">{esc(s.get("label"))}</span>'
            f'<span class="score-total">{esc(s.get("total", 0))}<sub>/100</sub></span>'
            f'<span class="score-breakdown">{esc(breakdown)}</span></div>'
        )
    top = max(scores, key=lambda s: s.get("total", 0)) if scores else None
    total = top.get("total", "—") if top else "—"
    return f"""
    <div class="verdict-card">
      <div class="verdict-score">{esc(total)} <sub>/100</sub></div>
      <div class="verdict-text">
        <span class="verdict-label">design-judge 評価 · 完了</span>
        <h3>{esc(evaluation.get("verdict", ""))}</h3>
        <div class="score-rows">{"".join(rows)}</div>
      </div>
    </div>"""


PAGE_TEMPLATE = """<!doctype html>
<html lang="ja">
<head>
<meta charset="utf-8" />
<title>{title}</title>
<style>
{css}
</style>
</head>
<body>
<div class="wrap">
  <div class="top">
    <span class="eyebrow">Multi-agent Workflow — Cycle Dashboard</span>
    <h1>{task_title}</h1>
    <p class="lede">cycle_id = {cycle_id}</p>
  </div>

  <section class="exhibit">
    <div class="board">
      <div class="stage-track">
        {stage_track}
      </div>
      <div class="board-grid">
        {proposal_cards}
        {verdict_card}
      </div>
    </div>
  </section>
</div>
</body>
</html>
"""

CSS = """
:root {
  --ink: #151a21; --paper: #eff2f1; --paper-raised: #ffffff; --line: #d7dcda;
  --muted: #5b6560; --accent: #2d7d8c; --accent-soft: #e2eef0;
  --claude: #a8752c; --claude-soft: #f6ead3; --codex: #4d51ab; --codex-soft: #e6e6f6;
  --success: #3f8f5f; --warning: #b4691f;
  --font-ui: "Segoe UI Variable", "Segoe UI", ui-sans-serif, system-ui, sans-serif;
  --font-mono: "Cascadia Mono", "Cascadia Code", ui-monospace, "SFMono-Regular", Consolas, monospace;
}
@media (prefers-color-scheme: dark) {
  :root {
    --ink: #e9edee; --paper: #11151a; --paper-raised: #171c22; --line: #2b3138;
    --muted: #93a09c; --accent: #5fb6c4; --accent-soft: #16282c;
    --claude: #d9a24f; --claude-soft: #2c2415; --codex: #8f93e0; --codex-soft: #1e1f33;
    --success: #63b784; --warning: #d78f45;
  }
}
* { box-sizing: border-box; }
body { margin: 0; background: var(--paper); color: var(--ink); font-family: var(--font-ui); line-height: 1.55; }
.wrap { max-width: 1000px; margin: 0 auto; padding: 48px 24px 72px; }
.eyebrow { font-family: var(--font-mono); font-size: 12px; letter-spacing: .08em; text-transform: uppercase; color: var(--accent); }
h1 { font-size: clamp(22px, 3vw, 30px); font-weight: 620; margin: 8px 0 4px; }
.lede { font-family: var(--font-mono); color: var(--muted); font-size: 13px; margin: 0; }
.board { background: var(--paper-raised); border: 1px solid var(--line); border-radius: 12px; padding: 26px; margin-top: 24px; }
.stage-track { display: flex; align-items: center; overflow-x: auto; padding-bottom: 6px; margin-bottom: 28px; }
.stage { display: flex; flex-direction: column; align-items: center; gap: 8px; min-width: 108px; }
.stage-dot { width: 26px; height: 26px; border-radius: 50%; display: flex; align-items: center; justify-content: center;
  font-family: var(--font-mono); font-size: 11px; font-weight: 700; border: 2px solid var(--line);
  background: var(--paper-raised); color: var(--muted); z-index: 1; }
.stage.is-done .stage-dot { border-color: var(--success); color: var(--success); background: color-mix(in srgb, var(--success) 12%, var(--paper-raised)); }
.stage.is-active .stage-dot { border-color: var(--warning); color: var(--warning); background: color-mix(in srgb, var(--warning) 14%, var(--paper-raised)); }
.stage.is-skipped .stage-dot { color: var(--muted); border-style: dashed; }
.stage-label { font-size: 11.5px; text-align: center; color: var(--muted); max-width: 100px; }
.stage.is-done .stage-label, .stage.is-active .stage-label { color: var(--ink); font-weight: 600; }
.stage-line { height: 2px; flex: 1; background: var(--line); margin-top: -22px; min-width: 20px; }
.stage-line.is-done { background: var(--success); }
.board-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 18px; }
@media (max-width: 720px) { .board-grid { grid-template-columns: 1fr; } }
.proposal-card { border: 1px solid var(--line); border-radius: 10px; padding: 18px; background: var(--paper); }
.proposal-card.claude { border-top: 3px solid var(--claude); }
.proposal-card.codex { border-top: 3px solid var(--codex); }
.agent-id { display: flex; align-items: center; gap: 9px; margin-bottom: 12px; }
.agent-chip { font-family: var(--font-mono); font-size: 11px; font-weight: 700; padding: 3px 9px; border-radius: 4px; }
.agent-chip.claude { color: var(--claude); background: var(--claude-soft); }
.agent-chip.codex { color: var(--codex); background: var(--codex-soft); }
.agent-model { font-size: 12px; color: var(--muted); }
.proposal-title { font-size: 15px; font-weight: 620; margin: 0 0 8px; }
.proposal-body { font-size: 13.5px; color: var(--muted); margin: 0 0 14px; }
.evidence-row { display: flex; gap: 8px; flex-wrap: wrap; font-family: var(--font-mono); font-size: 11px; }
.ev { padding: 3px 8px; border-radius: 999px; border: 1px solid var(--line); color: var(--muted); }
.ev b { color: var(--ink); }
.verdict-card { grid-column: 1 / -1; border: 1px solid var(--line); border-radius: 10px; padding: 18px 20px;
  background: linear-gradient(180deg, var(--accent-soft), var(--paper)); display: flex; gap: 18px; flex-wrap: wrap; }
.verdict-score { font-family: var(--font-mono); font-size: 26px; font-weight: 700; color: var(--accent); line-height: 1; min-width: 64px; }
.verdict-score sub { font-size: 12px; color: var(--muted); font-weight: 500; }
.verdict-text { flex: 1; min-width: 220px; }
.verdict-text h3 { margin: 0 0 6px; font-size: 14px; }
.verdict-label { font-family: var(--font-mono); font-size: 11px; text-transform: uppercase; letter-spacing: .05em; color: var(--accent); display: block; margin-bottom: 4px; }
.score-rows { margin-top: 10px; display: flex; flex-direction: column; gap: 6px; }
.score-row { display: flex; align-items: baseline; gap: 10px; font-size: 12.5px; flex-wrap: wrap; }
.score-label-chip { font-family: var(--font-mono); font-weight: 700; min-width: 32px; }
.score-total { font-family: var(--font-mono); color: var(--accent); font-weight: 700; }
.score-total sub { color: var(--muted); font-weight: 500; }
.score-breakdown { color: var(--muted); }
"""


def render_html(cycle: dict[str, Any]) -> str:
    task = cycle["task"] or {}
    proposal_cards = "".join(
        render_proposal_card(p, i + 1) for i, p in enumerate(cycle["proposals"])
    )
    return PAGE_TEMPLATE.format(
        title=esc(task.get("title") or cycle["cycle_id"]),
        css=CSS,
        task_title=esc(task.get("title") or cycle["cycle_id"]),
        cycle_id=esc(cycle["cycle_id"]),
        stage_track=render_stage_track(cycle),
        proposal_cards=proposal_cards,
        verdict_card=render_verdict_card(cycle["evaluation"]),
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("log", type=Path, help="Path to a cycle-log JSONL file")
    parser.add_argument(
        "-o", "--output", type=Path, default=None,
        help="Output HTML path (default: <log>.html next to the input file)",
    )
    args = parser.parse_args(argv)

    events = load_events(args.log)
    cycle = compute_cycle(events)
    output = render_html(cycle)

    out_path = args.output or args.log.with_suffix(".html")
    out_path.write_text(output, encoding="utf-8")
    print(f"wrote {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
