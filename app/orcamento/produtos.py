"""Produtos de tabela (feature 309) — fonte única da Visita Mágica para a venda e para o teto.

Um produto tem PREÇO ao cliente (fixo por visita; por faixa de data especial quando houver) e a
COMPOSIÇÃO de vagas; o cachê de cada vaga vem "pela tabela vigente na data" (`cache: None`) ou é um
valor fixo. O preço não passa pelo markup e não escala com a duração; o cachê das vagas vira o TETO
da vaga do evento (cachê nasce vazio — decisões 236/238). Tudo que a venda (`quote_ops`) e o teto
(`calendar.routes._compute_performer_caches`) precisam do produto sai daqui, com os mesmos argumentos
(`cfg`, `faixa`) — é o que impede "preço certo com teto errado" (lição da 307 com `cache_na_faixa`).

Puro: sem `flask.request`, sem banco (os getters de `pricing` releem a tabela, como sempre fizeram).
"""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from . import settings as _cfg
from .pricing import (
    cache_na_faixa,
    calcular_maquiador,
    get_ator_prices,
    get_coordenador_prices,
    get_especial_prices,
)

MARCA_PRODUTO = "cachê da tabela · produto"
AVISO_NOEL_AVULSO = 'Para a Visita Mágica use o produto de tabela em vez do item "Papai Noel".'
AVISO_ESTIMATIVA = (
    '"{rotulo}" não tem preço de {faixa}: preço ESTIMADO (cachês × {fator} × markup {markup}). '
    "Confira antes de enviar."
)
AVISO_VAGA_SEM_CACHE = (
    '"{label}" não está na tabela de preços: a vaga nasce sem teto e ficou fora da estimativa.'
)
NOTA_PRODUTO_SUMIU = 'produto "{chave}" não está mais na tabela de preços — teto não aplicado'
NOTA_VAGA_SEM_TABELA = '"{label}" não está na tabela de preços — teto não aplicado'
DETALHE_TABELA = "preço de tabela"
DETALHE_ESTIMADO = "preço estimado (sem preço de {faixa})"
PERSONAGEM_DO_PRODUTO = "Papai Noel"
_CENTAVO = Decimal("0.01")
_DURACOES = ("1h", "2h", "3h", "4h")


class ProdutoDesconhecido(Exception):
    """A seleção cita um produto que não está (mais) na tabela de preços."""

    def __init__(self, chave: str) -> None:
        super().__init__(chave)
        self.chave = chave


def _q(valor: float | Decimal) -> float:
    """Dinheiro com 2 casas, HALF_UP (Princípio IX) — `round()` do Python arredonda ao par."""
    return float(Decimal(str(valor)).quantize(_CENTAVO, rounding=ROUND_HALF_UP))


def _fmt_brl(valor: float) -> str:
    return "R$ " + f"{valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _num(valor: Any) -> str:
    return f"{float(valor):g}".replace(".", ",")


# ── resolução ───────────────────────────────────────────────────────────────────────────────────
def vagas_congeladas(produto: dict) -> list[dict]:
    """As vagas como o snapshot as guarda: só o que o teto precisa para emitir a vaga depois."""
    return [
        {
            "label": v["label"],
            "tipo": v["tipo"],
            "cache": v.get("cache"),
            "needs_makeup": bool(v.get("needs_makeup")),
        }
        for v in produto.get("vagas") or []
    ]


