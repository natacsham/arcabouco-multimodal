"""Execution projection contracts; fixtures are synthetic, not study evidence."""
from __future__ import annotations

import copy
import json
from pathlib import Path
import sys
import unittest
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "vendor"))
from rdflib import BNode, Graph, Literal, RDF, URIRef
from pyshacl import validate
from semantic_execution import EX, M, project_execution, query_execution, semantic_execution_summary


def fixture():
    base = Graph().parse(ROOT / "ontology/main.ttl", format="turtle")
    for index in (1, 2):
        k, cr, origin, source, excerpt, claim = (M[f"{prefix}{index}"] for prefix in ("K", "CR", "O", "S", "E", "CLM"))
        base.add((k, RDF.type, M.ConhecimentoMultimodalArticulado))
        base.add((cr, RDF.type, M.CriterioDeDecisaoMultimodal))
        base.add((cr, M.possuiOrigem, origin))
        base.add((origin, M.origemEmFonte, source))
        base.add((origin, M.origemSustentadaPorTrecho, excerpt))
        base.add((source, RDF.type, M.Fonte))
        base.add((excerpt, RDF.type, M.TrechoDocumental))
        base.add((excerpt, M.trechoDeFonte, source))
        base.add((claim, M.elegibilidadeOperacional, Literal("DOCUMENTED_OPERATIONAL_CLAIM")))
    base.add((M.ART, RDF.type, M.ArticulacaoDocumentada))
    base.add((M.APP, M.operacaoDaAplicacaoAnalitica, Literal("SYNTHETIC relation of two contributions")))
    base.add((M.APP, M.enunciado, Literal("SYNTHETIC scoped understanding")))
    base.add((M.CONTRIB1, M.contribuicaoDoTrecho, M.E1))
    base.add((M.E1, M.trechoDeFonte, M.S1))

    context = {"id": "synthetic-execution", "confirmed": True, "assertions": [
        {"id": "assertion-p1", "kind": "need", "value": "NEED", "state": "CONFIRMADO",
         "subject_id": "p1", "situation_id": "s1", "source_text": "Synthetic text"}]}
    def grounding(index):
        return {"id": f"G{index}", "knowledge": {"id": f"K{index}"}, "claim_id": f"CLM{index}",
                "criterion": {"id": f"CR{index}"}, "origin_ids": [f"O{index}"],
                "justification": f"Synthetic exact support {index}",
                "sources": [{"id": f"S{index}", "excerpt_id": f"E{index}", "locator": f"Synthetic {index}", "review_status": "SYNTHETIC"}]}
    def step(index, participant="p1", situation="s1"):
        return {"id": f"OP{index}", "participant_id": participant, "situation_id": situation,
                "state": "PASS", "action": "Synthetic action", "function_ids": [f"F{index}"],
                "selected_representation_ids": ["TEXT", "AUDIO"] if index == 1 else ["TEXT"],
                "responsible_participant": {"id": participant}, "groundings": [grounding(index)],
                "input_requirements": [{"representation_id": "DRAFT", "meaning_unit": "same_content"}],
                "output_spec": [{"representation_id": "CHECKED", "meaning_unit": "same_content"}],
                "phase_conditions": [{"id": "condition", "phase": "verification", "state": "PENDING", "label": "Synthetic check after preparation"}],
                "check_ids": ["check1"]}
    steps = [step(1), step(2)]
    steps[0]["groundings"].append({"id": "APP", "analytical_application_id": "APP", "claim_id": "APP",
        "knowledge": {"id": "ART"}, "application_kind": "GROUNDED_ANALYTICAL_APPLICATION",
        "criterion_applications": [{"criterion_id": "CR1", "origin_ids": ["O1"], "justification": "Synthetic synthesis"}],
        "construction": {"id": "ART", "premises": [{"knowledge_id": "K1", "claim_id": "CLM1", "contribution_ids": ["CONTRIB1"]}]}})
    relation = {"id": "REL", "participant_id": "p1", "situation_id": "s1", "state": "PASS",
                "kind": "SEQUENTIAL", "from_capability": "OP1", "to_capability": "OP2",
                "temporal": "PRODUCE_BEFORE_REVIEW", "meaning_unit": "same_content", "groundings": [grounding(1)],
                "information_roles": [{"representation_id": "TEXT", "function_id": "F1", "information_component": "draft",
                    "role": "Reviewable draft", "alone_sufficient_for_goal": True, "claim_ids": ["CLM1"]}]}
    choice = {"id": "plan1", "participant_id": "p1", "situation_id": "s1", "state": "PASS", "steps": steps,
              "relations": [relation], "composition_type": "CONNECTED_PATH", "ready_for_application": True,
              "ready_for_whole_task": False, "covered_functions": [{"id": "F1"}, {"id": "F2"}],
              "limits": ["Synthetic fixture does not establish effectiveness"], "check_ids": ["check1"]}
    result = {"context_id": context["id"], "status": "COMPOSED", "proposal_status": "COMPLETE",
              "choices": [choice], "pending_candidates": [], "partial_segments": [],
              "context_scope": [{"participant_id": "p1", "situation_id": "s1"}, {"participant_id": "p2", "situation_id": "s2"}],
              "capability_evaluations": steps + [step(1, "p2", "s2")], "relation_evaluations": [relation],
              "required_functions": [{"id": "req1", "participant_id": "p1", "situation_id": "s1", "function_id": "F1",
                  "task_ids": ["TASK"], "origin": "SYNTHETIC", "claim_ids": ["CLM1"], "check_ids": ["check1"],
                  "witnesses": [{"need_ids": ["NEED"], "assertion_ids": ["assertion-p1"]}]}],
              "execution_evidence": [{"id": f"check{i}", "state": state, "kind": "SYNTHETIC_CHECK", "stage": "verification",
                  "explanation": "Synthetic execution evidence", "expected": {"value": True},
                  "observed": {"participant_id": "p1", "situation_id": "s1", "value": state == "PASS"}}
                    for i, state in enumerate(("PASS", "PENDING", "FAIL", "NOT_EXECUTED"), 1)],
              "gaps": [{"code": "SYNTHETIC_PENDING", "participant_id": "p2", "situation_id": "s2", "explanation": "Synthetic gap"}]}
    return base, context, result


