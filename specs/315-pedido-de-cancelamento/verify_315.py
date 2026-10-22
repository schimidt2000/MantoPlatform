"""Verificação da feature 315 — o Comercial pede o cancelamento pelo sistema e o Superadmin decide.

A tabela de cenários está na `spec.md` (seção "Verificação", 1–28). Escrito ANTES do núcleo (Princípio
VIII): a primeira rodada, contra o código da `main` (só com as duas colunas no banco), fica em
`verify_315_primeira_falha.txt`.

O HARNESS É O DA 306, IMPORTADO (`verify_306` como módulo), como a 312 faz: o dublê do Google que
falha fechado, o disjuntor de rede, o `_send` falso, os usuários e talentos descartáveis, os eventos
nos meses isolados, o `cenario()` e o `limpar()`. Os dados levam o prefixo da 306 (`__v306_` /
`v306`) e saem no `limpar()` dela. Atenção: o `cenario()` da 306 roda o "27" sempre — aqui o 27 é a
regressão barata (contratos que outras features leem) e a limpeza é o 28, no `finally`.

Blocos (acompanham o `tasks.md`):

  H1  1–9, 16, 17, 26   pedir
  H2  6 (detalhe), 10–15 ver enquanto espera
  H3  13, 18–25          decidir
  R   27                 contratos lidos por outras features
  L   28                 limpeza e nenhuma rede (roda sempre)

Rodar contra o manto_local (PowerShell, na raiz do worktree)::

    . <scratchpad>\\env315.ps1
    & $py specs\\315-pedido-de-cancelamento\\verify_315.py
    & $py specs\\315-pedido-de-cancelamento\\verify_315.py '--so=1,5'   # aspas simples (PowerShell)

Saída: 0 = tudo OK; 1 = algum cenário falhou; 2 = ambiente impróprio.
"""

from __future__ import annotations

import argparse
import json
import sys
import threading
import uuid
from datetime import datetime, timedelta
from pathlib import Path

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI.parent / "306-dinheiro-do-cancelamento"))

import verify_306 as v6  # noqa: E402 — sobe o app, o dublê, o disjuntor e o e-mail falso

from app import db  # noqa: E402
from app.constants import RoleName  # noqa: E402

app = v6.app
estado = v6.estado
_garante = v6._garante
_no_banco = v6._no_banco
_no_banco_escrever = v6._no_banco_escrever
_cliente = v6._cliente
_erro = v6._erro
_codigo = v6._codigo

ROTA = "/api/events/{id}/pedido-cancelamento"
ROTA_VELHA = "/api/events/{id}/solicitar-exclusao"
KIND_PEDIDO = "evento.pedido_cancelamento"
KIND_DECIDIDO = "evento.pedido_decidido"
NOME = f"{v6.PREFIX}Cliente da devolução"
PIX = "pix-devolucao-315@exemplo.test"
MOTIVO = "A cliente desistiu da festa (verify 315)"
TOKEN = uuid.uuid4().hex[:6].upper()


# ── ajudantes ─────────────────────────────────────────────────────────────────────────────────
def _corpo(
    modo: str | None = "parte",
    valor: str | None = "600.00",
    *,
    nome: str | None = NOME,
    pix: str | None = PIX,
    motivo: str = MOTIVO,
    **extra,
) -> dict:
    devolucao: dict = {}
    if modo is not None:
        devolucao["modo"] = modo
    if valor is not None:
        devolucao["valor"] = valor
    if nome is not None:
        devolucao["nome"] = nome
    if pix is not None:
        devolucao["pix"] = pix
    corpo = {"motivo": motivo, "devolucao": devolucao}
    corpo.update(extra)
    return corpo


def _nada(**extra) -> dict:
    return _corpo("nada", None, nome=None, pix=None, **extra)


def _pedir(apelido: str, ev: int, corpo: dict | None = None, *, velha: bool = False):
    rota = ROTA_VELHA if velha else ROTA
    return _cliente(apelido).post(rota.format(id=ev), json=corpo if corpo is not None else _corpo())


def _pedir_ok(apelido: str, ev: int, corpo: dict | None = None, *, velha: bool = False) -> dict:
    r = _pedir(apelido, ev, corpo, velha=velha)
    _garante(r.status_code == 200, f"pedir {ev} como {apelido} → {r.status_code} {r.get_data(as_text=True)[:400]}")
    return r.get_json()


def _recusar(apelido: str, ev: int, motivo: str | None = "A cliente voltou atrás", *, velha: bool = False):
    rota = ROTA_VELHA if velha else ROTA
    return _cliente(apelido).delete(rota.format(id=ev), json={"motivo": motivo} if motivo else {})


def _pedido(ev: int) -> dict:
    linha = _no_banco(
        "SELECT deletion_requested_at, deletion_requested_by_id, deletion_request_reason, "
        "deletion_request_scope, deletion_request_refund FROM calendar_events WHERE id = :i",
        i=ev,
    )[0]
    refund = None
    if linha[4]:
        try:
            refund = json.loads(linha[4])
        except ValueError:
            refund = {"_cru": linha[4]}
    return {"at": linha[0], "by": linha[1], "reason": linha[2], "scope": linha[3], "refund": refund}


def _sem_pedido(ev: int) -> bool:
    p = _pedido(ev)
    return all(p[k] is None for k in ("at", "by", "reason", "scope", "refund"))


def _avisos(kind: str, ev: int) -> list[dict]:
    linhas = _no_banco(
        "SELECT user_id, severity, title, body, link_path, read_at, dedupe_key FROM notifications "
        "WHERE kind = :k AND entity_type = 'calendar_event' AND entity_id = :i ORDER BY id",
        k=kind,
        i=ev,
    )
    chaves = ("user", "severidade", "titulo", "corpo", "link", "lida", "chave")
    return [dict(zip(chaves, x, strict=True)) for x in linhas]


def _decididos(apelido: str) -> list[dict]:
    uid = estado["usuarios"][apelido]["id"]
    linhas = _no_banco(
        "SELECT title, body, link_path, entity_id, created_at FROM notifications "
        "WHERE kind = :k AND user_id = :u ORDER BY id",
        k=KIND_DECIDIDO,
        u=uid,
    )
    return [dict(zip(("titulo", "corpo", "link", "entidade", "quando"), x, strict=True)) for x in linhas]


