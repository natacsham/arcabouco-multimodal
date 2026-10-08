"""Controlled JSON operations for AMADO; no HTTP, storage or generated files."""
import json
import sys

ENGINE = None


def initialize():
    global ENGINE
    from engine import DecisionEngine, VERSION
    ENGINE = DecisionEngine()
    return {"python": sys.version.split()[0], "rdflib": __import__("rdflib").__version__,
            "triples": len(ENGINE.graph), "engine_version": VERSION,
            "execution": "BROWSER_WEB_WORKER", "case_storage": False}


def dispatch(request):
    if not isinstance(request, dict):
        raise ValueError("A operação deve ser um objeto JSON.")
    if ENGINE is None:
        raise RuntimeError("O ambiente ainda não está pronto.")
    operation = request.get("operation")
    payload = request.get("payload", {})
    if not isinstance(payload, dict):
        raise ValueError("As informações devem ser enviadas como um objeto.")
    if operation == "catalog":
        return ENGINE.catalog_payload()
    if operation == "start":
        template = request.get("template")
        if template is None:
            return ENGINE.start_free_context()
        if not isinstance(template, str) or template not in ENGINE.contexts:
            raise ValueError("Exemplo não reconhecido na base.")
        return ENGINE.start_context(template)
    if operation == "clear":
        ENGINE.clear()
        return {"cleared": True}
    if ENGINE.current is None:
        raise ValueError("Carregue um exemplo ou informe um caso antes de continuar.")
    if operation == "update":
        return ENGINE.update_context(payload)
    if operation == "analyze":
        narrative = payload.get("narrative", "")
        if not isinstance(narrative, str) or not narrative.strip():
            raise ValueError("Descreva um caso antes de organizar as informações.")
        if len(narrative) > 10000:
            raise ValueError("Use até 10.000 caracteres na descrição do caso.")
        return ENGINE.analyze_narrative(narrative, "text")
    if operation == "confirm":
        if not isinstance(payload.get("confirmed"), bool):
            raise ValueError("Informe se o relato foi conferido.")
        correction = payload.get("correction", "")
        if not isinstance(correction, str) or len(correction) > 10000:
            raise ValueError("Use até 10.000 caracteres na correção.")
        return ENGINE.confirm_reported(payload["confirmed"], correction)
    if operation == "generate":
        return ENGINE.generate()
    raise ValueError("Operação não disponível nesta versão pública.")


def dispatch_json(raw):
    if not isinstance(raw, str) or len(raw) > 200000:
        raise ValueError("A descrição excede o tamanho aceito.")
    return json.dumps(dispatch(json.loads(raw)), ensure_ascii=False)
