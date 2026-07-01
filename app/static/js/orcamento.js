'use strict';

// ── Settings injetados pelo template ─────────────────────────────────────────
const S = () => window.SETTINGS;

// ── Estado global ─────────────────────────────────────────────────────────────
let performers    = [];
let coordQty      = 1;
let forasp        = false;
let kmIda         = 0;
let transportTipo = 'carro';
let comCarretinha = false;
let numCarros     = 1;
let colabOverride  = null;  // null = auto
let acrescimo      = 0;        // legado (não usado; mantido p/ compat de reset/reabertura)
let acrescimoTipo  = 'valor';  // legado

// ── Acréscimos tipados (feature 099) ─────────────────────────────────────────
function readOrcAcrescimos() {
  const list = document.getElementById('orc-acrescimos-list');
  if (!list) return [];
  return [...list.querySelectorAll('.orc-acr-row')].map(row => ({
    tipo: (row.querySelector('.acr-tipo') || {}).value || '',
    descricao: (row.querySelector('.acr-desc') || {}).value || '',
    isPercent: (row.querySelector('.acr-unit') || {}).value === '1',
    value: parseFloat(((row.querySelector('.acr-value') || {}).value || '0').replace(/\./g, '').replace(',', '.')) || 0,
  })).filter(a => a.tipo && a.value);
}
function acrescimoAddFor(base) {
  let add = 0;
  for (const a of readOrcAcrescimos()) add += a.isPercent ? base * a.value / 100 : a.value;
  return add;
}
let showSosiaCustom = false;
let notaFiscal     = false;
let modoEntradas   = false;
let prevOnlyDJ     = false;
let duracaoCustom  = 0;
let personalizadoAtivo    = false;
let personalizadoCriterio = 'valor_final'; // 'valor_final' | 'multiplicador'
let custMult       = [0, 0, 0, 0];
let custValor      = [0, 0, 0, 0];

// ── Formatação ────────────────────────────────────────────────────────────────
const BRL = new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' });
const fmt = (v) => BRL.format(v);

// ── Lógica de negócio ─────────────────────────────────────────────────────────
function eventFlags() {
  let show = false, makeup = false, makesReg = 0, makesEsp = 0;
  const sempShow = new Set(window.ESPECIAIS_SEMPRE_SHOW || []);
  for (const p of performers) {
    if ((p.type === 'ator' && p.show) ||
        (p.type === 'especial' && (p.show || p.cantor || sempShow.has(p.personagem))) ||
        p.type === 'cantor' /* legado */)
      show = true;
    if ((p.type === 'ator' || p.type === 'cantor' || p.type === 'especial') && p.makeup) {
      makeup = true;
      p.makeup_tipo === 'especial' ? makesEsp++ : makesReg++;
    }
  }
  return { show, makeup, makesReg, makesEsp };
}

function maquiadorCost(reg, esp) {
  const m = S().maquiador;
  let t = esp * m.make_especial;
  if (reg >= 1) t += m.make_1;
  if (reg >= 2) t += m.make_2_adicional;
  if (reg >= 3) t += (reg - 2) * m.make_extra_adicional;
  return t;
}

function isNoturno() {
  const el = document.querySelector('[name=event_time]');
  if (!el || !el.value) return false;
  return parseInt(el.value.split(':')[0], 10) >= 19;
}

function isOnlyDJ() {
  return performers.length > 0 && performers.every(p => p.type === 'especial' && p.personagem === 'DJ');
}

function minCoord() {
  if (isOnlyDJ()) return 0;
  const regras = S().especiais_regras || {};
  let min = 1;
  for (const p of performers) {
    if (p.type === 'especial') {
      min = Math.max(min, (regras[p.personagem] || {}).min_coordenadores || 1);
    }
  }
  return min;
}

function autoColab() {
  const { show } = eventFlags();
  return coordQty + performers.length + (show ? 1 : 0);
}

function transportBreakdown() {
  if (!forasp || kmIda <= 0) return null;
  const { show } = eventFlags();
  const t    = S().transporte;
  const kmT  = kmIda * 2;
  const colab = colabOverride !== null ? colabOverride : autoColab();
  const tarifa = transportTipo === 'van'
    ? (comCarretinha ? t.van_com_carretinha : t.van_sem_carretinha)
    : null;
  const vt   = transportTipo === 'van'
    ? kmT * tarifa
    : numCarros * t.carro_por_km * kmT;
  const afsp  = (colab * kmT) / t.afsp_divisor;
  const ashow = (show && kmT > t.ashow_min_km) ? kmT / t.ashow_divisor : 0;
  return { kmT, colab, vt, afsp, ashow, total: vt + afsp + ashow, tarifa };
}

function transportCost() {
  const tb = transportBreakdown();
  return tb ? tb.total : 0;
}

// Cachê-base (pré-markup): artistas + coordenador + show customizado.
// É a base do orçamento personalizado por multiplicador.
function cacheBase() {
  const { show } = eventFlags();
  const cfg   = S();
  const cache = [0, 0, 0, 0];

  for (const p of performers) {
    let prices;
    if (p.type === 'ator') {
      if (p.subtipo === 'cantor') {
        const c = cfg.cantor;
        prices = c.base.map((v, i) =>
          v + (p.show ? c.show_extra[i] : 0) + (p.makeup ? c.make_extra[i] : 0)
        );
      } else {
        const key = `${p.subtipo}|${p.show}|${p.makeup}`;
        prices = cfg.ator[key] || [0, 0, 0, 0];
      }
    } else if (p.type === 'cantor') {
      // legado: cantor era tipo separado, sempre com show
      const c = cfg.cantor;
      prices = c.base.map((v, i) => v + c.show_extra[i] + (p.makeup ? c.make_extra[i] : 0));
    } else if (p.type === 'especial') {
      const ep = cfg.especiais[p.personagem];
      const comCantor = new Set(window.ESPECIAIS_COM_CANTOR || []);
      if (!ep) { prices = [0, 0, 0, 0]; }
      else if (Array.isArray(ep)) { prices = ep; }
      else if (comCantor.has(p.personagem) && p.cantor) { prices = ep['cantor'] || [0, 0, 0, 0]; }
      else if (p.show) { prices = ep['show'] || ep['true'] || [0, 0, 0, 0]; }
      else { prices = ep['none'] || ep['false'] || [0, 0, 0, 0]; }
    } else {
      prices = [0, 0, 0, 0];
    }
    for (let i = 0; i < 4; i++) cache[i] += prices[i];
  }

  // Coordenador
  const cp = cfg.coordenador[String(show)] || [0, 0, 0, 0];
  for (let i = 0; i < 4; i++) cache[i] += cp[i] * coordQty;

  // Show customizado: +R$50 por artista (não inclui coord, técnico, maquiador)
  if (showSosiaCustom && performers.length > 0) {
    const customAdd = performers.length * 50;
    for (let i = 0; i < 4; i++) cache[i] += customAdd;
  }

  return cache;
}

