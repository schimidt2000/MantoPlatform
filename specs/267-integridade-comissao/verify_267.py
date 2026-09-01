"""Verificação da feature 267 — integridade do vínculo e a comissão que bate.

Cenários:
 1. Comissão EducaManto (venda num mês, realização em outro) liquidada pelo mês da REALIZAÇÃO
    persiste — hoje o clique atualiza 0 linhas e o item volta para "não pago".
 2. O mês da VENDA não liquida essa mesma comissão (o inverso do bug: hoje ele liquida uma
    comissão que nem exibe).
 3. O controle INDIVIDUAL tem o mesmo comportamento do lote (são 4 cópias do mesmo filtro).
 4. `paid_at` usa o relógio de São Paulo, não o do processo.
 5. Venda preenchida pelo PATCH em bloco (`/api/events/<id>`) cria a linha de comissão — hoje só
    a criação e o painel inline criam.
 6. KPI do evento: com linha real usa o valor da linha; sem linha cai na regra canônica; venda da
    Loja Virtual e evento cancelado mostram R$ 0,00.
 7. Vincular pré-contrato pela tela do evento marca `manual`+`locked` e injeta a cliente em
    `event_clients` (paridade com o caminho da tela de formulários).
 8. Excluir evento solta a resposta e limpa o rastro do vínculo, sem apagá-la.
 9. Limpeza total.

Rodar contra o manto_local (PowerShell)::

    $env:DATABASE_URL = (gc .local-db-url -Raw).Trim(); $env:FLASK_ENV = "development"
    .venv/Scripts/python.exe specs/267-integridade-comissao/verify_267.py
"""

from __future__ import annotations

import os
import sys
import traceback
from collections.abc import Callable
from datetime import date, datetime, timedelta
from decimal import Decimal
from pathlib import Path

for _stream in (sys.stdout, sys.stderr):  # console do Windows em cp1252
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))
os.environ.setdefault("FLASK_ENV", "development")
if not os.environ.get("DATABASE_URL"):
    os.environ["DATABASE_URL"] = (REPO_ROOT / ".local-db-url").read_text(encoding="utf-8").strip()

from sqlalchemy import create_engine, text  # noqa: E402

from app import create_app, db  # noqa: E402
from app.constants import RoleName, now_sp  # noqa: E402
from app.models import (  # noqa: E402
    CalendarEvent,
    Client,
    CommissionPayment,
    EventClient,
    FormResponse,
    Role,
    User,
)

PREFIX = "__v267_"
SENHA = "verify-267-senha"

# Venda em MARÇO, realização em MAIO — é o recorte que expõe o bug: o item aparece no ciclo de
# maio (coalesce) e a liquidação procura a venda em maio, onde ela não está.
MES_VENDA = date(2026, 3, 10)
MES_REALIZACAO = date(2026, 5, 20)
TAG_REALIZACAO = "2026-05"
TAG_VENDA = "2026-03"

app = create_app()
app.config["TESTING"] = True

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
        db.session.rollback()
        resultados.append((nome, False, traceback.format_exc().strip().splitlines()[-1]))
        print(f"  FALHA  {nome}: {exc}")


def _garante(cond: bool, msg: str) -> None:
    if not cond:
        raise AssertionError(msg)


def _usuario(sufixo: str, papel: str) -> User:
    email = f"{PREFIX}{sufixo}@manto.local"
    user = User.query.filter_by(email=email).first()
    if user is None:
        user = User(name=f"{PREFIX}{sufixo}", email=email, is_active=True, has_access=True)
        db.session.add(user)
    user.set_password(SENHA)
    user.roles.clear()
    user.roles.append(Role.query.filter_by(name=papel).one())
    db.session.commit()
    return user


def _login(c, user: User) -> None:
    r = c.post("/api/auth/login", json={"email": user.email, "password": SENHA})
    _garante(r.status_code == 200, f"login {user.email} → {r.status_code}")


