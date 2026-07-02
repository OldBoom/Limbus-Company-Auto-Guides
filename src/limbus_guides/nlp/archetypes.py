"""
Status-effect and mechanic archetypes for guide generation.

Mechanic summaries reference docs/status-effects.md and docs/domain-primer.md.
"""

from __future__ import annotations

import re
from typing import Any, Callable

from limbus_guides.nlp.synergy import extract_unique_tremor_types, format_unique_tremor_label

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

_ARCHETYPE_RESULT = dict[str, Any]


def _kit_blob(
    skills: list[dict],
    combat_text: str = "",
    raw_markdown: str = "",
) -> str:
    parts = [combat_text, raw_markdown]
    for skill in skills:
        parts.extend(skill.get("on_use_effects", []))
        parts.extend(skill.get("skill_bonuses", []))
        for coin in skill.get("coin_effects", []):
            parts.append(coin.get("effect", ""))
    return " ".join(parts)


def _prominence(profile: dict | None, label: str) -> int:
    profile = profile or {}
    primary = profile.get("primary_mechanics", [])
    if label in primary:
        return 200 - primary.index(label) * 10
    return int(profile.get("status_effects", {}).get(label, 0))


def _payoff_skill_name(skills: list[dict]) -> str:
    s3 = next((s for s in skills if s.get("skill_num") == 3), None)
    return s3["name"] if s3 else "S3"


def _threshold_values(text: str, status: str) -> list[int]:
    return [
        int(m.group(1))
        for m in re.finditer(rf"(\d+)\+\s+[^;]*{re.escape(status)}", text, re.I)
    ]


def _build_archetype(
    *,
    kind: str,
    status: str,
    setup_summary: str,
    tips: list[str],
    threshold: int | None = None,
    payoff_skill: str | None = None,
    extra: dict | None = None,
) -> _ARCHETYPE_RESULT:
    result: _ARCHETYPE_RESULT = {
        "kind": kind,
        "status": status,
        "setup_summary": setup_summary,
        "tips": tips[:4],
    }
    if threshold is not None:
        result["threshold"] = threshold
    if payoff_skill:
        result["payoff_skill"] = payoff_skill
    if extra:
        result.update(extra)
    return result


def _sin_archetype(
    status: str,
    *,
    kind: str,
    skills: list[dict],
    combat_text: str,
    raw_markdown: str,
    mechanic_profile: dict | None,
    min_prominence: int,
    stack_tip: str,
    payoff_tip: str,
    setup_summary: str,
    skip_if: Callable[[str], bool] | None = None,
    extra_signals: Callable[[str], int] | None = None,
    extra_tips: Callable[[str, list[dict]], list[str]] | None = None,
) -> _ARCHETYPE_RESULT | None:
    if skip_if and skip_if(_kit_blob(skills, combat_text, raw_markdown)):
        return None

    if _prominence(mechanic_profile, status) < min_prominence:
        return None

    blob = _kit_blob(skills, combat_text, raw_markdown)
    if not re.search(re.escape(status), blob, re.I):
        return None

    signals = 0
    if re.search(rf"Inflict[^;]*{status}", blob, re.I):
        signals += 2
    if re.search(rf"Gain[^;]*{status}", blob, re.I):
        signals += 1
    if re.search(rf"every \d+[^;]*{status}|{status}[^;]*\(max", blob, re.I):
        signals += 2
    thresholds = _threshold_values(blob, status)
    if thresholds:
        signals += 1
    if extra_signals:
        signals += extra_signals(blob)

    if signals < 2:
        return None

    tips = [stack_tip]
    if thresholds:
        th = min(thresholds)
        tips.append(payoff_tip.format(threshold=th, payoff=_payoff_skill_name(skills)))
    elif payoff_tip:
        tips.append(payoff_tip.format(threshold="?", payoff=_payoff_skill_name(skills)))

    if extra_tips:
        tips.extend(extra_tips(blob, skills))

    return _build_archetype(
        kind=kind,
        status=status,
        setup_summary=setup_summary.format(payoff=_payoff_skill_name(skills)),
        tips=tips,
        threshold=min(thresholds) if thresholds else None,
        payoff_skill=_payoff_skill_name(skills),
    )


# ---------------------------------------------------------------------------
# Seven sin-keywords
# ---------------------------------------------------------------------------


