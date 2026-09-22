"""Verificação da feature 301 — todo o comercial vê e abre o orçamento de qualquer colega.

Cenários (a tabela da seção "Verificação" da spec):
   1. A salva um orçamento; B lista o histórico e vê a linha de A, com o nome de A e
      `pode_excluir` falso — e verdadeiro na linha do próprio B.
   2. B abre o detalhe do orçamento de A: 200 com `quote` **e** `form_snapshot`.
   3. B filtra por vendedor (`user_id`) — o filtro deixa de ser privilégio de superadmin.
   4. B baixa o PDF do orçamento de A.
   5. B reenvia o e-mail do orçamento de A: 200 **e** linha de auditoria gravada (conexão
      separada). Reenviar o PRÓPRIO orçamento não gera linha.
   6. Evento vinculado ao orçamento de A: B abre o evento e recebe o resumo do orçamento.
   7. B vincula o orçamento de A a um evento SEM orçamento: 200 e FK gravado (conexão separada).
   8. B tenta trocar e soltar o vínculo do orçamento de A — **DEVE falhar** (409, com o nome de A).
   9. B tenta re-aplicar o orçamento de A no evento já vinculado a A, nas DUAS formas (valores +
      data, e só equipe) — **DEVE falhar**, e nada do evento muda.
  10. B tenta apagar um orçamento de A **sem evento vivo vinculado** — **DEVE falhar** (404) — e
      logo depois A apaga o mesmo e conclui 200.
  11. F (FINANCEIRO) tenta listar o histórico — **DEVE falhar** (403).
  12. F tenta vincular o orçamento de A a um evento — **DEVE falhar** (404).
  13. Limpeza.

DOIS ARRANJOS SÃO OBRIGATÓRIOS, e sem eles este arquivo passa verde sem testar nada:

* **Cenário 9** — aplicar é IDEMPOTENTE (`set_event_orcamento`: "só cria/marca o que falta") e
  `aplicar_fora_sp_do_orcamento` só escreve quando há o que escrever. Se o evento nascesse
  vinculado pelo caminho normal, a equipe e o fora de SP já estariam lá e uma re-aplicação
  **aceita** também não mudaria nada — a asserção "inalterado" seria verdadeira dos dois jeitos.
  Por isso o vínculo do `ev_reaplicar` é gravado DIRETO no banco, sem aplicar nada, com um
  orçamento que vende fora de SP e equipe de apoio, e num evento **sem venda**.
* **Cenário 10** — o DELETE tem DUAS recusas: a autoria (404) e o evento vivo vinculado (409). Com
  um orçamento amarrado a evento, o 409 recusaria sozinho e o cenário passaria mesmo se a trava de
  autoria tivesse sido solta junto com a de leitura — que é justamente o erro simétrico que ele
  existe para pegar. Por isso usa um orçamento **sem evento**, espera **404** (não "recusa") e
  fecha com o contraste: o mesmo DELETE feito por A conclui 200.

ESCRITA SE CONFERE POR CONEXÃO SEPARADA (`_no_banco`): o autoflush da sessão do app mostra o que
ainda não foi commitado, e foi assim que o hotfix 257 passou verde com os anexos sumindo.

REQUISIÇÕES HTTP FICAM FORA DE `app.app_context()`: contexto persistente vaza o usuário entre
requisições e faz cenário de permissão passar por engano — e aqui cinco cenários DEVEM falhar.

Rodar contra o manto_local (PowerShell)::

    $env:DATABASE_URL = (gc .local-db-url -Raw).Trim(); $env:FLASK_ENV = "development"; $env:MANTO_SEM_THREADS = "1"
    .venv/Scripts/python.exe specs/301-orcamentos-visiveis-comercial/verify_301.py
"""

from __future__ import annotations

import json
import os
import sys
import traceback
import uuid
from collections.abc import Callable
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path

for _stream in (sys.stdout, sys.stderr):  # console do Windows em cp1252
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))
os.environ.setdefault("FLASK_ENV", "development")
os.environ.setdefault("MANTO_SEM_THREADS", "1")
os.environ.setdefault("MAIL_SUPPRESS_SEND", "true")  # cinto, além do suspensório do localhost
if not os.environ.get("DATABASE_URL"):
    os.environ["DATABASE_URL"] = (REPO_ROOT / ".local-db-url").read_text(encoding="utf-8").strip()

