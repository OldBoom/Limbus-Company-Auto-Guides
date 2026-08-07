#!/usr/bin/env python3
"""Sync docs/parsed-ids/*.md against the live wiki identity roster.

The roster is discovered from the wiki itself (pages transcluding Template:IDPage),
so new identities are picked up without editing this file. With no arguments the
script fetches every roster page that has no local markdown yet.

  python scripts/fetch_wiki_identities.py --dry-run     # report drift, fetch nothing
  python scripts/fetch_wiki_identities.py               # fetch what is missing
  python scripts/fetch_wiki_identities.py --limit 20    # fetch missing, 20 at a time
  python scripts/fetch_wiki_identities.py --all --force # re-fetch the whole roster
  python scripts/fetch_wiki_identities.py --rebuild-config
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path
from urllib.parse import unquote, urlparse

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

# Ensure Unicode prints on Windows terminals
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from limbus_guides.config_io import load_json_config
from limbus_guides.ingestion.markdown_loader import _infer_sinner
from limbus_guides.ingestion.wiki_parser import (
    fetch_and_save,
    fetch_identity_roster,
    wiki_title_to_stem,
)
from limbus_guides.paths import CONFIG_DIR, PARSED_IDS_DIR

# Hand-curated parses — do not overwrite unless --force
PROTECTED_STEMS = {
    "Ring_Apprentice_Faust",
    "Blade_Lineage_Salsu_Yi_Sang",
    "Ring_Pointillist_Student_Yi_Sang",
}


def url_to_page_title(url: str) -> str:
    path = urlparse(url).path
    title = path.split("/wiki/")[-1] if "/wiki/" in path else path.strip("/")
    return unquote(title)


def local_stems() -> set[str]:
    return {p.stem for p in PARSED_IDS_DIR.glob("*.md")}


def identity_title(md_path: Path) -> str:
    """Display title from the markdown's H1, falling back to the filename stem."""
    with md_path.open(encoding="utf-8") as fh:
        first = fh.readline().strip()
    return first[2:].strip() if first.startswith("# ") else md_path.stem.replace("_", " ")


def rebuild_sinners_config() -> dict[str, list[str]]:
    """Regenerate config/sinners.json from local parsed markdown.

    The roster is derived output, not hand-curated input — sinner ids already in the
    file are preserved so existing references stay stable.
    """
    config_path = CONFIG_DIR / "sinners.json"
    existing = load_json_config(config_path) if config_path.exists() else {}
    known_ids = {s["name"]: s.get("id") for s in existing.get("sinners", [])}

    by_sinner: dict[str, list[str]] = defaultdict(list)
    for path in sorted(PARSED_IDS_DIR.glob("*.md")):
        by_sinner[_infer_sinner(identity_title(path))].append(path.stem)

    def slugify(name: str) -> str:
        return (
            name.lower()
            .replace(" ", "_")
            .replace("ō", "o")
            .replace("ū", "u")
            .replace("ö", "o")
        )

    config = {
        "_note": existing.get(
            "_note",
            "Sinners and identity wiki slugs. Full URLs: "
            "https://limbuscompany.wiki.gg/wiki/<slug>",
        ),
        "sinners": [
            {
                "id": known_ids.get(name) or slugify(name),
                "name": name,
                "identities": sorted(slugs),
            }
            for name, slugs in sorted(by_sinner.items())
            if name != "Unknown"
        ],
    }
    config_path.write_text(
        json.dumps(config, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return {name: sorted(slugs) for name, slugs in by_sinner.items()}


def main() -> int:
    parser = argparse.ArgumentParser(description="Sync parsed-ids against the live wiki roster")
    parser.add_argument("urls", nargs="*", help="Explicit wiki URLs or page titles")
    parser.add_argument("--all", action="store_true", help="Re-fetch every roster page")
    parser.add_argument("--force", action="store_true", help="Overwrite protected stems")
    parser.add_argument("--limit", type=int, help="Stop after N successful fetches")
    parser.add_argument("--dry-run", action="store_true", help="Report drift, fetch nothing")
    parser.add_argument(
        "--rebuild-config",
        action="store_true",
        help="Regenerate config/sinners.json from local parsed files and exit",
    )
    args = parser.parse_args()

    if args.rebuild_config:
        by_sinner = rebuild_sinners_config()
        total = sum(len(v) for v in by_sinner.values())
        for name, slugs in sorted(by_sinner.items()):
            print(f"  {len(slugs):3d}  {name}")
        print(f"Rebuilt config/sinners.json — {total} identities across {len(by_sinner)} sinners")
        return 0

    if args.urls:
        targets = [
            (wiki_title_to_stem(url_to_page_title(u) if u.startswith("http") else u),
             unquote(u))
            for u in args.urls
        ]
    else:
        roster = fetch_identity_roster()
        have = local_stems()
        by_stem = {wiki_title_to_stem(t): t for t in roster}
        orphans = sorted(have - set(by_stem))
        missing = sorted(s for s in by_stem if s not in have)

        print(f"Live roster: {len(roster)} identities")
        print(f"Local parsed: {len(have)}  |  missing: {len(missing)}  |  orphaned: {len(orphans)}")
        if orphans:
            print("  Orphaned (local file not on the wiki roster — renamed or removed):")
            for stem in orphans:
                print(f"    {stem}")

        selected = sorted(by_stem) if args.all else missing
        targets = [(stem, by_stem[stem]) for stem in selected]

    if args.dry_run:
        for stem, page in targets:
            print(f"WOULD FETCH: {stem}  <-  {page}")
        print(f"\nDry run: {len(targets)} page(s) would be fetched")
        return 0

    if not targets:
        print("\nNothing to fetch — local parses match the live roster.")
        return 0

    print(f"\nFetching {len(targets)} page(s)...")
    ok, skipped = 0, 0
    failures: list[tuple[str, str]] = []

    for stem, page in targets:
        if args.limit is not None and ok >= args.limit:
            print(f"Reached --limit {args.limit}; {len(targets) - ok - skipped} still pending")
            break
        if stem in PROTECTED_STEMS and not args.force:
            print(f"SKIP (protected): {stem}")
            skipped += 1
            continue
        try:
            fetch_and_save(page, stem=stem)
            ok += 1
            print(f"OK   [{ok}/{len(targets)}] {stem}")
        except Exception as exc:
            failures.append((page, str(exc)))
            print(f"FAIL {page} — {exc}")

    print(f"\nDone: {ok} saved, {skipped} skipped, {len(failures)} failed")
    if failures:
        print("\nFailures:")
        for page, err in failures:
            print(f"  {page}: {err}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