def resolver_produtos(selecao: Any, cfg: dict, *, tolerar_ausente: bool = False) -> list[dict]:
    """Cada item da seleção vira um produto resolvido, na ordem em que foi vendido.

    A seleção é a lista do payload (``[{"chave"}]``) ou a lista CONGELADA do snapshot (``{chave,
    rotulo, preco_aplicado, faixa_chave, estimado, vagas}``). Produto que ainda existe na tabela sai
    com a definição viva (preço e composição atuais) — e, quando o item traz vagas congeladas, são
    ELAS que mandam na composição (o que foi vendido), a tabela só dá o valor do cachê. Produto que
    sumiu: na venda levanta `ProdutoDesconhecido`; no teto (``tolerar_ausente``) sai como fantasma
    (``existe=False``) com as vagas congeladas, para o Noel não sumir do elenco.
    """
    tabela = cfg.get("produtos") if isinstance(cfg.get("produtos"), dict) else {}
    resolvidos: list[dict] = []
    for item in selecao or []:
        if not isinstance(item, dict):
            continue
        chave = str(item.get("chave") or "").strip()
        if not chave:
            continue
        definicao = tabela.get(chave)
        congeladas = item.get("vagas") if isinstance(item.get("vagas"), list) else None
        if definicao is None:
            # Na venda o produto sumido é erro; no teto NUNCA levanta (roda depois do insert no Google —
            # uma exceção deixaria evento órfão): fantasma com as vagas congeladas que houver.
            if not tolerar_ausente:
                raise ProdutoDesconhecido(chave)
            resolvidos.append({
                "chave": chave,
                "rotulo": str(item.get("rotulo") or chave),
                "descricao": "",
                "ativo": False,
                "preco": float(item.get("preco_aplicado") or 0),
                "por_faixa": {},
                "vagas": [v for v in congeladas or [] if isinstance(v, dict) and v.get("label")],
                "inclui_noturno": True,
                "existe": False,
            })
            continue
        vagas = (
            [v for v in congeladas if isinstance(v, dict) and v.get("label") and v.get("tipo") in _cfg.TIPOS_DE_VAGA]
            if congeladas
            else list(definicao.get("vagas") or [])
        )
        resolvidos.append({
            "chave": chave,
            "rotulo": definicao["rotulo"],
            "descricao": definicao.get("descricao") or "",
            "ativo": bool(definicao.get("ativo", True)),
            "preco": float(definicao["preco"]),
            "por_faixa": definicao.get("por_faixa") or {},
            "vagas": vagas,
            "inclui_noturno": bool(definicao.get("inclui_noturno", True)),
            "existe": True,
        })
    return resolvidos


def cache_da_vaga(vaga: dict, faixa: dict | None, cfg: dict) -> float | None:
    """Cachê 1h da vaga: o fixo do produto, ou o da tabela vigente na data (faixa da 307 inclusa).

    Sempre ``show=False`` — a Visita não tem show, e um avulso com show no mesmo orçamento não pode
    subir o coordenador do produto para a coluna de show. Especial fora da tabela devolve ``None``
    (sem teto): o getter devolveria zeros e o piso da faixa os elevaria a 650 — nunca.
    """
    if vaga.get("cache") is not None:
        return float(vaga["cache"])
    tipo = vaga.get("tipo")
    label = vaga.get("label") or ""
    if tipo == "especial":
        if label not in (cfg.get("especiais") or {}):
            return None
        prices = get_especial_prices(label, False, False, faixa=faixa)
        prices, _ = cache_na_faixa({"type": "especial", "personagem": label}, prices, faixa)
        return float(prices[0])
    if tipo == "ator":
        prices = get_ator_prices("cara_limpa", False, False)
        prices, _ = cache_na_faixa({"type": "ator", "subtipo": "cara_limpa"}, prices, faixa)
        return float(prices[0])
    if tipo == "coordenador":
        return float(get_coordenador_prices(False, 1, faixa=faixa)[0])
    if tipo == "maquiador":
        return float(calcular_maquiador(1, 0))
    return None


