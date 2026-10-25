"""Synthetic algorithm contracts, not new scenario rules or research evidence.

These tests exercise existing schema fields with a deliberately tiny catalogue.
They are not deployed in the browser and add no claim to the research base.
"""
from __future__ import annotations

import copy
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

from experimental.v2.composer import Composer, _SituatedRun
from test_situated_composition import synthetic_catalogue


def offered(result):
    return [proposal for field in ("choices", "pending_candidates", "partial_segments")
            for proposal in result.get(field, [])]


def operation_ids(proposal):
    return [step["id"] for step in proposal["steps"]]


class StructuralCompositionTests(unittest.TestCase):
    def setUp(self):
        self.composer = Composer([])
        self.composer.base = synthetic_catalogue()
        self.context = {
            "id": "synthetic-functional-contract",
            "confirmed": True,
            "tarefas": ["UNREGISTERED-TASK"],
            "funcoes_requeridas_ids": ["F-B"],
            "facts": {"R:sufficiency": True},
        }

    def compose(self):
        return self.composer.compose_context(copy.deepcopy(self.context))

    def require_prepared_input(self):
        operation = self.composer.base["decision_components"][1]["operation_contract"]
        operation["transfer_scope"].update(
            requires_existing_representation=True,
            input_context_witness={"any": [{"field": "modalidades", "ids": ["DRAFT"]}]},
        )

    def test_functional_transfer_does_not_require_historical_task_name(self):
        contract = self.composer.base["decision_components"][1]["operation_contract"]
        contract["transfer_scope"]["task_ids"] = ["HISTORICAL-TASK"]
        result = self.compose()
        self.assertTrue(any(operation_ids(plan) == ["OP-B"] for plan in result["choices"]),
                        "A published functional-transfer permission must work outside the source task.")
        self.assertEqual({row["function_id"] for row in result["required_functions"]}, {"F-B"})

    def test_information_identity_is_required_between_producer_and_consumer(self):
        self.require_prepared_input()
        initial = self.compose()
        evaluations = {row["id"]: row for row in initial["capability_evaluations"]}
        self.context["information_bindings"] = [
            {"operation_id": identifier, "participant_id": evaluations[identifier]["participant_id"],
             "situation_id": evaluations[identifier]["situation_id"], "information_unit_id": "same-draft"}
            for identifier in ("OP-A", "OP-B")]
        linked = self.compose()
        self.assertTrue(any(operation_ids(plan) == ["OP-A", "OP-B"] for plan in offered(linked)))
        self.context["information_bindings"][1]["information_unit_id"] = "another-draft"
        broken = self.compose()
        self.assertFalse(any(operation_ids(plan) == ["OP-A", "OP-B"] for plan in offered(broken)))
        self.assertTrue(any(check["kind"] == "INFORMATION_IDENTITY" and check["state"] == "FAIL"
                            for check in broken["execution_evidence"]))

    def test_explicitly_task_bound_operation_remains_outside_new_task(self):
        contract = self.composer.base["decision_components"][1]["operation_contract"]
        contract["transfer_scope"].update(task_ids=["HISTORICAL-TASK"],
                                         allow_new_task_with_functional_witness=False)
        result = self.compose()
        self.assertFalse(any("OP-B" in operation_ids(plan) for plan in offered(result)))

    def test_authorized_producer_can_enable_a_required_consumer(self):
        self.require_prepared_input()
        result = self.compose()
        connected = [plan for plan in offered(result) if operation_ids(plan) == ["OP-A", "OP-B"]]
        self.assertTrue(connected,
                        "An authorized producer must not be discarded only because its function is instrumental.")
        self.assertEqual({row["function_id"] for row in result["required_functions"]}, {"F-B"},
                         "Producer discovery must not convert an offered function into a user requirement.")
        self.assertTrue(any(plan["covers_all_required_functions"] for plan in connected))
        self.assertTrue(all(any(relation["id"] == "R" and relation["from_capability"] == "OP-A"
                                and relation["to_capability"] == "OP-B" for relation in plan["relations"])
                            for plan in connected))
        self.assertFalse(any(operation_ids(plan) == ["OP-B"] for plan in result["choices"]),
                         "Absent draft is not silently available to a standalone consumer.")

    def test_bound_input_does_not_remain_a_question_or_missing_function(self):
        self.require_prepared_input()
        result = self.compose()
        self.assertTrue(any(operation_ids(plan) == ["OP-A", "OP-B"] for plan in result["choices"]))
        self.assertFalse(any(row["id"] == "OP-B:input_available" for row in result["facts_to_confirm"]),
                         "A supported path that prepares its own input does not ask for it as existing.")
        self.assertFalse(any(row["function"]["id"] == "F-B" for row in result["missing_functions"]),
                         "Coverage must consider the selected producer-consumer path.")

    def test_explicitly_absent_input_can_be_prepared_without_being_declared_present(self):
        self.require_prepared_input()
        self.context["facts"]["OP-B:input_available"] = False
        result = self.compose()
        self.assertTrue(any(operation_ids(plan) == ["OP-A", "OP-B"] for plan in result["choices"]))
        self.assertFalse(any(operation_ids(plan) == ["OP-B"] for plan in result["choices"]))
        self.assertIs(self.context["facts"]["OP-B:input_available"], False,
                      "Proposed preparation must not overwrite the reported absence.")

    def test_removing_authorization_removes_only_the_connected_path(self):
        self.require_prepared_input()
        self.composer.base["decision_components"][0]["operation_contract"]["relations"] = []
        result = self.compose()
        self.assertFalse(any(operation_ids(plan) == ["OP-A", "OP-B"] for plan in offered(result)))
        self.assertTrue(any(operation_ids(plan) == ["OP-B"] for plan in result["pending_candidates"]),
                        "The consumer remains conditional on an externally supplied input.")

    def test_equal_representation_with_different_information_cannot_supply_input(self):
        self.require_prepared_input()
        self.composer.base["decision_components"][0]["operation_contract"]["output_spec"][0]["meaning_unit"] = "OTHER_CONTENT"
        result = self.compose()
        self.assertFalse(any(operation_ids(plan) == ["OP-A", "OP-B"] for plan in offered(result)),
                         "Matching DRAFT types do not establish that the same information is being reviewed.")

    def test_known_input_does_not_add_an_unnecessary_producer(self):
        self.require_prepared_input()
        self.context["facts"]["OP-B:input_available"] = True
        result = self.compose()
        self.assertTrue(any(operation_ids(plan) == ["OP-B"] for plan in result["choices"]))
        self.assertFalse(any("OP-A" in operation_ids(plan) for plan in result["choices"]),
                         "More operations do not imply a better recommendation when the input is available.")

    def test_failed_producer_cannot_make_consumer_input_available(self):
        self.require_prepared_input()
        producer = self.composer.base["decision_components"][0]["operation_contract"]
        producer["requires_facts"] = [{"id": "CanProduce", "label": "Synthetic ability to prepare this input"}]
        self.context["facts"]["CanProduce"] = False
        result = self.compose()
        self.assertFalse(any("OP-A" in operation_ids(plan) for plan in offered(result)))
        self.assertFalse(any(operation_ids(plan) == ["OP-B"] for plan in result["choices"]))
        self.assertTrue(any(operation_ids(plan) == ["OP-B"] for plan in result["pending_candidates"]))

    def test_pending_producer_preserves_the_conditional_dependency(self):
        self.require_prepared_input()
        producer = self.composer.base["decision_components"][0]["operation_contract"]
        producer["requires_facts"] = [{"id": "CanProduce", "label": "Synthetic ability to prepare this input"}]
        result = self.compose()
        self.assertTrue(any(operation_ids(plan) == ["OP-A", "OP-B"] for plan in result["pending_candidates"]))
        self.assertFalse(any(operation_ids(plan) == ["OP-A", "OP-B"] for plan in result["choices"]),
                         "A possible producer does not make the whole path ready for use.")

    def test_failed_information_handoff_blocks_the_dependency(self):
        self.require_prepared_input()
        self.context["facts"]["R:sufficiency"] = False
        result = self.compose()
        self.assertFalse(any(operation_ids(plan) == ["OP-A", "OP-B"] for plan in offered(result)))
        self.assertTrue(any(operation_ids(plan) == ["OP-B"] for plan in result["pending_candidates"]))

    def test_satisfied_path_is_not_hidden_by_pending_shortcut(self):
        """A->C->B is usable; unknown A->B is an optional, different path."""
        base = self.composer.base
        base["knowledge"][0]["operation_claims"][0]["function_ids"].append("F-C")
        base["context_elements"].append({"id": "F-C", "rotulo": "Synthetic intermediate function"})
        a = base["decision_components"][0]["operation_contract"]
        c = copy.deepcopy(base["decision_components"][0])
        c.update(id="OP-C", label="OP-C")
        c["operation_contract"].update(
            id="OP-C", action="Synthetic intermediate action", function_ids=["F-C"],
            input_requirements=[{"representation_id": "DRAFT", "meaning_unit": "SAME_CONTENT"}],
        )
        a_to_c = copy.deepcopy(a["relations"][0])
        a_to_c.update(id="R-AC", to_function_ids=["F-C"])
        c_to_b = copy.deepcopy(a["relations"][0])
        c_to_b.update(id="R-CB", from_function_ids=["F-C"])
        a["relations"].append(a_to_c)
        c["operation_contract"]["relations"] = [c_to_b]
        base["decision_components"].append(c)
        self.context["funcoes_requeridas_ids"] = ["F-A", "F-B", "F-C"]
        self.context["facts"] = {"R:sufficiency": None, "R-AC:sufficiency": True,
                                  "R-CB:sufficiency": True}
        result = self.compose()
        expected = [plan for plan in result["choices"] if operation_ids(plan) == ["OP-A", "OP-C", "OP-B"]]
        self.assertTrue(expected, "A pending shortcut cannot hide a fully checked authorized path.")
        self.assertTrue(any({relation["id"] for relation in plan["relations"]} == {"R-AC", "R-CB"}
                            for plan in expected),
                        "Only the selected relations may justify and order this proposal.")

    def test_known_access_variant_without_input_does_not_hide_preparable_alternative(self):
        """Alternative routes have different unresolved conditions, not a total ranking."""
        self.require_prepared_input()
        consumer = self.composer.base["decision_components"][1]["operation_contract"]
        consumer["operation_variants"] = [
            {"id": "OP-B-OTHER-INPUT", "requires_facts": [],
             "input_requirements": [{"representation_id": "UNAVAILABLE-EXTERNAL-INPUT",
                                      "meaning_unit": "SAME_CONTENT"}]},
            {"id": "OP-B-PREPARABLE", "requires_facts": [
                {"id": "CanUseAlternative", "label": "Synthetic unknown access condition"}],
             "input_requirements": [{"representation_id": "DRAFT", "meaning_unit": "SAME_CONTENT"}]},
        ]
        result = self.compose()
        self.assertTrue(any(operation_ids(plan) == ["OP-A", "OP-B-PREPARABLE"]
                            for plan in result["pending_candidates"]),
                        "Access certainty cannot discard a route whose different input can actually be prepared.")
        self.assertFalse(any(operation_ids(plan) == ["OP-B-OTHER-INPUT"] for plan in result["choices"]),
                         "Known access does not establish availability of the required input.")


