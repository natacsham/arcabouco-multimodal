"""Synthetic checks for the read-only bridge to the thesis knowledge records.

No participant observation is reconstructed here. Context names deliberately do
not match the demonstration catalogue; the bridge must read knowledge records,
not retrieve complete prepared scenarios.
"""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parents[1]
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "vendor"))
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from rdflib.compare import to_isomorphic  # noqa: E402
from trajectory import ResearchComposer, TrajectoryError, build_trajectory_graph  # noqa: E402
from test_composition import keyboard_audio_context, local, signatures  # noqa: E402

KNOWLEDGE_FILE = ROOT / "data" / "knowledge-base.json"


def file_hash(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def trajectory_context():
    case = keyboard_audio_context()
    case["id"] = "SYN-TRJ-NEW-071"
    case["facts"].update({
        "LearningCommunicationContext": True,
        "KeyboardEffortAcceptable": True,
        "KeyboardCompatible": True,
        "KeyboardFeedbackPerceptible": True,
        "SpeechEffortAcceptable": False,
        "SpeechCompatible": False,
        "SpeechFeedbackPerceptible": False,
        "CanVerifyMeaning": True,
    })
    return case


def positive_steps(result):
    return {local(item["id"]) for item in result.get("capability_evaluations", [])
            if item["state"] == "PASS"}


class TrajectoryTests(unittest.TestCase):
    def assert_not_ready(self, result):
        self.assertNotEqual(result["status"], "COMPOSED")
        self.assertEqual(result["choices"], [])

    def test_01_reads_real_knowledge_with_hash_and_original_record_values(self):
        result = ResearchComposer().compose(trajectory_context())
        self.assertEqual(result["status"], "COMPOSED")
        evidence = result["trajectory_evidence"]
        self.assertEqual(evidence["base_sha256"], file_hash(KNOWLEDGE_FILE))
        self.assertEqual(len(evidence["bindings_sha256"]), 64)
        original = json.loads(KNOWLEDGE_FILE.read_text(encoding="utf-8"))
        by_id = {item["id"]: item for item in original["knowledge"]}
        records = {item["id"]: item for item in evidence["records"]
                   if item["collection"] == "knowledge"}
        self.assertTrue({"K28", "K29", "K41"}.issubset(records))
        for identifier in ("K28", "K29", "K41"):
            self.assertEqual(records[identifier]["record"], by_id[identifier])
            self.assertEqual(len(records[identifier]["sha256"]), 64)

    def test_02_blocked_speech_input_does_not_disable_speech_output(self):
        case = trajectory_context()
        self.assertIs(case["facts"]["CanUseSpeech"], False)
        result = ResearchComposer().compose(case)
        self.assertEqual(signatures(result), {("CaptureKeyboard", "ReviewSpeech")})
        self.assertIn("CaptureSpeech", {local(row["id"]) for row in result["exclusions"] if "id" in row})

    def test_03_audio_support_is_necessary_for_the_audio_only_context(self):
        case = trajectory_context()
        self.assert_not_ready(ResearchComposer(include_audio=False).compose(case))
        self.assertEqual(ResearchComposer(include_audio=True).compose(case)["status"], "COMPOSED")

    def test_04_removing_audio_adapts_to_visual_review_only_when_viable(self):
        case = trajectory_context()
        case["resources"].update(AudioOutput=False, Display=True)
        case["facts"].update(AudioUsable=False, CanReviewVisualText=True)
        result = ResearchComposer().compose(case)
        self.assertEqual(signatures(result), {("CaptureKeyboard", "ReviewText")})
        case["facts"]["CanReviewVisualText"] = False
        self.assert_not_ready(ResearchComposer().compose(case))

    def test_05_unknown_operability_is_pending_and_identifies_what_to_confirm(self):
        case = trajectory_context()
        case["facts"]["KeyboardEffortAcceptable"] = None
        result = ResearchComposer().compose(case)
        self.assert_not_ready(result)
        self.assertEqual(result["proposal_status"], "CONDITIONAL")
        self.assertTrue(result["pending_candidates"])
        self.assertIn("KeyboardEffortAcceptable", {local(row["id"]) for row in result["facts_to_confirm"]})
        checks = [row for row in result["execution_evidence"]
                  if row["kind"] == "REQUIRES_requiresFact"
                  and local(row["expected"]["concept"]) == "KeyboardEffortAcceptable"]
        self.assertTrue(checks)
        self.assertEqual({row["state"] for row in checks}, {"PENDING"})

    def test_06_known_impediments_exclude_instead_of_simulating_operation(self):
        for key in ("KeyboardEffortAcceptable", "KeyboardCompatible", "KeyboardFeedbackPerceptible"):
            with self.subTest(key=key):
                case = trajectory_context()
                case["facts"][key] = False
                result = ResearchComposer().compose(case)
                self.assert_not_ready(result)
                self.assertNotIn("CaptureKeyboard", positive_steps(result))

    def test_07_missing_review_is_partial_coverage_not_a_complete_plan(self):
        case = trajectory_context()
        case["facts"]["CanCorrect"] = False
        result = ResearchComposer().compose(case)
        self.assert_not_ready(result)
        self.assertEqual(result["proposal_status"], "PARTIAL")
        self.assertIn("CaptureKeyboard", positive_steps(result))
        self.assertTrue(result["partial_segments"])
        self.assertTrue(all(not segment["ready_for_whole_task"] for segment in result["partial_segments"]))
        self.assertTrue(any(row["code"] == "FUNCTION_NOT_COVERED"
                            and local(row["function"]) == "Review" for row in result["gaps"]))

    def test_08_does_not_promote_candidate_and_partial_records_to_primary_evidence(self):
        result = ResearchComposer().compose(trajectory_context())
        records = {item["id"]: item["record"] for item in result["trajectory_evidence"]["records"]
                   if item["collection"] == "knowledge"}
        self.assertEqual(records["K28"]["status_revisao"], "CANDIDATO_RECONSTRUIDO_A_REVISAR")
        self.assertEqual(records["K29"]["status_revisao"], "CANDIDATO_RECONSTRUIDO_A_REVISAR")
        self.assertEqual(records["K41"]["foundation_review_status"], "PARCIAL")
        for choice in result["choices"]:
            self.assertEqual(choice["epistemic_status"], "PROPOSED_NOT_EVALUATED")

    def test_09_missing_or_changed_pending_records_fail_closed(self):
        original = json.loads(KNOWLEDGE_FILE.read_text(encoding="utf-8"))
        for operation in ("remove", "mark_pending"):
            with self.subTest(operation=operation), tempfile.TemporaryDirectory(prefix="mado-v2-test-") as folder:
                changed = copy.deepcopy(original)
                if operation == "remove":
                    changed["knowledge"] = [row for row in changed["knowledge"] if row["id"] != "K41"]
                else:
                    record = next(row for row in changed["knowledge"] if row["id"] == "K41")
                    record["status_revisao"] = "PENDENTE"
                temporary = Path(folder) / "knowledge-base.json"
                temporary.write_text(json.dumps(changed, ensure_ascii=False), encoding="utf-8")
                with self.assertRaises(TrajectoryError):
                    ResearchComposer(base_path=temporary)

    def test_10_scenario_identifier_has_no_selection_effect(self):
        composer = ResearchComposer()
        case = trajectory_context()
        expected = signatures(composer.compose(case))
        for identifier in ("NEW-NO-TEMPLATE-118", "TEA", "HISTORIA", "BLIND", "DOCENTE"):
            case["id"] = identifier
            self.assertEqual(signatures(composer.compose(case)), expected)

    def test_11_profile_and_diagnosis_are_not_interpreted_as_functional_facts(self):
        for field in ("profile", "diagnosis", "persona"):
            with self.subTest(field=field):
                case = trajectory_context()
                case[field] = "Identificador de pessoa não é condição funcional"
                result = ResearchComposer().compose(case)
                self.assert_not_ready(result)
                self.assertTrue(result["input_issues"])

    def test_12_rdf_build_and_execution_are_reproducible(self):
        first, second = build_trajectory_graph(), build_trajectory_graph()
        self.assertEqual(to_isomorphic(first).graph_digest(), to_isomorphic(second).graph_digest())
        composer = ResearchComposer()
        case = trajectory_context()
        before_case = copy.deepcopy(case)
        before_graph = to_isomorphic(composer.graph).graph_digest()
        self.assertEqual(composer.compose(case), composer.compose(case))
        self.assertEqual(case, before_case)
        self.assertEqual(to_isomorphic(composer.graph).graph_digest(), before_graph)

    def test_13_preserved_base_ontology_queries_and_engine_are_not_written(self):
        protected = {KNOWLEDGE_FILE, ROOT / "engine.py", *ROOT.glob("ontology/*.ttl"), *ROOT.glob("queries/*.rq")}
        before = {str(path): file_hash(path) for path in protected}
        ResearchComposer().compose(trajectory_context())
        after = {str(path): file_hash(path) for path in protected}
        self.assertEqual(before, after)

    def test_14_contradictory_aliases_require_correction(self):
        case = trajectory_context()
        case["facts"]["v2:CanUseKeyboard"] = False
        result = ResearchComposer().compose(case)
        self.assert_not_ready(result)
        self.assertTrue(any(row["code"] == "CONFLICTING_INPUT_ALIASES" for row in result["input_issues"]))

    def test_15_meaning_verification_cannot_be_assumed_from_type_compatibility(self):
        for value in (None, False):
            with self.subTest(value=value):
                case = trajectory_context()
                case["facts"]["CanVerifyMeaning"] = value
                result = ResearchComposer().compose(case)
                self.assert_not_ready(result)
                self.assertEqual(bool(result["pending_candidates"]), value is None)

    def test_16_no_generalization_outside_registered_learning_communication_scope(self):
        case = trajectory_context()
        case["facts"]["LearningCommunicationContext"] = False
        self.assert_not_ready(ResearchComposer().compose(case))

    def test_17_existing_content_review_does_not_require_creating_content_again(self):
        case = trajectory_context()
        case["task"] = "TaskReviewExistingText"
        case["facts"]["CanUseKeyboard"] = False
        # CanCorrect remains an independently confirmed fact. No correction
        # device is inferred merely because the speech output is available.
        result = ResearchComposer().compose(case)
        self.assertEqual(signatures(result), {("ReviewSpeech",)})
        self.assertEqual(result["choices"][0]["relations"], [])

    def test_18_removing_prepared_scenarios_and_decisions_has_no_effect(self):
        original = json.loads(KNOWLEDGE_FILE.read_text(encoding="utf-8"))
        for collection in ("contexts", "decisions", "decision_components", "modal_configurations",
                           "elicitation_synthesis", "transfer_mappings", "comparison_oracle"):
            original.pop(collection, None)
        with tempfile.TemporaryDirectory(prefix="mado-v2-no-scenarios-") as folder:
            temporary = Path(folder) / "knowledge-base.json"
            temporary.write_text(json.dumps(original, ensure_ascii=False), encoding="utf-8")
            result = ResearchComposer(base_path=temporary).compose(trajectory_context())
        self.assertEqual(signatures(result), {("CaptureKeyboard", "ReviewSpeech")})
        self.assertTrue(all(row["collection"] not in {"contexts", "decisions", "decision_components", "modal_configurations"}
                            for row in result["trajectory_evidence"]["records"]))

    def test_19_partial_provenance_is_present_and_separate_from_complete_choices(self):
        case = trajectory_context()
        case["facts"]["CanCorrect"] = False
        result = ResearchComposer().compose(case)
        evidence = result["trajectory_evidence"]
        self.assertEqual(result["proposal_status"], "PARTIAL")
        self.assertEqual(evidence["records"], [])
        self.assertEqual(evidence["applications"], [])
        self.assertTrue(evidence["partial_applications"])
        records = {row["id"] for row in evidence["partial_records"] if row["collection"] == "knowledge"}
        self.assertEqual(records, {"K41"})
        self.assertNotIn("K28", records)
        self.assertTrue(all(row["usage"] == "PARTIAL_SEGMENT_NOT_WHOLE_TASK" for row in evidence["partial_records"]))

    def test_20_pending_provenance_is_not_reported_as_authorized_complete_use(self):
        case = trajectory_context()
        case["facts"]["KeyboardEffortAcceptable"] = None
        result = ResearchComposer().compose(case)
        evidence = result["trajectory_evidence"]
        self.assertEqual(result["proposal_status"], "CONDITIONAL")
        self.assertEqual(evidence["applications"], [])
        self.assertEqual(evidence["records"], [])
        self.assertTrue(evidence["pending_applications"])
        self.assertTrue(evidence["pending_records"])

    def test_21_pending_bridge_application_is_not_promoted_to_authorized(self):
        bindings = json.loads((HERE / "trajectory-bindings.json").read_text(encoding="utf-8"))
        bindings["applications"][0]["status"] = "PENDING"
        with tempfile.TemporaryDirectory(prefix="mado-v2-pending-binding-") as folder:
            temporary = Path(folder) / "bindings.json"
            temporary.write_text(json.dumps(bindings, ensure_ascii=False), encoding="utf-8")
            with self.assertRaises(TrajectoryError):
                ResearchComposer(bindings_path=temporary)

    def test_22_review_requires_available_content_in_both_output_modes(self):
        for mode in ("speech", "visual"):
            for value in (False, None):
                with self.subTest(mode=mode, content=value):
                    case = trajectory_context()
                    case["task"] = "TaskReviewExistingText"
                    case["facts"]["ContentAvailable"] = value
                    if mode == "visual":
                        case["resources"].update(AudioOutput=False, Display=True)
                        case["facts"].update(AudioUsable=False, CanReviewVisualText=True)
                    result = ResearchComposer().compose(case)
                    self.assert_not_ready(result)
                    self.assertEqual(result["proposal_status"], "NONE" if value is False else "CONDITIONAL")
                    if value is None:
                        self.assertIn("ContentAvailable", {local(row["id"]) for row in result["facts_to_confirm"]})
                    else:
                        self.assertIn("ContentAvailable", {local(row["id"]) for row in result["unavailable_conditions"]})

    def test_23_bridge_cannot_drop_functional_conditions_derived_from_knowledge(self):
        original = json.loads((HERE / "trajectory-bindings.json").read_text(encoding="utf-8"))
        for index, application in enumerate(original["applications"]):
            for removed in [None, *application["requires_facts"]]:
                with self.subTest(target=application["target"], removed=removed), tempfile.TemporaryDirectory(prefix="mado-v2-no-condition-") as folder:
                    changed = copy.deepcopy(original)
                    changed["applications"][index]["requires_facts"] = (
                        [] if removed is None else [fact for fact in application["requires_facts"] if fact != removed]
                    )
                    temporary = Path(folder) / "bindings.json"
                    temporary.write_text(json.dumps(changed, ensure_ascii=False), encoding="utf-8")
                    with self.assertRaises(TrajectoryError):
                        ResearchComposer(bindings_path=temporary)

    def test_24_bridge_cannot_substitute_unrelated_existing_knowledge_or_primary_support(self):
        original = json.loads((HERE / "trajectory-bindings.json").read_text(encoding="utf-8"))
        target = next(index for index, row in enumerate(original["applications"]) if row["target"] == "CaptureKeyboard")
        foreign_primary = next(row["primary_contribution_ids"] for row in original["applications"] if row["target"] == "ReviewSpeech")
        mutations = (("knowledge_ids", ["K29"]),
                     ("knowledge_ids", ["K41", "K41"]),
                     ("primary_contribution_ids", foreign_primary),
                     ("primary_contribution_ids", []))
        for field, value in mutations:
            with self.subTest(field=field, value=value), tempfile.TemporaryDirectory(prefix="mado-v2-wrong-support-") as folder:
                changed = copy.deepcopy(original)
                changed["applications"][target][field] = value
                temporary = Path(folder) / "bindings.json"
                temporary.write_text(json.dumps(changed, ensure_ascii=False), encoding="utf-8")
                with self.assertRaises(TrajectoryError):
                    ResearchComposer(bindings_path=temporary)


if __name__ == "__main__":
    unittest.main(verbosity=2)