def _sa_ativos() -> set[int]:
    return {
        r[0]
        for r in _no_banco(
            "SELECT DISTINCT u.id FROM users u JOIN user_roles ur ON ur.user_id = u.id "
            "JOIN roles r ON r.id = ur.role_id WHERE r.name = 'SUPERADMIN' AND u.is_active AND u.has_access"
        )
    }


def _detalhe(apelido: str, ev: int, *, papel: str | None = None) -> dict:
    c = _impersonar(apelido, papel) if papel else _cliente(apelido)
    r = c.get(f"/api/events/{ev}")
    _garante(r.status_code == 200, f"detalhe {ev} como {apelido}/{papel} → {r.status_code}")
    return r.get_json()


def _impersonar(apelido: str, papel: str):
    c = _cliente(apelido)
    r = c.post(v6.ROTAS["impersonate"], json={"role": papel})
    _garante(r.status_code == 200, f"Ver como {papel} → {r.status_code}")
    return c


def _bloco(detalhe: dict) -> dict | None:
    return (detalhe.get("event") or {}).get("deletion_request")


def _texto(obj) -> str:
    return json.dumps(obj, ensure_ascii=False, default=str)


def _evento(rotulo: str, **kw) -> int:
    return v6._evento(f"315 {rotulo}", **kw)


def _resumo_na_agenda(apelido: str, ev: int) -> dict | None:
    """O evento no mês, no dia e na busca (o mesmo serializador): devolve os três resumos."""
    inicio = _no_banco("SELECT start_at, title FROM calendar_events WHERE id = :i", i=ev)[0]
    c = _cliente(apelido)
    mes = c.get(f"/api/agenda?ym={inicio[0]:%Y-%m}").get_json()
    dia = c.get(f"/api/agenda/day/{inicio[0]:%Y-%m-%d}").get_json()
    busca = c.get("/api/agenda/search", query_string={"q": inicio[1]}).get_json()
    achados = {}
    for rotulo, corpo in (("mês", mes), ("dia", dia), ("busca", busca)):
        for item in _itens(corpo):
            if item.get("id") == ev:
                achados[rotulo] = item
    return achados


def _itens(obj) -> list[dict]:
    """Todo dicionário com `id` e `situacao` (o resumo da agenda), em qualquer profundidade."""
    out: list[dict] = []
    if isinstance(obj, dict):
        if "id" in obj and "situacao" in obj:
            out.append(obj)
        for v in obj.values():
            out += _itens(v)
    elif isinstance(obj, list):
        for v in obj:
            out += _itens(v)
    return out


def _faixa(apelido: str, *, papel: str | None = None) -> dict:
    c = _impersonar(apelido, papel) if papel else _cliente(apelido)
    r = c.get("/api/events/sumidos-google")
    _garante(r.status_code == 200, f"faixa como {apelido} → {r.status_code}")
    return r.get_json()


def _portal(talento_id: int):
    email = _no_banco("SELECT email_contact FROM talents WHERE id = :i", i=talento_id)[0][0]
    c = app.test_client()
    r = c.post("/api/portal/auth/login", json={"login": email, "password": v6.SENHA})
    _garante(r.status_code == 200, f"login do portal → {r.status_code}")
    return c


def _no_portal(talento_id: int, ev: int, *, historico: bool = False) -> list[dict]:
    corpo = _portal(talento_id).get("/api/portal/historico" if historico else "/api/portal/agenda").get_json()
    out: list[dict] = []

    def varrer(x):
        if isinstance(x, dict):
            evento = x.get("event") if isinstance(x.get("event"), dict) else None
            if (evento and evento.get("id") == ev) or x.get("event_id") == ev:
                out.append(x)
            for v in x.values():
                varrer(v)
        elif isinstance(x, list):
            for v in x:
                varrer(v)

    varrer(corpo)
    return out


def _cache_pago(ev: int) -> int:
    """Um evento com elenco escalado e o cachê marcado pago (pelo caminho real das vagas)."""
    v6._escalar(ev, estado["t"])
    _no_banco_escrever(
        "UPDATE event_roles SET payment_status = 'pago' WHERE event_id = :i AND talent_id = :t",
        i=ev,
        t=estado["t"],
    )
    return ev


def _ao_mesmo_tempo(*chamadas):
    """Roda as chamadas em threads que largam juntas; devolve as respostas na ordem dada."""
    largada = threading.Barrier(len(chamadas))
    respostas: list = [None] * len(chamadas)

    def corre(i, fn):
        largada.wait()
        respostas[i] = fn()

    threads = [threading.Thread(target=corre, args=(i, fn)) for i, fn in enumerate(chamadas)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=60)
    return respostas


# ── semente ───────────────────────────────────────────────────────────────────────────────────
def semente() -> None:
    v6._usuario("sa2", RoleName.SUPERADMIN)
    v6._usuario("rev", RoleName.REVENDEDOR_EDUCAMANTO)


