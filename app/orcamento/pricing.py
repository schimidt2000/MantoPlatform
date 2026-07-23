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


def aplicar_markup(totais: list, show: bool) -> list:
    """Apply markup multipliers to a list of [1h, 2h, 3h, 4h] cache totals."""
    s = _cfg.load()
    m = s["markup"]["show" if show else "receptivo"]
    return [round(totais[i] * m[i], 2) for i in range(4)]


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


def get_coordenador_prices(show: bool, qty: int) -> tuple:
    """Return (1h, 2h, 3h, 4h) cache prices for coordinators (multiplied by qty)."""
    p = _cfg.load()["coordenador"][str(show).lower()]
    return tuple(p[i] * qty for i in range(4))


def get_especial_prices(personagem: str, show: bool, cantor: bool = False) -> tuple:
    """Return (1h, 2h, 4h) cache prices for a special character."""
    p = _cfg.load()["especiais"].get(personagem, [0, 0, 0])
    if isinstance(p, dict):
        if personagem in _cfg.ESPECIAIS_COM_CANTOR and cantor:
            return tuple(p.get("cantor", [0, 0, 0]))
        if show:
            return tuple(p.get("show", p.get("true", [0, 0, 0])))
        return tuple(p.get("none", p.get("false", [0, 0, 0])))
    return tuple(p)


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
