"""ngspice adapter for the Lab 04 Common-Emitter reference circuit.

Responsibilities:
* build a SPICE netlist from validated SI inputs,
* run ngspice as an external process (no shell),
* parse the ASCII results into plain Python data.

No Flask and no HTML live here. The route layer decides how to present
the numbers; ``svg_plots.py`` renders charts from the parsed arrays.
"""

from __future__ import annotations

import math
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path

from dc_bias import VCE_SAT

MODEL_DESCRIPTION = (
    "Generic small-signal NPN (IS=1e-14 A, BF=β, VAF=100 V, "
    "CJC=8 pF, CJE=25 pF, TF=0.6 ns)"
)

ANALYSES = ("op", "ac", "tran")

# AC sweep chosen to expose both coupling-capacitor roll-off and the
# high-frequency transistor roll-off for the reference component values.
AC_START_HZ = 1.0
AC_STOP_HZ = 100e6
AC_POINTS_PER_DECADE = 30

# Transient: five cycles at the user frequency, 200 samples per cycle.
TRAN_CYCLES = 5.0
TRAN_SAMPLES_PER_CYCLE = 200.0


class SpiceError(RuntimeError):
    """Raised when ngspice is missing, fails, or returns unusable data."""


@dataclass(frozen=True)
class CircuitParams:
    """Reference CE voltage-divider circuit, all values in SI units.

    ``amp`` is the peak value of the sinusoidal source (volts);
    ``freq`` is in hertz. Coupling capacitors and the load resistor use
    the Lab 04 baseline fixture.
    """

    vcc: float
    r1: float
    r2: float
    rc: float
    re: float
    beta: float
    amp: float = 10e-3
    freq: float = 1e3
    cin: float = 10e-6
    cout: float = 10e-6
    rl: float = 10e3


def _num(value: float) -> str:
    """Format a number for a SPICE deck without scientific padding."""
    return f"{float(value):.12g}"


def _exe_candidates() -> list[str]:
    candidates: list[str] = []

    override = os.environ.get("NGSPICE_BIN", "").strip()
    if override:
        candidates.append(override)

    for name in ("ngspice_con", "ngspice"):
        found = shutil.which(name)
        if found:
            candidates.append(found)

    home = os.environ.get("USERPROFILE") or os.environ.get("HOME") or ""
    if home:
        candidates.append(str(Path(home) / "ngspice-env" / "Library" / "bin" / "ngspice_con.exe"))
        candidates.append(str(Path(home) / "ngspice-env" / "Library" / "bin" / "ngspice.exe"))

    candidates.extend(
        [
            r"C:\Spice64\bin\ngspice_con.exe",
            r"C:\Spice64\bin\ngspice.exe",
            "/usr/local/bin/ngspice",
            "/usr/bin/ngspice",
        ]
    )
    return candidates


def find_ngspice() -> str | None:
    """Return the ngspice executable path, or ``None`` when unavailable.

    ``NGSPICE_BIN`` wins, then ``ngspice_con``/``ngspice`` on PATH, then
    a few documented install locations.
    """
    for candidate in _exe_candidates():
        try:
            if candidate and Path(candidate).is_file():
                return str(Path(candidate))
        except OSError:
            continue
    return None


def parse_version(text: str) -> str:
    """Extract ``ngspice-41`` (or similar) from a version banner."""
    match = re.search(r"ngspice-\d+(?:\.\d+)?", text or "")
    return match.group(0) if match else "ngspice"


def _engine_version(exe: str) -> str:
    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0) if sys.platform == "win32" else 0
    for flag in ("-v", "--version"):
        try:
            proc = subprocess.run(
                [exe, flag],
                capture_output=True,
                text=True,
                timeout=10,
                shell=False,
                creationflags=flags,
            )
        except (OSError, subprocess.SubprocessError):
            continue
        version = parse_version((proc.stdout or "") + (proc.stderr or ""))
        if version != "ngspice":
            return version
    return "ngspice"


