// Local, synthetic documentation checks. Never a participant-session record.
import fs from 'node:fs/promises';
import path from 'node:path';
import http from 'node:http';
import assert from 'node:assert/strict';
import crypto from 'node:crypto';
import {fileURLToPath, pathToFileURL} from 'node:url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const web = path.join(root, 'web'), prefix = '/arcabouco-multimodal/';
const artifacts = path.join(root, 'tests/.artifacts/source-catalog');
const reportPath = path.join(root, 'evidence/source-catalog-browser.json');
const modules = process.env.AMADO_NODE_MODULES || path.join(process.env.USERPROFILE,
  '.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules');
const {chromium} = await import(pathToFileURL(path.join(modules, 'playwright/index.mjs')).href);
const mime = {'.html':'text/html; charset=utf-8','.js':'text/javascript','.css':'text/css',
  '.json':'application/json','.svg':'image/svg+xml','.png':'image/png'};
const server = http.createServer(async (req,res) => {
  try {
    const pathname = decodeURIComponent(new URL(req.url,'http://localhost').pathname);
    if (pathname === '/favicon.ico') { res.writeHead(204).end(); return; }
    if (!pathname.startsWith(prefix)) { res.writeHead(404).end(); return; }
    let relative = pathname.slice(prefix.length);
    if (!relative || relative.endsWith('/')) relative += 'index.html';
    const file = path.resolve(web,relative);
    if (!file.startsWith(web + path.sep)) { res.writeHead(403).end(); return; }
    res.writeHead(200,{'Content-Type':mime[path.extname(file)] || 'application/octet-stream',
      'Cache-Control':'no-store'}).end(await fs.readFile(file));
  } catch { res.writeHead(404).end(); }
});
await new Promise(resolve => server.listen(0,'127.0.0.1',resolve));
const base = `http://127.0.0.1:${server.address().port}${prefix}`;
const catalog = JSON.parse(await fs.readFile(path.join(web,'assets/source-catalog.json'),'utf8'));
const pilot = JSON.parse(await fs.readFile(path.join(web,'assets/explanation-pilot.json'),'utf8'));
const report = {version:catalog.base_version, type:'SYNTHETIC_DOCUMENTATION_BROWSER_CHECK',
  executed_at:new Date().toISOString(), checks:{}, errors:[], external_requests:[], screenshots:[],
  build:JSON.parse(await fs.readFile(path.join(web,'amado/manifest.json'),'utf8')),
  hashes:Object.fromEntries(await Promise.all(['web/source-path.js','web/ontologia/index.html',
    'web/site.css','web/assets/source-catalog.json','web/assets/explanation-pilot.json',
    'tests/source-catalog-browser.mjs'].map(async name => [name,
      crypto.createHash('sha256').update(await fs.readFile(path.join(root,name))).digest('hex')]))),
  limitations:['Não representa validação humana nem conformidade WCAG integral.',
    'NVDA, VoiceOver e TalkBack não testados.','Links externos conferidos sintaticamente; não acessados pelo teste.',
    'Capturas e verificações são da interface local sob subcaminho, não do endereço publicado.']};
const browser = await chromium.launch({headless:true, executablePath:process.env.AMADO_CHROMIUM ||
  path.join(process.env.LOCALAPPDATA,'ms-playwright/chromium-1243/chrome-win64/chrome.exe')});
report.browser = browser.version();
const context = await browser.newContext({viewport:{width:1280,height:900},reducedMotion:'reduce'});
const requests = [];
let failCatalog = false;
await context.route('**/*', route => {
  const url = route.request().url(); requests.push(url);
  if (!url.startsWith(new URL(base).origin + '/')) {
    report.external_requests.push(url); return route.abort();
  }
  if (failCatalog && url.endsWith('/assets/source-catalog.json')) {
    return route.fulfill({status:503,contentType:'application/json',body:'{}'});
  }
  return route.continue();
});
const page = await context.newPage();
page.on('pageerror', error => report.errors.push(error.message));
const check = (name,value) => { report.checks[name] = Boolean(value); assert(value,name); };
async function reflow(name) {
  const result = await page.evaluate(() => ({viewport:innerWidth,width:document.documentElement.scrollWidth}));
  report.layout ??= {}; report.layout[name] = result;
  check(name, result.width <= result.viewport + 1);
}
async function openWithKeyboard(selector) {
  const summary = page.locator(`${selector} > summary`);
  await summary.focus(); await page.keyboard.press('Enter');
  await page.locator(`${selector}[open]`).waitFor();
  return summary;
}
async function shot(name) {
  await fs.mkdir(artifacts,{recursive:true});
  const file = path.join(artifacts,name);
  await page.screenshot({path:file,fullPage:false,animations:'disabled'});
  report.screenshots.push(path.relative(root,file).replaceAll('\\','/'));
}

