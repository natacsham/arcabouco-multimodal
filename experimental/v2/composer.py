"""Experimental, data-driven composition of grounded interaction capabilities.

This module does not interpret narrative, infer abilities from diagnoses, perform
the suggested interactions, or classify CARE relations. It enumerates proposals
whose registered conditions and representation transitions were checked. The
analytical synthesis is recorded in RDF, not discovered by this program.
"""

from __future__ import annotations

import copy
import hashlib
import itertools
import json
import re
import sys
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[2]
if (ROOT / "vendor").is_dir():
    sys.path.insert(0, str(ROOT / "vendor"))

from rdflib import Graph, Literal, Namespace, RDF, RDFS, URIRef  # noqa: E402
from rdflib.namespace import XSD  # noqa: E402

V2 = Namespace("https://w3id.org/mado/experimental/v2#")
MADO = Namespace("https://w3id.org/mado#")
MAX_CHOICES = 64
MAX_COMBINATIONS_PER_PHASE = 4096
ACCEPTED_EPISTEMIC = {"DESIGN_SYNTHESIS_NOT_EMPIRICAL", "PARTIAL_LEGACY"}


def _local(value: Any) -> str:
    return str(value).rsplit("#", 1)[-1].rsplit("/", 1)[-1]


def _json_hash(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                     separators=(",", ":")).encode()).hexdigest()


def _worst(states: list[str]) -> str:
    if "FAIL" in states:
        return "FAIL"
    if "PENDING" in states:
        return "PENDING"
    return "PASS"


class _Checks:
    def __init__(self) -> None:
        self.rows: list[dict[str, Any]] = []
        self.history: list[dict[str, Any]] = []

    def add(self, stage: str, subject: Any, kind: str, state: str,
            expected: Any, observed: Any, explanation: str) -> dict[str, Any]:
        row = dict(stage=stage, subject=str(subject), kind=kind, state=state,
                   expected=expected, observed=observed, explanation=explanation)
        row["id"] = "check-" + _json_hash(row)[:16]
        self.history.append(row)
        if not any(existing["id"] == row["id"] for existing in self.rows):
            self.rows.append(row)
        return row


