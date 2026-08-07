#!/usr/bin/env python3
"""Run the full ingestion → NLP → guide generation pipeline."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from limbus_guides.pipeline.run import main  # noqa: E402


if __name__ == "__main__":
    raise SystemExit(main())
