"""AMADO public deterministic engine. No HTTP service, history or case-file writes."""

from __future__ import annotations
import copy
import html
import hashlib
import json
import re
import sys
import unicodedata
import uuid
import warnings
from datetime import datetime, timezone
from pathlib import Path
from execution_trace import ExecutionEvidence, build_explanation

ROOT = Path(__file__).resolve().parent
for dependency_path in (ROOT / "vendor",):
    if dependency_path.exists():
        sys.path.insert(0, str(dependency_path))
        break
warnings.filterwarnings("ignore", category=DeprecationWarning)
from rdflib import Graph, Literal, Namespace, RDF
from rdflib.namespace import SKOS

MADO = Namespace("https://w3id.org/mado#")
ONTOLOGY = ROOT / "ontology" / "mado-combined.ttl"
DATA_JSON = ROOT / "data" / "knowledge-base.json"
UI_VOCAB_JSON = ROOT / "data" / "interface-vocabulary.json"
QUERY_DIR = ROOT / "queries"
VERSION = "1.4.0-rc1"
UI_VERSION = "AMADO-web-1.4.0-rc1"
PRACTICAL_COPY = {
    "PAD-ORGANIZAR-CONTEUDO-PERSISTENTE": {
        "group": "start",
        "title": "Texto para organizar e permitir retomada",
        "text": "Divida o material digital em partes curtas e registre a ideia principal, a autoria e o que ainda precisa ser revisto.",
        "relation": "O texto organiza o que foi dito, desenhado ou mostrado e permite que a informação seja retomada sem depender da memória da fala.",
    },
    "PAD-EXPRESSAO-AUTORAL-FALA-AUDIO": {
        "group": "combine",
        "title": "Fala e áudio para preservar a autoria",
        "text": "Deixe o estudante explicar cada parte com a própria voz. Guarde também um texto curto para ele conferir ou refazer.",
        "relation": "A fala preserva a forma autoral de expressão; o áudio mantém essa contribuição recuperável e o texto curto apoia revisão e correção.",
    },
    "PAD-REPRESENTACAO-VISUAL-EXPLICADA": {
        "group": "combine",
        "title": "Imagem e desenho para representar relações",
        "text": "Escolha as imagens e os desenhos com o estudante. Explique em texto ou fala o que cada um mostra.",
        "relation": "Imagem e desenho mostram relações visuais; texto ou fala explicam o significado para quem não percebe ou interpreta o visual da mesma forma.",
    },
    "PAD-VIDEO-PROCESSO": {
        "group": "conditional",
        "title": "Vídeo, quando for preciso mostrar processo ou mudança",
        "text": "Use vídeo apenas para mostrar uma mudança, um processo ou um contraste. Pause, explique e ofereça legenda e descrição do conteúdo visual.",
        "relation": "O vídeo apresenta a mudança no tempo; pausas, fala, legenda e descrição preservam o conteúdo e tornam seus pontos principais recuperáveis.",
    },
    "PAD-JOGO-CONSOLIDACAO-FEEDBACK": {
        "group": "conditional",
        "title": "Jogo, quando for preciso relacionar e conferir",
        "text": "Use um jogo curto apenas para ordenar, comparar ou relacionar ideias. Explique cada resposta e permita uma nova tentativa.",
        "relation": "A ação no jogo testa uma relação; o feedback em texto ou fala explica o resultado e orienta a retomada, sem transformar o jogo em recompensa.",
    },
    "PAD-PAPEIS-TURNOS-AUTORIA": {
        "group": "participation",
        "title": "Fala organizada por papéis e transições",
        "text": "Combine antes quem fala, quando a turma pergunta e como uma ideia interrompida será retomada.",
        "relation": "A fala continua sendo espaço de participação, enquanto o roteiro visível marca turnos, transições e pontos de retomada.",
    },
    "PAD-REVISAO-CONFIRMACAO": {
        "group": "review",
        "title": "Texto e fala para revisar e confirmar",
        "text": "Revise cada parte com o estudante e peça a um colega que diga o que compreendeu antes da publicação.",
        "relation": "O registro escrito mantém a versão a conferir; a explicação oral do estudante e a devolutiva de um colega revelam o que precisa ser ajustado.",
    },
    "PAD-ORIENTACAO-AUDIO-RECUPERAVEL": {
        "group": "start",
        "title": "Dê uma orientação que possa ser repetida",
        "text": "Apresente orientações curtas por áudio e deixe a pessoa repetir a última mensagem quando quiser.",
        "relation": "O áudio apresenta a orientação no momento da ação; a repetição e o registro textual mantêm seu conteúdo disponível para conferência.",
    },
    "PAD-RETORNO-HAPTICO-RUIDO": {
        "group": "combine",
        "title": "Acrescente um aviso por vibração",
        "text": "Use uma vibração simples para avisar que há nova orientação, mantendo o conteúdo disponível em áudio ou texto.",
        "relation": "A vibração chama a atenção sem depender da escuta; o áudio ou o texto comunica o significado completo do aviso.",
    },
    "PAD-CONTEUDO-WEB-EQUIVALENTE": {
        "group": "start",
        "title": "Preserve o significado da página",
        "text": "Descreva o que cada elemento visual comunica e organize títulos e relações para que o leitor de tela apresente o conteúdo na ordem correta.",
        "relation": "A organização textual preserva estrutura e relações; a descrição verbaliza o conteúdo visual e o leitor de tela o apresenta por voz e navegação sequencial.",
    },
    "PAD-COMUNICACAO-MULTIFORMATO": {
        "group": "start",
        "title": "Ofereça mais de uma forma de comunicar",
        "text": "Permita escrever ou falar a mensagem. Mostre o texto reconhecido antes do envio, ofereça leitura em voz alta e informe claramente se houve envio ou erro.",
        "relation": "A voz pode produzir a mensagem, o texto visível permite revisar e corrigir, e a leitura em voz confirma o conteúdo antes e depois do envio.",
    },
}
PRACTICAL_HEADLINES = {
    "PAD-ORGANIZAR-CONTEUDO-PERSISTENTE": "Organize com o estudante, a professora e a turma um material digital em partes curtas. Preserve a autoria do estudante e reserve momentos para perguntas, revisão e ajustes.",
    "PAD-ORIENTACAO-AUDIO-RECUPERAVEL": "Ofereça orientações curtas por áudio, que possam ser repetidas, e use outro aviso quando o ambiente dificultar a escuta.",
    "PAD-CONTEUDO-WEB-EQUIVALENTE": "Organize o conteúdo para que as informações visuais também possam ser compreendidas e navegadas com leitor de tela.",
    "PAD-COMUNICACAO-MULTIFORMATO": "Permita que a pessoa produza e compreenda mensagens usando texto ou voz, sempre com confirmação e possibilidade de correção.",
}


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def unique(values):
    seen, result = (set(), [])
    for value in values or []:
        marker = (
            json.dumps(value, ensure_ascii=False, sort_keys=True)
            if isinstance(value, dict)
            else str(value)
        )
        if marker not in seen:
            seen.add(marker)
            result.append(value)
    return result


def normalize_text(value):
    value = unicodedata.normalize("NFD", str(value or "").casefold())
    value = "".join((char for char in value if unicodedata.category(char) != "Mn"))
    return re.sub("[^a-z0-9]+", " ", value).strip()


def local_id(value):
    return str(value).rsplit("#", 1)[-1]


