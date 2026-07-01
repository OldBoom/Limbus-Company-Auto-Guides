"""Request logging and monitoring hooks."""

from __future__ import annotations

import json
import time
from pathlib import Path

from limbus_guides.paths import DATA_DIR

LOG_PATH = DATA_DIR / "logs" / "requests.jsonl"


def log_request(
    *,
    input_slug: str,
    output_chars: int,
    latency_ms: int,
    token_count: int = 0,
    cost_eur: float = 0.0,
    generator: str = "template",
) -> None:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "input_slug": input_slug,
        "output_chars": output_chars,
        "latency_ms": latency_ms,
        "token_count": token_count,
        "cost_eur": cost_eur,
        "generator": generator,
    }
    with LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")
