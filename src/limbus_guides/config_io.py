"""Load project JSON config files."""

from __future__ import annotations

import json
from pathlib import Path


def load_json_config(path: Path) -> dict:
    """Parse JSON config; ignores whole-line ``#`` comments if present."""
    text = path.read_text(encoding="utf-8")
    lines = [line for line in text.splitlines() if not line.lstrip().startswith("#")]
    return json.loads("\n".join(lines))
