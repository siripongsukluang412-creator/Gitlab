# AGENTS.md — conventions for this project

## Architecture

- `dc_bias.py` holds **all** engineering math. It must not import Flask
  or touch HTTP.
- `app.py` holds **only** HTTP concerns: reading the form, converting
  display units to SI units, and rendering.
- `templates/index.html` must not compute engineering values. It only
  formats what the route passes in.
- `static/style.css` holds presentation only.

## Units

- All values passed to `dc_bias.py` are SI: volts, ohms, dimensionless β.
- Unit conversion happens once, in `app.py:read_form`.
- Display formatting lives in the `volt` and `amp` Jinja filters.

## Validation

- Validate every field in `dc_bias.validate_inputs`.
- Return `(inputs, errors)`; `errors` maps a field name to an English
  message.
- Invalid input must return HTTP 400 and re-render the form with the
  user's values preserved. Never raise a 500 for bad input.

## Testing

- Write the failing test first (red → green → refactor).
- Run the full suite before claiming success:

  ```powershell
  py -m unittest discover -s tests -t . -v
  ```

- Every new engineering behavior needs a test in `tests/test_dc_bias.py`.
- Every new route or unit-conversion behavior needs a test in
  `tests/test_web.py`.

## Style

- Python: type hints on public functions, short docstrings, no
  dependencies beyond Flask.
- UI copy is English; code comments may be English or Thai.
- Keep the form to the seven lab inputs. No AC, transient, editor, or
  FET features.
