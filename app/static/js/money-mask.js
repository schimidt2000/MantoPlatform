/*
 * money-mask.js — Fonte única da máscara de valores monetários (padrão brasileiro).
 *
 * Estilo "calculadora": os dígitos preenchem da direita para a esquerda, com os
 * centavos sempre presentes. Ex.: digitar 4 0 0 0 0 0 → "4.000,00".
 *
 * Aplica-se automaticamente a todo <input class="brl-input"> ao carregar a página.
 * O backend converte a string mascarada de volta para número (app/money.py),
 * portanto não é necessário "desmascarar" no envio do formulário.
 */
(function () {
  "use strict";

  /** Formata uma quantidade de centavos no padrão brasileiro: 400000 → "4.000,00". */
  function formatCents(cents) {
    var negative = cents < 0;
    cents = Math.abs(cents);
    var inteiro = Math.floor(cents / 100);
    var dec = String(cents % 100).padStart(2, "0");
    // Agrupa o milhar com ponto.
    var milhar = String(inteiro).replace(/\B(?=(\d{3})+(?!\d))/g, ".");
    return (negative ? "-" : "") + milhar + "," + dec;
  }

  /** Extrai os centavos (inteiro) a partir do texto digitado. */
  function digitsToCents(text) {
    var digits = (text || "").replace(/\D/g, "");
    if (!digits) return null;
    return parseInt(digits, 10);
  }

  /** Aplica/atualiza a máscara em um input. */
  function applyMask(input) {
    var cents = digitsToCents(input.value);
    input.value = cents === null ? "" : formatCents(cents);
  }

  function onInput(e) {
    applyMask(e.target);
    // Mantém o cursor no fim (comportamento natural da máscara calculadora).
    var len = e.target.value.length;
    try {
      e.target.setSelectionRange(len, len);
    } catch (_) {
      /* alguns tipos de input não suportam setSelectionRange */
    }
  }

  function init(root) {
    var scope = root || document;
    scope.querySelectorAll("input.brl-input").forEach(function (input) {
      if (input.dataset.brlBound === "1") return;
      input.dataset.brlBound = "1";
      // Normaliza o valor inicial (ex.: vindo do servidor) para o padrão.
      if (input.value) applyMask(input);
      input.addEventListener("input", onInput);
    });
  }

  // Exposto para reinicializar campos inseridos dinamicamente (ex.: linhas de personagem).
  window.MoneyMask = { init: init, format: formatCents, applyMask: applyMask };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", function () {
      init();
    });
  } else {
    init();
  }
})();
