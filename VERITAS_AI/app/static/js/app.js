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
  const items = [[pct(t.accuracy), 'Acurácia no teste isolado'], [pct(t.f1_macro), 'F1 macro no teste'], [num(META.training_set_size), 'Notícias no treinamento'], [num(t.n), 'Notícias no teste']];
  $('#homeKpis').innerHTML = items.map(([v, l]) => `<div class="kpi"><div class="v">${v}</div><div class="l">${l}</div></div>`).join('');
}

/* ---------- contador / validação ---------- */
const words = s => (s.match(/\S+/g) || []).length;
function updateCounter() { const v = $('#text').value; $('#counter').textContent = `${num(v.length)} caracteres · ${num(words(v))} palavras`; if (v.trim()) $('#err').textContent = ''; }
$('#text').addEventListener('input', updateCounter);
$('#btnClear').addEventListener('click', () => { $('#title').value = ''; $('#text').value = ''; updateCounter(); $('#err').textContent = ''; $('#text').focus(); });
const EXAMPLES = [
  {title: 'Exemplo demonstrativo A (texto sintético)', text: 'URGENTE!!! Compartilhe antes que apaguem! Políticos tentam esconder a verdade e a mídia não quer que você saiba o que aconteceu hoje. Divulgue para todos os seus contatos, o Brasil precisa acordar! Isso é um absurdo e ninguém fala nada sobre o assunto. Passe adiante agora mesmo, porque eles querem que você fique calado e não descubra o que realmente está acontecendo por trás dos bastidores do poder.'},
  {title: 'Exemplo demonstrativo B (texto sintético)', text: 'O Ministério da Fazenda informou nesta quarta-feira que a arrecadação federal cresceu no trimestre, segundo dados divulgados pela Receita. De acordo com o órgão, o resultado foi puxado pela retomada da atividade econômica, mas a pasta não detalhou projeções para os próximos meses. Em nota, a Receita afirmou que os números ainda serão consolidados e que uma nova divulgação está prevista para o início do próximo período.'}
];
let exIdx = 0;
$('#btnExample').addEventListener('click', () => { const e = EXAMPLES[exIdx++ % EXAMPLES.length]; $('#title').value = e.title; $('#text').value = e.text; updateCounter(); toast('Exemplo sintético carregado — não pertence ao corpus.'); });

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

