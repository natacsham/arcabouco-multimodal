"""Derive the Home example from the same in-memory result used by AMADO.

Only the prepared, public synthetic fixture is exported. Never visitor data.
"""
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from engine import DecisionEngine, VERSION


def main():
    engine = DecisionEngine()
    engine.start_context("CTX-TRANSFERENCIA-RECURSO-DIGITAL-01")
    engine.update_context({"mapping_confirmed": True, "transfer_confirmed": True})
    generated = engine.generate()
    result = {key: generated[key] for key in ("decision", "traceability", "articulations_used", "execution_evidence", "explanation") if key in generated}
    choices = result["explanation"]["configurations"]
    pilot = [row for row in choices if any(
        support.get("criterion_id") == "CA02" and {"K38", "K43"} <= set(support.get("knowledge_ids", []))
        for support in row.get("application", {}).get("supports", []))]
    if not pilot:
        raise RuntimeError("The approved pilot has no generated configuration; no separate story will replace it.")
    # Keep the full graph/evidence for fidelity; disclose that only one choice
    # is expanded on the Home. All decision configurations remain in the result.
    result["explanation"]["configurations"] = pilot[:1]
    result["version"] = VERSION
    result["example_label"] = "Exemplo de aplicação — organização de conteúdo persistente"
    result["prepared_public_example"] = True
    result["selection_notice"] = "Uma escolha exibida; registros da execução completa preservados. Não é sessão de participante."
    result["source_hashes"] = {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
                               for name in ("engine.py", "execution_trace.py", "data/knowledge-base.json", "ontology/mado-combined.ttl")}
    # Execution identifiers/timestamps remain labelled as a prepared technical run.
    target = ROOT / "web/assets/explanation-pilot.json"
    target.parent.mkdir(exist_ok=True)
    target.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"pilot": pilot[0]["component_id"], "version": VERSION, "bytes": target.stat().st_size}))


if __name__ == "__main__":
    main()
