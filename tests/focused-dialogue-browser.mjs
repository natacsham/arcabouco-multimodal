// Real-browser regression of short clarification rounds and action-first output.
// Synthetic inputs, not participant sessions or a full accessibility evaluation.
import assert from 'node:assert/strict';
async function advanceUnderstanding(page){
  await page.locator('#case-understanding').waitFor({state:'visible',timeout:180000});
  assert(await page.locator('#case-questions').isHidden(),'Understanding precedes questions');
  assert(await page.locator('#understanding-summary').innerText(),'Preview contains registered information');
  await page.locator('#continue-understanding').click();
}
import fs from 'node:fs/promises';
import path from 'node:path';
import http from 'node:http';
import crypto from 'node:crypto';
import {fileURLToPath,pathToFileURL} from 'node:url';

const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const web=path.join(root,'web'),prefix='/arcabouco-multimodal/';
const artifacts=path.join(root,'tests/.artifacts/focused-dialogue');await fs.mkdir(artifacts,{recursive:true});
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
const browser=await chromium.launch({headless:true,executablePath:process.env.AMADO_CHROMIUM||path.join(process.env.PROGRAMFILES,'Google/Chrome/Application/chrome.exe')});
const context=await browser.newContext({viewport:{width:1280,height:900},reducedMotion:'reduce'});
const report={type:'SYNTHETIC_FOCUSED_DIALOGUE_BROWSER',checked_at:new Date().toISOString(),checks:[],cases:[],errors:[],
  limits:['Not an expert review or a learning outcome.','NVDA and actual dictation recognition were not evaluated.']};
