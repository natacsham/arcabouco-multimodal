"""Partial and conditional coverage must never masquerade as completed tasks."""
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE.parents[1] / "vendor"))
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from rdflib import Literal, Namespace, RDF  # noqa: E402
from composer import Composer  # noqa: E402
from test_composition import BASE_FILES, EXTENSION, keyboard_audio_context, local, speech_visual_context  # noqa: E402

V2 = Namespace("https://w3id.org/mado/experimental/v2#")


class PartialCompositionTests(unittest.TestCase):
    def test_missing_review_retains_only_grounded_initial_step(self):
        case = speech_visual_context()
        case["facts"]["CanCorrect"] = False
        result = Composer(BASE_FILES).compose(case)
        self.assertEqual(result["proposal_status"], "PARTIAL")
        self.assertEqual(result["choices"], [])
        self.assertEqual(len(result["partial_segments"]), 1)
        segment = result["partial_segments"][0]
        self.assertEqual([local(row["id"]) for row in segment["steps"]], ["CaptureSpeech"])
        self.assertEqual([local(row["id"]) for row in segment["missing_functions"]], ["Review"])
        self.assertFalse(segment["covers_all_required_functions"])
        self.assertFalse(segment["ready_for_whole_task"])
        self.assertEqual(segment["entry"]["origin"], "DECLARED_TASK_INPUT")
        self.assertEqual([local(row["id"]) for row in segment["remaining_after"]], ["Review"])

    def test_internal_segment_does_not_assume_prior_output_exists(self):
        case = speech_visual_context()
        case["facts"]["CanUseSpeech"] = False
        result = Composer(BASE_FILES).compose(case)
        self.assertEqual(result["proposal_status"], "PARTIAL")
        segment = result["partial_segments"][0]
        self.assertEqual([local(row["id"]) for row in segment["steps"]], ["ReviewText"])
        self.assertEqual(segment["entry"]["origin"], "PRIOR_FUNCTION_OUTPUT_REQUIRED")
        self.assertEqual(local(segment["entry"]["prior_function"]), "Expression")
        self.assertFalse(segment["entry"]["availability_verified"])
        self.assertFalse(segment["ready_for_whole_task"])

    def test_pending_whole_plan_separates_usable_step_and_question(self):
        case = speech_visual_context()
        case["facts"]["CanCorrect"] = None
        result = Composer(BASE_FILES).compose(case)
        self.assertEqual(result["proposal_status"], "CONDITIONAL")
        self.assertEqual(result["choices"], [])
        self.assertTrue(result["pending_candidates"])
        self.assertTrue(result["partial_segments"])
        self.assertIn("CanCorrect", {local(item["id"]) for item in result["facts_to_confirm"]})
        for segment in result["partial_segments"]:
            self.assertTrue(all(step["state"] == "PASS" for step in segment["steps"]))
        for candidate in result["pending_candidates"]:
            self.assertFalse(candidate["conditions_satisfied"])
            self.assertTrue(candidate["covers_all_required_functions"])

    def test_known_impediment_is_not_reported_as_missing_information(self):
        case = speech_visual_context()
        case["facts"]["CanCorrect"] = False
        result = Composer(BASE_FILES).compose(case)
        self.assertIn("CanCorrect", {local(item["id"]) for item in result["unavailable_conditions"]})
        self.assertNotIn("CanCorrect", {local(item["id"]) for item in result["facts_to_confirm"]})

    def test_missing_final_function_does_not_hide_supported_prior_sequence(self):
        composer = Composer(BASE_FILES)
        composer.graph.add((V2.Submit, RDF.type, V2.Function))
        composer.graph.add((V2.Submit, V2.order, Literal(3)))
        composer.graph.add((V2.SubmittedText, RDF.type, V2.Representation))
        composer.graph.add((V2.TaskCreateReviewedText, V2.requiresFunction, V2.Submit))
        composer.graph.set((V2.TaskCreateReviewedText, V2.outputType, V2.SubmittedText))
        result = composer.compose(speech_visual_context())
        self.assertEqual(result["proposal_status"], "PARTIAL")
        self.assertEqual(result["choices"], [])
        self.assertEqual(len(result["partial_segments"]), 1)
        segment = result["partial_segments"][0]
        self.assertEqual([local(row["id"]) for row in segment["steps"]], ["CaptureSpeech", "ReviewText"])
        self.assertEqual([local(row["id"]) for row in segment["remaining_after"]], ["Submit"])
        self.assertFalse(segment["ready_for_whole_task"])
        self.assertTrue(any("Não implica conclusão, envio" in limit for limit in segment["limits"]))

    def test_disconnected_steps_are_not_combined_into_a_fake_complete_path(self):
        composer = Composer(BASE_FILES)
        composer.graph.remove((V2.ProductionThenReview, None, None))
        result = composer.compose(speech_visual_context())
        self.assertEqual(result["proposal_status"], "PARTIAL")
        self.assertEqual(result["choices"], [])
        self.assertTrue(result["integration_gaps"])
        self.assertEqual(len(result["partial_segments"]), 2)
        self.assertTrue(all(len(segment["steps"]) == 1 for segment in result["partial_segments"]))
        self.assertEqual(result["missing_functions"], [])
        self.assertTrue(all(row["state"] == "CAPABILITY_AVAILABLE" for row in result["function_coverage"]))

    def test_bounded_search_discloses_incomplete_enumeration(self):
        with patch("composer.MAX_COMBINATIONS_PER_PHASE", 1):
            result = Composer(BASE_FILES).compose(speech_visual_context())
        self.assertTrue(any(row["truncated"] for row in result["search"].values()))
        self.assertTrue(any(row["code"] == "SEARCH_LIMIT_REACHED" for row in result["gaps"]))
        self.assertNotEqual(result["status"], "COMPOSED")

    def test_unknown_condition_of_impossible_route_is_not_a_question(self):
        case = keyboard_audio_context()
        case["facts"]["SpeechInputUsable"] = None
        result = Composer([*BASE_FILES, EXTENSION]).compose(case)
        self.assertEqual(result["proposal_status"], "COMPLETE")
        self.assertNotIn("SpeechInputUsable", {local(row["id"]) for row in result["facts_to_confirm"]})
        case["facts"]["CanCorrect"] = None
        result = Composer([*BASE_FILES, EXTENSION]).compose(case)
        self.assertEqual(result["proposal_status"], "CONDITIONAL")
        self.assertEqual({local(row["id"]) for row in result["facts_to_confirm"]}, {"CanCorrect"})

    def test_review_existing_content_never_assumes_content_exists(self):
        for factory in (speech_visual_context, keyboard_audio_context):
            for value in (False, None):
                with self.subTest(mode=factory.__name__, content=value):
                    case = factory()
                    case["task"] = "TaskReviewExistingText"
                    case["facts"]["ContentAvailable"] = value
                    result = Composer([*BASE_FILES, EXTENSION]).compose(case)
                    self.assertEqual(result["choices"], [])
                    self.assertEqual(result["proposal_status"], "NONE" if value is False else "CONDITIONAL")
                    self.assertEqual(result["partial_segments"], [])
                    if value is None:
                        self.assertIn("ContentAvailable", {local(row["id"]) for row in result["facts_to_confirm"]})


if __name__ == "__main__":
    unittest.main(verbosity=2)
