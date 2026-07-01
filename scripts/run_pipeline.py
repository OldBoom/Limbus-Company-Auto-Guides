#!/usr/bin/env python3
"""Run the full ingestion → NLP → guide generation pipeline."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from limbus_guides.pipeline.run import run_pipeline  # noqa: E402


def main() -> int:
    guides = run_pipeline(use_ollama=False)
    print(f"Generated {len(guides)} guides in data/guides/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
