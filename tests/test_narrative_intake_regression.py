"""Synthetic intake checks, not empirical validation."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from engine import DecisionEngine


class NarrativeIntakeRegression(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = DecisionEngine()

    def analyze(self, narrative):
        self.engine.start_free_context()
        return self.engine.analyze_narrative(narrative)["current"]

    def test_recovery_requirement_is_not_positive_ability_or_negated_difficulty(self):
        for phrase, expected in (
            ("não consegue retomar as instruções", True),
            ("não tem dificuldade de retomar as instruções", False),
            ("consegue retomar as instruções", False),
        ):
            current = self.analyze("Uma pessoa precisa acessar o material. A pessoa " + phrase + ".")
            rows = current["context"]["access_requirements"]
            self.assertEqual(any(r["matrix_id"] == "MF-04" for r in rows), expected)
            if expected:
                self.assertIn("FUN-MANTER-INFORMACAO-RECUPERAVEL", rows[0]["function_ids"])
                self.assertIn("retomar as instrucoes", rows[0]["matched_text"])

    def test_draft_revision_is_one_episode_without_invented_feedback(self):
        current = self.analyze(
            "Quero escrever uma mensagem por ditado e revisar o texto antes de enviar. "
            "Consigo usar o teclado para corrigir erros. Tenho microfone e ditado disponíveis.")
        raw = current["context"]["raw"]
        self.assertEqual(len(current["context"]["situations"]), 1)
        self.assertNotIn("TAR-OPERAR-SISTEMA", raw["tarefas"])
        self.assertNotIn("NEC-REVISAO-E-CONFIRMACAO", raw["necessidades"])
        self.assertNotIn("REC-FEEDBACK-ACESSIVEL", raw["recursos_disponiveis"])

    def test_first_person_barrier_preserves_explicit_capacity(self):
        current = self.analyze(
            "Preciso preencher um formulário. Consigo usar o teclado, mas não consigo operar o mouse.")
        person = current["participations"][0]
        requirement = current["context"]["access_requirements"][0]
        self.assertEqual(requirement["matrix_id"], "MF-02")
        self.assertEqual(requirement["participant_id"], person["id"])
        facts = current["context"]["situated_facts"]
        self.assertTrue(any(f["fact_id"].endswith("#CanUseKeyboard") and f["value"] is True for f in facts))
        self.assertTrue(all(f["state"] == "RELATADO" for f in facts))

    def test_teacher_ability_is_not_given_to_supported_person(self):
        current = self.analyze(
            "Quero ajudar uma pessoa a preencher um formulário. "
            "A pessoa não consegue usar o mouse. O professor consegue usar o teclado.")
        supported = next(p for p in current["participations"] if p["papel_id"] == "PAPEL-PESSOA-APOIADA")
        self.assertFalse(any(f["participant_id"] == supported["id"] for f in current["context"]["situated_facts"]))

    def test_planned_purchase_is_not_available(self):
        current = self.analyze("Preciso preencher um formulário. Quero comprar um computador com teclado.")
        raw = current["context"]["raw"]
        self.assertTrue({"REC-COMPUTADOR", "REC-TECLADO"} <= set(raw["recursos_propostos"]))
        self.assertFalse({"REC-COMPUTADOR", "REC-TECLADO"} & set(raw["recursos_disponiveis"]))

    def test_uncertain_or_ambiguous_ability_is_not_assigned(self):
        for narrative in (
            "A professora precisa escrever um texto. Quero preencher um formulário. Consigo usar o teclado que a professora não consegue usar.",
            "Preciso preencher um formulário. Não é verdade que consigo usar o teclado.",
            "Preciso preencher um formulário. Se eu consigo usar o teclado, poderei fazer a tarefa.",
        ):
            current = self.analyze(narrative)
            self.assertFalse(any(f["fact_id"].endswith("#CanUseKeyboard")
                                 for f in current["context"]["situated_facts"]), narrative)

    def test_negated_purchase_does_not_override_explicit_availability(self):
        current = self.analyze("Preciso preencher um formulário. Não preciso comprar um teclado porque já tenho teclado disponível.")
        raw = current["context"]["raw"]
        self.assertIn("REC-TECLADO", raw["recursos_disponiveis"])
        self.assertNotIn("REC-TECLADO", raw["recursos_propostos"])


if __name__ == "__main__":
    unittest.main()
