"""Cache and markup calculation functions for the quote calculator."""
from . import settings as _cfg


def aplicar_markup(totais: list, show: bool) -> list:
    """Apply markup multipliers to a list of [1h, 2h, 4h] cache totals."""
    s = _cfg.load()
    m = s["markup"]["show" if show else "receptivo"]
    return [round(totais[i] * m[i], 2) for i in range(3)]


def get_ator_prices(subtipo: str, show: bool, makeup: bool) -> tuple:
    """Return (1h, 2h, 4h) cache prices for an actor."""
    key = f"{subtipo}|{str(show).lower()}|{str(makeup).lower()}"
    p = _cfg.load()["ator"].get(key, [0, 0, 0])
    return tuple(p)


def get_cantor_prices(show: bool, makeup: bool) -> tuple:
    """Return (1h, 2h, 4h) cache prices for a singer (ator subtype)."""
    c = _cfg.load()["cantor"]
    base       = c["base"]
    show_extra = c["show_extra"]
    make_extra = c["make_extra"]
    return tuple(
        base[i] + (show_extra[i] if show else 0) + (make_extra[i] if makeup else 0)
        for i in range(3)
    )


def get_tecnico_prices() -> tuple:
    """Return (1h, 2h, 4h) cache prices for a sound technician."""
    return tuple(_cfg.load()["tecnico_som"])


def get_coordenador_prices(show: bool, qty: int) -> tuple:
    """Return (1h, 2h, 4h) cache prices for coordinators (multiplied by qty)."""
    p = _cfg.load()["coordenador"][str(show).lower()]
    return (p[0] * qty, p[1] * qty, p[2] * qty)


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
