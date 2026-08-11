"""Confirmação de convite: quem falta e o lembrete automático (feature 231).

Mais da metade das escalações futuras está sem confirmação — o convite sai e a pessoa não
responde no portal. Isso custa nos dois lados: o casting não sabe com quem pode contar, e o
artista sem resposta é quem descobre tarde que era para estar lá.

Este módulo é a fonte única de **"quem ainda não confirmou"**: o painel do casting na home lê
daqui, e a rotina de e-mail também. Se as duas listas divergissem, o painel cobraria alguém que
o robô já cobrou (ou o contrário).

**A regra do e-mail, e por que ela é assim (o pedido foi explícito: nada de spam):**

1. **Só quem já recebeu o convite** (`invite_status="pending"`). Cargo com convite nunca enviado
   (`NULL`) NÃO recebe e-mail automático: o primeiro contato é o convite, e mandá-lo é decisão
   de quem escala — a pessoa pode nem estar fechada. Esses aparecem no painel para o casting
   resolver na mão.
2. **Só na semana do evento** — entre 24h e 7 dias antes. Antes disso a cobrança é ruído; depois,
   já não é e-mail que resolve, é telefone.
3. **No máximo 2 lembretes por convite**, com pelo menos 3 dias entre eles.
4. **No máximo 1 e-mail por pessoa por dia**: quem tem três eventos sem responder recebe **um**
   e-mail listando os três, não três e-mails.
5. **Só em horário decente** (9h–20h de Brasília) — a rodada simplesmente não acontece fora disso.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import or_, text

from app import db
from app.models import CalendarEvent, EventRole, SiteSetting

#: Só entra na cobrança automática o convite que já foi enviado e não teve resposta.
STATUS_COBRAVEL = "pending"

#: Janela de cobrança, contada a partir do início do evento.
ANTECEDENCIA_MAXIMA = timedelta(days=7)
ANTECEDENCIA_MINIMA = timedelta(hours=24)

#: Teto de lembretes por convite e intervalo mínimo entre eles.
MAX_LEMBRETES = 2
INTERVALO_MINIMO = timedelta(days=3)

#: Faixa de horário (Brasília) em que a rodada pode disparar e-mail.
HORA_INICIO = 9
HORA_FIM = 20

#: A rodada é diária; o intervalo do lock é menor que 24h para tolerar variação de horário de
#: deploy sem pular um dia inteiro.
INTERVALO_RODADA = timedelta(hours=20)


def _sem_confirmacao_base():
    """Consulta-base: cargo com talento, em evento futuro que ainda vai acontecer.

    Reaproveita os filtros do painel de casting da home (`dashboard_service._base_filters`), em
    vez de reescrevê-los: fora ensaio, fora evento cancelado, fora cargo dispensado e fora a vaga
    sentinela de presença — nenhum dos quatro gera cobrança, e divergir do painel faria a lista
    do e-mail contradizer a lista da tela.

    `invite_status` NULL precisa de `or_` explícito: em SQL, `NULL != 'accepted'` é NULL, não
    verdadeiro, e o cargo sem convite sumiria justamente da lista feita para encontrá-lo.
    """
    from app.api.dashboard_service import _base_filters, dashboard_cutoff
    from app.talent_portal.portal_ops import now_sp

    # Corte próprio, e NÃO o `dashboard_cutoff()` que os outros painéis usam: aquele vale
    # `release_date` (01/06/2026 hoje), e com ele a lista viria com 59 eventos que já
    # aconteceram — ninguém cobra confirmação de evento de junho. Aqui é da meia-noite de hoje
    # para a frente, que mantém o evento de HOJE ainda não confirmado (o mais urgente que existe
    # nesta tela) e descarta o passado. `dashboard_cutoff` continua sendo a fonte dos demais
    # filtros, para não divergir do resto da home no que é comum.
    agora = now_sp()
    f = _base_filters(dashboard_cutoff())
    f["future_events"] = CalendarEvent.start_at >= agora.replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    return (
        EventRole.query.filter(
            EventRole.talent_id.isnot(None),
            f["not_dismissed"],
            f["not_presence"],
            or_(
                EventRole.invite_status.is_(None),
                EventRole.invite_status.notin_(["accepted", "rejected"]),
            ),
        )
        .join(CalendarEvent)
        .filter(f["not_cancelled"], f["exclude_ensaios"], f["future_events"])
    )


def escalacoes_sem_confirmacao() -> list[EventRole]:
    """Todo cargo futuro em que a pessoa está escalada e ainda não confirmou.

    Inclui **os dois** casos, porque o casting precisa agir de forma diferente em cada um:
    convite enviado sem resposta (cobrar) e convite nunca enviado (mandar).

    Returns:
        Cargos ordenados pelo evento mais próximo — a ordem em que a cobrança importa.
    """
    return _sem_confirmacao_base().order_by(CalendarEvent.start_at.asc()).all()


def _elegiveis_para_lembrete(agora: datetime) -> list[EventRole]:
    """Convites que a regra autoriza cobrar por e-mail nesta rodada."""
    limite_max = agora + ANTECEDENCIA_MAXIMA
    limite_min = agora + ANTECEDENCIA_MINIMA
    corte_intervalo = agora - INTERVALO_MINIMO

    return (
        _sem_confirmacao_base()
        .filter(
            EventRole.invite_status == STATUS_COBRAVEL,
            EventRole.invite_reminder_count < MAX_LEMBRETES,
            or_(
                EventRole.invite_reminder_at.is_(None),
                EventRole.invite_reminder_at <= corte_intervalo,
            ),
            CalendarEvent.start_at <= limite_max,
            CalendarEvent.start_at >= limite_min,
        )
        .order_by(CalendarEvent.start_at.asc())
        .all()
    )


def _claim_rodada(agora: datetime) -> bool:
    """Reivindica a rodada do dia de forma atômica (só um worker ganha).

    Mesmo `UPDATE` condicional de `_claim_auto_sync` (`app/calendar/sync.py`): sem isso os 3
    workers do gunicorn mandariam o mesmo lembrete três vezes.
    """
    limite = agora - INTERVALO_RODADA
    resultado = db.session.execute(
        text(
            "UPDATE site_settings SET invite_reminder_run_at = :agora "
            "WHERE id = 1 AND (invite_reminder_run_at IS NULL OR invite_reminder_run_at < :limite)"
        ),
        {"agora": agora, "limite": limite},
    )
    db.session.commit()
    return resultado.rowcount == 1


def rodar_lembretes(forcar: bool = False) -> dict[str, Any]:
    """Roda a cobrança do dia: agrupa por pessoa, manda um e-mail e marca os cargos.

    Args:
        forcar: Pula a trava de horário e a de execução única — só para teste manual.

    Returns:
        `{"enviados": n_de_emails, "cargos": n_de_cargos, "pulados": motivo->contagem}`.
    """
    from app.email_service import send_invite_reminder_email
    from app.talent_portal.portal_ops import now_sp

    agora = now_sp()
    pulados: dict[str, int] = {}

    if not forcar and not (HORA_INICIO <= agora.hour < HORA_FIM):
        return {"enviados": 0, "cargos": 0, "pulados": {"fora_do_horario": 1}}

    if not forcar and not _claim_rodada(agora):
        return {"enviados": 0, "cargos": 0, "pulados": {"rodada_ja_feita": 1}}

    elegiveis = _elegiveis_para_lembrete(agora)

    # Agrupa por pessoa: um e-mail com todos os eventos dela, nunca um por evento.
    por_talento: dict[int, list[EventRole]] = {}
    for cargo in elegiveis:
        if not (cargo.talent and cargo.talent.email_contact):
            pulados["sem_email"] = pulados.get("sem_email", 0) + 1
            continue
        por_talento.setdefault(cargo.talent_id, []).append(cargo)

    enviados = 0
    cargos_marcados = 0
    for cargos in por_talento.values():
        talento = cargos[0].talent
        if not send_invite_reminder_email(talento, cargos):
            pulados["falha_no_envio"] = pulados.get("falha_no_envio", 0) + 1
            continue
        enviados += 1
        # Marca só depois do envio dar certo: e-mail que não saiu não gastou a cota de lembretes.
        for cargo in cargos:
            cargo.invite_reminder_at = agora
            cargo.invite_reminder_count = (cargo.invite_reminder_count or 0) + 1
            cargos_marcados += 1

    if enviados:
        db.session.commit()

    return {"enviados": enviados, "cargos": cargos_marcados, "pulados": pulados}


def ultima_rodada() -> datetime | None:
    """Quando a última rodada de lembrete aconteceu — o painel mostra isso ao casting."""
    settings = SiteSetting.query.get(1)
    return settings.invite_reminder_run_at if settings else None
