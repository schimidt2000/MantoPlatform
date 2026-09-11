"""Verificação da feature 298 — o formulário vira evento; a Home mostra só o que precisa de destino.

Cenários (17 linhas da tabela da spec):
  1. Formulário chegado antes do corte (23h de 31/05 em SP) fica fora de tudo; data de início vazia
     vale 01/06/2026.
  2. Formulário desde junho com data futura: grupo, cor, tipo "Festa", distância e dias desde a
     chegada; mesma data → o que chegou por último vem primeiro; FINANCEIRO não "cria evento".
  3. Data informada passada → grupo "já passou".
  4. Corporativo aparece como "Corporativo".
  5. Mesmo telefone → uma linha, representada pelo último; marca "outro com evento"; escolher um
     encerra o outro como "repetido".
  6. Encerrar com motivo: grava (conexão separada), apaga o sino, entra no histórico; "outro" sem
     frase é recusado no campo.
  7. Reabrir: volta à lista, o sino não reacende, entra no histórico; reabrir de novo → 409.
  8. Sugestão: empate −1/+1 → o mais cedo; descartar é definitivo e idempotente; confirmar liga.
  9. Ligar leva a cliente do evento; divergência não mexe no evento e "usar a cliente do evento" troca.
 10. Cancelado não volta; excluído e desvinculado (tela e aba Comercial) voltam; ligar desfaz o
     encerramento; formulário do histórico não se encerra.
 11. Dados para o cadastro de evento nos dois vocabulários (site e WhatsForm) e no corporativo.
 12. Alertas do cadastro (data 2049, "Boleto", período ambíguo, sem hora, endereço incompleto, tipo
     desconhecido, evento da cliente sem formulário).
 13. Contagens da tela Formulários somam o total e batem com a Home.
 14a. Sync não religa encerrado; os quatro caminhos recusam o segundo vínculo (tela, aba Comercial,
      edição, POST /api/events) — nada chega ao Google.
 14b. Formulário que chega ligado não gera aviso; os dois comandos de correção contam e aplicam.
 15. CASTING encerrando e FINANCEIRO pedindo dados para o cadastro → exatamente 403 (DEVEM falhar);
     COMERCIAL em 200 como controle.
 16. Limpeza.

O GOOGLE AGENDA NUNCA É CHAMADO. `app.calendar.routes.insert_event` é trocado, dentro deste
processo, por uma função falsa que conta a chamada e levanta erro — a view importa a função na hora
da requisição (`agenda_write.py:740`), então a troca vale. Todo evento de teste leva
"[TESTE verify 298] pode apagar" no título (decisão do dono, 11/09).

DUAS ARMADILHAS DA CASA, respeitadas de propósito: escrita conferida por **conexão separada**
(o autoflush esconde falta de commit) e requisições HTTP **fora** de `app.app_context()` (contexto
persistente vaza o usuário logado entre requisições).

Rodar contra o manto_local (PowerShell)::

    $env:DATABASE_URL = (gc .local-db-url -Raw).Trim(); $env:FLASK_ENV = "development"; $env:MANTO_SEM_THREADS = "1"
    .venv/Scripts/python.exe specs/298-formulario-vira-evento/verify_298.py
"""

from __future__ import annotations

import json
import os
import sys
import traceback
from collections.abc import Callable
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

for _stream in (sys.stdout, sys.stderr):  # console do Windows em cp1252
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))
os.environ.setdefault("FLASK_ENV", "development")
os.environ.setdefault("MANTO_SEM_THREADS", "1")
if not os.environ.get("DATABASE_URL"):
    os.environ["DATABASE_URL"] = (REPO_ROOT / ".local-db-url").read_text(encoding="utf-8").strip()

from sqlalchemy import create_engine, text  # noqa: E402

from app import create_app, db, limiter  # noqa: E402
from app.constants import RoleName, now_sp  # noqa: E402
from app.models import (  # noqa: E402
    CalendarEvent,
    Client,
    EventClient,
    FormResponse,
    Notification,
    Role,
    SiteSetting,
    User,
)

PREFIX = "__v298_"
SENHA = "verify-298-senha"
TITULO_TESTE = "[TESTE verify 298] pode apagar"
SP = ZoneInfo("America/Sao_Paulo")
KIND = "form_response.nova"

app = create_app()
app.config["TESTING"] = True
limiter.enabled = False  # pelo OBJETO: `RATELIMIT_ENABLED` só é lido no `init_app`

# ── O Google fica de fora ────────────────────────────────────────────────────────────────────────
import app.calendar.routes as _rotas  # noqa: E402

_google = {"chamadas": 0}


def _google_falso(*_args, **_kwargs):
    _google["chamadas"] += 1
    raise RuntimeError("verify 298: o Google Agenda não pode ser chamado")


_rotas.insert_event = _google_falso

resultados: list[tuple[str, bool, str]] = []
estado: dict = {}
_engine_externo = create_engine(os.environ["DATABASE_URL"], future=True)


def _no_banco(sql: str, **params):
    """Lê pelo banco, por fora da sessão do app (o autoflush esconde falta de commit)."""
    with _engine_externo.connect() as conn:
        return conn.execute(text(sql), params).fetchone()


def cenario(nome: str, fn: Callable[[], None]) -> None:
    try:
        fn()
        resultados.append((nome, True, ""))
        print(f"  OK     {nome}")
    except Exception as exc:  # noqa: BLE001 — harness: registra e segue
        with app.app_context():
            db.session.rollback()
        resultados.append((nome, False, traceback.format_exc().strip().splitlines()[-1]))
        print(f"  FALHA  {nome}: {exc}")


