"""One-time, lossless migration of the preserved pilot into the curated base.

This is an authoring operation, never invoked while answering a user's case.
The original IRIs, source assertions and documentary statuses are retained.
"""
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "vendor")]
sys.dont_write_bytecode = True


def capture():
    from rdflib import URIRef
    from experimental.v2.trajectory import ResearchComposer
    from experimental.v2.composer import _SituatedRun
    composer = ResearchComposer(legacy_projection=False)
    run = _SituatedRun(composer, {})
    statements = []
    for subject, predicate, obj in sorted(composer.graph, key=lambda triple: tuple(t.n3() for t in triple)):
        row = {"subject": str(subject), "predicate": str(predicate), "object": str(obj),
               "kind": "iri" if isinstance(obj, URIRef) else "literal"}
        if getattr(obj, "datatype", None):
            row["datatype"] = str(obj.datatype)
        if getattr(obj, "language", None):
            row["language"] = obj.language
        statements.append(row)
    return {"migration_origin_commit": "285de388dedd9ff7d6938e35c0bff4eb0fad9c75",
            "status": "PRESERVED_CURATED_PILOT_NOT_HUMAN_VALIDATION",
            "components": run.project_rdf_operations(),
            "bindings": {key: composer.bindings.get(key, {}) for key in ("facts", "contracts", "situated_task_bindings")},
            "statements": statements,
            "source_sha256": {Path(name).relative_to(ROOT).as_posix(): digest
                              for name, digest in composer.fingerprints.items()
                              if Path(name).is_relative_to(ROOT) and name.endswith(".ttl")}}


def normalize(pilot):
    """Preserve legacy evidence without asserting undocumented equivalence."""
    v2 = "https://w3id.org/mado/experimental/v2#"
    native = "https://w3id.org/mado#"
    subclass = "http://www.w3.org/2000/01/rdf-schema#subClassOf"
    incompatible = {(v2 + "Contribution", subclass, native + "ContribuicaoNaArticulacao"),
                    (v2 + "ArticulationSupport", subclass, native + "ArticulacaoDocumentada")}
    kept, adapted = [], []
    for row in pilot.get("statements", []):
        target = adapted if (row["subject"], row["predicate"], row["object"]) in incompatible else kept
        target.append(row)
    pilot["statements"] = kept
    if adapted:
        pilot["schema_alignment"] = {
            "preserved_historical_assertions": adapted,
            "status": "REPRESENTATION_CORRECTION_NOT_NEW_DOCUMENT_REVIEW",
            "reason": "O piloto registra contribuições documentais diretas e sínteses delimitadas; não contém todos os metadados de curadoria nem entradas em conhecimentos exigidos pelas classes nativas. Não se presume equivalência de registros ou aprovação. Validação específica conserva fontes, escopo e premissas.",
        }
    return pilot


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--capture", type=Path)
    parser.add_argument("--import-capture", type=Path)
    parser.add_argument("--normalize-current", action="store_true")
    parser.add_argument("--complete-bindings", action="store_true", help="Preserve existing generic task refinements in the common catalogue")
    args = parser.parse_args()
    if args.capture:
        args.capture.write_text(json.dumps(capture(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    elif args.import_capture or args.normalize_current or args.complete_bindings:
        path = ROOT / "data/knowledge-base.json"
        data = json.loads(path.read_text(encoding="utf-8-sig"))
        pilot = json.loads(args.import_capture.read_text(encoding="utf-8")) if args.import_capture else data["pilot_catalogue"]
        if args.complete_bindings:
            original = json.loads((ROOT / "experimental/v2/trajectory-bindings.json").read_text(encoding="utf-8"))
            pilot["bindings"]["situated_task_bindings"] = original["situated_task_bindings"]
        data["pilot_catalogue"] = normalize(pilot)
        with path.open("w", encoding="utf-8", newline="\n") as target:
            target.write(json.dumps(data, ensure_ascii=False, indent=2) + "\n")
    else:
        parser.error("Choose --capture before runtime migration, or --import-capture afterwards.")
