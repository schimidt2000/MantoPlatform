"""Verificação da feature 313 — desconto e PIX na calculadora (3b, noite do desconto).

A tabela de cenários está na `spec.md` (seção "Verificação": 1–16 e L). Escrito ANTES do núcleo (Princípio VIII): a
primeira rodada, contra a `main`, fica em `verify_313_primeira_falha.txt`.

O cenário 1 compara o recálculo de todos os orçamentos do espelho com o gabarito gravado na `c074657b`
(`gabarito_paridade.py --gravar`); o caminho vem de `--gabarito=<json>` ou de `GABARITO_313`. As exceções da regra
do dono (Q7: o acréscimo em R$ uma vez; o BV sobre a base com os outros acréscimos) são conferidas pela FÓRMULA, a
partir do que o gabarito tinha — não só "é diferente".

Rodar contra o manto_local (PowerShell, na raiz do worktree)::

    . <scratchpad>\\env313.ps1
    & $py specs\\313-desconto-e-pix-na-calculadora\\verify_313.py '--gabarito=<scratchpad>\\gabarito313.json'
    & $py specs\\313-desconto-e-pix-na-calculadora\\verify_313.py '--so=2,3'      # iteração (a limpeza roda sempre)

Saída: 0 = tudo OK; 1 = algum cenário falhou; 2 = ambiente impróprio.
"""

from __future__ import annotations

import io
import json
import math
import os
import subprocess
import sys
import traceback
import uuid
from collections.abc import Callable
from datetime import datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(AQUI))
os.environ.setdefault("FLASK_ENV", "development")
os.environ.setdefault("MANTO_SEM_THREADS", "1")
if not os.environ.get("DATABASE_URL"):
    os.environ["DATABASE_URL"] = (REPO_ROOT / ".local-db-url").read_text(encoding="utf-8").strip()

from sqlalchemy import create_engine, text  # noqa: E402

from app import create_app, db, limiter, maps  # noqa: E402
from app.calendar import routes as cal_routes  # noqa: E402
from app.calendar import service as cal_service  # noqa: E402
from app.constants import RoleName, now_sp  # noqa: E402
from app.models import CalendarEvent, OrcamentoHistory, Role, SiteSetting, User  # noqa: E402

PREFIX = "__v313_"
SENHA = "verify-313-senha"
CENTAVO = Decimal("0.01")
PIX = "verify313-pix@exemplo.test"
QUEM = f"{PREFIX}Buffet Parceiro"
ATOR = {"type": "ator", "subtipo": "cara_limpa", "nome": "Teste", "makeup": False}
VISITA = "visita_magica"
TOL = 0.011  # um centavo de folga nas fórmulas independentes (float × arredondamento da conta)

app = create_app()
app.config["TESTING"] = True
limiter.enabled = False

resultados: list[tuple[str, bool, str]] = []
estado: dict = {}
OPCOES: dict = {"so": None, "gabarito": os.environ.get("GABARITO_313")}
_externo = create_engine(os.environ["DATABASE_URL"], future=True)

# ── dublês do Google (com contador) ─────────────────────────────────────────────────────────────
GOOGLE = {"insert": 0}


def _fake_insert(*_a, **_k):
    GOOGLE["insert"] += 1
    return {"id": f"{PREFIX}g{uuid.uuid4().hex[:10]}", "htmlLink": "https://fake.local"}


maps.cidade_do_endereco = lambda _e: (None, None)
cal_routes._fetch_travel_data = lambda _ev, _s: {}
cal_service.insert_event = _fake_insert
cal_service.update_event = lambda *a, **k: None
cal_service.delete_event = lambda *a, **k: None
cal_routes.insert_event = _fake_insert
for _nome in ("update_event", "delete_event"):
    if hasattr(cal_routes, _nome):
        setattr(cal_routes, _nome, lambda *a, **k: None)


# ── utilidades ──────────────────────────────────────────────────────────────────────────────────
def q(x) -> Decimal:
    return Decimal(str(x)).quantize(CENTAVO, rounding=ROUND_HALF_UP)


def _no_banco(sql: str, **params):
    with _externo.connect() as conn:
        return conn.execute(text(sql), params).fetchall()


def cenario(nome: str, fn: Callable[[], None]) -> None:
    try:
        fn()
        resultados.append((nome, True, ""))
        print(f"  OK     {nome}")
    except Exception as exc:  # noqa: BLE001
        with app.app_context():
            db.session.rollback()
        ultima = traceback.format_exc().strip().splitlines()[-1]
        resultados.append((nome, False, ultima))
        print(f"  FALHA  {nome}: {str(exc)[:500]}")


def _garante(cond: bool, msg: str) -> None:
    if not cond:
        raise AssertionError(msg)


def _perto(a, b, msg: str, tol: float = TOL) -> None:
    _garante(
        a is not None and b is not None and abs(float(a) - float(b)) <= tol, f"{msg}: {a} ≠ {b}"
    )


def _deve_quebrar(fn: Callable[[], None], rotulo: str) -> None:
    """Prova por mutação: com a regra errada ligada, a conferência TEM de falhar."""
    try:
        fn()
    except AssertionError:
        return
    raise AssertionError(f"mutação '{rotulo}' passou despercebida — o cenário não protege a regra")


def _cliente(papel: str):
    c = app.test_client()
    r = c.post("/api/auth/login", json={"email": estado[papel]["email"], "password": SENHA})
    _garante(r.status_code == 200, f"login {papel} → {r.status_code}")
    return c


def _erro(r) -> dict:
    corpo = r.get_json(silent=True) or {}
    return corpo.get("error") or {}


def _fmt(v) -> str:
    from app.orcamento.quote_ops import _fmt_brl

    return _fmt_brl(float(v))


def _texto_pct(d: float) -> str:
    """A regra do % da proposta, escrita de novo aqui (oráculo independente): uma casa, para baixo, vírgula."""
    piso = math.floor(round(d, 6) * 10) / 10
    return (f"{piso:.1f}".rstrip("0").rstrip(".")).replace(".", ",")


