"""Synthetic export regressions: preserve stated perspective, never invent one."""

import copy
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "vendor"))

from engine import DecisionEngine, MADO
from rdflib import Graph, Namespace, RDF, RDFS, Literal
from pyshacl import validate

SH = Namespace("http://www.w3.org/ns/shacl#")


class ContextGraphExportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = DecisionEngine()
        cls.shapes = Graph().parse(ROOT / "shapes/main.shacl.ttl", format="turtle")

    def setUp(self):
        self.engine.start_context("CTX-TRANSFERENCIA-RECURSO-DIGITAL-01")
        self.context = self.engine.current["context"]
        self.assertTrue(self.context["situations"])
        self.situation = self.context["situations"][0]
        self.episode = MADO[self.situation["id"]]

    def test_episode_preserves_parent_description_perspectives(self):
        graph = self.engine.build_context_graph()
        expected = {MADO[p] for p in self.context["perspectiva_ids"]}
        self.assertEqual(expected, {MADO.P02, MADO.P03})
        self.assertEqual(set(graph.objects(self.episode, MADO.descritoSobPerspectiva)), expected)

    def test_episode_specific_perspective_is_not_overridden(self):
        self.situation["perspectiva_ids"] = ["P02"]
        graph = self.engine.build_context_graph()
        self.assertEqual(set(graph.objects(self.episode, MADO.descritoSobPerspectiva)), {MADO.P02})

    def test_explicit_empty_episode_perspective_stays_missing(self):
        self.situation["perspectiva_ids"] = []
        graph = self.engine.build_context_graph()
        self.assertFalse(list(graph.objects(self.episode, MADO.descritoSobPerspectiva)))

    def test_missing_parent_perspective_is_not_invented_and_fails_shape(self):
        self.context.pop("perspectiva_ids")
        graph = self.engine.graph + self.engine.build_context_graph()
        self.assertFalse(list(graph.objects(self.episode, MADO.descritoSobPerspectiva)))
        conforms, report, _ = validate(graph, shacl_graph=self.shapes, inference="none", allow_warnings=True)
        self.assertFalse(conforms)
        self.assertTrue(any(
            report.value(result, SH.focusNode) == self.episode
            and report.value(result, SH.resultPath) == MADO.descritoSobPerspectiva
            and report.value(result, SH.sourceConstraintComponent) == SH.MinCountConstraintComponent
            for result in report.subjects(RDF.type, SH.ValidationResult)
        ))

    def test_legacy_runtime_decision_export_conforms_with_episode(self):
        self.engine.update_context({"mapping_confirmed": True, "transfer_confirmed": True})
        result = self.engine.generate()
        runtime = self.engine.build_decision_graph(result)
        self.assertTrue(list(runtime.objects(self.episode, MADO.descritoSobPerspectiva)))
        conforms, report, text = validate(
            self.engine.graph + runtime, shacl_graph=self.shapes,
            inference="none", allow_warnings=True, allow_infos=True, advanced=True,
        )
        violations = [r for r in report.subjects(RDF.type, SH.ValidationResult)
                      if report.value(r, SH.resultSeverity) == SH.Violation]
        self.assertTrue(conforms, str(text))
        self.assertEqual(violations, [])

    def situated_case(self):
        """New synthetic input using real MF04 needs, not invented derivations."""
        self.engine.start_free_context()
        self.engine.current["context"].update({
            "id": "SYN-CQ010-CURRENT", "revision": 7,
            "tarefas": ["TAR-PRODUZIR-CONTEUDO-MULTIMODAL", "TAR-REVISAR-E-CONFIRMAR"],
            "necessidades": ["NEC-FUNCAO-EXPLICITA-POR-MODALIDADE", "NEC-PRESERVAR-CONTEUDO-PARA-REVISAO"],
            "situations": [
                {"id": "SYN-EP-PRODUZIR", "task_ids": ["TAR-PRODUZIR-CONTEUDO-MULTIMODAL"],
                 "participant_ids": ["SYN-P-A", "SYN-P-B"]},
                {"id": "SYN-EP-REVISAR", "task_ids": ["TAR-REVISAR-E-CONFIRMAR"],
                 "participant_ids": ["SYN-P-A", "SYN-P-B"]},
            ],
            "assertions": [
                {"id": "SYN-NEED-A", "kind": "need", "subject_id": "SYN-P-A",
                 "situation_id": "SYN-EP-PRODUZIR", "state": "CONFIRMADO",
                 "value": "NEC-FUNCAO-EXPLICITA-POR-MODALIDADE"},
                {"id": "SYN-NEED-B", "kind": "need", "subject_id": "SYN-P-B",
                 "situation_id": "SYN-EP-REVISAR", "state": "CONFIRMADO",
                 "value": "NEC-PRESERVAR-CONTEUDO-PARA-REVISAO"},
            ],
        })
        self.engine.current["participations"] = [
            {"id": pid, "papel_id": "PAPEL-ESTUDANTE"} for pid in ("SYN-P-A", "SYN-P-B")]
        self.engine.current["mapping_confirmed"] = True
        return self.engine.generate_situated()

    def test_cq010_roundtrip_of_current_requirements_keeps_exact_scope(self):
        result = self.situated_case()
        self.assertEqual(len(result["required_functions"]), 2)
        runtime = self.engine.build_context_graph(situated_result=result)
        graph = Graph().parse(data=runtime.serialize(format="turtle"), format="turtle")
        rows = list(graph.query(self.engine.queries["CQ-010"]))
        actual = {(r.contexto, r.episodioPai, r.participacao, r.tarefa, r.funcao, r.condicao) for r in rows}
        expected = {
            (MADO["SYN-EP-PRODUZIR"], MADO["SYN-CQ010-CURRENT"], MADO["SYN-P-A"],
             MADO["TAR-PRODUZIR-CONTEUDO-MULTIMODAL"], MADO["FUN-ORGANIZAR-CONTEUDO"],
             MADO["NEC-FUNCAO-EXPLICITA-POR-MODALIDADE"]),
            (MADO["SYN-EP-REVISAR"], MADO["SYN-CQ010-CURRENT"], MADO["SYN-P-B"],
             MADO["TAR-REVISAR-E-CONFIRMAR"], MADO["FUN-MANTER-INFORMACAO-RECUPERAVEL"],
             MADO["NEC-PRESERVAR-CONTEUDO-PARA-REVISAO"]),
        }
        # Equality rules out every other participant/task/episode cross-product.
        self.assertEqual(actual, expected)
        self.assertEqual(len(set(graph.subjects(RDF.type, MADO.FuncaoRequeridaSituada))), 2)
        for row in rows:
            self.assertIn((row.requisito, MADO.statusDoRegistro,
                           Literal("CONTEXTUAL_TASK_SCOPE_NOT_CAUSAL_SUPPORT")), graph)
            self.assertTrue(list(graph.objects(row.requisito, RDFS.comment)))
        conforms, _, report = validate(self.engine.graph + graph, shacl_graph=self.shapes,
                                      inference="none", allow_warnings=True)
        self.assertTrue(conforms, str(report))

    def test_situated_export_rejects_other_context_and_stale_revision(self):
        result = self.situated_case()
        wrong = copy.deepcopy(result)
        wrong["context_id"] = "SYN-ANOTHER-CONTEXT"
        with self.assertRaisesRegex(ValueError, "revisão atuais"):
            self.engine.build_context_graph(situated_result=wrong)
        self.engine.current["context"]["revision"] += 1
        with self.assertRaisesRegex(ValueError, "revisão atuais"):
            self.engine.build_context_graph(situated_result=result)

    def test_situated_export_cannot_reassign_a_requirement_to_another_participant(self):
        result = self.situated_case()
        altered = copy.deepcopy(result)
        requirement = next(r for r in altered["required_functions"] if r["participant_id"] == "SYN-P-A")
        requirement["participant_id"] = "SYN-P-B"
        with self.assertRaisesRegex(ValueError, "testemunho de derivação"):
            self.engine.build_context_graph(situated_result=altered)

    def test_situated_export_rejects_changed_confirmation_or_active_episode(self):
        result = self.situated_case()
        self.engine.current["mapping_confirmed"] = False
        with self.assertRaisesRegex(ValueError, "Confirme o contexto"):
            self.engine.build_context_graph(situated_result=result)
        self.engine.current["mapping_confirmed"] = True
        self.engine.current["context"]["active_situation_id"] = "SYN-EP-PRODUZIR"
        with self.assertRaisesRegex(ValueError, "revisão atuais"):
            self.engine.build_context_graph(situated_result=result)
        active = self.engine.generate_situated()
        graph = self.engine.build_context_graph(situated_result=active)
        rows = list(graph.query(self.engine.queries["CQ-010"]))
        self.assertEqual({(r.contexto, r.participacao) for r in rows},
                         {(MADO["SYN-EP-PRODUZIR"], MADO["SYN-P-A"])})


if __name__ == "__main__":
    unittest.main()