def find_burn_archetype(
    skills: list[dict],
    combat_text: str = "",
    raw_markdown: str = "",
    mechanic_profile: dict | None = None,
) -> _ARCHETYPE_RESULT | None:
    """Burn — Turn End Potency damage; stack Potency + Count on target."""
    return _sin_archetype(
        "Burn",
        kind="burn_stacker",
        skills=skills,
        combat_text=combat_text,
        raw_markdown=raw_markdown,
        mechanic_profile=mechanic_profile,
        min_prominence=6,
        stack_tip=(
            "**Burn** stacks on the target — each turn it deals **Turn End** damage "
            "equal to Burn Potency before Count ticks down."
        ),
        payoff_tip=(
            "Hold **{payoff}** until **{threshold}+ Burn** on the target unlocks "
            "the skill's bonus Coin Power or damage scaling."
        ),
        setup_summary=(
            "**Burn** specialist — apply Potency and Count with early skills, let ticks "
            "soften targets, then cash out with **{payoff}** at Burn thresholds."
        ),
    )


def find_bleed_archetype(
    skills: list[dict],
    combat_text: str = "",
    raw_markdown: str = "",
    mechanic_profile: dict | None = None,
    *,
    nails_archetype: dict | None = None,
) -> _ARCHETYPE_RESULT | None:
    """Bleed — damage on coin toss; stack Potency + Count on target."""
    if nails_archetype:
        return None
    blob = _kit_blob(skills, combat_text, raw_markdown)
    if re.search(r"\bNails\b", blob) and re.search(r"Inflict[^;]*Nails", blob, re.I):
        return None

    return _sin_archetype(
        "Bleed",
        kind="bleed_stacker",
        skills=skills,
        combat_text=combat_text,
        raw_markdown=raw_markdown,
        mechanic_profile=mechanic_profile,
        min_prominence=6,
        stack_tip=(
            "**Bleed** punishes aggression — each coin flip on a Bleeding target deals "
            "Potency damage and consumes Count."
        ),
        payoff_tip=(
            "Reach **{threshold}+ Bleed** before firing **{payoff}**; many skills add "
            "Coin Power or damage per Bleed stack on target."
        ),
        setup_summary=(
            "**Bleed** stacker — build Potency and Count on one target, then spike with "
            "**{payoff}** once threshold skills unlock full damage."
        ),
    )


def find_tremor_archetype(
    skills: list[dict],
    combat_text: str = "",
    raw_markdown: str = "",
    mechanic_profile: dict | None = None,
) -> _ARCHETYPE_RESULT | None:
    """Tremor — raises Stagger Threshold; Tremor Burst is the burst payoff."""
    unique = sorted(extract_unique_tremor_types(raw_markdown or combat_text))

    def extra_signals(blob: str) -> int:
        score = 0
        if re.search(r"Tremor Burst", blob, re.I):
            score += 2
        if unique:
            score += 1
        return score

    def extra_tips(blob: str, _skills: list[dict]) -> list[str]:
        tips: list[str] = []
        if re.search(r"Tremor Burst", blob, re.I):
            tips.append(
                "Trigger **Tremor Burst** on stagger setups — Burst raises Stagger Threshold "
                "by Tremor Potency before Count decays."
            )
        if unique:
            label = format_unique_tremor_label(unique[0])
            tips.append(
                f"Kit uses **{label}** — keep the same unique Tremor subtype on one target "
                f"for Amplitude Conversion and Burst payoffs."
            )
        return tips

    arch = _sin_archetype(
        "Tremor",
        kind="tremor_stacker",
        skills=skills,
        combat_text=combat_text,
        raw_markdown=raw_markdown,
        mechanic_profile=mechanic_profile,
        min_prominence=6,
        stack_tip=(
            "Layer **Tremor Potency and Count** on the main target — Tremor fuels "
            "stagger breaks and Burst triggers."
        ),
        payoff_tip=(
            "At **{threshold}+ Tremor**, commit **{payoff}** or Burst coins for maximum "
            "Stagger Threshold pressure."
        ),
        setup_summary=(
            "**Tremor** control — stack on one target, then break with **{payoff}** or "
            "**Tremor Burst** for Stagger Threshold spikes."
        ),
        extra_signals=extra_signals,
        extra_tips=extra_tips,
    )
    if arch and unique:
        arch["unique_subtypes"] = unique
    return arch


def find_rupture_archetype(
    skills: list[dict],
    combat_text: str = "",
    raw_markdown: str = "",
    mechanic_profile: dict | None = None,
) -> _ARCHETYPE_RESULT | None:
    """Rupture — hit-based damage; stack Potency + Count on target."""
    return _sin_archetype(
        "Rupture",
        kind="rupture_stacker",
        skills=skills,
        combat_text=combat_text,
        raw_markdown=raw_markdown,
        mechanic_profile=mechanic_profile,
        min_prominence=6,
        stack_tip=(
            "**Rupture** deals damage **when the target is hit** — stack Potency and Count "
            "before your heavy coins land."
        ),
        payoff_tip=(
            "Build to **{threshold}+ Rupture**, then unload **{payoff}** for amplified "
            "on-hit burst damage."
        ),
        setup_summary=(
            "**Rupture** burst kit — stack on a focus target, then cash out with "
            "**{payoff}** while Rupture Count is high."
        ),
    )


