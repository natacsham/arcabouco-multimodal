"""Build an explicit public projection from an authorized local source directory.

No source is modified. Original quotations, individual evaluation records and local
paths are not published. Locators and relationships remain inspectable.
"""

import argparse
import copy
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "vendor"))
from rdflib import Graph, Literal, Namespace, RDF, OWL, RDFS

M = Namespace("https://w3id.org/mado#")
VERSION = "1.3.0-rc1"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def locator(row):
    parts = [
        str(row[k])
        for k in (
            "arquivo",
            "pagina",
            "localizacao",
            "secao",
            "codigo_trabalho",
            "fonte_item",
        )
        if row.get(k)
    ]
    if not parts:
        parts = [
            "Registro documental "
            + row["id"]
            + "; localização adicional não disponível nesta distribuição"
        ]
    return " · ".join(parts)


def scrub(value):
    if isinstance(value, dict):
        return {
            k: scrub(v)
            for k, v in value.items()
            if k not in {"source_base", "source_criteria", "raw_sessions", "events"}
        }
    if isinstance(value, list):
        return [scrub(v) for v in value]
    if isinstance(value, str):
        if re.search(r"[A-Za-z]:[/\\]|file://", value):
            return "[Caminho local omitido da distribuição pública]"
    return value


def build(source):
    original_json = source / "data/knowledge-base.json"
    original_rdf = source / "ontology/mado-combined.ttl"
    data = json.loads(original_json.read_text(encoding="utf-8-sig"))
    data = scrub(copy.deepcopy(data))
    g = Graph().parse(original_rdf, format="turtle")
    counts = {
        "withheld_excerpts": 0,
        "withheld_origin_texts": 0,
        "withheld_result_quotes": 0,
    }
    withheld = []
    for row in data["excerpts"]:
        row["localizacao_publica"] = locator(row)
        row["estado_publicacao"] = "TEXTO_NAO_REDISTRIBUIDO"
        row.pop("trecho", None)
        row["aviso_publicacao"] = (
            "Texto original não redistribuído. Consulte a fonte e a localização indicadas."
        )
        node = M[row["id"]]
        g.remove((node, M.conteudoDoTrecho, None))
        g.set(
            (
                node,
                RDFS.label,
                Literal("Referência ao trecho " + row["id"], lang="pt-BR"),
            )
        )
        g.set((node, M.estadoDePublicacaoDoTrecho, Literal("TEXTO_NAO_REDISTRIBUIDO")))
        g.set((node, M.localizacaoDocumental, Literal(row["localizacao_publica"])))
        counts["withheld_excerpts"] += 1
        withheld.append(row["id"])
    for row in data["criterion_origins"]:
        row.pop("texto_item_original", None)
        row["estado_publicacao"] = "TEXTO_NAO_REDISTRIBUIDO"
        row["localizacao_publica"] = locator(row)
        row["aviso_publicacao"] = (
            "Texto do item original não redistribuído; referência documental preservada."
        )
        # Content is retained only in the private, unchanged thesis package.
        node = M[row["id"]]
        for predicate in (
            M.textoItemOriginal,
            M.textoDoItemOriginal,
            M.conteudoDoTrecho,
        ):
            g.remove((node, predicate, None))
        counts["withheld_origin_texts"] += 1
    for row in data["results"]:
        row.pop("descricao", None)
        row["estado_publicacao"] = "TEXTO_NAO_REDISTRIBUIDO"
        row["localizacao_publica"] = (
            "Resultado registrado em "
            + str(row.get("trecho_id", row["id"]))
            + "; consulte a fonte documental indicada."
        )
        node = M[row["id"]]
        for predicate in (M.descricaoDoResultado, M.enunciado, M.descricao):
            g.remove((node, predicate, None))
        g.set(
            (
                node,
                RDFS.label,
                Literal("Registro documental do resultado " + row["id"], lang="pt-BR"),
            )
        )
        g.set(
            (node, M.estadoDePublicacaoDoRegistro, Literal("TEXTO_NAO_REDISTRIBUIDO"))
        )
        g.set((node, M.localizacaoDocumental, Literal(row["localizacao_publica"])))
        counts["withheld_result_quotes"] += 1
    # Questionnaire aggregates remain in the private research package, not in the app.
    data["persona_validation"] = []
    for node in list(g.subjects(RDF.type, M.ValidacaoDePersona)):
        g.remove((node, None, None))
        g.remove((None, None, node))
    # Public teaching adaptation: preserve functional conditions, not diagnostic identity.
    public_description = (
        "Exemplo didático adaptado: um estudante tem interesse intenso e conhecimento "
        "aprofundado sobre um tema. Expressa suas ideias por fala, imagens e desenho. "
        "É necessário preservar sua autoria e organizar os momentos de participação "
        "com a professora e a turma. Este texto público não é a transcrição da entrevista."
    )
    related = {"CTX-RELATADO-01", "CTX-ELICITACAO-01", "CTX-RECONSTRUIDO-HISTORIA-01"}
    for row in data["contexts"]:
        if row["id"] in related:
            row["descricao_do_contexto"] = public_description
            row["natureza"] = "ADAPTACAO_DIDATICA_PUBLICA_NAO_EMPIRICA"
            row["status"] = "ADAPTACAO_PUBLICA"
            node = M[row["id"]]
            g.set(
                (node, M.descricaoDoContexto, Literal(public_description, lang="pt-BR"))
            )
            g.set((node, M.statusDoRegistro, Literal("ADAPTACAO_PUBLICA")))
        if row["id"] in related | {"CTX-TRANSFERENCIA-RECURSO-DIGITAL-01"}:
            row["public_disclosure"] = (
                "Adaptação didática; não é um novo registro de avaliação humana."
            )
            row["caracteristicas_pessoa"] = [
                k
                for k in row.get("caracteristicas_pessoa", [])
                if not any(t in k for t in ("TEA", "TDAH", "DIAGNOSTICO"))
            ]
    for row in data["context_participations"]:
        if row.get("contexto_id") in related | {"CTX-TRANSFERENCIA-RECURSO-DIGITAL-01"}:
            row["caracteristica_ids"] = [
                k
                for k in row.get("caracteristica_ids", [])
                if not any(t in k for t in ("TEA", "TDAH", "DIAGNOSTICO"))
            ]
    data["metadata"].update(
        version=VERSION,
        title="Base pública MADO " + VERSION,
        interface_version="AMADO-web-" + VERSION,
        derived_from_version="1.2.0-RC4-DEMO-FIX2",
        public_projection=True,
        note="Projeção pública posterior à tese; texto original dos trechos não redistribuído.",
        decision_component_count=len(data["decision_components"]),
        active_decision_pattern_count=sum(
            bool(r.get("active_in_rc4", r.get("active_in_rc3")))
            for r in data["decision_components"]
        ),
    )
    # Preserve exact situated support in the migrated demonstration oracle.
    components = {r["id"]: r for r in data["decision_components"]}
    for cfg in data["modal_configurations"]:
        component = components.get(cfg.get("componente_id"), {})
        support_rows = []
        for i, support in enumerate(component.get("criterion_support", []), 1):
            kids = [
                k
                for k in support.get("knowledge_ids", [])
                if k in cfg.get("conhecimento_ids", [])
            ]
            origins = [
                o
                for o in support.get("origin_ids", [])
                if o in cfg.get("origem_criterio_ids", [])
            ]
            if (
                not kids
                or not origins
                or support.get("criterion_id") not in cfg.get("criterio_ids", [])
            ):
                continue
            node = M[f"APL-{cfg['id']}-{i:02d}"]
            g.add((node, RDF.type, M.AplicacaoDeCriterio))
            g.add((M[cfg["id"]], M.possuiAplicacaoDeCriterio, node))
            g.add((node, M.aplicacaoNaConfiguracao, M[cfg["id"]]))
            g.add((node, M.criterioAplicado, M[support["criterion_id"]]))
            g.add(
                (
                    node,
                    M.justificativaDaAplicacao,
                    Literal(support["justification"], lang="pt-BR"),
                )
            )
            for kid in kids:
                g.add((node, M.conhecimentoDaAplicacao, M[kid]))
            for oid in origins:
                g.add((node, M.origemDaAplicacao, M[oid]))
            support_rows.append(
                {
                    **support,
                    "selected_knowledge_ids": kids,
                    "selected_origin_ids": origins,
                }
            )
        cfg["criterion_support"] = support_rows
    # Add revised TBox; version metadata is a replacement, never the old version IRI.
    tbox = Graph().parse(ROOT / "ontology/main.ttl", format="turtle")
    for ont in list(g.subjects(RDF.type, OWL.Ontology)):
        for prop in (OWL.versionIRI, OWL.versionInfo, OWL.priorVersion):
            g.remove((ont, prop, None))
    g += tbox
    # Strip local paths and quote predicates wherever duplicates were recorded.
    for s, p, o in list(g):
        if isinstance(o, Literal) and re.search(r"[A-Za-z]:[/\\]|file://", str(o)):
            g.remove((s, p, o))
        if str(p).rsplit("#", 1)[-1] in {"textoItemOriginal", "textoDoItemOriginal"}:
            g.remove((s, p, o))
        if p in {
            M.consideraCaracteristicaRelevanteDaPessoa,
            M.temCaracteristicaRelevante,
        } and any(t in str(o) for t in ("TEA", "TDAH", "DIAGNOSTICO")):
            if s in {
                M[r["id"]]
                for r in data["contexts"]
                if r["id"] in related | {"CTX-TRANSFERENCIA-RECURSO-DIGITAL-01"}
            } or str(s).split("#")[-1] in {
                r["id"]
                for r in data["context_participations"]
                if r.get("contexto_id")
                in related | {"CTX-TRANSFERENCIA-RECURSO-DIGITAL-01"}
            }:
                g.remove((s, p, o))
    (ROOT / "data/knowledge-base.json").write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    g.serialize(ROOT / "ontology/mado-combined.ttl", format="turtle")
    g.serialize(ROOT / "ontology/mado.owl", format="xml")
    report = {
        "version": VERSION,
        "source_sha256": {
            "knowledge-base.json": sha(original_json),
            "mado-combined.ttl": sha(original_rdf),
        },
        "source_version_preserved": True,
        "public_projection": counts,
        "withheld_excerpt_ids": withheld,
        "triples": len(g),
        "human_evaluation_of_this_version": False,
        "limitations": [
            "Textos originais requerem consulta às fontes; sua redistribuição não foi autorizada.",
            "Adaptação pública do caso não equivale à transcrição ou validação humana.",
        ],
    }
    (ROOT / "evidence/public-projection.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "source", type=Path, help="Existing local FIX2 directory; read-only input"
    )
    args = parser.parse_args()
    print(json.dumps(build(args.source), ensure_ascii=True))
