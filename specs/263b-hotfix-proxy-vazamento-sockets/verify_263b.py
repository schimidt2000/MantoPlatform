"""Verificação do hotfix 263b — o proxy do frontend solta o backend quando o cliente some.

O defeito: `frontend/server.js` (http-proxy 1.18.1) só desligava a conexão com o Flask em
`req.on('aborted')`, que em Node moderno nunca dispara para um GET cujo cliente some DURANTE a
resposta. O `proxyRes` ficava pausado, o kernel enchia a fila de recepção do socket e o socket
ficava em CLOSE_WAIT para sempre — em mídia (prazo 0) sem nenhum prazo que limpasse. Em produção:
432 MB de `sock` no cgroup, 142 sockets, processo Node em 85 MB, contêiner morto por memória
(08/09 e 10/09/2026).

Este verify NÃO usa o `manto_local`: o defeito é do proxy Node, então o "banco" aqui é um backend
falso em Node (`harness/upstream.js`) que conta o que acontece com cada conexão. O proxy testado é
o `server.js` de verdade, rodando de dentro de `frontend/` (os `dist/` das três SPAs precisam
existir — `npm run build`).

Cenários (cada um mede e imprime números):
  1. Download de mídia abandonado (GET /uploads/big, 5 clientes leem 2 MB e fecham): o backend
     vê as 5 respostas fecharem em < 10 s e fica com 0 conexões. Antes do hotfix: 5 presas.
  2. Backend terminou de escrever antes de o cliente sumir (arquivo de 0,6 MB, cliente lê 0,1 MB):
     nenhum socket do proxy fica em CLOSE_WAIT com o backend. Antes: 5 CLOSE_WAIT eternos.
  3. Mesmo abandono numa rota /api (prazo de 180 s): solta em < 10 s, não em 180 s.
  4. Cliente manda o corpo inteiro e some antes de o Flask responder (POST /api/lento, que demora
     3 s): o backend vê o socket fechar antes de responder; nada fica em CLOSE_WAIT.
  4b. O inverso: o backend cai no meio da resposta (GET /api/morre) e o cliente recebe EOF/erro
     em < 3 s — não silêncio (é o que faz o player refazer o `Range`).
  5. Download completo de 40 MB por Range: 206 e todos os bytes.
  6. Upload completo de 20 MB com backend lendo devagar (200 ms/MB): 200 e todos os bytes.
  7. GET /api/json, SPA (`/` e `/nfc/<code>`), redirect `/f/<slug>?q` → `/catalogo/f/<slug>?q`.
  8. Nenhuma linha `[proxy]` de 502 no log do proxy para cliente que abortou (não é falha do
     backend, não pode aparecer como Bad Gateway).
  9. Guardas estáticas no fonte: mídia com prazo de inatividade (não zero), `requestTimeout` de 30
     min, ganchos de `res 'close'`/`res 'pipe'`/`proxyReq 'close'` presentes.
  10. Um segundo proxy apontando para porta fechada: `/api/*` responde 502 "Bad Gateway" e a SPA
     continua de pé (o caminho de erro não mudou).

Rodar (PowerShell, da raiz do repositório)::

    python specs\\263b-hotfix-proxy-vazamento-sockets\\verify_263b.py
    python specs\\263b-hotfix-proxy-vazamento-sockets\\verify_263b.py --antes   # server.js da main:
                                                                                # deve FALHAR em 1-4

Opções: --server <caminho/server.js> (outro proxy; precisa estar dentro de uma pasta com
`node_modules` e `apps/*/dist`), --porta-upstream/--porta-proxy (padrão 45101/45102),
--manter-logs (não apaga a pasta de logs).
"""
from __future__ import annotations

import argparse
import http.client
import json
import os
import platform
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
FRONTEND = REPO_ROOT / "frontend"
HARNESS = Path(__file__).resolve().parent / "harness"
MB = 1024 * 1024
WINDOWS = platform.system() == "Windows"

resultados: list[tuple[str, bool, str]] = []