def find_sinking_archetype(
    skills: list[dict],
    combat_text: str = "",
    raw_markdown: str = "",
    mechanic_profile: dict | None = None,
) -> _ARCHETYPE_RESULT | None:
    """Sinking — SP damage on hit; stack Potency + Count on target."""
    return _sin_archetype(
        "Sinking",
        kind="sinking_stacker",
        skills=skills,
        combat_text=combat_text,
        raw_markdown=raw_markdown,
        mechanic_profile=mechanic_profile,
        min_prominence=6,
        stack_tip=(
            "**Sinking** drains SP when the target is hit — stack Potency and Count to "
            "push enemies toward negative SP breakpoints."
        ),
        payoff_tip=(
            "At **{threshold}+ Sinking**, **{payoff}** and follow-up coins deal bonus "
            "damage or SP-pressure payoffs."
        ),
        setup_summary=(
            "**Sinking** pressure — stack on one target to drain SP, then finish with "
            "**{payoff}** at Sinking thresholds."
        ),
    )


_POISE_TO_COINPWR = re.compile(
    r"Coin Power\s+\+(\d+)\s+for every\s+(\d+)\s+Poise Count[^(]*\(max\s+(\d+)\)",
    re.IGNORECASE,
)
_POISE_CRIT = re.compile(r"critical hit.*poise|poise.*critical", re.I)
_GAIN_POISE = re.compile(r"Gain[^;]*Poise", re.I)


def find_poise_archetype(
    skills: list[dict],
    combat_text: str = "",
    raw_markdown: str = "",
    mechanic_profile: dict | None = None,
) -> _ARCHETYPE_RESULT | None:
    """Poise — self buff; crit chance from Potency; stack Count on self."""
    if _prominence(mechanic_profile, "Poise") < 6:
        return None

    blob = _kit_blob(skills, combat_text, raw_markdown)
    if not re.search(r"Poise", blob, re.I):
        return None

    signals = 0
    if _GAIN_POISE.search(blob):
        signals += 2
    if _POISE_TO_COINPWR.search(blob):
        signals += 2
    if _POISE_CRIT.search(blob):
        signals += 1
    thresholds = _threshold_values(blob, "Poise")
    if thresholds:
        signals += 1

    if signals < 2:
        return None

    tips: list[str] = [
        "**Poise** on self raises crit chance per Potency — build Count with skills "
        "and clash wins before the finisher."
    ]
    pm = _POISE_TO_COINPWR.search(blob)
    if pm:
        tips.append(
            f"Combat or skills convert Poise to **+{pm.group(1)} Coin Power per "
            f"{pm.group(2)} Poise Count** (max +{pm.group(3)}) — clash to stack faster."
        )
    if thresholds:
        th = min(thresholds)
        tips.append(
            f"Reach **{th}+ Poise Count** before **{_payoff_skill_name(skills)}** — "
            f"crit damage and Coin Power spike at the threshold."
        )

    return _build_archetype(
        kind="poise_stacker",
        status="Poise",
        setup_summary=(
            "**Poise** fighter — stack Count on self for crits and Coin Power, then "
            f"commit **{_payoff_skill_name(skills)}** at Poise thresholds."
        ),
        tips=tips,
        threshold=min(thresholds) if thresholds else None,
        payoff_skill=_payoff_skill_name(skills),
    )


# ---------------------------------------------------------------------------
# Extra mechanics (user list + docs/status-effects.md)
# ---------------------------------------------------------------------------

_AGGRO_GAIN = re.compile(r"Gain\s+\+?(\d+)\s+Aggro", re.I)
_AGGRO_SLOT = re.compile(r"Aggro to (?:this Skill Slot|the leftmost Slot)", re.I)


