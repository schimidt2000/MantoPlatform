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
        "Homem-Aranha":           {"false": [250, 300, 350], "true": [400, 450, 500]},
        "Perna de Pau":           [400, 450, 500],
        "Monociclo":              [400, 450, 500],
        "Malabar":                [350, 400, 450],
        "Pirofagista":            [450, 500, 550],
        "Boneco Grande Especial": {"false": [400, 450, 500], "true": [400, 450, 500]},
        "Sósia":                  [350, 400, 450],
        "Sósia com Show":         {"false": [450, 500, 550], "true": [450, 500, 550]},
        "Sósia Cantor":           {"false": [500, 550, 600], "true": [500, 550, 600]},
        "Bailarino":              [400, 450, 500],
    },
    "especiais_regras": {
        "Boneco Grande Especial": {
            "transporte_especial": 1000,
            "min_coordenadores":   2,
        },
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

# Especiais que têm checkbox de show (técnico de som é adicionado se marcado)
ESPECIAIS_COM_SHOW: set = {"Homem-Aranha", "Boneco Grande Especial", "Sósia com Show", "Sósia Cantor"}


def _migrate(data: dict) -> dict:
    """Aplica migrações na config salva no banco sem alterar o banco."""
    especiais = data.setdefault("especiais", {})

    # Renomear Transformer → Boneco Grande Especial
    if "Transformer" in especiais and "Boneco Grande Especial" not in especiais:
        old = especiais.pop("Transformer")
        especiais["Boneco Grande Especial"] = (
            old if isinstance(old, dict) else {"false": old, "true": old}
        )

    # Adicionar especiais novos que ainda não existem na config salva
    for nome, val in DEFAULTS["especiais"].items():
        if nome not in especiais:
            especiais[nome] = copy.deepcopy(val)

    # Adicionar especiais_regras se ausente
    if "especiais_regras" not in data:
        data["especiais_regras"] = copy.deepcopy(DEFAULTS["especiais_regras"])

    return data


def load() -> dict:
    """Return current pricing config, falling back to DEFAULTS."""
    try:
        from app.models import SiteSetting
        setting = SiteSetting.query.get(1)
        if setting and setting.pricing_config:
            return _migrate(json.loads(setting.pricing_config))
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
