"""Collect version-matched technical evidence; never synthesize human results."""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NAVIGATION_HTML = ("web/amado/index.html", "web/amado/guiado.html")
NAVIGATION_CHANGE = {"before": "Modelo e arquivos", "after": "Documentação técnica", "files": list(NAVIGATION_HTML)}
NAVIGATION_CHECKS = {
    "all_runtime_css_data_queries_and_ontology_bytes_preserved",
    "both_amado_html_only_navigation_label_changed", "no_base_runtime_or_case_request",
} | {f"{view}_{check}" for view in ("original", "guided") for check in (
    "served_html_matches", "navigation_labels", "documentation_reached_by_tab",
    "documentation_link_destination", "return_to_amado")}


def read(name):
    return json.loads((ROOT / name).read_text(encoding="utf-8"))


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def navigation_required_paths(manifest):
    """Runtime and semantic bytes that a label-only change may not alter."""
    return {
        "engine.py", "web/amado/engine.py", "web/amado/bridge.py", "web/amado/assets/base.zip",
        "ontology/main.ttl", "ontology/mado.owl", "shapes/main.shacl.ttl", "web/shell.css", "web/site.js",
    } | set(manifest["files"]) | {
        "web/amado/" + name for name in manifest["frontend_sha256"] if "web/amado/" + name not in NAVIGATION_HTML
    } | {"web/amado/runtime/" + name for name in manifest.get("runtime", {})} | {
        "web/amado/runtime/" + name for name in manifest.get("license_notices", {})}


def navigation_delta_valid(report, manifest, browser, guided):
    """Accept only the checked literal label change; works with shallow Git.

    Reverse the allowed replacement and hash those exact bytes against the
    preserved functional reports. A flag in the delta report is insufficient.
    """
    try:
        if not report or report.get("change_kind") != "NAVIGATION_LABEL_ONLY" or report.get("allowed_change") != NAVIGATION_CHANGE:
            return False
        if report.get("completed") is not True or not NAVIGATION_CHECKS.issubset(report.get("checks", {})):
            return False
        if not all(value is True for value in report["checks"].values()) or report.get("build") != manifest:
            return False
        records = {row["file"]: row for row in report["unchanged_files"]}
        if not navigation_required_paths(manifest).issubset(records):
            return False
        for name, row in records.items():
            relative = Path(name)
            if relative.is_absolute() or ".." in relative.parts:
                return False
            if row.get("unchanged") is not True or row["baseline_sha256"] != row["current_sha256"] or row["current_sha256"] != digest(ROOT / name):
                return False
        history = {row["reference"]: row for row in report["historical_evidence"]}
        previous = (("evidence/browser-report.json", browser), ("evidence/guided-report.json", guided))
        for name, prior in previous:
            reference = f"{report['baseline_commit']}:{name}"
            if prior is None or prior.get("completed") is not True or history[reference]["sha256"] != digest(ROOT / name):
                return False
            if not prior.get("checks") or not all(value is True for value in prior["checks"].values()) or prior.get("errors"):
                return False
            for key in ("core_sha256", "bridge_sha256", "base_zip_sha256", "files", "runtime", "license_notices"):
                if prior["build"].get(key) != manifest.get(key):
                    return False
            if set(prior["build"]["frontend_sha256"]) != set(manifest["frontend_sha256"]):
                return False
            for key, value in manifest["frontend_sha256"].items():
                if "web/amado/" + key not in NAVIGATION_HTML and prior["build"]["frontend_sha256"][key] != value:
                    return False
        html_records = {row["file"]: row for row in report["html_delta"]}
        if set(html_records) != set(NAVIGATION_HTML):
            return False
        before = b">Modelo e arquivos</a>"
        after = ">Documentação técnica</a>".encode("utf-8")
        for name in NAVIGATION_HTML:
            raw = (ROOT / name).read_bytes()
            if raw.count(after) != 1:
                return False
            old_sha = hashlib.sha256(raw.replace(after, before)).hexdigest()
            current_sha = hashlib.sha256(raw).hexdigest()
            item = html_records[name]
            frontend_name = Path(name).name
            if item.get("only_navigation_label_changed") is not True or item["baseline_sha256"] != old_sha or item["current_sha256"] != current_sha:
                return False
            if manifest["frontend_sha256"][frontend_name] != current_sha:
                return False
            if any(prior["build"]["frontend_sha256"][frontend_name] != old_sha for _, prior in previous):
                return False
        return True
    except (KeyError, TypeError, ValueError, OSError):
        return False


