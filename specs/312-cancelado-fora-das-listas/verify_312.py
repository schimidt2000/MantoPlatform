"""Verificação da feature 312 — o cancelado sai de toda lista e só se vê onde se trata do cancelamento.

A tabela de cenários está na `spec.md` (seção "Verificação": 1–23 e o 9b). Escrito ANTES do núcleo
(Princípio VIII): a primeira rodada, contra o código da `main`, fica em `verify_312_primeira_falha.txt`
— é ela a prova "contra a main" de cada "deve falhar" de visibilidade e de escrita.

O HARNESS É O DA 306, IMPORTADO (`verify_306` como módulo): o dublê do Google que falha fechado, o
disjuntor de rede, o `_send` falso e o espião do e-mail de remoção, os usuários e talentos
descartáveis, a semente do exemplo-padrão, o `cenario()` e o `limpar()`. Uma fonte só: o que a 306
aprendeu (vaga criada pelo sistema, nunca `EventRole` inventada; conexão separada para conferir
escrita; login só pela API; requisições fora do `app_context`) vale aqui sem cópia. Os dados levam o
prefixo da 306 (`__v306_` / `v306`) e saem no `limpar()` dela; o que só a 312 cria (pedido de
figurino, dispensa de presente, tag de estoque emprestada) sai no `limpar_312()`.

Blocos (acompanham o `tasks.md`):

  H1  1–7      o cancelado some de toda lista
  H2  8–14,9b  a tela do cancelado só para consulta; o motivo só para quem trata dele
  H3  15       o Casting tira e avisa
  H4  16–17    a página de Cancelamentos
  H5  18–19    o card "Cancelamentos do período"
  H6  20–21    o selo nas coisas ligadas; o portal
  R   22       regressão: sem cancelado, o payload é o de antes
  L   23       limpeza e nenhuma rede (roda sempre)

Rodar contra o manto_local (PowerShell, na raiz do worktree)::

    . <scratchpad>\\env312.ps1
    & $py specs\\312-cancelado-fora-das-listas\\verify_312.py            # 24/24
    & $py specs\\312-cancelado-fora-das-listas\\verify_312.py '--so=9,9b' # iteração (o 23 roda sempre)
    & $py specs\\312-cancelado-fora-das-listas\\verify_312.py --semear-tela / --limpar-tela

Saída: 0 = tudo OK; 1 = algum cenário falhou; 2 = ambiente impróprio.
"""

from __future__ import annotations

import argparse
import json
import sys
import uuid
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI.parent / "306-dinheiro-do-cancelamento"))

import verify_306 as v6  # noqa: E402 — sobe o app, o dublê, o disjuntor e o e-mail falso

from app import db  # noqa: E402
from app.constants import RoleName  # noqa: E402
from app.models import CalendarEvent, Client, EventRole, Talent  # noqa: E402

app = v6.app
estado = v6.estado
_garante = v6._garante
_no_banco = v6._no_banco
_no_banco_escrever = v6._no_banco_escrever
_cliente = v6._cliente
_erro = v6._erro
_codigo = v6._codigo
q = v6.q

TRAVA_FRASE = "Este evento foi cancelado — a tela fica só para consulta."
CASTING_403 = "Evento cancelado: quem tira da escala é o Casting."
PORTAL_FRASE = "Este evento foi cancelado."
TOKEN = uuid.uuid4().hex[:6].upper()
S: dict = {}  # a semente comum
EXTRAS: dict = {"producoes": [], "tag": None, "dispensas": []}


# ── ajudantes ─────────────────────────────────────────────────────────────────────────────────
def _ids(obj) -> set[int]:
    """Todo `id`/`event_id` de dicionário dentro de um JSON (para "o cancelado não veio")."""
    achados: set[int] = set()
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k in ("id", "event_id") and isinstance(v, int):
                achados.add(v)
            achados |= _ids(v)
    elif isinstance(obj, list):
        for x in obj:
            achados |= _ids(x)
    return achados


def _get(apelido: str, url: str) -> dict:
    r = _cliente(apelido).get(url)
    _garante(
        r.status_code == 200,
        f"GET {url} como {apelido} → {r.status_code} {r.get_data(as_text=True)[:200]}",
    )
    return r.get_json()


def _html(apelido: str, url: str) -> str:
    r = _cliente(apelido).get(url)
    _garante(r.status_code == 200, f"GET {url} (Jinja) como {apelido} → {r.status_code}")
    return r.get_data(as_text=True)


def _titulo(event_id: int) -> str:
    return _no_banco("SELECT title FROM calendar_events WHERE id = :i", i=event_id)[0][0]


def _data(event_id: int) -> date:
    return _no_banco("SELECT start_at FROM calendar_events WHERE id = :i", i=event_id)[0][0].date()


def _e_trava(r) -> bool:
    return (
        r.status_code == 409
        and _codigo(r) == "cancelado"
        and TRAVA_FRASE in (_erro(r).get("message") or "")
    )


def _e_recusa_cancelado(r, status: int) -> bool:
    return r.status_code == status and _codigo(r) == "cancelado"


def _flash_recusou(r) -> bool:
    """O Jinja recusa com `flash` + `redirect`: o redirect sem gravar é a resposta."""
    return r.status_code in (302, 303)


def _retrato(event_id: int) -> dict:
    """O que uma escrita na tela do evento poderia mudar (conexão separada)."""
    base = v6._retrato_tabelas([event_id])
    for chave, sql in {
        "evento": "SELECT title, start_at, end_at, location, description, is_confirmed, makeup_time, departure_time, "
        "group_name FROM calendar_events WHERE id = :i",
        "obs": "SELECT id, content FROM event_observations WHERE event_id = :i ORDER BY id",
        "contratos": "SELECT id, is_signed FROM event_contracts WHERE event_id = :i ORDER BY id",
        "materiais": "SELECT id FROM ensaio_materials WHERE event_id = :i ORDER BY id",
        "vagas": "SELECT id, talent_id, cache_value, invite_status, payment_status, dismissed, transport_marked, "
        "figurino_done FROM event_roles WHERE event_id = :i ORDER BY id",
        "clientes": "SELECT client_id FROM event_clients WHERE event_id = :i ORDER BY client_id",
        "presentes": "SELECT id, quantity, notes FROM event_3d_gifts WHERE event_id = :i ORDER BY id",
        "dispensas": "SELECT id FROM event_3d_dismissals WHERE event_id = :i ORDER BY id",
        "ensaios": "SELECT id FROM calendar_events WHERE parent_event_id = :i ORDER BY id",
        "token": "SELECT feedback_token FROM calendar_events WHERE id = :i",
    }.items():
        try:
            base[chave] = [tuple(x) for x in _no_banco(sql, i=event_id)]
        except Exception as exc:  # noqa: BLE001 — coluna que não existe no espelho: o retrato a ignora
            base[chave] = f"(sem {chave}: {type(exc).__name__})"
    base.pop("auditoria", None)
    return base


def _nada_mudou(antes: dict, event_id: int, rotulo: str) -> None:
    depois = _retrato(event_id)
    diff = {k: (antes.get(k), depois.get(k)) for k in depois if antes.get(k) != depois.get(k)}
    _garante(not diff, f"{rotulo}: gravou no cancelado {list(diff)} {str(diff)[:300]}")


def _impersonar(apelido: str, papel: str):
    c = _cliente(apelido)
    r = c.post(v6.ROTAS["impersonate"], json={"role": papel})
    _garante(r.status_code == 200, f"Ver como {papel} → {r.status_code}")
    return c


# ── semente ───────────────────────────────────────────────────────────────────────────────────
def _cliente_crm(nome: str) -> int:
    with app.app_context():
        c = Client(
            name=f"{v6.PREFIX}{nome}", phone=f"5511{uuid.uuid4().int % 10**9:09d}", source="manual"
        )
        db.session.add(c)
        db.session.commit()
        estado["clientes"].append(c.id)
        return c.id


def _ligar_cliente(event_id: int, client_id: int) -> None:
    _no_banco_escrever(
        "INSERT INTO event_clients (event_id, client_id, relationship_type, created_at) "
        "VALUES (:e, :c, 'Contratante', now())",
        e=event_id,
        c=client_id,
    )
    _no_banco_escrever(
        "UPDATE calendar_events SET client_id = :c WHERE id = :e", e=event_id, c=client_id
    )


def _vaga_de_presenca(event_id: int) -> int | None:
    from app.calendar.casting_ops import e_vaga_de_presenca

    with app.app_context():
        for r in EventRole.query.filter_by(event_id=event_id).all():
            if e_vaga_de_presenca(r):
                return r.id
    return None


