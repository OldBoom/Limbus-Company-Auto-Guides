"""Tests for identity portrait parsing from the wiki list page."""

from limbus_guides.ingestion.identity_portraits import (
    parse_list_page_identity_images,
    resolve_portrait_thumb,
    thumb_url_to_full,
)

SAMPLE = """
<a href="/wiki/Blade_Lineage_Salsu_Yi_Sang"><img src="/images/thumb/Blade_Lineage_Salsu_Yi_Sang.png/125px-x.png"></a>
<a href="/wiki/Blade_Lineage_Salsu_Yi_Sang"><img src="/images/thumb/Blade_Lineage_Salsu_Yi_Sang_Uptied.png/125px-y.png"></a>
<a href="/wiki/List_of_Identities#yisang"><img src="/images/thumb/Yi_Sang_Icon.png/60px-Yi_Sang_Icon.png"></a>
<a href="/wiki/The_House_of_Spiders:_The_Ring_Apprentice_Faust"><img src="/images/thumb/The_House_of_Spiders_The_Ring_Apprentice_Faust_Uptied.png/125px-a.png"></a>
"""


def test_parse_prefers_uptied_artwork() -> None:
    by_path = parse_list_page_identity_images(SAMPLE)
    assert "Blade_Lineage_Salsu_Yi_Sang" in by_path
    assert "_Uptied" in by_path["Blade_Lineage_Salsu_Yi_Sang"]
    assert "Yi_Sang_Icon" not in "".join(by_path.values())


def test_resolve_ring_apprentice_slug() -> None:
    by_path = parse_list_page_identity_images(SAMPLE)
    thumb = resolve_portrait_thumb("Ring_Apprentice_Faust", by_path)
    assert thumb is not None
    assert "Ring_Apprentice" in thumb


def test_thumb_url_to_full() -> None:
    url = thumb_url_to_full("/images/thumb/Foo_Uptied.png/125px-Foo_Uptied.png?abc")
    assert url.endswith("/images/Foo_Uptied.png")
