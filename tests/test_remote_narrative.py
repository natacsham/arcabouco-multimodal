"""Synthetic intake regressions, not pre-registered recommendations or user evidence."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from engine import DecisionEngine
from situated_context import ACTIVE_STATES


ORIGINAL = (
    "Sou uma professora do 1 ano do ensino fundamental I, onde tenho uma turma de 25 alunos que estão sendo alfabetizados. "
    "Tenho 3 alunos dessa turma com Transtorno do Espectro Autista. "
    "Estou querendo ministrar o conteudo referente a introdução fonemica. "
    "No entanto, devido a condições climáticas as aulas não podem ser presenciais. Estão sendo remotas. "
    "Por isso, vou precisar do apoio de um mediador, os pais, por exemplo, para que possam me apoiar "
    "indiretamente na condução da explicação e na realização das atividades."
)


class RemoteNarrativeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = DecisionEngine()

    def analyze(self, narrative=ORIGINAL):
        self.engine.start_free_context()
        return self.engine.analyze_narrative(narrative)["current"]

    def test_class_subgroup_diagnosis_do_not_infer_abilities(self):
        current = self.analyze()
        people = current["participations"]
        total = next(p for p in people if p.get("group_scope") == "TOTAL")
        subgroup = next(p for p in people if p.get("reported_condition"))
        self.assertEqual(total["quantidade"], 25)
        self.assertEqual(subgroup["quantidade"], 3)
        self.assertEqual(subgroup["parent_group_id"], total["id"])
        self.assertEqual(subgroup["reported_condition"]["text"], "Transtorno do Espectro Autista")
        for field in ("caracteristica_ids", "modalidade_ids", "recurso_operado_ids"):
            self.assertEqual(subgroup[field], [])
        self.assertEqual(current["context"]["situated_facts"], [])
        self.assertEqual(current["context"]["access_requirements"], [])

    def test_instruction_has_teacher_actor_and_pupils_recipients(self):
        current = self.analyze()
        teacher = next(p for p in current["participations"] if p["papel_id"] == "PAPEL-PROFESSORA")
        pupils = [p for p in current["participations"] if p["papel_id"] == "PAPEL-ESTUDANTE"]
        situation = next(s for s in current["context"]["situations"] if s["kind"] == "instruction")
        self.assertEqual(situation["actor_ids"], [teacher["id"]])
        self.assertEqual(set(situation["recipient_ids"]), {p["id"] for p in pupils})
        self.assertEqual(current["context"]["requester_participation_id"], teacher["id"])
        self.assertEqual(situation["task_ids"], ["TAR-COMUNICAR-CONTEUDO-1545B38"])
        self.assertTrue(all(not p["tarefa_ids"] for p in pupils))

    def test_remote_does_not_invent_classroom_hardware_or_ava(self):
        current = self.analyze()
        context = current["context"]
        self.assertEqual(context["situations"][0]["delivery_mode"], "REMOTE")
        for field in ("ambientes", "recursos_digitais", "recursos_disponiveis", "modalidades_disponiveis"):
            self.assertEqual(context["raw"][field], [])
        delivery = [a for a in context["assertions"] if a.get("delivery_mode")]
        self.assertEqual([a["delivery_mode"] for a in delivery], ["REMOTE"])
        self.assertEqual(delivery[0]["source_text"], "remotas")

    def test_family_support_is_one_proposed_mediator_not_preparer(self):
        current = self.analyze()
        helpers = [p for p in current["participations"] if p["papel_id"] == "PAPEL-MEDIADOR"]
        self.assertEqual(len(helpers), 1)
        self.assertEqual(helpers[0]["participation_status"], "PROPOSTO")
        self.assertIn("pais", helpers[0]["apoio_informado"])
        situation = current["context"]["situations"][0]
        self.assertEqual(situation["support_participant_ids"], [helpers[0]["id"]])
        self.assertNotIn(helpers[0]["id"], situation["actor_ids"])
        self.assertNotIn(helpers[0]["id"], situation.get("preparation_actor_ids", []))
        rows = [a for a in current["context"]["assertions"] if a["subject_id"] == helpers[0]["id"] and a["kind"] == "participation"]
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["state"], "INFERIDO_PARA_CONFIRMACAO")

    def test_generic_phone_does_not_imply_audio_and_haptic_orientation(self):
        current = self.analyze(ORIGINAL + " As famílias usam celular para acessar o material.")
        resources = current["context"]["raw"]["recursos_disponiveis"]
        self.assertIn("REC-SMARTPHONE", resources)
        self.assertNotIn("REC-SMARTPHONE-AUDIO-HAPTICO", resources)

    def test_class_count_without_noun_precedes_subgroup_count(self):
        current = self.analyze("Sou professora e tenho uma turma de 30. Tenho 3 alunos com TEA. Quero ministrar o conteúdo.")
        self.assertEqual(next(p for p in current["participations"] if p.get("group_scope") == "TOTAL")["quantidade"], 30)
        self.assertEqual(next(p for p in current["participations"] if p.get("reported_condition"))["quantidade"], 3)

    def test_new_diagnosis_and_delivery_assertions_have_exact_source_spans(self):
        current = self.analyze()
        rows = [a for a in current["context"]["assertions"] if "source_start" in a]
        self.assertGreaterEqual(len(rows), 3)
        for row in rows:
            self.assertEqual(ORIGINAL[row["source_start"]:row["source_end"]], row["source_text"])

    def test_functional_question_is_scoped_and_not_diagnostic_prescription(self):
        current = self.analyze()
        self.assertLessEqual(len(current["questions"]), 3)
        subgroup = next(p for p in current["participations"] if p.get("reported_condition"))
        question = next(q for q in current["questions"] if q["field"] == "functional_observation")
        self.assertEqual(question["participant_id"], subgroup["id"])
        self.assertIn("esses 3 estudantes acompanham e respondem nas aulas remotas", question["label"])
        self.assertNotIn("TEA informado", question["label"])
        self.assertFalse(any(q["field"] == "digital_use" for q in current["questions"]))
        self.assertTrue(any(q["field"] == "recursos_digitais" for q in current["questions"]))
        self.assertFalse(any(q["field"] in {"tarefas", "barreira_ou_necessidade"} for q in current["questions"]))

    def test_unknown_functional_answer_is_not_a_confirmation_or_loop(self):
        current = self.analyze()
        question = next(q for q in current["questions"] if q["field"] == "functional_observation")
        after = self.engine.update_context({"question_answers": [{"question_id": question["id"], "state": "UNKNOWN"}]})
        self.assertNotIn(question["id"], {q["id"] for q in after["questions"]})
        self.assertEqual(after["context"]["access_requirements"], [])

    def test_grade_and_subject_change_do_not_dispatch_another_task(self):
        first = self.analyze()
        fourth = self.analyze(ORIGINAL.replace("1 ano", "4 ano").replace("25 alunos", "30 alunos")
                              .replace("introdução fonemica", "derivação por sufixação em Língua Portuguesa"))
        other = self.analyze(ORIGINAL.replace("introdução fonemica", "um assunto de Ciências"))
        self.assertEqual(first["context"]["raw"]["tarefas"], fourth["context"]["raw"]["tarefas"])
        self.assertEqual(first["context"]["raw"]["tarefas"], other["context"]["raw"]["tarefas"])
        self.assertEqual(next(p for p in fourth["participations"] if p.get("group_scope") == "TOTAL")["quantidade"], 30)
        self.assertIn("sufixação", fourth["context"]["texto_curto"])

    def test_explicit_in_person_is_distinct_from_negated_in_person(self):
        for statement, expected in (("As aulas são presenciais.", "IN_PERSON"),
                                    ("As aulas não são presenciais. São remotas.", "REMOTE"),
                                    ("As aulas não são presenciais, são remotas.", "REMOTE"),
                                    ("Não será presencial; será remoto.", "REMOTE"),
                                    ("Não será presencial mas remoto.", "REMOTE"),
                                    ("As aulas são remotas e presenciais.", "MIXED")):
            current = self.analyze("Sou uma professora e tenho uma turma de 30 alunos. Quero ministrar o conteúdo. " + statement)
            self.assertEqual(current["context"]["situations"][0]["delivery_mode"], expected)

    def test_unknown_negated_diagnosis_not_affirmed(self):
        for statement in ("Não sei se tenho 3 alunos com TEA.", "Não tenho 3 alunos com autismo.",
                          "Talvez tenha 3 alunos com Transtorno do Espectro Autista."):
            current = self.analyze("Sou professora e tenho uma turma de 30 alunos. " + statement + " Quero ministrar o conteúdo.")
            self.assertFalse(any(p.get("reported_condition") for p in current["participations"]), statement)
            self.assertFalse(any(a["kind"] == "reported_condition" and a["state"] in ACTIVE_STATES for a in current["context"]["assertions"]))

    def test_synthetic_passive_content_form_is_recognized(self):
        current = self.analyze("Sou professora do 4 ano. Tenho uma turma de 30 alunos. Tenho 3 alunos com TEA. O conteúdo a ser ministrado são as derivações com sufixo. As aulas são remotas.")
        self.assertEqual(current["context"]["situations"][0]["kind"], "instruction")
        self.assertEqual(len([p for p in current["participations"] if p.get("reported_condition")]), 1)

    def test_review_removes_remote_assertion_without_stale_delivery_state(self):
        current = self.analyze()
        delivery = next(a for a in current["context"]["assertions"] if a.get("delivery_mode"))
        after = self.engine.update_context({"assertion_changes": [{"op": "remove", "id": delivery["id"]}]})
        self.assertNotIn("delivery_mode", after["context"]["situations"][0])
        self.assertEqual(len([p for p in after["participations"] if p.get("reported_condition")]), 1)


if __name__ == "__main__":
    unittest.main()
