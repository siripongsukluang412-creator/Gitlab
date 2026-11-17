"""Independent DC bias calculations for a BJT common-emitter amplifier.

Pure engineering logic: no Flask, no I/O. All inputs are SI units
(volts, ohms, dimensionless beta).

Supported single-supply configurations:

* voltage-divider bias (the original Lab 02 model),
* fixed bias,
* emitter bias.

The voltage-divider bias network is solved through its Thevenin
equivalent, so the base current stays explicit instead of being assumed
negligible. That makes the result usable as an independent reference for
the textbook hand calculation in ``docs/validation.md``.

New modes return a plain ``dict`` so the route and the browser table can
share the same key names and the same units. The legacy ``calculate()``
function and its ``BiasResult`` dataclass are intentionally kept
unchanged for the original divider tests.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Mapping

VCE_SAT = 0.2  # V, typical small-signal BJT saturation voltage

MODE_DIVIDER = "divider"
MODE_FIXED = "fixed"
MODE_EMITTER = "emitter"
BIAS_MODES = (MODE_DIVIDER, MODE_FIXED, MODE_EMITTER)

FIELD_LABELS = {
    "vcc": "V_CC",
    "r1": "R_1",
    "r2": "R_2",
    "rc": "R_C",
    "re": "R_E",
    "beta": "β",
    "vbe": "V_BE",
}

FIXED_FIELD_LABELS = {
    "vcc": "V_CC",
    "rb": "R_B",
    "rc": "R_C",
    "beta": "β",
    "vbe": "V_BE",
}

EMITTER_FIELD_LABELS = {
    "vcc": "V_CC",
    "rb": "R_B",
    "rc": "R_C",
    "re": "R_E",
    "beta": "β",
    "vbe": "V_BE",
}

MODE_FIELD_LABELS = {
    MODE_DIVIDER: FIELD_LABELS,
    MODE_FIXED: FIXED_FIELD_LABELS,
    MODE_EMITTER: EMITTER_FIELD_LABELS,
}

REGION_LABELS = {
    "active": "Active region",
    "saturation": "Saturation region",
    "cutoff": "Cutoff region",
}

# Result values are stored in SI units. The display layer formats them.
RESULT_UNITS = {
    "vbb": "V",
    "rth": "Ω",
    "vb": "V",
    "ve": "V",
    "vc": "V",
    "vce": "V",
    "ib": "A",
    "ic": "A",
    "ie": "A",
}


@dataclass(frozen=True)
class BiasInputs:
    vcc: float
    r1: float
    r2: float
    rc: float
    re: float
    beta: float
    vbe: float


@dataclass(frozen=True)
class BiasResult:
    vbb: float
    rth: float
    ib: float
    ic: float
    ie: float
    vce: float
    vb: float
    vc: float
    ve: float
    region: str
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True)
class FixedBiasInputs:
    vcc: float
    rb: float
    rc: float
    beta: float
    vbe: float


@dataclass(frozen=True)
class EmitterBiasInputs:
    vcc: float
    rb: float
    rc: float
    re: float
    beta: float
    vbe: float


BiasInput = BiasInputs | FixedBiasInputs | EmitterBiasInputs
ResultDict = dict[str, object]


def _read_number(
    raw: object,
    field: str,
    errors: dict[str, str],
    labels: Mapping[str, str],
) -> float | None:
    text = "" if raw is None else str(raw).strip()
    label = labels[field]
    if not text:
        errors[field] = f"{label} is required."
        return None
    try:
        value = float(text)
    except (TypeError, ValueError):
        errors[field] = f"{label} must be a number."
        return None
    if not math.isfinite(value):
        errors[field] = f"{label} must be a finite number."
        return None
    return value


def validate_inputs(
    raw: Mapping[str, object], mode: str = MODE_DIVIDER
) -> tuple[BiasInput | None, dict[str, str]]:
    """Validate raw form values in SI units for the selected bias mode.

    Returns ``(inputs, errors)``. ``errors`` maps a field name to an
    English message, so the route can render it next to the input.
    Unknown modes fall back to the original divider validation.
    """
    if mode not in MODE_FIELD_LABELS:
        mode = MODE_DIVIDER

    labels = MODE_FIELD_LABELS[mode]
    errors: dict[str, str] = {}
    values: dict[str, float] = {}

    for field in labels:
        value = _read_number(raw.get(field), field, errors, labels)
        if value is not None:
            values[field] = value

    def check(field: str, ok, message: str) -> None:
        if field not in errors and field in values and not ok(values[field]):
            errors[field] = message

    check("vcc", lambda v: v > 0, "V_CC must be greater than 0 V.")
    check("rc", lambda v: v >= 0, "R_C must not be negative.")
    check("beta", lambda v: 1 <= v <= 10000, "β must be between 1 and 10000.")
    check("vbe", lambda v: 0 <= v <= 2, "V_BE must be between 0 and 2 V.")

    if mode == MODE_DIVIDER:
        check("r1", lambda v: v > 0, "R_1 must be greater than 0 Ω.")
        check("r2", lambda v: v > 0, "R_2 must be greater than 0 Ω.")
        check("re", lambda v: v >= 0, "R_E must not be negative.")
    elif mode == MODE_FIXED:
        check("rb", lambda v: v > 0, "R_B must be greater than 0 Ω.")
    else:
        check("rb", lambda v: v > 0, "R_B must be greater than 0 Ω.")
        check("re", lambda v: v > 0, "R_E must be greater than 0 Ω.")

    if errors:
        return None, errors

    if mode == MODE_FIXED:
        return FixedBiasInputs(**values), {}
    if mode == MODE_EMITTER:
        return EmitterBiasInputs(**values), {}
    return BiasInputs(**values), {}


def calculate(inputs: BiasInputs) -> BiasResult:
    """Solve the voltage-divider bias point for a common-emitter BJT."""
    divider = inputs.r1 + inputs.r2
    vbb = inputs.vcc * inputs.r2 / divider
    rth = inputs.r1 * inputs.r2 / divider

    if vbb <= inputs.vbe:
        return BiasResult(
            vbb=vbb,
            rth=rth,
            ib=0.0,
            ic=0.0,
            ie=0.0,
            vce=inputs.vcc,
            vb=vbb,
            vc=inputs.vcc,
            ve=0.0,
            region="cutoff",
            warnings=(
                "V_BB ≤ V_BE: the base-emitter junction is not forward biased, "
                "so the transistor is in cutoff.",
            ),
        )

    ib = (vbb - inputs.vbe) / (rth + (inputs.beta + 1) * inputs.re)
    ic = inputs.beta * ib
    ie = (inputs.beta + 1) * ib
    vce = inputs.vcc - ic * inputs.rc - ie * inputs.re
    ve = ie * inputs.re
    vc = inputs.vcc - ic * inputs.rc
    vb = ve + inputs.vbe

    if vce < VCE_SAT:
        return BiasResult(
            vbb=vbb,
            rth=rth,
            ib=ib,
            ic=ic,
            ie=ie,
            vce=vce,
            vb=vb,
            vc=vc,
            ve=ve,
            region="saturation",
            warnings=(
                f"V_CE = {vce:.2f} V is below V_CE(sat) = {VCE_SAT:.1f} V. "
                "The transistor is in saturation; the linear model "
                "overstates the real collector-emitter voltage.",
            ),
        )

    return BiasResult(
        vbb=vbb,
        rth=rth,
        ib=ib,
        ic=ic,
        ie=ie,
        vce=vce,
        vb=vb,
        vc=vc,
        ve=ve,
        region="active",
    )


def _result(
    *,
    mode: str,
    ib: float,
    ic: float,
    ie: float,
    vce: float,
    vb: float,
    vc: float,
    ve: float,
    region: str,
    vbb: float | None = None,
    rth: float | None = None,
    warnings: tuple[str, ...] = (),
) -> ResultDict:
    """Build the common result dict used by every bias mode."""
    return {
        "mode": mode,
        "vbb": vbb,
        "rth": rth,
        "vb": vb,
        "ve": ve,
        "vc": vc,
        "vce": vce,
        "ib": ib,
        "ic": ic,
        "ie": ie,
        "region": region,
        "warnings": tuple(warnings),
    }


def _cutoff_warning(supply_label: str) -> str:
    return (
        f"{supply_label} ≤ V_BE: the base-emitter junction is not forward "
        "biased, so the transistor is in cutoff."
    )


def _saturation_warning(vce: float) -> str:
    return (
        f"V_CE = {vce:.2f} V is below V_CE(sat) = {VCE_SAT:.1f} V. "
        "The transistor is in saturation; the linear model overstates the "
        "real collector-emitter voltage."
    )


def calculate_divider(inputs: BiasInputs) -> ResultDict:
    """Return the unchanged voltage-divider solution as a result dict."""
    result = calculate(inputs)
    return _result(
        mode=MODE_DIVIDER,
        vbb=result.vbb,
        rth=result.rth,
        ib=result.ib,
        ic=result.ic,
        ie=result.ie,
        vce=result.vce,
        vb=result.vb,
        vc=result.vc,
        ve=result.ve,
        region=result.region,
        warnings=result.warnings,
    )


def calculate_fixed(inputs: FixedBiasInputs) -> ResultDict:
    """Solve single-supply fixed bias (base resistor, no emitter resistor)."""
    if inputs.vcc <= inputs.vbe:
        return _result(
            mode=MODE_FIXED,
            ib=0.0,
            ic=0.0,
            ie=0.0,
            vce=inputs.vcc,
            vb=inputs.vcc,
            vc=inputs.vcc,
            ve=0.0,
            region="cutoff",
            warnings=(_cutoff_warning("V_CC"),),
        )

    ib = (inputs.vcc - inputs.vbe) / inputs.rb
    ic = inputs.beta * ib
    ie = (inputs.beta + 1) * ib
    vce = inputs.vcc - ic * inputs.rc
    vc = vce
    vb = inputs.vbe
    ve = 0.0

    if vce < VCE_SAT:
        return _result(
            mode=MODE_FIXED,
            ib=ib,
            ic=ic,
            ie=ie,
            vce=vce,
            vb=vb,
            vc=vc,
            ve=ve,
            region="saturation",
            warnings=(_saturation_warning(vce),),
        )

    return _result(
        mode=MODE_FIXED,
        ib=ib,
        ic=ic,
        ie=ie,
        vce=vce,
        vb=vb,
        vc=vc,
        ve=ve,
        region="active",
    )


def calculate_emitter(inputs: EmitterBiasInputs) -> ResultDict:
    """Solve single-supply emitter bias (RB from VCC to base, RE to ground)."""
    if inputs.vcc <= inputs.vbe:
        return _result(
            mode=MODE_EMITTER,
            ib=0.0,
            ic=0.0,
            ie=0.0,
            vce=inputs.vcc,
            vb=inputs.vcc,
            vc=inputs.vcc,
            ve=0.0,
            region="cutoff",
            warnings=(_cutoff_warning("V_CC"),),
        )

    ib = (inputs.vcc - inputs.vbe) / (
        inputs.rb + (inputs.beta + 1) * inputs.re
    )
    ic = inputs.beta * ib
    ie = (inputs.beta + 1) * ib
    vce = inputs.vcc - ic * inputs.rc - ie * inputs.re
    ve = ie * inputs.re
    vc = inputs.vcc - ic * inputs.rc
    vb = ve + inputs.vbe

    if vce < VCE_SAT:
        return _result(
            mode=MODE_EMITTER,
            ib=ib,
            ic=ic,
            ie=ie,
            vce=vce,
            vb=vb,
            vc=vc,
            ve=ve,
            region="saturation",
            warnings=(_saturation_warning(vce),),
        )

    return _result(
        mode=MODE_EMITTER,
        ib=ib,
        ic=ic,
        ie=ie,
        vce=vce,
        vb=vb,
        vc=vc,
        ve=ve,
        region="active",
    )


def solve_bias(mode: str, inputs: BiasInput) -> ResultDict:
    """Choose the calculation function for the requested bias mode."""
    if mode == MODE_FIXED:
        return calculate_fixed(inputs)  # type: ignore[arg-type]
    if mode == MODE_EMITTER:
        return calculate_emitter(inputs)  # type: ignore[arg-type]
    return calculate_divider(inputs)  # type: ignore[arg-type]
