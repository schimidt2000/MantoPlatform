"""Verificação da feature 307 — Papai Noel em data especial na Calculadora de Orçamento.

Cenários 1–18 da `spec.md` (seção "Verificação"). Escrito ANTES do núcleo (Princípio VIII): a
primeira rodada fica em `verify_307_primeira_falha.txt`.

A configuração de preços REAL do `manto_local` é lida por conexão separada no início, substituída por
uma configuração de teste determinística (markup receptivo 2,6 e show 2,8; coordenador 250/300;
"Papai Noel" em [600, 650, 675, 700] (o cachê de verdade — a 309 desfez a engenharia reversa 712 da
307), sem "Ajudante do Noel" e sem `datas_especiais` — para provar a migração) e RESTAURADA no `finally`, conferida por conexão separada. Premissas lidas do espelho em
15/10/2026 (T001): markup receptivo = show = [2.6, 2.5, 2.45, 2.4]; coordenador false
[250, 300, 325, 350]; especiais."Papai Noel" = [600, 650, 675, 700]; especiais_excluidos =
["Ajudante Especial"]. Se o espelho vier diferente (ex.: um "Salvar configurações" da conferência de
tela persistiu a tabela migrada), o `preparar()` avisa — e o cenário 12 prova a migração do mesmo jeito.

Requisições correm FORA do `app.app_context()`; login só por `POST /api/auth/login` com usuários
descartáveis (prefixo `__v307_`), cookie do próprio test_client; limpeza no `finally`.

Rodar contra o manto_local (PowerShell)::

    $env:DATABASE_URL = (gc .local-db-url -Raw).Trim(); $env:FLASK_ENV = "development"
    $env:MANTO_SEM_THREADS = "1"; $env:PYTHONUTF8 = "1"
    .\\.venv\\Scripts\\python.exe specs\\307-natal-papai-noel-calculadora\\verify_307.py --regressao [--so=3,4]

Sem `--regressao` o cenário 17 (`verify_305.py --regressao`, em subprocesso — demora) sai como
PULADO e fica FORA da contagem: o portão da feature é a rodada com a flag.
"""

from __future__ import annotations

import copy
import io
import json
import os
import subprocess
import sys
import traceback
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))
os.environ.setdefault("FLASK_ENV", "development")
os.environ.setdefault("MANTO_SEM_THREADS", "1")
if not os.environ.get("DATABASE_URL"):
    os.environ["DATABASE_URL"] = (REPO_ROOT / ".local-db-url").read_text(encoding="utf-8").strip()

from sqlalchemy import create_engine, text  # noqa: E402

from app import create_app, db, limiter  # noqa: E402
from app.constants import RoleName  # noqa: E402
from app.models import OrcamentoHistory, Role, User  # noqa: E402
from app.orcamento import quote_ops  # noqa: E402
from app.orcamento import settings as _cfg  # noqa: E402

PREFIX = "__v307_"
SENHA = "verify-307-senha"
ROTULO = "Véspera e Natal"
NOTA = "Valores especiais de 24 e 25 de dezembro."
NOEL_ANTIGO = [600, 650, 675, 700]
MARCA_CACHE = "cachê da data especial"
MARCA_PISO = "piso da data especial"
ESPECIAL_DESCARTAVEL = f"{PREFIX}Especial"

app = create_app()
app.config["TESTING"] = True
limiter.enabled = False

resultados: list[tuple[str, str, str]] = []  # (nome, "OK" | "FALHA" | "PULADO", detalhe)
estado: dict = {}
_externo = create_engine(os.environ["DATABASE_URL"], future=True)


class Pulado(Exception):
    """Cenário que não rodou de propósito (fora da contagem — nunca conta como OK)."""


# ── utilidades ──────────────────────────────────────────────────────────────────────────────────
def _no_banco(sql: str, **params):
    with _externo.connect() as conn:
        return conn.execute(text(sql), params).fetchall()


def cenario(nome: str, fn: Callable[[], None]) -> None:
    try:
        fn()
        resultados.append((nome, "OK", ""))
        print(f"  OK     {nome}")
    except Pulado as motivo:
        resultados.append((nome, "PULADO", str(motivo)))
        print(f"  PULADO {nome}: {motivo}")
    except Exception as exc:  # noqa: BLE001 — o verify registra e segue
        with app.app_context():
            db.session.rollback()
        ultima = traceback.format_exc().strip().splitlines()[-1]
        resultados.append((nome, "FALHA", ultima))
        print(f"  FALHA  {nome}: {str(exc)[:400]}")


def _garante(cond: bool, msg: str) -> None:
    if not cond:
        raise AssertionError(msg)


def _iguais(a: float, b: float, msg: str, tol: float = 0.011) -> None:
    _garante(abs(float(a) - float(b)) <= tol, f"{msg}: {a} ≠ {b}")


def _cliente(papel: str):
    c = app.test_client()
    r = c.post("/api/auth/login", json={"email": estado[papel]["email"], "password": SENHA})
    _garante(r.status_code == 200, f"login {papel} → {r.status_code}")
    return c


def _erro(r) -> dict:
    corpo = r.get_json(silent=True) or {}
    return corpo.get("error") or {}


# ── configuração de preços: real × de teste ─────────────────────────────────────────────────────
def _config_real() -> str | None:
    rows = _no_banco("SELECT pricing_config FROM site_settings WHERE id = 1")
    return rows[0][0] if rows else None


