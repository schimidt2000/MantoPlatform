"""Verificação funcional da feature 205 — Loja de Interações Virtuais.

Roda contra a cópia local de produção (`manto_local`, Postgres) via DATABASE_URL.
REGRA: requests do test client SEMPRE fora de `app.app_context()`.

Cenários implementados:
  V0 — Fundação: dinheiro em Numeric e conversão de centavos confinada ao cliente da operadora.
  V1 — Campanha: rascunho invisível, geração idempotente de horários, publicação, RBAC.
  V2 — Reserva e soft lock: disputa simultânea com duas conexões reais, limites anti-abuso,
       expiração preguiçosa e duplo clique.
  V3 — Efetivação: caminho feliz, reentrega quíntupla, segredo inválido, não pago, valor
       divergente, operadora indisponível, aviso órfão e conflito com devolução.
  V4 — Upsell 3D: peça liberada no payload, total somado, presente na Fila de Impressão.
  V5 — Fila de Produção: linha completa, fluxo de status, envio do vídeo e caminho de falha.
  V6 — Privacidade: validação dupla, bloqueio por tentativas e varredura de vazamento.
  V7 — Sincronização não altera nem apaga evento de venda virtual.
  V8 — Um aviso por pedido e a política de retry (3 tentativas nos minutos 0, 1 e 2).
  V9 — Financeiro segregado: 10 vendas virtuais não mexem em volume, ticket médio nem base de
       comissão; o DRE sobe exatamente a soma e o canal aparece identificado.
  V10 — Resiliência: Calendar API em 503 e servidor de e-mail em 500. A venda se efetiva mesmo
       assim, a varredura retenta com o intervalo de 1 minuto, desiste depois de 3, a falha fica
       visível na fila, e o retorno dos serviços fecha o fluxo de ponta a ponta.

Uso:
    $env:DATABASE_URL = (Get-Content .local-db-url -Raw).Trim()
    $env:PYTHONPATH = (Get-Location).Path
    .venv\\Scripts\\python.exe specs\\205-loja-interacoes-virtuais\\verify_205.py
"""

import os
import secrets
import sys
from datetime import date, datetime, time, timedelta
from decimal import Decimal

# Os rótulos usam acento e seta ("→"). No Windows, quando a saída é redirecionada (pipe, arquivo,
# CI), o Python cai no codepage do console e explode com UnicodeEncodeError no meio do relatório —
# escondendo a falha real. Forçar UTF-8 aqui deixa o script rodável em qualquer console.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

if "sqlite" in os.environ.get("DATABASE_URL", "sqlite"):
    sys.exit("ERRO: aponte DATABASE_URL para manto_local (Postgres), nunca SQLite.")

from app import create_app, db  # noqa: E402
from app.constants import RoleName, now_sp  # noqa: E402
from app.models import (  # noqa: E402
    CalendarEvent,
    CatalogCharacter,
    CatalogItem,
    User,
    VirtualCampaign,
    VirtualOrder,
)

PASSWORD = "verify-205-senha"

# Identificador desta execução — ver a nota em `webhook()`.
RUN_ID = secrets.token_hex(4)

app = create_app()
results: list[tuple[str, bool, str]] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    results.append((name, ok, detail))
    print(f"{'PASS' if ok else 'FAIL'}  {name}" + (f"  [{detail}]" if detail and not ok else ""))


def limpar_campanha(camp_id: int) -> None:
    """Apaga uma campanha de teste e tudo que pende dela.

    A ordem não é opcional: `virtual_campaign_slots.order_id` e `virtual_orders.slot_id` apontam
    um para o outro. Apagar em qualquer outra ordem esbarra numa das duas FKs. Primeiro desfazemos
    o vínculo do slot, depois os pedidos saem, e só então a campanha (que cascateia os slots).

    Precisa rodar dentro de `app.app_context()`.
    """
    from app.models import VirtualCampaignSlot as _S

    _S.query.filter_by(campaign_id=camp_id).update({"order_id": None}, synchronize_session=False)
    db.session.commit()
    from app.models import (
        CalendarEvent as _CE,
    )
    from app.models import (
        VirtualPaymentNotification as _PNc,
    )
    from app.models import (
        VirtualRefundRequest as _RRc,
    )

    # Tudo que aponta para o pedido sai antes dele. Notificações e devoluções existem justamente
    # para sobreviver ao fluxo normal (são auditoria e dinheiro pendente) — por isso nenhuma tem
    # cascade, e por isso a limpeza do teste precisa ser explícita.
    eventos_para_apagar = []
    for pedido in VirtualOrder.query.filter_by(campaign_id=camp_id).all():
        _PNc.query.filter_by(order_id=pedido.id).delete(synchronize_session=False)
        _RRc.query.filter_by(order_id=pedido.id).delete(synchronize_session=False)
        if pedido.event_id:
            eventos_para_apagar.append(pedido.event_id)
        db.session.delete(pedido)
    db.session.commit()

    # Os eventos gerados pelas vendas também são do teste — não podem ficar na Agenda local.
    for ev in _CE.query.filter(_CE.id.in_(eventos_para_apagar)).all() if eventos_para_apagar else []:
        db.session.delete(ev)
    db.session.commit()
    # Avisos órfãos e recusados desta execução (não têm pedido para pendurar).
    _PNc.query.filter(_PNc.transaction_nsu.like(f"{RUN_ID}-%")).delete(synchronize_session=False)
    db.session.commit()
    camp = VirtualCampaign.query.get(camp_id)
    if camp is not None:
        db.session.delete(camp)
        db.session.commit()


# ── Preparação: usuários e um personagem ativo para a campanha ───────────────

with app.app_context():
    superadmin = (
        User.query.filter(User.has_access.is_(True))
        .filter(User.roles.any(name=RoleName.SUPERADMIN))
        .first()
    )
    outsider = (
        User.query.filter(User.has_access.is_(True))
        .filter(~User.roles.any(name=RoleName.SUPERADMIN))
        .filter(~User.roles.any(name=RoleName.COMERCIAL))
        .filter(User.email.isnot(None))
        .first()
    )
    if not superadmin:
        sys.exit("ERRO: manto_local sem usuário SUPERADMIN com acesso.")

    superadmin.set_password(PASSWORD)
    if outsider:
        outsider.set_password(PASSWORD)

    # Personagem próprio da verificação. Criamos em vez de reusar um existente porque a cópia
    # local pode não ter nenhum (a feature 185 não populou este banco), e porque um fixture
    # próprio deixa o script rodável em qualquer máquina sem depender do estado do dump.
    tema = CatalogItem.query.first()
    if not tema:
        sys.exit("ERRO: manto_local sem CatalogItem — o personagem precisa de um tema pai.")

    # Limpa restos de uma execução interrompida antes de recriar — um script de verificação
    # precisa poder rodar duas vezes seguidas sem cuidado manual.
    antigo = CatalogCharacter.query.filter_by(slug="verify205-personagem").first()
    if antigo is not None:
        for camp in VirtualCampaign.query.filter_by(catalog_character_id=antigo.id).all():
            limpar_campanha(camp.id)
        db.session.delete(antigo)
        db.session.commit()

    character = CatalogCharacter(
        catalog_item_id=tema.id,
        name="Verify205 Personagem",
        slug="verify205-personagem",
        is_active=True,
    )
    db.session.add(character)
    db.session.flush()

    superadmin_email = superadmin.email
    outsider_email = outsider.email if outsider else None
    character_id = character.id
    db.session.commit()

client = app.test_client()
campaign_id: int | None = None
slug: str | None = None


def login(email: str) -> None:
    client.post("/api/auth/login", json={"email": email, "password": PASSWORD})


