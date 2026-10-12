// Synthetic fixtures exercise only the projection of existing output fields.
// This is not a test of the decision engine, participant evidence, DOM behavior,
// visual layout or accessibility. No browser, network or output artifact is used.
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import vm from 'node:vm';
import {participantName} from '../web/amado/intake.mjs';

const source = await fs.readFile(new URL('../web/amado/simple-flow.js', import.meta.url), 'utf8');
const start = source.indexOf('function legacyOutput(response) {');
const stop = source.indexOf('function compositionFoundations(response) {', start);
assert(start >= 0 && stop > start, 'The two rendering functions must be present');
const helperStart = source.indexOf('const esc =');
const helperStop = source.indexOf('let catalog', helperStart);
assert(helperStart >= 0 && helperStop > helperStart, 'Shared text escaping helpers must be present');
const script = new vm.Script('"use strict";\n'+source.slice(helperStart, helperStop)+
  '\nlet speechText = "";\n'+source.slice(start, stop)+
  '\nglobalThis.renderers = {legacyOutput, compositionOutput};', {filename:'result-rendering-projection.js'});

const elements = () => new Map();
function render(kind, response, labels = {}) {
  const nodes = elements();
  const $ = selector => {
    if (!nodes.has(selector)) nodes.set(selector, {
      innerHTML:'', textContent:'',
      // The renderers read speech text. This stub deliberately makes no claim
      // about browser innerText, visibility, speech or accessible names.
      get innerText() { return this.innerHTML.replace(/<[^>]*>/g, ' '); },
    });
    return nodes.get(selector);
  };
  const context = vm.createContext({$, participantName, compositionCatalog:{labels}});
  script.runInContext(context);
  const original = structuredClone(response);
  context.renderers[kind](response);
  assert.deepEqual(response, original, 'Rendering must not change a decision or its conditions');
  return {main:$('#orientation-main').innerHTML, detail:$('#orientation-detail-body').innerHTML,
    title:$('#orientation-title').textContent, state:$('#orientation-state').textContent};
}
let checks = 0;
function check(name, run) { run(); checks++; console.log(`PASS ${name}`); }

function legacyFixture() {
  return {synthetic:true, decision:{status:'GERADA_PARCIAL',
    orientacao_principal:'ORIENTATION_DETAIL',
    sintese_pratica:{texto:'ACTION_HEADLINE', etapas:[{titulo:'CHOICE_TITLE',
      itens:['ACTION_STEP'], como_combinar:'MODAL_RELATION', component_ids:['SYNTHETIC-COMPONENT'],
      condicoes:['USE_CONDITION'], alternativas:['ALTERNATIVE'], acompanhamento:['FOLLOW_UP'],
      recursos_estruturados:[
        {id:'R1', label:'PENDING_READER', estado:'NAO_CONFIRMADO', opcional:false},
        {id:'R2', label:'PREPARE_DESCRIPTION', estado:'PROPOSTO_A_PREPARAR', opcional:false},
      ]}]},
    configuracao_modal:[{component_id:'SYNTHETIC-COMPONENT', modo:'Texto', acao:'ACTION_DETAIL',
      funcao:'DECLARED_FUNCTION', responsavel:'RESPONSIBLE_ROLE', availability_status:'CONDICIONAL_A_CONFIRMACAO',
      conditions:['USE_CONDITION'], alternative:'ALTERNATIVE', monitoring:'FOLLOW_UP', limit:'CHOICE_LIMIT'}],
    participant_coverage:[
      {participant_id:'P1', label:'Pessoa relacionada', component_ids:['SYNTHETIC-COMPONENT'], status:'ROTA_DECLARADA_A_CONFERIR_EM_USO'},
      {participant_id:'P2', label:'Pessoa ainda sem apoio', component_ids:[], status:'SEM_ROTA_FUNDAMENTADA'},
    ],
    condicoes:['USE_CONDITION'], alternativas:['ALTERNATIVE'], acompanhamento:['FOLLOW_UP'], limite:'DECISION_LIMIT',
    informacoes_ausentes:['Qual recurso pode ser confirmado?', 'Função requerida ainda sem cobertura: UNCOVERED_FUNCTION'],
  }};
}

check('partial legacy output leads with action and preserves the modal relation', () => {
  const result = render('legacyOutput', legacyFixture());
  assert.match(result.state, /parte/);
  assert(result.main.indexOf('ACTION_STEP') < result.main.indexOf('MODAL_RELATION'));
  assert(result.main.indexOf('class="orientation-step"') < result.main.indexOf('class="orientation-gaps"'));
  assert.match(result.main, /class="step-combination"/);
  assert.equal(result.title,'O que você pode fazer');
  assert.match(result.main, /<h4>Como fazer<\/h4><ol class="action-instructions">/);
  assert.doesNotMatch(result.main, /orientação segura/);
});

