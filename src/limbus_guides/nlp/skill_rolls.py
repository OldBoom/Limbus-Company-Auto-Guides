"""Estimate skill attack rolls from parsed skill stats."""

from __future__ import annotations

import re
from typing import Literal

_CP_VALUE = re.compile(r"([+-]?\d+)")
_DAMAGE_PLUS = re.compile(r"Damage\s*\+(\d+)", re.IGNORECASE)

_FINAL_PWR_SCALE = re.compile(
    r"Final Power\s+\+(\d+)\s+for every\s+(\d+)\s+([\w ]+?)\s+on target[^(]*\(max\s+(\d+)\)",
    re.IGNORECASE,
)
_STAT_SCALE_COUNT = re.compile(
    r"(Clash Power|Coin Power|Final Power|Base Power)\s+\+(\d+)\s+for every\s+(\d+)\s+"
    r"([\w ]+?)\s+(?:on target|Count)[^(]*\(max\s+(\d+)\)",
    re.IGNORECASE,
)
_PERCENT_PER_NEG = re.compile(
    r"[Dd]eal\s+\+(\d+)%\s+damage for every type of negative effect[^(]*\(max\s+(\d+)%\)",
    re.IGNORECASE,
)
_PERCENT_PER_COUNT = re.compile(
    r"[Dd]eal\s+\+(\d+)%\s+damage for every\s+([\w ]+?)(?:\s+on target)?[^(]*\(max\s+(\d+)%\)",
    re.IGNORECASE,
)
_PERCENT_FLAT = re.compile(
    r"(?:deal|Deal)\s+\+(\d+)%\s+damage(?!\s+for every)",
    re.IGNORECASE,
)
_PCT_DAMAGE = re.compile(r"\+(\d+)%\s+(?:damage|Damage)", re.IGNORECASE)
_AT_STAT_BONUS = re.compile(
    r"At\s+\d+\+[^,;]*?,?\s*(?:Coin Power|Clash Power|Final Power|Base Power)\s+\+(\d+)",
    re.IGNORECASE,
)
_IF_STAT_BONUS = re.compile(
    r"If[^,;]*?(?:Coin Power|Clash Power|Final Power|Base Power)\s+\+(\d+)",
    re.IGNORECASE,
)

RollKind = Literal["base", "stacked"]

TIER_BOUNDARIES = (0.10, 0.20, 0.40, 0.60, 0.80, 0.90)
TIER_NAMES = (
    "Extremely Low",
    "Low",
    "Slightly Low",
    "Average",
    "Slightly High",
    "High",
    "Extremely High",
)


def _parse_cp(coin_power: str | None) -> int:
    if not coin_power:
        return 0
    m = _CP_VALUE.search(coin_power.replace(" ", ""))
    return abs(int(m.group(1))) if m else 0


_REUSE_TAG = "[Reuse -"


def _coin_count(skill: dict) -> int:
    """Return the number of coin flips for this skill.

    In Limbus Company, Atk Weight is the number of *targets* hit — it is
    NOT the flip count.  The actual flip count equals the number of rows in
    the coin-effects table, excluding any rows that are purely a reuse
    continuation (i.e. whose effect contains '[Reuse -').
    """
    coins = skill.get("coin_effects", [])
    non_reuse = [c for c in coins if _REUSE_TAG not in c.get("effect", "")]
    max_nr = max((c["coin"] for c in non_reuse), default=0)
    return max_nr if max_nr > 0 else 1


def compute_coin_count(skill: dict) -> int:
    """Public alias for use outside this module (e.g. display in generation)."""
    return _coin_count(skill)


def _heads_damage_bonus_total(skill: dict) -> int:
    """Sum flat Damage +N across all coins that proc on hit/heads."""
    total = 0
    for coin in skill.get("coin_effects", []):
        eff = coin.get("effect", "")
        if not re.search(r"\[(?:Heads Hit|On Hit)\]", eff, re.I):
            continue
        for m in _DAMAGE_PLUS.finditer(eff):
            total += int(m.group(1))
    return total



def estimate_skill_rolls(skill: dict) -> dict[str, int | float] | None:
    """Estimate lowest / highest attack roll.

    Formula: low = BP (all Tails); high = BP + coins × CP (all Heads).
    Flat [Heads Hit] / [On Hit] Damage +N bonuses are added to high.

    These are **raw rolls** — they do not account for:
    - Offense vs Defense Level damage modifier (M = (Off−Def)/(|Off−Def|+25) × 100%)
    - Sin affinity resistances of the target
    - Sanity-based Heads probability (50 + SP %)

    Raw rolls are suitable for comparing identities with each other.  Actual
    in-game damage will be higher when Offense Level > enemy Defense Level and
    the attack's affinity hits a Fatal resistance.

    Returns None for non-attack skills (atk_weight == 0).
    """
    atk_weight = skill.get("atk_weight")
    if atk_weight == 0:
        return None

    bp = skill.get("base_power") or 0
    cp = _parse_cp(skill.get("coin_power"))
    n = _coin_count(skill)
    dmg_bonus = _heads_damage_bonus_total(skill)

    low_fp = bp
    high_fp = bp + n * cp
    high_dmg = dmg_bonus

    return {
        "low_total": low_fp,
        "high_total": high_fp + high_dmg,
        "coin_count": n,
        "base_power": bp,
        "coin_power": cp,
        "flat_damage": high_dmg,
    }