def _bv_que_acompanha(bv, venda, total) -> float:
    """A regra da 305 escrita de novo aqui (oráculo independente — a mutação do cenário 2 troca a do app):
    ``bv × venda ÷ total`` ao centavo, HALF_UP; venda a até R$ 0,01 do total devolve o BV cheio."""
    bv_d, venda_d, total_d = (Decimal(str(x)) for x in (bv, venda, total))
    if abs(venda_d - total_d) <= CENTAVO:
        return float(q(bv_d))
    return float(q(bv_d * venda_d / total_d))


# ── fixtures ────────────────────────────────────────────────────────────────────────────────────
def _usuario(apelido: str, papel: str) -> dict:
    email = f"{PREFIX}{apelido}@manto.local"
    u = User(
        name=f"{PREFIX}{apelido}",
        email=email,
        is_active=True,
        has_access=True,
        receives_commission=True,
    )
    u.set_password(SENHA)
    u.roles.append(Role.query.filter_by(name=papel).one())
    db.session.add(u)
    db.session.flush()
    return {"id": u.id, "email": email}


def _payload(**extra) -> dict:
    corpo = {
        "performers": [ATOR],
        "coordenador_qty": 1,
        "event_date": (now_sp().date() + timedelta(days=60)).isoformat(),
        "event_time": "15:00",
        "client_name": f"{PREFIX}Cliente",
        "event_location": f"{PREFIX}Salão de festas",
        "incluir_duracao": ["1h", "2h", "3h", "4h"],
        "modo_duracao": "horas",
    }
    corpo.update(extra)
    return corpo


def _acr(tipo: str, valor: float, pct: bool, descricao: str = "") -> dict:
    return {"tipo": tipo, "descricao": descricao, "is_percent": pct, "value": valor}


def _calcular(corpo: dict, papel: str = "com") -> dict:
    r = _cliente(papel).post("/api/orcamento/calcular", json=corpo)
    _garante(r.status_code == 200, f"calcular → {r.status_code} {r.get_data(as_text=True)[:300]}")
    return r.get_json()


def _calcular_400(corpo: dict) -> dict:
    r = _cliente("com").post("/api/orcamento/calcular", json=corpo)
    _garante(
        r.status_code == 400, f"esperava 400, veio {r.status_code} {r.get_data(as_text=True)[:200]}"
    )
    return _erro(r).get("fields") or {}


def _salvar(res: dict, papel: str = "com") -> int:
    r = _cliente(papel).post("/api/orcamento/salvar", json=res)
    _garante(r.status_code == 201, f"salvar → {r.status_code} {r.get_data(as_text=True)[:200]}")
    return r.get_json()["id"]


def _bv_cheio(res: dict, col: int) -> float:
    linhas = [a for a in res["snapshot"].get("acrescimos") or [] if a.get("is_bv")]
    _garante(linhas, "orçamento sem linha de BV")
    return float(sum(a["valores_brl"][col] for a in linhas))


def _linhas(eid: int) -> list[dict]:
    rows = _no_banco(
        "SELECT tipo, is_percent, amount_brl, is_bv FROM event_acrescimos WHERE event_id = :i ORDER BY id",
        i=eid,
    )
    return [dict(zip(("tipo", "is_percent", "amount_brl", "is_bv"), r, strict=True)) for r in rows]


def _evento(eid: int) -> dict:
    r = _no_banco("SELECT sale_value, sale_value_gross FROM calendar_events WHERE id = :i", i=eid)[
        0
    ]
    return {"venda": r[0], "bruto": r[1]}


def _comissao(eid: int):
    rows = _no_banco(
        "SELECT amount FROM commission_payments WHERE event_id = :i AND status <> 'cancelado' ORDER BY id",
        i=eid,
    )
    return rows[0][0] if rows else None


def _taxa() -> Decimal:
    with app.app_context():
        s = db.session.get(SiteSetting, 1) or SiteSetting.query.first()
        return Decimal(
            str(s.default_commission_rate if s and s.default_commission_rate is not None else 2)
        )


def _corpo_criacao(
    titulo: str, orc: int | None, *, venda, bruto, duracao: str = "2", **extra
) -> dict:
    d = (now_sp().date() + timedelta(days=60)).isoformat()
    corpo = {
        "title": titulo,
        "event_type": "R&I",
        "date": d,
        "start": "15:00",
        "end": "17:00",
        "location": f"{PREFIX}Salão",
        "description": "",
        "needs_rehearsal": False,
        "sale_value": venda,
        "sale_value_gross": bruto,
        "transport_value": 0,
        "acrescimo_value": 0,
        "with_invoice": False,
        "is_cortesia_permuta": False,
        "seller_id": estado["sa"]["id"],
        "sale_date": None,
        "payment_method": None,
        "payment_installments": None,
        "payment_due_date": None,
        "orcamento_history_id": orc,
        "characters": [],
        "orc_caches": [],
        "acrescimos": [],
        "client_pairs": [],
        "observations": [],
        "duracao": duracao,
    }
    corpo.update(extra)
    return corpo


def _criar(corpo: dict, papel: str = "com") -> int:
    r = _cliente(papel).post("/api/events", json=corpo)
    _garante(
        r.status_code == 201, f"POST /api/events → {r.status_code} {r.get_data(as_text=True)[:300]}"
    )
    j = r.get_json()
    return (j.get("event") or j).get("id")


def _evento_sem_venda(rotulo: str) -> int:
    with app.app_context():
        inicio = datetime.combine(
            now_sp().date() + timedelta(days=60), datetime.min.time()
        ).replace(hour=15)
        ev = CalendarEvent(
            title=f"{PREFIX}(R&I) {rotulo}",
            event_type="R&I",
            start_at=inicio,
            end_at=inicio + timedelta(hours=2),
            google_event_id=f"{PREFIX}{uuid.uuid4().hex[:8]}",
            source="google_calendar",
            location=f"{PREFIX}Salão",
        )
        db.session.add(ev)
        db.session.commit()
        return ev.id


def preparar() -> None:
    with app.app_context():
        limpar()
        for apelido, papel in (
            ("sa", RoleName.SUPERADMIN),
            ("com", RoleName.COMERCIAL),
            ("fin", RoleName.FINANCEIRO),
            ("cast", RoleName.CASTING),
            ("rev", RoleName.REVENDEDOR_EDUCAMANTO),
        ):
            estado[apelido] = _usuario(apelido, papel)
        db.session.commit()


