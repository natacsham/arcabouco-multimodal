// Presentation-only checks. This does not rerun semantic/ontology validation.
import fs from 'node:fs/promises';
import path from 'node:path';
import http from 'node:http';
import assert from 'node:assert/strict';
import crypto from 'node:crypto';
import {fileURLToPath,pathToFileURL} from 'node:url';
import {coreInvariantAudit, historicalReport, typographySnapshot, assertAmadoTypography, assertFixedViewportDoubling} from './presentation-metrics.mjs';

const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const web=path.join(root,'web');
const artifacts=path.join(root,'tests','.artifacts','site-presentation');
await fs.mkdir(artifacts,{recursive:true});
const modules=process.env.AMADO_NODE_MODULES || path.join(process.env.USERPROFILE,'.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules');
const {chromium}=await import(pathToFileURL(path.join(modules,'playwright/index.mjs')).href);
const mime={'.html':'text/html; charset=utf-8','.css':'text/css','.js':'text/javascript','.mjs':'text/javascript','.json':'application/json','.xml':'application/xml','.txt':'text/plain','.wasm':'application/wasm','.zip':'application/zip'};
const server=http.createServer(async(req,res)=>{
  try{
    const pathname=decodeURIComponent(new URL(req.url,'http://localhost').pathname);
    if(pathname==='/favicon.ico'){res.writeHead(204).end();return;}
    if(!pathname.startsWith('/MADO/')){res.writeHead(404).end();return;}
    let rel=pathname.slice('/MADO/'.length);
    if(!rel || rel.endsWith('/')) rel+='index.html';
    const target=path.resolve(web,rel);
    if(!target.startsWith(web+path.sep)){res.writeHead(403).end();return;}
    const contents=await fs.readFile(target);
    res.writeHead(200,{'Content-Type':mime[path.extname(target)]||'application/octet-stream','Cache-Control':'no-store'}).end(contents);
  }catch{res.writeHead(404).end();}
});
await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
const base=(process.env.AMADO_SITE_URL || `http://127.0.0.1:${server.address().port}/MADO/`).replace(/\/?$/,'/');
const origin=new URL(base).origin;
const publicBase='https://natacsham.github.io/MADO/';
const browser=await chromium.launch({headless:true,executablePath:process.env.AMADO_CHROMIUM || 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe'});
const report={
  scope:'Conteúdo, navegação, SEO técnico e apresentação acessível; não revalida motor ou ontologia.',
  execution_target:process.env.AMADO_SITE_URL?'PUBLIC_SITE':'LOCAL_SUBPATH',
  browser:browser.version(),started_at_utc:new Date().toISOString(),checks:{},pages:{},errors:[],external_requests:[],request_methods:[],
  limitations:['Não é declaração de conformidade WCAG.','NVDA, VoiceOver e fala audível não avaliados.','Metadados corretos não garantem indexação nem posição em buscas.','Contraste medido em amostra de elementos e estados; não cobre todos os pixels.','Casos e resultados semânticos permanecem vinculados aos relatórios de execução próprios.']
};
if(process.env.AMADO_SITE_URL) report.public_url=base;
if(process.env.AMADO_DEPLOYMENT_COMMIT) report.repository_commit_at_test=process.env.AMADO_DEPLOYMENT_COMMIT;
const sha=data=>crypto.createHash('sha256').update(data).digest('hex');
report.build=JSON.parse(await fs.readFile(path.join(web,'amado','manifest.json'),'utf8'));
report.source_sha256={};
for(const name of ['index.html','ontologia/index.html','site.css','shell.css','site.js','amado/index.html','amado/styles.css','amado/app.js','robots.txt','sitemap.xml']){
  try{report.source_sha256[name]=sha(await fs.readFile(path.join(web,name)));}catch{}
}
report.site_assets_sha256={};
for(const name of Object.keys(report.build.site_assets_sha256||{})){
  report.site_assets_sha256[name]=sha(await fs.readFile(path.join(web,name)));
}
const context=await browser.newContext({viewport:{width:1280,height:900},reducedMotion:'reduce'});
await context.route('**/*',async route=>{
  const req=route.request();
  if(!req.url().startsWith(origin+'/') && !req.url().startsWith('blob:')){
    report.external_requests.push(req.url());return route.abort();
  }
  report.request_methods.push(req.method());return route.continue();
});
const page=await context.newPage();
page.on('pageerror',error=>report.errors.push(error.message));
const check=(key,value)=>{report.checks[key]=Boolean(value);assert(value,key);};
const settled=()=>page.evaluate(()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve))));
const idle=()=>page.waitForFunction(()=>document.getElementById('main')?.getAttribute('aria-busy')==='false',{}, {timeout:180000});
async function keyboardFocus(selector){
  await page.evaluate(()=>{document.activeElement?.blur();window.scrollTo({top:0,behavior:'instant'});});
  for(let n=0;n<80;n++){
    await page.keyboard.press('Tab');
    if(await page.locator(selector).evaluate(el=>el===document.activeElement)) return;
  }
  throw new Error('Tab did not reach '+selector);
}
async function focusSample(selector){
  return page.locator(selector).evaluate(el=>{
    const s=getComputedStyle(el),r=el.getBoundingClientRect();
    return {outline_style:s.outlineStyle,outline_width:s.outlineWidth,outline_color:s.outlineColor,visible:r.width>0&&r.height>0,in_view:r.top>=0&&r.bottom<=innerHeight};
  });
}
async function svgTextScale(){
  return page.locator('.uml-diagram').evaluate(svg=>({width:svg.getBoundingClientRect().width,
    texts:[...svg.querySelectorAll('text')].map(el=>({text:el.textContent,
      rendered_pixel_size:parseFloat(getComputedStyle(el).fontSize)*Math.abs(el.getScreenCTM().a)}))}));
}
async function textSamples(){
  return page.evaluate(()=>{
    const rgba=value=>{
      const m=value.match(/rgba?\(([^)]+)\)/);if(!m)return null;
      const v=m[1].split(/[,\s/]+/).filter(Boolean).map(Number);return [...v.slice(0,3),v[3]??1];
    };
    const blend=(fg,bg)=>[0,1,2].map(i=>fg[i]*fg[3]+bg[i]*(1-fg[3]));
    function bg(el){
      const layers=[];let n=el;
      while(n){const c=rgba(getComputedStyle(n).backgroundColor);if(c)layers.push(c);n=n.parentElement;}
      let out=[255,255,255];for(const c of layers.reverse())out=blend(c,out);return out;
    }
    const lum=c=>c.map(x=>x/255).map(x=>x<=.04045?x/12.92:((x+.055)/1.055)**2.4).reduce((a,x,i)=>a+x*[.2126,.7152,.0722][i],0);
    const result=[];
    for(const selector of ['h1','h2','p','summary','a.button','button:not([disabled])','.nav a','.site-footer p','.topbar a','.topbar button:not([disabled])','[data-reading-status]']){
      const elements=[...document.querySelectorAll(selector)].filter(el=>el.checkVisibility() && el.textContent.trim());
      for(const el of elements.slice(0,3)){
        const s=getComputedStyle(el),foreground=rgba(s.color),background=bg(el);
        if(!foreground || s.opacity!=='1')continue;
        const rendered=blend(foreground,background),l1=lum(rendered),l2=lum(background);
        const ratio=(Math.max(l1,l2)+.05)/(Math.min(l1,l2)+.05);
        const large=parseFloat(s.fontSize)>=24 || (parseFloat(s.fontSize)>=18.66 && parseInt(s.fontWeight)>=700);
        result.push({selector,text:el.textContent.trim().slice(0,65),foreground:s.color,background:background.map(Math.round),ratio,minimum:large?3:4.5});
      }
    }
    return result;
  });
}
async function assertReflow(key){
  await settled();
  const size=await page.evaluate(()=>({viewport:innerWidth,scroll:document.documentElement.scrollWidth}));
  report.layout_dimensions??={};report.layout_dimensions[key]=size;
  if(size.scroll>size.viewport+1){
    report.layout_overflow??={};
    report.layout_overflow[key]=await page.evaluate(()=>[...document.querySelectorAll('body *')].filter(el=>el.checkVisibility()&&el.getBoundingClientRect().right>innerWidth+1).slice(0,15).map(el=>({tag:el.tagName,id:el.id,text:el.textContent.trim().slice(0,80),right:el.getBoundingClientRect().right})));
  }
  check(key,size.scroll<=size.viewport+1);return size;
}
const localTargets=new Map();
async function checkLocalLinks(name){
  const links=await page.locator('a[href]').evaluateAll(nodes=>nodes.map(el=>({href:el.href,text:el.textContent.trim()})));
  const currentDocument=new URL(page.url());currentDocument.hash='';
  const currentIds=await page.locator('[id],a[name]').evaluateAll(nodes=>nodes.map(el=>el.id||el.getAttribute('name')));
  const checked=[];
  for(const link of links){
    const target=new URL(link.href);
    if(target.origin!==origin || !target.pathname.startsWith(new URL(base).pathname))continue;
    const anchor=decodeURIComponent(target.hash.slice(1));target.hash='';
    if(!localTargets.has(target.href)){
      const response=await context.request.get(target.href);
      const contentType=response.headers()['content-type']||'';
      const html=contentType.includes('text/html')?await response.text():null;
      const ids=html===null?[]:await page.evaluate(text=>{
        const doc=new DOMParser().parseFromString(text,'text/html');
        return [...doc.querySelectorAll('[id],a[name]')].map(el=>el.id||el.getAttribute('name'));
      },html);
      localTargets.set(target.href,{status:response.status(),ids,html:html!==null});
    }
    const resource=localTargets.get(target.href);
    const ids=target.href===currentDocument.href?currentIds:resource.ids;
    const item={href:target.pathname+(anchor?'#'+anchor:''),text:link.text,status:resource.status,anchor_exists:!anchor||ids.includes(anchor)};
    checked.push(item);
  }
  report.pages[name].local_links=checked;
  check(name+'_local_links_and_anchors',checked.length>0&&checked.every(link=>link.status===200&&link.anchor_exists));
}
try{
  report.core_invariants=await coreInvariantAudit(root);
  report.historical_baseline=historicalReport(root,'evidence/site-presentation-report.json','bbd1df9');
  check('site_assets_match_manifest',Object.keys(report.site_assets_sha256).length>=5 && JSON.stringify(report.site_assets_sha256)===JSON.stringify(report.build.site_assets_sha256));
  report.served_site_assets_sha256={};
  for(const name of Object.keys(report.site_assets_sha256)){
    const response=await context.request.get(base+name);
    assert.equal(response.status(),200,'Asset must be served: '+name);
    report.served_site_assets_sha256[name]=sha(await response.body());
  }
  check('served_site_assets_match',JSON.stringify(report.served_site_assets_sha256)===JSON.stringify(report.site_assets_sha256));
  const titles=[];
  for(const [name,rel] of [['home',''],['ontology','ontologia/'],['amado','amado/']]){
    await page.setViewportSize({width:1280,height:900});
    await page.emulateMedia({forcedColors:'none',reducedMotion:'reduce'});
    const response=await page.goto(base+rel,{waitUntil:'domcontentloaded'});
    check(name+'_http_200',response.status()===200);
    if(name==='amado')await idle();
    const metadata=await page.evaluate(()=>({
      title:document.title,lang:document.documentElement.lang,
      author:document.querySelector('meta[name="author"]')?.content,
      description:document.querySelector('meta[name="description"]')?.content,
      canonical:document.querySelector('link[rel="canonical"]')?.href,
      og_title:document.querySelector('meta[property="og:title"]')?.content,
      og_url:document.querySelector('meta[property="og:url"]')?.content,
      robots:document.querySelector('meta[name="robots"]')?.content,
      jsonld:[...document.querySelectorAll('script[type="application/ld+json"]')].map(x=>JSON.parse(x.textContent)),
      h1_count:document.querySelectorAll('h1').length,main_count:document.querySelectorAll('main').length
    }));
    report.pages[name]={metadata};titles.push(metadata.title);
    const pageFile=rel+'index.html';
    check(name+'_served_source_matches',sha(await response.body())===report.source_sha256[pageFile]);
    check(name+'_semantic_document',metadata.lang==='pt-BR'&&metadata.h1_count===1&&metadata.main_count===1);
    check(name+'_seo',metadata.title.length>10&&metadata.description?.length>30&&metadata.canonical===publicBase+rel&&metadata.og_url===metadata.canonical&&Boolean(metadata.og_title)&&metadata.jsonld.length>0&&!/noindex/i.test(metadata.robots||''));
    check(name+'_jsonld_schema',metadata.jsonld.every(x=>x['@context']==='https://schema.org' && Boolean(x['@type']||x['@graph'])));
    check(name+'_author_metadata',metadata.author==='Natacsha Ordones Raposo de Melo');
    const navigation=await page.locator('header.site-header .nav a').allInnerTexts();
    check(name+'_shared_navigation',JSON.stringify(navigation.map(x=>x.trim()))===JSON.stringify(['Entenda a MADO','Documentação técnica','Experimente o AMADO']));
    check(name+'_single_current_navigation',await page.locator('header.site-header .nav a[aria-current="page"]').count()===1);
    check(name+'_shared_shell_loaded',await page.locator('link[rel="stylesheet"][href$="shell.css"]').count()===1);
    check(name+'_no_positive_tabindex',await page.locator('[tabindex]').evaluateAll(nodes=>nodes.every(x=>Number(x.getAttribute('tabindex'))<=0)));
    await page.keyboard.press('Tab');
    const skip=await page.evaluate(()=>({href:document.activeElement?.getAttribute('href'),name:document.activeElement?.textContent}));
    check(name+'_skip_link_first',skip.href?.startsWith('#')&&/conteúdo/i.test(skip.name));
    await page.keyboard.press('Enter');
    check(name+'_skip_link_focus',await page.evaluate(()=>document.activeElement===document.querySelector('main')));

    {
      const toolbar=page.locator('[data-site-accessibility]');
      check(name+'_toolbar_present',await toolbar.count()===1);
      const selectors=['[data-font-increase]','[data-font-decrease]','[data-font-reset]','[data-site-contrast]'];
      check(name+'_native_named_buttons',await page.locator(selectors.join(',')).evaluateAll(nodes=>nodes.length===4&&nodes.every(x=>x.tagName==='BUTTON'&&x.type==='button'&&Boolean(x.textContent.trim()||x.getAttribute('aria-label')))));
      await keyboardFocus('[data-font-increase]');
      const focus=await focusSample('[data-font-increase]');report.pages[name].focus=focus;
      check(name+'_keyboard_visible_focus',focus.visible&&focus.in_view&&focus.outline_style!=='none'&&parseFloat(focus.outline_width)>=2);
      const originalSize=await page.locator('html').evaluate(el=>parseFloat(getComputedStyle(el).fontSize));
      report.pages[name].font_base=originalSize;
      check(name+'_font_base_16',originalSize===16);
      report.pages[name].typography_desktop=await typographySnapshot(page);
      if(name==='ontology')report.pages[name].svg_desktop=await svgTextScale();
      if(name==='amado')assertAmadoTypography(report.pages[name].typography_desktop);
      if(name==='home')check('home_h1_desktop_40',report.pages[name].typography_desktop.headings.h1[0].pixels===40);
      await page.keyboard.press('Enter');
      check(name+'_keyboard_text_enlargement',await page.locator('html').evaluate(el=>parseFloat(getComputedStyle(el).fontSize))>originalSize);
      for(let n=0;n<25;n++)if(await page.locator('[data-font-increase]').isEnabled())await page.locator('[data-font-increase]').click();
      const enlarged=await page.locator('html').evaluate(el=>({style:el.style.fontSize,pixels:parseFloat(getComputedStyle(el).fontSize)}));
      report.pages[name].font_200=enlarged;
      check(name+'_text_200_percent',Math.abs(enlarged.pixels/originalSize-2)<.02);
      report.pages[name].typography_desktop_200=await typographySnapshot(page);
      report.pages[name].desktop_doubling=assertFixedViewportDoubling(report.pages[name].typography_desktop,report.pages[name].typography_desktop_200);
      if(name==='ontology'){
        report.pages[name].svg_desktop_200=await svgTextScale();
        const before=report.pages[name].svg_desktop,after=report.pages[name].svg_desktop_200;
        check('ontology_rendered_svg_text_doubles',Math.abs(after.width/before.width-2)<.02&&before.texts.every((row,index)=>Math.abs(after.texts[index].rendered_pixel_size/row.rendered_pixel_size-2)<.02));
      }
      check(name+'_actual_fonts_double_fixed_viewport',true);
      await assertReflow(name+'_text_200_reflow');
      await page.locator('[data-font-reset]').click();
      check(name+'_font_reset',await page.locator('html').evaluate(el=>parseFloat(getComputedStyle(el).fontSize))===originalSize);
      for(let n=0;n<15;n++)if(await page.locator('[data-font-decrease]').isEnabled())await page.locator('[data-font-decrease]').click();
      check(name+'_font_not_below_100',await page.locator('html').evaluate(el=>parseFloat(getComputedStyle(el).fontSize))===originalSize);
      const live=await page.locator('[data-reading-status]').evaluate(el=>({role:el.getAttribute('role'),live:el.getAttribute('aria-live')}));
      check(name+'_status_semantics',live.role==='status'||live.live==='polite');
      report.pages[name].contrast_default=await textSamples();
      check(name+'_contrast_default',report.pages[name].contrast_default.length>8&&report.pages[name].contrast_default.every(x=>x.ratio>=x.minimum));
      await keyboardFocus('[data-site-contrast]');await page.keyboard.press('Space');
      check(name+'_contrast_keyboard_toggle',await page.locator('html').getAttribute('data-contrast')==='high'&&await page.locator('[data-site-contrast]').getAttribute('aria-pressed')==='true');
      report.pages[name].contrast_high=await textSamples();
      check(name+'_contrast_high',report.pages[name].contrast_high.every(x=>x.ratio>=x.minimum));
      await page.screenshot({path:path.join(artifacts,name+'-contrast.png')});
      await page.locator('[data-site-contrast]').click();
      await page.locator('[data-site-top]').focus();await page.keyboard.press('Enter');await settled();
      check(name+'_top_link_focus',await page.evaluate(()=>document.activeElement?.id==='inicio'));
    }
    if(name==='amado'){
      const homeLink=page.locator('header').getByRole('link',{name:'Entenda a MADO',exact:true});
      check('amado_home_navigation',await homeLink.count()===1);
      const href=await homeLink.getAttribute('href');
      check('amado_home_subpath',new URL(href,page.url()).pathname==='/MADO/');
      const top=page.getByRole('link',{name:/Voltar ao (?:topo|início)/i});
      check('amado_top_link',await top.count()===1);
      await top.focus();await page.keyboard.press('Enter');await settled();
      check('amado_top_focus',await page.evaluate(()=>['inicio','page-title'].includes(document.activeElement?.id)));
      report.pages[name].contrast_default=await textSamples();
      check('amado_contrast_sample',report.pages[name].contrast_default.every(x=>x.ratio>=x.minimum));
      const originalURL=page.url().split('#')[0];
      const switcher=page.getByRole('navigation',{name:'Apresentação do AMADO',exact:true});
      const views=await switcher.locator('a').evaluateAll(nodes=>nodes.map(el=>({text:el.textContent.trim(),href:el.href,current:el.getAttribute('aria-current')})));
      report.pages[name].view_navigation=views;
      check('amado_two_presentations_linked',views.length===2&&views.filter(x=>x.current==='page').length===1&&views[0].text==='Visão atual'&&views[0].current==='page'&&views[0].href===base+'amado/'&&views[1].text.startsWith('Visão guiada')&&views[1].href===base+'amado/guiado.html');
      check('amado_view_change_discloses_discard',(await switcher.innerText()).includes('Ao mudar de visão, o caso aberto é descartado.'));
      await keyboardFocus('.view-switch a[href$="guiado.html"]');
      await page.keyboard.press('Enter');
      await page.waitForURL(base+'amado/guiado.html');
      const guidedSwitch=page.getByRole('navigation',{name:'Apresentação do AMADO',exact:true});
      await guidedSwitch.waitFor();
      check('guided_view_current_navigation',await guidedSwitch.locator('a[aria-current="page"]').count()===1&&/Visão guiada/.test(await guidedSwitch.locator('a[aria-current="page"]').innerText()));
      const returnLink=guidedSwitch.getByRole('link',{name:'Visão atual',exact:true});
      check('guided_view_return_link',await returnLink.count()===1&&new URL(await returnLink.getAttribute('href'),page.url()).href===originalURL);
      await returnLink.focus();await page.keyboard.press('Enter');
      await page.waitForURL(originalURL);await idle();
      check('amado_view_navigation_keyboard_roundtrip',page.url()===originalURL&&await page.locator('#runtime-error').innerText()==='');
      report.pages[name].guided_scope='Somente navegação entre apresentações; funcionamento e geração na visão guiada são avaliados no relatório próprio.';
    }
    if(name==='home'){
      const body=await page.locator('body').innerText();
      const headline=async selector=>(await page.locator(selector).textContent()).trim();
      check('home_approved_headlines',(await headline('h1'))==='Apoio a decisões de acessibilidade na interação digital'&&(await headline('#exemplo h2'))==='Como o conhecimento orienta uma decisão'&&(await headline('#exemplo .eyebrow'))==='Exemplo de aplicação'&&(await headline('#multimodal'))==='O papel das modalidades na orientação');
      report.pages[name].technical_terms_visible=body.match(/\b(?:RDF|OWL|SHACL|SPARQL|Pyodide|K\d{2}|CA\d{2}|ART-[A-Z]+-\d+)\b/g)||[];
      check('home_no_unexplained_identifiers',report.pages[name].technical_terms_visible.length===0);
      check('home_explanatory_example_preserved',await page.locator('#exemplo .steps>li').count()>=3);
      const cardTitles=await page.locator('main .cards h3').allInnerTexts();
      check('home_no_three_artifact_triptych',!['Arcabouço','MADO','AMADO'].every(term=>cardTitles.some(title=>title.trim()===term)));
      const problem=page.locator('.research-problem');
      const problemText=(await problem.innerText()).replace(/\s+/g,' ');
      const preservedStatements=[
        'Encontrar informação não é o mesmo que saber como empregá-la.',
        'Normas, estudos, artefatos, personas e resultados oferecem conhecimentos diferentes.',
        'O Arcabouço Multimodal para Acessibilidade Digital organiza as relações entre esses conhecimentos, preservando suas condições e permitindo conferir seu emprego em uma nova decisão.',
        'A MADO representa o conhecimento e suas relações; o AMADO permite consultar essa mesma base e acompanhar a construção de uma orientação.'
      ];
      check('home_problem_content_preserved',preservedStatements.every(text=>problemText.includes(text)));
      check('home_problem_three_functional_blocks',JSON.stringify(await problem.locator('.problem-block h3').allInnerTexts())===JSON.stringify(['De onde vem o conhecimento','Como o conhecimento se articula','Uma base para conferir']));
      report.pages[name].example_desktop_grid=await page.locator('#exemplo .steps').evaluate(el=>({columns:getComputedStyle(el).gridTemplateColumns.split(' ').length,items:[...el.children].map(item=>({top:item.getBoundingClientRect().top,left:item.getBoundingClientRect().left}))}));
      const grid=report.pages[name].example_desktop_grid;
      check('home_example_two_by_two',grid.columns===2&&grid.items.length===4&&Math.abs(grid.items[0].top-grid.items[1].top)<1&&Math.abs(grid.items[2].top-grid.items[3].top)<1&&grid.items[2].top>grid.items[0].top);
      report.pages[name].problem_desktop_columns=await problem.locator('.problem-grid').evaluate(el=>getComputedStyle(el).gridTemplateColumns.split(' ').length);
      check('home_problem_three_desktop_columns',report.pages[name].problem_desktop_columns===3);
      check('home_problem_static_not_interactive',await problem.locator('.problem-block').evaluateAll(nodes=>nodes.every(el=>!el.hasAttribute('tabindex')&&getComputedStyle(el).cursor!=='pointer')));
      check('home_limits_preserved',await page.getByText('Quando não há conhecimento suficiente',{exact:true}).count()===1&&await page.getByText('O que esta demonstração não comprova',{exact:true}).count()===1&&(await page.locator('main').textContent()).includes('Ela não comprova ganho de aprendizagem, cobertura universal ou acessibilidade integral.'));
    }
    if(name!=='amado'){
      const text=await page.locator('body').innerText();
      check(name+'_authorship_and_acronym',text.includes('Natacsha Ordones Raposo de Melo')&&text.includes('Multimodal Accessibility Decision Ontology'));
      if(name==='home')check('home_approved_project_description',text.includes('A MADO organiza conhecimentos sobre acessibilidade e interação multimodal')&&text.includes('Projeto de pesquisa de doutorado de Natacsha Ordones Raposo de Melo.'));
      report.pages[name].long_main_paragraphs=await page.locator('main p').evaluateAll(nodes=>nodes.map(el=>el.textContent.replace(/\s+/g,' ').trim()).filter(text=>text.length>170));
      if(name==='home'){
        const card=page.locator('main .card').first();
        const snapshot=()=>card.evaluate(el=>{const r=el.getBoundingClientRect(),s=getComputedStyle(el);return {width:r.width,height:r.height,transform:s.transform,border:s.borderColor,shadow:s.boxShadow,transition:s.transitionDuration,tabindex:el.getAttribute('tabindex'),cursor:s.cursor};});
        await page.emulateMedia({reducedMotion:'no-preference'});
        await page.mouse.move(0,0);await settled();const before=await snapshot();
        await card.hover();await card.evaluate(async el=>{await Promise.all(el.getAnimations().map(a=>a.finished.catch(()=>{})));});
        const hovered=await snapshot();report.pages[name].hover={before,hovered};
        check('home_static_card_keeps_geometry',Math.abs(hovered.width-before.width)<1&&Math.abs(hovered.height-before.height)<1&&hovered.transform==='none');
        check('home_static_card_not_click_target',hovered.tabindex===null&&hovered.cursor!=='pointer');
        await page.emulateMedia({reducedMotion:'reduce'});await settled();
        const reduced=await snapshot();report.pages[name].hover.reduced=reduced;
        check('home_hover_respects_reduced_motion',reduced.transform==='none'&&reduced.transition.split(',').every(x=>parseFloat(x)===0));
      }else{
        check('ontology_no_repeated_record_example',!/\b(?:ART-REF-03|K43)\b/.test(text)&&await page.locator('#exemplo-tecnico').count()===0);
        const disclosures=page.locator('main .concept-grid > details');
        check('ontology_six_native_concept_disclosures',await disclosures.count()===6&&await disclosures.locator(':scope > summary').count()===6);
        report.pages[name].concept_disclosures=[];
        for(let index=0;index<6;index++){
          const item=disclosures.nth(index),summary=item.locator(':scope > summary');
          if(await item.getAttribute('open')!==null)await summary.click();
          await keyboardFocus(`main .concept-grid > details:nth-child(${index+1}) > summary`);
          const label=(await summary.innerText()).trim();
          check('ontology_concept_'+(index+1)+'_keyboard_focus',await summary.evaluate(el=>el===document.activeElement));
          check('ontology_concept_'+(index+1)+'_pointer_means_action',await summary.evaluate(el=>getComputedStyle(el).cursor)==='pointer');
          await page.keyboard.press('Enter');
          check('ontology_concept_'+(index+1)+'_keyboard_opens',await item.getAttribute('open')!==null);
          const detailText=await item.locator(':scope > :not(summary)').allInnerTexts();
          check('ontology_concept_'+(index+1)+'_has_definition',detailText.join(' ').trim().length>40);
          await page.keyboard.press('Space');
          check('ontology_concept_'+(index+1)+'_keyboard_closes',await item.getAttribute('open')===null&&await summary.evaluate(el=>el===document.activeElement));
          report.pages[name].concept_disclosures.push({label,keyboard_open_close:true});
        }
        check('ontology_relations_definition_list',await page.locator('#relacoes .model-relations dt').count()===6&&await page.locator('#relacoes .model-relations dd').count()===6);
        const sequence=page.locator('figure.uml-sequence'),svg=sequence.locator('svg'),equivalent=page.locator('details.sequence-text');
        check('ontology_inline_svg_not_raster',await svg.count()===1&&await sequence.locator('canvas,img').count()===0&&await svg.getAttribute('role')==='img');
        check('ontology_svg_has_name_description',await svg.locator('title').count()===1&&await svg.locator('desc').count()===1&&(await svg.getAttribute('aria-labelledby')).split(/\s+/).length===2);
        check('ontology_uml_four_lifelines',await svg.locator('.uml-lifeline').count()===4&&(await svg.locator('.uml-participants').textContent()).includes('Pessoa')&&(await svg.locator('.uml-participants').textContent()).includes('Base MADO'));
        check('ontology_uml_calls_returns_alternative',await svg.locator('.uml-message,.uml-call').count()>=6&&await svg.locator('.uml-reply').count()>=3&&await svg.locator('.uml-alt').count()===1&&await svg.locator('.uml-alt .uml-guard').count()===2);
        report.pages[name].svg_accessible_snapshot=await svg.ariaSnapshot();
        check('ontology_svg_single_accessible_image',await sequence.getByRole('img').count()===1&&/^- ['"]?img /.test(report.pages[name].svg_accessible_snapshot.trim()));
        const height=await sequence.evaluate(el=>el.getBoundingClientRect().height);
        report.pages[name].diagram_desktop_height=height;check('ontology_diagram_compact_desktop',height<=700);
        for(const selector of ['h1','#camadas-titulo'])check('ontology_'+(selector==='h1'?'title':'flow_title')+'_single_line_desktop',await page.locator(selector).evaluate(el=>{const range=document.createRange();range.selectNodeContents(el);return new Set([...range.getClientRects()].filter(r=>r.width>0).map(r=>Math.round(r.top))).size===1;}));
        check('ontology_sequence_text_collapsed',await equivalent.count()===1&&await equivalent.getAttribute('open')===null);
        await keyboardFocus('details.sequence-text > summary');await page.keyboard.press('Enter');
        check('ontology_sequence_text_keyboard_opens',await equivalent.getAttribute('open')!==null);
        const expectedStages=['Informar o caso.','Organizar as informações.','Conferir e confirmar.','Consultar a base.','Verificar e compor.','Apresentar o resultado.'];
        check('ontology_text_equivalent_six_stages',JSON.stringify(await equivalent.locator('ol > li > strong').allTextContents())===JSON.stringify(expectedStages));
        const equivalentText=await equivalent.innerText();
        check('ontology_text_keeps_confirmation_and_suspension',equivalentText.includes('a pessoa revisa, corrige ou complementa')&&equivalentText.includes('sem dados ou fundamentos suficientes, suspende')&&equivalentText.includes('SPARQL'));
        const accessibleSequence=await equivalent.ariaSnapshot();report.pages[name].sequence_accessible_snapshot=accessibleSequence;
        check('ontology_sequence_accessible_order',(accessibleSequence.match(/- listitem:/g)||[]).length===6&&expectedStages.every((text,index)=>index===0||accessibleSequence.indexOf(text)>accessibleSequence.indexOf(expectedStages[index-1])));
        report.pages[name].sequence_accessibility_scope='SVG com nome e descrição; alternativa HTML em seis etapas, aberta por teclado e examinada na árvore acessível. Não é teste humano com NVDA ou VoiceOver.';
        await page.keyboard.press('Space');check('ontology_sequence_text_keyboard_closes',await equivalent.getAttribute('open')===null);
        check('ontology_preparation_separate',await page.locator('.curation-note').evaluate(el=>Boolean(el.compareDocumentPosition(document.querySelector('.uml-sequence'))&Node.DOCUMENT_POSITION_FOLLOWING))&&(await page.locator('.curation-note').textContent()).includes('O clique não cria'));
        check('ontology_reasoner_not_runtime_composer',(await page.locator('.implementation-list').textContent()).includes('não é o mecanismo que compõe a orientação durante o uso da página'));
        check('ontology_scope_preserved',(await page.locator('.execution-limit').textContent()).includes('A consulta não cria conhecimento nem incorpora o caso à base'));
        report.pages[name].compact_layout=await page.evaluate(()=>({viewport:innerWidth,page_height:document.documentElement.scrollHeight,
          section_height:document.querySelector('#camadas').getBoundingClientRect().height,figure_height:document.querySelector('.uml-sequence').getBoundingClientRect().height}));
        try{
          const before=JSON.parse(await fs.readFile(path.join(root,'tests/.artifacts/documentation-layout/before-bbd1df9.json'),'utf8'));
          report.pages[name].layout_baseline={reference:before.reference,sources:before.sources,measurements:before.measurements};
        }catch{report.pages[name].layout_baseline={reference:'bbd1df9',status:'Measurements not available in this checkout; current dimensions are measured directly.'};}
        await sequence.screenshot({path:path.join(artifacts,'ontology-sequence-desktop.png')});
      }
      report.pages[name].false_pointer_targets=await page.locator('main *').evaluateAll(nodes=>nodes.filter(el=>el.checkVisibility()&&getComputedStyle(el).cursor==='pointer'&&!el.closest('a[href],button,summary')).map(el=>({tag:el.tagName,text:el.textContent.trim().slice(0,70)})));
      check(name+'_pointer_only_actual_controls',report.pages[name].false_pointer_targets.length===0);
    }
    await checkLocalLinks(name);
    await page.screenshot({path:path.join(artifacts,name+'-desktop.png'),fullPage:true});
    if(name==='ontology'){
      const summary=page.locator('.concept-grid > details > summary').first();
      await summary.click();
      await page.screenshot({path:path.join(artifacts,'ontology-desktop-concept-open.png'),fullPage:true});
      await summary.click();
    }
    await page.setViewportSize({width:320,height:900});
    await assertReflow(name+'_reflow_320');
    report.pages[name].typography_mobile=await typographySnapshot(page);
    if(name==='amado')assertAmadoTypography(report.pages[name].typography_mobile,true);
    if(name==='home')check('home_h1_mobile_32',report.pages[name].typography_mobile.headings.h1[0].pixels===32);
    if(name==='home'){
      report.pages[name].problem_mobile_columns=await page.locator('.problem-grid').evaluate(el=>getComputedStyle(el).gridTemplateColumns.split(' ').length);
      check('home_problem_single_mobile_column',report.pages[name].problem_mobile_columns===1);
      check('home_example_single_mobile_column',await page.locator('#exemplo .steps').evaluate(el=>getComputedStyle(el).gridTemplateColumns.split(' ').length)===1);
    }
    await page.evaluate(()=>window.scrollTo({top:0,behavior:'instant'}));await settled();
    await page.screenshot({path:path.join(artifacts,name+'-mobile.png'),fullPage:true});
    await page.screenshot({path:path.join(artifacts,name+'-mobile-viewport.png')});
    if(name==='ontology'){
      const summary=page.locator('.concept-grid > details > summary').first();
      await summary.click();
      const scroll=page.locator('.uml-scroll');
      await scroll.focus();const oldScroll=await scroll.evaluate(el=>el.scrollLeft);await page.keyboard.press('ArrowRight');
      await page.waitForFunction(()=>document.querySelector('.uml-scroll').scrollLeft>0);
      check('ontology_svg_scroll_by_keyboard',await scroll.evaluate((el,old)=>el.scrollLeft>old&&el===document.activeElement,oldScroll));
      check('ontology_svg_scroll_named',Boolean(await scroll.getAttribute('aria-label'))&&await scroll.getAttribute('role')==='region');
      await page.locator('.uml-sequence').screenshot({path:path.join(artifacts,'ontology-sequence-mobile.png')});
      await assertReflow('ontology_open_concept_reflow_320');
      await page.screenshot({path:path.join(artifacts,'ontology-mobile-concept-open.png'),fullPage:true});
      await summary.click();
      await page.locator('details.sequence-text > summary').click();
      await assertReflow('ontology_text_equivalent_reflow_320');
      await page.locator('details.sequence-text').screenshot({path:path.join(artifacts,'ontology-sequence-text-mobile.png')});
    }
    {
      for(let n=0;n<25;n++)if(await page.locator('[data-font-increase]').isEnabled())await page.locator('[data-font-increase]').click();
      report.pages[name].typography_mobile_200=await typographySnapshot(page);
      report.pages[name].mobile_doubling=assertFixedViewportDoubling(report.pages[name].typography_mobile,report.pages[name].typography_mobile_200);
      check(name+'_mobile_actual_fonts_double_fixed_viewport',true);
      await page.evaluate(()=>window.scrollTo({top:0,behavior:'instant'}));await settled();
      await page.screenshot({path:path.join(artifacts,name+'-mobile-200.png')});
      await assertReflow(name+'_mobile_text_200_reflow');
      await page.locator('h1').screenshot({path:path.join(artifacts,name+'-mobile-200-title.png')});
      await page.locator('[data-font-reset]').click();
      if(name==='ontology')await page.locator('details.sequence-text > summary').click();
    }
    await page.emulateMedia({forcedColors:'active',reducedMotion:'reduce'});
    await assertReflow(name+'_forced_colors_reflow');
    check(name+'_forced_colors_and_reduced_motion',await page.evaluate(()=>matchMedia('(forced-colors:active)').matches&&matchMedia('(prefers-reduced-motion:reduce)').matches&&getComputedStyle(document.documentElement).scrollBehavior==='auto'));
    await page.screenshot({path:path.join(artifacts,name+'-forced-colors.png'),fullPage:true});
    check(name+'_no_persistent_storage',await page.evaluate(async()=>localStorage.length===0&&sessionStorage.length===0&&document.cookie===''&&(await indexedDB.databases()).length===0&&(await caches.keys()).length===0));
    await page.emulateMedia({forcedColors:'none'});
    {
      await page.locator('[data-font-increase]').click();await page.locator('[data-site-contrast]').click();await page.reload();
      if(name==='amado')await idle();
      check(name+'_preferences_not_restored',await page.locator('html').getAttribute('data-contrast')!=='high'&&await page.locator('html').evaluate(el=>parseFloat(getComputedStyle(el).fontSize))===16);
    }
  }
  check('distinct_page_titles',new Set(titles).size===3);
  const homeParagraphs=new Set(report.pages.home.long_main_paragraphs);
  report.repeated_main_paragraphs=report.pages.ontology.long_main_paragraphs.filter(text=>homeParagraphs.has(text));
  check('home_and_ontology_have_distinct_content',report.repeated_main_paragraphs.length===0);
  const sitemapResponse=await context.request.get(base+'sitemap.xml');
  const sitemap=await sitemapResponse.text();
  report.sitemap_urls=[...sitemap.matchAll(/<loc>\s*([^<]+)\s*<\/loc>/g)].map(x=>x[1]);
  check('sitemap_three_pages',sitemapResponse.status()===200&&['','ontologia/','amado/'].every(rel=>report.sitemap_urls.includes(publicBase+rel)));
  // A robots.txt under /MADO/ cannot govern the host. The project controls
  // the sitemap, not the root-level robots policy of the Pages host.
  report.robots={status:'NOT_ASSERTED',reason:'robots.txt deve estar na raiz da origem; o projeto está em /MADO/. Submissão do sitemap ao mecanismo de busca é uma etapa externa.'};
  check('no_external_requests_or_case_post',report.external_requests.length===0&&report.request_methods.every(x=>x==='GET'));
  check('no_javascript_errors',report.errors.length===0);
  assert.deepEqual(await coreInvariantAudit(root),report.core_invariants);
  check('editorial_preserves_semantic_and_runtime_files',true);
  report.change_verification={baseline:report.historical_baseline,
    change:'Documentação técnica compacta, diagrama de sequência UML em SVG com equivalente HTML recolhível e nome atualizado do link de navegação.',
    scope:'Verificações atuais de apresentação, dimensões, equivalente textual, teclado, ampliação e reflow. O baseline histórico não é contado como teste atual. O motor não recebe nova avaliação semântica nem humana.',
    unchanged_semantic_and_runtime_files:report.core_invariants.all_unchanged};
  report.completed=true;
}catch(error){report.completed=false;report.failure=error.message;console.error(error);process.exitCode=1;}
finally{
  report.finished_at_utc=new Date().toISOString();
  const reportName=process.env.AMADO_SITE_URL?'site-public-report.json':'site-presentation-report.json';
  const output=path.join(root,'evidence',reportName);
  await fs.writeFile(output,JSON.stringify(report,null,2)+'\n');
  await browser.close();await new Promise(resolve=>server.close(resolve));
  console.log(JSON.stringify({completed:report.completed,checks_passed:Object.values(report.checks).filter(x=>x===true).length,checks_total:Object.keys(report.checks).length,report:'evidence/'+reportName,failure:report.failure}));
}
