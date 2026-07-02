"""Parse skill data from identity markdown into structured dicts for guide generation."""

from __future__ import annotations

import re

from limbus_guides.nlp.mechanic_signals import clean_effect_text
from limbus_guides.ingestion.markdown_loader import parse_traits_list
from limbus_guides.nlp.synergy import extract_unique_tremor_types

# ---------------------------------------------------------------------------
# Compile-once regexes
# ---------------------------------------------------------------------------

_SKILL_HEADER = re.compile(r"^### Skill (\d+):\s*(.+)", re.MULTILINE)
_SECTION_BOUNDARY = re.compile(r"^## ", re.MULTILINE)
_OWNERSHIP_NOTE = re.compile(r"^\(×\d+")  # "(×4 Owned)" type lines

# Attack-skill stats row: | 61 (60+1) | 3 | +4 | x3 |  (4 columns, last is Atk Weight)
_STATS_DATA = re.compile(
    r"^\|\s*\d+[^|]*\|\s*(\d+)\s*\|\s*([+-]\d+)\s*\|\s*x(\d+)\s*\|"
)

_ON_USE = re.compile(r"^\*\*\[On Use\]\*\*\s+(.+)")

# "At 10+ Corpus Ingredient Count, ..." → groups: ("10", "Corpus Ingredient Count")
_THRESHOLD = re.compile(r"[Aa]t (\d+)\+\s+([^,]+?)(?=\s*,)")

# "consume up to 20 Corpus Ingredient Count" → groups: ("20", "Corpus Ingredient")
_CONSUME = re.compile(
    r"consume\s+(?:up to\s+)?(\d+)\s+([\w ]+?)\s+Count", re.IGNORECASE
)

# "Gain +4 Corpus Ingredient Count" → groups: ("4", "Corpus Ingredient")
_GAIN_COUNT = re.compile(r"[Gg]ain\s+\+?(\d+)\s+([\w ]+?)\s+Count")

# "Spend 1 Tigermark Round" / "Spend 1 Scorch Propellant Ammo"
_SPEND_AMMO = re.compile(r"Spend\s+(\d+)\s+([^;]+)", re.IGNORECASE)

# "Consume 15 District 12 Fuel" / "Consume up to 25 District 12 Fuel"
_CONSUME_AMMO = re.compile(r"Consume\s+(?:up to\s+)?(\d+)\s+([^;]+)", re.IGNORECASE)

_AMMO_NAME_KWS = ("ammo", "round", "bullet", "fuel")

_UNBREAKABLE = re.compile(r"Unbreakable Coin", re.IGNORECASE)
_CRIT_BONUS = re.compile(r"\+(\d+)%\s+Damage on Critical Hit", re.IGNORECASE)

# "Final Power +1 for every 4 Bleed on target (max 3)"
_FINAL_PWR_SCALE = re.compile(
    r"Final Power\s+\+(\d+)\s+for every\s+(\d+)\s+([\w ]+?)\s+on target[^(]*\(max\s+(\d+)\)",
    re.IGNORECASE,
)

# "Clash Power +1 for every 3 Bleed on target (max 2)"
# "Coin Power +1 for every 3 Bleed Count on target (max 2)"
_STAT_SCALE_COUNT = re.compile(
    r"(Clash Power|Coin Power|Final Power|Base Power)\s+\+(\d+)\s+for every\s+(\d+)\s+"
    r"([\w ]+?)\s+(?:on target|Count)[^(]*\(max\s+(\d+)\)",
    re.IGNORECASE,
)

# "Clash Power +1 for every type of negative effect on target (max 2)"
_STAT_SCALE_NEG = re.compile(
    r"(Clash Power|Coin Power|Final Power|Base Power)\s+\+(\d+)\s+for every type of negative effect"
    r"[^(]*\(max\s+(\d+)\)",
    re.IGNORECASE,
)

# "Deal +5% damage for every type of negative effect on target (max 30%)"
_PERCENT_PER_NEG = re.compile(
    r"[Dd]eal\s+\+(\d+)%\s+damage for every type of negative effect[^(]*\(max\s+(\d+)%\)",
    re.IGNORECASE,
)

# "Deal +3% damage for every Corpus Ingredient Count consumed"
_PERCENT_PER_COUNT = re.compile(
    r"[Dd]eal\s+\+(\d+)%\s+damage for every\s+([\w ]+?)\s+consumed",
    re.IGNORECASE,
)

_CONSUME_CHARGE_CP = re.compile(
    r"[Cc]onsume\s+(\d+)\s+Charge Count[^;]*gain\s+\+(\d+)\s+Coin Power",
    re.IGNORECASE,
)
_AT_CHARGE_CP = re.compile(
    r"At\s+(\d+)\+\s+Charge[^;]*Coin Power\s+\+(\d+)",
    re.IGNORECASE,
)
_AT_CHARGE_CLASH = re.compile(
    r"At\s+(\d+)\+\s+Charge[^;]*Clash Power\s+\+(\d+)",
    re.IGNORECASE,
)
_CLASH_FROM_POTENCY = re.compile(
    r"Clash Power equal to Charge Potency[^()]*\(max\s+(\d+)\)",
    re.IGNORECASE,
)
_POTENCY_DAMAGE_PCT = re.compile(
    r"Charge Potency x (\d+)%[^()]*\(max (\d+)%\)",
    re.IGNORECASE,
)
_CHARGE_COIN_SCALING = re.compile(
    r"Consume up to (\d+) Charge Count to gain Coin Power[^;]*Charge Count consumed",
    re.IGNORECASE,
)
_OVERFLOW_CHARGE_DMG = re.compile(
    r"Charge Count past the Max Charge Count Cap[^;]*\+(\d+)% damage[^()]*\(max (\d+)%\)",
    re.IGNORECASE,
)
_DAMAGE_PER_SELF_RESOURCE = re.compile(
    r"Deal \+(\d+)% damage for every ([^;]+?) on self \(max (\d+)%\)",
    re.IGNORECASE,
)
_STAT_PER_SELF_RESOURCE = re.compile(
    r"(Atk Weight|Coin Power|Base Power|Clash Power) \+(\d+) for every (\d+) ([^;]+?) on self \(max (\d+)\)",
    re.IGNORECASE,
)
_HAS_STATE_SKILL_FLIP = re.compile(
    r"has (.+?), activate\s+'([^']+)' instead",
    re.IGNORECASE,
)
_ON_USE_GAIN_RESOURCE = re.compile(
    r"\[On Use\] Gain (\d+) (.+?)(?:\s*;|\s*$)",
    re.IGNORECASE,
)
_KILL_GAIN_RESOURCE = re.compile(
    r"kills the target, gain (\d+) (.+?)(?:\s*;|\s*$)",
    re.IGNORECASE,
)
_MOUNT_STATE = re.compile(r"mount (.+?)(?:\s*;|$)", re.IGNORECASE)
_MOUNT_SP_COST = re.compile(r"Lose (\d+) SP every time[^;]*mount", re.IGNORECASE)
_LOSE_STATE_TURN_END = re.compile(r"\[Turn End\][^;]*Lose (.+?)(?:\s*;|$)", re.IGNORECASE)
_GAIN_STATE_NEXT_TURN = re.compile(
    r"\[Combat Start\][^;]*gain (\d+) (.+?) next turn",
    re.IGNORECASE,
)
_UNIQUE_ARCHETYPE_EXCLUDED = frozenset({
    "Nails", "Fanatic",
    "Discard", "Insight", "Erudition",
    "Overcharge", "Unbreakable Coin", "Unfocused Volley",
})

_COIN_ROW = re.compile(r"^\|\s*(\d)\s*\|(.+)\|$")

# "loses Iron Maiden and gains **The Self Unbound — Flow State**"
_LOSE_GAIN = re.compile(
    r"loses\s+\*{0,2}([\w ]+?)\*{0,2}\s+and gains\s+\*{0,2}([^*(\n]+?)\*{0,2}"
    r"(?=\s*\(|\s*$|\n)",
    re.IGNORECASE,
)

# "Coin Power +1 for every 5 Poise Count (max 3)"
_POISE_TO_COINPWR = re.compile(
    r"Coin Power\s+\+(\d+)\s+for every\s+(\d+)\s+Poise Count[^(]*\(max\s+(\d+)\)",
    re.IGNORECASE,
)

# "On clash win, gain +1 Poise Count."
_CLASH_WIN_POISE = re.compile(r"clash win.*gain.*Poise", re.IGNORECASE)


# ---------------------------------------------------------------------------
# Core parsing helpers
# ---------------------------------------------------------------------------


