from __future__ import annotations
def _title_line(width: int, title: str) -> str:
    return f'<text x="{width // 2}" y="28" text-anchor="middle" class="chart-title">{title}</text>'

"""Dependency-free SVG charts for the Lab 04 SPICE results.

The project deliberately avoids a JavaScript charting dependency: the
server renders static SVG from the parsed ngspice arrays, so the page
works without any client-side plotting library.

Two public helpers exist:

* :func:`bode_svg` draws gain and phase against a logarithmic frequency axis.
* :func:`transient_svg` draws input and output waveforms on a linear time axis.

All values are SI on input; labels convert to the display units named in
the axis titles (Hz, dB, degrees, ms, mV).

Every chart embeds a small self-contained script that provides:

* hover / touch scrubbing with a live value readout tooltip,
* a Play / Pause toggle that animates a marker along the waveforms,
* a scrub timeline for seeking through the data.

No external charting library is required.
"""


import html
import json
import math
from collections.abc import Sequence

WIDTH = 780
HEIGHT = 400
MARGIN_LEFT = 82
MARGIN_RIGHT = 24

# Keep the embedded SVG small even when ngspice returns thousands of rows.
MAX_POINTS = 600

# Trace colors: yellow (#facc15) and blue (#38bdf8).
_GAIN_COLOR = "#facc15"
_PHASE_COLOR = "#38bdf8"
_VIN_COLOR = "#facc15"
_VOUT_COLOR = "#38bdf8"
_AXIS_COLOR = "#475569"
_GRID_COLOR = "#e2e8f0"
_TEXT_COLOR = "#1e293b"
_TOOLTIP_BG = "#0f172a"
_MARKER_SIZE = 5


def _finite(values: Sequence[float]) -> list[float]:
    return [float(value) for value in values if math.isfinite(float(value))]


def _trim(number: float) -> str:
    text = f"{number:.3g}"
    return text


def _hertz(value: float) -> str:
    magnitude = abs(value)
    if magnitude >= 1e9:
        return f"{_trim(value / 1e9)}G"
    if magnitude >= 1e6:
        return f"{_trim(value / 1e6)}M"
    if magnitude >= 1e3:
        return f"{_trim(value / 1e3)}k"
    return _trim(value)


def _plain(value: float, digits: int = 0) -> str:
    return f"{value:.{digits}f}"


def _decimate(count: int, limit: int = MAX_POINTS) -> list[int]:
    """Return evenly spaced indices covering the full array."""
    if count <= limit:
        return list(range(count))
    step = (count - 1) / (limit - 1)
    indices = {int(round(step * i)) for i in range(limit)}
    indices.add(0)
    indices.add(count - 1)
    return sorted(indices)


def _linear_scale(
    values: Sequence[float], lo: float, hi: float
) -> tuple[float, float, float, float]:
    if not values:
        return 0.0, 1.0, 0.0, 1.0
    vmin = min(values)
    vmax = max(values)
    if math.isclose(vmin, vmax):
        pad = abs(vmin) * 0.1 or 1.0
        vmin -= pad
        vmax += pad
    span = vmax - vmin
    pad = span * 0.08
    return vmin - pad, vmax + pad, vmin, vmax


def _map_log(value: float, fmin: float, fmax: float, x0: float, x1: float) -> float:
    low = math.log10(max(fmin, 1e-12))
    high = math.log10(max(fmax, 1e-11))
    if math.isclose(low, high):
        return (x0 + x1) / 2
    fraction = (math.log10(max(value, 1e-12)) - low) / (high - low)
    return x0 + fraction * (x1 - x0)


def _map_linear(
    value: float, vmin: float, vmax: float, y0: float, y1: float
) -> float:
    if math.isclose(vmin, vmax):
        return (y0 + y1) / 2
    fraction = (value - vmin) / (vmax - vmin)
    return y1 - fraction * (y1 - y0)


def _text(
    x: float,
    y: float,
    label: str,
    *,
    size: float = 12,
    anchor: str = "middle",
    color: str = _TEXT_COLOR,
    weight: str = "400",
) -> str:
    return (
        f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" '
        f'text-anchor="{anchor}" fill="{color}" font-weight="{weight}">'
        f"{html.escape(label)}</text>"
    )