class DecisionEngine:
    context_fields = {
        "tarefas": "tarefas",
        "caracteristicas_pessoa": "caracteristicas_pessoa",
        "recursos_digitais": "recursos_digitais",
        "barreiras": "barreiras",
        "necessidades": "necessidades",
        "ambientes": "ambientes",
        "modalidades_disponiveis": "modalidades",
        "recursos_disponiveis": "recursos_disponiveis",
        "recursos_impedidos": "recursos_impedidos",
        "recursos_propostos": "recursos_propostos",
        "funcoes_requeridas_ids": "funcoes_decisorias",
    }

    def __init__(self):
        self.graph = Graph()
        with ONTOLOGY.open("rb") as handle:
            self.graph.parse(file=handle, format="turtle")
        self.data = json.loads(DATA_JSON.read_text(encoding="utf-8"))
        self.ui_vocab = json.loads(UI_VOCAB_JSON.read_text(encoding="utf-8"))
        self.queries = {
            path.stem: path.read_text(encoding="utf-8")
            for path in sorted(QUERY_DIR.glob("CQ-*.rq"))
        }
        self.concepts = {row["id"]: row for row in self.data["context_elements"]}
        self.contexts = {row["id"]: row for row in self.data["contexts"]}
        self.knowledge = {row["id"]: row for row in self.data["knowledge"]}
        self.criteria = {row["id"]: row for row in self.data["criteria"]}
        self.criterion_origins = {
            row["id"]: row for row in self.data.get("criterion_origins", [])
        }
        self.sources = {row["id"]: row for row in self.data["sources"]}
        self.excerpts = {row["id"]: row for row in self.data["excerpts"]}
        self.decisions = {row["id"]: row for row in self.data["decisions"]}
        self.results = {row["id"]: row for row in self.data["results"]}
        self.studies = {row["id"]: row for row in self.data.get("studies", [])}
        self.artifacts = {row["id"]: row for row in self.data.get("artifacts", [])}
        self.personas = {
            row.get("ontology_id") or row.get("id") or row.get("persona"): row
            for row in self.data.get("personas", [])
        }
        self.articulations = {
            row["id"]: row for row in self.data.get("articulations", [])
        }
        self.transfer_mappings = self.data.get("transfer_mappings", [])
        self.participations = self.data.get("context_participations", [])
        self.components = [
            row
            for row in self.data["decision_components"]
            if row.get("active_in_rc4", row.get("active_in_rc3"))
        ]
        self.current = None
        self._evidence = None
        self._record_checks = False
        self.start_context("CTX-TRANSFERENCIA-RECURSO-DIGITAL-01")

    def _check(self, stage, subject, rule, outcome, message, **details):
        if self._evidence is not None and self._record_checks:
            return self._evidence.check(stage, subject, rule, outcome, message, **details)
        return None

    def _task_path(self, start, end):
        """Return an actual shortest skos:broader witness, not a guessed hierarchy."""
        queue = [[start]]
        seen = set()
        while queue:
            path = queue.pop(0)
            if path[-1] == end:
                return path
            if path[-1] in seen:
                continue
            seen.add(path[-1])
            for parent in sorted(self.graph.objects(MADO[path[-1]], SKOS.broader), key=str):
                queue.append(path + [local_id(parent)])
        return []

    def label(self, identifier):
        public = self.ui_vocab.get("concepts", {}).get(identifier, {})
        return public.get("label") or self.concepts.get(identifier, {}).get(
            "rotulo", identifier
        )

    def technical_label(self, identifier):
        return self.concepts.get(identifier, {}).get("rotulo", identifier)

    def labels(self, identifiers):
        return [self.label(identifier) for identifier in identifiers or []]

    def participation_payload(self, rows):
        return [
            {
                "id": row["id"],
                "papel_id": row["papel_id"],
                "papel": self.label(row["papel_id"]),
                "caracteristicas": [
                    {
                        "id": identifier,
                        "label": self.label(identifier),
                        "categoria": self.concepts.get(identifier, {}).get(
                            "categoria_caracteristica", ""
                        ),
                    }
                    for identifier in row.get("caracteristica_ids", [])
                ],
                "tarefas": self.labels(row.get("tarefa_ids")),
                "modalidades": self.labels(row.get("modalidade_ids")),
                "recursos_operados": self.labels(row.get("recurso_operado_ids")),
                "objetivo": row.get("objetivo_participacao", ""),
                "origem_registro": row.get("status_evidencia", ""),
                "estatuto": row.get("status_evidencia", ""),
            }
            for row in rows
        ]

    def resource_state(self, context, identifier):
        if identifier in set(context.get("recursos_impedidos", [])):
            return "IMPEDIDO"
        if identifier in set(context.get("recursos_disponiveis", [])):
            return "DISPONIVEL_CONFIRMADO"
        if identifier in set(context.get("recursos_propostos", [])):
            return "PROPOSTO_A_PREPARAR"
        return "NAO_CONFIRMADO"

    def resource_state_payload(self, context):
        identifiers = unique(
            context.get("recursos_disponiveis", [])
            + context.get("recursos_impedidos", [])
            + context.get("recursos_propostos", [])
        )
        return [
            {
                "id": identifier,
                "label": self.label(identifier),
                "estado": self.resource_state(context, identifier),
            }
            for identifier in identifiers
        ]

    def context_payload(self, context=None):
        c = context or self.current["context"]
        if context is None or c.get("id") == self.current.get("context", {}).get("id"):
            participation_rows = self.current.get("participations", [])
        else:
            participation_rows = [
                row for row in self.participations if row.get("contexto_id") == c["id"]
            ]
        characteristic_rows = [
            {
                "id": identifier,
                "label": self.label(identifier),
                "categoria": self.concepts.get(identifier, {}).get(
                    "categoria_caracteristica", ""
                ),
                "status": self.concepts.get(identifier, {}).get("status", ""),
            }
            for identifier in c.get("caracteristicas_pessoa", [])
        ]
        return {
            "id": c["id"],
            "natureza": c.get("natureza", ""),
            "status": c.get("status", ""),
            "texto_curto": c.get("descricao_do_contexto", ""),
            "objetivo": c.get("objetivo", ""),
            "titulo_curto": c.get("titulo_curto", ""),
            "premissas_do_exemplo": c.get("premissas_do_exemplo", []),
            "operacao_do_recurso": c.get("operacao_do_recurso", ""),
            "impedimentos_verificados": bool(c.get("impedimentos_verificados", False)),
            "tarefas": self.labels(c.get("tarefas")),
            "caracteristicas_relevantes": self.labels(c.get("caracteristicas_pessoa")),
            "caracteristicas_estruturadas": characteristic_rows,
            "participantes": self.participation_payload(participation_rows),
            "recursos_digitais": self.labels(c.get("recursos_digitais")),
            "barreiras": self.labels(c.get("barreiras")),
            "necessidades": self.labels(c.get("necessidades")),
            "ambientes": self.labels(c.get("ambientes")),
            "modalidades_disponiveis": self.labels(c.get("modalidades_disponiveis")),
            "recursos_disponiveis": self.labels(c.get("recursos_disponiveis")),
            "recursos_impedidos": self.labels(c.get("recursos_impedidos")),
            "recursos_propostos": self.labels(c.get("recursos_propostos")),
            "estado_dos_recursos": self.resource_state_payload(c),
            "funcoes_requeridas": self.labels(c.get("funcoes_requeridas_ids")),
            "restricoes": c.get("restricoes", []),
            "informacoes_ausentes": c.get("informacoes_ausentes", []),
            "baseado_em": c.get("baseado_em_contexto_ids", []),
            "raw": {
                field: copy.deepcopy(c.get(field, [])) for field in self.context_fields
            },
        }

    def catalog_payload(self):
        grouped = {}
        for row in self.concepts.values():
            public = self.ui_vocab.get("concepts", {}).get(row["id"], {})
            grouped.setdefault(row["tipo"], []).append(
                {
                    "id": row["id"],
                    "label": public.get("label") or row["rotulo"],
                    "technical_label": row["rotulo"],
                    "description": public.get("description", ""),
                    "aliases": public.get("aliases", []),
                    "status": row["status"],
                    "categoria": row.get("categoria_caracteristica", ""),
                    "category_label": public.get("category_label")
                    or row.get("categoria_caracteristica", "")
                    or "Outros",
                    "scope": public.get("scope", "GERAL"),
                    "order": int(public.get("order", 500)),
                    "group": self.ui_vocab.get("groups", {}).get(
                        row["tipo"], row["tipo"].replace("_", " ").title()
                    ),
                    "curated": bool(public.get("show_in_interface", bool(public))),
                }
            )
        for values in grouped.values():
            values.sort(key=lambda row: row["label"].casefold())
        template_ids = [
            "CTX-TRANSFERENCIA-RECURSO-DIGITAL-01",
            "CTX-DEMO-MOB-RUIDO",
            "CTX-DEMO-WEB-LEITOR-TELA",
            "CTX-DEMO-COMUNICACAO-MULTIFORMATO",
        ]
        return {
            "reported": self.context_payload(self.contexts["CTX-RELATADO-01"]),
            "reconstructed": self.context_payload(
                self.contexts["CTX-TRANSFERENCIA-RECURSO-DIGITAL-01"]
            ),
            "transfer": self.context_payload(
                self.contexts["CTX-TRANSFERENCIA-RECURSO-DIGITAL-01"]
            ),
            "elicitation_synthesis": self.data.get("elicitation_synthesis", {}),
            "templates": [
                self.context_payload(self.contexts[identifier])
                for identifier in template_ids
            ],
            "concepts": grouped,
            "groups": self.ui_vocab.get("groups", {}),
            "boundary": "A MADO descreve condições funcionais situadas; não possui classe de deficiência, não prescreve por diagnóstico e só mobiliza articulações com origem e confirmação registradas.",
        }

    def start_context(self, template_id):
        if template_id not in self.contexts:
            raise ValueError("Cenário não localizado na base.")
        self._evidence = None
        self._record_checks = False
        context = copy.deepcopy(self.contexts[template_id])
        context["id"] = f"CTX-CASO-{uuid.uuid4().hex[:10].upper()}"
        context["template_id"] = template_id
        session_participations = []
        for index, row in enumerate(
            (
                item
                for item in self.participations
                if item.get("contexto_id") == template_id
            ),
            1,
        ):
            copied = copy.deepcopy(row)
            copied["id"] = f"PART-CASO-{index:02d}-{uuid.uuid4().hex[:6].upper()}"
            copied["contexto_id"] = context["id"]
            session_participations.append(copied)
        self.current = {
            "context": context,
            "reported_confirmed": False,
            "transfer_confirmed": False,
            "mapping_confirmed": False,
            "created_at": now_iso(),
            "last_result": None,
            "participations": session_participations,
            "scenario_mode": "known_case",
            "narrative_interpretation": None,
        }
        return self.current_payload()

    def _invalidate_result(self):
        self._evidence = None
        self._record_checks = False
        self.current["last_result"] = None

    def clear(self):
        """Discard the current case, not a history entry; no filesystem writes."""
        return self.start_free_context()

    def current_payload(self):
        last_result = copy.deepcopy(self.current.get("last_result"))
        if last_result is not None:
            last_result.pop("query_results", None)
        return {
            "context": self.context_payload(),
            "reported_confirmed": self.current["reported_confirmed"],
            "reported_correction": self.current.get("reported_correction", ""),
            "transfer_confirmed": self.current["transfer_confirmed"],
            "mapping_confirmed": self.current["mapping_confirmed"],
            "questions": self.missing_questions(),
            "scenario_mode": self.current.get("scenario_mode", "known_case"),
            "narrative_interpretation": self.current.get("narrative_interpretation"),
            "last_result": last_result,
        }

    def confirm_reported(self, confirmed, correction=""):
        self.current["reported_confirmed"] = bool(confirmed)
        self.current["reported_correction"] = correction.strip()
        self._invalidate_result()
        return self.current_payload()

    def start_free_context(self):
        self.start_context("CTX-TESTE-RC2-DIAGNOSTICO-ISOLADO")
        self.current["scenario_mode"] = "free_narrative"
        context = self.current["context"]
        context.update(
            {
                "descricao_do_contexto": "",
                "perspectiva_ids": ["P-USUARIO-TEMPORARIO"],
                "objetivo": "",
                "tarefas": [],
                "caracteristicas_pessoa": [],
                "recursos_digitais": [],
                "barreiras": [],
                "necessidades": [],
                "ambientes": [],
                "modalidades_disponiveis": [],
                "recursos_disponiveis": [],
                "recursos_impedidos": [],
                "restricoes": [],
                "informacoes_ausentes": [],
                "recursos_propostos": [],
                "operacao_do_recurso": "",
                "impedimentos_verificados": False,
                "premissas_do_exemplo": [],
                "titulo_curto": "Caso informado agora",
                "funcoes_requeridas_ids": [],
            }
        )
        self.current["participations"] = []
        return self.current_payload()

    def analyze_narrative(self, narrative, input_modality="text"):
        narrative = str(narrative or "").strip()
        if len(narrative) > 20000:
            raise ValueError("Use até 20.000 caracteres para descrever este caso.")
        if len(narrative) < 20:
            raise ValueError(
                "Descreva o caso em uma ou mais frases antes de organizar as informações."
            )
        if self.current.get("scenario_mode") != "free_narrative":
            self.start_free_context()
        self._invalidate_result()
        self.current["mapping_confirmed"] = False
        self.current["transfer_confirmed"] = False
        normalized = normalize_text(narrative)
        context = self.current["context"]
        context["restricoes"] = []
        context["operacao_do_recurso"] = ""
        context["impedimentos_verificados"] = False
        context["premissas_do_exemplo"] = []
        detected = {field: [] for field in self.context_fields}
        evidence = []
        field_for_type = {
            "TAREFA": "tarefas",
            "CARACTERISTICA_PESSOA": "caracteristicas_pessoa",
            "RECURSO_DIGITAL": "recursos_digitais",
            "BARREIRA": "barreiras",
            "NECESSIDADE": "necessidades",
            "AMBIENTE": "ambientes",
            "MODALIDADE": "modalidades_disponiveis",
            "RECURSO_DISPONIVEL": "recursos_disponiveis",
        }
        for identifier, concept in self.concepts.items():
            field = field_for_type.get(concept.get("tipo"))
            if not field:
                continue
            public = self.ui_vocab.get("concepts", {}).get(identifier, {})
            aliases = unique(
                public.get("aliases", [])
                + [public.get("label", ""), concept.get("rotulo", "")]
            )
            for alias in aliases:
                token = normalize_text(alias)
                if len(token) >= 4 and token in normalized:
                    detected[field].append(identifier)
                    evidence.append(
                        {
                            "field": field,
                            "concept_id": identifier,
                            "label": self.label(identifier),
                            "matched_text": alias,
                            "status": "IDENTIFICADO_PARA_CONFIRMACAO",
                        }
                    )
                    break
        cues = [
            (
                "\\b(pessoa cega|usuario cego|usuaria cega).{0,50}\\b(usa|utiliza).{0,20}\\b(leitor de tela|talkback|voiceover)\\b",
                "caracteristicas_pessoa",
                "CAR-PESSOA-CEGA-LEITOR-TELA",
            ),
            (
                "\\b(setimo ano|7 ano|fundamental ii)\\b",
                "caracteristicas_pessoa",
                "CAR-SETIMO-ANO",
            ),
            (
                "\\b(interesse intenso|interesse profundo|conhecimento aprofundado|domina um tema|hiperfoco)\\b",
                "caracteristicas_pessoa",
                "CAR-INTERESSE-CONHECIMENTO-TEMA",
            ),
            (
                "\\b(explica|narra|fala|oralmente).{0,35}\\b(conhecimento|conteudo|tema|ideia)\\b",
                "caracteristicas_pessoa",
                "CAR-EXPRESSAO-ORAL-AUTORAL",
            ),
            (
                "\\b(desenho|imagem|mapa).{0,35}\\b(explica|organiza|representa|mostra)\\b",
                "caracteristicas_pessoa",
                "CAR-EXPRESSAO-VISUAL-AUTORAL",
            ),
            (
                "\\b(criar|produzir|construir|preparar).{0,40}\\b(recurso|conteudo|apresentacao|pagina|video|jogo)\\b",
                "tarefas",
                "TAR-PRODUZIR-CONTEUDO-MULTIMODAL",
            ),
            (
                "\\b(organizar|estruturar).{0,30}\\b(conteudo|ideias|informacao)\\b",
                "tarefas",
                "TAR-ORGANIZAR-CONTEUDO-DIGITAL",
            ),
            (
                "\\b(revisar|confirmar|retomar|corrigir)\\b",
                "tarefas",
                "TAR-REVISAR-E-CONFIRMAR",
            ),
            (
                "\\b(navegar|orientar|rota|destino)\\b",
                "tarefas",
                "TAR-NAVEGAR-E-ORIENTAR-SE",
            ),
            (
                "\\b(operar|controlar|acionar|preencher|enviar)\\b",
                "tarefas",
                "TAR-OPERAR-SISTEMA",
            ),
            (
                "\\b(conteudo educacional|pagina|site|web)\\b",
                "tarefas",
                "TAR-ACESSAR-COMPREENDER-CONTEUDO-DIGITAL",
            ),
            (
                "\\b(imagem|imagens|visual|grafico).{0,35}\\b(sem descricao|nao tem descricao|nao possuem descricao)\\b",
                "barreiras",
                "BAR-ELEMENTOS-SEM-REPRESENTACAO-ADEQUADA-F915D33",
            ),
            (
                "\\b(imagem|imagens|visual|grafico).{0,35}\\b(sem descricao|nao tem descricao|nao possuem descricao)\\b",
                "necessidades",
                "NEC-ACESSO-EQUIVALENTE",
            ),
            (
                "\\b(compreender|entender).{0,30}\\b(conteudo|material|imagem|imagens|pagina|site)\\b",
                "necessidades",
                "NEC-ACESSO-EQUIVALENTE",
            ),
            (
                "\\b(navegar|operar|usar).{0,25}\\b(teclado)\\b",
                "necessidades",
                "NEC-ENTRADA-ALTERNATIVA",
            ),
            (
                "\\b(fala longa|fala extensa|contribuicoes orais|fala espontanea)\\b",
                "barreiras",
                "BAR-CONTRIBUICAO-EXTENSA-SEM-SEQUENCIA",
            ),
            (
                "\\b(protagonismo|valorizar conhecimento|preservar participacao)\\b",
                "necessidades",
                "NEC-PRESERVAR-PROTAGONISMO",
            ),
            (
                "\\b(turma|colegas|sala de aula)\\b",
                "necessidades",
                "NEC-APOIAR-COMPREENSAO-TURMA",
            ),
            (
                "\\b(sala de aula|turma|professora|professor)\\b",
                "ambientes",
                "AMB-SALA-DE-AULA",
            ),
            (
                "\\b(projetor|data show|datashow)\\b",
                "recursos_disponiveis",
                "REC-COMPUTADOR-DATASHOW",
            ),
            (
                "\\b(palavras chave|linha do tempo)\\b",
                "recursos_disponiveis",
                "REC-PALAVRAS-CHAVE-LINHA-DO-TEMPO",
            ),
            ("\\b(apresentacao|slides?)\\b", "recursos_digitais", "RED-APRESENTACAO"),
            (
                "\\b(ambiente virtual|ava|sigaa|moodle|google classroom)\\b",
                "recursos_digitais",
                "RED-AVA",
            ),
            ("\\b(formulario)\\b", "recursos_digitais", "RED-FORMULARIO"),
            (
                "\\b(mensagens?|chat|comunicacao digital)\\b",
                "recursos_digitais",
                "RED-MENSAGENS",
            ),
            (
                "\\b(aplicativo de orientacao|aplicativo de navegacao)\\b",
                "recursos_digitais",
                "RED-APLICATIVO-ORIENTACAO",
            ),
            ("\\b(video)\\b", "recursos_digitais", "RED-VIDEO"),
            ("\\b(jogo|quiz|atividade interativa)\\b", "recursos_digitais", "RED-JOGO"),
            ("\\b(celular|smartphone)\\b", "recursos_disponiveis", "REC-SMARTPHONE"),
            ("\\b(computador|notebook)\\b", "recursos_disponiveis", "REC-COMPUTADOR"),
            (
                "\\b(leitor de tela|talkback|voiceover)\\b",
                "recursos_disponiveis",
                "REC-LEITOR-DE-TELA",
            ),
            ("\\b(legenda|legendas)\\b", "recursos_disponiveis", "REC-LEGENDAS"),
            ("\\b(audiodescricao)\\b", "recursos_disponiveis", "REC-AUDIODESCRICAO"),
            ("\\b(audio|orientacao falada)\\b", "modalidades_disponiveis", "MOD-AUDIO"),
            (
                "\\b(vibracao|retorno tatil|haptico)\\b",
                "modalidades_disponiveis",
                "MOD-HAPTICO",
            ),
        ]
        for pattern, field, identifier in cues:
            match = re.search(pattern, normalized)
            if (
                match
                and identifier in self.concepts
                and (identifier not in detected[field])
            ):
                detected[field].append(identifier)
                evidence.append(
                    {
                        "field": field,
                        "concept_id": identifier,
                        "label": self.label(identifier),
                        "matched_text": match.group(0),
                        "status": "INFERIDO_POR_REGRA_LOCAL_PARA_CONFIRMACAO",
                    }
                )
        blocked_cues = [
            (
                "\\b(sem|nao (?:ha|tem|pode usar|esta disponivel)).{0,24}\\b(video|reprodutor de video)\\b",
                "REC-REPRODUTOR-VIDEO",
            ),
            (
                "\\b(sem|nao (?:ha|tem|pode usar|esta disponivel)).{0,24}\\b(jogo|quiz|plataforma de jogo)\\b",
                "REC-PLATAFORMA-JOGO-QUIZ",
            ),
            (
                "\\b(sem|nao (?:ha|tem|pode usar|esta disponivel)).{0,24}\\b(internet|conexao)\\b",
                "REC-CONEXAO-INTERNET",
            ),
        ]
        for pattern, identifier in blocked_cues:
            match = re.search(pattern, normalized)
            if match and identifier in self.concepts:
                detected["recursos_disponiveis"] = [
                    value
                    for value in detected["recursos_disponiveis"]
                    if value != identifier
                ]
                detected["recursos_impedidos"].append(identifier)
                evidence.append(
                    {
                        "field": "recursos_impedidos",
                        "concept_id": identifier,
                        "label": self.label(identifier),
                        "matched_text": match.group(0),
                        "status": "IMPEDIMENTO_IDENTIFICADO_PARA_CONFIRMACAO",
                    }
                )
        output_cues = (
            (
                "\\b(sem descricao|nao (?:ha|tem) descricao|precisa (?:de|criar) descricao|descricao a preparar)\\b",
                "REC-DESCRICAO-TEXTUAL",
            ),
            (
                "\\b(feedback a preparar|precisa (?:de|criar) feedback|sem feedback)\\b",
                "REC-FEEDBACK-EXPLICATIVO",
            ),
        )
        for pattern, identifier in output_cues:
            match = re.search(pattern, normalized)
            if (
                match
                and identifier in self.concepts
                and (identifier not in detected["recursos_impedidos"])
            ):
                detected["recursos_disponiveis"] = [
                    value
                    for value in detected["recursos_disponiveis"]
                    if value != identifier
                ]
                detected["recursos_propostos"].append(identifier)
                evidence.append(
                    {
                        "field": "recursos_propostos",
                        "concept_id": identifier,
                        "label": self.label(identifier),
                        "matched_text": match.group(0),
                        "status": "PROPOSTO_PARA_CONFIRMACAO",
                    }
                )
        if not re.search("\\b(leitor de tela|talkback|voiceover)\\b", normalized):
            detected["caracteristicas_pessoa"] = [
                value
                for value in detected["caracteristicas_pessoa"]
                if value != "CAR-PESSOA-CEGA-LEITOR-TELA"
            ]
        for field, identifiers in detected.items():
            context[field] = unique(identifiers)
        context["descricao_do_contexto"] = narrative
        sentences = [
            item.strip()
            for item in re.split("(?<=[.!?])\\s+", narrative)
            if item.strip()
        ]
        objective_sentence = next(
            (
                sentence
                for sentence in sentences
                if re.search(
                    "\\b(objetiv|precisa|deve|espera|quer|para que)\\w*\\b",
                    normalize_text(sentence),
                )
            ),
            "",
        )
        context["objetivo"] = objective_sentence
        roles = []
        role_cues = [
            ("PAPEL-ESTUDANTE", "\\b(estudante|aluno|aluna)\\b"),
            ("PAPEL-PROFESSORA", "\\b(professora|professor|docente)\\b"),
            ("PAPEL-TURMA", "\\b(turma|colegas)\\b"),
            ("PAPEL-PESSOA-APOIADA", "\\b(pessoa|usuario|usuaria)\\b"),
            (
                "PAPEL-RESPONSAVEL-ADAPTACAO",
                "\\b(responsavel pela adaptacao|responsavel por adaptar|pessoa responsavel por adaptar)\\b",
            ),
        ]
        for role_id, pattern in role_cues:
            if re.search(pattern, normalized):
                roles.append(
                    {
                        "id": f"PART-CASO-{len(roles) + 1:02d}-{uuid.uuid4().hex[:6].upper()}",
                        "contexto_id": context["id"],
                        "papel_id": role_id,
                        "caracteristica_ids": (
                            copy.deepcopy(context["caracteristicas_pessoa"])
                            if role_id in {"PAPEL-ESTUDANTE", "PAPEL-PESSOA-APOIADA"}
                            else []
                        ),
                        "tarefa_ids": (
                            copy.deepcopy(context["tarefas"])
                            if role_id in {"PAPEL-ESTUDANTE", "PAPEL-PESSOA-APOIADA"}
                            else []
                        ),
                        "modalidade_ids": (
                            copy.deepcopy(context["modalidades_disponiveis"])
                            if role_id in {"PAPEL-ESTUDANTE", "PAPEL-PESSOA-APOIADA"}
                            else []
                        ),
                        "recurso_operado_ids": [],
                        "objetivo_participacao": "",
                        "status_evidencia": "IDENTIFICADO_PARA_CONFIRMACAO",
                    }
                )
        self.current["participations"] = roles
        context["informacoes_ausentes"] = [
            item["question"] for item in self.missing_questions()
        ]
        interpretation = {
            "narrative": narrative,
            "fields": {
                "pessoa_e_participacao": self.participation_payload(roles),
                "objetivo": context["objetivo"],
                "atividade": self.labels(context["tarefas"]),
                "dificuldade": self.labels(context["barreiras"]),
                "necessidade": self.labels(context["necessidades"]),
                "ambiente": self.labels(context["ambientes"]),
                "formas_de_interacao": self.labels(context["modalidades_disponiveis"]),
                "recursos_digitais": self.labels(context["recursos_digitais"]),
                "recursos_disponiveis": self.labels(context["recursos_disponiveis"]),
                "recursos_impedidos": self.labels(context["recursos_impedidos"]),
            },
            "evidence": evidence,
            "missing_questions": context["informacoes_ausentes"],
            "status": "AGUARDANDO_CONFIRMACAO_HUMANA",
            "note": "A organização é determinística e local. Ela não diagnostica a pessoa; todos os elementos precisam ser confirmados antes da consulta.",
        }
        self.current["narrative_interpretation"] = interpretation
        return {"current": self.current_payload(), "interpretation": interpretation}

    def update_context(self, body):
        if not isinstance(body, dict):
            raise ValueError("O contexto deve ser um objeto estruturado.")
        for field in self.context_fields:
            if field in body and (
                not isinstance(body[field], list)
                or not all(isinstance(v, str) for v in body[field])
            ):
                raise ValueError(
                    "Cada condição deve ser uma lista de conceitos reconhecidos: "
                    + field
                )
        for field in ("mapping_confirmed", "transfer_confirmed"):
            if field in body and not isinstance(body[field], bool):
                raise ValueError("A confirmação deve ser explícita: " + field)
        previous_context = self.current["context"]
        previous_participations = self.current.get("participations", [])
        context = copy.deepcopy(previous_context)
        participations = copy.deepcopy(previous_participations)
        for scalar in ("objetivo", "descricao_do_contexto", "operacao_do_recurso"):
            if scalar in body:
                context[scalar] = str(body.get(scalar, "")).strip()
        for field in self.context_fields:
            if field not in body:
                continue
            identifiers = unique(body.get(field) or [])
            invalid = [
                identifier
                for identifier in identifiers
                if identifier not in self.concepts
            ]
            if invalid:
                raise ValueError(f"Conceitos não reconhecidos: {', '.join(invalid)}")
            context[field] = identifiers
        resource_fields = (
            "recursos_disponiveis",
            "recursos_impedidos",
            "recursos_propostos",
        )
        for index, left in enumerate(resource_fields):
            for right in resource_fields[index + 1 :]:
                overlap = set(context.get(left, [])) & set(context.get(right, []))
                if overlap:
                    raise ValueError(
                        "Um recurso não pode estar em dois estados (disponível, impedido ou proposto): "
                        + ", ".join(self.labels(sorted(overlap)))
                    )
        if "impedimentos_verificados" in body:
            if not isinstance(body["impedimentos_verificados"], bool):
                raise ValueError(
                    "Informe explicitamente se os impedimentos foram conferidos."
                )
            context["impedimentos_verificados"] = body["impedimentos_verificados"]
        if "restricoes" in body:
            context["restricoes"] = unique(
                (
                    str(value).strip()
                    for value in body.get("restricoes", [])
                    if str(value).strip()
                )
            )
        if "participations" in body:
            rows = []
            for index, incoming in enumerate(body.get("participations") or [], 1):
                role_id = incoming.get("papel_id")
                if role_id not in self.concepts:
                    raise ValueError(f"Papel não reconhecido: {role_id}")
                rows.append(
                    {
                        "id": incoming.get("id")
                        or f"PART-CASO-{index:02d}-{uuid.uuid4().hex[:6].upper()}",
                        "contexto_id": context["id"],
                        "papel_id": role_id,
                        "caracteristica_ids": unique(
                            incoming.get("caracteristica_ids") or []
                        ),
                        "tarefa_ids": unique(incoming.get("tarefa_ids") or []),
                        "modalidade_ids": unique(incoming.get("modalidade_ids") or []),
                        "recurso_operado_ids": unique(
                            incoming.get("recurso_operado_ids") or []
                        ),
                        "objetivo_participacao": str(
                            incoming.get("objetivo_participacao", "")
                        ).strip(),
                        "status_evidencia": (
                            "CONFIRMADO_NA_SESSAO"
                            if body.get("mapping_confirmed") is True
                            else "IDENTIFICADO_PARA_CONFIRMACAO"
                        ),
                    }
                )
            participations = rows
        elif "caracteristicas_pessoa" in body:
            for row in participations:
                if row.get("papel_id") in {"PAPEL-ESTUDANTE", "PAPEL-PESSOA-APOIADA"}:
                    row["caracteristica_ids"] = copy.deepcopy(
                        context.get("caracteristicas_pessoa", [])
                    )
                    row["status_evidencia"] = "IDENTIFICADO_PARA_CONFIRMACAO"
                    break
        for row in participations:
            for participant_field, context_field in (
                ("tarefa_ids", "tarefas"),
                ("modalidade_ids", "modalidades_disponiveis"),
                ("recurso_operado_ids", "recursos_disponiveis"),
            ):
                if (
                    context_field in body
                    or "participations" in body
                    or (
                        participant_field == "recurso_operado_ids"
                        and any((f in body for f in resource_fields))
                    )
                ):
                    before = row.get(participant_field, [])
                    row[participant_field] = [
                        identifier
                        for identifier in before
                        if identifier in context.get(context_field, [])
                    ]
                    if before != row[participant_field]:
                        row["status_evidencia"] = "IDENTIFICADO_PARA_CONFIRMACAO"
        mapping_confirmed = bool(body.get("mapping_confirmed", False))
        transfer_confirmed = bool(body.get("transfer_confirmed", False))
        changed = (
            context != previous_context or participations != previous_participations
        )
        confirmation_revoked = (
            self.current["mapping_confirmed"]
            and (not mapping_confirmed)
            or (self.current["transfer_confirmed"] and (not transfer_confirmed))
        )
        self.current["context"] = context
        self.current["participations"] = participations
        self.current["mapping_confirmed"] = mapping_confirmed
        self.current["transfer_confirmed"] = transfer_confirmed
        if changed or confirmation_revoked:
            self._invalidate_result()
        context["informacoes_ausentes"] = [
            item["question"] for item in self.missing_questions()
        ]
        return self.current_payload()

    def missing_questions(self):
        c, questions = (self.current["context"], [])
        if not str(c.get("objetivo") or "").strip():
            questions.append(
                {
                    "field": "objetivo",
                    "question": "O que você espera alcançar com esta atividade?",
                }
            )
        if not c.get("tarefas"):
            questions.append(
                {
                    "field": "tarefas",
                    "question": "Qual atividade a pessoa precisa realizar?",
                }
            )
        if not c.get("barreiras") and (not c.get("necessidades")):
            questions.append(
                {
                    "field": "barreira_ou_necessidade",
                    "question": "O que está dificultando a atividade ou precisa ser apoiado?",
                }
            )
        functional_characteristics = [
            identifier
            for identifier in c.get("caracteristicas_pessoa", [])
            if self.concepts.get(identifier, {}).get("categoria_caracteristica")
            != "ESCOPO_DE_PUBLICO"
        ]
        if not functional_characteristics:
            questions.append(
                {
                    "field": "caracteristicas_pessoa",
                    "question": "Quais características, capacidades, dificuldades ou formas de expressão são relevantes nesta atividade?",
                }
            )
        if not self.current.get("participations"):
            questions.append(
                {
                    "field": "participantes",
                    "question": "Quem participa da atividade e quem utiliza ou controla cada recurso?",
                }
            )
        if not c.get("modalidades_disponiveis"):
            questions.append(
                {
                    "field": "modalidades_disponiveis",
                    "question": "Quais formas de interação estão realmente disponíveis?",
                }
            )
        if c.get("tarefas"):
            for field, question in (
                (
                    "recursos_digitais",
                    "Qual aplicativo, página, conteúdo ou outro recurso digital está envolvido?",
                ),
                ("ambientes", "Em que ambiente ocorre a interação?"),
                (
                    "recursos_disponiveis",
                    "Quais equipamentos ou recursos estão disponíveis para realizar a atividade?",
                ),
            ):
                if not c.get(field):
                    questions.append({"field": field, "question": question})
        return questions

    @staticmethod
    def intersects(context, field, identifiers):
        return bool(set(context.get(field, [])) & set(identifiers or []))

    def build_context_graph(self):
        graph = Graph()
        graph.bind("mado", MADO)
        context, ctx = (self.current["context"], MADO[self.current["context"]["id"]])
        graph.add((ctx, RDF.type, MADO.ContextoDeInteracaoDigital))
        graph.add((ctx, MADO.identificador, Literal(context["id"])))
        graph.add(
            (
                ctx,
                MADO.descricaoDoContexto,
                Literal(context.get("descricao_do_contexto", ""), lang="pt-BR"),
            )
        )
        if context.get("objetivo"):
            graph.add((ctx, MADO.objetivo, Literal(context["objetivo"], lang="pt-BR")))
        graph.add(
            (
                ctx,
                MADO.statusConfirmacao,
                Literal(
                    "CONFIRMADO_PARA_CONSULTA"
                    if self.current.get("mapping_confirmed")
                    else "AGUARDANDO_CONFIRMACAO"
                ),
            )
        )
        predicate_map = {
            "tarefas": MADO.temTarefa,
            "caracteristicas_pessoa": MADO.consideraCaracteristicaRelevanteDaPessoa,
            "recursos_digitais": MADO.envolveRecursoDigital,
            "barreiras": MADO.apresentaBarreira,
            "necessidades": MADO.apresentaNecessidade,
            "ambientes": MADO.ocorreEmAmbiente,
            "modalidades_disponiveis": MADO.temModalidadeDisponivel,
            "recursos_disponiveis": MADO.temRecursoDisponivel,
            "recursos_impedidos": MADO.temRecursoImpedido,
            "recursos_propostos": MADO.temRecursoProposto,
            "funcoes_requeridas_ids": MADO.requerFuncaoDecisoria,
            "perspectiva_ids": MADO.descritoSobPerspectiva,
        }
        for field, predicate in predicate_map.items():
            for identifier in context.get(field, []):
                graph.add((ctx, predicate, MADO[identifier]))
        if "P-USUARIO-TEMPORARIO" in context.get("perspectiva_ids", []):
            # Describes authorship of this input, not an expert review or diagnosis.
            graph.add((MADO["P-USUARIO-TEMPORARIO"], RDF.type, MADO.Perspectiva))
            graph.add((MADO["P-USUARIO-TEMPORARIO"], MADO.enunciado,
                       Literal("Perspectiva de quem descreve o contexto nesta execução temporária.", lang="pt-BR")))
        for value in context.get("restricoes", []):
            graph.add((ctx, MADO.restricao, Literal(value, lang="pt-BR")))
        if context.get("operacao_do_recurso"):
            graph.add(
                (
                    ctx,
                    MADO.operacaoDoRecurso,
                    Literal(context["operacao_do_recurso"], lang="pt-BR"),
                )
            )
        graph.add(
            (
                ctx,
                MADO.impedimentosVerificados,
                Literal(bool(context.get("impedimentos_verificados", False))),
            )
        )
        for value in context.get("premissas_do_exemplo", []):
            graph.add((ctx, MADO.premissaDoExemplo, Literal(value, lang="pt-BR")))
        for row in self.current.get("participations", []):
            participation = MADO[row["id"]]
            graph.add((participation, RDF.type, MADO.ParticipacaoNoContexto))
            graph.add((participation, MADO.identificador, Literal(row["id"])))
            graph.add((participation, MADO.participacaoEmContexto, ctx))
            graph.add((ctx, MADO.temParticipacao, participation))
            graph.add((participation, MADO.temPapelNoContexto, MADO[row["papel_id"]]))
            graph.add(
                (
                    participation,
                    MADO.origemDoRegistro,
                    Literal(row.get("status_evidencia", "SESSAO")),
                )
            )
            if row.get("objetivo_participacao"):
                graph.add(
                    (
                        participation,
                        MADO.objetivoDaParticipacao,
                        Literal(row["objetivo_participacao"], lang="pt-BR"),
                    )
                )
            for identifier in row.get("caracteristica_ids", []):
                graph.add(
                    (participation, MADO.temCaracteristicaRelevante, MADO[identifier])
                )
            for identifier in row.get("tarefa_ids", []):
                graph.add((participation, MADO.realizaTarefa, MADO[identifier]))
            for identifier in row.get("modalidade_ids", []):
                graph.add(
                    (
                        participation,
                        MADO.participanteUtilizaModalidade,
                        MADO[identifier],
                    )
                )
            for identifier in row.get("recurso_operado_ids", []):
                graph.add((participation, MADO.operaRecurso, MADO[identifier]))
        for missing in context.get("informacoes_ausentes", []):
            graph.add((ctx, MADO.informacaoAusente, Literal(missing, lang="pt-BR")))
        return graph

    def retrieve_transfer_candidates(self, context_graph):
        """Recupera conhecimento direto e o que somente se torna utilizável por articulação confirmada."""
        combined = self.graph + context_graph
        context_id = self.current["context"]["id"]
        query = self.queries["CQ-002"].replace(
            "CTX-TRANSFERENCIA-RECURSO-DIGITAL-01", context_id
        )
        candidate_rows = list(combined.query(query))
        rows, excluded, conditional = [], [], []
        context = self.current["context"]
        self.knowledge_authorization = {}
        for row in candidate_rows:
            kid = local_id(row[0])
            if kid not in self.knowledge:
                continue
            state, reasons = self.authorize_knowledge(kid, context)
            aid = local_id(row[3]) if row[3] else ""
            if aid and not self.articulation_authorized(aid):
                state, reasons = "EXCLUIDO", reasons + [
                    "Articulação sem confirmação e curadoria habilitadas."
                ]
            self.knowledge_authorization[kid] = state
            witness = {
                "knowledge_id": kid, "mode": str(row[2]), "articulation_id": aid,
                "input_knowledge_id": local_id(row[8]),
                "context_task_id": local_id(row[9]), "knowledge_task_id": local_id(row[10]),
                "context_concept_id": local_id(row[11]) if row[11] else "",
                "match_predicate": local_id(row[12]),
                "required_function_id": local_id(row[6]) if row[6] else "",
                "task_path": self._task_path(local_id(row[9]), local_id(row[10])),
                "authorization": state,
            }
            witness["id"] = "WIT-" + hashlib.sha256(json.dumps(witness, sort_keys=True).encode()).hexdigest()[:16]
            check_id = self._check(
                "retrieval", kid, "cq2_concrete_witness", "PASS",
                "Correspondência retornada pela consulta; a autorização é verificada separadamente.",
                operator="TASK_PATH_AND_FUNCTIONAL_MATCH", witness_id=witness["id"],
            )
            witness["check_ids"] = [check_id] if check_id else []
            if self._evidence is not None and self._record_checks:
                witness["check_ids"] += self._evidence.checks_for(kid, "knowledge")
                if aid:
                    witness["check_ids"] += self._evidence.checks_for(aid, "articulation")
                self._evidence.data["retrieval"].append(witness)
            audit = {
                "knowledge_id": kid,
                "articulation_id": aid,
                "state": state,
                "reasons": reasons,
            }
            if state == "EXCLUIDO":
                excluded.append(audit)
                continue
            if state == "CONDICIONAL":
                conditional.append(audit)
            rows.append(row)
        direct_ids = unique(
            (
                local_id(row[0])
                for row in rows
                if str(row[2]) == "DIRETA" and local_id(row[0]) in self.knowledge
            )
        )
        articulated_ids = unique(
            (
                local_id(row[0])
                for row in rows
                if str(row[2]) == "POR_ARTICULACAO"
                and local_id(row[0]) in self.knowledge
            )
        )
        articulation_ids = unique(
            (
                local_id(row[3])
                for row in rows
                if row[3] is not None and local_id(row[3]) in self.articulations
            )
        )
        all_knowledge = unique(direct_ids + articulated_ids)
        criterion_ids, direct_criteria = ([], [])
        for component in self.components:
            for support in component.get("criterion_support", []):
                criterion_id = support.get("criterion_id")
                support_knowledge = set(support.get("knowledge_ids", []))
                origins = [
                    oid
                    for oid in support.get("origin_ids", [])
                    if oid in self.criterion_origins
                ]
                if (
                    criterion_id in self.criteria
                    and origins
                    and support_knowledge & set(all_knowledge)
                ):
                    criterion_ids.append(criterion_id)
                if (
                    criterion_id in self.criteria
                    and origins
                    and support_knowledge & set(direct_ids)
                ):
                    direct_criteria.append(criterion_id)
        criterion_ids = unique(criterion_ids)
        direct_criteria = unique(direct_criteria)
        retrieval_by_key = {}
        for row in rows:
            knowledge_id = local_id(row[0])
            if knowledge_id not in self.knowledge:
                continue
            key = tuple(str(row[i] or "") for i in (0, 2, 3, 4, 5, 6))
            value = retrieval_by_key.setdefault(key,
                {
                    "knowledge_id": knowledge_id,
                    "mode": str(row[2]),
                    "articulation_id": local_id(row[3]) if row[3] else "",
                    "articulation_type": str(row[4]) if row[4] else "",
                    "confirmation_level": str(row[5]) if row[5] else "",
                    "added_function_id": local_id(row[6]) if row[6] else "",
                    "correspondences": [],
                }
            )
            if row[7] and str(row[7]) not in value["correspondences"]:
                value["correspondences"].append(str(row[7]))
        retrieval = [{**value, "correspondences": " | ".join(value["correspondences"])} for value in retrieval_by_key.values()]
        return {
            "direct_knowledge_ids": direct_ids,
            "articulated_knowledge_ids": articulated_ids,
            "knowledge_ids": all_knowledge,
            "articulation_ids": articulation_ids,
            "criterion_ids": criterion_ids,
            "direct_criterion_ids": direct_criteria,
            "rows": retrieval,
            "excluded_knowledge": unique(excluded),
            "conditional_knowledge": unique(conditional),
        }

    def articulation_authorized(self, identifier):
        row = self.articulations.get(identifier, {})
        allowed_curation = {
            "APROVADA_PARA_CONSULTA",
            "APROVADA_PARA_TESTE_RC2",
            "APROVADA_PARA_CONSULTA_RC3",
            "APROVADA_PARA_O_CASO_RC3",
        }
        allowed_confirmation = {
            "DOCUMENTADA_DIRETAMENTE",
            "RECONSTRUIDA_A_PARTIR_DAS_PUBLICACOES",
            "INFORMADA_PELA_AUTORA",
            "DOCUMENTADA_E_RECONSTRUIDA",
            "DOCUMENTADA_E_INFORMADA_PELA_AUTORA",
        }
        authorized = (
            row.get("habilitada_para_decisao") is True
            and row.get("estado_curadoria") in allowed_curation
            and row.get("nivel_confirmacao") in allowed_confirmation
        )
        self._check("articulation", identifier, "curation_and_confirmation", "PASS" if authorized else "FAIL",
                    "Conferência de habilitação, curadoria e origem da relação.", operator="ALL",
                    enabled=row.get("habilitada_para_decisao"), curation=row.get("estado_curadoria"),
                    confirmation=row.get("nivel_confirmacao"))
        return authorized

    def authorize_knowledge(self, identifier, context):
        """Selection gate, distinct from candidate retrieval; never uses diagnosis/name IDs."""
        knowledge = self.knowledge[identifier]
        present = {
            v
            for field in self.context_fields
            if field not in {"recursos_impedidos", "recursos_propostos"}
            for v in context.get(field, [])
        }
        blocked = set(context.get("recursos_impedidos", []))
        reasons = []
        app = knowledge.get("aplicabilidade") or {}
        tasks = set(app.get("tarefas", []))
        task_closure = set(context.get("tarefas", []))
        for task in list(task_closure):
            task_closure.update(
                local_id(v)
                for v in self.graph.transitive_objects(MADO[task], SKOS.broader)
            )
        self._check("knowledge", identifier, "task_compatibility", "PASS" if not tasks or tasks & task_closure else "FAIL",
                    "Compatibilidade da tarefa com sua hierarquia declarada.", operator="ANY_OR_UNCONSTRAINED",
                    expected_ids=sorted(tasks), observed_ids=sorted(task_closure), matched_ids=sorted(tasks & task_closure))
        if tasks and not tasks.intersection(task_closure):
            reasons.append(
                "A tarefa do conhecimento não corresponde à tarefa informada."
            )
        impediments = set(knowledge.get("condicoes_impeditivas_ids", [])) & present
        required = set(knowledge.get("condicoes_necessarias_ids", []))
        self._check("knowledge", identifier, "no_structured_impediment", "FAIL" if impediments or required & blocked else "PASS",
                    "Verificação de condições impeditivas e recursos necessários impedidos.", operator="NONE",
                    expected_ids=sorted(set(knowledge.get("condicoes_impeditivas_ids", [])) | required),
                    observed_ids=sorted(present | blocked), matched_ids=sorted(impediments | (required & blocked)))
        if impediments:
            reasons.append(
                "Condição impeditiva presente: "
                + ", ".join(self.labels(sorted(impediments)))
            )
        if required & blocked:
            reasons.append(
                "Recurso necessário impedido: "
                + ", ".join(self.labels(sorted(required & blocked)))
            )
        if knowledge.get("classificacao_operacional") == "PENDENTE_DE_FUNDAMENTACAO":
            reasons.append("Conhecimento ainda pendente de fundamentação.")
        if not knowledge.get("fonte_ids") or not knowledge.get("trecho_ids"):
            reasons.append("Conhecimento sem fonte e localização documental.")
        self._check("knowledge", identifier, "documentary_presence", "PASS" if knowledge.get("fonte_ids") and knowledge.get("trecho_ids") else "FAIL",
                    "Presença de referências documentais; não verifica integralmente a correção da conclusão.",
                    operator="PRESENCE", source_ids=knowledge.get("fonte_ids", []), excerpt_ids=knowledge.get("trecho_ids", []))
        self._check("knowledge", identifier, "foundation_operational_state",
                    "FAIL" if knowledge.get("classificacao_operacional") == "PENDENTE_DE_FUNDAMENTACAO" else "PASS",
                    "Estado operacional permitido pelo catálogo.", operator="NOT_EQUAL",
                    observed=knowledge.get("classificacao_operacional"), forbidden="PENDENTE_DE_FUNDAMENTACAO")
        if reasons:
            return "EXCLUIDO", reasons
        missing = required - present
        conditional_missing = bool(missing) and knowledge.get("classificacao_operacional") == "CONDICIONAL" and all(
            self.concepts.get(v, {}).get("tipo") == "recurso_disponivel" or v.startswith("REC-") for v in missing)
        self._check("knowledge", identifier, "required_conditions", "PENDING" if conditional_missing else ("FAIL" if missing else "PASS"),
                    "Condições necessárias estruturadas do conhecimento.", operator="ALL",
                    expected_ids=sorted(required), observed_ids=sorted(present), matched_ids=sorted(required & present), missing_ids=sorted(missing))
        if missing:
            if knowledge.get("classificacao_operacional") == "CONDICIONAL" and all(
                self.concepts.get(v, {}).get("tipo") == "recurso_disponivel"
                or v.startswith("REC-")
                for v in missing
            ):
                return "CONDICIONAL", [
                    "Confirmar recurso antes da aplicação: "
                    + ", ".join(self.labels(sorted(missing)))
                ]
            return "EXCLUIDO", [
                "Condição necessária ausente: "
                + ", ".join(self.labels(sorted(missing)))
            ]
        return "APLICAVEL", []

    def evaluate_component(
        self, component, context, authorized_knowledge, authorized_criteria
    ):
        reasons, matches = ([], [])
        available_roles = {
            row.get("papel_id") for row in self.current.get("participations", [])
        }
        missing_roles = set(component.get("required_role_ids", [])) - available_roles
        if (
            "PAPEL-PESSOA-APOIADA" in missing_roles
            and "PAPEL-ESTUDANTE" in available_roles
        ):
            missing_roles.remove("PAPEL-PESSOA-APOIADA")
        self._check("component", component["id"], "required_roles", "FAIL" if missing_roles else "PASS",
                    "Papéis participantes exigidos pelo padrão.", operator="ALL_WITH_STUDENT_AS_SUPPORTED_PERSON",
                    expected_ids=component.get("required_role_ids", []), observed_ids=sorted(available_roles), missing_ids=sorted(missing_roles))
        if missing_roles:
            reasons.append(
                "papel participante ausente: "
                + ", ".join(self.labels(sorted(missing_roles)))
            )
        required_resources = set(component.get("required_resource_ids", []))
        resource_groups = component.get("required_any_resource_groups", [])
        if not required_resources and (not resource_groups):
            resource_groups = [component.get("resource_ids", [])]
        available_resources = set(context.get("recursos_disponiveis", []))
        blocked_resources = set(context.get("recursos_impedidos", []))
        blocked_core_resources = required_resources & blocked_resources
        unknown_core_resources = (
            required_resources - available_resources - blocked_resources
        )
        if blocked_core_resources:
            reasons.append(
                "recurso nuclear explicitamente impedido: "
                + ", ".join(self.labels(sorted(blocked_core_resources)))
            )
        resource_gate = "CONFIRMADO_DISPONIVEL"
        if unknown_core_resources:
            if component.get("role") == "condicional" and component.get("alternative"):
                resource_gate = "CONDICIONAL_A_CONFIRMACAO"
                matches.append(
                    {
                        "field": "recursos_a_confirmar",
                        "ids": sorted(unknown_core_resources),
                        "labels": self.labels(sorted(unknown_core_resources)),
                    }
                )
            else:
                reasons.append(
                    "recurso nuclear ainda não confirmado: "
                    + ", ".join(self.labels(sorted(unknown_core_resources)))
                )
        self._check("component", component["id"], "core_resources",
                    "FAIL" if blocked_core_resources or (unknown_core_resources and resource_gate != "CONDICIONAL_A_CONFIRMACAO") else
                    ("PENDING" if unknown_core_resources else "PASS"),
                    "Disponibilidade dos recursos nucleares.", operator="ALL",
                    expected_ids=sorted(required_resources), observed_ids=sorted(available_resources),
                    matched_ids=sorted(required_resources & available_resources), blocked_ids=sorted(blocked_core_resources),
                    missing_ids=sorted(unknown_core_resources))
        for group_index, group in enumerate(resource_groups, 1):
            options = set(group)
            group_pending = bool(options and not options & available_resources and not options <= blocked_resources
                                 and component.get("role") == "condicional" and component.get("alternative"))
            self._check("component", component["id"], f"resource_option_group_{group_index}",
                        "PASS" if options & available_resources else ("PENDING" if group_pending else "FAIL"),
                        "Ao menos um recurso deste grupo deve estar disponível.", operator="ANY",
                        expected_ids=sorted(options), observed_ids=sorted(available_resources), matched_ids=sorted(options & available_resources))
            if options & available_resources:
                matches.append(
                    {
                        "field": "recursos_disponiveis",
                        "ids": sorted(options & available_resources),
                        "labels": self.labels(sorted(options & available_resources)),
                    }
                )
            elif options and options <= blocked_resources:
                reasons.append(
                    "todos os meios alternativos estão impedidos: "
                    + ", ".join(self.labels(sorted(options)))
                )
            elif (
                component.get("role") == "condicional"
                and component.get("alternative")
                and options
            ):
                resource_gate = "CONDICIONAL_A_CONFIRMACAO"
                matches.append(
                    {
                        "field": "recursos_a_confirmar",
                        "ids": sorted(options - blocked_resources),
                        "labels": self.labels(sorted(options - blocked_resources)),
                    }
                )
            else:
                reasons.append(
                    "nenhum meio necessário confirmado: "
                    + ", ".join(self.labels(sorted(options)))
                )
        proposed_outputs = set(component.get("proposed_resource_ids", []))
        self._check("component", component["id"], "proposed_outputs_not_blocked", "FAIL" if proposed_outputs & blocked_resources else "PASS",
                    "Adaptações a preparar não podem estar impedidas.", operator="NONE",
                    expected_ids=sorted(proposed_outputs), observed_ids=sorted(blocked_resources), matched_ids=sorted(proposed_outputs & blocked_resources))
        if proposed_outputs & blocked_resources:
            reasons.append(
                "adaptação necessária explicitamente impedida: "
                + ", ".join(self.labels(sorted(proposed_outputs & blocked_resources)))
            )
        if (
            proposed_outputs - available_resources
            and resource_gate == "CONFIRMADO_DISPONIVEL"
        ):
            resource_gate = "REQUER_PREPARACAO"
        if component["id"] == "PAD-VIDEO-PROCESSO":
            # This authored pattern explicitly promises captions and visual description.
            # Reject a contradictory instruction; do not invent a new media alternative.
            conflicting_access = blocked_resources & {"REC-LEGENDAS", "REC-AUDIODESCRICAO"}
            self._check("component", component["id"], "video_instruction_resource_consistency",
                        "FAIL" if conflicting_access else "PASS",
                        "A instrução registrada não pode exigir legenda ou audiodescrição explicitamente impedida.",
                        operator="NONE", expected_ids=["REC-LEGENDAS", "REC-AUDIODESCRICAO"],
                        observed_ids=sorted(blocked_resources), matched_ids=sorted(conflicting_access))
            if conflicting_access:
                reasons.append("a instrução deste padrão de vídeo exige recurso de acessibilidade impedido; sua alternativa textual não foi replanejada")
        for field, identifiers in component.get("requires_all", {}).items():
            matched = self.intersects(context, field, identifiers)
            self._check("component", component["id"], f"required_field_{field}", "PASS" if matched else "FAIL",
                        "Cada campo é obrigatório; os conceitos dentro do campo são opções alternativas.", operator="ANY_IN_FIELD",
                        field=field, expected_ids=identifiers, observed_ids=context.get(field, []),
                        matched_ids=sorted(set(context.get(field, [])) & set(identifiers)))
            if matched:
                values = sorted(set(context.get(field, [])) & set(identifiers))
                matches.append(
                    {"field": field, "ids": values, "labels": self.labels(values)}
                )
            else:
                reasons.append(f"sem correspondência obrigatória em {field}")
        any_groups = component.get("requires_any_groups") or (
            [component.get("requires_any", [])] if component.get("requires_any") else []
        )
        for group_index, clauses in enumerate(any_groups, 1):
            group_match = False
            for clause in clauses:
                if self.intersects(context, clause["field"], clause["ids"]):
                    group_match = True
                    values = sorted(
                        set(context.get(clause["field"], [])) & set(clause["ids"])
                    )
                    matches.append(
                        {
                            "field": clause["field"],
                            "ids": values,
                            "labels": self.labels(values),
                        }
                    )
            if not group_match:
                reasons.append(
                    f"grupo funcional {group_index} sem condição contextual compatível"
                )
            self._check("component", component["id"], f"functional_group_{group_index}", "PASS" if group_match else "FAIL",
                        "Pelo menos uma condição deste grupo deve corresponder ao contexto.", operator="ANY_CLAUSE",
                        clauses=[{"field": c["field"], "expected_ids": c["ids"], "observed_ids": context.get(c["field"], []),
                                  "matched_ids": sorted(set(c["ids"]) & set(context.get(c["field"], [])))} for c in clauses],
                        matched_ids=unique(v for c in clauses for v in c["ids"] if v in context.get(c["field"], [])))
        component_knowledge = [
            kid
            for kid in component["knowledge_ids"]
            if kid in authorized_knowledge
            and (
                self.authorize_knowledge(kid, context)[0] == "APLICAVEL"
                or component.get("role") == "condicional"
                and self.authorize_knowledge(kid, context)[0] == "CONDICIONAL"
            )
        ]
        if any(
            self.authorize_knowledge(kid, context)[0] == "CONDICIONAL"
            for kid in component_knowledge
        ):
            resource_gate = "CONDICIONAL_A_CONFIRMACAO"
        if not component_knowledge:
            reasons.append(
                "nenhum conhecimento do componente foi recuperado pela consulta semântica"
            )
        self._check("component", component["id"], "retrieved_knowledge", "PASS" if component_knowledge else "FAIL",
                    "Conhecimento recuperado e autorizado que pertence a este padrão.", operator="ANY",
                    expected_ids=component["knowledge_ids"], observed_ids=authorized_knowledge, matched_ids=component_knowledge)
        component_criteria = []
        for support in component.get("criterion_support", []):
            cid = support.get("criterion_id")
            if cid not in self.criteria:
                reasons.append(f"critério {cid} não localizado")
                continue
            common = set(support.get("knowledge_ids", [])) & set(component_knowledge)
            origins = [
                oid
                for oid in support.get("origin_ids", [])
                if self.valid_origin(oid, cid)
            ]
            if (
                cid in authorized_criteria
                and common
                and origins
                and str(support.get("justification", "")).strip()
            ):
                component_criteria.append(cid)
            self._check("component", component["id"], "criterion_support_" + cid,
                        "PASS" if cid in component_criteria else "FAIL",
                        "Ligação situada entre critério, conhecimento autorizado, origem válida e justificativa registrada.",
                        operator="ALL", criterion_id=cid, knowledge_ids=sorted(common), origin_ids=origins,
                        authorized=cid in authorized_criteria, justification_present=bool(str(support.get("justification", "")).strip()))
        if not component_criteria:
            reasons.append(
                "nenhum critério com conhecimento e origem documental situados foi recuperado"
            )
        self._check("component", component["id"], "any_situated_criterion", "PASS" if component_criteria else "FAIL",
                    "Ao menos um critério com suporte situado é exigido; nem todo critério candidato foi usado.", operator="ANY", matched_ids=component_criteria)
        maturity = {
            "funcao": bool(str(component.get("function", "")).strip()),
            "responsavel": bool(component.get("responsible_role_id")),
            "condicao": bool(component.get("conditions")),
            "alternativa": bool(str(component.get("alternative", "")).strip()),
            "acompanhamento": bool(str(component.get("monitoring", "")).strip()),
            "limite": bool(str(component.get("limit", "")).strip()),
            "origem_criterio": any(
                (s.get("origin_ids") for s in component.get("criterion_support", []))
            ),
        }
        for gate, passed in maturity.items():
            self._check("component", component["id"], "documented_field_" + gate, "PASS" if passed else "FAIL",
                        "Conferência da presença de um campo documental, não da eficácia do seu conteúdo.", operator="PRESENCE", field=gate)
            if not passed:
                reasons.append(f"porta de maturidade ausente: {gate}")
        return (
            not reasons,
            matches,
            reasons,
            component_knowledge,
            component_criteria,
            resource_gate,
        )

    def selected_support(self, component, knowledge_ids, criterion_ids):
        rows = []
        for support in component.get("criterion_support", []):
            if support.get("criterion_id") not in criterion_ids:
                continue
            common = [
                kid for kid in support.get("knowledge_ids", []) if kid in knowledge_ids
            ]
            origins = [
                oid
                for oid in support.get("origin_ids", [])
                if self.valid_origin(oid, support.get("criterion_id"))
            ]
            if common and origins:
                rows.append(
                    {
                        **support,
                        "selected_knowledge_ids": common,
                        "selected_origin_ids": origins,
                    }
                )
        return rows

    def valid_origin(self, origin_id, criterion_id):
        origin = self.criterion_origins.get(origin_id, {})
        return (
            origin.get("criterio_id") == criterion_id
            and origin.get("fonte_id") in self.sources
            and origin.get("trecho_id") in self.excerpts
        )

    def knowledge_matches(self, knowledge, context):
        matches = []
        for context_field, app_field in self.context_fields.items():
            values = set(context.get(context_field, [])) & set(
                (knowledge.get("aplicabilidade") or {}).get(app_field, [])
            )
            if values:
                ordered = sorted(values)
                matches.append(
                    {
                        "field": context_field,
                        "ids": ordered,
                        "labels": self.labels(ordered),
                    }
                )
        return matches

    def trace_knowledge(self, knowledge_ids, context, component_map):
        rows = []
        for kid in knowledge_ids:
            row = self.knowledge[kid]
            rows.append(
                {
                    "id": kid,
                    "classification": row.get("classificacao_operacional", ""),
                    "enunciado": row["enunciado"],
                    "articulacao": row.get("articulacao", ""),
                    "matched_by": self.knowledge_matches(row, context),
                    "selected_by_components": component_map.get(kid, []),
                    "fontes": [
                        {"id": sid, "titulo": self.sources[sid].get("titulo", sid)}
                        for sid in row.get("fonte_ids", [])
                    ],
                    "trechos": [
                        {"id": tid, "texto": self.excerpts[tid].get("trecho", "")}
                        for tid in row.get("trecho_ids", [])
                    ],
                    "perspectivas": row.get("perspectiva_ids", []),
                    "limite": row.get("limite_transferencia") or row.get("limite", ""),
                }
            )
        return rows

    def historical_precedents(self, knowledge_ids):
        selected, precedents = (set(knowledge_ids), [])
        for decision in self.decisions.values():
            if decision["id"].startswith("D-TESTE") or decision["id"] == "D-ELIC-01":
                continue
            used = set(decision.get("conhecimento_principal_ids", [])) | set(
                decision.get("conhecimento_condicional_ids", [])
            )
            common = sorted(selected & used)
            if common:
                precedents.append(
                    {
                        "id": decision["id"],
                        "enunciado": decision.get("enunciado", ""),
                        "shared_knowledge": common,
                        "limite": decision.get("limite", ""),
                        "resultados": [
                            self.results[rid].get("descricao")
                            or self.results[rid].get("enunciado", "")
                            for rid in decision.get("resultado_ids", [])
                            if rid in self.results
                        ],
                    }
                )
        return precedents

    def entity_title(self, identifier):
        if identifier in self.studies:
            return (
                self.studies[identifier].get("titulo")
                or self.studies[identifier].get("nome")
                or identifier
            )
        if identifier in self.artifacts:
            return (
                self.artifacts[identifier].get("nome")
                or self.artifacts[identifier].get("titulo")
                or identifier
            )
        if identifier in self.personas:
            row = self.personas[identifier]
            return f"Persona {row.get('nome', identifier)}"
        if identifier in self.sources:
            return self.sources[identifier].get("titulo", identifier)
        return self.label(identifier)

    def compose_transfer_orientation(self, selected, context):
        by_id = {item["id"]: item for item in selected}
        phases = [
            (
                "1. Organizar objetivo, autoria e transições",
                ["PAD-ORGANIZAR-CONTEUDO-PERSISTENTE", "PAD-PAPEIS-TURNOS-AUTORIA"],
            ),
            (
                "2. Produzir e preservar a contribuição autoral",
                [
                    "PAD-EXPRESSAO-AUTORAL-FALA-AUDIO",
                    "PAD-REPRESENTACAO-VISUAL-EXPLICADA",
                ],
            ),
            (
                "3. Acrescentar vídeo ou jogo somente pela função",
                ["PAD-VIDEO-PROCESSO", "PAD-JOGO-CONSOLIDACAO-FEEDBACK"],
            ),
            (
                "4. Revisar, confirmar e registrar o que precisa mudar",
                ["PAD-REVISAO-CONFIRMACAO"],
            ),
        ]
        rendered = []
        for title, identifiers in phases:
            actions = [
                str(by_id[i]["action"]).strip().rstrip(".")
                for i in identifiers
                if i in by_id
            ]
            if actions:
                rendered.append(f"{title}: " + "; ".join(actions) + ".")
        known = {identifier for _, identifiers in phases for identifier in identifiers}
        remaining = [item for item in selected if item["id"] not in known]
        for index, item in enumerate(remaining, 1):
            action = str(item.get("action", "")).strip().rstrip(".")
            if action:
                rendered.append(
                    f"{index}. {item.get('label', 'Configuração aplicável')}: {action}."
                )
        objective = str(context.get("objetivo", "")).strip().rstrip(".")
        framing = (
            "construa o recurso como uma produção compartilhada com autoria identificável, função explícita para cada modo e alternativa equivalente. "
            if set(by_id) & known
            else "combine os meios disponíveis conforme as funções abaixo e prepare as adaptações indicadas antes de usá-las. "
        )
        return (
            f"Para {(objective[:1].lower() + objective[1:] if objective else 'responder ao objetivo confirmado')}, "
            + framing
            + " ".join(rendered)
        )

    def build_practical_summary(self, configurations, status, context=None):
        """Projeta a mesma decisão em linguagem simples, sem selecionar conteúdo novo."""
        if status not in {"GERADA", "GERADA_PARCIAL"} or not configurations:
            return {
                "titulo": "Ainda não é possível orientar este caso",
                "texto": "Faltam informações ou conhecimentos verificados para construir uma orientação segura.",
                "etapas": [],
                "component_ids": [],
                "derivacao": "PROJECAO_DA_MESMA_DECISAO_SEM_NOVO_CONTEUDO",
            }
        by_id = {
            item.get("component_id", item.get("id")): item for item in configurations
        }
        primary = next(
            (
                item
                for item in configurations
                if item.get("papel", item.get("role")) == "principal"
            ),
            configurations[0],
        )
        primary_id = primary.get("component_id", primary.get("id"))
        interview_ids = {
            "PAD-ORGANIZAR-CONTEUDO-PERSISTENTE",
            "PAD-EXPRESSAO-AUTORAL-FALA-AUDIO",
            "PAD-REPRESENTACAO-VISUAL-EXPLICADA",
            "PAD-VIDEO-PROCESSO",
            "PAD-JOGO-CONSOLIDACAO-FEEDBACK",
            "PAD-PAPEIS-TURNOS-AUTORIA",
            "PAD-REVISAO-CONFIRMACAO",
        }
        selected_ids = set(by_id)
        if selected_ids & interview_ids:
            clauses = []
            if "PAD-ORGANIZAR-CONTEUDO-PERSISTENTE" in selected_ids:
                clauses.append("texto para organizar e retomar")
            if "PAD-EXPRESSAO-AUTORAL-FALA-AUDIO" in selected_ids:
                clauses.append("fala e áudio para preservar a autoria")
            if "PAD-REPRESENTACAO-VISUAL-EXPLICADA" in selected_ids:
                clauses.append("imagem e desenho para representar relações")
            headline = "Construa o recurso em partes curtas: " + "; ".join(clauses) + "."
            optional_modes = [label for identifier, label in (
                ("PAD-VIDEO-PROCESSO", "vídeo"), ("PAD-JOGO-CONSOLIDACAO-FEEDBACK", "jogo")) if identifier in selected_ids]
            if optional_modes:
                headline += " Considere " + " e ".join(optional_modes) + " somente quando cumprir uma função necessária, com acessibilidade, feedback e alternativa."
        else:
            headline = PRACTICAL_HEADLINES.get(
                primary_id,
                f"Comece por esta ação: {str(primary.get('acao', primary.get('action', ''))).strip().rstrip('.')}.",
            )
        group_specs = [
            (
                "estrutura",
                "Organizar conteúdo, participação e retomada",
                ["PAD-ORGANIZAR-CONTEUDO-PERSISTENTE", "PAD-PAPEIS-TURNOS-AUTORIA"],
            ),
            (
                "autoria",
                "Combinar voz, texto, imagem e desenho",
                [
                    "PAD-EXPRESSAO-AUTORAL-FALA-AUDIO",
                    "PAD-REPRESENTACAO-VISUAL-EXPLICADA",
                ],
            ),
            ("video", "Vídeo como possibilidade funcional", ["PAD-VIDEO-PROCESSO"]),
            (
                "jogo",
                "Jogo como possibilidade funcional",
                ["PAD-JOGO-CONSOLIDACAO-FEEDBACK"],
            ),
            (
                "revisao",
                "Revisar e confirmar antes de concluir",
                ["PAD-REVISAO-CONFIRMACAO"],
            ),
        ]
        used, groups = (set(), [])

        def build_group(group_id, title, component_ids):
            rows = [
                by_id[identifier] for identifier in component_ids if identifier in by_id
            ]
            if not rows:
                return None
            used.update(component_ids)
            copies = [
                PRACTICAL_COPY.get(identifier, {})
                for identifier in component_ids
                if identifier in by_id
            ]
            availability = unique(
                (
                    row.get("availability_status", "CONFIRMADO_DISPONIVEL")
                    for row in rows
                )
            )
            return {
                "id": group_id,
                "titulo": title,
                "modos": unique(
                    (
                        row.get("modo", self.label(row.get("mode_id")))
                        for row in rows
                        if row.get("modo") or row.get("mode_id")
                    )
                ),
                "funcao": " ".join(
                    unique(
                        (
                            str(row.get("funcao", row.get("function", ""))).strip()
                            for row in rows
                            if str(row.get("funcao", row.get("function", ""))).strip()
                        )
                    )
                ),
                "como_combinar": " ".join(
                    unique(
                        (
                            copy_row.get("relation", "")
                            for copy_row in copies
                            if copy_row.get("relation")
                        )
                    )
                ),
                "itens": [
                    copy_row.get("text", "")
                    for copy_row in copies
                    if copy_row.get("text")
                ],
                "condicoes": unique(
                    (value for row in rows for value in row.get("conditions", []))
                ),
                "alternativas": unique(
                    (
                        row.get("alternative", "")
                        for row in rows
                        if row.get("alternative")
                    )
                ),
                "acompanhamento": unique(
                    (row.get("monitoring", "") for row in rows if row.get("monitoring"))
                ),
                "estado_recurso": availability,
                "recursos": unique(
                    (
                        resource.get("label")
                        for row in rows
                        for resource in row.get("resource_options", [])
                        if resource.get("label")
                    )
                ),
                "recursos_estruturados": unique(
                    (
                        resource
                        for row in rows
                        for resource in row.get("resource_options", [])
                    )
                ),
                "component_ids": [
                    row.get("component_id", row.get("id")) for row in rows
                ],
            }

        for group_id, title, identifiers in group_specs:
            group = build_group(group_id, title, identifiers)
            if group:
                groups.append(group)
        for identifier, row in by_id.items():
            if identifier in used:
                continue
            copy_row = PRACTICAL_COPY.get(identifier, {})
            group = build_group(
                f"other-{identifier}",
                copy_row.get("title", row.get("label", "Como aplicar")),
                [identifier],
            )
            if group:
                groups.append(group)
        return {
            "titulo": "Sugestão para este caso",
            "texto": headline,
            "etapas": groups,
            "component_ids": [
                item.get("component_id", item.get("id")) for item in configurations
            ],
            "resultado_esperado": " ".join(
                unique(
                    (
                        item.get("monitoring")
                        for item in configurations
                        if item.get("monitoring")
                    )
                )
            ),
            "aviso_resultado": "Esses são sinais para acompanhamento, não uma garantia de aprendizagem ou de eficácia em outros contextos.",
            "derivacao": "PROJECAO_DA_MESMA_DECISAO_SEM_NOVO_CONTEUDO",
        }

    def build_de_para(self, selected=None, retrieval=None):
        """Compatibility accessor: explanations are built once from execution evidence."""
        result = self.current.get("last_result") or {}
        if result.get("explanation"):
            return copy.deepcopy(result["explanation"]["de_para"])
        raise RuntimeError("Execute a decisão antes de solicitar sua explicação.")

    def build_decision_graph(self, result):
        graph = self.build_context_graph()
        c, ctx = (self.current["context"], MADO[self.current["context"]["id"]])
        decision = MADO[result["decision"]["id"]]
        if self.current.get("mapping_confirmed"):
            graph.set((ctx, MADO.statusConfirmacao, Literal("CONFIRMADO_PARA_GERACAO")))
        graph.add(
            (ctx, MADO.statusDoRegistro, Literal("CONTEXTO_TEMPORARIO_NAO_EMPIRICO"))
        )
        for missing in result["decision"].get("informacoes_ausentes", []):
            graph.add((ctx, MADO.informacaoAusente, Literal(missing, lang="pt-BR")))
        graph.add((decision, RDF.type, MADO.DecisaoDeAcessibilidadeMultimodal))
        graph.add((decision, MADO.identificador, Literal(result["decision"]["id"])))
        graph.add((decision, MADO.respondeA, ctx))
        graph.add(
            (
                decision,
                MADO.enunciado,
                Literal(result["decision"]["orientacao_principal"], lang="pt-BR"),
            )
        )
        graph.add(
            (
                decision,
                MADO.rationale,
                Literal(result["decision"]["justificativa"], lang="pt-BR"),
            )
        )
        graph.add((decision, MADO.statusDecisao, Literal(result["decision"]["status"])))
        for index, item in enumerate(
            result["decision"].get("configuracao_modal", []), 1
        ):
            configuration = MADO[f"CFG-{result['decision']['id']}-{index:02d}"]
            graph.add((configuration, RDF.type, MADO.ConfiguracaoModalDaDecisao))
            graph.add(
                (
                    configuration,
                    MADO.identificador,
                    Literal(f"CFG-{result['decision']['id']}-{index:02d}"),
                )
            )
            graph.add((configuration, MADO.configuracaoDeDecisao, decision))
            graph.add((decision, MADO.possuiConfiguracaoModal, configuration))
            if item.get("mode_id"):
                graph.add((decision, MADO.articulaModalidade, MADO[item["mode_id"]]))
                graph.add(
                    (configuration, MADO.configuraModalidade, MADO[item["mode_id"]])
                )
            graph.add(
                (
                    configuration,
                    MADO.executadaPorPapel,
                    MADO[item["responsible_role_id"]],
                )
            )
            graph.add((configuration, MADO.temPapelModal, MADO[item["modal_role_id"]]))
            graph.add(
                (
                    configuration,
                    MADO.temFuncaoModal,
                    Literal(item["funcao"], lang="pt-BR"),
                )
            )
            graph.add(
                (
                    configuration,
                    MADO.temAcaoOperacional,
                    Literal(item["acao"], lang="pt-BR"),
                )
            )
            graph.add(
                (
                    configuration,
                    MADO.origemDoRegistro,
                    Literal(
                        item.get("contribution_status", "RECUPERADO_DE_ESTUDO_ANTERIOR")
                    ),
                )
            )
            graph.add(
                (
                    configuration,
                    MADO.significadoFuncional,
                    Literal(item.get("functional_meaning", ""), lang="pt-BR"),
                )
            )
            graph.add(
                (
                    configuration,
                    MADO.estadoDeDisponibilidadeDaConfiguracao,
                    Literal(item.get("availability_status", "CONFIRMADO_DISPONIVEL")),
                )
            )
            for function_id in item.get("function_ids", []):
                graph.add(
                    (configuration, MADO.cumpreFuncaoDecisoria, MADO[function_id])
                )
            for resource_id in item.get("resource_ids", []):
                graph.add((configuration, MADO.configuraRecurso, MADO[resource_id]))
            for condition_id in item.get("condition_ids", []):
                graph.add(
                    (
                        configuration,
                        MADO.configuracaoConsideraCondicao,
                        MADO[condition_id],
                    )
                )
            for knowledge_id in item.get("knowledge_ids", []):
                graph.add(
                    (
                        configuration,
                        MADO.configuracaoSustentadaPorConhecimento,
                        MADO[knowledge_id],
                    )
                )
            for criterion_id in item.get("criterion_ids", []):
                graph.add(
                    (configuration, MADO.configuracaoAplicaCriterio, MADO[criterion_id])
                )
            for articulation_id in item.get("articulation_ids", []):
                graph.add(
                    (
                        configuration,
                        MADO.configuracaoMobilizaArticulacao,
                        MADO[articulation_id],
                    )
                )
            for origin_id in item.get("criterion_origin_ids", []):
                graph.add(
                    (
                        configuration,
                        MADO.configuracaoUsaOrigemDoCriterio,
                        MADO[origin_id],
                    )
                )
            for support_index, support in enumerate(
                item.get("criterion_support", []), 1
            ):
                application = MADO[
                    f"APL-{result['decision']['id']}-{index:02d}-{support_index:02d}"
                ]
                graph.add((application, RDF.type, MADO.AplicacaoDeCriterio))
                graph.add((configuration, MADO.possuiAplicacaoDeCriterio, application))
                graph.add((application, MADO.aplicacaoNaConfiguracao, configuration))
                graph.add(
                    (application, MADO.criterioAplicado, MADO[support["criterion_id"]])
                )
                graph.add(
                    (
                        application,
                        MADO.justificativaDaAplicacao,
                        Literal(support["justification"], lang="pt-BR"),
                    )
                )
                for kid in support["selected_knowledge_ids"]:
                    graph.add((application, MADO.conhecimentoDaAplicacao, MADO[kid]))
                for contribution in self.data.get("contributions", []):
                    kid, aid = contribution.get("knowledge_id"), contribution.get("articulation_id")
                    if (kid in support["selected_knowledge_ids"]
                            and aid in item.get("articulation_ids", [])
                            and kid in self.articulations.get(aid, {}).get("conhecimento_resultante_ids", [])):
                        graph.add((application, MADO.aplicacaoMobilizaContribuicao, MADO[contribution["id"]]))
                for oid in support["selected_origin_ids"]:
                    graph.add((application, MADO.origemDaAplicacao, MADO[oid]))
            for value in item.get("conditions", []):
                graph.add(
                    (
                        configuration,
                        MADO.condicaoDaConfiguracao,
                        Literal(value, lang="pt-BR"),
                    )
                )
            if item.get("alternative"):
                graph.add(
                    (
                        configuration,
                        MADO.alternativaDaConfiguracao,
                        Literal(item["alternative"], lang="pt-BR"),
                    )
                )
            if item.get("monitoring"):
                graph.add(
                    (
                        configuration,
                        MADO.acompanhamentoDaConfiguracao,
                        Literal(item["monitoring"], lang="pt-BR"),
                    )
                )
            if item.get("limit"):
                graph.add(
                    (
                        configuration,
                        MADO.limiteDaConfiguracao,
                        Literal(item["limit"], lang="pt-BR"),
                    )
                )
            graph.add(
                (
                    decision,
                    MADO.expressaoOperacional,
                    Literal(f"{item['papel']}: {item['funcao']}", lang="pt-BR"),
                )
            )
        for identifier in result["decision"].get("resource_ids", []):
            graph.add((decision, MADO.empregaRecurso, MADO[identifier]))
        for identifier in result["decision"].get("conditional_resource_ids", []):
            graph.add((decision, MADO.consideraRecursoCondicional, MADO[identifier]))
        for identifier in result["decision"].get("knowledge_ids", []):
            graph.add((decision, MADO.sustentadaPor, MADO[identifier]))
        for identifier in result["decision"].get("criterion_ids", []):
            graph.add((decision, MADO.aplicaCriterio, MADO[identifier]))
        for identifier in result["decision"].get("articulation_ids", []):
            graph.add((decision, MADO.mobilizaArticulacao, MADO[identifier]))
        if "K33" in result["decision"].get("knowledge_ids", []):
            graph.add((decision, MADO.atendeRequisitoDeExpressao, MADO.K33))
        for value in result["decision"].get("condicoes", []):
            graph.add(
                (decision, MADO.condicaoDeAplicacao, Literal(value, lang="pt-BR"))
            )
        for value in result["decision"].get("alternativas", []):
            graph.add((decision, MADO.alternativa, Literal(value, lang="pt-BR")))
        for value in result["decision"].get("acompanhamento", []):
            graph.add(
                (decision, MADO.indicadorDeAcompanhamento, Literal(value, lang="pt-BR"))
            )
        if result["decision"].get("resultado_esperado"):
            graph.add(
                (
                    decision,
                    MADO.resultadoEsperado,
                    Literal(result["decision"]["resultado_esperado"], lang="pt-BR"),
                )
            )
            graph.add(
                (
                    decision,
                    MADO.estatutoDoResultadoEsperado,
                    Literal(
                        result["decision"].get(
                            "estatuto_resultado_esperado", "EXPECTATIVA_OBSERVAVEL"
                        )
                    ),
                )
            )
        graph.add(
            (decision, MADO.limite, Literal(result["decision"]["limite"], lang="pt-BR"))
        )
        return graph

    def run_runtime_queries(self, runtime_graph, context_id, decision_id):
        combined, summary, results = (self.graph + runtime_graph, {}, {})
        for cq_id, query in self.queries.items():
            if cq_id == "CQ-008":
                runtime_query = query.replace(
                    "CTX-TESTE-RC2-DIAGNOSTICO-ISOLADO", context_id
                ).replace("D-TESTE-RC2-SUSPENSA", decision_id)
            else:
                runtime_query = query.replace(
                    "CTX-TRANSFERENCIA-RECURSO-DIGITAL-01", context_id
                )
                runtime_query = runtime_query.replace(
                    "D-TESTE-RC4-TRANSFERENCIA", decision_id
                )
            query_result = combined.query(runtime_query)
            headers = [str(value) for value in query_result.vars]
            serialized = [
                dict(
                    zip(headers, ["" if value is None else str(value) for value in row])
                )
                for row in query_result
            ]
            results[cq_id], summary[cq_id] = (serialized, len(serialized))
        return (summary, results)

    def trace_graph_payload(self, result):
        """Compatibility accessor; do not infer causal edges from grouped query rows."""
        return copy.deepcopy(result["explanation"]["graph"])

    def trace_svg(self, graph_payload):
        colors = {
            "context": "#0b5f73",
            "function": "#6f3c8f",
            "articulation": "#7b4b00",
            "knowledge": "#176b3a",
            "criterion": "#9a4f00",
            "criterion_origin": "#65502c",
            "configuration": "#2f5f8f",
            "source": "#354f85",
            "excerpt": "#465963",
            "contribution": "#764e20",
        }
        groups = [
            "context",
            "function",
            "articulation",
            "knowledge",
            "criterion",
            "criterion_origin",
            "configuration",
            "source",
            "excerpt",
            "contribution",
        ]
        grouped = {
            kind: [node for node in graph_payload["nodes"] if node["kind"] == kind]
            for kind in groups
        }
        positions = {}
        width = 35 + len(groups) * 230
        max_rows = max([len(grouped[kind]) for kind in groups] + [1])
        height = max(420, 90 + max_rows * 92)
        for column, kind in enumerate(groups):
            for row, node in enumerate(grouped[kind]):
                positions[node["id"]] = (35 + column * 230, 55 + row * 92)
        parts = [
            f'<svg xmlns="http://www.w3.org/2000/svg" role="img" aria-labelledby="title desc" viewBox="0 0 {width} {height}"><title id="title">Caminho da orientação</title><desc id="desc">Grafo do contexto às funções, articulações, conhecimentos, critérios, configurações e fontes.</desc><style>text{{font-family:Segoe UI,Arial,sans-serif;font-size:12px}} .edge{{stroke:#6b7780;stroke-width:1.4;marker-end:url(#arrow)}} .node{{rx:9;stroke:#fff;stroke-width:2}}</style><defs><marker id="arrow" markerWidth="8" markerHeight="8" refX="7" refY="3" orient="auto"><path d="M0,0 L0,6 L8,3 z" fill="#6b7780"/></marker></defs>'
        ]
        for edge in graph_payload["edges"]:
            if edge["source"] not in positions or edge["target"] not in positions:
                continue
            x1, y1 = positions[edge["source"]]
            x2, y2 = positions[edge["target"]]
            parts.append(
                f'<line class="edge" x1="{x1 + 180}" y1="{y1 + 30}" x2="{x2}" y2="{y2 + 30}"/>'
            )
        for node in graph_payload["nodes"]:
            x, y = positions[node["id"]]
            label = node["label"][:62] + ("…" if len(node["label"]) > 62 else "")
            parts.append(
                f"""<g tabindex="0" aria-label="{html.escape(node['kind'] + ': ' + node['label'])}"><rect class="node" x="{x}" y="{y}" width="180" height="60" fill="{colors[node['kind']]}"/><text x="{x + 9}" y="{y + 25}" fill="#fff">{html.escape(label[:30])}</text><text x="{x + 9}" y="{y + 43}" fill="#fff">{html.escape(label[30:60])}</text></g>"""
            )
        parts.append("</svg>")
        return "".join(parts)

    def _finish_execution_evidence(self, result):
        """Freeze checks and documentary references before making display projections."""
        evidence = self._evidence.data
        evidence["status"] = result["decision"]["status"]
        evidence["hashes"] = {
            "engine_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            "base_sha256": hashlib.sha256(DATA_JSON.read_bytes()).hexdigest(),
            "ontology_sha256": hashlib.sha256(ONTOLOGY.read_bytes()).hexdigest(),
            "cq2_sha256": hashlib.sha256(self.queries["CQ-002"].encode()).hexdigest(),
        }
        entities = evidence["entities"]
        catalogs = [self.knowledge, self.articulations, self.criteria, self.criterion_origins,
                    self.excerpts, self.sources, self.concepts, self.studies, self.artifacts, self.personas]

        def include(identifier):
            if not identifier or identifier in entities:
                return
            original = next((c[identifier] for c in catalogs if identifier in c), {})
            row = copy.deepcopy(original)
            row["id"] = identifier
            row["title"] = original.get("titulo") or original.get("enunciado") or original.get("rotulo") or original.get("nome") or self.label(identifier)
            entities[identifier] = row

        entities[evidence["context_id"]] = {"id": evidence["context_id"], "title": "Contexto confirmado desta execução"}
        for field in self.context_fields:
            for identifier in self.current["context"].get(field, []):
                include(identifier)
        selected_map = {c["component_id"]: c for c in evidence["components"]}
        used_knowledge = result["decision"]["knowledge_ids"]
        construction = {kid: [aid for aid, a in self.articulations.items() if kid in a.get("conhecimento_resultante_ids", [])]
                        for kid in used_knowledge}
        evidence["knowledge_construction"] = construction
        for kid in used_knowledge:
            include(kid)
            knowledge = self.knowledge[kid]
            for tid in knowledge.get("trecho_ids", []):
                include(tid)
                include(self.excerpts.get(tid, {}).get("fonte_id"))
            for sid in knowledge.get("fonte_ids", []):
                include(sid)
            pending = knowledge.get("pending_foundation_items", [])
            if pending or knowledge.get("foundation_review_status"):
                evidence["documentary_conditions"].append({"subject_id": kid, "outcome": "NOT_EXECUTED",
                    "text": "Revisão documental: " + str(knowledge.get("foundation_review_status", "não informada")),
                    "pending_foundation_items": pending,
                    "interpretation": "Fidelidade a um registro não confirma integralmente a fundamentação da conclusão."})
        for aid in unique(a for ids in construction.values() for a in ids):
            include(aid)
            art = self.articulations[aid]
            for field in ("conhecimento_entrada_ids", "fonte_ids", "estudo_ids", "artefato_ids", "persona_ids", "trecho_ids"):
                for identifier in art.get(field, []):
                    include(identifier)
            evidence["documentary_conditions"].append({"subject_id": aid, "outcome": "NOT_EXECUTED",
                "text": art.get("condicao", ""), "limit": art.get("limite", ""),
                "interpretation": "Condição documental livre; não foi avaliada como regra nesta execução."})
        evidence["contributions"] = []
        for contribution in self.data.get("contributions", []):
            kid, aid = contribution.get("knowledge_id"), contribution.get("articulation_id")
            if aid not in construction.get(kid, []):
                continue
            row = copy.deepcopy(contribution)
            tid = row.get("excerpt_id")
            excerpt = self.excerpts.get(tid, {})
            sid = excerpt.get("fonte_id")
            include(tid)
            include(sid)
            location = excerpt.get("localizacao_publica") or excerpt.get("localizacao") or "; ".join(
                str(excerpt[k]) for k in ("pagina", "secao") if excerpt.get(k))
            row["excerpt"] = {"id": tid, "location": location,
                              "publication_notice": excerpt.get("aviso_publicacao", ""), "publication_state": excerpt.get("estado_publicacao", "")}
            row["source"] = {"id": sid, "title": self.sources.get(sid, {}).get("titulo", sid)} if sid else None
            evidence["contributions"].append(row)
        for index, cfg in enumerate(result["decision"]["configuracao_modal"], 1):
            component = selected_map[cfg["component_id"]]
            component["configuration"] = {**copy.deepcopy(cfg), "id": f"CFG-{result['decision']['id']}-{index:02d}"}
            for fid in cfg.get("function_ids", []):
                include(fid)
            for condition in cfg.get("conditions", []):
                check_id = self._check("documentary", cfg["component_id"], "documentary_condition", "NOT_EXECUTED",
                                       "Condição textual preservada para julgamento; não executada pelo motor.", text=condition)
                evidence["documentary_conditions"].append({"subject_id": cfg["component_id"], "text": condition,
                                                           "outcome": "NOT_EXECUTED", "check_ids": [check_id]})
            for n, support in enumerate(cfg.get("criterion_support", []), 1):
                cid = support["criterion_id"]
                include(cid)
                origins = []
                for oid in support["selected_origin_ids"]:
                    origin = self.criterion_origins[oid]
                    for identifier in (oid, origin.get("fonte_id"), origin.get("trecho_id")):
                        include(identifier)
                    origins.append(copy.deepcopy(origin))
                evidence["supports"].append({"id": f"SUP-{cfg['component_id']}-{n:02d}",
                    "component_id": cfg["component_id"], "criterion_id": cid,
                    "criterion_statement": self.criteria[cid]["enunciado"],
                    "knowledge_ids": support["selected_knowledge_ids"], "origins": origins,
                    "justification": support.get("justification", ""),
                    "check_ids": [r["id"] for r in evidence["checks"] if r["subject_id"] == cfg["component_id"] and r["rule_id"] == "criterion_support_" + cid]})
        for witness in evidence["retrieval"]:
            for field in ("knowledge_id", "input_knowledge_id", "articulation_id", "context_concept_id", "required_function_id", "context_task_id", "knowledge_task_id"):
                include(witness.get(field))
        result["execution_evidence"] = copy.deepcopy(evidence)
        result["explanation"] = build_explanation(result["execution_evidence"])
        result["de_para"] = result["explanation"]["de_para"]

    def generate(self):
        context = self.current["context"]
        self._evidence = ExecutionEvidence(VERSION, context["id"])
        self._record_checks = True
        questions = self.missing_questions()
        if not self.current.get("mapping_confirmed"):
            questions = [
                {
                    "field": "mapping",
                    "question": "Confirme se a organização representa corretamente o contexto.",
                }
            ] + questions
        self._check("context", context["id"], "context_confirmation", "PASS" if self.current.get("mapping_confirmed") else "FAIL",
                    "Confirmação explícita da organização do contexto.", operator="IS_TRUE", observed=self.current.get("mapping_confirmed"))
        self._check("context", context["id"], "minimum_context", "FAIL" if questions else "PASS",
                    "Conferência dos campos mínimos antes de avaliar configurações.", operator="NO_MISSING_FIELDS",
                    missing_fields=[r["field"] for r in questions])
        context_graph = self.build_context_graph()
        retrieval = self.retrieve_transfer_candidates(context_graph)

        def select_components(knowledge_ids, criterion_ids, record=False):
            self._record_checks = record
            selected_rows, rejected_rows = ([], [])
            if questions:
                if record:
                    self._evidence.data["components"] = [
                        {"component_id": c["id"], "title": c["label"], "selection": "NOT_EVALUATED",
                         "check_ids": self._evidence.checks_for(context["id"], "context"),
                         "reasons": ["Contexto incompleto ou não confirmado; este padrão não foi avaliado."]}
                        for c in self.components]
                return (selected_rows, rejected_rows)
            for component in self.components:
                (
                    eligible,
                    matches,
                    reasons,
                    component_knowledge,
                    component_criteria,
                    resource_gate,
                ) = self.evaluate_component(
                    component, context, knowledge_ids, criterion_ids
                )
                if record:
                    self._evidence.data["components"].append({
                        "component_id": component["id"], "title": component["label"],
                        "selection": ("CONDITIONAL" if resource_gate == "CONDICIONAL_A_CONFIRMACAO" else "SELECTED") if eligible else "REJECTED",
                        "availability_status": resource_gate, "matches": copy.deepcopy(matches),
                        "check_ids": self._evidence.checks_for(component["id"], "component"), "reasons": reasons,
                    })
                if eligible:
                    resource_options = [
                        {
                            "id": rid,
                            "label": self.label(rid),
                            "opcional": bool(component.get("required_resource_ids"))
                            and rid not in component.get("required_resource_ids", [])
                            and (rid not in component.get("proposed_resource_ids", [])),
                            "estado": (
                                "PROPOSTO_A_PREPARAR"
                                if rid in component.get("proposed_resource_ids", [])
                                and self.resource_state(context, rid)
                                == "NAO_CONFIRMADO"
                                else self.resource_state(context, rid)
                            ),
                        }
                        for rid in unique(
                            component.get("resource_ids", [])
                            + component.get("proposed_resource_ids", [])
                        )
                    ]
                    selected_resources = [
                        row["id"]
                        for row in resource_options
                        if row["estado"] == "DISPONIVEL_CONFIRMADO"
                    ]
                    configured_resources = [
                        row["id"]
                        for row in resource_options
                        if row["estado"] != "IMPEDIDO"
                    ]
                    support_rows = self.selected_support(
                        component, component_knowledge, component_criteria
                    )
                    selected_rows.append(
                        {
                            **component,
                            "matches": matches,
                            "selected_knowledge_ids": component_knowledge,
                            "selected_criterion_ids": component_criteria,
                            "selected_resource_ids": selected_resources,
                            "configured_resource_ids": configured_resources,
                            "resource_options": resource_options,
                            "resource_gate": resource_gate,
                            "selected_support": support_rows,
                        }
                    )
                else:
                    rejected_rows.append(
                        {
                            "id": component["id"],
                            "label": component["label"],
                            "reasons": reasons,
                        }
                    )
            return (selected_rows, rejected_rows)

        selected, rejected = select_components(
            retrieval["knowledge_ids"], retrieval["criterion_ids"], record=True
        )
        isolated_selected, _ = select_components(
            retrieval["direct_knowledge_ids"], retrieval["direct_criterion_ids"]
        )
        self._record_checks = True
        primary = [item for item in selected if item.get("role") == "principal"]
        status = (
            "GERADA"
            if primary
            else "SUSPENSA_POR_CARACTERIZACAO_OU_COBERTURA_INSUFICIENTE"
        )
        if not primary:
            selected = []
            for row in self._evidence.data["components"]:
                if row["selection"] in {"SELECTED", "CONDITIONAL"}:
                    row["selection"] = "REJECTED"
                    row["reasons"].append("Não há configuração principal; o conjunto não foi emitido.")
                    row["check_ids"].append(self._check("component", row["component_id"], "principal_required", "FAIL",
                                                         "Um conjunto sem configuração principal é suspenso.", operator="ANY_PRIMARY"))
        if not primary and (not questions):
            questions = [
                {
                    "field": "coverage",
                    "question": "A base não possui configuração principal verificada para esta combinação; registre a lacuna antes de decidir.",
                }
            ]
        offered_functions = unique(f for item in selected for f in item.get("function_ids", []))
        required_functions = unique(context.get("funcoes_requeridas_ids", []))
        remaining_functions = [f for f in required_functions if f not in offered_functions]
        if primary and remaining_functions:
            status = "GERADA_PARCIAL"
        self._evidence.data["functions"] = {
            "required": required_functions, "offered": offered_functions,
            "verified": [f for f in required_functions if f in offered_functions],
            "remaining": remaining_functions,
            "interpretation": "Interseção declarada de requisitos e funções dos padrões; não comprova eficácia em uso.",
        }
        self._check("coverage", context["id"], "required_functions_coverage", "PENDING" if remaining_functions else ("PASS" if required_functions else "NOT_EXECUTED"),
                    "Funções requeridas comparadas às oferecidas pelos padrões selecionados.", operator="SET_COVERAGE",
                    expected_ids=required_functions, observed_ids=offered_functions,
                    matched_ids=[f for f in required_functions if f in offered_functions], missing_ids=remaining_functions)
        selected_knowledge_ids = unique(
            (kid for item in selected for kid in item.get("selected_knowledge_ids", []))
        )
        selected_criterion_ids = unique(
            (cid for item in selected for cid in item.get("selected_criterion_ids", []))
        )
        selected_articulation_ids = unique(
            (
                articulation_id
                for articulation_id in retrieval["articulation_ids"]
                if set(
                    self.articulations[articulation_id].get(
                        "conhecimento_resultante_ids", []
                    )
                )
                & set(selected_knowledge_ids)
            )
        )
        decision_id = f"D-GERADA-{uuid.uuid4().hex[:10].upper()}"
        if status in {"GERADA", "GERADA_PARCIAL"}:
            orientation = self.compose_transfer_orientation(selected, context)
            justification = f"A consulta recuperou {len(retrieval['direct_knowledge_ids'])} conhecimentos diretamente e acrescentou {len(retrieval['articulated_knowledge_ids'])} por relações documentadas e habilitadas. Esses conhecimentos fundamentaram {len(selected_criterion_ids)} critérios e {len(selected)} componentes da configuração."
        else:
            orientation = "A decisão foi suspensa porque ainda não há informação ou cobertura suficiente para construir uma orientação fundamentada."
            justification = "A MADO não completa lacunas por inferência livre e não oferece uma recomendação genérica de emergência."
        contribution_status = {
            "PAD-VIDEO-PROCESSO": "CONDICIONAL_POR_FUNCAO_E_ACESSIBILIDADE",
            "PAD-JOGO-CONSOLIDACAO-FEEDBACK": "CONDICIONAL_POR_FUNCAO_E_FEEDBACK",
        }
        configuration = []
        for item in selected:
            condition_ids = unique(
                (
                    identifier
                    for match in item.get("matches", [])
                    for identifier in match.get("ids", [])
                )
            )
            support_rows = item.get("selected_support", [])
            criterion_origin_ids = unique(
                (
                    oid
                    for support in support_rows
                    for oid in support.get("selected_origin_ids", [])
                )
            )
            config_articulations = unique(
                (
                    articulation_id
                    for articulation_id in selected_articulation_ids
                    if set(
                        self.articulations[articulation_id].get(
                            "conhecimento_resultante_ids", []
                        )
                    )
                    & set(item.get("selected_knowledge_ids", []))
                )
            )
            configuration.append(
                {
                    "component_id": item["id"],
                    "papel": item["role"],
                    "mode_id": item.get("mode_id"),
                    "modo": self.label(item.get("mode_id")),
                    "funcao": item.get("function", ""),
                    "function_ids": item.get("function_ids", []),
                    "funcoes_decisorias": self.labels(item.get("function_ids", [])),
                    "acao": item["action"],
                    "modal_role_id": item["modal_role_id"],
                    "papel_modal": self.label(item["modal_role_id"]),
                    "responsible_role_id": item["responsible_role_id"],
                    "responsavel": self.label(item["responsible_role_id"]),
                    "resource_ids": item.get(
                        "configured_resource_ids", item.get("selected_resource_ids", [])
                    ),
                    "confirmed_resource_ids": item.get("selected_resource_ids", []),
                    "conditional_resource_ids": [
                        row["id"]
                        for row in item.get("resource_options", [])
                        if row["estado"] == "NAO_CONFIRMADO"
                    ],
                    "proposed_resource_ids": [
                        row["id"]
                        for row in item.get("resource_options", [])
                        if row["estado"] == "PROPOSTO_A_PREPARAR"
                    ],
                    "recursos": self.labels(
                        item.get(
                            "configured_resource_ids",
                            item.get("selected_resource_ids", []),
                        )
                    ),
                    "resource_options": item.get("resource_options", []),
                    "availability_status": item.get(
                        "resource_gate", "CONFIRMADO_DISPONIVEL"
                    ),
                    "condition_ids": condition_ids,
                    "functional_meaning": item.get("functional_meaning", ""),
                    "knowledge_ids": item.get("selected_knowledge_ids", []),
                    "criterion_ids": item.get("selected_criterion_ids", []),
                    "criterion_origin_ids": criterion_origin_ids,
                    "articulation_ids": config_articulations,
                    "conditions": item.get("conditions", []),
                    "alternative": item.get("alternative", ""),
                    "monitoring": item.get("monitoring", ""),
                    "limit": item.get("limit", ""),
                    "contribution_status": contribution_status.get(
                        item["id"], "CONFIGURACAO_MATURA_RC4"
                    ),
                }
            )
        for item, config in zip(selected, configuration):
            config["criterion_support"] = copy.deepcopy(
                item.get("selected_support", [])
            )
        matched_needs = {
            identifier
            for item in selected
            for match in item.get("matches", [])
            if match.get("field") == "necessidades"
            for identifier in match.get("ids", [])
        }
        coverage_notes = [
            f"A necessidade '{self.label(identifier)}' foi registrada, mas a base ainda não documenta sua ligação específica com a configuração selecionada."
            for identifier in context.get("necessidades", [])
            if identifier not in matched_needs
        ]
        coverage_notes += ["Função requerida ainda sem cobertura: " + self.label(f) for f in remaining_functions]
        component_map = {}
        for item in selected:
            for kid in item.get("selected_knowledge_ids", []):
                component_map.setdefault(kid, []).append(item["id"])
        criteria_trace = []
        for cid in selected_criterion_ids:
            criterion = self.criteria[cid]
            situated = [
                {
                    "component_id": item["id"],
                    "knowledge_ids": support["selected_knowledge_ids"],
                    "origin_ids": support["selected_origin_ids"],
                    "justification": support.get("justification", ""),
                }
                for item in selected
                for support in item.get("selected_support", [])
                if support.get("criterion_id") == cid
            ]
            criteria_trace.append(
                {
                    "id": cid,
                    "enunciado": criterion["enunciado"],
                    "situated_support": situated,
                    "fundamentado_por": unique(
                        (kid for row in situated for kid in row["knowledge_ids"])
                    ),
                    "origens_documentais": unique(
                        (oid for row in situated for oid in row["origin_ids"])
                    ),
                    "origens_detalhadas": [
                        {
                            "id": oid,
                            "fonte_id": self.criterion_origins.get(oid, {}).get(
                                "fonte_id", ""
                            ),
                            "trecho_id": self.criterion_origins.get(oid, {}).get(
                                "trecho_id", ""
                            ),
                            "texto": self.criterion_origins.get(oid, {}).get(
                                "texto_item_original", ""
                            ),
                        }
                        for oid in unique(
                            (oid for row in situated for oid in row["origin_ids"])
                        )
                    ],
                    "justificativa": " | ".join(
                        unique((row["justification"] for row in situated))
                    ),
                    "status": "USO_SITUADO_COM_ORIGEM_DOCUMENTAL_RC3",
                }
            )
        decision = {
            "id": decision_id,
            "status": status,
            "orientacao_principal": orientation,
            "justificativa": justification,
            "sintese_pratica": self.build_practical_summary(
                configuration, status, context
            ),
            "configuracao_modal": configuration,
            "resource_ids": unique(
                (
                    resource_id
                    for item in selected
                    for resource_id in item.get("selected_resource_ids", [])
                )
            ),
            "recursos": self.labels(
                unique(
                    (
                        resource_id
                        for item in selected
                        for resource_id in item.get("selected_resource_ids", [])
                    )
                )
            ),
            "conditional_resource_ids": unique(
                (
                    row["id"]
                    for item in selected
                    for row in item.get("resource_options", [])
                    if row["estado"] == "NAO_CONFIRMADO"
                )
            ),
            "proposed_resource_ids": unique(
                (
                    row["id"]
                    for item in selected
                    for row in item.get("resource_options", [])
                    if row["estado"] == "PROPOSTO_A_PREPARAR"
                )
            ),
            "recursos_condicionais": self.labels(
                unique(
                    (
                        resource_id
                        for item in selected
                        for resource_id in item.get("configured_resource_ids", [])
                        if resource_id not in item.get("selected_resource_ids", [])
                    )
                )
            ),
            "condicoes": unique(
                (value for item in selected for value in item.get("conditions", []))
            )
            + context.get("restricoes", []),
            "alternativas": unique(
                (
                    item.get("alternative")
                    for item in selected
                    if item.get("alternative")
                )
            ),
            "gatilhos_de_adaptacao": (
                [
                    "Retirar ou substituir um modo quando ele não acrescentar a função prevista ou não puder ser percebido, operado ou compreendido.",
                    "Reexecutar a consulta se tarefa, recursos, participantes ou condições funcionais forem alterados.",
                    "Suspender a decisão quando faltar recurso essencial sem alternativa funcionalmente equivalente.",
                ]
                if selected
                else []
            ),
            "acompanhamento": unique(
                (item.get("monitoring") for item in selected if item.get("monitoring"))
            ),
            "resultado_esperado": " ".join(
                unique(
                    (
                        item.get("monitoring")
                        for item in selected
                        if item.get("monitoring")
                    )
                )
            ),
            "estatuto_resultado_esperado": "EXPECTATIVA_OBSERVAVEL_NAO_EVIDENCIA_DE_EFICACIA",
            "resultado_observado": "Ainda não observado; deve ser registrado após a aplicação.",
            "informacoes_ausentes": [item["question"] for item in questions]
            + coverage_notes,
            "knowledge_ids": selected_knowledge_ids,
            "criterion_ids": selected_criterion_ids,
            "articulation_ids": selected_articulation_ids,
            "component_ids": [item["id"] for item in selected],
            "limite": "Decisão válida somente para o contexto, as relações confirmadas e a cobertura representada; apoia a escolha e o acompanhamento, mas não demonstra eficácia pedagógica nem constitui orientação universal.",
        }

        for trace in criteria_trace:
            for detail in trace["origens_detalhadas"]:
                origin = self.criterion_origins[detail["id"]]
                for field in (
                    "aviso_publicacao",
                    "localizacao_publica",
                    "estado_publicacao",
                ):
                    if field in origin:
                        detail[field] = origin[field]

        def comparison_payload(items, knowledge_ids):
            covered = unique(
                (
                    function_id
                    for item in items
                    for function_id in item.get("function_ids", [])
                )
            )
            required = context.get("funcoes_requeridas_ids", [])
            return {
                "knowledge_ids": knowledge_ids,
                "component_ids": [item["id"] for item in items],
                "covered_function_ids": covered,
                "covered_functions": self.labels(covered),
                "remaining_function_ids": [
                    identifier for identifier in required if identifier not in covered
                ],
                "modalities": unique(
                    (
                        self.label(item.get("mode_id"))
                        for item in items
                        if item.get("mode_id")
                    )
                ),
                "alternatives": unique(
                    (
                        item.get("alternative")
                        for item in items
                        if item.get("alternative")
                    )
                ),
            }

        comparison = {
            "isolated": comparison_payload(
                isolated_selected, retrieval["direct_knowledge_ids"]
            ),
            "articulated": comparison_payload(selected, retrieval["knowledge_ids"]),
            "added_knowledge_ids": retrieval["articulated_knowledge_ids"],
            "articulation_ids": retrieval["articulation_ids"],
            "interpretation": "A comparação mede cobertura funcional e rastreabilidade. Ela não afirma superioridade pedagógica nem eficácia universal.",
        }
        isolated_component_ids = set(comparison["isolated"]["component_ids"])
        isolated_function_ids = set(comparison["isolated"]["covered_function_ids"])
        isolated_modalities = set(comparison["isolated"]["modalities"])
        isolated_alternatives = set(comparison["isolated"]["alternatives"])
        comparison["added_component_ids"] = [
            identifier
            for identifier in comparison["articulated"]["component_ids"]
            if identifier not in isolated_component_ids
        ]
        comparison["added_function_ids"] = [
            identifier
            for identifier in comparison["articulated"]["covered_function_ids"]
            if identifier not in isolated_function_ids
        ]
        comparison["added_modalities"] = [
            value
            for value in comparison["articulated"]["modalities"]
            if value not in isolated_modalities
        ]
        comparison["added_alternatives"] = [
            value
            for value in comparison["articulated"]["alternatives"]
            if value not in isolated_alternatives
        ]
        de_para = []  # Populated exclusively from the recorded execution below.
        articulations_used = [
            self.articulations[identifier] for identifier in selected_articulation_ids
        ]
        result = {
            "executed_at": now_iso(),
            "version": VERSION,
            "interface_version": UI_VERSION,
            "execution_mode": "LOCAL_DETERMINISTICA_SEM_LLM_SEM_SIMILARIDADE_TEXTUAL",
            "context": self.context_payload(),
            "decision": decision,
            "de_para": de_para,
            "articulation_comparison": comparison,
            "articulations_used": articulations_used,
            "traceability": {
                "criteria": criteria_trace,
                "knowledge": self.trace_knowledge(
                    selected_knowledge_ids, context, component_map
                ),
                "components": [
                    {
                        "id": item["id"],
                        "label": item["label"],
                        "role": item["role"],
                        "matches": item["matches"],
                    }
                    for item in selected
                ],
                "historical_decisions": self.historical_precedents(
                    selected_knowledge_ids
                ),
                "rejected_candidates": rejected,
                "semantic_retrieval": retrieval["rows"],
            },
        }
        session_graph = self.build_decision_graph(result)
        result["traceability"]["excluded_knowledge"] = retrieval["excluded_knowledge"]
        result["traceability"]["conditional_knowledge"] = retrieval[
            "conditional_knowledge"
        ]
        self._finish_execution_evidence(result)
        isolated_by_id = {item["id"]: item for item in isolated_selected}
        comparison["added_configuration_ids"] = [
            c["id"] for c in result["explanation"]["configurations"]
            if c["component_id"] in comparison["added_component_ids"]]
        comparison["evidence_delta"] = []
        for item in selected:
            previous = isolated_by_id.get(item["id"], {})
            def support_tuples(supports):
                return {(s["criterion_id"], k, o) for s in supports
                        for k in s["selected_knowledge_ids"] for o in s["selected_origin_ids"]}
            added_pairs = support_tuples(item.get("selected_support", [])) - support_tuples(previous.get("selected_support", []))
            if not added_pairs and item["id"] in isolated_by_id:
                continue
            explanation_config = next(c for c in result["explanation"]["configurations"] if c["component_id"] == item["id"])
            comparison["evidence_delta"].append({
                "component_id": item["id"], "configuration_id": explanation_config["id"],
                "configuration_added": item["id"] not in isolated_by_id,
                "added_support_pairs": [{"criterion_id": c, "knowledge_id": k, "origin_id": o}
                                        for c, k, o in sorted(added_pairs)],
                "retrieval_witnesses": [w for w in explanation_config["application"]["retrieval_witnesses"]
                                        if w["mode"] == "POR_ARTICULACAO" and any(k == w["knowledge_id"] for _, k, _ in added_pairs)],
                "interpretation": "Diferença de escolha e suporte nesta execução determinística, não evidência de eficácia em uso.",
            })
        result["query_summary"], result["query_results"] = self.run_runtime_queries(
            session_graph, context["id"], decision_id
        )
        result["trace_graph"] = result["explanation"]["graph"]
        result["relevance_delta"] = {
            "added_configuration_count": len(comparison["added_component_ids"]),
            "added_component_ids": comparison["added_component_ids"],
            "added_function_ids": comparison["added_function_ids"],
            "added_modalities": comparison["added_modalities"],
            "conditional_modes": [
                item
                for item in configuration
                if item["contribution_status"].startswith("CONDICIONAL_")
            ],
            "de_para_rows": len(result["de_para"]),
            "interpretation": "A novidade é demonstrada pelo encadeamento entre condições, articulações, funções e configurações, não por trocar palavras de uma prática anterior.",
        }
        self.current["last_result"] = result
        self._record_checks = False
        return result
