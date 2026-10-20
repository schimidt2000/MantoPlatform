"""Verificação da feature 309 — Produtos de tabela (Visita Mágica pelo preço da tabela de venda).

Cenários 1–20 da `spec.md` (seção "Verificação"). Escrito ANTES do núcleo (Princípio VIII): a primeira
rodada fica em `verify_309_primeira_falha.txt` e GRAVA o gabarito do cenário 1
(`verify_309_golden.json`: quote + mensagem + texto do PDF de payloads sem produto e sem Noel/Ajudante,
no HEAD `6356b80`), que as rodadas seguintes comparam chave a chave.

A configuração de preços REAL do `manto_local` é lida por conexão separada no início, substituída por
uma configuração de teste determinística (markup 2,6/2,5/2,45/2,4; coordenador 250/300/325/350 e
300/350/375/400 com show; `make_1` 250, `make_especial` 300; "Papai Noel" GRAVADO em 712/800/850/900 e
"Ajudante do Noel" em 423/480/510/540 para provar a inversa; SEM `produtos` para provar os padrões; faixa
`natal` da 307) e RESTAURADA no `finally`, conferida por conexão separada.

O Google é DUBLADO (insert/update/delete e o tempo de deslocamento) como no `verify_305.py`; eventos
descartáveis são R&I, criados só pela API (ou direto no banco para o vínculo 273 e o script) e apagados na
mesma rodada. Requisições correm FORA do `app.app_context()`; login só por `POST /api/auth/login` com
usuários descartáveis (prefixo `__v309_`).

Rodar contra o manto_local (PowerShell, a partir do worktree)::

    $env:DATABASE_URL = (gc .local-db-url -Raw).Trim(); $env:FLASK_ENV = "development"
    $env:MANTO_SEM_THREADS = "1"; $env:PYTHONUTF8 = "1"
    C:\\Users\\schim\\Desktop\\Manto_Platform\\.venv\\Scripts\\python.exe specs\\309-produtos-de-tabela\\verify_309.py --regressao ['--so=2,3']

Sem `--regressao` o cenário 19 (`verify_307.py --regressao`, em subprocesso — demora; ele encadeia a
305) sai como PULADO e fica FORA da contagem: o portão da feature é a rodada com a flag.
"""

from __future__ import annotations

import copy
import io
import json
import os
import subprocess
import sys
import traceback
import uuid
from collections.abc import Callable
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO_ROOT))
os.environ.setdefault("FLASK_ENV", "development")
os.environ.setdefault("MANTO_SEM_THREADS", "1")
if not os.environ.get("DATABASE_URL"):
    os.environ["DATABASE_URL"] = (REPO_ROOT / ".local-db-url").read_text(encoding="utf-8").strip()

from sqlalchemy import create_engine, text  # noqa: E402

from app import create_app, db, limiter, maps  # noqa: E402
from app.calendar import routes as cal_routes  # noqa: E402
from app.calendar import service as cal_service  # noqa: E402
from app.constants import RoleName  # noqa: E402
from app.models import CalendarEvent, EventRole, OrcamentoHistory, Role, User  # noqa: E402
from app.orcamento import quote_ops  # noqa: E402
from app.orcamento import settings as _cfg  # noqa: E402

PREFIX = "__v309_"
SENHA = "verify-309-senha"
GOLDEN = AQUI / "verify_309_golden.json"
SCRIPT = AQUI / "rebaixar_tetos_noel_309.py"
NOEL_712 = [712, 800, 850, 900]
AJUDANTE_423 = [423, 480, 510, 540]
NOEL_600 = [600, 650, 675, 700]
AJUDANTE_270 = [270, 320, 345, 370]
CHAVES_NOVAS = ("produtos", "produtos_total", "coordenadores_inclusos", "avisos")
MARCA_PRODUTO = "cachê da tabela · produto"
VISITA = "visita_magica"
VISITA_AJ = "visita_magica_ajudante"
ROTULO_VISITA = "Visita Mágica — Papai Noel"
ROTULO_VISITA_AJ = "Visita Mágica — Papai Noel + Ajudante"

app = create_app()
app.config["TESTING"] = True
limiter.enabled = False

resultados: list[tuple[str, str, str]] = []  # (nome, "OK" | "FALHA" | "PULADO", detalhe)
estado: dict = {}
_externo = create_engine(os.environ["DATABASE_URL"], future=True)


# ── dublês do Google (feature 305) ──────────────────────────────────────────────────────────────
def _fake_insert(*_a, **_k):
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


def _iguais(a, b, msg: str, tol: float = 0.011) -> None:
    _garante(a is not None and b is not None, f"{msg}: {a} ≠ {b}")
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


def _config_salva() -> dict:
    return json.loads(_no_banco("SELECT pricing_config FROM site_settings WHERE id = 1")[0][0])


