"""Synergy detection: support-passive rules + embedding similarity."""

from __future__ import annotations

import re

from limbus_guides.nlp.mechanics import build_mechanic_profile
from limbus_guides.nlp.similarity import top_similar

SUPPORT_PASSIVE_RE = re.compile(
    r"(inflict|apply|gain|grant).{0,60}"
    r"(Bleed|Burn|Tremor|Rupture|Sinking|Poise|Charge"
    r"|Dark Flame|Nails|Bloodfeast|Deathrite)",
    re.IGNORECASE,
)
SCALES_OFF_RE = re.compile(
    r"(for every|per|at)\s+\d+\+?\s+"
    r"(Bleed|Burn|Corpus Ingredient|Poise|Charge|Rupture|Sinking"
    r"|Magic Bullet|Bloodfeast|Nails|Dark Flame|Deathrite|Arrow"
    r"|Blooming Thorn|Talisman)",
    re.IGNORECASE,
)
SCALES_NEG_EFFECT_RE = re.compile(
    r"for every type of negative effect",
    re.IGNORECASE,
)

# Named unique Tremor subtypes (e.g. Tremor — Scorch, Tremor - Decay)
_UNIQUE_TREMOR_SUBTYPE_RE = re.compile(
    r"Tremor\s*[-—]\s*([A-Za-z]+)",
    re.IGNORECASE,
)
_UNIQUE_TREMOR_GENERIC_RE = re.compile(
    r"['\"]Unique Tremor['\"]|Unique Tremor",
    re.IGNORECASE,
)

_UNIQUE_TREMOR_RULE_SCORE = 0.95  # Above generic status rules (0.9)
_UNIQUE_TREMOR_MATCH_BONUS = 0.12  # Boost for teammates already in the list
# Ordered longest-first so that specific sub-factions match before generic ones.
_FACTION_PREFIXES: list[tuple[str, str]] = [
    ("Kurokumo Clan", "Kurokumo"),
    ("Liu Assoc.", "Liu Assoc"),
    ("Seven Assoc.", "Seven Assoc"),
    ("Edgar Family", "Edgar Family"),
    ("Blade Lineage", "Blade Lineage"),
    ("Cinq Assoc.", "Cinq Assoc"),
    ("Devyat'", "Devyat"),
    ("Firefist", "Firefist"),
    ("Tingtang Gang", "Tingtang"),
    ("Ring Apprentice", "The Ring"),
    ("Ring Pointillist", "The Ring"),
    ("Ring Fauvist", "The Ring"),
    ("Ring Nursefather", "The Ring"),
    ("The House of Spiders", "The Ring"),
    ("La Manchaland", "La Manchaland"),
    ("The Thumb East", "The Thumb"),
    ("Lobotomy E.G.O", "EGO"),
]

_FACTION_BONUS = 0.07  # Soft bump — meaningful but won't override a better cross-faction fit

# Too common to drive meaningful trait-based synergy matching
GENERIC_TRAITS = frozenset({"Fixer", "Syndicate", "The Backstreets", "The Fingers"})

LORD_HONGYUAN_SLUG = "The_Lord_of_Hongyuan_Hong_Lu"
WILD_HUNT_HEATHCLIFF_SLUG = "Wild_Hunt_Heathcliff"
_HEISHOU_PACK_TRAIT = "Heishou Pack"
_HEISHOU_LORD_SCORE = 0.99  # Always the primary synergy for Heishou Pack members

# Identities whose name prefix does not reflect their faction passive group.
_FACTION_SLUG_OVERRIDES: dict[str, str] = {
    WILD_HUNT_HEATHCLIFF_SLUG: "Edgar Family",
}

_RESONANCE_RE = re.compile(r"\bReson\.", re.IGNORECASE)


def _is_heishou_pack(identity: dict) -> bool:
    return _HEISHOU_PACK_TRAIT in _traits_list(identity)


def _heishou_lord_synergy_entry(lord: dict) -> dict:
    return {
        "teammate_slug": LORD_HONGYUAN_SLUG,
        "teammate_name": lord.get("name", LORD_HONGYUAN_SLUG),
        "reason": (
            "**The Lord of Hongyuan Hong Lu** is the core Heishou Pack enabler — "
            "his passives heal SP and command allies that **Return to the battlefield** "
            "to use free Unopposed Attacks, stack **Life from Death**, and amplify "
            "**Heishou Bolus Contamination** for the whole faction."
        ),
        "score": _HEISHOU_LORD_SCORE,
        "source": "rule",
        "faction_match": True,
        "heishou_lord_synergy": True,
    }


