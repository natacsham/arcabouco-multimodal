import assert from 'node:assert/strict';
import {situatedOutput} from '../web/amado/situated-output.mjs';
const step={id:'OP-A',label:'Revisar o conteúdo',action:'Confira o texto antes de continuar.',modes:['texto'],functions:['Revisão'],
  monitoring:'Verifique se a informação pode ser corrigida.',groundings:[{knowledge:{label:'Conhecimento específico'},
    contributions:[{statement:'Paráfrase localizada',source:{title:'Fonte primária',url:'https://www.w3.org/example'},locator:'Seção 1'}]}]};
const output=situatedOutput({proposal_status:'PARTIAL',partial_segments:[{id:'A',steps:[step],relations:[]}],gaps:[{message:'Falta uma operação de retorno.'}]});
assert.match(output.html,/Confira o texto/);
assert.match(output.html,/Como observar se ajudou/);
assert.match(output.html,/Por que esta ação/);
assert.match(output.html,/Fonte primária/);
assert.match(output.html,/Falta uma operação/);
assert.doesNotMatch(output.html,/fala|jogo|imagem/);
assert.doesNotMatch(output.html,/Como as etapas se conectam/);
assert.match(output.foundationHTML,/https:\/\/www.w3.org\/example/);
const pending=situatedOutput({proposal_status:'CONDITIONAL',pending_candidates:[{steps:[step]}]});
assert.match(pending.html,/Confirme as condições/);
const hostile=situatedOutput({choices:[{steps:[{...step,action:'<script>bad()</script>'}]}]});
assert.doesNotMatch(hostile.html,/<script>/);
const independent=situatedOutput({choices:[{steps:[step]}]});
assert.match(independent.html,/não precisam ser executadas em sequência/);
const actualContract=situatedOutput({choices:[{steps:[{...step,check_ids:['CHECK-1'],
  functions:[{id:'F1',label:'Permitir a revisão'}],
  function_derivation:[{function_id:'F1',origin:'DOCUMENTED_FUNCTIONAL_WITNESS',
    witnesses:[{needs:[{label:'Retomar a instrução'}],assertions:[{source_text:'Não consigo retomar a instrução.'}]}]}]}]}],
  execution_evidence:[{id:'CHECK-1',state:'PENDING',explanation:'O recurso ainda precisa ser confirmado.'}]});
assert.match(actualContract.html,/O recurso ainda precisa ser confirmado.*A confirmar/);
assert.match(actualContract.html,/Retomar a instrução/);
assert.match(actualContract.html,/Não consigo retomar a instrução/);
assert.match(actualContract.foundationHTML,/O recurso ainda precisa ser confirmado/);
const scopedGaps=situatedOutput({gaps:[{code:'NO_DOCUMENTED_FUNCTION_REQUIREMENT',participant_label:'Pessoa A',situation_label:'Consulta individual'},
  {code:'NO_DOCUMENTED_FUNCTION_REQUIREMENT',participant_label:'Pessoa B',situation_label:'Consulta individual'}]});
assert.match(scopedGaps.html,/Pessoa A — Consulta individual/);
assert.match(scopedGaps.html,/Pessoa B — Consulta individual/);
console.log('PASS situated actions: actual modes, monitoring, grounds, gaps, conditionality, escaping and no invented relations.');