def _parse_skill_block(skill_num: int, name: str, block_text: str) -> dict:
    """Parse one skill's text block into a structured dict."""
    lines = block_text.splitlines()

    base_power: int | None = None
    coin_power: str | None = None
    atk_weight: int | None = None

    on_use_effects: list[str] = []
    skill_bonuses: list[str] = []
    coin_effects: list[dict] = []
    conditions: list[str] = []
    resources_consumed: list[dict] = []
    resources_gained: list[dict] = []
    has_unbreakable = False
    crit_bonus: int | None = None
    damage_scales: list[str] = []

    # --- 1. Stats row ---
    after_header = False
    for line in lines:
        stripped = line.strip()
        if "| Base Power" in stripped or "| Offense Level" in stripped:
            after_header = True
            continue
        if after_header and "|---" in stripped:
            continue
        if after_header and stripped.startswith("|"):
            m = _STATS_DATA.match(stripped)
            if m:
                base_power = int(m.group(1))
                coin_power = m.group(2)
                atk_weight = int(m.group(3))
            after_header = False

    # --- 2. On-use effects (with continuation bullet lines) ---
    i = 0
    while i < len(lines):
        raw = lines[i]
        m = _ON_USE.match(raw)
        if m:
            effect = m.group(1).strip()
            # threshold check
            tm = _THRESHOLD.search(effect)
            if tm:
                conditions.append(f"At {tm.group(1)}+ {tm.group(2).strip()}")
            # resource consumed
            cm = _CONSUME.search(effect)
            if cm:
                resources_consumed.append(
                    {"amount": int(cm.group(1)), "resource": cm.group(2).strip()}
                )
            if _UNBREAKABLE.search(effect):
                has_unbreakable = True
            # gather continuation bullet lines (- item)
            segments = [effect]
            j = i + 1
            while j < len(lines) and lines[j].strip().startswith("- "):
                cont = lines[j].strip()[2:]
                if _UNBREAKABLE.search(cont):
                    has_unbreakable = True
                cm2 = _CONSUME.search(cont)
                if cm2:
                    resources_consumed.append(
                        {"amount": int(cm2.group(1)), "resource": cm2.group(2).strip()}
                    )
                segments.append(cont)
                j += 1
            on_use_effects.append(" / ".join(segments))
            i = j
            continue

        # Standalone bold lines — skill bonuses and trigger tags like **[On Kill]**
        stripped = raw.strip()
        if stripped.startswith("**"):
            cb = _CRIT_BONUS.search(stripped)
            if cb:
                crit_bonus = int(cb.group(1))
            else:
                clean = re.sub(r"\*+", "", stripped).strip()
                if clean and not clean.startswith("|") and not _OWNERSHIP_NOTE.match(clean):
                    if clean.startswith("[") and "]" in clean:
                        on_use_effects.append(clean)
                    elif "[[:Category:" not in clean and "[[" not in clean:
                        skill_bonuses.append(clean)
        i += 1

    # Wiki renderer may pack [On Use] clauses into one semicolon-separated bonus line
    for text in skill_bonuses + on_use_effects:
        for tm in _THRESHOLD.finditer(text):
            cond = f"At {tm.group(1)}+ {tm.group(2).strip().rstrip(':')}"
            if cond not in conditions:
                conditions.append(cond)
        for cm in _CONSUME.finditer(text):
            entry = {"amount": int(cm.group(1)), "resource": cm.group(2).strip()}
            if entry not in resources_consumed:
                resources_consumed.append(entry)
        if _UNBREAKABLE.search(text):
            has_unbreakable = True

    # --- 3. Coin effects table ---
    in_coin_table = False
    for line in lines:
        stripped = line.strip()
        if "| Coin |" in stripped or "| Coin|" in stripped:
            in_coin_table = True
            continue
        if in_coin_table and "|---" in stripped:
            continue
        if in_coin_table:
            if stripped.startswith("##") or stripped.startswith("---"):
                break
            if stripped.startswith("|"):
                m = _COIN_ROW.match(stripped)
                if m:
                    coin_num = int(m.group(1))
                    eff = m.group(2).strip()
                    coin_effects.append(
                        {
                            "coin": coin_num,
                            "effect": eff,
                            "cleaned_effect": clean_effect_text(eff),
                        }
                    )
                    gm = _GAIN_COUNT.search(eff)
                    if gm:
                        resources_gained.append(
                            {
                                "coin": coin_num,
                                "amount": int(gm.group(1)),
                                "resource": gm.group(2).strip(),
                            }
                        )

    # --- 4. Damage scale extraction from all effect text ---
    all_eff = (
        " ".join(on_use_effects)
        + " "
        + " ".join(skill_bonuses)
        + " "
        + " ".join(e["effect"] for e in coin_effects)
    )

    for m in _STAT_SCALE_NEG.finditer(all_eff):
        damage_scales.append(
            f"{m.group(1)} +{m.group(2)} per negative effect type (max +{m.group(3)})"
        )
    for m in _STAT_SCALE_COUNT.finditer(all_eff):
        damage_scales.append(
            f"{m.group(1)} +{m.group(2)} per {m.group(3)} {m.group(4)} (max +{m.group(5)})"
        )
    for m in _PERCENT_PER_NEG.finditer(all_eff):
        damage_scales.append(f"+{m.group(1)}% per negative effect type (max +{m.group(2)}%)")
    for m in _PERCENT_PER_COUNT.finditer(all_eff):
        damage_scales.append(f"+{m.group(1)}% per {m.group(2)} consumed")
    for m in _CONSUME_CHARGE_CP.finditer(all_eff):
        damage_scales.append(
            f"Consume {m.group(1)} Charge Count for +{m.group(2)} Coin Power"
        )
    for m in _AT_CHARGE_CP.finditer(all_eff):
        damage_scales.append(f"At {m.group(1)}+ Charge, Coin Power +{m.group(2)}")
    for m in _AT_CHARGE_CLASH.finditer(all_eff):
        damage_scales.append(f"At {m.group(1)}+ Charge, Clash Power +{m.group(2)}")
    cm = _CLASH_FROM_POTENCY.search(all_eff)
    if cm:
        damage_scales.append(f"Clash Power = Charge Potency (max +{cm.group(1)})")
    pm = _POTENCY_DAMAGE_PCT.search(all_eff)
    if pm:
        damage_scales.append(
            f"+{pm.group(1)}% damage per Charge Potency on final coin (max +{pm.group(2)}%)"
        )
    for m in _DAMAGE_PER_SELF_RESOURCE.finditer(all_eff):
        resource = m.group(2).strip()
        damage_scales.append(
            f"+{m.group(1)}% damage per {resource} (max +{m.group(3)}%)"
        )
    for m in _STAT_PER_SELF_RESOURCE.finditer(all_eff):
        damage_scales.append(
            f"{m.group(1)} +{m.group(2)} per {m.group(3)} {m.group(4).strip()} "
            f"(max +{m.group(5)})"
        )
    coin_scale = _CHARGE_COIN_SCALING.search(all_eff)
    if coin_scale:
        damage_scales.append(
            f"Final coin: consume up to {coin_scale.group(1)} Charge for matching Coin Power"
        )

    return {
        "skill_num": skill_num,
        "name": name,
        "base_power": base_power,
        "coin_power": coin_power,
        "atk_weight": atk_weight,
        "on_use_effects": on_use_effects,
        "skill_bonuses": skill_bonuses,
        "coin_effects": coin_effects,
        "conditions": conditions,
        "resources_consumed": resources_consumed,
        "resources_gained": resources_gained,
        "has_unbreakable": has_unbreakable,
        "crit_bonus": crit_bonus,
        "damage_scales": damage_scales,
    }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def _iter_skill_blocks(md_text: str):
    """Yield (skill_num, name, block_text, is_alternate) for every skill block."""
    matches = list(_SKILL_HEADER.finditer(md_text))
    section_starts = [m.start() for m in _SECTION_BOUNDARY.finditer(md_text)]
    seen: set[int] = set()
    for i, m in enumerate(matches):
        skill_num = int(m.group(1))
        name = m.group(2).strip()
        start = m.end()
        if i + 1 < len(matches):
            end = matches[i + 1].start()
        else:
            next_section = next((pos for pos in section_starts if pos > start), len(md_text))
            end = next_section
        is_alternate = skill_num in seen
        seen.add(skill_num)
        yield skill_num, name, md_text[start:end], is_alternate


def parse_skills(md_text: str) -> list[dict]:
    """
    Return the primary skill set (first S1, S2, S3 encountered).
    Identities with multiple states (e.g. Iron Maiden → Flow State) contain two
    skill sets; only the first occurrence of each skill number is returned.
    """
    if not md_text:
        return []
    primary: list[dict] = []
    for skill_num, name, block, is_alternate in _iter_skill_blocks(md_text):
        if not is_alternate:
            primary.append(_parse_skill_block(skill_num, name, block))
    return sorted(primary, key=lambda s: s["skill_num"])


def parse_all_skills(md_text: str) -> tuple[list[dict], list[dict]]:
    """
    Return (primary_skills, alternate_skills).
    Alternate skills are additional skill blocks for the same slot number
    (e.g. alternate states, Unclashable buff skills, post-transition variants).
    Each alternate dict includes an ``is_alternate=True`` flag.
    """
    if not md_text:
        return [], []
    primary: list[dict] = []
    alternates: list[dict] = []
    for skill_num, name, block, is_alternate in _iter_skill_blocks(md_text):
        parsed = _parse_skill_block(skill_num, name, block)
        parsed["is_alternate"] = is_alternate
        if is_alternate:
            alternates.append(parsed)
        else:
            primary.append(parsed)
    primary.sort(key=lambda s: s["skill_num"])
    return primary, alternates


def find_resource_loop(
    skills: list[dict], mechanic_profile: dict
) -> dict | None:
    """
    Detect a consumable resource loop: a unique mechanic that is gated by
    threshold conditions on multiple skills.

    Returns None for identities with no unique consumable resource (e.g. pure
    Poise-stackers or negative-effect scalers).
    """
    unique = mechanic_profile.get("unique_mechanics", {})
    if not unique:
        return None

    resource_name: str | None = None
    threshold: int | None = None
    max_consume: int | None = None
    payoff_skills: list[int] = []
    build_skills: list[int] = []

    for skill in skills:
        for cond in skill["conditions"]:
            for uname in unique:
                if uname in cond:
                    resource_name = uname
                    m = re.search(r"(\d+)\+", cond)
                    if m:
                        candidate = int(m.group(1))
                        threshold = min(threshold, candidate) if threshold is not None else candidate
                    if skill["skill_num"] not in payoff_skills:
                        payoff_skills.append(skill["skill_num"])
        for consumed in skill["resources_consumed"]:
            if resource_name and resource_name in consumed["resource"]:
                max_consume = max(max_consume or 0, consumed["amount"])
        for gained in skill["resources_gained"]:
            if resource_name and resource_name in gained["resource"]:
                if skill["skill_num"] not in build_skills:
                    build_skills.append(skill["skill_num"])

    if not resource_name:
        return None

    return {
        "resource": resource_name,
        "threshold": threshold,
        "max": max_consume,
        "build_skills": sorted(build_skills),
        "payoff_skills": sorted(payoff_skills),
    }


