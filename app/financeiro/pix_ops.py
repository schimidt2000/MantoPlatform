"""PIX recebido → venda: a regra de vínculo e as respostas do "É esta?" (feature 318).

Núcleo de negócio, sem `flask.request` e **sem commit** (quem chama comita): a rodada da thread
(`pix_email_ops`) e os endpoints (`app/api/pix_write.py`).

A regra (decisão do dono de 22/10, "valor + mais um sinal"):

- **candidatas** são as vendas da cobrança (evento líder, fora cancelada/cortesia/ensaio/loja, com
  saldo) — `cobranca_ops.vendas_desde`, o mesmo universo da lista de cobranças;
- **valor forte** é o PIX igual, ao centavo, ao saldo, ao sinal (metade), a uma parcela ainda não
  coberta, ou a um comprovante anexado à mão que ainda não tem PIX (conciliação);
- **liga sozinho** só com exatamente uma candidata de valor forte **e** o nome do pagador batendo
  com a contratante/empresa/outra cliente da venda **ou** esse pagador já tendo PIX ligado à mesma
  venda/cliente ("já pagou antes" — cada confirmação ensina), **e** o aviso autenticado pelo Inter;
- o resto com alguma candidata vai para "É esta?"; sem candidata, é ignorado (sem fila).

"Prime Dreams" no Inter MEI é tratado à parte: repasse do Inter Prime (o PIX da cliente já foi lido
na Prime) é transferência entre contas; o que sobra é repasse da InfinitePay, que vira "É esta?" só
para o Financeiro, com as vendas no cartão, nunca sozinho.

O pagamento é gravado sempre pelo núcleo de comprovante (`cancel_ops.gravar_comprovante_no_grupo`):
trava do grupo e recálculo do cancelado (306) valem para o PIX como para o comprovante manual.
"""

from __future__ import annotations

import difflib
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal
from itertools import combinations

from sqlalchemy import func, or_

from app import db
from app.constants import (
    EVENT_PAYMENT_ORIGEM_COMPROVANTE,
    EVENT_PAYMENT_ORIGEM_PIX,
    FOLGA_COBRANCA,
    PIX_ESTADO_CONTA_PROPRIA,
    PIX_ESTADO_IGNORADO,
    PIX_ESTADO_LIGADO_AUTO,
    PIX_ESTADO_LIGADO_CONFIRMADO,
    PIX_ESTADO_NOVO,
    PIX_ESTADO_PARA_CONFERIR,
    PIX_ESTADO_SEM_VENDA,
    PIX_ESTADOS_LIGADOS,
    PIX_KIND_LIGADO,
    PIX_KIND_PARA_CONFERIR,
    PIX_KIND_REPASSE,
    PIX_MAX_SUGESTOES,
    PIX_NOME_SEMELHANCA,
    PIX_NOME_STOPWORDS,
    PIX_PAGADOR_PRIME,
    PIX_REPASSE_FAIXA,
    PIX_REPASSE_MAX_VENDAS,
    PIX_REPASSE_PRIME_DIAS,
    PIX_REPASSE_PRIME_MAX_SOMA,
    PIX_SUGESTAO_REPASSE,
    PIX_SUGESTAO_VENDA,
    PIX_TIPO_PIX,
    PIX_TITULAR_PRIME,
    PIX_TOLERANCIA_VALOR,
    RoleName,
    now_sp,
)
from app.models import (
    CalendarEvent,
    ContaRecebimento,
    EventLog,
    EventPayment,
    PixRecebido,
    SiteSetting,
    User,
)
from app.money import format_brl
from app.utils import strip_accents_lower

ENTIDADE = "pix_recebido"
# Comprovante manual anexado até 3 dias antes do PIX ainda pode ser o mesmo pagamento (a cliente
# manda o comprovante no WhatsApp e a comercial anexa; o aviso pode ser processado depois).
_JANELA_CONCILIACAO = timedelta(days=3)
_CENTAVO = Decimal("0.01")


class PixErro(Exception):
    """Recusa de uma resposta ao "É esta?" (vira `json_error` no endpoint)."""

    def __init__(self, mensagem: str, *, status: int = 409, codigo: str | None = None) -> None:
        super().__init__(mensagem)
        self.mensagem = mensagem
        self.status = status
        self.codigo = codigo


# ── nomes ──────────────────────────────────────────────────────────────────────────────────────
def normalizar_nome(nome: str | None) -> str:
    """Minúsculas, sem acento, só letras/dígitos separados por um espaço."""
    texto = strip_accents_lower(nome or "")
    return re.sub(r"[^a-z0-9]+", " ", texto).strip()


def _termos(nome_norm: str) -> set[str]:
    return {t for t in nome_norm.split() if len(t) >= 3 and t not in PIX_NOME_STOPWORDS}


def nome_bate(pagador_norm: str | None, nomes: list[str]) -> bool:
    """O pagador é alguém da venda? Dois termos em comum, ou o nome inteiro muito parecido
    (`PIX_NOME_SEMELHANCA`). Um termo só não basta: "Ana" bateria com toda "Ana Paula" que pagasse
    um valor igual (revisão adversarial da 318)."""
    if not pagador_norm:
        return False
    termos_pagador = _termos(pagador_norm)
    for nome in nomes:
        alvo = normalizar_nome(nome)
        if not alvo:
            continue
        if len(termos_pagador & _termos(alvo)) >= 2:
            return True
        if difflib.SequenceMatcher(None, pagador_norm, alvo).ratio() >= PIX_NOME_SEMELHANCA:
            return True
    return False


