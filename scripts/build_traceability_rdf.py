"""Project public, reviewed JSON contributions onto the existing public RDF.

No private document or legacy extraction is read. This builder does not infer
new knowledge, promote documentary states, or generate a user's decision.
The sorted N-Triples output is a valid, deterministic Turtle subset.
"""
import argparse
from datetime import date
import hashlib
import json
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
sys.dont_write_bytecode = True
sys.path.insert(0, str(ROOT / "vendor"))
from rdflib import BNode, Graph, Literal, Namespace, OWL, RDF, RDFS, URIRef, XSD
from rdflib.namespace import SKOS
from urllib.parse import urlsplit
from rdflib.compare import to_canonical_graph

M = Namespace("https://w3id.org/mado#")
DCT = Namespace("http://purl.org/dc/terms/")
STATES = {"CONFERIDA_NO_DOCUMENTO", "CONFERIDA_NO_REGISTRO", "PENDENTE"}
ART_TEXT = {
    "operation_explanation": M.explicacaoDaOperacaoAnalitica,
    "added_understanding": M.compreensaoAcrescentada,
    "authorship": M.autoriaDaArticulacao,
    "reconstruction_origin": M.origemDaReconstrucao,
}
CONTRIBUTION_TEXT = {
    "statement": M.afirmacaoDaContribuicao,
    "justification": M.justificativaDaContribuicao,
}
CONTRIBUTION_CODES = {
    "contribution_role": M.papelDaContribuicao,
    "nature": M.naturezaDaContribuicao,
    "verification_status": M.estadoDeConferenciaDaContribuicao,
    "reviewer": M.responsavelPelaConferencia,
}


def validate_contributions(data):
    indexes = {key: {r["id"]: r for r in data[key]}
               for key in ("knowledge", "articulations", "excerpts", "sources")}
    seen = set()
    for row in data.get("contributions", []):
        required = ("id", "articulation_id", "knowledge_id", "excerpt_id",
                    *CONTRIBUTION_TEXT, *CONTRIBUTION_CODES, "review_date")
        for key in required:
            if not isinstance(row.get(key), str) or not row[key].strip():
                raise ValueError(f"Contribuição {row.get('id')}: campo ausente/vazio {key}")
        if row["id"] in seen:
            raise ValueError(f"Contribuição duplicada: {row['id']}")
        seen.add(row["id"])
        if row["verification_status"] not in STATES:
            raise ValueError(f"Estado documental desconhecido: {row['id']}")
        date.fromisoformat(row["review_date"])
        art = indexes["articulations"][row["articulation_id"]]
        k = indexes["knowledge"][row["knowledge_id"]]
        excerpt = indexes["excerpts"][row["excerpt_id"]]
        if excerpt["fonte_id"] not in indexes["sources"]:
            raise ValueError(f"Fonte inexistente no trecho: {row['id']}")
        if k["id"] not in art["conhecimento_resultante_ids"]:
            raise ValueError(f"Conhecimento não é produto da articulação: {row['id']}")
        if excerpt["id"] not in k["trecho_ids"] or excerpt["id"] not in art["trecho_ids"]:
            raise ValueError(f"Trecho não pertence ao conhecimento e à articulação: {row['id']}")
        if excerpt["fonte_id"] not in k["fonte_ids"]:
            raise ValueError(f"Fonte do trecho não sustenta o conhecimento: {row['id']}")
        if "source_id" in row or "fonte_id" in row:
            raise ValueError(f"Fonte deve ser resolvida somente pelo trecho: {row['id']}")
        for key in ART_TEXT:
            if not isinstance(art.get(key), str) or not art[key].strip():
                raise ValueError(f"Operação analítica incompleta: {art['id']}/{key}")
    return indexes


def replace_values(graph, subject, predicate, values):
    graph.remove((subject, predicate, None))
    for value in values:
        graph.add((subject, predicate, value))


