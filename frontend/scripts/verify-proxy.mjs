/**
 * Verificação funcional do proxy reverso de `frontend/server.js` (feature 206).
 *
 * Sobe um backend falso no lugar do Flask e o servidor de produção real, e confere para onde cada
 * URL vai: backend, bundle interno, bundle público ou bundle do portal — mais o comportamento com
 * o backend fora do ar. Os dois casos que motivam o teste são de ordem: `/catalogo/midia/*` e
 * `/portal/photo/*` são sub-caminhos de prefixos montados, e viram `index.html` se o bloco de
 * proxy rodar depois dos mounts.
 *
 * Requer os três `dist` compilados (`npm run build`).
 *
 * Uso:
 *     node scripts/verify-proxy.mjs        # a partir de frontend/
 */
import http from "node:http";
import path from "node:path";
import { spawn } from "node:child_process";
import { fileURLToPath } from "node:url";

const FRONTEND_DIR = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const BACKEND_PORT = 5099;
const FRONT_PORT = 3099;

const backend = http.createServer((req, res) => {
  res.setHeader("content-type", "text/plain");
  res.end(
    `BACKEND ${req.method} ${req.url} host=${req.headers.host} xff=${req.headers["x-forwarded-for"] ?? "-"}`,
  );
});
await new Promise((resolve) => backend.listen(BACKEND_PORT, "127.0.0.1", resolve));

const server = spawn(process.execPath, ["server.js"], {
  cwd: FRONTEND_DIR,
  env: { ...process.env, PORT: String(FRONT_PORT), BACKEND_URL: `http://127.0.0.1:${BACKEND_PORT}` },
  stdio: ["ignore", "ignore", "pipe"],
});
server.stderr.on("data", (chunk) => {
  const text = String(chunk);
  if (!text.includes("DeprecationWarning")) process.stdout.write(`  [server] ${text}`);
});
await new Promise((resolve) => setTimeout(resolve, 1200));

/** Classifica a resposta: backend, ou qual bundle SPA respondeu. */
function classify(status, body) {
  if (body.startsWith("BACKEND ")) return "backend";
  if (status === 502) return "502";
  if (body.includes("/catalogo/assets/")) return "spa:public";
  if (body.includes("/portal/assets/")) return "spa:portal";
  if (/<html/i.test(body) || /<!doctype html>/i.test(body)) return "spa:internal";
  return `outro(${status})`;
}

const CASES = [
  ["/api/dashboard", "backend"],
  ["/api", "backend"],
  ["/api/portal/auth/login", "backend"],
  ["/apiary", "spa:internal"],
  ["/uploads/talent_photos/x.jpg", "backend"],
  ["/uploads", "backend"],
  ["/catalogo/midia/tema.jpg", "backend"],
  ["/catalogo", "spa:public"],
  ["/catalogo/tema/frozen", "spa:public"],
  ["/portal/photo/ficha.jpg", "backend"],
  ["/portal", "spa:portal"],
  ["/portal/agenda", "spa:portal"],
  ["/google/callback?code=x", "backend"],
  ["/google/connect", "backend"],
  ["/cadastro", "backend"],
  ["/cadastro/check-cpf", "backend"],
  ["/avaliar/token123", "backend"],
  ["/static/style.css", "backend"],
  ["/formularios", "spa:internal"],
  ["/figurinos/12/print", "backend"],
  ["/figurinos/12/print?debug=1", "backend"],
  ["/figurinos", "spa:internal"],
  ["/figurinos/12", "spa:internal"],
  ["/", "spa:internal"],
  ["/agenda", "spa:internal"],
];

let failed = 0;
const check = (ok, label) => {
  if (!ok) failed++;
  console.log(`  [${ok ? "OK " : "XX "}] ${label}`);
};

console.log("\n=== Roteamento ===");
for (const [url, expected] of CASES) {
  const response = await fetch(`http://127.0.0.1:${FRONT_PORT}${url}`, { redirect: "manual" });
  const got = classify(response.status, await response.text());
  check(got === expected, `${url.padEnd(34)} → ${got}${got === expected ? "" : ` (esperado ${expected})`}`);
}

console.log("\n=== Formularios publicos: /f/<slug> canonico -> React da vitrine ===");
const FORM_CASES = [
  ["/f/pre-contrato", "/catalogo/f/pre-contrato", "link antigo abre o formulario novo"],
  ["/f/corporativo?utm_source=bio", "/catalogo/f/corporativo?utm_source=bio", "query preservada"],
];
for (const [url, expected, nota] of FORM_CASES) {
  const r = await fetch(`http://127.0.0.1:${FRONT_PORT}${url}`, { redirect: "manual" });
  const loc = r.headers.get("location");
  check(r.status === 302 && loc === expected, `${url.padEnd(34)} → ${r.status} ${loc} (${nota})`);
}
// O destino do redirect e servido pela SPA publica (nao pelo Jinja nem pelo ERP)
const formDest = await fetch(`http://127.0.0.1:${FRONT_PORT}/catalogo/f/pre-contrato`, { redirect: "manual" });
const formDestBody = await formDest.text();
check(
  formDest.status === 200 && formDestBody.includes("/catalogo/assets/"),
  `/catalogo/f/pre-contrato → ${formDest.status} bundle da SPA publica`,
);