def _garante(cond: bool, msg: str) -> None:
    if not cond:
        raise AssertionError(msg)


def _usuario(sufixo: str, papel: str) -> tuple[str, int]:
    email = f"{PREFIX}{sufixo}@manto.local"
    user = User.query.filter_by(email=email).first()
    if user is None:
        user = User(name=f"{PREFIX}{sufixo}", email=email, is_active=True, has_access=True)
        db.session.add(user)
    user.set_password(SENHA)
    user.roles.clear()
    user.roles.append(Role.query.filter_by(name=papel).one())
    db.session.commit()
    return email, user.id


def _login(c, email: str) -> None:
    r = c.post("/api/auth/login", json={"email": email, "password": SENHA})
    _garante(r.status_code == 200, f"login {email} → {r.status_code}")


def _chamar(email: str, metodo: str, url: str, corpo: dict | None = None):
    """Uma requisição autenticada, fora de qualquer contexto de aplicação."""
    with app.test_client() as c:
        _login(c, email)
        return getattr(c, metodo)(url, json=corpo) if corpo is not None else getattr(c, metodo)(url)


# ── Oráculos independentes (não usam o código que está sendo verificado) ─────────────────────────

def _corte_utc() -> datetime:
    settings = SiteSetting.query.get(1)
    dia = settings.release_date if settings and settings.release_date else date(2026, 6, 1)
    return datetime.combine(dia, time.min, tzinfo=SP).astimezone(timezone.utc).replace(tzinfo=None)


def _dia_sp(utc_naive: datetime) -> date:
    return utc_naive.replace(tzinfo=timezone.utc).astimezone(SP).date()


# ── Semeadura ────────────────────────────────────────────────────────────────────────────────────

def _tel(n: int) -> str:
    return f"55119{n:08d}"


def _secoes(campos: list[tuple[str, str]]) -> str:
    return json.dumps(
        [{"secao": "Dados", "campos": [[k, k, v] for k, v in campos]}], ensure_ascii=False
    )


def _form(nome: str, *, chegou: datetime, data: date | None, tipo: str = "comum",
          telefone: str | None = None, campos: list[tuple[str, str]] | None = None,
          client_id: int | None = None, event_id: int | None = None) -> int:
    fr = FormResponse(
        form_type=tipo,
        data=_secoes(campos or []),
        contact_name=f"{PREFIX}{nome}",
        contact_phone=telefone,
        contact_phone_display=f"+{telefone}" if telefone else None,
        event_date=data,
        client_id=client_id,
        client_link_source="manual" if client_id else None,
        event_id=event_id,
        event_link_source="manual" if event_id else None,
        event_link_locked=bool(event_id),
        created_at=chegou,
    )
    db.session.add(fr)
    db.session.flush()
    return fr.id


def _cliente(nome: str, telefone: str) -> int:
    cl = Client(name=f"{PREFIX}{nome}", phone=telefone, phone_display=f"+{telefone}", source="manual")
    db.session.add(cl)
    db.session.flush()
    return cl.id


def _evento(nome: str, dia: date, cliente_id: int | None = None) -> int:
    inicio = datetime.combine(dia, time(15, 0))
    ev = CalendarEvent(
        title=f"{PREFIX}{nome} {TITULO_TESTE}",
        start_at=inicio,
        end_at=inicio + timedelta(hours=3),
        google_event_id=f"{PREFIX}{nome}",
        source="platform",
    )
    db.session.add(ev)
    db.session.flush()
    if cliente_id:
        db.session.add(EventClient(event_id=ev.id, client_id=cliente_id, relationship_type="Contratante"))
        ev.client_id = cliente_id
    return ev.id


def _aviso(form_id: int, user_id: int) -> None:
    db.session.add(Notification(
        user_id=user_id, kind=KIND, title=f"{PREFIX}aviso {form_id}",
        dedupe_key=f"{KIND}:{form_id}:{PREFIX}{user_id}",
        entity_type="form_response", entity_id=form_id, created_at=now_sp(),
    ))


NATIVO_J1 = [
    ("nome_contratante", "J1"), ("endereco_contratante", "Rua da Contratante, 1"),
    ("cpf", "123.456.789-00"), ("email", "j1@exemplo.com"),
    ("nome_aniversariante", "Ana"), ("idade_aniversariante", "5"),
    ("tipo_contratacao", "Receptivo e Interativo"), ("qtd_personagens", "2"),
    ("quais_personagens", "Mickey e Minnie"), ("tema_evento", "Fundo do mar"),
    ("hora_evento", "15:00"), ("periodo_contratacao", "3 horas"),
    ("espaco_evento", "Salão de Festas"), ("cep", "01234-567"), ("logradouro", "Rua das Festas"),
    ("numero", "100"), ("complemento", ""), ("bairro", "Centro"), ("cidade", "São Paulo"),
    ("estado", "SP"),
    ("forma_pagamento", "Em 2x no PIX (50% no ato + 50% em até 2 dias antes do evento)"),
    ("descreva_outros", ""), ("observacoes", "Chegar 15 min antes"),
]
WHATSFORM_J2 = [
    ("nome_completo_contratante", "J2"), ("data_do_evento", "2026-10-10 16:00"),
    ("periodo_de_contratacao", "das 16h às 19h"),
    ("tipo_de_contratacao", "Receptivo, Interativo e Show"),
    ("forma_de_pagamento", "À vista"), ("tema_do_evento", "Circo"),
    ("logradouro", "Rua WhatsForm"), ("numero", "7"), ("cep", "04000-000"),
    ("bairro", "Vila"), ("cidade", "São Paulo"), ("estado", "SP"),
]
CORP_J3 = [
    ("razao_social", "Empresa J3"), ("endereco_empresa", "Av Empresa, 1"),
    ("hora_evento", "10:00"), ("periodo_contratacao", "das 10h às 12h"),
    ("endereco_evento", "Rua do Evento Corporativo, 50 - Centro, São Paulo - SP, 01000-000"),
    ("briefing", "Evento de fim de ano"), ("forma_pagamento", "Faturado"),
]
ALERTAS_J4 = [
    ("nome_contratante", "J4"), ("tipo_contratacao", "Algo estranho"),
    ("hora_evento", ""), ("periodo_contratacao", "3h ou 4h"),
    ("logradouro", "Rua Sem Numero"), ("numero", ""), ("cep", ""), ("bairro", "Bairro"),
    ("cidade", "São Paulo"), ("estado", "SP"), ("forma_pagamento", "Boleto"),
]