def project_documentary_metadata(graph, data):
    """Links and conference states are annotations, not approval conditions.

    Uses only existing records. No original is fetched, no quotation restored,
    and no bibliographic reference is promoted to operational knowledge.
    """
    for collection in ("sources", "references", "excerpts", "criterion_origins"):
        for row in data.get(collection, []):
            node = M[row["id"]]
            url = row.get("document_url") or row.get("url")
            replace_values(graph, node, RDFS.seeAlso,
                           [URIRef(url)] if url and urlsplit(url).scheme in {"http", "https"}
                           and urlsplit(url).netloc else [])
            for field, predicate in (("document_version", M.versaoDocumental),
                                     ("document_review_status", M.estadoDeConferenciaDocumental),
                                     ("document_review_date", M.dataDaConsultaDocumental),
                                     ("document_paraphrase", M.parafraseDocumental)):
                value = row.get(field)
                if field == "document_version":
                    value = value or row.get("edition")
                elif field == "document_review_status":
                    value = value or row.get("access_status") or row.get("status_localizacao")
                elif field == "document_review_date":
                    value = value or row.get("consulted_at")
                replace_values(graph, node, predicate, [Literal(value)] if value else [])
            if row.get("localizacao_publica"):
                replace_values(graph, node, M.localizacaoDocumental,
                               [Literal(row["localizacao_publica"])])
            if collection == "references":
                replace_values(graph, node, DCT.bibliographicCitation,
                               [Literal(row["referencia_exata"])] if row.get("referencia_exata") else [])
                replace_values(graph, node, DCT.isReferencedBy,
                               [M[row["fonte_que_cita_id"]]] if row.get("fonte_que_cita_id") else [])


