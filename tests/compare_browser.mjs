// Semantic parity of independently executed native and Pyodide decisions.
// This comparison is intentionally stricter than a status/configuration count.
import fs from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import crypto from 'node:crypto';

const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const nativePath=path.join(root,'evidence/native-cases.json');
const browserPath=path.join(root,'tests/.artifacts/browser/decisions.json');
const [native,browser]=await Promise.all([nativePath,browserPath].map(async file=>JSON.parse(await fs.readFile(file,'utf8'))));
const queries={};
for (const filename of await fs.readdir(path.join(root,'queries'))) {
  if (!filename.endsWith('.rq')) continue;
  const query=await fs.readFile(path.join(root,'queries',filename),'utf8');
  queries[filename.slice(0,-3)]=new Set([...query.matchAll(/GROUP_CONCAT\([\s\S]*?\)\s+AS\s+\?(\w+)/gi)].map(match=>match[1]));
}
const generatedID=s=>s
  .replace(/CTX-CASO-[A-F0-9]+/g,'CTX-CASO-DYNAMIC')
  .replace(/D-GERADA-[A-F0-9]+/g,'D-GERADA-DYNAMIC')
  .replace(/PART-CASO-(\d+)-[A-F0-9]+/g,'PART-CASO-$1-DYNAMIC');
