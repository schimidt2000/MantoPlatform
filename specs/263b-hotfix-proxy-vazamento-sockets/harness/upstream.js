// Backend falso para o verify_263b.py — faz o papel do Flask/gunicorn atrás do proxy do
// frontend/server.js. Só existe para observar o que o PROXY faz com a conexão quando o cliente
// some: quantas respostas continuam abertas, quantas fecharam sem terminar e quando.
//
//   UPSTREAM_PORT=45101 node upstream.js
//
// Rotas:
//   GET  /uploads/big?mb=N   corpo de N MB (padrão 300), video/mp4, chunks de 64 KB respeitando
//   GET  /api/x?mb=N         backpressure (write() false → espera 'drain'); aceita Range: bytes=A-
//   GET  /api/json           JSON pequeno
//   POST /api/3d/nfc/1/entregas   lê o corpo devagar (200 ms por MB) e responde {"bytes": n}
//   POST /api/lento          lê o corpo inteiro, espera 3 s e responde {"bytes": n}
//   GET  /__stats            contadores (a própria conexão do /__stats é descontada)
//   GET  /__reset            zera os contadores
"use strict";
const http = require("node:http");

const PORT = Number(process.env.UPSTREAM_PORT || 45101);
const CHUNK = Buffer.alloc(64 * 1024, 0x41);
const ts = () => new Date().toISOString().slice(11, 23);
const log = (...a) => console.log(`[${ts()}] [upstream]`, ...a);

let seq = 0;
const abertas = new Map(); // id → { url, escritos, inicio }
const contadores = novoContador();

function novoContador() {
  return {
    iniciadas: 0,
    concluidas: 0, // res 'close' com writableFinished === true
    fechadas_incompletas: 0, // res 'close' com writableFinished === false (cliente/proxy soltou)
    lento_fechou_antes: 0, // /api/lento: socket fechou antes de a resposta sair
    lento_respondidas: 0,
    ultima_fechada_incompleta_ms: null, // quanto tempo depois do início a última soltura chegou
  };
}

const server = http.createServer((req, res) => {
  const id = ++seq;
  const [pathOnly, query = ""] = req.url.split("?");
  const params = new URLSearchParams(query);

  if (pathOnly === "/__stats") {
    server.getConnections((err, n) => {
      res.setHeader("content-type", "application/json");
      res.end(
        JSON.stringify({
          ...contadores,
          conexoes: err ? -1 : Math.max(0, n - 1),
          respostas_abertas: abertas.size,
          abertas: [...abertas.values()].map((a) => ({ url: a.url, escritos: a.escritos, ha_ms: Date.now() - a.inicio })),
        }),
      );
    });
    return;
  }
  if (pathOnly === "/__reset") {
    Object.assign(contadores, novoContador());
    res.setHeader("content-type", "application/json");
    res.end('{"ok":true}');
    return;
  }

  contadores.iniciadas += 1;
  const info = { url: req.url, escritos: 0, inicio: Date.now() };
  abertas.set(id, info);
  log(`#${id} ${req.method} ${req.url} range=${req.headers.range ?? "-"}`);
  res.on("close", () => {
    abertas.delete(id);
    if (res.writableFinished) contadores.concluidas += 1;
    else {
      contadores.fechadas_incompletas += 1;
      contadores.ultima_fechada_incompleta_ms = Date.now() - info.inicio;
    }
    log(`#${id} res 'close' escritos=${info.escritos} terminou=${res.writableFinished} apos=${Date.now() - info.inicio}ms`);
  });

  // Backend que MORRE no meio da resposta (deploy, worker reciclado): escreve 1 MB e destrói o
  // socket meio segundo depois. Serve para conferir que o cliente recebe EOF/erro, não silêncio.
  if (pathOnly === "/api/morre") {
    res.setHeader("content-type", "video/mp4");
    res.setHeader("content-length", String(4 * 1024 * 1024));
    res.write(Buffer.alloc(1024 * 1024, 0x44));
    info.escritos = 1024 * 1024;
    setTimeout(() => req.socket.destroy(), 500);
    return;
  }

  if (pathOnly === "/api/json") {
    res.setHeader("content-type", "application/json");
    res.end(JSON.stringify({ ok: true, n: 42 }));
    return;
  }

  if (req.method === "POST" && pathOnly === "/api/3d/nfc/1/entregas") {
    let lidos = 0;
    let proximaPausa = 1024 * 1024;
    req.on("data", (c) => {
      lidos += c.length;
      if (lidos >= proximaPausa) {
        proximaPausa += 1024 * 1024;
        req.pause();
        setTimeout(() => req.resume(), 200);
      }
    });
    req.on("end", () => {
      res.setHeader("content-type", "application/json");
      res.end(JSON.stringify({ bytes: lidos }));
    });
    return;
  }

  if (req.method === "POST" && pathOnly === "/api/lento") {
    let lidos = 0;
    let fechou = false;
    req.socket.once("close", () => {
      fechou = true;
    });
    req.on("data", (c) => (lidos += c.length));
    req.on("end", () => {
      setTimeout(() => {
        if (fechou || res.destroyed) {
          contadores.lento_fechou_antes += 1;
          log(`#${id} /api/lento: socket já tinha fechado antes da resposta`);
          if (!res.destroyed) res.destroy();
          return;
        }
        contadores.lento_respondidas += 1;
        res.setHeader("content-type", "application/json");
        res.end(JSON.stringify({ bytes: lidos }));
      }, 3000);
    });
    return;
  }

  if (pathOnly === "/uploads/big" || pathOnly === "/api/x") {
    const total = Math.round(Number(params.get("mb") || 300) * 1024 * 1024);
    let inicio = 0;
    const m = /^bytes=(\d+)-/.exec(req.headers.range ?? "");
    if (m) {
      inicio = Number(m[1]);
      res.statusCode = 206;
      res.setHeader("content-range", `bytes ${inicio}-${total - 1}/${total}`);
      res.setHeader("accept-ranges", "bytes");
    }
    res.setHeader("content-type", "video/mp4");
    res.setHeader("content-length", String(total - inicio));
    let restam = total - inicio;
    const bombear = () => {
      while (restam > 0) {
        const n = Math.min(CHUNK.length, restam);
        const ok = res.write(n === CHUNK.length ? CHUNK : CHUNK.subarray(0, n));
        restam -= n;
        info.escritos += n;
        if (!ok) {
          res.once("drain", bombear);
          return;
        }
      }
      res.end();
    };
    bombear();
    return;
  }

  res.statusCode = 404;
  res.end("nao encontrado");
});

server.listen(PORT, "127.0.0.1", () => log(`ouvindo em 127.0.0.1:${PORT}`));
