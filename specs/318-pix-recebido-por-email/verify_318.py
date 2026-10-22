"""Verificação da feature 318 — o PIX que cai no Inter se liga sozinho à venda.

A tabela de cenários está na `spec.md` (seção "Verificação": 1–29 e o 27b). Escrito ANTES do núcleo
(Princípio VIII): a primeira rodada fica em `verify_318_primeira_falha.txt`.

O HARNESS É O DA 306, IMPORTADO (`verify_306` como módulo), como na 312: o app com o dublê do Google
que falha fechado, o disjuntor de rede, o e-mail falso, os usuários descartáveis (`_usuario`), o
login pela API (`_cliente`), os eventos de dinheiro em meses isolados (`_evento`), a conexão separada
(`_no_banco`), o `cenario()` e o `limpar()`. Os dados levam o prefixo da 306 (`__v306_`) e saem no
`limpar()` dela; o que só a 318 cria (PIX recebidos, números de conta, interruptor) sai no
`limpar_318()`.

A caixa de e-mail é INJETADA: os avisos são montados aqui (`_aviso`) com nomes fictícios e entram
por `pix_email_ops.processar_brutos`, o mesmo caminho da rodada real depois do IMAP. Nenhuma rede.

Os valores dos cenários têm centavos "estranhos" (…,47 / …,83) para não casar com venda real do
espelho; a guarda `_valores_livres` sai com código 2 se algum casar.

Blocos (acompanham o `tasks.md`):

  H1  1–6, 23–25, 27b   o PIX óbvio entra sozinho; leitura e rodada
  H2  7–12              "É esta?"
  H3  13–16             nada conta em dobro
  H4  17–18             conta que recebeu
  H5  19–22             "Prime Dreams" no MEI
  H6  26–28             desfazer; pagamento sem arquivo nas telas
  L   29                limpeza e nenhuma rede (roda sempre)

Rodar (PowerShell, na raiz do worktree, com o banco do worktree em `.local-db-url`)::

    $env:DATABASE_URL = (Get-Content .local-db-url -Raw).Trim(); $env:FLASK_ENV = 'development'
    $env:MANTO_SEM_THREADS = '1'; $env:PYTHONUTF8 = '1'
    & $py specs\\318-pix-recebido-por-email\\verify_318.py
    & $py specs\\318-pix-recebido-por-email\\verify_318.py '--so=1,2'

Saída: 0 = tudo OK; 1 = algum cenário falhou; 2 = ambiente impróprio.
"""

from __future__ import annotations

import argparse
import io
import sys
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from email.mime.text import MIMEText
from email.utils import format_datetime
from pathlib import Path

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI.parent / "306-dinheiro-do-cancelamento"))

import verify_306 as v6  # noqa: E402 — sobe o app, o dublê, o disjuntor e o e-mail falso

from app import db  # noqa: E402
from app.constants import RoleName  # noqa: E402
from app.models import Client, EventClient, EventPayment  # noqa: E402

app = v6.app
estado = v6.estado
_garante = v6._garante
_igual = v6._igual
_no_banco = v6._no_banco
_no_banco_escrever = v6._no_banco_escrever
_cliente = v6._cliente
_codigo = v6._codigo
PREFIX = v6.PREFIX

TOKEN = uuid.uuid4().hex[:8]
MSGID_PREFIX = f"<v318-{TOKEN}-"
CONTA_MEI = "900318001"
CONTA_PRIME = "900318002"
S: dict = {}


# ── ajudantes ─────────────────────────────────────────────────────────────────────────────────
def _aviso(
    valor: str,
    nome: str,
    *,
    conta: str = CONTA_MEI,
    titular: str = "JOAO",
    dkim: bool = True,
    quando: datetime | None = None,
    devolucao: bool = False,
    formato_estranho: bool = False,
) -> tuple[bytes, str]:
    """Um aviso do Inter como chega na caixa (HTML puro), com `Message-ID` único."""
    if formato_estranho:
        frase = f"Olá, {titular} Seu Pix de R$ {valor} chegou."
    elif devolucao:
        frase = (
            f"Olá, {titular} Você recebeu a devolução de um Pix, no valor de R$ {valor}, "
            f"na conta {conta}. Acesse o app."
        )
    else:
        frase = (
            f"Olá, {titular} Você recebeu um Pix no valor de R$ {valor} de {nome}, na conta "
            f"{conta}. Abraços da equipe Inter."
        )
    msg = MIMEText(f"<html><body><table><tr><td>{frase}</td></tr></table></body></html>", "html")
    msg_id = f"{MSGID_PREFIX}{uuid.uuid4().hex[:12]}@inter.co>"
    msg["Message-ID"] = msg_id
    msg["From"] = "no-reply@inter.co"
    msg["To"] = "joao@mantoproducoes.com.br"
    msg["Subject"] = "Pix devolução recebida" if devolucao else "Pagamento Pix recebido"
    quando = quando or datetime.now(timezone.utc)
    msg["Date"] = format_datetime(quando)
    if dkim:
        msg["Authentication-Results"] = (
            "mx.google.com; dkim=pass header.i=@inter.co header.s=s1; spf=pass; dmarc=pass"
        )
    else:
        msg["Authentication-Results"] = "mx.google.com; dkim=pass header.i=@golpe.example; spf=fail"
    return msg.as_bytes(), msg_id


def _processar(*brutos: bytes) -> dict:
    from app.financeiro import pix_email_ops

    with app.app_context():
        return pix_email_ops.processar_brutos(list(brutos))


