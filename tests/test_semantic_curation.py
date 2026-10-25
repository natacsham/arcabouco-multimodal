"""Semantic migration guards, not evidence of usefulness or human evaluation."""
import copy
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.migrate_semantic_curation import (migrate, validate_semantic_curation,
    contracts, KNOWLEDGE_REASONS, ART_REASONS, CARE_CLAIM, HAPTIC_OP, HAPTIC_APP, HAPTIC_REL)
from scripts.build_traceability_rdf import validate_contributions, validate_operational_contracts


class SemanticCurationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads((ROOT/'data'/'knowledge-base.json').read_text(encoding='utf-8'))

    def haptic(self, data):
        return next(c['operation_contract'] for c in data['decision_components']
                    if c.get('operation_contract',{}).get('id') == HAPTIC_OP)

    def test_curates_every_existing_record_without_whole_statement_promotion(self):
        self.assertEqual(set(KNOWLEDGE_REASONS), {k['id'] for k in self.data['knowledge']})
        self.assertEqual(set(ART_REASONS), {k['id'] for k in self.data['articulations']})
        self.assertEqual(45, len(self.data['knowledge']))
        self.assertEqual(17, len(self.data['articulations']))
        self.assertEqual(11, len(self.data['functional_matrix']))
        self.assertEqual(31, len(self.data['contributions']))
        for collection in ('knowledge','articulations','functional_matrix','contributions'):
            for record in self.data[collection]:
                review = record['semantic_curation']
                self.assertTrue(review['reason'])
                self.assertEqual(64, len(review['history']['sha256']))
                self.assertFalse(review['whole_statement_promoted'])
                self.assertFalse(review['human_evaluation'])
        self.assertEqual(45, len({k['semantic_curation']['reason'] for k in self.data['knowledge']}))

    def test_idempotent_and_does_not_remove_an_independently_migrated_pilot(self):
        self.assertEqual(self.data, migrate(self.data))
        data=copy.deepcopy(self.data)
        data['pilot_catalogue']={'independently_maintained':True}
        self.assertEqual(data['pilot_catalogue'], migrate(data)['pilot_catalogue'])

    def test_full_existing_validators_still_pass(self):
        validate_contributions(self.data)
        claims=validate_operational_contracts(self.data)
        self.assertIn(CARE_CLAIM,claims)
        validate_semantic_curation(self.data)

    def test_candidate_and_historical_flags_do_not_gain_authority(self):
        knowledge={k['id']:k for k in self.data['knowledge']}
        for kid in ('K36','K37','K38','K40','K43'):
            claim=next(c for c in knowledge[kid]['operation_claims'] if c['id']==f'CLM-{kid}-LEGACY')
            self.assertNotEqual('DOCUMENTED_OPERATIONAL_CLAIM', claim['eligibility'])
        matrix=next(m for m in self.data['functional_matrix'] if m['id']=='MF-05')
        self.assertEqual('PROPOSED_NOT_AUTHORIZED',matrix['semantic_curation']['disposition'])
        negative=next(a for a in self.data['articulations'] if a['id']=='ART-TESTE-NAO-CONFIRMADA')
        self.assertFalse(negative['habilitada_para_decisao'])
        self.assertFalse(negative['intellectual_synthesis']['authorized_application_ids'])

    def test_intellectual_construction_is_not_runtime_or_modal_combination(self):
        for art in self.data['articulations']:
            synthesis=art['intellectual_synthesis']
            self.assertFalse(synthesis['runtime_creates_this_synthesis'])
            self.assertFalse(synthesis['historical_enabled_flag_is_authorization'])
            self.assertTrue(synthesis['operation'])
            self.assertTrue(synthesis['conditional_formulation'])
        historical=next(a for a in self.data['articulations'] if a['id']=='ART-TRJ-04')
        self.assertFalse(historical['intellectual_synthesis']['authorized_application_ids'])
        sequence=next(r for _,o in contracts(self.data) for r in o.get('relations',[]) if r['id']=='REL-ART-TRF-04-DESCREVER-ORGANIZAR')
        self.assertEqual('SEQUENTIAL',sequence['kind'])
        self.assertEqual(1,len(set(sequence['required_information'])))

    def test_haptic_allocation_has_two_non_interchangeable_information_parts(self):
        op=self.haptic(self.data)
        rel=op['relations'][0]
        self.assertEqual(HAPTIC_REL,rel['id'])
        self.assertEqual([HAPTIC_APP],rel['analytical_application_ids'])
        self.assertEqual({'MOD-HAPTICO','MOD-AUDIO'},set(op['selected_representation_ids']))
        self.assertEqual({'DISPONIBILIDADE_DA_MENSAGEM','CONTEUDO_DA_ORIENTACAO'},set(rel['required_information']))
        self.assertTrue(all(r['alone_sufficient_for_goal'] is False for r in rel['information_roles']))
        self.assertIn(HAPTIC_OP+':same_event_binding', {f['id'] for f in op['requires_facts']})
        self.assertIn(HAPTIC_OP+':tactile_notice_needed', {f['id'] for f in op['requires_facts']})

    def test_deleting_a_modality_invalidates_the_complementary_contract(self):
        data=copy.deepcopy(self.data)
        self.haptic(data)['selected_representation_ids']=['MOD-AUDIO']
        with self.assertRaisesRegex(ValueError,'not selected'):
            validate_semantic_curation(data)

    def test_counting_two_modes_without_two_contributions_is_not_complementarity(self):
        data=copy.deepcopy(self.data)
        rel=self.haptic(data)['relations'][0]
        for role in rel['information_roles']:
            role['information_component']='ONE_UNDISTINGUISHED_MESSAGE'
        rel['required_information']=['ONE_UNDISTINGUISHED_MESSAGE']
        with self.assertRaisesRegex(ValueError,'Invalid complementary'):
            validate_semantic_curation(data)

    def test_missing_theoretical_contribution_blocks_analytical_authorization(self):
        data=copy.deepcopy(self.data)
        data['contributions']=[c for c in data['contributions'] if c['id']!='C-K40-CARE']
        with self.assertRaises(ValueError):
            validate_operational_contracts(data)

    def test_bibliographic_reference_cannot_replace_an_executable_premise(self):
        data=copy.deepcopy(self.data)
        app=next(a for art in data['articulations'] for a in art.get('operational_applications',[]) if a['id']==HAPTIC_APP)
        app['premises'][-1]['claim_id']=data['references'][0]['id']
        with self.assertRaisesRegex(ValueError,'Unusable analytical premise'):
            validate_operational_contracts(data)

    def test_mode_role_cannot_borrow_a_claim_outside_its_exact_application(self):
        data=copy.deepcopy(self.data)
        self.haptic(data)['relations'][0]['information_roles'][0]['claim_ids']=['CLM-K38-LEGACY']
        with self.assertRaisesRegex(ValueError,'Unfounded modal'):
            validate_semantic_curation(data)

    def test_point_review_does_not_upgrade_the_historical_study_or_claim_efficacy(self):
        contribution={c['id']:c for c in self.data['contributions']}
        self.assertEqual('CONFERIDA_NO_DOCUMENTO',contribution['C-K40-CARE']['verification_status'])
        self.assertEqual('CONFERIDA_NO_REGISTRO',contribution['C-K40-02']['verification_status'])
        app=next(a for art in self.data['articulations'] for a in art.get('operational_applications',[]) if a['id']==HAPTIC_APP)
        self.assertFalse(app['empirical_effect_authorized'])
        self.assertFalse(app['review']['human_evaluation'])
        self.assertEqual([{'criterion_id':'CA-CARE-COMPLEMENTARITY',
            'origin_ids':['ORI-CARE-COMPLEMENTARITY']}],app['criterion_support'])
        origin=next(o for o in self.data['criterion_origins']if o['id']=='ORI-CARE-COMPLEMENTARITY')
        self.assertEqual('TD-CARE-COMPLEMENTARITY',origin['trecho_id'])
        criterion=next(c for c in self.data['criteria']if c['id']=='CA-CARE-COMPLEMENTARITY')
        self.assertEqual('CRITERIO_ANALITICO_DE_CLASSIFICACAO_MMI',criterion['natureza'])
        self.assertFalse(criterion['human_evaluation'])


if __name__ == '__main__':
    unittest.main()