try {
  check('catalogue_version_matches_current_build', catalog.base_version === report.build.version);
  check('documentation_hashes_match_current_build', Object.entries(report.hashes)
    .filter(([name]) => name.startsWith('web/'))
    .every(([name, hash]) => report.build.site_assets_sha256?.[name.slice(4)] === hash));
  await page.goto(base + 'ontologia/',{waitUntil:'networkidle'});
  check('catalogue_and_pilot_loaded_lazily', !requests.some(url => /assets\/(source-catalog|explanation-pilot)\.json$/.test(url)));
  const pathSummary = await openWithKeyboard('[data-source-path-details]');
  await page.locator('[data-source-path] .source-stages').waitFor();
  check('path_loaded_from_prepared_public_pilot', requests.some(url => url.endsWith('/assets/explanation-pilot.json')));
  check('keyboard_focus_preserved_after_path_load', await pathSummary.evaluate(el => document.activeElement === el));
  const focusStyle = await pathSummary.evaluate(el => ({style:getComputedStyle(el).outlineStyle,width:getComputedStyle(el).outlineWidth}));
  report.focus = focusStyle;
  check('summary_has_visible_focus_style', focusStyle.style !== 'none' && parseFloat(focusStyle.width) >= 2);
  const pathText = await page.locator('[data-source-path]').innerText();
  check('blocked_articulation_not_presented_as_used', !pathText.includes('ART-TESTE-NAO-CONFIRMADA'));
  const active = pilot.explanation.configurations[0].construction.articulations
    .filter(a => a.mobilized_in_execution === true && a.habilitada_para_decisao !== false);
  check('count_matches_active_articulations', pathText.includes(`${active.length} articulações documentadas`));
  const catalogSummary = await openWithKeyboard('[data-source-catalog-details]');
  await page.locator('#source-publication').waitFor();
  check('catalogue_loaded_from_derived_projection', requests.some(url => url.endsWith('/assets/source-catalog.json')));
  check('keyboard_focus_preserved_after_catalogue_load', await catalogSummary.evaluate(el => document.activeElement === el));
  const select = page.locator('#source-publication');
  await select.focus(); await page.keyboard.press('ArrowDown'); await page.keyboard.press('Enter');
  const selected = await select.inputValue();
  const expected = catalog.references.filter(reference => reference.fonte_que_cita_id === selected);
  check('publication_can_be_selected_with_keyboard', Boolean(selected) && expected.length > 0);
  const references = page.locator('[data-source-references] > li');
  check('reference_count_matches_source_id', await references.count() === expected.length);
  check('reference_count_has_status_semantics', await page.locator('[data-source-count]').getAttribute('role') === 'status');
  check('citations_do_not_imply_operational_promotion', (await references.first().innerText()).includes('Referência citada, sem promoção automática a conhecimento.'));
  const referenceState = references.first().locator('details > summary');
  await referenceState.focus(); await page.keyboard.press('Enter');
  check('reference_state_preserves_canonical_promotion_code', (await references.first().innerText()).includes(expected[0].audit?.promotion_status || 'BIBLIOGRAFIA_CITADA'));
  await page.keyboard.press('Enter');
  await reflow('desktop_reflow_1280');
  const links = await page.locator('[data-source-path] a, [data-source-catalog] a').evaluateAll(elements =>
    elements.map(el => ({href:el.href,label:el.textContent.trim()})));
  check('rendered_links_use_http_https_only', links.every(({href,label}) => {
    const url = new URL(href); return ['http:','https:'].includes(url.protocol) && !url.username && !url.password && label;
  }));
  await page.locator('[data-source-catalog-details]').evaluate(el => { el.open = false; });
  await page.locator('[data-source-path-details]').scrollIntoViewIfNeeded();
  await shot('desktop.png');
  for (let n=0; n<4; n++) await page.locator('[data-font-increase]').click();
  check('text_amplification_reaches_200_percent', (await page.locator('[data-reading-status]').innerText()).includes('200%'));
  await reflow('text_200_percent_reflow_1280');
  await page.locator('[data-font-reset]').click();
  await page.setViewportSize({width:320,height:900});
  await reflow('mobile_reflow_320');
  await page.locator('[data-source-catalog-details]').evaluate(el => { el.open = true; });
  await page.locator('#source-publication').scrollIntoViewIfNeeded();
  await reflow('mobile_catalogue_reflow_320');
  await shot('mobile.png');

  await page.setViewportSize({width:1280,height:900});
  failCatalog = true;
  await page.goto(base + 'ontologia/',{waitUntil:'networkidle'});
  await openWithKeyboard('[data-source-catalog-details]');
  await page.locator('[data-source-catalog] [role=status]').waitFor();
  check('loading_failure_has_retry_instructions', (await page.locator('[data-source-catalog]').innerText()).includes('Feche e abra'));
  check('loading_failure_clears_busy_state', await page.locator('[data-source-catalog]').getAttribute('aria-busy') === null);
  await page.locator('[data-source-catalog-details] > summary').focus();
  await page.keyboard.press('Enter'); failCatalog = false; await page.keyboard.press('Enter');
  await page.locator('#source-publication').waitFor();
  check('loading_failure_recovers_by_keyboard', await page.locator('#source-publication').isVisible());
  check('no_runtime_original_source_requests', report.external_requests.length === 0);
  check('no_javascript_errors', report.errors.length === 0);
  report.passed = true;
} catch (error) {
  report.passed = false; report.failure = error.stack || String(error); process.exitCode = 1;
} finally {
  await context.close(); await browser.close(); await new Promise(resolve => server.close(resolve));
  await fs.writeFile(reportPath,JSON.stringify(report,null,2));
  console.log(JSON.stringify({passed:report.passed,checks:report.checks,failure:report.failure,
    report:path.relative(root,reportPath).replaceAll('\\','/')}));
}