def _pix(msg_id: str) -> dict:
    linhas = _no_banco(
        "SELECT id, estado, event_payment_id, conta_id, tipo_sugestao, candidatos, motivo, "
        "decidido_por_id, pagamentos_extra, autenticado FROM pix_recebidos WHERE message_id = :m",
        m=msg_id,
    )
    _garante(len(linhas) == 1, f"PIX {msg_id}: esperava 1 linha, veio {len(linhas)}")
    (pid, est, pag, conta, tipo_sug, cands, motivo, quem, extra, aut) = linhas[0]
    return {
        "id": pid,
        "estado": est,
        "pagamento": pag,
        "conta_id": conta,
        "tipo_sugestao": tipo_sug,
        "candidatos": cands or [],
        "motivo": motivo,
        "decidido_por": quem,
        "extra": extra or [],
        "autenticado": aut,
    }


def _sugeridos(p: dict) -> set[int]:
    ids: set[int] = set()
    for c in p["candidatos"]:
        ids |= set(c.get("event_ids") or [])
    return ids


def _pagamentos(event_id: int) -> list[tuple]:
    return _no_banco(
        "SELECT id, amount, file_path, origem, conta_id FROM event_payments WHERE event_id = :e "
        "ORDER BY id",
        e=event_id,
    )


def _recebido(event_id: int) -> Decimal:
    return sum((Decimal(str(r[1] or 0)) for r in _pagamentos(event_id)), Decimal("0"))


def _conta_id(apelido: str) -> int:
    return _no_banco("SELECT id FROM contas_recebimento WHERE apelido = :a", a=apelido)[0][0]


def _venda(rotulo: str, valor: str, contratante: str, *, vendedor: str = "vend", **kw) -> int:
    """Venda isolada (2047+) com a contratante `contratante` (prefixada) ligada como cliente."""
    eid = v6._evento(rotulo, venda=float(Decimal(valor)), vendedor=vendedor, **kw)
    with app.app_context():
        c = Client(
            name=f"{PREFIX}{contratante}",
            phone=f"55993{uuid.uuid4().int % 10**8:08d}",
        )
        db.session.add(c)
        db.session.flush()
        db.session.add(EventClient(event_id=eid, client_id=c.id, relationship_type="Contratante"))
        db.session.commit()
    return eid


def _get(apelido: str, url: str, status: int = 200) -> dict:
    r = _cliente(apelido).get(url)
    _garante(r.status_code == status, f"GET {url} como {apelido} → {r.status_code} {r.get_data(as_text=True)[:200]}")
    return r.get_json(silent=True) or {}


def _post(apelido: str, url: str, corpo: dict | None = None):
    return _cliente(apelido).post(url, json=corpo or {})


def _ligar_leitura(desde: datetime | None = None) -> None:
    _no_banco_escrever(
        "UPDATE site_settings SET pix_email_ativo = true, pix_email_ativo_desde = :d WHERE id = 1",
        d=desde or datetime(2000, 1, 1),
    )


# ── preparo e limpeza ─────────────────────────────────────────────────────────────────────────
VALORES = (
    "7311.47", "8622.94", "4311.47", "5133.83", "3977.21", "6241.59", "2468.13", "1999.67",
    "2127.83", "1351.29", "1801.73", "2311.29", "1234.57", "2718.28", "1618.03", "4747.47",
    "3131.31", "5133.83", "3434.34", "2626.26", "5858.58", "2424.24", "1163.64", "3737.37",
)


def _valores_livres() -> None:
    """Nenhuma venda real do espelho pode ter valor/saldo igual aos dos cenários."""
    vals = [Decimal(v) for v in VALORES]
    batidas = _no_banco(
        "SELECT count(*) FROM calendar_events WHERE cancelled_at IS NULL AND group_leader_id IS NULL "
        "AND coalesce(google_event_id,'') NOT LIKE 'v306%' AND (sale_value = ANY(:v) OR "
        "sale_value / 2 = ANY(:v))",
        v=vals,
    )[0][0]
    if batidas:
        v6._sair(f"{batidas} venda(s) do espelho com valor igual a um dos cenários — troque os valores.")


def limpar_318() -> None:
    _no_banco_escrever(
        "DELETE FROM notifications WHERE entity_type = 'pix_recebido' AND entity_id IN "
        "(SELECT id FROM pix_recebidos WHERE message_id LIKE :m)",
        m="<v318-%",
    )
    _no_banco_escrever("DELETE FROM pix_recebidos WHERE message_id LIKE :m", m="<v318-%")
    _no_banco_escrever(
        "UPDATE contas_recebimento SET numero_conta = NULL WHERE numero_conta IN (:a, :b)",
        a=CONTA_MEI,
        b=CONTA_PRIME,
    )
    if "config_pix" in S:
        c = S["config_pix"]
        _no_banco_escrever(
            "UPDATE site_settings SET pix_email_ativo = :a, pix_email_ativo_desde = :d, "
            "pix_pagadores_proprios = :p, pix_email_ultimo_erro = :e, pix_email_ultimo_erro_em = :ee "
            "WHERE id = 1",
            **c,
        )
    _no_banco_escrever("DELETE FROM import_state WHERE key = 'pix_email_verify'")


def preparar() -> None:
    limpar_318()
    v6.limpar()
    v6._papeis_existem()
    _valores_livres()
    a, d, p, e, ee = _no_banco(
        "SELECT pix_email_ativo, pix_email_ativo_desde, pix_pagadores_proprios, pix_email_ultimo_erro, "
        "pix_email_ultimo_erro_em FROM site_settings WHERE id = 1"
    )[0]
    S["config_pix"] = {"a": a, "d": d, "p": p, "e": e, "ee": ee}
    v6._usuario("sa", RoleName.SUPERADMIN)
    v6._usuario("com", RoleName.COMERCIAL)
    v6._usuario("fin", RoleName.FINANCEIRO)
    v6._usuario("cast", RoleName.CASTING)
    v6._usuario("vend", RoleName.COMERCIAL)
    v6._usuario("vend2", RoleName.COMERCIAL)
    _no_banco_escrever(
        "UPDATE contas_recebimento SET numero_conta = :n WHERE apelido = 'Inter MEI'", n=CONTA_MEI
    )
    _no_banco_escrever(
        "UPDATE contas_recebimento SET numero_conta = :n WHERE apelido = 'Inter Prime'", n=CONTA_PRIME
    )
    _no_banco_escrever(
        "UPDATE site_settings SET pix_pagadores_proprios = :p WHERE id = 1",
        p="Prime Dreams\nMonta Producoes\nSocio Ficticio Verify",
    )
    _ligar_leitura()