def limpar() -> None:
    ids = [
        r[0]
        for r in _no_banco(
            "SELECT id FROM calendar_events WHERE title LIKE :p OR google_event_id LIKE :p",
            p=f"%{PREFIX}%",
        )
    ]
    for eid in ids:
        for tabela in (
            "commission_payments",
            "event_logs",
            "event_roles",
            "event_clients",
            "event_acrescimos",
        ):
            db.session.execute(text(f"DELETE FROM {tabela} WHERE event_id = :i"), {"i": eid})
    db.session.commit()
    for eid in ids:
        ev = db.session.get(CalendarEvent, eid)
        if ev is not None:
            db.session.delete(ev)
    db.session.commit()
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


# ── 1 · paridade com o gabarito ─────────────────────────────────────────────────────────────────
def _linhas_de_acrescimo(memoria: list[dict]) -> list[list[float]]:
    return [m["valores"] for m in memoria if str(m.get("label", "")).startswith("Acréscimo:")]


def _q7_esperado(g_snap: dict, g_quote: dict) -> dict[str, float]:
    """O preço que a regra da Q7 dá, refeito do que o gabarito tinha (oráculo independente da R1).

    A base de cada coluna é o total de antes sem os acréscimos e sem a nota (o gabarito somava todos os % sobre a
    mesma base). Sobre ela: os não-BV (R$ inteiro, % sobre a base), o BV em % sobre base + não-BV, o BV em reais
    inteiro, a nota no fim. Acima de 4h, a base de 4h escala ÷ 4 × h e os R$ entram uma vez.
    """
    nota = bool(g_snap.get("nota_fiscal"))
    acr = [a for a in g_snap.get("acrescimos") or [] if a.get("tipo") and a.get("value")]
    linhas_mem = _linhas_de_acrescimo(g_quote.get("memoria") or [])
    out: dict[str, float] = {}
    bases = []
    for col in range(4):
        total = float(g_quote[f"total_{col + 1}h"])
        antes_nf = total * 0.84 if nota else total
        soma_antiga = sum(linha[col] for linha in linhas_mem)
        bases.append(antes_nf - soma_antiga)

    def _preco(base: float) -> float:
        nao_bv = sum(
            (base * a["value"] / 100) if a["is_percent"] else a["value"]
            for a in acr
            if not a.get("is_bv")
        )
        bv = sum(
            ((base + nao_bv) * a["value"] / 100) if a["is_percent"] else a["value"]
            for a in acr
            if a.get("is_bv")
        )
        preco = base + nao_bv + bv
        return preco / 0.84 if nota else preco

    for col in range(4):
        out[f"total_{col + 1}h"] = _preco(bases[col])
    dc = int(g_snap.get("duracao_custom") or 0)
    if dc > 4 and g_quote.get("total_custom"):
        out["total_custom"] = _preco(bases[3] / 4 * dc)
    return out


def _e_excecao(g_snap: dict) -> tuple[bool, bool]:
    acr = [a for a in g_snap.get("acrescimos") or [] if a.get("tipo") and a.get("value")]
    bv_pct = any(a.get("is_bv") and a.get("is_percent") for a in acr)
    outro = any(not a.get("is_bv") for a in acr)
    dc = int(g_snap.get("duracao_custom") or 0)
    fixo = any(not a.get("is_percent") for a in acr)
    return (bv_pct and outro), (dc > 4 and fixo)


def c1_paridade() -> None:
    import gabarito_paridade as gp

    caminho = OPCOES.get("gabarito")
    _garante(
        caminho and Path(caminho).exists(),
        f"sem gabarito ({caminho!r}): rode gabarito_paridade.py --gravar",
    )
    gabarito = json.loads(Path(caminho).read_text(encoding="utf-8"))
    with app.app_context():
        atual = json.loads(
            json.dumps(gp.recalcular_todos(), ensure_ascii=False, sort_keys=True, default=str)
        )
    # Os orçamentos que o próprio verify cria não estão no gabarito.
    atual = {k: v for k, v in atual.items() if k in gabarito}
    difs = gp.diferencas(gabarito, atual)
    fora, excecoes, erradas = [], 0, []
    for oid, caminhos in difs.items():
        g = gabarito[oid]
        if "erro" in g:
            fora.append((oid, caminhos[:3]))
            continue
        bv_outro, extra_fixo = _e_excecao(g["snapshot"])
        if not (bv_outro or extra_fixo):
            fora.append((oid, caminhos[:4]))
            continue
        excecoes += 1
        esperado = _q7_esperado(g["snapshot"], g["quote"])
        for chave, valor in esperado.items():
            veio = atual[oid]["quote"].get(chave)
            if veio is None or abs(float(veio) - valor) > 0.02:
                erradas.append((oid, chave, round(valor, 2), veio))
    print(
        f"         paridade: {len(gabarito)} no gabarito, {len(difs)} com diferença, {excecoes} exceções da Q7"
    )
    _garante(not fora, f"diferença fora das exceções da Q7 em {len(fora)}: {fora[:5]}")
    # O espelho tem orçamentos com BV + outro acréscimo e com extra + R$: sem nenhuma exceção, a regra nova não
    # está no código (é o vermelho contra a `main`).
    _garante(
        excecoes > 0,
        "nenhuma exceção da Q7 — a regra do acréscimo uma vez / BV sobre tudo não está no código",
    )
    _garante(not erradas, f"exceções da Q7 fora da fórmula em {len(erradas)}: {erradas[:5]}")


