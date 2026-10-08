// Current-version checks: real Pyodide, both presentations and shared explanation.
// These synthetic fixtures are not participant session records.
import fs from 'node:fs/promises';
import path from 'node:path';
import http from 'node:http';
import assert from 'node:assert/strict';
import crypto from 'node:crypto';
import {fileURLToPath,pathToFileURL} from 'node:url';

const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const web=path.join(root,'web'), prefix='/arcabouco-multimodal/';
const artifacts=path.join(root,'tests/.artifacts/browser');
await fs.mkdir(artifacts,{recursive:true});
const modules=process.env.AMADO_NODE_MODULES||path.join(process.env.USERPROFILE,'.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules');
const {chromium}=await import(pathToFileURL(path.join(modules,'playwright/index.mjs')).href);
const mime={'.html':'text/html; charset=utf-8','.js':'text/javascript','.mjs':'text/javascript','.css':'text/css','.json':'application/json','.wasm':'application/wasm','.zip':'application/zip'};
const server=http.createServer(async(req,res)=>{
  try{
    let url=decodeURIComponent(new URL(req.url,'http://localhost').pathname);
    if(url==='/favicon.ico'){res.writeHead(204).end();return;}
    if(!url.startsWith(prefix)){res.writeHead(404).end();return;}
    let rel=url.slice(prefix.length);if(!rel||rel.endsWith('/'))rel+='index.html';
    const file=path.resolve(web,rel);if(!file.startsWith(web+path.sep)){res.writeHead(403).end();return;}
    res.writeHead(200,{'Content-Type':mime[path.extname(file)]||'application/octet-stream','Cache-Control':'no-store'}).end(await fs.readFile(file));
  }catch{res.writeHead(404).end();}
});
await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
const base=process.env.TRACE_PUBLIC_URL||`http://127.0.0.1:${server.address().port}${prefix}`;
const origin=new URL(base).origin;
const report={version:'1.4.0-rc1',type:'SYNTHETIC_TECHNICAL_BROWSER_CHECK',execution_target:process.env.TRACE_PUBLIC_URL?'PUBLIC_SITE':'LOCAL_SUBPATH',executed_at:new Date().toISOString(),checks:{},errors:[],external_requests:[],methods:[],limitations:['NVDA e VoiceOver não testados.','Não representa avaliação humana ou conformidade WCAG integral.','Tempos de laboratório; sem garantia de desempenho em dispositivos móveis.']};
report.build=JSON.parse(await fs.readFile(path.join(web,'amado/manifest.json'),'utf8'));
report.test_sha256=crypto.createHash('sha256').update(await fs.readFile(fileURLToPath(import.meta.url))).digest('hex');
const browser=await chromium.launch({headless:true,executablePath:process.env.AMADO_CHROMIUM||path.join(process.env.LOCALAPPDATA,'ms-playwright/chromium-1243/chrome-win64/chrome.exe')});
report.browser=browser.version();
const context=await browser.newContext({viewport:{width:1280,height:900},reducedMotion:'reduce'});
let failBundle=false;
const requests=[];
await context.route('**/*',route=>{
  const req=route.request();report.methods.push(req.method());
  requests.push({url:req.url(),body:req.postData()||''});
  if(!req.url().startsWith(origin+'/')&&!req.url().startsWith('blob:')){report.external_requests.push(req.url());return route.abort();}
  if(failBundle&&req.url().endsWith('/assets/base.zip'))return route.abort('failed');
  return route.continue();
});
let page=await context.newPage();page.on('pageerror',e=>report.errors.push(e.message));
const check=(key,value)=>{report.checks[key]=Boolean(value);assert(value,key);};
const idle=target=>target.waitForFunction(()=>document.querySelector('#main')?.getAttribute('aria-busy')==='false',{}, {timeout:180000});
const openAncestors=async locator=>locator.evaluate(el=>{let p=el.parentElement;while(p){if(p.tagName==='DETAILS')p.open=true;p=p.parentElement;}});
async function reflow(key){
  const dimensions=await page.evaluate(()=>({viewport:innerWidth,width:document.documentElement.scrollWidth}));
  report.layout??={};report.layout[key]=dimensions;check(key,dimensions.width<=dimensions.viewport+1);
}
async function contrastSamples(){
  return page.evaluate(()=>{
    const rgba=text=>{const m=text.match(/rgba?\(([^)]+)\)/);if(!m)return null;const a=m[1].split(/[,\s/]+/).filter(Boolean).map(Number);return [...a.slice(0,3),a[3]??1];};
    const blend=(a,b)=>[0,1,2].map(i=>a[i]*a[3]+b[i]*(1-a[3]));
    const lum=a=>a.map(x=>x/255).map(x=>x<=.04045?x/12.92:((x+.055)/1.055)**2.4).reduce((s,x,i)=>s+x*[.2126,.7152,.0722][i],0);
    return ['.explanation p','.explanation summary','.explanation strong','.explanation li','button','h1'].flatMap(selector=>[...document.querySelectorAll(selector)].filter(e=>e.checkVisibility()).slice(0,6).map(el=>{
      const style=getComputedStyle(el),fg=rgba(style.color);let p=el,layers=[];
      while(p){const c=rgba(getComputedStyle(p).backgroundColor);if(c)layers.push(c);p=p.parentElement;}
      let bg=[255,255,255];for(const c of layers.reverse())bg=blend(c,bg);
      const a=lum(blend(fg,bg)),b=lum(bg),large=parseFloat(style.fontSize)>=24||(parseFloat(style.fontSize)>=18.66&&parseInt(style.fontWeight)>=700);
      return {selector,text:el.textContent.trim().slice(0,65),ratio:(Math.max(a,b)+.05)/(Math.min(a,b)+.05),minimum:large?3:4.5};
    }));
  });
}
try{
  const servedManifest=await context.request.get(base+'amado/manifest.json');
  assert(servedManifest.ok(),'Manifest must be served by the tested site');
  assert.deepEqual(await servedManifest.json(),report.build,'Served manifest must equal the exact locally tested build');
  check('served_manifest_matches_current_build',true);
  await page.goto(base);
  await page.locator('[data-explanation-pilot-details] > summary').click();
  await page.locator('[data-explanation-component]').first().waitFor();
  check('home_pilot_derived_choice_loaded',await page.locator('[data-explanation-component]').count()===1);
  const pilot=await context.request.get(base+'assets/explanation-pilot.json').then(r=>r.json());
  check('pilot_source_matches_base',pilot.source_hashes['data/knowledge-base.json']===report.build.files['data/knowledge-base.json']);
  check('pilot_has_confirmed_or_pending_contributions',pilot.explanation.configurations.some(c=>c.construction.contributions.length>0));
  await page.screenshot({path:path.join(artifacts,'home.png'),fullPage:true});
  await page.goto(base+'ontologia/');
  check('technical_documentation_loads',(await page.locator('h1').textContent()).includes('Documentação'));
  for(const file of ['main.ttl','mado-public.ttl','mado.owl','main.shacl.ttl']){
    const res=await context.request.get(base+'downloads/'+file);
    const expected=await fs.readFile(path.join(web,'downloads',file));
    check('download_'+file,res.ok()&&crypto.createHash('sha256').update(await res.body()).digest('hex')===crypto.createHash('sha256').update(expected).digest('hex'));
  }
  const displayed=[];
  for(const view of ['index.html','guiado.html']){
    await page.goto(base+'amado/'+view);await idle(page);
    check(view+'_ready',await page.locator('#health').getAttribute('data-state')==='ready');
    await page.locator('#reported-step input[value="yes"]').check();
    await page.locator('#confirm-reported').click();await idle(page);
    await page.locator('#mapping-confirmed').check();
    await page.locator('#generate-known').click();await idle(page);
    check(view+'_generation_no_error',!(await page.locator('#runtime-error').textContent()).trim());
    check(view+'_explicit_partial_coverage',(await page.locator('#decision-status').textContent()).includes('parcial'));
    const choice=page.locator('[data-explanation-component]').first();
    await openAncestors(choice);await choice.locator(':scope > summary').focus();
    await page.keyboard.press('Enter');check(view+'_keyboard_choice',await choice.getAttribute('open')!==null);
    const build=choice.locator('[data-explanation-reading="construction"]');
    await build.locator(':scope > summary').focus();await page.keyboard.press('Enter');
    check(view+'_construction_visible',await build.getAttribute('open')!==null);
    check(view+'_documentary_status_not_overstated',(await page.locator('.explanation').innerText()).includes('registro'));
    const use=choice.locator('[data-explanation-reading="application"]');
    await use.locator(':scope > summary').click();
    const content=await page.locator('.explanation').first().textContent();displayed.push(content);
    check(view+'_two_readings_present',content.includes('Como este conhecimento foi construído')&&content.includes('Por que foi usado aqui'));
    const focus=await use.locator(':scope > summary').evaluate(el=>({style:getComputedStyle(el).outlineStyle,width:getComputedStyle(el).outlineWidth}));
    await use.locator(':scope > summary').focus();await page.keyboard.press('Tab');
    check(view+'_focusable_disclosures',await page.locator('.explanation summary').count()>3);
    report.contrast??={};report.contrast[view]=await contrastSamples();
    check(view+'_sampled_contrast',report.contrast[view].every(s=>s.ratio>=s.minimum));
    await page.locator('[data-site-contrast]').click();
    report.contrast[view+'_high']=await contrastSamples();check(view+'_high_contrast',report.contrast[view+'_high'].every(s=>s.ratio>=s.minimum));
    await page.locator('[data-site-contrast]').click();
    await reflow(view+'_desktop');
    await page.screenshot({path:path.join(artifacts,view+'-trace.png'),fullPage:true});
    await page.setViewportSize({width:320,height:900});await reflow(view+'_320');
    for(let i=0;i<4;i++)await page.locator('[data-font-increase]').click();
    check(view+'_text_200',await page.locator('html').evaluate(el=>parseFloat(getComputedStyle(el).fontSize))===32);
    await reflow(view+'_320_200');
    await page.screenshot({path:path.join(artifacts,view+'-mobile.png')});
    await page.locator('[data-font-reset]').click();await page.setViewportSize({width:1280,height:900});
    await page.locator('#clear-case').click();await idle(page);
    check(view+'_clear_discards_decision',!await page.locator('#saida').isVisible());
  }
  // Random instance suffixes are not displayed in ordinary explanatory content.
  await fs.writeFile(path.join(artifacts,'explanation-view-comparison.json'),JSON.stringify(displayed));
  const normalizeText=s=>s.replace(/D-GERADA-[A-F0-9]+/g,'D-GERADA').replace(/CTX-CASO-[A-F0-9]+/g,'CTX-CASO').replace(/PART-CASO-(\d+)-[A-F0-9]+/g,'PART-CASO-$1').replace(/CHECK-[a-f0-9]+/g,'CHECK');
  check('same_explanation_in_both_views',normalizeText(displayed[0])===normalizeText(displayed[1]));
  // A separate isolated worker executes the same structured input fixtures as native Python.
  await page.evaluate(()=>{
    window.probeWorker=new Worker('./worker.mjs',{type:'module'});let seq=0;const pending=new Map();
    window.probeWorker.onmessage=({data})=>{const p=pending.get(data.id);if(!p)return;pending.delete(data.id);clearTimeout(p.timer);data.type==='error'?p.reject(new Error(data.error)):p.resolve(data.data);};
    window.probe=payload=>new Promise((resolve,reject)=>{const id=++seq,timer=setTimeout(()=>reject(new Error('Worker timeout')),180000);pending.set(id,{resolve,reject,timer});window.probeWorker.postMessage({id,...payload});});
  });
  const probe=request=>page.evaluate(r=>window.probe(r),request);
  const decisions={};
  for(const [name,template] of Object.entries({principal:'CTX-TRANSFERENCIA-RECURSO-DIGITAL-01',principal_sem_jogo:'CTX-TRANSFERENCIA-RECURSO-DIGITAL-01',leitor_tela:'CTX-DEMO-WEB-LEITOR-TELA',mobilidade_ruido:'CTX-DEMO-MOB-RUIDO',comunicacao:'CTX-DEMO-COMUNICACAO-MULTIFORMATO',diagnostico_isolado:'CTX-TESTE-RC2-DIAGNOSTICO-ISOLADO',sem_confirmacao:'CTX-TRANSFERENCIA-RECURSO-DIGITAL-01'})){
    const state=await probe({operation:'start',template});
    const payload={mapping_confirmed:name!=='sem_confirmacao',transfer_confirmed:name!=='sem_confirmacao'};
    if(name==='principal_sem_jogo')Object.assign(payload,{recursos_disponiveis:state.context.raw.recursos_disponiveis.filter(r=>r!=='REC-PLATAFORMA-JOGO-QUIZ'),recursos_propostos:state.context.raw.recursos_propostos.filter(r=>r!=='REC-PLATAFORMA-JOGO-QUIZ'),recursos_impedidos:['REC-PLATAFORMA-JOGO-QUIZ']});
    await probe({operation:'update',payload});decisions[name]=await probe({operation:'generate'});
    console.log(name,decisions[name].decision.status);
  }
  const native=JSON.parse(await fs.readFile(path.join(root,'evidence/regression-report.json'),'utf8'));
  const payload=structuredClone(native.cases.combinacao_nao_cadastrada.input);
  await probe({operation:'start',template:null});await probe({operation:'update',payload});
  decisions.combinacao_nao_cadastrada=await probe({operation:'generate'});
  payload.recursos_disponiveis=payload.recursos_disponiveis.filter(r=>r!=='REC-ENTRADA-VOZ');payload.recursos_impedidos=['REC-ENTRADA-VOZ'];
  await probe({operation:'update',payload});decisions.combinacao_sem_voz=await probe({operation:'generate'});
  check('novel_condition_change_affects_choice',JSON.stringify(decisions.combinacao_nao_cadastrada.decision.component_ids)!==JSON.stringify(decisions.combinacao_sem_voz.decision.component_ids));
  check('all_eight_queries_returned',Object.keys(decisions.principal.query_summary).length===8);
  check('checks_have_four_state_vocabulary',Object.values(decisions).filter(r=>r.execution_evidence).flatMap(r=>r.execution_evidence.checks).every(c=>['PASS','FAIL','PENDING','NOT_EXECUTED'].includes(c.outcome)));
  check('same_table_and_graph_projection',Object.values(decisions).filter(r=>r.explanation).every(r=>JSON.stringify(r.de_para)===JSON.stringify(r.explanation.de_para)&&JSON.stringify(r.trace_graph)===JSON.stringify(r.explanation.graph)));
  await fs.writeFile(path.join(artifacts,'decisions.json'),JSON.stringify(decisions));
  await page.evaluate(()=>window.probeWorker.terminate());
  // Failure recovery is not a successful empty orientation.
  failBundle=true;await page.goto(base+'amado/');await idle(page);
  check('failed_load_does_not_generate',Boolean((await page.locator('#runtime-error').textContent()).trim())&&!await page.locator('#saida').isVisible());
  failBundle=false;await page.locator('#clear-case').click();await idle(page);
  check('load_failure_recovers',await page.locator('#health').getAttribute('data-state')==='ready');
  await page.locator('#free-tab').click();await idle(page);
  await page.locator('#free-narrative').fill('MARCADOR-PRIVACIDADE. Uma pessoa precisa de ajuda.');
  await page.locator('#organize-narrative').click();await idle(page);
  await page.locator('#free-confirmed').check();await page.locator('#generate-free').click();await idle(page);
  check('insufficient_narrative_suspends',(await page.locator('#decision-status').textContent()).includes('suspensa'));
  await page.reload();await idle(page);
  check('reload_does_not_restore_case',await page.locator('#free-narrative').inputValue()==='');
  check('no_browser_case_storage',await page.evaluate(async()=>localStorage.length===0&&sessionStorage.length===0&&document.cookie===''&&(await indexedDB.databases()).length===0&&(await caches.keys()).length===0));
  check('no_case_transmission',report.methods.every(m=>m==='GET')&&report.external_requests.length===0&&!requests.some(r=>(r.url+r.body).includes('MARCADOR-PRIVACIDADE')));
  check('no_javascript_errors',report.errors.length===0);
  report.completed=true;
}catch(error){report.failure=String(error.stack||error).replaceAll(root,'<PROJECT>').replaceAll(root.replaceAll('\\','/'),'<PROJECT>');process.exitCode=1;await page.screenshot({path:path.join(artifacts,'traceability-failure.png'),fullPage:true}).catch(()=>{});}
finally{
  const name=process.env.TRACE_PUBLIC_URL?'traceability-public.json':'traceability-browser.json';
  await fs.writeFile(path.join(root,'evidence',name),JSON.stringify(report,null,2));
  await browser.close();await new Promise(resolve=>server.close(resolve));
  console.log(JSON.stringify({completed:report.completed,checks:report.checks,failure:report.failure},null,2));
}
