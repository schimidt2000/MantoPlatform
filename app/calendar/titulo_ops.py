"""O título do evento, as vagas de personagem e o título do ensaio andando juntos (feature 339).

O título do Google Agenda é a fonte de verdade do elenco (`docs/00` §6 item 6) e o sync o copia para
o sistema em toda rodada (`calendar/routes.py::sync_events`). Até a 339 a ligação era de mão única e
cheia de buracos: em evento criado pela plataforma o sync nunca olhava as vagas; em evento do Google
ele só testava se o nome aparecia, não quantas vezes; e remover uma vaga no sistema nunca tirava o
nome do título — no evento 1423 o título continuou com dois STORMTROOPERS depois de a vaga sair, e o
ensaio marcado em seguida copiou os dois.

Regras deste módulo:

- **Contagem**: personagens do título contados por nome normalizado (`parse_characters` + `_chave`
  do vínculo 273), com repetição.
- **O que SAIU do título** (antigo × novo) é o que mexe nas vagas: vaga vazia daquele nome sai;
  sobrando só gente escalada, ninguém sai — as vagas ficam marcadas e o Casting é avisado. Diferença
  antiga de grafia entre vaga e título nunca dispara nada.
- **Remover/acrescentar vaga pelo sistema** ajusta UMA ocorrência do título, e só se título e vagas
  ficaram desiguais na direção certa — assim a vaga que sai porque o título já perdeu o nome não o
  tira uma segunda vez.
- **Ensaio futuro** acompanha o título do evento.
- **Google** só depois do commit (`docs/00` §6 item 25); falha vira aviso, nunca desfaz.

Módulo puro: nada de `flask.request`/`current_user`; autor e relógio entram por parâmetro.
"""

from __future__ import annotations

import logging
import re
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from app.models import EventLog, db

logger = logging.getLogger(__name__)

#: Aviso devolvido à tela quando o Google recusa o título novo (spec, seção "Textos").
AVISO_FALHA_GOOGLE = (
    "Não foi possível atualizar o título no Google Agenda. Corrija o título por lá."
)

_PREFIXO_TIPO = re.compile(r"^(\s*\([^)]*\)\s*)?(.*)$", re.DOTALL)
_SEPARADOR = re.compile(r"\s*\+\s*")


@dataclass
class Reconciliacao:
    """O que a comparação título antigo × novo fez com as vagas."""

    removidas: list[str] = field(default_factory=list)
    marcadas: dict[str, tuple[int, int]] = field(default_factory=dict)


def chave_do_nome(nome: str | None) -> str:
    """Nome comparável de personagem: sem prefixo "(TIPO)", sem acento, sem caixa, espaços colapsados."""
    from app.calendar.orcamento_evento_ops import _chave
    from app.calendar.routes import strip_role_prefix

    return _chave(strip_role_prefix(nome or ""))


def contar_personagens(titulo: str | None) -> Counter:
    """Quantas vezes cada personagem aparece no título (nomes de equipe não contam — regra da 239)."""
    from app.calendar.routes import parse_characters

    return Counter(chave_do_nome(p) for p in parse_characters(titulo or ""))


def _partes(titulo: str) -> tuple[str, list[str]]:
    m = _PREFIXO_TIPO.match(titulo or "")
    prefixo = (m.group(1) or "").strip() if m else ""
    resto = m.group(2) if m else (titulo or "")
    return prefixo, [p.strip() for p in _SEPARADOR.split(resto) if p.strip()]


def _juntar(prefixo: str, partes: list[str]) -> str:
    corpo = " + ".join(partes)
    return f"{prefixo} {corpo}".strip() if prefixo else corpo


def tirar_ultima_ocorrencia(titulo: str, nome: str) -> str | None:
    """O título sem a última ocorrência de `nome`, ou `None` se o nome não está nele."""
    prefixo, partes = _partes(titulo)
    alvo = chave_do_nome(nome)
    for i in range(len(partes) - 1, -1, -1):
        if chave_do_nome(partes[i]) == alvo:
            return _juntar(prefixo, partes[:i] + partes[i + 1 :])
    return None


def acrescentar_personagem(titulo: str, nome: str) -> str:
    """O título com `nome` no fim, em maiúsculas como os títulos que a plataforma gera."""
    prefixo, partes = _partes(titulo)
    return _juntar(prefixo, [*partes, nome.strip().upper()])


def _vagas_do_nome(event: Any, chave: str) -> list[Any]:
    return [
        r
        for r in event.roles
        if r.role_type != "extra" and chave_do_nome(r.character_name) == chave
    ]


def _ordem_de_saida(role: Any) -> tuple[bool, int]:
    """Vaga vazia que sai primeiro: a dispensada (108), depois a mais recente (FR-019)."""
    return (role.dismissed_at is None, -(role.id or 0))


def _log(event: Any, mensagem: str, *, autor_nome: str, autor_papel: str, agora: datetime) -> None:
    db.session.add(
        EventLog(
            event_id=event.id,
            actor_name=autor_nome,
            actor_role=autor_papel,
            message=mensagem,
            created_at=agora,
        )
    )