def preco_do_produto(produto: dict, faixa: dict | None, cfg: dict) -> dict:
    """Preço aplicado do produto na data: o normal, o da faixa, ou a ESTIMATIVA marcada.

    Sem preço para a faixa da data (produto novo sem `por_faixa.natal`): Σ cachês 1h das vagas pela
    tabela NORMAL × `fator_cache` × `markup` da estimativa — "cachê dobrado e markup um pouco mais
    alto" (dono, 19/10/2026) —, nunca o preço normal em silêncio, nunca bloqueio. Vagas sem cachê
    resolvível ficam fora da soma e avisam.

    Returns:
        ``{preco_aplicado, faixa_chave, estimado, avisos}``.
    """
    avisos: list[str] = []
    if faixa is None:
        return {"preco_aplicado": _q(produto["preco"]), "faixa_chave": None, "estimado": False, "avisos": avisos}
    chave_faixa = faixa.get("chave")
    na_faixa = (produto.get("por_faixa") or {}).get(chave_faixa)
    if isinstance(na_faixa, dict) and na_faixa.get("preco"):
        return {"preco_aplicado": _q(na_faixa["preco"]), "faixa_chave": chave_faixa, "estimado": False, "avisos": avisos}
    estimativa = cfg.get("produtos_estimativa") or _cfg._ESTIMATIVA_PADRAO
    fator = Decimal(str(estimativa.get("fator_cache", 2.0)))
    markup = Decimal(str(estimativa.get("markup", 3.0)))
    soma = Decimal("0")
    for vaga in produto.get("vagas") or []:
        cache = cache_da_vaga(vaga, None, cfg)  # tabela NORMAL de propósito
        if cache is None:
            avisos.append(AVISO_VAGA_SEM_CACHE.format(label=vaga.get("label")))
            continue
        soma += Decimal(str(cache))
    preco = _q(soma * fator * markup)
    avisos.insert(0, AVISO_ESTIMATIVA.format(
        rotulo=produto["rotulo"], faixa=faixa.get("rotulo") or chave_faixa, fator=_num(fator), markup=_num(markup),
    ))
    return {"preco_aplicado": preco, "faixa_chave": chave_faixa, "estimado": True, "avisos": avisos}


def aplicar(selecao: Any, cfg: dict, faixa: dict | None) -> list[dict]:
    """Produtos da venda, resolvidos e precificados (o que vai em `quote.produtos` e no snapshot)."""
    aplicados = []
    for produto in resolver_produtos(selecao, cfg):
        preco = preco_do_produto(produto, faixa, cfg)
        aplicados.append({**produto, **preco})
    return aplicados


# ── composição ──────────────────────────────────────────────────────────────────────────────────
def coordenadores_inclusos(produtos: list[dict]) -> int:
    return sum(1 for p in produtos for v in p.get("vagas") or [] if v.get("tipo") == "coordenador")


def split_coordenadores(coordenador_qty: int, produtos: list[dict]) -> tuple[int, int, int]:
    """``(total, da_formula, inclusos)`` — fonte única da venda e do teto (nada de coordenador em dobro).

    ``coordenador_qty`` já traz o mínimo da conta de hoje (1, ou o `min_coordenadores` de um especial
    avulso): o coordenador do produto conta para esse mínimo — BGE (2) + Visita = o do produto + 1 da
    fórmula. O total nunca fica abaixo do que os produtos trazem.
    """
    inclusos = coordenadores_inclusos(produtos)
    total = max(int(coordenador_qty or 0), inclusos)
    return total, total - inclusos, inclusos


def makes_dos_produtos(produtos: list[dict]) -> int:
    """Makes COMUNS trazidas pelos produtos (`needs_makeup` nas vagas de especial/ator)."""
    return sum(1 for p in produtos for v in p.get("vagas") or [] if v.get("needs_makeup"))


def incremento_make(makes_produtos: int, regulares_avulsos: int, especiais_avulsos: int) -> float:
    """O que a venda cobra de maquiador: só o INCREMENTO dos avulsos sobre as makes do produto.

    O preço do produto já inclui a maquiagem do Noel; um ator maquiado no mesmo orçamento paga o
    degrau seguinte da tabela (`make_2_adicional`…), não o `make_1` de novo.
    """
    if regulares_avulsos <= 0 and especiais_avulsos <= 0:
        return 0.0
    return float(
        calcular_maquiador(makes_produtos + regulares_avulsos, especiais_avulsos)
        - calcular_maquiador(makes_produtos, 0)
    )