def _config_de_teste(real: str | None) -> dict:
    """A tabela real com os números do espelho fixados, o Noel GRAVADO em 712 (prova a inversa) e SEM
    `produtos` (prova os padrões). `markup.show` igual ao receptivo, como em produção."""
    cfg = json.loads(real) if real else copy.deepcopy(_cfg.DEFAULTS)
    cfg["markup"] = {"receptivo": [2.6, 2.5, 2.45, 2.4], "show": [2.6, 2.5, 2.45, 2.4]}
    cfg["coordenador"] = {"false": [250, 300, 325, 350], "true": [300, 350, 375, 400]}
    cfg.setdefault("ator", {})["boneco|false|false"] = [200, 250, 275, 300]
    cfg["ator"]["cara_limpa|false|false"] = [200, 250, 275, 300]
    cfg["ator"]["cara_limpa|false|true"] = [220, 270, 295, 320]
    cfg["ator"]["cara_limpa|true|false"] = [300, 350, 375, 400]
    cfg["tecnico_som"] = [750, 800, 825, 850]
    cfg["brinde_show"] = 100
    cfg["maquiador"] = {
        "make_1": 250,
        "make_2_adicional": 50,
        "make_extra_adicional": 100,
        "make_especial": 300,
    }
    esp = cfg.setdefault("especiais", {})
    esp["Papai Noel"] = list(NOEL_712)
    esp["Ajudante do Noel"] = list(AJUDANTE_423)
    esp["Perna de Pau"] = [400, 450, 475, 500]
    cfg["especiais_excluidos"] = ["Ajudante Especial"]
    cfg["datas_especiais"] = copy.deepcopy(_cfg.DEFAULTS["datas_especiais"])
    cfg.pop("produtos", None)
    cfg.pop("produtos_estimativa", None)
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
    if noel_real not in ([float(v) for v in NOEL_600], NOEL_600):
        print(
            f"  AVISO  o espelho não tem o Papai Noel cru em 600 ({noel_real}); recarregue o dump da produção"
        )
    _gravar_config(_config_de_teste(estado["config_real"]))
    with app.app_context():
        limpar()
        for apelido, papel in (
            ("sa", RoleName.SUPERADMIN),
            ("com", RoleName.COMERCIAL),
            ("cast", RoleName.CASTING),
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


NOEL = {"type": "especial", "personagem": "Papai Noel"}
BONECO = {"type": "ator", "subtipo": "boneco"}
ATOR_SHOW = {"type": "ator", "subtipo": "cara_limpa", "show": True}
ATOR_MAKE_ESP = {"type": "ator", "subtipo": "cara_limpa", "makeup": True, "makeup_tipo": "especial"}
PROD_NOEL = {"chave": VISITA}
PROD_NOEL_AJ = {"chave": VISITA_AJ}


def _payload(
    data: str, performers: list[dict], produtos: list[dict] | None = None, hora: str = "", **extra
) -> dict:
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
    if produtos is not None:
        corpo["produtos"] = produtos
    corpo.update(extra)
    return corpo


def _calcular(corpo: dict, papel: str = "com", esperado: int = 200) -> dict:
    r = _cliente(papel).post("/api/orcamento/calcular", json=corpo)
    _garante(
        r.status_code == esperado, f"calcular → {r.status_code} {r.get_data(as_text=True)[:300]}"
    )
    return r.get_json()


def _salvar(res: dict, papel: str = "com") -> int:
    r = _cliente(papel).post("/api/orcamento/salvar", json=res)
    _garante(r.status_code == 201, f"salvar → {r.status_code} {r.get_data(as_text=True)[:200]}")
    return r.get_json()["id"]


def _linha(memoria: list[dict], tipo: str, trecho: str = "") -> dict:
    for linha in memoria:
        if linha["tipo"] == tipo and trecho in linha["label"]:
            return linha
    raise AssertionError(
        f"memória sem linha {tipo!r} contendo {trecho!r}: {[(linha['tipo'], linha['label']) for linha in memoria]}"
    )


def _invariante(memoria: list[dict], total: float, col: int = 0) -> None:
    """Σcache × markup + Σproduto + Σpos = TOTAL (a regra do hotfix 210, com a linha nova da 309)."""
    caches = sum(linha["valores"][col] for linha in memoria if linha["tipo"] == "cache")
    markup = _linha(memoria, "markup", "Markup")["valores"][col]
    produtos = sum(linha["valores"][col] for linha in memoria if linha["tipo"] == "produto")
    pos = sum(linha["valores"][col] for linha in memoria if linha["tipo"] == "pos")
    _iguais(
        round(caches * markup, 2) + produtos + pos, total, "memória não fecha com o total", tol=0.02
    )
    _iguais(_linha(memoria, "total", "TOTAL")["valores"][col], total, "linha TOTAL ≠ total")


def _texto_do_pdf(quote: dict) -> str:
    from pypdf import PdfReader

    from app.orcamento.pdf import gerar_orcamento_pdf

    with app.app_context():
        pdf = gerar_orcamento_pdf(quote)
    _garante(pdf[:4] == b"%PDF", "PDF não gerado")
    return "\n".join(p.extract_text() or "" for p in PdfReader(io.BytesIO(pdf)).pages)


def _sem_chaves_novas(quote: dict) -> dict:
    return {k: v for k, v in quote.items() if k not in CHAVES_NOVAS}


def _dia(dias: int) -> str:
    return (datetime(2026, 12, 20) + timedelta(days=dias)).date().isoformat()


# ── eventos descartáveis ────────────────────────────────────────────────────────────────────────
def _corpo_evento(
    titulo: str,
    data: str,
    *,
    orc: int | None,
    characters: list[dict],
    venda: float,
    hora: str = "15:00",
) -> dict:
    fim = f"{int(hora[:2]) + 1:02d}:{hora[3:]}"
    return {
        "title": f"{PREFIX}{titulo}",
        "event_type": "R&I",
        "date": data,
        "start": hora,
        "end": fim,
        "location": f"{PREFIX}Salão",
        "description": "",
        "needs_rehearsal": False,
        "sale_value": venda,
        "sale_value_gross": venda,
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
        "duracao": "1",
        "characters": characters,
        "orc_caches": [],
        "acrescimos": [],
        "client_pairs": [],
        "observations": [],
    }


def _criar_evento(corpo: dict, papel: str = "com") -> int:
    r = _cliente(papel).post("/api/events", json=corpo)
    _garante(
        r.status_code == 201, f"POST /api/events → {r.status_code} {r.get_data(as_text=True)[:300]}"
    )
    j = r.get_json()
    return (j.get("event") or j)["id"]


def _evento_direto(
    rotulo: str,
    data: str,
    roles: list[tuple[str, str, float | None]] | None = None,
    venda: float | None = None,
) -> int:
    """Evento criado direto no banco (vínculo 273 e script): `roles` = (nome, role_type, cache_cap)."""
    with app.app_context():
        inicio = datetime.fromisoformat(f"{data}T15:00:00")
        ev = CalendarEvent(
            title=f"{PREFIX}(R&I) {rotulo}",
            event_type="R&I",
            start_at=inicio,
            end_at=inicio + timedelta(hours=1),
            google_event_id=f"{PREFIX}{uuid.uuid4().hex[:8]}",
            source="google_calendar",
            location=f"{PREFIX}Salão",
            sale_value=Decimal(str(venda)) if venda is not None else None,
            sale_value_gross=Decimal(str(venda)) if venda is not None else None,
            seller_id=estado["sa"]["id"] if venda is not None else None,
        )
        db.session.add(ev)
        db.session.flush()
        for nome, tipo, cap in roles or []:
            db.session.add(
                EventRole(event_id=ev.id, character_name=nome, role_type=tipo, cache_cap=cap)
            )
        db.session.commit()
        return ev.id


def _roles(eid: int) -> list[dict]:
    rows = _no_banco(
        "SELECT id, character_name, role_type, cache_cap, cache_value, cache_cap_note, talent_id FROM event_roles WHERE event_id = :e ORDER BY id",
        e=eid,
    )
    return [
        {
            "id": r[0],
            "nome": r[1],
            "tipo": r[2],
            "cap": float(r[3]) if r[3] is not None else None,
            "valor": float(r[4]) if r[4] is not None else None,
            "nota": r[5] or "",
            "talento": r[6],
        }
        for r in rows
    ]


def _por_nome(roles: list[dict], nome: str) -> list[dict]:
    return [r for r in roles if r["nome"] == nome]


def _prefill(oid: int, papel: str = "com") -> dict:
    r = _cliente(papel).get(f"/api/events/new/prefill?orcamento_id={oid}")
    _garante(r.status_code == 200, f"prefill → {r.status_code}")
    return r.get_json()


def _characters_do_prefill(pre: dict) -> list[dict]:
    return [
        {
            "name": c["label"],
            "needs_makeup": bool(c.get("needs_makeup")),
            "is_singer": bool(c.get("is_singer")),
            "cache_value": None,
            "talent_id": None,
        }
        for c in pre.get("caches") or []
        if (c.get("role_type") or "character") == "character"
    ]


def _itens_do_teto(
    snap: dict, data_evento: str | None = None, horas_extra: int | None = None
) -> list[dict]:
    with app.app_context():
        return cal_routes._compute_performer_caches(
            snap, horas_extra=horas_extra, data_evento=data_evento
        )


# ── 1 · paridade (gabarito) ─────────────────────────────────────────────────────────────────────
PAYLOADS_GABARITO = {
    "boneco_20_12": _payload("2026-12-20", [BONECO]),
    "boneco_24_12": _payload("2026-12-24", [BONECO]),
    "boneco_fora_sp": _payload(
        "2026-12-20",
        [BONECO],
        fora_sp=True,
        deslocamento_responsavel="manto",
        transporte_tipo="van",
        km_ida=50,
        carretinha=False,
    ),
    "boneco_nf": _payload("2026-12-20", [BONECO], nota_fiscal=True),
    "boneco_bv": _payload(
        "2026-12-20", [BONECO], acrescimos=[{"tipo": "BV", "value": 10, "is_percent": True}]
    ),
    "perna_show_6h": _payload(
        "2026-12-20",
        [{"type": "especial", "personagem": "Perna de Pau"}, ATOR_SHOW],
        duracao_custom=6,
    ),
}


def cen_01_paridade() -> None:
    atual = {}
    for nome, corpo in PAYLOADS_GABARITO.items():
        res = _calcular(corpo)
        atual[nome] = {"quote": _sem_chaves_novas(res["quote"]), "pdf": _texto_do_pdf(res["quote"])}
    if not GOLDEN.exists():
        GOLDEN.write_text(
            json.dumps(atual, ensure_ascii=False, indent=1, sort_keys=True), encoding="utf-8"
        )
        print(
            f"         GABARITO GRAVADO em {GOLDEN.name} (HEAD atual) — as próximas rodadas comparam com ele"
        )
        return
    golden = json.loads(GOLDEN.read_text(encoding="utf-8"))
    for nome, esperado in golden.items():
        _garante(nome in atual, f"gabarito tem {nome} e a rodada não")
        atual_q = json.loads(json.dumps(atual[nome]["quote"], sort_keys=True))
        esperado_q = json.loads(json.dumps(esperado["quote"], sort_keys=True))
        diferentes = [
            k for k in sorted(set(atual_q) | set(esperado_q)) if atual_q.get(k) != esperado_q.get(k)
        ]
        _garante(not diferentes, f"{nome}: quote difere do gabarito nas chaves {diferentes}")
        _garante(atual[nome]["pdf"] == esperado["pdf"], f"{nome}: texto do PDF difere do gabarito")


# ── 2–4 · o produto na venda ────────────────────────────────────────────────────────────────────
def cen_02_produto_noel_20_12() -> None:
    res = _calcular(_payload("2026-12-20", [], [PROD_NOEL]))
    q = res["quote"]
    for d in ("1h", "2h", "3h", "4h"):
        _iguais(q[f"total_{d}"], 2500.00, f"Visita Noel 20/12 {d}")
    _garante(q.get("data_especial") is None, "20/12 não tem faixa")
    produtos = q.get("produtos")
    _garante(isinstance(produtos, list) and len(produtos) == 1, f"quote.produtos: {produtos}")
    p = produtos[0]
    _garante(p["chave"] == VISITA and p["rotulo"] == ROTULO_VISITA, f"produto aplicado: {p}")
    _iguais(p["preco_aplicado"], 2500.00, "preco_aplicado")
    _garante(p["faixa_chave"] is None and p["estimado"] is False, f"faixa/estimado: {p}")
    _garante(
        p["vagas"] == ["Papai Noel", "Coordenador", "Maquiador"], f"vagas do quote: {p['vagas']}"
    )
    _iguais(q["produtos_total"], 2500.00, "produtos_total")
    _garante(
        q["coordenadores_inclusos"] == 1,
        f"coordenadores_inclusos: {q.get('coordenadores_inclusos')}",
    )
    _garante(q["avisos"] == [], f"avisos inesperados: {q['avisos']}")
    mem = q["memoria"]
    prod = _linha(mem, "produto", ROTULO_VISITA)
    _iguais(prod["valores"][0], 2500.00, "linha do produto")
    _garante("preço de tabela" in prod["detalhe"], f"detalhe do produto: {prod['detalhe']!r}")
    _linha(mem, "subtotal", "Após produtos")
    idx = [linha["label"] for linha in mem]
    _garante(
        idx.index("= Após markup") < idx.index(ROTULO_VISITA) < idx.index("= Após produtos"),
        f"ordem da memória: {idx}",
    )
    _invariante(mem, 2500.00)
    _garante(
        q["show_1h"] and not q["show_2h"] and not q["show_3h"] and not q["show_4h"],
        "só produto = só a coluna 1h",
    )
    _garante(q["total_custom"] is None, "só produto não tem régua")
    msg = q["message"]
    _garante(ROTULO_VISITA in msg and "R$ 2.500,00" in msg, "mensagem sem o produto")
    _garante(
        "2 horas" not in msg and "4 horas" not in msg,
        "mensagem de só-produto lista várias durações",
    )
    _garante("R$ 2.375,00" in msg, "PIX único da Visita (2.500 × 0,95)")
    _garante("Papai Noel" in q["team_lines"], f"equipe sem o Noel do produto: {q['team_lines']}")
    pdf = _texto_do_pdf(q)
    _garante("Visita M" in pdf and "2.500,00" in pdf, "PDF sem o produto")
    _garante("4 horas" not in pdf, "PDF de só-produto lista 4 horas")
    snap = res["snapshot"]
    _garante(
        snap["produtos"][0]["chave"] == VISITA and snap["produtos"][0]["preco_aplicado"] == 2500.0,
        f"snapshot.produtos: {snap['produtos']}",
    )
    vagas = snap["produtos"][0]["vagas"]
    _garante(
        [v["label"] for v in vagas] == ["Papai Noel", "Coordenador", "Maquiador"],
        f"vagas congeladas: {vagas}",
    )
    _garante(
        vagas[0]["tipo"] == "especial"
        and vagas[0]["needs_makeup"] is True
        and vagas[0]["cache"] is None,
        f"vaga do Noel: {vagas[0]}",
    )
    _iguais(snap["produtos_total"], 2500.00, "snapshot.produtos_total")


def cen_03_faixa_e_ajudante() -> None:
    q = _calcular(_payload("2026-12-24", [], [PROD_NOEL]))["quote"]
    _iguais(q["total_1h"], 5000.00, "Visita Noel 24/12")
    _garante(
        q["produtos"][0]["faixa_chave"] == "natal" and q["produtos"][0]["estimado"] is False,
        f"faixa: {q['produtos'][0]}",
    )
    _garante(
        (q.get("data_especial") or {}).get("chave") == "natal",
        "data_especial da 307 continua no quote",
    )
    q = _calcular(_payload("2026-12-20", [], [PROD_NOEL_AJ]))["quote"]
    _iguais(q["total_1h"], 3600.00, "Noel + Ajudante 20/12")
    _garante(
        q["produtos"][0]["vagas"] == ["Papai Noel", "Ajudante do Noel", "Coordenador", "Maquiador"],
        "vagas do produto com ajudante",
    )
    _garante("Ajudante do Noel" in q["team_lines"], "equipe sem o Ajudante")
    q = _calcular(_payload("2026-12-25", [], [PROD_NOEL_AJ]))["quote"]
    _iguais(q["total_1h"], 6500.00, "Noel + Ajudante 25/12")
    _garante(not q["show_2h"] and not q["show_4h"], "só produto → só 1h")


def cen_04_noturno_embutido() -> None:
    q = _calcular(_payload("2026-12-20", [], [PROD_NOEL], hora="20:00"))["quote"]
    _iguais(q["total_1h"], 2500.00, "Visita às 20h não soma noturno")
    _garante(
        not any(
            linha["tipo"] == "pos" and "noturno" in linha["label"].lower() for linha in q["memoria"]
        ),
        "noturno apareceu na memória da Visita",
    )
    q = _calcular(_payload("2026-12-20", [BONECO], [PROD_NOEL], hora="20:00"))["quote"]
    # boneco 200 × 2,6 + 2.500 + noturno só do boneco (o coordenador é o do produto): 3.070
    _iguais(q["total_1h"], 3070.00, "produto + boneco às 20h")
    _iguais(_linha(q["memoria"], "pos", "noturno")["valores"][0], 50.00, "noturno só do boneco")
    _invariante(q["memoria"], 3070.00)


# ── 5–7 · convivência com avulsos ───────────────────────────────────────────────────────────────
def cen_05_produto_mais_avulsos() -> None:
    q = _calcular(_payload("2026-12-20", [BONECO], [PROD_NOEL]))["quote"]
    _iguais(q["total_1h"], 200 * 2.6 + 2500, "1h = boneco × markup + produto")
    _iguais(q["total_2h"], 250 * 2.5 + 2500, "2h")
    _iguais(q["total_3h"], 275 * 2.45 + 2500, "3h")
    _iguais(q["total_4h"], 300 * 2.4 + 2500, "4h")
    _garante(q["coordenadores_inclusos"] == 1, "coordenador incluso")
    coord = _linha(q["memoria"], "cache", "Coordenador")
    _iguais(coord["valores"][0], 0, "nenhum coordenador cobrado fora do produto")
    _garante(q["show_4h"], "com avulso as 4 colunas voltam")
    for col in range(4):
        _invariante(q["memoria"], q[f"total_{['1h', '2h', '3h', '4h'][col]}"], col)

    res2 = _calcular(_payload("2026-12-20", [], [PROD_NOEL, PROD_NOEL]))
    _iguais(res2["quote"]["total_1h"], 5000.00, "dois produtos")
    _garante(res2["quote"]["coordenadores_inclusos"] == 2, "dois coordenadores inclusos")
    itens = _itens_do_teto(res2["snapshot"])
    _garante(len([i for i in itens if i["label"] == "Papai Noel"]) == 2, "dois Noéis no teto")
    _garante(
        len([i for i in itens if i["label"] == "Coordenador"]) == 2, "dois Coordenadores no teto"
    )
    maqs = [i for i in itens if i["label"] == "Maquiador"]
    _garante(len(maqs) == 1, f"UM Maquiador por orçamento: {len(maqs)}")
    _iguais(maqs[0]["cache_1h"], 300, "teto do Maquiador com 2 makes = make_1 + make_2_adicional")

    res3 = _calcular(_payload("2026-12-20", [ATOR_SHOW], [PROD_NOEL]))
    itens = _itens_do_teto(res3["snapshot"])
    coords = [i for i in itens if i["label"] == "Coordenador"]
    _garante(
        coords and coords[0]["cache_1h"] == 250,
        f"coordenador do produto fica em 250 com show avulso: {coords}",
    )

    q4 = _calcular(_payload("2026-12-20", [ATOR_MAKE_ESP], [PROD_NOEL]))["quote"]
    # incremento: calcular_maquiador(1 comum do produto + 0, 1 especial) − calcular_maquiador(1, 0) = 300 → × 1,5 = 450
    _iguais(
        _linha(q4["memoria"], "pos", "Maquiador")["valores"][0],
        450.00,
        "make do avulso cobra só o incremento",
    )
    _invariante(q4["memoria"], q4["total_1h"])


def cen_06_fora_sp_nf_bv_pix() -> None:
    from app.orcamento.transport import calcular_van

    res = _calcular(
        _payload(
            "2026-12-20",
            [],
            [PROD_NOEL],
            fora_sp=True,
            deslocamento_responsavel="manto",
            transporte_tipo="van",
            km_ida=50,
            carretinha=False,
        )
    )
    with app.app_context():
        tb = calcular_van(2, 50.0, False, False)  # Noel + coordenador do produto
    _iguais(
        res["quote"]["total_1h"],
        round(2500 + tb["total"], 2),
        "fora de SP soma por cima do produto",
    )
    q = _calcular(_payload("2026-12-20", [], [PROD_NOEL], nota_fiscal=True))["quote"]
    _iguais(q["total_1h"], round(2500 / 0.84, 2), "NF sobre o produto")
    res = _calcular(
        _payload(
            "2026-12-20",
            [],
            [PROD_NOEL],
            acrescimos=[{"tipo": "BV", "value": 10, "is_percent": True}],
        )
    )
    _iguais(res["quote"]["total_1h"], 2750.00, "BV 10% sobre o produto")
    _iguais(res["snapshot"]["acrescimos"][0]["valores_brl"][0], 250.00, "valores_brl do BV (305)")
    _garante(
        "R$ 2.375,00" in _calcular(_payload("2026-12-20", [], [PROD_NOEL]))["quote"]["message"],
        "PIX −5% sobre o total com produto",
    )


def cen_07_regua_e_personalizado() -> None:
    from app.calendar.orcamento_evento_ops import _total_da_duracao

    def _conferir(corpo: dict, esperado: float, rotulo: str) -> None:
        res = _calcular(corpo)
        _iguais(res["quote"]["total_custom"], esperado, f"{rotulo}: venda")
        oid = _salvar(res)
        pre = _prefill(oid)
        _iguais(pre["total_custom"], esperado, f"{rotulo}: prefill")
        with app.app_context():
            entry = db.session.get(OrcamentoHistory, oid)
            _iguais(float(_total_da_duracao(entry, 6)), esperado, f"{rotulo}: _total_da_duracao")

    # boneco 4h = 300 × 2,4 = 720; régua: (720 ÷ 4 × 6) + 2.500 = 3.580 — o produto não escala
    _conferir(_payload("2026-12-20", [BONECO], [PROD_NOEL], duracao_custom=6), 3580.00, "6h")
    _conferir(
        _payload("2026-12-20", [BONECO], [PROD_NOEL], duracao_custom=6, nota_fiscal=True),
        round(3580 / 0.84, 2),
        "6h com NF",
    )
    _conferir(
        _payload(
            "2026-12-20",
            [BONECO],
            [PROD_NOEL],
            duracao_custom=6,
            acrescimos=[{"tipo": "BV", "value": 10, "is_percent": True}],
        ),
        3938.00,
        "6h com BV 10%",
    )

    q = _calcular(
        _payload(
            "2026-12-20",
            [BONECO],
            [PROD_NOEL],
            personalizado=True,
            personalizado_criterio="valor_final",
            cust_valor_1h="3000",
            cust_valor_2h="3000",
            cust_valor_3h="3000",
            cust_valor_4h="3000",
        )
    )["quote"]
    _iguais(q["total_1h"], 3000.00, "valor final vence")
    _garante(
        not any(linha["tipo"] == "produto" for linha in q["memoria"]),
        "linha do produto saiu no valor final",
    )
    _garante(
        not any("Após produtos" in linha["label"] for linha in q["memoria"]),
        "subtotal do produto saiu no valor final",
    )
    _iguais(_linha(q["memoria"], "total", "TOTAL")["valores"][0], 3000.00, "TOTAL = digitado")
    _garante(
        q["produtos"] and q["produtos"][0]["chave"] == VISITA,
        "quote.produtos continua no personalizado (afirma o produto para o teto)",
    )

    q = _calcular(
        _payload(
            "2026-12-20",
            [BONECO],
            [PROD_NOEL],
            personalizado=True,
            personalizado_criterio="multiplicador",
            cust_mult_1h="2",
            cust_mult_2h="2",
            cust_mult_3h="2",
            cust_mult_4h="2",
        )
    )["quote"]
    _iguais(q["total_1h"], 200 * 2 + 2500, "multiplicador não multiplica o produto")
    _calcular(
        _payload(
            "2026-12-20",
            [BONECO],
            [PROD_NOEL],
            personalizado=True,
            personalizado_criterio="multiplicador",
            cust_mult_1h="0",
            cust_mult_2h="0",
            cust_mult_3h="0",
            cust_mult_4h="0",
        ),
        esperado=400,
    )


# ── 8–10 · teto das vagas ───────────────────────────────────────────────────────────────────────
def cen_08_teto() -> None:
    snap = _calcular(_payload("2026-12-20", [BONECO], [PROD_NOEL_AJ]))["snapshot"]
    itens = _itens_do_teto(snap)
    labels = [i["label"] for i in itens]
    _garante(
        labels[:2] == ["Papai Noel", "Ajudante do Noel"], f"vagas do produto primeiro: {labels}"
    )
    _garante(labels[2] == "Boneco", f"avulsos depois do produto: {labels}")
    _garante(
        labels[-2:] == ["Coordenador", "Maquiador"] or labels[-1] == "Maquiador",
        f"extras no fim: {labels}",
    )
    noel, aju = itens[0], itens[1]
    for h in ("1h", "2h", "3h", "4h"):
        _iguais(noel[f"cache_{h}"], 600, f"Noel flat {h}")
        _iguais(aju[f"cache_{h}"], 270, f"Ajudante flat {h}")
    _garante(
        noel.get("origem") == "produto" and noel.get("produto_chave") == VISITA_AJ,
        f"origem do item: {noel}",
    )
    _garante(
        noel["needs_makeup"] is True and noel["role_type"] == "character", f"flags do Noel: {noel}"
    )
    _garante(
        MARCA_PRODUTO in noel["cap_notes"]["cache_1h"],
        f"cap_note: {noel['cap_notes']['cache_1h']!r}",
    )
    coords = [i for i in itens if i["label"] == "Coordenador"]
    _garante(
        len(coords) == 1 and coords[0]["cache_1h"] == 250,
        f"coordenador do produto 250, nenhum da fórmula: {coords}",
    )
    _garante(MARCA_PRODUTO in coords[0]["cap_notes"]["cache_1h"], "nota do coordenador do produto")
    maq = [i for i in itens if i["label"] == "Maquiador"]
    _garante(len(maq) == 1 and maq[0]["cache_1h"] == 250, f"Maquiador único 250: {maq}")

    itens24 = _itens_do_teto(snap, data_evento="2026-12-24")
    _iguais(itens24[0]["cache_1h"], 1000, "Noel na faixa pela data do EVENTO")
    _iguais(itens24[1]["cache_1h"], 650, "Ajudante na faixa")
    _iguais(
        [i for i in itens24 if i["label"] == "Coordenador"][0]["cache_1h"],
        500,
        "coordenador da faixa",
    )
    _garante("Véspera e Natal" in itens24[0]["cap_notes"]["cache_1h"], "nota cita a faixa")

    regua = _itens_do_teto(snap, horas_extra=6)
    _iguais(regua[0]["cache_custom"], 600, "régua não escala a vaga do produto")
    _garante(regua[2]["cache_custom"] > 300, "a régua continua escalando o avulso")

    noturno = _itens_do_teto({**snap, "event_time": "20:00"})
    _iguais(noturno[0]["cache_1h"], 600, "noturno embutido: teto do Noel sem +50")
    _iguais(noturno[2]["cache_1h"], 250, "boneco avulso ganha +50 no teto")

    # Label de especial que não existe na tabela → sem teto, nunca 0 nem piso.
    snap_x = copy.deepcopy(snap)
    snap_x["produtos"][0]["vagas"][0]["label"] = "Inexistente 309"
    item = _itens_do_teto(snap_x, data_evento="2026-12-24")[0]
    _garante(
        item["cache_1h"] is None and item["label"] == "Inexistente 309",
        f"label desconhecido: {item}",
    )
    _garante("tabela" in item["cap_notes"]["cache_1h"], "nota explica a falta de teto")


def cen_09_prefill_criacao_vinculo() -> None:
    res = _calcular(_payload("2026-12-20", [], [PROD_NOEL_AJ]))
    oid = _salvar(res)
    pre = _prefill(oid)
    caches = pre["caches"]
    _garante(
        [c["label"] for c in caches][:2] == ["Papai Noel", "Ajudante do Noel"],
        f"prefill: {[c['label'] for c in caches]}",
    )
    _iguais(caches[0]["cache_1h"], 600, "prefill Noel 600")
    _iguais(pre["total_1h"], 3600.00, "prefill total 1h")

    eid = _criar_evento(
        _corpo_evento(
            "criacao", "2026-12-20", orc=oid, characters=_characters_do_prefill(pre), venda=3600
        )
    )
    roles = _roles(eid)
    noel = _por_nome(roles, "Papai Noel")
    _garante(
        len(noel) == 1 and noel[0]["cap"] == 600 and noel[0]["valor"] is None,
        f"vaga do Noel na criação: {noel}",
    )
    _garante(MARCA_PRODUTO in noel[0]["nota"], f"nota da vaga: {noel[0]['nota']!r}")
    aju = _por_nome(roles, "Ajudante do Noel")
    _garante(len(aju) == 1 and aju[0]["cap"] == 270, f"Ajudante: {aju}")
    coords = _por_nome(roles, "Coordenador")
    _garante(
        len(coords) == 1 and coords[0]["cap"] == 250 and coords[0]["tipo"] == "extra",
        f"Coordenador: {coords}",
    )
    maq = _por_nome(roles, "Maquiador")
    _garante(len(maq) == 1 and maq[0]["cap"] == 250, f"Maquiador: {maq}")
    estado["eid_criacao"] = eid
    estado["role_noel"] = noel[0]["id"]

    # Dois produtos → 2 Noéis, 2 Coordenadores, UM Maquiador (300) também na criação.
    res2 = _calcular(_payload("2026-12-20", [], [PROD_NOEL, PROD_NOEL]))
    oid2 = _salvar(res2)
    eid2 = _criar_evento(
        _corpo_evento(
            "criacao2",
            "2026-12-20",
            orc=oid2,
            characters=_characters_do_prefill(_prefill(oid2)),
            venda=5000,
        )
    )
    roles2 = _roles(eid2)
    _garante(len(_por_nome(roles2, "Papai Noel")) == 2, "dois Noéis")
    _garante(len(_por_nome(roles2, "Coordenador")) == 2, "dois Coordenadores")
    maq2 = _por_nome(roles2, "Maquiador")
    _garante(len(maq2) == 1 and maq2[0]["cap"] == 300, f"UM Maquiador 300: {maq2}")

    # 24/12: a data do EVENTO manda (orçamento de 20/12 vinculado a evento de 24/12).
    eid3 = _evento_direto(
        "vinculo",
        "2026-12-24",
        roles=[("Papai Noel", "character", None), ("Ajudante do Noel", "character", None)],
    )
    r = _cliente("com").patch(f"/api/events/{eid3}/orcamento", json={"orcamento_history_id": oid})
    _garante(
        r.status_code == 200, f"vínculo 273 → {r.status_code} {r.get_data(as_text=True)[:200]}"
    )
    roles3 = _roles(eid3)
    _garante(
        _por_nome(roles3, "Papai Noel")[0]["cap"] == 1000,
        f"vínculo em 24/12: Noel {_por_nome(roles3, 'Papai Noel')}",
    )
    _garante(_por_nome(roles3, "Ajudante do Noel")[0]["cap"] == 650, "vínculo: Ajudante 650")
    _garante(
        _por_nome(roles3, "Coordenador") and _por_nome(roles3, "Coordenador")[0]["cap"] == 500,
        f"vínculo cria Coordenador 500: {roles3}",
    )
    _garante(
        len(_por_nome(roles3, "Maquiador")) == 1
        and _por_nome(roles3, "Maquiador")[0]["cap"] == 250,
        "vínculo cria Maquiador 250",
    )


def cen_10_casting_rebaixa() -> None:
    rid = estado.get("role_noel")
    _garante(rid is not None, "cenário 9 não criou a vaga do Noel")
    r = _cliente("cast").post(f"/api/roles/{rid}/assign", json={"cache_value": 900})
    _garante(
        r.status_code == 200, f"assign casting → {r.status_code} {r.get_data(as_text=True)[:200]}"
    )
    _iguais(
        _roles(estado["eid_criacao"])[0]["valor"]
        if False
        else [x for x in _roles(estado["eid_criacao"]) if x["id"] == rid][0]["valor"],
        600,
        "casting 900 → 600 (teto)",
    )
    r = _cliente("sa").post(f"/api/roles/{rid}/assign", json={"cache_value": 900})
    _garante(r.status_code == 200, f"assign superadmin → {r.status_code}")
    _iguais(
        [x for x in _roles(estado["eid_criacao"]) if x["id"] == rid][0]["valor"],
        900,
        "superadmin passa do teto",
    )


# ── 11–12 · migração e avulsos ──────────────────────────────────────────────────────────────────
def cen_11_migracao() -> None:
    base = _config_de_teste(estado["config_real"])
    m = _cfg._migrate(copy.deepcopy(base))
    _garante(m["especiais"]["Papai Noel"] == NOEL_600, f"712 → 600: {m['especiais']['Papai Noel']}")
    _garante(
        m["especiais"]["Ajudante do Noel"] == AJUDANTE_270,
        f"423 → 270: {m['especiais']['Ajudante do Noel']}",
    )
    _garante(
        m["produtos"][VISITA]["preco"] == 2500
        and m["produtos"][VISITA_AJ]["por_faixa"]["natal"]["preco"] == 6500,
        "produtos padrão injetados",
    )
    _garante(
        m["produtos_estimativa"] == {"fator_cache": 2.0, "markup": 3.0},
        f"estimativa padrão: {m.get('produtos_estimativa')}",
    )
    _garante(
        [v["label"] for v in m["produtos"][VISITA_AJ]["vagas"]]
        == ["Papai Noel", "Ajudante do Noel", "Coordenador", "Maquiador"],
        "vagas do padrão",
    )

    editado = copy.deepcopy(base)
    editado["especiais"]["Papai Noel"] = [650, 700, 725, 750]
    _garante(
        _cfg._migrate(editado)["especiais"]["Papai Noel"] == [650, 700, 725, 750],
        "valor editado intocado",
    )
    cru = copy.deepcopy(base)
    cru["especiais"]["Papai Noel"] = list(NOEL_600)
    _garante(
        _cfg._migrate(cru)["especiais"]["Papai Noel"] == NOEL_600,
        "600 NÃO vira 712 (troca da 307 removida)",
    )

    for ruim in (None, [], "x"):
        cfg = copy.deepcopy(base)
        cfg["produtos"] = ruim
        m = _cfg._migrate(cfg)
        _garante(VISITA in m["produtos"], f"bloco malformado {ruim!r} não voltou aos padrões")
    cfg = copy.deepcopy(base)
    cfg["produtos"] = {
        "sem_vagas": {"rotulo": "x", "preco": 100},
        "preco_texto": {
            "rotulo": "x",
            "preco": "abc",
            "vagas": [{"label": "A", "tipo": "ator", "cache": None}],
        },
        "ok309": {
            "rotulo": "Ok",
            "descricao": "",
            "ativo": True,
            "preco": 900,
            "por_faixa": {"inexistente": {"preco": 1}},
            "vagas": [
                {"label": "qualquer", "tipo": "coordenador", "cache": None, "needs_makeup": True},
                "lixo",
            ],
            "inclui_noturno": True,
        },
    }
    m = _cfg._migrate(cfg)
    _garante(
        "sem_vagas" not in m["produtos"] and "preco_texto" not in m["produtos"],
        f"produtos malformados sobraram: {list(m['produtos'])}",
    )
    ok = m["produtos"]["ok309"]
    _garante(
        ok["por_faixa"] == {} and len(ok["vagas"]) == 1,
        f"faixa inexistente e vaga lixo descartadas: {ok}",
    )
    _garante(
        ok["vagas"][0]["label"] == "Coordenador" and ok["vagas"][0]["needs_makeup"] is False,
        f"label forçado e make só de especial/ator: {ok['vagas'][0]}",
    )
    _garante(m["markup"]["receptivo"][0] == 2.6, "tabela real preservada")

    with app.app_context():
        vivo = _cfg.load()
    _garante(vivo["especiais"]["Papai Noel"] == NOEL_600, "load() real: Noel 600")
    _garante(VISITA in vivo["produtos"], "load() real tem os produtos")


def cen_12_avulsos() -> None:
    q = _calcular(_payload("2026-12-20", [NOEL]))["quote"]
    _iguais(q["total_1h"], 2210.00, "Noel avulso 20/12 = (600 + 250) × 2,6")
    _garante(
        any("use o produto" in a.lower() for a in q["avisos"]), f"aviso do produto: {q['avisos']}"
    )
    _garante(
        q["produtos"] == [] and q["produtos_total"] == 0 and q["coordenadores_inclusos"] == 0,
        "chaves novas sempre presentes, vazias",
    )
    q = _calcular(_payload("2026-12-24", [NOEL]))["quote"]
    _iguais(q["total_1h"], 5010.00, "Noel avulso 24/12 segue a faixa da 307")
    q = _calcular(_payload("2026-12-20", [NOEL], [PROD_NOEL]))["quote"]
    _garante(
        not any("use o produto" in a.lower() for a in q["avisos"]),
        "com produto no orçamento o aviso não aparece",
    )


# ── 13–15 · configuração ────────────────────────────────────────────────────────────────────────
def _produto(**mudar) -> dict:
    p = {
        "rotulo": f"{PREFIX}Produto",
        "descricao": "teste",
        "ativo": True,
        "preco": 1000.0,
        "por_faixa": {"natal": {"preco": 2000.0}},
        "vagas": [
            {"label": "Papai Noel", "tipo": "especial", "cache": None, "needs_makeup": True},
            {"label": "Coordenador", "tipo": "coordenador", "cache": None, "needs_makeup": False},
        ],
        "inclui_noturno": True,
    }
    p.update(mudar)
    return p


def _bloco_produtos(extra: dict | None = None, estimativa: dict | None = None) -> dict:
    with app.app_context():
        atuais = _cfg.load()["produtos"]
    bloco = {"produtos": {**copy.deepcopy(atuais), **(extra or {})}}
    if estimativa is not None:
        bloco["produtos_estimativa"] = estimativa
    return bloco


def _recusa(sa, corpo: dict, rotulo: str, prefixo: str) -> None:
    r = sa.post("/api/orcamento/settings", json=corpo)
    _garante(r.status_code == 400, f"{rotulo} → {r.status_code} {r.get_data(as_text=True)[:200]}")
    campos = _erro(r).get("fields") or {}
    _garante(
        any(k.startswith(prefixo) for k in campos), f"{rotulo}: fields sem {prefixo!r}: {campos}"
    )


def cen_13_salvar_produtos() -> None:
    sa = _cliente("sa")
    chave = "teste309"
    r = sa.post("/api/orcamento/settings", json=_bloco_produtos({chave: _produto()}))
    _garante(
        r.status_code == 200, f"salvar produto → {r.status_code} {r.get_data(as_text=True)[:300]}"
    )
    salvo = _config_salva()["produtos"].get(chave)
    _garante(
        salvo and salvo["preco"] == 1000.0 and salvo["vagas"][1]["label"] == "Coordenador",
        f"persistido (conexão separada): {salvo}",
    )
    opc = sa.get("/api/orcamento/opcoes").get_json()["settings"]
    _garante(
        chave in opc["produtos"] and opc["produtos_estimativa"]["markup"] == 3.0,
        "/opcoes devolve produtos e estimativa",
    )
    _iguais(
        _calcular(_payload("2026-12-20", [], [{"chave": chave}]))["quote"]["total_1h"],
        1000.00,
        "produto novo vende pelo preço salvo",
    )

    _recusa(
        sa, _bloco_produtos({chave: _produto(preco=0)}), "preço zero", f"produtos.{chave}.preco"
    )
    _recusa(
        sa,
        _bloco_produtos({"Chave Ruim": _produto()}),
        "chave fora do padrão",
        "produtos.Chave Ruim",
    )
    _recusa(
        sa,
        _bloco_produtos(
            {chave: _produto(vagas=[{"label": "", "tipo": "especial", "cache": None}])}
        ),
        "vaga sem label",
        f"produtos.{chave}.vagas.0.label",
    )
    _recusa(
        sa,
        _bloco_produtos({chave: _produto(vagas=[{"label": "DJ", "tipo": "dj", "cache": None}])}),
        "tipo desconhecido",
        f"produtos.{chave}.vagas.0.tipo",
    )
    _recusa(
        sa,
        _bloco_produtos(
            {chave: _produto(vagas=[{"label": "Papai Noel", "tipo": "especial", "cache": 0}])}
        ),
        "cachê zero",
        f"produtos.{chave}.vagas.0.cache",
    )
    _recusa(
        sa,
        _bloco_produtos({chave: _produto(descricao="x" * 121)}),
        "descrição longa",
        f"produtos.{chave}.descricao",
    )
    _recusa(
        sa,
        _bloco_produtos(estimativa={"fator_cache": 2.0, "markup": 9}),
        "markup da estimativa fora de [1, 6]",
        "produtos_estimativa.markup",
    )
    _garante(
        _config_salva()["produtos"][chave]["preco"] == 1000.0, "corpo inválido não gravou nada"
    )

    r = sa.post(
        "/api/orcamento/settings",
        json=_bloco_produtos(
            {chave: _produto(por_faixa={"natal": {"preco": 2000.0}, "pascoa": {"preco": 1.0}})}
        ),
    )
    _garante(r.status_code == 200, f"faixa órfã não é 400 → {r.status_code}")
    _garante(
        any("pascoa" in a for a in (r.get_json().get("avisos") or [])),
        f"aviso da faixa órfã: {r.get_json().get('avisos')}",
    )
    _garante(
        "pascoa" not in _config_salva()["produtos"][chave]["por_faixa"], "faixa órfã descartada"
    )

    # Chave ausente no corpo mantém o salvo (tela aberta desde antes do deploy).
    r = sa.post("/api/orcamento/settings", json={"brinde_show": 100})
    _garante(
        r.status_code == 200 and chave in _config_salva()["produtos"],
        "corpo sem `produtos` apagou os produtos",
    )
    estado["chave_teste"] = chave


def cen_14_inativo_e_apagado() -> None:
    sa = _cliente("sa")
    chave = estado.get("chave_teste") or "teste309"
    res = _calcular(_payload("2026-12-20", [], [{"chave": chave}]))
    snap = res["snapshot"]
    r = sa.post("/api/orcamento/settings", json=_bloco_produtos({chave: _produto(ativo=False)}))
    _garante(r.status_code == 200, "desligar produto")
    _iguais(
        _calcular(snap)["quote"]["total_1h"],
        1000.00,
        "produto inativo continua resolvendo snapshot antigo",
    )
    bloco = _bloco_produtos()
    bloco["produtos"].pop(chave, None)
    r = sa.post("/api/orcamento/settings", json=bloco)
    _garante(r.status_code == 200, "remover produto")
    r = _cliente("com").post("/api/orcamento/calcular", json=snap)
    _garante(
        r.status_code == 400 and "produtos" in (_erro(r).get("fields") or {}),
        f"produto apagado na venda → {r.status_code} {_erro(r)}",
    )
    itens = _itens_do_teto(snap)
    _garante(
        itens and itens[0]["label"] == "Papai Noel" and itens[0]["cache_1h"] is None,
        f"vaga congelada sem teto: {itens[:1]}",
    )
    _garante(
        "não está mais na tabela" in itens[0]["cap_notes"]["cache_1h"], "nota do prefill explica"
    )


def cen_15_estimativa() -> None:
    sa = _cliente("sa")
    chave = "estim309"
    r = sa.post(
        "/api/orcamento/settings",
        json=_bloco_produtos(
            {
                chave: _produto(
                    rotulo=f"{PREFIX}Sem preço de Natal",
                    preco=2500.0,
                    por_faixa={},
                    vagas=[
                        {
                            "label": "Papai Noel",
                            "tipo": "especial",
                            "cache": None,
                            "needs_makeup": True,
                        },
                        {
                            "label": "Coordenador",
                            "tipo": "coordenador",
                            "cache": None,
                            "needs_makeup": False,
                        },
                        {
                            "label": "Maquiador",
                            "tipo": "maquiador",
                            "cache": None,
                            "needs_makeup": False,
                        },
                    ],
                )
            }
        ),
    )
    _garante(r.status_code == 200, f"produto sem faixa → {r.status_code}")
    res = _calcular(_payload("2026-12-24", [], [{"chave": chave}]))
    q = res["quote"]
    _iguais(q["total_1h"], 6600.00, "estimativa = (600 + 250 + 250) × 2,0 × 3,0")
    p = q["produtos"][0]
    _garante(p["estimado"] is True and p["faixa_chave"] == "natal", f"estimado: {p}")
    _garante(
        any("ESTIMADO" in a and "2" in a and "3" in a for a in q["avisos"]),
        f"aviso da estimativa com os fatores: {q['avisos']}",
    )
    _garante(
        "estimad" in _linha(q["memoria"], "produto", "Sem preço")["detalhe"].lower(),
        "linha da memória marca a estimativa",
    )
    _garante("(estimativa)" in q["message"], "mensagem marca a estimativa")
    _garante("estimativa" in _texto_do_pdf(q).lower(), "PDF marca a estimativa")
    itens = _itens_do_teto(res["snapshot"], data_evento="2026-12-24")
    _iguais(itens[0]["cache_1h"], 1000, "teto do Noel pela faixa, não pela estimativa")
    _iguais(
        [i for i in itens if i["label"] == "Coordenador"][0]["cache_1h"],
        500,
        "coordenador pela faixa",
    )
    _iguais(
        [i for i in itens if i["label"] == "Maquiador"][0]["cache_1h"], 250, "maquiador pela tabela"
    )
    bloco = _bloco_produtos()
    bloco["produtos"].pop(chave, None)
    sa.post("/api/orcamento/settings", json=bloco)


# ── 16–17 · neutralidade e permissão ────────────────────────────────────────────────────────────
def cen_16_educamanto_neutro() -> None:
    from app.educamanto.quote_ops import _totais_contratacao

    with app.app_context():
        com_prod = quote_ops.calculate_quote(_payload("2026-12-20", [BONECO], [PROD_NOEL]))[
            "quote"
        ]["total_1h"]
        sem_prod = quote_ops.calculate_quote(_payload("2026-12-20", [BONECO]))["quote"]["total_1h"]
    _garante(
        com_prod != sem_prod, "o produto precisa estar ativo na venda para o cenário fazer sentido"
    )

    def totais(payload: dict) -> dict:
        with app.app_context():
            return _totais_contratacao({"payload": payload, "duracoes": ["1h"]}, "x")[0]

    _iguais(
        totais(_payload("2026-12-20", [BONECO], [PROD_NOEL]))["1h"],
        totais(_payload("2026-12-20", [BONECO]))["1h"],
        "EducaManto ignora produtos",
    )
    _iguais(
        totais(_payload("2026-12-20", [BONECO]))["1h"],
        (200 + 250) * 2.6,
        "contratação Manto no preço normal",
    )


def cen_17_comercial_nao_edita() -> None:
    r = _cliente("com").post("/api/orcamento/settings", json=_bloco_produtos())
    _garante(r.status_code == 403, f"COMERCIAL devia levar 403, levou {r.status_code}")


# ── 18 · script dos tetos antigos ───────────────────────────────────────────────────────────────
def _rodar_script(*args: str) -> str:
    _garante(SCRIPT.exists(), f"script inexistente: {SCRIPT.name}")
    r = subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        cwd=str(REPO_ROOT),
        env={**os.environ, "PYTHONUTF8": "1", "MANTO_SEM_THREADS": "1"},
        timeout=600,
    )
    _garante(r.returncode == 0, f"script falhou: {(r.stderr or r.stdout)[-600:]}")
    return r.stdout


