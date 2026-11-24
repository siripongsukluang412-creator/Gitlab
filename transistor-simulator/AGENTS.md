# AGENTS.md — conventions for this project

## Architecture

- `dc_bias.py` holds the **analytical** engineering math for the three DC
  bias modes. It must not import Flask or touch HTTP.
- `spice_engine.py` holds the **SPICE** adapter: netlist generation,
  running `ngspice` as an external process, and parsing its ASCII output.
  It must not import Flask and must never invent result values.
- `svg_plots.py` renders dependency-free SVG charts from parsed arrays.
- `app.py` holds **only** HTTP concerns: reading the form, converting
  display units to SI units, validating the source, and rendering.
- `templates/index.html` must not compute engineering values. It only
  formats what the route passes in.
- `static/style.css` holds presentation only.

## Units

- All values passed to `dc_bias.py` and `spice_engine.py` are SI: volts,
  ohms, hertz, dimensionless β.
- Unit conversion happens once, in `app.py:read_form`.
- Display formatting lives in the Jinja filters (`volt`, `amp`, `mv`,
  `db`, `hz`, `gainx`).

## Validation

- Validate every bias field in `dc_bias.validate_inputs`.
- Validate the transient source in `spice_engine.validate_source`.
  Amplitude must be > 0 V peak (≤ 10 V); frequency 1 Hz–1 MHz.
- SPICE is allowed **only** for the voltage-divider reference circuit.
  Fixed/Emitter modes stay analytical and return HTTP 400 if a SPICE
  analysis is requested.
- SPICE also rejects `R_E = 0` because the reference netlist requires an
  emitter resistor (the analytical model still allows it).
- Return `(inputs, errors)`; `errors` maps a field name to an English
  message.
- Invalid input must return HTTP 400 and re-render the form with the
  user's values preserved. Never raise a 500 for bad input.
- A missing/failing ngspice engine must render an error panel and no
  chart. Never fabricate a trace or report success.

## Testing

- Write the failing test first (red → green → refactor).
- Run the full suite before claiming success:

  ```powershell
  py -m unittest discover -s tests -t . -v
  ```

- Every new engineering behavior needs a test in
  `tests/test_dc_bias.py` or `tests/test_spice_engine.py`.
- Every new route, unit-conversion, or rendering behavior needs a test in
  `tests/test_web.py`. Mock `app.spice_engine.run_simulation` in route
  tests; keep one real ngspice integration test in
  `tests/test_spice_engine.py`.

## Style

- Python: type hints on public functions, short docstrings, no Python
  dependencies beyond Flask.
- `ngspice` is an optional external engine, not a Python dependency.
- UI copy is English; code comments may be English or Thai.
- The form keeps the seven lab bias inputs plus the sine-source controls
  for the divider SPICE analyses. No circuit editor or FET features.
