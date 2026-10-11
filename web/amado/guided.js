// Presentation only. Reuse the original controls, renderers and single Worker.
// No retrieval, decision text, confirmation or storage is created here.
const $ = selector => document.querySelector(selector);
const $$ = selector => [...document.querySelectorAll(selector)];
const main = $('#main');
let stage = 1;
let pendingAction = null;
let lastMode = 'known';
let knownReviewed = false;
let scheduled = false;
const free = () => $('#free-tab').getAttribute('aria-selected') === 'true';
const readyForReview = () => free() ? !$('#free-interpretation').hidden : knownReviewed;
const readyForResult = () => !$('#saida').hidden;
const busy = () => main.getAttribute('aria-busy') === 'true';

function updateNavigation() {
  $$('[data-guide-step]').forEach(button => {
    const value = Number(button.dataset.guideStep);
    button.setAttribute('aria-disabled', String(value === 2 ? !readyForReview() : value === 3 ? !readyForResult() : false));
    if (value === stage) button.setAttribute('aria-current', 'step');
    else button.removeAttribute('aria-current');
  });
}

function showStage(next, focus = false) {
  stage = next;
  $('#guide-status').textContent = '';
  document.body.dataset.guideStage = String(stage);
  if (stage === 1) {
    $('#reported-step').open = true;
    $('#free-narrative-block').open = true;
  } else if (stage === 2) {
    $('#organized-step').open = true;
    $('#free-interpretation').open = true;
  }
  updateNavigation();
  if (!focus) return;
  const target = stage === 3 ? $('#decision-title') : stage === 2
    ? $(free() ? '#free-interpretation > summary' : '#organized-step > summary')
    : $(free() ? '#free-tab' : '#known-tab');
  requestAnimationFrame(() => {
    target.focus({preventScroll: true});
    $('#guide-progress').scrollIntoView({block: 'start', behavior: 'auto'});
  });
}

function synchronize() {
  scheduled = false;
  const nowBusy = busy();
  const mode = free() ? 'free' : 'known';
  if (mode !== lastMode) { lastMode = mode; knownReviewed = false; showStage(1); }
  if (!nowBusy && pendingAction) {
    const action = pendingAction; pendingAction = null;
    const failed = Boolean($('#runtime-error').textContent.trim());
    if (!failed && action === 'review' && !free() && $('#organized-step').open) knownReviewed = true;
    if (!failed && action === 'generate' && readyForResult()) showStage(3, true);
    else if (!failed && action === 'review' && readyForReview()) showStage(2, true);
    else if (action === 'clear' || action === 'switch') showStage(1, true);
  }
  if (stage === 3 && !readyForResult()) showStage(readyForReview() ? 2 : 1, true);
  if (stage === 2 && !readyForReview()) showStage(1, true);
  updateNavigation();
}
function schedule() {
  if (scheduled) return;
  scheduled = true;
  // Run after all listeners for the user action. A microtask can run between
  // capture and target listeners and see the previous busy state.
  setTimeout(synchronize, 0);
}

function invalidateReviewedReport() {
  knownReviewed = false;
  // Use the original invalidation handler, including lastResult and speech.
  // A fresh confirmation of the report also invalidates the engine's result.
  $('#mapping-confirmed').checked = false;
  $('#mapping-confirmed').dispatchEvent(new Event('change', {bubbles: true}));
  updateNavigation();
}
$('#reported-correction').addEventListener('input', invalidateReviewedReport);
$$('input[name="reported-confirmation"]').forEach(input => input.addEventListener('change', () => {
  if (knownReviewed || readyForResult()) invalidateReviewedReport();
}));

main.addEventListener('click', event => {
  const button = event.target.closest('button');
  if (!button || button.disabled) return;
  if (button.id === 'clear-case') { knownReviewed = false; pendingAction = 'clear'; showStage(1); }
  else if (busy()) return;
  else if (['known-tab', 'free-tab'].includes(button.id)) pendingAction = 'switch';
  else if (['confirm-reported', 'organize-narrative'].includes(button.id)) {
    if (button.id === 'confirm-reported') invalidateReviewedReport();
    pendingAction = 'review';
  }
  else if (['generate-known', 'generate-free'].includes(button.id)) pendingAction = 'generate';
}, true);
$('#template-select').addEventListener('change', () => { if (!busy()) pendingAction = 'review'; }, true);
$$('[role="tab"]').forEach(tab => tab.addEventListener('keydown', event => {
  if (['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(event.key) && !busy()) pendingAction = 'switch';
}, true));
$$('[data-guide-step]').forEach(button => button.addEventListener('click', () => {
  if (busy()) return;
  if (button.getAttribute('aria-disabled') === 'true') {
    $('#guide-status').textContent = Number(button.dataset.guideStep) === 2
      ? 'Primeiro escolha ou descreva o caso e organize as informações.'
      : 'Confira as informações e construa a orientação para acessar esta etapa.';
    return;
  }
  if ('speechSynthesis' in window) speechSynthesis.cancel();
  $('#guide-status').textContent = '';
  showStage(Number(button.dataset.guideStep), true);
}));
$('#guide-expand').addEventListener('click', () => {
  $$('#shared-explanation .explanation-choice').forEach(item => { item.open = true; });
  $('#guide-status').textContent = 'Escolhas abertas. Os aprofundamentos documentais continuam opcionais.';
});
$('#guide-collapse').addEventListener('click', () => {
  $$('#shared-explanation .explanation-choice').forEach(item => { item.open = false; });
  $('#guide-status').textContent = 'Escolhas recolhidas. Seus títulos, modos e estados continuam visíveis.';
});

// Keep the speech stop action available even when another step is visible.
$('.intro > .actions').append($('#stop-speech'));
const observer = new MutationObserver(schedule);
observer.observe(main, {attributes: true, attributeFilter: ['aria-busy']});
for (const selector of ['#saida', '#free-interpretation', '#known-tab', '#free-tab']) {
  observer.observe($(selector), {attributes: true, attributeFilter: ['hidden', 'aria-selected']});
}
// Observe only presenter replacement, not its internal graph/disclosure updates.
observer.observe($('#shared-explanation'), {childList: true});
observer.observe($('#reported-status'), {childList: true});
$('#guide-progress').hidden = false;
showStage(1);
synchronize();