from sqlalchemy import create_engine, text  # noqa: E402

from app import create_app, db, limiter, maps  # noqa: E402
from app import email_service as es  # noqa: E402
from app.calendar import routes as cal_routes  # noqa: E402
from app.calendar import service as cal_service  # noqa: E402
from app.constants import RoleName, now_sp  # noqa: E402
from app.models import CalendarEvent, EventRole, OrcamentoHistory, Role, User  # noqa: E402

PREFIX = "__v301_"
SENHA = "verify-301-senha"
DESTINO = "__v301_destino@manto.local"  # endereço descartável; o envio está travado de duas formas

app = create_app()
app.config["TESTING"] = True
# Muitos logins: o "10 per hour" de /api/auth/login estoura. `RATELIMIT_ENABLED` depois do
# `create_app` não desliga nada — o objeto sim.
limiter.enabled = False

resultados: list[tuple[str, bool, str]] = []
estado: dict = {}
_externo = create_engine(os.environ["DATABASE_URL"], future=True)

# ── dublês: nada sai para o Google nem para o SMTP ───────────────────────────────────────────────
maps.cidade_do_endereco = lambda _e: (None, None)
cal_routes._fetch_travel_data = lambda _ev, _s: {}
cal_service.insert_event = lambda *a, **k: {"id": f"{PREFIX}g{uuid.uuid4().hex[:10]}"}
cal_service.update_event = lambda *a, **k: None
cal_service.delete_event = lambda *a, **k: None
cal_routes.insert_event = cal_service.insert_event
_emails: list[str] = []


def _fake_quote_email(to: str, client_name: str, pdf_bytes: bytes) -> bool:
    _emails.append(to)
    return True


es.send_quote_email = _fake_quote_email


def _no_banco(sql: str, **params):
    """Conexão separada — a única testemunha confiável de que algo foi commitado."""
    with _externo.connect() as conn:
        return conn.execute(text(sql), params).fetchall()


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


def _login(c, email: str) -> None:
    r = c.post("/api/auth/login", json={"email": email, "password": SENHA})
    _garante(r.status_code == 200, f"login {email} → {r.status_code}")


# ── fixtures (dentro de app_context) ─────────────────────────────────────────────────────────────


def _usuario(sufixo: str, *papeis: str) -> User:
    user = User(
        name=f"{PREFIX}{sufixo}",
        email=f"{PREFIX}{sufixo}@manto.local",
        is_active=True,
        has_access=True,
    )
    user.set_password(SENHA)
    for p in papeis:
        user.roles.append(Role.query.filter_by(name=p).one())
    db.session.add(user)
    db.session.commit()
    return user


def _orcamento(
    dono_id: int,
    sufixo: str,
    *,
    fora_sp: bool = False,
    km: float = 0,
    coordenadores: int = 1,
    has_show: bool = False,
    performers: list[dict] | None = None,
) -> OrcamentoHistory:
    data = (now_sp().date() + timedelta(days=45)).isoformat()
    performers = performers or [
        {"type": "ator", "subtipo": "cara_limpa", "nome": "Bluey", "makeup": False}
    ]
    snap = {
        "performers": performers,
        "coordenador_qty": coordenadores,
        "fora_sp": fora_sp,
        "km_ida": km,
        "transporte_tipo": "carro",
        "num_carros": 1,
        "num_colaboradores": len(performers) + coordenadores,
        "event_date": data,
        "event_time": "15:00",
        "nota_fiscal": True,
        "acrescimos": [],
    }
    entry = OrcamentoHistory(
        user_id=dono_id,
        client_name=f"{PREFIX}{sufixo}",
        event_location=f"{PREFIX}Sítio, Jundiaí",
        event_date=data,
        total_1h=Decimal("3000"),
        total_2h=Decimal("4200"),
        total_3h=Decimal("5000"),
        total_4h=Decimal("5600"),
        has_show=has_show,
        form_snapshot=json.dumps(snap),
    )
    db.session.add(entry)
    db.session.commit()
    return entry