# ── 2–4 · o desconto ────────────────────────────────────────────────────────────────────────────
def _confere_desconto_pct(com_bv: bool) -> None:
    acr = [_acr("BV", 10, True)] if com_bv else []
    r0 = _calcular(_payload(acrescimos=acr))
    r = _calcular(_payload(acrescimos=acr, desconto_pct=10))
    qq, sn = r["quote"], r["snapshot"]
    for d in range(1, 5):
        bruto = r0["quote"][f"total_{d}h"]
        _garante(qq.get(f"bruto_{d}h") == bruto, f"bruto_{d}h {qq.get(f'bruto_{d}h')} ≠ {bruto}")
        _garante(
            qq[f"total_{d}h"] == round(bruto * 0.9, 2),
            f"total_{d}h {qq[f'total_{d}h']} ≠ {bruto} × 0,9",
        )
        if com_bv:
            cheio = _bv_cheio(r, d - 1)
            _garante(cheio == _bv_cheio(r0, d - 1), "o BV cheio mudou com o desconto")
            _perto(
                qq.get(f"bv_{d}h"), _bv_que_acompanha(cheio, qq[f"total_{d}h"], bruto), f"bv_{d}h"
            )
            _garante(isinstance(qq.get(f"bv_{d}h"), float), "bv_* não é número no JSON")
    _garante(
        any(str(m.get("label", "")).startswith("Desconto (10%)") for m in qq.get("memoria") or []),
        "memória sem a linha do desconto",
    )
    _garante(
        sn.get("versao_conta") == 2
        and sn.get("desconto_pct_digitado") == 10
        and sn.get("desconto_aplicado") == 10,
        f"snapshot: versao={sn.get('versao_conta')} digitado={sn.get('desconto_pct_digitado')} "
        f"aplicado={sn.get('desconto_aplicado')}",
    )
    if com_bv:
        _garante(
            r0["quote"].get("bv_1h") == _bv_cheio(r0, 0), "sem desconto o BV a repassar é o cheio"
        )
        _garante(
            not any(
                "BV a repassar" in str(m.get("label")) for m in r0["quote"].get("memoria") or []
            ),
            "sem desconto a memória ganhou linha (paridade)",
        )


def c2_desconto_pct() -> None:
    _confere_desconto_pct(False)
    _confere_desconto_pct(True)

    from app.orcamento import quote_ops

    original = getattr(quote_ops, "bv_que_acompanha", None)
    if original is not None:
        quote_ops.bv_que_acompanha = lambda bv, venda, total: Decimal(str(bv))
        try:
            _deve_quebrar(lambda: _confere_desconto_pct(True), "BV sem acompanhar o desconto")
        finally:
            quote_ops.bv_que_acompanha = original


def c3_desconto_valor() -> None:
    r0 = _calcular(_payload())
    bruto2 = r0["quote"]["total_2h"]
    valor = float(int(bruto2 * 0.9))  # um valor redondo, como a equipe fecha
    r = _calcular(_payload(desconto_valor=valor, desconto_duracao="2h"))
    qq, sn = r["quote"], r["snapshot"]
    d_exato = (1 - valor / bruto2) * 100
    _garante(
        qq["total_2h"] == valor, f"a duração digitada não saiu exata: {qq['total_2h']} ≠ {valor}"
    )
    _perto(qq.get("desconto_pct"), d_exato, "desconto_pct exato", tol=1e-6)
    _garante(
        qq.get("desconto_pct_texto") == _texto_pct(d_exato),
        f"texto {qq.get('desconto_pct_texto')!r}",
    )
    for d in (1, 3, 4):
        _garante(
            qq[f"total_{d}h"] == round(r0["quote"][f"total_{d}h"] * (1 - d_exato / 100), 2),
            f"total_{d}h pelo mesmo %",
        )
    _garante(
        sn.get("desconto_valor") == valor and sn.get("desconto_duracao") == "2h",
        "snapshot sem o digitado",
    )
    # 10% exato achado pelo valor (9,9999…%) → "10"; 8,333…% → "8,3".
    v10 = round(bruto2 * 0.9, 2)
    r10 = _calcular(_payload(desconto_valor=v10, desconto_duracao="2h"))
    _garante(
        r10["quote"].get("desconto_pct_texto") == _texto_pct(r10["quote"]["desconto_pct"]),
        "texto do 10%",
    )
    r83 = _calcular(_payload(desconto_pct=100 / 12))
    _garante(
        r83["quote"].get("desconto_pct_texto") == "8,3",
        f"8,333…% → {r83['quote'].get('desconto_pct_texto')!r}",
    )
    # Igual ao cheio = sem desconto.
    rig = _calcular(_payload(desconto_valor=bruto2, desconto_duracao="2h"))
    _garante(not rig["quote"].get("desconto_pct"), "valor igual ao cheio virou desconto")
    # Inválidos.
    for corpo, campo in (
        (_payload(desconto_valor=bruto2 + 100, desconto_duracao="2h"), "desconto_valor"),
        (_payload(desconto_valor=0.0001, desconto_duracao="2h"), None),
        (_payload(desconto_valor=-10, desconto_duracao="2h"), "desconto_valor"),
        (_payload(desconto_valor=valor), "desconto_valor"),
        (_payload(desconto_duracao="2h", desconto_valor=None), None),
        (
            _payload(desconto_valor=valor, desconto_duracao="3h", incluir_duracao=["1h", "2h"]),
            "desconto_valor",
        ),
        (_payload(desconto_pct=100), "desconto_pct"),
        (_payload(desconto_pct=-5), "desconto_pct"),
        (_payload(desconto_pct="abc"), "desconto_pct"),
    ):
        if campo is None:
            continue
        fields = _calcular_400(corpo)
        _garante(
            campo in fields,
            f"{campo} fora de {fields} ({ {k: corpo.get(k) for k in ('desconto_pct', 'desconto_valor', 'desconto_duracao')} })",
        )


def c4_base_do_desconto() -> None:
    base = _payload(
        fora_sp=True,
        deslocamento_responsavel="manto",
        km_ida=120,
        transporte_tipo="van",
        num_carros=1,
        nota_fiscal=True,
        acrescimos=[_acr("Outro", 100, False)],
    )
    r0 = _calcular(base)
    r = _calcular({**base, "desconto_pct": 10})
    _garante(
        (r0["quote"].get("transport_breakdown") or {}).get("total"),
        "o orçamento não tem transporte",
    )
    for d in range(1, 5):
        bruto = r0["quote"][f"total_{d}h"]
        _garante(r["quote"][f"bruto_{d}h"] == bruto, f"bruto_{d}h sem transporte/acréscimo/nota")
        _garante(
            r["quote"][f"total_{d}h"] == round(bruto * 0.9, 2),
            f"total_{d}h: o desconto não foi sobre o total",
        )
        _garante(r["quote"][f"pix_{d}h"] == round(bruto * 0.9, 2), f"pix_{d}h sobre outra base")


