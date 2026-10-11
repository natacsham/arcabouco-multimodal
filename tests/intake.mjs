import assert from 'node:assert/strict';
import {legacyQuestions, legacyAnswer, legacySummary, detectCompositionTask, compositionDraft, compositionQuestions, compositionSummary} from '../web/amado/intake.mjs';

const item = (id, label = id) => ({id, label, curated: true});
const catalog = {concepts: {TAREFA: [item('T1', 'Ler uma página')], BARREIRA: [item('B1', 'Imagem sem descrição')],
  NECESSIDADE: [item('N1', 'Descrição equivalente')], RECURSO_DISPONIVEL: [item('R1', 'Teclado')],
  CARACTERISTICA_PESSOA: [item('C1', 'Dificuldade para ver imagens')], PAPEL_NO_CONTEXTO: [{...item('P1', 'Pessoa apoiada'), curated: false}, {...item('P2', 'Professor'), curated: false}], MODALIDADE: [item('M1', 'Texto')]}};
const current = {context: {id: 'CASE', texto_curto: 'A pessoa precisa ler.', objetivo: 'Ler', impedimentos_verificados: false,
  raw: {tarefas: ['T1'], recursos_disponiveis: [], recursos_impedidos: ['R1'], recursos_propostos: []},
  participantes: [{id: 'PART1', papel_id: 'P1', papel: 'Pessoa apoiada', caracteristicas: [{id: 'C1'}],
    tarefas: ['Ler uma página'], modalidades: ['Texto'], recursos_operados: ['Teclado']}],
  tarefas: ['Ler uma página'], caracteristicas_relevantes: ['Dificuldade para ver imagens']},
  questions: [{field: 'barreira_ou_necessidade', question: 'Qual dificuldade?'}, {field: 'participantes', question: 'Quem participa?'},
    {field: 'recursos_disponiveis', question: 'Quais recursos?'}, {field: 'mapping', question: 'Confirme'}]};
const original = structuredClone(current);
const questions = legacyQuestions(current, catalog);
assert.equal(questions.length, 3);
assert.equal(questions[0].options.find(row => row.id === 'N1').field, 'necessidades');
const answer = legacyAnswer(current, questions[0], ['N1']);
assert.deepEqual(answer.necessidades, ['N1']);
assert.deepEqual(answer.barreiras, []);
assert.deepEqual(answer.tarefas, ['T1']);
assert.equal(answer.mapping_confirmed, false);
assert.equal(answer.impedimentos_verificados, false);
const roles = legacyAnswer(current, questions[1], ['P2']);
assert.equal(roles.participations.length, 2);
assert.deepEqual(roles.participations[0].recurso_operado_ids, ['R1']);
assert.deepEqual(roles.participations[1].recurso_operado_ids, []);
assert.deepEqual(roles.participations[1].caracteristica_ids, []);
const resources = legacyAnswer(current, questions[2], ['R1']);
assert.deepEqual(resources.recursos_disponiveis, ['R1']);
assert.deepEqual(resources.recursos_impedidos, []);
assert.equal(resources.impedimentos_verificados, false);
assert.deepEqual(legacyAnswer(current, questions[0], null).tarefas, ['T1']);
assert.deepEqual(current, original);
assert(legacySummary(current).some(row => row.label === 'Pessoas' && row.value === 'Pessoa apoiada'));
const groupCurrent = {context: {raw:{modalidades_disponiveis:[]}, participantes:[
  {id:'DEAF',label:'Estudantes surdos (2)',papel:'Estudante',modalidades:[]},
  {id:'BLIND',label:'Estudante cego (1)',papel:'Estudante',modalidades:[]} ]},
  participations:[{id:'DEAF',label:'Estudantes surdos (2)',quantidade:2,papel_id:'P1',modalidade_ids:[],caracteristica_ids:[]},
    {id:'BLIND',label:'Estudante cego (1)',papel_id:'P1',modalidade_ids:[],caracteristica_ids:[]}],
  questions:[{field:'modalidades_disponiveis',participant_id:'DEAF',participant_label:'Estudantes surdos (2)',
    answer_field:'modalidade_ids',concept_ids:['M1'],question:'Como este grupo acompanha a atividade?'}]};
