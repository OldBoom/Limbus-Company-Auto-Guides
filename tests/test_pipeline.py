"""Tests for markdown loader, mechanic extraction, and domain context."""

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from limbus_guides.domain.context import (
    get_guide_writing_context,
    load_domain_primer,
    playstyle_hints_from_text,
)
from limbus_guides.ingestion.markdown_loader import load_all_parsed, load_parsed_identity
from limbus_guides.nlp.generation import generate_guide
from limbus_guides.nlp.mechanics import extract_mechanics_regex_only
from limbus_guides.paths import DOMAIN_PRIMER_PATH


def test_load_parsed_identities():
    identities = load_all_parsed()
    assert len(identities) >= 3
    assert "Ring_Apprentice_Faust" in identities


def test_faust_has_bleed():
    identity = load_parsed_identity("Ring_Apprentice_Faust")
    assert "Bleed" in identity["description_text"] or "Bleed" in identity["raw_markdown"]


def test_regex_mechanic_extraction():
    identity = load_parsed_identity("Blade_Lineage_Salsu_Yi_Sang")
    profile = extract_mechanics_regex_only(identity["description_text"])
    assert "Poise" in profile.get("all_mechanics", {}) or "Poise" in profile.get("primary_mechanics", [])


def test_domain_primer_exists():
    assert DOMAIN_PRIMER_PATH.exists()
    text = load_domain_primer()
    assert "Battle" in text and "Rotation" in text


def test_guide_writing_context_mentions_rotation():
    ctx = get_guide_writing_context()
    assert "rotation" in ctx.lower()
    assert "Skill 3" in ctx


def test_playstyle_hints_for_skill_3_kit():
    identity = load_parsed_identity("Ring_Pointillist_Student_Yi_Sang")
    hints = playstyle_hints_from_text(identity["raw_markdown"])
    assert any("Skill 3" in h or "rotation" in h.lower() for h in hints)


def test_generated_guide_includes_domain_context():
    identity = load_parsed_identity("Ring_Apprentice_Faust")
    identity["mechanic_profile"] = {"primary_mechanics": ["Bleed", "Corpus Ingredient"]}
    guide = generate_guide(identity, synergies=[], use_ollama=False)
    assert guide.get("domain_context") == "docs/domain-primer.md"
    # Smart guide uses 'template_smart' generator
    assert guide.get("generator") in ("template", "template_smart")


def test_sinners_config_loads():
    from limbus_guides.config_io import load_json_config
    from limbus_guides.paths import CONFIG_DIR

    config = load_json_config(CONFIG_DIR / "sinners.json")
    assert len(config["sinners"]) == 12


# --- Skill parser tests ---

def test_skill_parser_finds_three_skills():
    from limbus_guides.nlp.skill_parser import parse_skills

    faust = load_parsed_identity("Ring_Apprentice_Faust")
    skills = parse_skills(faust["raw_markdown"])
    assert len(skills) == 3
    assert {s["skill_num"] for s in skills} == {1, 2, 3}


def test_skill_parser_detects_resource_loop():
    from limbus_guides.nlp.skill_parser import find_resource_loop, parse_skills

    faust = load_parsed_identity("Ring_Apprentice_Faust")
    skills = parse_skills(faust["raw_markdown"])
    profile = {"unique_mechanics": {"Corpus Ingredient": 22}}
    loop = find_resource_loop(skills, profile)
    assert loop is not None
    assert loop["resource"] == "Corpus Ingredient"
    assert loop["threshold"] == 10
    assert loop["max"] == 20


def test_skill_parser_detects_state_transition():
    from limbus_guides.nlp.skill_parser import find_state_transition

    faust = load_parsed_identity("Ring_Apprentice_Faust")
    transition = find_state_transition(faust["raw_markdown"])
    assert transition is not None
    assert "Iron Maiden" in transition["from_state"]


def test_skill_parser_no_passive_contamination():
    """Skill blocks must not contain ownership markers like (×4 Owned)."""
    from limbus_guides.nlp.skill_parser import parse_skills

    yi_sang = load_parsed_identity("Blade_Lineage_Salsu_Yi_Sang")
    skills = parse_skills(yi_sang["raw_markdown"])
    for skill in skills:
        for bonus in skill.get("skill_bonuses", []):
            assert not bonus.startswith("(×"), f"Ownership marker leaked: {bonus!r}"


def test_smart_guide_references_skill_names():
    """Generated playstyle should mention at least one actual skill name."""
    identity = load_parsed_identity("Blade_Lineage_Salsu_Yi_Sang")
    from limbus_guides.nlp.mechanics import build_mechanic_profile

    identity["mechanic_profile"] = build_mechanic_profile(identity)
    guide = generate_guide(identity, synergies=[], use_ollama=False)
    playstyle = guide["playstyle_guide"]
    # The skill name "Striker's Stance" or "Heel Turn" or "Flank Thrust" must appear
    assert any(name in playstyle for name in ["Striker", "Heel Turn", "Flank Thrust"])


def test_unique_tremor_synergy_prioritizes_same_subtype():
    from limbus_guides.ingestion.markdown_loader import load_all_parsed
    from limbus_guides.nlp.synergy import extract_unique_tremor_types, find_synergy_teammates

    roster = load_all_parsed()
    soldato = roster["The_Thumb_East_Soldato_II_Sinclair"]
    capo = roster["The_Thumb_East_Capo_IIII_Meursault"]

    assert "Scorch" in extract_unique_tremor_types(soldato["raw_markdown"])
    assert "Scorch" in extract_unique_tremor_types(capo["raw_markdown"])

    synergies = find_synergy_teammates(soldato, roster, k=5)
    rule_picks = [s for s in synergies if s.get("source") == "rule"]
    capo_pick = next(s for s in rule_picks if s["teammate_slug"] == capo["slug"])
    assert capo_pick.get("unique_tremor_match")
    assert capo_pick["score"] >= 0.95
    assert rule_picks[0]["teammate_slug"] == capo["slug"]


