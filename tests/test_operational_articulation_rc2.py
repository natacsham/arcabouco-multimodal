"""Structural and semantic guards for scoped analytical operationalization.

These are implementation checks, not an evaluation of recommendation utility.
No user-facing examples or ready-made answers are created by this suite.
"""
import copy
import hashlib
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.build_traceability_rdf import (validate_contributions,
    validate_operational_contracts, validate_analytical_applications, iter_operation_contracts,
    build_graph, M, Graph)


class OperationalArticulationRC2Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data=json.loads((ROOT/'data/knowledge-base.json').read_text(encoding='utf-8'))

    def first_application(self,data):
        return next(a for r in data['articulations'] for a in r.get('operational_applications',[]))

    def test_whole_collection_integrity_and_candidate_states(self):
        validate_contributions(self.data)
        validate_operational_contracts(self.data)
        self.assertEqual(45,len(self.data['knowledge']))
        self.assertEqual(11,len(self.data['functional_matrix']))
        for row in self.data['knowledge']:
            self.assertFalse(row['rc2_audit']['whole_statement_promoted'])
        for kid in ('K38','K36','K43'):
            k=next(k for k in self.data['knowledge'] if k['id']==kid)
            c=next(c for c in k['operation_claims'] if c['id']==f'CLM-{kid}-LEGACY')
            self.assertEqual('PROPOSED_OPERATIONALIZATION',c['eligibility'])

    def test_pending_premise_cannot_authorize(self):
        data=copy.deepcopy(self.data)
        app=self.first_application(data)
        app['premises'][0]={'knowledge_id':'K38','claim_id':'CLM-K38-LEGACY','contribution_ids':[]}
        with self.assertRaisesRegex(ValueError,'Unusable analytical premise'):
            validate_operational_contracts(data)

    def test_wrong_knowledge_cannot_reuse_contribution(self):
        data=copy.deepcopy(self.data)
        app=self.first_application(data)
        app['premises'][0]['contribution_ids']=['C-K43-02']
        with self.assertRaisesRegex(ValueError,'Unusable analytical contribution'):
            validate_operational_contracts(data)

    def test_missing_contribution_blocks_authorization(self):
        data=copy.deepcopy(self.data)
        target=next(a for r in data['articulations'] for a in r.get('operational_applications',[])
                    if a['id']=='APP-ART-TRF-04-ORGANIZAR-RETOMAR')
        data['contributions']=[c for c in data['contributions'] if c['id']!='C-K38-MMI-NAV']
        with self.assertRaises(ValueError):
            validate_operational_contracts(data)

    def test_empty_premise_contributions_cannot_authorize(self):
        data=copy.deepcopy(self.data)
        self.first_application(data)['premises'][0]['contribution_ids']=[]
        with self.assertRaisesRegex(ValueError,'lacks a localized contribution'):
            validate_operational_contracts(data)

    def test_origin_must_belong_to_premises(self):
        data=copy.deepcopy(self.data)
        app=self.first_application(data)
        app['criterion_support']=[{'criterion_id':'CA38','origin_ids':['ORI-0238']}]
        with self.assertRaisesRegex(ValueError,'exact premise'):
            validate_operational_contracts(data)

    def test_cycles_do_not_authorize_themselves(self):
        data=copy.deepcopy(self.data)
        app=self.first_application(data)
        app['depends_on_application_ids']=[app['id']]
        with self.assertRaisesRegex(ValueError,'Circular analytical'):
            validate_operational_contracts(data)

    def test_wrong_target_not_authorized(self):
        data=copy.deepcopy(self.data)
        app=self.first_application(data)
        app['authorized_operation_ids']=['OP-NOT-EXISTING']
        with self.assertRaisesRegex(ValueError,'Unknown authorized operation'):
            validate_operational_contracts(data)

    def situated_run(self,context,data=None):
        from experimental.v2.composer import Composer, _SituatedRun
        composer=Composer([])
        composer.base=copy.deepcopy(self.data if data is None else data)
        return _SituatedRun(composer,context)

    def test_situated_resource_state_is_not_broadcast_to_other_people(self):
        context={'id':'SYN-OWNED-RESOURCE','confirmed':True,
            'participations':[{'id':'p1'},{'id':'p2'}],
            'situations':[{'id':'s','participant_ids':['p1','p2'],
                'resource_states':[{'resource_id':'REC-SAIDA-AUDIO',
                    'state':'DISPONIVEL_CONFIRMADO','participant_id':'p1'}]}]}
        units={u['participant_id']:u for u in self.situated_run(context).normalize()}
        self.assertIn('REC-SAIDA-AUDIO',units['p1']['recursos_disponiveis'])
        self.assertNotIn('REC-SAIDA-AUDIO',units['p2']['recursos_disponiveis'])
        context['situations'][0]['resource_states'][0]['state']='IMPEDIDO'
        units={u['participant_id']:u for u in self.situated_run(context).normalize()}
        self.assertIn('REC-SAIDA-AUDIO',units['p1']['recursos_impedidos'])
        self.assertNotIn('REC-SAIDA-AUDIO',units['p2']['recursos_impedidos'])

    def test_runtime_requires_the_explicit_claim_contribution_edge(self):
        data=copy.deepcopy(self.data)
        claim=next(c for k in data['knowledge'] for c in k.get('operation_claims',[])
                   if c['id']=='CLM-K42-TD-ORI-0148')
        claim['contribution_ids']=[]
        run=self.situated_run({'id':'SYN-WITHDRAWN-PREMISE'},data)
        accepted,rejected=run.analytical_groundings(['APP-ART-TRF-02-CAPTIONS'],
            {'participant_id':'p','situation_id':'s'},'OP-PAD-VIDEO-PROCESSO-CAPTIONS')
        self.assertFalse(bool(accepted))
        self.assertTrue(rejected)

    def test_video_routes_are_not_conjoined(self):
        op=next(r for r in iter_operation_contracts(self.data) if r['id']=='OP-PAD-VIDEO-PROCESSO')
        text,audio=op['operation_variants']
        self.assertEqual(['MOD-TEXTO'],text['selected_representation_ids'])
        self.assertEqual(['MOD-AUDIO'],audio['selected_representation_ids'])
        self.assertEqual(['CanReadText'],[f['id'] for f in text['requires_facts']])
        self.assertEqual(['AudioUsable'],[f['id'] for f in audio['requires_facts']])
        self.assertNotEqual(text['analytical_application_ids'],audio['analytical_application_ids'])
        self.assertEqual([],op['relations'])
        for variant in (text,audio):
            self.assertEqual(variant['input_requirements'][0]['meaning_unit'],variant['output_spec'][0]['meaning_unit'])
            self.assertEqual(variant['relations'][0]['meaning_unit'],variant['output_spec'][0]['meaning_unit'])
        self.assertNotEqual(text['input_requirements'][0]['meaning_unit'],audio['input_requirements'][0]['meaning_unit'])

    def test_relation_cannot_change_information_unit_without_explicit_mapping(self):
        data=copy.deepcopy(self.data)
        op=next(r['operation_contract'] for r in data['decision_components'] if r['id']=='PAD-VIDEO-PROCESSO')
        op['operation_variants'][0]['relations'][0]['meaning_unit']='UNRELATED_INFORMATION'
        with self.assertRaisesRegex(ValueError,'inconsistent with information'):
            validate_operational_contracts(data)

    def test_stored_text_not_confused_with_perceptual_audio(self):
        op=next(r for r in iter_operation_contracts(self.data)
                if r['id']=='OP-PAD-REPRESENTACAO-VISUAL-EXPLICADA-TEXT_SCREEN_READER')
        self.assertEqual(['MOD-TEXTO'],op['stored_representation_ids'])
        self.assertEqual(['MOD-AUDIO'],op['selected_representation_ids'])
        self.assertEqual('MOD-AUDIO',op['output_spec'][0]['representation_id'])
        self.assertEqual({'UsesScreenReader','AudioUsable'},{f['id'] for f in op['requires_facts']})
        self.assertTrue(op['presentation_transformation'])

    def test_prepared_output_is_not_required_as_existing_resource(self):
        for op in iter_operation_contracts(self.data):
            if op.get('operation_scope')!='PREPARATION_FOR_RECIPIENT':continue
            prerequisites=set(op['resource_requirements']['all'])
            prerequisites.update(x for group in op['resource_requirements']['any'] for x in group)
            self.assertFalse(prerequisites.intersection(op['output_resource_ids']))
            self.assertTrue(any(c['phase']=='production' for c in op['condition_phases']))
            self.assertTrue(any(c['phase']=='verification' for c in op['condition_phases']))
            self.assertEqual([],op['conditions'])

    def test_text_organization_does_not_claim_multimodal_relation(self):
        op=next(r for r in iter_operation_contracts(self.data) if r['id']=='OP-PAD-ORGANIZAR-CONTEUDO-PERSISTENTE')
        self.assertEqual([],op['relations'])
        self.assertIn('FUN-MANTER-INFORMACAO-RECUPERAVEL',op['function_ids'])
        self.assertTrue(op['analytical_application_ids'])

    def test_historical_learning_context_no_longer_runtime_requirement(self):
        b=json.loads((ROOT/'experimental/v2/trajectory-bindings.json').read_text(encoding='utf-8'))
        for c in [*b['contracts'].values(),*b['applications']]:
            self.assertNotIn('LearningCommunicationContext',c.get('requires_facts',[]))
        self.assertIn('LearningCommunicationContext',b['facts'])

    def test_trajectory_fingerprints_match_same_reviewed_records(self):
        b=json.loads((ROOT/'experimental/v2/trajectory-bindings.json').read_text(encoding='utf-8'))
        for collection,records in b['records'].items():
            index={r['id']:r for r in self.data[collection]}
            for rid,expected in records.items():
                encoded=json.dumps(index[rid],sort_keys=True,ensure_ascii=False,separators=(',',':'))
                self.assertEqual(expected,hashlib.sha256(encoded.encode('utf-8')).hexdigest())
        self.assertEqual({'knowledge/K28','knowledge/K29','knowledge/K41'},
                         set(b['scope_revision_rc2']['record_hashes_refreshed']))

    def test_scoped_witnesses_prevent_generic_audio_and_authorship_transfer(self):
        ops={r['id']:r for r in iter_operation_contracts(self.data)}
        for oid in ('OP-PAD-ORIENTACAO-AUDIO-RECUPERAVEL','OP-PAD-RETORNO-HAPTICO-RUIDO'):
            op=ops[oid]
            self.assertFalse(op['transfer_scope']['allow_new_task_with_functional_witness'])
            clauses=op['applicability_witness']['all']
            self.assertEqual({'modalidades','barreiras','tarefas'},{c['field'] for c in clauses})
        haptic=ops['OP-PAD-RETORNO-HAPTICO-RUIDO']
        self.assertFalse(haptic['independent_support_allowed'])
        self.assertTrue(haptic['relations'][0]['requires_analytical_authorization'])
        self.assertFalse(haptic['relations'][0].get('analytical_application_ids'))
        self.assertTrue(ops['OP-PAD-EXPRESSAO-AUTORAL-FALA-AUDIO']['applicability_witness']['any'])

    def test_rdf_projection_preserves_exact_analytical_premises(self):
        graph=build_graph(Graph().parse(ROOT/'ontology/mado-combined.ttl',format='turtle'),
                          Graph().parse(ROOT/'ontology/main.ttl',format='turtle'),self.data)
        app=M['APP-ART-TRF-04-ORGANIZAR-RETOMAR']
        self.assertIn((app,M.premissaOperacional,M['CLM-K38-MMI-NAV']),graph)
        self.assertIn((app,M.autorizaOperacao,M['OP-PAD-ORGANIZAR-CONTEUDO-PERSISTENTE']),graph)
        self.assertNotIn((app,M.premissaOperacional,M['CLM-K38-LEGACY']),graph)


if __name__=='__main__':
    unittest.main()
