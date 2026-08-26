"""Operações de casting como fonte única de lógica (feature 146).

O núcleo de cada ação de casting mora aqui, com parâmetros explícitos (sem `request.form`,
`flash` ou `current_user`), para ser reusado por DOIS adaptadores finos: o handler Jinja
(`app/calendar/routes.py`, que lê o form e dá `flash`) e o endpoint JSON (`app/api/agenda_write.py`,
que lê o JSON e devolve o evento serializado). UMA implementação da regra (teto de cachê,
transições de convite, e-mails), zero divergência (Princípio I).

Ações: `assign_role` (escalar/atualizar/desescalar — US1/146), `add_role`/`delete_role`
(adicionar/remover cargo — US2/147), `send_invite`/`set_figurino_done`/`dismiss_role`/
`restore_role` (convite/figurino/dispensar/restaurar — US3/148), `set_transporte`
(carrinho de transporte fora de SP — feature 239).
"""

import json
from datetime import datetime
from decimal import Decimal
from typing import Any
from zoneinfo import ZoneInfo

from app.email_service import (
    send_async,
    send_event_changed_email,
    send_invite_email,
    send_removal_email,
)
from app.models import EventLog, EventRole, Talent, db
from app.money import format_brl, parse_brl

# Sentinela de "chave ausente" (feature 239). `None` é um valor LEGÍTIMO para `travel_cache`
# ("não definido"), então não dá para usar `None` como "não veio no payload": o casting em
# React nunca manda essa chave, e o `assign_role` gravava NULL por cima do adicional de
# transporte a cada "Salvar" — perda silenciosa de dado. Só grava quem realmente mandou.
_UNSET: Any = object()

_CENTAVOS = Decimal("0.01")


def e_vaga_de_presenca(role: Any) -> bool:
    """A vaga é o "Técnico de Som (Presença)" — quem vai fisicamente ao evento (feature 239)?

    Todo SHOW nasce com DUAS vagas de som: a do PIX ("Técnico de Som", Nivaldo — essa recebe)
    e a de presença, designada pela equipe de ensaio. A de presença **nunca** tem cachê
    (decisão 9) e fica fora de todos os somatórios de dinheiro (decisão 10) — quem paga é a
    outra. Fonte única do teste, para a regra não virar `character_name == "..."` espalhado.

    Args:
        role: O `EventRole` a testar (aceita qualquer objeto com `character_name`/`role_type`).

    Returns:
        True quando é a vaga de presença.
    """
    from app.calendar.routes import PRESENCE_CHARACTER

    return (
        getattr(role, "character_name", None) == PRESENCE_CHARACTER
        and getattr(role, "role_type", None) == "extra"
    )


