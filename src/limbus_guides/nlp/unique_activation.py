"""Detect skills with non-standard activation rules worth calling out in guides."""

from __future__ import annotations

import re

from limbus_guides.nlp.mechanic_signals import MECHANIC_SIGNALS, clean_effect_text, extract_notable_effects

# Signal labels that describe identity-defining activation, not routine conditionals.
_UNIQUE_SIGNAL_LABELS = frozenset(
    {
        "kill-chain",
        "hp-finisher",
        "kill-reuse",
        "unbreakable",
        "sp-cost",
        "tremor-convert",
    }
)

_UNIQUE_TEXT_MARKERS = re.compile(
    r"Unclashable|Indiscriminate|does not trigger Defense|"
    r"cannot trigger this Skill|Its attack does not hit|"
    r"consume\s+(?:up to\s+)?\d+\s+\w+\s+Count|"
    r"Installation Art|alternate skill|Apply \d+ Offense Level",
    re.IGNORECASE,
)


def _skill_text_blob(skill: dict) -> str:
    parts: list[str] = []
    parts.extend(skill.get("skill_bonuses", []))
    parts.extend(skill.get("on_use_effects", []))
    for coin in skill.get("coin_effects", []):
        parts.append(coin.get("effect", ""))
    return " ".join(parts)


def has_unique_activation(skill: dict) -> bool:
    """True when a skill has special rules beyond standard attack + status application."""
    if skill.get("atk_weight") == 0:
        return True
    if skill.get("conditions"):
        return True
    if skill.get("resources_consumed"):
        return True
    if skill.get("has_unbreakable") and re.search(r"consume|At \d+\+", _skill_text_blob(skill), re.I):
        return True

    blob = _skill_text_blob(skill)
    if _UNIQUE_TEXT_MARKERS.search(blob):
        return True
    if re.search(r"\[On Kill\]|below.*% HP.*reuse|At \d+\+.*consume", blob, re.I):
        return True
    for signal in MECHANIC_SIGNALS:
        if signal.label in _UNIQUE_SIGNAL_LABELS and signal.pattern.search(blob):
            return True
    return False


def _shorten(text: str, limit: int = 140) -> str:
    clean = clean_effect_text(text).replace(" / ", "; ")
    if len(clean) <= limit:
        return clean
    return clean[: limit - 1].rstrip() + "…"


def _summarize_activation_segment(segment: str) -> str:
    """Compress resource-gated activation lines into one actionable phrase."""
    consume = re.search(
        r"At (\d+)\+ ([^,]+?), consume (\d+) [^:]+?:\s*(.+)",
        segment,
        re.I,
    )
    if consume:
        effects = consume.group(4)
        bits: list[str] = []
        if "Clash Power" in effects:
            bits.append("Clash Power boost")
        if "Unbreakable" in effects:
            bits.append("Unbreakable final coin")
        effect_str = " + ".join(bits) if bits else _shorten(effects, 80)
        return (
            f"At {consume.group(1)}+ {consume.group(2).strip()}, "
            f"spend {consume.group(3)} for {effect_str}"
        )
    return segment


_GENERIC_SCALING = re.compile(
    r"deal \+\d+% damage for every type of negative effect|"
    r"final power \+\d+ for every \d+ bleed",
    re.IGNORECASE,
)


def _is_generic_scaling(text: str) -> bool:
    return bool(_GENERIC_SCALING.search(text))


def describe_unique_activation(skill: dict, max_notes: int = 2) -> list[str]:
    """Return concise activation notes only for skills with unique rules."""
    if not has_unique_activation(skill):
        return []

    notes: list[str] = []

    for line in extract_notable_effects(skill, max_results=max_notes):
        if _is_generic_scaling(line):
            continue
        if any(
            kw in line.lower()
            for kw in (
                "kill",
                "execute",
                "unbreakable",
                "sp on use",
                "amplitude conversion",
                "tremor",
            )
        ):
            if line not in notes:
                notes.append(line)

    for eff in skill.get("on_use_effects", []):
        if not _UNIQUE_TEXT_MARKERS.search(eff) and "[On Kill]" not in eff:
            continue
        for segment in re.split(r"\s*;\s*", eff):
            if _is_generic_scaling(segment):
                continue
            if "[On Kill]" in segment and any("kill" in n.lower() for n in notes):
                continue
            if _UNIQUE_TEXT_MARKERS.search(segment) or "[On Kill]" in segment:
                short = _shorten(_summarize_activation_segment(segment))
                if short not in notes:
                    notes.append(short)

    for bonus in skill.get("skill_bonuses", []):
        for segment in re.split(r"\s*;\s*", bonus):
            if _is_generic_scaling(segment):
                continue
            if _UNIQUE_TEXT_MARKERS.search(segment) or re.search(
                r"consume|At \d+\+.*Count", segment, re.I
            ):
                short = _shorten(_summarize_activation_segment(segment))
                if short not in notes:
                    notes.append(short)

    if skill.get("atk_weight") == 0 and not notes:
        blob = _skill_text_blob(skill)
        if blob.strip():
            notes.append(_shorten(blob))

    return notes[:max_notes]
