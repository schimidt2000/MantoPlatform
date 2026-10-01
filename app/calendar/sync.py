"""Fonte única da sincronização da agenda com o Google Calendar.

Reúne, em um só lugar, a lógica de "sincronizar uma faixa de meses" usada por:
  - a sincronização automática interna (thread de background em ``app/__init__.py``);
  - o script ``sync_worker.py`` (execução manual / backup).

O ciclo, desde a feature 303:

1. reconfere no Google, pelo próprio id, cada evento marcado "Sumiu do Google Agenda"
   (``sumico_ops.reconferir_marcados``) — o que voltou perde a marca, mesmo num mês que o ciclo
   não lista;
2. por mês: busca a lista do Google → ``sync_events`` → ``_cleanup_stale_events`` (a limpeza, que
   confere no Google cada evento que faltou na lista: o que mudou de data é atualizado, o que tem
   dinheiro fica e é marcado, e só o vazio com ausência confirmada é apagado) →
   ``_mark_month_synced``;
3. grava o resumo no ``AuditLog``, com os totais dos sumiços ANTES da lista de meses.

O botão "Sincronizar agora" do ``/admin/sync`` (``sync_now``) só busca e sincroniza — não limpa.
Quem limpa é este ciclo e o "Limpar eventos fantasma" (``cleanup_past``).

Os helpers concretos vivem em ``app/calendar/routes.py``; aqui eles são importados
de forma tardia (dentro das funções) para evitar import circular.
"""

from __future__ import annotations

import logging
from collections import Counter
from datetime import date, datetime, timedelta
from typing import TYPE_CHECKING

from sqlalchemy.exc import SQLAlchemyError

if TYPE_CHECKING:
    from app.calendar.sumico_ops import ResultadoLimpeza

logger = logging.getLogger(__name__)


