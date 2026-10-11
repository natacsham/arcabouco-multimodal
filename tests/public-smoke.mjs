// Small real public-site verification. Synthetic input; not a participant session.
// Does not mutate product, use hidden decision APIs, or repeat the local QA suite.
import assert from 'node:assert/strict';
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
    'Synthetic explicit follow-up answers; not an expert session or learning evaluation.',
    'The mathematics topic is contextual. The confirmed operational task is accessible digital-content access, not a complete mathematics-teaching method.',
    'GERADA_PARCIAL does not establish coverage of every participant or guarantee educational benefit.',
    'Microphone accuracy, screen readers, comprehension with users and full WCAG conformance were not tested in this public smoke.',
    'Negative resource phrases in narrative are not treated as verified parser support; the local variant tested unconfirmed reader availability and operation.',
    'This smoke verifies a short partial-answer regression and one complete flow in each presentation; it does not replace the full local regression.'
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
    window.__publicSmoke = {operations: [], state: null, generated: null};
    const NativeWorker = window.Worker;
    window.Worker = class extends NativeWorker {
      constructor(...args) {
        super(...args); this.operations = new Map();
        this.addEventListener('message', event => {
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
  for (const view of ['index.html', 'guiado.html']) {
    const page = await context.newPage(); page.on('pageerror', error => report.errors.push(error.message));
    await page.goto(base + 'amado/' + view, {waitUntil: 'domcontentloaded'}); await ready(page);
    const flow = report.flows[view] = {questions: []};
    check(view + '_real_worker_ready', await page.locator('#analyze-case').isEnabled());
    check(view + '_direct_challenge_heading',(await page.locator('h1').innerText()).trim()==='Qual é o seu desafio de hoje?');
    await page.locator('#case-narrative').fill('Sou docente e quero ensinar um assunto complexo de matemática à minha turma, com dois estudantes surdos e um estudante cego.');
    await page.locator('#analyze-case').click();await page.locator('#case-questions').waitFor({state:'visible',timeout:180000});
    await page.locator('#questions-form input[value="TAR-ORGANIZAR-CONTEUDO-DIGITAL"]').check();
    await page.locator('#answer-questions').click();
    await page.locator('#questions-form [data-question="barreira_ou_necessidade"]').waitFor({state:'visible',timeout:180000});
    const barrier=page.locator('#questions-form input[value="BAR-CONTEUDO-SEM-ESTRUTURA-PERSISTENTE"]');
    const label=barrier.locator('xpath=ancestor::label[1]'),box=await label.boundingBox();assert(box);
    await label.click({position:{x:box.width-12,y:box.height/2}});
    check(view+'_whole_option_selects_one_barrier',await barrier.isChecked()&&await page.locator('#questions-form input:checked').count()===1&&await label.evaluate(element=>getComputedStyle(element).cursor)==='pointer');
    await page.locator('#answer-questions').click();
    await page.waitForFunction(()=>!document.querySelector('#case-review').hidden||document.querySelector('#questions-form [data-question]')?.dataset.question!=='barreira_ou_necessidade',{}, {timeout:20000});
    check(view+'_single_barrier_answer_advances',true);
    await page.locator('#new-case').click();await ready(page);
    await page.locator('#case-narrative').fill('Sou docente e quero ensinar um assunto complexo de matemática à minha turma, com dois estudantes surdos e um estudante cego.');
    await page.locator('#analyze-case').click(); await page.locator('#case-questions').waitFor({state: 'visible', timeout: 180000});
    const initial = await page.evaluate(() => window.__publicSmoke.state);
    check(view + '_no_inferred_classroom_or_access_technology', initial.context.raw.ambientes.length === 0 &&
      !/Libras|leitor de tela|Braille/i.test(JSON.stringify(initial.context.participantes.map(person => [person.modalidades, person.recursos_operados]))));
    while (await page.locator('#case-questions').isVisible()) {
      const row = page.locator('#questions-form [data-question]'), id = await row.getAttribute('data-question');
      const person = await page.locator('#question-person').innerText(), field = id.split(':')[0];
      const progress=await page.locator('#question-progress').innerText();
      assert(/\d+\s+de\s+\d+/.test(progress),'Progress is available while answering');
      const values = field === 'tarefas' ? ['TAR-ACESSAR-COMPREENDER-CONTEUDO-DIGITAL'] :
        field === 'participantes' ? ['PAPEL-RESPONSAVEL-ADAPTACAO'] :
        field === 'modalidades_disponiveis' ? /surd/i.test(person) ? ['MOD-TEXTO', 'MOD-IMAGEM'] : /ceg/i.test(person) ? ['MOD-AUDIO'] : ['MOD-TEXTO'] :
        field === 'caracteristicas_pessoa' ? /ceg/i.test(person) ? ['CAR-INTERACAO-NAO-VISUAL'] : ['unknown'] :
        field === 'recursos_digitais' ? ['RED-PAGINA-WEB'] : field === 'ambientes' ? ['AMB-SALA-DE-AULA'] :
        field === 'recursos_disponiveis' ? person ? /ceg/i.test(person) ? ['REC-LEITOR-DE-TELA'] : /adapta/i.test(person) ? ['REC-EDITOR-MULTIMIDIA'] : ['unknown'] : [] :
        field === 'apoios_informados' ? [/surd/i.test(person) ? 'O grupo consegue compreender o texto e as imagens usados na atividade. Outros apoios ainda precisam ser conferidos.' :
          'O estudante usa leitura em voz do conteúdo pelo leitor de tela e pode pedir a retomada da informação.'] : [];
      if (field === 'recursos_disponiveis' && !person)
        for (const candidate of ['REC-COMPUTADOR', 'REC-LEITOR-DE-TELA', 'REC-EDITOR-MULTIMIDIA'])
          if (await row.locator('input[value="' + candidate + '"]').count()) values.push(candidate);
      if (field === 'barreira_ou_necessidade')
        for (const candidate of ['NEC-ACESSO-EQUIVALENTE', 'NEC-ALTERNATIVA-FUNCIONAL-EQUIVALENTE'])
          if (await row.locator('input[value="' + candidate + '"]').count()) values.push(candidate);
      assert(values.length, 'Unexpected question: ' + id);
      if (field === 'apoios_informados') await row.locator('textarea').fill(values[0]);
      else for (const value of values) {
        const control = row.locator('input[value="' + value + '"]'); assert.equal(await control.count(), 1, 'Existing concept ' + value);
        if (!await control.isVisible()) await control.evaluate(element => {
          for (let ancestor = element.parentElement; ancestor; ancestor = ancestor.parentElement) if (ancestor.tagName === 'DETAILS') ancestor.open = true;
        });
        await control.check();
      }
      if(field==='modalidades_disponiveis'&&person&&await row.locator('textarea').count()){
        const note=row.locator('textarea');await note.evaluate(element=>{for(let ancestor=element.parentElement;ancestor;ancestor=ancestor.parentElement)if(ancestor.tagName==='DETAILS')ancestor.open=true;});
        await note.fill(/surd/i.test(person)?'O grupo consegue compreender o texto e as imagens usados na atividade. Outros apoios ainda precisam ser conferidos.':
          'O estudante usa leitura em voz do conteúdo pelo leitor de tela e pode pedir a retomada da informação.');
      }
      flow.questions.push({id, participant_label: person, values,progress});
      assert.equal(new Set(flow.questions.map(item => item.id)).size, flow.questions.length, 'No repeated question');
      assert(flow.questions.length <= 20, 'Intake terminates');
      await page.locator('#answer-questions').click();
      await page.waitForFunction(previous => !document.querySelector('#case-review').hidden ||
        document.querySelector('#questions-form [data-question]')?.dataset.question !== previous, id, {timeout: 180000});
    }
    const state = await page.evaluate(() => window.__publicSmoke.state);
    flow.participants = state.participations.filter(person => person.papel_id === 'PAPEL-ESTUDANTE');
    check(view + '_groups_and_task_preserved', flow.participants.some(person => /surd/i.test(person.label) && person.quantidade === 2) &&
      flow.participants.some(person => /ceg/i.test(person.label) && person.quantidade === 1) &&
      JSON.stringify(state.context.raw.tarefas) === JSON.stringify(['TAR-ACESSAR-COMPREENDER-CONTEUDO-DIGITAL']));
    check(view + '_explicit_confirmation_required', await page.locator('#generate-orientation').isDisabled());
    await page.locator('#case-confirmed').check(); await page.locator('#generate-orientation').click();
    await page.locator('#orientation-result').waitFor({state: 'visible', timeout: 180000});
    const result = await page.evaluate(() => window.__publicSmoke.generated);
    flow.decision = {status: result.decision.status, component_ids: result.decision.component_ids,
      knowledge_ids: result.decision.knowledge_ids, articulation_ids: result.decision.articulation_ids,
      limitations: result.decision.informacoes_ausentes, checks_executed: result.execution_evidence.checks.length};
    check(view + '_actual_partial_decision_and_exact_grounds', flow.decision.status === 'GERADA_PARCIAL' &&
      JSON.stringify(flow.decision.component_ids) === JSON.stringify(['PAD-CONTEUDO-WEB-EQUIVALENTE']) &&
      JSON.stringify([...flow.decision.knowledge_ids].sort()) === JSON.stringify(['K10', 'K42']) &&
      JSON.stringify(flow.decision.articulation_ids) === JSON.stringify(['ART-REF-03']) && flow.decision.checks_executed > 0);
    check(view + '_partial_status_visible', (await page.locator('#orientation-state').innerText()) === 'Apoio para parte do desafio');
    check(view+'_partial_orientation_starts_with_supported_action',await page.locator('#orientation-main .orientation-step').count()>0&&
      !/^\s*Faltam informa[cç][oõ]es e apoios verificados/i.test(await page.locator('#orientation-main').innerText())&&
      (await page.locator('#orientation-main .step-action').first().innerText()).trim().length>20);
    await page.locator('#orientation-foundations > summary').click();
    // Native details dispatches toggle asynchronously after the click. Wait for
    // this execution's record, not a delay or a prepared/global catalogue.
    await page.locator('#orientation-foundation-body [data-knowledge-id="K10"]').first().waitFor({state: 'attached'});
    flow.configuration_groundings = (result.explanation?.configurations || []).map(configuration => ({
      id: configuration.id, supports: configuration.application?.supports,
      construction_knowledge_ids: (configuration.construction?.knowledge || []).map(item => item.id),
      articulation_ids: (configuration.construction?.articulations || []).filter(item => item.mobilized_in_execution === true).map(item => item.id)
    }));
    // Identifiers are deliberately inside collapsed technical details. Inspect
    // the rendered records rather than requiring jargon in the visible summary.
    flow.foundation_record_ids = await page.locator('#orientation-foundation-body [data-knowledge-id]').evaluateAll(nodes =>
      nodes.map(node => node.dataset.knowledgeId));
    check(view + '_foundation_records_render', flow.foundation_record_ids.includes('K10') && flow.foundation_record_ids.includes('K42'));
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
