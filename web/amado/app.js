import { request, restart } from './client.mjs';
const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => [...document.querySelectorAll(selector)];
let catalog = null;
let currentCase = null;
let lastResult = null;
let activeTab = "known";
let busy = false;
let organizedNarrative = null;
let operationEpoch = 0;
const INTERVIEW_TEMPLATE = "CTX-TRANSFERENCIA-RECURSO-DIGITAL-01";

function normalizeNarrative(value) {
  return String(value || "").replace(/\r\n/g, "\n").trim();
}

function scrollBehavior() {
  return window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth';
}

function invalidateDecision(free, message = "As informações mudaram. Confira a organização e construa novamente a orientação.") {
  lastResult = null;
  $("#saida").hidden = true;
  $(free ? "#free-confirmed" : "#mapping-confirmed").checked = false;
  $(free ? "#free-status" : "#known-status").textContent = message;
  if ("speechSynthesis" in window) window.speechSynthesis.cancel();
}

async function runBusy(statusTarget, operation) {
  if (busy) return;
  const epoch = operationEpoch;
  busy = true;
  const controls = $$("main button, main input, main textarea, main select").map((node) => [node, node.disabled]);
  controls.forEach(([node]) => { if (!['clear-case', 'stop-speech'].includes(node.id)) node.disabled = true; });
  $("#main").setAttribute("aria-busy", "true");
  $('#runtime-error').textContent = '';
  $(statusTarget).classList.remove("error-message");
  try { return await operation(); }
  catch (error) { if (epoch === operationEpoch) showError(statusTarget, error); }
  finally {
    if (epoch === operationEpoch) {
      controls.forEach(([node, disabled]) => { node.disabled = disabled; });
      $("#main").setAttribute("aria-busy", "false");
      busy = false;
    }
  }
}

function interpretationFromContext(currentPayload) {
  const context = currentPayload.context;
  return {
    fields: {pessoa_e_participacao: context.participantes, objetivo: context.objetivo, atividade: context.tarefas, dificuldade: context.barreiras, necessidade: context.necessidades, ambiente: context.ambientes, formas_de_interacao: context.modalidades_disponiveis, recursos_digitais: context.recursos_digitais, recursos_disponiveis: context.recursos_disponiveis, recursos_impedidos: context.recursos_impedidos, recursos_propostos: context.recursos_propostos, restricoes: context.restricoes, operacao_do_recurso: context.operacao_do_recurso},
    missing_questions: currentPayload.questions.map((item) => typeof item === "string" ? item : item.question),
  };
}

const fieldConfig = {
  tarefas: ["TAREFA", "Atividade"],
  caracteristicas_pessoa: ["CARACTERISTICA_PESSOA", "Pessoa e participação"],
  barreiras: ["BARREIRA", "Dificuldade observada"],
  necessidades: ["NECESSIDADE", "O que precisa ser apoiado"],
  funcoes_requeridas_ids: ["FUNCAO_DECISORIA", "O que a orientação precisa garantir"],
  ambientes: ["AMBIENTE", "Onde ocorre"],
  modalidades_disponiveis: ["MODALIDADE", "Formas de interação"],
  recursos_digitais: ["RECURSO_DIGITAL", "Aplicativo ou conteúdo utilizado"],
  recursos_disponiveis: ["RECURSO_DISPONIVEL", "Dispositivos e apoios disponíveis"],
  recursos_propostos: ["RECURSO_DISPONIVEL", "Recursos propostos (a preparar)"],
  recursos_impedidos: ["RECURSO_DISPONIVEL", "Recursos que não podem ser usados"],
};
const resourceFields = ["recursos_disponiveis", "recursos_propostos", "recursos_impedidos"];
// Presentation groups only: selecting a requirement remains an explicit action.
const functionCategories = {
  "Situação e acompanhamento": ["FUN-CARACTERIZAR-CONDICOES", "FUN-ACOMPANHAR-RESULTADO", "FUN-SELECIONAR-MODO-POR-CONDICAO"],
  "Acesso, revisão e retorno": ["FUN-PRESERVAR-ACESSO", "FUN-MANTER-INFORMACAO-RECUPERAVEL", "FUN-PRESERVAR-SIGNIFICADO-ENTRE-MODOS", "FUN-PERMITIR-REVISAO", "FUN-FEEDBACK-PERCEPTIVEL"],
  "Expressão e participação": ["FUN-PRESERVAR-PROTAGONISMO", "FUN-COORDENAR-AUTORIA", "FUN-EXPRESSAR-CONHECIMENTO"],
  "Organização e aprendizagem": ["FUN-ORGANIZAR-CONTEUDO", "FUN-CONTEXTUALIZAR-MUDANCA", "FUN-CONSOLIDAR-COM-FEEDBACK", "FUN-REDUZIR-SOBRECARGA"],
};

async function api(path, options = {}) {
  const payload = options.body ? JSON.parse(options.body) : {};
  const operations = {'/api/health':'initialize', '/api/catalog':'catalog', '/api/context':'update', '/api/generate':'generate', '/api/confirm-reported':'confirm', '/api/analyze-narrative':'analyze'};
  if (!operations[path]) throw new Error('Operação não disponível nesta versão pública.');
  return request(operations[path], {payload});
}

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>'"]/g, (char) => ({"&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;"}[char]));
}

function documentText(record) {
  if (!record) return 'Referência indicada; o conteúdo não foi disponibilizado nesta distribuição pública.';
  return [record.texto || record.trecho || record.aviso_publicacao || 'Texto não disponibilizado nesta distribuição pública; consulte a fonte.', record.localizacao_publica ? `Localização: ${record.localizacao_publica}.` : ''].filter(Boolean).join(' ');
}

function contributionLabel(status) {
  const labels = {
    PRESERVADO_DO_RELATO: "Preservado do relato",
    ACRESCENTADO_PELA_MADO: "Acrescentado pelo conhecimento recuperado",
    CONDICIONAL_POR_FUNCAO_E_ACESSIBILIDADE: "Usar somente quando cumprir a função e estiver acessível",
    CONDICIONAL_POR_FUNCAO_E_FEEDBACK: "Usar somente quando cumprir a função e oferecer feedback",
    CONFIGURACAO_MATURA_RC4: "Configuração completa",
    RECUPERADO_DE_ESTUDO_ANTERIOR: "Recuperado da base",
  };
  return labels[status] || String(status || "").replaceAll("_", " ").toLowerCase();
}

function availabilityLabel(status) {
  return ({
    CONFIRMADO_DISPONIVEL: "Recurso confirmado",
    CONDICIONAL_A_CONFIRMACAO: "Confirmar o recurso antes de usar",
    DISPONIVEL_CONFIRMADO: "Disponível",
    NAO_CONFIRMADO: "A confirmar",
    PROPOSTO_A_PREPARAR: "Proposto, ainda a preparar",
    REQUER_PREPARACAO: "Requer preparação da adaptação",
    IMPEDIDO: "Não pode ser usado",
  })[status] || String(status || "").replaceAll("_", " ").toLowerCase();
}

function resourceStatusClass(status) {
  if (status === "IMPEDIDO") return "blocked";
  return status === "DISPONIVEL_CONFIRMADO" ? "available" : "unknown";
}

function resourceStatusText(resource) {
  const state = resource.estado || "NAO_CONFIRMADO";
  const status = state === "NAO_CONFIRMADO" ? "Disponibilidade não informada" : availabilityLabel(state);
  return `${resource.opcional ? "Opcional; " : ""}${status}`;
}

function renderResourceOption(resource) {
  return `${escapeHtml(resource.label)} <span class="resource-state ${resourceStatusClass(resource.estado)}">${escapeHtml(resourceStatusText(resource))}</span>`;
}

function list(selector, values, empty = "Nenhum item informado.") {
  const element = $(selector);
  element.innerHTML = (values?.length ? values : [empty]).map((value) => `<li>${escapeHtml(value)}</li>`).join("");
}

function summaryCard(label, values, empty = "Não informado.") {
  const content = Array.isArray(values) ? values : [values];
  return `<article><h3>${escapeHtml(label)}</h3>${content.filter(Boolean).length ? content.filter(Boolean).map((value) => `<p>${escapeHtml(value)}</p>`).join("") : `<p>${escapeHtml(empty)}</p>`}</article>`;
}

