"""Orçamento → evento: vincular e aplicar o que foi vendido (feature 273).

O orçamento já sabe tudo que o evento precisa saber sobre a venda — se é fora de SP (e quantos km),
quantos coordenadores foram vendidos, quem vai maquiado, se tem show (técnico de som), os tetos de
cachê por papel. A criação a partir do orçamento (`_create_event_core`, feature 152/239) aproveita
quase tudo isso; o que ficava de fora era o "fora de SP" (só o endereço classificava), e o evento
que nasce fora do fluxo — importado do Google Calendar, o caminho comum de quem marca a data no
celular e orça depois — não recebia **nada**: 44 dos 104 eventos futuros em 02/09/2026.

Este módulo é a fonte única de "o que o orçamento diz e como isso entra no evento", usada pela
criação, pelo vínculo posterior (`PATCH /api/events/<id>/orcamento`) e pela reclassificação
dentro/fora de SP. Puro no sentido da constituição: nada de `flask.request`; quem chama comita.

Regras que valem em todo caminho:

- **Nunca apaga nem rebaixa.** Aplicar a equipe cria o que falta (coordenadores até a quantidade
  vendida, maquiador, técnico de som) e marca maquiagem/cantor/teto em personagens que ainda não
  tinham — jamais remove uma vaga, desmarca maquiagem ou reduz um teto que alguém já subiu.
- **Personagem casa por nome normalizado** (sem acento, sem caixa, sem espaços duplicados). O que
  não casa é devolvido no relatório (`nao_casados`) para a tela dizer, em vez de inventar vaga:
  o evento do Google já tem o elenco pelo título, e um "Mickey que fala" do orçamento não pode
  virar um segundo Mickey.
- **Valores só em evento sem venda** (decisão D1 do plano das ondas): com venda digitada, o vínculo
  é rastro; os valores ficam como a comercial deixou.
"""

from __future__ import annotations

import json
import logging
import unicodedata
from datetime import datetime
from decimal import Decimal
from typing import Any

from app import db
from app.models import CalendarEvent, EventLog, EventRole, OrcamentoHistory

logger = logging.getLogger(__name__)

DURACOES_TABELA = (1, 2, 3, 4)


class OrcamentoJaVinculado(Exception):
    """O orçamento já está preso a outro evento não cancelado (1:1 entre vivos)."""

    def __init__(self, event_id: int) -> None:
        super().__init__(f"orçamento já vinculado ao evento {event_id}")
        self.event_id = event_id


# ── leitura do orçamento ───────────────────────────────────────────────────────────────────────

def snapshot_do_orcamento(entry: OrcamentoHistory) -> dict:
    """`form_snapshot` como dict; `{}` quando ausente ou corrompido (registros legados)."""
    try:
        return json.loads(entry.form_snapshot or "{}") or {}
    except (TypeError, ValueError):
        return {}


def _km_ida(snap: dict) -> float:
    """Km de ida do orçamento; snapshots v1 só tinham `kmT` (ida e volta) — ver `casting_ops`."""
    km = float(snap.get("km_ida") or 0)
    if km <= 0 and snap.get("kmT"):
        km = float(snap.get("kmT") or 0) / 2
    return km


def resumo_do_orcamento(entry: OrcamentoHistory) -> dict:
    """O que o orçamento vendeu, na forma que a aba Comercial mostra (chips) e o vínculo aplica."""
    snap = snapshot_do_orcamento(entry)
    performers = snap.get("performers", []) or []
    return {
        "id": entry.id,
        "client_name": entry.client_name or "",
        "event_date": entry.event_date or "",
        "event_location": entry.event_location or "",
        "fora_sp": bool(snap.get("fora_sp")),
        "km_ida": _km_ida(snap) if snap.get("fora_sp") else 0,
        "deslocamento_cliente": snap.get("deslocamento_responsavel") == "cliente",
        "coordenador_qty": max(int(snap.get("coordenador_qty", 1) or 1), 0),
        "maquiagens": sum(1 for p in performers if p.get("makeup")),
        "cantores": sum(
            1 for p in performers
            if p.get("type") == "cantor" or p.get("subtipo") == "cantor" or p.get("cantor")
        ),
        "personagens": [
            ((p.get("nome") or p.get("personagem") or "").strip()) for p in performers
        ],
        "has_show": bool(entry.has_show),
        "total_1h": float(entry.total_1h or 0),
        "total_2h": float(entry.total_2h or 0),
        "total_3h": float(entry.total_3h or 0),
        "total_4h": float(entry.total_4h or 0),
    }


