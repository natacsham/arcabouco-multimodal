"""Synthetic reuse checks: no new scenario, pattern or knowledge is registered."""
import copy
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from engine import DecisionEngine


NARRATIVE = ("Tenho uma turma e quero ensinar um assunto complexo de matemática. "
             "Entre os alunos, tenho dois surdos e um cego. Quero saber como passar esse conteúdo para eles.")


def classroom(engine):
    engine.analyze_narrative(NARRATIVE)
    rows = copy.deepcopy(engine.current["participations"])
    students = [row for row in rows if row["papel_id"] == "PAPEL-ESTUDANTE"]
    students[0].update(modalidade_ids=["MOD-TEXTO", "MOD-IMAGEM"],
                       apoios_informados="Texto e imagens são compreendidos; outra forma de comunicação ainda a conferir.")
    students[1].update(caracteristica_ids=["CAR-INTERACAO-NAO-VISUAL"], modalidade_ids=["MOD-AUDIO"],
                       recurso_operado_ids=["REC-LEITOR-DE-TELA"])
    rows.append({"id": "PREPARACAO-CONFIRMADA", "papel_id": "PAPEL-RESPONSAVEL-ADAPTACAO",
                 "label": "Docente prepara o material", "recurso_operado_ids": ["REC-EDITOR-MULTIMIDIA"],
                 "modalidade_ids": ["MOD-TEXTO"]})
    engine.update_context({
        "tarefas": ["TAR-ACESSAR-COMPREENDER-CONTEUDO-DIGITAL"],
        "necessidades": ["NEC-ACESSO-EQUIVALENTE", "NEC-ALTERNATIVA-FUNCIONAL-EQUIVALENTE", "NEC-APOIAR-COMPREENSAO-TURMA"],
        "recursos_digitais": ["RED-PAGINA-WEB"],
        "recursos_disponiveis": ["REC-COMPUTADOR", "REC-EDITOR-MULTIMIDIA", "REC-LEITOR-DE-TELA"],
        "ambientes": ["AMB-SALA-DE-AULA"], "participations": rows,
        "mapping_confirmed": True, "transfer_confirmed": True,
    })
    return rows