function contextCards(context) {
  const blocked = context.recursos_impedidos || [];
  const blockedSummary = blocked.length ? [
    ...blocked, ...(context.impedimentos_verificados ? [] : ["Outros impedimentos ainda não foram verificados."]),
  ] : [context.impedimentos_verificados ? "Nenhum impedimento confirmado após verificação." : "Não informado: os impedimentos ainda não foram verificados."];
  const participants = (context.participantes || []).map((person) => {
    const tasks = (person.tarefas || []).join("; ") || "atividade não atribuída";
    const resources = (person.recursos_operados || []).join("; ") || "operação de dispositivos e apoios não atribuída";
    const modes = (person.modalidades || []).join("; ") || "formas de interação não atribuídas";
    return `${person.papel || "Papel não informado"}. Atividade: ${tasks}. Opera: ${resources}. Interage por: ${modes}.`;
  });
  return [
    summaryCard("Características relevantes da pessoa", context.caracteristicas_relevantes),
    summaryCard("Participantes e responsabilidades", participants),
    summaryCard("Atividade", context.tarefas),
    summaryCard("Objetivo", context.objetivo),
    summaryCard("Dificuldade observada", context.barreiras),
    summaryCard("O que precisa ser apoiado", context.necessidades),
    summaryCard("O que a orientação precisa garantir (requisitos a conferir)", context.funcoes_requeridas),
    summaryCard("Formas de interação", context.modalidades_disponiveis),
    summaryCard("Aplicativo ou conteúdo utilizado", context.recursos_digitais),
    summaryCard("Como o aplicativo ou conteúdo é operado", context.operacao_do_recurso),
    summaryCard("Dispositivos e apoios disponíveis", context.recursos_disponiveis),
    summaryCard("Recursos propostos (a preparar)", context.recursos_propostos),
    summaryCard("Recursos que não podem ser usados", blockedSummary),
    summaryCard("Condições ou restrições importantes", context.restricoes),
    summaryCard("Onde ocorre", context.ambientes),
  ].join("");
}

function fieldLabels(field, identifiers) {
  const labels = new Map((catalog.concepts[fieldConfig[field][0]] || []).map((item) => [item.id, item.label]));
  return identifiers.map((id) => labels.get(id) || id);
}

function refreshFieldPreview(containerSelector, field) {
  const details = $(`${containerSelector} details[data-group="${field}"]`);
  if (!details) return;
  const values = checkedValues(containerSelector, field);
  const labels = fieldLabels(field, values);
  details.querySelector(".count").textContent = `(${values.length})`;
  details.querySelector(".selection-preview").textContent = labels.length ? labels.slice(0, 3).join("; ") + (labels.length > 3 ? ` e mais ${labels.length - 3}` : "") : "Nenhuma opção marcada";
}

function draftContext(free) {
  const source = currentCase.context;
  const raw = gatherContext(free ? "#free-controlled-fields" : "#controlled-fields", free);
  const context = {...source, ...raw, raw};
  Object.keys(fieldConfig).forEach((field) => { context[field] = fieldLabels(field, raw[field]); });
  context.caracteristicas_relevantes = context.caracteristicas_pessoa;
  context.funcoes_requeridas = context.funcoes_requeridas_ids;
  let profileUpdated = false;
  context.participantes = (source.participantes || []).map((person) => {
    // Remove obsolete assignments without inventing responsibility for new items.
    const updated = {...person,
      tarefas: (person.tarefas || []).filter((value) => context.tarefas.includes(value)),
      modalidades: (person.modalidades || []).filter((value) => context.modalidades_disponiveis.includes(value)),
      recursos_operados: (person.recursos_operados || []).filter((value) => context.recursos_disponiveis.includes(value)),
    };
    if (!profileUpdated && ["PAPEL-ESTUDANTE", "PAPEL-PESSOA-APOIADA"].includes(person.papel_id)) {
      updated.caracteristicas = raw.caracteristicas_pessoa.map((id, index) => ({id, label: context.caracteristicas_relevantes[index]}));
      profileUpdated = true;
    }
    return updated;
  });
  return context;
}

function refreshDraftPreview(free) {
  const context = draftContext(free);
  $(free ? "#free-summary" : "#context-summary").innerHTML = contextCards(context);
  if (!free) $("#organized-text").textContent = context.descricao_do_contexto;
  const assumptions = context.premissas_do_exemplo || [];
  const target = free ? "#free-assumptions" : "#known-assumptions";
  $(target).hidden = !assumptions.length;
  list(`${target} ul`, assumptions);
}

function draftChanged(free) {
  invalidateDecision(free);
  refreshDraftPreview(free);
}

function showResourceReview(free, visible) {
  const notice = $(free ? "#free-resource-review" : "#known-resource-review");
  notice.hidden = !visible;
  notice.textContent = visible ? "Confira também a descrição, a forma de operação e as modalidades: a mudança de recursos não reescreve esses campos automaticamente." : "";
}

function renderReported() {
  const reported = catalog.reported;
  $("#reported-text").textContent = reported.texto_curto;
  $("#reported-summary").innerHTML = [
    summaryCard("Pessoa", reported.caracteristicas_relevantes),
    summaryCard("Como participava", [...reported.modalidades_disponiveis, ...reported.tarefas]),
    summaryCard("O que precisava ser preservado", reported.necessidades),
    summaryCard("Contexto", reported.ambientes),
  ].join("");
}

function checkedValues(container, field) {
  return $$(`${container} input[data-field="${field}"]:checked`).map((input) => input.value);
}

function buildControlledFields(containerSelector, raw, prefix) {
  const container = $(containerSelector);
  container.innerHTML = "";
  Object.entries(fieldConfig).forEach(([field, [type, question]]) => {
    const selected = new Set(raw?.[field] || []);
    const all = catalog.concepts[type] || [];
    const options = all
      .filter((item) => type === "FUNCAO_DECISORIA" || (item.curated && (prefix !== "outro_caso" || item.scope !== "CASO_ENTREVISTA")) || selected.has(item.id)
        || (resourceFields.includes(field) && resourceFields.some((other) => (raw?.[other] || []).includes(item.id))))
      .sort((a, b) => {
        const selectedDifference = Number(selected.has(b.id)) - Number(selected.has(a.id));
        if (selectedDifference) return selectedDifference;
        return (a.order || 500) - (b.order || 500) || a.label.localeCompare(b.label, "pt-BR");
      });
    const details = document.createElement("details");
    details.className = "controlled";
    details.setAttribute("data-group", field);
    const selectedLabels = options.filter((item) => selected.has(item.id)).map((item) => item.label);
    const preview = selectedLabels.length ? selectedLabels.slice(0, 3).join("; ") + (selectedLabels.length > 3 ? ` e mais ${selectedLabels.length - 3}` : "") : "Nenhuma opção marcada";
    const help = type === "FUNCAO_DECISORIA" ? '<p class="field-help">Marque somente os requisitos pertinentes ao caso. São requisitos estruturados para conferência; não são transcrição literal nem interpretação automática completa.</p>' : "";
    details.innerHTML = `<summary><span>${escapeHtml(question)} <span class="count">(${selected.size})</span></span><small class="selection-preview">${escapeHtml(preview)}</small></summary>${help}<div class="choices"></div>`;
    const choices = details.querySelector(".choices");
    const categories = new Map();
    options.forEach((item) => {
      const category = type === "FUNCAO_DECISORIA"
        ? Object.entries(functionCategories).find(([, identifiers]) => identifiers.includes(item.id))?.[0] || "Outros requisitos"
        : item.category_label || "Outras opções";
      if (!categories.has(category)) categories.set(category, []);
      categories.get(category).push(item);
    });
    categories.forEach((items, category) => {
      const group = document.createElement("section");
      group.className = "choice-group";
      group.setAttribute("aria-label", category);
      group.innerHTML = `<h4>${escapeHtml(category)}</h4>`;
      items.forEach((item) => {
        const label = document.createElement("label");
        label.title = item.description || item.technical_label || "";
        label.innerHTML = `<input type="checkbox" data-field="${field}" value="${escapeHtml(item.id)}" ${selected.has(item.id) ? "checked" : ""}> <span>${escapeHtml(item.label)}</span>${item.description ? `<small>${escapeHtml(item.description)}</small>` : ""}`;
        group.append(label);
      });
      choices.append(group);
    });
    choices.addEventListener("change", (eventObject) => {
      const input = eventObject.target;
      if (input.checked && resourceFields.includes(field)) {
        resourceFields.filter((other) => other !== field).forEach((other) => {
          const oppositeInput = container.querySelector(`input[data-field="${other}"][value="${CSS.escape(input.value)}"]`);
          if (oppositeInput) oppositeInput.checked = false;
        });
      }
      (resourceFields.includes(field) ? resourceFields : [field]).forEach((changed) => refreshFieldPreview(containerSelector, changed));
      draftChanged(prefix === "outro_caso");
      if (resourceFields.includes(field)) showResourceReview(prefix === "outro_caso", true);
    });
    container.append(details);
  });
}

