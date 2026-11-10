"""Independent DC bias calculations for a BJT common-emitter amplifier.

Pure engineering logic: no Flask, no I/O. All inputs are SI units
(volts, ohms, dimensionless beta).

The voltage-divider bias network is solved through its Thevenin
equivalent, so the base current stays explicit instead of being assumed
negligible. That makes the result usable as an independent reference for
the textbook hand calculation in ``docs/validation.md``.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Mapping

VCE_SAT = 0.2  # V, typical small-signal BJT saturation voltage

FIELD_LABELS = {
    "vcc": "V_CC",
    "r1": "R_1",
    "r2": "R_2",
    "rc": "R_C",
    "re": "R_E",
    "beta": "β",
    "vbe": "V_BE",
}

REGION_LABELS = {
    "active": "Active region",
    "saturation": "Saturation region",
    "cutoff": "Cutoff region",
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


def _read_number(raw: object, field: str, errors: dict[str, str]) -> float | None:
    text = "" if raw is None else str(raw).strip()
    label = FIELD_LABELS[field]
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


def validate_inputs(raw: Mapping[str, object]) -> tuple[BiasInputs | None, dict[str, str]]:
    """Validate raw form values in SI units.

    Returns ``(inputs, errors)``. ``errors`` maps a field name to an
    English message, so the route can render it next to the input.
    """
    errors: dict[str, str] = {}
    values: dict[str, float] = {}

    for field in FIELD_LABELS:
        value = _read_number(raw.get(field), field, errors)
        if value is not None:
            values[field] = value

    def check(field: str, ok, message: str) -> None:
        if field not in errors and field in values and not ok(values[field]):
            errors[field] = message

    check("vcc", lambda v: v > 0, "V_CC must be greater than 0 V.")
    check("r1", lambda v: v > 0, "R_1 must be greater than 0 Ω.")
    check("r2", lambda v: v > 0, "R_2 must be greater than 0 Ω.")
    check("rc", lambda v: v >= 0, "R_C must not be negative.")
    check("re", lambda v: v >= 0, "R_E must not be negative.")
    check("beta", lambda v: 1 <= v <= 10000, "β must be between 1 and 10000.")
    check("vbe", lambda v: 0 <= v <= 2, "V_BE must be between 0 and 2 V.")

    if errors:
        return None, errors
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