def _mesmo_nome(pagador_norm: str | None, referencia_norm: str) -> bool:
    """O pagador É esta pessoa/empresa: os termos da referência (sem "ltda", "me"…) estão todos no
    nome do pagador — "PRIME DREAMS LTDA" é "Prime Dreams"."""
    if not pagador_norm or not referencia_norm:
        return False
    termos_ref = _termos(referencia_norm)
    termos_pag = _termos(pagador_norm)
    if not termos_ref:
        return pagador_norm == referencia_norm
    return termos_ref <= termos_pag and len(termos_pag - termos_ref) <= 1


def pagadores_proprios() -> set[str]:
    """Nomes (normalizados) que são transferência entre contas da empresa — nunca venda."""
    s = db.session.get(SiteSetting, 1)
    texto = (s.pix_pagadores_proprios if s else None) or ""
    return {normalizar_nome(linha) for linha in texto.splitlines() if normalizar_nome(linha)}


def e_pagador_proprio(pagador_norm: str | None) -> bool:
    return any(_mesmo_nome(pagador_norm, ref) for ref in pagadores_proprios())


def conta_por_numero(numero: str | None) -> ContaRecebimento | None:
    if not numero:
        return None
    return ContaRecebimento.query.filter_by(numero_conta=numero).first()


# ── vendas candidatas ──────────────────────────────────────────────────────────────────────────
def vendas_abertas() -> list:
    """As vendas com saldo da cobrança (`VendaResumo`), no corte da Home."""
    from app.financeiro.cobranca_ops import SITUACAO_COM_SALDO, vendas_desde
    from app.formularios.formularios_ops import corte_dia_sp

    return [v for v in vendas_desde(corte_dia_sp()) if v.situacao == SITUACAO_COM_SALDO]


def _nomes_da_venda(venda) -> list[str]:
    nomes: list[str] = []
    for evento in venda.eventos:
        for ec in evento.event_clients or []:
            if ec.client is not None:
                nomes += [ec.client.name or "", ec.client.company or ""]
        if evento.client is not None:
            nomes += [evento.client.name or "", evento.client.company or ""]
    if venda.cliente:
        nomes.append(venda.cliente)
    return [n for n in dict.fromkeys(nomes) if n]


def _clientes_da_venda(venda) -> set[int]:
    ids: set[int] = set()
    for evento in venda.eventos:
        if evento.client_id:
            ids.add(evento.client_id)
        ids |= {ec.client_id for ec in evento.event_clients or []}
    return ids


def _alvos(venda) -> list[tuple[str, Decimal]]:
    """Os valores que um PIX dessa venda costuma ter, com o motivo de cada um."""
    alvos: list[tuple[str, Decimal]] = []
    saldo = venda.saldo
    if saldo is not None and saldo > 0:
        alvos.append(("valor = saldo", saldo))
    if venda.sinal_pendente and venda.valor:
        sinal = (venda.valor / 2 - venda.recebido_liquido).quantize(_CENTAVO)
        if sinal > 0:
            alvos.append(("valor = sinal", sinal))
    recebido, acumulado = venda.recebido_liquido, Decimal("0")
    for parcela in sorted(venda.principal.installments or [], key=lambda p: (p.due_date, p.id)):
        acumulado += Decimal(str(parcela.amount or 0))
        if acumulado > recebido + FOLGA_COBRANCA and parcela.amount:
            alvos.append(("valor = parcela", Decimal(str(parcela.amount))))
    return alvos


def _igual(a: Decimal, b: Decimal) -> bool:
    return abs(Decimal(str(a)) - Decimal(str(b))) <= PIX_TOLERANCIA_VALOR


def _ja_pagou(pix: PixRecebido) -> tuple[set[int], set[int]]:
    """Vendas (principais) e clientes que este pagador já pagou por PIX ligado."""
    from app.financeiro.cobranca_ops import principal_da_venda

    if not pix.pagador_norm:
        return set(), set()
    anteriores = (
        db.session.query(EventPayment)
        .join(PixRecebido, PixRecebido.event_payment_id == EventPayment.id)
        .filter(
            PixRecebido.pagador_norm == pix.pagador_norm,
            PixRecebido.estado.in_(PIX_ESTADOS_LIGADOS),
            PixRecebido.id != pix.id,
        )
        .all()
    )
    principais: set[int] = set()
    clientes: set[int] = set()
    for pagamento in anteriores:
        evento = db.session.get(CalendarEvent, pagamento.event_id)
        if evento is None:
            continue
        principal = principal_da_venda(evento)
        principais.add(principal.id)
        for e in (principal, *(principal.satellites or [])):
            if e.client_id:
                clientes.add(e.client_id)
            clientes |= {ec.client_id for ec in e.event_clients or []}
    return principais, clientes


@dataclass
class Sugestao:
    """Uma resposta possível ao "É esta?": uma venda (ou 1–3 no repasse) e por quê."""

    event_ids: list[int]
    motivos: list[str]
    valor_alvo: Decimal
    forte: bool = False
    nome: bool = False
    ja_pagou: bool = False
    conciliar: int | None = None  # id do comprovante manual a conciliar
    pontos: int = 0
    distancia: int = 0
    extra: dict = field(default_factory=dict)

    def para_json(self) -> dict:
        return {
            "event_ids": self.event_ids,
            "motivos": self.motivos,
            "valor_alvo": str(self.valor_alvo),
            "conciliar": self.conciliar,
            "pontos": self.pontos,
            **self.extra,
        }


