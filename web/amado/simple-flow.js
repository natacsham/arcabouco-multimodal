import {request, restart} from './client.mjs';
import {renderExplanation} from '../explanation.js';
import {setupDictation} from './voice.js';
import {situatedOutput} from './situated-output.mjs';
import {legacyQuestions, legacyAnswer, legacySummary, accessRequirementSummary, participantName,
  compositionDraft, compositionQuestions, compositionSummary, questionRound,legacyEditor,legacyRevision,
  compositionEditor,compositionRevision,usedSourceRecords,reviewContext} from './intake.mjs';

const $ = selector => document.querySelector(selector);
const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const para = value => value ? '<p>'+esc(value)+'</p>' : '';
const list = values => {
  const items = Array.isArray(values) ? values : values ? [values] : [];
  return items.length ? '<ul>'+items.map(value => '<li>'+esc(typeof value === 'object' ? value.label || value.title || value.titulo || '' : value)+'</li>').join('')+'</ul>' : '';
};
let catalog, compositionCatalog, current, mode = 'legacy', draft, result, busy = false, epoch = 0;
let questions = [], refinementQuestions = [], answered = new Set(), handled = new Set(), exampleNarrative = null, exampleId = null, speechText = '', organizedNarrative = null;
let roundAnswered = 0, clarificationRound = 1;
let editorRows=[], editorReturn='case-review', editorContext=null, reading=false;
// One control changes state instead of exposing separate start/stop actions.
$('#stop-reading').hidden=true;
$('#read-orientation').textContent='Ouvir';
function stopReading(message='') {
  if ('speechSynthesis' in window) speechSynthesis.cancel();
  reading=false; $('#read-orientation').textContent='Ouvir';
  $('#read-orientation').setAttribute('aria-pressed','false');
  $('#reading-message').textContent=message;
}
const unknown = value => typeof value === 'string' && /^(?:ainda )?nao sei(?: ainda)?[.!]?$/.test(value.normalize('NFD').replace(/\p{M}/gu,'').toLowerCase().trim());
function resetQuestions() { answered.clear(); handled.clear(); refinementQuestions=[]; roundAnswered = 0; clarificationRound = 1; }
const voice = setupDictation({button:$('#dictate-case'),input:$('#case-narrative'),status:$('#dictation-status'),
  preview:$('#dictation-preview'),dialog:$('#speech-consent'),allow:$('#allow-browser-dictation'),cancel:$('#cancel-dictation')});