function renderKnownContext() {
  const context = currentCase.context;
  showResourceReview(false, false);
  $("#organized-text").textContent = context.texto_curto;
  $("#context-description").value = context.texto_curto || "";
  $("#objective").value = context.objetivo || "";
  $("#restrictions").value = (context.restricoes || []).join("\n");
  $("#operation").value = context.operacao_do_recurso || "";
  $("#impediments-verified").checked = Boolean(context.impedimentos_verificados);
  $("#mapping-confirmed").checked = currentCase.mapping_confirmed;
  buildControlledFields("#controlled-fields", context.raw, "caso_entrevista");
  refreshDraftPreview(false);
}

function gatherContext(container, free = false) {
  const raw = {};
  Object.keys(fieldConfig).forEach((field) => { raw[field] = checkedValues(container, field); });
  return {
    ...raw,
    descricao_do_contexto: free ? $("#free-narrative").value.trim() : $("#context-description").value.trim(),
    objetivo: free ? $("#free-objective").value.trim() : $("#objective").value.trim(),
    restricoes: $(free ? "#free-restrictions" : "#restrictions").value.split("\n").map((value) => value.trim()).filter(Boolean),
    operacao_do_recurso: $(free ? "#free-operation" : "#operation").value.trim(),
    impedimentos_verificados: $(free ? "#free-impediments-verified" : "#impediments-verified").checked,
    mapping_confirmed: free ? $("#free-confirmed").checked : $("#mapping-confirmed").checked,
    transfer_confirmed: !free,
    input_modality: "text",
  };
}

function renderFreeInterpretation(interpretation) {
  const fields = interpretation.fields;
  showResourceReview(true, false);
  $("#free-objective").value = fields.objetivo || "";
  $("#free-restrictions").value = (currentCase.context.restricoes || []).join("\n");
  $("#free-operation").value = currentCase.context.operacao_do_recurso || "";
  $("#free-impediments-verified").checked = Boolean(currentCase.context.impedimentos_verificados);
  renderMissingQuestions(interpretation.missing_questions || []);
  buildControlledFields("#free-controlled-fields", currentCase.context.raw, "outro_caso");
  refreshDraftPreview(true);
  $("#free-confirmed").checked = false;
  $("#free-status").textContent = "Confira a organização antes de construir a orientação.";
  $("#free-interpretation").hidden = false;
  $("#free-interpretation").open = true;
  $("#free-interpretation").scrollIntoView({behavior: scrollBehavior(), block: "start"});
}

function renderMissingQuestions(questions) {
  const missing = questions.map((item) => typeof item === "string" ? item : item.question).filter(Boolean);
  $("#free-missing").hidden = !missing.length;
  list("#free-missing ul", missing);
}

function renderTemplates() {
  const select = $("#template-select");
  // Rótulos históricos preservados para corresponder às capturas da tese.
  // Estes nomes são apresentação; não participam da recuperação ou decisão.
  const previousLabels = {
    "CTX-DEMO-MOB-RUIDO": "Pessoa cega acompanha orientação por smartphone em ambiente físico ruidoso.",
    "CTX-DEMO-WEB-LEITOR-TELA": "Pessoa cega acessa conteúdo educacional com elementos visuais sem representação adequada.",
    "CTX-DEMO-COMUNICACAO-MULTIFORMATO": "Pessoa utiliza canal de mensagens de um AVA e necessita alternativas ao canal exclusivamente textual.",
  };
  select.innerHTML = '<option value="">Selecione…</option>' + catalog.templates.slice(1).map((item) => {
    const currentLabel = item.titulo_curto || item.texto_curto;
    const label = previousLabels[item.id] ? `${previousLabels[item.id]} (${currentLabel})` : currentLabel;
    return `<option value="${escapeHtml(item.id)}">${escapeHtml(label)}</option>`;
  }).join("");
}

function renderCriteria(rows) {
  $("#criteria").innerHTML = rows.length ? rows.map((row) => `<article><h4>${escapeHtml(row.id)}</h4><p>${escapeHtml(row.enunciado)}</p><p><strong>Conhecimentos empregados:</strong> ${escapeHtml(row.fundamentado_por.join(", "))}</p><p><strong>Por que se aplica aqui:</strong> ${escapeHtml(row.justificativa)}</p><details><summary>Ver origens documentais</summary><ul>${(row.origens_detalhadas || []).map((origin) => `<li><strong>${escapeHtml(origin.id)}</strong> — ${escapeHtml(documentText(origin))} <small>(${escapeHtml(origin.fonte_id)}; ${escapeHtml(origin.trecho_id)})</small></li>`).join("")}</ul></details></article>`).join("") : "<p>Nenhum critério aplicado.</p>";
}

function renderKnowledge(rows) {
  $("#knowledge").innerHTML = rows.length ? rows.map((row) => `<details><summary><strong>${escapeHtml(row.id)}</strong> — ${escapeHtml(row.enunciado)}</summary><p><strong>Articulação:</strong> ${escapeHtml(row.articulacao)}</p><p><strong>Correspondência:</strong> ${row.matched_by.map((m) => escapeHtml(m.labels.join(", "))).join("; ") || "Princípio geral ligado à tarefa."}</p><p><strong>Trechos:</strong> ${row.trechos.map((x) => escapeHtml(`${x.id}: ${documentText(x)}`)).join(" | ")}</p><p><strong>Fontes:</strong> ${row.fontes.map((x) => escapeHtml(`${x.id}: ${x.titulo}`)).join(" | ")}</p><p><strong>Limite:</strong> ${escapeHtml(row.limite)}</p></details>`).join("") : "<p>Nenhum conhecimento empregado.</p>";
}

function renderDelta(selector, rows, empty) {
  const target = $(selector);
  target.innerHTML = rows.length ? rows.map((row) => `<article class="delta-item"><strong>${escapeHtml(row.modo)}</strong><p>${escapeHtml(row.funcao)}</p><p>${escapeHtml(row.acao)}</p><small>${escapeHtml(contributionLabel(row.contribution_status))}</small></article>`).join("") : `<p>${escapeHtml(empty)}</p>`;
}

// One reading order for the guide and trace, only in "Testar outro caso".
// These are explanatory labels, never inputs to retrieval or composition.
const TRACE_STEPS = [
  {kind: "context", label: "Contexto", description: "O caso confirmado: quem participa, o que precisa fazer, o objetivo, as dificuldades, os recursos e as restrições. Não é apenas o lugar onde a atividade acontece."},
  {kind: "function", label: "Função exigida", description: "O que a orientação precisa garantir nesse caso, como permitir retomar uma informação ou oferecer outra forma de entrada. É um requisito a conferir, não uma modalidade nem uma habilidade atribuída à pessoa."},
  {kind: "articulation", label: "Articulação confirmada", description: "Uma relação documentada que complementa, refina ou limita conhecimentos. Confirmada significa aceita para uso na base; não significa eficácia comprovada em qualquer contexto. O agente consulta essa relação, não a inventa."},
  {kind: "knowledge", label: "Conhecimento", description: "Uma compreensão registrada na pesquisa, com fundamentos, condições e limites de aplicação. Pode sustentar uma escolha para o caso; não é apenas a lista de documentos consultados."},
  {kind: "criterion", label: "Critério", description: "Um direcionamento ou cuidado que orienta a escolha e o uso dos modos e recursos. Só contribui quando é aplicável ao caso; não produz uma decisão sozinho."},
  {kind: "criterion_origin", label: "Origem do critério", description: "O registro documental que explica de onde veio o critério e qual item o fundamenta. Não é um critério novo; é parte de sua rastreabilidade."},
  {kind: "configuration", label: "Configuração multimodal", description: "Uma parte concreta da orientação: qual modo usar, para quê, com qual recurso, por quem e em quais condições. As configurações selecionadas compõem a decisão e explicitam alternativas e acompanhamento; cada cartão pode tratar de um modo dessa combinação."},
  {kind: "source", label: "Fonte", description: "O documento ou registro que sustenta o conhecimento ou a origem de um critério. Permite conferir o fundamento; sua presença não comprova que a orientação já foi aplicada com sucesso."},
];
const originalTraceOrder = $("#trace-reading-order").textContent;
const originalDeparaOrder = $("#depara-reading-order").textContent;

