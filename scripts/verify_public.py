"""Reproduce the public release's Python, RDF, SHACL and query checks.

Run: python -B scripts/verify_public.py

ROBOT/HermiT is not rerun here. Its prior successful report is accepted only
when it records exactly the SHA-256 of the current combined ontology. Generate
that report first with scripts/verify_reasoner.py when the ontology changes.
Browser/manual accessibility checks and expert review are separate evidence.
No visitor session, narrative, decision text or runtime RDF is written to disk.
"""

import argparse
from concurrent.futures import ThreadPoolExecutor
from contextlib import redirect_stderr, redirect_stdout
from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path
import platform
import os
import subprocess
import sys
import tempfile
import time
import traceback
import unittest
import warnings

ROOT = Path(__file__).resolve().parents[1]
sys.dont_write_bytecode = True
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "vendor"))


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def relative(path):
    return path.resolve().relative_to(ROOT).as_posix()


def redact(value):
    """Published diagnostics must not disclose this checkout's local path."""
    if isinstance(value, dict):
        return {key: redact(item) for key, item in value.items()}
    if isinstance(value, list):
        return [redact(item) for item in value]
    if isinstance(value, str):
        for prefix in (str(ROOT), ROOT.as_posix(), ROOT.as_uri()):
            value = value.replace(prefix + "\\", "").replace(prefix + "/", "")
            value = value.replace(prefix, ".")
        # Tracebacks may mention the Python runtime outside this repository.
        for prefix in (sys.prefix, str(Path(sys.executable).parent)):
            value = value.replace(prefix, "<PYTHON_RUNTIME>")
        return value
    return value


def source_hashes():
    files = set(ROOT.glob("*.py"))
    for folder, pattern in (
        ("ontology", "*.ttl"),
        ("ontology", "*.owl"),
        ("shapes", "*.ttl"),
        ("queries", "*.rq"),
        ("data", "*.json"),
        ("tests", "test_*.py"),
        ("scripts", "verify_*.py"),
        ("scripts", "migrate_*.py"),
    ):
        files.update((ROOT / folder).glob(pattern))
    # The situated path is public runtime, not merely an optional experiment.
    for folder, patterns in (("experimental/v2", ("*.py", "*.ttl", "trajectory-bindings.json")),
                             ("experimental/v2/extensions", ("*.ttl",)),
                             ("experimental/v2/tests", ("test_*.py",))):
        for pattern in patterns:
            files.update((ROOT / folder).glob(pattern))
    files.add(ROOT / "web/amado/bridge.py")
    return {relative(path): sha256(path) for path in sorted(files)}


def _run_test_suite(pattern="test_*.py", capture_console=False):
    stream = io.StringIO()
    def execute():
        suite = unittest.TestLoader().discover(str(ROOT / "tests"), pattern=pattern)
        return unittest.TextTestRunner(stream=stream, verbosity=2).run(suite)
    if capture_console:
        with redirect_stdout(stream), redirect_stderr(stream):
            result = execute()
    else:
        result = execute()
    return {
        "passed": result.wasSuccessful() and result.testsRun > 0,
        "discovery": "tests/test_*.py",
        "tests_run": result.testsRun,
        "failures": [{"test": str(test), "traceback": detail} for test, detail in result.failures],
        "errors": [{"test": str(test), "traceback": detail} for test, detail in result.errors],
        "skipped": [{"test": str(test), "reason": reason} for test, reason in result.skipped],
        "expected_failures": len(result.expectedFailures),
        "unexpected_successes": len(result.unexpectedSuccesses),
        "output": stream.getvalue(),
    }


def _run_test_file(path):
    """A fresh interpreter per file prevents cross-worker module/state leaks."""
    command = [sys.executable, "-B", str(Path(__file__).resolve()), "--_test-file", path.name]
    environment = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONDONTWRITEBYTECODE="1")
    try:
        process = subprocess.run(command, cwd=ROOT, env=environment, capture_output=True,
                                 text=True, encoding="utf-8", errors="replace", check=False)
        record = json.loads(process.stdout)
        for key in ("passed", "tests_run", "failures", "errors", "skipped",
                    "expected_failures", "unexpected_successes", "output"):
            if key not in record:
                raise ValueError(f"Worker result has no {key}")
        if process.returncode not in (0, 1) or (process.returncode == 0) != bool(record["passed"]):
            raise ValueError(f"Worker exit {process.returncode} disagrees with its result")
        if process.stderr:
            record["output"] += "\nWorker stderr:\n" + process.stderr
        return record
    except Exception:
        detail = traceback.format_exc()
        if "process" in locals():
            detail += "\nWorker stdout:\n" + process.stdout + "\nWorker stderr:\n" + process.stderr
        return {"passed": False, "tests_run": 0, "failures": [],
                "errors": [{"test": path.name, "traceback": detail}], "skipped": [],
                "expected_failures": 0, "unexpected_successes": 0, "output": detail}


