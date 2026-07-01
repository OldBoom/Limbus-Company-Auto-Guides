#!/usr/bin/env python3
"""Fetch wiki.gg identity pages and write docs/parsed-ids/*.md files."""

from __future__ import annotations

import argparse
import json
import sys
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
from limbus_guides.ingestion.wiki_parser import (
    fetch_and_save,
    fetch_wikitext,
    filename_to_wiki_title,
    wiki_title_to_stem,
)
from limbus_guides.paths import CONFIG_DIR, PARSED_IDS_DIR

# Default batch from user selection (wiki page titles)
DEFAULT_PAGES = [
    "Liu_Assoc._South_Section_3_Yi_Sang",
    "Seven_Assoc._South_Section_4_Faust",
    "Cinq_Assoc._East_Section_3_Don_Quixote",
    "The_Manager_of_La_Manchaland_Don_Quixote",
    "Edgar_Family_Chief_Butler_Ry%C5%8Dsh%C5%AB",
    "Kurokumo_Clan_Wakashu_Ry%C5%8Dsh%C5%AB",
    "Blade_Lineage_Mentor_Meursault",
    "The_Ring_Fauvist_Student_Meursault",
    "The_Thumb_East_Capo_IIII_Meursault",
    "Liu_Assoc._South_Section_5_Hong_Lu",
    "Tingtang_Gang_Gangleader_Hong_Lu",
    "The_House_of_Spiders:_The_Ring_Nursefather_Hong_Lu",
    "Seven_Assoc._South_Section_4_Heathcliff",
    "Kurokumo_Clan_Wakashu_Heathcliff",
    "Kurokumo_Clan_Captain_Ishmael",
    "Edgar_Family_Butler_Ishmael",
    "Liu_Assoc._South_Section_4_Ishmael",
    "Kurokumo_Clan_Wakashu_Rodion",
    "Lobotomy_E.G.O::The_Sword_Sharpened_with_Tears_Rodion",
    "Liu_Assoc._South_Section_4_Director_Rodion",
    "The_Thumb_East_Soldato_II_Sinclair",
    "Devyat'_Assoc._North_Section_3_Sinclair",
    "The_House_of_Spiders:_The_Middle_Nursefather_Outis",
    "Lobotomy_E.G.O::Magic_Bullet_Outis",
    "The_Barber_of_La_Manchaland_Outis",
    "The_Priest_of_La_Manchaland_Gregor",
    "Firefist_Office_Survivor_Gregor",
]

# Hand-curated reference files — do not overwrite unless --force
PROTECTED_STEMS = {
    "Ring_Apprentice_Faust",
    "Blade_Lineage_Salsu_Yi_Sang",
    "Ring_Pointillist_Student_Yi_Sang",
    "The_House_of_Spiders_The_Ring_Apprentice_Faust",
}


def url_to_page_title(url: str) -> str:
    path = urlparse(url).path
    title = path.split("/wiki/")[-1] if "/wiki/" in path else path.strip("/")
    return unquote(title)


def collect_all_parsed_slugs() -> list[str]:
    return sorted(p.stem for p in PARSED_IDS_DIR.glob("*.md"))


def update_sinners_config(new_entries: dict[str, list[str]]) -> None:
    """Merge identity slugs into config/sinners.json by sinner name."""
    config_path = CONFIG_DIR / "sinners.json"
    config = load_json_config(config_path)
    sinner_map = {s["name"]: s for s in config.get("sinners", [])}

    for sinner_name, slugs in new_entries.items():
        if sinner_name not in sinner_map:
            continue
        existing = set(sinner_map[sinner_name].get("identities", []))
        for slug in slugs:
            existing.add(slug)
        sinner_map[sinner_name]["identities"] = sorted(existing)

    config_path.write_text(json.dumps(config, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Fetch wiki identities into docs/parsed-ids/")
    parser.add_argument("urls", nargs="*", help="Wiki URLs or page titles (optional)")
    parser.add_argument("--force", action="store_true", help="Overwrite protected reference files")
    parser.add_argument(
        "--all",
        action="store_true",
        help="Fetch every slug that already has a docs/parsed-ids/*.md file",
    )
    parser.add_argument("--update-config", action="store_true", help="Update config/sinners.json")
    args = parser.parse_args()

    if args.all:
        slug_pages = [(stem, filename_to_wiki_title(stem)) for stem in collect_all_parsed_slugs()]
    elif args.urls:
        slug_pages = [
            (wiki_title_to_stem(url_to_page_title(u) if u.startswith("http") else u), unquote(u))
            for u in args.urls
        ]
    else:
        pages = [unquote(p) for p in DEFAULT_PAGES]
        slug_pages = [(wiki_title_to_stem(p), p) for p in pages]

    sinner_additions: dict[str, list[str]] = {}
    ok, fail = 0, 0

    for stem, page in slug_pages:
        if stem in PROTECTED_STEMS and not args.force:
            print(f"SKIP (protected): {stem}")
            continue
        out_path = PARSED_IDS_DIR / f"{stem}.md"
        if out_path.exists() and not args.force:
            print(f"SKIP (exists): {stem}")
            continue
        try:
            path = fetch_and_save(page, stem=stem)
            print(f"OK: {path.name}")
            ok += 1
            if args.update_config:
                from limbus_guides.ingestion.wiki_parser import _extract_idpage, _line_value

                wt = fetch_wikitext(page)
                body = _extract_idpage(wt)
                sinner = _line_value(body, "sinner") or "Unknown"
                sinner_additions.setdefault(sinner, []).append(stem)
        except Exception as exc:
            print(f"FAIL: {page} — {exc}")
            fail += 1

    if args.update_config and sinner_additions:
        update_sinners_config(sinner_additions)
        print("Updated config/sinners.json")

    print(f"\nDone: {ok} saved, {fail} failed")
    return 1 if fail else 0


if __name__ == "__main__":
    raise SystemExit(main())