function calcTotals() {
  const { show, makeup, makesReg, makesEsp } = eventFlags();
  const cfg   = S();
  const cache = cacheBase();

  // Orçamento personalizado: total final = valor digitado ou base × multiplicador.
  // Nada é somado depois (transporte/NF/extras ficam fora).
  if (personalizadoAtivo) {
    if (personalizadoCriterio === 'multiplicador') {
      return [0, 1, 2, 3].map(i => Math.round(cache[i] * (custMult[i] || 0) * 100) / 100);
    }
    return [0, 1, 2, 3].map(i => Math.round((custValor[i] || 0) * 100) / 100);
  }

  // Markup
  const markup = cfg.markup[show ? 'show' : 'receptivo'];
  const t = cache.map((v, i) => v * markup[i]);

  // Brinde (pós-markup)
  if (show) {
    const brinde = cfg.brinde_show ?? 100;
    for (let i = 0; i < 4; i++) t[i] += brinde;
  }

  // Adicional noturno (pós-markup)
  if (isNoturno()) {
    const notAdd = (performers.length + coordQty) * 50;
    for (let i = 0; i < 4; i++) t[i] += notAdd;
  }

  // Técnico de Som (pós-markup, 1.5×)
  if (show) {
    for (let i = 0; i < 4; i++) t[i] += Math.round(cfg.tecnico_som[i] * 1.5 * 100) / 100;
  }

  // Maquiador (pós-markup, 1.5×)
  if (makeup) {
    const mc = maquiadorCost(makesReg, makesEsp);
    for (let i = 0; i < 4; i++) t[i] += Math.round(mc * 1.5 * 100) / 100;
  }

  // Transporte especial pós-markup — uma vez por tipo
  const regras = cfg.especiais_regras || {};
  const seenTransport = new Set();
  for (const p of performers) {
    if (p.type === 'especial' && !seenTransport.has(p.personagem)) {
      const tEsp = (regras[p.personagem] || {}).transporte_especial || 0;
      if (tEsp) {
        for (let i = 0; i < 4; i++) t[i] += tEsp;
        seenTransport.add(p.personagem);
      }
    }
  }

  // BGE: acréscimo por sub-tipo (por unidade, pós-markup)
  for (const p of performers) {
    if (p.type === 'especial' && p.personagem === 'Boneco Grande Especial') {
      const bgeExtra = p.bge_subtipo === 'dinossauro'   ? 130
                     : p.bge_subtipo === 'transformers' ? 70
                     : 0;
      if (bgeExtra > 0) {
        for (let i = 0; i < 4; i++) t[i] = Math.round((t[i] + bgeExtra) * 100) / 100;
      }
    }
  }

  // Transporte (pós-markup)
  const tc = transportCost();
  for (let i = 0; i < 4; i++) t[i] += tc;

  // Acréscimos tipados (feature 099): percentuais sobre o total pré-acréscimos; R$ somam.
  for (let i = 0; i < 4; i++) {
    t[i] = Math.round((t[i] + acrescimoAddFor(t[i])) * 100) / 100;
  }

  // Nota Fiscal (÷ 0,84)
  if (notaFiscal) {
    for (let i = 0; i < 4; i++) {
      t[i] = Math.round((t[i] / 0.84) * 100) / 100;
    }
  }

  return t;
}

// ── UI ────────────────────────────────────────────────────────────────────────
function update() {
  const minC   = minCoord();
  const onlyDJ = isOnlyDJ();

  // Transição → DJ-only: zera coordenador automaticamente
  if (onlyDJ && !prevOnlyDJ) {
    coordQty = 0;
  } else if (!onlyDJ && prevOnlyDJ && coordQty === 0) {
    // Saiu de DJ-only com coordenador zerado: restaura o mínimo
    coordQty = Math.max(1, minC);
  } else if (coordQty < minC) {
    coordQty = minC;
  }
  prevOnlyDJ = onlyDJ;

  document.getElementById('coord-qty').textContent = coordQty;
  document.getElementById('coordenador_qty').value  = coordQty;

  renderPerformers();
  updateAutoServices();
  updateTotals();
  updateDebugPanel();
  updateCacheBaseReadout();
  syncColabField();
}

function updateTotals() {
  const [t1, t2, t3, t4] = calcTotals();
  document.getElementById('total-1h').textContent = fmt(t1);
  document.getElementById('total-2h').textContent = fmt(t2);
  document.getElementById('total-3h').textContent = fmt(t3);
  document.getElementById('total-4h').textContent = fmt(t4);

  const customWrap = document.getElementById('total-custom-wrap');
  if (customWrap && !personalizadoAtivo && duracaoCustom > 0 && ![1, 2, 3, 4].includes(duracaoCustom)) {
    const tCustom = Math.round(t4 / 4 * duracaoCustom * 100) / 100;
    document.getElementById('total-custom').textContent = fmt(tCustom);
    const lblEl = document.getElementById('lbl-custom');
    if (lblEl) lblEl.textContent = modoEntradas
      ? `${duracaoCustom * 2} entradas`
      : `${duracaoCustom} horas`;
    customWrap.style.display = '';
  } else if (customWrap) {
    customWrap.style.display = 'none';
  }
}

function setDuracaoCustom(val) {
  duracaoCustom = (isNaN(val) || val < 0) ? 0 : val;
  updateTotals();
  updateDebugPanel();
}

function updateAutoServices() {
  const { show, makeup, makesReg, makesEsp } = eventFlags();

  // Label do coordenador
  const coordLbl = document.getElementById('coord-obrig-label');
  if (coordLbl) {
    const onlyDJ = isOnlyDJ();
    coordLbl.textContent = onlyDJ ? 'opcional para DJ' : 'sempre obrigatório';
    coordLbl.style.color = onlyDJ ? 'var(--blue)' : 'var(--muted)';
  }

  document.getElementById('auto-tecnico').style.display = show ? '' : 'none';

  const hasBGE   = performers.some(p => p.type === 'especial' && p.personagem === 'Boneco Grande Especial');
  const bgeWarn  = document.getElementById('bge-warning');
  if (bgeWarn) bgeWarn.style.display = hasBGE ? '' : 'none';

  const hasSosia = performers.some(p => p.type === 'especial' && SOSIA_TYPES.has(p.personagem));
  const sosiaPanel = document.getElementById('sosia-show-panel');
  if (sosiaPanel) {
    sosiaPanel.style.display = hasSosia ? '' : 'none';
    if (!hasSosia && showSosiaCustom) {
      showSosiaCustom = false;
      const el = document.getElementById('sosia-predefinido');
      if (el) el.checked = true;
    }
  }

  const maqDiv = document.getElementById('auto-maquiador');
  if (makeup) {
    const total = makesReg + makesEsp;
    document.getElementById('maquiador-detail').textContent =
      `${total} make${total !== 1 ? 's' : ''} — ${fmt(maquiadorCost(makesReg, makesEsp))}`;
    maqDiv.style.display = '';
  } else {
    maqDiv.style.display = 'none';
  }
}

function syncColabField() {
  const { makeup } = eventFlags();
  const warn = document.getElementById('colab-makeup-warn');
  if (warn) warn.style.display = makeup ? '' : 'none';
  if (colabOverride !== null) return;
  const input = document.getElementById('num_colaboradores');
  if (input) input.value = autoColab();
}

