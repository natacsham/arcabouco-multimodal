"""Progress is an observation of actual operations, never part of a decision."""
import copy
import importlib.util
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "vendor"))
spec = importlib.util.spec_from_file_location("progress_web_bridge", ROOT / "web/amado/bridge.py")
bridge = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bridge)


class ProgressBridgeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from experimental.v2.trajectory import ResearchComposer
        cls.composer = ResearchComposer()
        cls.example = json.loads((ROOT / "experimental/v2/examples/learning-contribution.json").read_text(encoding="utf-8"))

    def setUp(self):
        from types import SimpleNamespace
        self.engine = SimpleNamespace(current={})
        for target, value in (("COMPOSER", self.composer), ("ENGINE", self.engine)):
            mocked = patch.object(bridge, target, value)
            mocked.start()
            self.addCleanup(mocked.stop)

    def test_composition_progress_does_not_change_result(self):
        request = {"operation": "compose", "payload": copy.deepcopy(self.example)}
        expected = bridge.dispatch(request)
        events = []
        actual = bridge.dispatch(request, progress=events.append)
        self.assertEqual(actual, expected)
        self.assertEqual([(row["stage"], row["state"]) for row in events], [
            ("verification", "running"), ("verification", "completed"),
            ("retrieval", "running"), ("retrieval", "completed"),
            ("composition", "running"), ("composition", "completed")])
        self.assertFalse(any(row["stage"] == "presentation" for row in events))

    def test_bad_input_does_not_complete_verification_or_start_composition(self):
        events = []
        with self.assertRaises(ValueError):
            bridge.dispatch({"operation": "compose", "payload": {"narrative": "arbitrary"}}, progress=events.append)
        self.assertEqual([(row["stage"], row["state"]) for row in events], [("verification", "running")])

    def test_engine_exception_does_not_complete_composition(self):
        events = []
        with patch.object(self.composer, "compose_context", side_effect=RuntimeError("controlled failure")):
            with self.assertRaises(RuntimeError):
                bridge.dispatch({"operation": "compose", "payload": copy.deepcopy(self.example)}, progress=events.append)
        self.assertEqual(events[-1]["stage"], "verification")
        self.assertEqual(events[-1]["state"], "completed")
        self.assertFalse(any(row["stage"] == "composition" for row in events))

    def test_generate_callback_forwarding_preserves_json_result(self):
        events = []
        def generate(progress=None):
            if progress:
                progress({"stage": "retrieval", "state": "running", "message": "actual boundary"})
            return {"decision": "exact"}
        self.engine.generate_situated = generate
        self.assertEqual(bridge.dispatch_json('{"operation":"generate"}', progress=events.append), '{"decision": "exact"}')
        self.assertEqual(events, [{"stage": "retrieval", "state": "running", "message": "actual boundary"}])


class EngineProgressTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from engine import DecisionEngine
        cls.engine = DecisionEngine()

    def setUp(self):
        self.engine.start_context("CTX-TRANSFERENCIA-RECURSO-DIGITAL-01")
        self.engine.update_context({"mapping_confirmed": True, "transfer_confirmed": True})

    def test_actual_engine_progress_preserves_full_decision(self):
        from types import SimpleNamespace
        before = copy.deepcopy(self.engine.current)
        events = []
        with patch("engine.now_iso", return_value="2026-10-11T00:00:00Z"), patch("engine.uuid.uuid4", return_value=SimpleNamespace(hex="1234567890abcdef")):
            expected = self.engine.generate()
            self.engine.current = copy.deepcopy(before)
            actual = self.engine.generate(progress=events.append)
        # SPARQL result sets do not promise row order without ORDER BY.
        for result in (actual, expected):
            for key, rows in result["query_results"].items():
                result["query_results"][key] = sorted(rows, key=lambda row: json.dumps(row, sort_keys=True))
        self.assertEqual(actual, expected)
        self.assertEqual([(row["stage"], row["state"]) for row in events], [
            ("retrieval", "running"), ("retrieval", "completed"),
            ("verification", "running"), ("verification", "completed"),
            ("composition", "running"), ("composition", "completed")])

    def test_failed_retrieval_has_no_later_or_completed_phase(self):
        events = []
        with patch.object(self.engine, "retrieve_transfer_candidates", side_effect=RuntimeError("controlled failure")):
            with self.assertRaisesRegex(RuntimeError, "controlled failure"):
                self.engine.generate(progress=events.append)
        self.assertEqual([(row["stage"], row["state"]) for row in events], [("retrieval", "running")])

    def test_failed_selection_does_not_claim_composition(self):
        events = []
        with patch.object(self.engine, "evaluate_component", side_effect=RuntimeError("controlled failure")):
            with self.assertRaisesRegex(RuntimeError, "controlled failure"):
                self.engine.generate(progress=events.append)
        self.assertEqual(events[-1]["stage"], "verification")
        self.assertEqual(events[-1]["state"], "running")
        self.assertFalse(any(row["stage"] == "composition" for row in events))


if __name__ == "__main__":
    unittest.main()