def run_unit_tests(jobs=1, pattern="test_*.py"):
    if jobs == 1:
        return _run_test_suite(pattern)
    files = sorted((ROOT / "tests").glob(pattern))
    # executor.map preserves filename order in the report, regardless of finish order.
    with ThreadPoolExecutor(max_workers=jobs) as pool:
        records = list(pool.map(_run_test_file, files))
    report = {"passed": bool(records) and all(row["passed"] for row in records),
              "discovery": "tests/" + pattern, "jobs": jobs,
              "isolation": "ONE_PYTHON_SUBPROCESS_PER_TEST_FILE",
              "files_run": len(files)}
    for key in ("tests_run", "expected_failures", "unexpected_successes"):
        report[key] = sum(row[key] for row in records)
    for key in ("failures", "errors", "skipped"):
        report[key] = [entry for row in records for entry in row[key]]
    report["output"] = "\n".join(f"=== {path.name} ===\n{row['output']}"
                                 for path, row in zip(files, records))
    report["per_file"] = [{"file": path.name, "passed": row["passed"],
                           "tests_run": row["tests_run"]} for path, row in zip(files, records)]
    return report


def validate_graph(graph, shapes):
    from pyshacl import validate
    from rdflib import RDF, Namespace

    sh = Namespace("http://www.w3.org/ns/shacl#")
    conforms, report_graph, _ = validate(
        graph,
        shacl_graph=shapes,
        inference="none",
        allow_warnings=True,
        allow_infos=True,
        abort_on_first=False,
        advanced=True,
    )
    findings = []
    for node in report_graph.subjects(RDF.type, sh.ValidationResult):
        findings.append({
            "severity": str(report_graph.value(node, sh.resultSeverity)),
            "focus": str(report_graph.value(node, sh.focusNode) or ""),
            "path": str(report_graph.value(node, sh.resultPath) or ""),
            "constraint": str(report_graph.value(node, sh.sourceConstraintComponent) or ""),
            "messages": sorted(str(message) for message in report_graph.objects(node, sh.resultMessage)),
        })
    findings.sort(key=lambda row: (row["severity"], row["focus"], row["path"], str(row["messages"])))
    counts = {
        name: sum(row["severity"] == str(sh[name]) for row in findings)
        for name in ("Violation", "Warning", "Info")
    }
    return {
        "passed": bool(conforms) and counts["Violation"] == 0,
        "conforms_with_documentary_warnings_allowed": bool(conforms),
        "inference": "none",
        "data_triples": len(graph),
        "shape_triples": len(shapes),
        "violations": counts["Violation"],
        "warnings": counts["Warning"],
        "infos": counts["Info"],
        "findings": findings,
    }


def reasoner_evidence(report_path, combined_path):
    report = json.loads(report_path.read_text(encoding="utf-8-sig"))
    matching_hash = report.get("input_sha256") == sha256(combined_path)
    public_paths = report.get("path_redaction", {}).get("applied") is True
    passed = all((
        report.get("passed") is True,
        report.get("profile_passed") is True,
        report.get("consistency_passed") is True,
        report.get("input_unchanged_during_check") is True,
        report.get("profile", {}).get("exit_code") == 0,
        report.get("hermit", {}).get("exit_code") == 0,
        matching_hash,
        public_paths,
    ))
    return {
        "passed": passed,
        "report": relative(report_path),
        "report_sha256": sha256(report_path),
        "input_sha256": report.get("input_sha256"),
        "matches_current_combined_graph": matching_hash,
        "checked_at_utc": report.get("checked_at_utc"),
        "profile_passed": report.get("profile_passed"),
        "consistency_passed": report.get("consistency_passed"),
        "path_redaction_applied": public_paths,
        "java_version": report.get("java", {}).get("stderr", "").strip(),
        "robot_version": report.get("robot", {}).get("stdout", "").strip(),
        "reasoner_rerun": False,
        "policy": "A changed graph requires a fresh successful reasoner report; this check never treats an older result as approval of different bytes.",
    }


