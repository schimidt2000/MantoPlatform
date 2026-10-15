"""Cache and markup calculation functions for the quote calculator."""
from . import settings as _cfg

# Acréscimo de "Show customizado" (opção de Sósia): +R$50 por artista, não conta
# coordenador/técnico/maquiador (feature 172).
SOSIA_CUSTOM_ADD_PER_ARTIST = 50


def compute_show_pricing(performers: list[dict], show_sosia_tipo: str) -> tuple[bool, float]:
    """Detecta se o evento tem show e o acréscimo de "show customizado" por artista.

    Fonte única reusada tanto pelo cálculo do orçamento (`app/orcamento/routes.py`) quanto pelo
    recálculo do elenco na criação de evento (`_compute_performer_caches`,
    `app/calendar/routes.py`) — antes duplicada nos dois lugares (feature 172).

    Args:
        performers: lista de performers do orçamento (mesmo formato salvo em
            `OrcamentoHistory.form_snapshot["performers"]`).
        show_sosia_tipo: `"predefinido"` ou `"customizado"` (snapshot `show_sosia_tipo`).

    Returns:
        Tupla `(has_show, custom_add_per_artist)` — `custom_add_per_artist` é `0.0` quando
        `show_sosia_tipo` não é `"customizado"` ou não há performers.
    """
    has_show = any(
        p.get("type") == "cantor"
        or (p.get("type") == "ator" and p.get("show"))
        or (
            p.get("type") == "especial"
            and (
                p.get("show")
                or p.get("cantor")
                or p.get("personagem", "") in _cfg.ESPECIAIS_SEMPRE_SHOW
            )
        )
        for p in performers
    )
    custom_add = (
        float(SOSIA_CUSTOM_ADD_PER_ARTIST)
        if show_sosia_tipo == "customizado" and performers
        else 0.0
    )
    return has_show, custom_add


def markup_vigente(show: bool, faixa: dict | None = None, settings: dict | None = None) -> list:
    """O markup que a conta usa: o da faixa de data especial, ou o normal por show/receptivo.

    Fonte única (feature 307) para `aplicar_markup`, a linha da memória e o ``markup_used`` do
    quote — com uma faixa, o markup é o dela para receptivo E show, porque o que é especial é a
    data, não o produto. ``settings`` evita reler a tabela dentro de um cálculo.
    """
    if faixa is not None and faixa.get("markup"):
        return list(faixa["markup"])
    cfg = settings if settings is not None else _cfg.load()
    return list(cfg["markup"]["show" if show else "receptivo"])


def aplicar_markup(
    totais: list, show: bool, faixa: dict | None = None, settings: dict | None = None
) -> list:
    """Apply markup multipliers to a list of [1h, 2h, 3h, 4h] cache totals."""
    m = markup_vigente(show, faixa, settings)
    return [round(totais[i] * m[i], 2) for i in range(4)]


# Feature 307: marcas na memória de cálculo e na nota do teto para o cachê que veio da faixa e
# para o que foi elevado ao piso dela (o React pinta pelo `tipo`; o texto é o que explica o número).
MARCA_CACHE_FAIXA = "cachê da data especial"
MARCA_PISO_FAIXA = "piso da data especial"


def cache_na_faixa(performer: dict, prices: tuple | list, faixa: dict | None) -> tuple[tuple, str]:
    """Cachê do performer dentro da faixa de data especial e a marca que explica (feature 307).

    Fonte única da regra "sobrescrita × piso", usada pela venda (`quote_ops.calculate_quote`) e
    pelo teto das vagas (`calendar.routes._compute_performer_caches`): especial com sobrescrita já
    veio com o cachê da faixa dos getters; qualquer outro performer (ator, boneco, cantor, especial
    sem sobrescrita) sobe ao piso. Sem faixa, devolve o que recebeu e nenhuma marca.
    """
    if faixa is None or performer.get("type") not in ("ator", "cantor", "especial"):
        return tuple(prices), ""
    sobrescrito = (
        performer.get("type") == "especial"
        and performer.get("personagem", "") in (faixa.get("cache") or {})
    )
    if sobrescrito:
        return tuple(prices), MARCA_CACHE_FAIXA
    elevado = aplicar_piso(prices, faixa)
    if tuple(float(v) for v in prices) == elevado:
        return elevado, ""
    return elevado, MARCA_PISO_FAIXA


