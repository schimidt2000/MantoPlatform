"""Pricing configuration for the quote calculator.

Settings are persisted in SiteSetting.pricing_config (JSON TEXT column).
Falls back to DEFAULTS when no configuration has been saved yet.
"""
import copy
import json

DEFAULTS: dict = {
    "markup": {
        "receptivo": [3.0, 2.7, 2.5],
        "show":      [2.6, 2.4, 2.2],
    },
    "ator": {
        "cara_limpa|false|false": [200, 250, 300],
        "cara_limpa|false|true":  [220, 270, 320],
        "cara_limpa|true|false":  [300, 350, 400],
        "cara_limpa|true|true":   [320, 370, 420],
        "boneco|false|false":     [200, 250, 300],
        "boneco|true|false":      [300, 350, 400],
    },
    "cantor": {
        "false": [350, 400, 450],
        "true":  [370, 420, 470],
    },
    "tecnico_som": [750, 800, 850],
    "coordenador": {
        "false": [250, 300, 350],
        "true":  [300, 350, 400],
    },
    "especiais": {
        "Homem-Aranha": {"false": [250, 300, 350], "true": [400, 450, 500]},
        "Perna de Pau":  [400, 450, 500],
        "Monociclo":     [400, 450, 500],
        "Malabar":       [350, 400, 450],
        "Pirofagista":   [450, 500, 550],
        "Transformer":   [400, 450, 500],
    },
    "brinde_show": 100,
    "maquiador": {
        "make_1":               250,
        "make_2_adicional":     50,
        "make_extra_adicional": 100,
        "make_especial":        300,
    },
    "transporte": {
        "van_com_carretinha": 5.5,
        "van_sem_carretinha": 6.3,
        "carro_por_km":       1.9,
        "afsp_divisor":       3.0,
        "ashow_divisor":      6.0,
        "ashow_min_km":       500,
    },
}

# Especiais que têm variante show/receptivo
ESPECIAIS_COM_SHOW: set = {"Homem-Aranha"}


def load() -> dict:
    """Return current pricing config, falling back to DEFAULTS."""
    try:
        from app.models import SiteSetting
        setting = SiteSetting.query.get(1)
        if setting and setting.pricing_config:
            return json.loads(setting.pricing_config)
    except Exception:
        pass
    return copy.deepcopy(DEFAULTS)


def save(data: dict) -> None:
    """Persist pricing config to the database."""
    from app import db
    from app.models import SiteSetting
    setting = SiteSetting.query.get(1)
    if not setting:
        setting = SiteSetting(id=1)
        db.session.add(setting)
    setting.pricing_config = json.dumps(data, ensure_ascii=False)
    db.session.commit()


def especiais_list() -> list:
    """Return list of special character names."""
    return list(load()["especiais"].keys())
