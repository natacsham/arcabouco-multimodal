"""Documentary contribution checks; synthetic cases are NOT empirical evidence."""
import copy
import importlib.util
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "vendor"))
sys.path.insert(0, str(ROOT / "scripts"))
from rdflib import Graph, Literal, RDF, XSD
from rdflib.compare import isomorphic
from pyshacl import validate
import build_traceability_rdf as builder

spec = importlib.util.spec_from_file_location("ontology_fixture", ROOT / "tests/test_ontology.py")
fixture_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fixture_module)
M, text = fixture_module.M, fixture_module.text


def synthetic_data():
    art = {"id": "ART", "conhecimento_resultante_ids": ["K2"], "trecho_ids": ["T1", "T2"]}
    art.update({key: "Explicação sintética para teste, não histórica." for key in builder.ART_TEXT})
    return {
        "sources": [{"id": "F1"}],
        "excerpts": [{"id": "T2", "fonte_id": "F1"}],
        "knowledge": [{"id": "K2", "fonte_ids": ["F1"], "trecho_ids": ["T2"]}],
        "articulations": [art],
        "contributions": [{
            "id": "C2", "articulation_id": "ART", "knowledge_id": "K2", "excerpt_id": "T2",
            "statement": "O trecho oferece uma parcela delimitada do conhecimento.",
            "contribution_role": "CONDICAO", "nature": "PARAFRASE_DE_REGISTRO",
            "justification": "Apoio parcial, não prova da decisão completa.",
            "verification_status": "CONFERIDA_NO_REGISTRO", "reviewer": "Teste sintético",
            "review_date": "2026-10-08",
        }],
    }


def contribution_graph(link_application=False):
    graph = fixture_module.fixture()
    fixture_module.add_articulation(graph)
    if link_application:
        graph.add((M.CFG, M.configuracaoMobilizaArticulacao, M.ART))
    return builder.build_graph(graph, Graph(), synthetic_data())


class ContributionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.shapes = Graph().parse(ROOT / "shapes/main.shacl.ttl", format="turtle")
        cls.kb = json.loads((ROOT / "data/knowledge-base.json").read_text(encoding="utf-8-sig"))

    def assert_valid(self, graph, expected=True):
        conforms, _, report = validate(graph, shacl_graph=self.shapes,
                                      inference="none", allow_warnings=True)
        self.assertEqual(bool(conforms), expected, str(report))

    def test_complete_contribution_passes(self):
        self.assert_valid(contribution_graph(True))

    def test_partial_decision_retains_structural_requirements(self):
        graph = contribution_graph(True)
        graph.set((M.D, M.statusDecisao, Literal("GERADA_PARCIAL")))
        self.assert_valid(graph)
        fixture_module.erase_configurations(graph)
        self.assert_valid(graph, False)

    def test_civil_date_does_not_invent_time_or_unsupported_datatype(self):
        graph = contribution_graph()
        self.assertEqual(str(graph.value(M.C2, M.dataDaConferencia)), "2026-10-08")
        graph.set((M.C2, M.dataDaConferencia, Literal("08/10/2026")))
        self.assert_valid(graph, False)
        data = synthetic_data()
        data["contributions"][0]["review_date"] = "2026-02-30"
        with self.assertRaises(ValueError):
            builder.validate_contributions(data)

    def test_missing_excerpt_fails(self):
        graph = contribution_graph()
        graph.remove((M.C2, M.contribuicaoDoTrecho, None))
        self.assert_valid(graph, False)

    def test_source_must_belong_to_exact_knowledge(self):
        graph = contribution_graph()
        graph.remove((M.K2, M.derivadoDe, None))
        graph.add((M.F2, RDF.type, M.Fonte))
        graph.add((M.K2, M.derivadoDe, M.F2))
        self.assert_valid(graph, False)

    def test_contribution_must_refer_to_articulation_output(self):
        graph = contribution_graph()
        graph.set((M.C2, M.contribuicaoParaConhecimento, M.K1))
        self.assert_valid(graph, False)

    def test_blank_justification_fails(self):
        graph = contribution_graph()
        graph.set((M.C2, M.justificativaDaContribuicao, text("   ")))
        self.assert_valid(graph, False)

    def test_unknown_confirmation_fails(self):
        graph = contribution_graph()
        graph.set((M.C2, M.estadoDeConferenciaDaContribuicao, Literal("APROVADA")))
        self.assert_valid(graph, False)

    def test_missing_analytical_operation_fails(self):
        graph = contribution_graph()
        graph.remove((M.ART, M.explicacaoDaOperacaoAnalitica, None))
        self.assert_valid(graph, False)

    def test_pending_can_be_kept_in_base(self):
        graph = contribution_graph()
        graph.set((M.C2, M.estadoDeConferenciaDaContribuicao, Literal("PENDENTE")))
        self.assert_valid(graph)

    def test_pending_cannot_be_used_by_application(self):
        graph = contribution_graph(True)
        graph.set((M.C2, M.estadoDeConferenciaDaContribuicao, Literal("PENDENTE")))
        self.assert_valid(graph, False)

    def test_other_application_cannot_borrow_contribution(self):
        graph = contribution_graph(True)
        graph.add((M["CFG-APP-1"], M.aplicacaoMobilizaContribuicao, M.C2))
        self.assert_valid(graph, False)

    def test_application_requires_actual_articulation_in_configuration(self):
        graph = contribution_graph(True)
        graph.remove((M.CFG, M.configuracaoMobilizaArticulacao, M.ART))
        self.assert_valid(graph, False)

    def test_pilot_json_has_valid_exact_pairs(self):
        builder.validate_contributions(self.kb)
        pilot = [c for c in self.kb["contributions"] if c["knowledge_id"] in ("K38", "K43")]
        self.assertTrue(pilot)
        self.assertTrue(all(c["verification_status"] == "CONFERIDA_NO_REGISTRO" for c in pilot))

    def test_json_rejects_independent_source_and_duplicate_id(self):
        data = synthetic_data()
        data["contributions"][0]["source_id"] = "F1"
        with self.assertRaises(ValueError):
            builder.validate_contributions(data)
        data = synthetic_data()
        data["contributions"].append(copy.deepcopy(data["contributions"][0]))
        with self.assertRaises(ValueError):
            builder.validate_contributions(data)

    def test_json_rejects_wrong_output_and_unregistered_excerpt(self):
        for field, value in (("conhecimento_resultante_ids", []), ("trecho_ids", ["T1"])):
            data = synthetic_data()
            data["articulations"][0][field] = value
            with self.assertRaises(ValueError):
                builder.validate_contributions(data)

    def test_exporter_is_idempotent_without_private_inputs(self):
        data = synthetic_data()
        base = contribution_graph(True)
        tbox = Graph().parse(ROOT / "ontology/main.ttl", format="turtle")
        first = builder.build_graph(base, tbox, data)
        ttl, xml = builder.canonical_outputs(first)
        second = builder.build_graph(Graph().parse(data=ttl, format="turtle"), tbox, data)
        self.assertEqual((ttl, xml), builder.canonical_outputs(second))
        self.assertTrue(isomorphic(first, Graph().parse(data=xml, format="xml")))

    def test_pilot_rdf_removes_f07_only_from_k43(self):
        graph = Graph().parse(ROOT / "ontology/mado-combined.ttl", format="turtle")
        self.assertNotIn((M.K43, M.derivadoDe, M.F07), graph)
        self.assertIn((M.K38, M.derivadoDe, M.F07), graph)
        for row in self.kb["contributions"]:
            node = M[row["id"]]
            self.assertIn((node, M.contribuicaoDoTrecho, M[row["excerpt_id"]]), graph)
            self.assertFalse(list(graph.objects(node, M.derivadoDe)))

    def test_new_query_exposes_exact_contribution_not_all_articulation_sources(self):
        graph = Graph().parse(ROOT / "ontology/mado-combined.ttl", format="turtle")
        rows = list(graph.query((ROOT / "queries/CQ-003.rq").read_text(encoding="utf-8")))
        contribution_rows = [row.asdict() for row in rows if row.asdict().get("contribuicao")]
        self.assertTrue(contribution_rows)
        expected = {c["id"]: c for c in self.kb["contributions"]}
        excerpts = {t["id"]: t for t in self.kb["excerpts"]}
        for row in contribution_rows:
            contribution = expected[str(row["contribuicao"]).split("#")[-1]]
            self.assertEqual(row["conhecimento"], M[contribution["knowledge_id"]])
            self.assertEqual(row["articulacao"], M[contribution["articulation_id"]])
            self.assertEqual(row["trecho"], M[contribution["excerpt_id"]])
            self.assertEqual(row["fonte"], M[excerpts[contribution["excerpt_id"]]["fonte_id"]])


if __name__ == "__main__":
    unittest.main()
