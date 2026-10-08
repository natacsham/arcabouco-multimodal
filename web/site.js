// Reading preferences live only in this page. No storage, analytics or requests.
const root = document.documentElement;
const readingTools = document.querySelector('[data-site-accessibility]');
if (readingTools) {
  let scale = 100;
  const baseFontSize = parseFloat(getComputedStyle(root).fontSize);
  const decrease = readingTools.querySelector('[data-font-decrease]');
  const increase = readingTools.querySelector('[data-font-increase]');
  const status = readingTools.querySelector('[data-reading-status]');
  const contrast = readingTools.querySelector('[data-site-contrast]');
  const setScale = value => {
    scale = Math.max(100, Math.min(200, value));
    root.style.fontSize = scale === 100 ? '' : `${baseFontSize * scale / 100}px`;
    // Keep boundary controls focusable and explain their unavailable state.
    decrease.setAttribute('aria-disabled', String(scale === 100));
    increase.setAttribute('aria-disabled', String(scale === 200));
    status.textContent = `Texto: ${scale}%`;
  };
  decrease.addEventListener('click', () => setScale(scale - 25));
  increase.addEventListener('click', () => setScale(scale + 25));
  readingTools.querySelector('[data-font-reset]').addEventListener('click', () => setScale(100));
  contrast.addEventListener('click', () => {
    const enabled = root.dataset.contrast !== 'high';
    if (enabled) root.dataset.contrast = 'high';
    else delete root.dataset.contrast;
    document.body.classList.toggle('high-contrast', enabled);
    contrast.setAttribute('aria-pressed', String(enabled));
  });
  setScale(100);
  readingTools.hidden = false;
}

// The ordinary anchors work without JavaScript; with it, also restore focus.
document.querySelectorAll('[data-site-top]').forEach(link => {
  link.addEventListener('click', event => {
    const target = document.getElementById('inicio');
    if (!target) return;
    event.preventDefault();
    target.focus({preventScroll: true});
    window.scrollTo({top: 0, behavior: 'instant'});
  });
});