def find_aggro_archetype(
    skills: list[dict],
    combat_text: str = "",
    raw_markdown: str = "",
    mechanic_profile: dict | None = None,
) -> _ARCHETYPE_RESULT | None:
    """Aggro — draw enemy focus to this unit or a skill slot."""
    blob = _kit_blob(skills, combat_text, raw_markdown)
    gains = [int(m.group(1)) for m in _AGGRO_GAIN.finditer(blob)]
    if not gains and not _AGGRO_SLOT.search(blob):
        return None

    max_aggro = max(gains) if gains else 3
    tank_signals = sum(
        1
        for kw in ("assist defense", "nullify that damage", "cannot drop below 1", "shield")
        if kw in blob.lower()
    )

    tips = [
        f"Skills grant up to **+{max_aggro} Aggro** — enemies focus this slot, letting "
        f"teammates attack safely."
    ]
    if tank_signals:
        tips.append(
            "Pair **Aggro** with Guard/Assist Defense — you're meant to be hit while "
            "buffs and passives trigger."
        )

    return _build_archetype(
        kind="aggro_tank",
        status="Aggro",
        setup_summary=(
            "**Aggro** frontliner — raise Aggro on key skill slots to pull enemy focus "
            "while the kit tanks or sets up."
        ),
        tips=tips,
    )


_HASTE_GAIN = re.compile(r"Gain[^;]*\bHaste\b", re.I)


def find_haste_archetype(
    skills: list[dict],
    combat_text: str = "",
    raw_markdown: str = "",
    mechanic_profile: dict | None = None,
) -> _ARCHETYPE_RESULT | None:
    """Haste — +Speed for one turn; acts earlier next round."""
    blob = _kit_blob(skills, combat_text, raw_markdown)
    if len(_HASTE_GAIN.findall(blob)) < 1 and "Haste" not in blob:
        return None
    if _prominence(mechanic_profile, "Haste") < 1 and len(_HASTE_GAIN.findall(blob)) < 2:
        return None

    return _build_archetype(
        kind="haste_tempo",
        status="Haste",
        setup_summary=(
            "**Haste** tempo — gain Speed for the next turn to act earlier and secure "
            "clashes or support triggers."
        ),
        tips=[
            "**Haste** adds Speed for one turn — chain skills that grant it before your "
            "carry line or evade sequences.",
            "Higher Speed helps win clashes and can gate bonus damage on speed-check kits.",
        ],
    )


_PARALYZE_INFLICT = re.compile(r"Inflict[^;]*Paralyze", re.I)


def find_paralyze_archetype(
    skills: list[dict],
    combat_text: str = "",
    raw_markdown: str = "",
    mechanic_profile: dict | None = None,
) -> _ARCHETYPE_RESULT | None:
    """Paralyze — fix target coin Power to 0 for one turn."""
    blob = _kit_blob(skills, combat_text, raw_markdown)
    inflicts = len(_PARALYZE_INFLICT.findall(blob))
    if inflicts < 1:
        return None

    return _build_archetype(
        kind="paralyze_control",
        status="Paralyze",
        setup_summary=(
            "**Paralyze** control — inflict Paralyze to shut down enemy coin Power, "
            "then follow with high-impact coins while they cannot clash back."
        ),
        tips=[
            "Land **Paralyze** before the enemy's big skill — affected coins flip at **0 Power**.",
            "Stack Paralyze on priority targets right before your **S3** or Unbreakable coins.",
        ],
    )


_FRAGILE_INFLICT = re.compile(r"Inflict[^;]*Fragil", re.I)


def find_fragile_archetype(
    skills: list[dict],
    combat_text: str = "",
    raw_markdown: str = "",
    mechanic_profile: dict | None = None,
) -> _ARCHETYPE_RESULT | None:
    """Fragile / Fragility — target takes +10% skill damage per Count (max 10)."""
    blob = _kit_blob(skills, combat_text, raw_markdown)
    if not _FRAGILE_INFLICT.search(blob):
        return None

    return _build_archetype(
        kind="fragile_setup",
        status="Fragile",
        setup_summary=(
            "**Fragile** setup — apply Fragile or typed Fragility debuffs so the team "
            "deals amplified skill damage on the following turn."
        ),
        tips=[
            "Apply **Fragile** (or Slash/Pierce/Blunt Fragility) before burst turns — "
            "each Count adds **+10% damage taken** from skills (max 10).",
            "Coordinate with teammates: debuff first, then heavy coins while Fragile is active.",
        ],
    )


_DISCARD_RE = re.compile(r"\bDiscard(?:ing)?\b", re.I)
_INSIGHT_RE = re.compile(r"\bInsight\b", re.I)
_ERUDITION_RE = re.compile(r"\bErudition\b", re.I)


