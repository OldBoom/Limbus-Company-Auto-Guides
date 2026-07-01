#!/usr/bin/env python3
"""Run evaluation metrics and write data/evaluation_results.json.

Usage
-----
  python scripts/run_evaluation.py                  # full 3-column evaluation (default)
  python scripts/run_evaluation.py --baseline naive     # print naive ROUGE only
  python scripts/run_evaluation.py --baseline ablation  # print ablation ROUGE only
"""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from limbus_guides.eval.metrics import run_evaluation  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate guide quality.")
    parser.add_argument(
        "--baseline",
        choices=["naive", "ablation"],
        default=None,
        help="Print only the specified baseline ROUGE-L score and exit.",
    )
    args = parser.parse_args()

    results = run_evaluation()

    if args.baseline:
        score = results["rouge_l"][args.baseline]
        print(f"ROUGE-L ({args.baseline}): {score}")
        return 0

    out = ROOT / "data" / "evaluation_results.json"
    out.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(json.dumps(results, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
