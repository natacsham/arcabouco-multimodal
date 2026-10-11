"""Publication-policy tests, separate from the product/ontology test evidence.

Run explicitly: python -B tests/publish-gates.py
All mutations are synthetic fixtures inside an isolated temporary directory.
"""
import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

REPO = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("publication_gate", REPO / "scripts/publish_traceability.py")
gate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)


class PublicationGateTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(prefix="amado-publication-gate-")
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.override = patch.object(gate, "ROOT", self.root)
        self.override.start()
        self.addCleanup(self.override.stop)
        for name in ("engine.py", "web/amado/engine.py"):
            self.write(name, "same synthetic engine")
        self.write("web/amado/bridge.py", "synthetic bridge")
        self.write("web/amado/assets/base.zip", "synthetic bundle")
        self.write("data/knowledge-base.json", '{"synthetic":true}')
        self.write("web/amado/runtime/pyodide.mjs", "synthetic runtime")
        self.write("web/amado/runtime/licenses/README.md", "synthetic license")
        self.front = {name: "synthetic " + name for name in gate.UNUSED_SIMPLE_FLOW}
        self.front.update({"completo.html": '<script src="app.js"></script>',
                           "completo-guiado.html": '<script src="guided.js"></script>',
                           "app.js": "import './client.mjs';", "guided.js": "// preserved view",
                           "client.mjs": "new Worker('./worker.mjs');", "worker.mjs": "// preserved worker",
                           "styles.css": "body { color: black; }", "composition.js": "// preserved composition"})
        for name, content in self.front.items():
            self.write("web/amado/" + name, content)
        self.site = {"index.html": "synthetic home", "site.css": "body {color:black}",
                     "site.js": "// synthetic site", "source-path.js": "// synthetic source view",
                     "assets/source-catalog.json": '{"synthetic":true}'}
        for name, content in self.site.items():
            self.write("web/" + name, content)
        full_route = "await page.goto(base+'amado/'+(view==='index.html'?'completo.html':'completo-guiado.html'));"
        for name in gate.FULL_VIEW_TESTS.values():
            self.write(name, full_route)
        self.write("tests/compare_browser.mjs", "// synthetic exact comparator")
        self.write("evidence/native-cases.json", '{"synthetic":"native"}')
        self.write("tests/.artifacts/browser/decisions.json", '{"synthetic":"browser"}')
        self.manifest = {
            "version": "1.4.0-rc2", "origin_commit": "synthetic", "instrument": "AMADO",
            "core_sha256": gate.sha("engine.py"), "bridge_sha256": gate.sha("web/amado/bridge.py"),
            "base_zip_sha256": gate.sha("web/amado/assets/base.zip"), "pyodide_version": "synthetic",
            "runtime": {"pyodide.mjs": {"sha256": gate.sha("web/amado/runtime/pyodide.mjs")}},
            "license_notices": {"licenses/README.md": gate.sha("web/amado/runtime/licenses/README.md")},
            "composition": {"version": "synthetic"},
            "files": {"data/knowledge-base.json": gate.sha("data/knowledge-base.json")},
            "frontend_sha256": {name: gate.sha("web/amado/" + name) for name in self.front},
            "site_assets_sha256": {name: gate.sha("web/" + name) for name in self.site},
        }
        self.report = {"type": "SYNTHETIC_TECHNICAL_BROWSER_CHECK", "version": "1.4.0-rc2",
                       "build": copy.deepcopy(self.manifest), "completed": True, "errors": [],
                       "checks": {"synthetic": True}, "executed_at": "2026-10-11T00:00:00Z",
                       "test_sha256": gate.sha("tests/traceability-browser.mjs")}
        self.write("evidence/traceability-browser.json", json.dumps(self.report))

    def write(self, name, content):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    def change_front(self, name):
        self.write("web/amado/" + name, "changed " + name)
        self.manifest["frontend_sha256"][name] = gate.sha("web/amado/" + name)

    def reuse(self, report=None):
        return gate.preserved_components(report or self.report, self.manifest)

    def test_same_build_remains_current(self):
        result = self.reuse()
        self.assertTrue(result["passed"])
        self.assertEqual(result["evidence_use"], "CURRENT_BUILD_EXECUTION")

    def test_only_unused_entry_changes_allow_explicit_reuse_without_mutation(self):
        original = copy.deepcopy(self.report)
        for name in gate.UNUSED_SIMPLE_FLOW:
            self.change_front(name)
        result = self.reuse()
        self.assertTrue(result["passed"], result["checks"])
        self.assertEqual(result["evidence_use"], "REUSED_UNCHANGED_COMPONENTS")
        self.assertEqual(self.report, original)
        self.assertEqual(set(result["unconsumed_entry_changes"]), {"web/amado/" + n for n in gate.UNUSED_SIMPLE_FLOW})
        self.assertIn("web/amado/completo.html", result["used_inputs"])
        self.assertNotIn("web/amado/index.html", result["used_inputs"])

    def test_composition_has_its_own_exact_test(self):
        report = copy.deepcopy(self.report)
        report["type"] = "SYNTHETIC_COMPOSITION_BROWSER_NOT_HUMAN_EVALUATION"
        report["test_sha256"] = gate.sha("tests/composition-browser.mjs")
        self.change_front("simple-flow.css")
        self.assertTrue(self.reuse(report)["passed"])
        self.write("tests/composition-browser.mjs", "// changed test")
        self.assertFalse(self.reuse(report)["passed"])

    def test_changed_core_shared_ui_source_or_base_never_reuses(self):
        for name in ("engine.py", "web/amado/engine.py", "web/amado/bridge.py", "web/amado/assets/base.zip",
                     "web/amado/app.js", "web/amado/completo.html", "web/source-path.js",
                     "web/assets/source-catalog.json", "data/knowledge-base.json",
                     "web/amado/runtime/pyodide.mjs", "web/amado/runtime/licenses/README.md"):
            with self.subTest(name=name):
                previous = (self.root / name).read_bytes()
                self.change_front("simple-flow.css")
                self.write(name, "incompatible input")
                self.assertFalse(self.reuse()["passed"])
                (self.root / name).write_bytes(previous)

    def test_updated_manifest_cannot_authorize_changed_shared_inputs(self):
        self.change_front("app.js")
        result = self.reuse()
        self.assertFalse(result["passed"])
        self.assertFalse(result["checks"]["only_unconsumed_entry_hashes_may_differ"])

    def test_site_hash_change_is_not_an_unused_entry_change(self):
        self.write("web/source-path.js", "changed source renderer")
        self.manifest["site_assets_sha256"]["source-path.js"] = gate.sha("web/source-path.js")
        self.assertFalse(self.reuse()["passed"])

    def test_unknown_report_or_changed_test_fails_closed(self):
        self.change_front("intake.mjs")
        unknown = copy.deepcopy(self.report)
        unknown["type"] = "UNKNOWN_TEST"
        self.assertFalse(self.reuse(unknown)["passed"])
        self.write("tests/traceability-browser.mjs", "// changed test")
        self.assertFalse(self.reuse()["passed"])

    def test_test_must_navigate_complete_views(self):
        self.change_front("intake.mjs")
        self.write("tests/traceability-browser.mjs", "await page.goto(base+'amado/index.html');")
        self.report["test_sha256"] = gate.sha("tests/traceability-browser.mjs")
        self.assertFalse(self.reuse()["passed"])

    def test_imported_intake_is_not_treated_as_unused(self):
        self.write("web/amado/app.js", "import './intake.mjs';")
        digest = gate.sha("web/amado/app.js")
        self.manifest["frontend_sha256"]["app.js"] = digest
        self.report["build"]["frontend_sha256"]["app.js"] = digest
        self.change_front("intake.mjs")
        result = self.reuse()
        self.assertFalse(result["passed"])
        self.assertFalse(result["checks"]["unconsumed_modules_not_referenced"])

    def test_missing_complete_view_hash_does_not_infer_relocation_in_rc2(self):
        self.change_front("index.html")
        for manifest in (self.manifest, self.report["build"]):
            manifest["frontend_sha256"].pop("completo.html")
        self.assertFalse(self.reuse()["passed"])

    def test_legacy_rc1_relocation_is_preserved(self):
        report = copy.deepcopy(self.report)
        report["build"]["version"] = self.manifest["version"] = "1.4.0-rc1"
        legacy = {name: digest for name, digest in report["build"]["frontend_sha256"].items()
                  if name not in gate.UNUSED_SIMPLE_FLOW and name not in {"completo.html", "completo-guiado.html"}}
        legacy.update({"index.html": gate.sha("web/amado/completo.html"),
                       "guiado.html": gate.sha("web/amado/completo-guiado.html")})
        report["build"]["frontend_sha256"] = legacy
        result = self.reuse(report)
        self.assertTrue(result["passed"], result["checks"])
        self.assertEqual(result["relocated_views"]["web/amado/index.html"], "web/amado/completo.html")

    def parity(self):
        return {"build": copy.deepcopy(self.manifest), "passed": True,
                "test_sha256": gate.sha("tests/compare_browser.mjs"),
                "native_sha256": gate.sha("evidence/native-cases.json"),
                "browser_sha256": gate.sha("tests/.artifacts/browser/decisions.json")}

    def test_parity_checks_both_artifacts_and_does_not_claim_historical_seal(self):
        parity = self.parity()
        self.change_front("simple-flow.css")
        result = gate.parity_components(parity, self.report, self.manifest)
        self.assertTrue(result["passed"], result["checks"])
        self.assertFalse(result["artifact_hash_sealed_in_originating_report"])
        self.assertNotEqual(result["evidence_use"], "CURRENT_BUILD_EXECUTION")

    def test_changed_compared_artifact_invalidates_parity(self):
        parity = self.parity()
        for name in ("evidence/native-cases.json", "tests/.artifacts/browser/decisions.json"):
            with self.subTest(name=name):
                original = (self.root / name).read_bytes()
                self.write(name, "altered artifact")
                self.assertFalse(gate.parity_components(parity, self.report, self.manifest)["passed"])
                (self.root / name).write_bytes(original)

    def test_absent_browser_artifact_preserves_recorded_digest_without_claiming_check(self):
        parity = self.parity()
        (self.root / "tests/.artifacts/browser/decisions.json").unlink()
        result = gate.parity_components(parity, self.report, self.manifest)
        self.assertTrue(result["passed"], result["checks"])
        self.assertEqual(result["browser_artifact_verification"], "RECORDED_DIGEST_WITHOUT_ARTIFACT")
        self.assertFalse(result["browser_artifact_checked_directly"])
        self.assertFalse(result["artifact_hash_sealed_in_originating_report"])

    def test_absent_browser_artifact_still_requires_a_valid_recorded_digest(self):
        parity = self.parity()
        (self.root / "tests/.artifacts/browser/decisions.json").unlink()
        for digest in (None, "", "not-a-sha256"):
            with self.subTest(digest=digest):
                parity["browser_sha256"] = digest
                self.assertFalse(gate.parity_components(parity, self.report, self.manifest)["passed"])

    def test_empty_originating_checks_cannot_approve_parity(self):
        self.report["checks"] = {}
        self.assertFalse(gate.parity_components(self.parity(), self.report, self.manifest)["passed"])

    def test_failed_originating_execution_invalidates_parity(self):
        self.report["completed"] = False
        self.assertFalse(gate.parity_components(self.parity(), self.report, self.manifest)["passed"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