def _normalize_ammo_name(name: str) -> str:
    name = re.sub(r"\s+", " ", name.strip())
    name = re.split(r"\s+and\s+", name, maxsplit=1, flags=re.IGNORECASE)[0].strip()
    return name


def _is_ammo_resource(name: str) -> bool:
    lowered = name.lower()
    return any(kw in lowered for kw in _AMMO_NAME_KWS)


def _accumulate_ammo_spends(
    text: str,
    skill_num: int,
    spend_per_skill: dict[int, int],
    ammo_names: set[str],
) -> None:
    for pattern in (_SPEND_AMMO, _CONSUME_AMMO):
        for match in pattern.finditer(text):
            amount = int(match.group(1))
            name = _normalize_ammo_name(match.group(2))
            if not _is_ammo_resource(name):
                continue
            ammo_names.add(name)
            spend_per_skill[skill_num] += amount


def _ammo_display_label(ammo_names: set[str]) -> str:
    if len(ammo_names) == 1:
        return next(iter(ammo_names))
    if all("Tigermark" in name for name in ammo_names):
        return "Tigermark Rounds"
    if all("Ammo" in name for name in ammo_names):
        base = next(iter(ammo_names)).replace("Ammo", "").strip()
        return f"{base} Ammo".strip()
    return " / ".join(sorted(ammo_names))


def find_unique_ammo_economy(
    skills: list[dict],
    alternate_skills: list[dict] | None = None,
) -> dict | None:
    """
    Detect limited unique ammo spent on skills (e.g. Tigermark Round, District 12 Fuel).

    Matches both ``Spend N …`` coin flips and ``Consume N …`` / ``Consume up to N …``
    on coins or skill headers. Returns None when the kit does not spend ammo, or when
    every attack skill spends ammo equally with no cheaper skills to skip.
    """
    from collections import defaultdict

    all_skills = list(skills) + list(alternate_skills or [])
    spend_per_skill: dict[int, int] = defaultdict(int)
    ammo_names: set[str] = set()

    for skill in all_skills:
        skill_num = skill["skill_num"]
        for coin in skill.get("coin_effects", []):
            _accumulate_ammo_spends(coin.get("effect", ""), skill_num, spend_per_skill, ammo_names)
        skill_level = " ".join(
            skill.get("on_use_effects", []) + skill.get("skill_bonuses", [])
        )
        _accumulate_ammo_spends(skill_level, skill_num, spend_per_skill, ammo_names)

    if not ammo_names:
        return None

    primary_nums = {s["skill_num"] for s in skills}
    spending_skills = set(spend_per_skill)
    non_spending = sorted(primary_nums - spending_skills)

    if len(spending_skills) >= 2:
        premium_skill = max(spend_per_skill, key=lambda sn: (spend_per_skill[sn], sn))
        budget_skills = [
            sn
            for sn in sorted(spend_per_skill)
            if sn != premium_skill and spend_per_skill[sn] < spend_per_skill[premium_skill]
        ]
        if not budget_skills:
            budget_skills = [sn for sn in sorted(spend_per_skill) if sn != premium_skill]
    elif len(spending_skills) == 1 and non_spending:
        premium_skill = next(iter(spending_skills))
        budget_skills = non_spending
    else:
        return None

    return {
        "ammo_label": _ammo_display_label(ammo_names),
        "premium_skill": premium_skill,
        "budget_skills": budget_skills,
        "spend_per_skill": dict(spend_per_skill),
    }


def find_state_transition(md_text: str) -> dict | None:
    """
    Detect Iron Maiden → Flow State type passive-triggered transitions.
    Returns None if no transition is found.
    """
    m = _LOSE_GAIN.search(md_text)
    if not m:
        return None

    from_state = m.group(1).strip()
    to_state = m.group(2).strip().rstrip("—").strip()

    # Infer the trigger from surrounding context
    idx = m.start()
    ctx = md_text[max(0, idx - 300) : idx + 100]
    trigger = "passive condition"
    if "Artwork: Fascia" in ctx:
        trigger = "reaching Artwork: Fascia tier 2 via the combat passive"
    elif "Stagger" in ctx:
        trigger = "a stagger-based passive"

    effect = ""
    if "Self Unbound" in to_state or "Flow State" in md_text[idx : idx + 60]:
        effect = "Unlocks Evade/Counter defensive skills and an upgraded attack skill set."

    return {
        "from_state": from_state,
        "to_state": to_state,
        "trigger": trigger,
        "effect": effect,
    }


def find_damage_conditions(skills: list[dict]) -> list[str]:
    """Unique damage-scaling conditions across all skills, for use in core_idea."""
    seen: set[str] = set()
    result: list[str] = []
    for skill in skills:
        for ds in skill["damage_scales"]:
            if ds not in seen:
                seen.add(ds)
                result.append(ds)
    return result


_RES2_PASSIVE = re.compile(r"\*\*\(×2\s*Res\)\*\*")
_RES_REQ_LINE = re.compile(r"^\*\*\(×\d+\s*Res\)\*\*\s*$")
_ALLY_FACING_PASSIVE_RE = re.compile(
    r"\b(?:\d+\s+)?all(?:y|ies)\b|\bother\s+\w+\s+allies|"
    r"deployed identity|deployment order",
    re.IGNORECASE,
)


def _split_passive_blocks(section_text: str) -> list[str]:
    blocks: list[str] = []
    current: list[str] = []
    for line in section_text.splitlines():
        if line.startswith("### "):
            if current:
                blocks.append("\n".join(current).strip())
            current = [line]
        elif current:
            current.append(line)
    if current:
        blocks.append("\n".join(current).strip())
    return blocks


def _strip_res_req_markers(block: str) -> str:
    lines = [ln for ln in block.splitlines() if not _RES_REQ_LINE.match(ln.strip())]
    return "\n".join(lines).strip()


def _partition_res2_passives_from_support(support_text: str) -> tuple[str, str]:
    """×2 Res passives are combat buffs — move them out of Support Passive."""
    combat_blocks: list[str] = []
    support_blocks: list[str] = []
    for block in _split_passive_blocks(support_text):
        if _RES2_PASSIVE.search(block):
            combat_blocks.append(_strip_res_req_markers(block))
        else:
            support_blocks.append(block)
    return "\n\n".join(combat_blocks).strip(), "\n\n".join(support_blocks).strip()


def _merge_passive_sections(*parts: str) -> str:
    return "\n\n".join(p.strip() for p in parts if p and p.strip()).strip()


def select_primary_support_passive(support_text: str) -> str:
    """When multiple passives share ## Support Passive, pick the ally-facing one."""
    blocks = _split_passive_blocks(support_text)
    if len(blocks) <= 1:
        return support_text.strip()

    def score(block: str) -> tuple[int, int]:
        ally = bool(_ALLY_FACING_PASSIVE_RE.search(block))
        return ((10 if ally else 0), len(block))

    return max(blocks, key=score)


def parse_passives_text(md_text: str) -> tuple[str, str]:
    """Return (combat_passives_text, support_passive_text)."""
    sections: dict[str, str] = {}
    current: str | None = None
    buf: list[str] = []

    for line in md_text.splitlines():
        if line.startswith("## Combat Passives"):
            if current and buf:
                sections[current] = "\n".join(buf)
            current, buf = "combat", []
        elif line.startswith("## Support Passive"):
            if current and buf:
                sections[current] = "\n".join(buf)
            current, buf = "support", []
        elif line.startswith("## ") and current:
            if buf:
                sections[current] = "\n".join(buf)
            current = None
        elif current is not None:
            buf.append(line)

    if current and buf:
        sections[current] = "\n".join(buf)

    combat_extra, support_remaining = _partition_res2_passives_from_support(
        sections.get("support", "")
    )
    combat = _merge_passive_sections(sections.get("combat", ""), combat_extra)
    support = select_primary_support_passive(support_remaining)
    return combat, support


_ALLY_COMBO = re.compile(
    r"Before\s+([\w\s:.']+?)\s+uses\s+(?:its\s+)?[Ss]kill\s+(\d+)",
    re.IGNORECASE,
)

_RESONANCE_RE = re.compile(r"\bReson\.", re.IGNORECASE)
_TRAIT_COND_RE = re.compile(r"<>")


def detect_resonance_dependency(text: str) -> bool:
    """True when kit text scales off team Resonance (same-trait ally count)."""
    return bool(_RESONANCE_RE.search(text))


def detect_trait_conditional(text: str) -> bool:
    """True when passives use <> wiki placeholder for ally trait conditions."""
    return bool(_TRAIT_COND_RE.search(text))