const groupQuestion = legacyQuestions(groupCurrent,catalog)[0];
assert.equal(groupQuestion.id,'modalidades_disponiveis:DEAF');
assert.equal(groupQuestion.label,'Como este grupo acompanha o conteúdo?');
assert.deepEqual(groupQuestion.options.map(row=>row.id),['M1']);
const groupAnswer = legacyAnswer(groupCurrent,groupQuestion,['M1']);
assert.deepEqual(groupAnswer.participations[0].modalidade_ids,['M1']);
assert.deepEqual(groupAnswer.participations[1].modalidade_ids,[]);
assert.deepEqual(groupAnswer.modalidades_disponiveis,[]);
const noteAnswer = legacyAnswer(groupCurrent,groupQuestion,[],'Usam Libras com apoio de intérprete.');
assert.equal(noteAnswer.participations[0].apoios_informados,'Usam Libras com apoio de intérprete.');
assert.deepEqual(noteAnswer.participations[0].modalidade_ids,[],'A note is not promoted to an executable concept');
assert(legacySummary(groupCurrent).find(row=>row.label==='Pessoas').value.includes('Estudante cego (1)'));
assert.deepEqual(groupCurrent.participations[0].modalidade_ids,[],'Participant answers are immutable');
// The real worker can return a labelled context projection without a raw
// participations property. Answers must preserve labels, counts and earlier IDs.
const projectedGroup = structuredClone(groupCurrent);
delete projectedGroup.participations;
Object.assign(projectedGroup.context.participantes[0], {papel_id:'P1',quantidade:2,
  tarefas:['Ler uma página'],modalidades:['Texto'],observacoes:'Grupo confirmado',apoios_informados:'Apoio anterior'});
Object.assign(projectedGroup.context.participantes[1], {papel_id:'P1',quantidade:1,modalidades:[]});
projectedGroup.questions[0] = {...projectedGroup.questions[0],participant_id:'BLIND',participant_label:'Estudante cego (1)'};
const projectedQuestion = legacyQuestions(projectedGroup,catalog)[0];
const projectedAnswer = legacyAnswer(projectedGroup,projectedQuestion,['M1']);
assert.deepEqual(projectedAnswer.participations[0].modalidade_ids,['M1']);
assert.deepEqual(projectedAnswer.participations[0].tarefa_ids,['T1']);
assert.equal(projectedAnswer.participations[0].quantidade,2);
assert.equal(projectedAnswer.participations[0].label,'Estudantes surdos (2)');
assert.equal(projectedAnswer.participations[0].apoios_informados,'Apoio anterior');
assert.deepEqual(projectedAnswer.participations[1].modalidade_ids,['M1']);
const requirementCatalog=structuredClone(catalog);
requirementCatalog.concepts.RECURSO_DISPONIVEL.push({...item('R2','Editor para preparar conteúdo'),curated:false});
const requirementQuestion=legacyQuestions({...groupCurrent,questions:[{field:'recursos_disponiveis',
  participant_id:'DEAF',participant_label:'Grupo',answer_field:'recurso_operado_ids',concept_ids:['R2'],
  question:'Quem prepara o conteúdo pode usar um editor?'}]},requirementCatalog)[0];
assert.deepEqual(requirementQuestion.options.map(row=>row.id),['R2'],
  'A specific existing capability requirement must be answerable even if hidden in the general catalogue');
const specificRole=legacyQuestions({...current,questions:[{field:'participantes',concept_ids:['P2'],
  question:'Quem pode preparar ou adaptar o conteúdo?'}]},catalog)[0];
assert.equal(specificRole.label,'Quem pode preparar ou adaptar o conteúdo?');
assert.deepEqual(specificRole.options.map(row=>row.id),['P2']);
const multiSupported=structuredClone(groupCurrent);
multiSupported.participations.forEach(person=>person.papel_id='PAPEL-ESTUDANTE');
multiSupported.participations[0].modalidade_ids=['M1'];
multiSupported.questions=[{field:'recursos_disponiveis',question:'Quais equipamentos estão disponíveis?'}];
const globalEquipment=legacyAnswer(multiSupported,legacyQuestions(multiSupported,catalog)[0],['R1']);
assert.deepEqual(globalEquipment.participations,multiSupported.participations,
  'A global equipment answer must preserve different personal answers, not remap them to empty global modalities');