def _gravar_config(cfg: dict) -> None:
    with _externo.begin() as conn:
        conn.execute(
            text("UPDATE site_settings SET pricing_config = :j WHERE id = 1"),
            {"j": json.dumps(cfg, ensure_ascii=False)},
        )


def _config_de_teste(real: str | None) -> dict:
    """A tabela real com os números do espelho fixados — e o Noel no cachê ANTIGO (prova a migração).

    `markup.show` e `coordenador.true` DIFERENTES dos normais: é assim que o cenário de show prova
    que a faixa substitui também o markup de show e usa a lista única de coordenador.
    """
    cfg = json.loads(real) if real else copy.deepcopy(_cfg.DEFAULTS)
    cfg["markup"] = {"receptivo": [2.6, 2.5, 2.45, 2.4], "show": [2.8, 2.6, 2.5, 2.4]}
    cfg["coordenador"] = {"false": [250, 300, 325, 350], "true": [300, 350, 375, 400]}
    cfg.setdefault("ator", {})["boneco|false|false"] = [200, 250, 275, 300]
    cfg["tecnico_som"] = [750, 800, 825, 850]
    cfg["brinde_show"] = 100
    esp = cfg.setdefault("especiais", {})
    esp["Papai Noel"] = list(NOEL_ANTIGO)
    esp.pop("Ajudante do Noel", None)
    esp.pop(ESPECIAL_DESCARTAVEL, None)
    esp["Perna de Pau"] = [400, 450, 475, 500]
    esp["Homem-Aranha"] = {"false": [250, 300, 325, 350], "true": [400, 450, 475, 500]}
    cfg["especiais_excluidos"] = ["Ajudante Especial"]
    cfg.pop("datas_especiais", None)
    return cfg


# ── fixtures ────────────────────────────────────────────────────────────────────────────────────
def _usuario(apelido: str, papel: str) -> dict:
    email = f"{PREFIX}{apelido}@manto.local"
    u = User(name=f"{PREFIX}{apelido}", email=email, is_active=True, has_access=True)
    u.set_password(SENHA)
    u.roles.append(Role.query.filter_by(name=papel).one())
    db.session.add(u)
    db.session.flush()
    return {"id": u.id, "email": email}


def preparar() -> None:
    estado["config_real"] = _config_real()
    try:
        noel_real = json.loads(estado["config_real"] or "{}").get("especiais", {}).get("Papai Noel")
    except json.JSONDecodeError:
        noel_real = None
    if noel_real != [float(v) for v in NOEL_ANTIGO] and noel_real != NOEL_ANTIGO:
        print(
            f"  AVISO  o espelho não tem o Papai Noel antigo ({noel_real}); recarregue o dump da produção"
        )
    _gravar_config(_config_de_teste(estado["config_real"]))
    with app.app_context():
        limpar()
        for apelido, papel in (("sa", RoleName.SUPERADMIN), ("com", RoleName.COMERCIAL)):
            estado[apelido] = _usuario(apelido, papel)
        db.session.commit()


def limpar() -> None:
    db.session.execute(
        text("DELETE FROM orcamento_history WHERE client_name LIKE :p"), {"p": f"{PREFIX}%"}
    )
    db.session.execute(
        text("DELETE FROM audit_logs WHERE entity_name LIKE :p"), {"p": f"%{PREFIX}%"}
    )
    db.session.commit()
    for u in User.query.filter(User.email.like(f"{PREFIX}%")).all():
        u.roles.clear()
        db.session.delete(u)
    db.session.commit()


NOEL = {"type": "especial", "personagem": "Papai Noel"}
AJUDANTE = {"type": "especial", "personagem": "Ajudante do Noel"}
BONECO = {"type": "ator", "subtipo": "boneco"}
PERNA_DE_PAU = {"type": "especial", "personagem": "Perna de Pau"}
ARANHA_SHOW = {"type": "especial", "personagem": "Homem-Aranha", "show": True}
ESPECIAL_VAZIO = {"type": "especial"}


def _payload(data: str, performers: list[dict], hora: str = "", **extra) -> dict:
    corpo = {
        "performers": performers,
        "coordenador_qty": 1,
        "event_date": data,
        "event_time": hora,
        "client_name": f"{PREFIX}Cliente",
        "event_location": f"{PREFIX}Salão de festas",
        "incluir_duracao": ["1h", "2h", "3h", "4h"],
        "modo_duracao": "horas",
    }
    corpo.update(extra)
    return corpo


def _calcular(corpo: dict, papel: str = "com") -> dict:
    r = _cliente(papel).post("/api/orcamento/calcular", json=corpo)
    _garante(r.status_code == 200, f"calcular → {r.status_code} {r.get_data(as_text=True)[:200]}")
    return r.get_json()


def _linha(memoria: list[dict], tipo: str, trecho: str = "") -> dict:
    for linha in memoria:
        if linha["tipo"] == tipo and trecho in linha["label"]:
            return linha
    raise AssertionError(f"memória sem linha {tipo!r} contendo {trecho!r}")


def _texto_do_pdf(quote: dict) -> str:
    from pypdf import PdfReader

    from app.orcamento.pdf import gerar_orcamento_pdf

    with app.app_context():
        pdf = gerar_orcamento_pdf(quote)
    _garante(pdf[:4] == b"%PDF", "PDF não gerado")
    return "\n".join(p.extract_text() or "" for p in PdfReader(io.BytesIO(pdf)).pages)


