// Buscador de respostas de formulário de pré-contrato na criação de evento (feature 118).
// Mesmo padrão do client_picker.js: debounce + resultados + seleção com hidden input.
(function () {
  "use strict";

  var block = document.getElementById("form-response-block");
  if (!block) return;

  var searchUrl = block.dataset.searchUrl;
  var hidden = document.getElementById("form-response-id");
  var selected = document.getElementById("form-response-selected");
  var selName = document.getElementById("form-response-name");
  var selMeta = document.getElementById("form-response-meta");
  var removeBtn = document.getElementById("form-response-remove");
  var searchWrap = document.getElementById("form-response-search-wrap");
  var input = document.getElementById("form-response-search");
  var results = document.getElementById("form-response-results");
  var timer = null;

  function select(item) {
    hidden.value = item.id;
    selName.textContent = item.name;
    var meta = item.form_type;
    if (item.event_date) meta += " · evento em " + item.event_date;
    meta += " · recebido em " + item.created_at;
    selMeta.textContent = meta;
    selected.style.display = "flex";
    searchWrap.style.display = "none";
    results.style.display = "none";
    input.value = "";
  }

  removeBtn.addEventListener("click", function () {
    hidden.value = "";
    selected.style.display = "none";
    searchWrap.style.display = "";
  });

  input.addEventListener("input", function () {
    clearTimeout(timer);
    var q = input.value.trim();
    if (q.length < 2) { results.style.display = "none"; return; }
    timer = setTimeout(function () {
      fetch(searchUrl + "?q=" + encodeURIComponent(q))
        .then(function (r) { return r.json(); })
        .then(function (list) {
          results.innerHTML = "";
          if (!list.length) {
            var empty = document.createElement("div");
            empty.className = "meta";
            empty.style.cssText = "padding:8px 12px; font-size:12.5px;";
            empty.textContent = "Nenhuma resposta encontrada.";
            results.appendChild(empty);
          }
          list.forEach(function (item) {
            var row = document.createElement("div");
            row.style.cssText = "padding:8px 12px; cursor:pointer; border-bottom:1px solid #eee; font-size:13.5px;";
            var title = document.createElement("div");
            title.style.fontWeight = "600";
            title.textContent = item.name;
            var meta = document.createElement("div");
            meta.className = "meta";
            meta.style.fontSize = "12px";
            meta.textContent = item.form_type +
              (item.phone_display ? " · " + item.phone_display : "") +
              (item.event_date ? " · evento em " + item.event_date : "");
            row.appendChild(title);
            row.appendChild(meta);
            row.addEventListener("click", function () { select(item); });
            row.addEventListener("mouseenter", function () { row.style.background = "#f4f2f7"; });
            row.addEventListener("mouseleave", function () { row.style.background = ""; });
            results.appendChild(row);
          });
          results.style.display = "block";
        })
        .catch(function () { results.style.display = "none"; });
    }, 250);
  });

  document.addEventListener("click", function (e) {
    if (!block.contains(e.target)) results.style.display = "none";
  });
})();
