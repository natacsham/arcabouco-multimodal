// Real Pyodide/native parity and UI checks for synthetic composition contexts.
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import path from 'node:path';
import http from 'node:http';
import crypto from 'node:crypto';
import {execFileSync} from 'node:child_process';
import {fileURLToPath,pathToFileURL} from 'node:url';

const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const web=path.join(root,'web'), prefix='/arcabouco-multimodal/';
const modules=process.env.AMADO_NODE_MODULES||path.join(process.env.USERPROFILE,'.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules');
const {chromium}=await import(pathToFileURL(path.join(modules,'playwright/index.mjs')).href);
const mime={'.html':'text/html; charset=utf-8','.js':'text/javascript','.mjs':'text/javascript','.css':'text/css','.json':'application/json','.wasm':'application/wasm','.zip':'application/zip'};
const server=http.createServer(async(req,res)=>{
  try{
    const pathname=decodeURIComponent(new URL(req.url,'http://localhost').pathname);
    if(pathname==='/favicon.ico'){res.writeHead(204).end();return;}
    if(!pathname.startsWith(prefix)){res.writeHead(404).end();return;}
    let relative=pathname.slice(prefix.length);if(!relative||relative.endsWith('/'))relative+='index.html';
    const file=path.resolve(web,relative);if(!file.startsWith(web+path.sep)){res.writeHead(403).end();return;}
    res.writeHead(200,{'Content-Type':mime[path.extname(file)]||'application/octet-stream','Cache-Control':'no-store'}).end(await fs.readFile(file));
  }catch{res.writeHead(404).end();}
});
await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
const base=process.env.COMPOSITION_PUBLIC_URL||`http://127.0.0.1:${server.address().port}${prefix}`;
const report={type:'SYNTHETIC_COMPOSITION_BROWSER_NOT_HUMAN_EVALUATION',executed_at:new Date().toISOString(),
  target:process.env.COMPOSITION_PUBLIC_URL?'PUBLIC_SITE':'LOCAL_SUBPATH',checks:{},errors:[],external_requests:[],
  limits:['No participant session or learning outcome is measured.','NVDA and VoiceOver not tested; no full WCAG conformance claim.']};
