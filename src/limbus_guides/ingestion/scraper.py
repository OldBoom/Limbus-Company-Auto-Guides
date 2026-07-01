"""Scrape identity pages from limbuscompany.wiki.gg."""

from __future__ import annotations

import re
import time
from urllib.parse import quote

import requests
from bs4 import BeautifulSoup

from limbus_guides.ingestion.markdown_loader import parse_identity_markdown, save_identity_json
from limbus_guides.paths import CONFIG_DIR

WIKI_BASE = "https://limbuscompany.wiki.gg/wiki/"
USER_AGENT = "LimbusCompanyAutoGuides/0.1 (academic NLP project)"


def fetch_wiki_page(slug: str) -> str:
    url = WIKI_BASE + quote(slug.replace(" ", "_"))
    resp = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=30)
    resp.raise_for_status()
    return resp.text


def html_to_markdown_stub(html: str, slug: str) -> str:
    """Extract main content from wiki HTML into a simplified text blob for parsing.

    Full parsing follows docs/301-wiki-identity-parsing.mdc; this stub extracts
    the article body for prototype ingestion.
    """
    soup = BeautifulSoup(html, "html.parser")
    content = soup.find("div", class_="mw-parser-output") or soup.find("article") or soup.body
    if not content:
        return f"# {slug.replace('_', ' ')}\n\n(No content extracted)"
    for tag in content.find_all(["script", "style", "nav", "table", "noscript"]):
        tag.decompose()
    text = content.get_text("\n", strip=True)
    title = slug.replace("_", " ")
    h1 = soup.find("h1")
    if h1:
        title = h1.get_text(strip=True)
    return f"# {title}\n\n{text}"


def scrape_identity(slug: str, delay_s: float = 1.0) -> dict:
    html = fetch_wiki_page(slug)
    md_stub = html_to_markdown_stub(html, slug)
    identity = parse_identity_markdown(md_stub, slug)
    identity["source"] = "wiki_scrape"
    identity["wiki_url"] = WIKI_BASE + quote(slug.replace(" ", "_"))
    time.sleep(delay_s)
    return identity


def scrape_config_identities() -> list[dict]:
    from limbus_guides.config_io import load_json_config

    config_path = CONFIG_DIR / "sinners.json"
    if not config_path.exists():
        return []
    config = load_json_config(config_path)
    slugs: list[str] = list(config.get("parsed_reference_slugs", []))
    for sinner in config.get("sinners", []):
        slugs.extend(sinner.get("identities", []))
    seen: set[str] = set()
    results = []
    for slug in slugs:
        if slug in seen:
            continue
        seen.add(slug)
        try:
            results.append(scrape_identity(slug))
        except Exception as exc:
            results.append({"slug": slug, "error": str(exc)})
    return results