# ── H1 — pedir ────────────────────────────────────────────────────────────────────────────────
def c1_pedir() -> None:
    ev = _evento("c1")
    v6._comprovante(ev, 1000)
    sa = _sa_ativos()
    resposta = _pedir_ok("com", ev)
    _garante("event" in resposta, f"1: a resposta não é o detalhe: {list(resposta)[:8]}")
    p = _pedido(ev)
    _garante(p["at"] is not None and p["by"] == estado["usuarios"]["com"]["id"], f"1: pedido {p}")
    _garante(p["reason"] == MOTIVO and p["scope"] == "todos", f"1: motivo/alcance {p}")
    dev = (p["refund"] or {}).get("devolucao") or {}
    _garante(
        dev.get("modo") == "parte" and dev.get("valor") == "600.00" and dev.get("nome") == NOME and dev.get("pix") == PIX,
        f"1: devolução {p['refund']}",
    )
    historico = " ".join(m for m, _ in v6._historico(ev))
    _garante("Pediu o cancelamento" in historico, f"1: histórico {historico[:200]}")
    _garante(PIX not in historico and NOME not in historico, "1: nome/PIX no histórico")
    auditoria = _no_banco(
        "SELECT detail FROM audit_logs WHERE action = 'cancel_requested' AND entity_type = 'agenda' AND entity_id = :i",
        i=ev,
    )
    _garante(len(auditoria) == 1, f"1: auditoria {auditoria}")
    _garante(PIX not in (auditoria[0][0] or "") and NOME not in (auditoria[0][0] or ""), "1: nome/PIX na auditoria")
    avisos = _avisos(KIND_PEDIDO, ev)
    _garante({a["user"] for a in avisos} == sa, f"1: aviso a {sorted(a['user'] for a in avisos)} ≠ SA {sorted(sa)}")
    _garante(len(avisos) == len(sa), f"1: avisos em dobro {len(avisos)}")
    texto = _texto(avisos)
    _garante(MOTIVO in texto and estado["usuarios"]["com"]["email"].split("@")[0] in texto, f"1: aviso {texto[:300]}")
    _garante(PIX not in texto and NOME not in texto, "1: nome/PIX no sino")
    _garante(all(a["link"] == f"/events/{ev}" for a in avisos), "1: link do aviso")


def c2_urgencia() -> None:
    perto = _evento("c2 perto", inicio=datetime.now().replace(microsecond=0) + timedelta(days=3))
    longe = _evento("c2 longe")
    passado = _evento("c2 passado", inicio=datetime.now().replace(microsecond=0) - timedelta(days=10))
    for ev, esperado in ((perto, "urgent"), (longe, "info"), (passado, "urgent")):
        _pedir_ok("com", ev, _nada())
        sev = {a["severidade"] for a in _avisos(KIND_PEDIDO, ev)}
        _garante(sev == {esperado}, f"2: evento {ev} severidade {sev} ≠ {esperado}")


def c3_campos() -> None:
    ev = _evento("c3")
    for corpo, campo in (
        ({**_corpo(), "motivo": "  "}, "motivo"),
        (_corpo(None, None, nome=None, pix=None), "devolucao_modo"),
        (_corpo("parte", None), "devolucao_valor"),
        (_corpo("tudo", "2000.00", nome=None), "devolucao_nome"),
        (_corpo("tudo", "2000.00", pix=None), "devolucao_pix"),
        (_corpo(venda_nova="1500.00"), "venda_nova"),
    ):
        r = _pedir("com", ev, corpo)
        _garante(r.status_code == 400 and campo in (_erro(r).get("fields") or {}), f"3: {campo} → {r.status_code} {_erro(r)}")
        _garante(_sem_pedido(ev), f"3: {campo} gravou")
    # Nada com nome e PIX: aceitos, mas não gravados.
    _pedir_ok("com", ev, _corpo("nada", None))
    dev = (_pedido(ev)["refund"] or {}).get("devolucao") or {}
    _garante(dev.get("modo") == "nada" and "nome" not in dev and "pix" not in dev, f"3: Nada gravou {dev}")
    # Venda virtual: só o motivo.
    virtual = _evento("c3 virtual", tipo="VIRTUAL")
    _pedir_ok("com", virtual, {"motivo": MOTIVO})
    _garante(_pedido(virtual)["refund"] is None, f"3: virtual gravou devolução {_pedido(virtual)}")


def c4_alcance() -> None:
    g = v6._grupo("315 c4", pagos=(), comissao=None, dias=2)
    p, s1, s2 = g["principal"], *g["dias"]
    r = _pedir("com", p, _nada())
    _garante(r.status_code == 400 and "alcance" in (_erro(r).get("fields") or {}), f"4: sem alcance {r.status_code} {_erro(r)}")
    r = _pedir("com", p, _nada(alcance="so_este_dia"))
    _garante(r.status_code == 400 and "venda_nova" in (_erro(r).get("fields") or {}), f"4: sem venda_nova {_erro(r)}")
    r = _pedir("com", p, _corpo("tudo", "100.00", alcance="so_este_dia", venda_nova="2000.00"))
    _garante(r.status_code == 400 and "devolucao_modo" in (_erro(r).get("fields") or {}), f"4: tudo no corte {_erro(r)}")
    _garante(_sem_pedido(p), "4: recusa gravou")
    _pedir_ok("com", p, _nada(alcance="so_este_dia", venda_nova="2000.00"))
    _garante(_pedido(p)["scope"] == "so_este_dia", f"4: alcance {_pedido(p)}")
    _garante((_pedido(p)["refund"] or {}).get("venda_nova") == "2000.00", f"4: venda_nova {_pedido(p)}")
    # Num outro dia da venda: sem escolha de alcance (mandar é 400); vale só para ele.
    r = _pedir("vend2", s1, _nada(alcance="todos", venda_nova="2500.00"))
    _garante(r.status_code == 400 and "alcance" in (_erro(r).get("fields") or {}), f"4: alcance no satélite {_erro(r)}")
    _pedir_ok("vend2", s1, _nada(venda_nova="2500.00"))
    _garante(_pedido(s1)["scope"] == "so_este_dia", f"4: satélite {_pedido(s1)}")
    # "Todos os dias" num outro grupo.
    g2 = v6._grupo("315 c4b", pagos=(), comissao=None, dias=1)
    _pedir_ok("com", g2["principal"], _nada(alcance="todos"))
    _garante(_pedido(g2["principal"])["scope"] == "todos", f"4: todos {_pedido(g2['principal'])}")
    _garante(_sem_pedido(s2), "4: o pedido de um dia desceu a outro")