def _comprovantes_conciliaveis(pix: PixRecebido) -> list[EventPayment]:
    """Comprovantes manuais do mesmo valor, recentes, que ainda não têm PIX."""
    desde = pix.recebido_em + timedelta(hours=3) - _JANELA_CONCILIACAO  # SP → UTC, com folga
    ligados = db.session.query(PixRecebido.event_payment_id).filter(
        PixRecebido.event_payment_id.isnot(None)
    )
    consulta = EventPayment.query.filter(
        EventPayment.origem == EVENT_PAYMENT_ORIGEM_COMPROVANTE,
        EventPayment.amount.between(pix.valor - PIX_TOLERANCIA_VALOR, pix.valor + PIX_TOLERANCIA_VALOR),
        EventPayment.created_at >= desde,
        EventPayment.id.notin_(ligados),
    )
    if pix.conta_id is not None:
        # Comprovante marcado com OUTRA conta é outro dinheiro (ex.: o sinal pago na Cora).
        consulta = consulta.filter(
            or_(EventPayment.conta_id.is_(None), EventPayment.conta_id == pix.conta_id)
        )
    return consulta.order_by(EventPayment.id).all()


def sugestoes_de_venda(pix: PixRecebido, vendas: list | None = None) -> list[Sugestao]:
    """Todas as candidatas do PIX comum (sem cortar em 3), da melhor para a pior."""
    from app.financeiro.cobranca_ops import (
        motivo_fora_da_venda,
        principal_da_venda,
        resumo_da_venda_do_evento,
    )

    vendas = vendas if vendas is not None else vendas_abertas()
    abertas = {v.principal.id for v in vendas}
    descartados = set(pix.descartados or [])
    principais_pagos, clientes_pagos = _ja_pagou(pix)
    por_principal: dict[int, Sugestao] = {}

    # Comprovante manual do mesmo valor pode ser este PIX — ou outro pagamento de valor igual (sinal
    # e saldo de 50% são iguais por construção). Por isso a conciliação NUNCA é automática: vira
    # "É esta?" com as duas saídas ("é este comprovante" / "é pagamento novo").
    for pagamento in _comprovantes_conciliaveis(pix):
        evento = db.session.get(CalendarEvent, pagamento.event_id)
        if evento is None:
            continue
        principal = principal_da_venda(evento)
        if principal.id in descartados or motivo_fora_da_venda(principal) is not None:
            continue
        venda = resumo_da_venda_do_evento(principal)
        nome = nome_bate(pix.pagador_norm, _nomes_da_venda(venda))
        ja = principal.id in principais_pagos or bool(_clientes_da_venda(venda) & clientes_pagos)
        motivos = ["comprovante já anexado"] + (["nome bate"] if nome else []) + (
            ["já pagou antes"] if ja else []
        )
        por_principal.setdefault(
            principal.id,
            Sugestao([principal.id], motivos, Decimal(str(pagamento.amount)), forte=True, nome=nome,
                     ja_pagou=ja, conciliar=pagamento.id,
                     extra={"pode_novo": principal.id in abertas}),
        )

    for venda in vendas:
        pid = venda.principal.id
        if pid in descartados or pid in por_principal:
            continue
        motivos = [m for m, alvo in _alvos(venda) if _igual(alvo, pix.valor)]
        forte = bool(motivos)
        nome = nome_bate(pix.pagador_norm, _nomes_da_venda(venda))
        ja = pid in principais_pagos or bool(_clientes_da_venda(venda) & clientes_pagos)
        saldo = venda.saldo or Decimal("0")
        if not forte and not ((nome or ja) and pix.valor <= saldo + PIX_TOLERANCIA_VALOR):
            continue
        if nome:
            motivos.append("nome bate")
        if ja:
            motivos.append("já pagou antes")
        por_principal[pid] = Sugestao([pid], motivos, saldo, forte=forte, nome=nome, ja_pagou=ja)

    for s in por_principal.values():
        s.pontos = 4 * s.forte + 2 * s.ja_pagou + s.nome
        evento = db.session.get(CalendarEvent, s.event_ids[0])
        s.distancia = abs((evento.start_at - pix.recebido_em).days) if evento and evento.start_at else 99999
    return sorted(por_principal.values(), key=lambda s: (-s.pontos, s.distancia, s.event_ids[0]))


# ── "Prime Dreams" no MEI ──────────────────────────────────────────────────────────────────────
def _e_da_prime(pix: PixRecebido) -> bool:
    if pix.conta is not None:
        return pix.conta.apelido == "Inter Prime"
    return (pix.titular_lido or "").upper() == PIX_TITULAR_PRIME


def e_repasse_prime_dreams(pix: PixRecebido) -> bool:
    """PIX de "Prime Dreams" que caiu fora da Prime (no MEI): repasse, não venda."""
    return _mesmo_nome(pix.pagador_norm, PIX_PAGADOR_PRIME) and not _e_da_prime(pix)


def _pares_ja_usados(pix: PixRecebido) -> set[int]:
    """PIX da Prime que já explicaram outro repasse — não servem de par duas vezes."""
    usados: set[int] = set()
    outros = PixRecebido.query.filter(
        PixRecebido.estado == PIX_ESTADO_CONTA_PROPRIA,
        PixRecebido.id != pix.id,
        PixRecebido.recebido_em >= pix.recebido_em - timedelta(days=PIX_REPASSE_PRIME_DIAS + 3),
    ).all()
    for outro in outros:
        for c in outro.candidatos or []:
            usados |= set(c.get("par_prime") or [])
    return usados


