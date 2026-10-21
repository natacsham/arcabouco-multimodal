"""Synthetic intake regressions; no authored scenario or new decision pattern."""
import copy
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from engine import DecisionEngine, MADO
from rdflib import Graph
from rdflib.namespace import RDF, XSD


class IntakeContextRepairTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = DecisionEngine()

    def setUp(self):
        self.engine.start_free_context()

    def analyze(self, narrative):
        return self.engine.analyze_narrative(narrative)["current"]

    def test_explicit_classroom_is_reused_instead_of_asked_again(self):
        current = self.analyze("Sou mediadora e quero ajudar uma pessoa cega a acessar conteúdo digital na sala de aula.")
        self.assertIn("AMB-SALA-DE-AULA", current["context"]["raw"]["ambientes"])
        self.assertFalse(any(q["field"] == "ambientes" for q in current["questions"]))
        material = next(q for q in current["questions"] if q["field"] == "recursos_digitais")
        self.assertIn("sala de aula", material["question"])
        self.assertNotIn("equipamento", material["question"])

    def test_bare_or_online_class_does_not_establish_physical_classroom(self):
        for narrative in ("Quero ajudar uma pessoa cega a acompanhar uma aula.",
                          "Quero ajudar uma pessoa cega a acompanhar uma aula online."):
            self.engine.start_free_context()
            current = self.analyze(narrative)
            self.assertNotIn("AMB-SALA-DE-AULA", current["context"]["raw"]["ambientes"])

    def test_mediator_and_plural_people_are_recognized_without_inventing_professor(self):
        current = self.analyze("Sou mediadora e quero ajudar pessoas a preencher um formulário digital.")
        roles = {person["papel_id"] for person in current["participations"]}
        self.assertIn("PAPEL-MEDIADOR", roles)
        self.assertIn("PAPEL-PESSOA-APOIADA", roles)
        self.assertNotIn("PAPEL-PROFESSORA", roles)
        self.assertEqual(current["context"]["requester_relation"], "support")
        # Explicit "Sou mediadora" identifies who narrates, not what help is
        # requested. Intention and profession remain separate above.
        mediator = next(p for p in current["participations"] if p["papel_id"] == "PAPEL-MEDIADOR")
        self.assertEqual(current["context"]["requester_participation_id"], mediator["id"])

    def test_requester_intention_is_not_replaced_by_profession(self):
        current = self.analyze("Sou mediadora. A pessoa que apoio vai dar aula. O que posso falar com o professor para ele fazer?")
        self.assertEqual(current["context"]["requester_relation"], "seek_guidance")
        self.assertIn("PAPEL-MEDIADOR", {person["papel_id"] for person in current["participations"]})
        self.assertIn("PAPEL-PROFESSORA", {person["papel_id"] for person in current["participations"]})
        mediator = next(p for p in current["participations"] if p["papel_id"] == "PAPEL-MEDIADOR")
        self.assertEqual(current["context"]["requester_participation_id"], mediator["id"])
        self.engine.start_free_context()
        current = self.analyze("Sou mediadora. Uma pessoa precisa preencher um formulário digital.")
        self.assertEqual(current["context"]["requester_relation"], "")

    def test_plural_groups_have_unknown_count_and_survive_update_and_rdf(self):
        current = self.analyze("Quero ensinar pessoas muito diferentes a usar o Google Forms.")
        people = next(row for row in current["participations"] if row["papel_id"] == "PAPEL-PESSOA-APOIADA")
        self.assertEqual(people["grupo_rotulo"], "pessoas")
        self.assertIsNone(people["quantidade"])
        self.assertIn("Pessoas", people["label"])
        self.assertIn("quantidade não informada", people["label"])
        payload = json.loads(json.dumps(current["participations"]))
        self.engine.update_context({"participations": payload})
        self.assertIsNone(self.engine.current_payload()["participations"][0]["quantidade"])
        graph = Graph().parse(data=self.engine.build_context_graph().serialize(format="turtle"), format="turtle")
        subject = MADO[people["id"]]
        self.assertIn((subject, RDF.type, MADO.ParticipacaoNoContexto), graph)
        self.assertIn((subject, MADO.temPapelNoContexto, MADO["PAPEL-PESSOA-APOIADA"]), graph)
        # The runtime RDF has no cardinality predicate: unknown is not serialized as one.
        self.assertFalse(any(getattr(value, "datatype", None) == XSD.integer for value in graph.objects(subject)))

    def test_plural_professions_and_reported_conditions_do_not_invent_count(self):
        for word in ("docentes", "professores", "professoras"):
            self.engine.start_free_context()
            current = self.analyze(f"{word} precisam adaptar um formulário.")
            person = next(row for row in current["participations"] if row["papel_id"] == "PAPEL-PROFESSORA")
            self.assertIsNone(person["quantidade"])
            self.assertEqual(person["grupo_rotulo"], word)
        self.engine.start_free_context()
        current = self.analyze("Quero apoiar estudantes surdos a ler uma página.")
        self.assertIsNone(next(row for row in current["participations"] if row["grupo_rotulo"] == "surdos")["quantidade"])
        self.engine.start_free_context()
        current = self.analyze("Duas professoras precisam adaptar um formulário.")
        self.assertEqual(next(row for row in current["participations"] if row["papel_id"] == "PAPEL-PROFESSORA")["quantidade"], 2)

    def test_negated_profession_does_not_add_school_role(self):
        current = self.analyze("Sou mediadora, não sou professora. Quero ajudar pessoas a preencher um formulário.")
        self.assertNotIn("PAPEL-PROFESSORA", {person["papel_id"] for person in current["participations"]})

    def test_self_report_is_preserved_without_repeating_requester_question(self):
        current = self.analyze("Eu preciso acessar uma página web e não consigo enxergar as informações.")
        self.assertEqual(current["context"]["requester_relation"], "self")
        self.assertFalse(any(q["field"] == "requester_relation" for q in current["questions"]))

    def test_requester_is_not_a_universal_profile_question(self):
        current = self.analyze("Uma pessoa precisa preencher um formulário digital e encontra campos sem rótulo.")
        self.assertFalse(any(q["field"] == "requester_relation" for q in current["questions"]))

    def test_forms_identifies_resource_but_asks_actual_action_without_ready_answer(self):
        before_patterns = copy.deepcopy(self.engine.components)
        before_knowledge = copy.deepcopy(self.engine.knowledge)
        current = self.analyze("Quero ensinar pessoas muito diferentes a usar o Google Forms.")
        self.assertEqual(current["context"]["raw"]["recursos_digitais"], ["RED-FORMULARIO"])
        self.assertEqual(current["context"]["raw"]["tarefas"], [])
        self.assertIn("ensinar", current["context"]["objetivo"])
        task = next(q for q in current["questions"] if q["field"] == "tarefas")
        self.assertIn("formulário", task["question"])
        self.assertEqual([q["label"] for q in task["options"]], ["Preencher e enviar respostas", "Criar ou adaptar o formulário",
                                                               "Ler e compreender perguntas e instruções", "Revisar respostas antes de enviar"])
        self.assertTrue(all(q["id"] in self.engine.concepts for q in task["options"]))
        self.assertEqual(self.engine.components, before_patterns)
        self.assertEqual(self.engine.knowledge, before_knowledge)

    def test_forms_explicit_action_is_not_replaced_by_reading(self):
        current = self.analyze("Quero ajudar pessoas a preencher um formulário digital no Google Forms.")
        self.assertIn("TAR-OPERAR-SISTEMA", current["context"]["raw"]["tarefas"])
        self.assertNotIn("TAR-ACESSAR-COMPREENDER-CONTEUDO-DIGITAL", current["context"]["raw"]["tarefas"])
        self.assertFalse(any(q["field"] == "tarefas" for q in current["questions"]))

    def test_unreported_school_roles_do_not_become_dialogue_options_or_conditional_roles(self):
        current = self.analyze("Quero preparar conteúdo digital para pessoas cegas e surdas usarem um formulário.")
        school_roles = {"PAPEL-PROFESSORA", "PAPEL-ESTUDANTE", "PAPEL-COLEGAS", "PAPEL-TURMA"}
        self.assertFalse(any(school_roles & set(q.get("concept_ids", [])) for q in current["questions"]))
        routes = self.engine._dialogue_routes(self.engine.current["context"])
        self.assertFalse(any(school_roles & set(route.get("required_role_ids", [])) for route in routes))
        self.engine.update_context({"mapping_confirmed": True})
        result = self.engine.generate()
        self.assertFalse(any(c["responsible_role_id"] in school_roles for c in result["decision"]["configuracao_modal"]))
        rejected = [r for r in result["execution_evidence"]["checks"] if r["rule_id"] == "required_roles" and r.get("outcome") == "FAIL"]
        self.assertTrue(rejected)

    def test_generic_adaptation_route_remains_available_without_professor(self):
        current = self.analyze("Quero ajudar uma pessoa cega a acessar informações em uma página web.")
        self.assertIn("PAD-CONTEUDO-WEB-EQUIVALENTE", {row["id"] for row in self.engine._dialogue_routes(self.engine.current["context"])})
        self.assertNotIn("PAPEL-PROFESSORA", {row["papel_id"] for row in current["participations"]})

    def test_requester_link_and_field_replacement_preserve_other_information(self):
        current = self.analyze("Sou mediadora e quero ajudar uma pessoa cega a acessar uma página web na sala de aula.")
        mediator = next(row for row in current["participations"] if row["papel_id"] == "PAPEL-MEDIADOR")
        self.engine.update_context({"requester_relation": "support", "requester_participation_id": mediator["id"],
                                    "recursos_disponiveis": ["REC-COMPUTADOR", "REC-LEITOR-DE-TELA"], "mapping_confirmed": True})
        before = copy.deepcopy(self.engine.current["context"])
        updated = self.engine.update_context({"recursos_disponiveis": ["REC-COMPUTADOR"]})
        self.assertEqual(updated["context"]["raw"]["recursos_disponiveis"], ["REC-COMPUTADOR"])
        self.assertEqual(updated["context"]["objetivo"], before["objetivo"])
        self.assertEqual(updated["context"]["raw"]["necessidades"], before["necessidades"])
        self.assertEqual(updated["context"]["requester_participation_id"], mediator["id"])
        self.assertFalse(updated["mapping_confirmed"])
        self.assertIsNone(updated["last_result"])
        people = [row for row in updated["participations"] if row["id"] != mediator["id"]]
        updated = self.engine.update_context({"participations": people})
        self.assertEqual(updated["context"]["requester_participation_id"], "")
        self.assertEqual(updated["context"]["requester_relation"], "support")

    def test_invalid_requester_update_does_not_mutate_state(self):
        self.analyze("Quero ajudar uma pessoa a preencher um formulário digital.")
        before = copy.deepcopy(self.engine.current)
        for payload in ({"requester_relation": "professor"}, {"requester_participation_id": "missing-person"}):
            with self.assertRaises(ValueError):
                self.engine.update_context(payload)
            self.assertEqual(self.engine.current, before)

    def test_count_with_predicate_is_preserved(self):
        current = self.analyze("Quero ensinar um conteúdo a uma turma. Dois são surdos e um é cego.")
        self.assertEqual([(row["grupo_rotulo"], row["quantidade"]) for row in current["participations"]
                          if row.get("grupo_rotulo") in {"surdos", "cego"}], [("surdos", 2), ("cego", 1)])

    def test_removing_available_equipment_does_not_restore_it_from_personal_capability(self):
        current = self.analyze("Uma pessoa cega precisa acessar o conteúdo de uma página web. Quero adaptar o material.")
        people = copy.deepcopy(current["participations"])
        people[0]["recurso_operado_ids"] = ["REC-COMPUTADOR", "REC-LEITOR-DE-TELA"]
        self.engine.update_context({"recursos_disponiveis": ["REC-COMPUTADOR", "REC-LEITOR-DE-TELA"], "participations": people})
        for payload in ({"recursos_disponiveis": [], "participations": people}, {"recursos_disponiveis": []},
                        {"recursos_impedidos": ["REC-LEITOR-DE-TELA"]}):
            updated = self.engine.update_context(payload)
            self.assertEqual(self.engine.available_context_values(self.engine.current["context"], "recursos_disponiveis"), [])
            self.assertEqual(updated["participations"][0]["recurso_operado_ids"], ["REC-COMPUTADOR", "REC-LEITOR-DE-TELA"])
            self.assertNotEqual(self.engine.resource_state(self.engine.current["context"], "REC-LEITOR-DE-TELA"), "DISPONIVEL_CONFIRMADO")

    def test_removing_person_also_removes_orphan_derived_requirement_without_reparsing(self):
        narrative = "Quero ajudar uma pessoa cega e duas pessoas surdas a acessar uma página web."
        current = self.analyze(narrative)
        blind = next(person for person in current["participations"] if person.get("grupo_rotulo") == "cega")
        blind_requirements = [row for row in current["context"]["access_requirements"] if row["participant_id"] == blind["id"]]
        blind_needs = {nid for row in blind_requirements for nid in row["requirement_ids"]}
        people = [person for person in current["participations"] if person["id"] != blind["id"]]
        updated = self.engine.update_context({"participations": people, "necessidades": current["context"]["raw"]["necessidades"]})
        self.assertNotIn(blind["id"], {person["id"] for person in updated["participations"]})
        self.assertNotIn(blind["id"], {row["participant_id"] for row in updated["context"]["access_requirements"]})
        retained_needs = {nid for row in updated["context"]["access_requirements"] for nid in row["requirement_ids"]}
        self.assertFalse((blind_needs - retained_needs) & set(updated["context"]["raw"]["necessidades"]))
        self.assertEqual(updated["context"]["texto_curto"], narrative)

    def test_removing_person_preserves_independently_reported_need(self):
        current = self.analyze("Quero ajudar uma pessoa cega a acessar uma página web e compreender o conteúdo.")
        self.assertTrue(any(row.get("field") == "necessidades" and row.get("concept_id") == "NEC-ACESSO-EQUIVALENTE"
                            for row in current["narrative_interpretation"]["evidence"]))
        updated = self.engine.update_context({"participations": []})
        self.assertEqual(updated["context"]["access_requirements"], [])
        self.assertIn("NEC-ACESSO-EQUIVALENTE", updated["context"]["raw"]["necessidades"])


if __name__ == "__main__":
    unittest.main()
