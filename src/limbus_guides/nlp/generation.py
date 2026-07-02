"""Guide text generation — skill-aware template + optional Ollama RAG."""

from __future__ import annotations

import json
import os
from textwrap import dedent

import re

from limbus_guides.domain.context import get_guide_writing_context, playstyle_hints_from_text
from limbus_guides.nlp.mechanic_signals import extract_notable_effects, top_fallback_coin_line
from limbus_guides.nlp.skill_parser import build_gameplan
from limbus_guides.nlp.skill_rolls import RollNormalizer, compute_coin_count, format_skill_rolls
from limbus_guides.nlp.synergy import GENERIC_TRAITS, format_unique_tremor_label

# ---------------------------------------------------------------------------
# Advice transformer — converts descriptive tooltip text to player instructions
# ---------------------------------------------------------------------------

_INFLICT = re.compile(r"^Inflict \+?(\d+) (\w+)(?: Count)?$", re.I)
_GAIN_STATUS = re.compile(r"^Gain \+?(\d+) (\w+)(?: Count)?(?:\s+next turn)?\.?$", re.I)
_DAMAGE_FLAT = re.compile(r"^Damage \+\d+$", re.I)
_IF_STATUS = re.compile(r"^If target has (\d+)\+ (\w+), deal \+(\d+)% damage", re.I)
_STAT_PER_NEG = re.compile(
    r"^(Clash|Coin|Final|Base) Power \+(\d+) for every type of negative effect[^(]*\(max (\d+)\)", re.I
)
_STAT_PER_COUNT = re.compile(
    r"^(Clash|Coin|Final|Base) Power \+(\d+) for every (\d+) (\w+)(?:\s+Count)?[^(]*\(max (\d+)\)", re.I
)
_AT_CONDITION = re.compile(r"^At (\d+)\+ ([\w ]+?),?\s+(?:Coin Power|Clash Power|Final Power|Base Power)\s*\+(\d+)", re.I)
_REFUND = re.compile(r"^C(\d+) refunds \+(\d+) ([\w ]+) Count(.*)")
_CONSUME_AT = re.compile(
    r"At (\d+)\+ ([\w ]+?), consume up to (\d+)", re.I
)
_DEAL_PER_NEG = re.compile(
    r"Deal \+(\d+)% damage for every type of negative effect[^(]*\(max (\d+)%\)", re.I
)
_CONSUME_CHARGE_CP_LINE = re.compile(
    r"^Consume (\d+) Charge Count for \+(\d+) Coin Power$", re.I
)
_POTENCY_CLASH_LINE = re.compile(
    r"^Clash Power = Charge Potency \(max \+(\d+)\)$", re.I
)
_AT_CHARGE_CLASH_LINE = re.compile(
    r"^At (\d+)\+ Charge, Clash Power \+(\d+)$", re.I
)
_CHARGE_COIN_SCALE_LINE = re.compile(
    r"^Final coin: consume up to (\d+) Charge for matching Coin Power$", re.I
)
_SELF_RESOURCE_DAMAGE_LINE = re.compile(r"^\+(\d+)% damage per (.+?) \(max \+(\d+)%\)$", re.I)
_SELF_RESOURCE_STAT_LINE = re.compile(
    r"^(Atk Weight|Coin Power|Base Power|Clash Power) \+(\d+) per (\d+) (.+?) \(max \+(\d+)\)$",
    re.I,
)


def _advise_line(text: str) -> str | None:
    """Reframe a descriptive mechanic line as a player instruction. Returns None to skip the line."""
    # Pure flat damage bonus — already in rolls, skip
    if _DAMAGE_FLAT.match(text):
        return None

    m = _INFLICT.match(text)
    if m:
        return None

    m = _GAIN_STATUS.match(text)
    if m and m.group(2).lower() in ("poise", "bleed", "burn", "rupture", "sinking", "tremor"):
        return None

    m = _IF_STATUS.match(text)
    if m:
        return f"Holds back until {m.group(1)}+ {m.group(2)} — deals +{m.group(3)}% more at that threshold."

    m = _STAT_PER_NEG.match(text)
    if m:
        stat, cap = m.group(1), m.group(3)
        return f"Stack {cap}+ debuff types on the target for up to +{cap} {stat} Power on this skill."

    m = _STAT_PER_COUNT.match(text)
    if m:
        stat, resource, cap = m.group(1), m.group(4).strip(), m.group(5)
        return f"Scales {stat} Power with {resource} stacks — apply liberally before committing (cap +{cap})."

    m = _AT_CONDITION.match(text)
    if m:
        return f"Needs {m.group(1)}+ {m.group(2).strip()} to activate — prioritise building stacks before using."

    m = _REFUND.match(text)
    if m:
        return f"Coin {m.group(1)} recovers {m.group(2)} {m.group(3)} Count{m.group(4)} — each use partially rebuilds your resource."

    m = _CONSUME_AT.match(text)
    if m:
        threshold, resource, amt = m.group(1), m.group(2).strip(), m.group(3)
        return f"At {threshold}+ {resource}: spend up to {amt} stacks — the more you burn, the higher the damage ceiling."

    m = _DEAL_PER_NEG.search(text)
    if m:
        return f"Each debuff type on the target adds +{m.group(1)}% damage (up to +{m.group(2)}%) — stack statuses broadly."

    m = _CONSUME_CHARGE_CP_LINE.match(text)
    if m:
        amt, cp = m.group(1), m.group(2)
        return (
            f"At **{amt}+ Charge Count**: spend **{amt}** stacks for **+{cp} Coin Power** "
            f"— save this for your dump turn."
        )

    m = _POTENCY_CLASH_LINE.match(text)
    if m:
        return (
            f"**Clash Power** equals **Charge Potency** (up to **+{m.group(1)}**) "
            f"— raise Potency before the spend flip."
        )

    m = _AT_CHARGE_CLASH_LINE.match(text)
    if m:
        return (
            f"Needs **{m.group(1)}+ Charge Count** for **+{m.group(2)} Clash Power** "
            f"— build stacks before committing."
        )

    m = _CHARGE_COIN_SCALE_LINE.match(text)
    if m:
        return (
            f"Final coin consumes up to **{m.group(1)} Charge Count** for matching "
            f"**Coin Power** — align the dump with your highest stack turn."
        )

    m = _SELF_RESOURCE_DAMAGE_LINE.match(text)
    if m:
        return (
            f"Up to **+{m.group(3)}% damage** (+{m.group(1)}% per **{m.group(2)}**) — "
            f"stack the resource before committing."
        )

    m = _SELF_RESOURCE_STAT_LINE.match(text)
    if m:
        return (
            f"**{m.group(1)}** scales with **{m.group(4)}** "
            f"(+{m.group(2)} per {m.group(3)}, max +{m.group(5)}) — build stacks first."
        )

    # Compound condition lines ("6+ Bleed, double crit ; 10+ Poise, +100% crit")
    if ";" in text and re.search(r"\d+\+", text):
        segments = [s.strip() for s in text.split(";") if s.strip()]
        if len(segments) >= 2:
            return "Peak output requires both conditions: " + " | ".join(segments[:2]) + "."

    return text


