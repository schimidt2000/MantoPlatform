"""Contagem pré-deploy da 303 — eventos PASSADOS com dinheiro que já não estão no Google Agenda.

SÓ LEITURA, dos dois lados:

- banco: o ``manto_local`` recém-restaurado do dump da madrugada, em transação somente leitura
  (``default_transaction_read_only=on``); nenhum ``create_app()``, nenhuma thread;
- Google: só ``events.list`` e ``events.get``. A credencial é montada do ``site_settings.google_token``
  e renovada só em memória — nada é gravado de volta (o ``load_credentials`` do app gravaria).

Por que existe: a 303 faz o sync parar de apagar evento com dinheiro. O ciclo automático só limpa do
mês corrente em diante, então o que sumiu do Google em meses PASSADOS ainda está no banco — e seria
marcado de uma vez, com faixa e sino, no primeiro "Limpar eventos fantasma" depois do deploy. Esta
contagem diz quantos são, para o dono decidir se a primeira rodada marca sem sino (spec, Casos de
borda, "Evento no passado"; research R17).

Dois passos:

1. ``--so-sonda``: o que o Google responde de verdade para os eventos que o sync já apagou por
   sumiço (ids tirados do ``audit_logs``) — calibra os três modos de "ausente" do núcleo e do dublê.
2. a contagem: por mês passado, lista o Google (com paginação), consulta por id cada evento do banco
   que não veio na lista e classifica.

Uso (na raiz do repo)::

    $env:PYTHONUTF8 = '1'
    .venv\\Scripts\\python.exe specs\\303-sync-nao-apaga-venda\\contagem_pre_deploy.py --so-sonda
    .venv\\Scripts\\python.exe specs\\303-sync-nao-apaga-venda\\contagem_pre_deploy.py [--desde 2025-01]
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import psycopg
import psycopg.rows
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

RAIZ = Path(__file__).resolve().parents[2]
CALENDAR_ID = "eventos@mantoproducoes.com.br"
TZ = ZoneInfo("America/Sao_Paulo")

# Espelham app/calendar/routes.py:68-76 e app/constants.py (o script não importa o app de propósito:
# importar `app` sobe configuração e pode abrir conexão gravável).
SOUND_TECH_TALENT_ID = 42
SOUND_TECH_CHARACTER = "Técnico de Som"
TIPO_SHOW = "SHOW"
TIPO_VIRTUAL = "VIRTUAL"
TIPO_ENSAIO = "ENSAIO"
PREFIXO_ID_LOCAL = "virtual-local-"

AUSENTE, PRESENTE, INCONCLUSIVO = "ausente", "presente", "inconclusivo"


class GoogleSoLeitura:
    """Só `list` (paginado) e `get`. Qualquer outro uso do cliente fica fora do alcance do script."""

    def __init__(self, creds: Credentials) -> None:
        self._eventos = build("calendar", "v3", credentials=creds, cache_discovery=False).events()
        self.chamadas: Counter[str] = Counter()

    def listar_mes(self, inicio: date, fim: date) -> list[dict]:
        """Todos os eventos de [inicio, fim), com paginação (o app hoje não pagina)."""
        t0 = datetime(inicio.year, inicio.month, 1, tzinfo=TZ).isoformat()
        t1 = datetime(fim.year, fim.month, 1, tzinfo=TZ).isoformat()
        itens: list[dict] = []
        pedido = self._eventos.list(
            calendarId=CALENDAR_ID, timeMin=t0, timeMax=t1, singleEvents=True,
            orderBy="startTime", showDeleted=False, maxResults=2500,
        )
        while pedido is not None:
            self.chamadas["list"] += 1
            resposta = pedido.execute()
            itens.extend(resposta.get("items", []))
            pedido = self._eventos.list_next(pedido, resposta)
        return itens

    def consultar(self, google_event_id: str) -> tuple[str, dict | None, str]:
        """(desfecho, item, motivo) — a mesma regra que a 303 vai ter em `consultar_evento`."""
        self.chamadas["get"] += 1
        try:
            item = self._eventos.get(calendarId=CALENDAR_ID, eventId=google_event_id).execute()
        except HttpError as exc:
            status = getattr(exc, "status_code", None) or getattr(exc.resp, "status", None)
            if status in (404, 410):
                return AUSENTE, None, f"http_{status}"
            return INCONCLUSIVO, None, f"http_{status}"
        except Exception as exc:  # noqa: BLE001 — rede, timeout: a sonda precisa registrar, não cair
            return INCONCLUSIVO, None, type(exc).__name__
        if item.get("status") == "cancelled":
            return AUSENTE, item, "cancelled"
        inicio = item.get("start") or {}
        if not (inicio.get("dateTime") or inicio.get("date")):
            return INCONCLUSIVO, item, "sem_inicio"
        return PRESENTE, item, "serie_recorrente" if item.get("recurrence") else "ok"


@dataclass
class Totais:
    """O que a saída mostra ao dono."""

    meses: int = 0
    eventos_no_banco: int = 0
    fora_da_lista: int = 0
    com_dinheiro: list[dict] = field(default_factory=list)
    vazios: list[dict] = field(default_factory=list)
    mudaram_de_data: list[dict] = field(default_factory=list)
    presentes_sem_mudanca: list[dict] = field(default_factory=list)
    inconclusivos: list[dict] = field(default_factory=list)
    motivos: Counter = field(default_factory=Counter)


def _conectar() -> psycopg.Connection:
    url = (RAIZ / ".local-db-url").read_text(encoding="utf-8").strip()
    url = re.sub(r"^postgresql\+\w+://", "postgresql://", url)
    if "localhost" not in url and "127.0.0.1" not in url:
        sys.exit("ABORTADO: .local-db-url não aponta para o banco local.")
    conn = psycopg.connect(
        url, autocommit=True, options="-c default_transaction_read_only=on",
        row_factory=psycopg.rows.dict_row,
    )
    somente_leitura = conn.execute("show default_transaction_read_only").fetchone()
    if not somente_leitura or list(somente_leitura.values())[0] != "on":
        sys.exit("ABORTADO: a conexão não está em modo somente leitura.")
    return conn


def _credencial(conn: psycopg.Connection) -> Credentials:
    linha = conn.execute("select google_token from site_settings where id = 1").fetchone()
    if not linha or not linha["google_token"]:
        sys.exit("ABORTADO: site_settings.google_token vazio no espelho.")
    dados = json.loads(linha["google_token"])
    creds = Credentials(
        token=dados.get("token"), refresh_token=dados.get("refresh_token"),
        token_uri=dados.get("token_uri"), client_id=dados.get("client_id"),
        client_secret=dados.get("client_secret"), scopes=dados.get("scopes"),
    )
    # O token do dump costuma estar vencido. Renova SÓ em memória: nada é gravado (o refresh token
    # continua valendo para a produção, que renova o dela sozinha).
    if not creds.valid and creds.refresh_token:
        creds.refresh(Request())
    return creds


def _brl(valor: Decimal | None) -> str:
    inteiro, centavos = f"{Decimal(valor or 0):,.2f}".split(".")
    return f"R$ {inteiro.replace(',', '.')},{centavos}"


def _inicio_do_item(item: dict) -> datetime | None:
    """Início do item do Google como horário de parede de São Paulo, sem fuso (como o banco)."""
    inicio = item.get("start") or {}
    if inicio.get("dateTime"):
        return datetime.fromisoformat(inicio["dateTime"]).astimezone(TZ).replace(tzinfo=None)
    if inicio.get("date"):
        return datetime.fromisoformat(inicio["date"])
    return None


def _preso(conn: psycopg.Connection, ev: dict) -> dict[str, Any]:
    """A regra de "com dinheiro" da FR-001 (research R2), em SQL."""
    eid = ev["id"]
    pag = conn.execute(
        "select count(*) n, coalesce(sum(amount), 0) total from event_payments where event_id = %s",
        (eid,),
    ).fetchone()
    contratos = conn.execute(
        "select count(*) n from event_contracts where event_id = %s", (eid,)
    ).fetchone()["n"]
    escalados = conn.execute(
        """select count(*) n from event_roles
           where event_id = %(id)s and talent_id is not null
             and not (%(show)s and role_type = 'extra' and character_name = %(vaga)s
                      and talent_id = %(tecnico)s)""",
        {"id": eid, "show": ev["event_type"] == TIPO_SHOW, "vaga": SOUND_TECH_CHARACTER,
         "tecnico": SOUND_TECH_TALENT_ID},
    ).fetchone()["n"]
    satelites = conn.execute(
        "select count(*) n from calendar_events where group_leader_id = %s", (eid,)
    ).fetchone()["n"]
    grupo = "satelite" if ev["group_leader_id"] else ("principal" if satelites else None)
    venda = Decimal(ev["sale_value"] or 0)
    return {
        "venda": venda, "recebido": Decimal(pag["total"] or 0), "n_comprovantes": pag["n"],
        "contratos": contratos, "escalados": escalados, "grupo": grupo,
        "vazio": not (venda > 0 or pag["n"] or contratos or escalados or grupo),
    }


def _extras_do_vazio(conn: psycopg.Connection, ev: dict) -> dict[str, int]:
    """O que o evento "vazio" ainda carrega e a exclusão levaria junto (só para o dono saber)."""
    eid = ev["id"]

    def n(sql: str) -> int:
        return conn.execute(sql, (eid,)).fetchone()["n"]

    return {
        "ensaios_filhos": n("select count(*) n from calendar_events where parent_event_id = %s"),
        "reembolsos": n("select count(*) n from event_reimbursements where event_id = %s"),
        "notas": n("select count(*) n from event_invoices where event_id = %s"),
        "presentes_3d": n("select count(*) n from event_3d_gifts where event_id = %s"),
        "vaga_som_com_cache": n(
            f"""select count(*) n from event_roles where event_id = %s and role_type = 'extra'
                and character_name = '{SOUND_TECH_CHARACTER}' and talent_id = {SOUND_TECH_TALENT_ID}
                and (coalesce(cache_value, 0) > 0 or coalesce(payment_status, 'nao_pago') <> 'nao_pago')"""
        ),
    }


def _convites_aceitos(conn: psycopg.Connection, event_id: int) -> int:
    return conn.execute(
        """select count(*) n from event_roles
           where event_id = %s and talent_id is not null and invite_status = 'accepted'""",
        (event_id,),
    ).fetchone()["n"]


def _linha(ev: dict, **mais: Any) -> dict:
    return {"id": ev["id"], "titulo": (ev["title"] or "")[:70], "quando": ev["start_at"],
            "tipo": ev["event_type"], **mais}


def sonda(conn: psycopg.Connection, google: GoogleSoLeitura) -> None:
    """O que o Google responde para evento que o sync já apagou por sumiço."""
    print("== SONDA: resposta do Google para eventos apagados por sumiço (desde 01/08/2026) ==")
    linhas = conn.execute(
        """select created_at, entity_name, detail from audit_logs
           where action = 'auto_deleted' and created_at >= '2026-08-01' order by created_at"""
    ).fetchall()
    if not linhas:
        print("   nenhuma linha auto_deleted no período")
    for linha in linhas:
        achado = re.search(r"gcal:([^\s|]+)", linha["detail"] or "")
        if not achado:
            print(f"   {linha['created_at']:%d/%m %H:%M}  sem id do Google no detalhe")
            continue
        desfecho, item, motivo = google.consultar(achado.group(1))
        forma = ""
        if item is not None:
            forma = f" · item com chaves {sorted(item.keys())}"
        print(f"   {linha['created_at']:%d/%m %H:%M}  {(linha['entity_name'] or '')[:50]:50}  "
              f"-> {desfecho} ({motivo}){forma}")
    print()


def contar(conn: psycopg.Connection, google: GoogleSoLeitura, desde: date, ate: date) -> Totais:
    """Percorre os meses [desde, ate) que têm evento no banco."""
    totais = Totais()
    meses = conn.execute(
        """select distinct date_trunc('month', start_at)::date mes from calendar_events
           where start_at >= %s and start_at < %s order by 1""",
        (desde, ate),
    ).fetchall()
    for m in meses:
        inicio: date = m["mes"]
        fim = date(inicio.year + (inicio.month == 12), inicio.month % 12 + 1, 1)
        try:
            itens = google.listar_mes(inicio, fim)
        except Exception as exc:  # noqa: BLE001 — um mês sem resposta não pode parar os outros
            print(f"   {inicio:%Y-%m}: LISTA FALHOU ({type(exc).__name__}) — mês pulado")
            continue
        vivos = {i.get("id") for i in itens if i.get("id")}
        eventos = conn.execute(
            """select id, title, start_at, end_at, event_type, google_event_id, sale_value,
                      group_leader_id, parent_event_id
               from calendar_events
               where start_at >= %s and start_at < %s and cancelled_at is null
               order by start_at""",
            (inicio, fim),
        ).fetchall()
        totais.meses += 1
        totais.eventos_no_banco += len(eventos)
        fora = [
            e for e in eventos
            if e["event_type"] != TIPO_VIRTUAL
            and not (e["google_event_id"] or "").startswith(PREFIXO_ID_LOCAL)
            and e["google_event_id"] not in vivos
        ]
        totais.fora_da_lista += len(fora)
        for ev in fora:
            _classificar(conn, google, ev, totais)
        print(f"   {inicio:%Y-%m}: {len(eventos):4d} no banco · {len(itens):4d} no Google · "
              f"{len(fora):3d} fora da lista")
    return totais


def _classificar(conn: psycopg.Connection, google: GoogleSoLeitura, ev: dict, totais: Totais) -> None:
    desfecho, item, motivo = google.consultar(ev["google_event_id"])
    totais.motivos[f"{desfecho}:{motivo}"] += 1
    if desfecho == INCONCLUSIVO:
        totais.inconclusivos.append(_linha(ev, motivo=motivo))
        return
    if desfecho == PRESENTE:
        novo = _inicio_do_item(item or {})
        if novo and novo != ev["start_at"]:
            totais.mudaram_de_data.append(
                _linha(ev, para=novo, convites_aceitos=_convites_aceitos(conn, ev["id"]))
            )
        else:
            totais.presentes_sem_mudanca.append(_linha(ev, motivo=motivo))
        return
    preso = _preso(conn, ev)
    if preso["vazio"]:
        totais.vazios.append(_linha(ev, motivo=motivo, **_extras_do_vazio(conn, ev)))
    else:
        totais.com_dinheiro.append(_linha(ev, motivo=motivo, **preso))


def imprimir(totais: Totais, google: GoogleSoLeitura) -> None:
    print()
    print("== RESULTADO ==")
    print(f"meses varridos: {totais.meses} · eventos no banco: {totais.eventos_no_banco} · "
          f"fora da lista do Google: {totais.fora_da_lista}")
    print(f"respostas do Google por evento: {dict(totais.motivos)}")
    print(f"chamadas ao Google: {dict(google.chamadas)}")

    cd = totais.com_dinheiro
    print()
    print(f"-- COM DINHEIRO, ausência confirmada (seriam MARCADOS): {len(cd)} · venda "
          f"{_brl(sum((e['venda'] for e in cd), Decimal(0)))} · recebido "
          f"{_brl(sum((e['recebido'] for e in cd), Decimal(0)))}")
    for e in cd:
        motivos = [f"venda {_brl(e['venda'])}" if e["venda"] else "",
                   f"{e['n_comprovantes']} comprovante(s) {_brl(e['recebido'])}" if e["n_comprovantes"] else "",
                   "contrato" if e["contratos"] else "",
                   f"{e['escalados']} escalado(s)" if e["escalados"] else "",
                   f"grupo ({e['grupo']})" if e["grupo"] else ""]
        print(f"   {e['id']:5d}  {e['quando']:%d/%m/%Y}  {e['titulo']:70}  "
              f"{' · '.join(x for x in motivos if x)}")

    md = totais.mudaram_de_data
    print()
    print(f"-- MUDARAM DE DATA no Google (seriam movidos, não marcados): {len(md)} · e-mails de "
          f"'evento alterado' que sairiam: {sum(e['convites_aceitos'] for e in md)}")
    for e in md:
        print(f"   {e['id']:5d}  {e['quando']:%d/%m/%Y %H:%M} -> {e['para']:%d/%m/%Y %H:%M}  "
              f"{e['titulo']:60}  {e['convites_aceitos']} convite(s) aceito(s)")

    vz = totais.vazios
    print()
    print(f"-- VAZIOS, ausência confirmada (seriam APAGADOS, como hoje): {len(vz)}")
    for chave, rotulo in (("ensaios_filhos", "com ensaio ligado"), ("reembolsos", "com reembolso"),
                          ("notas", "com nota fiscal"), ("presentes_3d", "com presente 3D"),
                          ("vaga_som_com_cache", "SHOW com cachê na vaga automática de som")):
        quais = [e for e in vz if e[chave]]
        print(f"   {rotulo}: {len(quais)}" + (f"  ids {[e['id'] for e in quais][:20]}" if quais else ""))
    por_tipo = Counter(e["tipo"] or "sem tipo" for e in vz)
    print(f"   por tipo: {dict(por_tipo)}")

    print()
    print(f"-- PRESENTES no Google, fora da lista do mês e sem mudança de data: "
          f"{len(totais.presentes_sem_mudanca)}  {[e['id'] for e in totais.presentes_sem_mudanca][:20]}")
    print(f"-- INCONCLUSIVOS: {len(totais.inconclusivos)}  "
          f"{[(e['id'], e['motivo']) for e in totais.inconclusivos][:20]}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--desde", default=None, help="AAAA-MM (padrão: o mês do evento mais antigo)")
    parser.add_argument("--so-sonda", action="store_true")
    args = parser.parse_args()

    conn = _conectar()
    google = GoogleSoLeitura(_credencial(conn))
    dump = conn.execute("select max(created_at) ate from audit_logs").fetchone()["ate"]
    print(f"espelho: último audit_log em {dump:%d/%m/%Y %H:%M} UTC · calendário {CALENDAR_ID}")
    print()

    sonda(conn, google)
    if args.so_sonda:
        return

    hoje = datetime.now(TZ).date()
    ate = date(hoje.year, hoje.month, 1)  # meses ANTERIORES ao corrente: o ciclo cuida do resto
    if args.desde:
        ano, mes = (int(x) for x in args.desde.split("-"))
        desde = date(ano, mes, 1)
    else:
        primeiro = conn.execute("select min(start_at) d from calendar_events").fetchone()["d"]
        desde = date(primeiro.year, primeiro.month, 1)
    print(f"== CONTAGEM: meses de {desde:%Y-%m} até antes de {ate:%Y-%m} ==")
    imprimir(contar(conn, google, desde, ate), google)


if __name__ == "__main__":
    main()