function canonicalValue(value,trail=[]) {
  if (typeof value==='string') {
    const result=generatedID(value);
    if ((trail[0]==='query_results' && queries[trail[1]]?.has(trail.at(-1))) || (trail[0]==='traceability' && trail[1]==='semantic_retrieval' && trail.at(-1)==='correspondences')) {
      return result.split(' | ').sort().join(' | ');
    }
    return result;
  }
  if (Array.isArray(value)) {
    const result=value.map((row,index)=>canonicalValue(row,[...trail,index]));
    // SPARQL result sets and graph topology have no presentation sequence.
    // Decision configurations, practical steps and all other arrays keep order.
    const key=String(trail.at(-1));
    const relationalList=key.endsWith('_ids') || ['articulacoes','trajetoria','semantic_retrieval','articulations_used','retrieval','retrieval_witnesses','checks','check_ids','witness_ids'].includes(key);
    if (relationalList || trail[0]==='query_results' || (trail[0]==='trace_graph' && ['nodes','edges'].includes(trail[1]))) {
      result.sort((a,b)=>JSON.stringify(a).localeCompare(JSON.stringify(b),'en'));
    }
    return result;
  }
  if (value && typeof value==='object') return Object.fromEntries(Object.keys(value).sort().filter(key=>!(trail.length===0 && key==='executed_at')).map(key=>[generatedID(key),canonicalValue(value[key],[...trail,key])]));
  return value;
}
function canonical(value) {
  // CHECK identities hash their actual predicate payload, which can contain
  // a transient context ID. Normalize the predicate, not merely erase the ID.
  const mapping=new Map((value.execution_evidence?.checks||[]).map(row=>{
    const {id,...predicate}=row;
    return [id,'CHECK-SEMANTIC-'+crypto.createHash('sha256').update(JSON.stringify(canonicalValue(predicate))).digest('hex')];
  }));
  const replace=item=>{
    if(typeof item==='string')return mapping.get(item)||item;
    if(Array.isArray(item))return item.map(replace);
    if(item&&typeof item==='object')return Object.fromEntries(Object.entries(item).map(([k,v])=>[k,replace(v)]));
    return item;
  };
  return canonicalValue(replace(value));
}
function differences(a,b,trail='$',result=[]) {
  if (result.length>=30 || Object.is(a,b)) return result;
  if (a && b && typeof a==='object' && typeof b==='object' && Array.isArray(a)===Array.isArray(b)) {
    if (Array.isArray(a) && a.length!==b.length) result.push({path:trail+'.length',native:a.length,browser:b.length});
    for (const key of new Set([...Object.keys(a),...Object.keys(b)])) differences(a[key],b[key],`${trail}.${key}`,result);
  } else result.push({path:trail,native:a,browser:b});
  return result;
}
const digest=value=>crypto.createHash('sha256').update(JSON.stringify(value)).digest('hex');
const report={
  type:'SYNTHETIC_NATIVE_BROWSER_PARITY_NOT_HUMAN_EVALUATION',
  build:JSON.parse(await fs.readFile(path.join(root,'web/amado/manifest.json'),'utf8')),
  executed_at:new Date().toISOString(),
  normalization:[
    'Somente horário de execução e sufixos aleatórios de contexto, participante e decisão são desconsiderados.',
    'Linhas SPARQL e topologia do grafo são comparadas como conjuntos ordenados canonicamente, preservando duplicatas.',
    'A ordem interna de GROUP_CONCAT é normalizada apenas nos campos declarados pelas consultas.',
    'Listas de identificadores, articulações, trajetória e correspondências de recuperação são relações sem ordem e são normalizadas.',
    'A ordem das configurações, passos práticos e demais listas é preservada.'
    ,'Identidades CHECK são recalculadas a partir do predicado normalizado; estado, condições e valores observados permanecem comparados.'
  ],
  native_sha256:crypto.createHash('sha256').update(await fs.readFile(nativePath)).digest('hex'),
  browser_sha256:crypto.createHash('sha256').update(await fs.readFile(browserPath)).digest('hex'),
  cases:{}, missing_in_browser:Object.keys(native).filter(key=>!(key in browser)),
  unexpected_in_browser:Object.keys(browser).filter(key=>!(key in native))
};
report.test_sha256=crypto.createHash('sha256').update(await fs.readFile(fileURLToPath(import.meta.url))).digest('hex');
const baseline=canonical(native.principal);
const reorder=structuredClone(native.principal);
reorder.decision.configuracao_modal.reverse();
const change=structuredClone(native.principal);
change.decision.configuracao_modal[0].funcao='FUNÇÃO ALTERADA NO TESTE DO COMPARADOR';
const relationOrder=structuredClone(native.principal);
relationOrder.decision.knowledge_ids.reverse();
const alteredCheck=structuredClone(native.principal);
alteredCheck.execution_evidence.checks[0].outcome='FAIL';
const alteredObservation=structuredClone(native.principal);
alteredObservation.execution_evidence.checks[0].observed_ids=['CONDITION-NOT-IN-THE-EXECUTION'];
report.comparator_self_checks={
  rejects_changed_configuration_order:differences(baseline,canonical(reorder)).length>0,
  rejects_changed_modal_function:differences(baseline,canonical(change)).length>0,
  accepts_unordered_knowledge_ids:differences(baseline,canonical(relationOrder)).length===0,
  rejects_changed_check_outcome:differences(baseline,canonical(alteredCheck)).length>0,
  rejects_changed_check_observation:differences(baseline,canonical(alteredObservation)).length>0
};
for (const id of Object.keys(native).filter(key=>key in browser)) {
  const left=canonical(native[id]), right=canonical(browser[id]);
  const mismatch=differences(left,right);
  report.cases[id]={equal:mismatch.length===0,status:native[id].decision.status,configurations:native[id].decision.component_ids,query_rows:native[id].query_summary,native_canonical_sha256:digest(left),browser_canonical_sha256:digest(right),differences:mismatch};
}
report.passed=report.missing_in_browser.length===0 && report.unexpected_in_browser.length===0 && Object.values(report.cases).every(row=>row.equal) && Object.values(report.comparator_self_checks).every(Boolean);
await fs.writeFile(path.join(root,'evidence/parity-report.json'),JSON.stringify(report,null,2));
console.log(JSON.stringify({passed:report.passed,cases:Object.fromEntries(Object.entries(report.cases).map(([id,row])=>[id,{equal:row.equal,differences:row.differences.slice(0,2)}])),missing:report.missing_in_browser},null,2));
if (!report.passed) process.exitCode=1;
