"""Synthetic evidence-contract tests; not a human evaluation or new knowledge."""

import copy
import hashlib
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from engine import DecisionEngine, MADO
from execution_trace import ExecutionEvidence, build_explanation
from rdflib.namespace import SKOS


class ExecutionEvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = e = DecisionEngine()
        cls.before = hashlib.sha256((ROOT / "data/knowledge-base.json").read_bytes()).hexdigest()
        e.update_context({"mapping_confirmed": True, "transfer_confirmed": True})
        cls.main = e.generate()
        cls.main_context = copy.deepcopy(e.current["context"])

        # Existing concepts, new conjunction; no pattern, rule or text is added to the base.
        left = e.contexts["CTX-DEMO-WEB-LEITOR-TELA"]
        right = e.contexts["CTX-DEMO-COMUNICACAO-MULTIFORMATO"]
        payload = {field: list(dict.fromkeys(left.get(field, []) + right.get(field, []))) for field in e.context_fields}
        payload["recursos_propostos"] = [v for v in payload["recursos_propostos"] if v not in payload["recursos_disponiveis"]]
        roles = {}
        for row in e.participations:
            if row.get("contexto_id") in {left["id"], right["id"]}:
                target = roles.setdefault(row["papel_id"], {"papel_id": row["papel_id"]})
                for field in ("caracteristica_ids", "tarefa_ids", "modalidade_ids", "recurso_operado_ids"):
                    target[field] = list(dict.fromkeys(target.get(field, []) + row.get(field, [])))
        payload.update(objetivo="Compreender uma página e revisar mensagens sobre seu conteúdo.",
                       participations=list(roles.values()), mapping_confirmed=True, transfer_confirmed=True)
        e.start_free_context()
        e.update_context(payload)
        cls.novel = e.generate()
        payload["recursos_disponiveis"] = [v for v in payload["recursos_disponiveis"] if v != "REC-ENTRADA-VOZ"]
        payload["recursos_impedidos"] = ["REC-ENTRADA-VOZ"]
        e.update_context(payload)
        cls.no_voice = e.generate()

        e.start_context("CTX-TRANSFERENCIA-RECURSO-DIGITAL-01")
        context = e.current["context"]
        blocked = {"REC-LEGENDAS", "REC-AUDIODESCRICAO"}
        e.update_context({"mapping_confirmed": True, "transfer_confirmed": True,
                          "recursos_disponiveis": list(dict.fromkeys([v for v in context["recursos_disponiveis"] if v not in blocked] + ["REC-REPRODUTOR-VIDEO"])),
                          "recursos_impedidos": sorted(blocked), "recursos_propostos": []})
        cls.no_video_access = e.generate()
        e.start_context("CTX-TRANSFERENCIA-RECURSO-DIGITAL-01")
        cls.unconfirmed = e.generate()

    def test_existing_composition_preserved_but_partial_explicit(self):
        self.assertEqual(len(self.main["decision"]["configuracao_modal"]), 7)
        self.assertEqual(self.main["decision"]["status"], "GERADA_PARCIAL")
        self.assertEqual(set(self.main["execution_evidence"]["functions"]["remaining"]),
                         {"FUN-CARACTERIZAR-CONDICOES", "FUN-PRESERVAR-ACESSO", "FUN-SELECIONAR-MODO-POR-CONDICAO"})

    def test_new_combination_uses_existing_patterns(self):
        self.assertEqual(set(self.novel["decision"]["component_ids"]),
                         {"PAD-CONTEUDO-WEB-EQUIVALENTE", "PAD-COMUNICACAO-MULTIFORMATO"})
        self.assertEqual(self.novel["decision"]["status"], "GERADA")

    def test_removing_voice_reports_partial_without_inventing_alternative(self):
        self.assertEqual(self.no_voice["decision"]["component_ids"], ["PAD-CONTEUDO-WEB-EQUIVALENTE"])
        self.assertEqual(self.no_voice["decision"]["status"], "GERADA_PARCIAL")
        rejected = next(r for r in self.no_voice["explanation"]["rejected"] if r["component_id"] == "PAD-COMUNICACAO-MULTIFORMATO")
        checks = {r["id"]: r for r in self.no_voice["execution_evidence"]["checks"]}
        self.assertTrue(any("REC-ENTRADA-VOZ" in checks[c].get("blocked_ids", []) for c in rejected["check_ids"]))
        self.assertFalse(any("acionador" in text for text in self.no_voice["decision"]["alternativas"]))

    def test_video_instruction_cannot_promise_explicitly_blocked_access(self):
        self.assertNotIn("PAD-VIDEO-PROCESSO", self.no_video_access["decision"]["component_ids"])
        checks = self.no_video_access["execution_evidence"]["checks"]
        gate = next(r for r in checks if r["rule_id"] == "video_instruction_resource_consistency")
        self.assertEqual(gate["outcome"], "FAIL")
        self.assertEqual(set(gate["matched_ids"]), {"REC-LEGENDAS", "REC-AUDIODESCRICAO"})
        self.assertFalse(any(c["component_id"] == "PAD-VIDEO-PROCESSO" for c in self.no_video_access["explanation"]["configurations"]))
        self.assertNotIn("vídeo", self.no_video_access["decision"]["sintese_pratica"]["texto"].lower())

    def test_retrieval_checks_reference_exact_witnesses(self):
        evidence = self.main["execution_evidence"]
        witnesses = {r["id"]: r for r in evidence["retrieval"]}
        for check in evidence["checks"]:
            if check["rule_id"] == "cq2_concrete_witness":
                self.assertIn(check["witness_id"], witnesses)
                self.assertEqual(check["subject_id"], witnesses[check["witness_id"]]["knowledge_id"])

    def test_ablation_records_added_choice_and_exact_grounding(self):
        comparison = self.novel["articulation_comparison"]
        delta = next(d for d in comparison["evidence_delta"] if d["component_id"] == "PAD-COMUNICACAO-MULTIFORMATO")
        self.assertTrue(delta["configuration_added"])
        self.assertIn(delta["configuration_id"], comparison["added_configuration_ids"])
        self.assertTrue(delta["added_support_pairs"])
        self.assertTrue(delta["retrieval_witnesses"])
        for pair in delta["added_support_pairs"]:
            self.assertEqual(self.engine.criterion_origins[pair["origin_id"]]["criterio_id"], pair["criterion_id"])

    def test_unknown_video_resource_is_conditional_not_rejected(self):
        row = next(r for r in self.main["execution_evidence"]["components"] if r["component_id"] == "PAD-VIDEO-PROCESSO")
        self.assertEqual(row["selection"], "CONDITIONAL")
        self.assertEqual(row["availability_status"], "CONDICIONAL_A_CONFIRMACAO")

    def test_unconfirmed_context_does_not_fabricate_component_failures(self):
        self.assertTrue(self.unconfirmed["decision"]["status"].startswith("SUSPENSA"))
        self.assertTrue(all(c["selection"] == "NOT_EVALUATED" for c in self.unconfirmed["execution_evidence"]["components"]))
        self.assertFalse(any(c["stage"] == "component" for c in self.unconfirmed["execution_evidence"]["checks"]))

    def test_every_retrieval_witness_uses_real_task_edges(self):
        graph = self.engine.graph
        for row in self.main["execution_evidence"]["retrieval"]:
            path = row["task_path"]
            self.assertEqual(path[0], row["context_task_id"])
            self.assertEqual(path[-1], row["knowledge_task_id"])
            for a, b in zip(path, path[1:]):
                self.assertIn((MADO[a], SKOS.broader, MADO[b]), graph)
            self.assertIn((MADO[row["input_knowledge_id"]], MADO.aplicavelATarefa, MADO[path[-1]]), graph)
            if row["context_concept_id"]:
                self.assertIn((MADO[row["input_knowledge_id"]], MADO[row["match_predicate"]], MADO[row["context_concept_id"]]), graph)

    def test_articulation_witness_has_actual_input_and_required_function(self):
        required = set(self.main_context["funcoes_requeridas_ids"])
        for row in self.main["execution_evidence"]["retrieval"]:
            if not row["articulation_id"]:
                continue
            art = self.engine.articulations[row["articulation_id"]]
            self.assertIn(row["input_knowledge_id"], art["conhecimento_entrada_ids"])
            self.assertIn(row["knowledge_id"], art["conhecimento_resultante_ids"])
            self.assertIn(row["required_function_id"], required)

    def test_offered_functions_never_become_unstated_context_requirements(self):
        required = set(self.main["execution_evidence"]["functions"]["required"])
        edges = self.main["trace_graph"]["edges"]
        self.assertEqual({e["target"] for e in edges if e["kind"] == "context_requirement"},
                         set(self.main["execution_evidence"]["functions"]["verified"]))
        self.assertNotIn("FUN-CONTEXTUALIZAR-MUDANCA", required)
        self.assertFalse(any(e["kind"] == "context_requirement" and e["target"] == "FUN-CONTEXTUALIZAR-MUDANCA" for e in edges))

    def test_single_projection_for_graph_and_depara(self):
        projected = build_explanation(self.main["execution_evidence"])
        self.assertEqual(projected, self.main["explanation"])
        self.assertEqual(projected["graph"], self.main["trace_graph"])
        self.assertEqual(projected["de_para"], self.main["de_para"])

    def test_exact_criterion_support_not_cartesian(self):
        by_component = {c["component_id"]: c for c in self.main["decision"]["configuracao_modal"]}
        for support in self.main["execution_evidence"]["supports"]:
            source = next(s for s in by_component[support["component_id"]]["criterion_support"] if s["criterion_id"] == support["criterion_id"])
            self.assertEqual(support["knowledge_ids"], source["selected_knowledge_ids"])
            self.assertEqual([o["id"] for o in support["origins"]], source["selected_origin_ids"])
            for origin in support["origins"]:
                self.assertEqual(origin["criterio_id"], support["criterion_id"])

    def test_contributions_anchored_in_excerpt_source_and_state_preserved(self):
        rows = self.main["execution_evidence"]["contributions"]
        self.assertTrue(rows)
        for row in rows:
            excerpt = self.engine.excerpts[row["excerpt_id"]]
            self.assertEqual(row["source"]["id"], excerpt["fonte_id"])
            self.assertIn(row["verification_status"], {"CONFERIDA_NO_DOCUMENTO", "CONFERIDA_NO_REGISTRO", "PENDENTE"})

    def test_documentary_contribution_graph_is_not_runtime_inference(self):
        graph = self.main["trace_graph"]
        nodes = {n["id"]: n for n in graph["nodes"]}
        edges = [e for e in graph["edges"] if e["kind"] == "documentary_contribution"]
        self.assertTrue(edges)
        self.assertTrue(any(nodes[e["source"]]["kind"] == "contribution" and nodes[e["target"]]["kind"] == "excerpt" for e in edges))
        self.assertTrue(all(not e["check_ids"] for e in edges))

    def test_documentary_construction_survives_without_runtime_expansion(self):
        # Projection-only fixture: absence of a runtime expansion is not absence of provenance.
        evidence = copy.deepcopy(self.main["execution_evidence"])
        evidence["retrieval"] = []
        projected = build_explanation(evidence)
        self.assertTrue(any(c["construction"]["contributions"] for c in projected["configurations"]))
        self.assertTrue(all(not a["mobilized_in_execution"] for c in projected["configurations"] for a in c["construction"]["articulations"]))

    def test_textual_conditions_are_not_claimed_as_executed(self):
        rows = self.main["execution_evidence"]["documentary_conditions"]
        self.assertTrue(rows)
        self.assertTrue(all(r["outcome"] == "NOT_EXECUTED" for r in rows))

    def test_no_base_enrichment_during_execution(self):
        self.assertEqual(self.before, hashlib.sha256((ROOT / "data/knowledge-base.json").read_bytes()).hexdigest())

    def test_clear_discards_evidence_and_result(self):
        self.engine._evidence = ExecutionEvidence("test", "temporary-case")
        self.engine.clear()
        self.assertIsNone(self.engine._evidence)
        self.assertIsNone(self.engine.current["last_result"])


if __name__ == "__main__":
    unittest.main()
