import assert from 'node:assert/strict';
import {legacyEditor,legacyRevision,legacyQuestions,legacyAnswer,compositionEditor,compositionRevision,usedSourceRecords,participantName} from '../web/amado/intake.mjs';
const item=(id,label=id)=>({id,label,curated:true});
const catalog={concepts:{TAREFA:[item('T1','Acessar conteúdo')],AMBIENTE:[item('A1','Sala de aula')],
  PAPEL_NO_CONTEXTO:[item('P1','Pessoa apoiada'),item('P2','Mediador')],MODALIDADE:[item('M1','Texto'),item('M2','Áudio')],
  CARACTERISTICA_PESSOA:[item('C1','Acesso não visual')],RECURSO_DIGITAL:[item('D1','Formulário')],RECURSO_DISPONIVEL:[item('R1','Computador'),item('R2','Projetor')]}};
const current={context:{texto_curto:'A pessoa precisa preencher um formulário na sala de aula.',objetivo:'Enviar a resposta',
  requester_relation:'support',requester_participation_id:null,raw:{tarefas:['T1'],ambientes:['A1'],recursos_digitais:[],recursos_disponiveis:['R1'],recursos_impedidos:[]}},
  participations:[{id:'P-A',label:'Pessoa apoiada',papel_id:'P1',caracteristica_ids:['C1'],modalidade_ids:['M1'],recurso_operado_ids:['R1']}],
  questions:[{field:'requester_relation',type:'single',question:'Como você participa?',options:[{id:'self',label:'Sou eu'},{id:'support',label:'Acompanho'}]}]};
const original=structuredClone(current),rows=legacyEditor(current,catalog);
assert(rows.find(row=>row.key==='recursos_digitais').options.some(option=>option.id==='D1'),'Missing fields remain editable');
assert.deepEqual(rows.find(row=>row.key==='ambientes').value,['A1'],'Environment already reported is present');
const revised=legacyRevision(current,catalog,{ambientes:[],recursos_digitais:['D1'],recursos_disponiveis:['R2'],
  'person:P-A:modalidade_ids':['M2'],'person:P-A:recurso_operado_ids':[],requester_relation:'seek_guidance'});
assert.deepEqual(revised.ambientes,[],'Unchecking removes a previous answer rather than merging it');
assert.deepEqual(revised.recursos_disponiveis,['R2']);
assert.deepEqual(revised.participations[0].modalidade_ids,['M2']);
assert.deepEqual(revised.participations[0].recurso_operado_ids,[]);
assert.equal(revised.descricao_do_contexto,current.context.texto_curto,'Correction does not rewrite or reparse the narrative');
assert.equal(revised.requester_relation,'seek_guidance');
assert.equal(revised.mapping_confirmed,false);assert.equal(revised.transfer_confirmed,false);
assert.deepEqual(current,original,'Editor updates remain immutable');
const removed=legacyRevision({...current,context:{...current.context,requester_participation_id:'P-A'}},catalog,{'remove:P-A':true});
assert.deepEqual(removed.participations,[],'Incorrectly identified participant can be removed');
assert.equal(removed.requester_participation_id,'','Link to removed participant must be cleared');
assert.deepEqual(current,original,'Removing in a draft does not alter prior context');
const pluralCurrent=structuredClone(current);pluralCurrent.participations[0]={...pluralCurrent.participations[0],label:'Pessoas apoiadas',grupo_rotulo:'Pessoas',quantidade:null};
assert.equal(participantName(pluralCurrent.participations[0]),'Pessoas apoiadas','An uncounted group retains its plural label without inventing a count');
const pluralRevision=legacyRevision(pluralCurrent,catalog,{});
assert.equal(pluralRevision.participations[0].quantidade,null,'Editor preserves unknown group size');
assert.equal(pluralRevision.participations[0].grupo_rotulo,'Pessoas');
const legacyCatalog=structuredClone(catalog);legacyCatalog.concepts.CARACTERISTICA_PESSOA.push({...item('C-LEGACY','Diversidade de perfis'),categoria:'ESCOPO_DE_PUBLICO'});
const legacyCurrent=structuredClone(current);legacyCurrent.context.raw.caracteristicas_pessoa=['C-LEGACY'];
const visibleLegacy=legacyEditor(legacyCurrent,legacyCatalog).find(row=>row.key==='caracteristicas_pessoa');
assert(visibleLegacy.options.some(row=>row.id==='C-LEGACY'),'Previously selected legacy descriptor is visible for deliberate editing');
assert.deepEqual(legacyRevision(legacyCurrent,legacyCatalog,{caracteristicas_pessoa:visibleLegacy.value}).caracteristicas_pessoa,['C-LEGACY']);
assert(!legacyEditor(current,legacyCatalog).find(row=>row.key==='caracteristicas_pessoa').options.some(row=>row.id==='C-LEGACY'),'Legacy descriptors are not added as new public choices');
assert.throws(()=>legacyRevision(current,catalog,{recursos_disponiveis:['R1'],recursos_impedidos:['R1']}),/disponível.*impedido/);
const roleQuestion=legacyQuestions(current,catalog)[0];
assert.equal(roleQuestion.type,'single');assert.equal(roleQuestion.options[0].id,'self');
assert.equal(legacyAnswer(current,roleQuestion,'self').requester_relation,'self');
assert(!Array.isArray(legacyAnswer(current,roleQuestion,'self').requester_relation));
const compCatalog={tasks:[item('T1','Escrever')],facts:[item('F1','Pode corrigir')],resources:[item('R1','Teclado')]};
const draft={task:'T1',confirmed:true,facts:{F1:null},resources:{R1:true}};
assert(compositionEditor(draft,compCatalog).some(row=>row.key==='facts:F1'&&row.value==='unknown'));
const compRevised=compositionRevision(draft,compCatalog,{'facts:F1':'true','resources:R1':'unknown'});
assert.equal(compRevised.facts.F1,true);assert.equal(compRevised.resources.R1,null);assert.equal(compRevised.confirmed,false);
assert.equal(draft.confirmed,true);
const evidence={execution_evidence:{entities:{S1:{title:'WCAG 2.2',url:'https://example.org/root'},S2:{title:'Not used'}}},
  explanation:{configurations:[{component_id:'CFG1',application:{supports:[{criterion_id:'CA1',origins:[{id:'ORI1',fonte_id:'S1',
    document_url:'https://example.org/root#section',document_paraphrase:'Preserve o significado.',localizacao_publica:'1.1.1',status_localizacao:'SECAO_ORIGINAL_CONFERIDA'}]}]}}]}};
const sources=usedSourceRecords(evidence);
assert.equal(sources.length,1);assert.equal(sources[0].title,'WCAG 2.2');assert.equal(sources[0].url,'https://example.org/root#section');
assert.equal(sources[0].statement,'Preserve o significado.');assert.equal(sources[0].componentId,'CFG1');assert.equal(sources[0].criterionId,'CA1');
assert(!sources.some(row=>row.sourceId==='S2'),'Catalogue presence is not usage');
console.log('Review input: replacement, unknown recovery, people scope, no narrative reparse, reconfirmation and exact source origins verified.');
