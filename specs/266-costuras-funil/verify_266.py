"""Verificação da feature 266 — costuras do funil (o lead aparece e tudo leva a tudo).

Cenários:
 1. Submissão pública com telefone de cliente existente → resposta nasce com `client_id`
    preenchido e `client_link_source="auto_phone"`.
 2. Submissão com telefone desconhecido → `client_id` nulo, sem erro, resposta salva.
 3. Submissão com telefone conhecido E evento real na data → o auto-vínculo de evento continua
    funcionando (não regrediu) e a cliente entra em `event_clients`.
 4. Associar pela tela grava `client_link_source="manual"`; desassociar zera os DOIS campos.
 5. Cliente criado a partir de resposta nasce `source="formulario"` e a origem aparece nas
    métricas (as duas metades: o valor gravado e o mapa que o traduz).
 6. Excluir cliente que tem resposta de formulário conclui sem erro (hoje: IntegrityError) e a
    resposta volta para a fila "sem cliente".
 7. Payload do dashboard traz o bloco `formularios` para COMERCIAL e **não** traz para CASTING
    (RBAC por ausência de chave, não por 403); os contadores batem com a listagem.
 8. `futuros_sem_evento` usa o relógio de São Paulo (a festa de hoje continua na fila).
 9. Limpeza total.

Toda asserção de escrita confere por **conexão separada** (lição do hotfix 257): o autoflush da
própria sessão esconde ausência de commit.

Rodar contra o manto_local (PowerShell)::

    $env:DATABASE_URL = (gc .local-db-url -Raw).Trim(); $env:FLASK_ENV = "development"
    .venv/Scripts/python.exe specs/266-costuras-funil/verify_266.py
"""

from __future__ import annotations

import os
import sys
import traceback
from collections.abc import Callable
from datetime import datetime, timedelta
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
    EventClient,
    FormResponse,
    Role,
    User,
)

PREFIX = "__v266_"
SENHA = "verify-266-senha"
TEL_CONHECIDO_NAC = "(11) 97666-0001"
TEL_DESCONHECIDO_NAC = "(11) 97666-0999"
# Data distante o bastante para não haver evento real na agenda: isola os cenários de
# vínculo de CLIENTE do vínculo de EVENTO.
DATA_LIVRE = "2029-11-13"

app = create_app()
app.config["TESTING"] = True
app.config["RATELIMIT_ENABLED"] = False  # o submit público é 10/hora; o teste faz mais que isso

resultados: list[tuple[str, bool, str]] = []
estado: dict = {}

# Conexão separada: confirma o que foi COMITADO, não o que a sessão do teste tem em memória.
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


def _payload_formulario(nome: str, tel_nacional: str, data_evento: str | None) -> dict:
    """Monta o corpo do POST público a partir do schema VIGENTE no banco.

    Preenche todo campo obrigatório com um valor plausível para o tipo, e sobrescreve os
    campos-sistema que o teste precisa controlar (nome, telefone, data). Assim o script não
    quebra quando alguém edita a estrutura do formulário pelo editor.
    """
    from app.formularios.formularios_ops import FORM_META, _load_fields

    dados: dict[str, str] = {}
    for campo in _load_fields("comum"):
        if not campo.required:
            continue
        tipo = campo.field_type
        if tipo == "data":
            dados[campo.field_key] = DATA_LIVRE
        elif tipo == "hora":
            dados[campo.field_key] = "14:00"
        elif tipo == "email":
            dados[campo.field_key] = "verify266@example.com"
        elif tipo == "telefone":
            dados[f"{campo.field_key}_ddi"] = "+55"
            dados[f"{campo.field_key}_national"] = tel_nacional
        elif tipo == "sim_nao":
            dados[campo.field_key] = "Sim"
        elif tipo == "selecao":
            opcoes = campo.options_list or [""]
            dados[campo.field_key] = opcoes[0]
        elif tipo == "cpf":
            dados[campo.field_key] = "12345678901"
        elif tipo == "cnpj":
            dados[campo.field_key] = "12345678000190"
        elif tipo == "cep":
            dados[campo.field_key] = "01310100"
        else:
            dados[campo.field_key] = f"{PREFIX}valor"
    dados[FORM_META["comum"]["name_key"]] = nome
    dados["whatsapp_ddi"] = "+55"
    dados["whatsapp_national"] = tel_nacional
    # `data_evento` é obrigatório no formulário; sem data explícita usamos uma sem evento na
    # agenda, para o auto-vínculo de evento não interferir nos cenários de cliente.
    dados["data_evento"] = data_evento or DATA_LIVRE
    return dados