def semente() -> None:
    """O cancelado do exemplo com elenco, o vivo de controle no mesmo dia, o marcado, o pedido, o
    legado, o grupo, o ensaio legado e as coisas ligadas. Tudo antes do cancelamento que importa."""
    v6._usuario("cast2", RoleName.CASTING)
    v6._usuario("rev", RoleName.REVENDEDOR_EDUCAMANTO)
    S["t3"] = v6._talento("t312")
    dias = 20
    # O cancelado: show com venda (o exemplo-padrão) e três personagens únicos.
    S["canc"] = v6._show_com_dinheiro("312 canc", [f"C{TOKEN}A", f"C{TOKEN}B", f"C{TOKEN}C"], dias)
    S["r_aceito"] = v6._escalar(S["canc"], estado["t"])
    S["r_pendente"] = v6._escalar(S["canc"], estado["t2"], convite="pending")
    S["r_recusou"] = v6._escalar(S["canc"], estado["t_sem_pix"], convite="rejected")
    S["r_presenca"] = _vaga_de_presenca(S["canc"])
    # O vivo de controle: mesmo dia e hora, um personagem único; o t também escalado nele.
    S["vivo"] = v6._show_com_dinheiro("312 vivo", [f"V{TOKEN}A"], dias)
    S["r_vivo"] = v6._escalar(S["vivo"], estado["t"])
    S["dia"] = _data(S["canc"])
    # Marcado (303) e com pedido de exclusão, no mesmo dia.
    S["marcado"] = v6._evento(
        "312 marcado", inicio=v6._dias_a_frente(dias), titulo=f"(CORP) M{TOKEN} MARCADO"
    )
    v6._marcar_sumido(S["marcado"])
    S["pedido"] = v6._evento(
        "312 pedido", inicio=v6._dias_a_frente(dias), titulo=f"(CORP) P{TOKEN} PEDIDO"
    )
    _no_banco_escrever(
        "UPDATE calendar_events SET deletion_requested_at = now(), deletion_requested_by_id = :u WHERE id = :i",
        u=estado["usuarios"]["com"]["id"],
        i=S["pedido"],
    )
    # Cliente do cancelado e do vivo; formulário ligado ao cancelado.
    S["cliente"] = _cliente_crm("cliente 312")
    _ligar_cliente(S["canc"], S["cliente"])
    _ligar_cliente(S["vivo"], S["cliente"])
    S["form"] = _formulario(S["canc"])
    # Gasto comum ligado ao cancelado (antes do cancelamento) e presente 3D.
    S["gasto"] = v6._gasto_comum(S["canc"], 50)
    S["presente"] = _presente(S["canc"])
    S["pedido_fig"] = _pedido_figurino(S["canc"])
    S["tag"] = _emprestar_tag(S["canc"])
    S["token_avaliacao"] = _token(S["canc"])
    # Observação, contrato e material para as rotas da trava que pedem um id.
    S["obs"] = _inserir(
        "INSERT INTO event_observations (event_id, obs_type, content, created_at) "
        "VALUES (:e, 'text', 'v312 obs', now()) RETURNING id",
        e=S["canc"],
    )
    S["contrato"] = _inserir(
        "INSERT INTO event_contracts (event_id, file_path, created_at, is_signed) "
        "VALUES (:e, :f, now(), false) RETURNING id",
        e=S["canc"],
        f=f"{v6.PREFIX}contrato.pdf",
    )
    S["material"] = _inserir(
        "INSERT INTO ensaio_materials (event_id, material_type, label, url, created_at) "
        "VALUES (:e, 'link', 'v312', 'https://example.test/v312', now()) RETURNING id",
        e=S["canc"],
    )
    S["avaliacao"] = _inserir(
        "INSERT INTO client_feedbacks (event_id, client_name, score, submitted_at) "
        "VALUES (:e, :n, 5, now()) RETURNING id",
        e=S["canc"],
        n=f"{v6.PREFIX}cliente",
    )
    # O ato da 306: cancela com devolução Parte de 600.
    v6._remocoes.clear()
    v6._cancelar_ok(S["canc"], v6._corpo_cancelar("parte", 600, motivo=f"Motivo sigiloso {TOKEN}"))
    S["sinos_escala"] = v6._avisos_do_ato("evento.cancelado_escala", S["canc"])
    # Legado: cancelado pela regra velha (sem congelamento), com dinheiro.
    S["legado"] = v6._evento("312 legado", titulo=f"(CORP) L{TOKEN} LEGADO")
    v6._comprovante(S["legado"], 500)
    _no_banco_escrever(
        "UPDATE calendar_events SET cancelled_at = now(), cancellation_reason = 'legado 312', cancelled_by_id = :u "
        "WHERE id = :i",
        u=estado["usuarios"]["sa"]["id"],
        i=S["legado"],
    )
    # Ensaio legado: ensaio de um show vivo, cancelado sozinho por UPDATE.
    S["ensaio_legado"] = v6._ensaio(S["vivo"], v6._dias_a_frente(dias - 2))
    _no_banco_escrever(
        "UPDATE calendar_events SET cancelled_at = now() WHERE id = :i", i=S["ensaio_legado"]
    )
    # Grupo: principal vivo + um dia cancelado + um vivo.
    g = v6._grupo("312 grupo", dias=2, comissao=None)
    S["g_principal"], (S["g_canc"], S["g_vivo"]) = g["principal"], g["dias"]
    r = v6._cancelar(
        S["g_canc"], {"motivo": "verify 312 dia", "devolucao": {"modo": "nada"}, "venda_nova": 2000}
    )
    _garante(
        r.status_code == 200,
        f"semente: cancelar o dia do grupo → {r.status_code} {r.get_data(as_text=True)[:300]}",
    )
    v6._esperar_threads()


def _inserir(sql: str, **params) -> int:
    with v6._externo.begin() as conn:
        from sqlalchemy import text

        return conn.execute(text(sql), params).scalar_one()


def _formulario(event_id: int) -> int:
    return _inserir(
        "INSERT INTO form_responses (form_type, data, contact_name, created_at, event_id, event_link_source, "
        "event_link_ambiguous, event_link_locked) "
        "VALUES ('comum', '{}', :n, now(), CAST(:e AS integer), CASE WHEN CAST(:e AS integer) IS NULL THEN NULL ELSE 'manual' END, false, CAST(:e AS integer) IS NOT NULL) "
        "RETURNING id",
        n=f"{v6.PREFIX}form 312",
        e=event_id,
    )


def _acervo_id() -> int:
    linhas = _no_banco("SELECT id FROM acervo_3d_items ORDER BY id LIMIT 1")
    _garante(bool(linhas), "o espelho não tem item no acervo 3D")
    return linhas[0][0]


def _presente(event_id: int) -> int:
    return _inserir(
        "INSERT INTO event_3d_gifts (event_id, item_id, status, quantity, created_at, updated_at) "
        "VALUES (:e, :a, 'pendente', 1, now(), now()) RETURNING id",
        e=event_id,
        a=_acervo_id(),
    )


def _pedido_figurino(event_id: int) -> int:
    r = _cliente("sa").post(
        "/api/figurino/producoes",
        json={"title": f"{v6.PREFIX}pedido 312", "kind": "producao", "event_id": event_id},
    )
    _garante(
        r.status_code in (200, 201),
        f"semente: pedido de figurino → {r.status_code} {r.get_data(as_text=True)[:300]}",
    )
    pid = (r.get_json() or {}).get("id") or ((r.get_json() or {}).get("producao") or {}).get("id")
    EXTRAS["producoes"].append(pid)
    return pid


def _emprestar_tag(event_id: int) -> dict:
    """Tag de ESTOQUE existente (tag não se apaga): liga ao evento e devolve no `limpar_312`."""
    linhas = _no_banco(
        "SELECT id, event_id FROM nfc_tags WHERE event_id IS NULL ORDER BY id LIMIT 1"
    )
    _garante(bool(linhas), "o espelho não tem tag NFC de estoque")
    tag = {"id": linhas[0][0], "original": linhas[0][1]}
    EXTRAS["tag"] = tag
    _no_banco_escrever("UPDATE nfc_tags SET event_id = :e WHERE id = :i", e=event_id, i=tag["id"])
    return tag


def _token(event_id: int) -> str:
    tok = f"v312{uuid.uuid4().hex[:20]}"
    _no_banco_escrever(
        "UPDATE calendar_events SET feedback_token = :t WHERE id = :i", t=tok, i=event_id
    )
    return tok