def cen_18_script_tetos() -> None:
    eid = _evento_direto(
        "script",
        "2026-12-18",
        roles=[
            ("Papai Noel", "character", 712),
            ("Ajudante do Noel", "character", 423),
            ("Noel 2", "character", 712),
            ("Papai Noel", "character", 712),
            ("Coordenador", "extra", 250),
        ],
    )
    roles = _roles(eid)
    com_valor = [r for r in roles if r["nome"] == "Papai Noel"][1]["id"]
    with app.app_context():
        role = db.session.get(EventRole, com_valor)
        role.cache_value = Decimal("712")
        db.session.commit()
    saida = _rodar_script()
    _garante(
        "Noel 2" in saida and "conferir" in saida.lower(),
        "dry-run lista a vaga de nome diferente para conferir à mão",
    )
    _garante(_por_nome(_roles(eid), "Papai Noel")[0]["cap"] == 712, "dry-run não grava")
    saida = _rodar_script("--execute")
    depois = _roles(eid)
    noeis = _por_nome(depois, "Papai Noel")
    sem_valor = [r for r in noeis if r["valor"] is None][0]
    com_valor_r = [r for r in noeis if r["valor"] is not None][0]
    _garante(
        sem_valor["cap"] == 600 and "712 → 600" in sem_valor["nota"],
        f"Noel sem cachê rebaixado: {sem_valor}",
    )
    _garante(com_valor_r["cap"] == 712, f"Noel com cachê digitado intocado: {com_valor_r}")
    aju = _por_nome(depois, "Ajudante do Noel")[0]
    _garante(aju["cap"] == 270 and "423 → 270" in aju["nota"], f"Ajudante rebaixado: {aju}")
    _garante(_por_nome(depois, "Noel 2")[0]["cap"] == 712, "nome diferente não é tocado")
    _garante(_por_nome(depois, "Coordenador")[0]["cap"] == 250, "coordenador intocado")
    _garante("1" in saida, "saída do execute informa o total corrigido")


