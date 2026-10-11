"""No capability may migrate from a group member or a diagnosis to another."""
import copy
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE.parents[1] / "vendor"))
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from trajectory import ResearchComposer
from test_trajectory import trajectory_context


def group_context():
    first = trajectory_context()
    second = copy.deepcopy(first)
    second["resources"].update(Display=True, AudioOutput=False)
    second["facts"].update(CanReviewVisualText=True, CanReviewSpeech=False, AudioUsable=False)
    shared = {"ContentAvailable": True, "LearningCommunicationContext": True}
    return {"id": "SYNTHETIC-UNREGISTERED-GROUP", "task": first["task"], "confirmed": True,
            "facts": shared, "resources": {"EditableText": True},
            "participants": [{"id": "P1", "label": "Condições declaradas A", "traits": [],
                              "facts": {key: value for key, value in first["facts"].items() if key not in shared},
                              "resources": first["resources"]},
                             {"id": "P2", "label": "Condições declaradas B", "traits": [],
                              "facts": {key: value for key, value in second["facts"].items() if key not in shared},
                              "resources": second["resources"]}]}


class ParticipantTests(unittest.TestCase):
    def test_distinct_routes_use_conditions_of_their_own_participant(self):
        result = ResearchComposer().compose(group_context())
        self.assertEqual(result["status"], "COMPOSED")
        self.assertTrue(result["covers_all_participants"])
        self.assertEqual(len(result["participant_results"]), 2)
        self.assertTrue(result["fingerprints"])
        routes = {row["participant_id"]: {step["id"].rsplit("#", 1)[-1] for choice in row["result"]["choices"] for step in choice["steps"]}
                  for row in result["participant_results"]}
        self.assertEqual(routes["P1"], {"CaptureKeyboard", "ReviewSpeech"})
        self.assertEqual(routes["P2"], {"CaptureKeyboard", "ReviewText"})
        checks = result["execution_evidence"]
        self.assertEqual(len({row["id"] for row in checks}), len(checks))
        self.assertTrue(all(row.get("participant_id") for row in checks))

    def test_missing_personal_capacities_are_not_filled_by_global_true_or_diagnosis(self):
        context = group_context()
        context["facts"]["CanReviewVisualText"] = True
        context["participants"][1]["facts"] = {}
        context["participants"][1]["traits"] = ["Pessoa surda"]
        result = ResearchComposer().compose(context)
        self.assertEqual(result["status"], "INSUFFICIENT")
        self.assertEqual(result["proposal_status"], "PARTIAL")
        self.assertEqual(result["choices"], [])
        self.assertFalse(result["covers_all_participants"])
        self.assertTrue(result["unscoped_personal_facts"])
        self.assertTrue(all(row.get("participant_id") for row in result["facts_to_confirm"]))
        self.assertEqual(result["participant_results"][1]["result"]["choices"], [])

    def test_resource_available_to_one_person_is_not_operability_of_another(self):
        context = group_context()
        context["resources"].update(Keyboard=True, Display=True)
        context["participants"][1]["facts"]["CanUseKeyboard"] = False
        result = ResearchComposer().compose(context)
        self.assertEqual(result["status"], "INSUFFICIENT")
        individual = result["participant_results"][1]["result"]
        self.assertFalse(any(step["id"].endswith("CaptureKeyboard") for choice in individual["choices"] for step in choice["steps"]))

    def test_conflicting_shared_facts_and_duplicate_people_are_blocked(self):
        for change in ("fact", "id"):
            context = group_context()
            if change == "fact":
                context["participants"][1]["facts"]["ContentAvailable"] = False
            else:
                context["participants"][1]["id"] = "P1"
            result = ResearchComposer().compose(context)
            self.assertEqual(result["status"], "INSUFFICIENT")
            self.assertTrue(result["input_issues"])
            self.assertEqual(result["participant_results"], [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
