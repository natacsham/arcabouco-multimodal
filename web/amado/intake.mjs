// Pure presentation helpers. Extraction is a draft for human confirmation;
// neither a resource name nor a diagnosis proves a functional capability.
const copy = value => JSON.parse(JSON.stringify(value));
const norm = value => String(value || '').normalize('NFD').replace(/\p{M}/gu, '').toLowerCase();
const uniq = values => [...new Set(values)];
const fields = {
  tarefas: ['TAREFA', 'O que a pessoa precisa conseguir fazer?'],
  caracteristicas_pessoa: ['CARACTERISTICA_PESSOA', 'Que capacidades ou dificuldades precisamos considerar?'],
  barreiras: ['BARREIRA', 'Quais dificuldades precisam ser consideradas?'],
  necessidades: ['NECESSIDADE', 'Que apoio faz falta?'],
  ambientes: ['AMBIENTE', 'Onde isso acontece?'],
  modalidades_disponiveis: ['MODALIDADE', 'Que formas de interação podem ser usadas?'],
  recursos_digitais: ['RECURSO_DIGITAL', 'Qual aplicativo ou conteúdo está envolvido?'],
  recursos_disponiveis: ['RECURSO_DISPONIVEL', 'Quais equipamentos e apoios estão disponíveis?'],
};
function options(catalog, type, selected = [], field, allowed) {
  return (catalog?.concepts?.[type] || []).filter(item => selected.includes(item.id) ||
    ((type === 'PAPEL_NO_CONTEXTO' || item.curated !== false || Array.isArray(allowed) && allowed.includes(item.id)) && item.scope !== 'CASO_ENTREVISTA'))
    .filter(item => !Array.isArray(allowed) || allowed.includes(item.id) || selected.includes(item.id))
    .filter(item => type !== 'CARACTERISTICA_PESSOA' || item.categoria !== 'ESCOPO_DE_PUBLICO' || selected.includes(item.id))
    .sort((a, b) => (a.order || 500) - (b.order || 500) || a.label.localeCompare(b.label, 'pt-BR'))
    .map(item => ({id: item.id, label: item.label, ...(field ? {field} : {})}));
}
function participants(current, catalog) {
  if (current.participations) return copy(current.participations);
  const byLabel = new Map(Object.values(catalog?.concepts || {}).flat().map(item => [item.label, item.id]));
  const ids = values => (values || []).map(item => typeof item === 'object' ? item.id : byLabel.get(item)).filter(Boolean);
  return (current.context?.participantes || []).map(row => ({id: row.id, papel_id: row.papel_id,
    label: row.label, grupo_rotulo: row.grupo_rotulo, quantidade: row.quantidade,
    observacoes: row.observacoes || '', apoios_informados: row.apoios_informados || '',
    status_evidencia: row.estatuto || row.origem_registro,
    caracteristica_ids: ids(row.caracteristicas), tarefa_ids: ids(row.tarefas),
    modalidade_ids: ids(row.modalidades), recurso_operado_ids: ids(row.recursos_operados),
    objetivo_participacao: row.objetivo || ''}));
}
export function participantName(person, fallback = '') {
  const label = person?.label || fallback || person?.grupo_rotulo || '';
  // Shorten only the engine's generated label. Preserve names and descriptions
  // supplied by people, and do not turn a diagnostic label into an ability.
  const generated = label.match(/^(\d+) estudante\(s\): (.+?) informado no relato$/i);
  if (!generated) return label;
  const count = Number(person?.quantidade || generated[1]);
  const description = person?.grupo_rotulo || generated[2];
  return (count === 1 ? 'Estudante ' : 'Estudantes ') + description + ' (' + count + ')';
}
function activityContext(current, catalog) {
  const context = current.context || {};
  const labels = new Map((catalog?.concepts?.TAREFA || []).map(item => [item.id, item.label]));
  const values = context.tarefas?.length ? context.tarefas : context.raw?.tarefas || [];
  const known = values.map(value => typeof value === 'object' ? value.label || labels.get(value.id) : labels.get(value) ||
    (String(value).startsWith('TAR-') ? '' : value)).filter(Boolean);
  return known.length ? 'Atividade informada: ' + uniq(known).join('; ') : '';
}
// A round is a short clarification, not a survey of every represented route.
// Answered/unknown fields stay completed as conversation steps; this does not
// turn their semantic requirements into confirmed facts.
export function questionRound(pending, answered = new Set(), handled = new Set(), count = 0, limit = 3) {
  const remaining = pending.filter(question => !answered.has(question.id) && !handled.has(question.id));
  const available = Math.max(0, limit - count);
  return {questions: remaining.slice(0, available), remaining: remaining.length,
    // A task answer may expose a useful follow-up. State the stable upper bound
    // instead of promising "one of one" and subsequently increasing the total.
    current: Math.min(count + 1, limit), total: remaining.length ? limit : count};
}
export function legacyQuestions(current, catalog) {
  const raw = current.context?.raw || {};
  const people = participants(current, catalog);
  const pending = (current.questions || []).filter(item => item.field !== 'mapping');
  return pending.filter(item => item.field !== 'apoios_informados' || !pending.some(other =>
    other.participant_id === item.participant_id && other.field === 'modalidades_disponiveis')).map(item => {
    const field = item.field;
    const person = item.participant_id && people.find(row => row.id === item.participant_id);
    const selected = person && item.answer_field ? person[item.answer_field] || [] : raw[field] || [];
    const contextLabel = item.context_label || activityContext(current, catalog);
    const activity = contextLabel.replace(/^Atividade informada:\s*/i, '');
    const scope = activity ? 'Para “'+activity+'”, ' : 'No desafio que você descreveu, ';
    const personLabel = item.participant_id ? participantName(person, item.participant_label) : '';
    const contextual = label => item.label || item.question || scope+label.charAt(0).toLowerCase()+label.slice(1);
    const question = {...item, id: item.id || (item.participant_id ? field+':'+item.participant_id : field),
      field, label: item.question, type: item.type || 'multi', options: [],
      context_label: contextLabel,
      participant_label: personLabel,
      help: item.help || item.reason || 'Marque apenas o que corresponde ao seu caso.', existingParticipations: people};
    if (field === 'objetivo') return {...question, type: 'text', label: contextual('O que você espera que as pessoas consigam fazer?')};
    if (['active_situation_id','digital_use','observation_scope'].includes(field)) return {...question,type:'single',label:contextual('Qual situação você deseja priorizar?'),options:item.options || []};
    if (field === 'functional_observation') return {...question,type:'text',label:contextual('Em qual ação esta pessoa precisa de apoio?')};
    if (field === 'requester_relation') return {...question, type:'single', label:contextual('Como você participa deste desafio?'),
      options:item.options || requesterOptions};
    if (field === 'barreira_ou_necessidade') return {...question, label: contextual('O que dificulta acessar, compreender ou utilizar o conteúdo ou recurso?'),
      help: item.help || item.reason || 'Pode marcar uma ou mais respostas. Não é preciso marcar todas.',
      options: [...options(catalog, 'BARREIRA', raw.barreiras, 'barreiras', item.concept_ids), ...options(catalog, 'NECESSIDADE', raw.necessidades, 'necessidades', item.concept_ids)]};
    if (field === 'participantes') return {...question,
      label: contextual(item.concept_ids ? 'Quem pode preparar ou adaptar o conteúdo ou recurso?' : 'Quem precisa do apoio e quem pode participar?'),
      help: item.help || item.reason || (item.concept_ids ? 'Selecione quem poderá assumir esse apoio.' : 'Inclua quem precisa do apoio e quem pode ajudar.'),
      options: options(catalog, 'PAPEL_NO_CONTEXTO', [], undefined, item.concept_ids)};
    if (field === 'apoios_informados') return {...question, type: 'text',
      label: contextual('Que forma de comunicação ou apoio '+(personLabel ? 'já é usada por '+personLabel : 'já é utilizada')+'?'),
      help: item.help || item.reason || 'Se souber, descreva o que já é usado. Você pode continuar sem preencher.'};
    const config = fields[field];
    const personalLabels = {caracteristicas_pessoa:'O que facilita ou dificulta o acesso de '+personLabel+' ao conteúdo ou recurso?',
      modalidades_disponiveis:'Que formas de acesso ao conteúdo '+personLabel+' já utiliza?', recursos_disponiveis:'Quais destes recursos '+personLabel+' já consegue utilizar?'};
    if (!config) return {...question, label: contextual('Qual informação precisa ser considerada?'), type: 'text'};
    const projected = {...question, label: contextual(item.participant_id ? personalLabels[field] || config[1] : config[1]),
      options: options(catalog, config[0], selected, undefined, item.concept_ids)};
    if(Array.isArray(item.options)) projected.options=projected.options.map(option=>({...option,
      label:item.options.find(explicit=>explicit.id===option.id)?.label || option.label}));
    if (field === 'tarefas' && !item.help && !item.reason) projected.help = 'Pense no que precisa ser feito, como acessar um material, escrever ou participar de uma apresentação.';
    if (item.participant_id && field === 'modalidades_disponiveis') {
      // A game may contain several access modes. It cannot, by itself, answer
      // how a person perceives the content. Keep it in resources and decisions.
      projected.options = projected.options.filter(option => option.id !== 'MOD-JOGO-INTERATIVO');
      projected.help = item.help || item.reason || 'Marque as formas que as pessoas indicadas já usam. Pode escolher mais de uma.';
      projected.note_label = 'Outra forma de comunicação ou apoio (opcional)';
      projected.handles_ids = ['apoios_informados:' + item.participant_id];
    } else if (item.participant_id && field === 'recursos_disponiveis') {
      projected.help = item.help || item.reason || 'Marque os recursos que as pessoas indicadas sabem utilizar.';
    }
    return projected;
  });
}
export function legacyAnswer(current, question, value, note = '') {
  const c = current.context || {};
  const payload = {...copy(c.raw || {}), objetivo: c.objetivo || '', descricao_do_contexto: c.texto_curto || '',
    restricoes: copy(c.restricoes || []), operacao_do_recurso: c.operacao_do_recurso || '',
    impedimentos_verificados: c.impedimentos_verificados === true, mapping_confirmed: false, transfer_confirmed: false};
  payload.requester_relation = c.requester_relation || 'unspecified';
  payload.requester_participation_id = c.requester_participation_id || '';
  payload.question_answers=[{question_id:question.id,
    state:value===null || value===undefined || value==='' || value==='unknown' || (Array.isArray(value) && value.includes('unknown')) ? 'UNKNOWN':'ANSWERED',value}];
  const preservedPeople = copy(question.existingParticipations || participants(current));
  // Global equipment/context answers must not clear distinct personal routes.
  if (preservedPeople.filter(person => ['PAPEL-ESTUDANTE','PAPEL-PESSOA-APOIADA'].includes(person.papel_id)).length > 1)
    payload.participations = preservedPeople;
  const hasNote = question.participant_id && typeof note === 'string' && note.trim();
  if (!hasNote && (value === null || value === undefined || value === '' || value === 'unknown')) return payload;
  if (['active_situation_id','digital_use','functional_observation','observation_scope'].includes(question.field)) return payload;
  if (question.field === 'requester_relation') { payload.requester_relation = value; return payload; }
  if (question.type === 'text' && !question.participant_id) { payload[question.field] = String(value).trim(); return payload; }
  const chosen = (Array.isArray(value) ? value : [value]).filter(id => question.options.some(item => item.id === id));
  if (question.participant_id) {
    const rows = copy(question.existingParticipations || participants(current));
    const person = rows.find(row => row.id === question.participant_id);
    const personalField = question.answer_field || {caracteristicas_pessoa:'caracteristica_ids',
      modalidades_disponiveis:'modalidade_ids', recursos_disponiveis:'recurso_operado_ids'}[question.field];
    if (person && personalField) person[personalField] = question.type === 'text' ? String(value || '').trim() : uniq([...(person[personalField] || []), ...chosen]);
    if (person && hasNote) person.apoios_informados = uniq([person.apoios_informados, note.trim()].filter(Boolean)).join('\n');
    payload.participations = rows;
  } else if (question.field === 'barreira_ou_necessidade') {
    for (const field of ['barreiras', 'necessidades']) payload[field] = uniq([...(payload[field] || []),
      ...chosen.filter(id => question.options.some(item => item.id === id && item.field === field))]);
  } else if (question.field === 'participantes') {
    const rows = copy(question.existingParticipations || current.participations || []);
    for (const role of chosen) if (!rows.some(row => row.papel_id === role)) rows.push({papel_id: role,
      caracteristica_ids: [], tarefa_ids: [], modalidade_ids: [], recurso_operado_ids: [], objetivo_participacao: ''});
    payload.participations = rows;
  } else {
    payload[question.field] = question.field === 'tarefas' && question.type === 'single' ? chosen :
      uniq([...(payload[question.field] || []), ...chosen]);
    if (question.field === 'recursos_disponiveis') {
      for (const field of ['recursos_impedidos', 'recursos_propostos']) payload[field] = (payload[field] || []).filter(id => !chosen.includes(id));
    }
  }
  return payload;
}
export function legacySummary(current) {
  const c = current.context || {};
  const people = c.participantes || [];
  const personName = person => participantName(person, person.papel);
  const rows = [
    ['Situações identificadas', (c.situations || []).map(s=>s.label+(s.id===c.active_situation_id?' — priorizada':''))],
    ['Sua participação', requesterOptions.find(item => item.id === c.requester_relation && item.id !== 'unspecified')?.label],
    ['Pessoas', people.map(personName)],
    ['Sobre a pessoa', c.caracteristicas_relevantes], ['Atividade', c.tarefas], ['Objetivo', c.objetivo],
    ['Dificuldade', c.barreiras], ['Apoio necessário', c.necessidades], ['Onde acontece', c.ambientes],
    ['Formas de interação', c.modalidades_disponiveis], ['Aplicativo ou conteúdo', c.recursos_digitais],
    ['Recursos disponíveis', c.recursos_disponiveis], ['Recursos impedidos', c.recursos_impedidos],
  ];
  for (const person of people) {
    const asLabels = values => (values || []).map(value => typeof value === 'object' ? value.label || value.titulo || value.id : value).filter(Boolean);
    const details = [asLabels(person.caracteristicas), asLabels(person.modalidades), asLabels(person.recursos_operados),
      person.observacoes || '', person.apoios_informados || ''].flat().filter(Boolean);
    if (details.length) rows.push(['Sobre '+personName(person), details]);
  }
  return rows.map(([label, value]) => ({label, value: Array.isArray(value) ? value.join('; ') : value || ''})).filter(row => row.value);
}

