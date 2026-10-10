"""Experimental, data-driven composition of grounded interaction capabilities.

This module does not interpret narrative, infer abilities from diagnoses, perform
the suggested interactions, or classify CARE relations. It enumerates proposals
whose registered conditions and representation transitions were checked. The
analytical synthesis is recorded in RDF, not discovered by this program.
"""

from __future__ import annotations

import hashlib
import itertools
import json
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
        return {**self._record(node), "url": str(url)} if valid else None

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
                                      "excerpt": self._record(excerpt),
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

    def compose(self, context: dict[str, Any]) -> dict[str, Any]:
        checks = _Checks()
        result: dict[str, Any] = {
            "status": "INSUFFICIENT", "context_id": context.get("id") if isinstance(context, dict) else None,
            "choices": [], "alternatives": [], "pending_candidates": [], "exclusions": [],
            "gaps": [], "input_issues": [], "required_functions": [], "truncated": False,
            "pending_truncated": False, "maximum_choices": MAX_CHOICES,
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
        relation_rules = sorted(set(self.graph.subjects(RDF.type, V2.RelationRule)), key=str)
        relation_cache: dict[tuple[str, str], list[dict[str, Any]]] = {}
        result["relation_evaluations"] = []
        for steps in itertools.product(*candidates):
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
            transitions: list[list[dict[str, Any]]] = []
            for left, right in zip(steps, steps[1:]):
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
                transitions.append(relation_cache[key])
            for relations in itertools.product(*transitions):
                state = _worst([step["state"] for step in steps] + [relation["state"] for relation in relations])
                bucket = result["choices"] if state == "PASS" else result["pending_candidates"]
                truncation = "truncated" if state == "PASS" else "pending_truncated"
                if len(bucket) >= MAX_CHOICES:
                    result[truncation] = True
                    continue
                proposal = self._choice(steps, relations, context, state)
                proposal["check_ids"].append(boundary["id"])
                bucket.append(proposal)
        result["alternatives"] = result["choices"]
        if result["choices"]:
            result["status"] = "COMPOSED"
        else:
            result["gaps"].append({"code": "PENDING_CONDITIONS" if result["pending_candidates"] else "NO_COMPLETE_COMPOSITION",
                                   "explanation": "Nenhum plano parcial ou candidato pendente é apresentado como orientação pronta."})
        result["limits"] = [
            "Resultados são propostas de projeto, não garantia de acessibilidade ou melhores resultados educacionais.",
            "Fatos e disponibilidade são declarações confirmadas no contexto; não medições realizadas pelo programa.",
            "Conferência documental representa o estado registrado da contribuição; não nova leitura das fontes nesta execução.",
            "Não há interpretação de texto livre, comparação de preferências nem otimização entre as alternativas.",
        ]
        return result
