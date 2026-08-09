#!/usr/bin/env python3
"""Fetch the wiki's mechanic pages into docs/_wiki-reference/ (gitignored).

These pages define what a mechanic *does*. They are the ground truth for any claim a
generated guide makes about game rules.

They exist because inferring mechanics from skill text is unreliable: an audit once
concluded "Nails is a Tremor mechanic" purely because N Corp. kits apply both on the same
coin. The Bleed page settles it in one line — "Nails is a source of Bleed". Identity
markdown in docs/parsed-ids/ answers "which identities have X", never "what does X do".

  python scripts/fetch_wiki_reference.py            # refresh all pages
  python scripts/fetch_wiki_reference.py --list     # show what is tracked
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from limbus_guides.ingestion.wiki_parser import fetch_wikitext  # noqa: E402

# Gitignored: these pages are ~500KB of raw wikitext and duplicate
# docs/status-effects.md for everything except the few gaps noted in its header.
OUT_DIR = ROOT / "docs" / "_wiki-reference"

# Wiki page title -> what it is authoritative for. Redirect targets are used directly
# ("Haste" redirects to "Haste & Bind").
PAGES: dict[str, str] = {
    "Status Effects": "master list of every status effect",
    "Battles": "turn structure, clashes, coins, defense skills, Stagger",
    "Sanity": "SP and its effect on Heads probability",
    "Sin Resonance": "Resonance and Absolute Resonance",
    "Bleed": "Bleed, and its related effects Nails and Bloodfeast",
    "Burn": "Burn",
    "Tremor": "Tremor, Tremor Burst, Amplitude Conversion",
    "Rupture": "Rupture",
    "Sinking": "Sinking",
    "Poise": "Poise",
    "Charge": "Charge",
    "Haste & Bind": "Haste and Bind",
    "Fragile & Resist Down": "Fragile, typed Fragility, Resist Down",
    "Paralyze": "Paralyze",
    "Aggro": "Aggro",
    "Protection": "Protection",
}


def filename_for(title: str) -> str:
    return title.replace(" ", "_").replace("&", "and").replace("__", "_") + ".wiki"


def main() -> int:
    parser = argparse.ArgumentParser(description="Refresh docs/wiki-reference/")
    parser.add_argument("--list", action="store_true", help="List tracked pages and exit")
    args = parser.parse_args()

    if args.list:
        for title, purpose in PAGES.items():
            print(f"  {title:26s} {filename_for(title):32s} {purpose}")
        return 0

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    failures: list[tuple[str, str]] = []
    for title in PAGES:
        try:
            wikitext = fetch_wikitext(title)
        except Exception as exc:
            failures.append((title, str(exc)))
            print(f"FAIL {title} — {exc}")
            continue
        if wikitext.strip().lower().startswith("#redirect"):
            failures.append((title, "page is a redirect; track its target instead"))
            print(f"FAIL {title} — redirect, track the target page instead")
            continue
        (OUT_DIR / filename_for(title)).write_text(wikitext, encoding="utf-8")
        print(f"OK   {title:26s} {len(wikitext):7d} chars")
        time.sleep(0.4)

    print(f"\nDone: {len(PAGES) - len(failures)} saved, {len(failures)} failed")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