def validate_source(
    analysis: str, amplitude: object, frequency: object
) -> tuple[dict[str, float], dict[str, str]]:
    """Validate the transient source; unused analyses need no source values.

    Returns ``(values, errors)``. Only ``tran`` requires a positive
    amplitude and a frequency inside the supported sweep.
    """
    if analysis not in ANALYSES:
        return {"amplitude": 0.0, "frequency": 0.0}, {}

    errors: dict[str, str] = {}
    values = {"amplitude": 0.0, "frequency": 0.0}

    if analysis != "tran":
        return values, errors

    def read(raw: object, key: str, label: str) -> float | None:
        text = "" if raw is None else str(raw).strip()
        if not text:
            errors[key] = f"{label} is required."
            return None
        try:
            value = float(text)
        except (TypeError, ValueError):
            errors[key] = f"{label} must be a number."
            return None
        if not math.isfinite(value):
            errors[key] = f"{label} must be a finite number."
            return None
        return value

    amp = read(amplitude, "amplitude", "V_in amplitude")
    freq = read(frequency, "frequency", "Frequency")

    if amp is not None:
        if amp <= 0:
            errors["amplitude"] = "V_in amplitude must be greater than 0 V."
        elif amp > 10:
            errors["amplitude"] = "V_in amplitude must be at most 10 V peak."
        else:
            values["amplitude"] = amp

    if freq is not None:
        if freq < 1 or freq > 1e6:
            errors["frequency"] = "Frequency must be between 1 Hz and 1 MHz."
        else:
            values["frequency"] = freq

    return values, errors


def transient_timing(freq_hz: float) -> tuple[float, float]:
    """Return ``(tstep, tstop)`` for a five-cycle window."""
    period = 1.0 / float(freq_hz)
    tstep = period / TRAN_SAMPLES_PER_CYCLE
    tstop = period * TRAN_CYCLES
    return tstep, tstop


def build_netlist(
    params: CircuitParams,
    analysis: str,
    ic: dict[str, float] | None = None,
) -> str:
    """Create a SPICE deck for the reference CE voltage-divider circuit."""
    if analysis not in ANALYSES:
        raise ValueError(f"unknown analysis {analysis!r}")

    lines = [
        "* BJT common-emitter, voltage-divider bias (ENG29 2121 Lab 04)",
        f".param beta={_num(params.beta)}",
        f"VCC vcc 0 DC {_num(params.vcc)}",
        f"VIN in 0 DC 0 AC 1 SIN(0 {_num(params.amp)} {_num(params.freq)})",
        f"R1 vcc base {_num(params.r1)}",
        f"R2 base 0 {_num(params.r2)}",
        f"RC vcc coll {_num(params.rc)}",
        f"RE emit 0 {_num(params.re)}",
        f"CIN in base {_num(params.cin)}",
        f"COUT coll out {_num(params.cout)}",
        f"RL out 0 {_num(params.rl)}",
        "Q1 coll base emit QNPN",
        (
            ".model QNPN NPN (IS=1e-14 BF={beta} VAF=100 "
            "CJC=8p CJE=25p TF=0.6n)"
        ),
    ]

    if analysis == "op":
        lines.extend(
            [
                ".control",
                "set filetype=ascii",
                "save all @q1[ib] @q1[ic] @q1[ie]",
                "op",
                "write op.raw",
                "quit",
                ".endc",
            ]
        )
    elif analysis == "ac":
        lines.extend(
            [
                ".control",
                "set wr_singlescale",
                "set wr_vecnames",
                "save v(out) v(in)",
                (
                    f"ac dec {AC_POINTS_PER_DECADE} "
                    f"{_num(AC_START_HZ)} {_num(AC_STOP_HZ)}"
                ),
                "let gain = v(out)/v(in)",
                "let gdb = db(gain)",
                "let gph = ph(gain)",
                "wrdata ac.dat gdb gph",
                "quit",
                ".endc",
            ]
        )
    else:
        if not ic or not {"base", "emit", "coll"} <= set(ic):
            raise ValueError("transient analysis needs operating-point ICs")
        tstep, tstop = transient_timing(params.freq)
        lines.extend(
            [
                (
                    f".ic v(base)={_num(ic['base'])} "
                    f"v(emit)={_num(ic['emit'])} "
                    f"v(coll)={_num(ic['coll'])} v(out)=0 v(in)=0"
                ),
                ".control",
                "set wr_singlescale",
                "set wr_vecnames",
                "save v(out) v(in)",
                (
                    f"tran {_num(tstep)} {_num(tstop)} 0 "
                    f"{_num(tstep)} uic"
                ),
                "wrdata tran.dat v(in) v(out)",
                "quit",
                ".endc",
            ]
        )

    lines.append(".end")
    return "\n".join(lines) + "\n"


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        raise SpiceError(f"Could not read {path.name}: {exc}") from exc