def _submeter(nome: str, tel_nacional: str, data_evento: str | None = None) -> FormResponse:
    with app.test_client() as c:
        r = c.post(
            "/api/formularios/comum",
            data=_payload_formulario(nome, tel_nacional, data_evento),
            content_type="application/x-www-form-urlencoded",
        )
        _garante(r.status_code == 201, f"submit → {r.status_code} {r.get_data(as_text=True)[:300]}")
    resposta = (
        FormResponse.query.filter(FormResponse.contact_name == nome)
        .order_by(FormResponse.id.desc())
        .first()
    )
    _garante(resposta is not None, f"resposta de {nome} não foi salva")
    return resposta


# ── Cenários ─────────────────────────────────────────────────────────


def cen_01_auto_associa_por_telefone() -> None:
    resposta = _submeter(f"{PREFIX}Contratante Conhecida", TEL_CONHECIDO_NAC)
    estado["resposta_1"] = resposta.id
    linha = _no_banco(
        "SELECT client_id, client_link_source FROM form_responses WHERE id = :i", i=resposta.id
    )
    _garante(
        linha.client_id == estado["client_conhecido"],
        f"client_id no banco: {linha.client_id} (esperado {estado['client_conhecido']})",
    )
    _garante(
        linha.client_link_source == "auto_phone",
        f"origem do vínculo: {linha.client_link_source}",
    )


def cen_02_telefone_desconhecido_nao_associa() -> None:
    resposta = _submeter(f"{PREFIX}Lead Novo", TEL_DESCONHECIDO_NAC)
    estado["resposta_2"] = resposta.id
    linha = _no_banco(
        "SELECT client_id, client_link_source FROM form_responses WHERE id = :i", i=resposta.id
    )
    _garante(linha.client_id is None, f"não podia associar: client_id={linha.client_id}")
    _garante(linha.client_link_source is None, f"origem indevida: {linha.client_link_source}")


def cen_03_evento_na_data_mantem_auto_vinculo() -> None:
    evento = estado["evento"]
    data_iso = evento.start_at.date().isoformat()
    resposta = _submeter(f"{PREFIX}Com Evento", TEL_CONHECIDO_NAC, data_iso)
    estado["resposta_3"] = resposta.id
    linha = _no_banco(
        "SELECT event_id, event_link_source, client_id FROM form_responses WHERE id = :i",
        i=resposta.id,
    )
    _garante(linha.event_id == evento.id, f"auto-vínculo de evento regrediu: {linha.event_id}")
    _garante(linha.event_link_source == "auto_date", f"origem: {linha.event_link_source}")
    _garante(linha.client_id == estado["client_conhecido"], "cliente não foi associado")
    vinculo = _no_banco(
        "SELECT id FROM event_clients WHERE event_id = :e AND client_id = :c",
        e=evento.id, c=estado["client_conhecido"],
    )
    _garante(vinculo is not None, "cliente não entrou em event_clients")


def cen_04_manual_e_desassociar() -> None:
    resposta_id = estado["resposta_2"]
    with app.test_client() as c:
        _login(c, estado["comercial"])
        r = c.post(
            f"/api/formularios/respostas/{resposta_id}/associar",
            json={"client_id": estado["client_conhecido"]},
        )
        _garante(r.status_code == 200, f"associar → {r.status_code} {r.get_data(as_text=True)[:200]}")
        linha = _no_banco(
            "SELECT client_id, client_link_source FROM form_responses WHERE id = :i", i=resposta_id
        )
        _garante(linha.client_link_source == "manual", f"origem manual: {linha.client_link_source}")

        r = c.post(f"/api/formularios/respostas/{resposta_id}/desassociar")
        _garante(r.status_code == 200, f"desassociar → {r.status_code}")
    linha = _no_banco(
        "SELECT client_id, client_link_source FROM form_responses WHERE id = :i", i=resposta_id
    )
    _garante(linha.client_id is None, f"client_id sobrou: {linha.client_id}")
    _garante(linha.client_link_source is None, f"origem sobrou: {linha.client_link_source}")


