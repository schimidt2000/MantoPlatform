'use strict';

// ── Settings injetados pelo template ─────────────────────────────────────────
const S = () => window.SETTINGS;

// ── Estado global ─────────────────────────────────────────────────────────────
let performers    = [];
let coordQty      = 1;
let forasp        = false;
let kmIda         = 0;
let transportTipo = 'van';
let comCarretinha = false;
let numCarros     = 1;
let colabOverride  = null;  // null = auto
let acrescimo      = 0;
let acrescimoTipo  = 'valor'; // 'valor' | 'percent'
let showSosiaCustom = false;

// ── Formatação ────────────────────────────────────────────────────────────────
const BRL = new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' });
const fmt = (v) => BRL.format(v);

// ── Lógica de negócio ─────────────────────────────────────────────────────────
function eventFlags() {
  let show = false, makeup = false, makesReg = 0, makesEsp = 0;
  for (const p of performers) {
    if (p.type === 'cantor' || (p.show && (p.type === 'ator' || p.type === 'especial')))
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

function minCoord() {
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

function calcTotals() {
  const { show, makeup, makesReg, makesEsp } = eventFlags();
  const cfg   = S();
  const cache = [0, 0, 0];

  for (const p of performers) {
    let prices;
    if (p.type === 'ator') {
      const key = `${p.subtipo}|${p.show}|${p.makeup}`;
      prices = cfg.ator[key] || [0, 0, 0];
    } else if (p.type === 'cantor') {
      prices = cfg.cantor[String(p.makeup)] || [0, 0, 0];
    } else if (p.type === 'especial') {
      const ep = cfg.especiais[p.personagem];
      prices = !ep ? [0, 0, 0] : Array.isArray(ep) ? ep : (ep[String(p.show)] || [0, 0, 0]);
    } else {
      prices = [0, 0, 0];
    }
    for (let i = 0; i < 3; i++) cache[i] += prices[i];
  }

  // Coordenador
  const cp = cfg.coordenador[String(show)] || [0, 0, 0];
  for (let i = 0; i < 3; i++) cache[i] += cp[i] * coordQty;

  // Show customizado: +R$50 por artista (não inclui coord, técnico, maquiador)
  if (showSosiaCustom && performers.length > 0) {
    const customAdd = performers.length * 50;
    for (let i = 0; i < 3; i++) cache[i] += customAdd;
  }

  // Adicional noturno (+R$50 por artista e coordenador se >= 19h; exceto técnico e maquiador)
  if (isNoturno()) {
    const notAdd = (performers.length + coordQty) * 50;
    for (let i = 0; i < 3; i++) cache[i] += notAdd;
  }

  // Técnico de Som
  if (show) {
    for (let i = 0; i < 3; i++) cache[i] += cfg.tecnico_som[i];
  }

  // Maquiador
  if (makeup) {
    const mc = maquiadorCost(makesReg, makesEsp);
    for (let i = 0; i < 3; i++) cache[i] += mc;
  }

  // Markup
  const markup = cfg.markup[show ? 'show' : 'receptivo'];
  const t = cache.map((v, i) => v * markup[i]);

  // Brinde (pós-markup)
  if (show) {
    const brinde = cfg.brinde_show ?? 100;
    for (let i = 0; i < 3; i++) t[i] += brinde;
  }

  // Transporte especial pós-markup — uma vez por tipo
  const regras = cfg.especiais_regras || {};
  const seenTransport = new Set();
  for (const p of performers) {
    if (p.type === 'especial' && !seenTransport.has(p.personagem)) {
      const tEsp = (regras[p.personagem] || {}).transporte_especial || 0;
      if (tEsp) {
        for (let i = 0; i < 3; i++) t[i] += tEsp;
        seenTransport.add(p.personagem);
      }
    }
  }

  // Transporte (pós-markup)
  const tc = transportCost();
  for (let i = 0; i < 3; i++) t[i] += tc;

  // Acréscimo
  if (acrescimo > 0) {
    for (let i = 0; i < 3; i++) {
      t[i] = acrescimoTipo === 'percent'
        ? Math.round(t[i] * (1 + acrescimo / 100) * 100) / 100
        : Math.round((t[i] + acrescimo) * 100) / 100;
    }
  }

  return t;
}

// ── UI ────────────────────────────────────────────────────────────────────────
function update() {
  // Enforce min coordinators (e.g. Boneco Grande Especial requires ≥ 2)
  const minC = minCoord();
  if (coordQty < minC) {
    coordQty = minC;
    document.getElementById('coord-qty').textContent = coordQty;
    document.getElementById('coordenador_qty').value  = coordQty;
  }
  renderPerformers();
  updateAutoServices();
  updateTotals();
  updateDebugPanel();
  syncColabField();
}

function updateTotals() {
  const [t1, t2, t4] = calcTotals();
  document.getElementById('total-1h').textContent = fmt(t1);
  document.getElementById('total-2h').textContent = fmt(t2);
  document.getElementById('total-4h').textContent = fmt(t4);
}

function updateAutoServices() {
  const { show, makeup, makesReg, makesEsp } = eventFlags();
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
  if (!tbody || !tfoot) return;

  const { show, makeup, makesReg, makesEsp } = eventFlags();
  const cfg    = S();
  const markup = cfg.markup[show ? 'show' : 'receptivo'];
  const markupLabels = markup.map(v => `${v}×`);
  const modeloLabel  = show ? 'Show' : 'Receptivo / Interativo';
  const rows  = [];
  const cache = [0, 0, 0];

  for (const p of performers) {
    let prices, label;
    if (p.type === 'ator') {
      const key = `${p.subtipo}|${p.show}|${p.makeup}`;
      prices = cfg.ator[key] || [0, 0, 0];
      const parts = [p.subtipo === 'boneco' ? 'Boneco' : 'Cara Limpa'];
      if (p.show)   parts.push('show');
      if (p.makeup) parts.push(`make ${p.makeup_tipo}`);
      label = (p.nome || 'Ator') + ` <span style="color:var(--muted)">(${parts.join(', ')})</span>`;
    } else if (p.type === 'cantor') {
      prices = cfg.cantor[String(p.makeup)] || [0, 0, 0];
      label  = (p.nome || 'Cantor') + ` <span style="color:var(--muted)">(cantor${p.makeup ? ', make' : ''})</span>`;
    } else if (p.type === 'especial') {
      const ep = cfg.especiais[p.personagem];
      prices   = !ep ? [0, 0, 0] : Array.isArray(ep) ? ep : (ep[String(p.show)] || [0, 0, 0]);
      label    = (p.nome || p.personagem) + ` <span style="color:var(--muted)">(${p.personagem}${p.show ? ', show' : ''})</span>`;
    } else {
      prices = [0, 0, 0]; label = p.nome || '?';
    }
    rows.push({ label, prices });
    for (let i = 0; i < 3; i++) cache[i] += prices[i];
  }

  // Coordenador
  const cp = cfg.coordenador[String(show)] || [0, 0, 0];
  const coordPrices = cp.map(v => v * coordQty);
  rows.push({ label: `Coordenador(es) (${coordQty}) <span style="color:var(--muted)">${show ? 'com show' : 'sem show'}</span>`, prices: coordPrices });
  for (let i = 0; i < 3; i++) cache[i] += coordPrices[i];

  // Show customizado
  if (showSosiaCustom && performers.length > 0) {
    const customAdd = performers.length * 50;
    rows.push({ label: `Show Customizado <span style="color:var(--muted)">(${performers.length} artista${performers.length !== 1 ? 's' : ''} × R$50)</span>`, prices: [customAdd, customAdd, customAdd] });
    for (let i = 0; i < 3; i++) cache[i] += customAdd;
  }

  // Adicional noturno
  if (isNoturno()) {
    const notCount = performers.length + coordQty;
    const notAdd = notCount * 50;
    rows.push({ label: `Adicional Noturno <span style="color:var(--muted)">(≥ 19h · ${notCount} pessoa${notCount !== 1 ? 's' : ''} × R$50)</span>`, prices: [notAdd, notAdd, notAdd] });
    for (let i = 0; i < 3; i++) cache[i] += notAdd;
  }

  if (show) {
    const tecnico = cfg.tecnico_som;
    rows.push({ label: 'Técnico de Som <span style="color:var(--muted)">(automático)</span>', prices: [...tecnico] });
    for (let i = 0; i < 3; i++) cache[i] += tecnico[i];
  }

  if (makeup) {
    const mc = maquiadorCost(makesReg, makesEsp);
    rows.push({ label: `Maquiador <span style="color:var(--muted)">(${makesReg} regular + ${makesEsp} especial)</span>`, prices: [mc, mc, mc] });
    for (let i = 0; i < 3; i++) cache[i] += mc;
  }

  rows.push({ label: '<strong>Subtotal Cachê</strong>', prices: [...cache], bold: true });

  const afterMarkup = cache.map((v, i) => v * markup[i]);
  rows.push({
    label: `<strong>× Markup</strong> <span style="color:var(--muted)">${modeloLabel} — ${markupLabels.join(' / ')}</span>`,
    prices: afterMarkup, bold: true, hl: 'warning'
  });

  let html = rows.map(r => `
    <tr style="${r.hl === 'warning' ? 'background:#fffbeb;' : ''}">
      <td>${r.label}</td>
      ${r.prices.map(v => `<td style="text-align:right;${r.bold ? 'font-weight:600;' : ''}">${fmt(v)}</td>`).join('')}
    </tr>`).join('');

  const running = [...afterMarkup];

  if (show) {
    const brinde = cfg.brinde_show ?? 100;
    html += `<tr><td>Brinde aniversariante <span style="color:var(--muted)">(pós-markup)</span></td><td style="text-align:right;" colspan="3">${fmt(brinde)}</td></tr>`;
    for (let i = 0; i < 3; i++) running[i] += brinde;
  }

  // Transporte especial pós-markup — uma vez por tipo
  const dbgRegras = cfg.especiais_regras || {};
  const dbgSeenTransport = new Set();
  for (const p of performers) {
    if (p.type === 'especial' && !dbgSeenTransport.has(p.personagem)) {
      const tEsp = (dbgRegras[p.personagem] || {}).transporte_especial || 0;
      if (tEsp) {
        html += `<tr><td>Transporte Especial — ${p.personagem} <span style="color:var(--muted)">(pós-markup, único)</span></td><td style="text-align:right;" colspan="3">${fmt(tEsp)}</td></tr>`;
        for (let i = 0; i < 3; i++) running[i] += tEsp;
        dbgSeenTransport.add(p.personagem);
      }
    }
  }

  const tb = transportBreakdown();
  if (tb) {
    const veiculoLabel = transportTipo === 'van'
      ? `Van ${comCarretinha ? 'c/ carretinha' : 's/ carretinha'} · R$${tb.tarifa}/km · ${tb.kmT}km`
      : `${numCarros} carro(s) · R$1,90/km × ${numCarros} · ${tb.kmT}km`;
    html += `
      <tr style="background:#fffbeb;"><td colspan="4" style="font-weight:600;font-size:12px;">Transporte — Fora de SP</td></tr>
      <tr><td style="padding-left:16px;">Veículo <span style="color:var(--muted)">(${veiculoLabel})</span></td><td style="text-align:right;" colspan="3">${fmt(tb.vt)}</td></tr>
      <tr><td style="padding-left:16px;">Adicional Fora SP <span style="color:var(--muted)">(${tb.colab} colab × ${tb.kmT}km ÷ 3)</span></td><td style="text-align:right;" colspan="3">${fmt(tb.afsp)}</td></tr>
      <tr><td style="padding-left:16px;">Adicional Show <span style="color:var(--muted)">${tb.ashow > 0 ? `(${tb.kmT}km ÷ 6)` : '(km ≤ 500 ou sem show)'}</span></td><td style="text-align:right;" colspan="3">${fmt(tb.ashow)}</td></tr>
      <tr style="background:#fffbeb;"><td style="font-weight:600;padding-left:16px;">Total Transporte</td><td style="text-align:right;font-weight:600;" colspan="3">${fmt(tb.total)}</td></tr>`;
    for (let i = 0; i < 3; i++) running[i] += tb.total;
  }

  if (acrescimo > 0) {
    if (acrescimoTipo === 'percent') {
      const addVals = running.map(v => Math.round(v * acrescimo / 100 * 100) / 100);
      html += `<tr style="background:#f0fdf4;"><td><strong>+ Acréscimo</strong> <span style="color:var(--muted)">(${acrescimo}%)</span></td>${addVals.map(v => `<td style="text-align:right;font-weight:600;">${fmt(v)}</td>`).join('')}</tr>`;
      for (let i = 0; i < 3; i++) running[i] = Math.round((running[i] + addVals[i]) * 100) / 100;
    } else {
      html += `<tr style="background:#f0fdf4;"><td><strong>+ Acréscimo</strong> <span style="color:var(--muted)">(valor fixo)</span></td><td style="text-align:right;font-weight:600;" colspan="3">${fmt(acrescimo)}</td></tr>`;
      for (let i = 0; i < 3; i++) running[i] = Math.round((running[i] + acrescimo) * 100) / 100;
    }
  }

  html += `
    <tr style="background:var(--green-soft);">
      <td><strong>TOTAL FINAL AO CLIENTE</strong></td>
      ${running.map(v => `<td style="text-align:right;font-weight:700;">${fmt(v)}</td>`).join('')}
    </tr>`;

  tbody.innerHTML = html;
  tfoot.innerHTML = `
    <tr style="background:var(--surface);color:var(--muted);">
      <td colspan="4" style="font-size:12px;font-style:italic;">
        Markup (${modeloLabel}): 1h × ${markup[0]} · 2h × ${markup[1]} · 4h × ${markup[2]}
        ${tb ? ` · Transporte ${fmt(tb.total)} pós-markup` : ''}
        ${acrescimo > 0 ? ` · Acréscimo ${acrescimoTipo === 'percent' ? acrescimo + '%' : fmt(acrescimo)} pós-tudo` : ''}
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
    const makeupSel = p.makeup ? `<select onchange="setProp(${i},'makeup_tipo',this.value)"><option value="comum" ${p.makeup_tipo!=='especial'?'selected':''}>Comum</option><option value="especial" ${p.makeup_tipo==='especial'?'selected':''}>Especial</option></select>` : '';
    controls = `
      <span class="badge badge-gold">Ator</span>
      ${nomeInput}
      <select onchange="setProp(${i},'subtipo',this.value)">
        <option value="cara_limpa" ${p.subtipo!=='boneco'?'selected':''}>Cara Limpa</option>
        <option value="boneco" ${p.subtipo==='boneco'?'selected':''}>Boneco</option>
      </select>
      <label class="chk"><input type="checkbox" ${p.show?'checked':''} onchange="setProp(${i},'show',this.checked)"> Show</label>
      <label class="chk"><input type="checkbox" ${p.makeup?'checked':''} onchange="setMakeup(${i},this.checked)"> Maquiagem</label>
      ${makeupSel}`;
  } else if (p.type === 'cantor') {
    const makeupSel = p.makeup ? `<select onchange="setProp(${i},'makeup_tipo',this.value)"><option value="comum" ${p.makeup_tipo!=='especial'?'selected':''}>Comum</option><option value="especial" ${p.makeup_tipo==='especial'?'selected':''}>Especial</option></select>` : '';
    controls = `
      <span class="badge badge-green">Cantor</span>
      ${nomeInput}
      <span style="font-size:12px;color:var(--muted);">(sempre com show)</span>
      <label class="chk"><input type="checkbox" ${p.makeup?'checked':''} onchange="setMakeup(${i},this.checked)"> Maquiagem</label>
      ${makeupSel}`;
  } else if (p.type === 'especial') {
    const especiais  = window.ESPECIAIS_LIST || [];
    const comShowSet = new Set(window.ESPECIAIS_COM_SHOW || []);
    const opts = especiais.map(e => `<option value="${e}" ${p.personagem===e?'selected':''}>${e}</option>`).join('');
    const showCheck = comShowSet.has(p.personagem)
      ? `<label class="chk"><input type="checkbox" ${p.show?'checked':''} onchange="setProp(${i},'show',this.checked)"> Show</label>` : '';
    const makeupSelEsp = p.makeup ? `<select onchange="setProp(${i},'makeup_tipo',this.value)"><option value="comum" ${p.makeup_tipo!=='especial'?'selected':''}>Comum</option><option value="especial" ${p.makeup_tipo==='especial'?'selected':''}>Especial</option></select>` : '';
    controls = `
      <span class="badge badge-blue">Especial</span>
      ${nomeInput}
      <select onchange="setPersonagem(${i},this.value)">${opts}</select>
      ${showCheck}
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
function addPerformer(type) {
  const p = { type, show: false, makeup: false, makeup_tipo: 'comum', nome: '' };
  if (type === 'ator')     { p.subtipo = 'cara_limpa'; }
  if (type === 'cantor')   { p.show = true; }
  if (type === 'especial') { p.personagem = (window.ESPECIAIS_LIST || ['Homem-Aranha'])[0]; }
  performers.push(p);
  update();
}

function removePerformer(i) { performers.splice(i, 1); update(); }

function setProp(i, key, value) { performers[i][key] = value; update(); }

function setMakeup(i, checked) {
  performers[i].makeup = checked;
  if (!checked) performers[i].makeup_tipo = 'comum';
  update();
}

// Tipos que são sempre "com show" — show pré-marcado ao selecionar
const SEMPRE_SHOW = new Set(['Sósia com Show', 'Sósia Cantor']);

// Tipos de sósia — disparam a pergunta predefinido/customizado
const SOSIA_TYPES = new Set(['Sósia', 'Sósia com Show', 'Sósia Cantor']);

function setPersonagem(i, value) {
  performers[i].personagem = value;
  const comShow = new Set(window.ESPECIAIS_COM_SHOW || []);
  if (!comShow.has(value)) {
    performers[i].show = false;
  } else if (SEMPRE_SHOW.has(value)) {
    performers[i].show = true;
  }
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

function setAcrescimoTipo(tipo) {
  acrescimoTipo = tipo;
  document.getElementById('acrescimo-unit').textContent = tipo === 'percent' ? '%' : 'R$';
  update();
}

function setAcrescimo(val) {
  acrescimo = parseFloat(val) || 0;
  update();
}

// ── Transporte ────────────────────────────────────────────────────────────────
function toggleForaSP(checked) {
  forasp = checked;
  document.getElementById('transport-section').style.display = checked ? 'block' : 'none';
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
        document.getElementById('km_ida').value = kmIda;
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
  acrescimo = 0; acrescimoTipo = 'valor'; showSosiaCustom = false;
  document.getElementById('quote-form').reset();
  document.getElementById('coord-qty').textContent  = '1';
  document.getElementById('coordenador_qty').value  = '1';
  document.getElementById('transport-section').style.display = 'none';
  document.getElementById('van-options').style.display   = '';
  document.getElementById('carro-options').style.display = 'none';
  document.getElementById('acrescimo-unit').textContent = 'R$';
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
  acrescimo     = parseFloat(snap.acrescimo_valor) || 0;
  acrescimoTipo = snap.acrescimo_tipo || 'valor';

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

  const isPercent = acrescimoTipo === 'percent';
  document.getElementById('acrescimo_valor').value            = acrescimo || 0;
  document.getElementById('acrescimo-valor-radio').checked    = !isPercent;
  document.getElementById('acrescimo-percent-radio').checked  = isPercent;
  document.getElementById('acrescimo-unit').textContent       = isPercent ? '%' : 'R$';

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
                <span class="badge badge-gray">4h ${fmt(e.total_4h)}</span>
                <span class="badge ${e.has_show ? 'badge-green' : 'badge-gray'}">${e.has_show ? 'Show' : 'Receptivo'}</span>
              </div>
              <div style="font-size:11px;color:var(--muted);margin-top:2px;">${e.created_at}</div>
            </div>
            <div style="display:flex;flex-direction:column;gap:4px;">
              <button class="btn btn-secondary btn-sm" onclick="restoreFromHistory(${e.id})">Reabrir</button>
              <button class="btn btn-danger btn-sm" onclick="deleteFromHistory(${e.id})">✕</button>
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
  document.getElementById('quote-form').addEventListener('submit', () => {
    document.getElementById('performers_json').value = JSON.stringify(performers);
  });

  document.getElementById('coord-qty-down').addEventListener('click', () => changeCoord(-1));
  document.getElementById('coord-qty-up').addEventListener('click',   () => changeCoord(1));

  document.querySelector('[name=event_time]')?.addEventListener('change', update);

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

  if (document.getElementById('t-carro')?.checked) {
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

  update();
  renderHistory();
});
