// One presentation contract for the prepared example and both AMADO views.
// This module displays recorded evidence. It never selects or creates knowledge.
const escape = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const array = value => Array.isArray(value) ? value : value == null ? [] : [value];
const text = value => value == null ? '' : typeof value === 'object'
  ? value.label || value.title || value.titulo || value.enunciado || value.statement || value.text || value.message || ''
  : String(value);
const list = (items, empty = 'Não detalhado neste registro.') => {
  const values = array(items).map(text).filter(Boolean);
  return values.length ? `<ul>${values.map(value => `<li>${escape(value)}</li>`).join('')}</ul>` : `<p class="explanation-gap">${escape(empty)}</p>`;
};
const field = (label, value, empty) => `<div class="explanation-field"><strong>${escape(label)}</strong>${list(value, empty)}</div>`;
const labels = {
  DISPONIVEL_CONFIRMADO:'Disponível', CONFIRMADO_DISPONIVEL:'Recurso confirmado', NAO_CONFIRMADO:'A confirmar', PROPOSTO_A_PREPARAR:'Proposto, ainda a preparar', REQUER_PREPARACAO:'Requer preparação', IMPEDIDO:'Não pode ser usado',
  PASS:'Condição atendida', FAIL:'Condição não atendida', PENDING:'A confirmar', NOT_EXECUTED:'Não verificado pelo motor',
  SELECTED:'Selecionada', CONDITIONAL:'Condicional', REJECTED:'Não utilizada', NOT_EVALUATED:'Não avaliada',
  CONFERIDA_NO_DOCUMENTO:'Conferida no documento', CONFERIDA_NO_REGISTRO:'Conferida no registro da base', PENDENTE:'Pendente de conferência',
  DOCUMENTADA_DIRETAMENTE:'Documentada diretamente', RECONSTRUIDA_A_PARTIR_DAS_PUBLICACOES:'Reconstruída a partir das publicações',
  DOCUMENTADA_E_RECONSTRUIDA:'Documentada e reconstruída', INFORMADA_PELA_AUTORA:'Informada pela autora',
  DOCUMENTADA_E_INFORMADA_PELA_AUTORA:'Documentada e informada pela autora', NAO_CONFIRMADA:'Não confirmada',
  COMPLEMENTA:'Complementação', CORROBORA:'Corroboração', REFINA:'Refinamento', CONDICIONA:'Condição', LIMITA:'Limite', CONTRASTA:'Contraste',
  OPERACIONALIZA:'Operacionalização', COMPLEMENTA_E_OPERACIONALIZA:'Complementação e operacionalização',
  COMPLEMENTA_E_CONDICIONA:'Complementação e condição', REFINA_E_OPERACIONALIZA:'Refinamento e operacionalização',
  SINTETIZA_EM_PERSONA:'Síntese em persona', REUTILIZA_EM_ESTUDO_POSTERIOR:'Reutilização em estudo posterior',
  CONTEXTUALIZA_E_REUTILIZA:'Contextualização e reutilização',
};
const human = value => labels[value] || text(value).replaceAll('_', ' ').toLocaleLowerCase('pt-BR');
const documentaryText = value => typeof value === 'object' && value
  ? [text(value),value.interpretation,value.limit,...array(value.pending_foundation_items),...array(value.limitations)].filter(Boolean).join(' ')
  : text(value);
const documentarySupport = row => {
  const support = row.documentary_support || (row.foundation_review_status ? {status:row.foundation_review_status,pending:row.pending_foundation_items} : null);
  if (!support && !row.limits?.length) return '';
  const values = support && typeof support === 'object'
    ? [support.status ? human(support.status) : '', text(support), support.justification, ...array(support.supported), ...array(support.pending), ...array(support.limitations)]
    : [support ? human(support) : ''];
  return `${support ? field('Alcance do apoio documental', values) : ''}${row.limits?.length ? field('Limites do registro', row.limits) : ''}`;
};
const technical = values => {
  const ids = array(values).flat().filter(Boolean);
  return ids.length ? `<details class="explanation-identifiers"><summary>Identificadores para conferência</summary><p>${ids.map(id => `<code>${escape(id)}</code>`).join(' · ')}</p></details>` : '';
};
const graphCleanups = new WeakMap();
let graphPresentationNumber = 0;