def runtime_check(shapes):
    from engine import DecisionEngine, MADO
    from rdflib import RDF

    engine = DecisionEngine()
    engine.start_context("CTX-TRANSFERENCIA-RECURSO-DIGITAL-01")
    engine.update_context({"mapping_confirmed": True, "transfer_confirmed": True})
    result = engine.generate()
    runtime = engine.build_decision_graph(result)
    combined = engine.graph + runtime
    check = validate_graph(combined, shapes)
    query_counts = result["query_summary"]
    check.update({
        "context": engine.current["context"]["id"],
        "decision_status": result["decision"]["status"],
        "runtime_triples": len(runtime),
        "runtime_configurations": len(set(runtime.subjects(RDF.type, MADO.ConfiguracaoModalDaDecisao))),
        "runtime_criterion_applications": len(set(runtime.subjects(RDF.type, MADO.AplicacaoDeCriterio))),
        "query_rows": query_counts,
        "all_eight_queries_executed": {f"CQ-{i:03d}" for i in range(1, 9)} <= set(query_counts),
        "all_current_queries_executed": set(query_counts) == set(engine.queries),
        "execution_scope": "LEGACY_SELECTOR_COMPATIBILITY_NOT_SITUATED_COMPOSER",
        "persisted_runtime_graph": False,
    })
    check["coverage_not_claimed_complete"] = check["decision_status"] in {"GERADA", "GERADA_PARCIAL"}
    check["passed"] = check["passed"] and check["coverage_not_claimed_complete"] and check["runtime_configurations"] > 0 and check["runtime_criterion_applications"] > 0 and check["all_eight_queries_executed"] and check["all_current_queries_executed"]
    return check


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", default="evidence/technical-report.json")
    parser.add_argument("--reasoner-report", default="evidence/reasoner-report.json")
    parser.add_argument("--jobs", type=int, default=1,
                        help="Run unittest files in N isolated Python processes (default: serial).")
    parser.add_argument("--_test-file", help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.jobs < 1:
        parser.error("--jobs must be at least 1.")
    if args._test_file is not None:
        name = args._test_file
        path = ROOT / "tests" / name
        if Path(name).name != name or not name.startswith("test_") or not name.endswith(".py") or not path.is_file():
            parser.error("The worker requires an existing tests/test_*.py filename.")
        temporary = ROOT / "tmp" / "verification-workers"
        temporary.mkdir(parents=True, exist_ok=True)
        tempfile.tempdir = str(temporary)
        warnings.filterwarnings("ignore", category=DeprecationWarning)
        record = _run_test_suite(name, capture_console=True)
        print(json.dumps(record, ensure_ascii=False))
        return 0 if record["passed"] else 1
    report_path = (ROOT / args.report).resolve()
    reasoner_path = (ROOT / args.reasoner_report).resolve()
    if not report_path.is_relative_to(ROOT) or not reasoner_path.is_relative_to(ROOT):
        parser.error("Reports must remain inside this project.")
    warnings.filterwarnings("ignore", category=DeprecationWarning)
    started = time.monotonic()
    before = source_hashes()
    report = {
        "checked_at_utc": datetime.now(timezone.utc).isoformat(),
        "scope": "PUBLIC_RELEASE_PYTHON_RDF_SHACL_AND_RUNTIME_QUERIES",
        "limits": [
            "Technical verification does not establish expert approval, educational outcomes or generalization.",
            "Unittest checks are not browser/manual accessibility verification.",
            "A query returning rows does not by itself establish semantic adequacy; exact support and exclusions have separate regression assertions.",
            "No visitor data, generated decision text or runtime RDF is retained by this report.",
        ],
        "versions": {"python": platform.python_version(), "platform": platform.system()},
        "source_sha256": before,
        "checks": {},
    }

    def check(name, action):
        check_started = time.monotonic()
        try:
            record = action()
        except Exception as error:
            record = {"passed": False, "error_type": type(error).__name__, "error": str(error), "traceback": traceback.format_exc()}
        record["elapsed_seconds"] = round(time.monotonic() - check_started, 3)
        report["checks"][name] = record
        print(f"{name}: {'PASS' if record.get('passed') else 'FAIL'}", flush=True)

    check("unittest", lambda: run_unit_tests(args.jobs))
    combined_path = ROOT / "ontology" / "mado-combined.ttl"
    try:
        import pyshacl
        import rdflib
        import engine

        report["versions"].update({"rdflib": rdflib.__version__, "pyshacl": pyshacl.__version__, "ontology": engine.VERSION, "executor": engine.UI_VERSION})
        shapes = rdflib.Graph().parse(ROOT / "shapes" / "main.shacl.ttl", format="turtle")
        graph = rdflib.Graph().parse(combined_path, format="turtle")
        report["graph_counts"] = {
            "triples": len(graph),
            "classes": len(set(graph.subjects(rdflib.RDF.type, rdflib.OWL.Class))),
            "object_properties": len(set(graph.subjects(rdflib.RDF.type, rdflib.OWL.ObjectProperty))),
            "data_properties": len(set(graph.subjects(rdflib.RDF.type, rdflib.OWL.DatatypeProperty))),
        }
        check("public_base_shacl", lambda: validate_graph(graph, shapes))
        check("runtime_main_decision_shacl_and_queries", lambda: runtime_check(shapes))
    except Exception as error:
        report["checks"]["rdf_and_runtime_loading"] = {"passed": False, "error_type": type(error).__name__, "error": str(error), "traceback": traceback.format_exc()}
    check("reasoner_prior_evidence", lambda: reasoner_evidence(reasoner_path, combined_path))
    after = source_hashes()
    changed = sorted(key for key in set(before) | set(after) if before.get(key) != after.get(key))
    report["checks"]["source_unchanged_during_check"] = {"passed": not changed, "changed_files": changed}
    report["passed"] = all(item.get("passed") for item in report["checks"].values())
    report["elapsed_seconds"] = round(time.monotonic() - started, 3)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(redact(report), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"passed": report["passed"], "report": relative(report_path), "elapsed_seconds": report["elapsed_seconds"]}))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
