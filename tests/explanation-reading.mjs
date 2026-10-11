// Presentation-only fidelity checks. These fixtures are technical executions,
// not participant records. No base, pattern or runtime decision is modified.
import fs from 'node:fs/promises';
import path from 'node:path';
import assert from 'node:assert/strict';
import crypto from 'node:crypto';
import {execFileSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';

const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const baseline='73013190f26cf8806e7f647dbb3fa36a8c07a3c3';
const source=await fs.readFile(path.join(root,'web/explanation.js'),'utf8');
const {projectConfiguration}=await import('data:text/javascript;base64,'+Buffer.from(source).toString('base64'));
const cases=JSON.parse(await fs.readFile(path.join(root,'evidence/native-cases.json'),'utf8'));
const report={type:'SYNTHETIC_PRESENTATION_FIDELITY_NOT_HUMAN_EVALUATION',baseline_commit:baseline,executed_at:new Date().toISOString(),checks:{},limits:['No reader comprehension or educational outcome is measured.']};
const check=(name,value)=>{report.checks[name]=Boolean(value);assert(value,name);};
const main=cases.principal;
const config=main.explanation.configurations.find(c=>c.component_id==='PAD-ORGANIZAR-CONTEUDO-PERSISTENTE');
const before=JSON.stringify(main);
const projection=projectConfiguration(main,config);
check('projection_does_not_mutate_execution',before===JSON.stringify(main));
check('persistent_structure_adds_foundation_not_choice',projection.effect.kind==='EXPANDED_FOUNDATION');
check('exact_added_support_pairs_preserved',JSON.stringify(projection.effect.addedSupportPairs)===JSON.stringify(main.articulation_comparison.evidence_delta.find(c=>c.component_id===config.component_id).added_support_pairs));
check('required_role_check_included',projection.checks.some(c=>c.rule_id==='required_roles'&&c.outcome==='PASS'));
check('partial_documentary_support_preserved',projection.foundationIncomplete.length>0);
check('only_mobilized_articulations_in_primary_construction',projection.construction.mobilized.every(a=>a.mobilized_in_execution===true&&a.nivel_confirmacao!=='NAO_CONFIRMADA'));
check('unconfirmed_relation_separated',projection.construction.unconfirmed.some(a=>a.id==='ART-TESTE-NAO-CONFIRMADA'));
check('historical_relations_separated',projection.construction.historical.some(a=>a.id==='ART-TRJ-01'&&a.mobilized_in_execution===false));
check('supports_keep_exact_knowledge_pairs',JSON.stringify(projection.supports)===JSON.stringify(config.application.supports));
const video=main.explanation.configurations.find(c=>c.component_id==='PAD-VIDEO-PROCESSO');
check('new_choice_effect_not_conflated_with_foundation',projectConfiguration(main,video).effect.kind==='NEW_CHOICE');
const withoutComparison=structuredClone(main);delete withoutComparison.articulation_comparison;
check('missing_comparison_is_not_approval',projectConfiguration(withoutComparison,config).effect.kind==='NOT_EXECUTED');
const recordedChecks=new Set(main.execution_evidence.checks.map(c=>c.id));
check('all_projected_checks_were_recorded',projection.checks.every(c=>recordedChecks.has(c.id)));
const retrievalGroups=Object.values(cases).flatMap(result=>(result.explanation?.configurations||[]).flatMap(c=>projectConfiguration(result,c).retrievalGroups));
check('excluded_knowledge_not_recast_as_used',retrievalGroups.every(group=>!group.authorizations.includes('EXCLUIDO')));
check('conditional_use_preserves_its_state',retrievalGroups.some(group=>group.authorizations.includes('CONDICIONAL')));
for(const [name,result] of Object.entries(cases)){
  for(const c of result.explanation?.configurations||[]){
    const value=projectConfiguration(result,c);
    check(name+'_'+c.component_id+'_identity_preserved',value.componentId===c.component_id);
    check(name+'_'+c.component_id+'_exact_supports_preserved',JSON.stringify(value.supports)===JSON.stringify(c.application.supports));
  }
}
// The V2 bridge/worker and bundle now legitimately add a separate operation.
// This assertion remains about the existing decision model and presentation.
// Exact bundle checks and composition parity are covered by their own tests.
const protectedFiles=execFileSync('git',['ls-tree','-r','--name-only',baseline,'--','engine.py','execution_trace.py','data','ontology','queries','shapes','web/amado/engine.py','web/amado/client.mjs'],{cwd:root}).toString().trim().split(/\r?\n/).filter(Boolean);
report.integration_changes_not_claimed_unchanged=['web/amado/bridge.py','web/amado/worker.mjs','web/amado/assets/base.zip'];
report.protected_files=[];
const sha=data=>crypto.createHash('sha256').update(data).digest('hex');
for(const file of protectedFiles){
  const old=execFileSync('git',['show',baseline+':'+file],{cwd:root,maxBuffer:64*1024*1024});
  const current=await fs.readFile(path.join(root,file));
  report.protected_files.push({file,baseline_sha256:sha(old),current_sha256:sha(current),unchanged:sha(old)===sha(current)});
}
check('ontology_base_queries_rules_and_engine_unchanged',report.protected_files.every(row=>row.unchanged));
report.passed=Object.values(report.checks).every(Boolean);
report.test_sha256=sha(await fs.readFile(fileURLToPath(import.meta.url)));
report.presenter_sha256=sha(Buffer.from(source));
const reportFlag=process.argv.indexOf('--report');
const reportPath=path.resolve(root,reportFlag>=0?process.argv[reportFlag+1]:'tests/.artifacts/explanation-reading.json');
assert(reportPath.startsWith(root+path.sep),'Report must stay inside the project.');
await fs.mkdir(path.dirname(reportPath),{recursive:true});
await fs.writeFile(reportPath,JSON.stringify(report,null,2));
console.log(JSON.stringify({passed:report.passed,checks:Object.keys(report.checks).length,protected_files:report.protected_files.length},null,2));