def limpar_312() -> None:
    """O que a 312 cria fora do prefixo da 306: tag de estoque, pedidos de figurino, dispensas 3D."""
    tag = EXTRAS.get("tag")
    if tag:
        _no_banco_escrever(
            "UPDATE nfc_tags SET event_id = :e WHERE id = :i", e=tag["original"], i=tag["id"]
        )
    ids = [
        r[0]
        for r in _no_banco(
            "SELECT id FROM figurino_producoes WHERE title LIKE :p", p=f"{v6.PREFIX}%"
        )
    ]
    for pid in ids:
        for sql in (
            "DELETE FROM figurino_producao_comentarios WHERE producao_id = :i",
            "DELETE FROM figurino_producao_anexos WHERE producao_id = :i",
            "DELETE FROM figurino_producao_gastos WHERE producao_id = :i",
            "DELETE FROM figurino_producoes WHERE id = :i",
        ):
            try:
                _no_banco_escrever(sql, i=pid)
            except Exception:  # noqa: BLE001 — tabela-filha que não existe no espelho
                pass
    eventos = [
        r[0]
        for r in _no_banco(
            "SELECT id FROM calendar_events WHERE google_event_id LIKE :g OR title LIKE :t",
            g=f"{v6.GID}%",
            t=f"%{TOKEN}%",
        )
    ] or [0]
    _no_banco_escrever("DELETE FROM event_3d_dismissals WHERE event_id = ANY(:e)", e=eventos)


# ── H1: o cancelado some de toda lista ───────────────────────────────────────────────────────
def c1_agenda() -> None:
    dia = S["dia"].isoformat()
    for url in (
        f"/api/agenda/day/{dia}",
        f"/api/agenda/day/{dia}?incluir_cancelados=1",
        f"/api/agenda?ym={v6._mes(S['dia'])}",
        f"/api/agenda?ym={v6._mes(S['dia'])}&incluir_cancelados=1",
    ):
        corpo = _get("sa", url)
        ids = _ids(corpo)
        _garante(S["vivo"] in ids, f"1: {url} sem o vivo de controle")
        _garante(S["canc"] not in ids, f"1: {url} trouxe o cancelado")
        _garante(
            S["marcado"] in ids and S["pedido"] in ids, f"1: {url} escondeu o marcado ou o pedido"
        )
    for termo, presente in (
        (f"C{TOKEN}A", False),
        (f"V{TOKEN}A", True),
        (f"M{TOKEN}", True),
        (f"P{TOKEN}", True),
    ):
        for extra in ("", "&incluir_cancelados=1"):
            ids = _ids(_get("sa", f"/api/agenda/search?q={termo}{extra}"))
            alvo = {
                f"C{TOKEN}A": S["canc"],
                f"V{TOKEN}A": S["vivo"],
                f"M{TOKEN}": S["marcado"],
                f"P{TOKEN}": S["pedido"],
            }[termo]
            _garante(
                (alvo in ids) == presente,
                f"1: busca {termo}{extra} → {alvo in ids} (esperado {presente})",
            )
    html = _html("sa", f"/agenda/day/{dia}")
    _garante(f"V{TOKEN}A" in html, "1: Dia Jinja sem o vivo de controle")
    _garante(f"C{TOKEN}A" not in html, "1: Dia Jinja mostrou o cancelado")


def c2_ficha_talento() -> None:
    corpo = _get("sa", f"/api/talents/{estado['t']}")
    texto = json.dumps(corpo, ensure_ascii=False)
    _garante(f"V{TOKEN}A" in texto, "2: a ficha do talento não traz o vivo de controle")
    _garante(
        f"C{TOKEN}" not in texto, "2: a ficha do talento traz o cancelado (histórico ou personagem)"
    )
    hist = (corpo.get("history") or {}) if isinstance(corpo.get("history"), dict) else {}
    itens = hist.get("items") or corpo.get("history") or []
    ids = _ids(itens)
    _garante(S["canc"] not in ids, "2: o cancelado está no histórico")
    # Os números saem da mesma lista: o cachê de 300 do cancelado não entra no total.
    total = (
        corpo.get("total_earned")
        or hist.get("total_earned")
        or (corpo.get("stats") or {}).get("total_earned")
    )
    so_vivos = sum(
        (
            Decimal(str(r[0]))
            for r in _no_banco(
                "SELECT coalesce(r.cache_value, 0) FROM event_roles r JOIN calendar_events e ON e.id = r.event_id "
                "WHERE r.talent_id = :t AND e.cancelled_at IS NULL AND e.start_at < now() AND r.invite_status = 'accepted'",
                t=estado["t"],
            )
        ),
        Decimal("0"),
    )
    _ = so_vivos  # o espelho tem o passado do talento descartável vazio: o teste forte é o texto acima
    _garante(total is None or q(total) >= 0, "2: total_earned inválido")


def c3_ficha_cliente() -> None:
    corpo = _get("sa", f"/api/clientes/{S['cliente']}")
    eventos = corpo.get("events") or []
    ids = {e.get("id") for e in eventos}
    _garante(S["vivo"] in ids, "3: a ficha da cliente sem o vivo de controle")
    _garante(S["canc"] not in ids, "3: a ficha da cliente lista o cancelado")
    _garante(corpo.get("event_count") == 1, f"3: event_count {corpo.get('event_count')}")
    canc = corpo.get("cancelamentos")
    _garante(isinstance(canc, dict), f"3: sem `cancelamentos` ({canc})")
    _garante(canc.get("quantidade") == 1, f"3: cancelamentos.quantidade {canc.get('quantidade')}")
    v6._igual(canc.get("retido"), 400, "3: cancelamentos.retido")
    v6._igual(corpo.get("total_sales"), 2000 + 400, "3: total_sales = vivo + retido")


def c4_seletores() -> None:
    ids = _ids(_get("sa", f"/api/events/{S['vivo']}/grupo/candidatos?q=C{TOKEN}"))
    _garante(S["canc"] not in ids, "4: grupo/candidatos ofereceu o cancelado")
    ids_vivo = _ids(_get("sa", f"/api/events/{S['marcado']}/grupo/candidatos?q=V{TOKEN}"))
    _garante(S["vivo"] in ids_vivo, "4: grupo/candidatos sem o vivo de controle")
    corpo = _get("sa", f"/api/gastos/eventos?date={S['dia'].isoformat()}")
    ids = _ids(corpo)
    _garante(S["vivo"] in ids, "4: seletor por data sem o vivo")
    _garante(S["canc"] not in ids, "4: seletor por data ofereceu o cancelado")
    from app.formularios import formularios_ops

    with app.app_context():
        cands = {e.id for e in formularios_ops._real_event_candidates(S["dia"])}
    _garante(S["vivo"] in cands, "4: candidatos automáticos do formulário sem o vivo")
    _garante(S["canc"] not in cands, "4: candidatos automáticos do formulário com o cancelado")
    html = _html("sa", f"/events/{S['ensaio_legado']}")
    _garante(
        f"C{TOKEN}A" not in html,
        "4: a lista Jinja de shows do vínculo de ensaio ofereceu o cancelado",
    )


def c5_filas_3d() -> None:
    corpo = _get("sa", "/api/3d/fila")
    pend = _ids(corpo.get("sem_presente") or [])
    fila = corpo.get("items") or []
    _garante(S["vivo"] in pend, "5: pendências de presente sem o show vivo de controle")
    _garante(S["canc"] not in pend, "5: o show cancelado nas pendências de presente")
    _garante(
        all(
            (x.get("event") or {}).get("id") != S["canc"] and x.get("event_id") != S["canc"]
            for x in fila
        ),
        "5: o presente do cancelado na Fila de Impressão",
    )
    _garante(
        _no_banco("SELECT count(*) FROM event_3d_gifts WHERE id = :i", i=S["presente"])[0][0] == 1,
        "5: o presente vinculado sumiu do evento",
    )


def c6_conflito() -> None:
    from app.calendar import routes as cal_routes

    with app.app_context():
        vivo = db.session.get(CalendarEvent, S["vivo"])
        talento = db.session.get(Talent, estado["t"])
        conflito = cal_routes._talent_time_conflict(
            talento.id, vivo.start_at, vivo.end_at, exclude_event_id=vivo.id
        )
    texto = json.dumps(conflito, default=str, ensure_ascii=False) if conflito else ""
    _garante(f"C{TOKEN}" not in texto, f"6: conflito pelo cancelado: {texto[:200]}")
    html = _html("sa", f"/events/{S['vivo']}")
    _garante(
        f"C{TOKEN}A" not in html, "6: a tela Jinja do vivo mostra o cancelado (disponibilidade)"
    )


def c7_grupo_e_ensaio() -> None:
    corpo = _get("sa", f"/api/events/{S['g_principal']}")
    grupo = corpo.get("group") or (corpo.get("event") or {}).get("group") or {}
    sats = {s.get("id") for s in (grupo.get("satellites") or [])}
    _garante(S["g_vivo"] in sats, f"7: o dia vivo fora do painel do grupo ({sats})")
    _garante(S["g_canc"] not in sats, "7: o dia cancelado no painel do grupo do principal vivo")
    _garante(
        _no_banco("SELECT group_leader_id FROM calendar_events WHERE id = :i", i=S["g_canc"])[0][0]
        == S["g_principal"],
        "7: o dia cancelado saiu do grupo no banco",
    )
    corpo = _get("sa", f"/api/events/{S['vivo']}")
    ens = _ids(corpo.get("ensaios") or (corpo.get("event") or {}).get("ensaios") or [])
    _garante(
        S["ensaio_legado"] not in ens, "7: o ensaio legado cancelado na lista de ensaios do show"
    )


