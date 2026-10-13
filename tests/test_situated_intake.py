"""Synthetic intake/review regressions; no empirical participant evidence."""
import copy
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from engine import DecisionEngine


NARRATIVE = ("Tenho uma turma de 20 estudantes. Alguns têm problemas de mobilidade, não, cognitivos. "
             "Eu vou apresentar slides e explicar tempos verbais. "
             "Cada estudante acessa o material em seu próprio computador. Depois faremos exercícios.")


class SituatedIntakeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = DecisionEngine()

    def setUp(self):
        self.engine.start_free_context()

    def analyze(self, text=NARRATIVE):
        return self.engine.analyze_narrative(text)["current"]

    def test_group_total_unknown_subset_and_self_correction(self):
        current = self.analyze()
        people = current["participations"]
        group = next(p for p in people if p.get("group_scope") == "TOTAL")
        affected = next(p for p in people if p.get("reported_condition"))
        self.assertEqual(group["quantidade"], 20)
        self.assertIsNone(affected["quantidade"])
        self.assertEqual(affected["parent_group_id"], group["id"])
        self.assertEqual(affected["caracteristica_ids"], [])
        self.assertEqual(affected["modalidade_ids"], [])
        self.assertEqual(affected["recurso_operado_ids"], [])
        statements = current["context"]["assertions"]
        retired = next(a for a in statements if a["kind"] == "reported_condition" and a["value"] == "mobilidade")
        self.assertEqual(retired["state"], "RETIRADO_POR_CORRECAO")
        self.assertTrue(any(a.get("supersedes") == retired["id"] for a in statements))
        self.assertEqual(current["context"]["access_requirements"], [])

    def test_original_spoken_correction_after_the_replacement(self):
        current = self.analyze("Eu tenho uma turma onde eu tenho alunos de, sei lá, eu tenho uma turma de 20 alunos e dentro deles eu tenho alunos com dificuldade de mobilidade, deficiência cognitiva, na verdade. E eu queria entender como é que eu faço pra eles aprenderem um determinado conteúdo que eu tô querendo ensinar numa aula.")
        group = next(p for p in current["participations"] if p.get("group_scope") == "TOTAL")
        affected = next(p for p in current["participations"] if p.get("reported_condition"))
        self.assertEqual(group["quantidade"], 20)
        self.assertEqual(affected["parent_group_id"], group["id"])
        self.assertEqual(affected["caracteristica_ids"], [])
        self.assertTrue(any(a["value"] == "mobilidade" and a["state"] == "RETIRADO_POR_CORRECAO" for a in current["context"]["assertions"]))

    def test_reported_difficulty_is_not_asked_again_as_if_missing(self):
        current = self.analyze("Eu tenho uma turma de 20 estudantes e alguns têm deficiência cognitiva. Quero apresentar slides enquanto explico e depois os alunos vão acessar o material no próprio computador. Eles têm dificuldade de lembrar a informação e retomar a atividade.")
        self.assertNotIn("TAR-REVISAR-E-CONFIRMAR", current["context"]["raw"]["tarefas"])
        self.assertEqual(len(current["context"]["situations"]), 2)
        question = next(q for q in current["questions"] if q["field"] == "observation_scope")
        self.assertIn("lembrar", question["label"])
        self.assertFalse(any(q["field"] == "functional_observation" for q in current["questions"]))
        result = self.engine.update_context({"question_answers": [{"question_id": question["id"], "value": question["options"][0]["id"]}]})
        assertion = next(a for a in result["context"]["assertions"] if a["kind"] == "functional_observation" and a["state"] != "RETIRADO_POR_CORRECAO")
        self.assertTrue(assertion["situation_id"])
        self.assertNotEqual(assertion["subject_id"], result["context"]["id"])

    def test_three_valued_facts_remain_scoped_and_can_be_revised(self):
        current = self.analyze()
        situation = next(s for s in current["context"]["situations"] if s["kind"] == "material_access")
        participant = next(p for p in current["participations"] if p.get("reported_condition"))
        payload = {"participant_id": participant["id"], "situation_id": situation["id"], "fact_id": "FACT-RETOMADA", "value": None}
        unknown = self.engine.update_context({"situated_facts": [payload]})
        self.assertIsNone(unknown["context"]["situated_facts"][0]["value"])
        result = self.engine.update_context({"situated_facts": [{**payload, "value": False}], "mapping_confirmed": True})
        self.assertEqual(len(result["context"]["situated_facts"]), 1)
        self.assertIs(result["context"]["situated_facts"][0]["value"], False)
        self.assertEqual(result["context"]["situated_facts"][0]["participant_id"], participant["id"])
        self.assertEqual(result["context"]["facts"], {})

    def test_answered_functional_observation_derives_only_for_its_scope(self):
        current = self.analyze()
        question = next(q for q in current["questions"] if q["field"] == "functional_observation")
        result = self.engine.update_context({"question_answers": [{"question_id": question["id"], "value": "Os formatos competem pela atenção"}]})
        requirements = result["context"]["access_requirements"]
        self.assertTrue(requirements)
        self.assertTrue(all(r["participant_id"] == question["participant_id"] and r["situation_ids"] == [question["situation_id"]] for r in requirements))
        self.assertTrue(all(r["assertion_ids"] for r in requirements))
        self.assertEqual(next(p for p in result["participations"] if p["id"] == question["participant_id"])["modalidade_ids"], [])

    def test_presenter_access_and_exercise_remain_distinct(self):
        current = self.analyze()
        situations = {s["kind"]: s for s in current["context"]["situations"]}
        self.assertEqual(set(situations), {"presentation", "material_access", "exercise"})
        presenter = next(p for p in current["participations"] if p["label"] == "Quem apresenta")
        self.assertEqual(presenter["papel_id"], "")
        self.assertIn("TAR-COMUNICAR-CONTEUDO-1545B38", presenter["tarefa_ids"])
        self.assertNotIn("TAR-ACESSAR-COMPREENDER-CONTEUDO-DIGITAL", presenter["tarefa_ids"])
        students = [p for p in current["participations"] if p["papel_id"] == "PAPEL-ESTUDANTE"]
        self.assertTrue(all("TAR-COMUNICAR-CONTEUDO-1545B38" not in p["tarefa_ids"] for p in students))
        self.assertEqual(situations["presentation"]["actor_ids"], [presenter["id"]])
        self.assertNotIn(presenter["id"], situations["presentation"]["recipient_ids"])
        self.assertNotIn(presenter["id"], situations["material_access"]["actor_ids"])
        self.assertEqual(situations["exercise"]["resource_ids"], [])
        self.assertEqual(situations["exercise"]["mode_ids"], [])
        self.assertEqual(situations["exercise"]["task_ids"], [])

    def test_priority_preserves_both_interactions_and_other_facts(self):
        current = self.analyze()
        priority = next(q for q in current["questions"] if q["field"] == "active_situation_id")
        self.assertEqual(len(priority["options"]), 2)
        before = copy.deepcopy(current["context"]["situations"])
        target = priority["options"][1]["id"]
        result = self.engine.update_context({"question_answers": [{"question_id": priority["id"], "value": target}]})
        self.assertEqual(result["context"]["active_situation_id"], target)
        self.assertEqual(result["context"]["situations"], before)
        self.assertFalse(any(q["field"] == "active_situation_id" for q in result["questions"]))

    def test_unknown_answer_is_not_repeated_and_total_questions_are_bounded(self):
        current = self.analyze()
        self.assertLessEqual(len(current["questions"]), 3)
        question = next(q for q in current["questions"] if q["field"] == "functional_observation")
        result = self.engine.update_context({"question_answers": [{"question_id": question["id"], "state": "UNKNOWN"}]})
        self.assertLessEqual(len(result["questions"]), 3)
        self.assertNotIn(question["id"], {q["id"] for q in result["questions"]})
        result = self.engine.update_context({"objetivo": "Acompanhar a explicação e acessar o material"})
        self.assertNotIn(question["id"], {q["id"] for q in result["questions"]})

    def test_questions_survive_missing_patterns(self):
        prior = self.engine.components
        try:
            self.engine.components = []
            current = self.analyze()
            self.assertTrue(any(q["field"] == "functional_observation" for q in current["questions"]))
            self.assertIn("TAR-COMUNICAR-CONTEUDO-1545B38", current["context"]["raw"]["tarefas"])
            self.assertFalse(any(q["field"] == "tarefas" for q in current["questions"]))
        finally:
            self.engine.components = prior

    def test_digital_intention_does_not_create_equipment(self):
        current = self.analyze("Quero explicar um assunto para uma turma de vinte estudantes.")
        question = next(q for q in current["questions"] if q["field"] == "digital_use")
        result = self.engine.update_context({"question_answers": [{"question_id": question["id"], "value": "consider"}]})
        self.assertEqual(result["context"]["raw"]["recursos_disponiveis"], [])
        self.assertEqual(result["context"]["raw"]["recursos_digitais"], [])
        self.assertTrue(any(a["kind"] == "digital_use" and a["value"] == "consider" for a in result["context"]["assertions"]))

    def test_planned_equipment_is_not_available(self):
        current = self.analyze("Uma pessoa precisa acessar uma página. Quero comprar um computador para isso.")
        self.assertNotIn("REC-COMPUTADOR", current["context"]["raw"]["recursos_disponiveis"])
        self.assertIn("REC-COMPUTADOR", current["context"]["raw"]["recursos_propostos"])

    def test_remove_replace_add_keep_unrelated_evidence_and_invalidate(self):
        current = self.analyze()
        condition = next(a for a in current["context"]["assertions"] if a["kind"] == "reported_condition" and a["state"] != "RETIRADO_POR_CORRECAO")
        group = next(a for a in current["context"]["assertions"] if a["kind"] == "group_count")
        self.engine.update_context({"mapping_confirmed": True})
        self.engine.current["last_result"] = {"sentinel": True}
        result = self.engine.update_context({"assertion_changes": [{"op": "remove", "id": condition["id"]},
            {"op": "replace", "id": group["id"], "assertion": {"value": 21}}]})
        self.assertFalse(result["mapping_confirmed"])
        self.assertIsNone(result["last_result"])
        self.assertEqual(len(result["context"]["situations"]), 3)
        self.assertTrue(any(a.get("supersedes") == group["id"] and a["value"] == 21 for a in result["context"]["assertions"]))
        self.assertFalse(any(p.get("reported_condition") for p in result["participations"]))
        target = result["context"]["situations"][1]
        person = next(p for p in result["participations"] if p.get("group_scope") == "TOTAL")
        result = self.engine.update_context({"assertion_changes": [{"op": "add", "assertion": {
            "subject_id": person["id"], "situation_id": target["id"], "kind": "functional_observation",
            "value": "Alguns não conseguem localizar o material", "source_text": "Resposta durante a revisão"}}]})
        self.assertTrue(any(a["kind"] == "functional_observation" and a["situation_id"] == target["id"] for a in result["context"]["assertions"]))

    def test_invalid_review_is_atomic(self):
        current = self.analyze()
        before = copy.deepcopy(self.engine.current)
        condition = next(a for a in current["context"]["assertions"] if a["kind"] == "reported_condition" and a["state"] != "RETIRADO_POR_CORRECAO")
        with self.assertRaises(ValueError):
            self.engine.update_context({"assertion_changes": [{"op": "remove", "id": condition["id"]},
                {"op": "add", "assertion": {"kind": "task", "value": "invented"}}]})
        self.assertEqual(self.engine.current, before)

    def test_removed_condition_does_not_return_on_unrelated_review(self):
        current = self.analyze()
        condition = next(a for a in current["context"]["assertions"] if a["kind"] == "reported_condition" and a["state"] != "RETIRADO_POR_CORRECAO")
        self.engine.update_context({"assertion_changes": [{"op": "remove", "id": condition["id"]}]})
        result = self.engine.update_context({"objetivo": "Acompanhar conteúdo", "mapping_confirmed": True})
        self.assertFalse(any(p.get("reported_condition") for p in result["participations"]))
        self.assertFalse(any(a["kind"] == "reported_condition" and a["state"] != "RETIRADO_POR_CORRECAO" for a in result["context"]["assertions"]))
        self.assertEqual(next(a for a in result["context"]["assertions"] if a["id"] == condition["id"])["state"], "RETIRADO_POR_CORRECAO")

    def test_remove_participant_retires_only_their_evidence_and_facts(self):
        current = self.analyze()
        person = next(p for p in current["participations"] if p.get("reported_condition"))
        situation = next(s for s in current["context"]["situations"] if s["kind"] == "material_access")
        self.engine.update_context({"situated_facts": [{"participant_id": person["id"], "situation_id": situation["id"], "fact_id": "FACT-RETOMADA", "value": True}]})
        result = self.engine.update_context({"participations": [p for p in current["participations"] if p["id"] != person["id"]]})
        result = self.engine.update_context({"objetivo": "Ainda acompanhar conteúdo"})
        self.assertNotIn(person["id"], {p["id"] for p in result["participations"]})
        self.assertFalse(any(a["subject_id"] == person["id"] and a["state"] != "RETIRADO_POR_CORRECAO" for a in result["context"]["assertions"]))
        self.assertFalse(any(f["participant_id"] == person["id"] for f in result["context"]["situated_facts"]))
        access = next(s for s in result["context"]["situations"] if s["kind"] == "material_access")
        self.assertNotIn(person["id"], access["actor_ids"])
        self.assertIn("TAR-ACESSAR-COMPREENDER-CONTEUDO-DIGITAL", access["task_ids"])

    def test_unknown_can_be_replaced_without_recreating_old_answers(self):
        current = self.analyze()
        question = next(q for q in current["questions"] if q["field"] == "functional_observation")
        self.engine.update_context({"question_answers": [{"question_id": question["id"], "state": "UNKNOWN"}]})
        self.engine.update_context({"question_answers": [{"question_id": question["id"], "value": "Os formatos competem pela atenção"}]})
        result = self.engine.update_context({"question_answers": [{"question_id": question["id"], "value": "Dificuldade de retomar a atividade"}]})
        current_observations = [a for a in result["context"]["assertions"] if a["kind"] == "functional_observation" and a["state"] != "RETIRADO_POR_CORRECAO"]
        self.assertEqual(len(current_observations), 1)
        self.assertEqual(current_observations[0]["value"], "Dificuldade de retomar a atividade")
        self.assertEqual(current_observations[0]["subject_id"], question["participant_id"])
        self.assertEqual(current_observations[0]["situation_id"], question["situation_id"])
        self.assertEqual(len([a for a in result["context"]["question_answers"] if a["question_id"] == question["id"]]), 1)

    def test_removing_one_scoped_task_preserves_another_actor(self):
        current = self.analyze()
        situation = next(s for s in current["context"]["situations"] if s["kind"] == "material_access")
        person = next(p for p in current["participations"] if p.get("reported_condition"))
        task = next(a for a in current["context"]["assertions"] if a["kind"] == "task" and a["subject_id"] == person["id"] and a["situation_id"] == situation["id"])
        result = self.engine.update_context({"assertion_changes": [{"op": "remove", "id": task["id"]}]})
        access = next(s for s in result["context"]["situations"] if s["id"] == situation["id"])
        self.assertIn(task["value"], access["task_ids"])
        self.assertNotIn(person["id"], access["actor_ids"])
        self.assertTrue(any(a["kind"] == "task" and a["value"] == task["value"] and a["state"] != "RETIRADO_POR_CORRECAO" for a in result["context"]["assertions"]))

    def test_turma_alone_does_not_create_comprehension_need(self):
        current = self.analyze("Tenho uma turma de vinte estudantes e vou explicar um assunto.")
        self.assertNotIn("NEC-APOIAR-COMPREENSAO-TURMA", current["context"]["raw"]["necessidades"])

    def test_old_example_has_real_scope_for_followup_facts(self):
        current = self.engine.start_context("CTX-DEMO-WEB-LEITOR-TELA")
        situation = current["context"]["situations"][0]
        person = current["participations"][0]
        result = self.engine.update_context({"situated_facts": [{"participant_id": person["id"],
            "situation_id": situation["id"], "fact_id": "FACT-CONFERIR", "label": "Condição apresentada", "value": None}]})
        self.assertEqual(result["context"]["situated_facts"][0]["label"], "Condição apresentada")
        self.assertEqual(result["context"]["active_situation_id"], situation["id"])

    def test_old_example_uses_existing_role_label_not_session_id(self):
        current = self.engine.start_context("CTX-TRANSFERENCIA-RECURSO-DIGITAL-01")
        self.assertTrue(current["participations"])
        for person in current["participations"]:
            self.assertEqual(person["label"], self.engine.label(person["papel_id"]))
            self.assertNotIn("PART-CASO", person["label"])

    def test_unknown_task_keeps_explicit_participants_without_inventing_action(self):
        current = self.analyze("Sou mediadora e quero ensinar pessoas a usar o Google Forms. Algumas precisam de apoio para perceber os campos do formulário. Há um computador disponível.")
        situation = current["context"]["situations"][0]
        self.assertTrue(situation["participant_ids"])
        mediator = next(p for p in current["participations"] if p["papel_id"] == "PAPEL-MEDIADOR")
        self.assertIn(mediator["id"], situation["participant_ids"])
        self.assertEqual(situation["actor_ids"], [])
        self.assertNotIn("REC-COMPUTADOR-DATASHOW", current["context"]["raw"]["recursos_disponiveis"])

    def test_aggregate_equipment_requires_both_components(self):
        for equipment in ("um computador", "um projetor"):
            current = self.analyze("Uma pessoa vai acessar uma página. Está disponível " + equipment + ".")
            self.assertNotIn("REC-COMPUTADOR-DATASHOW", current["context"]["raw"]["recursos_disponiveis"])
        current = self.analyze("Uma pessoa vai acessar uma página. Estão disponíveis um computador e um projetor.")
        self.assertIn("REC-COMPUTADOR-DATASHOW", current["context"]["raw"]["recursos_disponiveis"])

    def test_theme_does_not_change_functional_mapping(self):
        first = self.analyze()
        self.engine.start_free_context()
        second = self.analyze(NARRATIVE.replace("tempos verbais", "serviços públicos"))
        normalize = lambda current: [(s["kind"], s["task_ids"], s["resource_ids"], s["mode_ids"]) for s in current["context"]["situations"]]
        self.assertEqual(normalize(first), normalize(second))


if __name__ == "__main__":
    unittest.main()
