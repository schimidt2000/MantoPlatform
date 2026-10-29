"""Verificação da 309b — a Visita Mágica no orçamento diz o que se entrega: até 30 minutos + o que inclui.

Só leitura: a tabela de preços do `manto_local` NÃO é gravada. O cenário da tabela salva antes da 309b
roda `_migrate` sobre uma cópia em memória; os cenários de mensagem e PDF usam `settings.load` dublado
com essa cópia (mesmo caminho que a produção percorre no `load()`). Nada de Google, e-mail ou HTTP.

Rodar contra o manto_local (PowerShell, na raiz do repo)::

    $env:DATABASE_URL = (gc .local-db-url -Raw).Trim(); $env:FLASK_ENV = "development"
    $env:MANTO_SEM_THREADS = "1"; $env:PYTHONUTF8 = "1"
    .venv\\Scripts\\python.exe specs\\309b-visita-magica-30-minutos\\verify_309b.py

O cenário 4 DEVE falhar no código de antes (a mensagem dizia "visita padrão, até 1h").
"""

from __future__ import annotations

import copy
import io
import json
import os
import sys
import traceback
from collections.abc import Callable
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))
os.environ.setdefault("FLASK_ENV", "development")
os.environ.setdefault("MANTO_SEM_THREADS", "1")
if not os.environ.get("DATABASE_URL"):
    os.environ["DATABASE_URL"] = (REPO_ROOT / ".local-db-url").read_text(encoding="utf-8").strip()

from app import create_app  # noqa: E402
from app.orcamento import quote_ops  # noqa: E402
from app.orcamento import settings as _cfg  # noqa: E402

VISITA = "visita_magica"
VISITA_AJ = "visita_magica_ajudante"
DESCRICAO = "visita de até 30 minutos"
DESCRICAO_ANTIGA = "visita padrão, até 1h"
TRECHOS_DA_ARTE = (
    "Chegada mágica",
    "músicas natalinas",
    "até 10 presentes",
    "fornecidos pela contratante",
    "verdadeiro significado do Natal",
)

app = create_app()
resultados: list[tuple[str, str, str]] = []
_load_real = _cfg.load


def cenario(nome: str, fn: Callable[[], None]) -> None:
    try:
        fn()
        resultados.append((nome, "OK", ""))
        print(f"  OK     {nome}")
    except Exception as exc:  # noqa: BLE001 — o verify registra e segue
        resultados.append((nome, "FALHA", traceback.format_exc().strip().splitlines()[-1]))
        print(f"  FALHA  {nome}: {str(exc)[:400]}")


def _garante(cond: bool, msg: str) -> None:
    if not cond:
        raise AssertionError(msg)


def _config_salva_antes_da_309b() -> dict:
    """A tabela real do manto_local com os produtos como a 309 os gravava (sem `detalhes`, "até 1h")."""
    with app.app_context():
        base = copy.deepcopy(_load_real())
    base["produtos"] = {
        VISITA: {
            "rotulo": "Visita Mágica — Papai Noel",
            "descricao": DESCRICAO_ANTIGA,
            "ativo": True,
            "preco": 2500,
            "por_faixa": {"natal": {"preco": 5000}},
            "vagas": [
                {"label": "Papai Noel", "tipo": "especial", "cache": None, "needs_makeup": True},
                {
                    "label": "Coordenador",
                    "tipo": "coordenador",
                    "cache": None,
                    "needs_makeup": False,
                },
                {"label": "Maquiador", "tipo": "maquiador", "cache": None, "needs_makeup": False},
            ],
            "inclui_noturno": True,
        },
        VISITA_AJ: {
            "rotulo": "Visita Mágica — Papai Noel + Ajudante",
            "descricao": DESCRICAO_ANTIGA,
            "ativo": True,
            "preco": 3600,
            "por_faixa": {"natal": {"preco": 6500}},
            "vagas": [
                {"label": "Papai Noel", "tipo": "especial", "cache": None, "needs_makeup": True},
                {
                    "label": "Ajudante do Noel",
                    "tipo": "especial",
                    "cache": None,
                    "needs_makeup": False,
                },
                {
                    "label": "Coordenador",
                    "tipo": "coordenador",
                    "cache": None,
                    "needs_makeup": False,
                },
                {"label": "Maquiador", "tipo": "maquiador", "cache": None, "needs_makeup": False},
            ],
            "inclui_noturno": True,
        },
    }
    # Ida e volta em JSON, como sai da coluna `pricing_config`.
    return json.loads(json.dumps(base, ensure_ascii=False))


CFG_MIGRADA: dict = {}


def _payload(data: str, produtos: list[str], performers: list[dict] | None = None) -> dict:
    return {
        "performers": performers or [],
        "coordenador_qty": 1,
        "event_date": data,
        "event_time": "15:00",
        "client_name": "Cliente 309b",
        "event_location": "Salão 309b",
        "incluir_duracao": ["1h", "2h", "3h", "4h"],
        "modo_duracao": "horas",
        "produtos": [{"chave": c} for c in produtos],
    }