function renderRationaleGuide() {
  $("#free-rationale-terms").innerHTML = TRACE_STEPS.map((step) => `<li data-trace-kind="${step.kind}"><strong>${escapeHtml(step.label)}</strong><p>${escapeHtml(step.description)}</p></li>`).join("");
}

function traceDetailPresenter(result, graph) {
  const byId = new Map((graph.nodes || []).map((node) => [node.id, node]));
  const knowledge = new Map((result.traceability?.knowledge || []).map((row) => [row.id, row]));
  const criteria = new Map((result.traceability?.criteria || []).map((row) => [row.id, row]));
  const articulations = new Map((result.articulations_used || []).map((row) => [row.id, row]));
  const concepts = new Map(Object.values(catalog?.concepts || {}).flat().map((row) => [row.id, row]));
  const sources = new Map([...knowledge.values()].flatMap((row) => row.fontes || []).map((row) => [row.id, row]));
  const excerpts = new Map([...knowledge.values()].flatMap((row) => row.trechos || []).map((row) => [row.id, row]));
  const origins = new Map();
  for (const criterion of criteria.values()) {
    for (const origin of criterion.origens_detalhadas || []) {
      const entry = origins.get(origin.id) || {...origin, criteria: []};
      entry.criteria.push(criterion);
      origins.set(origin.id, entry);
    }
  }
  const configurations = result.decision?.configuracao_modal || [];
  // Same explicit ID contract as build_decision_graph; never match by mode label.
  const configurationById = new Map(configurations.map((item, index) => [`CFG-${result.decision.id}-${String(index + 1).padStart(2, "0")}`, item]));
  const text = (value) => Array.isArray(value) ? value.filter(Boolean).join("; ") : value;
  const field = (label, value, absent = "Não informado neste retorno.") => `<div class="trace-field"><strong>${escapeHtml(label)}</strong><p>${escapeHtml(text(value) || absent)}</p></div>`;
  const name = (id) => {
    const label = knowledge.get(id)?.enunciado || criteria.get(id)?.enunciado || articulations.get(id)?.rotulo || sources.get(id)?.titulo || concepts.get(id)?.label || byId.get(id)?.label;
    return label ? `${id} — ${label}` : `${id} — descrição não incluída neste retorno`;
  };
  const refs = (ids) => (ids || []).map(name);
  const originContent = (origin) => origin
    ? `${field("Critério ao qual este registro está ligado", origin.criteria.map((row) => `${row.id} — ${row.enunciado}`))}<div class="trace-field"><strong>Texto do item documental registrado na base</strong><p class="trace-origin-text">${escapeHtml(documentText(origin))}</p></div>${field("Fonte", origin.fonte_id ? name(origin.fonte_id) : null)}${field("Identificador do trecho", origin.trecho_id)}${field("Página, seção ou item na fonte", origin.localizacao_publica || origin.localizacao || origin.pagina || origin.secao, "Localização não fornecida neste retorno. O ID do trecho não substitui a página ou a seção da fonte.")}`
    : field("Conteúdo documental", null, "O grafo retornou o identificador, mas não incluiu o texto desta origem. Não foi preenchido por suposição.");
  const configurationContent = (item) => `${field("Função desta modalidade", item.funcao)}${field("Como usar", item.acao)}${field("Responsável indicado", item.responsavel)}<div class="trace-field"><strong>Recursos e disponibilidade</strong><p>${(item.resource_options || []).map(renderResourceOption).join("; ") || "Recursos não detalhados neste retorno."}</p></div>${field("Aplicar quando", item.conditions)}${field("Alternativa", item.alternative)}${field("Como acompanhar", item.monitoring)}${field("Limite", item.limit)}`;
  const articulationContent = (row) => `${field("Relação documentada", row.rotulo)}${field("Conhecimentos de entrada", refs(row.conhecimento_entrada_ids))}${field("Conhecimentos resultantes declarados nesta articulação", refs(row.conhecimento_resultante_ids))}${field("Condição", row.condicao)}${field("Limite", row.limite)}${field("Fontes", refs(row.fonte_ids))}${field("Trechos indicados pela articulação", (row.trecho_ids || []).map((id) => `${id} — ${documentText(excerpts.get(id))}`))}${field("Origem e nível de confirmação na base", [row.origem_relacao, row.nivel_confirmacao])}`;
  const record = (node) => {
    let body;
    if (node.kind === "criterion_origin") body = originContent(origins.get(node.id));
    else if (node.kind === "context" && result.context?.id === node.id) body = `${field("Descrição confirmada nesta execução", result.context.texto_curto)}${field("Objetivo", result.context.objetivo)}${field("Dificuldades", result.context.barreiras)}${field("Restrições", result.context.restricoes)}`;
    else if (node.kind === "knowledge" && knowledge.has(node.id)) {
      const row = knowledge.get(node.id);
      body = `${field("Conhecimento registrado", row.enunciado)}${field("Como o conhecimento foi articulado", row.articulacao)}${field("Correspondências registradas com o caso", (row.matched_by || []).flatMap((match) => match.labels || []), "Nenhuma correspondência direta descrita neste retorno; confira sua mobilização por configuração.")}${field("Trechos recuperados", (row.trechos || []).map((excerpt) => `${excerpt.id} — ${documentText(excerpt)}`))}${field("Fontes do conhecimento", (row.fontes || []).map((source) => `${source.id} — ${source.titulo}`))}${field("Limite de aplicação", row.limite)}`;
    } else if (node.kind === "articulation" && articulations.has(node.id)) body = articulationContent(articulations.get(node.id));
    else if (node.kind === "criterion" && criteria.has(node.id)) {
      const row = criteria.get(node.id);
      body = `${field("Enunciado do critério", row.enunciado)}${(row.situated_support || []).map((support) => field(`Uso na configuração ${support.component_id}`, support.justification)).join("")}${field("Origens documentais usadas", row.origens_documentais)}`;
    } else if (node.kind === "configuration" && configurationById.has(node.id)) body = configurationContent(configurationById.get(node.id));
    else if (node.kind === "function") body = `${field("O que precisa ser garantido", node.label)}${field("Como aparece nesta orientação", configurations.filter((item) => (item.function_ids || []).includes(node.id)).map((item) => `${item.modo}: ${item.funcao}`), "Nenhuma configuração com esta função foi detalhada no retorno.")}`;
    else if (node.kind === "source") body = `${field("Documento ou registro", sources.get(node.id)?.titulo || node.label)}${field("Itens de origem ligados a esta fonte", [...origins.values()].filter((origin) => origin.fonte_id === node.id).map((origin) => `${origin.id}: ${origin.texto}`), "Nenhum item de origem desta fonte foi detalhado nesta resposta.")}${field("Localização no documento", null, "Página, seção e versão não foram fornecidas neste retorno.")}`;
    else body = field("Descrição retornada", node.label);
    return `<div class="trace-record-body">${body}</div>`;
  };
  const walkthrough = () => configurations.length ? `<section class="trace-config-walkthrough" aria-labelledby="trace-choices-title"><div class="title-row"><h3 id="trace-choices-title">Por que estas escolhas?</h3><button id="collapse-trace-blocks" class="secondary" type="button">Recolher estes blocos</button></div><p>Abra uma escolha por vez para ver o motivo e os fundamentos usados neste caso.</p><div class="trace-config-cards">${configurations.map((item) => {
    const supports = [...criteria.values()].flatMap((criterion) => (criterion.situated_support || []).filter((support) => support.component_id === item.component_id).map((support) => ({criterion, support})));
    return `<details class="trace-config-card"><summary><span class="trace-choice-title">${escapeHtml(item.modo)}</span><span class="trace-choice-function">${escapeHtml(item.funcao)}</span></summary><div class="trace-choice-body">${field("Por que foi indicada", item.functional_meaning)}${configurationContent(item)}<details class="trace-choice-evidence"><summary>Conferir os fundamentos desta escolha</summary>${field("Condições consideradas nesta escolha", refs(item.condition_ids))}${field("Conhecimentos mobilizados", refs(item.knowledge_ids))}<div class="trace-field"><strong>Como os conhecimentos se complementam</strong>${(item.articulation_ids || []).map((id) => { const row = articulations.get(id); return row ? `<p><strong>${escapeHtml(name(id))}</strong></p>${field("Conhecimentos resultantes declarados e usados nesta escolha", refs((row.conhecimento_resultante_ids || []).filter((kid) => (item.knowledge_ids || []).includes(kid))))}${field("Condição da relação", row.condicao)}${field("Limite da relação", row.limite)}` : field("Articulação", name(id)); }).join("") || '<p>Nenhuma articulação foi indicada para esta configuração.</p>'}</div><div class="trace-field"><strong>Por que os critérios foram usados aqui</strong>${supports.length ? supports.map(({criterion, support}) => `<section class="trace-situated-support"><p><strong>${escapeHtml(criterion.id)} — ${escapeHtml(criterion.enunciado)}</strong></p>${field("Justificativa registrada para esta configuração", support.justification)}${field("Conhecimentos que sustentam este uso", refs(support.knowledge_ids))}<details><summary>Consultar os textos de origem de ${escapeHtml(criterion.id)}</summary>${(support.origin_ids || []).map((id) => `<div class="trace-origin-record"><p><strong>${escapeHtml(id)}</strong></p>${originContent(origins.get(id))}</div>`).join("") || '<p>Não foram retornadas origens para este uso.</p>'}</details></section>`).join("") : '<p>Não foi retornada justificativa situada por critério para esta configuração.</p>'}</div><small>Configuração da base: ${escapeHtml(item.component_id)}</small></details></div></details>`;
  }).join("")}</div></section>` : '<p>Nenhuma configuração foi detalhada nesta execução; não há uma explicação por escolha a apresentar.</p>';
  return {record, walkthrough, originContent};
}