def c5_pendente() -> None:
    ev = _evento("c5")
    _pedir_ok("com", ev, _nada())
    avisos = len(_avisos(KIND_PEDIDO, ev))
    r = _pedir("vend2", ev, _nada())
    _garante(r.status_code == 409 and _codigo(r) == "pedido_pendente", f"5: segundo → {r.status_code} {_erro(r)}")
    _garante(estado["usuarios"]["com"]["email"].split("@")[0] in (_erro(r).get("message") or ""), f"5: sem o nome {_erro(r)}")
    _garante(_pedido(ev)["by"] == estado["usuarios"]["com"]["id"], "5: sobrescreveu o pedido")
    _garante(len(_avisos(KIND_PEDIDO, ev)) == avisos, "5: avisou de novo")
    # Dois pedidos ao mesmo tempo: um vence.
    ev2 = _evento("c5 corrida")
    r1, r2 = _ao_mesmo_tempo(lambda: _pedir("com", ev2, _nada()), lambda: _pedir("vend2", ev2, _nada()))
    status = sorted([r1.status_code, r2.status_code])
    _garante(status == [200, 409], f"5: corrida {status} {r1.get_data(as_text=True)[:120]} {r2.get_data(as_text=True)[:120]}")
    _garante(len(_avisos(KIND_PEDIDO, ev2)) == len(_sa_ativos()), f"5: corrida avisou {_avisos(KIND_PEDIDO, ev2)}")


def c6_bloqueios() -> None:
    ensaio = _evento("c6 ensaio", tipo="ENSAIO", venda=None, taxa=None, vendedor=None)
    r = _pedir("com", ensaio, _nada())
    _garante(r.status_code == 409 and _codigo(r) == "ensaio", f"6: ensaio → {r.status_code} {_erro(r)}")
    pago = _cache_pago(v6._evento_com_elenco("315 c6 pago", ["fada"]))
    r = _pedir("com", pago, _nada())
    _garante(r.status_code == 409 and _codigo(r) == "cache_pago", f"6: cachê pago → {r.status_code} {_erro(r)}")
    for ev in (ensaio, pago):
        _garante(_sem_pedido(ev) and not _avisos(KIND_PEDIDO, ev), f"6: {ev} gravou ou avisou")
    # A ordem da 306: o bloqueio vem antes da forma (corpo incompleto ainda leva o 409).
    r = _pedir("com", ensaio, {"motivo": ""})
    _garante(r.status_code == 409 and _codigo(r) == "ensaio", f"6: ordem → {r.status_code} {_erro(r)}")
    # O detalhe avisa o menu (pela frase do servidor).
    bloqueio = (_detalhe("com", pago).get("event") or {}).get("pedido_bloqueado") or {}
    _garante(bloqueio.get("codigo") == "cache_pago" and bloqueio.get("frase"), f"6: detalhe sem bloqueio {bloqueio}")
    # Cachê pago só noutro dia: "só este dia" vale; "todos" leva o 409.
    # O dia pago precisa de vaga criada pelo sistema: um evento com elenco entra no grupo como 2º dia.
    g = v6._grupo("315 c6 grupo", pagos=(), comissao=None, dias=1)
    dia_pago = v6._evento_com_elenco("315 c6 dia pago", ["bruxa"])
    v6._agrupar(g["principal"], dia_pago)
    _cache_pago(dia_pago)
    r = _pedir("com", g["principal"], _nada(alcance="todos"))
    _garante(r.status_code == 409 and _codigo(r) == "cache_pago", f"6: todos com dia pago → {r.status_code} {_erro(r)}")
    _garante(_sem_pedido(g["principal"]), "6: 'todos' recusado gravou")
    _pedir_ok("com", g["principal"], _nada(alcance="so_este_dia", venda_nova="2000.00"))


def c7_marcado() -> None:
    ev = _evento("c7")
    v6._marcar_sumido(ev)
    marca = _no_banco("SELECT google_missing_since FROM calendar_events WHERE id = :i", i=ev)[0][0]
    _pedir_ok("com", ev, _nada())
    depois = _no_banco("SELECT google_missing_since FROM calendar_events WHERE id = :i", i=ev)[0][0]
    _garante(marca == depois, "7: a marca mudou")
    r = _cliente("sa").post(f"/api/events/{ev}/devolver-ao-google", json={})
    _garante(r.status_code == 200, f"7: devolver ao Google → {r.status_code} {r.get_data(as_text=True)[:200]}")
    _garante(not _sem_pedido(ev), "7: devolver ao Google fechou o pedido")


def c8_sem_google_nem_email() -> None:
    ev = _evento("c8")
    marco, emails = v6.google.marco(), len(v6._emails)
    _pedir_ok("com", ev, _nada())
    r = _recusar("sa", ev)
    _garante(r.status_code == 200, f"8: recusar → {r.status_code} {r.get_data(as_text=True)[:200]}")
    _garante(v6.google.chamadas[marco:] == [], f"8: Google {v6.google.chamadas[marco:]}")
    _garante(len(v6._emails) == emails, f"8: e-mails {v6._emails[emails:]}")


def c9_cancelado() -> None:
    ev = _evento("c9", venda=None, taxa=None, vendedor=None)
    v6._cancelar_ok(ev, {"motivo": "Cancelado antes (verify 315)", "devolucao": {"modo": "nada"}})
    r = _pedir("com", ev, _nada())
    _garante(r.status_code == 409 and _codigo(r) == "cancelado", f"9: cancelado → {r.status_code} {_erro(r)}")
    _garante(_sem_pedido(ev), "9: gravou no cancelado")


def c16_nao_tranca() -> None:
    ev = _evento("c16")
    _pedir_ok("com", ev, _nada())
    # O PATCH da aba Comercial substitui o bloco inteiro: vendedor e taxa vão como estão.
    vendedor, taxa = _no_banco("SELECT seller_id, commission_rate FROM calendar_events WHERE id = :i", i=ev)[0]
    corpo = {"sale_value": 2100, "seller_id": vendedor, "commission_rate": float(taxa) if taxa is not None else None}
    r = _cliente("com").patch(f"/api/events/{ev}/comercial", json=corpo)
    _garante(r.status_code == 200, f"16: editar a venda → {r.status_code} {r.get_data(as_text=True)[:200]}")
    _garante(_resumo_na_agenda("cast", ev).get("mês"), "16: o evento com pedido saiu do mês")


