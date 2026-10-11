"""Controlled JSON operations for AMADO; no HTTP, storage or generated files."""
import json
import sys

ENGINE = None
COMPOSER = None


def initialize():
    global ENGINE, COMPOSER
    from engine import DecisionEngine, VERSION
    ENGINE = DecisionEngine()
    COMPOSER = None
    return {"python": sys.version.split()[0], "rdflib": __import__("rdflib").__version__,
            "triples": len(ENGINE.graph), "engine_version": VERSION,
            "execution": "BROWSER_WEB_WORKER", "case_storage": False}


def composition_engine():
    """Load the reviewed composition extension, never an arbitrary input path."""
    global COMPOSER
    if COMPOSER is None:
        from experimental.v2.trajectory import ResearchComposer
        COMPOSER = ResearchComposer()
    return COMPOSER


def composition_catalog():
    """Project labels and actual requirements from the same RDF used to compose."""
    from pathlib import Path
    from rdflib import RDF, RDFS
    from rdflib.namespace import OWL
    from experimental.v2.composer import V2
    from experimental.v2.trajectory import HERE

    graph = composition_engine().graph

    def record(node):
        return {"id": str(node).rsplit("#", 1)[-1], "iri": str(node),
                "label": str(graph.value(node, RDFS.label) or node),
                "description": str(graph.value(node, RDFS.comment) or "")}

    def values(node, predicate):
        return [record(item)["id"] for item in sorted(set(graph.objects(node, predicate)), key=str)]

    def ordered_functions(node):
        return sorted(set(graph.objects(node, V2.requiresFunction)),
                      key=lambda item: (int(graph.value(item, V2.order) or 0), str(item)))

    tasks = [{**record(node), "required_functions": [record(item) for item in ordered_functions(node)],
              "input": record(graph.value(node, V2.inputType)),
              "output": record(graph.value(node, V2.outputType))}
             for node in sorted(set(graph.subjects(RDF.type, V2.Task)), key=str)]
    capabilities = [{**record(node), "function_id": record(graph.value(node, V2.provides))["id"],
                     "required_facts": values(node, V2.requiresFact),
                     "required_resources": values(node, V2.requiresResource)}
                    for node in sorted(set(graph.subjects(RDF.type, V2.Capability)), key=str)]
    relations = [{**record(node), "from_function": record(graph.value(node, V2.fromFunction))["id"],
                  "to_function": record(graph.value(node, V2.toFunction))["id"],
                  "required_facts": values(node, V2.requiresFact)}
                 for node in sorted(set(graph.subjects(RDF.type, V2.RelationRule)), key=str)]
    fields = {}
    for name, entity_type, predicate in (("facts", V2.ContextFact, V2.requiresFact),
                                          ("resources", V2.Resource, V2.requiresResource)):
        fields[name] = [{**record(node), "used_by": [record(item)["id"] for item in
                        sorted(set(graph.subjects(predicate, node)), key=str)], "default": None,
                        "scope": str(graph.value(node, V2.scope) or "person") if name == "facts" else "resource"}
                       for node in sorted(set(graph.subjects(RDF.type, entity_type)), key=str)]
    example = json.loads((Path(HERE) / "examples" / "learning-contribution.json").read_text(encoding="utf-8"))
    return {"version": str(next(graph.objects(None, OWL.versionInfo), "")), "tasks": tasks,
            **fields, "capabilities": capabilities, "relations": relations,
            "labels": {str(node): str(label) for node, label in sorted(graph.subject_objects(RDFS.label), key=lambda pair: str(pair[0]))},
            "values": [None, True, False], "case_storage": False,
            "scope": "Produzir ou revisar uma contribuição digital em contexto de aprendizagem; não verifica envio nem resultados de uso.",
            "synthetic_example": {"kind": "SYNTHETIC", "label": "Escrever e conferir pela leitura em voz", "context": example}}


