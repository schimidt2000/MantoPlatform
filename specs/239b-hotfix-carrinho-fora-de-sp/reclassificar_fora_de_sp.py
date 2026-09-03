"""Reclassifica dentro/fora de SP os eventos "desconhecidos" (hotfix 239b) — DRY-RUN por padrão.

Para cada evento futuro (a partir de 7 dias atrás) não cancelado, com endereço e `is_outside_sp`
NULL, pergunta ao `_lookup_sp_status` — agora com Geocoding do Google entre o CEP e o fallback por
texto — e mostra o resultado. Com `--execute` grava a classificação e, quando fora de SP, busca a
estimativa de trajeto (é ela que dá base à parcela do veículo no teto do carrinho). `--todos` inclui
os eventos passados (229 no histórico em 02/09/2026; só interessa para relatório).

O dry-run também consulta o Google (só leitura). Custo: uma chamada de Geocoding por evento.

Rodar no backend do Render::

    cd /opt/render/project/src && FLASK_ENV=development PYTHONPATH=$PWD \\
      .venv/bin/python specs/239b-hotfix-carrinho-fora-de-sp/reclassificar_fora_de_sp.py [--execute] [--todos]
"""
from __future__ import annotations

import os
import sys
from datetime import timedelta
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))
os.environ.setdefault("FLASK_ENV", "development")


def main(execute: bool, todos: bool) -> int:
    from app import create_app, db
    from app.calendar.routes import _fetch_travel_data, _lookup_sp_status
    from app.constants import now_sp
    from app.models import CalendarEvent, SiteSetting

    app = create_app()
    with app.app_context():
        q = CalendarEvent.query.filter(
            CalendarEvent.is_outside_sp.is_(None),
            CalendarEvent.cancelled_at.is_(None),
            CalendarEvent.location.isnot(None),
            CalendarEvent.location != "",
        )
        if not todos:
            q = q.filter(CalendarEvent.start_at >= now_sp() - timedelta(days=7))
        eventos = q.order_by(CalendarEvent.start_at).all()
        settings = SiteSetting.query.get(1)
        print(f"{'MODO EXECUTE' if execute else 'DRY-RUN'} — {len(eventos)} evento(s) sem classificação\n")
        contagem = {"fora": 0, "dentro": 0, "desconhecido": 0}
        for ev in eventos:
            flag = _lookup_sp_status(ev.location or "")
            rotulo = "FORA" if flag else ("dentro" if flag is False else "?")
            contagem["fora" if flag else ("dentro" if flag is False else "desconhecido")] += 1
            print(f"  ev {ev.id:<5} {ev.start_at.date()}  {rotulo:<7} {(ev.location or '')[:60]!r:<64} {ev.title[:36]}")
            if execute and flag is not None:
                ev.is_outside_sp = flag
                if flag and not ev.travel_distance_km:
                    _fetch_travel_data(ev, settings)
        if execute:
            db.session.commit()
        print(f"\nfora de SP: {contagem['fora']} · dentro: {contagem['dentro']} · continua desconhecido: {contagem['desconhecido']}")
        print("Gravado." if execute else "Nada gravado. Repita com --execute para aplicar.")
    return 0


if __name__ == "__main__":
    args = sys.argv[1:]
    sys.exit(main("--execute" in args, "--todos" in args))