function renderFreeTraceGraph(graph, result = {}) {
  const nodes = graph.nodes || [];
  const edges = graph.edges || [];
  const byId = new Map(nodes.map((node) => [node.id, node]));
  const presenter = traceDetailPresenter(result, graph);
  const position = (kind) => { const index = TRACE_STEPS.findIndex((step) => step.kind === kind); return index < 0 ? TRACE_STEPS.length : index; };
  const groups = [...TRACE_STEPS];
  if (nodes.some((node) => !TRACE_STEPS.some((step) => step.kind === node.kind))) {
    groups.push({kind: "other", label: "Outros registros retornados", description: "Tipo ainda sem definição neste guia. O registro é preservado para conferência."});
  }
  $("#trace-reading-order").textContent = `Ordem de leitura: ${TRACE_STEPS.map((step) => step.label).join(" → ")}.`;
  const meanings = {
    context: "Quem participa, o que precisa fazer e em quais condições.",
    function: "O que a orientação precisa garantir para essa tarefa.",
    articulation: "Uma relação registrada que complementa, refina ou limita conhecimentos.",
    knowledge: "Uma compreensão construída na pesquisa que sustenta a escolha.",
    criterion: "Um direcionamento ou cuidado que orienta a escolha dos modos e recursos.",
    criterion_origin: "O texto documental que fundamenta o critério.",
    configuration: "O modo escolhido, sua função, o recurso, o responsável e as condições de uso.",
    source: "O documento ou registro de onde vem o fundamento.",
    other: "Um registro adicional retornado nesta execução.",
  };
  // Explanations of the existing query/composer, not new inference rules.
  // Provenance is deliberately not described as a step that creates a decision.
  const connections = {
    context: ["Contexto → função", "A tarefa, as dificuldades e as necessidades delimitam o que precisa ser garantido, conforme os mapeamentos registrados na base."],
    function: ["Função → busca de articulações", "A função requerida permite buscar relações que acrescentem esse apoio aos conhecimentos recuperados diretamente."],
    articulation: ["Articulação → conhecimento complementar", "A relação habilitada permite recuperar seu conhecimento resultante, já registrado. O agente não cria esse conhecimento durante a consulta."],
    knowledge: ["Conhecimento → critério", "O uso de um critério precisa de conhecimento recuperado, justificativa e origem documental, ligados à mesma configuração."],
    criterion: ["Critério → escolha fundamentada", "Direciona o uso dos modos e recursos. O próximo cartão permite conferir de onde veio esse direcionamento."],
    criterion_origin: ["Origem → conferência do critério", "Mostra o texto que fundamenta o critério. É uma conferência da procedência, não uma etapa que gera a configuração."],
    configuration: ["Configurações → orientação", "As escolhas que atendem às condições do caso e possuem fundamentos compõem a orientação multimodal."],
    source: ["Fonte → sustentação dos fundamentos", "Permite conferir os documentos dos conhecimentos e critérios. A fonte já existia; não é produzida pela orientação."],
    other: ["Registro adicional → conferência", "O retorno preserva este registro, mas não há uma explicação específica de sua ligação neste guia."],
  };
  $("#free-trace-overview").hidden = false;
  $("#free-trace-overview").innerHTML = `<section class="trace-overview" aria-labelledby="trace-overview-title"><h3 id="trace-overview-title">Caminho da orientação</h3><p>As <strong>setas explicam as relações</strong>. A ordem guia a leitura; origem e fonte permitem conferir os fundamentos, não são etapas de criação da resposta. Abra os registros no próprio cartão.</p><ol class="trace-sequence">${groups.map((step, index) => {
    const items = nodes.filter((node) => step.kind === "other" ? position(node.kind) === TRACE_STEPS.length : node.kind === step.kind);
    const [connection, explanation] = connections[step.kind];
    return `<li class="trace-step" data-trace-kind="${step.kind}"><div class="trace-step-heading"><span class="trace-step-number">${index + 1}</span><strong>${escapeHtml(step.label)}</strong></div><p class="trace-step-meaning">${escapeHtml(meanings[step.kind])}</p><p class="trace-step-connection"><strong>${escapeHtml(connection)}</strong> ${escapeHtml(explanation)}</p><details class="trace-step-records"><summary>${items.length} ${items.length === 1 ? "registro" : "registros"} · Conferir ${escapeHtml(step.label.toLocaleLowerCase("pt-BR"))}</summary><div class="trace-step-records-body">${items.length ? `<ul>${items.map((node) => `<li><details class="trace-record"><summary>${escapeHtml(node.kind === "context" ? "Caso confirmado nesta execução" : node.label)}</summary><small>Identificador: ${escapeHtml(node.id)}</small>${presenter.record(node)}</details></li>`).join("")}</ul>` : '<p class="field-help">Nenhum registro deste tipo foi retornado nesta execução.</p>'}</div></details></li>`;
  }).join("")}</ol></section>`;
  const groupedArticulations = edges.some((edge) => edge.label === "produz/refina" && byId.get(edge.source)?.kind === "articulation");
  $("#free-trace-explanation").innerHTML = presenter.walkthrough();
  $("#free-trace-explanation").hidden = false;
  $("#collapse-trace-blocks")?.addEventListener("click", () => {
    if (activeTab !== "free") return;
    $("#trace-details").querySelectorAll("details").forEach((detail) => { detail.open = false; });
    $("#collapse-trace-blocks").focus();
    $("#free-reading-status").textContent = "Escolhas e registros recolhidos.";
  });
  // Records live in the overview cards. Do not repeat a library below them.
  $("#trace-graph").innerHTML = "";
  const endpoint = (id) => {
    const node = byId.get(id);
    const label = node?.kind === "context" ? "Caso confirmado nesta execução" : node?.label;
    return label ? `${escapeHtml(label)}<br><small>${escapeHtml(id)}</small>` : `${escapeHtml(id)} <small>(registro sem rótulo no retorno)</small>`;
  };
  // A stable copy keeps every returned relation and its direction intact.
  const orderedEdges = edges.map((edge, index) => ({edge, index})).sort((a, b) => position(byId.get(a.edge.source)?.kind) - position(byId.get(b.edge.source)?.kind) || a.index - b.index);
  $("#trace-table").innerHTML = orderedEdges.length ? `<details class="foundation trace-relations"><summary>Consultar as ligações técnicas <span class="trace-summary-meta">${orderedEdges.length} ligações entre os registros</span></summary>${groupedArticulations ? '<p class="trace-relation-note"><strong>Sobre estas ligações:</strong> alguns registros aparecem juntos porque foram usados na mesma escolha. Isso não significa que um tenha dado origem ao outro. Para conferir essa origem, abra os registros no cartão Articulação confirmada. Na tabela, essas ligações mantêm o nome técnico “produz/refina”.</p>' : ''}<div class="table-scroll rationale-relations"><table><caption>Ligações retornadas pela consulta — agrupadas pelo elemento de origem</caption><thead><tr><th scope="col">Origem</th><th scope="col">Relação registrada</th><th scope="col">Destino</th></tr></thead><tbody>${orderedEdges.map(({edge}) => `<tr><td>${endpoint(edge.source)}</td><td>${escapeHtml(edge.label)}</td><td>${endpoint(edge.target)}</td></tr>`).join("")}</tbody></table></div></details>` : '<p>Nenhuma ligação foi retornada nesta execução. A lista acima explica os conceitos, mas não representa uma cadeia comprovada para este caso.</p>';
}