def _e_evento_de_ensaio(event: Any) -> bool:
    return (event.event_type or "").upper() == "ENSAIO" or (event.title or "").startswith(
        "🟧 ENSAIO"
    )


def _remover_vazia(
    event: Any, role: Any, mensagem: str, *, autor_nome: str, autor_papel: str, agora: datetime
) -> None:
    _log(event, mensagem, autor_nome=autor_nome, autor_papel=autor_papel, agora=agora)
    if role in event.roles:
        event.roles.remove(role)
    db.session.delete(role)


# ── O título mudou: vagas a mais (FR-018..024) ────────────────────────────────────────────────


def reconciliar_vagas_pelo_titulo(
    event: Any,
    titulo_antigo: str | None,
    titulo_novo: str | None,
    *,
    autor_id: int | None,
    autor_nome: str,
    autor_papel: str,
    agora: datetime,
) -> Reconciliacao:
    """Aplica às vagas o que SAIU do título. Não comita.

    Para cada personagem que perdeu ocorrências: se há mais vagas dele do que o título novo pede,
    as vazias saem (FR-019); se ainda sobrar, todas ocupadas, nenhuma sai — as ocupadas recebem
    `sobrando_desde` e o Casting (e o Superadmin) é avisado (FR-020). Nenhum e-mail a artista.

    Args:
        event: O `CalendarEvent`, com as vagas carregadas.
        titulo_antigo: O título antes da mudança.
        titulo_novo: O título depois.
        autor_id: Quem mudou (fica fora do próprio aviso); `None` quando veio do Google.
        autor_nome: Nome para o `EventLog`.
        autor_papel: Papel para o `EventLog` ("Sistema" no sync, "Comercial" na edição).
        agora: Hora de parede de São Paulo.

    Returns:
        O que foi removido e o que ficou marcado.
    """
    resultado = Reconciliacao()
    if getattr(event, "is_cancelled", False) or _e_evento_de_ensaio(event):
        return resultado
    antigo, novo = contar_personagens(titulo_antigo), contar_personagens(titulo_novo)
    for chave, n_antigo in antigo.items():
        pedido = novo.get(chave, 0)
        if pedido >= n_antigo:
            continue
        vagas = _vagas_do_nome(event, chave)
        excedente = len(vagas) - pedido
        if excedente <= 0:
            continue
        nome = vagas[0].character_name
        vazias = sorted((r for r in vagas if not r.talent_id), key=_ordem_de_saida)[:excedente]
        for role in vazias:
            _remover_vazia(
                event,
                role,
                f"{nome.upper()}: o título pede {pedido}, havia {len(vagas)} — vaga vazia removida.",
                autor_nome=autor_nome,
                autor_papel=autor_papel,
                agora=agora,
            )
            resultado.removidas.append(nome)
        if excedente - len(vazias) <= 0:
            continue
        ocupadas = [r for r in vagas if r.talent_id]
        for role in ocupadas:
            role.sobrando_desde = role.sobrando_desde or agora
        resultado.marcadas[nome] = (pedido, len(ocupadas))
        from app.notificacoes.notificacoes_ops import frase_da_sobra

        _log(
            event,
            f"{frase_da_sobra(nome, pedido, len(ocupadas))} Nenhuma vaga removida; Casting avisado.",
            autor_nome=autor_nome,
            autor_papel=autor_papel,
            agora=agora,
        )
        from app.notificacoes.notificacoes_ops import notificar_vaga_sobrando

        notificar_vaga_sobrando(
            event, nome, chave=chave, pedido=pedido, vagas=len(ocupadas), autor_id=autor_id
        )
    return resultado


def resolver_sobra(
    event: Any, nome: str, *, autor_nome: str, autor_papel: str, agora: datetime
) -> list[str]:
    """Fecha a sobra de um personagem quando a escala mudou (FR-017, FR-021). Não comita.

    Se o personagem tem vaga marcada: remove as vagas vazias que ainda sobram (a pessoa que o Casting
    acabou de tirar deixou a dela vazia) e, quando vagas e título voltam a bater, limpa as marcas e
    encerra o aviso para todo mundo. Não mexe no título: ele já pede o número certo.

    Returns:
        Os nomes das vagas removidas.
    """
    chave = chave_do_nome(nome)
    vagas = _vagas_do_nome(event, chave)
    if not any(r.sobrando_desde for r in vagas):
        return []
    pedido = contar_personagens(event.title).get(chave, 0)
    excedente = len(vagas) - pedido
    saem = sorted((r for r in vagas if not r.talent_id), key=_ordem_de_saida)[: max(excedente, 0)]
    for role in saem:
        _remover_vazia(
            event,
            role,
            f"{role.character_name.upper()}: o título pede {pedido} — vaga vazia removida.",
            autor_nome=autor_nome,
            autor_papel=autor_papel,
            agora=agora,
        )
    ficam = [r for r in vagas if r not in saem]
    if len(ficam) <= pedido:
        for role in ficam:
            role.sobrando_desde = None
        from app.notificacoes.notificacoes_ops import encerrar_vaga_sobrando

        encerrar_vaga_sobrando(event.id, chave)
    return [r.character_name for r in saem]


