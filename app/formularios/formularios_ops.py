"""Núcleo de negócio do lado staff/admin de Formulários (migração 177, US7).

Extraído de `app/formularios/routes.py` (rotas `/formularios/*`, exceto o fluxo público
`/f/*` — já coberto por `app/api/formularios_write.py` desde a feature 163) — funções puras
(sem `flask.request`/`render_template`/`flash`), reusadas tanto pela view Jinja quanto pelos
endpoints de API (`app/api/formularios_admin_read.py`, `app/api/formularios_admin_write.py`).
"""

from __future__ import annotations

import json
import re
import urllib.parse
from dataclasses import dataclass
from datetime import UTC, date, datetime, time
from zoneinfo import ZoneInfo

from sqlalchemy import not_
from sqlalchemy.orm import joinedload

from app import db
from app.clientes.importer import normalize_phone
from app.constants import CORTE_FORMULARIOS_PADRAO, FORM_TIPO_ROTULOS
from app.models import (
    CalendarEvent,
    Client,
    EventClient,
    FormFieldDefinition,
    FormResponse,
    SiteSetting,
)
from app.utils import strip_accents_lower, unaccent_lower_sql

# Chaves de campos-sistema usadas pela automação de CPF/CNPJ/endereço do cliente (feature 119)
# — busca por chave estável, sobrevive a renomeação do rótulo pelo editor (FR-009 da 123).
SYSTEM_KEY_CPF = "cpf"
SYSTEM_KEY_CNPJ = "cnpj"
SYSTEM_KEY_ADDRESS_COMUM = "endereco_contratante"
SYSTEM_KEY_ADDRESS_CORPORATIVO = "endereco_empresa"


class FormValidationError(Exception):
    """Erro de validação de negócio (campo obrigatório/inválido, ação bloqueada)."""

    def __init__(self, field: str, message: str) -> None:
        super().__init__(message)
        self.field = field
        self.message = message


class FormularioJaTemDestino(Exception):
    """O formulário já tem destino — ligado a um evento ou encerrado (feature 298).

    Vira 409 em todos os caminhos, com a MESMA mensagem: tela Formulários, sugestão, criar evento,
    aba Comercial e edição do evento. Antes cada caminho fazia uma coisa — um sobrescrevia o
    vínculo, outro ignorava em silêncio, outro recusava com texto próprio.
    """

    MENSAGEM = "Este formulário já tem destino."

    def __init__(self, mensagem: str | None = None) -> None:
        self.message = mensagem or self.MENSAGEM
        super().__init__(self.message)


@dataclass
class VinculoResultado:
    """O que o núcleo de vínculo devolve a quem chamou (feature 298).

    ``divergencia_cliente`` vem preenchida quando a cliente do formulário não é nenhuma das
    clientes do evento: o núcleo não mexe em nada nesse caso (FR-015) e a tela oferece a troca.
    """

    divergencia_cliente: dict | None = None


# ── Destino do formulário (feature 298) ──────────────────────────────

_FUSO_SP = ZoneInfo("America/Sao_Paulo")

#: Partições que se excluem e somam o total — a MESMA regra serve os cartões da tela Formulários e
#: a lista da Home (FR-017: os dois números não podem divergir).
DESTINOS = ("sem_destino", "com_evento", "encerrados", "historico")


def corte_dia_sp() -> date:
    """Dia do corte de "o que é tarefa": a data de início do sistema, ou 01/06/2026 se vazia."""
    settings = SiteSetting.query.get(1)
    if settings is not None and settings.release_date:
        return settings.release_date
    return CORTE_FORMULARIOS_PADRAO


def corte_de_chegada() -> datetime:
    """Meia-noite de São Paulo do dia do corte, em UTC ingênuo — o fuso de ``created_at``.

    ``FormResponse.created_at`` é gravado com ``utcnow``: comparar com a meia-noite "ingênua" do
    dia punha no mês novo o formulário que chegou às 21h da véspera em Brasília. Por isso não se
    reusa o ``dashboard_cutoff`` das cobranças, que além disso cai em ``date.today()`` (UTC).
    """
    inicio_sp = datetime.combine(corte_dia_sp(), time.min, tzinfo=_FUSO_SP)
    return inicio_sp.astimezone(UTC).replace(tzinfo=None)


def dia_sp(utc_ingenuo: datetime) -> date:
    """Dia em São Paulo de um instante gravado em UTC ingênuo (``created_at``/``closed_at``)."""
    return utc_ingenuo.replace(tzinfo=UTC).astimezone(_FUSO_SP).date()


def iso_utc(utc_ingenuo: datetime | None) -> str | None:
    """ISO com ``+00:00`` de um instante em UTC ingênuo, para o navegador converter certo.

    Sem o fuso, ``new Date(iso)`` lia como hora local e "Recebida em" mostrava 3 h a mais
    (corrigido de carona na feature 298).
    """
    return utc_ingenuo.replace(tzinfo=UTC).isoformat() if utc_ingenuo else None


def condicao_sem_destino(corte: datetime):
    """Chegou desde o corte, sem evento e sem encerramento — o que vira tarefa na Home."""
    return db.and_(
        FormResponse.created_at >= corte,
        FormResponse.event_id.is_(None),
        FormResponse.closed_at.is_(None),
    )


