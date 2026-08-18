import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))

import render_dashboard as rd  # noqa: E402


def write_jsonl(path: Path, events: list[dict]) -> None:
    with path.open("w", encoding="utf-8") as f:
        for e in events:
            f.write(json.dumps(e, ensure_ascii=False) + "\n")


class TestLoadEvents(unittest.TestCase):
    def test_skips_blank_lines(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "c.jsonl"
            p.write_text('{"cycle_id": "a", "ts": "t", "event": "task_input_recorded", "task": {}}\n\n', encoding="utf-8")
            events = rd.load_events(p)
            self.assertEqual(len(events), 1)

    def test_invalid_json_raises_with_line_number(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "c.jsonl"
            p.write_text('{"ok": true}\nnot json\n', encoding="utf-8")
            with self.assertRaises(ValueError) as ctx:
                rd.load_events(p)
            self.assertIn(":2:", str(ctx.exception))


class TestComputeCycle(unittest.TestCase):
    def test_empty_events_raises(self):
        with self.assertRaises(ValueError):
            rd.compute_cycle([])

    def test_mixed_cycle_ids_raise(self):
        events = [
            {"cycle_id": "a", "event": "task_input_recorded", "task": {}},
            {"cycle_id": "b", "event": "task_input_recorded", "task": {}},
        ]
        with self.assertRaises(ValueError):
            rd.compute_cycle(events)

    def test_groups_events_by_type(self):
        events = [
            {"cycle_id": "a", "event": "task_input_recorded", "task": {"title": "T"}},
            {"cycle_id": "a", "event": "proposal_submitted", "agent": "claude-architect"},
            {"cycle_id": "a", "event": "proposal_submitted", "agent": "codex-independent-architect"},
            {"cycle_id": "a", "event": "round1_critique", "status": "done"},
            {"cycle_id": "a", "event": "anonymous_evaluation", "scores": []},
            {"cycle_id": "a", "event": "integrated_design", "adopted_from": "案1"},
            {"cycle_id": "a", "event": "implementation_gate", "decision": "proceed"},
        ]
        cycle = rd.compute_cycle(events)
        self.assertEqual(cycle["task"], {"title": "T"})
        self.assertEqual(len(cycle["proposals"]), 2)
        self.assertEqual(cycle["round1"]["status"], "done")
        self.assertIsNone(cycle["round2"])
        self.assertIsNotNone(cycle["evaluation"])
        self.assertIsNotNone(cycle["integrated"])
        self.assertEqual(cycle["gate"]["decision"], "proceed")

    def test_unknown_event_type_is_ignored_not_an_error(self):
        events = [
            {"cycle_id": "a", "event": "task_input_recorded", "task": {}},
            {"cycle_id": "a", "event": "some_future_event", "payload": 1},
        ]
        cycle = rd.compute_cycle(events)  # must not raise
        self.assertIsNotNone(cycle["task"])


class TestStageStatus(unittest.TestCase):
    def _cycle(self, **overrides):
        base = {
            "cycle_id": "a", "task": None, "proposals": [], "round1": None,
            "round2": None, "evaluation": None, "integrated": None, "gate": None,
        }
        base.update(overrides)
        return base

    def test_task_input_pending_then_done(self):
        self.assertEqual(rd.stage_status("task_input_recorded", self._cycle()), "pending")
        self.assertEqual(rd.stage_status("task_input_recorded", self._cycle(task={"x": 1})), "done")

    def test_proposal_submitted_thresholds(self):
        c0 = self._cycle(proposals=[])
        c1 = self._cycle(proposals=[{}])
        c2 = self._cycle(proposals=[{}, {}])
        self.assertEqual(rd.stage_status("proposal_submitted", c0), "pending")
        self.assertEqual(rd.stage_status("proposal_submitted", c1), "active")
        self.assertEqual(rd.stage_status("proposal_submitted", c2), "done")

    def test_round1_active_until_status_done(self):
        c_not_started = self._cycle(proposals=[])
        c_ready = self._cycle(proposals=[{}, {}])
        c_in_progress = self._cycle(proposals=[{}, {}], round1={"status": "in_progress"})
        c_done = self._cycle(proposals=[{}, {}], round1={"status": "done"})
        self.assertEqual(rd.stage_status("round1_critique", c_not_started), "pending")
        self.assertEqual(rd.stage_status("round1_critique", c_ready), "active")
        self.assertEqual(rd.stage_status("round1_critique", c_in_progress), "active")
        self.assertEqual(rd.stage_status("round1_critique", c_done), "done")

    def test_round2_skipped_when_absent_but_evaluation_happened(self):
        c = self._cycle(round2=None, evaluation={"scores": []})
        self.assertEqual(rd.stage_status("round2_critique", c), "skipped")

    def test_round2_pending_when_absent_and_no_evaluation_yet(self):
        c = self._cycle(round2=None, evaluation=None)
        self.assertEqual(rd.stage_status("round2_critique", c), "pending")

    def test_round2_done_when_present_and_marked_done(self):
        c = self._cycle(round2={"status": "done"})
        self.assertEqual(rd.stage_status("round2_critique", c), "done")

    def test_terminal_stages_done_when_event_present(self):
        c = self._cycle(evaluation={}, integrated={}, gate={})
        self.assertEqual(rd.stage_status("anonymous_evaluation", c), "done")
        self.assertEqual(rd.stage_status("integrated_design", c), "done")
        self.assertEqual(rd.stage_status("implementation_gate", c), "done")


class TestAgentClass(unittest.TestCase):
    def test_recognizes_claude_and_codex(self):
        self.assertEqual(rd.agent_class("claude-architect"), "claude")
        self.assertEqual(rd.agent_class("codex-independent-architect"), "codex")
        self.assertEqual(rd.agent_class("some-other-role"), "neutral")


class TestRenderHtml(unittest.TestCase):
    def test_render_html_escapes_and_includes_task_title(self):
        events = [
            {"cycle_id": "a", "event": "task_input_recorded", "task": {"title": "<script>alert(1)</script>"}},
            {"cycle_id": "a", "event": "proposal_submitted", "agent": "claude-architect",
             "model_alias": "sonnet", "title": "T1", "summary": "S1",
             "evidence": {"confirmed": 1, "inference": 0, "unknown": 0}},
        ]
        cycle = rd.compute_cycle(events)
        out = rd.render_html(cycle)
        self.assertNotIn("<script>alert(1)</script>", out)
        self.assertIn("&lt;script&gt;", out)
        self.assertIn("T1", out)

    def test_main_writes_output_file(self):
        with tempfile.TemporaryDirectory() as d:
            log_path = Path(d) / "cycle.jsonl"
            write_jsonl(log_path, [
                {"cycle_id": "a", "ts": "t", "event": "task_input_recorded", "task": {"title": "T"}},
            ])
            rc = rd.main([str(log_path)])
            self.assertEqual(rc, 0)
            out_path = log_path.with_suffix(".html")
            self.assertTrue(out_path.exists())
            self.assertIn("T", out_path.read_text(encoding="utf-8"))

    def test_sample_cycle_log_renders_without_error(self):
        sample = Path(__file__).resolve().parents[1] / "examples" / "cycle-logs" / "sample-cycle.jsonl"
        events = rd.load_events(sample)
        cycle = rd.compute_cycle(events)
        out = rd.render_html(cycle)
        self.assertIn(cycle["cycle_id"], out)
        for key, _label in rd.STAGE_ORDER:
            self.assertIn(rd.stage_status(key, cycle), {"pending", "active", "done", "skipped"})


if __name__ == "__main__":
    unittest.main()