function renderTraceGraph(graph, result = {}) {
  if (activeTab === "free") { renderFreeTraceGraph(graph, result); return; }
  $("#trace-reading-order").textContent = originalTraceOrder;
  $("#free-trace-overview").hidden = true;
  $("#free-trace-overview").innerHTML = "";
  $("#free-trace-explanation").hidden = true;
  $("#free-trace-explanation").innerHTML = "";
  const kindLabels = {context: "Contexto", function: "Função exigida", articulation: "Articulação", knowledge: "Conhecimento", criterion: "Critério", criterion_origin: "Origem do critério", configuration: "Configuração", source: "Fonte"};
  $("#trace-graph").innerHTML = `<div class="semantic-graph">${graph.nodes.map((node) => `<article class="graph-node ${node.kind}"><small>${kindLabels[node.kind]}</small><span>${escapeHtml(node.label)}</span></article>`).join("")}</div>`;
  $("#trace-table").innerHTML = `<table><caption>Relações usadas na orientação</caption><thead><tr><th>Origem</th><th>Relação</th><th>Destino</th></tr></thead><tbody>${graph.edges.map((edge) => `<tr><td>${escapeHtml(edge.source)}</td><td>${escapeHtml(edge.label)}</td><td>${escapeHtml(edge.target)}</td></tr>`).join("")}</tbody></table>`;
}

function renderComparison(result) {
  const comparison = result.articulation_comparison || {};
  const isolated = comparison.isolated || {};
  const articulated = comparison.articulated || {};
  $("#isolated-comparison").innerHTML = `<p><strong>${(isolated.knowledge_ids || []).length}</strong> conhecimentos caracterizam o caso, mas cobrem <strong>${(isolated.covered_function_ids || []).length}</strong> funções por configurações completas.</p><p>${(isolated.remaining_function_ids || []).length ? `${escapeHtml(isolated.remaining_function_ids.length)} funções ainda ficam sem cobertura operacional.` : "As funções foram cobertas."}</p>`;
  $("#articulated-comparison").innerHTML = `<p><strong>${(comparison.added_knowledge_ids || []).length}</strong> conhecimentos foram acrescentados por <strong>${(comparison.articulation_ids || []).length}</strong> relações documentadas.</p><p>A configuração passa a usar: ${escapeHtml((articulated.modalities || []).join(", ") || "nenhuma modalidade")}. Foram construídos ${(articulated.component_ids || []).length} componentes aplicáveis.</p>`;
}

function renderDePara(rows) {
  const target = $("#depara-table");
  $("#depara-reading-order").textContent = activeTab === "free"
    ? "Leia as colunas na ordem: condição do caso → o que ela significa → o que precisa ser garantido → como foi configurado → alternativa e limite. A fundamentação está em Ver o caminho completo da orientação."
    : originalDeparaOrder;
  if (!rows?.length) {
    target.innerHTML = activeTab === "free"
      ? "<p>Esta execução não retornou uma matriz de transformação das condições. Isso, isoladamente, não informa o motivo: confira o estado da decisão, as lacunas e o caminho da orientação.</p>"
      : "<p>O de/para não foi produzido porque a decisão foi suspensa ou não se trata do cenário de transferência.</p>";
    return;
  }
  target.innerHTML = `<div class="table-scroll"><table><caption>Transformações usadas na orientação</caption><thead><tr><th>Condição</th><th>O que ela significa</th><th>O que precisa ser garantido</th><th>Como foi configurado</th><th>Alternativa e limite</th></tr></thead><tbody>${rows.map((row) => `<tr><td>${escapeHtml(row.condicoes.join("; "))}</td><td>${escapeHtml(row.abstracao_funcional)}</td><td>${escapeHtml(row.implicacao_decisoria)}</td><td>${row.configuracao_multimodal.map((item) => `<strong>${escapeHtml(item.modo)}</strong>: ${escapeHtml(item.funcao)} <small>(${escapeHtml(item.responsavel)})</small>`).join("<br>")}</td><td>${escapeHtml(row.alternativa)}<br><small>${escapeHtml(row.condicao_limite)}</small></td></tr>`).join("")}</tbody></table></div>`;
}

function renderPracticalSummary(decision) {
  const summary = decision.sintese_pratica || {
    titulo: "Sugestão para este caso",
    texto: decision.orientacao_principal,
    etapas: [],
    component_ids: decision.component_ids || [],
  };
  $("#practical-title").textContent = summary.titulo;
  $("#practical-headline").textContent = summary.texto;
  $("#practical-steps").innerHTML = (summary.etapas || []).map((step) => {
    const items = step.itens || [];
    const structuredResources = Array.isArray(step.recursos_estruturados) ? step.recursos_estruturados
      : (step.recursos || []).map((label) => ({label, estado: "NAO_CONFIRMADO"}));
    const resources = structuredResources.filter((resource) => resource.estado !== "IMPEDIDO").map(renderResourceOption).join("; ");
    const preparation = (step.estado_recurso || []).map(availabilityLabel).join("; ");
    const modes = (step.modos || []).map((mode) => `<span class="mode-pill">${escapeHtml(mode)}</span>`).join("");
    const actions = items.length > 1
      ? `<ul>${items.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul>`
      : `<p>${escapeHtml(items[0] || "")}</p>`;
    const details = [
      ...(step.condicoes || []).map((value) => `<p><strong>Usar quando:</strong> ${escapeHtml(value)}</p>`),
      ...(step.alternativas || []).map((value) => `<p><strong>Se não puder usar:</strong> ${escapeHtml(value)}</p>`),
      ...(step.acompanhamento || []).map((value) => `<p><strong>Observar:</strong> ${escapeHtml(value)}</p>`),
    ].join("");
    return `<article class="practical-step"><div class="mode-pills">${modes}</div><h4>${escapeHtml(step.titulo)}</h4><p><strong>Função:</strong> ${escapeHtml(step.funcao || "")}</p><p><strong>Como se complementa:</strong> ${escapeHtml(step.como_combinar || "")}</p>${actions}<p class="availability"><strong>Recursos:</strong> ${resources || "sem recurso específico"}${preparation ? `<br><strong>Situação da adaptação:</strong> ${escapeHtml(preparation)}` : ""}</p>${details ? `<details class="summary-more"><summary>Condição, alternativa e acompanhamento</summary>${details}</details>` : ""}</article>`;
  }).join("");
  $("#expected-result").textContent = summary.resultado_esperado || decision.resultado_esperado || "";
  $("#expected-result-note").textContent = summary.aviso_resultado || "Este resultado é uma expectativa para acompanhamento, não uma garantia de eficácia.";
}

function setDecisionExpanded(expanded) {
  const show = activeTab === "known" || expanded;
  $("#decision-content").hidden = !show;
  $("#toggle-decision-content").hidden = activeTab !== "free";
  $("#toggle-decision-content").setAttribute("aria-expanded", String(show));
  $("#toggle-decision-content").textContent = show ? "Recolher orientação" : "Mostrar orientação";
}
$("#toggle-decision-content").addEventListener("click", () => {
  if (activeTab !== "free") return;
  setDecisionExpanded($("#decision-content").hidden);
  $("#toggle-decision-content").focus();
});

