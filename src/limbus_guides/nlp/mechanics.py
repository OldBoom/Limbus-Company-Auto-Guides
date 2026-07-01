"""Game mechanic extraction via spaCy EntityRuler (with regex fallback)."""

from __future__ import annotations

import re
from collections import Counter
from functools import lru_cache
from pathlib import Path

STATUS_EFFECTS = [
    "Bleed", "Burn", "Tremor", "Rupture", "Sinking", "Poise", "Charge",
    "Bind", "Haste", "Protection", "Shield",
]
STAT_MODIFIERS = [
    "Defense Level Up", "Defense Level Down", "Offense Level Up", "Offense Level Down",
    "Damage Up", "Damage Down", "Slash DMG Up", "Pierce DMG Up", "Blunt DMG Up",
    "Clash Power", "Coin Power", "Base Power", "Final Power", "Atk Weight",
]
UNIQUE_MECHANICS = [
    # Ring identity resources
    "Iron Maiden", "Corpus Ingredient", "Artwork: Fascia", "The Self Unbound", "Flow State",
    # Unique Burn variants
    "Dark Flame",
    # Unique Bleed variants / La Manchaland resource
    "Bloodfeast", "Hardblood", "Sewing Target", "Blood-tinged Scissorblades",
    # N Corp
    "Nails", "Fanatic",
    # Deathrite family (Heishou)
    "Deathrite",
    # Dieci resource loop
    "Discard", "Insight", "Erudition",
    # Charge-adjacent
    "Photoelectricity", "Overcharge",
    # Magic Bullet resource
    "Magic Bullet",
    # Princess of La Manchaland
    "Blooming Thorn", "Festive Fever",
    # Shi Faust
    "Arrow",
    # Heishou / Wu Yi Sang
    "Concussion", "Linebreaker",
    "Tarnished Blood", "Life from Death", "Heishou Bolus Contamination",
    # Wuthering Heights / Wild Hunt
    "Coffin", "Dullahan", "Impending Ruin", "Wild Hunt",
    # Talisman (Red Sheet Sinclair)
    "Talisman",
    # Universal utility
    "Assist Defense", "Somatic Frisson-inspiring Melody", "Unbreakable Coin",
]
ALL_MECHANICS = STATUS_EFFECTS + STAT_MODIFIERS + UNIQUE_MECHANICS

TRIGGER_RE = re.compile(
    r"\[(On Hit|On Use|Clash Win|Heads Hit|On Evade|Combat Start|Attack End|Skill End)\]"
)


def _load_status_effects_reference(path: Path | None = None) -> list[str]:
    from limbus_guides.paths import DOCS_DIR

    ref = path or (DOCS_DIR / "status-effects.md")
    if not ref.exists():
        return STATUS_EFFECTS
    extra = []
    for line in ref.read_text(encoding="utf-8").splitlines():
        if line.startswith("### ") and not line.startswith("### S"):
            name = line[4:].strip()
            if name and name not in ALL_MECHANICS:
                extra.append(name)
    return list(dict.fromkeys(STATUS_EFFECTS + extra[:20]))


@lru_cache(maxsize=1)
def _get_nlp():
    import spacy

    nlp = spacy.load("en_core_web_sm")
    if "entity_ruler" not in nlp.pipe_names:
        ruler = nlp.add_pipe("entity_ruler", before="ner")
        patterns = []
        status_effects = _load_status_effects_reference()
        for effect in status_effects:
            patterns.append({"label": "STATUS_EFFECT", "pattern": effect})
        for mod in STAT_MODIFIERS:
            patterns.append({"label": "STAT_MODIFIER", "pattern": mod})
        for mech in UNIQUE_MECHANICS:
            patterns.append({"label": "UNIQUE_MECHANIC", "pattern": mech})
        ruler.add_patterns(patterns)
    return nlp


def clear_mechanics_cache() -> None:
    """Clear spaCy NLP cache after UNIQUE_MECHANICS list is patched at runtime."""
    _get_nlp.cache_clear()


def extract_mechanics(text: str) -> dict:
    """Return mechanic profile from identity description text."""
    nlp = _get_nlp()
    doc = nlp(text)
    by_label: dict[str, Counter] = {
        "STATUS_EFFECT": Counter(),
        "STAT_MODIFIER": Counter(),
        "UNIQUE_MECHANIC": Counter(),
    }
    for ent in doc.ents:
        if ent.label_ in by_label:
            by_label[ent.label_][ent.text] += 1

    triggers = Counter(TRIGGER_RE.findall(text))
    all_mechs = Counter()
    for c in by_label.values():
        all_mechs.update(c)

    primary = [m for m, _ in all_mechs.most_common(3)]
    secondary = [m for m, _ in all_mechs.most_common(10)[3:8]]

    return {
        "primary_mechanics": primary,
        "secondary_mechanics": secondary,
        "status_effects": dict(by_label["STATUS_EFFECT"]),
        "stat_modifiers": dict(by_label["STAT_MODIFIER"]),
        "unique_mechanics": dict(by_label["UNIQUE_MECHANIC"]),
        "triggers": dict(triggers),
        "all_mechanics": dict(all_mechs),
    }


def extract_mechanics_regex_only(text: str) -> dict:
    """Fallback when spaCy model is not installed."""
    found = Counter()
    lower = text.lower()
    for mech in ALL_MECHANICS:
        if mech.lower() in lower:
            found[mech] += lower.count(mech.lower())
    triggers = Counter(TRIGGER_RE.findall(text))
    primary = [m for m, _ in found.most_common(3)]
    return {
        "primary_mechanics": primary,
        "secondary_mechanics": [m for m, _ in found.most_common(10)[3:8]],
        "triggers": dict(triggers),
        "all_mechanics": dict(found),
    }


def build_mechanic_profile(identity: dict) -> dict:
    text = identity.get("description_text") or identity.get("raw_markdown", "")
    try:
        profile = extract_mechanics(text)
    except Exception:
        profile = extract_mechanics_regex_only(text)
    profile["identity_slug"] = identity.get("slug")
    return profile
