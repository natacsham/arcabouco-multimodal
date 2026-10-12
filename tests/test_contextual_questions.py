"""Synthetic dialogue and reuse checks, not evidence from a participant session."""
import copy
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from engine import DecisionEngine


class ContextualQuestionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = DecisionEngine()

    def setUp(self):
        self.engine.start_free_context()

    def analyze(self, text):
        return self.engine.analyze_narrative(text)["current"]

    def test_documented_nonvisual_need_is_not_a_personal_ability(self):
        current = self.analyze("Uma pessoa cega precisa acessar o conteúdo de uma página web. Quero tornar as informações acessíveis.")
        requirements = current["context"]["access_requirements"]
        self.assertEqual([row["matrix_id"] for row in requirements], ["MF-01"])
        self.assertTrue(requirements[0]["source_ids"] and requirements[0]["excerpt_ids"])
        self.assertFalse(requirements[0]["capabilities_inferred"])
        person = current["participations"][0]
        self.assertEqual(person["modalidade_ids"], [])
        self.assertEqual(person["recurso_operado_ids"], [])
        self.assertNotIn("CAR-USA-LEITOR-TELA", person["caracteristica_ids"])
        self.assertFalse(any(row["field"] == "barreira_ou_necessidade" for row in current["questions"]))
        self.assertLessEqual(len(current["questions"]), 3)

    def test_low_vision_is_not_asserted_to_be_nonvisual_interaction(self):
        current = self.analyze("Uma pessoa com baixa visão precisa acessar conteúdo digital. Quero adaptar a página web.")
        self.assertTrue(current["context"]["access_requirements"])
        self.assertNotIn("CAR-INTERACAO-NAO-VISUAL", current["context"]["raw"]["caracteristicas_pessoa"])
        self.assertNotIn("CAR-PESSOA-CEGA-LEITOR-TELA", current["context"]["raw"]["caracteristicas_pessoa"])
        self.assertIn("baixa visao", current["context"]["access_requirements"][0]["matched_text"])

    def test_functional_description_recovers_same_design_need(self):
        literal = self.analyze("Uma pessoa cega precisa acessar conteúdo digital em uma página web. Quero adaptar o conteúdo.")
        self.engine.start_free_context()
        functional = self.analyze("Uma pessoa não consegue enxergar e precisa acessar conteúdo digital em uma página web. Quero adaptar o conteúdo.")
        self.assertEqual(set(literal["context"]["raw"]["necessidades"]), set(functional["context"]["raw"]["necessidades"]))
        self.assertEqual(functional["context"]["raw"]["modalidades_disponiveis"], [])

    def test_requirements_have_the_correct_participant_scope(self):
        current = self.analyze("Uma turma precisa acessar conteúdo digital sobre agricultura. Há uma pessoa cega e duas pessoas surdas. Quero que todos acompanhem a página web.")
        people = {row["id"]: row["grupo_rotulo"] for row in current["participations"] if row.get("grupo_rotulo")}
        requirements = current["context"]["access_requirements"]
        self.assertEqual({row["matrix_id"] for row in requirements}, {"MF-01", "MF-11"})
        self.assertEqual({row["matrix_id"]: people[row["participant_id"]] for row in requirements}, {"MF-01": "cega", "MF-11": "surdas"})
        self.assertTrue(all(not row["modalidade_ids"] and not row["recurso_operado_ids"] for row in current["participations"]))

    def test_negation_does_not_create_access_requirement(self):
        current = self.analyze("Uma pessoa não é cega e precisa acessar conteúdo digital em uma página web. Quero adaptar o material.")
        self.assertEqual(current["context"]["access_requirements"], [])

    def test_negated_groups_do_not_create_people_or_requirements(self):
        for statement in ("Não há alunos cegos nesta turma.", "Não existem pessoas surdas neste grupo."):
            self.engine.start_free_context()
            current = self.analyze(statement + " Quero adaptar uma página web para acessar conteúdo digital.")
            self.assertEqual(current["context"]["access_requirements"], [])
            self.assertFalse(any(person.get("grupo_rotulo") for person in current["participations"]))

    def test_negation_of_equipment_does_not_negate_the_person_in_another_clause(self):
        current = self.analyze("Não há computador, mas há uma pessoa cega que precisa acessar conteúdo digital em uma página web.")
        self.assertEqual([row["matrix_id"] for row in current["context"]["access_requirements"]], ["MF-01"])

    def test_contradiction_is_not_promoted_to_a_requirement(self):
        current = self.analyze("Uma pessoa cega precisa acessar conteúdo digital em uma página web. A pessoa não é cega. Quero adaptar o material.")
        self.assertTrue(current["context"]["access_requirements"])
        self.assertEqual(current["context"]["access_requirements"][0]["status"], "CONFLITO_A_CONFIRMAR")
        self.assertEqual(current["context"]["raw"]["necessidades"], [])

    def test_an_unverified_matrix_entry_cannot_derive_needs(self):
        previous = copy.deepcopy(self.engine.functional_matrix)
        try:
            for state in ("PENDENTE", "NAO_CONFERIDO", "NAO_CONFERIDO_NA_FONTE"):
                for row in self.engine.functional_matrix:
                    row["estado"] = state
                current = self.analyze("Uma pessoa cega precisa acessar conteúdo digital em uma página web. Quero adaptar o material.")
                self.assertEqual(current["context"]["access_requirements"], [])
        finally:
            self.engine.functional_matrix = previous

    def test_questions_are_contextual_and_explain_what_they_change(self):
        current = self.analyze("Uma pessoa cega precisa acessar o conteúdo de uma página web. Quero adaptar o material.")
        for question in current["questions"]:
            self.assertTrue(question["context_label"])
            self.assertTrue(question["reason"])
            self.assertTrue(question["candidate_component_ids"])
            self.assertNotEqual(question["label"], "Quais dificuldades ou necessidades você percebe?")
        self.assertFalse(any(row["field"] == "ambientes" for row in current["questions"]))

    def test_blocked_route_does_not_generate_questions_to_enable_it(self):
        self.analyze("Uma pessoa cega precisa acessar conteúdo digital em uma página web. Quero adaptar o material.")
        self.engine.update_context({"recursos_impedidos": ["REC-LEITOR-DE-TELA"]})
        self.assertNotIn("PAD-CONTEUDO-WEB-EQUIVALENTE", [row["id"] for row in self.engine._dialogue_routes(self.engine.current["context"])])
        self.assertFalse(any("REC-LEITOR-DE-TELA" in row.get("concept_ids", []) for row in self.engine.missing_questions()))

    def test_conditional_recommendation_reuses_existing_knowledge_without_inventing_resources(self):
        before_components = copy.deepcopy(self.engine.components)
        before_knowledge = copy.deepcopy(self.engine.knowledge)
        self.analyze("Uma pessoa cega precisa acessar conteúdo digital de serviços públicos em uma página web. Quero adaptar o material.")
        self.engine.update_context({"mapping_confirmed": True, "transfer_confirmed": True})
        result = self.engine.generate()
        self.assertEqual(result["decision"]["status"], "GERADA_PARCIAL")
        config = next(row for row in result["decision"]["configuracao_modal"] if row["component_id"] == "PAD-CONTEUDO-WEB-EQUIVALENTE")
        self.assertEqual(config["availability_status"], "CONDICIONAL_A_CONFIRMACAO")
        self.assertEqual(config["confirmed_resource_ids"], [])
        self.assertIn("K10", config["knowledge_ids"])
        self.assertTrue(any("Antes de aplicar" in text for text in config["conditions"]))
        self.assertTrue(result["execution_evidence"]["access_requirements"])
        self.assertTrue(any(row["access_requirement_witnesses"] for row in result["execution_evidence"]["retrieval"]))
        self.assertEqual(self.engine.components, before_components)
        self.assertEqual(self.engine.knowledge, before_knowledge)

    def test_changing_subject_does_not_change_the_retrieval_requirement(self):
        ids = []
        for subject in ("serviços públicos", "agricultura", "uma exposição cultural"):
            self.engine.start_free_context()
            current = self.analyze(f"Uma pessoa cega precisa acessar conteúdo digital sobre {subject} em uma página web. Quero adaptar o material.")
            ids.append((current["context"]["raw"]["necessidades"], [row["id"] for row in self.engine._dialogue_routes(self.engine.current["context"])]))
        self.assertEqual(ids[0], ids[1])
        self.assertEqual(ids[1], ids[2])

    def test_shared_text_does_not_assign_the_nonvisual_route_to_deaf_participants(self):
        current = self.analyze("Uma turma precisa acessar conteúdo digital sobre agricultura. Há uma pessoa cega e duas pessoas surdas. Quero que todos acompanhem a página web.")
        participants = copy.deepcopy(current["participations"])
        deaf = next(row for row in participants if row.get("grupo_rotulo") == "surdas")
        blind = next(row for row in participants if row.get("grupo_rotulo") == "cega")
        deaf["modalidade_ids"] = ["MOD-TEXTO"]
        self.engine.update_context({"participations": participants, "mapping_confirmed": True, "transfer_confirmed": True})
        result = self.engine.generate()
        coverage = {row["participant_id"]: row for row in result["decision"]["participant_coverage"]}
        self.assertNotIn("PAD-CONTEUDO-WEB-EQUIVALENTE", coverage[deaf["id"]]["component_ids"])
        self.assertNotIn("PAD-CONTEUDO-WEB-EQUIVALENTE", coverage[deaf["id"]]["conditional_component_ids"])
        self.assertIn("PAD-CONTEUDO-WEB-EQUIVALENTE", coverage[blind["id"]]["conditional_component_ids"])
        self.assertEqual(coverage[blind["id"]]["status"], "POSSIBILIDADE_CONDICIONAL_A_CONFIRMAR")

    def test_prepared_context_does_not_receive_derived_narrative_requirements(self):
        self.engine.start_context("CTX-TRANSFERENCIA-RECURSO-DIGITAL-01")
        current = self.engine.current_payload()
        self.assertEqual(current["context"]["access_requirements"], [])
        self.assertEqual(current["questions"], [])


if __name__ == "__main__":
    unittest.main()
