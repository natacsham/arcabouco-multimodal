// Synthetic public-flow regression. No personal narrative is written to evidence.
// Keeps historical simple-flow-browser.mjs as evidence of the former contract.
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import path from 'node:path';
import http from 'node:http';
import crypto from 'node:crypto';
import {execFileSync} from 'node:child_process';
import {fileURLToPath,pathToFileURL} from 'node:url';

const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const web=path.join(root,'web'),prefix='/arcabouco-multimodal/';
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
const base=`http://127.0.0.1:${server.address().port}${prefix}`,origin=new URL(base).origin;
// Both preserved complete views contain this exact static stylesheet version.
// No other query parameters, including case data, are allowed by this test.
const staticStyleQuery=new URL('amado/styles.css?v=1.2.0-rc4-ui3-demo-fix2-conexoes',base).href;
const sha=value=>crypto.createHash('sha256').update(value).digest('hex');
const report={type:'SYNTHETIC_SITUATED_FLOW_NOT_PARTICIPANT_SESSION',checked_at:new Date().toISOString(),checks:{},errors:[],
  limits:['Synthetic regression only; not human, clinical, accessibility-conformance or learning-outcome validation.',
    'Native/worker canonical comparison translates session IDs and excludes their derived hashes, not substantive conditions, scope, sources or decisions.',
    'No microphone or speech-recognition accuracy test; speech output is mocked to verify explicit controls without playing audio.',
    'NVDA, VoiceOver and TalkBack not executed. Computed contrast and keyboard smoke do not prove WCAG conformance.']};
report.build=JSON.parse(await fs.readFile(path.join(web,'amado/manifest.json'),'utf8'));
report.static_query_allowlist=['amado/styles.css?v=1.2.0-rc4-ui3-demo-fix2-conexoes'];
report.test_sha256=sha(await fs.readFile(fileURLToPath(import.meta.url)));
const check=(name,value)=>{report.checks[name]=Boolean(value);assert(value,name);};
const browser=await chromium.launch({headless:true,executablePath:process.env.AMADO_CHROMIUM||path.join(process.env.LOCALAPPDATA,'ms-playwright/chromium-1243/chrome-win64/chrome.exe')});
report.browser=browser.version();
const context=await browser.newContext({viewport:{width:1280,height:900},reducedMotion:'reduce'});
await context.addInitScript(()=>{
  window.__situatedProbe={records:[],current:null,generated:null};
  window.__readingProbe={speaks:0,cancels:0};
  window.SpeechSynthesisUtterance=class{constructor(text){this.text=text;}};
  Object.defineProperty(window,'speechSynthesis',{configurable:true,value:{
    getVoices:()=>[{localService:true,lang:'pt-BR',name:'Synthetic local voice'}],
    speak:()=>{window.__readingProbe.speaks++;},cancel:()=>{window.__readingProbe.cancels++;},
    addEventListener:()=>{},removeEventListener:()=>{}
  }});
  const NativeWorker=window.Worker;
  window.Worker=class extends NativeWorker{
    constructor(...args){super(...args);this.records=new Map();this.addEventListener('message',event=>{
      if(event.data.type!=='result')return;
      const record=this.records.get(event.data.id);if(!record)return;
      record.response=structuredClone(event.data.data);
      const data=record.response;
      if(data?.current?.context)window.__situatedProbe.current=data.current;
      else if(data?.context)window.__situatedProbe.current=data;
      if(record.request.operation==='generate')window.__situatedProbe.generated=data;
    });}
    postMessage(data,...rest){
      if(['start','analyze','update','generate'].includes(data.operation)){
        const record={request:structuredClone(data)};window.__situatedProbe.records.push(record);this.records.set(data.id,record);
      }
      return super.postMessage(data,...rest);
    }
  };
});
const requests=[];
await context.route('**/*',route=>{
  const request=route.request();requests.push({url:request.url(),method:request.method(),body:request.postData()||''});
  if(!request.url().startsWith(origin+'/')&&!request.url().startsWith('blob:'))return route.abort();
  return route.continue();
});
const ready=async page=>{
  await page.waitForFunction(()=>['ready','error'].includes(document.querySelector('#health')?.dataset.state)&&document.querySelector('#main')?.getAttribute('aria-busy')==='false',{}, {timeout:60000});
  assert.equal(await page.locator('#health').getAttribute('data-state'),'ready','Packaged runtime must initialize; rebuild if manifest hashes changed');
};
const state=page=>page.evaluate(()=>window.__situatedProbe.current);
const synthetic='Tenho uma turma de 12 estudantes. Alguns têm dificuldade de mobilidade, deficiência cognitiva, na verdade. Vou apresentar slides enquanto explico um conteúdo. Cada estudante acessa o material em seu próprio computador. Depois faremos exercícios.';
const artifacts=path.join(root,'tests/.artifacts/situated-flow');await fs.mkdir(artifacts,{recursive:true});