check('essential pending and preparation states are visible before collapsed care details', () => {
  const {main} = render('legacyOutput', legacyFixture());
  const care = main.indexOf('<details><summary>Cuidados');
  for (const value of ['PENDING_READER', 'PREPARE_DESCRIPTION', 'USE_CONDITION']) {
    assert(main.indexOf(value) >= 0 && main.indexOf(value) < care, value);
  }
  assert.match(main, /<details><summary>Cuidados, alternativas e acompanhamento<\/summary>/);
  for (const value of ['ALTERNATIVE', 'FOLLOW_UP', 'CHOICE_LIMIT']) assert.match(main, new RegExp(value));
});

check('participant links remain scoped and missing coverage remains explicit', () => {
  const {main} = render('legacyOutput', legacyFixture());
  const card = main.slice(main.indexOf('<article'), main.indexOf('</article>'));
  assert.match(card, /Pessoa relacionada/);
  assert.doesNotMatch(card, /Pessoa ainda sem apoio/);
  assert.match(main, /Ainda sem uma forma de acesso fundamentada/);
  assert.match(main, /Pessoa ainda sem apoio/);
  assert.match(main, /UNCOVERED_FUNCTION/);
});

check('conditional participant links do not become confirmed routes',()=>{
  const fixture=legacyFixture();
  fixture.decision.participant_coverage=[{label:'Pessoa da possibilidade',component_ids:[],
    conditional_component_ids:['SYNTHETIC-COMPONENT'],status:'POSSIBILIDADE_CONDICIONAL_A_CONFIRMAR'}];
  const {main}=render('legacyOutput',fixture);
  assert.match(main,/Possibilidade a confirmar para:<\/strong> Pessoa da possibilidade/);
  assert.match(main,/Ainda não é uma forma de acesso confirmada/);
  assert.doesNotMatch(main,/Participantes relacionados a esta opção/);
});

check('a suspended zero-choice result contains questions and never an actionable card', () => {
  const fixture = legacyFixture();
  fixture.decision.status = 'SUSPENSA_POR_CARACTERIZACAO_OU_COBERTURA_INSUFICIENTE';
  fixture.decision.configuracao_modal = [];
  fixture.decision.sintese_pratica = {texto:'Faltam informações para construir uma orientação segura.', etapas:[]};
  const result = render('legacyOutput', fixture);
  assert.match(result.title, /O que falta/);
  assert.match(result.main, /Qual recurso pode ser confirmado\?/);
  assert.doesNotMatch(result.main, /class="orientation-step"|ACTION_STEP|orientação segura/);
});

check('legacy explanations escape source text instead of interpreting markup', () => {
  const fixture = legacyFixture();
  fixture.decision.sintese_pratica.etapas[0].itens = ['<img src=x onerror=alert(1)>'];
  const {main} = render('legacyOutput', fixture);
  assert.match(main, /&lt;img/);
  assert.doesNotMatch(main, /<img/);
});

check('registered steps take precedence over the old summary and retain their order inside one action', () => {
  const fixture=legacyFixture(),step=fixture.decision.sintese_pratica.etapas[0];
  step.passos=[{texto:'SOURCE_STEP_ONE',component_id:'SYNTHETIC-COMPONENT',campo_origem:'acao'},
    {texto:'SOURCE_STEP_TWO',component_id:'SYNTHETIC-COMPONENT',campo_origem:'acao'}];
  const {main}=render('legacyOutput',fixture);
  assert(main.indexOf('SOURCE_STEP_ONE')<main.indexOf('SOURCE_STEP_TWO'));
  assert.doesNotMatch(main,/ACTION_STEP/);
  assert.equal((main.match(/<ol class="action-instructions">/g)||[]).length,1);
});

check('a conditional configuration remains visibly conditional before its details', () => {
  const fixture=legacyFixture();
  fixture.decision.sintese_pratica.etapas[0].aplicabilidade='CONDICIONAL_A_CONFIRMACAO';
  fixture.decision.sintese_pratica.etapas[0].antes_de_usar='CONFIRM_BEFORE_APPLY';
  const {main}=render('legacyOutput',fixture);
  assert(main.indexOf('CONFIRM_BEFORE_APPLY')<main.indexOf('<details>'));
  assert(main.indexOf('CONFIRM_BEFORE_APPLY')<main.indexOf('Como fazer'),'Conditional status precedes the imperative steps');
  assert.match(main,/CONFIRM_BEFORE_APPLY/);
});

check('local foundations contain only supports tied to that selected configuration', () => {
  const fixture=legacyFixture();
  fixture.explanation={configurations:[{component_id:'SYNTHETIC-COMPONENT',application:{supports:[{
    criterion_statement:'EXACT_CRITERION',justification:'EXACT_REASON',knowledge_ids:['K1'],origins:[{
      id:'O1',fonte_id:'F1',resumo_publico:'EXACT_ORIGIN',localizacao:'SECTION_ONE'}]}]},
    construction:{knowledge:[{id:'K1',enunciado:'EXACT_KNOWLEDGE'}]}},
    {component_id:'OTHER',application:{supports:[{criterion_statement:'UNRELATED_CRITERION'}]}}]};
  const {main}=render('legacyOutput',fixture);
  assert.match(main,/<details class="step-foundation"><summary>Por que esta ação foi sugerida\?/);
  for(const text of ['EXACT_CRITERION','EXACT_REASON','EXACT_ORIGIN','SECTION_ONE','EXACT_KNOWLEDGE'])assert(main.includes(text));
  assert.doesNotMatch(main,/UNRELATED_CRITERION/);
});

