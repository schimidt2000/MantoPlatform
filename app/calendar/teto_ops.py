"""Teto do cachê de uma vaga: efetivo, autorizado pelo Superadmin e recalculado (feature 339).

Fonte única das três perguntas que antes moravam espalhadas em `casting_ops.assign_role` e em
`agenda_read._serialize_role` (o mesmo `max` escrito duas vezes):

- **Qual é o limite desta vaga agora?** (`teto_efetivo`) — o maior entre o teto do orçamento com a
  parcela do carrinho (239), o teto que o Superadmin autorizou para a VAGA (339) e o cachê já salvo da
  pessoa atual (238: quem só reabre o card não vê o cachê de hoje rebaixado).
- **O Superadmin acabou de autorizar algo?** (`gravar_teto_autorizado`) — o valor acima do limite vira
  teto da vaga, com autor e data, e não depende mais do cachê da pessoa: tirar e pôr outro artista
  não o apaga (o caso do evento 1423).
- **O evento virou (ou deixou de ser) SHOW: qual o teto novo?** (`recalcular_tetos_pelo_tipo`) — a
  mesma conta da criação, com o "show" ligado ou desligado.

Módulo puro: nada de `flask.request` nem `current_user`; autor e relógio entram por parâmetro.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any

from app.money import format_brl

#: Tipos de performer cujo preço muda com o "show" na tabela. O "cantor" avulso é sempre show
#: (`_compute_performer_caches` força `show=True`), então não entra.
TIPOS_COM_SHOW = ("ator", "especial")


@dataclass(frozen=True)
class MudancaDeTeto:
    """Um teto que o recálculo mudou — vai para o `EventLog` e para o texto do aviso."""

    role_id: int
    personagem: str
    antes: Decimal | None
    depois: Decimal


def _dec(valor: Any) -> Decimal:
    return valor if isinstance(valor, Decimal) else Decimal(str(valor or 0))


def teto_efetivo(role: Any, parcela: Decimal, *, mesma_pessoa: bool = True) -> Decimal | None:
    """O limite que a trava aplica e que a tela anuncia (sem o número, para o Casting).

    Args:
        role: O `EventRole`, **antes** de gravar o cachê novo (o `cache_value` é o da pessoa atual).
        parcela: A parcela do carrinho de transporte (239) — zero quando a vaga não leva carro.
        mesma_pessoa: `False` quando o "Salvar" troca o artista (converge, T045): o cachê salvo de
            quem sai não vira limite de quem entra — senão o Casting pagaria a B, sem Superadmin, o
            valor acima do limite que era de A. O que passa de uma pessoa para a outra é só o teto
            autorizado, que é da vaga.

    Returns:
        `None` quando a vaga não tem teto de orçamento (sem limite nenhum); senão o maior entre
        `cache_cap + parcela`, `teto_autorizado` e — com a mesma pessoa — o `cache_value` atual.
    """
    if role.cache_cap is None:
        return None
    return max(
        _dec(role.cache_cap) + parcela,
        _dec(role.teto_autorizado),
        _dec(role.cache_value) if mesma_pessoa else Decimal("0"),
    )


def teto_da_nota(role: Any, parcela: Decimal) -> Decimal | None:
    """O limite contra o qual o log diz "acima do cap — autorizado pelo admin".

    É o efetivo **sem** o cachê atual: o Casting salvando os R$ 400 já autorizados não é uma
    autorização nova. Calcule antes de `gravar_teto_autorizado`, senão a primeira autorização do
    Superadmin some da nota.
    """
    if role.cache_cap is None:
        return None
    return max(_dec(role.cache_cap) + parcela, _dec(role.teto_autorizado))


def gravar_teto_autorizado(
    role: Any, *, cache: Decimal | None, parcela: Decimal, autor_id: int | None, agora: datetime
) -> str | None:
    """Aplica a regra do teto autorizado depois de um "Salvar" do **Superadmin** no card.

    - Só vale para vaga com teto de orçamento, com pessoa escalada e cachê maior que zero: tirar a
      pessoa ou salvar sem cachê nunca mexe na autorização (FR-003).
    - Cachê acima de `cache_cap + parcela` → vira o teto autorizado da vaga (FR-001).
    - Cachê dentro do limite do orçamento → a autorização deixa de existir: o último valor do
      Superadmin manda (FR-004, corrige erro de digitação sem tela nova).

    Args:
        role: O `EventRole` já com o talento novo atribuído.
        cache: O cachê que acabou de ser salvo (já parseado).
        parcela: Parcela do carrinho da vaga.
        autor_id: `User.id` de quem salvou.
        agora: Hora de parede de São Paulo (`now_sp()`).

    Returns:
        A frase para o `EventLog`, ou `None` quando nada mudou.
    """
    if role.cache_cap is None or not role.talent_id or cache is None or cache <= 0:
        return None
    limite_do_orcamento = _dec(role.cache_cap) + parcela
    if cache > limite_do_orcamento:
        if role.teto_autorizado is not None and _dec(role.teto_autorizado) == cache:
            return None
        role.teto_autorizado = cache
        role.teto_autorizado_por = autor_id
        role.teto_autorizado_em = agora
        return f"Limite da vaga {role.character_name} autorizado em R$ {format_brl(cache)}"
    if role.teto_autorizado is None:
        return None
    role.teto_autorizado = None
    role.teto_autorizado_por = None
    role.teto_autorizado_em = None
    return f"Autorização acima do limite da vaga {role.character_name} retirada"


def _snapshot_com_show(entry: Any, show: bool) -> dict:
    """Cópia do snapshot do orçamento com o "show" ligado/desligado em quem tem preço de show."""
    from app.calendar.orcamento_evento_ops import snapshot_do_orcamento

    snap = copy.deepcopy(snapshot_do_orcamento(entry))
    for performer in snap.get("performers") or []:
        if isinstance(performer, dict) and performer.get("type") in TIPOS_COM_SHOW:
            performer["show"] = show
    return snap


def _aplicar(role: Any, item: dict, chave: str, mudancas: list[MudancaDeTeto]) -> None:
    from app.calendar.orcamento_evento_ops import _cap_e_nota

    cap, nota = _cap_e_nota(item, chave)
    if cap is None:
        return
    novo = _dec(cap)
    antes = role.cache_cap
    role.cache_cap_note = nota
    if antes is not None and _dec(antes) == novo:
        return
    role.cache_cap = novo
    mudancas.append(MudancaDeTeto(role.id, role.character_name, antes, novo))


def recalcular_tetos_pelo_tipo(event: Any, *, show: bool) -> tuple[list[MudancaDeTeto], list[str]]:
    """Refaz o teto das vagas pelo orçamento ligado, com o "show" ligado ou desligado (FR-007/008).

    É a conta da criação (`_compute_performer_caches`) na duração real do evento, só que com o show
    trocado em cada personagem de tabela; o coordenador acompanha sozinho (o `has_show` sai dos
    performers) e o Técnico de Som recebe o teto da tabela de som quando entra show. Casamento
    vaga × item por nome normalizado, cada item servindo uma vaga (a regra do vínculo 273). O teto
    autorizado pelo Superadmin não é tocado: ele fica por cima no `teto_efetivo`.

    Args:
        event: O `CalendarEvent` (com o tipo novo já gravado).
        show: `True` ao entrar em SHOW, `False` ao sair.

    Returns:
        `(mudancas, nao_recalculadas)`: os tetos que mudaram, e os nomes das vagas de personagem que
        têm teto mas não casaram com o orçamento (ou o evento não tem orçamento) — o aviso diz que
        esses não foram recalculados.
    """
    from app.calendar.orcamento_evento_ops import (
        _chave,
        _chave_cache,
        _duracao_do_evento,
        data_do_evento,
    )
    from app.calendar.routes import SOUND_TECH_CHARACTER, _compute_performer_caches
    from app.models import OrcamentoHistory

    personagens = [r for r in event.roles if r.role_type != "extra"]
    entry = (
        OrcamentoHistory.query.get(event.orcamento_history_id)
        if event.orcamento_history_id
        else None
    )
    if entry is None:
        return [], [r.character_name for r in personagens if r.cache_cap is not None]

    duracao = _duracao_do_evento(event)
    chave = _chave_cache(duracao)
    itens = _compute_performer_caches(
        _snapshot_com_show(entry, show),
        horas_extra=duracao if duracao > 4 else None,
        data_evento=data_do_evento(event),
    )
    mudancas: list[MudancaDeTeto] = []

    livres = list(personagens)
    for item in itens:
        if (item.get("role_type") or "character") != "character":
            continue
        alvo = next(
            (r for r in livres if _chave(r.character_name) == _chave(item.get("label"))), None
        )
        if alvo is not None:
            livres.remove(alvo)
            _aplicar(alvo, item, chave, mudancas)
    nao_recalculadas = [r.character_name for r in livres if r.cache_cap is not None]

    extras = [i for i in itens if (i.get("role_type") or "character") == "extra"]
    apoio = sorted((r for r in event.roles if r.role_type == "extra"), key=lambda r: r.id or 0)
    coord_itens = [i for i in extras if _chave(i.get("label")).startswith("coordenador")]
    coord_vagas = [r for r in apoio if _chave(r.character_name).startswith("coordenador")]
    for item, role in zip(coord_itens, coord_vagas, strict=False):
        _aplicar(role, item, chave, mudancas)

    # A vaga de presença tem outro nome normalizado ("tecnico de som (presenca)"), então nunca casa:
    # ela não tem valor nem teto (239).
    som = _chave(SOUND_TECH_CHARACTER)
    tecnico_item = next((i for i in extras if _chave(i.get("label")) == som), None)
    tecnico_vaga = next((r for r in apoio if _chave(r.character_name) == som), None)
    if tecnico_item is not None and tecnico_vaga is not None:
        _aplicar(tecnico_vaga, tecnico_item, chave, mudancas)
    return mudancas, nao_recalculadas


def frase_das_mudancas(mudancas: list[MudancaDeTeto]) -> str:
    """ "Luke R$ 325 → R$ 425; Coordenador R$ 375 → R$ 425" — para o `EventLog` (FR-011)."""

    def _fmt(valor: Decimal | None) -> str:
        return "sem limite" if valor is None else f"R$ {format_brl(valor)}"

    return "; ".join(f"{m.personagem} {_fmt(m.antes)} → {_fmt(m.depois)}" for m in mudancas)