def condicao_particao(nome: str, corte: datetime):
    """Condição SQL de uma partição de ``DESTINOS`` (``None`` para nome desconhecido)."""
    desde_o_corte = FormResponse.created_at >= corte
    if nome == "historico":
        return FormResponse.created_at < corte
    if nome == "com_evento":
        return db.and_(desde_o_corte, FormResponse.event_id.isnot(None))
    if nome == "encerrados":
        return db.and_(
            desde_o_corte, FormResponse.event_id.is_(None), FormResponse.closed_at.isnot(None)
        )
    if nome == "sem_destino":
        return condicao_sem_destino(corte)
    return None


def destino_de(response: FormResponse, corte: datetime) -> str:
    """A partição de um formulário, em Python, com as MESMAS regras de ``condicao_particao``."""
    if response.created_at < corte:
        return "historico"
    if response.event_id is not None:
        return "com_evento"
    if response.closed_at is not None:
        return "encerrados"
    return "sem_destino"


def contar_por_destino(corte: datetime | None = None) -> dict:
    """Contagens por partição numa query só, mais o dia do corte (rótulos "desde DD/MM")."""
    corte = corte or corte_de_chegada()
    row = db.session.query(
        db.func.count(FormResponse.id),
        *[db.func.count(FormResponse.id).filter(condicao_particao(p, corte)) for p in DESTINOS],
    ).one()
    contagens: dict = {"total": row[0], **{p: row[i + 1] for i, p in enumerate(DESTINOS)}}
    contagens["corte"] = dia_sp(corte).isoformat()
    return contagens


def tipo_rotulo(form_type: str) -> str:
    """Tipo exibido na linha: "Festa" ou "Corporativo" (o ``form_type_label`` diz "Pré-contrato")."""
    return FORM_TIPO_ROTULOS.get(form_type, FORM_TIPO_ROTULOS["comum"])


def bloquear_formulario(response_id: int) -> FormResponse | None:
    """Relê o formulário com ``SELECT … FOR UPDATE``, sem commit (feature 298).

    Duas pessoas agindo no mesmo formulário passam a esperar uma pela outra, e a segunda enxerga
    o destino que a primeira deu — checar ``event_id`` só em Python deixava as duas passarem. O
    bloqueio dura até o commit (ou rollback) de quem chamou; ``populate_existing`` porque o objeto
    pode já estar na sessão com valores velhos.
    """
    return (
        db.session.query(FormResponse)
        .filter(FormResponse.id == response_id)
        .with_for_update()
        .populate_existing()
        .one_or_none()
    )


def _field_value_by_key(sections: list[dict], field_key: str) -> str:
    """Busca o valor de um campo pela chave estável (feature 123 — sobrevive a renomeação de
    rótulo). Respostas anteriores à feature 123 têm campos com só ``[rótulo, valor]``, sem
    chave — nesse caso a busca simplesmente não encontra nada (mesmo comportamento best-effort
    que a automação já tinha antes)."""
    for section in sections:
        for campo in section["campos"]:
            if len(campo) == 3 and campo[0] == field_key:
                return (campo[2] or "").strip()
    return ""


def fill_client_from_response(client: Client, response: FormResponse) -> None:
    """Completa CPF/CNPJ e endereço do cliente com dados da resposta (feature 119).

    Só preenche campos que estiverem vazios no cliente — nunca sobrescreve um valor já
    existente (manual ou de uma associação anterior).
    """
    sections = response.data_sections
    if response.form_type == "corporativo":
        cnpj = _field_value_by_key(sections, SYSTEM_KEY_CNPJ)
        address = _field_value_by_key(sections, SYSTEM_KEY_ADDRESS_CORPORATIVO)
        if cnpj and not client.cnpj:
            client.cnpj = cnpj
        if address and not client.address:
            client.address = address
    else:
        cpf = _field_value_by_key(sections, SYSTEM_KEY_CPF)
        address = _field_value_by_key(sections, SYSTEM_KEY_ADDRESS_COMUM)
        if cpf and not client.cpf:
            client.cpf = cpf
        if address and not client.address:
            client.address = address


