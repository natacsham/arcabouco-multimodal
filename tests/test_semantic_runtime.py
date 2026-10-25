"""Public RDF runtime causality checks. Narratives are synthetic test input only."""
import copy
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'vendor')]
from rdflib import Graph
from engine import DecisionEngine
from experimental.v2.trajectory import ResearchComposer
from semantic_catalogue import M, read_semantic_catalogue


def offered(result):
    return {step['id'] for field in ('choices', 'pending_candidates', 'partial_segments')
            for proposal in result.get(field, []) for step in proposal['steps']}


class SemanticRuntimeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = DecisionEngine()
        cases = json.loads((ROOT / 'tests/fixtures/articulation_transfer_cases.json').read_text(encoding='utf-8'))
        cls.engine.analyze_narrative(cases[0]['narrative'])
        cls.engine.update_context({'mapping_confirmed': True})
        cls.context = copy.deepcopy(cls.engine.current['context'])
        cls.context['participations'] = copy.deepcopy(cls.engine.current['participations'])
        cls.context['confirmed'] = True
        cls.original = cls.engine.generate_situated()

    def test_published_graph_contains_catalogue_and_four_preserved_pilot_operations(self):
        data = read_semantic_catalogue(self.engine.graph)
        self.assertEqual(data['metadata']['version'], '1.6.0-rc1')
        self.assertEqual(len(data['pilot_catalogue']['components']), 4)
        self.assertEqual(len({c['operation_contract']['id'] for c in data['pilot_catalogue']['components']}), 4)
        historical = json.loads((ROOT / 'experimental/v2/trajectory-bindings.json').read_text(encoding='utf-8'))
        self.assertEqual(data['pilot_catalogue']['bindings']['situated_task_bindings'], historical['situated_task_bindings'])

    def test_runtime_never_reads_authoring_json_or_independent_pilot_catalogue(self):
        original_open = Path.open
        forbidden = {'knowledge-base.json', 'base.ttl', 'schema.ttl', 'audio-review.ttl', 'trajectory-bindings.json'}
        def guarded(path, *args, **kwargs):
            if path.name in forbidden:
                raise AssertionError('Runtime attempted authoring/legacy input: ' + str(path))
            return original_open(path, *args, **kwargs)
        with patch.object(Path, 'open', guarded):
            result = ResearchComposer.from_public_graph(self.engine.graph).compose_context(copy.deepcopy(self.context))
        self.assertEqual(offered(result), offered(self.original))

    def test_removing_rdf_authorization_changes_decision_without_editing_python_or_json(self):
        graph = Graph()
        graph += self.engine.graph
        edge = (M['APP-ART-TRF-04-ORGANIZAR-RETOMAR'], M.autorizaOperacao,
                M['OP-PAD-ORGANIZAR-CONTEUDO-PERSISTENTE'])
        self.assertIn(edge, graph)
        self.assertIn(str(edge[2]).split('#')[-1], offered(self.original))
        graph.remove(edge)
        result = ResearchComposer.from_public_graph(graph).compose_context(copy.deepcopy(self.context))
        self.assertNotIn(str(edge[2]).split('#')[-1], offered(result))
        self.assertIn(edge, self.engine.graph, 'The frozen base must remain intact.')

    def test_execution_is_queryable_and_never_an_observed_outcome(self):
        summary = self.engine.inspect_execution()
        self.assertGreater(summary['counts']['checks'], 0)
        self.assertGreater(summary['counts']['operations'], 0)
        self.assertFalse(summary['observed_outcome'])
        self.assertFalse(summary['case_storage'])
        self.assertEqual(len(summary['query_ids']), 10)

    def test_clear_discards_the_ephemeral_graph_without_modifying_the_base(self):
        engine = DecisionEngine()
        base_count = len(engine.graph)
        engine._last_execution_graph = self.engine._last_execution_graph
        engine.clear()
        self.assertIsNone(engine._last_execution_graph)
        self.assertEqual(len(engine.graph), base_count)
        with self.assertRaises(ValueError):
            engine.inspect_execution()


if __name__ == '__main__':
    unittest.main()
