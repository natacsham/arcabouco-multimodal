"""Typed, ephemeral evidence for one situated composition.

This is a projection of what the executor returned, not another decision engine.
No case is written to disk, no result of use is asserted, and missing checks are
never manufactured. The knowledge graph passed in is read-only.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from urllib.parse import quote

from rdflib import BNode, Graph, Literal, Namespace, RDF, RDFS, URIRef, XSD
from rdflib.compare import to_canonical_graph
from rdflib.namespace import OWL, SKOS

M = Namespace("https://w3id.org/mado#")
EX = Namespace("https://w3id.org/mado/execution#")
CONTRACT = "MADO_EXECUTION_GRAPH_1"
_CLASSES = (
    "Execution", "Proposal", "OperationEvaluation", "RelationApplication", "Check",
    "ConditionEvaluation", "InformationBinding", "Gap", "SourceSupport", "PremiseUse",
    "ModalInformationRole", "ContextAssertion", "ObservationValue", "Coverage", "TemporalContract",
)
_OBJECTS = (
    "decision", "context", "situation", "participant", "responsibleParticipant", "consideredResource",
    "hasProposal", "hasOperation", "hasConfiguration", "hasRelation", "hasCheck",
    "hasGap", "hasCondition", "hasInput", "hasOutput", "hasInformationRole",
    "operation", "relation", "fromOperation", "toOperation", "representation",
    "function", "informationUnit", "usesAssertion",
    "usesContribution", "usesArticulation", "historicalArticulation", "historicalContribution", "analyticalApplication", "hasCriterionApplication",
    "hasPremise", "hasSupport", "source", "excerpt", "criterion", "origin",
    "knowledgeReference", "resultingKnowledge", "hasAssertion", "concept", "hasExpected", "hasObserved",
    "hasValue", "hasCoverage", "coveredFunction", "missingFunction", "forExecution", "hasInformationBinding", "hasTemporalContract",
)
_DATA = (
    "identifier", "state", "status", "kind", "stage", "phase", "selectionState",
    "action", "explanation", "justification", "limit", "temporal", "preserves",
    "position", "baseHash", "contextHash", "resultHash", "contractVersion",
    "confirmed", "readyForApplication", "coversWholeTask", "epistemicStatus",
    "informationComponent", "role", "aloneSufficient", "jointSufficiencyScope",
    "goal", "locator", "documentaryState", "sourceText", "value", "field",
    "sourceUrl", "derivationOrigin", "reportedTaskScope", "isObservedResult",
    "summaryOnly", "itemCount", "bindingOrigin", "semanticPreservationObserved",
    "organization", "windowRequirement", "verificationRequired", "bindingStatus", "requiredInformation",
)


def execution_schema_graph() -> Graph:
    """Small explicit vocabulary; it may also be merged into the public TBox."""
    graph = Graph()
    for name in _CLASSES:
        graph.add((EX[name], RDF.type, OWL.Class))
    for name in _OBJECTS:
        graph.add((EX[name], RDF.type, OWL.ObjectProperty))
    for name in _DATA:
        graph.add((EX[name], RDF.type, OWL.DatatypeProperty))
    graph.add((EX.Execution, RDFS.comment, Literal(
        "Registro computacional temporário de uma composição; não é resultado observado de uso.", lang="pt-BR")))
    return graph


def _digest(value) -> str:
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                    separators=(",", ":"), default=str).encode()).hexdigest()


def _graph_hash(graph: Graph) -> str:
    # Named nodes/literals are already stable anchors. Canonicalize only the
    # triples touching blank nodes; copying a 100k-triple catalogue into the
    # canonicalizer at each generation needlessly dominates browser latency.
    # Every ground triple is still included, so any base mutation changes hash.
    anonymous, lines = Graph(), []
    for triple in graph:
        if any(isinstance(term, BNode) for term in triple):
            anonymous.add(triple)
        else:
            lines.append(" ".join(term.n3() for term in triple))
    if anonymous:
        lines.extend(" ".join(term.n3() for term in triple) for triple in to_canonical_graph(anonymous))
    return hashlib.sha256("\n".join(sorted(lines)).encode()).hexdigest()


def canonical_graph_hash(graph: Graph) -> str:
    """Content hash stable across RDF parser blank-node identifiers."""
    return _graph_hash(graph)


def _id(value):
    if isinstance(value, dict):
        return value.get("id") or value.get("iri")
    return value


def _ref(value):
    value = _id(value)
    if value is None or value == "":
        return None
    text = str(value)
    return URIRef(text) if text.startswith(("http://", "https://", "urn:")) else M[quote(text, safe="-._~:")]


def project_execution(result: dict, context: dict, base_graph: Graph) -> Graph:
    """Project an immutable execution result into a separate in-memory graph.

    Identity is content-addressed. Metadata attached by an earlier projection is
    excluded from the identity so inspecting an execution cannot change it.
    """
    clean_result = {k: v for k, v in result.items() if k not in {
        "semantic_trace", "execution_graph", "execution_rdf", "semantic_queries"}}
    base_hash = _graph_hash(base_graph)
    result_hash, context_hash = _digest(clean_result), _digest(context)
    identity = _digest([CONTRACT, base_hash, context_hash, result_hash])
    namespace = Namespace("https://w3id.org/mado/execution/" + identity + "#")
    graph = execution_schema_graph()
    graph.bind("mado", M); graph.bind("exec", EX); graph.bind("run", namespace)
    execution, decision, root_context = namespace.execution, namespace.decision, namespace.context

    def node(kind, identity):
        return namespace[kind + "-" + _digest(identity)[:24]]

    def put(subject, predicate, value, *, lang=None):
        if value is not None and value != "":
            graph.add((subject, predicate, Literal(value, lang=lang)))

    def link(subject, predicate, value):
        target = _ref(value)
        if target is not None:
            graph.add((subject, predicate, target))
        return target

    def entity(subject, kind, identifier=None):
        graph.add((subject, RDF.type, kind))
        graph.add((subject, EX.forExecution, execution))
        put(subject, EX.identifier, identifier)
        return subject

    entity(execution, EX.Execution)
    graph.add((execution, EX.decision, decision))
    graph.add((execution, EX.context, root_context))
    for pred, value in ((EX.contractVersion, CONTRACT), (EX.baseHash, base_hash),
                        (EX.contextHash, context_hash), (EX.resultHash, result_hash)):
        put(execution, pred, value)
    entity(decision, M.DecisaoDeAcessibilidadeMultimodal, result.get("context_id"))
    graph.add((decision, M.respondeA, root_context))
    put(decision, M.statusDecisao, result.get("status"))
    put(decision, EX.status, result.get("proposal_status"))
    put(decision, EX.coversWholeTask, result.get("covers_whole_reported_task"))
    put(decision, EX.epistemicStatus, "COMPUTED_DESIGN_PROPOSAL_NOT_OBSERVED_OUTCOME")
    put(decision, EX.isObservedResult, False)
    entity(root_context, M.ContextoDeInteracaoDigital, context.get("id"))
    put(root_context, EX.confirmed, context.get("confirmed"))
    put(root_context, RDFS.label, context.get("label") or context.get("title"))

    scope_cache = {}
    def scope(row):
        sid, pid = row.get("situation_id"), row.get("participant_id")
        key = (sid, pid)
        if key in scope_cache:
            return scope_cache[key]
        situation = root_context if not sid else node("situation", sid)
        if situation != root_context:
            entity(situation, M.ContextoDeInteracaoDigital, sid)
            graph.add((situation, M.episodioDoContexto, root_context))
            put(situation, RDFS.label, row.get("situation_label"))
        participant = None
        if pid:
            participant = node("participation", [sid, pid])
            entity(participant, M.ParticipacaoNoContexto, pid)
            graph.add((situation, M.temParticipacao, participant))
            graph.add((participant, M.participacaoEmContexto, situation))
            put(participant, RDFS.label, row.get("participant_label"))
        scope_cache[key] = situation, participant
        return situation, participant

    def bind_scope(subject, row):
        situation, participant = scope(row)
        graph.add((subject, EX.situation, situation))
        if participant is not None:
            graph.add((subject, EX.participant, participant))
        return situation, participant

    for row in result.get("context_scope", []):
        situation, participant = scope(row)
        if participant is not None:
            put(participant, EX.role, row.get("task_participation"))
            for task in row.get("assigned_task_ids", []):
                link(participant, M.realizaTarefa, task)

    def check_links(subject, identifiers):
        for identifier in identifiers or []:
            graph.add((subject, EX.hasCheck, node("check", identifier)))

    # Structured observations remain queryable, including false/null values.
    # These values are evidence, never new approval statements.
    def observation(parent, predicate, value, path, depth=0):
        target = node("observation", path)
        entity(target, EX.ObservationValue)
        graph.add((parent, predicate, target))
        # Exact assertions, sources, applications, conditions and modal roles
        # have their own typed nodes below. Check observations are bounded
        # summaries of the original execution ledger, not copies of every
        # nested contract repeated for every check.
        if isinstance(value, (dict, list)) and depth >= 2:
            put(target, EX.summaryOnly, True)
            put(target, EX.itemCount, len(value))
        elif isinstance(value, dict):
            for key, item in sorted(value.items()):
                child = observation(target, EX.hasValue, item, [path, key], depth + 1)
                put(child, EX.field, key)
        elif isinstance(value, list):
            for index, item in enumerate(value[:16]):
                child = observation(target, EX.hasValue, item, [path, index], depth + 1)
                put(child, EX.position, index)
            if len(value) > 16:
                put(target, EX.summaryOnly, True)
                put(target, EX.itemCount, len(value))
        elif value is None:
            put(target, EX.state, "UNKNOWN")
        else:
            put(target, EX.value, value)
        return target

    for row in result.get("execution_evidence", []):
        if not isinstance(row, dict) or not row.get("id"):
            continue
        check = entity(node("check", row["id"]), EX.Check, row["id"])
        graph.add((execution, EX.hasCheck, check))
        for key in ("state", "stage", "kind", "phase", "explanation"):
            put(check, EX[key], row.get(key))
        put(check, EX.identifier, row.get("id"))
        link(check, EX.concept, row.get("subject"))
        for key, predicate in (("expected", EX.hasExpected), ("observed", EX.hasObserved)):
            if key in row:
                observation(check, predicate, row[key], [row["id"], key])
        observed = row.get("observed", {})
        if isinstance(observed, dict):
            bind_scope(check, observed)

    for row in context.get("assertions", []):
        assertion = entity(node("assertion", row.get("id", _digest(row))), EX.ContextAssertion, row.get("id"))
        graph.add((root_context, EX.hasAssertion, assertion))
        bind_scope(assertion, {"situation_id": row.get("situation_id"), "participant_id": row.get("subject_id")})
        for key in ("kind", "state"):
            put(assertion, EX[key], row.get(key))
        put(assertion, EX.sourceText, row.get("source_text"))
        if isinstance(row.get("value"), (str, int, float, bool)):
            put(assertion, EX.value, row["value"])

    for row in result.get("required_functions", []):
        req = entity(node("requirement", [row.get("id"), row.get("participant_id"), row.get("situation_id")]),
                     M.FuncaoRequeridaSituada, row.get("id"))
        situation, participant = bind_scope(req, row)
        graph.add((req, M.noContexto, situation))
        if participant is not None:
            graph.add((req, M.paraParticipacao, participant))
        link(req, M.requerFuncao, row.get("function_id"))
        put(req, EX.derivationOrigin, row.get("origin"))
        put(req, EX.reportedTaskScope, row.get("task_scope_kind"))
        for task in row.get("task_ids", []):
            link(req, M.paraTarefa, task)
        for claim in row.get("claim_ids", []):
            link(req, EX.usesAssertion, claim)
        for witness in row.get("witnesses", []):
            for identifier in witness.get("need_ids", []) + witness.get("characteristic_ids", []):
                link(req, M.derivadaDaCondicao, identifier)
            for identifier in witness.get("assertion_ids", []):
                graph.add((req, EX.hasAssertion, node("assertion", identifier)))
        check_links(req, row.get("check_ids"))

    for row in result.get("function_coverage", []):
        coverage = entity(node("coverage", [_id(row.get("function")), row.get("participant_id"), row.get("situation_id")]), EX.Coverage)
        graph.add((execution, EX.hasCoverage, coverage))
        bind_scope(coverage, row)
        link(coverage, EX.function, row.get("function"))
        put(coverage, EX.state, row.get("state"))

    def groundings(owner, records, *, configuration=None):
        for index, record in enumerate(records or []):
            support = entity(node("support", [str(owner), index, record.get("id")]), EX.SourceSupport, record.get("id"))
            graph.add((owner, EX.hasSupport, support))
            link(support, EX.usesAssertion, record.get("claim_id"))
            knowledge_record = record.get("knowledge") or {}
            is_knowledge = not isinstance(knowledge_record, dict) or knowledge_record.get("kind") != "ANALYTICAL_APPLICATION"
            knowledge = _ref(knowledge_record) if is_knowledge else None
            if knowledge is not None and (knowledge, RDF.type, M.ArticulacaoDocumentada) not in base_graph:
                graph.add((support, EX.knowledgeReference, knowledge))
            for result_id in record.get("resulting_knowledge_ids", []):
                link(support, EX.resultingKnowledge, result_id)
            analytical_id = record.get("analytical_application_id") or (
                record.get("id") if record.get("application_kind") == "EXISTING_RDF_CURATED_APPLICATION" else None)
            link(support, EX.analyticalApplication, analytical_id)
            put(support, EX.kind, record.get("application_kind"))
            put(support, EX.explanation, record.get("justification"))
            construction = record.get("construction") or record.get("articulation") or {}
            art_id = construction.get("id")
            # A locally built explanation id is not a newly discovered articulation.
            if art_id and (analytical_id or (_ref(art_id), RDF.type, M.ArticulacaoDocumentada) in base_graph):
                link(support, EX.usesArticulation, art_id)
            for historic in construction.get("documentary_articulations", []):
                link(support, EX.historicalArticulation, historic)
            for premise in construction.get("premises", []):
                pn = entity(node("premise", [str(support), premise.get("claim_id")]), EX.PremiseUse)
                graph.add((support, EX.hasPremise, pn))
                link(pn, EX.usesAssertion, premise.get("claim_id"))
                link(pn, EX.knowledgeReference, premise.get("knowledge_id"))
                for contribution in premise.get("contribution_ids", []):
                    link(pn, EX.usesContribution, contribution)
            for contribution in construction.get("contributions", []):
                historical = isinstance(contribution, dict) and contribution.get("status") == "LEGACY_RECORD_ONLY"
                link(support, EX.historicalContribution if historical else EX.usesContribution, contribution)
            for source in record.get("sources", []):
                # A separate pair prevents combinations of unrelated sources/excerpts.
                pair = entity(node("source", [str(support), source.get("id"), source.get("excerpt_id")]), EX.SourceSupport)
                graph.add((support, EX.hasSupport, pair))
                link(pair, EX.source, source.get("id"))
                link(pair, EX.excerpt, source.get("excerpt_id"))
                put(pair, RDFS.label, source.get("label") or source.get("titulo"))
                put(pair, EX.locator, source.get("locator"))
                put(pair, EX.sourceUrl, source.get("url"))
                put(pair, EX.documentaryState, source.get("review_status"))
            applications = record.get("criterion_applications")
            if applications is None:
                applications = [record] if _id(record.get("criterion")) else []
            for ai, application in enumerate(applications):
                criterion = application.get("criterion_id") or _id(application.get("criterion"))
                if not criterion:
                    continue
                app = entity(node("criterion", [str(support), ai, criterion]),
                             M.AplicacaoDeCriterio if configuration is not None else EX.SourceSupport)
                graph.add((support, EX.hasSupport, app))
                link(app, M.criterioAplicado if configuration is not None else EX.criterion, criterion)
                for origin in application.get("origin_ids", []):
                    link(app, M.origemDaAplicacao if configuration is not None else EX.origin, origin)
                criterion_record = application.get("criterion") or {}
                if isinstance(criterion_record, dict):
                    link(app, EX.source, criterion_record.get("source"))
                    put(app, EX.locator, criterion_record.get("locator"))
                if knowledge is not None and (knowledge, RDF.type, M.ArticulacaoDocumentada) not in base_graph:
                    graph.add((app, M.conhecimentoDaAplicacao if configuration is not None else EX.knowledgeReference, knowledge))
                link(app, EX.analyticalApplication, analytical_id)
                link(app, EX.usesAssertion, record.get("claim_id"))
                put(app, M.justificativaDaAplicacao if configuration is not None else EX.justification,
                    application.get("justification") or record.get("justification"), lang="pt-BR")
                if configuration is not None:
                    graph.add((configuration, M.possuiAplicacaoDeCriterio, app))
                    graph.add((configuration, EX.hasCriterionApplication, app))
                    graph.add((app, M.aplicacaoNaConfiguracao, configuration))
            check_links(support, record.get("check_ids"))

    def information(owner, record, predicate, index):
        binding = entity(node("information", [str(owner), str(predicate), index]), EX.InformationBinding)
        graph.add((owner, predicate, binding))
        link(binding, EX.representation, record.get("representation_id"))
        put(binding, EX.informationComponent, record.get("information_component") or record.get("meaning_unit"))
        identity = record.get("information_unit_id") or record.get("bound_information_id")
        if identity:
            graph.add((binding, EX.informationUnit, node("information-unit", identity)))
        # A generic meaning_unit is not fabricated into a proven shared identity.
        put(binding, EX.state, record.get("state"))

    operation_cache = {}
    def operation(row):
        key = (row.get("id"), row.get("participant_id"), row.get("situation_id"))
        if key in operation_cache:
            return operation_cache[key]
        occurrence = entity(node("operation", key), EX.OperationEvaluation, row.get("id"))
        operation_cache[key] = occurrence
        graph.add((execution, EX.hasOperation, occurrence))
        bind_scope(occurrence, row)
        link(occurrence, EX.operation, row.get("id"))
        put(occurrence, EX.state, row.get("state"))
        put(occurrence, EX.action, row.get("action"))
        put(occurrence, EX.explanation, row.get("limitation"))
        responsible = row.get("responsible_participant") or {}
        if _id(responsible):
            _, party = scope({"situation_id": row.get("situation_id"), "participant_id": _id(responsible), "participant_label": responsible.get("label")})
            graph.add((occurrence, EX.responsibleParticipant, party))
        for function in row.get("function_ids", []):
            link(occurrence, EX.function, function)
        for representation in row.get("selected_representation_ids", []):
            link(occurrence, EX.representation, representation)
        for resource in row.get("resources", []):
            link(occurrence, EX.consideredResource, resource)
        for index, record in enumerate(row.get("input_requirements", [])):
            information(occurrence, record, EX.hasInput, index)
        for index, record in enumerate(row.get("output_spec", [])):
            information(occurrence, record, EX.hasOutput, index)
        for index, condition in enumerate(row.get("phase_conditions", [])):
            cn = entity(node("condition", [str(occurrence), condition.get("id"), index]), EX.ConditionEvaluation, condition.get("id"))
            graph.add((occurrence, EX.hasCondition, cn))
            bind_scope(cn, row)
            for key in ("state", "phase", "kind"):
                put(cn, EX[key], condition.get(key))
            put(cn, RDFS.label, condition.get("label"))
            check_links(cn, condition.get("check_ids"))
        groundings(occurrence, row.get("groundings"))
        check_links(occurrence, row.get("check_ids"))
        return occurrence

    for row in result.get("capability_evaluations", []):
        operation(row)

    def relation(row, owner=None):
        key = [row.get("id"), row.get("participant_id"), row.get("situation_id"), row.get("from_capability"), row.get("to_capability")]
        rn = entity(node("relation", key), EX.RelationApplication, row.get("id"))
        graph.add((execution, EX.hasRelation, rn))
        if owner is not None:
            graph.add((owner, EX.hasRelation, rn))
        bind_scope(rn, row)
        link(rn, EX.relation, row.get("id"))
        for field in ("kind", "state", "temporal", "preserves", "explanation", "goal", "joint_sufficiency_scope"):
            put(rn, EX.jointSufficiencyScope if field == "joint_sufficiency_scope" else EX[field], row.get(field))
        for field, predicate in (("from_capability", EX.fromOperation), ("to_capability", EX.toOperation)):
            target = operation_cache.get((row.get(field), row.get("participant_id"), row.get("situation_id")))
            if target is not None:
                graph.add((rn, predicate, target))
            else:
                link(rn, predicate, row.get(field))
        for value in row.get("required_information", []):
            put(rn, EX.requiredInformation, value)
        identity = row.get("information_binding") or {}
        if identity.get("information_unit_id"):
            binding = entity(node("relation-information", key), EX.InformationBinding)
            graph.add((rn, EX.hasInformationBinding, binding))
            graph.add((binding, EX.informationUnit, node("information-unit", identity["information_unit_id"])))
            put(binding, EX.bindingOrigin, identity.get("origin"))
            put(binding, EX.semanticPreservationObserved, identity.get("semantic_preservation_observed"))
            bind_scope(binding, identity)
        temporal_contract = row.get("temporal_contract") or {}
        if temporal_contract:
            tn = entity(node("temporal-contract", key), EX.TemporalContract)
            graph.add((rn, EX.hasTemporalContract, tn))
            for field, predicate in (("organization", EX.organization), ("window_requirement", EX.windowRequirement),
                                     ("verification_required", EX.verificationRequired), ("binding_status", EX.bindingStatus)):
                put(tn, predicate, temporal_contract.get(field))
        for index, role in enumerate(row.get("information_roles", [])):
            role_node = entity(node("modal-role", [key, index]), EX.ModalInformationRole)
            graph.add((rn, EX.hasInformationRole, role_node))
            link(role_node, EX.representation, role.get("representation_id"))
            link(role_node, EX.function, role.get("function_id"))
            put(role_node, EX.informationComponent, role.get("information_component"))
            put(role_node, EX.role, role.get("role"))
            put(role_node, EX.aloneSufficient, role.get("alone_sufficient_for_goal"))
            for claim in role.get("claim_ids", []):
                link(role_node, EX.usesAssertion, claim)
        for index, condition in enumerate(row.get("phase_conditions", [])):
            cn = entity(node("condition", [str(rn), condition.get("id"), index]), EX.ConditionEvaluation, condition.get("id"))
            graph.add((rn, EX.hasCondition, cn))
            bind_scope(cn, row)
            for field in ("state", "phase", "kind"):
                put(cn, EX[field], condition.get(field))
            put(cn, RDFS.label, condition.get("label"))
            check_links(cn, condition.get("check_ids"))
        groundings(rn, row.get("groundings") or ([row["grounding"]] if row.get("grounding") else []))
        check_links(rn, row.get("check_ids"))
        return rn

    for row in result.get("relation_evaluations", []):
        relation(row)

    for group in ("choices", "pending_candidates", "partial_segments"):
        for plan in result.get(group, []):
            pn = entity(node("proposal", [group, plan.get("id"), plan.get("participant_id"), plan.get("situation_id")]), EX.Proposal, plan.get("id"))
            graph.add((execution, EX.hasProposal, pn))
            bind_scope(pn, plan)
            put(pn, EX.selectionState, group)
            put(pn, EX.state, plan.get("state"))
            put(pn, EX.kind, plan.get("composition_type"))
            put(pn, EX.readyForApplication, plan.get("ready_for_application"))
            put(pn, EX.coversWholeTask, plan.get("ready_for_whole_task"))
            for value in plan.get("covered_functions", []):
                link(pn, EX.coveredFunction, value)
            for value in plan.get("missing_functions", []):
                link(pn, EX.missingFunction, value)
            for value in plan.get("limits", []):
                put(pn, EX.limit, value)
            for index, step in enumerate(plan.get("steps", [])):
                occurrence = operation(step)
                graph.add((pn, EX.hasOperation, occurrence))
                # ConfiguracaoModalDaDecisao has one modality: do not merge them.
                modes = step.get("selected_representation_ids") or []
                for mode_index, mode in enumerate(modes):
                    cfg = entity(node("configuration", [str(pn), index, mode_index]), M.ConfiguracaoModalDaDecisao)
                    graph.add((pn, EX.hasConfiguration, cfg))
                    graph.add((decision, M.possuiConfiguracaoModal, cfg))
                    graph.add((cfg, M.configuracaoDeDecisao, decision))
                    graph.add((cfg, EX.hasOperation, occurrence))
                    bind_scope(cfg, step)
                    link(cfg, M.configuraModalidade, mode)
                    put(cfg, EX.position, index + 1)
                    put(cfg, EX.selectionState, group)
                    put(cfg, M.estadoDeDisponibilidadeDaConfiguracao, step.get("state"))
                    put(cfg, M.significadoFuncional, step.get("action"), lang="pt-BR")
                    # Functions belong to the selected operation. Do not claim
                    # every mode alone fulfils all its functions. Individual
                    # modal roles are recorded on the verified relation above.
                    for resource in step.get("selected_resource_ids", []):
                        link(cfg, M.configuraRecurso, resource)
                    for limit in step.get("limits", []):
                        put(cfg, M.limiteDaConfiguracao, limit, lang="pt-BR")
                    put(cfg, M.acompanhamentoDaConfiguracao, step.get("monitoring"), lang="pt-BR")
                    groundings(cfg, step.get("groundings"), configuration=cfg)
                    check_links(cfg, step.get("check_ids"))
            for row in plan.get("relations", []):
                relation(row, pn)
            check_links(pn, plan.get("check_ids"))

    for collection in ("gaps", "integration_gaps", "exclusions", "input_issues", "claim_audit"):
        for index, row in enumerate(result.get(collection, [])):
            if not isinstance(row, dict):
                continue
            gap = entity(node("gap", [collection, index, row]), EX.Gap, row.get("id"))
            graph.add((execution, EX.hasGap, gap))
            bind_scope(gap, row)
            put(gap, EX.kind, collection)
            put(gap, EX.status, row.get("code") or row.get("reason") or row.get("type"))
            put(gap, EX.explanation, row.get("explanation") or row.get("label"))
            link(gap, EX.concept, row.get("id"))
            for field, predicate in (("from_capability", EX.fromOperation), ("to_capability", EX.toOperation)):
                target = operation_cache.get((row.get(field), row.get("participant_id"), row.get("situation_id")))
                if target is not None:
                    graph.add((gap, predicate, target))
                else:
                    link(gap, predicate, row.get(field))
            check_links(gap, row.get("check_ids"))
    return graph


def semantic_execution_summary(graph: Graph) -> dict:
    execution = next(graph.subjects(RDF.type, EX.Execution), None)
    if execution is None:
        raise ValueError("Grafo sem execução situada.")
    return {
        "contract_version": CONTRACT, "execution_iri": str(execution),
        "decision_iri": str(graph.value(execution, EX.decision)),
        "graph_sha256": _graph_hash(graph),
        "base_sha256": str(graph.value(execution, EX.baseHash)),
        "triples": len(graph), "case_storage": False, "observed_outcome": False,
        "counts": {name: len(set(graph.subjects(RDF.type, kind))) for name, kind in (
            ("proposals", EX.Proposal), ("operations", EX.OperationEvaluation),
            ("relations", EX.RelationApplication), ("checks", EX.Check),
            ("requirements", M.FuncaoRequeridaSituada), ("configurations", M.ConfiguracaoModalDaDecisao),
            ("criterion_applications", M.AplicacaoDeCriterio), ("gaps", EX.Gap))},
        "query_ids": [f"EXEC-CQ-{i:03d}" for i in range(1, 11)],
    }


def query_execution(graph: Graph, base_graph: Graph | None = None, query_ids=None,
                    query_directory: Path | str | None = None) -> dict:
    """Run explicit, execution-scoped competency queries on demand.

    Historical CQ files remain unchanged; these queries do not manufacture
    legacy pattern fields to make new decisions fit the former selector.
    """
    summary = semantic_execution_summary(graph)
    directory = Path(query_directory) if query_directory else Path(__file__).resolve().parent / "queries"
    combined = Graph()
    if base_graph is not None:
        combined += base_graph
    combined += graph
    allowed = set(summary["query_ids"])
    queries = list(query_ids or summary["query_ids"])
    if any(identifier not in allowed for identifier in queries):
        raise ValueError("Consulta de execução desconhecida.")
    result = {}
    for identifier in queries:
        query = (directory / (identifier + ".rq")).read_text(encoding="utf-8")
        query = query.replace("<urn:mado:current-execution>", URIRef(summary["execution_iri"]).n3())
        answer = combined.query(query)
        result[identifier] = {
            "variables": [str(value) for value in answer.vars],
            "rows": [{str(key): value.toPython() if isinstance(value, Literal) else str(value)
                      for key, value in row.asdict().items()} for row in answer],
        }
    return result