# ── 1–2 · tabela normal ─────────────────────────────────────────────────────────────────────────
def cen_01_noel_20_12() -> None:
    res = _calcular(_payload("2026-12-20", [NOEL]))
    q = res["quote"]
    _iguais(q["total_1h"], 2210.00, "Noel 20/12 1h (600 + 250) × 2,6 — feature 309")
    _iguais(q["markup_used"][0], 2.6, "markup normal")
    _garante(
        q.get("data_especial") is None, f"data_especial devia ser None: {q.get('data_especial')}"
    )
    _garante(NOTA not in q["message"], "mensagem de 20/12 não leva a nota de Natal")


def cen_02_noel_mais_ajudante_20_12() -> None:
    res = _calcular(_payload("2026-12-20", [NOEL, AJUDANTE]))
    _iguais(
        res["quote"]["total_1h"],
        2912.00,
        "Noel + Ajudante 20/12 1h (600 + 270 + 250) × 2,6 — feature 309",
    )


# ── 3–9 · a faixa ───────────────────────────────────────────────────────────────────────────────
def cen_03_noel_24_12() -> None:
    res = _calcular(_payload("2026-12-24", [NOEL]))
    q = res["quote"]
    _iguais(q["total_1h"], 5010.00, "Noel 24/12 1h")
    _garante(
        (q.get("data_especial") or {}).get("rotulo") == ROTULO,
        f"data_especial: {q.get('data_especial')}",
    )
    _garante(
        q["data_especial"].get("nota_mensagem") == NOTA,
        "data_especial leva a nota (PDF e congelado)",
    )
    _iguais(q["markup_used"][0], 3.34, "markup da faixa em markup_used")
    markup = _linha(q["memoria"], "markup", "Markup")
    _garante(markup["detalhe"] == f"{ROTULO} · 24/12", f"detalhe do markup: {markup['detalhe']!r}")
    _iguais(markup["valores"][0], 3.34, "linha do markup na memória")
    noel = _linha(q["memoria"], "cache", "Papai Noel")
    _iguais(noel["valores"][0], 1000, "cachê do Noel na faixa")
    _garante(MARCA_CACHE in noel["detalhe"], f"detalhe do cachê: {noel['detalhe']!r}")
    _garante(f"_{NOTA}_" in q["message"], "mensagem sem a nota da data")
    _garante("R$ 4.759,50" in q["message"], "PIX à vista (−5%) continua: 5.010 × 0,95")
    _garante(NOTA in _texto_do_pdf(q), "PDF sem a nota da data")


def cen_04_noel_mais_ajudante_25_12() -> None:
    res = _calcular(_payload("2026-12-25", [NOEL, AJUDANTE]))
    _iguais(res["quote"]["total_1h"], 7181.00, "Noel + Ajudante 25/12 1h")


def cen_05_noturno_segue_por_fora() -> None:
    res = _calcular(_payload("2026-12-24", [NOEL], hora="20:00"))
    _iguais(res["quote"]["total_1h"], 5110.00, "Noel 24/12 às 20h")
    _linha(res["quote"]["memoria"], "pos", "noturno")


def cen_06_boneco_pelo_piso_e_linha_vazia() -> None:
    res = _calcular(_payload("2026-12-24", [NOEL, BONECO]))
    q = res["quote"]
    _iguais(q["total_1h"], 7181.00, "Noel + boneco 24/12 = Noel + Ajudante")
    boneco = _linha(q["memoria"], "cache", "Boneco")
    _iguais(boneco["valores"][0], 650, "boneco elevado ao piso")
    _garante(MARCA_PISO in boneco["detalhe"], f"detalhe do boneco: {boneco['detalhe']!r}")
    # Linha de especial ainda sem personagem continua custando zero — não sobe ao piso.
    res = _calcular(_payload("2026-12-24", [NOEL, ESPECIAL_VAZIO]))
    _iguais(res["quote"]["total_1h"], 5010.00, "especial vazio não entra no piso")


def cen_07_qualquer_produto_na_data_e_show() -> None:
    res = _calcular(_payload("2026-12-24", [PERNA_DE_PAU]))
    q = res["quote"]
    _iguais(q["markup_used"][0], 3.34, "markup da faixa vale para Perna de Pau")
    _iguais(
        _linha(q["memoria"], "cache", "Perna de Pau")["valores"][0],
        650,
        "max(tabela 400, piso 650)",
    )
    _iguais(q["total_1h"], 3841.00, "Perna de Pau 24/12 1h")
    # Show na faixa: markup da faixa (não o de show, 2,8) e coordenador da faixa (não o "true", 300);
    # brinde e técnico × 1,5 seguem por fora. (650 + 500) × 3,34 + 100 + 750 × 1,5 = 5.066,00.
    res = _calcular(_payload("2026-12-24", [ARANHA_SHOW]))
    q = res["quote"]
    _iguais(q["markup_used"][0], 3.34, "show na faixa usa o markup da faixa")
    _iguais(
        _linha(q["memoria"], "cache", "Coordenador")["valores"][0],
        500,
        "coordenador da faixa com show",
    )
    _linha(q["memoria"], "pos", "Técnico de som")
    _linha(q["memoria"], "pos", "Brinde")
    _iguais(q["total_1h"], 5066.00, "Homem-Aranha show 24/12 1h")


def cen_08_hora_extra_e_dois_coordenadores() -> None:
    res = _calcular(_payload("2026-12-24", [NOEL]))
    _iguais(res["quote"]["total_2h"], 10020.00, "2h = 2 × 1h na faixa")
    res = _calcular(_payload("2026-12-24", [NOEL], coordenador_qty=2))
    q = res["quote"]
    _iguais(
        _linha(q["memoria"], "cache", "Coordenador")["valores"][0], 1000, "2 coordenadores × 500"
    )
    _iguais(q["total_1h"], 6680.00, "Noel + 2 coordenadores 24/12 1h")
    res = _calcular(_payload("2026-12-24", [NOEL], duracao_custom=6))
    _iguais(res["quote"]["total_custom"], 30060.00, "6h = total_4h ÷ 4 × 6 (régua 236) na faixa")