def test_la_manchaland_trait_synergy_prioritizes_kindred_allies():
    from limbus_guides.nlp.synergy import find_synergy_teammates

    roster = load_all_parsed()
    manager = roster["The_Manager_of_La_Manchaland_Don_Quixote"]
    princess = roster["The_Princess_of_La_Manchaland_Rodion"]
    barber = roster["The_Barber_of_La_Manchaland_Outis"]

    assert "La Manchaland" in manager.get("traits_list", [])
    assert manager.get("alternate_skills")

    synergies = find_synergy_teammates(manager, roster, k=8)
    rule_picks = [s for s in synergies if s.get("source") == "rule"]
    princess_pick = next(s for s in rule_picks if s["teammate_slug"] == princess["slug"])
    barber_pick = next(s for s in rule_picks if s["teammate_slug"] == barber["slug"])

    assert princess_pick.get("trait_match")
    assert "Second Kindred" in princess_pick["reason"]
    assert princess_pick["score"] >= 0.97

    assert barber_pick.get("trait_match")
    assert barber_pick["score"] >= 0.9
    assert princess_pick["score"] >= barber_pick["score"]


def test_heishou_pack_synergy_prioritizes_lord_hong_lu():
    from limbus_guides.nlp.generation import _build_team_suggestions
    from limbus_guides.nlp.mechanics import build_mechanic_profile
    from limbus_guides.nlp.skill_parser import build_gameplan
    from limbus_guides.nlp.synergy import find_synergy_teammates

    roster = load_all_parsed()
    lord_slug = "The_Lord_of_Hongyuan_Hong_Lu"

    for slug in ("Heishou_Pack_-_Si_Branch_Gregor", "Heishou_Pack_-_Wu_Branch_Adept_Yi_Sang"):
        identity = roster[slug]
        synergies = find_synergy_teammates(identity, roster, k=5)
        assert synergies[0]["teammate_slug"] == lord_slug, slug
        assert synergies[0].get("heishou_lord_synergy"), slug

        identity["mechanic_profile"] = build_mechanic_profile(identity)
        gp = build_gameplan(identity)
        team = _build_team_suggestions(synergies, gp)
        assert "The Lord of Hongyuan Hong Lu" in team["lines"][1]
        assert "Heishou Pack" in team["lines"][0]
        assert team["picks"][0]["teammate_slug"] == lord_slug
        assert team["picks"][0]["teammate_name"] == "The Lord of Hongyuan Hong Lu"


def test_wild_hunt_heathcliff_edgar_family_faction_match():
    from limbus_guides.nlp.synergy import (
        WILD_HUNT_HEATHCLIFF_SLUG,
        _faction_for_identity,
        find_synergy_teammates,
    )

    roster = load_all_parsed()
    wild_hunt = roster[WILD_HUNT_HEATHCLIFF_SLUG]
    edgar_slug = "Edgar_Family_Butler_Ishmael"

    assert _faction_for_identity(wild_hunt) == "Edgar Family"

    synergies = find_synergy_teammates(wild_hunt, roster, k=8)
    edgar_pick = next(s for s in synergies if s["teammate_slug"] == edgar_slug)
    assert edgar_pick.get("faction_match") is True
    assert edgar_pick["score"] >= 0.85 + 0.07

    edgar = roster[edgar_slug]
    reverse = find_synergy_teammates(edgar, roster, k=8)
    wild_pick = next(s for s in reverse if s["teammate_slug"] == WILD_HUNT_HEATHCLIFF_SLUG)
    assert wild_pick.get("faction_match") is True


def test_embedding_team_suggestion_note_not_duplicated():
    from limbus_guides.nlp.generation import _build_team_suggestions, generate_guide
    from limbus_guides.nlp.mechanics import build_mechanic_profile
    from limbus_guides.nlp.skill_parser import build_gameplan
    from limbus_guides.nlp.synergy import find_synergy_teammates

    slug = "Blade_Lineage_Salsu_Yi_Sang"
    roster = load_all_parsed()
    identity = roster[slug]
    identity["mechanic_profile"] = build_mechanic_profile(identity)
    synergies = find_synergy_teammates(identity, roster, k=8)
    gp = build_gameplan(identity)
    team = _build_team_suggestions(synergies, gp)

    embed_pick = next(p for p in team["picks"] if p.get("source") == "embedding")
    embed_line = next(ln for ln in team["lines"] if embed_pick["teammate_name"] in ln)
    assert embed_pick["reason"].endswith(".")
    assert "(embedding; verify manually)" not in embed_pick["reason"]
    assert embed_line.count("*(similarity-based — verify)*") == 1
    assert "(embedding; verify manually)" not in embed_line

    guide = generate_guide(identity, synergies=synergies, use_ollama=False)
    assert guide.get("team_suggestion_intro")
    assert guide["team_suggestion_intro"] == team["intro"]


def test_ollama_team_suggestions_skip_structured_picks(monkeypatch):
    from limbus_guides.nlp.generation import generate_guide
    from limbus_guides.nlp.mechanics import build_mechanic_profile
    from limbus_guides.nlp.synergy import find_synergy_teammates

    slug = "Blade_Lineage_Salsu_Sinclair"
    roster = load_all_parsed()
    identity = roster[slug]
    identity["mechanic_profile"] = build_mechanic_profile(identity)
    synergies = find_synergy_teammates(identity, roster, k=5)

    llm_text = (
        "Core idea: test\n\n"
        "Playstyle: rotate skills\n\n"
        "Team suggestions:\n"
        "- **Custom LLM Pick**: synergy from the model."
    )
    monkeypatch.setattr(
        "limbus_guides.nlp.generation._ollama_generate",
        lambda *_args, **_kwargs: llm_text,
    )

    guide = generate_guide(identity, synergies=synergies, use_ollama=True)
    assert guide["team_suggestions"] == ["- **Custom LLM Pick**: synergy from the model."]
    assert "team_suggestion_picks" not in guide
    assert "team_suggestion_intro" not in guide


