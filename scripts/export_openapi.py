"""Export the active FastAPI schema for the frontend contract check."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from quoteflow.main import app


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("Usage: python scripts/export_openapi.py OUTPUT.json")
    output = Path(sys.argv[1])
    output.write_text(json.dumps(app.openapi(), indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