def c17_contrato_velho() -> None:
    ev = _evento("c17")
    _pedir_ok("com", ev, {"motivo": MOTIVO}, velha=True)
    p = _pedido(ev)
    _garante(p["at"] and p["refund"] is None and p["scope"] == "todos", f"17: pedido pelo caminho velho {p}")
    g = v6._grupo("315 c17", pagos=(), comissao=None, dias=1)
    _pedir_ok("com", g["principal"], {"motivo": MOTIVO}, velha=True)
    _garante(_pedido(g["principal"])["scope"] is None, f"17: principal pelo caminho velho {_pedido(g['principal'])}")
    r = _recusar("sa", ev, velha=True)
    _garante(r.status_code == 200 and _sem_pedido(ev), f"17: recusar pelo caminho velho → {r.status_code}")


def c26_q5d() -> None:
    ev = _evento("c26")
    _pedir_ok("com", ev, _nada())
    for velha in (False, True):
        r = _recusar("com", ev, velha=velha)
        _garante(r.status_code == 403, f"26: o autor fechou o pedido ({'velha' if velha else 'nova'}) → {r.status_code}")
    _garante(not _sem_pedido(ev), "26: o pedido sumiu")


# ── H2 — ver enquanto espera ──────────────────────────────────────────────────────────────────
def _pedido_completo(rotulo: str, apelido: str = "com") -> int:
    ev = _evento(rotulo)
    _pedir_ok(apelido, ev)
    return ev


def _confere_corte(ev: int) -> None:
    autor = _bloco(_detalhe("com", ev)) or {}
    _garante(autor.get("reason") == MOTIVO and autor.get("requested_by"), f"10: autor sem motivo {autor}")
    _garante((autor.get("devolucao") or {}).get("pix") == PIX, f"10: autor sem PIX {autor}")
    colega = _bloco(_detalhe("vend2", ev)) or {}
    _garante(colega.get("reason") == MOTIVO, f"10: colega sem motivo {colega}")
    dev = colega.get("devolucao") or {}
    _garante(dev.get("modo") == "parte" and "pix" not in dev and "nome" not in dev, f"10: colega leu nome/PIX {dev}")
    for apelido in ("fin", "sa"):
        b = _bloco(_detalhe(apelido, ev)) or {}
        _garante((b.get("devolucao") or {}).get("pix") == PIX and b.get("reason"), f"10: {apelido} {b}")
    for apelido, papel in (("cast", None), ("fig", None), ("ens", None), ("a3d", None), ("rev", None), ("sa", "CASTING"), ("sa", "COMERCIAL")):
        b = _bloco(_detalhe(apelido, ev, papel=papel))
        _garante(b is not None and b.get("requested_at"), f"10: {apelido}/{papel} sem o bloco {b}")
        if papel == "COMERCIAL":
            # O Superadmin autor? não; aqui o SA em "Ver como Comercial" é colega: motivo sim, PIX não.
            _garante(b.get("reason") == MOTIVO and "pix" not in (b.get("devolucao") or {}), f"10: SA ver como Comercial {b}")
            continue
        vazou = {k for k in ("reason", "requested_by", "requested_by_id", "devolucao", "venda_nova") if b.get(k)}
        _garante(not vazou, f"10: {apelido}/{papel} leu {vazou}")


def c10_corte() -> None:
    ev = _pedido_completo("c10")
    _confere_corte(ev)
    from app.calendar import solicitacao_ops

    real = solicitacao_ops.serializar_para

    def sem_corte(event, *, flags, usuario, impersonando=False):
        return real(event, flags=None, usuario=usuario, impersonando=impersonando)

    solicitacao_ops.serializar_para = sem_corte
    try:
        v6._deve_quebrar(lambda: _confere_corte(ev), "o detalhe sem o corte da Q6")
    finally:
        solicitacao_ops.serializar_para = real


def c11_fila() -> None:
    ev = _pedido_completo("c11")

    def item(c) -> dict:
        r = c.get(v6.ROTAS["cancelamentos"])
        _garante(r.status_code == 200, f"11: fila → {r.status_code}")
        achados = [x for x in r.get_json().get("pendentes") or [] if x.get("id") == ev]
        _garante(len(achados) == 1, f"11: o pedido não está na fila: {achados}")
        return achados[0]

    for apelido in ("sa", "fin"):
        x = item(_cliente(apelido))
        _garante(x.get("reason") == MOTIVO and (x.get("devolucao") or {}).get("pix") == PIX, f"11: {apelido} {x}")
        _garante(x.get("alcance") == "todos", f"11: alcance {x}")
    x = item(_impersonar("sa", "CASTING"))
    vazou = {k for k in ("reason", "requested_by", "devolucao") if x.get(k)}
    _garante(not vazou, f"11: Ver como Casting leu {vazou}")
    r = _cliente("com").get(v6.ROTAS["cancelamentos"])
    _garante(r.status_code == 403, f"11: Comercial na fila → {r.status_code}")


def c12_faixa() -> None:
    ev = _pedido_completo("c12")
    for apelido in ("com", "sa"):
        f = _faixa(apelido)
        pedidos = f.get("pedidos") or {}
        itens = [x for x in pedidos.get("items") or [] if x.get("id") == ev]
        _garante(pedidos.get("total", 0) >= 1 and len(itens) == 1, f"12: {apelido} {pedidos}")
        _garante(set(itens[0]) <= {"id", "title", "start_at"}, f"12: a faixa leva {set(itens[0])}")
        marcados = _no_banco(
            "SELECT count(*) FROM calendar_events WHERE google_missing_since IS NOT NULL AND cancelled_at IS NULL"
        )[0][0]
        _garante(f.get("total") == marcados, f"12: `total` deixou de ser só do sumiço {f.get('total')} ≠ {marcados}")
    for apelido, papel in (("cast", None), ("fin", None), ("rev", None), ("sa", "CASTING")):
        f = _faixa(apelido, papel=papel)
        _garante(f.get("pode_ver") is False and not f.get("pedidos"), f"12: {apelido}/{papel} vê a faixa {f}")