def _comissao_educamanto(status: str = "a_pagar") -> CommissionPayment:
    """Linha com ciclo pela REALIZAÇÃO (payable_from preenchido) — o caso EducaManto."""
    linha = CommissionPayment(
        event_id=None,
        event_title=f"{PREFIX}(EDU) COMISSAO CICLO",
        seller_id=estado["vendedor"].id,
        sale_date=MES_VENDA,
        payable_from=MES_REALIZACAO,
        amount=Decimal("123.45"),
        status=status,
    )
    db.session.add(linha)
    db.session.commit()
    return linha


def _set_status(c, item_id: str, status: str):
    return c.post(
        "/api/financeiro/pagamentos/set-status",
        json={"item_type": "commission", "item_id": item_id, "status": status},
    )


# ── Cenários ─────────────────────────────────────────────────────────


def cen_01_liquida_pelo_mes_da_realizacao() -> None:
    linha = _comissao_educamanto()
    with app.test_client() as c:
        _login(c, estado["financeiro"])
        r = _set_status(c, f"{estado['vendedor'].id}:{TAG_REALIZACAO}", "pago")
        _garante(r.status_code == 200, f"set-status → {r.status_code} {r.get_data(as_text=True)[:200]}")
    no_banco = _no_banco(
        "SELECT status, paid_at FROM commission_payments WHERE id = :i", i=linha.id
    )
    _garante(
        no_banco.status == "pago",
        f"liquidada pelo mês da realização não persistiu: status={no_banco.status}",
    )
    estado["linha_1"] = linha.id


def cen_02_mes_da_venda_nao_liquida() -> None:
    linha = _comissao_educamanto()
    with app.test_client() as c:
        _login(c, estado["financeiro"])
        _set_status(c, f"{estado['vendedor'].id}:{TAG_VENDA}", "pago")
    no_banco = _no_banco("SELECT status FROM commission_payments WHERE id = :i", i=linha.id)
    _garante(
        no_banco.status == "a_pagar",
        f"o mês da VENDA liquidou uma comissão que ele nem exibe: status={no_banco.status}",
    )
    estado["linha_2"] = linha.id


def cen_03_bulk_tem_o_mesmo_comportamento() -> None:
    linha = _comissao_educamanto()
    with app.test_client() as c:
        _login(c, estado["financeiro"])
        r = c.post(
            "/api/financeiro/pagamentos/bulk-action",
            json={
                "action": "pago",
                "items": [{"item_type": "commission", "item_id": f"{estado['vendedor'].id}:{TAG_REALIZACAO}"}],
            },
        )
        _garante(r.status_code == 200, f"bulk → {r.status_code} {r.get_data(as_text=True)[:200]}")
    no_banco = _no_banco("SELECT status FROM commission_payments WHERE id = :i", i=linha.id)
    _garante(no_banco.status == "pago", f"o lote não alcançou a linha: status={no_banco.status}")
    estado["linha_3"] = linha.id


def cen_04_paid_at_no_relogio_de_sp() -> None:
    """`date.today()` em produção (UTC) carimba o pagamento no dia seguinte depois das 21h de SP."""
    import inspect

    from app.financeiro import comissoes_ops

    fonte = inspect.getsource(comissoes_ops)
    codigo = "\n".join(
        linha for linha in fonte.splitlines() if not linha.strip().startswith("#")
    )
    _garante(
        "liquidar_periodo" in codigo,
        "a liquidação não foi extraída para comissoes_ops (4 cópias continuam divergindo)",
    )
    _garante(
        "date.today()" not in codigo.split("def liquidar_periodo")[1][:900],
        "liquidar_periodo ainda carimba paid_at com date.today() (UTC em produção)",
    )
    linha = _no_banco(
        "SELECT paid_at FROM commission_payments WHERE id = :i", i=estado["linha_1"]
    )
    _garante(
        linha.paid_at == now_sp().date(),
        f"paid_at fora do relógio de SP: {linha.paid_at} (esperado {now_sp().date()})",
    )