def test_priest_gregor_tank_role_and_la_manchaland_teammates():
    from limbus_guides.domain.context import infer_roles
    from limbus_guides.nlp.generation import generate_guide
    from limbus_guides.nlp.mechanics import build_mechanic_profile
    from limbus_guides.nlp.skill_parser import build_gameplan
    from limbus_guides.nlp.synergy import find_synergy_teammates

    slug = "The_Priest_of_La_Manchaland_Gregor"
    roster = load_all_parsed()
    identity = roster[slug]
    identity["mechanic_profile"] = build_mechanic_profile(identity)
    gp = build_gameplan(identity)

    roles = infer_roles(
        identity["raw_markdown"],
        identity["mechanic_profile"],
    )
    assert "Tank" in roles
    assert "Support" in roles

    synergies = find_synergy_teammates(identity, roster, k=8)
    rule_picks = [s for s in synergies if s.get("source") == "rule"]
    la_mancha_slugs = {
        "The_Manager_of_La_Manchaland_Don_Quixote",
        "The_Barber_of_La_Manchaland_Outis",
        "The_Princess_of_La_Manchaland_Rodion",
    }
    la_mancha_picks = [s for s in rule_picks if s["teammate_slug"] in la_mancha_slugs]
    assert len(la_mancha_picks) == 3
    assert all(s.get("trait_match") for s in la_mancha_picks)

    guide = generate_guide(identity, synergies=synergies, use_ollama=False)
    assert "Tank" in guide["core_idea"]
    team_text = "\n".join(guide["team_suggestions"])
    picks = guide.get("team_suggestion_picks", [])
    assert len(picks) <= 3
    assert all(p.get("teammate_slug") and p.get("teammate_name") for p in picks)
    assert sum(1 for s in la_mancha_slugs if s.replace("_", " ").split("_")[0] in team_text or any(
        name in team_text
        for name in (
            "The Manager of La Manchaland Don Quixote",
            "The Barber of La Manchaland Outis",
            "The Princess of La Manchaland Rodion",
        )
    )) >= 2
    assert "La Manchaland" in team_text
    assert "Manager of La Manchaland" in team_text or "Barber of La Manchaland" in team_text


def test_manager_don_quixote_playstyle_notes_trait_allies():
    from limbus_guides.nlp.mechanics import build_mechanic_profile
    from limbus_guides.nlp.skill_parser import build_gameplan, detect_trait_conditional

    identity = load_parsed_identity("The_Manager_of_La_Manchaland_Don_Quixote")
    assert detect_trait_conditional(identity["raw_markdown"])
    identity["mechanic_profile"] = build_mechanic_profile(identity)
    gp = build_gameplan(identity)
    assert gp.get("trait_conditional")
    assert gp.get("resonance_dependent")

    guide = generate_guide(identity, synergies=[], use_ollama=False)
    assert "alternate skills activate" in guide["playstyle_guide"].lower()


def test_unique_ammo_tip_in_thumb_guides():
    from limbus_guides.ingestion.markdown_loader import load_parsed_identity
    from limbus_guides.nlp.generation import generate_guide
    from limbus_guides.nlp.mechanics import build_mechanic_profile
    from limbus_guides.nlp.skill_parser import find_unique_ammo_economy, parse_all_skills

    for slug in ("The_Thumb_East_Capo_IIII_Meursault", "The_Thumb_East_Soldato_II_Sinclair"):
        identity = load_parsed_identity(slug)
        skills, alts = parse_all_skills(identity["raw_markdown"])
        ammo = find_unique_ammo_economy(skills, alts)
        assert ammo is not None, slug
        assert ammo["premium_skill"] == 3, slug

        identity["mechanic_profile"] = build_mechanic_profile(identity)
        guide = generate_guide(identity, synergies=[], use_ollama=False)
        playstyle = guide["playstyle_guide"].lower()
        assert "preserve" in playstyle or "ammo" in playstyle or "round" in playstyle
        assert "s3" in playstyle or "skip" in playstyle


def test_unique_ammo_tip_firefist_gregor():
    from limbus_guides.nlp.generation import generate_guide
    from limbus_guides.nlp.mechanics import build_mechanic_profile
    from limbus_guides.nlp.skill_parser import find_unique_ammo_economy, parse_all_skills

    slug = "Firefist_Office_Survivor_Gregor"
    identity = load_parsed_identity(slug)
    skills, alts = parse_all_skills(identity["raw_markdown"])
    ammo = find_unique_ammo_economy(skills, alts)
    assert ammo is not None
    assert ammo["ammo_label"] == "District 12 Fuel"
    assert ammo["premium_skill"] == 3
    assert set(ammo["budget_skills"]) == {1, 2}

    identity["mechanic_profile"] = build_mechanic_profile(identity)
    guide = generate_guide(identity, synergies=[], use_ollama=False)
    playstyle = guide["playstyle_guide"].lower()
    assert "district 12 fuel" in playstyle
    assert "preserve" in playstyle
    assert "s3" in playstyle


def test_negative_coin_archetype_rodion():
    from limbus_guides.nlp.generation import generate_guide, _build_overview_tips
    from limbus_guides.nlp.mechanics import build_mechanic_profile
    from limbus_guides.nlp.skill_parser import build_gameplan, find_negative_coin_archetype

    slug = "Lobotomy_E.G.O_The_Sword_Sharpened_with_Tears_Rodion"
    identity = load_parsed_identity(slug)
    identity["mechanic_profile"] = build_mechanic_profile(identity)
    gp = build_gameplan(identity)
    arch = find_negative_coin_archetype(
        identity["raw_markdown"],
        gp.get("alternate_skills"),
        gp.get("combat_passives_text", ""),
        gp.get("support_passive_text", ""),
    )
    assert arch is not None
    assert arch["kind"] == "negative_coin"
    assert arch["defense_drains_sp"] is True
    assert "Faded Faith" in arch["minus_skills"]

    overview = _build_overview_tips(gp)
    assert "Minus Coin kit" in overview
    assert "defense" in overview.lower() or "Guard" in overview

    guide = generate_guide(identity, synergies=[], use_ollama=False)
    assert "Minus Coin" in guide["core_idea"]
    assert guide["playstyle_guide"].startswith("- ")


