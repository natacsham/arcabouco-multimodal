// Presentation only. The execution remains the single origin of actions and grounds.
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
const unique = values => [...new Map(items(values).filter(Boolean).map(value=>[JSON.stringify(value),value])).values()];
const uniqueText = values => [...new Map(items(values).map(text).filter(Boolean).map(value=>[value,value])).values()];
const states = {PASS:'Conferida',SATISFIED:'Conferida',FAIL:'Não atendida',PENDING:'A confirmar',NOT_EXECUTED:'Não verificada'};
const sourceStates = {CONFERIDA_NO_REGISTRO:'Conferida no registro preservado',CONFERIDA_NO_DOCUMENTO:'Conferida no documento',PRIMARY_CHECKED:'Conferida na fonte primária',PENDING:'Conferência pendente'};
const originAttr = (path,phase) => ' data-origin-path="'+esc(path)+'"'+(phase?' data-phase="'+esc(phase)+'"':'');
const known = row => ['PASS','SATISFIED'].includes(row.state || row.outcome);
const trimSentence = value => String(text(value)).replace(/[?.]\s*$/,'');
function humanCondition(row) {
  const value=trimSentence(row);
  if(/^Ao menos um recurso:\s*/i.test(value)) return 'Informe se há como utilizar '+value.replace(/^Ao menos um recurso:\s*/i,'')+'.';
  if(/^Recurso:\s*/i.test(value)) return 'Confirme a disponibilidade de '+value.replace(/^Recurso:\s*/i,'')+'.';
  return (row.state==='FAIL'?'Esta condição não foi atendida: ':'Confirme: ')+value+'.';
}
function verificationAction(value) {
  const raw=String(text(value)).trim();
  if(!raw)return '';
  // This changes the framing of the existing check, not its meaning or result.
  if(/\?$/.test(raw)) return 'Confira: '+trimSentence(raw)+'.';
  return raw.replace(/^Depois de preparar,\s*conferir\b/i,'Depois de preparar, confira');
}
function actionProjection(step,path) {
  const raw=items(step.instructions).length?items(step.instructions):items(step.action);
  const field=items(step.instructions).length?'instructions':'action';
  const rows=raw.map((value,index)=>({text:text(value),phase:'action',origin_path:path+'.'+field+(field==='instructions'?'['+index+']':''),source_text:text(value)})).filter(row=>row.text);
  const absorbed=[];
  items(step.phase_conditions).forEach((row,index)=>{
    if(!['production','verification'].includes(row.phase))return;
    const source_text=String(text(row)),origin_path=path+'.phase_conditions['+index+']';
    // The generic production reminder is already expressed by the scoped action.
    // Keep its provenance without adding a redundant "prepare the resource" step.
    if(rows.length && row.phase==='production' && /^Preparar o recurso proposto e conservar a informação identificada como necessária\.?$/i.test(source_text)){
      absorbed.push({origin_path,source_text});return;
    }
    const rendered=row.phase==='verification'?verificationAction(row):source_text;
    if(rows.some(item=>item.text===rendered)){absorbed.push({origin_path,source_text});return;}
    rows.push({text:rendered,phase:row.phase,origin_path,source_text,state:row.state});
  });
  return {id:step.id,origin_path:path,rows,absorbed_origins:absorbed};
}
function preconditionsHTML(step,path,reviewEnabled) {
  const pending=items(step.phase_conditions).map((row,index)=>({row,path:path+'.phase_conditions['+index+']'})).filter(({row})=>row.phase==='precondition'&&!known(row));
  const conditions=items(step.conditions);
  if(!pending.length&&!conditions.length)return '';
  return '<div class="step-conditions"><p><strong>Antes de aplicar</strong></p><ul>'+pending.map(({row,path:origin})=>
    '<li'+originAttr(origin,'precondition')+'>'+esc(humanCondition(row))+'</li>').join('')+
    conditions.map((row,index)=>'<li'+originAttr(path+'.conditions['+index+']','precondition')+'>'+esc(text(row))+'</li>').join('')+
    '</ul>'+(pending.length&&reviewEnabled?'<button type="button" class="secondary" data-edit-case>Revisar esta informação</button>':'')+'</div>';
}
function practicalStep(step,index,choice,path,projections,reviewEnabled,start=1) {
  const projection=actionProjection(step,path);projections.push(projection);
  const responsibleRecord=step.responsible_participant;
  const responsibleLabel=text(responsibleRecord);
  const responsible=responsibleLabel && responsibleLabel===responsibleRecord?.id ?
    (step.operation_scope==='PREPARATION_FOR_RECIPIENT'?'Responsável pela preparação informado no relato':'Participante responsável informado no relato'):responsibleLabel;
  const beneficiary=step.participant_label||choice.participant_label;
  const modes=uniqueText(step.modes || step.mode),functions=uniqueText(step.functions || step.function);
  // `limitation` belongs to the historical pattern. The selected operational
  // contract supplies `limits`; do not turn the former into a new instruction.
  const limits=uniqueText(step.limits);
  const heading=items(choice.steps).length===1&&choiceTitle(choice)===step.label?'Passos':step.label||'Ação '+(index+1);
  return '<section class="situated-action"><h4>'+esc(heading)+'</h4>'+
    (responsible?'<p class="step-responsible"'+originAttr(path+'.responsible_participant')+'><strong>Quem realiza:</strong> '+esc(responsible)+'</p>':'')+
    (beneficiary?'<p class="step-beneficiary"'+originAttr(step.participant_label?path+'.participant_label':path.replace(/\.steps\[\d+\]$/,'')+'.participant_label')+'><strong>Para quem:</strong> '+esc(beneficiary)+'</p>':'')+
    (projection.rows.length?'<ol class="action-instructions" role="list" start="'+start+'">'+projection.rows.map((row,i)=>'<li'+originAttr(row.origin_path,row.phase)+'><span class="step-number">Passo '+(start+i)+'. </span><span class="step-instruction-text">'+esc(row.text)+'</span></li>').join('')+'</ol>':'')+
    (modes.length?'<p class="step-modes"'+originAttr(path+'.modes')+'><strong>Formas de interação:</strong> '+esc(modes.join('; '))+'</p>':'')+
    (functions.length?'<p class="step-purpose"'+originAttr(path+'.functions')+'><strong>Para quê:</strong> '+esc(functions.join('; '))+'</p>':'')+
    preconditionsHTML(step,path,reviewEnabled)+
    (step.monitoring?'<p class="step-monitoring"'+originAttr(path+'.monitoring')+'><strong>Como conferir:</strong> '+esc(text(step.monitoring))+'</p>':'')+
    (limits.length?'<div class="step-limits"><p><strong>Limites desta ação</strong></p>'+list(limits)+'</div>':'')+'</section>';
}
const relationNames={DEPENDENT_SEQUENCE:'Uma ação prepara a seguinte',SEQUENTIAL:'Uma ação prepara a seguinte',SEQUENTIAL_REVIEW:'Revisão do mesmo conteúdo',
  FUNCTIONAL_ALTERNATIVE:'Outra forma de realizar a mesma função',ALTERNATIVE:'Outra forma de realizar a mesma função',COMPLEMENTARITY:'Partes que se completam',REDUNDANCY:'Mesma informação em formas coordenadas'};