def c13_selo() -> None:
    ev = _pedido_completo("c13")
    for apelido in ("cast", "com"):
        achados = _resumo_na_agenda(apelido, ev)
        _garante(set(achados) == {"mês", "dia", "busca"}, f"13: {apelido} achou {set(achados)}")
        for onde, item in achados.items():
            _garante(item.get("situacao") == "exclusao_solicitada" and item.get("situacao_desde"), f"13: {onde} {item}")
    r = _recusar("sa", ev)
    _garante(r.status_code == 200, f"13: recusar → {r.status_code}")
    for onde, item in _resumo_na_agenda("cast", ev).items():
        _garante(item.get("situacao") is None, f"13: o selo ficou no {onde} {item}")


def c14_portal() -> None:
    futuro = v6._evento_com_elenco("315 c14 futuro", ["pirata"])
    v6._escalar(futuro, estado["t"])
    _pedir_ok("com", futuro, _nada())
    linhas = _no_portal(estado["t"], futuro)
    _garante(linhas and all(x.get("em_confirmacao") is True for x in linhas), f"14: portal futuro {linhas}")
    _garante(MOTIVO not in _texto(linhas), "14: o motivo foi ao portal")
    passado = v6._evento_com_elenco(
        "315 c14 passado", ["sereia"], inicio=datetime.now().replace(microsecond=0) - timedelta(days=5)
    )
    v6._escalar(passado, estado["t2"])
    _pedir_ok("com", passado, _nada())
    linhas = _no_portal(estado["t2"], passado, historico=True)
    _garante(linhas and all(x.get("em_confirmacao") is True for x in linhas), f"14: histórico {linhas}")


def c15_satelite() -> None:
    g = v6._grupo("315 c15", pagos=(), comissao=None, dias=2)
    p, s1, s2 = g["principal"], *g["dias"]
    _pedir_ok("com", p, _nada(alcance="todos"))
    for dia in (s1, s2):
        achados = _resumo_na_agenda("cast", dia)
        _garante(achados and all(x.get("situacao") == "exclusao_solicitada" for x in achados.values()), f"15: dia {dia} {achados}")
        corpo = _detalhe("cast", dia).get("event") or {}
        _garante(corpo.get("situacao") == "exclusao_solicitada" and corpo.get("pedido_da_venda"), f"15: detalhe {dia}")
    # Só este dia no 1º: os outros dias não herdam.
    g2 = v6._grupo("315 c15b", pagos=(), comissao=None, dias=1)
    _pedir_ok("com", g2["principal"], _nada(alcance="so_este_dia", venda_nova="2000.00"))
    achados = _resumo_na_agenda("cast", g2["dias"][0])
    _garante(all(x.get("situacao") is None for x in achados.values()), f"15: o dia herdou o 'só este dia' {achados}")


# ── H3 — decidir ──────────────────────────────────────────────────────────────────────────────
def c18_recusar() -> None:
    ev = _pedido_completo("c18")
    titulo = v6._no_banco("SELECT title FROM calendar_events WHERE id = :i", i=ev)[0][0]
    antes = len(_decididos("com"))
    r = _recusar("sa", ev, "A cliente desistiu de cancelar")
    _garante(r.status_code == 200 and "event" in (r.get_json() or {}), f"18: recusar → {r.status_code}")
    _garante(_sem_pedido(ev), f"18: o pedido ficou {_pedido(ev)}")
    novos = _decididos("com")[antes:]
    _garante(len(novos) == 1, f"18: respostas {novos}")
    _garante(titulo in (novos[0]["titulo"] or "") and "recusado" in (novos[0]["titulo"] or "").lower(), f"18: título {novos[0]}")
    _garante("A cliente desistiu de cancelar" in _texto(novos[0]), f"18: sem o motivo {novos[0]}")
    _garante(all(a["lida"] for a in _avisos(KIND_PEDIDO, ev)), "18: aviso do pedido não lido")
    _garante(all(x.get("id") != ev for x in (_faixa("com").get("pedidos") or {}).get("items") or []), "18: ficou na faixa")
    _garante("Recusou o pedido de cancelamento" in " ".join(m for m, _ in v6._historico(ev)), "18: histórico")


def c19_quem_recusa() -> None:
    ev = _pedido_completo("c19")
    for apelido in ("com", "vend2", "cast", "fin"):
        r = _recusar(apelido, ev)
        _garante(r.status_code == 403, f"19: {apelido} recusou → {r.status_code}")
    _garante(not _sem_pedido(ev), "19: o pedido sumiu")
    r = _impersonar("sa", "COMERCIAL").delete(ROTA.format(id=ev), json={})
    _garante(r.status_code == 200 and _sem_pedido(ev), f"19: SA real em Ver como → {r.status_code}")


def c20_cancelar() -> None:
    ev = _evento("c20", venda=None, taxa=None, vendedor=None)
    _pedir_ok("com", ev, _nada())
    antes = len(_decididos("com"))
    v6._cancelar_ok(ev, {"motivo": "Cancelado pelo pedido (verify 315)", "devolucao": {"modo": "nada"}})
    _garante(_sem_pedido(ev), f"20: o pedido ficou {_pedido(ev)}")
    novos = _decididos("com")[antes:]
    _garante(len(novos) == 1 and "Evento cancelado" in (novos[0]["titulo"] or ""), f"20: resposta {novos}")
    _garante(novos[0]["link"] == f"/events/{ev}", f"20: link {novos[0]}")
    _garante(all(a["lida"] for a in _avisos(KIND_PEDIDO, ev)), "20: aviso do pedido não lido")


