"""Load parsed identity markdown into structured JSON."""

from __future__ import annotations

import json
import re
from pathlib import Path

from limbus_guides.paths import IDENTITIES_DIR, PARSED_IDS_DIR


def _try_parse_skills(md_text: str) -> tuple[list[dict], list[dict]]:
    """Return (primary_skills, alternate_skills). Lazy import to avoid hard dependency."""
    try:
        from limbus_guides.nlp.skill_parser import parse_all_skills

        return parse_all_skills(md_text)
    except Exception:
        return [], []


def parse_traits_list(raw_traits: str | None) -> list[str]:
    """Split comma-separated Traits field; strip wiki pipe syntax (e.g. Soldato|name=...)."""
    if not raw_traits:
        return []
    return [
        part.split("|")[0].strip()
        for part in raw_traits.split(",")
        if part.strip()
    ]


def parse_identity_markdown(md_text: str, slug: str) -> dict:
    """Parse a docs/parsed-ids/*.md file into a JSON-serializable identity record."""
    lines = md_text.splitlines()
    title = slug.replace("_", " ")
    if lines and lines[0].startswith("# "):
        title = lines[0][2:].strip()

    quote_match = re.search(r'^> \*"(.+?)"\*', md_text, re.MULTILINE)
    flavor_quote = quote_match.group(1) if quote_match else ""

    def field(name: str) -> str | None:
        m = re.search(rf"\*\*{re.escape(name)}:\*\*\s*(.+)", md_text)
        return m.group(1).strip() if m else None

    sections: dict[str, str] = {}
    current = "_header"
    buf: list[str] = []
    for line in lines:
        if line.startswith("## "):
            if buf:
                sections[current] = "\n".join(buf).strip()
            current = line[3:].strip()
            buf = []
        else:
            buf.append(line)
    if buf:
        sections[current] = "\n".join(buf).strip()

    sinner = _infer_sinner(title)
    primary_skills, alternate_skills = _try_parse_skills(md_text)
    raw_traits = field("Traits")

    return {
        "slug": slug,
        "name": title,
        "sinner": sinner,
        "flavor_quote": flavor_quote,
        "rarity": field("Rarity"),
        "season": field("Season"),
        "release": field("Release"),
        "traits": raw_traits,
        "traits_list": parse_traits_list(raw_traits),
        "sections": sections,
        "raw_markdown": md_text,
        "description_text": _extract_description_text(md_text),
        "parsed_skills": primary_skills,
        "alternate_skills": alternate_skills,
    }


def _infer_sinner(title: str) -> str:
    sinners = [
        "Yi Sang", "Faust", "Don Quixote", "Ryōshū", "Meursault", "Hong Lu",
        "Heathcliff", "Ishmael", "Rodion", "Sinclair", "Outis", "Gregor",
    ]
    for s in sinners:
        if s in title or s.replace("ō", "o") in title:
            return s
    return "Unknown"


def _extract_description_text(md_text: str) -> str:
    skip_prefixes = ("#", ">", "---", "**Rarity", "**Season", "**Release", "**Traits", "**Stagger")
    parts = []
    for line in md_text.splitlines():
        s = line.strip()
        if not s or s.startswith(skip_prefixes):
            continue
        if s.startswith("|") and all(c in "|-: " for c in s):
            continue
        parts.append(s)
    return " ".join(parts)


def load_parsed_identity(slug: str, parsed_dir: Path | None = None) -> dict:
    base = parsed_dir or PARSED_IDS_DIR
    path = base / f"{slug}.md"
    if not path.exists():
        raise FileNotFoundError(path)
    return parse_identity_markdown(path.read_text(encoding="utf-8"), slug)


def load_all_parsed(parsed_dir: Path | None = None) -> dict[str, dict]:
    base = parsed_dir or PARSED_IDS_DIR
    return {
        p.stem: parse_identity_markdown(p.read_text(encoding="utf-8"), p.stem)
        for p in sorted(base.glob("*.md"))
    }


def save_identity_json(identity: dict, out_dir: Path | None = None) -> Path:
    dest = (out_dir or IDENTITIES_DIR) / f"{identity['slug']}.json"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(identity, indent=2, ensure_ascii=False), encoding="utf-8")
    return dest


def ingest_parsed_ids_to_json(parsed_dir: Path | None = None, out_dir: Path | None = None) -> list[Path]:
    identities = load_all_parsed(parsed_dir)
    return [save_identity_json(id_data, out_dir) for id_data in identities.values()]
