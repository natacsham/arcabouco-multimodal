// Small real public-site verification. Synthetic input; not a participant session.
// Does not mutate product, use hidden decision APIs, or repeat the local QA suite.
import assert from 'node:assert/strict';
async function advanceUnderstanding(page){
  await page.locator('#case-understanding').waitFor({state:'visible',timeout:180000});
  assert(await page.locator('#case-questions').isHidden(),'Understanding precedes questions');
  assert(await page.locator('#understanding-summary').innerText(),'Preview contains registered information');
  await page.locator('#continue-understanding').click();
}
import fs from 'node:fs/promises';
import path from 'node:path';
import crypto from 'node:crypto';
import {execFileSync} from 'node:child_process';
import {fileURLToPath, pathToFileURL} from 'node:url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const base = process.env.SMOKE_PUBLIC_URL || 'https://natacsham.github.io/arcabouco-multimodal/';
const origin = new URL(base).origin;
const modules = process.env.AMADO_NODE_MODULES || path.join(process.env.USERPROFILE, '.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules');
const {chromium} = await import(pathToFileURL(path.join(modules, 'playwright/index.mjs')).href);
const sha = bytes => crypto.createHash('sha256').update(bytes).digest('hex');
const expected = JSON.parse(await fs.readFile(path.join(root, 'web/amado/manifest.json'), 'utf8'));
const report = {
  type: 'SYNTHETIC_PUBLIC_SMOKE_NOT_PARTICIPANT_SESSION',
  url: base, checked_at: new Date().toISOString(),
  expected_commit: execFileSync('git', ['rev-parse', 'HEAD'], {cwd: root, encoding: 'utf8'}).trim(),
  commit_observation: 'Deployment commit supplied by the publisher; serving identity is verified independently by manifest and content hashes, not an HTTP commit identifier.',
  test_sha256: sha(await fs.readFile(fileURLToPath(import.meta.url))),
  checks: {}, assets: {}, flows: {}, errors: [], external_requests: [],
  limits: [
    'Synthetic task confirmation and unknown follow-up answers; not an expert session or learning evaluation.',
    'Mathematics and astronomy are contextual subjects. The confirmed operational task is digital-content access, not a complete teaching method for either subject.',
    'GERADA_PARCIAL does not establish coverage of every participant or guarantee educational benefit.',
    'Microphone accuracy, screen readers, comprehension with users and full WCAG conformance were not tested in this public smoke.',
    'Unknown reader availability and operation stay pending; this smoke does not establish personal skills from a reported disability.',
    'This smoke verifies a maximum-three-question initial round and a conditional partial output in each presentation; it does not replace the full local regression.'
  ]
};
const check = (name, result) => {report.checks[name] = Boolean(result); assert(result, name);};
let browser, context;
try {
  browser = await chromium.launch({headless: true, executablePath: process.env.AMADO_CHROMIUM || 'C:/Program Files/Google/Chrome/Application/chrome.exe'});
  report.browser = browser.version();
  context = await browser.newContext({viewport: {width: 1280, height: 900}, reducedMotion: 'reduce'});
  await context.route('**/*', route => {
    const request = route.request();
    if (!request.url().startsWith(origin + '/') && !request.url().startsWith('blob:')) {
      report.external_requests.push(request.url()); return route.abort();
    }
    return route.continue();
  });
  const manifestResponse = await context.request.get(base + 'amado/manifest.json', {headers: {'Cache-Control': 'no-cache'}});
  check('public_manifest_http_200', manifestResponse.ok());
  const manifestBytes = await manifestResponse.body();
  const manifest = JSON.parse(manifestBytes.toString());
  report.public_manifest_sha256 = sha(manifestBytes);
  report.version = manifest.version;
  assert.deepEqual(manifest, expected);
  check('public_manifest_matches_current_build', true);
  const assets = [
    ...Object.entries(expected.frontend_sha256).map(([file, hash]) => ['amado/' + file, hash]),
    ...Object.entries(expected.site_assets_sha256).map(([file, hash]) => [file, hash]),
    ...Object.entries(expected.runtime).map(([file, item]) => ['amado/runtime/' + file, item.sha256]),
    ['amado/engine.py', expected.core_sha256], ['amado/bridge.py', expected.bridge_sha256],
    ['amado/assets/base.zip', expected.base_zip_sha256]
  ];
  for (const [file, hash] of assets) {
    const response = await context.request.get(base + file);
    assert(response.ok(), file + ' HTTP response');
    const bytes = await response.body(); const actual = sha(bytes);
    report.assets[file] = {bytes: bytes.length, expected_sha256: hash, served_sha256: actual, passed: actual === hash};
    assert.equal(actual, hash, 'Published content hash: ' + file);
  }
  check('public_html_engine_base_runtime_and_catalog_hashes', Object.values(report.assets).every(item => item.passed));
  const docs = await context.newPage();
  docs.on('pageerror', error => report.errors.push(error.message));
  await docs.goto(base + 'ontologia/', {waitUntil: 'domcontentloaded'});
  await docs.locator('[data-source-catalog-details] > summary').click();
  await docs.locator('#source-publication').waitFor({state: 'visible'});
  const catalog = await (await context.request.get(base + 'assets/source-catalog.json')).json();
  report.source_catalog = {version: catalog.base_version, summary: catalog.summary};
  check('source_catalog_rendered_with_limits',
    (await docs.locator('[data-source-catalog]').innerText()).includes(catalog.summary.sources + ' fontes e ' + catalog.summary.references + ' referências') &&
    (await docs.locator('[data-source-catalog]').innerText()).includes('Ter um link não significa'));
  const publication = await docs.locator('#source-publication option').nth(1).getAttribute('value');
  assert(publication, 'An existing publication is selectable');
  await docs.locator('#source-publication').selectOption(publication);
  check('source_reference_selection_works', await docs.locator('[data-source-references] > li').count() > 0);
  await docs.close();

  await context.addInitScript(() => {
    window.__publicSmoke = {operations: [], state: null, generated: null, progress: []};
    const NativeWorker = window.Worker;
    window.Worker = class extends NativeWorker {
      constructor(...args) {
        super(...args); this.operations = new Map();
        this.addEventListener('message', event => {
          if(event.data.type==='progress'){window.__publicSmoke.progress.push(event.data);return;}
          if (event.data.type !== 'result') return;
          const operation = this.operations.get(event.data.id), data = event.data.data;
          if (data?.current?.context) window.__publicSmoke.state = data.current;
          else if (data?.context) window.__publicSmoke.state = data;
          if (operation === 'generate' || operation === 'compose') window.__publicSmoke.generated = data;
        });
      }
      postMessage(data, ...rest) {
        this.operations.set(data.id, data.operation); window.__publicSmoke.operations.push(data.operation);
        return super.postMessage(data, ...rest);
      }
    };
  });
  const ready = page => page.waitForFunction(() => document.querySelector('#health')?.dataset.state === 'ready' &&
    document.querySelector('#main')?.getAttribute('aria-busy') === 'false', {}, {timeout: 180000});
  for (const [view, topic] of [['index.html', 'matemática'], ['guiado.html', 'astronomia']]) {
    const page = await context.newPage(); page.on('pageerror', error => report.errors.push(error.message));
    await page.goto(base + 'amado/' + view, {waitUntil: 'domcontentloaded'}); await ready(page);
    const flow = report.flows[view] = {topic, questions: []};
    check(view + '_real_worker_ready', await page.locator('#analyze-case').isEnabled());
    check(view + '_direct_challenge_heading', (await page.locator('h1').innerText()).trim() === 'Qual é o seu desafio de hoje?');
    await page.locator('#case-narrative').fill('Sou docente e quero ensinar um assunto complexo de ' + topic + ' à minha turma, com dois estudantes surdos e um estudante cego.');
    await page.locator('#analyze-case').click();await advanceUnderstanding(page);
    await page.waitForFunction(() => !document.querySelector('#case-questions').hidden ||
      !document.querySelector('#case-review').hidden, {}, {timeout: 180000});
    const initial = await page.evaluate(() => window.__publicSmoke.state);
    const noInventedAbility = state => (state.participations || []).every(person =>
      !(person.modalidade_ids || []).length && !(person.recurso_operado_ids || []).length) &&
      !(state.context.raw.modalidades_disponiveis || []).length &&
      !(state.context.raw.recursos_disponiveis || []).includes('REC-LEITOR-DE-TELA');
    check(view + '_no_inferred_classroom_or_access_technology', initial.context.raw.ambientes.length === 0 &&
      noInventedAbility(initial));
    const requirements = initial.context.access_requirements || [];
    check(view + '_documented_needs_derived_without_inventing_abilities',
      requirements.length >= 2 && requirements.every(item => item.matrix_id && item.source_ids?.length &&
        item.excerpt_ids?.length && item.capabilities_inferred === false && item.participant_id));
    const originalPeople = new Map(initial.participations.map(person => [person.id, person]));
    check(view + '_derived_needs_belong_to_the_reported_participants',
      requirements.some(item => item.matrix_id === 'MF-01' && /ceg/i.test(originalPeople.get(item.participant_id)?.label || '')) &&
      requirements.some(item => item.matrix_id === 'MF-11' && /surd/i.test(originalPeople.get(item.participant_id)?.label || '')));
    let optionClickChecked = false;
    while (await page.locator('#case-questions').isVisible()) {
      const row = page.locator('#question-fields [data-question]'), id = await row.getAttribute('data-question');
      const person = await page.locator('#question-person').innerText(), field = id.split(':')[0];
      const labelText = await page.locator('#questions-title').innerText();
      const progress = await page.locator('#question-progress').innerText();
      const total = Number(await page.locator('#question-progress').getAttribute('data-total'));
      assert(flow.questions.length < 3, 'The initial clarification round is limited to three questions');
      assert(total <= 3 && total >= flow.questions.length + 1, 'Progress describes this short round');
      assert(/\d+\s+de(?:\s+até)?\s+\d+/.test(progress), 'Progress is available while answering');
      assert.notEqual(field, 'barreira_ou_necessidade', 'Documented access needs must not be asked again');
      assert(!/^(Quais dificuldades ou necessidades você percebe|O que facilita ou dificulta a participação)\?$/.test(labelText),
        'A follow-up must be contextual, not the previous generic prompt');
      let values;
      if (field === 'tarefas') values = ['TAR-ACESSAR-COMPREENDER-CONTEUDO-DIGITAL'];
      else if (field === 'objetivo') {
        values = ['Permitir que as pessoas acessem e compreendam o conteúdo apresentado.'];
        await row.locator('textarea').first().fill(values[0]);
      } else if (await row.locator('input[value="unknown"]').count()) values = ['unknown'];
      else {
        values = ['Ainda não sei'];
        await row.locator('textarea').first().fill(values[0]);
      }
      if (field !== 'objetivo' && values[0] !== 'Ainda não sei') {
        for (const value of values) {
          const control = row.locator('input[value="' + value + '"]');
          assert.equal(await control.count(), 1, 'Existing response option ' + value);
          await control.evaluate(element => {
            for (let ancestor = element.parentElement; ancestor; ancestor = ancestor.parentElement)
              if (ancestor.tagName === 'DETAILS') ancestor.open = true;
          });
          const label = control.locator('xpath=ancestor::label[1]');
          const box = await label.boundingBox(); assert(box);
          await label.click({position: {x: box.width - 12, y: box.height / 2}});
          assert(await control.isChecked(), 'Clicking the option label selects its control');
          assert.equal(await label.evaluate(element => getComputedStyle(element).cursor), 'pointer');
          optionClickChecked = true;
        }
      }
      flow.questions.push({id, label: labelText, participant_label: person, values, progress});
      assert.equal(new Set(flow.questions.map(item => item.id)).size, flow.questions.length, 'No repeated question');
      await page.locator('#answer-questions').click();
      await page.waitForFunction(previous => !document.querySelector('#case-review').hidden ||
        document.querySelector('#question-fields [data-question]')?.dataset.question !== previous, id, {timeout: 180000});
    }
    check(view + '_whole_option_is_clickable', optionClickChecked);
    check(view + '_short_contextual_round_finishes', flow.questions.length > 0 && flow.questions.length <= 3);
    const state = await page.evaluate(() => window.__publicSmoke.state);
    flow.participants = state.participations.filter(person => person.papel_id === 'PAPEL-ESTUDANTE');
    flow.access_requirements = state.context.access_requirements;
    check(view + '_groups_and_task_preserved', flow.participants.some(person => /surd/i.test(person.label) && person.quantidade === 2) &&
      flow.participants.some(person => /ceg/i.test(person.label) && person.quantidade === 1) &&
      JSON.stringify(state.context.raw.tarefas) === JSON.stringify(['TAR-ACESSAR-COMPREENDER-CONTEUDO-DIGITAL']));
    check(view + '_unknown_answers_do_not_become_personal_abilities', noInventedAbility(state));
    check(view + '_explicit_confirmation_required', await page.locator('#generate-orientation').isDisabled());
    await page.locator('#case-confirmed').check(); await page.locator('#generate-orientation').click();
    await page.locator('#orientation-result').waitFor({state: 'visible', timeout: 180000});
    const result = await page.evaluate(() => window.__publicSmoke.generated);
    const decision = result.decision, configurations = decision.configuracao_modal || [];
    flow.decision = {status: decision.status, component_ids: decision.component_ids,
      knowledge_ids: decision.knowledge_ids, articulation_ids: decision.articulation_ids,
      limitations: decision.informacoes_ausentes, checks_executed: result.execution_evidence.checks.length,
      participant_coverage: decision.participant_coverage,
      configurations: configurations.map(item => ({id: item.component_id, availability: item.availability_status,
        knowledge_ids: item.knowledge_ids, criterion_ids: item.criterion_ids, conditions: item.conditions}))};
    check(view + '_actual_partial_conditional_decision',
      decision.status === 'GERADA_PARCIAL' && configurations.length > 0 &&
      configurations.some(item => item.availability_status === 'CONDICIONAL_A_CONFIRMACAO') &&
      result.execution_evidence.checks.some(item => item.outcome === 'PENDING'));
    const selectedKnowledge = new Set(decision.knowledge_ids);
    const selectedCriteria = new Set(decision.criterion_ids);
    const supportRows = result.execution_evidence.supports || [];
    check(view + '_each_choice_has_exact_executed_foundation', configurations.every(configuration => {
      const supports = supportRows.filter(item => item.component_id === configuration.component_id);
      return supports.length > 0 && supports.every(item => selectedCriteria.has(item.criterion_id) &&
        item.knowledge_ids.length > 0 && item.knowledge_ids.every(id => selectedKnowledge.has(id) &&
          configuration.knowledge_ids.includes(id)) && item.origins.length > 0);
    }));
    check(view + '_conditional_scope_is_not_reported_as_a_confirmed_route',
      decision.participant_coverage.length === 2 && decision.participant_coverage.every(person =>
        !(person.component_ids || []).length) &&
      decision.participant_coverage.some(person => (person.conditional_component_ids || []).length));
    check(view + '_conditional_scope_uses_the_correct_requirement', decision.participant_coverage.every(person =>
      (person.conditional_component_ids || []).every(componentId => {
        const scope = result.execution_evidence.checks.find(item => item.subject_id === componentId &&
          item.rule_id === 'documented_access_requirement_scope');
        return !scope || state.context.access_requirements.some(item => item.participant_id === person.participant_id &&
          scope.expected_ids.includes(item.matrix_id));
      })));
    check(view + '_partial_status_visible', (await page.locator('#orientation-state').innerText()) === 'Apoio para parte do desafio');
    const cards = page.locator('#orientation-main .orientation-step');
    check(view + '_partial_orientation_starts_with_supported_action', await cards.count() === configurations.length &&
      !/^\s*Faltam informa[cç][oõ]es e apoios verificados/i.test(await page.locator('#orientation-main').innerText()) &&
      (await page.locator('#orientation-main .step-action').first().innerText()).trim().length > 20);
    const practical = decision.sintese_pratica.etapas;
    check(view + '_action_steps_keep_the_recorded_source_fragments', practical.length === configurations.length &&
      practical.every(group => group.component_ids.length === 1 && group.passos.length > 0 &&
        group.passos.every(step => {
          const source = configurations.find(item => item.component_id === step.component_id);
          return source && group.component_ids.includes(step.component_id) && step.campo_origem === 'acao' &&
            source.acao.includes(step.fragmento_origem);
        })));
    check(view + '_numbered_steps_stay_inside_each_configuration',
      await page.locator('#orientation-main .action-instructions').count() === configurations.length &&
      await page.locator('#orientation-main > ol').count() === 0);
    for (let i = 0; i < practical.length; i++) {
      if (practical[i].aplicabilidade !== 'CONDICIONAL_A_CONFIRMACAO') continue;
      const text = await cards.nth(i).innerText();
      assert(text.indexOf('Possibilidade') >= 0 && text.indexOf('Possibilidade') < text.indexOf('Como fazer'),
        'Conditional status must precede imperative instructions');
    }
    check(view + '_pending_status_precedes_the_instructions', true);
    await page.locator('#orientation-foundations > summary').click();
    // Native details dispatches toggle asynchronously. Wait for a record from
    // this execution, without pinning a former version's knowledge identifiers.
    await page.locator('#orientation-foundation-body [data-knowledge-id]').first().waitFor({state: 'attached'});
    flow.configuration_groundings = (result.explanation?.configurations || []).map(configuration => ({
      id: configuration.id, supports: configuration.application?.supports,
      construction_knowledge_ids: (configuration.construction?.knowledge || []).map(item => item.id),
      articulation_ids: (configuration.construction?.articulations || []).filter(item => item.mobilized_in_execution === true).map(item => item.id)
    }));
    flow.foundation_record_ids = await page.locator('#orientation-foundation-body [data-knowledge-id]').evaluateAll(nodes =>
      nodes.map(node => node.dataset.knowledgeId));
    const usedKnowledge = [...new Set(supportRows.flatMap(item => item.knowledge_ids))];
    check(view + '_foundation_records_render_the_actual_selected_support',
      usedKnowledge.length > 0 && usedKnowledge.every(id => flow.foundation_record_ids.includes(id)));
    const progress=await page.evaluate(()=>window.__publicSmoke.progress.filter(item=>item.operation==='generate'));
    check(view+'_real_request_progress',progress.some(item=>item.stage==='retrieval'&&item.state==='completed'&&Number.isInteger(item.id))&&
      progress.some(item=>item.stage==='verification'&&item.state==='completed')&&progress.some(item=>item.stage==='composition'&&item.state==='completed'));
    await page.locator('#orientation-sources > summary').click();
    check(view+'_linked_sources_actually_used',await page.locator('#orientation-sources-body a[href^="https://www.w3.org/"]').count()>0&&
      /Não buscou estes documentos na internet/.test(await page.locator('#orientation-sources').innerText()));
    const analysisCount=await page.evaluate(()=>window.__publicSmoke.operations.filter(item=>item==='analyze').length);
    await page.locator('#orientation-result [data-edit-case]').click();
    await page.locator('[data-revision="requester_relation"]').selectOption('seek_guidance');
    await page.locator('[data-revision="objetivo"]').fill('Orientar a pessoa responsável a oferecer acesso ao conteúdo.');
    await page.locator('#save-case').click();await page.locator('#case-review').waitFor({state:'visible',timeout:180000});
    check(view+'_correction_preserves_context_without_reparse',await page.evaluate(()=>window.__publicSmoke.operations.filter(item=>item==='analyze').length)===analysisCount&&
      await page.evaluate(()=>window.__publicSmoke.state.context.requester_relation)==='seek_guidance'&&await page.locator('#generate-orientation').isDisabled());
    await page.locator('#new-case').click();await ready(page);
    await page.locator('#case-narrative').fill('Quero ensinar pessoas muito diferentes a usar o Google Forms.');
    await page.locator('#analyze-case').click();
    await page.locator('#case-understanding').waitFor({state:'visible',timeout:180000});
    check(view+'_forms_recognized_without_teacher_assumption',/formulário/i.test(await page.locator('#understanding-summary').innerText())&&
      !/professor/i.test(await page.locator('#understanding-summary').innerText()));
    await page.locator('#continue-understanding').click();
    if(await page.locator('#case-questions').isVisible())await page.locator('#skip-questions').click();
    await page.locator('#case-review').waitFor({state:'visible'});await page.locator('#edit-case').click();
    await page.locator('[data-revision="objetivo"]').fill('Preencher e conferir as respostas do formulário.');
    await page.locator('[data-revision="requester_relation"]').selectOption('support');
    await page.locator('#save-case').click();await page.locator('#case-review').waitFor({state:'visible',timeout:180000});
    check(view+'_forms_missing_information_is_editable',await page.evaluate(()=>window.__publicSmoke.state.context.objetivo)==='Preencher e conferir as respostas do formulário.'&&
      await page.evaluate(()=>window.__publicSmoke.state.context.requester_relation)==='support');
    await page.reload(); await ready(page);
    check(view + '_reload_discards_case', await page.locator('#case-narrative').inputValue() === '' && await page.locator('#orientation-result').isHidden());
    check(view + '_no_case_storage', await page.evaluate(async () => localStorage.length === 0 && sessionStorage.length === 0 &&
      document.cookie === '' && (await indexedDB.databases()).length === 0 && (await caches.keys()).length === 0));
    await page.close();
  }
  check('no_page_javascript_errors', report.errors.length === 0);
  check('no_cross_origin_browser_requests', report.external_requests.length === 0);
  report.completed = true; report.passed = true;
} catch (error) {
  report.passed = false; report.completed = false;
  report.failure = String(error.stack || error).replaceAll(root, '<PROJECT>').replaceAll(root.replaceAll('\\', '/'), '<PROJECT>').replaceAll('file:///<PROJECT>', '<PROJECT>');
  process.exitCode = 1;
} finally {
  report.finished_at = new Date().toISOString();
  await context?.close(); await browser?.close();
  await fs.writeFile(path.join(root, 'evidence/public-smoke.json'), JSON.stringify(report, null, 2) + '\n', 'utf8');
  console.log(JSON.stringify({passed: report.passed, completed: report.completed, checks: Object.keys(report.checks).length,
    assets: Object.keys(report.assets).length, version: report.version, failure: report.failure || null}));
}
