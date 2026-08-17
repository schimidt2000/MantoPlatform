"""Verificação da feature 235 contra o manto_local (quickstart blocos 1, 2, 5, 7 e 8).

Roda com DATABASE_URL apontando para o espelho local:

    DATABASE_URL=$(cat .local-db-url) .venv/Scripts/python \
        specs/235-educamanto-responsabilidades/verify_235.py

A paridade numérica é RE-DERIVADA aqui a partir das linhas cruas do banco (não chama a
fórmula para conferir a própria fórmula): soma de custos independente × margem, comparada ao
resultado de `pricing_ops.calcular_configuracao`.
"""

from __future__ import annotations

import math
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

FALHAS: list[str] = []


def check(cond: bool, label: str) -> None:
    status = "ok" if cond else "FALHOU"
    print(f"  [{status}] {label}")
    if not cond:
        FALHAS.append(label)


def main() -> int:
    from app import create_app
    from app.educamanto import pdf_textos, pricing_ops, quote_ops
    from app.educamanto.pdf import gerar_orcamento_pdf
    from app.educamanto.pricing_ops import Responsabilidades
    from app.models import EducaMantoMusical, EducaMantoQuote
    from app.orcamento import settings as orc_settings

    app = create_app()
    with app.app_context():
        # ── Bloco 1: migração ─────────────────────────────────────────────
        print("1. Migração")
        musicais = EducaMantoMusical.query.order_by(EducaMantoMusical.id).all()
        ids = {m.id for m in musicais}
        check(len(musicais) == 7, f"7 musicais (encontrados: {len(musicais)})")
        check(ids == {1, 11, 15, 18, 23, 26, 29}, f"ids Master preservados ({sorted(ids)})")
        check(all(" - Master" not in m.name for m in musicais), "nomes sem ' - Master'")
        check(all("Cópia" not in m.name for m in musicais), "sem cópia órfã")
        proibidos = {"Som", "Catering apresentação", "Catering ensaio",
                     "Ajuda de custo ensaio", "Transporte"}
        sobras = [i.name for m in musicais for i in m.items if i.name in proibidos]
        check(not sobras, f"itens absorvidos removidos (sobras: {sobras})")

        uaa = EducaMantoMusical.query.get(1)
        check(uaa is not None and uaa.name == "Uma Aventura Animal", "id 1 = Uma Aventura Animal")
        from app.orcamento import settings as _orc
        tabela_caso = _orc.load()["educamanto_som_luz"]
        check(tabela_caso == {"som_luz": 4200, "som": 2900, "luz": 2900, "nenhum": 750},
              f"tabela única de som/luz por caso (3ª rodada) = {tabela_caso}")
        check((uaa.custo_alimentacao_1s, uaa.custo_alimentacao_2s) == (55, 73),
              "alimentação 55/73 por pessoa")
        check((uaa.custo_catering_ensaio_pp, uaa.custo_ajuda_ensaio_pp) == (28, 50),
              "custos de ensaio 28/50 por pessoa")
        # 4ª rodada — regra do dono: personagens = Cara Limpa + Bonecos (+ Papai Noel);
        # produção = item "Produção". Gabarito independente, derivado dos pacotes Master.
        equipe_esperada = {
            "Uma Aventura Animal": (9, 2), "Jardim Mágico": (8, 2),
            "Onda de Mudança": (7, 2), "Unicórnios": (5, 1),
            "Turma do Mantinho": (8, 2), "Natal": (6, 2),
            "Natal com Papai Noel": (7, 2),
        }
        for m in musicais:
            esp = equipe_esperada.get(m.name)
            check(esp == (m.num_personagens, m.num_producao),
                  f"{m.name}: {m.num_personagens} personagens + {m.num_producao} produção"
                  f" (esperado {esp})")
        check(not hasattr(uaa, "custo_cenario_1s"),
              "colunas custo_cenario_* removidas (4ª rodada)")
        check(pdf_textos.RESPONSABILIDADES_ORDEM == ("som", "iluminacao", "alimentacao")
              and "cenario" not in pdf_textos.RESPONSABILIDADES,
              "cenário fora das responsabilidades (textos e ordem)")
        check(all(m.num_ensaios == 2 for m in musicais), "num_ensaios=2 em todos")
        check(all(m.discount_days == 3 for m in musicais), "discount_days=3 em todos")

        # ── Bloco 2: matriz técnica e responsabilidades ───────────────────
        print("2. Matriz técnica (4 casos, UAA 1 dia/1 sessão)")
        esperado = {
            (True, True): (3, 14), (True, False): (2, 13),
            (False, True): (2, 13), (False, False): (1, 12),
        }
        resultados = {}
        for (som, ilum), (n_tec, hc) in esperado.items():
            resp = Responsabilidades(som=som, iluminacao=ilum)
            r = pricing_ops.calcular_configuracao(
                uaa, 1, 0, 0, resp, 0.0, False, 0.0
            )
            resultados[(som, ilum)] = r
            check(len(r.tecnicos) == n_tec and r.headcount_evento == hc,
                  f"som={'M' if som else 'C'}/ilum={'M' if ilum else 'C'} → "
                  f"{len(r.tecnicos)} técnicos, headcount {r.headcount_evento} (esp. {n_tec}/{hc})")
        full = resultados[(True, True)]
        sem_ilum = resultados[(True, False)]
        check(full.valor_final_sem_nota >= sem_ilum.valor_final_sem_nota,
              "tirar iluminação nunca aumenta o valor")

        # Paridade numérica re-derivada das linhas cruas (cenário 1 dia/1 sessão, tudo Manto).
        print("   Paridade numérica (re-derivação independente)")
        cfg_t = orc_settings.load()["transporte"]
        itens = sum(i.qty * i.cost_1s for i in uaa.items)
        hc_ens = uaa.num_personagens + uaa.num_producao
        hc_ev = hc_ens + 3
        # 3ª rodada: som/luz é UMA parcela pelo caso (técnicos inclusos), da tabela única.
        soma = (
            itens + orc_settings.load()["educamanto_som_luz"]["som_luz"]
            + hc_ev * uaa.custo_alimentacao_1s
            + cfg_t["caminhao_sp"]
            + (uaa.custo_catering_ensaio_pp + uaa.custo_ajuda_ensaio_pp) * hc_ens * uaa.num_ensaios
        )
        esperado_sem = math.ceil(soma * uaa.margin_1s / 100) * 100
        esperado_com = math.ceil(soma * uaa.margin_1s / 0.84 / 100) * 100
        check(full.valor_final_sem_nota == esperado_sem,
              f"sem NF {full.valor_final_sem_nota} == re-derivado {esperado_sem}")
        check(full.valor_final_com_nota == esperado_com,
              f"com NF {full.valor_final_com_nota} == re-derivado {esperado_com}")
        check(full.a_vista_sem_nota == round(esperado_sem * 0.95, 2), "à vista = 95% do sem NF")

        # ── Bloco 5: transporte ───────────────────────────────────────────
        print("5. Transporte")
        dentro = full.transporte
        check(dentro.modo == "caminhao_sp" and dentro.total == 0
              and dentro.caminhao == cfg_t["caminhao_sp"],
              f"dentro de SP: caminhão R$ {cfg_t['caminhao_sp']} na base, nada no líquido")
        fora = pricing_ops.calcular_configuracao(
            uaa, 1, 1, 0, Responsabilidades(), 0.0, True, 100.0
        )
        km_total = 200.0
        viagem = round(
            round(km_total * (cfg_t["van_com_carretinha"] + cfg_t["van_sem_carretinha"]), 2)
            + round(fora.headcount_evento * km_total / cfg_t["afsp_divisor"], 2), 2
        )
        check(fora.transporte.total == round(viagem * 2, 2),
              f"fora de SP: 2 vans, {viagem}/viagem × 2 dias = {fora.transporte.total}")
        sem_caminhao = [r for r in fora.item_rows if "Caminhão" in r["name"]]
        check(not sem_caminhao, "fora de SP: caminhão fora da base")

        # ── Bloco 6: contratação Manto embutida ───────────────────────────
        print("6. Contratação Manto embutida")
        from app.orcamento.quote_ops import calculate_quote

        performer = {"type": "ator", "subtipo": "cara_limpa", "nome": "", "show": False}
        entrada6 = quote_ops.parse_config_input({
            "musical_id": 1, "d1": 1, "d2": 0, "ensemble": 0,
            "responsabilidades": {}, "fora_sp": False, "acrescimo": 0,
            "contratacao_manto": {
                "duracoes": ["1h", "2h"],
                "payload": {"performers": [performer], "coordenador_qty": 1},
            },
        })
        _, r6, snap6 = quote_ops.calcular_config(entrada6)
        manto = calculate_quote({
            "performers": [performer], "coordenador_qty": 1,
            "nota_fiscal": False, "fora_sp": False,
        })["quote"]
        check(snap6.get("totais", {}).get("1h") == manto["total_1h"],
              "parte Manto = calculate_quote sem NF (fonte única)")
        liq = full.liquido  # mesma config base (tudo Manto, 1d/1s, sem extras)
        for dur in ("1h", "2h"):
            esp_sem = math.ceil((liq + manto[f"total_{dur}"]) / 100) * 100
            esp_com = math.ceil((liq + manto[f"total_{dur}"]) / 0.84 / 100) * 100
            comb = r6.combinados[dur]
            check(comb["sem_nota"] == esp_sem and comb["com_nota"] == esp_com,
                  f"combinado {dur}: {comb['sem_nota']}/{comb['com_nota']} — NF única sobre a soma")
        entrada6b = {
            "configs": [{
                "musical_id": 1, "d1": 1, "d2": 0, "ensemble": 0,
                "responsabilidades": {}, "fora_sp": False, "acrescimo": 0,
                "contratacao_manto": {
                    "duracoes": ["1h"],
                    "payload": {"performers": [performer], "coordenador_qty": 1},
                },
            }],
            "client_name": "TESTE-VERIFY-235-CONTRATACAO",
        }
        _, snapc = quote_ops.generate_quote(1, entrada6b)
        pdf_c = gerar_orcamento_pdf(snapc)
        check(snapc["configs"][0]["contratacao_manto"] is not None
              and pdf_c.startswith(b"%PDF") and len(pdf_c) > 1500,
              f"snapshot v2 com contratação + PDF gera ({len(pdf_c)} bytes)")

        # ── Bloco 7: RBAC (corte no servidor) ─────────────────────────────
        print("7. Corte de breakdown (função da API)")
        from app.api.educamanto_read import _cortar_breakdown
        cortado = _cortar_breakdown(full.to_dict())
        check("breakdown" not in cortado, "resposta cortada sem 'breakdown'")
        check("caminhao" not in (cortado.get("transporte") or {}),
              "custo do caminhão fora da resposta cortada")
        check(cortado.get("valor_final_sem_nota") == full.valor_final_sem_nota
              and cortado.get("acrescimo_maximo") == full.acrescimo_maximo,
              "valores finais e aviso de teto preservados")

        # ── Bloco 8: retrocompatibilidade e snapshot v2 ───────────────────
        print("8. Histórico")
        antigo = (
            EducaMantoQuote.query.filter(EducaMantoQuote.snapshot.isnot(None))
            .order_by(EducaMantoQuote.id).first()
        )
        if antigo is not None:
            snap_v1 = quote_ops.load_quote_snapshot(antigo)
            check("version" not in snap_v1, "snapshot antigo detectado como v1")
            pdf_v1 = gerar_orcamento_pdf(snap_v1)
            check(pdf_v1.startswith(b"%PDF") and len(pdf_v1) > 1500,
                  f"PDF v1 re-renderiza ({len(pdf_v1)} bytes)")
        else:
            print("  [aviso] espelho sem orçamentos antigos — pulei o re-render v1")

        entrada = {
            "configs": [{
                "musical_id": 1, "d1": 1, "d2": 0, "ensemble": 1,
                "responsabilidades": {"som": "manto", "iluminacao": "contratante"},
                "fora_sp": False, "acrescimo": 300.0,
            }],
            "client_name": "TESTE-VERIFY-235",
            "observacao": "Linha 1\nLinha 2 de observação de teste.",
        }
        quote, snapshot = quote_ops.generate_quote(0 or 1, entrada)
        check(snapshot.get("version") == 2, "snapshot novo é v2")
        rc = snapshot["configs"][0]["resultado"]
        recalc = pricing_ops.calcular_configuracao(
            uaa, 1, 0, 1, Responsabilidades(som=True, iluminacao=False), 300.0, False, 0.0
        )
        check(rc["sem_nota"] == recalc.valor_final_sem_nota,
              "valor congelado = recalculado no servidor")
        pdf_v2 = gerar_orcamento_pdf(snapshot)
        check(pdf_v2.startswith(b"%PDF") and len(pdf_v2) > 1500,
              f"PDF v2 gera ({len(pdf_v2)} bytes)")

    print()
    if FALHAS:
        print(f"FALHOU: {len(FALHAS)} checagem(ns):")
        for f in FALHAS:
            print(f"  - {f}")
        return 1
    print("VERIFY 235: tudo passou.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
