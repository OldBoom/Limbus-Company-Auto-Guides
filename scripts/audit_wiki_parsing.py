#!/usr/bin/env python3
"""Compare project parsed identities against live wiki.gg skill data."""

from __future__ import annotations

import json
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from limbus_guides.ingestion.wiki_parser import (
    _collect_skills,
    _extract_idpage,
    fetch_wikitext,
    filename_to_wiki_title,
    render_markdown,
)
from limbus_guides.nlp.skill_parser import parse_all_skills
from limbus_guides.paths import PARSED_IDS_DIR

REUSE_TAG = "[Reuse -"

# Identities with intentional post-fetch grafts (Key Status Effects, missing passives)
GRAFTED_STEMS = {"Ring_Apprentice_Faust"}


def _without_key_status_effects(text: str) -> str:
    """Drop hand-curated Key Status Effects prose for staleness comparison."""
    return re.sub(
        r"^## Key Status Effects\s*\n.*?(?=\n---\s*\n)",
        "",
        text,
        count=1,
        flags=re.S | re.M,
    )


def _normalize_for_staleness(text: str) -> str:
    """Normalize markdown before comparing stored vs fresh wiki render."""
    text = _without_key_status_effects(text)
    # Hand-grafted passive (wiki renderer may omit this block)
    text = re.sub(
        r"### Armor of Protection and Repression\n.*?(?=\n---\s*\n)",
        "",
        text,
        count=1,
        flags=re.S | re.M,
    )
    return text


def _skill_signature(skill: dict, *, from_wiki: bool) -> dict:
    if from_wiki:
        coins = skill.get("coins", [])
        non_reuse = [c for c in coins if REUSE_TAG not in c.get("effect", "")]
        return {
            "skill_num": skill["skill_num"],
            "name": skill["name"],
            "base_power": skill["base_power"],
            "coin_power": skill["coin_power"],
            "atk_weight": skill["atk_weight"],
            "coin_rows": len(coins),
            "coin_flips": max((c["coin"] for c in non_reuse), default=0) or len(non_reuse),
            "state": skill.get("state") or "",
            "is_defense": skill.get("is_defense", False),
        }
    coins = skill.get("coin_effects", [])
    non_reuse = [c for c in coins if REUSE_TAG not in c.get("effect", "")]
    cp = skill.get("coin_power") or "+0"
    return {
        "skill_num": skill["skill_num"],
        "name": skill["name"],
        "base_power": skill.get("base_power"),
        "coin_power": cp if isinstance(cp, str) else f"{cp:+d}",
        "atk_weight": skill.get("atk_weight"),
        "coin_rows": len(coins),
        "coin_flips": max((c["coin"] for c in non_reuse), default=0) or len(non_reuse),
        "state": "",
        "is_defense": False,
        "is_alternate": skill.get("is_alternate", False),
    }


def _primary_state_skills(states: dict[str, list[dict]]) -> list[dict]:
    """Attack skills from default state, or first state section for multi-state IDs."""
    default = states.get("", [])
    if any(not s.get("is_defense") and not s.get("is_alternate") for s in default):
        return default
    for state, skills in states.items():
        if state == "":
            continue
        if any(not s.get("is_defense") and not s.get("is_alternate") for s in skills):
            return skills
    return default


def _wiki_attack_skills(wt: str) -> tuple[list[dict], list[dict]]:
    """Primary and alternate attack skills from the primary skill set."""
    body = _extract_idpage(wt)
    states = _collect_skills(body)
    primary: list[dict] = []
    alternates: list[dict] = []
    for sk in _primary_state_skills(states):
        if sk.get("is_defense"):
            continue
        sig = _skill_signature(sk, from_wiki=True)
        if sk.get("is_alternate"):
            alternates.append(sig)
        else:
            primary.append(sig)
    primary.sort(key=lambda s: s["skill_num"])
    alternates.sort(key=lambda s: s["skill_num"])
    return primary, alternates