def _calcular(corpo: dict) -> dict:
    _cfg.load = lambda: copy.deepcopy(CFG_MIGRADA)
    try:
        with app.app_context():
            return quote_ops.calculate_quote(corpo)["quote"]
    finally:
        _cfg.load = _load_real


def _texto_do_pdf(quote: dict) -> str:
    from pypdf import PdfReader

    from app.orcamento.pdf import gerar_orcamento_pdf

    with app.app_context():
        pdf = gerar_orcamento_pdf(quote)
    _garante(pdf[:4] == b"%PDF", "PDF não gerado")
    texto = "\n".join(p.extract_text() or "" for p in PdfReader(io.BytesIO(pdf)).pages)
    return " ".join(texto.split())


# ── cenários ────────────────────────────────────────────────────────────────────────────────────
def c1_padroes():
    for chave in (VISITA, VISITA_AJ):
        p = _cfg.DEFAULTS["produtos"][chave]
        _garante(p["descricao"] == DESCRICAO, f"{chave}: descrição padrão {p['descricao']!r}")
        for trecho in TRECHOS_DA_ARTE:
            _garante(trecho in p["detalhes"], f"{chave}: 'o que inclui' sem {trecho!r}")
        _garante(len(p["detalhes"]) <= _cfg.PRODUTO_DETALHES_MAX, "texto padrão passa do limite")
        _garante("1h" not in p["descricao"] + p["detalhes"], f"{chave}: ainda fala em 1h")


def c2_tabela_salva_antes():
    migrada = _cfg._migrate(_config_salva_antes_da_309b())
    # Antes das conferências: os cenários 4–10 usam esta tabela, e no código antigo devem falhar pelo
    # texto, não por tabela vazia.
    CFG_MIGRADA.clear()
    CFG_MIGRADA.update(migrada)
    for chave in (VISITA, VISITA_AJ):
        p = migrada["produtos"][chave]
        _garante(p["descricao"] == DESCRICAO, f"{chave}: descrição migrada {p['descricao']!r}")
        _garante(
            p["detalhes"] == _cfg.DEFAULTS["produtos"][chave]["detalhes"],
            f"{chave}: detalhes {p['detalhes']!r}",
        )
        # O preço e a composição não podem mudar com a correção de texto.
    _garante(migrada["produtos"][VISITA]["preco"] == 2500, "preço da visita mudou")
    _garante(
        migrada["produtos"][VISITA_AJ]["por_faixa"] == {"natal": {"preco": 6500}},
        "preço do Natal mudou",
    )


def c3_edicao_do_time_preservada():
    cfg = _config_salva_antes_da_309b()
    cfg["produtos"][VISITA]["descricao"] = "visita expressa"
    cfg["produtos"][VISITA]["detalhes"] = ""
    cfg["produtos"][VISITA_AJ]["detalhes"] = "Texto do time."
    extra = copy.deepcopy(cfg["produtos"][VISITA])
    extra["descricao"] = DESCRICAO_ANTIGA
    extra.pop("detalhes")
    cfg["produtos"]["visita_duende"] = extra
    migrada = _cfg._migrate(cfg)["produtos"]
    _garante(
        migrada[VISITA]["descricao"] == "visita expressa", "descrição editada pelo time foi trocada"
    )
    _garante(
        migrada[VISITA]["detalhes"] == "", "'o que inclui' esvaziado pelo time voltou ao padrão"
    )
    _garante(migrada[VISITA_AJ]["detalhes"] == "Texto do time.", "texto do time sobrescrito")
    _garante(
        migrada["visita_duende"]["descricao"] == DESCRICAO_ANTIGA,
        "produto criado pelo time foi mexido",
    )
    _garante(migrada["visita_duende"]["detalhes"] == "", "produto do time ganhou o texto da Visita")


def c4_mensagem_so_produto():
    q = _calcular(_payload("2026-12-10", [VISITA]))
    msg = q["message"]
    _garante("até 1h" not in msg and "1 hora" not in msg, "mensagem ainda fala em 1 hora")
    linha = "🎅 *Visita Mágica — Papai Noel* (visita de até 30 minutos): *R$ 2.500,00*"
    _garante(linha in msg, "linha do produto não diz 30 minutos")
    seguinte = msg.split(linha, 1)[1].split("\n")[1]
    _garante(
        seguinte.startswith("_Chegada mágica") and seguinte.endswith("_"),
        f"logo abaixo do preço: {seguinte!r}",
    )
    for trecho in TRECHOS_DA_ARTE:
        _garante(trecho in seguinte, f"'o que inclui' sem {trecho!r}")
    _garante(
        q["produtos"][0]["detalhes"].startswith("Chegada mágica"), "quote.produtos sem detalhes"
    )