def preparar() -> None:
    e = estado
    e["comercial"], e["comercial_id"] = _usuario("comercial", RoleName.COMERCIAL)
    e["financeiro"], e["financeiro_id"] = _usuario("financeiro", RoleName.FINANCEIRO)
    e["casting"], e["casting_id"] = _usuario("casting", RoleName.CASTING)

    hoje = now_sp().date()
    agora = datetime.utcnow()
    e["hoje"] = hoje
    corte = _corte_utc()
    e["corte"] = corte

    def chegou(dias: int) -> datetime:
        return agora - timedelta(days=dias)

    f = {}
    f["A1"] = _form("A1", chegou=corte - timedelta(hours=1), data=hoje + timedelta(days=15))
    f["B1"] = _form("B1", chegou=chegou(20), data=hoje + timedelta(days=20))
    f["B2"] = _form("B2", chegou=chegou(10), data=hoje + timedelta(days=5))
    f["B3"] = _form("B3", chegou=chegou(2), data=hoje + timedelta(days=5))
    f["C1"] = _form("C1", chegou=chegou(40), data=hoje - timedelta(days=10))
    f["D1"] = _form("D1", chegou=chegou(1), data=hoje + timedelta(days=40), tipo="corporativo")

    p5 = _tel(2980005)
    ev_e3 = _evento("ev_e3", hoje - timedelta(days=20))
    f["E1"] = _form("E1", chegou=chegou(5), data=hoje + timedelta(days=12), telefone=p5)
    f["E2"] = _form("E2", chegou=chegou(1), data=hoje + timedelta(days=14), telefone=p5, tipo="corporativo")
    f["E3"] = _form("E3", chegou=chegou(30), data=hoje - timedelta(days=20), telefone=p5, event_id=ev_e3)

    f["F1"] = _form("F1", chegou=chegou(3), data=hoje + timedelta(days=9))
    f["F2"] = _form("F2", chegou=chegou(3), data=hoje + timedelta(days=9))

    p8 = _tel(2980008)
    k8 = _cliente("K8", p8)
    d8 = hoje + timedelta(days=20)
    f["G1"] = _form("G1", chegou=chegou(2), data=d8, telefone=p8)
    e["ev_m1"] = _evento("ev_m1", d8 - timedelta(days=1), k8)
    e["ev_p1"] = _evento("ev_p1", d8 + timedelta(days=1), k8)
    e["ev_p2"] = _evento("ev_p2", d8 + timedelta(days=2), k8)

    p9 = _tel(2980009)
    e["k9"] = _cliente("K9", p9)
    f["H1"] = _form("H1", chegou=chegou(2), data=hoje + timedelta(days=30), telefone=p9)
    e["ev9"] = _evento("ev9", hoje + timedelta(days=31), e["k9"])
    k9b = _cliente("K9b", _tel(2980091))
    e["k9c"] = _cliente("K9c", _tel(2980092))
    f["H2"] = _form("H2", chegou=chegou(2), data=hoje + timedelta(days=33),
                    telefone=_tel(2980091), client_id=k9b)
    e["ev9b"] = _evento("ev9b", hoje + timedelta(days=34), e["k9c"])

    for i, nome in enumerate(("I1", "I2", "I3", "I4", "I5"), start=1):
        f[nome] = _form(nome, chegou=chegou(3), data=hoje + timedelta(days=24 + i))
        e[f"ev10_{nome}"] = _evento(f"ev10_{nome}", hoje + timedelta(days=24 + i))
    f["I6"] = _form("I6", chegou=corte - timedelta(days=5), data=hoje + timedelta(days=50))

    f["J1"] = _form("J1", chegou=chegou(2), data=hoje + timedelta(days=60), campos=NATIVO_J1)
    f["J2"] = _form("J2", chegou=chegou(2), data=date(2026, 10, 10), campos=WHATSFORM_J2)
    f["J3"] = _form("J3", chegou=chegou(2), data=hoje + timedelta(days=61), tipo="corporativo",
                    campos=CORP_J3)
    p12 = _tel(2980012)
    k12 = _cliente("K12", p12)
    e["ev12"] = _evento("ev12", hoje + timedelta(days=30), k12)
    f["J4"] = _form("J4", chegou=chegou(2), data=date(2049, 4, 4), telefone=p12, campos=ALERTAS_J4)

    p14 = _tel(2980014)
    k14 = _cliente("K14", p14)
    d14 = hoje + timedelta(days=18)
    e["ev14"] = _evento("ev14", d14, k14)
    f["L1"] = _form("L1", chegou=chegou(2), data=d14, telefone=p14)
    e["ev14b"] = _evento("ev14b", hoje + timedelta(days=19))
    e["ev14c"] = _evento("ev14c", hoje + timedelta(days=20))
    f["L2"] = _form("L2", chegou=chegou(2), data=hoje + timedelta(days=19), event_id=e["ev14b"])

    e["ev_m"] = _evento("ev_m", hoje + timedelta(days=21))
    f["M1"] = _form("M1", chegou=chegou(1), data=hoje + timedelta(days=21), event_id=e["ev_m"])
    f["M2"] = _form("M2", chegou=chegou(1), data=hoje + timedelta(days=21), event_id=e["ev_m"])
    e["k14d"] = _cliente("K14d", _tel(2980141))
    e["ev14d"] = _evento("ev14d", hoje + timedelta(days=22), e["k14d"])
    f["M3"] = _form("M3", chegou=chegou(1), data=hoje + timedelta(days=22), event_id=e["ev14d"])

    f["N1"] = _form("N1", chegou=chegou(2), data=hoje + timedelta(days=23))

    for alvo in ("F1", "H1", "M2"):
        _aviso(f[alvo], e["comercial_id"])
        _aviso(f[alvo], e["financeiro_id"])
    db.session.commit()
    e["f"] = f