# ── 5–7 · PIX e proposta ────────────────────────────────────────────────────────────────────────
def c5_pix() -> None:
    acr = [_acr("BV", 10, True)]
    r0 = _calcular(_payload(acrescimos=acr))["quote"]
    for d in range(1, 5):
        _garante(
            r0.get("pix_pct") == 5 and r0.get(f"pix_{d}h") == round(r0[f"total_{d}h"] * 0.95, 2),
            f"sem desconto {d}h",
        )
    casos = ((3, 5), (5, 5), (10, 10), (4.96, 5))
    for dpct, pix_esperado in casos:
        r = _calcular(_payload(acrescimos=acr, desconto_pct=dpct))
        qq = r["quote"]
        _garante(
            qq.get("pix_pct") == pix_esperado,
            f"{dpct}%: pix_pct {qq.get('pix_pct')} ≠ {pix_esperado}",
        )
        for d in range(1, 5):
            bruto, total = qq[f"bruto_{d}h"], qq[f"total_{d}h"]
            if dpct >= 5:
                _garante(qq[f"pix_{d}h"] == total, f"{dpct}%: pix_{d}h ≠ total (vale o maior)")
                _garante(qq.get(f"bv_pix_{d}h") == qq.get(f"bv_{d}h"), f"{dpct}%: bv_pix ≠ bv")
            else:
                _garante(
                    qq[f"pix_{d}h"] == round(bruto * 0.95, 2),
                    f"{dpct}%: pix_{d}h somou os descontos",
                )
                _perto(
                    qq.get(f"bv_pix_{d}h"),
                    _bv_que_acompanha(_bv_cheio(r, d - 1), qq[f"pix_{d}h"], bruto),
                    "bv_pix",
                )
    r496 = _calcular(_payload(desconto_pct=4.96))["quote"]
    _garante(r496.get("desconto_pct_texto") == "4,9", f"4,96% → {r496.get('desconto_pct_texto')!r}")


def _blocos_da_mensagem(msg: str) -> list[str]:
    return [b for b in msg.split("\n\n") if "VALOR TOTAL" in b]


def c6_mensagem_e_pdf() -> None:
    from pypdf import PdfReader

    from app.orcamento.pdf import gerar_orcamento_pdf

    def _pdf(quote: dict) -> tuple[str, int]:
        with app.app_context():
            pdf = gerar_orcamento_pdf(quote)
        _garante(pdf[:4] == b"%PDF", "PDF não gerado")
        leitor = PdfReader(io.BytesIO(pdf))
        return "\n".join(p.extract_text() or "" for p in leitor.pages), len(leitor.pages)

    acr = [_acr("BV", 10, True)]
    sem = _calcular(_payload(acrescimos=acr))["quote"]
    _garante(
        "de R$" not in sem["message"] and "desconto de" not in sem["message"],
        "sem desconto, a mensagem mudou",
    )
    _garante(
        "desconto especial de 5% aplicado" in sem["message"], "sem desconto, a frase do PIX sumiu"
    )
    texto, paginas = _pdf(sem)
    _garante("PIX à vista (5%" in texto and paginas == 1, f"PDF sem desconto: {paginas} pág.")

    q3 = _calcular(_payload(acrescimos=acr, desconto_pct=3))["quote"]
    for d in range(1, 5):
        _garante(
            f"de {_fmt(q3[f'bruto_{d}h'])} por {_fmt(q3[f'total_{d}h'])}" in q3["message"],
            f"3%: de/por {d}h",
        )
        _garante(_fmt(q3[f"pix_{d}h"]) in q3["message"], f"3%: o PIX de {d}h")
    _garante("(desconto de 3% aplicado)" in q3["message"], "3%: a linha do desconto")
    _garante("desconto especial de 5% aplicado" in q3["message"], "3%: a frase do PIX de 5%")
    _garante("BV" not in q3["message"], "a palavra BV na proposta")

    q10 = _calcular(_payload(acrescimos=acr, desconto_pct=10))["quote"]
    _garante(
        "o mesmo valor — o desconto de 10% já está aplicado" in q10["message"],
        "10%: a frase do PIX",
    )
    _garante("desconto especial de 5%" not in q10["message"], "10%: o PIX de 5% por cima")
    texto, paginas = _pdf(q10)
    _garante(
        "Desconto de 10% aplicado" in texto and "de R$" in texto, "PDF com desconto sem o de/por"
    )
    _garante(paginas == 1, f"PDF com desconto em {paginas} páginas")

    fora = _calcular(
        _payload(
            fora_sp=True,
            deslocamento_responsavel="manto",
            km_ida=120,
            transporte_tipo="van",
            num_carros=1,
            desconto_pct=10,
        )
    )["quote"]
    transp = float((fora.get("transport_breakdown") or {}).get("total") or 0)
    _garante(transp > 0, "sem transporte")
    for d, bloco in enumerate(_blocos_da_mensagem(fora["message"]), start=1):
        _garante(
            f"Logística e Transporte: {_fmt(transp)}" in bloco, f"bloco {d} sem o transporte cheio"
        )
        _garante(
            f"Valor da Apresentação: {_fmt(round(fora[f'bruto_{d}h'] - transp, 2))}" in bloco,
            f"bloco {d}: a apresentação não sai do cheio",
        )

    so = _calcular(
        _payload(performers=[], produtos=[{"chave": VISITA}], coordenador_qty=0, desconto_pct=10)
    )["quote"]
    _garante(so.get("valor_unico"), "o só-produto não veio como valor único")
    _garante(
        f"de {_fmt(so['bruto_1h'])} por {_fmt(so['total_1h'])}" in so["message"]
        and "Total da visita" in so["message"],
        "só-produto sem de/por",
    )