def _evento(sufixo: str, *, dias: int = 45, orcamento_id: int | None = None) -> CalendarEvent:
    inicio = datetime.combine(
        now_sp().date() + timedelta(days=dias), datetime.min.time()
    ).replace(hour=15)
    ev = CalendarEvent(
        title=f"{PREFIX}{sufixo}",
        event_type="SHOW",
        start_at=inicio,
        end_at=inicio + timedelta(hours=2),
        google_event_id=f"{PREFIX}{uuid.uuid4().hex[:8]}",
        source="google_calendar",
        location=f"{PREFIX}Sítio, Jundiaí",
        # Vínculo gravado DIRETO, sem passar pelo endpoint: é o que mantém o evento "com algo
        # ainda por escrever" e torna a asserção do cenário 9 capaz de falhar.
        orcamento_history_id=orcamento_id,
    )
    db.session.add(ev)
    db.session.flush()
    db.session.add(EventRole(event_id=ev.id, character_name="Bluey", role_type="character"))
    db.session.commit()
    return ev


def _linha_evento(eid: int):
    return _no_banco(
        "SELECT orcamento_history_id, sale_value, sale_date, is_outside_sp FROM calendar_events"
        " WHERE id = :i",
        i=eid,
    )[0]


def _qtd_papeis(eid: int) -> int:
    return _no_banco("SELECT count(*) FROM event_roles WHERE event_id = :i", i=eid)[0][0]


def _qtd_auditoria(orc_id: int) -> int:
    return _no_banco(
        "SELECT count(*) FROM audit_logs WHERE entity_type = 'orcamento' AND entity_id = :i",
        i=orc_id,
    )[0][0]


def _ultima_auditoria(orc_id: int):
    """A linha em si, não a contagem. SC-008 pede que o reenvio seja **reconstituível** — quem
    enviou, qual orçamento e para quem —, e contar linhas prova só que existe alguma."""
    linhas = _no_banco(
        "SELECT actor_name, detail FROM audit_logs WHERE entity_type = 'orcamento'"
        " AND entity_id = :i ORDER BY id DESC LIMIT 1",
        i=orc_id,
    )
    return linhas[0] if linhas else None


def preparar() -> None:
    limpar()
    a = _usuario("a", RoleName.COMERCIAL)
    b = _usuario("b", RoleName.COMERCIAL)
    f = _usuario("f", RoleName.FINANCEIRO)
    estado.update(
        a_email=a.email, a_id=a.id, a_nome=a.name,
        b_email=b.email, b_id=b.id, b_nome=b.name,
        f_email=f.email,
    )

    # Orçamentos de A, um por cenário — o 1:1 entre orçamento e evento vivo obriga a separar.
    estado["orc_leitura"] = _orcamento(a.id, "leitura").id
    estado["orc_evento"] = _orcamento(a.id, "evento").id
    estado["orc_vincular"] = _orcamento(a.id, "vincular").id
    estado["orc_trocar"] = _orcamento(a.id, "trocar").id
    estado["orc_alvo"] = _orcamento(a.id, "alvo").id
    estado["orc_delete"] = _orcamento(a.id, "delete").id  # de propósito SEM evento (cenário 10)
    estado["orc_fin"] = _orcamento(a.id, "fin").id
    estado["orc_de_b"] = _orcamento(b.id, "deb").id

    # Orçamento do cenário 9: vende fora de SP e equipe de apoio, para que uma re-aplicação
    # ACEITA tivesse o que escrever. Sem isso a asserção "inalterado" nasce verdadeira.
    estado["orc_reaplicar"] = _orcamento(
        a.id,
        "reaplicar",
        fora_sp=True,
        km=120,
        coordenadores=3,
        has_show=True,
        performers=[
            {"type": "ator", "subtipo": "cara_limpa", "nome": "Elsa", "makeup": True, "show": True},
            {"type": "cantor", "subtipo": "cantor", "nome": "Anna", "makeup": True, "show": True},
        ],
    ).id

    estado["ev_detalhe"] = _evento("ev-detalhe", orcamento_id=estado["orc_evento"]).id
    estado["ev_livre"] = _evento("ev-livre", dias=46).id
    estado["ev_trocar"] = _evento("ev-trocar", dias=47, orcamento_id=estado["orc_trocar"]).id
    estado["ev_reaplicar"] = _evento(
        "ev-reaplicar", dias=48, orcamento_id=estado["orc_reaplicar"]
    ).id
    estado["ev_fin"] = _evento("ev-fin", dias=49).id


