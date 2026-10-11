"""Publish current presentation checks and explicitly qualified reusable evidence."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(name):
    return json.loads((ROOT / name).read_text(encoding="utf-8"))


def sha(name):
    return hashlib.sha256((ROOT / name).read_bytes()).hexdigest()


def preserved_components(report, manifest):
    """Require the exact tested inputs, including the preserved original views.

    The full build cannot match after replacing the two entry pages. Only those
    two paths may move; every prior runtime, base, engine and UI input must still
    match its recorded fingerprint. New presentation checks are required below.
    """
    previous = report.get("build") or {}
    required = ("version", "origin_commit", "core_sha256", "bridge_sha256",
                "base_zip_sha256", "pyodide_version", "runtime", "license_notices",
                "composition", "files")
    checks = {name: name in previous and previous[name] == manifest.get(name)
              for name in required}
    checks["core_file"] = previous.get("core_sha256") == sha("engine.py")
    checks["bridge_file"] = previous.get("bridge_sha256") == sha("web/amado/bridge.py")
    checks["bundle_file"] = previous.get("base_zip_sha256") == sha("web/amado/assets/base.zip")
    checks["base_files"] = bool(previous.get("files")) and all(
        (ROOT / name).is_file() and sha(name) == digest
        for name, digest in previous.get("files", {}).items())
    checks["runtime_files"] = bool(previous.get("runtime")) and all(
        (ROOT / "web/amado/runtime" / name).is_file()
        and sha("web/amado/runtime/" + name) == value.get("sha256")
        for name, value in previous.get("runtime", {}).items())
    old_views = {"index.html": "completo.html", "guiado.html": "completo-guiado.html"}
    front = previous.get("frontend_sha256") or {}
    checks["prior_ui_files"] = {"index.html", "guiado.html", "app.js", "worker.mjs", "client.mjs"} <= set(front) and all(
        (ROOT / "web/amado" / old_views.get(name, name)).is_file()
        and sha("web/amado/" + old_views.get(name, name)) == digest
        for name, digest in front.items())
    site = previous.get("site_assets_sha256") or {}
    checks["prior_shared_site_files"] = bool(site) and all(
        (ROOT / "web" / name).is_file() and sha("web/" + name) == digest
        for name, digest in site.items())
    return {"passed": all(checks.values()), "checks": checks,
            "evidence_use": "REUSED_UNCHANGED_COMPONENTS",
            "relocated_views": {"web/amado/" + name: "web/amado/" + path
                                for name, path in old_views.items()},
            "notice": "Resultados anteriores reutilizados somente para motor, base, ambiente de execução e apresentação completa preservados. Não são novas execuções da apresentação simplificada."}


def current_presentation(report, manifest):
    return (report.get("completed") is True and report.get("passed") is True
            and not report.get("errors") and bool(report.get("checks"))
            and all(report["checks"].values()) and report.get("build") == manifest
            and report.get("test_sha256") == sha("tests/simple-flow-browser.mjs"))


def main():
    manifest = read("web/amado/manifest.json")
    technical = read("evidence/technical-report.json")
    reasoner = read("evidence/reasoner-report.json")
    regression = read("evidence/regression-report.json")
    browser = read("evidence/traceability-browser.json")
    parity = read("evidence/parity-report.json")
    distribution = read("evidence/distribution-audit.json")
    composition = read("evidence/composition-browser.json")
    composition_model = read("experimental/v2/evidence/verification.json")
    composition_trajectory = read("experimental/v2/evidence/trajectory-report.json")
    composition_reasoner = read("experimental/v2/evidence/trajectory-reasoner-report.json")
    simple = read("evidence/simple-flow-browser.json")
    reused = {"traceability-browser.json": preserved_components(browser, manifest),
              "parity-report.json": preserved_components(parity, manifest),
              "composition-browser.json": preserved_components(composition, manifest)}
    checks = {
        "version": manifest["version"] == "1.4.0-rc1",
        "technical": technical.get("passed") is True,
        "reasoner": reasoner.get("passed") is True,
        "reasoner_current_graph": reasoner["input_sha256"] == sha("ontology/mado-combined.ttl"),
        "current_engine": technical["source_sha256"]["engine.py"] == manifest["core_sha256"] == sha("engine.py"),
        "current_trace_projection": technical["source_sha256"]["execution_trace.py"] == sha("execution_trace.py"),
        "all_technical_inputs_current": all(sha(name) == value for name, value in technical["source_sha256"].items()),
        "essential_technical_inputs_recorded": {"engine.py", "execution_trace.py", "data/knowledge-base.json", "ontology/mado-combined.ttl", "ontology/main.ttl", "shapes/main.shacl.ttl", "tests/test_contributions.py", "tests/test_execution_evidence.py", *[f"queries/CQ-{i:03d}.rq" for i in range(1,9)]} <= set(technical["source_sha256"]),
        "all_bundle_inputs_current": all(sha(name) == value for name, value in manifest["files"].items()),
        "regression": all(regression["checks"].values()),
        "regression_current_base": regression["base_sha256"]["knowledge-base.json"] == sha("data/knowledge-base.json"),
        "browser": browser.get("completed") is True and not browser.get("errors") and bool(browser.get("checks")) and all(browser["checks"].values()),
        "browser_preserved_components": reused["traceability-browser.json"]["passed"],
        "browser_current_test": browser.get("test_sha256") == sha("tests/traceability-browser.mjs"),
        "parity": parity.get("passed") is True,
        "parity_preserved_components": reused["parity-report.json"]["passed"],
        "parity_current_native": parity["native_sha256"] == sha("evidence/native-cases.json"),
        "parity_current_test": parity.get("test_sha256") == sha("tests/compare_browser.mjs"),
        "distribution": distribution.get("passed") is True,
        "distribution_files_current": bool(distribution.get("distribution_sha256")) and all(sha(name) == value for name, value in distribution.get("distribution_sha256", {}).items()),
        "composition_browser": composition.get("passed") is True and bool(composition.get("checks")) and all(composition["checks"].values()),
        "composition_preserved_components": reused["composition-browser.json"]["passed"],
        "composition_current_test": composition.get("test_sha256") == sha("tests/composition-browser.mjs"),
        "composition_model": composition_model.get("passed") is True and composition_trajectory.get("passed") is True,
        "composition_reasoner": composition_reasoner.get("passed") is True and composition_reasoner.get("input_sha256") == sha("experimental/v2/evidence/trajectory-combined.ttl"),
        "simple_flow_current_presentation": current_presentation(simple, manifest),
        "current_frontend_files": bool(manifest.get("frontend_sha256")) and all(
            sha("web/amado/" + name) == value for name, value in manifest.get("frontend_sha256", {}).items()),
    }
    if not all(checks.values()):
        raise SystemExit(json.dumps(checks))
    reports = ["technical-report.json", "reasoner-report.json", "regression-report.json", "traceability-browser.json", "parity-report.json", "distribution-audit.json", "build-manifest.json", "composition-browser.json", "simple-flow-browser.json"]
    target = ROOT / "web/evidence"
    target.mkdir(exist_ok=True)
    summary = {
        "version": manifest["version"], "instrument": "AMADO", "origin_commit": manifest["origin_commit"],
        "compiled_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "TECHNICALLY_CHECKED_RELEASE_CANDIDATE", "checks": checks,
        "results": {"unit_tests": technical["checks"]["unittest"]["tests_run"], "ontology_triples": technical["graph_counts"]["triples"],
                    "owl_2_dl": reasoner["profile_passed"], "hermit_consistency": reasoner["consistency_passed"],
                    "shacl": {k:technical["checks"]["public_base_shacl"][k] for k in ("violations","warnings","passed")},
                    "runtime_query_rows": technical["checks"]["runtime_main_decision_shacl_and_queries"]["query_rows"],
                    "browser_checks": simple["checks"],
                    "current_presentation": {"report": "simple-flow-browser.json", "checks": simple["checks"]},
                    "reused_component_evidence": reused,
                    "legacy_browser_checks": {"evidence_use": "REUSED_UNCHANGED_COMPONENTS", "checks": browser["checks"]},
                    "composition": {"version": manifest["composition"]["version"], "browser_checks": composition["checks"],
                                    "browser_evidence_use": "REUSED_UNCHANGED_COMPONENTS",
                                    "scope": "Produzir ou revisar uma contribuição digital; não substitui todas as tarefas do motor anterior.",
                                    "model_report": "https://github.com/natacsham/arcabouco-multimodal/tree/main/experimental/v2/evidence"}},
        "limits": ["Revisão técnica dos casos existentes, não nova avaliação humana.",
                   "Conferência em registro preservado não equivale à leitura do documento original.",
                   "Apoios parciais, pendências e verificações não executadas permanecem explícitos.",
                   "Alternativas textuais dos casos anteriores não são automaticamente recompostas; o módulo por funções verifica suas próprias rotas de entrada e revisão.",
                   "Testes não demonstram eficácia educacional ou aplicabilidade universal.",
                   "NVDA e VoiceOver não avaliados; não se declara conformidade WCAG integral."],
        "reports": {}, "historical_evidence_notice": "Os resultados da apresentação anterior são reutilizados para componentes cujos hashes foram conferidos, incluindo os arquivos preservados completo.html e completo-guiado.html. A apresentação simplificada possui seu próprio relatório atual. Relatórios herdados de 1.3 não integram a aprovação desta versão."
    }
    for name in reports:
        source = ROOT / "evidence" / name
        (target / name).write_bytes(source.read_bytes())
        summary["reports"][name] = {"url": name, "sha256": sha("evidence/" + name),
                                    **({"evidence_use": "REUSED_UNCHANGED_COMPONENTS"} if name in reused else
                                       {"evidence_use": "CURRENT_PRESENTATION_EXECUTION"} if name == "simple-flow-browser.json" else {})}
    smoke_path = ROOT / "evidence/simple-flow-public.json"
    if smoke_path.exists():
        smoke = read("evidence/simple-flow-public.json")
        verified = current_presentation(smoke, manifest)
        summary["public_smoke_status"] = "VERIFIED_CURRENT_BUILD" if verified else "NOT_VERIFIED_CURRENT_BUILD"
        if verified:
            (target / smoke_path.name).write_bytes(smoke_path.read_bytes())
            summary["reports"][smoke_path.name] = {"url": smoke_path.name, "sha256": sha("evidence/" + smoke_path.name)}
    else:
        summary["public_smoke_status"] = "PENDING_FOR_CURRENT_BUILD"
    (target / "report.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"passed": True, "version": manifest["version"], "checks": len(checks)}))


if __name__ == "__main__":
    main()
