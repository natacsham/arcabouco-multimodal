"""Reproduce synthetic trajectory-bridge checks without changing the old base.

By default prints JSON; --output may write only a JSON report inside this
experiment's evidence directory. Never a participant log or a usability result.
"""
from __future__ import annotations

import argparse
import copy
from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path
import platform
import sys
import unittest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "vendor"))
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE / "tests"))

from rdflib.compare import to_isomorphic  # noqa: E402
from rdflib import Graph, Literal, RDF  # noqa: E402
from pyshacl import validate  # noqa: E402
from composer import V2, MADO  # noqa: E402
from trajectory import ResearchComposer, build_trajectory_graph  # noqa: E402
from test_trajectory import trajectory_context  # noqa: E402


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def local(value):
    return str(value).rsplit("#", 1)[-1].rsplit("/", 1)[-1]


def summary(result):
    def steps(choices):
        return [[local(step["id"]) for step in choice["steps"]] for choice in choices]
    evidence = result.get("trajectory_evidence", {})
    return {
        "status": result["status"], "proposal_status": result["proposal_status"],
        "compositions": steps(result["choices"]),
        "conditional_compositions": steps(result["pending_candidates"]),
        "partial_segments": [
            {"steps": [local(step["id"]) for step in segment["steps"]],
             "covered_functions": [local(row["id"]) for row in segment["covered_functions"]],
             "missing_functions": [local(row["id"]) for row in segment["missing_functions"]],
             "entry": segment["entry"], "ready_for_whole_task": segment["ready_for_whole_task"]}
            for segment in result["partial_segments"]
        ],
        "facts_to_confirm": result["facts_to_confirm"],
        "resources_to_confirm": result["resources_to_confirm"],
        "unavailable_conditions": result["unavailable_conditions"],
        "function_coverage": result["function_coverage"],
        "integration_gaps": result["integration_gaps"],
        "trajectory_records": [{"collection": row["collection"], "id": row["id"], "sha256": row["sha256"]}
                               for row in evidence.get("records", [])],
        "pending_trajectory_records": [{"collection": row["collection"], "id": row["id"], "sha256": row["sha256"], "usage": row["usage"]}
                                       for row in evidence.get("pending_records", [])],
        "partial_trajectory_records": [{"collection": row["collection"], "id": row["id"], "sha256": row["sha256"], "usage": row["usage"]}
                                       for row in evidence.get("partial_records", [])],
        "partial_trajectory_records": [{"collection": row["collection"], "id": row["id"], "sha256": row["sha256"],
                                        "usage": row["usage"]} for row in evidence.get("partial_records", [])],
        "pending_trajectory_records": [{"collection": row["collection"], "id": row["id"], "sha256": row["sha256"],
                                        "usage": row["usage"]} for row in evidence.get("pending_records", [])],
        "base_sha256": evidence.get("base_sha256"),
        "bindings_sha256": evidence.get("bindings_sha256"),
        "gaps": result["gaps"], "limits": result.get("limits", []),
    }


