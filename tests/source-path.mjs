// Rendering contract tests. Fixtures are synthetic, never participant evidence.
// Pure HTML rendering: no browser/network, no generated report or persisted case.
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import {renderSourcePath} from '../web/source-path.js';
import {situatedOutput} from '../web/amado/situated-output.mjs';

const escape = value => String(value ?? '').replace(/[&<>"']/g, char => ({
  '&':'&amp;', '<':'&lt;', '>':'&gt;', '"':'&quot;', "'":'&#39;',
}[char]));
let checks = 0;
function check(name, run) { run(); checks++; console.log(`PASS ${name}`); }
function fixture() {
  const contribution = (id, art, statement, state='CONFERIDA_NO_REGISTRO') => ({
    id, articulation_id:art, knowledge_id:'K1', excerpt_id:`T-${id}`, statement,
    verification_status:state, justification:'Parcela documental; não prova a configuração inteira.',
    source:{id:'F1', title:'Fonte sintética', url:'https://example.org/source'},
    excerpt:{location:'Seção sintética 2', document_url:'https://example.org/source#section-2'},
  });
  return {prepared_public_example:true, explanation:{configurations:[{
    id:'CFG-SYNTHETIC', title:'Escolha sintética', function:'Permitir revisão do conteúdo',
    construction:{
      articulations:[
        {id:'A-USED', title:'Articulação empregada', mobilized_in_execution:true, habilitada_para_decisao:true,
         operation_explanation:'OPERATION_USED', added_understanding:'Compreensão resultante delimitada.', limite:'LIMIT_USED'},
        {id:'A-HISTORICAL', title:'Articulação histórica', mobilized_in_execution:false, habilitada_para_decisao:true,
         operation_explanation:'OPERATION_HISTORICAL'},
        {id:'A-BLOCKED', title:'Articulação bloqueada', mobilized_in_execution:false, habilitada_para_decisao:false,
         operation_explanation:'OPERATION_BLOCKED'},
      ],
      contributions:[contribution('C1','A-USED','CONTRIBUTION_USED'),
        contribution('C2','A-HISTORICAL','CONTRIBUTION_HISTORICAL'),
        contribution('C3','A-BLOCKED','CONTRIBUTION_BLOCKED'),
        contribution('C4','A-USED','CONTRIBUTION_PENDING','PENDENTE')],
      knowledge:[{id:'K1', enunciado:'Conhecimento sintético, não evidência empírica.',
        foundation_review_status:'PARCIAL', pending_foundation_items:['PENDING_DOCUMENT_CONTEXT'], limite:'KNOWLEDGE_LIMIT'}],
    },
    application:{context_conditions:[{id:'N1',label:'Revisar antes da publicação'}], supports:[{
      criterion_id:'CA-SYNTHETIC', criterion_statement:'CRITERION_COMPLETE_STATEMENT', knowledge_ids:['K1'],
      justification:'SITUATED_SUPPORT_JUSTIFICATION', origins:[{id:'O1', document_paraphrase:'OWN_ORIGIN_PARAPHRASE',
        localizacao_publica:'Seção 2', status_localizacao:'CONFERIDO_NA_SECAO_ORIGINAL',
        document_url:'https://example.org/criterion#section-2'}],
    }]},
  }]}};
}

