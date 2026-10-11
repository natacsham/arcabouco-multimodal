// Read-only views of the same curated records and prepared execution as AMADO.
// Opening this documentation does not generate a decision or query originals.
const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const rows = value => Array.isArray(value) ? value : [];
const label = row => row?.title || row?.titulo || row?.label || row?.enunciado || row?.id || '';
function link(url, text) {
  try { const u = new URL(url); if (!['https:', 'http:'].includes(u.protocol)) return ''; return `<a href="${esc(u.href)}">${esc(text)}</a>`; } catch { return ''; }
}
const list = values => `<ul>${values.filter(Boolean).map(v => `<li>${esc(v)}</li>`).join('')}</ul>`;
const accessLabel = state => ({
  NAO_CONSULTADA_NESTA_REVISAO: 'Original não consultado nesta revisão.',
  SECOES_SELECIONADAS_CONSULTADAS: 'Seções selecionadas consultadas; o documento completo não foi reconferido.',
  PAGINA_ATUAL_CONSULTADA_EDICAO_HISTORICA_NAO_CONFERIDA: 'Página atual consultada; edição histórica ainda não conferida.',
  ACESSO_RESTRITO: 'Acesso restrito; conteúdo não consultado.'
}[state] || 'Consulta do original não registrada.');

export function renderSourcePath(result) {
  const cfg = rows(result?.explanation?.configurations)[0];
  if (!cfg) return '<p>O exemplo não retornou uma escolha fundamentada. Nenhum percurso será inventado.</p>';
  const construction = cfg.construction || {};
  const allArts = rows(construction.articulations);
  const arts = allArts.filter(a => a.mobilized_in_execution === true && a.habilitada_para_decisao !== false);
  const historical = allArts.filter(a => a.mobilized_in_execution !== true && a.habilitada_para_decisao !== false);
  const blocked = allArts.filter(a => a.habilitada_para_decisao === false);
  const contributions = rows(construction.contributions).filter(c => arts.some(a => a.id === c.articulation_id) && ['CONFERIDA_NO_DOCUMENTO', 'CONFERIDA_NO_REGISTRO'].includes(c.verification_status));
  const knowledge = rows(construction.knowledge);
  const conditions = rows(cfg.application?.context_conditions);
  const supports = rows(cfg.application?.supports);
  return `<p><strong>Escolha do exemplo:</strong> ${esc(cfg.title)}. Esta é uma execução técnica preparada, não uma sessão de participante.</p>
    <ol class="source-stages" aria-label="Percurso documental da escolha">
      <li><strong>Conteúdos localizados</strong><span>${contributions.length} contribuições registradas.</span></li>
      <li><strong>Operação analítica</strong><span>${arts.length} articulações documentadas, realizadas antes da consulta.</span></li>
      <li><strong>Conhecimento resultante</strong><span>${knowledge.map(k => esc(k.id)).join(', ') || 'Não detalhado'}.</span></li>
      <li><strong>Critério aplicado</strong><span>${supports.map(s => esc(s.criterion_id)).join(', ') || 'Não detalhado'}; origem própria, não atribuída automaticamente aos conhecimentos.</span></li>
      <li><strong>Escolha situada</strong><span>${esc(cfg.function)}.</span></li>
    </ol>
    <details><summary>1. O que cada fonte contribuiu</summary><ul class="source-path-records">${contributions.map(c => `<li><strong>${esc(label(c.source))}</strong><p>${esc(c.statement)}</p><p>${esc(c.excerpt?.location || 'Localização ainda incompleta.')}</p>${link(c.excerpt?.document_url || c.source?.url, 'Consultar o original')}<p>Conferência: ${esc(c.verification_status)}. ${esc(c.justification)}</p></li>`).join('') || '<li>Contribuições individuais ainda não detalhadas.</li>'}</ul></details>
    <details><summary>2. Como os conteúdos foram relacionados</summary>${arts.map(a => `<h3>${esc(label(a))}</h3><p>${esc(a.operation_explanation || a.operacao || 'Operação não detalhada neste retorno.')}</p><p><strong>O que acrescentou:</strong> ${esc(a.added_understanding || 'Não detalhado.')}</p><p>${esc(a.limite || '')}</p>`).join('')}<p>${historical.length} relações históricas não mobilizadas e ${blocked.length} relações bloqueadas ficaram fora deste percurso.</p></details>
    <details><summary>3. Que conhecimento ficou disponível</summary>${knowledge.map(k => `<p><strong>${esc(k.id)}:</strong> ${esc(k.enunciado || label(k))}</p><p>${esc(k.limite || k.limite_transferencia || '')}</p>${k.foundation_review_status ? `<p><strong>Conferência da fundamentação:</strong> ${esc(k.foundation_review_status)}.</p>` : ''}${rows(k.pending_foundation_items).length ? `<details><summary>O que ainda precisa de conferência</summary>${list(k.pending_foundation_items)}</details>` : ''}`).join('')}</details>
    <details><summary>4. Por que foi empregado neste exemplo</summary><p>Informações do caso usadas na recuperação ou seleção:</p>${list(conditions.map(label))}<p>Critérios e conhecimentos associados a esta aplicação:</p>${supports.map(s => `<h3>${esc(s.criterion_id)}</h3><p>${esc(s.criterion_statement)}</p><p><strong>Conhecimentos empregados:</strong> ${rows(s.knowledge_ids).map(esc).join(', ')}.</p><p>${esc(s.justification)}</p><details><summary>Conferir a origem deste critério</summary><ul>${rows(s.origins).map(o => `<li><p>${esc(o.document_paraphrase || o.localizacao_publica || o.id)}</p><p>${esc(o.localizacao_publica)} · ${esc(o.status_localizacao)}</p>${link(o.document_url, 'Consultar a seção original')}</li>`).join('')}</ul></details>`).join('')}<p>Encontrar um registro não prova adequação. As verificações, as pendências e os limites permanecem na explicação da orientação.</p></details>
    <p><a href="../amado/">Experimentar a consulta no AMADO</a></p>`;
}

