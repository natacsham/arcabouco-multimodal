// Transport tests use the actual worker/client modules with deterministic runtime
// boundaries, not delays, percentages or simulated source downloads.
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {webcrypto} from 'node:crypto';
import vm from 'node:vm';

const workers = [], windowEvents = [];
globalThis.window = {addEventListener(){},dispatchEvent(event){windowEvents.push(event);}};
globalThis.CustomEvent = class {constructor(type, options){this.type=type;this.detail=options.detail;}};
globalThis.Worker = class {
  constructor(){this.sent=[];workers.push(this);}
  postMessage(value){this.sent.push(value);}
  terminate(){this.terminated=true;}
  emit(value){this.onmessage({data:value});}
};
const client = await import('../web/amado/client.mjs');
const received = [];
const resultPromise = client.request('generate',{}, {onProgress:event=>received.push(event)});
const firstWorker = workers.at(-1), first = firstWorker.sent.at(-1);
firstWorker.emit({id:first.id+100,operation:'generate',type:'progress',stage:'retrieval',state:'running',message:'stale'});
firstWorker.emit({id:first.id,operation:'analyze',type:'progress',stage:'retrieval',state:'running',message:'wrong operation'});
assert.equal(received.length,0);
const event = {id:first.id,operation:'generate',type:'progress',stage:'retrieval',state:'running',message:'Consulta em curso'};
firstWorker.emit(event);
assert.deepEqual(received,[event]);
assert.equal(windowEvents.at(-1).detail,'Consulta em curso'); // older view contract
firstWorker.emit({id:first.id,type:'result',data:{exact:'result'}});
assert.deepEqual(await resultPromise,{exact:'result'});
firstWorker.emit({...event,state:'completed'});
assert.equal(received.length,1,'Finished requests cannot report later progress');

const cancelled = [], secondPromise = client.request('compose',{}, {onProgress:event=>cancelled.push(event)});
const second = firstWorker.sent.at(-1);
firstWorker.emit({...event,id:second.id,operation:'compose',stage:'composition'});
const rejected = assert.rejects(secondPromise,/cancelada/);
client.restart();
await rejected;
assert.equal(cancelled.at(-1).state,'cancelled');
assert.equal(firstWorker.terminated,true);
const thirdPromise = client.request('initialize');
const newWorker = workers.at(-1), third = newWorker.sent.at(-1);
firstWorker.emit({...event,id:third.id,operation:'initialize'});
assert.equal(cancelled.length,2,'Old worker cannot update a new request');
firstWorker.onerror();
assert.equal(newWorker.terminated,undefined,'Old worker failure cannot terminate replacement');
newWorker.emit({id:third.id,type:'result',data:{ready:true}});
await thirdPromise;
const observerFailure = client.request('generate',{}, {onProgress(){throw new Error('presentation error');}});
const fourth = newWorker.sent.at(-1);
newWorker.emit({...event,id:fourth.id});
newWorker.emit({id:fourth.id,type:'result',data:{unchanged:true}});
assert.deepEqual(await observerFailure,{unchanged:true});
client.restart();

const source = (await readFile(new URL('../web/amado/worker.mjs',import.meta.url),'utf8'))
  .replace("import { loadPyodide } from './runtime/pyodide.mjs';",'')
  .replaceAll('import.meta.url',JSON.stringify(new URL('../web/amado/worker.mjs',import.meta.url).href));
async function runtime({badHash=false, fail=false}={}) {
  const output=[], globals=new Map(), operations=[];
  const bytes=new TextEncoder().encode('public package'), digest=Buffer.from(await webcrypto.subtle.digest('SHA-256',bytes)).toString('hex');
  const manifest={version:'test',pyodide_version:'test',base_zip_sha256:badHash?'wrong':digest,core_sha256:digest,bridge_sha256:digest};
  const fakePyodide={FS:{mkdirTree(){},writeFile(){}},globals:{set:(key,value)=>globals.set(key,value),delete:key=>globals.delete(key)},
    async runPythonAsync(code){
      if(!code.includes('dispatch_json')) return JSON.stringify({triples:3});
      const request=JSON.parse(globals.get('_request_json'));
      operations.push(request.operation);
      const emit=globals.get('_emit_progress_json');
      emit(JSON.stringify({stage:'retrieval',state:'running',message:'Recuperando registros'}));
      emit(JSON.stringify({stage:'retrieval',state:'completed',message:'Registros recuperados'}));
      emit(JSON.stringify({stage:'verification',state:'running',message:'Conferindo condições'}));
      if(fail) throw new Error('ValueError: Falha controlada');
      emit(JSON.stringify({stage:'verification',state:'completed',message:'Condições conferidas'}));
      emit(JSON.stringify({stage:'composition',state:'running',message:'Compondo'}));
      emit(JSON.stringify({stage:'composition',state:'completed',message:'Saída organizada'}));
      return JSON.stringify({operation:request.operation,unchanged:true});
    }};
  const context={URL,Uint8Array,crypto:webcrypto,postMessage:value=>output.push(value),self:{},
    fetch:async url=>({ok:true,json:async()=>manifest,arrayBuffer:async()=>bytes.buffer}),
    loadPyodide:async()=>fakePyodide};
  vm.runInNewContext(source,context);
  async function send(id,operation){
    context.self.onmessage({data:{id,operation}});
    // Wait for the queued operation itself, not an arbitrary timer.
    await vm.runInNewContext('queue',context);
  }
  return {output,globals,operations,send};
}
const success=await runtime();
await success.send(7,'generate');
const progress=success.output.filter(row=>row.type==='progress');
assert(progress.every(row=>row.id===7 && row.operation==='generate'));
assert.deepEqual(progress.filter(row=>row.state==='completed').map(row=>row.stage),['initialization','retrieval','verification','composition']);
assert.equal(progress.some(row=>row.stage==='presentation'),false,'Worker cannot report DOM rendering');
assert.equal(JSON.stringify(progress).includes('ABNT'),false);
assert.deepEqual(JSON.parse(JSON.stringify(success.output.at(-1))),{id:7,type:'result',data:{operation:'generate',unchanged:true}});
assert.equal(success.globals.size,0,'Transient callback and request are cleared');
const previousCount=success.output.length;
await success.send(8,'generate');
assert(success.output.slice(previousCount).every(row=>row.id===8));
assert.equal(success.output.slice(previousCount).some(row=>row.stage==='initialization'),false,'Warm calls do not pretend to reload base');

const failure=await runtime({fail:true});
await failure.send(9,'generate');
assert.equal(failure.output.at(-1).type,'error');
assert.equal(failure.output.at(-2).stage,'verification');
assert.equal(failure.output.at(-2).state,'failed');
assert.equal(failure.output.some(row=>row.stage==='composition'),false);
assert.equal(failure.globals.size,0);
const mismatch=await runtime({badHash:true});
await mismatch.send(10,'generate');
assert.equal(mismatch.output.at(-1).type,'error');
assert.equal(mismatch.output.at(-2).stage,'initialization');
assert.equal(mismatch.output.at(-2).state,'failed');
assert.equal(mismatch.operations.length,0,'Hash mismatch prevents any engine consultation');
console.log('PASS: correlated real-phase transport, cold/warm load, cancellation, stale events, failure and unchanged result contract.');