// Pure projection: no selection, inferred needs, ranking, or new knowledge.
// The references remain available so every sentence can be checked against the return.
export function projectConfiguration(result, config) {
  const evidence = result?.execution_evidence || {};
  const application = config?.application || {};
  const byCheck = new Map(array(evidence.checks).map(row => [row.id, row]));
  const recordedChecks = array(application.check_ids).map(id => byCheck.get(id)).filter(Boolean);
  const checked = recordedChecks.length ? recordedChecks : array(application.checks);
  const supports = array(application.supports);
  const knowledgeIds = new Set(supports.flatMap(row => array(row.knowledge_ids)));
  for (const row of array(config.construction?.knowledge)) if (row.id) knowledgeIds.add(row.id);
  const witnesses = Array.isArray(evidence.retrieval)
    ? evidence.retrieval.filter(row => knowledgeIds.has(row.knowledge_id) && row.authorization !== 'EXCLUIDO')
    : array(application.retrieval_witnesses);
  const grouped = new Map();
  for (const row of witnesses) {
    const key = JSON.stringify([row.knowledge_id, row.input_knowledge_id, row.articulation_id, row.match_predicate]);
    if (!grouped.has(key)) grouped.set(key, {knowledge_id:row.knowledge_id, input_knowledge_id:row.input_knowledge_id,
      articulation_id:row.articulation_id, match_predicate:row.match_predicate, concept_ids:[], required_function_ids:[], authorizations:[],
      task_paths:[], witness_ids:[], check_ids:[]});
    const group = grouped.get(key);
    for (const [field, value] of [['concept_ids',row.context_concept_id],['required_function_ids',row.required_function_id],['witness_ids',row.id],['authorizations',row.authorization]]) {
      if (value && !group[field].includes(value)) group[field].push(value);
    }
    const path = array(row.task_path);
    if (path.length && !group.task_paths.some(old => JSON.stringify(old) === JSON.stringify(path))) group.task_paths.push(path);
    for (const id of array(row.check_ids)) if (!group.check_ids.includes(id)) group.check_ids.push(id);
  }
  const construction = {mobilized:[], historical:[], unconfirmed:[]};
  for (const row of array(config.construction?.articulations)) {
    const blocked = ['NAO_CONFIRMADA','BLOQUEADA'].includes(row.nivel_confirmacao) || row.habilitada_para_decisao === false;
    construction[blocked ? 'unconfirmed' : row.mobilized_in_execution === true ? 'mobilized' : 'historical'].push(row);
  }
  const comparison = result?.articulation_comparison;
  const isolated = comparison?.isolated?.component_ids;
  const articulated = comparison?.articulated?.component_ids;
  const delta = array(comparison?.evidence_delta).find(row => row.component_id === config.component_id);
  let kind = 'NOT_EXECUTED';
  if (Array.isArray(isolated) && Array.isArray(articulated) && articulated.includes(config.component_id)) {
    kind = !isolated.includes(config.component_id) ? 'NEW_CHOICE'
      : array(delta?.added_support_pairs).length ? 'EXPANDED_FOUNDATION' : 'UNCHANGED';
  }
  return {
    componentId:config.component_id, matches:array(application.context_conditions), checks:checked,
    retrievalGroups:[...grouped.values()], supports, construction,
    effect:{kind, addedSupportPairs:array(delta?.added_support_pairs)},
    foundationIncomplete:array(config.construction?.knowledge).filter(row => ['PARCIAL','PENDENTE'].includes(row.foundation_review_status)),
  };
}

function contribution(row) {
  const statement = row.statement || row.contribution;
  const source = row.source || {};
  const excerpt = row.excerpt || {};
  const location = excerpt.location || row.location;
  return `<li class="explanation-contribution">${field('Contribuição registrada', statement, 'A contribuição individual desta fonte ainda não foi detalhada.')}${field('Fonte', text(source), 'A fonte não foi incluída neste retorno.')}${field('Localização', location, 'A localização documental não foi detalhada; o identificador não a substitui.')}${row.contribution_role ? field('Papel desta contribuição', human(row.contribution_role)) : ''}${row.nature ? field('Natureza do registro', human(row.nature)) : ''}${documentarySupport(row)}${row.justification ? field('Por que essa contribuição foi relacionada', row.justification) : ''}<p class="explanation-state"><strong>Conferência:</strong> ${escape(human(row.verification_status || 'PENDENTE'))}</p>${excerpt.publication_notice ? `<p class="explanation-note">${escape(excerpt.publication_notice)}</p>` : ''}${technical([row.id, row.articulation_id, row.knowledge_id, row.excerpt_id, source.id])}</li>`;
}