function status(text) { $('#flow-status').textContent = text; }
function invalidate() {
  result = null; $('#orientation-result').hidden = true; $('#case-confirmed').checked = false;
  $('#generate-orientation').disabled = true;
  renderExplanation($('#orientation-foundation-body'), {});
  stopReading();
}
function screen(id, focus) {
  for (const name of ['case-entry','case-understanding','case-editor','case-questions','case-review','orientation-result']) $('#'+name).hidden = name !== id;
  if (focus) $('#'+focus).focus();
}
async function run(action, message='', generating=false) {
  if (busy) return;
  busy = true; const expected = epoch; $('#main').setAttribute('aria-busy','true');
  $('#flow-error').textContent = ''; status(message);
  $('#generation-progress').hidden = !generating;
  if (generating) {
    $('#generation-stages').replaceChildren();
    $('#generation-status').textContent='Preparando as informações confirmadas.';
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
function generationStage(event) {
  if(!busy || $('#generation-progress').hidden)return;
  const allowed={initialization:'Carregar a base no navegador',retrieval:'Recuperar conhecimentos da base MADO',
    verification:'Conferir condições e fundamentos',composition:'Compor a orientação',presentation:'Apresentar o resultado'};
  if(!allowed[event.stage])return;
  const states={running:'Em andamento',completed:'Concluída',failed:'Interrompida',cancelled:'Cancelada'};
  let item=$('#generation-stages').querySelector('[data-stage="'+event.stage+'"]');
  if(!item){item=document.createElement('li');item.dataset.stage=event.stage;$('#generation-stages').append(item);}
  item.dataset.state=event.state;
  item.textContent=allowed[event.stage]+' — '+(states[event.state] || event.state);
  $('#generation-status').textContent=event.message || item.textContent;
}
function questionMarkup(question) {
  const id = question.id, description = ' aria-describedby="question-person question-context question-help"',
    base = '<fieldset class="question" data-question="'+esc(id)+'"'+description+'><legend class="sr-only">'+esc(question.label)+(question.participant_label ? ' — '+esc(question.participant_label) : '')+'</legend>';
  if (question.type === 'text') return base+'<label class="sr-only" for="answer-'+esc(id)+'">'+esc(question.label)+'</label><textarea id="answer-'+esc(id)+'" name="'+esc(id)+'"'+description+' rows="2"></textarea></fieldset>';
  if (question.type === 'single') {
    const choices = question.options.some(option => option.id === 'unknown') ? question.options :
      [...question.options, {id:'unknown',label:'Ainda não sei'}];
    return base+'<div class="question-options question-single">'+choices.map(option =>
      '<label><input type="radio" name="'+esc(id)+'" value="'+esc(option.id)+'"> '+esc(option.label)+'</label>').join('')+'</div></fieldset>';
  }
  const checkbox = (option,index) => '<label><input type="checkbox" name="'+esc(id)+'" value="'+esc(option.id)+'"> '+esc(option.label)+'</label>';
  const initial = question.options.slice(0,6), other = question.options.slice(6);
  const note = question.note_label ? '<div class="question-note"><label for="note-'+esc(id)+'">'+esc(question.note_label)+'</label><textarea id="note-'+esc(id)+'" name="'+esc(id)+':note"'+description+' maxlength="2000" rows="2"></textarea></div>' : '';
  return base+'<div class="question-options">'+initial.map(checkbox).join('')+'</div>'+
    (other.length ? '<details><summary>Ver outras respostas possíveis</summary><div class="question-options">'+other.map(checkbox).join('')+'</div></details>' : '')+
    '<label class="question-unknown"><input type="checkbox" name="'+esc(id)+'" value="unknown"> Ainda não sei</label>'+note+'</fieldset>';
}
function unanswered() {
  return [...(mode === 'legacy' ? legacyQuestions(current,catalog) : compositionQuestions(draft,compositionCatalog)),...refinementQuestions].filter(question => !answered.has(question.id) && !handled.has(question.id));
}
function askOrReview() {
  $('#new-case').hidden = false;
  // At most three pertinent clarifications before confirming the understanding.
  // Later refinement is opt-in and does not erase answered or unknown fields.
  const pending = unanswered();
  const round = questionRound(pending, answered, handled, roundAnswered);
  questions = round.questions.slice(0,1);
  if (!questions.length) { review(); return; }
  $('#questions-title').textContent = questions[0].label;
  $('#question-progress').textContent = 'Pergunta '+round.current+' de até '+round.total;
  $('#question-progress').dataset.current = String(round.current);
  $('#question-progress').dataset.total = String(round.total);
  $('#question-progress').dataset.round = String(clarificationRound);
  $('#question-progress-help').textContent = 'Depois, você confere o que entendemos. Pode seguir sem responder.';
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
function understanding() {
  const rows=summaryRows(), preferred=['Pessoas','Sua participação','Situações identificadas','Atividade','Objetivo','Onde acontece','Aplicativo ou conteúdo'];
  const selected=preferred.map(label=>rows.find(row=>row.label===label)).filter(Boolean);
  $('#understanding-summary').innerHTML=selected.length?'<dl class="review-summary">'+selected.map(row=>'<div><dt>'+esc(row.label)+'</dt><dd>'+esc(row.value)+'</dd></div>').join('')+'</dl>':para($('#case-narrative').value.trim());
  const pending=unanswered();
  $('#understanding-next').textContent=pending.length?'Vamos esclarecer até três pontos sobre este contexto para direcionar o apoio. Você pode responder somente o que souber.':'Já há informações para conferir o caso e consultar as possibilidades da base.';
  $('#continue-understanding').textContent=pending.length?'Responder às perguntas':'Conferir o caso';
  status('');screen('case-understanding','understanding-title');
}
$('#continue-understanding').addEventListener('click',askOrReview);
function fieldsHTML(rows) {
  return '<div class="review-fields">'+rows.map(row => '<div class="review-field"><strong>'+esc(row.label)+'</strong>'+para(row.value)+'</div>').join('')+'</div>';
}
function requirementsHTML() {
  if (mode !== 'legacy') return '';
  const rows = accessRequirementSummary(current);
  if (!rows.length) return '';
  return '<details class="review-requirements"><summary>O que a base acrescenta ao seu relato</summary>'+
    '<p>São requisitos de acesso recuperados das fontes, não habilidades individuais ou recursos já confirmados.</p>'+
    rows.map(row => '<section><h3>'+esc(row.participant)+'</h3>'+list(row.requirements.length ? row.requirements : [row.description])+
      (row.needsConfirmation ? '<p><strong>Precisa de conferência:</strong> há informações conflitantes neste requisito.</p>' : '')+
      '<details><summary>Conferir o fundamento deste requisito</summary>'+para(row.description)+
      (row.matchedText ? '<p><strong>Informação utilizada do relato:</strong> '+esc(row.matchedText)+'</p>' : '')+
      para(row.conditions)+para(row.limit)+
      '<p><strong>Registros de origem:</strong> '+esc([row.matrixId,...row.sourceIds,...row.excerptIds].filter(Boolean).join(' · '))+'</p></details></section>').join('')+'</details>';
}
function review() {
  invalidate();
  const rows = summaryRows(), narrative = $('#case-narrative').value.trim();
  const find = label => rows.find(row => row.label === label)?.value || '';
  const concise = [['Atividade',find('Atividade')],['Objetivo',find('Objetivo')],['Pessoas',find('Pessoas')]]
    .filter(([,value]) => value && value !== narrative);
  $('#review-summary').innerHTML = concise.length ? '<dl class="review-summary">'+concise.map(([label,value]) =>
    '<div><dt>'+esc(label)+'</dt><dd>'+esc(value)+'</dd></div>').join('')+'</dl>' : para(narrative.length > 300 ? narrative.slice(0,300)+'…' : narrative);
  $('#review-summary').innerHTML += requirementsHTML();
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
  if (organizedNarrative === text && (mode === 'legacy' ? current : draft)) { understanding(); return; }
  resetQuestions();
  if (exampleNarrative === text && exampleId) {
    if (exampleId === 'composition-example') {
      mode = 'composition'; draft = structuredClone(compositionCatalog.synthetic_example.context); draft.confirmed = false;
    } else { mode = 'legacy'; current = await request('start',{template:exampleId}); }
  } else {
    exampleId = exampleNarrative = null;
    // A subject, group name or task phrase must not choose a different reasoner.
    mode = 'legacy'; await request('start');
    const response = await request('analyze',{payload:{narrative:text}});
    current = response.current;
  }
  if (expected !== epoch) return;
  organizedNarrative = text;
  understanding();
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
      if (mode === 'legacy' && question.field === 'situated_fact') current = await request('update',{payload:{
        situated_facts:[{participant_id:question.participant_id,situation_id:question.situation_id,
          fact_id:question.fact_id,value:isUnknown?null:value==='true',label:question.label,
          source_text:question.label+' — '+(isUnknown?'Ainda não sei':value==='true'?'Sim':'Não')}],
        mapping_confirmed:false}});
      else if (mode === 'legacy') current = await request('update',{payload:legacyAnswer(current,question,value,note)});
      else if (mode !== 'legacy' && !isUnknown) {
        const target = question.participant_id ? draft.participants?.find(person => person.id === question.participant_id) : draft;
        if (target) { target[question.field] ||= {}; target[question.field][question.concept_id] = value === 'true'; }
      }
      // Finish this conversation step, not all semantic requirements for the field.
      // Unselected options and unknown answers remain unknown in the engine.
      answered.add(question.id);
      roundAnswered++;
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
  if (expected === epoch) understanding();
},'Carregando o exemplo…'));
function editNarrative() {
  voice.clear(); invalidate(); status(''); $('#flow-error').textContent = '';
  screen('case-entry'); $('#case-narrative').focus();
}
function editorField(row,index) {
  const id='revision-'+index;
  if(row.type==='remove')return '<label class="revision-remove"><input type="checkbox" data-revision="'+esc(row.key)+'"> '+esc(row.label)+' (ao salvar)</label>';
  if(row.type==='text')return '<div class="revision-text"><label for="'+id+'">'+esc(row.label)+'</label><textarea id="'+id+'" data-revision="'+esc(row.key)+'" rows="2">'+esc(row.value)+'</textarea></div>';
  if(row.type==='single')return '<div class="revision-text"><label for="'+id+'">'+esc(row.label)+'</label><select id="'+id+'" data-revision="'+esc(row.key)+'">'+row.options.map(option=>'<option value="'+esc(option.id)+'"'+(option.id===row.value?' selected':'')+'>'+esc(option.label)+'</option>').join('')+'</select></div>';
  const chosen=row.options.filter(option=>row.value.includes(option.id));
  return '<details class="revision-options"><summary>'+esc(row.label)+' <span>'+esc(chosen.length?chosen.map(option=>option.label).join('; '):'Ainda não informado')+'</span></summary>'+
    '<label for="'+id+'-search">Filtrar opções</label><input type="search" id="'+id+'-search" data-revision-filter="'+esc(row.key)+'" placeholder="Digite parte da opção">'+
    '<fieldset class="question-options" data-revision="'+esc(row.key)+'"><legend class="sr-only">'+esc(row.label)+'</legend>'+row.options.map(option=>'<label><input type="checkbox" value="'+esc(option.id)+'"'+(row.value.includes(option.id)?' checked':'')+'> '+esc(option.label)+'</label>').join('')+'</fieldset><p>Sem opções marcadas, esta informação fica em aberto.</p></details>';
}
function edit() {
  if(!(mode==='legacy'?current:draft)){editNarrative();return;}
  editorReturn=['case-understanding','case-questions','case-review','orientation-result'].find(id=>!$('#'+id).hidden) || 'case-review';
  voice.clear();status('');$('#flow-error').textContent='';$('#editor-error').textContent='';
  editorContext=mode==='legacy'?reviewContext(current,result):null;
  editorRows=mode==='legacy'?legacyEditor(editorContext,catalog):compositionEditor(draft,compositionCatalog);
  const groups=[...new Set(editorRows.map(row=>row.group))];
  $('#editor-fields').innerHTML=groups.map(group=>'<section class="revision-group"><h3>'+esc(group)+'</h3>'+editorRows.map((row,index)=>row.group===group?editorField(row,index):'').join('')+'</section>').join('');
  if(mode==='legacy')$('#editor-fields').innerHTML+='<details class="revision-options"><summary>Adicionar uma pessoa ou responsável que ainda não aparece</summary><label for="revision-new-role">Papel nesta atividade</label><select id="revision-new-role"><option value="">Não adicionar</option>'+(catalog.concepts.PAPEL_NO_CONTEXTO || []).map(row=>'<option value="'+esc(row.id)+'">'+esc(row.label)+'</option>').join('')+'</select><label for="revision-new-label">Como identificar esta pessoa ou grupo (opcional)</label><input id="revision-new-label" maxlength="200"></details>';
  screen('case-editor','editor-title');
}
$('#edit-case').addEventListener('click',edit);
document.querySelectorAll('[data-edit-case]').forEach(button => button.addEventListener('click',edit));
document.querySelectorAll('[data-edit-narrative]').forEach(button=>button.addEventListener('click',editNarrative));
$('#cancel-editor').addEventListener('click',()=>screen(editorReturn,editorReturn==='orientation-result'?'orientation-title':editorReturn==='case-questions'?'questions-title':editorReturn==='case-understanding'?'understanding-title':'review-title'));
$('#editor-fields').addEventListener('input',event=>{
  const key=event.target.dataset.revisionFilter;if(!key)return;
  const field=[...$('#editor-fields').querySelectorAll('[data-revision]')].find(item=>item.dataset.revision===key);
  const value=event.target.value.normalize('NFD').replace(/\p{M}/gu,'').toLowerCase();
  for(const label of field.querySelectorAll('label'))label.hidden=!label.innerText.normalize('NFD').replace(/\p{M}/gu,'').toLowerCase().includes(value);
});
$('#editor-form').addEventListener('submit',event=>{
  event.preventDefault();run(async expected=>{
    const values={};
    for(const row of editorRows){const field=[...$('#editor-fields').querySelectorAll('[data-revision]')].find(item=>item.dataset.revision===row.key);values[row.key]=row.type==='multi'?[...field.querySelectorAll('input:checked')].map(input=>input.value):row.type==='remove'?field.checked:field.value;}
    if(mode==='legacy'){
      const payload=legacyRevision(editorContext,catalog,values),role=$('#revision-new-role')?.value;
      if(role)payload.participations.push({papel_id:role,label:$('#revision-new-label').value.trim(),caracteristica_ids:[],tarefa_ids:[],modalidade_ids:[],recurso_operado_ids:[]});
      current=await request('update',{payload});
    }else draft=compositionRevision(draft,compositionCatalog,values);
    if(expected===epoch){invalidate();review();status('Informações atualizadas. Confirme novamente antes de gerar a orientação.');}
  },'Atualizando as informações revisadas…');
});

function sourceDisclosure(response) {
  const rows=usedSourceRecords(response), states={SECAO_ORIGINAL_CONFERIDA:'Seção do documento original conferida',PRIMARY_CHECKED:'Contribuição conferida na fonte primária',
    CONFERIDA_NO_REGISTRO:'Conferida no registro preservado',CONFERIDA_NO_DOCUMENTO:'Conferida no documento',PENDENTE:'Conferência documental pendente',
    ITEM_PRESERVADO_NA_PLANILHA_AUTORITATIVA:'Item preservado na planilha; documento original não conferido nesta revisão'};
  const safeLink=(url,title)=>{try{const link=new URL(url);if(['http:','https:'].includes(link.protocol))return '<a href="'+esc(link.href)+'">'+esc(title)+'</a>';}catch{}return esc(title);};
  const unique=new Map();for(const row of rows){const key=[row.sourceId,row.location,row.statement,row.applicationState].join('|');if(!unique.has(key))unique.set(key,row);}
  $('#orientation-sources-body').innerHTML=unique.size?'<ul class="source-disclosure">'+[...unique.values()].map(row=>'<li><strong>'+safeLink(row.url,row.title || 'Fonte registrada')+'</strong>'+(row.location?' — '+esc(row.location):'')+para(row.statement)+
    (row.applicationState==='conditional'?'<p>Fundamenta uma possibilidade que ainda depende de confirmação.</p>':row.applicationState==='partial'?'<p>Fundamenta somente uma parte do apoio apresentado.</p>':'')+
    '<p class="source-state">'+esc(states[row.status] || 'Origem registrada; confira o estado documental nos detalhes técnicos.')+'</p></li>').join('')+'</ul>':para('Não há origens de aplicação detalhadas neste resultado. A presença de uma fonte no catálogo não significa que ela foi usada neste caso.');
  $('#orientation-sources').open=false;
}
function legacyOutput(response) {
  const decision = response.decision, summary = decision.sintese_pratica || {};
  const configurations = decision.configuracao_modal || [];
  const suspended = decision.status.startsWith('SUSPENSA') || !configurations.length;
  const partial = decision.status === 'GERADA_PARCIAL';
  const unique = values => [...new Set(values.filter(Boolean))];
  const gaps = decision.informacoes_ausentes || [];
  const pendingQuestions = gaps.filter(value => /\?/.test(value) && !/^A necessidade |^Função requerida/.test(value));
  const uncoveredPeople = (decision.participant_coverage || []).filter(person => person.status === 'SEM_ROTA_FUNDAMENTADA');
  $('#orientation-title').textContent = suspended ? 'O que falta para orientar este caso' : 'O que você pode fazer';
  $('#orientation-state').textContent = suspended ? 'Ainda sem orientação' : partial ? 'Apoio para parte do desafio' : 'Orientação construída';
  const foundations = componentIds => {
    const configurations = (response.explanation?.configurations || []).filter(item => componentIds.includes(item.component_id));
    const supports = configurations.flatMap(item => item.application?.supports || []);
    if (!supports.length) return '';
    const knowledge = new Map([...(response.traceability?.knowledge || []),...configurations.flatMap(item => item.construction?.knowledge || [])].map(item => [item.id,item]));
    const criteria = new Map((response.traceability?.criteria || []).map(item => [item.id,item]));
    const text = item => item?.enunciado || item?.statement || item?.title || item?.titulo || item?.label || '';
    return '<details class="step-foundation"><summary>Por que esta ação foi sugerida?</summary>'+supports.map(support =>
      para(support.justification || support.justificativa)+
      '<p><strong>Critério aplicado:</strong> '+esc(support.criterion_statement || text(support.criterion || criteria.get(support.criterion_id)) || 'Descrição não incluída neste retorno.')+'</p>'+
      '<p><strong>Conhecimento empregado:</strong></p>'+list((support.knowledge_ids || []).map(id => text(knowledge.get(id))).filter(Boolean))+
      ((support.origins || []).length ? '<details><summary>Conferir as origens deste critério</summary>'+support.origins.map(origin =>
        para(origin.document_paraphrase || origin.resumo_publico || origin.enunciado_publico || origin.texto || origin.item_texto || origin.aviso_publicacao)+
        '<p><strong>Localização:</strong> '+esc(origin.localizacao_publica || origin.localizacao || origin.pagina || origin.secao || 'Não detalhada neste retorno.')+'</p>'+
        ((/^https?:\/\//.test(origin.document_url || ''))?'<p><a href="'+esc(origin.document_url)+'">Consultar esta fonte e seção</a></p>':'')+
        '<p><strong>Registros:</strong> '+esc([origin.id,origin.fonte_id,origin.trecho_id].filter(Boolean).join(' · '))+'</p>').join('')+'</details>' : '')).join('')+'</details>';
  };
  const card = step => {
    const rows = configurations.filter(item => (step.component_ids || []).includes(item.component_id));
    const resources = step.recursos_estruturados || rows.flatMap(item => item.resource_options || []);
    const pending = unique(resources.filter(item => !item.opcional && item.estado === 'NAO_CONFIRMADO').map(item => item.label));
    const preparation = unique(resources.filter(item => !item.opcional && item.estado === 'PROPOSTO_A_PREPARAR').map(item => item.label));
    const conditions = unique(step.condicoes || rows.flatMap(item => item.conditions || []));
    const responsible = unique(rows.map(item => item.responsavel));
    const people = (decision.participant_coverage || []).filter(person =>
      (person.component_ids || []).some(id => (step.component_ids || []).includes(id)));
    const conditionalPeople = (decision.participant_coverage || []).filter(person =>
      (person.conditional_component_ids || []).some(id => (step.component_ids || []).includes(id)));
    const limits = unique(rows.map(item => item.limit));
    const alternatives = unique(step.alternativas || rows.map(item => item.alternative));
    const monitoring = unique(step.acompanhamento || rows.map(item => item.monitoring));
    const conditional = step.aplicabilidade === 'CONDICIONAL_A_CONFIRMACAO' || rows.some(item => item.availability_status === 'CONDICIONAL_A_CONFIRMACAO');
    const actions = step.passos?.length ? step.passos.map(item => item.texto) : step.itens?.length ? step.itens : rows.map(item => item.acao);
    return '<article class="orientation-step"><h3>'+esc(step.titulo)+'</h3>'+
      (conditional ? '<p class="step-conditional">'+esc(step.antes_de_usar || 'Possibilidade condicionada: confirme os pontos abaixo antes de aplicar.')+'</p>' : '')+
      '<h4>Como fazer</h4><ol class="action-instructions">'+actions.filter(Boolean).map(action => '<li class="step-action">'+esc(action)+'</li>').join('')+'</ol>'+
      (step.como_combinar ? '<p class="step-combination"><strong>Por que combinar estas formas:</strong> '+esc(step.como_combinar)+'</p>' : '')+
      (people.length ? '<p class="step-responsibility"><strong>Participantes relacionados a esta opção:</strong> '+esc(people.map(person => participantName(person)).join('; '))+'. Confira a forma de acesso com cada pessoa.</p>' : '')+
      (conditionalPeople.length ? '<p class="step-responsibility"><strong>Possibilidade a confirmar para:</strong> '+esc(conditionalPeople.map(person => participantName(person)).join('; '))+'. Ainda não é uma forma de acesso confirmada para essas pessoas.</p>' : '')+
      (responsible.length ? '<p class="step-responsibility"><strong>Quem participa da aplicação:</strong> '+esc(responsible.join('; '))+'</p>' : '')+
      ((pending.length || preparation.length || conditions.length || conditional) ? '<div class="step-conditions">'+
        (pending.length ? '<p><strong>Antes de aplicar, confirme:</strong> '+esc(pending.join('; '))+'.</p>' : '')+
        (preparation.length ? '<p><strong>Precisa preparar:</strong> '+esc(preparation.join('; '))+'.</p>' : '')+
        conditions.map(condition => '<p><strong>Condição de uso:</strong> '+esc(condition)+'</p>').join('')+'</div>' : '')+
      ((alternatives.length || monitoring.length || limits.length) ? '<details><summary>Cuidados, alternativas e acompanhamento</summary>'+
        (alternatives.length ? '<h4>Se esta opção não funcionar</h4>'+list(alternatives) : '')+
        (monitoring.length ? '<h4>O que observar</h4>'+list(monitoring) : '')+
        (limits.length ? '<h4>Limites desta opção</h4>'+list(limits) : '')+'</details>' : '')+
      foundations(step.component_ids || [])+'</article>';
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
    const intro = summary.texto || decision.orientacao_principal;
    $('#orientation-main').innerHTML = (steps.some(step => step.titulo === intro) ? '' : para(intro))+
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
  $('#orientation-title').textContent = hasPossibilities ? 'O que você pode fazer' : 'O que falta para orientar este caso';
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
      '<p class="instruction-label">Como fazer</p><ol class="action-instructions">'+steps.map(step => '<li class="step-action">'+esc(step.action)+'</li>').join('')+'</ol>'+
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
      result = await request('generate',{}, {onProgress:generationStage});
    } else {
      const {evidence,...context} = draft; result = await request('compose',{payload:{...context,confirmed:true}},{onProgress:generationStage});
    }
    if (expected !== epoch) return;
    if (result.result_contract === 'AMADO_SITUATED_1') {
      const output=situatedOutput(result);
      $('#orientation-title').textContent=output.title;
      $('#orientation-state').textContent=output.state;
      $('#orientation-main').innerHTML=output.html;
      $('#orientation-detail-body').innerHTML=output.detailHTML;
    } else if (mode === 'legacy') legacyOutput(result); else compositionOutput(result);
    sourceDisclosure(result);
    if(result.result_contract==='AMADO_SITUATED_1') {
      const people=current?.context?.participantes || [], situations=current?.context?.situations || [];
      refinementQuestions=mode==='legacy'?[...(result.facts_to_confirm || []),...(result.resources_to_confirm || [])].map(row=>({
        ...row,id:row.question_id,type:'single',field:'situated_fact',
        context_label:situations.find(s=>s.id===row.situation_id)?.label || '',
        participant_label:participantName(people.find(p=>p.id===row.participant_id)),
        help:row.reason,options:[{id:'true',label:'Sim'},{id:'false',label:'Não'},{id:'unknown',label:'Ainda não sei'}]})):[];
    }
    $('#complete-information').hidden = !unanswered().length;
    $('#complete-information').textContent = 'Refinar esta orientação (opcional)';
    $('#orientation-foundation-body').replaceChildren();
    $('#orientation-case-body').innerHTML = para($('#case-narrative').value)+fieldsHTML(summaryRows())+requirementsHTML();
    for (const id of ['orientation-details','orientation-foundations','orientation-case']) $('#'+id).open = false;
    $('#reading-message').textContent = ''; status(''); screen('orientation-result','orientation-title');
    // Read the visible layout: hidden containers do not retain paragraph breaks in innerText.
    speechText = $('#orientation-main').innerText;
    generationStage({stage:'presentation',state:'completed',message:'Orientação apresentada com as fontes e condições registradas nesta execução.'});
  },'Relacionando seu caso aos conhecimentos da base…',true);
});
$('#complete-information').addEventListener('click',() => {
  roundAnswered = 0; clarificationRound++;
  invalidate(); askOrReview();
});
$('#orientation-foundations').addEventListener('toggle',() => {
  if (!$('#orientation-foundations').open || !result) return;
  if (result.result_contract === 'AMADO_SITUATED_1') $('#orientation-foundation-body').innerHTML=situatedOutput(result).foundationHTML;
  else if (mode === 'legacy') renderExplanation($('#orientation-foundation-body'),result);
  else $('#orientation-foundation-body').innerHTML = compositionFoundations(result);
});
$('#new-case').addEventListener('click',() => run(async expected => {
  voice.clear(); invalidate(); current = draft = null; resetQuestions(); exampleId = exampleNarrative = null;
  organizedNarrative = null;
  $('#case-narrative').value = ''; $('#case-template').value = ''; $('#question-fields').replaceChildren();
  await request('clear'); if (expected === epoch) { $('#new-case').hidden = true; status(''); screen('case-entry'); $('#case-narrative').focus(); }
},''));
$('#read-orientation').addEventListener('click',() => {
  if (reading) { stopReading('Leitura interrompida.'); return; }
  if (!('speechSynthesis' in window)) { $('#reading-message').textContent = 'A leitura em voz não está disponível neste navegador. A orientação continua em texto.'; return; }
  const voice = speechSynthesis.getVoices().find(item => item.localService && /^pt/i.test(item.lang));
  if (!voice) { $('#reading-message').textContent = 'Não foi encontrada uma voz local em português. Você pode ler a orientação em texto.'; return; }
  speechSynthesis.cancel(); const utterance = new SpeechSynthesisUtterance(speechText);
  utterance.voice = voice; utterance.lang = voice.lang;
  utterance.onend = () => stopReading('Leitura concluída.');
  utterance.onerror = () => stopReading('Leitura interrompida. A orientação continua em texto.');
  reading=true; $('#read-orientation').textContent='Parar';
  $('#read-orientation').setAttribute('aria-pressed','true');
  $('#reading-message').textContent = 'Lendo a orientação.'; speechSynthesis.speak(utterance);
});
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
