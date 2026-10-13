// Public smoke for AMADO_SITUATED_1. Invoke only after an authorized deployment.
// Synthetic data only. The historical public-smoke.mjs remains unchanged.
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import path from 'node:path';
import crypto from 'node:crypto';
import {execFileSync} from 'node:child_process';
import {fileURLToPath,pathToFileURL} from 'node:url';

assert(process.env.SMOKE_PUBLIC_URL,'Set SMOKE_PUBLIC_URL explicitly after deployment; no implicit public run.');
const target=new URL(process.env.SMOKE_PUBLIC_URL);
const local=['127.0.0.1','localhost','[::1]'].includes(target.hostname);
assert(target.protocol==='https:'||(local&&target.protocol==='http:'),'Use HTTPS, except a local dry run.');
assert(!target.username&&!target.password&&!target.search&&!target.hash,'Use an uncredentialed site root URL.');
const base=target.href.replace(/\/?$/,'/'),origin=target.origin;
const staticStyleQuery=new URL('amado/styles.css?v=1.2.0-rc4-ui3-demo-fix2-conexoes',base).href;
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const modules=process.env.AMADO_NODE_MODULES||path.join(process.env.USERPROFILE,'.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules');
const {chromium}=await import(pathToFileURL(path.join(modules,'playwright/index.mjs')).href);
const sha=bytes=>crypto.createHash('sha256').update(bytes).digest('hex');
const expected=JSON.parse(await fs.readFile(path.join(root,'web/amado/manifest.json'),'utf8'));
const report={type:local?'LOCAL_DRY_RUN_OF_SITUATED_PUBLIC_SMOKE':'SYNTHETIC_SITUATED_PUBLIC_SMOKE_NOT_PARTICIPANT_SESSION',
  url:base,checked_at:new Date().toISOString(),test_sha256:sha(await fs.readFile(fileURLToPath(import.meta.url))),
  expected_commit:process.env.SMOKE_EXPECTED_COMMIT||execFileSync('git',['rev-parse','HEAD'],{cwd:root,encoding:'utf8'}).trim(),
  commit_observation:'Expected deployment commit from the publisher or local checkout; serving identity is verified independently by content hashes.',
  checks:{},assets:{},download_assets:{},flows:{},errors:[],external_requests:[],completed:false,passed:false,
  static_query_allowlist:['amado/styles.css?v=1.2.0-rc4-ui3-demo-fix2-conexoes'],limits:[
    'Synthetic browser verification, not human, clinical, learning-outcome or WCAG-conformance validation.',
    'Serving identity is checked using the current local manifest and remote content hashes, not an assumed deployment commit.',
    'Conditional operations are not a complete solution. Unknown personal abilities remain unknown.',
    'Speech is mocked to prevent audio; microphone accuracy and real screen readers are not tested.',
    'This smoke does not replace the local regression or native/worker canonical parity checks.'
  ]};