class AnalyticalDependencyExecutionTests(unittest.TestCase):
    """Counterfactual mutations of existing records, never new base assertions."""
    CHILD = "APP-ART-TRF-04-ORGANIZAR-RETOMAR"
    PARENT = "APP-ART-TRF-04-DESCREVER-ORGANIZAR"
    RELATION = "REL-ART-TRF-04-DESCREVER-ORGANIZAR"

    def setUp(self):
        self.base = json.loads((ROOT / "data/knowledge-base.json").read_text(encoding="utf-8"))
        self.apps = {app["id"]: app for art in self.base["articulations"]
                     for app in art.get("operational_applications", [])}
        self.apps[self.PARENT]["depends_on_application_ids"] = [self.CHILD]
        self.unit = {"participant_id": "synthetic-person", "situation_id": "synthetic-situation"}

    def run_object(self, context=None):
        composer = Composer([])
        composer.base = self.base
        return _SituatedRun(composer, context or {"id": "synthetic-dependency-check"})

    def authorize_parent(self):
        return self.run_object().analytical_groundings([self.PARENT], self.unit, self.RELATION,
                                                       relation=True)

    def test_prior_synthesis_can_be_a_premise_without_authorizing_final_target(self):
        self.assertNotIn(self.RELATION, self.apps[self.CHILD]["authorized_relation_ids"])
        accepted, rejected = self.authorize_parent()
        self.assertFalse(rejected)
        self.assertEqual([row["id"] for row in accepted], [self.PARENT])
        self.assertEqual([row["id"] for row in accepted[0]["dependencies"]], [self.CHILD])
        self.assertEqual(accepted[0]["dependencies"][0]["use"], "SYNTHESIS_PREMISE_ONLY")
        self.assertEqual(accepted[0]["use"], "AUTHORIZED_TARGET")

    def test_child_does_not_independently_authorize_parent_target(self):
        accepted, rejected = self.run_object().analytical_groundings(
            [self.CHILD], self.unit, self.RELATION, relation=True)
        self.assertFalse(accepted)
        self.assertEqual(rejected[0]["reason"], "ANALYTICAL_APPLICATION_TARGET_MISMATCH")

    def test_removing_prior_synthesis_blocks_dependent_authorization(self):
        for art in self.base["articulations"]:
            art["operational_applications"] = [app for app in art.get("operational_applications", [])
                                               if app["id"] != self.CHILD]
        accepted, rejected = self.authorize_parent()
        self.assertFalse(accepted)
        self.assertEqual(rejected[0]["reason"], "ANALYTICAL_DEPENDENCY_FAILED")

    def test_premise_without_delimited_scope_cannot_be_reused(self):
        for field in ("authorized_operation_ids", "authorized_relation_ids", "authorized_requirement_ids"):
            self.apps[self.CHILD][field] = []
        accepted, rejected = self.authorize_parent()
        self.assertFalse(accepted)
        self.assertEqual(rejected[0]["reason"], "ANALYTICAL_DEPENDENCY_FAILED")

    def test_circular_syntheses_cannot_authorize_each_other(self):
        self.apps[self.CHILD]["depends_on_application_ids"] = [self.PARENT]
        accepted, rejected = self.authorize_parent()
        self.assertFalse(accepted)
        self.assertEqual(rejected[0]["reason"], "ANALYTICAL_DEPENDENCY_FAILED")

    def test_retrieval_requirement_depends_on_its_localized_contribution(self):
        context = {"id": "synthetic-explicit-needs", "confirmed": True,
                   "tarefas": ["UNREGISTERED-TASK"],
                   "necessidades": ["NEC-FUNCAO-EXPLICITA-POR-MODALIDADE",
                                     "NEC-PRESERVAR-CONTEUDO-PARA-REVISAO"]}
        original = self.run_object(context).run()
        requirements = {row["function_id"]: row for row in original["required_functions"]}
        self.assertIn("FUN-ORGANIZAR-CONTEUDO", requirements)
        self.assertIn("FUN-MANTER-INFORMACAO-RECUPERAVEL", requirements)
        self.assertIn(self.CHILD, requirements["FUN-MANTER-INFORMACAO-RECUPERAVEL"]["claim_ids"])
        self.base["contributions"] = [row for row in self.base["contributions"]
                                      if row["id"] != "C-K38-MMI-NAV"]
        changed = self.run_object(context).run()
        remaining = {row["function_id"] for row in changed["required_functions"]}
        self.assertIn("FUN-ORGANIZAR-CONTEUDO", remaining,
                      "Removing the retrieval premise must not erase independent documentary organization.")
        self.assertNotIn("FUN-MANTER-INFORMACAO-RECUPERAVEL", remaining)
        self.assertTrue(any(row.get("id") == self.CHILD and row["use"] == "AUDIT_ONLY"
                            for row in changed["claim_audit"]))