def pessoas(produtos: list[dict]) -> int:
    """Quem do produto entra na van (especial/ator e coordenador; o maquiador nunca entrou)."""
    return sum(1 for p in produtos for v in p.get("vagas") or [] if v.get("tipo") in ("especial", "ator", "coordenador"))


def somar_produtos(aplicados: list[dict]) -> float:
    return _q(sum(Decimal(str(p.get("preco_aplicado") or 0)) for p in aplicados))


def labels_de_personagem(produtos: list[dict]) -> list[str]:
    return [v["label"] for p in produtos for v in p.get("vagas") or [] if v.get("tipo") in ("especial", "ator")]


def noturno_do_produto(produtos: list[dict]) -> int:
    """Pessoas do produto que SOMAM o adicional noturno: só com `inclui_noturno` desligado."""
    return sum(
        1
        for p in produtos
        if not p.get("inclui_noturno", True)
        for v in p.get("vagas") or []
        if v.get("tipo") in ("especial", "ator", "coordenador")
    )


# ── régua >4h ───────────────────────────────────────────────────────────────────────────────────
def parte_do_produto_no_total(produtos_total: float, acrescimos: list[dict] | None, nota_fiscal: bool) -> Decimal:
    """O produto como ele está dentro do total de 4h: com os % dos acréscimos e a NF por cima."""
    pt = Decimal(str(produtos_total or 0))
    percentuais = sum(
        (Decimal(str(a.get("value") or 0)) for a in acrescimos or [] if a.get("is_percent")), Decimal("0")
    )
    pt = pt * (Decimal("1") + percentuais / 100)
    if nota_fiscal:
        from app.educamanto.pricing_ops import NF_DIVISOR

        pt = pt / Decimal(str(NF_DIVISOR))
    return pt


def total_na_duracao(total_4h: float, produtos_total: float, horas: int, acrescimos: list[dict] | None, nota_fiscal: bool) -> float:
    """Régua >4h com produto: tudo que não é produto escala ``÷ 4 × h``; o produto fica fixo.

    Fonte única da venda (`total_custom`), do prefill de "Novo evento", de `_total_da_duracao` e do
    BV da duração custom (305). Sem produto reproduz exatamente ``total_4h ÷ 4 × h`` — inclusive os
    acréscimos fixos, que a régua de hoje escala e continuam escalando.
    """
    fixo = parte_do_produto_no_total(produtos_total, acrescimos, nota_fiscal)
    total = Decimal(str(total_4h or 0))
    return _q((total - fixo) / 4 * Decimal(int(horas)) + fixo)


def base_na_duracao(base_4h: Decimal, produtos_total: float, horas: int) -> Decimal:
    """A base pré-acréscimos na duração: o que não é produto escala ``÷ 4 × h``; o produto fica fixo.

    É sobre ela que as linhas em % do evento (BV) são refeitas acima de 4h — um fator único para todas
    as linhas (`total_h ÷ total_4h`) errava a fixa para baixo e a % para cima.
    """
    pt = Decimal(str(produtos_total or 0))
    return (base_4h - pt) / 4 * Decimal(int(horas)) + pt


def cache_fixo_maquiador(produtos: list[dict]) -> float | None:
    """O maior cachê FIXO digitado numa vaga `maquiador` dos produtos (``None`` = todas pela tabela)."""
    fixos = [
        float(v["cache"])
        for p in produtos
        for v in p.get("vagas") or []
        if v.get("tipo") == "maquiador" and v.get("cache") is not None and float(v["cache"]) > 0
    ]
    return max(fixos) if fixos else None