def find_ally_combo(combat_text: str) -> dict | None:
    """Detect cross-identity passive triggers (e.g. 'Before Faust uses Skill 3...')."""
    m = _ALLY_COMBO.search(combat_text)
    if not m:
        return None
    ally_name = m.group(1).strip().rstrip(",")
    skill_num = int(m.group(2))
    after = combat_text[m.end() : m.end() + 300]
    skill_m = re.search(r'uses\s+"([^"]+)"', after, re.I)
    fired_skill = f'"{skill_m.group(1)}"' if skill_m else "a special skill"
    effect_m = re.search(r"\[On Use\][^;]+|Apply \d+ \w+", after, re.I)
    effect_note = effect_m.group(0).strip() if effect_m else ""
    return {
        "ally": ally_name,
        "trigger_skill": skill_num,
        "fired_skill": fired_skill,
        "effect_note": effect_note,
    }


def parse_combat_passive_notes(md_text: str) -> list[dict]:
    """Extract combat passive names and key mechanic lines (up to 4 per passive)."""
    combat_text, _ = parse_passives_text(md_text)
    if not combat_text.strip():
        return []

    notes: list[dict] = []
    blocks = re.split(r"^### ", combat_text, flags=re.MULTILINE)
    for block in blocks:
        block = block.strip()
        if not block:
            continue
        lines = block.splitlines()
        name = lines[0].strip()
        mechanic_lines: list[str] = []
        for line in lines[1:]:
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            plain = re.sub(r"\*+", "", stripped).strip(" -")
            if _OWNERSHIP_NOTE.match(plain) or re.search(r"\(×\d+", plain):
                continue
            for clause in re.split(r"\s*;+\s*", plain):
                clause = clause.strip(" -")
                if clause and len(clause) > 8 and "[[:Category:" not in clause:
                    mechanic_lines.append(clause)
        if mechanic_lines:
            notes.append({
                "name": name,
                "note": mechanic_lines[0],
                "mechanic_lines": mechanic_lines[:5],
            })
    return notes


_DEFENSE_SKILL_SECTION = re.compile(
    r"^## Defense Skills\s*\n(.*?)(?=^## |\Z)",
    re.MULTILINE | re.DOTALL,
)
_DEFENSE_SKILL_HEADER = re.compile(r"^### ((?:Evade|Counter|Guard):.+)", re.MULTILINE)
_DEFENSE_NOTABLE_KWS = re.compile(
    r"Turn End|Combat Start|Ready to Loose|Target Aim|Arrow.*Shi|Shield|Liferender|"
    r"Clashable|gain.*State|gain.*Aim|Ammo|Hardblood|Bloodfeast|Overcharge|"
    r"Serpent Arm|Defensive Stance|Strider|list of Skills|District 12 Fuel|"
    r"cannot be Staggered|as Counter|Tear — sharpened|lose \d+ SP",
    re.IGNORECASE,
)
_USE_AS_COUNTER = re.compile(
    r"use\s+['\"]([^'\"]+)['\"](?:\s+or\s+['\"]([^'\"]+)['\"])?\s+as\s+Counter",
    re.IGNORECASE,
)
_QUEUE_SKILL = re.compile(
    r"Add\s+(?:\d+\s+)?(.+?)\s+to the list of Skills",
    re.IGNORECASE,
)
_DEFENSE_COMBAT_START_GAIN = re.compile(
    r"\[Combat Start\][^;]*?\bGain\s+(\d+)\s+([^;]+?)(?:\s+next turn|\s+for the turn|\s*\(|;|$)",
    re.IGNORECASE,
)
_SNIPE_REPLACE = re.compile(
    r'Ready to Loose state, replace.*?with\s+"([^"]+)"',
    re.IGNORECASE,
)
_EQUIPPED_DEFENSE_UNLOCK = re.compile(
    r"equipped Defense Skills for the first time",
    re.IGNORECASE,
)


def _extract_defense_section(md_text: str) -> str:
    m = _DEFENSE_SKILL_SECTION.search(md_text)
    return m.group(1) if m else ""


def _extract_defense_clauses(block_lines: list[str]) -> list[str]:
    """Pull mechanic clauses from one ### Evade/Counter/Guard block."""
    mechanic_lines: list[str] = []
    for line in block_lines[1:]:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.startswith("|"):
            continue
        plain = re.sub(r"\*+", "", stripped).strip(" -")
        if _OWNERSHIP_NOTE.match(plain) or re.search(r"\(×\d+", plain):
            continue
        for clause in re.split(r"\s*;+\s*", plain):
            clause = clause.strip(" -")
            if not clause or len(clause) < 12:
                continue
            if "[[:Category:" in clause:
                continue
            lead = clause.lstrip("- ").lstrip()
            if not lead:
                continue
            if not (lead[0] in "[(0123456789" or lead[0].isupper()):
                continue
            mechanic_lines.append(clause)
    return mechanic_lines


def parse_all_defense_blocks(md_text: str) -> list[dict]:
    """Return every Evade/Counter/Guard block with parsed mechanic clauses."""
    defense_text = _extract_defense_section(md_text)
    if not defense_text.strip():
        return []

    blocks: list[dict] = []
    for block in re.split(r"^### ", defense_text, flags=re.MULTILINE):
        block = block.strip()
        if not block:
            continue
        lines = block.splitlines()
        header = lines[0].strip()
        if not re.match(r"(Evade|Counter|Guard):", header, re.IGNORECASE):
            continue
        clauses = _extract_defense_clauses(lines)
        if not clauses:
            continue
        blocks.append({
            "name": header,
            "clauses": clauses,
            "text": " ; ".join(clauses),
        })
    return blocks


def parse_defense_skill_notes(md_text: str) -> list[dict]:
    """
    Extract defense skill (Evade/Counter/Guard) names and notable mechanic lines.

    Only returns entries for defense skills that carry game-relevant mechanics
    (state gating, stack building, resource grants, unique triggers).
    Plain 'draw one card' / 'gain Poise on evade' counters are skipped.
    """
    notes: list[dict] = []
    for block in parse_all_defense_blocks(md_text):
        clauses = block["clauses"]
        is_notable = len(clauses) >= 3 or bool(
            _DEFENSE_NOTABLE_KWS.search(block["text"])
        )
        if is_notable:
            notes.append({
                "name": block["name"],
                "note": clauses[0],
                "mechanic_lines": clauses[:6],
            })
    return notes


def find_defense_archetype(
    md_text: str,
    alternate_skills: list[dict] | None = None,
    combat_text: str = "",
) -> dict | None:
    """
    Detect kits whose defense slot unlocks alternate skills, major buffs, or
    attack-skill counters (Shi Faust snipe, Middle Counter S3, Thumb reload, etc.).
    """
    blocks = parse_all_defense_blocks(md_text)
    if not blocks and not combat_text:
        return None

    alt_names = [s.get("name", "") for s in (alternate_skills or []) if s.get("name")]
    combined_defense = " ; ".join(b["text"] for b in blocks)
    tips: list[str] = []
    kind: str | None = None
    payoff: str | None = None
    defense_name = blocks[0]["name"] if blocks else ""

    # Snipe setup: Evade builds aim → combat passive fires alternate at Combat Start
    snipe_m = _SNIPE_REPLACE.search(combat_text)
    if snipe_m and _DEFENSE_NOTABLE_KWS.search(
        combined_defense + " " + combat_text
    ):
        payoff = snipe_m.group(1)
        kind = "snipe_setup"
        defense_name = next(
            (b["name"] for b in blocks if "Evade" in b["name"]),
            defense_name,
        )
        tips.append(
            f"Defense-first rotation — use **{defense_name}** to enter Ready to Loose "
            f"and stack Target Aim without attacking; **Snipe - Archery** then fires "
            f"**{payoff}** at Combat Start (up to +444% crit damage at max aim)."
        )
        if "did not use an Attack Skill" in combined_defense:
            tips.append(
                "On turns you Evade without attacking, you still gain Target Aim — "
                "plan defense turns as setup, not dead actions."
            )

    # Counter fires an attack skill (Middle Nursefather, etc.)
    if kind is None:
        for block in blocks:
            counter_m = _USE_AS_COUNTER.search(block["text"])
            if not counter_m:
                continue
            skills_fired = [g for g in counter_m.groups() if g]
            payoff = " or ".join(skills_fired)
            kind = "counter_skill"
            defense_name = block["name"]
            cond = ""
            if "Envy A-Reson" in block["text"]:
                cond = " at 6+ Envy Resonance"
            tips.append(
                f"At Combat Start{cond}, **{defense_name}** can fire **{payoff}** "
                f"as a Counter instead of a normal defensive clash — the defense slot "
                f"is your burst tool, not just protection."
            )
            break

    # Guard queues a skill or removes stagger (W Corp CCA Heathcliff)
    if kind is None:
        for block in blocks:
            queue_m = _QUEUE_SKILL.search(block["text"])
            if queue_m:
                queued = queue_m.group(1).strip()
                kind = "skill_queue"
                defense_name = block["name"]
                tips.append(
                    f"**{defense_name}** queues **{queued}** for the next turn when "
                    f"conditions are met — use the guard slot to set up a high-impact "
                    f"attack on the following turn."
                )
                if "Remove this unit's first Stagger Threshold" in block["text"]:
                    tips.append(
                        "That guard use also removes the first Stagger Threshold once "
                        "per encounter — valuable when you need to stay on the field."
                    )
                break
            if "Overcharge" in block["text"] and "Stagger Threshold" in block["text"]:
                kind = "skill_queue"
                defense_name = block["name"]
                tips.append(
                    f"**{defense_name}** grants Overcharge and can remove a Stagger "
                    f"Threshold — treat the guard slot as a setup turn for a stronger "
                    f"follow-up."
                )
                break

    # First defense equip unlocks upgraded kit (Thumb Capo)
    if _EQUIPPED_DEFENSE_UNLOCK.search(combat_text):
        unlock_tip = (
            "Equipping a defense skill for the first time this encounter reloads "
            "Savage Tigermark Round and unlocks the upgraded skill set — plan when "
            "you switch to defense to trigger the reload."
        )
        if kind is None:
            kind = "equip_unlock"
            tips.append(unlock_tip)
        elif kind != "equip_unlock" and unlock_tip not in tips:
            tips.append(unlock_tip)

    # Guard/Counter grants a major Combat Start buff
    if kind is None:
        for block in blocks:
            gain_m = _DEFENSE_COMBAT_START_GAIN.search(block["text"])
            if not gain_m:
                continue
            amount, buff = gain_m.group(1), gain_m.group(2).strip().rstrip(".")
            # Skip tiny or generic gains
            if int(amount) < 2 and "Fuel" not in buff and "Stance" not in buff:
                continue
            if "Aggro" in buff:
                continue
            kind = "guard_buff"
            defense_name = block["name"]
            payoff = buff
            tips.append(
                f"**{defense_name}** grants {amount} **{buff}** at Combat Start — "
                f"use the defense slot to prep buffs before your attack chain."
            )
            break

    # Power counter (Blade Lineage Mentor — stagger immunity + scaling)
    if kind is None:
        for block in blocks:
            if not block["name"].lower().startswith("counter:"):
                continue
            text = block["text"]
            if "cannot be Staggered" not in text:
                continue
            if not re.search(r"deal\s+\+\d+%\s+damage", text, re.I):
                continue
            kind = "power_counter"
            defense_name = block["name"]
            tips.append(
                f"**{defense_name}** prevents Stagger during the clash and scales "
                f"damage with Poise and missing HP — commit it as a finisher, not "
                f"passive protection."
            )
            break

    if not tips:
        return None

    return {
        "kind": kind or "defense_setup",
        "defense_name": defense_name,
        "payoff": payoff,
        "tips": tips[:3],
    }


