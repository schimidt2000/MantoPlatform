"""Verificação da feature 238 (teto autorizado) contra o manto_local.

    DATABASE_URL=$(cat .local-db-url) .venv/Scripts/python \
        specs/238-teto-autorizado/verify_238.py
"""

from __future__ import annotations

import os
import sys
from zoneinfo import ZoneInfo

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

FALHAS: list[str] = []
TZ = ZoneInfo("America/Sao_Paulo")


def check(cond: bool, label: str) -> None:
    print(f"  [{'ok' if cond else 'FALHOU'}] {label}")
    if not cond:
        FALHAS.append(label)


def main() -> int:
    from app import create_app, db
    from app.calendar.casting_ops import assign_role
    from app.models import CalendarEvent, EventRole

    app = create_app()
    with app.app_context():
        # Evento de laboratório próprio (o espelho pode ter sido recriado desde outros verifies).
        from datetime import datetime
        evento = CalendarEvent(
            title="(R&I) TESTE VERIFY 238 - LAB",
            start_at=datetime(2026, 8, 22, 20, 0), end_at=datetime(2026, 8, 22, 22, 0),
            google_event_id="fake-verify-238",
        )
        db.session.add(evento)
        db.session.commit()
        papel = EventRole(
            event_id=evento.id, character_name="Lab Teto 238",
            role_type="character", cache_value=460, cache_cap=370,
        )
        db.session.add(papel)
        db.session.commit()

        def salvar(valor, admin=False):
            assign_role(
                evento, papel, talent_id=None, cache_value=str(valor),
                travel_cache=None, actor_name="verify-238",
                is_superadmin=admin, tz=TZ,
            )
            return float(papel.cache_value or 0)

        print("1. Teto efetivo = max(cap, valor salvo pelo admin)")
        check(salvar(460) == 460, "casting MANTÉM os 460 autorizados (antes rebaixava p/ 370)")
        check(salvar(500) == 460, "acima do autorizado rebaixa para o teto efetivo (460)")
        check(salvar(420) == 420, "qualquer valor até o teto efetivo passa (420)")
        # Atenção: depois de salvar 420, o teto efetivo volta a ser o cap (max(370, 420)=420).
        check(salvar(450) == 420, "teto efetivo acompanha o valor vigente (450 → 420)")
        check(salvar(600, admin=True) == 600, "superadmin continua livre (600)")
        check(salvar(590) == 590, "e os 600 do admin viram o novo teto do casting (590 ok)")

        print("2. Regressão do comportamento clássico")
        papel2 = EventRole(
            event_id=evento.id, character_name="Lab Classico 238",
            role_type="character", cache_value=300, cache_cap=370,
        )
        db.session.add(papel2)
        db.session.commit()

        def salvar2(valor, admin=False):
            assign_role(
                evento, papel2, talent_id=None, cache_value=str(valor),
                travel_cache=None, actor_name="verify-238",
                is_superadmin=admin, tz=TZ,
            )
            return float(papel2.cache_value or 0)

        check(salvar2(350) == 350, "abaixo do cap segue normal")
        check(salvar2(400) == 370, "acima do cap (sem autorização prévia) rebaixa ao cap")
        papel3 = EventRole(
            event_id=evento.id, character_name="Lab Sem Cap 238",
            role_type="extra", cache_value=None, cache_cap=None,
        )
        db.session.add(papel3)
        db.session.commit()
        assign_role(
            evento, papel3, talent_id=None, cache_value="999",
            travel_cache=None, actor_name="verify-238", is_superadmin=False, tz=TZ,
        )
        check(float(papel3.cache_value) == 999, "papel sem cap continua sem teto")

    print()
    if FALHAS:
        print(f"FALHOU: {len(FALHAS)}:")
        for f in FALHAS:
            print(f"  - {f}")
        return 1
    print("VERIFY 238: tudo passou.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
