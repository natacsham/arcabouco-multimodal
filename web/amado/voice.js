// User-initiated dictation. No recording, upload endpoint or persistent audio.
export function setupDictation({button, input, status, preview, dialog, allow, cancel}) {
  const Recognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  let recognition = null, active = false, checking = false, permitted = false, token = 0;
  const caption = button.querySelector('span');
  function state(listening) {
    active = listening; button.setAttribute('aria-pressed', String(listening));
    caption.textContent = listening ? 'Parar' : 'Falar';
  }
  function closeDialog() { if (dialog.open) dialog.close(); button.focus(); }
  async function start(local) {
    if (active || checking) return;
    if (!Recognition) { status.textContent = 'O ditado não está disponível neste navegador. Você pode escrever ou usar o ditado do seu dispositivo.'; return; }
    const instance = new Recognition(); recognition = instance;
    instance.lang = 'pt-BR'; instance.continuous = true; instance.interimResults = true;
    if (local) instance.processLocally = true;
    const base = input.value.trimEnd(), segments = new Map(), thisToken = ++token;
    checking = true;
    let failed = false;
    instance.onstart = () => {
      if (thisToken !== token) { instance.abort(); return; }
      checking = false;
      state(true); status.textContent = 'Ouvindo… O texto reconhecido aparecerá no campo.';
    };
    instance.onresult = event => {
      if (thisToken !== token) return;
      let interim = '';
      for (let i = event.resultIndex; i < event.results.length; i++) {
        const result = event.results[i];
        if (result.isFinal) segments.set(i, result[0].transcript.trim());
        else interim += result[0].transcript;
      }
      const text = [base, ...[...segments.entries()].sort((a,b) => a[0]-b[0]).map(([,value]) => value)].filter(Boolean).join(' ');
      if (text.length > input.maxLength && input.maxLength > 0) {
        failed = true; status.textContent = 'O texto chegou ao limite do campo. Revise o que já foi transcrito antes de continuar.';
        instance.stop(); return;
      }
      input.value = text; input.dispatchEvent(new Event('input', {bubbles:true}));
      // Interim words are explicitly provisional; finalized text stays editable
      // in the narrative field. Do not announce every interim word as a status.
      preview.textContent = interim ? 'Transcrição provisória: '+interim : ''; preview.hidden = !interim;
    };
    instance.onerror = event => {
      if (thisToken !== token) return;
      failed = true; checking = false; state(false); preview.hidden = true;
      const messages = {
        'not-allowed':'O acesso ao microfone foi bloqueado. Confira a permissão do navegador ou continue escrevendo.',
        'service-not-allowed':'O serviço de ditado foi bloqueado. Você pode continuar escrevendo.',
        'audio-capture':'Não foi possível acessar o microfone. Confira a conexão e a permissão.',
        'no-speech':'Não foi identificada fala. Tente novamente ou continue escrevendo.',
        'network':'O serviço de ditado não respondeu. Seu texto foi preservado; tente novamente ou escreva.',
        'language-not-supported':'O ditado em português não está disponível neste navegador.'
      };
      status.textContent = messages[event.error] || 'O ditado foi interrompido. O texto já transcrito foi preservado.';
    };
    instance.onend = () => {
      if (thisToken !== token) return;
      checking = false; state(false); preview.hidden = true; recognition = null;
      if (!failed) status.textContent = 'Transcrição no campo. Confira o texto antes de continuar.';
    };
    try { instance.start(); } catch {
      checking = false; state(false); recognition = null; status.textContent = 'Não foi possível iniciar o ditado. Tente novamente ou continue escrevendo.';
    }
  }
  button.addEventListener('click', async () => {
    if (active) { recognition?.stop(); state(false); return; }
    if (checking) return;
    if (!Recognition) { await start(false); return; }
    if (permitted) { await start(false); return; }
    // Only claim local processing when the browser reports an installed language.
    const current = token;
    if ('processLocally' in Recognition.prototype && typeof Recognition.available === 'function') {
      checking = true;
      status.textContent = 'Verificando o ditado em português…';
      try {
        const availability = await Recognition.available({langs:['pt-BR'],processLocally:true});
        checking = false;
        if (current !== token) return;
        if (availability === 'available') { await start(true); return; }
      } catch { checking = false; }
    }
    if (current !== token) return;
    status.textContent = ''; dialog.showModal(); allow.focus();
  });
  allow.addEventListener('click', () => { permitted = true; closeDialog(); start(false); });
  cancel.addEventListener('click', closeDialog);
  dialog.addEventListener('close', () => button.focus());
  input.addEventListener('input', event => {
    if (event.isTrusted && recognition) {
      ++token; checking = false; recognition.abort(); recognition = null; state(false); preview.hidden = true;
      status.textContent = 'Ditado interrompido para preservar sua edição. Continue escrevendo ou inicie o ditado novamente.';
    }
  });
  return {
    stop() { if (recognition) { recognition.stop(); checking = false; state(false); } },
    clear() {
      ++token; checking = false; recognition?.abort(); recognition = null; state(false);
      preview.hidden = true; preview.textContent = ''; status.textContent = '';
      if (dialog.open) dialog.close();
    }
  };
}
