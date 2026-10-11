// Presentation for the RDF-backed composer. No rules, inferred facts or storage.
import { request } from './client.mjs';

const root = document.querySelector('#composition-panel');
const $ = selector => root.querySelector(selector);
const escape = value => String(value ?? '').replace(/[&<>"']/g, char => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char]));
const local = value => String(value ?? '').split(/[#/]/).pop();
let catalog = null, loading = false, running = false, epoch = 0, result = null;
let previousControls = [];
const names = new Map();
const stateName = {PASS:'Condição atendida', FAIL:'Condição não atendida', PENDING:'A confirmar', NOT_EXECUTED:'Não verificada'};
const statusName = {COMPLETE:'Combinação completa para esta tarefa', CONDITIONAL:'Possibilidades que precisam de confirmação', PARTIAL:'Apoio parcial: a tarefa ainda não está coberta', NONE:'Nenhuma combinação sustentada nas condições informadas', UNCONFIRMED:'Confirme as informações antes de continuar'};
const gapName = {FUNCTION_NOT_COVERED:'Há uma etapa da tarefa sem possibilidade disponível.', NO_COMPLETE_COMPOSITION:'Não foi encontrada uma sequência completa com condições atendidas.', PENDING_CONDITIONS:'Ainda há condições a confirmar.', NO_AUTHORIZED_RELATION:'Não há relação fundamentada que autorize ligar estas etapas.', TASK_BOUNDARY_MISMATCH:'A sequência não atende à entrada e à saída exigidas pela tarefa.', RELATION_NOT_AUTHORIZED:'A ligação entre etapas não foi autorizada pelas verificações.'};
const fieldGroups = [
  ['A atividade e o controle da revisão', ['LearningCommunicationContext','ContentAvailable','CanCorrect','ControlsCompletion','CanVerifyMeaning']],
  ['Escrever pelo teclado', ['CanUseKeyboard','KeyboardEffortAcceptable','KeyboardCompatible','KeyboardFeedbackPerceptible']],
  ['Usar a fala como entrada', ['CanUseSpeech','SpeechInputUsable','SpeechEffortAcceptable','SpeechCompatible','SpeechFeedbackPerceptible']],
  ['Conferir o conteúdo', ['CanReviewVisualText','CanReviewSpeech','AudioUsable','CanControlPlayback']],
];
function label(value) {
  if (typeof value === 'object' && value) return value.label || label(value.id);
  const text = String(value ?? '');
  return names.get(text) || (/^https?:\/\//.test(text) ? names.get(local(text)) || local(text) : text);
}
function paragraph(value, prefix='') { return value ? `<p>${prefix ? `<strong>${escape(prefix)}</strong> ` : ''}${escape(value)}</p>` : ''; }
function list(items) { return items?.length ? `<ul>${items.map(item => `<li>${escape(label(item))}</li>`).join('')}</ul>` : ''; }
function sourceLink(source) {
  if (!source) return '';
  let url;
  try { url = new URL(source.url); } catch { return escape(label(source)); }
  return /^https?:$/.test(url.protocol) ? `<a href="${escape(url.href)}" rel="noreferrer">${escape(label(source))}</a>` : escape(label(source));
}
function setStatus(text) { $('#composition-status').textContent = text; }
function lock(active) {
  running = active;
  root.setAttribute('aria-busy', String(active));
  if (active) {
    previousControls = [...document.querySelectorAll('main button, main input, main select, main textarea')].map(node => [node, node.disabled]);
    previousControls.forEach(([node]) => { if (!['clear-case','composition-cancel','stop-speech'].includes(node.id)) node.disabled = true; });
  } else {
    previousControls.forEach(([node, disabled]) => { node.disabled = disabled; });
    previousControls = [];
  }
  $('#composition-cancel').hidden = !active;
}
function invalidate() {
  result = null;
  $('#composition-result').replaceChildren();
  $('#composition-result').hidden = true;
  delete $('#composition-result').dataset.status;
  $('#composition-confirmed').checked = false;
  updateFieldCounts();
}
function reset() {
  epoch++;
  // The owning app resets the shared worker and controls on a full-page clear.
  running = false; loading = false; previousControls = [];
  root.setAttribute('aria-busy','false');
  $('#composition-cancel').hidden = true;
  $('#composition-form')?.reset();
  $('#composition-example-note').hidden = true;
  $('#composition-error').textContent = '';
  invalidate(); updateTask(); setStatus('');
}
function triField(item, kind) {
  return `<div class="composition-field"><label for="composition-${kind}-${escape(item.id)}">${escape(item.label)}</label><select id="composition-${kind}-${escape(item.id)}" data-composition-kind="${kind}" data-concept="${escape(item.id)}"><option value="">Ainda não sei</option><option value="true">Sim</option><option value="false">Não</option></select></div>`;
}
function fieldGroup(title, items, kind) {
  if (!items.length) return '';
  return `<details class="foundation composition-field-group"><summary>${escape(title)} <span data-field-count></span></summary><fieldset><legend class="composition-visually-hidden">${escape(title)} — indique sim, não ou ainda não sei</legend><div class="composition-fields">${items.map(item => triField(item, kind)).join('')}</div></fieldset></details>`;
}
function updateFieldCounts() {
  root.querySelectorAll('.composition-field-group').forEach(group => {
    const fields = [...group.querySelectorAll('select')];
    group.querySelector('[data-field-count]').textContent = `(${fields.filter(field => field.value !== '').length} de ${fields.length} informados)`;
  });
}
function renderForm() {
  (catalog.tasks || []).concat(catalog.facts || [], catalog.resources || [], catalog.capabilities || [], catalog.relations || []).forEach(item => {
    names.set(item.id,item.label); if (item.iri) names.set(item.iri,item.label);
  });
  Object.entries(catalog.labels || {}).forEach(([key,value]) => names.set(key,value));
  $('#composition-task').innerHTML = (catalog.tasks || []).map(item => `<option value="${escape(item.id)}">${escape(item.label)}</option>`).join('');
  const covered = new Set(fieldGroups.flatMap(([,ids]) => ids));
  $('#composition-fields').innerHTML = fieldGroup('Recursos disponíveis nesta atividade',catalog.resources || [],'resources') +
    fieldGroups.map(([title,ids]) => fieldGroup(title,ids.map(id => catalog.facts.find(item => item.id === id)).filter(Boolean),'facts')).join('') +
    fieldGroup('Outras condições da atividade',(catalog.facts || []).filter(item => !covered.has(item.id)),'facts');
  $('#composition-form').hidden = false;
  $('#composition-load').hidden = true;
  $('#composition-example').hidden = !catalog.synthetic_example;
  updateFieldCounts(); updateTask();
}
function updateTask() {
  const task = catalog?.tasks.find(item => item.id === $('#composition-task').value);
  $('#composition-task-help').textContent = task ? `Etapas consideradas: ${(task.required_functions || []).map(label).join(' → ')}.` : '';
}
async function loadCatalog() {
  if (catalog || loading || document.querySelector('#main').getAttribute('aria-busy') === 'true') return;
  const current = epoch;
  loading = true; lock(true); setStatus('Carregando as tarefas e condições representadas na base…');
  $('#composition-error').textContent = '';
  try {
    const loaded = await request('catalog_composition');
    if (current !== epoch) return;
    catalog = loaded; renderForm(); setStatus('Escolha a tarefa e confira as condições. Nenhuma condição foi presumida.');
  } catch (error) {
    if (current === epoch) { $('#composition-error').textContent = error.message; $('#composition-load').hidden = false; }
  } finally { if (current === epoch) { loading = false; lock(false); } }
}
function checksTable(checks) {
  if (!checks?.length) return '<p>Nenhuma verificação detalhada foi registrada para este item.</p>';
  return `<ul class="composition-checks">${checks.map(check => `<li><strong>${escape(label(check.expected?.concept || check.subject))}</strong>: ${escape(stateName[check.state] || check.state)}${check.observed && typeof check.observed === 'object' && 'value' in check.observed ? ` — resposta: ${check.observed.value === true ? 'sim' : check.observed.value === false ? 'não' : 'ainda não sei'}.` : ''}<details><summary>Conferir esta verificação</summary>${paragraph(check.explanation)}<p class="field-help">Registro: <code>${escape(check.id)}</code></p></details></li>`).join('')}</ul>`;
}
function trajectoryKnowledge(grounding) {
  const evidence = result?.trajectory_evidence;
  if (!evidence) return '';
  const applications = [...(evidence.applications || []), ...(evidence.pending_applications || []), ...(evidence.partial_applications || [])];
  const application = applications.find(item => item.id === grounding.id);
  const records = [...(evidence.records || []), ...(evidence.pending_records || []), ...(evidence.partial_records || [])];
  const knowledge = (application?.knowledge_ids || []).map(id => records.find(item => item.collection === 'knowledge' && item.id === id)).filter(Boolean);
  if (!knowledge.length) return '';
  return `<details class="foundation"><summary>Conhecimentos da pesquisa empregados nesta aplicação</summary><p>Esta aplicação é uma proposta de operacionalização: não altera o estado documental dos conhecimentos anteriores nem comprova benefício em uso.</p><ul>${knowledge.map(item => `<li>${paragraph(item.record.enunciado)}${paragraph(item.record.articulacao,'Como foi articulado:')}${paragraph(item.record.limite_transferencia,'Limite:')}<p class="field-help">${escape(item.id)} — ${item.record.status_revisao === 'CANDIDATO_RECONSTRUIDO_A_REVISAR' ? 'reconstrução analítica candidata, ainda sujeita a revisão documental' : item.record.status_revisao === 'CONFERIDO_PARA_O_ESCOPO_RC3' ? 'conferido no escopo anterior registrado' : escape(item.record.status_revisao || 'estado documental não informado')}${item.record.foundation_review_status === 'PARCIAL' ? '; a conferência da fundamentação permanece parcial' : ''}.</p></li>`).join('')}</ul></details>`;
}
function foundation(grounding) {
  if (!grounding) return '';
  const art = grounding.articulation || {}, criterion = grounding.criterion || {};
  return `<div class="composition-foundation">${paragraph(label(grounding.knowledge),'Conhecimento empregado:')}${paragraph(grounding.justification || criterion.justification,'Por que sustenta esta escolha:')}${trajectoryKnowledge(grounding)}
    <details class="foundation"><summary>Como as fontes foram articuladas</summary>${paragraph(art.operation,'Operação registrada na pesquisa:')}${paragraph(art.added_understanding,'O que essa relação acrescenta:')}
    <ul class="composition-sources">${(art.contributions || []).map(item => `<li>${paragraph(item.statement)}<p><strong>Fonte:</strong> ${sourceLink(item.source)}. <strong>Localização:</strong> ${escape(item.locator || 'Não registrada')}.</p><p class="field-help">${item.status === 'PRIMARY_CHECKED' ? 'Contribuição registrada com conferência da fonte primária.' : 'Contribuição preservada de registro anterior; não representa uma nova conferência do documento original.'}</p></li>`).join('')}</ul>${paragraph(art.interpretation)}</details>
    <details class="foundation"><summary>Critério e origem desta aplicação</summary>${paragraph(label(criterion))}${paragraph(criterion.justification)}<p>${sourceLink(criterion.source)} — ${escape(criterion.locator || 'Localização não registrada')}.</p><p class="field-help">Aplicação: <code>${escape(local(grounding.id))}</code></p></details></div>`;
}
function stepMarkup(step) {
  return `<li><h4>${escape(step.label)}</h4>${paragraph(step.action)}${paragraph(label(step.mode),'Forma de interação:')}${paragraph(label(step.function),'Função:')}
    <details class="foundation"><summary>Por que esta etapa pode ser usada</summary>${checksTable(step.condition_checks)}${(step.groundings || []).map(foundation).join('')}${paragraph(step.limitation,'Limite:')}</details></li>`;
}
function choiceMarkup(choice, kind, index) {
  const title = (choice.steps || []).map(step => step.label).join(' → ');
  const isPartial = kind === 'partial', isPending = kind === 'pending';
  return `<details class="foundation composition-choice" ${index === 0 && !isPending ? 'open' : ''} data-composition-choice="${kind}"><summary>${escape(title)} <span class="composition-badge">${isPartial ? 'Etapa parcial' : isPending ? 'A confirmar' : 'Condições atendidas'}</span></summary>
    ${isPartial ? `<p class="notice"><strong>Não conclui toda a tarefa.</strong> Ainda falta: ${(choice.missing_functions || []).map(item => escape(label(item))).join('; ')}.</p>${choice.entry ? `<p>Este trecho precisa receber <strong>${escape(label(choice.entry.representation))}</strong>. A disponibilidade dessa entrada não foi verificada; não execute o trecho sem ela.</p>` : ''}` : ''}
    ${isPending ? '<p class="notice">Esta combinação não está pronta para uso. Confirme as condições pendentes antes de considerá-la aplicável.</p>' : ''}
    <ol class="composition-steps">${(choice.steps || []).map(stepMarkup).join('')}</ol>
    ${(choice.relations || []).map(relation => `<div class="composition-connection"><h4>Por que essas etapas se conectam</h4>${paragraph(relation.explanation)}${paragraph(label(relation.shared_type),'Informação que passa de uma etapa à outra:')}<details class="foundation"><summary>Fundamento desta conexão</summary>${checksTable(relation.condition_checks)}${foundation(relation.grounding)}</details></div>`).join('')}
    <details class="foundation"><summary>Limites desta possibilidade</summary>${list(choice.limits)}</details></details>`;
}
function conditionQuestions(items) {
  return `<ul>${items.map(item => `<li><a href="#composition-${item.kind === 'resource' ? 'resources' : 'facts'}-${escape(local(item.id))}" data-composition-question="${escape(local(item.id))}">${escape(item.label)}</a> — ainda não confirmado.</li>`).join('')}</ul>`;
}
function renderResult(response) {
  result = response;
  $('#composition-result').dataset.status = response.proposal_status;
  const choices = response.choices || [], pending = response.pending_candidates || [], partial = response.partial_segments || [];
  const questions = [...(response.facts_to_confirm || []), ...(response.resources_to_confirm || [])];
  $('#composition-result').innerHTML = `<h3 id="composition-result-title" tabindex="-1">${escape(statusName[response.proposal_status] || 'Resultado da consulta')}</h3>
    <p>As condições foram conferidas a partir das suas respostas; não foram medidas pelo programa. As possibilidades abaixo são propostas de projeto, não comprovação de benefício em uso.</p>
    ${choices.length ? `<h4>Possibilidades completas</h4><p>${choices.length} ${choices.length > 1 ? 'combinações atendem' : 'combinação atende'} às condições representadas para a tarefa. A ordem não indica preferência.</p>${choices.map((choice,index) => choiceMarkup(choice,'complete',index)).join('')}` : ''}
    ${questions.length ? `<section aria-labelledby="composition-questions-title"><h4 id="composition-questions-title">O que falta confirmar</h4>${conditionQuestions(questions)}</section>` : ''}
    ${pending.length ? `<details class="foundation"><summary>Possibilidades condicionais (${pending.length})</summary>${pending.map((choice,index) => choiceMarkup(choice,'pending',index)).join('')}</details>` : ''}
    ${partial.length ? `<details class="foundation" ${!choices.length && !pending.length ? 'open' : ''}><summary>Partes que já têm apoio (${partial.length})</summary><p>Estes trechos não devem ser unidos para formar uma orientação que o motor não verificou.</p>${partial.map((choice,index) => choiceMarkup(choice,'partial',index)).join('')}</details>` : ''}
    ${response.missing_functions?.length ? `<h4>Etapas ainda sem cobertura</h4>${list(response.missing_functions.map(item => item.function))}` : ''}
    <details class="foundation"><summary>Por que outras possibilidades não foram usadas</summary>${response.unavailable_conditions?.length ? `<p>As seguintes condições foram declaradas como não atendidas:</p>${list(response.unavailable_conditions)}` : '<p>Nenhum impedimento declarado foi listado nesta execução.</p>'}${list((response.integration_gaps || []).map(item => item.explanation || item.label || gapName[item.code] || 'Uma ligação entre etapas permanece sem apoio.'))}${list((response.gaps || []).map(item => item.explanation || gapName[item.code] || 'Há uma limitação registrada que impede concluir a combinação.'))}</details>
    <details class="foundation"><summary>Limites e registros da execução</summary>${list(response.limits)}<p>Os fundamentos detalhados estão junto de cada etapa e conexão.</p><p class="field-help">Tarefa: ${escape(label(response.task))}. Identificador desta exploração: <code>${escape(response.context_id)}</code>.</p>${paragraph(response.trajectory_evidence?.base_sha256,'Hash da base consultada:')}${paragraph(response.trajectory_evidence?.bindings_sha256,'Hash das aplicações verificadas:')}</details>`;
  $('#composition-result').hidden = false;
  $('#composition-result-title').focus();
  setStatus(`${statusName[response.proposal_status] || 'Consulta concluída'}. ${questions.length ? `${questions.length} informações a confirmar.` : ''}`);
}
async function compose(event) {
  event.preventDefault();
  if (running || !catalog) return;
  if (!$('#composition-confirmed').checked) { $('#composition-error').textContent = 'Confira as informações e marque a confirmação antes de construir a combinação.'; $('#composition-confirmed').focus(); return; }
  const context = {id:`WEB-COMPOSITION-${crypto.randomUUID()}`, task:$('#composition-task').value, confirmed:true, facts:{}, resources:{}};
  root.querySelectorAll('[data-composition-kind]').forEach(field => { context[field.dataset.compositionKind][field.dataset.concept] = field.value === '' ? null : field.value === 'true'; });
  const current = epoch;
  window.dispatchEvent(new CustomEvent('amado-composition-start'));
  lock(true); $('#composition-error').textContent = ''; setStatus('Conferindo condições e combinando as etapas sustentadas pela base…');
  try { const response = await request('compose',{payload:context}); if (current === epoch) renderResult(response); }
  catch (error) { if (current === epoch) { $('#composition-error').textContent = error.message; setStatus('Não foi possível concluir. Suas respostas continuam disponíveis para tentar novamente.'); } }
  finally { if (current === epoch) lock(false); }
}

root.addEventListener('toggle', event => { if (event.target === root && root.open) loadCatalog(); }, true);
$('#composition-load').addEventListener('click',loadCatalog);
$('#composition-form').addEventListener('submit',compose);
$('#composition-form').addEventListener('change',event => {
  if (event.target.id === 'composition-confirmed') {
    if (!event.target.checked) {
      invalidate();
      setStatus('Confirmação retirada. Confira as informações e faça uma nova consulta.');
    }
    return;
  }
  const hadResult = Boolean(result); invalidate(); updateTask();
  if (hadResult) setStatus('As condições mudaram. Confirme as informações e faça uma nova consulta.');
});
$('#composition-example').addEventListener('click', () => {
  if (!catalog?.synthetic_example || running) return;
  const context = catalog.synthetic_example.context;
  $('#composition-task').value = context.task;
  root.querySelectorAll('[data-composition-kind]').forEach(field => {
    const value = context[field.dataset.compositionKind]?.[field.dataset.concept];
    field.value = value === true ? 'true' : value === false ? 'false' : '';
  });
  invalidate(); updateTask();
  $('#composition-example-note').hidden = false;
  $('#composition-example-note').textContent = `Exemplo sintético: ${catalog.synthetic_example.label}. As respostas são premissas de demonstração. Revise e confirme; elas não descrevem uma pessoa observada.`;
  setStatus('Exemplo preenchido. Abra os grupos para conferir as respostas e marque a confirmação.');
});
$('#composition-reset').addEventListener('click', () => { reset(); setStatus('Respostas e resultado desta exploração descartados.'); });
$('#composition-cancel').addEventListener('click', () => document.querySelector('#clear-case').click());
$('#composition-result').addEventListener('click', event => {
  const link = event.target.closest('[data-composition-question]');
  if (!link) return;
  event.preventDefault();
  const field = [...root.querySelectorAll('[data-concept]')].find(node => node.dataset.concept === link.dataset.compositionQuestion);
  if (field) { field.closest('details').open = true; field.focus(); }
});
window.addEventListener('amado-context-cleared',reset);
window.addEventListener('pagehide',reset);
new MutationObserver(() => { if (root.open && !catalog && !loading && document.querySelector('#main').getAttribute('aria-busy') !== 'true') loadCatalog(); }).observe(document.querySelector('#main'),{attributes:true,attributeFilter:['aria-busy']});