def assign_role(
    event: Any,
    role: Any,
    *,
    talent_id: Any,
    cache_value: Any,
    travel_cache: Any = _UNSET,
    actor_name: str,
    is_superadmin: bool,
    tz: ZoneInfo,
) -> str:
    """Escala/atualiza/desescala o talento de um cargo. Núcleo extraído de `_handle_assign_casting`.

    Aplica o teto de cachê (`cache_cap`) para não-superadmin, reseta figurino/convite ao trocar
    de talento, registra em `EventLog` e dispara os mesmos e-mails do fluxo Jinja (via
    `send_async`, isolável em teste). Retorna a mensagem de sucesso (o adaptador Jinja dá
    `flash`; o adaptador da API a ignora e devolve o evento serializado).

    Args:
        event: O `CalendarEvent` dono do cargo.
        role: O `EventRole` a atualizar (já carregado e pertencente ao evento).
        talent_id: Id do talento (str/int) ou vazio/None para desescalar.
        cache_value: Cachê cru (string pt-BR ou número); parseado aqui via `parse_brl`.
        travel_cache: Adicional de transporte cru; parseado aqui. **Omitir** o argumento
            (sentinela `_UNSET`) mantém o valor gravado — só quem manda a chave escreve nela.
        actor_name: Nome de quem executa (para o log).
        is_superadmin: Se pode ultrapassar o teto de cachê.
        tz: Fuso para timestamps (São Paulo).

    Returns:
        Mensagem de sucesso descrevendo o efeito.
    """
    old_talent_id = role.talent_id
    old_cache_value = role.cache_value
    old_travel_cache = role.travel_cache
    old_invite_status = role.invite_status
    # Feature 239 (decisão 9): a vaga de presença nunca tem valor. A trava fica AQUI porque este
    # é o núcleo dos dois adaptadores (handler Jinja e `POST /api/roles/<id>/assign`) — esconder
    # o campo só na tela deixaria a rota aceitando o valor.
    presenca = e_vaga_de_presenca(role)

    role.talent_id = int(talent_id) if talent_id else None

    new_cache = parse_brl(cache_value)
    # Teto de cachê: casting não ultrapassa o cap do orçamento; superadmin pode (fica no log).
    # Feature 238: se um superadmin JÁ salvou um valor acima do cap neste papel, esse valor é o
    # novo teto efetivo — o casting pode manter/usar até ele. Sem isso, o casting não conseguia
    # nem ESCALAR alguém sem rebaixar o cachê que o dono tinha acabado de subir (caso real do
    # Baile do Addan). O invariante se sustenta: só superadmin consegue deixar salvo um valor
    # acima do cap, porque este mesmo rebaixamento barra todo mundo antes.
    # Feature 239 (carrinho): quem leva o carro fora de SP tem direito à parcela de UM veículo
    # do orçamento POR CIMA do CAP — e o valor pago fica todo em `cache_value` (um número só),
    # para entrar automático na planilha de pagamentos/custo/DRE sem mudar o financeiro.
    parcela_transporte = (
        valor_transporte_papel(event) if role.does_transport else Decimal("0")
    )
    if new_cache is not None and role.cache_cap is not None:
        # A parcela entra DENTRO do `max`, nunca somada por cima dele: como o valor rebaixado é
        # gravado em `cache_value`, ele vira o `old_cache_value` da chamada seguinte — somar a
        # parcela depois do `max` faria cada "Salvar" render mais um degrau do tamanho da parcela
        # (catraca), e um casting comum subiria o cachê sem limite, sem superadmin e sem aviso.
        # Assim o teto vira ponto fixo: salvo `cap + parcela`, o próximo `max` devolve o mesmo
        # número — e o invariante da 238 continua valendo (valor autorizado por superadmin acima
        # de `cap + parcela` segue sendo o piso, sem rebaixamento).
        teto_efetivo = max(role.cache_cap + parcela_transporte, old_cache_value or 0)
        if new_cache > teto_efetivo and not is_superadmin:
            new_cache = teto_efetivo

    if presenca:
        new_cache = None

    role.cache_value = new_cache
    # Sem a guarda do `_UNSET` este trecho apagava o adicional de transporte a cada "Salvar"
    # do casting em React (que nunca manda a chave) — e ainda avisava o talento confirmado de
    # que o transporte tinha virado "não definido".
    if presenca:
        role.travel_cache = None
    elif travel_cache is not _UNSET:
        role.travel_cache = parse_brl(travel_cache)
    new_travel = role.travel_cache
    role.assigned_at = datetime.now(tz=tz) if role.talent_id else None
    if role.talent_id != old_talent_id:
        role.figurino_done_at = None
        role.invite_status = None
    # A presença também não entra no fluxo de pagamento: marcá-la como "a pagar" a colocaria
    # de volta na planilha por outra porta (paridade com `assign_tech_presence`, que só mexe
    # no `talent_id`).
    if role.talent_id and not presenca:
        role.payment_status = "nao_pago"
    # Remoção: avisa o talento trocado, salvo se ele havia recusado voluntariamente. A presença
    # fica de fora: ela nunca convidou ninguém, então "você foi removido do evento" seria um
    # e-mail sobre um convite que não existiu.
    if (
        not presenca
        and old_talent_id
        and old_talent_id != role.talent_id
        and old_invite_status != "rejected"
    ):
        old_talent = Talent.query.get(old_talent_id)
        if old_talent:
            send_async(send_removal_email, old_talent, event, role.character_name)
    db.session.commit()

    # Feature 239 (decisões 9/11): a presença sai daqui sem convite, sem e-mail e sem valor —
    # a designação é tarefa do painel de Ensaio e não convida ninguém para nada.
    if presenca:
        quem = role.talent.full_name if role.talent else None
        message = (
            f"Designou {quem} como {role.character_name} (vaga sem cachê)"
            if quem
            else f"Vaga de {role.character_name} atualizada."
        )
        db.session.add(EventLog(
            event_id=event.id,
            actor_name=actor_name,
            actor_role="Casting",
            message=message,
            created_at=datetime.now(tz=tz),
        ))
        db.session.commit()
        return message

    # Feature 239: o log precisa dizer que aquele cachê carrega a parcela do veículo — sem
    # isso o valor "fora da curva" de quem dirigiu vira um mistério na auditoria.
    transporte_nota = (
        f" (inclui transporte de R$ {format_brl(parcela_transporte)})"
        if parcela_transporte > 0
        else ""
    )
    # A nota de "acima do cap" compara contra o teto EFETIVO (cap + parcela do veículo), não
    # contra o `cache_cap` cru: com o carrinho marcado, `cap + parcela > cap` por construção, e
    # comparar com o cap cru marcaria TODO papel com carrinho como "autorizado pelo admin" —
    # inclusive quando quem salvou foi um casting comum, dentro do limite legítimo. A parcela já
    # é anunciada à parte por `transporte_nota`.
    teto_da_nota = (
        role.cache_cap + parcela_transporte if role.cache_cap is not None else None
    )

    if role.talent_id and role.talent_id != old_talent_id:
        role.invite_status = "pending"
        cap_note = ""
        if teto_da_nota and role.cache_value and role.cache_value > teto_da_nota:
            cap_note = f" (acima do cap de {teto_da_nota}R$ — autorizado pelo admin)"
        message = (
            f"Adicionou {role.talent.full_name} como {role.character_name} "
            f"com cachê de {role.cache_value or 0}R${cap_note}{transporte_nota}"
        )
        db.session.add(EventLog(
            event_id=event.id,
            actor_name=actor_name,
            actor_role="Casting",
            message=message,
            created_at=datetime.now(tz=tz),
        ))
        db.session.commit()
        send_async(send_invite_email, role)
        return message

    if role.talent_id:
        cap_note = ""
        if teto_da_nota and role.cache_value and role.cache_value > teto_da_nota:
            cap_note = f" (acima do cap de {teto_da_nota}R$ — autorizado pelo admin)"
        message = (
            f"Atualizou cachê de {role.talent.full_name} como {role.character_name} "
            f"para {role.cache_value or 0}R${cap_note}{transporte_nota}"
        )
        db.session.add(EventLog(
            event_id=event.id,
            actor_name=actor_name,
            actor_role="Casting",
            message=message,
            created_at=datetime.now(tz=tz),
        ))
        db.session.commit()
        # Notifica talento já confirmado se o cachê/transporte mudou.
        if old_invite_status == "accepted":
            changes = _cache_changes(old_cache_value, new_cache, old_travel_cache, new_travel)
            if changes:
                role.event_changed_at = datetime.now(tz=tz)
                role.change_description = "\n".join(changes)
                db.session.commit()
                send_async(send_event_changed_email, role, changes)
        return message

    # Sem talento (desescalado): confirma que a vaga foi salva (feature 138).
    return f"Vaga de {role.character_name} atualizada."