def c5_natal_com_ajudante():
    q = _calcular(_payload("2026-12-24", [VISITA_AJ]))
    msg = q["message"]
    _garante(
        "🎅 *Visita Mágica — Papai Noel + Ajudante* (visita de até 30 minutos): *R$ 6.500,00*"
        in msg,
        "Natal com ajudante: linha errada",
    )
    _garante("_Chegada mágica" in msg, "Natal com ajudante: sem 'o que inclui'")


def c6_dois_exemplares_um_paragrafo():
    q = _calcular(_payload("2026-12-10", [VISITA, VISITA]))
    _garante(q["message"].count("_Chegada mágica") == 1, "parágrafo repetido para dois exemplares")
    _garante(
        q["message"].count("(visita de até 30 minutos)") == 2,
        "as duas linhas de produto devem sair",
    )


def c7_produto_com_avulso():
    q = _calcular(_payload("2026-12-10", [VISITA], [{"type": "ator", "subtipo": "boneco"}]))
    msg = q["message"]
    _garante("_Chegada mágica" in msg, "com avulso: sem 'o que inclui'")
    _garante(
        msg.index("_Chegada mágica") < msg.index("🕐 *1 hora*"),
        "'o que inclui' deve vir antes das durações",
    )


def c8_pdf():
    q = _calcular(_payload("2026-12-10", [VISITA]))
    texto = _texto_do_pdf(q)
    _garante("visita de até 30 minutos" in texto, "PDF não diz 30 minutos")
    _garante("até 1h" not in texto, "PDF ainda fala em 1h")
    for trecho in TRECHOS_DA_ARTE:
        _garante(trecho in texto, f"PDF sem {trecho!r}")


def c9_orcamento_antigo_sem_detalhes():
    q = _calcular(_payload("2026-12-10", [VISITA]))
    for p in q["produtos"]:
        p.pop("detalhes")
        p["descricao"] = DESCRICAO_ANTIGA
    texto = _texto_do_pdf(q)
    _garante("Chegada mágica" not in texto, "orçamento antigo ganhou texto que não tinha")


def c10_validacao_da_tela():
    with app.app_context():
        cfg = _cfg.load()
    bloco = copy.deepcopy(CFG_MIGRADA["produtos"])
    bloco[VISITA]["detalhes"] = "Linha 1\nLinha   2"
    limpo, _est, _av = _cfg.validar_produtos(bloco, None, cfg["especiais"], cfg["datas_especiais"])
    _garante(
        limpo[VISITA]["detalhes"] == "Linha 1 Linha 2",
        f"quebra de linha não virou espaço: {limpo[VISITA]['detalhes']!r}",
    )
    _garante(
        limpo[VISITA_AJ]["detalhes"] == CFG_MIGRADA["produtos"][VISITA_AJ]["detalhes"],
        "detalhes perdido no salvar",
    )
    bloco[VISITA]["detalhes"] = "x" * (_cfg.PRODUTO_DETALHES_MAX + 1)
    try:
        _cfg.validar_produtos(bloco, None, cfg["especiais"], cfg["datas_especiais"])
    except _cfg.SettingsValidationError as exc:
        _garante(f"produtos.{VISITA}.detalhes" in exc.fields, f"erro sem o campo: {exc.fields}")
    else:
        raise AssertionError("texto acima do limite foi aceito")


if __name__ == "__main__":
    print("verify 309b — Visita Mágica: 30 minutos + o que inclui")
    for nome, fn in [
        ("1. padrões do código dizem 30 minutos e trazem o texto da arte", c1_padroes),
        (
            "2. tabela salva antes da 309b é corrigida ao carregar (preço intacto)",
            c2_tabela_salva_antes,
        ),
        ("3. edição do time e produto do time não são tocados", c3_edicao_do_time_preservada),
        (
            "4. mensagem só com a Visita: 30 minutos + o que inclui logo abaixo",
            c4_mensagem_so_produto,
        ),
        ("5. 24/12 com ajudante: preço do Natal e o mesmo texto", c5_natal_com_ajudante),
        ("6. dois exemplares: o parágrafo sai uma vez", c6_dois_exemplares_um_paragrafo),
        ("7. Visita + avulso: texto antes das durações", c7_produto_com_avulso),
        ("8. PDF diz 30 minutos e traz o que inclui", c8_pdf),
        (
            "9. orçamento salvo antes (sem detalhes) gera PDF como era",
            c9_orcamento_antigo_sem_detalhes,
        ),
        (
            "10. tela de preços: salva o texto numa linha e recusa acima do limite",
            c10_validacao_da_tela,
        ),
    ]:
        cenario(nome, fn)
    ok = sum(1 for _n, s, _d in resultados if s == "OK")
    print(f"\n{ok}/{len(resultados)} OK")
    sys.exit(0 if ok == len(resultados) else 1)