def validate_operational_contracts(data):
    """Check exact documentary pairs, never infer approval from a K or an ID."""
    knowledge = {r['id']: r for r in data.get('knowledge', [])}
    excerpts = {r['id']: r for r in data.get('excerpts', [])}
    sources = {r['id']: r for r in data.get('sources', [])}
    origins = {r['id']: r for r in data.get('criterion_origins', [])}
    contributions = {r['id']: r for r in data.get('contributions', [])}
    concepts = {r['id'] for r in data.get('context_elements', [])}
    claims = {}
    for kid, k in knowledge.items():
        for claim in k.get('operation_claims', []):
            cid = claim['id']
            if cid in claims:
                raise ValueError('Duplicate claim: ' + cid)
            claims[cid] = (kid, claim)
            eligible = claim.get('eligibility') == 'DOCUMENTED_OPERATIONAL_CLAIM'
            if eligible and claim.get('status') != 'SUPPORTED_IN_RECORDED_SCOPE':
                raise ValueError('Eligible claim lacks supported state: ' + cid)
            if claim.get('scope', {}).get('empirical_effect_authorized') is not False:
                raise ValueError('Migration cannot assert empirical effect: ' + cid)
            if not eligible:
                continue
            if not claim.get('support') or not claim.get('limits'):
                raise ValueError('Eligible claim lacks scoped support: ' + cid)
            pairs = set()
            for support in claim['support']:
                sid, tid = support['source_id'], support['excerpt_id']
                if (sid not in sources or tid not in excerpts or excerpts[tid].get('fonte_id') != sid
                        or sid not in k.get('fonte_ids', []) or tid not in k.get('trecho_ids', [])
                        or not support.get('support_scope') or not support.get('locator')):
                    raise ValueError('Invalid exact source/excerpt pair: ' + cid)
                if support.get('original_document_rechecked_in_this_migration') is not False:
                    raise ValueError('Migration must not invent original review: ' + cid)
                pairs.add((sid, tid))
            if ({s for s, _ in pairs} != set(claim['source_ids'])
                    or {t for _, t in pairs} != set(claim['excerpt_ids'])):
                raise ValueError('Claim index differs from exact support: ' + cid)
            for cid_ref in claim.get('contribution_ids', []):
                c = contributions.get(cid_ref, {})
                if c.get('knowledge_id') != kid or c.get('excerpt_id') not in claim['excerpt_ids']:
                    raise ValueError('Contribution belongs to another claim scope: ' + cid)
            for cid_ref in claim.get('review_basis_ids', []):
                c = contributions.get(cid_ref, {})
                if c.get('excerpt_id') not in claim['excerpt_ids'] or c.get('statement') != claim['statement']:
                    raise ValueError('Reused review does not support the same statement: ' + cid)
            if not set(claim.get('function_ids', [])) <= concepts:
                raise ValueError('Undefined function: ' + cid)
    for row in data.get('functional_matrix', []):
        contract = row.get('inference_contract')
        if not contract:
            continue
        if any(ref not in claims for ref in contract['claim_ids']):
            raise ValueError('Unknown matrix claim: ' + row['id'])
        if 'required_information_components' in contract:
            components = contract['required_information_components']
            if (not isinstance(components, list) or not components
                    or not set(components) <= {'VISUAL', 'SONORO'}):
                raise ValueError('Invalid required information component: ' + row['id'])
        for field in ('modos_que_podem_apoiar', 'modos_com_risco', 'requisito_ids', 'funcao_ids'):
            if not set(row.get(field, [])) <= concepts:
                raise ValueError('Undefined matrix concept: ' + row['id'])
        if contract['eligibility'] == 'DOCUMENTED_OPERATIONAL_CLAIM' and not any(
                claims[c][1]['eligibility'] == 'DOCUMENTED_OPERATIONAL_CLAIM' for c in contract['claim_ids']):
            raise ValueError('Matrix requires an eligible claim: ' + row['id'])
    for row in data.get('decision_components', []):
        op = row.get('operation_contract')
        if not op:
            continue
        if op['id'] != 'OP-' + row['id']:
            raise ValueError('Operation attached to wrong pattern: ' + row['id'])
    for op in iter_operation_contracts(data):
        if not set(op['function_ids'] + op['representation_ids']) <= concepts:
            raise ValueError('Undefined operation concept: ' + op['id'])
        witness = op.get('applicability_witness', {})
        for condition in witness.get('all', []) + witness.get('any', []):
            if condition.get('field') == 'required_information_components':
                components = condition.get('ids')
                if (not isinstance(components, list) or not components
                        or not set(components) <= {'VISUAL', 'SONORO'}):
                    raise ValueError('Invalid operation information component: ' + op['id'])
        supports = op['claim_support'] + [support for relation in op.get('relations', [])
                                          for support in relation.get('claim_support', [])]
        for support in supports:
            pair = claims.get(support['claim_id'])
            if not pair or pair[0] != support['knowledge_id']:
                raise ValueError('Wrong operation/knowledge claim: ' + op['id'])
            if pair[1]['eligibility'] != 'DOCUMENTED_OPERATIONAL_CLAIM':
                raise ValueError('Pending claim cannot authorize operation: ' + op['id'])
            criterion = support.get('criterion_id')
            if not criterion and support.get('origin_ids'):
                raise ValueError('Orphan criterion/origin reference: ' + op['id'])
            if criterion and (not support.get('origin_ids') or any(
                    origins.get(oid, {}).get('criterio_id') != criterion for oid in support['origin_ids'])):
                raise ValueError('Wrong exact criterion/origin pair: ' + op['id'])
            review = support.get('semantic_pair_review', {})
            direct_norm = (review.get('scope') == 'DIRECT_NORMATIVE_CLAUSE'
                           or set(pair[1].get('source_ids',[])) == {'FN-WCAG'})
            if direct_norm and any(
                    origins.get(oid, {}).get('trecho_id') not in pair[1]['excerpt_ids']
                    for oid in support.get('origin_ids', [])):
                raise ValueError('Normative claim/origin excerpt mismatch: ' + op['id'])
    validate_analytical_applications(data, claims)
    return claims


def iter_operation_contracts(data):
    """Yield declared parents and their explicitly identified variants."""
    for row in data.get('decision_components', []):
        parent = row.get('operation_contract')
        if not parent:
            continue
        yield parent
        for variant in parent.get('operation_variants', []):
            if variant.get('parent_operation_id') != parent['id']:
                raise ValueError('Wrong variant parent: ' + variant.get('id', '?'))
            merged = dict(parent, **variant)
            merged.pop('operation_variants', None)
            yield merged


