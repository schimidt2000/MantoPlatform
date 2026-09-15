"""Feature 299 — dados que podem enganar as listas, para o dono conferir antes do deploy.

SÓ LEITURA: nenhuma escrita, nenhum commit. Não depende de código da 299 (roda antes do deploy).

Uso no manto-backend (Render), pela entrada padrão:
    ssh ... 'cd /opt/render/project/src && MANTO_SEM_THREADS=1 PYTHONPATH=$PWD .venv/bin/python -' \
        < specs/299-sem-valor-cobrancas/dados_pre_deploy_299.py

Lista:
1. os 6 casos grandes de recebido acima do valor (o 344 entre eles), com cada comprovante;
2. as vendas desde a data de início com comprovante sem valor e quanto cada uma passaria a cobrar;
3. os eventos de valor simbólico, com o valor antes do desconto (bruto), para a edição de título;
4. a consulta do SC-001: as vendas sem valor que o painel "Sem valor" deve mostrar.
"""

import sys
from collections import defaultdict
from datetime import datetime
from decimal import Decimal

sys.path.insert(0, ".")

from app import create_app  # noqa: E402
from app.models import CalendarEvent, EventPayment, SiteSetting  # noqa: E402

GRANDES = (344, 85, 184, 288, 309, 319)
MARCADORES = ("🟧", "🟠")
UM_REAL = Decimal("1.00")


def brl(valor) -> str:
    """Valor em reais no padrão brasileiro, ou "sem valor"."""
    if valor is None:
        return "sem valor"
    texto = f"{Decimal(valor):,.2f}"
    return "R$ " + texto.replace(",", "X").replace(".", ",").replace("X", ".")


def casos_grandes() -> None:
    """Imprime cada comprovante dos casos grandes de recebido acima do valor."""
    print("=== 1. Casos grandes de recebido acima do valor (somando o grupo)")
    for lider_id in GRANDES:
        lider = CalendarEvent.query.session.get(CalendarEvent, lider_id)
        if lider is None:
            print(f"  {lider_id}: não existe")
            continue
        total = Decimal(0)
        print(f"  Venda {lider_id} — {lider.title[:60]!r} — valor {brl(lider.sale_value)}")
        for evento in [lider] + list(lider.satellites):
            papel = "principal" if evento.id == lider_id else "outro evento do grupo"
            cancelado = ", CANCELADO" if evento.cancelled_at else ""
            print(f"    evento {evento.id} ({papel}, {evento.start_at:%d/%m/%Y}{cancelado})")
            pagamentos = EventPayment.query.filter_by(event_id=evento.id).order_by(
                EventPayment.created_at
            )
            for pag in pagamentos:
                total += pag.amount or 0
                arquivo = (pag.file_path or "").rsplit("/", 1)[-1]
                print(
                    f"      comprovante {pag.id}: {brl(pag.amount)} em {pag.created_at:%d/%m/%Y %H:%M}"
                    f" · arquivo {arquivo}"
                )
        print(
            f"    recebido do grupo {brl(total)} · diferença {brl(total - (lider.sale_value or 0))}"
        )


def comprovantes_sem_valor(corte: datetime) -> None:
    """Imprime as vendas com comprovante sem valor e quanto passariam a cobrar."""
    print("\n=== 2. Vendas desde a data de início com comprovante sem valor")
    nulos = (
        EventPayment.query.join(CalendarEvent, EventPayment.event_id == CalendarEvent.id)
        .filter(EventPayment.amount.is_(None), CalendarEvent.start_at >= corte)
        .all()
    )
    por_venda = defaultdict(int)
    for pag in nulos:
        evento = CalendarEvent.query.session.get(CalendarEvent, pag.event_id)
        por_venda[(evento.group_leader or evento).id] += 1
    if not por_venda:
        print("  nenhuma")
    for venda_id, quantos in sorted(por_venda.items()):
        venda = CalendarEvent.query.session.get(CalendarEvent, venda_id)
        ids = [venda.id] + [s.id for s in venda.satellites]
        pagos = EventPayment.query.filter(EventPayment.event_id.in_(ids)).all()
        recebido = sum((p.amount or 0 for p in pagos), Decimal(0))
        saldo = (venda.sale_value or 0) - recebido
        print(
            f"  Venda {venda_id} ({venda.start_at:%d/%m/%Y}) {venda.title[:50]!r}: valor "
            f"{brl(venda.sale_value)}, recebido com valor {brl(recebido)}, {quantos} sem valor "
            f"→ cobraria {brl(saldo)}"
        )


def valores_simbolicos(corte: datetime) -> None:
    """Imprime os eventos de valor simbólico com o bruto (o R32 compara campo a campo)."""
    print("\n=== 3. Eventos de valor simbólico (líquido entre R$ 0,01 e R$ 0,99)")
    eventos = CalendarEvent.query.filter(
        CalendarEvent.start_at >= corte,
        CalendarEvent.sale_value > 0,
        CalendarEvent.sale_value < UM_REAL,
    ).all()
    for evento in eventos:
        print(
            f"  {evento.id} {evento.start_at:%d/%m/%Y} líquido {brl(evento.sale_value)} "
            f"bruto {brl(evento.sale_value_gross)} {evento.title[:45]!r}"
        )
    if not eventos:
        print("  nenhum")


def sem_valor_sc001(corte: datetime) -> None:
    """A consulta do SC-001: vendas sem valor que o painel "Sem valor" deve mostrar."""
    print('\n=== 4. SC-001: vendas sem valor esperadas no painel "Sem valor"')
    candidatos = CalendarEvent.query.filter(
        CalendarEvent.start_at >= corte,
        CalendarEvent.cancelled_at.is_(None),
        CalendarEvent.group_leader_id.is_(None),
    ).all()
    esperadas = [
        e
        for e in candidatos
        if (e.sale_value is None or e.sale_value < UM_REAL)
        and not e.is_cortesia_permuta
        and (e.event_type or "") not in ("ENSAIO", "VIRTUAL")
        and not e.title.lstrip().startswith(MARCADORES)
    ]
    for evento in sorted(esperadas, key=lambda e: e.start_at):
        print(
            f"  {evento.id} {evento.start_at:%d/%m/%Y} valor {brl(evento.sale_value)} {evento.title[:45]!r}"
        )
    print(f"  total: {len(esperadas)}")


app = create_app()
with app.app_context():
    configuracao = SiteSetting.query.first()
    dia = configuracao.release_date if configuracao and configuracao.release_date else None
    corte = datetime.combine(dia, datetime.min.time()) if dia else datetime(2026, 6, 1)
    print(f"Data de início: {corte:%d/%m/%Y}\n")
    casos_grandes()
    comprovantes_sem_valor(corte)
    valores_simbolicos(corte)
    sem_valor_sc001(corte)