def _condition_key(text: str) -> tuple[str, str] | None:
    """Extract (threshold, status) for deduplication between bonus and notable lines."""
    m = re.search(r"(\d+)\+\s*([\w]+)", text)
    if m:
        return (m.group(1), m.group(2).lower())
    return None

SYSTEM_PROMPT = dedent(f"""\
    You are a Limbus Company guide writer. Given structured identity data,
    produce Core Idea (2-3 sentences), Playstyle Guide (1 paragraph), and
    Team Suggestions (3-5 bullets). Only reference mechanics in the provided data.

    {get_guide_writing_context()}
""")


# ---------------------------------------------------------------------------
# Smart template: reads actual skill data
# ---------------------------------------------------------------------------


def _describe_skill(
    skill: dict,
    resource_loop: dict | None,
    poise_passive: dict | None,
    normalizer: RollNormalizer | None = None,
) -> str:
    """Per-skill paragraph: roll range, then all notable coin/activation details."""
    sn = skill["skill_num"]
    name = skill["name"]
    bp = skill.get("base_power")
    cp = skill.get("coin_power")
    aw = skill.get("atk_weight")
    crit = skill.get("crit_bonus")

    stat_parts = []
    if bp is not None:
        stat_parts.append(f"BP {bp}")
    if cp:
        stat_parts.append(f"CP {cp}")
    if aw is not None:
        coin_n = compute_coin_count(skill)
        stat_parts.append(f"x{coin_n}")
    if crit:
        stat_parts.append(f"+{crit}% on crit")
    stat_str = f"({', '.join(stat_parts)})" if stat_parts else ""

    header = f"**S{sn} — {name}** {stat_str}: {format_skill_rolls(skill, normalizer)}."

    raw_detail: list[str] = []
    seen_conds: set[tuple[str, str]] = set()

    for bonus in skill.get("skill_bonuses", [])[:2]:
        if "[[" in bonus or "[[:Category:" in bonus:
            continue
        ck = _condition_key(bonus)
        if ck:
            if ck in seen_conds:
                continue
            seen_conds.add(ck)
        raw_detail.append(bonus)

    for scale in skill.get("damage_scales", [])[:3]:
        if scale in raw_detail:
            continue
        ck = _condition_key(scale)
        if ck and ck in seen_conds:
            continue
        if ck:
            seen_conds.add(ck)
        raw_detail.append(scale)

    notable = extract_notable_effects(skill, max_results=4)
    for line in notable:
        ck = _condition_key(line)
        if ck and ck in seen_conds:
            continue
        if ck:
            seen_conds.add(ck)
        if line not in raw_detail:
            raw_detail.append(line)

    if not notable:
        fallback = top_fallback_coin_line(skill)
        if fallback and fallback not in raw_detail:
            raw_detail.append(fallback)

    # Transform all collected lines to player instructions; drop None (filtered lines)
    detail: list[str] = []
    for raw in raw_detail:
        advised = _advise_line(raw)
        if advised is not None and advised not in detail:
            detail.append(advised)

    res_gained = skill.get("resources_gained", [])
    if resource_loop and res_gained and not any(resource_loop.get("resource", "") in b for b in detail):
        rg = res_gained[0]
        trigger = ""
        for cd in skill.get("coin_effects", []):
            if cd["coin"] == rg["coin"]:
                eff = cd["effect"]
                if "[Clash Win]" in eff:
                    trigger = " on Clash Win"
                elif "[Heads Hit]" in eff:
                    trigger = " on Heads Hit"
                break
        detail.append(f"C{rg['coin']} refunds +{rg['amount']} {rg['resource']} Count{trigger}")

    if detail:
        return f"{header}\n" + "\n".join(f"- {d}" for d in detail[:6])
    return header


_COMBINED_BURN_TREMOR = re.compile(r"Burn\s*\+\s*Tremor|\(Burn\s*\+\s*Tremor\)", re.I)


def _skill_effect_text(gp: dict) -> str:
    skill_parts: list[str] = []
    for skill in gp.get("skills", []):
        for key in ("skill_bonuses", "on_use_effects"):
            skill_parts.extend(skill.get(key, []))
    return " ".join(skill_parts)


def _scaling_conditions_sentence(gp: dict) -> str | None:
    """Standard scaling block — inserted after the hook for dashboard layout."""
    dmg = gp.get("damage_conditions") or []
    if dmg:
        return f"Scaling conditions: {'; '.join(dmg[:2])}."

    skill_text = _skill_effect_text(gp)
    if (
        _COMBINED_BURN_TREMOR.search(skill_text)
        and gp.get("burn_archetype")
        and gp.get("tremor_archetype")
    ):
        return (
            "Scaling conditions: clash and coin power scale from combined "
            "**Burn + Tremor** on the target."
        )
    return None


def _ammo_dual_status_core_parts(name: str, role_str: str, gp: dict) -> tuple[str, list[str]] | None:
    """Hook plus kit-detail sentences for ammo damage carries (scaling added centrally)."""
    ammo = gp.get("unique_ammo")
    if not ammo:
        return None

    burn_arch = gp.get("burn_archetype")
    tremor_arch = gp.get("tremor_archetype")
    if not burn_arch and not tremor_arch:
        return None

    from limbus_guides.nlp.synergy import format_unique_tremor_label

    status_bits: list[str] = []
    if tremor_arch:
        subtypes = gp.get("unique_tremor_types") or tremor_arch.get("unique_subtypes") or []
        if subtypes:
            status_bits.append(f"**{format_unique_tremor_label(subtypes[0])}**")
        else:
            status_bits.append("**Tremor**")
    if burn_arch:
        status_bits.append("**Burn**")

    skill_text = _skill_effect_text(gp)
    status_phrase = " and ".join(status_bits)

    details: list[str] = []
    def_arch = gp.get("defense_archetype") or {}
    if def_arch.get("kind") == "equip_unlock":
        details.append(
            "Equipping defense once reloads **Savage Tigermark Round** "
            "and unlocks the upgraded S3."
        )

    combat = gp.get("combat_passives_text", "")
    if re.search(r"gain Damage Up equal to the amount spent", combat, re.I):
        details.append("Gains **Damage Up** next turn from ammo spent.")
    if re.search(r"convert the Coins to Unbreakable", skill_text, re.I):
        details.append("S3 turns **Unbreakable** at **3+** ammo.")

    support_arch = gp.get("support_archetype") or {}
    if (
        support_arch.get("kind") == "deploy_order"
        and "ammo" in (support_arch.get("setup_summary") or "").lower()
    ):
        passive = support_arch.get("passive_name") or "Support passive"
        details.append(
            f"Support passive (**{passive}**) resupplies the earliest-deployed "
            f"**Ammo** ally once per fight."
        )

    premium = ammo["premium_skill"]
    hook = (
        f"{name} is a {role_str} — **{ammo['ammo_label']}** damage carry who applies "
        f"{status_phrase} on hits, spending ammo for burst on S{premium}."
    )
    return hook, details