function practicalRelation(relation,path,reviewEnabled) {
  const preservation=relation.preservation||relation.preservation_obligation||relation.preserves;
  const preservationField=relation.preservation?'preservation':relation.preservation_obligation?'preservation_obligation':'preserves';
  const later=items(relation.phase_conditions).map((row,index)=>({row,path:path+'.phase_conditions['+index+']'})).filter(({row})=>row.phase!=='precondition');
  return '<div class="step-combination"><p><strong>'+esc(relationNames[relation.kind]||'Relação entre as ações')+':</strong> '+esc(relation.explanation||relation.justification||'')+'</p>'+
    (preservation?'<p'+originAttr(path+'.'+preservationField)+'><strong>O que deve ser preservado:</strong> '+esc(items(preservation).map(text).join('; '))+'</p>':'')+
    preconditionsHTML(relation,path,reviewEnabled)+(later.length?'<p><strong>Como conferir a combinação</strong></p><ul>'+later.map(({row,path:origin})=>'<li'+originAttr(origin,row.phase)+'>'+esc(verificationAction(row))+'</li>').join('')+'</ul>':'')+'</div>';
}
const choiceTitle=choice=>choice.label||items(choice.steps).map(step=>step.label).filter(Boolean).join(choice.composition_type==='INDEPENDENT_SUPPORTS'?' · ':' → ')||'Possibilidade de apoio';
const numberedChoiceTitle=(choice,index)=>'<span class="orientation-number">Orientação '+(index+1)+'</span> <span class="orientation-title">'+esc(choiceTitle(choice))+'</span>';
function practicalChoice(choice,kind,index,path,projections,reviewEnabled) {
  const scope=[choice.participant_label,choice.situation_label].filter(Boolean).join(' · ');
  // Only an already ordered path shares step numbers across operations.
  // Independent supports and functional alternatives do not acquire an order.
  const sequential=choice.composition_type==='CONNECTED_PATH'&&items(choice.relations).length>0&&
    items(choice.relations).every(row=>['DEPENDENT_SEQUENCE','SEQUENTIAL','SEQUENTIAL_REVIEW'].includes(row.kind));
  let nextStep=1;
  const actions=items(choice.steps).map((step,i)=>{
    const result=practicalStep(step,i,choice,path+'.steps['+i+']',projections,reviewEnabled,sequential?nextStep:1);
    nextStep+=projections[projections.length-1].rows.length;
    return result;
  }).join('');
  return '<article class="orientation-step situated-choice" data-choice-index="'+index+'"><h3>'+numberedChoiceTitle(choice,index)+'</h3>'+
    (scope?'<p class="choice-context">'+esc(scope)+'</p>':'')+
    (kind==='pending'?'<p class="step-conditional">Esta possibilidade depende das condições indicadas em “Antes de aplicar”.</p>':'')+
    (choice.composition_type==='INDEPENDENT_SUPPORTS'?'<p class="independent-supports">Estes apoios podem ser utilizados separadamente. Não há uma sequência obrigatória entre eles.</p>':'')+
    actions+
    items(choice.relations).map((row,i)=>practicalRelation(row,path+'.relations['+i+']',reviewEnabled)).join('')+
    (items(choice.missing_functions).length?'<div class="step-missing"><p><strong>Esta opção ainda não cobre:</strong></p>'+list(choice.missing_functions)+'</div>':'')+'</article>';
}
function derivation(step) {
  const rows=items(step.function_derivation),reported=[],needs=[];
  for(const row of rows){
    const fn=items(step.functions).find(f=>f.id===row.function_id);if(text(fn||row.function))needs.push(text(fn||row.function));
    for(const witness of items(row.witnesses)){
      reported.push(...items(witness.source_texts),...items(witness.assertions).map(a=>a.source_text).filter(Boolean));
      needs.push(...items(witness.need_labels),...items(witness.characteristic_labels),...items(witness.needs).map(text),...items(witness.characteristics).map(text));
      if(witness.task_label)needs.push(witness.task_label);
    }
  }
  return {reported:uniqueText(reported),needs:uniqueText(needs)};
}
function sourceInfo(row) {
  const s=row.source||row,url=s.url||s.document_url||row.document_url;
  return {id:s.source_id||s.id||row.source_id,name:s.title||s.titulo||s.label||s.source_id||s.id||'Fonte registrada',url,
    excerpt_id:row.excerpt_id||row.excerpt?.id||s.excerpt_id,
    locator:row.locator||row.location||row.excerpt?.locator||s.locator||s.location,
    status:row.review_status||row.verification_status||row.status||s.review_status};
}
function groundingRows(step){return items(step.groundings||step.grounding);}
function foundation(rendered,executionChecks,response,coverage) {
  const contributions=new Map(),sources=new Map(),analyses=new Map();
  const sourceRef=row=>{
    const info=sourceInfo(row),key=JSON.stringify([info.id||info.name,info.excerpt_id||info.locator||info.url]);
    if(!sources.has(key))sources.set(key,{...info,anchor:'amado-source-'+(sources.size+1),statuses:new Set()});
    const stored=sources.get(key);if(info.status)stored.statuses.add(info.status);return stored;
  };
  const contributionRef=(row,ground)=>{
    const related=items(ground.sources).find(s=>(s.id||s.source_id)===row.source_id&&s.excerpt_id===row.excerpt_id);
    const source=(row.source||related)?sourceRef(row.source?row:related):null;
    const key=row.id||JSON.stringify([row.statement||row.text,source?.anchor]);
    if(!contributions.has(key))contributions.set(key,{...row,source,anchor:'amado-contribution-'+(contributions.size+1)});
    return contributions.get(key);
  };
  const projections=rendered.map(({choice,path},index)=>{
    const grounds=items(choice.steps).flatMap(groundingRows).concat(items(choice.relations).flatMap(groundingRows));
    const contributionLinks=[],sourceLinks=[],analysisLinks=[],criteria=[],limits=[];
    for(const ground of grounds){
      const art=ground.construction||ground.articulation||{};
      const refs=items(ground.contributions||art.contributions).map(row=>contributionRef(row,ground));
      contributionLinks.push(...refs);
      // A source attached to a contribution is shown there once. Other exact
      // supporting references remain available, without asserting a new premise.
      sourceLinks.push(...items(ground.sources||ground.support).map(sourceRef));
      const analytical=ground.application_kind==='GROUNDED_ANALYTICAL_APPLICATION';
      if(analytical||!refs.length){
        const key=ground.analytical_application_id||ground.claim_id||ground.id||JSON.stringify([art.operation,art.added_understanding,text(ground.knowledge)]);
        if(!analyses.has(key))analyses.set(key,{anchor:'amado-analysis-'+(analyses.size+1),ground,art,analytical,refs});
        analysisLinks.push(analyses.get(key));
      }
      for(const row of items(ground.criterion_applications).length?ground.criterion_applications:ground.criterion?[{criterion:ground.criterion,justification:ground.criterion.justification||ground.justification,origin_ids:ground.origin_ids}]:[]){
        if(text(row.criterion))criteria.push({label:text(row.criterion),justification:row.justification,origin_ids:row.origin_ids,ground_id:ground.id});
      }
      limits.push(...items(ground.limits),...items(art.limits),...items(ground.claims||ground.claim).flatMap(claim=>items(claim.limits)));
    }
    const derivations=items(choice.steps).map(derivation),scope=[choice.participant_label,choice.situation_label].filter(Boolean).join(' · ');
    const sourceSet=new Set(contributionLinks.map(row=>row.source?.anchor).filter(Boolean));
    const links=unique(contributionLinks.map(row=>({anchor:row.anchor,label:row.source?row.source.name+(row.source.locator?' — '+row.source.locator:''):'Contribuição registrada'})));
    const extraSources=unique(sourceLinks.filter(row=>!sourceSet.has(row.anchor)).map(row=>({anchor:row.anchor,label:row.name+(row.locator?' — '+row.locator:'')})));
    const referredAnalyses=unique(analysisLinks.map(row=>({anchor:row.anchor,label:text(row.art.added_understanding)||text(row.ground.knowledge)||text(row.ground.claim)||'Compreensão registrada'})));
    return {choice,path,index,grounds,scope,reported:uniqueText(derivations.flatMap(d=>d.reported)),needs:uniqueText(derivations.flatMap(d=>d.needs)),links,extraSources,referredAnalyses,criteria,limits:uniqueText(limits)};
  });
  const linkList=rows=>rows.length?'<ul>'+rows.map(row=>'<li><a href="#'+esc(row.anchor)+'">'+esc(row.label)+'</a></li>').join('')+'</ul>':'';
  const choicesHTML=projections.map(p=>'<section class="foundation-choice"><h3>'+numberedChoiceTitle(p.choice,p.index)+'</h3>'+para(p.scope)+
    '<h4>Informação considerada no relato</h4>'+(p.reported.length?list(p.reported):para('O vínculo desta escolha está registrado pelas condições e funções abaixo; não há um trecho do relato associado neste resultado.'))+
    '<h4>Necessidade identificada</h4>'+list(p.needs)+
    '<h4>Contribuições das fontes</h4>'+linkList(p.links)+linkList(p.extraSources)+
    '<h4>Compreensão utilizada</h4>'+linkList(p.referredAnalyses)+
    '<h4>Critério e escolha autorizada</h4>'+list(uniqueText(p.criteria.map(row=>row.label)))+
    list(uniqueText(items(p.choice.steps).map(step=>step.action)))+
    (items(p.choice.relations).length?list(items(p.choice.relations).map(row=>(relationNames[row.kind]||'Relação entre as ações')+': '+text(row.explanation||row.preserves))):'')+
    '<h4>Condições verificadas e limites</h4>'+checksHTML(items(p.choice.steps).concat(items(p.choice.relations)).flatMap(row=>items(row.condition_checks)).filter(row=>row.phase==='precondition'))+
    list(uniqueText([...p.limits,...items(p.choice.limits)]))+'</section>').join('');
  const contributionsHTML=[...contributions.values()].map(row=>'<section class="step-grounding foundation-contribution" id="'+esc(row.anchor)+'" data-contribution-id="'+esc(row.id||'')+'"><h4>'+esc(text(row)||'Contribuição registrada')+'</h4>'+
    (row.source?'<p><a href="#'+esc(row.source.anchor)+'">'+esc(row.source.name+(row.source.locator?' — '+row.source.locator:''))+'</a></p>':'')+'</section>').join('');
  const analysesHTML=[...analyses.values()].map(row=>'<section class="step-grounding foundation-analysis" id="'+esc(row.anchor)+'"><h4>'+(row.analytical?'Como as contribuições foram articuladas':'Conhecimento empregado')+'</h4>'+
    (row.refs.length?'<p><strong>Contribuições relacionadas nesta compreensão:</strong></p>'+linkList(unique(row.refs.map(ref=>({anchor:ref.anchor,label:ref.source?ref.source.name+(ref.source.locator?' — '+ref.source.locator:''):'Contribuição registrada'})))):'')+
    para(row.art.operation||row.ground.justification)+
    (row.art.added_understanding?'<p><strong>Compreensão resultante:</strong> '+esc(text(row.art.added_understanding))+'</p>':para(row.ground.knowledge||row.ground.claim))+
    para(row.ground.authorized_application||row.ground.application_scope)+
    (row.analytical?'<p>Esta síntese foi construída na pesquisa. A consulta verifica sua aplicação ao caso; não demonstra benefício em uso.</p>':'')+
    list(uniqueText([...items(row.ground.conditions),...items(row.art.conditions)]))+'</section>').join('');
  const sourcesHTML=[...sources.values()].map(row=>'<section class="foundation-source" id="'+esc(row.anchor)+'"><h4>'+esc(row.name)+'</h4>'+para(row.locator)+
    (/^https?:\/\//.test(row.url||'')?'<p><a href="'+esc(row.url)+'" rel="noreferrer">Consultar '+esc(row.name)+'</a></p>':'')+
    list([...row.statuses].map(state=>sourceStates[state]||state))+'</section>').join('');
  const technical=projections.map(p=>'<section><h4>'+numberedChoiceTitle(p.choice,p.index)+'</h4>'+items(p.choice.steps).concat(items(p.choice.relations)).map(row=>
    '<p>'+esc([row.id,row.component_id,row.participant_id,row.situation_id].filter(Boolean).join(' · '))+'</p>'+list(row.check_ids)).join('')+
    items(p.choice.steps).filter(row=>row.limitation).map(row=>'<p><strong>Limite do padrão histórico, não instrução adicional desta operação:</strong> '+esc(text(row.limitation))+'</p>').join('')+
    p.grounds.map(g=>{const art=g.construction||g.articulation||{};return '<p>'+esc([g.id,g.claim_id,g.analytical_application_id,...items(g.origin_ids)].filter(Boolean).join(' · '))+'</p>'+para(g.justification||g.justificativa)+
      list(items(g.criterion_applications).map(a=>[text(a.criterion),...items(a.origin_ids),a.justification].filter(Boolean).join(' — ')))+
      (items(art.documentary_articulations).length?'<p><strong>Trajetória histórica, não confirmação desta aplicação:</strong></p>'+items(art.documentary_articulations).map(a=>para(a.operation)+para(a.added_understanding)+para(a.limit)).join(''):'');}).join('')+'</section>').join('');
  return '<p>O percurso liga as informações deste caso aos conhecimentos preparados na base. As fontes não são lidas na internet durante a geração.</p>'+choicesHTML+
    (contributionsHTML?'<section class="foundation-contributions"><h3>O que cada fonte contribuiu</h3>'+contributionsHTML+'</section>':'')+
    (analysesHTML?'<section class="foundation-understanding"><h3>Articulação e compreensão resultante</h3>'+analysesHTML+'</section>':'')+
    (sourcesHTML?'<section class="foundation-sources"><h3>Fontes e localizações</h3>'+sourcesHTML+'</section>':'')+
    '<section class="foundation-coverage"><h3>Cobertura por pessoa e situação</h3>'+list(coverage)+list(response.limits)+'</section>'+
    '<details class="foundation-technical"><summary>Consultar identificadores, histórico e verificações</summary>'+technical+
    '<h3>Possibilidades excluídas</h3>'+list(unique(response.exclusions))+'<h3>Verificações executadas</h3>'+checksHTML(executionChecks)+'</details>';
}
function checksHTML(checks){return list(unique(items(checks)).map(check=>(check.explanation||check.message||check.predicate||check.kind||check.id)+' — '+(states[check.state||check.outcome]||check.state||check.outcome||'Não verificada')));}
/** No selected operation, representation, relationship or epistemic state is changed. */
export function situatedOutput(response,{reviewEnabled=true}={}) {
  const executionChecks=Array.isArray(response.execution_evidence)?response.execution_evidence:items(response.execution_evidence?.checks);
  const checks=new Map(executionChecks.map(check=>[check.id,check]));
  const checked=item=>({...item,condition_checks:item.condition_checks||items(item.check_ids).map(id=>checks.get(id)).filter(Boolean)});
  const choices=['choices','partial_segments','pending_candidates'].flatMap((field,group)=>items(response[field]).map((choice,index)=>({
    choice:{...choice,steps:items(choice.steps).map(checked),relations:items(choice.relations).map(checked)},kind:['complete','partial','pending'][group],path:field+'['+index+']'})));
  // Keep the existing coverage-first presentation, including stable ties.
  choices.sort((a,b)=>items(b.choice.covered_functions).length-items(a.choice.covered_functions).length);
  const seen=new Set(),rendered=choices.filter(({choice})=>{const key=JSON.stringify([choice.situation_id,choice.participant_id,items(choice.steps).map(s=>s.id),items(choice.relations).map(r=>r.id)]);if(seen.has(key))return false;seen.add(key);return true;});
  const state={COMPLETE:response.covers_whole_reported_task===false?'Apoio às funções identificadas':'Percurso com condições conferidas',PARTIAL:'Apoio para parte do desafio',CONDITIONAL:'Possibilidades a confirmar',NONE:'Ainda sem uma operação fundamentada',UNCONFIRMED:'Confira o entendimento antes de gerar'}[response.proposal_status]||'Confira o alcance desta orientação';
  const scoped=row=>typeof row==='object'&&row?[row.participant_label,row.situation_label,row.explanation?[row.label,row.explanation].filter(Boolean).join(': '):row.message||text(row)].filter(Boolean).join(' — '):row;
  const gaps=unique(items(response.gaps).map(scoped)),coverage=items(response.coverage||response.function_coverage).map(row=>typeof row==='object'?
    [row.participant_label,row.situation_label,text(row.function),{CAPABILITY_AVAILABLE:'há operação com condições conferidas',CONDITIONAL_CAPABILITY:'depende de condições a confirmar',NO_AVAILABLE_CAPABILITY:'ainda sem operação utilizável'}[row.state]||text(row)].filter(Boolean).join(' — '):row);
  const projections=[];
  const html=(rendered.length?rendered.map(({choice,kind,path},index)=>practicalChoice(choice,kind,index,path,projections,reviewEnabled)).join(''):
    '<p>Não foi encontrada uma ação fundamentada para as condições confirmadas. Confira abaixo se falta uma informação do caso ou um apoio representado na base.</p>')+
    para(response.coverage_explanation)+(gaps.length?'<aside class="orientation-gaps"><h3>O que ficou sem cobertura</h3>'+list(gaps)+'</aside>':'');
  return {title:'O que fazer',state,html,detailHTML:'',foundationHTML:foundation(rendered,executionChecks,response,coverage),actionProjection:projections};
}
