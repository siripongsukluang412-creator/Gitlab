/* Interactive controls for the Lab 04 server-rendered SVG charts.
 *
 * The chart data is embedded in each SVG as a <script type="application/json">
 * element. This file is loaded as a normal external script from the page:
 * putting JavaScript inside an SVG element lets the HTML parser consume '<'
 * operators as markup, which silently corrupts the code.
 */
(function () {
  "use strict";

  var dataEl = document.getElementById("chart-data");
  if (!dataEl) {
    return;
  }

  var data;
  try {
    data = JSON.parse(dataEl.textContent || dataEl.text || "{}");
  } catch (exc) {
    return;
  }

  var svg = dataEl.ownerSVGElement || document.querySelector("svg.chart");
  if (!svg) {
    return;
  }

  var WIDTH = 780;
  var HEIGHT = 400;
  var X0 = 82;
  var X1 = WIDTH - 24;
  var BODE_GAIN_TOP = 52;
  var BODE_GAIN_BOTTOM = 206;
  var BODE_PHASE_TOP = 252;
  var BODE_PHASE_BOTTOM = 342;
  var TRAN_TOP = 56;
  var TRAN_BOTTOM = 342;

  var tooltip = svg.querySelector(".chart-tooltip");
  var tipText = tooltip ? tooltip.querySelector("text") : null;
  var guide = svg.querySelector(".chart-guide");
  var markers = Array.prototype.slice.call(svg.querySelectorAll(".chart-marker"));
  var scrubBar = svg.querySelector(".chart-scrub-bar");
  var scrubKnob = svg.querySelector(".chart-scrub-knob");
  var playBtn = svg.querySelector(".chart-play");
  var playLabel = svg.querySelector(".chart-play-label");

  var isBode = Array.isArray(data.freq);
  var count = isBode ? data.freq.length : (Array.isArray(data.time) ? data.time.length : 0);
  var index = 0;
  var playing = false;
  var animId = null;

  function mapLog(value, fmin, fmax, xa, xb) {
    var low = Math.log10(Math.max(fmin, 1e-12));
    var high = Math.log10(Math.max(fmax, 1e-11));
    if (Math.abs(high - low) < 1e-9) {
      return (xa + xb) / 2;
    }
    var frac = (Math.log10(Math.max(value, 1e-12)) - low) / (high - low);
    return xa + frac * (xb - xa);
  }

  function mapLinear(value, vmin, vmax, ya, yb) {
    if (Math.abs(vmax - vmin) < 1e-9) {
      return (ya + yb) / 2;
    }
    return yb - ((value - vmin) / (vmax - vmin)) * (yb - ya);
  }

  function xForIndex(i) {
    if (isBode) {
      return mapLog(data.freq[i], data.fmin, data.fmax, X0, X1);
    }
    var span = data.tmax - data.tmin;
    return Math.abs(span) < 1e-12
      ? (X0 + X1) / 2
      : X0 + ((data.time[i] - data.tmin) / span) * (X1 - X0);
  }

  function yForSeries(i, k) {
    if (isBode) {
      return k === 0
        ? mapLinear(data.gain[i], data.gmin, data.gmax, BODE_GAIN_TOP, BODE_GAIN_BOTTOM)
        : mapLinear(data.phase[i], data.pmin, data.pmax, BODE_PHASE_TOP, BODE_PHASE_BOTTOM);
    }
    return k === 0
      ? mapLinear(data.vin[i], data.vmin, data.vmax, TRAN_TOP, TRAN_BOTTOM)
      : mapLinear(data.vout[i], data.vmin, data.vmax, TRAN_TOP, TRAN_BOTTOM);
  }

  function readout(i) {
    if (isBode) {
      return (
        "f=" + Number(data.freq[i]).toPrecision(4) + " Hz" +
        "  gain=" + data.gain[i].toFixed(2) + " dB" +
        "  phase=" + data.phase[i].toFixed(1) + "°"
      );
    }
    return (
      "t=" + data.time[i].toFixed(4) + " ms" +
      "  Vin=" + data.vin[i].toFixed(2) + " mV" +
      "  Vout=" + data.vout[i].toFixed(2) + " mV"
    );
  }

  function hideTip() {
    if (tooltip) {
      tooltip.setAttribute("visibility", "hidden");
    }
    if (guide) {
      guide.setAttribute("visibility", "hidden");
    }
    markers.forEach(function (m) {
      m.setAttribute("visibility", "hidden");
    });
  }

  function setMarker(i, xpx, ypx) {
    if (count === 0) {
      return;
    }
    index = Math.max(0, Math.min(count - 1, i));
    var px = typeof xpx === "number" ? xpx : xForIndex(index);
    var primaryY = typeof ypx === "number" ? ypx : yForSeries(index, 0);

    markers.forEach(function (m, k) {
      m.setAttribute("cx", px.toFixed(2));
      m.setAttribute("cy", yForSeries(index, k).toFixed(2));
      m.setAttribute("visibility", "visible");
    });

    if (guide) {
      guide.setAttribute("x1", px.toFixed(2));
      guide.setAttribute("x2", px.toFixed(2));
      guide.setAttribute("y1", isBode ? BODE_GAIN_TOP : TRAN_TOP);
      guide.setAttribute("y2", isBode ? BODE_PHASE_BOTTOM : TRAN_BOTTOM);
      guide.setAttribute("visibility", "visible");
    }

    if (tooltip && tipText) {
      tipText.textContent = readout(index);
      var boxWidth = Math.max(220, tipText.textContent.length * 6.2);
      var tipBox = tooltip.querySelector("rect");
      if (tipBox) {
        tipBox.setAttribute("width", boxWidth.toFixed(1));
        tipBox.setAttribute("height", "22");
      }
      var tx = Math.min(Math.max(px + 12, 4), WIDTH - boxWidth - 4);
      var ty = Math.min(Math.max(primaryY - 30, 4), HEIGHT - 28);
      tooltip.setAttribute("transform", "translate(" + tx.toFixed(1) + "," + ty.toFixed(1) + ")");
      tooltip.setAttribute("visibility", "visible");
    }

    if (scrubKnob && count > 1) {
      var frac = index / (count - 1);
      scrubKnob.setAttribute("cx", (X0 + frac * (X1 - X0)).toFixed(2));
    }
  }

  function nearestIndex(px) {
    var best = 0;
    var bestDistance = Infinity;
    for (var i = 0; i < count; i += 1) {
      var distance = Math.abs(xForIndex(i) - px);
      if (distance < bestDistance) {
        bestDistance = distance;
        best = i;
      }
    }
    return best;
  }

  function svgPoint(event) {
    var box = svg.getBoundingClientRect();
    if (!box.width || !box.height) {
      return { x: 0, y: 0 };
    }
    var x = ((event.clientX - box.left) / box.width) * WIDTH;
    var y = ((event.clientY - box.top) / box.height) * HEIGHT;
    var point = svg.createSVGPoint();
    point.x = x;
    point.y = y;
    var ctm = svg.getScreenCTM();
    if (!ctm) {
      return { x: x, y: y };
    }
    var mapped = point.matrixTransform(ctm.inverse());
    return { x: mapped.x, y: mapped.y };
  }

  function onPointer(event) {
    if (count === 0) {
      return;
    }
    var point = svgPoint(event);
    var i = nearestIndex(point.x);
    setMarker(i);
  }

  function step() {
    if (!playing || count === 0) {
      return;
    }
    index = (index + 1) % count;
    setMarker(index);
    animId = window.requestAnimationFrame(step);
  }

  svg.addEventListener("mousemove", onPointer);
  svg.addEventListener("touchmove", function (event) {
    if (!event.touches.length) {
      return;
    }
    event.preventDefault();
    onPointer(event.touches[0]);
  }, { passive: false });
  svg.addEventListener("mouseleave", hideTip);
  svg.addEventListener("touchend", hideTip);

  if (playBtn) {
    playBtn.addEventListener("click", function () {
      playing = !playing;
      if (playLabel) {
        playLabel.textContent = playing ? "Pause" : "Play";
      }
      if (playing) {
        step();
      } else if (animId !== null) {
        window.cancelAnimationFrame(animId);
        animId = null;
      }
    });
  }

  if (scrubBar && count > 1) {
    scrubBar.addEventListener("click", function (event) {
      var point = svgPoint(event);
      var frac = Math.max(0, Math.min(1, (point.x - X0) / (X1 - X0)));
      setMarker(Math.round(frac * (count - 1)));
    });
  }
})();