def _line(
    x1: float,
    y1: float,
    x2: float,
    y2: float,
    color: str,
    width: float = 1.0,
    dash: str = "",
) -> str:
    extra = f' stroke-dasharray="{dash}"' if dash else ""
    return (
        f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
        f'stroke="{color}" stroke-width="{width}"{extra} />'
    )


def _polyline(points: list[tuple[float, float]], color: str) -> str:
    if len(points) < 2:
        return ""
    blob = " ".join(f"{x:.1f},{y:.1f}" for x, y in points)
    return (
        f'<polyline points="{blob}" fill="none" stroke="{color}" '
        'stroke-width="2" stroke-linejoin="round" stroke-linecap="round" />'
    )


def _circle(cx: float, cy: float, r: float, color: str) -> str:
    return (
        f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r:.1f}" fill="{color}" />'
    )


def _data_script(id_name: str, data: dict) -> str:
    """Embed chart data as JSON for the interactive script."""
    payload = json.dumps(data, separators=(",", ":"))
    return f'<script id="{id_name}" type="application/json">{payload}</script>'


def _interactive_script() -> str:
    """Return the self-contained JS that drives hover, scrub, and animation."""
    return (
        '<script type="text/javascript">'
        "(function(){"
        "var dataEl=document.getElementById('chart-data');"
        "if(!dataEl){return;}"
        "var data=JSON.parse(dataEl.textContent || dataEl.textContent);"
        "var svg=dataEl.ownerSVGElement || document.querySelector('svg');"
        "if(!svg){return;}"
        "var root=svg.ownerSVGElement || svg;"
        "var width=root.clientWidth || 780;"
        "var height=root.clientHeight || 400;"
        "var marginLeft=82;"
        "var marginRight=24;"
        "var x0=marginLeft;"
        "var x1=width-marginRight;"
        "var plotTop=52;"
        "var plotBottom=342;"
        "var tooltip=root.querySelector('.chart-tooltip');"
        "var tipBox=tooltip ? tooltip.querySelector('rect') : null;"
        "var tipText=tooltip ? tooltip.querySelector('text') : null;"
        "var guide=root.querySelector('.chart-guide');"
        "var markers=[];"
        "root.querySelectorAll('.chart-marker').forEach(function(m){markers.push(m);});"
        "var scrubBar=root.querySelector('.chart-scrub-bar');"
        "var scrubKnob=root.querySelector('.chart-scrub-knob');"
        "var playBtn=root.querySelector('.chart-play');"
        "var playing=false;"
        "var animId=null;"
        "var index=0;"
        "var n=data.freq ? data.freq.length : (data.time ? data.time.length : 0);"
        "function mapLog(v,fmin,fmax,xa,xb){"
        "  var lo=Math.log10(Math.max(fmin,1e-12));"
        "  var hi=Math.log10(Math.max(fmax,1e-11));"
        "  if(Math.abs(hi-lo)<1e-9){return (xa+xb)/2;}"
        "  var frac=(Math.log10(Math.max(v,1e-12))-lo)/(hi-lo);"
        "  return xa+frac*(xb-xa);"
        "}"
        "function mapLin(v,vmin,vmax,ya,yb){"
        "  if(Math.abs(vmax-vmin)<1e-9){return (ya+yb)/2;}"
        "  var frac=(v-vmin)/(vmax-vmin);"
        "  return yb-frac*(yb-ya);"
        "}"
        "function nearestIndex(xpx){"
        "  var best=0;var bestDist=1e18;"
        "  for(var i=0;i<n;i++){"
        "    var px=data.freq ? mapLog(data.freq[i],data.fmin,data.fmax,x0,x1) :"
        "      x0+(data.time[i]-data.tmin)/(data.tmax-data.tmin)*(x1-x0);"
        "    var d=Math.abs(px-xpx);"
        "    if(d<bestDist){bestDist=d;best=i;}"
        "  }"
        "  return best;"
        "}"
        "function showTip(i,xpx,ypx,label){"
        "  if(!tooltip||!tipText){return;}"
        "  tipText.textContent=label;"
        "  tooltip.setAttribute('transform','translate('+(xpx+12)+','+(ypx-28)+')');"
        "  tooltip.setAttribute('visibility','visible');"
        "}"
        "function hideTip(){"
        "  if(tooltip){tooltip.setAttribute('visibility','hidden');}"
        "  if(guide){guide.setAttribute('visibility','hidden');}"
        "  markers.forEach(function(m){m.setAttribute('visibility','hidden');});"
        "}"
        "function setMarker(i){"
        "  markers.forEach(function(m){m.setAttribute('visibility','hidden');});"
        "  var px=data.freq ? mapLog(data.freq[i],data.fmin,data.fmax,x0,x1) :"
        "    x0+(data.time[i]-data.tmin)/(data.tmax-data.tmin)*(x1-x0);"
        "  markers.forEach(function(m,k){"
        "    var py=data.freq ? (k===0 ? mapLin(data.gain[i],data.gmin,data.gmax,plotTop,plotBottom-154) : mapLin(data.phase[i],data.pmin,data.pmax,plotTop+146,plotBottom-154)) :"
        "      (k===0 ? mapLin(data.vin[i],data.vmin,data.vmax,plotTop,plotBottom) : mapLin(data.vout[i],data.vmin,data.vmax,plotTop,plotBottom)));"
        "    m.setAttribute('cx',px);"
        "    m.setAttribute('cy',py);"
        "    m.setAttribute('visibility','visible');"
        "  });"
        "  if(guide){"
        "    guide.setAttribute('x1',px);guide.setAttribute('x2',px);"
        "    guide.setAttribute('y1',plotTop);guide.setAttribute('y2',plotBottom);"
        "    guide.setAttribute('visibility','visible');"
        "  }"
        "  if(scrubKnob){"
        "    var frac=i/(n-1);"
        "    var kx=x0+frac*(x1-x0);"
        "    scrubKnob.setAttribute('cx',kx);"
        "  }"
        "}"
        "function onPointer(evt){"
        "  var pt=svg.createSVGPoint();"
        "  var cx=evt.clientX,cy=evt.clientY;"
        "  var box=svg.getBoundingClientRect();"
        "  var sx=(cx-box.left)/(box.right-box.left)*width;"
        "  var sy=(cy-box.top)/(box.bottom-box.top)*height;"
        "  pt.x=sx;pt.y=sy;"
        "  var p=pt.matrixTransform(svg.getScreenCTM().inverse());"
        "  var i=nearestIndex(p.x);"
        "  if(data.freq){"
        "    var gx=mapLog(data.freq[i],data.fmin,data.fmax,x0,x1);"
        "    var gy=mapLin(data.gain[i],data.gmin,data.gmax,plotTop,plotBottom-154);"
        "    var py=mapLin(data.phase[i],data.pmin,data.pmax,plotTop+146,plotBottom-154);"
        "    setMarker(i);"
        "    showTip(i,gx,gy,'f='+data.freq[i].toFixed(2)+'Hz  gain='+data.gain[i].toFixed(2)+'dB  phase='+data.phase[i].toFixed(1)+'°');"
        "  }else{"
        "    var tx=x0+(data.time[i]-data.tmin)/(data.tmax-data.tmin)*(x1-x0);"
        "    var vy=mapLin(data.vin[i],data.vmin,data.vmax,plotTop,plotBottom);"
        "    setMarker(i);"
        "    showTip(i,tx,vy,'t='+data.time[i].toFixed(4)+'s  Vin='+data.vin[i].toFixed(4)+'V  Vout='+data.vout[i].toFixed(4)+'V');"
        "  }"
        "}"
        "if(root){"
        "  root.addEventListener('mousemove',function(e){onPointer(e);});"
        "  root.addEventListener('touchmove',function(e){e.preventDefault();onPointer(e.touches[0]);},{passive:false});"
        "  root.addEventListener('mouseleave',hideTip);"
        "  root.addEventListener('touchend',hideTip);"
        "}"
        "if(playBtn){"
        "  playBtn.addEventListener('click',function(){"
        "    playing=!playing;"
        "    playBtn.textContent=playing?'Pause':'Play';"
        "    if(playing){step();}else{if(animId){cancelAnimationFrame(animId);animId=null;}}"
        "  });"
        "}"
        "function step(){"
        "  if(!playing){return;}"
        "  index=(index+1)%n;"
        "  setMarker(index);"
        "  animId=requestAnimationFrame(step);"
        "}"
        "if(scrubBar&&scrubKnob){"
        "  scrubBar.addEventListener('click',function(e){"
        "    var box=svg.getBoundingClientRect();"
        "    var sx=(e.clientX-box.left)/(box.right-box.left)*width;"
        "    var i=Math.round((sx-x0)/(x1-x0)*(n-1));"
        "    if(i<0)i=0;if(i>=n)i=n-1;"
        "    setMarker(i);"
        "  });"
        "}"
        "})();"
        "</script>"
    )


