"""
Status-effect and mechanic archetypes for guide generation.

Mechanic summaries reference docs/status-effects.md and docs/domain-primer.md.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
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


# Unique Tremor subtype blurbs (docs/status-effects.md) — kit-specific, not generic primers.
_UNIQUE_TREMOR_BLURBS: dict[str, str] = {
    "Decay": (
        "**Tremor — Decay** — Burst strips enemy **Defense Level** "
        "(1 per 4 Tremor Potency on target)."
    ),
    "Fracture": (
        "**Tremor — Fracture** — at **20+** combined Tremor Potency and Count, "
        "raises enemy **Stagger Level**."
    ),
    "Reverb": (
        "**Tremor — Reverb** — Burst deals **Sloth** damage equal to Tremor Potency."
    ),
    "Everlasting": (
        "**Tremor — Everlasting** — Burst can proc **additional Bursts** "
        "(Potency/Count % chance, each capped at 50%)."
    ),
    "Chain": (
        "**Tremor — Chain** — enemy loses **Clash Power** at high Tremor Potency on target."
    ),
    "Scorch": (
        "**Tremor — Scorch** — Burst deals **Wrath** damage from Tremor and Burn Potency; "
        "consumes **Burn Count**."
    ),
    "Hemorrhage": (
        "**Tremor — Hemorrhage** — Burst deals **Lust** damage from Tremor and Bleed Potency; "
        "consumes **Bleed Count**."
    ),
    "Superposition": (
        "**Tremor — Superposition** — stacks multiple Tremor types via "
        "**Amplitude Entanglement**."
    ),
}


def _sin_kit_signals(blob: str, status: str) -> int:
    signals = 0
    if re.search(rf"Inflict[^;]*{status}", blob, re.I):
        signals += 2
    if re.search(rf"Gain[^;]*{status}", blob, re.I):
        signals += 1
    if re.search(rf"every \d+[^;]*{status}|{status}[^;]*\(max", blob, re.I):
        signals += 2
    if _gate_thresholds(blob, status):
        signals += 1
    return signals


def describe_unique_tremor(subtype: str) -> str | None:
    return _UNIQUE_TREMOR_BLURBS.get(subtype.title())


def _gate_thresholds(text: str, status: str) -> list[int]:
    """Hard If/At N+ status checks on skills — not inflict amounts or per-stack rates."""
    status_re = re.escape(status)
    values: list[int] = []
    for m in re.finditer(
        rf"(?:if target has|at)\s+(\d+)\+\s+[^;|]*{status_re}",
        text,
        re.I,
    ):
        values.append(int(m.group(1)))
    for m in re.finditer(
        rf"(\d+)\+\s+{status_re}[^;]*(?:coin power|clash power|deal\s+\+|damage)",
        text,
        re.I,
    ):
        values.append(int(m.group(1)))
    return sorted(set(values))


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
    maintain_tip: str | None = None,
    setup_summary: str,
    gate_tip: str = "Skills check **{threshold}+ {status}** — favour those coins when stacked.",
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
    gates = _gate_thresholds(blob, status)
    if gates:
        signals += 1
    if extra_signals:
        signals += extra_signals(blob)

    if signals < 2:
        return None

    tips: list[str] = []
    if maintain_tip:
        tips.append(maintain_tip)
    if gates:
        tips.append(gate_tip.format(threshold=min(gates), status=status))

    if extra_tips:
        tips.extend(extra_tips(blob, skills))

    return _build_archetype(
        kind=kind,
        status=status,
        setup_summary=setup_summary,
        tips=tips,
        threshold=min(gates) if gates else None,
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
        setup_summary="**Burn** applicator.",
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
        setup_summary="**Bleed** focus.",
    )


def find_tremor_archetype(
    skills: list[dict],
    combat_text: str = "",
    raw_markdown: str = "",
    mechanic_profile: dict | None = None,
) -> _ARCHETYPE_RESULT | None:
    """Tremor — raises Stagger Threshold; early stagger is the payoff."""
    if _prominence(mechanic_profile, "Tremor") < 6:
        return None

    blob = _kit_blob(skills, combat_text, raw_markdown)
    if not re.search(r"Tremor", blob, re.I):
        return None

    unique = sorted(extract_unique_tremor_types(raw_markdown or combat_text))
    signals = _sin_kit_signals(blob, "Tremor")
    if re.search(r"Tremor Burst", blob, re.I):
        signals += 2
    if unique:
        signals += 1
    if re.search(r"Time Moratorium", blob, re.I):
        signals += 1

    if signals < 2:
        return None

    tips: list[str] = []
    for subtype in unique[:2]:
        blurb = describe_unique_tremor(subtype)
        if blurb:
            tips.append(blurb)
    if re.search(r"Time Moratorium", blob, re.I):
        tips.append(
            "**Time Moratorium** — time the stored-damage pop with your Tremor stacks."
        )
    elif re.search(r"Tremor Burst", blob, re.I) and not tips:
        tips.append("**Burst** when you're ready to break the stagger target.")

    if unique:
        label = format_unique_tremor_label(unique[0])
        setup_summary = f"**Tremor** control ({label})."
    else:
        setup_summary = "**Tremor** control — stack for early stagger breaks."

    arch = _build_archetype(
        kind="tremor_stacker",
        status="Tremor",
        setup_summary=setup_summary,
        tips=tips,
        payoff_skill=_payoff_skill_name(skills),
    )
    if unique:
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
        setup_summary="**Rupture** focus.",
    )


def find_sinking_archetype(
    skills: list[dict],
    combat_text: str = "",
    raw_markdown: str = "",
    mechanic_profile: dict | None = None,
) -> _ARCHETYPE_RESULT | None:
    """Sinking — SP drain on hit softens clashes; no separate burst window."""
    if _prominence(mechanic_profile, "Sinking") < 6:
        return None

    blob = _kit_blob(skills, combat_text, raw_markdown)
    if not re.search(r"Sinking", blob, re.I):
        return None

    if _sin_kit_signals(blob, "Sinking") < 2:
        return None

    return _build_archetype(
        kind="sinking_stacker",
        status="Sinking",
        setup_summary="**Sinking** clash-support.",
        tips=[],
        payoff_skill=_payoff_skill_name(skills),
    )


_POISE_TO_COINPWR = re.compile(
    r"Coin Power\s+\+(\d+)\s+for every\s+(\d+)\s+Poise Count[^(]*\(max\s+(\d+)\)",
    re.IGNORECASE,
)
_POISE_CRIT = re.compile(r"critical hit.*poise|poise.*critical", re.I)
_GAIN_POISE = re.compile(r"Gain[^;]*Poise", re.I)
_CLAUSE_TAG = re.compile(r"^\[([^\]]+)\]\s*")
_CONSUME_STATUS = re.compile(r"consume[^;]*(?:poise|charge)", re.I)

_GAIN_POISE_COUNT = re.compile(
    r"Gain\s+\+?(\d+)\s+Poise\s+Count(?:\s+next turn)?",
    re.I,
)
_GAIN_POISE_POTENCY = re.compile(
    r"Gain\s+(\d+)\s+Poise(?:\s+next turn)?(?!\s+Count)",
    re.I,
)
_GAIN_CHARGE_COUNT = re.compile(
    r"Gain\s+\+?(\d+)\s+Charge\s+Count",
    re.I,
)
_GAIN_POISE_VARIABLE = re.compile(
    r"gain\s+Poise\s+equal\s+to\s+([^;(]+)",
    re.I,
)


@dataclass
class _StackGain:
    label: str
    trigger: str
    amount: int
    kind: str  # "Count" or "Potency"
    note: str = ""


def _gain_context_is_ally(clause: str, match: re.Match[str]) -> bool:
    start = max(0, match.start() - 50)
    end = min(len(clause), match.end() + 60)
    window = clause[start:end]
    lower = window.lower()
    if "on self" in lower or "this unit" in lower:
        return False
    if not re.search(r"\ball(?:y|ies)\b", window, re.I):
        return False
    if re.search(r"random ally|said ally", window, re.I):
        return True
    return bool(
        re.search(r"\ball(?:y|ies)\b.*\bgain\b", window, re.I)
        or re.search(r"\bgain\b.*\ball(?:y|ies)\b", window, re.I)
        or re.search(r"\bapply\b[^;]*\ball(?:y|ies)\b", window, re.I)
    )


def _trigger_at_pos(clause: str, pos: int) -> str:
    """Best-effort trigger label around a gain effect."""
    local = clause[:pos]
    tags = list(_CLAUSE_TAG.finditer(local))
    if tags:
        return tags[-1].group(1).strip()
    for name in (
        "Combat Start",
        "Turn Start",
        "Turn End",
        "Attack End",
        "Skill End",
        "On Clash Win",
        "On Evade",
        "Clash Win",
        "Heads Hit",
        "On Hit",
        "On Use",
    ):
        if re.search(rf"(?:{re.escape(name)}\s*:)\s*$", local, re.I):
            return name
        if re.search(rf"\[{re.escape(name)}\]\s*$", local, re.I):
            return name
    tail = clause[pos : pos + 100]
    for name in ("Attack End", "Turn End", "Combat Start"):
        if re.search(rf"\bat {re.escape(name)}\b", tail, re.I):
            return name
    if re.search(r"\bnext turn\b", tail, re.I):
        return "next turn"
    return "On Use"


def _scan_clauses_for_gains(
    clauses: list[str],
    *,
    label: str,
    status: str,
) -> list[_StackGain]:
    gains: list[_StackGain] = []
    count_re = _GAIN_POISE_COUNT if status == "Poise" else _GAIN_CHARGE_COUNT
    variable_re = _GAIN_POISE_VARIABLE if status == "Poise" else None
    for clause in clauses:
        clause = re.sub(r"\n+---.*$", "", clause, flags=re.S).strip()
        if not clause:
            continue
        if _CONSUME_STATUS.search(clause):
            continue
        has_gain = count_re.search(clause) or (
            variable_re.search(clause) if variable_re else False
        ) or (
            status == "Poise" and _GAIN_POISE_POTENCY.search(clause)
        )
        if not has_gain:
            continue
        for m in count_re.finditer(clause):
            if _gain_context_is_ally(clause, m):
                continue
            gains.append(
                _StackGain(label, _trigger_at_pos(clause, m.start()), int(m.group(1)), "Count")
            )
        if status == "Poise":
            for m in _GAIN_POISE_POTENCY.finditer(clause):
                if _gain_context_is_ally(clause, m):
                    continue
                gains.append(
                    _StackGain(
                        label, _trigger_at_pos(clause, m.start()), int(m.group(1)), "Potency"
                    )
                )
            vm = _GAIN_POISE_VARIABLE.search(clause)
            if vm and not _gain_context_is_ally(clause, vm):
                source = vm.group(1).strip()
                gains.append(
                    _StackGain(
                        label,
                        _trigger_at_pos(clause, vm.start()),
                        0,
                        "Potency",
                        note=f"equal to {source}",
                    )
                )
    return gains


def _extract_stack_gains(
    skills: list[dict],
    combat_text: str = "",
    *,
    status: str,
    support_text: str = "",
) -> list[_StackGain]:
    """Kit-specific Poise / Charge gain lines from skills and passives."""
    gains: list[_StackGain] = []

    for skill in skills:
        sn = skill.get("skill_num")
        name = skill.get("name") or f"Skill {sn}"
        label = f"**S{sn} — {name}**" if sn else f"**{name}**"
        clauses: list[str] = []
        for field_name in ("on_use_effects", "skill_bonuses"):
            for line in skill.get(field_name, []):
                clauses.extend(_split_clauses(line))
        for coin in skill.get("coin_effects", []):
            clauses.extend(_split_clauses(coin.get("effect", "")))
        gains.extend(_scan_clauses_for_gains(clauses, label=label, status=status))

    for passive_blob in (combat_text, support_text):
        for part in re.split(r"###\s+", passive_blob):
            part = part.strip()
            if not part:
                continue
            lines = part.split("\n", 1)
            passive_name = lines[0].strip().strip("#").strip()
            body = lines[1] if len(lines) > 1 else ""
            if not body.strip():
                continue
            label = f"**{passive_name}**"
            passive_gains = _scan_clauses_for_gains(
                _split_clauses(body), label=label, status=status
            )
            gains.extend(passive_gains)

    return gains


def _format_gain_fragment(gain: _StackGain, *, status: str) -> str:
    if gain.note:
        trig = gain.trigger
        if trig.lower() in ("on use", "combat start", "turn end", "attack end"):
            return f"**Poise** {gain.note} at **{trig}**"
        return f"**Poise** {gain.note} on **{trig}**"
    unit = "Poise Count" if gain.kind == "Count" and status == "Poise" else (
        "Charge Count" if gain.kind == "Count" else "Poise"
    )
    trigger = gain.trigger
    if trigger.lower() in ("on use", "combat start", "turn end", "attack end", "next turn"):
        trigger = f"at **{trigger}**"
    elif trigger.lower() == "clash win":
        trigger = "on **Clash Win**"
    elif trigger.lower() == "on hit":
        trigger = "per **On Hit** coin"
    elif trigger.lower() == "heads hit":
        trigger = "per **Heads Hit** coin"
    else:
        trigger = f"on **{trigger}**"
    return f"**+{gain.amount} {unit}** {trigger}"


def _group_gain_fragments(gains: list[_StackGain], *, status: str) -> dict[str, list[str]]:
    grouped: dict[str, list[str]] = {}
    seen: set[tuple[str, str, int, str, str]] = set()
    for gain in gains:
        key = (gain.label, gain.trigger, gain.amount, gain.kind, gain.note)
        if key in seen:
            continue
        seen.add(key)
        grouped.setdefault(gain.label, []).append(_format_gain_fragment(gain, status=status))
    return grouped


def build_stack_ramp_tips(
    skills: list[dict],
    combat_text: str = "",
    *,
    status: str,
    payoff_label: str | None = None,
    support_text: str = "",
) -> list[str]:
    """
    Rotation tips describing how this kit actually gains Poise or Charge stacks,
    instead of generic 'ramp to 20' primers.
    """
    gains = _extract_stack_gains(
        skills, combat_text, status=status, support_text=support_text
    )
    if not gains:
        return []

    grouped = _group_gain_fragments(gains, status=status)
    payoff_key = None
    if payoff_label:
        for label in grouped:
            if payoff_label in label:
                payoff_key = label
                break

    ramp_labels = [
        label
        for label in grouped
        if label != payoff_key or len(grouped) == 1
    ]
    # Prefer skills that only build (drop payoff if other ramp sources exist).
    if payoff_key and len(ramp_labels) > 1:
        ramp_labels = [label for label in ramp_labels if label != payoff_key]

    def _total_amount(label: str) -> int:
        return sum(
            g.amount for g in gains if g.label == label and g.kind == "Count"
        ) or sum(g.amount for g in gains if g.label == label)

    ramp_labels.sort(key=_total_amount, reverse=True)
    ramp_labels = ramp_labels[:2]

    source_bits: list[str] = []
    for label in ramp_labels:
        frags = grouped[label]
        if len(frags) == 1:
            source_bits.append(f"{label} adds {frags[0]}")
        else:
            source_bits.append(f"{label} adds {frags[0]} and {frags[1]}")

    if not source_bits:
        return []

    payoff_ref = ""
    if payoff_label and payoff_key:
        payoff_ref = f" before committing **{payoff_label}**"
    elif payoff_label:
        payoff_ref = f" before **{payoff_label}**"

    if status == "Poise":
        has_potency = any(g.kind == "Potency" for g in gains)
        has_count = any(g.kind == "Count" for g in gains)
        goal = (
            "enough **Poise Potency** for reliable crits"
            if has_potency
            else "enough **Poise Count** for your scaling passives"
        )
        if has_potency and has_count:
            goal = "**Poise Count** and **Potency** for crits and Coin Power scaling"

        tip = (
            f"Build {goal}{payoff_ref} — {'; '.join(source_bits)}."
        )
        tips = [tip]
        if payoff_label and payoff_key and payoff_key not in ramp_labels:
            tips.append(
                f"**{payoff_label}** is your highest-damage skill — use the setup "
                f"skills above first, then commit it once stacks are up."
            )
        return tips[:2]

    # Charge
    tip = (
        f"Ramp **Charge Count** toward **20**{payoff_ref} — {'; '.join(source_bits)}."
    )
    return [tip]


def find_poise_archetype(
    skills: list[dict],
    combat_text: str = "",
    raw_markdown: str = "",
    mechanic_profile: dict | None = None,
    support_text: str = "",
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
    if signals < 2:
        return None

    payoff = _payoff_skill_name(skills)
    tips = build_stack_ramp_tips(
        skills,
        combat_text,
        status="Poise",
        payoff_label=payoff,
        support_text=support_text,
    )
    if not tips:
        tips = [
            "Use your setup skills and win clashes first — this kit only pays off "
            "once **Poise** stacks are on self."
        ]
    pm = _POISE_TO_COINPWR.search(blob)
    if pm:
        tips.append(
            f"**+{pm.group(1)} Coin Power per {pm.group(2)} Poise Count** "
            f"(max +{pm.group(3)}) — the Count you built converts straight into damage."
        )

    return _build_archetype(
        kind="poise_stacker",
        status="Poise",
        setup_summary="**Poise** fighter — stack on self, then spend on crits and scaling.",
        tips=tips,
        payoff_skill=payoff,
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
        f"Front-load **+{max_aggro} Aggro** on the slot you want enemies to target."
    ]
    if tank_signals:
        tips.append(
            "Pair high-Aggro turns with Guard or Assist Defense so passives trigger under pressure."
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
_SPEED_CHECK = re.compile(r"Speed is faster than the target", re.I)
_ON_EVADE_HASTE = re.compile(r"\[On Evade\][^;]*Gain[^;]*Haste", re.I)
_ON_USE_HASTE = re.compile(r"\[On Use\][^;]*Gain[^;]*Haste", re.I)


def _haste_play_tip(
    blob: str,
    raw_markdown: str = "",
    defense_archetype: dict | None = None,
) -> str:
    if _SPEED_CHECK.search(blob):
        return (
            "**Haste** raises Speed for next turn — several bonuses here require "
            "being faster than the target."
        )

    if _ON_EVADE_HASTE.search(blob):
        return (
            "**Haste** triggers on **Evade** — Evade when you want the Speed spike next turn."
        )

    def_arch = defense_archetype or {}
    defense_name = def_arch.get("defense_name", "")
    def_kind = def_arch.get("kind", "")

    if def_kind == "snipe_setup" or (
        defense_name and re.search(r"\bEvade\b", defense_name, re.I)
    ):
        return "**Haste** before **Evade** when you need higher Speed on the setup turn."

    if defense_name and re.search(r"\bGuard\b", defense_name, re.I):
        return (
            "Use **Haste** on attack turns — **Guard** covers defense; "
            "this is not an Evade rotation."
        )

    if re.search(r"^### Evade:", raw_markdown, re.MULTILINE | re.IGNORECASE):
        return "**Haste** before **Evade** when you need higher Speed on the setup turn."

    if re.search(r"^### Guard:", raw_markdown, re.MULTILINE | re.IGNORECASE):
        return (
            "Use **Haste** on attack turns — **Guard** covers defense; "
            "this is not an Evade rotation."
        )

    if _ON_USE_HASTE.search(blob):
        return (
            "Skills grant **Haste** next turn — use them when you want to act "
            "earlier on the following round."
        )

    return "Skills grant **Haste** — chain them when you need higher Speed next turn."


def find_haste_archetype(
    skills: list[dict],
    combat_text: str = "",
    raw_markdown: str = "",
    mechanic_profile: dict | None = None,
    *,
    defense_archetype: dict | None = None,
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
        setup_summary="**Haste** tempo on key skills.",
        tips=[
            _haste_play_tip(blob, raw_markdown, defense_archetype),
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
            "Land Paralyze immediately before the enemy's high-value skill or your moment of weakness.",
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
            "Apply Fragile or typed Fragility on the setup turn; coordinate team burst on the next turn.",
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

    tips: list[str] = []
    if _ERUDITION_RE.search(blob):
        tips.append(
            "Discard into **Erudition** for Shield spikes, then use the powered skill line."
        )
    if _INSIGHT_RE.search(blob):
        tips.append(
            "Discard to build **Insight**, then fire the powered skill set."
        )
    if not tips:
        tips.append("Plan which skills to Discard before the payoff turn.")

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
# Ally SP / HP regeneration
# ---------------------------------------------------------------------------

_ALLY_HEAL_MARKER = re.compile(
    r"(?:\d+\s+)?other\s+all(?:y|ies)|"
    r"\d+\s+all(?:y|ies)|"
    r"all\s+other\s+allies|"
    r"for\s+(?:the\s+)?all(?:y|ies)|"
    r"for\s+\d+\s+other\s+ally|"
    r"all(?:y|ies)\s+that|"
    r"all(?:y|ies)\s+with|"
    r"lowest\s+SP|"
    r"least\s+SP|"
    r"lowest\s+HP|"
    r"HP\s+percentage|"
    r"highest\s+max\s+HP|"
    r"said\s+all(?:y|ies)|"
    r"another\s+ally",
    re.I,
)

_SELF_HEAL_ONLY = re.compile(r"\bon self\b|\bthis unit\b", re.I)
_LIFESTEAL_HP = re.compile(r"heal\s+\d+%\s+of\s+the\s+HP\s+damage", re.I)


def _regen_clauses(
    skills: list[dict],
    combat_text: str = "",
    support_text: str = "",
) -> list[str]:
    """Semicolon-sized snippets from passives and skills — avoids cross-section false joins."""
    clauses: list[str] = []
    for source in (combat_text, support_text):
        if source.strip():
            clauses.extend(_split_clauses(source))
    for skill in skills:
        for field in ("on_use_effects", "skill_bonuses"):
            for line in skill.get(field, []):
                clauses.extend(_split_clauses(line))
        for coin in skill.get("coin_effects", []):
            clauses.extend(_split_clauses(coin.get("effect", "")))
    return clauses


def _split_clauses(blob: str) -> list[str]:
    return [part.strip() for part in re.split(r"\s*;\s*", blob) if part.strip()]


def _clause_heals_ally_sp(clause: str) -> bool:
    if not re.search(r"heal", clause, re.I) or not re.search(r"\bSP\b", clause):
        return False
    if _SELF_HEAL_ONLY.search(clause) and not _ALLY_HEAL_MARKER.search(clause):
        return False
    if _ALLY_HEAL_MARKER.search(clause):
        return True
    if re.search(r"Heal\s+\d+\s+all(?:y|ies)", clause, re.I):
        return True
    if re.search(
        r"all(?:y|ies)[^;]{0,120}heal(?:s)?\s+(?:\([^)]+\)\s*)?\d+(?:~\d+)?\s*SP",
        clause,
        re.I,
    ):
        return True
    return False


def _clause_heals_ally_hp(clause: str) -> bool:
    if not re.search(r"heal", clause, re.I):
        return False
    if _LIFESTEAL_HP.search(clause) and not _ALLY_HEAL_MARKER.search(clause):
        return False
    if _SELF_HEAL_ONLY.search(clause) and not _ALLY_HEAL_MARKER.search(clause):
        return False
    if not re.search(r"\d+\s*HP|HP\s+percentage|lowest\s+HP", clause, re.I):
        return False
    if _ALLY_HEAL_MARKER.search(clause):
        return True
    if re.search(
        r"all(?:y|ies)[^;]{0,120}heal(?:s)?\s+(?:\([^)]+\)\s*)?\d+(?:~\d+)?\s*HP",
        clause,
        re.I,
    ):
        return True
    if re.search(r"heal\s+\d+\s+all(?:y|ies)", clause, re.I):
        return True
    return False


def _ally_heal_clauses(
    skills: list[dict],
    combat_text: str = "",
    support_text: str = "",
    resource: str = "SP",
) -> list[str]:
    checker = _clause_heals_ally_sp if resource == "SP" else _clause_heals_ally_hp
    return [
        clause
        for clause in _regen_clauses(skills, combat_text, support_text)
        if checker(clause)
    ]


def _heal_timing_note(clauses: list[str]) -> str:
    joined = " ".join(clauses).lower()
    if "on hit" in joined:
        return "On Hit"
    if "attack end" in joined:
        return "Attack End"
    if "turn end" in joined:
        return "Turn End"
    if "combat start" in joined:
        return "Combat Start"
    if "on kill" in joined:
        return "On Kill"
    return "each turn"


def _heal_target_note(clauses: list[str], resource: str) -> str:
    joined = " ".join(clauses).lower()
    if f"lowest {resource.lower()}" in joined or f"least {resource.lower()}" in joined:
        return f"lowest-{resource} allies"
    if "lowest hp" in joined or "hp percentage" in joined:
        return "lowest-HP allies"
    if "highest max hp" in joined:
        return "highest max-HP ally"
    if "other ally" in joined or "other allies" in joined:
        return "other allies"
    return "teammates"


def find_sp_regenerator_archetype(
    skills: list[dict],
    combat_text: str = "",
    raw_markdown: str = "",
    mechanic_profile: dict | None = None,
    support_text: str = "",
) -> _ARCHETYPE_RESULT | None:
    """Ally-facing SP sustain — passives or skills that restore teammate SP."""
    _ = mechanic_profile
    clauses = _ally_heal_clauses(skills, combat_text, support_text, "SP")
    if not clauses:
        return None

    timing = _heal_timing_note(clauses)
    target = _heal_target_note(clauses, "SP")
    tips = [
        f"**SP sustain** fires at **{timing}** — restores **{target}**.",
    ]
    if "turn end" in " ".join(clauses).lower():
        tips.append(
            "Low-SP allies are topped up after clashes — let them spend freely, "
            "then rely on Turn End healing."
        )

    return _build_archetype(
        kind="sp_regenerator",
        status="SP Regeneration",
        setup_summary=(
            "**SP regenerator** — restores ally **SP** through passives and key skills."
        ),
        tips=tips,
    )


def find_hp_regenerator_archetype(
    skills: list[dict],
    combat_text: str = "",
    raw_markdown: str = "",
    mechanic_profile: dict | None = None,
    support_text: str = "",
) -> _ARCHETYPE_RESULT | None:
    """Ally-facing HP sustain — passives or skills that restore teammate HP."""
    _ = mechanic_profile
    clauses = _ally_heal_clauses(skills, combat_text, support_text, "HP")
    if not clauses:
        return None

    timing = _heal_timing_note(clauses)
    target = _heal_target_note(clauses, "HP")
    tips = [
        f"**HP sustain** triggers at **{timing}** — restores **{target}**.",
    ]
    if "on hit" in " ".join(clauses).lower():
        tips.append(
            "Heals flow when allies land hits — attackers need to connect for the passive to proc."
        )

    return _build_archetype(
        kind="hp_regenerator",
        status="HP Regeneration",
        setup_summary=(
            "**HP regenerator** — tops up ally **HP** through passives and skills."
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
    "sp_regenerator_archetype",
    "hp_regenerator_archetype",
)

SPECIAL_ARCHETYPE_KEYS: tuple[str, ...] = (
    "unique_mechanics_archetype",
    "charge_archetype",
    "nails_archetype",
)

OVERVIEW_ARCHETYPE_KEYS: tuple[str, ...] = (
    "unique_mechanics_archetype",
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
    support_text: str = "",
    nails_archetype: dict | None = None,
    defense_archetype: dict | None = None,
) -> dict[str, _ARCHETYPE_RESULT]:
    """Run all sin-keyword and extra mechanic detectors."""
    common = {
        "skills": skills,
        "combat_text": combat_text,
        "raw_markdown": raw_markdown,
        "mechanic_profile": mechanic_profile,
    }
    regen_common = {**common, "support_text": support_text}
    out: dict[str, _ARCHETYPE_RESULT] = {}

    mapping: list[tuple[str, Callable[..., _ARCHETYPE_RESULT | None], dict]] = [
        ("burn_archetype", find_burn_archetype, {}),
        ("bleed_archetype", find_bleed_archetype, {"nails_archetype": nails_archetype}),
        ("tremor_archetype", find_tremor_archetype, {}),
        ("rupture_archetype", find_rupture_archetype, {}),
        ("sinking_archetype", find_sinking_archetype, {}),
        ("poise_archetype", find_poise_archetype, {}),
        ("aggro_archetype", find_aggro_archetype, {}),
        ("haste_archetype", find_haste_archetype, {"defense_archetype": defense_archetype}),
        ("paralyze_archetype", find_paralyze_archetype, {}),
        ("fragile_archetype", find_fragile_archetype, {}),
        ("discard_archetype", find_discard_archetype, {}),
        ("sp_regenerator_archetype", find_sp_regenerator_archetype, {}),
        ("hp_regenerator_archetype", find_hp_regenerator_archetype, {}),
    ]
    regen_keys = {"sp_regenerator_archetype", "hp_regenerator_archetype"}
    stack_keys = {"poise_archetype"}
    for key, fn, extra in mapping:
        base = regen_common if key in regen_keys else common
        if key in stack_keys:
            arch = fn(**base, support_text=support_text, **extra)
        else:
            arch = fn(**base, **extra)
        if arch:
            out[key] = arch
    return out


def pick_primary_sin_archetype(gp: dict) -> _ARCHETYPE_RESULT | None:
    """Best sin-keyword archetype for core-idea narrative (matches primary mechanic order)."""
    for special in ("unique_mechanics_archetype", "nails_archetype", "charge_archetype"):
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