export const requesterOptions = [
  {id:'self',label:'Quero apoio para uma atividade que eu realizo'},
  {id:'support',label:'Acompanho ou apoio outra pessoa na atividade'},
  {id:'prepare',label:'Preparo ou adapto o material ou recurso'},
  {id:'seek_guidance',label:'Quero orientar quem conduz ou prepara a atividade'},
  {id:'unspecified',label:'Ainda não sei ou prefiro não informar'},
];

// This editor changes the existing context; it does not interpret a second
// narrative or merge unchecked options back into the previous selection.
export function reviewContext(current, response) {
  const updated=copy(current), c=updated.context || {};
  const rows=c.situated_facts ||= [];
  const key=row=>[row.participant_id || '',row.situation_id || '',row.fact_id || row.id].join('|');
  const known=new Set(rows.map(key));
  for(const row of [...(response?.facts_to_confirm || []),...(response?.resources_to_confirm || [])]) {
    // Preparation and post-production checks are not questions about resources
    // that already exist. Only actual contextual gaps become editable fields.
    if(['production','verification'].includes(row.phase) || known.has(key(row)))continue;
    rows.push({participant_id:row.participant_id,situation_id:row.situation_id,
      fact_id:row.fact_id || row.id,label:row.label,value:null,source_text:''});
    known.add(key(row));
  }
  return updated;
}
export function legacyEditor(current, catalog) {
  const c=current.context || {}, raw=c.raw || {};
  const rows=[{key:'requester_relation',field:'requester_relation',label:'Como você participa deste desafio?',type:'single',
    options:requesterOptions,value:c.requester_relation || 'unspecified',group:'Pessoas e participação'},
    {key:'objetivo',field:'objetivo',label:'O que você espera que as pessoas consigam fazer?',type:'text',value:c.objetivo || '',group:'Atividade e objetivo'},
    {key:'operacao_do_recurso',field:'operacao_do_recurso',label:'Quem utiliza ou prepara o recurso nesta atividade?',type:'text',value:c.operacao_do_recurso || '',group:'Pessoas e participação'},
    {key:'restricoes',field:'restricoes',label:'Outras condições ou restrições (uma por linha)',type:'text',value:(c.restricoes || []).join('\n'),group:'Recursos e condições'}];
  if(c.situations?.length>1)rows.push({key:'active_situation_id',field:'active_situation_id',type:'single',label:'Situação que deseja priorizar',
    options:[{id:'',label:'Ainda não escolhida'},...c.situations.map(s=>({id:s.id,label:s.label}))],value:c.active_situation_id || '',group:'Atividade e objetivo'});
  for(const fact of c.situated_facts || []) {
    const person=participants(current,catalog).find(p=>p.id===fact.participant_id);
    const situation=(c.situations || []).find(s=>s.id===fact.situation_id);
    rows.push({key:['fact',fact.participant_id,fact.situation_id,fact.fact_id].join(':'),field:'situated_fact',fact,
      label:fact.label || fact.fact_id,type:'single',value:fact.value===true?'true':fact.value===false?'false':'unknown',
      options:[{id:'true',label:'Sim'},{id:'false',label:'Não'},{id:'unknown',label:'Ainda não sei'}],
      group:[participantName(person)||'Condição informada',situation?.label].filter(Boolean).join(' · ')});
  }
  for(const assertion of c.assertions || []) {
    if(assertion.state==='RETIRADO_POR_CORRECAO')continue;
    const person=participants(current,catalog).find(p=>p.id===assertion.subject_id);
    const situation=(c.situations || []).find(s=>s.id===assertion.situation_id);
    const group=[participantName(person) || 'Informação do relato',situation?.label].filter(Boolean).join(' · ');
    rows.push({key:'assertion-remove:'+assertion.id,assertion_id:assertion.id,type:'remove',label:'Retirar “'+(assertion.source_text || String(assertion.value))+'”',value:false,group});
    if(typeof assertion.value==='string' && !/^[A-Z]+-/.test(assertion.value))rows.push({key:'assertion:'+assertion.id,assertion_id:assertion.id,field:'assertion',type:'text',
      label:'Informação registrada',value:assertion.value,group});
  }
  const labels={tarefas:'Atividade',ambientes:'Onde acontece',recursos_digitais:'Aplicativo ou material envolvido',
    recursos_disponiveis:'Equipamentos e apoios disponíveis',modalidades_disponiveis:'Formas de interação disponíveis',
    barreiras:'Dificuldades observadas',necessidades:'Apoio necessário',caracteristicas_pessoa:'Características informadas sem pessoa identificada'};
  for(const [field,[type]] of Object.entries(fields)) rows.push({key:field,field,label:labels[field],type:'multi',
    value:copy(raw[field] || []),options:options(catalog,type,raw[field] || []),
    group:field==='tarefas'?'Atividade e objetivo':['barreiras','necessidades','caracteristicas_pessoa'].includes(field)?'Dificuldades e apoio':'Recursos e condições'});
  rows.push({key:'recursos_impedidos',field:'recursos_impedidos',label:'Recursos que não podem ser usados',type:'multi',
    value:copy(raw.recursos_impedidos || []),options:options(catalog,'RECURSO_DISPONIVEL',raw.recursos_impedidos || []),group:'Recursos e condições'});
  rows.push({key:'recursos_propostos',field:'recursos_propostos',label:'Recursos que ainda poderão ser preparados',type:'multi',
    value:copy(raw.recursos_propostos || []),options:options(catalog,'RECURSO_DISPONIVEL',raw.recursos_propostos || []),group:'Recursos e condições'});
  for(const person of participants(current,catalog)) {
    const group=participantName(person) || 'Pessoa participante';
    rows.push({key:'remove:'+person.id,participant_id:person.id,field:'remove',type:'remove',label:'Remover esta pessoa ou grupo do caso',value:false,group});
    rows.push({key:'person:'+person.id+':label',participant_id:person.id,field:'label',type:'text',label:'Como identificar esta pessoa ou grupo',value:person.label || '',group});
    rows.push({key:'person:'+person.id+':papel_id',participant_id:person.id,field:'papel_id',type:'single',label:'Papel nesta atividade',
      value:person.papel_id || '',options:[{id:'',label:'Papel ainda não informado'},...options(catalog,'PAPEL_NO_CONTEXTO',[person.papel_id])],group});
    for(const [field,type,label] of [['caracteristica_ids','CARACTERISTICA_PESSOA','Características desta pessoa ou grupo'],
      ['modalidade_ids','MODALIDADE','Formas de interação que já utiliza'],['recurso_operado_ids','RECURSO_DISPONIVEL','Recursos que já consegue operar']])
      rows.push({key:'person:'+person.id+':'+field,participant_id:person.id,field,type:'multi',label,value:copy(person[field] || []),options:options(catalog,type,person[field] || []),group});
    rows.push({key:'person:'+person.id+':apoios_informados',participant_id:person.id,field:'apoios_informados',type:'text',label:'Outro apoio informado (opcional)',value:person.apoios_informados || '',group});
  }
  return rows;
}
export function legacyRevision(current,catalog,values) {
  const c=current.context || {}, payload={...copy(c.raw || {}),objetivo:c.objetivo || '',descricao_do_contexto:c.texto_curto || '',
    restricoes:copy(c.restricoes || []),operacao_do_recurso:c.operacao_do_recurso || '',impedimentos_verificados:c.impedimentos_verificados===true,
    requester_relation:c.requester_relation || 'unspecified',requester_participation_id:c.requester_participation_id || '',
    participations:participants(current,catalog),mapping_confirmed:false,transfer_confirmed:false};
  for(const row of legacyEditor(current,catalog)) if(Object.hasOwn(values,row.key)) {
    if(row.type==='remove')continue;
    let value=values[row.key];
    if(row.field==='situated_fact') {
      (payload.situated_facts ||= []).push({...row.fact,value:value==='true'?true:value==='false'?false:null,
        source_text:row.label+' — '+(value==='true'?'Sim':value==='false'?'Não':'Ainda não sei')});
      continue;
    }
    if(row.assertion_id) {
      if(String(value)!==row.value) (payload.assertion_changes ||= []).push({op:'replace',id:row.assertion_id,assertion:{value:String(value),source_text:String(value)}});
      continue;
    }
    if(row.type==='multi') value=uniq((Array.isArray(value)?value:[]).filter(id=>row.options.some(option=>option.id===id)));
    else value=String(value ?? '');
    if(row.field==='restricoes')value=value.split('\n').map(item=>item.trim()).filter(Boolean);
    if(row.type==='single'&&!row.options.some(option=>option.id===value)) continue;
    const target=row.participant_id?payload.participations.find(person=>person.id===row.participant_id):payload;
    if(target) target[row.field]=value;
  }
  payload.participations=payload.participations.filter(person=>values['remove:'+person.id]!==true);
  for(const assertion of c.assertions || [])if(values['assertion-remove:'+assertion.id]===true)
    (payload.assertion_changes ||= []).push({op:'remove',id:assertion.id});
  if(payload.requester_participation_id&&!payload.participations.some(person=>person.id===payload.requester_participation_id))payload.requester_participation_id='';
  // A resource cannot be simultaneously marked available and forbidden.
  const available=payload.recursos_disponiveis || [],blocked=payload.recursos_impedidos || [],proposed=payload.recursos_propostos || [];
  if(available.some(id=>blocked.includes(id)||proposed.includes(id))||blocked.some(id=>proposed.includes(id)))
    throw new Error('Um recurso está em mais de um estado: disponível, impedido ou ainda a preparar. Revise essas seleções antes de salvar.');
  return payload;
}

