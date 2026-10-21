"""Versioned, conservative narrative intake. Runtime records, not new MADO terms.

The parser proposes scoped statements with source text. Unrecognized language
stays in the narrative; a diagnosis is never converted to an ability. Review is
an explicit patch over statements, so correcting a statement cannot erase the
unrelated part of a case.
"""
from __future__ import annotations

import copy
import hashlib
import re
import unicodedata

VERSION = "1.0"
ACTIVE_STATES = {"RELATADO", "INFERIDO_PARA_CONFIRMACAO", "CONFIRMADO"}
STATES = ACTIVE_STATES | {"CONFLITO", "RETIRADO_POR_CORRECAO", "DESCONHECIDO"}
FIELDS = {
    "task": "tarefas", "characteristic": "caracteristicas_pessoa",
    "barrier": "barreiras", "need": "necessidades", "environment": "ambientes",
    "modality": "modalidades_disponiveis", "digital_resource": "recursos_digitais",
    "resource_available": "recursos_disponiveis", "resource_proposed": "recursos_propostos",
    "resource_blocked": "recursos_impedidos",
}
PERSON_FIELDS = {"task": "tarefa_ids", "characteristic": "caracteristica_ids",
                 "modality": "modalidade_ids", "resource_operation": "recurso_operado_ids"}
SITUATION_FIELDS = {"task": "task_ids", "environment": "env_ids", "barrier": "barrier_ids",
                    "need": "need_ids", "modality": "mode_ids", "digital_resource": "resource_ids"}
KINDS = set(FIELDS) | set(PERSON_FIELDS) | {"reported_condition", "group_count", "group_membership",
        "functional_observation", "functional_fact", "objective", "digital_use", "participation", "activity"}
TYPE_FOR_KIND = {"task": "TAREFA", "characteristic": "CARACTERISTICA_PESSOA", "barrier": "BARREIRA",
                 "need": "NECESSIDADE", "environment": "AMBIENTE", "modality": "MODALIDADE",
                 "digital_resource": "RECURSO_DIGITAL", "participation": "PAPEL",
                 "resource_operation": "RECURSO_DISPONIVEL", "resource_available": "RECURSO_DISPONIVEL",
                 "resource_proposed": "RECURSO_DISPONIVEL", "resource_blocked": "RECURSO_DISPONIVEL"}
RESOURCE_STATES = {"resource_available": "DISPONIVEL_CONFIRMADO", "resource_proposed": "PROPOSTO_A_PREPARAR",
                   "resource_blocked": "IMPEDIDO"}
FACT_LABELS = {
    "CanUseKeyboard": "Consegue utilizar o teclado",
    "CanUseSpeech": "Consegue falar",
    "CanReadText": "Consegue acompanhar informação escrita",
    "CanReviewVisualText": "Consegue conferir o texto apresentado na tela",
    "CanReviewSpeech": "Consegue conferir o texto pela leitura em voz",
    "CanControlPlayback": "Consegue controlar a reprodução",
    "CanCorrect": "Consegue corrigir o conteúdo antes de concluir",
    "ControlsCompletion": "Controla quando concluir ou confirmar",
    "ContentAvailable": "Há conteúdo a expressar ou revisar",
    "CanVerifyMeaning": "Consegue conferir o sentido do conteúdo",
    "AudioUsable": "Consegue ouvir o áudio nesta situação",
    "UsesScreenReader": "Utiliza leitor de tela",
    "KeyboardEffortAcceptable": "Digitar o conteúdo completo exige esforço aceitável",
    "SpeechInputUsable": "O reconhecimento de fala funciona nesta situação",
    "SameEditableTextDraft": "A revisão ocorre no mesmo texto produzido",
    "EditableText": "Há um campo de texto que pode ser corrigido",
    "Display": "O texto apresentado na tela pode ser lido",
}


def folded(value):
    return "".join(c for c in unicodedata.normalize("NFD", str(value).casefold())
                   if unicodedata.category(c) != "Mn")


def words(value):
    return re.sub(r"[^a-z0-9]+", " ", folded(value)).strip()


def negated_action(text, start):
    return bool(re.search(r"\bnao\s+(?:(?:quero|quer|pretendo|preciso|precisa|vou|vai|devo|consigo|consegue|conseguem|pode|podem)\s+)?$",
                          text[max(0, start - 45):start]))


def preparation_action(text):
    """An explicit first-person preparation action, not a job-title inference."""
    local = words(text)
    return next((match for match in re.finditer(
        r"\b(?:eu )?(?:posso|vou|pretendo|quero|preciso)\s+(?:preparar|editar|adaptar|acrescentar)\b", local)
        if not negated_action(local, match.start())), None)


def refresh_preparation_participation(context, people):
    """Projection from active primary statements; removing one revokes its use."""
    people_ids = {person["id"] for person in people}
    for situation in context.get("situations", []):
        statements = [row for row in context.get("assertions", [])
                      if row.get("kind") == "activity" and row.get("activity_phase") == "PREPARATION"
                      and not row.get("preparation_authority_id")
                      and row.get("situation_id") == situation["id"]
                      and row.get("subject_id") in people_ids and row.get("state") in ACTIVE_STATES
                      and preparation_action(row.get("value", ""))]
        if "preparation_actor_ids" in situation or statements:
            situation["preparation_actor_ids"] = list(dict.fromkeys(row["subject_id"] for row in statements))


def completion_control(text, start, end):
    """Deciding when to send is a condition, not a separate send task."""
    return bool(re.search(r"\b(?:(?:decido|decide|decidem|controlo|controla|controlam|decidir|controlar)\s+(?:quando|se)|antes de)\s*$",
                          text[max(0, start - 45):start]) or
                text[start:end] == "controlar" and re.match(r"\s+quando\b", text[end:]))


def functional_signal_pattern(signal):
    # Grammatical inflection of an existing signal, not a new design claim.
    choices = {"consegue": "(?:consigo|consegue|conseguem)",
               "perde": "(?:perco|perde|perdem)", "precisa": "(?:preciso|precisa|precisam)"}
    token = words(signal)
    pattern = " ".join(choices.get(word, re.escape(word)) for word in token.split())
    if token == "precisa retomar a explicacao":
        pattern += (
            r"|nao (?:consigo|consegue|conseguem) (?:retomar|recuperar) "
            r"(?:a |as |o |os )?(?:instrucoes|instrucao|explicacao)"
            r"|dificuldades? (?:de|para|em) (?:retomar|recuperar) "
            r"(?:a |as |o |os )?(?:instrucoes|instrucao|explicacao)"
            r"|retomar (?:um |o |cada )?passo sem recomecar"
        )
    if token == "dificuldade para digitar":
        pattern += r"|digitar textos longos causa (?:fadiga|dor|cansaco)"
    return r"\b(?:" + pattern + r")\b"


def resource_occurrences(narrative, token):
    """Read every explicit occurrence before projecting resource availability."""
    result = []
    for clause in re.split(r"[.!?;]", narrative):
        local = words(clause)
        for match in re.finditer(r"\b" + re.escape(token) + r"\b", local):
            before, after = local[:match.start()], local[match.end():]
            blocked = (re.search(r"\b(?:sem|nao (?:ha|tem|temos|tenho|esta disponivel))\s*(?:(?:um|uma|o|a)\s+)?$", before)
                       or re.match(r"\s+(?:(?:esta|estao)\s+)?(?:indisponivel|indisponiveis|nao disponivel)\b", after))
            available = (re.search(r"\b(?:tenho|temos|ha|tem|existe|existem|usa|usam|utiliza|utilizam|oferece|oferecem)\b(?!\s+que\b)[^.!?]{0,75}$", before)
                         or re.match(r"\s+(?:(?:esta|estao)\s+)?disponive(?:l|is)\b", after))
            acquisition = re.search(r"\b(?:quero|pretendo|vou|preciso|podemos|poderia)\b.{0,35}\b(?:comprar|adquirir|providenciar)\b[^.!?]{0,60}$", before)
            preparation = re.search(r"\b(?:quero|pretendo|vou|preciso|posso|podemos|poderia)\b.{0,35}\b(?:preparar|criar|considerar|produzir|acrescentar)\b[^.!?]{0,75}$", before)
            if acquisition and negated_action(before, acquisition.start()):
                acquisition = None
            if preparation and negated_action(before, preparation.start()):
                preparation = None
            if blocked:
                result.append(("recursos_impedidos", clause.strip()))
            elif acquisition or preparation:
                result.append(("recursos_propostos", clause.strip()))
            elif available and not re.search(r"\bnao\s+(?:tenho|temos|ha|tem|existe|existem)\b", before):
                result.append(("recursos_disponiveis", clause.strip()))
    return result


