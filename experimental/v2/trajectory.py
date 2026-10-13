"""Read-only, fail-closed bridge from the research JSON to the V2 composer.

The bindings are proposed assisted operationalizations, not a fresh reading of
the publications. No legacy status, original base or public motor is modified.
"""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
from typing import Any

try:
    from .composer import Composer, MADO, V2, ROOT, _json_hash
except ImportError:
    from composer import Composer, MADO, V2, ROOT, _json_hash
from rdflib import Graph, Literal, RDF, RDFS, URIRef
from rdflib.namespace import OWL

HERE = Path(__file__).resolve().parent
DEFAULT_BASE = ROOT / "data" / "knowledge-base.json"
DEFAULT_BINDINGS = HERE / "trajectory-bindings.json"
PUBLIC_RECORDS = ("https://github.com/natacsham/arcabouco-multimodal/blob/"
                  "73013190f26cf8806e7f647dbb3fa36a8c07a3c3/data/knowledge-base.json")
ALLOWED_KNOWLEDGE_STATES = {
    "CANDIDATO_RECONSTRUIDO_A_REVISAR", "CONFERIDO_PARA_O_ESCOPO_RC3"
}
# Curation contracts live with the versioned bindings, not as a K/target
# whitelist in Python. They remain independently checked against applications.


class TrajectoryError(ValueError):
    """The declared bridge cannot be substantiated by the supplied records."""


def _required_text(record: dict, key: str) -> str:
    value = record.get(key)
    if not isinstance(value, str) or not value.strip():
        raise TrajectoryError(f"Texto obrigatório ausente: {record.get('id', '?')}/{key}")
    return value