def _tooltip_group() -> str:
    """Return the hidden tooltip group placed inside the chart SVG."""
    return (
        '<g class="chart-tooltip" visibility="hidden">'
        '<rect x="0" y="0" width="1" height="1" rx="6" ry="6" '
        f'fill="{_TOOLTIP_BG}" stroke="#38bdf8" stroke-width="1" />'
        '<text x="8" y="14" font-size="11" fill="#e2e8f0" font-family="'
        '"Segoe UI", system-ui, sans-serif"></text>'
        "</g>"
    )


def _scrub_controls(
    x0: float, x1: float, bottom: float, color: str
) -> str:
    """Return the scrub timeline and Play/Pause toggle at the chart base."""
    knob_y = bottom + 30
    return (
        f'<line class="chart-scrub-bar" x1="{x0:.1f}" y1="{knob_y:.1f}" '
        f'x2="{x1:.1f}" y2="{knob_y:.1f}" stroke="#94a3b8" stroke-width="2" />'
        f'<circle class="chart-scrub-knob" cx="{x0:.1f}" cy="{knob_y:.1f}" r="5" '
        f'fill="{color}" stroke="#0f172a" stroke-width="1.5" />'
        f'<rect class="chart-play" x="{x0 - 4:.1f}" y="{knob_y + 12:.1f}" '
        f'width="34" height="18" rx="6" fill="#0f172a" stroke="#38bdf8" '
        'stroke-width="1" cursor="pointer" />'
        f'<text x="{x0 + 13:.1f}" y="{knob_y + 27:.1f}" font-size="11" '
        f'fill="#e2e8f0" text-anchor="middle" cursor="pointer">Play</text>'
    )