# ── Leitura da Home ──────────────────────────────────────────────────────────────────────────────

def _bloco(email: str) -> dict:
    r = _chamar(email, "get", "/api/dashboard")
    _garante(r.status_code == 200, f"/api/dashboard → {r.status_code}")
    bloco = r.get_json().get("formularios")
    _garante(isinstance(bloco, dict), "bloco `formularios` ausente (painel falhou ou sem permissão)")
    _garante("a_chegar" in bloco and "ja_passou" in bloco, f"bloco sem as listas: {list(bloco)}")
    return bloco


def _linha(bloco: dict, fid: int) -> tuple[str, int, dict] | None:
    for grupo in ("a_chegar", "ja_passou"):
        for i, linha in enumerate(bloco.get(grupo) or []):
            ids = [x["id"] for x in linha.get("formularios") or []]
            if fid in ids or linha.get("representante_id") == fid:
                return grupo, i, linha
    return None


def _detalhe(fid: int, email: str | None = None) -> dict:
    r = _chamar(email or estado["comercial"], "get", f"/api/formularios/respostas/{fid}")
    _garante(r.status_code == 200, f"detalhe {fid} → {r.status_code}")
    return r.get_json()


def _col(fid: int, coluna: str):
    return _no_banco(f"SELECT {coluna} FROM form_responses WHERE id = :i", i=fid)[0]


# ── Cenários ─────────────────────────────────────────────────────────────────────────────────────

def cen_01() -> None:
    f = estado["f"]
    bloco = _bloco(estado["comercial"])
    _garante(_linha(bloco, f["A1"]) is None, "formulário de antes do corte apareceu na Home")
    destino = _detalhe(f["A1"])["response"].get("destino")
    _garante(destino == "historico", f"destino do formulário de 31/05 23h = {destino!r}")
    from app.formularios import formularios_ops

    with app.app_context():
        settings = SiteSetting.query.get(1)
        settings.release_date = None
        db.session.flush()
        corte = formularios_ops.corte_de_chegada()
        db.session.rollback()
    esperado = datetime(2026, 6, 1, 3, 0)
    _garante(corte == esperado, f"com data de início vazia o corte foi {corte}, esperado {esperado}")


def cen_02() -> None:
    f, hoje = estado["f"], estado["hoje"]
    bloco = _bloco(estado["comercial"])
    _garante(bloco.get("pode_criar_evento") is True, "COMERCIAL deveria poder criar evento")
    b1 = _linha(bloco, f["B1"])
    _garante(b1 is not None and b1[0] == "a_chegar", f"B1 fora de 'a_chegar': {b1}")
    linha = b1[2]
    _garante(linha.get("severidade") == "amarelo", f"B1 (20 dias) com cor {linha.get('severidade')}")
    _garante(linha.get("tipo_rotulo") == "Festa", f"B1 com tipo {linha.get('tipo_rotulo')!r}")
    _garante(linha.get("dias_ate_a_data") == 20, f"B1 dias_ate_a_data={linha.get('dias_ate_a_data')}")
    with app.app_context():
        chegada = db.session.get(FormResponse, f["B1"]).created_at
    esperado = (hoje - _dia_sp(chegada)).days
    _garante(linha.get("dias_desde_chegada") == esperado,
             f"B1 dias_desde_chegada={linha.get('dias_desde_chegada')}, esperado {esperado}")
    b2, b3 = _linha(bloco, f["B2"]), _linha(bloco, f["B3"])
    _garante(b2 and b3, "B2/B3 ausentes")
    _garante(b2[2].get("severidade") == "vermelho", f"B2 (5 dias) com cor {b2[2].get('severidade')}")
    _garante(b3[1] < b2[1], "com a mesma data informada, o que chegou por último deveria vir primeiro")
    fin = _bloco(estado["financeiro"])
    _garante(fin.get("pode_criar_evento") is False, "FINANCEIRO não deveria 'criar evento'")


def cen_03() -> None:
    c1 = _linha(_bloco(estado["comercial"]), estado["f"]["C1"])
    _garante(c1 is not None and c1[0] == "ja_passou", f"C1 fora de 'ja_passou': {c1}")
    _garante(c1[2].get("dias_ate_a_data") == -10, f"C1 dias_ate_a_data={c1[2].get('dias_ate_a_data')}")
    _garante(c1[2].get("severidade") == "amarelo", "todo 'já passou' é amarelo")


