"""Synergy detection: support-passive rules + embedding similarity."""

from __future__ import annotations

import os
import re
import warnings

from limbus_guides.nlp.mechanic_signals import (
    extract_unique_tremor_types,
    format_unique_tremor_label,
)

# Re-exported for callers that historically imported them from this module.
__all__ = [
    "GENERIC_TRAITS",
    "SELF_GAINED_STATUSES",
    "extract_unique_tremor_types",
    "find_synergy_teammates",
    "format_unique_tremor_label",
]

_EMBEDDINGS_DISABLED_ENV = "LIMBUS_NO_EMBEDDINGS"
_embedding_warning_shown = False


def embeddings_enabled(override: bool | None = None) -> bool:
    """Whether to compute embedding-similarity teammates.

    Embeddings rank below every rule and only surface when fewer than three rules
    fire, so they are optional — skipping them avoids the sentence-transformers
    (and torch) dependency entirely. Set ``LIMBUS_NO_EMBEDDINGS=1`` to turn them off.
    """
    if override is not None:
        return override
    return os.environ.get(_EMBEDDINGS_DISABLED_ENV, "").lower() not in ("1", "true", "yes")


def _similar_pairs(slug: str, roster: dict[str, dict], k: int) -> list[tuple[str, float]]:
    """Embedding neighbours, or [] when sentence-transformers is unavailable."""
    global _embedding_warning_shown
    try:
        from limbus_guides.nlp.similarity import top_similar

        return top_similar(slug, roster, k=k)
    except ImportError as exc:  # sentence-transformers / torch not installed
        if not _embedding_warning_shown:
            _embedding_warning_shown = True
            warnings.warn(
                f"Embedding similarity unavailable ({exc}); using rule-based synergies only. "
                f"Install sentence-transformers or set {_EMBEDDINGS_DISABLED_ENV}=1 to silence.",
                RuntimeWarning,
                stacklevel=2,
            )
        return []

