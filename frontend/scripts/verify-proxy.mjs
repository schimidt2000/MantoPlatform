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
