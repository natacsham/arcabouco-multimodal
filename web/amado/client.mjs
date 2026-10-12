// This client holds only pending operations; no case history or persistent store.
let worker, sequence = 0;
const pending = new Map();

function publishProgress(item, data) {
  // Observers are presentation only: they cannot change or interrupt the result.
  item.lastProgress = data;
  try { item.onProgress?.(data); } catch { /* Keep the operation independent of its view. */ }
  window.dispatchEvent(new CustomEvent('amado-progress',{detail:data.message}));
}
function discard(message, state = 'cancelled') {
  worker?.terminate(); worker = null;
  const discarded = [...pending.entries()];
  pending.clear();
  for (const [id,item] of discarded) {
    clearTimeout(item.timer);
    if (item.lastProgress) publishProgress(item,{...item.lastProgress,id,state,message});
    item.reject(new Error(message));
  }
}
function ensureWorker() {
  if (worker) return;
  const activeWorker = new Worker(new URL('./worker.mjs',import.meta.url),{type:'module'});
  worker = activeWorker;
  activeWorker.onmessage = ({data}) => {
    if (worker !== activeWorker) return;
    const item = pending.get(data.id);
    if (!item) return;
    if (data.type === 'progress') {
      if (data.operation === item.operation) publishProgress(item,data);
      return;
    }
    pending.delete(data.id); clearTimeout(item.timer);
    if (data.type === 'error') item.reject(new Error(data.error)); else item.resolve(data.data);
  };
  activeWorker.onerror = () => {
    if (worker === activeWorker) discard('O processamento foi interrompido. Use Limpar caso e reiniciar para tentar novamente.','failed');
  };
}
export function request(operation,payload={}, {onProgress}={}) {
  ensureWorker();
  const id = ++sequence;
  return new Promise((resolve,reject) => {
    const timer = setTimeout(() => discard('O processamento ultrapassou três minutos e foi encerrado. Use Limpar caso e reiniciar; nenhuma resposta anterior substituiu esta execução.','failed'),180000);
    pending.set(id,{resolve,reject,timer,operation,onProgress});
    worker.postMessage({...payload,id,operation});
  });
}
export function restart() { discard('Operação cancelada: o caso temporário foi descartado.'); }
window.addEventListener('pagehide',() => discard('Página encerrada.'));