class ExistingKnowledgeCompositionTests(unittest.TestCase):
    """Held-out structured combination of existing concepts, not a ready answer."""
    RELATION = "REL-ART-TRF-04-DESCREVER-ORGANIZAR"
    DESCRIPTION = "OP-PAD-REPRESENTACAO-VISUAL-EXPLICADA-TEXT_VISUAL"
    ORGANIZATION = "OP-PAD-ORGANIZAR-CONTEUDO-PERSISTENTE"

    def setUp(self):
        self.composer = Composer([])
        self.composer.base = json.loads((ROOT / "data/knowledge-base.json").read_text(encoding="utf-8"))
        self.context = {
            "id": "synthetic-image-and-sequence", "confirmed": True,
            "participations": [{"id": "recipient", "papel_id": "PAPEL-PESSOA-APOIADA",
                                "facts": {"CanReadText": True}}],
            "tarefas": ["TASK-UNREGISTERED"],
            "necessidades": ["NEC-FUNCAO-EXPLICITA-POR-MODALIDADE",
                             "NEC-PRESERVAR-CONTEUDO-PARA-REVISAO",
                             "NEC-ALTERNATIVA-FUNCIONAL-EQUIVALENTE"],
            "modalidades_disponiveis": ["MOD-IMAGEM", "MOD-TEXTO"],
            "recursos_digitais": ["RED-IMAGEM-DIGITAL"],
            "recursos_disponiveis": ["REC-EDITOR-MULTIMIDIA"],
        }

    def compose(self):
        return self.composer.compose_context(copy.deepcopy(self.context))

    def test_existing_authorized_synthesis_connects_description_and_organization(self):
        result = self.compose()
        connected = [plan for plan in offered(result)
                     if operation_ids(plan) == [self.DESCRIPTION, self.ORGANIZATION]
                     and plan["composition_type"] == "CONNECTED_PATH"]
        self.assertTrue(connected)
        self.assertTrue(any(plan["covers_all_required_functions"] for plan in connected))
        relation = next(row for row in connected[0]["relations"] if row["id"] == self.RELATION)
        self.assertEqual(relation["kind"], "SEQUENTIAL")
        self.assertEqual(relation["meaning_unit"], "INFORMACAO_ESSENCIAL_DA_TAREFA")
        self.assertIn("APP-ART-TRF-04-DESCREVER-ORGANIZAR",
                      {ground["analytical_application_id"] for ground in relation["groundings"]})
        self.assertTrue(relation["groundings"][0]["construction"]["contributions"])
        self.assertFalse(any(plan["ready_for_whole_task"] for plan in connected),
                         "Formal coverage does not verify the prepared content or the whole task.")

    def test_removing_relation_preserves_actions_but_not_invented_sequence(self):
        for component in self.composer.base["decision_components"]:
            contract = component.get("operation_contract", {})
            contract["relations"] = [row for row in contract.get("relations", [])
                                     if row["id"] != self.RELATION]
        result = self.compose()
        self.assertFalse(any(row["id"] == self.RELATION for plan in offered(result)
                             for row in plan["relations"]))
        self.assertFalse(any(operation_ids(plan) == [self.DESCRIPTION, self.ORGANIZATION]
                             and plan["composition_type"] == "CONNECTED_PATH" for plan in offered(result)))
        available = {step["id"] for plan in offered(result) for step in plan["steps"]}
        self.assertIn(self.DESCRIPTION, available)
        self.assertIn(self.ORGANIZATION, available)

    def test_removing_description_contribution_preserves_independent_organization(self):
        self.composer.base["contributions"] = [row for row in self.composer.base["contributions"]
                                               if row["id"] != "C-K38-01"]
        result = self.compose()
        available = {step["id"] for plan in offered(result) for step in plan["steps"]}
        self.assertNotIn(self.DESCRIPTION, available)
        self.assertIn(self.ORGANIZATION, available)
        self.assertFalse(any(row["id"] == self.RELATION for plan in offered(result)
                             for row in plan["relations"]))

    def test_removing_visual_content_does_not_remove_unrelated_retrieval_support(self):
        self.context["modalidades_disponiveis"] = ["MOD-TEXTO"]
        self.context["recursos_digitais"] = []
        result = self.compose()
        available = {step["id"] for plan in offered(result) for step in plan["steps"]}
        self.assertNotIn(self.DESCRIPTION, available)
        self.assertIn(self.ORGANIZATION, available)


if __name__ == "__main__":
    unittest.main()