console.log("\n=== Host dedicado do portal ===");

/**
 * GET com `Host` arbitrário. Precisa ser `node:http` cru: o `fetch` (undici) trata `host` como
 * header proibido e o descarta silenciosamente — o teste passaria a medir outra coisa.
 */
function rawGet(pathname, hostHeader) {
  return new Promise((resolve, reject) => {
    const request = http.request(
      { host: "127.0.0.1", port: FRONT_PORT, path: pathname, headers: { Host: hostHeader } },
      (response) => {
        let body = "";
        response.on("data", (chunk) => (body += chunk));
        response.on("end", () =>
          resolve({ status: response.statusCode, location: response.headers.location, body }),
        );
      },
    );
    request.on("error", reject);
    request.end();
  });
}

const PORTAL_HOST = "portal.mantoproducoes.com.br";
const PORTAL_CASES = [
  ["/", "/portal/", "raiz vai para o portal, nao para o ERP interno"],
  ["/reset-password/abc123", "/portal/reset-password/abc123", "token do e-mail preservado"],
  ["/agenda?x=1", "/portal/agenda?x=1", "query preservada"],
];
for (const [url, expected, nota] of PORTAL_CASES) {
  const r = await rawGet(url, PORTAL_HOST);
  check(r.status === 302 && r.location === expected, `${url.padEnd(26)} → ${r.status} ${r.location} (${nota})`);
}
// Ja dentro de /portal nao pode redirecionar de novo (laco) nem roubar a API.
const noLoop = await rawGet("/portal/agenda", PORTAL_HOST);
check(noLoop.status === 200, `/portal/agenda ja prefixado → ${noLoop.status} (sem laco)`);
check(
  (await rawGet("/api/auth/me", PORTAL_HOST)).body.startsWith("BACKEND"),
  "/api no host do portal → ainda vai para o backend",
);
// Host normal continua entregando o ERP interno na raiz.
const internal = await rawGet("/", "app.mantoproducoes.com.br");
check(internal.status === 200, `/ em app.* → ${internal.status} (ERP interno, sem redirect)`);

// Sem `Cache-Control`, o navegador guarda o index.html por heurística e continua pedindo o
// bundle da versão anterior — o deploy sobe, a sondagem em produção passa e o usuário segue no
// JavaScript velho. Os dois lados do contrato precisam valer.
console.log("\n=== Cache do navegador ===");
for (const rota of ["/", "/agenda", "/catalogo", "/portal/"]) {
  const r = await fetch(`http://127.0.0.1:${FRONT_PORT}${rota}`);
  check(
    r.headers.get("cache-control") === "no-cache",
    `${rota.padEnd(12)} → cache-control: ${r.headers.get("cache-control")} (HTML revalida sempre)`,
  );
}
const htmlRaiz = await (await fetch(`http://127.0.0.1:${FRONT_PORT}/`)).text();
const assetPath = (htmlRaiz.match(/src="(\/assets\/[^"]+\.js)"/) || [])[1];
if (assetPath) {
  const asset = await fetch(`http://127.0.0.1:${FRONT_PORT}${assetPath}`);
  const cc = asset.headers.get("cache-control") || "";
  check(
    cc.includes("immutable") && cc.includes("max-age=31536000"),
    `${assetPath.slice(0, 24).padEnd(26)} → ${cc} (hash no nome ⇒ imutável)`,
  );
} else {
  check(false, "não achou o bundle no index.html para checar o cache do asset");
}

console.log("\n=== Cabeçalhos repassados ===");
const probe = await (await fetch(`http://127.0.0.1:${FRONT_PORT}/api/ping`)).text();
check(probe.includes(`host=127.0.0.1:${BACKEND_PORT}`), "changeOrigin reescreve o Host para o backend");
check(!probe.includes("xff=-"), "xfwd envia X-Forwarded-For");

console.log("\n=== Backend fora do ar ===");
await new Promise((resolve) => backend.close(resolve));
const down = await fetch(`http://127.0.0.1:${FRONT_PORT}/api/dashboard`);
check(down.status === 502 && (await down.text()).includes("Bad Gateway"), "/api → 502 Bad Gateway");
check((await fetch(`http://127.0.0.1:${FRONT_PORT}/agenda`)).status === 200, "SPA continua servindo");

server.kill();
console.log(`\n${failed === 0 ? "TODOS OS CHECKS OK" : `${failed} FALHA(S)`}`);
process.exit(failed === 0 ? 0 : 1);