def validate_analytical_applications(data, claims):
    """Analytical support is exact, scoped and dependency checked, not a score.

    A historic articulation is not an executable permission. Every operational
    application must independently identify its premises, result and targets.
    """
    arts = {r['id']: r for r in data.get('articulations', [])}
    contributions = {r['id']: r for r in data.get('contributions', [])}
    origins = {r['id']: r for r in data.get('criterion_origins', [])}
    excerpts = {r['id']: r for r in data.get('excerpts', [])}
    concepts = {r['id'] for r in data.get('context_elements', [])}
    operations = {r['id']: r for r in iter_operation_contracts(data)}
    relations = {r['id']: r for op in operations.values() for r in op.get('relations', [])}
    requirements = {r['id']: r for r in data.get('functional_matrix', [])}
    apps = {}
    for art in arts.values():
        for app in art.get('operational_applications', []):
            aid = app['id']
            if aid in apps:
                raise ValueError('Duplicate analytical application: ' + aid)
            apps[aid] = app
            if app.get('status') != 'GROUNDED_ANALYTICAL_APPLICATION':
                raise ValueError('Unknown analytical application status: ' + aid)
            if app.get('empirical_effect_authorized') is not False:
                raise ValueError('Analytical application cannot assert empirical effect: ' + aid)
            for field in ['premises', 'analytical_operation', 'result', 'function_ids', 'limits', 'conditions']:
                if not app.get(field):
                    raise ValueError('Incomplete analytical application ' + aid + ': ' + field)
            if not any(app.get(field) for field in ('authorized_operation_ids',
                                                    'authorized_relation_ids', 'authorized_requirement_ids')):
                raise ValueError('Analytical application has no authorized target: ' + aid)
            if not set(app['function_ids']) <= concepts:
                raise ValueError('Unknown analytical function: ' + aid)
            premise_excerpts = set()
            for premise in app['premises']:
                pair = claims.get(premise.get('claim_id'))
                if (not pair or pair[0] != premise.get('knowledge_id')
                        or pair[1].get('eligibility') != 'DOCUMENTED_OPERATIONAL_CLAIM'):
                    raise ValueError('Unusable analytical premise: ' + aid)
                claim = pair[1]
                premise_excerpts.update(claim.get('excerpt_ids', []))
                if not premise.get('contribution_ids'):
                    raise ValueError('Analytical premise lacks a localized contribution: ' + aid + '/' + premise['claim_id'])
                for cid in premise.get('contribution_ids', []):
                    c = contributions.get(cid, {})
                    if (cid not in claim.get('contribution_ids', [])
                            or c.get('knowledge_id') != premise['knowledge_id']
                            or c.get('excerpt_id') not in claim.get('excerpt_ids', [])
                            or c.get('verification_status') not in STATES - {'PENDENTE'}
                            or c.get('articulation_id') not in arts):
                        raise ValueError('Unusable analytical contribution: ' + aid + '/' + cid)
            for support in app.get('criterion_support', []):
                if not support.get('origin_ids'):
                    raise ValueError('Analytical criterion lacks origin: ' + aid)
                for oid in support['origin_ids']:
                    origin = origins.get(oid, {})
                    if (origin.get('criterio_id') != support['criterion_id']
                            or origin.get('trecho_id') not in premise_excerpts
                            or origin.get('trecho_id') not in excerpts):
                        raise ValueError('Analytical criterion not supported by exact premise: ' + aid + '/' + oid)
            if not set(app.get('authorized_operation_ids', [])) <= set(operations):
                raise ValueError('Unknown authorized operation: ' + aid)
            if not set(app.get('authorized_relation_ids', [])) <= set(relations):
                raise ValueError('Unknown authorized relation: ' + aid)
            if not set(app.get('authorized_requirement_ids', [])) <= set(requirements):
                raise ValueError('Unknown authorized requirement: ' + aid)
    for matrix in requirements.values():
        contract = matrix.get('inference_contract', {})
        for group in [contract, *contract.get('trigger_groups', [])]:
            for aid in group.get('analytical_application_ids', []):
                if aid not in apps or matrix['id'] not in apps[aid].get('authorized_requirement_ids', []):
                    raise ValueError('Analytical application does not authorize requirement: ' + matrix['id'])
                if not set(group.get('funcao_ids', matrix.get('funcao_ids', []))) & set(apps[aid]['function_ids']):
                    raise ValueError('Analytical requirement lacks function scope: ' + matrix['id'])
    for op in operations.values():
        for phase in op.get('condition_phases', []):
            if not phase.get('id') or not phase.get('label') or phase.get('phase') not in {'precondition','production','verification'}:
                raise ValueError('Invalid condition phase: ' + op['id'])
        for record, target_field in [(op, 'authorized_operation_ids')] + [
                (rel, 'authorized_relation_ids') for rel in op.get('relations', [])]:
            for aid in record.get('analytical_application_ids', []):
                if aid not in apps or record['id'] not in apps[aid][target_field]:
                    raise ValueError('Analytical application does not authorize target: ' + record['id'])
        for relation in op.get('relations', []):
            if relation.get('analytical_application_ids') and relation.get('scope') == 'BETWEEN_OPERATIONS':
                binding = relation.get('binding', {})
                if not all(binding.get(key) is True for key in ('same_subject', 'same_situation', 'same_information_unit')):
                    raise ValueError('Analytical dependency lacks situated binding: ' + relation['id'])
                for endpoint, spec_field, mode_field in [('from_operation_ids', 'output_spec', 'from_representation_ids'),
                                                        ('to_operation_ids', 'input_requirements', 'to_representation_ids')]:
                    if not relation.get(endpoint) or not set(relation[endpoint]) <= set(operations):
                        raise ValueError('Analytical dependency has unknown endpoint: ' + relation['id'])
                    for oid in relation[endpoint]:
                        available = {row['representation_id'] for row in operations[oid].get(spec_field, [])
                                     if row.get('meaning_unit') == relation.get('meaning_unit')}
                        if not set(relation.get(mode_field, [])) or not set(relation[mode_field]) <= available:
                            raise ValueError('Analytical dependency changes information contract: ' + relation['id'])
            if not relation.get('analytical_application_ids') or relation.get('scope')!='WITHIN_OPERATION':
                continue
            meaning=relation.get('meaning_unit')
            available={row['representation_id'] for row in op.get('input_requirements',[])+op.get('output_spec',[])
                       if row.get('meaning_unit')==meaning}
            if (not meaning or not set(relation.get('from_representation_ids',[])) <= available
                    or not set(relation.get('to_representation_ids',[])) <= available):
                raise ValueError('Analytical relation inconsistent with information specifications: '+relation['id'])
            if op.get('selected_representation_ids') and not set(relation.get('to_representation_ids',[])) <= set(op['selected_representation_ids']):
                raise ValueError('Analytical relation delivers an unselected representation: '+relation['id'])
        for field in ('output_resource_ids', 'recipient_resource_ids', 'selected_representation_ids'):
            if not set(op.get(field, [])) <= concepts:
                raise ValueError('Unknown selected output/resource: ' + op['id'] + '/' + field)
    def visit(aid, stack, seen):
        if aid in stack:
            raise ValueError('Circular analytical authorization: ' + aid)
        if aid in seen:
            return
        if aid not in apps:
            raise ValueError('Unknown analytical dependency: ' + aid)
        for dependency in apps[aid].get('depends_on_application_ids', []):
            visit(dependency, stack | {aid}, seen)
        seen.add(aid)
    seen = set()
    for aid in apps:
        visit(aid, set(), seen)
    return apps


