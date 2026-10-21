"""Held-out synthetic narratives and causal mechanism checks, not user validation.

The three original texts are the only input to the public intake/generation flow.
No condition is completed through the API. A structured-context comparison sends
the same confirmed ledger directly to the compositor: it checks contract parity,
not an independently annotated interpretation. Intake semantics have separate
tests in test_articulation_intake.py. Counterfactuals change explicit sentences;
foundation ablations mutate only a fresh in-memory copy of the research base.
"""
from __future__ import annotations

import copy
import json
from pathlib import Path
import sys
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from engine import DecisionEngine
from experimental.v2.composer import V2
from experimental.v2.trajectory import ResearchComposer
from rdflib import RDF

CASES = {row["id"]: row for row in json.loads(
    (ROOT / "tests/fixtures/articulation_transfer_cases.json").read_text(encoding="utf-8"))}
PLAN_FIELDS = ("choices", "pending_candidates", "partial_segments")
CAPTIONS = "OP-PAD-VIDEO-PROCESSO-CAPTIONS"
DESCRIPTION = "OP-PAD-VIDEO-PROCESSO-AUDIO_DESCRIPTION"
CAPTIONS_APP = "APP-ART-TRF-02-CAPTIONS"


def public_run(text):
    engine = DecisionEngine()
    engine.analyze_narrative(text)
    engine.update_context({"mapping_confirmed": True})
    context = copy.deepcopy(engine.current["context"])
    context["participations"] = copy.deepcopy(engine.current["participations"])
    context["confirmed"] = True
    result = engine.generate_situated()
    return context, result


def plans(result):
    return [plan for field in PLAN_FIELDS for plan in result.get(field, [])]


def offered_ids(result, participant_id=None):
    return {step["id"] for plan in plans(result)
            if participant_id is None or plan.get("participant_id") == participant_id
            for step in plan["steps"]}


def person_with_condition(context, term):
    return next(person["id"] for person in context["participations"]
                if person.get("reported_condition", {}).get("text") == term)


def signature(result, context):
    """Decision semantics without random session/person/proposal/check identifiers.

    Do not snapshot prose, generated hashes, ranks or incidental evidence order.
    Preserve the order of operations because sequence is a semantic property.
    """
    identities = {person["id"]: f"person-{position}:{person.get('label', '')}"
                  for position, person in enumerate(context["participations"])}
    identities.update({situation["id"]: f"situation-{position}:{situation.get('kind', '')}"
                       for position, situation in enumerate(context["situations"])})

    def owner(value):
        return identities.get(value, value)

    def identifiers(rows):
        return tuple(sorted(row["id"] if isinstance(row, dict) else row for row in rows))

    def step_key(step):
        return (step["id"], step["state"], tuple(sorted(step.get("function_ids", []))),
                tuple(sorted(step.get("selected_representation_ids", []))),
                tuple(sorted((row["id"], row["phase"], row["state"])
                             for row in step.get("phase_conditions", []))))

    def plan_key(plan):
        relations = tuple(sorted((row["id"], row.get("kind", ""),
                                  row.get("from_capability", ""), row.get("to_capability", ""))
                                 for row in plan.get("relations", [])))
        return (owner(plan.get("participant_id")), owner(plan.get("situation_id")),
                plan["state"], tuple(step_key(step) for step in plan["steps"]), relations,
                identifiers(plan.get("covered_functions", [])),
                identifiers(plan.get("missing_functions", [])),
                plan.get("covers_all_required_functions"), plan.get("ready_for_application"))

    return {
        "status": result["status"],
        "plans": {field: sorted(plan_key(plan) for plan in result.get(field, []))
                  for field in PLAN_FIELDS},
        "operations": sorted((owner(row.get("participant_id")), owner(row.get("situation_id")),
                              step_key(row)) for row in result.get("capability_evaluations", [])),
        "required": sorted((owner(row.get("participant_id")), owner(row.get("situation_id")),
                            row["function_id"]) for row in result["required_functions"]),
    }


class ArticulationExecutionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.runs = {identifier: public_run(row["narrative"]) for identifier, row in CASES.items()}

    def direct(self, identifier, change=None):
        context = copy.deepcopy(self.runs[identifier][0])
        composer = ResearchComposer(legacy_projection=False)
        if change:
            change(composer)
        return composer.compose_context(context)

    def test_three_original_narratives_reach_grounded_support_without_hidden_answers(self):
        for identifier, (context, result) in self.runs.items():
            with self.subTest(case=identifier):
                self.assertTrue(CASES[identifier]["synthetic"])
                self.assertTrue(result["required_functions"])
                self.assertTrue(plans(result), "The original narrative must produce support or a conditional possibility.")
                self.assertTrue(all(step["groundings"] for plan in plans(result) for step in plan["steps"]))
                self.assertFalse(any(plan.get("ready_for_application") for plan in plans(result)
                                     if any(condition["state"] != "PASS" for step in plan["steps"]
                                            for condition in step.get("phase_conditions", []))))

    def test_public_flow_matches_identical_confirmed_context_without_added_facts(self):
        for identifier, (context, result) in self.runs.items():
            with self.subTest(case=identifier):
                self.assertEqual(signature(result, context), signature(self.direct(identifier), context))

    def test_repeated_intake_is_deterministic_despite_new_session_ids(self):
        for identifier, (context, result) in self.runs.items():
            with self.subTest(case=identifier):
                repeated_context, repeated = public_run(CASES[identifier]["narrative"])
                self.assertEqual(signature(result, context), signature(repeated, repeated_context))

    def test_unknown_clarifications_preserve_original_personal_access_routes(self):
        engine = DecisionEngine()
        engine.analyze_narrative(CASES["recorded_content_access"]["narrative"])
        for _ in range(3):
            questions = engine.missing_questions()
            if not questions:
                break
            engine.update_context({"question_answers": [{"question_id": questions[0]["id"],
                "state": "UNKNOWN", "value": "unknown"}]})
        engine.update_context({"mapping_confirmed": True})
        context = dict(engine.current["context"], participations=engine.current["participations"])
        result = engine.generate_situated()
        self.assertIn(DESCRIPTION, offered_ids(result, person_with_condition(context, "cega")))
        self.assertIn(CAPTIONS, offered_ids(result, person_with_condition(context, "surda")))

    def test_catalogue_covers_organization_and_retrieval_separately(self):
        _, result = self.runs["catalogue_sequence"]
        steps = [step for plan in plans(result) for step in plan["steps"]]
        self.assertTrue(any({"FUN-ORGANIZAR-CONTEUDO", "FUN-MANTER-INFORMACAO-RECUPERAVEL"}
                            <= set(step["function_ids"]) for step in steps))
        self.assertFalse(any("HAPTICO" in step["id"] for step in steps))
        self.assertTrue(any(condition["phase"] == "production" and condition["state"] == "NOT_EXECUTED"
                            for step in steps for condition in step.get("phase_conditions", [])))

    def test_projector_removal_does_not_remove_individual_consultation_support(self):
        context, original = self.runs["catalogue_sequence"]
        text = CASES["catalogue_sequence"]["narrative"].replace(
            "com demonstração no projetor e prática no computador de cada pessoa",
            "sem projetor, com prática no computador de cada pessoa")
        changed_context, changed = public_run(text)
        self.assertTrue(offered_ids(original))
        self.assertEqual(signature(original, context), signature(changed, changed_context))

    def test_recorded_content_selects_routes_for_each_person_not_union_of_abilities(self):
        context, result = self.runs["recorded_content_access"]
        blind = person_with_condition(context, "cega")
        deaf = person_with_condition(context, "surda")
        self.assertIn(DESCRIPTION, offered_ids(result, blind))
        self.assertIn(CAPTIONS, offered_ids(result, deaf))
        for plan in plans(result):
            if plan.get("participant_id") == blind:
                for step in plan["steps"]:
                    if step["id"] == DESCRIPTION:
                        self.assertNotIn("MOD-TEXTO", step["selected_representation_ids"])

    def test_audio_loss_removes_blind_audio_route_not_other_participants_written_route(self):
        original_context, original = self.runs["recorded_content_access"]
        text = CASES["recorded_content_access"]["narrative"].replace(
            "consegue ouvir áudio", "não consegue ouvir áudio")
        context, result = public_run(text)
        self.assertIn(DESCRIPTION, offered_ids(original, person_with_condition(original_context, "cega")))
        self.assertNotIn(DESCRIPTION, offered_ids(result, person_with_condition(context, "cega")))
        self.assertIn(CAPTIONS, offered_ids(result, person_with_condition(context, "surda")))
        blind_operations = [step for step in result["capability_evaluations"]
                            if step.get("participant_id") == person_with_condition(context, "cega")]
        self.assertTrue(any(step["id"] == DESCRIPTION and step["state"] == "FAIL" for step in blind_operations))

    def test_dictation_uses_production_review_relation_without_educational_requirement(self):
        _, result = self.runs["dictation_review_control"]
        self.assertTrue(any({str(V2.CaptureSpeech), str(V2.ReviewText)} <= {step["id"] for step in plan["steps"]}
                            and str(V2.ProductionThenReview) in {row["id"] for row in plan["relations"]}
                            for plan in plans(result)))
        self.assertNotIn(str(V2.CaptureKeyboard), offered_ids(result), "Small corrections do not authorize prolonged typing.")

    def test_noise_blocks_speech_capture_but_retains_supported_review(self):
        text = CASES["dictation_review_control"]["narrative"].replace(
            "Estou numa sala silenciosa, sem outras pessoas ouvindo, e posso controlar quando começar, parar e confirmar o registro.",
            "Agora há ruído e o reconhecimento de fala não funciona neste ambiente; posso controlar quando começar, parar e confirmar o registro.")
        _, result = public_run(text)
        self.assertNotIn(str(V2.CaptureSpeech), offered_ids(result))
        self.assertNotIn(str(V2.CaptureKeyboard), offered_ids(result))
        self.assertIn(str(V2.ReviewText), offered_ids(result))

    def test_bibliographic_entry_alone_changes_no_decision(self):
        def add_unused_bibliography(composer):
            composer.base["references"].append({"id": "SYNTHETIC-UNUSED-REFERENCE",
                "titulo": "Synthetic bibliography-only ablation fixture", "url": "https://example.org/unused"})
        for identifier, (context, result) in self.runs.items():
            with self.subTest(case=identifier):
                self.assertEqual(signature(result, context), signature(self.direct(identifier, add_unused_bibliography), context))

    def test_missing_caption_contribution_blocks_dependent_route_not_audio_description(self):
        def remove_contribution(composer):
            composer.base["contributions"] = [row for row in composer.base["contributions"]
                                               if row["id"] != "C-K42-WCAG-0148"]
        context, original = self.runs["recorded_content_access"]
        changed = self.direct("recorded_content_access", remove_contribution)
        blind, deaf = person_with_condition(context, "cega"), person_with_condition(context, "surda")
        self.assertIn(CAPTIONS, offered_ids(original, deaf))
        self.assertNotIn(CAPTIONS, offered_ids(changed, deaf))
        self.assertIn(DESCRIPTION, offered_ids(changed, blind))
        self.assertTrue(any(row["kind"] == "ANALYTICAL_APPLICATION" and row["state"] == "FAIL"
                            for row in changed["execution_evidence"]))

    def test_missing_specific_application_cannot_borrow_another_articulation(self):
        def remove_application(composer):
            for articulation in composer.base["articulations"]:
                articulation["operational_applications"] = [row for row in articulation.get("operational_applications", [])
                                                             if row["id"] != CAPTIONS_APP]
        context, original = self.runs["recorded_content_access"]
        changed = self.direct("recorded_content_access", remove_application)
        blind, deaf = person_with_condition(context, "cega"), person_with_condition(context, "surda")
        self.assertIn(CAPTIONS, offered_ids(original, deaf))
        self.assertNotIn(CAPTIONS, offered_ids(changed, deaf))
        self.assertIn(DESCRIPTION, offered_ids(changed, blind))

    def test_removing_sequence_relation_preserves_independent_operations(self):
        def remove_sequence(composer):
            composer.graph.remove((V2.ProductionThenReview, RDF.type, V2.RelationRule))
        changed = self.direct("dictation_review_control", remove_sequence)
        offered = offered_ids(changed)
        self.assertIn(str(V2.CaptureSpeech), offered)
        self.assertIn(str(V2.ReviewText), offered)
        self.assertFalse(any(str(V2.ProductionThenReview) == relation["id"]
                             for plan in plans(changed) for relation in plan["relations"]))
        self.assertFalse(any({str(V2.CaptureSpeech), str(V2.ReviewText)} <= {step["id"] for step in plan["steps"]}
                             for plan in plans(changed)), "Independent support is not an invented connected route.")

    def test_original_test_narratives_are_not_in_browser_distribution_or_base(self):
        bundle = ROOT / "web/amado/assets/base.zip"
        self.assertTrue(bundle.is_file())
        texts = [ROOT / "data/knowledge-base.json"]
        texts.extend(path for path in (ROOT / "web").rglob("*")
                     if path.suffix in {".html", ".mjs", ".py", ".json"} and "vendor" not in path.parts)
        for path in texts:
            payload = path.read_text(encoding="utf-8", errors="replace")
            for identifier, case in CASES.items():
                self.assertNotIn(case["narrative"], payload, str(path))
                self.assertNotIn(identifier, payload, str(path))
        with zipfile.ZipFile(bundle) as archive:
            self.assertFalse(any("articulation_transfer_cases" in name or name.startswith("tests/")
                                 for name in archive.namelist()))
            for name in archive.namelist():
                payload = archive.read(name).decode("utf-8", errors="replace")
                for identifier, case in CASES.items():
                    self.assertNotIn(case["narrative"], payload, name)
                    self.assertNotIn(identifier, payload, name)


if __name__ == "__main__":
    unittest.main()