# ── fora de SP ─────────────────────────────────────────────────────────────────────────────────

def aplicar_fora_sp_do_orcamento(event: Any, entry: OrcamentoHistory | None) -> bool:
    """Se o orçamento foi feito com "evento fora de São Paulo", o evento é fora de SP.

    A caixinha é a palavra da comercial na hora da venda — vale mais que o endereço (que muitas
    vezes é só "Buffet X"). A quilometragem do orçamento vira a distância do evento quando ele
    ainda não tem nenhuma: é a base da parcela do veículo no teto do carrinho (239). Um orçamento
    SEM a caixinha não diz nada (pode ter sido esquecida): não rebaixa para "dentro".

    Returns:
        ``True`` quando o orçamento manda fora de SP — e o evento ficou (ou já estava) assim. É
        "o que o orçamento diz", não "o que mudou nesta chamada": quem reclassifica pelo endereço
        usa este retorno para NÃO rebaixar um evento que a caixinha já decidiu (a primeira versão
        devolvia "mudou", e o segundo retoque de endereço derrubava o fora de SP).
    """
    if entry is None:
        return False
    snap = snapshot_do_orcamento(entry)
    if not snap.get("fora_sp"):
        return False
    event.is_outside_sp = True
    km = _km_ida(snap)
    if km > 0 and not event.travel_distance_km:
        event.travel_distance_km = km
    return True


# ── equipe ────────────────────────────────────────────────────────────────────────────────────

def _chave(nome: str | None) -> str:
    """Nome de papel comparável: sem acento, sem caixa, sem espaços repetidos."""
    texto = unicodedata.normalize("NFD", (nome or "").strip())
    texto = "".join(ch for ch in texto if not unicodedata.combining(ch))
    return " ".join(texto.casefold().split())


def _duracao_do_evento(event: Any) -> int:
    """Horas do evento pela agenda (1..N), como a criação faz com `duracao`."""
    if not event.start_at or not event.end_at:
        return 1
    horas = (event.end_at - event.start_at).total_seconds() / 3600
    return max(1, int(round(horas)))


def _chave_cache(duracao: int) -> str:
    return "cache_custom" if duracao > 4 else f"cache_{duracao}h"


def _cap_e_nota(item: dict, chave: str) -> tuple[Any, Any]:
    cap = item.get(chave)
    notas = item.get("cap_notes")
    nota = notas.get(chave) if isinstance(notas, dict) and cap is not None else None
    return cap, nota


