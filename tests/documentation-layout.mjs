// Visual measurements only; this script never loads the AMADO engine.
import fs from 'node:fs/promises';
import path from 'node:path';
import http from 'node:http';
import crypto from 'node:crypto';
import assert from 'node:assert/strict';
import {execFileSync} from 'node:child_process';
import {fileURLToPath,pathToFileURL} from 'node:url';

const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const reference=process.env.MADO_LAYOUT_REF || null;
const label=reference ? 'before-'+reference : 'after';
const artifacts=path.join(root,'tests/.artifacts/documentation-layout');
await fs.mkdir(artifacts,{recursive:true});
const modules=process.env.AMADO_NODE_MODULES || path.join(process.env.USERPROFILE,'.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules');
const {chromium}=await import(pathToFileURL(path.join(modules,'playwright/index.mjs')).href);
const served=new Map();
const sha=bytes=>crypto.createHash('sha256').update(bytes).digest('hex');
const mime={'.html':'text/html; charset=utf-8','.css':'text/css','.js':'text/javascript','.svg':'image/svg+xml'};
const server=http.createServer(async(req,res)=>{
  try{
    const pathname=decodeURIComponent(new URL(req.url,'http://localhost').pathname);
    if(pathname==='/favicon.ico'){res.writeHead(204).end();return;}
    if(!pathname.startsWith('/MADO/')){res.writeHead(404).end();return;}
    let rel=pathname.slice(6);if(!rel||rel.endsWith('/'))rel+='index.html';
    if(rel.includes('..')||rel.startsWith('/')){res.writeHead(403).end();return;}
    if(!served.has(rel))served.set(rel,reference
      ?execFileSync('git',['show',`${reference}:web/${rel}`],{cwd:root,maxBuffer:4*1024*1024})
      :await fs.readFile(path.join(root,'web',rel)));
    res.writeHead(200,{'Content-Type':mime[path.extname(rel)]||'application/octet-stream','Cache-Control':'no-store'}).end(served.get(rel));
  }catch{res.writeHead(404).end();}
});
await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
const base=`http://127.0.0.1:${server.address().port}/MADO/`;
const browser=await chromium.launch({headless:true,executablePath:process.env.AMADO_CHROMIUM||'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe'});
const page=await browser.newPage({viewport:{width:1440,height:900},reducedMotion:'reduce'});
const report={scope:'Medição visual da documentação técnica, sem execução do motor ou nova verificação ontológica.',reference:reference||'WORKTREE',started_at_utc:new Date().toISOString(),browser:browser.version(),measurements:[],errors:[]};
page.on('pageerror',error=>report.errors.push(error.message));
await page.route('**/*',route=>route.request().url().startsWith(base)?route.continue():route.abort());
const measure=()=>page.evaluate(()=>{
  const height=selector=>document.querySelector(selector)?.getBoundingClientRect().height??null;
  const h1=document.querySelector('h1'),range=document.createRange();range.selectNodeContents(h1);
  const lines=[...range.getClientRects()].filter(rect=>rect.width>0&&rect.height>0).map(rect=>Math.round(rect.top));
  return {viewport:innerWidth,document_height:document.documentElement.scrollHeight,scroll_width:document.documentElement.scrollWidth,
    main_height:height('main'),sequence_section_height:height('#camadas'),diagram_height:height('figure.uml-sequence,figure.execution-sequence'),
    svg_height:height('figure.uml-sequence svg'),h1_lines:new Set(lines).size,h1_font:parseFloat(getComputedStyle(h1).fontSize),root_font:parseFloat(getComputedStyle(document.documentElement).fontSize)};
});
try{
  for(const width of reference?[1440,1280]:[1440,1280,320]){
    await page.setViewportSize({width,height:900});
    await page.goto(base+'ontologia/',{waitUntil:'networkidle'});
    report.measurements.push(await measure());
    const figure=page.locator('figure.uml-sequence,figure.execution-sequence');
    await page.screenshot({path:path.join(artifacts,`${label}-${width}-page.png`),fullPage:true});
    if(await figure.count())await figure.screenshot({path:path.join(artifacts,`${label}-${width}-diagram.png`)});
    if(!reference&&width>=1280){
      const row=report.measurements.at(-1);assert.equal(row.h1_lines,1,'Technical H1 must fit one line at desktop 100%.');
      assert(row.diagram_height<=700,'Default desktop diagram must be no taller than 700px.');
    }
    if(!reference&&width===320){
      for(let n=0;n<4;n++)await page.locator('[data-font-increase]').click();
      const details=page.locator('details.sequence-text');
      if(await details.count())await details.locator('summary').click();
      report.measurements.push({...await measure(),text_200_percent:true,text_equivalent_open:true});
      await page.screenshot({path:path.join(artifacts,`${label}-${width}-200-page.png`),fullPage:true});
      assert.equal(report.measurements.at(-1).scroll_width,320,'Page must reflow at320px with text enlarged.');
    }
  }
  assert.equal(report.errors.length,0);report.completed=true;
}catch(error){report.completed=false;report.failure=error.message;process.exitCode=1;}
finally{
  report.sources=Object.fromEntries([...served].map(([name,data])=>[name,sha(data)]));
  report.finished_at_utc=new Date().toISOString();
  await fs.writeFile(path.join(artifacts,label+'.json'),JSON.stringify(report,null,2)+'\n');
  await browser.close();await new Promise(resolve=>server.close(resolve));
  console.log(JSON.stringify(report));
}