def _cache_changes(
    old_cache: Any | None, new_cache: Any | None,
    old_travel: Any | None, new_travel: Any | None,
) -> list[str]:
    """Descreve mudanças de cachê/transporte para notificar talento confirmado (como no Jinja)."""
    changes: list[str] = []
    if new_cache != old_cache:
        old_fmt = f"R$ {old_cache:,.0f}" if old_cache else "não definido"
        new_fmt = f"R$ {new_cache:,.0f}" if new_cache else "não definido"
        changes.append(f"Cachê: {old_fmt} → {new_fmt}")
    if new_travel != old_travel:
        old_fmt = f"R$ {old_travel:,.0f}" if old_travel else "não definido"
        new_fmt = f"R$ {new_travel:,.0f}" if new_travel else "não definido"
        changes.append(f"Adicional de transporte: {old_fmt} → {new_fmt}")
    return changes


def _parcela_veiculo_do_orcamento(event: Any) -> Decimal | None:
    """Parcela de UM veículo (só a rodagem) recalculada do orçamento que gerou o evento.

    Mesmo caminho de `_build_orcamento_prefill` (`app/calendar/routes.py`): relê o
    `form_snapshot` e chama `calcular_van`/`calcular_carro`, mas fica só com `tb["transporte"]`
    — a rodagem do veículo. O `adicional_fora_sp` (km×2÷3 **por pessoa**) fica DE FORA de
    propósito: ele já está somado dentro do `cache_cap` de todo mundo (`_compute_performer_caches`),
    e pagá-lo de novo ao motorista seria pagar duas vezes o mesmo adicional.

    Com `transporte_tipo="carro"` e `num_carros>1`, `tb["transporte"]` é a soma dos carros —
    dividimos por `num_carros` para chegar à parcela de UM (decisão 3: cada marcado dirige um).

    Args:
        event: O `CalendarEvent` (precisa de `orcamento_history_id`).

    Returns:
        A parcela de um veículo, ou `None` quando não dá para recalcular (evento sem orçamento,
        orçamento apagado, snapshot sem fora-SP ou sem quilometragem) — aí o chamador cai no
        próximo degrau da cascata.
    """
    from app.models import OrcamentoHistory
    from app.orcamento.transport import calcular_carro, calcular_van

    if not getattr(event, "orcamento_history_id", None):
        return None
    entry = OrcamentoHistory.query.get(event.orcamento_history_id)
    if entry is None:
        return None

    try:
        snap = json.loads(entry.form_snapshot or "{}")
    except (TypeError, ValueError):
        return None
    if not snap.get("fora_sp"):
        return None
    if snap.get("deslocamento_responsavel") == "cliente":
        # A contratante assumiu o deslocamento: nenhum veículo da Manto roda, então o carrinho
        # vale zero POR DECISÃO do orçamento — não é "sem base de cálculo" (None), que cairia
        # na estimativa por km e pagaria um motorista por uma viagem que a cliente provê.
        return Decimal("0.00")

    # `km_ida` é a distância de IDA. Snapshots v1 guardavam só `kmT` (ida e volta) e repopular
    # o campo de ida com ele dobrava o transporte (histórico da migration a3f7c19d5e02) — por
    # isso só derivamos `kmT/2` quando `km_ida` não existe mesmo.
    km_ida = float(snap.get("km_ida") or 0)
    if km_ida <= 0 and snap.get("kmT"):
        km_ida = float(snap.get("kmT") or 0) / 2
    if km_ida <= 0:
        return None

    num_carros = max(int(float(snap.get("num_carros") or 1)), 1)
    num_colaboradores = max(int(float(snap.get("num_colaboradores") or 1)), 1)
    if snap.get("transporte_tipo", "van") == "van":
        tabela = calcular_van(
            num_colaboradores, km_ida, bool(snap.get("carretinha", False)), entry.has_show
        )
        parcela = Decimal(str(tabela["transporte"]))
    else:
        tabela = calcular_carro(num_carros, num_colaboradores, km_ida, entry.has_show)
        parcela = Decimal(str(tabela["transporte"])) / Decimal(num_carros)
    return parcela.quantize(_CENTAVOS)