def _par_na_prime(pix: PixRecebido) -> list[PixRecebido] | None:
    """O(s) PIX da Prime que este repasse está passando adiante (mesmo valor ou soma de até 3)."""
    usados = _pares_ja_usados(pix)
    janela = (
        PixRecebido.query.filter(
            PixRecebido.tipo == PIX_TIPO_PIX,
            PixRecebido.id != pix.id,
            PixRecebido.recebido_em >= pix.recebido_em - timedelta(days=PIX_REPASSE_PRIME_DIAS),
            PixRecebido.recebido_em <= pix.recebido_em + timedelta(hours=1),
            PixRecebido.valor.isnot(None),
        )
        .order_by(PixRecebido.recebido_em.desc())
        .all()
    )
    da_prime = [p for p in janela if _e_da_prime(p) and p.id not in usados][:20]
    for tamanho in range(1, PIX_REPASSE_PRIME_MAX_SOMA + 1):
        for grupo in combinations(da_prime, tamanho):
            if _igual(sum((p.valor for p in grupo), Decimal("0")), pix.valor):
                return list(grupo)
    return None


def sugestoes_de_repasse(pix: PixRecebido, vendas: list | None = None) -> list[Sugestao]:
    """Vendas no cartão cujo valor cobrado explica o repasse da InfinitePay (88–100%, até 3)."""
    vendas = vendas if vendas is not None else vendas_abertas()
    descartados = set(pix.descartados or [])
    cartao = [
        v for v in vendas
        if v.principal.payment_method == "cartao" and (v.saldo or 0) > 0
        and v.principal.id not in descartados
    ]
    cartao.sort(key=lambda v: abs((v.principal.start_at - pix.recebido_em).days) if v.principal.start_at else 99999)
    cartao = cartao[:30]  # teto da busca: 30 vendas, até 3 por grupo
    minimo, maximo = PIX_REPASSE_FAIXA
    achadas: list[Sugestao] = []
    for tamanho in range(1, PIX_REPASSE_MAX_VENDAS + 1):
        for grupo in combinations(cartao, tamanho):
            soma = sum((v.saldo for v in grupo), Decimal("0"))
            if soma * minimo - PIX_TOLERANCIA_VALOR <= pix.valor <= soma * maximo + PIX_TOLERANCIA_VALOR:
                taxa = soma - pix.valor
                achadas.append(
                    Sugestao(
                        [v.principal.id for v in grupo],
                        [f"taxa {format_brl(taxa, prefix=True)}"],
                        soma,
                        pontos=-tamanho,
                        extra={"taxa": str(taxa.quantize(_CENTAVO))},
                    )
                )
    alvo = Decimal("0.96")
    achadas.sort(key=lambda s: (len(s.event_ids), abs(pix.valor / s.valor_alvo - alvo)))
    return achadas


# ── decidir e ligar ────────────────────────────────────────────────────────────────────────────
def _rotulo_conta(pix: PixRecebido) -> str:
    return pix.conta.apelido if pix.conta is not None else "conta não cadastrada"


def _log(event_id: int, texto: str, usuario: User | None, pix: PixRecebido) -> None:
    if usuario is None:
        nome, papel = f"Sistema (PIX · {_rotulo_conta(pix)})", "Sistema"
    else:
        nome = usuario.name
        papel = ", ".join(r.name for r in usuario.roles)[:60] or None
    db.session.add(EventLog(event_id=event_id, actor_name=nome[:100], actor_role=papel, message=texto[:500]))


def _ligar_uma(
    pix: PixRecebido,
    principal_id: int,
    *,
    valor: Decimal,
    usuario: User | None,
    conciliar: int | None = None,
    conta_id: int | None = None,
) -> EventPayment | None:
    """Registra (ou concilia) o pagamento de uma venda. Sem commit.

    No automático (`usuario=None`), a venda é travada ANTES de gravar e a conciliação é refeita sob
    a trava: se a comercial anexou um comprovante do mesmo valor entre a leitura e a gravação,
    devolve `None` (o PIX vai para "É esta?" — nunca conta em dobro).
    """
    from app.calendar.cancel_ops import gravar_comprovante_no_grupo, travar_grupo

    evento = db.session.get(CalendarEvent, principal_id)
    if usuario is None and conciliar is None:
        travar_grupo(evento)
        db.session.expire_all()
        ids_grupo = {evento.id, *(e.id for e in evento.satellites or [])}
        if any(p.event_id in ids_grupo for p in _comprovantes_conciliaveis(pix)):
            return None
    if conciliar is not None:
        pagamento = db.session.get(EventPayment, conciliar)
        if pagamento.conta_id is None:
            pagamento.conta_id = pix.conta_id
        texto = (
            f"PIX de {format_brl(pix.valor, prefix=True)} de {pix.pagador_nome or '—'} "
            f"({_rotulo_conta(pix)}) conciliado com o comprovante já anexado"
        )
    else:
        pagamento = gravar_comprovante_no_grupo(
            evento,
            "adicionar",
            actor=usuario,
            valor=valor,
            origem=EVENT_PAYMENT_ORIGEM_PIX,
            conta_id=conta_id if conta_id is not None else pix.conta_id,
        )
        texto = (
            f"Pagamento de {format_brl(valor, prefix=True)} registrado pelo PIX de "
            f"{pix.pagador_nome or '—'} ({_rotulo_conta(pix)}, {pix.recebido_em:%d/%m %H:%M})"
        )
    _log(evento.id, texto + (" — automático" if usuario is None else ""), usuario, pix)
    return pagamento