# These are existing composer facts. A positive statement must cover the
# entire fact: ability to speak alone does not establish acceptance of speech.
REPORTED_FACT_PATTERNS = (
    ("CanUseKeyboard", r"\b(?P<no>nao\s+)?(?:consigo|consegue|conseguem|posso|pode|podem)\s+(?:usar|operar|escrever (?:com|usando))\s+(?:o |um )?teclado\b"),
    ("CanUseSpeech", r"\b(?P<no>nao\s+)?(?:consigo e aceito|consegue e aceita|conseguem e aceitam|posso e aceito|pode e aceita)\s+(?:falar|usar (?:a )?fala)\b"),
    ("CanReviewVisualText", r"\b(?P<no>nao\s+)?(?:consigo|consegue|conseguem|posso|pode|podem)\s+(?:ler|conferir|revisar)\s+(?:o |um )?texto\s+(?:na tela|visualmente)\b"),
    ("CanReviewSpeech", r"\b(?P<no>nao\s+)?(?:consigo|consegue|conseguem|posso|pode|podem)\s+conferir\s+(?:o )?(?:conteudo|texto)\s+(?:pela leitura em voz|ouvindo)\b"),
    ("CanControlPlayback", r"\b(?P<no>nao\s+)?(?:consigo|consegue|conseguem)\s+pausar e repetir\s+(?:a )?leitura\b"),
    ("CanCorrect", r"\b(?P<no>nao\s+)?(?:consigo|consegue|conseguem|posso|pode|podem)\s+(?:(?:usar|operar) (?:o )?teclado para )?corrigir\s+(?:o |um )?(?:rascunho|texto|erros)\b"),
    ("ControlsCompletion", r"\b(?P<no>nao\s+)?(?:decido|decide|decidem|controlo|controla|controlam)\s+quando\s+(?:concluir|enviar)\b"),
    ("ContentAvailable", r"\b(?P<no>nao\s+)?(?:tenho|temos|tem|ha)\s+(?:o |um )?conteudo\s+disponivel\b"),
    ("CanVerifyMeaning", r"\b(?P<no>nao\s+)?(?:consigo|consegue|conseguem)\s+(?:verificar o significado|confirmar o sentido do texto)\b"),
    ("CanUseSpeech", r"\b(?P<no>nao\s+)?(?:consigo|consegue|conseguem)\s+falar\b"),
    ("CanReviewVisualText", r"\b(?P<no>nao\s+)?(?:consigo|consegue|conseguem)\s+(?:falar e )?ler\s+(?:a )?tela\b"),
    ("CanReadText", r"\b(?P<no>nao\s+)?(?:(?:consigo|consegue|conseguem)\s+ler\s+(?:instrucoes|texto)|le\s+portugues|acompanha\s+informacoes escritas)\b"),
    ("AudioUsable", r"\b(?P<no>nao\s+)?(?:consigo|consegue|conseguem)\s+ouvir\s+(?:o )?audio\b"),
    ("UsesScreenReader", r"\b(?P<no>nao\s+)?(?:uso|usa|usam|utilizo|utiliza|utilizam)\s+(?:um |o )?leitor de tela\b"),
    ("CanCorrect", r"\b(?P<no>nao\s+)?(?:consigo|consegue|posso|pode)\s+(?:usar o teclado para pequenas correcoes|corrigir antes de concluir)\b"),
    ("ControlsCompletion", r"\b(?P<no>nao\s+)?(?:posso|pode|consigo|consegue)\s+controlar quando\s+(?:comecar|parar|confirmar|concluir)\b"),
)


def clause_owners(clause, people, context, previous=None):
    """Resolve explicit references only; diagnosis identifies a referent, never an ability."""
    local = words(clause)
    receivers = [p for p in people if p.get("papel_id") in {"PAPEL-ESTUDANTE", "PAPEL-PESSOA-APOIADA"}]
    mentioned = [p for p in receivers if p.get("reported_condition", {}).get("text")
                 and re.search(r"\b" + re.escape(words(p["reported_condition"]["text"])) + r"\b", local)]
    if len(mentioned) == 1:
        return mentioned
    if re.match(r"(?:ambos|ambas|os dois|as duas)\b", local) and len(receivers) == 2:
        return receivers
    if re.match(r"(?:ele|ela)\b", local) and previous and len(previous) == 1:
        return previous
    first_person = re.match(r"(?:eu\s+)?(?:consigo|posso|preciso|quero|estou|tenho|vou|decido|controlo)\b", local)
    if first_person or re.search(r"\b(?:que posso|e posso)\b", local):
        return [p for p in people if p["id"] == context.get("requester_participation_id")]
    if re.match(r"(?:algumas pessoas|alguns participantes|as pessoas|os participantes|o grupo|adultos)\b", local):
        return receivers if len(receivers) == 1 else []
    return people[:] if len(people) == 1 else []


def extract_reported_facts(context, people, narrative):
    """Project explicit, uniquely owned testimony; do not verify it for the user."""
    role_patterns = {
        "PAPEL-PROFESSORA": r"\b(?:professor(?:a)?|docente)\b",
        "PAPEL-MEDIADOR": r"\bmediador[ao]?\b",
        "PAPEL-ESTUDANTE": r"\b(?:alunos?|alunas?|estudantes?)\b",
        "PAPEL-PESSOA-APOIADA": r"\b(?:pessoa|usuario|usuaria)\b",
    }
    self_id = context.get("requester_participation_id")
    collected = {}
    previous = []
    for clause in re.split(r"(?<=[.!?;])\s+", narrative, flags=re.I):
        local = words(clause)
        if re.search(r"\b(?:nao sei|nao e (?:verdade|certo|garantido) que|talvez|acho que|sera que|parte d[ao]s?|um dos)\b", local):
            continue
        roles = {role for role, pattern in role_patterns.items() if re.search(pattern, local)}
        explicit_self = bool(re.search(r"\b(?:eu|consigo|posso|decido|controlo|tenho|aceito)\b", local))
        resolved = clause_owners(clause, people, context, previous)
        if explicit_self and roles and not resolved:
            # Do not attach a first-person ability to another person mentioned
            # in the same clause. This needs clarification, not role precedence.
            continue
        owners = ([p for p in people if p["id"] == self_id] if explicit_self and not roles else
                  [p for p in people if p.get("papel_id") in roles] if len(roles) == 1 else
                  people[:] if not roles and not explicit_self and len(people) == 1 else [])
        if resolved:
            owners = resolved
            previous = resolved
        if not owners:
            continue
        # "Some" is safe only when the represented group is itself scoped to
        # those people; never project the observation to an entire known class.
        if re.match(r"(?:alguns|algumas)\b", local) and any(p.get("group_scope") == "TOTAL" for p in owners):
            continue
        for person in owners:
            _collect_person_facts(context, collected, person, clause, local)
    for (pid, sid, fact_id), occurrences in collected.items():
        values = {value for value, _ in occurrences}
        conflict = len(values) > 1
        source = " / ".join(dict.fromkeys(source for _, source in occurrences))
        row = _assert(context, pid, sid, "functional_fact", {"fact_id": fact_id,
                      "value": None if conflict else next(iter(values)),
                      "label": FACT_LABELS.get(fact_id.rsplit("#", 1)[-1], fact_id)}, source,
                      "CONFLITO" if conflict else "RELATADO")
        _project(context, people, row)


def _collect_person_facts(context, collected, person, clause, local):
    """Keep each proposition local; a reported channel is not all operability checks."""
    situations = [s for s in context.get("situations", []) if person["id"] in s.get("participant_ids", [])
                  and s.get("task_ids")]
    local_situations = [s for s in situations if words(clause) in words(s.get("source_text", ""))]
    if len(local_situations) == 1:
        situations = local_situations
    if not situations:
        return
    if len(situations) > 1:
        active = [s for s in situations if s["id"] == context.get("active_situation_id")]
        if active:
            situations = active
        else:
            return
    sid = situations[0]["id"]
    for fact, pattern in REPORTED_FACT_PATTERNS:
        for match in re.finditer(pattern, local):
            # A hypothetical request is not testimony of current capacity.
            if re.search(r"\b(?:se|caso|diz que|disse que|pergunta se)\s+(?:(?:eu|ele|ela)\s+)?$", local[:match.start()]):
                continue
            key = (person["id"], sid, "https://w3id.org/mado/experimental/v2#" + fact)
            collected.setdefault(key, []).append((not bool(match.group("no")), clause.strip()))
    fixed = (
        ("KeyboardEffortAcceptable", False, r"\b(?:digitar|digitacao)\b.{0,35}\b(?:textos longos|muito tempo)\b.{0,30}\b(?:fadiga|cansa|dor|cansaco)\b"),
        ("SpeechInputUsable", False, r"\b(?:ruido|barulho)\b.{0,45}\b(?:impede|inviabiliza|impossibilita)\b.{0,35}\b(?:reconhecimento|ditado)\b"),
        ("SpeechInputUsable", False, r"\b(?:reconhecimento de fala|ditado)\b.{0,20}\bnao funciona\b"),
    )
    for fact, value, pattern in fixed:
        if re.search(pattern, local):
            collected.setdefault((person["id"], sid, "https://w3id.org/mado/experimental/v2#" + fact), []).append((value, clause.strip()))


