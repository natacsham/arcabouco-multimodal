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
import situated_context

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
VERSION = "1.6.0-rc1"
UI_VERSION = "AMADO-web-1.6.0-rc1-semantic1"
REQUESTER_RELATIONS = {
    "self": "Sou eu quem realizará a atividade",
    "support": "Apoio quem realizará a atividade",
    "prepare": "Preparo ou adapto o material ou recurso",
    "seek_guidance": "Busco orientações para conversar com quem conduz ou apoia a atividade",
    "unspecified": "Ainda não sei informar",
}
PRACTICAL_COPY = {
    "PAD-ORGANIZAR-CONTEUDO-PERSISTENTE": {
        "title": "Organize o material em blocos que possam ser revisados",
        "action_sha256": "e98ea6a0f0c762ce245ddfc5654676e62ea15753a3d1d02f626c0b464afcf698",
        "steps": [
            ("Crie blocos curtos, cada um com uma ideia central.", "criar blocos curtos com uma ideia central"),
            ("Identifique a autoria e inclua uma fonte ou exemplo.", "autoria identificada, fonte ou exemplo"),
            ("Reserve um ponto de revisão antes de publicar.", "um ponto explícito de revisão antes de publicar"),
        ],
        "relation": "O texto organiza o que foi dito, desenhado ou mostrado e permite que a informação seja retomada sem depender da memória da fala.",
    },
    "PAD-EXPRESSAO-AUTORAL-FALA-AUDIO": {
        "title": "Grave a explicação e mantenha um texto para revisão",
        "action_sha256": "46032a4425644082484b8bb0e3cf375f9f189b7c45c1987f3994edba8e263e87",
        "steps": [
            ("Grave a explicação em trechos curtos de áudio.", "registrar a explicação em trechos curtos de áudio"),
            ("Junte a cada trecho um resumo em texto que possa ser editado.", "associar uma síntese textual editável"),
            ("Permita que o estudante aprove ou refaça cada trecho.", "permitir que o estudante aprove ou refaça cada trecho"),
        ],
        "relation": "A fala preserva a forma autoral de expressão; o áudio mantém essa contribuição recuperável e o texto curto apoia revisão e correção.",
    },
    "PAD-REPRESENTACAO-VISUAL-EXPLICADA": {
        "title": "Explique o que cada imagem ou desenho comunica",
        "action_sha256": "cab923bfa75942c2b5140dbc121f1317cc082611e2e0db881298e21c64bc312d",
        "steps": [
            ("Escolha ou produza cada imagem e desenho com o estudante.", "selecionar ou produzir cada imagem e desenho com o estudante"),
            ("Registre o que cada representação demonstra.", "registrar o que ela demonstra"),
            ("Acrescente uma descrição em texto ou fala que preserve a informação usada na atividade.", "acrescentar descrição textual ou oral equivalente ao ponto usado na atividade"),
        ],
        "relation": "Imagem e desenho mostram relações visuais; texto ou fala explicam o significado para quem não percebe ou interpreta o visual da mesma forma.",
    },
    "PAD-VIDEO-PROCESSO": {
        "title": "Use um trecho de vídeo com pausa e explicação",
        "action_sha256": "ec98a9048ed087db1d070c48e9e7d21f55a5542cbde35092d21fdc79df4057af",
        "steps": [
            ("Use um trecho curto de vídeo somente para a relação que precisa ser mostrada.", "usar um trecho curto de vídeo somente para a relação previamente escolhida"),
            ("Pause para explicar e ofereça legendas e descrição do conteúdo visual.", "com pausa para explicação, legendas, descrição do conteúdo visual"),
            ("Retome a informação em texto ou fala.", "retomada em texto ou fala"),
        ],
        "relation": "O vídeo apresenta a mudança no tempo; pausas, fala, legenda e descrição preservam o conteúdo e tornam seus pontos principais recuperáveis.",
    },
    "PAD-JOGO-CONSOLIDACAO-FEEDBACK": {
        "title": "Use o jogo para relacionar ideias e explicar as respostas",
        "action_sha256": "0a7dd9a1c15b145104949cdbbd87a21913587511f5aee2f3974f830adceac700",
        "steps": [
            ("Crie poucas situações de ordenar, relacionar ou comparar.", "criar poucas situações de ordenar, relacionar ou comparar"),
            ("Depois de cada resposta, explique o resultado e permita uma nova tentativa.", "após cada resposta, oferecer feedback explicativo, permitir nova tentativa"),
            ("Discuta com a turma as respostas diferentes.", "discutir divergências com a turma"),
        ],
        "relation": "A ação no jogo testa uma relação; o feedback em texto ou fala explica o resultado e orienta a retomada, sem transformar o jogo em recompensa.",
    },
    "PAD-PAPEIS-TURNOS-AUTORIA": {
        "title": "Combine os momentos de participação e de retomada",
        "action_sha256": "fa9497b635ecae487fc2a88d125f0aa515535d0d09cb21773676714ac3af0554",
        "steps": [
            ("Combine quem abre cada bloco e quando os colegas podem perguntar.", "combinar quem abre cada bloco, quando colegas perguntam"),
            ("Combine como a professora sinaliza a passagem para a próxima parte.", "como a professora sinaliza a transição"),
            ("Defina como o estudante registra uma contribuição que ficará para revisão.", "como o estudante registra uma contribuição que ficará para revisão"),
        ],
        "relation": "A fala continua sendo espaço de participação, enquanto o roteiro visível marca turnos, transições e pontos de retomada.",
    },
    "PAD-REVISAO-CONFIRMACAO": {
        "title": "Confira o conteúdo e suas alternativas antes de publicar",
        "action_sha256": "fe70e0e3206fe55ab49180cacdeb8a05c062ee28d739c8de791abef29bd2a698",
        "steps": [
            ("Revise cada bloco com o estudante e teste com pelo menos um colega.", "revisar cada bloco com o estudante, testar com pelo menos um colega"),
            ("Registre o que precisou de explicação.", "registrar o que precisou de explicação"),
            ("Publique somente depois de confirmar o conteúdo e as alternativas.", "publicar somente após confirmação de conteúdo e alternativas"),
        ],
        "relation": "O registro editável mantém o conteúdo disponível para conferência; a revisão com o estudante e a devolutiva de um colega ajudam a identificar o que precisa ser explicado ou ajustado, incluindo as alternativas de acesso.",
    },
    "PAD-ORIENTACAO-AUDIO-RECUPERAVEL": {
        "title": "Permita ouvir e repetir cada orientação",
        "action_sha256": "afedb4cdf5b250beda732553750c8f83bfffbac3d2adb8082438cb8418d2999a",
        "steps": [
            ("Apresente cada orientação em um áudio curto.", "apresentar cada orientação em áudio curto"),
            ("Mantenha um comando acessível para repetir a última mensagem.", "manter um comando acessível para repetir a última mensagem"),
            ("Dê uma confirmação perceptível quando a ação for reconhecida.", "confirmar de forma perceptível quando a ação foi reconhecida"),
        ],
        "relation": "O áudio apresenta a orientação; a repetição permite ouvi-la novamente, e a confirmação informa se a ação foi reconhecida.",
    },
    "PAD-RETORNO-HAPTICO-RUIDO": {
        "title": "Acrescente um aviso por vibração",
        "action_sha256": "9a6e5bfd4376801d633b7a9e7d219ff42f73902d22e484ebb2f8429c1c2c2a66",
        "steps": [
            ("Use um aviso tátil simples e distinguível para sinalizar uma nova orientação.", "usar um padrão tátil simples e distinguível para avisar que há nova orientação"),
            ("Mantenha a mensagem completa em áudio repetível ou texto acessível.", "mantendo o conteúdo disponível em áudio repetível ou texto acessível"),
        ],
        "relation": "A vibração chama a atenção sem depender da escuta; o áudio ou o texto comunica o significado completo do aviso.",
    },
    "PAD-CONTEUDO-WEB-EQUIVALENTE": {
        "title": "Prepare o conteúdo para acesso com leitor de tela",
        "action_sha256": "27b44c7f63f87fdcf3354ae3f30a9e9352f1c0ea0b942adde796eca25a990155",
        "steps": [
            ("A pessoa responsável pela adaptação identifica a função de cada elemento visual.", "o responsável autorizado identifica a função dos elementos visuais"),
            ("Ela produz alternativas em texto que preservem essa informação.", "produz alternativas textuais equivalentes"),
            ("Ela organiza os títulos e as relações na página.", "estrutura títulos e relações na página"),
            ("A pessoa usuária confere a sequência e a compreensão com seu leitor de tela.", "a pessoa usuária verifica a sequência e a compreensão com seu leitor de tela"),
        ],
        "relation": "A organização textual preserva estrutura e relações; a descrição verbaliza o conteúdo visual e o leitor de tela o apresenta por voz e navegação sequencial.",
    },
    "PAD-COMUNICACAO-MULTIFORMATO": {
        "title": "Permita escrever ou ditar e conferir antes de enviar",
        "action_sha256": "dbaa29ab7a5da30716aeb0d54d6fcc2de5e183a40ffb918e51ccc85325e5c6ef",
        "steps": [
            ("A pessoa responsável pela adaptação oferece digitação e voz como entradas alternativas.", "o responsável autorizado integra digitação e voz como entradas alternativas"),
            ("Ela mostra o texto reconhecido antes do envio e oferece leitura em voz e retorno perceptível.", "apresenta o texto reconhecido antes do envio e disponibiliza leitura em voz e retorno perceptível"),
            ("A pessoa usuária revisa, corrige, confirma e decide quando enviar.", "a pessoa usuária revisa, corrige, confirma e decide quando enviar"),
        ],
        "relation": "A voz pode produzir a mensagem, o texto permite revisar e corrigir, e a leitura em voz oferece outra forma de conferir o conteúdo antes de decidir pelo envio.",
    },
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
        from semantic_catalogue import read_semantic_catalogue
        self.data = read_semantic_catalogue(self.graph)
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
        self.functional_matrix = self.data.get("functional_matrix", [])
        self.components = [
            row
            for row in self.data["decision_components"]
            if row.get("active_in_rc4", row.get("active_in_rc3"))
        ]
        self.current = None
        self._last_execution_graph = None
        self._evidence = None
        self._record_checks = False
        self._dialogue_route_ids = None
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
                "label": row.get("label") or row.get("grupo_rotulo") or self.label(row["papel_id"]),
                "grupo_rotulo": row.get("grupo_rotulo", ""),
                "quantidade": row.get("quantidade", 1),
                "parent_group_id": row.get("parent_group_id", ""),
                "group_scope": row.get("group_scope", ""),
                "observacoes": row.get("observacoes", ""),
                "apoios_informados": row.get("apoios_informados", ""),
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
            "requester_relation": c.get("requester_relation", ""),
            "requester_relation_label": REQUESTER_RELATIONS.get(c.get("requester_relation"), ""),
            "requester_relation_status": c.get("requester_relation_status", ""),
            "requester_participation_id": c.get("requester_participation_id", ""),
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
            "function_derivation": copy.deepcopy(c.get("function_derivation", [])),
            "access_requirements": copy.deepcopy(c.get("access_requirements", [])),
            "situated_version": c.get("situated_version", ""),
            "revision": c.get("revision", 0),
            "situations": copy.deepcopy(c.get("situations", [])),
            "assertions": copy.deepcopy(c.get("assertions", [])),
            "active_situation_id": c.get("active_situation_id", ""),
            "question_answers": copy.deepcopy(c.get("question_answers", [])),
            "facts": copy.deepcopy(c.get("facts", {})),
            "situated_facts": copy.deepcopy(c.get("situated_facts", [])),
            "review_changes": copy.deepcopy(c.get("review_changes", [])),
            "unmapped_text": copy.deepcopy(c.get("unmapped_text", [])),
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
        self._last_execution_graph = None
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
            copied["label"] = copied.get("label") or self.label(copied.get("papel_id", "")) or "Participante do exemplo"
            session_participations.append(copied)
        situated_context.from_legacy(context, session_participations)
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
        self._last_execution_graph = None
        self._evidence = None
        self._record_checks = False
        self._dialogue_route_ids = None
        self.current["last_result"] = None

    def clear(self):
        """Discard the current case, not a history entry; no filesystem writes."""
        self._last_execution_graph = None
        return self.start_free_context()

    def inspect_execution(self, format="summary", query_ids=None):
        """Read the last run in RAM; never append it to the knowledge base."""
        if self._last_execution_graph is None:
            raise ValueError("Gere uma orientação para conferir sua execução.")
        from semantic_execution import semantic_execution_summary, query_execution
        if format == "summary":
            return semantic_execution_summary(self._last_execution_graph)
        if format == "queries":
            return query_execution(self._last_execution_graph, self.graph, query_ids=query_ids)
        if format == "turtle":
            return {"format": "text/turtle", "content": self._last_execution_graph.serialize(format="turtle"),
                    "case_storage": False}
        raise ValueError("Formato de consulta não reconhecido.")

    def current_payload(self):
        last_result = copy.deepcopy(self.current.get("last_result"))
        if last_result is not None:
            last_result.pop("query_results", None)
        return {
            "context": self.context_payload(),
            # Internal worker contract: do not remap human labels back to IDs
            # or lose personal declarations when answering a follow-up.
            "participations": copy.deepcopy(self.current.get("participations", [])),
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
        self._last_execution_graph = None
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
                "requester_relation": "",
                "requester_relation_status": "",
                "requester_participation_id": "",
                "impedimentos_verificados": False,
                "premissas_do_exemplo": [],
                "titulo_curto": "Caso informado agora",
                "funcoes_requeridas_ids": [],
                "function_derivation": [],
                "access_requirements": [],
                "natureza": "CASO_INFORMADO_PELA_PESSOA",
                "status": "AGUARDANDO_CARACTERIZACAO",
            }
        )
        self.current["participations"] = []
        context.update(situated_context.fresh_contract())
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
        previous_situated = copy.deepcopy(self.current["context"])
        effective_narrative, _ = situated_context.corrected_text(narrative)
        normalized = normalize_text(effective_narrative)
        context = self.current["context"]
        context["restricoes"] = []
        context["operacao_do_recurso"] = ""
        context["requester_relation"] = ""
        context["requester_relation_status"] = ""
        context["requester_participation_id"] = ""
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
            if identifier == "REC-COMPUTADOR-DATASHOW" and not (
                re.search(r"\bcomputador(?:es)?\b", normalized) and re.search(r"\b(?:projetor|data show|datashow)\b", normalized)
            ):
                # An aggregate cannot be recognized from just one component.
                continue
            public = self.ui_vocab.get("concepts", {}).get(identifier, {})
            aliases = unique(
                public.get("aliases", [])
                + [public.get("label", ""), concept.get("rotulo", "")]
            )
            for alias in aliases:
                token = normalize_text(alias)
                if identifier == "REC-FEEDBACK-ACESSIVEL" and token in {"erro", "confirmacao"}:
                    # An error to correct is not evidence of feedback supplied
                    # by the interface. Keep the explicit feedback/status names.
                    continue
                if field == "ambientes" and token in {"turma", "professor", "professora", "aluno", "estudante", "aula"}:
                    # A participant or group does not establish the location.
                    continue
                matches = list(re.finditer(r"\b" + re.escape(token) + r"\b", normalized)) if len(token) >= 4 else []
                if field == "tarefas":
                    matches = [match for match in matches
                               if not situated_context.negated_action(normalized, match.start())]
                if matches:
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
                "\\b(acessar|ler|acompanhar|compreender|consultar).{0,45}\\b(conteudo|material|pagina|video|aula digital)\\b",
                "tarefas",
                "TAR-ACESSAR-COMPREENDER-CONTEUDO-DIGITAL",
            ),
            (
                "\\b(ensinar|explicar|apresentar|passar|ministrar).{0,45}\\b(assunto|conteudo|tema|material|aula|aulas)\\b|\\bconteudo a ser ministrado\\b",
                "tarefas",
                "TAR-COMUNICAR-CONTEUDO-1545B38",
            ),
            (
                "\\b(criar|produzir|construir|preparar|escrever|redigir|ditar).{0,40}\\b(recurso|conteudo|apresentacao|pagina|video|jogo|texto|mensagem|resposta|rascunho|registro|relatorio|documento)\\b",
                "tarefas",
                "TAR-PRODUZIR-CONTEUDO-MULTIMODAL",
            ),
            (
                "\\b(organizar|estruturar).{0,30}\\b(conteudo|ideias|informacao)\\b",
                "tarefas",
                "TAR-ORGANIZAR-CONTEUDO-DIGITAL",
            ),
            (
                "\\b(revisar|confirmar|corrigir)\\b",
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
                "\\b(consultar|buscar|pesquisar|selecionar|reservar)\\b.{0,45}\\b(catalogo digital|sistema|aplicativo|plataforma|servico digital)\\b",
                "tarefas",
                "TAR-OPERAR-SISTEMA",
            ),
            (
                "\\b(consulta individual|consultar depois|rever o material|rever o conteudo)\\b",
                "tarefas",
                "TAR-ACESSAR-COMPREENDER-CONTEUDO-DIGITAL",
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
                "\\b(sala de aula)\\b",
                "ambientes",
                "AMB-SALA-DE-AULA",
            ),
            (
                "\\b(?:computador(?:es)?.{0,50}(?:projetor|data show|datashow)|(?:projetor|data show|datashow).{0,50}computador(?:es)?)\\b",
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
            matches = re.finditer(pattern, normalized)
            match = next((candidate for candidate in matches
                          if field != "tarefas" or (
                              not situated_context.negated_action(normalized, candidate.start())
                              and not (identifier == "TAR-OPERAR-SISTEMA" and
                                       situated_context.completion_control(normalized, candidate.start(), candidate.end())))), None)
            if (match and field == "necessidades"
                    and identifier == "NEC-ENTRADA-ALTERNATIVA"
                    and re.search(
                        r"\b(?:consigo|consegue|conseguem|posso|pode|podem)\s+$",
                        normalized[max(0, match.start() - 30):match.start()])
                    and not situated_context.negated_action(normalized, match.start())):
                match = None
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
        if not re.search(r"\b(?:revisar|revisao|confirmar|confirmacao|corrigir)\b", normalized):
            detected["tarefas"] = [value for value in detected["tarefas"] if value != "TAR-REVISAR-E-CONFIRMAR"]
        if "TAR-REVISAR-E-CONFIRMAR" in detected["tarefas"]:
            duplicate = [
                item for item in evidence
                if item.get("field") == "necessidades"
                and item.get("concept_id") == "NEC-REVISAO-E-CONFIRMACAO"
                and normalize_text(item.get("matched_text")) in {"revisar", "confirmar"}
            ]
            if duplicate:
                evidence = [item for item in evidence if item not in duplicate]
                detected["necessidades"] = [
                    value for value in detected["necessidades"]
                    if value != "NEC-REVISAO-E-CONFIRMACAO"
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
                    "\\b(objetiv|precis|deve|esper|quer|para que)\\w*\\b",
                    normalize_text(sentence),
                )
            ),
            "",
        )
        context["objetivo"] = objective_sentence
        roles = []
        role_cues = [
            ("PAPEL-ESTUDANTE", "\\b(estudantes?|alunos?|alunas?)\\b"),
            ("PAPEL-PROFESSORA", "\\b(professor(?:a|es|as)?|docentes?)\\b"),
            ("PAPEL-TURMA", "\\b(turma|colegas)\\b"),
            ("PAPEL-PESSOA-APOIADA", "\\b(pessoas?|usuarios?|usuarias?|participantes?|adultos?|adultas?)\\b"),
            ("PAPEL-MEDIADOR", "\\b(mediador(?:a|es|as)?|facilitador(?:a|es|as)?)\\b"),
            (
                "PAPEL-RESPONSAVEL-ADAPTACAO",
                "\\b(responsavel pela adaptacao|responsavel por adaptar|pessoa responsavel por adaptar)\\b",
            ),
        ]
        for role_id, pattern in role_cues:
            role_matches = [match for match in re.finditer(pattern, normalized)
                            if not self._negated_access_signal(normalized, match.start())
                            and not re.search(r"\bsem (?:outras? |outros? )?$", normalized[max(0, match.start() - 25):match.start()])
                            and not re.search(r"\bnao (?:sou|somos)\s+$", normalized[max(0, match.start() - 25):match.start()])]
            if role_matches:
                plural = next((match for match in role_matches
                               if match.group(0).endswith("s") or match.group(0) == "turma"), None)
                group_info = {}
                if plural:
                    count_match = re.search(r"\b(\d+|um|uma|dois|duas|tres|quatro)\s+$",
                                            normalized[:plural.start()])
                    count = count_match.group(1) if count_match else None
                    quantity = (int(count) if count and count.isdigit()
                                else {"um": 1, "uma": 1, "dois": 2, "duas": 2, "tres": 3, "quatro": 4}.get(count))
                    group_label = {"PAPEL-ESTUDANTE": "Estudantes", "PAPEL-PROFESSORA": "Docentes",
                                   "PAPEL-PESSOA-APOIADA": "Pessoas apoiadas na interação",
                                   "PAPEL-MEDIADOR": "Pessoas que fazem a mediação",
                                   "PAPEL-TURMA": "Turma ou colegas"}.get(role_id, plural.group(0))
                    group_info = {"label": f"{group_label} ({quantity if quantity is not None else 'quantidade não informada'})",
                                  "grupo_rotulo": plural.group(0), "quantidade": quantity}
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
                        **group_info,
                    }
                )
        self.current["participations"] = roles
        # A reported diagnosis describes a group; it never supplies its
        # communication route, preferred mode or assistive technology.
        groups = [match for match in re.finditer(r"\b(?:(\d+|um|uma|dois|duas|tres|quatro)\s+)?(?:alunos?\s+|alunas?\s+|estudantes?\s+|pessoas?\s+)?(?:(?:e|sao|tem|possuem)\s+)?(surdos?|surdas?|cegos?|cegas?|(?:com\s+)?baixa visao)\b", normalized)
                  if not self._negated_access_signal(normalized, match.start(2))]
        if groups:
            roles = [row for row in roles if row["papel_id"] not in {"PAPEL-ESTUDANTE", "PAPEL-PESSOA-APOIADA"}]
            quantities = {"um": 1, "uma": 1, "dois": 2, "duas": 2, "tres": 3, "quatro": 4}
            for match in groups:
                count, description = match.groups()
                plural = description.endswith("s") or bool(re.search(r"\b(alunos|alunas|estudantes|pessoas)\b", match.group(0)))
                quantity = int(count) if count and count.isdigit() else quantities.get(count, None if plural else 1)
                student = bool(re.search(r"\b(alunos?|alunas?|estudantes?|turma)\b", normalized))
                label = (f"{quantity} {'estudante(s)' if student else 'pessoa(s)'}: {description} informado no relato"
                         if quantity is not None else
                         f"{'Estudantes' if student else 'Pessoas'}: {description} (quantidade não informada)")
                roles.append({"id": f"PART-CASO-{len(roles)+1:02d}-{uuid.uuid4().hex[:6].upper()}",
                              "contexto_id": context["id"], "papel_id": "PAPEL-ESTUDANTE" if student else "PAPEL-PESSOA-APOIADA",
                              "label": label, "grupo_rotulo": description, "quantidade": quantity,
                              "reported_condition": {"text": description, "start": match.start(), "end": match.end()},
                              "caracteristica_ids": [],
                              "tarefa_ids": copy.deepcopy(context["tarefas"]),
                              "modalidade_ids": [], "recurso_operado_ids": [],
                              "objetivo_participacao": match.group(0), "status_evidencia": "IDENTIFICADO_PARA_CONFIRMACAO"})
            self.current["participations"] = roles
            # An aggregate alias match cannot establish who has the condition.
            context["caracteristicas_pessoa"] = []
        # The requester is not automatically the supported person or whoever
        # holds a profession mentioned in the narrative. These are candidates
        # for confirmation, not abilities or authorization to adapt a resource.
        requester_cues = (
            ("seek_guidance", r"\b(?:o que (?:eu )?posso|quero|preciso)\s+(?:falar|dizer|orientar|conversar)\b.{0,65}\b(?:professor|professora|docente|mediador|mediadora|responsavel)\b"),
            ("prepare", r"\b(?:eu (?:vou|preciso|quero|posso)|quero|preciso|posso)\s+(?:preparar|adaptar|ajustar|editar)\b.{0,50}\b(?:material|conteudo|recurso|apresentacao|instrucoes|texto|video)\b"),
            ("support", r"\b(?:eu apoio|pessoa que (?:eu )?apoio|quero (?:ajudar|apoiar)|preciso (?:ajudar|apoiar))\b"),
            ("self", r"\b(?:para (?:meu uso|mim)|sou eu quem (?:vai|precisa)|eu mesmo preciso|eu mesma preciso|(?:eu )?(?:preciso|quero|vou) (?:acessar|usar|utilizar|preencher|enviar|ler|consultar|navegar|operar|produzir|escrever|redigir|ditar|revisar|corrigir))\b"),
        )
        for relation, pattern in requester_cues:
            match = next((candidate for candidate in re.finditer(pattern, normalized)
                          if not situated_context.negated_action(normalized, candidate.start())), None)
            if match:
                context["requester_relation"] = relation
                context["requester_relation_status"] = "IDENTIFICADO_PARA_CONFIRMACAO"
                evidence.append({"field": "requester_relation", "value": relation,
                                 "label": REQUESTER_RELATIONS[relation], "matched_text": match.group(0),
                                 "status": "IDENTIFICADO_PARA_CONFIRMACAO"})
                break
        # Identify who speaks only from an explicit self-description. The
        # profession is not a substitute for who uses or prepares the resource.
        self_role_patterns = {
            "PAPEL-MEDIADOR": r"\bsou (?:(?:um|uma) )?(?:mediador[ao]?|facilitador[ao]?)\b",
            "PAPEL-PROFESSORA": r"\bsou (?:(?:um|uma) )?(?:professor[ao]?|docente)\b",
        }
        for role_id, pattern in self_role_patterns.items():
            if re.search(pattern, normalized):
                matches = [p for p in roles if p.get("papel_id") == role_id]
                if len(matches) == 1:
                    context["requester_participation_id"] = matches[0]["id"]
        if context.get("requester_relation") == "prepare" and not context.get("requester_participation_id"):
            person = situated_context._person(context, "PAPEL-RESPONSAVEL-ADAPTACAO", "Quem relata e prepara o material", "requester-preparer")
            roles.append(person)
            context["requester_participation_id"] = person["id"]
        situated_context.build(context, roles, narrative, self.concepts, evidence, previous_situated)
        self.current["participations"] = roles
        self.derive_access_requirements(effective_narrative)
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
        if "requester_relation" in body:
            relation = body["requester_relation"]
            if not isinstance(relation, str) or relation not in {"", *REQUESTER_RELATIONS}:
                raise ValueError("Relação de quem solicita não reconhecida.")
            context["requester_relation"] = relation
            context["requester_relation_status"] = "INFORMADO_NA_SESSAO" if relation else ""
        if "requester_participation_id" in body:
            if not isinstance(body["requester_participation_id"], str):
                raise ValueError("O vínculo de quem solicita deve identificar uma participação.")
            context["requester_participation_id"] = body["requester_participation_id"].strip()
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
            if not isinstance(body["participations"], list):
                raise ValueError("As participações devem formar uma lista.")
            rows = []
            for index, incoming in enumerate(body.get("participations") or [], 1):
                role_id = incoming.get("papel_id")
                if role_id and role_id not in self.concepts:
                    raise ValueError(f"Papel não reconhecido: {role_id}")
                for field, expected_type in (("caracteristica_ids", "CARACTERISTICA_PESSOA"), ("tarefa_ids", "TAREFA"),
                                             ("modalidade_ids", "MODALIDADE"), ("recurso_operado_ids", "RECURSO_DISPONIVEL")):
                    values = incoming.get(field, [])
                    if not isinstance(values, list) or any(self.concepts.get(value, {}).get("tipo") != expected_type for value in values):
                        raise ValueError("Condição pessoal não reconhecida ou de tipo incorreto: " + field)
                quantity = incoming.get("quantidade", 1)
                unknown_group_size = quantity is None and bool(str(incoming.get("grupo_rotulo", "")).strip())
                if not unknown_group_size and (isinstance(quantity, bool) or not isinstance(quantity, int) or quantity < 1):
                    raise ValueError("A quantidade de participantes precisa ser um inteiro positivo.")
                rows.append(
                    {
                        "id": incoming.get("id")
                        or f"PART-CASO-{index:02d}-{uuid.uuid4().hex[:6].upper()}",
                        "contexto_id": context["id"],
                        "papel_id": role_id,
                        "label": str(incoming.get("label", "")).strip(),
                        "grupo_rotulo": str(incoming.get("grupo_rotulo", "")).strip(),
                        "quantidade": quantity,
                        "parent_group_id": str(incoming.get("parent_group_id", "")),
                        "group_scope": str(incoming.get("group_scope", "")),
                        "observacoes": str(incoming.get("observacoes", "")).strip(),
                        "apoios_informados": str(incoming.get("apoios_informados", "")).strip(),
                        "reported_condition": copy.deepcopy(next((row.get("reported_condition", {}) for row in previous_participations
                                                                   if row["id"] == incoming.get("id")), {})),
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
        elif "caracteristicas_pessoa" in body and len([row for row in participations if row.get("papel_id") in {"PAPEL-ESTUDANTE", "PAPEL-PESSOA-APOIADA"}]) <= 1:
            for row in participations:
                if row.get("papel_id") in {"PAPEL-ESTUDANTE", "PAPEL-PESSOA-APOIADA"}:
                    row["caracteristica_ids"] = copy.deepcopy(
                        context.get("caracteristicas_pessoa", [])
                    )
                    row["status_evidencia"] = "IDENTIFICADO_PARA_CONFIRMACAO"
                    break
        requester_id = context.get("requester_participation_id", "")
        if requester_id and requester_id not in {row["id"] for row in participations}:
            if "requester_participation_id" in body:
                raise ValueError("Quem solicita deve ser vinculado a uma participação existente.")
            # Removing a participant also removes its optional requester link;
            # the relation (support/preparation/etc.) remains independent.
            context["requester_participation_id"] = ""
        if "participations" in body:
            participant_ids = {row["id"] for row in participations}
            old_requirements = context.get("access_requirements", [])
            retained_requirements = [row for row in old_requirements
                                     if not row.get("participant_id") or row["participant_id"] in participant_ids]
            removed_requirements = [row for row in old_requirements if row not in retained_requirements]
            if removed_requirements:
                removed_needs = {nid for row in removed_requirements for nid in row.get("requirement_ids", [])}
                retained_needs = {nid for row in retained_requirements for nid in row.get("requirement_ids", [])}
                explicit_needs = {row.get("concept_id") for row in (self.current.get("narrative_interpretation") or {}).get("evidence", [])
                                  if row.get("field") == "necessidades"}
                orphan_needs = removed_needs - retained_needs - explicit_needs
                context["necessidades"] = [nid for nid in context.get("necessidades", []) if nid not in orphan_needs]
                context["access_requirements"] = retained_requirements
        for row in participations:
            for participant_field, context_field in (
                ("tarefa_ids", "tarefas"),
                ("modalidade_ids", "modalidades_disponiveis"),
                ("recurso_operado_ids", "recursos_disponiveis"),
            ):
                if participant_field == "recurso_operado_ids":
                    # A learned way of operating a device is not its current
                    # availability. Removing/blocking equipment does not erase
                    # that capability or reintroduce the equipment as available.
                    continue
                if "participations" in body and participant_field != "recurso_operado_ids":
                    continue
                if (
                    context_field in body
                    or (
                        participant_field == "recurso_operado_ids"
                        and any((f in body for f in resource_fields))
                    )
                ):
                    before = row.get(participant_field, [])
                    row[participant_field] = [identifier for identifier in before
                                              if (identifier not in context.get("recursos_impedidos", [])
                                                  if participant_field == "recurso_operado_ids" and "participations" in body
                                                  else identifier in context.get(context_field, []))]
                    if before != row[participant_field]:
                        row["status_evidencia"] = "IDENTIFICADO_PARA_CONFIRMACAO"
        situated_context.sync_legacy_edits(context, participations, body, previous_context)
        situated_context.review(context, participations, body, self.concepts)
        for left_index, left in enumerate(resource_fields):
            for right in resource_fields[left_index + 1:]:
                if set(context.get(left, [])) & set(context.get(right, [])):
                    raise ValueError("Um recurso não pode estar disponível, impedido e proposto ao mesmo tempo.")
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
        if body.get("assertion_changes") or body.get("question_answers"):
            self.derive_access_requirements("", observations_only=True)
        context["informacoes_ausentes"] = [
            item["question"] for item in self.missing_questions()
        ]
        return self.current_payload()

    @staticmethod
    def _negated_access_signal(text, start):
        # Restrict negation to the local clause, not another person's statement.
        prefix = text[max(0, start - 45):start]
        return bool(re.search(
            r"\b(?:nao (?:e|eh|sao|esta|estao|tem|tenho|temos|possui|ha|existe|existem)|sem|nenhum|nenhuma)\s*"
            r"(?:(?:um|uma|dois|duas|tres|quatro|qualquer|nenhum|nenhuma|\d+)\s+)?"
            r"(?:(?:alunos?|alunas?|estudantes?|pessoas?|usuarios?|usuarias?)\s+)?$", prefix))

    def derive_access_requirements(self, narrative, observations_only=False):
        """Apply the existing curated functional matrix, never a diagnosis->ability rule.

        Only design needs are projected into the context. Each inference keeps
        its documentary witness and participant scope; no mode, device, language
        or personal competence is filled by this operation.
        """
        context = self.current["context"]
        text = normalize_text(narrative)
        people = [row for row in self.current.get("participations", [])
                  if row.get("papel_id") in {"PAPEL-ESTUDANTE", "PAPEL-PESSOA-APOIADA"}]
        previous_derived_needs = {n for row in context.get("access_requirements", []) for n in row.get("requirement_ids", [])}
        requirements = ([copy.deepcopy(row) for row in context.get("access_requirements", []) if not row.get("assertion_ids")]
                        if observations_only else [])
        for matrix in situated_context.expanded_matrices(self.functional_matrix):
            inference_contract = matrix.get("inference_contract", {})
            if inference_contract.get("eligibility") == "NOT_ELIGIBLE":
                continue
            source_ids = [sid for sid in matrix.get("fonte_ids", []) if sid in self.sources]
            excerpt_ids = [tid for tid in matrix.get("trecho_ids", []) if tid in self.excerpts]
            if inference_contract.get("support"):
                source_ids = unique(row["source_id"] for row in inference_contract["support"] if row.get("source_id") in self.sources)
                excerpt_ids = unique(row["excerpt_id"] for row in inference_contract["support"] if row.get("excerpt_id") in self.excerpts)
            need_ids = [nid for nid in matrix.get("requisito_ids", [])
                        if self.concepts.get(nid, {}).get("tipo") == "NECESSIDADE"]
            if not source_ids or not excerpt_ids or not need_ids or matrix.get("estado") not in {
                "CONFERIDO_RC3", "CONFERIDO_NO_CASO_RC3", "RECONSTRUIDO_CONFERIDO_RC3", "CONFERIDO_NA_SECAO_ORIGINAL"
            }:
                continue
            observed = {}
            for signal in matrix.get("sinais_relato", []):
                token = normalize_text(signal)
                if not token:
                    continue
                for match in re.finditer(situated_context.functional_signal_pattern(token), text):
                    if any(a.get("kind") == "functional_observation" and a.get("state") in situated_context.ACTIVE_STATES
                           and re.search(situated_context.functional_signal_pattern(token), normalize_text(a.get("value", "")))
                           for a in context.get("assertions", [])):
                        continue
                    candidates = [row for row in people if row.get("reported_condition")
                                  and row["reported_condition"].get("start", -1) <= match.start() < row["reported_condition"].get("end", -1)]
                    person = candidates[0] if len(candidates) == 1 else (people[0] if len(people) == 1 else None)
                    key = (person["id"] if person else "", "")
                    record = observed.setdefault(key, {"person": person, "positive": [], "negative": []})
                    record["negative" if self._negated_access_signal(text, match.start()) else "positive"].append(match.group(0))
                    if person and not self._negated_access_signal(text, match.start()):
                        condition = next((a for a in context.get("assertions", [])
                                          if a.get("subject_id") == person["id"] and a.get("kind") == "reported_condition"
                                          and a.get("state") in situated_context.ACTIVE_STATES
                                          and re.search(situated_context.functional_signal_pattern(token), normalize_text(a.get("value", "")))), None)
                        if condition is not None:
                            record.setdefault("assertion_ids", []).append(condition["id"])
                        else:
                            scopes = [s for s in context.get("situations", []) if person["id"] in s.get("participant_ids", [])]
                            scope = next((s for s in scopes if s["id"] == context.get("active_situation_id")), scopes[0] if len(scopes) == 1 else None)
                            if scope:
                                clauses = [part.strip() for part in re.split(r"(?<=[.!?;])\s+", narrative)
                                           if re.search(situated_context.functional_signal_pattern(token), normalize_text(part))]
                                source = clauses[0] if len(clauses) == 1 else match.group(0)
                                assertion = situated_context._assert(context, person["id"], scope["id"], "functional_observation", source, source)
                                record.setdefault("assertion_ids", []).append(assertion["id"])
            for assertion in context.get("assertions", []):
                allowed_kinds = {"functional_observation"}
                if inference_contract.get("trigger_kind") == "FUNCTIONAL_OBSERVATION_OR_REPORTED_ACCESS_CONDITION":
                    allowed_kinds.add("reported_condition")
                if assertion.get("kind") not in allowed_kinds or assertion.get("state") not in situated_context.ACTIVE_STATES:
                    continue
                if any(assertion["id"] in record.get("assertion_ids", []) for record in observed.values()):
                    continue
                observation = normalize_text(assertion.get("value", ""))
                for signal in matrix.get("sinais_relato", []):
                    token = normalize_text(signal)
                    if not token:
                        continue
                    for match in re.finditer(situated_context.functional_signal_pattern(token), observation):
                        person = next((row for row in people if row["id"] == assertion["subject_id"]), None)
                        key = (person["id"] if person else "", assertion.get("situation_id", ""))
                        record = observed.setdefault(key, {"person": person, "positive": [], "negative": [], "assertion_ids": []})
                        record.setdefault("assertion_ids", []).append(assertion["id"])
                        record["negative" if self._negated_access_signal(observation, match.start()) else "positive"].append(match.group(0))
            for (participant_id, situation_id), observed_row in observed.items():
                if not observed_row["positive"]:
                    continue
                conflict = bool(observed_row["negative"])
                requirements.append({
                    "matrix_id": matrix["id"], "participant_id": participant_id,
                    "participant_label": observed_row["person"].get("label", "") if observed_row["person"] else "",
                    "trigger": unique(observed_row["positive"]), "matched_text": "; ".join(unique(observed_row["positive"])),
                    "description": matrix.get("descricao_simples", ""),
                    "requirement_ids": need_ids, "requirement_labels": self.labels(need_ids),
                    "function_ids": [fid for fid in matrix.get("funcao_ids", []) if fid in self.concepts],
                    "knowledge_ids": [kid for kid in matrix.get("knowledge_ids", []) if kid in self.knowledge],
                    "source_ids": source_ids, "excerpt_ids": excerpt_ids,
                    "conditions": matrix.get("condicoes", ""), "limit": matrix.get("contraindicacoes", ""),
                    "status": "CONFLITO_A_CONFIRMAR" if conflict else "DERIVADO_DA_BASE_PARA_CONFIRMACAO",
                    "capabilities_inferred": False,
                    "scope": "PARTICIPANTE" if participant_id else "RELATO_SEM_ATRIBUICAO_INDIVIDUAL",
                    "situation_ids": [situation_id] if situation_id else [s["id"] for s in context.get("situations", [])
                                      if participant_id and participant_id in s.get("participant_ids", [])],
                    "assertion_ids": unique(observed_row.get("assertion_ids", [])),
                    "trigger_group_id": matrix.get("trigger_group_id", ""),
                    "inference_contract": copy.deepcopy(inference_contract),
                    "eligibility": inference_contract.get("eligibility", "LEGACY_DOCUMENTED_REQUIREMENT"),
                })
        context["access_requirements"] = requirements
        retained = {nid for row in requirements if row["status"] != "CONFLITO_A_CONFIRMAR" for nid in row["requirement_ids"]}
        explicit = {a["value"] for a in context.get("assertions", []) if a["kind"] == "need" and a["state"] in situated_context.ACTIVE_STATES}
        context["necessidades"] = unique([nid for nid in context.get("necessidades", [])
            if nid not in previous_derived_needs or nid in retained or nid in explicit] + sorted(retained))

    def _task_components(self, context):
        """Existing patterns whose task requirement has a hierarchy witness."""
        return [component for component in self.components
                if self.intersects(context, "tarefas", component.get("requires_all", {}).get("tarefas", []))]

    def _operational_task_options(self, context):
        # This is a question, not a conversion of the person's intention.
        related = {kid for kid, knowledge in self.knowledge.items()
                   if self.intersects(context, "tarefas", knowledge.get("aplicabilidade", {}).get("tarefas", []))}
        components = [component for component in self.components
                      if related & set(component.get("knowledge_ids", []))]
        return unique(task for component in components
                      for task in component.get("requires_all", {}).get("tarefas", []))

    def _dialogue_routes(self, context):
        """Plan questions for viable existing routes, not every pattern's fields.

        This ranking controls clarification effort only. Generation independently
        verifies all applicable patterns and retains its documentary gates.
        """
        blocked = set(context.get("recursos_impedidos", []))
        available = set(self.available_context_values(context, "recursos_disponiveis"))
        role_ids = {row.get("papel_id") for row in self.current.get("participations", [])}
        if "PAPEL-ESTUDANTE" in role_ids:
            role_ids.add("PAPEL-PESSOA-APOIADA")
        candidates = []
        for component in self._task_components(context):
            # Do not turn a pattern's historical school roles into facts the
            # requester is pushed to adopt. Generic support/adaptation roles
            # may still be clarified; school roles must already be reported.
            school_roles = {"PAPEL-PROFESSORA", "PAPEL-ESTUDANTE", "PAPEL-COLEGAS", "PAPEL-TURMA"}
            if set(component.get("required_role_ids", [])) & (school_roles - role_ids):
                continue
            if not self._access_requirement_scope_matches(component, context):
                continue
            required = set(component.get("required_resource_ids", []))
            if blocked & (required | set(component.get("proposed_resource_ids", []))):
                continue
            resource_groups = component.get("required_any_resource_groups", []) or ([] if required else [component.get("resource_ids", [])])
            if any(group and set(group) <= blocked for group in resource_groups):
                continue
            groups = component.get("requires_any_groups") or ([component["requires_any"]] if component.get("requires_any") else [])
            # A possible resource cannot manufacture the need for video/game etc.
            if any(not any(self.intersects(context, row["field"], row.get("ids", [])) for row in group) for group in groups):
                continue
            mismatched_function = any(field in {"barreiras", "necessidades", "caracteristicas_pessoa"}
                                      and not self.intersects(context, field, ids)
                                      for field, ids in component.get("requires_all", {}).items())
            if mismatched_function:
                continue
            unknown = len(required - available)
            unknown += sum(bool(group) and not set(group) & available for group in resource_groups)
            unknown += len(set(component.get("required_role_ids", [])) - role_ids)
            unknown += sum(not self.intersects(context, field, ids) for field, ids in component.get("requires_all", {}).items()
                           if field != "tarefas")
            candidates.append((unknown, component))
        candidates.sort(key=lambda item: (item[0], item[1].get("role") != "principal", item[1]["id"]))
        required_functions = set(context.get("funcoes_requeridas_ids", []))
        if not candidates:
            return []
        if not required_functions:
            return [next((item[1] for item in candidates if item[1].get("role") == "principal"), candidates[0][1])]
        selected, covered = [], set()
        for _, component in candidates:
            offered = set(component.get("function_ids", []))
            if offered & (required_functions - covered):
                selected.append(component)
                covered.update(offered)
        return selected or [candidates[0][1]]

    @staticmethod
    def _access_requirement_scope_matches(component, context):
        requirements = [row for row in context.get("access_requirements", []) if row.get("status") != "CONFLITO_A_CONFIRMAR"]
        allowed = component.get("access_requirement_matrix_ids", [])
        return not requirements or not allowed or bool(set(allowed) & {row["matrix_id"] for row in requirements})

    def _free_missing_questions(self):
        context = self.current["context"]
        self.derive_required_functions()
        tasks = self.labels(context.get("tarefas", []))
        activity = tasks[0] if tasks else "o desafio que você descreveu"
        materials = self.labels(context.get("recursos_digitais", []))
        environments = self.labels(context.get("ambientes", []))
        situation = " · ".join([activity, *materials, *environments])
        routes = self._dialogue_routes(context)
        component_ids = [row["id"] for row in routes]
        questions = []

        def add(field, label, reason, *, options=None, required=False, priority=50, participant=None, **extra):
            question = {"field": field, "question": label, "label": label, "context_label": situation,
                        "reason": reason, "required": required, "priority": priority,
                        "candidate_component_ids": component_ids, **extra}
            if options is not None:
                question["concept_ids"] = unique(options)
            if participant:
                question.update(participant_id=participant["id"], participant_label=participant.get("label") or self.label(participant["papel_id"]))
            questions.append(question)

        role_ids = {row.get("papel_id") for row in self.current.get("participations", [])}
        narrated_mediation = re.search(r"\b(?:ensinar|treinar|orientar|mediar)\b.{0,60}\b(?:pessoas?|alunos?|estudantes?|grupo|turma)\b",
                                      normalize_text(context.get("descricao_do_contexto", "")))
        unassigned_preparation = any("PAPEL-RESPONSAVEL-ADAPTACAO" in component.get("required_role_ids", [])
                                    for component in routes) and "PAPEL-RESPONSAVEL-ADAPTACAO" not in role_ids
        if not context.get("requester_relation") and (narrated_mediation or unassigned_preparation):
            add("requester_relation", "Como você participa desse desafio?",
                "Isso distingue o que você poderá fazer do que precisa combinar com quem realiza ou prepara a atividade.",
                type="single", priority=-10, decision_relevant=False)
            questions[-1]["options"] = [{"id": key, "label": value} for key, value in REQUESTER_RELATIONS.items()]
        if not context.get("tarefas"):
            task_question = (f"O que as pessoas precisam fazer com {materials[0][:1].lower() + materials[0][1:]}?"
                             if materials else "Qual atividade precisa ser acessível no desafio que você descreveu?")
            add("tarefas", task_question,
                "A atividade determina quais conhecimentos da base podem ser aplicados.", required=True, priority=0)
            if "RED-FORMULARIO" in context.get("recursos_digitais", []):
                # Product recognition is not an answer. Ask about the intended
                # action using existing task concepts; never substitute reading
                # for creating, filling in or reviewing a form.
                task_choices = [
                    ("TAR-OPERAR-SISTEMA", "Preencher e enviar respostas"),
                    ("TAR-PREPARAR-ADAPTAR-CONTEUDO-5107638", "Criar ou adaptar o formulário"),
                    ("TAR-ACESSAR-COMPREENDER-CONTEUDO-DIGITAL", "Ler e compreender perguntas e instruções"),
                    ("TAR-REVISAR-E-CONFIRMAR", "Revisar respostas antes de enviar"),
                ]
                questions[-1].update(type="single", concept_ids=[identifier for identifier, _ in task_choices],
                                     options=[{"id": identifier, "label": label} for identifier, label in task_choices])
            return questions
        instructional = next((s for s in context.get("situations", []) if s.get("kind") == "instruction"), None)
        if not self._task_components(context) and not instructional:
            options = self._operational_task_options(context)
            if options:
                add("tarefas", "No desafio que você descreveu, o que precisa ficar acessível?",
                    "Precisamos distinguir a ação digital do assunto do conteúdo.", options=options,
                    type="single", required=True, priority=0)
                return questions
        if not str(context.get("objetivo", "")).strip():
            add("objetivo", f"Ao {activity[:1].lower() + activity[1:]}, o que precisa ser possível fazer?",
                "O objetivo informado ajuda a conferir se a orientação responde ao desafio.", type="text", priority=5)
        known_observation = any(a.get("kind") == "functional_observation" and a.get("state") in situated_context.ACTIVE_STATES
                                for a in context.get("assertions", []))
        if not context.get("barreiras") and not context.get("necessidades") and not known_observation:
            activity_target = materials[0][:1].lower() + materials[0][1:] if materials else activity[:1].lower() + activity[1:]
            add("barreira_ou_necessidade", f"Que dificuldade de acesso ou uso aparece ao lidar com {activity_target}?",
                "A dificuldade seleciona os apoios pertinentes; não é uma avaliação da pessoa.", required=True, priority=10)
        if not routes:
            if instructional and not context.get("recursos_digitais"):
                add("recursos_digitais", "Na explicação para a turma, que material digital você pretende usar ou preparar?",
                    "Isso esclarece o formato pretendido; não confirma que equipamentos, conexão ou material já estejam disponíveis.",
                    options=[identifier for identifier in ("RED-APRESENTACAO", "RED-AUDIO", "RED-VIDEO", "RED-PAGINA-WEB", "RED-MENSAGENS") if identifier in self.concepts],
                    priority=15)
            return questions
        # A relevant physical/online environment is clarified before equipment,
        # not asked again merely because a pattern supplies more location IDs.
        if not context.get("ambientes"):
            environment_options = unique(identifier for component in routes
                for identifier in component.get("requires_all", {}).get("ambientes", []))
            if environment_options:
                add("ambientes", "Onde essa atividade será realizada?",
                    "O local pode mudar quais formas de acesso e recursos são viáveis.",
                    options=environment_options, priority=12)
        if not context.get("recursos_digitais"):
            candidate_resources = unique(identifier for component in routes
                for identifier in component.get("requires_all", {}).get("recursos_digitais", []))
            if not candidate_resources:
                candidate_resources = unique(identifier for component in routes for kid in component.get("knowledge_ids", [])
                    for identifier in self.knowledge.get(kid, {}).get("aplicabilidade", {}).get("recursos_digitais", []))
            resource_question = (f"Em {environments[0][:1].lower() + environments[0][1:]}, que material ou aplicativo será usado?"
                                 if environments else "Que material ou aplicativo será usado nessa atividade?")
            add("recursos_digitais", resource_question,
                "Isso identifica o conteúdo ou aplicativo. Os equipamentos disponíveis são conferidos separadamente.",
                options=candidate_resources or None, priority=15)
        role_ids = {row.get("papel_id") for row in self.current.get("participations", [])}
        if "PAPEL-ESTUDANTE" in role_ids:
            role_ids.add("PAPEL-PESSOA-APOIADA")
        missing_roles = unique(identifier for component in routes for identifier in component.get("required_role_ids", [])
                               if identifier not in role_ids and identifier not in {
                                   "PAPEL-PROFESSORA", "PAPEL-ESTUDANTE", "PAPEL-COLEGAS", "PAPEL-TURMA"})
        if any(s.get("preparation_actor_ids") for s in context.get("situations", [])):
            missing_roles = [role for role in missing_roles if role != "PAPEL-RESPONSAVEL-ADAPTACAO"]
        if missing_roles:
            add("participantes", f"Quem pode preparar ou ajustar o material para {activity[:1].lower() + activity[1:]}?",
                "Essa resposta define quem realiza a adaptação; o cargo não comprova disponibilidade ou capacidade.",
                options=missing_roles, priority=25)
        available = set(self.available_context_values(context, "recursos_disponiveis"))
        blocked = set(context.get("recursos_impedidos", []))
        missing_resources = []
        for component in routes:
            missing_resources.extend(set(component.get("required_resource_ids", [])) - available - blocked)
            groups = component.get("required_any_resource_groups", []) or ([] if component.get("required_resource_ids") else [component.get("resource_ids", [])])
            for group in groups:
                if not set(group) & available:
                    missing_resources.extend(set(group) - blocked)
        if missing_resources:
            resource_scope = f" para usar {materials[0][:1].lower() + materials[0][1:]}" if materials else " nessa atividade"
            add("recursos_disponiveis", f"Quais equipamentos ou apoios estão disponíveis{resource_scope}?",
                "Perguntamos somente os recursos das possibilidades fundamentadas que ainda precisam de confirmação.",
                options=sorted(set(missing_resources)), priority=20)
        people = [row for row in self.current.get("participations", []) if row.get("papel_id") in {"PAPEL-ESTUDANTE", "PAPEL-PESSOA-APOIADA"}]
        for person in people:
            matrix_ids = {row["matrix_id"] for row in context.get("access_requirements", [])
                          if row.get("participant_id") == person["id"] and row.get("status") != "CONFLITO_A_CONFIRMAR"}
            personal_routes = [row for row in routes if not context.get("access_requirements")
                               or not row.get("access_requirement_matrix_ids")
                               or matrix_ids & set(row["access_requirement_matrix_ids"])]
            modes = unique(identifier for component in personal_routes
                           for identifier in component.get("requires_all", {}).get("modalidades_disponiveis", []))
            known_access = any(f.get("participant_id") == person["id"] and f.get("value") is True
                               and f.get("fact_id", "").rsplit("#", 1)[-1] in {"CanReadText", "UsesScreenReader", "AudioUsable", "CanReviewVisualText"}
                               for f in context.get("situated_facts", []))
            if modes and not person.get("modalidade_ids") and not known_access:
                add("modalidades_disponiveis", "Quais destas formas a pessoa já usa para acompanhar ou realizar essa atividade?",
                    "A necessidade de acesso é recuperada da base; a forma efetivamente utilizada depende da pessoa e do contexto.",
                    options=modes, participant=person, answer_field="modalidade_ids", priority=30)
        if len(people) > 1:
            required_resources = {rid for component in routes for rid in component.get("required_resource_ids", [])}
            operated = {rid for person in self.current.get("participations", []) for rid in person.get("recurso_operado_ids", [])}
            pending_operation = required_resources & available - operated
            for person in self.current.get("participations", []):
                if not pending_operation:
                    break
                allowed = set()
                if person in people:
                    applicable_matrix_ids = {row["matrix_id"] for row in context.get("access_requirements", [])
                                             if row.get("participant_id") == person["id"] and row.get("status") != "CONFLITO_A_CONFIRMAR"}
                    allowed = {rid for row in self.functional_matrix if row["id"] in applicable_matrix_ids for rid in row.get("recurso_ids", [])}
                elif any(person.get("papel_id") == component.get("responsible_role_id") for component in routes):
                    allowed = pending_operation
                relevant = pending_operation & allowed
                if relevant:
                    add("recursos_disponiveis", "Quais destes recursos essa pessoa consegue utilizar nesta atividade?",
                        "O equipamento disponível no local não comprova que a pessoa consegue operá-lo.", options=sorted(relevant),
                        participant=person, answer_field="recurso_operado_ids", priority=40)
        # An environment or functional characteristic is asked only when an
        # existing route explicitly depends on it, never just because it is empty.
        for field, label in (("caracteristicas_pessoa", "Qual destas condições interfere nessa atividade?"),):
            options = unique(identifier for component in routes for identifier in component.get("requires_all", {}).get(field, [])
                             if not self.intersects(context, field, [identifier]))
            if options:
                add(field, label, "Esta condição altera uma das possibilidades de apoio recuperadas.", options=options, priority=35)
        return sorted(questions, key=lambda row: (row["priority"], row["field"], row.get("participant_id", "")))

    def missing_questions(self):
        if self.current.get("scenario_mode") == "free_narrative":
            return situated_context.questions(self.current["context"], self.current.get("participations", []),
                                              self._free_missing_questions())
        c, questions = (self.current["context"], [])
        free = self.current.get("scenario_mode") == "free_narrative"
        task_components = self._task_components(c) if free else []
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
        if c.get("tarefas") and free and not task_components:
            operational_options = self._operational_task_options(c)
            if operational_options:
                questions.append({"field": "tarefas", "type": "single", "concept_ids": operational_options,
                                  "question": "Que atividade digital precisa ser acessível? Confirme a atividade, sem alterar o assunto informado."})
        if not c.get("barreiras") and (not c.get("necessidades")):
            questions.append(
                {
                    "field": "barreira_ou_necessidade",
                    "question": "O que está dificultando a atividade ou precisa ser apoiado?",
                }
            )
        elif free and task_components:
            unmet_groups = [group for component in task_components
                            for group in component.get("requires_any_groups", [])
                            if not any(self.intersects(c, row["field"], row.get("ids", [])) for row in group)]
            pending_ids = unique(identifier for group in unmet_groups for row in group
                                 if row["field"] in {"barreiras", "necessidades"} for identifier in row.get("ids", []))
            if pending_ids:
                questions.append({"field": "barreira_ou_necessidade", "type": "multi", "concept_ids": pending_ids, "required": False,
                                  "question": "O que precisa ser garantido ou está dificultando esta atividade? Marque somente o que corresponde ao caso."})
        functional_characteristics = [
            identifier
            for identifier in c.get("caracteristicas_pessoa", [])
            if self.concepts.get(identifier, {}).get("categoria_caracteristica")
            != "ESCOPO_DE_PUBLICO"
        ]
        supported = [row for row in self.current.get("participations", [])
                     if row.get("papel_id") in {"PAPEL-ESTUDANTE", "PAPEL-PESSOA-APOIADA"}]
        scoped = len(supported) > 1 and self.current.get("scenario_mode") == "free_narrative"
        if not functional_characteristics and not scoped:
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
        if free and task_components and self.current.get("participations"):
            available_roles = {row.get("papel_id") for row in self.current.get("participations", [])}
            if "PAPEL-ESTUDANTE" in available_roles:
                available_roles.add("PAPEL-PESSOA-APOIADA")
            missing_roles = unique(role for component in task_components for role in component.get("required_role_ids", [])
                                   if role not in available_roles)
            if missing_roles:
                questions.append({"field": "participantes", "type": "multi", "concept_ids": missing_roles, "required": False,
                                  "question": "Quem pode preparar, adaptar ou apoiar o conteúdo nesta atividade? Confirme a responsabilidade; ela não é presumida pelo cargo."})
        if not c.get("modalidades_disponiveis") and not scoped:
            questions.append(
                {
                    "field": "modalidades_disponiveis",
                    "question": "Quais formas de interação estão realmente disponíveis?",
                }
            )
        if scoped:
            relevant_characteristics = unique(identifier for component in task_components
                                              for kid in component.get("knowledge_ids", [])
                                              if self.intersects(c, "tarefas", self.knowledge.get(kid, {}).get("aplicabilidade", {}).get("tarefas", []))
                                              for identifier in self.knowledge.get(kid, {}).get("aplicabilidade", {}).get("caracteristicas_pessoa", [])
                                              if self.concepts.get(identifier, {}).get("categoria_caracteristica") != "ESCOPO_DE_PUBLICO")
            for participant in supported:
                label = participant.get("label") or participant.get("grupo_rotulo") or self.label(participant["papel_id"])
                for field, answer_field, concept_type, wording in (
                    ("modalidades_disponiveis", "modalidade_ids", "MODALIDADE", "Quais formas de interação permitem compreender o conteúdo para"),
                    ("caracteristicas_pessoa", "caracteristica_ids", "CARACTERISTICA_PESSOA", "Quais capacidades ou dificuldades são relevantes para"),
                ):
                    if not participant.get(answer_field):
                        options = relevant_characteristics if answer_field == "caracteristica_ids" else []
                        if answer_field == "caracteristica_ids" and not options:
                            continue
                        questions.append({"field": field, "answer_field": answer_field,
                                          "participant_id": participant["id"], "participant_label": label,
                                          "type": "multi", "required": False, "concept_ids": options or [key for key, value in self.concepts.items() if value.get("tipo") == concept_type],
                                          "question": f"{wording} {label}? Não presuma uma forma pelo diagnóstico."})
                if not participant.get("apoios_informados"):
                    questions.append({"field": "apoios_informados", "answer_field": "apoios_informados",
                                      "participant_id": participant["id"], "participant_label": label, "type": "text", "required": False,
                                      "question": f"Como {label} costuma compreender o conteúdo? Há outra forma de comunicação ou apoio que precisa ser considerada?"})
            required_resources = unique(identifier for component in task_components
                                        for identifier in component.get("required_resource_ids", []))
            operation_roles = {role for component in task_components for role in component.get("required_role_ids", [])}
            operation_roles.add("PAPEL-ESTUDANTE")
            for participant in self.current.get("participations", []):
                if participant.get("papel_id") not in operation_roles or participant.get("recurso_operado_ids") or not required_resources:
                    continue
                label = participant.get("label") or participant.get("grupo_rotulo") or self.label(participant["papel_id"])
                questions.append({"field": "recursos_disponiveis", "answer_field": "recurso_operado_ids",
                                  "participant_id": participant["id"], "participant_label": label,
                                  "type": "multi", "required": False, "concept_ids": required_resources,
                                  "question": f"Quais destes recursos {label} consegue utilizar nesta atividade? Disponibilidade no local não significa que a pessoa o utiliza."})
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
                    item = {"field": field, "question": question}
                    if free and task_components and field == "recursos_disponiveis":
                        options = unique(identifier for component in task_components
                                         for identifier in (component.get("required_resource_ids", []) or component.get("resource_ids", [])))
                        if options:
                            item.update(type="multi", concept_ids=options)
                    questions.append(item)
        return questions

    def available_context_values(self, context, field):
        """Presence somewhere in this context is not an ability of every person."""
        values = list(context.get(field, []))
        personal = {"caracteristicas_pessoa": "caracteristica_ids",
                    "modalidades_disponiveis": "modalidade_ids"}.get(field)
        if (personal and context is self.current.get("context")
                and self.current.get("scenario_mode") == "free_narrative"):
            values.extend(identifier for row in self.current.get("participations", [])
                          for identifier in row.get(personal, []))
        return unique(values)

    def matching_identifiers(self, context, field, identifiers):
        expected = set(identifiers or [])
        values = self.available_context_values(context, field)
        if field == "tarefas":
            return [value for value in values if any(self._task_path(value, target) for target in expected)]
        return sorted(set(values) & expected)

    def intersects(self, context, field, identifiers):
        return bool(self.matching_identifiers(context, field, identifiers))

    def derive_required_functions(self):
        """Operationalize existing applicable knowledge, never selected patterns.

        Only a functional witness (need, barrier or situated characteristic)
        licenses this proposed requirement. A broad principle/task alone does
        not turn every function in the catalogue into a context requirement.
        Prepared thesis contexts retain their explicitly recorded requirements.
        """
        if self.current.get("scenario_mode") != "free_narrative":
            return
        context = self.current["context"]
        previous = {row["function_id"] for row in context.get("function_derivation", [])}
        explicit = [value for value in context.get("funcoes_requeridas_ids", []) if value not in previous]
        context["funcoes_requeridas_ids"] = explicit
        derivations = []
        recording = self._record_checks
        self._record_checks = False
        try:
            # The curated applicability index supplies candidate requirements,
            # including functions of articulated products. This does not license
            # using those products: CQ2 and curation gates still decide that.
            for kid, knowledge in self.knowledge.items():
                application = knowledge.get("aplicabilidade") or {}
                task_paths = [self._task_path(observed, expected)
                              for observed in context.get("tarefas", [])
                              for expected in application.get("tarefas", [])
                              if self._task_path(observed, expected)]
                if not task_paths or self.authorize_knowledge(kid, context)[0] != "APLICAVEL":
                    continue
                witnesses = []
                for field in ("necessidades", "barreiras", "caracteristicas_pessoa"):
                    matches = self.matching_identifiers(context, field, application.get(field, []))
                    if matches:
                        witnesses.append({"field": field, "concept_ids": matches,
                                          "task_paths": task_paths,
                                          "participant_ids": unique([row["id"] for row in self.current.get("participations", [])
                                                              if field == "caracteristicas_pessoa" and set(matches) & set(row.get("caracteristica_ids", []))]
                                                              + [row["participant_id"] for row in context.get("access_requirements", [])
                                                                 if field == "necessidades" and row.get("participant_id") and set(matches) & set(row.get("requirement_ids", []))
                                                                 and row.get("status") != "CONFLITO_A_CONFIRMAR"])})
                if not witnesses:
                    continue
                supported_functions = knowledge.get("funcao_decisoria_ids", [])
                if "operation_claims" in knowledge:
                    supported_functions = unique(function for claim in knowledge["operation_claims"]
                        if claim.get("eligibility") == "DOCUMENTED_OPERATIONAL_CLAIM"
                        and claim.get("status") == "SUPPORTED_IN_RECORDED_SCOPE"
                        for function in claim.get("function_ids", []))
                for function in supported_functions:
                    if function in self.concepts:
                        derivations.append({"function_id": function, "knowledge_id": kid,
                                            "source_ids": knowledge.get("fonte_ids", []), "excerpt_ids": knowledge.get("trecho_ids", []),
                                            "correspondences": witnesses,
                                            "origin": "REQUISITO_DE_PROJETO_POR_APLICABILIDADE_DOCUMENTADA",
                                            "status": "REQUISITO_ANALITICO_PROPOSTO_NAO_RESULTADO_EMPIRICO",
                                            "knowledge_usage_authorized_by_this_step": False,
                                            "not_derived_from_component": True})
        finally:
            self._record_checks = recording
        context["function_derivation"] = derivations
        context["funcoes_requeridas_ids"] = unique(explicit + [row["function_id"] for row in derivations])

    def build_context_graph(self, situated_result=None):
        """Export this case; an optional current situated result replaces legacy requirements."""
        if situated_result is not None:
            snapshot = copy.deepcopy(self.current["context"])
            snapshot["participations"] = copy.deepcopy(self.current.get("participations", []))
            snapshot["confirmed"] = self.current.get("mapping_confirmed") is True
            digest = hashlib.sha256(json.dumps(snapshot, sort_keys=True, ensure_ascii=False,
                                               separators=(",", ":")).encode()).hexdigest()
            if not snapshot["confirmed"]:
                raise ValueError("Confirme o contexto antes de exportar seus requisitos situados.")
            if (not isinstance(situated_result, dict)
                    or situated_result.get("composition_kind") != "SITUATED_OPERATION_GRAPH"
                    or situated_result.get("context_id") != snapshot["id"]
                    or situated_result.get("execution_inputs", {}).get("context_sha256") != digest):
                raise ValueError("O resultado situado não pertence ao contexto e à revisão atuais.")
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
            if row.get("papel_id"):
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
        for situation in context.get("situations", []):
            episode = MADO[situation["id"]]
            graph.add((episode, RDF.type, MADO.ContextoDeInteracaoDigital))
            graph.add((episode, MADO.episodioDoContexto, ctx))
            graph.add((episode, MADO.identificador, Literal(situation["id"])))
            graph.add((episode, MADO.descricaoDoContexto, Literal(situation.get("label", ""), lang="pt-BR")))
            # An episode belongs to the same situated description unless a
            # local perspective is stated. Preserve an explicit empty value;
            # missing perspective must remain visible to SHACL, not invented.
            perspectives = situation.get("perspectiva_ids", context.get("perspectiva_ids", []))
            for perspective in perspectives or []:
                graph.add((episode, MADO.descritoSobPerspectiva, MADO[perspective]))
            for task in situation.get("task_ids", []):
                graph.add((episode, MADO.temTarefa, MADO[task]))
            # Participation already belongs to the overall context. Do not add
            # a second value to functional participacaoEmContexto or infer that
            # one person's ability belongs to the whole group.
        if situated_result is not None:
            from rdflib import URIRef, RDFS

            def resource(identifier):
                # Keep foreign RDF task/function IRIs; do not mint MADO aliases.
                return URIRef(identifier) if identifier.startswith(("https://", "http://", "urn:")) else MADO[identifier]

            situations = {row["id"]: row for row in context.get("situations", [])}
            people = {row["id"] for row in self.current.get("participations", [])}
            checks = {row["id"]: row for row in situated_result.get("execution_evidence", [])}
            for requirement in situated_result.get("required_functions", []):
                sid, pid = requirement.get("situation_id"), requirement.get("participant_id")
                situation = situations.get(sid)
                if (not situation or pid not in people or pid not in situation.get("participant_ids", [])
                        or context.get("active_situation_id") and sid != context["active_situation_id"]):
                    raise ValueError("Requisito situado fora da participação ou situação atuais.")
                tasks, function = requirement.get("task_ids", []), requirement.get("function_id")
                scope = requirement.get("task_scope_kind")
                recorded = [checks.get(check_id, {}) for check_id in requirement.get("check_ids", [])]
                witnessed_fields = ("id", "function_id", "situation_id", "participant_id", "task_ids",
                                    "task_scope_kind", "origin", "witnesses", "claim_ids")
                witnessed = any(row.get("kind") == "REQUIRED_FUNCTION_BEFORE_SELECTION"
                                and all(row.get("observed", {}).get("value", {}).get(field) == requirement.get(field)
                                        for field in witnessed_fields) for row in recorded)
                if (not function or not tasks or scope not in {
                        "REGISTERED_TASK_REQUIREMENT", "CONTEXTUAL_TASK_SCOPE_NOT_CAUSAL_SUPPORT"}
                        or not witnessed):
                    raise ValueError("Requisito situado sem tarefa e testemunho de derivação registrados.")
                occurrence = MADO["FUN-SIT-" + hashlib.sha256(json.dumps(
                    [context["id"], sid, pid, function], sort_keys=True).encode()).hexdigest()[:16]]
                graph.add((occurrence, RDF.type, MADO.FuncaoRequeridaSituada))
                graph.add((occurrence, MADO.noContexto, MADO[sid]))
                graph.add((occurrence, MADO.paraParticipacao, MADO[pid]))
                graph.add((occurrence, MADO.requerFuncao, resource(function)))
                graph.add((occurrence, MADO.origemDoRegistro, Literal(requirement.get("origin", ""))))
                graph.add((occurrence, MADO.statusDoRegistro, Literal(scope)))
                if scope == "CONTEXTUAL_TASK_SCOPE_NOT_CAUSAL_SUPPORT":
                    graph.add((occurrence, RDFS.comment, Literal(
                        "paraTarefa delimita o escopo contextual; não afirma que a tarefa fundamenta a necessidade funcional.", lang="pt-BR")))
                for task in tasks:
                    graph.add((occurrence, MADO.paraTarefa, resource(task)))
                for witness in requirement.get("witnesses", []):
                    for condition in witness.get("need_ids", []) + witness.get("characteristic_ids", []):
                        graph.add((occurrence, MADO.derivadaDaCondicao, resource(condition)))
            return graph
        for requirement in context.get("function_derivation", []):
            if not requirement.get("function_id"):
                continue
            for witness in requirement.get("correspondences", []):
                people = witness.get("participant_ids") or [None]
                for person in people:
                    signature = json.dumps([context["id"], requirement["function_id"], requirement.get("knowledge_id"), witness, person], sort_keys=True)
                    occurrence = MADO["FUN-SIT-" + hashlib.sha256(signature.encode()).hexdigest()[:16]]
                    graph.add((occurrence, RDF.type, MADO.FuncaoRequeridaSituada))
                    graph.add((occurrence, MADO.noContexto, MADO[witness.get("situation_id") or context["id"]]))
                    graph.add((occurrence, MADO.requerFuncao, MADO[requirement["function_id"]]))
                    if person:
                        graph.add((occurrence, MADO.paraParticipacao, MADO[person]))
                    for path in witness.get("task_paths", []):
                        if path:
                            graph.add((occurrence, MADO.paraTarefa, MADO[path[0]]))
                    for condition in witness.get("concept_ids", []):
                        graph.add((occurrence, MADO.derivadaDaCondicao, MADO[condition]))
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
                "participant_id": local_id(row[13]) if len(row) > 13 and row[13] else None,
                "required_function_id": local_id(row[6]) if row[6] else "",
                "task_path": self._task_path(local_id(row[9]), local_id(row[10])),
                "authorization": state,
                "access_requirement_witnesses": [copy.deepcopy(item) for item in context.get("access_requirements", [])
                                                  if row[11] and local_id(row[11]) in item.get("requirement_ids", [])
                                                  and item.get("status") != "CONFLITO_A_CONFIRMAR"],
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

    def authorize_knowledge_claim(self, identifier, claim_id, context, function_id=None):
        """Check the applied assertion, not the mere presence of a bibliography.

        A proposal with an unreviewed foundation is not a conditional advice.
        Conditionality is reserved for unknown *contextual* preconditions after
        an eligible documentary claim has been identified.
        """
        knowledge = self.knowledge.get(identifier, {})
        claim = next((row for row in knowledge.get("operation_claims", [])
                      if row.get("id") == claim_id), None)
        reasons = []
        if not claim:
            reasons.append("Afirmação operacional não registrada neste conhecimento.")
        else:
            if (claim.get("eligibility") != "DOCUMENTED_OPERATIONAL_CLAIM"
                    or claim.get("status") != "SUPPORTED_IN_RECORDED_SCOPE"
                    or claim.get("foundation_status") != "DOCUMENTED_IN_RECORDED_SCOPE"):
                reasons.append("A afirmação aplicada ainda não tem fundamentação autorizada no escopo registrado.")
            support = claim.get("support", [])
            if not support:
                reasons.append("A afirmação não indica uma contribuição documental localizada.")
            for row in support:
                excerpt = self.excerpts.get(row.get("excerpt_id"), {})
                if not excerpt or row.get("source_id") not in self.sources or excerpt.get("fonte_id") != row.get("source_id"):
                    reasons.append("O trecho e a fonte da afirmação não correspondem.")
                if not row.get("support_scope") or not row.get("review_status"):
                    reasons.append("O escopo e o estado de conferência do apoio não foram informados.")
            functions = set(claim.get("function_ids", []) or claim.get("scope", {}).get("function_ids", []))
            if function_id and function_id not in functions:
                reasons.append("A afirmação não autoriza esta função.")
        self._check("claim", claim_id, "localized_operational_claim", "FAIL" if reasons else "PASS",
                    "Conferência da afirmação empregada, separada da aprovação do conhecimento completo.",
                    knowledge_id=identifier, function_id=function_id, reasons=reasons)
        if reasons:
            return "EXCLUIDO", reasons
        return self.authorize_knowledge(identifier, context)

    def authorize_knowledge(self, identifier, context):
        """Selection gate, distinct from candidate retrieval; never uses diagnosis/name IDs."""
        knowledge = self.knowledge[identifier]
        present = {
            v
            for field in self.context_fields
            if field not in {"recursos_impedidos", "recursos_propostos"}
            for v in self.available_context_values(context, field)
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
        claims = knowledge.get("operation_claims")
        eligible_claims = [row for row in claims or []
                           if row.get("eligibility") == "DOCUMENTED_OPERATIONAL_CLAIM"
                           and row.get("status") == "SUPPORTED_IN_RECORDED_SCOPE"
                           and row.get("foundation_status") == "DOCUMENTED_IN_RECORDED_SCOPE"]
        if claims is not None and not eligible_claims:
            reasons.append("Nenhuma afirmação deste conhecimento está autorizada para orientação; registro mantido para auditoria.")
        if claims is not None:
            self._check("knowledge", identifier, "claim_level_authorization", "PASS" if eligible_claims else "FAIL",
                        "Há pelo menos uma parcela documentada; somente essa parcela poderá ser aplicada.",
                        claim_ids=[row["id"] for row in eligible_claims], whole_knowledge_authorized=False)
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
        conditional_application = (self.current.get("scenario_mode") == "free_narrative"
                                   and bool(component.get("conditions") and component.get("alternative"))
                                   and component["id"] in (self._dialogue_route_ids if self._dialogue_route_ids is not None
                                                          else {row["id"] for row in self._dialogue_routes(context)}))
        pending_application = []
        scope_matches = self._access_requirement_scope_matches(component, context)
        if component.get("access_requirement_matrix_ids") and context.get("access_requirements"):
            self._check("component", component["id"], "documented_access_requirement_scope", "PASS" if scope_matches else "FAIL",
                        "O requisito funcional documentado deve corresponder à aplicação do padrão; um rótulo de deficiência não autoriza outra rota.",
                        expected_ids=component.get("access_requirement_matrix_ids", []),
                        observed_ids=unique(row["matrix_id"] for row in context["access_requirements"] if row.get("status") != "CONFLITO_A_CONFIRMAR"))
        if not scope_matches:
            reasons.append("a rota não corresponde ao requisito de acesso documentado para este caso")
        available_roles = {
            row.get("papel_id") for row in self.current.get("participations", [])
        }
        missing_roles = set(component.get("required_role_ids", [])) - available_roles
        if (
            "PAPEL-PESSOA-APOIADA" in missing_roles
            and "PAPEL-ESTUDANTE" in available_roles
        ):
            missing_roles.remove("PAPEL-PESSOA-APOIADA")
        self._check("component", component["id"], "required_roles", ("PENDING" if conditional_application else "FAIL") if missing_roles else "PASS",
                    "Papéis participantes exigidos pelo padrão.", operator="ALL_WITH_STUDENT_AS_SUPPORTED_PERSON",
                    expected_ids=component.get("required_role_ids", []), observed_ids=sorted(available_roles), missing_ids=sorted(missing_roles))
        if missing_roles:
            (pending_application if conditional_application else reasons).append(
                "confirmar quem assume a responsabilidade: " + ", ".join(self.labels(sorted(missing_roles))))
        required_resources = set(component.get("required_resource_ids", []))
        supported_people = [row for row in self.current.get("participations", [])
                            if row.get("papel_id") in {"PAPEL-ESTUDANTE", "PAPEL-PESSOA-APOIADA"}]
        if self.current.get("scenario_mode") == "free_narrative" and len(supported_people) > 1 and required_resources:
            operation_rows = [row for row in self.current.get("participations", [])
                              if row.get("papel_id") in set(component.get("required_role_ids", [])) | {"PAPEL-ESTUDANTE"}]
            operated = {resource for row in operation_rows for resource in row.get("recurso_operado_ids", [])}
            missing_operation = required_resources - operated
            self._check("component", component["id"], "declared_resource_operation", "PENDING" if missing_operation else "PASS",
                        "Operação declarada por um participante; disponibilidade global não comprova capacidade individual nem acesso de toda a turma.",
                        operator="ALL_RESOURCES_HAVE_A_DECLARED_OPERATOR", expected_ids=sorted(required_resources), observed_ids=sorted(operated),
                        missing_ids=sorted(missing_operation), participant_ids=[row["id"] for row in operation_rows if required_resources & set(row.get("recurso_operado_ids", []))])
            if missing_operation:
                (pending_application if conditional_application else reasons).append("confirmar quem consegue utilizar: " + ", ".join(self.labels(sorted(missing_operation))))
        resource_groups = component.get("required_any_resource_groups", [])
        if not required_resources and (not resource_groups):
            resource_groups = [component.get("resource_ids", [])]
        available_resources = set(self.available_context_values(context, "recursos_disponiveis"))
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
        resource_gate = "CONDICIONAL_A_CONFIRMACAO" if pending_application else "CONFIRMADO_DISPONIVEL"
        if unknown_core_resources:
            if conditional_application or component.get("role") == "condicional" and component.get("alternative"):
                resource_gate = "CONDICIONAL_A_CONFIRMACAO"
                pending_application.append("confirmar disponibilidade de " + ", ".join(self.labels(sorted(unknown_core_resources))))
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
                                 and (conditional_application or component.get("role") == "condicional" and component.get("alternative")))
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
                (conditional_application or component.get("role") == "condicional" and component.get("alternative"))
                and options
            ):
                resource_gate = "CONDICIONAL_A_CONFIRMACAO"
                pending_application.append("confirmar um meio disponível entre " + ", ".join(self.labels(sorted(options - blocked_resources))))
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
            matching_ids = self.matching_identifiers(context, field, identifiers)
            pending_field = conditional_application and not matched and field in {"modalidades_disponiveis", "recursos_disponiveis", "recursos_digitais"}
            if field == "recursos_digitais" and context.get(field):
                pending_field = False
            if field == "recursos_disponiveis" and set(identifiers) <= blocked_resources:
                pending_field = False
            self._check("component", component["id"], f"required_field_{field}", "PASS" if matched else ("PENDING" if pending_field else "FAIL"),
                        "Cada campo é obrigatório; os conceitos dentro do campo são opções alternativas.", operator="ANY_IN_FIELD",
                        field=field, expected_ids=identifiers, observed_ids=self.available_context_values(context, field),
                        matched_ids=matching_ids,
                        participant_ids=[row["id"] for row in self.current.get("participations", [])
                                         if set(row.get({"caracteristicas_pessoa": "caracteristica_ids", "modalidades_disponiveis": "modalidade_ids", "recursos_disponiveis": "recurso_operado_ids"}.get(field, ""), [])) & set(matching_ids)],
                        task_paths=[self._task_path(value, target) for value in matching_ids for target in identifiers
                                    if field == "tarefas" and self._task_path(value, target)])
            if matched:
                values = matching_ids
                matches.append(
                    {"field": field, "ids": values, "labels": self.labels(values)}
                )
            else:
                if pending_field:
                    resource_gate = "CONDICIONAL_A_CONFIRMACAO"
                    pending_application.append("confirmar para esta aplicação: " + ", ".join(self.labels(identifiers)))
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
                    values = self.matching_identifiers(context, clause["field"], clause["ids"])
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
                        clauses=[{"field": c["field"], "expected_ids": c["ids"], "observed_ids": self.available_context_values(context, c["field"]),
                                  "matched_ids": self.matching_identifiers(context, c["field"], c["ids"])} for c in clauses],
                        matched_ids=unique(v for c in clauses for v in self.matching_identifiers(context, c["field"], c["ids"])))
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
        if pending_application:
            matches.append({"field": "application_to_confirm", "ids": [], "labels": unique(pending_application)})
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
        """Render only selected actions; presentation order is not a causal plan."""
        objective = str(context.get("objetivo", "")).strip().rstrip(".")
        rendered = []
        for item in selected:
            action = str(item.get("action", "")).strip().rstrip(".")
            if action:
                title = item.get("label") or "Orientação"
                rendered.append(f"{title}: {action}.")
        prefix = f"Objetivo informado: {objective}.\n\n" if objective else ""
        return prefix + "\n\n".join(rendered)

    def build_practical_summary(self, configurations, status, context=None):
        """Project selected actions without inventing modes, order or support.

        Curated wording is editorial, not a new decision rule. Its source-action
        fingerprint prevents stale copy from silently overriding changed data.
        Each step retains the source fragment used to write it.
        """
        if status not in {"GERADA", "GERADA_PARCIAL"} or not configurations:
            return {
                "titulo": "Ainda não é possível orientar este caso",
                "texto": "Faltam informações ou conhecimentos verificados para construir uma orientação segura.",
                "etapas": [],
                "component_ids": [],
                "derivacao": "PROJECAO_DA_MESMA_DECISAO_SEM_NOVO_CONTEUDO",
            }
        groups = []
        for row in configurations:
            identifier = row.get("component_id", row.get("id"))
            action = str(row.get("acao", row.get("action", ""))).strip()
            copy_row = PRACTICAL_COPY.get(identifier, {})
            fingerprint = hashlib.sha256(action.encode("utf-8")).hexdigest()
            curated = bool(
                action
                and copy_row.get("action_sha256") == fingerprint
                and copy_row.get("steps")
                and all(fragment in action for _, fragment in copy_row["steps"])
            )
            if curated:
                step_rows = copy_row["steps"]
            else:
                # Preserve changed/new actions literally. A semicolon is already
                # an explicit separation in that action, not a dependency inferred
                # between two different configurations.
                fragments = [part.strip() for part in action.split(";") if part.strip()]
                step_rows = [
                    (part[:1].upper() + part[1:].rstrip(".") + ".", part)
                    for part in fragments
                ]
            steps = [
                {
                    "texto": text,
                    "component_id": identifier,
                    "campo_origem": "acao",
                    "fragmento_origem": fragment,
                }
                for text, fragment in step_rows
            ]
            title = (
                copy_row["title"] if curated
                else row.get("label") or "Aplique a ação indicada"
            )
            function = str(row.get("funcao", row.get("function", ""))).strip()
            availability = row.get("availability_status", "CONFIRMADO_DISPONIVEL")
            resources = copy.deepcopy(row.get("resource_options", []))
            conditional = availability == "CONDICIONAL_A_CONFIRMACAO"
            groups.append({
                "id": f"choice-{identifier}",
                "titulo": title,
                "passos": steps,
                "itens": [step["texto"] for step in steps],
                "component_ids": [identifier],
                "modos": [row.get("modo") or self.label(row.get("mode_id"))]
                    if row.get("modo") or row.get("mode_id") else [],
                "funcao": function,
                "como_combinar": copy_row.get("relation", "") if curated else "",
                "condicoes": unique(row.get("conditions", [])),
                "alternativas": [row["alternative"]] if row.get("alternative") else [],
                "acompanhamento": [row["monitoring"]] if row.get("monitoring") else [],
                "estado_recurso": [availability],
                "aplicabilidade": availability,
                "antes_de_usar": (
                    "Possibilidade condicionada: confirme os pontos abaixo antes de aplicar."
                    if conditional else ""
                ),
                "recursos": unique(
                    resource.get("label") for resource in resources if resource.get("label")
                ),
                "recursos_estruturados": resources,
                "origem": {
                    "component_id": identifier,
                    "campo_acao": "acao",
                    "acao_original": action,
                    "acao_sha256": fingerprint,
                    "projecao_editorial_conferida": curated,
                    "relacao": "EXPLICACAO_EDITORIAL_DO_PADRAO_SELECIONADO" if curated else None,
                    "knowledge_ids": list(row.get("knowledge_ids", [])),
                    "criterion_ids": list(row.get("criterion_ids", [])),
                    "articulation_ids": list(row.get("articulation_ids", [])),
                },
            })
        primary = next(
            (row for row in configurations if row.get("papel", row.get("role")) == "principal"),
            configurations[0],
        )
        primary_id = primary.get("component_id", primary.get("id"))
        headline = next(
            (group["titulo"] for group in groups if group["component_ids"] == [primary_id]),
            "Orientações para as condições informadas",
        )
        return {
            "titulo": "Sugestão para este caso",
            "texto": headline,
            "etapas": groups,
            "component_ids": [row.get("component_id", row.get("id")) for row in configurations],
            "organizacao": "CARTOES_POR_CONFIGURACAO_SEM_ORDEM_CAUSAL_ENTRE_ELES",
            "resultado_esperado": " ".join(unique(
                row.get("monitoring") for row in configurations if row.get("monitoring")
            )),
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
            row["source"] = {"id": sid, "title": self.sources.get(sid, {}).get("titulo", sid),
                             "url": self.sources.get(sid, {}).get("url", ""),
                             "edition": self.sources.get(sid, {}).get("edition", "")} if sid else None
            row.setdefault("excerpt", {})
            row["excerpt"].update({key: copy.deepcopy(excerpt[key]) for key in
                                   ("document_url", "version", "review_status", "primary_review_status",
                                    "document_version", "document_review_status", "document_paraphrase") if key in excerpt})
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

    def generate_situated(self, progress=None):
        """Public semantic route for examples and narratives, with no topic dispatch.

        ``generate`` below remains a compatibility audit of the former pattern
        selector; it is not the public recommendation path in this revision.
        """
        from experimental.v2.trajectory import compose_context
        if self.current is None:
            raise ValueError("Informe e confira o caso antes de gerar a orientação.")
        context = copy.deepcopy(self.current["context"])
        context["participations"] = copy.deepcopy(self.current.get("participations", []))
        context["confirmed"] = self.current.get("mapping_confirmed") is True
        result = compose_context(context, engine=self, progress=progress)
        from semantic_execution import project_execution, semantic_execution_summary
        self._last_execution_graph = project_execution(result, context, self.graph)
        result["semantic_trace"] = semantic_execution_summary(self._last_execution_graph)
        result["fingerprints"] = {
            Path(name).relative_to(ROOT).as_posix() if Path(name).is_absolute() and Path(name).is_relative_to(ROOT) else name: digest
            for name, digest in result.get("fingerprints", {}).items()
        }
        result["result_contract"] = "AMADO_SITUATED_1"
        result["base_version"] = VERSION
        result["case_storage"] = False
        # Follow-up is the actual intake state, not a new justification or a
        # promise that more user input can repair absent operational knowledge.
        has_support = any(result.get(key) for key in ("choices", "pending_candidates", "partial_segments"))
        result["next_questions"] = copy.deepcopy(self.missing_questions()[:3]) if not has_support else []
        manifest = context.get("question_manifest", {})
        result["unresolved_answers"] = [
            copy.deepcopy(manifest[answer["question_id"]])
            for answer in context.get("question_answers", [])
            if answer.get("state") == "UNKNOWN" and answer.get("question_id") in manifest
        ] if not has_support else []
        result["intake_status"] = (
            "UNCONFIRMED" if not context["confirmed"] else
            "SUPPORT_AVAILABLE" if has_support else
            "NEEDS_CLARIFICATION" if result["next_questions"] else
            "CONTEXT_UNKNOWN" if result["unresolved_answers"] else "COVERAGE_LIMIT"
        )
        self.current["last_result"] = copy.deepcopy(result)
        return result

    def generate(self, progress=None):
        """Compose a decision; optional progress reports actual stage boundaries.

        Notifications contain no narrative or personal information and never
        become evidence of a verification. The returned result is unchanged.
        """
        if progress is not None and not callable(progress):
            raise TypeError("O observador de progresso deve ser uma função.")

        def notify(stage, state, message):
            if progress is not None:
                progress({"stage": stage, "state": state, "message": message})

        self.derive_required_functions()
        context = self.current["context"]
        self._dialogue_route_ids = ({row["id"] for row in self._dialogue_routes(context)}
                                   if self.current.get("scenario_mode") == "free_narrative" else set())
        self._evidence = ExecutionEvidence(VERSION, context["id"])
        self._evidence.data["access_requirements"] = copy.deepcopy(context.get("access_requirements", []))
        self._record_checks = True
        # Who requests guidance is useful for presentation but cannot authorize
        # a pattern or suspend a decision when its functional conditions hold.
        questions = [row for row in self.missing_questions() if row.get("decision_relevant", True)]
        if not self.current.get("mapping_confirmed"):
            questions = [
                {
                    "field": "mapping",
                    "question": "Confirme se a organização representa corretamente o contexto.",
                }
            ] + questions
        self._check("context", context["id"], "context_confirmation", "PASS" if self.current.get("mapping_confirmed") else "FAIL",
                    "Confirmação explícita da organização do contexto.", operator="IS_TRUE", observed=self.current.get("mapping_confirmed"))
        blocking_questions = [row for row in questions if row.get("required", True)]
        self._check("context", context["id"], "minimum_context", "FAIL" if blocking_questions else "PASS",
                    "Campos mínimos conferidos; perguntas sobre rotas individuais pendentes permanecem visíveis e são avaliadas em cada configuração.", operator="NO_MISSING_ESSENTIAL_FIELDS",
                    missing_fields=[r["field"] for r in blocking_questions], pending_questions=[row for row in questions if not row.get("required", True)])
        notify("retrieval", "running", "Consultando os conhecimentos e vínculos da base local da MADO…")
        context_graph = self.build_context_graph()
        retrieval = self.retrieve_transfer_candidates(context_graph)
        notify("retrieval", "completed", "Conhecimentos e articulações recuperados da base local.")
        notify("verification", "running", "Conferindo condições, critérios e apoios para este caso…")

        def select_components(knowledge_ids, criterion_ids, record=False):
            self._record_checks = record
            selected_rows, rejected_rows = ([], [])
            if blocking_questions:
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
                            "conditions": unique(component.get("conditions", []) + ["Antes de aplicar: " + text + "."
                                                  for match in matches if match.get("field") == "application_to_confirm" for text in match.get("labels", [])]),
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
        supported_partial = bool(selected) and self.current.get("scenario_mode") == "free_narrative"
        if not primary and supported_partial:
            status = "GERADA_PARCIAL"
        if not primary and not supported_partial:
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
                    "question": ("As partes fundamentadas abaixo não cobrem toda a atividade; falta uma configuração principal verificada."
                                 if supported_partial else "A base não possui configuração principal verificada para esta combinação; registre a lacuna antes de decidir."),
                }
            ]
        offered_functions = unique(f for item in selected for f in item.get("function_ids", []))
        required_functions = unique(context.get("funcoes_requeridas_ids", []))
        remaining_functions = [f for f in required_functions if f not in offered_functions]
        if primary and remaining_functions:
            status = "GERADA_PARCIAL"
        if primary and any(not row.get("required", True) for row in questions):
            status = "GERADA_PARCIAL"
        if primary and any(item.get("resource_gate") == "CONDICIONAL_A_CONFIRMACAO" for item in selected):
            status = "GERADA_PARCIAL"
        supported_people = [row for row in self.current.get("participations", [])
                            if row.get("papel_id") in {"PAPEL-ESTUDANTE", "PAPEL-PESSOA-APOIADA"}]
        participant_coverage = []
        if len(supported_people) > 1 and self.current.get("scenario_mode") == "free_narrative":
            for participant in supported_people:
                declared_modes = set(participant.get("modalidade_ids", []))
                operated = set(participant.get("recurso_operado_ids", []))
                participant_matrix_ids = {row["matrix_id"] for row in context.get("access_requirements", [])
                                          if row.get("participant_id") == participant["id"] and row.get("status") != "CONFLITO_A_CONFIRMAR"}
                def scoped_to_person(item):
                    allowed = set(item.get("access_requirement_matrix_ids", []))
                    if context.get("access_requirements") and allowed:
                        return bool(allowed & participant_matrix_ids)
                    return True
                compatible = [item["id"] for item in selected
                              if scoped_to_person(item) and item.get("resource_gate") != "CONDICIONAL_A_CONFIRMACAO"
                              and (item.get("mode_id") in declared_modes
                                   or operated & set(item.get("selected_resource_ids", [])))]
                conditional = [item["id"] for item in selected if scoped_to_person(item)
                               and item.get("resource_gate") == "CONDICIONAL_A_CONFIRMACAO"
                               and (participant_matrix_ids & set(item.get("access_requirement_matrix_ids", []))
                                    or item.get("mode_id") in declared_modes
                                    or operated & set(item.get("selected_resource_ids", [])))]
                participant_coverage.append({"participant_id": participant["id"],
                                             "label": participant.get("label") or participant.get("grupo_rotulo") or self.label(participant["papel_id"]),
                                             "component_ids": compatible,
                                             "conditional_component_ids": conditional,
                                             "status": "ROTA_DECLARADA_A_CONFERIR_EM_USO" if compatible else ("POSSIBILIDADE_CONDICIONAL_A_CONFIRMAR" if conditional else "SEM_ROTA_FUNDAMENTADA"),
                                             "meaning_or_learning_measured": False})
            if selected and any(not row["component_ids"] for row in participant_coverage):
                status = "GERADA_PARCIAL"
        ready_functions = {f for item in selected if item.get("resource_gate") != "CONDICIONAL_A_CONFIRMACAO" for f in item.get("function_ids", [])}
        self._evidence.data["functions"] = {
            "required": required_functions, "offered": offered_functions,
            "verified": [f for f in required_functions if f in ready_functions],
            "conditional": [f for f in required_functions if f in offered_functions and f not in ready_functions],
            "remaining": remaining_functions,
            "interpretation": "Funções de propostas condicionais permanecem a confirmar; funções dos demais padrões atendem às verificações registradas, não comprovam eficácia em uso.",
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
        notify("verification", "completed", "Conferência concluída; condições pendentes e limites foram preservados.")
        notify("composition", "running", "Organizando as ações e seus fundamentos para apresentação…")
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
            "participant_coverage": participant_coverage,
            "candidate_knowledge_ids": retrieval["knowledge_ids"],
            "function_derivation": copy.deepcopy(context.get("function_derivation", [])),
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
        notify("composition", "completed", "Resultado da consulta e rastreabilidade organizados.")
        return result