# ── 19 · regressão ──────────────────────────────────────────────────────────────────────────────
def cen_19_regressao() -> None:
    if "--regressao" not in sys.argv:
        raise Pulado("rode com --regressao para o portão da feature")
    r = subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / "specs/307-natal-papai-noel-calculadora/verify_307.py"),
            "--regressao",
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        cwd=str(REPO_ROOT),
        env={**os.environ, "PYTHONUTF8": "1"},
        timeout=2400,
    )
    ultima = (r.stdout.strip().splitlines() or ["?"])[-1]
    _garante(r.returncode == 0, f"verify_307 --regressao: {ultima}")


# ── 20 · limpeza ────────────────────────────────────────────────────────────────────────────────
def cen_20_limpeza() -> None:
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
    _garante(
        not _no_banco("SELECT 1 FROM calendar_events WHERE title LIKE :p", p=f"%{PREFIX}%"),
        "eventos descartáveis sobraram",
    )


CENARIOS: list[tuple[str, Callable[[], None]]] = [
    (
        "1. paridade sem `produtos`: quote, mensagem e PDF iguais ao gabarito do HEAD 6356b80",
        cen_01_paridade,
    ),
    (
        "2. Visita Noel 20/12 = 2.500 nas 4 colunas; memória (invariante); bloco único na mensagem e no PDF; snapshot congelado",
        cen_02_produto_noel_20_12,
    ),
    ("3. 24/12 = 5.000; Noel + Ajudante = 3.600 / 6.500", cen_03_faixa_e_ajudante),
    ("4. noturno embutido no produto; boneco avulso soma só o dele", cen_04_noturno_embutido),
    (
        "5. produto + boneco 4h; dois produtos = 2 Noéis, 2 coords, UM Maquiador 300; show avulso; make especial",
        cen_05_produto_mais_avulsos,
    ),
    ("6. fora de SP, NF, BV 10% e PIX sobre o total com produto", cen_06_fora_sp_nf_bv_pix),
    (
        "7. régua 6h (com NF e BV) igual na venda, no prefill e em _total_da_duracao; personalizado",
        cen_07_regua_e_personalizado,
    ),
    (
        "8. teto: ordem produto → avulsos → extras; flat; faixa pela data do evento; MARCA_PRODUTO; label desconhecido",
        cen_08_teto,
    ),
    (
        "9. prefill, criação por API e vínculo 273 com os tetos do produto",
        cen_09_prefill_criacao_vinculo,
    ),
    ("10. casting 900 → 600; superadmin 900 → 900", cen_10_casting_rebaixa),
    (
        "11. migração: 712→600 e 423→270 guardadas; 600 não vira 712; produtos padrão; bloco malformado",
        cen_11_migracao,
    ),
    (
        "12. avulsos: Noel 20/12 = 2.210 com aviso; 24/12 = 5.010; chaves novas sempre presentes",
        cen_12_avulsos,
    ),
    (
        "13. superadmin salva produtos; 7 corpos inválidos → 400 por campo; faixa órfã → aviso",
        cen_13_salvar_produtos,
    ),
    (
        "14. produto inativo recalcula; apagado → 400 na venda e vaga congelada sem teto",
        cen_14_inativo_e_apagado,
    ),
    (
        "15. produto sem preço de 24/25 → estimativa 6.600 marcada; teto pela faixa",
        cen_15_estimativa,
    ),
    (
        "16. EducaManto ignora `produtos` (com o produto provadamente ativo)",
        cen_16_educamanto_neutro,
    ),
    ("17. DEVE FALHAR: COMERCIAL não edita a configuração", cen_17_comercial_nao_edita),
    (
        "18. script rebaixa tetos 712/423 só sem cachê e sem artista; nome diferente só no relatório",
        cen_18_script_tetos,
    ),
    ("19. regressão (--regressao): verify_307 reescrito (encadeia a 305)", cen_19_regressao),
]


def main() -> int:
    print("Feature 309 — Produtos de tabela (Visita Mágica)")
    preparar()
    try:
        so = next((a.split("=", 1)[1].split(",") for a in sys.argv if a.startswith("--so=")), None)
        for nome, fn in CENARIOS:
            if so is None or nome.split(".", 1)[0] in so:
                cenario(nome, fn)
    finally:
        cenario("20. limpeza e restauração da configuração real", cen_20_limpeza)
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
