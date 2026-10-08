"""Regression tests of public execution, exact support and no history."""

import ast
import copy
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from engine import DecisionEngine, MADO, local_id
from rdflib import RDF


class EngineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = DecisionEngine()
        cls.engine.update_context(
            {"mapping_confirmed": True, "transfer_confirmed": True}
        )
        cls.main = cls.engine.generate()

    def setUp(self):
        self.engine.start_context("CTX-TRANSFERENCIA-RECURSO-DIGITAL-01")

    def test_main_seven_grounded_configurations(self):
        self.assertEqual(self.main["decision"]["status"], "GERADA_PARCIAL")
        self.assertEqual(len(self.main["decision"]["configuracao_modal"]), 7)
        self.assertTrue(
            all(
                c["criterion_support"] and c["funcao"] and c["alternative"]
                for c in self.main["decision"]["configuracao_modal"]
            )
        )

    def test_cq4_exact_pairs(self):
        expected = set()
        for i, cfg in enumerate(self.main["decision"]["configuracao_modal"], 1):
            config_id = f"CFG-{self.main['decision']['id']}-{i:02d}"
            for support in cfg["criterion_support"]:
                for kid in support["selected_knowledge_ids"]:
                    for oid in support["selected_origin_ids"]:
                        expected.add((config_id, support["criterion_id"], kid, oid))
        obtained = {
            (
                local_id(r["configuracao"]),
                local_id(r["criterio"]),
                local_id(r["conhecimentoFundamento"]),
                local_id(r["origem"]),
            )
            for r in self.main["query_results"]["CQ-004"]
        }
        self.assertEqual(expected, obtained)
        first = self.main["decision"]["configuracao_modal"][0]
        support = next(
            s for s in first["criterion_support"] if s["criterion_id"] == "CA02"
        )
        self.assertEqual(set(support["selected_knowledge_ids"]), {"K38", "K43"})

    def test_articulation_edges_not_cartesian(self):
        for edge in self.main["trace_graph"]["edges"]:
            if edge["label"] == "produz/refina":
                self.assertIn(
                    edge["target"],
                    self.engine.articulations[edge["source"]][
                        "conhecimento_resultante_ids"
                    ],
                )

    def test_all_queries_executed(self):
        self.assertEqual(
            set(self.main["query_summary"]), {f"CQ-{i:03}" for i in range(1, 9)}
        )
        self.assertTrue(self.main["query_results"]["CQ-003"])
        self.assertTrue(
            all(
                not row.get("conteudo") and row.get("estadoPublicacao")
                for row in self.main["query_results"]["CQ-003"]
            )
        )

    def test_no_history_or_write_methods(self):
        for field in ("sessions", "event_log", "last_export", "last_xlsx"):
            self.assertFalse(hasattr(self.engine, field))
        code = ast.parse((ROOT / "engine.py").read_text(encoding="utf-8"))
        for node in ast.walk(code):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                self.assertNotIn(
                    node.func.attr,
                    {
                        "write_text",
                        "write_bytes",
                        "mkdir",
                        "record_evaluation",
                        "log_event",
                    },
                )

    def test_blocked_knowledge(self):
        ctx = copy.deepcopy(self.engine.current["context"])
        ctx["recursos_disponiveis"] = [
            v for v in ctx["recursos_disponiveis"] if v != "REC-REPRODUTOR-VIDEO"
        ]
        ctx["recursos_impedidos"] = ["REC-REPRODUTOR-VIDEO"]
        self.assertEqual(self.engine.authorize_knowledge("K36", ctx)[0], "EXCLUIDO")

    def test_missing_resource_is_conditional_not_available(self):
        ctx = copy.deepcopy(self.engine.current["context"])
        ctx["recursos_disponiveis"] = [
            v for v in ctx["recursos_disponiveis"] if v != "REC-REPRODUTOR-VIDEO"
        ]
        ctx["recursos_impedidos"] = []
        self.assertEqual(self.engine.authorize_knowledge("K36", ctx)[0], "CONDICIONAL")

    def test_curated_articulation_allowlist(self):
        old = copy.deepcopy(self.engine.articulations["ART-REF-03"])
        try:
            self.engine.articulations["ART-REF-03"]["estado_curadoria"] = "PROPOSTA"
            self.assertFalse(self.engine.articulation_authorized("ART-REF-03"))
        finally:
            self.engine.articulations["ART-REF-03"] = old

    def test_failed_update_is_transactional(self):
        old = copy.deepcopy(self.engine.current)
        with self.assertRaises(ValueError):
            self.engine.update_context(
                {"objetivo": "changed", "tarefas": ["NOT-A-CONCEPT"]}
            )
        self.assertEqual(self.engine.current, old)

    def test_false_string_cannot_confirm(self):
        with self.assertRaises(ValueError):
            self.engine.update_context({"mapping_confirmed": "false"})

    def test_resource_cannot_be_blocked_and_available(self):
        ctx = self.engine.current["context"]
        with self.assertRaises(ValueError):
            self.engine.update_context(
                {"recursos_impedidos": [ctx["recursos_disponiveis"][0]]}
            )

    def test_edit_invalidates_previous_decision(self):
        self.engine.current["last_result"] = copy.deepcopy(self.main)
        self.engine.update_context(
            {"objetivo": "Outro objetivo requer nova confirmação"}
        )
        self.assertIsNone(self.engine.current["last_result"])
        self.assertFalse(self.engine.current["mapping_confirmed"])

    def test_clear_erases_input(self):
        self.engine.current["context"][
            "descricao_do_contexto"
        ] = "sentinel-private-input"
        self.engine.clear()
        self.assertNotIn("sentinel-private-input", json.dumps(self.engine.current))

    def test_context_preserves_documented_perspective(self):
        g = self.engine.build_context_graph()
        ctx = MADO[self.engine.current["context"]["id"]]
        self.assertEqual(set(g.objects(ctx, MADO.descritoSobPerspectiva)), {MADO.P02, MADO.P03})

    def test_free_context_not_attributed_to_specialist(self):
        self.engine.start_free_context()
        g = self.engine.build_context_graph()
        ctx = MADO[self.engine.current["context"]["id"]]
        self.assertEqual(set(g.objects(ctx, MADO.descritoSobPerspectiva)), {MADO["P-USUARIO-TEMPORARIO"]})
        self.assertIn((MADO["P-USUARIO-TEMPORARIO"], RDF.type, MADO.Perspectiva), g)

    def test_reported_correction_is_available_only_in_current_case(self):
        response = self.engine.confirm_reported(False, "Correção sintética de demonstração")
        self.assertEqual(response["reported_correction"], "Correção sintética de demonstração")
        self.engine.clear()
        self.assertEqual(self.engine.current_payload()["reported_correction"], "")

    def test_narrative_not_free_interpretation(self):
        self.engine.start_free_context()
        result = self.engine.analyze_narrative(
            "Uma pessoa precisa fazer algo ainda não descrito com informações suficientes."
        )
        self.assertFalse(result["current"]["mapping_confirmed"])
        self.assertTrue(self.engine.missing_questions())


if __name__ == "__main__":
    unittest.main()
