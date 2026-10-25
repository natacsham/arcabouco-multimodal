"""Synthetic representation tests, not empirical validation of an orientation."""
import copy
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'vendor'))
sys.path.insert(0, str(ROOT))
from rdflib import Graph, Literal, RDF, BNode, Namespace
from pyshacl import validate
from semantic_catalogue import M, SC, EDGES, project_semantic_catalogue, read_semantic_catalogue, has_semantic_catalogue


def fixture():
    return {
        'empty': [], 'none': None, 'number': 2.5, 'boolean': False,
        'metadata': {'nested': {'literal': 'Não é um diagnóstico.'}},
        'decision_components': [{'id': 'PAD-TEST', 'operation_contract': {
            'id': 'OP-TEST', 'function_ids': ['FUN-A', 'FUN-B'],
            'input_requirements': [{'representation_id': 'MOD-TEXTO', 'required': True}],
            'output_spec': [{'representation_id': 'MOD-AUDIO', 'required': True}],
            'resource_requirements': {'all': ['REC-ONE'], 'any': [['REC-TWO', 'REC-THREE']]},
            'claim_support': [{'knowledge_id': 'K38', 'claim_id': 'CLM-K38',
                               'criterion_id': 'CA02', 'origin_ids': ['ORI-1']}],
            'relations': [], 'scope': {'condition': 'Não transferir para outra pessoa.'},
            'applicability_witness': {'any': [{'field': 'task_ids', 'ids': ['TAR-A']}]},
        }}],
    }


def catalogue_shapes():
    """Exercise only new catalogue integrity, with no unrelated fixture burden."""
    source = Graph().parse(ROOT / 'shapes/main.shacl.ttl', format='turtle')
    graph = Graph()
    pending = [M.OperacaoDoCatalogoShape, M.SuporteDoCatalogoShape,
               M.RelacaoDoCatalogoShape, M.PapelInformacionalDoCatalogoShape,
               M.PremissasDoCatalogoShape]
    seen = set()
    while pending:
        node = pending.pop()
        if node in seen:
            continue
        seen.add(node)
        for triple in source.triples((node, None, None)):
            graph.add(triple)
            if isinstance(triple[2], BNode):
                pending.append(triple[2])
    return graph


def grounded_fixture():
    graph = project_semantic_catalogue(Graph(), fixture())
    graph.add((M['CLM-K38'], M.afirmacaoDoConhecimento, M.K38))
    graph.add((M.CA02, M.possuiOrigem, M['ORI-1']))
    graph.add((M['ORI-1'], M.origemSustentadaPorTrecho, M['TD-1']))
    return graph