def _devyat_courier_core_opening(name: str, role_str: str, gp: dict) -> str | None:
    """Devyat' kits: fast Courier Trunk below spike threshold, power at 15+, forced Strategic R&R."""
    retreat = gp.get("retreating_archetype") or {}
    if retreat.get("kind") != "devyat_courier":
        return None

    courier_label = retreat.get("courier_label", "Courier Trunk")
    threshold = retreat.get("courier_spike_threshold", 15)
    trigger = retreat.get("trigger_skill") or "maintenance Counter"

    rupture_note = ""
    if gp.get("rupture_archetype") or "Rupture" in (gp.get("primary_mechanics") or []):
        rupture_note = ", stacking **Rupture** on targets along the way"

    rejoin_note = ""
    combat = gp.get("combat_passives_text", "")
    if re.search(r"halve.*Courier Trunk", combat, re.I):
        rejoin_note = (
            " Rejoining once per fight **halves** carried stacks — front-load your best "
            "burst before returning."
        )

    return (
        f"{name} is a {role_str} — **Devyat' Courier** who races **{courier_label}** "
        f"below **{threshold}** for faster gains{rupture_note}, spikes clash power and "
        f"Shield at **{threshold}+**, then **{trigger}** forces **Strategic R&R** so "
        f"**Upon Retreat** can buff allies.{rejoin_note}"
    )