def _run_deck(
    exe: str,
    netlist: str,
    workdir: Path,
    stem: str,
    timeout: float,
) -> str:
    deck = workdir / f"{stem}.cir"
    log_path = workdir / f"{stem}.log"
    deck.write_text(netlist, encoding="ascii", errors="replace")

    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0) if sys.platform == "win32" else 0
    try:
        proc = subprocess.run(
            [exe, "-b", "-o", str(log_path), str(deck)],
            cwd=str(workdir),
            capture_output=True,
            text=True,
            timeout=timeout,
            shell=False,
            creationflags=flags,
        )
    except subprocess.TimeoutExpired as exc:
        raise SpiceError(f"ngspice timed out after {timeout:g} s.") from exc
    except OSError as exc:
        raise SpiceError(f"Could not start ngspice: {exc}") from exc

    log = _read_text(log_path) if log_path.is_file() else ""
    log = "\n".join(
        part for part in (log, (proc.stdout or "").strip(), (proc.stderr or "").strip()) if part
    )
    if proc.returncode != 0:
        tail = log[-1200:] if log else "(no log output)"
        raise SpiceError(f"ngspice exited with code {proc.returncode}.\n{tail}")
    return log


def _variables_from_raw(text: str) -> list[str]:
    names: list[str] = []
    inside = False
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("Variables:"):
            inside = True
            continue
        if inside:
            if stripped.startswith("Values:"):
                break
            parts = stripped.split()
            if len(parts) >= 2:
                names.append(parts[1])
    return names


def _values_from_raw(text: str, expected: int) -> list[float]:
    if "Values:" not in text:
        raise SpiceError("op.raw has no Values section")
    tail = text.split("Values:", 1)[1]
    tokens = tail.split()
    if not tokens:
        raise SpiceError("op.raw Values section is empty")
    first = tokens[0]
    try:
        float(first)
    except ValueError:
        pass
    else:
        # The first token is the point index ("0"), not a vector value.
        tokens = tokens[1:]
    values: list[float] = []
    for token in tokens[:expected]:
        try:
            values.append(float(token))
        except ValueError as exc:
            raise SpiceError(f"op.raw contains a non-numeric value: {token!r}") from exc
    if len(values) < expected:
        raise SpiceError("op.raw has fewer values than declared variables")
    return values


def parse_op_raw(text: str) -> dict[str, object]:
    """Parse the ASCII ``op.raw`` written by ngspice into SI values."""
    names = _variables_from_raw(text)
    values = _values_from_raw(text, len(names))
    raw = dict(zip(names, values))

    def need(name: str) -> float:
        if name not in raw:
            raise SpiceError(f"op.raw is missing the variable {name}")
        return raw[name]

    vb = need("v(base)")
    ve = need("v(emit)")
    vc = need("v(coll)")
    vce = vc - ve
    ib = need("i(@q1[ib])")
    ic = need("i(@q1[ic])")
    ie = abs(need("i(@q1[ie])")) if "i(@q1[ie])" in raw else ic + ib

    warnings: list[str] = []
    if ic < 1e-9:
        region = "cutoff"
        warnings.append(
            "I_C is essentially zero: the transistor is in cutoff."
        )
    elif vce < VCE_SAT:
        region = "saturation"
        warnings.append(
            f"V_CE = {vce:.2f} V is below V_CE(sat) = {VCE_SAT:.1f} V. "
            "The SPICE model is in saturation."
        )
    else:
        region = "active"

    return {
        "vb": vb,
        "ve": ve,
        "vc": vc,
        "vce": vce,
        "ib": ib,
        "ic": ic,
        "ie": ie,
        "region": region,
        "warnings": warnings,
    }


def _read_table(text: str, columns: int) -> tuple[list[str], list[list[float]]]:
    lines = [line for line in text.splitlines() if line.strip()]
    if not lines:
        raise SpiceError("ngspice output file is empty")

    header: list[str] = []
    start = 0
    try:
        float(lines[0].split()[0])
    except (ValueError, IndexError):
        header = lines[0].split()
        start = 1

    rows: list[list[float]] = []
    for line in lines[start:]:
        parts = line.split()
        if len(parts) < columns:
            continue
        try:
            rows.append([float(part) for part in parts[:columns]])
        except ValueError:
            continue
    if not rows:
        raise SpiceError("ngspice output contains no numeric rows")
    return header, rows


