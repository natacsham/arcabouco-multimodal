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
const bounded=situatedOutput({proposal_status:'COMPLETE',covers_whole_reported_task:false,
  coverage_explanation:'O apoio cobre as funções confirmadas, não todas as ações do relato.',choices:[{steps:[step]}],
  gaps:[{code:'UNMAPPED_TASK',label:'Enviar formulário',explanation:'Enviar o formulário ainda não tem operação representada.',participant_label:'Quem preenche'}]});
assert.equal(bounded.state,'Apoio às funções identificadas');
assert.match(bounded.html,/não todas as ações do relato/);
assert.match(bounded.html,/Quem preenche — Enviar formulário: Enviar o formulário ainda não tem operação representada/);
assert.doesNotMatch(bounded.html,/UNMAPPED_TASK/);
const phases=situatedOutput({proposal_status:'CONDITIONAL',pending_candidates:[{composition_type:'INDEPENDENT_SUPPORTS',steps:[{...step,
  selected_representation_ids:['Text'],representation_selection_status:'SELECTED_VARIANT',
  phase_conditions:[{id:'prepare-text',label:'Preparar a descrição textual',phase:'production',state:'PENDING'},
    {id:'can-edit',label:'Há como editar este material',phase:'precondition',state:'PENDING'},
    {id:'verify',label:'Conferir a sequência de leitura com a pessoa',phase:'verification',state:'NOT_EXECUTED'}],
  groundings:[{application_kind:'GROUNDED_ANALYTICAL_APPLICATION',analytical_application_id:'ANA-1',
    authorized_application:'Organizar a instrução mantendo sua informação essencial.',
    construction:{operation:'Relacionar acesso não visual e representação equivalente.',added_understanding:'O conteúdo pode ser recuperado em outra forma de acesso.',
      contributions:[{statement:'Contribuição efetivamente utilizada',source:{title:'Fonte conhecida',url:'https://www.w3.org/example'},locator:'Seção conferida'}]}}]}],relations:[]}]});
assert.match(phases.html,/O que esta ação propõe preparar/);
assert.match(phases.html,/não são apresentados como prontos/);
assert.match(phases.html,/Depois de preparar, confira antes de utilizar/);
assert.match(phases.html,/Como as contribuições foram articuladas/);
assert.match(phases.html,/Organizar a instrução mantendo/);
assert.match(phases.html,/Não há uma sequência obrigatória/);
assert.doesNotMatch(phases.html,/→/);
assert.doesNotMatch(phases.foundationHTML,/→/);
assert.match(phases.foundationHTML,/Contribuição efetivamente utilizada/);
const relation=situatedOutput({choices:[{steps:[step],relations:[{kind:'DEPENDENT_SEQUENCE',explanation:'O rascunho produzido é a entrada da revisão.',
  groundings:[{application_kind:'GROUNDED_ANALYTICAL_APPLICATION',construction:{operation:'Relacionar produção e revisão.',added_understanding:'A revisão conserva o mesmo rascunho.'}}]}]}]});
assert.match(relation.html,/Por que esta relação pode ser utilizada/);
assert.match(relation.html,/A revisão conserva o mesmo rascunho/);
const relationPhases=situatedOutput({choices:[{steps:[step],relations:[{kind:'DEPENDENT_SEQUENCE',explanation:'Revisar o mesmo rascunho.',check_ids:['REL-CHECK'],
  phase_conditions:[{id:'VerifyDraft',label:'Conferir se o rascunho mantém a intenção',phase:'verification',state:'NOT_EXECUTED'}],grounding:{justification:'Síntese registrada.'}}]}],
  execution_evidence:[{id:'REL-CHECK',state:'NOT_EXECUTED',explanation:'A revisão do rascunho ainda não foi observada.'}]});
assert.match(relationPhases.html,/Depois de preparar, confira antes de utilizar/);
assert.match(relationPhases.html,/A revisão do rascunho ainda não foi observada.*Não verificada/);
assert.equal((relationPhases.foundationHTML.match(/Síntese registrada/g)||[]).length,1,'Technical presentation must not duplicate the same relation ground');
const ranked=situatedOutput({partial_segments:[{label:'Apoio independente limitado',steps:[step],covered_functions:['one']}],
  pending_candidates:[{label:'Produzir e revisar',steps:[{...step,id:'OP-B'}],covered_functions:['one','two']}]});
assert(ranked.html.indexOf('Produzir e revisar')<ranked.html.indexOf('Apoio independente limitado'));
assert.match(ranked.html,/Confirme as condições/,'Ordering must not promote a conditional proposal to ready');
const personSummary=situatedOutput({choices:[{participant_label:'Participante A',situation_label:'Consulta individual',steps:[step]}]});
assert.match(personSummary.html,/<summary>Revisar o conteúdo <span class="choice-context">Participante A · Consulta individual<\/span><\/summary>/,
  'The person and situation must be identifiable before expanding a repeated action title');
console.log('PASS situated actions: actual modes, monitoring, grounds, gaps, conditionality, escaping and no invented relations.');
