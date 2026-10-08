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
from rdflib import BNode, Graph, Literal, Namespace, OWL, RDF, XSD
from rdflib.compare import to_canonical_graph

M = Namespace("https://w3id.org/mado#")
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


def build_graph(base, tbox, data):
    """Return a new graph; never mutate the caller's graphs or JSON."""
    validate_contributions(data)
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

    for row in data["knowledge"]:
        node = M[row["id"]]
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