def _compare_skill_sets(
    wiki_skills: list[dict],
    local_sigs: list[dict],
    label: str,
) -> list[str]:
    issues: list[str] = []
    wiki_by_num = {s["skill_num"]: s for s in wiki_skills}
    local_by_num = {s["skill_num"]: s for s in local_sigs}

    if set(wiki_by_num) != set(local_by_num):
        issues.append(
            f"{label} SKILL_SET: wiki S{sorted(wiki_by_num)} vs parsed S{sorted(local_by_num)}"
        )

    for num in sorted(set(wiki_by_num) | set(local_by_num)):
        w = wiki_by_num.get(num)
        l = local_by_num.get(num)
        if not w:
            issues.append(f"{label} S{num}: present in parsed but missing from wiki")
            continue
        if not l:
            issues.append(f"{label} S{num}: present on wiki but missing from parsed")
            continue
        prefix = f"{label} S{num} ({w['name']})"
        for field in ("base_power", "coin_power", "atk_weight", "coin_rows", "coin_flips"):
            diff = _diff_field(field, w[field], l[field])
            if diff:
                issues.append(f"{prefix}: {diff}")
    return issues


def _diff_field(label: str, wiki_val, local_val) -> str | None:
    if wiki_val != local_val:
        return f"{label}: wiki={wiki_val!r} vs parsed={local_val!r}"
    return None


def compare_identity(stem: str, md_text: str, wt: str) -> list[str]:
    issues: list[str] = []
    wiki_primary, wiki_alts = _wiki_attack_skills(wt)
    local_primary, local_alts = parse_all_skills(md_text)
    local_primary_sigs = [_skill_signature(s, from_wiki=False) for s in local_primary]
    local_alt_sigs = [_skill_signature(s, from_wiki=False) for s in local_alts]

    # Fresh render vs stored markdown (staleness; ignore hand-grafted Key Status Effects)
    fresh_md = render_markdown(filename_to_wiki_title(stem), wt)
    if (
        stem not in GRAFTED_STEMS
        and _normalize_for_staleness(fresh_md).strip() != _normalize_for_staleness(md_text).strip()
    ):
        issues.append("STALE: stored parsed-ids markdown differs from fresh wiki render")

    issues.extend(_compare_skill_sets(wiki_primary, local_primary_sigs, "Primary"))
    issues.extend(_compare_skill_sets(wiki_alts, local_alt_sigs, "Alt"))

    return issues


def collect_project_slugs() -> list[str]:
    slugs = sorted(p.stem for p in PARSED_IDS_DIR.glob("*.md"))
    return slugs


def main() -> int:
    slugs = collect_project_slugs()
    print(f"Auditing {len(slugs)} identities against live wiki...\n")

    all_issues: dict[str, list[str]] = {}
    fetch_failures: dict[str, str] = {}

    for i, stem in enumerate(slugs):
        md_path = PARSED_IDS_DIR / f"{stem}.md"
        md_text = md_path.read_text(encoding="utf-8")
        title = filename_to_wiki_title(stem)
        try:
            wt = fetch_wikitext(title)
        except Exception as exc:
            fetch_failures[stem] = f"{title}: {exc}"
            continue
        issues = compare_identity(stem, md_text, wt)
        if issues:
            all_issues[stem] = issues
        if i < len(slugs) - 1:
            time.sleep(0.35)

    # Summary output
    print("=" * 72)
    print("FETCH FAILURES")
    print("=" * 72)
    if fetch_failures:
        for stem, err in fetch_failures.items():
            print(f"  {stem}: {err}")
    else:
        print("  (none)")

    print("\n" + "=" * 72)
    print("ISSUES BY IDENTITY")
    print("=" * 72)
    if not all_issues:
        print("  No discrepancies found.")
    else:
        for stem, issues in sorted(all_issues.items()):
            print(f"\n## {stem}")
            for issue in issues:
                print(f"  - {issue}")

    # Coin-count-only rollup (most impactful for guides)
    coin_issues = {
        stem: [i for i in issues if "coin_rows" in i or "coin_flips" in i]
        for stem, issues in all_issues.items()
        if any("coin_rows" in i or "coin_flips" in i for i in issues)
    }
    print("\n" + "=" * 72)
    print("COIN COUNT MISMATCHES (guides impact)")
    print("=" * 72)
    if not coin_issues:
        print("  (none)")
    else:
        for stem, issues in sorted(coin_issues.items()):
            print(f"\n  {stem}:")
            for issue in issues:
                if "coin_" in issue:
                    print(f"    {issue}")

    out = {
        "audited": len(slugs),
        "with_issues": len(all_issues),
        "fetch_failures": fetch_failures,
        "issues": all_issues,
    }
    report_path = ROOT / "data" / "wiki_audit_report.json"
    report_path.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nFull report: {report_path}")
    return 1 if fetch_failures or all_issues else 0


if __name__ == "__main__":
    raise SystemExit(main())