def cen_09_transporte_personalizado_bv() -> None:
    from app.orcamento.transport import calcular_van

    res = _calcular(
        _payload(
            "2026-12-24",
            [NOEL],
            fora_sp=True,
            deslocamento_responsavel="manto",
            transporte_tipo="van",
            km_ida=50,
            carretinha=False,
        )
    )
    with app.app_context():
        tb = calcular_van(2, 50.0, False, False)
    _iguais(
        res["quote"]["total_1h"],
        round(5010.00 + tb["total"], 2),
        "fora de SP soma por cima da faixa",
    )

    res = _calcular(
        _payload(
            "2026-12-24",
            [NOEL],
            personalizado=True,
            personalizado_criterio="valor_final",
            cust_valor_1h="4000",
            cust_valor_2h="4000",
            cust_valor_3h="4000",
            cust_valor_4h="4000",
        )
    )
    _iguais(res["quote"]["total_1h"], 4000.00, "personalizado vence")
    _garante(
        res["quote"].get("data_especial") is not None, "data_especial informativo no personalizado"
    )
    # Multiplicador: a base é o cachê da faixa (coerente com o teto da vaga) — 1.500 × 2 = 3.000.
    res = _calcular(
        _payload(
            "2026-12-24",
            [NOEL],
            personalizado=True,
            personalizado_criterio="multiplicador",
            cust_mult_1h="2",
            cust_mult_2h="2",
            cust_mult_3h="2",
            cust_mult_4h="2",
        )
    )
    _iguais(res["quote"]["total_1h"], 3000.00, "multiplicador sobre o cachê da faixa")

    res = _calcular(
        _payload("2026-12-24", [NOEL], acrescimos=[{"tipo": "BV", "value": 10, "is_percent": True}])
    )
    _iguais(res["quote"]["total_1h"], 5511.00, "BV 10% sobre o total da faixa")
    _iguais(res["snapshot"]["acrescimos"][0]["valores_brl"][0], 501.00, "valores_brl do BV (305)")


# ── 10 · EducaManto ─────────────────────────────────────────────────────────────────────────────
def cen_10_educamanto_neutro() -> None:
    from app.educamanto.quote_ops import _totais_contratacao

    # Primeiro prova que a faixa ESTÁ ativa no cálculo direto — senão "neutro" não testaria nada.
    with app.app_context():
        direto_24 = quote_ops.calculate_quote(_payload("2026-12-24", [NOEL]))["quote"]["total_1h"]
        direto_20 = quote_ops.calculate_quote(_payload("2026-12-20", [NOEL]))["quote"]["total_1h"]
    _garante(direto_24 != direto_20, "a faixa precisa estar ativa para o cenário fazer sentido")

    def totais(data: str) -> dict:
        contratacao = {"payload": _payload(data, [NOEL]), "duracoes": ["1h"]}
        with app.app_context():
            return _totais_contratacao(contratacao, "x")[0]

    _iguais(totais("2026-12-24")["1h"], totais("2026-12-20")["1h"], "EducaManto ignora a faixa")
    _iguais(totais("2026-12-24")["1h"], 2210.00, "contratação Manto no preço normal")


# ── 11 · teto das vagas ─────────────────────────────────────────────────────────────────────────
def _itens_do_teto(
    snap: dict, data_evento: str | None = None, horas_extra: int | None = None
) -> list[dict]:
    from app.calendar.routes import _compute_performer_caches

    with app.app_context():
        return _compute_performer_caches(snap, horas_extra=horas_extra, data_evento=data_evento)


def _tetos(snap: dict, data_evento: str | None = None) -> dict[str, dict]:
    return {item["label"]: item for item in _itens_do_teto(snap, data_evento)}


def _snap(data: str, performers: list[dict], hora: str = "", coordenador_qty: int = 1) -> dict:
    return {
        "performers": performers,
        "coordenador_qty": coordenador_qty,
        "event_date": data,
        "event_time": hora,
        "fora_sp": False,
        "show_sosia_tipo": "predefinido",
    }


class _Capturado(Exception):
    """Interrompe `aplicar_equipe_do_orcamento` logo depois de o teto ser pedido (espião)."""


def _data_pedida_pelo_vinculo(entry_id: int, start_at: datetime | None) -> str | None:
    """Que `data_evento` o vínculo 273 passa ao teto para um evento com esse `start_at`.

    O orçamento é relido pelo id DENTRO do contexto: instância de outro contexto chega destacada.
    """
    from app.calendar import routes as cal_routes
    from app.calendar.orcamento_evento_ops import aplicar_equipe_do_orcamento

    capturado: dict = {}
    original = cal_routes._compute_performer_caches

    def espiao(snapshot, horas_extra=None, data_evento=None):
        capturado["data_evento"] = data_evento
        raise _Capturado()

    cal_routes._compute_performer_caches = espiao
    evento = SimpleNamespace(
        id=0, start_at=start_at, end_at=None, roles=[], title=f"{PREFIX}vínculo"
    )
    try:
        with app.app_context():
            try:
                aplicar_equipe_do_orcamento(evento, db.session.get(OrcamentoHistory, entry_id))
            except _Capturado:
                pass
            finally:
                db.session.rollback()
    finally:
        cal_routes._compute_performer_caches = original
    _garante("data_evento" in capturado, "o vínculo 273 não chegou a pedir o teto")
    return capturado["data_evento"]