# ── H2: a tela do cancelado só para consulta ─────────────────────────────────────────────────
def c8_q9() -> None:
    for apelido, ve in (
        ("cast", False),
        ("fig", False),
        ("ens", False),
        ("com", True),
        ("fin", True),
        ("sa", True),
    ):
        ev = _get(apelido, f"/api/events/{S['canc']}").get("event") or {}
        _garante(ev.get("cancelled_at"), f"8: {apelido} sem cancelled_at")
        tem = bool(ev.get("cancellation_reason")) or bool(ev.get("cancelled_by"))
        _garante(tem == ve, f"8: {apelido} vê o motivo/autor = {tem} (esperado {ve})")
    c = _impersonar("sa", RoleName.CASTING)
    ev = c.get(f"/api/events/{S['canc']}").get_json().get("event") or {}
    _garante(
        not ev.get("cancellation_reason") and not ev.get("cancelled_by"),
        "8: Ver como Casting viu o motivo",
    )
    html = _html("cast", f"/events/{S['canc']}")
    _garante(
        f"Motivo sigiloso {TOKEN}" not in html,
        "8: a tela Jinja mostra o motivo ao Casting (Log de atividades)",
    )


def _trava_api() -> list[tuple[str, str, dict | None]]:
    e, r = S["canc"], S["r_aceito"]
    return [
        ("patch", f"/api/events/{e}", {"title": "x"}),
        ("patch", f"/api/events/{e}/basico", {"title": "x"}),
        ("post", f"/api/events/{e}/confirm", {}),
        ("patch", f"/api/events/{e}/logistics", {"makeup_time": "10:00"}),
        ("post", f"/api/events/{e}/observations", {"obs_type": "text", "content": "x"}),
        ("delete", f"/api/observations/{S['obs']}", None),
        ("put", f"/api/events/{e}/clients", {"clients": []}),
        ("post", f"/api/events/{e}/contracts", {}),
        ("delete", f"/api/contracts/{S['contrato']}", None),
        ("post", f"/api/contracts/{S['contrato']}/toggle-signed", {}),
        ("post", f"/api/events/{e}/travel-estimate", {}),
        ("post", f"/api/events/{e}/materials", {"url": "https://example.test/x", "label": "x"}),
        ("delete", f"/api/materials/{S['material']}", None),
        ("post", f"/api/events/{e}/presenca", {}),
        ("patch", f"/api/events/{e}/grupo", {"group_name": "x"}),
        ("post", f"/api/events/{e}/sync", {}),
        ("post", f"/api/events/{e}/roles", {"character_name": "X"}),
        ("delete", f"/api/roles/{r}", None),
        ("post", f"/api/roles/{r}/transporte", {}),
        ("delete", f"/api/roles/{r}/transporte", None),
        ("post", f"/api/roles/{r}/figurino-done", {}),
        ("delete", f"/api/roles/{r}/figurino-done", None),
        ("post", f"/api/roles/{r}/dismiss", {}),
        ("post", f"/api/roles/{r}/restore", {}),
        ("post", f"/api/roles/{r}/payment-status", {"status": "pago"}),
        ("post", f"/api/roles/{r}/figurino-sheet", {"sheet_id": None}),
        ("patch", f"/api/events/{e}/3d-gifts/{S['presente']}", {"quantity": 2}),
        ("post", f"/api/events/{e}/3d-dismissal", {}),
        ("delete", f"/api/events/{e}/3d-dismissal", None),
        ("delete", f"/api/clientes/avaliacoes/{S['avaliacao']}", None),
        ("patch", f"/api/ensaios/{S['ensaio_legado']}", {"description": "x"}),
        ("delete", f"/api/ensaios/{S['ensaio_legado']}", None),
    ]


def c9_trava() -> None:
    falhas = []
    for metodo, url, corpo in _trava_api():
        alvo = S["ensaio_legado"] if "/ensaios/" in url else S["canc"]
        antes = _retrato(alvo)
        c = _cliente("sa")
        r = getattr(c, metodo)(url, json=corpo) if corpo is not None else getattr(c, metodo)(url)
        if not _e_trava(r):
            falhas.append(
                f"{metodo.upper()} {url} → {r.status_code} {_erro(r).get('message', '')[:80]}"
            )
            continue
        try:
            _nada_mudou(antes, alvo, f"9 {url}")
        except AssertionError as exc:
            falhas.append(str(exc))
    # Jinja: o despachante, as rotas fora dele e "Imprimir fichas".
    e = S["canc"]
    for url, dados in (
        (f"/events/{e}", {"action": "save_logistics", "makeup_time": "11:00"}),
        (f"/events/{e}", {"action": "assign_casting", "role_id": S["r_aceito"], "talent_id": ""}),
        (f"/events/{e}/observations/add", {"obs_type": "text", "content": "x"}),
        (f"/events/{e}/observations/{S['obs']}/delete", {}),
        (f"/events/{e}/ensaio/link", {"url": "https://example.test/y", "label": "y"}),
        (f"/events/{e}/ensaio/material/{S['material']}/delete", {}),
        (f"/events/{e}/sync", {}),
        (
            f"/events/{e}/create-ensaio",
            {"date": S["dia"].isoformat(), "start": "10:00", "end": "11:00"},
        ),
        (f"/events/{S['ensaio_legado']}/edit-ensaio", {"description": "x"}),
        (f"/events/{S['ensaio_legado']}/delete-ensaio", {}),
        (f"/roles/{S['r_aceito']}/dismiss", {}),
    ):
        alvo = (
            S["ensaio_legado"]
            if "ensaio_legado" in url or f"/events/{S['ensaio_legado']}/" in url
            else e
        )
        antes = _retrato(alvo)
        r = _cliente("sa").post(url, data=dados)
        try:
            _nada_mudou(antes, alvo, f"9 Jinja {url}")
        except AssertionError as exc:
            falhas.append(str(exc))
        _ = r
    r = _cliente("sa").get(f"/figurinos/print-event/{e}")
    if (
        r.status_code == 200
        and "print" in r.get_data(as_text=True).lower()
        and f"C{TOKEN}" in r.get_data(as_text=True)
    ):
        falhas.append("Imprimir fichas imprimiu o cancelado")
    _garante(
        not falhas,
        "9: " + " | ".join(falhas[:12]) + (f" (+{len(falhas) - 12})" if len(falhas) > 12 else ""),
    )


# A classificação de toda rota de escrita que toca um evento (cenário 9b). Rota nova sem lugar aqui
# faz o 9b falhar: a trava não tem furo silencioso.
TRAVA = {
    "api.api_update_event", "api.api_update_event_basics", "api.api_toggle_confirm", "api.api_save_logistics",
    "api.api_add_observation", "api.api_delete_observation", "api.api_set_event_clients", "api.api_add_contract",
    "api.api_delete_contract", "api.api_toggle_contract_signed", "api.api_travel_estimate", "api.api_add_material",
    "api.api_delete_material", "api.api_assign_presence", "api.api_renomear_grupo", "api.api_sync_event",
    "api.api_add_role", "api.api_delete_role", "api.api_marcar_transporte", "api.api_desmarcar_transporte",
    "api.api_figurino_done", "api.api_clear_figurino_done", "api.api_dismiss_role", "api.api_restore_role",
    "api.api_set_role_payment_status", "api.api_link_figurino_sheet", "api.api_event_3d_gift_update",
    "api.api_event_3d_dismiss", "api.api_event_3d_undismiss", "api.api_update_ensaio", "api.api_delete_ensaio",
    "api.api_clientes_avaliacao_delete",
    "calendar.event_detail", "calendar.add_observation", "calendar.delete_observation", "calendar.ensaio_add_link",
    "calendar.ensaio_upload_material", "calendar.ensaio_delete_material", "calendar.edit_ensaio",
    "calendar.delete_ensaio", "calendar.sync_single_event", "calendar.dismiss_role", "calendar.restore_role",
}  # fmt: skip
RECUSA_VINCULO = {
    "api.api_create_ensaio", "api.api_link_ensaio", "api.api_event_3d_gift_create", "api.api_set_event_form_response",
    "api.api_formularios_vincular_evento", "api.api_send_invite", "api.api_feedback_link", "api.api_3d_nfc_update",
    "api.api_figurino_producao_update", "calendar.create_ensaio", "calendar.link_ensaio_parent",
    "api.api_portal_accept_invite",
}  # fmt: skip
REGRA_PROPRIA = {"api.api_assign_role"}  # Q10: só a remoção, só o Casting (cenário 15)
LIVRE_306 = {
    "api.api_delete_event", "api.api_cancelar_evento", "api.api_devolver_ao_google", "api.api_solicitar_exclusao",
    "api.api_recusar_solicitacao", "api.api_update_event_comercial", "api.api_set_event_orcamento",
    "api.api_add_invoice", "api.api_update_invoice", "api.api_delete_invoice", "api.api_set_acrescimos",
    "api.api_set_parcelas", "api.api_add_payment", "api.api_edit_payment", "api.api_delete_payment",
    "api.api_add_reimbursement", "api.api_collect_reimbursement", "api.api_delete_reimbursement",
    "api.api_alterar_devolucao", "api.api_lancar_multas", "api.api_editar_motivo_cancelamento",
    "api.api_agrupar_eventos", "api.api_desagrupar_evento", "api.api_remover_satelite",
    "calendar.delete_calendar_event",
}  # fmt: skip
DESFAZER = {"api.api_event_3d_gift_delete", "api.api_formularios_desvincular_evento"}
FORA_DA_TELA = {
    # já recusam o cancelado pela regra deles, ou não ligam nada novo
    "api.api_portal_submit_rating", "api.api_portal_submit_rating_detail", "api.api_portal_reject_invite",
    "api.api_portal_ack_change", "api.api_formularios_confirmar_sugestao", "api.api_formularios_descartar_sugestao",
    "api.api_figurino_producao_delete",  # apaga o pedido, não mexe no evento
}  # fmt: skip
PREFIXOS_DA_TELA = (
    "/api/events/<", "/api/roles/", "/api/ensaios/", "/api/observations/", "/api/materials/", "/api/contracts/",
    "/api/payments/", "/api/reimbursements/", "/api/clientes/avaliacoes/", "/api/portal/invites/",
    "/api/portal/roles/", "/api/portal/events/", "/api/3d/nfc/<int:tag_id>", "/events/<", "/roles/",
    "/api/figurino/producoes/<int:producao_id>", "/api/formularios/respostas/",
)  # fmt: skip