def uid(prefix, *values):
    return prefix + hashlib.sha256("|".join(map(str, values)).encode()).hexdigest()[:12].upper()


def fresh_contract():
    return {"situated_version": VERSION, "revision": 0, "situations": [], "assertions": [],
            "question_answers": [], "question_manifest": {}, "active_situation_id": "", "review_changes": [], "unmapped_text": [],
            "facts": {}, "situated_facts": []}


def corrected_text(narrative):
    """Only explicit local repair markers license retracting the earlier term."""
    text = folded(narrative)
    corrections = []
    patterns = [
        r"(?P<old>mobilidade|motor(?:a|as|es)?)(?P<link>[^.!?]{0,65}?(?:nao\s*[,;:]?\s*(?:e|eh|sao)?|quer dizer|na verdade|corrigindo|melhor dizendo)[^.!?]{0,35}?)(?P<new>cognitiv[ao]s?)",
        r"(?:nao (?:e|eh|sao)\s+)(?P<old>mobilidade|motor(?:a|as|es)?)(?P<link>[^.!?]{0,25}?)(?P<new>cognitiv[ao]s?)",
        r"(?P<old>mobilidade|motor(?:a|as|es)?)(?P<link>[^.!?]{0,45}?)(?P<new>cognitiv[ao]s?)[,\s]*(?:na verdade|quer dizer|melhor dizendo)\b",
    ]
    spans = set()
    for pattern in patterns:
        for match in re.finditer(pattern, text):
            if match.span("old") in spans:
                continue
            spans.add(match.span("old"))
            corrections.append({"old": narrative[match.start("old"):match.end("old")],
                                "new": narrative[match.start("new"):match.end("new")],
                                "source_text": narrative[match.start():match.end()],
                                "span": match.span("old")})
    # A later explicit repair about the requester's preparation replaces earlier
    # statements of that same responsibility. It does not erase their profession,
    # recipients or tasks, and does not interpret an unrelated "não" as repair.
    for repair in re.finditer(r"\b(?:correcao|corrigindo|na verdade)\s*[:,]?\s*(?:eu )?nao\s+"
                              r"(?:posso|vou|pretendo|quero|consigo)\s+(?:preparar|adaptar|editar)\b[^.!?]*", text):
        for clause in re.finditer(r"[^.!?;]+", text[:repair.start()]):
            intent = re.search(r"\b(?:eu )?(?:posso|vou|pretendo|quero|preciso)\s+"
                               r"(?:preparar|editar|adaptar|acrescentar)\b", clause.group(0))
            if intent and not negated_action(words(clause.group(0)), intent.start()):
                span = (clause.start() + intent.start(), clause.end())
                spans.add(span)
                corrections.append({"old": narrative[span[0]:span[1]], "new": narrative[repair.start():repair.end()],
                                    "source_text": narrative[repair.start():repair.end()], "span": span})
    result = list(narrative)
    for start, end in spans:
        result[start:end] = " " * (end - start)
    return "".join(result), corrections


def _assert(context, subject, situation, kind, value, source, state="RELATADO", **extra):
    identifier = uid("AS-", context["revision"], subject, situation, kind, value, source)
    row = {"id": identifier, "subject_id": subject, "situation_id": situation, "kind": kind,
           "value": value, "source_text": source, "state": state, "revision": context["revision"], **extra}
    if not any(item["id"] == identifier for item in context["assertions"]):
        context["assertions"].append(row)
    return row


def _person(context, role, label, suffix):
    return {"id": uid("PART-", context["id"], suffix), "contexto_id": context["id"],
            "papel_id": role, "label": label, "grupo_rotulo": "", "quantidade": 1,
            "caracteristica_ids": [], "tarefa_ids": [], "modalidade_ids": [], "recurso_operado_ids": [],
            "objetivo_participacao": "", "status_evidencia": "IDENTIFICADO_PARA_CONFIRMACAO"}


def enrich_operational_observations(context, people, narrative, concepts):
    """Project literal preparation, ownership and application affordances.

    No source claims, recommendations or diagnostic capabilities are created.
    Devices/resources stay separate from the representations to be prepared.
    """
    previous = []
    clauses = [c.strip() for c in re.split(r"(?<=[.!?;])\s+", narrative) if c.strip()]
    active = next((s for s in context["situations"] if s["id"] == context.get("active_situation_id")), None)
    resource_patterns = (
        ("REC-COMPUTADOR", r"\bcomputador(?:es)?\b"), ("REC-TECLADO", r"\bteclado\b"),
        ("REC-MICROFONE", r"\bmicrofone\b"), ("REC-LEITOR-DE-TELA", r"\bleitor de tela\b"),
        ("REC-VOZ-RECONHECIMENTO-DE-FALA-B24FB5F", r"\breconhecimento de fala\b"),
        ("REC-DESCRICAO-TEXTUAL", r"\bdescricao (?:textual|das informacoes visuais|de imagens)\b"),
        ("REC-LEGENDAS", r"\blegendas?\b"),
    )
    personal_resources = set()
    for clause in clauses:
        local = words(clause)
        owners = clause_owners(clause, people, context, previous)
        if owners:
            previous = owners
        prep = preparation_action(local)
        situations = ([active] if active else context["situations"] if len(context["situations"]) == 1 else [])
        if prep and owners:
            for situation in situations:
                situation["preparation_actor_ids"] = list(dict.fromkeys([*situation.get("preparation_actor_ids", []), *[p["id"] for p in owners]]))
                for person in owners:
                    primary = _assert(context, person["id"], situation["id"], "activity", clause, clause,
                                      activity_phase="PREPARATION")
                    for mode, pattern in (("MOD-TEXTO", r"\b(?:texto|instrucoes escritas)\b"), ("MOD-IMAGEM", r"\bimagens\b")):
                        if mode in concepts and re.search(pattern, local):
                            _assert(context, person["id"], situation["id"], "activity", "Preparar " + concepts[mode].get("rotulo", mode), clause,
                                    activity_phase="PREPARATION", proposed_representation_id=mode,
                                    preparation_authority_id=primary["id"])
        if not situations:
            continue
        # Keep each person's usable devices scoped to that person. An explicit
        # "both" clause is the only multi-person propagation done here.
        for resource, pattern in resource_patterns:
            if resource not in concepts or not re.search(pattern, local):
                continue
            token = re.search(pattern, local).group(0)
            occurrences = resource_occurrences(clause, token)
            if not occurrences and re.search(r"\b(?:consigo|consegue|conseguem)\s+(?:usar|operar)\b", local):
                occurrences = [("recursos_disponiveis", clause)]
            for field, source in occurrences:
                kind = {"recursos_disponiveis": "resource_available", "recursos_propostos": "resource_proposed", "recursos_impedidos": "resource_blocked"}[field]
                for situation in situations:
                    # Prepared output serves this situation. Its author is
                    # preserved separately, without pretending it exists.
                    targets = [context["id"]] if prep else [p["id"] for p in owners]
                    for subject in targets:
                        row = _assert(context, subject, situation["id"], kind, resource, source)
                        _project(context, people, row)
                        if subject != context["id"]:
                            personal_resources.add((situation["id"], resource))
                        if kind == "resource_available":
                            for person in owners:
                                if person["id"] == subject and resource not in person["recurso_operado_ids"]:
                                    person["recurso_operado_ids"].append(resource)
        # Same editable output is explicitly shown then corrected. This is a
        # reported application affordance, not confirmation of meaning/access.
        if (re.search(r"\bmostra (?:o )?texto reconhecido\b", local)
                and re.search(r"(?<!nao )\b(?:posso|pode) corrigir\b", local) and len(owners) == 1
                and not re.search(r"\bnao mostra\b", local)):
            for situation in situations:
                for fact in ("SameEditableTextDraft", "EditableText"):
                    row = _assert(context, owners[0]["id"], situation["id"], "functional_fact",
                                  {"fact_id": "https://w3id.org/mado/experimental/v2#" + fact,
                                   "value": True, "label": FACT_LABELS[fact]}, clause)
                    _project(context, people, row)
    # Remove the legacy unowned lexical projection when the narrative actually
    # states who uses that device. In particular, one reader does not give every
    # participant a screen reader. Person-scoped assertions are authoritative.
    for sid, resource in personal_resources:
        context["assertions"] = [a for a in context["assertions"] if not (
            a.get("subject_id") == context["id"] and a.get("situation_id") == sid
            and a.get("kind") in RESOURCE_STATES and a.get("value") == resource)]
        situation = next(s for s in context["situations"] if s["id"] == sid)
        situation["resource_states"] = [r for r in situation["resource_states"] if r["resource_id"] != resource]