def _avisar(pix: PixRecebido, kind: str, sugestoes: list[Sugestao]) -> None:
    from app.notificacoes import notificacoes_ops as notif

    valor = format_brl(pix.valor, prefix=True)
    quem = pix.pagador_nome or "—"
    destinatarios: list[User] = []
    if kind == PIX_KIND_LIGADO or kind == PIX_KIND_PARA_CONFERIR:
        if sugestoes:
            evento = db.session.get(CalendarEvent, sugestoes[0].event_ids[0])
            if evento is not None and evento.seller is not None and evento.seller.is_active:
                destinatarios.append(evento.seller)
    if kind == PIX_KIND_PARA_CONFERIR:
        destinatarios += notif.resolver_destinatarios((RoleName.FINANCEIRO,))
    if kind == PIX_KIND_REPASSE:
        destinatarios = notif.resolver_destinatarios((RoleName.FINANCEIRO, RoleName.SUPERADMIN))
    if not destinatarios:
        return
    titulos = {
        PIX_KIND_LIGADO: f"PIX de {valor} entrou na venda — {quem}",
        PIX_KIND_PARA_CONFERIR: f"PIX de {valor} para conferir — é desta venda? ({quem})",
        PIX_KIND_REPASSE: f"Repasse da InfinitePay de {valor} para conferir",
    }
    link = "/pix"
    if kind == PIX_KIND_LIGADO and sugestoes:
        link = f"/events/{sugestoes[0].event_ids[0]}"
    notif.emitir(
        kind,
        title=titulos[kind],
        body=f"{_rotulo_conta(pix)} · {pix.recebido_em:%d/%m/%Y %H:%M}",
        link_path=link,
        entidade=(ENTIDADE, pix.id),
        dedupe_key=f"{kind}:{pix.id}",
        destinatarios=list({u.id: u for u in destinatarios}.values()),
    )


def vincular(pix: PixRecebido, *, vendas: list | None = None, permitir_auto: bool = True) -> None:
    """Decide o que fazer com um PIX novo (ou reavaliado). Sem commit.

    `permitir_auto=False` no "Desfazer": a ligação desfeita não volta sozinha.
    """
    if pix.tipo != PIX_TIPO_PIX or pix.valor is None:
        pix.estado = PIX_ESTADO_IGNORADO
        return
    vendas = vendas if vendas is not None else vendas_abertas()

    if e_repasse_prime_dreams(pix):
        par = _par_na_prime(pix)
        if par:
            pix.estado = PIX_ESTADO_CONTA_PROPRIA
            pix.candidatos = [{"par_prime": [p.id for p in par]}]  # não serve de par de novo
            pix.motivo = "repasse da Prime (" + ", ".join(
                f"PIX de {format_brl(p.valor, prefix=True)} em {p.recebido_em:%d/%m}" for p in par
            ) + ")"
            return
        sugestoes = sugestoes_de_repasse(pix, vendas)[:PIX_MAX_SUGESTOES]
        if sugestoes:
            pix.estado = PIX_ESTADO_PARA_CONFERIR
            pix.tipo_sugestao = PIX_SUGESTAO_REPASSE
            pix.candidatos = [s.para_json() for s in sugestoes]
            pix.motivo = "repasse da InfinitePay (sem PIX da Prime que explique o valor)"
            _avisar(pix, PIX_KIND_REPASSE, sugestoes)
        else:
            pix.estado = PIX_ESTADO_SEM_VENDA
            pix.candidatos = []
            pix.motivo = "repasse sem par na Prime e sem venda no cartão que explique o valor"
        return

    if e_pagador_proprio(pix.pagador_norm):
        pix.estado = PIX_ESTADO_CONTA_PROPRIA
        pix.motivo = "pagador próprio (transferência entre contas)"
        return

    sugestoes = sugestoes_de_venda(pix, vendas)
    fortes = [s for s in sugestoes if s.forte]
    pix.tipo_sugestao = PIX_SUGESTAO_VENDA
    if (
        permitir_auto
        and len(fortes) == 1
        and fortes[0].conciliar is None  # conciliação sempre pergunta (pode ser outro pagamento)
        and (fortes[0].nome or fortes[0].ja_pagou)
        and pix.autenticado
    ):
        escolhida = fortes[0]
        pagamento = _ligar_uma(pix, escolhida.event_ids[0], valor=pix.valor, usuario=None)
        if pagamento is not None:
            db.session.flush()
            pix.estado = PIX_ESTADO_LIGADO_AUTO
            pix.event_payment_id = pagamento.id
            pix.candidatos = [escolhida.para_json()]
            pix.motivo = "; ".join(escolhida.motivos)
            pix.decidido_em = now_sp()
            _avisar(pix, PIX_KIND_LIGADO, [escolhida])
            return
        # Um comprovante do mesmo valor apareceu sob a trava: pergunta, com ele entre as opções.
        sugestoes = sugestoes_de_venda(pix, vendas)
        fortes = [s for s in sugestoes if s.forte]
    if sugestoes:
        pix.estado = PIX_ESTADO_PARA_CONFERIR
        pix.candidatos = [s.para_json() for s in sugestoes[:PIX_MAX_SUGESTOES]]
        pix.motivo = "e-mail não autenticado pelo Inter" if not pix.autenticado else (
            "mais de uma venda com esse valor" if len(fortes) > 1 else "só o valor bate"
            if fortes else "o nome bate, o valor não"
        )
        _avisar(pix, PIX_KIND_PARA_CONFERIR, sugestoes)
        return
    pix.estado = PIX_ESTADO_SEM_VENDA
    pix.candidatos = []
    pix.motivo = "nenhuma venda aberta com esse valor ou esse pagador"