function makePresenter(result) {
  const presentationId = ++graphPresentationNumber;
  const localGraphs = new Map();
  const knowledge = new Map(array(result.traceability?.knowledge).map(row => [row.id,row]));
  const criteria = new Map(array(result.traceability?.criteria).map(row => [row.id,row]));
  const checks = new Map(array(result.execution_evidence?.checks).map(row => [row.id,row]));
  const nodes = new Map(array(result.explanation?.graph?.nodes).map(row => [row.id,row]));
  const known = new Map([...Object.entries(result.execution_evidence?.entities || {}), ...knowledge, ...criteria, ...nodes]);
  for (const row of array(result.context?.participantes)) {
    if (row.papel_id && row.papel) known.set(row.papel_id,{id:row.papel_id,title:row.papel});
  }
  for (const config of array(result.explanation?.configurations)) {
    for (const row of array(config.construction?.knowledge)) if (row.id) known.set(row.id,row);
    for (const row of array(config.construction?.articulations)) if (row.id) known.set(row.id,row);
  }
  const resolve = value => typeof value === 'string' && known.has(value) ? text(known.get(value)) : text(value);
  const refs = values => array(values).map(value => {
    const resolved = resolve(value);
    return /^[A-Z][A-Z0-9-]+$/.test(resolved) ? 'Registro sem descrição incluída neste retorno; consulte o identificador técnico.' : resolved;
  });
  const checkRows = ids => array(ids).map(id => checks.get(id)).filter(Boolean);

  function support(row) {
    const criterion = row.criterion || criteria.get(row.criterion_id || row.id) || {};
    const origins = array(row.origins);
    const originHtml = origins.length ? `<details><summary>De onde veio este cuidado</summary><ul class="explanation-records">${origins.map(origin => `<li>${field('Fonte', resolve(origin.fonte_id), 'Fonte não descrita neste retorno.')}${field('Item documental', origin.resumo_publico || origin.enunciado_publico || origin.texto || origin.item_texto || origin.aviso_publicacao, 'Texto do item não redistribuído; consulte a fonte e sua localização.')}${field('Localização', origin.localizacao_publica || origin.localizacao || origin.pagina || origin.secao, 'Localização não detalhada neste registro.')}${technical([origin.id,origin.fonte_id,origin.trecho_id])}</li>`).join('')}</ul></details>` : '<p class="explanation-gap">A origem documental deste apoio não foi detalhada neste retorno.</p>';
    return `<li class="explanation-support">${field('Cuidado que orienta esta escolha', row.criterion_statement || text(criterion) || row.criterion_label, 'O enunciado do critério não foi incluído neste retorno.')}${field('Por que se aplica aqui', row.justification || row.justificativa, 'Não há justificativa situada detalhada; a presença do critério não substitui essa explicação.')}${field('Conhecimentos que sustentam este uso', refs(row.knowledge_ids))}${originHtml}${technical([row.id,row.criterion_id,...array(row.knowledge_ids),...array(row.origin_ids)])}</li>`;
  }

  function construction(config) {
    const data = config.construction || {};
    const view = projectConfiguration(result,config);
    const relation = row => {
      const contributions = array(data.contributions).filter(item => item.articulation_id === row.id);
      const outputIds = new Set([...array(row.conhecimento_resultante_ids || row.output_knowledge_ids), ...contributions.map(item => item.knowledge_id)]);
      const outputs = array(data.knowledge).filter(item => outputIds.has(item.id));
      return `<details data-construction-articulation="${escape(row.id)}"><summary>${escape(text(row) || 'Articulação registrada')}</summary>
        <ol class="explanation-construction-sequence"><li><strong>Contribuições das fontes</strong>${contributions.length ? `<ul class="explanation-records">${contributions.map(contribution).join('')}</ul>` : '<p class="explanation-gap">As contribuições individuais não estão detalhadas neste retorno.</p>'}</li>
        <li>${field('Operação registrada',row.operation_explanation,'O procedimento não está detalhado; o nome da relação não o substitui.')}${field('Conhecimentos de partida',refs(row.conhecimento_entrada_ids || row.input_knowledge_ids))}</li>
        <li>${field('Entendimento acrescentado',row.added_understanding,'O entendimento acrescentado não foi detalhado.')}${outputs.length ? `<ul class="explanation-records">${outputs.map(item => `<li>${field('Conhecimento produzido ou refinado',text(item))}${documentarySupport(item)}${technical(item.id)}</li>`).join('')}</ul>` : ''}</li>
        <li>${field('Condição e limite', [row.condicao || row.condition,row.limite || row.limit])}${documentarySupport(row)}${row.nivel_confirmacao ? field('Estado documental',human(row.nivel_confirmacao)) : ''}</li></ol>${technical(row.id)}</details>`;
    };
    const group = (key,label,note) => view.construction[key].length ? `<section data-construction-group="${key}"><h4>${label}</h4><p class="explanation-note">${note}</p>${view.construction[key].map(relation).join('')}</section>` : '';
    return `<details class="explanation-reading" data-explanation-reading="construction"><summary>Como esse conhecimento foi construído</summary><div class="explanation-reading-body"><p class="explanation-note">As fontes foram relacionadas antes desta consulta. A síntese é um registro da pesquisa, não uma interpretação criada pelo AMADO agora.</p>
      ${group('mobilized','Articulações percorridas nesta consulta','Estas relações participaram da recuperação do conhecimento para este caso.')}
      ${group('historical','Construção anterior, não percorrida agora','Estas relações documentam a trajetória. Sua presença não significa que tenham participado da seleção desta vez.')}
      ${group('unconfirmed','Relações não confirmadas ou bloqueadas','São registros para conferência, não apoios confirmados da escolha.')}
      ${!array(data.articulations).length ? '<p class="explanation-gap">Nenhuma operação de articulação foi detalhada para esta escolha.</p>' : ''}
      <details><summary>Consultar todos os conhecimentos desta escolha</summary>${array(data.knowledge).length ? `<ul class="explanation-records">${data.knowledge.map(row => `<li>${field('Conhecimento registrado',text(row))}${row.articulacao || row.articulation ? field('Articulação registrada',row.articulacao || row.articulation) : ''}${field('Limite',row.limite || row.limit)}${documentarySupport(row)}${technical(row.id)}</li>`).join('')}</ul>` : '<p class="explanation-gap">Não há conhecimento detalhado neste retorno.</p>'}</details></div></details>`;
  }

  function application(config) {
    const data = config.application || {};
    const view = projectConfiguration(result,config);
    const functional = view.checks.filter(row => row.rule_id?.startsWith('functional_group_') || row.rule_id === 'required_field_tarefas');
    const operational = view.checks.filter(row => row.rule_id === 'required_roles' || row.rule_id?.startsWith('resource_option_group_') || row.rule_id === 'core_resources' || row.field === 'modalidades_disponiveis');
    const conditionText = row => {
      const role = row.rule_id === 'required_roles';
      const ids = role ? array(row.expected_ids) : array(row.matched_ids);
      const groupMeaning = {ANY_CLAUSE:'Este grupo pede ao menos uma correspondência, não todas.',ANY_IN_FIELD:'As opções deste campo são alternativas; basta uma correspondência.',ANY:'Ao menos uma opção deve estar disponível.',ALL:'Todos os itens exigidos neste teste são conferidos.'}[row.operator] || '';
      return `<li data-check-id="${escape(row.id)}"><strong>${escape(role ? 'Participação exigida' : human(row.outcome))}:</strong> ${escape(refs(ids).join('; ') || 'Nenhum item correspondente registrado.')}${role ? `<span> — ${escape(human(row.outcome))}.</span>` : ''}${groupMeaning ? `<p class="explanation-note">${escape(groupMeaning)}</p>` : ''}${technical([row.id])}</li>`;
    };
    const withItems = rows => rows.filter(row => array(row.expected_ids).length || array(row.matched_ids).length || array(row.clauses).length);
    const knowledgeIds = [...new Set(view.supports.flatMap(row => array(row.knowledge_ids)))];
    const addedIds = view.effect.addedSupportPairs.map(row => row.knowledge_id).filter(id => knowledgeIds.includes(id));
    const visibleKnowledgeIds = [...new Set([...addedIds,...knowledgeIds])].slice(0,2);
    const taskIds = [...new Set(functional.filter(row => row.field === 'tarefas').flatMap(row => array(row.matched_ids)))];
    const conditionIds = [...new Set(functional.filter(row => row.rule_id?.startsWith('functional_group_')).flatMap(row => array(row.matched_ids)))];
    const visibleConditions = conditionIds.slice(0,2);
    const operationalItems = withItems(operational).map(row => ({row,ids:row.rule_id === 'required_roles' ? array(row.expected_ids) : array(row.matched_ids)}));
    const retrieval = kid => {
      const groups = view.retrievalGroups.filter(row => row.knowledge_id === kid);
      return groups.length ? `<details><summary>Conferir como este conhecimento foi recuperado</summary><p class="explanation-note">As correspondências abaixo ocorreram na consulta. Elas não provam que uma característica causou a escolha, nem identificam por si só a pessoa responsável por ela.</p>${groups.map(group => `<div class="explanation-witness" data-witness-id="${escape(group.witness_ids[0] || '')}">${group.authorizations.some(state => ['CONDICIONAL','CONDITIONAL'].includes(state)) ? '<p class="explanation-gap" data-retrieval-conditional>Conhecimento com uso condicional neste caminho. A recuperação preserva condições pendentes; não equivale a autorização sem ressalvas.</p>' : ''}${field('Estado registrado da recuperação',group.authorizations.map(human))}${field('Conhecimento de entrada',refs(group.input_knowledge_id))}${group.articulation_id ? field('Articulação percorrida',refs(group.articulation_id)) : '<p>Recuperação direta, sem expansão por articulação neste caminho.</p>'}${group.concept_ids.length ? field('Condições do caso que corresponderam',refs(group.concept_ids)) : '<p>Este caminho usa um princípio geral com tarefa compatível; não registra uma característica individual correspondente.</p>'}${field('Caminho de compatibilidade entre tarefas',group.task_paths.map(path => refs(path).join(' → ')))}${group.required_function_ids.length ? field('Funções já informadas no contexto que habilitaram a articulação',refs(group.required_function_ids)) : ''}${technical([...group.witness_ids,...group.check_ids])}</div>`).join('')}</details>` : '<p class="explanation-gap">Não há testemunha de recuperação detalhada para este conhecimento no retorno.</p>';
    };
    const criteriaHtml = view.supports.length ? `<details><summary>Conferir os ${view.supports.length} critérios, conhecimentos ligados e origens</summary><ul class="explanation-records">${view.supports.map(row => `<li data-support-id="${escape(row.id)}"><ul class="explanation-records">${support(row)}</ul></li>`).join('')}</ul></details>` : '<p class="explanation-gap">Nenhum apoio situado foi detalhado.</p>';
    return `<details class="explanation-reading" data-explanation-reading="application" open><summary>Por que neste caso</summary><div class="explanation-reading-body" data-explanation-reasons>
      <ol class="explanation-reason-sequence">
        <li data-reason-step="context"><h4>O que correspondeu ao caso</h4>${taskIds.length ? field('Tarefa',refs(taskIds)) : ''}${visibleConditions.length ? list(refs(visibleConditions)) : '<p>Não há condição funcional detalhada neste grupo de testes.</p>'}${conditionIds.length ? '<p class="explanation-note">O grupo pede ao menos uma correspondência, não todas.</p>' : ''}${withItems(functional).length ? `<details><summary>Conferir todas as correspondências e a regra do grupo</summary><ul class="explanation-checked">${withItems(functional).map(conditionText).join('')}</ul></details>` : '<p class="explanation-gap">O retorno não detalha uma correspondência de tarefa ou condição para este padrão.</p>'}</li>
        <li data-reason-step="checks"><h4>O que permitiu usar esta opção</h4>${operationalItems.length ? `<ul class="explanation-checked">${operationalItems.map(({row,ids}) => `<li data-check-id="${escape(row.id)}"><strong>${escape(row.rule_id === 'required_roles' ? 'Participação exigida' : row.field === 'modalidades_disponiveis' ? 'Forma de interação' : 'Recurso disponível')}:</strong> ${escape(refs(ids).join('; ') || 'Não confirmado')} — ${escape(human(row.outcome))}.${row.operator === 'ANY' ? '<span class="explanation-note"> Basta uma das opções deste grupo.</span>' : ''}</li>`).join('')}</ul>` : '<p>Não há testes de participação, modalidade ou recurso detalhados.</p>'}</li>
        <li data-reason-step="knowledge"><h4>O que o conhecimento acrescenta</h4>${visibleKnowledgeIds.length ? `<ul class="explanation-knowledge-brief">${visibleKnowledgeIds.map(kid => `<li data-knowledge-brief="${escape(kid)}">${escape(resolve(kid))}${addedIds.includes(kid) ? '<span class="explanation-note"> Apoio acrescentado com as articulações.</span>' : ''}</li>`).join('')}</ul>` : '<p class="explanation-gap">O retorno não detalhou conhecimentos ligados aos critérios.</p>'}<p class="explanation-note">São entendimentos registrados na base. Recuperação não equivale a confirmação integral.</p>${knowledgeIds.length ? `<details><summary>Consultar os ${knowledgeIds.length} conhecimentos e como foram recuperados</summary>${knowledgeIds.map(kid => `<section class="explanation-knowledge" data-knowledge-id="${escape(kid)}">${field('Entendimento registrado',refs(kid))}${documentarySupport(known.get(kid) || {})}${retrieval(kid)}${technical(kid)}</section>`).join('')}</details>` : ''}</li>
        <li data-reason-step="criteria"><h4>Por que esses critérios se aplicam</h4>${list(view.supports.map(row => row.justification || row.justificativa),'A justificativa situada não foi detalhada. A presença de critérios não preenche essa lacuna.')}${criteriaHtml}</li>
        <li data-reason-step="choice"><h4>O que ainda precisa ser conferido</h4>${list(config.conditions,'Não foi registrada uma condição textual de aplicação.')}<p class="explanation-note">Essas condições foram escritas no padrão; não foram comprovadas automaticamente.</p>${array(data.required_functions).length ? `<details><summary>Conferir funções requeridas e oferecidas</summary>${list(refs(data.required_functions))}<p class="explanation-note">Essas funções já estavam informadas no contexto e correspondem às oferecidas pelo padrão. A interface não as deduziu das barreiras ou do objetivo.</p></details>` : '<p class="explanation-note">Não foi registrada uma função requerida correspondente. A função da escolha é a oferecida pelo padrão.</p>'}</li>
      </ol></div></details>`;
  }

  function conditions(config) {
    return `<details class="explanation-reading" data-explanation-reading="conditions"><summary>Condições, alternativa e acompanhamento</summary><div class="explanation-reading-body">${field('Recursos e disponibilidade',array(config.resource_options).map(resource => `${text(resource)} — ${human(resource.estado || 'NAO_CONFIRMADO')}${resource.opcional ? ' (opcional)' : ''}`))}${field('Condições de aplicação registradas',config.conditions)}<p class="explanation-note">Uma condição documental não é uma verificação automática. A confirmação do objetivo e a adequação da aplicação continuam exigindo conferência humana.</p>${field('Alternativa registrada',config.alternative)}<p class="explanation-note">Esta alternativa está documentada; não foi replanejada nem testada nesta execução.</p>${field('Como acompanhar',config.monitoring)}${field('Limites',config.limit)}${array(config.application?.limitations).length ? `<details><summary>Conferências documentais ainda pendentes</summary>${list(config.application.limitations.map(documentaryText))}</details>` : ''}</div></details>`;
  }

  function effect(config) {
    const view = projectConfiguration(result,config);
    const wording = {
      NEW_CHOICE:['Escolha acrescentada pela articulação','Esta opção não estava na execução isolada e foi selecionada quando as articulações foram habilitadas.'],
      EXPANDED_FOUNDATION:['Fundamentação ampliada','Esta opção já era selecionada sem articulações. A articulação acrescentou apoios; não foi responsável por criar esta escolha.'],
      UNCHANGED:['Sem diferença registrada para esta escolha','A comparação não registra uma nova escolha nem novos pares de apoio para este padrão.'],
      NOT_EXECUTED:['Comparação não disponível','Este retorno não permite comparar a seleção isolada com a seleção que usa articulações. Nenhum efeito foi presumido.'],
    }[view.effect.kind];
    const pairKeys = new Set();
    const pairs = view.effect.addedSupportPairs.filter(pair => { const key = `${pair.criterion_id}|${pair.knowledge_id}`; if (pairKeys.has(key)) return false; pairKeys.add(key); return true; });
    return `<aside class="explanation-effect" data-articulation-effect="${view.effect.kind}"><strong>${wording[0]}</strong><p>${wording[1]}</p>${pairs.length ? `<details><summary>Conferir os apoios acrescentados nesta comparação</summary><ul>${pairs.map(pair => `<li>${field('Critério',refs(pair.criterion_id))}${field('Conhecimento acrescentado a este apoio',refs(pair.knowledge_id))}${technical([pair.criterion_id,pair.knowledge_id,...view.effect.addedSupportPairs.filter(p => p.criterion_id === pair.criterion_id && p.knowledge_id === pair.knowledge_id).map(p => p.origin_id)])}</li>`).join('')}</ul></details>` : ''}</aside>`;
  }

  function technicalChecks(config) {
    const view = projectConfiguration(result,config);
    return `<details class="explanation-checks"><summary>Verificações técnicas desta escolha</summary><p class="explanation-note">São verificações da composição, não comprovação de aprendizagem ou eficácia.</p>${view.checks.length ? `<ul>${view.checks.map(row => `<li data-technical-check-id="${escape(row.id)}"><strong>${escape(human(row.outcome))}:</strong> ${escape(row.message || 'Verificação sem descrição.')}${array(row.expected_ids).length ? field('Itens esperados',refs(row.expected_ids)) : ''}${array(row.matched_ids).length ? field('Correspondências',refs(row.matched_ids)) : ''}${array(row.missing_ids).length ? field('Itens ausentes',refs(row.missing_ids)) : ''}${technical([row.id,row.rule_id])}</li>`).join('')}</ul>` : '<p>Não há verificações detalhadas.</p>'}${technical(config.component_id)}</details>`;
  }

  function configuration(config, index = 0) {
    const viewName = `explanation-view-${presentationId}-${localGraphs.size}`;
    const view = projectConfiguration(result,config);
    const original = array(result.decision?.configuracao_modal).find(row => row.component_id === config.component_id);
    return `<details class="explanation-choice" data-explanation-component="${escape(config.component_id || '')}"${index === 0 ? ' open' : ''}><summary><span class="explanation-title">${index + 1}. ${escape(config.title || config.function || 'Escolha multimodal')}</span><span class="explanation-purpose">${escape(config.function || 'Função não detalhada.')}</span><span class="explanation-modalities">${escape(array(config.modalities).map(text).join(' · '))}</span><span class="explanation-state">${escape(human(config.selection || 'SELECTED'))} · ${escape(human(config.availability_status || 'NAO_CONFIRMADO'))}</span></summary><div class="explanation-choice-body">
      <section class="explanation-action" data-explanation-action><h3>O que fazer</h3>${list(config.actions,'A ação não foi detalhada neste retorno.')}${field('Para que serve esta forma de interação',config.function)}${original?.responsavel ? field('Responsável registrado',original.responsavel) : ''}</section>
      ${view.foundationIncomplete.length ? '<p class="explanation-gap" data-foundation-warning>Parte da fundamentação documental ainda requer conferência. Os apoios e limites estão explicitados abaixo; seleção não significa validação completa.</p>' : ''}
      ${effect(config)}${application(config)}${conditions(config)}${construction(config)}${localGraph(config, viewName)}${technicalChecks(config)}</div></details>`;
  }

  function localGraph(config, viewName) {
    const ids = new Set([config.id]);
    const add = value => array(value).forEach(row => { const id = typeof row === 'object' ? row?.id : row; if (nodes.has(id)) ids.add(id); });
    add(config.application?.context_conditions);
    add(config.application?.required_functions);
    add(config.application?.offered_functions);
    for (const row of array(config.construction?.knowledge)) { add(row.id); add(row.fonte_ids); add(row.trecho_ids); }
    for (const row of array(config.construction?.articulations)) {
      add(row.id); add(row.conhecimento_entrada_ids); add(row.conhecimento_resultante_ids); add(row.trecho_ids); add(row.fonte_ids);
    }
    for (const row of array(config.construction?.contributions)) { add(row.id); add(row.excerpt?.id); add(row.source?.id); }
    const supportIds = new Set();
    for (const row of array(config.application?.supports)) {
      supportIds.add(row.id); add(row.criterion_id); add(row.knowledge_ids);
      for (const origin of array(row.origins)) { add(origin.id); add(origin.fonte_id); add(origin.trecho_id); }
    }
    const allEdges = array(result.explanation?.graph?.edges);
    for (const edge of allEdges) if (edge.source === config.id || edge.target === config.id) { add(edge.source); add(edge.target); }
    const witnessIds = new Set(array(config.application?.retrieval_witnesses).flatMap(row => array(row.check_ids)));
    const edges = allEdges.filter(edge => ids.has(edge.source) && ids.has(edge.target)
      && (!edge.support_id || supportIds.has(edge.support_id))
      && (edge.kind !== 'retrieval_witness' || array(edge.check_ids).some(id => witnessIds.has(id))));
    if (!edges.length) return '<p class="explanation-gap">Não há relações retornadas suficientes para desenhar um grafo local desta escolha.</p>';
    const connected = new Set(edges.flatMap(edge => [edge.source, edge.target]));
    const focusIds = [...ids].filter(id => connected.has(id) && nodes.has(id));
    const key = `${presentationId}-${localGraphs.size}`;
    localGraphs.set(key, {edges, focusIds, config});
    const kind = id => ({context:'Contexto', configuration:'Configuração', knowledge:'Conhecimento', criterion:'Critério', articulation:'Articulação', contribution:'Contribuição', source:'Fonte', excerpt:'Registro documental', criterion_origin:'Origem do critério', function:'Função'}[nodes.get(id)?.kind] || 'Registro');
    return `<details name="${viewName}" class="explanation-local-graph" data-explanation-reading="graph" data-local-graph="${key}"><summary>Grafo local desta escolha</summary><p class="explanation-note">Escolha um registro para ver as relações diretamente ligadas a ele. Abra cada cartão para consultar seus detalhes. As setas indicam relações registradas, não uma sequência causal. Alternar a leitura não gera outra orientação.</p><label class="explanation-graph-selector">Registro em foco<select data-graph-focus>${focusIds.map(id => `<option value="${escape(id)}">${escape(`${kind(id)}: ${text(nodes.get(id)) || 'Sem descrição'}`)}</option>`).join('')}</select></label><p class="explanation-graph-legend"><span>— Uso ou correspondência nesta execução</span><span>┄ Relação documental preexistente</span></p><div class="explanation-graph-controls"><button type="button" data-graph-previous>Relações anteriores</button><button type="button" data-graph-next>Próximas relações</button><p data-graph-status role="status"></p></div><div class="explanation-graph-stage" data-graph-stage></div><p class="explanation-note">São mostradas até quatro relações por vez, apenas entre registros ligados a esta escolha. A tabela completa continua disponível ao final da explicação.</p></details>`;
  }

  function bindGraphs(target) {
    const cleanups = [];
    const documentaryKinds = new Set(['documentary_contribution','documentary_provenance','documented_articulation','exact_origin']);
    const kindNames = {context:'Contexto',configuration:'Configuração modal',knowledge:'Conhecimento',criterion:'Critério',articulation:'Articulação',contribution:'Contribuição documental',source:'Fonte',excerpt:'Registro documental',criterion_origin:'Origem do critério',function:'Função'};
    const nodeCard = id => {
      const row = {...(result.execution_evidence?.entities?.[id] || {}), ...(knowledge.get(id) || {}), ...(criteria.get(id) || {}), ...(known.get(id) || {})};
      const title = text(nodes.get(id)) || text(row) || 'Registro sem descrição';
      const shortTitle = title.length > 105 ? `${title.slice(0,102).trimEnd()}…` : title;
      return `<details class="explanation-graph-node" data-graph-node-id="${escape(id)}"><summary><span class="explanation-graph-kind">${escape(kindNames[nodes.get(id)?.kind] || 'Registro')}</span>${escape(shortTitle)}</summary><div class="explanation-graph-node-body">${field('Descrição completa', title)}${row.operation_explanation ? field('Operação registrada',row.operation_explanation) : ''}${row.added_understanding ? field('Entendimento acrescentado',row.added_understanding) : ''}${row.articulacao ? field('Articulação do conhecimento',row.articulacao) : ''}${row.justification ? field('Justificativa registrada',row.justification) : ''}${row.localizacao_publica || row.location ? field('Localização',row.localizacao_publica || row.location) : ''}${documentarySupport(row)}${row.limite || row.limit ? field('Limite',row.limite || row.limit) : ''}${row.verification_status ? field('Conferência',human(row.verification_status)) : ''}${row.aviso_publicacao ? `<p class="explanation-note">${escape(row.aviso_publicacao)}</p>` : ''}${technical([id])}</div></details>`;
    };
    for (const root of target.querySelectorAll('[data-local-graph]')) {
      const data = localGraphs.get(root.dataset.localGraph);
      if (!data) continue;
      const select = root.querySelector('[data-graph-focus]');
      const stage = root.querySelector('[data-graph-stage]');
      const previous = root.querySelector('[data-graph-previous]');
      const next = root.querySelector('[data-graph-next]');
      const status = root.querySelector('[data-graph-status]');
      const markerId = `graph-arrow-${root.dataset.localGraph}`;
      let page = 0, initialized = false, frame = 0;
      const draw = () => {
        frame = 0;
        if (!root.open || !stage.isConnected) return;
        const svg = stage.querySelector('svg');
        const focal = stage.querySelector('[data-graph-focal] > details > summary');
        if (!svg || !focal || !stage.clientWidth) return;
        const area = stage.getBoundingClientRect(), center = focal.getBoundingClientRect();
        svg.setAttribute('viewBox', `0 0 ${stage.clientWidth} ${stage.clientHeight}`);
        const paths = [...stage.querySelectorAll('[data-graph-source]')].map(relation => {
          const neighbor = relation.querySelector('details > summary').getBoundingClientRect();
          const incoming = relation.dataset.graphTarget === select.value;
          const start = incoming ? {x:neighbor.right-area.left,y:neighbor.top-area.top+neighbor.height/2} : {x:center.right-area.left,y:center.top-area.top+center.height/2};
          const end = incoming ? {x:center.left-area.left,y:center.top-area.top+center.height/2} : {x:neighbor.left-area.left,y:neighbor.top-area.top+neighbor.height/2};
          const middle = (start.x+end.x)/2;
          return `<path class="${documentaryKinds.has(relation.dataset.graphKind) ? 'graph-documentary' : 'graph-execution'}" d="M ${start.x} ${start.y} C ${middle} ${start.y}, ${middle} ${end.y}, ${end.x} ${end.y}" marker-end="url(#${markerId})"/>`;
        }).join('');
        svg.innerHTML = `<defs><marker id="${markerId}" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M 0 0 L 10 5 L 0 10 z"/></marker></defs>${paths}`;
      };
      const schedule = () => { if (!frame) frame = requestAnimationFrame(draw); };
      const observer = typeof ResizeObserver === 'function' ? new ResizeObserver(schedule) : null;
      const render = () => {
        initialized = true;
        const focus = select.value;
        const incident = data.edges.filter(edge => edge.source === focus || edge.target === focus);
        const pages = Math.max(1, Math.ceil(incident.length/4));
        page = Math.min(page,pages-1);
        const shown = incident.slice(page*4,page*4+4);
        const relationCard = edge => {
          const incoming = edge.target === focus;
          const label = edge.label || edge.relation || '';
          const documentary = documentaryKinds.has(edge.kind);
          return `<div class="explanation-graph-relation ${documentary ? 'graph-documentary' : 'graph-execution'}" data-graph-source="${escape(edge.source)}" data-graph-target="${escape(edge.target)}" data-graph-kind="${escape(edge.kind || '')}" data-graph-label="${escape(label)}">${nodeCard(incoming ? edge.source : edge.target)}<p class="explanation-graph-edge-label"><strong>${escape(label)}</strong><span>${documentary ? 'Relação documental' : 'Nesta execução'} · ${incoming ? 'deste registro para o foco →' : 'do foco para este registro →'}</span></p></div>`;
        };
        stage.innerHTML = `<svg class="explanation-graph-arrows" aria-hidden="true" focusable="false"></svg><div class="explanation-graph-column" data-graph-incoming>${shown.filter(edge => edge.target === focus).map(relationCard).join('')}</div><div class="explanation-graph-focal" data-graph-focal><p class="explanation-graph-focus-label">Registro em foco</p>${nodeCard(focus)}</div><div class="explanation-graph-column" data-graph-outgoing>${shown.filter(edge => edge.target !== focus).map(relationCard).join('')}</div>`;
        previous.disabled = page === 0;
        next.disabled = page >= pages-1;
        status.textContent = incident.length ? `Relações ${page*4+1} a ${Math.min(page*4+4,incident.length)} de ${incident.length} ligadas ao foco.` : 'Nenhuma relação local retornada para este foco.';
        schedule();
      };
      const onSelect = () => { page = 0; render(); };
      const onPrevious = () => { page = Math.max(0,page-1); render(); };
      const onNext = () => { page++; render(); };
      const onToggle = event => {
        if (event.target === root) {
          if (root.open) { if (!initialized) render(); observer?.observe(stage); schedule(); }
          else observer?.disconnect();
        } else if (root.open) schedule();
      };
      select.addEventListener('change',onSelect);
      previous.addEventListener('click',onPrevious);
      next.addEventListener('click',onNext);
      root.addEventListener('toggle',onToggle,true);
      window.addEventListener('resize',schedule);
      cleanups.push(() => { observer?.disconnect(); if (frame) cancelAnimationFrame(frame); select.removeEventListener('change',onSelect); previous.removeEventListener('click',onPrevious); next.removeEventListener('click',onNext); root.removeEventListener('toggle',onToggle,true); window.removeEventListener('resize',schedule); });
    }
    let disposed = false;
    const removalObserver = typeof MutationObserver === 'function' ? new MutationObserver(() => {
      if (!target.querySelector('[data-local-graph]')) dispose();
    }) : null;
    const dispose = () => {
      if (disposed) return;
      disposed = true;
      removalObserver?.disconnect();
      cleanups.splice(0).forEach(cleanup => cleanup());
      graphCleanups.delete(target);
    };
    // The application clears the output with replaceChildren(), without rendering a new result.
    // Release graph listeners and their result closure on that path as well.
    removalObserver?.observe(target,{childList:true});
    return dispose;
  }

  function graph() {
    const edges = array(result.explanation?.graph?.edges);
    if (!edges.length) return '<p class="explanation-gap">Não há relações estruturadas retornadas para esta execução.</p>';
    const name = id => text(nodes.get(id)) || 'Registro sem descrição';
    return `<details class="explanation-relations"><summary>Conferir as relações registradas nesta execução (${edges.length})</summary><p class="explanation-note">Estas relações vêm do mesmo retorno que explica as escolhas. Estar presente na mesma orientação não significa que um registro produziu outro.</p><div class="explanation-table-scroll" role="region" tabindex="0" aria-label="Tabela de relações; use as setas para percorrer quando necessário"><table><caption>Origem, relação e destino retornados pelo motor</caption><thead><tr><th scope="col">De</th><th scope="col">Relação registrada</th><th scope="col">Para</th></tr></thead><tbody>${edges.map(edge => `<tr><td>${escape(name(edge.source))}</td><td>${escape(edge.label || human(edge.relation) || 'Relação não descrita')}</td><td>${escape(name(edge.target))}</td></tr>`).join('')}</tbody></table></div><details><summary>Identificadores das relações</summary><ul>${edges.map(edge => `<li><code>${escape(edge.source)}</code> → ${escape(edge.label || edge.relation)} → <code>${escape(edge.target)}</code></li>`).join('')}</ul></details></details>`;
  }
  function rejected() {
    const rows = array(result.explanation?.rejected);
    if (!rows.length) return '';
    return `<details class="explanation-rejected"><summary>Possibilidades não utilizadas nesta execução (${rows.length})</summary><p class="explanation-note">Uma possibilidade pode ter sido excluída ou nem ter sido avaliada. Os motivos abaixo foram registrados pelo motor, não inferidos pela interface.</p>${rows.map(row => {
      const recorded = checkRows(row.check_ids);
      return `<details><summary>${escape(row.title || 'Possibilidade da base')} — ${escape(human(row.selection))}</summary>${field('Motivo registrado', row.reasons, 'O retorno não incluiu um motivo textual.')}${recorded.length ? `<ul>${recorded.map(check => `<li><strong>${escape(human(check.outcome))}:</strong> ${escape(check.message || 'Verificação sem explicação textual.')}${check.text ? `<p>${escape(check.text)}</p>` : ''}${technical([check.id,check.rule_id])}</li>`).join('')}</ul>` : '<p class="explanation-gap">Não há verificações específicas retornadas para esta possibilidade; nenhuma aprovação foi presumida.</p>'}${technical([row.component_id])}</details>`;
    }).join('')}</details>`;
  }
  return {configuration, graph, rejected, refs, bindGraphs};
}