def from_legacy(context, people):
    """Preserve old examples in one explicit runtime scope, without parsing them."""
    if context.get("situated_version"):
        return
    context.update(fresh_contract())
    source = "Informações preservadas do exemplo: " + str(context.get("template_id", ""))
    sid = uid("SIT-", context["id"], "preserved_example")
    situation = {"id": sid, "label": "Situação do exemplo preservado", "kind": "preserved_example",
                 "task_ids": list(context.get("tarefas", [])), "participant_ids": [p["id"] for p in people],
                 "actor_ids": [p["id"] for p in people if p.get("tarefa_ids")],
                 "recipient_ids": [p["id"] for p in people if not p.get("tarefa_ids")],
                 "env_ids": list(context.get("ambientes", [])), "resource_ids": list(context.get("recursos_digitais", [])),
                 "mode_ids": list(context.get("modalidades_disponiveis", [])), "need_ids": list(context.get("necessidades", [])),
                 "barrier_ids": list(context.get("barreiras", [])), "resource_states": [], "source_text": source, "state": "RELATADO"}
    context["situations"] = [situation]
    context["active_situation_id"] = sid
    for kind, field in FIELDS.items():
        for value in context.get(field, []):
            _assert(context, context["id"], sid, kind, value, source)
            if kind in RESOURCE_STATES:
                situation["resource_ids"].append(value)
                situation["resource_states"].append({"resource_id": value, "state": RESOURCE_STATES[kind]})
    for person in people:
        _assert(context, person["id"], "", "participation", person.get("papel_id", ""), source)
        for kind, field in PERSON_FIELDS.items():
            for value in person.get(field, []):
                _assert(context, person["id"], sid, kind, value, source)