_MINUS_SP_GATE = re.compile(
    r"less than 0 SP|Minus Coin Skills|Uses Minus Coin",
    re.IGNORECASE,
)
_TURN_END_SP_DRAIN = re.compile(r"\[Turn End\].*?\blose\s+\d+\s+SP", re.IGNORECASE)
_SP_THRESHOLD_BONUS = re.compile(r"At (-\d+) or less SP", re.IGNORECASE)


def _coin_power_int(coin_power: str | None) -> int | None:
    if not coin_power:
        return None
    cleaned = coin_power.replace(" ", "").lstrip("+")
    try:
        return int(cleaned)
    except ValueError:
        return None


def find_negative_coin_archetype(
    md_text: str,
    alternate_skills: list[dict] | None,
    combat_text: str,
    support_text: str = "",
) -> dict | None:
    """
    Detect SP-gated Minus Coin kits (e.g. Sword Sharpened with Tears Rodion).

    These identities swap to high-Base-Power minus-coin alternates below 0 SP and
    often need deliberate defense turns to drain SP first.
    """
    alts = alternate_skills or []
    minus_skills = [
        s for s in alts
        if (_cp := _coin_power_int(s.get("coin_power"))) is not None and _cp < 0
    ]
    if len(minus_skills) < 2:
        return None
    if not _MINUS_SP_GATE.search(combat_text):
        return None

    blocks = parse_all_defense_blocks(md_text)
    defense_drains_sp = any(_TURN_END_SP_DRAIN.search(b["text"]) for b in blocks)
    full_passive_text = f"{combat_text} {support_text}"
    sp_thresholds = sorted(
        {int(m.group(1)) for m in _SP_THRESHOLD_BONUS.finditer(full_passive_text)}
    )

    blessing_label = "Blessing" if "Blessing" in combat_text else "positive SP"
    despair_label = "Despair" if "Despair" in combat_text else "negative SP"
    minus_names = [s["name"] for s in minus_skills]
    tips: list[str] = []

    alt_preview = ", ".join(minus_names[:2])
    if len(minus_names) > 2:
        alt_preview += ", …"

    tips.append(
        f"**Minus Coin kit** — at 0+ SP you run **{blessing_label}** Plus Coin skills; "
        f"below 0 SP you swap to **{despair_label}** Minus Coin alternates "
        f"({alt_preview}) with much higher Base Power."
    )

    if defense_drains_sp and blocks:
        def_label = " / ".join(b["name"] for b in blocks[:2])
        tips.append(
            f"Spend the opening turns on **{def_label}** — both grant Deep Tears on "
            f"use and drain SP at Turn End to build Tear-sharpened stacks, pushing "
            f"you into **{despair_label}** where the real damage lives."
        )
    else:
        tips.append(
            f"Deliberately drain SP with Minus Coin skills and avoid SP healing until "
            f"you are in **{despair_label}** — missing SP adds up to +20% damage on "
            f"Base Skills."
        )

    if sp_thresholds:
        shallow = max(sp_thresholds)  # e.g. -15 (least negative threshold)
        deep = min(sp_thresholds)  # e.g. -30
        bonus = (
            f"Final Power to allies' Minus Coin skills at **{shallow} SP**"
        )
        if deep < shallow:
            bonus += f" (+15% damage at **{deep} SP**)"
        tips.append(
            f"Support passive adds {bonus} — plan to stay deeply negative once setup is done."
        )
    elif any("Deep Tears" in (s.get("name") or "") for s in alts) or "Deep Tears" in combat_text:
        tips.append(
            "Build Deep Tears during setup, then cash out with Despair Skill 3 "
            "(consumes up to 20 stacks for up to +60% damage)."
        )

    return {
        "kind": "negative_coin",
        "blessing_label": blessing_label,
        "despair_label": despair_label,
        "minus_skills": minus_names,
        "sp_thresholds": sp_thresholds,
        "defense_drains_sp": defense_drains_sp,
        "tips": tips[:3],
    }


_NAILS_INFLICT = re.compile(r"\bInflict\s+\+?\d+\s+Nails\b", re.IGNORECASE)
_NAILS_THRESHOLD = re.compile(
    r"(?:have|with|at|targets?\s+that\s+have)\s+(\d+)\+\s+Nails|(\d+)\+\s+Nails",
    re.IGNORECASE,
)
_NAILS_PASSIVE_TREMOR = re.compile(
    r"target has Nails.*?(?:Tremor|inflict \+?\d+ Tremor)",
    re.IGNORECASE | re.DOTALL,
)
_FANATIC_NAILS = re.compile(r"Fanatic.*?inflict \+?\d+ Nails", re.IGNORECASE)
_TREMOR_BURST = re.compile(r"Trigger Tremor Burst", re.IGNORECASE)


def find_nails_archetype(
    md_text: str,
    combat_text: str = "",
    skills: list[dict] | None = None,
) -> dict | None:
    """
    N Corp. Fanatic kits that stack Nails (unique Bleed) toward threshold payoffs,
    often paired with Tremor Burst / debuff setup (Mittelhammer Don Quixote).
    """
    combined = f"{md_text}\n{combat_text}"
    inflict_count = len(_NAILS_INFLICT.findall(combined))
    if inflict_count == 0 and "Nails" not in combined:
        return None

    threshold = 5
    tm = _NAILS_THRESHOLD.search(combined)
    if tm:
        threshold = int(next(g for g in tm.groups() if g))

    has_passive_link = bool(_NAILS_PASSIVE_TREMOR.search(combined))
    has_fanatic = bool(_FANATIC_NAILS.search(combined))
    has_burst = bool(_TREMOR_BURST.search(combined))

    if inflict_count < 2 and not (has_passive_link and has_burst):
        return None

    setup_skills: list[str] = []
    payoff_skill = ""
    payoff_note = ""
    burst_skill = ""
    damage_skill = ""
    debuff_skill = ""

    for skill in skills or []:
        name = skill.get("name", "")
        sn = skill.get("skill_num")
        label = f"S{sn}" if sn else name
        eff_text = " ".join(
            e.get("effect", "") for e in skill.get("coin_effects", [])
        ) + " " + " ".join(skill.get("on_use_effects", []))
        if _NAILS_INFLICT.search(eff_text):
            setup_skills.append(label)
        if _TREMOR_BURST.search(eff_text):
            burst_skill = name or label
        if _NAILS_THRESHOLD.search(eff_text) and "+20%" in eff_text:
            damage_skill = name or label
        if _NAILS_THRESHOLD.search(eff_text) and (
            "Paralyze" in eff_text or "Attack Power Down" in eff_text
        ):
            debuff_skill = name or label

    payoff_skill = burst_skill or damage_skill or debuff_skill
    if burst_skill and damage_skill == burst_skill:
        payoff_note = f"+20% damage at {threshold}+ Nails"
    elif burst_skill:
        payoff_note = "Tremor Burst payoff"
    elif damage_skill:
        payoff_note = f"+20% damage at {threshold}+ Nails"
    elif debuff_skill:
        payoff_note = f"debuffs at {threshold}+ Nails on Heads"

    tips: list[str] = []
    setup_str = " and ".join(setup_skills[:2]) if setup_skills else "early skills"

    tips.append(
        f"**Nails setup** — use {setup_str} to stack **Nails** (unique Bleed) on the "
        f"target before the payoff; Nails also feed Bleed damage each turn."
    )

    if payoff_skill:
        burst_part = (
            " triggers **Tremor Burst** and"
            if has_burst and payoff_skill == burst_skill
            else ""
        )
        bonus = f" ({payoff_note})" if payoff_note else f" at **{threshold}+ Nails**"
        tips.append(
            f"Cash out with **{payoff_skill}** —{burst_part} deals bonus damage{bonus}; "
            f"do not fire it until the Nails threshold is met."
        )

    if has_passive_link:
        passive_tip = (
            "Combat passive adds **Tremor Count** whenever the target already has "
            "**Nails** — each Nail-applying hit snowballs Tremor for Burst payoffs."
        )
        if has_fanatic:
            passive_tip += " In **Fanatic** state she also inflicts extra Nails per hit."
        tips.append(passive_tip)
    elif has_fanatic:
        tips.append(
            "Stay in or reach **Fanatic** state for bonus Nails on hit — "
            "pair with low-SP Fanatic allies for zealotry passives."
        )

    return {
        "kind": "nails_setup",
        "threshold": threshold,
        "setup_skills": setup_skills,
        "payoff_skill": payoff_skill,
        "has_tremor_burst": has_burst,
        "has_fanatic": has_fanatic,
        "tips": tips[:3],
        "setup_summary": (
            f"Stack **Nails** to **{threshold}+** on the target, then burst with "
            f"**{payoff_skill or 'the payoff skill'}**"
            + (" and Tremor Burst" if has_burst else "")
            + "."
        ),
    }