def cen_11_teto_pela_data() -> None:
    t = _tetos(_snap("2026-12-24", [NOEL, AJUDANTE]))
    _iguais(t["Papai Noel"]["cache_1h"], 1000, "teto do Noel 24/12")
    _iguais(t["Ajudante do Noel"]["cache_1h"], 650, "teto do Ajudante 24/12")
    _iguais(t["Coordenador"]["cache_1h"], 500, "teto do Coordenador 24/12")
    _garante(
        ROTULO in t["Papai Noel"]["cap_notes"]["cache_1h"],
        f"cap_note: {t['Papai Noel']['cap_notes']['cache_1h']!r}",
    )

    t = _tetos(_snap("2026-12-24", [NOEL], hora="20:00"))
    _iguais(t["Papai Noel"]["cache_1h"], 1050, "teto do Noel 24/12 à noite (+50)")

    t = _tetos(_snap("2026-12-20", [NOEL, AJUDANTE]))
    _iguais(t["Papai Noel"]["cache_1h"], 600, "teto do Noel 20/12 (cachê é cachê — feature 309)")
    _iguais(t["Ajudante do Noel"]["cache_1h"], 270, "teto do Ajudante 20/12")
    _iguais(t["Coordenador"]["cache_1h"], 250, "teto do Coordenador 20/12")

    t = _tetos(_snap("2026-12-20", [NOEL, AJUDANTE]), data_evento="2026-12-24")
    _iguais(t["Papai Noel"]["cache_1h"], 1000, "a data do EVENTO manda no vínculo")
    _iguais(t["Ajudante do Noel"]["cache_1h"], 650, "idem para o ajudante")
    _iguais(t["Coordenador"]["cache_1h"], 500, "idem para o coordenador")

    t = _tetos(_snap("2026-12-24", [NOEL, BONECO]))
    _iguais(t["Boneco"]["cache_1h"], 650, "boneco com teto no piso")
    _garante(
        MARCA_PISO in t["Boneco"]["cap_notes"]["cache_1h"], "cap_note do boneco explica o piso"
    )

    coords = [
        i
        for i in _itens_do_teto(_snap("2026-12-24", [NOEL], coordenador_qty=2))
        if i["label"] == "Coordenador"
    ]
    _garante(
        len(coords) == 2 and all(c["cache_1h"] == 500 for c in coords),
        f"2 coordenadores a 500: {coords}",
    )

    regua = {i["label"]: i for i in _itens_do_teto(_snap("2026-12-24", [NOEL]), horas_extra=6)}
    _iguais(
        regua["Papai Noel"]["cache_custom"],
        6000,
        "régua >4h com cachê linear da faixa (4000 ÷ 4 × 6)",
    )
    _iguais(regua["Coordenador"]["cache_custom"], 3000, "coordenador na régua >4h")

    # O vínculo 273 passa a data do EVENTO (orçamento de 20/12, evento em 24/12).
    with app.app_context():
        entry = OrcamentoHistory(
            user_id=estado["com"]["id"],
            client_name=f"{PREFIX}vinculo",
            event_location="x",
            event_date="2026-12-20",
            total_1h=2210.0,
            total_2h=0,
            total_3h=0,
            total_4h=0,
            has_show=False,
            form_snapshot=json.dumps(_snap("2026-12-20", [NOEL])),
            result_snapshot=None,
        )
        db.session.add(entry)
        db.session.commit()
        entry_id = entry.id
    _garante(
        _data_pedida_pelo_vinculo(entry_id, datetime(2026, 12, 24, 15, 0)) == "2026-12-24",
        "aplicar_equipe_do_orcamento não passou a data do evento",
    )
    _garante(
        _data_pedida_pelo_vinculo(entry_id, None) is None,
        "evento sem start_at → cai na data do orçamento",
    )