function updateDebugPanel() {
  const tbody = document.getElementById('debug-tbody');
  const tfoot = document.getElementById('debug-tfoot');
  const thead = document.getElementById('debug-thead');
  if (!tbody || !tfoot) return;

  // Modo personalizado: memória simplificada (sem markup/extras automáticos).
  if (personalizadoAtivo) {
    const base   = cacheBase();
    const totals = calcTotals();
    if (thead) {
      thead.innerHTML = `<tr><th>Item</th>
        <th style="text-align:right;">1h</th>
        <th style="text-align:right;">2h</th>
        <th style="text-align:right;">3h</th>
        <th style="text-align:right;">4h</th></tr>`;
    }
    let rows = `<tr style="background:#f1f5f9;"><td><strong>Subtotal Cachê (base)</strong></td>` +
      base.map(v => `<td style="text-align:right;font-weight:600;">${fmt(v)}</td>`).join('') + `</tr>`;
    if (personalizadoCriterio === 'multiplicador') {
      rows += `<tr style="background:#fffbeb;"><td><strong>× Multiplicador</strong> <span style="color:var(--muted)">personalizado</span></td>` +
        custMult.map(v => `<td style="text-align:right;">${(v || 0)}×</td>`).join('') + `</tr>`;
    } else {
      rows += `<tr style="background:#faf5ff;"><td><strong>Valor final</strong> <span style="color:var(--muted)">digitado</span></td>` +
        custValor.map(v => `<td style="text-align:right;">${fmt(v || 0)}</td>`).join('') + `</tr>`;
    }
    rows += `<tr style="background:var(--green-soft);"><td><strong>TOTAL FINAL AO CLIENTE</strong> <span style="color:var(--muted)">(personalizado · sem extras)</span></td>` +
      totals.map(v => `<td style="text-align:right;font-weight:700;">${fmt(v)}</td>`).join('') + `</tr>`;
    tbody.innerHTML = rows;
    tfoot.innerHTML = `<tr style="background:var(--surface);color:var(--muted);">
      <td colspan="4" style="font-size:12px;font-style:italic;">
        Orçamento personalizado — transporte, Nota Fiscal e acréscimos não são somados.
      </td></tr>`;
    return;
  }

  const { show, makeup, makesReg, makesEsp } = eventFlags();
  const cfg    = S();
  const markup = cfg.markup[show ? 'show' : 'receptivo'];
  const markupLabels = markup.map(v => `${v}×`);
  const modeloLabel  = show ? 'Show' : 'Receptivo / Interativo';

  const tCfg = cfg.transporte;
  const tb   = transportBreakdown();
  const perPersonTransport = (tb && kmIda > 0)
    ? Math.round(kmIda * 2 / tCfg.afsp_divisor * 100) / 100
    : 0;

  const showCustomCol = duracaoCustom > 0 && ![1, 2, 3, 4].includes(duracaoCustom);
  const totalCols = 3 + (showCustomCol ? 1 : 0);

  if (thead) {
    thead.innerHTML = `<tr>
      <th>Profissional</th>
      <th style="text-align:right;">Cachê 1h</th>
      <th style="text-align:right;">Cachê 2h</th>
      <th style="text-align:right;">Cachê 3h</th>
      <th style="text-align:right;">Cachê 4h</th>
      ${showCustomCol ? `<th style="text-align:right;background:var(--surface-2);">Cachê ${duracaoCustom}h</th>` : ''}
    </tr>`;
  }

  // Nh para itens escaláveis: 4h ÷ 4 × N
  const nhScale = (p4) => Math.round(p4 / 4 * duracaoCustom * 100) / 100;

  // renderCells: nhValue explícito tem precedência; flat=true usa p4; flat=false escala
  function renderCells(basePrices, bold, hlGreen, flat, nhValue) {
    const bst = bold ? 'font-weight:600;' : '';
    let cells = basePrices.map(v =>
      `<td style="text-align:right;${bst}${hlGreen ? 'font-weight:700;' : ''}">${fmt(v)}</td>`
    ).join('');
    if (showCustomCol) {
      let nV;
      if (nhValue !== undefined) { nV = nhValue; }
      else if (flat)             { nV = basePrices[3]; }
      else                       { nV = nhScale(basePrices[3]); }
      cells += `<td style="text-align:right;${bst};background:var(--surface-2);">${fmt(nV)}</td>`;
    }
    return cells;
  }

  // Gera cells iguais para todas as colunas (itens pós-markup de valor fixo)
  function flatCols(value, style = '') {
    const td = (bg) => `<td style="text-align:right;${style}${bg}">${fmt(value)}</td>`;
    return td('') + td('') + td('') + (showCustomCol ? td('background:var(--surface-2);') : '');
  }

  // Gera cells com valor específico por coluna + Nh
  function perCols(vals, nhVal, bold = false) {
    const bst = bold ? 'font-weight:700;' : '';
    let cells = vals.map(v => `<td style="text-align:right;${bst}">${fmt(v)}</td>`).join('');
    if (showCustomCol) cells += `<td style="text-align:right;${bst}background:var(--surface-2);">${fmt(nhVal)}</td>`;
    return cells;
  }

  const rows  = [];
  const cache = [0, 0, 0, 0];
  let cacheNh = 0;

  for (const p of performers) {
    let prices, label;
    if (p.type === 'ator') {
      if (p.subtipo === 'cantor') {
        const c = cfg.cantor;
        prices = c.base.map((v, i) =>
          v + (p.show ? c.show_extra[i] : 0) + (p.makeup ? c.make_extra[i] : 0)
        );
        const parts = ['Cantor'];
        if (p.show)   parts.push('com show');
        if (p.makeup) parts.push('maquiagem');
        label = (p.nome || 'Cantor') + ` <span style="color:var(--muted)">(${parts.join(', ')})</span>`;
      } else {
        const key = `${p.subtipo}|${p.show}|${p.makeup}`;
        prices = cfg.ator[key] || [0, 0, 0, 0];
        const parts = [p.subtipo === 'boneco' ? 'Boneco' : 'Cara Limpa'];
        if (p.show)   parts.push('show');
        if (p.makeup) parts.push(`make ${p.makeup_tipo}`);
        label = (p.nome || 'Ator') + ` <span style="color:var(--muted)">(${parts.join(', ')})</span>`;
      }
    } else if (p.type === 'cantor') {
      const c = cfg.cantor;
      prices = c.base.map((v, i) => v + c.show_extra[i] + (p.makeup ? c.make_extra[i] : 0));
      label  = (p.nome || 'Cantor') + ` <span style="color:var(--muted)">(cantor${p.makeup ? ', make' : ''})</span>`;
    } else if (p.type === 'especial') {
      const ep = cfg.especiais[p.personagem];
      const comCantor  = new Set(window.ESPECIAIS_COM_CANTOR  || []);
      const sempShowD  = new Set(window.ESPECIAIS_SEMPRE_SHOW || []);
      if (!ep) { prices = [0, 0, 0, 0]; }
      else if (Array.isArray(ep)) { prices = ep; }
      else if (comCantor.has(p.personagem) && p.cantor) { prices = ep['cantor'] || [0, 0, 0, 0]; }
      else if (p.show) { prices = ep['show'] || ep['true'] || [0, 0, 0, 0]; }
      else { prices = ep['none'] || ep['false'] || [0, 0, 0, 0]; }
      const parts = [p.personagem];
      if (p.cantor) parts.push('cantor');
      else if (p.show) parts.push('show');
      else if (sempShowD.has(p.personagem)) parts.push('técnico incluso');
      label = (p.nome || p.personagem) + ` <span style="color:var(--muted)">(${parts.join(', ')})</span>`;
    } else {
      prices = [0, 0, 0, 0]; label = p.nome || '?';
    }
    rows.push({ label, prices, flat: false });
    for (let i = 0; i < 4; i++) cache[i] += prices[i];
    cacheNh += nhScale(prices[3]);
  }

  const cp = cfg.coordenador[String(show)] || [0, 0, 0, 0];
  const coordPrices = cp.map(v => v * coordQty);
  rows.push({
    label: `Coordenador(es) (${coordQty}) <span style="color:var(--muted)">${show ? 'com show' : 'sem show'}</span>`,
    prices: coordPrices, flat: false,
  });
  for (let i = 0; i < 4; i++) cache[i] += coordPrices[i];
  cacheNh += nhScale(coordPrices[3]);

  if (showSosiaCustom && performers.length > 0) {
    const customAdd = performers.length * 50;
    rows.push({ label: `Show Customizado <span style="color:var(--muted)">(${performers.length} artista${performers.length !== 1 ? 's' : ''} × R$50)</span>`, prices: [customAdd, customAdd, customAdd, customAdd], flat: true });
    for (let i = 0; i < 4; i++) cache[i] += customAdd;
    cacheNh += customAdd;
  }

  // Adicional Transporte — informativo pré-markup (azul, NÃO entra em cache[] nem em cacheNh)
  if (tb) {
    rows.push({
      label: `Adicional Transporte (fora SP) <span style="color:var(--muted)">(${tb.colab} pessoas × ${fmt(perPersonTransport)}/pessoa)</span>`,
      prices: [tb.afsp, tb.afsp, tb.afsp, tb.afsp],
      flat: true,
      hl: 'transport',
    });
  }

  // Paleta de cores por categoria
  const C_PRE  = '#fffef5'; // pré-markup: creme (entra no cache, afetado pelo markup)
  const C_INFO = '#eff6ff'; // informativo: azul (transporte fora SP, não entra no cache)
  const C_SBTL = '#f1f5f9'; // subtotal: cinza neutro
  const C_MKP  = '#fffbeb'; // markup: âmbar
  const C_POST = '#faf5ff'; // pós-markup: lilás (adicionais após markup)
  const C_TOT  = 'var(--green-soft)'; // total final: verde

  const subtotalNh = showCustomCol ? Math.round(cacheNh * 100) / 100 : undefined;
  rows.push({ label: '<strong>Subtotal Cachê</strong>', prices: [...cache], bold: true, nhValue: subtotalNh, hl: 'subtotal' });

  const afterMarkup  = cache.map((v, i) => v * markup[i]);
  const afterMarkupNh = showCustomCol ? Math.round(cacheNh * markup[3] * 100) / 100 : undefined;
  rows.push({
    label: `<strong>× Markup</strong> <span style="color:var(--muted)">${modeloLabel} — ${markupLabels.join(' / ')}</span>`,
    prices: afterMarkup, bold: true, hl: 'warning', nhValue: afterMarkupNh,
  });

  // Legenda de cores
  const legend = `<tr><td colspan="${totalCols + 1}" style="padding:4px 0 10px;">
    <span style="display:inline-flex;gap:16px;align-items:center;flex-wrap:wrap;font-size:11px;color:var(--muted);">
      <span style="display:inline-flex;align-items:center;gap:4px;"><span style="display:inline-block;width:10px;height:10px;background:${C_PRE};border:1px solid #e5e7eb;border-radius:2px;margin-top:1px;"></span>Afetado pelo markup</span>
      <span style="display:inline-flex;align-items:center;gap:4px;"><span style="display:inline-block;width:10px;height:10px;background:${C_MKP};border:1px solid #fde68a;border-radius:2px;margin-top:1px;"></span>Markup</span>
      <span style="display:inline-flex;align-items:center;gap:4px;"><span style="display:inline-block;width:10px;height:10px;background:${C_POST};border:1px solid #ddd6fe;border-radius:2px;margin-top:1px;"></span>Pós-markup</span>
      <span style="display:inline-flex;align-items:center;gap:4px;"><span style="display:inline-block;width:10px;height:10px;background:${C_INFO};border:1px solid #bfdbfe;border-radius:2px;margin-top:1px;"></span>Informativo (não entra no cache)</span>
    </span>
  </td></tr>`;

  let html = legend + rows.map(r => {
    const bg =
      r.hl === 'warning'   ? C_MKP  :
      r.hl === 'transport' ? C_INFO  :
      r.hl === 'subtotal'  ? C_SBTL  :
      C_PRE;
    return `<tr style="background:${bg};">
      <td>${r.label}</td>
      ${renderCells(r.prices, r.bold, false, r.flat, r.nhValue)}
    </tr>`;
  }).join('');

  const running = [...afterMarkup];
  let runningNh = afterMarkupNh || 0;

  if (show) {
    const brinde = cfg.brinde_show ?? 100;
    html += `<tr style="background:${C_POST};"><td>Brinde aniversariante <span style="color:var(--muted)">(pós-markup)</span></td>${flatCols(brinde)}</tr>`;
    for (let i = 0; i < 4; i++) running[i] += brinde;
    runningNh += brinde;
  }

  if (isNoturno()) {
    const notCount = performers.length + coordQty;
    const notAdd = notCount * 50;
    html += `<tr style="background:${C_POST};"><td>Adicional Noturno <span style="color:var(--muted)">(≥ 19h · ${notCount} pessoa${notCount !== 1 ? 's' : ''} × R$50)</span></td>${flatCols(notAdd)}</tr>`;
    for (let i = 0; i < 4; i++) running[i] += notAdd;
    runningNh += notAdd;
  }

  if (show) {
    const tecVals = cfg.tecnico_som.map(v => Math.round(v * 1.5 * 100) / 100);
    const tecNh = showCustomCol ? Math.round(cfg.tecnico_som[3] / 4 * duracaoCustom * 1.5 * 100) / 100 : 0;
    html += `<tr style="background:${C_POST};"><td>Técnico de Som <span style="color:var(--muted)">(pós-markup · 1,5×)</span></td>${perCols(tecVals, tecNh)}</tr>`;
    for (let i = 0; i < 4; i++) running[i] = Math.round((running[i] + tecVals[i]) * 100) / 100;
    if (showCustomCol) runningNh = Math.round((runningNh + tecNh) * 100) / 100;
  }

  if (makeup) {
    const mc = maquiadorCost(makesReg, makesEsp);
    const mcMkp = Math.round(mc * 1.5 * 100) / 100;
    const totalMakes = makesReg + makesEsp;
    html += `<tr style="background:${C_POST};"><td>Maquiador <span style="color:var(--muted)">(${totalMakes} make${totalMakes !== 1 ? 's' : ''} · pós-markup · 1,5×)</span></td>${flatCols(mcMkp)}</tr>`;
    for (let i = 0; i < 4; i++) running[i] = Math.round((running[i] + mcMkp) * 100) / 100;
    if (showCustomCol) runningNh = Math.round((runningNh + mcMkp) * 100) / 100;
  }

  const dbgRegras = cfg.especiais_regras || {};
  const dbgSeenTransport = new Set();
  for (const p of performers) {
    if (p.type === 'especial' && !dbgSeenTransport.has(p.personagem)) {
      const tEsp = (dbgRegras[p.personagem] || {}).transporte_especial || 0;
      if (tEsp) {
        html += `<tr style="background:${C_POST};"><td>Transporte Especial — ${p.personagem} <span style="color:var(--muted)">(pós-markup, único)</span></td>${flatCols(tEsp)}</tr>`;
        for (let i = 0; i < 4; i++) running[i] += tEsp;
        runningNh += tEsp;
        dbgSeenTransport.add(p.personagem);
      }
    }
  }

  // BGE: acréscimo por sub-tipo (por unidade, pós-markup)
  for (const p of performers) {
    if (p.type === 'especial' && p.personagem === 'Boneco Grande Especial') {
      const bgeExtra = p.bge_subtipo === 'dinossauro'   ? 130
                     : p.bge_subtipo === 'transformers' ? 70
                     : 0;
      if (bgeExtra > 0) {
        const bgeNomeDbg = p.bge_subtipo === 'dinossauro' ? 'Dinossauro' : 'Transformers';
        html += `<tr style="background:${C_POST};"><td>BGE ${bgeNomeDbg} <span style="color:var(--muted)">(acréscimo pós-markup)</span></td>${flatCols(bgeExtra)}</tr>`;
        for (let i = 0; i < 4; i++) running[i] = Math.round((running[i] + bgeExtra) * 100) / 100;
        runningNh = Math.round((runningNh + bgeExtra) * 100) / 100;
      }
    }
  }

  if (tb) {
    const veiculoLabel = transportTipo === 'van'
      ? `Van ${comCarretinha ? 'c/ carretinha' : 's/ carretinha'} · R$${tb.tarifa}/km · ${tb.kmT}km`
      : `${numCarros} carro(s) · R$1,90/km × ${numCarros} · ${tb.kmT}km`;
    html += `
      <tr style="background:${C_POST};"><td colspan="${totalCols + 1}" style="font-weight:600;font-size:12px;">Transporte — Fora de SP</td></tr>
      <tr style="background:${C_POST};"><td style="padding-left:16px;">Veículo <span style="color:var(--muted)">(${veiculoLabel})</span></td>${flatCols(tb.vt)}</tr>
      <tr style="background:${C_POST};"><td style="padding-left:16px;">Adicional Fora SP <span style="color:var(--muted)">(${tb.colab} pessoas × ${fmt(perPersonTransport)}/pessoa)</span></td>${flatCols(tb.afsp)}</tr>
      <tr style="background:${C_POST};"><td style="padding-left:16px;">Adicional Show <span style="color:var(--muted)">${tb.ashow > 0 ? `(${tb.kmT}km ÷ 6)` : '(km ≤ 500 ou sem show)'}</span></td>${flatCols(tb.ashow)}</tr>
      <tr style="background:${C_POST};"><td style="font-weight:600;padding-left:16px;">Total Transporte</td>${flatCols(tb.total, 'font-weight:600;')}</tr>`;
    for (let i = 0; i < 4; i++) running[i] += tb.total;
    runningNh += tb.total;
  }

  const _acrs = readOrcAcrescimos();
  if (_acrs.length) {
    const addVals = running.map(v => Math.round(acrescimoAddFor(v) * 100) / 100);
    const addNh   = Math.round(acrescimoAddFor(runningNh) * 100) / 100;
    html += `<tr style="background:${C_POST};"><td><strong>+ Acréscimos</strong> <span style="color:var(--muted)">(${_acrs.length})</span></td>${perCols(addVals, addNh, true)}</tr>`;
    for (let i = 0; i < 4; i++) running[i] = Math.round((running[i] + addVals[i]) * 100) / 100;
    runningNh = Math.round((runningNh + addNh) * 100) / 100;
  }

  if (notaFiscal) {
    const nfAdd   = running.map(v => Math.round((v / 0.84 - v) * 100) / 100);
    const nfAddNh = Math.round((runningNh / 0.84 - runningNh) * 100) / 100;
    html += `<tr style="background:${C_POST};"><td><strong>+ Nota Fiscal</strong> <span style="color:var(--muted)">(÷ 0,84)</span></td>${perCols(nfAdd, nfAddNh, true)}</tr>`;
    for (let i = 0; i < 4; i++) running[i] = Math.round(running[i] / 0.84 * 100) / 100;
    runningNh = Math.round(runningNh / 0.84 * 100) / 100;
  }

  html += `
    <tr style="background:${C_TOT};">
      <td><strong>TOTAL FINAL AO CLIENTE</strong></td>
      ${perCols(running, runningNh, true)}
    </tr>`;

  tbody.innerHTML = html;
  tfoot.innerHTML = `
    <tr style="background:var(--surface);color:var(--muted);">
      <td colspan="${totalCols + 1}" style="font-size:12px;font-style:italic;">
        Markup (${modeloLabel}): 1h × ${markup[0]} · 2h × ${markup[1]} · 3h × ${markup[2]} · 4h × ${markup[3]}
        ${tb ? ` · Transporte total ${fmt(tb.total)}` : ''}
        ${readOrcAcrescimos().length ? ` · Acréscimos (${readOrcAcrescimos().length})` : ''}
        ${notaFiscal ? ' · Nota Fiscal (÷ 0,84)' : ''}
      </td>
    </tr>`;
}

