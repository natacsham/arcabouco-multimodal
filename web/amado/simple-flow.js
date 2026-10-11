import {request, restart} from './client.mjs';
import {renderExplanation} from '../explanation.js';
import {setupDictation} from './voice.js';
import {legacyQuestions, legacyAnswer, legacySummary, detectCompositionTask,
  compositionDraft, compositionQuestions, compositionSummary} from './intake.mjs';

const $ = selector => document.querySelector(selector);
const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const para = value => value ? '<p>'+esc(value)+'</p>' : '';
const list = values => {
  const items = Array.isArray(values) ? values : values ? [values] : [];
  return items.length ? '<ul>'+items.map(value => '<li>'+esc(typeof value === 'object' ? value.label || value.title || value.titulo || '' : value)+'</li>').join('')+'</ul>' : '';
};
let catalog, compositionCatalog, current, mode = 'legacy', draft, result, busy = false, epoch = 0;
let questions = [], skipped = new Set(), exampleNarrative = null, exampleId = null, speechText = '', organizedNarrative = null;
const voice = setupDictation({button:$('#dictate-case'),input:$('#case-narrative'),status:$('#dictation-status'),
  preview:$('#dictation-preview'),dialog:$('#speech-consent'),allow:$('#allow-browser-dictation'),cancel:$('#cancel-dictation')});