def _markers(count: int, color_a: str, color_b: str) -> str:
    """Return hidden marker circles for live value readout."""
    parts: list[str] = []
    for color in (color_a, color_b):
        parts.append(
            f'<circle class="chart-marker" cx="0" cy="0" r="{_MARKER_SIZE}" '
            f'fill="{color}" visibility="hidden" />'
        )
    return "".join(parts)


def _guide_line(x0: float, y_top: float, y_bottom: float) -> str:
    """Return the vertical hover guide line."""
    return (
        f'<line class="chart-guide" x1="0" y1="{y_top:.1f}" x2="0" y2="{y_bottom:.1f}" '
        f'stroke="#38bdf8" stroke-width="1" stroke-dasharray="6 4" visibility="hidden" />'
    )


def bode_svg(
    frequency_hz: Sequence[float],
    gain_db: Sequence[float],
    phase_deg: Sequence[float],
) -> str:
    """Render a two-panel Bode plot: gain (dB) above, phase (degrees) below."""
    freq_raw = _finite(frequency_hz)
    gain_raw = _finite(gain_db)
    phase_raw = _finite(phase_deg)
    count = min(len(freq_raw), len(gain_raw), len(phase_raw))
    if count < 2:
        return (
            f'<svg class="chart" role="img" viewBox="0 0 {WIDTH} {HEIGHT}" '
            'xmlns="http://www.w3.org/2000/svg">'
            + _title_line(WIDTH, "Not enough AC data to plot")
            + "</svg>"
        )

    indices = _decimate(count)
    freq = [freq_raw[i] for i in indices]
    gain = [gain_raw[i] for i in indices]
    phase = [phase_raw[i] for i in indices]

    x0, x1 = float(MARGIN_LEFT), float(WIDTH - MARGIN_RIGHT)
    gain_top, gain_bottom = 52.0, 206.0
    phase_top, phase_bottom = 252.0, 342.0

    gmin, gmax, _, _ = _linear_scale(gain, 0, 0)
    pmin, pmax, _, _ = _linear_scale(phase, 0, 0)

    parts: list[str] = [
        f'<svg class="chart" role="img" viewBox="0 0 {WIDTH} {HEIGHT}" '
        'xmlns="http://www.w3.org/2000/svg">',
        _title_line(WIDTH, "Bode plot (SPICE AC sweep)"),
        _text(16, (gain_top + gain_bottom) / 2, "Gain (dB)", size=12, anchor="start", weight="600"),
        _text(16, (phase_top + phase_bottom) / 2, "Phase (°)", size=12, anchor="start", weight="600"),
    ]

    parts.extend(
        _y_ticks(gmin, gmax, gain_top, gain_bottom, x0, x1, _plain, 0)
    )
    parts.extend(
        _y_ticks(pmin, pmax, phase_top, phase_bottom, x0, x1, _plain, 0)
    )
    parts.append(_line(x0, phase_bottom, x1, phase_bottom, _AXIS_COLOR, 1.2))
    parts.append(
        _text((x0 + x1) / 2, phase_bottom + 20, "Frequency (Hz)", size=12, weight="600")
    )

    fmin, fmax = min(freq), max(freq)
    low = math.floor(math.log10(max(fmin, 1e-12)))
    high = math.ceil(math.log10(max(fmax, 1e-11)))
    for exponent in range(low, high + 1):
        decade = 10.0 ** exponent
        if decade < fmin or decade > fmax:
            continue
        x = _map_log(decade, fmin, fmax, x0, x1)
        parts.append(_line(x, gain_top, x, gain_bottom, _GRID_COLOR, 1, "4 4"))
        parts.append(_line(x, phase_top, x, phase_bottom, _GRID_COLOR, 1, "4 4"))
        parts.append(_text(x, phase_bottom + 16, _hertz(decade), size=11, color=_AXIS_COLOR))

    gain_points = [
        (_map_log(f, fmin, fmax, x0, x1), _map_linear(g, gmin, gmax, gain_top, gain_bottom))
        for f, g in zip(freq, gain)
    ]
    phase_points = [
        (_map_log(f, fmin, fmax, x0, x1), _map_linear(p, pmin, pmax, phase_top, phase_bottom))
        for f, p in zip(freq, phase)
    ]
    parts.append(_polyline(gain_points, _GAIN_COLOR))
    parts.append(_polyline(phase_points, _PHASE_COLOR))

    parts.append(_line(x0, gain_bottom + 10, x0 + 18, gain_bottom + 10, _GAIN_COLOR, 2))
    parts.append(_text(x0 + 24, gain_bottom + 14, "Gain (dB)", size=11, anchor="start"))
    parts.append(_line(x0 + 110, gain_bottom + 10, x0 + 128, gain_bottom + 10, _PHASE_COLOR, 2))
    parts.append(_text(x0 + 134, gain_bottom + 14, "Phase (°)", size=11, anchor="start"))

    parts.append(_guide_line(x0, gain_top, phase_bottom))
    parts.append(_markers(2, _GAIN_COLOR, _PHASE_COLOR))
    parts.append(_tooltip_group())
    parts.append(
        _scrub_controls(x0, x1, phase_bottom, _GAIN_COLOR)
    )
    parts.append(
        _data_script(
            "chart-data",
            {
                "freq": freq,
                "gain": gain,
                "phase": phase,
                "fmin": fmin,
                "fmax": fmax,
                "gmin": gmin,
                "gmax": gmax,
                "pmin": pmin,
                "pmax": pmax,
            },
        )
    )
    parts.append(_interactive_script())

    parts.append("</svg>")
    return "".join(parts)


