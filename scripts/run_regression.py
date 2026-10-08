"""Execute synthetic checks; these reports are not human session logs."""

import copy
import hashlib
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from engine import DecisionEngine


def digest():
    return {
        p.name: hashlib.sha256(p.read_bytes()).hexdigest()
        for p in (ROOT / "data").glob("*.json")
    }


def main():
    e = DecisionEngine()
    before = digest()
    results, summary = {}, {}
    fixtures = {
        "principal": "CTX-TRANSFERENCIA-RECURSO-DIGITAL-01",
        "principal_sem_jogo": "CTX-TRANSFERENCIA-RECURSO-DIGITAL-01",
        "leitor_tela": "CTX-DEMO-WEB-LEITOR-TELA",
        "mobilidade_ruido": "CTX-DEMO-MOB-RUIDO",
        "comunicacao": "CTX-DEMO-COMUNICACAO-MULTIFORMATO",
        "diagnostico_isolado": "CTX-TESTE-RC2-DIAGNOSTICO-ISOLADO",
        "sem_confirmacao": "CTX-TRANSFERENCIA-RECURSO-DIGITAL-01",
    }
    for name, template in fixtures.items():
        e.start_context(template)
        payload = {
            "mapping_confirmed": name != "sem_confirmacao",
            "transfer_confirmed": name != "sem_confirmacao",
        }
        if name == "principal_sem_jogo":
            ctx = e.current["context"]
            payload.update(
                recursos_disponiveis=[
                    v
                    for v in ctx.get("recursos_disponiveis", [])
                    if v != "REC-PLATAFORMA-JOGO-QUIZ"
                ],
                recursos_propostos=[
                    v
                    for v in ctx.get("recursos_propostos", [])
                    if v != "REC-PLATAFORMA-JOGO-QUIZ"
                ],
                recursos_impedidos=["REC-PLATAFORMA-JOGO-QUIZ"],
            )
        e.update_context(payload)
        start = time.perf_counter()
        results[name] = e.generate()
        summary[name] = {
            "status": results[name]["decision"]["status"],
            "components": results[name]["decision"]["component_ids"],
            "seconds": round(time.perf_counter() - start, 3),
            "query_rows": results[name]["query_summary"],
        }
        print(
            name, summary[name]["status"], len(summary[name]["components"]), flush=True
        )

    # An unregistered combination: reading a visual web page and reviewing messages
    # in the same digital workflow. Only existing controlled conditions are used.
    left = copy.deepcopy(e.contexts["CTX-DEMO-WEB-LEITOR-TELA"])
    right = copy.deepcopy(e.contexts["CTX-DEMO-COMUNICACAO-MULTIFORMATO"])
    e.start_free_context()
    payload = {
        field: list(dict.fromkeys(left.get(field, []) + right.get(field, [])))
        for field in e.context_fields
    }
    payload["recursos_propostos"] = [
        r
        for r in payload["recursos_propostos"]
        if r not in payload["recursos_disponiveis"]
    ]
    payload.update(
        objetivo="Compreender uma página e revisar mensagens sobre seu conteúdo.",
        descricao_do_contexto="Caso sintético não cadastrado: acesso ao conteúdo de uma página e comunicação no mesmo fluxo, com teclado, leitor de tela, voz e revisão. Combinação técnica de condições; não é observação empírica.",
        mapping_confirmed=True,
        transfer_confirmed=True,
        impedimentos_verificados=True,
    )
    roles = {}
    for row in e.participations:
        if row.get("contexto_id") not in {left["id"], right["id"]}:
            continue
        role = roles.setdefault(row["papel_id"], {"papel_id": row["papel_id"]})
        for field in (
            "caracteristica_ids",
            "tarefa_ids",
            "modalidade_ids",
            "recurso_operado_ids",
        ):
            role[field] = list(dict.fromkeys(role.get(field, []) + row.get(field, [])))
    payload["participations"] = list(roles.values())
    e.update_context(payload)
    results["combinacao_nao_cadastrada"] = e.generate()
    novel = results["combinacao_nao_cadastrada"]
    summary["combinacao_nao_cadastrada"] = {
        "status": novel["decision"]["status"],
        "components": novel["decision"]["component_ids"],
        "knowledge": novel["decision"]["knowledge_ids"],
        "comparison": novel["articulation_comparison"],
        "input": copy.deepcopy(payload),
    }
    # Remove the microphone route, preserving the reading task and its resources.
    payload["recursos_disponiveis"] = [
        r for r in payload["recursos_disponiveis"] if r != "REC-ENTRADA-VOZ"
    ]
    payload["recursos_impedidos"] = ["REC-ENTRADA-VOZ"]
    e.update_context(payload)
    results["combinacao_sem_voz"] = e.generate()
    summary["combinacao_sem_voz"] = {
        "status": results["combinacao_sem_voz"]["decision"]["status"],
        "components": results["combinacao_sem_voz"]["decision"]["component_ids"],
    }
    assert before == digest(), "A synthetic test must not enrich the base to pass."
    checks = {
        "four_examples_compose_with_declared_coverage": all(
            results[n]["decision"]["status"] in {"GERADA", "GERADA_PARCIAL"}
            for n in ("principal", "leitor_tela", "mobilidade_ruido", "comunicacao")
        ),
        "game_block_removes_configuration": "PAD-JOGO-CONSOLIDACAO-FEEDBACK"
        not in results["principal_sem_jogo"]["decision"]["component_ids"],
        "diagnosis_alone_suspends": results["diagnostico_isolado"]["decision"][
            "status"
        ].startswith("SUSPENSA"),
        "unconfirmed_suspends": results["sem_confirmacao"]["decision"][
            "status"
        ].startswith("SUSPENSA"),
        "novel_combination_composes_two_functions": {
            "PAD-CONTEUDO-WEB-EQUIVALENTE",
            "PAD-COMUNICACAO-MULTIFORMATO",
        }
        <= set(novel["decision"]["component_ids"]),
        "removing_voice_changes_decision": novel["decision"]["component_ids"]
        != results["combinacao_sem_voz"]["decision"]["component_ids"],
        "base_unchanged": before == digest(),
    }
    out = ROOT / "evidence"
    (out / "native-cases.json").write_text(
        json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    report = {
        "version": "1.4.0-rc1",
        "type": "SYNTHETIC_TECHNICAL_REGRESSION_NOT_HUMAN_EVALUATION",
        "checks": checks,
        "cases": summary,
        "base_sha256": before,
    }
    (out / "regression-report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(checks))
    if not all(checks.values()):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