def test_infer_roles_aggro_tank_and_count_status_specialist():
    from limbus_guides.domain.context import infer_roles
    from limbus_guides.nlp.mechanics import build_mechanic_profile

    priest = load_parsed_identity("The_Priest_of_La_Manchaland_Gregor")
    priest_mp = build_mechanic_profile(priest)
    priest_roles = infer_roles(priest["raw_markdown"], priest_mp)
    assert "Tank" in priest_roles
    assert "Support" in priest_roles

    devyat = load_parsed_identity("Devyat'_Assoc._North_Section_3_Sinclair")
    devyat_mp = build_mechanic_profile(devyat)
    devyat_roles = infer_roles(devyat["raw_markdown"], devyat_mp)
    assert "Status Specialist" in devyat_roles

    ring = load_parsed_identity("Ring_Pointillist_Student_Yi_Sang")
    ring_mp = build_mechanic_profile(ring)
    ring_roles = infer_roles(ring["raw_markdown"], ring_mp)
    assert "Status Specialist" in ring_roles


def test_support_archetype_overview_and_core_idea():
    from limbus_guides.domain.context import infer_roles
    from limbus_guides.nlp.generation import _build_core_idea, _build_overview_tips, generate_guide
    from limbus_guides.nlp.mechanics import build_mechanic_profile
    from limbus_guides.nlp.skill_parser import build_gameplan, find_support_archetype

    cases = {
        "The_Priest_of_La_Manchaland_Gregor": "on_hit_ally",
        "The_Manager_of_La_Manchaland_Don_Quixote": "combat_start_ally",
        "District_20_Yurodivy_Hong_Lu": "deploy_order",
        "Blade_Lineage_Mentor_Meursault": "poise_share",
    }
    for slug, expected_kind in cases.items():
        identity = load_parsed_identity(slug)
        identity["mechanic_profile"] = build_mechanic_profile(identity)
        gp = build_gameplan(identity)
        arch = find_support_archetype(
            gp.get("support_passive_text", ""),
            gp.get("combat_passives_text", ""),
            raw_markdown=identity["raw_markdown"],
            mechanic_profile=identity["mechanic_profile"],
        )
        assert arch is not None, slug
        assert arch["kind"] == expected_kind, f"{slug}: {arch['kind']}"
        assert "Support" in infer_roles(identity["raw_markdown"], identity["mechanic_profile"])

        overview = _build_overview_tips(gp)
        assert arch["tips"][0] in overview or arch["tips"][0].replace("**", "") in overview.replace("**", "")

        core = _build_core_idea(identity["name"], gp)
        assert arch["setup_summary"] in core

        guide = generate_guide(identity, synergies=[], use_ollama=False)
        assert "Support" in guide["core_idea"] or arch["setup_summary"] in guide["core_idea"]


def test_retreating_archetype_overview_and_core_idea():
    from limbus_guides.nlp.generation import _build_core_idea, _build_overview_tips
    from limbus_guides.nlp.mechanics import build_mechanic_profile
    from limbus_guides.nlp.skill_parser import build_gameplan, find_retreating_archetype

    cases = {
        "Devyat'_Assoc._North_Section_3_Sinclair": "devyat_courier",
        "Heishou_Pack_-_Si_Branch_Gregor": "heishou_substitute",
        "Heishou_Pack_-_Wu_Branch_Adept_Yi_Sang": "heishou_backup",
    }
    for slug, expected_kind in cases.items():
        identity = load_parsed_identity(slug)
        identity["mechanic_profile"] = build_mechanic_profile(identity)
        gp = build_gameplan(identity)
        arch = find_retreating_archetype(
            identity["raw_markdown"],
            gp.get("combat_passives_text", ""),
            gp.get("support_passive_text", ""),
            traits_list=identity.get("traits_list") or [],
        )
        assert arch is not None, slug
        assert arch["kind"] == expected_kind, f"{slug}: {arch['kind']}"

        overview = _build_overview_tips(gp)
        assert arch["tips"][0] in overview or arch["tips"][0].replace("**", "") in overview.replace("**", "")

        core = _build_core_idea(identity["name"], gp)
        if expected_kind == "devyat_courier":
            assert "Courier Trunk" in core
            assert "Strategic R&R" in core
            assert "Devyat" in core
            assert "**Rupture** focus" not in core
        else:
            assert arch["setup_summary"] in core
        tips_blob = " ".join(arch.get("tips", [])).lower()
        assert "two copies" not in tips_blob
        assert "duplicate" not in arch["setup_summary"].lower()
        assert "stagger or death" not in tips_blob
        assert "backup identity for this sinner" not in tips_blob
        assert "slot a backup identity on this sinner" not in tips_blob
        if expected_kind.startswith("heishou"):
            assert "heishou pack identity on a backup" in tips_blob.replace("**", "")

    lord = load_parsed_identity("The_Lord_of_Hongyuan_Hong_Lu")
    lord_gp = build_gameplan({**lord, "mechanic_profile": build_mechanic_profile(lord)})
    assert find_retreating_archetype(
        lord["raw_markdown"],
        lord_gp.get("combat_passives_text", ""),
        lord_gp.get("support_passive_text", ""),
        traits_list=lord.get("traits_list") or [],
    ) is None


def test_defense_archetype_overview_tips():
    from limbus_guides.nlp.generation import generate_guide, _build_overview_tips
    from limbus_guides.nlp.mechanics import build_mechanic_profile
    from limbus_guides.nlp.skill_parser import build_gameplan, find_defense_archetype

    cases = {
        "Shi_Assoc._East_Section_3_Faust": "snipe_setup",
        "The_House_of_Spiders_The_Middle_Nursefather_Outis": "counter_skill",
        "W_Corp._L4_Cleanup_Agent_-_CCA_Heathcliff": "skill_queue",
        "The_Thumb_East_Capo_IIII_Meursault": "equip_unlock",
        "Blade_Lineage_Mentor_Meursault": "power_counter",
    }
    for slug, expected_kind in cases.items():
        identity = load_parsed_identity(slug)
        identity["mechanic_profile"] = build_mechanic_profile(identity)
        gp = build_gameplan(identity)
        arch = find_defense_archetype(
            identity["raw_markdown"],
            gp.get("alternate_skills"),
            gp.get("combat_passives_text", ""),
        )
        assert arch is not None, slug
        assert arch["kind"] == expected_kind, f"{slug}: {arch['kind']}"
        overview = _build_overview_tips(gp)
        assert overview.startswith("- "), slug
        assert arch["tips"][0] in overview or arch["tips"][0].replace("**", "") in overview.replace("**", "")

        guide = generate_guide(identity, synergies=[], use_ollama=False)
        assert guide["playstyle_guide"].startswith("- "), slug