export function renderExplanation(target, result, {prepared = false} = {}) {
  if (!target) return;
  graphCleanups.get(target)?.();
  const explanation = result?.explanation;
  if (!explanation || !Array.isArray(explanation.configurations)) {
    target.innerHTML = '<p class="explanation-gap">A explicação estruturada não foi incluída neste retorno. Não será substituída por uma justificativa presumida.</p>';
    return;
  }
  const presenter = makePresenter(result);
  const remaining = result.execution_evidence?.functions?.remaining || [];
  const stages = array(explanation.stages);
  target.innerHTML = `<div class="explanation"><p>${escape(explanation.summary || 'Abra uma escolha para conferir como seu conhecimento foi construído e por que ele foi empregado aqui.')}</p>${prepared ? '<p class="explanation-note">Esta é uma execução preparada para explicar os registros. Ela não usa informações digitadas por você nem substitui uma avaliação em uso.</p>' : ''}${result.selection_notice ? `<p class="explanation-note">${escape(result.selection_notice)}</p>` : ''}${remaining.length ? `<aside class="explanation-gap"><strong>A orientação não cobre todas as funções requeridas.</strong>${list(presenter.refs(remaining))}<p>Essa cobertura é declarada pelos padrões selecionados, não observada em uma aplicação.</p></aside>` : ''}${stages.length ? `<details class="explanation-stages"><summary>Ver o percurso desta execução</summary><ol>${stages.map(stage => `<li><strong>${escape(stage.title)}</strong><p>${escape(stage.summary)}</p></li>`).join('')}</ol></details>` : ''}${explanation.configurations.length ? `<div class="explanation-choices">${explanation.configurations.map(presenter.configuration).join('')}</div>` : '<p class="explanation-gap">Nenhuma configuração foi selecionada. Confira as lacunas e condições retornadas; não há decisão fundamentada a explicar.</p>'}${presenter.rejected()}${presenter.graph()}${array(result.execution_evidence?.documentary_conditions).length ? `<details><summary>Condições documentais que ainda exigem conferência</summary><p class="explanation-note">Estas condições não foram confirmadas como regras executáveis nesta consulta.</p>${list(result.execution_evidence.documentary_conditions.map(documentaryText))}</details>` : ''}${array(result.execution_evidence?.limitations).length ? `<details><summary>Limites desta explicação</summary>${list(result.execution_evidence.limitations)}</details>` : ''}</div>`;
  graphCleanups.set(target,presenter.bindGraphs(target));
}