# ── respostas ao "É esta?" ─────────────────────────────────────────────────────────────────────
def _travar(pix_id: int) -> PixRecebido:
    pix = PixRecebido.query.filter_by(id=pix_id).with_for_update().first()
    if pix is None:
        raise PixErro("PIX não encontrado.", status=404)
    return pix


def confirmar(
    pix_id: int, event_ids: list[int], usuario: User, *, novo: bool = False
) -> PixRecebido:
    """"É esta" / "Outra venda…" (e, no repasse, as 1–3 vendas sugeridas). Sem commit.

    Quando a venda tem um comprovante manual do mesmo valor, `novo=False` concilia com ele ("é este
    comprovante") e `novo=True` registra outro pagamento ("é pagamento novo").
    """
    from app.financeiro.cobranca_ops import principal_da_venda

    pix = _travar(pix_id)
    if pix.estado != PIX_ESTADO_PARA_CONFERIR:
        raise PixErro("Este PIX já foi decidido.", codigo="ja_decidido")
    repasse = pix.tipo_sugestao == PIX_SUGESTAO_REPASSE

    principais: list[int] = []
    for eid in event_ids:
        evento = db.session.get(CalendarEvent, eid) if eid else None
        if evento is None:
            raise PixErro("Venda não encontrada.", status=404)
        principais.append(principal_da_venda(evento).id)
    principais = list(dict.fromkeys(principais))  # dois dias da mesma venda são UMA venda
    if not principais or (not repasse and len(principais) != 1) or len(principais) > PIX_REPASSE_MAX_VENDAS:
        raise PixErro("Escolha a venda deste PIX.", status=400, codigo="venda_obrigatoria")

    abertas = {v.principal.id: v for v in vendas_abertas()}
    pagamentos: list[EventPayment] = []
    if repasse:
        sugeridos = [set(c.get("event_ids") or []) for c in pix.candidatos or []]
        if set(principais) not in sugeridos:
            raise PixErro(
                "Escolha uma das combinações sugeridas para este repasse.",
                status=400,
                codigo="repasse_fora_das_sugestoes",
            )
        # O cliente pagou na InfinitePay (conta da Prime): é essa a conta do pagamento, não o MEI
        # para onde o dono passou o dinheiro depois — senão o total do MEI sairia inflado.
        infinitepay = ContaRecebimento.query.filter_by(banco="infinitepay").first()
        cobrado = Decimal("0")
        for pid in principais:
            venda = abertas.get(pid)
            if venda is None:
                raise PixErro("Essa venda não está mais em aberto.", codigo="venda_indisponivel")
            cobrado += venda.saldo
            pagamentos.append(
                _ligar_uma(
                    pix, pid, valor=venda.saldo, usuario=usuario,
                    conta_id=infinitepay.id if infinitepay else None,
                )
            )
        taxa = cobrado - pix.valor
        pix.motivo = (
            f"repasse da InfinitePay: cobrado {format_brl(cobrado, prefix=True)}, "
            f"taxa {format_brl(taxa, prefix=True)}"
        )
    else:
        pid = principais[0]
        conciliavel = None
        if not novo:
            conciliavel = next(
                (s for s in sugestoes_de_venda(pix) if s.event_ids[0] == pid and s.conciliar), None
            )
        if conciliavel is None and pid not in abertas:
            raise PixErro("Essa venda não está mais em aberto.", codigo="venda_indisponivel")
        pagamentos.append(
            _ligar_uma(
                pix, pid, valor=pix.valor, usuario=usuario,
                conciliar=conciliavel.conciliar if conciliavel else None,
            )
        )
        pix.motivo = f"confirmado por {usuario.name}"
    db.session.flush()
    pix.estado = PIX_ESTADO_LIGADO_CONFIRMADO
    pix.event_payment_id = pagamentos[0].id
    pix.pagamentos_extra = [p.id for p in pagamentos[1:]]
    pix.decidido_por_id = usuario.id
    pix.decidido_em = now_sp()
    _marcar_lidas(pix)
    return pix


def descartar(pix_id: int, event_id: int, usuario: User) -> PixRecebido:
    """"Não é esta": a venda sai das sugestões; sem nenhuma, o PIX sai da fila. Sem commit."""
    from app.financeiro.cobranca_ops import principal_da_venda

    pix = _travar(pix_id)
    if pix.estado != PIX_ESTADO_PARA_CONFERIR:
        raise PixErro("Este PIX já foi decidido.", codigo="ja_decidido")
    evento = db.session.get(CalendarEvent, event_id)
    pid = principal_da_venda(evento).id if evento is not None else event_id
    pix.descartados = list(dict.fromkeys([*(pix.descartados or []), pid]))
    restantes = [c for c in (pix.candidatos or []) if pid not in (c.get("event_ids") or [])]
    pix.candidatos = restantes
    if not restantes:
        pix.estado = PIX_ESTADO_SEM_VENDA
        pix.decidido_por_id = usuario.id
        pix.decidido_em = now_sp()
        pix.motivo = f"sugestões descartadas por {usuario.name}"
        _marcar_lidas(pix)
    return pix