def limpar() -> None:
    ids = [
        r[0]
        for r in _no_banco(
            "SELECT id FROM calendar_events WHERE title LIKE :p OR google_event_id LIKE :p",
            p=f"%{PREFIX}%",
        )
    ]
    for eid in ids:
        for tabela in ("commission_payments", "event_logs", "event_roles", "event_clients"):
            db.session.execute(text(f"DELETE FROM {tabela} WHERE event_id = :i"), {"i": eid})
    db.session.commit()
    for eid in ids:
        ev = CalendarEvent.query.get(eid)
        if ev is not None:
            db.session.delete(ev)
    db.session.commit()
    orcs = OrcamentoHistory.query.filter(OrcamentoHistory.client_name.like(f"{PREFIX}%")).all()
    for o in orcs:
        db.session.execute(
            text("DELETE FROM audit_logs WHERE entity_type = 'orcamento' AND entity_id = :i"),
            {"i": o.id},
        )
        db.session.delete(o)
    db.session.commit()
    # `roles.clear()` ANTES do delete: apagar em massa estoura a FK de `user_roles`.
    for u in User.query.filter(User.email.like(f"{PREFIX}%")).all():
        u.roles.clear()
        db.session.delete(u)
    db.session.commit()


# ───────────────────────────── cenários ─────────────────────────────


def cen_01_lista_do_time() -> None:
    with app.test_client() as c:
        _login(c, estado["b_email"])
        r = c.get("/api/orcamento/historico?q=" + PREFIX)
    _garante(r.status_code == 200, f"listagem → {r.status_code}")
    corpo = r.get_json()
    _garante(
        "is_superadmin" not in corpo,
        "a chave `is_superadmin` continua no payload (R5): ela só servia para esconder tela",
    )
    por_id = {e["id"]: e for e in corpo["entries"]}
    linha_a = por_id.get(estado["orc_leitura"])
    _garante(linha_a is not None, "B não enxerga o orçamento de A — a trava de leitura continua lá")
    _garante(
        linha_a["user_name"] == estado["a_nome"],
        f"coluna Vendedor: {linha_a['user_name']!r} ≠ {estado['a_nome']!r}",
    )
    _garante(linha_a.get("pode_excluir") is False, "B não pode excluir o orçamento de A (FR-006)")
    linha_b = por_id.get(estado["orc_de_b"])
    _garante(linha_b is not None and linha_b.get("pode_excluir") is True, "B pode excluir o próprio")
    _garante(
        any(u["id"] == estado["a_id"] for u in corpo.get("users", [])),
        "a lista de vendedores do filtro não veio para quem não é superadmin (FR-005)",
    )


def cen_02_detalhe_de_outro() -> None:
    with app.test_client() as c:
        _login(c, estado["b_email"])
        r = c.get(f"/api/orcamento/historico/{estado['orc_leitura']}")
    _garante(r.status_code == 200, f"detalhe → {r.status_code} {r.get_data(as_text=True)[:200]}")
    corpo = r.get_json()
    _garante("quote" in corpo and corpo["quote"], "sem `quote` no detalhe")
    _garante("form_snapshot" in corpo and corpo["form_snapshot"], "sem `form_snapshot` (Recalcular)")


def cen_03_filtro_por_vendedor() -> None:
    with app.test_client() as c:
        _login(c, estado["b_email"])
        ra = c.get(f"/api/orcamento/historico?q={PREFIX}&user_id={estado['a_id']}")
        rb = c.get(f"/api/orcamento/historico?q={PREFIX}&user_id={estado['b_id']}")
    _garante(ra.status_code == 200 and rb.status_code == 200, "filtro por vendedor recusado")
    ids_a = {e["id"] for e in ra.get_json()["entries"]}
    ids_b = {e["id"] for e in rb.get_json()["entries"]}
    _garante(estado["orc_leitura"] in ids_a, "filtro por A não trouxe o orçamento de A")
    _garante(estado["orc_de_b"] not in ids_a, "filtro por A trouxe orçamento de B")
    _garante(ids_b == {estado["orc_de_b"]}, f"filtro por B trouxe demais: {ids_b}")