def c21_venda_de_varios_dias() -> None:
    # Todos os dias: o pedido do 1º (todos) e o do 3º dia fecham, uma resposta a cada autor.
    g = v6._grupo("315 c21a", pagos=(), comissao=None, dias=2)
    p, s1, s2 = g["principal"], *g["dias"]
    _pedir_ok("com", p, _nada(alcance="todos"))
    _pedir_ok("vend2", s2, _nada(venda_nova="2000.00"))
    a_com, a_vend2 = len(_decididos("com")), len(_decididos("vend2"))
    v6._cancelar_ok(p, {"motivo": "Todos (verify 315)", "devolucao": {"modo": "nada"}, "alcance": "todos"})
    _garante(_sem_pedido(p) and _sem_pedido(s2), "21a: sobrou pedido")
    _garante(len(_decididos("com")) - a_com == 1 and len(_decididos("vend2")) - a_vend2 == 1, "21a: respostas")
    # Só o 2º dia: os pedidos do 1º e do 3º continuam.
    g = v6._grupo("315 c21b", pagos=(), comissao=None, dias=2)
    p, s1, s2 = g["principal"], *g["dias"]
    _pedir_ok("com", p, _nada(alcance="todos"))
    _pedir_ok("vend2", s2, _nada(venda_nova="2000.00"))
    a_com, a_vend2 = len(_decididos("com")), len(_decididos("vend2"))
    v6._cancelar_ok(s1, {"motivo": "Só o 2º (verify 315)", "devolucao": {"modo": "nada"}, "venda_nova": 2500})
    _garante(not _sem_pedido(p) and not _sem_pedido(s2), "21b: um pedido fechou sem cair")
    _garante(len(_decididos("com")) == a_com and len(_decididos("vend2")) == a_vend2, "21b: respondeu sem cair")
    # Só o 1º (passagem): o pedido dele fecha e diz para onde foi a venda.
    g = v6._grupo("315 c21c", pagos=(), comissao=None, dias=2)
    p, s1, _s2 = g["principal"], *g["dias"]
    _pedir_ok("com", p, _nada(alcance="todos"))
    a_com = len(_decididos("com"))
    v6._cancelar_ok(
        p,
        {"motivo": "Só o 1º (verify 315)", "devolucao": {"modo": "nada"}, "alcance": "so_este_dia",
         "novo_principal_id": s1, "venda_nova": 2500},
    )
    novos = _decididos("com")[a_com:]
    _garante(len(novos) == 1 and "venda passou para o dia" in _texto(novos), f"21c: resposta {novos}")


def c22_excluir() -> None:
    ev = _evento("c22", venda=None, taxa=None, vendedor=None)
    titulo = _no_banco("SELECT title FROM calendar_events WHERE id = :i", i=ev)[0][0]
    _pedir_ok("com", ev, _nada())
    antes = len(_decididos("com"))
    r = _cliente("sa").delete(v6.ROTAS["excluir"].format(id=ev))
    _garante(r.status_code == 200, f"22: excluir → {r.status_code} {r.get_data(as_text=True)[:200]}")
    novos = _decididos("com")[antes:]
    _garante(len(novos) == 1 and "excluído" in (novos[0]["titulo"] or "").lower() and titulo in novos[0]["titulo"], f"22: {novos}")
    _garante(novos[0]["link"] is None and novos[0]["entidade"] is None, f"22: link/entidade {novos[0]}")
    _garante(not _avisos(KIND_PEDIDO, ev), "22: sobrou aviso do pedido")


def c23_decisoes_ao_mesmo_tempo() -> None:
    ev = _evento("c23", venda=None, taxa=None, vendedor=None)
    _pedir_ok("com", ev, _nada())
    antes = len(_decididos("com"))
    r1, r2 = _ao_mesmo_tempo(lambda: _recusar("sa", ev), lambda: _recusar("sa2", ev))
    status = sorted([r1.status_code, r2.status_code])
    _garante(status == [200, 409], f"23: recusa × recusa {status}")
    perdeu = r1 if r1.status_code == 409 else r2
    _garante(_codigo(perdeu) == "sem_pedido", f"23: código {_erro(perdeu)}")
    _garante(len(_decididos("com")) - antes == 1, "23: duas respostas")
    # Recusa × cancelamento: uma resposta só.
    ev2 = _evento("c23b", venda=None, taxa=None, vendedor=None)
    _pedir_ok("com", ev2, _nada())
    antes = len(_decididos("com"))
    v6._instalar_espiao_ao_cancelar()
    _ao_mesmo_tempo(
        lambda: _recusar("sa2", ev2),
        lambda: _cliente("sa").post(v6.ROTAS["cancelar"].format(id=ev2), json={"motivo": "x", "devolucao": {"modo": "nada"}}),
    )
    v6._esperar_threads()
    _garante(len(_decididos("com")) - antes == 1, f"23: recusa × cancelar deu {len(_decididos('com')) - antes} respostas")


def c24_pessoas() -> None:
    # Autor sem acesso: a decisão segue, a resposta não sai.
    ev = _evento("c24")
    _pedir_ok("vend2", ev, _nada())
    _no_banco_escrever("UPDATE users SET has_access = false WHERE id = :u", u=estado["usuarios"]["vend2"]["id"])
    try:
        antes = len(_decididos("vend2"))
        r = _recusar("sa", ev)
        _garante(r.status_code == 200, f"24: recusar → {r.status_code}")
        _garante(len(_decididos("vend2")) == antes, "24: respondeu a quem perdeu o acesso")
    finally:
        _no_banco_escrever("UPDATE users SET has_access = true WHERE id = :u", u=estado["usuarios"]["vend2"]["id"])
    # O Superadmin pede (pela API) e decide: recebe o aviso como os outros; não recebe a resposta.
    ev2 = _evento("c24b")
    _pedir_ok("sa", ev2, _nada())
    _garante(estado["usuarios"]["sa"]["id"] in {a["user"] for a in _avisos(KIND_PEDIDO, ev2)}, "24: SA autor sem aviso")
    antes = len(_decididos("sa"))
    _garante(_recusar("sa", ev2).status_code == 200, "24: SA recusa o próprio")
    _garante(len(_decididos("sa")) == antes, "24: SA recebeu a própria resposta")


