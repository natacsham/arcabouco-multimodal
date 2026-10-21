import assert from 'node:assert/strict';
import {situatedOutput} from '../web/amado/situated-output.mjs';
const source={id:'F1',title:'Fonte primária',url:'https://www.w3.org/example'};
const contribution={id:'C1',statement:'Paráfrase localizada',source,excerpt:{id:'T1',locator:'Seção 1'},status:'CONFERIDA_NO_REGISTRO'};
const step={id:'OP-A',label:'Revisar o conteúdo',action:'Confira o texto antes de continuar.',modes:['texto'],functions:['Revisão'],
  responsible_participant:{id:'P1',label:'Quem prepara o material'},participant_label:'Pessoa que acompanha o conteúdo',
  monitoring:'Verifique se a informação pode ser corrigida.',groundings:[{id:'G1',knowledge:{label:'Conhecimento específico'},contributions:[contribution]}]};
const response={proposal_status:'PARTIAL',partial_segments:[{id:'A',steps:[step],relations:[]}],gaps:[{message:'Falta uma operação de retorno.'}]};
const original=structuredClone(response),output=situatedOutput(response);
assert.deepEqual(response,original,'Rendering must not alter execution data');
assert.equal(output.title,'O que fazer');
assert.equal(output.detailHTML,'','The former complete-orientation duplicate must be removed');
assert.match(output.html,/Confira o texto/);
assert.match(output.html,/Como conferir/);
assert.match(output.html,/Quem realiza:<\/strong> Quem prepara o material/);
assert.match(output.html,/Para quem:<\/strong> Pessoa que acompanha o conteúdo/);
assert.match(output.html,/class="orientation-step situated-choice"/);
assert.equal((output.html.match(/Revisar o conteúdo/g)||[]).length,1,'A single operation must not repeat the choice title as an adjacent action title');
assert.match(output.html,/<h4>Passos<\/h4>/);
assert.match(output.html,/data-origin-path="partial_segments\[0\].steps\[0\].action" data-phase="action"/);
assert.match(output.html,/Falta uma operação/);
assert.doesNotMatch(output.html,/<details|<summary|Fonte primária|Paráfrase localizada|Conhecimento específico|fala|jogo|imagem/);
assert.match(output.foundationHTML,/https:\/\/www.w3.org\/example/);
assert.match(output.foundationHTML,/Informação considerada no relato/);
assert.match(output.foundationHTML,/Necessidade identificada/);
assert.equal((output.foundationHTML.match(/<details/g)||[]).length,1,'Only one technical disclosure within the external foundation disclosure');
const pending=situatedOutput({proposal_status:'CONDITIONAL',pending_candidates:[{steps:[step]}]});
assert.match(pending.html,/depende das condições/);
const hostile=situatedOutput({choices:[{steps:[{...step,action:'<script>bad()</script>',responsible_participant:{id:'a',label:'<img src=x onerror=x>'},
  groundings:[{contributions:[{statement:'<svg onload=x>',source:{title:'<b>Fonte</b>',url:'javascript:alert(1)'}}]}]}]}]});