function renderDecision(result) {
  lastResult = result;
  const decision = result.decision;
  // Depois da confirmação, recolhe as etapas de entrada para que a pessoa
  // chegue diretamente à orientação sem percorrer novamente uma página longa.
  if (activeTab === "known") {
    $("#reported-step").open = false;
    $("#organized-step").open = false;
  } else {
    $("#free-narrative-block").open = false;
    $("#free-interpretation").open = false;
  }
  $("#saida").hidden = false;
  setDecisionExpanded(true);
  $("#decision-status").textContent = decision.status === "GERADA" ? "Orientação construída" : "Decisão suspensa";
  $("#decision-status").classList.toggle("suspended", decision.status !== "GERADA");
  renderPracticalSummary(decision);
  $("#orientation-details").open = false;
  $("#orientation").textContent = decision.orientacao_principal;
  $("#rationale").textContent = decision.justificativa;
  renderComparison(result);
  renderDePara(result.de_para || []);
  $("#modal-configuration").innerHTML = decision.configuracao_modal.map((item) => `<article class="mode-card"><span class="role">${escapeHtml(item.papel_modal)}</span><h3>${escapeHtml(item.modo)}</h3><p><strong>Para quê:</strong> ${escapeHtml(item.funcao)}</p><p><strong>Como usar:</strong> ${escapeHtml(item.acao)}</p><p><strong>Responsável:</strong> ${escapeHtml(item.responsavel)}</p><p><strong>Recursos:</strong> ${(item.resource_options || []).map(renderResourceOption).join("; ") || "sem recurso específico"}</p><details class="mode-more"><summary>Condições, alternativa e acompanhamento</summary><p><strong>Aplicar quando:</strong> ${escapeHtml((item.conditions || []).join(" "))}</p><p><strong>Se não funcionar:</strong> ${escapeHtml(item.alternative)}</p><p><strong>Observar:</strong> ${escapeHtml(item.monitoring)}</p><p><strong>Limite:</strong> ${escapeHtml(item.limit)}</p></details><small>${escapeHtml(contributionLabel(item.contribution_status))} · ${escapeHtml(availabilityLabel(item.availability_status))}</small></article>`).join("");
  list("#resources", decision.recursos);
  list("#conditional-resources", decision.recursos_condicionais, "Nenhum recurso precisa de confirmação.");
  list("#conditions", decision.condicoes);
  list("#alternatives", decision.alternativas);
  list("#monitoring", decision.acompanhamento);
  list("#missing", decision.informacoes_ausentes);
  $("#missing-box").hidden = !decision.informacoes_ausentes.length;
  $("#limit").textContent = decision.limite;
  $("#technical-summary").textContent = `A execução usou ${result.traceability.knowledge.length} conhecimentos, ${result.traceability.criteria.length} critérios, ${result.articulations_used.length} articulações confirmadas e respondeu ${Object.keys(result.query_summary).length} questões de competência.`;
  renderCriteria(result.traceability.criteria);
  renderKnowledge(result.traceability.knowledge);
  $("#rejected").innerHTML = result.traceability.rejected_candidates.length ? `<ul>${result.traceability.rejected_candidates.map((row) => `<li><strong>${escapeHtml(row.label)}</strong>: ${escapeHtml(row.reasons.join("; "))}</li>`).join("")}</ul>` : "<p>Nenhuma possibilidade foi excluída.</p>";
  renderTraceGraph(result.trace_graph, result);
  $("#saida").scrollIntoView({behavior: scrollBehavior(), block: "start"});
  $("#decision-title").focus({preventScroll:true});
}

function showError(target, error) {
  if (target === '#health') $('#health').dataset.state = 'error';
  $(target).textContent = error.message || String(error);
  $(target).classList.add("error-message");
  $('#runtime-error').textContent = error.message || String(error);
}

async function generate(container, free, statusTarget) {
  if (!$(free ? "#free-confirmed" : "#mapping-confirmed").checked) {
    throw new Error("Confira as informações e marque que a organização representa corretamente o caso antes de construir a orientação.");
  }
  if (free && normalizeNarrative($("#free-narrative").value) !== organizedNarrative) {
    throw new Error("A descrição mudou. Clique em Organizar as informações e confirme a nova organização antes de gerar.");
  }
  $(statusTarget).textContent = "Consultando conhecimentos e critérios…";
  const payload = gatherContext(container, free);
  currentCase = await api("/api/context", {method: "POST", body: JSON.stringify(payload)});
  refreshDraftPreview(free);
  if (free) renderMissingQuestions(currentCase.questions || []);
  const result = await api("/api/generate", {method: "POST", body: "{}"});
  renderDecision(result);
  $(statusTarget).textContent = result.decision.status === "GERADA" ? "Orientação pronta." : "A decisão foi suspensa; confira as informações ausentes.";
}

$("#confirm-reported").addEventListener("click", () => runBusy('#reported-status', async () => {
    const selected = $("input[name='reported-confirmation']:checked");
    if (!selected) throw new Error("Escolha como deseja explorar a adaptação pública antes de continuar.");
    currentCase = await api("/api/confirm-reported", {method: "POST", body: JSON.stringify({confirmed: selected.value === "yes", correction: $("#reported-correction").value})});
    $("#reported-status").textContent = "Conferência aplicada somente ao caso aberto, sem gravação.";
    $("#reported-step").open = false;
    $("#organized-step").open = true;
    $("#organized-step").scrollIntoView({behavior: scrollBehavior(), block: "start"});
}));

$("#generate-known").addEventListener("click", () => runBusy("#known-status", () => generate("#controlled-fields", false, "#known-status")));

$("#organize-narrative").addEventListener("click", () => runBusy("#narrative-status", async () => {
    const narrative = normalizeNarrative($("#free-narrative").value);
    if (!narrative) throw new Error("Descreva um caso ou escolha um dos exemplos antes de organizar.");
    $("#narrative-status").textContent = "Organizando as informações…";
    // Um resumo de demonstração não contém toda a caracterização estruturada.
    // Reorganizar texto inalterado deve manter os dados e as correções visíveis,
    // não substituir a sessão completa pelo reconhecimento do resumo.
    if (organizedNarrative === narrative && currentCase) {
      Object.keys(fieldConfig).forEach((field) => refreshFieldPreview("#free-controlled-fields", field));
      refreshDraftPreview(true);
      $("#free-interpretation").hidden = false;
      $("#free-interpretation").open = true;
      $("#narrative-status").textContent = "Organização preservada. Confira as informações e confirme para continuar.";
      return;
    }
    invalidateDecision(true);
    const response = await api("/api/analyze-narrative", {method: "POST", body: JSON.stringify({narrative, input_modality: "text"})});
    currentCase = response.current;
    organizedNarrative = narrative;
    $("#template-select").value = "";
    renderFreeInterpretation(response.interpretation);
    $("#narrative-status").textContent = "Organização pronta para conferência.";
}));

$("#generate-free").addEventListener("click", () => runBusy("#free-status", () => generate("#free-controlled-fields", true, "#free-status")));

$("#template-select").addEventListener("change", (eventObject) => runBusy("#narrative-status", async () => {
  if (!eventObject.target.value) return;
  invalidateDecision(true);
  currentCase = await request('start', {template:eventObject.target.value});
  $("#free-narrative").value = currentCase.context.texto_curto;
  organizedNarrative = normalizeNarrative(currentCase.context.texto_curto);
  renderFreeInterpretation(interpretationFromContext(currentCase));
  $("#narrative-status").textContent = "Exemplo carregado com suas informações completas. Confira e confirme a organização.";
}));