# ── H1: o PIX óbvio entra sozinho ─────────────────────────────────────────────────────────────
def c1_valor_e_nome() -> None:
    eid = _venda("h1a", "7311.47", "Marisa Quintela Teste")
    raw, mid = _aviso("7.311,47", "MARISA QUINTELA TESTE")
    _processar(raw)
    p = _pix(mid)
    _garante(p["estado"] == "ligado_auto", f"estado {p['estado']} ({p['motivo']})")
    pags = _pagamentos(eid)
    _garante(len(pags) == 1, f"pagamentos: {pags}")
    _, valor, arquivo, origem, conta = pags[0]
    _igual(valor, "7311.47", "valor do pagamento")
    _garante(arquivo is None and origem == "pix_email", f"arquivo={arquivo} origem={origem}")
    _garante(conta == _conta_id("Inter MEI"), f"conta {conta}")
    _garante(p["pagamento"] == pags[0][0], "PIX não aponta para o pagamento")
    hist = _no_banco("SELECT actor_name FROM event_logs WHERE event_id = :e", e=eid)
    _garante(any("Sistema" in (h[0] or "") for h in hist), f"histórico sem 'Sistema': {hist}")
    noti = _no_banco(
        "SELECT count(*) FROM notifications WHERE kind = 'pix.ligado' AND user_id = :u "
        "AND entity_type = 'pix_recebido' AND entity_id = :p",
        u=estado["usuarios"]["vend"]["id"],
        p=p["id"],
    )[0][0]
    _garante(noti == 1, f"sino do vendedor: {noti}")
    S["h1_evento"], S["h1_raw"], S["h1_mid"] = eid, raw, mid


def c2_idempotente() -> None:
    _processar(S["h1_raw"])
    _processar(S["h1_raw"])
    _garante(len(_pagamentos(S["h1_evento"])) == 1, "o mesmo e-mail criou outro pagamento")
    n = _no_banco("SELECT count(*) FROM pix_recebidos WHERE message_id = :m", m=S["h1_mid"])[0][0]
    _garante(n == 1, f"{n} linhas para o mesmo e-mail")


def c3_sinal() -> None:
    eid = _venda("h1c", "8622.94", "Otavio Brandimarte Teste")
    raw, mid = _aviso("4.311,47", "Otavio Brandimarte Teste")
    _processar(raw)
    p = _pix(mid)
    _garante(p["estado"] == "ligado_auto", f"estado {p['estado']} ({p['motivo']})")
    _igual(_recebido(eid), "4311.47", "recebido depois do sinal")


def c4_ja_pagou_antes() -> None:
    eid = _venda("h1d", "10267.66", "Fulana Contratante Diversa")
    # o sinal (metade) pago por uma empresa de outro nome, confirmado à mão…
    raw1, mid1 = _aviso("5.133,83", "Empresa Pagadora Verify Ltda")
    _processar(raw1)
    p1 = _pix(mid1)
    _garante(p1["estado"] == "para_conferir", f"1º PIX deveria ir para conferir: {p1['estado']}")
    r = _post("com", f"/api/pix/{p1['id']}/confirmar", {"event_id": eid})
    _garante(r.status_code == 200, f"confirmar → {r.status_code} {r.get_data(as_text=True)[:200]}")
    # …o saldo, pela mesma empresa, liga sozinho
    raw2, mid2 = _aviso("5.133,83", "EMPRESA PAGADORA VERIFY LTDA")
    _processar(raw2)
    p2 = _pix(mid2)
    _garante(p2["estado"] == "ligado_auto", f"2º PIX: {p2['estado']} ({p2['motivo']})")
    _igual(_recebido(eid), "10267.66", "recebido total")


def c5_sem_dkim() -> None:
    eid = _venda("h1e", "3977.21", "Rogerio Autentico Teste")
    raw, mid = _aviso("3.977,21", "Rogerio Autentico Teste", dkim=False)
    _processar(raw)
    p = _pix(mid)
    _garante(p["estado"] == "para_conferir", f"sem DKIM ligou: {p['estado']}")
    _garante(not p["autenticado"], "marcou como autenticado")
    _garante(eid in _sugeridos(p), "a venda não foi sugerida")
    _garante(not _pagamentos(eid), "criou pagamento sem DKIM")


def c6_cancelada_e_quitada() -> None:
    canc = _venda("h1f", "6241.59", "Cecilia Cancelada Teste")
    _no_banco_escrever("UPDATE calendar_events SET cancelled_at = now() WHERE id = :e", e=canc)
    quit_ = _venda("h1g", "6241.59", "Cecilia Cancelada Teste")
    antigo = v6._comprovante(quit_, 6241.59)
    # Comprovante antigo: fora da janela de conciliação (o recente É conciliado — cenário 15).
    _no_banco_escrever(
        "UPDATE event_payments SET created_at = created_at - interval '60 days' WHERE id = :i", i=antigo
    )
    raw, mid = _aviso("6.241,59", "Cecilia Cancelada Teste")
    _processar(raw)
    p = _pix(mid)
    _garante(canc not in _sugeridos(p) and quit_ not in _sugeridos(p), f"sugeriu {_sugeridos(p)}")
    _garante(p["estado"] == "sem_venda", f"estado {p['estado']}")
    _garante(len(_pagamentos(quit_)) == 1, "mexeu na quitada")