def _build_core_idea(name: str, gp: dict) -> str:
    from limbus_guides.domain.context import infer_roles
    from limbus_guides.nlp.archetypes import pick_extra_archetype, pick_primary_sin_archetype

    transition = gp["state_transition"]
    resource = gp["resource_loop"]
    poise = gp["poise_passive"]
    neg_scale = gp["neg_effect_scaling"]
    # Build a text fragment that includes the support-passive header so infer_roles can detect it
    support_text = gp.get("support_passive_text", "")
    skill_lines: list[str] = []
    for skill in gp.get("skills", []):
        skill_lines.extend(skill.get("skill_bonuses", []))
        skill_lines.extend(skill.get("on_use_effects", []))
    raw_text = (
        gp.get("combat_passives_text", "")
        + ("\n## Support Passive\n" + support_text if support_text else "")
        + ("\n" + "\n".join(skill_lines) if skill_lines else "")
    )

    roles = infer_roles(raw_text)
    role_str = " / ".join(roles)

    parts: list[str] = []
    post_scaling: list[str] = []

    # Opening sentence: role + positioning
    if transition and resource:
        parts.append(
            f"{name} is a {role_str} — {transition['from_state']} → {transition['to_state']} identity. "
            f"The gameplan is building {resource['resource']} Count through skill hits and "
            f"the combat passive, then spending stacks to power up S{resource['payoff_skills'][0] if resource['payoff_skills'] else '2'} "
            f"(at {resource['threshold']}+ Count) and cash out with "
            f"S{resource['payoff_skills'][-1] if resource['payoff_skills'] else '3'} "
            f"(consumes up to {resource['max'] or '?'} for escalating damage)."
        )
    elif resource:
        parts.append(
            f"{name} is a {role_str} — {resource['resource']}-gated identity. "
            f"Build stacks through skill hits until the threshold ({resource['threshold']}+), "
            f"then spend via S{resource['payoff_skills'][0] if resource['payoff_skills'] else '?'} "
            f"for power spikes."
        )
    elif gp.get("poise_archetype"):
        arch = gp["poise_archetype"]
        parts.append(f"{name} is a {role_str} — {arch['setup_summary']}")
    elif poise:
        parts.append(
            f"{name} is a {role_str} — Poise-stacking fighter. "
            f"Poise Count built through skill use and clash wins converts directly to Coin Power "
            f"(+{poise['coin_power_per']} CP per {poise['poise_per']} Poise Count, max +{poise['max']}) "
            f"— every successful clash raises your flip strength."
        )
    elif neg_scale:
        parts.append(
            f"{name} is a {role_str} — damage scales with the number of debuff types on the target. "
            f"Stack varied statuses before committing high-value skills."
        )
    elif gp.get("unique_mechanics_archetype"):
        arch = gp["unique_mechanics_archetype"]
        parts.append(f"{name} is a {role_str} — {arch['setup_summary']}")
    elif gp.get("nails_archetype"):
        arch = gp["nails_archetype"]
        threshold = arch.get("threshold", 5)
        payoff = arch.get("payoff_skill") or "the payoff skill"
        burst_note = " via Tremor Burst" if arch.get("has_tremor_burst") else ""
        parts.append(
            f"{name} is a {role_str} — **Nails** (N Corp. Fanatic) setup fighter. "
            f"Stack Nails toward **{threshold}+** with early skills, then cash out with "
            f"**{payoff}**{burst_note} for burst damage and debuffs."
        )
    elif gp.get("charge_archetype"):
        arch = gp["charge_archetype"]
        parts.append(f"{name} is a {role_str} — {arch['setup_summary']}")
        def_arch = gp.get("defense_archetype")
        if def_arch and def_arch.get("kind") == "skill_queue":
            defense_name = def_arch.get("defense_name", "Guard")
            payoff = arch.get("payoff_skill", "S3")
            post_scaling.append(
                f"**{defense_name}** queues an extra **{payoff}** next turn and can "
                f"remove a Stagger Threshold when Charge Count is low — guard sets up the burst."
            )
    elif gp.get("negative_coin_archetype"):
        arch = gp["negative_coin_archetype"]
        despair = arch.get("despair_label", "negative SP")
        minus = arch.get("minus_skills", [])
        minus_preview = minus[0] if minus else "Minus Coin alternates"
        if arch.get("defense_drains_sp"):
            parts.append(
                f"{name} is a {role_str} — **Minus Coin** identity that must reach "
                f"**{despair}** (negative SP) to unlock {minus_preview} and peers. "
                f"Open with defense turns to drain SP and build Tear-sharpened, then "
                f"cash out Deep Tears with Despair Skill 3."
            )
        else:
            parts.append(
                f"{name} is a {role_str} — **Minus Coin** identity gated by SP: "
                f"below 0 SP she swaps to **{despair}** skills ({minus_preview}, …) "
                f"with far higher Base Power than the Plus Coin set."
            )
    elif (ammo_parts := _ammo_dual_status_core_parts(name, role_str, gp)):
        parts.append(ammo_parts[0])
        post_scaling.extend(ammo_parts[1])
    elif (devyat_open := _devyat_courier_core_opening(name, role_str, gp)):
        parts.append(devyat_open)
    elif (sin_arch := pick_primary_sin_archetype(gp)) and sin_arch.get("kind") not in (
        "nails_setup",
        "charge_scaling",
        "unique_mechanics",
    ):
        parts.append(f"{name} is a {role_str} — {sin_arch['setup_summary']}")
    elif (extra_arch := pick_extra_archetype(gp)):
        parts.append(f"{name} is a {role_str} — {extra_arch['setup_summary']}")
    elif gp.get("defense_archetype"):
        arch = gp["defense_archetype"]
        payoff = arch.get("payoff") or "a powered-up attack"
        defense_name = arch.get("defense_name", "the defense skill")
        kind = arch.get("kind", "")
        if kind == "snipe_setup":
            parts.append(
                f"{name} is a {role_str} — snipe archer whose defense slot builds Target Aim "
                f"and triggers **{payoff}** at Combat Start via Snipe - Archery."
            )
        elif kind == "counter_skill":
            parts.append(
                f"{name} is a {role_str} — **{defense_name}** can fire **{payoff}** as a "
                f"Counter for burst damage when conditions are met."
            )
        elif kind == "skill_queue":
            parts.append(
                f"{name} is a {role_str} — the defense slot queues high-impact skills or "
                f"major setup buffs for the following turn."
            )
        elif kind == "equip_unlock":
            parts.append(
                f"{name} is a {role_str} — equipping defense for the first time unlocks "
                f"an upgraded ammo/skill set for the rest of the encounter."
            )
        elif kind == "guard_buff":
            if "Tank" in role_str:
                parts.append(
                    f"{name} is a {role_str} — high-HP frontliner with +3 Aggro on every skill "
                    f"and a once-per-encounter lethal nullify. "
                    f"**{defense_name}** grants **{payoff}** at Combat Start; "
                    f"Skill 3 scales off missing HP and Bloodied Hand stacks."
                )
            else:
                parts.append(
                    f"{name} is a {role_str} — **{defense_name}** grants **{payoff}** at "
                    f"Combat Start, making the guard slot part of the damage rotation."
                )
        elif kind == "power_counter":
            parts.append(
                f"{name} is a {role_str} — **{defense_name}** is a high-damage counter "
                f"with Stagger immunity, not just a defensive tool."
            )
        else:
            parts.append(
                f"{name} is a {role_str} — the defense slot unlocks major buffs or "
                f"alternate skills; plan defense turns deliberately."
            )
    else:
        primary = gp["primary_mechanics"]
        mech = ", ".join(primary[:2]) if primary else "status"
        parts.append(f"{name} is a {role_str} applying sustained {mech} pressure with consistent skill stats.")

    if scaling := _scaling_conditions_sentence(gp):
        if scaling not in " ".join(parts):
            parts.append(scaling)
    parts.extend(post_scaling)

    if gp.get("heads_dependent"):
        parts.append(
            "Key damage is Heads-flip dependent — high-variance kit; "
            "pair with SP-rich allies or Gambit-style passives to maximise Heads output."
        )

    if "Support" in role_str and gp.get("support_archetype"):
        setup = gp["support_archetype"].get("setup_summary")
        passive = gp["support_archetype"].get("passive_name", "")
        blob = " ".join(parts)
        if setup and passive not in blob and setup not in blob:
            parts.append(setup)

    if gp.get("sp_regenerator_archetype"):
        setup = gp["sp_regenerator_archetype"].get("setup_summary")
        if setup:
            parts.append(setup)

    if gp.get("hp_regenerator_archetype"):
        setup = gp["hp_regenerator_archetype"].get("setup_summary")
        if setup:
            parts.append(setup)

    if gp.get("retreating_archetype"):
        retreat_arch = gp["retreating_archetype"]
        setup = retreat_arch.get("setup_summary")
        if setup and retreat_arch.get("kind") != "devyat_courier":
            blob = " ".join(parts)
            if setup not in blob:
                parts.append(setup)

    return " ".join(parts)


_ALT_SKIP_TAGS = re.compile(
    r"^\[(?:Indiscriminate|Unclashable|On Use|On Hit|On Kill|Heads Hit|Attack End|Clash Win)\]$",
    re.I,
)
_ALT_SKIP_PHRASES = re.compile(
    r"^(?:This Skill has the following properties|Does not trigger Defense Skills|"
    r"External effects cannot trigger|Its attack does not hit|"
    r"This Skill does not trigger)",
    re.I,
)


def _parse_alt_clauses(on_use_effects: list[str]) -> list[str]:
    """Split semicolon-separated on_use_effects into individual meaningful clauses."""
    clauses: list[str] = []
    for raw_line in on_use_effects:
        parts = re.split(r"\s*;\s*", raw_line)
        for part in parts:
            # Strip bracketed prefixes like [On Use], [Attack End], leading dashes
            clean = re.sub(r"^\[[\w\s]+\]\s*", "", part).strip(" -")
            clean = re.sub(r"\[\[:Category:[^\]]+\]\]?.*$", "", clean).strip()
            if not clean or len(clean) < 5:
                continue
            if _ALT_SKIP_TAGS.match(clean):
                continue
            if _ALT_SKIP_PHRASES.match(clean):
                continue
            clauses.append(clean)
    return clauses