def _traits_list(identity: dict) -> set[str]:
    """Return parsed trait labels for an identity (supports legacy JSON without traits_list)."""
    if identity.get("traits_list"):
        return set(identity["traits_list"])
    raw = identity.get("traits") or ""
    return {
        part.split("|")[0].strip()
        for part in raw.split(",")
        if part.strip()
    }


def _meaningful_traits(identity: dict) -> set[str]:
    return _traits_list(identity) - GENERIC_TRAITS


def _resonance_dependent(identity: dict) -> bool:
    return bool(_RESONANCE_RE.search(identity.get("raw_markdown", "")))


def _extract_faction(name: str) -> str | None:
    """Return the faction label for a given identity name, or None."""
    for prefix, faction in _FACTION_PREFIXES:
        if prefix.lower() in name.lower():
            return faction
    return None


def _faction_for_identity(identity: dict) -> str | None:
    """Faction label from name prefix, with slug-level overrides for edge cases."""
    slug = identity.get("slug", "")
    if slug in _FACTION_SLUG_OVERRIDES:
        return _FACTION_SLUG_OVERRIDES[slug]
    return _extract_faction(identity.get("name", ""))


def _faction_match(identity: dict, other: dict) -> bool:
    my_faction = _faction_for_identity(identity)
    return my_faction is not None and my_faction == _faction_for_identity(other)


def extract_unique_tremor_types(text: str) -> set[str]:
    """Return named unique Tremor subtypes (e.g. Scorch, Decay) present in kit text."""
    return {m.group(1).title() for m in _UNIQUE_TREMOR_SUBTYPE_RE.finditer(text)}


def format_unique_tremor_label(subtype: str) -> str:
    return f"Tremor — {subtype}"


def _unique_tremor_overlap(text_a: str, text_b: str) -> set[str]:
    return extract_unique_tremor_types(text_a) & extract_unique_tremor_types(text_b)

# Extracts the first ### header name from the support passive section text
_PASSIVE_NAME_RE = re.compile(r"^###\s+(.+)$", re.MULTILINE)


def _get_support_passive_section(identity: dict) -> str:
    """Return only the Support Passive section text (not the whole markdown)."""
    sections = identity.get("sections", {})
    # The section key might be exactly "Support Passive"
    for key in sections:
        if "support passive" in key.lower():
            return sections[key]
    return ""


def _support_passive_name(support_text: str) -> str:
    """Extract the primary ### header from support passive section, or fallback."""
    from limbus_guides.nlp.skill_parser import select_primary_support_passive

    primary = select_primary_support_passive(support_text)
    m = _PASSIVE_NAME_RE.search(primary)
    return m.group(1).strip() if m else "Support passive"


def _support_effects(support_text: str) -> set[str]:
    """Status effects inflicted by the support passive."""
    from limbus_guides.nlp.skill_parser import select_primary_support_passive

    support_text = select_primary_support_passive(support_text)
    effects: set[str] = set()
    for m in SUPPORT_PASSIVE_RE.finditer(support_text):
        effects.add(m.group(2).title())
    return effects


def _scales_off(text: str) -> set[str]:
    """Status effects / resources that this identity's skills scale off."""
    effects: set[str] = set()
    for m in SCALES_OFF_RE.finditer(text):
        effects.add(m.group(2).title())
    # Also include if identity scales with negative effect density
    if SCALES_NEG_EFFECT_RE.search(text):
        effects.add("_neg_effects")
    return effects