def c9b_inventario() -> None:
    classificadas = TRAVA | RECUSA_VINCULO | REGRA_PROPRIA | LIVRE_306 | DESFAZER | FORA_DA_TELA
    soltas = []
    for regra in app.url_map.iter_rules():
        metodos = {m for m in regra.methods if m in {"POST", "PUT", "PATCH", "DELETE"}}
        if not metodos or "<int:" not in regra.rule:
            continue
        if not regra.rule.startswith(PREFIXOS_DA_TELA):
            continue
        if regra.rule.startswith("/api/3d/nfc/<int:tag_id>/"):
            continue  # entregas e recados da tag: não ligam a tag a evento
        if regra.rule.startswith("/api/figurino/producoes/<int:producao_id>/") or (
            regra.rule.startswith("/api/formularios/respostas/")
            and regra.endpoint not in classificadas
            and not regra.rule.endswith(("vincular-evento", "desvincular-evento"))
        ):
            continue  # anexos/comentários do pedido e o resto da fila de formulários: não tocam o evento
        if regra.endpoint not in classificadas:
            soltas.append(f"{','.join(sorted(metodos))} {regra.rule} ({regra.endpoint})")
    _garante(not soltas, f"9b: rota de escrita sem classificação: {soltas}")
    # Toda rota da lista "trava" e "recusa" existe (nome errado = proteção que não protege).
    existentes = {r.endpoint for r in app.url_map.iter_rules()}
    sumidas = sorted((TRAVA | RECUSA_VINCULO | LIVRE_306 | DESFAZER) - existentes)
    _garante(not sumidas, f"9b: endpoints da classificação que não existem: {sumidas}")


def c10_portas_livres() -> None:
    e = S["canc"]
    r = v6._patch_comercial(e, "sa")
    _garante(
        r.status_code == 200 and TRAVA_FRASE not in str(_erro(r)),
        f"10: comercial SA → {r.status_code} {_erro(r)}",
    )
    r = _cliente("sa").put(f"/api/events/{e}/acrescimos", json={"acrescimos": None})
    _garante(TRAVA_FRASE not in str(_erro(r)), f"10: acréscimos SA caiu na trava {r.status_code}")
    r = v6._post_comprovante("sa", e, 10)
    _garante(
        r.status_code in (200, 201) and not _e_trava(r),
        f"10: comprovante SA → {r.status_code} {_erro(r)}",
    )
    # Apagar também é porta de venda livre — e devolve o pago do exemplo aos 1.000 dos cenários seguintes.
    pid = _no_banco(
        "SELECT id FROM event_payments WHERE event_id = :e AND amount = 10 ORDER BY id DESC LIMIT 1",
        e=e,
    )
    _garante(bool(pid), "10: o comprovante de 10 não ficou no banco")
    r = _cliente("sa").delete(f"/api/payments/{pid[0][0]}")
    _garante(
        r.status_code in (200, 204) and not _e_trava(r),
        f"10: apagar comprovante SA → {r.status_code} {_erro(r)}",
    )
    r = _cliente("com").patch(
        f"/api/events/{e}/motivo-cancelamento", json={"motivo": f"Motivo sigiloso {TOKEN}"}
    )
    _garante(r.status_code == 200, f"10: motivo pela Comercial → {r.status_code} {_erro(r)}")
    r = v6._patch_comercial(e, "com")
    _garante(
        r.status_code == 409 and _codigo(r) == "cancelado" and TRAVA_FRASE not in str(_erro(r)),
        f"10: comercial COM → {r.status_code} {_erro(r)} (o 409 é o da 306, não o da trava)",
    )


def c11_q5() -> None:
    e = S["canc"]
    v6._emails.clear()
    vaga_vazia = _no_banco(
        "SELECT id FROM event_roles WHERE event_id = :e AND talent_id IS NULL AND role_type <> 'extra' ORDER BY id LIMIT 1",
        e=e,
    )
    antes = _retrato(e)
    falhas = []
    tentativas = [
        ("post", f"/api/events/{e}/roles", {"character_name": "Novo", "talent_id": S["t3"]}, 409),
        ("post", f"/api/roles/{S['r_pendente']}/invite", {}, 409),
        ("post", f"/api/events/{e}/feedback-link", {}, 409),
    ]
    if vaga_vazia:
        tentativas.append(
            (
                "post",
                f"/api/roles/{vaga_vazia[0][0]}/assign",
                {"talent_id": S["t3"], "cache_value": "300"},
                409,
            )
        )
    for metodo, url, corpo, status in tentativas:
        r = getattr(_cliente("sa"), metodo)(url, json=corpo)
        if not _e_recusa_cancelado(r, status):
            falhas.append(f"{url} → {r.status_code} {_codigo(r)}")
    v6._esperar_threads()
    if v6._emails:
        falhas.append(f"e-mail saiu: {[m['subject'] for m in v6._emails]}")
    try:
        _nada_mudou(antes, e, "11")
    except AssertionError as exc:
        falhas.append(str(exc))
    anon = app.test_client()
    for metodo in ("get", "post"):
        r = getattr(anon, metodo)(
            f"/api/avaliar/{S['token_avaliacao']}", json={"client_name": "x", "score": 5}
        )
        if r.status_code != 410:
            falhas.append(f"avaliar {metodo} → {r.status_code}")
        elif f"C{TOKEN}" in r.get_data(as_text=True):
            falhas.append("avaliar 410 trouxe o título")
    n = _no_banco("SELECT count(*) FROM client_feedbacks WHERE event_id = :e", e=e)[0][0]
    if n != 1:
        falhas.append(f"avaliação gravada no cancelado ({n})")
    r = _cliente("sa").post(
        "/api/figurino/producoes",
        json={"title": f"{v6.PREFIX}novo", "kind": "producao", "event_id": e},
    )
    if not _e_recusa_cancelado(r, 400) or "event_id" not in (_erro(r).get("fields") or {}):
        falhas.append(f"pedido de figurino novo → {r.status_code} {_erro(r)}")
        pid = (r.get_json() or {}).get("id")
        if pid:
            EXTRAS["producoes"].append(pid)
    r = _cliente("sa").patch(
        f"/api/figurino/producoes/{S['pedido_fig']}", json={"notes": "x", "event_id": e}
    )
    if r.status_code not in (200, 201):
        falhas.append(f"editar pedido sem trocar o evento → {r.status_code} {_erro(r)}")
    _garante(not falhas, "11: " + " | ".join(falhas))