def _describe_alternate_skill(skill: dict, normalizer: RollNormalizer | None = None) -> str:
    """
    Compact description of an alternate skill block (triggered variant, unclashable buff, etc.).
    Listed under the primary skill with a sub-header.
    """
    sn = skill["skill_num"]
    name = skill["name"]
    aw = skill.get("atk_weight")
    bp = skill.get("base_power")
    cp = skill.get("coin_power")

    props: list[str] = []
    if aw == 0:
        props.append("Unclashable")
    if bp is not None and aw and aw > 0:
        stat_parts = [f"BP {bp}"]
        if cp:
            stat_parts.append(f"CP {cp}")
        props.append(", ".join(stat_parts))

    blob = " ".join(
        skill.get("skill_bonuses", [])
        + [e.get("effect", "") for e in skill.get("coin_effects", [])]
        + skill.get("on_use_effects", [])
    )
    if "Indiscriminate" in blob:
        props.append("Indiscriminate")

    prop_str = f" ({', '.join(props)})" if props else ""

    # Determine if the skill deals actual damage via coins
    has_coins = bool(skill.get("coin_effects")) or bool(skill.get("base_power"))
    rolls_str = ""
    if has_coins and skill.get("base_power") is not None:
        rolls_str = " " + format_skill_rolls(skill, normalizer) + "."
    elif aw == 0 and not has_coins:
        rolls_str = " No attack roll."

    header = f"*↳ Alternate S{sn} — {name}*{prop_str}:{rolls_str}"

    # Collect meaningful effect clauses from on_use_effects (primary source for unclashables)
    detail: list[str] = []
    alt_clauses = _parse_alt_clauses(skill.get("on_use_effects", []))
    for clause in alt_clauses:
        advised = _advise_line(clause)
        if advised and advised not in detail:
            detail.append(advised)

    # Grab coin effects for skills that do attack (have coin_effects)
    for ce in skill.get("coin_effects", [])[:2]:
        eff = re.sub(r"^\[[\w\s]+\]\s*", "", ce.get("effect", "")).strip()
        # Split on first ;  to get the primary part
        eff = eff.split(";")[0].strip()
        if eff and len(eff) > 5 and "[[:Category:" not in eff:
            advised = _advise_line(eff)
            if advised and advised not in detail:
                detail.append(advised)

    if detail:
        return header + "\n" + "\n".join(f"  - {d}" for d in detail[:5])
    return header


def _build_overview_tips(gp: dict) -> str:
    """
    2–4 rotation-level tips summarising what the player should focus on each turn.
    These appear before the per-skill breakdown.
    """
    resource = gp["resource_loop"]
    transition = gp["state_transition"]
    poise = gp["poise_passive"]
    neg_scale = gp["neg_effect_scaling"]
    dmg = gp["damage_conditions"]
    heads = gp.get("heads_dependent", False)
    support_text = gp.get("support_passive_text", "")
    skills = gp["skills"]

    tips: list[str] = []

    neg_coin = gp.get("negative_coin_archetype")
    if neg_coin:
        tips.extend(neg_coin.get("tips", []))

    support_arch = gp.get("support_archetype")
    if support_arch:
        tips.extend(support_arch.get("tips", []))

    retreat_arch = gp.get("retreating_archetype")
    if retreat_arch:
        tips.extend(retreat_arch.get("tips", []))

    unique_arch = gp.get("unique_mechanics_archetype")
    if unique_arch:
        tips.extend(unique_arch.get("tips", []))

    nails_arch = gp.get("nails_archetype")
    if nails_arch:
        tips.extend(nails_arch.get("tips", []))

    charge_arch = gp.get("charge_archetype")
    if charge_arch:
        tips.extend(charge_arch.get("tips", []))

    from limbus_guides.nlp.archetypes import OVERVIEW_ARCHETYPE_KEYS

    seen_tips: set[str] = set(tips)
    for key in OVERVIEW_ARCHETYPE_KEYS:
        if key in ("unique_mechanics_archetype", "nails_archetype", "charge_archetype"):
            continue
        arch = gp.get(key)
        if not arch:
            continue
        if key == "sinking_archetype" and unique_arch:
            mechanics = unique_arch.get("mechanics", [])
            primary = gp.get("primary_mechanics", [])
            if any(m in primary[:2] for m in mechanics):
                continue
            continue
        for tip in arch.get("tips", []):
            if tip not in seen_tips:
                tips.append(tip)
                seen_tips.add(tip)

    defense_arch = gp.get("defense_archetype")
    if defense_arch and not neg_coin and not charge_arch:
        tips.extend(defense_arch.get("tips", []))
    elif defense_arch and not neg_coin and charge_arch:
        tips.extend(defense_arch.get("tips", [])[:1])

    # Unique ammo spent on coin flips — preserve for premium skills
    unique_ammo = gp.get("unique_ammo")
    if unique_ammo:
        budget_str = ", ".join(f"S{n}" for n in unique_ammo["budget_skills"])
        premium = unique_ammo["premium_skill"]
        spends_on_budget = any(
            unique_ammo["spend_per_skill"].get(n, 0) > 0 for n in unique_ammo["budget_skills"]
        )
        if spends_on_budget:
            opener = (
                f"Manage **{unique_ammo['ammo_label']}** — multiple skills spend limited ammo on coin flips."
            )
        else:
            opener = (
                f"Manage **{unique_ammo['ammo_label']}** — S{premium} spends ammo on its coin flips."
            )
        tips.append(
            f"{opener} Preserve **{unique_ammo['ammo_label']}** for S{premium}; when reserves are low, skip or pass on "
            f"weaker {budget_str} so your strongest skill keeps fully empowered coins."
        )

    # Resource loop: what to build and when to spend
    if resource:
        build = ", ".join(f"S{n}" for n in resource.get("build_skills", []))
        payoff = ", ".join(f"S{n}" for n in resource.get("payoff_skills", []))
        threshold = resource.get("threshold", "?")
        max_spend = resource.get("max")
        build_str = f" with {build}" if build else ""
        payoff_str = f" via {payoff}" if payoff else ""
        spend_str = f" (consumes up to {max_spend})" if max_spend else ""
        tips.append(
            f"Build {resource['resource']} Count{build_str} — spend{payoff_str} once you hit {threshold}+{spend_str}."
        )

    # Status threshold scaling — reach the condition before committing
    if dmg:
        status_tips = [d for d in dmg if "per" in d.lower() and "+" in d]
        if status_tips:
            tips.append(f"Reach scaling conditions before committing S3: {status_tips[0]}.")

    # Negative-effect scaling without a resource loop
    if neg_scale and not resource:
        tips.append("Stack several distinct status types on the target before using high-power skills — each debuff type adds to damage.")

    # State transition
    if transition:
        tips.append(
            f"The kit transitions to {transition['to_state']} once ({transition['trigger']}). "
            f"Before the transition, play normally; after, you gain access to a stronger skill set."
        )

    # Poise stacking — skip when archetype already covers the kit
    if poise and not gp.get("poise_archetype"):
        tips.append(
            f"Prioritise clashing — every successful clash win raises your Coin Power "
            f"(+{poise['coin_power_per']} CP per {poise['poise_per']} Poise Count, max +{poise['max']})."
        )

    # Heads-dependent kit
    if heads:
        tips.append("High-variance kit — key damage requires Heads flips. Bring SP-positive allies to maintain Gambit/blessing states.")

    import re as _re
    faction_m = _re.search(r"(The Ring|The Fingers|Kurokumo|Liu Assoc|Blade Lineage|Tingtang)\s+allies", support_text, _re.I)
    if faction_m:
        tips.append(f"Support passive scales with {faction_m.group(1)} allies on the field — prioritise faction team compositions.")

    # Ally combo trigger from combat passive (e.g. Nursefather + Ring Apprentice Faust)
    ally_combo = gp.get("ally_combo")
    if ally_combo:
        ally = ally_combo["ally"]
        trig = ally_combo["trigger_skill"]
        fired = ally_combo["fired_skill"]
        tips.append(
            f"Ally combo — before {ally} uses S{trig}, this identity automatically fires {fired}. "
            f"Slot {ally} alongside for a free extra hit every rotation."
        )

    s3 = next((s for s in skills if s["skill_num"] == 3), None)
    if s3 and s3.get("conditions"):
        tips.append(
            f"Hold S3 for when {s3['conditions'][0]} is met — "
            f"that condition is what unlocks its full damage ceiling."
        )
    elif s3 and s3.get("has_unbreakable"):
        tips.append("S3 carries Unbreakable Coin — commit it when the clash strongly favors you.")

    return "\n".join(f"- {t}" for t in tips)