assert.doesNotMatch(hostile.html,/<script>|<img src=/);
assert.doesNotMatch(hostile.foundationHTML,/<svg|href="javascript:/);
assert.match(hostile.html,/&lt;script&gt;/);
const independent=situatedOutput({choices:[{composition_type:'INDEPENDENT_SUPPORTS',steps:[step]}]});
assert.match(independent.html,/Não há uma sequência obrigatória/);
assert.doesNotMatch(independent.html,/→/);
const actualContract=situatedOutput({choices:[{steps:[{...step,check_ids:['CHECK-1'],functions:[{id:'F1',label:'Permitir a revisão'}],
  function_derivation:[{function_id:'F1',origin:'DOCUMENTED_FUNCTIONAL_WITNESS',
    witnesses:[{needs:[{label:'Retomar a instrução'}],assertions:[{source_text:'Não consigo retomar a instrução.'}]}]}]}]}],
  execution_evidence:[{id:'CHECK-1',phase:'precondition',state:'PENDING',explanation:'O recurso ainda precisa ser confirmado.'}]});
assert.doesNotMatch(actualContract.html,/Não consigo retomar a instrução/);
assert.match(actualContract.foundationHTML,/Não consigo retomar a instrução/);
assert.match(actualContract.foundationHTML,/Retomar a instrução/);
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
const analytical={id:'ANA-1',application_kind:'GROUNDED_ANALYTICAL_APPLICATION',analytical_application_id:'ANA-1',
  authorized_application:'Organizar a instrução mantendo sua informação essencial.',
  construction:{operation:'Relacionar acesso não visual e representação equivalente.',added_understanding:'O conteúdo pode ser recuperado em outra forma de acesso.',
    contributions:[contribution]},sources:[{...source,excerpt_id:'T1',locator:'Seção 1',review_status:'CONFERIDA_NO_REGISTRO'}]};
const phaseResponse={proposal_status:'CONDITIONAL',pending_candidates:[{composition_type:'INDEPENDENT_SUPPORTS',steps:[{...step,
  selected_representation_ids:['Text'],representation_selection_status:'SELECTED_VARIANT',
  phase_conditions:[{id:'prepare-text',label:'Preparar a descrição textual',phase:'production',state:'PENDING'},
    {id:'generic',label:'Preparar o recurso proposto e conservar a informação identificada como necessária.',phase:'production',state:'NOT_EXECUTED'},
    {id:'can-edit',label:'Ao menos um recurso: Editor de apresentação',phase:'precondition',state:'PENDING'},
    {id:'already-known',label:'A pessoa acompanha texto',phase:'precondition',state:'PASS'},
    {id:'verify',label:'Conferir a sequência de leitura com a pessoa',phase:'verification',state:'NOT_EXECUTED'}],
  limits:['A ação não confirma equivalência de todo o conteúdo.'],limitation:'Instrução histórica não autorizada.',
  groundings:[...step.groundings,analytical]}],relations:[]}]};
const phases=situatedOutput(phaseResponse);
assert.match(phases.html,/Preparar a descrição textual/);
assert.match(phases.html,/Informe se há como utilizar Editor de apresentação/);
assert.match(phases.html,/data-edit-case/);
const phaseSnapshot=structuredClone(phaseResponse);
const readOnlyPhases=situatedOutput(phaseResponse,{reviewEnabled:false});
assert.doesNotMatch(readOnlyPhases.html,/data-edit-case/,'Consumers without review handlers must not expose an inert button');
assert.equal(readOnlyPhases.html,phases.html.replaceAll('<button type="button" class="secondary" data-edit-case>Revisar esta informação</button>',''),
  'Disabling review removes only the control, not conditions or actions');
assert.deepEqual(readOnlyPhases.actionProjection,phases.actionProjection);
assert.equal(readOnlyPhases.foundationHTML,phases.foundationHTML);
assert.deepEqual(phaseResponse,phaseSnapshot,'The display option must not mutate decisions');
assert.match(phases.html,/Conferir a sequência de leitura com a pessoa/);
assert.match(phases.html,/não confirma equivalência/);
assert.doesNotMatch(phases.html,/não são apresentados como prontos|ainda precisa ser conferida|A pessoa acompanha texto|Instrução histórica|Preparar o recurso proposto/);
assert.match(phases.foundationHTML,/Instrução histórica não autorizada/);
assert.match(phases.foundationHTML,/Como as contribuições foram articuladas/);
assert.match(phases.foundationHTML,/Organizar a instrução mantendo/);
assert.equal((phases.foundationHTML.match(/data-contribution-id="C1"/g)||[]).length,1,'The same documentary/analytical premise is presented once');
assert.equal((phases.foundationHTML.match(/Paráfrase localizada/g)||[]).length,1,'The exact contribution text must not repeat as every link label');
assert.equal((phases.foundationHTML.match(/class="foundation-source"/g)||[]).length,1,'A source and excerpt are not repeated for each ground');
assert.match(phases.foundationHTML,/Contribuições relacionadas nesta compreensão/,'Every synthesis retains links to its own premises');
assert.equal(phases.actionProjection[0].absorbed_origins.length,1,'Generic reminder retains provenance without duplicating the specific action');
assert.equal(phases.actionProjection[0].rows.length,3);
assert.deepEqual(phases.actionProjection[0].rows.map(row=>row.phase),['action','production','verification']);
for(const row of phases.actionProjection[0].rows)assert(row.origin_path&&row.source_text);
const future=situatedOutput({choices:[{steps:[{...step,phase_conditions:[{label:'O conteúdo pode ser corrigido?',phase:'verification',state:'NOT_EXECUTED'}]}]}]});
assert.match(future.html,/Confira: O conteúdo pode ser corrigido\./);
assert.doesNotMatch(future.html,/O conteúdo pode ser corrigido.*Conferida/,'A future verification is never a passed check');
const relation=situatedOutput({choices:[{steps:[step],relations:[{kind:'DEPENDENT_SEQUENCE',explanation:'O rascunho produzido é a entrada da revisão.',
  preservation_obligation:'O mesmo rascunho editável',groundings:[analytical],
  phase_conditions:[{id:'VerifyDraft',label:'Conferir se o rascunho mantém a intenção',phase:'verification',state:'NOT_EXECUTED'}]}]}]});
assert.match(relation.html,/O rascunho produzido é a entrada da revisão/);
assert.match(relation.html,/Como conferir a combinação/);
assert.match(relation.html,/data-origin-path="choices\[0\].relations\[0\].preservation_obligation"/);
assert.doesNotMatch(relation.html,/Como as contribuições foram articuladas|Por que esta relação/);
assert.match(relation.foundationHTML,/Como as contribuições foram articuladas/);
const ranked=situatedOutput({partial_segments:[{label:'Apoio independente limitado',steps:[step],covered_functions:['one']}],
  pending_candidates:[{label:'Produzir e revisar',steps:[{...step,id:'OP-B'}],covered_functions:['one','two']}]});
assert(ranked.html.indexOf('Produzir e revisar')<ranked.html.indexOf('Apoio independente limitado'));
assert.match(ranked.html,/depende das condições/);
const video=situatedOutput({pending_candidates:[{participant_id:'A',participant_label:'Participante A',situation_label:'Consulta individual',steps:[{...step,id:'audio',modes:['áudio'],
  responsible_participant:{id:'PART-PREPARER',label:'PART-PREPARER'},operation_scope:'PREPARATION_FOR_RECIPIENT'}]},
  {participant_id:'B',participant_label:'Participante B',situation_label:'Consulta individual',steps:[{...step,id:'text',modes:['texto']}]}]});
assert(video.html.indexOf('Participante A')<video.html.indexOf('Participante B'),'Keep stable ordering between independent alternatives');
assert.match(video.html,/Responsável pela preparação informado no relato/);
assert.doesNotMatch(video.html,/PART-PREPARER|professora/);
assert.equal((video.html.match(/<article/g)||[]).length,2,'Different recipients do not become one numbered sequence');
const hrefs=[...phases.foundationHTML.matchAll(/href="#([^\"]+)"/g)].map(m=>m[1]);
for(const href of hrefs)assert(phases.foundationHTML.includes('id="'+href+'"'),'Every source/premise reference resolves: '+href);
const frozen=structuredClone(phaseResponse);Object.freeze(frozen);
assert.doesNotThrow(()=>situatedOutput(frozen));
assert.deepEqual(phaseResponse,structuredClone(phaseResponse));
console.log('PASS situated presentation: two readings, open practical steps, exact origins, roles, conditionality, deduplicated premises, preserved alternatives and immutable decisions.');