def test_nails_archetype_mittelhammer_don_quixote():
    from limbus_guides.nlp.generation import generate_guide, _build_overview_tips
    from limbus_guides.nlp.mechanics import build_mechanic_profile
    from limbus_guides.nlp.skill_parser import build_gameplan, find_nails_archetype

    slug = "N_Corp._Mittelhammer_Don_Quixote"
    identity = load_parsed_identity(slug)
    identity["mechanic_profile"] = build_mechanic_profile(identity)
    gp = build_gameplan(identity)
    arch = find_nails_archetype(
        identity["raw_markdown"],
        gp.get("combat_passives_text", ""),
        gp.get("skills"),
    )
    assert arch is not None
    assert arch["kind"] == "nails_setup"
    assert arch["threshold"] == 5
    assert arch["has_tremor_burst"] is True
    assert "Enactment" in arch["payoff_skill"]

    overview = _build_overview_tips(gp)
    assert overview.startswith("- ")
    assert "Nails setup" in overview
    assert "Enactment" in overview

    guide = generate_guide(identity, synergies=[], use_ollama=False)
    assert "Nails" in guide["core_idea"]
    assert "5+" in guide["core_idea"]
    assert "Enactment" in guide["core_idea"]
    assert guide["playstyle_guide"].startswith("- ")
    assert "nails" in guide["playstyle_guide"].lower()


def test_stack_ramp_trigger_and_ally_filtering():
    from limbus_guides.nlp.archetypes import build_stack_ramp_tips
    from limbus_guides.nlp.mechanics import build_mechanic_profile
    from limbus_guides.nlp.skill_parser import build_gameplan, parse_passives_text

    aedd = load_parsed_identity("LCE_E.G.O_AEDD_Gregor")
    aedd["mechanic_profile"] = build_mechanic_profile(aedd)
    combat, support = parse_passives_text(aedd["raw_markdown"])
    tips = build_stack_ramp_tips(
        aedd["parsed_skills"],
        combat,
        status="Charge",
        payoff_label="High-voltage Current Discharge",
        support_text=support,
    )
    assert tips
    blob = tips[0].lower()
    assert "combat start" in blob
    assert "+10" in tips[0]
    assert "+4 charge count" not in blob or "ally" not in blob

    faust = load_parsed_identity("W_Corp._L2_Cleanup_Agent_Faust")
    faust["mechanic_profile"] = build_mechanic_profile(faust)
    gp = build_gameplan(faust)
    from limbus_guides.nlp.archetypes import _extract_stack_gains

    faust_gains = _extract_stack_gains(
        gp["skills"],
        gp.get("combat_passives_text", ""),
        status="Charge",
        support_text=gp.get("support_passive_text", ""),
    )
    assert any(g.trigger == "Attack End" for g in faust_gains)

    seven = load_parsed_identity("Seven_Assoc._South_Section_4_Faust")
    seven["mechanic_profile"] = build_mechanic_profile(seven)
    gp7 = build_gameplan(seven)
    poise_tips = gp7.get("poise_archetype", {}).get("tips", [])
    if poise_tips:
        assert "rupture" in poise_tips[0].lower()


def test_poise_archetype_kit_specific_ramp():
    from limbus_guides.nlp.mechanics import build_mechanic_profile
    from limbus_guides.nlp.skill_parser import build_gameplan

    slug = "Blade_Lineage_Salsu_Yi_Sang"
    identity = load_parsed_identity(slug)
    identity["mechanic_profile"] = build_mechanic_profile(identity)
    gp = build_gameplan(identity)
    arch = gp.get("poise_archetype")
    assert arch is not None
    tips_blob = " ".join(arch["tips"])
    assert "Ramp **Poise Potency** to **20**" not in tips_blob
    assert "S1" in tips_blob or "Striker" in tips_blob
    assert "Poise Count" in tips_blob or "Clash Win" in tips_blob


def test_charge_archetype_w_corp_heathcliff():
    from limbus_guides.nlp.generation import generate_guide, _build_core_idea, _build_overview_tips
    from limbus_guides.nlp.mechanics import build_mechanic_profile
    from limbus_guides.nlp.skill_parser import build_gameplan, find_charge_archetype

    slug = "W_Corp._L4_Cleanup_Agent_-_CCA_Heathcliff"
    identity = load_parsed_identity(slug)
    identity["mechanic_profile"] = build_mechanic_profile(identity)
    gp = build_gameplan(identity)
    arch = find_charge_archetype(
        gp.get("skills", []),
        gp.get("combat_passives_text", ""),
        mechanic_profile=identity["mechanic_profile"],
    )
    assert arch is not None
    assert arch["kind"] == "charge_scaling"
    assert "20" in arch["tips"][0]
    assert "On Hit" in arch["tips"][0] or "+5" in arch["tips"][0]
    assert "rebuild" in arch["setup_summary"].lower() or "rebuild" in " ".join(arch["tips"]).lower()

    overview = _build_overview_tips(gp)
    assert "Charge" in overview
    assert "ramp" in overview.lower() or "toward **20**" in overview.lower()

    core = _build_core_idea(identity["name"], gp)
    assert "Charge" in core
    assert "20" in core or "cycle" in core.lower()

    guide = generate_guide(identity, synergies=[], use_ollama=False)
    assert "Charge" in guide["core_idea"]
    assert "checks Charge thresholds more than he stacks" not in guide["team_suggestion_intro"]
    playstyle = guide["playstyle_guide"]
    assert "+4 Coin Power" in playstyle or "Coin Power" in playstyle
    assert "10" in playstyle
    assert "Charge Potency" in playstyle or "Clash Power" in playstyle


def test_count_mechanic_mentions_avoids_substrings():
    from limbus_guides.ingestion.unique_mechanics_registry import count_mechanic_mentions

    text = "Gain 1 Charge on hit. Do not Recharge this skill."
    assert count_mechanic_mentions(text, "Charge") == 1
    assert count_mechanic_mentions("Fully Recharge the battery.", "Charge") == 0