def estimate_boosted_high(skill: dict) -> int | None:
    """
    Upper damage ceiling with max conditional bonuses applied on top of high_total.
    Returns None for non-attack skills.
    """
    rolls = estimate_skill_rolls(skill)
    if rolls is None:
        return None

    bp = int(rolls["base_power"])
    cp = int(rolls["coin_power"])
    n = int(rolls["coin_count"])
    flat = int(rolls["flat_damage"])

    skill_blob = " ; ".join(skill.get("skill_bonuses", []) + skill.get("damage_scales", []))
    coin_blob = " ; ".join(
        coin.get("cleaned_effect", coin.get("effect", ""))
        for coin in skill.get("coin_effects", [])
    )

    fp_bonus = 0
    bp_bonus = 0
    cp_bonus = 0
    pct_bonus = 0

    for blob in (skill_blob, coin_blob):
        for m in _FINAL_PWR_SCALE.finditer(blob):
            fp_bonus = max(fp_bonus, int(m.group(4)))

        for m in _STAT_SCALE_COUNT.finditer(blob):
            stat, _per, _interval, _res, cap = m.groups()
            cap_i = int(cap)
            if stat.lower() == "coin power":
                cp_bonus = max(cp_bonus, cap_i)
            elif stat.lower() == "final power":
                fp_bonus = max(fp_bonus, cap_i)
            elif stat.lower() == "base power":
                bp_bonus = max(bp_bonus, cap_i)

        for m in _AT_STAT_BONUS.finditer(blob):
            cp_bonus = max(cp_bonus, int(m.group(1)))

        for m in _IF_STAT_BONUS.finditer(blob):
            cp_bonus = max(cp_bonus, int(m.group(1)))

        for m in _PERCENT_PER_NEG.finditer(blob):
            pct_bonus = max(pct_bonus, int(m.group(2)))

        for m in _PERCENT_PER_COUNT.finditer(blob):
            pct_bonus = max(pct_bonus, int(m.group(3)))

    for m in _PERCENT_FLAT.finditer(skill_blob):
        pct_bonus += int(m.group(1))

    for m in _PCT_DAMAGE.finditer(coin_blob):
        pct_bonus += int(m.group(1))

    high_fp = bp + bp_bonus + n * (cp + cp_bonus)
    total = high_fp + flat + fp_bonus
    if pct_bonus:
        total = int(total * (1 + pct_bonus / 100))
    return total


def _percentile(sorted_vals: list[int], p: float) -> float:
    if not sorted_vals:
        return 0.0
    if len(sorted_vals) == 1:
        return float(sorted_vals[0])
    idx = (len(sorted_vals) - 1) * p
    lo = int(idx)
    hi = min(lo + 1, len(sorted_vals) - 1)
    frac = idx - lo
    return sorted_vals[lo] * (1 - frac) + sorted_vals[hi] * frac


class RollNormalizer:
    """Roster-wide percentile tiers per skill slot (S1/S2/S3)."""

    def __init__(self, cutoffs: dict[tuple[int, RollKind], tuple[float, ...]]):
        self._cutoffs = cutoffs

    def tier_label(self, slot: int, value: int, kind: RollKind = "base") -> str:
        cuts = self._cutoffs.get((slot, kind))
        if not cuts:
            return "Average"
        p10, p20, p40, p60, p80, p90 = cuts
        if value <= p10:
            return TIER_NAMES[0]
        if value <= p20:
            return TIER_NAMES[1]
        if value <= p40:
            return TIER_NAMES[2]
        if value <= p60:
            return TIER_NAMES[3]
        if value <= p80:
            return TIER_NAMES[4]
        if value <= p90:
            return TIER_NAMES[5]
        return TIER_NAMES[6]


def build_roll_normalizer(roster: dict[str, dict]) -> RollNormalizer:
    """Collect per-slot base and stacked high rolls across the roster."""
    buckets: dict[tuple[int, RollKind], list[int]] = {}

    for identity in roster.values():
        for skill in identity.get("parsed_skills") or []:
            slot = skill.get("skill_num")
            if slot not in (1, 2, 3):
                continue
            rolls = estimate_skill_rolls(skill)
            if rolls is None:
                continue
            buckets.setdefault((slot, "base"), []).append(int(rolls["high_total"]))
            boosted = estimate_boosted_high(skill)
            if boosted is not None:
                buckets.setdefault((slot, "stacked"), []).append(boosted)

    cutoffs: dict[tuple[int, RollKind], tuple[float, ...]] = {}
    for key, vals in buckets.items():
        sorted_vals = sorted(vals)
        cutoffs[key] = tuple(_percentile(sorted_vals, p) for p in TIER_BOUNDARIES)
    return RollNormalizer(cutoffs)


def format_skill_rolls(skill: dict, normalizer: RollNormalizer | None = None) -> str:
    """Human-readable roll summary for guide text, optionally with roster tier labels."""
    rolls = estimate_skill_rolls(skill)
    if rolls is None:
        return "no attack roll (activation skill)"

    low = int(rolls["low_total"])
    high = int(rolls["high_total"])
    base = f"rolls — low {low}, high {high}"

    if normalizer is None:
        return base

    slot = skill.get("skill_num", 0)
    base_tier = normalizer.tier_label(slot, high, "base")
    boosted = estimate_boosted_high(skill)
    if boosted is None or boosted == high:
        return f"{base} ({base_tier})"

    stacked_tier = normalizer.tier_label(slot, boosted, "stacked")
    if base_tier == stacked_tier:
        return f"{base} ({base_tier})"
    return f"{base} ({base_tier} / {stacked_tier} stacked)"