class Composer:
    """Load local RDF once and compose without modifying it or storing cases."""

    def __init__(self, paths: list[Path]) -> None:
        self.graph = Graph()
        self.fingerprints: dict[str, str] = {}
        for supplied in paths:
            path = Path(supplied).resolve(strict=True)
            if not path.is_file():
                raise ValueError(f"Arquivo RDF esperado: {path}")
            raw = path.read_bytes()
            self.fingerprints[str(path)] = hashlib.sha256(raw).hexdigest()
            # A file parser does not dereference owl:imports or remote contexts.
            self.graph.parse(data=raw.decode("utf-8-sig"), format="turtle")

    def compose_context(self, context: dict[str, Any], engine=None, progress=None) -> dict[str, Any]:
        """Compose situated occurrences from the same research operation records.

        Unlike ``compose`` (the preserved two-function pilot contract), this
        accepts MADO contexts. No narrative or scenario identifier selects an
        operation. ``engine`` supplies only its existing task hierarchy/labels.
        Every run owns its temporary state and never changes either engine.
        """
        return _SituatedRun(self, context, engine, progress).run()

    def _values(self, node: Any, predicate: URIRef) -> list[Any]:
        return sorted(set(self.graph.objects(node, predicate)), key=str)

    def _text(self, node: Any, predicate: URIRef, default: str = "") -> str:
        values = self._values(node, predicate)
        valid = (len(values) == 1 and isinstance(values[0], Literal)
                 and values[0].datatype in (None, XSD.string) and not values[0].language)
        return str(values[0]) if valid else default

    def _label(self, node: Any) -> str:
        labels = self._values(node, RDFS.label)
        preferred = [item for item in labels if getattr(item, "language", None)
                     in ("pt", "pt-br", "pt-BR")]
        return str((preferred or labels)[0]) if labels else _local(node)

    def _record(self, node: Any) -> dict[str, str]:
        return {"id": str(node), "label": self._label(node)}

    def _single(self, node: Any, predicate: URIRef, checks: _Checks,
                stage: str, *, iri: bool = False) -> Any | None:
        values = self._values(node, predicate)
        expected = "exatamente um IRI" if iri else "exatamente um literal de texto não vazio"
        valid = False
        if len(values) == 1:
            value = values[0]
            if iri:
                valid = isinstance(value, URIRef)
            elif predicate == V2.order:
                expected = "exatamente um literal xsd:integer"
                valid = isinstance(value, Literal) and value.datatype == XSD.integer and type(value.toPython()) is int
            else:
                valid = (isinstance(value, Literal) and value.datatype in (None, XSD.string)
                         and not value.language and bool(str(value).strip()))
        checks.add(stage, node, "FIELD_" + _local(predicate),
                   "PASS" if valid else "FAIL",
                   expected,
                   [str(value) for value in values],
                   "Integridade do registro conferida; não comprova a alegação documental.")
        return values[0] if valid else None

    def _source(self, node: Any, checks: _Checks, stage: str) -> dict[str, str] | None:
        if node is None:
            return None
        url = self._single(node, V2.url, checks, stage)
        try:
            parsed = urlsplit(str(url)) if url is not None else None
            url_valid = parsed is not None and parsed.scheme == "https" and bool(parsed.hostname)
        except ValueError:
            url_valid = False
        valid = ((node, RDF.type, MADO.Fonte) in self.graph
                 and any(isinstance(label, Literal) and str(label).strip() for label in self._values(node, RDFS.label))
                 and url_valid)
        checks.add(stage, node, "SOURCE_REFERENCE", "PASS" if valid else "FAIL",
                   "fonte tipada e nomeada, com endereço HTTPS não vazio",
                   {"url": str(url) if url is not None else None},
                   "Confere a referência registrada; não acessa o endereço nem comprova o conteúdo da fonte.")
        return {**self._record(node), "url": str(url),
                **{field: self._text(node, V2[field]) for field in ("edition", "review_status", "referenceKind")
                   if self._text(node, V2[field])}} if valid else None

    def _resolve(self, value: Any, entity_type: URIRef) -> URIRef | None:
        if not isinstance(value, str):
            return None
        candidates = sorted(set(self.graph.subjects(RDF.type, entity_type)), key=str)
        exact = [node for node in candidates if str(node) == value]
        if exact:
            return exact[0]
        short = value.split(":", 1)[1] if value.startswith(("v2:", "mado:")) else value
        matches = [node for node in candidates if _local(node) == short]
        return matches[0] if len(matches) == 1 else None

    def _normalize_map(self, raw: Any, entity_type: URIRef, group: str,
                       checks: _Checks, issues: list[dict[str, Any]]) -> dict[URIRef, Any]:
        values: dict[URIRef, Any] = {}
        if not isinstance(raw, dict):
            issues.append({"code": "INVALID_CONTEXT_MAP", "field": group})
            checks.add("context", group, "INPUT_MAP", "FAIL", "objeto", type(raw).__name__,
                       "As condições devem ser fornecidas explicitamente, sem interpretar narrativa.")
            return values
        for key, value in raw.items():
            node = self._resolve(key, entity_type)
            if node is None:
                issues.append({"code": "UNKNOWN_INPUT_CONCEPT", "field": group, "key": key})
                checks.add("context", key, "KNOWN_INPUT", "FAIL", str(entity_type), key,
                           "Conceito desconhecido ou ambíguo; a informação não será ignorada silenciosamente.")
                continue
            if value is not None and type(value) is not bool:
                issues.append({"code": "INVALID_CONTEXT_VALUE", "field": group, "key": key})
                checks.add("context", node, "TRISTATE_INPUT", "FAIL", "true, false ou null", value,
                           "Não se convertem textos, números ou diagnósticos em condições confirmadas.")
                continue
            if node in values and values[node] is not value:
                issues.append({"code": "CONFLICTING_INPUT_ALIASES", "field": group, "key": key})
                checks.add("context", node, "ALIAS_CONSISTENCY", "FAIL", values[node], value,
                           "Dois nomes do mesmo conceito receberam condições contraditórias.")
                continue
            values[node] = value
        return values

    def _requirements(self, node: URIRef, predicate: URIRef, entity_type: URIRef,
                      confirmed: dict[URIRef, Any], checks: _Checks,
                      stage: str) -> list[dict[str, Any]]:
        rows = []
        requirements = self._values(node, predicate)
        if not requirements:
            return [checks.add(stage, node, "MINIMUM_" + _local(predicate), "FAIL",
                               "ao menos uma condição declarada", [],
                               "A remoção dos requisitos não pode autorizar uma operação por um AND vazio.")]
        for required in requirements:
            declared = isinstance(required, URIRef) and (required, RDF.type, entity_type) in self.graph
            value = confirmed.get(required)
            state = "FAIL" if not declared or value is False else "PASS" if value is True else "PENDING"
            row = checks.add(stage, node, "REQUIRES_" + _local(predicate), state,
                             {"concept": str(required), "value": True},
                             {"concept": str(required), "value": value, "declared": declared},
                             "Todas as condições declaradas são necessárias (AND); ausência não é aprovação.")
            rows.append(row)
        return rows

    def _knowledge(self, node: Any, checks: _Checks, stage: str) -> dict[str, Any] | None:
        if node is None:
            return None
        declared = (node, RDF.type, MADO.ConhecimentoMultimodalArticulado) in self.graph
        epistemic = self._text(node, V2.epistemicStatus)
        valid = declared and epistemic in ACCEPTED_EPISTEMIC
        checks.add(stage, node, "KNOWLEDGE_STATUS", "PASS" if valid else "FAIL",
                   {"type": str(MADO.ConhecimentoMultimodalArticulado),
                    "epistemicStatus": sorted(ACCEPTED_EPISTEMIC)},
                   {"declared": declared, "epistemicStatus": epistemic},
                   "Síntese de projeto e registro parcial autorizam somente propostas, não resultado empírico.")
        return {**self._record(node), "epistemic_status": epistemic} if valid else None

    def _articulation(self, node: Any, knowledge: Any, checks: _Checks,
                      stage: str) -> dict[str, Any] | None:
        if node is None or knowledge is None:
            return None
        start = len(checks.history)
        declared = (node, RDF.type, V2.ArticulationSupport) in self.graph
        operation = self._single(node, V2.operation, checks, stage)
        understanding = self._single(node, V2.addedUnderstanding, checks, stage)
        status = self._text(node, V2.status)
        produces = self._values(node, V2.produces)
        produced = self._single(node, V2.produces, checks, stage, iri=True)
        valid = declared and status == "CURATED_FOR_PILOT" and knowledge == produced
        checks.add(stage, node, "ARTICULATION_AUTHORIZATION", "PASS" if valid else "FAIL",
                   {"status": "CURATED_FOR_PILOT", "produces": str(knowledge)},
                   {"status": status, "produces": [str(item) for item in produces], "declared": declared},
                   "O conhecimento empregado deve ser produto explícito desta articulação curada.")
        contributions = []
        candidates = sorted(set(self.graph.subjects(V2.inArticulation, node)), key=str)
        for contribution in candidates:
            cstart = len(checks.history)
            destination = self._single(contribution, V2.inArticulation, checks, stage, iri=True)
            excerpt = self._single(contribution, V2.excerpt, checks, stage, iri=True)
            source = self._single(excerpt, MADO.trechoDeFonte, checks, stage, iri=True) if excerpt else None
            source_record = self._source(source, checks, stage)
            locator = self._single(excerpt, MADO.localizacaoDocumental, checks, stage) if excerpt else None
            statement = self._single(contribution, V2.statement, checks, stage)
            cstatus = self._text(contribution, V2.status)
            cvalid = ((contribution, RDF.type, V2.Contribution) in self.graph
                      and cstatus in {"PRIMARY_CHECKED", "LEGACY_RECORD_ONLY"}
                      and destination == node
                      and excerpt is not None and (excerpt, RDF.type, MADO.TrechoDocumental) in self.graph
                      and source_record is not None)
            checks.add(stage, contribution, "CONTRIBUTION_RECORD", "PASS" if cvalid else "FAIL",
                       "contribuição tipada, localizada, com fonte nomeada e origem explícita",
                       {"status": cstatus, "source": str(source) if source else None},
                       "Conferência declarada refere-se ao trecho registrado, não a toda a publicação.")
            if cvalid and locator is not None and statement is not None:
                contributions.append({**self._record(contribution),
                                      "status": cstatus, "locator": str(locator), "statement": str(statement),
                                      "excerpt": {**self._record(excerpt),
                                                  **{field: self._text(excerpt, V2[field]) for field in ("document_url", "document_version", "document_review_status", "document_paraphrase")
                                                     if self._text(excerpt, V2[field])}},
                                      "source": source_record,
                                      "check_ids": [row["id"] for row in checks.history[cstart:]]})
        primary = [item for item in contributions if item["status"] == "PRIMARY_CHECKED"]
        checks.add(stage, node, "PRIMARY_CONTRIBUTION", "PASS" if primary else "FAIL",
                   "ao menos uma contribuição PRIMARY_CHECKED", [item["id"] for item in primary],
                   "Uma cadeia composta apenas por registros legados não habilita esta aplicação.")
        # Check fields directly as checks are deduplicated across exact applications.
        all_contributions_valid = len(contributions) == len(candidates)
        if not (valid and operation is not None and understanding is not None
                and primary and all_contributions_valid):
            return None
        return {**self._record(node), "operation": str(operation),
                "added_understanding": str(understanding), "status": status,
                "knowledge": str(knowledge), "contributions": contributions,
                "check_ids": [row["id"] for row in checks.history[start:]],
                "interpretation": "Síntese analítica previamente registrada; não descoberta pelo compositor."}

    def _grounding(self, node: URIRef, checks: _Checks,
                   stage: str) -> dict[str, Any] | None:
        start = len(checks.history)
        knowledge = self._single(node, V2.knowledge, checks, stage, iri=True)
        criterion = self._single(node, V2.criterion, checks, stage, iri=True)
        articulation = self._single(node, V2.articulation, checks, stage, iri=True)
        status = self._text(node, V2.status)
        criterion_source = self._single(criterion, V2.source, checks, stage, iri=True) if criterion else None
        criterion_source_record = self._source(criterion_source, checks, stage)
        criterion_locator = self._single(criterion, V2.locator, checks, stage) if criterion else None
        criterion_justification = self._single(criterion, V2.justification, checks, stage) if criterion else None
        criterion_known = (criterion is not None
                           and (criterion, RDF.type, MADO.CriterioDeDecisaoMultimodal) in self.graph
                           and criterion_source_record is not None
                           and criterion_locator is not None and criterion_justification is not None)
        knowledge_record = self._knowledge(knowledge, checks, stage)
        construction = self._articulation(articulation, knowledge, checks, stage)
        valid = status == "CURATED_FOR_PILOT" and criterion_known
        checks.add(stage, node, "GROUNDING_AUTHORIZATION", "PASS" if valid else "FAIL",
                   "CURATED_FOR_PILOT e critério registrado",
                   {"status": status, "criterion_registered": criterion_known},
                   "A aplicação liga exatamente este conhecimento, critério e articulação; não uma lista global.")
        if not (valid and knowledge_record and construction):
            return None
        return {**self._record(node), "knowledge": knowledge_record,
                "criterion": {**self._record(criterion),
                              "source": criterion_source_record,
                              "locator": str(criterion_locator), "justification": str(criterion_justification)},
                "articulation": construction,
                "check_ids": [row["id"] for row in checks.history[start:]]}

    def _capability(self, node: URIRef, function: URIRef, resources: dict,
                    facts: dict, checks: _Checks) -> dict[str, Any]:
        start = len(checks.history)
        fields = {name: self._single(node, V2[name], checks, "capability", iri=name != "action")
                  for name in ("provides", "mode", "inputType", "outputType", "action")}
        limitation = self._single(node, V2.limitation, checks, "capability")
        typed = all(fields[name] is not None and (fields[name], RDF.type, expected) in self.graph
                    for name, expected in (("mode", V2.Mode), ("inputType", V2.Representation),
                                            ("outputType", V2.Representation)))
        types = checks.add("capability", node, "CAPABILITY_CONCEPT_TYPES", "PASS" if typed else "FAIL",
                           "modo e representações declarados", {name: str(fields[name]) for name in ("mode", "inputType", "outputType")},
                           "Não se interpreta um recurso, diagnóstico ou rótulo como uma modalidade ou representação.")
        field_checks = list(checks.history[start:])
        rows = self._requirements(node, V2.requiresResource, V2.Resource, resources, checks, "capability")
        rows += self._requirements(node, V2.requiresFact, V2.ContextFact, facts, checks, "capability")
        supports, rejected = [], []
        for application in sorted(set(self.graph.subjects(V2.capability, node)), key=str):
            typed = (application, RDF.type, V2.GroundingApplication) in self.graph
            target = self._single(application, V2.capability, checks, "grounding", iri=True)
            justification = self._single(application, V2.justification, checks, "grounding")
            support = self._grounding(application, checks, "grounding")
            if typed and target == node and justification is not None and support:
                support["justification"] = str(justification)
                supports.append(support)
            else:
                rejected.append(str(application))
        grounded = checks.add("capability", node, "EXACT_GROUNDING", "PASS" if supports else "FAIL",
                              "ao menos uma aplicação exata autorizada", [item["id"] for item in supports],
                              "Nenhuma capacidade é selecionada somente por nome, modalidade ou bibliografia.")
        states = [row["state"] for row in rows] + [grounded["state"], types["state"]]
        if not all(value is not None for value in fields.values()) or limitation is None or fields["provides"] != function:
            states.append("FAIL")
        state = _worst(states)
        return {**self._record(node), "function": self._record(function),
                "mode": self._record(fields["mode"]) if fields["mode"] else None,
                "input_type": str(fields["inputType"]) if fields["inputType"] else None,
                "output_type": str(fields["outputType"]) if fields["outputType"] else None,
                "action": str(fields["action"]) if fields["action"] else "",
                "limitation": str(limitation) if limitation else "", "state": state,
                "required_resources": [self._record(item) for item in self._values(node, V2.requiresResource)],
                "required_facts": [self._record(item) for item in self._values(node, V2.requiresFact)],
                "groundings": supports, "rejected_groundings": rejected,
                "check_ids": list(dict.fromkeys([row["id"] for row in field_checks + rows + [grounded]]
                                                  + [cid for support in supports for cid in support["check_ids"]])),
                "evaluation_check_ids": list(dict.fromkeys(row["id"] for row in checks.history[start:])),
                "condition_checks": rows}

    def _relation(self, rule: URIRef, left: dict, right: dict, facts: dict,
                  checks: _Checks) -> dict[str, Any]:
        start = len(checks.history)
        fields = {name: self._single(rule, V2[name], checks, "relation", iri=True)
                  for name in ("fromFunction", "toFunction", "sharedType")}
        kind = self._single(rule, V2.relationKind, checks, "relation")
        explanation = self._single(rule, V2.explanation, checks, "relation")
        expected = {"from_function": left["function"]["id"], "to_function": right["function"]["id"],
                    "shared_type": left["output_type"]}
        actual = {"from_function": str(fields["fromFunction"]), "to_function": str(fields["toFunction"]),
                  "shared_type": str(fields["sharedType"]), "next_input_type": right["input_type"]}
        compatible = (fields["fromFunction"] is not None and fields["toFunction"] is not None
                      and fields["sharedType"] is not None
                      and str(fields["fromFunction"]) == left["function"]["id"]
                      and str(fields["toFunction"]) == right["function"]["id"]
                      and left["output_type"] == str(fields["sharedType"]) == right["input_type"])
        match = checks.add("relation", rule, "TYPED_TRANSITION", "PASS" if compatible else "FAIL", expected, actual,
                           "O tipo produzido pela primeira etapa deve ser o tipo aceito pela seguinte.")
        kind_check = checks.add("relation", rule, "SUPPORTED_RELATION_SEMANTICS",
                                "PASS" if str(kind) == "SEQUENTIAL_REVIEW" else "FAIL",
                                "SEQUENTIAL_REVIEW", str(kind) if kind else None,
                                "Relação de projeto registrada; não equivale a uma classificação CARE inferida.")
        requirements = self._requirements(rule, V2.requiresFact, V2.ContextFact, facts, checks, "relation")
        support = self._grounding(rule, checks, "relation_grounding")
        state = _worst([match["state"], kind_check["state"]] + [row["state"] for row in requirements]
                       + (["FAIL"] if not support or explanation is None else []))
        return {**self._record(rule), "state": state, "kind": str(kind) if kind else None,
                "from_capability": left["id"], "to_capability": right["id"],
                "from_function": left["function"]["id"], "to_function": right["function"]["id"],
                "shared_type": str(fields["sharedType"]) if fields["sharedType"] else None,
                "explanation": str(explanation) if explanation else "", "grounding": support,
                "condition_checks": requirements,
                "check_ids": [row["id"] for row in checks.history[start:]]}

    def _choice(self, steps: tuple[dict, ...], relations: tuple[dict, ...],
                context: dict, state: str) -> dict[str, Any]:
        signature = {"context": context, "steps": [step["id"] for step in steps],
                     "relations": [relation["id"] for relation in relations],
                     "files": sorted(self.fingerprints.values())}
        return {"id": "proposal-" + _json_hash(signature)[:20], "state": state,
                "steps": list(steps), "relations": list(relations),
                "explanation": {
                    "actions": [step["action"] for step in steps],
                    "why_combine": [relation["explanation"] for relation in relations],
                    "limitations": list(dict.fromkeys(step["limitation"] for step in steps)),
                    "text": " → ".join(step["action"] for step in steps),
                },
                "epistemic_status": "PROPOSED_NOT_EVALUATED",
                "check_ids": sorted(set(row for entry in (*steps, *relations) for row in entry["check_ids"])),
                "limits": [
                    "Proposta composta de capacidades e relações curadas; não foi aplicada nem avaliada em uso.",
                    "A compatibilidade de tipos não comprova preservação efetiva do significado do conteúdo.",
                    "Ordem determinística não representa ranking de qualidade ou escolha ótima.",
                ]}

    def _compose_participants(self, context: dict[str, Any]) -> dict[str, Any]:
        """Check the same task separately; one person's abilities cannot license another.

        Shared equipment is availability, not operability. Only facts explicitly
        scoped to the context in RDF are inherited by participants. Traits are
        descriptions and never become confirmed capabilities.
        """
        base = {key: value for key, value in context.items() if key != "participants"}
        empty = self.compose({**base, "confirmed": False})
        empty["context_id"] = context.get("id")
        empty["participant_results"] = []
        issues = empty["input_issues"]
        people = context.get("participants")
        if not isinstance(people, list) or not people or len(people) > 50:
            issues.append({"code": "INVALID_PARTICIPANTS"})
            empty.update(status="INSUFFICIENT", proposal_status="NONE")
            return empty
        checks = _Checks()
        shared_facts = self._normalize_map(base.get("facts", {}), V2.ContextFact,
                                          "facts", checks, issues)
        shared_resources = self._normalize_map(base.get("resources", {}), V2.Resource,
                                              "resources", checks, issues)
        context_facts = {key: value for key, value in shared_facts.items()
                         if self._text(key, V2.scope) == "context"}
        ignored = [self._record(key) for key in shared_facts if key not in context_facts]
        participants = []
        identifiers = set()
        for person in people:
            if not isinstance(person, dict) or set(person) - {"id", "label", "traits", "facts", "resources"}:
                issues.append({"code": "INVALID_PARTICIPANT_FIELDS"})
                continue
            identifier = person.get("id")
            traits = person.get("traits", [])
            if (not isinstance(identifier, str) or not identifier.strip() or identifier in identifiers
                    or not isinstance(person.get("label", ""), str)
                    or not isinstance(traits, list) or any(not isinstance(item, str) for item in traits)):
                issues.append({"code": "INVALID_PARTICIPANT_ID_OR_DESCRIPTION", "participant_id": identifier})
                continue
            identifiers.add(identifier)
            facts = self._normalize_map(person.get("facts", {}), V2.ContextFact,
                                        "participants.facts", checks, issues)
            resources = self._normalize_map(person.get("resources", {}), V2.Resource,
                                            "participants.resources", checks, issues)
            for key in facts.keys() & context_facts.keys():
                if context_facts[key] is not None and facts[key] is not context_facts[key]:
                    issues.append({"code": "CONFLICTING_CONTEXT_FACT", "participant_id": identifier, "fact": str(key)})
            participants.append((person, {**context_facts, **facts}, {**shared_resources, **resources}))
        if issues:
            empty.update(status="INSUFFICIENT", proposal_status="NONE")
            empty["gaps"] = [{"code": "INPUT_REQUIRES_CORRECTION"}]
            return empty
        if base.get("confirmed") is not True:
            return empty
        children = []
        for person, facts, resources in participants:
            child_context = {**base, "id": str(base.get("id", "context")) + ":" + person["id"],
                             "facts": {str(key): value for key, value in facts.items()},
                             "resources": {str(key): value for key, value in resources.items()}}
            child = self.compose(child_context)
            # Check identifiers must remain unambiguous after merging people.
            check_ids = {row["id"]: "check-" + _json_hash({"participant": person["id"], "check": row["id"]})[:16]
                         for row in child.get("execution_evidence", [])}
            def scope(value):
                if isinstance(value, dict):
                    for key, item in list(value.items()):
                        if key == "id" and isinstance(item, str) and item in check_ids:
                            value[key] = check_ids[item]
                        elif key == "check_ids":
                            value[key] = [check_ids.get(identifier, identifier) for identifier in item]
                        else:
                            scope(item)
                elif isinstance(value, list):
                    for item in value:
                        scope(item)
            scope(child)
            for row in child.get("execution_evidence", []):
                row["participant_id"] = person["id"]
            children.append({"participant_id": person["id"], "label": person.get("label") or person["id"],
                             "traits": list(person.get("traits", [])), "result": child})
        result = copy.deepcopy(children[0]["result"])
        for key in ("choices", "alternatives", "pending_candidates", "partial_segments", "exclusions", "gaps",
                    "input_issues", "facts_to_confirm", "resources_to_confirm", "unavailable_conditions",
                    "other_condition_diagnostics", "function_coverage", "missing_functions", "integration_gaps",
                    "capability_evaluations", "relation_evaluations", "execution_evidence"):
            result[key] = []
        result.update(context_id=context.get("id"), participant_results=children,
                      unscoped_personal_facts=ignored,
                      scope="Mesma tarefa conferida separadamente para cada participante; não transfere capacidades entre pessoas.")
        complete = all(child["result"]["status"] == "COMPOSED" for child in children)
        for child in children:
            person_id, person_label, individual = child["participant_id"], child["label"], child["result"]
            for key in ("pending_candidates", "partial_segments", "exclusions", "gaps", "input_issues",
                        "facts_to_confirm", "resources_to_confirm", "unavailable_conditions",
                        "other_condition_diagnostics", "function_coverage", "missing_functions", "integration_gaps",
                        "capability_evaluations", "relation_evaluations", "execution_evidence"):
                result[key].extend({**copy.deepcopy(row), "participant_id": person_id, "participant_label": person_label}
                                   for row in individual.get(key, []))
            for choice in individual["choices"]:
                proposal = {**copy.deepcopy(choice), "participant_id": person_id, "participant_label": person_label}
                if complete:
                    result["choices"].append(proposal)
                else:
                    proposal.update(state="PARTIAL", ready_for_whole_task=False,
                                    covers_participant_task=True, covers_all_participants=False)
                    proposal["limits"].append("Esta rota atende somente às condições deste participante; não é solução pronta para o grupo.")
                    result["partial_segments"].append(proposal)
        result["alternatives"] = result["choices"]
        result["status"] = "COMPOSED" if complete else "INSUFFICIENT"
        result["proposal_status"] = ("COMPLETE" if complete else "PARTIAL" if result["partial_segments"]
                                     else "CONDITIONAL" if result["pending_candidates"] else "NONE")
        result["covers_all_participants"] = complete
        if not complete:
            result["gaps"].append({"code": "PARTICIPANTS_NOT_ALL_COVERED",
                                   "participant_ids": [child["participant_id"] for child in children
                                                       if child["result"]["status"] != "COMPOSED"]})
        if ignored:
            result["limits"].append("Condições pessoais fornecidas no nível global não foram atribuídas automaticamente aos participantes.")
        return result

    def compose(self, context: dict[str, Any]) -> dict[str, Any]:
        if isinstance(context, dict) and "participants" in context:
            return self._compose_participants(context)
        checks = _Checks()
        result: dict[str, Any] = {
            "status": "INSUFFICIENT", "proposal_status": "NONE",
            "context_id": context.get("id") if isinstance(context, dict) else None,
            "choices": [], "alternatives": [], "pending_candidates": [], "exclusions": [],
            "partial_segments": [], "partial_truncated": False,
            "function_coverage": [], "missing_functions": [], "integration_gaps": [],
            "facts_to_confirm": [], "resources_to_confirm": [], "unavailable_conditions": [],
            "other_condition_diagnostics": [],
            "gaps": [], "input_issues": [], "required_functions": [], "truncated": False,
            "pending_truncated": False, "maximum_choices": MAX_CHOICES,
            "search": {phase: {"examined": 0, "limit": MAX_COMBINATIONS_PER_PHASE, "truncated": False}
                       for phase in ("complete", "partial")},
            "fingerprints": dict(self.fingerprints), "execution_evidence": checks.rows,
            "scope": "Propostas com uma capacidade por função, uma tarefa e transições registradas; sem interpretação de narrativa.",
        }
        if not isinstance(context, dict):
            result["input_issues"].append({"code": "CONTEXT_NOT_OBJECT"})
            return result
        allowed_fields = {"id", "task", "confirmed", "resources", "facts"}
        for unknown in sorted(set(context) - allowed_fields):
            result["input_issues"].append({"code": "UNKNOWN_CONTEXT_FIELD", "field": unknown})
        confirmed = context.get("confirmed") is True
        checks.add("context", context.get("id", "context"), "CONFIRMED_CONTEXT",
                   "PASS" if confirmed else "PENDING", True, context.get("confirmed"),
                   "O compositor não presume que o caso estruturado foi confirmado.")
        if not confirmed:
            result["status"] = "UNCONFIRMED"
            result["proposal_status"] = "UNCONFIRMED"
            checks.add("composition", "context", "COMPOSITION", "NOT_EXECUTED", "contexto confirmado", None,
                       "Nenhuma capacidade ou relação foi autorizada antes da confirmação.")
            return result
        raw_tasks = context.get("task", [])
        raw_tasks = [raw_tasks] if isinstance(raw_tasks, str) else raw_tasks
        task = self._resolve(raw_tasks[0], V2.Task) if isinstance(raw_tasks, list) and len(raw_tasks) == 1 else None
        if task is None:
            result["input_issues"].append({"code": "UNKNOWN_OR_MULTIPLE_TASKS", "value": raw_tasks})
            checks.add("context", "task", "SINGLE_REGISTERED_TASK", "FAIL", "uma tarefa registrada", raw_tasks,
                       "O piloto não concatena tarefas arbitrariamente nem interpreta seus nomes.")
            return result
        resources = self._normalize_map(context.get("resources", {}), V2.Resource, "resources", checks, result["input_issues"])
        facts = self._normalize_map(context.get("facts", {}), V2.ContextFact, "facts", checks, result["input_issues"])
        if result["input_issues"]:
            result["gaps"].append({"code": "INPUT_REQUIRES_CORRECTION"})
            return result
        task_input = self._single(task, V2.inputType, checks, "task", iri=True)
        task_output = self._single(task, V2.outputType, checks, "task", iri=True)
        boundary_types = task_input is not None and task_output is not None and all(
            (item, RDF.type, V2.Representation) in self.graph for item in (task_input, task_output))
        checks.add("task", task, "TASK_REPRESENTATION_TYPES", "PASS" if boundary_types else "FAIL",
                   "tipos de representação declarados", [str(task_input), str(task_output)],
                   "A tarefa precisa explicitar o estado de entrada e o estado esperado ao final.")
        functions = self._values(task, V2.requiresFunction)
        orders: dict[URIRef, int] = {}
        for function in functions:
            order = self._single(function, V2.order, checks, "task")
            try:
                if not isinstance(order, Literal) or type(order.toPython()) is not int:
                    raise ValueError("ordem não inteira")
                orders[function] = int(order)
                if (function, RDF.type, V2.Function) not in self.graph:
                    raise ValueError("função não declarada")
            except (ValueError, TypeError):
                checks.add("task", function, "FUNCTION_ORDER", "FAIL", "função tipada com ordem inteira",
                           str(order), "Não se infere a sequência pelo nome da tarefa ou configuração selecionada.")
                result["gaps"].append({"code": "INVALID_REQUIRED_FUNCTION", "function": str(function)})
        if not functions or len(set(orders.values())) != len(functions):
            result["gaps"].append({"code": "MISSING_OR_AMBIGUOUS_FUNCTION_ORDER"})
        if not boundary_types:
            result["gaps"].append({"code": "INVALID_TASK_REPRESENTATION"})
        if result["gaps"]:
            return result
        functions.sort(key=lambda item: orders[item])
        result["task"] = {**self._record(task), "input_type": str(task_input), "output_type": str(task_output)}
        result["required_functions"] = [self._record(item) for item in functions]
        checks.add("task", task, "REQUIRED_FUNCTIONS", "PASS", "funções explicitamente exigidas pela tarefa",
                   [str(item) for item in functions],
                   "As funções não são deduzidas retrospectivamente das capacidades selecionadas.")
        candidates: list[list[dict[str, Any]]] = []
        result["capability_evaluations"] = []
        for function in functions:
            options = []
            for node in sorted(set(self.graph.subjects(V2.provides, function)), key=str):
                if (node, RDF.type, V2.Capability) not in self.graph:
                    continue
                option = self._capability(node, function, resources, facts, checks)
                result["capability_evaluations"].append(option)
                if option["state"] == "FAIL":
                    result["exclusions"].append({"kind": "capability", "id": option["id"],
                                                 "check_ids": option["check_ids"], "reason": "CONDITION_OR_GROUNDING_FAILED"})
                else:
                    options.append(option)
            if not options:
                result["gaps"].append({"code": "FUNCTION_NOT_COVERED", "function": str(function)})
            candidates.append(options)
            available = [item["id"] for item in options if item["state"] == "PASS"]
            conditional = [item["id"] for item in options if item["state"] == "PENDING"]
            coverage = {"function": self._record(function), "available_capabilities": available,
                        "conditional_capabilities": conditional,
                        "state": "CAPABILITY_AVAILABLE" if available else "CONDITIONAL_CAPABILITY" if conditional else "NO_AVAILABLE_CAPABILITY",
                        "limit": "Disponibilidade de uma capacidade não comprova encadeamento completo da tarefa."}
            result["function_coverage"].append(coverage)
            if not available:
                result["missing_functions"].append(coverage)
        relation_rules = sorted(set(self.graph.subjects(RDF.type, V2.RelationRule)), key=str)
        relation_cache: dict[tuple[str, str], list[dict[str, Any]]] = {}
        result["relation_evaluations"] = []

        def consume(phase: str) -> bool:
            budget = result["search"][phase]
            if budget["examined"] >= budget["limit"]:
                budget["truncated"] = True
                return False
            budget["examined"] += 1
            return True

        def transition_options(left: dict, right: dict) -> list[dict[str, Any]]:
            key = (left["id"], right["id"])
            if key not in relation_cache:
                matches = []
                for rule in relation_rules:
                    if (URIRef(left["function"]["id"]) not in self._values(rule, V2.fromFunction)
                            or URIRef(right["function"]["id"]) not in self._values(rule, V2.toFunction)):
                        continue
                    relation = self._relation(rule, left, right, facts, checks)
                    result["relation_evaluations"].append(relation)
                    if relation["state"] == "FAIL":
                        result["exclusions"].append({"kind": "relation", "id": relation["id"],
                                                     "from_capability": left["id"], "to_capability": right["id"],
                                                     "reason": "RELATION_NOT_AUTHORIZED", "check_ids": relation["check_ids"]})
                    else:
                        matches.append(relation)
                if not matches:
                    absence = checks.add("relation", "|".join(key), "AUTHORIZED_TRANSITION", "FAIL",
                                         "relação tipada e fundamentada", [],
                                         "Proximidade de funções ou presença de várias modalidades não autoriza uma combinação.")
                    result["exclusions"].append({"kind": "transition", "from_capability": left["id"],
                                                 "to_capability": right["id"], "reason": "NO_AUTHORIZED_RELATION",
                                                 "check_ids": [absence["id"]]})
                relation_cache[key] = matches
            return relation_cache[key]

        for steps in itertools.product(*candidates):
            if not consume("complete"):
                break
            boundary_ok = steps[0]["input_type"] == str(task_input) and steps[-1]["output_type"] == str(task_output)
            boundary = checks.add("composition", "|".join(step["id"] for step in steps), "TASK_BOUNDARIES",
                                  "PASS" if boundary_ok else "FAIL",
                                  {"input": str(task_input), "output": str(task_output)},
                                  {"input": steps[0]["input_type"], "output": steps[-1]["output_type"]},
                                  "A sequência deve cumprir os tipos de entrada e saída declarados pela tarefa.")
            if not boundary_ok:
                result["exclusions"].append({"kind": "composition", "steps": [step["id"] for step in steps],
                                             "reason": "TASK_BOUNDARY_MISMATCH", "check_ids": [boundary["id"]]})
                continue
            transitions = [transition_options(left, right) for left, right in zip(steps, steps[1:])]
            for relations in itertools.product(*transitions):
                if not consume("complete"):
                    break
                state = _worst([step["state"] for step in steps] + [relation["state"] for relation in relations])
                bucket = result["choices"] if state == "PASS" else result["pending_candidates"]
                truncation = "truncated" if state == "PASS" else "pending_truncated"
                if len(bucket) >= MAX_CHOICES:
                    result[truncation] = True
                    continue
                proposal = self._choice(steps, relations, context, state)
                proposal["check_ids"].append(boundary["id"])
                proposal["covers_all_required_functions"] = True
                proposal["conditions_satisfied"] = state == "PASS"
                bucket.append(proposal)
            if result["search"]["complete"]["truncated"]:
                break

        # A segment never combines disconnected functions or satisfies the entire
        # task. It records usable design work even when the final decision is held.
        # Longest contiguous intervals first avoid showing redundant subsegments;
        # this is display enumeration by coverage, not a quality/preference score.
        if not result["choices"]:
            supported = [[item for item in options if item["state"] == "PASS"] for options in candidates]
            intervals = ((start, start + width) for width in range(len(functions) - 1, 0, -1)
                         for start in range(len(functions) - width + 1))
            for first, stop in intervals:
                if result["search"]["partial"]["truncated"]:
                    break
                for steps in itertools.product(*supported[first:stop]):
                    if not consume("partial"):
                        break
                    boundary_ok = ((first != 0 or steps[0]["input_type"] == str(task_input))
                                   and (stop != len(functions) or steps[-1]["output_type"] == str(task_output)))
                    boundary = checks.add("partial", "|".join(step["id"] for step in steps), "SEGMENT_BOUNDARIES",
                                          "PASS" if boundary_ok else "FAIL",
                                          {"task_input_if_initial": str(task_input), "task_output_if_final": str(task_output)},
                                          {"first_function_index": first, "stop_function_index": stop,
                                           "input": steps[0]["input_type"], "output": steps[-1]["output_type"]},
                                          "Somente fronteiras da tarefa presentes neste segmento são conferidas; a entrada de um segmento interno não é presumida disponível.")
                    if not boundary_ok:
                        continue
                    transitions = [[relation for relation in transition_options(left, right) if relation["state"] == "PASS"]
                                   for left, right in zip(steps, steps[1:])]
                    for relations in itertools.product(*transitions):
                        if not consume("partial"):
                            break
                        ids = [step["id"] for step in steps]
                        relation_ids = [relation["id"] for relation in relations]
                        redundant = False
                        for previous in result["partial_segments"]:
                            offset = first - previous["first_function_index"]
                            if (offset >= 0 and stop <= previous["stop_function_index"]
                                    and [step["id"] for step in previous["steps"]][offset:offset + len(ids)] == ids
                                    and [relation["id"] for relation in previous["relations"]][offset:offset + len(relation_ids)] == relation_ids):
                                redundant = True
                                break
                        if redundant:
                            continue
                        if len(result["partial_segments"]) >= MAX_CHOICES:
                            result["partial_truncated"] = True
                            continue
                        partial = self._choice(steps, relations, context, "PARTIAL")
                        partial.update({
                            "first_function_index": first, "stop_function_index": stop,
                            "covers_all_required_functions": False, "conditions_satisfied": True,
                            "ready_for_whole_task": False,
                            "covered_functions": [self._record(function) for function in functions[first:stop]],
                            "missing_functions": [self._record(function) for index, function in enumerate(functions)
                                                  if not first <= index < stop],
                            "entry": {"representation": steps[0]["input_type"],
                                      "origin": "DECLARED_TASK_INPUT" if first == 0 else "PRIOR_FUNCTION_OUTPUT_REQUIRED",
                                      "prior_function": str(functions[first - 1]) if first else None,
                                      "availability_verified": False,
                                      "can_execute_without_required_input": False},
                            "output_representation": steps[-1]["output_type"],
                            "remaining_after": [self._record(function) for function in functions[stop:]],
                        })
                        partial["check_ids"].append(boundary["id"])
                        partial["limits"].append("Segmento apoiado, não orientação completa. Não implica conclusão, envio ou atendimento das funções que ficaram de fora.")
                        if first:
                            partial["limits"].append("Esta parte depende da saída de uma função anterior; a disponibilidade dessa entrada não foi comprovada.")
                        result["partial_segments"].append(partial)
                    if result["search"]["partial"]["truncated"]:
                        break

        question_routes: dict[str, list[dict[str, str]]] = {}
        for pending in result["pending_candidates"]:
            for entry in pending["steps"] + pending["relations"]:
                question_routes.setdefault(entry["id"], []).append({
                    "id": pending["id"], "kind": "CONDITIONAL_COMPLETE_CANDIDATE"})
        if not result["choices"]:
            for capability in result["capability_evaluations"]:
                if capability["state"] == "PENDING" and capability["groundings"]:
                    question_routes.setdefault(capability["id"], []).append({
                        "id": capability["id"], "kind": "CONDITIONAL_CAPABILITY_NOT_COMPLETE_PLAN"})
        conditions: dict[tuple[str, str], dict[str, Any]] = {}
        for row in checks.rows:
            if row["kind"] not in {"REQUIRES_requiresFact", "REQUIRES_requiresResource"}:
                continue
            observed = row["observed"]
            if not observed["declared"] or observed["value"] is True:
                continue
            key = (row["kind"], observed["concept"])
            entry = conditions.setdefault(key, {
                **self._record(URIRef(observed["concept"])),
                "kind": "fact" if row["kind"] == "REQUIRES_requiresFact" else "resource",
                "value": observed["value"], "state": row["state"], "required_by": [], "check_ids": [],
                "candidate_ids": [], "candidates": [], "question_required_by": [],
            })
            if row["subject"] not in entry["required_by"]:
                entry["required_by"].append(row["subject"])
            entry["check_ids"].append(row["id"])
            if row["subject"] in question_routes:
                if row["subject"] not in entry["question_required_by"]:
                    entry["question_required_by"].append(row["subject"])
                for candidate in question_routes[row["subject"]]:
                    if candidate not in entry["candidates"]:
                        entry["candidates"].append(candidate)
                    if candidate["id"] not in entry["candidate_ids"]:
                        entry["candidate_ids"].append(candidate["id"])
        for key in sorted(conditions):
            condition = conditions[key]
            if condition["value"] is False:
                result["unavailable_conditions"].append(condition)
            elif condition["candidates"]:
                target = "facts_to_confirm" if condition["kind"] == "fact" else "resources_to_confirm"
                result[target].append(condition)
            else:
                condition["reason"] = "NO_CURRENTLY_VIABLE_CANDIDATE_DEPENDS_ON_THIS_CONFIRMATION"
                result["other_condition_diagnostics"].append(condition)
        result["integration_gaps"] = [item for item in result["exclusions"] if item["kind"] in {"relation", "transition", "composition"}]
        result["alternatives"] = result["choices"]
        if result["choices"]:
            result["status"] = "COMPOSED"
            result["proposal_status"] = "COMPLETE"
        else:
            result["proposal_status"] = ("CONDITIONAL" if result["pending_candidates"] else
                                         "PARTIAL" if result["partial_segments"] else "NONE")
            result["gaps"].append({"code": "PENDING_CONDITIONS" if result["pending_candidates"] else "NO_COMPLETE_COMPOSITION",
                                   "explanation": "Nenhum plano parcial ou candidato pendente é apresentado como orientação pronta."})
        if any(phase["truncated"] for phase in result["search"].values()):
            result["gaps"].append({"code": "SEARCH_LIMIT_REACHED",
                                   "explanation": "A busca foi limitada; ausência de uma composição não prova inexistência de outras combinações na base."})
        result["limits"] = [
            "Resultados são propostas de projeto, não garantia de acessibilidade ou melhores resultados educacionais.",
            "Fatos e disponibilidade são declarações confirmadas no contexto; não medições realizadas pelo programa.",
            "Conferência documental representa o estado registrado da contribuição; não nova leitura das fontes nesta execução.",
            "Não há interpretação de texto livre, comparação de preferências nem otimização entre as alternativas.",
            "Etapas parciais não podem ser unidas pela interface para fingir uma composição que não foi verificada.",
        ]
        return result

