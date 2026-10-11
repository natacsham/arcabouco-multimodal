// Synthetic checks of the public describe -> complete -> confirm -> orient flow.
// Uses the real worker and base. Mock speech tests cover UI behavior, not accuracy.
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
const base=process.env.SIMPLE_PUBLIC_URL||`http://127.0.0.1:${server.address().port}${prefix}`;
const origin=new URL(base).origin;
const sha=value=>crypto.createHash('sha256').update(value).digest('hex');
const report={type:'SYNTHETIC_SIMPLE_FLOW_BROWSER_NOT_PARTICIPANT_SESSION',checked_at:new Date().toISOString(),
  target:process.env.SIMPLE_PUBLIC_URL?'PUBLIC_SITE':'LOCAL_SUBPATH',checks:{},errors:[],external_requests:[],
  limits:['Speech recognition is mocked: no microphone capture or recognition accuracy is evaluated.',
    'NVDA, VoiceOver and comprehension with actual users were not tested; no full WCAG conformance claim.']};
report.build=JSON.parse(await fs.readFile(path.join(web,'amado/manifest.json'),'utf8'));
report.test_sha256=sha(await fs.readFile(fileURLToPath(import.meta.url)));
const check=(name,value)=>{report.checks[name]=Boolean(value);assert(value,name);};
const python=process.env.AMADO_PYTHON||'python';
const nativeResults=JSON.parse(execFileSync(python,['-B','-c',[
  'import sys,json,importlib.util',
  'from pathlib import Path',
  'sys.path[:0]=[str(Path.cwd()),str(Path.cwd()/"vendor")]',
  's=importlib.util.spec_from_file_location("simple_flow_bridge", "web/amado/bridge.py")',
  'm=importlib.util.module_from_spec(s);s.loader.exec_module(m);m.initialize()',
  'm.dispatch({"operation":"start","template":"CTX-DEMO-WEB-LEITOR-TELA"})',
  'm.dispatch({"operation":"update","payload":{"mapping_confirmed":True,"transfer_confirmed":True}})',
  'legacy=m.dispatch({"operation":"generate"})',
  'example=json.loads(Path("experimental/v2/examples/learning-contribution.json").read_text(encoding="utf-8"))',
  'composition=m.dispatch({"operation":"compose","payload":example})',
  'print(json.dumps({"legacy":legacy,"composition":composition},ensure_ascii=True))'
].join('\n')],{cwd:root,encoding:'utf8',maxBuffer:32*1024*1024}));
const native=nativeResults.legacy;
const projection=result=>({status:result.decision.status,
  components:result.decision.component_ids,knowledge:result.decision.knowledge_ids,
  configurations:result.decision.configuracao_modal,query_summary:result.query_summary});
report.native_decision={status:native.decision.status,components:native.decision.component_ids,
  projection_sha256:sha(JSON.stringify(projection(native)))};
