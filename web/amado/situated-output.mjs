// Presentation only: every action and relationship comes from this execution.
const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const items = value => Array.isArray(value) ? value : value ? [value] : [];
const diagnosticLabels={NO_DOCUMENTED_FUNCTION_REQUIREMENT:'Ainda não há uma necessidade funcional fundamentada e atribuída a esta pessoa nesta situação.',
  INPUT_REQUIRES_CORRECTION:'Há informações ambíguas ou incompatíveis no entendimento do caso. Revise os pontos indicados.',
  NO_COMPLETE_SITUATED_COMPOSITION:'Os apoios apresentados não cobrem toda a atividade para todos os participantes. Confira o alcance de cada opção.',
  NO_AUTHORIZED_RELATION:'Há ações possíveis, mas a base ainda não fundamenta sua combinação para esta situação.',
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
  return para(name)+(row.locator || row.location ? para(row.locator || row.location) : '')+
    (/^https?:\/\//.test(url || '') ? '<a href="'+esc(url)+'" rel="noreferrer">Consultar a fonte</a>' : '')+
    para(row.review_status || row.verification_status || row.status);
}
function groundingHTML(grounding) {
  const art = grounding.articulation || {}, knowledge = grounding.knowledge || {};
  const contributions = grounding.contributions || art.contributions || [];
  const claims = items(grounding.claims || grounding.claim);
  return '<section class="step-grounding">'+
    para(grounding.justification || grounding.justificativa)+
    (text(knowledge) ? '<h5>Conhecimento empregado</h5>'+para(knowledge) : '')+
    claims.map(claim=>para(claim.statement || claim.text)+list(claim.limits)).join('')+
    (contributions.length ? '<h5>O que as fontes acrescentaram</h5>'+contributions.map(c=>{
      const located=c.source?c:items(grounding.sources).find(s=>s.id===c.source_id && s.excerpt_id===c.excerpt_id);
      return para(c.statement || c.text)+(located?source(located):'');
    }).join('') : '')+
    (art.operation || art.added_understanding ? '<h5>Como o fundamento foi empregado</h5>'+para(art.operation)+para(art.added_understanding) : '')+
    (items(art.documentary_articulations).length ? '<details><summary>Construção anterior deste conhecimento</summary><p>Este percurso documental antecede a consulta. Não significa que todas as suas premissas tenham sido verificadas neste caso.</p>'+items(art.documentary_articulations).map(a=>para(a.operation)+para(a.added_understanding)+para(a.limit)).join('')+'</details>':'')+
    (grounding.criterion ? '<h5>Critério aplicado</h5>'+para(grounding.criterion)+para(grounding.criterion.justification) : '')+
    items(grounding.sources || grounding.support).map(source).join('')+
    list(grounding.limits)+'</section>';
}
function checksHTML(checks) {
  return list(items(checks).map(check=>
    (check.explanation || check.message || check.predicate || check.kind || check.id)+
    ' — '+(states[check.state || check.outcome] || check.state || check.outcome || 'Não verificada')));
}
function relationshipHTML(relation) {
  const names={DEPENDENT_SEQUENCE:'Uma ação prepara a seguinte',SEQUENTIAL:'Uma ação prepara a seguinte',SEQUENTIAL_REVIEW:'Revisão do mesmo conteúdo',
    FUNCTIONAL_ALTERNATIVE:'Outra forma de realizar a mesma função',ALTERNATIVE:'Outra forma de realizar a mesma função',COMPLEMENTARITY:'Partes que se completam',REDUNDANCY:'Mesma informação em formas coordenadas'};
  return '<div class="step-combination"><strong>'+esc(names[relation.kind] || 'Relação entre as ações')+':</strong> '+esc(relation.explanation || relation.justification || '')+
    (relation.preservation || relation.preservation_obligation || relation.preserves ? para('O que deve ser preservado: '+items(relation.preservation || relation.preservation_obligation || relation.preserves).map(text).join('; ')) : '')+'</div>';
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
    (step.monitoring ? '<p><strong>Como observar se ajudou:</strong> '+esc(text(step.monitoring))+'</p>' : '')+
    (items(step.conditions).length ? '<details><summary>Antes de aplicar</summary>'+list(step.conditions)+'</details>' : '')+
    '<details><summary>Por que esta ação foi sugerida?</summary>'+derivationHTML(step)+list(step.correspondences || step.witnesses)+
    items(step.groundings).map(groundingHTML).join('')+checksHTML(step.condition_checks)+list(step.limits || step.limitation)+
    '<details><summary>Conferir identificadores e verificações</summary>'+para([step.id,step.component_id,step.situation_id,step.participant_id].filter(Boolean).join(' · '))+list(step.check_ids)+'</details></details></section>';
}
function choiceHTML(choice,kind,index) {
  const title=choice.label || items(choice.steps).map(step=>step.label).filter(Boolean).join(' → ') || 'Possibilidade de apoio';
  const body=(kind==='pending' ? '<p class="step-conditional">Confirme as condições indicadas antes de aplicar esta possibilidade.</p>' : '')+
    para([choice.participant_label,choice.situation_label].filter(Boolean).join(' · '))+
    items(choice.steps).map(stepHTML).join('')+items(choice.relations).map(relationshipHTML).join('')+
    (items(choice.missing_functions).length ? '<p><strong>Esta opção ainda não cobre:</strong></p>'+list(choice.missing_functions) : '')+
    (items(choice.limits).length?'<details><summary>Limites deste percurso</summary>'+list(choice.limits)+'</details>':'');
  return '<details class="orientation-step situated-choice"'+(index===0?' open':'')+'><summary>'+esc(title)+'</summary>'+body+'</details>';
}
/** No invented modality, step, consequence or automatic equivalence. */
export function situatedOutput(response) {
  const executionChecks=Array.isArray(response.execution_evidence)?response.execution_evidence:items(response.execution_evidence?.checks);
  const checks=new Map(executionChecks.map(check=>[check.id,check]));
  const contextualize=choice=>({...choice,steps:items(choice.steps).map(step=>({...step,
    condition_checks:step.condition_checks || items(step.check_ids).map(id=>checks.get(id)).filter(Boolean)}))});
  const choices=[...items(response.choices).map(c=>[contextualize(c),'complete']),...items(response.partial_segments).map(c=>[contextualize(c),'partial']),...items(response.pending_candidates).map(c=>[contextualize(c),'pending'])];
  const seen=new Set();
  const rendered=choices.filter(([choice])=>{const key=JSON.stringify([choice.situation_id,choice.participant_id,items(choice.steps).map(s=>s.id),items(choice.relations).map(r=>r.id)]);if(seen.has(key))return false;seen.add(key);return true;});
  const state={COMPLETE:'Percurso com condições conferidas',PARTIAL:'Apoio para parte do desafio',CONDITIONAL:'Possibilidades a confirmar',NONE:'Ainda sem uma operação fundamentada',UNCONFIRMED:'Confira o entendimento antes de gerar'}[response.proposal_status] || 'Confira o alcance desta orientação';
  const scoped=row=>typeof row==='object'&&row?[row.participant_label,row.situation_label,text(row)].filter(Boolean).join(' — '):row;
  const gaps=unique(items(response.gaps).map(scoped)), coverage=items(response.coverage || response.function_coverage).map(row=>typeof row==='object'?
    [row.participant_label,row.situation_label,text(row.function),{CAPABILITY_AVAILABLE:'há operação com condições conferidas',CONDITIONAL_CAPABILITY:'depende de condições a confirmar',NO_AVAILABLE_CAPABILITY:'ainda sem operação utilizável'}[row.state] || text(row)].filter(Boolean).join(' — '):row);
  const html=(rendered.length?'<p>Examine uma possibilidade por vez. Ações independentes não precisam ser executadas em sequência.</p>'+rendered.map(([choice,kind],index)=>choiceHTML(choice,kind,index)).join(''):
    '<p>Não foi encontrada uma operação fundamentada para as condições confirmadas. Os motivos abaixo distinguem o que falta informar do que ainda falta representar na base.</p>')+
    (gaps.length?'<aside class="orientation-gaps"><h3>O que ficou sem cobertura</h3>'+list(gaps)+'</aside>':'');
  return {title:rendered.length?'O que você pode fazer':'O que falta para orientar este caso',state,html,
    detailHTML:'<h3>Cobertura por pessoa e situação</h3>'+list(coverage)+list(response.limits),
    foundationHTML:'<p>Os registros abaixo pertencem a esta execução; não representam leitura das normas na internet.</p>'+rendered.map(([choice])=>
      '<details><summary>'+esc(choice.label || items(choice.steps).map(s=>s.label).join(' → '))+'</summary>'+items(choice.steps).map(step=>'<h4>'+esc(step.label)+'</h4>'+items(step.groundings).map(groundingHTML).join('')+checksHTML(step.condition_checks)).join('')+
      items(choice.relations).map(r=>relationshipHTML(r)+items(r.groundings || r.grounding).map(groundingHTML).join('')).join('')+'</details>').join('')+
      '<details><summary>Possibilidades excluídas e verificações</summary>'+list(unique(response.exclusions))+checksHTML(executionChecks)+'</details>'};
}
