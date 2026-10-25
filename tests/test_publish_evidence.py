"""Small isolated tests of the label-only evidence gate; no engine or base loaded."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("publish_evidence_gate", ROOT / "scripts/publish_evidence.py")
PUBLISHER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PUBLISHER)
TRACE_SPEC = importlib.util.spec_from_file_location("traceability_publisher", ROOT / "scripts/publish_traceability.py")
TRACE_PUBLISHER = importlib.util.module_from_spec(TRACE_SPEC)
TRACE_SPEC.loader.exec_module(TRACE_PUBLISHER)
SHA = lambda data: hashlib.sha256(data).hexdigest()


class NavigationEvidenceGateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="mado-nav-gate-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        old_root = PUBLISHER.ROOT
        self.addCleanup(setattr, PUBLISHER, "ROOT", old_root)
        PUBLISHER.ROOT = self.root
        self.manifest = {"core_sha256": "engine", "bridge_sha256": "bridge", "base_zip_sha256": "base",
                         "files": {"data/knowledge-base.json": "data", "queries/CQ-001.rq": "query"},
                         "runtime": {}, "license_notices": {},
                         "frontend_sha256": {name: "" for name in (
                             "index.html", "guiado.html", "app.js", "guided.js", "styles.css", "guided.css", "views.css", "client.mjs", "worker.mjs")}}
        for name in PUBLISHER.navigation_required_paths(self.manifest):
            self.write(name, ("fixture:" + name).encode())
        self.old_html = b'<header><a href="../ontologia/">Modelo e arquivos</a></header>'
        current_html = self.old_html.replace(b">Modelo e arquivos</a>", ">Documentação técnica</a>".encode())
        for name in PUBLISHER.NAVIGATION_HTML:
            self.write(name, current_html)
        for name in self.manifest["frontend_sha256"]:
            self.manifest["frontend_sha256"][name] = PUBLISHER.digest(self.root / "web/amado" / name)
        previous_build = copy.deepcopy(self.manifest)
        for name in ("index.html", "guiado.html"):
            previous_build["frontend_sha256"][name] = SHA(self.old_html)
        self.browser = {"completed": True, "checks": {"real_historical_check": True}, "build": copy.deepcopy(previous_build)}
        self.guided = copy.deepcopy(self.browser)
        for name, value in (("browser-report.json", self.browser), ("guided-report.json", self.guided)):
            self.write("evidence/" + name, json.dumps(value).encode())
        self.report = {"change_kind": "NAVIGATION_LABEL_ONLY", "allowed_change": copy.deepcopy(PUBLISHER.NAVIGATION_CHANGE),
                       "completed": True, "baseline_commit": "fixture", "build": copy.deepcopy(self.manifest),
                       "checks": {key: True for key in PUBLISHER.NAVIGATION_CHECKS},
                       "unchanged_files": [{"file": name, "baseline_sha256": PUBLISHER.digest(self.root / name),
                                            "current_sha256": PUBLISHER.digest(self.root / name), "unchanged": True}
                                           for name in PUBLISHER.navigation_required_paths(self.manifest)],
                       "html_delta": [{"file": name, "baseline_sha256": SHA(self.old_html), "current_sha256": SHA(current_html),
                                       "only_navigation_label_changed": True} for name in PUBLISHER.NAVIGATION_HTML],
                       "historical_evidence": [{"reference": "fixture:evidence/" + name,
                                                "sha256": PUBLISHER.digest(self.root / "evidence" / name)}
                                               for name in ("browser-report.json", "guided-report.json")]}

    def write(self, name, content):
        target = self.root / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)

    def accepted(self):
        return PUBLISHER.navigation_delta_valid(self.report, self.manifest, self.browser, self.guided)

    def test_exact_label_only_change_passes(self):
        self.assertTrue(self.accepted())

    def test_additional_html_character_rejected_even_with_updated_current_hash(self):
        name = "web/amado/index.html"
        raw = (self.root / name).read_bytes() + b"!"
        self.write(name, raw)
        self.manifest["frontend_sha256"]["index.html"] = SHA(raw)
        self.report["build"] = copy.deepcopy(self.manifest)
        self.report["html_delta"][0]["current_sha256"] = SHA(raw)
        self.assertFalse(self.accepted())

    def test_javascript_byte_change_rejected(self):
        self.write("web/amado/app.js", b"changed")
        self.assertFalse(self.accepted())

    def test_historical_report_digest_change_rejected(self):
        name = "evidence/guided-report.json"
        self.write(name, (self.root / name).read_bytes() + b" ")
        self.assertFalse(self.accepted())

    def test_missing_protected_file_rejected(self):
        self.report["unchanged_files"] = [row for row in self.report["unchanged_files"] if row["file"] != "web/amado/worker.mjs"]
        self.assertFalse(self.accepted())


class PublicSituatedSummaryTests(unittest.TestCase):
    def test_isolated_writer_seals_both_files_without_approving_release(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            source = root / "full.json"
            original = json.dumps({"tests": {"count": 1, "success": True},
                                   "fixtures": {"reserved": "narrative"}}).encode()
            source.write_bytes(original)
            old_root = TRACE_PUBLISHER.ROOT
            TRACE_PUBLISHER.ROOT = root
            try:
                destination = root / "web/summary.json"
                record = TRACE_PUBLISHER.write_public_situated_summary("full.json", destination)
                self.assertEqual(record["sha256"], SHA(destination.read_bytes()))
                self.assertEqual(record["source_sha256"], SHA(original))
                self.assertEqual(source.read_bytes(), original)
                self.assertNotIn("passed", record)
                self.assertNotIn("evidence_use", record)
                with self.assertRaises(ValueError):
                    TRACE_PUBLISHER.write_public_situated_summary("full.json", source)
            finally:
                TRACE_PUBLISHER.ROOT = old_root

    def test_projection_excludes_inputs_ids_and_logs_without_changing_original(self):
        marker = "RESERVED_CASE_IDENTIFIER"
        report = {"schema_version": "fixture", "tests": {"count": 3, "success": True,
            "failures": 0, "errors": 0, "skipped": 0, "log": marker},
            "fixtures": {marker: "RESERVED_NARRATIVE"}, "summaries": {marker: {}},
            "results": {marker: "RESERVED_DECISION"}, "delta": {"complete_choices_with_relation": 2},
            "execution_cases": {marker: {"execution_shacl_conforms": True,
                "query_row_counts": {"EXEC-CQ-001": 4}, "input_kind": marker,
                "execution": {"counts": {"operations": 2}, "graph_sha256": "a" * 64,
                              "execution_iri": marker}}}}
        original = copy.deepcopy(report)
        projection = TRACE_PUBLISHER.public_situated_report(report, "evidence/full.json", "b" * 64)
        text = json.dumps(projection)
        self.assertEqual(report, original)
        for value in (marker, "RESERVED_NARRATIVE", "RESERVED_DECISION"):
            self.assertNotIn(value, text)
        self.assertEqual(projection["tests"]["count"], 3)
        self.assertEqual(projection["execution_checks"][0]["execution"]["graph_sha256"], "a" * 64)
        self.assertEqual(projection["projection"]["source_sha256"], "b" * 64)
        self.assertNotEqual(SHA(json.dumps(projection).encode()), SHA(json.dumps(report).encode()))

    def test_current_projection_contains_no_reserved_case_identifier_or_narrative(self):
        name = "experimental/v2/evidence/situated-report.json"
        source = (ROOT / name).read_bytes()
        report = json.loads(source)
        projection = TRACE_PUBLISHER.public_situated_report(report, name, SHA(source))
        text = json.dumps(projection, ensure_ascii=False)
        fixture = json.loads((ROOT / "tests/fixtures/articulation_transfer_cases.json").read_text(encoding="utf-8"))
        cases = fixture["cases"] if isinstance(fixture, dict) and "cases" in fixture else fixture
        if isinstance(cases, dict):
            cases = [{"id": identifier, **case} for identifier, case in cases.items()]
        for case in cases:
            self.assertNotIn(case["id"], text)
            self.assertNotIn(case["narrative"], text)
        self.assertEqual((ROOT / name).read_bytes(), source)
        self.assertEqual(len(projection["execution_checks"]), len(report["execution_cases"]))
        self.assertEqual(projection["tests"]["count"], report["tests"]["count"])


if __name__ == "__main__":
    unittest.main()