def project_operational_contracts(graph, data):
    """Project the same scoped claims; do not rewrite historical K review states."""
    for old in list(graph.subjects(M.contratoOperacionalSerializado, None)):
        graph.remove((old, M.contratoOperacionalSerializado, None))
        graph.remove((old, M.fundamentadaPorAplicacaoAnalitica, None))
    for old in list(graph.subjects(RDF.type, M.AfirmacaoOperacionalDocumentada)):
        graph.remove((old, None, None))
        graph.remove((None, None, old))
    for k in data.get('knowledge', []):
        for claim in k.get('operation_claims', []):
            node = M[claim['id']]
            graph.add((node, RDF.type, M.AfirmacaoOperacionalDocumentada))
            graph.add((node, M.identificador, Literal(claim['id'])))
            graph.add((node, M.enunciado, Literal(claim['statement'], lang='pt-BR')))
            graph.add((node, M.afirmacaoDoConhecimento, M[k['id']]))
            graph.add((M[k['id']], M.possuiAfirmacaoOperacional, node))
            for key, prop in [('eligibility', M.elegibilidadeOperacional), ('status', M.estadoDaAfirmacao),
                              ('epistemic_status', M.estatutoEpistemicoDaAfirmacao)]:
                graph.add((node, prop, Literal(claim[key])))
            for key, prop in [('source_ids', M.fonteDaAfirmacao), ('excerpt_ids', M.trechoDaAfirmacao),
                              ('function_ids', M.funcaoDaAfirmacao), ('contribution_ids', M.contribuicaoDaAfirmacao)]:
                for value in claim.get(key, []):
                    graph.add((node, prop, M[value]))
            graph.add((node, M.escopoDaAfirmacao, Literal(json.dumps(claim['scope'], ensure_ascii=False, sort_keys=True), lang='pt-BR')))
            for limit in claim['limits']:
                graph.add((node, M.limiteDaAfirmacao, Literal(limit, lang='pt-BR')))
            graph.add((node, M.originalReconferidoNaMigracao, Literal(False)))
    # Analytical applications reuse the operational assertion class. Their
    # epistemic kind is explicit and never changes historical K review states.
    for art in data.get('articulations', []):
        for app in art.get('operational_applications', []):
            node = M[app['id']]
            graph.add((node, RDF.type, M.AfirmacaoOperacionalDocumentada))
            graph.add((node, M.identificador, Literal(app['id'])))
            graph.add((node, M.enunciado, Literal(app['result'], lang='pt-BR')))
            graph.add((node, M.aplicacaoDaArticulacao, M[art['id']]))
            graph.add((node, M.elegibilidadeOperacional, Literal(app['status'])))
            graph.add((node, M.estadoDaAfirmacao, Literal('SCOPED_ANALYTICAL_SYNTHESIS')))
            graph.add((node, M.estatutoEpistemicoDaAfirmacao, Literal('SYNTESE_ANALITICA_FUNDAMENTADA')))
            graph.add((node, M.operacaoDaAplicacaoAnalitica, Literal(app['analytical_operation'], lang='pt-BR')))
            graph.add((node, M.efeitoEmpiricoAutorizado, Literal(False)))
            for premise in app['premises']:
                graph.add((node, M.premissaOperacional, M[premise['claim_id']]))
                for cid in premise.get('contribution_ids', []):
                    graph.add((node, M.contribuicaoDaAfirmacao, M[cid]))
            for pair in app.get('criterion_support', []):
                for oid in pair['origin_ids']:
                    graph.add((node, M.origemDaAplicacaoAnalitica, M[oid]))
            for field, prop in [('authorized_operation_ids', M.autorizaOperacao),
                                ('authorized_relation_ids', M.autorizaRelacaoOperacional),
                                ('authorized_requirement_ids', M.autorizaDerivacaoDeRequisito),
                                ('function_ids', M.funcaoDaAfirmacao),
                                ('depends_on_application_ids', M.dependeDeAplicacaoAnalitica)]:
                for value in app.get(field, []):
                    graph.add((node, prop, M[value]))
            for field, prop in [('conditions', M.condicaoDaAplicacaoAnalitica), ('limits', M.limiteDaAfirmacao)]:
                for value in app[field]:
                    graph.add((node, prop, Literal(value, lang='pt-BR')))
    for op in iter_operation_contracts(data):
        node = M[op['id']]
        graph.set((node, M.contratoOperacionalSerializado,
                   Literal(json.dumps(op, ensure_ascii=False, sort_keys=True))))
        for aid in op.get('analytical_application_ids', []):
            graph.add((node, M.fundamentadaPorAplicacaoAnalitica, M[aid]))
    for matrix in data.get('functional_matrix', []):
        contract = matrix.get('inference_contract')
        if not contract:
            continue
        node = M[matrix['id']]
        graph.add((node, RDF.type, SKOS.Concept))
        graph.set((node, M.identificador, Literal(matrix['id'])))
        graph.set((node, SKOS.prefLabel, Literal(matrix['descricao_simples'], lang='pt-BR')))
        graph.set((node, M.contratoOperacionalSerializado,
                   Literal(json.dumps(contract, ensure_ascii=False, sort_keys=True))))
        for group in [contract, *contract.get('trigger_groups', [])]:
            for aid in group.get('analytical_application_ids', []):
                graph.add((node, M.fundamentadaPorAplicacaoAnalitica, M[aid]))
    for concept in data.get('context_elements', []):
        node = M[concept['id']]
        # Curated public labels must also update pre-existing RDF concepts;
        # semantic annotations below are only required for newer concepts.
        graph.set((node, SKOS.prefLabel, Literal(concept['rotulo'], lang='pt-BR')))
        if not (concept.get('interaction_semantics') or concept.get('assertion_semantics')
                or concept.get('status') == 'REQUISITO_ANALITICO_1_5'):
            continue
        graph.add((node, RDF.type, SKOS.Concept))
        graph.set((node, M.identificador, Literal(concept['id'])))
        graph.add((node, SKOS.inScheme, URIRef('https://w3id.org/mado/scheme/' + concept['tipo'])))
        graph.set((node, M.statusDoRegistro, Literal(concept['status'])))
        for field, prop in [('interaction_semantics', M.tipoSemanticoDeInteracao),
                            ('assertion_semantics', M.tipoDeAfirmacaoContextual)]:
            if field in concept:
                graph.set((node, prop, Literal(concept[field]['kind'])))


