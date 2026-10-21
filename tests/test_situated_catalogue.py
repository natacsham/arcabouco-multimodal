"""Synthetic structural/adversarial checks, not empirical validation of guidance."""
import copy
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'scripts'))
sys.path.insert(0, str(ROOT / 'vendor'))
import build_traceability_rdf as builder
from rdflib import Graph, Literal, RDF
from pyshacl import validate

M = builder.M


class SituatedCatalogueTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads((ROOT / 'data/knowledge-base.json').read_text(encoding='utf8'))
        cls.by_id = {r['id']: r for r in cls.data['knowledge']}
        cls.shapes = Graph().parse(ROOT / 'shapes/main.shacl.ttl', format='turtle')
        cls.graph = builder.build_graph(
            Graph().parse(ROOT / 'ontology/mado-combined.ttl', format='turtle'),
            Graph().parse(ROOT / 'ontology/main.ttl', format='turtle'), cls.data)

    def test_full_inventory_is_audited_without_blanket_approval(self):
        self.assertEqual(len(self.data['knowledge']), 45)
        self.assertEqual(len(self.data['functional_matrix']), 11)
        active = [r for r in self.data['decision_components'] if r.get('active_in_rc4')]
        self.assertEqual(len(active), 11)
        self.assertTrue(all(k.get('operation_claims') for k in self.data['knowledge']))
        self.assertTrue(all(r.get('inference_contract') for r in self.data['functional_matrix']))
        self.assertTrue(all(r.get('operation_contract') for r in active))
        builder.validate_operational_contracts(self.data)
        eligible = {k['id'] for k in self.data['knowledge'] if any(
            c['eligibility'] == 'DOCUMENTED_OPERATIONAL_CLAIM' for c in k['operation_claims'])}
        self.assertNotIn('K37', eligible)
        self.assertNotIn('K27', eligible)
        self.assertIn('K38', eligible)
        self.assertLess(len(eligible), len(self.data['knowledge']))

    def test_partial_claim_does_not_promote_its_legacy_conclusion(self):
        k = self.by_id['K38']
        self.assertEqual(k['foundation_review_status'], 'PARCIAL')
        self.assertEqual(k['operation_claims'][0]['eligibility'], 'PROPOSED_OPERATIONALIZATION')
        scoped = next(c for c in k['operation_claims'] if c['id'] == 'CLM-K38-C-K38-03')
        self.assertEqual(scoped['excerpt_ids'], ['TD-EV29'])
        self.assertEqual(scoped['source_ids'], ['F08'])
        self.assertEqual(scoped['eligibility'], 'DOCUMENTED_OPERATIONAL_CLAIM')
        self.assertFalse(scoped['scope']['empirical_effect_authorized'])

    def test_scoped_claim_cannot_borrow_an_unrelated_excerpt(self):
        data = copy.deepcopy(self.data)
        k = next(x for x in data['knowledge'] if x['id'] == 'K38')
        c = next(x for x in k['operation_claims'] if x['id'] == 'CLM-K38-C-K38-03')
        c['support'][0]['excerpt_id'] = 'TD-EV02'
        with self.assertRaisesRegex(ValueError, 'source/excerpt'):
            builder.validate_operational_contracts(data)

    def test_reviewed_source_cannot_override_pending_claim(self):
        data = copy.deepcopy(self.data)
        k = next(x for x in data['knowledge'] if x['id'] == 'K37')
        c = k['operation_claims'][0]
        c['eligibility'] = 'DOCUMENTED_OPERATIONAL_CLAIM'
        with self.assertRaisesRegex(ValueError, 'supported state'):
            builder.validate_operational_contracts(data)

    def test_criterion_origin_cannot_be_crossed(self):
        data = copy.deepcopy(self.data)
        p = next(x for x in data['decision_components'] if x['id'] == 'PAD-CONTEUDO-WEB-EQUIVALENTE')
        p['operation_contract']['claim_support'][0]['origin_ids'] = ['ORI-0148']
        with self.assertRaisesRegex(ValueError, 'criterion/origin'):
            builder.validate_operational_contracts(data)

    def test_functional_signals_do_not_become_diagnosis_rules(self):
        rows = {r['id']: r for r in self.data['functional_matrix']}
        self.assertNotIn('trigger_groups', rows['MF-01']['inference_contract'])
        self.assertEqual(len(rows['MF-04']['inference_contract']['trigger_groups']), 2)
        for mid in ['MF-03','MF-04','MF-05','MF-06','MF-07','MF-08','MF-09','MF-10']:
            self.assertTrue(rows[mid]['sinais_relato'])
            self.assertNotIn('autismo', rows[mid]['sinais_relato'])
            self.assertIn('DIAGNOSIS_TO_CAPABILITY', rows[mid]['inference_contract']['forbidden_inferences'])
        self.assertEqual(rows['MF-05']['inference_contract']['eligibility'], 'PROPOSED_OPERATIONALIZATION')
        self.assertEqual(rows['MF-05']['requisito_ids'], [])
        self.assertEqual(rows['MF-07']['requisito_ids'], ['NEC-CONFERIR-OPERACAO-DO-RECURSO'])

    def test_legacy_modal_identifiers_have_distinct_semantics(self):
        rows = {r['id']: r for r in self.data['context_elements']}
        self.assertEqual(rows['MOD-TECLADO']['interaction_semantics']['kind'], 'INPUT_METHOD')
        self.assertEqual(rows['MOD-JOGO-INTERATIVO']['interaction_semantics']['kind'], 'COMPOSITE_ACTIVITY')
        self.assertEqual(rows['MOD-TOQUE']['interaction_semantics']['kind'], 'INPUT_METHOD')
        self.assertNotEqual(rows['MOD-FALA']['interaction_semantics']['kind'], rows['MOD-AUDIO']['interaction_semantics']['kind'])
        self.assertFalse(rows['CAR-PERFIS-FUNCIONAIS-DIVERSOS']['assertion_semantics']['group_to_member_inference_allowed'])

    def test_game_scope_cannot_assert_consolidation(self):
        p = next(x for x in self.data['decision_components'] if x['id'] == 'PAD-JOGO-CONSOLIDACAO-FEEDBACK')
        op = p['operation_contract']
        self.assertTrue(op['transfer_scope']['requires_existing_representation'])
        self.assertNotIn('FUN-CONSOLIDAR-COM-FEEDBACK', op['function_ids'])
        self.assertTrue(all(s['knowledge_id'] != 'K37' for s in op['claim_support']))
        self.assertTrue(op['integration_gaps'])

    def test_public_projection_passes_shapes_and_preserves_pending(self):
        # Historical quality warnings remain documentary issues, not violations.
        conforms, _, report = validate(self.graph, shacl_graph=self.shapes, inference='none', allow_warnings=True)
        self.assertTrue(conforms, str(report))
        self.assertIn((M['CLM-K37-LEGACY'], M.estadoDaAfirmacao, Literal('PENDING')), self.graph)
        self.assertIn((M['CLM-K38-C-K38-03'], M.elegibilidadeOperacional, Literal('DOCUMENTED_OPERATIONAL_CLAIM')), self.graph)

    def test_rdf_cannot_replace_the_claims_exact_source(self):
        graph = Graph()
        for triple in self.graph:
            graph.add(triple)
        node = M['CLM-K38-C-K38-03']
        graph.set((node, M.fonteDaAfirmacao, M.F01))
        conforms, _, _ = validate(graph, shacl_graph=self.shapes, inference='none', allow_warnings=True)
        self.assertFalse(conforms)

    def test_claim_query_joins_only_exact_excerpt_source_pairs(self):
        rows = list(self.graph.query((ROOT / 'queries/CQ-009.rq').read_text(encoding='utf8')))
        self.assertTrue(rows)
        for row in rows:
            if row.trecho:
                self.assertIn((row.trecho, M.trechoDeFonte, row.fonte), self.graph)
                self.assertIn((row.conhecimento, M.sustentadoPorTrecho, row.trecho), self.graph)
                self.assertIn((row.conhecimento, M.derivadoDe, row.fonte), self.graph)
        self.assertTrue(any(row.afirmacao == M['CLM-K38-C-K38-03'] and row.trecho == M['TD-EV29'] and row.fonte == M.F08 for row in rows))

    def test_all_operation_and_relation_pairs_have_scoped_semantic_review(self):
        origins = {r['id']: r for r in self.data['criterion_origins']}
        claims = {c['id']: c for k in self.data['knowledge'] for c in k['operation_claims']}
        for pattern in self.data['decision_components']:
            if not pattern.get('active_in_rc4'):
                continue
            op = pattern['operation_contract']
            for supports in [op['claim_support']] + [r['claim_support'] for r in op['relations']]:
                for support in supports:
                    review = support['semantic_pair_review']
                    self.assertEqual(review['status'], 'CONFERIDO_NO_REGISTRO')
                    self.assertFalse(review['original_document_rechecked'])
                    if review['scope'] == 'DIRECT_NORMATIVE_CLAUSE':
                        for oid in support['origin_ids']:
                            self.assertIn(origins[oid]['trecho_id'], claims[support['claim_id']]['excerpt_ids'])
                    if review['scope'] == 'CONTEXTUAL_CONTRIBUTION_ONLY':
                        self.assertIsNone(support['criterion_id'])
                        self.assertEqual(support['origin_ids'], [])

    def test_matching_criterion_id_does_not_excuse_wrong_normative_claim(self):
        data = copy.deepcopy(self.data)
        op = next(p['operation_contract'] for p in data['decision_components'] if p['id'] == 'PAD-VIDEO-PROCESSO')
        support = next(s for s in op['claim_support'] if s['claim_id'] == 'CLM-K42-TD-ORI-0148')
        support.update(criterion_id='CA05', origin_ids=['ORI-0090'])
        with self.assertRaisesRegex(ValueError, 'Normative claim/origin'):
            builder.validate_operational_contracts(data)

    def test_relationship_cannot_restore_a_discarded_claim_criterion_pair(self):
        data = copy.deepcopy(self.data)
        op = next(p['operation_contract'] for p in data['decision_components'] if p['id'] == 'PAD-VIDEO-PROCESSO')
        variant=next(v for v in op['operation_variants'] if v['id'].endswith('-CAPTIONS'))
        support=next(s for s in variant['relations'][0]['claim_support'] if s['claim_id']=='CLM-K42-TD-ORI-0148')
        support.update(criterion_id='CA05', origin_ids=['ORI-0090'])
        with self.assertRaisesRegex(ValueError, 'Normative claim/origin'):
            builder.validate_operational_contracts(data)

    def test_haptic_alert_requires_audio_and_separate_recovery_confirmation(self):
        from experimental.v2.composer import Composer
        composer = Composer([])
        composer.base = self.data
        oid, rid = 'OP-PAD-RETORNO-HAPTICO-RUIDO', 'REL-PAD-RETORNO-HAPTICO-RUIDO-01'
        context = {'id':'SYN-HAPTIC-AUDIT','confirmed':True,'tarefas':['TAR-ACOMPANHAR-ORIENTACAO-317CD64'],
            'modalidades_disponiveis':['MOD-AUDIO'],
            'barreiras':['BAR-AUDIO-PODE-PERDER-EFETIVIDADE-COM-RUIDO-04E2CCE'],
            'funcoes_requeridas_ids':['FUN-FEEDBACK-PERCEPTIVEL','FUN-MANTER-INFORMACAO-RECUPERAVEL'],
            'participations':[{'id':'p','papel_id':'PAPEL-PESSOA-APOIADA','recurso_operado_ids':['REC-VIBRACAO','REC-SAIDA-AUDIO']}],
            'recursos_disponiveis':['REC-VIBRACAO'],'recursos_impedidos':['REC-SAIDA-AUDIO'],
            'facts':{'AudioUsable':True,oid+':conditions':True,rid+':sufficiency':True,rid+':temporal':True}}
        def operation():
            result = composer.compose_context(context)
            return next(row for row in result['capability_evaluations'] if row['id'] == oid), result
        row, _ = operation()
        self.assertEqual(row['state'], 'FAIL')
        context['recursos_impedidos'] = []
        context['recursos_disponiveis'].append('REC-SAIDA-AUDIO')
        row, result = operation()
        def recovery_state(evaluation):
            return next(c['state'] for c in evaluation['phase_conditions'] if c['id']==oid+':recoverable_message')
        self.assertEqual(recovery_state(row), 'PENDING')
        context['facts'][oid+':recoverable_message'] = False
        self.assertEqual(recovery_state(operation()[0]), 'FAIL')
        context['facts'][oid+':recoverable_message'] = True
        row,result=operation()
        self.assertEqual(recovery_state(row), 'PASS')
        # These independent checks do not authorize the historical haptic
        # relationship, which still lacks a scoped analytical application.
        self.assertFalse(any(step['id']==oid for choice in result['choices'] for step in choice['steps']))

    def test_legacy_criterion_bundles_are_not_used_as_whole_k_support(self):
        ops = {p['id']: p['operation_contract'] for p in self.data['decision_components'] if p.get('active_in_rc4')}
        self.assertTrue(all(s['criterion_id'] is None for s in ops['PAD-PAPEIS-TURNOS-AUTORIA']['claim_support']))
        self.assertNotIn('CA23', {s['criterion_id'] for s in ops['PAD-ORIENTACAO-AUDIO-RECUPERAVEL']['claim_support']})
        comm = ops['PAD-COMUNICACAO-MULTIFORMATO']['claim_support']
        self.assertEqual([(s['knowledge_id'], s['criterion_id']) for s in comm if s['criterion_id']], [('K28', 'CA88')])


if __name__ == '__main__':
    unittest.main(verbosity=2)