SUPPORT_PASSIVE_RE = re.compile(
    # Word boundaries matter: without them "gain" matches inside "aGAINst", so
    # "On Clash Win against enemies with Burn" was read as the passive granting Burn.
    # That alone put 10 unrelated identities into each other's team suggestions.
    # Group 1 stays the verb and group 2 the status, as callers expect.
    # "give" is how the wiki words ally-granting clauses ("Give 1 Poise Potency and
    # +1 Poise Count to 2 other allies"), so it belongs with the other verbs.
    r"(\b(?:inflict|gain|grant)(?:s|ing)?\b|\bappl(?:y|ies|ying)\b|\bgiv(?:e|es|ing)\b)"
    r".{0,60}?"
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
# Category labels rather than synergy groups. Sharing one says nothing about whether
# two identities help each other, and each was generating teammate picks:
# E.G.O Gear appears on 19 identities, Limbus Company on 22, LCB on 12.
GENERIC_TRAITS = frozenset({
    "Fixer",
    "Syndicate",
    "The Backstreets",
    "The Fingers",
    "E.G.O Gear",
    "Limbus Company",
    "LCB",
    "Lobotomy Corp. Headquarters",
})

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
            "his passives heal allies that **Substitute in** or **Return to the battlefield**, "
            "command free Unopposed Attacks, stack **Life from Death**, and amplify "
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


# A status named inside a trigger is not one the passive applies. Two shapes occur:
#   "On Clash Win against enemies with Burn ..."      -> Burn is what it looks for
#   "If the said allies have Skills that inflict Burn, heal 5~10 SP" -> effect is the heal
# Reporting either as "inflicts Burn via the support passive" is simply false, and it is
# what put unrelated identities in each other's team suggestions.
_TRIGGER_LEAD_RE = re.compile(
    r"(?:against|targets?\s+(?:that|with)|enem(?:y|ies)\s+(?:that|with)|"
    r"all(?:y|ies)\s+(?:that|who|with)|that\s+(?:have|has|inflicts?)|with)\s*$",
    re.I,
)
_CONDITION_PREFIX_RE = re.compile(r"^\s*(?:When|If|Whenever|Upon)\b[^,]{0,120},", re.I)


def _match_is_trigger(clause: str, match: re.Match[str]) -> bool:
    """True when the status sits in the passive's condition rather than its effect."""
    before = clause[: match.start()]
    if _TRIGGER_LEAD_RE.search(before[-40:]):
        return True
    cond = _CONDITION_PREFIX_RE.match(clause)
    # Inside a leading "When ...," / "If ...," segment, the status is the trigger; the
    # effect is whatever follows the comma.
    return bool(cond and match.start() < cond.end())


def _split_clauses(text: str) -> list[tuple[int, str]]:
    """(offset, clause) pairs split on the wiki's ';' separator."""
    out: list[tuple[int, str]] = []
    pos = 0
    for part in text.split(";"):
        out.append((pos, part))
        pos += len(part) + 1
    return out


def _support_effects(support_text: str) -> set[str]:
    """Status effects the support passive actually applies (triggers excluded)."""
    from limbus_guides.nlp.skill_parser import select_primary_support_passive

    support_text = select_primary_support_passive(support_text)
    effects: set[str] = set()
    for _, clause in _split_clauses(support_text):
        for m in SUPPORT_PASSIVE_RE.finditer(clause):
            if _match_is_trigger(clause, m):
                continue
            effects.add(m.group(2).title())
    return effects


def _support_triggers(support_text: str) -> set[str]:
    """Statuses the support passive keys off but does not apply itself."""
    from limbus_guides.nlp.skill_parser import select_primary_support_passive

    support_text = select_primary_support_passive(support_text)
    triggers: set[str] = set()
    for _, clause in _split_clauses(support_text):
        for m in SUPPORT_PASSIVE_RE.finditer(clause):
            if _match_is_trigger(clause, m):
                triggers.add(m.group(2).title())
    return triggers - _support_effects(support_text)


def _scales_off(text: str) -> set[str]:
    """Status effects / resources that this identity's skills scale off."""
    effects: set[str] = set()
    for m in SCALES_OFF_RE.finditer(text):
        effects.add(m.group(2).title())
    # Also include if identity scales with negative effect density
    if SCALES_NEG_EFFECT_RE.search(text):
        effects.add("_neg_effects")
    return effects


# Statuses an ally GAINS on itself. SUPPORT_PASSIVE_RE also matches the verb "gain",
# so without this the reason text said things like "'Swordplay of the Homeland' inflicts
# Poise ... on the target" — Poise and Charge sit on your own unit, and nobody inflicts
# them on an enemy. This affected roughly 48 identities.
SELF_GAINED_STATUSES = frozenset({"Poise", "Charge", "Haste", "Protection", "Shield"})


def _build_rule_reason(
    passive_name: str,
    inflicted_effect: str,
    subject_scales: set[str],
    subject_text: str = "",
) -> str:
    """
    Build a human-readable synergy reason that explains the actual mechanic link.
    """
    grants_to_self = inflicted_effect in SELF_GAINED_STATUSES
    verb = "grants" if grants_to_self else "inflicts"

    # Threshold checks (e.g. 7+ Bleed) vs per-stack scaling
    threshold_m = re.search(
        rf"(\d+)\+\s+{re.escape(inflicted_effect)}",
        subject_text,
        re.I,
    )
    if threshold_m:
        return (
            f"'{passive_name}' {verb} {inflicted_effect} via the support passive — "
            f"helps reach {threshold_m.group(1)}+ {inflicted_effect} thresholds on key skills."
        )

    scale_note = ""
    if inflicted_effect in subject_scales:
        where = "on your own unit" if grants_to_self else "on the target"
        scale_note = f" — scales off {inflicted_effect} count/potency {where}"
    elif "_neg_effects" in subject_scales:
        scale_note = " — damage scales with how many negative effect types are on the target"
    return f"'{passive_name}' {verb} {inflicted_effect} via the support passive{scale_note}."


def find_synergy_teammates(
    identity: dict,
    roster: dict[str, dict],
    mechanic_profiles: dict[str, dict] | None = None,
    k: int = 5,
    use_embeddings: bool | None = None,
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
    trigger_matches: list[tuple[str, dict, str, str]] = []
    for other_slug, other in roster.items():
        if other_slug == slug:
            continue
        if other.get("sinner") == identity.get("sinner"):
            continue

        support_text = _get_support_passive_section(other)
        support_fx = _support_effects(support_text)
        overlap = my_scales & support_fx

        # A passive that only *keys off* the status still pairs well, but for the
        # opposite reason — this identity feeds it. Kept separate so the wording is
        # truthful and so it never outranks a passive that actually applies it.
        if not overlap:
            trig = my_scales & _support_triggers(support_text)
            if trig:
                trigger_matches.append(
                    (other_slug, other, next(iter(trig)), _support_passive_name(support_text))
                )

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
                # Same-generation Kindreds do not unlock alternate skills. The only
                # mechanical use in the wiki data is Bloodfeast precedence — Manager of
                # La Manchaland "takes precedence" over same-generation Kindreds when
                # consuming, and Prince of La Manchaland excludes "higher Kindreds".
                reason = (
                    f"Shares [{shared}] — same-generation Kindreds compete for the shared "
                    f"**Bloodfeast** pool, and precedence between them is fixed by kit."
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
                # Resonance is the Sin affinity of the skills queued in a turn, not a
                # count of same-trait allies — shared traits unlock alternates, nothing more.
                reason = (
                    f"Shares [{shared}] trait — unlocks this identity's "
                    f"trait-conditional passives and alternate skill variants."
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

    # --- Rule-based: teammate's support passive keys off a status this identity applies ---
    # Scored below every "applies the status" rule: the payoff is real but indirect, and
    # the wording has to say which direction the help runs.
    for other_slug, other, effect, passive_name in trigger_matches:
        if other_slug in seen:
            continue
        suggestions.append(
            {
                "teammate_slug": other_slug,
                "teammate_name": other.get("name", other_slug),
                "reason": (
                    f"'{passive_name}' does not apply {effect} itself — it rewards allies "
                    f"who do, so this kit's {effect} turns it on."
                ),
                "score": 0.80,
                "source": "rule",
                "faction_match": _faction_match(identity, other),
                "trigger_match": True,
            }
        )
        seen.add(other_slug)

    # Embedding entries rank below every rule, so they only reach the guide text as a
    # fallback when fewer than three rules fire — cosine similarity is close to noise on
    # a small roster. `generation.embedding_verify_note` tags those picks as unverified.
    embedding_entries: list[dict] = []
    pairs = _similar_pairs(slug, roster, k * 2) if embeddings_enabled(use_embeddings) else []
    for other_slug, sim_score in pairs:
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