def _build_playstyle(name: str, gp: dict, normalizer: RollNormalizer | None = None) -> str:
    skills = gp["skills"]
    alternate_skills = gp.get("alternate_skills", [])
    resource = gp["resource_loop"]
    transition = gp["state_transition"]
    poise = gp["poise_passive"]

    # Index alternates by skill_num for quick lookup
    from collections import defaultdict
    alt_by_num: dict[int, list[dict]] = defaultdict(list)
    for alt in alternate_skills:
        alt_by_num[alt["skill_num"]].append(alt)

    sections: list[str] = []

    overview = _build_overview_tips(gp)
    if overview:
        sections.append(overview)

    for skill in sorted(skills, key=lambda s: s["skill_num"]):
        skill_section = _describe_skill(skill, resource, poise, normalizer)
        # Append any alternate skill blocks immediately after their primary
        for alt in alt_by_num.get(skill["skill_num"], []):
            skill_section += "\n\n" + _describe_alternate_skill(alt, normalizer)
        sections.append(skill_section)

    ally_combo = gp.get("ally_combo")
    ally_combo_name = ally_combo["ally"] if ally_combo else None
    for passive in gp.get("combat_passive_notes", [])[:2]:
        mechanic_lines: list[str] = passive.get("mechanic_lines") or [passive["note"]]
        # If this passive is the ally combo passive, skip the first line (already in overview)
        # and start from the mechanic effects
        start_idx = 0
        if ally_combo_name and any(ally_combo_name in ml for ml in mechanic_lines[:1]):
            start_idx = 1
        lines_to_show = mechanic_lines[start_idx : start_idx + 3]
        if not lines_to_show:
            lines_to_show = mechanic_lines[:3]
        formatted_lines: list[str] = []
        for ml in lines_to_show:
            ml = ml.strip().rstrip(".")
            if len(ml) > 140:
                ml = ml[:137].rstrip() + "…"
            formatted_lines.append(ml)
        if len(formatted_lines) == 1:
            passive_text = formatted_lines[0] + "."
        else:
            passive_text = formatted_lines[0] + ".\n" + "\n".join(f"  - {l}." for l in formatted_lines[1:])
        sections.append(f"Combat passive — **{passive['name']}**: {passive_text}")

    if transition:
        sections.append(
            f"The transition to {transition['to_state']} triggers automatically "
            f"({transition['trigger']}, once per Encounter). "
            f"{transition['effect']}"
        )

    if poise and not gp.get("poise_archetype"):
        clash_note = " Clash wins are doubly valuable — they build Count (via skills) and the passive triggers." if poise["clash_win"] else ""
        sections.append(
            f"The 'Poised' passive converts Poise Count to Coin Power throughout the battle — "
            f"maintain pressure and keep clashing to sustain elevated flip results.{clash_note}"
        )

    # Defense skill notes — only for kits where the defense slot is mechanically significant.
    # Show at most the one richest defense skill (most mechanic_lines) to avoid bloat.
    defense_notes = sorted(
        gp.get("defense_skill_notes", []),
        key=lambda n: len(n.get("mechanic_lines", [])),
        reverse=True,
    )
    for def_note in defense_notes[:1]:
        lines_to_show = def_note.get("mechanic_lines", [def_note["note"]])[:4]
        formatted: list[str] = []
        for ml in lines_to_show:
            ml = ml.strip().rstrip(".")
            if len(ml) > 150:
                ml = ml[:147].rstrip() + "…"
            formatted.append(ml)
        if len(formatted) == 1:
            def_text = formatted[0] + "."
        else:
            def_text = formatted[0] + ".\n" + "\n".join(f"  - {l}." for l in formatted[1:])
        sections.append(f"Defense skill — **{def_note['name']}**: {def_text}")

    if gp.get("alternate_skills") and gp.get("trait_conditional"):
        traits = [t for t in gp.get("traits_list", []) if t not in GENERIC_TRAITS]
        if traits:
            sections.append(
                f"*Alternate skills activate when [{', '.join(traits[:2])}] allies are on the team.*"
            )

    return "\n\n".join(sections)


def _max_skill_coin_power(skills: list[dict]) -> int:
    """Highest Coin Power value across the skill set."""
    best = 0
    for skill in skills:
        cp = skill.get("coin_power") or ""
        m = re.search(r"(\d+)", cp.replace(" ", ""))
        if m:
            best = max(best, int(m.group(1)))
    return best


def _is_status_consumer(gp: dict, status: str) -> bool:
    """
    True when the kit checks status thresholds for bonus damage
    but does not reliably apply that status itself.
    """
    skills = gp.get("skills", [])
    status_lower = status.lower()
    has_threshold = any(
        status_lower in cond.lower()
        for skill in skills
        for cond in skill.get("conditions", [])
    ) or any(
        status_lower in cond.lower()
        for cond in gp.get("damage_conditions", [])
    )
    if not has_threshold:
        return False

    inflicted = 0
    for skill in skills:
        blob = " ".join(skill.get("skill_bonuses", []))
        for coin in skill.get("coin_effects", []):
            blob += " " + coin.get("effect", "")
        for m in re.finditer(rf"(?:Inflict|Gain)\s+\+?(\d+)\s+{status}\b", blob, re.I):
            inflicted += int(m.group(1))
    return inflicted < 6