def find_discard_archetype(
    skills: list[dict],
    combat_text: str = "",
    raw_markdown: str = "",
    mechanic_profile: dict | None = None,
) -> _ARCHETYPE_RESULT | None:
    """Discard — Dieci resource; discarding skills fuels Insight / Erudition payoffs."""
    blob = _kit_blob(skills, combat_text, raw_markdown)
    if not _DISCARD_RE.search(blob):
        return None

    tips = [
        "**Discard** is a resource loop — remove skills from hand rotation to fuel "
        "Insight, Erudition, or shield payoffs.",
    ]
    if _ERUDITION_RE.search(blob):
        tips.append(
            "**Erudition** stacks when you Discard — each discard can grant Shield or "
            "other defensive spikes (max 6 Erudition)."
        )
    if _INSIGHT_RE.search(blob):
        tips.append(
            "**Insight** pairs with Discard — plan which skills to cycle out before "
            "committing the empowered turn."
        )

    return _build_archetype(
        kind="discard_resource",
        status="Discard",
        setup_summary=(
            "**Discard** specialist — cycle skills intentionally to build Insight/Erudition, "
            "then cash out with the powered skill line."
        ),
        tips=tips,
    )


# ---------------------------------------------------------------------------
# Registry (for generation / tests)
# ---------------------------------------------------------------------------

SIN_KEYWORD_ARCHETYPE_KEYS: tuple[str, ...] = (
    "burn_archetype",
    "bleed_archetype",
    "tremor_archetype",
    "rupture_archetype",
    "sinking_archetype",
    "poise_archetype",
)

EXTRA_ARCHETYPE_KEYS: tuple[str, ...] = (
    "aggro_archetype",
    "haste_archetype",
    "paralyze_archetype",
    "fragile_archetype",
    "discard_archetype",
)

SPECIAL_ARCHETYPE_KEYS: tuple[str, ...] = (
    "charge_archetype",
    "nails_archetype",
)

OVERVIEW_ARCHETYPE_KEYS: tuple[str, ...] = (
    "nails_archetype",
    "charge_archetype",
    *SIN_KEYWORD_ARCHETYPE_KEYS,
    *EXTRA_ARCHETYPE_KEYS,
)


def detect_status_archetypes(
    skills: list[dict],
    combat_text: str = "",
    raw_markdown: str = "",
    mechanic_profile: dict | None = None,
    *,
    nails_archetype: dict | None = None,
) -> dict[str, _ARCHETYPE_RESULT]:
    """Run all sin-keyword and extra mechanic detectors."""
    common = {
        "skills": skills,
        "combat_text": combat_text,
        "raw_markdown": raw_markdown,
        "mechanic_profile": mechanic_profile,
    }
    out: dict[str, _ARCHETYPE_RESULT] = {}

    mapping: list[tuple[str, Callable[..., _ARCHETYPE_RESULT | None], dict]] = [
        ("burn_archetype", find_burn_archetype, {}),
        ("bleed_archetype", find_bleed_archetype, {"nails_archetype": nails_archetype}),
        ("tremor_archetype", find_tremor_archetype, {}),
        ("rupture_archetype", find_rupture_archetype, {}),
        ("sinking_archetype", find_sinking_archetype, {}),
        ("poise_archetype", find_poise_archetype, {}),
        ("aggro_archetype", find_aggro_archetype, {}),
        ("haste_archetype", find_haste_archetype, {}),
        ("paralyze_archetype", find_paralyze_archetype, {}),
        ("fragile_archetype", find_fragile_archetype, {}),
        ("discard_archetype", find_discard_archetype, {}),
    ]
    for key, fn, extra in mapping:
        arch = fn(**common, **extra)
        if arch:
            out[key] = arch
    return out


def pick_primary_sin_archetype(gp: dict) -> _ARCHETYPE_RESULT | None:
    """Best sin-keyword archetype for core-idea narrative (matches primary mechanic order)."""
    for special in ("nails_archetype", "charge_archetype"):
        if gp.get(special):
            return gp[special]

    primary = gp.get("primary_mechanics") or []
    ordered_keys = [
        ("Burn", "burn_archetype"),
        ("Bleed", "bleed_archetype"),
        ("Tremor", "tremor_archetype"),
        ("Rupture", "rupture_archetype"),
        ("Sinking", "sinking_archetype"),
        ("Poise", "poise_archetype"),
        ("Charge", "charge_archetype"),
    ]
    for label, key in ordered_keys:
        if label in primary and gp.get(key):
            return gp[key]

    for _label, key in ordered_keys:
        if gp.get(key):
            return gp[key]
    return None


def pick_extra_archetype(gp: dict) -> _ARCHETYPE_RESULT | None:
    for key in EXTRA_ARCHETYPE_KEYS:
        if gp.get(key):
            return gp[key]
    return None