def cen_05_patch_em_bloco_cria_comissao() -> None:
    evento = estado["evento"]
    _garante(
        CommissionPayment.query.filter_by(event_id=evento.id).count() == 0,
        "pré-condição: o evento não podia ter linha de comissão ainda",
    )
    with app.test_client() as c:
        _login(c, estado["superadmin"])
        r = c.patch(
            f"/api/events/{evento.id}",
            json={
                "title": evento.title,
                "event_type": "R&I",
                "date": evento.start_at.date().isoformat(),
                "start": "15:00",
                "end": "17:00",
                # Número, não string: `_validate_event_core` compara com 0 (routes.py:3213).
                "sale_value": 3000.0,
                "sale_value_gross": 3000.0,
                "sale_date": now_sp().date().isoformat(),
                "seller_id": estado["vendedor"].id,
            },
        )
        _garante(r.status_code == 200, f"PATCH em bloco → {r.status_code} {r.get_data(as_text=True)[:300]}")
    linha = _no_banco(
        "SELECT id, amount, seller_id FROM commission_payments WHERE event_id = :e", e=evento.id
    )
    _garante(linha is not None, "a venda pelo formulário completo não gerou linha de comissão")
    _garante(
        linha.seller_id == estado["vendedor"].id,
        f"comissão no vendedor errado: {linha.seller_id}",
    )
    _garante(Decimal(str(linha.amount)) > 0, f"valor da comissão: {linha.amount}")


def cen_06_kpi_le_a_comissao_real() -> None:
    evento = estado["evento"]
    with app.test_client() as c:
        _login(c, estado["superadmin"])
        r = c.get(f"/api/events/{evento.id}")
        _garante(r.status_code == 200, f"detalhe → {r.status_code}")
        kpi = r.get_json().get("kpi")
        _garante(kpi is not None, "KPI ausente para SUPERADMIN")
        linha = _no_banco(
            "SELECT amount FROM commission_payments WHERE event_id = :e", e=evento.id
        )
        _garante(
            abs(Decimal(str(kpi["commission"])) - Decimal(str(linha.amount))) < Decimal("0.01"),
            f"KPI={kpi['commission']} ≠ linha real={linha.amount}",
        )
        _garante(
            kpi.get("commission_source") == "linha",
            f"origem do número não sinalizada: {kpi.get('commission_source')}",
        )

    # Evento cancelado: o backref fica vazio, e sem a guarda o fallback inventaria número.
    evento.cancelled_at = datetime.now()
    db.session.commit()
    with app.test_client() as c:
        _login(c, estado["superadmin"])
        kpi = c.get(f"/api/events/{evento.id}").get_json().get("kpi")
        _garante(
            Decimal(str(kpi["commission"])) == Decimal("0"),
            f"evento cancelado exibindo comissão: {kpi['commission']}",
        )
    evento.cancelled_at = None
    db.session.commit()


def cen_07_vinculo_pela_tela_do_evento() -> None:
    evento = estado["evento"]
    resposta = estado["resposta"]
    with app.test_client() as c:
        _login(c, estado["superadmin"])
        r = c.patch(
            f"/api/events/{evento.id}/form-response", json={"form_response_id": resposta.id}
        )
        _garante(r.status_code == 200, f"vincular → {r.status_code} {r.get_data(as_text=True)[:200]}")
    linha = _no_banco(
        "SELECT event_id, event_link_source, event_link_locked FROM form_responses WHERE id = :i",
        i=resposta.id,
    )
    _garante(linha.event_id == evento.id, f"vínculo não gravou: {linha.event_id}")
    _garante(linha.event_link_source == "manual", f"origem: {linha.event_link_source}")
    _garante(
        linha.event_link_locked is True,
        "sem locked o retry do próximo sync religa e desfaz a decisão humana",
    )
    vinculo = _no_banco(
        "SELECT id FROM event_clients WHERE event_id = :e AND client_id = :c",
        e=evento.id, c=estado["cliente"].id,
    )
    _garante(vinculo is not None, "a cliente da resposta não entrou em event_clients")