def c7_orcamento_antigo() -> None:
    res = _calcular(_payload(acrescimos=[_acr("BV", 10, True)]))
    quote = {
        k: v
        for k, v in res["quote"].items()
        if not k.startswith(("bruto_", "pix_", "bv_", "desconto_", "base_4h"))
    }
    snap = {
        k: v
        for k, v in res["snapshot"].items()
        if k not in ("versao_conta", "bases", "brutos") and not k.startswith("desconto_")
    }
    with app.app_context():
        e = OrcamentoHistory(
            user_id=estado["com"]["id"],
            client_name=f"{PREFIX}antigo",
            event_location=f"{PREFIX}Salão",
            event_date=snap.get("event_date"),
            total_1h=quote["total_1h"],
            total_2h=quote["total_2h"],
            total_3h=quote["total_3h"],
            total_4h=quote["total_4h"],
            has_show=False,
            form_snapshot=json.dumps(snap),
            result_snapshot=json.dumps(quote),
        )
        db.session.add(e)
        db.session.commit()
        oid = e.id
    c = _cliente("com")
    r = c.get(f"/api/orcamento/historico/{oid}")
    _garante(r.status_code == 200, f"histórico → {r.status_code}")
    j = r.get_json()
    qj = j.get("quote") or j.get("result_snapshot") or {}
    _garante("bruto_1h" not in qj, "o orçamento antigo ganhou chave nova")
    pdf = c.get(f"/api/orcamento/historico/{oid}/pdf")
    _garante(pdf.status_code == 200 and pdf.data[:4] == b"%PDF", f"PDF antigo → {pdf.status_code}")
    from pypdf import PdfReader

    texto = "\n".join(p.extract_text() or "" for p in PdfReader(io.BytesIO(pdf.data)).pages)
    _garante("PIX à vista (5%" in texto, "o PDF antigo mudou o PIX")
    pre = c.get(f"/api/events/new/prefill?orcamento_id={oid}")
    _garante(pre.status_code == 200, f"prefill → {pre.status_code}")
    pj = pre.get_json()
    _garante(
        "bruto_1h" not in pj and "extra_por_horas" not in pj,
        f"prefill antigo com chave nova: {sorted(pj)}",
    )


# ── 8–10 · a ordem da conta ─────────────────────────────────────────────────────────────────────
def c8_acrescimo_uma_vez() -> None:
    base4 = _calcular(_payload())["quote"]["total_4h"]
    r = _calcular(_payload(duracao_custom=8, acrescimos=[_acr("Taxa de urgência", 300, False)]))[
        "quote"
    ]
    _perto(r.get("total_custom"), base4 / 4 * 8 + 300, "8h com urgência de 300 (uma vez)")
    rn = _calcular(
        _payload(
            duracao_custom=8, nota_fiscal=True, acrescimos=[_acr("Taxa de urgência", 300, False)]
        )
    )["quote"]
    _perto(rn.get("total_custom"), (base4 / 4 * 8 + 300) / 0.84, "8h com urgência e nota")
    # Sem parte fixa: a extra continua escalando o preço de 4h, centavo por centavo (analyze A2).
    lin = _calcular(
        _payload(duracao_custom=6, nota_fiscal=True, acrescimos=[_acr("BV", 10, True)])
    )["quote"]
    _garante(
        lin["total_custom"] == round(lin["total_4h"] / 4 * 6, 2),
        "sem parte fixa a extra mudou o centavo",
    )


def c9_bv_sobre_tudo() -> None:
    b = _calcular(_payload())["quote"]
    b1, b4 = b["total_1h"], b["total_4h"]
    r = _calcular(_payload(acrescimos=[_acr("Outro", 200, False), _acr("BV", 10, True)]))
    _perto(r["quote"]["total_1h"], b1 + 200 + 0.1 * (b1 + 200), "BV sobre a base com o Outro")
    _perto(_bv_cheio(r, 0), 0.1 * (b1 + 200), "valores_brl do BV")
    rn = _calcular(
        _payload(nota_fiscal=True, acrescimos=[_acr("Outro", 200, False), _acr("BV", 10, True)])
    )
    _perto(rn["quote"]["total_1h"], (b1 + 200 + 0.1 * (b1 + 200)) / 0.84, "com nota")
    _perto(_bv_cheio(rn, 0), 0.1 * (b1 + 200), "o BV antes da nota")
    r6 = _calcular(
        _payload(duracao_custom=6, acrescimos=[_acr("Outro", 200, False), _acr("BV", 10, True)])
    )
    base6 = b4 / 4 * 6
    _perto(r6["quote"]["total_custom"], base6 + 200 + 0.1 * (base6 + 200), "na extra de 6h")
    rr = _calcular(
        _payload(duracao_custom=6, acrescimos=[_acr("Outro", 200, False), _acr("BV", 150, False)])
    )
    _perto(rr["quote"]["total_1h"], b1 + 350, "BV em reais uma vez")
    _perto(rr["quote"]["total_custom"], base6 + 350, "BV em reais uma vez na extra")
    dois = _calcular(
        _payload(
            acrescimos=[_acr("Outro", 200, False), _acr("BV", 150, False), _acr("BV", 10, True)]
        )
    )
    _perto(dois["quote"]["total_1h"], b1 + 200 + 150 + 0.1 * (b1 + 200), "os dois BVs não se veem")


def c10_educamanto() -> None:
    from app.educamanto.quote_ops import _totais_contratacao

    p = {"performers": [ATOR], "coordenador_qty": 1, "event_time": "15:00", "modo_duracao": "horas"}
    with app.app_context():
        base, _m, _t = _totais_contratacao({"payload": p, "duracoes": ["1h", "4h"]}, "x.")
        com, _m, _t = _totais_contratacao(
            {
                "payload": {
                    **p,
                    "desconto_pct": 50,
                    "desconto_valor": 10,
                    "desconto_duracao": "1h",
                },
                "duracoes": ["1h", "4h"],
            },
            "x.",
        )
        _garante(base == com, f"o desconto chegou à contratação Manto: {base} × {com}")
        seis, _m, _t = _totais_contratacao(
            {"payload": {**p, "acrescimos": [_acr("Outro", 300, False)]}, "duracoes": ["6h"]}, "x."
        )
    _perto(seis["6h"], base["4h"] / 4 * 6 + 300, "contratação Manto em 6h: o R$ uma vez")


# ── 11–15 · o evento ────────────────────────────────────────────────────────────────────────────
def _orc_desconto(rotulo: str, dpct: float = 10, **extra) -> tuple[int, dict]:
    res = _calcular(
        _payload(
            client_name=f"{PREFIX}{rotulo}",
            acrescimos=[_acr("Outro", 200, False), _acr("BV", 10, True)],
            desconto_pct=dpct,
            **extra,
        )
    )
    return _salvar(res), res


