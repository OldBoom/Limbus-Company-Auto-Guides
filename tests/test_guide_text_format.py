"""Tests for dashboard guide text formatting."""

from limbus_guides.dashboard.text_format import (
    build_status_category_map,
    format_core_idea_html,
    format_guide_html,
    format_inline_guide_text,
    guide_format_css,
)


def test_status_category_map_has_core_keywords():
    cats = build_status_category_map()
    assert cats["Burn"] == "negative"
    assert cats["Poise"] == "positive"
    assert cats["Charge"] == "positive"
    assert cats["Haste"] == "positive"
    assert cats["Bind"] == "negative"


def test_format_inline_highlights_statuses_and_numbers():
    html = format_inline_guide_text("Apply 3 Burn and gain 2 Poise at 10+ Charge.")
    assert 'class="lc-status-neg"' in html
    assert "Burn" in html
    assert 'class="lc-status-pos"' in html
    assert "Poise" in html
    assert 'class="lc-num"' in html
    assert ">3<" in html
    assert ">10<" in html
    assert ">2<" in html


def test_format_inline_preserves_apostrophes():
    """Apostrophes must not be broken by number highlighting (&#x27; contains 27)."""
    reason = (
        "This identity's 'One day I'll wear me Armour for Cancelled Trains' "
        "inflicts Charge — teammate scales off Charge."
    )
    html = format_inline_guide_text(reason)
    assert 'lc-num">27</span>' not in html
    assert "identity&#x27;s" in html
    assert "I&#x27;ll" in html
    html2 = format_inline_guide_text("At 10+ Charge with I'll.")
    assert "I&#x27;ll" in html2
    assert ">10<" in html2


def test_format_inline_preserves_bold():
    html = format_inline_guide_text("**Burn** stacks at +5.")
    assert "<strong>" in html
    assert 'class="lc-status-neg"' in html
    assert 'class="lc-num"' in html
    assert ">+5<" in html


def test_format_guide_html_wraps_bullets():
    text = "- Lead with Burn.\n" + "*\u21b3 follow with Tremor."
    html = format_guide_html(text)
    assert "lc-guide-bullet" in html
    assert "lc-guide-alt" in html


def test_guide_format_css_includes_colour_classes():
    css = guide_format_css()
    assert ".lc-status-pos" in css
    assert ".lc-status-neu" in css
    assert ".lc-status-neg" in css
    assert ".lc-num" in css
    assert "#2dd4bf" in css


def test_status_category_map_includes_registry_mechanics():
    cats = build_status_category_map()
    assert cats["Coffin"] == "neutral"
    assert cats["Dullahan"] == "neutral"
    # Standard debuff classification wins over registry neutral default.
    assert cats["Impending Ruin"] == "negative"


def test_format_inline_highlights_registry_mechanics():
    html = format_inline_guide_text("Spend Coffin, then mount Dullahan for +10% damage.")
    assert 'class="lc-status-neu"' in html
    assert "Coffin" in html
    assert "Dullahan" in html


def test_format_core_idea_html_structure():
    text = (
        "Wild Hunt Heathcliff is a Damage Dealer / Status Specialist — "
        "**Dullahan** + **Coffin** carry — stack resources and cash out. "
        "Scaling conditions: Coin Power +1 per 3 Sinking (max +2). "
        "Support passive (**Endless Lamentation**) buffs teammates."
    )
    html = format_core_idea_html(text)
    assert "lc-core-idea" in html
    assert "lc-core-role" in html
    assert "Damage Dealer" in html
    assert "Status Specialist" in html
    assert "lc-core-hook" in html
    assert "Coffin" in html
    assert "lc-core-scaling" in html
    assert "Scaling" in html
    assert "lc-core-support" in html
    assert "Endless Lamentation" in html


def test_format_core_idea_html_w_corp_abbrev_name():
    """Corp. in the identity name must not break sentence splitting."""
    text = (
        "W Corp. L4 Cleanup Agent - CCA Heathcliff is a Damage Dealer / Support — "
        "**Charge** cycle — build Count toward **20**, then rebuild. "
        "**Guard: CCA Overcharge** queues an extra finisher next turn. "
        "Scaling conditions: Clash Power +1 per 6 Charge (max +2). "
        "Support passive (**Example Passive**) keys off deployment order."
    )
    html = format_core_idea_html(text)
    assert "lc-core-hook" in html
    assert "Charge" in html
    assert "lc-core-scaling" in html
    assert "lc-core-detail" in html
    assert "Guard" in html


def test_format_core_idea_html_liu_assoc():
    text = (
        "Liu Assoc. South Section 3 Yi Sang is a Damage Dealer — "
        "**Poise** fighter — **20 Potency** for guaranteed crits."
    )
    html = format_core_idea_html(text)
    assert "lc-core-hook" in html
    assert "Poise" in html


def test_format_core_idea_html_fallback():
    html = format_core_idea_html("Plain summary without the standard lead pattern.")
    assert 'class="lc-core-idea"' in html
    assert "lc-guide-line" in html