def build_graph(base, tbox, data):
    """Return a new graph; never mutate the caller's graphs or JSON."""
    validate_contributions(data)
    validate_operational_contracts(data)
    graph = Graph()
    for triple in base:
        graph.add(triple)
    # Replace declarations, ontology metadata and their anonymous axiom/list
    # closure. Individuals and their documentary data are retained.
    schema_types = (OWL.Ontology, OWL.Class, OWL.ObjectProperty,
                    OWL.DatatypeProperty, OWL.AnnotationProperty,
                    OWL.AllDisjointClasses, OWL.Axiom)
    schema = {s for typ in schema_types for s in graph.subjects(RDF.type, typ)}
    todo = list(schema)
    while todo:
        subject = todo.pop()
        for obj in graph.objects(subject):
            if isinstance(obj, BNode) and obj not in schema:
                schema.add(obj)
                todo.append(obj)
    for subject in schema:
        graph.remove((subject, None, None))
    for subject in list(graph.subjects(RDF.type, M.ContribuicaoNaArticulacao)):
        graph.remove((subject, None, None))
        graph.remove((None, None, subject))
    graph.remove((None, M.possuiContribuicao, None))
    graph.remove((None, M.aplicacaoMobilizaContribuicao, None))
    for triple in tbox:
        graph.add(triple)
    project_documentary_metadata(graph, data)

    for row in data["knowledge"]:
        node = M[row["id"]]
        # Keep the operational resource index and the queryable relation in
        # sync. An existing source-backed applicability correction must not
        # appear in the dialogue while remaining absent from the RDF.
        if "recursos_digitais" in row.get("aplicabilidade", {}):
            replace_values(graph, node, M.aplicavelARecursoDigital,
                           (M[value] for value in row["aplicabilidade"]["recursos_digitais"]))
        for key, predicate in (("fonte_ids", M.derivadoDe), ("trecho_ids", M.sustentadoPorTrecho)):
            replace_values(graph, node, predicate, (M[value] for value in row.get(key, [])))
        for key, predicate in (("enunciado", M.enunciado), ("articulacao", M.articulacao)):
            if key in row:
                replace_values(graph, node, predicate, [Literal(row[key], lang="pt-BR")])
        replace_values(graph, node, M.estadoDeRevisaoDaFundamentacao,
                       [Literal(row["foundation_review_status"])] if row.get("foundation_review_status") else [])
        replace_values(graph, node, M.pendenciaDeFundamentacao,
                       (Literal(value, lang="pt-BR") for value in row.get("pending_foundation_items", [])))
    for row in data["articulations"]:
        node = M[row["id"]]
        replace_values(graph, node, M.articulacaoSustentadaPorTrecho,
                       (M[value] for value in row["trecho_ids"]))
        for key, predicate in ART_TEXT.items():
            replace_values(graph, node, predicate,
                           [Literal(row[key], lang="pt-BR")] if row.get(key) else [])
    for row in data.get("contributions", []):
        node, art = M[row["id"]], M[row["articulation_id"]]
        graph.add((node, RDF.type, M.ContribuicaoNaArticulacao))
        graph.add((node, M.identificador, Literal(row["id"])))
        graph.add((node, M.contribuicaoNaArticulacao, art))
        graph.add((node, M.contribuicaoParaConhecimento, M[row["knowledge_id"]]))
        graph.add((node, M.contribuicaoDoTrecho, M[row["excerpt_id"]]))
        graph.add((art, M.possuiContribuicao, node))
        for key, predicate in CONTRIBUTION_TEXT.items():
            graph.add((node, predicate, Literal(row[key], lang="pt-BR")))
        for key, predicate in CONTRIBUTION_CODES.items():
            graph.add((node, predicate, Literal(row[key])))
        graph.add((node, M.dataDaConferencia, Literal(row["review_date"])))

    project_operational_contracts(graph, data)

    # Static example applications are projected by the same exact K/ART pair;
    # there is no global attribution of every contribution to every criterion.
    for app in list(graph.subjects(RDF.type, M.AplicacaoDeCriterio)):
        for cfg in graph.objects(app, M.aplicacaoNaConfiguracao):
            for row in data.get("contributions", []):
                art, k = M[row["articulation_id"]], M[row["knowledge_id"]]
                if (row["verification_status"] != "PENDENTE"
                        and (app, M.conhecimentoDaAplicacao, k) in graph
                        and (cfg, M.configuracaoMobilizaArticulacao, art) in graph
                        and (art, M.habilitadaParaDecisao, Literal(True)) in graph):
                    graph.add((app, M.aplicacaoMobilizaContribuicao, M[row["id"]]))
    return graph


