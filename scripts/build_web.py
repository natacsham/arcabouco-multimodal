"""Build only approved public assets. Inputs must already be public-projected."""

import hashlib
import json
import re
import shutil
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "web"
APP = WEB / "amado"
COMPOSITION_FILES = (
    "experimental/v2/composer.py",
    "experimental/v2/trajectory.py",
    "experimental/v2/examples/learning-contribution.json",
)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build():
    data = json.loads((ROOT / "data/knowledge-base.json").read_text(encoding="utf-8"))
    if not data["metadata"].get("public_projection"):
        raise RuntimeError(
            "Public projection has not been prepared; refusing to bundle private research data."
        )
    if any(row.get("trecho") for row in data["excerpts"]):
        raise RuntimeError("Original excerpts must not enter the public bundle.")
    (APP / "assets").mkdir(exist_ok=True)
    downloads = WEB / "downloads"
    downloads.mkdir(exist_ok=True)
    paths = [
        ROOT / "execution_trace.py",
        ROOT / "situated_context.py",
        ROOT / "semantic_catalogue.py",
        ROOT / "semantic_execution.py",
        ROOT / "shapes/execution.shacl.ttl",
        ROOT / "data/interface-vocabulary.json",
        ROOT / "ontology/mado-combined.ttl",
    ] + sorted((ROOT / "queries").glob("CQ-*.rq")) + sorted((ROOT / "queries").glob("EXEC-CQ-*.rq"))
    # Explicit public allowlist: no reports, private records or runtime cases.
    # Preserve this directory structure: the composer resolves its base from it.
    paths += [ROOT / name for name in COMPOSITION_FILES]
    version_match = re.search(r'owl:versionInfo\s+"([^"]+)"',
                              (ROOT / "experimental/v2/schema.ttl").read_text(encoding="utf-8"))
    if not version_match:
        raise RuntimeError("Composition schema must declare its own version.")
    executor_match = re.search(r'^UI_VERSION\s*=\s*"([^"]+)"',
                               (ROOT / "engine.py").read_text(encoding="utf-8"), re.MULTILINE)
    if not executor_match:
        raise RuntimeError("The instrument must declare its own revision.")
    for package in ("rdflib", "pyparsing", "html5rdf"):
        paths += [
            p
            for p in (ROOT / "vendor" / package).rglob("*")
            if p.is_file() and "__pycache__" not in p.parts and p.suffix != ".pyc"
        ]
        for info in (ROOT / "vendor").glob(package + "-*.dist-info"):
            paths += [p for p in info.rglob("*") if p.is_file()]
    with zipfile.ZipFile(APP / "assets/base.zip", "w", zipfile.ZIP_DEFLATED) as z:
        for path in sorted(paths):
            info = zipfile.ZipInfo(
                path.relative_to(ROOT).as_posix(), (2026, 10, 6, 0, 0, 0)
            )
            info.compress_type = zipfile.ZIP_DEFLATED
            z.writestr(info, path.read_bytes())
    shutil.copyfile(ROOT / "engine.py", APP / "engine.py")
    for source, dest in [
        ("ontology/main.ttl", "main.ttl"),
        ("ontology/mado-combined.ttl", "mado-public.ttl"),
        ("ontology/mado.owl", "mado.owl"),
        ("shapes/main.shacl.ttl", "main.shacl.ttl"),
        ("shapes/execution.shacl.ttl", "execution.shacl.ttl"),
    ]:
        shutil.copyfile(ROOT / source, downloads / dest)
    runtime = {
        p.name: {"bytes": p.stat().st_size, "sha256": sha(p)}
        for p in sorted((APP / "runtime").glob("*"))
        if p.is_file()
    }
    manifest = {
        "version": data["metadata"]["version"],
        "origin_commit": "d660b773ed08038a7a543205575a16fc22d2c1c2",
        "instrument": "AMADO",
        "executor_version": executor_match.group(1),
        "public_projection": True,
        "thesis_reference": "V21 / MADO 1.2.0-RC4 (preservada, não substituída)",
        "core_sha256": sha(APP / "engine.py"),
        "bridge_sha256": sha(APP / "bridge.py"),
        "base_zip_sha256": sha(APP / "assets/base.zip"),
        "pyodide_version": "314.0.7",
        "runtime": runtime,
        "license_notices": {
            p.relative_to(APP / "runtime").as_posix(): sha(p)
            for p in sorted((APP / "runtime/licenses").rglob("*")) if p.is_file()
        },
        "case_history": False,
        "llm": False,
        "composition": {
            "version": version_match.group(1),
            "implementation": "ResearchComposer",
            "case_storage": False,
            "files": {name: sha(ROOT / name) for name in COMPOSITION_FILES},
        },
        "frontend_sha256": {
            name: sha(APP / name)
            for name in ("index.html", "app.js", "styles.css", "worker.mjs", "client.mjs", "guiado.html", "guided.js", "guided.css", "views.css", "composition.js", "composition.css",
                         "simple-flow.js", "simple-flow.css", "voice.js", "intake.mjs", "situated-output.mjs", "completo.html", "completo-guiado.html")
        },
        "site_assets_sha256": {
            name: sha(WEB / name)
            for name in ("index.html", "ontologia/index.html", "site.css", "shell.css", "site.js", "sitemap.xml", "explanation.js", "explanation.css", "explanation-pilot.js", "assets/explanation-pilot.json", "source-path.js", "assets/source-catalog.json")
        },
        "files": {
            p.relative_to(ROOT).as_posix(): sha(p)
            for p in paths
            if "vendor" not in p.parts
        },
    }
    (APP / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (ROOT / "evidence/build-manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "version": manifest["version"],
                "bundle_bytes": (APP / "assets/base.zip").stat().st_size,
                "files": len(paths),
            }
        )
    )


if __name__ == "__main__":
    build()