def test_unique_mechanics_registry_sync_and_enrich():
    from limbus_guides.ingestion.unique_mechanics_registry import (
        count_mechanic_mentions,
        load_discovered_mechanics,
        sync_from_parsed_ids,
    )
    from limbus_guides.nlp.mechanics import build_mechanic_profile
    from limbus_guides.nlp.skill_parser import build_gameplan

    result = sync_from_parsed_ids(write=True)
    assert result["total"] >= 1
    discovered = load_discovered_mechanics()
    assert any("Unending Bereavement" == n or "Unrelenting Storm" == n for n in discovered)

    identity = load_parsed_identity("Wild_Hunt_Heathcliff")
    identity["mechanic_profile"] = build_mechanic_profile(identity)
    profile = identity["mechanic_profile"]
    assert "Coffin" in profile["unique_mechanics"]
    assert "Dullahan" in profile["unique_mechanics"]
    assert "Unending Bereavement" in profile.get("key_status_effects", [])
    assert profile["unique_mechanics"]["Unending Bereavement"] >= 8
    assert profile["unique_mechanics"]["Coffin"] > profile["unique_mechanics"].get(
        "Impending Ruin", 0
    )
    md = identity["raw_markdown"]
    assert count_mechanic_mentions(md, "Coffin") >= count_mechanic_mentions(md, "Charge")

    gp = build_gameplan(identity)
    assert gp.get("unique_mechanics_archetype") is not None


def test_unique_mechanics_archetype_wild_hunt_heathcliff():
    from limbus_guides.nlp.generation import generate_guide, _build_core_idea, _build_overview_tips
    from limbus_guides.nlp.mechanics import build_mechanic_profile
    from limbus_guides.nlp.skill_parser import build_gameplan, find_unique_mechanics_archetype

    slug = "Wild_Hunt_Heathcliff"
    identity = load_parsed_identity(slug)
    identity["mechanic_profile"] = build_mechanic_profile(identity)
    gp = build_gameplan(identity)
    arch = find_unique_mechanics_archetype(
        identity["raw_markdown"],
        gp.get("combat_passives_text", ""),
        gp.get("skills", []),
        gp.get("alternate_skills", []),
        identity["mechanic_profile"],
    )
    assert arch is not None
    assert arch["kind"] == "unique_mechanics"
    assert "Dullahan" in arch["mechanics"]
    assert "Coffin" in arch["mechanics"]
    assert any("Coffin" in t for t in arch["tips"])
    assert any("Dullahan" in t for t in arch["tips"])

    overview = _build_overview_tips(gp)
    assert "Coffin" in overview
    assert "Dullahan" in overview
    assert "clash-support" not in overview.lower()

    core = _build_core_idea(identity["name"], gp)
    assert "Dullahan" in core
    assert "Coffin" in core
    assert "Sinking clash-support" not in core

    guide = generate_guide(identity, synergies=[], use_ollama=False)
    assert "Lament" in guide["playstyle_guide"]
    assert "+12% damage per Coffin" in guide["playstyle_guide"] or "Coffin" in guide["playstyle_guide"]


def test_charge_archetype_w_corp_faust():
    from limbus_guides.nlp.generation import generate_guide, _build_overview_tips
    from limbus_guides.nlp.mechanics import build_mechanic_profile
    from limbus_guides.nlp.skill_parser import build_gameplan, find_charge_archetype

    slug = "W_Corp._L2_Cleanup_Agent_Faust"
    identity = load_parsed_identity(slug)
    identity["mechanic_profile"] = build_mechanic_profile(identity)
    gp = build_gameplan(identity)
    arch = find_charge_archetype(
        gp.get("skills", []),
        gp.get("combat_passives_text", ""),
        mechanic_profile=identity["mechanic_profile"],
    )
    assert arch is not None
    assert any("Clash Power" in t for t in arch["tips"])

    overview = _build_overview_tips(gp)
    assert "Charge" in overview

    guide = generate_guide(identity, synergies=[], use_ollama=False)
    assert "5" in guide["playstyle_guide"]
    assert "Clash Power" in guide["playstyle_guide"]


def test_docent_rodion_res2_combat_and_res3_support():
    from limbus_guides.nlp.generation import generate_guide
    from limbus_guides.nlp.mechanics import build_mechanic_profile
    from limbus_guides.nlp.skill_parser import build_gameplan, find_support_archetype

    slug = "The_Ring_Fauvist_Docent_Rodion"
    identity = load_parsed_identity(slug)
    identity["mechanic_profile"] = build_mechanic_profile(identity)
    gp = build_gameplan(identity)
    arch = find_support_archetype(
        gp.get("support_passive_text", ""),
        gp.get("combat_passives_text", ""),
        raw_markdown=identity["raw_markdown"],
        mechanic_profile=identity["mechanic_profile"],
    )
    assert arch is not None
    assert arch["kind"] == "deploy_order"
    assert "Nice and Slow" in gp["support_passive_text"]
    assert "Needs a Rougher Touch" not in gp["support_passive_text"]
    assert "Needs a Rougher Touch" in gp["combat_passives_text"]
    assert "Mauled Color" in gp["combat_passives_text"]

    guide = generate_guide(identity, synergies=[], use_ollama=False)
    assert "Nice and Slow" in guide["core_idea"]
    assert "Needs a Rougher Touch" not in guide["core_idea"]
    assert "Needs a Rougher Touch" in guide["playstyle_guide"]
    assert "Mauled Color" in guide["playstyle_guide"]


def test_res2_passive_classified_as_combat():
    from limbus_guides.nlp.skill_parser import parse_passives_text

    slug = "Blade_Lineage_Salsu_Sinclair"
    identity = load_parsed_identity(slug)
    combat, support = parse_passives_text(identity["raw_markdown"])
    assert "Bloodied Hands" in support
    assert "Slayer" not in support
    assert "Slayer" in combat