def cen_04_pdf_de_outro() -> None:
    with app.test_client() as c:
        _login(c, estado["b_email"])
        r = c.get(f"/api/orcamento/historico/{estado['orc_leitura']}/pdf")
    _garante(r.status_code == 200, f"PDF → {r.status_code}")
    _garante("pdf" in (r.headers.get("Content-Type") or "").lower(), f"tipo: {r.headers.get('Content-Type')}")


def cen_05_email_de_outro_auditado() -> None:
    antes = _qtd_auditoria(estado["orc_leitura"])
    with app.test_client() as c:
        _login(c, estado["b_email"])
        r = c.post(
            f"/api/orcamento/historico/{estado['orc_leitura']}/enviar-email",
            json={"to": DESTINO},
        )
    _garante(r.status_code == 200, f"e-mail → {r.status_code} {r.get_data(as_text=True)[:200]}")
    _garante(r.get_json().get("sent") is True, "resposta sem `sent: true`")
    depois = _qtd_auditoria(estado["orc_leitura"])
    _garante(
        depois == antes + 1,
        f"auditoria do reenvio alheio não persistiu ({antes}→{depois}) — `audit()` só faz `add`, "
        "a view precisa commitar (FR-013, hotfix 257)",
    )
    linha = _ultima_auditoria(estado["orc_leitura"])
    _garante(linha is not None, "auditoria gravada mas ilegível")
    ator, detalhe = linha[0], linha[1] or ""
    _garante(ator == estado["b_nome"], f"ator errado na auditoria: {ator!r} ≠ {estado['b_nome']!r}")
    _garante(DESTINO in detalhe, f"o destinatário não está no registro: {detalhe!r}")
    _garante(
        estado["a_nome"] in detalhe,
        f"o registro não diz de quem era o orçamento: {detalhe!r} (SC-008 pede reconstituível)",
    )
    # O próprio orçamento não gera linha.
    antes_b = _qtd_auditoria(estado["orc_de_b"])
    with app.test_client() as c:
        _login(c, estado["b_email"])
        r2 = c.post(
            f"/api/orcamento/historico/{estado['orc_de_b']}/enviar-email", json={"to": DESTINO}
        )
    _garante(r2.status_code == 200, f"e-mail do próprio → {r2.status_code}")
    _garante(
        _qtd_auditoria(estado["orc_de_b"]) == antes_b,
        "reenvio do PRÓPRIO orçamento gerou auditoria — FR-013 manda registrar só o alheio",
    )


def cen_06_evento_mostra_orcamento_alheio() -> None:
    with app.test_client() as c:
        _login(c, estado["b_email"])
        r = c.get(f"/api/events/{estado['ev_detalhe']}")
    _garante(r.status_code == 200, f"evento → {r.status_code}")
    venda = (r.get_json() or {}).get("venda") or {}
    orc = venda.get("orcamento")
    _garante(orc is not None, "a aba Comercial não recebeu o orçamento de outra pessoa (FR-009)")
    _garante(orc.get("id") == estado["orc_evento"], f"orçamento errado no payload: {orc.get('id')}")
    _garante(
        orc.get("autor") == estado["a_nome"],
        f"chave `autor` ausente ou errada: {orc.get('autor')!r} (não é `vendedor`: `venda.seller` "
        "já existe e é o vendedor DO EVENTO)",
    )
    _garante(
        orc.get("pode_gerir") is False,
        "`pode_gerir` deveria ser falso para B — sem essa flag a tela volta a deduzir permissão "
        "do silêncio do payload e passa a oferecer botão que o servidor recusa (R3)",
    )


def cen_07_vincular_orcamento_de_outro() -> None:
    with app.test_client() as c:
        _login(c, estado["b_email"])
        r = c.patch(
            f"/api/events/{estado['ev_livre']}/orcamento",
            json={"orcamento_history_id": estado["orc_vincular"]},
        )
    _garante(r.status_code == 200, f"vincular → {r.status_code} {r.get_data(as_text=True)[:300]}")
    orc_id, _v, _d, _f = _linha_evento(estado["ev_livre"])
    _garante(
        orc_id == estado["orc_vincular"],
        f"vínculo não persistiu (conexão separada): {orc_id}",
    )