def build(context, people, narrative, concepts, evidence, prior=None):
    """Build runtime scopes after legacy lexical recognition, without its broadcast assignments."""
    effective, corrections = corrected_text(narrative)
    text = words(effective)
    source_clauses = [part.strip() for part in re.split(r"(?<=[.!?;])\s+|\s+e depois\s+", effective, flags=re.I) if part.strip()]
    def source_clause(token):
        matches = [clause for clause in source_clauses if words(token) in words(clause)]
        return matches[0] if len(matches) == 1 else narrative
    # An intended acquisition/adaptation is not evidence of availability.
    # A mention used as an instrument ("produzir mensagem por ditado") is
    # different from producing/acquiring that instrument.
    for item in evidence:
        if item.get("field") != "recursos_disponiveis":
            continue
        value, token = item.get("concept_id"), words(item.get("matched_text", ""))
        occurrences = resource_occurrences(effective, token) if token else []
        states = {field for field, _ in occurrences}
        if not states:
            continue
        conflict = "recursos_disponiveis" in states and "recursos_impedidos" in states
        target = ("recursos_disponiveis" if conflict or "recursos_disponiveis" in states else
                  "recursos_impedidos" if "recursos_impedidos" in states else "recursos_propostos")
        for field in ("recursos_disponiveis", "recursos_impedidos", "recursos_propostos"):
            context[field] = [r for r in context.get(field, []) if r != value]
        # Conflicting testimony remains editable and blocks confirmation.
        context[target].append(value)
        source = " / ".join(dict.fromkeys(clause for field, clause in occurrences if conflict or field == target))
        item.update(field=target, matched_text=source)
        if conflict:
            item["status"] = "CONFLITO_A_CONFIRMAR"
    previous_revision = (prior or {}).get("revision", 0)
    context.update(fresh_contract())
    context["revision"] = previous_revision + 1
    # Re-analyzing a full narrative preserves the audit trail, not stale answers.
    for previous in (prior or {}).get("assertions", []):
        old = copy.deepcopy(previous)
        if old["state"] in ACTIVE_STATES:
            old["state"] = "RETIRADO_POR_CORRECAO"
        context["assertions"].append(old)
    for person in people:
        person["tarefa_ids"] = []
        person["modalidade_ids"] = []
        person["caracteristica_ids"] = []
    total = re.search(r"\b(?P<count>\d+|vinte)\s+(?:alunos|alunas|estudantes)\b", text)
    if not total:
        total = re.search(r"\bturma\s+(?:de |com )?(?P<count>\d+|vinte)\b", text)
    group = None
    if total:
        count = 20 if total.group("count") == "vinte" else int(total.group("count"))
        if count > 0:
            group = next((p for p in people if p.get("papel_id") == "PAPEL-ESTUDANTE"
                          and not p.get("reported_condition")), None)
            if group is None:
                group = _person(context, "PAPEL-ESTUDANTE", f"Estudantes ({count})", "total")
                people.append(group)
            group.update(quantidade=count, label=f"Estudantes ({count})", grupo_rotulo="estudantes",
                         group_scope="TOTAL")
            _assert(context, group["id"], "", "group_count", count, total.group(0))
            for person in people:
                if person is not group and person.get("papel_id") == "PAPEL-TURMA":
                    person.update(parent_group_id=group["id"], group_scope="GROUP_ROLE", quantidade=None,
                                  label=f"Turma — mesmo grupo de {count} estudantes")
                if person is not group and person.get("reported_condition"):
                    person["parent_group_id"] = group["id"]
                    _assert(context, person["id"], "", "group_membership", group["id"], narrative)
    cognitive = re.search(r"\b(?:deficiencia\s+|dificuldades?\s+|problemas?\s+)?cognitiv[ao]s?\b", text)
    if cognitive:
        subgroup = bool(re.search(r"\b(alguns|algumas|parte d[ao]s?|dentro deles|entre (?:eles|elas|os alunos))\b", text))
        person = next((p for p in people if p.get("reported_condition", {}).get("text") == cognitive.group(0)), None)
        if person is None:
            role = "PAPEL-ESTUDANTE" if any(p.get("papel_id") in {"PAPEL-TURMA", "PAPEL-ESTUDANTE"} for p in people) else "PAPEL-PESSOA-APOIADA"
            person = _person(context, role, "Parte do grupo: condição cognitiva relatada" if subgroup else "Pessoa ou grupo: condição cognitiva relatada", "cognitive-subgroup")
            person.update(quantidade=None, grupo_rotulo="alguns participantes" if subgroup else "participantes mencionados",
                          reported_condition={"text": cognitive.group(0), "start": cognitive.start(), "end": cognitive.end()})
            if group and subgroup:
                person["parent_group_id"] = group["id"]
                _assert(context, person["id"], "", "group_membership", group["id"], narrative)
            people.append(person)
        condition = _assert(context, person["id"], "", "reported_condition", cognitive.group(0), narrative)
        for correction in corrections:
            retired = _assert(context, person["id"], "", "reported_condition", correction["old"],
                              correction["source_text"], "RETIRADO_POR_CORRECAO")
            condition["supersedes"] = retired["id"]
    # Keep all declared roles, but an unnamed presenter has an unknown role.
    presentation = re.search(r"\b(apresent(?:ar|o|a|arei)|explic(?:ar|o|a|arei)|ensin(?:ar|o)|dar aula)\b", text)
    visual = re.search(r"\b(slides?|apresentacao)\b", text)
    access = re.search(r"\b(acess(?:ar|am|a|o)|consult(?:ar|am|a)|acompanhar|ler)\b.{0,55}\b(material|conteudo|arquivo|slides?|apresentacao)\b|\bconsulta individual\b", text)
    own_computer = re.search(r"\b(?:cada (?:um|aluno|estudante)|(?:seus|proprios?) computadores|computadores (?:proprios|deles)|cada qual)\b.{0,80}\b(?:computador|material|acessa|acessar|acompanhar)\b", text)
    if not own_computer:
        own_computer = re.search(r"\b(?:seus|proprios) computadores\b|\bcomputador de cada (?:pessoa|participante|aluno)\b", text)
    presenter = next((p for p in people if p["id"] == context.get("requester_participation_id")), None)
    if presenter is None:
        presenter = next((p for p in people if p.get("papel_id") == "PAPEL-PROFESSORA"), None)
    if presentation and visual and presenter is None:
        presenter = _person(context, "", "Quem apresenta", "presenter")
        people.append(presenter)
    receivers = [p for p in people if p.get("papel_id") in {"PAPEL-ESTUDANTE", "PAPEL-PESSOA-APOIADA"}]
    if not receivers and context.get("requester_relation") == "self":
        person = _person(context, "PAPEL-PESSOA-APOIADA", "Quem relata e realiza a atividade", "self")
        people.append(person)
        receivers = [person]
        context["requester_participation_id"] = person["id"]
    elif len(receivers) == 1 and context.get("requester_relation") == "self" and not context.get("requester_participation_id"):
        context["requester_participation_id"] = receivers[0]["id"]
    if group:
        receivers = [group, *[p for p in receivers if p.get("parent_group_id") == group["id"]]]

    def situation(key, label, task_ids, participants, source):
        actors = [presenter] if key == "presentation" else (participants if task_ids or key == "exercise" else [])
        recipients = [p for p in participants if p is not presenter] if key == "presentation" else []
        row = {"id": uid("SIT-", context["id"], key), "label": label,
               "task_ids": [t for t in task_ids if t in concepts],
               "participant_ids": list(dict.fromkeys(p["id"] for p in participants)),
               "actor_ids": [p["id"] for p in actors], "recipient_ids": [p["id"] for p in recipients],
               "env_ids": [], "resource_ids": [], "resource_states": [],
               "mode_ids": [], "need_ids": [], "barrier_ids": [], "source_text": source,
               "state": "RELATADO", "kind": key}
        context["situations"].append(row)
        for person in participants:
            if key == "presentation" and person is not presenter:
                continue
            for task in row["task_ids"]:
                if task not in person["tarefa_ids"]:
                    person["tarefa_ids"].append(task)
                _assert(context, person["id"], row["id"], "task", task, source)
        if not participants:
            for task in row["task_ids"]:
                _assert(context, context["id"], row["id"], "task", task, source, "INFERIDO_PARA_CONFIRMACAO")
        return row

    preparation = preparation_action(text)
    if presentation and visual:
        communication_tasks = list(dict.fromkeys(["TAR-COMUNICAR-CONTEUDO-1545B38", *[
            task for task in context.get("tarefas", []) if task in {"TAR-COMUNICAR-E-EXPRESSAR", "TAR-APRESENTAR-CONTEUDO-DIFERENTES-ESPACOS"}]]))
        row = situation("presentation", "Apresentação e explicação coletiva", communication_tasks,
                        [presenter, *receivers], source_clause(presentation.group(0)))
        row["mode_ids"] = [identifier for identifier in ("MOD-FALA", "MOD-TEXTO") if identifier in concepts]
        # Slides do not establish image, video or a projection device.
        row["resource_ids"] = [r for r in context.get("recursos_digitais", []) if r.startswith("RED-APRESENTACAO")]
        if not row["resource_ids"] and "RED-APRESENTACAO" in concepts:
            row["resource_ids"] = ["RED-APRESENTACAO"]
        for resource in row["resource_ids"]:
            _assert(context, presenter["id"], row["id"], "digital_resource", resource, narrative)
        for mode in row["mode_ids"]:
            _assert(context, presenter["id"], row["id"], "modality", mode, narrative, "INFERIDO_PARA_CONFIRMACAO")
    if access or (presentation and visual and own_computer):
        source = source_clause(access.group(0) if access else own_computer.group(0))
        access_task = ("TAR-OPERAR-SISTEMA" if "TAR-OPERAR-SISTEMA" in context.get("tarefas", [])
                       and re.search(r"\b(?:consultar|buscar|pesquisar|selecionar)\b.{0,45}\b(?:sistema|catalogo digital|aplicativo|plataforma)\b", text)
                       else "TAR-ACESSAR-COMPREENDER-CONTEUDO-DIGITAL")
        row = situation("material_access", "Consulta individual" if own_computer or re.search(r"\bconsulta individual\b", text) else "Acesso ao material",
                        [access_task], receivers, source)
        row["preparation_actor_ids"] = []
        row["resource_ids"] = [r for r in context.get("recursos_digitais", []) if r.startswith("RED-APRESENTACAO") and presentation and visual]
        if own_computer and "REC-COMPUTADOR" in concepts:
            row["resource_ids"].append("REC-COMPUTADOR")
            row["resource_states"].append({"resource_id": "REC-COMPUTADOR", "state": "DISPONIVEL_CONFIRMADO"})
            _assert(context, group["id"] if group else context["id"], row["id"], "resource_available", "REC-COMPUTADOR", own_computer.group(0))
        if re.search(r"\b(?:quero )?priorizar\b.{0,35}\b(?:consulta|acesso) individual\b", text):
            context["active_situation_id"] = row["id"]
    exercise = re.search(r"\b(exercicios?|atividades? praticas?)\b", text)
    if exercise:
        row = situation("exercise", "Realização de exercícios — meio não informado", [], receivers, source_clause(exercise.group(0)))
        _assert(context, group["id"] if group else context["id"], row["id"], "activity", "Realizar exercícios", exercise.group(0))
    if not context["situations"]:
        # A single context is not automatically a single actor. Assign only an
        # explicit sole supported actor; otherwise keep task attribution open.
        actors = receivers if len(receivers) == 1 else []
        if len(people) > 1:
            task_phrase = next((item.get("matched_text", "") for item in evidence if item.get("field") == "tarefas"), "")
            marker = text.find(words(task_phrase)) if task_phrase else -1
            before = text[:marker] if marker >= 0 else ""
            role_patterns = {"PAPEL-PROFESSORA": r"\b(?:professora?|docente)\b", "PAPEL-MEDIADOR": r"\bmediador[ao]?\b",
                             "PAPEL-ESTUDANTE": r"\b(?:alunos?|estudantes?)\b", "PAPEL-PESSOA-APOIADA": r"\b(?:pessoa|usuario|usuaria)\b"}
            matches = [(m.start(), role) for role, pattern in role_patterns.items() for m in re.finditer(pattern, before)]
            if matches:
                role = max(matches)[1]
                matched_people = [p for p in people if p.get("papel_id") == role]
                actors = matched_people if len(matched_people) == 1 else []
            else:
                actors = []
        task_ids = context.get("tarefas", [])
        if (len(people) == 1 and set(task_ids) == {"TAR-PRODUZIR-CONTEUDO-MULTIMODAL", "TAR-REVISAR-E-CONFIRMAR"}
                and re.search(r"\b(?:escrever|redigir|ditar|produzir)\b.{0,100}\b(?:revisar|corrigir)\b", text)):
            situation("production_review", "Produzir e revisar o mesmo conteúdo", task_ids, people, narrative)
        elif len(task_ids) <= 1:
            situation("reported_activity", "Atividade descrita", task_ids, actors if task_ids else people, narrative)
        else:
            # Do not distribute a multi-action narrative to the first actor.
            # Each source clause gives its own assignment, or an open scope.
            clauses = [part.strip() for part in re.split(r"(?<=[.!?;])\s+|\s+(?:e|enquanto)\s+(?=(?:a pessoa|o usuario|a usuaria|os alunos|a professora|o professor|o mediador|a mediadora)\b)", effective, flags=re.I) if part.strip()]
            grouped = {}
            for task in task_ids:
                matched = [words(e["matched_text"]) for e in evidence if e.get("field") == "tarefas" and e.get("concept_id") == task]
                candidates = [clause for clause in clauses if any(token and token in words(clause) for token in matched)]
                source = candidates[0] if len(candidates) == 1 else narrative
                local = words(source)
                role_matches = [(m.start(), role) for role, pattern in {
                    "PAPEL-PROFESSORA": r"\b(?:professora?|docente)\b", "PAPEL-MEDIADOR": r"\bmediador[ao]?\b",
                    "PAPEL-ESTUDANTE": r"\b(?:alunos?|estudantes?)\b", "PAPEL-PESSOA-APOIADA": r"\b(?:pessoa|usuario|usuaria)\b"
                }.items() for m in re.finditer(pattern, local)]
                owners = []
                if len(candidates) == 1 and role_matches:
                    found = {role for _, role in role_matches}
                    if len(found) == 1:
                        owners = [p for p in people if p.get("papel_id") in found]
                        if len(owners) > 1:
                            owners = []
                elif len(candidates) == 1 and len(people) == 1:
                    owners = people[:]
                key = (source, tuple(p["id"] for p in owners))
                grouped.setdefault(key, {"tasks": [], "owners": owners})["tasks"].append(task)
            for index, ((source, _), entry) in enumerate(grouped.items(), 1):
                situation(f"reported_activity_{index}", "Atividade: " + source[:100], entry["tasks"], entry["owners"], source)
    else:
        represented = {t for s in context["situations"] for t in s["task_ids"]}
        remaining = [t for t in context.get("tarefas", []) if t not in represented
                     and not (preparation and t == "TAR-PRODUZIR-CONTEUDO-MULTIMODAL")
                     and not ("TAR-OPERAR-SISTEMA" in represented and t == "TAR-ACESSAR-COMPREENDER-CONTEUDO-DIGITAL")]
        if remaining:
            situation("other_activity", "Outra atividade mencionada", remaining, [], narrative)
        context["tarefas"] = list(dict.fromkeys(t for s in context["situations"] for t in s["task_ids"]))
    if len(context["situations"]) == 1:
        context["active_situation_id"] = context["situations"][0]["id"]
    for person in people:
        _assert(context, person["id"], "", "participation", person.get("papel_id", ""), narrative)
        if person.get("reported_condition") and not any(a["subject_id"] == person["id"] and a["kind"] == "reported_condition" for a in context["assertions"]):
            _assert(context, person["id"], "", "reported_condition", person["reported_condition"]["text"], narrative)
    reverse_fields = {value: key for key, value in FIELDS.items()}
    single = context["situations"][0] if len(context["situations"]) == 1 else None
    for item in evidence:
        kind = reverse_fields.get(item.get("field"))
        value = item.get("concept_id")
        if not kind or not value or value not in context.get(item["field"], []):
            continue
        if kind == "task":
            # Task ownership was established above. A global lexical hit must
            # not add the preparer's task to every recipient's situation.
            continue
        subject = context["id"]
        scoped = single
        if not scoped and kind != "characteristic":
            # A local resource/environment is never broadcast into another
            # activity. Ambiguous references remain at narrative scope.
            token = words(item.get("matched_text", ""))
            local = [s for s in context["situations"] if token and token in words(s["source_text"])
                     and (s["source_text"] != narrative or len(source_clauses) == 1)]
            scoped = local[0] if len(local) == 1 else None
        sid = scoped["id"] if scoped else ""
        if kind == "characteristic":
            if len(receivers) == 1:
                subject = receivers[0]["id"]
                receivers[0]["caracteristica_ids"].append(value)
            else:
                sid = ""  # No implicit broadcast of a personal characteristic.
        state = ("CONFLITO" if item.get("status") == "CONFLITO_A_CONFIRMAR" else
                 "INFERIDO_PARA_CONFIRMACAO" if "INFERIDO" in item.get("status", "") else "RELATADO")
        _assert(context, subject, sid, kind, value, item.get("matched_text", narrative), state)
        if state == "CONFLITO":
            # Do not pass the contradictory resource through legacy arrays.
            context[item["field"]] = [v for v in context[item["field"]] if v != value]
            continue
        if scoped and kind in SITUATION_FIELDS and value not in scoped[SITUATION_FIELDS[kind]]:
            scoped[SITUATION_FIELDS[kind]].append(value)
        if scoped and kind in RESOURCE_STATES:
            scoped["resource_ids"] = list(dict.fromkeys(scoped["resource_ids"] + [value]))
            if not any(r["resource_id"] == value for r in scoped["resource_states"]):
                scoped["resource_states"].append({"resource_id": value, "state": RESOURCE_STATES[kind]})
    if context.get("objetivo"):
        _assert(context, context["id"], "", "objective", context["objetivo"], context["objetivo"])
    # Preserve a functional observation even when the lexicon cannot yet map
    # it. Pronouns in a multi-person, multi-activity narrative stay unassigned.
    for clause in re.split(r"(?<=[.!?;])\s+", effective):
        local = words(clause)
        if not re.search(r"\b(?:dificuldade(?:s)? (?:de|para|em)|nao (?:consigo|conseguem|consegue)|esquece(?:m)?|(?:se )?perde(?:m)?|fadiga)\b", local):
            continue
        if not re.search(r"\b(?:lembrar|retomar|localizar|encontrar|acompanhar|ler|ouvir|entender|compreender|operar|usar|navegar|enxergar|organizar|concentrar|atencao|informacao|atividade|sequencia|digitar)\b", local):
            continue
        observed_owners = clause_owners(clause, people, context)
        subject = observed_owners[0]["id"] if len(observed_owners) == 1 else receivers[0]["id"] if len(receivers) == 1 else context["id"]
        _assert(context, subject, single["id"] if single else "", "functional_observation", clause.strip(), clause.strip())
    context["unmapped_text"] = [narrative]
    enrich_operational_observations(context, people, effective, concepts)
    refresh_preparation_participation(context, people)
    extract_reported_facts(context, people, effective)
    # A computer is not proof of a readable display. Use the explicitly stated
    # readable screen and editable recognized output in the same personal scope.
    for person in people:
        for situation in context["situations"]:
            facts = [f for f in context["situated_facts"] if f["participant_id"] == person["id"]
                     and f["situation_id"] == situation["id"] and f["value"] is True]
            visual = next((f for f in facts if f["fact_id"].endswith("#CanReviewVisualText")), None)
            editable = next((f for f in facts if f["fact_id"].endswith("#EditableText")), None)
            if visual and editable:
                row = _assert(context, person["id"], situation["id"], "functional_fact",
                              {"fact_id": "https://w3id.org/mado/experimental/v2#Display", "value": True,
                               "label": FACT_LABELS["Display"]}, visual["source_text"] + " / " + editable["source_text"])
                _project(context, people, row)
    return effective