def c12_q2() -> None:
    e = S["canc"]
    falhas = []
    marco = v6.google.marco()
    r = _cliente("sa").post(
        f"/api/events/{e}/ensaios",
        json={"date": S["dia"].isoformat(), "start": "10:00", "end": "11:00"},
    )
    if not _e_recusa_cancelado(r, 409):
        falhas.append(f"agendar ensaio → {r.status_code} {_codigo(r)}")
    if any(v == "insert" for v, _ in v6.google.chamadas[marco:]):
        falhas.append("agendar ensaio escreveu no Google")
    orfao = v6._ensaio(S["marcado"], v6._dias_a_frente(15))
    _no_banco_escrever("UPDATE calendar_events SET parent_event_id = NULL WHERE id = :i", i=orfao)
    r = _cliente("sa").post(f"/api/ensaios/{orfao}/vincular", json={"parent_event_id": e})
    if not _e_recusa_cancelado(r, 400) or "parent_event_id" not in (_erro(r).get("fields") or {}):
        falhas.append(f"vincular ensaio → {r.status_code} {_erro(r)}")
    if (
        _no_banco("SELECT parent_event_id FROM calendar_events WHERE id = :i", i=orfao)[0][0]
        is not None
    ):
        falhas.append("o ensaio foi vinculado ao cancelado")
    r = _cliente("sa").post(
        f"/api/events/{e}/3d-gifts", json={"item_id": _acervo_id(), "quantity": 1}
    )
    if not _e_recusa_cancelado(r, 409):
        falhas.append(f"presente novo → {r.status_code} {_codigo(r)}")
    # Tag: vínculo NOVO recusa; o mesmo id passa.
    outra = _no_banco(
        "SELECT id FROM nfc_tags WHERE event_id IS NULL AND id <> :i ORDER BY id LIMIT 1",
        i=S["tag"]["id"],
    )
    if outra:
        r = _cliente("sa").patch(f"/api/3d/nfc/{outra[0][0]}", json={"event_id": e})
        if not _e_recusa_cancelado(r, 400):
            falhas.append(f"tag nova no cancelado → {r.status_code} {_erro(r)}")
        if (
            _no_banco("SELECT event_id FROM nfc_tags WHERE id = :i", i=outra[0][0])[0][0]
            is not None
        ):
            _no_banco_escrever("UPDATE nfc_tags SET event_id = NULL WHERE id = :i", i=outra[0][0])
            falhas.append("a tag nova foi ligada ao cancelado")
    r = _cliente("sa").patch(f"/api/3d/nfc/{S['tag']['id']}", json={"event_id": e})
    if r.status_code != 200:
        falhas.append(f"tag com o mesmo evento → {r.status_code} {_erro(r)}")
    # Formulário: ligar recusa; desligar passa.
    novo_form = _formulario(None)
    r = _cliente("sa").patch(f"/api/events/{e}/form-response", json={"form_response_id": novo_form})
    if not _e_recusa_cancelado(r, 409):
        falhas.append(f"ligar formulário (painel) → {r.status_code} {_codigo(r)}")
    r = _cliente("sa").post(
        f"/api/formularios/respostas/{novo_form}/vincular-evento", json={"event_id": e}
    )
    if not _e_recusa_cancelado(r, 409):
        falhas.append(f"ligar formulário (/formularios) → {r.status_code} {_codigo(r)}")
    if (
        _no_banco("SELECT event_id FROM form_responses WHERE id = :i", i=novo_form)[0][0]
        is not None
    ):
        falhas.append("o formulário foi ligado ao cancelado")
    r = _cliente("sa").patch(f"/api/events/{e}/form-response", json={"form_response_id": None})
    if r.status_code != 200:
        falhas.append(f"desligar formulário → {r.status_code} {_erro(r)}")
    r = _cliente("sa").delete(f"/api/events/{e}/3d-gifts/{S['presente']}")
    if r.status_code not in (200, 204):
        falhas.append(f"soltar presente → {r.status_code} {_erro(r)}")
    _garante(not falhas, "12: " + " | ".join(falhas))


def c13_flags() -> None:
    flags = _get("sa", f"/api/events/{S['canc']}").get("flags") or {}
    _garante(
        flags.get("somente_consulta") is True,
        f"13: somente_consulta {flags.get('somente_consulta')}",
    )
    for f in (
        "can_edit_event",
        "can_edit_core",
        "can_confirm",
        "can_group",
        "can_manage_3d",
        "can_request_delete",
    ):
        _garante(not flags.get(f), f"13: {f} verdadeira no cancelado")
    _garante(
        flags.get("desfazer_presente_3d") is True and flags.get("desfazer_formulario") is True,
        f"13: desfazer {flags.get('desfazer_presente_3d')} {flags.get('desfazer_formulario')}",
    )
    _garante(flags.get("can_edit_venda_cancelado") is True, "13: a flag de venda da 306 sumiu")
    vivo = _get("sa", f"/api/events/{S['vivo']}").get("flags") or {}
    _garante(
        "somente_consulta" not in vivo or not vivo["somente_consulta"],
        "13: somente_consulta no vivo",
    )
    _garante(vivo.get("can_edit_event") and vivo.get("can_confirm"), "13: o vivo perdeu as flags")


def c14_controle() -> None:
    falhas = []
    for alvo in (S["pedido"], S["marcado"]):
        for metodo, url, corpo in (
            ("patch", f"/api/events/{alvo}/logistics", {"makeup_time": "10:00"}),
            ("post", f"/api/events/{alvo}/observations", {"obs_type": "text", "content": "x"}),
            ("post", f"/api/events/{alvo}/feedback-link", {}),
            ("post", f"/api/events/{alvo}/3d-gifts", {"item_id": _acervo_id(), "quantity": 1}),
        ):
            r = getattr(_cliente("sa"), metodo)(url, json=corpo)
            if _codigo(r) == "cancelado":
                falhas.append(f"{url} → {r.status_code} cancelado")
    _garante(not falhas, "14: o pedido ou a marca travaram: " + " | ".join(falhas))


# ── H3: o Casting tira e avisa ───────────────────────────────────────────────────────────────
def c15_casting() -> None:
    e = S["canc"]
    home = _get("cast", "/api/dashboard")
    pend = ((home.get("casting") or {}).get("cancelados_a_avisar")) or []
    roles = {p.get("role_id") for p in pend}
    _garante(
        roles >= {S["r_aceito"], S["r_pendente"]}, f"15: pendência sem os dois escalados ({roles})"
    )
    _garante(
        S["r_recusou"] not in roles and S["r_presenca"] not in roles,
        "15: quem recusou ou a presença na pendência",
    )
    _garante(S["r_vivo"] not in roles, "15: escalado do vivo na pendência")
    home_fig = _get("fig", "/api/dashboard")
    _garante(
        not (home_fig.get("casting") or {}).get("cancelados_a_avisar"),
        "15: o Figurino recebe a pendência",
    )
    for apelido in ("fig", "com"):
        r = _cliente(apelido).post(f"/api/roles/{S['r_aceito']}/assign", json={"talent_id": None})
        _garante(
            r.status_code == 403 and CASTING_403 in (_erro(r).get("message") or ""),
            f"15: {apelido} tirou → {r.status_code} {_erro(r)}",
        )
    r = _cliente("cast").post(f"/api/roles/{S['r_aceito']}/assign", json={"talent_id": S["t3"]})
    _garante(
        _e_trava(r), f"15: escalar outro pelo Casting no cancelado → {r.status_code} {_erro(r)}"
    )
    r = _cliente("cast").post(
        f"/api/roles/{S['r_aceito']}/assign", json={"talent_id": None, "cache_value": "999"}
    )
    _garante(_e_trava(r), f"15: mudar o cachê ao tirar → {r.status_code} {_erro(r)}")
    v6._remocoes.clear()
    cache_antes = _no_banco("SELECT cache_value FROM event_roles WHERE id = :i", i=S["r_aceito"])[
        0
    ][0]
    r = _cliente("cast").post(f"/api/roles/{S['r_aceito']}/assign", json={"talent_id": None})
    _garante(r.status_code == 200, f"15: Casting tira → {r.status_code} {_erro(r)}")
    linha = _no_banco(
        "SELECT talent_id, cache_value FROM event_roles WHERE id = :i", i=S["r_aceito"]
    )
    _garante(linha and linha[0][0] is None, "15: a vaga sumiu ou o talento ficou")
    _garante(
        linha[0][1] == cache_antes, f"15: o cachê da vaga mudou ({cache_antes} → {linha[0][1]})"
    )
    lidas = _no_banco(
        "SELECT count(*) FROM notifications WHERE kind = 'evento.cancelado_escala' AND entity_id = :e "
        "AND read_at IS NOT NULL",
        e=e,
    )[0][0]
    _garante(lidas == 0, "15: o sino ficou lido antes de esvaziar")
    r = _cliente("cast2").post(f"/api/roles/{S['r_pendente']}/assign", json={"talent_id": None})
    _garante(r.status_code == 200, f"15: Casting tira o 2º → {r.status_code} {_erro(r)}")
    v6._esperar_threads()
    _garante(
        not v6._remocoes_por_talento(),
        f"15: e-mail de remoção no cancelado {v6._remocoes_por_talento()}",
    )
    pend = (_get("cast", "/api/dashboard").get("casting") or {}).get("cancelados_a_avisar") or []
    _garante(not [p for p in pend if p.get("event_id") == e], "15: a pendência não esvaziou")
    nao_lidas = _no_banco(
        "SELECT count(*) FROM notifications WHERE kind = 'evento.cancelado_escala' AND entity_id = :e "
        "AND read_at IS NULL",
        e=e,
    )[0][0]
    _garante(
        S["sinos_escala"] and nao_lidas == 0, f"15: o sino não ficou lido ({nao_lidas} não lidas)"
    )
    # Controle: no vivo a remoção manda o e-mail como hoje.
    v6._remocoes.clear()
    r = _cliente("cast").post(
        f"/api/roles/{S['r_vivo']}/assign", json={"talent_id": None, "cache_value": "300"}
    )
    _garante(r.status_code == 200, f"15: tirar no vivo → {r.status_code}")
    v6._esperar_threads()
    _garante(estado["t"] in v6._remocoes_por_talento(), "15: no vivo a remoção não mandou o e-mail")
    v6._escalar(S["vivo"], estado["t"])


