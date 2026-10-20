"""Rebaixa os tetos 712/423 que a 307 gravou nas vagas de Papai Noel / Ajudante do Noel (feature 309).

Entre 16/10/2026 e o deploy da 309 a tabela dizia "Papai Noel [712, 800, 850, 900] / Ajudante do Noel
[423, 480, 510, 540]" (engenharia reversa do preço da Visita Mágica) e esse número virou a BASE do
`EventRole.cache_cap` dos eventos criados ou vinculados a orçamento nesse período — mais noturno (+50) e
fora de SP por cima, e a coluna da duração (2h–4h). O vínculo 273 nunca rebaixa teto — por isso este script.

DRY-RUN por padrão: relata toda vaga em eventos a partir de 16/10/2026 que (a) se chama "Papai Noel" /
"Ajudante do Noel" e tem teto, ou (b) tem teto EXATAMENTE num valor das listas 712/423 (qualquer nome —
um Noel apelidado). A base vem da nota do teto (feature 239: "base 2h R$ 800 + noturno R$ 50 = R$ 850")
ou do próprio teto quando ele é exatamente um valor da lista. Com `--execute` rebaixa pela DIFERENÇA da
coluna (712→600 = −112; 800→650 = −150; 423→270 = −153; …) só as vagas com o nome certo, sem cachê
digitado e sem artista, e registra "(teto corrigido pela 309: 762 → 650)" na nota. Nome diferente, cachê
já digitado, artista escalado ou base fora da lista → "não corrigida — conferir à mão".

Rodar no backend do Render (Shell ou SSH)::

    cd /opt/render/project/src && MANTO_SEM_THREADS=1 PYTHONPATH=$PWD \\
      .venv/bin/python specs/309-produtos-de-tabela/rebaixar_tetos_noel_309.py [--execute]
"""

from __future__ import annotations

import os
import re
import sys
from datetime import datetime
from decimal import Decimal
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))
os.environ.setdefault("FLASK_ENV", "development")
os.environ.setdefault("MANTO_SEM_THREADS", "1")

DESDE = datetime(2026, 10, 16)
# nome → (bases gravadas pela 307 por coluna, cachê certo por coluna)
TABELAS = {
    "Papai Noel": ([712, 800, 850, 900], [600, 650, 675, 700]),
    "Ajudante do Noel": ([423, 480, 510, 540], [270, 320, 345, 370]),
}
TODAS_AS_BASES = sorted({b for bases, _ in TABELAS.values() for b in bases})
RE_BASE = re.compile(r"base \d+h(?: ÷ 4 × \d+h)? R\$ ?([\d.]+)")


def _base_da_nota(nota: str | None) -> int | None:
    """A base em reais que a nota do teto (feature 239) registra, ou ``None``."""
    m = RE_BASE.search(nota or "")
    if not m:
        return None
    try:
        return int(m.group(1).replace(".", ""))
    except ValueError:
        return None


def _inteiro(cap: Decimal) -> int | None:
    return int(cap) if cap == cap.to_integral_value() else None


def _delta(nome: str, cap: Decimal, nota: str | None) -> int | None:
    """Quanto tirar do teto: a diferença da coluna cuja base a 307 gravou; ``None`` = não é da lista."""
    if nome not in TABELAS:
        return None
    bases, certos = TABELAS[nome]
    base = _base_da_nota(nota)
    if base is None:
        base = _inteiro(cap)
    if base not in bases:
        return None
    i = bases.index(base)
    delta = bases[i] - certos[i]
    return delta if cap - delta >= certos[i] else None


def main(execute: bool) -> int:
    from sqlalchemy import or_

    from app import create_app, db
    from app.models import CalendarEvent, EventRole

    app = create_app()
    with app.app_context():
        vagas = (
            db.session.query(EventRole, CalendarEvent)
            .join(CalendarEvent, CalendarEvent.id == EventRole.event_id)
            .filter(
                CalendarEvent.start_at >= DESDE,
                EventRole.cache_cap.isnot(None),
                or_(
                    EventRole.character_name.in_(list(TABELAS)),
                    EventRole.cache_cap.in_([Decimal(f"{b}.00") for b in TODAS_AS_BASES]),
                ),
            )
            .order_by(CalendarEvent.start_at, EventRole.id)
            .all()
        )
        print(
            f"{'MODO EXECUTE' if execute else 'DRY-RUN'} — {len(vagas)} vaga(s) candidatas "
            f"(Noel/Ajudante com teto, ou teto exatamente 712/800/850/900/423/480/510/540) em eventos desde {DESDE:%d/%m/%Y}\n"
        )
        corrigidas = 0
        conferir = 0
        ja_certas = 0
        for role, ev in vagas:
            cap = Decimal(role.cache_cap).quantize(Decimal("0.01"))
            delta = _delta(role.character_name, cap, role.cache_cap_note)
            if role.character_name not in TABELAS:
                acao = "não corrigida — conferir à mão (nome diferente)"
            elif delta is None:
                _, certos = TABELAS[role.character_name]
                if _base_da_nota(role.cache_cap_note) in certos or _inteiro(cap) in certos:
                    ja_certas += 1
                    continue
                acao = "não corrigida — conferir à mão (base não é 712/423)"
            elif role.cache_value is not None:
                acao = "não corrigida — conferir à mão (cachê já digitado)"
            elif role.talent_id is not None:
                acao = "não corrigida — conferir à mão (artista escalado)"
            else:
                acao = f"rebaixar para {cap - delta:.2f}"
            if acao.startswith("rebaixar"):
                corrigidas += 1
            else:
                conferir += 1
            print(
                f"  ev {ev.id:<5} {ev.start_at:%d/%m/%Y %H:%M}  vaga {role.id:<6} {role.character_name!r:<20} "
                f"teto {float(cap):>8.2f}  cachê {('—' if role.cache_value is None else f'{float(role.cache_value):.2f}'):>8}  "
                f"artista {role.talent_id or '—':<5} → {acao}"
            )
            if execute and acao.startswith("rebaixar"):
                novo = cap - delta
                role.cache_cap = novo
                role.cache_cap_note = (
                    f"{role.cache_cap_note or ''} (teto corrigido pela 309: {cap:.0f} → {novo:.0f})"
                ).strip()
        if execute:
            db.session.commit()
        print(
            f"\n{'corrigidas' if execute else 'a corrigir'}: {corrigidas} · conferir à mão: {conferir} · "
            f"já no cachê certo (600/270): {ja_certas}"
        )
        print("Gravado." if execute else "Nada gravado. Repita com --execute para aplicar.")
    return 0


if __name__ == "__main__":
    sys.exit(main("--execute" in sys.argv[1:]))
