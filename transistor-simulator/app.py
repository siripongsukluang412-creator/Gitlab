"""Flask routes for the BJT DC bias web app.

Only HTTP concerns live here: reading the form, converting the selected
display units to SI units, and choosing a template. All engineering math
is in ``dc_bias.py``.
"""

from __future__ import annotations

from flask import Flask, render_template, request

from dc_bias import (
    MODE_DIVIDER,
    VCE_SAT,
    ResultDict,
    solve_bias,
    validate_inputs,
)

app = Flask(__name__)

DIVIDER_FIELD_SPECS = [
    {"name": "vcc", "label": "V_CC", "label_html": "V<sub>CC</sub>",
     "help": "Supply Voltage", "kind": "voltage", "default": "12.0", "unit": "V"},
    {"name": "r1", "label": "R_1", "label_html": "R<sub>1</sub>",
     "help": "Upper Divider", "kind": "resistance", "default": "100", "unit": "kΩ"},
    {"name": "r2", "label": "R_2", "label_html": "R<sub>2</sub>",
     "help": "Lower Divider", "kind": "resistance", "default": "22", "unit": "kΩ"},
    {"name": "rc", "label": "R_C", "label_html": "R<sub>C</sub>",
     "help": "Collector Resistor", "kind": "resistance", "default": "2.2", "unit": "kΩ"},
    {"name": "re", "label": "R_E", "label_html": "R<sub>E</sub>",
     "help": "Emitter Resistor", "kind": "resistance", "default": "1.0", "unit": "kΩ"},
    {"name": "beta", "label": "β", "label_html": "β",
     "help": "Current Gain", "kind": "none", "default": "100", "unit": "–"},
    {"name": "vbe", "label": "V_BE", "label_html": "V<sub>BE</sub>",
     "help": "Base-Emitter Voltage", "kind": "voltage", "default": "0.70", "unit": "V"},
]

FIXED_FIELD_SPECS = [
    {"name": "vcc", "label": "V_CC", "label_html": "V<sub>CC</sub>",
     "help": "Supply Voltage", "kind": "voltage", "default": "12.0", "unit": "V"},
    {"name": "rb", "label": "R_B", "label_html": "R<sub>B</sub>",
     "help": "Base Resistor", "kind": "resistance", "default": "470", "unit": "kΩ"},
    {"name": "rc", "label": "R_C", "label_html": "R<sub>C</sub>",
     "help": "Collector Resistor", "kind": "resistance", "default": "2.2", "unit": "kΩ"},
    {"name": "beta", "label": "β", "label_html": "β",
     "help": "Current Gain", "kind": "none", "default": "100", "unit": "–"},
    {"name": "vbe", "label": "V_BE", "label_html": "V<sub>BE</sub>",
     "help": "Base-Emitter Voltage", "kind": "voltage", "default": "0.70", "unit": "V"},
]

EMITTER_FIELD_SPECS = [
    {"name": "vcc", "label": "V_CC", "label_html": "V<sub>CC</sub>",
     "help": "Supply Voltage", "kind": "voltage", "default": "12.0", "unit": "V"},
    {"name": "rb", "label": "R_B", "label_html": "R<sub>B</sub>",
     "help": "Base Resistor", "kind": "resistance", "default": "470", "unit": "kΩ"},
    {"name": "rc", "label": "R_C", "label_html": "R<sub>C</sub>",
     "help": "Collector Resistor", "kind": "resistance", "default": "2.2", "unit": "kΩ"},
    {"name": "re", "label": "R_E", "label_html": "R<sub>E</sub>",
     "help": "Emitter Resistor", "kind": "resistance", "default": "1.0", "unit": "kΩ"},
    {"name": "beta", "label": "β", "label_html": "β",
     "help": "Current Gain", "kind": "none", "default": "100", "unit": "–"},
    {"name": "vbe", "label": "V_BE", "label_html": "V<sub>BE</sub>",
     "help": "Base-Emitter Voltage", "kind": "voltage", "default": "0.70", "unit": "V"},
]

FIELD_SPECS_BY_MODE = {
    MODE_DIVIDER: DIVIDER_FIELD_SPECS,
    "fixed": FIXED_FIELD_SPECS,
    "emitter": EMITTER_FIELD_SPECS,
}

# Kept as the divider alias because the original tests and page use it.
FIELD_SPECS = DIVIDER_FIELD_SPECS

MODE_SPECS = {
    MODE_DIVIDER: {
        "label": "Divider Bias",
        "subtitle": "Common Emitter (Voltage Divider Bias)",
        "circuit_title": "Circuit: Common-Emitter Amplifier",
        "circuit_aria": "Common-emitter amplifier with voltage-divider bias",
    },
    "fixed": {
        "label": "Fixed Bias",
        "subtitle": "Common Emitter (Fixed Bias)",
        "circuit_title": "Circuit: Fixed Bias",
        "circuit_aria": "Common-emitter amplifier with fixed base bias",
    },
    "emitter": {
        "label": "Emitter Bias",
        "subtitle": "Common Emitter (Emitter Bias)",
        "circuit_title": "Circuit: Emitter Bias",
        "circuit_aria": "Common-emitter amplifier with emitter bias",
    },
}