def aplicar_equipe_do_orcamento(event: Any, entry: OrcamentoHistory) -> dict:
    """Cria o que o orçamento vendeu e o evento não tem; marca o que o evento tem e não sabia.

    Personagens (por nome normalizado): `needs_makeup`/`is_singer` viram True quando o orçamento
    diz; `cache_cap`/`cache_cap_note` entram só onde não havia teto. Apoio: coordenadores até a
    quantidade vendida, "Técnico de Som" quando o orçamento tem show, "Maquiador" quando alguém
    vai maquiado — cada um com o teto da duração real do evento. Nada é removido ou rebaixado.

    Returns:
        Relatório para a tela e para o log: contagens e a lista de personagens do orçamento que
        não acharam papel no evento.
    """
    from app.calendar.routes import _compute_performer_caches

    snap = snapshot_do_orcamento(entry)
    duracao = _duracao_do_evento(event)
    chave = _chave_cache(duracao)
    itens = _compute_performer_caches(snap, horas_extra=duracao if duracao > 4 else None)
    papeis = list(event.roles)
    relatorio = {
        "personagens_casados": 0, "nao_casados": [], "maquiagem_marcada": 0,
        "cantor_marcado": 0, "tetos_aplicados": 0, "coordenadores_criados": 0,
        "tecnico_criado": False, "maquiador_criado": False, "duracao": duracao,
    }

    # Personagens: cada item do orçamento casa com no máximo um papel ainda livre.
    livres = [r for r in papeis if r.role_type != "extra"]
    for item in itens:
        if (item.get("role_type") or "character") != "character":
            continue
        alvo = next((r for r in livres if _chave(r.character_name) == _chave(item.get("label"))), None)
        if alvo is None:
            relatorio["nao_casados"].append((item.get("label") or "").strip())
            continue
        livres.remove(alvo)
        relatorio["personagens_casados"] += 1
        if item.get("needs_makeup") and not alvo.needs_makeup:
            alvo.needs_makeup = True
            relatorio["maquiagem_marcada"] += 1
        if item.get("is_singer") and not alvo.is_singer:
            alvo.is_singer = True
            relatorio["cantor_marcado"] += 1
        cap, nota = _cap_e_nota(item, chave)
        if cap is not None and alvo.cache_cap is None:
            alvo.cache_cap = cap
            alvo.cache_cap_note = nota
            relatorio["tetos_aplicados"] += 1

    extras = [i for i in itens if (i.get("role_type") or "character") == "extra"]
    apoio = [r for r in papeis if r.role_type == "extra"]

    # Coordenadores: até a quantidade vendida (o `_ensure_coordinator` da criação garante 1).
    coord_itens = [i for i in extras if _chave(i.get("label")).startswith("coordenador")]
    coord_existentes = [r for r in apoio if _chave(r.character_name).startswith("coordenador")]
    faltam = len(coord_itens) - len(coord_existentes)
    for item in coord_itens[:max(faltam, 0)]:
        cap, nota = _cap_e_nota(item, chave)
        db.session.add(EventRole(
            event_id=event.id, character_name="Coordenador", role_type="extra",
            cache_cap=cap, cache_cap_note=nota,
        ))
        relatorio["coordenadores_criados"] += 1
    for item, role in zip(coord_itens, coord_existentes, strict=False):
        cap, nota = _cap_e_nota(item, chave)
        if cap is not None and role.cache_cap is None:
            role.cache_cap, role.cache_cap_note = cap, nota
            relatorio["tetos_aplicados"] += 1

    # Técnico de som e maquiador: uma vaga cada, só se o orçamento vendeu e o evento não tem.
    for rotulo, marcador, chave_relatorio in (
        ("Técnico de Som", "tecnico de som", "tecnico_criado"),
        ("Maquiador", "maquiad", "maquiador_criado"),
    ):
        item = next((i for i in extras if _chave(i.get("label")) == _chave(rotulo)), None)
        if item is None:
            continue
        existente = next(
            (r for r in apoio if marcador in _chave(r.character_name) and "presenca" not in _chave(r.character_name)),
            None,
        )
        cap, nota = _cap_e_nota(item, chave)
        if existente is None:
            db.session.add(EventRole(
                event_id=event.id, character_name=rotulo, role_type="extra",
                cache_cap=cap, cache_cap_note=nota,
            ))
            relatorio[chave_relatorio] = True
        elif cap is not None and existente.cache_cap is None:
            existente.cache_cap, existente.cache_cap_note = cap, nota
            relatorio["tetos_aplicados"] += 1
    return relatorio


def _frase_relatorio(rel: dict) -> str:
    partes = []
    if rel.get("coordenadores_criados"):
        partes.append(f"+{rel['coordenadores_criados']} coordenador(es)")
    if rel.get("maquiador_criado"):
        partes.append("maquiador criado")
    if rel.get("tecnico_criado"):
        partes.append("técnico de som criado")
    if rel.get("maquiagem_marcada"):
        partes.append(f"maquiagem em {rel['maquiagem_marcada']} personagem(ns)")
    if rel.get("cantor_marcado"):
        partes.append(f"cantor em {rel['cantor_marcado']}")
    if rel.get("tetos_aplicados"):
        partes.append(f"teto em {rel['tetos_aplicados']} papel(is)")
    if rel.get("fora_sp"):
        partes.append("fora de SP")
    if rel.get("valores"):
        partes.append(f"valores de {rel['valores']}h aplicados")
    return ", ".join(partes) if partes else "nada a aplicar (já estava tudo lá)"