def valor_transporte_papel(event: Any) -> Decimal:
    """Quanto vale, para UM integrante marcado com o carrinho, levar o veículo (feature 239).

    É sempre a parcela de **um** veículo — o mesmo número para todos os papéis do evento, porque
    cada marcado leva um carro (decisão 3). Cascata de fontes, da mais fiel à mais grosseira:

    1. orçamento que gerou o evento (`orcamento_history_id`) — recálculo da rodagem; qualquer
       parcela vinda daqui é final, inclusive o zero deliberado de um orçamento com
       `deslocamento_responsavel == "cliente"` (a contratante leva o elenco);
    2. `km de ida × 2 × tarifa do carro` (a mesma sugestão que a tela Jinja antiga fazia);
    3. zero.

    **`event.transport_value` NUNCA entra nesta conta** (decisão 1). Aquele campo é o transporte
    VENDIDO: `_build_orcamento_prefill` o grava como `tb["total"]`, ou seja rodagem de TODOS os
    carros + `adicional_fora_sp` (que já está somado dentro do `cache_cap` de todo mundo, por
    `_compute_performer_caches`) + adicional de show — e, em evento lançado à mão, ainda com a
    margem de venda. Usá-lo pagaria o adicional fora-SP duas vezes e daria a um único motorista a
    frota inteira.

    O degrau 2 aplica a tarifa de CARRO mesmo quando o evento foi orçado com van (6,30/5,50): é
    aproximação conservadora **deliberada** (carro é a tarifa mais barata), não esquecimento — não
    "conserte" isto somando o adicional fora-SP de volta. `travel_distance_km` é a distância de
    IDA (ver `app/models.py`), por isso o ×2 para ida e volta.

    Args:
        event: O `CalendarEvent` do papel.

    Returns:
        O valor em reais, sempre `Decimal("0.00")` quando o evento não é fora de SP (dentro de
        SP não existe carrinho — decisão 4) ou quando não há nenhuma base de cálculo — sem base,
        zero mesmo: a decisão 1 não autoriza inventar valor (a tela avisa "sem base de cálculo").
    """
    zero = Decimal("0.00")
    if event is None or not getattr(event, "is_outside_sp", False):
        return zero

    # Parcela não-None do orçamento sempre curto-circuita — inclusive o ZERO deliberado do
    # deslocamento por conta da contratante, que não pode cair no degrau 2 (a estimativa por
    # km pagaria um motorista por uma viagem que a cliente provê).
    parcela = _parcela_veiculo_do_orcamento(event)
    if parcela is not None:
        return parcela if parcela > 0 else zero

    if getattr(event, "travel_distance_km", None):
        from app.orcamento import settings as orcamento_settings

        tarifa = Decimal(str(orcamento_settings.load()["transporte"]["carro_por_km"]))
        km_ida = Decimal(str(event.travel_distance_km))
        return (km_ida * 2 * tarifa).quantize(_CENTAVOS)

    return zero


