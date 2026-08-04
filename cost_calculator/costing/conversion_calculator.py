from dataclasses import dataclass
from math import isfinite, pi
from typing import Callable


@dataclass(frozen=True)
class CalculatorField:
    key: str
    label: str
    default: float = 1.0

    def as_dict(self):
        return {"key": self.key, "label": self.label, "default": self.default}


@dataclass(frozen=True)
class CalculatorMode:
    key: str
    label: str
    fields: tuple[CalculatorField, ...]
    area: Callable[[dict[str, float]], float]

    def as_dict(self):
        return {
            "key": self.key,
            "label": self.label,
            "fields": [field.as_dict() for field in self.fields],
        }


MATERIAL_PRESETS = (
    {'key': 'none', 'label': 'No Conversion', 'multiplier': 1},
    {"key": "aluminum", "label": "Aluminium", "multiplier": 0.0983},
    {"key": "brass", "label": "Brass", "multiplier": 0.3067},
    {"key": "steel", "label": "Stainless / steel / alloy", "multiplier": 0.2836},
    {"key": "custom", "label": "Custom", "multiplier": None},
)


def _rectangular_area(values):
    return values["height"] * values["width"]


def _round_area(values):
    return pi * (values["diameter"] ** 2 - values["holeDiameter"] ** 2) / 4

def _quantity_convert(values):
    return values['purchase'] / values['inventory']


# Add or modify calculator modes here. The frontend renders these fields
# automatically and sends their values back to the mode's area function.
MODES = (
    CalculatorMode(
        key="rectangular",
        label="Rectangular",
        fields=(
            CalculatorField("height", "Height"),
            CalculatorField("width", "Width"),
        ),
        area=_rectangular_area,
    ),
    CalculatorMode(
        key="round",
        label="Round",
        fields=(
            CalculatorField("diameter", "Diameter"),
            CalculatorField("holeDiameter", "Hole diameter", 0.0),
        ),
        area=_round_area,
    ),
    CalculatorMode(
        key='quantity',
        label='Quantity',
        fields = (
            CalculatorField('purchase', 'Purchase Quantity'),
            CalculatorField('inventory', 'Inventory Quantity')
            ),
        area=_quantity_convert
        )
)

DEFAULT_MODE = "rectangular"
DEFAULT_PRESET = "none"


def calculator_config():
    return {
        "default_mode": DEFAULT_MODE,
        "default_preset": DEFAULT_PRESET,
        "modes": [mode.as_dict() for mode in MODES],
        "presets": list(MATERIAL_PRESETS),
    }


def calculate_conversion(mode_key, values, multiplier):
    mode = next((item for item in MODES if item.key == mode_key), None)
    if mode is None:
        raise ValueError(f"Unknown conversion calculator mode: {mode_key}")

    normalized = {
        field.key: _finite_number((values or {}).get(field.key), field.default)
        for field in mode.fields
    }
    area = max(0.0, _finite_number(mode.area(normalized), 0.0))
    factor = area * _finite_number(multiplier, 0.0)
    return {"area": area, "factor": factor}


def _finite_number(value, default):
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return float(default)
    return parsed if isfinite(parsed) else float(default)
