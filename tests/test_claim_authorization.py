"""Claim authority is separate from bibliography and contextual confirmation."""
import copy
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from engine import DecisionEngine


class ClaimAuthorizationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = DecisionEngine()

    def setUp(self):
        self.saved = copy.deepcopy(self.engine.knowledge)
        self.addCleanup(setattr, self.engine, 'knowledge', self.saved)
        self.context = copy.deepcopy(self.engine.current['context'])
        self.identifier, self.claim = next((kid, claim) for kid, row in self.engine.knowledge.items()
            for claim in row.get('operation_claims', [])
            if claim.get('status') == 'SUPPORTED_IN_RECORDED_SCOPE'
            and claim.get('eligibility') == 'DOCUMENTED_OPERATIONAL_CLAIM')
        row = self.engine.knowledge[self.identifier]
        self.context['tarefas'] = list(row.get('aplicabilidade', {}).get('tarefas', []))
        self.context['recursos_disponiveis'] = list(row.get('condicoes_necessarias_ids', []))
        self.context['recursos_impedidos'] = []
        self.context['barreiras'] = []

    def test_exact_source_excerpt_pairs_not_parallel_lists(self):
        self.claim['support'][0]['source_id'] = 'NONEXISTENT-SOURCE'
        state, reasons = self.engine.authorize_knowledge_claim(self.identifier, self.claim['id'], self.context)
        self.assertEqual(state, 'EXCLUIDO')
        self.assertTrue(any('trecho' in reason.lower() for reason in reasons))

    def test_proposed_is_not_context_conditional(self):
        self.claim['status'] = 'PROPOSED_OPERATIONALIZATION'
        self.claim['eligibility'] = 'PROPOSED_OPERATIONALIZATION'
        self.assertEqual(self.engine.authorize_knowledge_claim(self.identifier, self.claim['id'], self.context)[0], 'EXCLUIDO')

    def test_adding_only_reference_does_not_enable_an_assertion(self):
        self.engine.knowledge[self.identifier]['fonte_ids'].append('F01')
        self.assertEqual(self.engine.authorize_knowledge_claim(self.identifier, 'UNWRITTEN-CLAIM', self.context)[0], 'EXCLUIDO')

    def test_contradictory_pending_foundation_is_not_approved(self):
        self.claim['foundation_status'] = 'PENDING'
        self.assertEqual(self.engine.authorize_knowledge_claim(self.identifier, self.claim['id'], self.context)[0], 'EXCLUIDO')

    def test_claim_for_another_function_does_not_authorize_it(self):
        self.assertEqual(self.engine.authorize_knowledge_claim(self.identifier, self.claim['id'], self.context, 'FUN-NOT-SUPPORTED')[0], 'EXCLUIDO')

    def test_pending_game_efficacy_does_not_authorize_learning_claim(self):
        claims = self.engine.knowledge['K37']['operation_claims']
        pending = [row for row in claims if row['eligibility'] == 'NOT_ELIGIBLE']
        self.assertTrue(pending)
        for row in pending:
            self.assertEqual(self.engine.authorize_knowledge_claim('K37', row['id'], self.context)[0], 'EXCLUIDO')


if __name__ == '__main__':
    unittest.main()