@pytest.mark.parametrize(
    "slug,key,kind",
    [
        ("Firefist_Office_Survivor_Gregor", "burn_archetype", "burn_stacker"),
        ("Kurokumo_Clan_Captain_Ishmael", "bleed_archetype", "bleed_stacker"),
        ("T_Corp._Class_3_Collection_Staff_Don_Quixote", "tremor_archetype", "tremor_stacker"),
        ("Devyat'_Assoc._North_Section_3_Sinclair", "rupture_archetype", "rupture_stacker"),
        ("Lobotomy_E.G.O_The_Sword_Sharpened_with_Tears_Rodion", "sinking_archetype", "sinking_stacker"),
        ("Blade_Lineage_Salsu_Yi_Sang", "poise_archetype", "poise_stacker"),
        ("Zwei_Assoc._West_Section_3_Ishmael", "aggro_archetype", "aggro_tank"),
        ("Seven_Assoc._South_Section_4_Faust", "haste_archetype", "haste_tempo"),
        ("Blade_Lineage_Mentor_Meursault", "paralyze_archetype", "paralyze_control"),
        ("Kurokumo_Clan_Captain_Ishmael", "fragile_archetype", "fragile_setup"),
    ],
)
def test_status_archetypes_detected(slug, key, kind):
    from limbus_guides.nlp.mechanics import build_mechanic_profile
    from limbus_guides.nlp.skill_parser import build_gameplan

    identity = load_parsed_identity(slug)
    identity["mechanic_profile"] = build_mechanic_profile(identity)
    gp = build_gameplan(identity)
    arch = gp.get(key)
    assert arch is not None, f"{slug} missing {key}"
    assert arch["kind"] == kind


def test_discard_archetype_synthetic():
    from limbus_guides.nlp.archetypes import find_discard_archetype

    md = (
        "## Skills\n### Skill 1: Test\n"
        "**[On Use] Discard 1 Skill to gain 1 Insight ; Erudition: Discard grants Shield**\n"
    )
    arch = find_discard_archetype([], combat_text=md, raw_markdown=md)
    assert arch is not None
    assert arch["kind"] == "discard_resource"
    assert not any("resource loop" in t.lower() for t in arch["tips"])


def test_sp_regenerator_archetype_liu_yi_sang():
    from limbus_guides.nlp.generation import _build_core_idea, _build_overview_tips
    from limbus_guides.nlp.mechanics import build_mechanic_profile
    from limbus_guides.nlp.skill_parser import build_gameplan

    slug = "Liu_Assoc._South_Section_3_Yi_Sang"
    identity = load_parsed_identity(slug)
    identity["mechanic_profile"] = build_mechanic_profile(identity)
    gp = build_gameplan(identity)
    arch = gp.get("sp_regenerator_archetype")
    assert arch is not None, slug
    assert arch["kind"] == "sp_regenerator"

    overview = _build_overview_tips(gp)
    assert arch["tips"][0] in overview or arch["tips"][0].replace("**", "") in overview.replace("**", "")

    core = _build_core_idea(identity["name"], gp)
    assert arch["setup_summary"] in core


def test_hp_regenerator_archetype_priest_gregor():
    from limbus_guides.nlp.generation import _build_core_idea, _build_overview_tips
    from limbus_guides.nlp.mechanics import build_mechanic_profile
    from limbus_guides.nlp.skill_parser import build_gameplan

    slug = "The_Priest_of_La_Manchaland_Gregor"
    identity = load_parsed_identity(slug)
    identity["mechanic_profile"] = build_mechanic_profile(identity)
    gp = build_gameplan(identity)
    hp_arch = gp.get("hp_regenerator_archetype")
    sp_arch = gp.get("sp_regenerator_archetype")
    assert hp_arch is not None, slug
    assert sp_arch is not None, slug
    assert hp_arch["kind"] == "hp_regenerator"
    assert sp_arch["kind"] == "sp_regenerator"

    overview = _build_overview_tips(gp)
    assert hp_arch["tips"][0] in overview or hp_arch["tips"][0].replace("**", "") in overview.replace("**", "")
    assert sp_arch["tips"][0] in overview or sp_arch["tips"][0].replace("**", "") in overview.replace("**", "")

    core = _build_core_idea(identity["name"], gp)
    assert hp_arch["setup_summary"] in core
    assert sp_arch["setup_summary"] in core


def test_sp_regenerator_skips_self_only_heal():
    from limbus_guides.nlp.mechanics import build_mechanic_profile
    from limbus_guides.nlp.skill_parser import build_gameplan

    slug = "Liu_Assoc._South_Section_5_Hong_Lu"
    identity = load_parsed_identity(slug)
    identity["mechanic_profile"] = build_mechanic_profile(identity)
    gp = build_gameplan(identity)
    assert gp.get("sp_regenerator_archetype") is None


def test_haste_tip_matches_defense_style():
    from limbus_guides.nlp.generation import generate_guide
    from limbus_guides.nlp.mechanics import build_mechanic_profile
    from limbus_guides.nlp.skill_parser import build_gameplan

    slug = "Heishou_Pack_-_Wu_Branch_Adept_Yi_Sang"
    identity = load_parsed_identity(slug)
    identity["mechanic_profile"] = build_mechanic_profile(identity)
    gp = build_gameplan(identity)
    arch = gp.get("haste_archetype")
    assert arch is not None
    tip = arch["tips"][0].lower()
    assert "evade sequence" not in tip
    assert "carry line" not in tip
    assert "faster than the target" in tip

    guide = generate_guide(identity, synergies=[], use_ollama=False)
    playstyle = guide["playstyle_guide"].lower()
    assert "carry line" not in playstyle
    assert "evade sequence" not in playstyle


def test_tremor_archetype_unique_subtype_blurb():
    from limbus_guides.nlp.mechanics import build_mechanic_profile
    from limbus_guides.nlp.skill_parser import build_gameplan

    slug = "The_Thumb_East_Capo_IIII_Meursault"
    identity = load_parsed_identity(slug)
    identity["mechanic_profile"] = build_mechanic_profile(identity)
    gp = build_gameplan(identity)
    arch = gp.get("tremor_archetype")
    assert arch is not None
    assert "Scorch" in arch["setup_summary"]
    tips_blob = " ".join(arch["tips"])
    assert "Tremor — Scorch" in tips_blob
    assert "Wrath" in tips_blob