try:
    # ── V0: fundação monetária (Princípio IX) ────────────────────────────────
    from app.integracoes import infinitepay_client as ipc

    check(
        "V0.1 conversão reais→centavos usa Decimal",
        ipc.reais_para_centavos(Decimal("150.00")) == 15000,
        f"obtido {ipc.reais_para_centavos(Decimal('150.00'))}",
    )
    check(
        "V0.2 conversão centavos→reais devolve Decimal",
        ipc.centavos_para_reais(19000) == Decimal("190.00"),
        f"obtido {ipc.centavos_para_reais(19000)}",
    )
    try:
        ipc.reais_para_centavos(150.0)
        float_recusado = False
    except TypeError:
        float_recusado = True
    check("V0.3 float é recusado como dinheiro", float_recusado)

    with app.app_context():
        import sqlalchemy as sa

        insp = sa.inspect(db.engine)
        nao_numeric = [
            f"{t}.{c['name']}"
            for t in insp.get_table_names()
            if t.startswith("virtual_")
            for c in insp.get_columns(t)
            if any(k in c["name"] for k in ("price", "total", "amount"))
            and "NUMERIC" not in str(c["type"]).upper()
        ]
    check("V0.4 nenhuma coluna monetária fora de Numeric", not nao_numeric, str(nao_numeric))

    # ── V1: campanha (US1) ───────────────────────────────────────────────────
    login(superadmin_email)

    resp = client.post(
        "/api/virtuais/campanhas",
        json={
            "catalog_character_id": character_id,
            "title": "Verify205 Papai Noel",
            "price_live": "150.00",
            "price_recorded": "90.00",
            "price_gift": "40.00",
            "recorded_capacity": 5,
            "recorded_delivery_days": 7,
            "tolerance_terms": "Tolerância de 10 minutos.",
        },
    )
    check("V1.1 cria campanha", resp.status_code == 201, f"{resp.status_code} {resp.get_data(as_text=True)[:200]}")
    if resp.status_code == 201:
        body = resp.get_json()
        campaign_id = body["id"]
        slug = body["slug"]
        check("V1.2 campanha nasce em rascunho", body["status"] == "rascunho", body["status"])
        check(
            "V1.3 preços voltam em reais decimais, não centavos",
            body["price_live"] == "150.00",
            str(body["price_live"]),
        )

    # Rascunho é invisível para o público.
    resp = client.get(f"/api/virtuais/campanhas/{slug}")
    check("V1.4 rascunho invisível no público (404)", resp.status_code == 404, str(resp.status_code))

    # Publicar sem capa deve ser bloqueado com o campo culpado.
    resp = client.post(f"/api/virtuais/campanhas/{campaign_id}/publicar", json={"status": "publicada"})
    faltou_capa = resp.status_code == 400 and "cover_url" in (resp.get_json() or {}).get("error", {}).get("fields", {})
    check("V1.5 publicar sem capa é bloqueado no campo", faltou_capa, resp.get_data(as_text=True)[:200])

    with app.app_context():
        campanha = VirtualCampaign.query.get(campaign_id)
        campanha.cover_url = "/uploads/virtual_covers/verify205.jpg"
        db.session.commit()

    resp = client.post(f"/api/virtuais/campanhas/{campaign_id}/publicar", json={"status": "publicada"})
    check("V1.6 publica com tudo preenchido", resp.status_code == 200, resp.get_data(as_text=True)[:200])

    resp = client.get(f"/api/virtuais/campanhas/{slug}")
    check("V1.7 publicada responde no público", resp.status_code == 200, str(resp.status_code))

    # Geração de horários — a segunda execução não pode duplicar nada (FR-004).
    amanha = (date.today() + timedelta(days=30)).isoformat()
    resp = client.post(
        f"/api/virtuais/campanhas/{campaign_id}/horarios",
        json={"date": amanha, "start": "14:00", "end": "18:00"},
    )
    primeira = resp.get_json() if resp.status_code == 201 else {}
    check(
        "V1.8 gera 24 horários de 10 min em 4h",
        primeira.get("created") == 24 and primeira.get("skipped") == 0,
        str(primeira),
    )

    resp = client.post(
        f"/api/virtuais/campanhas/{campaign_id}/horarios",
        json={"date": amanha, "start": "14:00", "end": "18:00"},
    )
    segunda = resp.get_json() if resp.status_code == 201 else {}
    check(
        "V1.9 reexecutar é idempotente (created=0, skipped=24)",
        segunda.get("created") == 0 and segunda.get("skipped") == 24,
        str(segunda),
    )

    resp = client.get(f"/api/virtuais/campanhas/{slug}/horarios")
    slots = (resp.get_json() or {}).get("slots", [])
    check("V1.10 horários aparecem no público", len(slots) == 24, f"{len(slots)} slots")

    # Horário vendido não pode ser removido (FR-008).
    with app.app_context():
        from app.models import VirtualCampaignSlot

        slot = VirtualCampaignSlot.query.filter_by(campaign_id=campaign_id).first()
        slot.status = "vendido"
        db.session.commit()
        slot_vendido_id = slot.id

    resp = client.delete(f"/api/virtuais/horarios/{slot_vendido_id}")
    check("V1.11 remover horário vendido dá 409", resp.status_code == 409, str(resp.status_code))

    with app.app_context():
        slot = VirtualCampaignSlot.query.get(slot_vendido_id)
        slot.status = "livre"
        db.session.commit()

    resp = client.delete(f"/api/virtuais/horarios/{slot_vendido_id}")
    check("V1.12 remover horário livre funciona", resp.status_code == 200, str(resp.status_code))

    # Pausar tira do ar com 410 (distinto de 404 — já existiu e pode voltar).
    resp = client.post(f"/api/virtuais/campanhas/{campaign_id}/publicar", json={"status": "pausada"})
    resp = client.get(f"/api/virtuais/campanhas/{slug}")
    check("V1.13 pausada responde 410 no público", resp.status_code == 410, str(resp.status_code))

    # RBAC: quem não é COMERCIAL nem SUPERADMIN não gere campanha (FR-010).
    if outsider_email:
        client.post("/api/auth/logout")
        login(outsider_email)
        resp = client.get("/api/virtuais/campanhas")
        check("V1.14 usuário sem papel recebe 403", resp.status_code == 403, str(resp.status_code))
        client.post("/api/auth/logout")
        login(superadmin_email)

    # ── V2: reserva e soft lock (US2) ────────────────────────────────────────
    #
    # Reativa a campanha e configura a operadora com um handle fake — a criação do link é
    # monkeypatchada, porque bater na InfinitePay de verdade num teste seria lento e frágil.
    client.post(f"/api/virtuais/campanhas/{campaign_id}/publicar", json={"status": "publicada"})

    with app.app_context():
        from app.models import SiteSetting

        settings = SiteSetting.query.get(1)
        settings.infinitepay_handle = "verify205"
        settings.infinitepay_webhook_token = "verify205-token"
        db.session.commit()

    from app.integracoes import infinitepay_client as ipc

    chamadas_operadora = {"n": 0}
    original_criar_link = ipc.criar_link_pagamento

    def fake_criar_link(**kwargs):
        chamadas_operadora["n"] += 1
        # Prova que o total chega como Decimal em reais, e não em centavos (Princípio IX).
        assert isinstance(kwargs["total"], Decimal), f"total veio {type(kwargs['total'])}"
        return {"payment_url": f"https://checkout.fake/{kwargs['order_nsu']}"}

    ipc.criar_link_pagamento = fake_criar_link

    def ficha(**extra):
        base = {
            "child_name": "Marina",
            "child_age": 6,
            "behavior_notes": "Adora dinossauros.",
            "contact_phone": "(11) 90000-0001",
            "contact_email": "mae@exemplo.com",
        }
        base.update(extra)
        return base

    # Horários disponíveis antes de qualquer reserva.
    slots_antes = (client.get(f"/api/virtuais/campanhas/{slug}/horarios").get_json() or {}).get("slots", [])
    alvo = slots_antes[0]["id"] if slots_antes else None
    check("V2.0 há horários para reservar", alvo is not None, f"{len(slots_antes)} slots")

    resp = client.post(
        f"/api/virtuais/campanhas/{slug}/reservar",
        json={"modality": "ao_vivo", "slot_id": alvo, **ficha()},
    )
    reserva = resp.get_json() if resp.status_code == 201 else {}
    check("V2.1 reserva criada", resp.status_code == 201, resp.get_data(as_text=True)[:200])
    order_token = reserva.get("public_token")

    with app.app_context():
        o = VirtualOrder.query.filter_by(public_token=order_token).first()
        lock_ok = o is not None and o.locked_until is not None
        janela = (o.locked_until - o.created_at).total_seconds() / 60 if lock_ok else 0
    check("V2.2 soft lock de 15 min a partir da criação", 14.5 <= janela <= 15.5, f"{janela:.1f} min")
    check(
        "V2.3 valores congelados em reais decimais",
        reserva.get("total_value") == "150.00",
        str(reserva.get("total_value")),
    )

    slots_depois = (client.get(f"/api/virtuais/campanhas/{slug}/horarios").get_json() or {}).get("slots", [])
    check(
        "V2.4 horário reservado some da lista pública",
        alvo not in [s["id"] for s in slots_depois],
        f"{len(slots_depois)} slots restantes",
    )

    # Limite por telefone: a segunda reserva com o mesmo contato devolve o pedido existente.
    livre2 = slots_depois[0]["id"]
    resp = client.post(
        f"/api/virtuais/campanhas/{slug}/reservar",
        json={"modality": "ao_vivo", "slot_id": livre2, **ficha()},
    )
    corpo = resp.get_json() or {}
    check(
        "V2.5 mesmo telefone → 429 com o pedido existente",
        resp.status_code == 429
        and corpo.get("error", {}).get("existing_order_token") == order_token,
        f"{resp.status_code} {resp.get_data(as_text=True)[:160]}",
    )

    # Duplo clique: mesmo client_token devolve o MESMO pedido, sem travar segundo horário.
    resp_a = client.post(
        f"/api/virtuais/campanhas/{slug}/reservar",
        json={
            "modality": "ao_vivo", "slot_id": livre2, "client_token": "tok-duplo",
            **ficha(contact_phone="(11) 90000-0002", contact_email="outra@exemplo.com"),
        },
    )
    resp_b = client.post(
        f"/api/virtuais/campanhas/{slug}/reservar",
        json={
            "modality": "ao_vivo", "slot_id": livre2, "client_token": "tok-duplo",
            **ficha(contact_phone="(11) 90000-0002", contact_email="outra@exemplo.com"),
        },
    )
    token_a = (resp_a.get_json() or {}).get("public_token")
    token_b = (resp_b.get_json() or {}).get("public_token")
    check(
        "V2.6 duplo clique devolve o mesmo pedido",
        resp_a.status_code == 201 and token_a and token_a == token_b,
        f"{resp_a.status_code}/{resp_b.status_code} {token_a} vs {token_b}",
    )

    # ── V2.7: DISPUTA SIMULTÂNEA com duas conexões reais ─────────────────────
    # É o caso que justifica `with_for_update()`. Duas threads, duas sessões de banco, o mesmo
    # slot. Rodar em sequência não provaria nada — o lock só aparece sob concorrência real.
    import threading

    with app.app_context():
        from app.models import VirtualCampaignSlot as _Slot

        disputado = (
            _Slot.query.filter_by(campaign_id=campaign_id, status="livre")
            .order_by(_Slot.start_at.desc())
            .first()
        )
        disputado_id = disputado.id

    resultados_disputa: list[int] = []
    lock_resultados = threading.Lock()

    def tentar_reservar(indice: int) -> None:
        c = app.test_client()
        r = c.post(
            f"/api/virtuais/campanhas/{slug}/reservar",
            json={
                "modality": "ao_vivo", "slot_id": disputado_id,
                **ficha(
                    contact_phone=f"(11) 91111-000{indice}",
                    contact_email=f"disputa{indice}@exemplo.com",
                ),
            },
        )
        with lock_resultados:
            resultados_disputa.append(r.status_code)

    threads = [threading.Thread(target=tentar_reservar, args=(i,)) for i in (1, 2)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    check(
        "V2.7 disputa simultânea: exatamente um 201 e um 409",
        sorted(resultados_disputa) == [201, 409],
        str(resultados_disputa),
    )

    with app.app_context():
        donos = VirtualOrder.query.filter_by(slot_id=disputado_id).count()
    check("V2.8 o horário disputado tem um único dono", donos == 1, f"{donos} pedidos")

    # Expiração preguiçosa: com o lock vencido, o horário reaparece sem a varredura rodar.
    with app.app_context():
        from app.models import VirtualCampaignSlot as _Slot2

        s = _Slot2.query.get(alvo)
        s.locked_until = now_sp() - timedelta(minutes=1)
        db.session.commit()

    slots_agora = (client.get(f"/api/virtuais/campanhas/{slug}/horarios").get_json() or {}).get("slots", [])
    check(
        "V2.9 lock vencido devolve o horário sem varredura",
        alvo in [s["id"] for s in slots_agora],
        "horário não reapareceu",
    )

    # Página do pedido: sem validar telefone, nada de dado de criança sai (FR-044a).
    resp = client.get(f"/api/virtuais/pedidos/{order_token}")
    corpo = resp.get_json() or {}
    vazou = [k for k in ("child_name", "child_age", "behavior_notes", "delivery_address") if k in corpo]
    check("V2.10 pedido responde sem login", resp.status_code == 200, str(resp.status_code))
    check("V2.11 resumo do pedido não vaza dado de criança", not vazou, f"vazou: {vazou}")
    check(
        "V2.12 dica do telefone mostra só os 4 últimos",
        corpo.get("phone_hint") == "•••• 0001",
        str(corpo.get("phone_hint")),
    )

    # Capacidade de vídeo gravado esgotada → 409 (FR-023).
    with app.app_context():
        camp = VirtualCampaign.query.get(campaign_id)
        camp.recorded_sold = camp.recorded_capacity
        db.session.commit()

    resp = client.post(
        f"/api/virtuais/campanhas/{slug}/reservar",
        json={
            "modality": "gravado",
            **ficha(contact_phone="(11) 92222-0001", contact_email="gravado@exemplo.com"),
        },
    )
    check("V2.13 vídeo gravado esgotado dá 409", resp.status_code == 409, str(resp.status_code))

    # Validação com campo culpado (FR-025).
    resp = client.post(
        f"/api/virtuais/campanhas/{slug}/reservar",
        json={"modality": "ao_vivo", "slot_id": alvo, **ficha(contact_email="nao-e-email")},
    )
    campos = (resp.get_json() or {}).get("error", {}).get("fields", {})
    check(
        "V2.14 e-mail inválido dá 400 no campo",
        resp.status_code == 400 and "contact_email" in campos,
        f"{resp.status_code} {campos}",
    )

    # Campanha pausada recusa reserva nova (FR-007).
    client.post(f"/api/virtuais/campanhas/{campaign_id}/publicar", json={"status": "pausada"})
    resp = client.post(
        f"/api/virtuais/campanhas/{slug}/reservar",
        json={"modality": "ao_vivo", "slot_id": alvo, **ficha(contact_phone="(11) 93333-0001")},
    )
    check("V2.15 campanha pausada recusa reserva", resp.status_code == 410, str(resp.status_code))

    ipc.criar_link_pagamento = original_criar_link
    check("V2.16 link de pagamento foi pedido à operadora", chamadas_operadora["n"] >= 1,
          f"{chamadas_operadora['n']} chamadas")

    # ── V3: efetivação idempotente (US3) — o cenário mais importante ─────────
    #
    # Isolamos o Google e a operadora: bater neles de verdade num teste seria lento e frágil, e o
    # que precisamos provar é a **decisão** do nosso código, não a API deles.
    from app.calendar import service as gcal_service
    from app.marketing import virtuais_ops as vops

    client.post(f"/api/virtuais/campanhas/{campaign_id}/publicar", json={"status": "publicada"})
    ipc.criar_link_pagamento = fake_criar_link

    eventos_criados = {"n": 0}

    def fake_insert_event(calendar_id, title, start_dt, end_dt, description="", location="",
                          conference_request_id=None):
        eventos_criados["n"] += 1
        return {
            "id": f"gcal-{eventos_criados['n']}-{conference_request_id}",
            "htmlLink": "https://calendar.google.com/event?eid=fake",
            "hangoutLink": "https://meet.google.com/abc-defg-hij",
        }

    gcal_insert_original = gcal_service.insert_event
    gcal_service.insert_event = fake_insert_event
    consultar_original = ipc.consultar_pagamento

    # `consultar_pagamento` é a fonte de verdade: o roteiro troca a resposta dela a cada caso.
    #
    # Por padrão ela devolve o total **do próprio pedido** — do contrário, todo caso teria que
    # lembrar de ajustar o valor à mão, e um esquecimento apareceria como "valor divergente",
    # escondendo o que o teste queria provar. Os casos que precisam de divergência forçam
    # `resposta_operadora` explicitamente.
    resposta_operadora = {"paid": True, "amount": None, "paid_amount": None,
                          "capture_method": "pix", "raw": {}}
    indisponivel = {"flag": False}

    def fake_consultar(**kwargs):
        if indisponivel["flag"]:
            raise ipc.InfinitePayIndisponivel("teste: operadora fora")
        resposta = dict(resposta_operadora)
        if resposta["paid_amount"] is None:
            with app.app_context():
                o = VirtualOrder.query.filter_by(order_nsu=kwargs.get("order_nsu")).first()
                resposta["paid_amount"] = Decimal(o.total_value) if o else Decimal("0")
        return resposta

    ipc.consultar_pagamento = fake_consultar

    # O V2 já provou o teto por origem; daqui em diante ele só atrapalharia (todas as reservas do
    # teste saem do mesmo test client, logo da mesma origem). Elevar o limite é exatamente o que
    # FR-020d prevê para picos legítimos de campanha.
    with app.app_context():
        camp = VirtualCampaign.query.get(campaign_id)
        camp.max_reservations_per_origin = 500
        db.session.commit()

    def nova_reserva(telefone: str, slot_id: int | None = None, modality: str = "ao_vivo"):
        """Cria uma reserva pela API pública e devolve o corpo da resposta.

        Falha alto se a reserva não sair: um helper que devolve `None` em silêncio faria o teste
        quebrar dez linhas adiante, escondendo a causa.
        """
        livres = (client.get(f"/api/virtuais/campanhas/{slug}/horarios").get_json() or {})["slots"]
        alvo_id = slot_id or (livres[0]["id"] if livres else None)
        r = client.post(
            f"/api/virtuais/campanhas/{slug}/reservar",
            json={"modality": modality, "slot_id": alvo_id if modality == "ao_vivo" else None,
                  **ficha(contact_phone=telefone, contact_email=f"{telefone}@ex.com")},
        )
        if r.status_code != 201:
            raise AssertionError(
                f"reserva de {telefone} falhou: {r.status_code} {r.get_data(as_text=True)[:200]}"
            )
        return r.get_json()

    def webhook(order_nsu: str, transaction: str, token: str = "verify205-token"):
        return client.post(
            f"/api/webhooks/infinitepay/{token}",
            json={"order_nsu": order_nsu, "transaction_nsu": f"{RUN_ID}-{transaction}",
                  "invoice_slug": "slug-teste", "amount": 15000, "paid_amount": 15000},
        )

    # V3.1 — caminho feliz.
    p1 = nova_reserva("(11) 94000-0001")
    r = webhook(p1["order_nsu"], "txn-feliz-1")
    check("V3.1 webhook responde 200", r.status_code == 200, str(r.status_code))

    with app.app_context():
        o = VirtualOrder.query.filter_by(order_nsu=p1["order_nsu"]).first()
        ev = o.event
        from app.models import EventRole as _ER
        from app.models import VirtualMediaDelivery as _MD

        escala = _ER.query.filter_by(event_id=o.event_id).count() if o.event_id else 0
        entrega = _MD.query.filter_by(order_id=o.id).count()
        dados = {
            "status": o.status, "event_id": o.event_id, "meet_url": o.meet_url,
            "tipo": ev.event_type if ev else None, "source": ev.source if ev else None,
            "sale_value": str(ev.sale_value) if ev else None,
            "slot_status": o.slot.status if o.slot else None,
            "escala": escala, "entrega": entrega,
        }
    check("V3.2 pedido vira pago", dados["status"] == "pago", str(dados["status"]))
    check("V3.3 evento criado como VIRTUAL/platform",
          dados["tipo"] == "VIRTUAL" and dados["source"] == "platform", str(dados))
    check("V3.4 evento carrega o valor da venda", dados["sale_value"] == "150.00", str(dados["sale_value"]))
    check("V3.5 meet_url preenchido (SC-011)", bool(dados["meet_url"]), str(dados["meet_url"]))
    check("V3.6 talento pré-escalado", dados["escala"] >= 1, f"{dados['escala']} cargo(s)")
    check("V3.7 entrega criada na fila de produção", dados["entrega"] == 1, str(dados["entrega"]))
    check("V3.8 horário marcado como vendido", dados["slot_status"] == "vendido", str(dados["slot_status"]))

    # V3.9 — REENTREGA QUÍNTUPLA: nada pode duplicar (SC-006).
    with app.app_context():
        from app.models import Event3DGift as _G
        from app.models import VirtualOrderNotification as _N

        antes = {
            "eventos": CalendarEvent.query.filter_by(event_type="VIRTUAL").count(),
            "escala": _ER.query.filter_by(event_id=dados["event_id"]).count(),
            "entregas": _MD.query.count(),
            "avisos": _N.query.count(),
            "presentes": _G.query.count(),
        }
    for _ in range(5):
        webhook(p1["order_nsu"], "txn-feliz-1")
    with app.app_context():
        depois = {
            "eventos": CalendarEvent.query.filter_by(event_type="VIRTUAL").count(),
            "escala": _ER.query.filter_by(event_id=dados["event_id"]).count(),
            "entregas": _MD.query.count(),
            "avisos": _N.query.count(),
            "presentes": _G.query.count(),
        }
    check("V3.9 reentrega x5 não duplica nada", antes == depois, f"{antes} != {depois}")

    # V3.10 — segredo inválido: 404 e nada criado.
    p2 = nova_reserva("(11) 94000-0002")
    with app.app_context():
        eventos_antes = CalendarEvent.query.filter_by(event_type="VIRTUAL").count()
    r = webhook(p2["order_nsu"], "txn-segredo", token="token-errado")
    with app.app_context():
        from app.models import VirtualPaymentNotification as _PN

        recusada = _PN.query.filter_by(transaction_nsu=f"{RUN_ID}-txn-segredo").first()
        eventos_depois = CalendarEvent.query.filter_by(event_type="VIRTUAL").count()
    check("V3.10 segredo inválido dá 404", r.status_code == 404, str(r.status_code))
    check("V3.11 tentativa recusada fica registrada",
          recusada is not None and recusada.secret_ok is False and recusada.outcome == "recusado",
          str(recusada.outcome if recusada else None))
    check("V3.12 segredo inválido não cria evento", eventos_antes == eventos_depois,
          f"{eventos_antes} -> {eventos_depois}")

    # V3.13 — operadora diz "não pago".
    resposta_operadora["paid"] = False
    r = webhook(p2["order_nsu"], "txn-naopago")
    with app.app_context():
        n = _PN.query.filter_by(transaction_nsu=f"{RUN_ID}-txn-naopago").first()
        o2 = VirtualOrder.query.filter_by(order_nsu=p2["order_nsu"]).first()
        estado = (n.recheck_result, n.outcome, o2.status)
    check("V3.13 'não pago' recusa a efetivação",
          estado == ("unpaid", "recusado", "aguardando"), str(estado))

    # V3.14 — valor divergente.
    resposta_operadora["paid"] = True
    resposta_operadora["paid_amount"] = Decimal("10.00")  # divergente de propósito
    r = webhook(p2["order_nsu"], "txn-divergente")
    with app.app_context():
        n = _PN.query.filter_by(transaction_nsu=f"{RUN_ID}-txn-divergente").first()
        o2 = VirtualOrder.query.filter_by(order_nsu=p2["order_nsu"]).first()
        estado = (n.recheck_result, n.outcome, o2.status)
    check("V3.14 valor divergente recusa a efetivação",
          estado == ("divergent", "recusado", "aguardando"), str(estado))

    # V3.15 — operadora indisponível: retém, nunca decide.
    resposta_operadora["paid_amount"] = None  # volta a espelhar o total do pedido
    indisponivel["flag"] = True
    r = webhook(p2["order_nsu"], "txn-indisponivel")
    with app.app_context():
        n = _PN.query.filter_by(transaction_nsu=f"{RUN_ID}-txn-indisponivel").first()
        o2 = VirtualOrder.query.filter_by(order_nsu=p2["order_nsu"]).first()
        estado = (n.recheck_result, n.outcome, o2.status)
    indisponivel["flag"] = False
    check("V3.15 indisponível retém o pedido, não decide",
          estado == ("unavailable", "retido", "aguardando"), str(estado))

    # V3.16 — notificação órfã.
    r = webhook("nsu-que-nao-existe", "txn-orfao")
    with app.app_context():
        n = _PN.query.filter_by(transaction_nsu=f"{RUN_ID}-txn-orfao").first()
    check("V3.16 aviso órfão é registrado, não descartado",
          r.status_code == 200 and n is not None and n.outcome == "orfao",
          str(n.outcome if n else None))

    # V3.17 — conflito: o horário foi vendido a outra pessoa enquanto o pagamento vinha.
    p3 = nova_reserva("(11) 94000-0003")
    with app.app_context():
        o3 = VirtualOrder.query.filter_by(order_nsu=p3["order_nsu"]).first()
        outro = VirtualOrder.query.filter_by(order_nsu=p1["order_nsu"]).first()
        # Simula o cenário real: entre o pagamento e o aviso, o horário passou para outro pedido.
        # Precisa ser um pedido que existe — a FK do slot não aceita id inventado.
        o3.slot.order_id = outro.id
        db.session.commit()
        eventos_antes = CalendarEvent.query.filter_by(event_type="VIRTUAL").count()
    r = webhook(p3["order_nsu"], "txn-conflito")
    with app.app_context():
        o3 = VirtualOrder.query.filter_by(order_nsu=p3["order_nsu"]).first()
        from app.models import VirtualRefundRequest as _RR

        devolucao = _RR.query.filter_by(order_id=o3.id).first()
        eventos_depois = CalendarEvent.query.filter_by(event_type="VIRTUAL").count()
        estado = (o3.status, o3.event_id, devolucao.status if devolucao else None)
    check("V3.17 conflito cancela e abre devolução",
          estado == ("cancelado", None, "pendente"), str(estado))
    check("V3.18 conflito não cria evento (SC-012)", eventos_antes == eventos_depois,
          f"{eventos_antes} -> {eventos_depois}")

    # ── V8: um único aviso por pedido (SC-020) ──────────────────────────────
    with app.app_context():
        avisos_compra = _N.query.filter_by(kind="compra_confirmada").count()
        pedidos_pagos = VirtualOrder.query.filter_by(status="pago").count()
    check("V8.1 um aviso de compra por pedido pago, mesmo com 6 webhooks",
          avisos_compra == pedidos_pagos, f"{avisos_compra} avisos / {pedidos_pagos} pagos")

    with app.app_context():
        cancelamentos = _N.query.filter_by(kind="cancelamento").count()
    check("V8.2 cancelamento também avisa uma vez", cancelamentos == 1, str(cancelamentos))

    # V8.3 — política de retry: 3 tentativas nos minutos 0, 1 e 2, sem a quarta.
    check("V8.3 primeira tentativa é imediata", vops.deve_tentar_novamente(0, None))
    check("V8.4 segunda espera 1 minuto",
          not vops.deve_tentar_novamente(1, now_sp()) and
          vops.deve_tentar_novamente(1, now_sp() - timedelta(minutes=1)))
    check("V8.5 não existe quarta tentativa",
          not vops.deve_tentar_novamente(3, now_sp() - timedelta(hours=1))
          and vops.retry_esgotou(3))

    # ── V7: sincronização não toca em evento virtual (SC-019) ───────────────
    from app.calendar.routes import _cleanup_stale_events, sync_events

    with app.app_context():
        virtuais = CalendarEvent.query.filter_by(event_type="VIRTUAL").all()
        antes_sync = {e.id: (e.title, e.start_at, e.event_type) for e in virtuais}
        ids_virtuais = list(antes_sync.keys())
        gid = virtuais[0].google_event_id if virtuais else None

        # A sincronização recebe o MESMO evento com título e horário alterados no Google.
        item_alterado = {
            "id": gid,
            "summary": "TITULO TROCADO NO GOOGLE",
            "start": {"dateTime": "2030-01-01T10:00:00-03:00"},
            "end": {"dateTime": "2030-01-01T11:00:00-03:00"},
        }
        sync_events([item_alterado])
        db.session.commit()

        depois_sync = {
            e.id: (e.title, e.start_at, e.event_type)
            for e in CalendarEvent.query.filter(CalendarEvent.id.in_(ids_virtuais)).all()
        }
    check("V7.1 sincronização não altera evento virtual", antes_sync == depois_sync,
          f"{antes_sync} != {depois_sync}")

    with app.app_context():
        # E o evento sumindo do Google não pode apagar a venda.
        mes = virtuais[0].start_at
        _cleanup_stale_events([], mes.year, mes.month)
        db.session.commit()
        sobreviveram = CalendarEvent.query.filter(CalendarEvent.id.in_(ids_virtuais)).count()
    check("V7.2 evento virtual sumido do Google não é apagado (FR-029b)",
          sobreviveram == len(ids_virtuais), f"{sobreviveram}/{len(ids_virtuais)}")

    # ── V4: upsell de presente 3D (US4) ─────────────────────────────────────
    from app.models import Acervo3DItem

    with app.app_context():
        peca = Acervo3DItem.query.filter_by(is_active=True).first()
        if peca is None:
            peca = Acervo3DItem(name="Verify205 Peça", photo_url="/uploads/x.jpg", is_active=True)
            db.session.add(peca)
            db.session.commit()
            peca_criada = True
        else:
            peca_criada = False
        peca_id = peca.id
        camp = VirtualCampaign.query.get(campaign_id)
        camp.acervo_items = [peca]
        db.session.commit()

    publico = client.get(f"/api/virtuais/campanhas/{slug}").get_json()
    check(
        "V4.1 peça liberada aparece no payload público",
        [g["id"] for g in publico.get("gift_items", [])] == [peca_id],
        str(publico.get("gift_items")),
    )

    r = client.post(
        f"/api/virtuais/campanhas/{slug}/reservar",
        json={
            "modality": "ao_vivo",
            "slot_id": (client.get(f"/api/virtuais/campanhas/{slug}/horarios").get_json()["slots"][0]["id"]),
            "gift_item_id": peca_id,
            "delivery_address": "Rua Teste, 100 - São Paulo/SP",
            **ficha(contact_phone="(11) 95000-0001", contact_email="presente@ex.com"),
        },
    )
    p_presente = r.get_json() if r.status_code == 201 else {}
    check(
        "V4.2 total soma o presente (150 + 40)",
        p_presente.get("total_value") == "190.00",
        f"{r.status_code} {p_presente.get('total_value')}",
    )

    webhook(p_presente["order_nsu"], "txn-presente")
    with app.app_context():
        o = VirtualOrder.query.filter_by(order_nsu=p_presente["order_nsu"]).first()
        from app.models import Event3DGift as _G3

        presentes = _G3.query.filter_by(event_id=o.event_id).all()
        estado_presente = [(g.item_id, g.status) for g in presentes]
    check(
        "V4.3 presente entra na Fila de Impressão como pendente",
        estado_presente == [(peca_id, "pendente")],
        str(estado_presente),
    )

    # Endereço é obrigatório só quando há presente (FR-014).
    r = client.post(
        f"/api/virtuais/campanhas/{slug}/reservar",
        json={
            "modality": "gravado", "gift_item_id": peca_id,
            **ficha(contact_phone="(11) 95000-0002", contact_email="semend@ex.com"),
        },
    )
    campos = (r.get_json() or {}).get("error", {}).get("fields", {})
    check(
        "V4.4 presente sem endereço dá 400 no campo",
        r.status_code == 400 and "delivery_address" in campos,
        f"{r.status_code} {campos}",
    )

    # Peça fora do acervo liberado é recusada (FR-016).
    r = client.post(
        f"/api/virtuais/campanhas/{slug}/reservar",
        json={
            "modality": "gravado", "gift_item_id": 999999,
            "delivery_address": "Rua X, 1",
            **ficha(contact_phone="(11) 95000-0003", contact_email="fora@ex.com"),
        },
    )
    check("V4.5 peça fora do acervo liberado é recusada", r.status_code == 400, str(r.status_code))

    # ── V5/V6: fila de produção, vídeo e validação dupla (US5) ──────────────
    import io as _io

    with app.app_context():
        from app.models import VirtualMediaDelivery as _MD2

        o = VirtualOrder.query.filter_by(order_nsu=p1["order_nsu"]).first()
        entrega_ao_vivo = _MD2.query.filter_by(order_id=o.id).first()
        entrega_id = entrega_ao_vivo.id
        token_pago = o.public_token
        telefone_certo = o.contact_phone_display

    fila = client.get("/api/virtuais/producao").get_json()
    linhas = fila.get("deliveries", [])
    primeira = linhas[0] if linhas else {}
    check("V5.1 fila lista as entregas pagas", len(linhas) >= 1, f"{len(linhas)} linha(s)")
    check(
        "V5.2 a linha cruza horário, criança, dicas e presente",
        all(k in primeira for k in ("start_at", "child_name", "behavior_notes", "gift")),
        str(sorted(primeira.keys())),
    )
    check(
        "V5.3 a fila nunca devolve o caminho do vídeo no disco",
        "video_path" not in primeira,
        str([k for k in primeira if "path" in k]),
    )

    r = client.patch(f"/api/virtuais/producao/{entrega_id}", json={"status": "gravando"})
    check("V5.4 muda para gravando", r.status_code == 200 and r.get_json()["status"] == "gravando",
          f"{r.status_code} {r.get_data(as_text=True)[:120]}")

    r = client.patch(f"/api/virtuais/producao/{entrega_id}", json={"status": "publicado"})
    check("V5.5 status fora dos três é recusado (FR-048a)", r.status_code == 400, str(r.status_code))

    # Entrega GRAVADA não finaliza sem vídeo (FR-048).
    # O V2.13 zerou a capacidade de propósito (caso "esgotado"); repõe para seguir.
    with app.app_context():
        camp = VirtualCampaign.query.get(campaign_id)
        camp.recorded_capacity = camp.recorded_sold + 10
        db.session.commit()

    r = client.post(
        f"/api/virtuais/campanhas/{slug}/reservar",
        json={"modality": "gravado", **ficha(contact_phone="(11) 96000-0001", contact_email="grav@ex.com")},
    )
    if r.status_code != 201:
        raise AssertionError(
            f"reserva de vídeo gravado falhou: {r.status_code} {r.get_data(as_text=True)[:200]}"
        )
    p_grav = r.get_json()
    webhook(p_grav["order_nsu"], "txn-gravado")
    with app.app_context():
        og = VirtualOrder.query.filter_by(order_nsu=p_grav["order_nsu"]).first()
        entrega_grav = _MD2.query.filter_by(order_id=og.id).first()
        entrega_grav_id = entrega_grav.id
        token_grav = og.public_token
        telefone_grav = og.contact_phone_display

    r = client.patch(f"/api/virtuais/producao/{entrega_grav_id}", json={"status": "finalizado"})
    campos = (r.get_json() or {}).get("error", {}).get("fields", {})
    check(
        "V5.6 gravado não finaliza sem vídeo",
        r.status_code == 400 and "video" in campos,
        f"{r.status_code} {campos}",
    )

    # Formato não suportado é recusado (FR-038d).
    r = client.post(
        f"/api/virtuais/producao/{entrega_grav_id}/video",
        data={"video": (_io.BytesIO(b"nao-e-video"), "arquivo.txt")},
        content_type="multipart/form-data",
    )
    check("V5.7 formato não suportado dá 400", r.status_code == 400, str(r.status_code))

    with app.app_context():
        eg = _MD2.query.get(entrega_grav_id)
        estado = (eg.status, eg.video_path)
    check("V5.8 falha no envio não finaliza a entrega", estado == ("pendente", None), str(estado))

    # Envio válido → finaliza e avisa.
    r = client.post(
        f"/api/virtuais/producao/{entrega_grav_id}/video",
        data={"video": (_io.BytesIO(b"\x00\x00\x00\x18ftypmp42" + b"x" * 2048), "video.mp4")},
        content_type="multipart/form-data",
    )
    check("V5.9 envio válido responde 200", r.status_code == 200, r.get_data(as_text=True)[:160])
    with app.app_context():
        eg = _MD2.query.get(entrega_grav_id)
        estado = (eg.status, bool(eg.video_path), eg.video_size_bytes)
        avisos_video = _N.query.filter_by(order_id=eg.order_id, kind="video_pronto").count()
        # Contar a linha prova a **trava**, não a **entrega**: a linha é gravada antes do disparo.
        # `attempts` é o que separa "o sistema tentou avisar" de "o sistema achou que avisou".
        aviso_video = _N.query.filter_by(order_id=eg.order_id, kind="video_pronto").first()
        tentou_enviar = bool(aviso_video and (aviso_video.attempts or 0) >= 1)
    check("V5.10 entrega finaliza com o vídeo guardado", estado[0] == "finalizado" and estado[1],
          str(estado))

    # Vídeo gravado não tem chamada — pedir sala criaria um link que ninguém usa, e a família
    # veria "entrar na chamada" num produto que não tem chamada.
    with app.app_context():
        og2 = VirtualOrder.query.filter_by(order_nsu=p_grav["order_nsu"]).first()
        sala_gravado = (og2.meet_url, og2.meet_pending)
    check("V5.10b vídeo gravado não ganha sala nem fica pendente", sala_gravado == (None, False),
          str(sala_gravado))
    check("V5.11 família avisada uma vez do vídeo", avisos_video == 1, str(avisos_video))
    check("V5.11b o aviso do vídeo foi de fato disparado, não só registrado (FR-039)",
          tentou_enviar, f"attempts={aviso_video.attempts if aviso_video else None}")

    # Guarda estrutural: um `kind` sem enviador não estoura — grava a linha e volta calado. O bug
    # não aparece em lugar nenhum até uma família reclamar que não recebeu.
    with app.app_context():
        from app.constants import VIRTUAL_NOTIFICATION_KINDS as _KINDS
        from app.marketing.virtuais_ops import _enviadores_de_aviso as _envs

        sem_enviador = [k for k in _KINDS if k not in _envs()]
    check("V5.11c todo tipo de aviso tem enviador (nenhum falha em silêncio)",
          not sem_enviador, str(sem_enviador))

    # ── V6: validação dupla e privacidade ───────────────────────────────────
    resumo = client.get(f"/api/virtuais/pedidos/{token_pago}").get_json()
    sensiveis = ["child_name", "child_age", "behavior_notes", "delivery_address", "video_url"]
    check(
        "V6.1 resumo do pedido não traz dado de criança",
        [k for k in sensiveis if k in resumo] == [],
        str([k for k in sensiveis if k in resumo]),
    )

    r = client.get(f"/api/virtuais/pedidos/{token_pago}/completo")
    check("V6.2 dados completos exigem validação (401)", r.status_code == 401, str(r.status_code))

    r = client.post(f"/api/virtuais/pedidos/{token_pago}/verificar", json={"phone": "(11) 90000-0000"})
    corpo = r.get_json() or {}
    check(
        "V6.3 telefone errado dá 401 com tentativas restantes",
        r.status_code == 401 and "attempts_left" in corpo.get("error", {}),
        f"{r.status_code} {corpo}",
    )

    r = client.post(f"/api/virtuais/pedidos/{token_pago}/verificar", json={"phone": telefone_certo})
    completo = r.get_json() if r.status_code == 200 else {}
    check("V6.4 telefone certo libera os dados", r.status_code == 200, str(r.status_code))
    check(
        "V6.5 dados completos trazem a ficha da criança",
        completo.get("child_name") and completo.get("verified") is True,
        str(completo.get("child_name")),
    )
    check(
        "V6.6 nem aqui o caminho do arquivo é devolvido",
        "video_path" not in completo,
        str([k for k in completo if "path" in k]),
    )

    # Vídeo: sem sessão dá 401; com sessão, serve o arquivo.
    c_anonimo = app.test_client()
    r = c_anonimo.get(f"/api/virtuais/pedidos/{token_grav}/video")
    check("V6.7 vídeo sem validação dá 401", r.status_code == 401, str(r.status_code))

    r = c_anonimo.post(f"/api/virtuais/pedidos/{token_grav}/verificar", json={"phone": telefone_grav})
    check("V6.8 valida o telefone do pedido gravado", r.status_code == 200, str(r.status_code))
    r = c_anonimo.get(f"/api/virtuais/pedidos/{token_grav}/video")
    check("V6.9 com sessão, o vídeo é servido", r.status_code == 200, str(r.status_code))

    # O que o player precisa não é um cabeçalho declarado, é a resposta parcial funcionando:
    # sem 206, buscar no meio do vídeo baixaria o arquivo inteiro de novo.
    r = c_anonimo.get(
        f"/api/virtuais/pedidos/{token_grav}/video", headers={"Range": "bytes=0-99"}
    )
    check(
        "V6.9b pedido Range devolve 206 com o pedaço certo",
        r.status_code == 206 and len(r.get_data()) == 100,
        f"{r.status_code} {len(r.get_data())} bytes",
    )

    # Bloqueio por tentativas (FR-044b).
    c_forca = app.test_client()
    codigos = []
    for _ in range(7):
        rr = c_forca.post(
            f"/api/virtuais/pedidos/{token_grav}/verificar", json={"phone": "(11) 90000-0000"}
        )
        codigos.append(rr.status_code)
    check("V6.10 tentativas em massa acabam bloqueadas (429)", 429 in codigos, str(codigos))

    # Varredura de vazamento: o vídeo não pode ser alcançável por caminho estático.
    with app.app_context():
        eg = _MD2.query.get(entrega_grav_id)
        nome_arquivo = eg.video_path
        pasta_video = app.config["VIRTUAL_VIDEO_FOLDER"]
        pasta_uploads = app.config["UPLOAD_FOLDER"]
    check(
        "V6.11 vídeos ficam FORA da pasta servida em /uploads",
        not os.path.abspath(pasta_video).startswith(os.path.abspath(pasta_uploads)),
        f"{pasta_video} dentro de {pasta_uploads}",
    )
    r = c_anonimo.get(f"/uploads/{nome_arquivo}")
    check(
        "V6.12 o arquivo não é alcançável por /uploads",
        r.status_code in (302, 401, 403, 404),
        str(r.status_code),
    )

    # ── V9: financeiro segregado (FR-052–055, SC-014) ────────────────────────
    #
    # O cenário mede três indicadores de evento ANTES, efetiva 10 vendas virtuais e mede DEPOIS.
    # Os três precisam sair idênticos; só o DRE pode subir — exatamente a soma das vendas.
    #
    # A janela é um dia próprio (hoje+31) e não o mês corrente: o mês corrente do `manto_local`
    # tem eventos reais entrando e saindo, e um teste que depende do estado do dump falha por
    # motivo errado. Num dia dedicado, "não mudou" significa o que diz.
    login(superadmin_email)

    data_v9 = date.today() + timedelta(days=31)
    janela = f"period=custom&start={data_v9.isoformat()}&end={data_v9.isoformat()}"

    # Evento presencial de controle. Sem ele os indicadores seriam 0 antes e 0 depois — e
    # "0 == 0" passaria mesmo com todos os filtros quebrados. É este show que dá o que distorcer.
    with app.app_context():
        controle = CalendarEvent(
            google_event_id=f"verify205-controle-{RUN_ID}",
            title="Verify205 Controle Presencial",
            start_at=datetime.combine(data_v9, time(10, 0)),
            end_at=datetime.combine(data_v9, time(12, 0)),
            event_type="SHOW",
            source="platform",
            sale_value=Decimal("1000.00"),
            sale_date=data_v9,
            commission_rate=10,
        )
        db.session.add(controle)
        db.session.commit()
        controle_id = controle.id

    resp = client.post(
        f"/api/virtuais/campanhas/{campaign_id}/horarios",
        json={"date": data_v9.isoformat(), "start": "14:00", "end": "18:00"},
    )
    check("V9.0 gera horários do dia da medição", resp.status_code == 201,
          resp.get_data(as_text=True)[:200])

    def snapshot() -> dict:
        """Os números que a fase promete não mexer, lidos pela API — não pelo ORM.

        Ler pelo endpoint é o ponto: um agregador esquecido só aparece no payload que o gestor
        realmente vê.
        """
        dre = client.get(f"/api/financeiro/dashboard?{janela}").get_json()
        pipe = client.get(f"/api/vendas/pipeline?{janela}").get_json()
        with app.app_context():
            camp_rev = Decimal(campaign_metrics_revenue(campaign_id))
        return {
            "ticket_medio": dre["kpis"]["ticket_medio"],
            "receita_bruta": Decimal(str(dre["dre"]["total"]["receita_bruta"])),
            "comissoes": Decimal(str(dre["dre"]["total"]["comissoes"])),
            "fator_r_pct": dre["kpis"]["fator_r_pct"],
            "breakeven_pct": dre["kpis"]["breakeven_pct"],
            "a_receber": dre["paineis"]["a_receber_clientes"],
            "receita_por_tipo": dre["paineis"]["receita_por_tipo"],
            "loja_virtual": dre["paineis"]["loja_virtual"],
            "volume_funil": len(pipe["eventos"]),
            "eventos_funil": [e["event_id"] for e in pipe["eventos"]],
            "pipe_loja": pipe.get("loja_virtual"),
            "campanha_revenue": camp_rev,
        }

    def campaign_metrics_revenue(camp_id: int) -> str:
        from app.marketing.virtuais_ops import campaign_metrics

        return campaign_metrics(VirtualCampaign.query.get(camp_id))["revenue"]

    with app.app_context():
        from app.models import CommissionPayment as _CP

        comissoes_antes = _CP.query.count()

    antes = snapshot()

    # 10 vendas virtuais ao vivo, pelo caminho real: reserva pública → webhook → efetivação.
    # Só os horários do dia da medição: a campanha ainda tem sobras do dia usado nos cenários
    # anteriores, e uma venda caindo lá fora deixaria a janela sem o que medir.
    livres = (client.get(f"/api/virtuais/campanhas/{slug}/horarios").get_json() or {})["slots"]
    alvos = [s["id"] for s in livres if s["start_at"].startswith(data_v9.isoformat())][:10]
    check("V9.1 há 10 horários livres para a medição", len(alvos) == 10, f"{len(alvos)} livres")

    # O teto de 20 reservas/minuto é proteção real e o V2 já provou que ele funciona. Aqui ele só
    # atrapalharia: 10 vendas em sequência no mesmo test client vêm todas do mesmo IP.
    from app import limiter as _limiter

    _limiter.enabled = False

    soma_virtual = Decimal("0")
    for i, slot_id in enumerate(alvos):
        p = nova_reserva(f"(11) 96000-00{i:02d}", slot_id=slot_id)
        r = webhook(p["order_nsu"], f"txn-v9-{i}")
        if r.status_code != 200:
            raise AssertionError(f"venda V9 #{i} falhou: {r.get_data(as_text=True)[:200]}")
        soma_virtual += Decimal(str(p["total_value"]))

    with app.app_context():
        pagos_v9 = VirtualOrder.query.filter(
            VirtualOrder.campaign_id == campaign_id,
            VirtualOrder.status == "pago",
            VirtualOrder.event_id.isnot(None),
        ).count()
        eventos_v9 = CalendarEvent.query.filter(
            CalendarEvent.event_type == "VIRTUAL",
            CalendarEvent.sale_date == data_v9,
        ).all()
        sem_vendedor = all(e.seller_id is None for e in eventos_v9)
        comissoes_depois = _CP.query.count()

    check("V9.2 as 10 vendas viraram evento VIRTUAL no dia medido",
          len(eventos_v9) == 10, f"{len(eventos_v9)} eventos")
    check("V9.3 venda virtual não tem vendedor (por isso some de 'Minhas Vendas')",
          sem_vendedor)

    depois = snapshot()

    # Os três indicadores prometidos (SC-014).
    check("V9.4 volume do funil comercial não mudou",
          depois["volume_funil"] == antes["volume_funil"],
          f"{antes['volume_funil']} → {depois['volume_funil']}")
    check("V9.5 ticket médio não mudou",
          depois["ticket_medio"] == antes["ticket_medio"],
          f"{antes['ticket_medio']} → {depois['ticket_medio']}")
    check("V9.6 base de comissão do DRE não mudou",
          depois["comissoes"] == antes["comissoes"],
          f"{antes['comissoes']} → {depois['comissoes']}")
    check("V9.7 nenhuma linha de comissão nasceu das vendas virtuais",
          comissoes_depois == comissoes_antes,
          f"{comissoes_antes} → {comissoes_depois}")

    # O DRE, sim, tem que subir — e exatamente a soma.
    delta = depois["receita_bruta"] - antes["receita_bruta"]
    check("V9.8 DRE subiu exatamente a soma das vendas virtuais",
          delta == soma_virtual, f"delta {delta} ≠ soma {soma_virtual}")
    check("V9.9 'a receber de clientes' ignorou a loja (venda já paga)",
          depois["a_receber"] == antes["a_receber"],
          f"{antes['a_receber']} → {depois['a_receber']}")

    # Consultável por campanha e identificada por canal (FR-053).
    check("V9.10 painel da campanha subiu a mesma soma (bate com o DRE)",
          depois["campanha_revenue"] - antes["campanha_revenue"] == soma_virtual,
          f"{antes['campanha_revenue']} → {depois['campanha_revenue']}")
    check("V9.11 receita aparece identificada como 'Loja Virtual'",
          depois["receita_por_tipo"].get("Loja Virtual") == float(soma_virtual),
          str(depois["receita_por_tipo"]))
    check("V9.12 bloco consolidado do canal traz as 10 vendas",
          depois["loja_virtual"]["vendas"] == 10
          and Decimal(str(depois["loja_virtual"]["receita"])) == soma_virtual,
          str(depois["loja_virtual"]))
    check("V9.13 'VIRTUAL' não vira barra própria diluída nos tipos de evento",
          "VIRTUAL" not in depois["receita_por_tipo"],
          str(list(depois["receita_por_tipo"])))

    # Funil do gestor: as vendas ficam fora por padrão, mas o consolidado do canal aparece.
    virtual_ids = {e.id for e in eventos_v9}
    check("V9.14 funil do gestor não foi poluído pelas vendas virtuais",
          not (virtual_ids & set(depois["eventos_funil"])),
          str(virtual_ids & set(depois["eventos_funil"])))
    check("V9.15 gestor vê o consolidado da loja separado no pipeline",
          (depois["pipe_loja"] or {}).get("vendas") == 10, str(depois["pipe_loja"]))

    # FR-055: o opt-in explícito traz o canal de volta para o consolidado.
    optin = client.get(f"/api/vendas/pipeline?{janela}&incluir_loja_virtual=1").get_json()
    check("V9.16 opt-in explícito devolve as vendas ao funil consolidado",
          len(optin["eventos"]) == depois["volume_funil"] + 10
          and optin["incluir_loja_virtual"] is True,
          f"{len(optin['eventos'])} eventos")
    optin_dre = client.get(f"/api/financeiro/dashboard?{janela}&incluir_loja_virtual=1").get_json()
    check("V9.17 opt-in no DRE recalcula o ticket médio com a loja dentro",
          optin_dre["kpis"]["ticket_medio"] != depois["ticket_medio"]
          and optin_dre["paineis"]["incluir_loja_virtual"] is True,
          f"{depois['ticket_medio']} → {optin_dre['kpis']['ticket_medio']}")

    # Fator R e break-even leem a cascata inteira: a receita da loja é dinheiro que entrou, e
    # tirá-la daqui distorceria o enquadramento tributário — o oposto do que FR-053 pede.
    check("V9.18 Fator R e break-even enxergaram a receita da loja",
          depois["fator_r_pct"] != antes["fator_r_pct"]
          or depois["breakeven_pct"] != antes["breakeven_pct"],
          f"fator_r {antes['fator_r_pct']}→{depois['fator_r_pct']}, "
          f"breakeven {antes['breakeven_pct']}→{depois['breakeven_pct']}")

    # Comissões (módulo próprio): a loja não pode aparecer em nenhum recorte de vendedor.
    with app.app_context():
        from app.financeiro import comissoes_ops

        mes_v9 = data_v9.strftime("%Y-%m")
        entradas = comissoes_ops.get_month_entries(mes_v9)
        titulos_virtuais = [e.event_title for e in entradas if "VIRTUAL" in (e.event_title or "")]
    check("V9.19 módulo de comissões não enxerga venda virtual",
          not titulos_virtuais, str(titulos_virtuais[:3]))

    # ── V10: resiliência a falha de serviço externo (FR-056, FR-056a, FR-057) ─
    #
    # Os cenários anteriores fingem o Google e a operadora **respondendo**. Este finge os dois
    # **caindo** — que é o caminho onde os bugs moram, porque nunca é exercitado em teste feliz.
    #
    # As falhas são as de verdade: `HttpError` 503 da Calendar API e `SMTPResponseException` 500 do
    # servidor de e-mail. Levantar um `Exception` genérico provaria só que o `except` existe;
    # levantar o tipo real prova que ele pega o que vai acontecer em produção.
    from googleapiclient.errors import HttpError as _GoogleHttpError

    from app import email_service as _mail
    from app.marketing import virtuais_ops as _ops

    class _Resp503:
        status = 503
        reason = "Service Unavailable"

        def __getitem__(self, chave):
            return {"status": 503}[chave]

    google_fora = {"flag": True}

    def insert_event_instavel(*a, **kw):
        if google_fora["flag"]:
            raise _GoogleHttpError(
                resp=_Resp503(), content=b'{"error": {"message": "Backend Error"}}'
            )
        return fake_insert_event(*a, **kw)

    gcal_service.insert_event = insert_event_instavel
    # `_criar_evento_google` e `regerar_sala` importam de `app.calendar.service` dentro da função,
    # então trocar o atributo do módulo alcança as duas.

    mail_fora = {"flag": True}
    mail_send_original = _mail.mail.send

    def mail_send_instavel(msg):
        if mail_fora["flag"]:
            import smtplib

            raise smtplib.SMTPResponseException(500, b"Internal server error")
        return None

    _mail.mail.send = mail_send_instavel
    emails_habilitados_original = _mail._emails_enabled
    # Sem isso, `_send` sai antes de tocar no SMTP e o teste mediria o interruptor, não a falha.
    _mail._emails_enabled = lambda: True

    livres_v10 = (
        client.get(f"/api/virtuais/campanhas/{slug}/horarios").get_json() or {}
    )["slots"]
    alvo_v10 = next(
        (s["id"] for s in livres_v10 if s["start_at"].startswith(data_v9.isoformat())), None
    )
    check("V10.0 há horário livre para o cenário de falha", alvo_v10 is not None, str(alvo_v10))

    p10 = nova_reserva("(11) 97000-0001", slot_id=alvo_v10)
    r = webhook(p10["order_nsu"], "txn-v10-falha")
    check("V10.1 a venda se efetiva mesmo com Google e e-mail fora", r.status_code == 200,
          r.get_data(as_text=True)[:200])

    with app.app_context():
        o10 = VirtualOrder.query.filter_by(order_nsu=p10["order_nsu"]).first()
        order_id_v10 = o10.id
        estado = {
            "status": o10.status,
            "event_id": o10.event_id,
            "google_id": o10.event.google_event_id if o10.event else None,
            "meet_pending": bool(o10.meet_pending),
            "meet_attempts": o10.meet_attempts or 0,
        }
        from app.models import VirtualOrderNotification as _VN

        aviso = _VN.query.filter_by(order_id=o10.id, kind="compra_confirmada").first()
        aviso_estado = {
            "existe": aviso is not None,
            "sent_ok": bool(aviso.sent_ok) if aviso else None,
            "attempts": (aviso.attempts or 0) if aviso else 0,
            "erro": (aviso.error_message or "")[:60] if aviso else None,
        }

    check("V10.2 a venda virou evento apesar do 503 do Google",
          estado["status"] == "pago" and estado["event_id"] is not None, str(estado))
    check("V10.3 o evento ficou com id local, para a varredura reconhecer",
          (estado["google_id"] or "").startswith("virtual-local-"), str(estado["google_id"]))
    check("V10.4 a sala ficou pendente e a 1ª tentativa foi contada",
          estado["meet_pending"] and estado["meet_attempts"] == 1, str(estado))
    check("V10.5 o aviso registrou a falha do servidor de e-mail",
          aviso_estado["existe"] and aviso_estado["sent_ok"] is False
          and aviso_estado["attempts"] == 1,
          str(aviso_estado))
    check("V10.6 a falha do e-mail guarda o motivo, não só o fato",
          bool(aviso_estado["erro"]), str(aviso_estado["erro"]))

    # A falha precisa **aparecer**: silêncio é o único desfecho inaceitável (FR-056a).
    fila = client.get("/api/virtuais/producao").get_json() or {}
    linha = next(
        (d for d in fila.get("deliveries", []) if d["order_nsu"] == p10["order_nsu"]), None
    )
    check("V10.7 a Fila de Produção expõe o aviso que falhou",
          bool(linha) and len(linha.get("avisos_falhos") or []) == 1,
          str(linha.get("avisos_falhos") if linha else None))

    # O painel do evento é o outro lugar onde a equipe abre quando a família liga. Serializador
    # diferente do da fila — se só um dos dois expusesse a falha, ela sumiria justamente para quem
    # está com o telefone na mão.
    detalhe = client.get(f"/api/events/{estado['event_id']}").get_json() or {}
    bloco = detalhe.get("pedido_virtual") or {}
    check("V10.7b o painel do evento também expõe a falha do aviso",
          len(bloco.get("avisos_falhos") or []) == 1 and bloco.get("id") == order_id_v10,
          str({k: bloco.get(k) for k in ("id", "avisos_falhos", "meet_attempts")}))

    # Varredura: com o intervalo de 1 minuto ainda correndo, ela **não** pode retentar.
    with app.app_context():
        resultado = _ops.retentar_salas()
    check("V10.8 a varredura respeita o intervalo de 1 minuto entre tentativas",
          resultado["retidas"] == 1 and resultado["resolvidas"] == 0, str(resultado))

    # Envelhece a última tentativa para simular a passagem do minuto, sem prender o teste.
    def envelhecer_sala(order_id: int, minutos: int = 2) -> None:
        with app.app_context():
            o = VirtualOrder.query.get(order_id)
            o.meet_last_attempt_at = now_sp() - timedelta(minutes=minutos)
            db.session.commit()

    envelhecer_sala(order_id_v10)
    with app.app_context():
        resultado = _ops.retentar_salas()
        o10 = VirtualOrder.query.get(order_id_v10)
        attempts_2 = o10.meet_attempts or 0
    check("V10.9 passado o intervalo, a varredura tenta de novo e conta a tentativa",
          attempts_2 == 2 and resultado["retidas"] == 1, f"{attempts_2} tentativas, {resultado}")

    envelhecer_sala(order_id_v10)
    with app.app_context():
        _ops.retentar_salas()
        o10 = VirtualOrder.query.get(order_id_v10)
        attempts_3 = o10.meet_attempts or 0
    envelhecer_sala(order_id_v10)
    with app.app_context():
        resultado = _ops.retentar_salas()
        o10 = VirtualOrder.query.get(order_id_v10)
        attempts_4 = o10.meet_attempts or 0
    check("V10.10 esgotadas as 3 tentativas, a varredura para de tentar",
          attempts_3 == 3 and attempts_4 == 3 and resultado["esgotadas"] == 1,
          f"3ª={attempts_3}, 4ª={attempts_4}, {resultado}")

    fila = client.get("/api/virtuais/producao").get_json() or {}
    linha = next(
        (d for d in fila.get("deliveries", []) if d["order_nsu"] == p10["order_nsu"]), None
    )
    check("V10.11 a desistência aparece na fila como estado explícito",
          bool(linha) and linha.get("meet_retry_esgotado") is True,
          str(linha.get("meet_retry_esgotado") if linha else None))

    # ── O Google volta. A partir daqui tudo tem que se resolver sozinho. ──────
    google_fora["flag"] = False

    # A varredura desistiu (e está certa em ter desistido): quem reabre é a equipe, pelo botão.
    r = client.post(f"/api/virtuais/pedidos/{order_id_v10}/sala")
    check("V10.12 a ação manual cria a sala que faltava e reconcilia o id do Google",
          r.status_code == 200 and bool((r.get_json() or {}).get("meet_url")),
          r.get_data(as_text=True)[:200])

    with app.app_context():
        o10 = VirtualOrder.query.get(order_id_v10)
        final = {
            "meet_url": o10.meet_url,
            "meet_pending": bool(o10.meet_pending),
            "google_id": o10.event.google_event_id if o10.event else None,
        }
    check("V10.13 o evento deixou de ter id local — está de verdade no Google",
          not (final["google_id"] or "").startswith("virtual-local-")
          and not final["meet_pending"] and bool(final["meet_url"]),
          str(final))

    # ── O servidor de e-mail volta. ──────────────────────────────────────────
    mail_fora["flag"] = False

    r = client.post(f"/api/virtuais/pedidos/{order_id_v10}/avisos/compra_confirmada/reenviar")
    check("V10.14 o reenvio manual entrega o aviso que tinha falhado", r.status_code == 200,
          r.get_data(as_text=True)[:200])

    with app.app_context():
        aviso = _VN.query.filter_by(order_id=order_id_v10, kind="compra_confirmada").first()
        aviso_final = {"sent_ok": bool(aviso.sent_ok), "erro": aviso.error_message}
        # A trava continua valendo: não pode ter nascido um segundo registro do mesmo aviso.
        quantos = _VN.query.filter_by(order_id=order_id_v10, kind="compra_confirmada").count()
    check("V10.15 o aviso consta entregue e sem erro pendente",
          aviso_final["sent_ok"] and aviso_final["erro"] is None, str(aviso_final))
    check("V10.16 o reenvio NÃO criou um segundo registro (a trava continua de pé)",
          quantos == 1, f"{quantos} registros")

    r = client.post(f"/api/virtuais/pedidos/{order_id_v10}/avisos/compra_confirmada/reenviar")
    check("V10.17 reenviar um aviso já entregue é recusado (evita 2º e-mail à família)",
          r.status_code == 400, r.get_data(as_text=True)[:200])

    fila = client.get("/api/virtuais/producao").get_json() or {}
    linha = next(
        (d for d in fila.get("deliveries", []) if d["order_nsu"] == p10["order_nsu"]), None
    )
    check("V10.18 resolvido, o alerta some da fila",
          bool(linha) and not linha.get("avisos_falhos")
          and linha.get("meet_retry_esgotado") is False,
          str({"avisos": linha.get("avisos_falhos"), "sala": linha.get("meet_retry_esgotado")}
              if linha else None))

    # ── Alerta de prazo de vídeo: a terceira rotina que o FR-057 nomeia. ──────
    with app.app_context():
        from app.models import VirtualMediaDelivery as _MD3

        entrega10 = _MD3.query.filter_by(order_id=order_id_v10).first()
        entrega10.due_date = date.today() + timedelta(days=1)
        entrega10.deadline_alert_at = None
        entrega10.status = "pendente"
        db.session.commit()

        alertados = _ops.alertar_prazos_video()
        entrega10 = _MD3.query.filter_by(order_id=order_id_v10).first()
        alertado_em = entrega10.deadline_alert_at
        # Segunda passagem: o alerta não pode sair de novo, senão vira ruído que se aprende a ignorar.
        alertados_2 = _ops.alertar_prazos_video()

    check("V10.19 a varredura alerta o prazo de vídeo vencendo", alertados >= 1 and bool(alertado_em),
          f"{alertados} alertado(s)")
    check("V10.20 o alerta sai uma vez só por entrega", alertados_2 == 0, f"{alertados_2} repetido(s)")

    # As duas ações nascem no banner da Fila de Produção, então precisam do gate **da fila**. Com o
    # gate de campanhas, o CASTING veria os dois botões e levaria 403 nos dois — botão morto ao
    # clique, que é o que o Princípio V proíbe.
    import inspect as _inspect

    from app.api.virtuais_write import (
        api_virtuais_reenviar_aviso as _f_reenv,
    )
    from app.api.virtuais_write import (
        api_virtuais_regerar_sala as _f_sala,
    )

    fontes = _inspect.getsource(_f_sala) + _inspect.getsource(_f_reenv)
    check("V10.21b as ações do banner usam o gate da Fila de Produção, não o de campanhas",
          "require_producao_access()" in fontes
          and "require_virtuais_access()" not in fontes,
          "gate estreito deixaria o botão morto para CASTING")

    # ── Origem do conflito na devolução (FR-018b). ───────────────────────────
    #
    # Dois conflitos com culpas opostas: a reserva que simplesmente venceu, e o horário que o
    # sistema liberou **sem conseguir confirmar** se havia pagamento. Quem atende o telefone
    # precisa saber qual é — a segunda pode ser uma família que pagou em dia.
    p11 = nova_reserva("(11) 97000-0002")
    with app.app_context():
        o11 = VirtualOrder.query.filter_by(order_nsu=p11["order_nsu"]).first()
        o11.expired_unverified = True
        o11.locked_until = now_sp() - timedelta(minutes=1)
        o11.slot.status = "livre"
        o11.slot.order_id = None
        o11.slot_id = None
        db.session.commit()
        _ops._abrir_devolucao(o11)
        db.session.commit()

    devolucoes = (client.get("/api/virtuais/devolucoes?status=pendente").get_json() or {})
    dev = next(
        (d for d in devolucoes.get("refunds", [])
         if (d.get("order") or {}).get("order_nsu") == p11["order_nsu"]),
        None,
    )
    check("V10.22 a devolução distingue o conflito sem confirmação da operadora",
          bool(dev) and dev.get("sem_confirmacao") is True
          and "sem confirmação" in (dev.get("reason_label") or "").lower(),
          str({k: dev.get(k) for k in ("reason", "reason_label", "sem_confirmacao")} if dev else None))

    # ── O ciclo completo não pode deixar uma rotina derrubar as outras (FR-057b). ──
    expirar_original = _ops.expirar_reservas

    def expirar_explodindo(**kw):
        raise RuntimeError("teste: rotina de reservas caiu")

    _ops.expirar_reservas = expirar_explodindo
    with app.app_context():
        resumo = _ops.ciclo_de_varredura()
    _ops.expirar_reservas = expirar_original
    check("V10.21 uma rotina caída não impede as outras duas de rodar",
          "erro" in (resumo.get("reservas") or {})
          and "erro" not in (resumo.get("salas") or {})
          and not isinstance(resumo.get("prazos"), dict),
          str(resumo))

    _mail.mail.send = mail_send_original
    _mail._emails_enabled = emails_habilitados_original
    _limiter.enabled = True

    gcal_service.insert_event = gcal_insert_original
    ipc.consultar_pagamento = consultar_original
    ipc.criar_link_pagamento = original_criar_link

finally:
    # Limpeza: nada da verificação pode ficar no banco local.
    #
    # Ordem importa: os pedidos apontam para os horários, e apagar a campanha cascateia os
    # horários — então os pedidos saem primeiro, senão a FK `fk_virtual_orders_slot_id` bloqueia.
    with app.app_context():
        if campaign_id:
            limpar_campanha(campaign_id)
        # Evento presencial de controle do V9 — fixture do teste, não pode ficar no financeiro.
        controle_restante = CalendarEvent.query.filter_by(
            title="Verify205 Controle Presencial"
        ).all()
        for ev in controle_restante:
            db.session.delete(ev)
        if controle_restante:
            db.session.commit()
        personagem = CatalogCharacter.query.get(character_id)
        if personagem:
            db.session.delete(personagem)
            db.session.commit()
        # Vídeos do teste não podem ficar ocupando disco.
        pasta = app.config.get("VIRTUAL_VIDEO_FOLDER")
        if pasta and os.path.isdir(pasta):
            for nome in os.listdir(pasta):
                if nome.startswith("205-"):
                    try:
                        os.remove(os.path.join(pasta, nome))
                    except OSError:
                        pass

falhas = [r for r in results if not r[1]]
print(f"\n{len(results) - len(falhas)}/{len(results)} PASS")
if falhas:
    print("\nFALHAS:")
    for nome, _, detalhe in falhas:
        print(f"  - {nome}: {detalhe}")
sys.exit(1 if falhas else 0)