def nao_e_venda(pix_id: int, usuario: User) -> PixRecebido:
    """"Não é de venda": sai da fila e não é mais reavaliado. Sem commit."""
    pix = _travar(pix_id)
    if pix.estado != PIX_ESTADO_PARA_CONFERIR:
        raise PixErro("Este PIX já foi decidido.", codigo="ja_decidido")
    pix.estado = PIX_ESTADO_SEM_VENDA
    pix.candidatos = []
    pix.decidido_por_id = usuario.id
    pix.decidido_em = now_sp()
    pix.motivo = f"não é de venda (por {usuario.name})"
    _marcar_lidas(pix)
    return pix


def desfazer(pix_id: int, usuario: User) -> PixRecebido:
    """Desfaz uma ligação (automática ou confirmada). Sem commit.

    Pagamento de PIX ainda sem arquivo sai (pelo núcleo); com arquivo anexado depois, ou comprovante
    manual conciliado, fica como comprovante manual. O PIX volta a "para conferir" (sem ligar de
    novo sozinho) ou, sem nenhuma candidata, a "sem venda".
    """
    from app.calendar.cancel_ops import gravar_comprovante_no_grupo

    pix = _travar(pix_id)
    if pix.estado not in PIX_ESTADOS_LIGADOS:
        raise PixErro("Este PIX não está ligado a uma venda.", codigo="nao_ligado")
    ids = [i for i in [pix.event_payment_id, *(pix.pagamentos_extra or [])] if i]
    pix.event_payment_id = None
    pix.pagamentos_extra = []
    db.session.flush()
    for pid in ids:
        pagamento = db.session.get(EventPayment, pid)
        if pagamento is None:
            continue
        evento = db.session.get(CalendarEvent, pagamento.event_id)
        if pagamento.origem == EVENT_PAYMENT_ORIGEM_PIX and not pagamento.file_path:
            valor = pagamento.amount
            gravar_comprovante_no_grupo(evento, "excluir", actor=usuario, comprovante=pagamento)
            _log(evento.id, f"Desfez o PIX de {format_brl(pix.valor, prefix=True)}: pagamento de "
                 f"{format_brl(valor, prefix=True)} excluído", usuario, pix)
        else:
            pagamento.origem = EVENT_PAYMENT_ORIGEM_COMPROVANTE
            _log(evento.id, f"Desfez o PIX de {format_brl(pix.valor, prefix=True)}: o comprovante "
                 "anexado fica como pagamento manual", usuario, pix)
    db.session.flush()
    pix.estado = PIX_ESTADO_NOVO
    pix.decidido_por_id = usuario.id
    pix.decidido_em = now_sp()
    vincular(pix, permitir_auto=False)
    if pix.estado == PIX_ESTADO_SEM_VENDA:
        pix.motivo = f"desfeito por {usuario.name}; nenhuma venda aberta com esse valor"
    return pix


def _marcar_lidas(pix: PixRecebido) -> None:
    from app.notificacoes import notificacoes_ops as notif

    notif.marcar_lidas_por_entidade(ENTIDADE, pix.id)


# ── leitura ────────────────────────────────────────────────────────────────────────────────────
def listar(aba: str, *, ver_repasse: bool) -> list[PixRecebido]:
    consulta = PixRecebido.query
    if aba == "ligados":
        consulta = consulta.filter(
            PixRecebido.estado.in_(PIX_ESTADOS_LIGADOS),
            PixRecebido.recebido_em >= now_sp() - timedelta(days=30),
        )
    else:
        consulta = consulta.filter(PixRecebido.estado == PIX_ESTADO_PARA_CONFERIR)
    if not ver_repasse:
        consulta = consulta.filter(
            db.or_(PixRecebido.tipo_sugestao.is_(None), PixRecebido.tipo_sugestao != PIX_SUGESTAO_REPASSE)
        )
    return consulta.order_by(PixRecebido.recebido_em.desc()).limit(200).all()


def contagem_para_conferir(*, ver_repasse: bool) -> int:
    return len(listar("conferir", ver_repasse=ver_repasse))


def _evento_resumo(evento: CalendarEvent, alvo: str | None) -> dict:
    from app.financeiro.vendas_ops import contratante_name

    return {
        "event_id": evento.id,
        "titulo": evento.title,
        "data": evento.start_at.date().isoformat() if evento.start_at else None,
        "cliente": contratante_name(evento),
        "vendedor": evento.seller.name if evento.seller else None,
        "saldo": alvo,
    }