async function switchTab(name) {
  if (name === activeTab) return;
  const known = name === "known";
  clearInputAndResult();
  currentCase = await request('start', {template:known ? INTERVIEW_TEMPLATE : null});
  activeTab = name;
  setDecisionExpanded(true);
  document.body.classList.toggle("free-case-view", !known);
  $("#free-reading-tools").hidden = known;
  $("#free-reading-status").textContent = "";
  $("#known-panel").hidden = !known;
  $("#free-panel").hidden = known;
  $("#known-tab").setAttribute("aria-selected", String(known));
  $("#free-tab").setAttribute("aria-selected", String(!known));
  $("#known-tab").tabIndex = known ? 0 : -1;
  $("#free-tab").tabIndex = known ? -1 : 0;
  $("#saida").hidden = true;
  if (known) renderKnownContext();
  $('#health').dataset.state = 'ready';
  $("#health").textContent = 'Pronto. O caso anterior foi descartado; nada foi salvo.';
}
$("#known-tab").addEventListener("click", () => runBusy("#health", () => switchTab("known")));
$("#free-tab").addEventListener("click", () => runBusy("#health", () => switchTab("free")));
$("#collapse-free-details").addEventListener("click", () => {
  if (activeTab !== "free") return;
  $$("#free-panel details, #saida details").forEach((detail) => { detail.open = false; });
  setDecisionExpanded(false);
  $("#collapse-free-details").focus();
  $("#free-reading-status").textContent = "Detalhes recolhidos. Suas informações e a orientação foram mantidas.";
});
$$('[role="tab"]').forEach((tab) => tab.addEventListener("keydown", async (evt) => {
  if (!["ArrowLeft", "ArrowRight", "Home", "End"].includes(evt.key)) return;
  evt.preventDefault();
  const name = evt.key === "Home" ? "known" : evt.key === "End" ? "free" : activeTab === "known" ? "free" : "known";
  await runBusy("#health", () => switchTab(name));
  $(`#${activeTab}-tab`).focus();
}));

$("#free-narrative").addEventListener("input", () => {
  invalidateDecision(true);
  const changed = normalizeNarrative($("#free-narrative").value) !== organizedNarrative;
  $("#free-interpretation").hidden = changed;
  $("#narrative-status").textContent = changed ? "Descrição alterada. Organize novamente; os dados do exemplo anterior não serão presumidos." : "Confira a organização e confirme novamente.";
});
["#free-objective", "#free-restrictions", "#free-operation"].forEach((selector) => $(selector).addEventListener("input", () => draftChanged(true)));
["#context-description", "#objective", "#restrictions", "#operation"].forEach((selector) => $(selector).addEventListener("input", () => draftChanged(false)));
$("#free-impediments-verified").addEventListener("change", () => draftChanged(true));
$("#impediments-verified").addEventListener("change", () => draftChanged(false));
$("#free-confirmed").addEventListener("change", () => {
  if (!$("#free-confirmed").checked) invalidateDecision(true);
  else showResourceReview(true, false);
});
$("#mapping-confirmed").addEventListener("change", () => {
  if (!$("#mapping-confirmed").checked) invalidateDecision(false);
  else showResourceReview(false, false);
});

function speakLocally(text) {
  if (!('speechSynthesis' in window)) {
    $('#speech-status').textContent = 'Leitura em voz alta indisponível. O conteúdo integral continua em texto.'; return;
  }
  const voice = speechSynthesis.getVoices().find(item => item.localService === true && item.lang.toLowerCase().startsWith('pt'));
  if (!voice) {
    $('#speech-status').textContent = 'Nenhuma voz local em português está disponível. Por privacidade, o AMADO não usa uma voz remota. O texto permanece disponível.'; return;
  }
  speechSynthesis.cancel();
  const utterance = new SpeechSynthesisUtterance(text);
  utterance.voice = voice; utterance.lang = voice.lang;
  utterance.onend = () => { $('#speech-status').textContent = 'Leitura concluída.'; };
  utterance.onerror = () => { $('#speech-status').textContent = 'A leitura foi interrompida. Você pode continuar pelo texto.'; };
  $('#speech-status').textContent = 'Lendo com uma voz local. Use Parar para interromper.';
  speechSynthesis.speak(utterance);
}
$("#speak-button").addEventListener("click", () => {
  if (!lastResult) return;
  const decision = lastResult.decision;
  const summary = decision.sintese_pratica || {};
  const text = [summary.texto || decision.orientacao_principal, ...(summary.etapas || []).flatMap((step) => [step.titulo, `Formas: ${(step.modos || []).join(", ")}.`, `Função: ${step.funcao || ""}.`, `Como se complementam: ${step.como_combinar || ""}.`, ...(step.itens || [])]), summary.resultado_esperado || "", summary.aviso_resultado || ""].join(" ");
  speakLocally(text);
});
$("#speak-detailed-button").addEventListener("click", () => {
  if (!lastResult) return;
  const decision = lastResult.decision;
  const text = [decision.orientacao_principal, ...decision.configuracao_modal.map((item) => `${item.modo}: ${item.funcao}. ${item.acao}`), ...decision.condicoes].join(" ");
  speakLocally(text);
});
$("#stop-speech").addEventListener("click", () => { if ("speechSynthesis" in window) speechSynthesis.cancel(); $('#speech-status').textContent = 'Leitura interrompida.'; });

// The browser's usual recognition service may send audio elsewhere. No such
// service is started by this public build; text and keyboard cover every action.
$$('.dictate').forEach(button => {
  button.disabled = true; button.textContent = 'Ditado indisponível';
  button.title = 'Ditado remoto desativado por privacidade. Use texto ou teclado.';
});
$$('.dictation-status').forEach(node => { node.textContent = 'Ditado remoto desativado nesta versão. Use texto ou teclado.'; });

async function load() {
  $('#health').dataset.state = 'loading';
  const health = await api("/api/health");
  catalog = await api("/api/catalog");
  renderRationaleGuide();
  renderReported(); renderTemplates();
  currentCase = await request('start', {template:INTERVIEW_TEMPLATE});
  renderKnownContext();
  $('#health').dataset.state = 'ready';
  $("#health").textContent = `AMADO pronto: base carregada no navegador (${health.triples} triplas). A construção pode levar alguns segundos.`;
}

function clearInputAndResult() {
  currentCase = null; lastResult = null; organizedNarrative = null;
  if ('speechSynthesis' in window) speechSynthesis.cancel();
  $$('textarea').forEach(node => { node.value = ''; });
  $$('input[type="checkbox"], input[type="radio"]').forEach(node => { node.checked = false; });
  $('#template-select').value = '';
  $('#saida').hidden = true; $('#free-interpretation').hidden = true;
  ['#free-controlled-fields','#controlled-fields','#free-summary','#context-summary','#practical-steps','#orientation','#rationale','#modal-configuration','#depara-table','#trace-graph','#trace-table','#free-trace-overview','#free-trace-explanation','#criteria','#knowledge','#rejected','#practical-headline','#expected-result','#expected-result-note','#resources','#conditional-resources','#conditions','#alternatives','#monitoring','#missing','#isolated-comparison','#articulated-comparison','#technical-summary','#limit','#free-missing ul','#free-assumptions ul','#known-assumptions ul'].forEach(selector => $(selector).replaceChildren());
  $('#organized-text').textContent = '';
  $('#reported-correction').value = '';
  ['#reported-status','#known-status','#free-status','#narrative-status','#speech-status','#runtime-error'].forEach(selector => { $(selector).textContent = ''; });
  $('#reported-step').open = true; $('#organized-step').open = false;
  $('#free-narrative-block').open = true;
}

$('#clear-case').addEventListener('click', () => {
  operationEpoch++;
  restart(); clearInputAndResult();
  busy = false; activeTab = 'known';
  document.body.classList.remove('free-case-view');
  $('#known-panel').hidden = false; $('#free-panel').hidden = true;
  $('#known-tab').setAttribute('aria-selected','true'); $('#free-tab').setAttribute('aria-selected','false');
  $('#known-tab').tabIndex = 0; $('#free-tab').tabIndex = -1;
  $('#free-reading-tools').hidden = true;
  $$('main button, main input, main textarea, main select').forEach(node => { node.disabled = node.classList.contains('dictate'); });
  $('#main').setAttribute('aria-busy','false');
  $('#health').textContent = 'Caso descartado. Reiniciando o ambiente de execução…';
  runBusy('#health', load);
});
window.addEventListener('amado-progress', e => {
  $('#health').dataset.state = 'loading';
  $('#health').textContent = e.detail;
});
$$('textarea').forEach(node => { node.maxLength = 10000; node.autocomplete = 'off'; });
window.addEventListener('pagehide', clearInputAndResult);
window.addEventListener('pageshow', e => { if (e.persisted) $('#clear-case').click(); });
runBusy('#health', load);