class RecordedTests(unittest.TextTestResult):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.successes = []

    def addSuccess(self, test):
        super().addSuccess(test)
        self.successes.append(test.id())


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, help="JSON dentro de experimental/v2/evidence; omitido imprime JSON.")
    args = parser.parse_args(argv)
    destination = args.output.resolve() if args.output else None
    if destination and (destination.suffix != ".json" or not destination.is_relative_to((HERE / "evidence").resolve())):
        parser.error("O relatório só pode ser gravado como JSON dentro de experimental/v2/evidence.")
    protected = sorted({ROOT / "engine.py", ROOT / "data/knowledge-base.json",
                        *ROOT.glob("ontology/*.ttl"), *ROOT.glob("queries/*.rq")})
    before = {path.relative_to(ROOT).as_posix(): digest(path) for path in protected}
    code_hashes = {path.relative_to(ROOT).as_posix(): digest(path)
                   for path in (HERE / "composer.py", HERE / "trajectory.py", HERE / "schema.ttl", HERE / "base.ttl",
                                HERE / "trajectory-bindings.json", HERE / "extensions/audio-review.ttl", HERE / "shapes.ttl")}
    original_context = trajectory_context()
    cases = []

    def add(identifier, mutation, expected_status, expected_steps, *, audio=True):
        case = copy.deepcopy(original_context)
        case["id"] = identifier
        mutation(case)
        result = ResearchComposer(include_audio=audio).compose(case)
        actual = summary(result)
        actual_steps = {tuple(row) for row in actual["compositions"]}
        expected = {"proposal_status": expected_status,
                    "compositions": [list(row) for row in sorted(expected_steps)]}
        passed = result["proposal_status"] == expected_status and actual_steps == set(expected_steps)
        cases.append({"id": identifier, "evidence_type": "synthetic", "context": case,
                      "include_audio_knowledge": audio, "expected": expected, "actual": actual, "passed": passed})
        return result

    complete = add("SYN-TRJ-NEW-071", lambda case: None, "COMPLETE", {("CaptureKeyboard", "ReviewSpeech")})
    add("SYN-TRJ-NEW-072", lambda case: None, "PARTIAL", set(), audio=False)

    def visual(case):
        case["resources"].update(AudioOutput=False, Display=True)
        case["facts"].update(AudioUsable=False, CanReviewVisualText=True)
    add("SYN-TRJ-NEW-073", visual, "COMPLETE", {("CaptureKeyboard", "ReviewText")})
    add("SYN-TRJ-NEW-074", lambda case: case["facts"].update(KeyboardEffortAcceptable=None), "CONDITIONAL", set())
    add("SYN-TRJ-NEW-075", lambda case: case["facts"].update(CanCorrect=False), "PARTIAL", set())
    add("SYN-TRJ-NEW-076", lambda case: case["facts"].update(CanUseKeyboard=False), "PARTIAL", set())

    stream = io.StringIO()
    suite = unittest.defaultTestLoader.discover(str(HERE / "tests"), pattern="test_*.py")
    tests = unittest.TextTestRunner(stream=stream, verbosity=2, resultclass=RecordedTests).run(suite)
    first_graph, second_graph = build_trajectory_graph(), build_trajectory_graph()
    reproducible = to_isomorphic(first_graph).graph_digest() == to_isomorphic(second_graph).graph_digest()
    shapes = Graph().parse(HERE / "shapes.ttl", format="turtle")
    shacl_ok, _, shacl_text = validate(first_graph, shacl_graph=shapes, inference="none", advanced=True)
    query_results = {}
    for name in ("grounding", "relations", "trajectory"):
        rows = list(first_graph.query((HERE / "queries" / f"{name}.rq").read_text(encoding="utf-8")))
        if name == "grounding":
            expected = {"TrajectoryGroundKeyboard", "TrajectoryGroundSpeech", "TrajectoryGroundTextReview", "TrajectoryGroundAudioReview"}
            passed = {local(row.application) for row in rows} == expected
        elif name == "relations":
            passed = len(rows) == 1 and str(rows[0].shared) == str(V2.TextDraft)
        else:
            passed = (len(rows) == 11 and {local(row.legacy) for row in rows} == {"K28", "K29", "K41"})
        query_results[name] = {"passed": passed, "row_count": len(rows),
                               "rows": [[str(value) for value in row] for row in rows]}
    negative_results = {}
    mutations = {
        "missing_legacy_locator": lambda graph: graph.remove((MADO["TD-EV29"], MADO.localizacaoDocumental, None)),
        "wrong_application_knowledge": lambda graph: graph.set((V2.TrajectoryGroundKeyboard, V2.knowledge, MADO.K28)),
        "primary_support_removed": lambda graph: [graph.set((node, V2.status, Literal("LEGACY_RECORD_ONLY")))
                                                   for node in list(graph.subjects(RDF.type, V2.Contribution))],
        "missing_capability_function": lambda graph: graph.remove((V2.CaptureKeyboard, V2.provides, None)),
    }
    for name, mutation in mutations.items():
        changed = Graph()
        for triple in first_graph:
            changed.add(triple)
        mutation(changed)
        valid, _, details = validate(changed, shacl_graph=shapes, inference="none", advanced=True)
        negative_results[name] = {"rejected": not bool(valid), "report": str(details)}
    combined = "\n".join(sorted(first_graph.serialize(format="nt").splitlines())) + "\n"
    combined_hash = hashlib.sha256(combined.encode("utf-8")).hexdigest()
    logical_path = HERE / "evidence/trajectory-reasoner-report.json"
    logical = {"status": "NOT_RUN", "required_before_release": True}
    if logical_path.is_file():
        saved = json.loads(logical_path.read_text(encoding="utf-8"))
        logical = {"report": "evidence/trajectory-reasoner-report.json",
                   "matches_current_graph": saved.get("input_sha256") == combined_hash,
                   "profile_passed": saved.get("profile_passed"),
                   "consistency_passed": saved.get("consistency_passed"),
                   "passed": saved.get("passed") is True and saved.get("input_sha256") == combined_hash}
        if destination:
            logical_path.write_text(json.dumps(saved, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    after = {path.relative_to(ROOT).as_posix(): digest(path) for path in protected}
    code_after = {name: digest(ROOT / name) for name in code_hashes}
    preserved = before == after and code_hashes == code_after
    report = {
        "artifact": "MADO V2 — ponte experimental para conhecimentos da trajetória",
        "checked_at_utc": datetime.now(timezone.utc).isoformat(),
        "tool": {"python": platform.python_version(), "command": "python -B experimental/v2/verify_trajectory.py"},
        "evidence_type": "synthetic_only",
        "scope": "Recombinação delimitada de capacidades existentes; não interpretação automática de narrativa, teste humano ou prova de benefício educacional.",
        "cases": cases,
        "trace_sample": complete.get("trajectory_evidence", {}),
        "graph": {"triples": len(first_graph), "isomorphism_digest": str(to_isomorphic(first_graph).graph_digest()),
                  "repeated_build_identical": reproducible, "serialized_sha256": combined_hash},
        "shacl": {"conforms": bool(shacl_ok), "report": str(shacl_text)},
        "queries": query_results,
        "negative_shacl": negative_results,
        "reasoner": logical,
        "tests": {"run": tests.testsRun, "passed": len(tests.successes), "successes": tests.successes,
                  "failures": [{"test": test.id(), "traceback": details} for test, details in tests.failures],
                  "errors": [{"test": test.id(), "traceback": details} for test, details in tests.errors],
                  "log": stream.getvalue()},
        "preservation": {"unchanged": preserved, "before": before, "after": after,
                         "experimental_code_before": code_hashes, "experimental_code_after": code_after},
        "not_performed_by_this_command": ["OWL 2 DL/HermiT run by separate verify_reasoner.py command", "human validation", "browser UI test"],
        "passed": (all(case["passed"] for case in cases) and tests.wasSuccessful() and reproducible and preserved
                   and bool(shacl_ok) and all(row["passed"] for row in query_results.values())
                   and all(row["rejected"] for row in negative_results.values())
                   and logical.get("passed", True)),
    }
    serialized = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if destination:
        destination.parent.mkdir(parents=True, exist_ok=True)
        (HERE / "evidence/trajectory-combined.ttl").write_text(combined, encoding="utf-8", newline="\n")
        first_graph.serialize(HERE / "evidence/trajectory-combined.owl", format="xml")
        destination.write_text(serialized, encoding="utf-8", newline="\n")
        print(json.dumps({"passed": report["passed"], "tests": tests.testsRun,
                          "cases_passed": sum(case["passed"] for case in cases),
                          "report": str(destination)}, ensure_ascii=True))
    else:
        print(serialized)
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
