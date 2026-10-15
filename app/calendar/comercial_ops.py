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
   `[]` significa "apague tudo" — menos o BV pago ou no banco, que não sai por aqui (feature 305).
   No formulário isso era `if _acr_tipos:` — sem essa distinção, salvar qualquer outra parte da
   aba Comercial apagaria todos os acréscimos do evento.
2. **BV já pago continua pago.** O status de pagamento é herdado da linha de mesmo ``id``
   (feature 305; a chave `(recebedor, pix)` só vale para o bundle antigo), porque a gravação apaga
   e recria as linhas. Sem isso, salvar a aba "despaga" alguém que já recebeu.
3. **Acréscimo percentual é congelado em reais** (`amount_brl`) no momento do save, sobre a venda
   daquele instante. Mudar a venda depois não reescreve acréscimo antigo.

O upload do arquivo da nota fica na camada de rota: aqui só chega o caminho já salvo.
"""

from __future__ import annotations

import re
from collections import Counter
from datetime import date, datetime
from decimal import ROUND_HALF_UP, Decimal
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


_CENTAVO = Decimal("0.01")
#: Estados do BV em que o dinheiro já saiu (ou está saindo): o valor não muda mais (P-20 da 305).
_BV_CONGELADO = ("pago", "no_banco")


class AcrescimosRecusados(Exception):
    """A lista de acréscimos não pode ser gravada (feature 305). `erros` = ``{"items.<i>.<campo>": msg}``,
    pelo índice da REQUISIÇÃO — a tela marca a linha certa. Nada foi apagado."""

    def __init__(self, erros: dict[str, str]) -> None:
        super().__init__("; ".join(erros.values()))
        self.erros = erros


def _q(valor: Decimal) -> Decimal:
    return valor.quantize(_CENTAVO, rounding=ROUND_HALF_UP)


#: "1.500" sem vírgula: o milhar à brasileira, que `Decimal` lê como 1,50 (feature 305).
_MILHAR_SEM_CENTAVOS = re.compile(r"^-?\d{1,3}(\.\d{3})+$")
#: Teto das colunas `Numeric(12,2)`: acima disso o flush estoura com 500 em vez do 400 na linha.
_TETO_DO_VALOR = Decimal("1e10")


def _valor_digitado(valor: Any) -> Decimal | None:
    """O número do editor: número do JSON, ou texto à brasileira ("1.309,52", "100,00", "10,5") ou com
    ponto decimal ("150.00", vindo do bundle antigo). Antes, "100,00" virava `None` e a linha era
    DESCARTADA em silêncio depois do delete — um BV digitado com vírgula sumia (feature 305).

    O texto ambíguo é recusado (`None` → "Valor inválido." na linha), nunca reinterpretado: "1.500"
    (que a tela convida, com o placeholder "150,00") virava R$ 1,50 a pagar, e "1,309.52" virava 1,31.
    """
    if isinstance(valor, bool):
        return None
    if isinstance(valor, (int, float, Decimal)):
        d = _to_decimal(valor)
    elif isinstance(valor, str):
        texto = valor.replace("R$", "").replace(" ", "").replace(" ", "").strip()
        if "," in texto and "." in texto and texto.rfind(".") > texto.rfind(","):
            return None
        if "," in texto:
            texto = texto.replace(".", "").replace(",", ".")
        elif _MILHAR_SEM_CENTAVOS.match(texto):
            return None
        d = _to_decimal(texto)
    else:
        return None
    if d is None or not d.is_finite() or abs(d) >= _TETO_DO_VALOR:
        return None
    # Ao centavo, que é o que a coluna guarda: as guardas de zero, negativo e teto olham o valor
    # gravado — R$ 0,004 passava pelo "zero" e virava BV de R$ 0,00; 9.999.999.999,995 estourava.
    d = _q(d)
    return d if abs(d) < _TETO_DO_VALOR else None


def valor_do_bv_percentual(
    venda: Any, with_invoice: bool, percentual: Decimal, soma_bv_reais: Decimal, soma_perc_bv: Decimal
) -> Decimal | None:
    """A régua do BV em % lançado no evento (feature 305; D2, 3a-Q5 e 3b-Q7). `None` sem base.

    O % é sobre o preço COM os outros acréscimos e ANTES do BV e da nota — o dono: "o acréscimo
    adicionado manualmente é colocado por cima de tudo no valor, e o BV é calculado em cima de tudo
    isso". Desfazendo a venda: líquido = venda × 0,84 com nota; base = (líquido − BVs em reais) ÷
    (1 + Σ % dos BVs ÷ 100), ao centavo. No exemplo da D2, R$ 1.309,52 com nota → R$ 100,00 (a régua
    antiga dava R$ 130,95, % sobre a venda cheia). Um BV não entra na base de outro.
    """
    from app.calendar.orcamento_evento_ops import divisor_da_nota

    venda_d = _to_decimal(venda)
    if venda_d is None or venda_d <= 0:
        return None
    liquido = venda_d * divisor_da_nota() if with_invoice else venda_d
    divisor = Decimal("1") + soma_perc_bv / 100
    if divisor <= 0:
        return None
    base = _q((liquido - soma_bv_reais) / divisor)
    if base <= 0 or percentual <= 0:
        return None
    return _q(base * percentual / 100)


def _sem_venda(event: Any) -> bool:
    from app.calendar.event_ops import sem_valor_de_venda

    return bool(getattr(event, "is_cortesia_permuta", False)) or sem_valor_de_venda(event.sale_value)


def substituir_acrescimos(
    event: Any, itens: list[dict] | None, *, reenviados: list | None = None
) -> list[dict]:
    """Regrava os acréscimos do evento. `None` não mexe em nada; `[]` apaga todos (menos o BV pago
    ou no banco, que dá `AcrescimosRecusados`). Sem commit.

    Feature 305 — o editor deixa de estragar o BV:

    - **Identidade, não chave.** Cada item pode trazer o ``id`` que a tela recebeu no GET; só da
      linha antiga de mesmo id herdam-se o status de pagamento, o PIX que veio vazio ("mantém"), a
      descrição que não veio e o valor congelado do pago. Linha nova (sem id) nasce ``nao_pago``.
      Herdar pela chave (recebedor, PIX) fazia um BV novo para quem já tinha um BV pago nascer
      "pago" — e dois BVs da mesma pessoa se fundirem. A chave só vale para o bundle antigo (que não
      manda id nenhum), e mesmo lá só quando há uma candidata.
    - **BV pago ou no banco não muda de valor** — em R$ ou em % (P-20).
    - **BV em %** pela régua de `valor_do_bv_percentual`, recalculado só a pagar; com a venda sem
      valor, o existente mantém o valor e um novo é recusado.
    - **BV em reais** como digitado (3a-Q7 = B).
    - **Quem recebe e PIX obrigatórios** em todo BV (B8); a lista inteira é recusada ANTES de apagar.
    - Valor à brasileira aceito; valor ilegível ou ambíguo recusado (nunca descartado em silêncio);
      "bv" é BV. BV sem valor, zero ou negativo é recusado na linha — apagar o valor e salvar
      tirava o BV da Planilha e subia a comissão com 200; o negativo virava repasse negativo.
    - O mesmo ``id`` duas vezes na lista é recusado: as duas linhas herdariam o "pago" da antiga.
    - O evento é travado e relido antes (`travar_evento`): a régua do % usa a venda de agora, não
      a de antes de uma mudança de venda concorrente. As linhas antigas são lidas com ``FOR UPDATE``
      (um "marcar pago" concorrente falha alto em vez de sumir) e, no fim, a coleção
      ``event.acrescimos`` é recarregada: o sync da comissão, que vem logo depois, lia a coleção
      VELHA (com o BV apagado) — também no gêmeo Jinja de antes.

    Args:
        event: O `CalendarEvent` dono dos acréscimos.
        itens: Cada item aceita ``id``, ``tipo``, ``descricao``, ``is_percent``, ``value``,
            ``bv_recipient``, ``bv_pix`` e ``valor_visto`` (o R$ que a tela mostrou do BV a pagar;
            diferente do gravado → recusa, porque a venda o mudou depois). Item sem `tipo` é
            ignorado (a linha em branco deixada pelo usuário); o que não é BV com valor zero ou
            vazio também, como no editor antigo.
        reenviados: Só o gêmeo Jinja (que grava venda e acréscimos no mesmo envio): recebe a
            chave (`_bv_na_tela`) de cada BV em reais a pagar que é a MESMA linha antiga com o
            MESMO número — os que a B10 deve fazer acompanhar a venda (`so_os_reenviados`).

    Returns:
        As trocas de quem recebe ou de PIX em BV pago ou no banco (``valor``, ``status``,
        ``quem_antes``, ``quem_depois``, ``pix_antes``, ``pix_depois``) — quem chama grava o
        rastro (`frase_da_troca_no_bv_pago`). O valor congela; quem recebe e o PIX, não (FR-017a).

    Raises:
        AcrescimosRecusados: alguma linha não pode ser gravada; nada foi apagado.
    """
    if itens is None:
        return []
    from app.calendar.orcamento_evento_ops import _fmt_reais, erros_do_bv, travar_evento

    travar_evento(event)
    # `populate_existing`: o objeto já na sessão (lido antes, sem trava) seria devolvido com os
    # valores velhos — um "pago" que entrou no meio voltaria a "a pagar".
    antigas = (
        EventAcrescimo.query.filter_by(event_id=event.id).order_by(EventAcrescimo.id)
        .with_for_update().populate_existing().all()
    )
    por_id = {a.id: a for a in antigas}
    usa_id = any(isinstance(i, dict) and "id" in i for i in itens)
    sem_venda = _sem_venda(event)
    cancelado = getattr(event, "cancelled_at", None) is not None
    erros: dict[str, str] = {}
    linhas: list[dict] = []
    descricoes_livres = [a for a in antigas]
    ids_usados: set[int] = set()

    for indice, item in enumerate(itens):
        if not isinstance(item, dict):
            continue
        tipo = item.get("tipo")
        tipo = tipo.strip() if isinstance(tipo, str) else ""
        bruto = item.get("value")
        if not tipo:
            continue
        if tipo.upper() == ACRESCIMO_TIPO_BV:
            tipo = ACRESCIMO_TIPO_BV
        eh_bv = tipo == ACRESCIMO_TIPO_BV
        valor = _valor_digitado(bruto)
        vazio = bruto is None or (isinstance(bruto, str) and not bruto.strip())
        if valor is None and not vazio:
            erros[f"items.{indice}.value"] = "Valor inválido."
            continue
        if valor is None or valor == 0:
            if eh_bv:
                erros[f"items.{indice}.value"] = "Informe o valor do BV (ou remova a linha)."
            continue
        if valor < 0 and eh_bv:
            erros[f"items.{indice}.value"] = "O BV não pode ser negativo."
            continue
        antiga = None
        if usa_id:
            try:
                antiga = por_id.get(int(item.get("id"))) if item.get("id") is not None else None
            except (TypeError, ValueError, OverflowError):
                antiga = None
            if antiga is not None:
                if antiga.id in ids_usados:
                    erros[f"items.{indice}.id"] = "Esta linha aparece duas vezes na lista: recarregue a página."
                    continue
                ids_usados.add(antiga.id)
        linhas.append({"indice": indice, "item": item, "tipo": tipo[:40], "valor": valor,
                       "is_percent": bool(item.get("is_percent")), "is_bv": tipo == ACRESCIMO_TIPO_BV,
                       "antiga": antiga})

    # Bundle antigo (nenhum id): a linha antiga é achada pelo que dá — o BV pela chave (recebedor,
    # PIX) ou pelo recebedor, só se houver UMA candidata; os outros por tipo e valor.
    if not usa_id:
        bvs_antigos = [a for a in antigas if a.is_bv]
        for linha in linhas:
            item = linha["item"]
            if linha["is_bv"]:
                recebedor = (item.get("bv_recipient") or "").strip() if isinstance(item.get("bv_recipient"), str) else ""
                pix = (item.get("bv_pix") or "").strip() if isinstance(item.get("bv_pix"), str) else ""
                candidatas = [a for a in bvs_antigos if (a.bv_recipient or "") == recebedor
                              and (not pix or (a.bv_pix or "") == pix)]
                if len(candidatas) == 1:
                    linha["antiga"] = candidatas[0]
                    bvs_antigos.remove(candidatas[0])
            else:
                for a in descricoes_livres:
                    if not a.is_bv and a.tipo == linha["tipo"] and _to_decimal(a.value) == linha["valor"]:
                        linha["antiga"] = a
                        descricoes_livres.remove(a)
                        break

    # BV pago ou no banco não sai nem vira outra coisa pelo editor (a Comercial não marca pagamento —
    # apagar o BV pago tiraria da Planilha e da DRE dinheiro que já saiu). Desmarca-se na Planilha.
    usadas = {id(linha["antiga"]) for linha in linhas if linha["antiga"] is not None}
    for linha in linhas:
        antiga = linha["antiga"]
        if antiga is not None and antiga.is_bv and antiga.bv_payment_status in _BV_CONGELADO and not linha["is_bv"]:
            erros[f"items.{linha['indice']}.tipo"] = "Este BV já foi pago: ele não muda de tipo por aqui."
    if any(a.is_bv and a.bv_payment_status in _BV_CONGELADO and id(a) not in usadas for a in antigas):
        erros["items"] = (
            "Um BV já pago (ou no banco) saiu da lista: ele não se apaga por aqui. Recarregue a página; "
            "para desfazer o pagamento, use a Planilha de Pagamentos."
        )

    # Os BVs em reais e os % dos BVs, para a régua (todos, pagos inclusive: fazem parte do preço).
    soma_bv_reais = Decimal("0")
    soma_perc_bv = Decimal("0")
    for linha in linhas:
        if not linha["is_bv"]:
            continue
        antiga = linha["antiga"]
        congelada = antiga is not None and antiga.is_bv and antiga.bv_payment_status in _BV_CONGELADO
        if congelada:
            if antiga.is_percent:
                soma_perc_bv += _to_decimal(antiga.value) or Decimal("0")
            else:
                soma_bv_reais += _to_decimal(antiga.amount_brl) or Decimal("0")
        elif linha["is_percent"]:
            soma_perc_bv += _q(linha["valor"])
        else:
            soma_bv_reais += _q(linha["valor"])

    venda = _to_decimal(event.sale_value) or Decimal("0")
    novas: list[dict] = []
    trocas: list[dict] = []
    for linha in linhas:
        item, antiga, indice = linha["item"], linha["antiga"], linha["indice"]
        if "descricao" in item:
            descricao = item.get("descricao")
            descricao = (descricao.strip() or None) if isinstance(descricao, str) else None
        else:
            descricao = antiga.descricao if antiga is not None else None
        registro = {"tipo": linha["tipo"], "descricao": descricao[:200] if descricao else None,
                    "is_bv": linha["is_bv"], "bv_recipient": None, "bv_pix": None,
                    "bv_payment_status": "nao_pago"}
        if linha["is_bv"]:
            recebedor = item.get("bv_recipient")
            pix = item.get("bv_pix")
            recebedor = recebedor.strip() if isinstance(recebedor, str) else recebedor
            pix = pix.strip() if isinstance(pix, str) else pix
            if not pix and antiga is not None and antiga.is_bv and antiga.bv_pix:
                pix = antiga.bv_pix  # PIX vazio = mantém o da MESMA linha
            for campo, mensagem in erros_do_bv(recebedor, pix).items():
                erros[f"items.{indice}.{campo}"] = mensagem
            registro.update(bv_recipient=recebedor or None, bv_pix=pix or None)
            if antiga is not None and antiga.is_bv:
                registro["bv_payment_status"] = antiga.bv_payment_status or "nao_pago"
            if registro["bv_payment_status"] in _BV_CONGELADO and antiga is not None:
                registro.update(is_percent=antiga.is_percent, value=antiga.value, amount_brl=antiga.amount_brl)
                if (recebedor or None) != antiga.bv_recipient or (pix or None) != antiga.bv_pix:
                    # O dinheiro já saiu para alguém: quem recebe e o PIX seguem editáveis, mas a
                    # troca deixa rastro — senão o registro de quem recebeu se reescreve calado.
                    trocas.append({
                        "valor": antiga.amount_brl, "status": antiga.bv_payment_status,
                        "quem_antes": antiga.bv_recipient, "quem_depois": recebedor or None,
                        "pix_antes": antiga.bv_pix, "pix_depois": pix or None,
                    })
            elif linha["is_percent"]:
                percentual = _q(linha["valor"])
                if sem_venda or cancelado:
                    if antiga is not None and antiga.is_bv and antiga.is_percent and antiga.amount_brl is not None:
                        valor_bv = _to_decimal(antiga.amount_brl)
                    else:
                        erros[f"items.{indice}.value"] = (
                            "Sem valor de venda, o BV em % não tem base: lance-o em reais ou depois do valor de venda."
                        )
                        continue
                else:
                    valor_bv = valor_do_bv_percentual(
                        venda, bool(event.with_invoice), percentual, soma_bv_reais, soma_perc_bv
                    )
                    if valor_bv is None:
                        erros[f"items.{indice}.value"] = "A base do BV ficou negativa: confira os valores."
                        continue
                registro.update(is_percent=True, value=percentual, amount_brl=valor_bv)
            else:
                visto = _to_decimal(item.get("valor_visto")) if not isinstance(item.get("valor_visto"), bool) else None
                if visto is not None and (not visto.is_finite() or abs(visto) >= _TETO_DO_VALOR):
                    visto = None  # lixo (inf, NaN, 1e30): como se não viesse — nunca 500 no `_q`
                if (
                    visto is not None
                    and antiga is not None
                    and antiga.is_bv
                    and not antiga.is_percent
                    and _q(visto) != _q(_to_decimal(antiga.amount_brl) or Decimal("0"))
                ):
                    # O editor abriu antes de a venda mudar o BV (B10, outra aba ou outra pessoa):
                    # gravar "como digitado" desfaria a proporção sem ninguém ver.
                    erros[f"items.{indice}.value"] = (
                        f"O BV mudou para {_fmt_reais(antiga.amount_brl or 0)} desde que o editor abriu: "
                        "recarregue a página e confira."
                    )
                    continue
                registro.update(is_percent=False, value=_q(linha["valor"]), amount_brl=_q(linha["valor"]))
                if (
                    reenviados is not None
                    and antiga is not None
                    and antiga.is_bv
                    and not antiga.is_percent
                    and _q(linha["valor"]) == _q(_to_decimal(antiga.value) or Decimal("0"))
                ):
                    # A MESMA linha (pela identidade) com o MESMO número: reenviada, não digitada —
                    # o gêmeo Jinja a deixa acompanhar a venda. Trocar só quem recebe ou o PIX não conta.
                    reenviados.append(_bv_na_tela(recebedor, pix, False, linha["valor"]))
        else:
            # Acréscimo que não é BV: só registro (não entra em comissão, DRE nem Planilha).
            if linha["is_percent"]:
                registro.update(is_percent=True, value=linha["valor"], amount_brl=_q(venda * linha["valor"] / 100))
            else:
                registro.update(is_percent=False, value=linha["valor"], amount_brl=linha["valor"])
        novas.append(registro)

    if erros:
        raise AcrescimosRecusados(erros)

    for antiga in antigas:
        db.session.delete(antiga)
    db.session.flush()
    for registro in novas:
        db.session.add(EventAcrescimo(event_id=event.id, **registro))
    db.session.flush()
    db.session.expire(event, ["acrescimos"])
    return trocas


def _pix_mascarado(pix: Any) -> str:
    """Os 4 últimos caracteres do PIX: o rastro diz que mudou sem virar outro lugar de dado de pagamento."""
    texto = (pix or "").strip() if isinstance(pix, str) else ""
    if not texto:
        return "—"
    return "…" + texto[-4:] if len(texto) > 4 else "…"


def frase_da_troca_no_bv_pago(troca: dict) -> str:
    """O `AuditLog` da troca de quem recebe ou do PIX num BV pago ou no banco (sem o PIX inteiro)."""
    from app.calendar.orcamento_evento_ops import _fmt_reais

    situacao = "no banco" if troca["status"] == "no_banco" else "pago"
    partes = []
    if troca["quem_antes"] != troca["quem_depois"]:
        partes.append(f"quem recebe {troca['quem_antes'] or '—'} → {troca['quem_depois'] or '—'}")
    if troca["pix_antes"] != troca["pix_depois"]:
        partes.append(f"PIX {_pix_mascarado(troca['pix_antes'])} → {_pix_mascarado(troca['pix_depois'])}")
    return f"BV pago ({situacao}) de {_fmt_reais(troca['valor'] or 0)}: " + "; ".join(partes)


def estado_da_venda(event: Any) -> tuple[Any, bool, bool]:
    """(venda, nota, cortesia) ANTES de uma escrita — o "antes" de `acompanhar_bv_da_venda`.

    Trava e relê o evento antes (`travar_evento`): lido sem trava, duas mudanças de venda ao mesmo
    tempo partiam do mesmo "antes" e o BV era proporcionado duas vezes (1.000 → 1.200 e → 1.500
    davam BV 180 em vez de 150). Chamado ANTES de qualquer escrita na venda.
    """
    from app.calendar.orcamento_evento_ops import travar_evento

    travar_evento(event)
    return event.sale_value, bool(event.with_invoice), bool(getattr(event, "is_cortesia_permuta", False))


def _bv_na_tela(recebedor: Any, pix: Any, is_percent: Any, value: Any) -> tuple[str, str, bool, Decimal]:
    """O BV como a tela do Jinja o mostra: quem recebe, PIX, unidade e número. Quem recebe e o PIX
    entram na chave — só pelo valor, o 120 redigitado de um BV casava com o 120 reenviado de OUTRO,
    e a proporção ia para o BV errado."""
    return (
        (recebedor or "").strip(),
        (pix or "").strip(),
        bool(is_percent),
        _q(_to_decimal(value) or Decimal("0")),
    )


def bvs_a_pagar_por_valor(event: Any) -> Counter:
    """Os BVs a pagar como a tela os mostra (`_bv_na_tela`) — o gêmeo Jinja conta os em reais para
    saber se algum foi digitado agora (os reenviados quem diz é `substituir_acrescimos`, pela
    identidade). Dois BVs iguais em tudo são intercambiáveis: tanto faz qual acompanha a venda.

    Lê colunas, não entidades: um objeto carregado aqui, sem trava, voltaria de um `FOR UPDATE`
    seguinte com o status velho.
    """
    linhas = (
        db.session.query(
            EventAcrescimo.bv_recipient, EventAcrescimo.bv_pix, EventAcrescimo.is_percent,
            EventAcrescimo.value, EventAcrescimo.bv_payment_status,
        )
        .filter(EventAcrescimo.event_id == event.id, EventAcrescimo.is_bv.is_(True))
        .all()
    )
    return Counter(
        _bv_na_tela(recebedor, pix, is_percent, value)
        for recebedor, pix, is_percent, value, status in linhas
        if (status or "nao_pago") not in _BV_CONGELADO
    )


def _liquido(venda: Decimal, nota: bool) -> Decimal:
    from app.calendar.orcamento_evento_ops import divisor_da_nota

    return venda * divisor_da_nota() if nota else venda


def acompanhar_bv_da_venda(
    event: Any,
    antes: tuple[Any, bool, bool],
    *,
    actor_name: str,
    tz: Any,
    so_os_reenviados: Counter | None = None,
) -> str | None:
    """O BV a pagar acompanha a venda que muda depois (feature 305, B10; 3a-Q1 = B, Q8 = A). Sem commit.

    O dono: "se o valor total do orçamento mudar, o BV deve acompanhar proporcionalmente" — e, do BV
    combinado com o intermediador, "se o valor diminuir, acredito que deva diminuir proporcionalmente".
    Uma regra só para todo BV **a pagar** no evento, venha do orçamento ou digitado à mão:

    - **em reais**: na proporção do valor LÍQUIDO (venda × 0,84 com nota), de antes para depois — a
      nota que sai com a venda caindo 16% (a cliente desistiu da nota) não é desconto, e o BV fica;
      a nota que entra ou sai com a mesma venda muda o preço, e o BV acompanha. Grava ``amount_brl``
      E ``value`` (o editor reenvia ``value``; sem isso o próximo salvar desfazia a conta);
    - **em %**: a régua de `valor_do_bv_percentual` sobre a venda e a nota novas;
    - venda que vai a "Valor a definir" ou cortesia: nada muda; na volta a um valor, o BV em % é
      recalculado (é % do preço) e o em reais fica, com o aviso "confira o BV";
    - pago ou no banco: intacto. Evento cancelado ou satélite: nada (o cancelamento é da 1b).

    Args:
        event: O evento, já com a venda e a nota novas atribuídas.
        antes: ``estado_da_venda(event)`` capturado antes de qualquer escrita.
        actor_name: Quem editou, para o `EventLog`.
        tz: Fuso do carimbo do log.
        so_os_reenviados: Só o gêmeo Jinja: os BVs em reais que o envio reenviou sem mexer (as
            chaves que `substituir_acrescimos(reenviados=)` devolveu — a mesma linha, pelo id, com
            o mesmo número). Os outros foram digitados agora e ficam como estão. ``None`` = todos
            (a API grava a venda em outra requisição).

    Returns:
        O aviso para a tela, ou ``None`` quando nada mudou.
    """
    from app.calendar.event_ops import _mesmo_valor, sem_valor_de_venda
    from app.models import EventLog

    if getattr(event, "cancelled_at", None) is not None or getattr(event, "is_satellite", False):
        return None
    venda_antes, nota_antes, cortesia_antes = antes
    venda_nova = _to_decimal(event.sale_value)
    nota_nova = bool(event.with_invoice)
    cortesia_nova = bool(getattr(event, "is_cortesia_permuta", False))
    real_antes = not cortesia_antes and not sem_valor_de_venda(venda_antes)
    real_nova = not cortesia_nova and not sem_valor_de_venda(venda_nova)
    if not real_nova:
        return None
    if real_antes and _mesmo_valor(venda_antes, venda_nova) and nota_antes == nota_nova:
        return None
    linhas = (
        EventAcrescimo.query.filter_by(event_id=event.id, is_bv=True)
        .order_by(EventAcrescimo.id).with_for_update().populate_existing().all()
    )
    a_pagar = [a for a in linhas if (a.bv_payment_status or "nao_pago") not in _BV_CONGELADO]
    if so_os_reenviados is not None:
        saldo = Counter(so_os_reenviados)
        reenviados = []
        for a in a_pagar:
            chave = _bv_na_tela(a.bv_recipient, a.bv_pix, a.is_percent, a.value)
            if a.is_percent:
                reenviados.append(a)  # o % já saiu da régua com a venda nova; refazer dá o mesmo
            elif saldo[chave] > 0:
                saldo[chave] -= 1
                reenviados.append(a)
        a_pagar = reenviados
    if not a_pagar:
        return None
    from app.orcamento.quote_ops import bv_que_acompanha

    mudancas: list[tuple[EventAcrescimo, Decimal, Decimal]] = []
    em_reais_ficou = False
    for a in a_pagar:
        if a.is_percent:
            continue
        valor_antes = _to_decimal(a.amount_brl) or Decimal("0")
        if not real_antes:
            em_reais_ficou = True
            continue
        novo = bv_que_acompanha(
            valor_antes, _liquido(venda_nova, nota_nova), _liquido(_to_decimal(venda_antes), nota_antes)
        )
        if novo != valor_antes:
            a.amount_brl = novo
            a.value = novo
            mudancas.append((a, valor_antes, novo))
    soma_bv_reais = sum(
        (_to_decimal(a.amount_brl) or Decimal("0") for a in linhas if not a.is_percent), Decimal("0")
    )
    soma_perc_bv = sum((_to_decimal(a.value) or Decimal("0") for a in linhas if a.is_percent), Decimal("0"))
    for a in a_pagar:
        if not a.is_percent:
            continue
        valor_antes = _to_decimal(a.amount_brl) or Decimal("0")
        novo = valor_do_bv_percentual(venda_nova, nota_nova, _to_decimal(a.value) or Decimal("0"),
                                      soma_bv_reais, soma_perc_bv)
        if novo is not None and novo != valor_antes:
            a.amount_brl = novo
            mudancas.append((a, valor_antes, novo))
    from app.calendar.orcamento_evento_ops import _fmt_reais

    for a, de, para in mudancas:
        venda_txt = _fmt_reais(venda_antes) if real_antes else "a definir"
        db.session.add(EventLog(
            event_id=event.id, actor_name=actor_name, actor_role="Comercial",
            message=(f"BV acompanhou a venda: de {_fmt_reais(de)} para {_fmt_reais(para)} — venda de "
                     f"{venda_txt} para {_fmt_reais(venda_nova)}, para {a.bv_recipient or '—'}"),
            created_at=datetime.now(tz=tz),
        ))
    db.session.flush()
    db.session.expire(event, ["acrescimos"])
    avisos = []
    if mudancas:
        de = sum((m[1] for m in mudancas), Decimal("0"))
        para = sum((m[2] for m in mudancas), Decimal("0"))
        avisos.append(f"O BV acompanhou a venda: de {_fmt_reais(de)} para {_fmt_reais(para)}. "
                      "Confira o BV e o valor total com BV.")
    if em_reais_ficou:
        avisos.append("Confira o BV: o valor de venda voltou, e o BV em reais ficou como estava.")
    return " ".join(avisos) or None


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


def atualizar_nota(
    nota: Any,
    *,
    amount: Any,
    issue_date: Any,
    arquivo: str | None,
    agora: datetime,
) -> None:
    """Edita UMA nota fiscal já existente. Sem commit.

    Mesma regra de emissão de `sincronizar_notas`: anexar arquivo é o que emite a nota, e o
    carimbo de `issued_at` só acontece na **transição** — reenviar o mesmo arquivo não reescreve
    a data de emissão. `arquivo=None` preserva o que já estava lá, em vez de apagar: um PATCH sem
    upload é edição de valor ou data, não remoção de anexo.
    """
    nota.amount = _to_decimal(amount)
    nota.issue_date = _to_date(issue_date)
    if arquivo:
        nota.file = arquivo
        if nota.status != "emitida":
            nota.status = "emitida"
            nota.issued_at = agora


def remover_nota(nota: Any) -> None:
    """Remove uma nota fiscal do evento. Sem commit.

    O arquivo em disco **não** é apagado de propósito: nota fiscal é documento contábil, e o
    caminho pode estar referenciado num registro anterior. O mesmo vale para o resto do sistema —
    nenhum upload é removido do armazenamento por ação de tela.
    """
    db.session.delete(nota)


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
