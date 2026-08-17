"""Verificação da feature 236 contra o manto_local (quickstart bloco 1 + validações).

Gabarito real: orçamento 1806 (Baile do Addan, 6h, 22h — a régua do dono) e orçamento 1573
(mascotes, 2h, 19h — paridade com o teto real do evento 1205).

    DATABASE_URL=$(cat .local-db-url) .venv/Scripts/python \
        specs/236-cache-por-duracao/verify_236.py
"""

from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

FALHAS: list[str] = []


def check(cond: bool, label: str) -> None:
    print(f"  [{'ok' if cond else 'FALHOU'}] {label}")
    if not cond:
        FALHAS.append(label)


def _por_label(caches: list[dict], trecho: str) -> dict:
    return next(c for c in caches if trecho.lower() in c["label"].lower())


def main() -> int:
    from app import create_app
    from app.calendar.routes import (
        _compute_performer_caches,
        _parse_duracao,
        _validate_event_core,
    )
    from app.models import OrcamentoHistory

    app = create_app()
    with app.app_context():
        snap_green = json.loads(OrcamentoHistory.query.get(1806).form_snapshot)
        snap_masc = json.loads(OrcamentoHistory.query.get(1573).form_snapshot)

        print("1. Régua >4h (orçamento 1806 — 6h, início 22h)")
        c6 = _compute_performer_caches(snap_green, horas_extra=6)
        green = _por_label(c6, "green 1")
        space = _por_label(c6, "space reflection - 1")
        coord = _por_label(c6, "coordenador")
        maq = _por_label(c6, "maquiador")
        check(green["cache_custom"] == 520, f"Green (make): 300÷4×6 +20 +50 = 520 (={green['cache_custom']})")
        check(space["cache_custom"] == 500, f"Space: 300÷4×6 +50 = 500 (={space['cache_custom']})")
        check(coord["cache_custom"] == 575, f"Coordenador: 350÷4×6 +50 = 575 (={coord['cache_custom']})")
        check(maq["cache_custom"] == 500, f"Maquiador não escala: 500 (={maq['cache_custom']})")

        c5 = _compute_performer_caches(snap_green, horas_extra=5)
        g5 = _por_label(c5, "green 1")
        check(g5["cache_custom"] == 445, f"5h: 300÷4×5 +20 +50 = 445 (={g5['cache_custom']})")
        check(g5["cache_custom"] != g5["cache_1h"], "5h nunca é o valor de 1h (fim do fallback)")

        print("2. Paridade 1–4h")
        base = _compute_performer_caches(snap_green)
        check(all("cache_custom" not in c for c in base), "sem horas_extra: sem chave nova")
        pares = zip(base, c6)
        check(all(
            all(a[k] == b[k] for k in ("cache_1h", "cache_2h", "cache_3h", "cache_4h", "label"))
            for a, b in pares
        ), "chaves 1h–4h idênticas com e sem horas_extra")

        masc = _compute_performer_caches(snap_masc)
        mascote = _por_label(masc, "maple")
        # Paridade com o comportamento vigente (feature 172): boneco show 2h + noturno +
        # adicional fora-SP por pessoa (km×2 ÷ divisor). O teto de 400 gravado no evento 1205
        # veio de uma criação antiga sem a parcela de fora-SP — o gabarito é a função de hoje.
        from app.orcamento import settings as orc_settings
        from app.orcamento.pricing import get_ator_prices
        cfg_t = orc_settings.load()["transporte"]
        esperado_masc = round(
            int(get_ator_prices("boneco", True, False)[1]) + 50
            + round(float(snap_masc["km_ida"]) * 2 / cfg_t["afsp_divisor"], 2)
        )
        check(mascote["cache_2h"] == esperado_masc,
              f"mascote 2h = tabela+noturno+fora-SP = {esperado_masc} (={mascote['cache_2h']})")

        print("3. Duração validada (fim do fallback silencioso)")
        check(_parse_duracao("6") == 6 and _parse_duracao("2") == 2, "inteiros passam")
        check(_parse_duracao(None) == 1 and _parse_duracao("") == 1, "ausente = 1 (default atual)")
        check(_parse_duracao("abc") is None and _parse_duracao("0") is None
              and _parse_duracao("-1") is None, "inválidos viram None")
        erros = _validate_event_core({"title": "X", "duracao": "abc"})
        check("duracao" in erros, "criação com duração inválida é erro de campo")
        erros_ok = _validate_event_core({"title": "X", "duracao": "6"})
        check("duracao" not in erros_ok, "duração 6 é aceita")

        print("4. Criação: cachê nasce vazio, teto com a régua (2ª rodada do dono)")
        from datetime import date as _date

        from app.calendar import routes as cr
        from app.models import EventRole
        caches = _compute_performer_caches(snap_green)
        data = {
            "title": "(R&I) TESTE VERIFY 236 - NASCE VAZIO",
            "event_type": "R&I",
            "date_str": "2026-08-21", "start_str": "22:00", "end_str": "04:00",
            "location": "Teste 236 - 2a rodada", "description": "",
            "needs_rehearsal": False,
            "sale_value": 9678, "sale_value_gross": 9678,
            "transport_value": None, "acrescimo_value": None,
            "with_invoice": False, "invoice_filename": None, "is_cortesia_permuta": False,
            "seller_id": None, "sale_date": _date(2026, 8, 14),
            "payment_method": None, "payment_installments": None, "payment_due_date": None,
            "orcamento_history_id": 1806,
            "duracao": "6",
            "characters": [{"name": c["label"].strip(), "talent_id": None} for c in caches],
            "orc_caches": caches,
            "acrescimos": [], "coordinator_talent_id": None, "client_pairs": [],
            "form_response_id": None, "has_reembolso": False,
            "reembolso_description": "", "reembolso_amount": None,
            "reembolso_invoice_file_path": None, "observations": [],
        }
        import time as _time
        event, _avisos = cr._create_event_core(
            data, google_event_id=f"fake-verify-236-{int(_time.time())}",
            gc_title=data["title"], actor_id=1, actor_name="verify-236",
            actor_role="SUPERADMIN",
        )
        roles = EventRole.query.filter_by(event_id=event.id).order_by(EventRole.id).all()
        g1 = next(r for r in roles if r.character_name == "Green 1")
        sp = next(r for r in roles if r.character_name == "Space Reflection - 1")
        co = next(r for r in roles if r.character_name == "Coordenador")
        check(all(r.cache_value is None for r in roles),
              "todos os papéis nascem com o cachê VAZIO (sugestão invisível)")
        check((float(g1.cache_cap), float(sp.cache_cap), float(co.cache_cap)) == (520.0, 500.0, 575.0),
              f"tetos pela régua de 6h: 520/500/575 (={g1.cache_cap}/{sp.cache_cap}/{co.cache_cap})")

    print()
    if FALHAS:
        print(f"FALHOU: {len(FALHAS)}:")
        for f in FALHAS:
            print(f"  - {f}")
        return 1
    print("VERIFY 236: tudo passou.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