def c11_prefill() -> None:
    oid, res = _orc_desconto("c11", duracao_custom=6)
    pj = _cliente("com").get(f"/api/events/new/prefill?orcamento_id={oid}").get_json()
    qq = res["quote"]
    for d in range(1, 5):
        _garante(
            pj.get(f"bruto_{d}h") == qq[f"bruto_{d}h"] and pj[f"total_{d}h"] == qq[f"total_{d}h"],
            f"prefill {d}h",
        )
    _garante(pj.get("desconto_pct") == 10, f"prefill desconto_pct {pj.get('desconto_pct')}")
    _garante(
        pj.get("total_custom") == qq["total_custom"]
        and pj.get("bruto_custom") == qq["bruto_custom"],
        "extra",
    )
    extra = pj.get("extra_por_horas") or {}
    r7 = _calcular(
        _payload(
            acrescimos=[_acr("Outro", 200, False), _acr("BV", 10, True)],
            desconto_pct=10,
            duracao_custom=7,
        )
    )["quote"]
    _garante(
        extra.get("7", {}).get("total") == r7["total_custom"],
        f"7h {extra.get('7')} ≠ {r7['total_custom']}",
    )
    _garante(extra.get("7", {}).get("bruto") == r7["bruto_custom"], "7h cheio")
    _garante("24" in extra and "4" not in extra, f"faixa do extra_por_horas: {sorted(extra)[:3]}…")
    linhas = (pj.get("acrescimos_do_orcamento") or {}).get("linhas") or []
    bv = next((linha for linha in linhas if linha.get("is_bv")), None)
    _garante(bv and bv.get("valores_final"), f"prefill sem valores_final do BV: {bv}")
    _perto(bv["valores_final"]["2"], qq["bv_2h"], "valores_final 2h = bv_2h")


def c12_evento() -> None:
    oid, res = _orc_desconto("c12", dpct=3)
    qq = res["quote"]
    eid = _criar(
        _corpo_criacao(
            f"{PREFIX}c12",
            oid,
            venda=qq["total_2h"],
            bruto=qq["bruto_2h"],
            bv_recipient=QUEM,
            bv_pix=PIX,
        )
    )
    ev = _evento(eid)
    _garante(
        q(ev["venda"]) == q(qq["total_2h"]) and q(ev["bruto"]) == q(qq["bruto_2h"]), f"evento {ev}"
    )
    bvs = [linha for linha in _linhas(eid) if linha["is_bv"]]
    _garante(len(bvs) == 1, f"BVs {bvs}")
    _perto(bvs[0]["amount_brl"], qq["bv_2h"], "BV gravado = bv_2h")
    com = _comissao(eid)
    esperado = q(
        (Decimal(str(qq["total_2h"])) - Decimal(str(bvs[0]["amount_brl"]))) * _taxa() / 100
    )
    _garante(com is not None and q(com) == esperado, f"comissão {com} ≠ {esperado}")
    # O alerta de BV pendente não acende (o BV nasceu).
    from app.calendar.orcamento_evento_ops import deduzir_duracao

    with app.app_context():
        entry = db.session.get(OrcamentoHistory, oid)
        dur, origem = deduzir_duracao(entry, bruto=qq["bruto_2h"], horas_agenda=None)
        dur_f, _o = deduzir_duracao(entry, bruto=qq["total_2h"], horas_agenda=None)
    _garante(dur == 2 and origem == "pelo valor", f"dedução pelo cheio: {dur} {origem}")
    _garante(dur_f == 2, f"dedução pelo final (bruto = final): {dur_f}")
    # PIX digitado por cima: o BV acompanha a venda digitada (outro orçamento igual — um orçamento vira um evento só,
    # a regra 1:1 da 273).
    oid2, _res2 = _orc_desconto("c12b", dpct=3)
    eid2 = _criar(
        _corpo_criacao(
            f"{PREFIX}c12b",
            oid2,
            venda=qq["pix_2h"],
            bruto=qq["bruto_2h"],
            bv_recipient=QUEM,
            bv_pix=PIX,
        )
    )
    bvs2 = [linha for linha in _linhas(eid2) if linha["is_bv"]]
    _perto(
        bvs2[0]["amount_brl"] if bvs2 else None,
        qq["bv_pix_2h"],
        "BV com o PIX digitado = bv_pix_2h",
    )
    # Desconto concedido no Comercial (só os eventos do Superadmin do verify).
    hoje = now_sp().date()
    url = f"/api/vendas/pipeline?period=custom&start={(hoje - timedelta(days=1)).isoformat()}&end={(hoje + timedelta(days=1)).isoformat()}&seller_id={estado['sa']['id']}"
    k = (_cliente("sa").get(url).get_json() or {}).get("kpis") or {}
    esperado_desc = (qq["bruto_2h"] - qq["total_2h"]) + (qq["bruto_2h"] - qq["pix_2h"])
    _perto(k.get("desconto_concedido"), esperado_desc, "desconto concedido", tol=0.02)


def c13_antigo_vira_evento() -> None:
    from app.calendar.orcamento_evento_ops import acrescimos_do_orcamento

    snap = {
        "performers": [],
        "coordenador_qty": 1,
        "nota_fiscal": False,
        "personalizado_ativo": False,
        "duracao_custom": "6",
        "event_time": "15:00",
        "fora_sp": False,
        "acrescimos": [
            {"tipo": "BV", "descricao": "", "is_percent": True, "value": 10, "is_bv": True}
        ],
    }
    with app.app_context():
        e = OrcamentoHistory(
            user_id=estado["com"]["id"],
            client_name=f"{PREFIX}c13",
            event_location=f"{PREFIX}Salão",
            event_date=(now_sp().date() + timedelta(days=60)).isoformat(),
            total_1h=Decimal("1100"),
            total_2h=Decimal("1650"),
            total_3h=Decimal("2200"),
            total_4h=Decimal("2750"),
            has_show=False,
            form_snapshot=json.dumps(snap),
            result_snapshot=json.dumps({"total_custom": 4125.0}),
        )
        db.session.add(e)
        db.session.commit()
        res = acrescimos_do_orcamento(e, 6)
        bv = [linha for linha in res["linhas"] if linha["is_bv"]]
        _garante(bv and Decimal(str(bv[0]["amount_brl"])) == Decimal("375.00"), f"6h legado: {res}")
        _garante(
            Decimal(str(res["total"])) == Decimal("4125.00"), f"total 6h legado {res['total']}"
        )
        oid = e.id
    eid = _criar(
        _corpo_criacao(f"{PREFIX}c13", oid, venda=1650, bruto=1650, bv_recipient=QUEM, bv_pix=PIX)
    )
    bvs = [linha for linha in _linhas(eid) if linha["is_bv"]]
    _garante(bvs and q(bvs[0]["amount_brl"]) == Decimal("150.00"), f"BV do legado {bvs}")


