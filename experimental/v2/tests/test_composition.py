"""Executable claims for the isolated V2 pilot, not human validation.

All contexts are synthetic fixtures authored in tests. The composer receives only
structured conditions; it does not load this module or a catalogue of scenarios.
Mutations below affect an in-memory RDF graph, never the preserved public base.
"""

from __future__ import annotations

import copy
import hashlib
import sys
import unittest
from pathlib import Path

V2_DIR = Path(__file__).resolve().parents[1]
REPO = V2_DIR.parents[1]
sys.path.insert(0, str(REPO / "vendor"))
sys.path.insert(0, str(V2_DIR))

from rdflib import Graph, Literal, Namespace, RDF, RDFS  # noqa: E402
from composer import Composer  # noqa: E402

V2 = Namespace("https://w3id.org/mado/experimental/v2#")
MADO = Namespace("https://w3id.org/mado#")
BASE_FILES = [V2_DIR / "schema.ttl", V2_DIR / "base.ttl"]
EXTENSION = V2_DIR / "extensions" / "audio-review.ttl"


def local(value):
    return str(value).rsplit("#", 1)[-1].rsplit("/", 1)[-1]


def signatures(result):
    """Decision semantics, independent of context labels and proposal hashes."""
    return {
        tuple(local(step["id"]) for step in choice["steps"])
        for choice in result["choices"]
    }


def speech_visual_context():
    return {
        "id": "synthetic-spoken-contribution",
        "task": "TaskCreateReviewedText",
        "confirmed": True,
        "resources": {
            "Microphone": True, "SpeechRecognition": True, "Keyboard": False,
            "EditableText": True, "Display": True, "TextToSpeech": False,
            "AudioOutput": False,
        },
        "facts": {
            "ContentAvailable": True, "CanUseSpeech": True,
            "SpeechInputUsable": True, "CanUseKeyboard": False,
            "CanReviewVisualText": True, "CanReviewSpeech": False,
            "AudioUsable": False, "CanControlPlayback": False,
            "CanCorrect": True, "ControlsCompletion": True,
        },
    }


def keyboard_audio_context():
    case = speech_visual_context()
    case["id"] = "synthetic-new-condition-conjunction"
    case["resources"].update(
        Microphone=False, SpeechRecognition=False, Keyboard=True, Display=False,
        TextToSpeech=True, AudioOutput=True,
    )
    case["facts"].update(
        CanUseSpeech=False, SpeechInputUsable=False, CanUseKeyboard=True,
        CanReviewVisualText=False, CanReviewSpeech=True, AudioUsable=True,
        CanControlPlayback=True,
    )
    return case