def cen_04() -> None:
    d1 = _linha(_bloco(estado["comercial"]), estado["f"]["D1"])
    _garante(d1 is not None, "corporativo ausente da Home")
    _garante(d1[2].get("tipo_rotulo") == "Corporativo", f"tipo {d1[2].get('tipo_rotulo')!r}")
    _garante(d1[2].get("severidade") == "cinza", "a 40 dias a cor é cinza")


def cen_05() -> None:
    f = estado["f"]
    bloco = _bloco(estado["comercial"])
    e1, e2 = _linha(bloco, f["E1"]), _linha(bloco, f["E2"])
    _garante(e1 and e2 and e1[2] is e2[2] or (e1 and e2 and e1[2] == e2[2]),
             "formulários do mesmo telefone deveriam estar numa linha só")
    linha = e2[2]
    _garante(linha.get("representante_id") == f["E2"], "a linha deveria ser representada pelo último")
    _garante(linha.get("repetido") is True, "marca 'preencheu 2 vezes' ausente")
    _garante(linha.get("outro_com_evento") is True, "marca 'já tem outro formulário com evento' ausente")
    r = _chamar(estado["comercial"], "post",
                f"/api/formularios/respostas/{f['E2']}/manter-entre-repetidos", {})
    _garante(r.status_code == 200, f"manter-entre-repetidos → {r.status_code} {r.get_data(as_text=True)[:200]}")
    _garante(_col(f["E1"], "closed_reason") == "repetido", "E1 deveria ter sido encerrado como repetido")
    _garante(_col(f["E2"], "closed_at") is None, "E2 (o que vale) não pode ser encerrado")


def cen_06() -> None:
    f = estado["f"]
    r = _chamar(estado["comercial"], "post", f"/api/formularios/respostas/{f['F2']}/encerrar",
                {"motivo": "outro", "frase": ""})
    _garante(r.status_code == 400, f"'outro' sem frase → {r.status_code}")
    campos = (r.get_json().get("error") or {}).get("fields") or {}
    _garante("frase" in campos, f"o erro deveria apontar o campo frase: {campos}")
    r = _chamar(estado["comercial"], "post", f"/api/formularios/respostas/{f['F1']}/encerrar",
                {"motivo": "desistiu"})
    _garante(r.status_code == 200, f"encerrar → {r.status_code} {r.get_data(as_text=True)[:200]}")
    linha = _no_banco(
        "SELECT closed_reason, closed_by_id, closed_at FROM form_responses WHERE id = :i", i=f["F1"])
    _garante(linha[0] == "desistiu" and linha[1] == estado["comercial_id"] and linha[2] is not None,
             f"encerramento não gravado como esperado: {tuple(linha)}")
    nao_lidas = _no_banco(
        "SELECT count(*) FROM notifications WHERE entity_type='form_response' AND entity_id=:i "
        "AND read_at IS NULL", i=f["F1"])[0]
    _garante(nao_lidas == 0, f"{nao_lidas} aviso(s) ainda acesos depois de encerrar")
    hist = _no_banco(
        "SELECT count(*) FROM audit_logs WHERE entity_type='form_response' AND entity_id=:i "
        "AND action='formulario.encerrado'", i=f["F1"])[0]
    _garante(hist == 1, "encerramento ausente do histórico de ações")
    _garante(_linha(_bloco(estado["comercial"]), f["F1"]) is None, "encerrado continua na Home")


def cen_07() -> None:
    f = estado["f"]
    avisos_antes = _no_banco(
        "SELECT count(*) FROM notifications WHERE entity_type='form_response' AND entity_id=:i",
        i=f["F1"])[0]
    r = _chamar(estado["comercial"], "post", f"/api/formularios/respostas/{f['F1']}/reabrir", {})
    _garante(r.status_code == 200, f"reabrir → {r.status_code}")
    _garante(_col(f["F1"], "closed_at") is None, "reaberto continua encerrado no banco")
    acesos = _no_banco(
        "SELECT count(*) FROM notifications WHERE entity_type='form_response' AND entity_id=:i "
        "AND read_at IS NULL", i=f["F1"])[0]
    avisos_depois = _no_banco(
        "SELECT count(*) FROM notifications WHERE entity_type='form_response' AND entity_id=:i",
        i=f["F1"])[0]
    _garante(acesos == 0 and avisos_depois == avisos_antes, "reabrir não pode reacender nem criar aviso")
    hist = _no_banco(
        "SELECT count(*) FROM audit_logs WHERE entity_type='form_response' AND entity_id=:i "
        "AND action='formulario.reaberto'", i=f["F1"])[0]
    _garante(hist == 1, "reabertura ausente do histórico de ações")
    _garante(_linha(_bloco(estado["comercial"]), f["F1"]) is not None, "reaberto não voltou à Home")
    r = _chamar(estado["comercial"], "post", f"/api/formularios/respostas/{f['F1']}/reabrir", {})
    _garante(r.status_code == 409, f"reabrir de novo → {r.status_code}")


def cen_08() -> None:
    f, e = estado["f"], estado
    linha = _linha(_bloco(e["comercial"]), f["G1"])
    _garante(linha is not None, "G1 ausente")
    sug = linha[2].get("sugestao") or {}
    _garante(sug.get("event_id") == e["ev_m1"], f"empate −1/+1 deveria sugerir o mais cedo: {sug}")
    base = f"/api/formularios/respostas/{f['G1']}/sugestao"
    for _ in range(2):
        r = _chamar(e["comercial"], "post", f"{base}/{e['ev_m1']}/descartar", {})
        _garante(r.status_code == 200, f"descartar → {r.status_code}")
    pares = _no_banco(
        "SELECT count(*) FROM form_response_dismissed_events WHERE form_response_id=:i", i=f["G1"])[0]
    _garante(pares == 1, f"descartar duas vezes gravou {pares} pares")
    sug = (_linha(_bloco(e["comercial"]), f["G1"])[2].get("sugestao") or {})
    _garante(sug.get("event_id") == e["ev_p1"], f"depois do descarte deveria sugerir +1: {sug}")
    r = _chamar(e["comercial"], "post", f"{base}/{e['ev_p1']}/confirmar", {})
    _garante(r.status_code == 200, f"confirmar → {r.status_code} {r.get_data(as_text=True)[:200]}")
    _garante(_col(f["G1"], "event_id") == e["ev_p1"], "confirmar não ligou")


