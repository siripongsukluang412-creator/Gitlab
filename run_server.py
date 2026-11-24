"""Start the Lab 04 simulator on http://127.0.0.1:5000.

Run with the interpreter that has Flask installed (``py run_server.py``
on Windows where ``py`` selects Python 3.14, not the bare ``python``
launcher which may point to a Python without Flask).
"""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent / "transistor-simulator"))

from app import app  # noqa: E402


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)