class _SituatedRun:
    """Run-local evaluator for the existing, qualified research operations.

    The JSON contracts are part of the research base, not a second catalogue of
    answers. They qualify existing components and source claims. This evaluator
    checks a finite operation graph; it neither writes claims nor invents edges.
    """

    FIELD_KINDS = {"task": "tarefas", "characteristic": "caracteristicas_pessoa",
                   "barrier": "barreiras", "need": "necessidades", "environment": "ambientes",
                   "modality": "modalidades_disponiveis", "digital_resource": "recursos_digitais",
                   "resource_available": "recursos_disponiveis", "resource_proposed": "recursos_propostos",
                   "resource_blocked": "recursos_impedidos"}
    SITUATION_FIELDS = {"task_ids": "tarefas", "env_ids": "ambientes", "mode_ids": "modalidades_disponiveis",
                        "need_ids": "necessidades", "barrier_ids": "barreiras"}
    RELATIONS = {"SEQUENTIAL", "SEQUENTIAL_REVIEW", "ALTERNATIVE", "COMPLEMENTARITY", "REDUNDANCY"}
    # Identity bridges, not affordance inference. A computer is not a legible
    # display, voice control is not dictation, and a microphone is not ASR.
    RESOURCE_ALIASES = {"REC-MICROFONE": "Microphone", "REC-TECLADO": "Keyboard",
                        "REC-TTS": "TextToSpeech"}

    def __init__(self, composer, context, engine=None, progress=None):
        self.composer, self.engine, self.progress = composer, engine, progress
        self.context = copy.deepcopy(context) if isinstance(context, dict) else {}
        self.base = copy.deepcopy(getattr(composer, "base", {}))
        self.index = {name: {row["id"]: row for row in self.base.get(name, []) if isinstance(row, dict) and "id" in row}
                      for name in ("knowledge", "sources", "excerpts", "criteria", "criterion_origins", "context_elements", "contributions", "articulations")}
        self.checks = _Checks()
        self.conditions = []
        self.result = {
            "schema_version": "2.0.0-alpha3", "composition_kind": "SITUATED_OPERATION_GRAPH",
            "status": "INSUFFICIENT", "proposal_status": "NONE", "context_id": self.context.get("id"),
            "choices": [], "alternatives": [], "pending_candidates": [], "partial_segments": [],
            "exclusions": [], "gaps": [], "input_issues": [], "function_coverage": [], "missing_functions": [],
            "integration_gaps": [], "required_functions": [], "capability_evaluations": [], "relation_evaluations": [],
            "facts_to_confirm": [], "resources_to_confirm": [], "unavailable_conditions": [],
            "other_condition_diagnostics": [], "claim_audit": [], "participant_results": [], "situation_results": [],
            "execution_evidence": self.checks.rows, "fingerprints": dict(composer.fingerprints),
            "execution_inputs": {"context_sha256": _json_hash(self.context), "catalogue_sha256": _json_hash(self.base),
                                 "rdf_graph_sha256": _json_hash(sorted(" ".join(term.n3() for term in triple) for triple in composer.graph))},
            "search": {"complete": {"examined": 0, "limit": MAX_COMBINATIONS_PER_PHASE, "truncated": False}},
            "maximum_choices": MAX_CHOICES, "truncated": False, "pending_truncated": False, "partial_truncated": False,
            "scope": "Composição situada limitada às funções, operações, relações e alegações documentadas na base.",
            "limits": ["Propostas de projeto; não demonstram compreensão, preservação efetiva de significado ou acessibilidade em uso.",
                       "Alegações documentais pendentes permanecem na auditoria e não autorizam orientação.",
                       "Condições são declarações situadas; o programa não mede a capacidade das pessoas.",
                       "A enumeração é determinística, limitada e não classifica uma alternativa como ótima."]}
        if not isinstance(context, dict):
            self.result["input_issues"].append({"code": "CONTEXT_NOT_OBJECT"})
        self.people = {}
        self.rdf_components = self.project_rdf_operations()

    def project_rdf_operations(self):
        """A transient view of existing RDF capabilities, not another engine.

        Keep their own identifiers and task/function vocabulary. No equivalence
        to the main FUN-* concepts is asserted by this projection.
        """
        graph, result = self.composer.graph, []
        for entity_type in (V2.Function, V2.Task, V2.Resource, V2.Mode, V2.Representation, V2.ContextFact):
            for node in graph.subjects(RDF.type, entity_type):
                self.index["context_elements"][str(node)] = {"id": str(node), "rotulo": self.composer._record(node)["label"]}
        rules = []
        for node in sorted(graph.subjects(RDF.type, V2.RelationRule), key=str):
            shared = self.composer._values(node, V2.sharedType)
            if len(shared) != 1:
                continue
            rules.append({"id": str(node), "kind": self.composer._text(node, V2.relationKind), "scope": "BETWEEN_OPERATIONS",
                "from_function_ids": [str(x) for x in self.composer._values(node, V2.fromFunction)],
                "to_function_ids": [str(x) for x in self.composer._values(node, V2.toFunction)],
                "from_representation_ids": [str(shared[0])], "to_representation_ids": [str(shared[0])],
                "meaning_unit": str(shared[0]), "preserves": self.composer._text(node, V2.explanation),
                "sufficiency": "DECLARED_DRAFT_REVIEW_WITH_REQUIRED_CHECKS", "temporal": "PRODUCTION_BEFORE_REVIEW",
                "requires_facts": self.rdf_facts(node), "claim_support": [{"rdf_application_id": str(node)}],
                "explanation": self.composer._text(node, V2.explanation)})
        for node in sorted(graph.subjects(RDF.type, V2.Capability), key=str):
            functions = [str(x) for x in self.composer._values(node, V2.provides)]
            inputs, outputs = self.composer._values(node, V2.inputType), self.composer._values(node, V2.outputType)
            bindings = getattr(self.composer, "bindings", {}).get("contracts", {}).get(_local(node), {})
            facts = self.rdf_facts(node)
            for short in bindings.get("requires_facts", []):
                facts.append({"id": str(V2[short]), "label": getattr(self.composer, "bindings", {}).get("facts", {}).get(short, {}).get("label", short)})
            result.append({"id": str(node), "label": self.composer._record(node)["label"], "active_in_rc4": True,
                "mode_id": str(next(iter(self.composer._values(node, V2.mode)), "")),
                "operation_contract": {"id": str(node), "function_ids": functions,
                    "action": self.composer._text(node, V2.action),
                    "input_requirements": [{"representation_id": str(x), "meaning_unit": str(x), "required": True} for x in inputs],
                    "output_spec": [{"representation_id": str(x), "meaning_unit": str(x), "required": True} for x in outputs],
                    "representation_ids": [str(x) for x in self.composer._values(node, V2.mode)],
                    "selected_representation_ids": [str(x) for x in self.composer._values(node, V2.mode)],
                    "resource_requirements": {"all": [str(x) for x in self.composer._values(node, V2.requiresResource)], "capability_check_required": False},
                    "requires_facts": facts, "role_requirements": {},
                    "transfer_scope": {"task_ids": [str(t) for t in graph.subjects(RDF.type, V2.Task)
                                                     if any((t, V2.requiresFunction, URIRef(f)) in graph for f in functions)]},
                    "claim_support": [{"rdf_application_id": str(x)} for x in graph.subjects(V2.capability, node)],
                    "limits": [self.composer._text(node, V2.limitation)],
                    "relations": [r for r in rules if set(r["from_function_ids"]) & set(functions)]}})
        return result

    def rdf_facts(self, node):
        return [{"id": str(x), "label": self.composer._record(x)["label"]}
                for x in self.composer._values(node, V2.requiresFact)]

    def rdf_alias(self, identifier, entity_type):
        if entity_type == V2.Resource:
            local = str(identifier).removeprefix(str(MADO))
            identifier = self.RESOURCE_ALIASES.get(local, identifier)
        node = self.composer._resolve(identifier, entity_type)
        if node is None and entity_type == V2.ContextFact and identifier in getattr(self.composer, "bindings", {}).get("facts", {}):
            return str(V2[identifier])
        return str(node) if node is not None else identifier

    def fact_alias(self, identifier):
        resource = self.rdf_alias(identifier, V2.Resource)
        if self.composer._resolve(resource, V2.Resource) is not None:
            return resource
        return self.rdf_alias(identifier, V2.ContextFact)

    def assign_fact(self, unit, identifier, value):
        key = self.fact_alias(identifier)
        if value is not None and type(value) is not bool:
            self.result["input_issues"].append({"code": "INVALID_FACT_VALUE", "id": key})
        elif key in unit["facts"] and unit["facts"][key] is not value:
            self.result["input_issues"].append({"code": "CONFLICTING_SITUATED_FACT", "id": key,
                "situation_id": unit["situation_id"], "participant_id": unit["participant_id"]})
        else:
            unit["facts"][key] = value

    def label(self, identifier):
        row = self.index["context_elements"].get(identifier, {})
        return row.get("rotulo") or identifier

    def record(self, identifier):
        return {"id": identifier, "label": self.label(identifier)}

    def emit(self, stage, state, message):
        if self.progress:
            self.progress({"stage": stage, "state": state, "message": message})

    def check(self, unit, subject, kind, state, expected, observed, explanation):
        scope = {"situation_id": unit.get("situation_id"), "participant_id": unit.get("participant_id")}
        return self.checks.add("situated_" + kind.lower(), subject, kind, state,
                               {**scope, "value": expected}, {**scope, "value": observed}, explanation)

    def matches(self, observed, expected):
        if observed == expected:
            return True
        if self.engine is not None and hasattr(self.engine, "_task_path"):
            return bool(self.engine._task_path(observed, expected))
        skos_broader = URIRef("http://www.w3.org/2004/02/skos/core#broader")
        pending, seen = [MADO[observed]], set()
        while pending:
            current = pending.pop()
            if current == MADO[expected]:
                return True
            if current not in seen:
                seen.add(current)
                pending.extend(self.composer.graph.objects(current, skos_broader))
        return False

    def intersects(self, values, required):
        return any(self.matches(value, expected) for value in values for expected in required)

    def normalize(self):
        people = self.context.get("participations", self.context.get("participants", []))
        if not isinstance(people, list):
            self.result["input_issues"].append({"code": "INVALID_PARTICIPANTS"})
            return []
        for person in people:
            if not isinstance(person, dict) or not isinstance(person.get("id"), str) or not person["id"] or person["id"] in self.people:
                self.result["input_issues"].append({"code": "INVALID_OR_DUPLICATE_PARTICIPANT"})
                continue
            self.people[person["id"]] = person
        situations = self.context.get("situations")
        explicit = bool(situations)
        if situations is None or situations == []:
            tasks = self.context.get("tarefas", []) or ([self.context["task"]] if self.context.get("task") else [])
            situations = [{"id": "situation-default", "task_ids": tasks,
                           "participant_ids": list(self.people)}]
        if not isinstance(situations, list) or len(situations) > 50 or any(not isinstance(s, dict) for s in situations):
            self.result["input_issues"].append({"code": "INVALID_SITUATIONS"})
            return []
        assertions = self.context.get("assertions", [])
        if not isinstance(assertions, list):
            self.result["input_issues"].append({"code": "INVALID_ASSERTIONS"})
            return []
        situated_facts = self.context.get("situated_facts", [])
        if not isinstance(situated_facts, list) or any(not isinstance(fact, dict) or not isinstance(fact.get("fact_id"), str) for fact in situated_facts):
            self.result["input_issues"].append({"code": "INVALID_SITUATED_FACTS"})
            return []
        units, seen = [], set()
        active = self.context.get("active_situation_id")
        if active and not any(isinstance(s, dict) and s.get("id") == active for s in situations):
            self.result["input_issues"].append({"code": "UNKNOWN_ACTIVE_SITUATION", "id": active})
            return []
        self.result["deferred_situation_ids"] = [s.get("id") for s in situations if active and s.get("id") != active]
        for situation in situations:
            if active and situation.get("id") != active:
                continue
            sid = situation.get("id") if isinstance(situation, dict) else None
            if not isinstance(sid, str) or not sid or sid in seen:
                self.result["input_issues"].append({"code": "INVALID_OR_DUPLICATE_SITUATION"})
                continue
            seen.add(sid)
            ids = situation.get("participant_ids", [])
            if not isinstance(ids, list) or any(identifier not in self.people for identifier in ids):
                self.result["input_issues"].append({"code": "UNKNOWN_SITUATION_PARTICIPANT", "situation_id": sid})
                continue
            if not ids and not explicit:
                ids = list(self.people)
            for pid in ids or [self.context.get("id") or "unassigned-person"]:
                person = self.people.get(pid, {})
                unit = {"situation_id": sid, "participant_id": pid, "participant": person,
                        "situation_label": situation.get("label", sid), "participant_label": person.get("label", person.get("rotulo", pid)),
                        "participant_ids": ids, "situation": situation, "facts": {},
                        "required_explicit": list(situation.get("function_ids", [])) if len(ids) <= 1 else list(person.get("function_ids", [])), "assertion_ids": []}
                for field in set(self.FIELD_KINDS.values()):
                    # Legacy arrays refer to one situation. Personal arrays do
                    # not license each member of a multi-person context.
                    inherit = not explicit and (len(self.people) <= 1 or field not in {"caracteristicas_pessoa", "modalidades_disponiveis", "necessidades", "barreiras"})
                    unit[field] = list(self.context.get(field, [])) if inherit else []
                for origin, field in self.SITUATION_FIELDS.items():
                    if origin in situation:
                        if len(ids) > 1 and origin in {"need_ids", "barrier_ids", "mode_ids"}:
                            continue
                        unit[field] = list(situation[origin])
                unit["caracteristicas_pessoa"] = list(person.get("caracteristica_ids", person.get("characteristic_ids", unit["caracteristicas_pessoa"])))
                if person.get("modalidade_ids"):
                    unit["modalidades_disponiveis"] = list(person["modalidade_ids"])
                if not explicit and len(ids) <= 1 and not unit["required_explicit"]:
                    unit["required_explicit"] = list(self.context.get("funcoes_requeridas_ids", []))
                for source in (self.context if not explicit else {}, situation, person):
                    facts = source.get("facts", {})
                    if isinstance(facts, dict):
                        for key, value in facts.items():
                            if len(ids) > 1 and source is not person:
                                concept = self.composer._resolve(key, V2.ContextFact)
                                if concept is None or self.composer._text(concept, V2.scope) != "context":
                                    continue
                            self.assign_fact(unit, key, value)
                # The legacy pilot maps are normalized into this same situated
                # contract; they never invoke its old search procedure.
                for key, value in (self.context.get("resources", {}) if not explicit else {}).items():
                    if value is not None and type(value) is not bool:
                        self.result["input_issues"].append({"code": "INVALID_RESOURCE_VALUE", "id": key})
                    resource = self.rdf_alias(key, V2.Resource)
                    if value is True:
                        unit["recursos_disponiveis"].append(resource)
                    elif value is False:
                        unit["recursos_impedidos"].append(resource)
                for fact in situated_facts:
                    if fact.get("participant_id") == pid and fact.get("situation_id") == sid:
                        value = fact.get("value")
                        self.assign_fact(unit, fact["fact_id"], value)
                for resource in situation.get("resource_states", []):
                    field = {"DISPONIVEL_CONFIRMADO": "recursos_disponiveis", "PROPOSTO_A_PREPARAR": "recursos_propostos", "IMPEDIDO": "recursos_impedidos"}.get(resource.get("state"))
                    if field and resource.get("resource_id"):
                        unit[field].append(resource["resource_id"])
                for key, value in person.get("resources", {}).items():
                    resource = self.rdf_alias(key, V2.Resource)
                    if value is not None and type(value) is not bool:
                        self.result["input_issues"].append({"code": "INVALID_PERSON_RESOURCE_VALUE", "id": key, "participant_id": pid})
                    elif value is False:
                        unit["recursos_disponiveis"] = [r for r in unit["recursos_disponiveis"]
                                                        if self.rdf_alias(r, V2.Resource) != resource]
                        unit["recursos_impedidos"].append(resource)
                    elif value is True:
                        unit["recursos_disponiveis"].append(resource)
                for assertion in assertions:
                    if not isinstance(assertion, dict):
                        self.result["input_issues"].append({"code": "INVALID_ASSERTION"})
                        continue
                    scope = assertion.get("situation_id", "")
                    owner = assertion.get("subject_id", "")
                    if scope != sid and (scope or explicit and len(situations) > 1):
                        continue
                    if owner not in {pid, self.context.get("id"), ""}:
                        continue
                    if owner != pid and assertion.get("kind") in {"characteristic", "modality", "need", "barrier"} and len(self.people) > 1:
                        continue
                    state = assertion.get("state")
                    if state == "CONFLITO":
                        self.result["input_issues"].append({"code": "CONFLICTING_ASSERTION", "assertion_id": assertion.get("id"), "situation_id": sid})
                        continue
                    accepted = state == "CONFIRMADO" or state == "RELATADO" and self.context.get("confirmed") is True
                    field = self.FIELD_KINDS.get(assertion.get("kind"))
                    value = assertion.get("value")
                    if accepted and field and isinstance(value, str):
                        unit[field].append(value)
                        unit["assertion_ids"].append(assertion.get("id"))
                for field in set(self.FIELD_KINDS.values()):
                    unit[field] = sorted(set(unit[field]))
                for field in ("recursos_disponiveis", "recursos_impedidos", "recursos_propostos"):
                    unit[field] = sorted({self.rdf_alias(value, V2.Resource) for value in unit[field]})
                unit["tarefas"] = [self.rdf_alias(t, V2.Task) for t in unit["tarefas"]]
                # Participation in an episode is not execution of every task
                # in it. Keep the task context separate from personal action.
                assigned = [a["value"] for a in assertions if isinstance(a, dict)
                            and a.get("subject_id") == pid and a.get("kind") == "task"
                            and (a.get("situation_id", "") == sid or not a.get("situation_id") and len(situations) == 1)
                            and a.get("state") == "CONFIRMADO" and isinstance(a.get("value"), str)]
                personal = person.get("tarefa_ids", person.get("task_ids", []))
                unit["executed_task_ids"] = sorted(set(assigned or [task for task in personal if task in unit["tarefas"]]))
                if pid in situation.get("actor_ids", []) and not unit["executed_task_ids"]:
                    unit["executed_task_ids"] = list(unit["tarefas"])
                unit["task_participation"] = ("ACTOR" if unit["executed_task_ids"] else
                                               "RECIPIENT" if pid in situation.get("recipient_ids", []) else "UNSPECIFIED")
                conflicts = set(unit["recursos_disponiveis"]) & set(unit["recursos_impedidos"])
                if conflicts:
                    self.result["input_issues"].append({"code": "CONFLICTING_RESOURCE_STATE", "ids": sorted(conflicts), "situation_id": sid})
                units.append(unit)
        return units

    def claim(self, knowledge_id, claim_id):
        knowledge = self.index["knowledge"].get(knowledge_id, {})
        claims = knowledge.get("operation_claims", knowledge.get("claims", []))
        matches = [row for row in claims if row.get("id", row.get("claim_id")) == claim_id]
        if len(matches) != 1:
            return None, "MISSING_OR_AMBIGUOUS_CLAIM"
        claim = matches[0]
        if (claim.get("eligibility") != "DOCUMENTED_OPERATIONAL_CLAIM"
                or claim.get("status") != "SUPPORTED_IN_RECORDED_SCOPE"
                or claim.get("foundation_status") != "DOCUMENTED_IN_RECORDED_SCOPE"):
            return None, "CLAIM_FOUNDATION_PENDING_OR_INELIGIBLE"
        support = claim.get("support", [])
        if not support:
            return None, "CLAIM_WITHOUT_LOCALIZED_SUPPORT"
        for item in support:
            source, excerpt = item.get("source_id"), item.get("excerpt_id")
            if (source not in knowledge.get("fonte_ids", []) or excerpt not in knowledge.get("trecho_ids", [])
                    or source not in self.index["sources"] or excerpt not in self.index["excerpts"]
                    or self.index["excerpts"][excerpt].get("fonte_id") != source):
                return None, "CLAIM_SOURCE_EXCERPT_MISMATCH"
        return claim, None

    def scoped_access_assertions(self, unit, matrix, group, group_id):
        """Recheck existing matrix observations; never trust supplied functions."""
        from situated_context import functional_signal_pattern, words
        assertions = {a["id"]: a for a in self.context.get("assertions", [])
            if isinstance(a, dict) and a.get("id") and a.get("kind") == "functional_observation"
            and a.get("subject_id") == unit["participant_id"]
            and a.get("situation_id") == unit["situation_id"]
            and (a.get("state") == "CONFIRMADO"
                 or a.get("state") == "RELATADO" and self.context.get("confirmed") is True)}
        found = {}
        expected_needs = set(group.get("requisito_ids", []))
        for requirement in self.context.get("access_requirements", []):
            if not isinstance(requirement, dict):
                continue
            if (requirement.get("matrix_id") != matrix["id"]
                    or requirement.get("trigger_group_id", "") != group_id
                    or requirement.get("participant_id") != unit["participant_id"]
                    or unit["situation_id"] not in requirement.get("situation_ids", [])
                    or requirement.get("status") != "DERIVADO_DA_BASE_PARA_CONFIRMACAO"
                    or set(requirement.get("requirement_ids", [])) != expected_needs):
                continue
            for assertion_id in requirement.get("assertion_ids", []):
                assertion = assertions.get(assertion_id)
                if assertion is None:
                    continue
                text = words(assertion.get("value", ""))
                for signal in group.get("sinais_relato", matrix.get("sinais_relato", [])):
                    for match in re.finditer(functional_signal_pattern(signal), text):
                        prefix = text[max(0, match.start() - 45):match.start()]
                        negated = re.search(
                            r"\b(?:nao (?:e|eh|sao|esta|estao|tem|tenho|temos|possui|ha|existe|existem)|sem|nenhum|nenhuma)\s*"
                            r"(?:(?:um|uma|dois|duas|tres|quatro|qualquer|nenhum|nenhuma|\d+)\s+)?"
                            r"(?:(?:alunos?|alunas?|estudantes?|pessoas?|usuarios?|usuarias?)\s+)?$", prefix)
                        if not negated:
                            found[assertion_id] = assertion
        return list(found.values())

    def derive_functions(self, unit):
        matched_needs, matched_tasks = set(), set()
        unit["unknown_requirements"] = set(unit["required_explicit"]) - set(self.index["context_elements"])
        for identifier in unit["required_explicit"]:
            if identifier not in self.index["context_elements"]:
                self.result["gaps"].append({"code": "UNKNOWN_REQUIRED_FUNCTION", "type": "KNOWLEDGE_GAP", "id": identifier,
                                           "situation_id": unit["situation_id"], "participant_id": unit["participant_id"]})
        derived = {identifier: {"function_id": identifier, "origin": "EXPLICIT_CONTEXT_REQUIREMENT", "witnesses": [], "claim_ids": []}
                   for identifier in unit["required_explicit"] if identifier in self.index["context_elements"]}
        unit["task_refinements"] = []
        for binding in getattr(self.composer, "bindings", {}).get("situated_task_bindings", []):
            required_tasks = set(binding.get("task_ids_all", []))
            if not required_tasks or not required_tasks <= set(unit["executed_task_ids"]):
                continue
            task = self.composer._resolve(binding.get("rdf_task_id"), V2.Task)
            primary = binding.get("primary_contribution_ids", [])
            if task is None or not primary or any(self.composer._text(V2[c], V2.status) != "PRIMARY_CHECKED" for c in primary):
                self.result["claim_audit"].append({"id": binding.get("id"), "reason": "TASK_REFINEMENT_FOUNDATION_NOT_RECORDED", "use": "AUDIT_ONLY"})
                continue
            facts = binding.get("required_facts", [])
            if not facts or any(unit["facts"].get(f["id"]) is False for f in facts):
                continue
            refinement = {**binding, "state": "PASS" if all(unit["facts"].get(f["id"]) is True for f in facts) else "PENDING",
                          "function_ids": [str(f) for f in self.composer._values(task, V2.requiresFunction)]}
            unit["task_refinements"].append(refinement)
            unit["tarefas"].append(str(task))
            matched_tasks.update(required_tasks)
        for task in unit["tarefas"]:
            if (unit["task_participation"] == "RECIPIENT" or
                    len(unit["participant_ids"]) > 1 and task not in unit["executed_task_ids"]
                    and not any(r["rdf_task_id"] == task for r in unit["task_refinements"])):
                continue
            node = self.composer._resolve(task, V2.Task)
            if node is None:
                continue
            if self.composer._values(node, V2.requiresFunction):
                matched_tasks.add(str(node))
            for function in self.composer._values(node, V2.requiresFunction):
                if (function, RDF.type, V2.Function) not in self.composer.graph:
                    continue
                refinement = next((r for r in unit["task_refinements"] if r["rdf_task_id"] == str(node)), None)
                derived[str(function)] = {"function_id": str(function), "origin": "REGISTERED_TASK_REFINEMENT" if refinement else "REGISTERED_TASK_FUNCTION_REQUIREMENT",
                    "witnesses": [{"task_id": str(node), "predicate": str(V2.requiresFunction), "function_id": str(function),
                                   "task_label": self.label(str(node)), "function_label": self.label(str(function)),
                                   "provenance": "EXISTING_RDF_PILOT_TASK_CONTRACT_NOT_NARRATIVE_INFERENCE",
                                   "refinement": copy.deepcopy(refinement)}], "claim_ids": [],
                    "requirement_state": refinement["state"] if refinement else "PASS"}
        claims_by_id = {claim.get("id", claim.get("claim_id")): (kid, claim)
                        for kid, knowledge in self.index["knowledge"].items()
                        for claim in knowledge.get("operation_claims", knowledge.get("claims", []))}
        # The existing functional matrix binds a precise observation/need to a
        # design requirement. The much broader K applicability list is not a
        # licence to import every function mentioned by that knowledge.
        for matrix in self.base.get("functional_matrix", []):
            contract = matrix.get("inference_contract", {})
            groups = contract.get("trigger_groups") or [matrix]
            for group_index, group in enumerate(groups, 1):
                group_id = (group.get("id", f"{matrix['id']}-G{group_index}")
                            if contract.get("trigger_groups") else "")
                observation_assertions = self.scoped_access_assertions(unit, matrix, group, group_id)
                observed_needs = set(unit["necessidades"]) & set(group.get("requisito_ids", []))
                if observation_assertions:
                    observed_needs.update(group.get("requisito_ids", []))
                observed_traits = set(unit["caracteristicas_pessoa"]) & set(group.get("caracteristica_ids", matrix.get("caracteristica_ids", [])))
                if not observed_needs and not observed_traits:
                    continue
                claim_ids = group.get("claim_ids", contract.get("claim_ids", []))
                admitted = []
                for cid in claim_ids:
                    kid, raw = claims_by_id.get(cid, (None, {}))
                    claim, reason = self.claim(kid, cid)
                    if reason or contract.get("eligibility") != "DOCUMENTED_OPERATIONAL_CLAIM":
                        self.result["claim_audit"].append({"knowledge_id": kid, "claim_id": cid,
                            "reason": reason or "INFERENCE_FOUNDATION_PENDING", "use": "AUDIT_ONLY",
                            "situation_id": unit["situation_id"], "participant_id": unit["participant_id"]})
                    else:
                        admitted.append(claim)
                supported = {function for claim in admitted for function in claim.get("scope", {}).get("function_ids", claim.get("function_ids", []))}
                functions = set(group.get("funcao_ids", matrix.get("funcao_ids", []))) or supported
                if functions & supported:
                    matched_needs.update(observed_needs)
                for function in sorted(functions & supported):
                    if function not in self.index["context_elements"]:
                        continue
                    row = derived.setdefault(function, {"function_id": function, "origin": "DOCUMENTED_FUNCTIONAL_WITNESS", "witnesses": [], "claim_ids": []})
                    relevant_assertions = [a for a in self.context.get("assertions", []) if a.get("id") in unit["assertion_ids"]
                                           and (a.get("kind") == "need" and a.get("value") in observed_needs
                                                or a.get("kind") == "characteristic" and a.get("value") in observed_traits)]
                    relevant_assertions = list({a["id"]: a for a in relevant_assertions + observation_assertions}.values())
                    row["witnesses"].append({"matrix_id": matrix["id"], "need_ids": sorted(observed_needs),
                        "trigger_group_id": group_id, "observation_bridge": bool(observation_assertions),
                        "matrix_label": matrix.get("rotulo", matrix.get("label", matrix["id"])),
                        "needs": [self.record(x) for x in sorted(observed_needs)],
                        "characteristic_ids": sorted(observed_traits), "characteristics": [self.record(x) for x in sorted(observed_traits)],
                        "assertion_ids": [a["id"] for a in relevant_assertions],
                        "assertions": [{"id": a["id"], "kind": a["kind"], "value": a["value"], "label": self.label(a["value"]),
                                        "source_text": a.get("source_text", ""), "state": a.get("state"),
                                        "subject_id": a.get("subject_id"), "situation_id": a.get("situation_id")}
                                       for a in relevant_assertions]})
                    row["claim_ids"].extend(claim["id"] for claim in admitted if function in claim.get("scope", {}).get("function_ids", claim.get("function_ids", [])))
        for identifier, requirement in sorted(derived.items()):
            registered_task = requirement["origin"] in {"REGISTERED_TASK_REFINEMENT", "REGISTERED_TASK_FUNCTION_REQUIREMENT"}
            requirement["task_ids"] = (sorted({w["task_id"] for w in requirement["witnesses"] if w.get("task_id")})
                                       if registered_task else list(unit["tarefas"]))
            requirement["task_scope_kind"] = ("REGISTERED_TASK_REQUIREMENT" if registered_task
                                                else "CONTEXTUAL_TASK_SCOPE_NOT_CAUSAL_SUPPORT")
            requirement.update(situation_id=unit["situation_id"], participant_id=unit["participant_id"],
                               situation_label=unit["situation_label"], participant_label=unit["participant_label"],
                               id="occurrence-" + _json_hash([unit["situation_id"], unit["participant_id"], identifier])[:16])
            row = self.check(unit, requirement["id"], "REQUIRED_FUNCTION_BEFORE_SELECTION", requirement.get("requirement_state", "PASS"),
                             "exigência explícita ou testemunho funcional com alegação localizada", requirement,
                             "A função foi requerida antes de consultar os componentes, independentemente do nome do caso.")
            requirement["check_ids"] = [row["id"]]
            self.result["required_functions"].append({**self.record(identifier), **requirement})
        unit["requirements"] = derived
        actions = set(unit["executed_task_ids"])
        if not actions and unit["task_participation"] != "RECIPIENT" and len(unit["participant_ids"]) <= 1:
            actions = set(unit["tarefas"])
        unmatched_tasks = actions - matched_tasks
        # A functional witness may support an unknown single task, but it does
        # not establish coverage of additional actions merely listed beside it.
        task_gaps = unmatched_tasks if matched_tasks or len(actions) > 1 else set()
        need_gaps = set(unit["necessidades"]) - matched_needs
        unit["scope_gaps"] = []
        for code, identifiers, explanation in (
            ("UNMAPPED_TASK", task_gaps, "Esta ação foi informada, mas não possui um vínculo documentado com as funções compostas. O apoio disponível não cobre automaticamente essa ação."),
            ("UNMAPPED_NEED", need_gaps, "Esta necessidade foi informada, mas não possui uma derivação funcional autorizada nesta execução. Não é falta de resposta da pessoa."),
        ):
            for identifier in sorted(identifiers):
                gap = {"code": code, "type": "FUNCTION_GAP", "id": identifier, "label": self.label(identifier),
                       "situation_id": unit["situation_id"], "participant_id": unit["participant_id"], "explanation": explanation}
                unit["scope_gaps"].append(gap)
                self.result["gaps"].append(gap)
        unit["coverage_scope"] = "REGISTERED_TASK_FUNCTIONS" if actions and not unmatched_tasks else "DECLARED_FUNCTIONS_ONLY"
        return derived

    def groundings(self, supports, unit, target):
        admitted, rejected = [], []
        for support in supports or []:
            if support.get("rdf_application_id"):
                node = URIRef(support["rdf_application_id"])
                local_checks = _Checks()
                grounded = self.composer._grounding(node, local_checks, "situated_rdf_grounding")
                mapped = [self.check(unit, row["subject"], row["kind"], row["state"], row["expected"], row["observed"], row["explanation"]) for row in local_checks.rows]
                if (not grounded or any(row["state"] == "FAIL" for row in mapped)
                        or grounded["knowledge"].get("epistemic_status") != "DESIGN_SYNTHESIS_NOT_EMPIRICAL"):
                    rejected.append({**support, "reason": "RDF_EXACT_GROUNDING_FAILED", "use": "AUDIT_ONLY", "check_ids": [x["id"] for x in mapped]})
                    continue
                capability = next(iter(self.composer.graph.objects(node, V2.capability)), None)
                functions = ([str(x) for x in self.composer._values(capability, V2.provides)] if capability else
                             [str(x) for p in (V2.fromFunction, V2.toFunction) for x in self.composer._values(node, p)])
                grounded.update(claim_id=str(node), claim={"id": str(node), "statement": grounded["knowledge"]["label"],
                    "function_ids": functions, "foundation_status": "PRIMARY_CONTRIBUTIONS_CHECKED_FOR_PILOT",
                    "operationalization_status": "PROPOSED_NOT_EVALUATED"}, check_ids=[x["id"] for x in mapped],
                    justification=self.composer._text(node, V2.justification) or self.composer._text(node, V2.explanation),
                    operationalization_status="PROPOSED_NOT_EVALUATED", application_kind="EXISTING_RDF_CURATED_APPLICATION")
                grounded["sources"] = [{**c["source"], "excerpt_id": c["excerpt"]["id"], "locator": c["locator"],
                                        "review_status": c["status"], "support_scope": c["statement"]}
                                       for c in grounded["articulation"]["contributions"] if c["status"] == "PRIMARY_CHECKED"]
                grounded["construction"] = grounded["articulation"]
                admitted.append(grounded)
                continue
            kid, cid = support.get("knowledge_id"), support.get("claim_id")
            claim, reason = self.claim(kid, cid)
            criterion_id, origins = support.get("criterion_id"), support.get("origin_ids", [])
            has_criterion = criterion_id is not None
            if not reason and (not support.get("justification") or has_criterion and (criterion_id not in self.index["criteria"] or not origins)):
                reason = "MISSING_EXACT_CRITERION_APPLICATION"
            if not reason and not has_criterion and origins:
                reason = "ORIGINS_WITHOUT_CRITERION"
            if not reason and any(self.index["criterion_origins"].get(oid, {}).get("criterio_id") != criterion_id for oid in origins):
                reason = "CRITERION_ORIGIN_MISMATCH"
            pair_review = support.get("semantic_pair_review", {})
            if not reason and pair_review:
                if pair_review.get("status") != "CONFERIDO_NO_REGISTRO":
                    reason = "SEMANTIC_APPLICATION_REVIEW_PENDING"
                elif pair_review.get("scope") == "CONTEXTUAL_CONTRIBUTION_ONLY" and has_criterion:
                    reason = "CONTEXTUAL_CLAIM_CANNOT_ASSERT_CRITERION_APPLICATION"
                elif pair_review.get("scope") == "DIRECT_NORMATIVE_CLAUSE":
                    claim_excerpts = set(claim.get("excerpt_ids", [])) or {item["excerpt_id"] for item in claim["support"]}
                    origin_excerpts = {self.index["criterion_origins"].get(oid, {}).get("trecho_id") for oid in origins}
                    if not has_criterion or not origin_excerpts or not origin_excerpts <= claim_excerpts:
                        reason = "DIRECT_NORMATIVE_CLAIM_ORIGIN_MISMATCH"
            claim_scope = (claim or {}).get("scope", {})
            if not reason and claim_scope.get("task_ids") and not self.intersects(unit["tarefas"], claim_scope["task_ids"]):
                if not claim_scope.get("allow_new_task_with_functional_witness"):
                    reason = "CLAIM_OUTSIDE_TRANSFER_SCOPE"
            checked = self.check(unit, target + ":" + str(cid), "EXACT_CLAIM_GROUNDING", "FAIL" if reason else "PASS",
                                 "alegação localizada elegível e aplicação exata de critério", {**support, "reason": reason},
                                 "Pendência documental exclui o uso; não é convertida em pergunta sobre capacidade pessoal.")
            if reason:
                rejected.append({**support, "reason": reason, "check_ids": [checked["id"]], "use": "AUDIT_ONLY"})
                continue
            knowledge = self.index["knowledge"][kid]
            sources = [{"id": item["source_id"], "label": self.index["sources"][item["source_id"]].get("titulo", item["source_id"]),
                        "excerpt_id": item["excerpt_id"], "locator": self.index["excerpts"][item["excerpt_id"]].get("localizacao_publica", ""),
                        "url": self.index["excerpts"][item["excerpt_id"]].get("document_url") or self.index["sources"][item["source_id"]].get("url") or "",
                        "source_sha256": _json_hash(self.index["sources"][item["source_id"]]),
                        "excerpt_sha256": _json_hash(self.index["excerpts"][item["excerpt_id"]]),
                        "review_status": item.get("review_status"), "support_scope": item.get("support_scope")}
                       for item in claim["support"]]
            contributions = []
            histories = []
            for contribution_id in claim.get("contribution_ids", []):
                contribution = self.index["contributions"].get(contribution_id, {})
                if contribution.get("knowledge_id") != kid or contribution.get("excerpt_id") not in {item["excerpt_id"] for item in claim["support"]}:
                    continue
                source = self.index["excerpts"][contribution["excerpt_id"]].get("fonte_id")
                contributions.append({"id": contribution_id, "statement": contribution.get("statement", ""),
                                      "role": contribution.get("contribution_role"), "excerpt_id": contribution["excerpt_id"], "source_id": source,
                                      "source": {"id": source, "label": self.index["sources"].get(source, {}).get("titulo", source),
                                                 "url": self.index["excerpts"][contribution["excerpt_id"]].get("document_url") or self.index["sources"].get(source, {}).get("url", "")},
                                      "excerpt": {"id": contribution["excerpt_id"], "locator": self.index["excerpts"][contribution["excerpt_id"]].get("localizacao_publica", "")},
                                      "status": contribution.get("verification_status"), "justification": contribution.get("justification"),
                                      "interpretation": "DOCUMENTARY_HISTORY_SCOPED_TO_CLAIM"})
                art = self.index["articulations"].get(contribution.get("articulation_id"), {})
                if art:
                    histories.append({"id": art["id"], "operation": art.get("operation_explanation", art.get("tipo_articulacao", "")),
                                      "added_understanding": art.get("added_understanding", ""), "limit": art.get("limite", ""),
                                      "interpretation": "DOCUMENTARY_HISTORY_NOT_FULL_CLAIM_AUTHORIZATION"})
            construction = {"id": target + ":construction:" + cid, "operation": support["justification"],
                            "added_understanding": claim.get("statement", claim.get("text", "")), "contributions": contributions,
                            "documentary_articulations": histories, "limits": claim.get("limits", []),
                            "interpretation": "EXECUTION_EXPANSION_OF_DOCUMENTED_SCOPED_CLAIM_NOT_NEW_RESEARCH_SYNTHESIS"}
            admitted.append({"id": target + ":" + cid + (":" + criterion_id if criterion_id else ""),
                             "knowledge": {"id": kid, "label": claim.get("statement", claim.get("text", kid)), "documentary_enunciado": knowledge.get("enunciado", "")},
                             "claim_id": cid, "claim": claim, "criterion": {"id": criterion_id, "label": self.index["criteria"][criterion_id].get("enunciado", criterion_id)} if has_criterion else None,
                             "origin_ids": origins, "sources": sources, "justification": support["justification"],
                             "application_kind": "EXACT_CRITERION_APPLICATION" if has_criterion else "DOCUMENTED_KNOWLEDGE_CONTRIBUTION_WITHOUT_CRITERION_ASSERTION",
                             "construction": construction, "articulation": construction,
                             "semantic_pair_review": copy.deepcopy(pair_review),
                             "epistemic_status": claim.get("epistemic_status"), "operationalization_status": "PROPOSED_NOT_EVALUATED",
                             "check_ids": [checked["id"]]})
        self.result["claim_audit"].extend(rejected)
        return admitted, rejected

    def condition(self, unit, target, identifier, kind, value, label):
        state = "PASS" if value is True else "FAIL" if value is False else "PENDING"
        row = self.check(unit, target, "REQUIRES_" + kind.upper(), state, {"id": identifier, "value": True}, value, label)
        if value is not True:
            self.conditions.append({"id": identifier, "label": label, "kind": kind, "value": value, "state": state,
                                    "participant_id": unit["participant_id"], "situation_id": unit["situation_id"],
                                    "required_by": [target], "check_ids": [row["id"]]})
        return row

    def resource_value(self, unit, identifier):
        identifier = self.rdf_alias(identifier, V2.Resource)
        if identifier in unit["recursos_impedidos"]:
            if unit["facts"].get(identifier) is True:
                self.check(unit, identifier, "RESOURCE_STATE_CONSISTENCY", "FAIL", "um recurso impedido não pode ser confirmado como disponível sem corrigir o conflito",
                           {"explicitly_blocked": True, "availability_fact": True},
                           "As declarações situadas são contraditórias; a operação permanece bloqueada, não disponível.")
            return False
        if identifier in unit["facts"]:
            return unit["facts"][identifier]
        if identifier in unit["recursos_disponiveis"]:
            return True
        return unit["facts"].get(identifier)

    def operation(self, component, unit):
        contract = component.get("operation_contract", {})
        identifier = contract.get("id", component["id"])
        functions = contract.get("function_ids", [])
        if not set(functions) & set(unit["requirements"]):
            return None
        roles = contract.get("role_requirements", {})
        subject_roles = roles.get("subject_role_ids", [])
        person_role = unit["participant"].get("papel_id", unit["participant"].get("role_id"))
        if subject_roles and person_role and person_role not in subject_roles:
            return None
        start = len(self.checks.history)
        scope = contract.get("transfer_scope", {})
        scoped_tasks = scope.get("task_ids", [])
        transfer_ok = bool(set(functions) & set(unit["requirements"])) and scope.get("allow_new_task_with_functional_witness") is True
        task_ok = self.intersects(unit["tarefas"], scoped_tasks) if scoped_tasks else transfer_ok
        self.check(unit, identifier, "OPERATION_TASK_SCOPE", "PASS" if task_ok else "FAIL", scoped_tasks, unit["tarefas"],
                   "Transferência usa função previamente requerida e o escopo publicado; não reconhece assunto pelo nome.")
        for refinement in unit.get("task_refinements", []):
            if set(functions) & set(refinement["function_ids"]):
                for fact in refinement["required_facts"]:
                    self.condition(unit, identifier, fact["id"], "fact", unit["facts"].get(fact["id"]), fact["label"])
        if scope.get("requires_actor"):
            actor_value = True if unit["task_participation"] == "ACTOR" else False if unit["task_participation"] == "RECIPIENT" else unit["facts"].get(identifier + ":actor")
            self.condition(unit, identifier, identifier + ":actor", "fact", actor_value,
                           "Esta pessoa realiza a ação indicada, ou acompanha a ação de outra pessoa?")
        supports, rejected = self.groundings(contract.get("claim_support", []), unit, identifier)
        self.check(unit, identifier, "OPERATION_FOUNDATION", "PASS" if any(support["criterion"] for support in supports) else "FAIL", "ao menos uma aplicação exata de critério com alegação elegível", [x["claim_id"] for x in supports],
                   "Uma operação sem fundamento utilizável fica fora das recomendações.")
        supported_functions = {function for support in supports for function in support["claim"].get("scope", {}).get("function_ids", support["claim"].get("function_ids", []))}
        self.check(unit, identifier, "OPERATION_FUNCTION_SUPPORT", "PASS" if set(functions) <= supported_functions else "FAIL",
                   functions, sorted(supported_functions), "O fundamento deve sustentar as funções declaradas da operação, não somente um tema próximo.")
        if not unit["tarefas"]:
            self.condition(unit, identifier, "task_context", "fact", None, "Qual ação esta pessoa precisa realizar nesta situação?")
        if subject_roles:
            self.condition(unit, identifier, identifier + ":subject_role", "fact", True if person_role in subject_roles else None,
                           "Confirmar a quem se aplica esta operação e seu papel na tarefa.")
        participants = [self.people[pid] for pid in unit["participant_ids"] if pid in self.people]
        for role in roles.get("all", []):
            present = any(p.get("papel_id", p.get("role_id")) == role for p in participants)
            self.condition(unit, identifier, role, "fact", True if present else None, "Confirmar responsável: " + self.label(role))
        requirements = contract.get("resource_requirements", {})
        for resource in requirements.get("all", []):
            self.condition(unit, identifier, resource, "resource", self.resource_value(unit, resource), self.label(resource))
        for group in requirements.get("any", []):
            values = [self.resource_value(unit, resource) for resource in group]
            value = True if True in values else False if values and all(v is False for v in values) else None
            group_id = "ANY:" + "|".join(group)
            if group_id in unit["facts"]:
                value = unit["facts"].get(group_id)
            self.condition(unit, identifier, group_id, "resource", value,
                           "Ao menos um recurso: " + ", ".join(self.label(x) for x in group))
        operator_role = requirements.get("operator_role_id")
        if operator_role:
            operators = [p for p in participants if p.get("papel_id", p.get("role_id")) == operator_role]
            operated = {self.rdf_alias(resource, V2.Resource) for p in operators for resource in p.get("recurso_operado_ids", [])}
            necessary = requirements.get("all", [])
            operation_ok = all(self.rdf_alias(resource, V2.Resource) in operated for resource in necessary) and all(any(self.rdf_alias(resource, V2.Resource) in operated for resource in group) for group in requirements.get("any", []))
            explicit = unit["facts"].get(identifier + ":operability")
            value = explicit if identifier + ":operability" in unit["facts"] else True if operation_ok and operators else None
            self.condition(unit, identifier, identifier + ":operability", "fact", value,
                           "Confirmar que o responsável consegue operar os recursos nesta situação.")
        elif requirements.get("capability_check_required", True) and (requirements.get("all") or requirements.get("any")):
            operated = {self.rdf_alias(resource, V2.Resource) for resource in unit["participant"].get("recurso_operado_ids", [])}
            operation_ok = all(self.rdf_alias(resource, V2.Resource) in operated for resource in requirements.get("all", [])) and all(any(self.rdf_alias(resource, V2.Resource) in operated for resource in group) for group in requirements.get("any", []))
            value = unit["facts"].get(identifier + ":operability") if identifier + ":operability" in unit["facts"] else True if operation_ok else None
            self.condition(unit, identifier, identifier + ":operability", "fact", value,
                           "A pessoa responsável consegue usar os recursos necessários nesta situação?")
        for field, identifiers in contract.get("requires_all", {}).items():
            if field == "tarefas" or field not in unit:
                continue
            value = True if self.intersects(unit[field], identifiers) else unit["facts"].get(identifier + ":" + field)
            self.condition(unit, identifier, identifier + ":" + field, "fact", value,
                           "Confirmar " + field.replace("_", " ") + ": " + ", ".join(self.label(x) for x in identifiers))
        for fact in contract.get("requires_facts", []):
            self.condition(unit, identifier, fact["id"], "fact", unit["facts"].get(fact["id"]), fact["label"])
        if contract.get("conditions"):
            condition_id = "condition-" + _json_hash(contract["conditions"])[:16]
            self.condition(unit, identifier, condition_id, "fact", unit["facts"].get(condition_id, unit["facts"].get(identifier + ":conditions")),
                           "A informação essencial e as condições de percepção, ação e mediação foram conferidas com esta pessoa?")
        if scope.get("requires_existing_representation"):
            self.condition(unit, identifier, identifier + ":input_available", "fact", unit["facts"].get(identifier + ":input_available"),
                           "A representação de entrada já está disponível ou foi escolhida para esta tarefa?")
        typed = (bool(contract.get("input_requirements")) and bool(contract.get("output_spec"))
                 and all(isinstance(item, dict) and item.get("representation_id") and item.get("meaning_unit")
                         for item in contract.get("input_requirements", []) + contract.get("output_spec", [])))
        self.check(unit, identifier, "OPERATION_REPRESENTATIONS", "PASS" if typed else "FAIL", "entradas e saídas qualificadas por unidade informacional", contract.get("representation_ids"),
                   "As descrições de entrada e saída não constituem comprovação da preservação efetiva do conteúdo.")
        self.check(unit, identifier, "SCOPED_ACTION_PRESENT", "PASS" if isinstance(contract.get("action"), str) and contract["action"].strip() else "FAIL",
                   "ação delimitada no contrato curado", contract.get("action"), "O texto histórico do padrão não substitui uma ação autorizada.")
        checks = self.checks.history[start:]
        state = _worst([row["state"] for row in checks if row["kind"] != "EXACT_CLAIM_GROUNDING"])
        witness_checks = [check for f in functions if f in unit["requirements"] for check in unit["requirements"][f]["check_ids"]]
        return {"id": identifier, "component_id": component["id"], "label": component.get("label", identifier),
                "state": state, "function": {"id": functions[0] if functions else "", "label": component.get("function", "")},
                "functions": [self.record(f) for f in functions], "function_ids": functions,
                "action": contract.get("action", ""), "instructions": [contract.get("action", "")],
                "mode": self.record(component.get("mode_id", "")), "modes": [self.record(x) for x in contract.get("selected_representation_ids", [])],
                "representation_options": [self.record(x) for x in contract.get("representation_ids", [])],
                "representation_selection_status": "NOT_SELECTED_BY_CONTEXT_UNION",
                "resources": [self.record(x) for x in sorted(set(requirements.get("all", []) + [x for group in requirements.get("any", []) for x in group]))],
                "conditions": contract.get("conditions", []), "monitoring": component.get("monitoring", ""),
                "limits": contract.get("limits", []), "limitation": component.get("limit", ""),
                "groundings": supports, "rejected_groundings": rejected,
                "function_derivation": [copy.deepcopy(unit["requirements"][f]) for f in functions if f in unit["requirements"]],
                "input_requirements": contract.get("input_requirements", []), "output_spec": contract.get("output_spec", []),
                "relation_contracts": contract.get("relations", []),
                "check_ids": witness_checks + [row["id"] for row in checks if row["kind"] != "EXACT_CLAIM_GROUNDING" or row["state"] == "PASS"],
                "participant_id": unit["participant_id"], "situation_id": unit["situation_id"],
                "participant_label": unit["participant_label"], "situation_label": unit["situation_label"],
                "task_participation": unit["task_participation"], "executed_task_ids": unit["executed_task_ids"],
                "epistemic_status": "PROPOSED_NOT_EVALUATED"}

    def relation(self, rule, left, right, unit, internal=False):
        identifier = rule.get("id", "unidentified-relation")
        kind = {"COMPLEMENTARY": "COMPLEMENTARITY", "REDUNDANT": "REDUNDANCY"}.get(rule.get("kind"), rule.get("kind"))
        start = len(self.checks.history)
        meaning = rule.get("meaning_unit")
        from_modes = set(rule.get("from_representation_ids", []))
        to_modes = set(rule.get("to_representation_ids", []))
        left_specs = left["input_requirements"] + left["output_spec"] if internal else left["output_spec"]
        right_specs = right["input_requirements"] + right["output_spec"] if internal else right["input_requirements"]
        available_left = {item["representation_id"] for item in left_specs if item.get("meaning_unit") == meaning}
        available_right = {item["representation_id"] for item in right_specs if item.get("meaning_unit") == meaning}
        types_ok = bool(meaning and from_modes and to_modes and from_modes <= available_left and to_modes <= available_right)
        functions_ok = bool(set(rule.get("from_function_ids", [])) & set(left["function_ids"]) and
                            set(rule.get("to_function_ids", [])) & set(right["function_ids"]))
        semantic_ok = kind in self.RELATIONS and bool(rule.get("preserves")) and bool(rule.get("sufficiency"))
        if kind in {"ALTERNATIVE", "REDUNDANCY", "COMPLEMENTARITY"}:
            semantic_ok = semantic_ok and len(from_modes | to_modes) >= 2
        if kind in {"SEQUENTIAL", "SEQUENTIAL_REVIEW"} and not internal:
            semantic_ok = semantic_ok and bool(from_modes & to_modes)
        self.check(unit, identifier, "RELATION_SEMANTICS", "PASS" if semantic_ok and types_ok and functions_ok else "FAIL",
                   "funções, representações, unidade informacional, preservação e suficiência explícitas",
                   {"kind": kind, "meaning_unit": meaning, "preserves": rule.get("preserves"), "sufficiency": rule.get("sufficiency"),
                    "from_operation": left["id"], "to_operation": right["id"],
                    "from_participant": left["participant_id"], "to_participant": right["participant_id"],
                    "available_from_representations": sorted(available_left), "available_to_representations": sorted(available_right),
                    "types_match": types_ok, "functions_match": functions_ok},
                   "Coocorrência de modalidades não autoriza relação funcional; a classificação é uma declaração curada de escopo delimitado.")
        supports, rejected = self.groundings(rule.get("claim_support", []), unit, identifier)
        self.check(unit, identifier, "RELATION_FOUNDATION", "PASS" if supports else "FAIL", "fundamento específico da relação", [x["claim_id"] for x in supports],
                   "A existência das capacidades não substitui a justificativa de sua combinação.")
        supported_functions = {function for support in supports for function in support["claim"].get("scope", {}).get("function_ids", support["claim"].get("function_ids", []))}
        required_functions = set(rule.get("from_function_ids", [])) | set(rule.get("to_function_ids", []))
        self.check(unit, identifier, "RELATION_FUNCTION_SUPPORT", "PASS" if required_functions and required_functions <= supported_functions else "FAIL",
                   sorted(required_functions), sorted(supported_functions),
                   "Alegações sobre outra função não autorizam esta ligação, ainda que tenham fonte e critério válidos.")
        sufficiency = rule.get("sufficiency")
        if sufficiency == "REQUIRES_SITUATED_CONFIRMATION":
            questions = {
                "COMPLEMENTARITY": "Cada apresentação oferece uma parte necessária para entender ou realizar a mesma tarefa?",
                "REDUNDANCY": "Cada apresentação comunica sozinha a mesma informação essencial, conferida neste caso?",
                "ALTERNATIVE": "A alternativa permite acessar a mesma informação essencial e realizar a mesma ação neste caso?",
                "SEQUENTIAL": "A informação produzida na primeira etapa fica disponível e utilizável na etapa seguinte?",
                "SEQUENTIAL_REVIEW": "A pessoa consegue conferir e corrigir a mesma informação produzida na etapa anterior?"}
            self.condition(unit, identifier, identifier + ":sufficiency", "fact", unit["facts"].get(identifier + ":sufficiency"), questions.get(kind, "A relação informada foi conferida nesta situação?"))
        elif kind == "COMPLEMENTARITY" and sufficiency not in {"JOINT_REQUIRED", "JOINTLY_SUFFICIENT"}:
            self.check(unit, identifier, "JOINT_SUFFICIENCY", "FAIL", "parcelas necessárias em conjunto", sufficiency,
                       "Complementaridade exige contribuição conjunta; modalidades intercambiáveis não bastam.")
        elif kind in {"ALTERNATIVE", "REDUNDANCY"} and sufficiency not in {"EACH_SUFFICIENT", "INDIVIDUALLY_SUFFICIENT"}:
            self.check(unit, identifier, "INDIVIDUAL_SUFFICIENCY", "FAIL", "suficiência funcional de cada alternativa", sufficiency,
                       "Mesmo tipo de saída não comprova equivalência individual, esforço ou compreensão.")
        temporal = rule.get("temporal")
        if temporal in {"SIMULTANEOUS", "WITHIN_WINDOW", "SYNCHRONIZED", "COORDINATION_MUST_BE_SPECIFIED_IN_CONTEXT"}:
            self.condition(unit, identifier, identifier + ":temporal", "fact", unit["facts"].get(identifier + ":temporal"),
                           "É possível perceber e usar essas apresentações no tempo necessário, sem perder informação?")
        if left["participant_id"] != right["participant_id"]:
            self.condition(unit, identifier, identifier + ":handoff", "fact", unit["facts"].get(identifier + ":handoff"),
                           "A pessoa que recebe a informação consegue percebê-la e dar continuidade à ação?")
        for fact in rule.get("requires_facts", []):
            self.condition(unit, identifier, fact["id"], "fact", unit["facts"].get(fact["id"]), fact["label"])
        rows = self.checks.history[start:]
        return {"id": identifier, "kind": kind, "state": _worst([row["state"] for row in rows if row["kind"] != "EXACT_CLAIM_GROUNDING"]),
                "from_capability": left["id"], "to_capability": right["id"], "internal_to_operation": internal,
                "meaning_unit": meaning, "preserves": rule.get("preserves"), "sufficiency": sufficiency, "temporal": temporal,
                "explanation": rule.get("explanation") or str(rule.get("preserves", "")),
                "grounding": supports[0] if supports else None, "groundings": supports, "rejected_groundings": rejected,
                "function_derivation": {"from": left.get("function_derivation", []), "to": right.get("function_derivation", [])},
                "check_ids": [row["id"] for row in rows if row["kind"] != "EXACT_CLAIM_GROUNDING" or row["state"] == "PASS"],
                "participant_id": unit["participant_id"], "situation_id": unit["situation_id"]}

    def proposal(self, unit, steps, relations, covered, complete):
        state = _worst([step["state"] for step in steps] + [relation["state"] for relation in relations])
        checks = sorted({cid for item in list(steps) + list(relations) for cid in item["check_ids"]})
        signature = [unit["situation_id"], unit["participant_id"], [step["id"] for step in steps], [row["id"] for row in relations]]
        return {"id": "proposal-" + _json_hash(signature)[:20], "state": state, "steps": list(steps), "relations": list(relations),
                "participant_id": unit["participant_id"], "situation_id": unit["situation_id"],
                "participant_label": unit["participant_label"], "situation_label": unit["situation_label"],
                "covered_functions": [self.record(f) for f in sorted(covered)],
                "missing_functions": [self.record(f) for f in sorted((set(unit["requirements"]) - covered) | unit["unknown_requirements"])],
                "covers_all_required_functions": complete, "conditions_satisfied": state == "PASS",
                "coverage_scope": unit["coverage_scope"], "scope_gaps": copy.deepcopy(unit["scope_gaps"]),
                "ready_for_functional_scope": complete and state == "PASS" and self.context.get("confirmed") is True,
                "ready_for_whole_task": complete and state == "PASS" and self.context.get("confirmed") is True
                                        and unit["coverage_scope"] == "REGISTERED_TASK_FUNCTIONS",
                "epistemic_status": "PROPOSED_NOT_EVALUATED", "check_ids": checks,
                "explanation": {"actions": [step["action"] for step in steps], "why_combine": [row["explanation"] for row in relations],
                                "text": "\n".join(step["action"] for step in steps),
                                "limitations": list(dict.fromkeys(x for step in steps for x in step["limits"]))},
                "limits": ["A relação verifica obrigações declaradas; não comprova preservação semântica do conteúdo real.",
                           "Esta proposta se aplica somente à pessoa e à situação identificadas."]}

    def compose_unit(self, unit):
        required = set(unit["requirements"])
        if not required:
            self.result["gaps"].append({"code": "NO_DOCUMENTED_FUNCTION_REQUIREMENT", "type": "FUNCTION_GAP" if unit["necessidades"] or unit["tarefas"] else "CONTEXT_GAP",
                                        "situation_id": unit["situation_id"], "participant_id": unit["participant_id"]})
            return {"situation_id": unit["situation_id"], "participant_id": unit["participant_id"], "status": "INSUFFICIENT", "choices": [], "pending_candidates": [], "partial_segments": []}
        candidates, internal = [], {}
        for component in sorted(self.base.get("decision_components", []) + self.rdf_components, key=lambda row: row["id"]):
            if not component.get("active_in_rc4", component.get("active_in_rc3")) or not component.get("operation_contract"):
                continue
            operation = self.operation(component, unit)
            if operation is None:
                continue
            relations = [self.relation(rule, operation, operation, unit, internal=True) for rule in operation["relation_contracts"]
                         if rule.get("scope", "WITHIN_OPERATION") in {"WITHIN_OPERATION", "BOTH"}]
            self.result["relation_evaluations"].extend(relations)
            operation["state"] = _worst([operation["state"]] + [row["state"] for row in relations])
            operation["check_ids"] = sorted(set(operation["check_ids"] + [cid for row in relations for cid in row["check_ids"]]))
            internal[operation["id"]] = relations
            self.result["capability_evaluations"].append(operation)
            if operation["state"] == "FAIL":
                self.result["exclusions"].append({"kind": "operation", "id": operation["id"], "participant_id": unit["participant_id"],
                                                  "situation_id": unit["situation_id"], "reason": "CONDITION_OR_FOUNDATION_FAILED", "check_ids": operation["check_ids"]})
            else:
                candidates.append(operation)
        for function in sorted(required):
            available = [row["id"] for row in candidates if function in row["function_ids"] and row["state"] == "PASS"]
            pending = [row["id"] for row in candidates if function in row["function_ids"] and row["state"] == "PENDING"]
            coverage = {"function": self.record(function), "participant_id": unit["participant_id"], "situation_id": unit["situation_id"],
                        "participant_label": unit["participant_label"], "situation_label": unit["situation_label"],
                        "function_derivation": copy.deepcopy(unit["requirements"][function]),
                        "available_capabilities": available, "conditional_capabilities": pending,
                        "state": "CAPABILITY_AVAILABLE" if available else "CONDITIONAL_CAPABILITY" if pending else "NO_AVAILABLE_CAPABILITY"}
            self.result["function_coverage"].append(coverage)
            if not available:
                self.result["missing_functions"].append(coverage)
            represented = any(function in c.get("operation_contract", {}).get("function_ids", [])
                              for c in self.base.get("decision_components", []) + self.rdf_components)
            if not represented:
                self.result["gaps"].append({"code": "NO_OPERATION_FOR_REQUIRED_FUNCTION", "type": "FUNCTION_GAP",
                    "id": function, "label": self.label(function), "situation_id": unit["situation_id"], "participant_id": unit["participant_id"],
                    "explanation": "A função é necessária, mas não há operação representada para atendê-la; mais perguntas não corrigem esta lacuna da base."})
        result = {"situation_id": unit["situation_id"], "participant_id": unit["participant_id"], "status": "INSUFFICIENT",
                  "choices": [], "pending_candidates": [], "partial_segments": []}
        edge_cache = {}
        def edges(left, right):
            key = (left["id"], right["id"])
            if key not in edge_cache:
                matching = []
                for owner in (left, right):
                    for rule in owner["relation_contracts"]:
                        if (rule.get("scope", "WITHIN_OPERATION") in {"BETWEEN_OPERATIONS", "BOTH"}
                                and set(rule.get("from_function_ids", [])) & set(left["function_ids"])
                                and set(rule.get("to_function_ids", [])) & set(right["function_ids"])
                                and rule.get("kind") != "ALTERNATIVE"):
                            relation = self.relation(rule, left, right, unit)
                            self.result["relation_evaluations"].append(relation)
                            if relation["state"] != "FAIL":
                                matching.append(relation)
                edge_cache[key] = matching
            return edge_cache[key]
        # Finite subsets of represented operations, never a search over text or
        # inferred scenarios. A multi-operation set must have authorized edges.
        for size in range(1, len(candidates) + 1):
            if self.result["search"]["complete"]["truncated"]:
                break
            for steps in itertools.combinations(candidates, size):
                budget = self.result["search"]["complete"]
                if budget["examined"] >= budget["limit"]:
                    budget["truncated"] = True
                    break
                budget["examined"] += 1
                covered = set().union(*(set(step["function_ids"]) for step in steps)) & required
                relations = [row for step in steps for row in internal[step["id"]]]
                connectors = []
                for left in steps:
                    for right in steps:
                        if left["id"] == right["id"]:
                            continue
                        connecting = edges(left, right)
                        if connecting:
                            connectors.append(sorted(connecting, key=lambda row: (row["state"] != "PASS", row["id"]))[0])
                reached = {steps[0]["id"]}
                changed = True
                while changed:
                    changed = False
                    for relation in connectors:
                        pair = {relation["from_capability"], relation["to_capability"]}
                        if pair & reached and not pair <= reached:
                            relations.append(relation)
                            reached.update(pair)
                            changed = True
                if len(reached) != len(steps):
                    if covered == required:
                        self.result["integration_gaps"].append({"code": "NO_AUTHORIZED_RELATION", "operation_ids": [step["id"] for step in steps],
                            "situation_id": unit["situation_id"], "participant_id": unit["participant_id"]})
                    continue
                dependencies = {step["id"]: set() for step in steps}
                for relation in connectors:
                    if relation["kind"] in {"SEQUENTIAL", "SEQUENTIAL_REVIEW"}:
                        dependencies[relation["to_capability"]].add(relation["from_capability"])
                ordered = []
                while dependencies:
                    ready = sorted(key for key, prior in dependencies.items() if not prior)
                    if not ready:
                        self.result["integration_gaps"].append({"code": "CYCLIC_OPERATION_DEPENDENCY", "situation_id": unit["situation_id"], "participant_id": unit["participant_id"]})
                        break
                    ordered.extend(ready)
                    for key in ready:
                        dependencies.pop(key)
                    for prior in dependencies.values():
                        prior.difference_update(ready)
                if dependencies:
                    continue
                by_id = {step["id"]: step for step in steps}
                steps = tuple(by_id[key] for key in ordered)
                complete = covered == required and not unit["unknown_requirements"] and not unit["scope_gaps"]
                proposal = self.proposal(unit, steps, relations, covered, complete)
                if not complete:
                    # Keep an authorized connected sequence even when another
                    # reported action/need remains unmapped. A scope gap must
                    # not erase valid composition into isolated suggestions.
                    target = "partial_segments" if proposal["state"] == "PASS" else "pending_candidates"
                    step_ids = {step["id"] for step in steps}
                    # A connected subsequence is useful even if a separate
                    # function is uncovered. Keep inclusion-minimal supports,
                    # with the same bounded output policy as full choices.
                    keep_partial = not any(
                        {step["id"] for step in old["steps"]} <= step_ids
                        and {f["id"] for f in old["covered_functions"]} >= covered
                        for old in result[target])
                    if len(result[target]) >= MAX_CHOICES:
                        self.result["partial_truncated" if target == "partial_segments" else "pending_truncated"] = True
                        keep_partial = False
                    if keep_partial and proposal["state"] == "PASS":
                        proposal.update(state="PARTIAL", ready_for_whole_task=False)
                        result[target] = [old for old in result[target]
                                          if not {step["id"] for step in old["steps"]} < step_ids]
                        result["partial_segments"].append(proposal)
                    elif keep_partial and proposal["state"] == "PENDING":
                        proposal.update(ready_for_whole_task=False, scope="CONDITIONAL_OPERATION_NOT_WHOLE_TASK")
                        result["pending_candidates"].append(proposal)
                    continue
                target = "choices" if proposal["ready_for_functional_scope"] else "pending_candidates"
                if len(result[target]) >= MAX_CHOICES:
                    self.result["truncated" if target == "choices" else "pending_truncated"] = True
                    continue
                # Only inclusion-minimal complete choices; no extra modality is
                # suggested simply because it happens to be available.
                step_ids = {step["id"] for step in steps}
                if any(old["covers_all_required_functions"] and {step["id"] for step in old["steps"]} <= step_ids for old in result[target]):
                    continue
                result[target].append(proposal)
        if result["choices"]:
            result["status"] = "COMPOSED"
        elif result["pending_candidates"]:
            result["status"] = "CONDITIONAL"
        return result

    def run(self):
        self.emit("retrieval", "running", "Recuperando alegações e funções pertinentes às situações informadas…")
        units = self.normalize()
        self.result["context_scope"] = [{"participant_id": u["participant_id"], "participant_label": u["participant_label"],
                                         "situation_id": u["situation_id"], "situation_label": u["situation_label"],
                                         "task_participation": u["task_participation"], "assigned_task_ids": u["executed_task_ids"]}
                                        for u in units]
        if self.result["input_issues"]:
            self.result["gaps"].append({"code": "INPUT_REQUIRES_CORRECTION", "type": "CONTEXT_GAP"})
            return self.result
        # This whole phase finishes before any component is examined.
        for unit in units:
            self.derive_functions(unit)
        # Global requirements are not copied into every person's obligations.
        # Keep any unmapped requirement visible as a scope gap.
        scoped_functions = {f for unit in units for f in unit["requirements"]}
        unassigned = (set(self.context.get("funcoes_requeridas_ids", [])) - scoped_functions
                      if not self.context.get("active_situation_id") else set())
        for situation in self.context.get("situations", []):
            if self.context.get("active_situation_id") and situation["id"] != self.context["active_situation_id"]:
                continue
            if len(situation.get("participant_ids", [])) > 1:
                covered = {f for unit in units if unit["situation_id"] == situation["id"] for f in unit["requirements"]}
                unassigned.update(set(situation.get("function_ids", [])) - covered)
        self.result["unassigned_scope_requirements"] = [self.record(f) for f in sorted(unassigned)]
        if unassigned:
            self.result["gaps"].append({"code": "REQUIRED_FUNCTION_SCOPE_UNASSIGNED", "type": "CONTEXT_SCOPE_GAP", "function_ids": sorted(unassigned),
                "explanation": "A função foi requerida globalmente, mas não há atribuição documentada a uma pessoa e situação. Não foi replicada para todas as pessoas."})
        self.emit("retrieval", "completed", "Funções requeridas e seus testemunhos documentais foram identificados.")
        self.emit("composition", "running", "Conferindo operações, participantes, recursos e relações documentadas…")
        unit_results = [self.compose_unit(unit) for unit in units]
        for unit, row in zip(units, unit_results):
            row.update(participant_label=unit["participant_label"], situation_label=unit["situation_label"])
        self.result["situation_results"] = unit_results
        all_complete = bool(unit_results) and not unassigned and all(row["status"] == "COMPOSED" for row in unit_results)
        for row in unit_results:
            self.result["pending_candidates"].extend(row["pending_candidates"])
            self.result["partial_segments"].extend(row["partial_segments"])
            for choice in row["choices"]:
                if all_complete:
                    self.result["choices"].append(choice)
                else:
                    choice.update(state="PARTIAL", ready_for_whole_task=False, covers_participant_situation=True)
                    self.result["partial_segments"].append(choice)
        viable = {step["id"] for row in self.result["pending_candidates"] + self.result["partial_segments"] + self.result["choices"] for step in row["steps"]}
        viable |= {row["id"] for row in self.result["capability_evaluations"] if row["state"] == "PENDING"}
        viable |= {row["id"] for row in self.result["relation_evaluations"] if row["state"] == "PENDING" and row.get("grounding")}
        merged_conditions = {}
        for condition in self.conditions:
            key = (condition["id"], condition["participant_id"], condition["situation_id"], condition["value"])
            if key in merged_conditions:
                merged = merged_conditions[key]
                merged["required_by"] = sorted(set(merged["required_by"] + condition["required_by"]))
                merged["check_ids"] = sorted(set(merged["check_ids"] + condition["check_ids"]))
            else:
                merged_conditions[key] = condition
        for key, condition in merged_conditions.items():
            condition.update(question_id="question-" + _json_hash(key)[:16], fact_id=condition["id"],
                             candidate_ids=list(condition["required_by"]),
                             field="situated_facts", values=[None, True, False],
                             reason="Esta informação altera a admissibilidade das operações e relações indicadas.")
            if condition["value"] is False:
                self.result["unavailable_conditions"].append(condition)
            elif any(self.fact_alias(fact.get("fact_id")) == self.fact_alias(condition["id"]) and fact.get("participant_id") == condition["participant_id"]
                     and fact.get("situation_id") == condition["situation_id"] and fact.get("value") is None
                     for fact in self.context.get("situated_facts", [])):
                condition["answered_unknown"] = True
                self.result["other_condition_diagnostics"].append(condition)
            elif any(target in viable for target in condition["required_by"]):
                self.result["resources_to_confirm" if condition["kind"] == "resource" else "facts_to_confirm"].append(condition)
            else:
                self.result["other_condition_diagnostics"].append(condition)
        if self.context.get("confirmed") is not True:
            self.result.update(status="UNCONFIRMED", proposal_status="UNCONFIRMED")
        elif all_complete:
            self.result.update(status="COMPOSED", proposal_status="COMPLETE")
        else:
            self.result["proposal_status"] = "CONDITIONAL" if self.result["pending_candidates"] else "PARTIAL" if self.result["partial_segments"] else "NONE"
        if any(phase["truncated"] for phase in self.result["search"].values()):
            self.result["gaps"].append({"code": "SEARCH_LIMIT_REACHED", "type": "SEARCH_LIMIT",
                                        "explanation": "Busca interrompida no limite; ausência de solução não prova inexistência."})
        if not all_complete:
            self.result["gaps"].append({"code": "NO_COMPLETE_SITUATED_COMPOSITION", "type": "COVERAGE_GAP"})
        self.result["alternatives"] = self.result["choices"]
        deferred = self.result.get("deferred_situation_ids", [])
        self.result["covers_selected_scope"] = all_complete
        self.result["covers_all_participants"] = all_complete and not deferred
        self.result["coverage_scope"] = "REGISTERED_TASK_FUNCTIONS" if units and all(u["coverage_scope"] == "REGISTERED_TASK_FUNCTIONS" for u in units) else "DECLARED_FUNCTIONS_ONLY"
        self.result["covers_whole_reported_task"] = all_complete and not deferred and self.result["coverage_scope"] == "REGISTERED_TASK_FUNCTIONS"
        self.result["coverage_explanation"] = ("Cobertura das funções registradas para as tarefas confirmadas; não comprova êxito em uso."
            if self.result["coverage_scope"] == "REGISTERED_TASK_FUNCTIONS" else
            "A cobertura refere-se às funções fundamentadas nesta execução, não à resolução integral de todas as ações do relato.")
        if deferred:
            self.result["coverage_explanation"] += f" A análise se limita à situação priorizada; {len(deferred)} situação(ões) ficou(aram) para depois."
        self.result["trajectory_evidence"] = {"base_sha256": getattr(self.composer, "base_sha256", None),
            "operationalization_status": "PROPOSED_NOT_EVALUATED", "legacy_statuses_preserved": True,
            "applications": [support for row in self.result["choices"] for step in row["steps"] for support in step["groundings"]],
            "pending_applications": [support for row in self.result["pending_candidates"] for step in row["steps"] for support in step["groundings"]],
            "partial_applications": [support for row in self.result["partial_segments"] for step in row["steps"] for support in step["groundings"]]}
        by_scope = {(u["participant_id"], u["situation_id"]): u for u in units}
        for group in ("gaps", "integration_gaps", "exclusions"):
            for row in self.result[group]:
                unit = by_scope.get((row.get("participant_id"), row.get("situation_id")))
                if unit:
                    row.update(participant_label=unit["participant_label"], situation_label=unit["situation_label"])
        self.emit("composition", "completed", "Possibilidades, impedimentos e lacunas situadas foram verificados.")
        return self.result