def aplicar_piso(prices: tuple | list, faixa: dict | None) -> tuple:
    """Eleva cada duração ao piso da faixa de data especial (feature 307).

    Sem piso Noel + boneco (200) sairia mais barato que Noel + ajudante e o teto do boneco ficaria em
    200 contra os 500–750 pagos no Natal de 2025. Sem faixa devolve os preços como vieram.
    """
    piso = (faixa or {}).get("piso")
    if not piso:
        return tuple(prices)
    piso4 = _cfg._ensure4(list(piso))
    return tuple(max(float(prices[i]), float(piso4[i])) for i in range(4))


def get_ator_prices(subtipo: str, show: bool, makeup: bool) -> tuple:
    """Return (1h, 2h, 3h, 4h) cache prices for an actor."""
    key = f"{subtipo}|{str(show).lower()}|{str(makeup).lower()}"
    p = _cfg.load()["ator"].get(key, [0, 0, 0, 0])
    return tuple(p)


def get_cantor_prices(show: bool, makeup: bool) -> tuple:
    """Return (1h, 2h, 3h, 4h) cache prices for a singer (ator subtype)."""
    c = _cfg.load()["cantor"]
    base       = c["base"]
    show_extra = c["show_extra"]
    make_extra = c["make_extra"]
    return tuple(
        base[i] + (show_extra[i] if show else 0) + (make_extra[i] if makeup else 0)
        for i in range(4)
    )


def get_tecnico_prices() -> tuple:
    """Return (1h, 2h, 4h) cache prices for a sound technician."""
    return tuple(_cfg.load()["tecnico_som"])


def get_coordenador_prices(show: bool, qty: int, faixa: dict | None = None) -> tuple:
    """Return (1h, 2h, 3h, 4h) cache prices for coordinators (multiplied by qty).

    Feature 307: na faixa de data especial o coordenador tem uma lista só, com e sem show.
    """
    if faixa is not None and faixa.get("coordenador"):
        p = _cfg._ensure4(list(faixa["coordenador"]))
    else:
        p = _cfg.load()["coordenador"][str(show).lower()]
    return tuple(p[i] * qty for i in range(4))


def get_especial_prices(
    personagem: str, show: bool, cantor: bool = False, faixa: dict | None = None
) -> tuple:
    """Return (1h, 2h, 3h, 4h) cache prices for a special character.

    SEMPRE 4 valores (feature 254): os defaults antigos tinham 3 itens e um personagem removido
    da tabela (recalcular orçamento antigo) derrubava o cálculo inteiro com IndexError no
    `prices[3]`. `_ensure4` também normaliza tabela legada salva com 3 valores.

    Feature 307: a sobrescrita da faixa de data especial (`faixa["cache"][personagem]`) vale para
    qualquer variante do especial — simples, show ou cantor.
    """
    zeros = [0, 0, 0, 0]
    sobrescrita = (faixa or {}).get("cache", {}).get(personagem)
    if isinstance(sobrescrita, list) and sobrescrita:
        return tuple(_cfg._ensure4(list(sobrescrita)))
    p = _cfg.load()["especiais"].get(personagem, zeros)
    if isinstance(p, dict):
        if personagem in _cfg.ESPECIAIS_COM_CANTOR and cantor:
            return tuple(_cfg._ensure4(p.get("cantor", zeros)))
        if show:
            return tuple(_cfg._ensure4(p.get("show", p.get("true", zeros))))
        return tuple(_cfg._ensure4(p.get("none", p.get("false", zeros))))
    return tuple(_cfg._ensure4(p))


def calcular_maquiador(num_regular: int, num_especial: int) -> float:
    """Calculate total makeup artist cost based on number of regular/special makeups."""
    m = _cfg.load()["maquiador"]
    total = float(num_especial * m["make_especial"])
    if num_regular >= 1:
        total += m["make_1"]
    if num_regular >= 2:
        total += m["make_2_adicional"]
    if num_regular >= 3:
        total += (num_regular - 2) * m["make_extra_adicional"]
    return total