def question_id(field, situation_id="", participant_id=""):
    return uid("Q-", field, situation_id, participant_id)


def expanded_matrices(matrices):
    for original in matrices:
        groups = original.get("inference_contract", {}).get("trigger_groups", [])
        if not groups:
            yield original
        else:
            for index, group in enumerate(groups, 1):
                row = copy.deepcopy(original)
                row.update({key: copy.deepcopy(group[key]) for key in ("sinais_relato", "requisito_ids", "funcao_ids", "knowledge_ids") if key in group})
                row["trigger_group_id"] = group.get("id", f"{original['id']}-G{index}")
                row["inference_contract"].update({key: copy.deepcopy(group[key]) for key in ("claim_ids", "support", "eligibility") if key in group})
                yield row


def questions(context, people, legacy):
    """Decision-changing uncertainties precede optional template-specific questions."""
    rows = []
    situations = [s for s in context.get("situations", []) if s.get("state") != "RETIRADO_POR_CORRECAO"]
    active = next((s for s in situations if s["id"] == context.get("active_situation_id")), None)
    def add(field, label, reason, priority, situation=None, participant=None, **extra):
        sid = situation["id"] if situation else ""
        pid = participant["id"] if participant else ""
        rows.append({"id": question_id(field, sid, pid), "field": field, "question": label, "label": label,
                     "reason": reason, "context_label": situation["label"] if situation else "Situações relatadas",
                     "situation_id": sid, "participant_id": pid, "priority": priority,
                     "required": False, "decision_relevant": True, "candidate_component_ids": [], **extra})
    priority_options = [s for s in situations if s.get("task_ids")]
    if len(priority_options) > 1 and not active:
        add("active_situation_id", "Qual parte você quer analisar primeiro?",
            "A prioridade organiza a análise; as outras atividades continuam registradas.", -30, type="single",
            options=[{"id": s["id"], "label": s["label"]} for s in priority_options])
    if situations and not context.get("recursos_digitais") and not any(s.get("resource_ids") for s in situations):
        if not any(a["kind"] == "digital_use" and a["state"] in ACTIVE_STATES for a in context.get("assertions", [])):
            add("digital_use", "Há algum material ou recurso digital nessa atividade?",
                "Distingue uso atual, possibilidade a considerar e uma restrição ao uso de recursos digitais.", -15,
                situation=active or situations[0], type="single", options=[
                    {"id": "already_uses", "label": "Já é usado"}, {"id": "consider", "label": "Quero considerar"},
                    {"id": "not_intended", "label": "Não pode ou não pretendo usar"}, {"id": "unknown", "label": "Ainda não sei"}])
    targets = [active] if active else situations[:1]
    for situation in targets:
        if not situation:
            continue
        unscoped = [a for a in context.get("assertions", []) if a["kind"] == "functional_observation"
                    and a["state"] in ACTIVE_STATES and (not a.get("situation_id") or a["subject_id"] == context["id"])]
        if unscoped and (len(situations) > 1 or len([p for p in people if p.get("papel_id") in {"PAPEL-ESTUDANTE", "PAPEL-PESSOA-APOIADA"}]) > 1):
            observation = unscoped[0]
            candidates = [p for p in people if p.get("papel_id") in {"PAPEL-ESTUDANTE", "PAPEL-PESSOA-APOIADA"}]
            add("observation_scope", f"A dificuldade já relatada — “{observation['value']}” — refere-se a quem e a qual atividade?",
                "Preserva a dificuldade informada sem atribuí-la a todos ou misturar as duas interações.", -5,
                situation=situation, type="single", assertion_id=observation["id"], options=[
                    {"id": p["id"] + "|" + s["id"], "label": p.get("label", p["id"]) + " — " + s["label"]}
                    for p in candidates for s in situations if p["id"] in s.get("participant_ids", []) and s.get("task_ids")])
            continue
        affected = [p for p in people if p["id"] in situation.get("participant_ids", []) and p.get("reported_condition")]
        for person in affected:
            known = any(a["kind"] == "functional_observation" and a["subject_id"] == person["id"]
                        and a["situation_id"] == situation["id"] and a["state"] in ACTIVE_STATES for a in context.get("assertions", []))
            derived = any(r.get("participant_id") == person["id"] and r.get("status") != "CONFLITO_A_CONFIRMAR"
                          for r in context.get("access_requirements", []))
            if not known and not derived:
                add("functional_observation", f"Em {situation['label'].lower()}, o que essas pessoas precisam conseguir fazer e ainda encontram dificuldade?",
                    "A condição relatada não informa, sozinha, que apoio muda a participação nessa atividade.", -5,
                    situation=situation, participant=person, type="text")
    answers = {a["question_id"] for a in context.get("question_answers", []) if a.get("state") in {"ANSWERED", "UNKNOWN"}}
    for question in legacy:
        q = copy.deepcopy(question)
        if q["field"] == "tarefas" and context.get("tarefas"):
            # Lack of a canned pattern does not change the narrated activity.
            continue
        q.setdefault("situation_id", active["id"] if active else (situations[0]["id"] if len(situations) == 1 else ""))
        q["id"] = question_id(q["field"], q["situation_id"], q.get("participant_id", ""))
        rows.append(q)
    unique_rows = {}
    for q in sorted(rows, key=lambda item: (item.get("priority", 50), item["id"])):
        if q["id"] not in answers and q["id"] not in unique_rows:
            unique_rows[q["id"]] = q
    context.setdefault("question_manifest", {}).update({q["id"]: copy.deepcopy(q) for q in rows})
    return list(unique_rows.values())[:3]


