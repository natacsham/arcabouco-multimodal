// End-to-end synthetic regression: narratives are typed through the public UI.
// The Worker observer only reads messages; it never supplies facts or invokes APIs.
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import path from 'node:path';
import http from 'node:http';
import os from 'node:os';
import crypto from 'node:crypto';
import {execFileSync} from 'node:child_process';
import {fileURLToPath,pathToFileURL} from 'node:url';

const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const web=path.join(root,'web'),prefix='/arcabouco-multimodal/';
const fixtureBytes=await fs.readFile(path.join(root,'tests/fixtures/articulation_transfer_cases.json'));
const cases=JSON.parse(fixtureBytes.toString('utf8'));
assert.equal(cases.length,3);
let playwright;
try { playwright=await import('playwright'); }
catch(error) {
  if(error.code!=='ERR_MODULE_NOT_FOUND')throw error;
  const modules=process.env.AMADO_NODE_MODULES||path.join(os.homedir(),'.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules');
  playwright=await import(pathToFileURL(path.join(modules,'playwright/index.mjs')).href);
}
const {chromium}=playwright;
const mime={'.html':'text/html; charset=utf-8','.js':'text/javascript','.mjs':'text/javascript','.css':'text/css','.json':'application/json','.wasm':'application/wasm','.zip':'application/zip'};
const server=http.createServer(async(req,res)=>{
  try {
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
const report={type:'SYNTHETIC_ARTICULATION_UI_NOT_HUMAN_EVALUATION',checks:{},cases:[],errors:[],limits:[
  'Three synthetic texts entered manually via visible controls; no claim of human relevance or learning outcomes.',
  'Speech output is mocked for start/stop controls; microphone accuracy and assistive-technology reading are not tested.'
]};
const sha=value=>crypto.createHash('sha256').update(value).digest('hex');
report.checked_at=new Date().toISOString();
report.build=JSON.parse(await fs.readFile(path.join(web,'amado/manifest.json'),'utf8'));
report.test_sha256=sha(await fs.readFile(fileURLToPath(import.meta.url)));
report.fixture_sha256=sha(fixtureBytes);
// Evidence may be published; the private fixture identifiers and narratives
// remain exclusively in tests. Ordinals and fixture hashes identify this run.
const publicCaseId=value=>cases.reduce((name,row,index)=>name.replaceAll(row.id,'synthetic-'+(index+1)),String(value));
const check=(name,value)=>{const label=publicCaseId(name);report.checks[label]=Boolean(value);assert(value,label);};
const launch={headless:true};
if(process.env.AMADO_CHROMIUM)launch.executablePath=process.env.AMADO_CHROMIUM;
else if(process.platform==='win32'&&process.env.LOCALAPPDATA){
  const localBrowser=path.join(process.env.LOCALAPPDATA,'ms-playwright/chromium-1243/chrome-win64/chrome.exe');
  if(await fs.access(localBrowser).then(()=>true,()=>false))launch.executablePath=localBrowser;
}
// In CI the Playwright installation supplies its own executable; no Windows
// path or browser revision is assumed when the local fallback is absent.
const browser=await chromium.launch(launch);
report.browser=browser.version();
const context=await browser.newContext({viewport:{width:1280,height:900},reducedMotion:'reduce'});
await context.addInitScript(()=>{
  window.__articulationReadOnly={records:[],progress:[],current:null,generated:null};
  window.__speechControls={speaks:0,cancels:0,texts:[]};
  window.SpeechSynthesisUtterance=class{constructor(text){this.text=text;}};
  Object.defineProperty(window,'speechSynthesis',{configurable:true,value:{
    getVoices:()=>[{localService:true,lang:'pt-BR',name:'Synthetic local voice'}],
    speak:utterance=>{window.__speechControls.speaks++;window.__speechControls.texts.push(utterance.text);},cancel:()=>{window.__speechControls.cancels++;},
    addEventListener:()=>{},removeEventListener:()=>{}
  }});
  const NativeWorker=window.Worker;
  window.Worker=class extends NativeWorker {
    constructor(...args){super(...args);this.requests=new Map();this.addEventListener('message',event=>{
      const data=event.data,probe=window.__articulationReadOnly;
      if(data.type==='progress'){probe.progress.push(structuredClone(data));return;}
      if(data.type!=='result')return;
      const record=this.requests.get(data.id);if(!record)return;
      record.response=structuredClone(data.data);
      if(data.data?.current?.context)probe.current=data.data.current;
      else if(data.data?.context)probe.current=data.data;
      if(record.request.operation==='generate')probe.generated=data.data;
    });}
    postMessage(data,...rest){
      if(['start','analyze','update','generate'].includes(data.operation)){
        const record={request:structuredClone(data)};
        window.__articulationReadOnly.records.push(record);this.requests.set(data.id,record);
      }
      return super.postMessage(data,...rest);
    }
  };
});
const requests=[];
await context.route('**/*',route=>{
  const req=route.request();requests.push({url:req.url(),method:req.method(),body:req.postData()||''});
  if(!req.url().startsWith(origin+'/')&&!req.url().startsWith('blob:'))return route.abort();
  return route.continue();
});
const ready=async page=>{
  await page.waitForFunction(()=>['ready','error'].includes(document.querySelector('#health')?.dataset.state)&&document.querySelector('#main')?.getAttribute('aria-busy')==='false',{}, {timeout:60000});
  assert.equal(await page.locator('#health').getAttribute('data-state'),'ready','Build and verify the browser package before this test');
};
const idle=page=>page.waitForFunction(()=>document.querySelector('#main')?.getAttribute('aria-busy')==='false',{}, {timeout:180000});
const proposals=result=>[...(result.choices||[]),...(result.pending_candidates||[]),...(result.partial_segments||[])];
// Re-execute the messages produced by the visible interface in local Python.
// This does not send records, answers or confirmations into the browser.
const nativeReplay=String.raw`
import sys,json,importlib.util
from pathlib import Path
sys.path[:0]=[str(Path.cwd()),str(Path.cwd()/"vendor")]
spec=importlib.util.spec_from_file_location("articulation_bridge","web/amado/bridge.py")
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);m.initialize()
records=json.loads(sys.stdin.buffer.read().decode("utf-8"));mapping={}
def replace(value,ids):
    if isinstance(value,str):
        for old,new in sorted(ids.items(),key=lambda row:-len(row[0])):value=value.replace(old,new)
        return value
    if isinstance(value,list):return [replace(v,ids) for v in value]
    if isinstance(value,dict):return {replace(k,ids):replace(v,ids) for k,v in value.items()}
    return value
def bind(old,new):
    old=old.get("current",old);new=new.get("current",new)
    if "context" not in old or "context" not in new:return
    mapping[old["context"]["id"]]=new["context"]["id"]
    groups=[("participations",old.get("participations",[]),new.get("participations",[]))]
    groups += [(key,old["context"].get(key,[]),new["context"].get(key,[])) for key in ("situations","assertions")]
    for key,left,right in groups:
        if len(left)!=len(right):raise AssertionError(f"Different {key} counts")
        for a,b in zip(left,right):mapping[a["id"]]=b["id"]
    questions=list(m.ENGINE.current["context"].get("question_manifest",{}).values())
    for question in old.get("questions",[]):
        target=replace(question,mapping)
        found=[q for q in questions if all(q.get(k,"")==target.get(k,"") for k in ("field","situation_id","participant_id"))]
        if len(found)==1:mapping[question["id"]]=found[0]["id"]
last={}
for record in records:
    request=replace(record["request"],mapping);request.pop("id",None)
    last=m.dispatch(request);bind(record["response"],last)
print(json.dumps(replace(last,{v:k for k,v in mapping.items()}),ensure_ascii=True))
`;
const canonical=value=>{
  if(typeof value==='string')return value.replace(/\b(?:check|proposal|occurrence|question)-[0-9a-f]{16,64}\b/g,match=>match.split('-')[0]+'-<volatile>');
  if(Array.isArray(value))return value.map(canonical);
  if(value&&typeof value==='object')return Object.fromEntries(Object.keys(value).sort().filter(key=>!['created_at','generated_at','checked_at','context_sha256'].includes(key)).map(key=>[key,canonical(value[key])]));
  return value;
};
async function generate(page,fixture){
  const recordStart=await page.evaluate(()=>window.__articulationReadOnly.records.length);
  await page.locator('#case-narrative').fill(fixture.narrative);
  await page.locator('#analyze-case').focus();await page.keyboard.press('Enter');
  await page.locator('#case-understanding').waitFor({state:'visible',timeout:180000});await idle(page);
  check(fixture.id+'_understanding_before_questions',await page.locator('#case-questions').isHidden());
  check(fixture.id+'_not_a_prepared_template',await page.locator('#case-template').inputValue()==='');
  await page.locator('#continue-understanding').click();
  const questions=[],questionLabels=[];
  while(await page.locator('#case-questions').isVisible()){
    check(fixture.id+'_max_three_questions',questions.length<3&&Number(await page.locator('#question-progress').getAttribute('data-total'))<=3);
    const group=page.locator('#questions-form [data-question]');
    const id=await group.getAttribute('data-question');
    questionLabels.push(await page.locator('#questions-title').innerText());
    check(fixture.id+'_no_repeated_question_'+questions.length,!questions.includes(id));questions.push(id);
    // No fabricated confirmations: contextual unknowns remain unknown.
    if(await page.locator('#answer-unknown').isVisible())await page.locator('#answer-unknown').click();
    else {await group.locator('input[value="unknown"]').check();await page.locator('#answer-questions').click();}
    await idle(page);
  }
  await page.locator('#case-review').waitFor({state:'visible'});
  check(fixture.id+'_confirmation_required',await page.locator('#generate-orientation').isDisabled());
  await page.locator('#case-confirmed').check();await page.locator('#generate-orientation').focus();await page.keyboard.press('Enter');
  await page.locator('#orientation-result').waitFor({state:'visible',timeout:180000});await idle(page);
  const probe=await page.evaluate(()=>window.__articulationReadOnly),result=probe.generated;
  report.current_case={id:publicCaseId(fixture.id),questions:questionLabels,status:result?.status,
    proposal_status:result?.proposal_status,proposals:result?proposals(result).length:0,
    gap_codes:(result?.gaps||[]).map(row=>row.code||row.reason||'UNSPECIFIED')};
  check(fixture.id+'_situated_contract',result?.result_contract==='AMADO_SITUATED_1');
  check(fixture.id+'_grounded_proposals',proposals(result).length>0);
  check(fixture.id+'_actions_visible',await page.locator('.situated-action').count()>0);
  check(fixture.id+'_orientations_numbered_in_display_order',await page.locator('#orientation-main .situated-choice').evaluateAll(rows=>rows.length>0&&rows.every((row,index)=>{
    const number=row.querySelector(':scope > h3 .orientation-number');
    return number?.textContent.trim()==='Orientação '+(index+1)&&row.dataset.choiceIndex===String(index)&&
      Boolean(row.querySelector(':scope > h3 .orientation-title')?.textContent.trim());
  })));
  const practicalText=await page.locator('#orientation-main').innerText();
  check(fixture.id+'_no_object_strings',!practicalText.includes('[object Object]'));
  check(fixture.id+'_whole_practical_orientation_open',await page.locator('#orientation-main details').count()===0);
  check(fixture.id+'_single_foundation_disclosure',await page.locator('#orientation-foundations').count()===1&&
    await page.locator('#orientation-foundations').getAttribute('open')===null&&
    (await page.locator('#orientation-foundations > summary').innerText()).trim()==='Como chegamos a esta orientação');
  check(fixture.id+'_no_duplicate_complete_orientation',await page.locator('details#orientation-details,details#orientation-sources').count()===0);
  check(fixture.id+'_responsible_and_beneficiary_visible',await page.locator('#orientation-main .step-responsible').count()>0&&await page.locator('#orientation-main .step-beneficiary').count()>0);
  check(fixture.id+'_steps_with_origin_and_phase',await page.locator('#orientation-main .action-instructions li').count()>0&&
    await page.locator('#orientation-main .action-instructions li').evaluateAll(rows=>rows.every(row=>Boolean(row.dataset.originPath)&&Boolean(row.dataset.phase))));
  check(fixture.id+'_step_numbers_are_inline_not_legacy_badges',await page.locator('#orientation-main .step-number').evaluateAll(rows=>rows.every(row=>{
    const style=getComputedStyle(row);return ['inline','block'].includes(style.display)&&style.backgroundColor==='rgba(0, 0, 0, 0)'&&style.borderRadius==='0px';
  })));
  check(fixture.id+'_action_conditions_and_monitoring_have_distinct_surfaces',await page.locator('#orientation-main').evaluate(main=>{
    const selectors=['.action-instructions','.step-conditions','.step-monitoring'];
    const colors=selectors.map(selector=>[...main.querySelectorAll(selector)].map(row=>getComputedStyle(row).backgroundColor));
    return colors[0].length>0&&colors.every(group=>group.every(color=>color!=='rgba(0, 0, 0, 0)'))&&
      colors.every((group,index)=>group.every(color=>colors.every((other,otherIndex)=>otherIndex===index||!other.includes(color))));
  }));
  check(fixture.id+'_no_internal_review_comments',!/ainda precisa ser conferida|Estes recursos não são apresentados como prontos|\bNOT_EXECUTED\b|\bGROUNDED_ANALYTICAL_APPLICATION\b/.test(practicalText));
  check(fixture.id+'_technical_foundations_not_in_practical',await page.locator('#orientation-main .step-grounding,#orientation-main .foundation-source').count()===0);
  check(fixture.id+'_no_hidden_confirmation',probe.records.slice(recordStart).filter(r=>r.request.operation==='update').every(r=>{
    const payload=r.request.payload||{};
    return !(payload.situated_facts||[]).some(f=>f.value===true);
  }));
  const actualStages=new Set(probe.progress.filter(p=>p.operation==='generate').map(p=>p.stage));
  const renderedStages=await page.locator('#generation-stages [data-stage]').evaluateAll(rows=>rows.map(r=>r.dataset.stage));
  check(fixture.id+'_progress_from_execution',renderedStages.length>0&&renderedStages.every(stage=>stage==='presentation'||actualStages.has(stage)));
  check(fixture.id+'_no_online_document_claim',!/lendo (a |as |o |os )?(ABNT|normas|artigos)/i.test(await page.locator('#generation-stages').innerText()));
  const native=JSON.parse(execFileSync(process.env.AMADO_PYTHON||'python',['-B','-W','ignore','-c',nativeReplay],{
    cwd:root,encoding:'utf8',input:JSON.stringify(probe.records),maxBuffer:64*1024*1024}));
  const parity=JSON.stringify(canonical(result))===JSON.stringify(canonical(native));
  check(fixture.id+'_native_browser_parity',parity);
  report.cases.push({id:publicCaseId(fixture.id),questions:questions.length,status:result.status,proposal_status:result.proposal_status,
    parity,canonical_sha256:sha(JSON.stringify(canonical(result))),
    proposals:proposals(result).length,relations:proposals(result).flatMap(p=>p.relations||[]).length,
    analytical_applications:proposals(result).flatMap(p=>p.steps||[]).flatMap(s=>s.groundings||[]).filter(g=>g.application_kind==='GROUNDED_ANALYTICAL_APPLICATION').length});
  delete report.current_case;
  return result;
}
let page;
try{
  for(const fixture of cases){
    page=await context.newPage();page.on('pageerror',error=>report.errors.push(error.message));
    await page.goto(base+'amado/index.html');await ready(page);
    check(fixture.id+'_single_narrative_input',await page.locator('textarea:visible').count()===1);
    check(fixture.id+'_not_in_example_selector',!(await page.locator('#case-template').innerText()).includes(fixture.narrative));
    const result=await generate(page,fixture);
    if(process.env.AMADO_BROWSER_SCREENSHOTS){
      await fs.mkdir(process.env.AMADO_BROWSER_SCREENSHOTS,{recursive:true});
      await page.screenshot({path:path.join(process.env.AMADO_BROWSER_SCREENSHOTS,fixture.id+'.png'),fullPage:true});
      await page.locator('#orientation-title').scrollIntoViewIfNeeded();
      await page.screenshot({path:path.join(process.env.AMADO_BROWSER_SCREENSHOTS,fixture.id+'-practical-viewport.png')});
    }
    const grounding=page.locator('#orientation-foundations > summary');
    await grounding.focus();await page.keyboard.press('Enter');
    check(fixture.id+'_keyboard_grounding',await grounding.evaluate(el=>el.parentElement.open));
    // The native details toggle schedules lazy foundation rendering. Observe
    // its completed DOM instead of racing that event on fast CI browsers.
    await page.locator('#orientation-foundations .foundation-source a[href^="http"]').first().waitFor({state:'visible',timeout:10000});
    check(fixture.id+'_foundation_matches_numbered_orientations',await page.evaluate(()=>{
      const headings=selector=>[...document.querySelectorAll(selector)].map(row=>[
        row.querySelector('.orientation-number')?.textContent.trim(),row.querySelector('.orientation-title')?.textContent.trim()]);
      const practical=headings('#orientation-main .situated-choice > h3'),technical=headings('#orientation-foundations .foundation-choice > h3');
      return practical.length>0&&JSON.stringify(practical)===JSON.stringify(technical);
    }));
    check(fixture.id+'_localized_source_links',await page.locator('.foundation-choice a[href^="#"]').count()>0&&await page.locator('.foundation-source a[href^="http"]').count()>0);
    check(fixture.id+'_source_anchors_resolve',await page.locator('#orientation-foundations a[href^="#"]').evaluateAll(links=>links.every(link=>Boolean(document.getElementById(link.hash.slice(1))))));
    check(fixture.id+'_sources_only_in_foundation',await page.locator('.foundation-source').count()===await page.locator('#orientation-foundations .foundation-source').count());
    if(process.env.AMADO_BROWSER_SCREENSHOTS){
      await page.locator('#orientation-foundations').scrollIntoViewIfNeeded();
      await page.screenshot({path:path.join(process.env.AMADO_BROWSER_SCREENSHOTS,fixture.id+'-detail.png'),fullPage:false});
    }
    if(fixture.id==='dictation_review_control'){
      check('dictation_exposes_a_real_relation',proposals(result).some(p=>(p.relations||[]).length>0));
      check('dictation_sequential_routes_keep_continuous_step_numbers',await page.locator('#orientation-main .situated-choice').evaluateAll(articles=>{
        const result=window.__articulationReadOnly.generated;
        const sequential=articles.filter(article=>{
          const path=article.querySelector('.action-instructions li')?.dataset.originPath||'';
          const match=/^(choices|pending_candidates|partial_segments)\[(\d+)\]/.exec(path);
          const choice=match&&result[match[1]]?.[Number(match[2])];
          return choice?.composition_type==='CONNECTED_PATH'&&choice.steps.length>1&&choice.relations?.length>0&&
            choice.relations.every(relation=>['DEPENDENT_SEQUENCE','SEQUENTIAL','SEQUENTIAL_REVIEW'].includes(relation.kind));
        });
        return sequential.length>0&&sequential.every(article=>{
          const numbers=[...article.querySelectorAll('.step-number')].map(row=>Number(/Passo (\d+)/.exec(row.textContent)?.[1]));
          return numbers.length>1&&numbers.every((number,index)=>number===index+1)&&
            [...article.querySelectorAll('.action-instructions')].every(list=>Number(list.start)===Number(/Passo (\d+)/.exec(list.querySelector('.step-number')?.textContent)?.[1]));
        });
      }));
      check('dictation_exposes_instruction_condition_and_check_regions',await page.locator('#orientation-main').evaluate(main=>
        ['.action-instructions','.step-conditions','.step-monitoring'].every(selector=>main.querySelector(selector))));
      await page.locator('#read-orientation').focus();await page.keyboard.press('Enter');
      check('one_control_starts_speech',await page.locator('#read-orientation').innerText()==='Parar');
      const speech=await page.evaluate(()=>window.__speechControls.texts.at(-1));
      check('speech_uses_only_practical_orientation_with_foundation_open',speech.trim()===(await page.locator('#orientation-main').innerText()).trim());
      await page.keyboard.press('Enter');check('one_control_stops_speech',await page.locator('#read-orientation').innerText()==='Ouvir');
      const pending=[...(result.facts_to_confirm||[]),...(result.resources_to_confirm||[])].find(row=>row.fact_id);
      if(pending){
        report.review_counterfactual={condition:pending.label,value:false,source:'SYNTHETIC_REVIEW_CHANGE_NOT_IN_ORIGINAL_NARRATIVE'};
        const review=page.locator('#orientation-main .step-conditions [data-edit-case]').first();
        check('pending_action_links_directly_to_review',await review.count()===1);
        await review.click();
        const key=['fact',pending.participant_id,pending.situation_id,pending.fact_id].join(':');
        const control=page.locator('[data-revision="'+key+'"]');
        check('unanswered_condition_is_editable',await control.count()===1);
        check('unanswered_condition_starts_unknown',await control.inputValue()==='unknown');
        await control.selectOption('false');await page.locator('#save-case').click();await idle(page);
        check('revision_revokes_previous_result',await page.locator('#orientation-result').isHidden()&&await page.locator('#generate-orientation').isDisabled());
        await page.locator('#edit-case').click();
        check('revision_preserves_explicit_negative',await page.locator('[data-revision="'+key+'"]').inputValue()==='false');
        await page.locator('#cancel-editor').click();
      }
      const reviewButton=page.locator('#case-review:visible #edit-case, #orientation-result:visible [data-edit-case]').first();
      await reviewButton.click();await page.locator('[data-edit-narrative]:visible').click();
      const noisyNarrative=fixture.narrative.replace('Estou numa sala silenciosa, sem outras pessoas ouvindo, e posso controlar quando começar, parar e confirmar o registro.',
        'Há ruído e o reconhecimento de fala não funciona neste ambiente. Posso controlar quando começar, parar e confirmar o registro.');
      assert.notEqual(noisyNarrative,fixture.narrative);
      const noisy=await generate(page,{...fixture,id:fixture.id+'_noise',narrative:noisyNarrative});
      check('noise_removes_speech_capture',proposals(noisy).every(p=>(p.steps||[]).every(step=>!String(step.id).includes('CaptureSpeech'))));
      check('noise_does_not_invent_long_typing_route',proposals(noisy).every(p=>(p.steps||[]).every(step=>!String(step.id).includes('CaptureKeyboard'))));
    }
    for(const width of [375,320]){
      await page.setViewportSize({width,height:900});
      check(fixture.id+'_reflow_'+width,await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));
      await page.evaluate(()=>document.documentElement.style.fontSize='125%');
      check(fixture.id+'_step_numbers_not_badges_text125_'+width,await page.locator('#orientation-main .step-number').evaluateAll(rows=>rows.every(row=>['inline','block'].includes(getComputedStyle(row).display)&&getComputedStyle(row).backgroundColor==='rgba(0, 0, 0, 0)')));
      await page.evaluate(()=>document.documentElement.style.fontSize='200%');
      check(fixture.id+'_text200_'+width,await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));
      check(fixture.id+'_instruction_text_reflows_text200_'+width,await page.locator('#orientation-main').evaluate(main=>{
        const walker=document.createTreeWalker(main,NodeFilter.SHOW_TEXT),range=document.createRange();let node;
        while((node=walker.nextNode())){
          if(!node.textContent.trim())continue;
          range.selectNodeContents(node);
          if([...range.getClientRects()].some(rect=>rect.width>0&&(rect.left< -1||rect.right>innerWidth+1)))return false;
        }
        return true;
      }));
      await page.evaluate(()=>document.documentElement.style.fontSize='');
      if(width===320){
        check(fixture.id+'_regions_have_noncolor_boundaries_320',await page.locator('#orientation-main .situated-choice,#orientation-main .action-instructions,#orientation-main .step-conditions,#orientation-main .step-monitoring').evaluateAll(rows=>rows.length>0&&rows.every(row=>{
          const style=getComputedStyle(row);
          return ['Top','Right','Bottom','Left'].some(side=>parseFloat(style['border'+side+'Width'])>=1&&!['none','hidden'].includes(style['border'+side+'Style']));
        })));
        await page.emulateMedia({forcedColors:'active'});
        check(fixture.id+'_regions_remain_distinct_in_forced_colors_320',await page.locator('#orientation-main .situated-choice,#orientation-main .action-instructions,#orientation-main .step-conditions,#orientation-main .step-monitoring').evaluateAll(rows=>rows.length>0&&rows.every(row=>{
          const style=getComputedStyle(row);
          return ['Top','Right','Bottom','Left'].some(side=>parseFloat(style['border'+side+'Width'])>=1&&!['none','hidden'].includes(style['border'+side+'Style']));
        })));
        await page.emulateMedia({forcedColors:'none'});
      }
      if(width===320&&process.env.AMADO_BROWSER_SCREENSHOTS){
        await page.locator('#orientation-title').scrollIntoViewIfNeeded();
        await page.screenshot({path:path.join(process.env.AMADO_BROWSER_SCREENSHOTS,fixture.id+'-practical-320.png')});
      }
    }
    check(fixture.id+'_no_case_storage',await page.evaluate(async()=>localStorage.length===0&&sessionStorage.length===0&&document.cookie===''&&(await indexedDB.databases()).length===0&&(await caches.keys()).length===0));
    await page.close();page=null;
  }
  check('no_case_transmission',requests.every(r=>r.method==='GET'&&r.url.startsWith(origin+'/')&&!r.body&&!new URL(r.url).search));
  check('no_javascript_errors',report.errors.length===0);
  report.passed=true;
}catch(error){
  report.passed=false;
  report.failure=String(error.stack||error).replaceAll(root,'<PROJECT>').replaceAll(root.replaceAll('\\','/'),'<PROJECT>')
    .replaceAll(os.homedir(),'<USERPROFILE>').replaceAll(os.homedir().replaceAll('\\','/'),'<USERPROFILE>');
  process.exitCode=1;
}
finally{
  await browser.close();server.closeAllConnections();await new Promise(resolve=>server.close(resolve));
  // Optional evidence path is chosen by the caller; ordinary execution creates
  // no tracked report or copy of the narratives.
  if(process.env.AMADO_BROWSER_EVIDENCE)await fs.writeFile(process.env.AMADO_BROWSER_EVIDENCE,JSON.stringify(report,null,2)+'\n');
  console.log(JSON.stringify(report,null,2));
}
