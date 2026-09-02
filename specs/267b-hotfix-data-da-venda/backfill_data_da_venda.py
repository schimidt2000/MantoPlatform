"""Backfill da data da venda (hotfix 267b) — DRY-RUN por padrão; `--execute` grava.

Eventos com venda (`sale_value > 0`), não cancelados e `sale_date` NULL ganham a data em que a
venda foi registrada, pela melhor evidência disponível, nesta ordem:

1. `created_at` da linha viva de comissão do evento (a linha nasce no instante em que a venda é
   gravada — é a evidência mais direta; cobre as 44 vendas de agosto/setembro de 2026);
2. `created_at` do primeiro `EventLog` "Atualizou dados comerciais: venda …" (eventos importados do
   Google cuja venda foi digitada depois, ou de vendedor que não recebe comissão);
3. `created_at` do próprio evento (último recurso).

Os carimbos são UTC (`utcnow`); a data é convertida para o dia em São Paulo antes de virar
`sale_date`. As linhas de comissão `a_pagar`/`no_banco` do evento que também estejam sem
`sale_date` recebem a mesma data — é ela que define o ciclo da Planilha de Pagamentos.

Rodar no backend do Render (só SELECT sem `--execute`)::

    cd /opt/render/project/src && FLASK_ENV=development PYTHONPATH=$PWD \\
      .venv/bin/python specs/267b-hotfix-data-da-venda/backfill_data_da_venda.py [--execute]

Local (manto_local)::

    $env:DATABASE_URL = (gc .local-db-url -Raw).Trim(); $env:FLASK_ENV = "development"
    .\\.venv\\Scripts\\python.exe specs\\267b-hotfix-data-da-venda\\backfill_data_da_venda.py
"""
from __future__ import annotations

import os
import sys
from datetime import UTC, date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))
os.environ.setdefault("FLASK_ENV", "development")

TZ_SP = ZoneInfo("America/Sao_Paulo")


def dia_sp(carimbo_utc: datetime) -> date:
    """`utcnow` gravado sem fuso → dia civil em São Paulo."""
    return carimbo_utc.replace(tzinfo=UTC).astimezone(TZ_SP).date()


def data_sugerida(ev, CommissionPayment, EventLog) -> tuple[date, str]:
    cp = (
        CommissionPayment.query.filter(
            CommissionPayment.event_id == ev.id, CommissionPayment.status != "cancelado"
        )
        .order_by(CommissionPayment.created_at.asc())
        .first()
    )
    if cp is not None:
        return dia_sp(cp.created_at), f"comissão #{cp.id}"
    log = (
        EventLog.query.filter(
            EventLog.event_id == ev.id,
            EventLog.message.like("Atualizou dados comerciais: venda%"),
        )
        .order_by(EventLog.created_at.asc())
        .first()
    )
    if log is not None:
        return dia_sp(log.created_at), "log da venda"
    return dia_sp(ev.created_at), "criação do evento"


def main(execute: bool) -> int:
    from app import create_app, db
    from app.models import CalendarEvent, CommissionPayment, EventLog

    app = create_app()
    with app.app_context():
        eventos = (
            CalendarEvent.query.filter(
                CalendarEvent.sale_value > 0,
                CalendarEvent.sale_date.is_(None),
                CalendarEvent.cancelled_at.is_(None),
            )
            .order_by(CalendarEvent.id)
            .all()
        )
        print(f"{'MODO EXECUTE' if execute else 'DRY-RUN'} — {len(eventos)} evento(s) com venda e sem data\n")
        print(f"{'ev':>5}  {'vendedor':<28} {'venda':>10}  {'festa':<10}  {'data sugerida':<13} fonte             título")
        comissoes_tocadas = 0
        for ev in eventos:
            data, fonte = data_sugerida(ev, CommissionPayment, EventLog)
            vendedor = ev.seller.name[:28] if ev.seller else "(sem vendedor)"
            print(f"{ev.id:>5}  {vendedor:<28} {float(ev.sale_value):>10.2f}  {ev.start_at.date()}  {data}    {fonte:<17} {ev.title[:44]}")
            if execute:
                ev.sale_date = data
                for cp in CommissionPayment.query.filter(
                    CommissionPayment.event_id == ev.id,
                    CommissionPayment.sale_date.is_(None),
                    CommissionPayment.status.in_(["a_pagar", "no_banco"]),
                ).all():
                    cp.sale_date = data
                    comissoes_tocadas += 1
        if execute:
            db.session.commit()
            print(f"\nGravado: {len(eventos)} evento(s) e {comissoes_tocadas} linha(s) de comissão com sale_date preenchida.")
        else:
            print("\nNada gravado. Repita com --execute para aplicar.")
    return 0


if __name__ == "__main__":
    sys.exit(main("--execute" in sys.argv[1:]))
