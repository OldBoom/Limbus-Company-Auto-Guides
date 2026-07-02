"""Discover and register identity-specific mechanics from parsed markdown."""

from __future__ import annotations

import json
import re
from datetime import date
from pathlib import Path

from limbus_guides.nlp.mechanics import (
    STAT_MODIFIERS,
    STATUS_EFFECTS,
    UNIQUE_MECHANICS,
    clear_mechanics_cache,
)
from limbus_guides.paths import CONFIG_DIR, PARSED_IDS_DIR

_REGISTRY_PATH = CONFIG_DIR / "unique_mechanics.json"

# Generic buffs that may appear in Key Status Effects but are not identity resources.
_NON_RESOURCE_KEY_STATUS = frozenset({
    "Attack Power Up",
    "Defense Power Up",
    "Slash Resist Down",
    "Gluttony DMG Up",
    "Damage Up",
    "Damage Down",
})

# Key-status headings that are standard shared effects, not identity resources.
_KEY_STATUS_SHARED_EFFECTS = frozenset({
    "Impending Ruin",
})

_MENTION_RE_CACHE: dict[str, re.Pattern[str]] = {}


def count_mechanic_mentions(text: str, term: str) -> int:
    """Count whole-phrase mentions; avoids substring hits (e.g. Charge in Recharge)."""
    if not text or not term:
        return 0
    key = term.lower()
    pat = _MENTION_RE_CACHE.get(key)
    if pat is None:
        pat = re.compile(
            r"(?<![A-Za-z])" + re.escape(term) + r"(?![A-Za-z])",
            re.IGNORECASE,
        )
        _MENTION_RE_CACHE[key] = pat
    return len(pat.findall(text))


def parse_key_status_effects(md: str) -> list[str]:
    """Return ### headings under ## Key Status Effects."""
    m = re.search(r"^## Key Status Effects\s*$", md, re.M)
    if not m:
        return []
    rest = md[m.end() :]
    end = re.search(r"^## ", rest, re.M)
    section = rest[: end.start()] if end else rest
    return [h.strip() for h in re.findall(r"^### (.+)$", section, re.M) if h.strip()]


def load_registry() -> dict:
    if not _REGISTRY_PATH.exists():
        return {"mechanics": []}
    return json.loads(_REGISTRY_PATH.read_text(encoding="utf-8"))


def load_discovered_mechanics() -> list[str]:
    """Names only, in registry order."""
    return [entry["name"] for entry in load_registry().get("mechanics", [])]


def get_all_unique_mechanics() -> list[str]:
    """Built-in UNIQUE_MECHANICS plus auto-discovered config entries."""
    seen: set[str] = set()
    merged: list[str] = []
    for name in [*UNIQUE_MECHANICS, *load_discovered_mechanics()]:
        if name not in seen:
            seen.add(name)
            merged.append(name)
    return merged


def _is_registerable(term: str) -> bool:
    if not term or term in _NON_RESOURCE_KEY_STATUS:
        return False
    if term in STATUS_EFFECTS or term in STAT_MODIFIERS:
        return False
    if term in UNIQUE_MECHANICS:
        return False
    return True


def sync_from_parsed_ids(
    parsed_dir: Path | None = None,
    *,
    write: bool = True,
) -> dict:
    """
    Scan parsed-ids markdown for Key Status Effects not yet registered.
    Appends new terms to config/unique_mechanics.json.
    """
    parsed_dir = parsed_dir or PARSED_IDS_DIR
    registry = load_registry()
    by_name: dict[str, dict] = {e["name"]: e for e in registry.get("mechanics", [])}
    added: list[str] = []

    for path in sorted(parsed_dir.glob("*.md")):
        md = path.read_text(encoding="utf-8")
        slug = path.stem
        for term in parse_key_status_effects(md):
            if not _is_registerable(term):
                continue
            if term in by_name:
                if slug not in by_name[term].get("source_slugs", []):
                    by_name[term].setdefault("source_slugs", []).append(slug)
                continue
            if term in UNIQUE_MECHANICS:
                continue
            entry = {
                "name": term,
                "source_slugs": [slug],
                "discovered_at": date.today().isoformat(),
            }
            by_name[term] = entry
            added.append(term)

    registry["mechanics"] = sorted(by_name.values(), key=lambda e: e["name"].lower())
    if write:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        _REGISTRY_PATH.write_text(
            json.dumps(registry, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        if added:
            clear_mechanics_cache()

    return {"added": added, "total": len(registry["mechanics"])}


def sync_from_markdown(
    md: str,
    slug: str,
    *,
    write: bool = True,
    only: set[str] | None = None,
) -> list[str]:
    """Register Key Status Effects from a single identity markdown file."""
    registry = load_registry()
    by_name: dict[str, dict] = {e["name"]: e for e in registry.get("mechanics", [])}
    added: list[str] = []

    for term in parse_key_status_effects(md):
        if only is not None and term not in only:
            continue
        if not _is_registerable(term):
            continue
        if term in by_name:
            if slug not in by_name[term].get("source_slugs", []):
                by_name[term].setdefault("source_slugs", []).append(slug)
            continue
        if term in UNIQUE_MECHANICS:
            continue
        by_name[term] = {
            "name": term,
            "source_slugs": [slug],
            "discovered_at": date.today().isoformat(),
        }
        added.append(term)

    if write:
        registry["mechanics"] = sorted(by_name.values(), key=lambda e: e["name"].lower())
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        _REGISTRY_PATH.write_text(
            json.dumps(registry, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        if added:
            clear_mechanics_cache()

    return added


def enrich_mechanic_profile(profile: dict, identity: dict) -> dict:
    """
    Merge Key Status Effects and discovered mechanic counts into unique_mechanics
    so unique_mechanics_archetype can see new identity resources.
    """
    md = identity.get("raw_markdown") or identity.get("description_text") or ""
    key_fx = parse_key_status_effects(md)
    profile = dict(profile)
    profile["key_status_effects"] = key_fx

    unique = dict(profile.get("unique_mechanics", {}))

    for term in get_all_unique_mechanics():
        count = count_mechanic_mentions(md, term)
        if count:
            unique[term] = max(unique.get(term, 0), count)

    for term in key_fx:
        if term in _NON_RESOURCE_KEY_STATUS:
            continue
        body_count = count_mechanic_mentions(md, term)
        if term in _KEY_STATUS_SHARED_EFFECTS:
            if body_count:
                unique[term] = max(unique.get(term, 0), body_count)
            continue
        # Key Status headings are authoritative for identity-specific resources.
        unique[term] = max(unique.get(term, 0), body_count, 8)

    profile["unique_mechanics"] = unique
    return profile
