"""Typed, lossless RDF catalogue. JSON is an authoring format, never a reader fallback.

Semantic edges are authoritative. Field/list nodes only preserve key presence,
ordering, primitive types and editorial metadata. They contain no JSON payload.
"""
from __future__ import annotations

import hashlib
import re
from urllib.parse import quote, unquote

from rdflib import Graph, Literal, Namespace, RDF, RDFS, OWL, URIRef, XSD

M = Namespace('https://w3id.org/mado#')
SC = Namespace('https://w3id.org/mado/catalogue#')
ROOT = SC.Catalogue

# Each key has its own predicate: aliases never silently merge distinct fields.
EDGE_NAMES = {
    'operation_contract': 'possuiContratoDeOperacao',
    'operation_variants': 'possuiVarianteOperacional',
    'inference_contract': 'possuiContratoDeDerivacao',
    'operation_claims': 'possuiParcelaOperacional',
    'operational_applications': 'possuiAplicacaoAnaliticaOperacional',
    'function_ids': 'funcoesDoContrato',
    'input_requirements': 'entradasRequeridasDoContrato',
    'output_spec': 'saidasDoContrato',
    'resource_requirements': 'requisitosDeRecursoDoContrato',
    'role_requirements': 'requisitosDePapelDoContrato',
    'requires_facts': 'fatosRequeridosDoContrato',
    'conditions': 'condicoesDoContrato',
    'condition_phases': 'condicoesPorFaseDoContrato',
    'claim_support': 'suportesDoContrato',
    'grounded_claim_ids': 'parcelasFundamentadorasDoContrato',
    'analytical_application_ids': 'aplicacoesAutorizadorasDoContrato',
    'relations': 'relacoesDoContrato',
    'all': 'exigeTodosOsItens',
    'any': 'exigeAlgumDosGrupos',
    'requires_all': 'requerTodasAsCondicoes',
    'requires_any': 'requerAlgumaCondicao',
    'support': 'suportesDaDerivacao',
    'knowledge_id': 'conhecimentoDoSuporteOperacional',
    'knowledge_ids': 'conhecimentosDoContrato',
    'claim_id': 'parcelaDoSuporteOperacional',
    'claim_ids': 'parcelasDaDerivacao',
    'criterion_id': 'criterioDoSuporteOperacional',
    'origin_ids': 'origensDoSuporteOperacional',
    'source_id': 'fonteDoSuporteOperacional',
    'source_ids': 'fontesDoContrato',
    'excerpt_id': 'trechoDoSuporteOperacional',
    'excerpt_ids': 'trechosDoContrato',
    'articulation_id': 'articulacaoDoSuporteOperacional',
    'contribution_ids': 'contribuicoesDoContrato',
    'fonte_id': 'fonteDoRegistroDoCatalogo',
    'fonte_ids': 'fontesDoRegistroDoCatalogo',
    'trecho_ids': 'trechosDoRegistroDoCatalogo',
    'from_operation_ids': 'operacoesDeOrigemDaRelacao',
    'to_operation_ids': 'operacoesDeDestinoDaRelacao',
    'from_function_ids': 'funcoesDeOrigemDaRelacao',
    'to_function_ids': 'funcoesDeDestinoDaRelacao',
    'from_representation_ids': 'representacoesDeOrigemDaRelacao',
    'to_representation_ids': 'representacoesDeDestinoDaRelacao',
    'representation_id': 'representacaoDoRequisito',
    'representation_ids': 'representacoesDoContrato',
    'selected_representation_ids': 'representacoesSelecionadasDoContrato',
    'operator_role_id': 'papelOperadorDoContrato',
    'subject_role_ids': 'papeisDoDestinatarioDoContrato',
    'task_ids': 'tarefasDoContrato',
    'transfer_scope': 'escopoDeTransferenciaDoContrato',
    'binding': 'vinculoInformacionalDaRelacao',
    'scope': 'escopoEstruturadoDoContrato',
    'premise_claim_ids': 'premissasDaAplicacaoOperacional',
    'parent_operation_id': 'operacaoBaseDaVariante',
    'required_information_components': 'componentesInformacionaisRequeridos',
    'rdf_application_id': 'fundamentoRdfDoContrato',
    'information_roles': 'papeisInformacionaisDaRelacao',
    'required_information': 'informacaoRequeridaPelaRelacao',
    'information_component': 'parcelaInformacionalDoPapel',
    'function_id': 'funcaoDoPapelInformacional',
    'role': 'papelInformacionalDeclarado',
    'alone_sufficient_for_goal': 'suficienciaIsoladaParaObjetivo',
    'each_alone_sufficient': 'suficienciaIsoladaDeCadaParcela',
    'joint_sufficiency_scope': 'escopoDaSuficienciaConjunta',
    'goal': 'objetivoDaRelacaoOperacional',
    'temporal_contract': 'contratoTemporalDaRelacao',
    'same_subject': 'exigeMesmoParticipante',
    'same_situation': 'exigeMesmaSituacao',
    'same_information_unit': 'exigeMesmaUnidadeInformacional',
    'meaning_unit': 'unidadeDeSignificadoDoContrato',
    'temporal': 'coordenacaoTemporalDeclarada',
    'verification_phase': 'faseDeVerificacaoDoContrato',
    'authorized_operation_ids': 'autorizaOperacao',
    'authorized_relation_ids': 'autorizaRelacaoOperacional',
    'authorized_requirement_ids': 'autorizaDerivacaoDeRequisito',
    'depends_on_application_ids': 'dependeDeAplicacaoAnalitica',
    'premises': 'premissasEstruturadasDaAplicacao',
    'criterion_support': 'suportesDeCriterioDaAplicacaoAnalitica',
    'requisito_ids': 'requisitosDaMatrizFuncional',
    'funcao_ids': 'funcoesDaMatrizFuncional',
    'caracteristica_ids': 'caracteristicasDaMatrizFuncional',
    'recurso_ids': 'recursosDaMatrizFuncional',
    'aplicabilidade': 'condicoesDeAplicabilidadeDoConhecimento',
    'tarefas': 'tarefasDaAplicabilidade',
    'barreiras': 'barreirasDaAplicabilidade',
    'ambientes': 'ambientesDaAplicabilidade',
    'recursos_disponiveis': 'recursosDaAplicabilidade',
    'recursos_digitais': 'recursosDigitaisDaAplicabilidade',
    'caracteristicas_pessoa': 'caracteristicasDaAplicabilidade',
    'ids': 'itensDaCondicaoOperacional',
    'situated_task_bindings': 'refinamentosDeTarefaSituada',
    'task_ids_all': 'exigeTodasAsTarefas',
    'rdf_task_id': 'tarefaRefinadaNoCatalogo',
    'required_facts': 'fatosNecessariosAoRefinamento',
    'requires_same_actor_and_situation': 'exigeMesmoAtorESituacao',
    'primary_contribution_ids': 'contribuicoesPrimariasDoContrato',
}
EDGES = {key: M[value] for key, value in EDGE_NAMES.items()}
REFERENCE_KEYS = {key for key in EDGES if key.endswith(('_id', '_ids'))}
REFERENCE_KEYS |= {'all', 'any', 'required_information_components'}
REFERENCE_KEYS |= {'tarefas', 'barreiras', 'ambientes', 'recursos_disponiveis',
                   'recursos_digitais', 'caracteristicas_pessoa', 'ids', 'task_ids_all'}
