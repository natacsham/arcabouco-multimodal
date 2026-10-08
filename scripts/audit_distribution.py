"""Fail closed when the Git publication inventory contains withheld material."""
import hashlib
import io
import json
from pathlib import Path
import re
import subprocess
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "vendor"))
from rdflib import Graph, Literal, Namespace

M = Namespace("https://w3id.org/mado#")
PROTECTED = (M.conteudoDoTrecho, M.textoItemOriginal, M.textoDoItemOriginal)


def main():
    tracked = subprocess.check_output(["git", "ls-files", "-z"], cwd=ROOT).decode().split("\0")
    tracked = [name for name in tracked if name]
    findings, rdf_files, zip_entries = [], {}, []

    def inspect(name, contents):
        suffix = Path(name).suffix
        if suffix in (".ttl", ".owl", ".rdf"):
            graph = Graph().parse(data=contents, format="turtle" if suffix == ".ttl" else "xml")
            protected = sum(1 for predicate in PROTECTED for obj in graph.objects(None, predicate) if isinstance(obj, Literal) and str(obj).strip())
            rdf_files[name] = {"sha256": hashlib.sha256(contents).hexdigest(), "triples": len(graph), "withheld_content_literals": protected}
            if protected:
                findings.append({"file": name, "reason": "WITHHELD_CONTENT_LITERAL", "count": protected})
        if suffix == ".json" and "knowledge-base" in name:
            data = json.loads(contents)
            if not data.get("metadata", {}).get("public_projection"):
                findings.append({"file": name, "reason": "NOT_PUBLIC_PROJECTED"})
            if any(row.get("trecho") for row in data.get("excerpts", [])):
                findings.append({"file": name, "reason": "ORIGINAL_EXCERPT_TEXT"})
        if not name.startswith(("vendor/", "web/amado/runtime/")) and suffix in (".json", ".ttl", ".owl", ".html", ".md"):
            text = contents.decode("utf-8", errors="replace")
            if re.search(r"[A-Za-z]:[\\/](?:Users|CodexAudit)", text):
                findings.append({"file": name, "reason": "PRIVATE_ABSOLUTE_PATH"})
            if re.search(r"(?:ghp_|github_pat_)[A-Za-z0-9_]{20,}", text):
                findings.append({"file": name, "reason": "CREDENTIAL_PATTERN"})

    for name in tracked:
        if name == "ontology/data.ttl" or name.startswith(("evidence/private/", "sessions/", "exports/", "curation/")):
            findings.append({"file": name, "reason": "PRIVATE_OR_LEGACY_PATH"})
        contents = (ROOT / name).read_bytes()
        if not name.startswith(("vendor/", "web/amado/runtime/")):
            inspect(name, contents)
        if name == "web/amado/assets/base.zip":
            with zipfile.ZipFile(io.BytesIO(contents)) as package:
                for entry in package.namelist():
                    zip_entries.append(entry)
                    if entry.startswith("vendor/"):
                        continue
                    if entry == "ontology/data.ttl" or entry.startswith(("sessions/", "exports/", "curation/")):
                        findings.append({"file": name + ":" + entry, "reason": "PRIVATE_BUNDLE_ENTRY"})
                    inspect(name + ":" + entry, package.read(entry))
    report = {
        "scope": "TRACKED_PUBLIC_FILES_AND_BROWSER_BUNDLE",
        "tracked_file_count": len(tracked), "browser_bundle_entries": len(zip_entries),
        "rdf_files": rdf_files, "findings": findings, "passed": not findings,
        "limits": ["Structural and pattern checks do not replace documentary rights review or guarantee absence of every identifying inference."],
    }
    (ROOT / "evidence/distribution-audit.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"passed": report["passed"], "tracked_files": len(tracked), "findings": findings}))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
