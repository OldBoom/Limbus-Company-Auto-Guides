"""End-to-end pipeline orchestration."""

from __future__ import annotations

import json
import time
from pathlib import Path

from limbus_guides.ingestion.markdown_loader import ingest_parsed_ids_to_json, load_all_parsed
from limbus_guides.nlp.generation import generate_guide
from limbus_guides.nlp.keywords import extract_keywords
from limbus_guides.nlp.mechanics import build_mechanic_profile
from limbus_guides.nlp.skill_rolls import build_roll_normalizer
from limbus_guides.nlp.synergy import find_synergy_teammates
from limbus_guides.paths import GUIDES_DIR, IDENTITIES_DIR


def load_identities_json(identities_dir: Path | None = None) -> dict[str, dict]:
    base = identities_dir or IDENTITIES_DIR
    roster: dict[str, dict] = {}
    for path in sorted(base.glob("*.json")):
        roster[path.stem] = json.loads(path.read_text(encoding="utf-8"))
    return roster


def run_pipeline(
    identities_dir: Path | None = None,
    guides_dir: Path | None = None,
    use_ollama: bool = False,
) -> dict[str, dict]:
    """Ingest parsed IDs → mechanic profiles → synergies → guides."""
    t0 = time.perf_counter()
    dest_id = identities_dir or IDENTITIES_DIR
    dest_guides = guides_dir or GUIDES_DIR

    ingest_parsed_ids_to_json(out_dir=dest_id)

    from limbus_guides.ingestion.unique_mechanics_registry import sync_from_parsed_ids

    mech_sync = sync_from_parsed_ids()
    if mech_sync["added"]:
        print(f"Registered {len(mech_sync['added'])} new unique mechanic(s): {', '.join(mech_sync['added'])}")

    roster = load_identities_json(dest_id)
    if not roster:
        roster = load_all_parsed()
        for slug, data in roster.items():
            (dest_id / f"{slug}.json").write_text(
                json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8"
            )

    profiles = {slug: build_mechanic_profile(data) for slug, data in roster.items()}
    keywords = extract_keywords(roster)
    roll_normalizer = build_roll_normalizer(roster)

    guides: dict[str, dict] = {}
    dest_guides.mkdir(parents=True, exist_ok=True)

    for slug, identity in roster.items():
        identity = dict(identity)
        identity["mechanic_profile"] = profiles[slug]
        identity["keywords"] = keywords.get(slug, [])
        synergies = find_synergy_teammates(identity, roster, profiles)
        guide = generate_guide(identity, synergies, use_ollama=use_ollama, normalizer=roll_normalizer)
        output = {
            "identity_slug": slug,
            "identity_name": identity.get("name"),
            "sinner": identity.get("sinner"),
            "mechanic_profile": profiles[slug],
            "synergies": synergies,
            **guide,
        }
        guides[slug] = output
        (dest_guides / f"{slug}.json").write_text(
            json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8"
        )

    elapsed_ms = int((time.perf_counter() - t0) * 1000)
    manifest = {
        "identity_count": len(guides),
        "elapsed_ms": elapsed_ms,
        "guides_dir": str(dest_guides),
    }
    (dest_guides / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return guides


def run_for_slug(
    slug: str,
    *,
    identities_dir: Path | None = None,
    guides_dir: Path | None = None,
    use_ollama: bool = False,
) -> dict:
    """Re-ingest roster and regenerate guide JSON for a single identity."""
    dest_id = identities_dir or IDENTITIES_DIR
    dest_guides = guides_dir or GUIDES_DIR

    ingest_parsed_ids_to_json(out_dir=dest_id)
    roster = load_identities_json(dest_id)
    if slug not in roster:
        raise KeyError(f"Identity slug not found after ingest: {slug!r}")

    from limbus_guides.ingestion.unique_mechanics_registry import sync_from_parsed_ids

    sync_from_parsed_ids()

    profiles = {s: build_mechanic_profile(data) for s, data in roster.items()}
    keywords = extract_keywords(roster)
    roll_normalizer = build_roll_normalizer(roster)

    identity = dict(roster[slug])
    identity["mechanic_profile"] = profiles[slug]
    identity["keywords"] = keywords.get(slug, [])
    synergies = find_synergy_teammates(identity, roster, profiles)
    guide = generate_guide(identity, synergies, use_ollama=use_ollama, normalizer=roll_normalizer)
    output = {
        "identity_slug": slug,
        "identity_name": identity.get("name"),
        "sinner": identity.get("sinner"),
        "mechanic_profile": profiles[slug],
        "synergies": synergies,
        **guide,
    }

    dest_guides.mkdir(parents=True, exist_ok=True)
    (dest_guides / f"{slug}.json").write_text(
        json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    guide_files = [p for p in dest_guides.glob("*.json") if p.name != "manifest.json"]
    manifest = {
        "identity_count": len(guide_files),
        "guides_dir": str(dest_guides),
        "last_updated_slug": slug,
    }
    (dest_guides / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return output


def main() -> int:
    """CLI entrypoint for `python -m limbus_guides.pipeline.run` and `limbus-pipeline`."""
    guides = run_pipeline(use_ollama=False)
    print(f"Generated {len(guides)} guides in data/guides/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