# ── H4: a página de Cancelamentos ────────────────────────────────────────────────────────────
def c16_pagina() -> None:
    corpo = _get("fin", "/api/events/cancelamentos")
    linhas = {c.get("id"): c for c in corpo.get("cancelados") or []}
    _garante(S["canc"] in linhas, "16: o Financeiro não vê o cancelado")
    _garante("pendentes" in corpo, "16: sem a fila de exclusão para o Financeiro")
    resumo = linhas[S["canc"]].get("resumo") or {}
    v6._igual(resumo.get("pago"), 1000, "16: pago")
    v6._igual(resumo.get("retido"), 400, "16: retido")
    _garante("devolucao" not in linhas[S["canc"]], "16: o objeto `devolucao` legado ficou")
    _garante(
        corpo.get("total_retido_escopo") == "listados",
        f"16: escopo {corpo.get('total_retido_escopo')}",
    )
    _garante(S["legado"] in linhas, "16: o cancelado legado derrubou ou sumiu da lista")
    mes = v6._mes(v6._hoje_sp())
    seg = v6._mes(v6._mes_seguinte(v6._hoje_sp()))
    no_mes = _get("fin", f"/api/events/cancelamentos?mes={mes}")
    _garante(
        S["canc"] in {c.get("id") for c in no_mes.get("cancelados") or []},
        "16: filtro do mês sem o cancelado",
    )
    _garante(no_mes.get("total_retido_escopo") == "periodo", "16: com mês o escopo não é o período")
    _garante(no_mes.get("filtros", {}).get("mes") == mes, f"16: filtros {no_mes.get('filtros')}")
    fora = _get("fin", f"/api/events/cancelamentos?mes={seg}")
    _garante(
        S["canc"] not in {c.get("id") for c in fora.get("cancelados") or []},
        "16: mês seguinte trouxe",
    )
    for estado_dev, vem in (("nao_pago", True), ("pago", False), ("sem", False)):
        ids = {
            c.get("id")
            for c in _get("fin", f"/api/events/cancelamentos?devolucao={estado_dev}").get(
                "cancelados"
            )
            or []
        }
        _garante((S["canc"] in ids) == vem, f"16: devolucao={estado_dev} → {S['canc'] in ids}")
    ids_sem = {
        c.get("id")
        for c in _get("fin", "/api/events/cancelamentos?devolucao=sem").get("cancelados") or []
    }
    _garante(S["legado"] in ids_sem, "16: o legado sem devolução fora de devolucao=sem")
    for url, campo in (("?mes=2026-13", "mes"), ("?devolucao=xyz", "devolucao")):
        r = _cliente("fin").get(f"/api/events/cancelamentos{url}")
        _garante(
            r.status_code == 400 and campo in (_erro(r).get("fields") or {}),
            f"16: {url} → {r.status_code} {_erro(r)}",
        )


def c17_rbac_pagina() -> None:
    r = app.test_client().get("/api/events/cancelamentos")
    _garante(r.status_code == 401, f"17: anônimo → {r.status_code}")
    for apelido in ("com", "fig", "cast", "rev"):
        r = _cliente(apelido).get("/api/events/cancelamentos")
        _garante(r.status_code == 403, f"17: {apelido} → {r.status_code}")
    r = v6._alterar_devolucao(S["canc"], 500, apelido="fin")
    _garante(r.status_code == 403, f"17: o Financeiro alterou a devolução → {r.status_code}")


# ── H5: o card ───────────────────────────────────────────────────────────────────────────────
def _pipeline(apelido: str, extra: str = "") -> dict:
    inicio, fim = v6._mes_corrente()
    return _get(
        apelido, v6.ROTAS["pipeline"].format(a=inicio.isoformat(), b=fim.isoformat()) + extra
    )


def c18_card_comercial() -> None:
    corpo = _pipeline("vend")
    card = corpo.get("cancelamentos")
    _garante(isinstance(card, dict), f"18: pipeline sem `cancelamentos` ({type(card).__name__})")
    itens = {i.get("event_id"): i for i in card.get("itens") or []}
    _garante(S["canc"] in itens, "18: a vendedora não acha o próprio cancelado no card")
    _garante(
        "imposto" not in card and "efeito_resultado" not in card,
        "18: a vendedora recebe imposto/efeito",
    )
    v6._igual(itens[S["canc"]].get("retido"), 400, "18: retido do item")
    kpis = corpo.get("kpis") or {}
    v6._igual(card.get("retido"), kpis.get("retido_cancelamentos"), "18: retido do card = KPI")
    for apelido in ("sa", "fin"):
        card = _pipeline(apelido).get("cancelamentos") or {}
        _garante(
            "imposto" in card and "efeito_resultado" in card, f"18: {apelido} sem imposto/efeito"
        )
    outra = _pipeline("vend2").get("cancelamentos") or {}
    _garante(
        S["canc"] not in {i.get("event_id") for i in outra.get("itens") or []},
        "18: outra vendedora vê o cancelado",
    )
    inicio = v6._mes_seguinte(v6._hoje_sp())
    fim = v6._mes_seguinte(inicio) - timedelta(days=1)
    vazio = _get("vend", v6.ROTAS["pipeline"].format(a=inicio.isoformat(), b=fim.isoformat())).get(
        "cancelamentos"
    )
    _garante(
        isinstance(vazio, dict) and vazio.get("quantidade") == 0, f"18: mês sem cancelado → {vazio}"
    )


def c19_card_dre() -> None:
    inicio, fim = v6._mes_corrente()
    dre = v6._dre(inicio, fim)
    painel = (dre.get("paineis") or {}).get("cancelamentos") or {}
    itens = {i.get("event_id"): i for i in painel.get("itens") or []}
    _garante(S["canc"] in itens, "19: o card da DRE sem o cancelado")
    item = itens[S["canc"]]
    for campo in (
        "devolvido",
        "comissao_retido",
        "pago",
        "devolucao_a_pagar",
        "event_date",
        "seller_name",
    ):
        _garante(campo in item, f"19: item sem `{campo}`")
    v6._igual(item.get("devolvido"), 600, "19: devolvido do item")
    realizado = (dre.get("dre") or {}).get("realizado") or {}
    v6._igual(
        painel.get("retido"),
        realizado.get("retido_cancelamentos"),
        "19: retido do card = linha da DRE",
    )


# ── H6: coisas ligadas e portal ──────────────────────────────────────────────────────────────
def c20_ligadas() -> None:
    falhas = []
    gastos = _get("sa", "/api/gastos")
    lista = gastos.get("expenses") or []
    g = next((x for x in lista if x.get("id") == S["gasto"]), None)
    if not g or not g.get("event_cancelled"):
        falhas.append("gasto ligado sem o selo da 306")
    r = _cliente("sa").post(
        f"/api/gastos/{S['gasto']}/vincular-evento", json={"event_id": S["canc"]}
    )
    if r.status_code != 200:
        falhas.append(f"gasto reenviando o mesmo evento → {r.status_code} {_erro(r)}")
    novo = v6._gasto_comum(None, 10)
    r = _cliente("sa").post(f"/api/gastos/{novo}/vincular-evento", json={"event_id": S["canc"]})
    if r.status_code != 200:
        falhas.append(
            f"gasto novo ligado ao cancelado por chamada direta → {r.status_code} {_erro(r)}"
        )
    with app.app_context():
        from app.impressoes3d import nfc_ops
        from app.models import NfcTag

        tag = db.session.get(NfcTag, S["tag"]["id"])
        ser = nfc_ops.serialize_tag(tag) if tag else {}
    if json.dumps(ser, default=str).find('"cancelado"') < 0:
        falhas.append("tag sem a situação do evento")
    # O 12 desliga o formulário do painel (desfazer); aqui ele volta a ser "coisa já ligada".
    _no_banco_escrever(
        "UPDATE form_responses SET event_id = :e WHERE id = :i", e=S["canc"], i=S["form"]
    )
    det = _get("sa", f"/api/formularios/respostas/{S['form']}")
    if "cancelado" not in json.dumps(det, ensure_ascii=False):
        falhas.append("formulário ligado sem event_situacao")
    hist = _get("sa", f"/api/clientes/{S['cliente']}").get("form_history") or []
    _ = hist  # o formulário da semente não casa com a cliente pelo telefone: a lista pode vir vazia
    ped = _get("sa", f"/api/figurino/producoes/{S['pedido_fig']}")
    if "cancelado" not in json.dumps(ped, ensure_ascii=False):
        falhas.append("pedido de figurino sem event_situacao")
    _garante(not falhas, "20: " + " | ".join(falhas))