// ── Renderização de profissionais ─────────────────────────────────────────────
function renderPerformers() {
  const container = document.getElementById('performers-list');
  if (!container) return;
  if (performers.length === 0) {
    container.innerHTML = '<p style="font-size:13px;color:var(--muted);font-style:italic;margin-bottom:12px;">Nenhum profissional adicionado.</p>';
    return;
  }
  container.innerHTML = performers.map(buildCard).join('');
}

function buildCard(p, i) {
  const nomeInput = `<input type="text" style="min-width:130px;max-width:180px;" placeholder="Nome do personagem" value="${(p.nome||'').replace(/"/g,'&quot;')}" onchange="setProp(${i},'nome',this.value)">`;

  let controls = '';
  if (p.type === 'ator') {
    const isCantor = p.subtipo === 'cantor';
    const makeupSel = p.makeup ? `<select onchange="setProp(${i},'makeup_tipo',this.value)"><option value="comum" ${p.makeup_tipo!=='especial'?'selected':''}>Comum</option><option value="especial" ${p.makeup_tipo==='especial'?'selected':''}>Especial</option></select>` : '';
    controls = `
      <span class="badge badge-gold">${isCantor ? 'Cantor' : 'Ator'}</span>
      ${nomeInput}
      <select onchange="setSubtipo(${i},this.value)">
        <option value="cara_limpa" ${p.subtipo==='cara_limpa'?'selected':''}>Cara Limpa</option>
        <option value="boneco"     ${p.subtipo==='boneco'?'selected':''}>Boneco</option>
        <option value="cantor"     ${p.subtipo==='cantor'?'selected':''}>Cantor</option>
      </select>
      <label class="chk"><input type="checkbox" ${p.show?'checked':''} onchange="setProp(${i},'show',this.checked)"> Show</label>
      ${!isCantor && p.subtipo==='boneco' ? '' : `<label class="chk"><input type="checkbox" ${p.makeup?'checked':''} onchange="setMakeup(${i},this.checked)"> Maquiagem</label>`}
      ${makeupSel}`;
  } else if (p.type === 'cantor') {
    // Legado — cantor era tipo separado
    const makeupSel = p.makeup ? `<select onchange="setProp(${i},'makeup_tipo',this.value)"><option value="comum" ${p.makeup_tipo!=='especial'?'selected':''}>Comum</option><option value="especial" ${p.makeup_tipo==='especial'?'selected':''}>Especial</option></select>` : '';
    controls = `
      <span class="badge badge-green">Cantor</span>
      ${nomeInput}
      <span style="font-size:12px;color:var(--muted);">(sempre com show)</span>
      <label class="chk"><input type="checkbox" ${p.makeup?'checked':''} onchange="setMakeup(${i},this.checked)"> Maquiagem</label>
      ${makeupSel}`;
  } else if (p.type === 'especial') {
    const especiais    = window.ESPECIAIS_LIST || [];
    const comShowSet   = new Set(window.ESPECIAIS_COM_SHOW || []);
    const comCantorSet = new Set(window.ESPECIAIS_COM_CANTOR || []);
    const sempShowSet  = new Set(window.ESPECIAIS_SEMPRE_SHOW || []);
    const isSempShow   = sempShowSet.has(p.personagem);
    const isBGE        = p.personagem === 'Boneco Grande Especial';
    const opts = especiais.map(e => `<option value="${e}" ${p.personagem===e?'selected':''}>${e}</option>`).join('');
    const showCheck = (!isSempShow && comShowSet.has(p.personagem))
      ? `<label class="chk"><input type="checkbox" ${p.show?'checked':''} onchange="setProp(${i},'show',this.checked)"> Show</label>` : '';
    const cantorCheck = comCantorSet.has(p.personagem)
      ? `<label class="chk"><input type="checkbox" ${p.cantor?'checked':''} onchange="setProp(${i},'cantor',this.checked)"> Cantor</label>` : '';
    const sempNote = isSempShow
      ? `<span style="font-size:11px;color:var(--blue);white-space:nowrap;">🎧 técnico de som incluso</span>` : '';
    const makeupSelEsp = p.makeup ? `<select onchange="setProp(${i},'makeup_tipo',this.value)"><option value="comum" ${p.makeup_tipo!=='especial'?'selected':''}>Comum</option><option value="especial" ${p.makeup_tipo==='especial'?'selected':''}>Especial</option></select>` : '';

    // Sub-tipo exclusivo para BGE
    const sub = p.bge_subtipo || 'dinossauro';
    const bgeOutroInput = sub === 'outro'
      ? `<input type="text" placeholder="Nome do BGE" value="${(p.bge_outro_nome||'').replace(/"/g,'&quot;')}" onchange="setProp(${i},'bge_outro_nome',this.value)" style="min-width:120px;max-width:180px;">`
      : '';
    const bgeControls = isBGE ? `
      <select onchange="setBgeSubtipo(${i},this.value)" style="max-width:175px;">
        <option value="dinossauro"   ${sub==='dinossauro'?'selected':''}>Dinossauro (+R$130)</option>
        <option value="transformers" ${sub==='transformers'?'selected':''}>Transformers (+R$70)</option>
        <option value="outro"        ${sub==='outro'?'selected':''}>Outro</option>
      </select>${bgeOutroInput}` : '';

    controls = `
      <span class="badge badge-blue">Especial</span>
      ${isBGE ? '' : nomeInput}
      <select onchange="setPersonagem(${i},this.value)">${opts}</select>
      ${showCheck}
      ${cantorCheck}
      ${sempNote}
      ${bgeControls}
      <label class="chk"><input type="checkbox" ${p.makeup?'checked':''} onchange="setMakeup(${i},this.checked)"> Maquiagem</label>
      ${makeupSelEsp}`;
  }

  return `
    <div class="performer-row">
      ${controls}
      <button type="button" class="btn btn-danger btn-sm" style="margin-left:auto;" onclick="removePerformer(${i})">✕</button>
    </div>`;
}