function status(text) { $('#flow-status').textContent = text; }
function invalidate() {
  result = null; $('#orientation-result').hidden = true; $('#case-confirmed').checked = false;
  $('#generate-orientation').disabled = true;
  renderExplanation($('#orientation-foundation-body'), {});
  if ('speechSynthesis' in window) speechSynthesis.cancel();
}
function screen(id, focus) {
  for (const name of ['case-entry','case-questions','case-review','orientation-result']) $('#'+name).hidden = name !== id;
  if (focus) $('#'+focus).focus();
}
async function run(action, message='') {
  if (busy) return;
  busy = true; const expected = epoch; $('#main').setAttribute('aria-busy','true');
  $('#flow-error').textContent = ''; status(message);
  const controls = [...document.querySelectorAll('#main button,#main input,#main textarea,#main select')].map(element => [element,element.disabled]);
  controls.forEach(([element]) => element.disabled = true);
  let recoveryFocus;
  try { await action(expected); }
  catch (error) {
    if (expected === epoch) { $('#flow-error').textContent = error.message || String(error); status(''); recoveryFocus = error.field; }
  } finally {
    if (expected === epoch) {
      busy = false; $('#main').setAttribute('aria-busy','false');
      controls.forEach(([element,disabled]) => element.disabled = disabled);
      $('#generate-orientation').disabled = !$('#case-confirmed').checked;
      $('#load-example').disabled = !$('#case-template').value;
      if (recoveryFocus) $('#'+recoveryFocus)?.focus();
    }
  }
}
function questionMarkup(question) {
  const id = question.id, base = '<fieldset class="question" data-question="'+esc(id)+'"><legend class="sr-only">'+esc(question.label)+'</legend>';
  if (question.type === 'text') return base+'<label class="sr-only" for="answer-'+esc(id)+'">'+esc(question.label)+'</label><textarea id="answer-'+esc(id)+'" name="'+esc(id)+'" rows="2"></textarea></fieldset>';
  if (question.type === 'single') return base+'<div class="question-options question-single">'+question.options.map(option =>
    '<label><input type="radio" name="'+esc(id)+'" value="'+esc(option.id)+'"> '+esc(option.label)+'</label>').join('')+'</div></fieldset>';
  const checkbox = (option,index) => '<label><input type="checkbox" name="'+esc(id)+'" value="'+esc(option.id)+'"> '+esc(option.label)+'</label>';
  const initial = question.options.slice(0,6), other = question.options.slice(6);
  const note = question.participant_id ? '<details><summary>Outra forma de apoio</summary><label for="note-'+esc(id)+'">Descreva o apoio usado por este grupo</label><textarea id="note-'+esc(id)+'" name="'+esc(id)+':note" maxlength="2000" rows="2"></textarea></details>' : '';
  return base+'<div class="question-options">'+initial.map(checkbox).join('')+'</div>'+
    (other.length ? '<details><summary>Ver outras respostas possíveis</summary><div class="question-options">'+other.map(checkbox).join('')+'</div></details>' : '')+
    '<label class="question-unknown"><input type="checkbox" name="'+esc(id)+'" value="unknown"> Ainda não sei</label>'+note+'</fieldset>';
}
function unanswered() {
  return (mode === 'legacy' ? legacyQuestions(current,catalog) : compositionQuestions(draft,compositionCatalog)).filter(question => !skipped.has(question.id));
}
function askOrReview() {
  $('#new-case').hidden = false;
  // One missing piece at a time; the rest of the decomposition stays internal.
  questions = unanswered().slice(0,1);
  if (!questions.length) { review(); return; }
  $('#questions-title').textContent = questions[0].label;
  $('#question-person').textContent = questions[0].participant_label || '';
  $('#question-person').hidden = !questions[0].participant_label;
  $('#question-fields').innerHTML = questions.map(questionMarkup).join('');
  status(''); screen('case-questions','questions-title');
}
function summaryRows() { return mode === 'legacy' ? legacySummary(current) : compositionSummary(draft,compositionCatalog); }
function fieldsHTML(rows) {
  return '<div class="review-fields">'+rows.map(row => '<div class="review-field"><strong>'+esc(row.label)+'</strong>'+para(row.value)+'</div>').join('')+'</div>';
}
function review() {
  invalidate();
  const rows = summaryRows(), narrative = $('#case-narrative').value.trim();
  const find = label => rows.find(row => row.label === label)?.value || '';
  const concise = [['Atividade',find('Atividade')],['Objetivo',find('Objetivo')],['Pessoas',find('Pessoas')]]
    .filter(([,value]) => value && value !== narrative);
  $('#review-summary').innerHTML = concise.length ? '<dl class="review-summary">'+concise.map(([label,value]) =>
    '<div><dt>'+esc(label)+'</dt><dd>'+esc(value)+'</dd></div>').join('')+'</dl>' : para(narrative.length > 300 ? narrative.slice(0,300)+'…' : narrative);
  $('#review-fields').innerHTML = fieldsHTML(rows)+'<h3>Seu relato</h3>'+para(narrative);
  const missing = mode === 'legacy' ? current.questions || [] : compositionQuestions(draft,compositionCatalog);
  $('#review-gaps').hidden = !missing.length;
  $('#review-gaps').textContent = missing.length ? 'Algumas informações ainda não foram confirmadas. A orientação mostrará esses limites.' : '';
  $('#review-details').open = false; status(''); screen('case-review','review-title');
}
async function organize(expected) {
  voice.clear(); invalidate(); skipped.clear();
  const text = $('#case-narrative').value.trim();
  if (text.length < 20) {
    $('#case-narrative').setAttribute('aria-invalid','true');
    throw Object.assign(new Error('Descreva o que a pessoa precisa fazer e o que dificulta a atividade.'),{field:'case-narrative'});
  }
  $('#case-narrative').removeAttribute('aria-invalid');
  if (organizedNarrative === text && (mode === 'legacy' ? current : draft)) { askOrReview(); return; }
  if (exampleNarrative === text && exampleId) {
    if (exampleId === 'composition-example') {
      mode = 'composition'; draft = structuredClone(compositionCatalog.synthetic_example.context); draft.confirmed = false;
    } else { mode = 'legacy'; current = await request('start',{template:exampleId}); }
  } else {
    exampleId = exampleNarrative = null;
    const task = detectCompositionTask(text);
    if (task) {
      compositionCatalog ||= await request('catalog_composition');
      mode = 'composition'; draft = {...compositionDraft(text,compositionCatalog),id:'WEB-'+crypto.randomUUID(),confirmed:false};
    } else {
      mode = 'legacy'; await request('start'); const response = await request('analyze',{payload:{narrative:text}});
      current = response.current;
    }
  }
  if (expected !== epoch) return;
  organizedNarrative = text;
  askOrReview();
}
$('#case-form').addEventListener('submit',event => { event.preventDefault(); run(organize,'Lendo o que você informou…'); });
$('#questions-form').addEventListener('change',event => {
  const changed = event.target;
  if (changed.type !== 'checkbox' || !changed.checked) return;
  for (const other of document.getElementsByName(changed.name)) if (other !== changed &&
      (changed.value === 'unknown' || other.value === 'unknown')) other.checked = false;
});
$('#questions-form').addEventListener('submit',event => {
  event.preventDefault();
  run(async expected => {
    for (const question of questions) {
      const controls = [...document.getElementsByName(question.id)];
      const value = question.type === 'multi' ? controls.filter(field => field.checked).map(field => field.value) :
        question.type === 'single' ? controls.find(field => field.checked)?.value : controls[0]?.value.trim();
      const note = document.getElementsByName(question.id+':note')[0]?.value.trim() || '';
      if (!value || value === 'unknown' || Array.isArray(value) && (!value.length || value.includes('unknown'))) {
        skipped.add(question.id);
        if (!(mode === 'legacy' && note && question.participant_id)) continue;
      }
      if (mode === 'legacy') current = await request('update',{payload:legacyAnswer(current,question,value,note)});
      else {
        const target = question.participant_id ? draft.participants?.find(person => person.id === question.participant_id) : draft;
        if (target) { target[question.field] ||= {}; target[question.field][question.concept_id] = value === 'true'; }
      }
    }
    if (expected === epoch) askOrReview();
  },'Atualizando as informações…');
});
$('#skip-questions').addEventListener('click',review);
$('#case-confirmed').addEventListener('change',() => {
  $('#generate-orientation').disabled = !$('#case-confirmed').checked;
  if (!$('#case-confirmed').checked) invalidate();
});
$('#case-narrative').addEventListener('input',() => {
  invalidate(); skipped.clear();
  $('#case-narrative').removeAttribute('aria-invalid');
  if ($('#case-narrative').value.trim() !== exampleNarrative) { exampleId = exampleNarrative = null; $('#case-template').value = ''; }
});
$('#case-template').addEventListener('change',() => { $('#load-example').disabled = !$('#case-template').value; });
$('#load-example').addEventListener('click',() => run(async expected => {
  voice.clear(); invalidate(); skipped.clear();
  exampleId = $('#case-template').value;
  if (exampleId === 'composition-example') {
    compositionCatalog ||= await request('catalog_composition');
    mode = 'composition'; draft = structuredClone(compositionCatalog.synthetic_example.context); draft.confirmed = false;
    exampleNarrative = 'Uma pessoa precisa escrever e revisar uma contribuição para uma atividade de aprendizagem. Usa teclado e texto editável e confere o rascunho pela leitura em voz. As condições deste exemplo estão preparadas para demonstração e devem ser conferidas.';
  } else {
    mode = 'legacy'; current = await request('start',{template:exampleId});
    exampleNarrative = current.context.texto_curto;
  }
  $('#case-narrative').value = exampleNarrative;
  organizedNarrative = exampleNarrative;
  if (expected === epoch) askOrReview();
},'Carregando o exemplo…'));
function edit() {
  voice.clear(); invalidate(); skipped.clear(); status(''); $('#flow-error').textContent = '';
  screen('case-entry'); $('#case-narrative').focus();
}
$('#edit-case').addEventListener('click',edit);
document.querySelectorAll('[data-edit-case]').forEach(button => button.addEventListener('click',edit));
function legacyOutput(response) {
  const decision = response.decision, summary = decision.sintese_pratica || {};
  const suspended = decision.status.startsWith('SUSPENSA');
  $('#orientation-state').textContent = suspended ? 'Ainda falta apoio para este caso' : decision.status === 'GERADA_PARCIAL' ? 'Orientação com limites' : 'Orientação construída';
  $('#orientation-main').innerHTML = para(summary.texto || decision.orientacao_principal) +
    (!suspended ? (summary.etapas || []).map(step => '<article class="orientation-step"><h3>'+esc(step.titulo)+'</h3>'+
      para(step.como_combinar)+list(step.itens)+'</article>').join('') : list(decision.informacoes_ausentes));
  $('#orientation-detail-body').innerHTML = para(decision.orientacao_principal)+
    (decision.configuracao_modal || []).map(item => '<h3>'+esc(item.modo)+'</h3>'+para(item.funcao)+para(item.acao)).join('')+
    '<h3>Condições</h3>'+list(decision.condicoes)+'<h3>Alternativas</h3>'+list(decision.alternativa ? [decision.alternativa] : decision.alternativas)+
    '<h3>Acompanhamento</h3>'+list(decision.acompanhamento)+'<h3>Limites</h3>'+para(decision.limite)+list(decision.informacoes_ausentes);
  speechText = [summary.texto || decision.orientacao_principal,...(summary.etapas || []).map(step => [step.titulo,step.funcao,step.como_combinar,...(step.itens || [])].filter(Boolean).join('. '))].join('. ');
}
function compositionOutput(response) {
  const names = new Map(Object.entries(compositionCatalog.labels || {}));
  const label = item => typeof item === 'object' && item ? item.label || label(item.id) : names.get(item) || String(item || '').split('#').pop();
  const state = {COMPLETE:'Orientação construída',CONDITIONAL:'Há condições a confirmar',PARTIAL:'Apoio parcial',
    INSUFFICIENT:'Ainda falta apoio para este caso',NONE:'Ainda falta apoio para este caso'};
  $('#orientation-state').textContent = state[response.proposal_status] || 'Confira as condições';
  const view = local => {
    const complete = local.choices || [], partial = local.partial_segments || [], pending = local.pending_candidates || [];
    const choices = complete.length ? complete : pending.length ? pending : partial;
    return para(complete.length ? 'Estas formas de produzir e conferir o conteúdo atendem às condições informadas.' :
    pending.length ? 'Estas possibilidades dependem de informações ainda não confirmadas. Confira as condições antes de utilizá-las.' :
    partial.length ? 'Há apoio para parte da atividade. Estas etapas ainda não cobrem a tarefa inteira.' : 'Não encontramos uma combinação sustentada nas condições informadas.')+
    choices.map(choice => '<article class="orientation-step">'+(choice.steps || []).map(step => '<h3>'+esc(step.label)+'</h3>'+para(step.action)+
      '<p><strong>Função:</strong> '+esc(label(step.function))+'</p>').join('')+
      (choice.relations || []).map(relation => para(relation.explanation)).join('')+
      (choice.entry ? '<p><strong>Antes de usar esta parte:</strong> é necessário '+esc(label(choice.entry.representation))+'. A disponibilidade dessa entrada ainda não foi verificada.</p>' : '')+
      (choice.missing_functions?.length ? '<p><strong>Ainda falta:</strong> '+esc(choice.missing_functions.map(label).join('; '))+'</p>' : '')+'</article>').join('');
  };
  const people = response.participant_results || [];
  $('#orientation-main').innerHTML = people.length ? people.map(person => '<section class="participant-orientation"><h3>'+esc(person.label)+'</h3>'+view(person.result)+'</section>').join('') : view(response);
  const choices = [...(response.choices || []),...(response.pending_candidates || []),...(response.partial_segments || [])];
  $('#orientation-detail-body').innerHTML = '<h3>Condições a confirmar</h3>'+list([...(response.facts_to_confirm || []),...(response.resources_to_confirm || [])])+
    '<h3>Limites</h3>'+list(response.limits)+choices.map(choice => list(choice.limits)+(choice.steps || []).map(step => para(step.limitation)).join('')).join('');
  speechText = $('#orientation-main').innerText;
}
function compositionFoundations(response) {
  if (response.participant_results?.length) return response.participant_results.map(person =>
    '<h3>'+esc(person.label)+'</h3>'+compositionFoundations(person.result)).join('');
  const names = new Map(Object.entries(compositionCatalog.labels || {}));
  const label = item => typeof item === 'object' && item ? item.label || label(item.id) : names.get(item) || String(item || '').split('#').pop();
  const states = {PASS:'Atendida',FAIL:'Não atendida',PENDING:'A confirmar',NOT_EXECUTED:'Não verificada'};
  const conditions = checks => list((checks || []).map(check => [check.explanation || check.subject,states[check.state] || check.state].filter(Boolean).join(' — ')));
  const trajectory = grounding => {
    const evidence = response.trajectory_evidence;
    if (!evidence) return '';
    const application = [...(evidence.applications || []),...(evidence.pending_applications || []),...(evidence.partial_applications || [])].find(item => item.id === grounding.id);
    const records = [...(evidence.records || []),...(evidence.pending_records || []),...(evidence.partial_records || [])];
    return (application?.knowledge_ids || []).map(id => records.find(item => item.collection === 'knowledge' && item.id === id)).filter(Boolean).map(item =>
      '<h4>Conhecimento da pesquisa empregado</h4>'+para(item.record.enunciado)+para(item.record.articulacao)+para(item.record.limite_transferencia)+
      '<p>'+esc(item.id)+' — '+esc(item.record.status_revisao || 'Estado de conferência não informado')+
      (item.record.foundation_review_status === 'PARCIAL' ? '; conferência da fundamentação parcial' : '')+'. Esta aplicação é uma proposta analítica, não demonstra benefício em uso.</p>').join('');
  };
  const sources = grounding => {
    if (!grounding) return '<p>Não há fundamento detalhado registrado para esta ligação.</p>';
    const art = grounding?.articulation || {}, criterion = grounding?.criterion || {};
    return '<h4>Conhecimento empregado</h4>'+para(label(grounding.knowledge))+para(grounding?.justification || criterion.justification)+trajectory(grounding)+
      '<h4>Como o conhecimento foi articulado</h4>'+para(art.operation)+para(art.added_understanding)+
      '<ul>'+(art.contributions || []).map(item => '<li>'+para(item.statement)+'<p><strong>Fonte:</strong> '+esc(item.source?.label || item.source?.title || item.source?.id || '')+
        ' — '+esc(item.locator || 'Localização não registrada')+'.</p>'+para(item.status === 'PRIMARY_CHECKED' ? 'Contribuição registrada com conferência da fonte primária.' : 'Contribuição preservada de registro anterior; não equivale a nova leitura do documento original.')+'</li>').join('')+'</ul>'+para(art.interpretation)+
      '<h4>Critério empregado</h4>'+para(label(criterion))+para(criterion.justification)+
      '<p><strong>Origem do critério:</strong> '+esc(criterion.source?.label || criterion.source?.title || criterion.source?.id || 'Não registrada')+' — '+esc(criterion.locator || 'Localização não registrada')+'.</p>';
  };
  return [...(response.choices || []),...(response.pending_candidates || []),...(response.partial_segments || [])].map(choice =>
    '<details><summary>'+esc((choice.steps || []).map(step => step.label).join(' → '))+'</summary>'+
    (choice.steps || []).map(step => '<h3>'+esc(step.label)+'</h3>'+conditions(step.condition_checks)+
      (step.groundings || []).map(sources).join('')).join('')+
    (choice.relations || []).map(relation => '<h3>Por que as etapas se conectam</h3>'+para(relation.explanation)+conditions(relation.condition_checks)+sources(relation.grounding)).join('')+'</details>').join('');
}
$('#generate-orientation').addEventListener('click',() => {
  if (!$('#case-confirmed').checked) return;
  run(async expected => {
    if (mode === 'legacy') {
      current = await request('update',{payload:{mapping_confirmed:true,transfer_confirmed:false}});
      result = await request('generate');
    } else {
      const {evidence,...context} = draft; result = await request('compose',{payload:{...context,confirmed:true}});
    }
    if (expected !== epoch) return;
    if (mode === 'legacy') legacyOutput(result); else compositionOutput(result);
    $('#orientation-foundation-body').replaceChildren();
    $('#orientation-case-body').innerHTML = para($('#case-narrative').value)+fieldsHTML(summaryRows());
    for (const id of ['orientation-details','orientation-foundations','orientation-case']) $('#'+id).open = false;
    $('#reading-message').textContent = ''; status(''); screen('orientation-result','orientation-title');
  },'Construindo a orientação para seu caso…');
});
$('#orientation-foundations').addEventListener('toggle',() => {
  if (!$('#orientation-foundations').open || !result) return;
  if (mode === 'legacy') renderExplanation($('#orientation-foundation-body'),result);
  else $('#orientation-foundation-body').innerHTML = compositionFoundations(result);
});
$('#new-case').addEventListener('click',() => run(async expected => {
  voice.clear(); invalidate(); current = draft = null; skipped.clear(); exampleId = exampleNarrative = null;
  organizedNarrative = null;
  $('#case-narrative').value = ''; $('#case-template').value = ''; $('#question-fields').replaceChildren();
  await request('clear'); if (expected === epoch) { $('#new-case').hidden = true; status(''); screen('case-entry'); $('#case-narrative').focus(); }
},''));
$('#read-orientation').addEventListener('click',() => {
  if (!('speechSynthesis' in window)) { $('#reading-message').textContent = 'A leitura em voz não está disponível neste navegador. A orientação continua em texto.'; return; }
  const voice = speechSynthesis.getVoices().find(item => item.localService && /^pt/i.test(item.lang));
  if (!voice) { $('#reading-message').textContent = 'Não foi encontrada uma voz local em português. Você pode ler a orientação em texto.'; return; }
  speechSynthesis.cancel(); const utterance = new SpeechSynthesisUtterance(speechText);
  utterance.voice = voice; utterance.lang = voice.lang;
  utterance.onend = () => $('#reading-message').textContent = 'Leitura concluída.';
  utterance.onerror = () => $('#reading-message').textContent = 'Leitura interrompida. A orientação continua em texto.';
  $('#reading-message').textContent = 'Lendo a orientação. Use Parar leitura para interromper.'; speechSynthesis.speak(utterance);
});
$('#stop-reading').addEventListener('click',() => { if ('speechSynthesis' in window) speechSynthesis.cancel(); $('#reading-message').textContent = 'Leitura interrompida.'; });
async function load() {
  await run(async expected => {
    $('#health').dataset.state = 'loading'; $('#health').textContent = 'Preparando o AMADO…'; $('#retry-load').hidden = true;
    try {
      await request('initialize'); catalog = await request('catalog');
      $('#case-template').innerHTML = '<option value="">Selecione um exemplo…</option>'+catalog.templates.map(item => '<option value="'+esc(item.id)+'">'+esc(item.titulo_curto || item.texto_curto)+'</option>').join('')+
        '<option value="composition-example">Escrever e conferir um texto com outra forma de interação</option>';
      if (expected !== epoch) return;
      $('#health').dataset.state = 'ready'; $('#health').textContent = '';
    } catch (error) {
      $('#health').dataset.state = 'error'; $('#health').textContent = 'Não foi possível carregar o AMADO.';
      $('#retry-load').hidden = false; throw error;
    }
  });
  $('#analyze-case').disabled = $('#health').dataset.state !== 'ready';
}
$('#retry-load').addEventListener('click',() => { ++epoch; busy = false; restart(); load(); });
window.addEventListener('pagehide',() => voice.clear());
load();
