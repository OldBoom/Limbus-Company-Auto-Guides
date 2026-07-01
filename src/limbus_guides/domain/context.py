"""Load domain primer and build guide-generation context."""

from __future__ import annotations

import re
from functools import lru_cache

from limbus_guides.paths import DOMAIN_PRIMER_PATH

# Condensed rules from docs/domain-primer.md for prompts (keep in sync when primer edits).
GUIDE_WRITING_RULES = """
Domain rules for Limbus Company guides (from docs/domain-primer.md):

Terminology:
- Battle = full encounter; Turn = every unit acts once; Rotation = 3xS1, 2xS2, 1xS3 queue across many turns.
- Skill 3 appears once per rotation, not once per turn.

On-field roles (state in the opening sentence of every guide):
- Damage Dealer: Rating is heavily influenced based on the ID's damage and utility to both deal damage and amplify the damage of others, including their own.
- Status Specialist: Rating is heavily influenced based on the ID's ability to stack the count and potency of every status or brings something unique to that status to make it overall effective and stronger.
- Support: Rating is heavily influenced based on the ID's ability to give buffs to allies, debuffs to enemies, and overall utility to help defeat enemies quicker.
  Some Support identities spend most turns on Guard/Evade rather than attacking — say so explicitly.
- Tank: Rating is heavily influenced based on the ID's ability to take damage and their benefits to taking damage.
- Many identities hold two roles simultaneously; list both and explain the priority.

Rotation:
- When a unit acts, the player picks 1 of 2 skills shown from the rotation queue.
- Skill 1 is setup/chip damage; Skill 3 is the lone finisher slot per rotation.

Skill 3 — commit only when the attack is likely to land:
- Enemy is Staggered (cannot clash back when they next act).
- An ally is already clashing the same target.
- Target has debuffs that weaken clash (Bind, Defense Level Down) or buff your Clash Power.
- Clash numbers favor you (Clash Power, Final Power, Unbreakable Coin, kit conditions met).

Playstyle tone:
- Open with the role(s), then describe rotation pressure and hit confidence.
- Call out state changes (e.g. Flow State) and resource gates (at X+ Count, if Y+ Bleed).
- Team suggestions: name specific identities; explain inflict->scale or archetype synergy.
- Unique Tremor kits (e.g. Tremor — Scorch): prioritize teammates with the same named Tremor subtype over generic Tremor/Burn appliers.
- Only reference mechanics present in the identity data; do not invent skills or numbers.
""".strip()

MAX_PRIMER_CHARS_FOR_LLM = 6000


@lru_cache(maxsize=1)
def load_domain_primer() -> str:
    if not DOMAIN_PRIMER_PATH.exists():
        return GUIDE_WRITING_RULES
    return DOMAIN_PRIMER_PATH.read_text(encoding="utf-8")


def get_guide_writing_context(*, include_full_primer: bool = False) -> str:
    """Context block for LLM / template guide generation."""
    if include_full_primer:
        primer = load_domain_primer()
        if len(primer) > MAX_PRIMER_CHARS_FOR_LLM:
            primer = primer[:MAX_PRIMER_CHARS_FOR_LLM] + "\n\n[... truncated ...]"
        return f"{GUIDE_WRITING_RULES}\n\n---\n\nFull domain primer:\n{primer}"
    return GUIDE_WRITING_RULES


