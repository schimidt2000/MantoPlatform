/* Upload de formulário com barra de progresso real (feature 105).
 *
 * Fonte única do envio com progresso do módulo de revisão: intercepta o submit,
 * envia via XHR (FormData) e reporta bytes reais em xhr.upload.onprogress.
 * As rotas respondem {"redirect": url} (sucesso) ou {"error": msg} (400) quando o
 * header X-Requested-With está presente; sem arquivos selecionados, o submit
 * tradicional segue normalmente (sem barra).
 */
(function (global) {
  'use strict';

  function formatMb(bytes) {
    return (bytes / (1024 * 1024)).toFixed(1).replace('.', ',') + ' MB';
  }

  function hasSelectedFiles(form) {
    var inputs = form.querySelectorAll('input[type="file"]');
    for (var i = 0; i < inputs.length; i++) {
      if (inputs[i].files && inputs[i].files.length) return true;
    }
    return false;
  }

  function setFormDisabled(form, disabled) {
    var fields = form.querySelectorAll('input, textarea, select, button');
    for (var i = 0; i < fields.length; i++) fields[i].disabled = disabled;
  }

  /**
   * Liga o envio com progresso a um formulário.
   *
   * @param {HTMLFormElement} form
   * @param {Object} opts
   * @param {HTMLElement} opts.wrapEl     Container da barra (mostrado durante o envio).
   * @param {HTMLElement} opts.barEl      Elemento cuja largura vira o % enviado.
   * @param {HTMLElement} opts.labelEl    Texto "N% — X MB de Y MB".
   * @param {HTMLElement} opts.errorEl    Onde exibir erros sem recarregar.
   * @param {HTMLElement} opts.submitBtn  Botão de envio (desabilita + texto de estado).
   */
  function uploadFormWithProgress(form, opts) {
    form.addEventListener('submit', function (e) {
      if (!hasSelectedFiles(form)) return; // envio rápido: fluxo tradicional

      e.preventDefault();
      if (opts.errorEl) { opts.errorEl.hidden = true; opts.errorEl.textContent = ''; }

      var data = new FormData(form);
      var xhr = new XMLHttpRequest();
      var originalText = opts.submitBtn ? opts.submitBtn.textContent : '';

      function fail(message) {
        setFormDisabled(form, false);
        if (opts.submitBtn) opts.submitBtn.textContent = originalText;
        if (opts.wrapEl) opts.wrapEl.hidden = true;
        if (opts.errorEl) { opts.errorEl.textContent = message; opts.errorEl.hidden = false; }
        else alert(message);
      }

      setFormDisabled(form, true);
      if (opts.submitBtn) { opts.submitBtn.disabled = true; opts.submitBtn.textContent = 'Enviando…'; }
      if (opts.wrapEl) opts.wrapEl.hidden = false;
      if (opts.barEl) opts.barEl.style.width = '0%';
      if (opts.labelEl) opts.labelEl.textContent = 'Preparando envio…';

      xhr.upload.addEventListener('progress', function (ev) {
        if (!ev.lengthComputable) return;
        var pct = Math.round((ev.loaded / ev.total) * 100);
        if (opts.barEl) opts.barEl.style.width = pct + '%';
        if (opts.labelEl) {
          opts.labelEl.textContent = pct + '% — ' + formatMb(ev.loaded) + ' de ' + formatMb(ev.total);
        }
      });

      xhr.addEventListener('load', function () {
        var json = null;
        try { json = JSON.parse(xhr.responseText); } catch (err) { json = null; }
        if (xhr.status >= 200 && xhr.status < 300 && json && json.redirect) {
          if (opts.labelEl) opts.labelEl.textContent = '100% — processando…';
          global.location = json.redirect;
          return;
        }
        fail((json && json.error) || 'Não foi possível concluir o envio. Tente novamente.');
      });
      xhr.addEventListener('error', function () {
        fail('Falha de conexão durante o envio. Verifique a internet e tente de novo — seus dados foram mantidos.');
      });
      xhr.addEventListener('abort', function () {
        fail('Envio cancelado. Seus dados foram mantidos.');
      });

      xhr.open('POST', form.getAttribute('action') || global.location.pathname);
      xhr.setRequestHeader('X-Requested-With', 'XMLHttpRequest');
      xhr.send(data);
    });
  }

  global.uploadFormWithProgress = uploadFormWithProgress;
})(window);