def c14_vinculo() -> None:
    oid, res = _orc_desconto("c14")
    qq = res["quote"]
    eid = _evento_sem_venda("c14")
    corpo = {
        "orcamento_history_id": oid,
        "aplicar_valores_duracao": 2,
        "bv_recipient": QUEM,
        "bv_pix": PIX,
    }
    r = _cliente("com").patch(f"/api/events/{eid}/orcamento", json=corpo)
    _garante(r.status_code == 200, f"vínculo → {r.status_code} {r.get_data(as_text=True)[:300]}")
    ev = _evento(eid)
    _garante(
        q(ev["venda"]) == q(qq["total_2h"]) and q(ev["bruto"]) == q(qq["bruto_2h"]),
        f"vínculo gravou {ev}",
    )
    bvs = [linha for linha in _linhas(eid) if linha["is_bv"]]
    _perto(bvs[0]["amount_brl"] if bvs else None, qq["bv_2h"], "BV do vínculo")
    canc = _evento_sem_venda("c14b")
    with _externo.begin() as conn:
        conn.execute(
            text("UPDATE calendar_events SET cancelled_at = now() WHERE id = :i"), {"i": canc}
        )
    r2 = _cliente("com").patch(f"/api/events/{canc}/orcamento", json={**corpo})
    _garante(r2.status_code == 409, f"vínculo em cancelado → {r2.status_code}")


def c15_rbac() -> None:
    corpo = _payload(desconto_pct=10)
    for papel in ("fin", "cast", "rev"):
        r = _cliente(papel).post("/api/orcamento/calcular", json=corpo)
        _garante(r.status_code == 403, f"{papel} → {r.status_code}")
    for papel in ("com", "sa"):
        _garante(
            _cliente(papel).post("/api/orcamento/calcular", json=corpo).status_code == 200,
            f"{papel} recusado",
        )


def c16_regressao() -> None:
    falhas = []
    for caminho, args in (
        ("specs/305-bv-do-orcamento-no-evento/verify_305.py", ["--regressao"]),
        ("specs/307-natal-papai-noel-calculadora/verify_307.py", []),
        ("specs/309-produtos-de-tabela/verify_309.py", []),
        ("specs/235-educamanto-responsabilidades/verify_235.py", []),
    ):
        p = subprocess.run(
            [sys.executable, str(REPO_ROOT / caminho), *args],
            capture_output=True,
            text=True,
            cwd=str(REPO_ROOT),
            env={**os.environ, "PYTHONUTF8": "1"},
            timeout=1800,
        )
        if p.returncode != 0:
            linhas = [
                linha
                for linha in (p.stdout or "").splitlines()
                if "FALHA" in linha or "FAIL" in linha
            ]
            falhas.append(f"{caminho}: {linhas[:3] or (p.stderr or '')[-300:]}")
    _garante(not falhas, " | ".join(falhas))


def cL_limpeza() -> None:
    with app.app_context():
        limpar()
        _garante(
            CalendarEvent.query.filter(CalendarEvent.title.like(f"{PREFIX}%")).count() == 0,
            "evento sobrou",
        )
        _garante(User.query.filter(User.email.like(f"{PREFIX}%")).count() == 0, "usuário sobrou")
        _garante(
            OrcamentoHistory.query.filter(OrcamentoHistory.client_name.like(f"{PREFIX}%")).count()
            == 0,
            "orçamento sobrou",
        )


CENARIOS = [
    ("1", "paridade com o gabarito; exceções da Q7 pela fórmula", c1_paridade),
    ("2", "desconto em % (com e sem BV) + mutação", c2_desconto_pct),
    ("3", "desconto pelo valor; o texto do %; inválidos", c3_desconto_valor),
    ("4", "a base do desconto é o total", c4_base_do_desconto),
    ("5", "PIX vale o maior (3%, 5%, 10%, 4,96%)", c5_pix),
    ("6", "mensagem e PDF", c6_mensagem_e_pdf),
    ("7", "orçamento antigo: histórico, PDF, prefill", c7_orcamento_antigo),
    ("8", "o acréscimo em R$ uma vez; sem parte fixa, o centavo de hoje", c8_acrescimo_uma_vez),
    ("9", "o BV sobre tudo; BV em reais uma vez", c9_bv_sobre_tudo),
    ("10", "EducaManto", c10_educamanto),
    ("11", "prefill", c11_prefill),
    ("12", "evento criado: cheio, venda, BV, comissão, dedução, PIX digitado", c12_evento),
    ("13", "orçamento antigo vira evento (régua e denominador de hoje)", c13_antigo_vira_evento),
    ("14", "vínculo 273", c14_vinculo),
    ("15", "DEVE FALHAR: Financeiro, Casting e Revendedor no cálculo", c15_rbac),
    ("16", "regressão 305/307/309/235", c16_regressao),
]


def main() -> int:
    for a in sys.argv[1:]:
        if a.startswith("--so="):
            OPCOES["so"] = {s.strip() for s in a.split("=", 1)[1].split(",") if s.strip()}
        elif a.startswith("--gabarito="):
            OPCOES["gabarito"] = a.split("=", 1)[1]
    if (
        os.environ.get("MANTO_SEM_THREADS") != "1"
        or "localhost" not in os.environ["DATABASE_URL"]
        and "127.0.0.1" not in os.environ["DATABASE_URL"]
    ):
        print("ambiente impróprio: MANTO_SEM_THREADS=1 e DATABASE_URL local")
        return 2
    print("── verify 313 — desconto e PIX na calculadora ──")
    try:
        preparar()
        for num, nome, fn in CENARIOS:
            if OPCOES["so"] is None or num in OPCOES["so"]:
                cenario(f"{num} · {nome}", fn)
    finally:
        cenario("L · limpeza", cL_limpeza)
    ok = sum(1 for _, passou, _ in resultados if passou)
    print(f"\n{ok}/{len(resultados)} cenários OK · chamadas ao Google: {GOOGLE['insert']}")
    return 0 if ok == len(resultados) else 1


if __name__ == "__main__":
    sys.exit(main())
