"""Publish only matching 1.4 evidence; never count inherited reports as new tests."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(name):
    return json.loads((ROOT / name).read_text(encoding="utf-8"))


def sha(name):
    return hashlib.sha256((ROOT / name).read_bytes()).hexdigest()


def main():
    manifest = read("web/amado/manifest.json")
    technical = read("evidence/technical-report.json")
    reasoner = read("evidence/reasoner-report.json")
    regression = read("evidence/regression-report.json")
    browser = read("evidence/traceability-browser.json")
    parity = read("evidence/parity-report.json")
    distribution = read("evidence/distribution-audit.json")
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
        "browser_current_build": browser["build"] == manifest,
        "browser_current_test": browser.get("test_sha256") == sha("tests/traceability-browser.mjs"),
        "parity": parity.get("passed") is True,
        "parity_current_build": parity.get("build") == manifest,
        "parity_current_native": parity["native_sha256"] == sha("evidence/native-cases.json"),
        "parity_current_test": parity.get("test_sha256") == sha("tests/compare_browser.mjs"),
        "distribution": distribution.get("passed") is True,
        "distribution_files_current": bool(distribution.get("distribution_sha256")) and all(sha(name) == value for name, value in distribution.get("distribution_sha256", {}).items()),
    }
    if not all(checks.values()):
        raise SystemExit(json.dumps(checks))
    reports = ["technical-report.json", "reasoner-report.json", "regression-report.json", "traceability-browser.json", "parity-report.json", "distribution-audit.json", "build-manifest.json"]
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
                    "browser_checks": browser["checks"]},
        "limits": ["Revisão técnica dos casos existentes, não nova avaliação humana.",
                   "Conferência em registro preservado não equivale à leitura do documento original.",
                   "Apoios parciais, pendências e verificações não executadas permanecem explícitos.",
                   "Alternativas textuais não são automaticamente avaliadas ou recompostas.",
                   "Testes não demonstram eficácia educacional ou aplicabilidade universal.",
                   "NVDA e VoiceOver não avaliados; não se declara conformidade WCAG integral."],
        "reports": {}, "historical_evidence_notice": "Outros relatórios herdados de 1.3 permanecem no histórico; não integram a aprovação desta versão."
    }
    for name in reports:
        source = ROOT / "evidence" / name
        (target / name).write_bytes(source.read_bytes())
        summary["reports"][name] = {"url": name, "sha256": sha("evidence/" + name)}
    smoke_path = ROOT / "evidence/traceability-public.json"
    if smoke_path.exists():
        smoke = read("evidence/traceability-public.json")
        verified = smoke.get("completed") is True and not smoke.get("errors") and smoke.get("build") == manifest and bool(smoke.get("checks")) and all(smoke["checks"].values()) and smoke.get("test_sha256") == sha("tests/traceability-browser.mjs")
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