# ── 12 · migração da configuração ───────────────────────────────────────────────────────────────
def cen_12_migracao() -> None:
    base = _config_de_teste(estado["config_real"])

    m = _cfg._migrate(copy.deepcopy(base))
    # Feature 309: a troca 600 → 712 da 307 foi removida; 600 fica 600 e a inversa guardada desfaz 712/423.
    _garante(
        m["especiais"]["Papai Noel"] == [600, 650, 675, 700],
        f"Noel 600 fica 600 (309): {m['especiais']['Papai Noel']}",
    )
    _garante(
        m["especiais"]["Ajudante do Noel"] == [270, 320, 345, 370],
        "Ajudante do Noel injetado em 270",
    )
    reverso = copy.deepcopy(base)
    reverso["especiais"]["Papai Noel"] = [712, 800, 850, 900]
    reverso["especiais"]["Ajudante do Noel"] = [423, 480, 510, 540]
    m_rev = _cfg._migrate(reverso)
    _garante(
        m_rev["especiais"]["Papai Noel"] == [600, 650, 675, 700]
        and m_rev["especiais"]["Ajudante do Noel"] == [270, 320, 345, 370],
        f"inversa guardada 712 → 600 / 423 → 270: {m_rev['especiais']['Papai Noel']} {m_rev['especiais']['Ajudante do Noel']}",
    )
    _garante(m["datas_especiais"]["natal"]["dias"] == ["12-24", "12-25"], "bloco natal injetado")
    _garante(m["markup"]["receptivo"][0] == 2.6, "markup real preservado")

    editado = copy.deepcopy(base)
    editado["especiais"]["Papai Noel"] = [650, 700, 725, 750]
    _garante(
        _cfg._migrate(editado)["especiais"]["Papai Noel"] == [650, 700, 725, 750],
        "valor editado intocado",
    )

    for ruim in (
        None,
        [],
        {"natal": None},
        {"natal": {"dias": "12-24"}},
        {"natal": {"dias": ["12-24"], "markup": "x"}},
    ):
        cfg = copy.deepcopy(base)
        cfg["datas_especiais"] = ruim
        m = _cfg._migrate(cfg)
        _garante(
            m["datas_especiais"]["natal"]["markup"][0] > 0,
            f"bloco malformado {ruim!r} não virou padrão",
        )
        _garante(
            m["markup"]["receptivo"][0] == 2.6 and "Papai Noel" in m["especiais"],
            f"tabela real perdida com {ruim!r}",
        )

    # Sobrescrita malformada é DESCARTADA (o Noel volta para tabela + piso), nunca vira cachê zero.
    cfg = copy.deepcopy(base)
    cfg["datas_especiais"] = {
        "natal": {"dias": ["12-24"], "cache": {"Papai Noel": "x", "DJ": [1, 2]}}
    }
    m = _cfg._migrate(cfg)
    _garante(
        m["datas_especiais"]["natal"]["cache"] == {},
        f"sobrescrita malformada sobrou: {m['datas_especiais']['natal']['cache']}",
    )
    _garante(m["datas_especiais"]["natal"]["piso"][0] == 650, "piso padrão preenchido")

    # `dias: []` é faixa desligada — fica salva, mas nenhuma data cai nela.
    cfg = copy.deepcopy(base)
    cfg["datas_especiais"] = {
        "natal": {**copy.deepcopy(_cfg.DEFAULTS["datas_especiais"]["natal"]), "dias": []}
    }
    m = _cfg._migrate(cfg)
    _garante(
        m["datas_especiais"]["natal"]["dias"] == []
        and _cfg.faixa_especial("2026-12-24", m) is None,
        "dias vazio = desligada",
    )

    # Especial excluído: não volta à tabela E a faixa padrão não fica com a sobrescrita órfã dele.
    excluido = copy.deepcopy(base)
    excluido["especiais_excluidos"] = ["Ajudante do Noel"]
    m = _cfg._migrate(excluido)
    _garante("Ajudante do Noel" not in m["especiais"], "excluído respeitado")
    _garante(
        "Ajudante do Noel" not in m["datas_especiais"]["natal"]["cache"],
        "sobrescrita órfã removida",
    )
    _garante("Papai Noel" in m["datas_especiais"]["natal"]["cache"], "a sobrescrita do Noel fica")

    _garante(
        _cfg.faixa_especial("abcd-12-24", m) is None
        and _cfg.faixa_especial("2026-12-24 ", m) is not None,
        "data só no formato AAAA-MM-DD",
    )

    with app.app_context():
        vivo = _cfg.load()
    _garante(
        vivo["especiais"]["Papai Noel"] == [600, 650, 675, 700],
        "load() real mantém o Noel em 600 (309)",
    )
    _garante(
        vivo["datas_especiais"]["natal"]["markup"][0] == 3.34, "load() real tem a faixa padrão"
    )


# ── 13–14 · configuração pela API ───────────────────────────────────────────────────────────────
def _bloco_natal(**mudar) -> dict:
    natal = copy.deepcopy(_cfg.DEFAULTS["datas_especiais"]["natal"])
    natal.update(mudar)
    return {"datas_especiais": {"natal": natal}}


def _natal_no_banco() -> dict:
    cfg = json.loads(_no_banco("SELECT pricing_config FROM site_settings WHERE id = 1")[0][0])
    return (cfg.get("datas_especiais") or {}).get("natal") or {}


def _recusa(sa, corpo: dict, rotulo: str, trecho_da_chave: str = "datas_especiais") -> None:
    r = sa.post("/api/orcamento/settings", json=corpo)
    _garante(r.status_code == 400, f"{rotulo} → {r.status_code}")
    campos = _erro(r).get("fields") or {}
    _garante(
        any(k.startswith(trecho_da_chave) for k in campos),
        f"{rotulo}: fields sem a chave: {campos}",
    )