def _data_do_termo(q: str) -> date | None:
    """Interpreta o termo como data do evento: `dd/mm/aaaa`, `dd/mm/aa`, `dd-mm-aaaa` ou ISO.

    O buscador de pré-contrato oferece "nome, telefone ou data" — sem isto, digitar a data do
    evento (o jeito mais natural de achar a resposta de uma cliente cujo nome não se lembra)
    devolvia lista vazia.
    """
    termo = q.strip()
    for formato in ("%d/%m/%Y", "%d/%m/%y", "%d-%m-%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(termo, formato).date()
        except ValueError:
            continue
    return None


def search_responses(q: str) -> list[FormResponse]:
    """Busca respostas por nome, telefone ou data do evento (sem acentos).

    Usado pelo buscador de pré-contrato de `/events/new` e `/events/<id>/edit`.
    """
    q = (q or "").strip()
    if len(q) < 2:
        return []
    like = f"%{strip_accents_lower(q)}%"
    # Só conta como telefone o que tem dígito suficiente para não casar com tudo: "12" (de uma
    # data digitada pela metade) traria meio banco.
    digits = "".join(c for c in q if c.isdigit())
    conditions = [unaccent_lower_sql(FormResponse.contact_name).like(like)]
    if len(digits) >= 4:
        conditions.append(FormResponse.contact_phone.ilike(f"%{digits}%"))
    data = _data_do_termo(q)
    if data is not None:
        conditions.append(FormResponse.event_date == data)
    from sqlalchemy import or_

    return (
        FormResponse.query.options(
            joinedload(FormResponse.client), joinedload(FormResponse.closed_by)
        )
        .filter(or_(*conditions))
        .order_by(FormResponse.created_at.desc())
        .limit(10)
        .all()
    )


# Filtros da listagem = as partições por destino (feature 298). Os filtros antigos
# (`sem_evento`, `sem_cliente`, `ambiguos`, `futuros_sem_evento`) contavam o histórico importado e
# diziam 1.347 "sem evento"; chave antiga ou desconhecida cai em "todos", sem erro.
STATUS_FILTERS = DESTINOS


def _status_condition(filtro: str, corte: datetime):
    """Condição SQL de um filtro de destino (``None`` para filtro desconhecido/vazio)."""
    if filtro not in STATUS_FILTERS:
        return None
    return condicao_particao(filtro, corte)


def count_status(corte: datetime | None = None) -> dict:
    """Contadores dos cartões da tela de formulários — as partições por destino e o corte."""
    return contar_por_destino(corte)


def list_responses(
    limit: int = 200, filtro: str = "", corte: datetime | None = None
) -> tuple[list[FormResponse], bool]:
    """Lista as respostas mais recentes (tela de índice), com filtro de destino opcional.

    Cliente e quem encerrou vêm em ``joinedload``: a listagem mostra os dois em cada linha, e
    sem isso seriam até ``limit`` queries extras (N+1).

    Returns:
        ``(respostas, truncado)`` — ``truncado`` diz que o filtro tem mais que ``limit``, para a
        tela avisar "use a busca" em vez de fingir que a lista acabou.
    """
    corte = corte or corte_de_chegada()
    query = FormResponse.query.options(
        joinedload(FormResponse.client), joinedload(FormResponse.closed_by)
    )
    condition = _status_condition(filtro, corte)
    if condition is not None:
        query = query.filter(condition)
    linhas = query.order_by(FormResponse.created_at.desc()).limit(limit + 1).all()
    return linhas[:limit], len(linhas) > limit


def ensure_event_client(event: CalendarEvent, client_id: int | None) -> None:
    """Garante o cliente na associação evento↔cliente (``event_clients``), sem commit.

    É o elo que faltava entre o vínculo de formulário e a ficha da cliente: sem uma linha
    em ``event_clients``, o evento não aparece no perfil dela (correção de dados de
    06/08/2026 preencheu o retroativo; daqui em diante todo vínculo passa por aqui).
    Primeiro cliente do evento entra como Contratante (e assume o ``client_id``
    denormalizado); demais entram como Outros — o comercial ajusta a relação na tela do
    evento se for o caso.
    """
    if not client_id:
        return
    already = EventClient.query.filter_by(event_id=event.id, client_id=client_id).first()
    if already:
        return
    has_any = EventClient.query.filter_by(event_id=event.id).first() is not None
    db.session.add(
        EventClient(
            event_id=event.id,
            client_id=client_id,
            relationship_type="Outros" if has_any else "Contratante",
        )
    )
    if not has_any and event.client_id is None:
        event.client_id = client_id


def associate_client(response: FormResponse, client_id: int | None) -> Client:
    """Associa a resposta a um cliente existente ou cria um a partir dos dados dela.

    Se a resposta já estiver vinculada a um evento, o cliente também entra na associação
    evento↔cliente — é isso que faz o evento aparecer na ficha dela.

    Raises:
        FormValidationError: cliente informado não encontrado, ou resposta sem telefone
            válido para criar um cliente novo.
    """
    if client_id:
        client = Client.query.get(client_id)
        if not client:
            raise FormValidationError("client_id", "Cliente não encontrado.")
    else:
        phone = response.contact_phone
        if not phone:
            raise FormValidationError(
                "client_id", "A resposta não tem telefone válido para criar o cliente."
            )
        client = Client.query.filter_by(phone=phone).first()
        if not client:
            client = Client(
                name=response.contact_name,
                phone=phone,
                phone_display=response.contact_phone_display,
                # A ficha nasceu de uma resposta de formulário, não de digitação na tela —
                # é o que separa a aquisição por formulário do cadastro manual no gráfico
                # de origem (o mapa de `client_ops.client_metrics` traduz esta chave).
                source="formulario",
            )
            db.session.add(client)
            db.session.flush()
    fill_client_from_response(client, response)
    response.client_id = client.id
    response.client_link_source = "manual"
    if response.event_id is not None and response.event is not None:
        ensure_event_client(response.event, client.id)
    db.session.commit()
    return client


def dissociate_client(response: FormResponse) -> None:
    """Remove a associação da resposta com o cliente (e o rastro de como ela foi feita)."""
    response.client_id = None
    response.client_link_source = None
    db.session.commit()


def _limpar_encerramento(response: FormResponse) -> None:
    """Ligar a um evento desfaz o encerramento: um evento real vence o motivo (feature 298)."""
    response.closed_reason = None
    response.closed_note = None
    response.closed_by_id = None
    response.closed_at = None


def _ids_clientes_do_evento(event: CalendarEvent) -> set[int]:
    ids = {ec.client_id for ec in EventClient.query.filter_by(event_id=event.id).all()}
    if event.client_id:
        ids.add(event.client_id)
    return ids


def cliente_do_evento_para(response: FormResponse, event: CalendarEvent) -> int | None:
    """A cliente do evento que o formulário deve receber (feature 298, FR-015).

    Prefere a ficha com o MESMO telefone do formulário (é quem preencheu); na falta, a
    contratante denormalizada do evento; na falta, a primeira associada.
    """
    vinculos = EventClient.query.filter_by(event_id=event.id).all()
    if response.contact_phone:
        for ec in vinculos:
            if ec.client is not None and ec.client.phone == response.contact_phone:
                return ec.client_id
    if event.client_id:
        return event.client_id
    return vinculos[0].client_id if vinculos else None


def _ref_cliente(client_id: int | None) -> dict:
    cliente = db.session.get(Client, client_id) if client_id else None
    return {"id": client_id, "nome": cliente.name if cliente else None}


def divergencia_de_cliente(
    response: FormResponse, event: CalendarEvent | None = None
) -> dict | None:
    """Cliente do formulário que não é nenhuma das clientes do evento; ``None`` se não divergem.

    "Divergem" exige as duas preenchidas: formulário sem cliente, ou evento sem nenhuma, não é
    divergência — nesses casos o núcleo simplesmente leva a que falta.
    """
    event = event or response.event
    if event is None or response.client_id is None:
        return None
    ids = _ids_clientes_do_evento(event)
    if not ids or response.client_id in ids:
        return None
    return {
        "formulario": _ref_cliente(response.client_id),
        "evento": _ref_cliente(cliente_do_evento_para(response, event)),
    }


def _levar_cliente(response: FormResponse, event: CalendarEvent) -> VinculoResultado:
    """A cliente nos dois sentidos, sem trocar ninguém (feature 298, FR-015).

    Até a 298 só existia formulário→evento, e quando o evento já tinha outra cliente a do
    formulário entrava como "Outros" — mexia no evento justamente quando as duas divergiam.
    """
    if response.client_id is None:
        client_id = cliente_do_evento_para(response, event)
        if client_id is not None:
            response.client_id = client_id
            response.client_link_source = "evento"
        return VinculoResultado()
    if not _ids_clientes_do_evento(event):
        ensure_event_client(event, response.client_id)
        return VinculoResultado()
    return VinculoResultado(divergencia_cliente=divergencia_de_cliente(response, event))


def apply_event_link(
    response: FormResponse,
    event: CalendarEvent,
    *,
    source: str = "manual",
    decisao_humana: bool = True,
) -> VinculoResultado:
    """Núcleo ÚNICO do vínculo resposta→evento, **sem commit** (features 267 e 298).

    Até a 298, três caminhos gravavam o vínculo à mão (criar evento, envio público e o
    reprocessamento do sync) e cada um esquecia uma parte. Agora todos entram aqui, e o vínculo
    sempre: desfaz o encerramento, leva a cliente nos dois sentidos (sem trocar ninguém quando
    divergem) e apaga, para TODOS os destinatários, o aviso "nova resposta" desse formulário.

    Sem commit de propósito: quem chama pode estar dentro de um laço ou de uma transação maior.

    Args:
        response: a resposta a vincular.
        event: o evento de destino (objeto, não id).
        source: origem do vínculo, ``"manual"`` por padrão.
        decisao_humana: grava ``event_link_locked``. O automático passa ``False``: se o evento for
            excluído, a resposta volta para a fila e pode ser religada ao evento recriado.

    Returns:
        ``VinculoResultado`` com a divergência de cliente, quando houver.
    """
    _limpar_encerramento(response)
    response.event_id = event.id
    response.event_link_source = source
    response.event_link_ambiguous = False
    if decisao_humana:
        response.event_link_locked = True
    resultado = _levar_cliente(response, event)
    from app.notificacoes import notificacoes_ops

    notificacoes_ops.marcar_lidas_por_entidade(
        "form_response", response.id, notificacoes_ops.KIND_FORM_RESPONSE
    )
    return resultado


def clear_event_link(response: FormResponse) -> None:
    """Desfaz o vínculo de evento, **sem commit** (feature 267).

    Marca `event_link_locked`: uma vez que um humano decide desfazer, a automação não pode
    religar sozinha ao mesmo evento no próximo ciclo de sincronização.
    """
    response.event_id = None
    response.event_link_source = None
    response.event_link_ambiguous = False
    response.event_link_locked = True


def link_event(
    response: FormResponse, event_id: int
) -> tuple[CalendarEvent, VinculoResultado]:
    """Associa manualmente a resposta a um evento existente da agenda (features 126 e 298).

    Até a 298 este wrapper SOBRESCREVIA um vínculo existente. Agora recusa: formulário com evento
    levanta ``FormularioJaTemDestino`` (409), a mesma regra de todos os caminhos (FR-018). A tela
    nunca oferecia ligar um formulário já ligado, então nenhum uso legítimo dependia disso.

    Raises:
        FormValidationError: evento não encontrado.
        FormularioJaTemDestino: o formulário já tem evento.
    """
    event = CalendarEvent.query.get(event_id)
    if not event:
        raise FormValidationError("event_id", "Evento não encontrado.")
    bloqueado = bloquear_formulario(response.id)
    if bloqueado is None or bloqueado.event_id is not None:
        raise FormularioJaTemDestino()
    resultado = apply_event_link(bloqueado, event)
    db.session.commit()
    return event, resultado


def vincular_formulario_ao_evento(
    event: CalendarEvent, form_response_id: int | None
) -> VinculoResultado | None:
    """Caminho da edição do evento: liga o pré-contrato escolhido, **sem commit** (184 → 298).

    ``None`` não desliga (contrato antigo do PATCH em bloco — a tela manda o id atual em toda
    gravação). Formulário já ligado a ESTE evento: nada a fazer. Ligado a OUTRO: antes era
    ignorado em silêncio; agora levanta ``FormularioJaTemDestino``.
    """
    if form_response_id is None:
        return None
    response = bloquear_formulario(form_response_id)
    if response is None or response.event_id == event.id:
        return None
    if response.event_id is not None:
        raise FormularioJaTemDestino()
    return apply_event_link(response, event)


def unlink_event(response: FormResponse) -> None:
    """Desfaz o vínculo de evento — automático ou manual (feature 126, FR-008)."""
    clear_event_link(response)
    db.session.commit()


def delete_response(response: FormResponse) -> None:
    """Exclui uma resposta — chamador já deve ter checado a permissão (SUPERADMIN).

    Leva junto as notificações dela (feature 272): referência fraca, sem FK — este é o único lugar
    que garante que nenhum sino aponta para id morto.
    """
    from app.notificacoes import notificacoes_ops

    notificacoes_ops.apagar_por_entidade("form_response", response.id)
    db.session.delete(response)
    db.session.commit()


# ── Editor de estrutura dos formulários (feature 123) ────────────────


def list_field_definitions(form_type: str) -> list[FormFieldDefinition]:
    """Campos de um formulário, na ordem de exibição vigente."""
    return (
        FormFieldDefinition.query.filter_by(form_type=form_type)
        .order_by(FormFieldDefinition.order)
        .all()
    )


def _unique_field_key(form_type: str, label: str) -> str:
    """Gera uma chave estável (slug) a partir do rótulo, única dentro do formulário."""
    base = re.sub(r"[^a-z0-9]+", "_", strip_accents_lower(label)).strip("_") or "campo"
    existing = {
        row[0]
        for row in db.session.query(FormFieldDefinition.field_key).filter_by(form_type=form_type).all()
    }
    key = base
    suffix = 2
    while key in existing:
        key = f"{base}_{suffix}"
        suffix += 1
    return key


def _next_order(form_type: str) -> int:
    """Posição no fim da lista global — o agrupamento por seção não depende de contiguidade em
    `order`, então um campo novo sempre cai no fim da sua seção."""
    last = (
        FormFieldDefinition.query.filter_by(form_type=form_type)
        .order_by(FormFieldDefinition.order.desc())
        .first()
    )
    return (last.order + 1) if last else 0


def _parse_options(raw: str) -> list[str]:
    return [line.strip() for line in (raw or "").splitlines() if line.strip()]


def create_field(form_type: str, data: dict) -> FormFieldDefinition:
    """Adiciona um campo personalizado ao fim de uma seção.

    Args:
        data: `label`, `section_name`, `field_type`, `help_text`, `required` (bool),
            `options` (string com uma opção por linha, só para `field_type == "selecao"`).

    Raises:
        FormValidationError: rótulo/seção ausente, tipo inválido, ou seleção sem opções.
    """
    label = (data.get("label") or "").strip()
    section_name = (data.get("section_name") or "").strip()
    field_type = data.get("field_type") or ""
    if not label or not section_name:
        raise FormValidationError("label", "Informe o rótulo e a seção do campo.")
    if field_type not in FormFieldDefinition.FIELD_TYPES:
        raise FormValidationError("field_type", "Tipo de campo inválido.")
    options = None
    if field_type == "selecao":
        opts = _parse_options(data.get("options", ""))
        if not opts:
            raise FormValidationError(
                "options", "Um campo de seleção precisa de pelo menos uma opção."
            )
        options = json.dumps(opts, ensure_ascii=False)
    field = FormFieldDefinition(
        form_type=form_type,
        section_name=section_name,
        field_key=_unique_field_key(form_type, label),
        field_type=field_type,
        label=label,
        help_text=(data.get("help_text") or "").strip() or None,
        required=bool(data.get("required")),
        options=options,
        order=_next_order(form_type),
        is_system=False,
    )
    db.session.add(field)
    db.session.commit()
    return field


def update_field(field: FormFieldDefinition, data: dict) -> FormFieldDefinition:
    """Edita rótulo/texto de ajuda/obrigatoriedade/opções de um campo.

    `field_type`/`field_key` são imutáveis após criação (nunca alterados aqui) — evita
    inconsistência de formato em respostas já salvas e preserva a busca por chave (feature 119).

    Raises:
        FormValidationError: rótulo vazio, ou seleção sem opções.
    """
    label = (data.get("label") or "").strip()
    if not label:
        raise FormValidationError("label", "O rótulo não pode ficar vazio.")
    if field.field_type == "selecao":
        opts = _parse_options(data.get("options", ""))
        if not opts:
            raise FormValidationError(
                "options", "Um campo de seleção precisa de pelo menos uma opção."
            )
        field.options = json.dumps(opts, ensure_ascii=False)
    field.label = label
    field.help_text = (data.get("help_text") or "").strip() or None
    field.placeholder = (data.get("placeholder") or "").strip() or None
    field.required = bool(data.get("required"))
    db.session.commit()
    return field


def move_field(field: FormFieldDefinition, direction: str) -> None:
    """Reordena um campo dentro da própria seção (`direction`: `"up"`/`"down"`)."""
    siblings = (
        FormFieldDefinition.query.filter_by(form_type=field.form_type, section_name=field.section_name)
        .order_by(FormFieldDefinition.order)
        .all()
    )
    idx = siblings.index(field)
    swap_idx = idx - 1 if direction == "up" else idx + 1
    if 0 <= swap_idx < len(siblings):
        other = siblings[swap_idx]
        field.order, other.order = other.order, field.order
        db.session.commit()


def delete_field(field: FormFieldDefinition) -> None:
    """Remove um campo personalizado.

    Raises:
        FormValidationError: campo é `is_system` (usado por outras partes do sistema).
    """
    if field.is_system:
        raise FormValidationError(
            "is_system",
            f'"{field.label}" é um campo do sistema (usado por outras telas) e não pode ser '
            "removido — só o texto e a obrigatoriedade podem ser ajustados.",
        )
    db.session.delete(field)
    db.session.commit()


# ─────────────────────────────────────────────────────────────────────────────
# Núcleo dos formulários públicos, movido de `routes.py` na fase 3 da remoção do Jinja.
#
# Estes símbolos nunca foram só do Jinja: `app/api/formularios_write.py`,
# `app/api/catalogo_read.py`, `app/calendar/sync.py` e `app/cli.py` importavam-nos de dentro do
# blueprint. Enquanto morassem lá, apagar a superfície Jinja derrubava a API viva.
#
# Continuam puros: não importam `flask.request`, `render_template` nem `flash` — quem monta a
# resposta HTTP é a camada de rota, que passa o dicionário de campos por argumento.
# ─────────────────────────────────────────────────────────────────────────────

DEFAULT_WHATSAPP_NUMBER = "5511970570577"

FIELD_TYPE_LABELS = {
    "texto_curto": "Texto curto",
    "texto_longo": "Texto longo (parágrafo)",
    "selecao": "Seleção (lista de opções)",
    "data": "Data",
    "hora": "Hora",
    "telefone": "Telefone/WhatsApp",
    "email": "E-mail",
    "cpf": "CPF",
    "cnpj": "CNPJ",
    "cep": "CEP",
    "sim_nao": "Sim/Não",
}

# Campos de endereço acoplados ao autopreenchimento por CEP (só existem no formulário 'comum').
CEP_TARGET_KEYS = ("logradouro", "bairro", "cidade", "estado")

FORM_META = {
    "comum": {
        "title": "Informações para Pré-Contrato — Manto Produções",
        "header": "INFORMAÇÕES PARA PRÉ-CONTRATO",
        "message_title": "INFORMAÇÕES PARA PRÉ-CONTRATO — MANTO PRODUÇÕES",
        "name_key": "nome_contratante",
    },
    "corporativo": {
        "title": "Contrato Corporativo — Manto Produções",
        "header": "CONTRATO CORPORATIVO",
        "message_title": "CONTRATO CORPORATIVO — MANTO PRODUÇÕES",
        "name_key": "razao_social",
    },
}

# ── Helpers de validação/montagem ────────────────────────────────────


def _only_digits(raw: str | None) -> str:
    return "".join(c for c in (raw or "") if c.isdigit())


def _build_phone_display(form, prefix: str) -> str:
    """Telefone como digitado (DDI + nacional), ex.: ``"+55 (11) 99999-9999"``."""
    national = (form.get(f"{prefix}_national") or "").strip()
    if not national:
        return ""
    if national.startswith("+"):
        return national
    ddi = (form.get(f"{prefix}_ddi") or "+55").strip()
    if not ddi.startswith("+"):
        ddi = "+" + ddi.lstrip("+")
    return f"{ddi} {national}".strip()


def _parse_event_date(raw: str | None) -> date | None:
    """Converte a data do input HTML (``YYYY-MM-DD``) em ``date``."""
    try:
        return datetime.strptime((raw or "").strip(), "%Y-%m-%d").date()
    except ValueError:
        return None


def _fmt_date_br(d: date | None) -> str:
    return d.strftime("%d/%m/%Y") if d else ""


def _valid_email(raw: str) -> bool:
    return "@" in raw and "." in raw.split("@")[-1] and " " not in raw


def _whatsapp_target() -> str:
    """Número destino das mensagens (settings, com fallback para o padrão)."""
    settings = SiteSetting.query.get(1)
    number = _only_digits(getattr(settings, "whatsapp_form_number", None) or "")
    return number or DEFAULT_WHATSAPP_NUMBER


def _build_message(title: str, sections: list[dict]) -> str:
    """Formata a mensagem de WhatsApp: título + seções com ``*Rótulo:* valor`` por linha."""
    lines = [f"*{title}*"]
    for section in sections:
        lines.append("")
        lines.append(f"*— {section['secao']} —*")
        for campo in section["campos"]:
            label, value = campo[-2], campo[-1]
            if (value or "").strip():
                lines.append(f"*{label}:* {value}")
    return "\n".join(lines)


def _whatsapp_link(message: str) -> str:
    return (
        "https://api.whatsapp.com/send?phone="
        f"{_whatsapp_target()}&text={urllib.parse.quote(message)}"
    )


def _save_response(form_type: str, contact_name: str, phone_display: str,
                   event_date: date | None, sections: list[dict]) -> FormResponse:
    """Persiste a resposta (sempre ANTES de abrir o WhatsApp — SC-002)."""
    response = FormResponse(
        form_type=form_type,
        data=json.dumps(sections, ensure_ascii=False),
        contact_name=contact_name[:200],
        contact_phone=normalize_phone(phone_display),
        contact_phone_display=phone_display[:30] or None,
        event_date=event_date,
    )
    db.session.add(response)
    db.session.commit()
    return response


# ── Vínculo automático a evento da agenda (feature 126) ──────────────


def _real_event_candidates(event_date: date) -> list[CalendarEvent]:
    """Eventos "reais" (não ensaio, não satélite) numa data — candidatos a vínculo."""
    return (
        CalendarEvent.query
        .filter(
            db.func.date(CalendarEvent.start_at) == event_date,
            not_(CalendarEvent.title.like("🟧 ENSAIO%")),
            CalendarEvent.group_leader_id.is_(None),
        )
        .all()
    )


def _event_client_phones(event_id: int) -> set[str]:
    """Telefones dos clientes já associados a um evento (para checar contradição)."""
    return {
        ec.client.phone for ec in EventClient.query.filter_by(event_id=event_id).all()
        if ec.client and ec.client.phone
    }


def _attempt_auto_link(response: FormResponse) -> str | None:
    """Tenta vincular a resposta a um evento real da agenda (endurecido pós-feature 126).

    Só vincula sozinho quando os DOIS sinais confirmam: existe evento real na data
    informada E o telefone da resposta pertence a um cliente associado a exatamente um
    desses eventos. Qualquer coisa a menos vira revisão manual (``"ambiguous"``) — a
    Manto costuma ter vários eventos no mesmo dia e clientes recorrentes, então data
    sozinha ou identidade sozinha já vincularam resposta errada em evento errado
    (correção de dados de 06/08/2026: 25 vínculos desfeitos).

    Retorna ``"auto_date"`` se vinculou (persiste ``response.event_id`` no objeto, sem
    commit — quem chama decide quando salvar), ``"ambiguous"`` se há candidato na data
    mas sem confirmação pelo telefone, ou ``None`` se não havia evento na data.
    """
    if (
        response.event_id is not None
        or response.event_link_locked
        or response.closed_at is not None
        or not response.event_date
    ):
        return None

    candidates = _real_event_candidates(response.event_date)
    if not candidates:
        return None
    if not response.contact_phone:
        return "ambiguous"

    matched = [e for e in candidates if response.contact_phone in _event_client_phones(e.id)]
    if len(matched) == 1:
        # Pelo núcleo (feature 298): o vínculo automático também leva a cliente e apaga o aviso,
        # mas NÃO grava decisão humana — excluído o evento, a resposta volta para a fila e a
        # automação pode religá-la ao evento recriado.
        apply_event_link(response, matched[0], source="auto_date", decisao_humana=False)
        return "auto_date"
    return "ambiguous"


def attempt_auto_link_client(response: FormResponse) -> str | None:
    """Vincula a resposta à ficha da cliente quando o telefone identifica uma só (feature 266).

    `Client.phone` é UNIQUE, então "bate com exatamente uma" é garantia do banco e não
    heurística: é literalmente a mesma consulta que a comercial dispara hoje clicando em
    "associar" na sugestão da tela. O que se ganha é não precisar do clique em toda resposta
    de cliente recorrente — o que hoje deixa o cartão "sem cliente" cheio de gente conhecida.

    **Nunca cria cliente**: o endpoint de submissão é público e sem autenticação, e deixá-lo
    inserir em ``clients`` seria porta aberta para poluir o CRM. Criar continua sendo ação
    humana, por ``associate_client``.

    Não roda no reprocessamento do sync de propósito (ver ``retry_auto_link_pending``): não
    existe equivalente de ``event_link_locked`` para cliente, então religar em ciclo desfaria
    a decisão de quem desassociou.

    Args:
        response: resposta recém-salva (sem commit — quem chama decide quando salvar).

    Returns:
        ``"auto_phone"`` se vinculou, ``None`` se não havia telefone, já havia vínculo, ou
        nenhuma ficha corresponde.
    """
    if response.client_id is not None or response.client_link_source or not response.contact_phone:
        return None
    client = Client.query.filter_by(phone=response.contact_phone).first()
    if client is None:
        return None
    fill_client_from_response(client, response)
    response.client_id = client.id
    return "auto_phone"


def retry_auto_link_pending() -> int:
    """Reprocessa respostas sem evento vinculado (feature 126).

    Chamada pelo ciclo de sincronização da agenda para cobrir o caso do evento ser
    criado/importado DEPOIS da resposta já ter chegado. Nunca reprocessa uma resposta
    que um humano já decidiu manualmente (``event_link_locked``). Retorna quantas
    respostas foram vinculadas nesta chamada.
    """
    pending = FormResponse.query.filter(
        FormResponse.event_id.is_(None),
        FormResponse.event_link_locked.is_(False),
        FormResponse.event_date.isnot(None),
        # Encerrado já tem destino (feature 298): religar ou marcar ambíguo desfaria a decisão.
        FormResponse.closed_at.is_(None),
    ).all()
    if not pending:
        return 0
    linked = 0
    for response in pending:
        result = _attempt_auto_link(response)
        if result == "auto_date":
            linked += 1
        elif result == "ambiguous":
            response.event_link_ambiguous = True
    db.session.commit()
    return linked


# ── Motor dinâmico dos formulários públicos (feature 123) ────────────


def _load_fields(form_type: str) -> list[FormFieldDefinition]:
    """Campos de um formulário, na ordem de exibição vigente."""
    return list_field_definitions(form_type)


def _grouped_sections(fields: list[FormFieldDefinition]) -> list[dict]:
    """Agrupa campos por seção, preservando a ordem de primeira aparição da seção e a ordem
    interna dos campos dentro dela (não depende de os campos de uma seção serem contíguos em
    ``order`` — um campo novo cai no fim da própria seção onde quer que seja inserido)."""
    by_section: dict[str, list[FormFieldDefinition]] = {}
    section_order: list[str] = []
    for field in fields:
        if field.section_name not in by_section:
            by_section[field.section_name] = []
            section_order.append(field.section_name)
        by_section[field.section_name].append(field)
    return [{"secao": name, "campos": by_section[name]} for name in section_order]


def _validate_dynamic(f, fields: list[FormFieldDefinition]) -> dict[str, str]:
    """Valida um formulário público a partir da definição de campos vigente (feature 123)."""
    errors: dict[str, str] = {}
    for field in fields:
        key = field.field_key
        if field.field_type == "telefone":
            if field.required and len(_only_digits(f.get(f"{key}_national"))) < 10:
                errors[f"{key}_national"] = f'Informe "{field.label}" com DDD.'
            continue
        raw = (f.get(key) or "").strip()
        if not raw:
            if field.required:
                errors[key] = f'Preencha o campo obrigatório: "{field.label}".'
            continue
        if field.field_type == "cpf" and len(_only_digits(raw)) != 11:
            errors[key] = "CPF inválido — confira os 11 dígitos."
        elif field.field_type == "cnpj" and len(_only_digits(raw)) != 14:
            errors[key] = "CNPJ inválido — confira os 14 dígitos."
        elif field.field_type == "cep" and len(_only_digits(raw)) != 8:
            errors[key] = "CEP inválido — confira os 8 dígitos."
        elif field.field_type == "email" and not _valid_email(raw):
            errors[key] = "Informe um e-mail válido."
        elif field.field_type == "data" and not _parse_event_date(raw):
            errors[key] = "Selecione uma data válida."
    # Regra especial preservada da versão hardcoded: "Descreva Outros" é obrigatório quando a
    # forma de pagamento escolhida é "Outros" — acoplada à chave, não generalizável sem lógica
    # condicional entre campos (fora de escopo da feature 123, ver spec/Assumptions).
    if any(fld.field_key == "descreva_outros" for fld in fields):
        if f.get("forma_pagamento") == "Outros" and not (f.get("descreva_outros") or "").strip():
            errors["descreva_outros"] = "Descreva a forma de pagamento."
    return errors


def _build_sections_dynamic(f, fields: list[FormFieldDefinition]) -> list[dict]:
    """Monta as seções ``[chave, rótulo, valor]`` a partir da definição de campos vigente.

    Agrupa pelo mesmo critério de ``_grouped_sections`` (por nome de seção, não por
    contiguidade em ``order``) — um campo personalizado inserido numa seção que já não está
    mais "por último" na ordenação global ainda cai na seção certa, sem duplicar o bloco.
    """
    by_section: dict[str, list[list[str]]] = {}
    section_order: list[str] = []
    for field in fields:
        if field.field_type == "telefone":
            value = _build_phone_display(f, field.field_key)
        elif field.field_type == "data":
            value = _fmt_date_br(_parse_event_date(f.get(field.field_key)))
        else:
            value = (f.get(field.field_key) or "").strip()
        if field.section_name not in by_section:
            by_section[field.section_name] = []
            section_order.append(field.section_name)
        by_section[field.section_name].append([field.field_key, field.label, value])
    return [{"secao": name, "campos": by_section[name]} for name in section_order]