def main():
    technical = read("evidence/technical-report.json")
    reasoner = read("evidence/reasoner-report.json")
    regression = read("evidence/regression-report.json")
    browser = read("evidence/browser-report.json")
    parity = read("evidence/parity-report.json")
    distribution = read("evidence/distribution-audit.json")
    manifest = read("web/amado/manifest.json")
    checks = {
        "technical_passed": technical.get("passed") is True,
        "technical_engine_matches": technical["source_sha256"]["engine.py"] == digest(ROOT / "engine.py"),
        "web_engine_matches_native": manifest["core_sha256"] == digest(ROOT / "engine.py"),
        "reasoner_passed": reasoner.get("passed") is True,
        "reasoner_graph_matches": reasoner["input_sha256"] == digest(ROOT / "ontology/mado-combined.ttl"),
        "regression_passed": all(regression["checks"].values()),
        "regression_base_matches": regression["base_sha256"]["knowledge-base.json"] == digest(ROOT / "data/knowledge-base.json"),
        "browser_completed": browser.get("completed") is True and not browser.get("errors"),
        "browser_engine_matches": browser["build"]["core_sha256"] == manifest["core_sha256"],
        "browser_bridge_matches": browser["build"]["bridge_sha256"] == manifest["bridge_sha256"],
        "browser_frontend_matches": browser["build"]["frontend_sha256"] == manifest["frontend_sha256"],
        "browser_base_matches": browser["build"]["base_zip_sha256"] == manifest["base_zip_sha256"],
        "parity_passed": parity.get("passed") is True,
        "distribution_passed": distribution.get("passed") is True,
    }
    presentation_path = ROOT / "evidence/site-presentation-report.json"
    presentation = read("evidence/site-presentation-report.json") if presentation_path.exists() else None
    if manifest.get("site_assets_sha256"):
        checks["presentation_passed"] = (
            presentation is not None
            and presentation.get("completed") is True
            and not presentation.get("errors")
            and bool(presentation.get("checks"))
            and all(value is True for value in presentation["checks"].values())
        )
        checks["presentation_assets_match"] = presentation is not None and all(
            presentation.get("source_sha256", {}).get(name) == value
            for name, value in manifest["site_assets_sha256"].items()
        )
    guided_path = ROOT / "evidence/guided-report.json"
    guided = read("evidence/guided-report.json") if guided_path.exists() else None
    if "guiado.html" in manifest["frontend_sha256"]:
        checks["guided_view_passed"] = (
            guided is not None and guided.get("completed") is True
            and not guided.get("errors") and bool(guided.get("checks"))
            and all(value is True for value in guided["checks"].values())
        )
        checks["guided_view_build_matches"] = guided is not None and all(
            guided.get("build", {}).get(key) == manifest.get(key)
            for key in ("core_sha256", "bridge_sha256", "base_zip_sha256", "frontend_sha256", "files")
        )
    navigation_path = ROOT / "evidence/navigation-delta-report.json"
    navigation = read("evidence/navigation-delta-report.json") if navigation_path.exists() else None
    navigation_valid = navigation_delta_valid(navigation, manifest, browser, guided)
    navigation_fallback = navigation_valid and (
        not checks["browser_frontend_matches"] or not checks.get("guided_view_build_matches", True))
    if navigation_fallback:
        # Keep the historical reports unchanged, and do not describe their
        # earlier generation checks as executions of this presentation.
        checks.pop("browser_frontend_matches")
        checks.pop("guided_view_build_matches", None)
        checks["navigation_only_delta_verified_against_functional_evidence"] = True
    smoke_path = ROOT / "evidence/public-smoke.json"
    smoke = read("evidence/public-smoke.json") if smoke_path.exists() else None
    smoke_matches = smoke is not None and all(
        smoke["build"].get(key) == manifest.get(key)
        for key in ("core_sha256", "bridge_sha256", "base_zip_sha256", "frontend_sha256", "site_assets_sha256")
    )
    if smoke_matches:
        checks["public_smoke_passed"] = (
            smoke.get("completed") is True
            and smoke.get("execution_target") == "PUBLIC_SITE"
            and not smoke.get("errors")
            and bool(smoke.get("checks"))
            and all(value is True for value in smoke["checks"].values())
        )
        checks["public_smoke_build_matches"] = True
    if not all(checks.values()):
        raise SystemExit(json.dumps(checks, ensure_ascii=False))
    summary = {
        "version": "1.3.0-rc1",
        "instrument": "AMADO",
        "status": "TECHNICALLY_CHECKED_RELEASE_CANDIDATE",
        "compiled_at_utc": datetime.now(timezone.utc).isoformat(),
        "checks": checks,
        "results": {
            "unit_tests": technical["checks"]["unittest"]["tests_run"],
            "ontology_triples": technical["graph_counts"]["triples"],
            "shacl": {key: technical["checks"]["public_base_shacl"][key] for key in ("violations", "warnings", "passed")},
            "runtime_shacl": {key: technical["checks"]["runtime_main_decision_shacl_and_queries"][key] for key in ("violations", "warnings", "passed")},
            "owl_2_dl": reasoner["profile_passed"],
            "hermit_consistency": reasoner["consistency_passed"],
            "runtime_query_rows": technical["checks"]["runtime_main_decision_shacl_and_queries"]["query_rows"],
            "regression_checks": regression["checks"],
            "browser_checks": browser["checks"],
            "parity": parity,
        },
        "limits": [
            "Esta revisão posterior não substitui a versão da tese nem sua avaliação humana.",
            "Os casos de regressão são sintéticos; não são logs ou pareceres da especialista.",
            "Sem prova de eficácia educacional, generalização ou interpretação irrestrita de narrativas.",
            "65 avisos documentais da base permanecem visíveis; não foram preenchidos artificialmente.",
            "NVDA e VoiceOver não avaliados; os testes não constituem conformidade WCAG integral.",
            "Textos protegidos não redistribuídos: a auditoria documental completa requer as fontes originais.",
        ],
        "reports": {},
        "public_smoke_status": "VERIFIED_CURRENT_BUILD" if smoke_matches else "PENDING_FOR_CURRENT_BUILD",
    }
    if navigation_fallback:
        summary["results"].pop("browser_checks")
        summary["results"]["historical_functional_browser"] = {
            "report": "browser-report.json", "checks": browser["checks"], "executed_in_current_delta": False,
            "scope": "Prior functional execution; preserved runtime and exact navigation-label-only HTML delta verified separately."}
        summary["results"]["navigation_delta_checks"] = navigation["checks"]
        summary["navigation_delta_status"] = "VERIFIED_CURRENT_NAVIGATION_ONLY_CHANGE"
        summary["limits"].append("Nesta alteração de navegação, geração e recuperação funcional não foram repetidas; os relatórios anteriores são preservados e vinculados por hashes e reversão exata do rótulo.")
    target = ROOT / "web/evidence"
    target.mkdir(exist_ok=True)
    reports = ["technical-report.json", "reasoner-report.json", "regression-report.json", "browser-report.json", "browser-baseline-report.json", "parity-report.json", "public-projection.json", "public-content-audit.json", "distribution-audit.json", "build-manifest.json"]
    baseline = browser.get("change_verification", {}).get("baseline_report")
    if baseline and Path(baseline).name == baseline and baseline not in reports:
        reports.append(baseline)
    if presentation is not None:
        reports.append("site-presentation-report.json")
        summary["results"]["presentation_checks"] = presentation["checks"]
    if guided is not None:
        reports.append("guided-report.json")
        if navigation_fallback:
            summary["results"]["historical_functional_guided"] = {
                "report": "guided-report.json", "checks": guided["checks"], "executed_in_current_delta": False,
                "scope": "Prior guided-flow execution; not counted as executed by the current navigation check."}
        else:
            summary["results"]["guided_view_checks"] = guided["checks"]
        guided_baseline = guided.get("change_verification", {}).get("baseline_report")
        if guided_baseline and Path(guided_baseline).name == guided_baseline and guided_baseline not in reports:
            reports.append(guided_baseline)
    guided_public_path = ROOT / "evidence/guided-public-report.json"
    if guided_public_path.exists():
        guided_public = read("evidence/guided-public-report.json")
        reports.append("guided-public-report.json")
        public_guided_baseline = guided_public.get("change_verification", {}).get("baseline_report")
        if public_guided_baseline and Path(public_guided_baseline).name == public_guided_baseline and public_guided_baseline not in reports:
            reports.append(public_guided_baseline)
        guided_public_current = all(
            guided_public.get("build", {}).get(key) == manifest.get(key)
            for key in ("core_sha256", "bridge_sha256", "base_zip_sha256", "frontend_sha256", "site_assets_sha256")
        )
        summary["guided_public_status"] = (
            "VERIFIED_CURRENT_BUILD" if guided_public_current
            and guided_public.get("completed") is True
            and not guided_public.get("errors")
            and bool(guided_public.get("checks"))
            and all(value is True for value in guided_public["checks"].values())
            else "NOT_VERIFIED_CURRENT_BUILD"
        )
    if smoke is not None:
        reports.append("public-smoke.json")
        if smoke_matches:
            summary["results"]["public_smoke_checks"] = smoke["checks"]
        else:
            summary["historical_public_smoke"] = {
                "report": "public-smoke.json",
                "reason": "The recorded smoke tested an earlier build; not evidence for the current presentation.",
            }
    if navigation_valid:
        reports.append("navigation-delta-report.json")
    navigation_public_path = ROOT / "evidence/navigation-public-report.json"
    if navigation_public_path.exists():
        navigation_public = read("evidence/navigation-public-report.json")
        reports.append("navigation-public-report.json")
        public_navigation_current = navigation_public.get("execution_target") == "PUBLIC_SITE" and navigation_delta_valid(navigation_public, manifest, browser, guided)
        summary["public_navigation_status"] = "VERIFIED_CURRENT_NAVIGATION_ONLY_CHANGE" if public_navigation_current else "NOT_VERIFIED_CURRENT_NAVIGATION_CHANGE"
        if public_navigation_current:
            summary["results"]["public_navigation_checks"] = navigation_public["checks"]
            if not smoke_matches:
                summary["public_smoke_status"] = "NAVIGATION_VERIFIED_FUNCTIONAL_EXECUTION_HISTORICAL"
    for name in reports:
        path = ROOT / "evidence" / name
        summary["reports"][name] = {"sha256": digest(path), "url": name}
        (target / name).write_bytes(path.read_bytes())
    (target / "report.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"version": summary["version"], "checks_passed": len(checks), "public_report": "web/evidence/report.json"}))


if __name__ == "__main__":
    main()