_UNBREAKABLE_POTENCY = re.compile(
    r"(\d+)\+\s+Charge Potency[^;]*Unbreakable Coin",
    re.IGNORECASE,
)


def find_charge_archetype(
    skills: list[dict],
    combat_text: str = "",
    mechanic_profile: dict | None = None,
) -> dict | None:
    """
    Kits where Charge Count and Charge Potency severely buff skills
    (W Corp. L4 Cleanup Agent Heathcliff, etc.).
    """
    profile = mechanic_profile or {}
    primary = profile.get("primary_mechanics", [])
    charge_mentions = profile.get("status_effects", {}).get("Charge", 0)
    if "Charge" not in primary and charge_mentions < 12:
        return None

    combined = combat_text
    for skill in skills:
        combined += " " + " ".join(skill.get("on_use_effects", []))
        combined += " " + " ".join(skill.get("skill_bonuses", []))
        combined += " " + " ".join(skill.get("damage_scales", []))
        combined += " " + " ".join(e.get("effect", "") for e in skill.get("coin_effects", []))

    if not re.search(r"Charge", combined, re.I):
        return None

    signals = 0
    tips: list[str] = [
        "**Charge Count** caps at **20** — build with lighter skills, dump stacks on "
        "empowered coins, then ramp back up for the next cycle."
    ]
    s3_name = next((s["name"] for s in skills if s.get("skill_num") == 3), "S3")

    consume_matches = _CONSUME_CHARGE_CP.findall(combined)
    big_consume = max((int(amt), int(cp)) for amt, cp in consume_matches) if consume_matches else None
    if big_consume and big_consume[1] >= 3:
        signals += 2
        tips.append(
            f"When ready, spend **{big_consume[0]}** stacks on **{s3_name}** for "
            f"**+{big_consume[1]} Coin Power**, then start building again."
        )

    cm = _CLASH_FROM_POTENCY.search(combined)
    if cm:
        signals += 1
        tips.append(
            f"**Charge Potency** adds up to **+{cm.group(1)} Clash Power** on "
            f"**{s3_name}** — higher Potency tiers matter on the spend turn."
        )

    um = _UNBREAKABLE_POTENCY.search(combined)
    if um:
        signals += 1
        tips.append(
            f"At **{um.group(1)}+ Charge Potency** (or below 50% HP), **{s3_name}** "
            f"converts all coins to **Unbreakable**."
        )

    pm = _POTENCY_DAMAGE_PCT.search(combined)
    if pm:
        signals += 1
        tips.append(
            f"The final coin deals bonus Slash damage equal to **Charge Potency × {pm.group(1)}%** "
            f"(max **{pm.group(2)}%**) — stack Potency before the spend flip."
        )

    coin_scale = _CHARGE_COIN_SCALING.search(combined)
    if coin_scale:
        signals += 1
        tips.append(
            f"**{s3_name}**'s last coin can consume up to **{coin_scale.group(1)} Charge Count** "
            f"for matching **Coin Power** — align the dump with your highest stack turn."
        )

    overflow = _OVERFLOW_CHARGE_DMG.search(combined)
    if overflow:
        signals += 1
        tips.append(
            f"Overflowing past the Charge Count cap adds **+{overflow.group(1)}% damage per stack** "
            f"(max **+{overflow.group(2)}%**) — intentional overcap spikes spend turns."
        )

    if _AT_CHARGE_CP.search(combined):
        signals += 1

    clash_at = _AT_CHARGE_CLASH.findall(combined)
    if clash_at:
        signals += 1
        th, cp = max((int(a), int(b)) for a, b in clash_at)
        tips.append(
            f"At **{th}+ Charge Count**, **{s3_name}** gains **+{cp} Clash Power** — "
            f"build stacks before the finisher."
        )

    if any("charge" in c.lower() for s in skills for c in s.get("conditions", [])):
        signals += 1

    min_signals = 1 if "Charge" in primary else 2
    if signals < min_signals:
        return None

    if len(tips) == 1:
        tips.append(
            "Stack **Charge Count** before offensive skills — this kit checks Charge "
            "and consumes stacks for large Coin Power and Clash Power spikes."
        )

    setup_summary = (
        f"**Charge** cycle — build Count toward **20**, spend on empowered skills "
        f"(often **{s3_name}**), then rebuild for the next window."
    )

    return {
        "kind": "charge_scaling",
        "payoff_skill": s3_name,
        "tips": tips[:4],
        "setup_summary": setup_summary,
    }


def _leading_unique_mechanics(mechanic_profile: dict | None) -> list[tuple[str, int]]:
    """Top identity-specific resources from mechanic_profile, excluding handled archetypes."""
    from limbus_guides.ingestion.unique_mechanics_registry import _NON_RESOURCE_KEY_STATUS
    from limbus_guides.nlp.mechanics import STAT_MODIFIERS, STATUS_EFFECTS

    profile = mechanic_profile or {}
    unique = profile.get("unique_mechanics", {})
    primary = profile.get("primary_mechanics", [])
    key_fx = profile.get("key_status_effects", [])
    excluded = (
        _UNIQUE_ARCHETYPE_EXCLUDED
        | frozenset(STATUS_EFFECTS)
        | frozenset(STAT_MODIFIERS)
        | _NON_RESOURCE_KEY_STATUS
    )
    seen: set[str] = set()
    candidates: list[tuple[str, int]] = []

    for name in key_fx:
        if name in excluded or name in seen:
            continue
        candidates.append((name, unique.get(name, 8)))
        seen.add(name)

    for name in primary:
        if name in excluded or name not in unique or unique[name] < 3:
            continue
        if name not in seen:
            candidates.append((name, unique[name]))
            seen.add(name)

    for name, count in sorted(unique.items(), key=lambda x: -x[1]):
        if name in seen or name in excluded or count < 4:
            continue
        candidates.append((name, count))
        seen.add(name)

    candidates.sort(key=lambda x: -x[1])
    return candidates[:3]


def _resource_matches_mechanic(resource: str, mechanic: str) -> bool:
    res, mech = resource.strip().lower(), mechanic.lower()
    return mech in res or res in mech


