"""Public bridge checks; all contexts are synthetic, not participant evidence."""
import copy
import importlib.util
import json
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "vendor"))


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


bridge = load_module("composition_web_bridge", ROOT / "web/amado/bridge.py")
build_web = load_module("composition_build_web", ROOT / "scripts/build_web.py")


class CompositionBridgeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from experimental.v2.trajectory import ResearchComposer
        cls.composer = ResearchComposer()
        cls.example = json.loads((ROOT / "experimental/v2/examples/learning-contribution.json").read_text(encoding="utf-8"))

    def setUp(self):
        self.context = copy.deepcopy(self.example)
        self.legacy = SimpleNamespace(current=None)
        self.engine_patch = patch.object(bridge, "ENGINE", self.legacy)
        self.composer_patch = patch.object(bridge, "COMPOSER", self.composer)
        self.engine_patch.start()
        self.composer_patch.start()
        self.addCleanup(self.engine_patch.stop)
        self.addCleanup(self.composer_patch.stop)

    def compose(self):
        return bridge.dispatch({"operation": "compose", "payload": self.context})

    def test_catalog_uses_the_same_graph_and_defaults_to_unknown(self):
        from rdflib import RDF, RDFS
        from experimental.v2.composer import V2
        catalog = bridge.dispatch({"operation": "catalog_composition"})
        self.assertEqual(catalog["version"], "2.0.0-alpha6")
        for group, entity_type in (("facts", V2.ContextFact), ("resources", V2.Resource)):
            self.assertEqual({row["iri"] for row in catalog[group]},
                             {str(node) for node in self.composer.graph.subjects(RDF.type, entity_type)})
            for row in catalog[group]:
                self.assertIsNone(row["default"])
                self.assertEqual(row["label"], str(self.composer.graph.value(V2[row["id"]], RDFS.label)))
                if row["id"] == "LearningCommunicationContext":
                    # Historical origin remains queryable but must not gate
                    # production/review outside an educational setting.
                    self.assertEqual(row["used_by"], [])
                else:
                    self.assertTrue(row["used_by"])
        self.assertEqual(catalog["synthetic_example"]["kind"], "SYNTHETIC")
        self.assertEqual(catalog["synthetic_example"]["context"], self.example)
        self.assertEqual(catalog["labels"][str(V2.TextDraft)], "Rascunho textual editável")
        self.assertFalse(catalog["case_storage"])

    def test_composes_without_legacy_case_and_matches_direct_execution(self):
        from engine import VERSION
        from semantic_execution import project_execution, semantic_execution_summary
        from rdflib.compare import isomorphic
        expected = self.composer.compose_context(self.context, engine=self.legacy)
        expected_graph = project_execution(expected, self.context, self.composer.graph)
        expected["semantic_trace"] = semantic_execution_summary(expected_graph)
        expected.update(result_contract="AMADO_SITUATED_1", base_version=VERSION, case_storage=False)
        expected["fingerprints"] = {Path(name).relative_to(ROOT).as_posix(): value
                                    for name, value in expected["fingerprints"].items()}
        actual = self.compose()
        self.assertEqual(actual, expected)
        self.assertTrue(isomorphic(self.legacy._last_execution_graph, expected_graph))
        self.assertEqual(actual["proposal_status"], "COMPLETE")
        self.assertIsNone(self.legacy.current)
        self.assertEqual([step["id"].split("#")[-1] for step in actual["choices"][0]["steps"]],
                         ["CaptureKeyboard", "ReviewSpeech"])
        self.assertTrue(all(not Path(name).is_absolute() and "\\" not in name
                            for name in actual["fingerprints"]))

    def test_does_not_read_or_replace_legacy_context(self):
        self.legacy.current = {"context": {"task": "other-domain", "narrative": "not composition input"},
                               "last_result": {"preserve": True}}
        before = copy.deepcopy(self.legacy.current)
        self.compose()
        self.assertEqual(self.legacy.current, before)

    def test_unconfirmed_is_never_composed(self):
        self.context["confirmed"] = False
        result = self.compose()
        self.assertEqual(result["proposal_status"], "UNCONFIRMED")
        self.assertEqual(result["choices"], [])

    def test_unknown_conditions_remain_pending_not_true(self):
        self.context["facts"]["KeyboardEffortAcceptable"] = None
        result = self.compose()
        self.assertEqual(result["proposal_status"], "CONDITIONAL")
        self.assertEqual(result["choices"], [])
        self.assertTrue(result["facts_to_confirm"])

    def test_blocked_correction_keeps_partial_work_not_complete_decision(self):
        self.context["facts"]["CanCorrect"] = False
        result = self.compose()
        self.assertEqual(result["proposal_status"], "PARTIAL")
        self.assertEqual(result["choices"], [])
        self.assertTrue(result["partial_segments"])
        self.assertTrue(result["trajectory_evidence"]["partial_applications"])

    def test_rejects_text_instead_of_confirmed_fields(self):
        self.context["narrative"] = "Uma pessoa tem um teclado."
        with self.assertRaisesRegex(ValueError, "não interpreta texto livre"):
            self.compose()

    def test_rejects_non_boolean_values_and_unknown_concepts(self):
        for group, key, value in (("facts", "CanUseKeyboard", "true"),
                                   ("resources", "Keyboard", 1),
                                   ("facts", "Diagnosis", True),
                                   ("resources", "arbitrary-file-path", True)):
            with self.subTest(group=group, key=key, value=value):
                self.context = copy.deepcopy(self.example)
                self.context[group][key] = value
                with self.assertRaises(ValueError):
                    self.compose()

    def test_rejects_bad_task_confirmation_identifier_and_map(self):
        for field, value in (("task", ["TaskCreateReviewedText"]), ("task", "Anything"),
                             ("confirmed", "yes"), ("id", ""), ("id", "x" * 201),
                             ("facts", []), ("resources", True)):
            with self.subTest(field=field):
                self.context = copy.deepcopy(self.example)
                self.context[field] = value
                with self.assertRaises(ValueError):
                    self.compose()

    def test_missing_maps_do_not_inherit_synthetic_example(self):
        self.context.pop("facts")
        self.context.pop("resources")
        result = self.compose()
        self.assertEqual(result["choices"], [])
        self.assertEqual(result["proposal_status"], "CONDITIONAL")

    def test_dispatch_json_preserves_the_same_contract(self):
        request = json.dumps({"operation": "compose", "payload": self.context})
        self.assertEqual(json.loads(bridge.dispatch_json(request)), json.loads(json.dumps(self.compose())))

    def test_runtime_allowlist_has_only_required_public_files(self):
        expected = {"composer.py", "trajectory.py", "learning-contribution.json"}
        paths = [Path(name) for name in build_web.COMPOSITION_FILES]
        self.assertEqual({path.name for path in paths}, expected)
        self.assertTrue(all((ROOT / path).is_file() for path in paths))
        self.assertTrue(all("evidence" not in path.parts and "private" not in path.parts for path in paths))


if __name__ == "__main__":
    unittest.main()