const preciseTask=legacyQuestions({...current,questions:[{field:'tarefas',type:'single',concept_ids:['T1'],
  question:'Que atividade digital precisa ser acessível?'}]},catalog)[0];
const broaderTask=structuredClone(current);broaderTask.context.raw.tarefas=['BROAD-TASK'];
assert.deepEqual(legacyAnswer(broaderTask,preciseTask,'T1').tarefas,['T1'],
  'A radio-confirmed operational activity replaces the broad extraction hypothesis instead of adding another task');

const composition = {tasks: [{id: 'TaskCreateReviewedText', label: 'Escrever e revisar', required_functions: [item('Expression'), item('Review')]},
  {id: 'TaskReviewExistingText', label: 'Revisar texto', required_functions: [item('Review')]}],
  facts: ['LearningCommunicationContext', 'ContentAvailable', 'CanUseKeyboard', 'CanUseSpeech', 'CanReviewVisualText', 'CanReviewSpeech', 'CanCorrect', 'ControlsCompletion', 'KeyboardEffortAcceptable'].map(id => item(id)),
  resources: ['Keyboard', 'EditableText', 'Microphone', 'Display', 'TextToSpeech', 'AudioOutput'].map(id => item(id)),
  capabilities: [{id: 'CaptureKeyboard', function_id: 'Expression', required_facts: ['CanUseKeyboard', 'KeyboardEffortAcceptable'], required_resources: ['Keyboard', 'EditableText']},
    {id: 'CaptureSpeech', function_id: 'Expression', required_facts: ['CanUseSpeech'], required_resources: ['Microphone', 'EditableText']},
    {id: 'ReviewText', function_id: 'Review', required_facts: ['CanReviewVisualText', 'CanCorrect'], required_resources: ['Display', 'EditableText']},
    {id: 'ReviewSpeech', function_id: 'Review', required_facts: ['CanReviewSpeech', 'CanCorrect'], required_resources: ['AudioOutput', 'TextToSpeech', 'EditableText']}],
  relations: [{from_function: 'Expression', to_function: 'Review', required_facts: ['ControlsCompletion']}]};
