"""Unit tests for wiki_parser ingestion."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from limbus_guides.ingestion.wiki_parser import (
    _collect_skills,
    _parse_skill_params,
    filename_to_wiki_title,
    render_markdown,
)
from limbus_guides.nlp.skill_parser import parse_all_skills
from limbus_guides.nlp.skill_rolls import compute_coin_count


def _fake_idpage_body(skill_lines: str) -> str:
    return (
        "|prefix=Test ID\n|sinner=Test\n|quote=Hi\n|hp=66\n|hpgrowth=2\n"
        "|speed=3~7\n|defmod=+0\n|season=0\n|rarity=3\n|releasedate=2020.01.01\n"
        f"{skill_lines}"
    )


def test_coin_count_emits_blank_first_coin():
    params = {
        "slevel": "3",
        "name": "Test Skill",
        "coin": "4",
        "ce2": "Effect on coin 2",
        "ce3": "Effect on coin 3",
        "ce4": "Effect on coin 4",
        "spower": "3",
        "cpower": "+3",
        "amt": "4",
    }
    skill = _parse_skill_params(params)
    assert len(skill["coins"]) == 4
    assert skill["coins"][0]["coin"] == 1
    assert skill["coins"][0]["effect"] == "—"
    assert skill["coins"][3]["effect"] == "Effect on coin 4"


def test_coin_zero_emits_no_rows():
    params = {
        "slevel": "2",
        "name": "Heel Turn",
        "coin": "0",
        "spower": "7",
        "cpower": "+2",
        "amt": "2",
        "ce1": "[Clash Win] should not appear",
    }
    skill = _parse_skill_params(params)
    assert skill["coins"] == []


def test_atkweight_preferred_over_amt():
    params = {
        "slevel": "3",
        "name": "Alt Skill",
        "coin": "1",
        "amt": "0",
        "atkweight": "3",
        "spower": "4",
        "cpower": "+3",
    }
    skill = _parse_skill_params(params)
    assert skill["atk_weight"] == 3


def test_tiered_awakening_stats():
    params = {
        "slevel": "1",
        "name": "Awakened",
        "4spower": "10",
        "4cpower": "-4",
        "coin": "1",
        "ce1": "Hit",
    }
    skill = _parse_skill_params(params)
    assert skill["base_power"] == 10
    assert skill["coin_power"] == "-4"


def test_alternate_skill_interleaved_in_markdown():
    body = _fake_idpage_body(
        "|skill1={{UptieSkills|slevel=1|name=Primary|spower=3|cpower=+2|coin=1|ce1=A}}\n"
        "|skill1-2={{UptieSkills|slevel=1|name=Alternate|spower=5|cpower=+3|coin=2|ce1=B|ce2=C}}\n"
        "|skill2={{UptieSkills|slevel=2|name=Second|spower=4|cpower=+2|coin=1|ce1=D}}\n"
    )
    wt = "{{IDPage|" + body + "}}"
    md = render_markdown("Test_ID", wt)
    primary, alternates = parse_all_skills(md)
    assert len(primary) == 2
    assert len(alternates) == 1
    assert alternates[0]["name"] == "Alternate"
    assert "### Skill 1: Primary" in md
    assert md.index("### Skill 1: Primary") < md.index("### Skill 1: Alternate")
    assert md.index("### Skill 1: Alternate") < md.index("### Skill 2: Second")


def test_status_effect_exclusive_state_section():
    body = _fake_idpage_body(
        "|skill1={{UptieSkills|slevel=1|name=Iron Skill|spower=3|cpower=+2|coin=1|ce1=X|"
        "se={{StatusEffect|Iron Maiden|r}} exclusive Skill}}\n"
    )
    wt = "{{IDPage|" + body + "}}"
    md = render_markdown("Test_ID", wt)
    assert "## Skills — Iron Maiden" in md


def test_filename_to_wiki_title_overrides():
    assert filename_to_wiki_title("Ring_Apprentice_Faust") == (
        "The_House_of_Spiders:_The_Ring_Apprentice_Faust"
    )
    assert filename_to_wiki_title("Ring_Pointillist_Student_Yi_Sang") == (
        "The_Ring_Pointillist_Student_Yi_Sang"
    )
    assert filename_to_wiki_title("Lobotomy_E.G.O_Magic_Bullet_Outis") == (
        "Lobotomy_E.G.O::Magic_Bullet_Outis"
    )
    assert filename_to_wiki_title("LCE_E.G.O_AEDD_Gregor") == (
        "LCE_E.G.O::AEDD_Gregor"
    )
    assert filename_to_wiki_title("N_Corp._E.G.O_Contempt,_Awe_Ryōshū") == (
        "N_Corp._E.G.O::Contempt,_Awe_Ryōshū"
    )


def test_coin_count_round_trip_for_pointillist_pattern():
    params = {
        "slevel": "3",
        "name": "Pointillist",
        "coin": "4",
        "ce2": "c2",
        "ce3": "c3",
        "ce4": "c4",
        "spower": "3",
        "cpower": "+3",
        "amt": "4",
    }
    skill = _parse_skill_params(params)
    parsed_skill = {
        "coin_effects": [{"coin": c["coin"], "effect": c["effect"]} for c in skill["coins"]],
    }
    assert compute_coin_count(parsed_skill) == 4