# ── valores ───────────────────────────────────────────────────────────────────────────────────

def aplicar_valores_do_orcamento(event: Any, entry: OrcamentoHistory, *, duracao: int, sale_date=None) -> bool:
    """Venda, transporte e nota fiscal do orçamento para a duração escolhida — só em evento SEM venda.

    Os totais vêm de `_build_orcamento_prefill` (a mesma conta da tela de criação: transporte
    fora-SP, deslocamento por conta da cliente, acréscimo legado). Com venda já digitada não
    mexe (D1 do plano das ondas): quem chama decide se avisa.

    Returns:
        ``True`` quando aplicou.
    """
    from app.calendar.event_ops import resolver_data_da_venda
    from app.calendar.routes import _build_orcamento_prefill

    if event.sale_value or getattr(event, "is_cortesia_permuta", False):
        # Cortesia/permuta grava venda 0 de propósito — não é "sem venda".
        return False
    if duracao not in DURACOES_TABELA:
        # A régua acima de 4h só existe na criação (que recalcula os cachês para a duração real);
        # o `total_custom` do prefill usa o `duracao_custom` gravado no orçamento, não a pedida.
        return False
    pre = _build_orcamento_prefill(entry.id)
    total = pre.get(f"total_{duracao}h") or 0
    if not total:
        return False
    valor = Decimal(str(total)).quantize(Decimal("0.01"))
    event.sale_value = valor
    event.sale_value_gross = valor
    event.transport_value = Decimal(str(pre.get("transport_value") or 0))
    event.acrescimo_value = Decimal(str(pre.get("acrescimo_value") or 0))
    event.with_invoice = bool(pre.get("with_invoice"))
    event.sale_date = resolver_data_da_venda(sale_date, valor, None, event.sale_date)
    # Acréscimos tipados (BV etc.) nascem junto, como na criação a partir do orçamento — senão
    # dois eventos vendidos pelo mesmo orçamento teriam BV diferente conforme o caminho.
    from app.calendar.routes import _criar_acrescimos_do_orcamento

    _criar_acrescimos_do_orcamento(event, pre.get("acrescimos") or [])
    return True


# ── o vínculo ─────────────────────────────────────────────────────────────────────────────────

def outro_evento_vivo_do_orcamento(entry_id: int, *, exceto_event_id: int | None) -> CalendarEvent | None:
    """Evento não cancelado que já aponta para este orçamento (1:1 entre vivos)."""
    q = CalendarEvent.query.filter(
        CalendarEvent.orcamento_history_id == entry_id, CalendarEvent.cancelled_at.is_(None)
    )
    if exceto_event_id is not None:
        q = q.filter(CalendarEvent.id != exceto_event_id)
    return q.first()


def desvincular_eventos_cancelados(entry_id: int, *, actor_name: str, tz: Any) -> list[int]:
    """Solta o FK dos eventos CANCELADOS que ainda apontam para o orçamento (antes de apagá-lo).

    "Cancelar libera o orçamento" (decisão 5) — mas a 224 mantém a linha cancelada, e a FK sem
    `ondelete` estourava `IntegrityError` no DELETE mesmo sem evento vivo. Cada evento solto
    ganha uma linha no histórico; sem commit.
    """
    soltos: list[int] = []
    cancelados = CalendarEvent.query.filter(
        CalendarEvent.orcamento_history_id == entry_id, CalendarEvent.cancelled_at.isnot(None)
    ).all()
    for ev in cancelados:
        ev.orcamento_history_id = None
        db.session.add(EventLog(
            event_id=ev.id, actor_name=actor_name, actor_role="Comercial",
            message=f"Orçamento #{entry_id} excluído do histórico; vínculo desfeito (evento cancelado)",
            created_at=datetime.now(tz=tz),
        ))
        soltos.append(ev.id)
    return soltos