const labels = {Keyboard:'Teclado disponível', TextDraft:'Texto a revisar', Review:'Conferir o conteúdo'};
function choice(id, action) {
  return {id, steps:[{id:'S-'+id, label:'Etapa '+id, action, limitation:'LIMIT_'+id,
    function:{id:'Review',label:'Conferir o conteúdo'}, condition_checks:[]}],
    relations:[{explanation:'RELATION_'+id, condition_checks:[]}], limits:['CHOICE_LIMIT_'+id]};
}
function compositionFixture() {
  const pending = choice('pending','PENDING_ACTION');
  pending.steps[0].condition_checks.push({state:'PENDING', observed:{concept:'https://example.org/#Keyboard'}, explanation:'PENDING_CHECK'});
  const partial = choice('partial','PARTIAL_ACTION');
  partial.entry = {representation:'https://example.org/#TextDraft', availability_verified:false};
  partial.missing_functions = [{id:'Review',label:'Conferir o conteúdo'}];
  return {synthetic:true, proposal_status:'COMPLETE', choices:[choice('complete','COMPLETE_ACTION')],
    pending_candidates:[pending], partial_segments:[partial],
    facts_to_confirm:[], resources_to_confirm:[{id:'Keyboard',label:'Teclado disponível',candidate_ids:['pending']}],
    unavailable_conditions:[], limits:['COMPOSITION_LIMIT']};
}

check('complete, partial and pending compositions are all retained in separate groups', () => {
  const {main} = render('compositionOutput', compositionFixture(), labels);
  assert.equal((main.match(/class="orientation-group"/g) || []).length, 3);
  assert.equal((main.match(/class="orientation-step"/g) || []).length, 3);
  const groups = main.split('<section class="orientation-group">').slice(1);
  assert.match(groups[0], /COMPLETE_ACTION/);
  assert.doesNotMatch(groups[0], /PENDING_ACTION|PARTIAL_ACTION/);
  assert.match(groups[1], /PARTIAL_ACTION/);
  assert.match(groups[2], /PENDING_ACTION/);
  assert.match(groups[2], /A confirmar:/);
  assert.match(main, /<h3>Opções para realizar a atividade<\/h3>/);
  assert.match(main, /<h4>Etapa complete<\/h4>/);
});

check('pending requirements remain named conditions rather than silently confirmed', () => {
  const {main} = render('compositionOutput', compositionFixture(), labels);
  const pendingGroup = main.split('<section class="orientation-group">').at(-1);
  assert.match(pendingGroup, /Antes de usar, confirme/);
  assert.match(pendingGroup, /Teclado disponível/);
  assert.doesNotMatch(pendingGroup, /https:\/\/example\.org|#Keyboard/);
  assert.match(pendingGroup, /ainda não estão prontas para uso/);
});

check('partial segments retain required entry and missing task coverage', () => {
  const {main} = render('compositionOutput', compositionFixture(), labels);
  assert.match(main, /Esta parte depende de:<\/strong> Texto a revisar/);
  assert.match(main, /A disponibilidade dessa entrada ainda não foi verificada/);
  assert.match(main, /Esta opção ainda não cobre:<\/strong> Conferir o conteúdo/);
  assert.match(main, /RELATION_partial/);
  assert.match(main, /LIMIT_partial/);
});

check('participant output nests headings and preserves each participant conditions', () => {
  const local = compositionFixture();
  const fixture = {synthetic:true, proposal_status:'PARTIAL', participant_results:[{label:'Participante sintético',result:local}]};
  const {main,detail} = render('compositionOutput', fixture, labels);
  assert.match(main, /<h3>Participante sintético<\/h3>/);
  assert.match(main, /<h4>Opções para realizar a atividade<\/h4>/);
  assert.match(main, /<h5>Etapa complete<\/h5>/);
  assert.match(detail, /Teclado disponível/);
  assert.match(detail, /COMPOSITION_LIMIT/);
});

check('empty composition does not create a recommendation', () => {
  const fixture = {synthetic:true, proposal_status:'NONE', choices:[], pending_candidates:[], partial_segments:[],
    facts_to_confirm:[], resources_to_confirm:[], limits:['NO_SUPPORTED_ROUTE']};
  const result = render('compositionOutput', fixture, labels);
  assert.match(result.title, /O que falta/);
  assert.doesNotMatch(result.main, /class="orientation-step"/);
  assert.match(result.detail, /NO_SUPPORTED_ROUTE/);
});

console.log(`PASS ${checks} synthetic result-projection checks; engine, browser and accessibility not evaluated`);
