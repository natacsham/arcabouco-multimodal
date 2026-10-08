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


if __name__ == "__main__":
    unittest.main()
