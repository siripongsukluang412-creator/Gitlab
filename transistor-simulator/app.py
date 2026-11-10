"""Flask routes for the BJT DC bias web app.

Only HTTP concerns live here: reading the form, converting the selected
display units to SI units, and choosing a template. All engineering math
is in ``dc_bias.py``.
"""

from __future__ import annotations

from flask import Flask, render_template, request

from dc_bias import VCE_SAT, calculate, validate_inputs

app = Flask(__name__)

FIELD_SPECS = [
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

UNIT_OPTIONS = {
    "voltage": [("V", 1.0), ("mV", 1e-3)],
    "resistance": [("kΩ", 1e3), ("Ω", 1.0), ("MΩ", 1e6)],
    "none": [("–", 1.0)],
}

UNIT_FACTORS = {
    unit: factor for options in UNIT_OPTIONS.values() for unit, factor in options
}


def read_form(form_data) -> tuple[dict[str, str], dict[str, str], dict[str, str]]:
    """Return (display values, selected units, SI base-unit values)."""
    values: dict[str, str] = {}
    units: dict[str, str] = {}
    base: dict[str, str] = {}

    for spec in FIELD_SPECS:
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


def build_fields(values: dict[str, str], units: dict[str, str]) -> list[dict]:
    return [
        {
            **spec,
            "value": values[spec["name"]],
            "selected_unit": units[spec["name"]],
            "unit_options": UNIT_OPTIONS[spec["kind"]],
        }
        for spec in FIELD_SPECS
    ]


def build_circuit(values: dict[str, str], units: dict[str, str]) -> dict[str, str]:
    def with_unit(name: str) -> str:
        unit = units[name]
        value = values[name].strip()
        return value if unit == "–" else f"{value} {unit}"

    return {
        "vcc": with_unit("vcc"),
        "r1": with_unit("r1"),
        "r2": with_unit("r2"),
        "rc": with_unit("rc"),
        "re": with_unit("re"),
        "beta": values["beta"].strip() or "100",
    }


def build_status(result) -> dict[str, str]:
    if result.region == "active":
        return {
            "tone": "ok",
            "title": "Active region approximation OK",
            "detail": (
                f"V_CE = {result.vce:.2f} V > {VCE_SAT:.1f} V "
                "(transistor in active region)."
            ),
        }
    if result.region == "saturation":
        return {
            "tone": "warn",
            "title": "Saturation region warning",
            "detail": result.warnings[0],
        }
    return {
        "tone": "off",
        "title": "Cutoff region",
        "detail": result.warnings[0],
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


def render_page(values, units, result=None, errors=None):
    return render_template(
        "index.html",
        fields=build_fields(values, units),
        values=values,
        errors=errors or {},
        result=result,
        status=build_status(result) if result else None,
        circuit=build_circuit(values, units),
    )


@app.get("/")
def index():
    values = {spec["name"]: spec["default"] for spec in FIELD_SPECS}
    units = {spec["name"]: spec["unit"] for spec in FIELD_SPECS}
    return render_page(values, units)


@app.post("/")
def calculate_bias():
    values, units, base = read_form(request.form)
    inputs, errors = validate_inputs(base)
    if inputs is None:
        return render_page(values, units, errors=errors), 400
    return render_page(values, units, result=calculate(inputs))


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