# ── H2: "É esta?" ─────────────────────────────────────────────────────────────────────────────
def c7_duas_vendas() -> None:
    a = _venda("h2a", "2468.13", "Igual Primeira Teste")
    b = _venda("h2b", "2468.13", "Igual Segunda Teste", vendedor="vend2")
    raw, mid = _aviso("2.468,13", "Pagador Generico Nenhum")
    _processar(raw)
    p = _pix(mid)
    _garante(p["estado"] == "para_conferir", f"estado {p['estado']}")
    _garante({a, b} <= _sugeridos(p), f"sugeridos {_sugeridos(p)}")
    _garante(not _pagamentos(a) and not _pagamentos(b), "criou pagamento com duas candidatas")
    S["h2_pix"], S["h2_a"], S["h2_b"] = p["id"], a, b


def c8_so_valor() -> None:
    eid = _venda("h2c", "1999.67", "Nome Que Nao Bate")
    raw, mid = _aviso("1.999,67", "Outra Pessoa Qualquer")
    _processar(raw)
    p = _pix(mid)
    _garante(p["estado"] == "para_conferir", f"estado {p['estado']}")
    _garante(eid in _sugeridos(p), "não sugeriu")
    motivos = [m for c in p["candidatos"] for m in c.get("motivos", [])]
    _garante(any("saldo" in m for m in motivos), f"motivos {motivos}")
    S["h2c_pix"], S["h2c_ev"] = p["id"], eid


def c9_comercial_confirma() -> None:
    lista = _get("com", "/api/pix?aba=conferir")
    _garante(any(i["id"] == S["h2_pix"] for i in lista.get("itens", [])), "PIX fora da fila")
    r = _post("com", f"/api/pix/{S['h2_pix']}/confirmar", {"event_id": S["h2_a"]})
    _garante(r.status_code == 200, f"confirmar → {r.status_code} {r.get_data(as_text=True)[:200]}")
    p = _no_banco("SELECT estado, decidido_por_id FROM pix_recebidos WHERE id = :i", i=S["h2_pix"])[0]
    _garante(p[0] == "ligado_confirmado", f"estado {p[0]}")
    _garante(p[1] == estado["usuarios"]["com"]["id"], "decidido_por errado")
    _igual(_recebido(S["h2_a"]), "2468.13", "recebido da confirmada")
    _garante(not _pagamentos(S["h2_b"]), "a outra ganhou pagamento")
    r2 = _post("com", f"/api/pix/{S['h2_pix']}/confirmar", {"event_id": S["h2_b"]})
    _garante(r2.status_code == 409, f"confirmar de novo → {r2.status_code}")


def c10_descartar() -> None:
    r = _post("com", f"/api/pix/{S['h2c_pix']}/descartar", {"event_id": S["h2c_ev"]})
    _garante(r.status_code == 200, f"descartar → {r.status_code}")
    est = _no_banco("SELECT estado FROM pix_recebidos WHERE id = :i", i=S["h2c_pix"])[0][0]
    _garante(est == "sem_venda", f"estado {est}")
    lista = _get("com", "/api/pix?aba=conferir")
    _garante(all(i["id"] != S["h2c_pix"] for i in lista.get("itens", [])), "continua na fila")


def c11_outra_venda() -> None:
    sugerida = _venda("h2d", "1351.29", "Sugerida Errada Teste")
    certa = _venda("h2e", "9000.00", "Venda Certa Teste")
    raw, mid = _aviso("1.351,29", "Ninguem Conhecido")
    _processar(raw)
    p = _pix(mid)
    _garante(sugerida in _sugeridos(p), "não sugeriu a de valor igual")
    r = _post("fin", f"/api/pix/{p['id']}/confirmar", {"event_id": certa})
    _garante(r.status_code == 200, f"outra venda → {r.status_code} {r.get_data(as_text=True)[:200]}")
    _igual(_recebido(certa), "1351.29", "recebido da escolhida")
    _garante(not _pagamentos(sugerida), "a sugerida ganhou pagamento")


def c12_casting_recusado() -> None:
    r = _cliente("cast").get("/api/pix?aba=conferir")
    _garante(r.status_code == 403, f"Casting leu a fila: {r.status_code}")
    raw, mid = _aviso("1.801,73", "Casting Nao Pode")
    _venda("h2f", "1801.73", "Alguem Outro Nome")
    _processar(raw)
    p = _pix(mid)
    r2 = _post("cast", f"/api/pix/{p['id']}/confirmar", {"event_id": next(iter(_sugeridos(p)))})
    _garante(r2.status_code == 403, f"Casting confirmou: {r2.status_code}")


# ── H3: nada conta em dobro ───────────────────────────────────────────────────────────────────
def _anexar(apelido: str, event_id: int, valor: str, **extra):
    dados = {"amount": valor, "file": (io.BytesIO(b"%PDF-1.4 v318"), f"{PREFIX}comprovante.pdf")}
    dados.update(extra)
    return _cliente(apelido).post(
        f"/api/events/{event_id}/payments", data=dados, content_type="multipart/form-data"
    )


def c13_duplicata_anexar() -> None:
    eid = S["h1_evento"]  # pagamento de PIX sem arquivo, R$ 7.311,47
    pag_pix = _pagamentos(eid)[0][0]
    r = _anexar("com", eid, "7311.47")
    _garante(r.status_code == 409 and _codigo(r) == "possivel_duplicata", f"→ {r.status_code} {_codigo(r)}")
    _garante(len(_pagamentos(eid)) == 1, "criou pagamento sem perguntar")
    r2 = _anexar("com", eid, "7311.47", anexar_a=str(pag_pix))
    _garante(r2.status_code in (200, 201), f"anexar → {r2.status_code} {r2.get_data(as_text=True)[:200]}")
    pags = _pagamentos(eid)
    _garante(len(pags) == 1 and pags[0][2], f"arquivo não foi para o pagamento do PIX: {pags}")
    _igual(_recebido(eid), "7311.47", "recebido depois de anexar")


