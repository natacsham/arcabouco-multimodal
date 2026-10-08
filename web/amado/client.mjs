// This client holds only pending operations; no case history or persistent store.
let worker, sequence = 0;
const pending = new Map();

function discard(message) {
  worker?.terminate(); worker = null;
  for (const item of pending.values()) { clearTimeout(item.timer); item.reject(new Error(message)); }
  pending.clear();
}
function ensureWorker() {
  if (worker) return;
  worker = new Worker(new URL('./worker.mjs',import.meta.url),{type:'module'});
  worker.onmessage = ({data}) => {
    if (data.type === 'progress') { window.dispatchEvent(new CustomEvent('amado-progress',{detail:data.message})); return; }
    const item = pending.get(data.id);
    if (!item) return;
    pending.delete(data.id); clearTimeout(item.timer);
    if (data.type === 'error') item.reject(new Error(data.error)); else item.resolve(data.data);
  };
  worker.onerror = () => { discard('O processamento foi interrompido. Use Limpar caso e reiniciar para tentar novamente.'); };
}
export function request(operation,payload={}) {
  ensureWorker();
  const id = ++sequence;
  return new Promise((resolve,reject) => {
    const timer = setTimeout(() => discard('O processamento ultrapassou três minutos e foi encerrado. Use Limpar caso e reiniciar; nenhuma resposta anterior substituiu esta execução.'),180000);
    pending.set(id,{resolve,reject,timer});
    worker.postMessage({id,operation,...payload});
  });
}
export function restart() { discard('Operação cancelada: o caso temporário foi descartado.'); }
window.addEventListener('pagehide',() => discard('Página encerrada.'));