# ── memória e avisos ────────────────────────────────────────────────────────────────────────────
def linhas_da_memoria(aplicados: list[dict], faixa: dict | None) -> list[dict]:
    """Uma linha tipo ``produto`` por exemplar (valores iguais nas 4 colunas)."""
    linhas = []
    for p in aplicados:
        if p.get("estimado"):
            detalhe = DETALHE_ESTIMADO.format(faixa=(faixa or {}).get("rotulo") or p.get("faixa_chave"))
        elif p.get("faixa_chave"):
            detalhe = f"{DETALHE_TABELA} · {(faixa or {}).get('rotulo') or p['faixa_chave']}"
        else:
            detalhe = DETALHE_TABELA
        linhas.append({
            "label": p["rotulo"],
            "detalhe": detalhe,
            "valores": [p["preco_aplicado"]] * 4,
            "tipo": "produto",
        })
    return linhas


def avisos_para(performers: list[dict], aplicados: list[dict]) -> list[str]:
    """Avisos do servidor para a calculadora (a tela nunca decide): Noel avulso sem produto + os da venda."""
    avisos: list[str] = []
    noel_avulso = any(
        p.get("type") == "especial" and (p.get("personagem") or "").strip() == PERSONAGEM_DO_PRODUTO
        for p in performers or []
    )
    if noel_avulso and not aplicados:
        avisos.append(AVISO_NOEL_AVULSO)
    for p in aplicados:
        avisos.extend(p.get("avisos") or [])
    # Dois exemplares do mesmo produto estimado repetiriam o aviso (e a chave React).
    return list(dict.fromkeys(avisos))


def bloco_da_mensagem(aplicados: list[dict]) -> str:
    """Linhas do produto para a mensagem WhatsApp (uma por exemplar)."""
    linhas = []
    for p in aplicados:
        descricao = f" ({p['descricao']})" if p.get("descricao") else ""
        marca = " (estimativa)" if p.get("estimado") else ""
        linhas.append(f"🎅 *{p['rotulo']}*{descricao}: *{_fmt_brl(p['preco_aplicado'])}*{marca}")
    return "\n".join(linhas)


def para_quote(aplicados: list[dict]) -> list[dict]:
    return [
        {
            "chave": p["chave"],
            "rotulo": p["rotulo"],
            "descricao": p.get("descricao") or "",
            "preco_aplicado": p["preco_aplicado"],
            "faixa_chave": p.get("faixa_chave"),
            "estimado": bool(p.get("estimado")),
            "vagas": [v["label"] for v in p.get("vagas") or []],
        }
        for p in aplicados
    ]


def para_snapshot(aplicados: list[dict]) -> list[dict]:
    return [
        {
            "chave": p["chave"],
            "rotulo": p["rotulo"],
            "preco_aplicado": p["preco_aplicado"],
            "faixa_chave": p.get("faixa_chave"),
            "estimado": bool(p.get("estimado")),
            "vagas": vagas_congeladas(p),
        }
        for p in aplicados
    ]


# ── teto das vagas ──────────────────────────────────────────────────────────────────────────────
def _nota(descricao: str, base: float, adicionais: list[tuple[str, float]], total: float) -> str:
    partes = [f"{descricao}: base 1h {_fmt_brl(base)}"]
    partes += [f"+ {nome} {_fmt_brl(valor)}" for nome, valor in adicionais if valor]
    return " ".join(partes) + f" — teto {_fmt_brl(total)}"


