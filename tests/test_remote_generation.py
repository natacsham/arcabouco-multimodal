"""Remote teaching regressions; follow-up answers are synthetic, not user facts.

The narrative is not a scenario/template in the executable knowledge base.
These checks deliberately do not expect a complete lesson or a ready-made text.
"""
import copy
import hashlib
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from engine import DecisionEngine


def narrative(topic="derivações com sufixo", total=30, year=4):
    return (f"Sou uma professora do {year} ano do ensino fundamental I, onde tenho uma turma de {total} alunos. "
            "Tenho 3 alunos dessa turma com Transtorno do Espectro Autista. "
            f"Estou querendo ministrar o conteúdo referente a {topic}. "
            "No entanto, devido a condições climáticas as aulas não podem ser presenciais. "
            "Estão sendo remotas. Por isso, vou precisar do apoio de um mediador, os pais, por exemplo, "
            "para que possam me apoiar indiretamente na condução da explicação e na realização das atividades.")


class RemoteGenerationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = DecisionEngine()
        cls.base_hash = hashlib.sha256((ROOT / "data/knowledge-base.json").read_bytes()).hexdigest()

    def analyze(self, text=None):
        self.engine.start_free_context()
        return self.engine.analyze_narrative(text or narrative())["current"]

    def test_unexplained_access_needs_have_actual_followup_not_fake_advice(self):
        self.analyze()
        expected = copy.deepcopy(self.engine.missing_questions())
        self.engine.update_context({"mapping_confirmed": True})
        result = self.engine.generate_situated()
        self.assertEqual(result["proposal_status"], "NONE")
        self.assertEqual(result["intake_status"], "NEEDS_CLARIFICATION")
        self.assertTrue(result["next_questions"])
        self.assertLessEqual(len(result["next_questions"]), 3)
        self.assertEqual({q["id"] for q in result["next_questions"]},
                         {q["id"] for q in expected[:3]})
        self.assertTrue(any(q["field"] == "functional_observation" for q in result["next_questions"]))
        self.assertEqual(result["choices"], [])

    def test_unknown_answer_is_not_repeated_or_promoted_to_support_need(self):
        self.analyze()
        question = next(q for q in self.engine.missing_questions() if q["field"] == "functional_observation")
        self.engine.update_context({"question_answers": [{"question_id": question["id"], "state": "UNKNOWN"}]})
        self.engine.update_context({"mapping_confirmed": True})
        result = self.engine.generate_situated()
        self.assertNotIn(question["id"], {q["id"] for q in result["next_questions"]})
        self.assertIn(question["id"], {q["id"] for q in result["unresolved_answers"]})
        self.assertFalse(self.engine.current["context"]["access_requirements"])
        self.assertFalse(result["choices"])

    def test_unknown_context_is_not_classified_as_proven_base_limit(self):
        self.analyze()
        for _ in range(3):
            available = self.engine.missing_questions()
            if not available:
                break
            self.engine.update_context({"question_answers": [
                {"question_id": q["id"], "state": "UNKNOWN"}
                for q in available if q["id"] in self.engine.current["context"]["question_manifest"]
            ]})
        # Legacy resource questions use a distinct skip contract. Do not turn
        # their presence into a false claim that every question was answered.
        self.engine.update_context({"mapping_confirmed": True})
        result = self.engine.generate_situated()
        self.assertTrue(result["unresolved_answers"])
        self.assertIn(result["intake_status"], {"NEEDS_CLARIFICATION", "CONTEXT_UNKNOWN"})
        self.assertFalse(result["choices"])

    def test_real_functional_answer_reaches_existing_analytical_operation(self):
        self.analyze()
        question = next(q for q in self.engine.missing_questions() if q["field"] == "functional_observation")
        # Explicit synthetic answer: not inferred from TEA or the school year.
        self.engine.update_context({"question_answers": [{"question_id": question["id"],
            "value": "Precisam de instruções por etapas e precisam retomar a explicação."}]})
        self.engine.update_context({"mapping_confirmed": True})
        result = self.engine.generate_situated()
        proposals = result["choices"] + result["pending_candidates"] + result["partial_segments"]
        steps = [s for p in proposals for s in p["steps"]]
        self.assertTrue(any(s["id"] == "OP-PAD-ORGANIZAR-CONTEUDO-PERSISTENTE" for s in steps))
        self.assertNotEqual(result["proposal_status"], "COMPLETE")
        self.assertFalse(result["covers_whole_reported_task"])
        self.assertTrue(result["capability_evaluations"])
        requirements = self.engine.current["context"]["access_requirements"]
        self.assertTrue(requirements)
        self.assertTrue(all(r["participant_id"] == question["participant_id"] for r in requirements))

    def test_subject_is_not_a_route_selector(self):
        results = []
        for topic in ("derivações com sufixo", "introdução fonêmica", "ciclo da água"):
            self.analyze(narrative(topic))
            question = next(q for q in self.engine.missing_questions() if q["field"] == "functional_observation")
            self.engine.update_context({"question_answers": [{"question_id": question["id"],
                "value": "Precisam de instruções por etapas e precisam retomar a explicação."}],
                "mapping_confirmed": True})
            result = self.engine.generate_situated()
            results.append((result["proposal_status"], sorted({s["id"] for p in
                result["choices"] + result["pending_candidates"] + result["partial_segments"] for s in p["steps"]})))
        self.assertEqual(results[0], results[1])
        self.assertEqual(results[1], results[2])
        self.assertEqual(self.base_hash, hashlib.sha256((ROOT / "data/knowledge-base.json").read_bytes()).hexdigest())


if __name__ == "__main__":
    unittest.main()
