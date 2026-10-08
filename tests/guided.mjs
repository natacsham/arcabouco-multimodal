// Directed QA of the alternative presentation, using the unchanged real engine.
import fs from 'node:fs/promises';
import path from 'node:path';
import http from 'node:http';
import crypto from 'node:crypto';
import assert from 'node:assert/strict';
import {fileURLToPath,pathToFileURL} from 'node:url';
import {coreInvariantAudit, historicalReport, typographySnapshot, assertAmadoTypography, assertFixedViewportDoubling} from './presentation-metrics.mjs';

const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const web=path.join(root,'web');
const artifacts=path.join(root,'tests/.artifacts/guided');
await fs.mkdir(artifacts,{recursive:true});
const modules=process.env.AMADO_NODE_MODULES||path.join(process.env.USERPROFILE,'.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules');
const {chromium}=await import(pathToFileURL(path.join(modules,'playwright/index.mjs')).href);
const mime={'.html':'text/html; charset=utf-8','.css':'text/css','.js':'text/javascript','.mjs':'text/javascript','.json':'application/json','.wasm':'application/wasm','.zip':'application/zip'};
const server=http.createServer(async(req,res)=>{
  try{
    const pathname=decodeURIComponent(new URL(req.url,'http://localhost').pathname);
    if(pathname==='/favicon.ico'){res.writeHead(204).end();return;}
    if(!pathname.startsWith('/MADO/')){res.writeHead(404).end();return;}
    let rel=pathname.slice(6);if(!rel||rel.endsWith('/'))rel+='index.html';
    const target=path.resolve(web,rel);
    if(!target.startsWith(web+path.sep)){res.writeHead(403).end();return;}
    const body=await fs.readFile(target);
    res.writeHead(200,{'Content-Type':mime[path.extname(target)]||'application/octet-stream','Cache-Control':'no-store'}).end(body);
  }catch{res.writeHead(404).end();}
});
await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
const base=(process.env.AMADO_GUIDED_BASE||`http://127.0.0.1:${server.address().port}/MADO/amado/`).replace(/\/?$/,'/');
const origin=new URL(base).origin;
const layoutDelta=process.env.AMADO_LAYOUT_DELTA==='1';
const sha=data=>crypto.createHash('sha256').update(data).digest('hex');
const report={scope:'Visão guiada comparada à apresentação original, sem alteração ou nova validação da ontologia.',execution_target:process.env.AMADO_GUIDED_BASE?'PUBLIC_SITE':'LOCAL_SUBPATH',checks:{},errors:[],external_requests:[],request_methods:[],timings:{},started_at_utc:new Date().toISOString(),limitations:['Não é declaração de conformidade WCAG.','NVDA, VoiceOver e síntese audível não avaliados.','Casos sintéticos; não representa sessão humana.','Não repete a regressão semântica completa do motor.']};
if(process.env.AMADO_DEPLOYMENT_COMMIT)report.repository_commit_at_test=process.env.AMADO_DEPLOYMENT_COMMIT;
report.build=JSON.parse(await fs.readFile(path.join(web,'amado/manifest.json'),'utf8'));
report.source_sha256={};
for(const name of ['index.html','guiado.html','app.js','guided.js','guided.css','views.css','styles.css','client.mjs','worker.mjs'])report.source_sha256[name]=sha(await fs.readFile(path.join(web,'amado',name)));
const browser=await chromium.launch({headless:true,executablePath:process.env.AMADO_CHROMIUM||'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe'});
report.browser=browser.version();
const context=await browser.newContext({viewport:{width:1280,height:900},reducedMotion:'reduce'});
let failBase=false;
await context.route('**/*',route=>{
  const request=route.request();report.request_methods.push(request.method());
  if(!request.url().startsWith(origin+'/')&&!request.url().startsWith('blob:')){report.external_requests.push(request.url());return route.abort();}
  if(failBase&&request.url().endsWith('/assets/base.zip'))return route.abort('failed');
  return route.continue();
});
let page=await context.newPage();page.on('pageerror',error=>report.errors.push(error.message));
const check=(key,value)=>{report.checks[key]=Boolean(value);assert(value,key);};
const idle=async target=>{
  await target.waitForFunction(()=>document.querySelector('#main')?.getAttribute('aria-busy')==='false',{}, {timeout:180000});
  await target.evaluate(()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve))));
};
const stage=async value=>page.waitForFunction(expected=>document.body.dataset.guideStage===String(expected),value,{timeout:10000});
const text=(target,selector)=>target.locator(selector).textContent();
async function reflow(key){
  const values=await page.evaluate(()=>({viewport:innerWidth,width:document.documentElement.scrollWidth}));
  report.layout??={};report.layout[key]=values;
  if(values.width>values.viewport+1)report.layout[key].offenders=await page.locator('body *').evaluateAll(nodes=>nodes.filter(el=>el.checkVisibility()&&el.getBoundingClientRect().right>innerWidth+1).slice(0,20).map(el=>({tag:el.tagName,id:el.id,class:el.className,text:el.textContent.replace(/\s+/g,' ').trim().slice(0,70),right:el.getBoundingClientRect().right})));
  check(key,values.width<=values.viewport+1);
}
async function content(target){
  return target.evaluate(()=>{
    const clean=value=>String(value||'').replace(/\s+/g,' ').trim();
    const value=selector=>clean(document.querySelector(selector)?.textContent);
    const steps=[...document.querySelectorAll('#practical-steps > .practical-step')].map(el=>{
      const guided=el.matches('details');
      const purpose=guided?el.querySelector('.guide-config-purpose'):el.querySelector('p');
      const availability=el.querySelector(guided?'.guide-config-availability':'.availability');
      return {title:clean(el.querySelector(guided?'.guide-config-title':'h4')?.textContent).replace(/^\d+\.\s*/,''),modes:[...el.querySelectorAll('.mode-pill')].map(x=>clean(x.textContent)),purpose:clean(purpose?.textContent),availability:clean(availability?.textContent),paragraphs:[...el.querySelectorAll(guided?'.guide-config-body p':'p')].filter(x=>x!==purpose&&x!==availability).map(x=>clean(x.textContent)),items:[...el.querySelectorAll('li')].map(x=>clean(x.textContent)),resource_states:[...el.querySelectorAll('.resource-state')].map(x=>({label:clean(x.textContent),classes:x.className}))};
    });
    return {headline:value('#practical-headline'),orientation:value('#orientation'),rationale:value('#rationale'),expected:value('#expected-result'),expected_note:value('#expected-result-note'),limit:value('#limit'),steps,configurations:[...document.querySelectorAll('#modal-configuration .mode-card')].map(x=>clean(x.textContent)),resources:value('#resources'),conditional_resources:value('#conditional-resources'),conditions:value('#conditions'),alternatives:value('#alternatives'),monitoring:value('#monitoring'),missing:value('#missing'),criteria:value('#criteria'),knowledge:value('#knowledge')};
  });
}
async function contrastSamples(){
  return page.evaluate(()=>{
    const rgba=text=>{const match=text.match(/rgba?\(([^)]+)\)/);if(!match)return null;const values=match[1].split(/[,\s/]+/).filter(Boolean).map(Number);return [...values.slice(0,3),values[3]??1];};
    const blend=(front,back)=>[0,1,2].map(i=>front[i]*front[3]+back[i]*(1-front[3]));
    const lum=rgb=>rgb.map(x=>x/255).map(x=>x<=.04045?x/12.92:((x+.055)/1.055)**2.4).reduce((sum,x,i)=>sum+x*[.2126,.7152,.0722][i],0);
    const samples=[];
    for(const selector of ['h1','h2','p','button','summary','.guide-config-purpose','.guide-config-availability','.resource-state']){
      for(const el of [...document.querySelectorAll(selector)].filter(x=>x.checkVisibility()&&x.textContent.trim()).slice(0,4)){
        const style=getComputedStyle(el),front=rgba(style.color);if(!front||style.opacity!=='1')continue;
        const layers=[];let ancestor=el;
        while(ancestor){const color=rgba(getComputedStyle(ancestor).backgroundColor);if(color)layers.push(color);ancestor=ancestor.parentElement;}
        let back=[255,255,255];for(const color of layers.reverse())back=blend(color,back);
        const fg=lum(blend(front,back)),bg=lum(back),ratio=(Math.max(fg,bg)+.05)/(Math.min(fg,bg)+.05);
        const large=parseFloat(style.fontSize)>=24||(parseFloat(style.fontSize)>=18.66&&parseInt(style.fontWeight)>=700);
        samples.push({selector,text:el.textContent.replace(/\s+/g,' ').trim().slice(0,65),ratio,minimum:large?3:4.5});
      }
    }
    return samples;
  });
}
async function originalCase(){
  const original=await context.newPage();original.on('pageerror',error=>report.errors.push(error.message));
  await original.goto(base);await idle(original);
  await original.locator('#reported-step input[value="yes"]').check();
  await original.locator('#confirm-reported').click();await idle(original);
  await original.locator('#mapping-confirmed').check();
  await original.locator('#generate-known').click();await idle(original);
  assert.equal(await original.locator('#modal-configuration .mode-card').count(),7);
  const result=await content(original);await original.close();return result;
}
try{
  report.core_invariants=await coreInvariantAudit(root);
  report.historical_baseline=historicalReport(root,'evidence/guided-report.json');
  for(const [name,expected] of Object.entries(report.source_sha256)){
    const response=await context.request.get(base+name);
    check('served_'+name.replaceAll('.','_')+'_matches',response.status()===200&&sha(await response.body())===expected);
  }
  // Start the original-view reference in parallel, in an isolated tab/Worker.
  const originalResult=originalCase().then(value=>({value}),error=>({error}));
  const started=Date.now();await page.goto(base+'guiado.html');await idle(page);await stage(1);
  report.timings.load_ms=Date.now()-started;
  check('runtime_ready',await page.locator('#health').getAttribute('data-state')==='ready'&&await text(page,'#runtime-error')==='');
  report.typography={initial_desktop:await typographySnapshot(page)};
  assertAmadoTypography(report.typography.initial_desktop);
  check('initial_functional_labels_at_least_16',true);
  check('no_duplicate_ids',await page.locator('[id]').evaluateAll(nodes=>new Set(nodes.map(x=>x.id)).size===nodes.length));
  check('two_real_tabs_only',await page.locator('[role="tab"]').count()===2&&await page.locator('[data-guide-step]').count()===3);
  check('stage_one_only',await page.locator('#reported-step').isVisible()&&!await page.locator('#organized-step').isVisible()&&!await page.locator('#saida').isVisible());
  await page.keyboard.press('Tab');check('keyboard_skip_first',await page.evaluate(()=>document.activeElement?.getAttribute('href'))==='#main');
  await page.keyboard.press('Enter');check('keyboard_skip_focus',await page.evaluate(()=>document.activeElement?.id)==='main');
  await page.locator('[data-guide-step="2"]').focus();await page.keyboard.press('Enter');
  check('cannot_skip_confirmation',await page.locator('body').getAttribute('data-guide-stage')==='1'&&await page.locator('#mapping-confirmed').isChecked()===false&&Boolean(await text(page,'#guide-status')));
  await page.locator('#confirm-reported').click();await idle(page);
  check('missing_selection_error_visible',await page.locator('body').getAttribute('data-guide-stage')==='1'&&await page.locator('#runtime-error').isVisible()&&Boolean(await text(page,'#runtime-error')));
  check('error_does_not_unlock_review',await page.locator('[data-guide-step="2"]').getAttribute('aria-disabled')==='true');
  await page.locator('#reported-step input[value="yes"]').check();await page.locator('#confirm-reported').click();await idle(page);await stage(2);
  check('review_is_unconfirmed',!await page.locator('#mapping-confirmed').isChecked());
  check('obsolete_navigation_message_cleared',await text(page,'#guide-status')==='');
  check('review_focus',await page.locator('#organized-step > summary').evaluate(el=>document.activeElement===el));
  report.typography.review_desktop=await typographySnapshot(page);
  assertAmadoTypography(report.typography.review_desktop);
  check('review_typographic_hierarchy',true);
  await page.locator('#generate-known').click();await idle(page);
  check('generation_requires_confirmation',await page.locator('body').getAttribute('data-guide-stage')==='2'&&await page.locator('#runtime-error').isVisible()&&!await page.locator('#saida').isVisible());
  await page.locator('#mapping-confirmed').check();
  const generation=Date.now();await page.locator('#generate-known').click();await idle(page);await stage(3);
  report.timings.principal_generation_ms=Date.now()-generation;
  check('principal_seven_configurations',await text(page,'#decision-status')==='Orientação construída'&&await page.locator('#modal-configuration .mode-card').count()===7);
  check('result_focus',await page.evaluate(()=>document.activeElement?.id)==='decision-title');
  const guidedResult=await content(page),originalOutcome=await originalResult;
  if(originalOutcome.error)throw originalOutcome.error;
  const baseline=originalOutcome.value;
  assert.deepEqual(guidedResult,baseline);check('same_content_modes_resources_as_original',true);
  report.comparison={scope:'Síntese, títulos e conteúdo dos blocos, modos, funções, recursos e estados, orientação detalhada, condições, alternativas, acompanhamento, critérios e conhecimentos; apenas wrappers e prefixos numéricos da apresentação são desconsiderados.',original_sha256:sha(JSON.stringify(baseline)),guided_sha256:sha(JSON.stringify(guidedResult)),configurations:guidedResult.configurations.length,steps:guidedResult.steps.length};
  if(report.historical_baseline.comparison){
    check('decision_content_matches_pre_editorial_baseline',report.comparison.guided_sha256===report.historical_baseline.comparison.guided_sha256);
  }
  check('practical_disclosures_closed',await page.locator('#practical-steps > details').count()===guidedResult.steps.length&&await page.locator('#practical-steps > details[open]').count()===0);
  const first=page.locator('#practical-steps > details').first();
  check('modes_function_resources_visible_when_closed',await first.locator('.mode-pills').isVisible()&&await first.locator('.guide-config-purpose').isVisible()&&await first.locator('.guide-config-availability').isVisible());
  await first.locator(':scope > summary').focus();await page.keyboard.press('Enter');
  check('configuration_keyboard_opens',await first.getAttribute('open')!==null);
  report.configuration_focus=await first.locator(':scope > summary').evaluate(el=>{
    const s=getComputedStyle(el),r=el.getBoundingClientRect();
    return {style:s.outlineStyle,width:s.outlineWidth,color:s.outlineColor,visible:r.top>=0&&r.bottom<=innerHeight};
  });
  check('configuration_focus_visible',report.configuration_focus.style!=='none'&&parseFloat(report.configuration_focus.width)>=2&&report.configuration_focus.visible);
  await page.keyboard.press('Space');check('configuration_keyboard_closes',await first.getAttribute('open')===null);
  await page.locator('#guide-expand').click();check('expand_all',await page.locator('#practical-steps > details[open]').count()===guidedResult.steps.length);
  await page.locator('#guide-collapse').click();check('collapse_all_preserves_content',await page.locator('#practical-steps > details[open]').count()===0&&JSON.stringify(await content(page))===JSON.stringify(guidedResult));
  report.contrast_default=await contrastSamples();
  check('measured_text_contrast',report.contrast_default.length>10&&report.contrast_default.every(x=>x.ratio>=x.minimum));
  await page.locator('[data-site-contrast]').click();report.contrast_high=await contrastSamples();
  check('measured_high_contrast',report.contrast_high.every(x=>x.ratio>=x.minimum));
  await page.locator('[data-site-contrast]').click();
  report.typography.result_desktop=await typographySnapshot(page);assertAmadoTypography(report.typography.result_desktop);
  for(let n=0;n<4;n++)await page.locator('[data-font-increase]').click();
  report.typography.result_desktop_200=await typographySnapshot(page);
  report.typography.desktop_ratios=assertFixedViewportDoubling(report.typography.result_desktop,report.typography.result_desktop_200);
  await reflow('result_desktop_text_200');await page.locator('[data-font-reset]').click();
  check('desktop_fixed_viewport_fonts_double',true);
  await page.screenshot({path:path.join(artifacts,'result-desktop.png'),fullPage:true});
  await page.setViewportSize({width:320,height:900});await reflow('result_reflow_320');
  report.typography.result_mobile=await typographySnapshot(page);assertAmadoTypography(report.typography.result_mobile,true);
  await page.screenshot({path:path.join(artifacts,'result-mobile.png'),fullPage:true});
  for(let n=0;n<20;n++)if(await page.locator('[data-font-increase]').isEnabled())await page.locator('[data-font-increase]').click();
  check('text_reaches_200',await page.locator('html').evaluate(el=>parseFloat(getComputedStyle(el).fontSize))===32);
  report.typography.result_mobile_200=await typographySnapshot(page);
  report.typography.mobile_ratios=assertFixedViewportDoubling(report.typography.result_mobile,report.typography.result_mobile_200);
  check('mobile_fixed_viewport_fonts_double',true);
  await reflow('result_reflow_320_text_200');
  if(layoutDelta){
    report.mobile_reading_width=await first.evaluate(el=>{
      const summary=el.querySelector(':scope > summary'),s=getComputedStyle(summary);
      return {card_width:el.getBoundingClientRect().width,text_width:summary.clientWidth-parseFloat(s.paddingLeft)-parseFloat(s.paddingRight),font_size:getComputedStyle(document.documentElement).fontSize};
    });
    // Project readability check, not a numeric WCAG requirement. The usable
    // text area matters; record the enclosing card width without an arbitrary
    // extra minimum that would depend on the original page's outer gutters.
    check('mobile_reading_width_preserved',report.mobile_reading_width.text_width>=220);
  }
  await page.screenshot({path:path.join(artifacts,'result-mobile-200.png')});
  await page.locator('#guide-progress').screenshot({path:path.join(artifacts,'steps-mobile-200.png')});
  await first.screenshot({path:path.join(artifacts,'configuration-mobile-200.png')});
  await page.locator('[data-font-reset]').click();await page.emulateMedia({forcedColors:'active',reducedMotion:'reduce'});await reflow('forced_colors_reflow');
  check('forced_colors_and_reduced_motion',await page.evaluate(()=>matchMedia('(forced-colors:active)').matches&&matchMedia('(prefers-reduced-motion:reduce)').matches));
  await page.emulateMedia({forcedColors:'none',reducedMotion:'reduce'});await page.setViewportSize({width:1280,height:900});
  if(!layoutDelta){
  await page.locator('[data-guide-step="2"]').click();await stage(2);
  check('back_preserves_confirmation',await page.locator('#mapping-confirmed').isChecked());
  await page.locator('[data-guide-step="3"]').click();await stage(3);
  check('forward_preserves_result',JSON.stringify(await content(page))===JSON.stringify(guidedResult));
  await page.locator('[data-guide-step="1"]').click();await stage(1);
  await page.locator('#confirm-reported').click();await idle(page);await stage(2);
  check('reconfirm_report_invalidates_previous_result',!await page.locator('#mapping-confirmed').isChecked()&&await page.locator('[data-guide-step="3"]').getAttribute('aria-disabled')==='true'&&!await page.locator('#saida').isVisible());
  await page.locator('[data-guide-step="3"]').focus();await page.keyboard.press('Enter');
  check('reconfirm_cannot_reopen_stale_result',await page.locator('body').getAttribute('data-guide-stage')==='2');
  await page.locator('#mapping-confirmed').check();await page.locator('#generate-known').click();await idle(page);await stage(3);
  check('reconfirmed_report_requires_new_generation',await page.locator('#modal-configuration .mode-card').count()===7&&JSON.stringify(await content(page))===JSON.stringify(guidedResult));
  await page.locator('[data-guide-step="2"]').click();
  await page.locator('#organized-step .foundation > summary').click();
  await page.locator('#objective').fill('Objetivo revisado para conferir a invalidação.');
  check('editing_invalidates_old_result',!await page.locator('#mapping-confirmed').isChecked()&&!await page.locator('#saida').isVisible()&&await page.locator('[data-guide-step="3"]').getAttribute('aria-disabled')==='true');
  await page.locator('[data-guide-step="1"]').click();await stage(1);await page.locator('#free-tab').click();await idle(page);await stage(1);
  await page.locator('#template-select').selectOption('CTX-DEMO-WEB-LEITOR-TELA');await idle(page);await stage(2);
  check('example_requires_review',!await page.locator('#free-confirmed').isChecked()&&await page.locator('#free-summary').isVisible());
  const exampleDescription=await page.locator('#free-narrative').inputValue();
  await page.locator('[data-guide-step="1"]').click();await stage(1);
  await page.locator('#organize-narrative').click();await idle(page);await stage(2);
  check('synchronous_preserved_organization_advances',await page.locator('#free-narrative').inputValue()===exampleDescription&&!await page.locator('#free-confirmed').isChecked());
  await page.locator('#free-confirmed').check();await page.locator('#generate-free').click();await idle(page);await stage(3);
  check('screen_reader_example_constructed',await text(page,'#decision-status')==='Orientação construída'&&await page.locator('#modal-configuration .mode-card').count()>0);
  await page.locator('[data-guide-step="1"]').click();await stage(1);
  await page.locator('#free-narrative').fill('Uma pessoa precisa de ajuda. MARCADOR-GUIADO-SINTETICO');
  check('changed_narrative_invalidates_review',await page.locator('#free-interpretation').getAttribute('hidden')!==null&&!await page.locator('#saida').isVisible());
  await page.locator('#organize-narrative').click();await idle(page);await stage(2);
  check('incomplete_narrative_reports_missing',await page.locator('#free-missing li').count()>0);
  await page.locator('#free-confirmed').check();await page.locator('#generate-free').click();await idle(page);await stage(3);
  check('incomplete_narrative_suspends',await text(page,'#decision-status')==='Decisão suspensa');
  check('stop_available_at_every_stage',await page.locator('.intro #stop-speech').isVisible()&&await page.locator('#stop-speech').isEnabled());
  await page.locator('#clear-case').click();await idle(page);await stage(1);
  check('clear_discards_and_resets',await page.locator('#free-narrative').inputValue()===''&&!await page.locator('#saida').isVisible()&&await page.locator('#known-tab').getAttribute('aria-selected')==='true');
  failBase=true;await page.locator('#clear-case').click();await idle(page);
  check('load_failure_is_visible',await page.locator('#runtime-error').isVisible()&&Boolean(await text(page,'#runtime-error'))&&await page.locator('#clear-case').isEnabled());
  failBase=false;await page.locator('#clear-case').click();await idle(page);await stage(1);
  check('clear_recovers_failed_runtime',await text(page,'#runtime-error')===''&&await page.locator('#health').getAttribute('data-state')==='ready'&&!await page.locator('#saida').isVisible());
  await page.screenshot({path:path.join(artifacts,'start-desktop.png'),fullPage:true});
  }
  check('no_storage',await page.evaluate(async()=>localStorage.length===0&&sessionStorage.length===0&&document.cookie===''&&(await indexedDB.databases()).length===0&&(await caches.keys()).length===0));
  check('no_external_or_case_upload',report.external_requests.length===0&&report.request_methods.every(method=>method==='GET'));
  check('no_javascript_errors',report.errors.length===0);
  const finalManifest=JSON.parse(await fs.readFile(path.join(web,'amado/manifest.json'),'utf8'));
  check('manifest_not_changed_during_run',JSON.stringify(finalManifest)===JSON.stringify(report.build));
  const served=await context.request.get(base+'manifest.json');check('served_manifest_matches',JSON.stringify(await served.json())===JSON.stringify(report.build));
  assert.deepEqual(await coreInvariantAudit(root),report.core_invariants);
  check('editorial_preserves_semantic_and_runtime_files',true);
  if(layoutDelta){
    const baselineName=process.env.AMADO_GUIDED_BASE?'guided-public-before-layout-polish.json':'guided-before-layout-polish.json';
    const baseline=JSON.parse(await fs.readFile(path.join(root,'evidence',baselineName),'utf8'));
    assert.equal(baseline.completed,true);
    for(const key of ['core_sha256','base_zip_sha256','bridge_sha256','files','site_assets_sha256'])assert.deepEqual(baseline.build[key],report.build[key]);
    assert.deepEqual(Object.keys(baseline.source_sha256),Object.keys(report.source_sha256));
    for(const [name,value] of Object.entries(baseline.source_sha256))if(name!=='guided.css')assert.equal(value,report.source_sha256[name]);
    check('css_only_invariants_confirmed',true);
    report.scope='Delta de layout da visão guiada: somente espaçamento móvel em guided.css; motor e comportamento preservados por comparação de hashes.';
    report.change_verification={baseline_report:baselineName,baseline_build:baseline.build,baseline_check_count:Object.values(baseline.checks).filter(Boolean).length,change:'Espaçamentos laterais móveis em pixels para preservar largura de leitura quando o texto é ampliado; nenhuma mudança na lógica do adaptador ou do motor.',scope:'Reexecutados caso principal, equivalência com a visão original, confirmações, teclado, disclosures, contraste e reflow 320 px/200%. Os testes completos de outro exemplo, narrativa insuficiente, invalidação, limpeza e recuperação pertencem ao baseline de 60 verificações identificado; não foram repetidos após este ajuste somente de CSS.',unchanged_engine_base_bridge_queries:true,unchanged_guided_javascript:true};
  }
  if(!layoutDelta){
    report.change_verification={baseline:report.historical_baseline,
      change:'Revisão editorial e tipográfica; comportamento guiado e conteúdo decisório preservados.',
      scope:'Reexecutados confirmação, sete configurações e equivalência do conteúdo com a outra apresentação e o baseline, navegação por etapas, teclado, invalidação, outro exemplo, narrativa incompleta, limpeza, falha de carregamento e recuperação; medidas tipográficas efetivas, ampliação a 200% no mesmo viewport e reflow a 320px. Não é nova validação OWL nem avaliação humana.',
      unchanged_semantic_and_runtime_files:report.core_invariants.all_unchanged};
  }
  report.completed=true;
}catch(error){report.completed=false;report.failure=String(error.stack||error).replaceAll(root,'<workspace>').replaceAll(root.replaceAll('\\','/'),'<workspace>');console.error(error);await page.screenshot({path:path.join(artifacts,'failure.png'),fullPage:true}).catch(()=>{});process.exitCode=1;}
finally{
  report.finished_at_utc=new Date().toISOString();
  const name=process.env.AMADO_GUIDED_BASE?'guided-public-report.json':'guided-report.json';
  await fs.writeFile(path.join(root,'evidence',name),JSON.stringify(report,null,2)+'\n');
  await browser.close();await new Promise(resolve=>server.close(resolve));
  console.log(JSON.stringify({completed:report.completed,passed:Object.values(report.checks).filter(Boolean).length,total:Object.keys(report.checks).length,report:'evidence/'+name,failure:report.failure}));
}