function renderResult(r, text, title) {
  const pF = r.probabilities.FAKE, pT = r.probabilities.TRUE, isF = r.label === 'FAKE';
  const [nivel, expl] = margemInfo(r.margin), ind = r.indicators;
  const ece = METRICS ? dec(METRICS.test.ece, 3) : '—';
  const toks = text.split(/(\s+)/); let cnt = 0, shown = '';
  toks.forEach(t => { if (/\S/.test(t)) { cnt++; shown += cnt > 200 ? `<span class="cut">${esc(t)}</span>` : esc(t); } else shown += esc(t); });
  $('#resultPane').innerHTML = `
  <div class="card stack">
    <div class="res-head"><span class="tag ${isF ? 'fake' : 'true'}">${r.label}</span><div class="verdict">${esc(r.label_pt)}</div></div>
    <p class="muted" style="font-size:13.5px">Estimativa do classificador sobre <b>padrões de linguagem</b> — não é verificação dos fatos.</p>
    <div class="probs">
      <div class="pbar" role="img" aria-label="Probabilidade FAKE ${pctp(pF)}, TRUE ${pctp(pT)}"><i class="f" style="width:0" data-w="${pF * 100}"></i><i class="t" style="width:0" data-w="${pT * 100}"></i></div>
      <div class="plabels"><span class="f" data-tip="Probabilidade estimada pelo modelo de o texto pertencer à classe FAKE do corpus de treino.">FAKE ${pctp(pF)}</span><span class="t" data-tip="Probabilidade estimada pelo modelo de o texto pertencer à classe TRUE do corpus de treino.">TRUE ${pctp(pT)}</span></div>
    </div>
    <div class="gauge"><div><b>Margem do classificador: ${nivel}</b> (${pct(r.margin, 0)} de diferença entre as classes)</div>
      <div class="meter"><i style="width:0" data-w="${r.margin * 100}"></i></div>
      <div>${expl} <b>Isto não é certeza factual</b>: as probabilidades <u>não foram calibradas formalmente</u> (erro de calibração esperado no teste: ${ece}) e valem para textos parecidos com os do corpus.</div></div>
    ${r.warnings.map(w => `<div class="warnbox">${ic('alert')}<div>${esc(w)}</div></div>`).join('')}
    ${whySection(r)}
    <div class="inds">
      <div class="ind"><b>${num(ind.palavras)}</b><span>palavras</span></div>
      <div class="ind"><b>${ind.exclamacoes}</b><span>exclamações</span></div>
      <div class="ind"><b>${ind.interrogacoes}</b><span>interrogações</span></div>
      <div class="ind"><b>${pct(ind.proporcao_maiusculas, 0)}</b><span>letras maiúsculas</span></div>
    </div>
    <p class="tiny muted">Indicadores descritivos do texto (contagens simples); não são entradas diretas do modelo.</p>
    <details class="txt"><summary>Texto analisado${title ? ' — ' + esc(title) : ''}</summary><div class="body">${shown}</div>${ind.texto_truncado ? '<p class="tiny muted">Trecho esmaecido: fora das 200 primeiras palavras, não analisado.</p>' : ''}</details>
    <div class="meta-line"><span>Modelo: ${esc(r.model.model_name)}</span><span>· v${esc(r.model.version)}</span><span>· treinado em ${esc(String(r.model.trained_at).slice(0, 10))}</span></div>
    <div class="warnbox">${ic('info')}<div><b>Limitações.</b> O modelo aprendeu padrões do <i>Fake.br Corpus</i> (principalmente 2015–2018, fontes concentradas). Pode errar com notícias de outras fontes, épocas ou estilos, e não consulta fontes nem checa fatos. Use como apoio à leitura crítica, nunca como veredito.</div></div>
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
  box.innerHTML = '<div class="hist">' + h.map(i => `<button class="card hitem" data-id="${i.id}"><span class="t">${esc(i.title)}</span><span class="tag ${i.label === 'FAKE' ? 'fake' : 'true'}">${i.label}</span><span class="d">${new Date(i.ts).toLocaleString('pt-BR')}</span><span class="d">modelo v${esc(i.model)}</span><span class="p"><span style="color:var(--fake)">FAKE ${pctp(i.probs.FAKE)}</span><span style="color:var(--true)">TRUE ${pctp(i.probs.TRUE)}</span></span></button>`).join('') + '</div><div id="histDetail"></div>';
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
  const rb = m.robustness, sh = rb.source_holdout, lo = rb.length_only_baseline_val;
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
    <div class="card wide note-card"><h3>${ic('alert')} Leitura crítica do desempenho</h3><ul>
      <li>Um classificador que usa <b>apenas o número de palavras</b> alcança ${pct(lo.f1_macro_val)} de F1 macro na validação: parte do desempenho vem de um atalho do corpus (as notícias TRUE são bem mais longas).</li>
      <li>Treinando só com o par de fontes dominante (${esc(sh.train_domains.join(' + '))}) e testando em outras fontes, o recall cai para <b>${pct(sh.recall_FAKE)}</b> (FAKE) e <b>${pct(sh.recall_TRUE)}</b> (TRUE): as métricas do teste principal <b>superestimam</b> o desempenho em fontes novas.</li>
      <li>Corpus de 2015–2018 com fontes concentradas: ${pct(Math.max(...Object.values(d.top_domains.FAKE)))} das FAKE vêm de um único site.</li>
      <li>As probabilidades não são calibradas formalmente. O sistema classifica estilo; <b>não verifica fatos</b>.</li></ul></div>
  </div></div>`;
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
  const m = METRICS, d = m.dataset, mi = MODEL_INFO, sp = d.split, rb = m.robustness.source_holdout;
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
      <li>No teste isolado, a acurácia foi de ${pct(m.test.accuracy, 1)}; mas, treinando com um par de fontes e testando em outras, o recall de FAKE caiu para ${pct(rb.recall_FAKE, 1)}. Em textos de fontes e épocas diferentes, o desempenho pode ser bem menor.</li>
      <li>Use o resultado como apoio à leitura crítica, nunca como veredito. Veja os detalhes no <a class="learn" href="#dashboard">dashboard de inteligência</a>.</li></ul></article>
  </div>`;
}

/* ---------- init ---------- */
updateCounter(); route(); loadMetrics();
})();
