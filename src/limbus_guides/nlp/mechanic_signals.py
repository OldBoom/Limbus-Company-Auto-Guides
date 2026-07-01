"""Data-driven mechanic signal table for skill guide generation."""

from __future__ import annotations

import re
from typing import NamedTuple

_WIKI_MARKUP = re.compile(r"\[\[:[^\]]+\]\]?|\[\[[^\]]+\]\]")
_TRIGGER_PREFIX = re.compile(r"^(?:\[[^\]]+\]\s*)+")

_NOTABLE_MARKERS = re.compile(
    r"%|\[On Kill\]|\[Reuse|\[Heads Hit\]|\[On Use\]|<|>|\+|\bbelow\b|\bless than\b",
    re.IGNORECASE,
)


class MechanicSignal(NamedTuple):
    pattern: re.Pattern[str]
    label: str
    advice: str


MECHANIC_SIGNALS: list[MechanicSignal] = [
    MechanicSignal(
        re.compile(r"\[On Kill\].*use this skill", re.I),
        "kill-chain",
        "chains on kill — close out injured enemies to trigger a free second attack",
    ),
    MechanicSignal(
        re.compile(
            r"(?:below|less than)\s*(\d+)%\s*HP.*reuse|reuse.*(?:below|less than)\s*(\d+)%\s*HP",
            re.I,
        ),
        "hp-finisher",
        "executes weakened targets — reuses coin against enemies below {hp}% HP",
    ),
    MechanicSignal(
        re.compile(r"\[Reuse\s*-[^\]]+\]\s*\+(\d+)%", re.I),
        "reuse-damage",
        "reuse hit: +{pct}% damage",
    ),
    MechanicSignal(
        re.compile(
            r"(?:If target has|At)\s+(\d+)\+\s+(Bleed|Burn|Rupture|Poise|Sinking|Tremor)[^,;]*,?\s*"
            r"(double|deal \+\d+%|Coin Power \+|Base Power \+)",
            re.I,
        ),
        "status-threshold",
        "Delay until {n}+ {status} on target — that is when the damage condition activates.",
    ),
    MechanicSignal(
        re.compile(r"double.*crit chance", re.I),
        "crit-double",
        "doubles crit chance under condition",
    ),
    MechanicSignal(
        re.compile(r"\[On Kill\].*reuse", re.I),
        "kill-reuse",
        "reuses skill on kill",
    ),
    MechanicSignal(
        re.compile(r"convert.*Unbreakable|Unbreakable Coin", re.I),
        "unbreakable",
        "converts coins to Unbreakable under condition",
    ),
    MechanicSignal(
        re.compile(r"\+\d+\s+Aggro", re.I),
        "aggro-draw",
        "draws enemy aggro — intended to absorb hits",
    ),
    MechanicSignal(
        re.compile(r"Amplitude Conversion", re.I),
        "tremor-convert",
        "triggers Amplitude Conversion into Tremor — Scorch",
    ),
    MechanicSignal(
        re.compile(r"\[On Use\].*Lose\s+(\d+)\s+SP", re.I),
        "sp-cost",
        "costs {n} SP on use — manage SP above 0 to stay in Blessing state",
    ),
]


def clean_effect_text(text: str) -> str:
    """Strip wiki markup and leading trigger tags from coin/skill text."""
    cleaned = _WIKI_MARKUP.sub("", text)
    cleaned = re.sub(r"\*+", "", cleaned)
    cleaned = _TRIGGER_PREFIX.sub("", cleaned.strip())
    cleaned = re.sub(r"\s*;\s*", "; ", cleaned)
    return cleaned.strip(" ;")


def _render_advice(template: str, match: re.Match[str]) -> str:
    groups = match.groups()
    rendered = template
    if "{hp}" in rendered:
        hp = next((g for g in groups if g and g.isdigit()), "?")
        rendered = rendered.replace("{hp}", hp)
    if "{pct}" in rendered:
        pct = next((g for g in groups if g and g.isdigit()), "?")
        rendered = rendered.replace("{pct}", pct)
    if "{n}" in rendered:
        n = next((g for g in groups if g and g.isdigit()), "?")
        rendered = rendered.replace("{n}", n)
    if "{status}" in rendered:
        status = next(
            (g for g in groups if g and not g.isdigit() and g[0].isupper()),
            "status",
        )
        rendered = rendered.replace("{status}", status)
    return rendered


def _skill_text_chunks(skill: dict) -> list[str]:
    chunks: list[str] = []
    for bonus in skill.get("skill_bonuses", []):
        if bonus and "[[" not in bonus and "[[:Category:" not in bonus:
            chunks.append(bonus)
    for eff in skill.get("on_use_effects", []):
        chunks.append(eff)
    for coin in skill.get("coin_effects", []):
        raw = coin.get("effect", "")
        if raw:
            chunks.append(raw)
        cleaned = coin.get("cleaned_effect") or clean_effect_text(raw)
        if cleaned and cleaned != raw:
            chunks.append(cleaned)
    return chunks


def _is_notable_fallback(text: str) -> bool:
    return bool(_NOTABLE_MARKERS.search(text))


def extract_notable_effects(skill: dict, max_results: int = 4) -> list[str]:
    """
    Scan skill bonuses and coin effects against MECHANIC_SIGNALS.
    Returns human-readable advice lines for each signal that fires.
    """
    hits: list[str] = []
    seen_labels: set[str] = set()
    seen_text: set[str] = set()
    unmatched_notable: list[str] = []

    for chunk in _skill_text_chunks(skill):
        if not chunk.strip():
            continue

        matched_any = False
        for signal in MECHANIC_SIGNALS:
            if signal.label in seen_labels:
                continue
            m = signal.pattern.search(chunk)
            if m:
                advice = _render_advice(signal.advice, m)
                if advice not in seen_text:
                    hits.append(advice)
                    seen_text.add(advice)
                    seen_labels.add(signal.label)
                matched_any = True

        if not matched_any and _is_notable_fallback(chunk):
            cleaned = clean_effect_text(chunk)
            if not cleaned:
                continue
            # Skip long raw coin rows that were already partially captured by signals
            if len(cleaned) > 160:
                continue
            if cleaned not in seen_text:
                unmatched_notable.append(cleaned)

    if not hits:
        for fallback in unmatched_notable:
            if len(hits) >= max_results:
                break
            if fallback not in seen_text:
                hits.append(fallback)
                seen_text.add(fallback)
    elif len(hits) < max_results:
        for fallback in unmatched_notable:
            if len(hits) >= max_results:
                break
            if fallback not in seen_text and not any(fallback in h or h in fallback for h in hits):
                hits.append(fallback)
                seen_text.add(fallback)

    return hits[:max_results]


def top_fallback_coin_line(skill: dict) -> str | None:
    """Return the first cleaned non-trivial coin line when no signals fired."""
    for coin in skill.get("coin_effects", []):
        raw = coin.get("effect", "")
        cleaned = coin.get("cleaned_effect") or clean_effect_text(raw)
        if cleaned and _is_notable_fallback(raw):
            return cleaned
    return None
