"""In-memory execution evidence and its projections. No persistence or inference."""

from __future__ import annotations

import copy
import hashlib
import json


class ExecutionEvidence:
    """Record predicates where evaluated; deduplicate repeated authorization checks."""

    def __init__(self, version, context_id):
        self.data = {
            "schema_version": "1.0", "version": version, "context_id": context_id,
            "checks": [], "retrieval": [], "components": [], "supports": [],
            "documentary_conditions": [], "functions": {}, "entities": {},
            "limitations": [
                "Cobertura funcional é uma correspondência declarada, não comprovação de eficácia.",
                "Alternativas textuais não foram replanejadas nem testadas nesta execução.",
                "Condições documentais livres não são regras executáveis.",
            ],
        }
        self._checks = {}

    def check(self, stage, subject_id, rule_id, outcome, message, **details):
        row = {"stage": stage, "subject_id": subject_id, "rule_id": rule_id,
               "outcome": outcome, "message": message, **copy.deepcopy(details)}
        digest = hashlib.sha256(json.dumps(row, sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:16]
        identifier = "CHECK-" + digest
        if identifier not in self._checks:
            row["id"] = identifier
            self._checks[identifier] = row
            self.data["checks"].append(row)
        return identifier

    def checks_for(self, subject, stage=None):
        return [r["id"] for r in self.data["checks"]
                if r["subject_id"] == subject and (stage is None or r["stage"] == stage)]


def build_explanation(evidence):
    """Only project recorded checks and exact supports; never rerun selection."""
    entities = evidence["entities"]
    context_id = evidence["context_id"]
    required = set(evidence["functions"].get("required", []))
    checks = {r["id"]: r for r in evidence["checks"]}
    nodes, edges = {}, []
    configurations, de_para = [], []

    def entity(identifier):
        return entities.get(identifier, {"id": identifier, "title": identifier})

    def title(identifier):
        row = entity(identifier)
        return row.get("title") or row.get("enunciado") or row.get("rotulo") or identifier

    def node(identifier, kind):
        if identifier:
            nodes[identifier] = {"id": identifier, "kind": kind, "label": title(identifier)}

    def edge(source, target, label, kind, check_ids=(), support_id=None):
        if not source or not target:
            return
        row = {"source": source, "target": target, "label": label,
               "kind": kind, "check_ids": list(check_ids)}
        if support_id:
            row["support_id"] = support_id
        existing = next((e for e in edges if (e["source"], e["target"], e["kind"], e.get("support_id")) ==
                         (source, target, kind, support_id)), None)
        if existing:
            existing["check_ids"] = list(dict.fromkeys(existing["check_ids"] + list(check_ids)))
        else:
            edges.append(row)

    node(context_id, "context")
    for component in evidence["components"]:
        if component["selection"] not in {"SELECTED", "CONDITIONAL"}:
            continue
        cfg = component["configuration"]
        cid = component["component_id"]
        cfg_id = cfg["id"]
        nodes[cfg_id] = {"id": cfg_id, "label": component["title"], "kind": "configuration"}
        check_ids = component["check_ids"]
        matched = list(dict.fromkeys(v for r in component.get("matches", []) for v in r.get("ids", [])))
        matching_checks = [checks[x] for x in check_ids if x in checks]
        supports = [r for r in evidence["supports"] if r["component_id"] == cid]
        knowledge_ids = list(dict.fromkeys(k for s in supports for k in s["knowledge_ids"]))
        # Include selected knowledge not tied to every criterion without inventing pairs.
        knowledge_ids = list(dict.fromkeys(knowledge_ids + cfg.get("knowledge_ids", [])))
        witnesses = [r for r in evidence["retrieval"] if r["knowledge_id"] in knowledge_ids
                     and r["authorization"] != "EXCLUIDO"]
        # An existential match needs one concrete witness per retrieved K/ART/function.
        # Keep every witness in execution_evidence; avoid duplicating all combinations in each card.
        representatives = {}
        for witness in witnesses:
            representatives.setdefault((witness["knowledge_id"], witness.get("articulation_id"), witness.get("required_function_id")), witness)
        art_ids = list(dict.fromkeys(r["articulation_id"] for r in witnesses if r.get("articulation_id")))
        construction_art_ids = list(dict.fromkeys(
            aid for kid in knowledge_ids for aid in evidence.get("knowledge_construction", {}).get(kid, [])))
        contributions = [r for r in evidence.get("contributions", [])
                         if r["knowledge_id"] in knowledge_ids and r["articulation_id"] in construction_art_ids]
        for contribution in contributions:
            coid, aid, kid = contribution["id"], contribution["articulation_id"], contribution["knowledge_id"]
            nodes[coid] = {"id": coid, "kind": "contribution", "label": contribution["statement"],
                          "verification_status": contribution["verification_status"],
                          "nature": contribution.get("nature", "")}
            node(aid, "articulation")
            node(kid, "knowledge")
            edge(coid, aid, "parcela documental da articulação", "documentary_contribution")
            edge(coid, kid, "contribui para a construção registrada", "documentary_contribution")
            tid = contribution.get("excerpt_id")
            sid = (contribution.get("source") or {}).get("id")
            if tid:
                node(tid, "excerpt")
                edge(coid, tid, "ancorada no registro", "documentary_contribution")
            if sid:
                node(sid, "source")
                edge(tid, sid, "registro localizado na fonte", "documentary_contribution")
        context_conditions = [{"id": v, "label": title(v),
                               "check_ids": [r["id"] for r in matching_checks if v in r.get("matched_ids", [])]}
                              for v in matched]
        functions = cfg.get("function_ids", [])
        for function in functions:
            node(function, "function")
            if function in required:
                edge(context_id, function, "requisito informado e confirmado", "context_requirement")
            edge(function, cfg_id, "função oferecida pelo padrão", "offered_function", check_ids)
        for kid in knowledge_ids:
            node(kid, "knowledge")
            edge(kid, cfg_id, "sustenta configuração", "selected_knowledge", check_ids)
            for tid in entity(kid).get("trecho_ids", []):
                node(tid, "excerpt")
                edge(kid, tid, "sustentado por registro", "documentary_provenance")
                sid = entity(tid).get("fonte_id")
                if sid:
                    node(sid, "source")
                    edge(tid, sid, "localizado em", "documentary_provenance")
        for witness in witnesses:
            aid = witness.get("articulation_id")
            if aid:
                node(aid, "articulation")
                node(witness["input_knowledge_id"], "knowledge")
                edge(witness["input_knowledge_id"], aid, "entrada compatível nesta recuperação", "retrieval_witness", witness["check_ids"])
                edge(aid, witness["knowledge_id"], "produz/refina", "documented_articulation", witness["check_ids"])
        for support in supports:
            criterion = support["criterion_id"]
            node(criterion, "criterion")
            edge(criterion, cfg_id, "orienta configuração", "situated_support", support_id=support["id"])
            for kid in support["knowledge_ids"]:
                edge(kid, criterion, "fundamenta este uso", "situated_support", support_id=support["id"])
            for origin in support["origins"]:
                oid, sid, tid = origin["id"], origin.get("fonte_id"), origin.get("trecho_id")
                node(oid, "criterion_origin")
                edge(oid, criterion, "origina critério", "exact_origin", support_id=support["id"])
                if tid:
                    node(tid, "excerpt")
                    edge(oid, tid, "documentado no registro", "exact_origin", support_id=support["id"])
                if sid:
                    node(sid, "source")
                    edge(sid, oid, "registra origem", "exact_origin", support_id=support["id"])
        configuration = {
            "component_id": cid, "id": cfg_id, "title": component["title"],
            "selection": component["selection"], "availability_status": cfg["availability_status"],
            "function": cfg["funcao"], "modalities": [cfg["modo"]], "actions": [cfg["acao"]],
            "conditions": cfg.get("conditions", []), "alternative": cfg.get("alternative", ""),
            "limit": cfg.get("limit", ""), "monitoring": cfg.get("monitoring", ""),
            "resource_options": cfg.get("resource_options", []),
            "construction": {"contributions": contributions,
                             "articulations": [{**entity(aid), "mobilized_in_execution": aid in art_ids} for aid in construction_art_ids],
                             "knowledge": [entity(kid) for kid in knowledge_ids]},
            "application": {"context_conditions": context_conditions,
                            "required_functions": [{"id": f, "label": title(f)} for f in functions if f in required],
                            "offered_functions": [{"id": f, "label": title(f)} for f in functions],
                            "supports": supports, "check_ids": check_ids, "checks": matching_checks,
                            "retrieval_witnesses": list(representatives.values()),
                            "retrieval_witness_ids": [w["check_ids"][0] for w in witnesses],
                            "retrieval_witness_note": "Uma testemunha concreta suficiente por conhecimento/articulação/função; todas as correspondências permanecem no registro da execução.",
                            "limitations": [r for r in evidence["documentary_conditions"] if r["subject_id"] in [cid] + construction_art_ids + knowledge_ids]},
        }
        configurations.append(configuration)
        trajectory_ids = list(dict.fromkeys(v for aid in art_ids
                              for field in ("estudo_ids", "artefato_ids", "persona_ids", "fonte_ids")
                              for v in entity(aid).get(field, [])))
        de_para.append({
            "id": "DEPARA-" + cid, "condicao_ids": matched, "condicoes": [title(v) for v in matched],
            "abstracao_funcional": cfg.get("functional_meaning", ""),
            "abstracao_origin": "FORMULACAO_DOCUMENTADA_DO_PADRAO_NAO_INFERENCIA_NOVA",
            "conhecimento_ids": knowledge_ids, "articulacao_ids": art_ids,
            "articulacoes": [title(a) for a in art_ids],
            "trajetoria": [{"id": v, "titulo": title(v)} for v in trajectory_ids],
            "criterio_ids": list(dict.fromkeys(s["criterion_id"] for s in supports)),
            "origem_criterio_ids": list(dict.fromkeys(o["id"] for s in supports for o in s["origins"])),
            "implicacao_decisoria": cfg["funcao"], "componente_ids": [cid],
            "configuracao_multimodal": [{"modo": cfg["modo"], "funcao": cfg["funcao"],
                "responsavel": cfg["responsavel"], "recursos": cfg["recursos"],
                "estado_recurso": cfg["availability_status"]}],
            "alternativa": cfg["alternative"], "condicao_limite": " ".join(cfg["conditions"] + [cfg["limit"]]),
            "acompanhamento": cfg["monitoring"], "check_ids": check_ids,
        })
    stages = [{"id": key, "title": label,
               "summary": summary, "check_ids": [r["id"] for r in evidence["checks"] if r["stage"] == key]}
              for key, label, summary in [
                  ("context", "Conferência do contexto", "O contexto foi informado e confirmado; não é um diagnóstico automático."),
                  ("retrieval", "Recuperação situada", "Tarefa e condições correspondentes são registradas como testemunhas da consulta."),
                  ("knowledge", "Condições do conhecimento", "Foram conferidas as restrições estruturadas e a presença de proveniência."),
                  ("articulation", "Articulações documentadas", "Uma entrada compatível e uma função requerida habilitam a recuperação; a síntese é anterior à execução."),
                  ("component", "Escolha de configurações", "Os padrões existentes foram confrontados com condições, recursos e suporte documental."),
                  ("coverage", "Cobertura declarada e limites", "Funções requeridas e oferecidas são comparadas; isso não mede eficácia em uso."),
              ]]
    return {"schema_version": "1.0", "status": evidence["status"],
            "summary": "Percurso das verificações registradas, com construção documental separada da aplicação ao caso.",
            "stages": stages, "configurations": configurations,
            "rejected": [r for r in evidence["components"] if r["selection"] in {"REJECTED", "NOT_EVALUATED"}],
            "functions": evidence["functions"], "limitations": evidence["limitations"],
            "graph": {"nodes": list(nodes.values()), "edges": edges}, "de_para": de_para}
