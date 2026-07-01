#!/usr/bin/env python3
"""Download identity portraits from the wiki List of Identities page."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from limbus_guides.config_io import load_json_config
from limbus_guides.ingestion.identity_portraits import (
    fetch_all_listed_portraits,
    fetch_identity_portraits,
)
from limbus_guides.paths import CONFIG_DIR, GUIDES_DIR

DEFAULT_OUT = ROOT / "src" / "limbus_guides" / "dashboard" / "static" / "images" / "identities"


def _slugs_from_guides() -> list[str]:
    return sorted(
        p.stem for p in GUIDES_DIR.glob("*.json") if p.name != "manifest.json"
    )


def _slugs_from_config() -> list[str]:
    cfg = load_json_config(CONFIG_DIR / "sinners.json")
    slugs: list[str] = []
    for sinner in cfg.get("sinners", []):
        slugs.extend(sinner.get("identities", []))
    return sorted(set(slugs))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=DEFAULT_OUT,
        help=f"Output directory (default: {DEFAULT_OUT})",
    )
    parser.add_argument(
        "--source",
        choices=("all", "guides", "config", "union"),
        default="all",
        help="Which identities to fetch (default: every identity on the wiki list page)",
    )
    args = parser.parse_args()

    if args.source == "all":
        result = fetch_all_listed_portraits(args.out_dir)
        manifest = result["identities"]
        missing = result["missing"]
        print(f"Downloaded {len(manifest)} portraits -> {args.out_dir}")
        if missing:
            print(f"Missing ({len(missing)}):", ", ".join(missing), file=sys.stderr)
            return 1
        print(json.dumps({"count": len(manifest), "out_dir": str(args.out_dir)}, indent=2))
        return 0

    if args.source == "guides":
        slugs = _slugs_from_guides()
    elif args.source == "config":
        slugs = _slugs_from_config()
    else:
        slugs = sorted(set(_slugs_from_guides()) | set(_slugs_from_config()))

    if not slugs:
        print("No identity slugs found.", file=sys.stderr)
        return 1

    result = fetch_identity_portraits(slugs, args.out_dir)
    manifest = result["identities"]
    missing = result["missing"]

    print(f"Downloaded {len(manifest)} portraits -> {args.out_dir}")
    if missing:
        print(f"Missing ({len(missing)}):", ", ".join(missing), file=sys.stderr)
        return 1

    print(json.dumps({"count": len(manifest), "out_dir": str(args.out_dir)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