def find_unique_mechanics_archetype(
    md_text: str,
    combat_text: str = "",
    skills: list[dict] | None = None,
    alternate_skills: list[dict] | None = None,
    mechanic_profile: dict | None = None,
) -> dict | None:
    """
    Kits whose guide narrative should lead with identity-specific resources
    (from mechanic_profile.unique_mechanics) rather than a sin-keyword alone.
    """
    leading = _leading_unique_mechanics(mechanic_profile)
    if not leading:
        return None

    mechanic_names = [name for name, _ in leading[:2]]
    combined = f"{md_text}\n{combat_text}"
    all_skills = list(skills or []) + list(alternate_skills or [])

    signals = 0
    stack_gains: dict[str, dict[str, tuple[int, str]]] = {}
    damage_scales: list[tuple[int, str, int, str]] = []
    stat_scales: list[tuple[str, int, int, str, int]] = []

    for skill in all_skills:
        skill_name = skill.get("name", "S3")
        text = " ".join(skill.get("on_use_effects", []))
        for m in _ON_USE_GAIN_RESOURCE.finditer(text):
            resource = m.group(2).strip()
            if not any(_resource_matches_mechanic(resource, n) for n in mechanic_names):
                continue
            key = next(n for n in mechanic_names if _resource_matches_mechanic(resource, n))
            stack_gains.setdefault(key, {})["use"] = (int(m.group(1)), skill_name)
            signals += 1
        for m in _KILL_GAIN_RESOURCE.finditer(text):
            resource = m.group(2).strip()
            if not any(_resource_matches_mechanic(resource, n) for n in mechanic_names):
                continue
            key = next(n for n in mechanic_names if _resource_matches_mechanic(resource, n))
            stack_gains.setdefault(key, {})["kill"] = (int(m.group(1)), skill_name)
            signals += 1
        for m in _DAMAGE_PER_SELF_RESOURCE.finditer(text):
            resource = m.group(2).strip()
            if any(_resource_matches_mechanic(resource, n) for n in mechanic_names):
                damage_scales.append(
                    (int(m.group(1)), resource, int(m.group(3)), skill_name)
                )
                signals += 1
        for m in _STAT_PER_SELF_RESOURCE.finditer(text):
            resource = m.group(4).strip()
            if any(_resource_matches_mechanic(resource, n) for n in mechanic_names):
                stat_scales.append(
                    (m.group(1), int(m.group(2)), int(m.group(3)), resource, int(m.group(5)))
                )
                signals += 1

    flip = _HAS_STATE_SKILL_FLIP.search(combined)
    if flip and any(
        _resource_matches_mechanic(flip.group(1).strip(), n) for n in mechanic_names
    ):
        signals += 2

    mount = _MOUNT_STATE.search(combined)
    if mount and any(
        _resource_matches_mechanic(mount.group(1).strip(), n) for n in mechanic_names
    ):
        signals += 1

    if signals < 2:
        return None

    tips: list[str] = []
    for mech, gains in stack_gains.items():
        parts: list[str] = []
        if "use" in gains:
            amt, skill_name = gains["use"]
            parts.append(f"**+{amt} {mech}** on use (**{skill_name}**)")
        if "kill" in gains:
            amt, skill_name = gains["kill"]
            parts.append(f"**+{amt}** on kill (**{skill_name}**)")
        if parts:
            tips.append(
                f"**{mech} stacks** — {'; '.join(parts)}. Build stacks before the finisher."
            )

    if flip:
        state, alt_skill = flip.group(1).strip(), flip.group(2).strip()
        base_skill = next(
            (
                s["name"]
                for s in (skills or [])
                if flip.group(0) in " ".join(s.get("on_use_effects", []))
            ),
            next((s["name"] for s in (skills or []) if s.get("skill_num") == 3), "S3"),
        )
        tips.append(
            f"With **{state}**, **{base_skill}** flips to **{alt_skill}** — "
            f"acquire **{state}** first, then commit the payoff skill."
        )
        if _LOSE_STATE_TURN_END.search(combined):
            tips.append(
                f"**{state}** is lost at **Turn End** after the finisher — "
                f"plan the next acquisition before the following turn."
            )

    if mount:
        state = mount.group(1).strip()
        sp_cost = _MOUNT_SP_COST.search(combined)
        sp_note = f" (**-{sp_cost.group(1)} SP** to mount)" if sp_cost else ""
        tips.append(
            f"**Turn Start** mounts **{state}**{sp_note} while you hold the resource — "
            f"skills check **{state}** during that window."
        )

    for pct, resource, cap, skill_name in damage_scales[:2]:
        tips.append(
            f"**{skill_name}** scales up to **+{cap}% damage** "
            f"(+{pct}% per **{resource}**) — stack before the spend turn."
        )

    for stat, per, every, resource, cap in stat_scales[:1]:
        tips.append(
            f"**{stat}** rises with **{resource}** (+{per} per {every}, max +{cap}) — "
            f"build the resource before committing."
        )

    counter_name = ""
    counter_payoff = ""
    counter_sp_gate = ""
    for block in parse_all_defense_blocks(md_text):
        if not any(n.lower() in block["text"].lower() for n in mechanic_names):
            continue
        cm = _USE_AS_COUNTER.search(block["text"])
        if cm:
            counter_name = block["name"]
            counter_payoff = cm.group(1) or cm.group(2) or ""
            sp_m = re.search(r"has\s+(\d+)\+\s+SP", block["text"], re.I)
            if sp_m:
                counter_sp_gate = sp_m.group(1)
            break
        gain_m = _GAIN_STATE_NEXT_TURN.search(block["text"])
        if gain_m and any(
            _resource_matches_mechanic(gain_m.group(2).strip(), n) for n in mechanic_names
        ):
            counter_name = block["name"]
            state = gain_m.group(2).strip()
            tips.append(
                f"**{counter_name}** grants **{state}** next turn at Combat Start "
                f"when missing — use the defense slot to set up the payoff."
            )
            break

    if counter_name and counter_payoff:
        sp_part = f" at **{counter_sp_gate}+ SP**" if counter_sp_gate else ""
        tips.append(
            f"**{counter_name}**{sp_part} can fire **{counter_payoff}** as Counter "
            f"(once per turn) — a second burst line without spending your S3 slot."
        )

    label = " + ".join(f"**{n}**" for n in mechanic_names)
    payoff_skill = flip.group(2).strip() if flip else ""
    if flip:
        setup_summary = (
            f"{label} carry — stack resources, acquire **{flip.group(1).strip()}** for "
            f"**{payoff_skill}**, then rebuild."
        )
    else:
        setup_summary = (
            f"{label} identity — build unique-resource stacks, hit payoff windows, then rebuild."
        )

    return {
        "kind": "unique_mechanics",
        "mechanics": mechanic_names,
        "payoff_skill": payoff_skill,
        "tips": tips[:4],
        "setup_summary": setup_summary,
    }


_STRATEGIC_RR = re.compile(r"Strategic R&R Mode|Activate Strategic R&R", re.IGNORECASE)
_SELF_REJOIN = re.compile(
    r"after Retreating using .Strategic R&R Mode.|if this unit rejoins the battle",
    re.IGNORECASE,
)
_UPON_RETREAT = re.compile(r"Upon Retreat", re.IGNORECASE)
_ALLY_RETURN_SUPPORT = re.compile(
    r"other ally units Substitute in or Return to the battlefield|"
    r"When other ally units Substitute",
    re.IGNORECASE,
)
_HEISHOU_SUBSTITUTE = re.compile(
    r"killed in this Encounter.*?Substitut|Substituting Identity",
    re.IGNORECASE | re.DOTALL,
)
_HEISHOU_TRAIT = re.compile(r"\bHeishou Pack\b", re.IGNORECASE)
_RETREAT_TRIGGER_SKILL = re.compile(
    r"### (?:Counter|Skill \d+): ([^\n]+)\n(?:[^#]|\n(?!##))*?"
    r"\[Turn End\]\s*Activate Strategic R&R Mode",
    re.IGNORECASE,
)


def find_retreating_archetype(
    raw_markdown: str,
    combat_text: str = "",
    support_text: str = "",
    traits_list: list[str] | None = None,
) -> dict | None:
    """
    Detect kits that leave the field and reappear — Strategic R&R (Devyat),
    Heishou backup substitutes, or faction backup-slot identities.
    """
    combined = f"{combat_text}\n{support_text}\n{raw_markdown}"
    traits = traits_list or []
    has_heishou_trait = any("Heishou Pack" in t for t in traits) or bool(
        _HEISHOU_TRAIT.search(raw_markdown[:500])
    )

    # Ally-only return enablers (e.g. Lord of Hongyuan) are not retreating kits themselves.
    if (
        _ALLY_RETURN_SUPPORT.search(combined)
        and not _STRATEGIC_RR.search(combined)
        and not _UPON_RETREAT.search(support_text)
        and not _HEISHOU_SUBSTITUTE.search(combined)
        and not has_heishou_trait
    ):
        return None

    kind: str | None = None
    tips: list[str] = []
    setup_summary = ""
    trigger_skill = ""

    if _STRATEGIC_RR.search(combined):
        kind = "strategic_rr"
        trigger_m = _RETREAT_TRIGGER_SKILL.search(raw_markdown)
        trigger_skill = trigger_m.group(1).strip() if trigger_m else "maintenance Counter"
        setup_summary = (
            f"**Retreating** identity — activates **Strategic R&R Mode** after "
            f"**{trigger_skill}**, leaving the field while **Upon Retreat** buffs "
            f"allies; can rejoin later at a stack penalty."
        )
        tips.append(
            f"**Strategic R&R Mode** — **{trigger_skill}** triggers retreat at Turn End "
            f"after your maintenance turn; build stacks on field first so "
            f"**Upon Retreat** ally buffs are worth the tempo loss."
        )
        if _SELF_REJOIN.search(combined):
            tips.append(
                "Rejoining once per encounter **halves** your carried stacks — treat the "
                "first rotation as your main value window before returning."
            )
        elif _UPON_RETREAT.search(support_text):
            tips.append(
                "**Upon Retreat** applies team Clash Power Up — retreat when allies can "
                "carry the next turn without you on field."
            )

    elif _HEISHOU_SUBSTITUTE.search(combined):
        kind = "heishou_substitute"
        setup_summary = (
            "**Heishou substitute** — when this identity is killed, your **backup unit** "
            "Substitutes in and continues the rotation."
        )
        tips.append(
            "Assign a **backup identity** for this sinner — if this unit dies, the backup "
            "**Substitutes** in and can pick up Heishou passive value on entry."
        )
        if has_heishou_trait:
            tips.append(
                "Pair with **Heishou Pack** teammates (and **The Lord of Hongyuan** if "
                "available) so Return-to-field procs and faction passives stack across substitutions."
            )

    elif has_heishou_trait:
        kind = "heishou_backup"
        setup_summary = (
            "**Heishou Pack** — assign a **backup identity** for this sinner so a substitute "
            "can **Return to the battlefield** when the active unit falls."
        )
        tips.append(
            "**Backup unit** — slot a backup identity on this sinner (another Heishou Pack "
            "ID is ideal) so stagger or death **Substitutes** them in with a fresh skill queue."
        )
        tips.append(
            "Deploy this identity before its backup in the lineup when running multiple "
            "Heishou units — the substitute re-enters ready for another rotation."
        )

    if not kind:
        return None

    return {
        "kind": kind,
        "trigger_skill": trigger_skill or None,
        "setup_summary": setup_summary,
        "tips": tips[:3],
    }


_SUPPORT_PASSIVE_NAME = re.compile(r"^###\s+(.+)$", re.MULTILINE)


def _support_passive_title(support_text: str) -> str:
    match = _SUPPORT_PASSIVE_NAME.search(select_primary_support_passive(support_text))
    return match.group(1).strip() if match else "Support passive"