def _unwrap_degrees(phases: list[float]) -> list[float]:
    if not phases:
        return []
    result = [phases[0]]
    for phase in phases[1:]:
        adjusted = phase
        while adjusted - result[-1] > 180.0:
            adjusted -= 360.0
        while adjusted - result[-1] < -180.0:
            adjusted += 360.0
        result.append(adjusted)
    return result


def parse_ac_dat(text: str) -> dict[str, object]:
    """Parse ``ac.dat`` (frequency, gain dB, phase radians)."""
    _, rows = _read_table(text, 3)
    freq = [row[0] for row in rows]
    gain = [row[1] for row in rows]
    phase_deg = _unwrap_degrees([math.degrees(row[2]) for row in rows])

    peak_index = max(range(len(gain)), key=gain.__getitem__)
    midband_gain = gain[peak_index]
    threshold = midband_gain - 3.0

    f_low: float | None
    if gain[0] >= threshold:
        f_low = None
    else:
        f_low = None
        for index, value in enumerate(gain):
            if value >= threshold:
                f_low = freq[index]
                break

    f_high: float | None
    if gain[-1] >= threshold:
        f_high = None
    else:
        f_high = None
        for index in range(peak_index + 1, len(gain)):
            if gain[index] < threshold:
                f_high = freq[index]
                break

    return {
        "frequency_hz": freq,
        "gain_db": gain,
        "phase_deg": phase_deg,
        "midband_gain_db": midband_gain,
        "midband_frequency_hz": freq[peak_index],
        "f_low_hz": f_low,
        "f_high_hz": f_high,
    }


def parse_tran_dat(text: str) -> dict[str, object]:
    """Parse ``tran.dat`` (time, v(in), v(out))."""
    _, rows = _read_table(text, 3)
    time_s = [row[0] for row in rows]
    vin = [row[1] for row in rows]
    vout = [row[2] for row in rows]

    vin_pp = max(vin) - min(vin)
    vout_pp = max(vout) - min(vout)
    gain = vout_pp / vin_pp if vin_pp > 0 else 0.0

    vin_mean = sum(vin) / len(vin)
    vout_mean = sum(vout) / len(vout)
    covariance = sum(
        (a - vin_mean) * (b - vout_mean) for a, b in zip(vin, vout)
    )

    return {
        "time_s": time_s,
        "vin_v": vin,
        "vout_v": vout,
        "vin_pp": vin_pp,
        "vout_pp": vout_pp,
        "gain_pp": gain,
        "inverted": covariance < 0,
    }


def run_simulation(
    params: CircuitParams, analysis: str, timeout: float = 45.0
) -> dict[str, object]:
    """Run one analysis and return parsed data plus provenance."""
    if analysis not in ANALYSES:
        raise SpiceError(f"unknown analysis {analysis!r}")

    exe = find_ngspice()
    if not exe:
        raise SpiceError(
            "ngspice not found. Install ngspice and put ngspice_con (or "
            "ngspice) on PATH, or set NGSPICE_BIN to the executable."
        )

    workdir = Path(tempfile.mkdtemp(prefix=f"bjt-ce-{analysis}-"))
    engine = _engine_version(exe)
    started = time.perf_counter()

    if analysis == "op":
        log = _run_deck(exe, build_netlist(params, "op"), workdir, "op", timeout)
        data = parse_op_raw(_read_text(workdir / "op.raw"))
        netlist = build_netlist(params, "op")
    elif analysis == "ac":
        netlist = build_netlist(params, "ac")
        log = _run_deck(exe, netlist, workdir, "ac", timeout)
        data = parse_ac_dat(_read_text(workdir / "ac.dat"))
    else:
        op_netlist = build_netlist(params, "op")
        _run_deck(exe, op_netlist, workdir, "op", timeout)
        op_data = parse_op_raw(_read_text(workdir / "op.raw"))
        ic = {
            "base": float(op_data["vb"]),
            "emit": float(op_data["ve"]),
            "coll": float(op_data["vc"]),
        }
        netlist = build_netlist(params, "tran", ic=ic)
        log = _run_deck(exe, netlist, workdir, "tran", timeout)
        data = parse_tran_dat(_read_text(workdir / "tran.dat"))
        data["initial_conditions"] = ic

    return {
        "analysis": analysis,
        "engine": engine,
        "model": MODEL_DESCRIPTION,
        "netlist": netlist,
        "log": log,
        "data": data,
        "duration_s": time.perf_counter() - started,
        "workdir": str(workdir),
    }
