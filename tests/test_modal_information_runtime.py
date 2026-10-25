"""Existing haptic/audio contract, positive execution and scoped ablations.

This structured synthetic input is not an empirical case or a new catalogue
scenario. The positive run uses the unchanged public base. Negative runs remove
one condition or premise in isolated memory copies; no new rule is installed.
"""
import copy
import hashlib
import json
from pathlib import Path
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from experimental.v2.composer import Composer
from scripts.migrate_semantic_curation import HAPTIC_OP, HAPTIC_REL, HAPTIC_APP, CARE_CLAIM


def structured_context():
    return {
        'id':'SYN-MODAL-INFORMATION-CONTRACT', 'confirmed':True,
        'tarefas':['TAR-ACOMPANHAR-ORIENTACAO-317CD64'],
        'modalidades_disponiveis':['MOD-AUDIO','MOD-HAPTICO'],
        'barreiras':['BAR-AUDIO-PODE-PERDER-EFETIVIDADE-COM-RUIDO-04E2CCE'],
        'funcoes_requeridas_ids':['FUN-FEEDBACK-PERCEPTIVEL','FUN-MANTER-INFORMACAO-RECUPERAVEL'],
        'participations':[{'id':'p-synthetic','papel_id':'PAPEL-PESSOA-APOIADA',
            'recurso_operado_ids':['REC-VIBRACAO','REC-SAIDA-AUDIO']}],
        'recursos_disponiveis':['REC-VIBRACAO','REC-SAIDA-AUDIO'], 'recursos_impedidos':[],
        'facts':{'AudioUsable':True, HAPTIC_OP+':input_available':True,
            HAPTIC_OP+':recoverable_message':True,HAPTIC_OP+':tactile_notice_needed':True,
            HAPTIC_OP+':same_event_binding':True,
            HAPTIC_REL+':sufficiency':True,HAPTIC_REL+':temporal':True},
    }


def chosen_haptic(result):
    return [c for c in result['choices'] if any(s['id']==HAPTIC_OP for s in c['steps'])]


class ModalInformationRuntimeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.path=ROOT/'data/knowledge-base.json'
        cls.digest=hashlib.sha256(cls.path.read_bytes()).hexdigest()
        cls.data=json.loads(cls.path.read_text(encoding='utf-8'))

    def run_contract(self,context=None,data=None):
        composer=Composer([])
        composer.base=copy.deepcopy(self.data if data is None else data)
        context=copy.deepcopy(structured_context() if context is None else context)
        before=copy.deepcopy(context)
        result=composer.compose_context(context)
        self.assertEqual(before,context)
        self.assertEqual(self.digest,hashlib.sha256(self.path.read_bytes()).hexdigest())
        return result

    def test_real_base_produces_a_scoped_complementary_choice(self):
        result=self.run_contract()
        choices=chosen_haptic(result)
        self.assertTrue(choices,[(r['id'],r['state'])for r in result['capability_evaluations'] if r['id']==HAPTIC_OP])
        relation=next(r for c in choices for r in c['relations'] if r['id']==HAPTIC_REL)
        self.assertEqual('PASS',relation['state'])
        self.assertEqual('COMPLEMENTARITY',relation['kind'])
        self.assertEqual({'DISPONIBILIDADE_DA_MENSAGEM','CONTEUDO_DA_ORIENTACAO'},set(relation['required_information']))
        self.assertEqual({'MOD-AUDIO','MOD-HAPTICO'},{r['representation_id']for r in relation['information_roles']})
        self.assertTrue(all(r['alone_sufficient_for_goal'] is False for r in relation['information_roles']))
        self.assertTrue(any(r['kind']=='MODAL_INFORMATION_CONTRIBUTION' and r['state']=='PASS'
                            for r in result['execution_evidence']))
        # A usable proposal does not assert its subsequent human check happened.
        step=next(s for c in choices for s in c['steps'] if s['id']==HAPTIC_OP)
        self.assertTrue(any(p['phase']=='verification' and p['state']=='NOT_EXECUTED' for p in step['phase_conditions']))

    def test_removing_either_resource_removes_the_complementary_choice(self):
        for resource in ('REC-SAIDA-AUDIO','REC-VIBRACAO'):
            with self.subTest(resource=resource):
                context=structured_context()
                context['recursos_disponiveis'].remove(resource)
                context['recursos_impedidos']=[resource]
                result=self.run_contract(context)
                self.assertFalse(chosen_haptic(result))
                row=next(r for r in result['capability_evaluations'] if r['id']==HAPTIC_OP)
                self.assertEqual('FAIL',row['state'])

    def test_unknown_or_false_access_is_not_confirmed_by_having_audio(self):
        for value in (None,False):
            with self.subTest(value=value):
                context=structured_context();context['facts']['AudioUsable']=value
                result=self.run_contract(context)
                self.assertFalse(chosen_haptic(result))
                row=next(r for r in result['capability_evaluations'] if r['id']==HAPTIC_OP)
                fact=next(p for p in row['phase_conditions'] if p['id']=='AudioUsable')
                self.assertEqual('PENDING' if value is None else 'FAIL',fact['state'])

    def test_removing_theory_premise_does_not_leave_complementarity_authorized(self):
        data=copy.deepcopy(self.data)
        claim=next(c for k in data['knowledge'] for c in k.get('operation_claims',[]) if c['id']==CARE_CLAIM)
        claim.update(eligibility='PROPOSED_OPERATIONALIZATION',foundation_status='PENDING')
        result=self.run_contract(data=data)
        self.assertFalse(chosen_haptic(result))
        self.assertTrue(any(r['state']=='FAIL' and (CARE_CLAIM in str(r) or HAPTIC_APP in str(r)) for r in result['execution_evidence']))

    def test_removing_relation_authorization_cannot_be_repaired_by_operational_support(self):
        data=copy.deepcopy(self.data)
        op=next(c['operation_contract']for c in data['decision_components']if c.get('operation_contract',{}).get('id')==HAPTIC_OP)
        op['relations'][0]['analytical_application_ids']=[]
        result=self.run_contract(data=data)
        self.assertFalse(chosen_haptic(result))
        self.assertTrue(any(r['kind']=='RELATION_ANALYTICAL_AUTHORIZATION' and r['state']=='FAIL' for r in result['execution_evidence']))

    def test_tactile_need_and_shared_event_are_not_inferred_from_noise(self):
        for fact in (HAPTIC_OP+':tactile_notice_needed',HAPTIC_OP+':same_event_binding'):
            with self.subTest(fact=fact):
                context=structured_context();context['facts'][fact]=False
                self.assertFalse(chosen_haptic(self.run_contract(context)))

    def test_labels_do_not_create_or_remove_the_functional_combination(self):
        first=self.run_contract()
        context=structured_context()
        context.update(id='UNREGISTERED-ANOTHER-ID',label='Outro título sem função de seleção',description='Sem assunto cadastrado.')
        second=self.run_contract(context)
        signature=lambda result:[([s['id']for s in c['steps']],[r['id']for r in c['relations']])for c in chosen_haptic(result)]
        self.assertTrue(signature(first))
        self.assertEqual(signature(first),signature(second))


if __name__=='__main__':
    unittest.main()
