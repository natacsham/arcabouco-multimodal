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
          generationVisible:document.querySelector('#generation-progress')?.checkVisibility()===true,
          generationText:document.querySelector('#generation-progress')?.textContent.trim()||'',
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
async function questionProgress(page){
  const text=await page.locator('#question-progress').innerText();
  const match=text.match(/(\d+)\s+de\s+(\d+)/i);
  assert(match,'Question progress exposes current and currently estimated total: '+text);
  const current=Number(match[1]),total=Number(match[2]);
  assert(current>0&&total>=current,'Consistent current/total question count');
  return {current,total,text};
}
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
    check(key('direct_challenge_heading'),(await page.locator('h1').innerText()).trim()==='Qual é o seu desafio de hoje?'&&
      !/problema/i.test(await page.locator('#case-entry').innerText())&&await page.locator('#dictate-case').innerText()==='Falar');
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
    // Regression of the reported loop: the old flow re-asked the barrier when
    // the organizing task received ONE valid option, not every offered need.
    await page.locator('#case-narrative').fill('Sou docente e quero ensinar um assunto complexo de matemática à minha turma, com dois estudantes surdos e um estudante cego.');
    await page.locator('#analyze-case').click();await page.locator('#case-questions').waitFor({state:'visible',timeout:180000});
    const sparseInitial=await page.evaluate(()=>window.__simpleProbe.state);
    const sparseAnswers=[], sparseProgress=[];
    while(await page.locator('#case-questions').isVisible()){
      const row=page.locator('#questions-form [data-question]'),question=await row.getAttribute('data-question');
      const field=question.split(':')[0],person=await page.locator('#question-person').innerText();
      const progress=await questionProgress(page);sparseProgress.push(progress);
      assert(!sparseAnswers.some(answer=>answer.id===question),'A completed partial/unknown answer must not be re-asked: '+question);
      assert(sparseAnswers.length<22,'Partial/unknown answers must terminate without skip-all');
      if(field==='tarefas')await row.locator('input[value="TAR-ORGANIZAR-CONTEUDO-DIGITAL"]').check();
      else if(field==='barreira_ou_necessidade'){
        const control=row.locator('input[value="BAR-CONTEUDO-SEM-ESTRUTURA-PERSISTENTE"]');
        const label=control.locator('xpath=ancestor::label[1]');
        check(key('whole_option_has_pointer'),await label.evaluate(element=>getComputedStyle(element).cursor)==='pointer');
        const box=await label.boundingBox();assert(box);
        await label.click({position:{x:box.width-12,y:box.height/2}});
        check(key('whole_option_click_selects_single_barrier'),await control.isChecked()&&await row.locator('input:checked').count()===1);
      }else if(field==='apoios_informados')await row.locator('textarea').fill('não sei');
      else if(field==='objetivo')await row.locator('textarea').fill('Ainda não sei');
      else await row.locator('input[value="unknown"]').check();
      if(field==='modalidades_disponiveis'&&person){
        check(key('group_access_has_named_participant'),/estudante/i.test(person)&&/surd|ceg/i.test(person));
        check(key('group_question_programmatically_names_context'),await row.evaluate(element=>{
          const references=(element.getAttribute('aria-describedby')||'').split(/\s+/).filter(Boolean);
          return ['question-person','question-context','question-help'].every(id=>references.includes(id)&&document.getElementById(id))&&
            element.querySelector('legend')?.textContent.includes(document.getElementById('question-person').textContent);
        }));
        check(key('game_not_offered_as_perceptual_access'),await row.locator('input[value="MOD-JOGO-INTERATIVO"]').count()===0);
        const note=row.locator('textarea');
        if(await note.count()){
          await note.evaluate(element=>{for(let ancestor=element.parentElement;ancestor;ancestor=ancestor.parentElement)if(ancestor.tagName==='DETAILS')ancestor.open=true;});
          await note.fill('não sei');
        }
        if(!sparseAnswers.some(answer=>answer.id.startsWith('modalidades_disponiveis:')))
          await page.screenshot({path:path.join(artifacts,view+'-question-progress.png'),fullPage:true});
      }
      if(field!=='tarefas')assert((await page.locator('#question-context').innerText()).includes('Organizar'),'Follow-up identifies the selected activity');
      sparseAnswers.push({id:question,participant:person,answer:field==='tarefas'?'TAR-ORGANIZAR-CONTEUDO-DIGITAL':field==='barreira_ou_necessidade'?'BAR-CONTEUDO-SEM-ESTRUTURA-PERSISTENTE':'unknown'});
      await page.locator('#answer-questions').click();
      await page.waitForFunction(previous=>!document.querySelector('#case-review').hidden||document.querySelector('#questions-form [data-question]')?.dataset.question!==previous,question,{timeout:20000});
    }
    const sparseState=await page.evaluate(()=>window.__simpleProbe.state);
    check(key('partial_and_unknown_answers_advance_once'),sparseAnswers.some(answer=>answer.id==='barreira_ou_necessidade')&&new Set(sparseAnswers.map(answer=>answer.id)).size===sparseAnswers.length);
    check(key('question_progress_increases'),sparseProgress.every((progress,index)=>index===0||progress.current>sparseProgress[index-1].current));
    check(key('unknown_free_text_is_not_support_fact'),(sparseState.participations||[]).every(person=>!/^\s*(?:ainda )?n[aã]o sei[.!]?\s*$/i.test(person.apoios_informados||'')));
    check(key('single_barrier_does_not_assert_all_needs'),
      JSON.stringify([...sparseState.context.raw.barreiras].sort())===JSON.stringify([...new Set([...sparseInitial.context.raw.barreiras,'BAR-CONTEUDO-SEM-ESTRUTURA-PERSISTENTE'])].sort())&&
      JSON.stringify(sparseState.context.raw.necessidades)===JSON.stringify(sparseInitial.context.raw.necessidades));
    report.partial_answer_regression??={};report.partial_answer_regression[view]={answers:sparseAnswers,progress:sparseProgress,raw:sparseState.context.raw,
      note:'This regression uses one offered barrier and unknown answers. The historical published flow repeated that barrier question after the first selection.'};
    await page.locator('#new-case').click();await ready(page);
    // A collective teaching challenge must not collapse different participants
    // into the single-person writing pilot or infer an assistive technology.
    await page.locator('#case-narrative').fill('Sou docente e quero ensinar um assunto complexo de matemática à minha turma, com dois estudantes surdos e um estudante cego.');
    await page.locator('#analyze-case').click();
    await page.locator('#case-questions').waitFor({state:'visible',timeout:180000});
    const teaching=await page.evaluate(()=>window.__simpleProbe.state);
    const groups=teaching.context.participantes;
    check(key('teaching_participants_distinct'),groups.some(group=>/surd/i.test(group.label)&&group.quantidade===2)&&
      groups.some(group=>/ceg/i.test(group.label)&&group.quantidade===1));
    check(key('teaching_task_general_not_theme_key'),teaching.context.raw.tarefas.length>0&&
      teaching.context.raw.tarefas.every(id=>!/matemat/i.test(id)));
    check(key('no_inferred_classroom_or_assistive_technology'),teaching.context.raw.ambientes.length===0&&
      !JSON.stringify(groups.map(group=>[group.modalidades,group.recursos_operados])).match(/Libras|leitor de tela|Braille/i));
    check(key('specific_question_focus'),await page.locator('#questions-title').evaluate(el=>el===document.activeElement)&&
      (await page.locator('#questions-title').innerText()).includes('?')&&await page.locator('#questions-form [data-question]').count()===1);
    const groupAnswers=[];
    report.teaching_case??={};report.teaching_case[view]={answers:groupAnswers};
    while(await page.locator('#case-questions').isVisible()){
      const row=page.locator('#questions-form [data-question]'),question=await row.getAttribute('data-question');
      const questionPerson=await page.locator('#question-person').innerText();
      const field=question.split(':')[0];
      const values=field==='tarefas' ? ['TAR-ACESSAR-COMPREENDER-CONTEUDO-DIGITAL'] :
        field==='participantes' ? ['PAPEL-RESPONSAVEL-ADAPTACAO'] :
        field==='modalidades_disponiveis' ? /surd/i.test(questionPerson) ? ['MOD-TEXTO','MOD-IMAGEM'] : /ceg/i.test(questionPerson) ? ['MOD-AUDIO'] : ['MOD-TEXTO'] :
        field==='caracteristicas_pessoa' ? /ceg/i.test(questionPerson) ? ['CAR-INTERACAO-NAO-VISUAL'] : ['unknown'] :
        field==='recursos_digitais' ? ['RED-PAGINA-WEB'] : field==='ambientes' ? ['AMB-SALA-DE-AULA'] :
        field==='recursos_disponiveis' ? questionPerson ? /ceg/i.test(questionPerson) ? ['REC-LEITOR-DE-TELA'] :
          /adapta/i.test(questionPerson) ? ['REC-EDITOR-MULTIMIDIA'] : ['unknown'] : [] :
        field==='apoios_informados' ? [/surd/i.test(questionPerson) ? 'O grupo consegue compreender o texto e as imagens usados na atividade. Outros apoios ainda precisam ser conferidos.' :
          'O estudante usa leitura em voz do conteúdo pelo leitor de tela e pode pedir a retomada da informação.'] : [];
      // An engine-derived resource question may offer only the required subset;
      // the ordinary equipment question still shows the public catalogue.
      if(field==='recursos_disponiveis'&&!questionPerson){
        for(const candidate of ['REC-COMPUTADOR','REC-LEITOR-DE-TELA','REC-EDITOR-MULTIMIDIA'])
          if(await row.locator('input[value="'+candidate+'"]').count())values.push(candidate);
      }
      if(field==='barreira_ou_necessidade'){
        for(const candidate of ['NEC-ACESSO-EQUIVALENTE','NEC-ALTERNATIVA-FUNCIONAL-EQUIVALENTE'])
          if(await row.locator('input[value="'+candidate+'"]').count())values.push(candidate);
      }
      assert(values.length,'Unexpected teaching intake question: '+question);
      if(field==='apoios_informados')await row.locator('textarea').fill(values[0]);
      else for(const value of values){
        const control=row.locator('input[value="'+value+'"]');
        assert.equal(await control.count(),1,'Existing concept must be selectable: '+value);
        if(!await control.isVisible())await control.evaluate(element=>{
          for(let ancestor=element.parentElement;ancestor;ancestor=ancestor.parentElement)if(ancestor.tagName==='DETAILS')ancestor.open=true;
        });
        await control.check();
      }
      if(field==='modalidades_disponiveis'&&questionPerson&&await row.locator('textarea').count()){
        const note=row.locator('textarea');await note.evaluate(element=>{for(let ancestor=element.parentElement;ancestor;ancestor=ancestor.parentElement)if(ancestor.tagName==='DETAILS')ancestor.open=true;});
        await note.fill(/surd/i.test(questionPerson)?'O grupo consegue compreender o texto e as imagens usados na atividade. Outros apoios ainda precisam ser conferidos.':
          'O estudante usa leitura em voz do conteúdo pelo leitor de tela e pode pedir a retomada da informação.');
      }
      await page.locator('#answer-questions').click();
      groupAnswers.push({question,participant_label:questionPerson,values});
      assert.equal(new Set(groupAnswers.map(item=>item.question)).size,groupAnswers.length,
        'Teaching questions must advance, not repeat a group answer');
      assert(groupAnswers.length<=20,'Teaching intake must terminate');
      await page.waitForFunction(previous=>!document.querySelector('#case-review').hidden||
        document.querySelector('#questions-form [data-question]')?.dataset.question!==previous,question,{timeout:180000});
    }
    await page.locator('#case-review').waitFor({state:'visible',timeout:180000});
    const teachingAnswered=await page.evaluate(()=>window.__simpleProbe.state);
    const scopedGroups=teachingAnswered.participations.filter(group=>group.papel_id==='PAPEL-ESTUDANTE');
    const deaf=scopedGroups.find(group=>/surd/i.test(group.label)),blind=scopedGroups.find(group=>/ceg/i.test(group.label));
    check(key('answers_preserve_group_counts_and_separation'),deaf.quantidade===2&&blind.quantidade===1&&
      JSON.stringify([...deaf.modalidade_ids].sort())===JSON.stringify(['MOD-IMAGEM','MOD-TEXTO'])&&JSON.stringify(blind.modalidade_ids)===JSON.stringify(['MOD-AUDIO'])&&
      teachingAnswered.context.raw.modalidades_disponiveis.length===0&&
      deaf.tarefa_ids.length>0&&blind.tarefa_ids.length>0);
    check(key('groups_answered_individually'),groupAnswers.filter(item=>item.question.startsWith('modalidades_disponiveis:')).length===2&&
      groupAnswers.some(item=>/surd/i.test(item.participant_label))&&groupAnswers.some(item=>/ceg/i.test(item.participant_label)));
    const teachingSummary=await page.locator('#review-summary').innerText();
    check(key('short_review_preserves_groups'),/surd/i.test(teachingSummary)&&/ceg/i.test(teachingSummary)&&
      teachingSummary.length<650&&!teachingSummary.includes('Para a orientação, consideraremos'));
    check(key('teaching_waits_for_confirmation'),await page.locator('#generate-orientation').isDisabled());
    await page.locator('#case-confirmed').check();await page.locator('#generate-orientation').click();
    await page.locator('#orientation-result').waitFor({state:'visible',timeout:180000});
    const teachingResult=await page.evaluate(()=>window.__simpleProbe.generated);
    check(key('teaching_uses_actual_engine_after_confirmation'),await page.evaluate(()=>window.__simpleProbe.generationKind)==='generate'&&
      Boolean(teachingResult.decision?.status)&&teachingResult.execution_evidence.checks.length>0);
    report.teaching_case??={};report.teaching_case[view]={answers:groupAnswers,context:teachingAnswered.context,
      participant_conditions:scopedGroups,decision_status:teachingResult.decision.status,
      component_ids:teachingResult.decision.component_ids,knowledge_ids:teachingResult.decision.knowledge_ids,
      articulation_ids:teachingResult.decision.articulation_ids,
      limitations:teachingResult.decision.informacoes_ausentes,
      note:'This checks the real public intake and explicit synthetic follow-up answers, not a pre-registered mathematics response. The partial coverage and unresolved personal conditions remain visible.'};
    check(key('teaching_reuses_existing_pattern_with_partial_limit'),teachingResult.decision.status==='GERADA_PARCIAL'&&
      JSON.stringify(teachingResult.decision.component_ids)===JSON.stringify(['PAD-CONTEUDO-WEB-EQUIVALENTE'])&&
      JSON.stringify([...teachingResult.decision.knowledge_ids].sort())===JSON.stringify(['K10','K42'])&&
      JSON.stringify(teachingResult.decision.articulation_ids)===JSON.stringify(['ART-REF-03']));
    check(key('partial_orientation_starts_with_supported_action'),
      (await page.locator('#orientation-main').innerText()).trim().length>0&&
      !/^\s*Faltam informa[cç][oõ]es e apoios verificados/i.test(await page.locator('#orientation-main').innerText())&&
      await page.locator('#orientation-main .orientation-step').count()>0&&
      (await page.locator('#orientation-main .step-action').first().innerText()).trim().length>20);
    check(key('partial_orientation_has_named_blocks_and_limits'),
      await page.locator('#orientation-main .step-combination').count()>0&&
      await page.locator('.orientation-gaps').count()>0&&
      !/Fun[cç][aã]o requerida ainda sem/i.test(await page.locator('#orientation-main').innerText()));
    await page.screenshot({path:path.join(artifacts,view+'-teaching-partial.png'),fullPage:true});
    await page.locator('#new-case').click();await ready(page);
    await page.locator('#case-narrative').fill('Sou docente e quero ensinar um assunto complexo de matemática à minha turma, com dois estudantes surdos e um estudante cego.');
    await page.locator('#analyze-case').click();await page.locator('#case-questions').waitFor({state:'visible',timeout:180000});
    const variantAnswers=[];
    while(await page.locator('#case-questions').isVisible()){
      const row=page.locator('#questions-form [data-question]'),question=await row.getAttribute('data-question');
      const field=question.split(':')[0],person=await page.locator('#question-person').innerText();
      if(field==='apoios_informados')await row.locator('textarea').fill(/surd/i.test(person) ?
        'O grupo compreende texto e imagens. Outros apoios ainda precisam ser conferidos.' : 'A operação de leitor de tela ainda não foi confirmada. É preciso conferir outra forma de acesso.');
      else {
        const wanted=field==='tarefas' ? ['TAR-ACESSAR-COMPREENDER-CONTEUDO-DIGITAL'] :
          field==='barreira_ou_necessidade' ? ['NEC-ACESSO-EQUIVALENTE','NEC-ALTERNATIVA-FUNCIONAL-EQUIVALENTE'] :
          field==='participantes' ? ['PAPEL-RESPONSAVEL-ADAPTACAO'] :
          field==='modalidades_disponiveis' ? /surd/i.test(person) ? ['MOD-TEXTO','MOD-IMAGEM'] : ['MOD-AUDIO'] :
          field==='caracteristicas_pessoa' ? /ceg/i.test(person) ? ['CAR-INTERACAO-NAO-VISUAL'] : ['unknown'] :
          field==='recursos_digitais' ? ['RED-PAGINA-WEB'] : field==='ambientes' ? ['AMB-SALA-DE-AULA'] :
          field==='recursos_disponiveis' ? !person||/adapta/i.test(person) ? ['REC-EDITOR-MULTIMIDIA'] : ['unknown'] : [];
        assert(wanted.length,'Unexpected resource variant question: '+question);
        for(const value of wanted){
          const control=row.locator('input[value="'+value+'"]');
          assert.equal(await control.count(),1,'Existing resource variant option: '+value);
          if(!await control.isVisible())await control.evaluate(element=>{for(let ancestor=element.parentElement;ancestor;ancestor=ancestor.parentElement)if(ancestor.tagName==='DETAILS')ancestor.open=true;});
          await control.check();
        }
        if(field==='modalidades_disponiveis'&&person&&await row.locator('textarea').count()){
          const note=row.locator('textarea');await note.evaluate(element=>{for(let ancestor=element.parentElement;ancestor;ancestor=ancestor.parentElement)if(ancestor.tagName==='DETAILS')ancestor.open=true;});
          await note.fill(/surd/i.test(person)?'O grupo compreende texto e imagens. Outros apoios ainda precisam ser conferidos.':
            'A operação de leitor de tela ainda não foi confirmada. É preciso conferir outra forma de acesso.');
        }
      }
      await page.locator('#answer-questions').click();variantAnswers.push(question);
      assert.equal(new Set(variantAnswers).size,variantAnswers.length,'Resource variant questions must not repeat');
      assert(variantAnswers.length<=20,'Resource variant intake must terminate');
      await page.waitForFunction(previous=>!document.querySelector('#case-review').hidden||
        document.querySelector('#questions-form [data-question]')?.dataset.question!==previous,question,{timeout:180000});
    }
    const changedTeachingState=await page.evaluate(()=>window.__simpleProbe.state);
    check(key('reader_availability_and_operation_not_confirmed'),
      !changedTeachingState.context.raw.recursos_disponiveis.includes('REC-LEITOR-DE-TELA')&&
      changedTeachingState.participations.every(person=>!person.recurso_operado_ids.includes('REC-LEITOR-DE-TELA')));
    await page.locator('#case-confirmed').check();await page.locator('#generate-orientation').click();
    await page.locator('#orientation-result').waitFor({state:'visible',timeout:180000});
    const changedTeaching=await page.evaluate(()=>window.__simpleProbe.generated);
    report.teaching_resource_variant??={};report.teaching_resource_variant[view]={questions:variantAnswers,
      status:changedTeaching.decision.status,component_ids:changedTeaching.decision.component_ids,
      information_missing:changedTeaching.decision.informacoes_ausentes,
      note:'Same narrative; the reader availability and personal operation were not confirmed in the follow-up answers. This checks absence of support, not recognition of a textual prohibition.'};
    check(key('unconfirmed_reader_changes_teaching_decision'),changedTeaching.decision.status.startsWith('SUSPENSA')&&
      changedTeaching.decision.component_ids.length===0&&await page.locator('#orientation-result').isVisible());
    check(key('suspended_output_has_no_invented_action'),await page.locator('#orientation-main .orientation-step').count()===0&&
      (await page.locator('#orientation-main').innerText()).trim().length>0);
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
      const provisional=[{transcript:' Uma parte ainda sendo reconhecida',confidence:1}];provisional.isFinal=false;
      window.__speech.instances.at(-1).emit('result',{resultIndex:2,results:[first,second,provisional]});
    });
    check(key('provisional_voice_visibly_distinct'),/Transcrição provisória/.test(await page.locator('#dictation-preview').innerText())&&
      !(await page.locator('#case-narrative').inputValue()).includes('ainda sendo reconhecida'));
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
    await page.waitForFunction(()=>!document.querySelector('#case-questions').hidden||!document.querySelector('#case-review').hidden,{}, {timeout:180000});
    check(key('unchanged_narrative_preserves_answers'),
      (await page.locator('#case-questions').isHidden()||await page.locator('#questions-form [name="objetivo"]').count()===0)&&
      await page.evaluate(()=>window.__simpleProbe.state.context.objetivo)==='Compreender a informação das imagens e continuar a atividade.');
    if(await page.locator('#case-questions').isVisible())await page.locator('#skip-questions').click();
    await page.locator('#case-review').waitFor({state:'visible',timeout:180000});
    const busySnapshots=await page.evaluate(()=>window.__simpleProbe.busySnapshots);
    check(key('inputs_blocked_while_processing'),busySnapshots.length>0&&busySnapshots.every(snapshot=>snapshot.busy&&snapshot.controls.every(control=>control.blocked)));
    check(key('generation_progress_visible'),busySnapshots.filter(snapshot=>['generate','compose'].includes(snapshot.operation)).every(snapshot=>snapshot.generationVisible&&/orienta|combin|verifica/i.test(snapshot.generationText)));
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
}catch(error){report.passed=false;report.failure=String(error.stack||error)
  .replaceAll(root,'<PROJECT>').replaceAll(root.replaceAll('\\','/'),'<PROJECT>').replaceAll('file:///<PROJECT>','<PROJECT>');
  process.exitCode=1;await page?.screenshot({path:path.join(artifacts,'failure.png'),fullPage:true}).catch(()=>{});}
finally{
  await browser.close();await new Promise(resolve=>server.close(resolve));
  await fs.writeFile(path.join(root,'evidence',process.env.SIMPLE_PUBLIC_URL?'simple-flow-public.json':'simple-flow-browser.json'),JSON.stringify(report,null,2)+'\n');
  console.log(JSON.stringify({passed:report.passed,checks:Object.keys(report.checks).length,failure:report.failure||null},null,2));
}