const check=(name,result)=>{report.checks[name]=Boolean(result);assert(result,name);};
const artifacts=path.join(root,'tests/.artifacts',local?'situated-public-dry-run':'situated-public');
await fs.mkdir(artifacts,{recursive:true});
const reportFile=local?path.join(artifacts,'report.json'):path.join(root,'evidence/situated-public-smoke.json');
const requests=[];let browser,context;
const ready=async page=>{
  await page.waitForFunction(()=>['ready','error'].includes(document.querySelector('#health')?.dataset.state)&&document.querySelector('#main')?.getAttribute('aria-busy')==='false',{}, {timeout:60000});
  assert.equal(await page.locator('#health').getAttribute('data-state'),'ready','Public packaged runtime must initialize.');
};
const current=page=>page.evaluate(()=>window.__publicSituated.current);
const generated=page=>page.evaluate(()=>window.__publicSituated.generated);
const newPage=async view=>{
  const page=await context.newPage();page.on('pageerror',error=>report.errors.push(error.message));
  await page.goto(base+'amado/'+view,{waitUntil:'domcontentloaded'});await ready(page);return page;
};
async function finishQuestions(page,key){
  let count=0;
  while(await page.locator('#case-questions').isVisible()){
    assert(++count<=3,'No more than three questions in one round.');
    assert(Number(await page.locator('#question-progress').getAttribute('data-total'))<=3);
    const state=await current(page),row=page.locator('#questions-form [data-question]'),id=await row.getAttribute('data-question');
    const question=state.questions.find(q=>q.id===id);assert(question,'Visible question belongs to engine response.');
    if(question.field==='active_situation_id'){
      const selected=state.context.situations.find(s=>s.kind==='material_access')||state.context.situations[0];
      await row.locator('input[value="'+selected.id+'"]').check();await page.locator('#answer-questions').click();
    }else if(question.type==='text')await page.locator('#answer-unknown').click();
    else{await row.locator('input[value="unknown"]').check();await page.locator('#answer-questions').click();}
    await page.waitForFunction(previous=>!document.querySelector('#case-review').hidden||document.querySelector('#questions-form [data-question]')?.dataset.question!==previous,id,{timeout:60000});
  }
  await page.locator('#case-review').waitFor({state:'visible',timeout:60000});
  check(key+'_max_three_questions',count<=3);return count;
}
async function generateSimple(page){
  assert(await page.locator('#generate-orientation').isDisabled(),'Explicit confirmation required.');
  await page.locator('#case-confirmed').check();await page.locator('#generate-orientation').click();
  await page.locator('#orientation-result').waitFor({state:'visible',timeout:60000});return generated(page);
}
try{
  browser=await chromium.launch({headless:true,executablePath:process.env.AMADO_CHROMIUM||'C:/Program Files/Google/Chrome/Application/chrome.exe'});
  report.browser=browser.version();context=await browser.newContext({viewport:{width:1280,height:900},reducedMotion:'reduce'});
  await context.route('**/*',route=>{
    const request=route.request();requests.push({url:request.url(),method:request.method(),has_body:Boolean(request.postData())});
    if(!request.url().startsWith(origin+'/')&&!request.url().startsWith('blob:')){report.external_requests.push(request.url());return route.abort();}
    return route.continue();
  });
  const manifestResponse=await context.request.get(base+'amado/manifest.json',{headers:{'Cache-Control':'no-cache'}});
  check('public_manifest_http_200',manifestResponse.ok());
  const manifestBytes=await manifestResponse.body(),manifest=JSON.parse(manifestBytes.toString());
  report.public_manifest_sha256=sha(manifestBytes);report.version=manifest.version;report.build=manifest;
  assert.deepEqual(manifest,expected);check('served_manifest_matches_current_build',true);
  const assets=[...Object.entries(expected.frontend_sha256).map(([file,hash])=>['amado/'+file,hash]),
    ...Object.entries(expected.site_assets_sha256).map(([file,hash])=>[file,hash]),
    ...Object.entries(expected.runtime).map(([file,item])=>['amado/runtime/'+file,item.sha256]),
    ['amado/engine.py',expected.core_sha256],['amado/bridge.py',expected.bridge_sha256],['amado/assets/base.zip',expected.base_zip_sha256]];
  for(let start=0;start<assets.length;start+=4)await Promise.all(assets.slice(start,start+4).map(async([file,hash])=>{
    const response=await context.request.get(base+file,{headers:{'Cache-Control':'no-cache'}});assert(response.ok(),file+' HTTP response');
    const bytes=await response.body(),actual=sha(bytes);report.assets[file]={bytes:bytes.length,expected_sha256:hash,served_sha256:actual,passed:actual===hash};
    assert.equal(actual,hash,'Published content hash: '+file);
  }));
  check('served_html_engine_base_runtime_catalog_hashes',Object.values(report.assets).every(item=>item.passed));
  for(const file of ['downloads/mado-public.ttl','downloads/mado.owl','downloads/main.ttl','downloads/main.shacl.ttl']){
    const hash=sha(await fs.readFile(path.join(root,'web',file)));
    const response=await context.request.get(base+file,{headers:{'Cache-Control':'no-cache'}});assert(response.ok(),file+' HTTP response');
    const bytes=await response.body(),actual=sha(bytes);report.download_assets[file]={bytes:bytes.length,expected_sha256:hash,served_sha256:actual,passed:actual===hash};
    assert.equal(actual,hash,'Published download hash: '+file);
  }
  check('downloads_current',Object.keys(report.download_assets).length===4&&Object.values(report.download_assets).every(item=>item.passed));
  await context.addInitScript(()=>{
    window.__publicSituated={current:null,generated:null,speaks:0};
    window.SpeechSynthesisUtterance=class{constructor(text){this.text=text;}};
    Object.defineProperty(window,'speechSynthesis',{configurable:true,value:{getVoices:()=>[],speak:()=>window.__publicSituated.speaks++,cancel:()=>{},addEventListener:()=>{},removeEventListener:()=>{}}});
    const NativeWorker=window.Worker;
    window.Worker=class extends NativeWorker{
      constructor(...args){super(...args);this.operations=new Map();this.addEventListener('message',event=>{
        if(event.data.type!=='result')return;const data=event.data.data,operation=this.operations.get(event.data.id);
        if(data?.current?.context)window.__publicSituated.current=data.current;
        else if(data?.context)window.__publicSituated.current=data;
        if(operation==='generate'||operation==='compose')window.__publicSituated.generated=data;
      });}
      postMessage(data,...rest){this.operations.set(data.id,data.operation);return super.postMessage(data,...rest);}
    };
  });
  const narrative=await newPage('index.html');
  await narrative.locator('#case-narrative').fill('Tenho uma turma de 12 estudantes. Alguns têm dificuldade de mobilidade, deficiência cognitiva, na verdade. Vou apresentar slides enquanto explico um conteúdo. Cada estudante acessa o material em seu próprio computador. Depois faremos exercícios.');
  await narrative.locator('#analyze-case').click();await narrative.locator('#case-understanding').waitFor({state:'visible',timeout:60000});
  let state=await current(narrative);
  check('versioned_situated_intake',state.context.situated_version==='1.0'&&state.context.situations.length===3);
  check('self_correction_preserved',state.context.assertions.some(a=>a.kind==='reported_condition'&&a.value==='mobilidade'&&a.state==='RETIRADO_POR_CORRECAO'));
  check('no_diagnostic_capabilities',state.participations.filter(p=>p.reported_condition?.text).every(p=>!p.caracteristica_ids.length&&!p.modalidade_ids.length&&!p.recurso_operado_ids.length));
  check('exercise_medium_remains_unknown',state.context.situations.find(s=>s.kind==='exercise').resource_ids.length===0);
  check('understanding_before_questions',await narrative.locator('#case-questions').isHidden());
  await narrative.locator('#continue-understanding').click();const questions=await finishQuestions(narrative,'narrative');
  state=await current(narrative);const unknownAnswers=state.context.question_answers.filter(answer=>answer.state==='UNKNOWN');
  check('unknown_saved_without_repetition',unknownAnswers.length>0&&unknownAnswers.every(answer=>!state.questions.some(question=>question.id===answer.question_id)));
  const output=await generateSimple(narrative);check('narrative_uses_situated_result',output.result_contract==='AMADO_SITUATED_1'&&output.proposal_status!=='COMPLETE');
  report.flows.narrative={contract:output.result_contract,status:output.status,proposal_status:output.proposal_status,questions};
  await narrative.screenshot({path:path.join(artifacts,'narrative.png'),fullPage:true});
  await narrative.close();
  for(const view of ['index.html','guiado.html']){
    const page=await newPage(view);await page.locator('#case-examples > summary').click();
    await page.locator('#case-template').selectOption('CTX-TRANSFERENCIA-RECURSO-DIGITAL-01');await page.locator('#load-example').click();
    await page.locator('#case-understanding').waitFor({state:'visible',timeout:60000});await page.locator('#continue-understanding').click();
    await finishQuestions(page,view);const result=await generateSimple(page);
    check(view+'_situated_conditional_operations',result.result_contract==='AMADO_SITUATED_1'&&result.pending_candidates.length>0&&result.proposal_status!=='COMPLETE');
    check(view+'_role_labels_not_session_ids',result.pending_candidates.every(candidate=>candidate.participant_label&&!candidate.participant_label.startsWith('PART-CASO')));
    check(view+'_rendered_action_grounding_links',await page.locator('.situated-action').count()>0&&await page.locator('.step-grounding a[href^="http"]').count()>0);
    check(view+'_no_automatic_speech',await page.evaluate(()=>window.__publicSituated.speaks===0));
    check(view+'_no_case_storage',await page.evaluate(async()=>localStorage.length===0&&sessionStorage.length===0&&document.cookie===''&&(await indexedDB.databases()).length===0&&(await caches.keys()).length===0));
    report.flows[view]={contract:result.result_contract,status:result.status,proposal_status:result.proposal_status,operations:result.pending_candidates.flatMap(candidate=>candidate.steps).length};
    await page.locator('#orientation-title').scrollIntoViewIfNeeded();await page.screenshot({path:path.join(artifacts,view+'.png')});await page.close();
  }
  for(const view of ['completo.html','completo-guiado.html']){
    const page=await newPage(view);await page.locator('input[name="reported-confirmation"][value="yes"]').check();await page.locator('#confirm-reported').click();
    await page.waitForFunction(()=>document.querySelector('#main').getAttribute('aria-busy')==='false',{}, {timeout:60000});
    await page.locator('#mapping-confirmed').check();await page.locator('#generate-known').click();await page.locator('#saida').waitFor({state:'visible',timeout:60000});
    const result=await generated(page);
    check(view+'_situated_actions_and_grounding',result?.result_contract==='AMADO_SITUATED_1'&&await page.locator('.situated-action').count()>0&&await page.locator('.step-grounding').count()>0);
    check(view+'_current_footer',(await page.locator('.version-note').innerText()).includes('MADO 1.5.0-rc1'));
    check(view+'_no_runtime_error',!(await page.locator('#runtime-error').innerText()).trim());await page.close();
  }
  const home=await context.newPage();home.on('pageerror',error=>report.errors.push(error.message));await home.goto(base);
  await home.locator('[data-explanation-pilot-details] > summary').click();await home.locator('[data-explanation-pilot] .situated-action').first().waitFor({state:'visible',timeout:60000});
  check('home_situated_pilot',await home.locator('[data-explanation-pilot] .step-grounding').count()>0);await home.close();
  check('no_case_transmission',requests.every(request=>request.method==='GET'&&!request.has_body&&request.url.startsWith(origin+'/')&&(!new URL(request.url).search||request.url===staticStyleQuery)));
  check('no_javascript_errors',report.errors.length===0);report.completed=true;report.passed=true;
}catch(error){
  report.passed=false;report.failure=String(error.stack||error).replaceAll(root,'<PROJECT>').replaceAll(root.replaceAll('\\','/'),'<PROJECT>');process.exitCode=1;
}finally{
  await browser?.close();await fs.writeFile(reportFile,JSON.stringify(report,null,2)+'\n');
  console.log(JSON.stringify({passed:report.passed,type:report.type,checks:Object.keys(report.checks).length,assets:Object.keys(report.assets).length,failure:report.failure||null},null,2));
}