class CompositionTests(unittest.TestCase):
    def make(self, extension=False):
        return Composer([*BASE_FILES, *([EXTENSION] if extension else [])])

    def assert_not_ready(self, result):
        self.assertNotEqual(result["status"], "COMPOSED")
        self.assertEqual(result["choices"], [])

    def test_01_baseline_composes_speech_and_visual_review(self):
        result = self.make().compose(speech_visual_context())
        self.assertEqual(result["status"], "COMPOSED")
        self.assertEqual(signatures(result), {("CaptureSpeech", "ReviewText")})
        self.assertEqual(result["choices"][0]["relations"][0]["kind"], "SEQUENTIAL_REVIEW")

    def test_02_new_conjunction_requires_documented_knowledge_increment(self):
        case = keyboard_audio_context()
        baseline = self.make().compose(case)
        extended = self.make(True).compose(case)
        self.assert_not_ready(baseline)
        self.assertEqual(extended["status"], "COMPOSED")
        self.assertEqual(signatures(extended), {("CaptureKeyboard", "ReviewSpeech")})
        supporting_knowledge = {
            local(support["knowledge"]["id"])
            for step in extended["choices"][0]["steps"]
            for support in step["groundings"]
        }
        self.assertIn("KAudioReview", supporting_knowledge)

    def test_03_extension_does_not_add_capability_rule_action_task_or_scenario(self):
        base, extended = self.make(), self.make(True)
        for entity_type in (V2.Capability, V2.RelationRule, V2.Task, V2.Function):
            with self.subTest(entity_type=local(entity_type)):
                before = set(base.graph.subjects(RDF.type, entity_type))
                after = set(extended.graph.subjects(RDF.type, entity_type))
                self.assertEqual(before, after)
                for entity in before:
                    self.assertEqual(set(base.graph.predicate_objects(entity)),
                                     set(extended.graph.predicate_objects(entity)))
        extension = Graph().parse(EXTENSION, format="turtle")
        self.assertEqual(list(extension.triples((None, V2.action, None))), [])
        self.assertEqual(list(extension.triples((None, RDF.type, MADO.ContextoDeInteracaoDigital))), [])
        before_engine = hashlib.sha256((V2_DIR / "composer.py").read_bytes()).hexdigest()
        extended.compose(keyboard_audio_context())
        self.assertEqual(before_engine, hashlib.sha256((V2_DIR / "composer.py").read_bytes()).hexdigest())

    def test_04_removing_extension_reverses_its_operational_effect(self):
        case = keyboard_audio_context()
        self.assert_not_ready(self.make().compose(case))
        self.assertEqual(self.make(True).compose(case)["status"], "COMPOSED")
        self.assert_not_ready(self.make().compose(case))

    def test_05_bibliography_alone_never_enables_audio_review(self):
        composer = self.make()
        composer.graph.add((V2.ExtraReference, RDF.type, MADO.Fonte))
        composer.graph.add((V2.ExtraReference, RDFS.label, Literal("Referência bibliográfica adicional")))
        composer.graph.add((V2.ExtraReference, V2.url, Literal("https://example.org/reference")))
        self.assert_not_ready(composer.compose(keyboard_audio_context()))

    def test_06_missing_contributions_block_the_application(self):
        composer = self.make(True)
        for contribution in list(composer.graph.subjects(V2.inArticulation, V2.ArtAudioReview)):
            composer.graph.remove((contribution, None, None))
        self.assert_not_ready(composer.compose(keyboard_audio_context()))

    def test_07_missing_exact_support_cannot_be_replaced_by_other_grounding(self):
        composer = self.make(True)
        composer.graph.remove((V2.GroundAudioReview, None, None))
        self.assert_not_ready(composer.compose(keyboard_audio_context()))

    def test_08_unconfirmed_contribution_cannot_authorize_selection(self):
        composer = self.make(True)
        composer.graph.set((V2.CAudioMMI, V2.status, Literal("UNCONFIRMED")))
        self.assert_not_ready(composer.compose(keyboard_audio_context()))

    def test_09_missing_source_or_locator_blocks_grounding(self):
        for predicate in (MADO.trechoDeFonte, MADO.localizacaoDocumental):
            with self.subTest(predicate=local(predicate)):
                composer = self.make(True)
                composer.graph.remove((V2.ExcerptMMI, predicate, None))
                self.assert_not_ready(composer.compose(keyboard_audio_context()))

    def test_10_unknown_task_is_not_resolved_by_names_or_fallback(self):
        case = keyboard_audio_context()
        case["task"] = "ExplainHistoryByKeyboardAndSpeech"
        result = self.make(True).compose(case)
        self.assert_not_ready(result)
        self.assertTrue(result["input_issues"])

    def test_11_absent_and_null_resource_are_pending_false_is_exclusion(self):
        for value in (None, "ABSENT", False):
            with self.subTest(value=value):
                case = keyboard_audio_context()
                if value == "ABSENT":
                    del case["resources"]["TextToSpeech"]
                else:
                    case["resources"]["TextToSpeech"] = value
                result = self.make(True).compose(case)
                self.assert_not_ready(result)
                self.assertEqual(bool(result["pending_candidates"]), value is not False)
                matching = [row for row in result["execution_evidence"]
                            if row["kind"] == "REQUIRES_requiresResource"
                            and local(row["expected"]["concept"]) == "TextToSpeech"]
                self.assertTrue(matching)
                self.assertEqual({row["state"] for row in matching},
                                 {"FAIL" if value is False else "PENDING"})

    def test_12_absent_fact_is_pending_false_fact_blocks(self):
        for value in (None, False):
            with self.subTest(value=value):
                case = keyboard_audio_context()
                case["facts"]["CanCorrect"] = value
                result = self.make(True).compose(case)
                self.assert_not_ready(result)
                self.assertEqual(bool(result["pending_candidates"]), value is None)

    def test_13_every_ready_step_has_only_satisfied_resource_and_fact_requirements(self):
        case = keyboard_audio_context()
        composer = self.make(True)
        result = composer.compose(case)
        self.assertTrue(result["choices"])
        for choice in result["choices"]:
            for step in choice["steps"]:
                self.assertEqual(step["state"], "PASS")
                self.assertTrue(all(row["state"] == "PASS" for row in step["condition_checks"]))
                for record in step["required_resources"]:
                    self.assertIs(case["resources"][local(record["id"])], True)
                for record in step["required_facts"]:
                    self.assertIs(case["facts"][local(record["id"])], True)

    def test_14_diagnostic_or_persona_fields_are_rejected_not_inferred(self):
        for field in ("diagnosis", "persona", "role", "narrative", "theme"):
            with self.subTest(field=field):
                case = keyboard_audio_context()
                case[field] = "Professor, TEA, História, pessoa cega"
                result = self.make(True).compose(case)
                self.assert_not_ready(result)
                self.assertIn({"code": "UNKNOWN_CONTEXT_FIELD", "field": field}, result["input_issues"])

    def test_15_context_identifier_does_not_select_the_configuration(self):
        composer = self.make(True)
        case = keyboard_audio_context()
        original = composer.compose(case)
        for case_id in ("ENTREVISTA", "TEA", "BLIND", "MAPA", "sem-cadastro-8431"):
            case["id"] = case_id
            self.assertEqual(signatures(original), signatures(composer.compose(case)))

    def test_16_repeated_execution_is_deterministic_and_does_not_mutate_inputs(self):
        composer = self.make(True)
        case = keyboard_audio_context()
        before_case, before_graph = copy.deepcopy(case), set(composer.graph)
        first, second = composer.compose(case), composer.compose(case)
        self.assertEqual(first, second)
        self.assertEqual(case, before_case)
        self.assertEqual(set(composer.graph), before_graph)

    def test_17_single_function_reuses_review_without_forcing_a_second_modality(self):
        case = keyboard_audio_context()
        case["task"] = "TaskReviewExistingText"
        self.assert_not_ready(self.make().compose(case))
        result = self.make(True).compose(case)
        self.assertEqual(signatures(result), {("ReviewSpeech",)})
        self.assertEqual(result["choices"][0]["relations"], [])
        self.assertEqual(len(result["required_functions"]), 1)

    def test_18_incompatible_intermediate_representation_blocks_composition(self):
        composer = self.make(True)
        composer.graph.set((V2.ReviewSpeech, V2.inputType, V2.ContributionContent))
        result = composer.compose(keyboard_audio_context())
        self.assert_not_ready(result)
        self.assertTrue(any(row["kind"] == "TYPED_TRANSITION" and row["state"] == "FAIL"
                            for row in result["execution_evidence"]))

    def test_19_wrong_function_cannot_fulfil_required_review(self):
        composer = self.make(True)
        composer.graph.set((V2.ReviewSpeech, V2.provides, V2.Expression))
        self.assert_not_ready(composer.compose(keyboard_audio_context()))

    def test_20_relation_is_not_invented_from_adjacent_capabilities(self):
        composer = self.make(True)
        composer.graph.remove((V2.ProductionThenReview, None, None))
        result = composer.compose(keyboard_audio_context())
        self.assert_not_ready(result)
        self.assertTrue(any(row.get("reason") == "NO_AUTHORIZED_RELATION"
                            for row in result["exclusions"]))

    def test_21_relation_without_grounding_cannot_be_used(self):
        composer = self.make(True)
        composer.graph.remove((V2.ProductionThenReview, V2.articulation, None))
        self.assert_not_ready(composer.compose(keyboard_audio_context()))

    def test_22_sequential_review_is_not_automatically_care_complementarity(self):
        result = self.make(True).compose(keyboard_audio_context())
        self.assertTrue(result["choices"])
        for choice in result["choices"]:
            self.assertEqual(choice["epistemic_status"], "PROPOSED_NOT_EVALUATED")
            self.assertEqual({relation["kind"] for relation in choice["relations"]}, {"SEQUENTIAL_REVIEW"})
            self.assertTrue(any("não foi aplicada" in limit for limit in choice["limits"]))
            self.assertTrue(any("não comprova" in limit for limit in choice["limits"]))
        composer = self.make(True)
        composer.graph.set((V2.ProductionThenReview, V2.relationKind, Literal("CARE_COMPLEMENTARITY")))
        self.assert_not_ready(composer.compose(keyboard_audio_context()))

    def test_23_unconfirmed_case_does_not_execute_composition(self):
        case = keyboard_audio_context()
        case["confirmed"] = False
        result = self.make(True).compose(case)
        self.assertEqual(result["status"], "UNCONFIRMED")
        self.assertEqual(result["choices"], [])
        self.assertTrue(any(row["state"] == "NOT_EXECUTED" for row in result["execution_evidence"]))

    def test_24_all_explanation_checks_reference_execution_records(self):
        result = self.make(True).compose(keyboard_audio_context())
        self.assertTrue(result["choices"])
        known = {row["id"] for row in result["execution_evidence"]}
        def visit(value):
            if isinstance(value, dict):
                if "check_ids" in value:
                    self.assertTrue(set(value["check_ids"]).issubset(known))
                for item in value.values():
                    visit(item)
            elif isinstance(value, list):
                for item in value:
                    visit(item)
        visit(result["choices"])

    def test_25_wrong_produced_knowledge_blocks_articulation_application(self):
        composer = self.make(True)
        composer.graph.set((V2.ArtAudioReview, V2.produces, V2.KInput))
        self.assert_not_ready(composer.compose(keyboard_audio_context()))

    def test_26_unknown_resource_and_non_boolean_values_require_correction(self):
        for key, value in (("NewMagicDevice", True), ("TextToSpeech", "true"), ("TextToSpeech", 1)):
            with self.subTest(key=key, value=value):
                case = keyboard_audio_context()
                case["resources"][key] = value
                result = self.make(True).compose(case)
                self.assert_not_ready(result)
                self.assertTrue(result["input_issues"])

    def test_27_external_graph_labels_do_not_replace_functional_semantics(self):
        composer = self.make(True)
        original = composer.compose(keyboard_audio_context())
        composer.graph.set((V2.KAudioReview, RDFS.label, Literal("Outro título sem efeito decisório")))
        composer.graph.set((V2.CaptureKeyboard, RDFS.label, Literal("Operação alternativa")))
        self.assertEqual(signatures(original), signatures(composer.compose(keyboard_audio_context())))

    def test_28_declared_relations_and_exact_sources_are_present_in_explanation(self):
        result = self.make(True).compose(keyboard_audio_context())
        review = result["choices"][0]["steps"][-1]
        support = review["groundings"][0]
        self.assertEqual(local(support["id"]), "GroundAudioReview")
        self.assertEqual(local(support["knowledge"]["id"]), "KAudioReview")
        self.assertEqual(local(support["criterion"]["id"]), "CriterionReview")
        construction = support["articulation"]
        self.assertEqual(local(construction["id"]), "ArtAudioReview")
        self.assertTrue(construction["operation"])
        self.assertTrue(construction["added_understanding"])
        self.assertEqual({local(row["id"]) for row in construction["contributions"]},
                         {"CAudioMMI", "CAudioReview"})
        for contribution in construction["contributions"]:
            self.assertTrue(contribution["statement"])
            self.assertTrue(contribution["locator"])
            self.assertTrue(contribution["source"]["url"])

    def test_29_capabilities_recombine_without_fixed_input_output_pairs(self):
        case = speech_visual_context()
        case["resources"] = {key: True for key in case["resources"]}
        case["facts"] = {key: True for key in case["facts"]}
        self.assertEqual(signatures(self.make().compose(case)), {
            ("CaptureSpeech", "ReviewText"), ("CaptureKeyboard", "ReviewText"),
        })
        self.assertEqual(signatures(self.make(True).compose(case)), {
            ("CaptureSpeech", "ReviewText"), ("CaptureKeyboard", "ReviewText"),
            ("CaptureSpeech", "ReviewSpeech"), ("CaptureKeyboard", "ReviewSpeech"),
        })

    def test_30_legacy_only_contributions_do_not_become_checked_primary_sources(self):
        composer = self.make(True)
        for contribution in list(composer.graph.subjects(V2.inArticulation, V2.ArtAudioReview)):
            composer.graph.set((contribution, V2.status, Literal("LEGACY_RECORD_ONLY")))
        self.assert_not_ready(composer.compose(keyboard_audio_context()))

    def test_31_criterion_without_documentary_justification_does_not_authorize(self):
        for predicate in (V2.source, V2.locator, V2.justification):
            with self.subTest(predicate=local(predicate)):
                composer = self.make(True)
                composer.graph.remove((V2.CriterionReview, predicate, None))
                self.assert_not_ready(composer.compose(keyboard_audio_context()))

    def test_32_ready_choice_does_not_appropriate_rejected_application_checks(self):
        composer = self.make(True)
        composer.graph.add((V2.BadAudioSupport, RDF.type, V2.GroundingApplication))
        composer.graph.add((V2.BadAudioSupport, V2.capability, V2.ReviewSpeech))
        composer.graph.add((V2.BadAudioSupport, V2.status, Literal("UNCONFIRMED")))
        result = composer.compose(keyboard_audio_context())
        self.assertEqual(result["status"], "COMPOSED")
        check_by_id = {row["id"]: row for row in result["execution_evidence"]}
        for choice in result["choices"]:
            self.assertTrue(choice["check_ids"])
            for check_id in choice["check_ids"]:
                self.assertEqual(check_by_id[check_id]["state"], "PASS")
        self.assertTrue(any(row["state"] == "FAIL" for row in result["execution_evidence"]))

    def test_33_multiple_tasks_are_not_silently_composed(self):
        case = keyboard_audio_context()
        case["task"] = ["TaskCreateReviewedText", "TaskReviewExistingText"]
        self.assert_not_ready(self.make(True).compose(case))

    def test_34_missing_requirements_do_not_become_vacuously_satisfied(self):
        mutations = (
            (V2.CaptureKeyboard, V2.requiresResource),
            (V2.CaptureKeyboard, V2.requiresFact),
            (V2.ReviewSpeech, V2.requiresResource),
            (V2.ReviewSpeech, V2.requiresFact),
            (V2.ProductionThenReview, V2.requiresFact),
        )
        for subject, predicate in mutations:
            with self.subTest(subject=local(subject), predicate=local(predicate)):
                composer = self.make(True)
                composer.graph.remove((subject, predicate, None))
                self.assert_not_ready(composer.compose(keyboard_audio_context()))

    def test_35_ambiguous_articulation_product_cannot_authorize_either_knowledge(self):
        composer = self.make(True)
        composer.graph.add((V2.ArtInput, V2.produces, V2.KAudioReview))
        self.assert_not_ready(composer.compose(keyboard_audio_context()))

    def test_36_non_text_action_cannot_be_rendered_as_instruction(self):
        for value in (True, False, 1, 3.14):
            with self.subTest(value=value):
                composer = self.make(True)
                composer.graph.set((V2.CaptureKeyboard, V2.action, Literal(value)))
                self.assert_not_ready(composer.compose(keyboard_audio_context()))

    def test_37_unusable_source_url_blocks_documentary_grounding(self):
        for source in (V2.SourceMMI, V2.SourceReview):
            for value in (None, "", "http://example.org/unsecured", "file:///private.pdf"):
                with self.subTest(source=local(source), value=value):
                    composer = self.make(True)
                    composer.graph.remove((source, V2.url, None))
                    if value is not None:
                        composer.graph.add((source, V2.url, Literal(value)))
                    self.assert_not_ready(composer.compose(keyboard_audio_context()))

    def test_38_action_uses_pilot_string_contract_labels_may_have_language(self):
        composer = self.make(True)
        composer.graph.set((V2.CaptureKeyboard, V2.action,
                            Literal("Registrar a contribuição no rascunho editável", lang="pt")))
        # rdf:langString is valid RDF text, but outside the pilot's explicit
        # xsd:string action contract. Language-tagged labels remain supported.
        self.assert_not_ready(composer.compose(keyboard_audio_context()))
        composer.graph.set((V2.CaptureKeyboard, V2.action,
                            Literal("Registrar a contribuição no rascunho editável")))
        composer.graph.set((V2.CaptureKeyboard, RDFS.label, Literal("Entrada por teclado", lang="pt")))
        self.assertEqual(composer.compose(keyboard_audio_context())["status"], "COMPOSED")


if __name__ == "__main__":
    unittest.main(verbosity=2)
