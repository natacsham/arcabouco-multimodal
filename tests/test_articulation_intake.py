"""Synthetic held-out narratives. No response templates or case IDs at runtime."""
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from engine import DecisionEngine

CASES = {row["id"]: row for row in json.loads((ROOT / "tests/fixtures/articulation_transfer_cases.json").read_text(encoding="utf-8"))}


class ArticulationIntakeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = DecisionEngine()

    def analyze(self, case_or_text):
        text = CASES.get(case_or_text, {}).get("narrative", case_or_text)
        self.engine.start_free_context()
        self.engine.analyze_narrative(text)
        return self.engine.current["context"], self.engine.current["participations"]

    def facts(self, context, person):
        return {f["fact_id"].rsplit("#", 1)[-1]: f["value"] for f in context["situated_facts"] if f["participant_id"] == person["id"]}

    def test_catalogue_is_an_action_not_a_new_domain_recipe(self):
        c, people = self.analyze("catalogue_sequence")
        self.assertEqual(c["tarefas"], ["TAR-OPERAR-SISTEMA"])
        situation = next(s for s in c["situations"] if s["id"] == c["active_situation_id"])
        self.assertTrue(situation["preparation_actor_ids"])
        self.assertTrue(set(situation["actor_ids"]).isdisjoint(situation["preparation_actor_ids"]))
        receiver = next(p for p in people if p["id"] in situation["actor_ids"])
        self.assertTrue(self.facts(c, receiver)["CanReadText"])
        self.assertTrue(any(r["matrix_id"] == "MF-04" and r["participant_id"] == receiver["id"] for r in c["access_requirements"]))
        keys = [(r["matrix_id"], r["participant_id"], r["trigger_group_id"]) for r in c["access_requirements"]]
        self.assertEqual(len(keys), len(set(keys)))
        self.assertFalse(any(q["field"] in {"tarefas", "barreira_ou_necessidade", "requester_relation"} for q in self.engine.missing_questions()))

    def test_preparation_is_not_recipient_activity_or_ready_material(self):
        c, people = self.analyze("recorded_content_access")
        self.assertEqual(c["tarefas"], ["TAR-ACESSAR-COMPREENDER-CONTEUDO-DIGITAL"])
        situation = c["situations"][0]
        self.assertEqual(len(situation["actor_ids"]), 2)
        self.assertEqual(len(situation["preparation_actor_ids"]), 1)
        self.assertTrue(any(a.get("activity_phase") == "PREPARATION" for a in c["assertions"]))
        self.assertIn("REC-DESCRICAO-TEXTUAL", c["recursos_propostos"])
        self.assertNotIn("REC-DESCRICAO-TEXTUAL", c["recursos_disponiveis"])

    def test_personal_routes_are_not_broadcast(self):
        c, people = self.analyze("recorded_content_access")
        blind = next(p for p in people if p.get("reported_condition", {}).get("text") == "cega")
        deaf = next(p for p in people if p.get("reported_condition", {}).get("text") == "surda")
        self.assertEqual(self.facts(c, blind), {"AudioUsable": True, "UsesScreenReader": True})
        self.assertEqual(self.facts(c, deaf), {"CanReadText": True})
        self.assertNotIn("REC-LEITOR-DE-TELA", deaf["recurso_operado_ids"])
        self.assertFalse(any(r["resource_id"] == "REC-LEITOR-DE-TELA" for r in c["situations"][0]["resource_states"]))
        by_id = {a["id"]: a for a in c["assertions"]}
        for requirement in c["access_requirements"]:
            self.assertTrue(requirement["assertion_ids"])
            for identifier in requirement["assertion_ids"]:
                self.assertEqual(by_id[identifier]["subject_id"], requirement["participant_id"])

    def test_confirmation_preserves_scoped_facts_and_requirements(self):
        for case in CASES:
            with self.subTest(case=case):
                c, _ = self.analyze(case)
                facts = {(f["participant_id"], f["situation_id"], f["fact_id"]): f["value"] for f in c["situated_facts"]}
                requirements = c["access_requirements"]
                self.engine.update_context({"mapping_confirmed": True})
                after = self.engine.current["context"]
                self.assertEqual(facts, {(f["participant_id"], f["situation_id"], f["fact_id"]): f["value"] for f in after["situated_facts"]})
                self.assertEqual(requirements, after["access_requirements"])
                self.assertTrue(all(f["state"] == "CONFIRMADO" for f in after["situated_facts"]))

    def test_audio_negation_affects_only_the_explicit_person(self):
        text = CASES["recorded_content_access"]["narrative"].replace("consegue ouvir áudio", "não consegue ouvir áudio")
        c, people = self.analyze(text)
        blind = next(p for p in people if p.get("reported_condition", {}).get("text") == "cega")
        deaf = next(p for p in people if p.get("reported_condition", {}).get("text") == "surda")
        self.assertIs(self.facts(c, blind)["AudioUsable"], False)
        self.assertTrue(self.facts(c, deaf)["CanReadText"])

    def test_unknown_answer_keeps_requirements_from_active_reported_conditions(self):
        c, _ = self.analyze("recorded_content_access")
        before = {(r["matrix_id"], r["participant_id"], tuple(r["assertion_ids"])) for r in c["access_requirements"]}
        questions = self.engine.missing_questions()
        self.assertTrue(questions)
        self.engine.update_context({"question_answers": [{"question_id": questions[0]["id"], "state": "UNKNOWN", "value": "unknown"}]})
        after = self.engine.current["context"]
        self.assertEqual(before, {(r["matrix_id"], r["participant_id"], tuple(r["assertion_ids"])) for r in after["access_requirements"]})
        self.assertFalse(any(q["id"] == questions[0]["id"] for q in self.engine.missing_questions()))

    def test_retracting_condition_removes_only_its_access_requirement(self):
        c, people = self.analyze("recorded_content_access")
        blind = next(p for p in people if p.get("reported_condition", {}).get("text") == "cega")
        condition = next(a for a in c["assertions"] if a["subject_id"] == blind["id"] and a["kind"] == "reported_condition")
        condition["state"] = "RETIRADO_POR_CORRECAO"
        self.engine.derive_access_requirements("", observations_only=True)
        self.assertEqual({r["matrix_id"] for r in c["access_requirements"]}, {"MF-11"})

    def test_same_draft_and_limited_keyboard_effort_are_distinct(self):
        c, people = self.analyze("dictation_review_control")
        self.assertEqual(len(people), 1)
        self.assertEqual(len(c["situations"]), 1)
        self.assertEqual(set(c["tarefas"]), {"TAR-PRODUZIR-CONTEUDO-MULTIMODAL", "TAR-REVISAR-E-CONFIRMAR"})
        facts = self.facts(c, people[0])
        for fact in ("CanUseSpeech", "CanUseKeyboard", "CanReviewVisualText", "CanCorrect", "ControlsCompletion", "SameEditableTextDraft", "EditableText", "Display"):
            self.assertIs(facts[fact], True)
        self.assertIs(facts["KeyboardEffortAcceptable"], False)
        for unknown in ("LearningCommunicationContext", "CanVerifyMeaning", "SpeechEffortAcceptable", "SpeechInputUsable"):
            self.assertNotIn(unknown, facts)

    def test_no_diagnosis_implies_a_reading_ability(self):
        c, people = self.analyze("Sou mediadora. Uma participante é cega e outra é surda. Vou disponibilizar material para consulta individual.")
        self.assertEqual(c["situated_facts"], [])
        self.assertFalse(any(p["recurso_operado_ids"] for p in people))

    def test_explicit_nonworking_speech_input_is_not_hidden_by_existing_device(self):
        text = CASES["dictation_review_control"]["narrative"].replace(
            "Estou numa sala silenciosa, sem outras pessoas ouvindo, e posso controlar quando começar, parar e confirmar o registro.",
            "Agora há ruído e o reconhecimento de fala não funciona neste ambiente; mantenho controle para corrigir e confirmar o registro.")
        c, people = self.analyze(text)
        self.assertIs(self.facts(c, people[0])["SpeechInputUsable"], False)
        self.assertIs(self.facts(c, people[0])["KeyboardEffortAcceptable"], False)

    def test_second_persons_device_is_not_a_shared_resource(self):
        c, people = self.analyze("recorded_content_access")
        deaf = next(p for p in people if p.get("reported_condition", {}).get("text") == "surda")
        facts = [a for a in c["assertions"] if a.get("value") == "REC-LEITOR-DE-TELA" and a["kind"] == "resource_available"]
        self.assertTrue(facts)
        self.assertFalse(any(a["subject_id"] in {c["id"], deaf["id"]} for a in facts))

    def test_non_scenario_paraphrase_and_topic_change(self):
        c, people = self.analyze("Preciso redigir um relatório no computador e revisar antes de enviar. Consigo falar e ler a tela. Consigo usar o teclado para pequenas correções.")
        self.assertEqual(set(c["tarefas"]), {"TAR-PRODUZIR-CONTEUDO-MULTIMODAL", "TAR-REVISAR-E-CONFIRMAR"})
        self.assertTrue(self.facts(c, people[0])["CanCorrect"])
        self.assertLessEqual(len(self.engine.missing_questions()), 3)

    def test_prepare_does_not_approve_or_invent_perception(self):
        c, people = self.analyze("Sou mediadora. Uma participante é cega. Posso preparar descrição textual. Quero disponibilizar conteúdo para consulta individual.")
        self.assertIn("REC-DESCRICAO-TEXTUAL", c["recursos_propostos"])
        self.assertNotIn("REC-DESCRICAO-TEXTUAL", c["recursos_disponiveis"])
        self.assertEqual(c["situated_facts"], [])

    def test_negated_preparation_is_not_a_responsible_actor(self):
        text = CASES["recorded_content_access"]["narrative"].replace(
            "Posso editar o vídeo, preparar texto e acrescentar descrição das informações visuais.",
            "Não posso preparar ou adaptar o material.")
        c, people = self.analyze(text)
        self.assertFalse(any(s.get("preparation_actor_ids") for s in c["situations"]))
        self.assertFalse(any(a.get("activity_phase") == "PREPARATION" and a["state"] == "RELATADO" for a in c["assertions"]))
        self.assertFalse(any(f["fact_id"].endswith("CanPrepareMaterial") for f in c["situated_facts"]))
        self.assertTrue(any(p["papel_id"] == "PAPEL-MEDIADOR" for p in people))

    def test_explicit_later_correction_revokes_only_preparation(self):
        c, people = self.analyze(CASES["recorded_content_access"]["narrative"]
                                + " Correção: não posso preparar ou adaptar o material.")
        self.assertFalse(any(s.get("preparation_actor_ids") for s in c["situations"]))
        self.assertNotEqual(c["requester_relation"], "prepare")
        self.assertEqual({r["matrix_id"] for r in c["access_requirements"]}, {"MF-01", "MF-11"})
        self.assertTrue(any(p["papel_id"] == "PAPEL-MEDIADOR" for p in people))

    def test_removing_primary_preparation_statement_revokes_derived_actor(self):
        c, _ = self.analyze("recorded_content_access")
        primary = next(a for a in c["assertions"] if a.get("activity_phase") == "PREPARATION"
                       and not a.get("preparation_authority_id"))
        self.assertTrue(any(a.get("preparation_authority_id") == primary["id"] for a in c["assertions"]))
        self.engine.update_context({"assertion_changes": [{"op": "remove", "id": primary["id"]}]})
        current = self.engine.current["context"]
        self.assertFalse(any(s.get("preparation_actor_ids") for s in current["situations"]))
        self.assertEqual({r["matrix_id"] for r in current["access_requirements"]}, {"MF-01", "MF-11"})

    def test_editing_primary_preparation_to_negative_revokes_actor(self):
        c, _ = self.analyze("recorded_content_access")
        primary = next(a for a in c["assertions"] if a.get("activity_phase") == "PREPARATION"
                       and not a.get("preparation_authority_id"))
        self.engine.update_context({"assertion_changes": [{"op": "replace", "id": primary["id"],
            "assertion": {"value": "Não posso preparar ou adaptar o material.",
                          "source_text": "Não posso preparar ou adaptar o material."}}]})
        self.assertFalse(any(s.get("preparation_actor_ids") for s in self.engine.current["context"]["situations"]))

    def test_computer_alone_does_not_confirm_display_or_editable_text(self):
        c, people = self.analyze("Preciso escrever um documento e revisar antes de enviar. Tenho computador e teclado.")
        facts = self.facts(c, people[0])
        self.assertNotIn("Display", facts)
        self.assertNotIn("EditableText", facts)


if __name__ == "__main__":
    unittest.main()