CLASSES = {
    'knowledge': M.ConhecimentoMultimodalArticulado,
    'sources': M.Fonte, 'excerpts': M.TrechoDocumental,
    'criteria': M.CriterioDeDecisaoMultimodal,
    'criterion_origins': M.RelacaoDeOrigemDoCriterio,
    'articulations': M.ArticulacaoDocumentada,
    'contributions': M.ContribuicaoNaArticulacao,
    'operation_contract': M.OperacaoDeInteracao,
    'operation_variants': M.OperacaoDeInteracao,
    'operation_claims': M.AfirmacaoOperacionalDocumentada,
    'operational_applications': M.AfirmacaoOperacionalDocumentada,
    'relations': M.RelacaoOperacional,
    'claim_support': M.SuporteOperacional,
    'input_requirements': M.RequisitoOperacional,
    'output_spec': M.RequisitoOperacional,
    'condition_phases': M.RequisitoOperacional,
    'inference_contract': M.DerivacaoDeRequisito,
    'information_roles': M.PapelInformacionalNaRelacao,
    'situated_task_bindings': M.RefinamentoDeTarefaSituada,
}
SC_CLASSES = (SC.Record, SC.List, SC.Value, SC.Null)

# Reuse the ontology's existing authoritative documentary relations instead of
# creating a second source/status graph that the executor would ignore.
NATIVE = {
    'knowledge': {'fonte_ids': M.derivadoDe, 'trecho_ids': M.sustentadoPorTrecho,
                  'enunciado': M.enunciado, 'articulacao': M.articulacao},
    'criteria': {'enunciado': M.enunciado},
    'excerpts': {'fonte_id': M.trechoDeFonte},
    'criterion_origins': {'fonte_id': M.origemEmFonte, 'trecho_id': M.origemSustentadaPorTrecho},
    'articulations': {'conhecimento_entrada_ids': M.articulaConhecimentoDeEntrada,
        'conhecimento_resultante_ids': M.produzConhecimento,
        'fonte_ids': M.articulacaoDerivadaDe, 'trecho_ids': M.articulacaoSustentadaPorTrecho,
        'habilitada_para_decisao': M.habilitadaParaDecisao,
        'nivel_confirmacao': M.nivelDeConfirmacao, 'estado_curadoria': M.estadoDeCuradoria},
    'contributions': {'articulation_id': M.contribuicaoNaArticulacao,
        'knowledge_id': M.contribuicaoParaConhecimento, 'excerpt_id': M.contribuicaoDoTrecho,
        'verification_status': M.estadoDeConferenciaDaContribuicao,
        'statement': M.afirmacaoDaContribuicao, 'justification': M.justificativaDaContribuicao},
    'operation_claims': {'source_ids': M.fonteDaAfirmacao, 'excerpt_ids': M.trechoDaAfirmacao,
        'contribution_ids': M.contribuicaoDaAfirmacao, 'function_ids': M.funcaoDaAfirmacao,
        'status': M.estadoDaAfirmacao, 'eligibility': M.elegibilidadeOperacional,
        'epistemic_status': M.estatutoEpistemicoDaAfirmacao, 'statement': M.enunciado,
        'limits': M.limiteDaAfirmacao},
    'operational_applications': {'status': M.elegibilidadeOperacional,
        'analytical_operation': M.operacaoDaAplicacaoAnalitica,
        'conditions': M.condicaoDaAplicacaoAnalitica, 'limits': M.limiteDaAfirmacao,
        'empirical_effect_authorized': M.efeitoEmpiricoAutorizado},
}
DATA_PREDICATES = {M.enunciado, M.articulacao, M.estadoDaAfirmacao,
    M.elegibilidadeOperacional, M.estatutoEpistemicoDaAfirmacao,
    M.limiteDaAfirmacao, M.operacaoDaAplicacaoAnalitica,
    M.condicaoDaAplicacaoAnalitica, M.efeitoEmpiricoAutorizado,
    M.habilitadaParaDecisao, M.nivelDeConfirmacao, M.estadoDeCuradoria,
    M.estadoDeConferenciaDaContribuicao, M.afirmacaoDaContribuicao, M.justificativaDaContribuicao}