async function load(disclosure, target, url, render) {
  if (!disclosure || !target) return;
  let done = false, busy = false;
  disclosure.addEventListener('toggle', async () => {
    if (!disclosure.open || done || busy) return;
    busy = true; target.setAttribute('aria-busy', 'true'); target.textContent = 'Carregando os registros…';
    try { const response = await fetch(new URL(url, import.meta.url)); if (!response.ok) throw new Error(); const data = await response.json(); render(target, data); done = true; }
    catch { target.innerHTML = '<p role="status">Não foi possível carregar. Feche e abra este bloco para tentar novamente.</p>'; }
    finally { busy = false; target.removeAttribute('aria-busy'); }
  });
}
function renderCatalog(target, data) {
  const sources = rows(data.sources), refs = rows(data.references);
  target.innerHTML = `<p>${sources.length} fontes e ${refs.length} referências. Ter um link não significa que o texto integral foi conferido ou utilizado na orientação.</p><details><summary>Fontes da trajetória e diretrizes</summary><ul class="source-catalog-list">${sources.map(s => `<li><strong>${esc(label(s))}</strong> — ${link(s.url, 'Consultar a origem') || 'Link ainda não localizado'}${s.edition ? ` · ${esc(s.edition)}` : ''}<p>${esc(accessLabel(s.access_status))}</p></li>`).join('')}</ul></details><div class="source-catalog-filter"><label for="source-publication">Referências citadas na publicação</label><select id="source-publication"><option value="">Escolha uma publicação</option>${sources.filter(s => refs.some(r => r.fonte_que_cita_id === s.id)).map(s => `<option value="${esc(s.id)}">${esc(label(s))}</option>`).join('')}</select></div><p data-source-count role="status"></p><ul class="source-catalog-list" data-source-references></ul>`;
  const select = target.querySelector('select'), output = target.querySelector('[data-source-references]');
  select.addEventListener('change', () => {
    const selected = refs.filter(r => r.fonte_que_cita_id === select.value);
    target.querySelector('[data-source-count]').textContent = `${selected.length} referências desta publicação.`;
    output.innerHTML = selected.map(r => `<li><p>${esc(r.referencia_exata || r.id)}</p>${link(r.url, 'Consultar a referência original') || '<p>Endereço ainda não localizado.</p>'}<p>Referência citada, sem promoção automática a conhecimento.</p><p>${esc(accessLabel(r.access_status))}</p><details><summary>Estado desta referência</summary><p>Conferência do texto integral: não confirmada nesta auditoria.</p><p>${esc(r.audit?.promotion_status || 'BIBLIOGRAFIA_CITADA')} · ${esc(r.audit?.full_text_available || 'NAO_CONFIRMADO')} · ${esc(r.audit?.metadata_status || '')}</p><p>${esc(r.edition || '')} ${r.consulted_at ? ` · Consulta registrada em ${esc(r.consulted_at)}` : ''}</p><p>Bibliografia citada não é autorização automática para orientar uma decisão.</p></details></li>`).join('');
  });
}
if (typeof document !== 'undefined') {
  load(document.querySelector('[data-source-path-details]'), document.querySelector('[data-source-path]'), './assets/explanation-pilot.json', (t,d) => { t.innerHTML = renderSourcePath(d); });
  load(document.querySelector('[data-source-catalog-details]'), document.querySelector('[data-source-catalog]'), './assets/source-catalog.json', renderCatalog);
}
