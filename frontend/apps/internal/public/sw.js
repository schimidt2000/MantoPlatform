/*
 * Service worker da Plataforma Manto (feature 332): só os avisos no celular.
 *
 * Sem cache de página e sem modo offline, de propósito: o deploy troca o bundle, e um service
 * worker com cache seguraria a versão velha na tela da equipe (o mesmo motivo do `no-cache` do
 * `server.js`). O aviso chega cifrado do servidor (Web Push); o navegador entrega já decifrado.
 * Contrato do corpo: `{titulo, corpo, link, tag}` (specs/332-crm-avisos-no-celular/contracts/api.md).
 */

self.addEventListener("install", () => self.skipWaiting());
self.addEventListener("activate", (event) => event.waitUntil(self.clients.claim()));

self.addEventListener("push", (event) => {
  let aviso = {};
  try {
    aviso = event.data ? event.data.json() : {};
  } catch (erro) {
    aviso = {};
  }
  const opcoes = {
    body: aviso.corpo || "",
    icon: "/icone-192.png",
    lang: "pt-BR",
    data: { link: aviso.link || "/conversas" },
  };
  if (aviso.tag) {
    // Avisos da mesma conversa se substituem; `renotify` faz o novo tocar mesmo assim.
    opcoes.tag = aviso.tag;
    opcoes.renotify = true;
  }
  event.waitUntil(self.registration.showNotification(aviso.titulo || "Plataforma Manto", opcoes));
});

/** Só caminhos da própria Plataforma: o link do aviso nunca leva para fora. */
function destinoDoAviso(link) {
  const url = new URL(link || "/conversas", self.location.origin);
  return url.origin === self.location.origin ? url.href : new URL("/conversas", self.location.origin).href;
}

self.addEventListener("notificationclick", (event) => {
  event.notification.close();
  const destino = destinoDoAviso(event.notification.data && event.notification.data.link);
  event.waitUntil(
    (async () => {
      const abas = await self.clients.matchAll({ type: "window", includeUncontrolled: true });
      for (const aba of abas) {
        if (new URL(aba.url).origin !== self.location.origin) continue;
        try {
          await aba.focus();
          await aba.navigate(destino);
          return;
        } catch (erro) {
          // Aba que este service worker não controla não aceita `navigate`: abre uma nova.
        }
      }
      await self.clients.openWindow(destino);
    })(),
  );
});

// O navegador trocou a assinatura deste aparelho (expirou ou foi renovada): registra a nova. A
// antiga some sozinha no servidor no próximo aviso (o serviço responde 410).
self.addEventListener("pushsubscriptionchange", (event) => {
  event.waitUntil(
    (async () => {
      const opcoes = event.oldSubscription && event.oldSubscription.options;
      const nova = event.newSubscription || (opcoes ? await self.registration.pushManager.subscribe(opcoes) : null);
      if (!nova) return;
      await fetch("/api/push/aparelhos", {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(nova.toJSON()),
      });
    })(),
  );
});
