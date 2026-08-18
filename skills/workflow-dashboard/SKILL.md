---
name: workflow-dashboard
description: Record review-protocol.md progress and each architect's proposal as a cycle log, and render it into an HTML dashboard. Invoke manually to log a phase transition or to generate/refresh the dashboard for a running or finished cycle.
argument-hint: "log <event-json> PATH | render PATH [--output PATH]"
disable-model-invocation: true
user-invocable: true
---

# workflow-dashboard

Gives the parent Claude Code session (the sole orchestrator of `multi-agent-design` / `outcome-improvement-cycle`) a way to record what stage a cycle has reached and what each independent architect proposed, then turn that record into a shareable HTML dashboard. See `docs/agent-workflow/cycle-log-schema.md` for the exact event schema.

## Boundaries

- This Skill does not run design work itself. It only appends facts about a cycle already being run by `multi-agent-design` or `outcome-improvement-cycle`, and renders those facts.
- Only the orchestrating session writes log lines. Subagents and Codex never write to the log directly — their output is summarized into a log line by the orchestrator, consistent with subagents being read-only (`docs/agent-workflow/subagents.md`).
- The log is append-only. Never rewrite or delete an existing line. A correction is a new line, not an edit.
- `tools/render_dashboard.py` never writes to the input log — it only reads it and writes a separate HTML file.
- Do not fabricate proposal content, scores, or a verdict that was not actually produced. If a phase has not happened yet, do not log it.

## Usage

### Logging a phase transition

Append one JSON line matching the schema in `docs/agent-workflow/cycle-log-schema.md` to the cycle's log file (default convention: `.agent-workflow/cycles/<cycle_id>.jsonl` in the adopting project, but any path the user prefers is fine — this plugin does not enforce a location). Do this once per meaningful event: `task_input_recorded`, each `proposal_submitted`, `round1_critique`, `round2_critique` (only if actually run), `anonymous_evaluation`, `integrated_design`, `implementation_gate`.

### Rendering the dashboard

```text
python tools/render_dashboard.py <cycle-log.jsonl> [-o output.html]
```

Run this any time during or after a cycle — the dashboard reflects however far the log has gotten, showing not-yet-reached stages as pending and a skipped Round 2 distinctly from a pending one. Re-run it after each new log line to refresh.

## Example

`examples/cycle-logs/sample-cycle.jsonl` is a complete, illustrative cycle log. Render it to see the expected output shape:

```text
python tools/render_dashboard.py examples/cycle-logs/sample-cycle.jsonl
```
