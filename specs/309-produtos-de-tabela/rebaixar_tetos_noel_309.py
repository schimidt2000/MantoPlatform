"""Rebaixa os tetos 712/423 que a 307 gravou nas vagas de Papai Noel / Ajudante do Noel (feature 309).

Entre 16/10/2026 e o deploy da 309 a tabela dizia "Papai Noel 712 / Ajudante do Noel 423" (engenharia
reversa do preço da Visita Mágica) e esse número virou `EventRole.cache_cap` dos eventos criados ou
vinculados a orçamento nesse período. O vínculo 273 nunca rebaixa teto — por isso este script.

DRY-RUN por padrão: relata toda vaga com teto exatamente 712,00 ou 423,00 em eventos a partir de
16/10/2026, qualquer nome (um Noel apelidado nasce com o nome digitado). Com `--execute` rebaixa para
600 / 270 SÓ as vagas "Papai Noel" / "Ajudante do Noel" sem cachê digitado e sem artista, e registra
"(teto corrigido pela 309: 712 → 600)" na nota do teto. Nome diferente, cachê já digitado ou artista
escalado → "não corrigida — conferir à mão" (o superadmin decide na tela).

Rodar no backend do Render (Shell ou SSH)::

    cd /opt/render/project/src && MANTO_SEM_THREADS=1 PYTHONPATH=$PWD \\
      .venv/bin/python specs/309-produtos-de-tabela/rebaixar_tetos_noel_309.py [--execute]
"""

from __future__ import annotations

import os
import sys
from datetime import datetime
from decimal import Decimal
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))
os.environ.setdefault("FLASK_ENV", "development")
os.environ.setdefault("MANTO_SEM_THREADS", "1")

DESDE = datetime(2026, 10, 16)
TETOS = {
    Decimal("712.00"): (Decimal("600.00"), "Papai Noel"),
    Decimal("423.00"): (Decimal("270.00"), "Ajudante do Noel"),
}


def main(execute: bool) -> int:
    from app import create_app, db
    from app.models import CalendarEvent, EventRole

    app = create_app()
    with app.app_context():
        vagas = (
            db.session.query(EventRole, CalendarEvent)
            .join(CalendarEvent, CalendarEvent.id == EventRole.event_id)
            .filter(CalendarEvent.start_at >= DESDE, EventRole.cache_cap.in_(list(TETOS)))
            .order_by(CalendarEvent.start_at, EventRole.id)
            .all()
        )
        print(
            f"{'MODO EXECUTE' if execute else 'DRY-RUN'} — {len(vagas)} vaga(s) com teto 712/423 em eventos desde {DESDE:%d/%m/%Y}\n"
        )
        corrigidas = 0
        conferir = 0
        for role, ev in vagas:
            novo, nome_esperado = TETOS[Decimal(role.cache_cap).quantize(Decimal("0.01"))]
            if role.character_name != nome_esperado:
                acao = "não corrigida — conferir à mão (nome diferente)"
            elif role.cache_value is not None:
                acao = "não corrigida — conferir à mão (cachê já digitado)"
            elif role.talent_id is not None:
                acao = "não corrigida — conferir à mão (artista escalado)"
            else:
                acao = f"rebaixar para {novo:.0f}"
            if acao.startswith("rebaixar"):
                corrigidas += 1
            else:
                conferir += 1
            print(
                f"  ev {ev.id:<5} {ev.start_at:%d/%m/%Y %H:%M}  vaga {role.id:<6} {role.character_name!r:<22} "
                f"teto {float(role.cache_cap):>7.2f}  cachê {('—' if role.cache_value is None else f'{float(role.cache_value):.2f}'):>8}  "
                f"artista {role.talent_id or '—':<5} → {acao}"
            )
            if execute and acao.startswith("rebaixar"):
                antes = int(role.cache_cap)
                role.cache_cap = novo
                role.cache_cap_note = f"{role.cache_cap_note or ''} (teto corrigido pela 309: {antes} → {int(novo)})".strip()
        if execute:
            db.session.commit()
        print(
            f"\n{'corrigidas' if execute else 'a corrigir'}: {corrigidas} · conferir à mão: {conferir}"
        )
        print("Gravado." if execute else "Nada gravado. Repita com --execute para aplicar.")
    return 0


if __name__ == "__main__":
    sys.exit(main("--execute" in sys.argv[1:]))