MODE_TABS = [
    {"id": "divider", "label": MODE_SPECS["divider"]["label"]},
    {"id": "fixed", "label": MODE_SPECS["fixed"]["label"]},
    {"id": "emitter", "label": MODE_SPECS["emitter"]["label"]},
]


UNIT_OPTIONS = {
    "voltage": [("V", 1.0), ("mV", 1e-3)],
    "resistance": [("kΩ", 1e3), ("Ω", 1.0), ("MΩ", 1e6)],
    "none": [("–", 1.0)],
}

UNIT_FACTORS = {
    unit: factor for options in UNIT_OPTIONS.values() for unit, factor in options
}


def _normalise_mode(raw_mode: object) -> str:
    mode = "" if raw_mode is None else str(raw_mode)
    return mode if mode in FIELD_SPECS_BY_MODE else MODE_DIVIDER


def read_form(
    form_data, mode: str = MODE_DIVIDER
) -> tuple[dict[str, str], dict[str, str], dict[str, str]]:
    """Return (display values, selected units, SI base-unit values)."""
    specs = FIELD_SPECS_BY_MODE.get(mode, DIVIDER_FIELD_SPECS)
    values: dict[str, str] = {}
    units: dict[str, str] = {}
    base: dict[str, str] = {}

    for spec in specs:
        name = spec["name"]
        values[name] = form_data.get(name, "")

        unit = form_data.get(f"{name}_unit", spec["unit"])
        if unit not in UNIT_FACTORS:
            unit = spec["unit"]
        units[name] = unit

        text = values[name].strip()
        if not text:
            base[name] = ""
            continue
        try:
            base[name] = str(float(text) * UNIT_FACTORS[unit])
        except ValueError:
            base[name] = text

    return values, units, base


def build_fields(
    values: dict[str, str], units: dict[str, str], mode: str = MODE_DIVIDER
) -> list[dict]:
    specs = FIELD_SPECS_BY_MODE.get(mode, DIVIDER_FIELD_SPECS)
    return [
        {
            **spec,
            "value": values[spec["name"]],
            "selected_unit": units[spec["name"]],
            "unit_options": UNIT_OPTIONS[spec["kind"]],
        }
        for spec in specs
    ]


def build_circuit(
    values: dict[str, str], units: dict[str, str], mode: str = MODE_DIVIDER
) -> dict[str, str]:
    def with_unit(name: str) -> str:
        if name not in values:
            return ""
        unit = units[name]
        value = values[name].strip()
        return value if unit == "–" else f"{value} {unit}"

    circuit = {
        "vcc": with_unit("vcc"),
        "beta": values.get("beta", "").strip() or "100",
    }
    for name in ("r1", "r2", "rb", "rc", "re"):
        circuit[name] = with_unit(name)
    return circuit


def build_status(result: ResultDict) -> dict[str, str]:
    region = str(result["region"])
    vce = float(result["vce"])
    warnings = result["warnings"]
    warning_text = warnings[0] if warnings else ""

    if region == "active":
        return {
            "tone": "ok",
            "title": "Active region approximation OK",
            "detail": (
                f"V_CE = {vce:.2f} V > {VCE_SAT:.1f} V "
                "(transistor in active region)."
            ),
        }
    if region == "saturation":
        return {
            "tone": "warn",
            "title": "Saturation region warning",
            "detail": warning_text,
        }
    return {
        "tone": "off",
        "title": "Cutoff region",
        "detail": warning_text,
    }


@app.template_filter("volt")
def format_voltage(value: float) -> str:
    return f"{value:.2f} V"


@app.template_filter("amp")
def format_current(value: float) -> str:
    magnitude = abs(value)
    if magnitude < 1e-3:
        return f"{value * 1e6:.1f} µA"
    if magnitude < 1:
        return f"{value * 1e3:.2f} mA"
    return f"{value:.2f} A"


def render_page(
    values,
    units,
    mode: str = MODE_DIVIDER,
    result: ResultDict | None = None,
    errors=None,
):
    mode = _normalise_mode(mode)
    return render_template(
        "index.html",
        fields=build_fields(values, units, mode),
        values=values,
        errors=errors or {},
        result=result,
        status=build_status(result) if result else None,
        circuit=build_circuit(values, units, mode),
        mode=mode,
        mode_spec=MODE_SPECS[mode],
        mode_tabs=MODE_TABS,
    )


@app.get("/")
def index():
    mode = _normalise_mode(request.args.get("mode"))
    values = {spec["name"]: spec["default"] for spec in FIELD_SPECS_BY_MODE[mode]}
    units = {spec["name"]: spec["unit"] for spec in FIELD_SPECS_BY_MODE[mode]}
    return render_page(values, units, mode)


@app.post("/")
def calculate_bias():
    mode = _normalise_mode(request.form.get("mode"))
    values, units, base = read_form(request.form, mode)
    inputs, errors = validate_inputs(base, mode)
    if inputs is None:
        return render_page(values, units, mode, errors=errors), 400
    return render_page(values, units, mode, result=solve_bias(mode, inputs))


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