def c14_duplicata_outro() -> None:
    eid = _venda("h3b", "4622.58", "Hilda Duplicata Teste")
    raw, mid = _aviso("2.311,29", "Hilda Duplicata Teste")
    _processar(raw)
    _garante(_pix(mid)["estado"] == "ligado_auto", "sinal não ligou")
    r = _anexar("com", eid, "2311.29")
    _garante(r.status_code == 409 and _codigo(r) == "possivel_duplicata", f"→ {r.status_code}")
    r = _anexar("com", eid, "2311.29", forcar_novo="1")
    _garante(r.status_code in (200, 201), f"forcar_novo → {r.status_code}")
    _igual(_recebido(eid), "4622.58", "recebido com o segundo pagamento")


def c15_concilia() -> None:
    eid = _venda("h3c", "2127.83", "Joana Concilia Teste")
    manual = v6._comprovante(eid, 2127.83)
    raw, mid = _aviso("2.127,83", "Joana Concilia Teste")
    _processar(raw)
    p = _pix(mid)
    # Revisão adversarial: conciliar nunca é automático (o comprovante pode ser de outro pagamento
    # de mesmo valor) — pergunta, com o comprovante como opção.
    _garante(p["estado"] == "para_conferir", f"conciliou sozinho: {p['estado']}")
    _garante(any(c.get("conciliar") == manual for c in p["candidatos"]), f"{p['candidatos']}")
    _garante(len(_pagamentos(eid)) == 1, "criou pagamento antes de perguntar")
    r = _post("com", f"/api/pix/{p['id']}/confirmar", {"event_id": eid})
    _garante(r.status_code == 200, f"confirmar conciliação → {r.status_code} {r.get_data(as_text=True)[:200]}")
    p = _pix(mid)
    pags = _pagamentos(eid)
    _garante(len(pags) == 1, f"criou outro pagamento: {pags}")
    _garante(p["pagamento"] == manual, "não conciliou com o manual")
    _garante(pags[0][4] == _conta_id("Inter MEI"), "conta não marcada no manual")


def c16_valor_diferente() -> None:
    eid = S["h1_evento"]
    antes = len(_pagamentos(eid))
    r = _anexar("com", eid, "123.45")
    _garante(r.status_code in (200, 201), f"comprovante comum → {r.status_code}")
    _garante(len(_pagamentos(eid)) == antes + 1, "não criou")


# ── H4: conta que recebeu ─────────────────────────────────────────────────────────────────────
def c17_resumo_por_conta() -> None:
    eid = _venda("h4a", "3000.00", "Conta Manual Teste")
    r = _anexar("com", eid, "777.77", conta_id=str(_conta_id("Inter Prime")))
    _garante(r.status_code in (200, 201), f"manual com conta → {r.status_code}")
    res = _get("fin", "/api/pix/resumo-por-conta?meses=1")
    contas = {c["conta"]: c["por_mes"] for c in res.get("contas", [])}
    mes = datetime.now().strftime("%Y-%m")
    _garante(Decimal(contas.get("Inter Prime", {}).get(mes, "0")) >= Decimal("777.77"), f"Prime: {contas}")
    _garante(Decimal(contas.get("Inter MEI", {}).get(mes, "0")) >= Decimal("7311.47"), f"MEI: {contas}")
    r2 = _cliente("com").get("/api/pix/resumo-por-conta?meses=1")
    _garante(r2.status_code == 403, f"Comercial leu o resumo: {r2.status_code}")


def c18_conta_nao_cadastrada() -> None:
    raw, mid = _aviso("13,37", "Conta Desconhecida", conta="999999999")
    _processar(raw)
    p = _pix(mid)
    _garante(p["conta_id"] is None, "inventou conta")
    saude = _get("sa", "/api/pix/saude")
    _garante(saude.get("conta_nao_cadastrada_7d", 0) >= 1, f"saúde: {saude}")


# ── H5: "Prime Dreams" no MEI ─────────────────────────────────────────────────────────────────
def c19_repasse_da_prime() -> None:
    _venda("h5a", "5555.55", "Clube Prime Teste")
    raw_p, mid_p = _aviso("1.234,57", "Clube Sem Venda", conta=CONTA_PRIME, titular="PRIME")
    _processar(raw_p)
    raw, mid = _aviso("1.234,57", "PRIME DREAMS")
    _processar(raw)
    p = _pix(mid)
    _garante(p["estado"] == "conta_propria", f"repasse da Prime: {p['estado']} ({p['motivo']})")


def c20_repasse_infinitepay() -> None:
    eid = _venda("h5b", "1000.00", "Cartao Cliente Teste")
    _no_banco_escrever("UPDATE calendar_events SET payment_method = 'cartao' WHERE id = :e", e=eid)
    raw, mid = _aviso("950,00", "PRIME DREAMS")
    _processar(raw)
    p = _pix(mid)
    _garante(p["estado"] == "para_conferir" and p["tipo_sugestao"] == "repasse_infinitepay", f"{p}")
    # Vendas reais no cartão com saldo na mesma faixa podem ocupar as 3 sugestões: só então a
    # ausência da do verify é aceitável.
    concorrentes = _no_banco(
        "SELECT count(*) FROM calendar_events e WHERE e.payment_method = 'cartao' "
        "AND e.cancelled_at IS NULL AND e.group_leader_id IS NULL AND e.id <> :e "
        "AND e.sale_value BETWEEN 950 AND 1080",
        e=eid,
    )[0][0]
    _garante(eid in _sugeridos(p) or concorrentes >= 3, "não sugeriu a venda no cartão")
    lista_com = _get("com", "/api/pix?aba=conferir")
    _garante(all(i["id"] != p["id"] for i in lista_com.get("itens", [])), "Comercial viu o repasse")
    S["h5_pix"], S["h5_ev"] = p["id"], eid


