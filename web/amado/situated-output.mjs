// Presentation only: every action and relationship comes from this execution.
const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const items = value => Array.isArray(value) ? value : value ? [value] : [];
const diagnosticLabels={NO_DOCUMENTED_FUNCTION_REQUIREMENT:'Ainda não há uma necessidade funcional fundamentada e atribuída a esta pessoa nesta situação.',
  INPUT_REQUIRES_CORRECTION:'Há informações ambíguas ou incompatíveis no entendimento do caso. Revise os pontos indicados.',
  NO_COMPLETE_SITUATED_COMPOSITION:'Os apoios apresentados não cobrem toda a atividade para todos os participantes. Confira o alcance de cada opção.',
  NO_AUTHORIZED_RELATION:'Há ações possíveis, mas a base ainda não fundamenta sua combinação para esta situação.',
  UNMAPPED_TASK:'Esta ação foi informada, mas ainda não possui uma função operacional ligada à orientação.',
  UNMAPPED_NEED:'Esta necessidade foi informada, mas ainda não possui uma função operacional ligada à orientação.',
  NO_OPERATION_FOR_REQUIRED_FUNCTION:'A necessidade foi identificada, mas não há uma operação utilizável para atendê-la nas condições confirmadas.',
  CYCLIC_OPERATION_DEPENDENCY:'As ações dependem umas das outras sem um início executável.',
  CONDITION_OR_FOUNDATION_FAILED:'Uma condição necessária ou o fundamento desta operação não foi atendido.',
  SEARCH_LIMIT_REACHED:'A busca atingiu seu limite. Isso não significa que nenhuma solução seja possível.'};