def cen_13_salvar_faixa() -> None:
    sa = _cliente("sa")
    r = sa.post(
        "/api/orcamento/settings",
        json=_bloco_natal(markup=[3.5, 3.5, 3.5, 3.5], dias=["12-24", "12-25", "12-26"]),
    )
    _garante(
        r.status_code == 200, f"salvar faixa → {r.status_code} {r.get_data(as_text=True)[:300]}"
    )
    natal = sa.get("/api/orcamento/opcoes").get_json()["settings"]["datas_especiais"]["natal"]
    _iguais(natal["markup"][0], 3.5, "markup salvo volta no /opcoes")
    _garante("12-26" in natal["dias"], "dia novo salvo")
    _garante(
        _natal_no_banco().get("dias") == ["12-24", "12-25", "12-26"],
        "persistido no banco (conexão separada)",
    )
    _iguais(
        _calcular(_payload("2026-12-26", [NOEL]))["quote"]["total_1h"],
        5250.00,
        "26/12 passou a cair na faixa a 3,5",
    )

    _recusa(sa, _bloco_natal(dias=["13-40"]), "dia inválido", "datas_especiais.natal.dias")
    _recusa(sa, _bloco_natal(dias=["12-24", "12-24"]), "dia repetido", "datas_especiais.natal.dias")
    _recusa(
        sa,
        _bloco_natal(markup=[33.4, 3.34, 3.34, 3.34]),
        "markup absurdo",
        "datas_especiais.natal.markup",
    )
    _recusa(
        sa,
        _bloco_natal(cache={"Personagem Inexistente": [1, 2, 3, 4]}),
        "especial desconhecido",
        "datas_especiais.natal.cache",
    )
    _recusa(
        sa,
        _bloco_natal(cache={"Perna de Pau": [0, 0, 0, 0]}),
        "sobrescrita zerada",
        "datas_especiais.natal.cache.Perna de Pau",
    )
    _recusa(
        sa, _bloco_natal(piso=[650, -1, 650, 650]), "piso negativo", "datas_especiais.natal.piso"
    )
    _recusa(
        sa,
        _bloco_natal(coordenador=["abc", 1, 2, 3]),
        "coordenador não numérico",
        "datas_especiais.natal.coordenador",
    )
    _recusa(sa, _bloco_natal(rotulo="x" * 61), "rótulo longo", "datas_especiais.natal.rotulo")
    duas = _bloco_natal()
    duas["datas_especiais"]["teste"] = {
        **copy.deepcopy(_cfg.DEFAULTS["datas_especiais"]["natal"]),
        "dias": ["12-24"],
    }
    _recusa(sa, duas, "mesmo dia em duas faixas", "datas_especiais.teste.dias")
    no_banco = _natal_no_banco()
    _iguais(no_banco["markup"][0], 3.5, "corpo inválido não gravou nada (conexão separada)")
    _garante("13-40" not in no_banco["dias"], "dia inválido não entrou")

    r = sa.post(
        "/api/orcamento/settings",
        json=_bloco_natal(
            markup=[3.335, 3.34, 3.34, 3.34], dias=[], nota_mensagem="linha 1\nlinha 2"
        ),
    )
    _garante(r.status_code == 200, "markup com 3 casas, dias vazio e nota com quebra são aceitos")
    no_banco = _natal_no_banco()
    _iguais(no_banco["markup"][0], 3.34, "markup gravado com 2 casas (HALF_UP)")
    _garante(no_banco["dias"] == [], "dias vazio gravado = faixa desligada")
    _garante(no_banco["nota_mensagem"] == "linha 1 linha 2", "nota numa linha só")
    _garante(
        _calcular(_payload("2026-12-24", [NOEL]))["quote"].get("data_especial") is None,
        "faixa desligada não pega 24/12",
    )

    # Excluir um especial tira a sobrescrita dele da faixa (servidor), senão todo salvar daria 400.
    r = sa.post(
        "/api/orcamento/settings/especiais",
        json={"nome": ESPECIAL_DESCARTAVEL, "prices": [100, 100, 100, 100]},
    )
    _garante(r.status_code == 201, f"criar especial descartável → {r.status_code}")
    r = sa.post(
        "/api/orcamento/settings",
        json=_bloco_natal(cache={ESPECIAL_DESCARTAVEL: [700, 700, 700, 700]}),
    )
    _garante(
        r.status_code == 200 and ESPECIAL_DESCARTAVEL in _natal_no_banco()["cache"],
        "sobrescrita do descartável gravada",
    )
    r = sa.delete(f"/api/orcamento/settings/especiais/{ESPECIAL_DESCARTAVEL}")
    _garante(r.status_code == 204, f"excluir especial → {r.status_code}")
    _garante(
        ESPECIAL_DESCARTAVEL not in _natal_no_banco()["cache"],
        "DELETE não limpou a sobrescrita da faixa",
    )

    r = sa.post("/api/orcamento/settings", json=_bloco_natal())
    _garante(r.status_code == 200, "voltar ao padrão")


def cen_14_comercial_nao_edita() -> None:
    r = _cliente("com").post("/api/orcamento/settings", json=_bloco_natal())
    _garante(r.status_code == 403, f"COMERCIAL devia levar 403, levou {r.status_code}")


# ── 15–16 · legado e memória ────────────────────────────────────────────────────────────────────
def cen_15_legado_sem_data() -> None:
    res = _calcular({**_payload("", [NOEL]), "event_date": ""})
    _garante(res["quote"].get("data_especial") is None, "sem data = sem faixa")
    _iguais(res["quote"]["total_1h"], 2210.00, "sem data = preço normal")

    with app.app_context():
        entry = OrcamentoHistory(
            user_id=estado["com"]["id"],
            client_name=f"{PREFIX}legado",
            event_location="x",
            event_date="2026-12-24",
            total_1h=100,
            total_2h=200,
            total_3h=300,
            total_4h=400,
            has_show=False,
            form_snapshot=None,
            result_snapshot=None,
        )
        db.session.add(entry)
        db.session.commit()
        legado = quote_ops.quote_for_entry(entry)
    _garante(legado.get("data_especial") is None, "legado sem data_especial")
    _garante(_texto_do_pdf(legado) != "", "PDF do legado gera")

    snapshot_24 = _calcular(_payload("2026-12-24", [NOEL]))["snapshot"]
    snap_antigo = {k: v for k, v in snapshot_24.items() if k != "event_date"}
    res = _calcular(snap_antigo)
    _garante(
        res["quote"].get("data_especial") is None, "snapshot antigo sem event_date = conta de hoje"
    )


