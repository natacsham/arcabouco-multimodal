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
    .filter(item => type !== 'CARACTERISTICA_PESSOA' || item.categoria !== 'ESCOPO_DE_PUBLICO')
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
  const preservedPeople = copy(question.existingParticipations || participants(current));
  // Global equipment/context answers must not clear distinct personal routes.
  if (preservedPeople.filter(person => ['PAPEL-ESTUDANTE','PAPEL-PESSOA-APOIADA'].includes(person.papel_id)).length > 1)
    payload.participations = preservedPeople;
  const hasNote = question.participant_id && typeof note === 'string' && note.trim();
  if (!hasNote && (value === null || value === undefined || value === '' || value === 'unknown')) return payload;
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
