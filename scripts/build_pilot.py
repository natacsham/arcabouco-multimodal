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
    result = engine.generate_situated()
    collections = ("choices", "partial_segments", "pending_candidates")
    pilot = [(group, row) for group in collections for row in result[group]
             if any(step.get("component_id") == "PAD-ORGANIZAR-CONTEUDO-PERSISTENTE" for step in row.get("steps", []))]
    if not pilot:
        raise RuntimeError("The approved pilot has no generated configuration; no separate story will replace it.")
    # Keep checks and documentary scope, but display a single genuine proposal.
    # Never convert a conditional proposal into a ready orientation for the Home.
    selected_group, selected = pilot[0]
    for group in collections:
        result[group] = [selected] if group == selected_group else []
    result["alternatives"] = []
    result["version"] = VERSION
    result["example_label"] = "Exemplo de aplicação — organização de conteúdo persistente"
    result["prepared_public_example"] = True
    result["selection_notice"] = "Uma possibilidade da execução preparada. As condições pendentes continuam pendentes; não é uma sessão de participante."
    result["source_hashes"] = {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
                               for name in ("engine.py", "situated_context.py", "experimental/v2/composer.py", "experimental/v2/trajectory.py",
                                            "data/knowledge-base.json", "ontology/mado-combined.ttl")}
    # Execution identifiers/timestamps remain labelled as a prepared technical run.
    target = ROOT / "web/assets/explanation-pilot.json"
    target.parent.mkdir(exist_ok=True)
    target.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"pilot": selected["id"], "state": selected_group, "version": VERSION, "bytes": target.stat().st_size}))


if __name__ == "__main__":
    main()