const text = value => typeof value === 'object' && value ? value.label || value.statement || value.text || value.message || value.explanation || diagnosticLabels[value.code] || diagnosticLabels[value.reason] || value.reason || value.id || '' : value || '';
const para = value => value ? '<p>'+esc(text(value))+'</p>' : '';
const list = value => items(value).length ? '<ul>'+items(value).map(item=>'<li>'+esc(text(item))+'</li>').join('')+'</ul>' : '';
const states = {PASS:'Conferida',SATISFIED:'Conferida',FAIL:'Não atendida',PENDING:'A confirmar',NOT_EXECUTED:'Não verificada'};
const unique = values => [...new Map(items(values).filter(Boolean).map(value=>[JSON.stringify(value),value])).values()];
function source(row) {
  const s = row.source || row, url = s.url || s.document_url || row.document_url;
  const name = s.title || s.titulo || s.label || s.source_id || s.id;
  const locator=row.locator || row.location || row.excerpt?.locator || s.locator || s.location;
  return para(name)+(locator ? para(locator) : '')+
    (/^https?:\/\//.test(url || '') ? '<a href="'+esc(url)+'" rel="noreferrer">Consultar a fonte</a>' : '')+
    para(row.review_status || row.verification_status || row.status);
}
function groundingHTML(grounding) {
  const art = grounding.construction || grounding.articulation || {}, knowledge = grounding.knowledge || {};
  const contributions = grounding.contributions || art.contributions || [];
  const claims = items(grounding.claims || grounding.claim);
  const analytical = grounding.application_kind === 'GROUNDED_ANALYTICAL_APPLICATION';
  const statement=grounding.justification || grounding.justificativa;
  const constructionLimits=unique([...items(grounding.limits),...items(art.limits),...claims.flatMap(claim=>items(claim.limits))]);
  return '<section class="step-grounding">'+
    (statement && statement!==art.operation?para(statement):'')+
    (text(knowledge) && (!analytical || text(knowledge)!==text(art.added_understanding)) ? '<h5>Conhecimento empregado</h5>'+para(knowledge) : '')+
    claims.filter(claim=>text(claim)!==text(knowledge) && text(claim)!==text(art.added_understanding)).map(claim=>para(claim.statement || claim.text)).join('')+
    (contributions.length ? '<h5>O que as fontes acrescentaram</h5>'+contributions.map(c=>{
      const located=c.source?c:items(grounding.sources).find(s=>s.id===c.source_id && s.excerpt_id===c.excerpt_id);
      return para(c.statement || c.text)+(located?source(located):'');
    }).join('') : '')+
    (art.operation || art.added_understanding ? '<h5>'+(analytical?'Como as contribuições foram articuladas':'Como o fundamento foi empregado')+'</h5>'+para(art.operation)+
      (art.added_understanding?'<p><strong>Compreensão resultante:</strong> '+esc(text(art.added_understanding))+'</p>':'') : '')+
    (analytical ? '<p class="analytical-scope">Esta síntese analítica fundamentou esta aplicação. Não é uma descoberta feita durante a consulta nem prova de benefício em uso.</p>'+para(grounding.authorized_application || grounding.application_scope)+list(grounding.conditions || art.conditions) : '')+
    (items(art.documentary_articulations).length ? '<details><summary>Construção anterior deste conhecimento</summary><p>Este percurso documental antecede a consulta. Não significa que todas as suas premissas tenham sido verificadas neste caso.</p>'+items(art.documentary_articulations).map(a=>para(a.operation)+para(a.added_understanding)+para(a.limit)).join('')+'</details>':'')+
    (items(grounding.criterion_applications).some(row=>row.criterion)?'<h5>Critérios aplicados nesta escolha</h5>'+items(grounding.criterion_applications).map(row=>para(row.criterion)+para(row.justification)).join(''):
      grounding.criterion ? '<h5>Critério aplicado</h5>'+para(grounding.criterion)+para(grounding.criterion.justification) : '')+
    items(grounding.sources || grounding.support).map(source).join('')+
    list(constructionLimits)+'</section>';
}
function checksHTML(checks) {
  return list(items(checks).map(check=>
    (check.explanation || check.message || check.predicate || check.kind || check.id)+
    ' — '+(states[check.state || check.outcome] || check.state || check.outcome || 'Não verificada')));
}
function phasesHTML(conditions, preparedOutputs=[]) {
  const rows=items(conditions), phaseRows=phase=>rows.filter(row=>row.phase===phase);
  const production=phaseRows('production').length?phaseRows('production'):items(preparedOutputs);
  const pending=phaseRows('precondition').filter(row=>!['PASS','SATISFIED'].includes(row.state));
  const phaseList=values=>list(values.map(row=>({label:text(row)+(row.state==='FAIL'?' — não atendida':row.state==='PASS'||row.state==='SATISFIED'?' — conferida':' — ainda precisa ser conferida')})));
  return (production.length?'<div class="step-preparation"><p><strong>O que esta ação propõe preparar:</strong></p>'+list(production)+'<p>Estes recursos não são apresentados como prontos ou já conferidos.</p></div>':'')+
    (pending.length?'<div class="step-conditions"><p><strong>Antes de começar, confirme:</strong></p>'+phaseList(pending)+'</div>':'')+
    (phaseRows('verification').length?'<div class="step-verification"><p><strong>Depois de preparar, confira antes de utilizar:</strong></p>'+phaseList(phaseRows('verification'))+'</div>':'');
}
function relationshipHTML(relation) {
  const names={DEPENDENT_SEQUENCE:'Uma ação prepara a seguinte',SEQUENTIAL:'Uma ação prepara a seguinte',SEQUENTIAL_REVIEW:'Revisão do mesmo conteúdo',
    FUNCTIONAL_ALTERNATIVE:'Outra forma de realizar a mesma função',ALTERNATIVE:'Outra forma de realizar a mesma função',COMPLEMENTARITY:'Partes que se completam',REDUNDANCY:'Mesma informação em formas coordenadas'};
  return '<div class="step-combination"><strong>'+esc(names[relation.kind] || 'Relação entre as ações')+':</strong> '+esc(relation.explanation || relation.justification || '')+
    (relation.preservation || relation.preservation_obligation || relation.preserves ? para('O que deve ser preservado: '+items(relation.preservation || relation.preservation_obligation || relation.preserves).map(text).join('; ')) : '')+
    phasesHTML(relation.phase_conditions)+
    (items(relation.groundings || relation.grounding).length?'<details><summary>Por que esta relação pode ser utilizada?</summary>'+items(relation.groundings || relation.grounding).map(groundingHTML).join('')+checksHTML(relation.condition_checks)+'</details>':'')+'</div>';
}
function derivationHTML(step) {
  const origins={EXPLICIT_CONTEXT_REQUIREMENT:'Função informada no contexto',
    DOCUMENTED_FUNCTIONAL_WITNESS:'Necessidade relacionada à matriz funcional',
    REGISTERED_TASK_FUNCTION_REQUIREMENT:'Função necessária à ação representada',
    REGISTERED_TASK_REFINEMENT:'Refinamento da ação, sujeito às condições indicadas'};
  return items(step.function_derivation).map(row=>{
    const fn=items(step.functions).find(f=>f.id===row.function_id);
    const witnesses=items(row.witnesses).flatMap(w=>[
      ...items(w.need_labels),...items(w.characteristic_labels),...items(w.source_texts),
      ...items(w.needs).map(text),...items(w.characteristics).map(text),
      ...items(w.assertions).map(a=>a.source_text).filter(Boolean),
      ...(w.task_label?[w.task_label]:[])]);
    return '<p><strong>'+esc(origins[row.origin] || 'Condição relacionada à função')+':</strong> '+esc(text(fn) || text(row.function) || '')+'</p>'+list(unique(witnesses));
  }).join('');
}
function stepHTML(step, index) {
  const instructions=items(step.instructions).length?items(step.instructions):items(step.action);
  const modes=items(step.modes || step.mode).map(text), functions=items(step.functions || step.function).map(text);
  return '<section class="situated-action"><h4>'+esc(step.label || 'Ação '+(index+1))+'</h4>'+
    (instructions.length>1 ? '<ol class="action-instructions">'+instructions.map(value=>'<li>'+esc(text(value))+'</li>').join('') : para(instructions[0]))+
    (functions.length ? '<p><strong>Finalidade:</strong> '+esc(functions.join('; '))+'</p>' : '')+
    (modes.length ? '<p><strong>Formas de interação desta ação:</strong> '+esc(modes.join('; '))+'</p>' : '')+
    phasesHTML(step.phase_conditions,step.prepared_outputs)+
    (step.monitoring ? '<p><strong>Como observar se ajudou:</strong> '+esc(text(step.monitoring))+'</p>' : '')+
    (items(step.conditions).length ? '<details><summary>Antes de aplicar</summary>'+list(step.conditions)+'</details>' : '')+
    '<details><summary>Por que esta ação foi sugerida?</summary>'+derivationHTML(step)+list(step.correspondences || step.witnesses)+
    items(step.groundings).map(groundingHTML).join('')+checksHTML(step.condition_checks)+list(step.limits || step.limitation)+
    '<details><summary>Conferir identificadores e verificações</summary>'+para([step.id,step.component_id,step.situation_id,step.participant_id].filter(Boolean).join(' · '))+list(step.check_ids)+'</details></details></section>';
}
function choiceTitle(choice) {
  return choice.label || items(choice.steps).map(step=>step.label).filter(Boolean).join(choice.composition_type==='INDEPENDENT_SUPPORTS'?' · ':' → ') || 'Possibilidade de apoio';
}
function choiceHTML(choice,kind,index) {
  const independent=choice.composition_type==='INDEPENDENT_SUPPORTS';
  const title=choiceTitle(choice);
  const scope=[choice.participant_label,choice.situation_label].filter(Boolean).join(' · ');
  const body=(kind==='pending' ? '<p class="step-conditional">Confirme as condições indicadas antes de aplicar esta possibilidade.</p>' :
    choice.ready_for_application===false?'<p class="step-conditional">Há ações fundamentadas para este caso. Prepare e confira os pontos indicados antes de utilizar o resultado.</p>':'')+
    (independent?'<p class="independent-supports">Estes apoios atendem necessidades diferentes. Não há uma sequência obrigatória nem uma relação multimodal presumida entre eles.</p>':'')+
    items(choice.steps).map(stepHTML).join('')+items(choice.relations).map(relationshipHTML).join('')+
    (items(choice.missing_functions).length ? '<p><strong>Esta opção ainda não cobre:</strong></p>'+list(choice.missing_functions) : '')+
    (items(choice.limits).length?'<details><summary>Limites deste percurso</summary>'+list(choice.limits)+'</details>':'');
  return '<details class="orientation-step situated-choice"'+(index===0?' open':'')+'><summary>'+esc(title)+
    (scope?' <span class="choice-context">'+esc(scope)+'</span>':'')+'</summary>'+body+'</details>';
}
/** No invented modality, step, consequence or automatic equivalence. */
export function situatedOutput(response) {
  const executionChecks=Array.isArray(response.execution_evidence)?response.execution_evidence:items(response.execution_evidence?.checks);
  const checks=new Map(executionChecks.map(check=>[check.id,check]));
  const checked=item=>({...item,condition_checks:item.condition_checks || items(item.check_ids).map(id=>checks.get(id)).filter(Boolean)});
  const contextualize=choice=>({...choice,steps:items(choice.steps).map(checked),relations:items(choice.relations).map(checked)});
  const choices=[...items(response.choices).map(c=>[contextualize(c),'complete']),...items(response.partial_segments).map(c=>[contextualize(c),'partial']),...items(response.pending_candidates).map(c=>[contextualize(c),'pending'])];
  // Presentation order only: do not lead with a generic single support when
  // an actual proposal covers more required functions. Stable ties preserve
  // the producer's order; pending states and missing coverage remain explicit.
  choices.sort(([left],[right])=>items(right.covered_functions).length-items(left.covered_functions).length);
  const seen=new Set();
  const rendered=choices.filter(([choice])=>{const key=JSON.stringify([choice.situation_id,choice.participant_id,items(choice.steps).map(s=>s.id),items(choice.relations).map(r=>r.id)]);if(seen.has(key))return false;seen.add(key);return true;});
  const state={COMPLETE:response.covers_whole_reported_task===false?'Apoio às funções identificadas':'Percurso com condições conferidas',PARTIAL:'Apoio para parte do desafio',CONDITIONAL:'Possibilidades a confirmar',NONE:'Ainda sem uma operação fundamentada',UNCONFIRMED:'Confira o entendimento antes de gerar'}[response.proposal_status] || 'Confira o alcance desta orientação';
  const scoped=row=>typeof row==='object'&&row?[row.participant_label,row.situation_label,
    row.explanation?[row.label,row.explanation].filter(Boolean).join(': '):row.message || text(row)].filter(Boolean).join(' — '):row;
  const gaps=unique(items(response.gaps).map(scoped)), coverage=items(response.coverage || response.function_coverage).map(row=>typeof row==='object'?
    [row.participant_label,row.situation_label,text(row.function),{CAPABILITY_AVAILABLE:'há operação com condições conferidas',CONDITIONAL_CAPABILITY:'depende de condições a confirmar',NO_AVAILABLE_CAPABILITY:'ainda sem operação utilizável'}[row.state] || text(row)].filter(Boolean).join(' — '):row);
  const html=(rendered.length?'<p>Examine uma possibilidade por vez. Ações independentes não precisam ser executadas em sequência.</p>'+rendered.map(([choice,kind],index)=>choiceHTML(choice,kind,index)).join(''):
    '<p>Não foi encontrada uma operação fundamentada para as condições confirmadas. Os motivos abaixo distinguem o que falta informar do que ainda falta representar na base.</p>')+
    para(response.coverage_explanation)+
    (gaps.length?'<aside class="orientation-gaps"><h3>O que ficou sem cobertura</h3>'+list(gaps)+'</aside>':'');
  return {title:rendered.length?'O que você pode fazer':'O que falta para orientar este caso',state,html,
    detailHTML:'<h3>Cobertura por pessoa e situação</h3>'+list(coverage)+list(response.limits),
    foundationHTML:'<p>Os registros abaixo pertencem a esta execução; não representam leitura das normas na internet.</p>'+rendered.map(([choice])=>
      '<details><summary>'+esc(choiceTitle(choice))+'</summary>'+items(choice.steps).map(step=>'<h4>'+esc(step.label)+'</h4>'+items(step.groundings).map(groundingHTML).join('')+checksHTML(step.condition_checks)).join('')+
      items(choice.relations).map(relationshipHTML).join('')+'</details>').join('')+
      '<details><summary>Possibilidades excluídas e verificações</summary>'+list(unique(response.exclusions))+checksHTML(executionChecks)+'</details>'};
}