def c25_pedido_legado() -> None:
    ev = _evento("c25")
    _no_banco_escrever(
        "UPDATE calendar_events SET deletion_requested_at = :t, deletion_requested_by_id = :u, "
        "deletion_request_reason = :m WHERE id = :i",
        t=datetime.now().replace(microsecond=0),
        u=estado["usuarios"]["com"]["id"],
        m=MOTIVO,
        i=ev,
    )
    fila = _cliente("sa").get(v6.ROTAS["cancelamentos"]).get_json().get("pendentes") or []
    item = [x for x in fila if x.get("id") == ev]
    _garante(item and item[0].get("reason") == MOTIVO and not item[0].get("devolucao"), f"25: fila {item}")
    _garante(_bloco(_detalhe("sa", ev)), "25: detalhe sem o pedido")
    _garante(any(x.get("id") == ev for x in (_faixa("sa").get("pedidos") or {}).get("items") or []), "25: fora da faixa")
    _garante(all(x.get("situacao") == "exclusao_solicitada" for x in _resumo_na_agenda("cast", ev).values()), "25: selo")
    _garante(not _avisos(KIND_PEDIDO, ev), "25: aviso retroativo")
    antes = len(_decididos("com"))
    _garante(_recusar("sa", ev).status_code == 200 and _sem_pedido(ev), "25: recusar o legado")
    _garante(len(_decididos("com")) - antes == 1, "25: o autor do legado não recebeu a resposta")


# ── R — contratos que outras features leem ────────────────────────────────────────────────────
def c27_contratos() -> None:
    from app.calendar import sumico_ops

    with app.app_context():
        f = sumico_ops.faixa_sumidos()
    _garante(set(f) >= {"total", "items"} and "pedidos" not in f, f"27: faixa_sumidos mudou {set(f)}")


CENARIOS = [
    ("H1", "1", "pedir: grava as cinco colunas, histórico, auditoria e o aviso a cada Superadmin", c1_pedir),
    ("H1", "2", "urgência: ≤ 7 dias e passado urgentes; longe informativo", c2_urgencia),
    ("H1", "3", "a forma da devolução (400 por campo; Nada; venda virtual)", c3_campos),
    ("H1", "4", "venda de vários dias: o alcance, o corte e o outro dia", c4_alcance),
    ("H1", "5", "DEVE FALHAR: segundo pedido e pedidos ao mesmo tempo", c5_pendente),
    ("H2", "6", "DEVE FALHAR: ensaio e cachê pago (porta, ordem e detalhe)", c6_bloqueios),
    ("H1", "7", "evento marcado: aceita e não decide no devolver ao Google", c7_marcado),
    ("H1", "8", "pedir e recusar sem Google nem e-mail", c8_sem_google_nem_email),
    ("H1", "9", "DEVE FALHAR: pedido em evento cancelado", c9_cancelado),
    ("H2", "10", "DEVE FALHAR (leitura): o corte da Q6 e da premissa 5 no detalhe, com mutação", c10_corte),
    ("H2", "11", "DEVE FALHAR (leitura): a fila com o corte; Comercial 403", c11_fila),
    ("H2", "12", "a faixa: pedidos a Comercial e Superadmin; `total` só do sumiço", c12_faixa),
    ("H3", "13", "o selo no mês, no dia e na busca; some na decisão", c13_selo),
    ("H2", "14", "o portal: Evento em confirmação no futuro e no histórico", c14_portal),
    ("H2", "15", "o satélite herda o pedido de todos os dias", c15_satelite),
    ("H1", "16", "o pedido não tranca", c16_nao_tranca),
    ("H1", "17", "o caminho velho (corpo só com o motivo)", c17_contrato_velho),
    ("H3", "18", "recusar: fecha, responde, marca lido, limpa", c18_recusar),
    ("H3", "19", "DEVE FALHAR: quem não é Superadmin real não recusa", c19_quem_recusa),
    ("H3", "20", "cancelar fecha o pedido e responde com link", c20_cancelar),
    ("H3", "21", "venda de vários dias: todos, um dia, a passagem", c21_venda_de_varios_dias),
    ("H3", "22", "excluir o vazio responde sem link", c22_excluir),
    ("H3", "23", "DEVE FALHAR: decisões ao mesmo tempo — um vencedor, uma resposta", c23_decisoes_ao_mesmo_tempo),
    ("H3", "24", "autor sem acesso; o Superadmin que pede e decide", c24_pessoas),
    ("H3", "25", "o pedido de antes do deploy", c25_pedido_legado),
    ("H1", "26", "DEVE FALHAR: o autor não fecha o próprio pedido (Q5 = D)", c26_q5d),
    ("R", "27", "contratos que outras features leem (faixa_sumidos)", c27_contratos),
]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--so", default=None)
    args = parser.parse_args()
    if args.so:
        v6.OPCOES["so"] = {s.strip() for s in args.so.split(",") if s.strip()}
    v6.guarda_de_ambiente()
    print(f"\n── verify 315 (token {TOKEN}) ──")
    try:
        v6.preparar()
        try:
            semente()
        except Exception as exc:  # noqa: BLE001 — sem semente nenhum cenário prova nada
            v6.resultados.append(("S", "0 · semente", "FALHA", str(exc)))
            print(f"  FALHA      0 · semente: {str(exc)[:600]}")
            raise
        for bloco, num, nome, fn in CENARIOS:
            v6.cenario(bloco, num, nome, fn)
    except Exception:  # noqa: BLE001 — a limpeza roda e o placar sai
        pass
    finally:
        try:
            v6.limpar()
            sobras = v6._sobras_do_verify()
            _garante(not sobras, f"a limpeza deixou: {sobras}")
            _garante(not v6.rede_bloqueada, f"conexões externas tentadas: {v6.rede_bloqueada}")
            v6.resultados.append(("L", "28 · limpeza e nenhuma rede", "OK", ""))
            print("  OK         28 · limpeza e nenhuma rede")
        except Exception as exc:  # noqa: BLE001
            v6.resultados.append(("L", "28 · limpeza e nenhuma rede", "FALHA", str(exc)))
            print(f"  FALHA      28 · limpeza: {exc}")
    oks = sum(1 for r in v6.resultados if r[2] == "OK")
    print(f"\n{oks}/{len(v6.resultados)} cenários OK")
    for bloco in ("S", "H1", "H2", "H3", "R", "L"):
        linhas = [r for r in v6.resultados if r[0] == bloco]
        if linhas:
            print(f"  {bloco}: {sum(1 for r in linhas if r[2] == 'OK')}/{len(linhas)}")
    _ = db
    return 0 if oks == len(v6.resultados) else 1


if __name__ == "__main__":
    sys.exit(main())