const browser=await chromium.launch({headless:true,executablePath:process.env.AMADO_CHROMIUM||path.join(process.env.LOCALAPPDATA,'ms-playwright/chromium-1243/chrome-win64/chrome.exe')});
report.browser=browser.version();
const context=await browser.newContext({viewport:{width:1280,height:900},reducedMotion:'reduce'});
await context.addInitScript(()=>{
  window.__simpleProbe={operations:[],generated:null,state:null,busySnapshots:[]};
  const NativeWorker=window.Worker;
  window.Worker=class extends NativeWorker{
    constructor(...args){super(...args);this.operations=new Map();this.addEventListener('message',event=>{
      if(event.data.type!=='result')return;
      const operation=this.operations.get(event.data.id),data=event.data.data;
      if(operation==='generate'||operation==='compose'){window.__simpleProbe.generated=data;window.__simpleProbe.generationKind=operation;}
      if(data?.current?.context)window.__simpleProbe.state=data.current;
      else if(data?.context)window.__simpleProbe.state=data;
    });}
    postMessage(data,...rest){
      window.__simpleProbe.operations.push(data.operation);this.operations.set(data.id,data.operation);
      if(['analyze','update','generate','compose'].includes(data.operation)){
        const controls=[...document.querySelectorAll('#main input,#main textarea,#main select')].filter(element=>element.checkVisibility());
        window.__simpleProbe.busySnapshots.push({operation:data.operation,
          busy:document.querySelector('#main')?.getAttribute('aria-busy')==='true',
          controls:controls.map(element=>({id:element.id,name:element.name,blocked:element.matches(':disabled')||element.readOnly===true}))});
      }
      return super.postMessage(data,...rest);
    }
  };
  window.__speech={starts:0,stops:0,aborts:0,instances:[]};
  class MockSpeechRecognition extends EventTarget{
    constructor(){super();window.__speech.instances.push(this);}
    emit(type,properties={}){const event=new Event(type);Object.assign(event,properties);this.dispatchEvent(event);this['on'+type]?.(event);}
    start(){window.__speech.starts++;this.emit('start');}
    stop(){window.__speech.stops++;this.emit('end');}
    abort(){window.__speech.aborts++;this.emit('end');}
  }
  window.SpeechRecognition=MockSpeechRecognition;window.webkitSpeechRecognition=MockSpeechRecognition;
});
const requests=[];let failBundle=false;
await context.route('**/*',route=>{
  const request=route.request();requests.push({url:request.url(),method:request.method(),body:request.postData()||''});
  if(!request.url().startsWith(origin+'/')&&!request.url().startsWith('blob:')){report.external_requests.push(request.url());return route.abort();}
  if(failBundle&&request.url().endsWith('/assets/base.zip'))return route.abort('failed');
  return route.continue();
});
const ready=page=>page.waitForFunction(()=>document.querySelector('#health')?.dataset.state==='ready'&&document.querySelector('#main')?.getAttribute('aria-busy')==='false',{}, {timeout:180000});
async function contrastSamples(page){
  return page.evaluate(()=>{
    const rgba=text=>{const match=text.match(/rgba?\(([^)]+)\)/);if(!match)return null;const values=match[1].split(/[,\s/]+/).filter(Boolean).map(Number);return [...values.slice(0,3),values[3]??1];};
    const blend=(front,back)=>[0,1,2].map(index=>front[index]*front[3]+back[index]*(1-front[3]));
    const luminance=color=>color.map(value=>value/255).map(value=>value<=.04045?value/12.92:((value+.055)/1.055)**2.4).reduce((total,value,index)=>total+value*[.2126,.7152,.0722][index],0);
    const contrast=(left,right)=>(Math.max(luminance(left),luminance(right))+.05)/(Math.min(luminance(left),luminance(right))+.05);
    const background=element=>{const layers=[];for(let current=element;current;current=current.parentElement){const color=rgba(getComputedStyle(current).backgroundColor);if(color)layers.push(color);}let result=[255,255,255];for(const color of layers.reverse())result=blend(color,result);return result;};
    const samples=[...document.querySelectorAll('h1,#case-entry label,#case-help,#case-narrative,#health,#main button,[data-site-accessibility] button')].filter(element=>element.checkVisibility()).map(element=>{
      const style=getComputedStyle(element),bg=background(element),foreground=rgba(style.color);
      const large=parseFloat(style.fontSize)>=24||(parseFloat(style.fontSize)>=18.66&&parseInt(style.fontWeight)>=700);
      return {kind:'text',element:element.id||element.tagName,text:element.textContent.trim().slice(0,70),ratio:contrast(blend(foreground,bg),bg),minimum:large?3:4.5};
    });
    const field=document.querySelector('#case-narrative'),style=getComputedStyle(field),fieldBackground=background(field);
    samples.push({kind:'field_boundary',element:field.id,ratio:contrast(blend(rgba(style.borderTopColor),fieldBackground),fieldBackground),minimum:3});
    if(document.activeElement===field&&style.outlineStyle!=='none'&&parseFloat(style.outlineWidth)>0){
      samples.push({kind:'focus',element:field.id,ratio:contrast(blend(rgba(style.outlineColor),background(field.parentElement)),background(field.parentElement)),minimum:3});
    }else samples.push({kind:'focus',element:field.id,ratio:0,minimum:3});
    return samples;
  });
}
const artifacts=path.join(root,'tests/.artifacts/simple-flow');await fs.mkdir(artifacts,{recursive:true});
let page;
try{
  const served=await context.request.get(base+'amado/manifest.json');assert(served.ok());
  assert.deepEqual(await served.json(),report.build);check('served_manifest_matches_build',true);
  for(const view of ['index.html','guiado.html']){
    page=await context.newPage();page.on('pageerror',error=>report.errors.push(error.message));
    await page.goto(base+'amado/'+view);await ready(page);
    const key=name=>view+'_'+name;
    check(key('one_initial_narrative'),await page.locator('textarea:visible').count()===1);
    check(key('no_separate_writing_module'),await page.locator('#composition-panel').count()===0);
    check(key('examples_recollected'),await page.locator('#case-examples').getAttribute('open')===null);
    check(key('label_and_concrete_placeholder'),await page.locator('label[for="case-narrative"]').count()===1&&/pessoa|aluno|estudante/i.test(await page.locator('#case-narrative').getAttribute('placeholder')));
    check(key('microphone_visible'),await page.locator('#dictate-case').isVisible()&&/falar|ditar/i.test(await page.locator('#dictate-case').innerText())&&await page.locator('#dictate-case svg').count()>0);
    await page.locator('#case-narrative').focus();
    report.contrast??={};report.contrast[view]=await contrastSamples(page);
    check(key('sampled_text_field_focus_contrast'),report.contrast[view].every(sample=>sample.ratio>=sample.minimum));
    if(view==='index.html')await page.screenshot({path:path.join(artifacts,'initial-entry.png'),fullPage:true});
    await page.locator('[data-site-contrast]').click();await page.locator('#case-narrative').focus();
    report.contrast[view+'_high']=await contrastSamples(page);
    check(key('sampled_high_contrast'),report.contrast[view+'_high'].every(sample=>sample.ratio>=sample.minimum));
    await page.locator('[data-site-contrast]').click();await page.locator('#case-narrative').focus();await page.keyboard.press('Tab');
    check(key('keyboard_reaches_voice'),await page.locator('#dictate-case').evaluate(el=>el===document.activeElement));
    await page.locator('#case-examples > summary').focus();await page.keyboard.press('Enter');
    await page.locator('#case-template').selectOption('CTX-DEMO-WEB-LEITOR-TELA');
    await page.locator('#load-example').click();
    await page.locator('#case-review').waitFor({state:'visible',timeout:180000});
    check(key('example_has_review'),/leitor de tela/i.test(await page.locator('#review-summary').innerText()));
    check(key('example_entry_hidden'),await page.locator('#case-entry').isHidden());
    check(key('generation_waits_confirmation'),await page.locator('#generate-orientation').isDisabled()&&!await page.locator('#case-confirmed').isChecked());
    await page.locator('#case-confirmed').focus();await page.keyboard.press('Space');
    await page.locator('#generate-orientation').focus();await page.keyboard.press('Enter');
    await page.locator('#orientation-result').waitFor({state:'visible',timeout:180000});
    check(key('orientation_focus'),await page.locator('#orientation-title').evaluate(el=>el===document.activeElement));
    check(key('meaningful_main'),/texto|textua/i.test(await page.locator('#orientation-main').innerText()));
    check(key('foundations_recollected'),await page.locator('#orientation-foundations').getAttribute('open')===null);
    const result=await page.evaluate(()=>window.__simpleProbe.generated);
    assert.deepEqual(projection(result),projection(native),view+' unchanged real decision');
    check(key('exact_native_decision_projection'),true);
    check(key('real_traceability'),result.decision.configuracao_modal.some(row=>row.knowledge_ids.length>0&&row.criterion_ids.length>0)&&result.execution_evidence.checks.length>0);
    const operationsBeforeDetails=await page.evaluate(()=>JSON.stringify(window.__simpleProbe.operations));
    await page.locator('#orientation-foundations > summary').focus();await page.keyboard.press('Enter');
    check(key('foundations_keyboard_access'),await page.locator('#orientation-foundations').getAttribute('open')!==null);
    check(key('details_do_not_regenerate'),await page.evaluate(()=>JSON.stringify(window.__simpleProbe.operations))===operationsBeforeDetails);
    await page.keyboard.press('Enter');
    await page.screenshot({path:path.join(artifacts,view+'-orientation.png'),fullPage:true});
    await page.locator('#orientation-result [data-edit-case]').click();
    check(key('editing_discards_orientation'),await page.locator('#orientation-result').isHidden()&&!await page.locator('#case-confirmed').isChecked());
    await page.locator('#new-case').click();await ready(page);
    check(key('clear_case'),await page.locator('#case-narrative').inputValue()===''&&await page.locator('#orientation-result').isHidden());
    // A new narrative reaches composition through the same public field.
    await page.locator('#case-narrative').fill('O aluno quer escrever uma resposta e revisar o texto. Tem um teclado. Há campo de texto editável. Consegue usar o teclado. Não pode falar. Sem microfone. Sem tela. Não consegue ler o texto na tela. Leitura em voz disponível. Saída de áudio disponível. Tem conteúdo. Consegue conferir o texto pela leitura em voz. Consegue pausar e repetir a leitura. Consegue corrigir o texto. Controla quando concluir. Consegue confirmar o sentido do texto.');
    await page.locator('#analyze-case').click();
    await page.locator('#case-questions').waitFor({state:'visible',timeout:180000});
    const v2Questions=await page.locator('#questions-form [data-question]').first().getAttribute('data-question');
    check(key('composition_asks_missing_conditions'),v2Questions?.startsWith('facts:')||v2Questions?.startsWith('resources:'));
    let compositionAnswers=0;
    while(await page.locator('#case-questions').isVisible()){
      const row=page.locator('#questions-form [data-question]');
      const question=await row.getAttribute('data-question');
      assert(['facts:KeyboardEffortAcceptable','facts:KeyboardCompatible','facts:KeyboardFeedbackPerceptible','facts:AudioUsable'].includes(question),'Unexpected extraction gap: '+question);
      const control=row.locator('input[value="true"]');
      if(await control.count())await control.check();else await row.locator('select').selectOption('true');
      await page.locator('#answer-questions').click();compositionAnswers++;
      assert(compositionAnswers<=4,'Question must advance after an explicit answer');
      await page.waitForFunction(previous=>!document.querySelector('#case-review').hidden||document.querySelector('#questions-form [data-question]')?.dataset.question!==previous,question,{timeout:180000});
    }
    check(key('only_four_unstated_composition_conditions'),compositionAnswers===4);
    await page.locator('#case-review').waitFor({state:'visible',timeout:180000});
    await page.locator('#case-confirmed').check();await page.locator('#generate-orientation').click();
    await page.locator('#orientation-result').waitFor({state:'visible',timeout:180000});
    const composed=await page.evaluate(()=>window.__simpleProbe.generated);
    check(key('narrative_composes_without_loading_template'),await page.evaluate(()=>window.__simpleProbe.generationKind)==='compose'&&composed.proposal_status==='COMPLETE');
    const chosenSteps=composed.choices.map(choice=>choice.steps.map(step=>step.id));
    assert.deepEqual(chosenSteps,nativeResults.composition.choices.map(choice=>choice.steps.map(step=>step.id)));
    check(key('keyboard_then_audio_review'),chosenSteps.some(steps=>steps.length===2&&steps[0].endsWith('#CaptureKeyboard')&&steps[1].endsWith('#ReviewSpeech')));
    check(key('composition_foundation_present'),composed.choices.every(choice=>choice.steps.every(step=>step.groundings.length>0&&step.groundings.every(item=>item.knowledge.id&&item.criterion.id&&item.articulation.contributions.length>0))));
    await page.locator('#new-case').click();await ready(page);
    // Dictation is explicit and requires confirmation before a remote browser service.
    await page.locator('#dictate-case').focus();await page.keyboard.press('Enter');
    await page.locator('#speech-consent').waitFor({state:'visible'});
    check(key('voice_not_started_without_consent'),await page.evaluate(()=>window.__speech.starts)===0);
    await page.locator('#cancel-dictation').click();
    check(key('cancel_voice_returns_focus'),await page.locator('#dictate-case').evaluate(el=>el===document.activeElement));
    await page.locator('#dictate-case').click();await page.locator('#allow-browser-dictation').click();
    check(key('voice_started_after_consent'),await page.evaluate(()=>window.__speech.starts)===1);
    await page.evaluate(()=>{
      const first=[{transcript:'Uma pessoa usa um computador.',confidence:1}];first.isFinal=true;
      window.__speech.instances.at(-1).emit('result',{resultIndex:0,results:[first]});
      const second=[{transcript:' Precisa ler imagens com o leitor de tela.',confidence:1}];second.isFinal=true;
      window.__speech.instances.at(-1).emit('result',{resultIndex:1,results:[first,second]});
    });
    check(key('voice_transcript_no_duplication'),await page.locator('#case-narrative').evaluate(el=>(el.value.match(/Uma pessoa usa um computador/g)||[]).length===1&&el.value.includes('leitor de tela')));
    await page.locator('#dictate-case').click();
    check(key('voice_stop'),await page.evaluate(()=>window.__speech.stops)>0&&await page.locator('#dictate-case').getAttribute('aria-pressed')==='false');
    await page.locator('#dictate-case').click();
    if(await page.locator('#speech-consent').isVisible())await page.locator('#allow-browser-dictation').click();
    await page.locator('#case-narrative').fill('Texto revisado manualmente.');
    const manualText=await page.locator('#case-narrative').inputValue();
    await page.evaluate(()=>{const result=[{transcript:'Resultado de voz atrasado',confidence:1}];result.isFinal=true;window.__speech.instances.at(-1).emit('result',{resultIndex:0,results:[result]});});
    check(key('manual_edit_preserved_against_late_voice'),await page.evaluate(()=>window.__speech.aborts)>0&&(await page.locator('#case-narrative').inputValue())===manualText&&await page.locator('#dictate-case').getAttribute('aria-pressed')==='false');
    await page.locator('#dictate-case').click();
    await page.evaluate(()=>window.__speech.instances.at(-1).emit('error',{error:'not-allowed'}));
    check(key('permission_error_preserves_text'),/permiss|microfone|bloque/i.test(await page.locator('#dictation-status').innerText())&&(await page.locator('#case-narrative').inputValue())===manualText);
    // An incomplete real narrative asks for missing data, rather than filling an example.
    const marker='MARCADOR-PRIVACIDADE';
    await page.locator('#case-narrative').fill(marker+'. Uma pessoa cega usa leitor de tela, mas as imagens não têm descrição.');
    await page.locator('#analyze-case').click();
    await page.locator('#case-questions').waitFor({state:'visible',timeout:180000});
    const before=await page.evaluate(()=>window.__simpleProbe.state);
    check(key('only_missing_questions'),await page.locator('#questions-form [data-question]').count()>0&&!await page.locator('#orientation-result').isVisible());
    const objective=page.locator('#questions-form [name="objetivo"]');assert(await objective.count()===1,'Incomplete narrative must ask for an objective');
    await objective.fill('Compreender a informação das imagens e continuar a atividade.');
    await page.locator('#answer-questions').click();
    await page.waitForFunction(()=>window.__simpleProbe.state?.context?.objetivo==='Compreender a informação das imagens e continuar a atividade.',{}, {timeout:180000});
    const after=await page.evaluate(()=>window.__simpleProbe.state);
    assert.deepEqual(after.context.raw.caracteristicas_pessoa,before.context.raw.caracteristicas_pessoa);
    assert.deepEqual(after.context.raw.recursos_disponiveis,before.context.raw.recursos_disponiveis);
    check(key('answer_preserves_other_information'),true);
    if(await page.locator('#case-questions').isVisible())await page.locator('#skip-questions').click();
    await page.locator('#case-review').waitFor({state:'visible',timeout:180000});
    check(key('unknown_not_silently_completed'),await page.locator('#generate-orientation').isDisabled());
    await page.locator('#edit-case').click();await page.locator('#analyze-case').click();
    await page.locator('#case-questions').waitFor({state:'visible',timeout:180000});
    check(key('unchanged_narrative_preserves_answers'),await page.locator('#questions-form [name="objetivo"]').count()===0&&await page.evaluate(()=>window.__simpleProbe.state.context.objetivo)==='Compreender a informação das imagens e continuar a atividade.');
    await page.locator('#skip-questions').click();await page.locator('#case-review').waitFor({state:'visible',timeout:180000});
    const busySnapshots=await page.evaluate(()=>window.__simpleProbe.busySnapshots);
    check(key('inputs_blocked_while_processing'),busySnapshots.length>0&&busySnapshots.every(snapshot=>snapshot.busy&&snapshot.controls.every(control=>control.blocked)));
    report.busy_controls??={};report.busy_controls[view]=busySnapshots;
    await page.setViewportSize({width:320,height:900});
    check(key('reflow_320'),await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));
    await page.evaluate(()=>document.documentElement.style.fontSize='200%');
    check(key('reflow_320_text_200'),await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));
    await page.screenshot({path:path.join(artifacts,view+'-narrow.png'),fullPage:true});
    await page.evaluate(()=>document.documentElement.style.fontSize='');await page.setViewportSize({width:1280,height:900});
    await page.reload();await ready(page);
    check(key('reload_forgets_narrative'),await page.locator('#case-narrative').inputValue()===''&&await page.locator('#orientation-result').isHidden());
    check(key('no_case_storage'),await page.evaluate(async()=>localStorage.length===0&&sessionStorage.length===0&&document.cookie===''&&(await indexedDB.databases()).length===0&&(await caches.keys()).length===0));
    await page.locator('#case-narrative').fill('Olá');await page.locator('#analyze-case').click();
    check(key('short_description_error'),(await page.locator('#flow-error').innerText()).trim().length>0&&await page.locator('#case-entry').isVisible());
    await page.close();
  }
  failBundle=true;page=await context.newPage();page.on('pageerror',error=>report.errors.push(error.message));
  await page.goto(base+'amado/');await page.waitForFunction(()=>document.querySelector('#health')?.dataset.state==='error',{}, {timeout:180000});
  check('loading_failure_shows_error',(await page.locator('#flow-error').innerText()).trim().length>0&&await page.locator('#orientation-result').isHidden());
  failBundle=false;await page.locator('#retry-load').click();await ready(page);
  check('retry_loads_real_engine',await page.locator('#analyze-case').isEnabled());
  const unsupported=await browser.newContext({viewport:{width:1280,height:900}});
  await unsupported.addInitScript(()=>{window.SpeechRecognition=undefined;window.webkitSpeechRecognition=undefined;});
  await unsupported.route('**/*',route=>{
    const request=route.request();requests.push({url:request.url(),method:request.method(),body:request.postData()||''});
    if(!request.url().startsWith(origin+'/')&&!request.url().startsWith('blob:')){report.external_requests.push(request.url());return route.abort();}
    return route.continue();
  });
  const unsupportedPage=await unsupported.newPage();unsupportedPage.on('pageerror',error=>report.errors.push(error.message));
  await unsupportedPage.goto(base+'amado/');await ready(unsupportedPage);
  await unsupportedPage.locator('#dictate-case').click();
  check('unsupported_voice_has_text_alternative',/navegador|dispon[ií]vel|suporte/i.test(await unsupportedPage.locator('#dictation-status').innerText())&&await unsupportedPage.locator('#case-narrative').isEnabled());
  await unsupported.close();
  check('no_case_transmission',requests.every(row=>row.method==='GET'&&!((row.url+row.body).includes('MARCADOR-PRIVACIDADE')))&&report.external_requests.length===0);
  check('no_javascript_errors',report.errors.length===0);
  report.completed=true;report.passed=true;
}catch(error){report.passed=false;report.failure=String(error.stack||error).replaceAll(root,'<PROJECT>');process.exitCode=1;await page?.screenshot({path:path.join(artifacts,'failure.png'),fullPage:true}).catch(()=>{});}
finally{
  await browser.close();await new Promise(resolve=>server.close(resolve));
  await fs.writeFile(path.join(root,'evidence',process.env.SIMPLE_PUBLIC_URL?'simple-flow-public.json':'simple-flow-browser.json'),JSON.stringify(report,null,2)+'\n');
  console.log(JSON.stringify({passed:report.passed,checks:Object.keys(report.checks).length,failure:report.failure||null},null,2));
}
