// Functional checks of the real Web Worker under a GitHub Pages-like subpath.
import fs from 'node:fs/promises';
import path from 'node:path';
import http from 'node:http';
import assert from 'node:assert/strict';
import { fileURLToPath, pathToFileURL } from 'node:url';
import {coreInvariantAudit, historicalReport, typographySnapshot, assertAmadoTypography, assertFixedViewportDoubling} from './presentation-metrics.mjs';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const web = path.join(root, 'web');
const modules = process.env.AMADO_NODE_MODULES || path.join(process.env.USERPROFILE,'.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules');
const {chromium} = await import(pathToFileURL(path.join(modules,'playwright/index.mjs')).href);
const artifacts = process.env.AMADO_BROWSER_EVIDENCE || path.join(root,'tests','.artifacts','browser');
await fs.mkdir(artifacts,{recursive:true});
const mime = {'.html':'text/html; charset=utf-8','.js':'text/javascript','.mjs':'text/javascript','.css':'text/css','.wasm':'application/wasm','.json':'application/json','.zip':'application/zip','.py':'text/plain; charset=utf-8'};
const server = http.createServer(async(req,res) => {
  try {
    const pathname = decodeURIComponent(new URL(req.url,'http://localhost').pathname);
    if (pathname === '/favicon.ico') { res.writeHead(204).end(); return; }
    if (!pathname.startsWith('/mado/')) { res.writeHead(404).end(); return; }
    let rel = pathname.slice(6);
    if (!rel || rel.endsWith('/')) rel += 'index.html';
    const target = path.resolve(web,rel);
    if (!target.startsWith(web + path.sep)) { res.writeHead(403).end(); return; }
    const contents = await fs.readFile(target);
    res.writeHead(200,{'Content-Type':mime[path.extname(target)] || 'application/octet-stream','Cache-Control':'no-store'}).end(contents);
  } catch { res.writeHead(404).end(); }
});
await new Promise(resolve => server.listen(0,'127.0.0.1',resolve));
const publicURL=process.env.AMADO_PUBLIC_URL || '';
const shellDelta=process.env.AMADO_SHELL_DELTA==='1';
const contentDelta=process.env.AMADO_CONTENT_DELTA==='1';
const guidedDelta=process.env.AMADO_GUIDED_DELTA==='1';
const editorialDelta=process.env.AMADO_EDITORIAL_DELTA==='1';
const origin = publicURL ? new URL(publicURL).origin : `http://127.0.0.1:${server.address().port}`;
const browser = await chromium.launch({headless:true,executablePath:process.env.AMADO_CHROMIUM || path.join(process.env.LOCALAPPDATA,'ms-playwright/chromium-1243/chrome-win64/chrome.exe')});
const context = await browser.newContext({viewport:{width:1280,height:900}});
const external = [], methods = [], errors = [];
let faultMode='', delayObserved=()=>{};
const delayedRoutes=[];
await context.route('**/*',route => {
  const req = route.request();
  if (!req.url().startsWith(origin+'/') && !req.url().startsWith('blob:')) { external.push(req.url()); return route.abort(); }
  methods.push(req.method());
  if (faultMode==='hash' && req.url().endsWith('/manifest.json')) return route.fulfill({contentType:'application/json',body:JSON.stringify({...report.build,bridge_sha256:'0'.repeat(64)})});
  if (faultMode==='network' && req.url().endsWith('/assets/base.zip')) return route.abort('failed');
  if (faultMode==='delay' && req.url().endsWith('/assets/base.zip')) { delayedRoutes.push(route); delayObserved(); return; }
  return route.continue();
});
const page = await context.newPage();
page.on('pageerror',error => errors.push(error.message));
const report = {browser:browser.version(),checks:{},timings:{},external_requests:external,errors,limitations:['NVDA não testado','VoiceOver não testado','Não é avaliação de conformidade WCAG','Tempos de laboratório, sem garantia para dispositivos móveis']};
report.execution_target=publicURL ? 'PUBLIC_SITE' : 'LOCAL_SUBPATH';
if (process.env.AMADO_DEPLOYMENT_COMMIT) report.repository_commit_at_test=process.env.AMADO_DEPLOYMENT_COMMIT;
report.build=JSON.parse(await fs.readFile(path.join(web,'amado','manifest.json'),'utf8'));
const idle = async (target=page) => {
  await target.waitForFunction(() => document.getElementById('main').getAttribute('aria-busy') === 'false',{}, {timeout:180000});
};
function contrast(a,b) {
  const lum=hex=>{
    const c=hex.slice(1).match(/../g).map(x=>parseInt(x,16)/255).map(x=>x<=.04045?x/12.92:((x+.055)/1.055)**2.4);
    return c[0]*.2126+c[1]*.7152+c[2]*.0722;
  };
  return (Math.max(lum(a),lum(b))+.05)/(Math.min(lum(a),lum(b))+.05);
}
// Declared CSS pairs, including focus against adjacent surfaces. This is a
// measured palette sample, not a substitute for a full accessibility audit.
const palette=[
  ['body','#142f37','#f3f7f8',4.5],['surface','#142f37','#ffffff',4.5],
  ['primary button','#ffffff','#075b70',4.5],['header','#ffffff','#063d4a',4.5],
  ['secondary button','#073f4c','#d6ebef',4.5],['help','#304e55','#ffffff',4.5],
  ['summary muted','#405c64','#ffffff',4.5],['optional','#485f66','#ffffff',4.5],
  ['role','#0c6275','#ffffff',4.5],['status available','#124f2a','#dff2e5',4.5],
  ['status conditional','#664700','#fff0bd',4.5],['status blocked','#7d1d08','#fbe2dc',4.5],
  ['error','#7d1818','#fff4f4',4.5],['focus surface','#bd4b00','#ffffff',3],
  ['focus soft','#bd4b00','#e7f4f6',3],['focus added','#bd4b00','#f1eaff',3],
  ['focus header','#ffffff','#063d4a',3],['input border','#5f858f','#ffffff',3],
  ...['#075b70','#6f3c8f','#7b4b00','#176b3a','#8b4700','#65502c','#2f5f8f','#354f85'].map(bg=>['graph '+bg,'#ffffff',bg,4.5]),
  ['high contrast text','#000000','#ffffff',4.5],['high contrast button','#ffffff','#004254',4.5],
  ['high contrast focus','#c53b00','#dff6ff',3]
];
report.palette_contrast=palette.map(([name,foreground,background,minimum])=>({name,foreground,background,ratio:contrast(foreground,background),minimum}));
async function generateFree() {
  await page.locator('#free-confirmed').check();
  const started = Date.now();
  await page.locator('#generate-free').click(); await idle();
  assert.equal(await page.locator('#runtime-error').textContent(),'');
  assert.equal(await page.locator('#health').getAttribute('role'),'status');
  assert.equal(await page.locator('#runtime-error').getAttribute('role'),'alert');
  assert.equal(await page.locator('#speech-status').getAttribute('role'),'status');
  assert(await page.getByRole('tab',{name:'Testar outro caso'}).count());
  assert(await page.getByRole('button',{name:/Limpar caso/}).count());
  report.checks.accessible_progress_and_control_names=true;
  assert(report.palette_contrast.every(row=>row.ratio>=row.minimum));
  report.checks.measured_palette_contrast=true;
  return Date.now()-started;
}
try {
  if(editorialDelta){
    report.core_invariants=await coreInvariantAudit(root);
    report.historical_baseline=historicalReport(root,'evidence/browser-report.json');
  }
  if (publicURL || process.env.AMADO_DELTA_ONLY === '1' || shellDelta || contentDelta || guidedDelta || editorialDelta) {
    const directedURL=publicURL || origin+'/mado/amado/';
    if (publicURL) report.public_url=publicURL;
    const loadStarted=Date.now();
    if(shellDelta){
      faultMode='delay';
      const loadingAsset=new Promise(resolve=>{delayObserved=resolve;});
      await page.goto(directedURL);
      await Promise.race([loadingAsset,new Promise((_,reject)=>setTimeout(()=>reject(new Error('Loading asset interception not reached')),30000))]);
      assert.equal(await page.locator('#main').getAttribute('aria-busy'),'true');
      assert.equal(await page.locator('#clear-case').isEnabled(),true);
      assert.equal(await page.locator('#stop-speech').isEnabled(),true);
      assert.equal(await page.locator('[data-font-increase]').isEnabled(),true);
      assert.equal(await page.locator('[data-site-contrast]').isEnabled(),true);
      report.loading_status=await page.locator('#health').evaluate(el=>({text:el.textContent,role:el.getAttribute('role'),state:el.dataset.state,background:getComputedStyle(el).backgroundColor,border:getComputedStyle(el).borderLeftColor}));
      assert.equal(report.loading_status.role,'status');
      assert.equal(report.loading_status.state,'loading');
      assert(report.loading_status.text.trim().length>0);
      await page.locator('[data-font-increase]').click();
      assert.equal(await page.locator('html').evaluate(el=>parseFloat(getComputedStyle(el).fontSize)),20);
      await page.locator('[data-font-reset]').click();
      await page.locator('[data-site-contrast]').click();
      assert.equal(await page.locator('html').getAttribute('data-contrast'),'high');
      await page.locator('[data-site-contrast]').click();
      report.checks.reading_controls_usable_during_loading=true;
      report.checks.loading_status_announced=true;
      faultMode='';for(const route of delayedRoutes.splice(0))await route.continue().catch(()=>{});
      await idle();
      report.ready_status=await page.locator('#health').evaluate(el=>({text:el.textContent,role:el.getAttribute('role'),state:el.dataset.state,background:getComputedStyle(el).backgroundColor,border:getComputedStyle(el).borderLeftColor}));
      assert.notEqual(report.ready_status.text,report.loading_status.text);
      assert.equal(report.ready_status.state,'ready');
      assert.notEqual(report.ready_status.background,report.loading_status.background);
      report.checks.ready_and_loading_messages_distinct=true;
    }else{await page.goto(directedURL);await idle();}
    assert.match(await page.locator('#health').textContent(),/AMADO pronto/);
    assert.equal(await page.locator('#runtime-error').textContent(),'');
    report.timings.public_load_ms=Date.now()-loadStarted;
    const deployedManifest=await page.evaluate(()=>fetch('./manifest.json',{cache:'no-store'}).then(response=>response.json()));
    for (const key of ['core_sha256','bridge_sha256','base_zip_sha256','frontend_sha256','site_assets_sha256','files']) assert.deepEqual(deployedManifest[key],report.build[key]);
    report.checks.published_assets_match_verified_build=true;
    await page.locator('#reported-step input[value="yes"]').check();
    await page.locator('#confirm-reported').click(); await idle();
    await page.locator('#mapping-confirmed').check();
    const generationStarted=Date.now();
    await page.locator('#generate-known').click(); await idle();
    assert.equal(await page.locator('#decision-status').textContent(),'Orientação construída');
    assert.equal(await page.locator('#modal-configuration .mode-card').count(),7);
    report.timings.public_generation_ms=Date.now()-generationStarted;
    report.checks.public_interview_seven_configurations=true;
    if(editorialDelta){
      const before=await typographySnapshot(page);assertAmadoTypography(before);
      for(let n=0;n<4;n++)await page.locator('[data-font-increase]').click();
      const after=await typographySnapshot(page);
      report.typography={desktop:before,desktop_200:after,desktop_ratios:assertFixedViewportDoubling(before,after)};
      assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));
      await page.locator('[data-font-reset]').click();
      report.checks.original_typography_and_fixed_viewport_doubling=true;
    }
    if (process.env.AMADO_DELTA_ONLY === '1' || shellDelta) {
      // No voice is synthesized here; this checks the stop control's action
      // while the real worker is busy, without an OS-voice dependency.
      await page.evaluate(()=>{
        window.amadoCancelCalls=0;
        const original=window.speechSynthesis.cancel.bind(window.speechSynthesis);
        window.speechSynthesis.cancel=()=>{window.amadoCancelCalls++;original();};
      });
      await page.locator('#organized-step > summary').click();
      await page.locator('#generate-known').click();
      assert.equal(await page.locator('#main').getAttribute('aria-busy'),'true');
      assert.equal(await page.locator('#generate-known').isDisabled(),true);
      assert.equal(await page.locator('#stop-speech').isEnabled(),true);
      if(shellDelta){
        assert.equal(await page.locator('[data-font-increase]').isEnabled(),true);
        assert.equal(await page.locator('[data-site-contrast]').isEnabled(),true);
        assert.equal(await page.locator('#clear-case').isEnabled(),true);
        report.checks.reading_controls_usable_during_generation=true;
      }
      await page.locator('#stop-speech').click();
      assert.equal(await page.evaluate(()=>window.amadoCancelCalls),1);
      assert.equal(await page.locator('#speech-status').textContent(),'Leitura interrompida.');
      await idle();
      assert.equal(await page.locator('#modal-configuration .mode-card').count(),7);
      assert.equal(await page.locator('#runtime-error').textContent(),'');
      report.checks.stop_speech_remains_operable_while_busy=true;
      report.checks.repeated_generation_preserves_seven_configurations=true;
    }
    await page.locator('#practical-summary').screenshot({path:path.join(artifacts,'public-orientation.png')});
    await page.emulateMedia({reducedMotion:'reduce'});
    await page.setViewportSize({width:320,height:900});
    await page.evaluate(()=>{window.scrollTo({top:0,behavior:'instant'});});
    await page.evaluate(()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve))));
    assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
    await page.screenshot({path:path.join(artifacts,'public-mobile.png')});
    report.checks.public_mobile_reflow_reduced_motion=true;
    if(editorialDelta){
      const before=await typographySnapshot(page);assertAmadoTypography(before,true);
      for(let n=0;n<4;n++)await page.locator('[data-font-increase]').click();
      const after=await typographySnapshot(page);
      report.typography.mobile=before;report.typography.mobile_200=after;
      report.typography.mobile_ratios=assertFixedViewportDoubling(before,after);
      assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));
      await page.screenshot({path:path.join(artifacts,'editorial-mobile-200.png')});
      await page.locator('[data-font-reset]').click();
      report.checks.original_mobile_typography_200_preserves_content=true;
    }
    await page.setViewportSize({width:1280,height:900});
    await page.locator('#free-tab').click(); await idle();
    if(shellDelta){
      assert.equal(await page.locator('#health').getAttribute('data-state'),'ready');
      report.checks.tab_switch_returns_ready_status=true;
    }
    await page.locator('#template-select').selectOption('CTX-DEMO-WEB-LEITOR-TELA'); await idle();
    await generateFree();
    assert.equal(await page.locator('#decision-status').textContent(),'Orientação construída');
    report.checks.public_screen_reader_example=true;
    await page.locator('#clear-case').click(); await idle();
    assert.equal(await page.locator('#saida').isVisible(),false);
    report.checks.public_clear_discards_case=true;
  } else {
  if (process.env.AMADO_PROBES_ONLY !== '1' && process.env.AMADO_RECOVERY_ONLY !== '1') {
  let started = Date.now();
  await page.goto(origin+'/mado/amado/');
  await page.keyboard.press('Tab');
  assert.equal(await page.locator(':focus').textContent(),'Ir para o conteúdo');
  await page.keyboard.press('Enter');
  assert.equal(await page.locator(':focus').getAttribute('id'),'main');
  await idle();
  assert.match(await page.locator('#health').textContent(),/AMADO pronto/);
  assert.equal(await page.locator('#runtime-error').textContent(),'');
  report.timings.initial_load_ms=Date.now()-started;
  report.checks.subpath_and_keyboard_skip=true;
  assert.equal(await page.locator('.dictate:not(:disabled)').count(),0);
  report.checks.remote_dictation_disabled=true;
  await page.locator('#known-tab').focus(); await page.keyboard.press('End'); await idle();
  assert.equal(await page.locator(':focus').getAttribute('id'),'free-tab');
  assert.equal(await page.locator('#free-tab').getAttribute('aria-selected'),'true');
  await page.keyboard.press('Home'); await idle();
  assert.equal(await page.locator(':focus').getAttribute('id'),'known-tab');
  report.checks.keyboard_tab_navigation=true;
  await page.locator('#organized-step > summary').click();
  await page.locator('#generate-known').click(); await idle();
  assert.equal(await page.locator('#saida').isVisible(),false);
  assert.match(await page.locator('#runtime-error').textContent(),/Confira/);
  report.checks.confirmation_required=true;
  await page.locator('#reported-step input[value="yes"]').check();
  await page.locator('#confirm-reported').click(); await idle();
  await page.locator('#mapping-confirmed').check();
  started=Date.now();
  await page.locator('#generate-known').click(); await idle();
  report.timings.interview_ms=Date.now()-started;
  assert.match(await page.locator('#decision-status').textContent(),/Orientação construída/);
  assert.equal(await page.locator('#modal-configuration .mode-card').count(),7);
  assert.equal(await page.locator(':focus').getAttribute('id'),'decision-title');
  report.checks.interview_seven_configurations=true;
  await page.screenshot({path:path.join(artifacts,'interview.png'),fullPage:true});
  for (const [id,key] of [['CTX-DEMO-MOB-RUIDO','mobility'],['CTX-DEMO-WEB-LEITOR-TELA','screen_reader'],['CTX-DEMO-COMUNICACAO-MULTIFORMATO','communication']]) {
    if (await page.locator('#free-panel').isHidden()) { await page.locator('#free-tab').click(); await idle(); }
    await page.locator('#template-select').selectOption(id); await idle();
    report.timings[key+'_ms']=await generateFree();
    assert.equal(await page.locator('#decision-status').textContent(),'Orientação construída');
    report.checks[key]=true;
    if (key === 'mobility') {
      assert.equal(await page.locator('#modal-configuration .mode-card').count(),2);
      await page.locator('#trace-details > summary').click();
      assert(await page.locator('.trace-step').count()>=7);
      const concepts=await page.locator('.trace-step').allTextContents();
      assert(concepts.some(s=>s.includes('Origem')));
      report.checks.trace_concepts_and_relations=true;
      assert.match(await page.locator('#trace-details').textContent(),/Texto do item original não redistribuído/);
      assert(!await page.locator('#trace-details').textContent().then(text=>text.includes('undefined')));
      report.checks.public_source_disclosure=true;
      await page.screenshot({path:path.join(artifacts,'mobility-trace.png'),fullPage:true});
      await page.locator('#free-interpretation > summary').click();
      await page.locator('#free-interpretation details.foundation > summary').click();
      await page.locator('#free-controlled-fields details[data-group="recursos_impedidos"] > summary').click();
      await page.locator('#free-controlled-fields input[data-field="recursos_impedidos"][value="REC-VIBRACAO"]').check();
      assert.equal(await page.locator('#saida').isVisible(),false);
      await generateFree();
      assert.equal(await page.locator('#modal-configuration .mode-card').count(),1);
      report.checks.resource_change_removes_configuration=true;
    }
  }
  // No history survives a switch; current forms and outcome are discarded.
  await page.locator('#known-tab').click(); await idle();
  await page.locator('#free-tab').click(); await idle();
  assert.equal(await page.locator('#free-narrative').inputValue(),'');
  assert.equal(await page.locator('#saida').isVisible(),false);
  report.checks.tab_switch_discards_case=true;
  await page.locator('#free-narrative').fill('Uma pessoa precisa de ajuda. MARCADOR-PRIVACIDADE');
  await page.locator('#organize-narrative').click(); await idle();
  assert(await page.locator('#free-missing li').count()>0);
  await generateFree();
  assert.equal(await page.locator('#decision-status').textContent(),'Decisão suspensa');
  report.checks.unknown_narrative_suspends=true;
  assert.deepEqual(await page.evaluate(()=>({local:localStorage.length,session:sessionStorage.length,cookies:document.cookie})),{local:0,session:0,cookies:''});
  assert.equal(await page.locator('#evaluation-details,.exports').count(),0);
  report.checks.no_storage_or_research_controls=true;
  await page.setViewportSize({width:320,height:900});
  assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
  await page.screenshot({path:path.join(artifacts,'mobile.png'),fullPage:true});
  await page.screenshot({path:path.join(artifacts,'mobile-viewport.png')});
  report.checks.reflow_320=true;
  await page.setViewportSize({width:1280,height:900});
  await page.locator('#font-button').click(); await page.locator('#font-button').click();
  assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
  report.checks.text_enlargement=true;
  await page.locator('#clear-case').click(); await idle();
  assert.equal(await page.locator('#free-narrative').inputValue(),'');
  assert(!await page.locator('body').innerText().then(t=>t.includes('MARCADOR-PRIVACIDADE')));
  assert.equal(await page.locator('#saida').isVisible(),false);
  report.checks.clear_destroys_current=true;
  await page.reload(); await idle();
  assert.equal(await page.locator('#free-narrative').inputValue(),'');
  report.checks.refresh_does_not_restore=true;
  // Two simultaneous tabs share only public asset downloads, never a case.
  const second=await context.newPage();
  second.on('pageerror',error=>errors.push(error.message));
  await second.goto(origin+'/mado/amado/'); await idle(second);
  await second.locator('#free-tab').click(); await idle(second);
  await second.locator('#template-select').selectOption('CTX-DEMO-COMUNICACAO-MULTIFORMATO'); await idle(second);
  await second.locator('#free-confirmed').check();
  await page.locator('#reported-step input[value="yes"]').check();
  await page.locator('#confirm-reported').click(); await idle();
  await page.locator('#mapping-confirmed').check();
  if (!(await page.locator('#organized-step').evaluate(node=>node.open))) await page.locator('#organized-step > summary').click();
  const concurrentStart=Date.now();
  await Promise.all([page.locator('#generate-known').click(),second.locator('#generate-free').click()]);
  await Promise.all([idle(),idle(second)]);
  assert.equal(await page.locator('#decision-status').textContent(),'Orientação construída');
  assert.equal(await second.locator('#decision-status').textContent(),'Orientação construída');
  assert.equal(await page.locator('#modal-configuration .mode-card').count(),7);
  assert.equal(await second.locator('#modal-configuration .mode-card').count(),1);
  const secondDecision=await second.locator('#decision-content').textContent();
  await page.locator('#clear-case').click(); await idle();
  assert.equal(await page.locator('#saida').isVisible(),false);
  assert.equal(await second.locator('#decision-content').textContent(),secondDecision);
  assert.equal(await second.locator('#saida').isVisible(),true);
  report.timings.two_tabs_ms=Date.now()-concurrentStart;
  report.checks.simultaneous_tabs_isolated=true;
  await second.close();
  } else if (process.env.AMADO_RECOVERY_ONLY !== '1') { await page.goto(origin+'/mado/amado/'); await idle(); }
  if (process.env.AMADO_SKIP_PROBES !== '1' && process.env.AMADO_RECOVERY_ONLY !== '1') {
    // A separate worker checks real structured inputs, independently of narration.
    await page.evaluate(() => {
      window.amadoProbeWorker=new Worker('./worker.mjs',{type:'module'});
      window.amadoProbePending=new Map(); window.amadoProbeSequence=0;
      window.amadoProbeWorker.onmessage=({data})=>{
        const item=window.amadoProbePending.get(data.id);
        if (!item) return;
        window.amadoProbePending.delete(data.id); clearTimeout(item.timer);
        if (data.type==='error') item.reject(new Error(data.error)); else item.resolve(data.data);
      };
      window.amadoProbe=payload=>new Promise((resolve,reject)=>{
        const id=++window.amadoProbeSequence;
        const timer=setTimeout(()=>reject(new Error('Tempo excedido na prova estruturada.')),180000);
        window.amadoProbePending.set(id,{resolve,reject,timer});
        window.amadoProbeWorker.postMessage({id,...payload});
      });
    });
    const fixtures=[
      ['principal','CTX-TRANSFERENCIA-RECURSO-DIGITAL-01'],
      ['principal_sem_jogo','CTX-TRANSFERENCIA-RECURSO-DIGITAL-01'],
      ['leitor_tela','CTX-DEMO-WEB-LEITOR-TELA'],
      ['mobilidade_ruido','CTX-DEMO-MOB-RUIDO'],
      ['comunicacao','CTX-DEMO-COMUNICACAO-MULTIFORMATO'],
      ['diagnostico_isolado','CTX-TESTE-RC2-DIAGNOSTICO-ISOLADO'],
      ['sem_confirmacao','CTX-TRANSFERENCIA-RECURSO-DIGITAL-01'],
    ];
    const decisions={};
    report.runtime=await page.evaluate(()=>window.amadoProbe({operation:'initialize'}));
    await page.evaluate(()=>window.amadoProbe({operation:'clear'}));
    const freshCatalog=await page.evaluate(()=>window.amadoProbe({operation:'catalog'}));
    assert(freshCatalog.templates.length>=4);
    report.checks.clear_keeps_readonly_base_available=true;
    for (const [id,template] of fixtures) {
      const state=await page.evaluate(template=>window.amadoProbe({operation:'start',template}),template);
      {
        const payload={mapping_confirmed:id!=='sem_confirmacao',transfer_confirmed:id!=='sem_confirmacao'};
        if (id==='principal_sem_jogo') {
          const raw=state.context.raw;
          payload.recursos_disponiveis=(raw.recursos_disponiveis||[]).filter(x=>x!=='REC-PLATAFORMA-JOGO-QUIZ');
          payload.recursos_propostos=(raw.recursos_propostos||[]).filter(x=>x!=='REC-PLATAFORMA-JOGO-QUIZ');
          payload.recursos_impedidos=[...new Set([...(raw.recursos_impedidos||[]),'REC-PLATAFORMA-JOGO-QUIZ'])];
        }
        await page.evaluate(payload=>window.amadoProbe({operation:'update',payload}),payload);
      }
      const probeStarted=Date.now();
      decisions[id]=await page.evaluate(()=>window.amadoProbe({operation:'generate'}));
      report.timings['probe_'+id+'_ms']=Date.now()-probeStarted;
      console.log(`${id}: ${decisions[id].decision.status}`);
    }
    // Same synthetic controlled combination as the native regression. This is
    // an input fixture, not a copied output or an added composition rule.
    const nativeReport=JSON.parse(await fs.readFile(path.join(root,'evidence','regression-report.json'),'utf8'));
    const novelInput=structuredClone(nativeReport.cases.combinacao_nao_cadastrada.input);
    assert(novelInput.recursos_disponiveis.includes('REC-ENTRADA-VOZ'),'Native input fixture must preserve the original available voice resource.');
    await page.evaluate(()=>window.amadoProbe({operation:'start',template:null}));
    await page.evaluate(payload=>window.amadoProbe({operation:'update',payload}),novelInput);
    decisions.combinacao_nao_cadastrada=await page.evaluate(()=>window.amadoProbe({operation:'generate'}));
    novelInput.recursos_disponiveis=novelInput.recursos_disponiveis.filter(r=>r!=='REC-ENTRADA-VOZ');
    novelInput.recursos_impedidos=['REC-ENTRADA-VOZ'];
    await page.evaluate(payload=>window.amadoProbe({operation:'update',payload}),novelInput);
    decisions.combinacao_sem_voz=await page.evaluate(()=>window.amadoProbe({operation:'generate'}));
    assert.notDeepEqual(decisions.combinacao_nao_cadastrada.decision.component_ids,decisions.combinacao_sem_voz.decision.component_ids);
    report.checks.novel_combination_and_resource_change=true;
    await fs.writeFile(path.join(artifacts,'decisions.json'),JSON.stringify(decisions,null,2));
    await page.evaluate(()=>window.amadoProbeWorker.terminate());
    report.checks.structured_probes=Object.keys(decisions);
  }
  if (process.env.AMADO_PROBES_ONLY !== '1') {
    for (const mode of ['hash','network']) {
      faultMode=mode;
      await page.goto(origin+'/mado/amado/'); await idle();
      assert((await page.locator('#runtime-error').textContent()).trim().length>0);
      assert.equal(await page.locator('#saida').isVisible(),false);
      assert.equal(await page.locator('#health').getAttribute('data-state'),'error');
      assert.equal(await page.locator('#health').evaluate(el=>el.classList.contains('status')),true);
      report.error_status_samples??={};
      report.error_status_samples[mode]=await page.locator('#health').evaluate(el=>({text:el.textContent,role:el.getAttribute('role'),state:el.dataset.state,background:getComputedStyle(el).backgroundColor,border:getComputedStyle(el).borderLeftColor}));
      report.checks[mode+'_failure_has_distinct_error_state']=true;
      faultMode='';
      await page.locator('#clear-case').click(); await idle();
      assert.equal(await page.locator('#runtime-error').textContent(),'');
      assert.match(await page.locator('#health').textContent(),/AMADO pronto/);
      assert.equal(await page.locator('#health').getAttribute('data-state'),'ready');
      report.checks[mode+'_failure_recovers']=true;
    }
    faultMode='delay';
    const waitingForAsset=new Promise(resolve=>{delayObserved=resolve;});
    await page.goto(origin+'/mado/amado/');
    await Promise.race([waitingForAsset,new Promise((_,reject)=>setTimeout(()=>reject(new Error('Não interceptou o carregamento para testar cancelamento.')),30000))]);
    assert.equal(await page.locator('#main').getAttribute('aria-busy'),'true');
    assert.equal(await page.locator('#clear-case').isEnabled(),true);
    faultMode='';
    await page.locator('#clear-case').click();
    for (const route of delayedRoutes.splice(0)) await route.continue().catch(()=>{});
    await idle();
    assert.equal(await page.locator('#runtime-error').textContent(),'');
    assert.match(await page.locator('#health').textContent(),/AMADO pronto/);
    assert.equal(await page.locator('#saida').isVisible(),false);
    report.checks.cancel_loading_and_reinitialize=true;
  }
  }
  assert.equal(external.length,0); assert(methods.every(m=>m==='GET')); assert.equal(errors.length,0);
  if(editorialDelta){
    assert.deepEqual(await coreInvariantAudit(root),report.core_invariants);
    report.checks.editorial_preserves_semantic_and_runtime_files=true;
  }
  report.checks.no_case_network_requests=true;
  report.completed=true;
} catch(error) {
  report.failure=String(error.stack || error); process.exitCode=1;
  await page.screenshot({path:path.join(artifacts,'failure.png'),fullPage:true});
} finally {
  const reportName=publicURL ? 'public-smoke.json' : editorialDelta ? 'report-editorial-typography.json' : guidedDelta ? 'report-guided-delta.json' : contentDelta ? 'report-content-delta.json' : shellDelta ? 'report-shell-delta.json' : process.env.AMADO_DELTA_ONLY === '1' ? 'report-delta.json' : process.env.AMADO_RECOVERY_ONLY === '1' ? 'report-recovery.json' : process.env.AMADO_PROBES_ONLY === '1' ? 'report-probes.json' : 'report.json';
  await fs.writeFile(path.join(artifacts,reportName),JSON.stringify(report,null,2));
  if (report.completed) {
    const publicPath=path.join(root,'evidence',publicURL ? 'public-smoke.json' : 'browser-report.json');
    const publicReport={...report,type:'SYNTHETIC_BROWSER_REGRESSION_NOT_HUMAN_SESSION',executed_at:new Date().toISOString()};
    if(editorialDelta){
      publicReport.change_verification={
        baseline:report.historical_baseline,
        change:'Revisão editorial e tipográfica; sem mudança no aplicativo, adaptador guiado, motor, base, consultas ou ponte.',
        scope:'Executados nesta revisão: caso principal com sete configurações, exemplo de leitor de tela, limpeza, fontes efetivas a 100/200% em viewport fixo, reflow desktop/320px e ausência de envio do caso. A equivalência de conteúdo, estados, teclado e recuperação da visão guiada são executados separadamente em guided-report.json. Não foram reexecutadas as sondagens semânticas completas.',
        guided_view_report:'guided-report.json',guided_view_verified_by_this_run:false,
        unchanged_semantic_and_runtime_files:report.core_invariants.all_unchanged
      };
      await fs.writeFile(publicPath,JSON.stringify(publicReport,null,2)+'\n');
    }else if(!publicURL && guidedDelta){
      const baseline=JSON.parse(await fs.readFile(path.join(root,'evidence/browser-before-guided-view.json'),'utf8'));
      for(const key of ['core_sha256','bridge_sha256','base_zip_sha256','files'])assert.deepEqual(baseline.build[key],report.build[key]);
      for(const name of ['app.js','styles.css','worker.mjs','client.mjs'])assert.equal(baseline.build.frontend_sha256[name],report.build.frontend_sha256[name]);
      publicReport.change_verification={
        baseline_report:'browser-before-guided-view.json',baseline_build:baseline.build,
        baseline_check_count:Object.values(baseline.checks).filter(x=>x===true).length,
        previous_baseline_report:baseline.change_verification?.baseline_report,
        change:'Seção do problema reorganizada na Home e acesso a uma visão guiada separada do AMADO. Na visão atual, somente navegação e folha adicional para alternar apresentações; app.js, styles.css, worker, cliente, motor, base e consultas preservados.',
        scope:'Regressão dirigida da visão atual: caso principal com sete configurações, exemplo de leitor de tela, reflow, limpeza e ausência de envio do caso. Esta execução não testa a geração da visão guiada, não repete a regressão semântica completa nem os testes de recuperação; esses resultados pertencem a relatórios separados.',
        guided_view_report:'guided-report.json',
        guided_view_verified_by_this_run:false,
        unchanged_engine_base_bridge_queries:true,
        unchanged_amado_app_worker_client_styles:true
      };
      await fs.writeFile(publicPath,JSON.stringify(publicReport,null,2));
    }else if(!publicURL && contentDelta){
      const baseline=JSON.parse(await fs.readFile(path.join(root,'evidence/browser-before-content-refinement.json'),'utf8'));
      for(const key of ['core_sha256','bridge_sha256','base_zip_sha256','files'])assert.deepEqual(baseline.build[key],report.build[key]);
      for(const name of ['app.js','styles.css','worker.mjs','client.mjs'])assert.equal(baseline.build.frontend_sha256[name],report.build.frontend_sha256[name]);
      publicReport.change_verification={
        baseline_report:'browser-before-content-refinement.json',baseline_build:baseline.build,
        baseline_check_count:Object.values(baseline.checks).filter(x=>x===true).length,
        previous_baseline_report:baseline.change_verification?.baseline_report,
        change:'Refinamento editorial da apresentação e da página técnica; no AMADO, somente o nome do link de navegação. Motor, base, ponte, consultas e scripts do instrumento preservados.',
        scope:'Delta de apresentação: execução real do caso principal com sete configurações, exemplo de leitor de tela, reflow e limpeza. A regressão semântica completa e os testes de recuperação pertencem aos relatórios anteriores preservados; não foram repetidos para esta edição de conteúdo.',
        unchanged_engine_base_bridge_queries:true,
        unchanged_amado_app_worker_client_styles:true
      };
      await fs.writeFile(publicPath,JSON.stringify(publicReport,null,2));
    }else if(!publicURL && shellDelta){
      const baseline=JSON.parse(await fs.readFile(path.join(root,'evidence/browser-before-unified-shell.json'),'utf8'));
      for(const key of ['core_sha256','bridge_sha256','base_zip_sha256','files'])assert.deepEqual(baseline.build[key],report.build[key]);
      publicReport.change_verification={
        baseline_report:'browser-before-unified-shell.json',baseline_build:baseline.build,
        baseline_check_count:Object.values(baseline.checks).filter(x=>x===true).length,
        baseline_structured_probes:baseline.checks.structured_probes,
        change:'Cabeçalho e barra de leitura unificados, handlers antigos de apresentação removidos, estados de execução e textos públicos ajustados. Nenhuma alteração no motor, base, ponte ou consultas.',
        scope:'Delta de interface: carregamento real com controle de leitura disponível, caso principal e sua reconstrução, exemplo de leitor de tela, interrupção de fala durante geração, reflow, limpeza e ausência de envio do caso. As nove sondagens semânticas pertencem ao baseline preservado, não foram reexecutadas nesta revisão.',
        unchanged_engine_base_bridge_queries:true,
        voice_limit:'Verificada a chamada de interrupção; não houve síntese audível nem avaliação com leitor de tela.'
      };
      await fs.writeFile(publicPath,JSON.stringify(publicReport,null,2));
    }else if (!publicURL && process.env.AMADO_DELTA_ONLY === '1') {
      const previous=JSON.parse(await fs.readFile(publicPath,'utf8'));
      for (const key of ['core_sha256','base_zip_sha256','bridge_sha256','files']) assert.deepEqual(previous.build[key],report.build[key]);
      await fs.writeFile(path.join(root,'evidence/browser-baseline-report.json'),JSON.stringify(previous,null,2));
      publicReport.change_verification={
        baseline_report:'browser-baseline-report.json',
        baseline_build:previous.build,
        baseline_check_count:Object.values(previous.checks).filter(value=>value===true).length,
        baseline_structured_probes:previous.checks.structured_probes,
        change:'runBusy mantém stop-speech habilitado, assim como clear-case. Nenhuma outra alteração no frontend desde a regressão completa.',
        scope:'As 27 verificações e 9 provas estruturadas pertencem ao baseline identificado. A versão final recebeu o teste dirigido de interrupção de fala durante consulta real, reconstrução do caso principal, outro exemplo, reflow e limpeza. Não houve reexecução das nove provas após essa alteração de uma linha.',
        unchanged_engine_base_bridge_queries:true,
        voice_limit:'Foi verificada a chamada à função de interrupção; não foi realizada síntese audível nem avaliação com leitor de tela.'
      };
      await fs.writeFile(publicPath,JSON.stringify(publicReport,null,2));
    } else if (process.env.AMADO_RECOVERY_ONLY === '1' || process.env.AMADO_PROBES_ONLY === '1') {
      const previous=await fs.readFile(publicPath,'utf8').then(JSON.parse).catch(()=>({}));
      previous[process.env.AMADO_RECOVERY_ONLY === '1' ? 'recovery' : 'structured_probes']=publicReport;
      await fs.writeFile(publicPath,JSON.stringify(previous,null,2));
    } else await fs.writeFile(publicPath,JSON.stringify(publicReport,null,2));
  }
  await browser.close(); await new Promise(resolve=>server.close(resolve));
  console.log(JSON.stringify(report,null,2));
}