def cen_09() -> None:
    f, e = estado["f"], estado
    r = _chamar(e["comercial"], "post", f"/api/formularios/respostas/{f['H1']}/vincular-evento",
                {"event_id": e["ev9"]})
    _garante(r.status_code == 200, f"vincular → {r.status_code} {r.get_data(as_text=True)[:200]}")
    linha = _no_banco("SELECT client_id, client_link_source FROM form_responses WHERE id=:i", i=f["H1"])
    _garante(linha[0] == e["k9"] and linha[1] == "evento", f"cliente do evento não veio: {tuple(linha)}")
    acesos = _no_banco(
        "SELECT count(*) FROM notifications WHERE entity_type='form_response' AND entity_id=:i "
        "AND read_at IS NULL", i=f["H1"])[0]
    _garante(acesos == 0, "o aviso deveria sumir para todos ao ligar")
    r = _chamar(e["comercial"], "post", f"/api/formularios/respostas/{f['H2']}/vincular-evento",
                {"event_id": e["ev9b"]})
    _garante(r.status_code == 200, f"vincular divergente → {r.status_code}")
    _garante(r.get_json().get("divergencia_cliente"), "divergência não devolvida")
    clientes_ev = _no_banco("SELECT count(*) FROM event_clients WHERE event_id=:i", i=e["ev9b"])[0]
    _garante(clientes_ev == 1, f"a divergência mexeu no evento ({clientes_ev} clientes)")
    r = _chamar(e["comercial"], "post",
                f"/api/formularios/respostas/{f['H2']}/usar-cliente-do-evento", {})
    _garante(r.status_code == 200, f"usar-cliente-do-evento → {r.status_code}")
    linha = _no_banco("SELECT client_id, client_link_source FROM form_responses WHERE id=:i", i=f["H2"])
    _garante(linha[0] == e["k9c"] and linha[1] == "evento", f"cliente não trocada: {tuple(linha)}")


def cen_10() -> None:
    f, e = estado["f"], estado
    com = e["comercial"]
    for nome in ("I1", "I2", "I3", "I4", "I5"):
        if nome == "I3":
            r = _chamar(com, "post", f"/api/formularios/respostas/{f['I3']}/encerrar",
                        {"motivo": "teste"})
            _garante(r.status_code == 200, f"encerrar I3 → {r.status_code}")
        r = _chamar(com, "post", f"/api/formularios/respostas/{f[nome]}/vincular-evento",
                    {"event_id": e[f"ev10_{nome}"]})
        _garante(r.status_code == 200, f"vincular {nome} → {r.status_code}")
    _garante(_col(f["I3"], "closed_at") is None, "ligar deveria desfazer o encerramento")
    with app.app_context():
        db.session.get(CalendarEvent, e["ev10_I1"]).cancelled_at = datetime.utcnow()
        from app.calendar.routes import _delete_event

        _delete_event(db.session.get(CalendarEvent, e["ev10_I2"]), also_from_google=False)
        db.session.commit()
    _garante(_col(f["I1"], "event_id") == e["ev10_I1"], "cancelar o evento soltou o formulário")
    _garante(_col(f["I2"], "event_id") is None, "excluir o evento não soltou o formulário")
    r = _chamar(com, "post", f"/api/formularios/respostas/{f['I4']}/desvincular-evento", {})
    _garante(r.status_code == 200, f"desvincular (tela) → {r.status_code}")
    r = _chamar(com, "patch", f"/api/events/{e['ev10_I5']}/form-response", {"form_response_id": None})
    _garante(r.status_code == 200, f"desvincular (aba Comercial) → {r.status_code}")
    bloco = _bloco(com)
    _garante(_linha(bloco, f["I1"]) is None, "formulário de evento cancelado voltou à Home")
    for nome in ("I2", "I4", "I5"):
        _garante(_linha(bloco, f[nome]) is not None, f"{nome} deveria ter voltado à Home")
    r = _chamar(com, "post", f"/api/formularios/respostas/{f['I6']}/encerrar", {"motivo": "teste"})
    _garante(r.status_code == 422, f"encerrar formulário do histórico → {r.status_code}")


def _para_evento(fid: int) -> dict:
    r = _chamar(estado["comercial"], "get", f"/api/formularios/respostas/{fid}/para-evento")
    _garante(r.status_code == 200, f"para-evento {fid} → {r.status_code} {r.get_data(as_text=True)[:200]}")
    return r.get_json()


