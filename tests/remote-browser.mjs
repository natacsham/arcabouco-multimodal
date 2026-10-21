// Real UI regression. The supplied narrative and explicitly synthetic follow-up
// remain tests only. No answer or confirmation is injected through the API.
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import path from 'node:path';
import http from 'node:http';
import os from 'node:os';
import {fileURLToPath,pathToFileURL} from 'node:url';

const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const web=path.join(root,'web'),prefix='/arcabouco-multimodal/';
let playwright;
try{playwright=await import('playwright');}
catch(error){
  if(error.code!=='ERR_MODULE_NOT_FOUND')throw error;
  const modules=process.env.AMADO_NODE_MODULES||path.join(os.homedir(),'.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules');
  playwright=await import(pathToFileURL(path.join(modules,'playwright/index.mjs')).href);
}
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
const base=`http://127.0.0.1:${server.address().port}${prefix}`;
const launch={headless:true};
if(process.env.AMADO_CHROMIUM)launch.executablePath=process.env.AMADO_CHROMIUM;
else if(process.platform==='win32'&&process.env.LOCALAPPDATA){
  const installed=path.join(process.env.LOCALAPPDATA,'ms-playwright/chromium-1243/chrome-win64/chrome.exe');
  if(await fs.access(installed).then(()=>true,()=>false))launch.executablePath=installed;
}
const browser=await playwright.chromium.launch(launch);
const context=await browser.newContext({viewport:{width:1280,height:900},reducedMotion:'reduce'});
const errors=[],networkWrites=[];
await context.route('**/*',route=>{
  const request=route.request();
  if(request.method()!=='GET')networkWrites.push(request.url());
  if(!request.url().startsWith(new URL(base).origin+'/')&&!request.url().startsWith('blob:'))return route.abort();
  return route.continue();
});
await context.addInitScript(()=>{
  window.__remoteReadOnly={current:null,result:null};
  const NativeWorker=window.Worker;
  window.Worker=class extends NativeWorker{
    constructor(...args){super(...args);this.operations=new Map();this.addEventListener('message',event=>{
      if(event.data.type!=='result')return;
      const operation=this.operations.get(event.data.id),data=event.data.data;
      if(data?.current?.context)window.__remoteReadOnly.current=data.current;
      else if(data?.context&&operation!=='generate')window.__remoteReadOnly.current=data;
      if(operation==='generate')window.__remoteReadOnly.result=data;
    });}
    postMessage(data,...rest){this.operations.set(data.id,data.operation);return super.postMessage(data,...rest);}
  };
});
const original='Sou uma professora do 1 ano do ensino fundamental I, onde tenho uma turma de 25 alunos que estão sendo alfabetizados. Tenho 3 alunos dessa turma com Transtorno do Espectro Autista. Estou querendo ministrar o conteudo referente a introdução fonemica. No entanto, devido a condições climáticas as aulas não podem ser presenciais. Estão sendo remotas. Por isso, vou precisar do apoio de um mediador, os pais, por exemplo, para que possam me apoiar indiretamente na condução da explicação e na realização das atividades.';
const adapted=original.replace('1 ano','4 ano').replace('25 alunos que estão sendo alfabetizados','30 alunos').replace('introdução fonemica','derivação por sufixação na disciplina de Língua Portuguesa');
// These conditions were NOT supplied by the user: they exercise an existing
// organization/retomada operation, not a prepared phonemic-awareness answer.
const synthetic=' Os alunos conseguem ler instruções curtas e ouvir áudio, mas perdem a sequência quando explico vários passos somente pela fala. Posso preparar instruções escritas e imagens das telas. Tenho computador com editor de apresentação; as famílias usam celular para acessar o material.';
const idle=page=>page.waitForFunction(()=>document.querySelector('#main')?.getAttribute('aria-busy')==='false',{}, {timeout:180000});
async function analyze(page,narrative,{scopeSyntheticObservation=false,groupCount=25}={}){
  await page.locator('#case-narrative').fill(narrative);
  await page.locator('#analyze-case').focus();await page.keyboard.press('Enter');
  await page.locator('#case-understanding').waitFor({state:'visible',timeout:180000});await idle(page);
  assert(await page.locator('#case-questions').isHidden());
  await page.locator('#continue-understanding').click();
  const questions=[];
  while(await page.locator('#case-questions').isVisible()){
    await idle(page);
    const field=page.locator('#question-fields [data-question]');
    const id=await field.getAttribute('data-question');
    assert(questions.length<3&&!questions.includes(id),'Unknown answers must not repeat or exceed the round');
    questions.push(id);
    const title=await page.locator('#questions-title').innerText();
    if(scopeSyntheticObservation&&/^Qual parte você quer analisar primeiro/.test(title)){
      await field.getByRole('radio',{name:'Apresentação e explicação coletiva',exact:true}).check();
      await page.locator('#answer-questions').click();
    }else if(scopeSyntheticObservation&&/refere-se a quem e a qual atividade/.test(title)){
      await field.getByRole('radio',{name:'Estudantes ('+groupCount+') — Apresentação e explicação coletiva',exact:true}).check();
      await page.locator('#answer-questions').click();
    }else if(await page.locator('#answer-unknown').isVisible())await page.locator('#answer-unknown').click();
    else{await field.locator('input[value="unknown"]').check();await page.locator('#answer-questions').click();}
    await idle(page);
  }
  await page.locator('#case-review').waitFor({state:'visible'});
  assert(await page.locator('#generate-orientation').isDisabled());
  return questions;
}
async function generate(page){
  await page.locator('#case-confirmed').check();await page.locator('#generate-orientation').click();
  await page.locator('#orientation-result').waitFor({state:'visible',timeout:180000});await idle(page);
  assert(await page.locator('#orientation-title').evaluate(el=>el===document.activeElement));
  return page.evaluate(()=>window.__remoteReadOnly.result);
}
const choices=result=>[...(result.choices||[]),...(result.pending_candidates||[]),...(result.partial_segments||[])];
try{
  for(const view of ['index.html','guiado.html']){
    const narrative=view==='index.html'?original:adapted,groupCount=view==='index.html'?25:30;
    const page=await context.newPage();page.on('pageerror',error=>errors.push(error.message));
    await page.goto(base+'amado/'+view);
    await page.waitForFunction(()=>['ready','error'].includes(document.querySelector('#health')?.dataset.state),{}, {timeout:180000});
    assert.equal(await page.locator('#health').getAttribute('data-state'),'ready');await idle(page);
    const questions=await analyze(page,narrative);
    const current=await page.evaluate(()=>window.__remoteReadOnly.current);
    const participants=current.participations||current.context.participantes||[];
    assert(participants.some(row=>(row.quantidade===groupCount||row.count===groupCount)),'The class total is retained without adding its subgroup');
    assert(participants.some(row=>(row.quantidade===3||row.count===3)&&/autis|TEA/i.test(JSON.stringify(row))),'The subgroup is retained');
    const empty=await generate(page);
    assert.equal(empty.result_contract,'AMADO_SITUATED_1');
    assert.equal(choices(empty).length,0,'Unknown capabilities must not become invented recommendations');
    assert.equal(empty.intake_status,'CONTEXT_UNKNOWN','Answered unknown conditions are not classified as a demonstrated base limitation');
    assert(empty.unresolved_answers.length>0&&empty.unresolved_answers.length<=3);
    assert.deepEqual(empty.next_questions,[],'Unknown answers are available for review, not automatically asked again');
    assert.equal(await page.locator('#orientation-main .orientation-recovery').count(),1);
    assert.equal(await page.locator('#orientation-main .situated-action').count(),0);
    assert.match(await page.locator('#orientation-main').innerText(),/Não é preciso repetir as respostas agora/);
    assert(!/ainda sem uma operação fundamentada/i.test(await page.locator('#orientation-state').innerText()));
    assert.match(await page.locator('#generation-status').innerText(),/sem orientação/);
    const review=page.locator('#orientation-main [data-edit-case]');
    await review.focus();await page.keyboard.press('Enter');
    await page.locator('#case-editor').waitFor({state:'visible'});
    assert(await page.locator('#editor-title').evaluate(el=>el===document.activeElement));
    assert(await page.locator('[data-revision="recursos_digitais"]').count());
    assert(await page.locator('[data-revision="recursos_disponiveis"]').count());
    assert.equal(await page.locator('#case-narrative').inputValue(),narrative);
    await page.locator('#case-editor [data-edit-narrative]').click();
    await page.locator('#case-entry').waitFor({state:'visible'});
    await analyze(page,narrative+synthetic,{scopeSyntheticObservation:true,groupCount});
    const revised=await page.evaluate(()=>window.__remoteReadOnly.current);
    assert(!(revised.context.raw?.recursos_disponiveis||[]).includes('REC-SMARTPHONE-AUDIO-HAPTICO'),
      'A generic family cellphone must not become a device with audio/haptic orientation');
    const supported=await generate(page);
    if(!choices(supported).length)console.error(JSON.stringify({view,followup_failure:{status:supported.proposal_status,intake_status:supported.intake_status,gaps:supported.gaps,exclusions:supported.exclusions,next_questions:supported.next_questions}}));
    assert(choices(supported).length>0,'Explicit synthetic functional conditions enable existing scoped support');
    assert(await page.locator('#orientation-main .situated-action').count()>0);
    assert.equal(await page.locator('#orientation-main .orientation-recovery').count(),0);
    await page.setViewportSize({width:320,height:760});
    assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1),'The revised result reflows at 320 CSS pixels');
    console.log(JSON.stringify({view,questions:questions.length,empty_status:empty.intake_status,synthetic_followup_status:supported.proposal_status,synthetic_supports:choices(supported).length}));
    await page.close();
  }
  assert.deepEqual(errors,[]);assert.deepEqual(networkWrites,[]);
  console.log('PASS remote browser: visible typed narrative, unknown answers, truthful empty state, keyboard review, editable gaps and synthetic functional follow-up. No human validation or pedagogical efficacy claim.');
}finally{await context.close();await browser.close();await new Promise(resolve=>server.close(resolve));}