def registra(nome: str, ok: bool, detalhe: str) -> None:
    resultados.append((nome, ok, detalhe))
    print(f"{'PASS' if ok else 'FAIL'}  {nome} — {detalhe}", flush=True)


# ── processos ───────────────────────────────────────────────────────────────────────────────


def porta_ouvindo(porta: int) -> bool:
    with socket.socket() as s:
        s.settimeout(0.3)
        return s.connect_ex(("127.0.0.1", porta)) == 0


def espera_porta(porta: int, segundos: float = 15) -> bool:
    fim = time.time() + segundos
    while time.time() < fim:
        if porta_ouvindo(porta):
            return True
        time.sleep(0.2)
    return False


def mata(proc: subprocess.Popen | None) -> None:
    if proc is None or proc.poll() is not None:
        return
    if WINDOWS:
        subprocess.run(["taskkill", "/PID", str(proc.pid), "/T", "/F"], capture_output=True)
    else:
        proc.terminate()
    try:
        proc.wait(5)
    except subprocess.TimeoutExpired:
        proc.kill()


# ── clientes ────────────────────────────────────────────────────────────────────────────────


def conexao(porta: int) -> http.client.HTTPConnection:
    return http.client.HTTPConnection("127.0.0.1", porta, timeout=60)


def get_json(porta: int, caminho: str) -> dict:
    c = conexao(porta)
    c.request("GET", caminho, headers={"Connection": "close"})
    r = c.getresponse()
    corpo = r.read()
    c.close()
    return json.loads(corpo)


def stats(porta_upstream: int) -> dict:
    return get_json(porta_upstream, "/__stats")


def get_e_abandonar(porta_proxy: int, caminho: str, ler: int) -> tuple[str, int]:
    """GET com Range, lê `ler` bytes e FECHA o socket com dados ainda chegando (o celular que some)."""
    s = socket.create_connection(("127.0.0.1", porta_proxy), timeout=30)
    s.sendall(
        f"GET {caminho} HTTP/1.1\r\nHost: 127.0.0.1\r\nRange: bytes=0-\r\nConnection: keep-alive\r\n\r\n".encode()
    )
    primeiro = s.recv(65536)
    status = primeiro.split(b"\r\n", 1)[0].decode(errors="replace")
    lidos = len(primeiro)
    while lidos < ler:
        pedaco = s.recv(65536)
        if not pedaco:
            break
        lidos += len(pedaco)
    s.close()
    return status, lidos


def get_completo(porta_proxy: int, caminho: str, cabecalhos: dict | None = None) -> tuple[int, dict, int, bytes]:
    c = conexao(porta_proxy)
    c.request("GET", caminho, headers={"Connection": "close", **(cabecalhos or {})})
    r = c.getresponse()
    total = 0
    inicio = b""
    while True:
        pedaco = r.read(1024 * 1024)
        if not pedaco:
            break
        if not inicio:
            inicio = pedaco[:4096]
        total += len(pedaco)
    c.close()
    return r.status, dict(r.getheaders()), total, inicio


def post_upload(porta_proxy: int, caminho: str, tamanho: int) -> tuple[int, dict]:
    c = conexao(porta_proxy)
    c.putrequest("POST", caminho)
    c.putheader("Content-Type", "application/octet-stream")
    c.putheader("Content-Length", str(tamanho))
    c.putheader("Connection", "close")
    c.endheaders()
    pedaco = b"B" * 65536
    restam = tamanho
    while restam > 0:
        n = min(len(pedaco), restam)
        c.send(pedaco[:n])
        restam -= n
    r = c.getresponse()
    corpo = json.loads(r.read() or b"{}")
    c.close()
    return r.status, corpo


def post_e_sumir(porta_proxy: int, caminho: str, tamanho: int) -> None:
    """Manda cabeçalhos + corpo inteiro e fecha sem esperar a resposta."""
    s = socket.create_connection(("127.0.0.1", porta_proxy), timeout=30)
    s.sendall(
        f"POST {caminho} HTTP/1.1\r\nHost: 127.0.0.1\r\nContent-Type: application/octet-stream\r\n"
        f"Content-Length: {tamanho}\r\n\r\n".encode()
    )
    s.sendall(b"C" * tamanho)
    s.close()