class SemanticExecutionTests(unittest.TestCase):
    def setUp(self):
        self.base, self.context, self.result = fixture()
        self.graph = project_execution(self.result, self.context, self.base)

    def validate(self, graph=None):
        return validate(self.base + (graph if graph is not None else self.graph),
                        shacl_graph=str(ROOT / "shapes/execution.shacl.ttl"), inference="none")

    def test_deterministic_identity_and_input_immutability(self):
        initial = copy.deepcopy((self.context, self.result))
        base_before = set(self.base)
        duplicate = project_execution(self.result, self.context, self.base)
        self.assertEqual(set(self.graph), set(duplicate))
        self.assertEqual(initial, (self.context, self.result))
        self.assertEqual(base_before, set(self.base))
        self.context["confirmed"] = False
        changed = project_execution(self.result, self.context, self.base)
        self.assertNotEqual(semantic_execution_summary(changed)["execution_iri"], semantic_execution_summary(self.graph)["execution_iri"])

    def test_projection_does_not_assert_observed_result(self):
        self.assertFalse(list(self.graph.subjects(RDF.type, M.Resultado)))
        self.assertFalse(semantic_execution_summary(self.graph)["observed_outcome"])
        self.assertFalse(semantic_execution_summary(self.graph)["case_storage"])

    def test_all_four_check_states_preserved(self):
        actual = {str(self.graph.value(n, EX.state)) for n in self.graph.subjects(RDF.type, EX.Check)}
        self.assertEqual(actual, {"PASS", "PENDING", "FAIL", "NOT_EXECUTED"})

    def test_same_operation_has_distinct_participant_occurrences(self):
        occurrences = list(self.graph.subjects(EX.operation, M.OP1))
        self.assertEqual(len(occurrences), 2)
        self.assertNotEqual(self.graph.value(occurrences[0], EX.participant), self.graph.value(occurrences[1], EX.participant))

    def test_one_configuration_per_actual_representation(self):
        configurations = list(self.graph.subjects(RDF.type, M.ConfiguracaoModalDaDecisao))
        self.assertEqual(len(configurations), 3)
        self.assertTrue(all(len(list(self.graph.objects(cfg, M.configuraModalidade))) == 1 for cfg in configurations))
        self.assertFalse(list(self.graph.triples((None, M.cumpreFuncaoDecisoria, None))),
            "An operation's functions are not attributed indiscriminately to each individual mode.")

    def test_resource_options_are_not_asserted_as_selected_resources(self):
        self.result["choices"][0]["steps"][0]["resources"] = [{"id": "EDITOR-A"}, {"id": "EDITOR-B"}]
        graph = project_execution(self.result, self.context, self.base)
        self.assertTrue(list(graph.triples((None, EX.consideredResource, M["EDITOR-A"]))))
        self.assertFalse(list(graph.triples((None, M.configuraRecurso, M["EDITOR-A"]))))

    def test_criterion_origins_never_cross(self):
        rows = query_execution(self.graph, self.base, ["EXEC-CQ-004"])["EXEC-CQ-004"]["rows"]
        pairs = {(row["criterio"], row["origem"]) for row in rows}
        self.assertEqual(pairs, {(str(M.CR1), str(M.O1)), (str(M.CR2), str(M.O2))})
        self.assertFalse(any(row.get("conhecimento") == str(M.ART) for row in rows))

    def test_analytical_application_is_not_mistyped_as_single_knowledge(self):
        grounding = self.result["choices"][0]["steps"][0]["groundings"][1]
        grounding["knowledge"] = {"id": "APP", "kind": "ANALYTICAL_APPLICATION"}
        grounding["resulting_knowledge_ids"] = ["K1", "K2"]
        graph = project_execution(self.result, self.context, self.base)
        self.assertFalse(list(graph.triples((None, M.conhecimentoDaAplicacao, M.APP))))
        self.assertFalse(list(graph.triples((None, EX.knowledgeReference, M.APP))))
        self.assertTrue(list(graph.triples((None, EX.resultingKnowledge, M.K1))))
        self.assertTrue(list(graph.triples((None, EX.resultingKnowledge, M.K2))))

    def test_analytical_premise_reaches_localized_contribution(self):
        rows = query_execution(self.graph, self.base, ["EXEC-CQ-003"])["EXEC-CQ-003"]["rows"]
        self.assertTrue(rows)
        self.assertTrue(all(row.get("premissa") == str(M.CLM1) and row.get("contribuicao") == str(M.CONTRIB1)
                            and row.get("fonte") == str(M.S1) for row in rows))

    def test_missing_contribution_does_not_expand_to_unrelated_sources(self):
        self.result["choices"][0]["steps"][0]["groundings"][1]["construction"]["premises"][0]["contribution_ids"] = []
        graph = project_execution(self.result, self.context, self.base)
        rows = query_execution(graph, self.base, ["EXEC-CQ-003"])["EXEC-CQ-003"]["rows"]
        self.assertTrue(rows)
        self.assertTrue(all(not row.get("contribuicao") and not row.get("fonte") for row in rows))

    def test_generic_meaning_label_is_not_shared_information_proof(self):
        self.assertFalse(list(self.graph.triples((None, EX.informationUnit, None))))
        self.assertTrue(list(self.graph.triples((None, EX.informationComponent, Literal("same_content")))))

    def test_binding_preserves_proposed_identity_without_observed_meaning(self):
        relation = self.result["relation_evaluations"][0]
        relation["information_binding"] = {"information_unit_id": "synthetic-shared-draft", "participant_id": "p1",
            "situation_id": "s1", "origin": "PROPOSED_SHARED_INFORMATION", "semantic_preservation_observed": False}
        graph = project_execution(self.result, self.context, self.base)
        binding = next(graph.objects(None, EX.hasInformationBinding))
        self.assertEqual(graph.value(binding, EX.bindingOrigin), Literal("PROPOSED_SHARED_INFORMATION"))
        self.assertEqual(graph.value(binding, EX.semanticPreservationObserved), Literal(False))
        self.assertTrue(self.validate(graph)[0])
        graph.set((binding, EX.semanticPreservationObserved, Literal(True)))
        self.assertFalse(self.validate(graph)[0])

    def test_blank_node_labels_do_not_change_base_or_execution_identity(self):
        left, right = Graph(), Graph()
        left.add((M.fixture, M.hasRecord, BNode("parser-one")))
        left.add((BNode("parser-one"), M.enunciado, Literal("Same blank node content")))
        right.add((M.fixture, M.hasRecord, BNode("parser-two")))
        right.add((BNode("parser-two"), M.enunciado, Literal("Same blank node content")))
        projected_left = semantic_execution_summary(project_execution(self.result, self.context, left))
        projected_right = semantic_execution_summary(project_execution(self.result, self.context, right))
        self.assertEqual(projected_left["base_sha256"], projected_right["base_sha256"])
        self.assertEqual(projected_left["execution_iri"], projected_right["execution_iri"])

    def test_large_check_observations_are_explicitly_summarized(self):
        self.result["execution_evidence"][0]["observed"] = {"contracts": [{"large": list(range(1000))} for _ in range(100)]}
        graph = project_execution(self.result, self.context, self.base)
        summaries = list(graph.subjects(EX.summaryOnly, Literal(True)))
        self.assertTrue(summaries)
        self.assertTrue(any(graph.value(n, EX.itemCount) == Literal(100) for n in summaries))
        self.assertLess(len(list(graph.subjects(RDF.type, EX.ObservationValue))), 100)

    def test_temporal_contract_is_distinct_from_functional_relation(self):
        self.result["relation_evaluations"][0]["temporal_contract"] = {"organization": "OUTPUT_THEN_INPUT",
            "verification_required": True, "window_requirement": "Synthetic timing condition"}
        graph = project_execution(self.result, self.context, self.base)
        temporal = next(graph.objects(None, EX.hasTemporalContract))
        relation = next(graph.subjects(EX.hasTemporalContract, temporal))
        self.assertEqual(graph.value(temporal, EX.organization), Literal("OUTPUT_THEN_INPUT"))
        self.assertEqual(graph.value(relation, EX.kind), Literal("SEQUENTIAL"))
        self.assertTrue(self.validate(graph)[0])

    def test_modal_roles_are_queryable_without_json(self):
        roles = list(self.graph.subjects(RDF.type, EX.ModalInformationRole))
        self.assertEqual(len(roles), 1)
        role = roles[0]
        self.assertEqual(self.graph.value(role, EX.informationComponent), Literal("draft"))
        self.assertEqual(self.graph.value(role, EX.representation), M.TEXT)
        self.assertEqual(self.graph.value(role, EX.usesAssertion), M.CLM1)

    def test_competency_queries_are_execution_scoped(self):
        answers = query_execution(self.graph, self.base)
        self.assertEqual(len(answers), 10)
        for key in ("EXEC-CQ-001", "EXEC-CQ-002", "EXEC-CQ-003", "EXEC-CQ-004", "EXEC-CQ-005", "EXEC-CQ-006", "EXEC-CQ-007", "EXEC-CQ-008", "EXEC-CQ-009", "EXEC-CQ-010"):
            self.assertTrue(answers[key]["rows"], key)
        self.assertEqual(len(answers["EXEC-CQ-007"]["rows"]), 4)
        self.assertEqual(len(answers["EXEC-CQ-010"]["rows"]), 1)
        with self.assertRaises(ValueError):
            query_execution(self.graph, self.base, ["CQ-UNKNOWN"])

    def test_full_execution_shapes_pass(self):
        conforms, _, report = self.validate()
        self.assertTrue(conforms, report)

    def test_scope_contamination_is_rejected(self):
        proposal = next(self.graph.subjects(RDF.type, EX.Proposal))
        operation = next(n for n in self.graph.subjects(EX.operation, M.OP1)
                         if self.graph.value(self.graph.value(n, EX.participant), EX.identifier) == Literal("p2"))
        self.graph.add((proposal, EX.hasOperation, operation))
        self.assertFalse(self.validate()[0])

    def test_missing_execution_check_is_rejected(self):
        check = next(self.graph.subjects(RDF.type, EX.Check))
        self.graph.remove((check, RDF.type, EX.Check))
        self.assertFalse(self.validate()[0])

    def test_crossed_source_excerpt_pair_is_rejected(self):
        support = next(self.graph.subjects(EX.excerpt, M.E1))
        self.graph.set((support, EX.source, M.S2))
        self.assertFalse(self.validate()[0])

    def test_other_execution_is_not_queried_as_current(self):
        other_context = copy.deepcopy(self.context)
        other_context["id"] = "other-execution"
        other = project_execution(self.result, other_context, self.base)
        answers = query_execution(self.graph, self.base + other, ["EXEC-CQ-007"])
        self.assertEqual(len(answers["EXEC-CQ-007"]["rows"]), 4)