class FunctionalReuseTests(unittest.TestCase):
    def setUp(self):
        self.engine = DecisionEngine()

    def test_literal_group_counts_do_not_infer_access_route_or_environment(self):
        for text in (NARRATIVE, NARRATIVE.replace("dois surdos", "dois alunos surdos")):
            self.engine.analyze_narrative(text)
            students = [row for row in self.engine.current["participations"] if row["papel_id"] == "PAPEL-ESTUDANTE"]
            self.assertEqual([row["quantidade"] for row in students], [2, 1])
            snapshot = self.engine.current_payload()
            self.assertEqual(snapshot["participations"], self.engine.current["participations"])
            snapshot["participations"][0]["label"] = "Alteração somente na resposta"
            self.assertNotEqual(snapshot["participations"][0]["label"], self.engine.current["participations"][0].get("label"))
            for row in students:
                self.assertEqual(row["modalidade_ids"], [])
                self.assertEqual(row["recurso_operado_ids"], [])
                self.assertEqual(row["caracteristica_ids"], [])
            self.assertEqual(self.engine.current["context"]["ambientes"], [])
            self.assertTrue(self.engine.current["context"]["tarefas"])
            questions = self.engine.missing_questions()
            self.assertFalse(any(row["field"] == "modalidades_disponiveis" and not row.get("participant_id") for row in questions))

    def test_function_requirements_exist_before_component_selection(self):
        classroom(self.engine)
        self.engine.components = []
        self.engine.derive_required_functions()
        self.assertIn("FUN-PRESERVAR-SIGNIFICADO-ENTRE-MODOS", self.engine.current["context"]["funcoes_requeridas_ids"])
        derivations = self.engine.current["context"]["function_derivation"]
        self.assertTrue(all(row["not_derived_from_component"] for row in derivations))
        self.assertTrue(all(row["knowledge_usage_authorized_by_this_step"] is False for row in derivations))
        self.assertTrue(all(row["correspondences"] and row["source_ids"] for row in derivations))

    def test_narrative_reaches_existing_support_through_actual_followup_questions(self):
        self.engine.analyze_narrative(NARRATIVE)

        def answer(field, value, participant_id=None):
            matches = [row for row in self.engine.missing_questions()
                       if row["field"] == field and row.get("participant_id") == participant_id]
            self.assertEqual(len(matches), 1, (field, participant_id))
            question = matches[0]
            if question.get("concept_ids") and isinstance(value, list):
                self.assertTrue(set(value) <= set(question["concept_ids"]))
            if participant_id:
                rows = copy.deepcopy(self.engine.current["participations"])
                target = next(row for row in rows if row["id"] == participant_id)
                target[question["answer_field"]] = value
                payload = {"participations": rows}
            elif field == "participantes":
                rows = copy.deepcopy(self.engine.current["participations"])
                rows += [{"id": "RESP-CONFIRMADO", "papel_id": role, "label": "Responsável confirmado"} for role in value]
                payload = {"participations": rows}
            elif field == "barreira_ou_necessidade":
                payload = {"necessidades": self.engine.current["context"]["necessidades"] + value}
            else:
                payload = {field: value}
            self.engine.update_context(payload)

        self.assertEqual(self.engine.current["context"]["tarefas"], ["TAR-COMUNICAR-CONTEUDO-1545B38"])
        answer("tarefas", ["TAR-ACESSAR-COMPREENDER-CONTEUDO-DIGITAL"])
        # The matrix supplies design needs with documentary witnesses, rather
        # than making the person re-enter a general accessibility principle.
        self.assertFalse(any(row["field"] == "barreira_ou_necessidade" for row in self.engine.missing_questions()))
        self.assertTrue(self.engine.current["context"]["access_requirements"])
        answer("recursos_digitais", ["RED-PAGINA-WEB"])
        answer("recursos_disponiveis", ["REC-LEITOR-DE-TELA", "REC-EDITOR-MULTIMIDIA"])
        answer("participantes", ["PAPEL-RESPONSAVEL-ADAPTACAO"])
        students = [row for row in self.engine.current["participations"] if row["papel_id"] == "PAPEL-ESTUDANTE"]
        self.assertFalse(any(row.get("participant_id") == students[0]["id"] for row in self.engine.missing_questions()))
        answer("modalidades_disponiveis", ["MOD-AUDIO"], students[1]["id"])
        answer("recursos_disponiveis", ["REC-LEITOR-DE-TELA"], students[1]["id"])
        answer("recursos_disponiveis", ["REC-EDITOR-MULTIMIDIA"], "RESP-CONFIRMADO")
        self.engine.update_context({"mapping_confirmed": True, "transfer_confirmed": True})
        decision = self.engine.generate()["decision"]
        self.assertEqual(decision["status"], "GERADA_PARCIAL")
        self.assertEqual(decision["component_ids"], ["PAD-CONTEUDO-WEB-EQUIVALENTE"])
        self.assertEqual(set(decision["knowledge_ids"]), {"K10", "K42"})
        self.assertEqual(decision["articulation_ids"], ["ART-REF-03"])
        students = [row for row in self.engine.current["participations"] if row["papel_id"] == "PAPEL-ESTUDANTE"]
        self.assertEqual(students[0]["recurso_operado_ids"], [])
        self.assertNotIn("CAR-INTERACAO-NAO-VISUAL", students[0]["caracteristica_ids"])
        self.assertFalse(any(row.get("participant_id") == students[0]["id"] for row in self.engine.missing_questions()))

    def test_global_equipment_does_not_prove_individual_operation(self):
        classroom(self.engine)
        rows = copy.deepcopy(self.engine.current["participations"])
        for row in rows:
            row["recurso_operado_ids"] = []
        self.engine.update_context({"participations": rows, "mapping_confirmed": True, "transfer_confirmed": True})
        result = self.engine.generate()
        self.assertEqual(result["decision"]["component_ids"], ["PAD-CONTEUDO-WEB-EQUIVALENTE"])
        self.assertEqual(result["decision"]["configuracao_modal"][0]["availability_status"], "CONDICIONAL_A_CONFIRMACAO")
        self.assertTrue(all(not row["component_ids"] for row in result["decision"]["participant_coverage"]))
        checks = result["execution_evidence"]["checks"]
        operation = [row for row in checks if row["rule_id"] == "declared_resource_operation"
                     and row["subject_id"] == "PAD-CONTEUDO-WEB-EQUIVALENTE"]
        self.assertEqual(operation[0]["outcome"], "PENDING")

    def test_existing_pattern_is_reused_with_documented_articulation_and_partial_limit(self):
        classroom(self.engine)
        result = self.engine.generate()
        decision = result["decision"]
        self.assertEqual(decision["status"], "GERADA_PARCIAL")
        self.assertEqual(decision["component_ids"], ["PAD-CONTEUDO-WEB-EQUIVALENTE"])
        self.assertEqual(set(decision["knowledge_ids"]), {"K10", "K42"})
        self.assertEqual(decision["articulation_ids"], ["ART-REF-03"])
        self.assertNotIn(self.engine.current["context"]["id"], self.engine.contexts)
        self.assertEqual(len(decision["participant_coverage"]), 2)
        self.assertTrue(all(row["meaning_or_learning_measured"] is False for row in decision["participant_coverage"]))
        # Personal declarations remain personal after composition.
        students = [row for row in self.engine.current["participations"] if row["papel_id"] == "PAPEL-ESTUDANTE"]
        self.assertNotIn("REC-LEITOR-DE-TELA", students[0]["recurso_operado_ids"])
        self.assertNotIn("MOD-IMAGEM", students[1]["modalidade_ids"])
        self.assertEqual(self.engine.current["context"]["modalidades_disponiveis"], [])

    def test_resource_removal_has_an_actual_selection_consequence(self):
        classroom(self.engine)
        initial = self.engine.generate()["decision"]
        rows = copy.deepcopy(self.engine.current["participations"])
        for row in rows:
            row["recurso_operado_ids"] = [identifier for identifier in row.get("recurso_operado_ids", []) if identifier != "REC-LEITOR-DE-TELA"]
        self.engine.update_context({"recursos_disponiveis": ["REC-COMPUTADOR", "REC-EDITOR-MULTIMIDIA"],
                                    "recursos_impedidos": ["REC-LEITOR-DE-TELA"], "participations": rows,
                                    "mapping_confirmed": True, "transfer_confirmed": True})
        changed = self.engine.generate()["decision"]
        self.assertTrue(initial["component_ids"])
        self.assertEqual(changed["component_ids"], [])
        self.assertTrue(changed["status"].startswith("SUSPENSA"))

    def test_hierarchy_matching_is_the_same_for_retrieval_and_components(self):
        context = {"tarefas": ["TAR-CONSTRUIR-RECURSO-DIGITAL-HISTORIA"]}
        self.assertTrue(self.engine.intersects(context, "tarefas", ["TAR-PRODUZIR-CONTEUDO-MULTIMODAL"]))
        self.assertFalse(self.engine.intersects(context, "tarefas", ["TAR-NAVEGAR-E-ORIENTAR-SE"]))


if __name__ == "__main__":
    unittest.main(verbosity=2)
