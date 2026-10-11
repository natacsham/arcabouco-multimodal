import {request, restart} from './client.mjs';
import {renderExplanation} from '../explanation.js';
import {setupDictation} from './voice.js';
import {legacyQuestions, legacyAnswer, legacySummary, participantName, detectCompositionTask,
  compositionDraft, compositionQuestions, compositionSummary} from './intake.mjs';

const $ = selector => document.querySelector(selector);
const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const para = value => value ? '<p>'+esc(value)+'</p>' : '';
const list = values => {
  const items = Array.isArray(values) ? values : values ? [values] : [];
  return items.length ? '<ul>'+items.map(value => '<li>'+esc(typeof value === 'object' ? value.label || value.title || value.titulo || '' : value)+'</li>').join('')+'</ul>' : '';
};
let catalog, compositionCatalog, current, mode = 'legacy', draft, result, busy = false, epoch = 0;
let questions = [], answered = new Set(), handled = new Set(), exampleNarrative = null, exampleId = null, speechText = '', organizedNarrative = null;
const unknown = value => typeof value === 'string' && /^(?:ainda )?nao sei(?: ainda)?[.!]?$/.test(value.normalize('NFD').replace(/\p{M}/gu,'').toLowerCase().trim());
function resetQuestions() { answered.clear(); handled.clear(); }
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
async function run(action, message='', generating=false) {
  if (busy) return;
  busy = true; const expected = epoch; $('#main').setAttribute('aria-busy','true');
  $('#flow-error').textContent = ''; status(message);
  $('#generation-progress').hidden = !generating;
  if (generating) {
    $('#generate-orientation').textContent = 'Gerando orientação…';
    $('#generation-progress').scrollIntoView({block:'center',behavior:'instant'});
  }
  const controls = [...document.querySelectorAll('#main button,#main input,#main textarea,#main select')].map(element => [element,element.disabled]);
  controls.forEach(([element]) => element.disabled = true);
  let recoveryFocus;
  try { await action(expected); }
  catch (error) {
    if (expected === epoch) { $('#flow-error').textContent = error.message || String(error); status(''); recoveryFocus = error.field; }
  } finally {
    if (expected === epoch) {
      busy = false; $('#main').setAttribute('aria-busy','false');
      $('#generation-progress').hidden = true;
      $('#generate-orientation').textContent = 'Gerar orientação';
      controls.forEach(([element,disabled]) => element.disabled = disabled);
      $('#generate-orientation').disabled = !$('#case-confirmed').checked;
      $('#load-example').disabled = !$('#case-template').value;
      if (recoveryFocus) $('#'+recoveryFocus)?.focus();
    }
  }
}
function questionMarkup(question) {
  const id = question.id, description = ' aria-describedby="question-person question-context question-help"',
    base = '<fieldset class="question" data-question="'+esc(id)+'"'+description+'><legend class="sr-only">'+esc(question.label)+(question.participant_label ? ' — '+esc(question.participant_label) : '')+'</legend>';
  if (question.type === 'text') return base+'<label class="sr-only" for="answer-'+esc(id)+'">'+esc(question.label)+'</label><textarea id="answer-'+esc(id)+'" name="'+esc(id)+'"'+description+' rows="2"></textarea></fieldset>';
  if (question.type === 'single') return base+'<div class="question-options question-single">'+question.options.map(option =>
    '<label><input type="radio" name="'+esc(id)+'" value="'+esc(option.id)+'"> '+esc(option.label)+'</label>').join('')+'</div></fieldset>';
  const checkbox = (option,index) => '<label><input type="checkbox" name="'+esc(id)+'" value="'+esc(option.id)+'"> '+esc(option.label)+'</label>';
  const initial = question.options.slice(0,6), other = question.options.slice(6);
  const note = question.note_label ? '<div class="question-note"><label for="note-'+esc(id)+'">'+esc(question.note_label)+'</label><textarea id="note-'+esc(id)+'" name="'+esc(id)+':note"'+description+' maxlength="2000" rows="2"></textarea></div>' : '';
  return base+'<div class="question-options">'+initial.map(checkbox).join('')+'</div>'+
    (other.length ? '<details><summary>Ver outras respostas possíveis</summary><div class="question-options">'+other.map(checkbox).join('')+'</div></details>' : '')+
    '<label class="question-unknown"><input type="checkbox" name="'+esc(id)+'" value="unknown"> Ainda não sei</label>'+note+'</fieldset>';
}
function unanswered() {
  return (mode === 'legacy' ? legacyQuestions(current,catalog) : compositionQuestions(draft,compositionCatalog)).filter(question => !answered.has(question.id) && !handled.has(question.id));
}
function askOrReview() {
  $('#new-case').hidden = false;
  // One missing piece at a time; the rest of the decomposition stays internal.
  const pending = unanswered();
  questions = pending.slice(0,1);
  if (!questions.length) { review(); return; }
  $('#questions-title').textContent = questions[0].label;
  $('#question-progress').textContent = 'Pergunta '+(answered.size+1)+' de '+(answered.size+pending.length)+' previstas';
  $('#question-progress').dataset.current = String(answered.size+1);
  $('#question-progress').dataset.total = String(answered.size+pending.length);
  $('#question-progress-help').textContent = 'As próximas perguntas dependem das suas respostas.';
  $('#question-person').textContent = questions[0].participant_label || '';
  $('#question-person').hidden = !questions[0].participant_label;
  $('#question-context').textContent = questions[0].context_label || '';
  $('#question-context').hidden = !questions[0].context_label;
  $('#question-help').textContent = questions[0].help || '';
  $('#question-help').hidden = !questions[0].help;
  $('#question-fields').innerHTML = questions.map(questionMarkup).join('');
  $('#answer-unknown').hidden = questions[0].type !== 'text';
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
  voice.clear(); invalidate();
  const text = $('#case-narrative').value.trim();
  if (text.length < 20) {
    $('#case-narrative').setAttribute('aria-invalid','true');
    throw Object.assign(new Error('Descreva o que a pessoa precisa fazer e o que dificulta a atividade.'),{field:'case-narrative'});
  }
  $('#case-narrative').removeAttribute('aria-invalid');
  if (organizedNarrative === text && (mode === 'legacy' ? current : draft)) { askOrReview(); return; }
  resetQuestions();
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
      let value = question.type === 'multi' ? controls.filter(field => field.checked).map(field => field.value) :
        question.type === 'single' ? controls.find(field => field.checked)?.value : controls[0]?.value.trim();
      const typedNote = document.getElementsByName(question.id+':note')[0]?.value.trim() || '';
      const note = unknown(typedNote) ? '' : typedNote;
      const isUnknown = !value || value === 'unknown' || unknown(value) || Array.isArray(value) && (!value.length || value.includes('unknown'));
      if (isUnknown) value = null;
      if (mode === 'legacy' && (!isUnknown || note && question.participant_id)) current = await request('update',{payload:legacyAnswer(current,question,value,note)});
      else if (mode !== 'legacy' && !isUnknown) {
        const target = question.participant_id ? draft.participants?.find(person => person.id === question.participant_id) : draft;
        if (target) { target[question.field] ||= {}; target[question.field][question.concept_id] = value === 'true'; }
      }
      // Finish this conversation step, not all semantic requirements for the field.
      // Unselected options and unknown answers remain unknown in the engine.
      answered.add(question.id);
      (question.handles_ids || []).forEach(id => handled.add(id));
    }
    if (expected === epoch) askOrReview();
  },'Atualizando as informações…');
});
$('#answer-unknown').addEventListener('click',() => {
  const field = document.getElementsByName(questions[0]?.id)[0];
  if (field) field.value = 'Ainda não sei';
  $('#questions-form').requestSubmit();
});
$('#skip-questions').addEventListener('click',review);
$('#case-confirmed').addEventListener('change',() => {
  $('#generate-orientation').disabled = !$('#case-confirmed').checked;
  if (!$('#case-confirmed').checked) invalidate();
});
$('#case-narrative').addEventListener('input',() => {
  invalidate(); resetQuestions();
  $('#case-narrative').removeAttribute('aria-invalid');
  if ($('#case-narrative').value.trim() !== exampleNarrative) { exampleId = exampleNarrative = null; $('#case-template').value = ''; }
});
$('#case-template').addEventListener('change',() => { $('#load-example').disabled = !$('#case-template').value; });
$('#load-example').addEventListener('click',() => run(async expected => {
  voice.clear(); invalidate(); resetQuestions();
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
  voice.clear(); invalidate(); status(''); $('#flow-error').textContent = '';
  screen('case-entry'); $('#case-narrative').focus();
}
$('#edit-case').addEventListener('click',edit);
document.querySelectorAll('[data-edit-case]').forEach(button => button.addEventListener('click',edit));
function legacyOutput(response) {
  const decision = response.decision, summary = decision.sintese_pratica || {};
  const configurations = decision.configuracao_modal || [];
  const suspended = decision.status.startsWith('SUSPENSA') || !configurations.length;
  const partial = decision.status === 'GERADA_PARCIAL';
  const unique = values => [...new Set(values.filter(Boolean))];
  const gaps = decision.informacoes_ausentes || [];
  const pendingQuestions = gaps.filter(value => /\?/.test(value) && !/^A necessidade |^Função requerida/.test(value));
  const uncoveredPeople = (decision.participant_coverage || []).filter(person => person.status === 'SEM_ROTA_FUNDAMENTADA');
  $('#orientation-title').textContent = suspended ? 'O que falta para orientar este caso' : 'Orientação para o seu caso';
  $('#orientation-state').textContent = suspended ? 'Ainda sem orientação' : partial ? 'Apoio para parte do desafio' : 'Orientação construída';
  const card = step => {
    const rows = configurations.filter(item => (step.component_ids || []).includes(item.component_id));
    const resources = step.recursos_estruturados || rows.flatMap(item => item.resource_options || []);
    const pending = unique(resources.filter(item => !item.opcional && item.estado === 'NAO_CONFIRMADO').map(item => item.label));
    const preparation = unique(resources.filter(item => !item.opcional && item.estado === 'PROPOSTO_A_PREPARAR').map(item => item.label));
    const conditions = unique(step.condicoes || rows.flatMap(item => item.conditions || []));
    const responsible = unique(rows.map(item => item.responsavel));
    const people = (decision.participant_coverage || []).filter(person =>
      (person.component_ids || []).some(id => (step.component_ids || []).includes(id)));
    const limits = unique(rows.map(item => item.limit));
    const alternatives = unique(step.alternativas || rows.map(item => item.alternative));
    const monitoring = unique(step.acompanhamento || rows.map(item => item.monitoring));
    const conditional = rows.some(item => item.availability_status === 'CONDICIONAL_A_CONFIRMACAO');
    const actions = step.itens?.length ? step.itens : rows.map(item => item.acao);
    return '<article class="orientation-step"><h3>'+esc(step.titulo)+'</h3>'+
      actions.filter(Boolean).map(action => '<p class="step-action">'+esc(action)+'</p>').join('')+
      (step.como_combinar ? '<p class="step-combination"><strong>Como as formas se combinam:</strong> '+esc(step.como_combinar)+'</p>' : '')+
      (people.length ? '<p class="step-responsibility"><strong>Participantes relacionados a esta opção:</strong> '+esc(people.map(person => participantName(person)).join('; '))+'. Confira a forma de acesso com cada pessoa.</p>' : '')+
      (responsible.length ? '<p class="step-responsibility"><strong>Quem participa da aplicação:</strong> '+esc(responsible.join('; '))+'</p>' : '')+
      ((pending.length || preparation.length || conditions.length || conditional) ? '<div class="step-conditions">'+
        (pending.length ? '<p><strong>Antes de usar, confirme:</strong> '+esc(pending.join('; '))+'.</p>' : '')+
        (preparation.length ? '<p><strong>Precisa preparar:</strong> '+esc(preparation.join('; '))+'.</p>' : '')+
        (conditional && !pending.length ? '<p><strong>Uso condicionado:</strong> confira as condições desta opção antes de utilizá-la.</p>' : '')+
        conditions.map(condition => '<p><strong>Condição de uso:</strong> '+esc(condition)+'</p>').join('')+'</div>' : '')+
      ((alternatives.length || monitoring.length || limits.length) ? '<details><summary>Cuidados, alternativas e acompanhamento</summary>'+
        (alternatives.length ? '<h4>Se esta opção não funcionar</h4>'+list(alternatives) : '')+
        (monitoring.length ? '<h4>O que observar</h4>'+list(monitoring) : '')+
        (limits.length ? '<h4>Limites desta opção</h4>'+list(limits) : '')+'</details>' : '')+'</article>';
  };
  if (suspended) {
    $('#orientation-main').innerHTML = '<div class="orientation-gaps">'+
      para(pendingQuestions.length ? 'Precisamos esclarecer estes pontos para verificar quais formas de apoio se aplicam ao seu caso.' :
        'Com as informações confirmadas, a base ainda não encontrou uma forma de apoio aplicável a este caso.')+
      (pendingQuestions.length ? list(pendingQuestions) : para('Os motivos e os apoios que ficaram sem cobertura estão disponíveis nos detalhes abaixo.'))+'</div>';
  } else {
    const steps = summary.etapas?.length ? summary.etapas : configurations.map(item => ({
      titulo: item.modo, itens: [item.acao], component_ids: [item.component_id]
    }));
    $('#orientation-main').innerHTML = para(summary.texto || decision.orientacao_principal)+
      '<div class="orientation-cards">'+steps.map(card).join('')+'</div>'+
      ((partial || uncoveredPeople.length) ? '<aside class="orientation-gaps"><h3>O que ainda precisa de apoio</h3>'+
        para('As opções acima apoiam parte do desafio. Elas ainda não cobrem tudo o que foi informado.')+
        (uncoveredPeople.length ? '<p><strong>Ainda sem uma forma de acesso fundamentada:</strong> '+esc(uncoveredPeople.map(person => participantName(person)).join('; '))+'.</p>' : '')+
        (gaps.length ? '<details><summary>Conferir os pontos que ficaram em aberto</summary>'+list(gaps)+'</details>' : '')+'</aside>' : '');
  }
  $('#orientation-detail-body').innerHTML = para(decision.orientacao_principal)+
    configurations.map(item => '<h3>'+esc(item.modo)+'</h3>'+para(item.funcao)+para(item.acao)).join('')+
    '<h3>Condições</h3>'+list(decision.condicoes)+'<h3>Alternativas</h3>'+list(decision.alternativa ? [decision.alternativa] : decision.alternativas)+
    '<h3>Acompanhamento</h3>'+list(decision.acompanhamento)+'<h3>Limites</h3>'+para(decision.limite)+list(decision.informacoes_ausentes);
  speechText = $('#orientation-main').innerText;
}
function compositionOutput(response) {
  const names = new Map(Object.entries(compositionCatalog.labels || {}));
  const label = item => typeof item === 'object' && item ? item.label || label(item.id) : names.get(item) || names.get(String(item || '').split('#').pop()) || String(item || '').split('#').pop();
  const unique = values => [...new Set(values.filter(Boolean))];
  const state = {COMPLETE:'Orientação construída',CONDITIONAL:'Há possibilidades a confirmar',PARTIAL:'Apoio para parte do desafio',
    INSUFFICIENT:'Ainda sem orientação completa',NONE:'Ainda sem orientação'};
  $('#orientation-state').textContent = state[response.proposal_status] || 'Confira as condições';
  const people = response.participant_results || [];
  const localResults = people.length ? people.map(person => person.result) : [response];
  const hasPossibilities = localResults.some(local => (local.choices || []).length || (local.pending_candidates || []).length || (local.partial_segments || []).length);
  const groupHeading = people.length ? 'h4' : 'h3', choiceHeading = people.length ? 'h5' : 'h4';
  $('#orientation-title').textContent = hasPossibilities ? 'Orientação para o seu caso' : 'O que falta para orientar este caso';
  const card = (choice, kind, local) => {
    const steps = choice.steps || [], relations = choice.relations || [];
    const pending = unique([...steps, ...relations].flatMap(item => item.condition_checks || [])
      .filter(check => check.state === 'PENDING').map(check => label(check.observed?.concept || check.expected?.concept) || check.explanation));
    const linkedPending = [...(local.facts_to_confirm || []), ...(local.resources_to_confirm || [])]
      .filter(item => (item.candidate_ids || []).includes(choice.id)).map(label);
    const conditions = unique([...pending, ...linkedPending]);
    const limitations = unique([...(choice.limits || []), ...steps.map(step => step.limitation)]);
    return '<article class="orientation-step"><'+choiceHeading+'>'+esc(steps.map(step => step.label).join(' → ') || 'Possibilidade de apoio')+'</'+choiceHeading+'>'+
      (kind === 'pending' ? '<p class="step-conditions"><strong>A confirmar:</strong> esta possibilidade ainda depende das condições indicadas abaixo.</p>' : '')+
      steps.map(step => '<p class="step-action">'+esc(step.action)+'</p>').join('')+
      relations.map(relation => '<p class="step-combination"><strong>Como as etapas se conectam:</strong> '+esc(relation.explanation)+'</p>').join('')+
      (conditions.length ? '<div class="step-conditions"><p><strong>Antes de usar, confirme:</strong></p>'+list(conditions)+'</div>' : '')+
      (choice.entry ? '<p class="step-conditions"><strong>Esta parte depende de:</strong> '+esc(label(choice.entry.representation))+'. '+
        (choice.entry.availability_verified ? 'Essa entrada foi conferida nesta execução.' : 'A disponibilidade dessa entrada ainda não foi verificada.')+'</p>' : '')+
      (choice.missing_functions?.length ? '<p class="step-conditions"><strong>Esta opção ainda não cobre:</strong> '+esc(choice.missing_functions.map(label).join('; '))+'.</p>' : '')+
      (limitations.length ? '<details><summary>Cuidados e limites desta opção</summary>'+list(limitations)+'</details>' : '')+'</article>';
  };
  const view = local => {
    const groups = [
      ['complete', 'Opções para realizar a atividade', local.choices || [], 'As condições necessárias destas opções foram confirmadas para o caso informado.'],
      ['partial', 'Apoio para uma parte da atividade', local.partial_segments || [], 'Estas partes têm fundamento, mas não formam uma orientação completa. Confira a entrada necessária e o que ficou de fora.'],
      ['pending', 'Possibilidades que precisam de confirmação', local.pending_candidates || [], 'Estas opções ainda não estão prontas para uso; dependem das informações indicadas em cada cartão.']
    ];
    const visible = groups.filter(([, , choices]) => choices.length);
    if (!visible.length) {
      const missing = unique([...(local.facts_to_confirm || []), ...(local.resources_to_confirm || [])].map(label));
      return '<div class="orientation-gaps">'+para('Ainda não encontramos uma combinação fundamentada para as condições confirmadas.')+
        (missing.length ? '<p><strong>Precisamos confirmar:</strong></p>'+list(missing) : para('Confira nos detalhes quais apoios e etapas ficaram sem cobertura.'))+'</div>';
    }
    return visible.map(([kind, title, choices, explanation]) => '<section class="orientation-group"><'+groupHeading+'>'+esc(title)+'</'+groupHeading+'>'+para(explanation)+
      '<div class="orientation-cards">'+choices.map(choice => card(choice,kind,local)).join('')+'</div></section>').join('');
  };
  $('#orientation-main').innerHTML = people.length ? people.map(person => '<section class="participant-orientation"><h3>'+esc(person.label)+'</h3>'+view(person.result)+'</section>').join('') : view(response);
  const details = local => {
    const choices = [...(local.choices || []), ...(local.pending_candidates || []), ...(local.partial_segments || [])];
    return '<h3>Condições a confirmar</h3>'+list([...(local.facts_to_confirm || []), ...(local.resources_to_confirm || [])].map(label))+
      (local.unavailable_conditions?.length ? '<h3>Condições informadas como indisponíveis</h3>'+list(local.unavailable_conditions.map(label)) : '')+
      '<h3>Limites</h3>'+list(local.limits)+choices.map(choice => list(choice.limits)+(choice.steps || []).map(step => para(step.limitation)).join('')).join('');
  };
  $('#orientation-detail-body').innerHTML = people.length ? people.map(person => '<section><h3>'+esc(person.label)+'</h3>'+details(person.result)+'</section>').join('') : details(response);
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
    const pending = mode === 'legacy' ? legacyQuestions(current,catalog) : compositionQuestions(draft,compositionCatalog);
    $('#complete-information').hidden = !pending.length;
    $('#orientation-foundation-body').replaceChildren();
    $('#orientation-case-body').innerHTML = para($('#case-narrative').value)+fieldsHTML(summaryRows());
    for (const id of ['orientation-details','orientation-foundations','orientation-case']) $('#'+id).open = false;
    $('#reading-message').textContent = ''; status(''); screen('orientation-result','orientation-title');
    // Read the visible layout: hidden containers do not retain paragraph breaks in innerText.
    speechText = $('#orientation-main').innerText;
  },'Relacionando seu caso aos conhecimentos da base…',true);
});
$('#complete-information').addEventListener('click',() => {
  const pending = mode === 'legacy' ? legacyQuestions(current,catalog) : compositionQuestions(draft,compositionCatalog);
  // Reopen unanswered requirements only on this explicit user request.
  for (const question of pending) { answered.delete(question.id); handled.delete(question.id); }
  invalidate(); askOrReview();
});
$('#orientation-foundations').addEventListener('toggle',() => {
  if (!$('#orientation-foundations').open || !result) return;
  if (mode === 'legacy') renderExplanation($('#orientation-foundation-body'),result);
  else $('#orientation-foundation-body').innerHTML = compositionFoundations(result);
});
$('#new-case').addEventListener('click',() => run(async expected => {
  voice.clear(); invalidate(); current = draft = null; resetQuestions(); exampleId = exampleNarrative = null;
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