def _add_months(d: date, n: int) -> date:
    """Retorna o primeiro dia do mês ``n`` meses após ``d``."""
    month = d.month - 1 + n
    return date(d.year + month // 12, month % 12 + 1, 1)


def _resumo_do_mes(resultado: ResultadoLimpeza) -> str:
    """Os números da limpeza do mês que não são zero — " (2 removido(s), 1 marcado(s))"."""
    partes = [
        (len(resultado.removidos), "removido(s)"),
        (len(resultado.marcados), "marcado(s)"),
        (len(resultado.movidos), "com data nova"),
        (len(resultado.desmarcados), "de volta ao Google"),
        (len(resultado.inconclusivos), "sem confirmação"),
        (len(resultado.falhas), "com falha"),
    ]
    texto = ", ".join(f"{n} {rotulo}" for n, rotulo in partes if n)
    return f" ({texto})" if texto else ""


def _somar(totais: Counter, resultado: ResultadoLimpeza) -> None:
    totais["marcados"] += len(resultado.marcados)
    totais["movidos"] += len(resultado.movidos)
    totais["desmarcados"] += len(resultado.desmarcados)
    totais["inconclusivos"] += len(resultado.inconclusivos)
    totais["falhas"] += len(resultado.falhas)


def _reconferir(totais: Counter) -> bool:
    """Reconfere os marcados antes dos meses; `False` quando algo falhou (o ciclo sai com erro).

    A falha aqui nunca impede os meses de listar, sincronizar e limpar — cada mês tem o seu
    disjuntor. Inconclusivo não é erro: o evento só espera a próxima rodada.
    """
    from app import db
    from app.calendar import sumico_ops

    try:
        saida = sumico_ops.reconferir_marcados()
    except Exception:  # noqa: BLE001 — a reconferência não pode derrubar o ciclo
        db.session.rollback()
        logger.exception("[sync] falha na reconferência dos marcados")
        return False
    totais["desmarcados"] += len(saida["reapareceram"])
    totais["inconclusivos"] += len(saida["inconclusivos"])
    totais["falhas"] += len(saida["falhas"])
    return not saida["falhas"]


def _frase_sumicos(totais: Counter) -> str:
    """O texto fixo da FR-042, sempre presente no resumo do ciclo."""
    return (
        f"Sumiços: {totais['marcados']} marcado(s), {totais['movidos']} com data atualizada, "
        f"{totais['desmarcados']} de volta ao Google Agenda, {totais['inconclusivos']} sem "
        f"confirmação, {totais['falhas']} com falha. "
    )


def run_calendar_sync(lookahead_months: int = 6) -> dict:
    """Sincroniza a agenda com o Google Calendar para uma faixa de meses.

    Deve ser chamada dentro de um contexto de aplicação Flask (``app.app_context()``).

    Antes dos meses, reconfere os eventos marcados pelo próprio id. Depois sincroniza de hoje
    até ``lookahead_months`` meses à frente, mais um buffer que cobre o evento mais distante já
    existente no banco; em cada mês a limpeza confere no Google o que faltou na lista (mudou de
    data → atualizado; com dinheiro → marcado; vazio com ausência confirmada → apagado). Registra
    o resultado no ``AuditLog`` (visível em /admin/logs), com os totais dos sumiços antes da
    lista de meses. Evento sem confirmação do Google não conta como erro; evento que não pôde ser
    gravado conta.

    Args:
        lookahead_months: Quantos meses à frente sincronizar (padrão 6).

    Returns:
        Dicionário com ``months`` (qtd de meses), ``errors`` (qtd de erros) e
        ``results`` (lista de resumos por mês).
    """
    from app import db
    from app.models import AuditLog, CalendarEvent
    from app.calendar.routes import (
        CALENDAR_ID,
        sync_events,
        _cleanup_stale_events,
        _mark_month_synced,
    )
    from app.calendar.service import fetch_events_for_month

    now = datetime.now()
    current = date(now.year, now.month, 1)
    last = _add_months(current, lookahead_months)

    # Estende o horizonte para cobrir o evento mais distante já no banco (+1 mês de buffer).
    last_event = (
        CalendarEvent.query.filter(CalendarEvent.start_at >= datetime(now.year, now.month, 1))
        .order_by(CalendarEvent.start_at.desc())
        .first()
    )
    if last_event and last_event.start_at:
        last_in_db = _add_months(date(last_event.start_at.year, last_event.start_at.month, 1), 1)
        if last_in_db > last:
            last = last_in_db

    months: list[date] = []
    m = current
    while m <= last:
        months.append(m)
        m = _add_months(m, 1)

    errors = 0
    results: list[str] = []
    totais: Counter = Counter()
    if not _reconferir(totais):
        errors += 1
    for m in months:
        ym = f"{m.year:04d}-{m.month:02d}"
        try:
            items = fetch_events_for_month(CALENDAR_ID, m.year, m.month)
            sync_events(items)
            limpeza = _cleanup_stale_events(items, m.year, m.month)
            _mark_month_synced(ym)
            _somar(totais, limpeza)
            # Evento que não pôde ser gravado é erro do ciclo; o que ficou sem confirmação do
            # Google não é — ele só espera a próxima rodada.
            if limpeza.falhas:
                errors += 1
            results.append(f"{ym}: {len(items)} eventos{_resumo_do_mes(limpeza)}")
        except Exception as exc:  # noqa: BLE001 — um mês com erro não pode abortar os demais
            # Erro de banco deixa a sessão inválida, e sem o rollback todos os meses seguintes
            # falhavam junto. Em erro que NÃO é de banco o pendente de `sync_events` tem de
            # ficar: os e-mails ao elenco já saíram (vaga removida, evento alterado), e desfazer
            # a vaga apagada e o `event_changed_at` repetiria o e-mail a cada ciclo.
            if isinstance(exc, SQLAlchemyError):
                db.session.rollback()
            errors += 1
            results.append(f"{ym}: ERRO — {exc}")

    # feature 126: reprocessa respostas de formulário ainda sem evento vinculado — cobre o
    # caso do evento ter sido criado/importado DEPOIS da resposta já ter chegado.
    linked_count = 0
    try:
        from app.formularios.formularios_ops import retry_auto_link_pending
        linked_count = retry_auto_link_pending()
    except Exception:  # noqa: BLE001 — best-effort, não pode derrubar o ciclo de sync
        pass

    status = "ok" if not errors else "erro"
    # Os totais dos sumiços vêm ANTES da lista de meses, que é cortada nos oito primeiros.
    detail = (
        f"{len(months)} mês(es) sincronizado(s). {errors} erro(s). "
        + (f"{linked_count} resposta(s) de formulário vinculada(s) automaticamente. " if linked_count else "")
        + _frase_sumicos(totais)
        + " | ".join(results[:8])
        + (" [...]" if len(results) > 8 else "")
    )
    try:
        db.session.add(
            AuditLog(
                actor_name="auto-sync",
                actor_role="Sistema",
                entity_type="agenda",
                entity_id=None,
                entity_name=f"cron-{now.strftime('%Y-%m-%d %H:%M')}",
                action=f"sync_{status}",
                detail=detail,
            )
        )
        db.session.commit()
    except Exception:  # noqa: BLE001 — log é best-effort; não pode derrubar o ciclo
        db.session.rollback()

    return {"months": len(months), "errors": errors, "results": results}


def _claim_auto_sync(interval_seconds: int) -> bool:
    """Reivindica o ciclo de sincronização automática de forma atômica.

    Faz um ``UPDATE`` condicional em ``site_settings``: só "ganha" o ciclo se a
    última sincronização automática foi há mais de ``interval_seconds`` (ou nunca).
    Como o ``UPDATE`` é atômico no banco, apenas um processo/worker ganha por ciclo,
    evitando execução concorrente (a coluna ``google_event_id`` é única).

    Args:
        interval_seconds: Intervalo mínimo entre ciclos.

    Returns:
        ``True`` se este processo deve executar o ciclo agora; ``False`` caso outro
        já tenha reivindicado dentro do intervalo.
    """
    from sqlalchemy import text
    from app import db

    now = datetime.utcnow()
    threshold = now - timedelta(seconds=interval_seconds)
    result = db.session.execute(
        text(
            "UPDATE site_settings SET calendar_auto_sync_at = :now "
            "WHERE id = 1 AND (calendar_auto_sync_at IS NULL OR calendar_auto_sync_at < :threshold)"
        ),
        {"now": now, "threshold": threshold},
    )
    db.session.commit()
    return result.rowcount == 1