def _detect_key_status(gp: dict, synergies: list[dict] | None = None) -> str | None:
    """Infer a scaling status from kit data — not from synergy picks alone."""
    _STATUS_NAMES = ("Bleed", "Burn", "Rupture", "Poise", "Sinking", "Tremor", "Charge")

    for cond in gp.get("damage_conditions", []):
        for s in _STATUS_NAMES:
            if s.lower() in cond.lower():
                return s

    resource = gp.get("resource_loop")
    if resource:
        res = resource["resource"]
        for s in _STATUS_NAMES:
            if s.lower() in res.lower():
                return s

    for skill in gp.get("skills", []):
        for ds in skill.get("damage_scales", []):
            for s in _STATUS_NAMES:
                if s.lower() in ds.lower():
                    return s
        for cond in skill.get("conditions", []):
            for s in _STATUS_NAMES:
                if s.lower() in cond.lower():
                    return s
        for bonus in skill.get("skill_bonuses", []):
            for s in _STATUS_NAMES:
                if re.search(rf"\d+\+\s+{s}|per\s+{s}|every\s+{s}", bonus, re.I):
                    return s

    return None


def _team_intro(gp: dict, synergies: list[dict]) -> str:
    """One or two sentences describing what team compositions this identity fits into."""
    from limbus_guides.nlp.archetypes import pick_extra_archetype, pick_primary_sin_archetype

    resource = gp.get("resource_loop")
    neg_scale = gp.get("neg_effect_scaling")
    ally_combo = gp.get("ally_combo")
    poise = gp.get("poise_passive")
    support_text = gp.get("support_passive_text", "")
    heads = gp.get("heads_dependent", False)
    skills = gp.get("skills", [])
    max_cp = _max_skill_coin_power(skills)
    primary = gp.get("primary_mechanics", [])
    key_status = _detect_key_status(gp, synergies)

    pieces: list[str] = []

    meaningful_traits = [t for t in gp.get("traits_list", []) if t not in GENERIC_TRAITS]
    kindred_traits = [t for t in meaningful_traits if "Kindred" in t]
    trait_kit = bool(
        meaningful_traits
        and (gp.get("trait_conditional") or gp.get("resonance_dependent"))
        and (gp.get("alternate_skills") or gp.get("resonance_dependent"))
    )

    if ally_combo:
        pieces.append(
            f"Built around a two-identity combo with {ally_combo['ally']} — "
            f"slot both for the passive synergy."
        )
    elif "Heishou Pack" in meaningful_traits:
        pieces.append(
            "**Heishou Pack** composition — anchor the team with **The Lord of Hongyuan Hong Lu**; "
            "his passives heal allies that **Substitute in** or **Return to the battlefield**, "
            "command free Unopposed Attacks, and stack **Life from Death** and "
            "**Heishou Bolus Contamination** for the faction."
        )
    elif trait_kit and kindred_traits:
        pieces.append(
            f"La Manchaland support — pair with same-generation [{kindred_traits[0]}] allies "
            f"to unlock alternate Hardblood skills and strengthen Bloodfeast passives."
        )
    elif (
        "bloodfeast" in gp.get("combat_passives_text", "").lower()
        and "La Manchaland" in meaningful_traits
        and not trait_kit
    ):
        pieces.append(
            "La Manchaland Bloodfeast tank — slot alongside other La Manchaland identities "
            "to feed the shared pool while absorbing aggro for Hardblood spenders."
        )
    elif trait_kit:
        shared = meaningful_traits[0]
        pieces.append(
            f"Trait-dependent kit — [{shared}] allies raise Resonance and unlock alternate skills."
        )
    elif gp.get("unique_tremor_types") or gp.get("tremor_archetype"):
        arch = gp.get("tremor_archetype") or {}
        if arch.get("setup_summary"):
            pieces.append(arch["setup_summary"])
        else:
            labels = ", ".join(
                format_unique_tremor_label(t) for t in gp["unique_tremor_types"]
            )
            pieces.append(
                f"Uses unique Tremor ({labels}) — prioritize teammates who apply the same "
                f"Tremor subtype so Amplitude Conversion and Burst effects stack on one target."
            )
    elif gp.get("nails_archetype"):
        threshold = gp["nails_archetype"].get("threshold", 5)
        pieces.append(
            f"**Nails/Tremor** setup — reach **{threshold}+ Nails** before the burst skill; "
            f"this kit self-applies both but Tremor Burst payoffs reward patient stacking."
        )
    elif gp.get("charge_archetype"):
        pieces.append(gp["charge_archetype"].get("setup_summary", (
            "**Charge** cycle — build Count toward **20**, spend on highest-damage skills, "
            "then rebuild for the next window."
        )))
    elif (sin_arch := pick_primary_sin_archetype(gp)) and sin_arch.get("setup_summary"):
        pieces.append(sin_arch["setup_summary"])
    elif (extra_arch := pick_extra_archetype(gp)) and extra_arch.get("status") == "Aggro":
        pieces.append(
            "**Aggro** frontliner — draws enemy focus so teammates can apply statuses and burst safely."
        )
    elif neg_scale:
        pieces.append(
            "Fits into any team that can spread varied status types — "
            "each distinct debuff on the target adds to damage output."
        )
    elif resource and key_status:
        pieces.append(
            f"Pairs best with teammates whose support passives apply or amplify {key_status}, "
            f"accelerating stack build-up."
        )
    elif resource:
        res = resource["resource"]
        pieces.append(
            f"Pairs best with teammates who can accelerate {res} stack generation."
        )
    elif poise:
        pieces.append(
            "Works in any aggressive composition; clash-heavy lineups let this identity "
            "build Poise Count faster and sustain elevated Coin Power."
        )
    elif heads and (max_cp >= 15 or (primary and primary[0].lower() == "coin power")):
        pieces.append(
            "High Coin Power damage dealer — pair with SP-positive allies to fuel Gambit "
            "and maximise Heads output."
        )
        if key_status and _is_status_consumer(gp, key_status):
            pieces.append(
                f"Teammates that apply {key_status} help him hit his damage thresholds; "
                f"he does not stack much {key_status} on his own."
            )
    elif key_status and _is_status_consumer(gp, key_status):
        pieces.append(
            f"Benefits when teammates apply {key_status} — "
            f"he checks {key_status} thresholds more than he stacks it himself."
        )
    elif key_status:
        pieces.append(
            f"Best placed in a {key_status}-focused team — "
            f"teammates that apply or extend {key_status} increase this kit's damage ceiling."
        )
    else:
        pieces.append(
            "Flexible pick; slotting alongside identities whose support passives "
            "provide relevant statuses or SP recovery maximises uptime."
        )

    if gp.get("resonance_dependent") and gp.get("traits_list"):
        key_trait = next((t for t in gp["traits_list"] if t not in GENERIC_TRAITS), None)
        if key_trait:
            pieces.append(
                f"Resonance-scaling identity — each additional [{key_trait}] ally "
                f"on the team directly improves skill and Counter output."
            )

    # Note if a faction team is naturally recommended
    rule_matches = [s for s in synergies if s.get("source") == "rule"]
    faction_matches = [s for s in rule_matches if s.get("faction_match")]
    if faction_matches and not ally_combo:
        pieces.append("Same-faction teammates provide additional passive synergy where available.")

    # Note if the support passive makes this identity a support pick
    import re as _re
    if _re.search(r"ally|allies|team", support_text, _re.I):
        pieces.append(
            "The support passive also benefits teammates directly — "
            "consider this identity even in compositions where it is not the primary damage dealer."
        )

    return " ".join(pieces)