def _build_rule_reason(
    passive_name: str,
    inflicted_effect: str,
    subject_scales: set[str],
    subject_text: str = "",
) -> str:
    """
    Build a human-readable synergy reason that explains the actual mechanic link.
    """
    # Threshold checks (e.g. 7+ Bleed) vs per-stack scaling
    threshold_m = re.search(
        rf"(\d+)\+\s+{re.escape(inflicted_effect)}",
        subject_text,
        re.I,
    )
    if threshold_m:
        return (
            f"'{passive_name}' inflicts {inflicted_effect} via the support passive — "
            f"helps reach {threshold_m.group(1)}+ {inflicted_effect} thresholds on key skills."
        )

    scale_note = ""
    if inflicted_effect in subject_scales:
        scale_note = f" — scales off {inflicted_effect} count/potency on the target"
    elif "_neg_effects" in subject_scales:
        scale_note = " — damage scales with how many negative effect types are on the target"
    return (
        f"'{passive_name}' inflicts {inflicted_effect} via the support passive{scale_note}."
    )


def find_synergy_teammates(
    identity: dict,
    roster: dict[str, dict],
    mechanic_profiles: dict[str, dict] | None = None,
    k: int = 5,
) -> list[dict]:
    slug = identity["slug"]
    text = identity.get("raw_markdown", "")
    my_scales = _scales_off(text)
    if mechanic_profiles and slug in mechanic_profiles:
        my_scales.update(mechanic_profiles[slug].get("primary_mechanics", []))

    my_faction = _faction_for_identity(identity)

    suggestions: list[dict] = []
    seen: set[str] = set()

    # --- Rule-based: Heishou Pack members always lead with Lord of Hongyuan ---
    if (
        _is_heishou_pack(identity)
        and slug != LORD_HONGYUAN_SLUG
        and LORD_HONGYUAN_SLUG in roster
    ):
        lord = roster[LORD_HONGYUAN_SLUG]
        if lord.get("sinner") != identity.get("sinner"):
            suggestions.append(_heishou_lord_synergy_entry(lord))
            seen.add(LORD_HONGYUAN_SLUG)

    # --- Rule-based: support passive of teammate inflicts what this identity scales off ---
    for other_slug, other in roster.items():
        if other_slug == slug:
            continue
        if other.get("sinner") == identity.get("sinner"):
            continue

        support_text = _get_support_passive_section(other)
        support_fx = _support_effects(support_text)
        overlap = my_scales & support_fx

        if overlap:
            effect = next(iter(overlap))
            passive_name = _support_passive_name(support_text)
            reason = _build_rule_reason(passive_name, effect, my_scales, text)
            base_score = 0.9
            # Soft faction bonus — same-faction allies are slightly preferred
            if my_faction and _faction_match(identity, other):
                base_score += _FACTION_BONUS
            suggestions.append(
                {
                    "teammate_slug": other_slug,
                    "teammate_name": other.get("name", other_slug),
                    "reason": reason,
                    "score": base_score,
                    "source": "rule",
                    "faction_match": _faction_match(identity, other),
                }
            )
            seen.add(other_slug)

    # --- Rule-based (reversed): this identity's support passive inflicts what teammate scales off ---
    my_support_text = _get_support_passive_section(identity)
    my_support_fx = _support_effects(my_support_text)
    my_passive_name = _support_passive_name(my_support_text)

    if my_support_fx:
        for other_slug, other in roster.items():
            if other_slug == slug or other_slug in seen:
                continue
            if other.get("sinner") == identity.get("sinner"):
                continue
            other_text = other.get("raw_markdown", "")
            other_scales = _scales_off(other_text)
            overlap2 = other_scales & my_support_fx

            if overlap2:
                effect = next(iter(overlap2))
                reason = (
                    f"This identity's '{my_passive_name}' inflicts {effect} — "
                    f"{other.get('name', other_slug)} scales off {effect}."
                )
                base_score = 0.85
                if my_faction and _faction_match(identity, other):
                    base_score += _FACTION_BONUS
                suggestions.append(
                    {
                        "teammate_slug": other_slug,
                        "teammate_name": other.get("name", other_slug),
                        "reason": reason,
                        "score": base_score,
                        "source": "rule",
                        "faction_match": _faction_match(identity, other),
                    }
                )
                seen.add(other_slug)

    # --- Rule-based: same unique Tremor subtype (e.g. Tremor — Scorch) ---
    my_unique_tremor = extract_unique_tremor_types(text)
    if my_unique_tremor:
        for other_slug, other in roster.items():
            if other_slug == slug or other_slug in seen:
                continue
            if other.get("sinner") == identity.get("sinner"):
                continue
            other_text = other.get("raw_markdown", "")
            shared = my_unique_tremor & extract_unique_tremor_types(other_text)
            if not shared:
                continue
            subtype = sorted(shared)[0]
            label = format_unique_tremor_label(subtype)
            reason = (
                f"Shares the same unique Tremor type ({label}) — "
                f"stack Tremor on one target for Amplitude Conversion and Burst setups."
            )
            base_score = _UNIQUE_TREMOR_RULE_SCORE
            if my_faction and _faction_match(identity, other):
                base_score += _FACTION_BONUS
            suggestions.append(
                {
                    "teammate_slug": other_slug,
                    "teammate_name": other.get("name", other_slug),
                    "reason": reason,
                    "score": base_score,
                    "source": "rule",
                    "faction_match": _faction_match(identity, other),
                    "unique_tremor_match": True,
                }
            )
            seen.add(other_slug)

    # --- Rule-based: trait overlap (Resonance / alternate skill unlock) ---
    my_traits = _meaningful_traits(identity)
    has_alternates = bool(identity.get("alternate_skills"))
    is_resonance = _resonance_dependent(identity)

    has_bloodfeast_kit = "bloodfeast" in text.lower()
    la_manchaland_trait = "La Manchaland" in my_traits
    trait_synergy_eligible = my_traits and (
        has_alternates or is_resonance or (has_bloodfeast_kit and la_manchaland_trait)
    )

    if trait_synergy_eligible:
        for other_slug, other in roster.items():
            if other_slug == slug or other_slug in seen:
                continue
            if other.get("sinner") == identity.get("sinner"):
                continue
            overlap = my_traits & _meaningful_traits(other)
            if not overlap:
                continue
            kindred_overlap = {t for t in overlap if "Kindred" in t}
            if kindred_overlap:
                shared = sorted(kindred_overlap)[0]
                reason = (
                    f"Shares [{shared}] trait — same-generation ally activates "
                    f"this identity's trait-conditional passive and alternate skills."
                )
                base_score = 0.97
            elif "La Manchaland" in overlap and has_bloodfeast_kit:
                shared = "La Manchaland"
                reason = (
                    f"Shares [{shared}] — feeds the shared Bloodfeast pool "
                    f"and strengthens allied Hardblood / Bloodfeast passives."
                )
                base_score = 0.95
            else:
                shared = sorted(overlap)[0]
                reason = (
                    f"Shares [{shared}] trait — presence raises Resonance, "
                    f"scaling Resonance-dependent skills and unlocking alternate skill variants."
                )
                base_score = 0.93
            suggestions.append(
                {
                    "teammate_slug": other_slug,
                    "teammate_name": other.get("name", other_slug),
                    "reason": reason,
                    "score": base_score,
                    "source": "rule",
                    "faction_match": True,
                    "trait_match": True,
                }
            )
            seen.add(other_slug)

    # Boost any existing pick that shares the same unique Tremor subtype
    if my_unique_tremor:
        for entry in suggestions:
            other = roster.get(entry["teammate_slug"], {})
            shared = my_unique_tremor & extract_unique_tremor_types(other.get("raw_markdown", ""))
            if shared:
                entry["score"] = max(entry["score"], _UNIQUE_TREMOR_RULE_SCORE) + _UNIQUE_TREMOR_MATCH_BONUS
                entry["unique_tremor_match"] = True

    # Embedding-based entries are NOT included in team_suggestions
    # (cosine similarity is noise with a small roster).
    # They are kept in the synergy JSON for evaluation/debug purposes only.
    embedding_entries: list[dict] = []
    for other_slug, sim_score in top_similar(slug, roster, k=k * 2):
        if other_slug in seen:
            continue
        other = roster[other_slug]
        faction_bonus = _FACTION_BONUS if _faction_match(identity, other) else 0.0
        embedding_entries.append(
            {
                "teammate_slug": other_slug,
                "teammate_name": other.get("name", other_slug),
                "reason": f"Mechanic similarity score: {sim_score:.2f}.",
                "score": sim_score + faction_bonus,
                "source": "embedding",
                "faction_match": faction_bonus > 0,
            }
        )
        if len(embedding_entries) >= k:
            break

    suggestions.sort(key=lambda x: x["score"], reverse=True)
    # Include embedding entries in the output JSON for transparency, but mark them
    # so generation.py can filter them from guide text.
    return (suggestions + embedding_entries)[:k]
