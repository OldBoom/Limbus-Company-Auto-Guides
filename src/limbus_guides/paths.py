"""Project path helpers."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DOCS_DIR = ROOT / "docs"
DOMAIN_PRIMER_PATH = DOCS_DIR / "domain-primer.md"
PARSED_IDS_DIR = DOCS_DIR / "parsed-ids"
DATA_DIR = ROOT / "data"
IDENTITIES_DIR = DATA_DIR / "identities"
GUIDES_DIR = DATA_DIR / "guides"
CONFIG_DIR = ROOT / "config"