LANG_PREDICATES = {M.enunciado, M.articulacao, M.limiteDaAfirmacao,
                  M.operacaoDaAplicacaoAnalitica, M.condicaoDaAplicacaoAnalitica,
                  M.afirmacaoDaContribuicao, M.justificativaDaContribuicao}
NATIVE_PREDICATES = set(p for fields in NATIVE.values() for p in fields.values())
REFERENCE_KEYS |= {'trecho_id'}
REFERENCE_KEYS |= {key for fields in NATIVE.values() for key in fields if key.endswith(('_id', '_ids'))}


def iri(identifier):
    return URIRef(identifier) if identifier.startswith(('http://', 'https://', 'urn:')) else M[identifier]


def _node(path):
    value = '/'.join(quote(str(part), safe='') for part in path)
    return SC['node-' + hashlib.sha256(value.encode('utf-8')).hexdigest()[:24]]


def _field_iri(prefix, key):
    """RDF/XML-safe QName; original field spelling is explicit metadata."""
    local = re.sub(r'[^A-Za-z0-9_-]', '_', key)
    if local != key:
        local = local[:64] + '-' + hashlib.sha256(key.encode('utf-8')).hexdigest()[:12]
    return SC[prefix + local]


def has_semantic_catalogue(graph):
    return graph.value(ROOT, SC.rootValue) is not None


