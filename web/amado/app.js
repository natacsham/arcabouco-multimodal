import { request, restart } from './client.mjs';
import { renderExplanation } from '../explanation.js';
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
const originalDeparaOrder = $("#depara-reading-order").textContent;

function renderRationaleGuide() {
  $("#free-rationale-terms").innerHTML = TRACE_STEPS.map((step) => `<li data-trace-kind="${step.kind}"><strong>${escapeHtml(step.label)}</strong><p>${escapeHtml(step.description)}</p></li>`).join("");
}

function renderTraceGraph(graph, result = {}) {
  // Both modes and views read the same explanatory projection. Legacy graph
  // groupings are not substituted for missing evidence in the new contract.
  $("#trace-reading-order").textContent = "Abra uma escolha: confira como seu conhecimento foi construído e por que foi empregado neste caso.";
  $("#free-trace-overview").hidden = true;
  $("#free-trace-overview").replaceChildren();
  $("#free-trace-explanation").hidden = true;
  $("#free-trace-explanation").replaceChildren();
  $("#trace-table").replaceChildren();
  renderExplanation($("#trace-graph"), result);
}

function renderComparison(result) {
  const comparison = result.articulation_comparison || {};
  const isolated = comparison.isolated || {};
  const articulated = comparison.articulated || {};
  const configs = result.explanation?.configurations || [];
  const entities = result.execution_evidence?.entities || {};
  const labels = new Map((result.explanation?.graph?.nodes || []).map(row => [row.id, row.label]));
  const label = id => {
    const row = entities[id] || {};
    return row.title || row.label || row.rotulo || row.enunciado || labels.get(id) || 'Descrição não incluída neste retorno';
  };
  const deltas = comparison.evidence_delta;
  const details = Array.isArray(deltas) ? (deltas.length ? deltas.map(delta => {
    const config = configs.find(row => row.component_id === delta.component_id);
    const supports = config?.application?.supports || [];
    const groups = new Map();
    for (const pair of delta.added_support_pairs || []) {
      const key = JSON.stringify([pair.criterion_id, pair.knowledge_id]);
      if (!groups.has(key)) groups.set(key, { ...pair, origin_ids: [] });
      if (!groups.get(key).origin_ids.includes(pair.origin_id)) groups.get(key).origin_ids.push(pair.origin_id);
    }
    const supportRows = [...groups.values()].map(pair => {
      const support = supports.find(row => row.criterion_id === pair.criterion_id && (row.knowledge_ids || []).includes(pair.knowledge_id));
      const origins = pair.origin_ids.map(id => {
        const origin = support?.origins?.find(row => row.id === id) || entities[id] || {};
        return [origin.fonte_id ? label(origin.fonte_id) : 'Fonte não detalhada', origin.localizacao_publica || origin.location || 'Localização não detalhada', origin.aviso_publicacao].filter(Boolean).join(' — ');
      });
      return `<li><p><strong>Critério:</strong> ${escapeHtml(support?.criterion_statement || label(pair.criterion_id))}</p><p><strong>Apoio acrescentado:</strong> ${escapeHtml(label(pair.knowledge_id))}</p>${support?.justification ? `<p><strong>Justificativa registrada:</strong> ${escapeHtml(support.justification)}</p>` : ''}<p><strong>Origem do critério:</strong></p><ul>${origins.map(value => `<li>${escapeHtml(value)}</li>`).join('')}</ul><details><summary>Identificadores deste apoio</summary><p>${escapeHtml([pair.criterion_id, pair.knowledge_id, ...pair.origin_ids].join(' · '))}</p></details></li>`;
    }).join('');
    const witnesses = (delta.retrieval_witnesses || []).map(row => `<li><p><strong>Conhecimento de partida:</strong> ${escapeHtml(label(row.input_knowledge_id))}</p><p><strong>Articulação percorrida:</strong> ${escapeHtml(label(row.articulation_id))}</p><p><strong>Conhecimento recuperado:</strong> ${escapeHtml(label(row.knowledge_id))}</p>${row.required_function_id ? `<p><strong>Função requerida:</strong> ${escapeHtml(label(row.required_function_id))}</p>` : ''}<details><summary>Identificadores da correspondência</summary><p>${escapeHtml([row.input_knowledge_id, row.articulation_id, row.knowledge_id, ...(row.check_ids || [])].filter(Boolean).join(' · '))}</p></details></li>`).join('');
    return `<details data-comparison-component="${escapeHtml(delta.component_id)}"><summary>${escapeHtml(config?.title || label(delta.configuration_id))}</summary><p><strong>${delta.configuration_added ? 'Escolha acrescentada pela recuperação articulada.' : 'Escolha já presente na recuperação isolada, com fundamento adicional.'}</strong></p>${supportRows ? `<ul>${supportRows}</ul>` : '<p>Não foram retornados apoios adicionais de critério para esta escolha.</p>'}${witnesses ? `<details><summary>Como o apoio adicional foi recuperado</summary><ul>${witnesses}</ul></details>` : '<p>O retorno não detalhou uma correspondência de recuperação para este acréscimo.</p>'}${delta.interpretation ? `<p>${escapeHtml(delta.interpretation)}</p>` : ''}</details>`;
  }).join('') : '<p>Esta execução não registrou acréscimo de escolha ou de apoio de critério em relação à recuperação isolada.</p>') : '<p>A comparação desta execução não retornou diferenças detalhadas de fundamento. Os totais não substituem essa evidência.</p>';
  $("#isolated-comparison").innerHTML = `<p><strong>${(isolated.knowledge_ids || []).length}</strong> conhecimentos foram recuperados. Os padrões selecionados oferecem <strong>${(isolated.covered_function_ids || []).length}</strong> funções; a correspondência com os requisitos do contexto é conferida separadamente.</p><p>${(isolated.remaining_function_ids || []).length ? `${escapeHtml(isolated.remaining_function_ids.length)} funções requeridas ainda ficam sem cobertura declarada.` : 'Não restam funções requeridas sem cobertura declarada nesta comparação.'} Isso não comprova eficácia observada.</p>`;
  $("#articulated-comparison").innerHTML = `<p><strong>${(comparison.added_knowledge_ids || []).length}</strong> conhecimentos foram acrescentados por <strong>${(comparison.articulation_ids || []).length}</strong> relações documentadas.</p><p>As configurações selecionadas apresentam: ${escapeHtml((articulated.modalities || []).join(", ") || 'nenhuma modalidade')}. Foram selecionadas ${(articulated.component_ids || []).length} configurações, com condições e limites próprios.</p><details data-articulation-delta><summary>O que a articulação acrescentou a cada escolha</summary><p>A comparação distingue uma configuração nova de um apoio adicional para uma configuração já presente. Não demonstra resultado de uma aplicação.</p>${details}</details>`;
}