// Replays the actual bridge operations, translating only per-session IDs.
const replayPython=String.raw`
import sys,json,importlib.util
from pathlib import Path
sys.path[:0]=[str(Path.cwd()),str(Path.cwd()/"vendor")]
spec=importlib.util.spec_from_file_location("situated_bridge","web/amado/bridge.py")
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);m.initialize()
records=json.loads(sys.stdin.buffer.read().decode("utf-8")); mapping={}
def replace(value, ids):
    if isinstance(value,str):
        for old,new in sorted(ids.items(),key=lambda row:-len(row[0])): value=value.replace(old,new)
        return value
    if isinstance(value,list): return [replace(v,ids) for v in value]
    if isinstance(value,dict): return {replace(k,ids):replace(v,ids) for k,v in value.items()}
    return value
def bind(old,new):
    old=old.get("current",old);new=new.get("current",new)
    if "context" not in old or "context" not in new:return
    mapping[old["context"]["id"]]=new["context"]["id"]
    for label,left,right in [("participations",old.get("participations",[]),new.get("participations",[]))]+[(key,old["context"].get(key,[]),new["context"].get(key,[])) for key in ("situations","assertions")]:
        if len(left)!=len(right): raise AssertionError(f"Different {label} counts on {request['operation']}: worker={len(left)}, native={len(right)}")
        for a,b in zip(left,right):mapping[a["id"]]=b["id"]
    all_questions=list(m.ENGINE.current["context"].get("question_manifest",{}).values())
    for question in old.get("questions",[]):
        target=replace(question,mapping)
        candidates=[q for q in all_questions if all(q.get(key,"")==target.get(key,"") for key in ("field","situation_id","participant_id"))]
        if len(candidates)==1:mapping[question["id"]]=candidates[0]["id"]
last={}
for record in records:
    request=replace(record["request"],mapping);request.pop("id",None)
    last=m.dispatch(request)
    bind(record["response"],last)
print(json.dumps(replace(last,{v:k for k,v in mapping.items()}),ensure_ascii=True))
`;
const canonical=value=>{
  if(typeof value==='string')return value.replace(/\b(?:check|proposal|occurrence|question)-[0-9a-f]{16,64}\b/g,match=>match.split('-')[0]+'-<volatile>');
  if(Array.isArray(value))return value.map(canonical);
  if(value&&typeof value==='object')return Object.fromEntries(Object.keys(value).sort().filter(key=>!['created_at','generated_at','checked_at','context_sha256'].includes(key)).map(key=>[key,canonical(value[key])]));
  return value;
};
async function contrastSamples(page){
  return page.evaluate(()=>{
    const rgba=text=>{const m=text.match(/rgba?\(([^)]+)\)/);if(!m)return null;const v=m[1].split(/[,\s/]+/).filter(Boolean).map(Number);return [...v.slice(0,3),v[3]??1];};
    const blend=(a,b)=>[0,1,2].map(i=>a[i]*a[3]+b[i]*(1-a[3]));
    const lum=c=>c.map(v=>v/255).map(v=>v<=.04045?v/12.92:((v+.055)/1.055)**2.4).reduce((sum,v,i)=>sum+v*[.2126,.7152,.0722][i],0);
    const ratio=(a,b)=>(Math.max(lum(a),lum(b))+.05)/(Math.min(lum(a),lum(b))+.05);
    const bg=el=>{let color=[255,255,255];const stack=[];for(let n=el;n;n=n.parentElement){const c=rgba(getComputedStyle(n).backgroundColor);if(c)stack.push(c);}for(const c of stack.reverse())color=blend(c,color);return color;};
    const rows=[...document.querySelectorAll('#orientation-main h4,#orientation-main p,#orientation-main li,#orientation-main summary,#read-orientation')].filter(el=>el.checkVisibility()).map(el=>{
      const style=getComputedStyle(el),background=bg(el),large=parseFloat(style.fontSize)>=24||(parseFloat(style.fontSize)>=18.66&&parseInt(style.fontWeight)>=700);
      return {kind:'text',element:el.tagName,class_name:el.className,ratio:ratio(blend(rgba(style.color),background),background),minimum:large?3:4.5};
    });
    const el=document.activeElement,style=getComputedStyle(el),background=bg(el.parentElement);
    rows.push({kind:'focus',element:el.tagName,ratio:style.outlineStyle!=='none'&&parseFloat(style.outlineWidth)>0?ratio(blend(rgba(style.outlineColor),background),background):0,minimum:3});
    return rows;
  });
}
let page;
try{
  page=await context.newPage();page.on('pageerror',error=>report.errors.push(error.message));
  await page.goto(base+'amado/index.html');await ready(page);
  check('served_manifest_matches_build',JSON.stringify(await (await context.request.get(base+'amado/manifest.json')).json())===JSON.stringify(report.build));
  check('single_free_narrative_entry',await page.locator('textarea:visible').count()===1);
  await page.locator('#case-narrative').fill(synthetic);await page.locator('#analyze-case').click();
  await page.locator('#case-understanding').waitFor({state:'visible',timeout:180000});
  let current=await state(page),situations=current.context.situations;
  check('versioned_situated_contract',current.context.situated_version==='1.0');
  check('total_and_unknown_subset',current.participations.some(p=>p.quantidade===12&&p.group_scope==='TOTAL')&&current.participations.some(p=>p.reported_condition&&p.quantidade===null));
  check('self_correction_retires_mobility',current.context.assertions.some(a=>a.kind==='reported_condition'&&a.value==='mobilidade'&&a.state==='RETIRADO_POR_CORRECAO'));
  check('no_diagnosis_to_capability',current.participations.filter(p=>p.reported_condition).every(p=>!p.caracteristica_ids.length&&!p.modalidade_ids.length&&!p.recurso_operado_ids.length));
  check('distinct_actions_and_unknown_exercise_medium',situations.length===3&&situations.find(s=>s.kind==='exercise').resource_ids.length===0);
  check('understanding_precedes_questions',await page.locator('#case-questions').isHidden());
  await page.locator('#continue-understanding').click();
  const answered=[];let selectedPriority='';
  while(await page.locator('#case-questions').isVisible()){
    const progress=page.locator('#question-progress');
    check('at_most_three_total_per_round',Number(await progress.getAttribute('data-total'))<=3&&answered.length<3);
    const row=page.locator('#questions-form [data-question]'),id=await row.getAttribute('data-question');
    current=await state(page);const question=current.questions.find(q=>q.id===id);assert(question,'Rendered question belongs to current engine response');
    answered.push({id,field:question.field});
    if(question.field==='active_situation_id'){
      selectedPriority=current.context.situations.find(s=>s.kind==='material_access').id;
      await row.locator('input[value="'+selectedPriority+'"]').check();await page.locator('#answer-questions').click();
    }else if(question.type==='text')await page.locator('#answer-unknown').click();
    else {await row.locator('input[value="unknown"]').check();await page.locator('#answer-questions').click();}
    await page.waitForFunction(previous=>!document.querySelector('#case-review').hidden||document.querySelector('#questions-form [data-question]')?.dataset.question!==previous,id,{timeout:180000});
  }
  await page.locator('#case-review').waitFor({state:'visible',timeout:180000});
  current=await state(page);
  check('priority_preserves_other_situations',Boolean(selectedPriority)&&current.context.active_situation_id===selectedPriority&&current.context.situations.length===3);
  check('unknown_persisted_not_reasked',current.context.question_answers.some(a=>a.state==='UNKNOWN')&&answered.every(a=>!current.questions.some(q=>q.id===a.id)));
  check('generation_requires_confirmation',await page.locator('#generate-orientation').isDisabled());
  const condition=current.context.assertions.find(a=>a.kind==='reported_condition'&&a.state!=='RETIRADO_POR_CORRECAO');
  await page.locator('#edit-case').click();await page.locator('[data-revision="assertion-remove:'+condition.id+'"]').check();
  await page.locator('#save-case').click();await page.locator('#case-review').waitFor({state:'visible',timeout:180000});
  current=await state(page);
  check('review_removes_only_selected_assertion',current.context.assertions.find(a=>a.id===condition.id).state==='RETIRADO_POR_CORRECAO'&&current.context.situations.length===3&&!current.participations.some(p=>p.reported_condition?.text));
  check('review_revokes_confirmation',!current.mapping_confirmed&&await page.locator('#generate-orientation').isDisabled());
  await page.locator('#case-confirmed').check();await page.locator('#generate-orientation').click();
  await page.locator('#orientation-result').waitFor({state:'visible',timeout:180000});
  const probe=await page.evaluate(()=>window.__situatedProbe),result=probe.generated;
  check('public_result_contract',result.result_contract==='AMADO_SITUATED_1');
  check('result_scope_is_selected_situation',Boolean(result.situation_results?.length)&&result.situation_results.every(s=>s.situation_id===selectedPriority));
  check('result_explains_pending_or_missing_support',(await page.locator('#orientation-main').innerText()).trim().length>40);
  check('sources_collapsed_initially',await page.locator('#orientation-sources').getAttribute('open')===null);
  await page.screenshot({path:path.join(artifacts,'situated-orientation.png'),fullPage:true});
  const native=JSON.parse(execFileSync(process.env.AMADO_PYTHON||'python',['-B','-W','ignore','-c',replayPython],{
    cwd:root,encoding:'utf8',input:JSON.stringify(probe.records),maxBuffer:64*1024*1024}));
  const initialParity=JSON.stringify(canonical(result))===JSON.stringify(canonical(native));
  report.canonical_result_sha256=sha(JSON.stringify(canonical(result)));
  report.result={contract:result.result_contract,status:result.status,question_count:answered.length};
  await page.locator('#new-case').click();await ready(page);
  await page.locator('#case-examples > summary').click();
  await page.locator('#case-template').selectOption('CTX-TRANSFERENCIA-RECURSO-DIGITAL-01');
  await page.locator('#load-example').click();
  await page.locator('#case-understanding').waitFor({state:'visible',timeout:180000});
  await page.locator('#continue-understanding').click();
  if(await page.locator('#case-questions').isVisible())await page.locator('#skip-questions').click();
  await page.locator('#case-review').waitFor({state:'visible',timeout:180000});
  await page.locator('#case-confirmed').check();await page.locator('#generate-orientation').click();
  await page.locator('#orientation-result').waitFor({state:'visible',timeout:180000});
  const positive=await page.evaluate(()=>window.__situatedProbe.generated);
  check('prepared_example_has_grounded_conditional_operations',positive.result_contract==='AMADO_SITUATED_1'&&positive.pending_candidates.length>0&&positive.proposal_status!=='COMPLETE');
  check('prepared_example_uses_role_labels',positive.pending_candidates.every(candidate=>candidate.participant_label&&!candidate.participant_label.startsWith('PART-CASO')));
  check('actions_and_conditions_rendered',await page.locator('.situated-action').count()>0&&await page.locator('.step-conditional').count()>0);
  check('no_automatic_speech',await page.evaluate(()=>window.__readingProbe.speaks===0));
  await page.locator('#read-orientation').focus();await page.keyboard.press('Enter');
  check('keyboard_starts_local_speech',await page.evaluate(()=>window.__readingProbe.speaks===1)&&await page.locator('#read-orientation').getAttribute('aria-pressed')==='true');
  await page.keyboard.press('Enter');
  check('same_control_stops_speech',await page.locator('#read-orientation').innerText()==='Ouvir'&&await page.locator('#read-orientation').getAttribute('aria-pressed')==='false');
  const grounding=page.locator('.situated-action summary').filter({hasText:'Por que esta ação foi sugerida?'}).first();
  await grounding.focus();await page.keyboard.press('Enter');
  check('keyboard_opens_action_grounding',await grounding.evaluate(el=>el.parentElement.open));
  check('grounding_links_real_sources',await page.locator('.situated-action .step-grounding a[href^="http"]').count()>0);
  check('no_raw_object_rendering',!(await page.locator('#orientation-main').innerText()).includes('[object Object]'));
  await page.locator('#orientation-details > summary').focus();await page.keyboard.press('Enter');
  check('coverage_exposed_by_person_and_situation',/Cobertura por pessoa e situação/.test(await page.locator('#orientation-detail-body').innerText()));
  await page.locator('#orientation-sources > summary').focus();await page.keyboard.press('Enter');
  check('source_disclosure_has_links',await page.locator('#orientation-sources-body a[href^="http"]').count()>0);
  await grounding.focus();
  report.contrast={normal:await contrastSamples(page)};
  check('new_text_and_focus_sampled_contrast',report.contrast.normal.length>10&&report.contrast.normal.every(s=>s.ratio>=s.minimum));
  await page.locator('[data-site-contrast]').focus();await page.keyboard.press('Enter');await grounding.focus();
  report.contrast.high=await contrastSamples(page);
  check('high_contrast_new_text_and_focus',report.contrast.high.every(s=>s.ratio>=s.minimum));
  await page.locator('[data-site-contrast]').focus();await page.keyboard.press('Enter');
  await page.screenshot({path:path.join(artifacts,'conditional-operations.png'),fullPage:true});
  await page.locator('#orientation-title').scrollIntoViewIfNeeded();
  await page.screenshot({path:path.join(artifacts,'conditional-operations-viewport.png')});
  const positiveProbe=await page.evaluate(()=>window.__situatedProbe);
  const positiveNative=JSON.parse(execFileSync(process.env.AMADO_PYTHON||'python',['-B','-W','ignore','-c',replayPython],{
    cwd:root,encoding:'utf8',input:JSON.stringify(positiveProbe.records),maxBuffer:64*1024*1024}));
  const conditionalParity=JSON.stringify(canonical(positive))===JSON.stringify(canonical(positiveNative));
  report.conditional_result={status:positive.status,proposal_status:positive.proposal_status,operation_count:positive.pending_candidates.flatMap(c=>c.steps).length,
    canonical_sha256:sha(JSON.stringify(canonical(positive)))};
  for(const width of [375,320]){
    await page.setViewportSize({width,height:900});
    check('layout_'+width+'_no_horizontal_overflow',await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));
    await page.evaluate(()=>document.documentElement.style.fontSize='200%');
    check('layout_'+width+'_text_200_percent',await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));
    if(width===375){
      await page.locator('#orientation-title').scrollIntoViewIfNeeded();
      await page.screenshot({path:path.join(artifacts,'conditional-375-text200.png')});
    }
    await page.evaluate(()=>document.documentElement.style.fontSize='');
  }
  for(const view of ['completo.html','completo-guiado.html']){
    const full=await context.newPage();full.on('pageerror',error=>report.errors.push(error.message));
    await full.goto(base+'amado/'+view);await ready(full);
    await full.locator('input[name="reported-confirmation"][value="yes"]').check();
    await full.locator('#confirm-reported').click();
    await full.waitForFunction(()=>document.querySelector('#main').getAttribute('aria-busy')==='false',{}, {timeout:180000});
    await full.locator('#mapping-confirmed').check();await full.locator('#generate-known').click();
    await full.locator('#saida').waitFor({state:'visible',timeout:180000});
    const output=await full.evaluate(()=>window.__situatedProbe.generated);
    check(view+'_situated_contract',output?.result_contract==='AMADO_SITUATED_1');
    check(view+'_actions_and_grounding',await full.locator('.situated-action').count()>0&&await full.locator('.step-grounding').count()>0);
    check(view+'_no_runtime_error',!(await full.locator('#runtime-error').innerText()).trim());
    check(view+'_current_version_footer',(await full.locator('.version-note').innerText()).includes('MADO '+report.build.version));
    await full.screenshot({path:path.join(artifacts,view+'-situated.png'),fullPage:true});
    await full.close();
  }
  const home=await context.newPage();home.on('pageerror',error=>report.errors.push(error.message));
  await home.goto(base);
  await home.locator('[data-explanation-pilot-details] > summary').focus();await home.keyboard.press('Enter');
  await home.locator('[data-explanation-pilot] .situated-action').first().waitFor({state:'visible',timeout:60000});
  check('home_pilot_uses_current_situated_actions',await home.locator('[data-explanation-pilot] .step-grounding').count()>0);
  await home.screenshot({path:path.join(artifacts,'home-situated-pilot.png'),fullPage:true});
  await home.close();
  check('no_case_storage',await page.evaluate(async()=>localStorage.length===0&&sessionStorage.length===0&&document.cookie===''&&(await indexedDB.databases()).length===0&&(await caches.keys()).length===0));
  check('no_case_transmission',requests.every(r=>r.method==='GET'&&r.url.startsWith(origin+'/')&&!r.body&&(!new URL(r.url).search||r.url===staticStyleQuery)));
  check('no_javascript_errors',report.errors.length===0);
  check('native_bridge_worker_canonical_parity',initialParity);
  check('conditional_native_worker_canonical_parity',conditionalParity);
  // Reuse the three disclosed synthetic fixtures, not bespoke browser answers.
  const replayCases=JSON.parse(execFileSync(process.env.AMADO_PYTHON||'python',['-B','-W','ignore','-c',
    "import sys,json;sys.path.insert(0,'tests');from test_narrative_to_actions import export_replays;print(json.dumps(export_replays(),ensure_ascii=True))"],
    {cwd:root,encoding:'utf8',maxBuffer:64*1024*1024}));
  report.narrative_cases=[];
  for(const replayCase of replayCases){
    const workerResult=await page.evaluate(async records=>{
      const {request}=await import('./client.mjs');
      const mapping=new Map();
      const replace=(value,ids)=>{
        if(typeof value==='string'){
          for(const [old,newId] of [...ids].sort((a,b)=>b[0].length-a[0].length))value=value.split(old).join(newId);
          return value;
        }
        if(Array.isArray(value))return value.map(v=>replace(v,ids));
        if(value&&typeof value==='object')return Object.fromEntries(Object.entries(value).map(([k,v])=>[replace(k,ids),replace(v,ids)]));
        return value;
      };
      let last;
      for(const record of records){
        const call=replace(record.request,mapping);
        last=await request(call.operation,{payload:call.payload});
        const old=record.response.current||record.response,current=last.current||last;
        if(old.context&&current.context){
          mapping.set(old.context.id,current.context.id);
          const groups=[[old.participations||[],current.participations||[]],
            ...['situations','assertions'].map(key=>[old.context[key]||[],current.context[key]||[]])];
          for(const [left,right] of groups){
            if(left.length!==right.length)throw Error('Native/worker decomposition differs');
            left.forEach((value,i)=>mapping.set(value.id,right[i].id));
          }
          for(const oldQuestion of old.questions||[]){
            const target=replace(oldQuestion,mapping);
            const found=(current.questions||[]).filter(q=>['field','situation_id','participant_id'].every(key=>(q[key]||'')===(target[key]||'')));
            if(found.length===1)mapping.set(oldQuestion.id,found[0].id);
          }
        }
      }
      return replace(last,new Map([...mapping].map(([a,b])=>[b,a])));
    },replayCase.records);
    const nativeResult=replayCase.records.at(-1).response;
    const equal=JSON.stringify(canonical(workerResult))===JSON.stringify(canonical(nativeResult));
    check('narrative_'+replayCase.id+'_native_worker_parity',equal);
    report.narrative_cases.push({id:replayCase.id,parity:equal,proposal_status:workerResult.proposal_status,
      canonical_sha256:sha(JSON.stringify(canonical(workerResult)))});
  }
  report.passed=true;
}catch(error){
  report.passed=false;report.failure=String(error.stack||error).replaceAll(root,'<PROJECT>').replaceAll(root.replaceAll('\\','/'),'<PROJECT>')
    .replaceAll(process.env.USERPROFILE,'<USERPROFILE>').replaceAll(process.env.USERPROFILE.replaceAll('\\','/'),'<USERPROFILE>');
  process.exitCode=1;await page?.screenshot({path:path.join(artifacts,'failure.png'),fullPage:true}).catch(()=>{});
}finally{
  await browser.close();server.closeAllConnections();await new Promise(resolve=>server.close(resolve));
  await fs.writeFile(path.join(root,'evidence/situated-browser.json'),JSON.stringify(report,null,2)+'\n');
  console.log(JSON.stringify({passed:report.passed,checks:Object.keys(report.checks).length,failure:report.failure||null},null,2));
}