def cen_11() -> None:
    f = estado["f"]
    j1 = _para_evento(f["J1"])
    v = j1.get("valores") or {}
    _garante(v.get("start") == "15:00" and v.get("end") == "18:00", f"horário J1: {v.get('start')}–{v.get('end')}")
    loc = v.get("location") or ""
    _garante("Rua das Festas" in loc and "100" in loc and "Contratante" not in loc, f"local J1: {loc!r}")
    _garante(v.get("event_type") == "R&I", f"tipo J1: {v.get('event_type')!r}")
    _garante(v.get("payment_method") == "pix_parcelado" and v.get("payment_installments") == 2,
             f"pagamento J1: {v.get('payment_method')} {v.get('payment_installments')}")
    _garante(v.get("characters") == ["Mickey", "Minnie"], f"personagens J1: {v.get('characters')}")
    rotulos = {o.get("label") for o in j1.get("observacoes") or []}
    _garante("Tema" in rotulos, f"observação 'Tema' ausente: {rotulos}")
    for proibido in ("sale_value", "seller_id", "title"):
        _garante(proibido not in v, f"'{proibido}' não pode vir do formulário")
    j2 = (_para_evento(f["J2"]).get("valores") or {})
    _garante(j2.get("start") == "16:00" and j2.get("end") == "19:00", f"horário WhatsForm: {j2}")
    _garante(j2.get("event_type") == "SHOW", f"tipo WhatsForm: {j2.get('event_type')!r}")
    j3 = _para_evento(f["J3"])
    v3 = j3.get("valores") or {}
    _garante((v3.get("location") or "").startswith("Rua do Evento Corporativo"),
             f"corporativo deveria usar o endereço do evento: {v3.get('location')!r}")
    _garante(v3.get("event_type") == "CORP", "corporativo deveria ser CORP")
    _garante("Briefing" in {o.get("label") for o in j3.get("observacoes") or []}, "briefing ausente")


def cen_12() -> None:
    j4 = _para_evento(estado["f"]["J4"])
    motivos = {a.get("motivo") for a in j4.get("alertas") or []}
    for m in ("data_suspeita", "hora_ausente", "periodo_ambiguo", "endereco_incompleto",
              "sem_correspondente", "tipo_sem_correspondente"):
        _garante(m in motivos, f"alerta {m!r} ausente: {sorted(motivos)}")
    boleto = [a for a in j4["alertas"] if a.get("motivo") == "sem_correspondente"]
    _garante(any("Boleto" in (a.get("texto_da_cliente") or "") for a in boleto),
             "o alerta de pagamento deveria trazer o texto da cliente")
    eventos = {x.get("event_id") for x in j4.get("eventos_da_cliente") or []}
    _garante(estado["ev12"] in eventos, "o evento da cliente sem formulário deveria ser avisado")


def cen_13() -> None:
    r = _chamar(estado["comercial"], "get", "/api/formularios/respostas")
    _garante(r.status_code == 200, f"lista → {r.status_code}")
    counts = r.get_json().get("counts") or {}
    partes = ("sem_destino", "com_evento", "encerrados", "historico")
    _garante(all(p in counts for p in partes) and "corte" in counts, f"contagens: {counts}")
    _garante(sum(counts[p] for p in partes) == counts["total"], f"as partições não somam o total: {counts}")
    home = _bloco(estado["comercial"]).get("contagens") or {}
    _garante(home.get("sem_destino") == counts["sem_destino"],
             f"Home ({home.get('sem_destino')}) × tela ({counts['sem_destino']})")


def cen_14a() -> None:
    f, e = estado["f"], estado
    com = e["comercial"]
    r = _chamar(com, "post", f"/api/formularios/respostas/{f['L1']}/encerrar", {"motivo": "desistiu"})
    _garante(r.status_code == 200, f"encerrar L1 → {r.status_code}")
    from app.formularios import formularios_ops

    with app.app_context():
        formularios_ops.retry_auto_link_pending()
    _garante(_col(f["L1"], "event_id") is None, "o sync religou um formulário encerrado")
    r = _chamar(com, "post", f"/api/formularios/respostas/{f['L2']}/vincular-evento",
                {"event_id": e["ev14c"]})
    _garante(r.status_code == 409, f"segundo vínculo pela tela → {r.status_code}")
    r = _chamar(com, "patch", f"/api/events/{e['ev14c']}/form-response", {"form_response_id": f["L2"]})
    _garante(r.status_code == 409, f"segundo vínculo pela aba Comercial → {r.status_code}")
    with app.app_context():
        try:
            formularios_ops.vincular_formulario_ao_evento(db.session.get(CalendarEvent, e["ev14c"]), f["L2"])
            recusou = False
        except formularios_ops.FormularioJaTemDestino:
            recusou = True
        db.session.rollback()
    _garante(recusou, "a edição do evento deveria recusar formulário de outro evento")
    antes = _google["chamadas"]
    r = _chamar(com, "post", "/api/events", {"form_response_id": f["L2"], "title": TITULO_TESTE})
    _garante(r.status_code == 409, f"POST /api/events com formulário já ligado → {r.status_code}")
    _garante(_google["chamadas"] == antes, "o Google foi chamado")
    _garante(_col(f["L2"], "event_id") == e["ev14b"], "o primeiro vínculo foi trocado")


