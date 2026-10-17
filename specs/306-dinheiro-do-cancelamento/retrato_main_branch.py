"""Retrato das telas dos meses sem cancelamento, `main` × branch, com relógio fixo (feature 306).

É a regressão do SC-002 e do cenário 23: nos meses sem cancelado, a DRE (API e Jinja), a
Tendência e os painéis da DRE, o Dashboard Comercial, o `/admin/desempenho`, a ficha, a lista e as
métricas de clientes, a Home (Performance e cobranças), Comissões e os itens de comissão e de BV da
Planilha saem idênticos ao centavo entre a `main` e a branch.

Como compara (quickstart §3):
- os dois lados rodam em subprocesso, no mesmo banco: a `main` por `git archive` do
  `git merge-base HEAD main`, a branch pelo próprio worktree;
- relógio fixo: `datetime`, `date` e `now_sp` trocados em todo módulo `app.*` já carregado (o que
  inclui `app.financeiro.routes`, `app.api.financeiro_read` e, na branch, `app.financeiro.dre_ops`),
  com `isinstance` preservado; `ensure_recurring_entries` e `_ensure_salary_payments` neutralizados
  (o GET da DRE e o da Planilha gravam);
- a `main` roda primeiro e aquece Comissões e Planilha (o resync da `main` grava o que o app de hoje
  gravaria); depois a branch roda e NÃO pode escrever linha nenhuma de comissão;
- compara os valores das chaves que a `main` devolve; chave que só existe na branch fica fora e é
  listada à parte; os itens da Planilha se comparam pela identidade (tipo e id);
- fica fora o que muda de propósito: o ticket médio do Jinja (FR-043), o `sale_count`, o item aberto
  de comissão de soma zero (R6) e, por cancelado com dinheiro (o `legado` e o que o verify já
  cancelou), o mês do `cancelled_at`, o do `expense_date` de cada devolução ligada a ele e, na
  Tendência embutida em toda resposta da DRE, esses meses e o do evento.

O script não importa nada que só exista na branch: cada lado roda o app da árvore que recebe.

Login: cria um SUPERADMIN temporário (o `/admin/desempenho` é só dele) e o apaga no fim; com
`V306_EMAIL`/`V306_SENHA` no ambiente, usa esse usuário, que precisa ser SUPERADMIN.

`--mutacao` (cenário 23, liga a partir da História 3): só na branch, o retido do período é somado
sem a condição da quantidade de cancelados; o retrato TEM de acusar (saída 1). Enquanto o gancho
não existir na branch, sai 3.

`--sem-resync`: os dois lados só leem (o resync de comissões neutralizado). É o modo da mutação do
23, que roda com cancelados do verify no banco: o resync da `main` cancelaria as linhas deles.

Saída: 0 = idêntico; 1 = diferença; 2 = ambiente impróprio; 3 = mutação sem gancho.
`--json` imprime o resumo na última linha.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
import uuid
from datetime import date, datetime
from pathlib import Path

AQUI = Path(__file__).resolve().parent
REPO_ROOT = AQUI.parents[1]

_LADO = r'''
import json, os, sys
import datetime as _dt
from datetime import timedelta
from decimal import Decimal

_DATETIME = _dt.datetime
_DATE = _dt.date
FIXO = _DATETIME.fromisoformat(os.environ["V306_RELOGIO"])


class _MetaDatetime(type):
    def __instancecheck__(cls, obj):
        return isinstance(obj, _DATETIME)

    def __subclasscheck__(cls, sub):
        return issubclass(sub, _DATETIME)


class _MetaDate(type):
    def __instancecheck__(cls, obj):
        return isinstance(obj, _DATE)

    def __subclasscheck__(cls, sub):
        return issubclass(sub, _DATE)


class _Relogio(_DATETIME, metaclass=_MetaDatetime):
    @classmethod
    def now(cls, tz=None):
        return FIXO if tz is None else FIXO.replace(tzinfo=tz)

    @classmethod
    def today(cls):
        return FIXO

    @classmethod
    def utcnow(cls):
        return FIXO + timedelta(hours=3)


class _Data(_DATE, metaclass=_MetaDate):
    @classmethod
    def today(cls):
        return FIXO.date()


def _now_sp():
    return FIXO


from app import create_app, db, limiter  # noqa: E402

app = create_app()
app.config["TESTING"] = True
limiter.enabled = False

import importlib  # noqa: E402

for nome in (
    "app.constants", "app.gastos.gastos_ops", "app.financeiro.routes", "app.financeiro.comissoes_ops",
    "app.financeiro.vendas_ops", "app.financeiro.cobranca_ops", "app.financeiro.dre_ops",
    "app.calendar.cancel_ops", "app.api.financeiro_read", "app.api.dashboard", "app.api.dashboard_service",
    "app.api.clientes_read", "app.api.admin_config_read", "app.clientes.client_ops",
):
    try:
        importlib.import_module(nome)
    except ImportError:
        pass

import app.constants as constants  # noqa: E402
import app.financeiro.routes as fin_routes  # noqa: E402
import app.gastos.gastos_ops as gastos_ops  # noqa: E402

_NOW_SP = constants.now_sp
gastos_ops.ensure_recurring_entries = lambda *a, **k: None
fin_routes._ensure_salary_payments = lambda *a, **k: None
if os.environ.get("V306_SEM_RESYNC") == "1":
    import app.financeiro.comissoes_ops as comissoes_ops

    comissoes_ops._resync_pending_commissions = lambda *a, **k: None
    fin_routes._resync_pending_commissions = lambda *a, **k: None
for nome, mod in list(sys.modules.items()):
    if mod is None or not (nome == "app" or nome.startswith("app.")):
        continue
    if getattr(mod, "datetime", None) is _DATETIME:
        mod.datetime = _Relogio
    if getattr(mod, "date", None) is _DATE:
        mod.date = _Data
    if getattr(mod, "now_sp", None) is _NOW_SP:
        mod.now_sp = _now_sp

if os.environ.get("V306_MUTACAO") == "1":
    # Gancho da mutação do 23 (liga a partir da História 3): o retido do período somado sem a
    # condição da quantidade de cancelados. Revisitar o alvo quando a H3 nascer.
    try:
        import app.calendar.cancel_ops as cancel_ops
        real = cancel_ops.totais_cancelamentos
    except (ImportError, AttributeError):
        print(json.dumps({"erro": "mutação sem gancho"}))
        sys.exit(3)

    def _sem_condicao(*a, **k):
        base = real(*a, **k)
        if isinstance(base, dict):
            base = dict(base)
            base["quantidade"] = max(1, int(base.get("quantidade") or 0))
        return base

    cancel_ops.totais_cancelamentos = _sem_condicao


def _limpo(v):
    """Decimal vira texto (o expoente conta: 0 × 0,00), data vira ISO, linha do ORM vira tipo:id."""
    if isinstance(v, Decimal):
        return str(v)
    if isinstance(v, (_DATE, _DATETIME)):
        return v.isoformat()
    if isinstance(v, dict):
        return {str(k): _limpo(x) for k, x in v.items()}
    if isinstance(v, (list, tuple, set)):
        return [_limpo(x) for x in v]
    if isinstance(v, (int, float, str, bool)) or v is None:
        return v
    if getattr(v, "id", None) is not None:
        return f"{type(v).__name__}:{v.id}"
    return type(v).__name__


from flask import template_rendered  # noqa: E402

_JINJA = (
    "drg_realizado", "drg_projetado", "drg_total", "ratio_custo_talento", "breakeven_pct",
    "breakeven_atingido", "fixed_cost", "fator_r_pct", "fator_r_protegido", "a_receber_clientes",
    "recebimentos_previstos", "recebimentos_previstos_total", "nf_a_emitir", "nf_a_emitir_total",
    "custo_nota_itens", "custo_nota_total", "pagamentos_pendentes", "pagamentos_realizados",
    "receita_por_tipo", "receita_tipo_max", "top_sellers", "monthly_trend", "auditoria", "events_data",
)
capturas = {}


def _gravar(_s, template, context, **_k):
    if template.name == "financeiro/dashboard.html":
        capturas["dre_jinja"] = {k: _limpo(context.get(k)) for k in _JINJA}


template_rendered.connect(_gravar, app)
c = app.test_client()
r = c.post("/api/auth/login", json={"email": os.environ["V306_EMAIL"], "password": os.environ["V306_SENHA"]})
if r.status_code != 200:
    print(json.dumps({"erro": f"login {r.status_code}"}))
    sys.exit(2)


def _get(url):
    resp = c.get(url)
    if resp.status_code != 200:
        return {"__status": resp.status_code}
    return resp.get_json()


meses = json.loads(os.environ["V306_MESES"])
saida = {"dre": {}, "dre_jinja": {}, "pipeline": {}, "desempenho": {}, "comissoes": {}, "planilha": {}}
for m in meses:
    ano, mes = int(m[:4]), int(m[5:7])
    ini = _DATE(ano, mes, 1)
    fim = _DATE(ano + (mes // 12), mes % 12 + 1, 1) - timedelta(days=1)
    q = f"period=custom&start={ini.isoformat()}&end={fim.isoformat()}"
    saida["dre"][m] = _get(f"/api/financeiro/dashboard?{q}")
    capturas.clear()
    c.get(f"/financeiro/?{q}")
    saida["dre_jinja"][m] = capturas.get("dre_jinja")
    saida["pipeline"][m] = _get(f"/api/vendas/pipeline?{q}")
    saida["desempenho"][m] = _get(f"/api/admin/desempenho?month={m}")
    saida["comissoes"][m] = _get(f"/api/financeiro/comissoes?month={m}")
    p = _get(f"/api/financeiro/pagamentos?month={m}") or {}
    saida["planilha"][m] = {
        f"{i['type']}:{i['id']}": i for i in (p.get("items") or []) if i.get("type") in ("commission", "bv")
    }
saida["clientes_lista"] = _get("/api/clientes/")
saida["clientes_metricas"] = _get("/api/clientes/metricas")
saida["clientes"] = {str(cid): _get(f"/api/clientes/{cid}") for cid in json.loads(os.environ["V306_CLIENTES"])}
saida["home"] = _get("/api/dashboard")
print(json.dumps(_limpo(saida), ensure_ascii=False))
'''


def _sql(url: str, consulta: str, **params) -> list:
    from sqlalchemy import create_engine, text

    eng = create_engine(url, future=True)
    try:
        with eng.connect() as conn:
            conn.exec_driver_sql("SET default_transaction_read_only = on")
            return conn.execute(text(consulta), params).fetchall()
    finally:
        eng.dispose()


def _meses_do_espelho(url: str, hoje: date) -> tuple[list[str], list[str], dict[str, list[str]]]:
    """Os meses do espelho, os da Tendência que saem por `legado` e os excluídos, com o motivo.

    Cancelado `legado` é o que não tem linha em `event_cancellations` (na `main` a tabela nem
    existe); sem dinheiro (nem comprovante com valor, nem devolução) ele não entra na DRE (P-24).
    """
    inicio, fim = _sql(
        url,
        "SELECT min(start_at), max(start_at) FROM calendar_events WHERE start_at < :lim "
        "AND coalesce(google_event_id, '') NOT LIKE 'v306%'",
        lim=datetime(hoje.year + 1, 12, 31),
    )[0]
    meses: list[str] = []
    if inicio:
        a, m = inicio.year, inicio.month
        while (a, m) <= (fim.year, fim.month):
            meses.append(f"{a:04d}-{m:02d}")
            a, m = (a + 1, 1) if m == 12 else (a, m + 1)
    com_dinheiro = (
        "(EXISTS (SELECT 1 FROM event_payments p WHERE p.event_id = e.id AND coalesce(p.amount, 0) > 0) "
        "OR EXISTS (SELECT 1 FROM special_expenses s WHERE s.event_id = e.id "
        "AND s.category = 'Devolução a cliente'))"
    )
    # Todo cancelado com dinheiro sai da comparação: o `legado` (sem linha congelada, o de antes do
    # deploy) e também o que o próprio verify cancelou antes de chamar o retrato (a mutação do 23).
    cancelados = _sql(
        url,
        "SELECT e.id, e.cancelled_at, e.start_at FROM calendar_events e "
        f"WHERE e.cancelled_at IS NOT NULL AND {com_dinheiro}",
    )
    fora: dict[str, list[str]] = {}
    for _id, cancelado_em, _inicio in cancelados:
        fora.setdefault(f"{cancelado_em:%Y-%m}", []).append("cancelled_at de cancelado")
    ids = [x[0] for x in cancelados]
    if ids:
        for (quando,) in _sql(
            url,
            "SELECT expense_date FROM special_expenses WHERE event_id = ANY(:ids) "
            "AND category = 'Devolução a cliente'",
            ids=ids,
        ):
            fora.setdefault(f"{quando:%Y-%m}", []).append("devolução de cancelado")
    # As linhas de comissão que o próprio verify semeou em meses reais (vendedores `__v306_`): a
    # mutação do 23 roda depois dos cenários B1/B2, e um vendedor só com "no banco" (que a 306 passa
    # a mostrar em Comissões) faria a base sair diferente sem ser do espelho (rodada de 17/10).
    for (ciclo,) in _sql(
        url,
        "SELECT DISTINCT coalesce(c.payable_from, c.sale_date, date(c.created_at)) FROM commission_payments c "
        "JOIN users u ON u.id = c.seller_id WHERE u.email LIKE '\\_\\_v306\\_%'",
    ):
        if ciclo is not None:
            fora.setdefault(f"{ciclo:%Y-%m}", []).append("linha de comissão do verify")
    tendencia = sorted({f"{x[2]:%Y-%m}" for x in cancelados} | set(fora))
    return [m for m in meses if m not in fora], tendencia, fora


def _arvore_main() -> Path:
    base = subprocess.run(
        ["git", "-C", str(REPO_ROOT), "merge-base", "HEAD", "main"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    destino = Path(tempfile.mkdtemp(prefix="v306_retrato_main_"))
    arquivo = destino / "base.tar"
    subprocess.run(
        ["git", "-C", str(REPO_ROOT), "archive", "--format=tar", "-o", str(arquivo), base, "app"],
        check=True,
    )
    subprocess.run(["tar", "-xf", str(arquivo), "-C", str(destino)], check=True)
    return destino


def _rodar(raiz: Path, env_extra: dict) -> tuple[int, dict]:
    script = Path(tempfile.mkdtemp(prefix="v306_retrato_")) / "lado.py"
    script.write_text(_LADO, encoding="utf-8")
    env = {
        **os.environ,
        "PYTHONPATH": str(raiz),
        "MANTO_SEM_THREADS": "1",
        "FLASK_ENV": "development",
        "PYTHONUTF8": "1",
        **env_extra,
    }
    r = subprocess.run(
        [sys.executable, str(script)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=env,
        cwd=str(raiz),
        timeout=3600,
    )
    linhas = [x for x in r.stdout.strip().splitlines() if x.strip()]
    if not linhas:
        raise RuntimeError(f"lado {raiz} falhou ({r.returncode}): {r.stderr.strip()[-1500:]}")
    try:
        dados = json.loads(linhas[-1])
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            f"lado {raiz} sem JSON ({r.returncode}): {r.stderr.strip()[-1500:]}"
        ) from exc
    return r.returncode, dados


IGNORAR = {"ticket_medio", "sale_count"}  # mudam de propósito (FR-043)
_FOLHAS = [0]  # valores comparados: zero diferença em zero folhas não prova nada


def _chave_de_ordem(lista: list) -> str | None:
    """A chave de id comum a todos os itens da lista (`event_id` ou `id`), se houver."""
    for chave in ("event_id", "id"):
        if lista and all(isinstance(x, dict) and chave in x for x in lista):
            return chave
    return None


def _dif(a, b, caminho: str, extras: list[str]) -> list[str]:
    """Diferenças olhando só as chaves de `a` (a main); chaves só de `b` vão para `extras`."""
    if isinstance(a, dict) and isinstance(b, dict):
        out = []
        for k in b:
            if k not in a:
                extras.append(f"{caminho}/{k}")
        for k, v in a.items():
            if k in IGNORAR:
                continue
            if k not in b:
                out.append(f"{caminho}/{k}: some na branch")
            else:
                out.extend(_dif(v, b[k], f"{caminho}/{k}", extras))
        return out
    if isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b):
            return [f"{caminho}: {len(a)} itens na main × {len(b)} na branch"]
        chave = _chave_de_ordem(a)
        if chave is not None and _chave_de_ordem(b) == chave:
            # Itens com a mesma data saem na ordem do desempate do banco, que muda de uma consulta
            # para outra (a DRE de 2026-02 trocou dois shows de lugar na rodada de 17/10): compara
            # por id, porque o retrato confere valores, não a ordem de um empate.
            a = sorted(a, key=lambda x: str(x[chave]))
            b = sorted(b, key=lambda x: str(x[chave]))
        out = []
        for i, (x, y) in enumerate(zip(a, b, strict=True)):
            out.extend(_dif(x, y, f"{caminho}[{i}]", extras))
        return out
    _FOLHAS[0] += 1
    if isinstance(a, float) or isinstance(b, float):
        try:
            return [] if round(float(a), 2) == round(float(b), 2) else [f"{caminho}: {a} × {b}"]
        except (TypeError, ValueError):
            pass
    return [] if a == b else [f"{caminho}: {a!r} × {b!r}"]


def _sem_rotulos(corpo, rotulos: set[str]):
    """Tira da Tendência (embutida em toda resposta da DRE) os meses com cancelado."""
    if isinstance(corpo, dict):
        out = {}
        for k, v in corpo.items():
            if k == "monthly_trend" and isinstance(v, list):
                out[k] = [x for x in v if not (isinstance(x, dict) and x.get("label") in rotulos)]
            else:
                out[k] = _sem_rotulos(v, rotulos)
        return out
    if isinstance(corpo, list):
        return [_sem_rotulos(x, rotulos) for x in corpo]
    return corpo


def _comparar(main: dict, branch: dict) -> tuple[list[str], list[str], list[str]]:
    extras: list[str] = []
    proposito: list[str] = []
    difs: list[str] = []
    for secao, valor in main.items():
        if secao == "planilha":
            for m, itens in valor.items():
                outro = branch.get("planilha", {}).get(m, {})
                for chave, item in itens.items():
                    if chave not in outro:
                        difs.append(f"planilha/{m}/{chave}: some na branch")
                    else:
                        difs.extend(_dif(item, outro[chave], f"planilha/{m}/{chave}", extras))
                for chave, item in outro.items():
                    if chave in itens:
                        continue
                    if (
                        chave.startswith("commission:")
                        and abs(float(item.get("amount") or 0)) < 0.005
                    ):
                        proposito.append(f"planilha/{m}/{chave}: item aberto de soma zero (R6)")
                    else:
                        difs.append(f"planilha/{m}/{chave}: só na branch")
            continue
        difs.extend(_dif(valor, branch.get(secao), secao, extras))
    return difs, extras, proposito


def _vazios(lado: dict) -> list[str]:
    """Respostas que não vieram (status ≠ 200 ou Jinja sem render): "idêntico" vazio não prova nada."""
    out = []
    for secao, valor in lado.items():
        if secao in ("dre", "dre_jinja", "pipeline", "desempenho", "comissoes", "clientes"):
            for chave, resp in valor.items():
                if resp is None or (isinstance(resp, dict) and "__status" in resp):
                    out.append(f"{secao}/{chave}: {resp}")
        elif isinstance(valor, dict) and "__status" in valor:
            out.append(f"{secao}: {valor}")
    return out


def _usuario_temporario() -> tuple[str, str, int | None]:
    email = os.environ.get("V306_EMAIL")
    senha = os.environ.get("V306_SENHA")
    if email and senha:
        return email, senha, None
    sys.path.insert(0, str(REPO_ROOT))
    from app import create_app, db
    from app.constants import RoleName
    from app.models import Role, User

    app = create_app()
    email = f"__retrato306_{uuid.uuid4().hex[:8]}@manto.local"
    senha = uuid.uuid4().hex
    with app.app_context():
        u = User(
            name="__retrato306",
            email=email,
            is_active=True,
            has_access=True,
            receives_commission=False,
        )
        u.set_password(senha)
        u.roles.append(Role.query.filter_by(name=RoleName.SUPERADMIN).one())
        db.session.add(u)
        db.session.commit()
        return email, senha, u.id


def _apagar_usuario(uid: int | None) -> None:
    if uid is None:
        return
    from app import create_app, db
    from app.models import User

    app = create_app()
    with app.app_context():
        u = db.session.get(User, uid)
        if u is not None:
            u.roles.clear()
            db.session.delete(u)
            db.session.commit()


_LINHAS_COMISSAO = "SELECT id, amount, status, sale_date, payable_from, event_id FROM commission_payments ORDER BY id"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--mutacao", action="store_true")
    parser.add_argument(
        "--sem-resync", action="store_true", help="os dois lados só leem (sem resync de comissões)"
    )
    args = parser.parse_args()
    url = os.environ.get("DATABASE_URL") or ""
    if not url or not ("localhost" in url or "127.0.0.1" in url):
        print("DATABASE_URL ausente ou não é o manto_local.")
        return 2
    if os.environ.get("MANTO_SEM_THREADS") != "1" or os.environ.get("FLASK_ENV") != "development":
        print(
            "Faltam MANTO_SEM_THREADS=1 e FLASK_ENV=development (o espelho escreve em serviços reais)."
        )
        return 2
    relogio = datetime.now().replace(microsecond=0)
    meses, tendencia_fora, fora = _meses_do_espelho(url, relogio.date())
    clientes = [
        r[0]
        for r in _sql(
            url,
            "SELECT DISTINCT client_id FROM calendar_events WHERE client_id IS NOT NULL "
            "AND coalesce(google_event_id, '') NOT LIKE 'v306%' ORDER BY 1",
        )
    ]
    email, senha, uid = _usuario_temporario()
    try:
        env = {
            "V306_RELOGIO": relogio.isoformat(),
            "V306_MESES": json.dumps(meses),
            "V306_CLIENTES": json.dumps(clientes),
            "V306_EMAIL": email,
            "V306_SENHA": senha,
            **({"V306_SEM_RESYNC": "1"} if args.sem_resync else {}),
        }
        cod_main, main_lado = _rodar(_arvore_main(), env)
        antes = _sql(url, _LINHAS_COMISSAO)
        cod_branch, branch = _rodar(
            REPO_ROOT, {**env, **({"V306_MUTACAO": "1"} if args.mutacao else {})}
        )
        depois = _sql(url, _LINHAS_COMISSAO)
    finally:
        _apagar_usuario(uid)
    for lado, cod, dados in (("main", cod_main, main_lado), ("branch", cod_branch, branch)):
        if cod != 0:
            print(f"lado {lado} saiu {cod}: {dados.get('erro')}")
            if args.json:
                print(
                    json.dumps(
                        {"diferencas": None, "erro": f"{lado}: {dados.get('erro')}"},
                        ensure_ascii=False,
                    )
                )
            return 3 if cod == 3 else 2
        vazios = _vazios(dados)
        if vazios:
            print(
                f"lado {lado}: {len(vazios)} respostas vazias, a comparação não prova nada: {vazios[:10]}"
            )
            if args.json:
                print(
                    json.dumps(
                        {"diferencas": None, "erro": f"{lado}: respostas vazias"},
                        ensure_ascii=False,
                    )
                )
            return 2
    rotulos = {f"{m[5:7]}/{m[2:4]}" for m in tendencia_fora}
    difs, extras, proposito = _comparar(
        _sem_rotulos(main_lado, rotulos), _sem_rotulos(branch, rotulos)
    )
    if antes != depois:
        difs.append(
            f"a rodada da branch escreveu linhas de comissão ({len(antes)} → {len(depois)})"
        )
    for m in tendencia_fora:
        proposito.append(f"Tendência {m}: mês com cancelado, fora da comparação (FR-043)")
    for m, motivos in sorted(fora.items()):
        proposito.append(f"{m}: fora da comparação ({', '.join(sorted(set(motivos)))})")
    print(
        f"relógio: {relogio.isoformat()}; meses comparados: {len(meses)}; clientes: {len(clientes)}"
    )
    print(f"valores comparados: {_FOLHAS[0]}; diferenças: {len(difs)}")
    for d in difs[:60]:
        print(f"  DIF  {d}")
    novas = sorted({x.split("/")[-1] for x in extras})
    print(f"chaves só da branch (fora da comparação): {len(novas)}")
    for e in novas[:40]:
        print(f"  NOVA {e}")
    for p in proposito[:40]:
        print(f"  PROPÓSITO {p}")
    if args.json:
        print(
            json.dumps(
                {
                    "diferencas": len(difs),
                    "meses": len(meses),
                    "valores": _FOLHAS[0],
                    "primeiras": difs[:20],
                },
                ensure_ascii=False,
            )
        )
    return 0 if not difs else 1


if __name__ == "__main__":
    sys.exit(main())