// ── Ações ─────────────────────────────────────────────────────────────────────
// choice (opcional): subtipo do ator ('cara_limpa'|'boneco'|'cantor') ou nome do especial.
function addPerformer(type, choice) {
  const p = { type, show: false, makeup: false, makeup_tipo: 'comum', nome: '' };
  if (type === 'ator')     { p.subtipo = choice || 'cara_limpa'; }
  if (type === 'especial') {
    p.personagem = choice || (window.ESPECIAIS_LIST || ['Homem-Aranha'])[0];
    p.cantor = false;
    if (p.personagem === 'Boneco Grande Especial') {
      p.bge_subtipo = 'dinossauro';
      p.bge_outro_nome = '';
    }
  }
  performers.push(p);
  update();
}

// Adiciona a partir do dropdown e volta o select ao rótulo inicial.
function addFromDropdown(type, sel) {
  const choice = sel.value;
  if (!choice) return;
  addPerformer(type, choice);
  sel.value = '';
}

function setSubtipo(i, value) {
  performers[i].subtipo = value;
  // boneco não tem maquiagem; ao mudar para boneco, limpa
  if (value === 'boneco') performers[i].makeup = false;
  update();
}

function removePerformer(i) { performers.splice(i, 1); update(); }

function setProp(i, key, value) { performers[i][key] = value; update(); }

function setMakeup(i, checked) {
  performers[i].makeup = checked;
  if (!checked) performers[i].makeup_tipo = 'comum';
  update();
}

// Tipos de sósia — disparam a pergunta predefinido/customizado
const SOSIA_TYPES = new Set(['Sósia']);