class ResearchComposer(Composer):
    """Same compose API as Composer, with real-record projection and evidence."""

    def __init__(self, base_path: Path | str | None = None,
                 bindings_path: Path | str | None = None,
                 include_audio: bool = True, *, legacy_projection: bool = True) -> None:
        paths = [HERE / "schema.ttl", HERE / "base.ttl"]
        if include_audio:
            paths.append(HERE / "extensions" / "audio-review.ttl")
        super().__init__(paths)
        self.base_path = Path(base_path or DEFAULT_BASE).resolve(strict=True)
        self.bindings_path = Path(bindings_path or DEFAULT_BINDINGS).resolve(strict=True)
        self.include_audio = include_audio
        raw_base = self.base_path.read_bytes()
        raw_bindings = self.bindings_path.read_bytes()
        self.base_sha256 = hashlib.sha256(raw_base).hexdigest()
        self.bindings_sha256 = hashlib.sha256(raw_bindings).hexdigest()
        self.fingerprints[str(self.base_path)] = self.base_sha256
        self.fingerprints[str(self.bindings_path)] = self.bindings_sha256
        self.base = json.loads(raw_base.decode("utf-8-sig"))
        self.bindings = json.loads(raw_bindings.decode("utf-8-sig"))
        self.contracts = self.bindings.get("contracts")
        if not isinstance(self.contracts, dict) or not self.contracts:
            raise TrajectoryError("Contratos curados da ponte ausentes.")
        self.records: dict[tuple[str, str], dict] = {}
        self.application_records: dict[str, dict] = {}
        self.legacy_projection = legacy_projection
        self.situated_graph = Graph()
        self.situated_graph += self.graph
        # The original pilot remains reproducible on request. The situated
        # adapter reads operation contracts directly from every active research
        # component and is not limited by the old five pilot bindings.
        if legacy_projection:
            self._validate_records()
            self._project()
        self.projected_graph_sha256 = self._graph_hash()

    def _graph_hash(self) -> str:
        return hashlib.sha256("\n".join(sorted(
            " ".join(term.n3() for term in triple) for triple in self.graph
        )).encode()).hexdigest()

    def _validate_records(self) -> None:
        if (self.bindings.get("version") != "trajectory-pilot-1"
                or self.bindings.get("status") != "PROPOSED_OPERATIONALIZATION"):
            raise TrajectoryError("Ponte não autorizada como operacionalização proposta.")
        registry = self.bindings.get("records")
        if not isinstance(registry, dict) or not registry:
            raise TrajectoryError("A ponte exige registros identificados e hashes conferidos.")
        for collection, selected in registry.items():
            rows = self.base.get(collection)
            if not isinstance(rows, list) or not isinstance(selected, dict):
                raise TrajectoryError(f"Coleção inválida: {collection}")
            for identifier, expected_hash in selected.items():
                matches = [row for row in rows if isinstance(row, dict) and row.get("id") == identifier]
                if len(matches) != 1:
                    raise TrajectoryError(f"Registro ausente ou duplicado: {collection}/{identifier}")
                record = matches[0]
                if _json_hash(record) != expected_hash:
                    raise TrajectoryError(f"Registro mudou; reconferir a ponte: {collection}/{identifier}")
                if collection == "knowledge":
                    if record.get("status_revisao") not in ALLOWED_KNOWLEDGE_STATES:
                        raise TrajectoryError(f"Estado legado não admitido no piloto: {identifier}")
                    if record.get("foundation_review_status") not in (None, "PARCIAL"):
                        raise TrajectoryError(f"Estado da fundamentação não admitido: {identifier}")
                if collection == "contributions" and record.get("verification_status") not in {"CONFERIDA_NO_REGISTRO", "CONFERIDA_NO_DOCUMENTO"}:
                    raise TrajectoryError(f"Contribuição não conferida no registro: {identifier}")
                self.records[(collection, identifier)] = copy.deepcopy(record)

    def _record_from_base(self, collection: str, identifier: str) -> dict:
        try:
            return self.records[(collection, identifier)]
        except (KeyError, TypeError) as exc:
            raise TrajectoryError(f"Referência não vinculada/conferida: {collection}/{identifier}") from exc

    def _keep_record(self, collection: str, identifier: str, node: URIRef) -> None:
        record = self._record_from_base(collection, identifier)
        self.graph.add((node, V2.legacyCollection, Literal(collection)))
        self.graph.add((node, V2.legacyRecordId, Literal(identifier)))
        self.graph.add((node, V2.legacyRecordHash, Literal(_json_hash(record))))
        self.graph.add((node, V2.legacyRecordJSON, Literal(json.dumps(
            record, ensure_ascii=False, sort_keys=True, separators=(",", ":")))))

    def _project_source_excerpt(self, excerpt_id: str) -> set[tuple[str, str]]:
        excerpt = self._record_from_base("excerpts", excerpt_id)
        source_id = _required_text(excerpt, "fonte_id")
        source = self._record_from_base("sources", source_id)
        source_node, excerpt_node = MADO[source_id], MADO[excerpt_id]
        self.graph.add((source_node, RDF.type, MADO.Fonte))
        self.graph.add((source_node, RDFS.label, Literal(_required_text(source, "titulo"), lang="pt")))
        document_url = excerpt.get("document_url") or source.get("url")
        self.graph.add((source_node, V2.url, Literal(document_url or PUBLIC_RECORDS)))
        self.graph.add((source_node, V2.referenceKind, Literal("DOCUMENT_LINK_RECORDED" if document_url else "PUBLIC_METADATA_NOT_ORIGINAL_DOCUMENT")))
        for field in ("edition", "review_status"):
            if source.get(field):
                self.graph.add((source_node, V2[field], Literal(str(source[field]))))
        for field in ("document_url", "document_version", "document_review_status", "document_paraphrase"):
            if excerpt.get(field):
                self.graph.add((excerpt_node, V2[field], Literal(str(excerpt[field]))))
        self.graph.add((excerpt_node, RDF.type, MADO.TrechoDocumental))
        self.graph.add((excerpt_node, MADO.trechoDeFonte, source_node))
        self.graph.add((excerpt_node, MADO.localizacaoDocumental,
                        Literal(_required_text(excerpt, "localizacao_publica"))))
        self._keep_record("sources", source_id, source_node)
        self._keep_record("excerpts", excerpt_id, excerpt_node)
        return {("sources", source_id), ("excerpts", excerpt_id)}

    def _project(self) -> None:
        graph = self.graph
        # Save primary passages before replacing every generic pilot grounding.
        primary = {}
        for node in list(graph.subjects(RDF.type, V2.Contribution)):
            if str(graph.value(node, V2.status)) == "PRIMARY_CHECKED":
                primary[str(node).rsplit("#", 1)[-1]] = {
                    "excerpt": graph.value(node, V2.excerpt),
                    "statement": graph.value(node, V2.statement),
                }
        for kind in (V2.GroundingApplication, V2.Contribution, V2.ArticulationSupport,
                     MADO.ConhecimentoMultimodalArticulado):
            for node in list(graph.subjects(RDF.type, kind)):
                if str(node).startswith(str(V2)):
                    graph.remove((node, None, None))
        graph.remove((V2.SourceLegacy, None, None))
        graph.remove((V2.ExcerptLegacy, None, None))
        for predicate in (V2.knowledge, V2.criterion, V2.articulation, V2.status):
            graph.remove((V2.ProductionThenReview, predicate, None))
        for name in ("legacyCollection", "legacyRecordId", "legacyRecordHash", "legacyRecordJSON",
                     "legacyReviewStatus", "legacyFoundationStatus", "referenceKind", "bindingStatus"):
            graph.add((V2[name], RDF.type, OWL.DatatypeProperty))
        for name in ("derivedFromLegacy", "contributionForKnowledge", "conditionFromKnowledge"):
            graph.add((V2[name], RDF.type, OWL.ObjectProperty))

        for (collection, identifier), record in self.records.items():
            if collection != "knowledge":
                continue
            node = MADO[identifier]
            graph.add((node, RDF.type, MADO.ConhecimentoMultimodalArticulado))
            graph.add((node, RDFS.label, Literal(_required_text(record, "enunciado"), lang="pt")))
            graph.add((node, V2.epistemicStatus, Literal("PARTIAL_LEGACY")))
            graph.add((node, V2.legacyReviewStatus, Literal(record["status_revisao"])))
            graph.add((node, V2.legacyFoundationStatus, Literal(record.get("foundation_review_status", "NOT_REVIEWED_IN_PILOT"))))
            self._keep_record(collection, identifier, node)

        facts = self.bindings.get("facts")
        if not isinstance(facts, dict):
            raise TrajectoryError("Fatos operacionais ausentes.")
        for identifier, fact in facts.items():
            if not identifier.isidentifier() or not isinstance(fact, dict):
                raise TrajectoryError("Fato operacional inválido.")
            graph.add((V2[identifier], RDF.type, V2.ContextFact))
            graph.add((V2[identifier], RDFS.label, Literal(_required_text(fact, "label"), lang="pt")))
            if fact.get("scope") == "context":
                graph.add((V2[identifier], V2.scope, Literal("context")))
            for knowledge_id in fact.get("knowledge_ids", []):
                self._record_from_base("knowledge", knowledge_id)
                graph.add((V2[identifier], V2.conditionFromKnowledge, MADO[knowledge_id]))

        applications = self.bindings.get("applications")
        if not isinstance(applications, list) or not applications:
            raise TrajectoryError("Aplicações exatas ausentes.")
        ids, targets = set(), set()
        for binding in applications:
            identifier = _required_text(binding, "id")
            target = _required_text(binding, "target")
            if identifier in ids or target in targets:
                raise TrajectoryError("Aplicação ou alvo duplicado na ponte.")
            ids.add(identifier)
            targets.add(target)
            if self.contracts.get(target, {}).get("optional_extension") == "audio" and not self.include_audio:
                continue
            self._project_application(binding, primary, facts)
        expected = {target for target, contract in self.contracts.items()
                    if self.include_audio or contract.get("optional_extension") != "audio"}
        actual = {row["target"] for row in self.application_records.values()}
        if actual != expected:
            raise TrajectoryError("A ponte deve cumprir exatamente os contratos curados publicados.")

    def _project_application(self, binding: dict, primary: dict, facts: dict) -> None:
        graph = self.graph
        identifier, target_name = binding["id"], binding["target"]
        node, target = V2[identifier], V2[target_name]
        kind = binding.get("kind")
        if binding.get("status") != "PROPOSED_OPERATIONALIZATION" or kind not in ("capability", "relation"):
            raise TrajectoryError(f"Aplicação pendente ou inválida: {identifier}")
        contract = self.contracts.get(target_name)
        if contract is None or kind != contract["kind"] or binding.get("criterion") != contract["criterion"]:
            raise TrajectoryError(f"Alvo, função do vínculo ou critério fora do contrato: {identifier}")
        for field in ("knowledge_ids", "primary_contribution_ids", "requires_facts"):
            values = binding.get(field)
            if (not isinstance(values, list) or not values
                    or any(not isinstance(value, str) or not value for value in values)
                    or len(values) != len(set(values))):
                raise TrajectoryError(f"Lista de fundamento/condição inválida: {identifier}/{field}")
            actual_values = set(values)
            expected_values = set(contract[field])
            valid = (expected_values <= actual_values if field == "requires_facts"
                     else expected_values == actual_values)
            if not valid:
                raise TrajectoryError(f"Invariante removida ou fundamento trocado sem revisão: {identifier}/{field}")
        target_type = V2.Capability if kind == "capability" else V2.RelationRule
        if (target, RDF.type, target_type) not in graph or (kind == "relation" and node != target):
            raise TrajectoryError(f"Alvo inexistente ou incompatível: {identifier}")
        knowledge_ids = binding.get("knowledge_ids")
        supports = binding.get("legacy_supports")
        primary_ids = binding.get("primary_contribution_ids")
        if not knowledge_ids or not supports or not primary_ids:
            raise TrajectoryError(f"Fundamentação incompleta: {identifier}")
        if set(knowledge_ids) != {item.get("knowledge_id") for item in supports}:
            raise TrajectoryError(f"Conhecimentos sem contribuição específica: {identifier}")
        art, product = V2[identifier + "Articulation"], V2[identifier + "Knowledge"]
        graph.add((product, RDF.type, MADO.ConhecimentoMultimodalArticulado))
        graph.add((product, RDFS.label, Literal(_required_text(binding, "label"), lang="pt")))
        graph.add((product, V2.epistemicStatus, Literal("DESIGN_SYNTHESIS_NOT_EMPIRICAL")))
        graph.add((art, RDF.type, V2.ArticulationSupport))
        graph.add((art, V2.produces, product))
        graph.add((art, V2.operation, Literal(_required_text(binding, "operation"))))
        graph.add((art, V2.addedUnderstanding, Literal(_required_text(binding, "understanding"))))
        graph.add((art, V2.status, Literal("CURATED_FOR_PILOT")))
        graph.add((art, V2.bindingStatus, Literal("PROPOSED_OPERATIONALIZATION")))
        used: set[tuple[str, str]] = set()
        contribution_records = []
        for index, support in enumerate(supports):
            kid, excerpt_id = support.get("knowledge_id"), support.get("excerpt_id")
            knowledge = self._record_from_base("knowledge", kid)
            excerpt = self._record_from_base("excerpts", excerpt_id)
            if (excerpt_id not in knowledge.get("trecho_ids", [])
                    or excerpt.get("fonte_id") not in knowledge.get("fonte_ids", [])):
                raise TrajectoryError(f"Trecho não pertence ao conhecimento: {kid}/{excerpt_id}")
            used.add(("knowledge", kid))
            used.update(self._project_source_excerpt(excerpt_id))
            graph.add((product, V2.derivedFromLegacy, MADO[kid]))
            contribution_id = support.get("contribution_id")
            if contribution_id:
                contribution = self._record_from_base("contributions", contribution_id)
                if contribution.get("knowledge_id") != kid or contribution.get("excerpt_id") != excerpt_id:
                    raise TrajectoryError(f"Vínculo de contribuição inválido: {contribution_id}")
                statement = _required_text(contribution, "statement")
                used.add(("contributions", contribution_id))
                self._keep_record("contributions", contribution_id, MADO[contribution_id])
            else:
                if support.get("statement_field") != "rastreabilidade":
                    raise TrajectoryError("Uma contribuição legada exige um campo localizado explícito.")
                statement = _required_text(excerpt, "rastreabilidade")
            cnode = V2[identifier + "LegacyContribution" + str(index + 1)]
            graph.add((cnode, RDF.type, V2.Contribution))
            graph.add((cnode, V2.inArticulation, art))
            graph.add((cnode, V2.excerpt, MADO[excerpt_id]))
            graph.add((cnode, V2.statement, Literal(statement)))
            graph.add((cnode, V2.status, Literal("LEGACY_RECORD_ONLY")))
            graph.add((cnode, V2.contributionForKnowledge, MADO[kid]))
            if contribution_id:
                graph.add((cnode, V2.derivedFromLegacy, MADO[contribution_id]))
            contribution_records.append({"id": str(cnode), "knowledge_id": kid,
                                         "contribution_id": contribution_id,
                                         "excerpt_id": excerpt_id, "source_id": excerpt["fonte_id"],
                                         "status": "LEGACY_RECORD_ONLY", "statement": statement})
        for index, primary_id in enumerate(primary_ids):
            if primary_id not in primary:
                raise TrajectoryError(f"Contribuição primária não disponível: {primary_id}")
            template = primary[primary_id]
            cnode = V2[identifier + "PrimaryContribution" + str(index + 1)]
            graph.add((cnode, RDF.type, V2.Contribution))
            graph.add((cnode, V2.inArticulation, art))
            graph.add((cnode, V2.excerpt, template["excerpt"]))
            graph.add((cnode, V2.statement, template["statement"]))
            graph.add((cnode, V2.status, Literal("PRIMARY_CHECKED")))
        criterion_id = _required_text(binding, "criterion")
        if binding.get("criterion_origin"):
            criterion = self._record_from_base("criteria", criterion_id)
            origin = self._record_from_base("criterion_origins", binding.get("criterion_origin"))
            if (origin.get("criterio_id") != criterion_id
                    or binding.get("criterion_origin") != contract.get("criterion_origin")
                    or origin.get("fonte_id") != contract.get("criterion_source_id")):
                raise TrajectoryError("Origem do critério incompatível com o contrato curado.")
            used.update(self._project_source_excerpt(origin["trecho_id"]))
            used.update({("criteria", criterion_id), ("criterion_origins", origin["id"])})
            criterion_node = MADO[criterion_id]
            graph.add((criterion_node, RDF.type, MADO.CriterioDeDecisaoMultimodal))
            graph.add((criterion_node, RDFS.label, Literal(_required_text(criterion, "enunciado"), lang="pt")))
            primary_source = V2[_required_text(contract, "criterion_primary_source")]
            if (primary_source, RDF.type, MADO.Fonte) not in graph:
                raise TrajectoryError("Fonte primária do critério não declarada.")
            graph.add((criterion_node, V2.source, primary_source))
            graph.add((criterion_node, V2.locator, Literal(_required_text(contract, "criterion_locator"))))
            graph.add((criterion_node, V2.justification, Literal(_required_text(binding, "justification"))))
            self._keep_record("criteria", criterion_id, criterion_node)
            self._keep_record("criterion_origins", origin["id"], MADO[origin["id"]])
        else:
            criterion_node = V2[criterion_id]
            if (criterion_node, RDF.type, MADO.CriterioDeDecisaoMultimodal) not in graph:
                raise TrajectoryError("Critério não declarado no grafo; não se presume fundamentação por associação genérica.")
        if kind == "capability":
            graph.add((node, RDF.type, V2.GroundingApplication))
            graph.add((node, V2.capability, target))
            graph.add((node, V2.justification, Literal(_required_text(binding, "justification"))))
        for predicate, value in ((V2.knowledge, product), (V2.criterion, criterion_node), (V2.articulation, art)):
            graph.add((node, predicate, value))
        graph.add((node, V2.status, Literal("CURATED_FOR_PILOT")))
        graph.add((node, V2.bindingStatus, Literal("PROPOSED_OPERATIONALIZATION")))
        for fact_id in binding.get("requires_facts", []):
            if fact_id not in facts:
                raise TrajectoryError(f"Condição da ponte não declarada: {fact_id}")
            graph.add((target, V2.requiresFact, V2[fact_id]))
        self.application_records[str(node)] = {
            "id": str(node), "target": target_name, "kind": kind,
            "status": "PROPOSED_OPERATIONALIZATION", "knowledge_ids": list(knowledge_ids),
            "criterion": criterion_id, "articulation": str(art), "produced_knowledge": str(product),
            "operation": binding["operation"], "understanding": binding["understanding"],
            "legacy_contributions": contribution_records,
            "primary_contribution_ids": list(primary_ids),
            "requires_facts": list(binding.get("requires_facts", [])),
            "record_keys": sorted(used),
        }

    def compose_context(self, context: dict[str, Any], engine=None, progress=None) -> dict[str, Any]:
        # A caller may retain the legacy projection for its editable catalogue
        # and regression API. The situated evaluator uses the primary-grounded
        # RDF records before that historical projection, without swapping shared
        # state or invoking the legacy search.
        if self.legacy_projection:
            view = copy.copy(self)
            view.graph = self.situated_graph
            return Composer.compose_context(view, context, engine=engine, progress=progress)
        return super().compose_context(context, engine=engine, progress=progress)

    def compose(self, context: dict[str, Any]) -> dict[str, Any]:
        self.projected_graph_sha256 = self._graph_hash()
        result = super().compose(context)
        def used_applications(choices: list) -> list[str]:
            identifiers = set()
            for choice in choices:
                for step in choice.get("steps", []):
                    identifiers.update(item["id"] for item in step.get("groundings", []))
                identifiers.update(relation["grounding"]["id"] for relation in choice.get("relations", [])
                                   if relation.get("grounding"))
            return sorted(identifiers & self.application_records.keys())
        used = used_applications(result["choices"])
        pending = used_applications(result["pending_candidates"])
        partial = used_applications(result.get("partial_segments", []))
        def evidence_records(application_ids: list[str], usage: str) -> list[dict]:
            record_keys = {tuple(key) for identifier in application_ids
                           for key in self.application_records[identifier]["record_keys"]}
            return [{"collection": collection, "id": identifier, "usage": usage,
                     "sha256": _json_hash(self.records[(collection, identifier)]),
                     "record": copy.deepcopy(self.records[(collection, identifier)])}
                    for collection, identifier in sorted(record_keys)]
        result["trajectory_evidence"] = {
            "base_sha256": self.base_sha256, "bindings_sha256": self.bindings_sha256,
            "projected_graph_sha256": self.projected_graph_sha256,
            "interpretation": self.bindings["interpretation"],
            "records": evidence_records(used, "COMPLETE_PROPOSAL"),
            "pending_records": evidence_records(pending, "CONDITIONAL_CANDIDATE"),
            "partial_records": evidence_records(partial, "PARTIAL_SEGMENT_NOT_WHOLE_TASK"),
            "applications": [copy.deepcopy(self.application_records[key]) for key in used],
            "pending_applications": [copy.deepcopy(self.application_records[key]) for key in pending],
            "partial_applications": [copy.deepcopy(self.application_records[key]) for key in partial],
            "legacy_statuses_preserved": True,
            "scope": "Produzir e revisar uma contribuição em contexto de aprendizagem; não comprova envio, feedback de envio ou uso humano.",
        }
        return result


def build_trajectory_graph(base_path: Path | str | None = None,
                           bindings_path: Path | str | None = None,
                           include_audio: bool = True) -> Graph:
    """Return a deterministic RDF projection, without writing any file."""
    return ResearchComposer(base_path, bindings_path, include_audio).graph


def compose_context(context: dict[str, Any], engine=None, progress=None) -> dict[str, Any]:
    """Public situated contract; legacy bindings cannot gate unrelated claims."""
    composer = ResearchComposer(legacy_projection=False)
    return composer.compose_context(context, engine=engine, progress=progress)
