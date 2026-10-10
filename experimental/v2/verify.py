"""Reproduce the V2 synthetic experiments; never write into the preserved base.

Generated evidence is limited to synthetic fixtures. This is not a session log
and must not be presented as evidence collected from a participant.
"""
from __future__ import annotations

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
sys.path.insert(0, str(ROOT / "vendor"))
sys.path.insert(0, str(HERE))
from rdflib import Graph, Literal, Namespace, RDF
from pyshacl import validate
from composer import Composer

V2 = Namespace("https://w3id.org/mado/experimental/v2#")
MADO = Namespace("https://w3id.org/mado#")
BASE = [HERE / "schema.ttl", HERE / "base.ttl"]
EXT = HERE / "extensions/audio-review.ttl"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


def relative_fingerprints(result):
    result = copy.deepcopy(result)
    result["fingerprints"] = {Path(k).relative_to(ROOT).as_posix(): v for k, v in result["fingerprints"].items()}
    return result


def summary(result):
    def local(value):
        return value.rsplit("#", 1)[-1]
    return {
        "status": result["status"],
        "compositions": [[local(step["id"]) for step in choice["steps"]] for choice in result["choices"]],
        "knowledge": sorted({local(support["knowledge"]["id"]) for choice in result["choices"]
                             for step in choice["steps"] for support in step["groundings"]}
                            | {local(relation["grounding"]["knowledge"]["id"])
                               for choice in result["choices"] for relation in choice["relations"]}),
        "pending": len(result["pending_candidates"]),
        "gaps": result["gaps"],
    }


class RecordedTests(unittest.TextTestResult):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.successes = []

    def addSuccess(self, test):
        super().addSuccess(test)
        self.successes.append(test.id())