def cen_08_trocar_e_soltar_alheio() -> None:
    antes = _linha_evento(estado["ev_trocar"])[0]
    with app.test_client() as c:
        _login(c, estado["b_email"])
        troca = c.patch(
            f"/api/events/{estado['ev_trocar']}/orcamento",
            json={"orcamento_history_id": estado["orc_alvo"]},
        )
        solta = c.patch(
            f"/api/events/{estado['ev_trocar']}/orcamento", json={"orcamento_history_id": None}
        )
    for nome, r in (("trocar", troca), ("desvincular", solta)):
        _garante(r.status_code == 409, f"{nome} de vínculo alheio → {r.status_code}, esperado 409")
        # As chaves extras de `json_error` moram DENTRO do envelope `{"error": {...}}`.
        corpo = (r.get_json() or {}).get("error") or {}
        _garante(corpo.get("orcamento_de_outro") is True, f"{nome}: sem `orcamento_de_outro`")
        texto = json.dumps(corpo, ensure_ascii=False)
        _garante(
            estado["a_nome"] in texto,
            f"{nome}: a recusa não nomeia o autor (FR-010) — {texto[:200]}",
        )
    _garante(_linha_evento(estado["ev_trocar"])[0] == antes, "o vínculo mudou apesar da recusa")


def cen_09_reaplicar_alheio() -> None:
    antes = _linha_evento(estado["ev_reaplicar"])
    papeis_antes = _qtd_papeis(estado["ev_reaplicar"])
    _garante(
        antes[1] is None and antes[3] is not True,
        f"arranjo do cenário 9 quebrado: o evento já tem venda/fora-de-SP ({antes}) — uma "
        "re-aplicação aceita não mudaria nada e a asserção nasceria vazia",
    )
    with app.test_client() as c:
        _login(c, estado["b_email"])
        com_valores = c.patch(
            f"/api/events/{estado['ev_reaplicar']}/orcamento",
            json={
                "orcamento_history_id": estado["orc_reaplicar"],
                "aplicar_valores_duracao": 2,
                "sale_date": now_sp().date().isoformat(),
            },
        )
        so_equipe = c.patch(
            f"/api/events/{estado['ev_reaplicar']}/orcamento",
            json={"orcamento_history_id": estado["orc_reaplicar"], "aplicar_equipe": True},
        )
    for nome, r in (("valores+data", com_valores), ("só equipe", so_equipe)):
        _garante(
            r.status_code == 409,
            f"re-aplicar ({nome}) em vínculo alheio → {r.status_code}, esperado 409 — este é o vão "
            "que o 404 do alvo escondia (research R2)",
        )
    depois = _linha_evento(estado["ev_reaplicar"])
    _garante(depois == antes, f"o evento mudou apesar da recusa: {antes} → {depois}")
    _garante(
        _qtd_papeis(estado["ev_reaplicar"]) == papeis_antes,
        "a equipe foi aplicada apesar da recusa",
    )


def cen_10_delete_alheio_sem_evento() -> None:
    orc = estado["orc_delete"]
    vivo = _no_banco(
        "SELECT count(*) FROM calendar_events WHERE orcamento_history_id = :i"
        " AND cancelled_at IS NULL",
        i=orc,
    )[0][0]
    _garante(
        vivo == 0,
        f"arranjo do cenário 10 quebrado: o orçamento tem {vivo} evento(s) vivo(s) — o 409 "
        "recusaria sozinho e o cenário passaria mesmo com a trava de autoria solta",
    )
    with app.test_client() as c:
        _login(c, estado["b_email"])
        r = c.delete(f"/api/orcamento/historico/{orc}")
    _garante(r.status_code == 404, f"DELETE alheio → {r.status_code}, esperado 404 (FR-006/FR-010)")
    sobrou = _no_banco("SELECT count(*) FROM orcamento_history WHERE id = :i", i=orc)[0][0]
    _garante(sobrou == 1, "o orçamento de A foi apagado por B")
    # Contraste: o 404 tem de vir da AUTORIA, não do estado do registro.
    with app.test_client() as c:
        _login(c, estado["a_email"])
        ra = c.delete(f"/api/orcamento/historico/{orc}")
    _garante(ra.status_code in (200, 204), f"A não conseguiu apagar o próprio: {ra.status_code}")
    _garante(
        _no_banco("SELECT count(*) FROM orcamento_history WHERE id = :i", i=orc)[0][0] == 0,
        "o DELETE de A respondeu OK mas não apagou (falta commit?)",
    )