def set_transporte(
    event: Any, role: Any, *, faz_transporte: bool, actor_name: str, tz: ZoneInfo
) -> None:
    """Marca/desmarca o integrante como responsável pelo transporte fora de SP (feature 239).

    Só muda o marcador: o valor não é gravado em lugar nenhum aqui. Quem soma a parcela do
    veículo é o teto de `assign_role` — o pagamento continua sendo um número só em
    `cache_value` (decisão 2), então planilha de pagamentos, custo, DRE e KPI seguem intactos.
    Idempotente. A guarda de "só fora de SP" fica no adaptador (a view), como a RBAC.

    Args:
        event: O `CalendarEvent` dono do cargo.
        role: O `EventRole` a marcar.
        faz_transporte: True marca, False desmarca.
        actor_name: Nome de quem executa (para o log).
        tz: Fuso para timestamps (São Paulo).
    """
    if bool(role.does_transport) == faz_transporte:
        return
    role.does_transport = True if faz_transporte else None
    quem = role.talent.full_name if role.talent else role.character_name
    verbo = "Marcou" if faz_transporte else "Desmarcou"
    db.session.add(EventLog(
        event_id=event.id,
        actor_name=actor_name,
        actor_role="Casting",
        message=f"{verbo} {quem} como responsável pelo transporte",
        created_at=datetime.now(tz=tz),
    ))
    db.session.commit()


def add_role(
    event: Any,
    *,
    character_name: str,
    talent_id: Any,
    cache_value: Any,
    role_type: str,
    actor_name: str,
    tz: ZoneInfo,
) -> Any:
    """Adiciona um cargo ao evento (com ou sem talento). Núcleo de `_handle_add_role`.

    Cachê via `parse_brl` (Princípio VII — harmoniza com `assign_role`; o handler antigo usava
    `int()`, agora aceita decimais pt-BR). Se tem talento: `invite_status=pending` + convite.

    Returns:
        O `EventRole` criado.
    """
    from app.models import EventRole

    role = EventRole(event_id=event.id, character_name=character_name, role_type=role_type or "character")
    # Feature 239 (decisão 9): recriar a vaga de presença pelo "Adicionar pessoa" não pode ser a
    # porta dos fundos do cachê — sem valor, sem transporte e sem convite, como no `assign_role`.
    presenca = e_vaga_de_presenca(role)
    if talent_id:
        role.talent_id = int(talent_id)
        role.assigned_at = datetime.now(tz=tz)
        if not presenca:
            role.invite_status = "pending"
    role.cache_value = None if presenca else parse_brl(cache_value)
    if presenca:
        role.travel_cache = None
    db.session.add(role)
    db.session.flush()
    talent_name = role.talent.full_name if role.talent else None
    if talent_name and presenca:
        mensagem = f"Adicionou {talent_name} como {role.character_name} (vaga sem cachê)"
    elif talent_name:
        mensagem = (
            f"Adicionou {talent_name} como {role.character_name} "
            f"com um cachê de {role.cache_value or 0} reais"
        )
    else:
        mensagem = f"Adicionou função: {role.character_name}"
    db.session.add(EventLog(
        event_id=event.id,
        actor_name=actor_name,
        actor_role="Casting",
        message=mensagem,
        created_at=datetime.now(tz=tz),
    ))
    db.session.commit()
    if role.talent_id and not presenca:
        send_async(send_invite_email, role)
    return role