def cen_08_exclusao_solta_a_resposta() -> None:
    # Evento próprio: o do cenário 5 tem venda registrada, e o endpoint recusa com 409 excluir
    # evento com dinheiro preso (é caso de cancelamento, não de exclusão).
    evento = estado["evento_exclusao"]
    resposta = estado["resposta_exclusao"]
    resposta_id = resposta.id
    # Pré-condição explícita: sem um rastro para limpar, o teste passaria trivialmente.
    resposta.event_id = evento.id
    resposta.event_link_source = "auto_date"
    resposta.event_link_ambiguous = True
    db.session.commit()
    _garante(
        _no_banco(
            "SELECT event_link_source FROM form_responses WHERE id = :i", i=resposta_id
        ).event_link_source == "auto_date",
        "pré-condição não gravou o rastro de vínculo",
    )
    with app.test_client() as c:
        _login(c, estado["superadmin"])
        r = c.delete(f"/api/events/{evento.id}")
        _garante(
            r.status_code in (200, 204),
            f"excluir evento → {r.status_code} {r.get_data(as_text=True)[:300]}",
        )
    linha = _no_banco(
        "SELECT event_id, event_link_source FROM form_responses WHERE id = :i", i=resposta_id
    )
    _garante(linha is not None, "a resposta foi apagada junto — devia ser só desvinculada")
    _garante(linha.event_id is None, f"event_id órfão: {linha.event_id}")
    _garante(
        linha.event_link_source is None,
        f"rastro obsoleto do vínculo: {linha.event_link_source}",
    )
    estado.pop("evento_exclusao", None)


# ── Preparo e limpeza ────────────────────────────────────────────────


def preparar() -> None:
    limpar()
    estado["financeiro"] = _usuario("financeiro", RoleName.FINANCEIRO)
    estado["superadmin"] = _usuario("superadmin", RoleName.SUPERADMIN)
    estado["vendedor"] = _usuario("vendedor", RoleName.COMERCIAL)

    cliente = Client(
        name=f"{PREFIX}Cliente 267",
        phone="5511977770267",
        phone_display="+55 (11) 97777-0267",
        source="manual",
    )
    db.session.add(cliente)
    db.session.flush()
    estado["cliente"] = cliente

    inicio = datetime.combine(now_sp().date() + timedelta(days=60), datetime.min.time()).replace(
        hour=15
    )
    evento = CalendarEvent(
        title=f"{PREFIX}(R&I) VERIFY 267",
        start_at=inicio,
        end_at=inicio + timedelta(hours=2),
        google_event_id=f"{PREFIX}evt267",
        source="platform",
    )
    db.session.add(evento)
    db.session.flush()
    estado["evento"] = evento

    resposta = FormResponse(
        form_type="comum",
        data="[]",
        contact_name=f"{PREFIX}Contratante 267",
        contact_phone=cliente.phone,
        event_date=inicio.date(),
        client_id=cliente.id,
        client_link_source="manual",
    )
    db.session.add(resposta)

    # Segundo par evento+resposta, sem venda: é o do cenário 8 (o endpoint recusa excluir
    # evento com dinheiro preso, e o evento principal ganha venda no cenário 5).
    inicio_excl = inicio + timedelta(days=7)
    evento_excl = CalendarEvent(
        title=f"{PREFIX}(R&I) VERIFY 267 EXCLUSAO",
        start_at=inicio_excl,
        end_at=inicio_excl + timedelta(hours=2),
        google_event_id=f"{PREFIX}evt267excl",
        source="platform",
    )
    db.session.add(evento_excl)
    db.session.flush()
    estado["evento_exclusao"] = evento_excl

    resposta_excl = FormResponse(
        form_type="comum",
        data="[]",
        contact_name=f"{PREFIX}Contratante 267 exclusao",
        contact_phone=cliente.phone,
        event_date=inicio_excl.date(),
    )
    db.session.add(resposta_excl)
    db.session.commit()
    estado["resposta"] = resposta
    estado["resposta_exclusao"] = resposta_excl