def compose_context(payload):
    """Accept explicit, tri-state confirmations; never reinterpret narrative."""
    allowed = {"id", "task", "confirmed", "resources", "facts", "participants"}
    if set(payload) - allowed:
        raise ValueError("A composição aceita somente tarefa, condições e recursos confirmados; não interpreta texto livre.")
    identifier = payload.get("id", "WEB-COMPOSITION")
    if not isinstance(identifier, str) or not identifier.strip() or len(identifier) > 200:
        raise ValueError("Use um identificador de caso com até 200 caracteres, sem dados pessoais.")
    if type(payload.get("confirmed")) is not bool:
        raise ValueError("Informe explicitamente se as condições do caso foram conferidas.")
    catalog = composition_catalog()
    if not isinstance(payload.get("task"), str) or payload["task"] not in {row["id"] for row in catalog["tasks"]}:
        raise ValueError("Escolha uma das tarefas de composição representadas.")
    context = {"id": identifier, "task": payload["task"], "confirmed": payload["confirmed"]}
    def confirmed_values(values, group):
        known = {row["id"] for row in catalog[group]}
        if not isinstance(values, dict) or set(values) - known:
            raise ValueError("Há condições ou recursos não reconhecidos; confira os campos apresentados.")
        if any(value is not None and type(value) is not bool for value in values.values()):
            raise ValueError("Cada condição ou recurso deve ser Sim, Não ou Ainda não sei.")
        return dict(values)

    for group in ("facts", "resources"):
        context[group] = confirmed_values(payload.get(group, {}), group)
    if "participants" in payload:
        participants = payload["participants"]
        if not isinstance(participants, list) or not participants or len(participants) > 50:
            raise ValueError("Informe os participantes separadamente, sem dados pessoais.")
        identifiers = set()
        context["participants"] = []
        for person in participants:
            if not isinstance(person, dict) or set(person) - {"id", "label", "traits", "facts", "resources"}:
                raise ValueError("Cada participante aceita identificação, descrição, condições e recursos próprios.")
            person_id, label = person.get("id"), person.get("label", "")
            if not isinstance(person_id, str) or not person_id.strip() or len(person_id) > 200 or person_id in identifiers:
                raise ValueError("Use identificadores distintos para os participantes.")
            if not isinstance(label, str) or len(label) > 2000:
                raise ValueError("Use uma descrição curta para cada participante.")
            traits = person.get("traits", [])
            if not isinstance(traits, list) or any(not isinstance(trait, str) or len(trait) > 2000 for trait in traits):
                raise ValueError("As características informadas devem permanecer separadas por participante.")
            identifiers.add(person_id)
            context["participants"].append({"id": person_id, "label": label, "traits": list(traits),
                "facts": confirmed_values(person.get("facts", {}), "facts"),
                "resources": confirmed_values(person.get("resources", {}), "resources")})
    result = composition_engine().compose(context)
    # File hashes are identical in native and browser execution; host paths are
    # not evidence and must not be exposed or affect their public comparison.
    from pathlib import Path
    from experimental.v2.composer import ROOT
    def public_fingerprints(record):
        if "fingerprints" in record:
            record["fingerprints"] = {
                Path(name).resolve().relative_to(ROOT.resolve()).as_posix(): digest
                for name, digest in record["fingerprints"].items()
            }
        for participant in record.get("participant_results", []):
            public_fingerprints(participant["result"])
    public_fingerprints(result)
    return result


def dispatch(request):
    if not isinstance(request, dict):
        raise ValueError("A operação deve ser um objeto JSON.")
    if ENGINE is None:
        raise RuntimeError("O ambiente ainda não está pronto.")
    operation = request.get("operation")
    payload = request.get("payload", {})
    if not isinstance(payload, dict):
        raise ValueError("As informações devem ser enviadas como um objeto.")
    # Composition has its own confirmed context and must not reuse ENGINE.current.
    if operation == "catalog_composition":
        return composition_catalog()
    if operation == "compose":
        return compose_context(payload)
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
