/* VERITAS AI — frontend. Todos os números exibidos vêm da API (/api/analyze e /api/metrics). */
(() => {
'use strict';
const $ = (s, r = document) => r.querySelector(s);
const $$ = (s, r = document) => [...r.querySelectorAll(s)];
const esc = s => String(s).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const pct = (x, d = 1) => (x * 100).toLocaleString('pt-BR', {minimumFractionDigits: d, maximumFractionDigits: d}) + '%';
const pctp = x => x >= 0.9995 ? '>99,9%' : x <= 0.0005 ? '<0,1%' : pct(x);
const num = x => Number(x).toLocaleString('pt-BR');
const dec = (x, d = 3) => Number(x).toLocaleString('pt-BR', {minimumFractionDigits: d, maximumFractionDigits: d});
const ic = id => `<svg class="ic"><use href="#i-${id}"/></svg>`;
const HIST_KEY = 'veritas.history.v1', HIST_MAX = 50;
let METRICS = null, META = null, MODEL_INFO = null;

/* ---------- toast ---------- */
let toastT;
function toast(msg) { const t = $('#toast'); t.textContent = msg; t.classList.add('show'); clearTimeout(toastT); toastT = setTimeout(() => t.classList.remove('show'), 2800); }

/* ---------- roteamento por hash ---------- */
const VIEWS = ['inicio', 'analisar', 'dashboard', 'tecnologia', 'historico'];
function route() {
  const v = VIEWS.includes(location.hash.slice(1)) ? location.hash.slice(1) : 'inicio';
  VIEWS.forEach(n => { $('#view-' + n).hidden = n !== v; });
  $$('[data-nav]').forEach(a => a.classList.toggle('active', a.dataset.nav === v));
  if (v === 'historico') renderHistory();
  window.scrollTo({top: 0});
}
window.addEventListener('hashchange', route);

/* ---------- métricas ---------- */
async function loadMetrics() {
  try {
    const r = await fetch('/api/metrics'); if (!r.ok) throw new Error();
    const j = await r.json(); METRICS = j.metrics; META = j.metadata; MODEL_INFO = j.model_info;
    $('#modelBadge').textContent = `${META.model_name} · v${META.version}`;
    renderHomeKpis(); renderDashboard(); renderTech();
  } catch (e) {
    $('#modelBadge').textContent = 'modelo indisponível';
    $('#homeKpis').innerHTML = '<div class="card" style="grid-column:1/-1">Não foi possível carregar as métricas do modelo. Verifique se o servidor está em execução e se <code>model/</code> contém os arquivos gerados pelo notebook.</div>';
    $('#dashBody').innerHTML = '<div class="card">Métricas indisponíveis.</div>'; $('#techBody').innerHTML = '<div class="card">Informações do modelo indisponíveis.</div>';
  }
}
function renderHomeKpis() {
  const t = METRICS.test, d = METRICS.dataset;
  const G = METRICS.generalization, bal = G && G.configs[G.chosen] ? G.configs[G.chosen].balanced : null;
  const items = [[num(META.training_set_size), 'Notícias usadas no treinamento'], [pct(t.accuracy, 0), 'Acerto em teste com notícias parecidas com as do treinamento'], [bal != null ? pct(bal, 0) : '—', 'Acerto médio com fontes que o sistema nunca viu'], ['Sim', 'Pode responder “inconclusivo” quando não há sinais suficientes']];
  $('#homeKpis').innerHTML = items.map(([v, l]) => `<div class="kpi"><div class="v">${v}</div><div class="l">${l}</div></div>`).join('');
}

/* ---------- contador / validação ---------- */
const words = s => (s.match(/\S+/g) || []).length;
function updateCounter() { const v = $('#text').value; $('#counter').textContent = `${num(v.length)} caracteres · ${num(words(v))} palavras`; if (v.trim()) $('#err').textContent = ''; }
$('#text').addEventListener('input', () => { updateCounter(); if (currentEx && $('#text').value !== exText) { $('#exInfo').hidden = true; } });
$('#btnClear').addEventListener('click', () => { $('#title').value = ''; $('#text').value = ''; updateCounter(); $('#err').textContent = ''; $('#exInfo').hidden = true; currentEx = null; $('#text').focus(); });
const EXAMPLES = [
  {title: 'Exemplo demonstrativo A (texto sintético)', text: 'URGENTE!!! Compartilhe antes que apaguem! Políticos tentam esconder a verdade e a mídia não quer que você saiba o que aconteceu hoje. Divulgue para todos os seus contatos, o Brasil precisa acordar! Isso é um absurdo e ninguém fala nada sobre o assunto. Passe adiante agora mesmo, porque eles querem que você fique calado e não descubra o que realmente está acontecendo por trás dos bastidores do poder.'},
  {title: 'Exemplo demonstrativo B (texto sintético)', text: 'O Ministério da Fazenda informou nesta quarta-feira que a arrecadação federal cresceu no trimestre, segundo dados divulgados pela Receita. De acordo com o órgão, o resultado foi puxado pela retomada da atividade econômica, mas a pasta não detalhou projeções para os próximos meses. Em nota, a Receita afirmou que os números ainda serão consolidados e que uma nova divulgação está prevista para o início do próximo período.'}
];
const CAT = {politica: 'política', tv_celebridades: 'TV e celebridades', sociedade_cotidiano: 'sociedade e cotidiano', ciencia_tecnologia: 'ciência e tecnologia', religiao: 'religião', economia: 'economia'};
let currentEx = null, lastExId = '', exText = '', synIdx = 0;
function showExample(e) {
  currentEx = e; exText = e.text; $('#title').value = ''; $('#text').value = e.text; updateCounter();
  const info = $('#exInfo'); info.hidden = false;
  info.innerHTML = e.synthetic
    ? `Exemplo <b>sintético</b> (escrito para demonstração; não pertence ao corpus).`
    : `Trecho real do <b>Fake.br Corpus</b> (conjunto de teste, não usado no treino) · rótulo original: <b>${esc(e.label)}</b> · categoria: ${esc(CAT[e.category] || e.category)} · fonte: ${esc(e.source)}${e.year ? ' · ' + e.year : ''}${e.truncated ? ' · texto reduzido' : ''}`;
}
async function loadExample(label = 'ANY') {
  try {
    const r = await fetch(`/api/example?label=${label}&exclude=${encodeURIComponent(lastExId)}`);
    if (!r.ok) throw new Error('sem exemplos reais');
    const e = await r.json(); lastExId = e.id; showExample(e); toast(`Exemplo real (${e.label}) carregado.`);
  } catch (err) {
    const t = EXAMPLES[synIdx++ % EXAMPLES.length]; lastExId = ''; showExample({...t, synthetic: true}); $('#title').value = t.title; toast('Exemplo sintético carregado (exemplos reais indisponíveis).');
  }
}
$('#btnExample').addEventListener('click', () => loadExample('ANY'));
$('#btnExFake').addEventListener('click', () => loadExample('FAKE'));
$('#btnExTrue').addEventListener('click', () => loadExample('TRUE'));
function exampleCompare(r) {
  if (!currentEx || currentEx.synthetic || $('#text').value !== exText || $('#title').value.trim()) return '';
  const res = r.label === 'INCONCLUSIVE' ? 'inconclusivo' : r.label;
  return `<div class="excmp">${ic('info')}<div>Rótulo original no corpus: <b>${esc(currentEx.label === 'FAKE' ? 'falsa' : 'verdadeira')}</b> · Resultado do VERITAS AI: <b>${esc(r.plain ? r.plain.headline.toLowerCase() : res)}</b>. O rótulo do corpus foi atribuído pela fonte da notícia; ele não é uma checagem factual individual.</div></div>`;
}

/* ---------- análise ---------- */
function skeletonResult() { return '<div class="card stack"><div class="skeleton h20" style="width:60%;height:28px"></div><div class="skeleton h20" style="height:14px"></div><div class="skeleton h200" style="height:120px"></div><div class="skeleton h20"></div><div class="skeleton h20" style="width:80%"></div></div>'; }
async function analyze() {
  const text = $('#text').value, title = $('#title').value;
  if (!text.trim()) { $('#err').textContent = 'Cole o conteúdo da notícia para analisar.'; $('#text').focus(); return; }
  const btn = $('#btnAnalyze'); btn.disabled = true; btn.classList.add('loading'); $('.btn-label', btn).textContent = 'Analisando…';
  $('#resultPane').innerHTML = skeletonResult();
  if (matchMedia('(max-width:979px)').matches) $('#resultPane').scrollIntoView({behavior: 'smooth', block: 'start'});
  try {
    const [r] = await Promise.all([fetch('/api/analyze', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({text, title})}), new Promise(ok => setTimeout(ok, 450))]);
    const j = await r.json();
    if (!r.ok) throw new Error(j.error || 'Erro ao analisar.');
    renderResult(j, text, title); saveHistory(j, title, text);
  } catch (e) {
    const msg = e instanceof TypeError ? 'Não foi possível contatar o servidor. Verifique se o app está em execução.' : e.message;
    $('#resultPane').innerHTML = `<div class="card"><div class="warnbox">${ic('alert')}<div><b>Não foi possível concluir a análise.</b><br>${esc(msg)}</div></div></div>`;
  } finally { btn.disabled = false; btn.classList.remove('loading'); $('.btn-label', btn).textContent = 'Analisar'; }
}
$('#btnAnalyze').addEventListener('click', analyze);
$('#text').addEventListener('keydown', e => { if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') analyze(); });

function calibBlock(r) {
  if (!r.calibrated || !r.abstention) return '';
  const q = r.calibrated, a = r.abstention;
  return `<div class="calib"><b>Decisão (probabilidade calibrada):</b> FAKE ${pctp(q.FAKE)} · TRUE ${pctp(q.TRUE)}
    <span class="tip-i" data-tip="Ajuste (Platt) feito com previsões sobre fontes que o modelo não viu no treino, para corrigir o excesso de confiança da probabilidade bruta." tabindex="0">${ic('info')}</span>
    <div class="tiny muted" style="margin-top:4px">Regra: FAKE se P(FAKE) ≥ ${pct(a.hi, 0)}; TRUE se P(FAKE) ≤ ${pct(a.lo, 0)}; entre os dois, <b>inconclusivo</b>. Limiares definidos por experimentos entre fontes (ver Dashboard). A barra acima mostra a probabilidade bruta do modelo.</div></div>`;
}
function margemInfo(m) { return m >= 0.6 ? ['forte', 'O classificador separa bem as duas classes neste texto.'] : m >= 0.25 ? ['moderada', 'Há sinal para uma das classes, mas com sobreposição.'] : ['fraca', 'Os padrões do texto são ambíguos para o modelo.']; }
function termList(arr, cls, max) {
  if (!arr.length) return '<p class="muted tiny">Nenhum termo relevante nesta direção.</p>';
  const m = Math.max(...arr.map(x => Math.abs(x.weight)), 1e-9);
  return arr.map(x => `<div class="term"><span title="${esc(x.term)}">${esc(x.term)}</span><div class="bar"><i class="${cls}" style="width:0" data-w="${Math.abs(x.weight) / m * 100}"></i></div></div>`).join('');
}

/* ---------- explicabilidade: "Por que o VERITAS AI chegou a essa conclusão?" ---------- */
const sgn = (x, d = 2) => (x >= 0 ? '+' : '−') + Math.abs(x).toLocaleString('pt-BR', {minimumFractionDigits: d, maximumFractionDigits: d});
function termRows(arr, cls, mx) {
  if (!arr.length) return '<p class="muted tiny">Nenhum termo relevante nesta direção.</p>';
  return arr.map(x => `<div class="term2" data-tip="TF-IDF ${dec(x.tfidf, 3)} × coeficiente ${dec(x.coef, 2)} = ${sgn(x.weight, 3)}" tabindex="0"><span class="w" title="${esc(x.term)}"><span class="tx">${esc(x.term)}</span>${x.ngram > 1 ? '<span class="mini" title="bigrama: sequência de duas palavras">bi</span>' : ''}</span><div class="bar"><i class="${cls}" style="width:0" data-w="${Math.abs(x.weight) / mx * 100}"></i></div><em>${sgn(x.weight)}</em></div>`).join('');
}
function whySection(r) {
  const e = r.explanation; if (!e) return '';
  const evF = e.evidence.FAKE, evT = e.evidence.TRUE, tot = (evF + evT) || 1, net = evT - evF, z = e.decision;
  const pT = r.probabilities.TRUE, pF = r.probabilities.FAKE;
  const mx = Math.max(1e-9, ...e.FAKE.map(x => Math.abs(x.weight)), ...e.TRUE.map(x => Math.abs(x.weight)));
  const netSide = net > 0 ? 'TRUE' : 'FAKE', stronger = evT >= evF ? 'TRUE' : 'FAKE';
  let flip = '';
  if (netSide !== r.label) flip = ` <b>Atenção:</b> o saldo das evidências do texto apontava para ${netSide}, mas o intercepto do modelo inverteu o resultado — sinal de que o texto tem poucos padrões marcantes.`;
  const topShare = e.top_share.FAKE + e.top_share.TRUE;
  return `
  <section class="why" aria-labelledby="whyT">
    <h3 class="why-title" id="whyT">${ic('spark')}<span>Por que o VERITAS AI chegou a essa conclusão?</span></h3>
    <p class="why-lead">Neste texto, <b>${num(e.n_terms)}</b> termos e expressões (${num(e.n_bigrams)} bigramas) fazem parte do vocabulário aprendido pelo modelo: <b>${e.n_terms_toward.FAKE}</b> empurraram a decisão para FAKE e <b>${e.n_terms_toward.TRUE}</b> para TRUE. A Regressão Logística soma o peso de cada um (valor TF-IDF × coeficiente) e acrescenta o <b>intercepto</b> (${sgn(e.intercept)}), o viés de partida aprendido no treino. A evidência a favor de ${stronger} foi maior (${dec(Math.max(evF, evT), 2)} contra ${dec(Math.min(evF, evT), 2)}), e o resultado <b>z = ${sgn(z)}</b> vira probabilidade pela função logística.${flip}</p>
    <div class="eq" role="group" aria-label="Composição da decisão">
      <div class="cell"><span>Intercepto (b)</span><b>${sgn(e.intercept)}</b></div>
      <div class="cell f"><span>Evidência para FAKE</span><b>−${dec(evF, 2)}</b></div>
      <div class="cell t"><span>Evidência para TRUE</span><b>+${dec(evT, 2)}</b></div>
      <div class="cell res"><span>z = b + TRUE − FAKE</span><b>${sgn(z)} → P(TRUE) ${pctp(pT)}</b></div>
    </div>
    <div class="balance"><div class="bar2" role="img" aria-label="Evidência FAKE ${pct(evF / tot, 0)}, TRUE ${pct(evT / tot, 0)}"><i class="f" style="width:0" data-w="${evF / tot * 100}"></i><i class="t" style="width:0" data-w="${evT / tot * 100}"></i></div>
      <div class="cap"><span>FAKE ${pct(evF / tot, 0)} da evidência</span><span>TRUE ${pct(evT / tot, 0)}</span></div></div>
    <div class="terms cols2" style="margin-top:14px">
      <div><h4 class="f">Favoreceram FAKE</h4>${termRows(e.FAKE, 'f', mx)}</div>
      <div><h4 class="t">Favoreceram TRUE (notícia verdadeira)</h4>${termRows(e.TRUE, 't', mx)}</div>
    </div>
    <div class="facts">
      <div><b>${num(e.n_terms)}</b>termos reconhecidos pelo modelo</div>
      <div><b>${pct(e.vocab_coverage, 0)}</b>das palavras do texto estão no vocabulário</div>
      <div><b>${pct(topShare, 0)}</b>da evidência está nos termos listados</div>
    </div>
    <details class="howto"><summary>Como ler esta explicação</summary><ul>
      <li>O peso de um termo é o valor TF-IDF dele neste texto multiplicado pelo coeficiente aprendido; sinal <b>−</b> empurra para FAKE e <b>+</b> para TRUE. Passe o cursor sobre um termo para ver a conta; <span class="mini">bi</span> indica bigrama (sequência de duas palavras).</li>
      <li>O modelo reconhece <b>padrões estatísticos</b> do Fake.br Corpus (vocabulário, estilo, fonte, época). Ele <b>não faz checagem factual independente</b> nem consulta fontes.</li>
      <li>Uma palavra isolada <b>não prova</b> que o texto é falso ou verdadeiro; nomes de portais e expressões de agenda podem refletir a fonte do corpus, não a veracidade.</li>
      <li>As probabilidades não foram calibradas formalmente: use a <b>margem</b> como indicador de ambiguidade, não como certeza.</li></ul>
      <a class="learn" href="#tecnologia">Entenda como o modelo funciona ${ic('arrow')}</a></details>
  </section>`;
}

/* ---------- resultado (v3): um único veredito, linguagem simples; técnica recolhida em "Detalhes técnicos" ---------- */
const LEVEL_DOTS = {baixa: 1, moderada: 2, alta: 3, insuficiente: 0};
function plainHighlights(P) {
  const H = P.highlights, li = a => a.map(i => `<li>${esc(i.text)}</li>`).join('');
  const col = (cls, title, arr) => `<div class="hl ${cls}"><h4>${title}</h4>${arr.length ? `<ul>${li(arr)}</ul>` : '<p class="muted tiny">Nada de destaque neste lado.</p>'}</div>`;
  const notes = H.notas.length ? `<ul class="hl-notes">${H.notas.map(n => `<li>${esc(n.text)}</li>`).join('')}</ul>` : '';
  return `<div class="hl-grid">${col('f', 'Mais comum em notícias falsas', H.falsa)}${col('t', 'Mais comum em notícias verdadeiras', H.verdadeira)}</div>${notes}`;
}
function plainChecks(P) {
  const items = P.checkpoints.map(c => `<li><b>${esc(c.title)}</b>${c.items.length ? ': ' + c.items.map(x => '“' + esc(x) + '”').join(', ') : ''}<br><span class="muted">${esc(c.text)}</span></li>`);
  if (P.entities.length) items.push(`<li><b>Pessoas e instituições citadas</b>: ${P.entities.map(esc).join(', ')}<br><span class="muted">Verifique se existem e se realmente disseram ou fizeram o que o texto afirma. Aparecer no texto não é indício de falsidade.</span></li>`);
  return items.length ? `<ul class="checks">${items.join('')}</ul>` : '<p class="muted" style="font-size:13.5px">Não identificamos números, datas, declarações ou nomes específicos para destacar. Ainda assim, procure a fonte original da notícia.</p>';
}
function techDetails(r, text, title) {
  const pF = r.probabilities.FAKE, pT = r.probabilities.TRUE, ind = r.indicators;
  const toks = text.split(/(\s+)/); let cnt = 0, shown = '';
  toks.forEach(t => { if (/\S/.test(t)) { cnt++; shown += cnt > 200 ? `<span class="cut">${esc(t)}</span>` : esc(t); } else shown += esc(t); });
  return `<details class="techd"><summary>Detalhes técnicos (para quem quiser aprofundar)</summary><div class="stack" style="margin-top:12px">
    <p class="tiny muted">O sistema usa TF-IDF e Regressão Logística (veja <a class="learn" href="#tecnologia">Como a tecnologia funciona</a>). Abaixo estão os números internos da análise.</p>
    <div class="probs"><div class="pbar" role="img" aria-label="Probabilidade bruta FAKE ${pctp(pF)}, TRUE ${pctp(pT)}"><i class="f" style="width:0" data-w="${pF * 100}"></i><i class="t" style="width:0" data-w="${pT * 100}"></i></div>
      <div class="plabels"><span class="f">FAKE ${pctp(pF)}</span><span class="t">TRUE ${pctp(pT)}</span></div></div>
    <p class="tiny muted">Probabilidade bruta do classificador. A decisão final usa a probabilidade calibrada e as regras de inconclusivo, por isso o resultado principal pode diferir da barra acima. Nenhuma delas é a chance de a notícia ser verdadeira.</p>
    ${calibBlock(r)}
    ${whySection(r)}
    <div class="inds"><div class="ind"><b>${num(ind.palavras)}</b><span>palavras</span></div><div class="ind"><b>${ind.exclamacoes}</b><span>exclamações</span></div><div class="ind"><b>${ind.interrogacoes}</b><span>interrogações</span></div><div class="ind"><b>${pct(r.vocab_coverage, 0)}</b><span>palavras conhecidas</span></div></div>
    <details class="txt"><summary>Texto analisado${title ? ' — ' + esc(title) : ''}</summary><div class="body">${shown}</div>${ind.texto_truncado ? '<p class="tiny muted">Trecho esmaecido: fora das 200 primeiras palavras, não analisado.</p>' : ''}</details>
    <div class="meta-line"><span>Modelo: ${esc(r.model.model_name)}</span><span>· v${esc(r.model.version)}</span><span>· treinado em ${esc(String(r.model.trained_at).slice(0, 10))}</span></div></div></details>`;
}
function renderResult(r, text, title) {
  const P = r.plain, C = P.confidence, dots = LEVEL_DOTS[C.level] ?? 0;
  const warns = r.warnings.filter(w => !w.startsWith('Inconclusivo não significa'));
  $('#resultPane').innerHTML = `
  <div class="card stack result-main">
    <section class="verdict-box ${P.tone}" aria-live="polite">
      <span class="eyebrow-s">Resultado da análise</span>
      <div class="verdict-big">${esc(P.headline)}</div>
      <p class="verdict-sent">${esc(P.sentence)}</p>
      <div class="conf"><span class="conf-l">Nível de confiança</span><span class="conf-dots" aria-hidden="true">${[1, 2, 3].map(i => `<i class="${i <= dots ? 'on' : ''}"></i>`).join('')}</span><b>${esc(C.level)}</b></div>
      ${C.text ? `<p class="tiny muted" style="margin-top:6px">${esc(C.text)}</p>` : ''}
    </section>
    ${exampleCompare(r)}
    <section><h3 class="sec-t">Por que esse resultado?</h3><p class="plain-exp">${esc(P.explanation)}</p>
      ${warns.map(w => `<div class="warnbox">${ic('alert')}<div>${esc(w)}</div></div>`).join('')}</section>
    <section><h3 class="sec-t">O que chamou a atenção na notícia</h3>${plainHighlights(P)}</section>
    <section><h3 class="sec-t">Pontos que merecem verificação</h3>${plainChecks(P)}</section>
    <section><h3 class="sec-t">Verificação em fontes externas</h3><div class="warnbox ext">${ic('info')}<div>${esc(P.external.message)}</div></div></section>
    <div class="warnbox">${ic('info')}<div><b>Limitações.</b> ${esc(P.limits)}</div></div>
    ${techDetails(r, text, title)}
  </div>`;
  requestAnimationFrame(() => requestAnimationFrame(() => $$('#resultPane [data-w]').forEach(e => { e.style.width = e.dataset.w + '%'; })));
}

/* ---------- histórico (localStorage) ---------- */
const readHist = () => { try { return JSON.parse(localStorage.getItem(HIST_KEY)) || []; } catch { return []; } };
const writeHist = h => { try { localStorage.setItem(HIST_KEY, JSON.stringify(h.slice(0, HIST_MAX))); } catch { toast('Não foi possível salvar o histórico neste navegador.'); } };
function saveHistory(r, title, text) {
  const t = title.trim() || `Sem título (${words(text)} palavras)`;   // não guardamos o texto da notícia
  const h = readHist(); h.unshift({id: Date.now(), ts: new Date().toISOString(), title: t.slice(0, 80), label: r.label, probs: r.probabilities, margin: r.margin, terms: {FAKE: r.terms.FAKE.slice(0, 4), TRUE: r.terms.TRUE.slice(0, 4)}, model: r.model.version}); writeHist(h);
}
function renderHistory() {
  const h = readHist(), box = $('#histBody');
  if (!h.length) { box.innerHTML = `<div class="card empty-state">${ic('clock').replace('class="ic"', 'class="ic big"')}<h3>Histórico vazio</h3><p class="muted">As análises feitas na Central aparecem aqui, apenas neste navegador.</p><a class="btn primary" href="#analisar">Fazer uma análise</a></div>`; return; }
  box.innerHTML = '<div class="hist">' + h.map(i => `<button class="card hitem" data-id="${i.id}"><span class="t">${esc(i.title)}</span><span class="tag ${i.label === 'FAKE' ? 'fake' : i.label === 'TRUE' ? 'true' : 'inc'}">${i.label === 'FAKE' ? 'POSSIVELMENTE FALSA' : i.label === 'TRUE' ? 'POSSIVELMENTE VERDADEIRA' : 'INCONCLUSIVO'}</span><span class="d">${new Date(i.ts).toLocaleString('pt-BR')}</span><span class="d">modelo v${esc(i.model)}</span><span class="p"><span style="color:var(--fake)">FAKE ${pctp(i.probs.FAKE)}</span><span style="color:var(--true)">TRUE ${pctp(i.probs.TRUE)}</span></span></button>`).join('') + '</div><div id="histDetail"></div>';
  $$('.hitem', box).forEach(b => b.addEventListener('click', () => {
    const i = h.find(x => String(x.id) === b.dataset.id); if (!i) return;
    $('#histDetail').innerHTML = `<div class="card stack" style="margin-top:14px"><h3>${esc(i.title)}</h3><div class="muted tiny">${new Date(i.ts).toLocaleString('pt-BR')} · resultado: ${esc(i.label)} · margem ${pct(i.margin, 0)}</div><div class="terms cols2"><div><h4 class="f">Principais termos → FAKE</h4>${termList(i.terms.FAKE, 'f')}</div><div><h4 class="t">Principais termos → TRUE</h4>${termList(i.terms.TRUE, 't')}</div></div><p class="tiny muted">O texto original não é armazenado.</p></div>`;
    requestAnimationFrame(() => requestAnimationFrame(() => $$('#histDetail [data-w]').forEach(e => { e.style.width = e.dataset.w + '%'; })));
    $('#histDetail').scrollIntoView({behavior: 'smooth', block: 'nearest'});
  }));
}
$('#btnClearHist').addEventListener('click', () => { if (!readHist().length) return toast('O histórico já está vazio.'); if (confirm('Apagar todo o histórico de análises deste navegador?')) { localStorage.removeItem(HIST_KEY); renderHistory(); toast('Histórico apagado.'); } });

/* ---------- dashboard ---------- */
function donut(parts) {
  const total = parts.reduce((a, p) => a + p.v, 0), R = 52, C = 2 * Math.PI * R; let off = 0;
  const arcs = parts.map(p => { const len = p.v / total * C; const s = `<circle r="${R}" cx="70" cy="70" fill="none" stroke="${p.c}" stroke-width="18" stroke-dasharray="${len} ${C - len}" stroke-dashoffset="${-off}" transform="rotate(-90 70 70)"/>`; off += len; return s; }).join('');
  return `<svg viewBox="0 0 140 140" width="140" height="140" role="img" aria-label="Distribuição das classes">${arcs}<text x="70" y="66" text-anchor="middle" fill="#e8eefc" font-size="20" font-weight="700">${num(total)}</text><text x="70" y="84" text-anchor="middle" fill="#8fa0c4" font-size="10">notícias</text></svg>`;
}
function confusion(cm) {
  const tot = cm.flat().reduce((a, b) => a + b, 0), cell = (v, ok) => `<div class="c" style="background:${ok ? 'rgba(34,211,238,' : 'rgba(255,122,138,'}${(0.08 + 0.5 * v / Math.max(...cm.flat())).toFixed(2)})"><b>${num(v)}</b><span>${pct(v / tot, 1)}</span></div>`;
  return `<div class="cm"><div></div><div class="h">Predito FAKE</div><div class="h">Predito TRUE</div><div class="h">Real FAKE</div>${cell(cm[0][0], true)}${cell(cm[0][1], false)}<div class="h">Real TRUE</div>${cell(cm[1][0], false)}${cell(cm[1][1], true)}</div>
  <p class="tiny muted" style="text-align:center">Falsos negativos (FAKE → TRUE): <b>${cm[0][1]}</b> · Falsos positivos (TRUE → FAKE): <b>${cm[1][0]}</b></p>`;
}
function renderDashboard() {
  const m = METRICS, t = m.test, d = m.dataset, pcF = t.per_class.FAKE, pcT = t.per_class.TRUE;
  const tip = (l, x) => `<span data-tip="${x}" tabindex="0">${l}</span>`;
  const kpis = [[pct(t.accuracy, 2), tip('Acurácia', 'Proporção de acertos sobre todas as notícias do teste. Sozinha, pode enganar.')], [pct(t.precision_macro, 2), tip('Precisão (macro)', 'Dos textos que o modelo apontou como de uma classe, quantos realmente eram. Média das duas classes.')], [pct(t.recall_macro, 2), tip('Recall (macro)', 'Das notícias de uma classe, quantas o modelo encontrou. Média das duas classes.')], [pct(t.f1_macro, 2), tip('F1 macro', 'Média harmônica entre precisão e recall, calculada por classe e depois promediada.')]];
  const sp = d.split, spRow = n => `<tr><td>${n}</td><td class="n">${num(sp[n].n)}</td><td class="n">${num(sp[n].FAKE)}</td><td class="n">${num(sp[n].TRUE)}</td></tr>`;
  const mc = m.model_comparison, maxv = 1;
  const bars = mc.map(c => `<div class="gb"><div class="pair"><i style="height:${c.val.f1_macro * 118}px;background:#4a78ff"><em>${(c.val.f1_macro * 100).toFixed(1)}</em></i><i style="height:${c.test.f1_macro * 118}px;background:var(--cyan)"><em>${(c.test.f1_macro * 100).toFixed(1)}</em></i></div><span>${esc(c.model)}</span></div>`).join('');
  const topT = (arr, cls) => { const mx = Math.max(...arr.map(x => Math.abs(x.weight))); return arr.slice(0, 10).map(x => `<div class="term"><span>${esc(x.term)}</span><div class="bar"><i class="${cls}" style="width:${Math.abs(x.weight) / mx * 100}%"></i></div></div>`).join(''); };
  const G = m.generalization, AB = m.abstention, CAL = m.calibration;
  $('#dashBody').innerHTML = `
  <div class="kpi-strip" style="margin-top:18px">${kpis.map(([v, l]) => `<div class="kpi"><div class="v">${v}</div><div class="l">${l}</div></div>`).join('')}</div>
  <div class="dash-grid">
    <div class="card"><h3>Desempenho por classe (teste)</h3><div class="sub">Classe positiva para erros: FAKE.</div><div class="scroll-x"><table class="tbl"><thead><tr><th>Classe</th><th class="n">Precisão</th><th class="n">Recall</th><th class="n">F1</th><th class="n">n</th></tr></thead><tbody>
      <tr><td>FAKE</td><td class="n">${pct(pcF.precision)}</td><td class="n">${pct(pcF.recall)}</td><td class="n">${pct(pcF.f1)}</td><td class="n">${pcF.support}</td></tr>
      <tr><td>TRUE</td><td class="n">${pct(pcT.precision)}</td><td class="n">${pct(pcT.recall)}</td><td class="n">${pct(pcT.f1)}</td><td class="n">${pcT.support}</td></tr></tbody></table></div>
      <p class="tiny muted">ROC-AUC ${dec(t.roc_auc)} · Brier ${dec(t.brier)} · erro de calibração (ECE) ${dec(t.ece)}</p></div>
    <div class="card"><h3>Matriz de confusão (teste)</h3><div class="sub">Linhas: classe real · colunas: predita.</div>${confusion(t.confusion_matrix)}</div>
    <div class="card"><h3>Distribuição das classes</h3><div class="sub">Corpus após remoção de duplicatas.</div><div class="donut">${donut([{v: d.class_counts_clean.FAKE, c: '#ff7a8a'}, {v: d.class_counts_clean.TRUE, c: '#22d3ee'}])}<div class="legend"><div><i style="background:#ff7a8a"></i>FAKE: ${num(d.class_counts_clean.FAKE)}</div><div><i style="background:#22d3ee"></i>TRUE: ${num(d.class_counts_clean.TRUE)}</div><div class="muted tiny">${num(d.n_raw)} originais · ${num(d.n_removed_duplicates)} duplicatas removidas</div></div></div>
      <table class="tbl" style="margin-top:12px"><thead><tr><th>Conjunto</th><th class="n">Total</th><th class="n">FAKE</th><th class="n">TRUE</th></tr></thead><tbody>${['treino', 'validação', 'teste'].map(spRow).join('')}</tbody></table></div>
    <div class="card"><h3>Comparação entre modelos</h3><div class="sub">F1 macro — validação e teste (teste usado só após a seleção).</div><div class="gbars">${bars}</div><div class="legend-inline"><span><i style="background:#4a78ff"></i>Validação</span><span><i style="background:var(--cyan)"></i>Teste</span></div>
      <p class="tiny muted">Selecionado: ${esc(m.selected_model.name)} — preferido salvo vantagem &gt; 1 p.p. de outro modelo (probabilidades e coeficientes interpretáveis).</p></div>
    <div class="card wide"><h3>Principais características aprendidas</h3><div class="sub">Maiores coeficientes da Regressão Logística. São associações estatísticas do corpus, não prova de desinformação.</div><div class="terms cols2"><div><h4 class="f">Associados a FAKE</h4>${topT(m.top_terms.FAKE, 'f')}</div><div><h4 class="t">Associados a TRUE</h4>${topT(m.top_terms.TRUE, 't')}</div></div></div>
    ${genCard(G, m)}
    ${abstCard(AB, CAL, m)}
    ${noteCard(G, d, AB)}
  </div></div>`;
}



/* ---------- v2: generalização, abstenção, leitura crítica ---------- */
function genCard(G, m) {
  const rows = Object.entries(G.configs).filter(([, v]) => v.length_matched).sort((x, y) => y[1].length_matched.balanced - x[1].length_matched.balanced);
  const tr = rows.map(([k, v]) => { const tag = k === G.chosen ? ' <span class="tag true">v2</span>' : (k === G.v1 ? ' <span class="tag fake">v1</span>' : '');
    return `<tr><td>${esc(k)}${tag}</td><td class="n">${pct(v.recall_FAKE_mean, 1)}</td><td class="n">${pct(v.recall_TRUE_mean, 1)}</td><td class="n">${pct(v.balanced, 1)}</td><td class="n"><b>${pct(v.length_matched.balanced, 1)}</b></td></tr>`; }).join('');
  const t = G.temporal_split_train_le_2016_test_ge_2017, tt = Object.entries(t).map(([k, v]) => `<tr><td>${esc(k)}</td><td class="n">${pct(v.recall_FAKE, 1)}</td><td class="n">${pct(v.recall_TRUE, 1)}</td><td class="n">${pct(v.balanced, 1)}</td></tr>`).join('');
  return `<div class="card wide"><h3>Generalização entre fontes (leave-one-source-out)</h3><div class="sub">Cada fonte inteira fica de fora do treino; mede-se o recall na classe dessa fonte. “Comprimento controlado” avalia só faixas de tamanho em que existem as duas classes (200–800 palavras), para não premiar o atalho do tamanho do texto. Critério de escolha: última coluna.</div>
    <div class="scroll-x"><table class="tbl"><thead><tr><th>Configuração</th><th class="n">Recall FAKE</th><th class="n">Recall TRUE</th><th class="n">Balanceado</th><th class="n">Comp. controlado</th></tr></thead><tbody>${tr}</tbody></table></div>
    <h3 style="margin-top:16px">Separação temporal</h3><div class="sub">Treino com notícias até 2016 e teste em 2017–2018 (as TRUE são majoritariamente de 2017–2018).</div>
    <div class="scroll-x"><table class="tbl"><thead><tr><th>Configuração</th><th class="n">Recall FAKE</th><th class="n">Recall TRUE</th><th class="n">Balanceado</th></tr></thead><tbody>${tt}</tbody></table></div></div>`;
}
function abstCard(AB, CAL, m) {
  const o = AB.oof_source_shift, tr = AB.test_random, f = x => x == null ? '—' : pct(x, 1);
  const row = (n, a, b, c) => `<tr><td>${n}</td><td class="n">${a}</td><td class="n">${b}</td><td class="n">${c}</td></tr>`;
  return `<div class="card wide"><h3>Resultado inconclusivo e calibração</h3><div class="sub">Se a probabilidade calibrada de FAKE fica entre ${pct(AB.lo, 0)} e ${pct(AB.hi, 0)}, o sistema abstém-se. Limiares escolhidos em previsões sobre fontes não vistas (treino+validação), nunca no teste. ${AB.policy_met ? 'A meta de qualidade foi atingida.' : '<b>A meta de qualidade (' + pct(AB.target_selective_accuracy, 0) + ') não foi atingida</b>; usada a banda que maximiza acurácia × cobertura.'}</div>
    <div class="scroll-x"><table class="tbl"><thead><tr><th>Cenário</th><th class="n">Cobertura</th><th class="n">Acurácia nas decididas</th><th class="n">FAKE → TRUE</th></tr></thead><tbody>
      ${row('Entre fontes, sem abstenção', '100%', f(o.without.accuracy), o.without.FN)}
      ${row('Entre fontes, com abstenção', f(o.with.coverage), f(o.with.accuracy), o.with.FN)}
      ${row('Teste aleatório, sem abstenção', '100%', f(tr.before.accuracy), tr.before.FN)}
      ${row('Teste aleatório, com abstenção', f(tr.after.coverage), f(tr.after.accuracy), tr.after.FN)}</tbody></table></div>
    <p class="tiny muted">Calibração (erro esperado ECE): bruta ${dec(CAL.ece_raw, 3)} → calibrada ${dec(CAL.ece_cal_logo, 3)} entre fontes (calibrador avaliado sem ver a fonte testada); no teste aleatório, ${dec(CAL.test.ece_raw, 3)} → ${dec(CAL.test.ece_cal, 3)}. Inconclusivo não significa verdadeiro nem falso. Tempo de treino ${m.timing.train_fit_seconds} s; inferência ${m.timing.inference_ms_per_text} ms por texto.</p></div>`;
}
function noteCard(G, d, AB) {
  const c = G.configs, a = c[G.v1], b = c[G.chosen], lo = c['Baseline: só comprimento do texto'];
  const topF = Math.max(...Object.values(d.top_domains.FAKE));
  return `<div class="card wide note-card"><h3>${ic('alert')} Leitura crítica do desempenho</h3><ul>
      <li>Deixando uma fonte inteira de fora do treino, o recall médio de FAKE foi <b>${pct(b.recall_FAKE_mean, 1)}</b> na versão 2.0 (v1: ${pct(a.recall_FAKE_mean, 1)}) e o de TRUE, <b>${pct(b.recall_TRUE_mean, 1)}</b> (v1: ${pct(a.recall_TRUE_mean, 1)}). O teste aleatório superestima o desempenho em fontes novas.</li>
      ${lo ? `<li>Um classificador que usa <b>só o tamanho do texto</b> chega a ${pct(lo.balanced, 1)} no mesmo protocolo (${pct(lo.length_matched.balanced, 1)} com comprimento controlado): tamanho é um atalho do corpus.</li>` : ''}
      <li>${pct(topF, 0)} das FAKE vêm de um único site; as TRUE são mais recentes (2017–2018) que as FAKE (2016–2017). Sem mais fontes de FAKE, a generalização tem um teto.</li>
      <li>O sistema classifica estilo; <b>não verifica fatos</b>. Resultados inconclusivos são esperados em textos atípicos.</li></ul></div>`;
}

/* ---------- Conheça a tecnologia ---------- */
function toyTfidf() {
  const docs = ['o governo anunciou a medida', 'o governo não aprovou a medida', 'o urgente compartilhe antes que apaguem tudo'];
  const toks = docs.map(d => d.split(' ')), N = docs.length, target = toks[1];
  const df = t => toks.filter(d => d.includes(t)).length;
  return ['o', 'governo', 'medida', 'não', 'aprovou'].map(t => {
    const tf = target.filter(w => w === t).length, d = df(t), idf = Math.log((1 + N) / (1 + d)) + 1;
    return `<tr><td>${t}</td><td class="n">${tf}</td><td class="n">${d} de ${N}</td><td class="n">${dec(idf, 2)}</td><td class="n"><b>${dec(tf * idf, 2)}</b></td></tr>`;
  }).join('');
}
function sigmoidSvg() {
  const pts = []; for (let z = -6; z <= 6.01; z += 0.25) { const p = 1 / (1 + Math.exp(-z)); pts.push(`${(40 + (z + 6) / 12 * 280).toFixed(1)},${(130 - p * 110).toFixed(1)}`); }
  return `<svg class="sigm" viewBox="0 0 340 170" role="img" aria-label="Curva logística: z negativo leva a FAKE, z positivo a TRUE">
    <line x1="40" y1="130" x2="320" y2="130" stroke="#3a4a72"/><line x1="180" y1="16" x2="180" y2="136" stroke="#3a4a72" stroke-dasharray="3 4"/><line x1="40" y1="75" x2="320" y2="75" stroke="#3a4a72" stroke-dasharray="3 4"/>
    <polyline fill="none" stroke="url(#vg)" stroke-width="3" points="${pts.join(' ')}"/>
    <text x="34" y="24" fill="#8fa0c4" font-size="10" text-anchor="end">100%</text><text x="34" y="79" fill="#8fa0c4" font-size="10" text-anchor="end">50%</text><text x="34" y="134" fill="#8fa0c4" font-size="10" text-anchor="end">0%</text>
    <text x="180" y="150" fill="#8fa0c4" font-size="10" text-anchor="middle">z = 0</text>
    <text x="100" y="164" fill="#ff7a8a" font-size="11" text-anchor="middle">z &lt; 0 → FAKE</text><text x="262" y="164" fill="#22d3ee" font-size="11" text-anchor="middle">z &gt; 0 → TRUE</text>
    <text x="318" y="68" fill="#8fa0c4" font-size="10" text-anchor="end">P(TRUE)</text></svg>`;
}
function renderTech() {
  if (!METRICS || !MODEL_INFO) return;
  const m = METRICS, d = m.dataset, mi = MODEL_INFO, sp = d.split, G = m.generalization, rb = {recall_FAKE: G.configs[G.chosen].recall_FAKE_mean};
  const topF = Math.max(...Object.values(d.top_domains.FAKE)), topT = Math.max(...Object.values(d.top_domains.TRUE));
  const steps = [['scan', 'Você insere a notícia', 'Título e texto vão para o servidor local desta aplicação; o texto não é armazenado.'],
    ['eraser', 'Pré-processamento', 'Minúsculas, normalização de aspas e URLs, 200 primeiras palavras. Pontuação e negações ficam.'],
    ['layers', 'Vetorização TF-IDF', 'Cada termo vira um peso numérico (unigramas e bigramas).'],
    ['cpu', 'Classificação', 'Regressão Logística: soma de pesos × coeficientes + intercepto → probabilidade.'],
    ['chart', 'Resultado', 'Classe de maior probabilidade e margem do classificador.'],
    ['spark', 'Explicabilidade', 'Termos e contribuições que levaram à decisão.']];
  const tt = arr => arr.slice(0, 6).map(x => `<span class="chip">${esc(x.term)}</span>`).join('');
  $('#techBody').innerHTML = `
  <div class="flow" role="list">${steps.map(([i, t, p], k) => `<div class="fstep" role="listitem"><span class="ico">${ic(i)}</span><div><span class="k">Etapa ${k + 1}</span><h3>${t}</h3></div><p>${p}</p></div>`).join('')}</div>
  <div class="tech-grid">
    <article class="card"><h3>${ic('layers')} TF-IDF: palavras viram números</h3>
      <p><b>TF-IDF</b> (<i>Term Frequency–Inverse Document Frequency</i>) transforma texto em um vetor numérico, com uma posição para cada termo do vocabulário. Computadores não leem palavras; eles calculam sobre números.</p>
      <p><b>TF</b> mede quantas vezes o termo aparece no texto. <b>IDF</b> mede o quanto ele é raro no conjunto de notícias: termos presentes em quase todos os textos (como “o”) recebem peso baixo; termos mais específicos recebem peso alto. O produto indica a relevância do termo naquele documento.</p>
      <div class="formula">tf-idf(t, d) = tf(t, d) × idf(t)<br>idf(t) = ln((1 + N) / (1 + df(t))) + 1</div>
      <p>Em notícias, isso destaca marcas de estilo que distinguem um texto do outro sem listas de palavras escritas à mão, e combina bem com modelos lineares, fáceis de interpretar.</p>
      <div class="scroll-x ttbl"><table class="tbl"><thead><tr><th>Termo</th><th class="n">tf</th><th class="n">df</th><th class="n">idf</th><th class="n">tf × idf</th></tr></thead><tbody>${toyTfidf()}</tbody></table></div>
      <p class="tiny muted">Exemplo didático simplificado (3 frases curtas, valores do texto “o governo não aprovou a medida”). O modelo real usa tf sublinear (1 + ln tf), bigramas e normalização L2.</p>
      <div class="facts two"><div><b>${num(mi.n_features)}</b>atributos no vocabulário</div><div><b>${mi.ngram_range[0]}–${mi.ngram_range[1]} palavras</b>unigramas e bigramas</div></div>
    </article>
    <article class="card"><h3>${ic('cpu')} Regressão Logística: do número à classe</h3>
      <p>A <b>Regressão Logística</b> é um algoritmo de classificação que aprende um coeficiente (peso) para cada termo. Coeficiente positivo aproxima o texto da classe TRUE; negativo, da classe FAKE. Ela usa como entrada os valores TF-IDF do texto.</p>
      <div class="formula">z = b + w₁·x₁ + w₂·x₂ + … + wₙ·xₙ<br>P(TRUE) = 1 / (1 + e<sup>−z</sup>) &nbsp; P(FAKE) = 1 − P(TRUE)</div>
      <p>A soma <b>z</b> é convertida em probabilidade pela função logística: z = 0 equivale a 50%; z positivo indica mais de 50% para TRUE; z negativo, mais de 50% para FAKE. A classificação final é a classe de maior probabilidade.</p>
      ${sigmoidSvg()}
      <div class="facts two"><div><b>${num(mi.n_nonzero_coefs)}</b>coeficientes aprendidos</div><div><b>C = ${num(mi.C)}</b>regularização (classes balanceadas)</div></div>
      <p class="tiny muted">Termos de maior coeficiente neste modelo (associações do corpus, não provas):</p><div class="chips" style="margin-top:6px"><span class="tag fake">FAKE</span>${tt(m.top_terms.FAKE)}</div><div class="chips" style="margin-top:8px"><span class="tag true">TRUE</span>${tt(m.top_terms.TRUE)}</div>
    </article>
    <article class="card"><h3>${ic('clock')} Como o modelo aprende</h3>
      <p>O treinamento é <b>supervisionado</b>: o modelo recebe notícias já classificadas como FAKE ou TRUE, calcula a probabilidade com os coeficientes atuais, mede o erro (perda logística) e ajusta os coeficientes para reduzi-lo. Um termo frequente em um grupo e raro no outro termina com coeficiente mais forte.</p>
      <p>A regularização (C) impede que o modelo apenas decore os exemplos. Por isso os dados são separados em três partes:</p>
      <div class="facts"><div><b>${num(sp['treino'].n)}</b>treino: ajustam os coeficientes</div><div><b>${num(sp['validação'].n)}</b>validação: escolhe configurações</div><div><b>${num(sp['teste'].n)}</b>teste: avaliação final, usada uma vez</div></div>
      <p class="tiny muted">Ao analisar uma notícia, o modelo <b>não aprende nada novo</b>: apenas aplica os coeficientes já treinados, carregados do arquivo exportado.</p>
    </article>
    <article class="card"><h3>${ic('info')} O papel do Fake.br Corpus</h3>
      <p>O <b>Fake.br Corpus</b> (Monteiro et al., 2018) é a base rotulada que ensinou o modelo: notícias em português do Brasil classificadas como FAKE ou TRUE, pareadas por categoria e publicadas principalmente entre 2015 e 2018.</p>
      <div class="facts"><div><b>${num(d.n_raw)}</b>notícias originais</div><div><b>${num(d.n_removed_duplicates)}</b>duplicatas removidas</div><div><b>${num(d.class_counts_clean.FAKE)} / ${num(d.class_counts_clean.TRUE)}</b>FAKE / TRUE usadas</div></div>
      <p>Como o modelo só conhece esse corpus, ele aprende também suas particularidades: ${pct(topF, 0)} das FAKE vêm de um único site e ${pct(topT, 0)} das TRUE do g1.</p>
    </article>
    <article class="card note-card wide"><h3>${ic('alert')} O que o VERITAS AI não faz</h3><ul>
      <li>Não consulta fontes nem verifica fatos: ele compara o <b>estilo</b> do texto com os padrões do corpus de treino.</li>
      <li>No teste isolado, a acurácia foi de ${pct(m.test.accuracy, 1)}; mas, deixando uma fonte inteira de fora do treino, o recall médio de FAKE foi de ${pct(rb.recall_FAKE, 1)}. Em fontes e épocas diferentes o desempenho pode ser bem menor, e por isso o sistema pode responder <b>inconclusivo</b>.</li>
      <li>Use o resultado como apoio à leitura crítica, nunca como veredito. Veja os detalhes no <a class="learn" href="#dashboard">dashboard de inteligência</a>.</li></ul></article>
  </div>`;
}

/* ---------- init ---------- */
updateCounter(); route(); loadMetrics();
})();