def cen_05_origem_formulario() -> None:
    """Cliente criado a partir da resposta nasce 'formulario' e aparece no gráfico."""
    resposta_id = estado["resposta_2"]
    with app.test_client() as c:
        _login(c, estado["comercial"])
        r = c.post(f"/api/formularios/respostas/{resposta_id}/associar", json={})
        _garante(r.status_code == 200, f"criar cliente → {r.status_code} {r.get_data(as_text=True)[:200]}")
    linha = _no_banco(
        """SELECT c.id, c.source FROM clients c
           JOIN form_responses f ON f.client_id = c.id WHERE f.id = :i""",
        i=resposta_id,
    )
    _garante(linha is not None, "cliente não foi criado a partir da resposta")
    _garante(linha.source == "formulario", f"source do cliente: {linha.source}")
    estado["client_criado"] = linha.id

    with app.test_client() as c:
        _login(c, estado["comercial"])
        r = c.get("/api/clientes/metricas")
        _garante(r.status_code == 200, f"métricas → {r.status_code}")
        meses = r.get_json()["new_by_month"]
        _garante(bool(meses), "métricas vieram vazias")
        # A metade que costuma faltar: o mapa `source_keys` traduzindo o valor novo.
        _garante(
            meses[-1]["formulario"] >= 1,
            f"origem 'formulario' não subiu no gráfico: {meses[-1]}",
        )


def cen_06_excluir_cliente_solta_resposta() -> None:
    """Hoje isto estoura IntegrityError: a relação com Client não tem backref."""
    resposta_id = estado["resposta_2"]
    client_id = estado["client_criado"]
    with app.test_client() as c:
        _login(c, estado["superadmin"])
        r = c.delete(f"/api/clientes/{client_id}")
        _garante(
            r.status_code in (200, 204),
            f"excluir cliente → {r.status_code} {r.get_data(as_text=True)[:300]}",
        )
    _garante(
        _no_banco("SELECT id FROM clients WHERE id = :i", i=client_id) is None,
        "cliente não foi excluído",
    )
    linha = _no_banco(
        "SELECT client_id, client_link_source FROM form_responses WHERE id = :i", i=resposta_id
    )
    _garante(linha is not None, "a resposta foi apagada junto — devia ser só desvinculada")
    _garante(linha.client_id is None, f"client_id órfão: {linha.client_id}")
    _garante(linha.client_link_source is None, f"origem órfã: {linha.client_link_source}")
    estado.pop("client_criado", None)


def cen_07_dashboard_bloco_e_rbac() -> None:
    from app.formularios.formularios_ops import count_status

    esperado = count_status()
    with app.test_client() as c:
        _login(c, estado["comercial"])
        r = c.get("/api/dashboard")
        _garante(r.status_code == 200, f"dashboard COMERCIAL → {r.status_code}")
        body = r.get_json()
        _garante("formularios" in body, "bloco 'formularios' ausente para COMERCIAL")
        bloco = body["formularios"]
        _garante(bloco is not None, "bloco veio nulo para COMERCIAL")
        for chave in ("total", "sem_evento", "sem_cliente", "ambiguos", "futuros_sem_evento"):
            _garante(chave in bloco, f"contador '{chave}' ausente no bloco")
            _garante(
                bloco[chave] == esperado[chave],
                f"contador '{chave}': dashboard={bloco[chave]} listagem={esperado[chave]}",
            )
    with app.test_client() as c:
        _login(c, estado["casting"])
        r = c.get("/api/dashboard")
        _garante(r.status_code == 200, f"dashboard CASTING → {r.status_code}")
        # RBAC por ausência de chave/valor nulo — nunca por 403 (docs/00 §4).
        _garante(
            r.get_json().get("formularios") is None,
            "CASTING não pode receber o bloco de formulários",
        )


def cen_08_relogio_sao_paulo() -> None:
    """A festa de HOJE tem de continuar na fila 'futuros sem evento'.

    ⚠️ A metade comportamental deste teste é CEGA na máquina do dev: rodando em UTC-3,
    `date.today()` e `now_sp().date()` são o mesmo valor e o bug não aparece. Ele só se
    manifesta em produção (UTC), das 21h à meia-noite de Brasília. Por isso a asserção que
    realmente vale é a segunda: a condição do filtro tem de usar o relógio canônico.
    """
    import inspect

    from app.formularios.formularios_ops import _status_condition, list_responses

    hoje_sp = now_sp().date()
    resposta = FormResponse.query.get(estado["resposta_1"])
    resposta.event_date = hoje_sp
    resposta.event_id = None
    db.session.commit()

    ids = [r.id for r in list_responses(filtro="futuros_sem_evento")]
    _garante(
        resposta.id in ids,
        f"resposta com festa hoje ({hoje_sp}) sumiu da fila de futuros sem evento",
    )
    # Sem as linhas de comentário: o comentário que EXPLICA por que não usar `date.today()`
    # não pode reprovar o teste.
    codigo = "\n".join(
        linha for linha in inspect.getsource(_status_condition).splitlines()
        if not linha.strip().startswith("#")
    )
    _garante("date.today()" not in codigo, "_status_condition ainda usa date.today() (UTC em produção)")
    _garante("now_sp()" in codigo, "_status_condition não usa o relógio canônico now_sp()")


