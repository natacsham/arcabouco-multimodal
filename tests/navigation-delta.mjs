// Narrow current-run navigation QA, guarded by exact bytes against the last
// verified release. Historical engine executions are not counted as new tests.
import fs from 'node:fs/promises';
import path from 'node:path';
import http from 'node:http';
import crypto from 'node:crypto';
import assert from 'node:assert/strict';
import {execFileSync} from 'node:child_process';
import {fileURLToPath,pathToFileURL} from 'node:url';

const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const web=path.join(root,'web'),baseline='bbd1df9';
const sha=data=>crypto.createHash('sha256').update(data).digest('hex');
const git=args=>execFileSync('git',args,{cwd:root,maxBuffer:64*1024*1024});
const files=git(['ls-tree','-r','--name-only',baseline,'--','ontology','data','shapes','queries','engine.py','web/amado','web/shell.css','web/site.js'])
  .toString('utf8').trim().split(/\r?\n/).filter(file=>file&&!['web/amado/index.html','web/amado/guiado.html','web/amado/manifest.json'].includes(file));
const report={scope:'Delta atual: bytes preservados e navegação nas duas apresentações do AMADO. Nenhuma geração, consulta ou nova validação ontológica executada.',
  change_kind:'NAVIGATION_LABEL_ONLY',allowed_change:{before:'Modelo e arquivos',after:'Documentação técnica',files:['web/amado/index.html','web/amado/guiado.html']},
  build:JSON.parse(await fs.readFile(path.join(web,'amado/manifest.json'),'utf8')),
  baseline_commit:baseline,started_at_utc:new Date().toISOString(),checks:{},unchanged_files:[],html_delta:[],historical_evidence:[],requests:[],
  limitations:['Motor deliberadamente não iniciado neste teste de navegação.','Geração, estados, equivalência decisória e recuperação pertencem aos relatórios históricos identificados, não a esta execução.','Não é avaliação humana nem conformidade WCAG.']};