def canonical_outputs(graph):
    canonical = to_canonical_graph(graph)
    turtle = "".join(sorted(canonical.serialize(format="nt").splitlines(keepends=True))).encode("utf-8")
    ordered = Graph()
    for triple in sorted(canonical, key=lambda t: tuple(term.n3() for term in t)):
        ordered.add(triple)
    xml = ET.fromstring(ordered.serialize(format="xml", encoding="utf-8"))
    def normalize(node):
        for child in node:
            normalize(child)
            child.tail = "\n"
        if len(node) and (node.text is None or not node.text.strip()):
            node.text = "\n"
        node[:] = sorted(node, key=lambda e: (e.tag, sorted(e.attrib.items()), e.text or "", ET.tostring(e)))
        node.attrib.update(sorted(node.attrib.items()))
    normalize(xml)
    # XML normalizes literal carriage returns unless explicitly escaped.
    rdfxml = ET.tostring(xml, encoding="utf-8", xml_declaration=True).replace(b"\r", b"&#13;")
    return turtle, rdfxml


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Check canonical output without writing.")
    args = parser.parse_args()
    kb = json.loads((ROOT / "data/knowledge-base.json").read_text(encoding="utf-8-sig"))
    ttl_path, owl_path = ROOT / "ontology/mado-combined.ttl", ROOT / "ontology/mado.owl"
    graph = build_graph(Graph().parse(ttl_path, format="turtle"),
                        Graph().parse(ROOT / "ontology/main.ttl", format="turtle"), kb)
    turtle, rdfxml = canonical_outputs(graph)
    outputs = ((ttl_path, turtle), (owl_path, rdfxml))
    if args.check:
        outdated = [p.relative_to(ROOT).as_posix() for p, payload in outputs if p.read_bytes() != payload]
        if outdated:
            raise SystemExit("Exportação divergente: " + ", ".join(outdated))
    else:
        for path, payload in outputs:
            path.write_bytes(payload)
    print(json.dumps({"mode": "check" if args.check else "build", "triples": len(graph),
                      "contributions": len(kb.get("contributions", [])),
                      "sha256": hashlib.sha256(turtle).hexdigest(),
                      "private_inputs": False}, ensure_ascii=False))


if __name__ == "__main__":
    main()