function setPersonagem(i, value) {
  performers[i].personagem = value;
  performers[i].cantor = false;
  const comShow = new Set(window.ESPECIAIS_COM_SHOW || []);
  if (!comShow.has(value)) {
    performers[i].show = false;
  }
  if (value === 'Boneco Grande Especial') {
    if (!performers[i].bge_subtipo) performers[i].bge_subtipo = 'dinossauro';
    if (!performers[i].bge_outro_nome) performers[i].bge_outro_nome = '';
  }
  update();
}

function setBgeSubtipo(i, value) {
  performers[i].bge_subtipo = value;
  if (value !== 'outro') performers[i].bge_outro_nome = '';
  update();
}

function changeCoord(delta) {
  coordQty = Math.max(minCoord(), coordQty + delta);
  document.getElementById('coord-qty').textContent = coordQty;
  document.getElementById('coordenador_qty').value  = coordQty;
  update();
}

function setSosiaShowTipo(tipo) {
  showSosiaCustom = tipo === 'customizado';
  update();
}

// ── Editor de acréscimos tipados (feature 099) ───────────────────────────────
function _orcAcrTipos() {
  const blk = document.getElementById('orc-acrescimos');
  try { return JSON.parse(blk.dataset.tipos || '[]'); } catch (_) { return []; }
}
function orcAcrescimoRowHtml(sel) {
  const tipos = _orcAcrTipos();
  const opts = tipos.map(t => `<option value="${t}"${t === sel ? ' selected' : ''}>${t}</option>`).join('');
  return `<div class="orc-acr-row" style="display:flex; flex-wrap:wrap; gap:6px; align-items:center;">
    <select class="acr-tipo" onchange="onOrcAcrescimoTipoChange(this)" style="font-size:13px;">${opts}</select>
    <input type="text" class="acr-desc" placeholder="Descrição" style="font-size:13px; width:140px; display:none;">
    <input type="number" class="acr-value" min="0" step="0.01" placeholder="0" style="width:90px;" oninput="update()">
    <select class="acr-unit" onchange="update()" style="font-size:13px;"><option value="0">R$</option><option value="1">%</option></select>
    <button type="button" class="btn btn-sm btn-ghost orc-acr-remove" style="color:#c0392b;">×</button>
  </div>`;
}
function onOrcAcrescimoTipoChange(sel) {
  const row = sel.closest('.orc-acr-row');
  if (row) row.querySelector('.acr-desc').style.display = sel.value === 'Outro' ? '' : 'none';
  update();
}
function orcAddAcrescimo(sel) {
  const list = document.getElementById('orc-acrescimos-list');
  if (!list) return;
  const tmp = document.createElement('div');
  tmp.innerHTML = orcAcrescimoRowHtml(sel).trim();
  list.appendChild(tmp.firstChild);
  update();
}
(function initOrcAcrescimos() {
  const addBtn = document.getElementById('orc-add-acrescimo');
  const list = document.getElementById('orc-acrescimos-list');
  if (!addBtn || !list) return;
  addBtn.addEventListener('click', () => orcAddAcrescimo());
  list.addEventListener('click', (e) => {
    if (e.target.classList.contains('orc-acr-remove')) { e.target.closest('.orc-acr-row').remove(); update(); }
  });
})();

function setNotaFiscal(checked) {
  notaFiscal = checked;
  update();
}

function setModoEntradas(checked) {
  modoEntradas = checked;
  const lbls = modoEntradas
    ? ['1 entrada', '2 entradas', '4 entradas']
    : ['1 hora',    '2 horas',    '4 horas'];
  ['1h', '2h', '3h', '4h'].forEach((id, i) => {
    const el = document.getElementById(`lbl-${id}`);
    if (el) el.textContent = lbls[i];
  });
  update();
}

// ── Orçamento personalizado ────────────────────────────────────────────────────
const _DURS = ['1h', '2h', '3h', '4h'];

function setPersonalizado(checked) {
  personalizadoAtivo = checked;
  const panel = document.getElementById('personalizado-panel');
  if (panel) panel.style.display = checked ? 'block' : 'none';
  if (checked && personalizadoCriterio === 'multiplicador') prefillMultipliers();
  update();
}

function setPersonalizadoCriterio(crit) {
  personalizadoCriterio = crit;
  const isMult = crit === 'multiplicador';
  _DURS.forEach(dur => {
    const elV = document.getElementById('cust_valor_' + dur);
    const elM = document.getElementById('cust_mult_' + dur);
    if (elV) elV.style.display = isMult ? 'none' : '';
    if (elM) elM.style.display = isMult ? '' : 'none';
  });
  document.querySelectorAll('.pers-unit').forEach(el => { el.textContent = isMult ? '×' : 'R$'; });
  const readout = document.getElementById('cache-base-readout');
  if (readout) readout.style.display = isMult ? 'block' : 'none';
  if (isMult) prefillMultipliers();
  update();
}

function prefillMultipliers() {
  // Pré-preenche os multiplicadores com o markup vigente, se ainda vazios.
  const { show } = eventFlags();
  const markup = S().markup[show ? 'show' : 'receptivo'];
  _DURS.forEach((dur, i) => {
    const el = document.getElementById('cust_mult_' + dur);
    if (el && (!el.value || parseFloat(el.value) === 0)) {
      el.value = markup[i];
      custMult[i] = markup[i];
    }
  });
}

function setPersonalizadoVal(kind, idx, val) {
  // 'valor' usa a máscara BR (R$); 'mult' é multiplicador numérico simples.
  const num = kind === 'valor' ? MoneyMask.parseNumber(val) : (parseFloat(val) || 0);
  if (kind === 'mult') custMult[idx] = num;
  else custValor[idx] = num;
  updateTotals();
}

function updateCacheBaseReadout() {
  if (!personalizadoAtivo || personalizadoCriterio !== 'multiplicador') return;
  const base = cacheBase();
  ['cb-1h', 'cb-2h', 'cb-3h', 'cb-4h'].forEach((id, i) => {
    const el = document.getElementById(id);
    if (el) el.textContent = fmt(base[i]);
  });
}

// ── Transporte ────────────────────────────────────────────────────────────────
function toggleForaSP(checked) {
  forasp = checked;
  document.getElementById('transport-section').style.display = checked ? 'block' : 'none';
  if (checked) {
    const endereco = document.getElementById('event_location').value.trim();
    if (endereco) fetchDistancia();
  }
  update();
}

function setTransportTipo(tipo) {
  transportTipo = tipo;
  document.getElementById('van-options').style.display   = tipo === 'van'   ? '' : 'none';
  document.getElementById('carro-options').style.display = tipo === 'carro' ? '' : 'none';
  update();
}

// ── Google Maps ───────────────────────────────────────────────────────────────
function fetchDistancia() {
  const endereco = document.getElementById('event_location').value.trim();
  if (!endereco) { alert('Preencha o endereço do evento primeiro.'); return; }
  const btn = document.getElementById('btn-distancia');
  btn.disabled = true;
  btn.textContent = 'Calculando...';
  fetch('/orcamento/api/distancia?endereco=' + encodeURIComponent(endereco))
    .then(r => r.json())
    .then(data => {
      if (data.error) { alert('Erro: ' + data.error); }
      else {
        kmIda = data.km_ida;
        const kmEl = document.getElementById('km_ida');
        kmEl.value = kmIda;
        kmEl.classList.remove('orc-input-error');
        const errSpan = kmEl.nextSibling;
        if (errSpan && errSpan.classList && errSpan.classList.contains('orc-field-error')) errSpan.remove();
        colabOverride = null;
        update();
      }
    })
    .catch(() => alert('Erro de conexão ao calcular distância.'))
    .finally(() => { btn.disabled = false; btn.textContent = 'Calcular'; });
}