# ── sockets do proxy com o backend ──────────────────────────────────────────────────────────


def conexoes_do_proxy(pid_proxy: int, porta_upstream: int) -> dict[str, int]:
    """Estados dos sockets do PID do proxy cujo par é a porta do backend (netstat/ss)."""
    contagem: dict[str, int] = {}
    if WINDOWS:
        saida = subprocess.run(["netstat", "-ano", "-p", "TCP"], capture_output=True, text=True).stdout
        for linha in saida.splitlines():
            partes = linha.split()
            if len(partes) != 5 or partes[0] != "TCP":
                continue
            _, _local, remoto, estado, pid = partes
            if pid == str(pid_proxy) and remoto.endswith(f":{porta_upstream}"):
                contagem[estado] = contagem.get(estado, 0) + 1
    else:
        saida = subprocess.run(["ss", "-tanp"], capture_output=True, text=True).stdout
        for linha in saida.splitlines()[1:]:
            partes = linha.split()
            if len(partes) < 5:
                continue
            estado, remoto = partes[0], partes[4]
            if remoto.endswith(f":{porta_upstream}") and f"pid={pid_proxy}," in linha:
                estado = {"ESTAB": "ESTABLISHED", "CLOSE-WAIT": "CLOSE_WAIT"}.get(estado, estado)
                contagem[estado] = contagem.get(estado, 0) + 1
    return contagem


def espera(condicao, segundos: float, passo: float = 0.5) -> tuple[bool, float]:
    """Espera `condicao()` ficar verdadeira; devolve (conseguiu, segundos gastos)."""
    inicio = time.time()
    while time.time() - inicio < segundos:
        if condicao():
            return True, time.time() - inicio
        time.sleep(passo)
    return condicao(), time.time() - inicio


# ── cenários ────────────────────────────────────────────────────────────────────────────────


def cenario_abandono(nome: str, porta_proxy: int, porta_upstream: int, pid_proxy: int, caminho: str, ler: int, n: int) -> None:
    get_json(porta_upstream, "/__reset")
    for i in range(n):
        status, lidos = get_e_abandonar(porta_proxy, caminho, ler)
        assert "206" in status or "200" in status, f"{nome}: status inesperado {status!r}"
        assert lidos >= min(ler, 65536), f"{nome}: cliente #{i + 1} leu só {lidos} bytes"

    def solto() -> bool:
        s = stats(porta_upstream)
        c = conexoes_do_proxy(pid_proxy, porta_upstream)
        return s["conexoes"] == 0 and s["fechadas_incompletas"] + s["concluidas"] >= n and not any(
            estado in ("ESTABLISHED", "CLOSE_WAIT") for estado in c
        )

    ok, gasto = espera(solto, 12)
    s = stats(porta_upstream)
    c = conexoes_do_proxy(pid_proxy, porta_upstream)
    registra(
        nome,
        ok,
        f"{n} clientes abortaram lendo {ler // 1024} KB de {caminho}; backend: conexoes={s['conexoes']} "
        f"fechadas_incompletas={s['fechadas_incompletas']} concluidas={s['concluidas']} abertas={s['respostas_abertas']}; "
        f"sockets do proxy com o backend: {c or '{}'}; {'soltou' if ok else 'AINDA PRESO'} em {gasto:.1f}s",
    )