def cen_16_memoria_fecha_com_o_total() -> None:
    q = _calcular(_payload("2026-12-24", [NOEL, BONECO], hora="20:00"))["quote"]
    mem = q["memoria"]
    caches = sum(linha["valores"][0] for linha in mem if linha["tipo"] == "cache")
    markup = _linha(mem, "markup", "Markup")["valores"][0]
    pos = sum(linha["valores"][0] for linha in mem if linha["tipo"] == "pos")
    total = _linha(mem, "total", "TOTAL")["valores"][0]
    _iguais(
        round(caches * markup, 2) + pos, total, "memória soma com o total (hotfix 210)", tol=0.02
    )
    _iguais(total, q["total_1h"], "linha TOTAL = total_1h")


# ── 17 · regressão ──────────────────────────────────────────────────────────────────────────────
def cen_17_regressao() -> None:
    if "--regressao" not in sys.argv:
        raise Pulado("rode com --regressao para o portão da feature")
    # A config de teste fica no banco durante a 305 — ela não depende dos preços da calculadora.
    r = subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / "specs/305-bv-do-orcamento-no-evento/verify_305.py"),
            "--regressao",
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        cwd=str(REPO_ROOT),
        env={**os.environ, "PYTHONUTF8": "1"},
        timeout=1800,
    )
    ultima = (r.stdout.strip().splitlines() or ["?"])[-1]
    _garante(r.returncode == 0, f"verify_305 --regressao: {ultima}")


# ── 18 · limpeza ────────────────────────────────────────────────────────────────────────────────
def cen_18_limpeza() -> None:
    with app.app_context():
        db.session.rollback()
        limpar()
    real = estado.get("config_real")
    if real is not None:
        with _externo.begin() as conn:
            conn.execute(
                text("UPDATE site_settings SET pricing_config = :j WHERE id = 1"), {"j": real}
            )
    _garante(_config_real() == real, "configuração real NÃO foi restaurada")
    _garante(
        not _no_banco("SELECT 1 FROM users WHERE email LIKE :p", p=f"{PREFIX}%"),
        "usuários descartáveis sobraram",
    )
    _garante(
        not _no_banco("SELECT 1 FROM orcamento_history WHERE client_name LIKE :p", p=f"{PREFIX}%"),
        "orçamentos sobraram",
    )


CENARIOS: list[tuple[str, Callable[[], None]]] = [
    ("1. 20/12 · Papai Noel = 2.210,00 (309: cachê 600), sem faixa", cen_01_noel_20_12),
    ("2. 20/12 · Noel + Ajudante do Noel = 2.912,00", cen_02_noel_mais_ajudante_20_12),
    (
        "3. 24/12 · Noel = 5.010,00; data_especial; memória; PIX; nota na mensagem e no PDF",
        cen_03_noel_24_12,
    ),
    ("4. 25/12 · Noel + Ajudante = 7.181,00", cen_04_noel_mais_ajudante_25_12),
    ("5. 24/12 às 20h · noturno por fora = 5.110,00", cen_05_noturno_segue_por_fora),
    (
        "6. 24/12 · boneco entra pelo piso = 7.181,00; especial vazio não",
        cen_06_boneco_pelo_piso_e_linha_vazia,
    ),
    (
        "7. 24/12 · Perna de Pau = 3.841,00 e show = 5.066,00: markup e piso valem para qualquer produto",
        cen_07_qualquer_produto_na_data_e_show,
    ),
    (
        "8. 24/12 · 2h = 10.020,00; 2 coordenadores = 6.680,00; 6h pela régua",
        cen_08_hora_extra_e_dois_coordenadores,
    ),
    (
        "9. 24/12 · fora de SP, personalizado (valor e multiplicador) e BV 10% (305)",
        cen_09_transporte_personalizado_bv,
    ),
    ("10. EducaManto ignora a data (com a faixa provadamente ativa)", cen_10_educamanto_neutro),
    (
        "11. teto das vagas pela data: 24/12, noturno, 20/12, data do evento, piso, 2 coords, régua, vínculo 273",
        cen_11_teto_pela_data,
    ),
    (
        "12. migração guardada e defensiva do pricing_config (órfã removida; data só ISO)",
        cen_12_migracao,
    ),
    (
        "13. superadmin salva a faixa; 400 por campo e nada gravado; dias vazio desliga; DELETE limpa a faixa",
        cen_13_salvar_faixa,
    ),
    ("14. DEVE FALHAR: COMERCIAL não edita a configuração", cen_14_comercial_nao_edita),
    ("15. sem data, legado e snapshot antigo = conta de hoje", cen_15_legado_sem_data),
    ("16. memória de cálculo fecha com o total", cen_16_memoria_fecha_com_o_total),
    ("17. regressão (--regressao)", cen_17_regressao),
]


def main() -> int:
    print("Feature 307 — Papai Noel em data especial na Calculadora")
    preparar()
    try:
        so = next((a.split("=", 1)[1].split(",") for a in sys.argv if a.startswith("--so=")), None)
        for nome, fn in CENARIOS:
            if so is None or nome.split(".", 1)[0] in so:
                cenario(nome, fn)
    finally:
        cenario("18. limpeza e restauração da configuração real", cen_18_limpeza)
    contados = [r for r in resultados if r[1] != "PULADO"]
    ok = sum(1 for _, status, _ in contados if status == "OK")
    pulados = len(resultados) - len(contados)
    print(
        f"{ok}/{len(contados)} OK"
        + (f" · {pulados} pulado(s) — fora da contagem" if pulados else "")
    )
    return 0 if ok == len(contados) else 1


if __name__ == "__main__":
    sys.exit(main())