def _item(label: str, cache: float | None, *, role_type: str, needs_makeup: bool, descricao: str, adicionais: list[tuple[str, float]], nota_sem_teto: str, produto: dict, perfil: str | None = None) -> dict:
    if cache is None:
        notas = {f"cache_{h}": nota_sem_teto for h in _DURACOES}
        notas["cache_custom"] = nota_sem_teto
        valores: dict[str, Any] = {f"cache_{h}": None for h in _DURACOES}
        valores["cache_custom"] = None
    else:
        total = round(int(cache) + sum(v for _, v in adicionais))
        nota = _nota(descricao, float(cache), adicionais, float(total))
        notas = {f"cache_{h}": nota for h in _DURACOES}
        notas["cache_custom"] = f"{nota} (não escala com a duração)"
        valores = {f"cache_{h}": total for h in _DURACOES}
        valores["cache_custom"] = total
    return {
        "label": label,
        **valores,
        "needs_makeup": needs_makeup,
        "is_singer": False,
        "role_type": role_type,
        "cap_notes": notas,
        "origem": "produto",
        "produto_chave": produto["chave"],
        "perfil": perfil,
    }


def _perfil_da_vaga(produto: dict) -> str:
    """O que o casting lê na vaga do produto (feature 322): o produto vendido. A maquiagem vem da flag
    da vaga na leitura, como nos avulsos (`agenda_read._perfil_da_vaga`)."""
    return str(produto.get("rotulo") or produto["chave"])


def itens_do_teto(produtos: list[dict], faixa: dict | None, cfg: dict, *, transport_add: float, noturno_add: int) -> list[dict]:
    """Vagas `character` dos produtos para `_compute_performer_caches`, flat, na ordem vendida.

    O noturno só entra quando o produto NÃO o embute; o adicional fora de SP entra como nas demais.
    Produto que sumiu da tabela ou especial fora dela → ``cache_Nh = None`` com a nota (sem teto,
    nunca 0).
    """
    itens = []
    for produto in produtos:
        noturno = noturno_add if not produto.get("inclui_noturno", True) else 0
        adicionais = [("noturno", float(noturno)), ("fora-SP", float(transport_add))]
        for vaga in produto.get("vagas") or []:
            if vaga.get("tipo") not in ("especial", "ator"):
                continue
            if not produto.get("existe", True):
                cache, sem = None, NOTA_PRODUTO_SUMIU.format(chave=produto["chave"])
            else:
                cache = cache_da_vaga(vaga, faixa, cfg)
                sem = NOTA_VAGA_SEM_TABELA.format(label=vaga["label"])
            descricao = f"{vaga['label']} ({MARCA_PRODUTO} {produto['rotulo']}" + (f" · {faixa['rotulo']}" if faixa else "") + ")"
            itens.append(_item(
                vaga["label"], cache, role_type="character", needs_makeup=bool(vaga.get("needs_makeup")),
                descricao=descricao, adicionais=adicionais, nota_sem_teto=sem, produto=produto,
                perfil=_perfil_da_vaga(produto),
            ))
    return itens


def coordenadores_do_teto(produtos: list[dict], faixa: dict | None, cfg: dict, *, transport_add: float, noturno_add: int) -> list[dict]:
    """Uma vaga "Coordenador" (extra) por coordenador incluso nos produtos, pela tabela na data."""
    itens = []
    for produto in produtos:
        noturno = noturno_add if not produto.get("inclui_noturno", True) else 0
        adicionais = [("noturno", float(noturno)), ("fora-SP", float(transport_add))]
        for vaga in produto.get("vagas") or []:
            if vaga.get("tipo") != "coordenador":
                continue
            cache = cache_da_vaga(vaga, faixa, cfg) if produto.get("existe", True) else None
            descricao = f"Coordenador ({MARCA_PRODUTO} {produto['rotulo']}" + (f" · {faixa['rotulo']}" if faixa else "") + ")"
            itens.append(_item(
                "Coordenador", cache, role_type="extra", needs_makeup=False, descricao=descricao,
                adicionais=adicionais, nota_sem_teto=NOTA_PRODUTO_SUMIU.format(chave=produto["chave"]), produto=produto,
            ))
    return itens


def tem_maquiador(produtos: list[dict]) -> bool:
    return any(v.get("tipo") == "maquiador" for p in produtos for v in p.get("vagas") or [])