def main():
    output = HERE / "evidence"
    output.mkdir(exist_ok=True)
    # Verify byte preservation during this run, independent of prior UI edits.
    protected = sorted({ROOT / "engine.py", *ROOT.glob("ontology/*.ttl"),
                        *ROOT.glob("queries/*.rq"), ROOT / "data/knowledge-base.json"})
    before = {str(p.relative_to(ROOT)).replace("\\", "/"): digest(p) for p in protected if p.is_file()}
    base, extended = Composer(BASE), Composer([*BASE, EXT])
    shapes = Graph().parse(HERE / "shapes.ttl", format="turtle")
    report = {"version": "2.0.0-alpha1", "checked_at_utc": datetime.now(timezone.utc).isoformat(),
              "scope": "Synthetic pilot; no participant session, UI replacement or empirical effectiveness claim.",
              "shacl": {}, "queries": {}, "negative_shacl": {}}
    checks = []
    for name, composer in (("base", base), ("extended", extended)):
        passed, _, details = validate(composer.graph, shacl_graph=shapes, inference="none", advanced=True)
        report["shacl"][name] = {"conforms": bool(passed), "report": str(details), "triples": len(composer.graph)}
        checks.append(bool(passed))
        for query, expected in (("grounding", 9 if name == "base" else 11), ("relations", 1)):
            rows = list(composer.graph.query((HERE / "queries" / f"{query}.rq").read_text(encoding="utf-8")))
            key = f"{name}/{query}"
            report["queries"][key] = {"expected_rows": expected, "actual_rows": len(rows), "passed": len(rows) == expected,
                                      "rows": [[str(value) for value in row] for row in rows]}
            checks.append(len(rows) == expected)
    mutations = {
        "missing_source": lambda g: g.remove((V2.ExcerptMMI, MADO.trechoDeFonte, None)),
        "missing_locator": lambda g: g.remove((V2.ExcerptMMI, MADO.localizacaoDocumental, None)),
        "wrong_knowledge": lambda g: g.set((V2.GroundAudioReview, V2.knowledge, V2.KInput)),
        "missing_function": lambda g: g.remove((V2.ReviewSpeech, V2.provides, None)),
        "legacy_only": lambda g: [g.set((c, V2.status, Literal("LEGACY_RECORD_ONLY")))
                                   for c in list(g.subjects(V2.inArticulation, V2.ArtAudioReview))],
        "missing_relation_content": lambda g: g.remove((V2.ProductionThenReview, V2.sharedType, None)),
    }
    for name, mutation in mutations.items():
        graph = Graph()
        for triple in extended.graph:
            graph.add(triple)
        mutation(graph)
        conforms, _, details = validate(graph, shacl_graph=shapes, inference="none", advanced=True)
        report["negative_shacl"][name] = {"rejected": not bool(conforms), "report": str(details)}
        checks.append(not conforms)

    speech = json.loads((HERE / "examples/speech-visual.json").read_text(encoding="utf-8"))
    novel = json.loads((HERE / "examples/keyboard-audio.json").read_text(encoding="utf-8"))
    unavailable = copy.deepcopy(novel)
    unavailable["resources"]["AudioOutput"] = False
    unknown = copy.deepcopy(novel)
    unknown["facts"]["CanCorrect"] = None
    all_available = copy.deepcopy(novel)
    all_available["resources"] = {key: True for key in novel["resources"]}
    all_available["facts"] = {key: True for key in novel["facts"]}
    runs = {
        "speech_visual_base": base.compose(speech),
        "new_conjunction_base": base.compose(novel),
        "new_conjunction_extended": extended.compose(novel),
        "new_conjunction_removed_extension": Composer(BASE).compose(novel),
        "new_conjunction_audio_prevented": extended.compose(unavailable),
        "new_conjunction_correction_unknown": extended.compose(unknown),
        "all_available_base": base.compose(all_available),
        "all_available_extended": extended.compose(all_available),
    }
    expected = {"speech_visual_base": ("COMPOSED", 1), "new_conjunction_base": ("INSUFFICIENT", 0),
                "new_conjunction_extended": ("COMPOSED", 1), "new_conjunction_removed_extension": ("INSUFFICIENT", 0),
                "new_conjunction_audio_prevented": ("INSUFFICIENT", 0), "new_conjunction_correction_unknown": ("INSUFFICIENT", 0),
                "all_available_base": ("COMPOSED", 2), "all_available_extended": ("COMPOSED", 4)}
    report["experiments"] = {}
    for name, result in runs.items():
        passed = (result["status"], len(result["choices"])) == expected[name]
        report["experiments"][name] = {**summary(result), "expected": list(expected[name]), "passed": passed}
        checks.append(passed)
    report["experimental_design"] = {
        "composer_sha256": digest(HERE / "composer.py"),
        "added": "Conhecimento KAudioReview, sua articulação, contribuições localizadas e aplicação exata à capacidade já declarada.",
        "unchanged": ["motor", "capacidades", "funções", "tarefas", "ações unitárias", "regra de sequência"],
        "limit": "Experimento de habilitação por fundamento, não extração automática, descoberta de capacidade ou prova de melhor orientação.",
    }
    stream = io.StringIO()
    suite = unittest.defaultTestLoader.discover(str(HERE / "tests"), pattern="test_*.py")
    result = unittest.TextTestRunner(stream=stream, verbosity=2, resultclass=RecordedTests).run(suite)
    report["unit_tests"] = {"run": result.testsRun, "passed": result.wasSuccessful(),
                            "successes": result.successes,
                            "failures": [{"test": t.id(), "message": err} for t, err in result.failures + result.errors],
                            "skipped": len(result.skipped)}
    checks.append(result.wasSuccessful() and not result.skipped)
    report["preserved_files"] = before
    report["preserved_files_unchanged"] = all(digest(ROOT / path) == hash_value for path, hash_value in before.items())
    checks.append(report["preserved_files_unchanged"])
    # Stable sorted N-Triples is also valid Turtle and avoids blank-node churn.
    combined = "\n".join(sorted(extended.graph.serialize(format="nt").splitlines())) + "\n"
    (output / "combined.ttl").write_text(combined, encoding="utf-8", newline="\n")
    extended.graph.serialize(output / "combined.owl", format="xml")
    reasoner_file = output / "reasoner-report.json"
    if reasoner_file.is_file():
        logical = json.loads(reasoner_file.read_text(encoding="utf-8"))
        # Normalize line endings only; preserve measured values and timestamps.
        write_json(reasoner_file, logical)
        matches = logical.get("input_sha256") == digest(output / "combined.ttl")
        report["reasoner"] = {"report": "evidence/reasoner-report.json", "matches_current_graph": matches,
                              "profile_passed": logical.get("profile_passed"),
                              "consistency_passed": logical.get("consistency_passed"),
                              "checked_at_utc": logical.get("checked_at_utc")}
        checks.append(matches and logical.get("passed") is True)
    else:
        report["reasoner"] = {"status": "NOT_RUN", "required_before_release": True}
    report["passed"] = all(checks)
    write_json(output / "novel-case-trace.json", relative_fingerprints(runs["new_conjunction_extended"]))
    write_json(output / "verification.json", report)
    manifest_files = sorted(p for p in HERE.rglob("*") if p.is_file()
                            and "__pycache__" not in p.parts and p.name != "manifest.json")
    write_json(output / "manifest.json", {"version": "2.0.0-alpha1", "files": {
        p.relative_to(HERE).as_posix(): digest(p) for p in manifest_files}})
    print(json.dumps({"passed": report["passed"], "unit_tests": result.testsRun,
                      "shacl": {k: v["conforms"] for k, v in report["shacl"].items()},
                      "experiments": {k: v["status"] for k, v in report["experiments"].items()},
                      "report": "experimental/v2/evidence/verification.json"}))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