# ── Preparo e limpeza ────────────────────────────────────────────────


def preparar() -> None:
    limpar()
    estado["comercial"] = _usuario("comercial", RoleName.COMERCIAL)
    estado["casting"] = _usuario("casting", RoleName.CASTING)
    estado["superadmin"] = _usuario("superadmin", RoleName.SUPERADMIN)

    from app.clientes.importer import normalize_phone

    telefone = normalize_phone(f"+55 {TEL_CONHECIDO_NAC}")
    cliente = Client(
        name=f"{PREFIX}Cliente Recorrente",
        phone=telefone,
        phone_display=f"+55 {TEL_CONHECIDO_NAC}",
        source="manual",
    )
    db.session.add(cliente)
    db.session.flush()
    estado["client_conhecido"] = cliente.id

    # Evento real (não ensaio, não satélite) numa data futura livre, com a cliente associada:
    # é a dupla confirmação que o auto-vínculo de evento exige.
    inicio = datetime.combine(now_sp().date() + timedelta(days=45), datetime.min.time()).replace(
        hour=15
    )
    evento = CalendarEvent(
        title=f"{PREFIX}(R&I) VERIFY 266",
        start_at=inicio,
        end_at=inicio + timedelta(hours=2),
        google_event_id=f"{PREFIX}evt",
        source="platform",
    )
    db.session.add(evento)
    db.session.flush()
    db.session.add(EventClient(event_id=evento.id, client_id=cliente.id, relationship_type="Contratante"))
    db.session.commit()
    estado["evento"] = evento


def limpar() -> None:
    db.session.rollback()
    respostas = FormResponse.query.filter(FormResponse.contact_name.like(f"{PREFIX}%")).all()
    for r in respostas:
        db.session.delete(r)
    db.session.flush()
    eventos = CalendarEvent.query.filter(CalendarEvent.title.like(f"{PREFIX}%")).all()
    for e in eventos:
        EventClient.query.filter_by(event_id=e.id).delete(synchronize_session=False)
        FormResponse.query.filter_by(event_id=e.id).update(
            {"event_id": None}, synchronize_session=False
        )
        db.session.delete(e)
    db.session.flush()
    clientes = Client.query.filter(Client.name.like(f"{PREFIX}%")).all()
    for c in clientes:
        EventClient.query.filter_by(client_id=c.id).delete(synchronize_session=False)
        FormResponse.query.filter_by(client_id=c.id).update(
            {"client_id": None}, synchronize_session=False
        )
        db.session.delete(c)
    for sufixo in ("comercial", "casting", "superadmin"):
        user = User.query.filter_by(email=f"{PREFIX}{sufixo}@manto.local").first()
        if user:
            user.roles.clear()
            db.session.delete(user)
    db.session.commit()


def main() -> int:
    with app.app_context():
        _garante(
            app.config.get("MAIL_SUPPRESS_SEND") is True,
            "MAIL_SUPPRESS_SEND desligado — o script mandaria e-mail de verdade",
        )
        try:
            preparar()
            print("Feature 266 — costuras do funil, contra manto_local")
            cenario("1. auto-associa cliente pelo telefone", cen_01_auto_associa_por_telefone)
            cenario("2. telefone desconhecido não associa", cen_02_telefone_desconhecido_nao_associa)
            cenario("3. auto-vínculo de evento intacto + event_clients", cen_03_evento_na_data_mantem_auto_vinculo)
            cenario("4. associar grava manual / desassociar zera", cen_04_manual_e_desassociar)
            cenario("5. cliente da resposta nasce 'formulario'", cen_05_origem_formulario)
            cenario("6. excluir cliente solta a resposta", cen_06_excluir_cliente_solta_resposta)
            cenario("7. bloco do dashboard + RBAC por ausência", cen_07_dashboard_bloco_e_rbac)
            cenario("8. futuros_sem_evento no relógio de SP", cen_08_relogio_sao_paulo)
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
