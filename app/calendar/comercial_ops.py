"""As três coleções comerciais de um evento: acréscimos, notas fiscais e parcelas.

Funções puras — não leem `request` nem chamam `flash`. Recebem listas de dicionários já
convertidos e devolvem os avisos em vez de exibi-los, para a camada de rota decidir se vira
`flash` (Jinja) ou `warnings` no JSON (API).

O núcleo saiu de `_handle_update_comercial` (`app/calendar/routes.py`), onde era lido **linha a
linha do formulário** (`request.form.getlist("acrescimo_bv_recipient[]")`, arquivo por linha em
`nf_file__<key>`). Enquanto morasse lá, estas três escritas simplesmente não existiam para a
plataforma React — é o item 2 dos pré-requisitos da fase 6 em `docs/PLANO_REMOCAO_JINJA.md`.

## Três regras que não podem se perder na tradução

1. **Lista ausente ≠ lista vazia.** `None` significa "esta seção não foi enviada, não mexa";
   `[]` significa "apague tudo". No formulário isso era `if _acr_tipos:` — sem essa distinção,
   salvar qualquer outra parte da aba Comercial apagaria todos os acréscimos do evento.
2. **BV já pago continua pago.** O status de pagamento é preservado pela chave
   `(recebedor, pix)`, porque a gravação apaga e recria as linhas. Sem isso, salvar a aba
   "despaga" alguém que já recebeu.
3. **Acréscimo percentual é congelado em reais** (`amount_brl`) no momento do save, sobre a venda
   daquele instante. Mudar a venda depois não reescreve acréscimo antigo.

O upload do arquivo da nota fica na camada de rota: aqui só chega o caminho já salvo.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from app import db
from app.models import EventAcrescimo, EventInstallment, EventInvoice

# Tipo de acréscimo que representa repasse a terceiro (bonificação de venda) — o único que carrega
# recebedor, chave PIX e status de pagamento próprios.
ACRESCIMO_TIPO_BV = "BV"


def _to_decimal(valor: Any) -> Decimal | None:
    """Converte para `Decimal` sem passar por `float`, que introduziria erro de centavo."""
    if valor is None or valor == "":
        return None
    if isinstance(valor, Decimal):
        return valor
    try:
        return Decimal(str(valor))
    except (ArithmeticError, ValueError):
        return None


def _to_date(valor: Any) -> date | None:
    """Aceita `date` ou string ISO; devolve None para vazio ou inválido (nunca levanta)."""
    if not valor:
        return None
    if isinstance(valor, date) and not isinstance(valor, datetime):
        return valor
    if isinstance(valor, datetime):
        return valor.date()
    try:
        return date.fromisoformat(str(valor).strip())
    except ValueError:
        return None


def substituir_acrescimos(event: Any, itens: list[dict] | None) -> None:
    """Regrava os acréscimos do evento. `None` não mexe em nada; `[]` apaga todos. Sem commit.

    Args:
        event: O `CalendarEvent` dono dos acréscimos.
        itens: Cada item aceita ``tipo``, ``descricao``, ``is_percent``, ``value``,
            ``bv_recipient`` e ``bv_pix``. Item sem `tipo` ou com valor zero/nulo é ignorado —
            é como o editor antigo tratava linha em branco deixada pelo usuário.
    """
    if itens is None:
        return

    # A gravação apaga e recria, então o status de pagamento dos BVs precisa ser resgatado por
    # (recebedor, pix) — do contrário salvar a aba "despaga" quem já recebeu.
    status_anterior = {
        (a.bv_recipient or "", a.bv_pix or ""): a.bv_payment_status
        for a in event.acrescimos
        if a.is_bv
    }
    EventAcrescimo.query.filter_by(event_id=event.id).delete()

    venda = _to_decimal(event.sale_value) or Decimal("0")
    for item in itens:
        tipo = (item.get("tipo") or "").strip()
        valor = _to_decimal(item.get("value"))
        if not tipo or valor is None or valor == 0:
            continue

        is_percent = bool(item.get("is_percent"))
        amount = (
            (venda * valor / Decimal("100")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            if is_percent
            else valor
        )
        is_bv = tipo == ACRESCIMO_TIPO_BV
        recebedor = (item.get("bv_recipient") or "").strip() or None
        pix = (item.get("bv_pix") or "").strip() or None

        db.session.add(EventAcrescimo(
            event_id=event.id,
            tipo=tipo,
            descricao=(item.get("descricao") or "").strip() or None,
            is_percent=is_percent,
            value=valor,
            amount_brl=amount,
            is_bv=is_bv,
            bv_recipient=recebedor if is_bv else None,
            bv_pix=pix if is_bv else None,
            bv_payment_status=(
                status_anterior.get((recebedor or "", pix or ""), "nao_pago") if is_bv else "nao_pago"
            ),
        ))


def sincronizar_notas(event: Any, itens: list[dict] | None, agora: datetime) -> list[str]:
    """Casa as notas fiscais do evento com a lista recebida. Sem commit.

    Venda sem nota (`with_invoice` falso) apaga a coleção inteira, independentemente do que veio.
    Nota existente que **não** aparece na lista é removida — a lista é a verdade, como no editor
    antigo. `None` não mexe em nada.

    Args:
        event: O `CalendarEvent` dono das notas.
        itens: Cada item aceita ``id`` (existente), ``amount``, ``issue_date`` e ``file`` (caminho
            já salvo pela camada de rota). Item novo totalmente vazio é ignorado.
        agora: Momento do carimbo de emissão.

    Returns:
        Avisos para exibir sem bloquear — hoje, a divergência entre a soma das notas e a venda.
    """
    if not event.with_invoice:
        EventInvoice.query.filter_by(event_id=event.id).delete()
        return []
    if itens is None:
        return []

    existentes = {inv.id: inv for inv in event.invoices}
    vistos: set[int] = set()
    avisos: list[str] = []

    for item in itens:
        valor = _to_decimal(item.get("amount"))
        emissao = _to_date(item.get("issue_date"))
        arquivo = item.get("file") or None
        nota_id = item.get("id")

        if nota_id and int(nota_id) in existentes:
            nota = existentes[int(nota_id)]
            vistos.add(nota.id)
            nota.amount = valor
            nota.issue_date = emissao
            if arquivo:
                nota.file = arquivo
                # Anexar o arquivo é o que emite a nota; só carimba na transição, para não
                # reescrever a data de emissão a cada salvamento seguinte.
                if nota.status != "emitida":
                    nota.status = "emitida"
                    nota.issued_at = agora
        else:
            if valor is None and not emissao and not arquivo:
                continue
            db.session.add(EventInvoice(
                event_id=event.id,
                amount=valor,
                issue_date=emissao,
                file=arquivo,
                status="emitida" if arquivo else "a_emitir",
                issued_at=agora if arquivo else None,
            ))

    for nota_id, nota in existentes.items():
        if nota_id not in vistos:
            db.session.delete(nota)

    soma = sum(
        (_to_decimal(i.get("amount")) or Decimal("0") for i in itens), Decimal("0")
    )
    venda = _to_decimal(event.sale_value)
    if venda and soma and soma != venda:
        avisos.append(
            f"A soma das notas (R$ {soma:.2f}) é diferente do valor da venda (R$ {venda:.2f})."
        )
    return avisos


def substituir_parcelas(event: Any, itens: list[dict] | None) -> None:
    """Recria o cronograma de parcelas do evento (feature 065). Sem commit.

    `None` não mexe em nada; `[]` apaga o cronograma. Parcela sem data ou sem valor é ignorada.

    Args:
        event: O `CalendarEvent` dono das parcelas.
        itens: Cada item aceita ``due_date`` e ``amount``.
    """
    if itens is None:
        return

    EventInstallment.query.filter_by(event_id=event.id).delete()
    for item in itens:
        vencimento = _to_date(item.get("due_date"))
        valor = _to_decimal(item.get("amount"))
        if vencimento is None or valor is None:
            continue
        db.session.add(EventInstallment(event_id=event.id, due_date=vencimento, amount=valor))