def catalogue_schema_graph():
    g = Graph()
    for cls in SC_CLASSES + tuple(set(CLASSES.values())):
        g.add((cls, RDF.type, OWL.Class))
    for p in (SC.rootValue, *EDGES.values(), *(NATIVE_PREDICATES - DATA_PREDICATES)):
        g.add((p, RDF.type, OWL.ObjectProperty))
    # Editorial fields may hold either literal values or structural nodes.
    # They are annotations, never a substitute for the typed operational edges.
    for p in (SC.key, SC.orderFor, SC.identifier, SC.formatVersion, SC.hasField, SC.shortReferenceNamespace):
        g.add((p, RDF.type, OWL.AnnotationProperty))
    for p in (SC.literal, SC.primitiveType, *DATA_PREDICATES):
        g.add((p, RDF.type, OWL.DatatypeProperty))
    g.add((SC.NullValue, RDF.type, SC.Null))
    for key, p in EDGES.items():
        g.add((p, SC.key, Literal(key)))
    return g


def _clear(graph):
    for node in list(set(graph.subjects())):
        if str(node).startswith(str(SC) + 'node-') or node == ROOT:
            graph.remove((node, None, None))
        elif str(node).startswith('https://w3id.org/mado/experimental/v2#'):
            # Pilot authoring statements are reprojected below; stale pilot
            # operations must not remain after a curated removal.
            graph.remove((node, None, None))
        elif (node, RDF.type, SC.Record) in graph:
            for p in set(graph.predicates(node, None)):
                if str(p).startswith(str(SC)) or p in EDGES.values() or p in NATIVE_PREDICATES:
                    graph.remove((node, p, None))
            graph.remove((node, RDF.type, SC.Record))
            graph.remove((node, M.premissaOperacional, None))
            for cls in (M.OperacaoDeInteracao, M.RelacaoOperacional, M.SuporteOperacional,
                        M.RequisitoOperacional, M.DerivacaoDeRequisito):
                graph.remove((node, RDF.type, cls))
    # Dynamic field definitions are regenerated; no old authoring key survives.
    for p in list(set(graph.subjects(SC.key, None))) + list(set(graph.subjects(SC.orderFor, None))):
        if str(p).startswith(str(SC)):
            graph.remove((p, None, None))
    # Remove reserved container predicates from the pre-release serializer.
    for p in list(graph.subjects(RDF.type, OWL.AnnotationProperty)):
        if str(p).startswith(str(RDF) + '_'):
            graph.remove((p, None, None))
    graph.remove((URIRef('https://w3id.org/mado/experimental/v2'), None, None))