# ── Remover/acrescentar vaga pelo sistema ajusta o título (FR-027..029) ─────────────────────────


def ajustar_titulo_apos_remocao(
    event: Any, nome: str, *, autor_nome: str, autor_papel: str, agora: datetime
) -> bool:
    """Depois de uma vaga sair pelo sistema: tira do título UMA ocorrência, se ele ficou pedindo mais.

    Chame depois de a vaga sair da coleção `event.roles`. Não comita.

    Returns:
        `True` quando o título mudou.
    """
    chave = chave_do_nome(nome)
    pedido = contar_personagens(event.title).get(chave, 0)
    if pedido == 0:
        _log(
            event,
            f"Título não ajustado: {nome} não foi encontrado no título do evento.",
            autor_nome=autor_nome,
            autor_papel=autor_papel,
            agora=agora,
        )
        return False
    if pedido <= len(_vagas_do_nome(event, chave)):
        return False
    novo = tirar_ultima_ocorrencia(event.title, nome)
    if novo is None:
        return False
    event.title = novo
    _log(
        event,
        f"Título ajustado: saiu uma ocorrência de {nome.upper()}.",
        autor_nome=autor_nome,
        autor_papel=autor_papel,
        agora=agora,
    )
    return True


def ajustar_titulo_apos_inclusao(
    event: Any, nome: str, *, autor_nome: str, autor_papel: str, agora: datetime
) -> bool:
    """Depois de uma vaga de personagem entrar pelo sistema: põe o nome no fim do título, se faltar.

    Nome de equipe (Coordenador, Técnico de Som…) nunca entra no título (239). Não comita.
    """
    from app.calendar.routes import _is_reserved_title_name

    if _is_reserved_title_name(nome):
        return False
    chave = chave_do_nome(nome)
    if len(_vagas_do_nome(event, chave)) <= contar_personagens(event.title).get(chave, 0):
        return False
    event.title = acrescentar_personagem(event.title or "", nome)
    _log(
        event,
        f"Título ajustado: entrou {nome.strip().upper()}.",
        autor_nome=autor_nome,
        autor_papel=autor_papel,
        agora=agora,
    )
    return True


# ── O ensaio acompanha o título (FR-030) ───────────────────────────────────────────────────────


def propagar_titulo_aos_ensaios(event: Any, *, agora: datetime) -> list[Any]:
    """Dá aos ensaios futuros e não cancelados o título "🟧 ENSAIO — <título do evento>". Não comita.

    Ensaio já realizado fica como está: é registro do que aconteceu.

    Returns:
        Os ensaios cujo título mudou (para empurrar ao Google depois do commit).
    """
    from app.calendar.event_ops import ENSAIO_TITLE_PREFIX

    novo = f"{ENSAIO_TITLE_PREFIX}{event.title}"
    mudados = []
    for ensaio in list(getattr(event, "ensaios", None) or []):
        if ensaio.cancelled_at is not None or not ensaio.start_at or ensaio.start_at <= agora:
            continue
        if ensaio.title != novo:
            ensaio.title = novo
            mudados.append(ensaio)
    return mudados


# ── Google, depois do commit ────────────────────────────────────────────────────────────────────


def empurrar_titulos_ao_google(
    eventos: list[Any], *, autor_nome: str, agora: datetime
) -> list[str]:
    """Grava no Google Agenda o título atual de cada evento/ensaio. Chamar DEPOIS do commit.

    Evento "Sumiu do Google Agenda" (303) não tem par: fica só no sistema, sem aviso — vai ao Google
    quando o Superadmin devolver. Falha vira aviso para a tela e linha no histórico; nunca desfaz a
    mudança no sistema (FR-031).

    Returns:
        Os avisos para a resposta (no máximo um, mesmo com várias falhas).
    """
    from app.calendar.routes import CALENDAR_ID
    from app.calendar.service import update_event

    falhou = False
    vistos: set[int] = set()
    for ev in eventos:
        if (
            ev is None
            or ev.id in vistos
            or not ev.google_event_id
            or getattr(ev, "is_google_missing", False)
        ):
            continue
        vistos.add(ev.id)
        try:
            update_event(
                CALENDAR_ID,
                ev.google_event_id,
                ev.title,
                ev.start_at,
                ev.end_at,
                description=ev.description or "",
                location=ev.location or "",
            )
        except Exception as exc:  # noqa: BLE001 — Google fora/recusou: a vaga já foi gravada
            logger.warning("339: título do evento %s não foi ao Google: %s", ev.id, exc)
            falhou = True
            alvo_id = ev.parent_event_id or ev.id
            db.session.add(
                EventLog(
                    event_id=alvo_id,
                    actor_name=autor_nome,
                    actor_role="Sistema",
                    message=f'Não foi possível gravar no Google Agenda o título "{ev.title}".',
                    created_at=agora,
                )
            )
    if falhou:
        db.session.commit()
        return [AVISO_FALHA_GOOGLE]
    return []