export function compositionEditor(context,catalog) {
  const rows=[{key:'task',field:'task',type:'single',label:'Atividade',value:context.task || '',
    options:[{id:'',label:'Ainda não informada'},...(catalog.tasks || []).map(item=>({id:item.id,label:item.label}))],group:'Atividade e objetivo'}];
  const add=(target,person=null)=>{
    for(const field of ['facts','resources']) for(const item of catalog[field] || []) {
      if(person&&field==='facts'&&item.scope==='context')continue;
      if(!person&&context.participants?.length&&field==='facts'&&item.scope!=='context')continue;
      rows.push({key:(person?person.id+':':'')+field+':'+item.id,field,concept_id:item.id,participant_id:person?.id,
        type:'single',label:simpleQuestions[item.id] || item.label,value:target[field]?.[item.id]===true?'true':target[field]?.[item.id]===false?'false':'unknown',
        options:[{id:'true',label:'Sim'},{id:'false',label:'Não'},{id:'unknown',label:'Ainda não sei'}],
        group:person?.label || (field==='resources'?'Recursos e condições':'Condições da atividade')});
    }
  };
  add(context);for(const person of context.participants || [])add(person,person);
  return rows;
}
export function compositionRevision(context,catalog,values) {
  const updated=copy(context);updated.confirmed=false;
  for(const row of compositionEditor(context,catalog)) if(Object.hasOwn(values,row.key)) {
    if(row.field==='task'){if(row.options.some(item=>item.id===values[row.key]))updated.task=values[row.key];continue;}
    const target=row.participant_id?updated.participants.find(person=>person.id===row.participant_id):updated;
    target[row.field] ||= {};target[row.field][row.concept_id]=values[row.key]==='unknown'?null:values[row.key]==='true';
  }
  return updated;
}

