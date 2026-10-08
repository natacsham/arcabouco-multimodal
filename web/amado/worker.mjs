import { loadPyodide } from './runtime/pyodide.mjs';

let pyodide, ready;
let queue = Promise.resolve();
const allowed = new Set(['initialize','catalog','start','update','analyze','confirm','generate','clear']);

async function bytes(relative) {
  const response = await fetch(new URL(relative, import.meta.url));
  if (!response.ok) throw new Error(`Arquivo necessário indisponível (${response.status}): ${relative}`);
  return new Uint8Array(await response.arrayBuffer());
}
async function sha256(value) {
  const digest = await crypto.subtle.digest('SHA-256', value);
  return Array.from(new Uint8Array(digest), b => b.toString(16).padStart(2, '0')).join('');
}
async function initialize() {
  const response = await fetch(new URL('./manifest.json', import.meta.url), {cache:'no-store'});
  if (!response.ok) throw new Error('Não foi possível conferir a versão do AMADO. Tente reiniciar.');
  const manifest = await response.json();
  postMessage({type:'progress',message:'Carregando Python no navegador. A primeira carga pode demorar…'});
  pyodide = await loadPyodide({indexURL:new URL('./runtime/',import.meta.url).href});
  const [base, core, bridge] = await Promise.all([bytes('./assets/base.zip'),bytes('./engine.py'),bytes('./bridge.py')]);
  for (const [value, expected] of [[base,manifest.base_zip_sha256],[core,manifest.core_sha256],[bridge,manifest.bridge_sha256]]) {
    if (!expected || await sha256(value) !== expected) throw new Error('A versão dos arquivos não corresponde ao manifesto. Limpe e reinicie; nenhuma orientação será gerada com arquivos divergentes.');
  }
  pyodide.FS.mkdirTree('/app');
  pyodide.FS.writeFile('/app/base.zip',base);
  pyodide.FS.writeFile('/app/engine.py',core);
  pyodide.FS.writeFile('/app/bridge.py',bridge);
  postMessage({type:'progress',message:'Conferindo a base RDF e carregando as consultas…'});
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
  return {...JSON.parse(raw),version:manifest.version,pyodide:manifest.pyodide_version};
}
self.onmessage = ({data}) => {
  queue = queue.then(async () => {
    const {id,operation} = data;
    try {
      if (!Number.isInteger(id) || !allowed.has(operation)) throw new Error('Operação não disponível.');
      if (!ready) ready = initialize();
      const runtime = await ready;
      if (operation === 'initialize') { postMessage({id,type:'result',data:runtime}); return; }
      pyodide.globals.set('_request_json',JSON.stringify(data));
      let raw;
      try { raw = await pyodide.runPythonAsync('bridge.dispatch_json(_request_json)'); }
      finally { pyodide.globals.delete('_request_json'); }
      postMessage({id,type:'result',data:JSON.parse(raw)});
    } catch (error) {
      // Only send the final explanatory exception, not a stack or the case text.
      const lines = String(error?.message || error).trim().split('\n');
      postMessage({id,type:'error',error:lines.at(-1).replace(/^(ValueError|RuntimeError|Error):\s*/, '')});
    }
  });
};
