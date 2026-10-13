"""Reproduce situated-composition experiments on explicitly synthetic cases.

No empirical observation, human approval or source re-reading is inferred.
The only optional output is an evidence JSON under experimental/v2/evidence.
"""
from __future__ import annotations

import argparse
import copy
from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path
import sys
import unittest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

from experimental.v2.trajectory import ResearchComposer
from experimental.v2.composer import V2
from rdflib import RDF
import test_situated_composition as checks


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def public_paths(value):
    """Publish reproducible fingerprints without disclosing the host workspace."""
    if isinstance(value, dict):
        result = {}
        for key, item in value.items():
            if key == "fingerprints" and isinstance(item, dict):
                result[key] = {Path(name).relative_to(ROOT).as_posix() if Path(name).is_absolute() else name: digest
                               for name, digest in item.items()}
            else:
                result[key] = public_paths(item)
        return result
    if isinstance(value, list):
        return [public_paths(item) for item in value]
    return value


def brief(result):
    def proposals(rows):
        return [{"id": p["id"], "participant_id": p["participant_id"], "situation_id": p["situation_id"],
                 "steps": [s["id"] for s in p["steps"]], "relations": [r["id"] for r in p["relations"]],
                 "ready_for_whole_task": p["ready_for_whole_task"], "covers_all_required_functions": p["covers_all_required_functions"]}
                for p in rows]
    return {"status": result["status"], "proposal_status": result["proposal_status"],
            "choices": proposals(result["choices"]), "conditional": proposals(result["pending_candidates"]),
            "partial": proposals(result["partial_segments"]),
            "required_functions": result["required_functions"], "restrictions": result["unavailable_conditions"],
            "integration_gaps": result["integration_gaps"], "search": result["search"],
            "execution_inputs": result["execution_inputs"]}


def build_report():
    protected = [ROOT / "data/knowledge-base.json", ROOT / "data/interface-vocabulary.json",
                 ROOT / "ontology/main.ttl", ROOT / "ontology/mado-combined.ttl", ROOT / "shapes/main.shacl.ttl",
                 ROOT / "engine.py", HERE / "composer.py", HERE / "trajectory.py", HERE / "trajectory-bindings.json",
                 HERE / "base.ttl", HERE / "schema.ttl", HERE / "extensions/audio-review.ttl", Path(checks.__file__).resolve()]
    before = {p.relative_to(ROOT).as_posix(): sha(p) for p in protected}
    context = checks.collaborative_unknown_context()
    composer = ResearchComposer(legacy_projection=False)
    original_context = copy.deepcopy(context)
    complete = composer.compose_context(context)
    changed = copy.deepcopy(context)
    changed["participations"][1]["facts"]["AudioUsable"] = False
    blocked = composer.compose_context(changed)
    unknown_context = copy.deepcopy(context)
    unknown_context["participations"][1]["facts"]["AudioUsable"] = None
    unknown = composer.compose_context(unknown_context)
    isolated_composer = ResearchComposer(legacy_projection=False)
    isolated_composer.graph.remove((V2.ProductionThenReview, RDF.type, V2.RelationRule))
    isolated = isolated_composer.compose_context(context)
    no_articulation_composer = ResearchComposer(legacy_projection=False)
    no_articulation_composer.graph.remove((V2.ArtReview, V2.operation, None))
    no_articulation = no_articulation_composer.compose_context(context)
    main_actions = copy.deepcopy(context)
    main_actions["situations"][0]["task_ids"] = ["TAR-PRODUZIR-CONTEUDO-MULTIMODAL", "TAR-REVISAR-E-CONFIRMAR"]
    for participant in main_actions["participations"]:
        participant["tarefa_ids"] = list(main_actions["situations"][0]["task_ids"])
        participant["facts"]["SameEditableTextDraft"] = True
    refined = composer.compose_context(main_actions)
    stream = io.StringIO()
    test_result = unittest.TextTestRunner(stream=stream, verbosity=2).run(unittest.defaultTestLoader.loadTestsFromModule(checks))
    after = {p.relative_to(ROOT).as_posix(): sha(p) for p in protected}
    results = {"articulated": complete, "audio_blocked_for_second_person": blocked,
               "audio_unknown_for_second_person": unknown, "without_relation_in_memory_only": isolated,
               "without_articulation_operation_in_memory_only": no_articulation,
               "attributed_main_actions_refined": refined}
    return {"schema_version": "2.0.0-alpha3", "checked_at_utc": datetime.now(timezone.utc).isoformat(),
            "evidence_kind": "SYNTHETIC_EXECUTION_NOT_EMPIRICAL_VALIDATION",
            "scope": "A mesma busca situada consome operações dos PAD e uma projeção das capacidades RDF já registradas; não existe inferência por nome do cenário.",
            "limits": ["As duas sequências individuais não comprovam coordenação ou entendimento compartilhado entre as pessoas.",
                       "A ligação produzir/conferir o mesmo rascunho é delimitada ao contrato RDF; não autoriza arestas arbitrárias entre PADs.",
                       "A condição contextual não substitui curadoria de fontes e os testes não representam avaliação humana."],
            "fixtures": {"complete": context, "blocked": changed, "unknown": unknown_context, "main_actions": main_actions},
            "source_hashes_before": before, "source_hashes_after": after,
            "source_files_unchanged": before == after, "input_context_unchanged": context == original_context,
            "tests": {"count": test_result.testsRun, "failures": len(test_result.failures), "errors": len(test_result.errors),
                      "skipped": len(test_result.skipped), "success": test_result.wasSuccessful(), "log": stream.getvalue()},
            "summaries": {name: brief(result) for name, result in results.items()}, "results": results,
            "delta": {"complete_choices_with_relation": len(complete["choices"]), "complete_choices_without_relation": len(isolated["choices"]),
                      "complete_choices_without_articulation_operation": len(no_articulation["choices"]),
                      "grounding_ablation": "As contribuições e fontes permanecem no grafo; somente a operação registrada de ArtReview é retirada em memória. Isso testa a obrigação estrutural da articulação, não seu efeito humano.",
                      "second_person_blocked_complete_choices": len(blocked["choices"]),
                      "first_person_sequence_preserved": any(p["participant_id"] == "p-voice" and p.get("covers_participant_situation")
                                                              for p in blocked["partial_segments"])}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = public_paths(build_report())
    if args.output:
        target = args.output.resolve()
        allowed = (HERE / "evidence").resolve()
        if target.parent != allowed or target.suffix.lower() != ".json":
            parser.error("A saída deve ser um arquivo JSON diretamente em experimental/v2/evidence.")
        allowed.mkdir(exist_ok=True)
        target.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf8", newline="\n")
        print(json.dumps({"output": str(target), "tests": report["tests"]["count"], "success": report["tests"]["success"],
                          "source_files_unchanged": report["source_files_unchanged"], "delta": report["delta"]}, ensure_ascii=False))
    else:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["tests"]["success"] and report["source_files_unchanged"] and report["input_context_unchanged"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
