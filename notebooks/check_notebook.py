"""Count code cells whose saved output is an error. Exit status 1 if there are any.

    uv run python notebooks/check_notebook.py
"""
import json
import sys
from pathlib import Path

NOTEBOOK = Path(__file__).resolve().with_name("analysis.ipynb")


def error_cells(path: Path = NOTEBOOK) -> int:
    cells = json.loads(path.read_text(encoding="utf-8"))["cells"]
    return sum(1 for c in cells if c["cell_type"] == "code"
               for o in c.get("outputs", []) if o.get("output_type") == "error")


if __name__ == "__main__":
    n = error_cells()
    print(f"error cells: {n}")
    sys.exit(1 if n else 0)
