import { renderExplanation } from './explanation.js';
import { situatedOutput } from './amado/situated-output.mjs';
const disclosure = document.querySelector('[data-explanation-pilot-details]');
const target = document.querySelector('[data-explanation-pilot]');
let pending = false;
let loaded = false;

async function loadPilot() {
  if (!target || pending || loaded) return;
  pending = true;
  target.setAttribute('aria-busy', 'true');
  target.innerHTML = '<p role="status">Carregando os registros do exemplo…</p>';
  try {
    const response = await fetch(new URL('./assets/explanation-pilot.json', import.meta.url));
    if (!response.ok) throw new Error('Exemplo indisponível.');
    const result = await response.json();
    if (result.result_contract === 'AMADO_SITUATED_1') {
      const view = situatedOutput(result);
      target.innerHTML = '<p>Possibilidade gerada a partir dos registros atuais. Condições ainda não confirmadas permanecem indicadas; não é uma avaliação em uso.</p>'+view.html;
      loaded = true;
      return;
    }
    if (!Array.isArray(result.explanation?.configurations)) throw new Error('Registros incompletos.');
    renderExplanation(target, result, {prepared: true});
    loaded = true;
  } catch {
    target.innerHTML = '<p role="status">Não foi possível carregar os registros do exemplo. A explicação da pesquisa continua disponível nesta página.</p><button type="button" class="button secondary">Tentar carregar novamente</button>';
    target.querySelector('button').addEventListener('click', loadPilot);
  } finally {
    pending = false;
    target.removeAttribute('aria-busy');
  }
}
disclosure?.addEventListener('toggle', () => { if (disclosure.open) loadPilot(); });