def set_event_orcamento(
    event: Any,
    entry: OrcamentoHistory | None,
    *,
    actor_name: str,
    tz: Any,
    aplicar_equipe: bool = True,
    aplicar_valores_duracao: int | None = None,
    sale_date=None,
    sincronizar_comissao: Any = None,
) -> dict:
    """Vincula (ou desvincula, com ``entry=None``) o orçamento e aplica o que foi vendido. Não comita.

    Args:
        event: O `CalendarEvent` alvo (já sem satélite — a view recusa antes).
        entry: O orçamento, ou ``None`` para desvincular (só solta o FK; nada mais muda).
        actor_name: Quem executa, para o `EventLog`.
        tz: Fuso do carimbo do log.
        aplicar_equipe: Aplica fora de SP + equipe (padrão). Pode ser chamado de novo no mesmo
            orçamento: é idempotente, só cria/marca o que falta.
        aplicar_valores_duracao: 1..4 (tabela) para aplicar venda/transporte/nota/acréscimos em
            evento **sem venda** (cortesia/permuta conta como venda); ``None`` não mexe em valores.
        sale_date: Data da venda a gravar quando os valores forem aplicados (``None`` = hoje SP).
        sincronizar_comissao: Injetado pela view (mesmo arranjo da 267) — chamado quando os
            valores mudaram, para a linha de comissão nascer junto.

    Returns:
        Relatório (contagens, `nao_casados`, `fora_sp`, `valores`) — vai para a resposta da API.

    Raises:
        OrcamentoJaVinculado: outro evento não cancelado já aponta para o orçamento.
    """
    if entry is None:
        anterior = event.orcamento_history_id
        event.orcamento_history_id = None
        if anterior:
            db.session.add(EventLog(
                event_id=event.id, actor_name=actor_name, actor_role="Comercial",
                message=f"Desvinculou o orçamento #{anterior}", created_at=datetime.now(tz=tz),
            ))
        return {"desvinculado": anterior, "frase": "orçamento desvinculado"}

    outro = outro_evento_vivo_do_orcamento(entry.id, exceto_event_id=event.id)
    if outro is not None:
        raise OrcamentoJaVinculado(outro.id)

    novo_vinculo = event.orcamento_history_id != entry.id
    event.orcamento_history_id = entry.id
    relatorio: dict = {"vinculado": entry.id, "novo_vinculo": novo_vinculo}

    if aplicar_equipe:
        relatorio["fora_sp"] = aplicar_fora_sp_do_orcamento(event, entry)
        relatorio.update(aplicar_equipe_do_orcamento(event, entry))
    if aplicar_valores_duracao:
        if aplicar_valores_do_orcamento(event, entry, duracao=aplicar_valores_duracao, sale_date=sale_date):
            relatorio["valores"] = aplicar_valores_duracao
            if sincronizar_comissao is not None:
                db.session.flush()
                sincronizar_comissao(event)
        else:
            if event.sale_value:
                relatorio["valores_ignorados"] = "evento já tem venda"
            elif getattr(event, "is_cortesia_permuta", False):
                relatorio["valores_ignorados"] = "evento é cortesia/permuta"
            elif aplicar_valores_duracao not in DURACOES_TABELA:
                relatorio["valores_ignorados"] = "duração fora da tabela (1h a 4h)"
            else:
                relatorio["valores_ignorados"] = "orçamento sem total"

    quem = entry.client_name or "sem cliente"
    prefixo = "Vinculou o orçamento" if novo_vinculo else "Reaplicou o orçamento"
    relatorio["frase"] = _frase_relatorio(relatorio)
    db.session.add(EventLog(
        event_id=event.id, actor_name=actor_name, actor_role="Comercial",
        message=f"{prefixo} #{entry.id} ({quem}, {entry.event_date or 'sem data'}): {relatorio['frase']}",
        created_at=datetime.now(tz=tz),
    ))
    return relatorio