def cen_14b() -> None:
    f, e = estado["f"], estado
    from app.notificacoes import notificacoes_ops

    with app.app_context():
        gravadas = notificacoes_ops.notificar_resposta_formulario(db.session.get(FormResponse, f["M1"]))
        db.session.commit()
    _garante(gravadas == 0, f"formulário que já nasce ligado gerou {gravadas} aviso(s)")
    runner = app.test_cli_runner()
    saida = runner.invoke(args=["formularios-avisos-resolvidos"])
    _garante(saida.exit_code == 0, f"comando de avisos falhou: {saida.output[-300:]}")
    acesos = _no_banco(
        "SELECT count(*) FROM notifications WHERE entity_type='form_response' AND entity_id=:i "
        "AND read_at IS NULL", i=f["M2"])[0]
    _garante(acesos == 2, "sem --execute o comando não pode alterar nada")
    saida = runner.invoke(args=["formularios-avisos-resolvidos", "--execute"])
    _garante(saida.exit_code == 0, f"comando de avisos --execute falhou: {saida.output[-300:]}")
    acesos = _no_banco(
        "SELECT count(*) FROM notifications WHERE entity_type='form_response' AND entity_id=:i "
        "AND read_at IS NULL", i=f["M2"])[0]
    _garante(acesos == 0, "com --execute os avisos do formulário ligado deveriam ficar lidos")
    saida = runner.invoke(args=["formularios-cliente-do-evento"])
    _garante(saida.exit_code == 0, f"comando de clientes falhou: {saida.output[-300:]}")
    _garante(_col(f["M3"], "client_id") is None, "sem --execute o comando de clientes alterou dados")
    saida = runner.invoke(args=["formularios-cliente-do-evento", "--execute"])
    _garante(saida.exit_code == 0, f"comando de clientes --execute falhou: {saida.output[-300:]}")
    _garante(_col(f["M3"], "client_id") == e["k14d"], "o formulário ligado deveria ganhar a cliente do evento")


def cen_15() -> None:
    f, e = estado["f"], estado
    r = _chamar(e["casting"], "post", f"/api/formularios/respostas/{f['N1']}/encerrar", {"motivo": "teste"})
    _garante(r.status_code == 403, f"CASTING encerrando → {r.status_code} (esperado exatamente 403)")
    r = _chamar(e["financeiro"], "get", f"/api/formularios/respostas/{f['N1']}/para-evento")
    _garante(r.status_code == 403, f"FINANCEIRO pedindo dados do cadastro → {r.status_code}")
    _garante(_col(f["N1"], "closed_at") is None, "o formulário foi alterado por quem não podia")
    r = _chamar(e["comercial"], "get", f"/api/formularios/respostas/{f['N1']}/para-evento")
    _garante(r.status_code == 200, f"controle: COMERCIAL → {r.status_code}")


def limpar() -> None:
    db.session.rollback()
    ids = [r.id for r in FormResponse.query.filter(FormResponse.contact_name.like(f"{PREFIX}%")).all()]
    if ids:
        db.session.execute(text("DELETE FROM notifications WHERE entity_type='form_response' "
                                "AND entity_id = ANY(:ids)"), {"ids": ids})
        db.session.execute(text("DELETE FROM audit_logs WHERE entity_type='form_response' "
                                "AND entity_id = ANY(:ids)"), {"ids": ids})
        db.session.execute(text("DELETE FROM form_response_dismissed_events "
                                "WHERE form_response_id = ANY(:ids)"), {"ids": ids})
        db.session.execute(text("DELETE FROM form_responses WHERE id = ANY(:ids)"), {"ids": ids})
    Notification.query.filter(Notification.title.like(f"%{PREFIX}%")).delete(synchronize_session=False)
    eventos = [ev.id for ev in CalendarEvent.query.filter(CalendarEvent.title.like(f"{PREFIX}%")).all()]
    if eventos:
        for tabela in ("event_clients", "event_logs"):
            db.session.execute(text(f"DELETE FROM {tabela} WHERE event_id = ANY(:ids)"), {"ids": eventos})
        db.session.execute(text("DELETE FROM calendar_events WHERE id = ANY(:ids)"), {"ids": eventos})
    Client.query.filter(Client.name.like(f"{PREFIX}%")).delete(synchronize_session=False)
    for sufixo in ("comercial", "financeiro", "casting"):
        user = User.query.filter_by(email=f"{PREFIX}{sufixo}@manto.local").first()
        if user:
            user.roles.clear()
            db.session.delete(user)
    db.session.commit()


def main() -> int:
    with app.app_context():
        _garante(app.config.get("MAIL_SUPPRESS_SEND") is True,
                 "MAIL_SUPPRESS_SEND desligado — o script mandaria e-mail de verdade")
        limpar()  # sobra de uma rodada interrompida
        preparar()

    print("Feature 298 — o formulário vira evento, contra manto_local")
    try:
        cenario("1. antes do corte fica fora; data de início vazia = 01/06", cen_01)
        cenario("2. grupo, cor, tipo, distância, ordem e papel", cen_02)
        cenario("3. data passada → 'já passou'", cen_03)
        cenario("4. corporativo", cen_04)
        cenario("5. mesmo telefone numa linha; escolher encerra o repetido", cen_05)
        cenario("6. encerrar com motivo", cen_06)
        cenario("7. reabrir", cen_07)
        cenario("8. sugestão: empate, descarte e confirmação", cen_08)
        cenario("9. cliente vem junto; divergência", cen_09)
        cenario("10. cancelado, excluído, desvincular e histórico", cen_10)
        cenario("11. dados para o cadastro nos dois formatos", cen_11)
        cenario("12. alertas do cadastro", cen_12)
        cenario("13. contagens somam e batem com a Home", cen_13)
        cenario("14a. sync e segundo vínculo recusado (Google fora)", cen_14a)
        cenario("14b. aviso que não nasce e comandos de correção", cen_14b)
        cenario("15. papéis sem permissão recebem 403 (DEVEM falhar)", cen_15)
    finally:
        with app.app_context():
            cenario("16. limpeza", limpar)

    ok = sum(1 for _, passou, _ in resultados if passou)
    print(f"\n{ok}/{len(resultados)} OK · chamadas ao Google: {_google['chamadas']}")
    for nome, passou, erro in resultados:
        if not passou:
            print(f"  - {nome}: {erro}")
    return 0 if ok == len(resultados) and _google["chamadas"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