def limpar() -> None:
    db.session.rollback()
    CommissionPayment.query.filter(
        CommissionPayment.event_title.like(f"{PREFIX}%")
    ).delete(synchronize_session=False)
    for r in FormResponse.query.filter(FormResponse.contact_name.like(f"{PREFIX}%")).all():
        db.session.delete(r)
    db.session.flush()
    # `_clear_event_side_tables` é quem sabe das tabelas laterais SEM cascade (EventLog,
    # EventContract, EventPayment, EventRating, ClientFeedback, EventReimbursement) — sem ela o
    # delete estoura violação de FK (docs/04 §1, invariante 8).
    from app.calendar.routes import _clear_event_side_tables

    # Por `google_event_id`, não por título: a criação/edição PREFIXA o tipo no título
    # (`(R&I) …`), então um filtro ancorado no início do título perde o evento depois do PATCH.
    for e in CalendarEvent.query.filter(CalendarEvent.google_event_id.like("%v267%")).all():
        _clear_event_side_tables(e.id)
        EventClient.query.filter_by(event_id=e.id).delete(synchronize_session=False)
        CommissionPayment.query.filter_by(event_id=e.id).delete(synchronize_session=False)
        FormResponse.query.filter_by(event_id=e.id).update(
            {"event_id": None}, synchronize_session=False
        )
        db.session.delete(e)
    # Commit por fase: numa transação só o SQLAlchemy pode tentar apagar o usuário antes do
    # evento que o referencia como `seller_id`, e a FK estoura.
    db.session.commit()

    for c in Client.query.filter(Client.name.like(f"{PREFIX}%")).all():
        EventClient.query.filter_by(client_id=c.id).delete(synchronize_session=False)
        FormResponse.query.filter_by(client_id=c.id).update(
            {"client_id": None}, synchronize_session=False
        )
        db.session.delete(c)
    db.session.commit()

    for sufixo in ("financeiro", "superadmin", "vendedor"):
        user = User.query.filter_by(email=f"{PREFIX}{sufixo}@manto.local").first()
        if user:
            CommissionPayment.query.filter_by(seller_id=user.id).delete(synchronize_session=False)
            # Evento de outro teste que tenha ficado apontando para este vendedor.
            CalendarEvent.query.filter_by(seller_id=user.id).update(
                {"seller_id": None}, synchronize_session=False
            )
            db.session.commit()
            user.roles.clear()
            db.session.delete(user)
            db.session.commit()


def main() -> int:
    with app.app_context():
        try:
            preparar()
            print("Feature 267 — integridade e comissão, contra manto_local")
            cenario("1. liquida pelo mês da REALIZAÇÃO (EducaManto)", cen_01_liquida_pelo_mes_da_realizacao)
            cenario("2. mês da VENDA não liquida a mesma linha", cen_02_mes_da_venda_nao_liquida)
            cenario("3. lote com o mesmo comportamento do individual", cen_03_bulk_tem_o_mesmo_comportamento)
            cenario("4. paid_at no relógio de SP + fonte única", cen_04_paid_at_no_relogio_de_sp)
            cenario("5. PATCH em bloco cria a linha de comissão", cen_05_patch_em_bloco_cria_comissao)
            cenario("6. KPI lê a comissão real (e cancelado = 0)", cen_06_kpi_le_a_comissao_real)
            cenario("7. vínculo pela tela do evento: manual + locked + cliente", cen_07_vinculo_pela_tela_do_evento)
            cenario("8. exclusão solta a resposta sem apagá-la", cen_08_exclusao_solta_a_resposta)
        finally:
            cenario("9. limpeza", limpar)
    ok = sum(1 for _, passou, _ in resultados if passou)
    print(f"\n{ok}/{len(resultados)} OK")
    for nome, passou, erro in resultados:
        if not passou:
            print(f"  - {nome}: {erro}")
    return 0 if ok == len(resultados) else 1


if __name__ == "__main__":
    sys.exit(main())