class SemanticCatalogueTests(unittest.TestCase):
    def test_small_lossless_roundtrip(self):
        data = fixture()
        graph = project_semantic_catalogue(Graph(), data)
        self.assertEqual(data, read_semantic_catalogue(graph))

    def test_complete_authoring_roundtrip(self):
        data = json.loads((ROOT / 'data/knowledge-base.json').read_text(encoding='utf-8-sig'))
        graph = project_semantic_catalogue(Graph(), data)
        self.assertEqual(data, read_semantic_catalogue(graph))
        self.assertLess(len(graph), 110000, 'Projection must remain viable for the browser.')

    def test_direct_semantic_mutation_changes_loader(self):
        graph = project_semantic_catalogue(Graph(), fixture())
        graph.remove((M['OP-TEST'], M.funcoesDoContrato, M['FUN-A']))
        graph.add((M['OP-TEST'], M.funcoesDoContrato, M['FUN-NEW']))
        loaded = read_semantic_catalogue(graph)
        self.assertEqual(loaded['decision_components'][0]['operation_contract']['function_ids'],
                         ['FUN-B', 'FUN-NEW'])

    def test_exact_support_is_queryable_without_json(self):
        graph = grounded_fixture()
        rows = list(graph.query('''
            PREFIX m: <https://w3id.org/mado#>
            SELECT ?knowledge ?claim ?criterion ?origin WHERE {
              m:OP-TEST m:suportesDoContrato ?s .
              ?s m:conhecimentoDoSuporteOperacional ?knowledge ;
                 m:parcelaDoSuporteOperacional ?claim ;
                 m:criterioDoSuporteOperacional ?criterion ;
                 m:origensDoSuporteOperacional ?origin .
            }
        '''))
        self.assertEqual([tuple(row) for row in rows], [(M.K38, M['CLM-K38'], M.CA02, M['ORI-1'])])

    def test_serialized_json_not_used_or_required(self):
        graph = project_semantic_catalogue(Graph(), fixture())
        graph.add((M['OP-TEST'], M.contratoOperacionalSerializado, Literal('invalid JSON should be ignored')))
        self.assertEqual(read_semantic_catalogue(graph), fixture())
        graph.remove((None, M.contratoOperacionalSerializado, None))
        self.assertEqual(read_semantic_catalogue(graph), fixture())

    def test_native_authorization_is_authoritative(self):
        data = {'articulations': [{'id': 'ART-X', 'operational_applications': [{
            'id': 'APP-X', 'status': 'GROUNDED_ANALYTICAL_APPLICATION',
            'authorized_operation_ids': ['OP-TEST'], 'premises': [
                {'knowledge_id': 'K38', 'claim_id': 'CLM-K38'}]}]}]}
        graph = project_semantic_catalogue(Graph(), data)
        graph.remove((M['APP-X'], M.autorizaOperacao, M['OP-TEST']))
        loaded = read_semantic_catalogue(graph)
        self.assertEqual(loaded['articulations'][0]['operational_applications'][0]['authorized_operation_ids'], [])

    def test_missing_cumulative_premise_invalidates_only_dependent_application(self):
        data = {'articulations': [{'id': 'ART-X', 'operational_applications': [{
            'id': 'APP-X', 'premises': [{'knowledge_id': 'K38', 'claim_id': 'CLM-K38'}]},
            {'id': 'APP-OTHER', 'premises': [{'knowledge_id': 'K43', 'claim_id': 'CLM-K43'}]}]}]}
        graph = project_semantic_catalogue(Graph(), data)
        self.assertTrue(validate(graph, shacl_graph=catalogue_shapes())[0])
        graph.remove((M['APP-X'], M.premissaOperacional, M['CLM-K38']))
        self.assertFalse(validate(graph, shacl_graph=catalogue_shapes())[0])
        applications = read_semantic_catalogue(graph)['articulations'][0]['operational_applications']
        self.assertEqual(applications[0]['premises'][0]['missing_claim_id'], 'CLM-K38')
        self.assertIsNone(applications[0]['premises'][0]['claim_id'])
        self.assertEqual(applications[1], data['articulations'][0]['operational_applications'][1])

    def test_native_eligibility_and_source_are_authoritative(self):
        data = {'knowledge': [{'id': 'K38', 'operation_claims': [{
            'id': 'CLM-K38', 'eligibility': 'DOCUMENTED_OPERATIONAL_CLAIM',
            'status': 'DOCUMENTED', 'source_ids': ['F1'], 'function_ids': []}]}]}
        graph = project_semantic_catalogue(Graph(), data)
        graph.set((M['CLM-K38'], M.elegibilidadeOperacional, Literal('NOT_ELIGIBLE')))
        graph.remove((M['CLM-K38'], M.fonteDaAfirmacao, M.F1))
        loaded = read_semantic_catalogue(graph)['knowledge'][0]['operation_claims'][0]
        self.assertEqual(loaded['eligibility'], 'NOT_ELIGIBLE')
        self.assertEqual(loaded['source_ids'], [])

    def test_missing_catalogue_fails_closed(self):
        graph = Graph()
        graph.add((M['OP-TEST'], M.contratoOperacionalSerializado, Literal('{}')))
        self.assertFalse(has_semantic_catalogue(graph))
        with self.assertRaisesRegex(ValueError, 'absent'):
            read_semantic_catalogue(graph)

    def test_projection_is_idempotent_and_removes_old_operations(self):
        data = fixture()
        graph = project_semantic_catalogue(Graph(), data)
        original = set(graph)
        project_semantic_catalogue(graph, data)
        self.assertEqual(set(graph), original)
        project_semantic_catalogue(graph, {'decision_components': []})
        self.assertNotIn((M['OP-TEST'], RDF.type, M.OperacaoDeInteracao), graph)
        self.assertEqual(read_semantic_catalogue(graph), {'decision_components': []})

    def test_pilot_statements_are_real_triples_and_migrate_losslessly(self):
        data = fixture()
        data['pilot_catalogue'] = {'components': [], 'bindings': {}, 'statements': [
            {'subject': 'https://example.org/op', 'predicate': str(RDF.type),
             'object': 'https://w3id.org/mado/experimental/v2#Capability', 'kind': 'iri'},
        ]}
        graph = project_semantic_catalogue(Graph(), data)
        from rdflib import URIRef
        self.assertIn((URIRef('https://example.org/op'), RDF.type,
                       URIRef('https://w3id.org/mado/experimental/v2#Capability')), graph)
        self.assertEqual(read_semantic_catalogue(graph), data)

    def test_pilot_source_bindings_reuse_original_namespace(self):
        from rdflib import URIRef
        data = {'pilot_catalogue': {'bindings': {'situated_task_bindings': [{
            'id': 'BIND-X', 'sources': [{'id': 'SourceMMI', 'locator': '1.2'}],
            'primary_contribution_ids': ['CReviewMMI'],
        }]}, 'statements': []}}
        graph = project_semantic_catalogue(Graph(), data)
        source = URIRef('https://w3id.org/mado/experimental/v2#SourceMMI')
        self.assertIn((source, RDF.type, M.Fonte), graph)
        self.assertNotIn((M.SourceMMI, RDF.type, M.Fonte), graph)
        self.assertEqual(read_semantic_catalogue(graph), data)

    def test_shacl_checks_complete_support_and_rejects_wrong_pair(self):
        graph = grounded_fixture()
        shapes = catalogue_shapes()
        self.assertTrue(validate(graph, shacl_graph=shapes)[0])
        support = next(graph.objects(M['OP-TEST'], M.suportesDoContrato))
        graph.set((support, M.conhecimentoDoSuporteOperacional, M.K43))
        self.assertFalse(validate(graph, shacl_graph=shapes)[0])

    def test_shacl_rejects_wrong_criterion_origin(self):
        graph = grounded_fixture()
        support = next(graph.objects(M['OP-TEST'], M.suportesDoContrato))
        graph.set((support, M.origensDoSuporteOperacional, M['ORI-OTHER']))
        self.assertFalse(validate(graph, shacl_graph=catalogue_shapes())[0])

    def test_shacl_rejects_removed_all_function_or_support_links(self):
        for predicate in (M.funcoesDoContrato, M.suportesDoContrato):
            graph = grounded_fixture()
            graph.remove((M['OP-TEST'], predicate, None))
            self.assertFalse(validate(graph, shacl_graph=catalogue_shapes())[0])


if __name__ == '__main__':
    unittest.main()
