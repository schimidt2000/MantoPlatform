"""Emissão, leitura e retenção das notificações internas (feature 272).

Uma notificação é um **registro derivado de um fato que o banco já gravou**, endereçado a pessoas
concretas (resolvidas por papel no momento da emissão) com texto pronto em pt-BR e um caminho da
SPA interna para agir. Ela nasce no mesmo ponto do código que grava o fato e, quando o fato ainda
não foi comitado, na **mesma transação**.

Módulo puro no sentido da constituição: importa só `db`, `models`, `constants`, `money` e
`sqlalchemy` — nunca `flask.request` nem `current_user`. O `PresoAoEvento` da 303 entra só sob
`TYPE_CHECKING`: `sumico_ops` importa este módulo, e o import de verdade fecharia um ciclo. Não é só regra: o produtor da recusa de convite roda sob
sessão de **talento** (portal), onde não existe `current_user` interno, e é por isso que `audit()`
(que infere o ator da sessão) não serviu de molde.

Abrir este arquivo responde "quais fatos avisam quem": o catálogo de `kind` e os destinatários por
papel ficam no topo; os textos vivem nos produtores `notificar_*`, um por fato. Produtor novo (ondas
2-4 do funil) = constante no catálogo + entrada em `DESTINATARIOS_POR_KIND` + `notificar_x()` + uma
chamada no ponto do fato — sem tocar em tabela, endpoint ou UI.

Regimes de transação, explícitos por produtor:

- **A — atômico** (fato ainda não comitado: avaliação, recusa): `add(fato); flush();
  notificar_x(fato); commit()`. Nunca aviso sem fato.
- **B — best-effort depois do fato** (resposta de formulário, cuja gravação comita antes):
  `notificar_x(fato); commit()` em transação própria curta, `try/except → rollback → log`.
  Resposta sem notificação é aceitável; notificação sem resposta é impossível.

Em rotina de fundo (ondas 3-4), quem comita é a **rodada**, depois do claim atômico.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Iterable
from datetime import datetime, timedelta
from typing import TYPE_CHECKING

from sqlalchemy import and_, delete, or_, select, update
from sqlalchemy.exc import IntegrityError

from app import db
from app.constants import RoleName, now_sp
from app.models import ClientFeedback, EventRole, FormResponse, Notification, Role, User
from app.money import format_brl

if TYPE_CHECKING:
    from app.calendar.sumico_ops import PresoAoEvento
    from app.models import CalendarEvent

logger = logging.getLogger(__name__)

# ── Catálogo ───────────────────────────────────────────────────────────────────────────────────

KIND_FORM_RESPONSE = "form_response.nova"
KIND_AVALIACAO = "avaliacao.recebida"
KIND_CONVITE_RECUSADO = "convite.recusado"
KIND_RECADO_NFC = "recado_nfc.novo"
KIND_EVENTO_SUMIU_GOOGLE = "evento.sumiu_google"
KIND_EVENTO_CANCELADO = "evento.cancelado"
KIND_EVENTO_CANCELADO_ESCALA = "evento.cancelado_escala"
KIND_EVENTO_PEDIDO_CANCELAMENTO = "evento.pedido_cancelamento"
KIND_EVENTO_PEDIDO_DECIDIDO = "evento.pedido_decidido"

#: Quem é avisado de cada fato. Nenhum `kind` endereça "todo mundo": a decisão 5 da 266 vale para a
#: caixa — aviso que vira ruído deixa de avisar.
DESTINATARIOS_POR_KIND: dict[str, tuple[str, ...]] = {
    KIND_FORM_RESPONSE: (RoleName.COMERCIAL, RoleName.SUPERADMIN),
    KIND_AVALIACAO: (RoleName.COMERCIAL, RoleName.SUPERADMIN),
    KIND_CONVITE_RECUSADO: (RoleName.CASTING, RoleName.SUPERADMIN),
    # Os mesmos papéis que podem LER o recado no ERP. Avisar quem não pode abrir o link seria
    # produzir ruído com um beco sem saída no fim.
    KIND_RECADO_NFC: (RoleName.ARTISTA_3D, RoleName.SUPERADMIN),
    # Feature 303: quem vende (e precisa saber que a data saiu do calendário) e quem decide.
    KIND_EVENTO_SUMIU_GOOGLE: (RoleName.COMERCIAL, RoleName.SUPERADMIN),
    # Feature 306 (FR-067): o ensaio cancelado avisa quem ensaia; a escala, quem escala — sem o
    # Superadmin, que é quem cancela.
    KIND_EVENTO_CANCELADO: (RoleName.ENSAIO,),
    KIND_EVENTO_CANCELADO_ESCALA: (RoleName.CASTING,),
    # Feature 315: o pedido de cancelamento vai a quem decide; a resposta, só a quem pediu — sempre
    # pela lista explícita (`destinatarios=[autor]`), nunca por papel.
    KIND_EVENTO_PEDIDO_CANCELAMENTO: (RoleName.SUPERADMIN,),
    KIND_EVENTO_PEDIDO_DECIDIDO: (),
}

SEVERIDADES = ("info", "urgent")

#: Retenção: lida há mais de 30 dias e não lida há mais de 180 dias saem. Um aviso que ninguém
#: abriu em seis meses não é aviso.
RETENCAO_LIDA_DIAS = 30
RETENCAO_NAO_LIDA_DIAS = 180

#: Paginação por keyset (`id < antes_de`), nunca offset — a lista muda enquanto se pagina.
LIMITE_PADRAO = 30
LIMITE_MAXIMO = 100

#: Recusa de convite para evento nesta janela é `urgent` (mesma janela dos lembretes de convite).
ANTECEDENCIA_URGENTE_DIAS = 7

_LOTE_LIMPEZA = 1000


# ── Emissão ────────────────────────────────────────────────────────────────────────────────────

def resolver_destinatarios(papeis: Iterable[str]) -> list[User]:
    """Usuários ativos e com acesso que têm algum dos papéis.

    É o filtro que `_avisar_comercial` (266) usava, promovido a função única. `.distinct()` porque
    quem tem COMERCIAL+SUPERADMIN viria duas vezes pelo join; `has_access=False` é a pessoa "só
    pagamento" sem login — não tem como ler.
    """
    return (
        User.query.join(User.roles)
        .filter(
            Role.name.in_(list(papeis)),
            User.is_active.is_(True),
            User.has_access.is_(True),
        )
        .distinct()
        .all()
    )


def emitir(
    kind: str,
    *,
    title: str,
    dedupe_key: str,
    body: str | None = None,
    link_path: str | None = None,
    entidade: tuple[str, int] | None = None,
    severity: str = "info",
    destinatarios: list[User] | None = None,
) -> int:
    """Grava uma notificação por destinatário. **Não comita** — quem chama comita.

    Args:
        kind: valor do catálogo (`DESTINATARIOS_POR_KIND`).
        title: texto pronto (≤ 200 caracteres; o excedente é cortado).
        dedupe_key: identidade do aviso, `<kind>:<entity_id>[:<marcador>]`. É a `UNIQUE` do banco
            junto com `user_id` — dois workers emitindo o mesmo fato não produzem duas linhas.
        body: texto secundário (≤ 500).
        link_path: caminho **relativo** da SPA interna (`/formularios?resposta=12`).
        entidade: `(entity_type, entity_id)` — referência fraca, sem FK.
        severity: `"info"` ou `"urgent"`.
        destinatarios: lista explícita; `None` resolve por papel a partir do catálogo.

    Returns:
        Quantas linhas foram gravadas (0 quando todos os destinatários já tinham o aviso).

    Raises:
        ValueError: `kind` ou `severity` fora do catálogo — erro de programação, não de dado.

    Dedupe em duas camadas: um SELECT do que já existe (caminho normal, nunca estoura) e um
    SAVEPOINT em volta de cada inserção — se dois workers passarem pelo SELECT ao mesmo tempo e um
    bater na UNIQUE, só o savepoint volta e a transação do chamador **sobrevive**. Sem isso, uma
    corrida no aviso desfaria a recusa do convite: "o aviso derrubando o fato" é o que a decisão 7
    da 266 proibiu.
    """
    if kind not in DESTINATARIOS_POR_KIND:
        raise ValueError(f"kind de notificação fora do catálogo: {kind!r}")
    if severity not in SEVERIDADES:
        raise ValueError(f"severity inválida: {severity!r}")

    users = destinatarios if destinatarios is not None else resolver_destinatarios(
        DESTINATARIOS_POR_KIND[kind]
    )
    ids = sorted({u.id for u in users})
    if not ids:
        return 0

    ja_tem = {
        uid
        for (uid,) in db.session.execute(
            select(Notification.user_id).where(
                Notification.user_id.in_(ids), Notification.dedupe_key == dedupe_key
            )
        )
    }
    entity_type, entity_id = entidade if entidade else (None, None)
    agora = now_sp()
    gravadas = 0
    for uid in ids:
        if uid in ja_tem:
            continue
        try:
            with db.session.begin_nested():
                db.session.add(
                    Notification(
                        user_id=uid,
                        kind=kind,
                        severity=severity,
                        title=title[:200],
                        body=body[:500] if body else None,
                        link_path=link_path,
                        entity_type=entity_type,
                        entity_id=entity_id,
                        dedupe_key=dedupe_key[:120],
                        created_at=agora,
                    )
                )
                db.session.flush()
        except IntegrityError:
            # Outro worker gravou primeiro — o estado desejado já existe.
            logger.info("[notificacoes] %s já emitida para usuário %s", dedupe_key, uid)
            continue
        gravadas += 1
    return gravadas


# ── Produtores da v1 (o texto vive junto do catálogo) ──────────────────────────────────────────

def _garante_id(obj: object) -> None:
    if getattr(obj, "id", None) is None:
        db.session.flush()


def notificar_resposta_formulario(response: FormResponse) -> int:
    """Resposta de formulário público chegou → COMERCIAL/SUPERADMIN (substitui o e-mail da 266).

    Regime B: chamada depois de a resposta já estar comitada; quem chama comita em transação curta.
    """
    # Feature 298: formulário que já chega ligado a um evento (vínculo automático no envio) tem
    # destino — o aviso nasceria só para ser apagado. A Home é o lembrete do que falta.
    if response.event_id is not None:
        return 0
    _garante_id(response)
    data = response.event_date.strftime("%d/%m/%Y") if response.event_date else "data não informada"
    corpo = f"{response.form_type_label} · festa em {data}"
    if response.client_link_source == "auto_phone" and response.client is not None:
        corpo += f" · cliente identificada: {response.client.name}"
    return emitir(
        KIND_FORM_RESPONSE,
        title=f"Nova resposta: {response.contact_name or 'sem nome'}",
        body=corpo,
        link_path=f"/formularios?resposta={response.id}",
        entidade=("form_response", response.id),
        dedupe_key=f"{KIND_FORM_RESPONSE}:{response.id}",
    )


def notificar_avaliacao_recebida(feedback: ClientFeedback, event) -> int:
    """Avaliação da cliente → COMERCIAL/SUPERADMIN; nota ≤ 2 é `urgent`. Regime A."""
    _garante_id(feedback)
    try:
        tags = json.loads(feedback.tags) if feedback.tags else []
    except ValueError:
        tags = []
    partes = [feedback.client_name or "cliente"]
    if tags:
        partes.append(", ".join(str(t) for t in tags))
    if feedback.comment:
        partes.append(feedback.comment[:120])
    return emitir(
        KIND_AVALIACAO,
        title=f"{feedback.score}★ — {event.title}",
        body=" · ".join(partes),
        link_path=f"/events/{event.id}?aba=historico",
        entidade=("client_feedback", feedback.id),
        dedupe_key=f"{KIND_AVALIACAO}:{feedback.id}",
        severity="urgent" if feedback.score <= 2 else "info",
    )


def notificar_convite_recusado(role: EventRole) -> int:
    """Talento recusou o convite no portal → CASTING/SUPERADMIN. Regime A.

    Chave por dia (`:AAAAMMDD`): recusar, aceitar e recusar de novo no mesmo dia não re-avisa; uma
    recusa em outro dia é fato novo. `urgent` quando o evento é em ≤ 7 dias. É o único produtor
    sem `current_user` — a prova de que a emissão não depende de request.
    """
    _garante_id(role)
    event = role.event
    talent = role.talent
    nome = (talent.artistic_name or talent.full_name) if talent else "Talento"
    agora = now_sp()
    quando = f" · {event.start_at:%d/%m %H:%M}" if event and event.start_at else ""
    urgente = bool(
        event and event.start_at and event.start_at - agora <= timedelta(days=ANTECEDENCIA_URGENTE_DIAS)
    )
    return emitir(
        KIND_CONVITE_RECUSADO,
        title=f"{nome} recusou {role.character_name or 'o convite'}",
        body=f"{event.title}{quando}" if event else None,
        link_path=f"/events/{role.event_id}?aba=producao",
        entidade=("event_role", role.id),
        dedupe_key=f"{KIND_CONVITE_RECUSADO}:{role.id}:{agora:%Y%m%d}",
        severity="urgent" if urgente else "info",
    )


def notificar_evento_cancelado(event: CalendarEvent, ensaios: list[str], *, dedupe_key: str) -> int:
    """Feature 306 (FR-067): o evento foi cancelado e os ensaios dele caíram → equipe de Ensaio.

    Um por pessoa por ato (a chave vem do ato, pelo evento da URL: dois atos no mesmo grupo dão dois
    avisos). Só é chamado quando algum dia cancelado tinha ensaio. Informativo.
    """
    _garante_id(event)
    return emitir(
        KIND_EVENTO_CANCELADO,
        title=f"Evento cancelado: {event.title}",
        body=("Ensaios cancelados: " + "; ".join(ensaios)) if ensaios else None,
        link_path=f"/events/{event.id}",
        entidade=("calendar_event", event.id),
        dedupe_key=dedupe_key,
        severity="info",
    )


def notificar_cancelamento_na_escala(dia: CalendarEvent, escalados: int, *, dedupe_key: str) -> int:
    """Feature 306 (FR-067): um dia com elenco escalado foi cancelado → Casting, para tirar a escala.

    Um por dia cancelado com escalados; `urgent` quando o dia é em até 7 dias, como a recusa de
    convite. A tela leva à aba Produção do dia.
    """
    _garante_id(dia)
    agora = now_sp()
    urgente = bool(dia.start_at and dia.start_at - agora <= timedelta(days=ANTECEDENCIA_URGENTE_DIAS))
    quem = "o artista" if escalados == 1 else f"os {escalados} artistas"
    quando = f" · {dia.start_at:%d/%m %H:%M}" if dia.start_at else ""
    return emitir(
        KIND_EVENTO_CANCELADO_ESCALA,
        title=f"Evento cancelado: tire {quem} da escala e avise cada um pelo WhatsApp",
        body=f"{dia.title}{quando}",
        link_path=f"/events/{dia.id}?aba=producao",
        entidade=("calendar_event", dia.id),
        dedupe_key=dedupe_key,
        severity="urgent" if urgente else "info",
    )


def notificar_recado_nfc(recado) -> int:
    """Cliente escreveu um recado na página da luminária → ARTISTA_3D/SUPERADMIN (feature 297).

    Regime B (transação curta, melhor-esforço): quem chama comita o recado ANTES e trata a falha
    daqui sem desfazer nada. Um aviso que não sai é um aborrecimento; um recado que se perde por
    causa do aviso seria uma promessa quebrada com quem escreveu.

    O corpo traz o começo do texto porque o valor está justamente no que a pessoa disse — uma
    notificação que só diz "há um recado novo" obriga a abrir a tela para descobrir se importa.
    """
    _garante_id(recado)
    tag = recado.tag
    autor = recado.author_name or "Alguém"
    numero = f"nº {tag.sequence}" if tag else "tag"
    return emitir(
        KIND_RECADO_NFC,
        title=f"{autor} deixou um recado na luminária {numero}",
        body=recado.message[:200],
        link_path="/3d/tags?aba=videos",
        entidade=("nfc_tag_message", recado.id),
        dedupe_key=f"{KIND_RECADO_NFC}:{recado.id}",
    )


def _escalados_no_aviso(n: int) -> str:
    if n == 0:
        return "ninguém escalado"
    return "1 pessoa escalada" if n == 1 else f"{n} pessoas escaladas"


def notificar_evento_sumiu_google(
    event: CalendarEvent, *, marcado_em: datetime, preso: PresoAoEvento
) -> int:
    """Evento com dinheiro sumiu do Google Agenda e foi mantido → COMERCIAL/SUPERADMIN (303).

    Regime A, sem commit: roda dentro da transação que grava a marca — marca sem aviso não existe.
    A chave leva o carimbo da marca: um aviso por sumiço, e aviso novo se o evento voltar e sumir
    de novo. O corpo diz o que está preso para o evento mantido só por contrato ou comprovante sem
    valor não parecer alarme falso.
    """
    partes = [f"{event.start_at:%d/%m/%Y}" if event.start_at else "sem data"]
    if preso.venda > 0:
        partes.append(f"venda {format_brl(preso.venda, prefix=True)}")
    else:
        partes.append("parte de grupo comercial" if preso.grupo else "sem venda")
    recebido = f"recebido {format_brl(preso.recebido, prefix=True)}"
    if preso.n_comprovantes and not preso.recebido:
        rotulo = "comprovante" if preso.n_comprovantes == 1 else "comprovantes"
        recebido += f" ({preso.n_comprovantes} {rotulo} sem valor)"
    partes.append(recebido)
    partes.append(_escalados_no_aviso(preso.n_escalados))
    if preso.tem_contrato:
        partes.append("contrato anexado")
    return emitir(
        KIND_EVENTO_SUMIU_GOOGLE,
        title=f"Sumiu do Google Agenda — {event.title}",
        body=" · ".join(partes),
        link_path=f"/events/{event.id}",
        entidade=("calendar_event", event.id),
        dedupe_key=f"{KIND_EVENTO_SUMIU_GOOGLE}:{event.id}:{marcado_em:%Y%m%d%H%M%S%f}",
        severity="urgent",
    )


def notificar_pedido_cancelamento(
    event: CalendarEvent,
    *,
    carimbo: datetime,
    preso: PresoAoEvento,
    n_escalados: int,
    alcance: str,
    autor: str,
    motivo: str,
) -> int:
    """O Comercial pediu o cancelamento → SUPERADMIN (feature 315). Regime A, sem commit.

    Roda na transação que grava o pedido: pedido sem aviso não existe. A chave leva o carimbo — um
    aviso por pedido, e aviso novo se o pedido for recusado e feito de novo. `urgent` quando o evento
    é em ≤ 7 dias ou já passou. O corpo diz o que está em jogo para o Superadmin decidir sem abrir o
    evento; nome e PIX de quem recebe a devolução nunca entram (o sino não tem corte por papel).
    """
    agora = now_sp()
    urgente = bool(event.start_at and event.start_at - agora <= timedelta(days=ANTECEDENCIA_URGENTE_DIAS))
    partes = [f"{event.start_at:%d/%m/%Y}" if event.start_at else "sem data"]
    partes.append(f"venda {format_brl(preso.venda, prefix=True)}" if preso.venda > 0 else "sem venda")
    partes.append(f"recebido {format_brl(preso.recebido, prefix=True)}")
    partes.append(_escalados_no_aviso(n_escalados))
    partes.append(alcance)
    partes.append(f"pedido por {autor}: {motivo}")
    return emitir(
        KIND_EVENTO_PEDIDO_CANCELAMENTO,
        title=f"Cancelamento pedido — {event.title}",
        body=" · ".join(partes),
        link_path=f"/events/{event.id}",
        entidade=("calendar_event", event.id),
        dedupe_key=f"{KIND_EVENTO_PEDIDO_CANCELAMENTO}:{event.id}:{carimbo:%Y%m%d%H%M%S%f}",
        severity="urgent" if urgente else "info",
    )


def notificar_pedido_decidido(
    autor: User | None,
    *,
    quem_decidiu_id: int | None,
    decisao: str,
    carimbo: datetime,
    event_id: int,
    title: str,
    body: str | None = None,
    com_link: bool = True,
) -> int:
    """O Superadmin fechou o pedido → só quem pediu (feature 315). Sem commit.

    Uma resposta por pedido: a chave leva a decisão e o carimbo do pedido, e só a transação que
    ganhou o claim (ou o fecho do cancelamento) chega aqui. Não responde a quem perdeu o acesso nem
    a quem decidiu o próprio pedido — `emitir` não filtra a lista explícita, então o filtro é daqui.
    Na exclusão o evento não existe mais: sem entidade e sem link (`com_link=False`).
    """
    if autor is None or not (autor.is_active and autor.has_access) or autor.id == quem_decidiu_id:
        return 0
    return emitir(
        KIND_EVENTO_PEDIDO_DECIDIDO,
        title=title,
        body=body,
        link_path=f"/events/{event_id}" if com_link else None,
        entidade=("calendar_event", event_id) if com_link else None,
        dedupe_key=f"{KIND_EVENTO_PEDIDO_DECIDIDO}:{event_id}:{decisao}:{carimbo:%Y%m%d%H%M%S%f}",
        destinatarios=[autor],
    )


# ── A caixa do usuário ─────────────────────────────────────────────────────────────────────────

def contar_nao_lidas(user_id: int) -> int:
    """`COUNT` das não lidas — o endpoint do polling. **Nunca** ganhar join: roda a cada 60 s em
    toda aba aberta e precisa custar O(não lidas do usuário) pelo índice parcial."""
    return db.session.scalar(
        select(db.func.count(Notification.id)).where(
            Notification.user_id == user_id, Notification.read_at.is_(None)
        )
    ) or 0


def listar(
    user_id: int,
    *,
    antes_de: int | None = None,
    limite: int = LIMITE_PADRAO,
    somente_nao_lidas: bool = False,
) -> list[Notification]:
    """Página da caixa por keyset (`id < antes_de`), mais recente primeiro."""
    limite = max(1, min(int(limite or LIMITE_PADRAO), LIMITE_MAXIMO))
    q = Notification.query.filter(Notification.user_id == user_id)
    if antes_de is not None:
        q = q.filter(Notification.id < antes_de)
    if somente_nao_lidas:
        q = q.filter(Notification.read_at.is_(None))
    return q.order_by(Notification.id.desc()).limit(limite).all()


def marcar_lida(user_id: int, notification_id: int) -> Notification | None:
    """Marca uma notificação do usuário como lida (idempotente). `None` quando não é dele."""
    n = Notification.query.filter_by(id=notification_id, user_id=user_id).first()
    if n is None:
        return None
    if n.read_at is None:
        n.read_at = now_sp()
    return n


def marcar_lidas_ate(user_id: int, ate_id: int) -> int:
    """Marca lidas as não lidas do usuário com `id <= ate_id` — o teto evita engolir o aviso que
    chegou depois de a lista ser desenhada e ninguém viu."""
    resultado = db.session.execute(
        update(Notification)
        .where(
            Notification.user_id == user_id,
            Notification.read_at.is_(None),
            Notification.id <= ate_id,
        )
        .values(read_at=now_sp())
    )
    return resultado.rowcount or 0


def marcar_lidas_por_objeto(user_id: int, entity_type: str, entity_id: int) -> int:
    """Abrir o objeto por qualquer caminho marca lidas as notificações dele para este usuário."""
    resultado = db.session.execute(
        update(Notification)
        .where(
            Notification.user_id == user_id,
            Notification.read_at.is_(None),
            Notification.entity_type == entity_type,
            Notification.entity_id == entity_id,
        )
        .values(read_at=now_sp())
    )
    return resultado.rowcount or 0


def marcar_lidas_por_entidade(entity_type: str, entity_id: int, kind: str | None = None) -> int:
    """Marca lidas, para TODOS os destinatários, as notificações de um objeto (feature 298).

    É o "o aviso some sozinho": quando o formulário ganha destino (vira evento ou é encerrado),
    ninguém mais precisa ser avisado dele. Marcar como lida — e não apagar — preserva o histórico
    de `/notificacoes`, deixa lida a que já estava lida, e a retenção de 30 dias limpa sozinha.
    **Sem commit**: roda dentro da transação do fato (o vínculo, o encerramento).
    """
    condicoes = [
        Notification.entity_type == entity_type,
        Notification.entity_id == entity_id,
        Notification.read_at.is_(None),
    ]
    if kind:
        condicoes.append(Notification.kind == kind)
    resultado = db.session.execute(update(Notification).where(*condicoes).values(read_at=now_sp()))
    return resultado.rowcount or 0


def marcar_lidas_por_entidades(entity_type: str, entity_ids, kind: str | None = None) -> int:
    """Mesmo efeito de `marcar_lidas_por_entidade`, em lote (`entity_id IN (…)`), sem commit.

    `entity_ids` pode ser lista ou subconsulta — é o que as correções únicas por CLI usam.
    """
    condicoes = [
        Notification.entity_type == entity_type,
        Notification.entity_id.in_(entity_ids),
        Notification.read_at.is_(None),
    ]
    if kind:
        condicoes.append(Notification.kind == kind)
    resultado = db.session.execute(
        update(Notification).where(*condicoes).values(read_at=now_sp()),
        execution_options={"synchronize_session": False},
    )
    return resultado.rowcount or 0


def apagar_por_entidade(entity_type: str, entity_id: int) -> int:
    """Apaga as notificações de um objeto — para a exclusão do objeto não deixar link morto."""
    resultado = db.session.execute(
        delete(Notification).where(
            Notification.entity_type == entity_type, Notification.entity_id == entity_id
        )
    )
    return resultado.rowcount or 0


def _condicao_antigas(agora: datetime):
    corte_lida = agora - timedelta(days=RETENCAO_LIDA_DIAS)
    corte_nao_lida = agora - timedelta(days=RETENCAO_NAO_LIDA_DIAS)
    return or_(
        and_(Notification.read_at.isnot(None), Notification.read_at < corte_lida),
        and_(Notification.read_at.is_(None), Notification.created_at < corte_nao_lida),
    )


def contar_antigas(agora: datetime | None = None) -> int:
    """Quantas linhas `limpar_antigas` apagaria agora (o dry-run do CLI)."""
    agora = agora or now_sp()
    return db.session.scalar(
        select(db.func.count(Notification.id)).where(_condicao_antigas(agora))
    ) or 0


def limpar_antigas(agora: datetime | None = None) -> int:
    """Retenção: apaga em lotes de 1000 e **comita por lote** — para não segurar lock numa tabela
    que recebe INSERT a cada formulário. Idempotente: três workers rodando ao mesmo tempo produzem
    o mesmo resultado, por isso roda sem claim atômico (docs/04 §7, mesma justificativa do
    review-cleanup)."""
    agora = agora or now_sp()
    total = 0
    while True:
        ids = [
            i
            for (i,) in db.session.execute(
                select(Notification.id).where(_condicao_antigas(agora)).limit(_LOTE_LIMPEZA)
            )
        ]
        if not ids:
            break
        total += db.session.execute(
            delete(Notification).where(Notification.id.in_(ids))
        ).rowcount or 0
        db.session.commit()
    return total


def serializar(n: Notification) -> dict:
    """Forma JSON de uma notificação. `created_at`/`read_at` em ISO **naive São Paulo**, como
    `start_at` dos eventos — o front recorta a string, nunca passa por `Date` + `toISOString`."""
    return {
        "id": n.id,
        "kind": n.kind,
        "severity": n.severity,
        "title": n.title,
        "body": n.body,
        "link_path": n.link_path,
        "entity_type": n.entity_type,
        "entity_id": n.entity_id,
        "created_at": n.created_at.isoformat(timespec="seconds") if n.created_at else None,
        "read_at": n.read_at.isoformat(timespec="seconds") if n.read_at else None,
    }
