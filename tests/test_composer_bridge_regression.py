"""Synthetic regressions of existing ID bridges and honest functional coverage."""
import copy
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))
sys.path.insert(0, str(ROOT / "experimental/v2/tests"))

from experimental.v2.composer import Composer, V2
from experimental.v2.trajectory import ResearchComposer
from test_situated_composition import synthetic_catalogue
from test_trajectory import trajectory_context


def speech_context():
    context = trajectory_context()
    context["facts"].update(CanUseSpeech=True, SpeechInputUsable=True, SpeechEffortAcceptable=True,
        SpeechCompatible=True, SpeechFeedbackPerceptible=True, CanUseKeyboard=False,
        CanReviewVisualText=True, CanReviewSpeech=False)
    context["resources"].update(Microphone=True, SpeechRecognition=True, Display=True,
        Keyboard=False, TextToSpeech=False, AudioOutput=False)
    return context


class ResourceBridgeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.composer = ResearchComposer(legacy_projection=False)

    def test_microphone_identity_bridge_does_not_infer_recognizer(self):
        context = speech_context()
        context["resources"]["REC-MICROFONE"] = context["resources"].pop("Microphone")
        self.assertEqual(self.composer.compose_context(context)["status"], "COMPOSED")
        context["resources"]["SpeechRecognition"] = False
        blocked = self.composer.compose_context(context)
        self.assertFalse(blocked["choices"])
        self.assertTrue(any(r["id"] == str(V2.CaptureSpeech) for r in blocked["exclusions"]))

    def test_voice_control_is_not_recognizer_and_monitor_is_not_legible_display(self):
        context = speech_context()
        context["resources"].pop("SpeechRecognition")
        context["recursos_disponiveis"] = ["REC-ENTRADA-VOZ", "REC-COMPUTADOR"]
        pending = self.composer.compose_context(context)
        self.assertFalse(pending["choices"])
        self.assertIn(str(V2.SpeechRecognition), {r["id"] for r in pending["resources_to_confirm"]})

    def test_legacy_resource_arrays_and_scoped_facts_use_same_identity(self):
        context = speech_context()
        context["resources"].pop("Microphone")
        context["recursos_disponiveis"] = ["REC-MICROFONE"]
        self.assertEqual(self.composer.compose_context(context)["status"], "COMPOSED")
        context["recursos_impedidos"] = [str(V2.Microphone)]
        conflict = self.composer.compose_context(context)
        self.assertFalse(conflict["choices"])
        self.assertIn("CONFLICTING_RESOURCE_STATE", {r["code"] for r in conflict["input_issues"]})

    def test_scoped_fact_local_name_is_canonical_and_unknown_is_not_repeated(self):
        context = speech_context()
        context["facts"].pop("CanUseSpeech")
        context["situated_facts"] = [{"participant_id": context["id"], "situation_id": "situation-default",
                                     "fact_id": "CanUseSpeech", "value": True}]
        self.assertEqual(self.composer.compose_context(context)["status"], "COMPOSED")
        context["situated_facts"][0]["value"] = None
        unknown = self.composer.compose_context(context)
        self.assertFalse(any(r["id"] == str(V2.CanUseSpeech) for r in unknown["facts_to_confirm"]))
        self.assertTrue(any(r["id"] == str(V2.CanUseSpeech) and r.get("answered_unknown")
                            for r in unknown["other_condition_diagnostics"]))

    def test_alias_conflict_does_not_silently_overwrite_capability(self):
        context = speech_context()
        context["situated_facts"] = [{"participant_id": context["id"], "situation_id": "situation-default",
                                     "fact_id": str(V2.CanUseSpeech), "value": False}]
        result = self.composer.compose_context(context)
        self.assertFalse(result["choices"])
        self.assertIn("CONFLICTING_SITUATED_FACT", {r["code"] for r in result["input_issues"]})

    def test_resource_and_fact_bridge_do_not_cross_people_or_situations(self):
        first = speech_context()
        people = [{"id": "first", "facts": first["facts"], "resources": first["resources"]},
                  {"id": "second", "facts": {**first["facts"], "CanUseSpeech": False},
                   "resources": {**first["resources"], "Microphone": False}}]
        context = {"id": "two", "confirmed": True, "active_situation_id": "second-situation",
                   "participations": people,
                   "situations": [{"id": "first-situation", "participant_ids": ["first"],
                                    "task_ids": [str(V2.TaskCreateReviewedText)]},
                                   {"id": "second-situation", "participant_ids": ["second"],
                                    "task_ids": [str(V2.TaskCreateReviewedText)]}],
                   "situated_facts": [{"participant_id": "first", "situation_id": "first-situation",
                                       "fact_id": "REC-MICROFONE", "value": True}]}
        result = self.composer.compose_context(context)
        self.assertFalse(result["choices"])
        self.assertTrue(all(r["participant_id"] == "second" for r in result["required_functions"]))