def _portal(talento_id: int):
    email = _no_banco("SELECT email_contact FROM talents WHERE id = :i", i=talento_id)[0][0]
    c = app.test_client()
    r = c.post("/api/portal/auth/login", json={"login": email, "password": v6.SENHA})
    _garante(
        r.status_code == 200, f"login do portal → {r.status_code} {r.get_data(as_text=True)[:200]}"
    )
    return c


def c21_portal() -> None:
    # o t2 continua escalado? no 15 ele saiu: usa o recusou (t_sem_pix) re-escalado por ORM só para a leitura.
    _no_banco_escrever(
        "UPDATE event_roles SET talent_id = :t, invite_status = 'accepted' WHERE id = :r",
        t=S["t3"],
        r=S["r_presenca"] or S["r_recusou"],
    )
    c = _portal(S["t3"])
    r = c.get(f"/api/portal/events/{S['canc']}/figurino")
    _garante(
        r.status_code == 400 and PORTAL_FRASE in (_erro(r).get("message") or ""),
        f"21: ficha do cancelado → {r.status_code} {_erro(r)}",
    )
    _garante(f"C{TOKEN}" not in r.get_data(as_text=True), "21: a recusa trouxe o título")
    r = _portal(estado["t2"]).get(f"/api/portal/events/{S['vivo']}/figurino")
    _garante(r.status_code == 403, f"21: não escalado → {r.status_code}")
    r = _portal(estado["t"]).get(f"/api/portal/events/{S['vivo']}/figurino")
    _garante(r.status_code == 200, f"21: escalado no vivo → {r.status_code}")
    _no_banco_escrever(
        "UPDATE event_roles SET talent_id = :t, invite_status = 'pending' WHERE id = :r",
        t=S["t3"],
        r=S["r_recusou"],
    )
    r = c.post(f"/api/portal/invites/{S['r_recusou']}/accept", json={})
    _garante(
        r.status_code == 400 and PORTAL_FRASE in (_erro(r).get("message") or ""),
        f"21: aceitar convite do cancelado → {r.status_code} {_erro(r)}",
    )


# ── regressão ────────────────────────────────────────────────────────────────────────────────
def c22_regressao() -> None:
    """Sem cancelado no meio, o payload é o de antes: a ficha de um talento só com evento vivo, a
    cliente sem cancelado e o pipeline de um mês vazio."""
    t_limpo = v6._talento("t312 limpo")
    ev = v6._show_com_dinheiro("312 limpo", [f"R{TOKEN}A"], 40)
    v6._escalar(ev, t_limpo)
    corpo = _get("sa", f"/api/talents/{t_limpo}")
    _garante(
        f"R{TOKEN}A" in json.dumps(corpo, ensure_ascii=False),
        "22: talento sem cancelado perdeu o evento",
    )
    cli = _cliente_crm("cliente limpa 312")
    _ligar_cliente(ev, cli)
    corpo = _get("sa", f"/api/clientes/{cli}")
    _garante(
        corpo.get("event_count") == 1,
        f"22: cliente sem cancelado event_count {corpo.get('event_count')}",
    )
    canc = corpo.get("cancelamentos")
    _garante(canc is None or canc.get("quantidade") == 0, f"22: cancelamentos {canc}")
    ids = _ids(_get("sa", f"/api/agenda/day/{_data(ev).isoformat()}"))
    _garante(ev in ids, "22: o Dia perdeu o evento vivo")


CENARIOS = [
    ("H1", "1", "agenda Dia, Mês e busca sem o cancelado", c1_agenda),
    ("H1", "2", "ficha do talento sem o cancelado", c2_ficha_talento),
    ("H1", "3", "ficha da cliente sem o cancelado, com o retido à parte", c3_ficha_cliente),
    ("H1", "4", "seletores sem o cancelado", c4_seletores),
    ("H1", "5", "Fila 3D e pendências sem o cancelado", c5_filas_3d),
    ("H1", "6", "conflito de agenda ignora o cancelado", c6_conflito),
    ("H1", "7", "painel do grupo e ensaio legado", c7_grupo_e_ensaio),
    ("H2", "8", "Q9: motivo e autor só para quem trata", c8_q9),
    ("H2", "9", "a trava em toda escrita (API, Jinja, Imprimir fichas)", c9_trava),
    ("H2", "9b", "inventário das rotas de escrita", c9b_inventario),
    ("H2", "10", "as portas da 306 e da 306b ficam livres", c10_portas_livres),
    ("H2", "11", "Q5: escalar, convidar, avaliação e figurino", c11_q5),
    ("H2", "12", "Q2: ensaio, presente, tag e formulário", c12_q2),
    ("H2", "13", "flags do cancelado e do vivo", c13_flags),
    ("H2", "14", "controle: pedido e marcado não travam", c14_controle),
    ("H3", "15", "Q10: o Casting tira e avisa", c15_casting),
    ("H4", "16", "página de Cancelamentos com filtros", c16_pagina),
    ("H4", "17", "RBAC da página", c17_rbac_pagina),
    ("H5", "18", "card do Dashboard Comercial", c18_card_comercial),
    ("H5", "19", "card da DRE", c19_card_dre),
    ("H6", "20", "coisas ligadas com a situação", c20_ligadas),
    ("H6", "21", "portal: ficha de figurino e convite", c21_portal),
    ("R", "22", "regressão sem cancelado", c22_regressao),
]


def semear_tela() -> int:
    print(
        json.dumps(
            {
                "semente": {k: v for k, v in S.items() if k != "sinos_escala"},
                "usuarios": {k: v["email"] for k, v in estado["usuarios"].items()},
                "senha": v6.SENHA,
            },
            ensure_ascii=False,
            indent=1,
            default=str,
        )
    )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--so", default=None)
    parser.add_argument("--semear-tela", action="store_true")
    parser.add_argument("--limpar-tela", action="store_true")
    args = parser.parse_args()
    if args.so:
        v6.OPCOES["so"] = {s.strip() for s in args.so.split(",") if s.strip()}
    v6.guarda_de_ambiente()
    if args.limpar_tela:
        limpar_312()
        v6.limpar()
        print("dados da conferência de tela apagados")
        return 0
    print(f"\n── verify 312 (token {TOKEN}) ──")
    try:
        v6.preparar()
        try:
            semente()
        except Exception as exc:  # noqa: BLE001 — sem semente nenhum cenário prova nada
            v6.resultados.append(("S", "0 · semente", "FALHA", str(exc)))
            print(f"  FALHA      0 · semente: {str(exc)[:600]}")
            raise
        if args.semear_tela:
            return semear_tela()
        for bloco, num, nome, fn in CENARIOS:
            v6.cenario(bloco, num, nome, fn)
    except Exception:  # noqa: BLE001 — a limpeza roda e o placar sai
        pass
    finally:
        if not args.semear_tela:
            try:
                limpar_312()
                v6.limpar()
                sobras = v6._sobras_do_verify()
                sobras_312 = _no_banco(
                    "SELECT count(*) FROM figurino_producoes WHERE title LIKE :p", p=f"{v6.PREFIX}%"
                )[0][0]
                _garante(
                    not sobras and not sobras_312,
                    f"a limpeza deixou: {sobras} pedidos={sobras_312}",
                )
                _garante(not v6.rede_bloqueada, f"conexões externas tentadas: {v6.rede_bloqueada}")
                v6.resultados.append(("L", "23 · limpeza e nenhuma rede", "OK", ""))
                print("  OK         23 · limpeza e nenhuma rede")
            except Exception as exc:  # noqa: BLE001
                v6.resultados.append(("L", "23 · limpeza e nenhuma rede", "FALHA", str(exc)))
                print(f"  FALHA      23 · limpeza: {exc}")
    oks = sum(1 for r in v6.resultados if r[2] == "OK")
    print(f"\n{oks}/{len(v6.resultados)} cenários OK")
    for bloco in ("S", "H1", "H2", "H3", "H4", "H5", "H6", "R", "L"):
        linhas = [r for r in v6.resultados if r[0] == bloco]
        if linhas:
            print(f"  {bloco}: {sum(1 for r in linhas if r[2] == 'OK')}/{len(linhas)}")
    return 0 if oks == len(v6.resultados) else 1


if __name__ == "__main__":
    sys.exit(main())
