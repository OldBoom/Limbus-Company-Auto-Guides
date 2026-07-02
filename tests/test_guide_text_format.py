"""Tests for dashboard guide text formatting."""

from limbus_guides.dashboard.text_format import (
    build_status_category_map,
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
