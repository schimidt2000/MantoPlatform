/**
 * Lista de desejos do catálogo público (feature 140).
 *
 * 100% client-side (localStorage) — não existe conta de cliente na parte pública do
 * catálogo, então a lista fica só no navegador da pessoa (sobrevive a fechar a aba,
 * não sincroniza entre aparelhos). Usado por index.html, detail.html, categorias.html,
 * categoria_detail.html (widget flutuante) e lista_desejos.html (página completa).
 */
(function (root) {
  var KEY = "manto_catalogo_wishlist";

  function getAll() {
    try {
      var raw = root.localStorage.getItem(KEY);
      var list = raw ? JSON.parse(raw) : [];
      return Array.isArray(list) ? list : [];
    } catch (e) {
      return [];
    }
  }

  function saveAll(list) {
    try {
      root.localStorage.setItem(KEY, JSON.stringify(list));
    } catch (e) {
      /* localStorage indisponível (modo privado/cota) — degrada sem quebrar a página */
    }
  }

  function has(slug) {
    return getAll().some(function (i) { return i.slug === slug; });
  }

  function add(item) {
    var list = getAll();
    if (!item || !item.slug || list.some(function (i) { return i.slug === item.slug; })) {
      return list;
    }
    list.push({ slug: item.slug, name: item.name || "", cover: item.cover || "" });
    saveAll(list);
    return list;
  }

  function remove(slug) {
    var list = getAll().filter(function (i) { return i.slug !== slug; });
    saveAll(list);
    return list;
  }

  function toggle(item) {
    return has(item.slug) ? remove(item.slug) : add(item);
  }

  function count() {
    return getAll().length;
  }

  function buildMessage(baseUrl) {
    var list = getAll();
    if (!list.length) return "";
    var lines = ["Olá! Vi esses personagens no catálogo e gostaria de saber mais:", ""];
    list.forEach(function (i) {
      lines.push("• " + i.name + " — " + baseUrl + "/catalogo/" + i.slug);
    });
    return lines.join("\n");
  }

  function whatsappUrl(phoneNumber, baseUrl) {
    var msg = buildMessage(baseUrl);
    if (!msg) return null;
    return "https://api.whatsapp.com/send?phone=" + phoneNumber + "&text=" + encodeURIComponent(msg);
  }

  var api = {
    KEY: KEY,
    getAll: getAll,
    has: has,
    add: add,
    remove: remove,
    toggle: toggle,
    count: count,
    buildMessage: buildMessage,
    whatsappUrl: whatsappUrl,
  };

  root.MantoWishlist = api;
  if (typeof module !== "undefined" && module.exports) {
    module.exports = api;
  }
})(typeof window !== "undefined" ? window : global);
