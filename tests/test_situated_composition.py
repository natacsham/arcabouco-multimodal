"""Synthetic execution checks, not human or semantic-effectiveness validation."""
from __future__ import annotations

import copy
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "experimental/v2/tests"))

from experimental.v2.composer import Composer, V2
from rdflib import RDF, Literal, RDFS
from experimental.v2.trajectory import ResearchComposer
from test_trajectory import trajectory_context


def collaborative_unknown_context():
    """Synthetic unfamiliar context using existing tasks, not a stored case."""
    first = trajectory_context()
    first["facts"].update(CanUseSpeech=True, SpeechInputUsable=True, SpeechEffortAcceptable=True,
        SpeechCompatible=True, SpeechFeedbackPerceptible=True, CanUseKeyboard=False,
        CanReviewVisualText=True, CanReviewSpeech=False)
    first["resources"].update(Microphone=True, SpeechRecognition=True, Display=True, Keyboard=False,
                               TextToSpeech=False, AudioOutput=False)
    second = trajectory_context()
    people = [{"id": identifier, "label": label, "facts": item["facts"], "resources": item["resources"],
               "tarefa_ids": [str(V2.TaskCreateReviewedText)]}
              for identifier, label, item in [("p-voice", "Pessoa que registra por voz", first),
                                               ("p-keyboard", "Pessoa que registra por teclado", second)]]
    return {"id": "SYN-NOVEL-COLLAB-908", "label": "Preparação de notas para encontro comunitário", "confirmed": True,
            "participations": people, "situations": [{"id": "draft-notes", "label": "Produção e conferência das notas",
                "task_ids": [str(V2.TaskCreateReviewedText)], "participant_ids": [p["id"] for p in people],
                "actor_ids": [p["id"] for p in people]}]}


def synthetic_catalogue():
    """A deliberately tiny test graph; these are not research-base claims."""
    claim = {"id": "C", "statement": "SYNTHETIC TEST CLAIM", "eligibility": "DOCUMENTED_OPERATIONAL_CLAIM",
             "status": "SUPPORTED_IN_RECORDED_SCOPE", "foundation_status": "DOCUMENTED_IN_RECORDED_SCOPE",
             "function_ids": ["F-A", "F-B"], "support": [{"source_id": "S", "excerpt_id": "E"}]}
    support = {"knowledge_id": "K", "claim_id": "C", "criterion_id": "CR", "origin_ids": ["O"], "justification": "Synthetic exact link"}
    relation = {"id": "R", "kind": "SEQUENTIAL", "scope": "BETWEEN_OPERATIONS", "from_function_ids": ["F-A"],
                "to_function_ids": ["F-B"], "from_representation_ids": ["DRAFT"], "to_representation_ids": ["DRAFT"],
                "meaning_unit": "SAME_CONTENT", "preserves": "The explicitly identified draft", "sufficiency": "REQUIRES_SITUATED_CONFIRMATION",
                "temporal": "SEQUENTIAL", "claim_support": [support]}
    def operation(identifier, function, before, after):
        return {"id": identifier, "active_in_rc4": True, "label": identifier, "action": "DO NOT USE HISTORICAL ACTION",
                "operation_contract": {"id": identifier, "action": "Scoped " + identifier, "function_ids": [function],
                    "transfer_scope": {"allow_new_task_with_functional_witness": True}, "claim_support": [support],
                    "input_requirements": [{"representation_id": before, "meaning_unit": "SAME_CONTENT"}],
                    "output_spec": [{"representation_id": after, "meaning_unit": "SAME_CONTENT"}],
                    "resource_requirements": {}, "relations": [relation] if function == "F-A" else []}}
    return {"knowledge": [{"id": "K", "enunciado": "UNAURHORIZED WHOLE KNOWLEDGE", "fonte_ids": ["S"], "trecho_ids": ["E"], "operation_claims": [claim]}],
            "sources": [{"id": "S", "titulo": "Synthetic fixture", "url": "https://example.org/fixture"}],
            "excerpts": [{"id": "E", "fonte_id": "S", "localizacao_publica": "Synthetic paragraph 1"}],
            "criteria": [{"id": "CR"}], "criterion_origins": [{"id": "O", "criterio_id": "CR"}],
            "context_elements": [{"id": x, "rotulo": x} for x in ["F-A", "F-B", "NEED", "TASK", "RSC"]],
            "functional_matrix": [{"id": "MF", "requisito_ids": ["NEED"], "funcao_ids": ["F-A", "F-B"],
                                   "inference_contract": {"eligibility": "DOCUMENTED_OPERATIONAL_CLAIM", "claim_ids": ["C"]}}],
            "decision_components": [operation("OP-A", "F-A", "CONTENT", "DRAFT"), operation("OP-B", "F-B", "DRAFT", "CHECKED")]}


