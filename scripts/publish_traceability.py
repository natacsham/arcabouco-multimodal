"""Publish current presentation checks and explicitly qualified reusable evidence."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]

# These files belong only to the new entry flow, not the preserved full views.
# This exception is deliberately unavailable to unknown tests or older reports.
UNUSED_SIMPLE_FLOW = frozenset({"index.html", "guiado.html", "simple-flow.js",
                               "simple-flow.css", "intake.mjs", "voice.js"})
FULL_VIEW_TESTS = {
    "SYNTHETIC_TECHNICAL_BROWSER_CHECK": "tests/traceability-browser.mjs",
    "SYNTHETIC_COMPOSITION_BROWSER_NOT_HUMAN_EVALUATION": "tests/composition-browser.mjs",
}


def read(name):
    return json.loads((ROOT / name).read_text(encoding="utf-8"))


def sha(name):
    return hashlib.sha256((ROOT / name).read_bytes()).hexdigest()


def _matches(name, digest):
    return bool(digest) and (ROOT / name).is_file() and sha(name) == digest


def _complete_view_scope(report, manifest, scope_report):
    """RC2 full-view evidence: only explicitly unconsumed entry files may differ.

    The original build/report is never rewritten. Shared scripts, CSS, site
    projections, fixtures and runtime remain byte-bound; no broad exclusion of
    frontend hashes is allowed. Unknown navigation/dependencies fail closed.
    """
    previous = report.get("build") or {}
    test = FULL_VIEW_TESTS.get(scope_report.get("type"))
    test_text = (ROOT / test).read_text(encoding="utf-8") if test and (ROOT / test).is_file() else ""
    full_route = "base+'amado/'+(view==='index.html'?'completo.html':'completo-guiado.html')"
    routes = {re.sub(r"\s+", "", route) for route in re.findall(r"page\.goto\((.*?)\);", test_text)}
    allowed_routes = {"base", "base+'ontologia/'", "base+'amado/completo.html'", full_route}
    front = previous.get("frontend_sha256") or {}
    current_front = manifest.get("frontend_sha256") or {}
    required_views = {"completo.html", "completo-guiado.html", "app.js", "worker.mjs", "client.mjs"}
    used_front = {name: digest for name, digest in front.items() if name not in UNUSED_SIMPLE_FLOW}
    site = previous.get("site_assets_sha256") or {}
    used_inputs = {"web/amado/" + name: digest for name, digest in used_front.items()}
    used_inputs.update({"web/" + name: digest for name, digest in site.items()})
    used_inputs.update(previous.get("files") or {})
    used_inputs.update({"engine.py": previous.get("core_sha256"),
                       "web/amado/engine.py": previous.get("core_sha256"),
                       "web/amado/bridge.py": previous.get("bridge_sha256"),
                       "web/amado/assets/base.zip": previous.get("base_zip_sha256")})
    used_inputs.update({"web/amado/runtime/" + name: value.get("sha256")
                       for name, value in (previous.get("runtime") or {}).items()})
    used_inputs.update({"web/amado/runtime/" + name: digest
                       for name, digest in (previous.get("license_notices") or {}).items()})
    if test:
        used_inputs[test] = scope_report.get("test_sha256")
    # Conservative dependency guard: fail even on a newly mentioned entry module
    # in shared executable/style/HTML inputs instead of silently broadening reuse.
    shared_text = "\n".join((ROOT / name).read_text(encoding="utf-8")
                            for name in used_inputs
                            if name.startswith("web/") and Path(name).suffix in {".html", ".js", ".mjs", ".css"}
                            and "/runtime/" not in name and (ROOT / name).is_file())
    ignored_modules = UNUSED_SIMPLE_FLOW - {"index.html", "guiado.html"}
    checks = {
        "rc2_scope": previous.get("version") == manifest.get("version") == "1.4.0-rc2",
        "known_current_full_view_test": bool(test) and _matches(test, scope_report.get("test_sha256")),
        "full_view_navigation": full_route in routes and routes <= allowed_routes,
        "same_non_frontend_manifest": {k: v for k, v in previous.items() if k != "frontend_sha256"}
            == {k: v for k, v in manifest.items() if k != "frontend_sha256"},
        "same_frontend_inventory": set(front) == set(current_front),
        "actual_full_view_paths_recorded": required_views <= set(used_front),
        "only_unconsumed_entry_hashes_may_differ": all(current_front.get(name) == digest for name, digest in used_front.items()),
        "unconsumed_modules_not_referenced": all(name not in shared_text for name in ignored_modules),
        "used_inputs_current": bool(site) and bool(previous.get("files")) and bool(previous.get("runtime"))
            and all(_matches(name, digest) for name, digest in used_inputs.items()),
        "current_entry_files_match_manifest": all(_matches("web/amado/" + name, digest) for name, digest in current_front.items()),
    }
    return {"passed": all(checks.values()), "checks": checks,
            "evidence_use": "REUSED_UNCHANGED_COMPONENTS",
            "entrypoints": ["web/amado/completo.html", "web/amado/completo-guiado.html"],
            "used_inputs": used_inputs,
            "unconsumed_entry_changes": {"web/amado/" + name: {"tested": front.get(name), "current": current_front.get(name)}
                for name in sorted(UNUSED_SIMPLE_FLOW) if front.get(name) != current_front.get(name)},
            "notice": "Reúso limitado aos mesmos bytes das vistas completas e suas dependências; o manifesto original permanece no relatório. Não é uma nova execução da build global nem da entrada simplificada."}


def preserved_components(report, manifest, scope_report=None):
    """Require the exact tested inputs, including the preserved original views.

    The full build cannot match after replacing the two entry pages. Only those
    two paths may move; every prior runtime, base, engine and UI input must still
    match its recorded fingerprint. New presentation checks are required below.
    """
    previous = report.get("build") or {}
    if previous == manifest:
        current = {
            "core": sha("engine.py") == manifest["core_sha256"],
            "served_core": _matches("web/amado/engine.py", manifest["core_sha256"]),
            "bridge": sha("web/amado/bridge.py") == manifest["bridge_sha256"],
            "bundle": sha("web/amado/assets/base.zip") == manifest["base_zip_sha256"],
            "base_files": all(sha(name) == value for name, value in manifest["files"].items()),
            "frontend_files": all(sha("web/amado/" + name) == value for name, value in manifest["frontend_sha256"].items()),
            "site_files": all(sha("web/" + name) == value for name, value in manifest["site_assets_sha256"].items()),
            "runtime_files": bool(manifest.get("runtime")) and all(_matches("web/amado/runtime/" + name, value.get("sha256"))
                for name, value in manifest.get("runtime", {}).items()),
            "license_files": bool(manifest.get("license_notices")) and all(_matches("web/amado/runtime/" + name, value)
                for name, value in manifest.get("license_notices", {}).items()),
        }
        return {"passed": all(current.values()), "checks": current,
                "evidence_use": "CURRENT_BUILD_EXECUTION",
                "notice": "Execução repetida nesta versão, com todos os arquivos vinculados ao manifesto atual."}
    if previous.get("version") == manifest.get("version") == "1.4.0-rc2":
        return _complete_view_scope(report, manifest, scope_report or report)
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


def parity_components(report, browser, manifest):
    """Bind the actual compared artifacts without inventing an original seal."""
    comparison = preserved_components(report, manifest, scope_report=browser)
    execution = preserved_components(browser, manifest)
    browser_artifact = "tests/.artifacts/browser/decisions.json"
    artifact_present = (ROOT / browser_artifact).is_file()
    digest_recorded = bool(re.fullmatch(r"[a-f0-9]{64}", str(report.get("browser_sha256", ""))))
    checks = {
        "comparison_inputs_preserved": comparison["passed"],
        "originating_browser_inputs_preserved": execution["passed"],
        "originating_browser_completed": browser.get("completed") is True and not browser.get("errors")
            and bool(browser.get("checks")) and all(browser["checks"].values()),
        "originating_browser_test_current": _matches("tests/traceability-browser.mjs", browser.get("test_sha256")),
        "comparator_current": _matches("tests/compare_browser.mjs", report.get("test_sha256")),
        "native_artifact_current": _matches("evidence/native-cases.json", report.get("native_sha256")),
        "browser_artifact_digest_recorded": digest_recorded,
        "browser_artifact_matches_if_present": not artifact_present or _matches(browser_artifact, report.get("browser_sha256")),
        "comparison_passed": report.get("passed") is True,
    }
    return {"passed": all(checks.values()), "checks": checks,
            "evidence_use": "ARTIFACT_COMPARISON_WITH_QUALIFIED_BROWSER_PROVENANCE",
            "originating_report": "evidence/traceability-browser.json",
            "originating_report_sha256": sha("evidence/traceability-browser.json"),
            "originating_execution_at": browser.get("executed_at"),
            "originating_evidence_use": execution["evidence_use"],
            "native_sha256": report.get("native_sha256"), "browser_sha256": report.get("browser_sha256"),
            "browser_artifact_verification": "VERIFIED_PRESENT_ARTIFACT" if artifact_present else "RECORDED_DIGEST_WITHOUT_ARTIFACT",
            "browser_artifact_checked_directly": artifact_present,
            "artifact_hash_sealed_in_originating_report": False,
            "notice": ("O artefato nativo atual, o teste exato e a execução de navegador identificada foram conferidos. "
                       + ("O hash do artefato de navegador presente também foi conferido. " if artifact_present else
                          "O artefato de navegador não está disponível neste ambiente: conserva-se o digest registrado pelo comparador, sem nova conferência direta do arquivo. ")
                       + "O relatório originário não selou o hash de decisions.json; este vínculo é qualificado, não uma assinatura criptográfica histórica nem uma nova execução de navegador.")}


def current_public_smoke(report, manifest, *, situated=False):
    """Verify the bounded public smoke, not the full local browser regression.

    Preserve the deployment commit and execution time recorded by the test.
    Serving identity is established by the manifest/assets, not current HEAD.
    """
    expected = {"amado/" + name: digest for name, digest in manifest.get("frontend_sha256", {}).items()}
    expected.update(manifest.get("site_assets_sha256", {}))
    expected.update({"amado/runtime/" + name: item["sha256"]
                     for name, item in manifest.get("runtime", {}).items()})
    expected.update({"amado/engine.py": manifest.get("core_sha256"),
                     "amado/bridge.py": manifest.get("bridge_sha256"),
                     "amado/assets/base.zip": manifest.get("base_zip_sha256")})
    assets = report.get("assets") or {}
    test_checks = report.get("checks") or {}
    safe_paths = all(isinstance(name, str) and not name.startswith("/")
                     and "\\" not in name and ":" not in name
                     and ".." not in name.split("/") for name in assets)
    checks = {
        "recognized_smoke": report.get("type") == ("SYNTHETIC_SITUATED_PUBLIC_SMOKE_NOT_PARTICIPANT_SESSION" if situated else "SYNTHETIC_PUBLIC_SMOKE_NOT_PARTICIPANT_SESSION"),
        "completed_and_passed": report.get("completed") is True and report.get("passed") is True,
        "nonempty_successful_checks": bool(test_checks) and all(value is True for value in test_checks.values()),
        "no_errors": report.get("errors") == [] and report.get("external_requests") == [],
        "exact_test": _matches("tests/situated-public-smoke.mjs" if situated else "tests/public-smoke.mjs", report.get("test_sha256")),
        "exact_manifest": _matches("web/amado/manifest.json", report.get("public_manifest_sha256")),
        "version": report.get("version") == manifest.get("version"),
        "deployment_commit_recorded": bool(re.fullmatch(r"[a-f0-9]{40}", report.get("expected_commit") or "")),
        "all_consumed_assets_recorded": bool(manifest.get("frontend_sha256"))
            and bool(manifest.get("site_assets_sha256")) and bool(manifest.get("runtime"))
            and {"amado/index.html", "amado/guiado.html", "amado/client.mjs", "amado/worker.mjs",
                 "amado/simple-flow.js", "amado/intake.mjs"} <= set(expected)
            and set(assets) == set(expected),
        "current_asset_bytes": safe_paths and bool(assets) and all(
            isinstance(item, dict) and item.get("passed") is True
            and item.get("expected_sha256") == item.get("served_sha256") == expected.get(name)
            and _matches("web/" + name, item.get("served_sha256"))
            for name, item in assets.items()),
        "current_base_inputs": bool(manifest.get("files")) and all(
            _matches(name, digest) for name, digest in manifest.get("files", {}).items()),
        "current_native_engine": _matches("engine.py", manifest.get("core_sha256")),
    }
    if situated:
        downloads = report.get("download_assets") or {}
        expected_downloads = {"downloads/mado-public.ttl", "downloads/mado.owl",
                              "downloads/main.ttl", "downloads/main.shacl.ttl"}
        checks["current_download_bytes"] = set(downloads) == expected_downloads and all(
            isinstance(item, dict) and item.get("passed") is True
            and item.get("expected_sha256") == item.get("served_sha256")
            and _matches("web/" + name, item.get("served_sha256"))
            for name, item in downloads.items())
    return {"passed": all(checks.values()), "checks": checks,
            "evidence_use": "VERIFIED_CURRENT_BUILD_SYNTHETIC_SMOKE" if all(checks.values()) else "NOT_VERIFIED_CURRENT_BUILD",
            "checked_at": report.get("checked_at"), "expected_commit": report.get("expected_commit"),
            "commit_observation": report.get("commit_observation"),
            "test_sha256": report.get("test_sha256"), "public_manifest_sha256": report.get("public_manifest_sha256"),
            "check_count": len(test_checks), "asset_count": len(assets),
            "scope": ("Smoke público sintético do contrato situado, limitado às verificações registradas; não substitui a regressão local nem avaliação humana." if situated else "Smoke público sintético limitado aos checks registrados; não equivale aos 118 checks locais nem a avaliação humana."),
            "limits": report.get("limits", [])}


def current_presentation(report, manifest):
    return (report.get("completed") is True and report.get("passed") is True
            and not report.get("errors") and bool(report.get("checks"))
            and all(report["checks"].values()) and report.get("build") == manifest
            and report.get("test_sha256") == sha("tests/simple-flow-browser.mjs"))


def situated_release_checks(manifest, technical, reasoner, situated, browser, distribution, logical):
    """New runtime requires new evidence; old browser reports cannot approve it."""
    technical_inputs = technical.get("source_sha256") or {}
    frozen = situated.get("source_hashes_before") or {}
    required = {"engine.py", "situated_context.py", "data/knowledge-base.json", "experimental/v2/composer.py",
                "experimental/v2/trajectory.py", "experimental/v2/trajectory-bindings.json", "web/amado/bridge.py",
                "tests/test_situated_intake.py", "tests/test_situated_composition.py", "tests/test_situated_catalogue.py",
                *[f"queries/CQ-{i:03d}.rq" for i in range(1, 11)]}
    checks = browser.get("checks") or {}
    return {
        "version": manifest.get("version") == "1.5.0-rc1" and manifest.get("composition", {}).get("version") == "2.0.0-alpha3",
        "current_package": preserved_components({"build": manifest}, manifest)["passed"],
        "technical_passed": technical.get("passed") is True,
        "technical_inputs_current": required <= set(technical_inputs) and all(_matches(n, h) for n, h in technical_inputs.items()),
        "owl_and_hermit_current": reasoner.get("passed") is True and reasoner.get("profile_passed") is True
            and reasoner.get("consistency_passed") is True and _matches("ontology/mado-combined.ttl", reasoner.get("input_sha256")),
        "situated_tests": situated.get("tests", {}).get("success") is True and situated.get("tests", {}).get("count", 0) > 0
            and situated.get("tests", {}).get("skipped") == 0,
        "situated_frozen_inputs": bool(frozen) and situated.get("source_files_unchanged") is True
            and situated.get("input_context_unchanged") is True and frozen == situated.get("source_hashes_after")
            and all(_matches(n, h) for n, h in frozen.items()),
        "novel_case_and_ablation": situated.get("delta", {}).get("complete_choices_with_relation", 0) > 0
            and situated.get("delta", {}).get("complete_choices_without_relation") == 0
            and situated.get("delta", {}).get("complete_choices_without_articulation_operation") == 0
            and situated.get("delta", {}).get("first_person_sequence_preserved") is True,
        "browser_current_execution": browser.get("type") == "SYNTHETIC_SITUATED_FLOW_NOT_PARTICIPANT_SESSION"
            and browser.get("passed") is True and not browser.get("errors") and bool(checks)
            and all(value is True for value in checks.values()) and browser.get("build") == manifest
            and _matches("tests/situated-browser.mjs", browser.get("test_sha256")),
        "browser_native_parity": checks.get("conditional_native_worker_canonical_parity") is True,
        "distribution_current": distribution.get("passed") is True and bool(distribution.get("distribution_sha256"))
            and all(_matches(n, h) for n, h in distribution.get("distribution_sha256", {}).items()),
        "composition_rdf_reasoner": logical.get("passed") is True and logical.get("profile_passed") is True
            and logical.get("consistency_passed") is True
            and _matches("experimental/v2/evidence/trajectory-combined.ttl", logical.get("input_sha256")),
    }


def publish_situated(manifest):
    paths = {"technical": "evidence/technical-1.5-report.json", "reasoner": "evidence/reasoner-1.5-report.json",
             "situated": "experimental/v2/evidence/situated-report.json", "browser": "evidence/situated-browser.json",
             "distribution": "evidence/distribution-audit.json", "logical": "experimental/v2/evidence/trajectory-reasoner-report.json"}
    records = {key: read(name) for key, name in paths.items()}
    checks = situated_release_checks(manifest, **records)
    if not all(checks.values()):
        raise SystemExit(json.dumps({"published": False, "version": manifest.get("version"), "checks": checks}))
    technical, reasoner = records["technical"], records["reasoner"]
    target = ROOT / "web/evidence"
    target.mkdir(exist_ok=True)
    summary = {
        "version": manifest["version"], "instrument": "AMADO", "executor_version": manifest["executor_version"],
        "compiled_at_utc": datetime.now(timezone.utc).isoformat(), "status": "TECHNICALLY_CHECKED_RELEASE_CANDIDATE",
        "checks": checks,
        "results": {"unit_tests": technical["checks"]["unittest"]["tests_run"],
                    "ontology_triples": technical["graph_counts"]["triples"],
                    "owl_2_dl": reasoner["profile_passed"], "hermit_consistency": reasoner["consistency_passed"],
                    "shacl": {k: technical["checks"]["public_base_shacl"][k] for k in ("violations", "warnings", "passed")},
                    "query_rows_legacy_compatibility": technical["checks"]["runtime_main_decision_shacl_and_queries"]["query_rows"],
                    "situated_composition": {"version": manifest["composition"]["version"], "delta": records["situated"]["delta"],
                                             "tests": records["situated"]["tests"]["count"]},
                    "browser_checks": records["browser"]["checks"]},
        "limits": records["situated"]["limits"] + records["browser"]["limits"] + [
            "Conferência de um registro não equivale à leitura integral de todas as fontes.",
            "Relatórios de versões anteriores não são evidência desta execução.",
            "Verificações técnicas não comprovam utilidade, aprendizagem ou conformidade integral de acessibilidade."],
        "historical_evidence_notice": "Somente os relatórios listados abaixo aprovam estes bytes. Arquivos anteriores conservam sua própria versão e seu alcance.",
        "public_smoke_status": "PENDING_FOR_CURRENT_BUILD", "reports": {},
    }
    for key, name in paths.items():
        filename = Path(name).name
        (target / filename).write_bytes((ROOT / name).read_bytes())
        summary["reports"][filename] = {"url": filename, "sha256": sha(name), "evidence_use": "CURRENT_BUILD_EXECUTION"}
    smoke_name = "evidence/situated-public-smoke.json"
    if (ROOT / smoke_name).is_file():
        smoke = read(smoke_name)
        verification = current_public_smoke(smoke, manifest, situated=True)
        summary["public_smoke_status"] = verification["evidence_use"]
        summary["results"]["public_smoke"] = verification
        if verification["passed"]:
            filename = Path(smoke_name).name
            (target / filename).write_bytes((ROOT / smoke_name).read_bytes())
            summary["reports"][filename] = {"url": filename, "sha256": sha(smoke_name),
                "evidence_use": verification["evidence_use"], "expected_commit": smoke["expected_commit"]}
    (target / "report.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"passed": True, "version": manifest["version"], "checks": len(checks)}))


def main():
    manifest = read("web/amado/manifest.json")
    if manifest.get("version") == "1.5.0-rc1":
        return publish_situated(manifest)
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
    focused = read("evidence/focused-dialogue-browser.json")
    source_catalog = read("evidence/source-catalog-browser.json")
    reused = {"traceability-browser.json": preserved_components(browser, manifest),
              "parity-report.json": parity_components(parity, browser, manifest),
              "composition-browser.json": preserved_components(composition, manifest)}
    checks = {
        "version": manifest["version"] == read("data/knowledge-base.json")["metadata"]["version"] == "1.4.0-rc3",
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
        "focused_dialogue_current_execution": focused.get("passed") is True and not focused.get("errors")
            and bool(focused.get("checks")) and focused.get("build") == manifest
            and focused.get("test_sha256") == sha("tests/focused-dialogue-browser.mjs"),
        "source_catalog_browser": source_catalog.get("passed") is True and not source_catalog.get("errors")
            and bool(source_catalog.get("checks")) and all(source_catalog["checks"].values()),
        "source_catalog_current_build": source_catalog.get("build") == manifest,
        "source_catalog_current_inputs": bool(source_catalog.get("hashes"))
            and all(sha(name) == value for name, value in source_catalog.get("hashes", {}).items()),
        "current_frontend_files": bool(manifest.get("frontend_sha256")) and all(
            sha("web/amado/" + name) == value for name, value in manifest.get("frontend_sha256", {}).items()),
    }
    if not all(checks.values()):
        raise SystemExit(json.dumps(checks))
    reports = ["technical-report.json", "reasoner-report.json", "regression-report.json", "traceability-browser.json", "parity-report.json", "distribution-audit.json", "build-manifest.json", "composition-browser.json", "simple-flow-browser.json", "focused-dialogue-browser.json", "source-catalog-browser.json"]
    target = ROOT / "web/evidence"
    target.mkdir(exist_ok=True)
    summary = {
        "version": manifest["version"], "instrument": "AMADO", "origin_commit": manifest["origin_commit"],
        "executor_version": manifest["executor_version"],
        "compiled_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "TECHNICALLY_CHECKED_RELEASE_CANDIDATE", "checks": checks,
        "results": {"unit_tests": technical["checks"]["unittest"]["tests_run"], "ontology_triples": technical["graph_counts"]["triples"],
                    "owl_2_dl": reasoner["profile_passed"], "hermit_consistency": reasoner["consistency_passed"],
                    "shacl": {k:technical["checks"]["public_base_shacl"][k] for k in ("violations","warnings","passed")},
                    "runtime_query_rows": technical["checks"]["runtime_main_decision_shacl_and_queries"]["query_rows"],
                    "browser_checks": simple["checks"],
                    "current_presentation": {"report": "simple-flow-browser.json", "checks": simple["checks"]},
                    "context_revision": {"report": "focused-dialogue-browser.json", "checks": focused["checks"]},
                    "source_catalog": {"report": "source-catalog-browser.json", "checks": source_catalog["checks"],
                                       "scope": "Catálogo e percurso documental conferidos no navegador; não leitura integral das referências."},
                    "reused_component_evidence": reused,
                    "legacy_browser_checks": {"evidence_use": reused["traceability-browser.json"]["evidence_use"], "checks": browser["checks"]},
                    "composition": {"version": manifest["composition"]["version"], "browser_checks": composition["checks"],
                                    "browser_evidence_use": reused["composition-browser.json"]["evidence_use"],
                                    "scope": "A entrada comum usa o compositor por funções para escrita com revisão e revisão de texto. Acesso a conteúdo e demais tarefas seguem o motor existente, conforme sua cobertura; não se afirma composição completa para todas as tarefas.",
                                    "model_report": "https://github.com/natacsham/arcabouco-multimodal/tree/main/experimental/v2/evidence"}},
        "limits": ["Revisão técnica dos casos existentes, não nova avaliação humana.",
                   "Conferência em registro preservado não equivale à leitura do documento original.",
                   "Apoios parciais, pendências e verificações não executadas permanecem explícitos.",
                   "Alternativas textuais dos casos anteriores não são automaticamente recompostas; o módulo por funções verifica suas próprias rotas de entrada e revisão.",
                   "Testes não demonstram eficácia educacional ou aplicabilidade universal.",
                   "NVDA e VoiceOver não avaliados; não se declara conformidade WCAG integral."],
        "reports": {}, "historical_evidence_notice": "Os relatórios identificam individualmente execução atual ou reúso de componentes idênticos. A apresentação simplificada possui seu próprio relatório. Evidências antigas não aprovam bytes diferentes."
    }
    for name in reports:
        source = ROOT / "evidence" / name
        (target / name).write_bytes(source.read_bytes())
        summary["reports"][name] = {"url": name, "sha256": sha("evidence/" + name),
                                    **({"evidence_use": reused[name]["evidence_use"]} if name in reused else
                                       {"evidence_use": "CURRENT_PRESENTATION_EXECUTION"} if name == "simple-flow-browser.json" else {})}
    smoke_path = ROOT / "evidence/public-smoke.json"
    full_public_path = ROOT / "evidence/simple-flow-public.json"
    if smoke_path.exists():
        smoke = read("evidence/public-smoke.json")
        verification = current_public_smoke(smoke, manifest)
        summary["public_smoke_status"] = verification["evidence_use"]
        summary["results"]["public_smoke"] = verification
        if verification["passed"]:
            (target / smoke_path.name).write_bytes(smoke_path.read_bytes())
            summary["reports"][smoke_path.name] = {
                "url": smoke_path.name, "sha256": sha("evidence/" + smoke_path.name),
                "evidence_use": verification["evidence_use"], "expected_commit": smoke["expected_commit"]}
    elif full_public_path.exists():
        smoke_path = full_public_path
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