check('empty result does not fabricate a path', () => {
  assert.match(renderSourcePath({}), /Nenhum percurso será inventado/);
});
check('only mobilized and enabled articulations supply this path', () => {
  const html = renderSourcePath(fixture());
  assert(html.includes('OPERATION_USED'));
  assert(!html.includes('OPERATION_HISTORICAL'));
  assert(!html.includes('OPERATION_BLOCKED'));
  assert.match(html, /1 articulações documentadas/);
  assert.match(html, /1 relações históricas não mobilizadas e 1 relações bloqueadas/);
});
check('blocked articulation cannot re-enter by setting mobilized alone', () => {
  const data = fixture(); data.explanation.configurations[0].construction.articulations[2].mobilized_in_execution = true;
  assert(!renderSourcePath(data).includes('OPERATION_BLOCKED'));
});
check('contribution state and articulation scope are respected', () => {
  const html = renderSourcePath(fixture());
  assert(html.includes('CONTRIBUTION_USED'));
  for (const excluded of ['CONTRIBUTION_HISTORICAL','CONTRIBUTION_BLOCKED','CONTRIBUTION_PENDING']) assert(!html.includes(excluded));
  assert.match(html, /1 contribuições registradas/);
});
check('documentary pending items and limits remain visible', () => {
  const html = renderSourcePath(fixture());
  for (const text of ['PARCIAL','PENDING_DOCUMENT_CONTEXT','KNOWLEDGE_LIMIT','LIMIT_USED']) assert(html.includes(text));
});
check('criterion supplies statement, exact support, origin and locator', () => {
  const html = renderSourcePath(fixture());
  for (const text of ['CRITERION_COMPLETE_STATEMENT','SITUATED_SUPPORT_JUSTIFICATION','OWN_ORIGIN_PARAPHRASE',
                      'CONFERIDO_NA_SECAO_ORIGINAL','https://example.org/criterion#section-2']) assert(html.includes(text));
});
check('document URL is preferred over source URL', () => {
  const html = renderSourcePath(fixture());
  assert(html.includes('href="https://example.org/source#section-2"'));
  assert(!html.includes('href="https://example.org/source"'));
});
check('dangerous and relative URL schemes never create anchors', () => {
  for (const bad of ['javascript:alert(1)','data:text/html,<script>alert(1)</script>','file:///private.pdf','//example.org/relative']) {
    const data = fixture(), cfg = data.explanation.configurations[0];
    cfg.construction.contributions[0].excerpt.document_url = bad;
    cfg.application.supports[0].origins[0].document_url = bad;
    const html = renderSourcePath(data);
    assert(!html.includes('Consultar o original'), bad);
    assert(!html.includes('Consultar a seção original'), bad);
    assert(!html.includes('<script>'), bad);
  }
});
check('all documentary prose and identifiers are HTML escaped', () => {
  const data = fixture(), cfg = data.explanation.configurations[0];
  const attack = '<img src=x onerror="alert(1)"> & "';
  cfg.title = attack;
  cfg.construction.contributions[0].statement = attack;
  cfg.construction.contributions[0].source.title = attack;
  cfg.construction.knowledge[0].pending_foundation_items = [attack];
  cfg.application.supports[0].criterion_statement = attack;
  cfg.application.supports[0].origins[0].document_paraphrase = attack;
  const html = renderSourcePath(data);
  assert(!html.includes('<img'));
  assert(html.includes(escape(attack)));
});
check('rendering does not mutate the decision or evidence', () => {
  const data = fixture(), original = structuredClone(data);
  renderSourcePath(data); assert.deepEqual(data, original);
});

const pilot = JSON.parse(await fs.readFile(new URL('../web/assets/explanation-pilot.json', import.meta.url), 'utf8'));
check('prepared pilot uses the actual engine configuration and exact support', () => {
  const proposals=[...pilot.choices,...pilot.pending_candidates,...pilot.partial_segments];
  const cfg = proposals[0].steps.find(step=>step.component_id==='PAD-ORGANIZAR-CONTEUDO-PERSISTENTE');
  const output = situatedOutput(pilot), html=output.html, foundation=output.foundationHTML;
  assert.equal(pilot.prepared_public_example, true);
  assert.equal(pilot.result_contract,'AMADO_SITUATED_1');
  assert.equal(cfg.component_id, 'PAD-ORGANIZAR-CONTEUDO-PERSISTENTE');
  assert(html.includes(escape(cfg.label)));
  for (const support of cfg.groundings) {
    if(support.criterion)assert(foundation.includes(escape(support.criterion.label)));
    assert(foundation.includes(escape(support.justification)));
  }
  assert(!(html+foundation).includes('ART-TESTE-NAO-CONFIRMADA'));
});
check('prepared pilot preserves current knowledge review limitations', () => {
  const proposals=[...pilot.choices,...pilot.pending_candidates,...pilot.partial_segments], output=situatedOutput(pilot), html=output.html, foundation=output.foundationHTML;
  const reviewLabels={CONFERIDA_NO_REGISTRO:'Conferida no registro preservado',CONFERIDA_NO_DOCUMENTO:'Conferida no documento',PRIMARY_CHECKED:'Conferida na fonte primária',PENDING:'Conferência pendente'};
  for (const step of proposals[0].steps) {
    for (const support of step.groundings) {
      for (const item of support.claim?.limits || []) assert(foundation.includes(escape(item)));
      for (const source of support.sources || []) if(source.review_status) assert(foundation.includes(escape(reviewLabels[source.review_status]||source.review_status)));
    }
  }
  if(pilot.pending_candidates.length)assert(html.includes('Antes de aplicar'));
});
console.log(JSON.stringify({passed:true, checks, scope:'PURE_RENDERING_SYNTHETIC_AND_PREPARED_PILOT', network:false,
  limitations:['Não verifica reflow, contraste, teclado ou leitores de tela.','Não é validação humana.']}));