// ── Limpar ────────────────────────────────────────────────────────────────────
function clearAll() {
  if (!confirm('Limpar todos os campos?')) return;
  performers = []; coordQty = 1; forasp = false; kmIda = 0;
  transportTipo = 'van'; comCarretinha = false; numCarros = 1; colabOverride = null;
  acrescimo = 0; acrescimoTipo = 'valor'; showSosiaCustom = false; prevOnlyDJ = false;
  duracaoCustom = 0;
  personalizadoAtivo = false; personalizadoCriterio = 'valor_final';
  custMult = [0, 0, 0, 0]; custValor = [0, 0, 0, 0];
  document.getElementById('quote-form').reset();
  const persPanel = document.getElementById('personalizado-panel');
  if (persPanel) persPanel.style.display = 'none';
  document.querySelectorAll('.pers-unit').forEach(el => { el.textContent = 'R$'; });
  const dcEl = document.getElementById('duracao_custom');
  if (dcEl) dcEl.value = '';
  document.getElementById('coord-qty').textContent  = '1';
  document.getElementById('coordenador_qty').value  = '1';
  document.getElementById('transport-section').style.display = 'none';
  document.getElementById('van-options').style.display   = '';
  document.getElementById('carro-options').style.display = 'none';
  const acrList = document.getElementById('orc-acrescimos-list');
  if (acrList) acrList.innerHTML = '';
  update();
}

// ── Histórico (banco de dados via API) ───────────────────────────────────────

