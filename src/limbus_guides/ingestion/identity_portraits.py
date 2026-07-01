"""Parse identity portraits from the wiki List of Identities page."""

from __future__ import annotations

import json
import re
import time
from pathlib import Path
from urllib.parse import unquote

import requests
from bs4 import BeautifulSoup

from limbus_guides.ingestion.wiki_parser import filename_to_wiki_title, wiki_title_to_stem

LIST_PAGE_URL = "https://limbuscompany.wiki.gg/wiki/List_of_Identities"
WIKI_BASE = "https://limbuscompany.wiki.gg"
USER_AGENT = "LimbusCompanyAutoGuides/0.1 (academic NLP project)"

_THUMB_RE = re.compile(r"/images/thumb/(.+?)/\d+px-")


def thumb_url_to_full(thumb_src: str) -> str:
    """Convert a MediaWiki thumb URL to the full-size image URL."""
    if thumb_src.startswith("http"):
        path = thumb_src
    else:
        path = thumb_src
    m = _THUMB_RE.search(path)
    if m:
        return f"{WIKI_BASE}/images/{m.group(1)}"
    if path.startswith("/"):
        return f"{WIKI_BASE}{path}"
    return path


def parse_list_page_identity_images(html: str) -> dict[str, str]:
    """
    Parse identity portrait thumb URLs keyed by wiki page path.

    Skips sinner header icons and anchor-only links. When both base and Uptied
    portraits exist, prefers the Uptied artwork.
    """
    soup = BeautifulSoup(html, "html.parser")
    by_path: dict[str, str] = {}

    for anchor in soup.select('a[href^="/wiki/"]'):
        href = anchor.get("href", "")
        if href.startswith("/wiki/List_of_Identities#") or "/wiki/List_of_" in href:
            continue
        img = anchor.find("img")
        if not img:
            continue
        src = img.get("src", "")
        if not src or "_Icon.png" in src:
            continue

        wiki_path = unquote(href.removeprefix("/wiki/"))
        is_uptied = "_Uptied" in src
        prev = by_path.get(wiki_path)
        if prev is None or (is_uptied and "_Uptied" not in prev):
            by_path[wiki_path] = src

    return by_path


def slug_to_wiki_path(slug: str) -> str:
    """Map project identity slug to the wiki page path used on List of Identities."""
    return filename_to_wiki_title(slug).replace(" ", "_")


def resolve_portrait_thumb(slug: str, by_path: dict[str, str]) -> str | None:
    """Find the list-page thumb URL for a project identity slug."""
    direct = by_path.get(slug_to_wiki_path(slug))
    if direct:
        return direct
    for path, src in by_path.items():
        if wiki_title_to_stem(path) == slug:
            return src
    return None


def fetch_list_page_html() -> str:
    resp = requests.get(
        LIST_PAGE_URL,
        headers={"User-Agent": USER_AGENT},
        timeout=45,
    )
    resp.raise_for_status()
    return resp.text


def download_image(url: str) -> bytes:
    resp = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=60)
    resp.raise_for_status()
    return resp.content


def list_all_identity_slugs(html: str | None = None) -> list[str]:
    """Return project slugs for every identity portrait linked on the list page."""
    page_html = html if html is not None else fetch_list_page_html()
    by_path = parse_list_page_identity_images(page_html)
    return sorted({wiki_title_to_stem(path) for path in by_path})


def fetch_all_listed_portraits(
    out_dir: Path,
    *,
    delay_s: float = 0.35,
) -> dict[str, dict]:
    """Download portraits for every identity on the wiki list page."""
    page_html = fetch_list_page_html()
    by_path = parse_list_page_identity_images(page_html)
    slugs = sorted({wiki_title_to_stem(path) for path in by_path})
    return fetch_identity_portraits(slugs, out_dir, delay_s=delay_s, by_path=by_path)


def fetch_identity_portraits(
    slugs: list[str],
    out_dir: Path,
    *,
    delay_s: float = 0.35,
    by_path: dict[str, str] | None = None,
) -> dict[str, dict]:
    """
    Download one portrait per identity slug into ``out_dir``.

    Writes ``manifest.json`` mapping slug -> {filename, wiki_path, source_url}.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    if by_path is None:
        by_path = parse_list_page_identity_images(fetch_list_page_html())

    manifest: dict[str, dict] = {}
    missing: list[str] = []

    for slug in slugs:
        thumb = resolve_portrait_thumb(slug, by_path)
        if not thumb:
            missing.append(slug)
            continue

        full_url = thumb_url_to_full(thumb)
        ext = Path(unquote(full_url.split("?")[0])).suffix or ".png"
        filename = f"{slug}{ext}"
        dest = out_dir / filename

        if not dest.exists():
            dest.write_bytes(download_image(full_url))
            time.sleep(delay_s)

        wiki_path = slug_to_wiki_path(slug)
        for path in by_path:
            if wiki_title_to_stem(path) == slug:
                wiki_path = path
                break

        manifest[slug] = {
            "filename": filename,
            "wiki_path": wiki_path,
            "source_url": full_url,
        }

    manifest_path = out_dir / "manifest.json"
    manifest_path.write_text(
        json.dumps({"identities": manifest, "missing": missing}, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return {"identities": manifest, "missing": missing}
