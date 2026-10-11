// Pure presentation helpers. Extraction is a draft for human confirmation;
// neither a resource name nor a diagnosis proves a functional capability.
const copy = value => JSON.parse(JSON.stringify(value));
const norm = value => String(value || '').normalize('NFD').replace(/\p{M}/gu, '').toLowerCase();
const uniq = values => [...new Set(values)];
const fields = {
  tarefas: ['TAREFA', 'Qual atividade a pessoa precisa realizar?'],
  caracteristicas_pessoa: ['CARACTERISTICA_PESSOA', 'O que precisamos considerar sobre a pessoa nesta atividade?'],
  barreiras: ['BARREIRA', 'O que dificulta a atividade?'],
  necessidades: ['NECESSIDADE', 'Que apoio a pessoa precisa?'],
  ambientes: ['AMBIENTE', 'Onde a atividade acontece?'],
  modalidades_disponiveis: ['MODALIDADE', 'Que formas de interação podem ser usadas?'],
  recursos_digitais: ['RECURSO_DIGITAL', 'Qual aplicativo ou conteúdo está envolvido?'],
  recursos_disponiveis: ['RECURSO_DISPONIVEL', 'Quais equipamentos e apoios estão disponíveis?'],
};
function options(catalog, type, selected = [], field) {
  return (catalog?.concepts?.[type] || []).filter(item => selected.includes(item.id) ||
    ((type === 'PAPEL_NO_CONTEXTO' || item.curated !== false) && item.scope !== 'CASO_ENTREVISTA'))
    .filter(item => type !== 'CARACTERISTICA_PESSOA' || item.categoria !== 'ESCOPO_DE_PUBLICO')
    .sort((a, b) => (a.order || 500) - (b.order || 500) || a.label.localeCompare(b.label, 'pt-BR'))
    .map(item => ({id: item.id, label: item.label, ...(field ? {field} : {})}));
}
function participants(current, catalog) {
  if (current.participations) return copy(current.participations);
  const byLabel = new Map(Object.values(catalog?.concepts || {}).flat().map(item => [item.label, item.id]));
  const ids = values => (values || []).map(item => typeof item === 'object' ? item.id : byLabel.get(item)).filter(Boolean);
  return (current.context?.participantes || []).map(row => ({id: row.id, papel_id: row.papel_id,
    caracteristica_ids: ids(row.caracteristicas), tarefa_ids: ids(row.tarefas),
    modalidade_ids: ids(row.modalidades), recurso_operado_ids: ids(row.recursos_operados),
    objetivo_participacao: row.objetivo || ''}));
}
export function legacyQuestions(current, catalog) {
  const raw = current.context?.raw || {};
  return (current.questions || []).filter(item => item.field !== 'mapping').map(item => {
    const field = item.field;
    const question = {id: field, field, label: item.question, type: 'multi', options: []};
    if (field === 'objetivo') return {...question, type: 'text', label: 'O que a pessoa quer conseguir fazer?'};
    if (field === 'barreira_ou_necessidade') return {...question, label: 'O que dificulta a atividade ou precisa de apoio?',
      options: [...options(catalog, 'BARREIRA', raw.barreiras, 'barreiras'), ...options(catalog, 'NECESSIDADE', raw.necessidades, 'necessidades')]};
    if (field === 'participantes') return {...question, label: 'Quem participa desta atividade?',
      options: options(catalog, 'PAPEL_NO_CONTEXTO'), existingParticipations: participants(current, catalog)};
    const config = fields[field];
    return config ? {...question, label: config[1], options: options(catalog, config[0], raw[field] || [])} : {...question, type: 'text'};
  });
}
export function legacyAnswer(current, question, value) {
  const c = current.context || {};
  const payload = {...copy(c.raw || {}), objetivo: c.objetivo || '', descricao_do_contexto: c.texto_curto || '',
    restricoes: copy(c.restricoes || []), operacao_do_recurso: c.operacao_do_recurso || '',
    impedimentos_verificados: c.impedimentos_verificados === true, mapping_confirmed: false, transfer_confirmed: false};
  if (value === null || value === undefined || value === '' || value === 'unknown') return payload;
  if (question.type === 'text') { payload[question.field] = String(value).trim(); return payload; }
  const chosen = (Array.isArray(value) ? value : [value]).filter(id => question.options.some(item => item.id === id));
  if (question.field === 'barreira_ou_necessidade') {
    for (const field of ['barreiras', 'necessidades']) payload[field] = uniq([...(payload[field] || []),
      ...chosen.filter(id => question.options.some(item => item.id === id && item.field === field))]);
  } else if (question.field === 'participantes') {
    const rows = copy(question.existingParticipations || current.participations || []);
    for (const role of chosen) if (!rows.some(row => row.papel_id === role)) rows.push({papel_id: role,
      caracteristica_ids: [], tarefa_ids: [], modalidade_ids: [], recurso_operado_ids: [], objetivo_participacao: ''});
    payload.participations = rows;
  } else {
    payload[question.field] = uniq([...(payload[question.field] || []), ...chosen]);
    if (question.field === 'recursos_disponiveis') {
      for (const field of ['recursos_impedidos', 'recursos_propostos']) payload[field] = (payload[field] || []).filter(id => !chosen.includes(id));
    }
  }
  return payload;
}
export function legacySummary(current) {
  const c = current.context || {};
  const rows = [
    ['Pessoas', (c.participantes || []).map(item => item.papel)],
    ['Sobre a pessoa', c.caracteristicas_relevantes], ['Atividade', c.tarefas], ['Objetivo', c.objetivo],
    ['Dificuldade', c.barreiras], ['Apoio necessário', c.necessidades], ['Onde acontece', c.ambientes],
    ['Formas de interação', c.modalidades_disponiveis], ['Aplicativo ou conteúdo', c.recursos_digitais],
    ['Recursos disponíveis', c.recursos_disponiveis], ['Recursos impedidos', c.recursos_impedidos],
  ];
  return rows.map(([label, value]) => ({label, value: Array.isArray(value) ? value.join('; ') : value || ''})).filter(row => row.value);
}
export function detectCompositionTask(narrative) {
  const text = norm(narrative).replace(/\bnao (?:vai|precisa|quer|deve) (?:escrever|redigir|digitar|revisar|conferir|corrigir)\b/g, '');
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
  ['resources', 'Keyboard', /\b(teclado (?:esta )?disponivel|tem (?:um )?teclado)\b/, /\b(sem teclado|teclado indisponivel|nao (?:tem|ha) (?:um )?teclado)\b/],
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
export function compositionQuestions(context, catalog) {
  const task = (catalog.tasks || []).find(item => item.id === context.task);
  if (!task) return [];
  const requiredFunctions = new Set((task.required_functions || []).map(item => typeof item === 'string' ? item : item.id));
  const possible = (catalog.capabilities || []).filter(item => requiredFunctions.has(item.function_id) &&
    !(item.required_resources || []).some(id => context.resources?.[id] === false) &&
    !(item.required_facts || []).some(id => context.facts?.[id] === false));
  const needed = new Set();
  for (const capability of possible) {
    for (const id of capability.required_resources || []) if (context.resources?.[id] == null) needed.add('resources:' + id);
    for (const id of capability.required_facts || []) if (context.facts?.[id] == null) needed.add('facts:' + id);
  }
  if (requiredFunctions.size > 1 && [...requiredFunctions].every(id => possible.some(item => item.function_id === id))) {
    for (const relation of catalog.relations || []) if (requiredFunctions.has(relation.from_function) && requiredFunctions.has(relation.to_function)) {
      for (const id of relation.required_facts || []) if (context.facts?.[id] == null) needed.add('facts:' + id);
    }
  }
  return [...needed].map(key => {
    const [field, id] = key.split(':');
    const row = (catalog[field] || []).find(item => item.id === id);
    return {id: key, field, concept_id: id, label: row?.label || id, type: 'single',
      options: [{id: 'true', label: 'Sim'}, {id: 'false', label: 'Não'}, {id: 'unknown', label: 'Não sei'}]};
  });
}
export function compositionSummary(context, catalog) {
  const task = (catalog.tasks || []).find(item => item.id === context.task);
  const rows = task ? [{label: 'Atividade', value: task.label}] : [];
  for (const field of ['facts', 'resources']) {
    const confirmed = (catalog[field] || []).filter(item => context[field]?.[item.id] === true).map(item => item.label);
    const blocked = (catalog[field] || []).filter(item => context[field]?.[item.id] === false).map(item => item.label);
    if (confirmed.length) rows.push({label: field === 'facts' ? 'Condições informadas' : 'Recursos disponíveis', value: confirmed.join('; ')});
    if (blocked.length) rows.push({label: field === 'facts' ? 'Condições que não se aplicam' : 'Recursos indisponíveis', value: blocked.join('; ')});
  }
  return rows;
}