def project_semantic_catalogue(graph: Graph, data: dict) -> Graph:
    """Idempotent, typed projection. No filesystem access or JSON encoding."""
    _clear(graph)
    graph += catalogue_schema_graph()
    graph.bind('catalogue', SC)
    named = {}

    def write(value, path, key=None, reference=False, semantic=False):
        if value is None:
            return SC.NullValue
        if not isinstance(value, (dict, list)):
            if type(value) not in (str, bool, int, float):
                raise TypeError(f'Unsupported value at {path}: {type(value)}')
            if reference and isinstance(value, str):
                if key == 'primary_contribution_ids' and not value.startswith(('http://', 'https://', 'urn:')):
                    return URIRef('https://w3id.org/mado/experimental/v2#' + value)
                return iri(value)
            if not semantic:
                return Literal(value)
            node = _node(path)
            graph.add((node, RDF.type, SC.Value))
            graph.add((node, SC.primitiveType, Literal(type(value).__name__)))
            graph.add((node, SC.literal, Literal(value)))
            return node
        node = _node(path)
        if isinstance(value, list):
            graph.add((node, RDF.type, SC.List))
            if key == 'primary_contribution_ids' and all(isinstance(v, str) and not v.startswith(('http://', 'https://', 'urn:')) for v in value):
                graph.add((node, SC.shortReferenceNamespace, URIRef('https://w3id.org/mado/experimental/v2#')))
            for i, item in enumerate(value):
                # Own ordinal predicates preserve duplicates/order with one
                # statement per item, without redeclaring reserved rdf:_N.
                p = SC['item-' + str(i + 1)]
                graph.add((p, RDF.type, OWL.AnnotationProperty))
                graph.add((node, p, write(item, path + (i,), key, reference, semantic)))
            return node
        identifier = value.get('id')
        current = not any(any(token in str(part).lower() for token in
                              ('historical', 'previous', 'audit', 'snapshot')) for part in path)
        canonical = current and key in CLASSES and isinstance(identifier, str) and bool(identifier)
        if canonical:
            if key == 'sources' and 'pilot_catalogue' in path and not identifier.startswith(('http://', 'https://', 'urn:')):
                candidate = URIRef('https://w3id.org/mado/experimental/v2#' + identifier)
                # Early integration used the main namespace for two abbreviated
                # bibliographic bindings. These are the existing pilot sources,
                # not additional sources of knowledge.
                if identifier not in {row.get('id') for row in data.get('sources', [])}:
                    graph.remove((M[identifier], RDF.type, M.Fonte))
            else:
                candidate = iri(identifier)
            if candidate in named:
                if named[candidate] == value:
                    return candidate
                canonical = False
            if canonical:
                node = candidate
                named[node] = value
        graph.add((node, RDF.type, SC.Record))
        if current and key in CLASSES:
            # Anonymous support/requirement nodes have their own n-ary type.
            graph.add((node, RDF.type, CLASSES[key]))
        if canonical:
            graph.add((node, SC.identifier, Literal(identifier)))
        for field_key, field_value in value.items():
            override = NATIVE.get(key, {}).get(field_key) if current else None
            p = override or EDGES.get(field_key, _field_iri('field-', field_key))
            semantic_field = override is not None or field_key in EDGES
            object_field = semantic_field and p not in DATA_PREDICATES
            if semantic_field:
                # Replace the earlier documentary projection of this same
                # field, including old language tags, rather than unioning two
                # authoritative versions on a shared K/CA/claim individual.
                graph.remove((node, p, None))
            graph.add((p, SC.key, Literal(field_key)))
            alias = _field_iri('alias-', field_key)
            graph.add((alias, RDF.type, OWL.AnnotationProperty))
            graph.add((alias, SC.key, Literal(field_key)))
            graph.add((node, alias, p))
            if not semantic_field:
                graph.add((p, RDF.type, OWL.AnnotationProperty))
            child = write(field_value, path + (field_key,), field_key,
                          field_key in REFERENCE_KEYS, object_field)
            if p in LANG_PREDICATES and isinstance(child, Literal):
                child = Literal(str(child), lang='pt-BR')
            elif p in LANG_PREDICATES and isinstance(field_value, list):
                for position, literal in ordered_pairs(child):
                    if isinstance(literal, Literal):
                        graph.set((child, SC['item-' + str(position)], Literal(str(literal), lang='pt-BR')))
            if semantic_field and isinstance(field_value, list):
                order = _field_iri('order-', field_key +
                    ('-' + hashlib.sha256(str(p).encode()).hexdigest()[:10] if override else ''))
                graph.add((order, RDF.type, OWL.AnnotationProperty))
                graph.add((order, SC.orderFor, p))
                graph.add((node, order, child))
                for _, member in ordered_pairs(child):
                    graph.add((node, p, member))
            elif semantic_field and field_value is None:
                # Presence of a null field is recorded without inventing an IRI
                # target such as a "null criterion".
                order = _field_iri('order-', field_key +
                    ('-' + hashlib.sha256(str(p).encode()).hexdigest()[:10] if override else ''))
                graph.add((order, RDF.type, OWL.AnnotationProperty))
                graph.add((order, SC.orderFor, p))
                graph.add((node, order, SC.NullValue))
            else:
                graph.add((node, p, child))
        if current and key == 'operational_applications':
            # The native premise edge is cumulative, not a list of optional
            # alternatives. A missing edge is corruption, never fewer duties.
            for premise in value.get('premises', []):
                if premise.get('claim_id'):
                    graph.add((node, M.premissaOperacional, iri(premise['claim_id'])))
        return node

    def ordered_pairs(node):
        rows = []
        for p, value in graph.predicate_objects(node):
            suffix = str(p).removeprefix(str(SC) + 'item-')
            if str(p).startswith(str(SC) + 'item-') and suffix.isdigit():
                rows.append((int(suffix), value))
        return sorted(rows, key=lambda row: row[0])

    root = write(data, ('root',))
    graph.add((ROOT, SC.rootValue, root))
    graph.add((ROOT, SC.formatVersion, Literal('1.6.0-rc1')))
    for statement in data.get('pilot_catalogue', {}).get('statements', []):
        if statement['subject'] == 'https://w3id.org/mado/experimental/v2':
            # A single distributed ontology has a single current header.
            # The legacy header remains in the lossless authorship records.
            continue
        obj = URIRef(statement['object']) if statement['kind'] == 'iri' else Literal(
            statement['object'], lang=statement.get('language'),
            datatype=URIRef(statement['datatype']) if statement.get('datatype') else None)
        graph.add((URIRef(statement['subject']), URIRef(statement['predicate']), obj))
    return graph