report.build=JSON.parse(await fs.readFile(path.join(web,'amado/manifest.json'),'utf8'));
report.test_sha256=crypto.createHash('sha256').update(await fs.readFile(fileURLToPath(import.meta.url))).digest('hex');
report.target=process.env.SIMPLE_PUBLIC_URL?'PUBLIC_SITE':'LOCAL_SUBPATH';
const check=(name,value)=>{assert(value,name);report.checks.push(name);};
const ready=page=>page.waitForFunction(()=>document.querySelector('#health')?.dataset.state==='ready'&&document.querySelector('#main')?.getAttribute('aria-busy')==='false',{}, {timeout:180000});
await context.addInitScript(()=>{
  window.__focusedProbe={generated:null,state:null,operations:[],progress:[]};
  const NativeWorker=window.Worker;
  window.Worker=class extends NativeWorker{
    constructor(...args){super(...args);this.operations=new Map();this.addEventListener('message',event=>{
      if(event.data.type==='progress'){window.__focusedProbe.progress.push(event.data);return;}
      if(event.data.type!=='result')return;
      const operation=this.operations.get(event.data.id),data=event.data.data;
      if(operation==='generate'||operation==='compose')window.__focusedProbe.generated=data;
      if(data?.current?.context)window.__focusedProbe.state=data.current;
      else if(data?.context&&operation!=='generate')window.__focusedProbe.state=data;
    });}
    postMessage(data,...rest){this.operations.set(data.id,data.operation);window.__focusedProbe.operations.push(data.operation);return super.postMessage(data,...rest);}
  };
});
const external=[];
await context.route('**/*',route=>{
  const request=route.request(),url=request.url();
  if(!url.startsWith(new URL(base).origin+'/')&&!url.startsWith('blob:')){external.push(url);return route.abort();}
  if(request.method()!=='GET')external.push(request.method()+' '+url);
  return route.continue();
});
async function answerRound(page,previous=new Set()){
  const answers=[];
  while(await page.locator('#case-questions').isVisible()){
    const row=page.locator('#question-fields [data-question]');
    const id=await row.getAttribute('data-question'),field=id.split(':')[0];
    assert(!previous.has(id)&&!answers.includes(id),'Answered or unknown questions must not repeat: '+id);
    assert(answers.length<3,'A round must end after at most three questions');
    const title=await page.locator('#questions-title').innerText();
    assert(!/^(Quais dificuldades ou necessidades você percebe|O que facilita ou dificulta a participação)\?$/.test(title));
    const total=Number(await page.locator('#question-progress').getAttribute('data-total'));
    assert(total<=3&&total>=answers.length+1,'Progress belongs to this short round');
    const selectExisting=async ids=>{
      for(const candidate of ids){
        const input=row.locator('input[value="'+candidate+'"]');
        if(await input.count()){
          await input.evaluate(element=>{for(let ancestor=element.parentElement;ancestor;ancestor=ancestor.parentElement)if(ancestor.tagName==='DETAILS')ancestor.open=true;});
          const label=input.locator('xpath=ancestor::label[1]');
          assert.equal(await label.evaluate(element=>getComputedStyle(element).cursor),'pointer');
          await label.click();return true;
        }
      }
      return false;
    };
    if(field==='tarefas')assert(await selectExisting(['TAR-ACESSAR-COMPREENDER-CONTEUDO-DIGITAL','TAR-ORGANIZAR-CONTEUDO-DIGITAL']),'Represented task must be selectable');
    else if(field==='objetivo')await row.locator('textarea').first().fill('Permitir que as pessoas acessem e compreendam o conteúdo apresentado.');
    else if(await row.locator('input[value="unknown"]').count())await row.locator('input[value="unknown"]').check();
    else await row.locator('textarea').first().fill('Ainda não sei');
    answers.push(id);
    await page.locator('#answer-questions').focus();await page.keyboard.press('Enter');
    await page.waitForFunction(previous=>!document.querySelector('#case-review').hidden||document.querySelector('#question-fields [data-question]')?.dataset.question!==previous,id,{timeout:180000});
  }
  await page.locator('#case-review').waitFor({state:'visible'});
  assert(await page.locator('#generate-orientation').isDisabled(),'Generating still requires confirmation');
  return answers;
}
async function generate(page){
  await page.locator('#case-confirmed').check();await page.locator('#generate-orientation').click();
  await page.locator('#orientation-result').waitFor({state:'visible',timeout:180000});
  assert(await page.locator('#orientation-title').evaluate(element=>element===document.activeElement));
  return page.evaluate(()=>window.__focusedProbe.generated);
}
try{
  for(const view of ['index.html','guiado.html']){
    const page=await context.newPage();page.on('pageerror',error=>report.errors.push(error.message));
    await page.goto(base+'amado/'+view);await ready(page);
    const name=label=>view+': '+label;
    check(name('initial field has a visible label and generic example'),
      await page.locator('label[for="case-narrative"]').count()===1&&!/matem[aá]tica/i.test(await page.locator('#case-narrative').getAttribute('placeholder')));
    const narrative='Sou docente e quero ensinar um assunto complexo de astronomia à minha turma, com dois estudantes surdos e um estudante cego.';
    await page.locator('#case-narrative').fill(narrative);await page.locator('#analyze-case').click();await advanceUnderstanding(page);
    await page.waitForFunction(()=>!document.querySelector('#case-questions').hidden||!document.querySelector('#case-review').hidden,{}, {timeout:180000});
    const first=await answerRound(page);
    check(name('initial round has at most three contextual questions'),first.length<=3);
    const state=await page.evaluate(()=>window.__focusedProbe.state);
    check(name('access requirements are sourced and scoped'),state.context.access_requirements?.length>0&&
      state.context.access_requirements.every(item=>item.matrix_id&&item.source_ids.length&&item.capabilities_inferred===false));
    check(name('base requirements are distinguished from reported abilities'),await page.locator('.review-requirements').count()===1&&
      await page.locator('.review-requirements').getAttribute('open')===null);
    const beforeFacts=structuredClone(state.participations||[]);
    const result=await generate(page);
    check(name('the real engine returns recorded checks'),result.execution_evidence?.checks.length>0);
    const configs=result.decision.configuracao_modal||[];
    check(name('represented access challenge has conditional or supported actions'),configs.length>0);
    check(name('actions are numbered only inside each configuration'),
      await page.locator('#orientation-title').innerText()==='O que você pode fazer'&&
      await page.locator('.orientation-step .action-instructions').count()===configs.length&&
      await page.locator('#orientation-main > ol').count()===0);
    check(name('steps display registered action fragments'),await page.locator('.action-instructions .step-action').count()>0);
    check(name('unknown reader is not implicitly available'),!state.context.raw.recursos_disponiveis.includes('REC-LEITOR-DE-TELA'));
    check(name('pending conditions are visible'),await page.locator('#orientation-main .step-conditions').count()>0);
    check(name('foundations remain optional and local'),await page.locator('.step-foundation').count()>0&&
      await page.locator('.step-foundation[open]').count()===0);
    report.cases.push({view,narrative,questions:first,status:result.decision.status,components:result.decision.component_ids,
      knowledge:result.decision.knowledge_ids,requirements:state.context.access_requirements});
    if(await page.locator('#complete-information').isVisible()){
      await page.locator('#complete-information').click();
      const refinement=await answerRound(page,new Set(first));
      check(name('optional refinement asks only new questions'),refinement.length<=3&&!refinement.some(id=>first.includes(id)));
      const refined=await page.evaluate(()=>window.__focusedProbe.state);
      for(const person of beforeFacts){
        const after=(refined.participations||[]).find(row=>row.id===person.id);
        assert(after,'Participant remains present');
        for(const field of ['modalidade_ids','caracteristica_ids','recurso_operado_ids'])
          assert((person[field]||[]).every(id=>(after[field]||[]).includes(id)),'Refinement preserves earlier facts');
      }
    }
    await page.locator('#new-case').click();await ready(page);
    await page.locator('#case-examples > summary').click();
    await page.locator('#case-template').selectOption('CTX-DEMO-WEB-LEITOR-TELA');await page.locator('#load-example').click();await advanceUnderstanding(page);
    await page.waitForFunction(()=>!document.querySelector('#case-questions').hidden||!document.querySelector('#case-review').hidden,{}, {timeout:180000});
    check(name('complete prepared case skips questions'),await page.locator('#case-review').isVisible());
    await generate(page);
    const progress=await page.evaluate(()=>window.__focusedProbe.progress.filter(row=>row.operation==='generate'));
    check(name('generation reports actual request-correlated phases'),progress.some(row=>row.stage==='retrieval'&&row.state==='completed'&&Number.isInteger(row.id))&&
      progress.some(row=>row.stage==='verification'&&row.state==='completed')&&progress.some(row=>row.stage==='composition'&&row.state==='completed'));
    check(name('presentation recorded only after output'),await page.locator('#generation-stages [data-stage="presentation"][data-state="completed"]').count()===1);
    await page.locator('#orientation-sources > summary').click();
    check(name('used source disclosure contains source links'),await page.locator('#orientation-sources-body a[href^="https://www.w3.org/"]').count()>0);
    check(name('source disclosure distinguishes prior extraction from live fetching'),/Não buscou estes documentos na internet/.test(await page.locator('#orientation-sources').innerText()));
    const oldNarrative=await page.locator('#case-narrative').inputValue();
    const oldOperations=await page.evaluate(()=>window.__focusedProbe.operations.filter(value=>value==='analyze').length);
    await page.locator('#orientation-result [data-edit-case]').click();
    check(name('correction opens existing and missing fields'),await page.locator('#case-editor').isVisible()&&
      await page.locator('[data-revision="ambientes"]').count()===1&&await page.locator('[data-revision="recursos_digitais"]').count()===1);
    await page.locator('[data-revision="objetivo"]').fill('Conferir e enviar o conteúdo com autonomia.');
    await page.locator('[data-revision="requester_relation"]').selectOption('seek_guidance');
    await page.locator('#save-case').click();
    await page.locator('#case-review').waitFor({state:'visible',timeout:180000});
    check(name('correction preserves narrative and requires new confirmation'),await page.locator('#case-narrative').inputValue()===oldNarrative&&await page.locator('#generate-orientation').isDisabled());
    check(name('correction replaces state without interpreting narrative again'),await page.evaluate(()=>window.__focusedProbe.operations.filter(value=>value==='analyze').length)===oldOperations&&
      await page.evaluate(()=>window.__focusedProbe.state.context.objetivo)==='Conferir e enviar o conteúdo com autonomia.'&&
      await page.evaluate(()=>window.__focusedProbe.state.context.requester_relation)==='seek_guidance');
    await generate(page);
    await page.setViewportSize({width:320,height:760});
    check(name('action output reflows at 320 pixels'),await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));
    await page.setViewportSize({width:1280,height:900});
    await page.locator('[data-font-increase]').click();
    check(name('reading controls remain reachable'),await page.locator('[data-font-reset]').isVisible());
    await page.locator('[data-site-contrast]').click();
    check(name('high contrast remains operable'),await page.locator('[data-site-contrast]').getAttribute('aria-pressed')==='true');
    await page.locator('#new-case').click();await ready(page);
    const formNarrative='Quero ensinar pessoas muito diferentes a usar o Google Forms.';
    await page.locator('#case-narrative').fill(formNarrative);await page.locator('#analyze-case').click();
    await page.locator('#case-understanding').waitFor({state:'visible',timeout:180000});
    check(name('Google Forms preview identifies the resource without assigning a teacher'),/formulário/i.test(await page.locator('#understanding-summary').innerText())&&
      !/professor/i.test(await page.locator('#understanding-summary').innerText()));
    check(name('Google Forms preview preserves the stated intention before questions'),/ensinar pessoas muito diferentes a usar o Google Forms/i.test(await page.locator('#understanding-summary').innerText()));
    if(view==='index.html')await page.screenshot({path:path.join(artifacts,'google-forms-understanding.png'),fullPage:true});
    await page.locator('#continue-understanding').click();
    if(await page.locator('#case-questions').isVisible())await page.locator('#skip-questions').click();
    await page.locator('#case-review').waitFor({state:'visible'});await page.locator('#edit-case').click();
    check(name('incomplete Google Forms case has an editable missing objective'),await page.locator('[data-revision="objetivo"]').count()===1);
    if(view==='index.html'){
      await page.screenshot({path:path.join(artifacts,'google-forms-editor-desktop.png'),fullPage:true});
      await page.setViewportSize({width:320,height:760});
      check(name('review editor reflows at 320 pixels'),await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));
      await page.screenshot({path:path.join(artifacts,'google-forms-editor-mobile.png'),fullPage:true});
      await page.setViewportSize({width:1280,height:900});
    }
    await page.locator('[data-revision="objetivo"]').fill('Permitir preencher e conferir as respostas.');
    await page.locator('[data-revision="requester_relation"]').selectOption('support');
    const resources=page.locator('[data-revision="recursos_disponiveis"]');
    await resources.locator('xpath=ancestor::details[1]').evaluate(element=>element.open=true);
    await resources.locator('input[value="REC-COMPUTADOR"]').check();
    await page.locator('#save-case').click();await page.locator('#case-review').waitFor({state:'visible',timeout:180000});
    const formState=await page.evaluate(()=>window.__focusedProbe.state);
    check(name('Google Forms edits reach the engine without restarting the narrative'),formState.context.requester_relation==='support'&&
      formState.context.raw.recursos_disponiveis.includes('REC-COMPUTADOR')&&await page.locator('#case-narrative').inputValue()===formNarrative);
    await page.locator('#edit-case').click();
    const changedResources=page.locator('[data-revision="recursos_disponiveis"]');
    await changedResources.locator('xpath=ancestor::details[1]').evaluate(element=>element.open=true);
    await changedResources.locator('input[value="REC-COMPUTADOR"]').uncheck();
    await page.locator('#save-case').click();await page.locator('#case-review').waitFor({state:'visible',timeout:180000});
    check(name('removing a resource replaces the previous selection'),!await page.evaluate(()=>window.__focusedProbe.state.context.raw.recursos_disponiveis.includes('REC-COMPUTADOR')));
    await page.close();
  }
  check('no unhandled browser errors',report.errors.length===0);
  check('no cases sent outside the static site',external.length===0);
  report.passed=true;
}catch(error){report.passed=false;report.failure=error.stack;process.exitCode=1;}
finally{
  const output=path.join(root,'tests/.artifacts/focused-dialogue');await fs.mkdir(output,{recursive:true});
  await fs.writeFile(path.join(output,'report.json'),JSON.stringify(report,null,2));
  if(!process.env.SIMPLE_PUBLIC_URL)await fs.writeFile(path.join(root,'evidence/focused-dialogue-browser.json'),JSON.stringify(report,null,2));
  await context.close();await browser.close();server.close();
  console.log(JSON.stringify({passed:report.passed,checks:report.checks.length,failure:report.failure||null},null,2));
}