class SituatedGraphTests(unittest.TestCase):
    def setUp(self):
        self.composer = Composer([])
        self.composer.base = synthetic_catalogue()
        self.context = {"id": "unknown-438", "confirmed": True, "tarefas": ["TASK"], "necessidades": ["NEED"], "facts": {"R:sufficiency": True}}

    def compose(self, context=None):
        return self.composer.compose_context(context or self.context)

    def test_required_functions_precede_selection_and_new_context_recombines(self):
        result = self.compose()
        self.assertEqual(result["status"], "COMPOSED")
        self.assertEqual([s["id"] for s in result["choices"][0]["steps"]], ["OP-A", "OP-B"])
        self.assertEqual({x["origin"] for x in result["required_functions"]}, {"DOCUMENTED_FUNCTIONAL_WITNESS"})
        kinds = [row["kind"] for row in result["execution_evidence"]]
        self.assertLess(kinds.index("REQUIRED_FUNCTION_BEFORE_SELECTION"), kinds.index("OPERATION_TASK_SCOPE"))
        for step in result["choices"][0]["steps"]:
            self.assertEqual(step["action"], "Scoped " + step["id"])
            self.assertTrue(step["function_derivation"])
            self.assertNotIn("UNAURHORIZED", step["groundings"][0]["knowledge"]["label"])

    def test_labels_and_subject_text_never_route_operations(self):
        first = self.compose()
        context = copy.deepcopy(self.context)
        context.update(id="not-in-catalogue", label="Outro domínio", description="Palavras nunca usadas no protótipo")
        second = self.compose(context)
        self.assertEqual([[s["id"] for s in p["steps"]] for p in first["choices"]], [[s["id"] for s in p["steps"]] for p in second["choices"]])

    def test_unknown_relation_is_conditional_false_relation_blocks(self):
        del self.context["facts"]["R:sufficiency"]
        unknown = self.compose()
        self.assertFalse(unknown["choices"])
        self.assertTrue(any(p["covers_all_required_functions"] for p in unknown["pending_candidates"]))
        self.context["facts"]["R:sufficiency"] = False
        blocked = self.compose()
        self.assertFalse(blocked["choices"])
        self.assertFalse(any(p["covers_all_required_functions"] for p in blocked["pending_candidates"]))
        self.assertTrue(blocked["partial_segments"])

    def test_pending_foundation_never_becomes_context_question(self):
        self.composer.base["knowledge"][0]["operation_claims"][0]["foundation_status"] = "PENDING"
        result = self.compose()
        self.assertFalse(result["choices"] + result["pending_candidates"])
        self.assertTrue(result["claim_audit"])
        self.assertFalse(result["facts_to_confirm"])

    def test_same_types_without_registered_edge_do_not_compose(self):
        self.composer.base["decision_components"][0]["operation_contract"]["relations"] = []
        result = self.compose()
        self.assertFalse(result["choices"])
        self.assertTrue(result["partial_segments"])
        self.assertIn("NO_AUTHORIZED_RELATION", {x["code"] for x in result["integration_gaps"]})

    def test_relation_cannot_borrow_a_claim_about_another_function(self):
        claim = copy.deepcopy(self.composer.base["knowledge"][0]["operation_claims"][0])
        claim.update(id="UNRELATED", function_ids=["F-OTHER"])
        self.composer.base["knowledge"][0]["operation_claims"].append(claim)
        relation = self.composer.base["decision_components"][0]["operation_contract"]["relations"][0]
        relation["claim_support"] = [dict(relation["claim_support"][0], claim_id="UNRELATED")]
        result = self.compose()
        self.assertFalse(result["choices"])
        self.assertTrue(any(c["kind"] == "RELATION_FUNCTION_SUPPORT" and c["state"] == "FAIL" for c in result["execution_evidence"]))

    def test_declared_care_relations_check_sufficiency_temporality_and_access(self):
        for kind, valid_sufficiency, wrong_sufficiency in [
                ("COMPLEMENTARITY", "JOINT_REQUIRED", "EACH_SUFFICIENT"),
                ("ALTERNATIVE", "EACH_SUFFICIENT", "JOINT_REQUIRED"),
                ("REDUNDANCY", "INDIVIDUALLY_SUFFICIENT", "JOINT_REQUIRED")]:
            with self.subTest(kind=kind):
                self.composer.base = synthetic_catalogue()
                operation = self.composer.base["decision_components"][0]["operation_contract"]
                relation = operation["relations"][0]
                relation.update(kind=kind, scope="WITHIN_OPERATION", from_function_ids=["F-A"], to_function_ids=["F-A"],
                                from_representation_ids=["CONTENT"], to_representation_ids=["DRAFT"],
                                sufficiency=valid_sufficiency, temporal="WITHIN_WINDOW")
                operation["requires_facts"] = [{"id": "SelectedPresentationsAccessible", "label": "A pessoa consegue acessar as apresentações necessárias nesta relação?"}]
                context = {"id": "care-unknown", "confirmed": True, "tarefas": ["TASK"], "funcoes_requeridas_ids": ["F-A"],
                           "facts": {"SelectedPresentationsAccessible": True, "R:temporal": True}}
                self.assertEqual(self.compose(context)["status"], "COMPOSED")
                relation["sufficiency"] = wrong_sufficiency
                self.assertFalse(self.compose(context)["choices"])
                relation["sufficiency"] = valid_sufficiency
                context["facts"]["R:temporal"] = None
                self.assertTrue(self.compose(context)["pending_candidates"])
                context["facts"].update({"R:temporal": True, "SelectedPresentationsAccessible": False})
                self.assertFalse(self.compose(context)["choices"])

    def test_resource_mention_is_not_availability_and_episodes_do_not_borrow(self):
        self.composer.base["decision_components"][0]["operation_contract"]["resource_requirements"] = {"all": ["RSC"], "capability_check_required": False}
        context = {"id": "group", "confirmed": True, "active_situation_id": "two", "participations": [{"id": "p"}],
            "situations": [{"id": "one", "task_ids": ["TASK"], "need_ids": ["NEED"], "participant_ids": ["p"],
                            "resource_states": [{"resource_id": "RSC", "state": "DISPONIVEL_CONFIRMADO"}]},
                           {"id": "two", "task_ids": ["TASK"], "need_ids": ["NEED"], "participant_ids": ["p"], "resource_ids": ["RSC"]}]}
        result = self.compose(context)
        self.assertEqual(result["deferred_situation_ids"], ["one"])
        self.assertTrue(all(x["situation_id"] == "two" for x in result["required_functions"]))
        self.assertTrue(any(x["id"] == "RSC" for x in result["resources_to_confirm"]))
        self.assertFalse(result["choices"])

    def test_scoped_unknown_answer_not_repeated_and_other_person_not_authorized(self):
        self.context.pop("facts")
        self.context["situated_facts"] = [{"participant_id": self.context["id"], "situation_id": "situation-default", "fact_id": "R:sufficiency", "value": None}]
        result = self.compose()
        self.assertFalse(any(x["id"] == "R:sufficiency" for x in result["facts_to_confirm"]))
        self.assertTrue(any(x.get("answered_unknown") for x in result["other_condition_diagnostics"]))
        self.context["situated_facts"][0].update(participant_id="another-person", value=True)
        result = self.compose()
        self.assertFalse(result["choices"])

    def test_malformed_fact_fails_closed(self):
        self.context["situated_facts"] = [None]
        result = self.compose()
        self.assertTrue(result["input_issues"])
        self.assertFalse(result["choices"])

    def test_bounded_search_discloses_interruption(self):
        with patch("experimental.v2.composer.MAX_COMBINATIONS_PER_PHASE", 1):
            result = self.compose()
        self.assertEqual(result["search"]["complete"]["examined"], 1)
        self.assertTrue(result["search"]["complete"]["truncated"])
        self.assertIn("SEARCH_LIMIT_REACHED", {x["code"] for x in result["gaps"]})

    def test_unknown_requirement_is_not_silently_satisfied(self):
        context = {"id": "unknown-f", "confirmed": True, "participations": [{"id": "p"}],
                   "situations": [{"id": "s", "participant_ids": ["p"], "task_ids": ["TASK"], "function_ids": ["F-A", "UNKNOWN"]}]}
        result = self.compose(context)
        self.assertFalse(result["choices"])
        self.assertTrue(result["partial_segments"])
        self.assertIn("UNKNOWN", {f["id"] for p in result["partial_segments"] for f in p["missing_functions"]})

    def test_context_level_need_is_not_assigned_to_every_person(self):
        context = {"id": "some", "confirmed": True, "participations": [{"id": "a"}, {"id": "b"}],
                   "situations": [{"id": "s", "participant_ids": ["a", "b"], "task_ids": ["TASK"]}],
                   "assertions": [{"id": "reported-some", "subject_id": "some", "situation_id": "s", "kind": "need", "value": "NEED", "state": "CONFIRMADO"}]}
        self.assertFalse(self.compose(context)["required_functions"])
        context["assertions"] = []
        context["situations"][0]["need_ids"] = ["NEED"]
        self.assertFalse(self.compose(context)["required_functions"])

    def test_deferred_requirement_does_not_block_active_scope(self):
        context = {"id": "priority", "confirmed": True, "active_situation_id": "now", "participations": [{"id": "a"}, {"id": "b"}],
                   "situations": [{"id": "now", "participant_ids": ["a"], "task_ids": ["TASK"], "function_ids": ["F-A"]},
                                  {"id": "later", "participant_ids": ["a", "b"], "task_ids": ["TASK"], "function_ids": ["F-B"]}]}
        result = self.compose(context)
        self.assertEqual(result["status"], "COMPOSED")
        self.assertEqual(result["deferred_situation_ids"], ["later"])

    def test_explicit_inability_overrides_general_operated_resource(self):
        self.composer.base["decision_components"][0]["operation_contract"]["resource_requirements"] = {"all": ["RSC"], "capability_check_required": True}
        context = {"id": "operability", "confirmed": True, "participations": [{"id": "p", "recurso_operado_ids": ["RSC"]}],
                   "situations": [{"id": "s", "participant_ids": ["p"], "task_ids": ["TASK"], "function_ids": ["F-A"],
                                  "resource_states": [{"resource_id": "RSC", "state": "DISPONIVEL_CONFIRMADO"}]}],
                   "situated_facts": [{"participant_id": "p", "situation_id": "s", "fact_id": "OP-A:operability", "value": False}]}
        result = self.compose(context)
        self.assertFalse(result["choices"])
        self.assertTrue(any(c["id"] == "OP-A:operability" for c in result["unavailable_conditions"]))

    def test_impeded_resource_cannot_be_enabled_by_conflicting_generic_fact(self):
        self.composer.base["decision_components"][0]["operation_contract"]["resource_requirements"] = {"all": ["RSC"], "capability_check_required": False}
        context = {"id": "resource-conflict", "confirmed": True, "tarefas": ["TASK"], "funcoes_requeridas_ids": ["F-A"],
                   "recursos_impedidos": ["RSC"], "facts": {"RSC": True}}
        result = self.compose(context)
        self.assertFalse(result["choices"])
        self.assertTrue(any(row["kind"] == "RESOURCE_STATE_CONSISTENCY" and row["state"] == "FAIL" for row in result["execution_evidence"]))

    def test_returned_claims_do_not_expose_mutable_shared_catalogue(self):
        before = copy.deepcopy(self.composer.base)
        result = self.compose()
        result["choices"][0]["steps"][0]["groundings"][0]["claim"]["statement"] = "MUTATED RESULT ONLY"
        self.assertEqual(self.composer.base, before)

    def test_direct_normative_pair_must_use_its_actual_excerpt(self):
        self.composer.base["criterion_origins"][0]["trecho_id"] = "DIFFERENT-NORMATIVE-CLAUSE"
        self.composer.base["decision_components"][0]["operation_contract"]["claim_support"][0]["semantic_pair_review"] = {
            "status": "CONFERIDO_NO_REGISTRO", "scope": "DIRECT_NORMATIVE_CLAUSE"}
        result = self.compose()
        self.assertFalse(result["choices"])
        self.assertTrue(any(row["reason"] == "DIRECT_NORMATIVE_CLAIM_ORIGIN_MISMATCH" for row in result["claim_audit"]))

    def test_rdf_task_does_not_require_recipient_to_perform_actor_actions(self):
        graph = self.composer.graph
        graph.add((V2.TaskSynthetic, RDF.type, V2.Task))
        graph.add((V2.TaskSynthetic, V2.requiresFunction, V2.FunctionSynthetic))
        graph.add((V2.FunctionSynthetic, RDF.type, V2.Function))
        graph.add((V2.FunctionSynthetic, RDFS.label, Literal("Synthetic actor function")))
        context = {"id": "roles", "confirmed": True, "participations": [{"id": "actor"}, {"id": "recipient"}],
                   "situations": [{"id": "s", "task_ids": [str(V2.TaskSynthetic)], "participant_ids": ["actor", "recipient"],
                                  "actor_ids": ["actor"], "recipient_ids": ["recipient"]}]}
        result = self.compose(context)
        self.assertEqual({r["participant_id"] for r in result["required_functions"]}, {"actor"})


class ExistingResearchContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.composer = ResearchComposer(legacy_projection=False)

    def test_existing_rdf_recombines_in_same_general_engine(self):
        context = trajectory_context()
        context["id"] = "SYN-NEW-UNREGISTERED-908"
        with patch.object(self.composer, "compose", side_effect=AssertionError("Legacy search must not run")):
            result = self.composer.compose_context(context)
        self.assertEqual(result["composition_kind"], "SITUATED_OPERATION_GRAPH")
        self.assertEqual(result["status"], "COMPOSED")
        choice = result["choices"][0]
        self.assertEqual([s["id"] for s in choice["steps"]], [str(V2.CaptureKeyboard), str(V2.ReviewSpeech)])
        self.assertEqual(choice["relations"][0]["id"], str(V2.ProductionThenReview))
        self.assertTrue(all(s["groundings"][0]["sources"][0]["url"] for s in choice["steps"]))
        ids = {row["id"] for row in result["execution_evidence"]}
        self.assertTrue(set(choice["check_ids"]) <= ids)
        self.assertTrue(all(row["origin"] == "REGISTERED_TASK_FUNCTION_REQUIREMENT" for row in result["required_functions"]))

    def test_meaning_verification_perturbation_changes_actual_choice(self):
        context = trajectory_context()
        context["facts"]["CanVerifyMeaning"] = None
        unknown = self.composer.compose_context(context)
        self.assertFalse(unknown["choices"])
        self.assertTrue(unknown["pending_candidates"])
        context["facts"]["CanVerifyMeaning"] = False
        blocked = self.composer.compose_context(context)
        self.assertFalse(blocked["choices"])
        self.assertTrue(any(s["id"] == str(V2.CaptureKeyboard) for p in blocked["partial_segments"] for s in p["steps"]))
        self.assertFalse(any(s["id"] == str(V2.ReviewSpeech) for p in blocked["partial_segments"] for s in p["steps"]))

    def test_two_people_recombine_without_borrowing_abilities(self):
        context = collaborative_unknown_context()
        result = self.composer.compose_context(context)
        self.assertEqual(result["status"], "COMPOSED")
        selected = {p["participant_id"]: [s["id"] for s in p["steps"]] for p in result["choices"]}
        self.assertEqual(selected["p-voice"], [str(V2.CaptureSpeech), str(V2.ReviewText)])
        self.assertEqual(selected["p-keyboard"], [str(V2.CaptureKeyboard), str(V2.ReviewSpeech)])
        context["participations"][1]["facts"]["AudioUsable"] = False
        blocked = self.composer.compose_context(context)
        self.assertFalse(blocked["choices"])
        preserved = [p for p in blocked["partial_segments"] if p["participant_id"] == "p-voice"]
        self.assertTrue(any(p.get("covers_participant_situation") and len(p["steps"]) == 2 for p in preserved))
        self.assertFalse(any(s["id"] == str(V2.ReviewSpeech) for p in blocked["partial_segments"]
                             if p["participant_id"] == "p-keyboard" for s in p["steps"]))

    def test_no_implicit_main_function_equivalence(self):
        context = {"id": "unmapped-main", "confirmed": True, "tarefas": ["TASK-UNREGISTERED"], "funcoes_requeridas_ids": ["FUN-EXPRESSAR-CONHECIMENTO"]}
        result = self.composer.compose_context(context)
        self.assertFalse(any(x["id"].startswith(str(V2)) for x in result["capability_evaluations"]))

    def test_attributed_main_actions_refine_only_with_same_draft_condition(self):
        context = collaborative_unknown_context()
        tasks = ["TAR-PRODUZIR-CONTEUDO-MULTIMODAL", "TAR-REVISAR-E-CONFIRMAR"]
        context["situations"][0]["task_ids"] = tasks
        for person in context["participations"]:
            person["tarefa_ids"] = tasks
            person["facts"]["SameEditableTextDraft"] = True
        result = self.composer.compose_context(context)
        self.assertEqual(result["status"], "COMPOSED")
        self.assertTrue(all(f["origin"] == "REGISTERED_TASK_REFINEMENT" for f in result["required_functions"]))
        context["participations"][1]["facts"]["SameEditableTextDraft"] = None
        pending = self.composer.compose_context(context)
        self.assertFalse(pending["choices"])
        self.assertTrue(any(c["id"] == "SameEditableTextDraft" and c["participant_id"] == "p-keyboard" for c in pending["facts_to_confirm"]))
        context["participations"][1]["tarefa_ids"] = ["TAR-COMUNICAR-CONTRIBUICAO"]
        context["situations"][0]["actor_ids"] = ["p-voice"]
        unrelated = self.composer.compose_context(context)
        self.assertFalse(any(c["participant_id"] == "p-keyboard" for c in unrelated["capability_evaluations"]))

    def test_catalogue_contracts_are_all_visible_but_not_all_recommended(self):
        active = [c for c in self.composer.base["decision_components"] if c.get("active_in_rc4")]
        self.assertEqual(len(active), 11)
        context = {"id": "unknown-needs", "confirmed": True, "tarefas": ["TASK-UNREGISTERED"], "necessidades": ["NEED-NOT-IN-BASE"]}
        result = self.composer.compose_context(context)
        self.assertEqual(result["required_functions"], [])
        self.assertEqual(result["capability_evaluations"], [])


if __name__ == "__main__":
    unittest.main()