def find_support_archetype(
    support_text: str,
    combat_text: str = "",
    raw_markdown: str = "",
    mechanic_profile: dict | None = None,
) -> dict | None:
    """
    Detect how a Support identity reaches the point where teammate buffs apply.

    Returns None when the kit lacks a meaningful ally-facing support passive.
    """
    from limbus_guides.domain.context import infer_roles

    if not support_text.strip():
        return None

    combined = f"{support_text}\n{combat_text}"
    lower = combined.lower()
    ally_facing = bool(
        re.search(
            r"\b(?:\d+\s+)?all(?:y|ies)\b|\bother\s+\w+\s+allies|"
            r"deployed identity|deployment order",
            combined,
            re.IGNORECASE,
        )
    )
    if not ally_facing:
        return None

    roles = infer_roles(raw_markdown or combined, mechanic_profile)
    if "Support" not in roles:
        return None

    passive_name = _support_passive_title(support_text)
    kind = "ally_support"
    tips: list[str] = []
    setup_summary = ""

    if re.search(r"#1 deployed|earliest deployment order", combined, re.I):
        kind = "deploy_order"
        if "ammo" in lower:
            setup_summary = (
                f"Support passives resupply the earliest-deployed **Ammo** ally — "
                f"set deployment so your Ammo user spends first and can be refilled."
            )
            tips.append(
                f"**{passive_name}** targets the first **Ammo** ally in deployment order — "
                f"deploy them ahead of this unit and let them attack before expecting resupply."
            )
        elif "tremor burst" in lower:
            setup_summary = (
                f"Support passive (**{passive_name}**) procs when the **#1 deployed** ally "
                f"triggers Tremor Burst — stack Tremor on their target first."
            )
            tips.append(
                f"Place your Tremor carry as **#1 deployed** so their Bursts can trigger "
                f"**{passive_name}**'s bonus proc."
            )
        else:
            setup_summary = (
                f"Support passive (**{passive_name}**) keys off **deployment order** — "
                f"set your main carry as #1 deployed before the fight."
            )
            tips.append(
                f"**{passive_name}** watches the **#1 deployed ally** — "
                f"arrange the dashboard so the intended carry is first in line."
            )
    elif re.search(
        r"give .*?poise|to 2 other allies.*?poise|poise potency.*?other allies",
        combined,
        re.I,
    ):
        kind = "poise_share"
        setup_summary = (
            f"Support passive (**{passive_name}**) **shares Poise** whenever this unit gains stacks — "
            f"build Poise through clashes before allies need the payout."
        )
        tips.append(
            f"**{passive_name}** distributes Poise to allies when you gain it — "
            f"clash actively and use Poise-building skills to feed the team."
        )
    elif re.search(r"on hit", combined, re.I) and re.search(r"all(?:y|ies)", combined, re.I):
        kind = "on_hit_ally"
        target_note = " (lowest-HP ally hits)" if "lowest hp" in lower else ""
        setup_summary = (
            f"Support passive (**{passive_name}**) applies when allies **land hits**{target_note} — "
            f"keep this unit on field through the opening turn so damage dealers can act."
        )
        tips.append(
            f"**{passive_name}** triggers **On Hit** — protect this slot and let allies "
            f"attack each turn before expecting heals or buffs to flow."
        )
    elif re.search(r"fastest speed", combined, re.I) and re.search(r"all(?:y|ies)", combined, re.I):
        kind = "fastest_speed"
        setup_summary = (
            f"Support passive (**{passive_name}**) buffs your **fastest Speed ally** — "
            f"pair with a high-Speed attacker and keep this unit alive on field."
        )
        tips.append(
            f"**{passive_name}** amplifies the **fastest Speed ally** — "
            f"slot a quick damage dealer and avoid stagger so their hits keep the bonus."
        )
    elif re.search(r"combat start", combined, re.I) and re.search(r"all(?:y|ies)", combined, re.I):
        kind = "combat_start_ally"
        if "least hp" in lower:
            target = "your lowest-HP ally"
        elif "reson" in lower:
            target = "highest-Resonance allies in deployment order"
        elif any(
            faction in lower
            for faction in ("blade lineage", "kurokumo", "la manchaland", "liu assoc")
        ):
            target = "faction allies on the dashboard"
        else:
            target = "the intended ally"
        setup_summary = (
            f"Support passive (**{passive_name}**) applies at **Combat Start** — "
            f"set deployment with {target} before turn one."
        )
        tips.append(
            f"**{passive_name}** fires at **Combat Start** — "
            f"confirm roster and slot order pre-fight so the right ally receives the buff."
        )
    elif re.search(r"reson\.", combined, re.I):
        kind = "resonance_ally"
        setup_summary = (
            f"Support passive (**{passive_name}**) scales with **Resonance** — "
            f"field matching-trait allies to reach threshold before buffs fully apply."
        )
        tips.append(
            f"**{passive_name}** keys off **Resonance** — "
            f"add trait-matching teammates to raise Reson. before relying on the passive."
        )
    else:
        setup_summary = (
            f"Support passive (**{passive_name}**) buffs teammates — "
            f"keep this unit on field while allies run their attack rotation."
        )
        tips.append(
            f"**{passive_name}** supports allies passively — "
            f"prioritise staying alive and deployed so the team benefits each turn."
        )

    return {
        "kind": kind,
        "passive_name": passive_name,
        "setup_summary": setup_summary,
        "tips": tips[:2],
    }


def _compute_heads_dependent(skills: list[dict]) -> bool:
    heads_gated = 0
    total = 0
    for skill in skills:
        for coin in skill.get("coin_effects", []):
            eff = coin.get("effect", "")
            total += 1
            if "[Heads Hit]" in eff or "[Heads:" in eff:
                heads_gated += 1
    return total > 0 and (heads_gated / total) > 0.5


def build_gameplan(identity: dict) -> dict:
    """
    High-level wrapper — derive a complete gameplan dict from an identity record.
    Used by generation.py to build guide text.
    """
    raw = identity.get("raw_markdown", "")
    profile = identity.get("mechanic_profile", {})
    combat_text, support_text = parse_passives_text(raw)

    # Prefer pre-parsed skills stored in the identity JSON; otherwise derive from markdown
    if identity.get("parsed_skills"):
        skills: list[dict] = identity["parsed_skills"]
        alternate_skills: list[dict] = identity.get("alternate_skills") or []
    else:
        skills, alternate_skills = parse_all_skills(raw)

    combat_passive_notes = parse_combat_passive_notes(raw)
    defense_skill_notes = parse_defense_skill_notes(raw)
    ally_combo = find_ally_combo(combat_text)

    resource_loop = find_resource_loop(skills, profile)
    state_transition = find_state_transition(raw)
    damage_conditions = find_damage_conditions(skills)

    # Poise → Coin Power conversion (e.g. Blade Lineage Salsu)
    poise_passive: dict | None = None
    pm = _POISE_TO_COINPWR.search(combat_text)
    if pm:
        poise_passive = {
            "coin_power_per": int(pm.group(1)),
            "poise_per": int(pm.group(2)),
            "max": int(pm.group(3)),
            "clash_win": bool(_CLASH_WIN_POISE.search(combat_text)),
        }

    neg_effect_scaling = any(
        any("negative effect" in d for d in s.get("damage_scales", []))
        for s in skills
    )

    unique_tremor_types = sorted(extract_unique_tremor_types(raw))
    unique_ammo = find_unique_ammo_economy(skills, alternate_skills)
    defense_archetype = find_defense_archetype(raw, alternate_skills, combat_text)
    negative_coin_archetype = find_negative_coin_archetype(
        raw, alternate_skills, combat_text, support_text
    )
    support_archetype = find_support_archetype(
        support_text,
        combat_text,
        raw_markdown=raw,
        mechanic_profile=profile,
    )
    retreating_archetype = find_retreating_archetype(
        raw,
        combat_text,
        support_text,
        traits_list=identity.get("traits_list")
        or parse_traits_list(identity.get("traits")),
    )
    nails_archetype = find_nails_archetype(raw, combat_text, skills)
    charge_archetype = find_charge_archetype(skills, combat_text, profile)
    unique_mechanics_archetype = find_unique_mechanics_archetype(
        raw, combat_text, skills, alternate_skills, profile
    )

    from limbus_guides.nlp.archetypes import detect_status_archetypes

    status_archetypes = detect_status_archetypes(
        skills,
        combat_text,
        raw_markdown=raw,
        mechanic_profile=profile,
        support_text=support_text,
        nails_archetype=nails_archetype,
        defense_archetype=defense_archetype,
    )

    return {
        "skills": skills,
        "alternate_skills": alternate_skills,
        "resource_loop": resource_loop,
        "state_transition": state_transition,
        "damage_conditions": damage_conditions,
        "poise_passive": poise_passive,
        "neg_effect_scaling": neg_effect_scaling,
        "combat_passives_text": combat_text,
        "combat_passive_notes": combat_passive_notes,
        "defense_skill_notes": defense_skill_notes,
        "support_passive_text": support_text,
        "heads_dependent": _compute_heads_dependent(skills),
        "primary_mechanics": profile.get("primary_mechanics", []),
        "ally_combo": ally_combo,
        "unique_tremor_types": unique_tremor_types,
        "unique_ammo": unique_ammo,
        "defense_archetype": defense_archetype,
        "negative_coin_archetype": negative_coin_archetype,
        "support_archetype": support_archetype,
        "retreating_archetype": retreating_archetype,
        "nails_archetype": nails_archetype,
        "charge_archetype": charge_archetype,
        "unique_mechanics_archetype": unique_mechanics_archetype,
        **status_archetypes,
        "resonance_dependent": detect_resonance_dependency(raw),
        "trait_conditional": detect_trait_conditional(raw),
        "traits_list": identity.get("traits_list")
        or parse_traits_list(identity.get("traits")),
    }