class RealExecutionProjectionTests(unittest.TestCase):
    """Actual public engine, test-only narratives, no injected context facts."""
    case_evidence = {}

    @classmethod
    def setUpClass(cls):
        from engine import DecisionEngine
        cls.engine = DecisionEngine()
        cls.shapes = Graph().parse(ROOT / "shapes/main.shacl.ttl", format="turtle")
        cls.shapes.parse(ROOT / "shapes/execution.shacl.ttl", format="turtle")
        cls.outputs = {}
        cases = json.loads((ROOT / "tests/fixtures/articulation_transfer_cases.json").read_text(encoding="utf-8"))
        for case in cases:
            cls.engine.clear()
            cls.engine.analyze_narrative(case["narrative"])
            # Explicit synthetic confirmation of this test's decomposition;
            # no resources, abilities or missing facts are silently supplied.
            cls.engine.update_context({"mapping_confirmed": True})
            start = perf_counter()
            result = cls.engine.generate_situated()
            generation_seconds = perf_counter() - start
            graph = cls.engine._last_execution_graph
            answers = query_execution(graph, cls.engine.graph)
            conforms, _, report = validate(cls.engine.graph + graph,
                shacl_graph=cls.shapes, inference="none", allow_warnings=True)
            summary = semantic_execution_summary(graph)
            cls.outputs[case["id"]] = (result, graph, answers, conforms, report)
            cls.case_evidence[case["id"]] = {"execution": summary, "execution_shacl_conforms": bool(conforms),
                "query_row_counts": {key: len(value["rows"]) for key, value in answers.items()},
                "generation_seconds": round(generation_seconds, 3),
                "validation_scope": "FULL_STATIC_AND_EXECUTION_SHAPES_ON_BASE_PLUS_EXECUTION",
                "input_kind": "TEST_NARRATIVE_WITH_EXPLICIT_SYNTHETIC_MAPPING_CONFIRMATION_ONLY"}

    def test_three_public_narratives_project_current_scoped_evidence(self):
        self.assertEqual(set(self.outputs), {"catalogue_sequence", "recorded_content_access", "dictation_review_control"})
        for identifier, (result, graph, answers, _, _) in self.outputs.items():
            with self.subTest(case=identifier):
                summary = semantic_execution_summary(graph)
                self.assertEqual(summary["contract_version"], "MADO_EXECUTION_GRAPH_1")
                self.assertGreater(summary["counts"]["operations"], 0)
                self.assertGreater(summary["counts"]["configurations"], 0)
                self.assertEqual(len(answers), 10)
                self.assertEqual(len(answers["EXEC-CQ-007"]["rows"]), len(result["execution_evidence"]))
                self.assertTrue(answers["EXEC-CQ-004"]["rows"])
                self.assertFalse(list(graph.subjects(RDF.type, M.Resultado)))

    def test_full_execution_shapes_on_real_base_and_all_three_execution_graphs(self):
        for identifier, (_, _, _, conforms, report) in self.outputs.items():
            with self.subTest(case=identifier):
                self.assertTrue(conforms, report)

    def test_current_engine_clear_discards_execution_graph(self):
        self.engine.clear()
        self.assertIsNone(self.engine._last_execution_graph)

    def test_execution_marker_does_not_bypass_shared_configuration_contract(self):
        graph = next(iter(self.outputs.values()))[1]
        candidate = next(graph.subjects(RDF.type, M.ConfiguracaoModalDaDecisao))
        changed = self.engine.graph + graph
        changed.remove((candidate, EX.hasSupport, None))
        conforms, _, _ = validate(changed, shacl_graph=self.shapes, inference="none",
            allow_warnings=True, focus_nodes=[candidate])
        self.assertFalse(conforms, "An execution marker cannot exempt an unfounded configuration from validation.")

    def test_old_configuration_cannot_switch_contract_by_adding_run_marker(self):
        graph = next(iter(self.outputs.values()))[1]
        candidate = next(self.engine.graph.subjects(RDF.type, M.ConfiguracaoModalDaDecisao))
        execution = next(graph.subjects(RDF.type, EX.Execution))
        changed = self.engine.graph + graph
        changed.add((candidate, EX.forExecution, execution))
        conforms, _, _ = validate(changed, shacl_graph=self.shapes, inference="none",
            allow_warnings=True, focus_nodes=[candidate])
        self.assertFalse(conforms, "The new branch requires a full scoped execution contract, not a bypass marker.")


if __name__ == "__main__":
    unittest.main()