assert.equal(detectCompositionTask('O aluno precisa escrever uma resposta e conferir o texto na aula.'), 'TaskCreateReviewedText');
assert.equal(detectCompositionTask('A estudante vai revisar o texto já escrito.'), 'TaskReviewExistingText');
assert.equal(detectCompositionTask('Um aluno tem TEA e usa computador.'), null);
assert.equal(detectCompositionTask('Uma pessoa cega quer escrever e revisar um texto.'), null);
assert.equal(detectCompositionTask('A professora quer construir um vídeo com a turma.'), null);
assert.equal(detectCompositionTask('A professora não vai escrever, apenas conferir um texto.'), null);
assert.equal(detectCompositionTask('O aluno vai escrever e revisar um texto fora do contexto escolar.'), null);
assert.equal(detectCompositionTask('Os estudantes surdos e um estudante cego vão escrever uma resposta e revisar o texto na aula.'),null);
const unknown = compositionDraft('Uma estudante cega quer escrever e revisar um texto.', composition);
assert.equal(unknown.facts.CanReviewVisualText, null);
assert.equal(unknown.facts.CanUseKeyboard, null);
assert.equal(unknown.resources.Keyboard, null);
assert.equal(unknown.facts.LearningCommunicationContext, true);
const explicit = compositionDraft('O aluno quer escrever uma resposta e revisar o texto. Tem um teclado. Consegue usar o teclado. Não consegue ler o texto na tela. Não pode ouvir.', composition);
assert.equal(explicit.resources.Keyboard, true);
assert.equal(explicit.facts.CanUseKeyboard, true);
assert.equal(explicit.facts.CanReviewVisualText, false);
assert.equal(explicit.facts.CanReviewSpeech, false);
assert.equal(explicit.facts.KeyboardEffortAcceptable, null);
assert.equal(compositionDraft('O aluno tem um computador e um microfone.', composition).resources.Microphone, null);
assert.equal(compositionDraft('O aluno não tem teclado.', composition).resources.Keyboard, false);
assert.equal(compositionDraft('O aluno não tem um teclado.', composition).resources.Keyboard, false);
assert.equal(compositionDraft('O aluno não consegue usar teclado.', composition).facts.CanUseKeyboard, false);
assert.equal(compositionDraft('O aluno não consegue usar teclado. Consegue usar teclado em casa.', composition).facts.CanUseKeyboard, null);
const route = {task: 'TaskCreateReviewedText', facts: {CanUseSpeech: false, CanReviewSpeech: false}, resources: {Microphone: false}};
const routeQuestions = compositionQuestions(route, composition);
assert(!routeQuestions.some(row => row.concept_id === 'CanUseSpeech'));
assert(!routeQuestions.some(row => row.concept_id === 'AudioOutput'));
assert(routeQuestions.some(row => row.concept_id === 'CanUseKeyboard'));
assert(routeQuestions.some(row => row.concept_id === 'ControlsCompletion'));
const noRoutes = {...route, facts: {...route.facts, CanUseKeyboard: false, CanReviewVisualText: false}};
assert.deepEqual(compositionQuestions(noRoutes, composition), []);
const review = {...route, task: 'TaskReviewExistingText'};
assert(!compositionQuestions(review, composition).some(row => row.concept_id === 'Keyboard'));
assert(!compositionQuestions(review, composition).some(row => row.concept_id === 'ControlsCompletion'));
assert(compositionSummary(explicit, composition).some(row => row.label === 'Recursos disponíveis' && row.value === 'Keyboard'));
assert.equal(compositionDraft('O aluno usa computador e teclado para escrever e revisar uma resposta.',composition).resources.Keyboard,true);
assert.equal(compositionDraft('O aluno não usa teclado para escrever e revisar uma resposta.',composition).resources.Keyboard,false);
const naturalDraft = compositionDraft('O aluno usa computador e teclado para escrever uma resposta e revisar o texto.',composition);
const naturalQuestions = compositionQuestions(naturalDraft,composition);
assert(!naturalQuestions.some(row=>row.concept_id==='Microphone'),'Do not ask for every alternative route');
assert(naturalQuestions.every(row=>row.label.endsWith('?')),'Questions use actionable language rather than RDF labels');
const completeVisualRoute={task:'TaskCreateReviewedText',facts:{ContentAvailable:true,CanUseKeyboard:true,KeyboardEffortAcceptable:true,
  CanReviewVisualText:true,CanCorrect:true,ControlsCompletion:true},resources:{Keyboard:true,EditableText:true,Display:true}};
assert.deepEqual(compositionQuestions(completeVisualRoute,composition),[],'A complete route does not require surveying unused alternatives');
assert(compositionQuestions({...naturalDraft,resources:{...naturalDraft.resources,Keyboard:false}},composition)
  .some(row=>row.concept_id==='Microphone'),'A blocked route allows another represented route to be considered');
const groupComposition={...composition,facts:composition.facts.map(row=>({...row,scope:row.id==='LearningCommunicationContext'?'context':'person'}))};
const scopedDraft={task:'TaskCreateReviewedText',facts:{LearningCommunicationContext:true,CanReviewVisualText:true},
  resources:{Keyboard:true,EditableText:true,Display:true,Microphone:false},participants:[
    {id:'A',label:'Grupo A',facts:{ContentAvailable:true,CanUseKeyboard:true,KeyboardEffortAcceptable:true,CanReviewVisualText:true,CanCorrect:true,ControlsCompletion:true}},
    {id:'B',label:'Grupo B',facts:{ContentAvailable:true,CanUseKeyboard:true,KeyboardEffortAcceptable:true,CanReviewVisualText:false,CanReviewSpeech:true,CanCorrect:true,ControlsCompletion:true}}]};
const scopedQuestions=compositionQuestions(scopedDraft,groupComposition);
assert(scopedQuestions.every(row=>row.participant_id==='B'));
assert(scopedQuestions.every(row=>row.id.endsWith(':B')));
assert(!scopedQuestions.some(row=>row.concept_id==='CanReviewVisualText'),'Global visual ability must not overwrite individual negative condition');
assert(compositionSummary(scopedDraft,groupComposition).filter(row=>row.label==='Participante').length===2);
console.log('Intake: verified missing-field questions, immutable updates, participant preservation, explicit extraction, negation and viable-route questions.');