def para_api(pix: PixRecebido) -> dict:
    """O PIX como a tela o mostra (contrato `GET /api/pix`)."""
    sugestoes = []
    for c in pix.candidatos or []:
        eventos = [db.session.get(CalendarEvent, i) for i in c.get("event_ids") or []]
        eventos = [e for e in eventos if e is not None]
        if not eventos:
            continue
        if pix.tipo_sugestao == PIX_SUGESTAO_REPASSE:
            sugestoes.append({
                "vendas": [_evento_resumo(e, None) for e in eventos],
                "soma": c.get("valor_alvo"),
                "taxa": c.get("taxa"),
                "motivos": c.get("motivos") or [],
                "event_ids": [e.id for e in eventos],
            })
        else:
            item = _evento_resumo(eventos[0], c.get("valor_alvo"))
            item["motivos"] = c.get("motivos") or []
            item["event_ids"] = [eventos[0].id]
            # Comprovante manual do mesmo valor: a tela oferece "é este comprovante" e "é novo".
            item["conciliar"] = c.get("conciliar")
            item["pode_novo"] = bool(c.get("pode_novo", True))
            sugestoes.append(item)
    pagamento = None
    if pix.pagamento is not None:
        ev = db.session.get(CalendarEvent, pix.pagamento.event_id)
        pagamento = {
            "id": pix.pagamento.id,
            "event_id": pix.pagamento.event_id,
            "titulo": ev.title if ev else None,
            "valor": str(pix.pagamento.amount) if pix.pagamento.amount is not None else None,
        }
    return {
        "id": pix.id,
        "valor": str(pix.valor) if pix.valor is not None else None,
        "pagador": pix.pagador_nome,
        "conta": pix.conta.apelido if pix.conta else None,
        "recebido_em": pix.recebido_em.isoformat(timespec="seconds"),
        "autenticado": pix.autenticado,
        "estado": pix.estado,
        "tipo_sugestao": pix.tipo_sugestao,
        "sugestoes": sugestoes,
        "pagamento": pagamento,
        "decidido_por": pix.decidido_por.name if pix.decidido_por else None,
        "decidido_em": pix.decidido_em.isoformat(timespec="seconds") if pix.decidido_em else None,
        "motivo": pix.motivo,
    }


def resumo_por_conta(meses: int) -> dict:
    """Total recebido por conta e por mês (mês do registro do pagamento), últimos `meses`."""
    meses = max(1, min(int(meses or 6), 24))
    hoje = now_sp().date().replace(day=1)
    inicio = hoje
    for _ in range(meses - 1):
        inicio = (inicio - timedelta(days=1)).replace(day=1)
    # `created_at` é UTC: o mês é o de São Paulo (pagamento das 21h às 24h do último dia é do mês).
    mes = func.to_char(EventPayment.created_at - timedelta(hours=3), "YYYY-MM")
    linhas = (
        db.session.query(ContaRecebimento.apelido, mes, func.sum(EventPayment.amount))
        .outerjoin(ContaRecebimento, ContaRecebimento.id == EventPayment.conta_id)
        .filter(EventPayment.created_at >= datetime.combine(inicio, datetime.min.time()) + timedelta(hours=3))
        .group_by(ContaRecebimento.apelido, mes)
        .all()
    )
    lista_meses: list[str] = []
    d = inicio
    while d <= hoje:
        lista_meses.append(d.strftime("%Y-%m"))
        d = (d + timedelta(days=32)).replace(day=1)
    contas: dict[str, dict[str, str]] = {}
    sem_conta: dict[str, str] = {}
    for apelido, m, soma in linhas:
        alvo = contas.setdefault(apelido, {}) if apelido else sem_conta
        alvo[m] = str(Decimal(str(soma or 0)).quantize(_CENTAVO))
    ordem = [c.apelido for c in ContaRecebimento.query.order_by(ContaRecebimento.id).all()]
    return {
        "meses": lista_meses,
        "contas": [{"conta": a, "por_mes": contas.get(a, {})} for a in ordem],
        "sem_conta": sem_conta,
    }


# ── comprovante manual × PIX (usado pelo núcleo, sob a trava do grupo) ──────────────────────────
def pagamento_pix_sem_arquivo_igual(event: CalendarEvent, valor: Decimal) -> EventPayment | None:
    """O pagamento de PIX (sem arquivo) do grupo da venda com o mesmo valor, se houver."""
    from app.financeiro.cobranca_ops import principal_da_venda

    principal = principal_da_venda(event)
    ids = [principal.id, *(e.id for e in principal.satellites or [])]
    return (
        EventPayment.query.filter(
            EventPayment.event_id.in_(ids),
            EventPayment.origem == EVENT_PAYMENT_ORIGEM_PIX,
            EventPayment.file_path.is_(None),
            EventPayment.amount.between(valor - PIX_TOLERANCIA_VALOR, valor + PIX_TOLERANCIA_VALOR),
        )
        .order_by(EventPayment.id)
        .first()
    )


def resumo_da_duplicata(pagamento: EventPayment) -> dict:
    """O que a tela mostra na pergunta "esse comprovante é do PIX que já entrou?"."""
    pix = PixRecebido.query.filter_by(event_payment_id=pagamento.id).first()
    return {
        "id": pagamento.id,
        "valor": str(pagamento.amount),
        "conta": pagamento.conta.apelido if pagamento.conta else None,
        "recebido_em": pix.recebido_em.isoformat(timespec="seconds") if pix else None,
        "pagador": pix.pagador_nome if pix else None,
    }


def pix_do_pagamento(pagamento_id: int) -> PixRecebido | None:
    """O PIX ligado a este pagamento (direto ou como pagamento extra de um repasse)."""
    pix = PixRecebido.query.filter_by(event_payment_id=pagamento_id).first()
    if pix is not None:
        return pix
    for candidato in PixRecebido.query.filter(
        PixRecebido.estado.in_(PIX_ESTADOS_LIGADOS),
        PixRecebido.tipo_sugestao == PIX_SUGESTAO_REPASSE,
    ).all():
        if pagamento_id in (candidato.pagamentos_extra or []):
            return candidato
    return None