def c21_comercial_nao_confirma_repasse() -> None:
    r = _post("com", f"/api/pix/{S['h5_pix']}/confirmar", {"event_ids": [S["h5_ev"]]})
    _garante(r.status_code == 403, f"Comercial confirmou repasse: {r.status_code}")


def c22_repasse_duas_vendas() -> None:
    r = _post("fin", f"/api/pix/{S['h5_pix']}/confirmar", {"event_ids": [S["h5_ev"]]})
    _garante(r.status_code == 200, f"Financeiro → {r.status_code} {r.get_data(as_text=True)[:200]}")
    _igual(_recebido(S["h5_ev"]), "1000.00", "pagamento pelo valor cobrado")
    motivo = _no_banco("SELECT motivo FROM pix_recebidos WHERE id = :i", i=S["h5_pix"])[0][0] or ""
    _garante("50,00" in motivo or "50.00" in motivo, f"taxa não anotada: {motivo}")
    a = _venda("h5c", "600.00", "Cartao Dois A")
    b = _venda("h5d", "400.00", "Cartao Dois B")
    _no_banco_escrever(
        "UPDATE calendar_events SET payment_method = 'cartao' WHERE id IN (:a, :b)", a=a, b=b
    )
    raw, mid = _aviso("940,00", "PRIME DREAMS")
    _processar(raw)
    p = _pix(mid)
    _garante(p["tipo_sugestao"] == "repasse_infinitepay", f"{p}")
    r2 = _post("fin", f"/api/pix/{p['id']}/confirmar", {"event_ids": [a, b]})
    _garante(r2.status_code == 200, f"duas vendas → {r2.status_code} {r2.get_data(as_text=True)[:200]}")
    _igual(_recebido(a), "600.00", "venda A")
    _igual(_recebido(b), "400.00", "venda B")
    # O cliente pagou na InfinitePay: a conta do pagamento é a dela, não o MEI do repasse.
    contas = {r[4] for r in _pagamentos(a) + _pagamentos(b)}
    _garante(contas == {_conta_id("InfinitePay Prime")}, f"conta do repasse: {contas}")
    S["h5_multi"] = p["id"]


# ── H1 (leitura) e H6 ─────────────────────────────────────────────────────────────────────────
def c23_desligada_e_antes_do_inicio() -> None:
    from app.financeiro import pix_email_ops

    chamadas: list = []

    def buscar_falso(**kw):
        chamadas.append(kw)
        return []

    _no_banco_escrever("UPDATE site_settings SET pix_email_ativo = false WHERE id = 1")
    _no_banco_escrever("DELETE FROM import_state WHERE key = 'pix_email'")
    with app.app_context():
        pix_email_ops.rodada(buscar=buscar_falso)
    _garante(not chamadas, "leu a caixa com a leitura desligada")
    _ligar_leitura(datetime.now() + timedelta(days=1))
    eid = _venda("h1h", "3131.31", "Antes Do Inicio Teste")
    raw, mid = _aviso("3.131,31", "Antes Do Inicio Teste")
    _processar(raw)
    _garante(_pix(mid)["estado"] == "ignorado", "aviso anterior ao início entrou")
    _garante(not _pagamentos(eid), "ligou aviso anterior ao início")
    _ligar_leitura()


def c24_formato_desconhecido() -> None:
    raw, mid = _aviso("10,00", "X", formato_estranho=True)
    _processar(raw)
    _garante(_pix(mid)["estado"] == "nao_entendido", "não marcou como não entendido")
    saude = _get("com", "/api/pix/saude")
    _garante(saude.get("nao_entendidos_7d", 0) >= 1, f"saúde: {saude}")


def c25_rodada_unica() -> None:
    from app.financeiro import pix_email_ops

    _no_banco_escrever("DELETE FROM import_state WHERE key = 'pix_email'")
    with app.app_context():
        primeira = pix_email_ops.claim_sweep(900)
    with app.app_context():
        segunda = pix_email_ops.claim_sweep(900)
    _garante(primeira and not segunda, f"claim: {primeira}, {segunda}")


def c26_comercial_nao_desfaz() -> None:
    r = _post("com", f"/api/pix/{S['h2_pix']}/desfazer")
    _garante(r.status_code == 403, f"Comercial desfez: {r.status_code}")


def c27_desfazer() -> None:
    # sem arquivo → o pagamento sai; o PIX volta para conferir
    r = _post("fin", f"/api/pix/{S['h2_pix']}/desfazer")
    _garante(r.status_code == 200, f"desfazer → {r.status_code} {r.get_data(as_text=True)[:200]}")
    _garante(not _pagamentos(S["h2_a"]), "o pagamento sem arquivo ficou")
    est = _no_banco("SELECT estado, event_payment_id FROM pix_recebidos WHERE id = :i", i=S["h2_pix"])[0]
    _garante(est[0] == "para_conferir" and est[1] is None, f"PIX: {est}")
    # com arquivo (anexado no 13) → vira manual
    pid = _pix(S["h1_mid"])["id"]
    r2 = _post("sa", f"/api/pix/{pid}/desfazer")
    _garante(r2.status_code == 200, f"desfazer com arquivo → {r2.status_code}")
    pags = [p for p in _pagamentos(S["h1_evento"]) if p[1] == Decimal("7311.47")]
    _garante(len(pags) == 1 and pags[0][2], f"o pagamento com arquivo sumiu: {pags}")
    # repasse de duas vendas → os dois pagamentos
    r3 = _post("fin", f"/api/pix/{S['h5_multi']}/desfazer")
    _garante(r3.status_code == 200, f"desfazer repasse → {r3.status_code}")