def delete_role(
    event: Any, role: Any, *, is_superadmin: bool, actor_name: str, tz: ZoneInfo
) -> bool:
    """Remove um cargo. Núcleo de `_handle_delete_role`. Cargo com convite aceito só sai por
    superadmin (retorna False sem remover, nesse caso).

    Returns:
        True se removeu; False se bloqueado (convite aceito e não-superadmin).
    """
    if role.invite_status == "accepted" and not is_superadmin:
        return False
    db.session.add(EventLog(
        event_id=event.id,
        actor_name=actor_name,
        actor_role="Casting",
        message=f"Removeu vaga: {role.character_name}",
        created_at=datetime.now(tz=tz),
    ))
    db.session.delete(role)
    db.session.commit()
    return True


def send_invite(event: Any, role: Any, *, actor_name: str, tz: ZoneInfo) -> bool:
    """Reenvia o convite de um cargo com talento. Núcleo de `_handle_send_invite` (US3, feat. 148).

    Marca `invite_status=pending`, registra em `EventLog` e envia o convite de forma **síncrona**
    (`send_invite_email`, como o Jinja de hoje — não `send_async`), para o comportamento
    observável não mudar. Cargo sem talento é no-op (retorna False), igual ao handler atual.

    Returns:
        True se o e-mail foi enviado; False se não havia talento (no-op) ou o envio falhou.
    """
    if not role.talent_id:
        return False
    role.invite_status = "pending"
    db.session.add(EventLog(
        event_id=event.id,
        actor_name=actor_name,
        actor_role="Casting",
        message=f"Enviou convite para {role.talent.full_name} ({role.character_name})",
        created_at=datetime.now(tz=tz),
    ))
    db.session.commit()
    return send_invite_email(role)