def cenario_some_antes_da_resposta(porta_proxy: int, porta_upstream: int, pid_proxy: int) -> None:
    get_json(porta_upstream, "/__reset")
    for _ in range(3):
        post_e_sumir(porta_proxy, "/api/lento", 256 * 1024)

    def fechou() -> bool:
        s = stats(porta_upstream)
        c = conexoes_do_proxy(pid_proxy, porta_upstream)
        return s["lento_fechou_antes"] == 3 and s["conexoes"] == 0 and c.get("CLOSE_WAIT", 0) == 0 and c.get("ESTABLISHED", 0) == 0

    ok, gasto = espera(fechou, 8)
    s = stats(porta_upstream)
    c = conexoes_do_proxy(pid_proxy, porta_upstream)
    registra(
        "4. cliente some depois do corpo, antes da resposta (POST /api/lento, 3 s)",
        ok,
        f"backend: fechou_antes={s['lento_fechou_antes']} respondidas={s['lento_respondidas']} conexoes={s['conexoes']}; "
        f"sockets do proxy: {c or '{}'}; {gasto:.1f}s",
    )


def cenario_backend_morre(porta_proxy: int, porta_upstream: int) -> None:
    """O caminho inverso: o backend cai no meio da resposta e o cliente precisa saber (EOF/erro), não
    ficar mudo esperando um `end` que nunca vem — é o que faz o player refazer o `Range`."""
    get_json(porta_upstream, "/__reset")
    s = socket.create_connection(("127.0.0.1", porta_proxy), timeout=3)
    s.sendall(b"GET /api/morre HTTP/1.1\r\nHost: 127.0.0.1\r\nConnection: close\r\n\r\n")
    inicio = time.time()
    lidos = 0
    fim = "silencio"
    try:
        while True:
            pedaco = s.recv(65536)
            if not pedaco:
                fim = "EOF"
                break
            lidos += len(pedaco)
    except ConnectionResetError:
        fim = "RST"
    except TimeoutError:
        fim = "silencio (3 s sem nada)"
    finally:
        s.close()
    gasto = time.time() - inicio
    registra(
        "4b. backend morre no meio da resposta → cliente recebe o fim, não silêncio",
        fim in ("EOF", "RST") and gasto < 3,
        f"cliente leu {lidos} bytes e viu {fim} em {gasto:.1f}s (backend escreveu 1 MB e caiu aos 0,5 s)",
    )


def cenario_backend_fora(porta_proxy_502: int) -> None:
    status, _, _, inicio = get_completo(porta_proxy_502, "/api/json")
    registra("10a. backend fora do ar → 502 texto, sem derrubar o processo", status == 502 and inicio.strip() == b"Bad Gateway", f"status={status} corpo={inicio[:40]!r}")
    status, cab, _, inicio = get_completo(porta_proxy_502, "/")
    tipo = cab.get("Content-Type") or cab.get("content-type") or ""
    registra("10b. backend fora do ar → SPA continua de pé", status == 200 and "text/html" in tipo, f"status={status} tipo={tipo}")


def cenarios_legitimos(porta_proxy: int, porta_upstream: int, pid_proxy: int) -> None:
    get_json(porta_upstream, "/__reset")
    status, cab, total, _ = get_completo(porta_proxy, "/uploads/big?mb=40", {"Range": "bytes=0-"})
    registra(
        "5. download completo de 40 MB por Range",
        status == 206 and total == 40 * MB,
        f"status={status} bytes={total} content-range={cab.get('Content-Range') or cab.get('content-range')}",
    )

    status, corpo = post_upload(porta_proxy, "/api/3d/nfc/1/entregas", 20 * MB)
    registra("6. upload completo de 20 MB com backend lento", status == 200 and corpo.get("bytes") == 20 * MB, f"status={status} bytes={corpo.get('bytes')}")

    status, _, _, inicio = get_completo(porta_proxy, "/api/json")
    registra("7a. GET /api/json pelo proxy", status == 200 and json.loads(inicio) == {"ok": True, "n": 42}, f"status={status} corpo={inicio[:60]!r}")

    for caminho in ("/", "/nfc/ABC123"):
        status, cab, total, inicio = get_completo(porta_proxy, caminho)
        tipo = cab.get("Content-Type") or cab.get("content-type") or ""
        registra(
            f"7b. SPA {caminho}",
            status == 200 and "text/html" in tipo and b"<div id=\"root\"" in inicio,
            f"status={status} tipo={tipo} bytes={total}",
        )

    c = conexao(porta_proxy)
    c.request("GET", "/f/abc?utm=1", headers={"Connection": "close"})
    r = c.getresponse()
    r.read()
    local = r.getheader("Location")
    c.close()
    registra("7c. redirect /f/<slug>", r.status == 302 and local == "/catalogo/f/abc?utm=1", f"status={r.status} location={local}")

    time.sleep(1)
    s = stats(porta_upstream)
    conexoes = conexoes_do_proxy(pid_proxy, porta_upstream)
    registra(
        "7d. depois dos fluxos legítimos nada fica pendurado",
        s["conexoes"] == 0 and not any(e in ("ESTABLISHED", "CLOSE_WAIT") for e in conexoes),
        f"backend conexoes={s['conexoes']} sockets do proxy={conexoes or '{}'}",
    )