def sync_legacy_edits(context, people, body, previous):
    """Keep explicit legacy review controls in the same assertion ledger."""
    if not context.get("situated_version"):
        return
    active = context.get("active_situation_id", "")
    single = len(context.get("situations", [])) == 1
    sid = active or (context["situations"][0]["id"] if single else "")
    for kind, field in FIELDS.items():
        if field not in body or context.get(field, []) == previous.get(field, []):
            continue
        for row in context["assertions"]:
            if row["kind"] == kind and row["state"] in ACTIVE_STATES and row["value"] not in context.get(field, []):
                row["state"] = "RETIRADO_POR_CORRECAO"
                _project(context, people, row, remove=True)
        for value in context.get(field, []):
            if not any(a["kind"] == kind and a["value"] == value and a["state"] in ACTIVE_STATES for a in context["assertions"]):
                row = _assert(context, context["id"], sid, kind, value, "Informado na revisão")
                _project(context, people, row)
    if "participations" in body:
        by_id = {p["id"]: p for p in people}
        for row in context["assertions"]:
            if row["subject_id"] != context["id"] and row["subject_id"] not in by_id and row["state"] in ACTIVE_STATES:
                row["state"] = "RETIRADO_POR_CORRECAO"
                _project(context, people, row, remove=True)
            elif row["kind"] == "group_membership" and row["value"] not in by_id and row["state"] in ACTIVE_STATES:
                row["state"] = "RETIRADO_POR_CORRECAO"
        for person in people:
            if person.get("parent_group_id") and person["parent_group_id"] not in by_id:
                person.pop("parent_group_id", None)
        for situation in context.get("situations", []):
            for field in ("participant_ids", "actor_ids", "recipient_ids", "preparation_actor_ids"):
                situation[field] = [p for p in situation.get(field, []) if p in by_id]
        for person in people:
            applicable = [s for s in context.get("situations", []) if person["id"] in s.get("participant_ids", [])]
            psid = applicable[0]["id"] if len(applicable) == 1 else (sid if single else "")
            for kind, field in PERSON_FIELDS.items():
                for row in context["assertions"]:
                    if row["subject_id"] == person["id"] and row["kind"] == kind and row["state"] in ACTIVE_STATES and row["value"] not in person.get(field, []):
                        row["state"] = "RETIRADO_POR_CORRECAO"
                for value in person.get(field, []):
                    if not any(a["subject_id"] == person["id"] and a["kind"] == kind and a["value"] == value and a["state"] in ACTIVE_STATES for a in context["assertions"]):
                        _assert(context, person["id"], psid, kind, value, "Informado na revisão da participação")


def _validate_assertion(row, context, people, concepts):
    if not isinstance(row, dict) or row.get("kind") not in KINDS:
        raise ValueError("Tipo de afirmação não reconhecido.")
    if row.get("state", "RELATADO") not in STATES:
        raise ValueError("Estado de afirmação não reconhecido.")
    if row.get("subject_id", context["id"]) not in {context["id"], *[p["id"] for p in people]}:
        raise ValueError("A afirmação precisa identificar um participante ou o contexto existente.")
    if row.get("situation_id", "") not in {"", *[s["id"] for s in context.get("situations", [])]}:
        raise ValueError("Situação não reconhecida.")
    if row["kind"] in TYPE_FOR_KIND and row.get("value"):
        concept = concepts.get(row["value"], {})
        expected = TYPE_FOR_KIND[row["kind"]]
        if (expected == "PAPEL" and not str(row["value"]).startswith("PAPEL-")) or (expected != "PAPEL" and concept.get("tipo") != expected) or not concept:
            raise ValueError("O valor da afirmação não corresponde a um conceito existente do tipo esperado.")
    if row["kind"] == "group_count" and row.get("value") is not None:
        if isinstance(row["value"], bool) or not isinstance(row["value"], int) or row["value"] < 1:
            raise ValueError("A quantidade precisa ser positiva ou desconhecida.")
    if row["kind"] == "digital_use" and row.get("value") not in {"already_uses", "consider", "not_intended", "unknown"}:
        raise ValueError("Intenção de uso digital não reconhecida.")
    if row["kind"] == "functional_fact":
        value = row.get("value")
        if (not isinstance(value, dict) or not isinstance(value.get("fact_id"), str) or not value["fact_id"]
                or len(value["fact_id"]) > 200 or value.get("value") is not None and not isinstance(value.get("value"), bool)):
            raise ValueError("Uma condição deve ter identificador e valor sim, não ou desconhecido.")


def _project(context, people, assertion, remove=False):
    kind, value = assertion["kind"], assertion["value"]
    person = next((p for p in people if p["id"] == assertion["subject_id"]), None)
    situation = next((s for s in context.get("situations", []) if s["id"] == assertion.get("situation_id")), None)
    def update_list(target, field):
        values = target.setdefault(field, [])
        if remove:
            target[field] = [v for v in values if v != value]
        elif value not in values:
            values.append(value)
    if kind in FIELDS:
        # Global arrays remain a compatibility projection, not personal facts.
        if not remove or not any(a["id"] != assertion["id"] and a["kind"] == kind and a["value"] == value and a["state"] in ACTIVE_STATES for a in context["assertions"]):
            update_list(context, FIELDS[kind])
    if person and kind in PERSON_FIELDS:
        if not remove or not any(a["id"] != assertion["id"] and a["subject_id"] == person["id"]
                                 and a["kind"] == kind and a["value"] == value and a["state"] in ACTIVE_STATES for a in context["assertions"]):
            update_list(person, PERSON_FIELDS[kind])
    if situation and kind in SITUATION_FIELDS:
        if not remove or not any(a["id"] != assertion["id"] and a.get("situation_id") == situation["id"]
                                 and a["kind"] == kind and a["value"] == value and a["state"] in ACTIVE_STATES for a in context["assertions"]):
            update_list(situation, SITUATION_FIELDS[kind])
    if person and situation and kind == "task":
        if not remove:
            for field in ("participant_ids", "actor_ids"):
                if person["id"] not in situation.setdefault(field, []):
                    situation[field].append(person["id"])
        elif not any(a["id"] != assertion["id"] and a["subject_id"] == person["id"] and a.get("situation_id") == situation["id"]
                     and a["kind"] == "task" and a["state"] in ACTIVE_STATES for a in context["assertions"]):
            situation["actor_ids"] = [p for p in situation.get("actor_ids", []) if p != person["id"]]
    if kind in RESOURCE_STATES and situation and not person:
        situation["resource_states"] = [r for r in situation.get("resource_states", []) if r["resource_id"] != value]
        if not remove:
            situation["resource_states"].append({"resource_id": value, "state": RESOURCE_STATES[kind]})
    if person and kind == "reported_condition":
        if remove:
            person.pop("reported_condition", None)
        else:
            person["reported_condition"] = {"text": value}
    if person and kind == "group_count":
        person["quantidade"] = None if remove else value
    if person and kind == "participation":
        person["papel_id"] = "" if remove else value
    if kind == "activity" and assertion.get("activity_phase") == "PREPARATION":
        refresh_preparation_participation(context, people)
    if kind == "objective" and assertion["subject_id"] == context["id"]:
        context["objetivo"] = "" if remove else value
    if kind == "functional_fact":
        key = (assertion["subject_id"], assertion.get("situation_id", ""), value["fact_id"])
        context["situated_facts"] = [fact for fact in context.get("situated_facts", [])
                                     if (fact["participant_id"], fact["situation_id"], fact["fact_id"]) != key]
        if not remove:
            context["situated_facts"].append({"participant_id": key[0], "situation_id": key[1], "fact_id": key[2],
                                             "value": value.get("value"), "assertion_id": assertion["id"],
                                             "label": value.get("label", key[2]),
                                             "state": assertion["state"], "source_text": assertion["source_text"]})