class CoverageScopeTests(unittest.TestCase):
    def setUp(self):
        self.composer = Composer([])
        self.composer.base = synthetic_catalogue()
        self.context = {"id": "unknown", "confirmed": True, "tarefas": ["NEW_TASK"],
                        "funcoes_requeridas_ids": ["F-A", "F-B"], "facts": {"R:sufficiency": True}}

    def test_new_task_with_declared_functions_can_compose_without_claiming_whole_task(self):
        result = self.composer.compose_context(self.context)
        self.assertEqual(result["status"], "COMPOSED")
        self.assertEqual(result["coverage_scope"], "DECLARED_FUNCTIONS_ONLY")
        self.assertFalse(result["covers_whole_reported_task"])
        self.assertTrue(result["choices"][0]["ready_for_functional_scope"])
        self.assertFalse(result["choices"][0]["ready_for_whole_task"])

    def test_prioritized_episode_does_not_claim_whole_report(self):
        composer = ResearchComposer(legacy_projection=False)
        pilot = speech_context()
        context = {"id": "prioritized", "confirmed": True, "active_situation_id": "now",
                   "participations": [{"id": "p", "facts": pilot["facts"], "resources": pilot["resources"]}],
                   "situations": [{"id": "now", "participant_ids": ["p"], "task_ids": [str(V2.TaskCreateReviewedText)]},
                                  {"id": "later", "participant_ids": ["p"], "task_ids": ["TAR-OPERAR-SISTEMA"]}]}
        result = composer.compose_context(context)
        self.assertEqual(result["proposal_status"], "COMPLETE")
        self.assertTrue(result["covers_selected_scope"])
        self.assertFalse(result["covers_whole_reported_task"])
        self.assertFalse(result["covers_all_participants"])
        self.assertEqual(result["deferred_situation_ids"], ["later"])
        self.assertIn("situação priorizada", result["coverage_explanation"])


class FunctionalObservationBridgeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from test_narrative_to_actions import DecisionEngine, intake, confirm_presentation, confirmed_context
        cls.engine = DecisionEngine()
        intake(cls.engine, "presentation")
        confirm_presentation(cls.engine)
        cls.context = confirmed_context(cls.engine)

    def functions(self, context, composer=None):
        result = (composer or ResearchComposer(legacy_projection=False)).compose_context(context, engine=self.engine)
        return [{**r, "id": r["function_id"]} for r in result["required_functions"]]

    def test_observation_bridge_preserves_owner_and_source(self):
        rows = self.functions(self.context)
        recovered = next(r for r in rows if r["id"] == "FUN-MANTER-INFORMACAO-RECUPERAVEL")
        source = self.context["access_requirements"][0]
        self.assertEqual(recovered["participant_id"], source["participant_id"])
        self.assertEqual(recovered["situation_id"], source["situation_ids"][0])
        self.assertTrue(any(w["observation_bridge"] and w["assertions"] for w in recovered["witnesses"]))
        self.assertNotIn("FUN-ORGANIZAR-CONTEUDO", {r["id"] for r in rows})

    def test_wrong_scope_group_or_retired_observation_cannot_authorize(self):
        for mutation in ("person", "situation", "group", "retired", "conflict", "positive"):
            context = copy.deepcopy(self.context)
            requirement = context["access_requirements"][0]
            assertion = next(a for a in context["assertions"] if a["id"] == requirement["assertion_ids"][0])
            if mutation == "person": requirement["participant_id"] = "someone-else"
            if mutation == "situation": requirement["situation_ids"] = ["somewhere-else"]
            if mutation == "group": requirement["trigger_group_id"] = "MF-04-G1"
            if mutation == "retired": assertion["state"] = "RETIRADO_POR_CORRECAO"
            if mutation == "conflict": assertion["state"] = "CONFLITO"
            if mutation == "positive": assertion["value"] = "conseguem retomar as instruções"
            self.assertNotIn("FUN-MANTER-INFORMACAO-RECUPERAVEL", {r["id"] for r in self.functions(context)}, mutation)

    def test_supplied_functions_are_not_authority_and_claim_is_rechecked(self):
        context = copy.deepcopy(self.context)
        context["access_requirements"][0]["function_ids"] = ["FUN-ORGANIZAR-CONTEUDO"]
        rows = self.functions(context)
        self.assertIn("FUN-MANTER-INFORMACAO-RECUPERAVEL", {r["id"] for r in rows})
        self.assertNotIn("FUN-ORGANIZAR-CONTEUDO", {r["id"] for r in rows})
        requirement = next(row for row in rows if row["id"] == "FUN-MANTER-INFORMACAO-RECUPERAVEL")
        self.assertIn("APP-ART-TRF-04-ORGANIZAR-RETOMAR", requirement["claim_ids"])
        composer = ResearchComposer(legacy_projection=False)
        application = next(app for articulation in composer.base["articulations"]
                           for app in articulation.get("operational_applications", [])
                           if app["id"] == "APP-ART-TRF-04-ORGANIZAR-RETOMAR")
        # Retomada is now supported by this delimited analytical application,
        # not by K40's historical audio/mobility claim. Withdraw a real premise.
        self.assertIn("CLM-K38-MMI-NAV", {premise["claim_id"] for premise in application["premises"]})
        knowledge = next(k for k in composer.base["knowledge"] if k["id"] == "K38")
        claim = next(claim for claim in knowledge["operation_claims"] if claim["id"] == "CLM-K38-MMI-NAV")
        claim["status"] = "PENDING"
        self.assertNotIn("FUN-MANTER-INFORMACAO-RECUPERAVEL", {r["id"] for r in self.functions(context, composer)})


class RemainingCoverageScopeTests(unittest.TestCase):
    setUp = CoverageScopeTests.setUp

    def test_additional_unmapped_action_blocks_whole_challenge_but_keeps_support(self):
        self.context["tarefas"].append("SEND_FORM")
        result = self.composer.compose_context(self.context)
        self.assertFalse(result["choices"])
        self.assertTrue(result["partial_segments"])
        self.assertIn("UNMAPPED_TASK", {r["code"] for r in result["gaps"]})
        self.assertTrue(all(r["type"] == "FUNCTION_GAP" for r in result["gaps"] if r["code"] == "UNMAPPED_TASK"))

    def test_unmapped_explicit_need_is_not_silently_discarded(self):
        self.context["necessidades"] = ["UNREPRESENTED_NEED"]
        result = self.composer.compose_context(self.context)
        self.assertFalse(result["choices"])
        self.assertTrue(result["partial_segments"])
        gap = next(r for r in result["gaps"] if r["code"] == "UNMAPPED_NEED")
        self.assertEqual(gap["id"], "UNREPRESENTED_NEED")
        self.assertFalse(result["facts_to_confirm"])

    def test_no_operation_is_not_mislabeled_as_missing_user_information(self):
        self.composer.base["context_elements"].append({"id": "F-C", "rotulo": "Unsupported function"})
        self.context["funcoes_requeridas_ids"].append("F-C")
        result = self.composer.compose_context(self.context)
        self.assertFalse(result["choices"])
        self.assertIn("NO_OPERATION_FOR_REQUIRED_FUNCTION", {r["code"] for r in result["gaps"]})
        self.assertFalse(result["facts_to_confirm"])


if __name__ == "__main__":
    unittest.main()