const check=(name,value)=>{report.checks[name]=Boolean(value);assert(value,name);};
for(const file of files){
  const before=sha(git(['show',`${baseline}:${file}`])),current=sha(await fs.readFile(path.join(root,file)));
  report.unchanged_files.push({file,baseline_sha256:before,current_sha256:current,unchanged:before===current});
}
check('all_runtime_css_data_queries_and_ontology_bytes_preserved',report.unchanged_files.length>=25&&report.unchanged_files.every(row=>row.unchanged));
for(const file of ['web/amado/index.html','web/amado/guiado.html']){
  const before=git(['show',`${baseline}:${file}`]),current=await fs.readFile(path.join(root,file));
  const oldLabel='>Modelo e arquivos</a>',newLabel='>Documentação técnica</a>';
  const source=before.toString('utf8');
  assert.equal(source.split(oldLabel).length,2,'Exactly one old navigation label expected.');
  const expected=Buffer.from(source.replace(oldLabel,newLabel),'utf8');
  report.html_delta.push({file,baseline_sha256:sha(before),current_sha256:sha(current),only_navigation_label_changed:current.equals(expected)});
}
check('both_amado_html_only_navigation_label_changed',report.html_delta.every(row=>row.only_navigation_label_changed));
for(const file of ['evidence/browser-report.json','evidence/guided-report.json']){
  const bytes=git(['show',`${baseline}:${file}`]),prior=JSON.parse(bytes.toString('utf8'));
  assert.equal(prior.completed,true);
  report.historical_evidence.push({reference:`${baseline}:${file}`,sha256:sha(bytes),completed:true,
    scope:prior.scope||prior.change_verification?.scope,executed_by_current_run:false});
}
const modules=process.env.AMADO_NODE_MODULES||path.join(process.env.USERPROFILE,'.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules');
const {chromium}=await import(pathToFileURL(path.join(modules,'playwright/index.mjs')).href);
const server=http.createServer(async(req,res)=>{
  try{
    const pathname=decodeURIComponent(new URL(req.url,'http://localhost').pathname);
    if(pathname==='/favicon.ico'){res.writeHead(204).end();return;}
    if(!pathname.startsWith('/MADO/')){res.writeHead(404).end();return;}
    let rel=pathname.slice(6);if(!rel||rel.endsWith('/'))rel+='index.html';
    const target=path.resolve(web,rel);if(!target.startsWith(web+path.sep)){res.writeHead(403).end();return;}
    const mime={'.html':'text/html; charset=utf-8','.css':'text/css','.js':'text/javascript','.mjs':'text/javascript','.json':'application/json'};
    res.writeHead(200,{'Content-Type':mime[path.extname(target)]||'application/octet-stream','Cache-Control':'no-store'}).end(await fs.readFile(target));
  }catch{res.writeHead(404).end();}
});
await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
const base=(process.env.AMADO_SITE_URL||`http://127.0.0.1:${server.address().port}/MADO/`).replace(/\/?$/,'/');
const origin=new URL(base).origin;
report.execution_target=process.env.AMADO_SITE_URL?'PUBLIC_SITE':'LOCAL_SUBPATH';
if(process.env.AMADO_DEPLOYMENT_COMMIT)report.repository_commit_at_test=process.env.AMADO_DEPLOYMENT_COMMIT;
const browser=await chromium.launch({headless:true,executablePath:process.env.AMADO_CHROMIUM||'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe'});
report.browser=browser.version();
const page=await browser.newPage({viewport:{width:1280,height:900}});
await page.route('**/*',route=>{
  const url=route.request().url();report.requests.push({url:new URL(url).pathname,method:route.request().method()});
  if(!url.startsWith(origin+'/'))return route.abort();
  // A static navigation test must neither load the Python runtime nor imply
  // that the unchanged decision flow was re-executed.
  if(url.endsWith('/worker.mjs'))return route.fulfill({contentType:'text/javascript',body:'self.onmessage = () => {};'});
  return route.continue();
});
try{
  for(const [name,rel] of [['original','amado/'],['guided','amado/guiado.html']]){
    const response=await page.goto(base+rel,{waitUntil:'domcontentloaded'});
    const html=await response.body();
    check(name+'_served_html_matches',sha(html)===sha(await fs.readFile(path.join(web,rel.endsWith('/')?rel+'index.html':rel))));
    const nav=page.locator('header nav.nav');
    check(name+'_navigation_labels',JSON.stringify(await nav.locator('a').allTextContents())===JSON.stringify(['Entenda a MADO','Documentação técnica','Experimente o AMADO']));
    const link=nav.getByRole('link',{name:'Documentação técnica',exact:true});
    let reached=false;for(let n=0;n<35;n++){await page.keyboard.press('Tab');if(await link.evaluate(el=>el===document.activeElement)){reached=true;break;}}
    check(name+'_documentation_reached_by_tab',reached);
    await page.keyboard.press('Enter');await page.waitForURL(base+'ontologia/');
    check(name+'_documentation_link_destination',await page.locator('h1').count()===1&&await page.locator('header nav a[aria-current="page"]').textContent()==='Documentação técnica');
    await page.locator('header nav').getByRole('link',{name:'Experimente o AMADO',exact:true}).click();
    await page.waitForURL(base+'amado/');
    check(name+'_return_to_amado',page.url()===base+'amado/');
  }
  check('no_base_runtime_or_case_request',report.requests.every(row=>row.method==='GET'&&!/base\.zip|pyodide|python_stdlib/.test(row.url)));
  assert.deepEqual(JSON.parse(await fs.readFile(path.join(web,'amado/manifest.json'),'utf8')),report.build,'Manifest must remain unchanged during navigation QA.');
  report.completed=true;
}catch(error){report.completed=false;report.failure=error.message;process.exitCode=1;}
finally{
  report.finished_at_utc=new Date().toISOString();
  const name=process.env.AMADO_SITE_URL?'navigation-public-report.json':'navigation-delta-report.json';
  await fs.writeFile(path.join(root,'evidence',name),JSON.stringify(report,null,2)+'\n');
  await browser.close();await new Promise(resolve=>server.close(resolve));
  console.log(JSON.stringify({completed:report.completed,passed:Object.values(report.checks).filter(Boolean).length,total:Object.keys(report.checks).length,unchanged:report.unchanged_files.length,report:'evidence/'+name,failure:report.failure}));
}