def review(context, people, body, concepts):
    """Apply validated edits to copies; callers commit only after all validation."""
    changes = copy.deepcopy(body.get("assertion_changes", []))
    if not isinstance(changes, list):
        raise ValueError("As alterações devem formar uma lista.")
    revision = context.get("revision", 0) + 1
    changed_ids = []
    facts = body.get("situated_facts", [])
    if not isinstance(facts, list):
        raise ValueError("As condições situadas devem formar uma lista.")
    for fact in facts:
        if not isinstance(fact, dict):
            raise ValueError("Condição situada inválida.")
        row = {"subject_id": fact.get("participant_id", ""), "situation_id": fact.get("situation_id", ""),
               "kind": "functional_fact", "value": {"fact_id": fact.get("fact_id"), "value": fact.get("value"),
                                                       "label": str(fact.get("label") or fact.get("fact_id") or "")},
               "source_text": str(fact.get("source_text") or "Resposta explícita sobre a condição situada"), "state": "RELATADO"}
        _validate_assertion(row, context, people, concepts)
        if not row["situation_id"]:
            raise ValueError("A condição precisa identificar a situação em que foi informada.")
        situation = next(s for s in context["situations"] if s["id"] == row["situation_id"])
        if row["subject_id"] != context["id"] and row["subject_id"] not in situation.get("participant_ids", []):
            raise ValueError("O participante não está vinculado à situação informada.")
        previous = next((a for a in context["assertions"] if a["state"] in ACTIVE_STATES and a["kind"] == "functional_fact"
                         and a["subject_id"] == row["subject_id"] and a.get("situation_id") == row["situation_id"]
                         and a["value"]["fact_id"] == row["value"]["fact_id"]), None)
        changes.append({"op": "replace" if previous else "add", "id": previous["id"] if previous else "", "assertion": row})
    for change in changes:
        if not isinstance(change, dict) or change.get("op") not in {"add", "replace", "remove"}:
            raise ValueError("Operação de revisão não reconhecida.")
        previous = None
        if change["op"] != "add":
            previous = next((a for a in context["assertions"] if a["id"] == change.get("id") and a["state"] in ACTIVE_STATES | {"CONFLITO"}), None)
            if not previous:
                raise ValueError("Afirmação a revisar não encontrada ou já retirada.")
        new = None
        if change["op"] != "remove":
            new = {**(copy.deepcopy(previous) if previous else {}), **change.get("assertion", {})}
            new.setdefault("subject_id", context["id"])
            new.setdefault("situation_id", "")
            new.setdefault("source_text", "Correção informada na revisão")
            new["state"] = change.get("assertion", {}).get("state", "RELATADO")
            _validate_assertion(new, context, people, concepts)
        if previous:
            previous["state"] = "RETIRADO_POR_CORRECAO"
            _project(context, people, previous, remove=True)
            changed_ids.append(previous["id"])
        if new:
            new["id"] = uid("AS-", revision, len(context["assertions"]), new["subject_id"], new["situation_id"], new["kind"], new.get("value"))
            new["revision"] = revision
            if previous:
                new["supersedes"] = previous["id"]
            context["assertions"].append(new)
            if new["state"] in ACTIVE_STATES:
                _project(context, people, new)
            changed_ids.append(new["id"])
        context.setdefault("review_changes", []).append({"op": change["op"], "previous_id": previous["id"] if previous else "", "new_id": new["id"] if new else "", "revision": revision})
    if "active_situation_id" in body:
        value = body["active_situation_id"]
        if value not in {"", *[s["id"] for s in context.get("situations", [])]}:
            raise ValueError("A prioridade precisa identificar uma situação registrada.")
        context["active_situation_id"] = value
    answers = body.get("question_answers", [])
    if not isinstance(answers, list):
        raise ValueError("As respostas devem formar uma lista.")
    for answer in answers:
        if not isinstance(answer, dict) or not isinstance(answer.get("question_id"), str) or answer.get("state", "ANSWERED") not in {"ANSWERED", "UNKNOWN"}:
            raise ValueError("Resposta de acompanhamento inválida.")
        question = context.get("question_manifest", {}).get(answer["question_id"])
        if not question:
            raise ValueError("Pergunta não encontrada no acompanhamento deste caso.")
        value = answer.get("value")
        state = answer.get("state", "ANSWERED")
        if isinstance(value, str) and words(value) in {"nao sei", "ainda nao sei", "unknown"}:
            state = "UNKNOWN"
        for old in context["assertions"]:
            if old.get("question_id") == question["id"] and old["state"] in ACTIVE_STATES:
                old["state"] = "RETIRADO_POR_CORRECAO"
                _project(context, people, old, remove=True)
                changed_ids.append(old["id"])
        if state == "ANSWERED" and question["field"] == "active_situation_id":
            if value not in {s["id"] for s in context.get("situations", [])}:
                raise ValueError("Situação prioritária não reconhecida.")
            context["active_situation_id"] = value
        elif state == "ANSWERED" and question["field"] == "observation_scope":
            if value not in {option["id"] for option in question.get("options", [])}:
                raise ValueError("O alcance da dificuldade precisa corresponder a uma opção apresentada.")
            subject, situation = value.split("|", 1)
            if not any(p["id"] == subject for p in people) or not any(s["id"] == situation and subject in s.get("participant_ids", []) for s in context["situations"]):
                raise ValueError("O participante ou a situação mudou; revise o alcance da dificuldade.")
            previous = next((a for a in context["assertions"] if a["id"] == question.get("assertion_id") and a["state"] in ACTIVE_STATES), None)
            if previous is None:
                raise ValueError("A dificuldade já foi retirada ou corrigida.")
            previous["state"] = "RETIRADO_POR_CORRECAO"
            row = _assert(context, subject, situation, "functional_observation", previous["value"], previous["source_text"], supersedes=previous["id"])
            changed_ids.extend([previous["id"], row["id"]])
        elif state == "ANSWERED" and question["field"] in {"digital_use", "functional_observation"}:
            if not isinstance(value, str) or not value.strip():
                raise ValueError("Informe uma resposta ou indique que ainda não sabe.")
            row = {"subject_id": question.get("participant_id") or context["id"], "situation_id": question.get("situation_id", ""),
                   "kind": question["field"], "value": value.strip(), "source_text": value.strip(), "state": "RELATADO"}
            _validate_assertion(row, context, people, concepts)
            _assert(context, row["subject_id"], row["situation_id"], row["kind"], row["value"], row["source_text"], question_id=question["id"])
        context["question_answers"] = [a for a in context.get("question_answers", []) if a["question_id"] != answer["question_id"]]
        context["question_answers"].append({**copy.deepcopy(answer), "state": state, "revision": revision})
    if changes or answers or "active_situation_id" in body:
        context["revision"] = revision
    if changed_ids:
        # Function/candidate results are recomputed by the engine; never reuse
        # support from a retired statement. Explicit independent needs survive.
        affected_people = {a["subject_id"] for a in context["assertions"] if a["id"] in changed_ids
                           and a["state"] == "RETIRADO_POR_CORRECAO" and a["kind"] in {"reported_condition", "characteristic"}}
        removed = [r for r in context.get("access_requirements", []) if r.get("participant_id") in affected_people
                   or set(r.get("assertion_ids", [])) & set(changed_ids)]
        context["access_requirements"] = [r for r in context.get("access_requirements", []) if r not in removed]
        protected = {a["value"] for a in context["assertions"] if a["kind"] == "need" and a["state"] in ACTIVE_STATES}
        retained = {n for r in context["access_requirements"] for n in r.get("requirement_ids", [])}
        orphaned = {n for r in removed for n in r.get("requirement_ids", [])} - protected - retained
        context["necessidades"] = [n for n in context.get("necessidades", []) if n not in orphaned]
        derived_functions = {row["function_id"] for row in context.get("function_derivation", [])}
        context["function_derivation"] = []
        context["funcoes_requeridas_ids"] = [f for f in context.get("funcoes_requeridas_ids", []) if f not in derived_functions]
    if body.get("mapping_confirmed"):
        if any(a["state"] == "CONFLITO" for a in context.get("assertions", [])):
            raise ValueError("Resolva as afirmações conflitantes antes de confirmar a interpretação.")
        for row in context.get("assertions", []):
            if row["state"] in ACTIVE_STATES:
                row["state"] = "CONFIRMADO"
        for row in context.get("situations", []):
            row["state"] = "CONFIRMADO"
        for row in context.get("situated_facts", []):
            row["state"] = "CONFIRMADO"
    return changed_ids