def convidar_recem_escalados(
    event: Any,
    assigned_now: list[tuple[int, str]],
    *,
    actor_name: str,
    tz: ZoneInfo,
) -> int:
    """Convida quem acabou de ser pré-escalado na criação/edição do evento (feature 233).

    A tela de casting já convidava sozinha ao escalar (`assign_talent_to_role`), mas os dois
    caminhos que montam o elenco **junto com o evento** — `_create_roles_from_input` /
    `_apply_default_roles` na criação e `_reconcile_characters` na edição — gravavam o
    `talent_id` e paravam ali. O cargo nascia com pessoa e **sem convite** (`invite_status =
    NULL`), e nenhuma tela pedia a alguém para clicar em "Convidar".

    O efeito era invisível dos dois lados: para a produção, o cargo parecia resolvido; para a
    pessoa, o evento não existia (o portal só listava convite aceito ou pendente). Foi assim que
    uma coordenadora chegou ao evento 1192 sem conseguir abrir as fichas de figurino, e é a origem
    dos 26 cargos futuros sem convite que a 231 encontrou.

    **Não exige cachê preenchido.** A pré-escala do coordenador não tem campo de cachê — exigir o
    valor deixaria de fora exatamente o caso que originou isto. É a mesma regra da tela de casting,
    que também convida sem olhar o cachê; o e-mail de convite simplesmente omite a linha do valor
    quando ele ainda não existe.

    Args:
        event: Evento recém-criado ou editado.
        assigned_now: Pares `(talent_id, character_name)` de quem ACABOU de ser escalado — a mesma
            lista que os dois caminhos já montavam para avisar de conflito de horário.
        actor_name: Quem executou (vai para o `EventLog`).
        tz: Fuso de São Paulo.

    Returns:
        Quantos convites saíram.
    """
    if not assigned_now:
        return 0

    # Evento que já aconteceu não gera convite: "confirme sua presença" para um show da semana
    # passada é ruído, e a edição de evento antigo é rotina (ajuste de cachê, troca de ficha).
    fim = event.end_at or event.start_at
    if fim and fim < datetime.now(tz=tz).replace(tzinfo=None):
        return 0

    # Guarda os cargos que ESTE chamada marcou, e só esses recebem e-mail. Reconsultar por
    # `invite_status == "pending"` depois do commit pegaria também quem já estava convidado antes —
    # e reenviar convite a cada edição de evento é justamente o spam que não se quer.
    marcados: list[Any] = []
    for talent_id, character_name in assigned_now:
        role = EventRole.query.filter_by(
            event_id=event.id, talent_id=talent_id, character_name=character_name
        ).first()
        # Só o cargo sem convite nenhum: quem já está `pending`, `accepted` ou `rejected` não pode
        # ser reiniciado por uma edição de evento.
        if role is None or role.invite_status is not None or not role.talent:
            continue
        role.invite_status = "pending"
        db.session.add(EventLog(
            event_id=event.id,
            actor_name=actor_name,
            actor_role="Casting",
            message=(
                f"Convite automático para {role.talent.full_name} ({character_name}) "
                "ao ser escalado no evento"
            ),
            created_at=datetime.now(tz=tz),
        ))
        marcados.append(role)

    if marcados:
        db.session.commit()
        # `send_async` só depois do commit: e-mail de convite para escalação que não persistiu
        # seria pior que convite faltando.
        for role in marcados:
            send_async(send_invite_email, role)
    return len(marcados)


def set_figurino_done(event: Any, role: Any, *, actor_name: str, tz: ZoneInfo) -> None:
    """Marca o figurino de um cargo como separado. Núcleo de `_handle_figurino_done` (feat. 148).

    Ação de Figurino (não de casting): a RBAC (Figurino/superadmin) é aplicada nos adaptadores.
    """
    role.figurino_done_at = datetime.now(tz=tz)
    db.session.add(EventLog(
        event_id=event.id,
        actor_name=actor_name,
        actor_role="Figurino",
        message=f"Separou figurino de {role.character_name}",
        created_at=datetime.now(tz=tz),
    ))
    db.session.commit()


def dismiss_role(role: Any, *, actor_name: str, dismissed_by: int) -> bool:
    """Dispensa um cargo sem talento sem excluí-lo (feature 108). Núcleo de `dismiss_role`.

    O cargo continua existindo (o sync do Google nunca o recria) mas para de contar como tarefa
    pendente. Só cargos **sem talento** podem ser dispensados. Usa `datetime.utcnow()` (naive) e
    `dismissed_by` como o fluxo Jinja atual. Idempotente: já dispensado retorna True sem duplicar.

    Returns:
        True se o cargo foi (ou já estava) dispensado; False se tem talento (bloqueado).
    """
    if role.talent_id is not None:
        return False
    if role.dismissed_at is None:
        role.dismissed_at = datetime.utcnow()
        role.dismissed_by = dismissed_by
        db.session.add(EventLog(
            event_id=role.event_id,
            actor_name=actor_name,
            actor_role="Casting",
            message=f"Dispensou tarefa de casting: {role.character_name}",
            created_at=datetime.utcnow(),
        ))
        db.session.commit()
    return True


def restore_role(role: Any, *, actor_name: str) -> None:
    """Reverte a dispensa de um cargo, voltando a contá-lo como pendente. Núcleo de `restore_role`.

    Idempotente: cargo não dispensado é no-op.
    """
    if role.dismissed_at is not None:
        role.dismissed_at = None
        role.dismissed_by = None
        db.session.add(EventLog(
            event_id=role.event_id,
            actor_name=actor_name,
            actor_role="Casting",
            message=f"Restaurou tarefa de casting: {role.character_name}",
            created_at=datetime.utcnow(),
        ))
        db.session.commit()
