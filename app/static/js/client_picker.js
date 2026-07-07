/* Editor de clientes do evento (features 094/100/114 — múltiplos + relação).
 *
 * Componente compartilhado entre a página do evento (Dados da Venda) e a tela de criar
 * evento. Espera um #clients-block com data-search-url, data-create-url, data-relations
 * (JSON) e, opcionalmente, data-required="1" (exige ao menos um cliente no submit do form).
 */
(function () {
  const block = document.getElementById('clients-block');
  if (!block) return;
  const searchUrl = block.dataset.searchUrl;
  const createUrl = block.dataset.createUrl;
  const relations = JSON.parse(block.dataset.relations || '["Contratante"]');
  const listEl    = document.getElementById('clients-list');
  const emptyEl   = document.getElementById('clients-empty');
  const search    = document.getElementById('client-search');
  const results   = document.getElementById('client-results');
  const newToggle = document.getElementById('client-new-toggle');
  const newForm   = document.getElementById('client-new-form');
  const newName   = document.getElementById('client-new-name');
  const newPhone  = document.getElementById('client-new-phone');
  const newCompany= document.getElementById('client-new-company');
  const newSave   = document.getElementById('client-new-save');
  const newError  = document.getElementById('client-new-error');

  function esc(s) { return (s || '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/"/g,'&quot;'); }
  function currentIds() {
    return [...listEl.querySelectorAll('input[name="client_id[]"]')].map(i => i.value);
  }
  function refreshEmpty() {
    if (emptyEl) emptyEl.style.display = listEl.children.length ? 'none' : '';
  }
  function addClient(c) {
    if (currentIds().includes(String(c.id))) return; // evita duplicar o mesmo cliente
    const relOpts = relations.map(r => `<option value="${esc(r)}">${esc(r)}</option>`).join('');
    const row = document.createElement('div');
    row.className = 'client-row';
    row.style.cssText = 'display:flex; gap:8px; align-items:center; background:#f4f2f7; border:1px solid var(--line); border-radius:8px; padding:8px 12px;';
    row.innerHTML =
      `<input type="hidden" name="client_id[]" value="${esc(String(c.id))}">` +
      `<span style="font-size:16px;">👤</span>` +
      `<div style="flex:1; min-width:0;"><div style="font-weight:600;">${esc(c.name)}</div>` +
      `<div class="meta" style="font-size:12px;">${esc(c.phone_display || c.phone || '')}</div></div>` +
      `<select name="client_relation[]" class="form-control" style="font-size:12px; width:130px; flex:0 0 auto;">${relOpts}</select>` +
      `<a href="/clientes/${esc(String(c.id))}" target="_blank" class="btn btn-sm btn-ghost" style="font-size:11px;">Ficha</a>` +
      `<button type="button" class="btn btn-sm btn-ghost client-remove" style="font-size:13px; color:#c0392b;">×</button>`;
    listEl.appendChild(row);
    refreshEmpty();
  }

  listEl.addEventListener('click', function (e) {
    if (e.target.classList.contains('client-remove')) { e.target.closest('.client-row').remove(); refreshEmpty(); }
  });

  let timer = null;
  if (search) search.addEventListener('input', function () {
    const q = search.value.trim();
    clearTimeout(timer);
    if (q.length < 2) { results.style.display = 'none'; return; }
    timer = setTimeout(function () {
      fetch(searchUrl + '?q=' + encodeURIComponent(q))
        .then(r => r.json())
        .then(list => {
          results.innerHTML = '';
          if (!list.length) { results.style.display = 'none'; return; }
          list.forEach(c => {
            const row = document.createElement('div');
            row.style.cssText = 'padding:8px 12px; cursor:pointer; border-bottom:1px solid var(--line);';
            row.innerHTML = '<div style="font-weight:600;">' + esc(c.name) +
              '</div><div style="font-size:12px; color:var(--muted);">' +
              esc(c.phone_display || c.phone) + (c.company ? ' · ' + esc(c.company) : '') + '</div>';
            row.addEventListener('mouseenter', () => row.style.background = '#f4f2f7');
            row.addEventListener('mouseleave', () => row.style.background = '#fff');
            row.addEventListener('click', () => { addClient(c); search.value = ''; results.style.display = 'none'; });
            results.appendChild(row);
          });
          results.style.display = 'block';
        })
        .catch(() => { results.style.display = 'none'; });
    }, 250);
  });

  if (newToggle) newToggle.addEventListener('click', function () {
    newForm.style.display = newForm.style.display === 'none' ? 'block' : 'none';
  });

  if (newSave) newSave.addEventListener('click', function () {
    newError.style.display = 'none';
    const data = new FormData();
    data.append('name', newName.value.trim());
    data.append('phone', newPhone.value.trim());
    data.append('company', newCompany.value.trim());
    newSave.disabled = true;
    fetch(createUrl, { method: 'POST', body: data })
      .then(r => r.json().then(j => ({ ok: r.ok, j })))
      .then(({ ok, j }) => {
        newSave.disabled = false;
        if (!ok) { newError.textContent = j.error || 'Erro ao salvar.'; newError.style.display = 'block'; return; }
        addClient(j);
        newForm.style.display = 'none';
        newName.value = newPhone.value = newCompany.value = '';
      })
      .catch(() => { newSave.disabled = false; newError.textContent = 'Erro de rede.'; newError.style.display = 'block'; });
  });

  // Guarda no submit: exige ao menos um cliente quando data-required="1" (feature 094/100).
  if (block.dataset.required === '1') {
    const vendaForm = block.closest('form');
    if (vendaForm) vendaForm.addEventListener('submit', function (ev) {
      if (!currentIds().length) {
        ev.preventDefault();
        block.scrollIntoView({ behavior: 'smooth', block: 'center' });
        if (search) search.focus();
        var warn = document.getElementById('client-required-msg');
        if (!warn) {
          warn = document.createElement('p');
          warn.id = 'client-required-msg';
          warn.style.cssText = 'color:var(--red); font-size:12.5px; font-weight:600; margin:6px 0 0;';
          block.appendChild(warn);
        }
        warn.textContent = 'Associe ao menos um cliente ao evento antes de salvar os dados de venda.';
      }
    });
  }
})();