// Project only origins attached to an application used by this result. Source
// titles or the complete catalogue alone do not prove that a source was used.
export function usedSourceRecords(response) {
  const records=[],entities=response.execution_evidence?.entities || {};
  for(const config of response.explanation?.configurations || [])for(const support of config.application?.supports || [])
    for(const origin of support.origins || []) {
      const source=entities[origin.fonte_id] || {};
      records.push({id:origin.id,sourceId:origin.fonte_id,title:source.title || source.titulo || source.label || origin.fonte_item || origin.fonte_id,
        url:origin.document_url || source.url || '',location:origin.localizacao_publica || origin.localizacao || origin.secao || origin.pagina || '',
        statement:origin.document_paraphrase || origin.resumo_publico || origin.enunciado_publico || origin.aviso_publicacao || '',
        status:origin.status_localizacao || 'PENDENTE',componentId:config.component_id,criterionId:support.criterion_id,
        applicationState:config.selection==='CONDITIONAL'||config.availability_status==='CONDICIONAL_A_CONFIRMACAO'?'conditional':'selected'});
    }
  const collect=local=>{
    const choices=[...(local.choices || []).map(choice=>({choice,state:'selected'})),
      ...(local.pending_candidates || []).map(choice=>({choice,state:'conditional'})),...(local.partial_segments || []).map(choice=>({choice,state:'partial'}))];
    for(const {choice,state} of choices) {
      const grounds=[...(choice.steps || []).flatMap(step=>step.groundings || []),...(choice.relations || []).flatMap(row=>row.groundings || (row.grounding?[row.grounding]:[]))];
      for(const grounding of grounds) {
        const criterion=grounding.criterion || {};
        const contributions=grounding.contributions || grounding.construction?.contributions || grounding.articulation?.contributions || [];
        for(const row of [...contributions,...(grounding.sources || []),...(criterion.source?[{source:criterion.source,locator:criterion.locator,statement:criterion.justification,status:criterion.status}]:[])]) {
          const source=row.source || row;
          records.push({id:row.id || row.excerpt_id || grounding.id,sourceId:source.id,title:source.label || source.title || source.id || '',
            url:row.document_url || source.url || '',location:row.locator || row.excerpt?.locator || source.locator || '',statement:row.statement || row.support_scope || '',status:row.review_status || row.status || source.review_status || 'PENDENTE',componentId:choice.id,criterionId:criterion.id,applicationState:state});
        }
      }
    }
  };
  collect(response);for(const person of response.participant_results || [])if(person.result)collect(person.result);
  const unique=new Map();for(const row of records){const key=[row.id,row.sourceId,row.componentId,row.criterionId].join('|');if(!unique.has(key))unique.set(key,row);}
  return [...unique.values()];
}
export function accessRequirementSummary(current) {
  return (current.context?.access_requirements || []).map(row => ({
    participant: row.participant_label || 'Relato sem atribuição a uma pessoa',
    requirements: uniq(row.requirement_labels || []),
    description: row.description || '', matchedText: row.matched_text || '',
    conditions: row.conditions || '', limit: row.limit || '',
    needsConfirmation: row.status === 'CONFLITO_A_CONFIRMAR',
    sourceIds: row.source_ids || [], excerptIds: row.excerpt_ids || [], matrixId: row.matrix_id || '',
  }));
}
export function detectCompositionTask(narrative) {
  const text = norm(narrative).replace(/\bnao (?:vai|precisa|quer|deve) (?:escrever|redigir|digitar|revisar|conferir|corrigir)\b/g, '');
  // The legacy intake separates participants. Never collapse different groups
  // into one global ability just because the writing task is recognized.
  if (/\b(turma|estudantes|alunos|alunas|pessoas)\b/.test(text) ||
      (text.match(/\b(?:um|uma|dois|duas|[2-9]) (?:estudante|aluno|aluna|pessoa)\b/g) || []).length > 1) return null;
  if (/\b(fora (?:do contexto|da atividade) (?:escolar|de aprendizagem)|nao (?:e|ocorre em) (?:uma )?atividade (?:escolar|de aprendizagem))\b/.test(text)) return null;
  if (!/\b(aluno|aluna|estudante|aula|aprendizagem|escolar|curso|professor|professora)\b/.test(text)) return null;
  if (/\b(revisar|conferir|corrigir)\b.{0,40}\b(texto|rascunho)\b.{0,30}\b(ja (?:existe|disponivel|pronto|escrito)|existente)\b/.test(text) ||
      /\b(texto|rascunho)\b.{0,25}\b(ja (?:existe|disponivel|pronto|escrito)|existente)\b.{0,40}\b(revisar|conferir|corrigir)\b/.test(text)) return 'TaskReviewExistingText';
  if (/\b(escrever|redigir|digitar|produzir um texto)\b/.test(text) && /\b(revisar|conferir|corrigir)\b/.test(text) &&
      /\b(texto|rascunho|mensagem|resposta|contribuicao)\b/.test(text)) return 'TaskCreateReviewedText';
  return null;
}
// Only explicit statements about a fact are recognized. An isolated noun, a
// disability label, or the synthetic example never supplies an affirmative fact.
const cues = [
  ['resources', 'Keyboard', /\b(teclado (?:esta )?disponivel|tem (?:um )?teclado|(?:usa|utiliza) (?:um )?(?:computador e )?teclado)\b/, /\b(sem teclado|teclado indisponivel|nao (?:tem|ha|usa|utiliza) (?:um )?teclado)\b/],
  ['resources', 'EditableText', /\b(campo (?:de )?texto editavel|editor de texto disponivel|rascunho editavel disponivel)\b/, /\b(sem editor de texto|nao ha campo editavel)\b/],
  ['resources', 'Display', /\b(tela legivel disponivel|apresentacao visual legivel)\b/, /\b(sem tela|tela indisponivel)\b/],
  ['resources', 'Microphone', /\b(microfone (?:esta )?disponivel|tem (?:um )?microfone)\b/, /\b(sem microfone|microfone indisponivel|nao (?:tem|ha) microfone)\b/],
  ['resources', 'SpeechRecognition', /\b(reconhecimento de fala disponivel|ditado disponivel)\b/, /\b(sem reconhecimento de fala|ditado indisponivel)\b/],
  ['resources', 'TextToSpeech', /\b(leitura em voz disponivel|sintese de fala disponivel)\b/, /\b(sem leitura em voz|sintese de fala indisponivel)\b/],
  ['resources', 'AudioOutput', /\b(saida de audio disponivel|fone disponivel|fones disponiveis)\b/, /\b(sem saida de audio|sem fones|saida de audio indisponivel)\b/],
  ['facts', 'ContentAvailable', /\b(tem (?:o |um )?conteudo|conteudo disponivel|texto ja escrito|rascunho ja pronto)\b/, /\b(sem conteudo|conteudo indisponivel)\b/],
  ['facts', 'CanUseKeyboard', /\b(consegue (?:usar|operar) (?:o )?teclado|pode usar o teclado)\b/, /\b(nao consegue (?:usar|operar) (?:o )?teclado|nao pode usar o teclado)\b/],
  ['facts', 'CanUseSpeech', /\b(consegue e aceita (?:falar|usar a fala)|pode e aceita usar a fala)\b/, /\b(nao pode falar|nao consegue falar|nao aceita usar a fala)\b/],
  ['facts', 'CanReviewVisualText', /\b(consegue (?:ler|conferir) (?:o )?texto (?:na tela|visualmente))\b/, /\b(nao consegue (?:ler|conferir) (?:o )?texto (?:na tela|visualmente))\b/],
  ['facts', 'CanReviewSpeech', /\b(consegue conferir (?:o )?(?:conteudo|texto) (?:pela leitura em voz|ouvindo))\b/, /\b(nao pode ouvir|nao consegue ouvir|nao consegue conferir (?:o )?(?:conteudo|texto) ouvindo)\b/],
  ['facts', 'CanControlPlayback', /\b(consegue pausar e repetir (?:a )?leitura)\b/, /\b(nao consegue pausar|nao consegue repetir a leitura)\b/],
  ['facts', 'CanCorrect', /\b(consegue corrigir (?:o )?(?:rascunho|texto)|pode corrigir o texto)\b/, /\b(nao consegue corrigir (?:o )?(?:rascunho|texto)|nao pode corrigir o texto)\b/],
  ['facts', 'ControlsCompletion', /\b(controla quando (?:concluir|enviar)|decide quando (?:concluir|enviar))\b/, /\b(nao controla quando (?:concluir|enviar)|envio automatico)\b/],
  ['facts', 'CanVerifyMeaning', /\b(consegue verificar o significado|consegue confirmar o sentido do texto)\b/, /\b(nao consegue verificar o significado|nao consegue confirmar o sentido do texto)\b/],
];
export function compositionDraft(narrative, catalog) {
  const text = norm(narrative), task = detectCompositionTask(narrative), evidence = [];
  const result = {task, facts: Object.fromEntries((catalog.facts || []).map(item => [item.id, null])),
    resources: Object.fromEntries((catalog.resources || []).map(item => [item.id, null])), evidence};
  for (const [group, id, yes, no] of cues) {
    if (!(id in result[group])) continue;
    const negative = text.match(no), positive = text.match(yes);
    // A negative can contain the positive phrase. Remove it before checking
    // for a second, contradictory affirmation; mixed statements remain unknown.
    const independentPositive = negative && text.replace(no, '').match(yes);
    if (negative && independentPositive) continue;
    const match = negative || positive;
    if (match) { result[group][id] = !negative; evidence.push({group, id, value: !negative, matched_text: match[0]}); }
  }
  if (task && 'LearningCommunicationContext' in result.facts) {
    result.facts.LearningCommunicationContext = true;
    evidence.push({group: 'facts', id: 'LearningCommunicationContext', value: true,
      matched_text: text.match(/\b(aluno|aluna|estudante|aula|aprendizagem|escolar|curso|professor|professora)\b/)[0]});
  }
  return result;
}
const simpleQuestions = {
  Keyboard:'Há um teclado disponível, físico ou virtual?', EditableText:'É possível editar o texto no aplicativo?',
  Display:'Há uma apresentação do texto legível na tela?', Microphone:'Há um microfone disponível?',
  SpeechRecognition:'Há ditado que transforma a fala em texto?', TextToSpeech:'O aplicativo pode ler o texto em voz alta?',
  AudioOutput:'Há como ouvir a leitura do texto?', ContentAvailable:'Já há conteúdo para escrever ou revisar?',
  CanUseKeyboard:'A pessoa consegue escrever usando esse teclado?',
  KeyboardCompatible:'O teclado funciona no dispositivo e no aplicativo?',
  KeyboardEffortAcceptable:'É viável escrever assim sem esforço excessivo?',
  KeyboardFeedbackPerceptible:'A pessoa consegue conferir o que está digitando?',
  CanUseSpeech:'A pessoa consegue e quer usar a fala nesta atividade?',
  SpeechCompatible:'O ditado funciona neste dispositivo?', SpeechEffortAcceptable:'É viável usar a fala sem esforço excessivo?',
  SpeechFeedbackPerceptible:'A pessoa consegue conferir o texto transcrito?',
  SpeechInputUsable:'O ditado consegue entender a fala neste ambiente?',
  CanReviewVisualText:'A pessoa consegue ler e conferir o texto na tela?',
  CanReviewSpeech:'A pessoa consegue conferir o conteúdo ouvindo a leitura?',
  AudioUsable:'É possível ouvir com clareza e privacidade aqui?',
  CanControlPlayback:'A pessoa consegue pausar e repetir a leitura?',
  CanCorrect:'A pessoa consegue corrigir o texto quando necessário?',
  ControlsCompletion:'A pessoa decide quando concluir, sem envio automático?',
  CanVerifyMeaning:'A apresentação permite conferir se o texto expressa o que a pessoa queria dizer?',
};
export function compositionQuestions(context, catalog) {
  if (context.participants?.length) {
    const shared = Object.fromEntries((catalog.facts || []).filter(item => item.scope === 'context')
      .map(item => [item.id, context.facts?.[item.id] ?? null]));
    return context.participants.flatMap(person => compositionQuestions({task:context.task,
      facts:{...shared,...person.facts},resources:{...context.resources,...person.resources}},catalog)
      .map(question => ({...question,id:question.id+':'+person.id,participant_id:person.id,participant_label:person.label})));
  }
  const task = (catalog.tasks || []).find(item => item.id === context.task);
  if (!task) return [];
  const requiredFunctions = new Set((task.required_functions || []).map(item => typeof item === 'string' ? item : item.id));
  const possible = (catalog.capabilities || []).filter(item => item.authorized !== false && requiredFunctions.has(item.function_id) &&
    !(item.required_resources || []).some(id => context.resources?.[id] === false) &&
    !(item.required_facts || []).some(id => context.facts?.[id] === false));
  // Ask for one viable route per required function, not the union of every
  // alternative. A rejected condition causes the next route to be considered.
  // This changes the conversation, not authorization or the decision rules.
  const unknownCount = item => (item.required_resources || []).filter(id => context.resources?.[id] == null).length +
    (item.required_facts || []).filter(id => context.facts?.[id] == null).length;
  const selected = [...requiredFunctions].map(functionId => possible.filter(item => item.function_id === functionId)
    .sort((a,b) => unknownCount(a)-unknownCount(b) || a.id.localeCompare(b.id))[0]).filter(Boolean);
  const needed = new Set();
  for (const capability of selected) {
    for (const id of capability.required_resources || []) if (context.resources?.[id] == null) needed.add('resources:' + id);
    for (const id of capability.required_facts || []) if (context.facts?.[id] == null) needed.add('facts:' + id);
  }
  if (requiredFunctions.size > 1 && [...requiredFunctions].every(id => selected.some(item => item.function_id === id))) {
    for (const relation of catalog.relations || []) if (requiredFunctions.has(relation.from_function) && requiredFunctions.has(relation.to_function)) {
      for (const id of relation.required_facts || []) if (context.facts?.[id] == null) needed.add('facts:' + id);
    }
  }
  return [...needed].map(key => {
    const [field, id] = key.split(':');
    const row = (catalog[field] || []).find(item => item.id === id);
    return {id: key, field, concept_id: id, label: simpleQuestions[id] || row?.label || id, type: 'single',
      options: [{id: 'true', label: 'Sim'}, {id: 'false', label: 'Não'}, {id: 'unknown', label: 'Não sei'}]};
  });
}
export function compositionSummary(context, catalog) {
  const task = (catalog.tasks || []).find(item => item.id === context.task);
  const rows = task ? [{label: 'Atividade', value: task.label}] : [];
  for (const field of ['facts', 'resources']) {
    const relevant = (catalog[field] || []).filter(item => !context.participants?.length || field !== 'facts' || item.scope === 'context');
    const confirmed = relevant.filter(item => context[field]?.[item.id] === true).map(item => item.label);
    const blocked = relevant.filter(item => context[field]?.[item.id] === false).map(item => item.label);
    if (confirmed.length) rows.push({label: field === 'facts' ? 'Condições informadas' : 'Recursos disponíveis', value: confirmed.join('; ')});
    if (blocked.length) rows.push({label: field === 'facts' ? 'Condições que não se aplicam' : 'Recursos indisponíveis', value: blocked.join('; ')});
  }
  for (const person of context.participants || []) {
    const descriptions = [person.label,...(person.traits || [])];
    for (const field of ['facts','resources']) descriptions.push(...(catalog[field] || [])
      .filter(item => person[field]?.[item.id] === true).map(item => item.label));
    rows.push({label:'Participante',value:descriptions.filter(Boolean).join('; ')});
  }
  return rows;
}