def transient_svg(
    time_s: Sequence[float],
    vin_v: Sequence[float],
    vout_v: Sequence[float],
) -> str:
    """Render input and output waveforms on a millisecond / millivolt grid."""
    time_raw = _finite(time_s)
    vin_raw = _finite(vin_v)
    vout_raw = _finite(vout_v)
    count = min(len(time_raw), len(vin_raw), len(vout_raw))
    if count < 2:
        return (
            f'<svg class="chart" role="img" viewBox="0 0 {WIDTH} {HEIGHT}" '
            'xmlns="http://www.w3.org/2000/svg">'
            + _title_line(WIDTH, "Not enough transient data to plot")
            + "</svg>"
        )

    indices = _decimate(count)
    time_ms = [time_raw[i] * 1e3 for i in indices]
    vin_mv = [vin_raw[i] * 1e3 for i in indices]
    vout_mv = [vout_raw[i] * 1e3 for i in indices]

    x0, x1 = float(MARGIN_LEFT), float(WIDTH - MARGIN_RIGHT)
    y0, y1 = 56.0, 342.0

    combined = vin_mv + vout_mv
    vmin, vmax, _, _ = _linear_scale(combined, 0, 0)

    parts: list[str] = [
        f'<svg class="chart" role="img" viewBox="0 0 {WIDTH} {HEIGHT}" '
        'xmlns="http://www.w3.org/2000/svg">',
        _title_line(WIDTH, "Transient waveform (SPICE)"),
        _text(16, (y0 + y1) / 2, "Voltage (mV)", size=12, anchor="start", weight="600"),
    ]

    parts.extend(_y_ticks(vmin, vmax, y0, y1, x0, x1, _plain, 1))
    parts.append(_line(x0, y1, x1, y1, _AXIS_COLOR, 1.2))

    tmin, tmax = min(time_ms), max(time_ms)
    for index in range(6):
        fraction = index / 5
        value = tmin + (tmax - tmin) * fraction
        x = x0 + fraction * (x1 - x0)
        parts.append(_line(x, y0, x, y1, _GRID_COLOR, 1, "4 4"))
        parts.append(
            _text(x, y1 + 17, _trim(value), size=11, color=_AXIS_COLOR)
        )
    parts.append(
        _text((x0 + x1) / 2, y1 + 38, "Time (ms)", size=12, weight="600")
    )

    vin_points = [
        (x0 + (t - tmin) / (tmax - tmin) * (x1 - x0), _map_linear(v, vmin, vmax, y0, y1))
        for t, v in zip(time_ms, vin_mv)
    ]
    vout_points = [
        (x0 + (t - tmin) / (tmax - tmin) * (x1 - x0), _map_linear(v, vmin, vmax, y0, y1))
        for t, v in zip(time_ms, vout_mv)
    ]
    parts.append(_polyline(vin_points, _VIN_COLOR))
    parts.append(_polyline(vout_points, _VOUT_COLOR))

    legend_y = y1 + 56
    parts.append(_line(x0, legend_y, x0 + 18, legend_y, _VIN_COLOR, 2))
    parts.append(_text(x0 + 24, legend_y + 4, "Vin", size=11, anchor="start"))
    parts.append(_line(x0 + 74, legend_y, x0 + 92, legend_y, _VOUT_COLOR, 2))
    parts.append(_text(x0 + 98, legend_y + 4, "Vout", size=11, anchor="start"))

    parts.append(_guide_line(x0, y0, y1))
    parts.append(_markers(2, _VIN_COLOR, _VOUT_COLOR))
    parts.append(_tooltip_group())
    parts.append(
        _scrub_controls(x0, x1, y1, _VIN_COLOR)
    )
    parts.append(
        _data_script(
            "chart-data",
            {
                "time": time_ms,
                "vin": vin_mv,
                "vout": vout_mv,
                "tmin": tmin,
                "tmax": tmax,
                "vmin": vmin,
                "vmax": vmax,
            },
        )
    )
    parts.append(_interactive_script())

    parts.append("</svg>")
    return "".join(parts)

def _title_line(width: int, title: str) -> str:
    return f'<text x="{width // 2}" y="28" text-anchor="middle" class="chart-title">{title}</text>'

def _y_ticks(vmin: float, vmax: float, y0: float, y1: float, x0: float, x1: float, fmt=_plain, count: int = 5) -> list[str]:
    if vmax == vmin:
        vmax = vmin + 1.0
    out = []
    steps = max(1, count)
    for i in range(steps + 1):
        frac = i / steps
        val = vmin + frac * (vmax - vmin)
        y = y1 - frac * (y1 - y0)
        out.append(f'<line x1="{x0:.1f}" y1="{y:.1f}" x2="{x1:.1f}" y2="{y:.1f}" class="grid-line"/>')
        out.append(f'<text x="{x0 - 8:.1f}" y="{y + 4:.1f}" text-anchor="end" class="tick-label">{fmt(val)}</text>')
    return out