def guardas_estaticas(server_js: Path) -> None:
    fonte = server_js.read_text(encoding="utf-8")
    checagens = {
        "mídia com prazo de inatividade (não zero)": "isMediaRequest(req.url) ? MEDIA_PROXY_TIMEOUT_MS : PROXY_TIMEOUT_MS" in fonte
        and re.search(r"const MEDIA_PROXY_TIMEOUT_MS = [1-9]", fonte) is not None,
        "requestTimeout de 30 min": "server.requestTimeout = 30 * 60 * 1000" in fonte,
        "gancho proxyReq/res close": 'proxy.on("proxyReq"' in fonte and "proxyReq.destroy()" in fonte,
        "gancho res pipe": 'res.on("pipe"' in fonte and "origem.destroy()" in fonte,
        "gancho proxyReq close → res.destroy": 'proxyReq.once("close"' in fonte and "res.destroy()" in fonte,
        "sinal de vida": "[vida]" in fonte and "getActiveResourcesInfo" in fonte,
    }
    for nome, ok in checagens.items():
        registra(f"9. fonte: {nome}", ok, server_js.name)


# ── orquestração ────────────────────────────────────────────────────────────────────────────


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--server", help="caminho de um server.js alternativo (padrão: frontend/server.js do checkout)")
    ap.add_argument("--antes", action="store_true", help="testa o frontend/server.js da main (esperado: FALHA em 1-4)")
    ap.add_argument("--porta-upstream", type=int, default=45101)
    ap.add_argument("--porta-proxy", type=int, default=45102)
    ap.add_argument("--manter-logs", action="store_true")
    args = ap.parse_args()

    if not shutil.which("node"):
        print("node não encontrado no PATH", file=sys.stderr)
        return 2
    for porta in (args.porta_upstream, args.porta_proxy):
        if porta_ouvindo(porta):
            print(f"porta {porta} já está ocupada — use --porta-upstream/--porta-proxy", file=sys.stderr)
            return 2
    for app in ("internal", "public", "portal"):
        if not (FRONTEND / "apps" / app / "dist" / "index.html").exists():
            print(f"faltam os bundles: frontend/apps/{app}/dist/index.html (rode npm run build)", file=sys.stderr)
            return 2

    temporario: Path | None = None
    if args.antes:
        fonte = subprocess.run(["git", "show", "main:frontend/server.js"], cwd=REPO_ROOT, capture_output=True, text=True, encoding="utf-8")
        if fonte.returncode != 0:
            print(fonte.stderr, file=sys.stderr)
            return 2
        # Precisa morar em frontend/ para achar node_modules e os dist/ (caminhos relativos a __dirname).
        temporario = FRONTEND / ".verify_263b_antes.js"
        temporario.write_text(fonte.stdout, encoding="utf-8")
        server_js = temporario
    else:
        server_js = Path(args.server).resolve() if args.server else FRONTEND / "server.js"

    logs = Path(tempfile.mkdtemp(prefix="verify_263b_"))
    print(f"proxy: {server_js}\nlogs: {logs}\n", flush=True)

    ambiente = {k: v for k, v in os.environ.items() if k not in ("PORT", "BACKEND_URL")}
    upstream = proxy = None
    codigo = 1
    try:
        with open(logs / "upstream.log", "w", encoding="utf-8") as up_log, open(logs / "proxy.log", "w", encoding="utf-8") as px_log:
            upstream = subprocess.Popen(
                ["node", str(HARNESS / "upstream.js")],
                env={**ambiente, "UPSTREAM_PORT": str(args.porta_upstream)},
                cwd=HARNESS,
                stdout=up_log,
                stderr=subprocess.STDOUT,
            )
            proxy = subprocess.Popen(
                ["node", str(server_js)],
                env={**ambiente, "PORT": str(args.porta_proxy), "BACKEND_URL": f"http://127.0.0.1:{args.porta_upstream}"},
                cwd=server_js.parent,
                stdout=px_log,
                stderr=subprocess.STDOUT,
            )
            if not (espera_porta(args.porta_upstream) and espera_porta(args.porta_proxy)):
                print("servidores não subiram; veja os logs", file=sys.stderr)
                return 2

            cenario_abandono("1. download de mídia abandonado (GET /uploads/big)", args.porta_proxy, args.porta_upstream, proxy.pid, "/uploads/big", 2 * MB, 5)
            cenario_abandono("2. backend já tinha terminado (0,6 MB, cliente lê 0,1 MB)", args.porta_proxy, args.porta_upstream, proxy.pid, "/uploads/big?mb=0.6", 100 * 1024, 5)
            cenario_abandono("3. abandono em rota /api (prazo de 180 s não pode ser a única saída)", args.porta_proxy, args.porta_upstream, proxy.pid, "/api/x", 2 * MB, 2)
            cenario_some_antes_da_resposta(args.porta_proxy, args.porta_upstream, proxy.pid)
            cenario_backend_morre(args.porta_proxy, args.porta_upstream)
            cenarios_legitimos(args.porta_proxy, args.porta_upstream, proxy.pid)

            time.sleep(0.5)
            px_log.flush()
            texto = (logs / "proxy.log").read_text(encoding="utf-8", errors="replace")
            linhas_502 = [linha for linha in texto.splitlines() if "[proxy]" in linha]
            registra("8. cliente que abortou não vira [proxy] 502 no log", not linhas_502, f"{len(linhas_502)} linha(s) [proxy]: {linhas_502[:3]}")

        # Segundo proxy apontando para uma porta FECHADA: o caminho de 502 continua inteiro.
        # (Não pode ser a porta do primeiro proxy nem a do backend falso, senão vira 200.)
        porta_502 = args.porta_proxy + 1
        porta_fechada = args.porta_proxy + 2
        if porta_ouvindo(porta_fechada):
            print(f"porta {porta_fechada} deveria estar fechada para o cenário 10", file=sys.stderr)
            return 2
        with open(logs / "proxy502.log", "w", encoding="utf-8") as px502_log:
            proxy_502 = subprocess.Popen(
                ["node", str(server_js)],
                env={**ambiente, "PORT": str(porta_502), "BACKEND_URL": f"http://127.0.0.1:{porta_fechada}"},
                cwd=server_js.parent,
                stdout=px502_log,
                stderr=subprocess.STDOUT,
            )
            try:
                if not espera_porta(porta_502):
                    registra("10. proxy com backend fora do ar subiu", False, "não ouviu a porta")
                else:
                    cenario_backend_fora(porta_502)
            finally:
                mata(proxy_502)

        guardas_estaticas(server_js)

        falhas = [r for r in resultados if not r[1]]
        print(f"\n{len(resultados) - len(falhas)}/{len(resultados)} cenários OK" + (f" — FALHAS: {[f[0] for f in falhas]}" if falhas else ""))
        codigo = 1 if falhas else 0
        return codigo
    finally:
        mata(proxy)
        mata(upstream)
        if temporario is not None and temporario.exists():
            temporario.unlink()
        if not args.manter_logs and codigo == 0:
            shutil.rmtree(logs, ignore_errors=True)
        else:
            print(f"logs mantidos em {logs}")


if __name__ == "__main__":
    sys.exit(main())
