import { loadPyodide } from './runtime/pyodide.mjs';

let pyodide, ready;
let queue = Promise.resolve();
const allowed = new Set(['initialize','catalog','start','update','analyze','confirm','generate','clear','catalog_composition','compose']);

async function bytes(relative) {
  const response = await fetch(new URL(relative, import.meta.url));
  if (!response.ok) throw new Error(`Arquivo necessário indisponível (${response.status}): ${relative}`);
  return new Uint8Array(await response.arrayBuffer());
}
async function sha256(value) {
  const digest = await crypto.subtle.digest('SHA-256', value);
  return Array.from(new Uint8Array(digest), b => b.toString(16).padStart(2, '0')).join('');
}
async function initialize(progress) {
  progress({stage:'initialization',state:'running',message:'Carregando e conferindo a versão publicada da base…'});
  const response = await fetch(new URL('./manifest.json', import.meta.url), {cache:'no-store'});
  if (!response.ok) throw new Error('Não foi possível conferir a versão do AMADO. Tente reiniciar.');
  const manifest = await response.json();
  progress({stage:'initialization',state:'running',message:'Carregando o ambiente de consulta no navegador…'});
  pyodide = await loadPyodide({indexURL:new URL('./runtime/',import.meta.url).href});
  const [base, core, bridge] = await Promise.all([bytes('./assets/base.zip'),bytes('./engine.py'),bytes('./bridge.py')]);
  for (const [value, expected] of [[base,manifest.base_zip_sha256],[core,manifest.core_sha256],[bridge,manifest.bridge_sha256]]) {
    if (!expected || await sha256(value) !== expected) throw new Error('A versão dos arquivos não corresponde ao manifesto. Limpe e reinicie; nenhuma orientação será gerada com arquivos divergentes.');
  }
  pyodide.FS.mkdirTree('/app');
  pyodide.FS.writeFile('/app/base.zip',base);
  pyodide.FS.writeFile('/app/engine.py',core);
  pyodide.FS.writeFile('/app/bridge.py',bridge);
  progress({stage:'initialization',state:'running',message:'Arquivos conferidos. Carregando a base RDF e as consultas…'});
  const raw = await pyodide.runPythonAsync(`
import sys, zipfile, json
sys.dont_write_bytecode = True
with zipfile.ZipFile('/app/base.zip') as package:
    for entry in package.infolist():
        if entry.filename.startswith('/') or '..' in entry.filename.split('/'):
            raise ValueError('Caminho inválido no pacote da base.')
    package.extractall('/app')
sys.path.insert(0, '/app')
import bridge
json.dumps(bridge.initialize())
`);
  const runtime = {...JSON.parse(raw),version:manifest.version,pyodide:manifest.pyodide_version};
  progress({stage:'initialization',state:'completed',message:'Versão conferida e base pronta para consulta.'});
  return runtime;
}
self.onmessage = ({data}) => {
  queue = queue.then(async () => {
    const {id,operation} = data;
    let lastProgress;
    const progress = event => {
      if (!event || !['initialization','retrieval','verification','composition'].includes(event.stage)
          || !['running','completed'].includes(event.state) || typeof event.message !== 'string') return;
      lastProgress = {id,operation,type:'progress',stage:event.stage,state:event.state,message:event.message};
      postMessage(lastProgress);
    };
    try {
      if (!Number.isInteger(id) || !allowed.has(operation)) throw new Error('Operação não disponível.');
      if (!ready) ready = initialize(progress);
      const runtime = await ready;
      if (operation === 'initialize') { postMessage({id,type:'result',data:runtime}); return; }
      pyodide.globals.set('_request_json',JSON.stringify(data));
      pyodide.globals.set('_emit_progress_json', raw => progress(JSON.parse(raw)));
      let raw;
      try { raw = await pyodide.runPythonAsync('bridge.dispatch_json(_request_json, lambda event: _emit_progress_json(json.dumps(event, ensure_ascii=False)))'); }
      finally {
        pyodide.globals.delete('_request_json');
        pyodide.globals.delete('_emit_progress_json');
      }
      postMessage({id,type:'result',data:JSON.parse(raw)});
    } catch (error) {
      // Only send the final explanatory exception, not a stack or the case text.
      const lines = String(error?.message || error).trim().split('\n');
      if (lastProgress?.state === 'running') postMessage({...lastProgress,state:'failed',message:'Esta etapa foi interrompida. Nenhuma conclusão foi presumida.'});
      postMessage({id,type:'error',error:lines.at(-1).replace(/^(ValueError|RuntimeError|Error):\s*/, '')});
    }
  });
};