def test_thumb_capo_core_idea_describes_damage_kit():
    from limbus_guides.nlp.generation import _build_core_idea, generate_guide
    from limbus_guides.nlp.mechanics import build_mechanic_profile
    from limbus_guides.nlp.skill_parser import build_gameplan

    slug = "The_Thumb_East_Capo_IIII_Meursault"
    identity = load_parsed_identity(slug)
    identity["mechanic_profile"] = build_mechanic_profile(identity)
    gp = build_gameplan(identity)
    core = _build_core_idea(identity["name"], gp)
    assert "Tigermark" in core
    assert "Burn" in core
    assert "Scorch" in core
    assert "**Tremor — Scorch**" in core
    assert "damage carry" in core.lower()
    assert "Burn applicator" not in core
    assert "; equipping defense" not in core

    guide = generate_guide(identity, synergies=[], use_ollama=False)
    assert guide["core_idea"] == core


def test_thumb_soldato_sinclair_core_idea_describes_damage_kit():
    from limbus_guides.nlp.generation import _build_core_idea, generate_guide
    from limbus_guides.nlp.mechanics import build_mechanic_profile
    from limbus_guides.nlp.skill_parser import build_gameplan

    slug = "The_Thumb_East_Soldato_II_Sinclair"
    identity = load_parsed_identity(slug)
    identity["mechanic_profile"] = build_mechanic_profile(identity)
    gp = build_gameplan(identity)
    core = _build_core_idea(identity["name"], gp)
    assert "Scorch Propellant Ammo" in core
    assert "Burn" in core
    assert "Scorch" in core
    assert "**Tremor — Scorch**" in core
    assert "damage carry" in core.lower()
    assert "Ammunition Tribute" in core
    assert "Support passive" in core
    assert "Damage Up" in core
    assert "Unbreakable" in core
    assert "Burn applicator" not in core
    assert "; gains **Damage Up**" not in core
    assert core.count("resupply") == 1 or "Ammunition Tribute" in core

    guide = generate_guide(identity, synergies=[], use_ollama=False)
    assert guide["core_idea"] == core


def test_devyat_sinclair_core_idea_describes_courier_loop():
    from limbus_guides.nlp.generation import _build_core_idea, generate_guide
    from limbus_guides.nlp.mechanics import build_mechanic_profile
    from limbus_guides.nlp.skill_parser import build_gameplan

    slug = "Devyat'_Assoc._North_Section_3_Sinclair"
    identity = load_parsed_identity(slug)
    identity["mechanic_profile"] = build_mechanic_profile(identity)
    gp = build_gameplan(identity)
    core = _build_core_idea(identity["name"], gp)
    assert "Courier Trunk" in core
    assert "Courier Trunk — Sinclair" in core
    assert "Shield (max 20%)" not in core
    assert "15" in core
    assert "Strategic R&R" in core
    assert "Upon Retreat" in core
    assert "maintenance" in core.lower() or "W-wait" in core
    assert "halves" in core.lower()
    assert "Rupture focus" not in core
    assert core.count("Devyat") >= 1

    guide = generate_guide(identity, synergies=[], use_ollama=False)
    assert guide["core_idea"] == core


def test_tremor_unique_subtype_bold_in_core_idea():
    from limbus_guides.nlp.generation import _build_core_idea
    from limbus_guides.nlp.mechanics import build_mechanic_profile
    from limbus_guides.nlp.skill_parser import build_gameplan

    cases = {
        "District_20_Yurodivy_Hong_Lu": "Reverb",
        "Öufi_Assoc._South_Section_3_Heathcliff": "Decay",
        "T_Corp._Class_3_Collection_Staff_Don_Quixote": "Chain",
        "N_Corp._E.G.O_Contempt,_Awe_Ryōshū": "Hemorrhage",
    }
    for slug, subtype in cases.items():
        identity = load_parsed_identity(slug)
        identity["mechanic_profile"] = build_mechanic_profile(identity)
        gp = build_gameplan(identity)
        core = _build_core_idea(identity["name"], gp)
        assert f"**Tremor — {subtype}** control" in core
        assert f"**Tremor** control (Tremor — {subtype})" not in core


def test_archetype_tips_skip_basic_mechanic_primers():
    """Playstyle tips should be tactical, not status-effect tutorials."""
    from limbus_guides.nlp.mechanics import build_mechanic_profile
    from limbus_guides.nlp.generation import _build_overview_tips
    from limbus_guides.nlp.skill_parser import build_gameplan

    banned = (
        "deals damage when the target is hit",
        "each coin flip on a bleeding target",
        "drains sp when the target is hit",
        "turn end damage",
        "affected coins flip at 0 power",
        "+10% damage taken",
        "unlock full damage",
        "cash out with",
        "spend window",
        "ticks and attack procs",
        "coin flips keep proccing",
        "while stacks last",
        "while stacks remain",
        "potency and count",
        "stagger threshold lets you",
        "sp drain makes",
        "hits during your rotation",
        "use every appearance to build up",
        "keeps poise climbing",
        "heavy chain",
        "attack chain",
        "spend turn",
        "high-sp spenders",
        "passive top-ups",
        "keep this unit deployed",
        "keep this unit on field",
        "stay on field",
        "protect this slot",
        "protect this unit",
        "staying alive and deployed",
        "prioritise staying alive",
        "keeps bleed climbing",
        "evade sequence",
        "carry line",
        "stagger or death",
        "backup identity for this sinner",
        "slot a backup identity on this sinner",
    )
    for slug in (
        "Devyat'_Assoc._North_Section_3_Sinclair",
        "Kurokumo_Clan_Captain_Ishmael",
        "W_Corp._L4_Cleanup_Agent_-_CCA_Heathcliff",
        "Tingtang_Gang_Gangleader_Hong_Lu",
        "The_Thumb_East_Capo_IIII_Meursault",
        "Wild_Hunt_Heathcliff",
        "Blade_Lineage_Salsu_Yi_Sang",
    ):
        identity = load_parsed_identity(slug)
        identity["mechanic_profile"] = build_mechanic_profile(identity)
        gp = build_gameplan(identity)
        tips = _build_overview_tips(gp)
        blob = " ".join(tips).lower()
        for phrase in banned:
            assert phrase not in blob, f"{slug} playstyle tip still explains basics: {phrase!r}"