def cen_11_financeiro_no_historico() -> None:
    with app.test_client() as c:
        _login(c, estado["f_email"])
        r = c.get("/api/orcamento/historico")
    _garante(r.status_code == 403, f"FINANCEIRO no histórico → {r.status_code}, esperado 403")


def cen_12_financeiro_nao_vincula_alheio() -> None:
    antes = _linha_evento(estado["ev_fin"])[0]
    with app.test_client() as c:
        _login(c, estado["f_email"])
        r = c.patch(
            f"/api/events/{estado['ev_fin']}/orcamento",
            json={"orcamento_history_id": estado["orc_fin"]},
        )
    _garante(
        r.status_code == 404,
        f"FINANCEIRO vinculando orçamento alheio → {r.status_code}, esperado 404. Ele passa no "
        "`_can_manage_sale()`; quem o barra hoje é o 404-por-dono que esta feature remove — a "
        "remoção tem de ser condicionada ao papel (FR-011, SC-005)",
    )
    _garante(_linha_evento(estado["ev_fin"])[0] == antes, "o FINANCEIRO vinculou mesmo assim")


def cen_13_limpeza() -> None:
    limpar()
    _garante(
        OrcamentoHistory.query.filter(OrcamentoHistory.client_name.like(f"{PREFIX}%")).count() == 0,
        "orçamento descartável sobrou",
    )
    _garante(
        CalendarEvent.query.filter(CalendarEvent.title.like(f"{PREFIX}%")).count() == 0,
        "evento descartável sobrou",
    )
    _garante(
        User.query.filter(User.email.like(f"{PREFIX}%")).count() == 0, "usuário descartável sobrou"
    )


def main() -> int:
    print("Feature 301 — todo o comercial vê e abre o orçamento de qualquer colega")
    with app.app_context():
        preparar()
    try:
        cenario("1. B vê o orçamento de A na lista, com vendedor e pode_excluir", cen_01_lista_do_time)
        cenario("2. B abre o detalhe congelado de A (quote + form_snapshot)", cen_02_detalhe_de_outro)
        cenario("3. filtro por vendedor vale para quem não é superadmin", cen_03_filtro_por_vendedor)
        cenario("4. B baixa o PDF do orçamento de A", cen_04_pdf_de_outro)
        cenario("5. B reenvia o e-mail de A e a auditoria persiste; o próprio não audita", cen_05_email_de_outro_auditado)
        cenario("6. evento de A: B recebe resumo, autor e pode_gerir=false", cen_06_evento_mostra_orcamento_alheio)
        cenario("7. B vincula o orçamento de A a evento sem orçamento", cen_07_vincular_orcamento_de_outro)
        cenario("8. **deve falhar** B trocar/soltar vínculo alheio → 409 com o nome de A", cen_08_trocar_e_soltar_alheio)
        cenario("9. **deve falhar** B re-aplicar alheio (valores e só equipe) → 409, nada muda", cen_09_reaplicar_alheio)
        cenario("10. **deve falhar** B apagar orçamento de A sem evento → 404; A apaga → 200", cen_10_delete_alheio_sem_evento)
        cenario("11. **deve falhar** FINANCEIRO no histórico → 403", cen_11_financeiro_no_historico)
        cenario("12. **deve falhar** FINANCEIRO vinculando orçamento alheio → 404", cen_12_financeiro_nao_vincula_alheio)
    finally:
        with app.app_context():
            cenario("13. limpeza", cen_13_limpeza)
    ok = sum(1 for _, passou, _ in resultados if passou)
    print(f"{ok}/{len(resultados)} OK")
    return 0 if ok == len(resultados) else 1


if __name__ == "__main__":
    sys.exit(main())