def _embedding_verify_note(source: str) -> str:
    """Suffix for embedding-based teammate picks shown in team suggestions."""
    return " *(similarity-based — verify)*" if source == "embedding" else ""


def _build_team_suggestions(synergies: list[dict], gp: dict | None = None) -> dict:
    """
    Intro sentence describing the team role, followed by exactly 3 specific teammates.
    Prefers rule-based (passive-grounded) matches; falls back to embedding if needed.

    Returns intro, structured picks (for clickable UI links), and plain markdown lines.
    """
    rule_picks = [s for s in synergies if s.get("source") == "rule"]
    lord_picks = [s for s in rule_picks if s.get("heishou_lord_synergy")]
    trait_picks = [s for s in rule_picks if s.get("trait_match") and not s.get("heishou_lord_synergy")]
    other_rules = [s for s in rule_picks if not s.get("trait_match") and not s.get("heishou_lord_synergy")]
    embed_picks = [s for s in synergies if s.get("source") == "embedding"]

    # Lord of Hongyuan first for Heishou Pack; then trait allies; then other rules
    raw_picks = (lord_picks + trait_picks + other_rules + embed_picks)[:3]

    intro: str | None = None
    if gp is not None:
        intro = _team_intro(gp, synergies)

    picks: list[dict] = []
    lines: list[str] = []
    if intro:
        lines.append(intro)

    if raw_picks:
        for s in raw_picks:
            source = s.get("source", "")
            reason = s["reason"]
            picks.append(
                {
                    "teammate_slug": s["teammate_slug"],
                    "teammate_name": s["teammate_name"],
                    "reason": reason,
                    "source": source,
                }
            )
            lines.append(f"- **{s['teammate_name']}**: {reason}{_embedding_verify_note(source)}")
    else:
        lines.append(
            "- Pair with identities whose support passives inflict statuses this kit stacks "
            "or scales off."
        )

    return {"intro": intro, "picks": picks, "lines": lines}


def _smart_guide(
    identity: dict,
    synergies: list[dict],
    normalizer: RollNormalizer | None = None,
) -> dict:
    """Skill-aware template guide — reads parsed_skills and builds specific advice."""
    gp = build_gameplan(identity)
    name = identity.get("name", identity.get("slug", ""))
    team = _build_team_suggestions(synergies, gp)

    return {
        "core_idea": _build_core_idea(name, gp),
        "playstyle_guide": _build_playstyle(name, gp, normalizer),
        "team_suggestions": team["lines"],
        "team_suggestion_intro": team["intro"],
        "team_suggestion_picks": team["picks"],
        "generator": "template_smart",
        "domain_context": "docs/domain-primer.md",
    }


# ---------------------------------------------------------------------------
# Ollama path (unchanged, still available with USE_OLLAMA=1)
# ---------------------------------------------------------------------------


def _ollama_generate(prompt: str, model: str = "mistral") -> str | None:
    try:
        import requests

        resp = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": model,
                "prompt": prompt,
                "system": SYSTEM_PROMPT,
                "stream": False,
                "options": {"temperature": 0.3, "num_predict": 600},
            },
            timeout=120,
        )
        resp.raise_for_status()
        return resp.json().get("response")
    except Exception:
        return None


def _parse_llm_sections(text: str) -> dict:
    return {
        "core_idea": _section(text, "core idea") or text[:400],
        "playstyle_guide": _section(text, "playstyle") or text[400:900],
        "team_suggestions": _bullets(text, "team"),
        "generator": "ollama",
    }


def _section(text: str, keyword: str) -> str:
    lower = text.lower()
    idx = lower.find(keyword)
    if idx < 0:
        return ""
    chunk = text[idx : idx + 600]
    return chunk.split("\n\n")[0].strip()


def _bullets(text: str, keyword: str) -> list[str]:
    lower = text.lower()
    idx = lower.find(keyword)
    if idx < 0:
        return []
    tail = text[idx:]
    lines = [ln.strip() for ln in tail.splitlines() if ln.strip().startswith("-")]
    return lines[:5]


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def generate_guide(
    identity: dict,
    synergies: list[dict],
    use_ollama: bool | None = None,
    normalizer: RollNormalizer | None = None,
) -> dict:
    if use_ollama is None:
        use_ollama = os.environ.get("USE_OLLAMA", "").lower() in ("1", "true", "yes")

    if use_ollama:
        ctx = identity.get("raw_markdown", json.dumps(identity, ensure_ascii=False)[:8000])
        syn_text = "\n".join(f"- {s['teammate_name']}: {s['reason']}" for s in synergies)
        domain = get_guide_writing_context(include_full_primer=True)
        hints = playstyle_hints_from_text(ctx)
        prompt = (
            f"Domain context:\n{domain}\n\n"
            f"Identity data:\n{ctx}\n\n"
            f"Suggested synergies:\n{syn_text}\n\n"
            f"Playstyle hints:\n" + "\n".join(f"- {h}" for h in hints) + "\n\n"
            "Write the guide sections."
        )
        llm_out = _ollama_generate(prompt)
        if llm_out:
            guide = _parse_llm_sections(llm_out)
            team = _build_team_suggestions(synergies)
            llm_teams = guide.get("team_suggestions")
            if llm_teams:
                # LLM bullets are not aligned with structured picks — plain markdown only.
                guide["team_suggestions"] = llm_teams
            else:
                guide["team_suggestions"] = team["lines"]
                guide["team_suggestion_intro"] = team["intro"]
                guide["team_suggestion_picks"] = team["picks"]
            guide["domain_context"] = "docs/domain-primer.md"
            return guide

    return _smart_guide(identity, synergies, normalizer)