def c27b_reavaliar() -> None:
    from app.financeiro import pix_email_ops

    raw, mid = _aviso("2.718,28", "Sinal Antecipado Teste")
    _processar(raw)
    _garante(_pix(mid)["estado"] == "sem_venda", "devia ficar sem venda")
    raw2, mid2 = _aviso("1.618,03", "Sinal Muito Antigo Teste")
    _processar(raw2)
    _no_banco_escrever(
        "UPDATE pix_recebidos SET recebido_em = recebido_em - interval '8 days' WHERE message_id = :m",
        m=mid2,
    )
    a = _venda("h1i", "2718.28", "Sinal Antecipado Teste")
    b = _venda("h1j", "1618.03", "Sinal Muito Antigo Teste")
    with app.app_context():
        pix_email_ops.reavaliar_pendentes()
    _garante(_pix(mid)["estado"] == "ligado_auto", "não religou na reavaliação")
    _igual(_recebido(a), "2718.28", "recebido do sinal antecipado")
    _garante(_pix(mid2)["estado"] == "sem_venda" and not _pagamentos(b), "religou PIX de 8 dias")


def c28_sem_arquivo_nas_telas() -> None:
    eid = _venda("h6a", "4747.47", "Tela Sem Arquivo Teste")
    raw, mid = _aviso("4.747,47", "Tela Sem Arquivo Teste")
    _processar(raw)
    _garante(_pix(mid)["estado"] == "ligado_auto", "não ligou")
    d = _get("sa", f"/api/events/{eid}")
    itens = (d.get("pagamentos") or {}).get("items") or []
    _garante(itens and itens[0].get("file_path") is None, f"payload: {itens}")
    _garante(itens[0].get("origem") == "pix_email" and itens[0].get("conta") == "Inter MEI", f"{itens}")
    _garante((itens[0].get("pix") or {}).get("automatico") is True, f"{itens}")
    r = _cliente("sa").get(f"/events/{eid}")
    _garante(r.status_code == 200, f"Jinja → {r.status_code}")
    _garante('href="None"' not in r.get_data(as_text=True), "Jinja com link quebrado")


# ── R: achados da revisão adversarial (22/10) ─────────────────────────────────────────────────
def c30_dkim_forjado() -> None:
    from app.financeiro.pix_aviso import ler_aviso_inter

    _venda("r1", "3434.34", "Forjado Nome Teste")
    raw, _mid = _aviso("3.434,34", "Forjado Nome Teste")
    for velho, novo in (
        (b"header.i=@inter.co", b"header.i=@inter.co.evil.com"),
        (b"header.i=@inter.co", b"header.d=inter.co-evil.com"),
        (b"From: no-reply@inter.co", b"From: no-reply@inter.co.evil.com"),
        (b"Authentication-Results: mx.google.com;", b"Authentication-Results: mx.golpe.com;"),
    ):
        forjado = raw.replace(velho, novo)
        _garante(forjado != raw, f"substituição não aconteceu: {velho!r}")
        aviso = ler_aviso_inter(forjado)
        _garante(aviso is not None and not aviso.autenticado, f"forjado passou: {novo!r}")


def c31_nome_de_um_termo() -> None:
    eid = _venda("r2", "2626.26", "Teodora")
    raw, mid = _aviso("2.626,26", "TEODORA SILVA MACHADO")
    _processar(raw)
    p = _pix(mid)
    _garante(p["estado"] == "para_conferir", f"ligou sozinho por um termo só: {p['estado']}")
    _garante(not _pagamentos(eid), "criou pagamento")


def c32_excluir_pagamento_de_pix() -> None:
    eid = _venda("r3", "5858.58", "Excluir Pix Teste")
    raw, mid = _aviso("5.858,58", "Excluir Pix Teste")
    _processar(raw)
    pid = _pix(mid)["pagamento"]
    _garante(pid, "não ligou")
    r = _cliente("sa").delete(f"/api/payments/{pid}")
    _garante(r.status_code == 409 and _codigo(r) == "pagamento_de_pix", f"→ {r.status_code} {_codigo(r)}")
    _garante(len(_pagamentos(eid)) == 1, "apagou o pagamento do PIX")


def c33_conciliacao_outra_conta() -> None:
    eid = _venda("r4", "4848.48", "Sinal Na Cora Teste")
    manual = v6._comprovante(eid, 2424.24)
    _no_banco_escrever(
        "UPDATE event_payments SET conta_id = :c WHERE id = :i", c=_conta_id("Cora Monta"), i=manual
    )
    raw, mid = _aviso("2.424,24", "Sinal Na Cora Teste")
    _processar(raw)
    p = _pix(mid)
    _garante(all(c.get("conciliar") != manual for c in p["candidatos"]), "conciliou com a Cora")
    _garante(p["estado"] == "ligado_auto", f"o saldo devia ligar: {p['estado']} ({p['motivo']})")
    _igual(_recebido(eid), "4848.48", "sinal (Cora) + saldo (PIX)")


def c34_repasse_validado() -> None:
    a = _venda("r5", "1212.12", "Repasse Valida Teste")
    _no_banco_escrever("UPDATE calendar_events SET payment_method = 'cartao' WHERE id = :e", e=a)
    fora = _venda("r6", "8080.80", "Fora Das Sugestoes")
    raw, mid = _aviso("1.163,64", "PRIME DREAMS LTDA")
    _processar(raw)
    p = _pix(mid)
    _garante(p["tipo_sugestao"] == "repasse_infinitepay", f"'PRIME DREAMS LTDA' não é repasse: {p}")
    r = _post("fin", f"/api/pix/{p['id']}/confirmar", {"event_ids": [fora]})
    _garante(r.status_code == 400, f"repasse fora das sugestões → {r.status_code}")
    _garante(not _pagamentos(fora), "pagou venda fora das sugestões")


