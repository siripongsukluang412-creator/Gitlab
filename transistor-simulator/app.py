"""Flask routes for the BJT bias and amplifier simulator.

Only HTTP concerns live here: reading the form, converting the selected
display units to SI units, and choosing a template. All engineering math
is in ``dc_bias.py`` (analytical DC) and ``spice_engine.py`` (ngspice).
Charts are rendered server-side by ``svg_plots.py``.
"""

from __future__ import annotations

from flask import Flask, render_template, request

import spice_engine
import svg_plots
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

# The sine-source controls belong to the SPICE AC/transient analyses of the
# single reference voltage-divider circuit. They are shown for divider mode
# only; fixed/emitter modes remain purely analytical (Lab 03 behaviour).
SOURCE_FIELD_SPECS = [
    {"name": "amplitude", "label": "v_in", "label_html": "V<sub>in</sub>",
     "help": "V_in amplitude (peak)", "kind": "voltage", "default": "10",
     "unit": "mV", "source": True},
    {"name": "frequency", "label": "f", "label_html": "f",
     "help": "Frequency (sine source)", "kind": "frequency", "default": "1",
     "unit": "kHz", "source": True},
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

ANALYSIS_ANALYTICAL = "analytical"

ANALYSIS_SPECS = {
    ANALYSIS_ANALYTICAL: {
        "label": "Analytical DC",
        "spice": False,
        "heading": "DC Bias Results",
        "provenance": "Analytical model",
        "description": (
            "Ideal DC model using the active-region equations and the entered "
            "V_BE. No SPICE is involved."
        ),
    },
    "op": {
        "label": "SPICE DC (.op)",
        "spice": True,
        "heading": "SPICE DC Operating Point",
        "provenance": "SPICE simulation",
        "description": "ngspice operating-point solution for the reference circuit.",
    },
    "ac": {
        "label": "SPICE AC (.ac)",
        "spice": True,
        "heading": "SPICE AC Sweep",
        "provenance": "SPICE simulation",
        "description": "ngspice small-signal frequency sweep (1 Hz to 100 MHz).",
    },
    "tran": {
        "label": "SPICE Transient (.tran)",
        "spice": True,
        "heading": "SPICE Transient",
        "provenance": "SPICE simulation",
        "description": "ngspice time-domain run over five sine cycles.",
    },
}

ANALYSIS_TABS = [
    {"id": key, "label": spec["label"], "spice": spec["spice"]}
    for key, spec in ANALYSIS_SPECS.items()
]

SPICE_ONLY_DIVIDER_MESSAGE = (
    "SPICE simulation is only available for the voltage-divider reference "
    "circuit. Switch to Divider Bias, or use Analytical DC."
)


UNIT_OPTIONS = {
    "voltage": [("V", 1.0), ("mV", 1e-3)],
    "resistance": [("kΩ", 1e3), ("Ω", 1.0), ("MΩ", 1e6)],
    "frequency": [("Hz", 1.0), ("kHz", 1e3)],
    "none": [("–", 1.0)],
}

UNIT_FACTORS = {
    unit: factor for options in UNIT_OPTIONS.values() for unit, factor in options
}


def _normalise_mode(raw_mode: object) -> str:
    mode = "" if raw_mode is None else str(raw_mode)
    return mode if mode in FIELD_SPECS_BY_MODE else MODE_DIVIDER


def _normalise_analysis(raw_analysis: object) -> str:
    analysis = "" if raw_analysis is None else str(raw_analysis)
    return analysis if analysis in ANALYSIS_SPECS else ANALYSIS_ANALYTICAL


def _field_specs(mode: str) -> list[dict]:
    specs = FIELD_SPECS_BY_MODE.get(mode, DIVIDER_FIELD_SPECS)
    if mode == MODE_DIVIDER:
        return [*specs, *SOURCE_FIELD_SPECS]
    return list(specs)


def read_form(
    form_data, mode: str = MODE_DIVIDER
) -> tuple[dict[str, str], dict[str, str], dict[str, str]]:
    """Return (display values, selected units, SI base-unit values)."""
    specs = _field_specs(mode)
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
    return [
        {
            **spec,
            "value": values.get(spec["name"], spec["default"]),
            "selected_unit": units.get(spec["name"], spec["unit"]),
            "unit_options": UNIT_OPTIONS[spec["kind"]],
        }
        for spec in _field_specs(mode)
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


def build_spice_status(data: dict) -> dict[str, str]:
    region = str(data.get("region", "unknown"))
    warnings = data.get("warnings") or []
    vce = float(data.get("vce", 0.0))
    if region == "active":
        return {
            "tone": "ok",
            "title": "Active region (SPICE bias point)",
            "detail": f"V_CE = {vce:.2f} V from ngspice.",
        }
    if region == "saturation":
        return {
            "tone": "warn",
            "title": "Saturation region (SPICE bias point)",
            "detail": warnings[0] if warnings else f"V_CE = {vce:.2f} V.",
        }
    return {
        "tone": "off",
        "title": "Cutoff region (SPICE bias point)",
        "detail": warnings[0] if warnings else "I_C is essentially zero.",
    }


def build_spice_view(run: dict) -> dict:
    """Shape one ngspice run for the template, including the SVG chart."""
    analysis = str(run["analysis"])
    data = run["data"]
    view = {
        "analysis": analysis,
        "label": ANALYSIS_SPECS[analysis]["label"],
        "heading": ANALYSIS_SPECS[analysis]["heading"],
        "description": ANALYSIS_SPECS[analysis]["description"],
        "provenance": ANALYSIS_SPECS[analysis]["provenance"],
        "engine": run["engine"],
        "model": run["model"],
        "netlist": run["netlist"],
        "log": run["log"],
        "duration_ms": int(round(float(run["duration_s"]) * 1000)),
        "chart": None,
    }
    if analysis == "op":
        view["op"] = data
        view["status"] = build_spice_status(data)
    elif analysis == "ac":
        view["ac"] = data
        view["chart"] = svg_plots.bode_svg(
            data["frequency_hz"], data["gain_db"], data["phase_deg"]
        )
    else:
        view["tran"] = data
        view["chart"] = svg_plots.transient_svg(
            data["time_s"], data["vin_v"], data["vout_v"]
        )
    return view


def _spice_error_view(exc: Exception) -> dict[str, str]:
    exe = spice_engine.find_ngspice()
    return {
        "message": str(exc),
        "engine_path": exe or "not found",
    }


def _params_from_inputs(
    inputs, source: dict[str, float]
) -> "spice_engine.CircuitParams":
    amp = float(source.get("amplitude") or 0.0)
    freq = float(source.get("frequency") or 0.0)
    return spice_engine.CircuitParams(
        vcc=float(inputs.vcc),
        r1=float(inputs.r1),
        r2=float(inputs.r2),
        rc=float(inputs.rc),
        re=float(inputs.re),
        beta=float(inputs.beta),
        amp=amp if amp > 0 else 10e-3,
        freq=freq if freq > 0 else 1e3,
    )


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


@app.template_filter("mv")
def format_millivolt(value: float) -> str:
    return f"{value * 1e3:.1f} mV"


@app.template_filter("db")
def format_db(value: float) -> str:
    return f"{value:.2f} dB"


@app.template_filter("hz")
def format_hz(value) -> str:
    if value is None:
        return "outside sweep"
    value = float(value)
    magnitude = abs(value)
    if magnitude >= 1e6:
        return f"{value / 1e6:.2f} MHz"
    if magnitude >= 1e3:
        return f"{value / 1e3:.2f} kHz"
    return f"{value:.2f} Hz"


@app.template_filter("gainx")
def format_gain(value: float) -> str:
    return f"{value:.2f}×"


def render_page(
    values,
    units,
    mode: str = MODE_DIVIDER,
    analysis: str = ANALYSIS_ANALYTICAL,
    result: ResultDict | None = None,
    errors=None,
    spice: dict | None = None,
    spice_error: dict | None = None,
    notice: str | None = None,
):
    mode = _normalise_mode(mode)
    analysis = _normalise_analysis(analysis)
    return render_template(
        "index.html",
        fields=build_fields(values, units, mode),
        values=values,
        errors=errors or {},
        result=result,
        status=build_status(result) if result else None,
        spice=spice,
        spice_error=spice_error,
        notice=notice,
        circuit=build_circuit(values, units, mode),
        mode=mode,
        mode_spec=MODE_SPECS[mode],
        mode_tabs=MODE_TABS,
        analysis=analysis,
        analysis_spec=ANALYSIS_SPECS[analysis],
        analysis_tabs=ANALYSIS_TABS,
        spice_allowed=(mode == MODE_DIVIDER),
    )


@app.get("/")
def index():
    mode = _normalise_mode(request.args.get("mode"))
    analysis = _normalise_analysis(request.args.get("analysis"))
    notice = None
    if analysis != ANALYSIS_ANALYTICAL and mode != MODE_DIVIDER:
        analysis = ANALYSIS_ANALYTICAL
        notice = SPICE_ONLY_DIVIDER_MESSAGE

    specs = _field_specs(mode)
    values = {spec["name"]: spec["default"] for spec in specs}
    units = {spec["name"]: spec["unit"] for spec in specs}
    return render_page(values, units, mode, analysis=analysis, notice=notice)


@app.post("/")
def calculate_bias():
    mode = _normalise_mode(request.form.get("mode"))
    analysis = _normalise_analysis(request.form.get("analysis"))
    values, units, base = read_form(request.form, mode)

    if analysis != ANALYSIS_ANALYTICAL and mode != MODE_DIVIDER:
        return (
            render_page(
                values,
                units,
                mode,
                analysis=ANALYSIS_ANALYTICAL,
                errors={"analysis": SPICE_ONLY_DIVIDER_MESSAGE},
            ),
            400,
        )

    inputs, errors = validate_inputs(base, mode)

    if analysis == ANALYSIS_ANALYTICAL:
        if inputs is None:
            return render_page(values, units, mode, errors=errors), 400
        return render_page(
            values,
            units,
            mode,
            result=solve_bias(mode, inputs),
        )

    source_values, source_errors = spice_engine.validate_source(
        analysis, base.get("amplitude"), base.get("frequency")
    )
    errors.update(source_errors)

    # The SPICE reference netlist needs a real emitter resistor; RE = 0 is a
    # different topology (grounded emitter) and is rejected for simulations.
    if inputs is not None and float(inputs.re) <= 0:
        errors["re"] = "R_E must be greater than 0 Ω for the SPICE reference circuit."

    if inputs is None or errors:
        return render_page(
            values, units, mode, analysis=analysis, errors=errors
        ), 400

    params = _params_from_inputs(inputs, source_values)
    try:
        run = spice_engine.run_simulation(params, analysis)
    except spice_engine.SpiceError as exc:
        return render_page(
            values,
            units,
            mode,
            analysis=analysis,
            result=solve_bias(mode, inputs),
            spice_error=_spice_error_view(exc),
        )

    return render_page(
        values,
        units,
        mode,
        analysis=analysis,
        result=solve_bias(mode, inputs),
        spice=build_spice_view(run),
    )


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