function renderDePara(rows) {
  const target = $("#depara-table");
  $("#depara-reading-order").textContent = "Condição do caso → interpretação registrada no padrão → função oferecida → configuração → alternativa e limite. Os requisitos confirmados e as verificações estão no percurso de fundamentação; uma função oferecida não cria um requisito do contexto.";
  if (!rows?.length) {
    target.innerHTML = activeTab === "free"
      ? "<p>Esta execução não retornou uma matriz de transformação das condições. Isso, isoladamente, não informa o motivo: confira o estado da decisão, as lacunas e o caminho da orientação.</p>"
      : "<p>Não foi retornada uma transformação estruturada para este caso. Confira o estado da orientação e as lacunas; nenhuma transformação foi presumida.</p>";
    return;
  }
  target.innerHTML = `<div class="table-scroll"><table><caption>Condições consideradas e funções oferecidas na orientação</caption><thead><tr><th>Condição</th><th>Interpretação registrada no padrão</th><th>Função oferecida</th><th>Como foi configurado</th><th>Alternativa e limite</th></tr></thead><tbody>${rows.map((row) => `<tr><td>${escapeHtml(row.condicoes.join("; "))}</td><td>${escapeHtml(row.abstracao_funcional)}</td><td>${escapeHtml(row.implicacao_decisoria)}</td><td>${row.configuracao_multimodal.map((item) => `<strong>${escapeHtml(item.modo)}</strong>: ${escapeHtml(item.funcao)} <small>(${escapeHtml(item.responsavel)})</small>`).join("<br>")}</td><td>${escapeHtml(row.alternativa)}<br><small>${escapeHtml(row.condicao_limite)}</small></td></tr>`).join("")}</tbody></table></div>`;
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
  const partial = decision.status === "GERADA_PARCIAL";
  $("#decision-status").textContent = decision.status === "GERADA" ? "Orientação construída" : partial ? "Orientação parcial — há funções que ainda não foram cobertas" : "Decisão suspensa";
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
  $("#technical-summary").textContent = `A execução usou ${result.traceability.knowledge.length} conhecimentos, ${result.traceability.criteria.length} critérios, ${result.articulations_used.length} relações habilitadas na base e executou ${Object.keys(result.query_summary).length} consultas de competência. Esses números não comprovam eficácia nem independência entre as fontes.`;
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
  $(statusTarget).textContent = result.decision.status === "GERADA" ? "Orientação pronta." : result.decision.status === "GERADA_PARCIAL" ? "Orientação parcial disponível. Confira as funções não cobertas e os limites." : "A decisão foi suspensa; confira as informações ausentes.";
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