def infer_roles(text: str, mechanic_profile: dict | None = None) -> list[str]:
    """
    Infer on-field role(s) from kit text and optional mechanic profile.
    Returns a list of role strings drawn from: Damage Dealer, Status Specialist, Support, Tank.
    """
    roles: list[str] = []
    lower = text.lower()

    # Support: strong signal is a meaningful support passive
    if "## support passive" in lower:
        sp_idx = lower.find("## support passive")
        sp_text = lower[sp_idx : sp_idx + 600]
        support_keywords = ["inflict", "heal", "sp", "ally", "allies", "gain", "deal"]
        team_effect_keywords = [
            "deployed identity",
            "deployment order",
            "other allies",
            "fastest speed",
            "earliest deployment",
        ]
        if sum(1 for kw in support_keywords if kw in sp_text) >= 2:
            roles.append("Support")
        elif any(kw in sp_text for kw in team_effect_keywords):
            roles.append("Support")

    # Tank: Assist Defense, Guard passives, high aggro mechanics
    if (
        "assist defense" in lower
        or "[before getting hit]" in lower
        or "nullify that damage" in lower
        or "cannot drop below 1" in lower
        or re.search(r"gain \+\d+ aggro", lower)
    ):
        roles.append("Tank")
    # Supplementary: any Aggro mechanic also qualifies as Tank
    elif re.search(r"aggro", lower):
        roles.append("Tank")

    # Status Specialist: primary value is applying statuses, not just using them
    status_inflictors = ["inflict", "apply"]
    status_names = ["bleed", "burn", "tremor", "rupture", "sinking", "dark flame", "bind"]
    inflict_count = sum(
        1 for w in status_inflictors for s in status_names if f"{w} {s}" in lower or f"{w}" in lower
    )
    # Identities that primarily spread status and whose status_effects are dominated by infliction
    if inflict_count >= 4 or ("dark flame" in lower) or ("magic bullet" in lower):
        roles.append("Status Specialist")
    # Supplementary: kits that inflict status Count on enemies
    elif (
        re.search(r"inflict \+\d+ .*?\bcount\b", lower)
        or re.search(r"inflict \+\d+\s+count of", lower)
    ):
        roles.append("Status Specialist")

    # Damage Dealer: resource loop that cashes out, or high base-power finisher
    has_resource_loop = any(kw in lower for kw in [
        "consume", "corpus ingredient", "flow state", "poise count", "magic bullet",
        "final power +", "base power +",
    ])
    has_crit_or_burst = "+70%" in lower or "+100%" in lower or "critical hit" in lower
    if (has_resource_loop or has_crit_or_burst) and "Tank" not in roles:
        roles.append("Damage Dealer")

    # Fallback: every identity deals some damage
    if not roles:
        roles.append("Damage Dealer")
    elif "Status Specialist" in roles and "Damage Dealer" not in roles:
        # Pure status spreaders still deal damage, but secondary
        pass

    # Deduplicate while preserving priority order (Tank before Support when both apply)
    _ROLE_ORDER = ["Tank", "Damage Dealer", "Status Specialist", "Support"]
    seen: set[str] = set()
    result = []
    for r in roles:
        if r not in seen:
            seen.add(r)
            result.append(r)
    result.sort(key=lambda r: _ROLE_ORDER.index(r) if r in _ROLE_ORDER else 99)
    return result


def playstyle_hints_from_text(text: str, mechanic_profile: dict | None = None) -> list[str]:
    """Identity-specific hints derived from kit text + domain rules."""
    hints: list[str] = []
    lower = text.lower()

    # Role statement always comes first
    roles = infer_roles(text, mechanic_profile)
    role_str = " / ".join(roles)
    hints.append(f"On-field role: {role_str}.")

    if "skill 3" in lower or "### skill 3" in lower:
        hints.append(
            "Skill 3 appears once per rotation — recommend it only when the attack is "
            "likely to connect (staggered target, ally clash, favorable statuses, winning clash stats)."
        )

    if "flow state" in lower or "iron maiden" in lower:
        hints.append(
            "Note state transitions mid-battle and how skills or passives change after the switch."
        )

    if "for every" in lower and ("bleed" in lower or "negative effect" in lower):
        hints.append(
            "Stack relevant debuffs before cashing out high-cost skills; mention setup turns."
        )

    if "[on use]" in lower and "clash power" in lower:
        hints.append(
            "Mention building Clash Power / conditions before committing the rotation's Skill 3."
        )

    if "## support passive" in lower and "Support" in roles:
        hints.append(
            "This identity's primary team value is its Support Passive. "
            "Note whether it should prioritise Guard/Evade over attacking to stay healthy."
        )

    return hints
