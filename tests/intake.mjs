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
console.log('Intake: verified missing-field questions, immutable updates, participant preservation, explicit extraction, negation and viable-route questions.');
