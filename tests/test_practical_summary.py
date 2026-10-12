"""Presentation regressions; synthetic projections are not participant evidence.

These tests exercise existing actions without running retrieval or selecting a
new decision. They establish fidelity of the projection, not human comprehension.
"""
import copy
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from engine import DecisionEngine, PRACTICAL_COPY


class PracticalSummaryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        base = json.loads((ROOT / "data/knowledge-base.json").read_text(encoding="utf-8"))
        cls.patterns = {row["id"]: row for row in base["decision_components"]}

    def setUp(self):
        # Only the projection runs: no current context, graph or source data is
        # modified, and no participant abilities are inferred by this fixture.
        self.engine = DecisionEngine.__new__(DecisionEngine)
        self.engine.label = lambda identifier: str(identifier or "")

    def configuration(self, identifier):
        pattern = self.patterns[identifier]
        return {
            "component_id": identifier,
            "papel": pattern["role"],
            "modo": pattern["mode_id"],
            "acao": pattern["action"],
            "funcao": pattern["function"],
            "conditions": copy.deepcopy(pattern.get("conditions", [])),
            "alternative": pattern.get("alternative", ""),
            "monitoring": pattern.get("monitoring", ""),
            "limit": pattern.get("limit", ""),
            "availability_status": "CONFIRMADO_DISPONIVEL",
            "knowledge_ids": ["SYNTHETIC-SELECTED-K"],
            "criterion_ids": ["SYNTHETIC-SELECTED-CA"],
            "articulation_ids": ["SYNTHETIC-SELECTED-ART"],
        }

    def summary(self, rows, status="GERADA"):
        before = copy.deepcopy(rows)
        result = self.engine.build_practical_summary(rows, status)
        self.assertEqual(rows, before, "Presentation must not alter the decision")
        return result

    def test_each_existing_pattern_has_source_checked_action_steps(self):
        for identifier in PRACTICAL_COPY:
            with self.subTest(identifier=identifier):
                row = self.configuration(identifier)
                result = self.summary([row])
                self.assertEqual(len(result["etapas"]), 1)
                step_group = result["etapas"][0]
                self.assertTrue(step_group["origem"]["projecao_editorial_conferida"])
                self.assertEqual(step_group["origem"]["acao_original"], row["acao"])
                self.assertGreaterEqual(len(step_group["passos"]), 2)
                for step in step_group["passos"]:
                    self.assertIn(step["fragmento_origem"], row["acao"])
                    self.assertEqual(step["component_id"], identifier)
                    self.assertEqual(step["campo_origem"], "acao")
                self.assertEqual(step_group["itens"], [step["texto"] for step in step_group["passos"]])

    def test_video_alone_does_not_inherit_content_construction(self):
        result = self.summary([self.configuration("PAD-VIDEO-PROCESSO")])
        self.assertIn("vídeo", result["texto"])
        self.assertNotIn("Construa o recurso", result["texto"])
        self.assertNotIn("partes curtas", result["texto"])
        self.assertNotIn(": .", result["texto"])
        self.assertEqual(result["component_ids"], ["PAD-VIDEO-PROCESSO"])

    def test_audio_alone_does_not_add_image_or_drawing(self):
        result = self.summary([self.configuration("PAD-EXPRESSAO-AUTORAL-FALA-AUDIO")])
        group = result["etapas"][0]
        text = json.dumps({"titulo": result["texto"], "passos": group["passos"],
                           "como_combinar": group["como_combinar"]}, ensure_ascii=False).lower()
        self.assertNotIn("imagem", text)
        self.assertNotIn("desenho", text)
        self.assertIn("áudio", text)
        self.assertIn("texto", text)
        # A drawing remains in the source's explicit alternative, not in the
        # selected action or as an automatically selected modality.
        self.assertIn("desenho", group["alternativas"][0])

    def test_different_choices_are_not_merged_into_a_new_sequence(self):
        identifiers = ["PAD-VIDEO-PROCESSO", "PAD-ORIENTACAO-AUDIO-RECUPERAVEL"]
        result = self.summary([self.configuration(identifier) for identifier in identifiers])
        self.assertEqual([group["component_ids"] for group in result["etapas"]], [[identifier] for identifier in identifiers])
        self.assertEqual(result["organizacao"], "CARTOES_POR_CONFIGURACAO_SEM_ORDEM_CAUSAL_ENTRE_ELES")
        for group in result["etapas"]:
            self.assertTrue(all(step["component_id"] in group["component_ids"] for step in group["passos"]))

    def test_text_review_does_not_invent_an_oral_route(self):
        result = self.summary([self.configuration("PAD-REVISAO-CONFIRMACAO")])
        group = result["etapas"][0]
        self.assertEqual(group["modos"], ["MOD-TEXTO"])
        for unselected_mode in ("oral", "fala", "voz", "áudio"):
            self.assertNotIn(unselected_mode, group["como_combinar"].lower())
        self.assertIn("registro editável", group["como_combinar"].lower())
        self.assertIn("alternativas de acesso", group["como_combinar"].lower())

    def test_communication_does_not_invent_confirmation_after_sending(self):
        result = self.summary([self.configuration("PAD-COMUNICACAO-MULTIFORMATO")])
        relation = result["etapas"][0]["como_combinar"].lower()
        self.assertIn("antes de decidir pelo envio", relation)
        self.assertNotIn("depois", relation)
        self.assertNotIn("após", relation)

    def test_conditions_and_pending_state_remain_explicit(self):
        row = self.configuration("PAD-CONTEUDO-WEB-EQUIVALENTE")
        row["availability_status"] = "CONDICIONAL_A_CONFIRMACAO"
        row["conditions"] += ["SYNTHETIC: confirmar a forma de acesso antes de aplicar"]
        row["resource_options"] = [{"id": "SYNTHETIC-READER", "label": "Leitor a confirmar", "estado": "NAO_CONFIRMADO", "opcional": False}]
        group = self.summary([row], "GERADA_PARCIAL")["etapas"][0]
        self.assertEqual(group["aplicabilidade"], "CONDICIONAL_A_CONFIRMACAO")
        self.assertIn("antes de aplicar", group["antes_de_usar"])
        self.assertEqual(group["condicoes"], row["conditions"])
        self.assertEqual(group["recursos_estruturados"], row["resource_options"])
        self.assertEqual(group["alternativas"], [row["alternative"]])
        self.assertEqual(group["acompanhamento"], [row["monitoring"]])

    def test_projection_preserves_exact_selected_support(self):
        row = self.configuration("PAD-CONTEUDO-WEB-EQUIVALENTE")
        origin = self.summary([row])["etapas"][0]["origem"]
        for field in ("knowledge_ids", "criterion_ids", "articulation_ids"):
            self.assertEqual(origin[field], row[field])
        self.assertNotIn("K17", origin["knowledge_ids"])

    def test_changed_action_does_not_silently_reuse_old_editorial_steps(self):
        row = self.configuration("PAD-VIDEO-PROCESSO")
        row["acao"] = "Ação sintética alterada; conferir o registro atualizado"
        result = self.summary([row])
        group = result["etapas"][0]
        self.assertFalse(group["origem"]["projecao_editorial_conferida"])
        self.assertEqual(group["como_combinar"], "")
        self.assertEqual(group["itens"], ["Ação sintética alterada.", "Conferir o registro atualizado."])
        self.assertNotIn("vídeo", result["texto"].lower())

    def test_unknown_pattern_retains_action_without_an_invented_relation(self):
        row = {"component_id": "SYNTHETIC-NEW", "acao": "Conferir a alternativa declarada", "papel": "principal"}
        group = self.summary([row])["etapas"][0]
        self.assertEqual(group["itens"], ["Conferir a alternativa declarada."])
        self.assertEqual(group["como_combinar"], "")
        self.assertEqual(group["modos"], [])

    def test_empty_and_suspended_results_do_not_gain_actions(self):
        for rows, status in (([], "GERADA"), ([self.configuration("PAD-VIDEO-PROCESSO")], "SUSPENSA")):
            with self.subTest(status=status):
                result = self.summary(rows, status)
                self.assertEqual(result["etapas"], [])
                self.assertEqual(result["component_ids"], [])

    def test_detailed_orientation_has_only_selected_actions(self):
        selected = [copy.deepcopy(self.patterns["PAD-VIDEO-PROCESSO"])]
        before = copy.deepcopy(selected)
        rendered = self.engine.compose_transfer_orientation(selected, {"objetivo": "Observar uma mudança"})
        self.assertEqual(selected, before)
        self.assertIn(selected[0]["action"], rendered)
        self.assertNotIn("produção compartilhada", rendered)
        self.assertNotIn("1.", rendered)
        self.assertNotIn("2.", rendered)

    def test_detailed_orientation_does_not_assert_education_for_a_new_task(self):
        selected = [{"id": "SYNTHETIC-NEW", "label": "Apoio registrado", "action": "Revisar uma mensagem"}]
        rendered = self.engine.compose_transfer_orientation(selected, {"objetivo": "Enviar uma mensagem"})
        self.assertIn("Revisar uma mensagem", rendered)
        self.assertNotIn("estudante", rendered)
        self.assertNotIn("professora", rendered)
        self.assertNotIn("construa o recurso", rendered)


if __name__ == "__main__":
    unittest.main()