function _applySnapshot(snap) {
  performers    = snap.performers   || [];
  coordQty      = snap.coordenador_qty || 1;
  forasp        = !!snap.fora_sp;
  kmIda         = parseFloat(snap.km_ida) || 0;
  transportTipo = snap.transporte_tipo || 'van';
  comCarretinha = !!snap.carretinha;
  numCarros     = parseInt(snap.num_carros) || 1;
  colabOverride = snap.num_colaboradores ? parseInt(snap.num_colaboradores) : null;
  // Acréscimos (feature 099): reconstrói as linhas do editor a partir do snapshot.
  const _acrList = document.getElementById('orc-acrescimos-list');
  if (_acrList) {
    _acrList.innerHTML = '';
    let _acrs = snap.acrescimos;
    // Compat: snapshots antigos tinham um único acréscimo (acrescimo_valor/tipo).
    if (!_acrs && parseFloat(snap.acrescimo_valor) > 0) {
      _acrs = [{ tipo: 'Outro', descricao: 'Acréscimo', is_percent: snap.acrescimo_tipo === 'percent', value: parseFloat(snap.acrescimo_valor) }];
    }
    (_acrs || []).forEach(a => {
      const tmp = document.createElement('div');
      tmp.innerHTML = orcAcrescimoRowHtml(a.tipo).trim();
      const row = tmp.firstChild;
      if (a.descricao) { const d = row.querySelector('.acr-desc'); d.value = a.descricao; }
      row.querySelector('.acr-value').value = a.value || 0;
      row.querySelector('.acr-unit').value = a.is_percent ? '1' : '0';
      if (a.tipo === 'Outro') row.querySelector('.acr-desc').style.display = '';
      _acrList.appendChild(row);
    });
  }

  document.querySelector('[name=client_name]').value    = snap.client_name    || '';
  document.querySelector('[name=event_location]').value = snap.event_location || '';
  document.querySelector('[name=event_date]').value     = snap.event_date     || '';
  if (snap.event_time) document.querySelector('[name=event_time]').value = snap.event_time;

  document.getElementById('coord-qty').textContent = coordQty;
  document.getElementById('coordenador_qty').value = coordQty;

  const chk = document.getElementById('fora_sp');
  chk.checked = forasp;
  document.getElementById('transport-section').style.display = forasp ? 'block' : 'none';
  document.getElementById('km_ida').value       = kmIda;
  document.getElementById('carretinha').checked = comCarretinha;
  document.getElementById('num_carros').value   = numCarros;
  const isVan = transportTipo === 'van';
  document.getElementById('t-van').checked   = isVan;
  document.getElementById('t-carro').checked = !isVan;
  document.getElementById('van-options').style.display   = isVan  ? '' : 'none';
  document.getElementById('carro-options').style.display = !isVan ? '' : 'none';
  if (colabOverride !== null) document.getElementById('num_colaboradores').value = colabOverride;

  showSosiaCustom = snap.show_sosia_tipo === 'customizado';
  document.getElementById('sosia-predefinido').checked  = !showSosiaCustom;
  document.getElementById('sosia-customizado').checked  = showSosiaCustom;

  modoEntradas = snap.modo_duracao === 'entradas';
  document.getElementById('modo-horas').checked    = !modoEntradas;
  document.getElementById('modo-entradas').checked = modoEntradas;
  setModoEntradas(modoEntradas);

  duracaoCustom = parseInt(snap.duracao_custom) || 0;
  const dcEl = document.getElementById('duracao_custom');
  if (dcEl) dcEl.value = duracaoCustom || '';

  notaFiscal = !!snap.nota_fiscal;
  const nfEl = document.getElementById('nota_fiscal');
  if (nfEl) nfEl.checked = notaFiscal;

  // (acréscimos já reconstruídos acima a partir de snap.acrescimos)

  // Orçamento personalizado
  personalizadoAtivo    = !!snap.personalizado_ativo;
  personalizadoCriterio = snap.personalizado_criterio || 'valor_final';
  custMult  = [parseFloat(snap.cust_mult_1h)  || 0, parseFloat(snap.cust_mult_2h)  || 0, parseFloat(snap.cust_mult_3h)  || 0, parseFloat(snap.cust_mult_4h)  || 0];
  custValor = [parseFloat(snap.cust_valor_1h) || 0, parseFloat(snap.cust_valor_2h) || 0, parseFloat(snap.cust_valor_3h) || 0, parseFloat(snap.cust_valor_4h) || 0];
  const persChk = document.getElementById('personalizado_ativo');
  if (persChk) persChk.checked = personalizadoAtivo;
  document.getElementById('crit-valor').checked = personalizadoCriterio !== 'multiplicador';
  document.getElementById('crit-mult').checked  = personalizadoCriterio === 'multiplicador';
  _DURS.forEach((dur, i) => {
    const elV = document.getElementById('cust_valor_' + dur);
    const elM = document.getElementById('cust_mult_' + dur);
    if (elV) elV.value = custValor[i] || '';
    if (elM) elM.value = custMult[i] || '';
  });
  document.getElementById('personalizado-panel').style.display = personalizadoAtivo ? 'block' : 'none';
  if (personalizadoAtivo) setPersonalizadoCriterio(personalizadoCriterio);

  update();
  document.getElementById('history-panel').style.display = 'none';
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

function restoreFromHistory(id) {
  fetch(`/orcamento/api/historico/${id}`)
    .then(r => r.json())
    .then(snap => _applySnapshot(snap))
    .catch(() => alert('Erro ao carregar orçamento.'));
}

function deleteFromHistory(id) {
  if (!confirm('Remover este orçamento do histórico?')) return;
  fetch(`/orcamento/api/historico/${id}`, { method: 'DELETE' })
    .then(() => renderHistory())
    .catch(() => alert('Erro ao deletar.'));
}

function renderHistory() {
  const container = document.getElementById('history-list');
  const badge     = document.getElementById('history-count');
  if (!container) return;

  container.innerHTML = '<p style="font-size:13px;color:var(--muted);">Carregando...</p>';

  fetch('/orcamento/api/historico')
    .then(r => r.json())
    .then(history => {
      badge.textContent = history.length;

      if (history.length === 0) {
        container.innerHTML = '<p style="font-size:13px;color:var(--muted);font-style:italic;">Nenhum orçamento gerado ainda.</p>';
        return;
      }

      container.innerHTML = history.map(e => {
        const dateLabel = e.event_date
          ? new Date(e.event_date + 'T00:00').toLocaleDateString('pt-BR') : '';
        return `
          <div class="history-entry">
            <div class="history-entry-info">
              <div class="history-entry-name">${e.client_name || '(sem nome)'}</div>
              <div class="history-entry-sub">${e.event_location || ''} ${dateLabel ? '· ' + dateLabel : ''}</div>
              <div class="history-entry-vals">
                <span class="badge badge-gray">1h ${fmt(e.total_1h)}</span>
                <span class="badge badge-gray">2h ${fmt(e.total_2h)}</span>
                ${e.total_3h ? `<span class="badge badge-gray">3h ${fmt(e.total_3h)}</span>` : ''}
                <span class="badge badge-gray">4h ${fmt(e.total_4h)}</span>
                <span class="badge ${e.has_show ? 'badge-green' : 'badge-gray'}">${e.has_show ? 'Show' : 'Receptivo'}</span>
              </div>
              <div style="font-size:11px;color:var(--muted);margin-top:2px;">${e.created_at}</div>
            </div>
            <div style="display:flex;flex-direction:column;gap:4px;">
              <a href="/orcamento/historico/${e.id}/ver" class="btn btn-secondary btn-sm" style="white-space:nowrap;">Ver</a>
              <a href="/events/new?orcamento_id=${e.id}" class="btn btn-primary btn-sm" style="white-space:nowrap;">Criar evento</a>
              <button type="button" class="btn btn-ghost btn-sm" style="white-space:nowrap;" onclick="restoreFromHistory(${e.id})" title="Carrega os dados e recalcula com os preços atuais (gera um novo)">Recalcular</button>
              <button type="button" class="btn btn-danger btn-sm" onclick="deleteFromHistory(${e.id})">✕</button>
            </div>
          </div>`;
      }).join('');
    })
    .catch(() => {
      container.innerHTML = '<p style="font-size:13px;color:var(--muted);">Erro ao carregar histórico.</p>';
    });
}

// ── Init ──────────────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  const _REQUIRED_FIELDS = [
    { name: 'client_name',    msg: 'Nome do cliente é obrigatório' },
    { name: 'event_location', msg: 'Endereço do evento é obrigatório' },
    { name: 'event_date',     msg: 'Data do evento é obrigatória' },
    { name: 'event_time',     msg: 'Horário do evento é obrigatório' },
  ];

  // Limpa erro ao corrigir o campo
  _REQUIRED_FIELDS.forEach(({ name }) => {
    const el = document.querySelector(`[name="${name}"]`);
    if (!el) return;
    const clear = function () {
      el.classList.remove('orc-input-error');
      const next = el.nextSibling;
      if (next && next.classList && next.classList.contains('orc-field-error')) next.remove();
    };
    el.addEventListener('input', clear);
    el.addEventListener('change', clear);
  });

  document.getElementById('quote-form').addEventListener('submit', function (e) {
    // Limpa erros anteriores
    document.querySelectorAll('.orc-field-error').forEach(el => el.remove());
    document.querySelectorAll('.orc-input-error').forEach(el => el.classList.remove('orc-input-error'));

    const erros = [];
    for (const { name, msg } of _REQUIRED_FIELDS) {
      const el = document.querySelector(`[name="${name}"]`);
      if (!el || !el.value.trim()) {
        el && el.classList.add('orc-input-error');
        const span = document.createElement('span');
        span.className = 'orc-field-error';
        span.textContent = msg;
        el && el.after(span);
        if (el) erros.push(el);
      }
    }

    if (erros.length > 0) {
      e.preventDefault();
      erros[0].scrollIntoView({ behavior: 'smooth', block: 'center' });
      erros[0].focus();
      return;
    }

    // Bloqueia se fora de SP mas distância não calculada
    // (no modo personalizado o transporte não é somado, então não bloqueia)
    if (!personalizadoAtivo && forasp && kmIda <= 0) {
      e.preventDefault();
      const kmEl = document.getElementById('km_ida');
      kmEl.classList.add('orc-input-error');
      const errSpan = document.createElement('span');
      errSpan.className = 'orc-field-error';
      errSpan.textContent = 'Calcule a distância antes de gerar o orçamento.';
      kmEl.after(errSpan);
      document.getElementById('transport-section').scrollIntoView({ behavior: 'smooth', block: 'center' });
      return;
    }

    // Orçamento personalizado: cada duração incluída precisa de total > 0
    if (personalizadoAtivo) {
      const incl = Array.from(document.querySelectorAll('input[name="incluir_duracao"]:checked'))
        .map(c => c.value);
      const durs = incl.length ? incl : ['1h', '2h', '3h', '4h'];
      const totals = calcTotals();
      const idx = { '1h': 0, '2h': 1, '4h': 2 };
      const bad = durs.filter(d => !(totals[idx[d]] > 0));
      if (bad.length > 0) {
        e.preventDefault();
        const prefix = personalizadoCriterio === 'multiplicador' ? 'cust_mult_' : 'cust_valor_';
        const el = document.getElementById(prefix + bad[0]);
        if (el) {
          el.classList.add('orc-input-error');
          const span = document.createElement('span');
          span.className = 'orc-field-error';
          span.textContent = 'Informe um valor maior que zero.';
          el.parentNode.appendChild(span);
          el.scrollIntoView({ behavior: 'smooth', block: 'center' });
          el.focus();
        }
        return;
      }
    }

    document.getElementById('performers_json').value = JSON.stringify(performers);
  });

  document.getElementById('coord-qty-down').addEventListener('click', () => changeCoord(-1));
  document.getElementById('coord-qty-up').addEventListener('click',   () => changeCoord(1));

  document.querySelector('[name=event_time]')?.addEventListener('change', update);

  // Se fora de SP, recalcula automaticamente ao sair do campo de endereço
  document.getElementById('event_location')?.addEventListener('blur', function () {
    if (forasp && this.value.trim()) {
      kmIda = 0;
      document.getElementById('km_ida').value = 0;
      fetchDistancia();
    }
  });

  document.getElementById('km_ida')?.addEventListener('input', function () {
    kmIda = parseFloat(this.value) || 0;
    update();
  });

  document.getElementById('num_colaboradores')?.addEventListener('input', function () {
    const v = parseInt(this.value);
    colabOverride = isNaN(v) ? null : Math.max(1, v);
    update();
  });

  document.getElementById('carretinha')?.addEventListener('change', function () {
    comCarretinha = this.checked;
    const t = S().transporte;
    const rateEl = document.getElementById('carretinha-rate');
    if (rateEl) {
      const rate = comCarretinha ? t.van_com_carretinha : t.van_sem_carretinha;
      rateEl.textContent = `R$${rate.toFixed(2).replace('.', ',')}/km`;
    }
    update();
  });

  document.getElementById('num_carros')?.addEventListener('input', function () {
    numCarros = parseInt(this.value) || 1;
    update();
  });

  // Estado inicial a partir do DOM (para recargas)
  const chkForaSP = document.getElementById('fora_sp');
  if (chkForaSP?.checked) {
    forasp = true;
    document.getElementById('transport-section').style.display = 'block';
  }

  const kmInput = document.getElementById('km_ida');
  if (kmInput) kmIda = parseFloat(kmInput.value) || 0;

  const carretinhaEl = document.getElementById('carretinha');
  if (carretinhaEl) comCarretinha = carretinhaEl.checked;

  // Sincronizar estado inicial de van/carro com o que estiver checked no HTML
  if (document.getElementById('t-van')?.checked) {
    transportTipo = 'van';
    document.getElementById('van-options').style.display   = '';
    document.getElementById('carro-options').style.display = 'none';
  } else {
    transportTipo = 'carro';
    document.getElementById('van-options').style.display   = 'none';
    document.getElementById('carro-options').style.display = '';
  }

  const numCarrosEl = document.getElementById('num_carros');
  if (numCarrosEl) numCarros = parseInt(numCarrosEl.value) || 1;

  const colabEl = document.getElementById('num_colaboradores');
  if (colabEl?.value) {
    const v = parseInt(colabEl.value);
    if (!isNaN(v)) colabOverride = Math.max(1, v);
  }

  // Sincroniza campos que o browser pode restaurar após Back/refresh
  const nfEl = document.getElementById('nota_fiscal');
  if (nfEl) notaFiscal = nfEl.checked;

  const dcInit = document.getElementById('duracao_custom');
  if (dcInit?.value) duracaoCustom = parseInt(dcInit.value) || 0;

  // Orçamento personalizado (estado restaurado pelo browser)
  const persEl = document.getElementById('personalizado_ativo');
  if (persEl?.checked) {
    personalizadoAtivo = true;
    document.getElementById('personalizado-panel').style.display = 'block';
    const critMult = document.getElementById('crit-mult');
    personalizadoCriterio = critMult?.checked ? 'multiplicador' : 'valor_final';
    _DURS.forEach((dur, i) => {
      const elV = document.getElementById('cust_valor_' + dur);
      const elM = document.getElementById('cust_mult_' + dur);
      if (elV?.value) custValor[i] = parseFloat(elV.value) || 0;
      if (elM?.value) custMult[i] = parseFloat(elM.value) || 0;
    });
    setPersonalizadoCriterio(personalizadoCriterio);
  }

  update();
  renderHistory();

  // Reabrir a partir do histórico (link da página /orcamento/historico)
  const restoreId = new URLSearchParams(window.location.search).get('restore');
  if (restoreId) {
    window.history.replaceState({}, '', '/orcamento/');
    restoreFromHistory(parseInt(restoreId));
  }
});