def read_semantic_catalogue(graph: Graph) -> dict:
    """Load only graph statements; no JSON literal or authoring-file fallback."""
    root = graph.value(ROOT, SC.rootValue)
    if root is None:
        raise ValueError('Typed semantic catalogue is absent; no JSON fallback is permitted.')
    keys = {p: str(key) for p, key in graph.subject_objects(SC.key)}
    orders = {p: target for p, target in graph.subject_objects(SC.orderFor)}

    def identifier(node):
        value = graph.value(node, SC.identifier)
        if value is not None:
            return str(value)
        value = str(node)
        return value[len(str(M)):] if value.startswith(str(M)) else value

    def items(node):
        rows = []
        for p, value in graph.predicate_objects(node):
            suffix = str(p).removeprefix(str(SC) + 'item-')
            if str(p).startswith(str(SC) + 'item-') and suffix.isdigit():
                rows.append((int(suffix), value))
        return [v for _, v in sorted(rows, key=lambda row: row[0])]

    def read(node, reference=False, stack=()):
        if isinstance(node, Literal):
            value = node.toPython()
            if not isinstance(value, (str, bool, int, float)):
                raise ValueError(f'Unsupported primitive literal: {node.n3()}')
            return value
        if node == SC.NullValue:
            return None
        # A reference to K/CA/etc. is an identifier, not recursive expansion of
        # that source record. Anonymous group/requirement records remain maps.
        if reference and not str(node).startswith(str(SC)):
            return identifier(node)
        if node in stack:
            raise ValueError(f'Circular structural field: {node}')
        stack = stack + (node,)
        if (node, RDF.type, SC.List) in graph:
            short = graph.value(node, SC.shortReferenceNamespace)
            return [str(value)[len(str(short)):] if short and str(value).startswith(str(short))
                    else read(value, reference, stack) for value in items(node)]
        if (node, RDF.type, SC.Value) in graph:
            value = graph.value(node, SC.literal)
            if value is None:
                raise ValueError(f'Primitive field without literal: {node}')
            return read(value, False, stack)
        if (node, RDF.type, SC.Record) not in graph:
            raise ValueError(f'Untyped catalogue record: {node}')
        result = {}
        predicates = set(graph.predicates(node, None))
        local_keys = {p: str(graph.value(alias, SC.key))
                      for alias, p in graph.predicate_objects(node)
                      if str(alias).startswith(str(SC) + 'alias-')}
        present_fields = set(local_keys)
        handled = set()
        for order in predicates & orders.keys():
            p = orders[order]
            if p not in present_fields:
                continue
            key = local_keys[p]
            child = graph.value(node, order)
            values = set(graph.objects(node, p))
            if child == SC.NullValue:
                if len(values) > 1:
                    raise ValueError(f'Scalar relation with multiple targets: {node} {p}')
                result[key] = read(next(iter(values)), key in REFERENCE_KEYS, stack) if values else None
            else:
                original = items(child)
                present = [value for value in original if value in values]
                extras = sorted(values - set(original), key=str)
                short = graph.value(child, SC.shortReferenceNamespace)
                result[key] = [str(value)[len(str(short)):] if short and str(value).startswith(str(short))
                               else read(value, key in REFERENCE_KEYS, stack) for value in present + extras]
            handled.add(p)
        for p in present_fields - handled:
            key = local_keys[p]
            values = list(graph.objects(node, p))
            if len(values) != 1:
                raise ValueError(f'Non-list field has multiple values: {node} {p}')
            result[key] = read(values[0], key in REFERENCE_KEYS, stack)
        if 'premises' in result and (node, RDF.type, M.AfirmacaoOperacionalDocumentada) in graph:
            expected = {iri(p['claim_id']) for p in result['premises'] if p.get('claim_id')}
            actual = set(graph.objects(node, M.premissaOperacional))
            if expected != actual:
                result['semantic_integrity_errors'] = ['CUMULATIVE_PREMISE_EDGE_MISMATCH']
                for premise in result['premises']:
                    if premise.get('claim_id') and iri(premise['claim_id']) not in actual:
                        premise['missing_claim_id'] = premise['claim_id']
                        premise['claim_id'] = None
                        premise['semantic_integrity_error'] = 'MISSING_REQUIRED_PREMISE_EDGE'
                # An unqualified extra premise must also block this application.
                if actual - expected:
                    result['premises'].append({'knowledge_id': None, 'claim_id': None,
                        'semantic_integrity_error': 'UNQUALIFIED_PREMISE_EDGE'})
        return result

    result = read(root)
    if not isinstance(result, dict):
        raise ValueError('Catalogue root must be a record.')
    return result
