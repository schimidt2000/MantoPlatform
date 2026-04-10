"""Transport cost calculation functions for the quote calculator."""
from . import settings as _cfg


def calcular_van(num_colab: int, km_ida: float, carretinha: bool, show: bool) -> dict:
    """Calculate transport cost for a van.

    Args:
        num_colab: Number of collaborators travelling.
        km_ida: One-way distance in km.
        carretinha: Whether a trailer is attached (affects rate).
        show: Whether the event has a show (affects adicional show).

    Returns:
        Dict with transporte, adicional_fora_sp, adicional_show, total, tarifa.
    """
    t = _cfg.load()["transporte"]
    km_total = km_ida * 2
    tarifa = t["van_com_carretinha"] if carretinha else t["van_sem_carretinha"]
    vt    = km_total * tarifa
    afsp  = (num_colab * km_total) / t["afsp_divisor"]
    ashow = (km_total / t["ashow_divisor"]) if (show and km_total > t["ashow_min_km"]) else 0
    total = vt + afsp + ashow
    return {
        "transporte":        round(vt, 2),
        "adicional_fora_sp": round(afsp, 2),
        "adicional_show":    round(ashow, 2),
        "total":             round(total, 2),
        "tarifa":            tarifa,
    }


def calcular_carro(num_carros: int, num_colab: int, km_ida: float, show: bool) -> dict:
    """Calculate transport cost for private cars.

    Args:
        num_carros: Number of cars.
        num_colab: Number of collaborators travelling.
        km_ida: One-way distance in km.
        show: Whether the event has a show (affects adicional show).

    Returns:
        Dict with transporte, adicional_fora_sp, adicional_show, total.
    """
    t = _cfg.load()["transporte"]
    km_total = km_ida * 2
    vt    = num_carros * t["carro_por_km"] * km_total
    afsp  = (num_colab * km_total) / t["afsp_divisor"]
    ashow = (km_total / t["ashow_divisor"]) if (show and km_total > t["ashow_min_km"]) else 0
    total = vt + afsp + ashow
    return {
        "transporte":        round(vt, 2),
        "adicional_fora_sp": round(afsp, 2),
        "adicional_show":    round(ashow, 2),
        "total":             round(total, 2),
    }