const check=(name,value)=>{report.checks[name]=Boolean(value);assert(value,name);};
const sha=value=>crypto.createHash('sha256').update(value).digest('hex');
report.build=JSON.parse(await fs.readFile(path.join(web,'amado/manifest.json'),'utf8'));
report.test_sha256=sha(await fs.readFile(fileURLToPath(import.meta.url)));
const example=JSON.parse(await fs.readFile(path.join(root,'experimental/v2/examples/learning-contribution.json'),'utf8'));
const fixtures={};
function fixture(name,change){const value=structuredClone(example);value.id='SYN-BROWSER-'+name;change?.(value);fixtures[name]=value;}
fixture('keyboard_audio');
fixture('audio_blocked',x=>{x.resources.AudioOutput=false;});
fixture('visual_alternative',x=>{x.resources.AudioOutput=false;x.resources.Display=true;x.facts.CanReviewVisualText=true;});
fixture('unknown_effort',x=>{x.facts.KeyboardEffortAcceptable=null;});
fixture('no_correction',x=>{x.facts.CanCorrect=false;});
fixture('review_only',x=>{x.task='TaskReviewExistingText';});
fixture('not_confirmed',x=>{x.confirmed=false;});
const python=process.env.AMADO_PYTHON||'python';
const native=JSON.parse(execFileSync(python,['-B','-c',[
  'import sys,json,importlib.util',
  'from pathlib import Path',
  'sys.path[:0]=[str(Path.cwd()),str(Path.cwd()/"vendor")]',
  's=importlib.util.spec_from_file_location("public_composition_bridge", "web/amado/bridge.py")',
  'm=importlib.util.module_from_spec(s);s.loader.exec_module(m);m.initialize()',
  'print(json.dumps({k:m.dispatch({"operation":"compose","payload":v}) for k,v in json.load(sys.stdin).items()},ensure_ascii=True))'
].join('\n')],{cwd:root,input:JSON.stringify(fixtures),encoding:'utf8',maxBuffer:32*1024*1024}));
const browser=await chromium.launch({headless:true,executablePath:process.env.AMADO_CHROMIUM||path.join(process.env.LOCALAPPDATA,'ms-playwright/chromium-1243/chrome-win64/chrome.exe')});
const context=await browser.newContext({viewport:{width:1280,height:900},reducedMotion:'reduce'});
await context.route('**/*',route=>{
  const url=route.request().url();
  if(!url.startsWith(new URL(base).origin+'/')&&!url.startsWith('blob:')){report.external_requests.push(url);return route.abort();}
  return route.continue();
});
try{
  report.cases={};
  for(const view of ['index.html','guiado.html']){
    const page=await context.newPage();page.on('pageerror',error=>report.errors.push(error.message));
    await page.goto(base+'amado/'+view);
    await page.waitForFunction(()=>document.querySelector('#health')?.dataset.state==='ready'&&document.querySelector('#main')?.getAttribute('aria-busy')==='false',{}, {timeout:180000});
    const catalog=await page.evaluate(async()=>{const {request}=await import('./client.mjs');return request('catalog_composition');});
    check(view+'_catalog_from_rdf',catalog.tasks.length===2&&catalog.facts.every(x=>x.default===null));
    const results=await page.evaluate(async values=>{const {request}=await import('./client.mjs');const rows={};for(const [name,payload]of Object.entries(values))rows[name]=await request('compose',{payload});return rows;},fixtures);
    for(const [name,result]of Object.entries(results)){
      assert.deepEqual(result,native[name],view+' exact parity '+name);
      check(view+'_'+name+'_native_parity',true);
      report.cases[view+'/'+name]={status:result.proposal_status,choices:result.choices.map(c=>c.steps.map(s=>s.id)),result_sha256:sha(JSON.stringify(result))};
    }
    check(view+'_complete',results.keyboard_audio.proposal_status==='COMPLETE');
    check(view+'_blocked_audio_not_ready',results.audio_blocked.choices.length===0&&results.audio_blocked.proposal_status==='PARTIAL');
    check(view+'_recomposes_visual',results.visual_alternative.choices[0].steps.at(-1).id.endsWith('#ReviewText'));
    check(view+'_unknown_not_approved',results.unknown_effort.proposal_status==='CONDITIONAL'&&results.unknown_effort.choices.length===0);
    check(view+'_unconfirmed_not_approved',results.not_confirmed.proposal_status==='UNCONFIRMED');
    // UI checks added below use only controls, not prewritten result fixtures.
    const section=page.locator('#composition-panel');
    await section.locator(':scope > summary').focus();await page.keyboard.press('Enter');
    await page.waitForFunction(()=>document.querySelector('#composition-example')&&!document.querySelector('#composition-example').disabled,{}, {timeout:180000});
    await page.locator('#composition-example').click();
    check(view+'_example_unconfirmed',!await page.locator('#composition-confirmed').isChecked());
    await page.locator('#composition-confirmed').check();
    await page.locator('#composition-generate').click();
    await page.waitForFunction(()=>document.querySelector('#composition-result')?.dataset.status==='COMPLETE',{}, {timeout:180000});
    check(view+'_real_ui_complete',await page.locator('#composition-result').isVisible());
    check(view+'_meaningful_result',/teclado/i.test(await page.locator('#composition-result').innerText())&&/revis/i.test(await page.locator('#composition-result').innerText()));
    const screenshots=path.join(root,'tests/.artifacts/composition');
    await fs.mkdir(screenshots,{recursive:true});
    await page.locator('#composition-result').screenshot({path:path.join(screenshots,view+'.png')});
    await page.locator('#composition-confirmed').uncheck();
    check(view+'_revoked_confirmation_hides_result',await page.locator('#composition-result').isHidden());
    const selectField=async(id,value)=>{const field=page.locator('#'+id);await field.evaluate(el=>el.closest('details').open=true);await field.selectOption(value);};
    await selectField('composition-resources-AudioOutput','false');
    await page.locator('#composition-confirmed').check();
    await page.locator('#composition-generate').click();
    await page.waitForFunction(()=>document.querySelector('#composition-result')?.dataset.status==='PARTIAL',{}, {timeout:180000});
    check(view+'_ui_partial_not_ready',await page.locator('[data-composition-choice="complete"]').count()===0);
    await selectField('composition-resources-Display','true');
    await selectField('composition-facts-CanReviewVisualText','true');
    check(view+'_input_change_revokes_confirmation',!await page.locator('#composition-confirmed').isChecked()&&await page.locator('#composition-result').isHidden());
    await page.locator('#composition-confirmed').check();
    await page.locator('#composition-generate').click();
    await page.waitForFunction(()=>document.querySelector('#composition-result')?.dataset.status==='COMPLETE',{}, {timeout:180000});
    check(view+'_ui_visual_recomposition',/visual/i.test(await page.locator('[data-composition-choice="complete"]').first().innerText()));
    await selectField('composition-facts-KeyboardEffortAcceptable','');
    await page.locator('#composition-confirmed').check();
    await page.locator('#composition-generate').click();
    await page.waitForFunction(()=>document.querySelector('#composition-result')?.dataset.status==='CONDITIONAL',{}, {timeout:180000});
    await page.locator('[data-composition-question="KeyboardEffortAcceptable"]').click();
    check(view+'_question_focuses_missing_field',await page.locator('#composition-facts-KeyboardEffortAcceptable').evaluate(el=>el===document.activeElement));
    check(view+'_partial_documentary_status_visible_in_dom',/candidato|reconstru/i.test(await page.locator('#composition-result').textContent()));
    await page.setViewportSize({width:320,height:900});
    check(view+'_reflow_320',await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));
    await page.setViewportSize({width:1280,height:900});
    await page.evaluate(()=>document.documentElement.style.fontSize='200%');
    check(view+'_text_200',await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));
    await page.evaluate(()=>document.documentElement.style.fontSize='');
    await page.locator('#composition-task').selectOption('TaskReviewExistingText');
    await page.locator('#composition-reset').click();
    check(view+'_reset_clears_error_and_task_help',await page.locator('#composition-error').innerText()===''&&/produz|produç|express/i.test(await page.locator('#composition-task-help').innerText()));
    await page.locator('#clear-case').click();
    await page.waitForFunction(()=>document.querySelector('#health')?.dataset.state==='ready'&&document.querySelector('#main')?.getAttribute('aria-busy')==='false',{}, {timeout:180000});
    check(view+'_clear_discards',!await page.locator('#composition-confirmed').isChecked()&&await page.locator('#composition-result').isHidden());
    check(view+'_no_storage',await page.evaluate(()=>localStorage.length===0&&sessionStorage.length===0));
    await page.close();
  }
  check('no_external_case_requests',report.external_requests.length===0);
  check('no_page_errors',report.errors.length===0);
  report.passed=true;
}catch(error){report.passed=false;report.failure=String(error.message);process.exitCode=1;}
finally{
  await browser.close();await new Promise(resolve=>server.close(resolve));
  const out=path.join(root,'evidence',process.env.COMPOSITION_PUBLIC_URL?'composition-public.json':'composition-browser.json');
  await fs.writeFile(out,JSON.stringify(report,null,2)+'\n');
  console.log(JSON.stringify({passed:report.passed,checks:Object.keys(report.checks).length,failure:report.failure||null},null,2));
}
