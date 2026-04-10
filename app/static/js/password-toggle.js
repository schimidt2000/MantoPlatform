/**
 * Injeta automaticamente o botão de mostrar/ocultar senha
 * em todos os inputs type="password" da página.
 */
(function () {
  function init() {
    document.querySelectorAll('input[type="password"]').forEach(function (input) {
      // Evita duplicar se já foi processado
      if (input.dataset.pwToggle) return;
      input.dataset.pwToggle = "1";

      var wrapper = document.createElement("div");
      wrapper.className = "pw-wrap";

      input.parentNode.insertBefore(wrapper, input);
      wrapper.appendChild(input);

      var btn = document.createElement("button");
      btn.type = "button";
      btn.className = "pw-eye";
      btn.setAttribute("aria-label", "Mostrar senha");
      btn.innerHTML = eyeIcon(false);
      wrapper.appendChild(btn);

      btn.addEventListener("click", function () {
        var showing = input.type === "text";
        input.type = showing ? "password" : "text";
        btn.innerHTML = eyeIcon(showing);
        btn.setAttribute("aria-label", showing ? "Mostrar senha" : "Ocultar senha");
      });
    });
  }

  function eyeIcon(crossed) {
    if (crossed) {
      // olho fechado (senha oculta)
      return '<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94"/><path d="M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19"/><line x1="1" y1="1" x2="23" y2="23"/></svg>';
    }
    // olho aberto (senha visível)
    return '<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>';
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