def c35_anexar_no_cancelado() -> None:
    eid = _venda("r7", "3737.37", "Anexar Cancelado Teste")
    raw, mid = _aviso("3.737,37", "Anexar Cancelado Teste")
    _processar(raw)
    pid = _pix(mid)["pagamento"]
    _garante(pid, "não ligou")
    _no_banco_escrever("UPDATE calendar_events SET cancelled_at = now() WHERE id = :e", e=eid)
    r = _anexar("com", eid, "3737.37", anexar_a=str(pid))
    _garante(r.status_code == 409, f"Comercial anexou no cancelado: {r.status_code}")
    _garante(_pagamentos(eid)[0][2] is None, "o arquivo entrou")


CENARIOS = [
    ("H1", "1", "valor + nome, venda única → liga sozinho", c1_valor_e_nome),
    ("H1", "2", "o mesmo e-mail duas vezes", c2_idempotente),
    ("H1", "3", "sinal de 50%", c3_sinal),
    ("H1", "4", "já pagou antes → liga sem o nome", c4_ja_pagou_antes),
    ("H1", "5", "sem DKIM do Inter → para conferir", c5_sem_dkim),
    ("H1", "6", "cancelada e quitada não são candidatas", c6_cancelada_e_quitada),
    ("H2", "7", "duas vendas com o mesmo saldo", c7_duas_vendas),
    ("H2", "8", "só o valor bate", c8_so_valor),
    ("H2", "9", "Comercial confirma", c9_comercial_confirma),
    ("H2", "10", "descartar a única sugestão", c10_descartar),
    ("H2", "11", "Outra venda…", c11_outra_venda),
    ("H2", "12", "Casting lê/responde (DEVE FALHAR)", c12_casting_recusado),
    ("H3", "13", "comprovante igual ao PIX → possível duplicata → anexar", c13_duplicata_anexar),
    ("H3", "14", "é outro pagamento", c14_duplicata_outro),
    ("H3", "15", "PIX concilia com comprovante manual", c15_concilia),
    ("H3", "16", "comprovante de valor diferente", c16_valor_diferente),
    ("H4", "17", "resumo por conta × mês", c17_resumo_por_conta),
    ("H4", "18", "conta não cadastrada", c18_conta_nao_cadastrada),
    ("H5", "19", "repasse da Prime → ignorado", c19_repasse_da_prime),
    ("H5", "20", "repasse da InfinitePay → só Financeiro", c20_repasse_infinitepay),
    ("H5", "21", "Comercial confirma repasse (DEVE FALHAR)", c21_comercial_nao_confirma_repasse),
    ("H5", "22", "repasse: valor cobrado, taxa e duas vendas", c22_repasse_duas_vendas),
    ("H1", "23", "leitura desligada / antes do início", c23_desligada_e_antes_do_inicio),
    ("H6", "24", "formato desconhecido → saúde", c24_formato_desconhecido),
    ("H1", "25", "duas rodadas ao mesmo tempo", c25_rodada_unica),
    ("H6", "26", "Comercial desfaz (DEVE FALHAR)", c26_comercial_nao_desfaz),
    ("H6", "27", "desfazer: sem arquivo, com arquivo, repasse", c27_desfazer),
    ("H1", "27b", "PIX adiantado religa em 7 dias, não em 8", c27b_reavaliar),
    ("H6", "28", "pagamento sem arquivo no React e no Jinja", c28_sem_arquivo_nas_telas),
    ("R", "30", "e-mail forjado não é autenticado", c30_dkim_forjado),
    ("R", "31", "um termo só no nome não liga sozinho", c31_nome_de_um_termo),
    ("R", "32", "excluir pagamento de PIX pela tela do evento (DEVE FALHAR)", c32_excluir_pagamento_de_pix),
    ("R", "33", "comprovante de outra conta não é conciliado", c33_conciliacao_outra_conta),
    ("R", "34", "repasse: 'LTDA' e escolha fora das sugestões (DEVE FALHAR)", c34_repasse_validado),
    ("R", "35", "anexar no cancelado pela Comercial (DEVE FALHAR)", c35_anexar_no_cancelado),
]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--so", default=None)
    args = parser.parse_args()
    if args.so:
        v6.OPCOES["so"] = {s.strip() for s in args.so.split(",") if s.strip()}
    v6.guarda_de_ambiente()
    print("\n── verify 318 ──")
    try:
        preparar()
        for bloco, num, nome, fn in CENARIOS:
            v6.cenario(bloco, num, nome, fn)
    finally:
        try:
            limpar_318()
            v6.limpar()
            sobras = _no_banco("SELECT count(*) FROM pix_recebidos WHERE message_id LIKE '<v318-%'")[0][0]
            _garante(not sobras, f"sobraram {sobras} PIX do verify")
            sobras306 = v6._sobras_do_verify()
            _garante(not sobras306, f"a limpeza deixou: {sobras306}")
            _garante(not v6.rede_bloqueada, f"conexões externas tentadas: {v6.rede_bloqueada}")
            v6.resultados.append(("L", "29 · limpeza e nenhuma rede", "OK", ""))
            print("  OK         29 · limpeza e nenhuma rede")
        except Exception as exc:  # noqa: BLE001
            v6.resultados.append(("L", "29 · limpeza e nenhuma rede", "FALHA", str(exc)))
            print(f"  FALHA      29 · limpeza: {exc}")
    falhas = [r for r in v6.resultados if r[2] != "OK"]
    print(f"\n{len(v6.resultados) - len(falhas)}/{len(v6.resultados)} OK")
    return 1 if falhas else 0


if __name__ == "__main__":
    sys.exit(main())
