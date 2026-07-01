#!/usr/bin/env python3
"""Add one identity from a wiki URL — parse, patch mechanics, guide, reference, eval."""

from __future__ import annotations

import argparse
import importlib
import json
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path
from urllib.parse import unquote, urlparse

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from limbus_guides.config_io import load_json_config
from limbus_guides.eval.metrics import evaluate_single
from limbus_guides.ingestion.markdown_loader import _infer_sinner
from limbus_guides.ingestion.wiki_parser import (
    SLUG_TO_WIKI_OVERRIDES,
    fetch_wikitext,
    filename_to_wiki_title,
    infer_sinner_from_body,
    resolve_wiki_title,
    save_parsed_markdown,
    wiki_title_to_stem,
)
from limbus_guides.nlp import mechanics as mechanics_mod
from limbus_guides.nlp.mechanics import clear_mechanics_cache
from limbus_guides.paths import CONFIG_DIR, DATA_DIR, PARSED_IDS_DIR
from limbus_guides.pipeline.run import run_for_slug

PORTRAIT_DIR = ROOT / "src" / "limbus_guides" / "dashboard" / "static" / "images" / "identities"
REF_DIR = DATA_DIR / "evaluation" / "references"
MECHANICS_PATH = ROOT / "src" / "limbus_guides" / "nlp" / "mechanics.py"
SYNERGY_PATH = ROOT / "src" / "limbus_guides" / "nlp" / "synergy.py"

PROTECTED_STEMS = {
    "Ring_Apprentice_Faust",
    "Blade_Lineage_Salsu_Yi_Sang",
    "Ring_Pointillist_Student_Yi_Sang",
    "The_House_of_Spiders_The_Ring_Apprentice_Faust",
}


def url_to_page_title(url: str) -> str:
    path = urlparse(url).path
    title = path.split("/wiki/")[-1] if "/wiki/" in path else path.strip("/")
    return unquote(title)


def input_to_slug(raw: str) -> tuple[str, str]:
    """Return (slug, wiki_page_title)."""
    if raw.startswith("http"):
        title = url_to_page_title(raw)
    else:
        title = unquote(raw)
    slug = wiki_title_to_stem(title)
    return slug, title


def validate_round_trip(slug: str) -> str | None:
    mapped = filename_to_wiki_title(slug)
    if slug not in SLUG_TO_WIKI_OVERRIDES and wiki_title_to_stem(mapped) != slug:
        return f"Slug round-trip failed: {slug!r} -> {mapped!r} -> {wiki_title_to_stem(mapped)!r}"
    return None


def structural_warnings(md: str) -> list[str]:
    warns: list[str] = []
    if "## Skills" not in md and not re.search(r"^## Skills —", md, re.M):
        warns.append("Possible parse failure — no skills section found")
    skill_count = len(re.findall(r"^### Skill \d", md, re.M))
    if skill_count < 2:
        warns.append(f"Only {skill_count} skill(s) parsed — check wiki template")
    return warns


def parse_key_status_effects(md: str) -> list[str]:
    m = re.search(r"^## Key Status Effects\s*$", md, re.M)
    if not m:
        return []
    rest = md[m.end() :]
    end = re.search(r"^## ", rest, re.M)
    section = rest[: end.start()] if end else rest
    return [h.strip() for h in re.findall(r"^### (.+)$", section, re.M)]


def load_mechanics_list() -> list[str]:
    importlib.reload(mechanics_mod)
    return list(mechanics_mod.UNIQUE_MECHANICS)


def patch_unique_mechanic(term: str) -> bool:
    text = MECHANICS_PATH.read_text(encoding="utf-8")
    if f'"{term}"' in text:
        return False
    new_text, n = re.subn(
        r'(    "Unbreakable Coin",\n)(\]\nALL_MECHANICS)',
        rf'\1    "{term}",\n\2',
        text,
        count=1,
    )
    if n == 0:
        new_text, n = re.subn(
            r"(UNIQUE_MECHANICS = \[[\s\S]*?)(\n\]\nALL_MECHANICS)",
            rf'\1\n    "{term}",\2',
            text,
            count=1,
        )
    if n == 0:
        return False
    MECHANICS_PATH.write_text(new_text, encoding="utf-8")
    clear_mechanics_cache()
    importlib.reload(mechanics_mod)
    return True


def patch_regex_alternation(file_text: str, var_name: str, term: str) -> tuple[str, bool]:
    if f"|{term}" in file_text:
        return file_text, False
    pattern = rf'({var_name} = re\.compile\([\s\S]*?r"\([^)]*)(\|[^|"\)]+)"\)'
    m = re.search(pattern, file_text)
    if not m:
        return file_text, False
    escaped = re.escape(term)
    new_text = file_text[: m.end(1)] + f"|{escaped}" + file_text[m.start(2) :]
    return new_text, True


def patch_synergy_regex(var_name: str, term: str) -> bool:
    text = SYNERGY_PATH.read_text(encoding="utf-8")
    new_text, ok = patch_regex_alternation(text, var_name, term)
    if ok:
        SYNERGY_PATH.write_text(new_text, encoding="utf-8")
    return ok


def build_text_corpus(md_path: Path) -> str:
    parts = [md_path.read_text(encoding="utf-8")]
    identities_dir = DATA_DIR / "identities"
    for p in identities_dir.glob("*.json"):
        data = json.loads(p.read_text(encoding="utf-8"))
        parts.append(data.get("description_text", "") or "")
        parts.append(json.dumps(data.get("parsed_skills", {})))
    return "\n".join(parts)


def scaling_pattern_matches(term: str, corpus: str) -> bool:
    return bool(
        re.search(rf"(for every|per|at)\s+\d+\+?\s+{re.escape(term)}", corpus, re.I)
    )


def support_pattern_matches(term: str, corpus: str) -> bool:
    return bool(
        re.search(rf"(inflict|apply|gain|grant).{{0,60}}{re.escape(term)}", corpus, re.I)
    )


def process_mechanics(
    md: str,
    md_path: Path,
    *,
    confirm: bool,
) -> list[str]:
    """Auto-add unknown Key Status Effects to UNIQUE_MECHANICS + synergy regexes."""
    logs: list[str] = []
    corpus = build_text_corpus(md_path)
    known = set(load_mechanics_list())
    for term in parse_key_status_effects(md):
        if term in known:
            continue
        if confirm:
            ans = input(f'Add "{term}" to UNIQUE_MECHANICS? [y/N]: ').strip().lower()
            if ans not in ("y", "yes"):
                logs.append(f"[SKIP] Mechanic: {term} (not added)")
                continue
        if not patch_unique_mechanic(term):
            logs.append(f"[WARN] Mechanic: could not patch {term!r}")
            continue
        known.add(term)
        detail = f"{term} → added to UNIQUE_MECHANICS"
        extras: list[str] = []
        if scaling_pattern_matches(term, corpus):
            if patch_synergy_regex("SCALES_OFF_RE", term):
                extras.append("SCALES_OFF_RE")
        if support_pattern_matches(term, corpus):
            if patch_synergy_regex("SUPPORT_PASSIVE_RE", term):
                extras.append("SUPPORT_PASSIVE_RE")
        if extras:
            detail += f" + {', '.join(extras)}"
        logs.append(f"[OK]   Mechanics: {detail}")
    return logs


def infer_sinner_name(wt: str, page_title: str, override: str | None) -> str:
    if override:
        return override
    try:
        sinner = infer_sinner_from_body(wt)
        if sinner and sinner != "Unknown":
            return sinner
    except ValueError:
        pass
    title = page_title.replace("_", " ")
    sinner = _infer_sinner(title)
    if sinner != "Unknown":
        return sinner
    if sys.stdin.isatty():
        entered = input("Could not infer sinner — enter name: ").strip()
        if entered:
            return entered
    return "Unknown"


def slugify_sinner_id(name: str) -> str:
    return (
        name.lower()
        .replace(" ", "_")
        .replace("ō", "o")
        .replace("ū", "u")
        .replace("ö", "o")
    )


def update_sinners_config(sinner_name: str, slug: str) -> None:
    config_path = CONFIG_DIR / "sinners.json"
    config = load_json_config(config_path)
    sinner_map = {s["name"]: s for s in config.get("sinners", [])}
    if sinner_name in sinner_map:
        existing = set(sinner_map[sinner_name].get("identities", []))
        existing.add(slug)
        sinner_map[sinner_name]["identities"] = sorted(existing)
    else:
        config.setdefault("sinners", []).append(
            {
                "id": slugify_sinner_id(sinner_name),
                "name": sinner_name,
                "identities": [slug],
            }
        )
    config_path.write_text(json.dumps(config, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def copy_portrait(src: Path, slug: str) -> Path:
    PORTRAIT_DIR.mkdir(parents=True, exist_ok=True)
    dest = PORTRAIT_DIR / f"{slug}{src.suffix.lower()}"
    shutil.copy2(src, dest)
    return dest


def wiki_excerpt(md_path: Path, lines: int = 40) -> str:
    return "\n".join(md_path.read_text(encoding="utf-8").splitlines()[:lines])


def prompt_reference(identity_name: str, slug: str, md_path: Path, ref_file: Path | None) -> str | None:
    if ref_file:
        return ref_file.read_text(encoding="utf-8").strip()

    print("\n── Wiki source excerpt (paste into your LLM) ──")
    print(wiki_excerpt(md_path))
    print("\n── Suggested reference prompt ──")
    print(
        f"Write 2-4 sentences for an evaluation reference for {identity_name}.\n"
        "Sentence 1: role + primary mechanic. Sentences 2-3: resource loop / state transition.\n"
        "Ground only in the wiki excerpt above, not in any generated guide.\n"
    )
    print(f"Enter reference text for: {slug}")
    print("(Blank line to finish, Ctrl+C to skip.)")
    lines: list[str] = []
    try:
        while True:
            line = input("> " if not lines else "> ")
            if not line.strip() and lines:
                break
            if not line.strip() and not lines:
                continue
            lines.append(line)
    except (KeyboardInterrupt, EOFError):
        return None
    text = " ".join(lines).strip()
    return text or None


def prompt_portrait_path(cli_path: Path | None) -> Path | None:
    if cli_path:
        return cli_path if cli_path.exists() else None
    try:
        raw = input("\nPortrait PNG path (Enter to skip): ").strip().strip('"')
    except (KeyboardInterrupt, EOFError):
        return None
    if not raw:
        return None
    p = Path(raw)
    return p if p.exists() else None


def run_smoke_test(slug: str) -> int:
    kw = slug.replace("'", "''")  # pytest -k uses fnmatch
    cmd = [
        sys.executable,
        "-m",
        "pytest",
        "tests/test_wiki_parser.py",
        "tests/test_pipeline.py",
        "-k",
        kw,
        "-q",
    ]
    return subprocess.call(cmd, cwd=ROOT)


def main() -> int:
    parser = argparse.ArgumentParser(description="Add one identity from wiki URL or page title")
    parser.add_argument("target", help="Wiki URL or page title")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--force", action="store_true", help="Overwrite existing parsed markdown")
    parser.add_argument("--force-protected", action="store_true", help="Allow overwriting protected stems")
    parser.add_argument("--portrait", type=Path, help="Portrait image path")
    parser.add_argument("--skip-portrait", action="store_true")
    parser.add_argument("--skip-ref", action="store_true")
    parser.add_argument("--ref-file", type=Path, help="Pre-written reference .txt")
    parser.add_argument("--add-sinner", help="Override inferred sinner name")
    parser.add_argument("--confirm-mechanics", action="store_true", help="Prompt before adding mechanics")
    parser.add_argument("--ollama", action="store_true", help="Use Ollama for guide generation")
    parser.add_argument("--smoke-test", action="store_true", help="Run pytest for this slug after completion")
    args = parser.parse_args()

    report: list[str] = []
    slug, _input_title = input_to_slug(args.target)

    rt_err = validate_round_trip(slug)
    if rt_err:
        report.append(f"[WARN] {rt_err}")

    md_path = PARSED_IDS_DIR / f"{slug}.md"
    if slug in PROTECTED_STEMS and md_path.exists() and args.force and not args.force_protected:
        print(f"[FAIL] {slug} is protected. Pass --force-protected to overwrite.")
        return 1
    if md_path.exists() and not args.force:
        print(f"[INFO] Parsed file exists: {md_path} (use --force to re-fetch)")

    if args.dry_run:
        try:
            wiki_title = resolve_wiki_title(slug)
            report.append(f"[OK]   Slug:     {slug}")
            report.append(f"[OK]   Wiki:     {wiki_title}")
            report.append(f"[OK]   Round-trip: {wiki_title_to_stem(wiki_title) == slug or slug in SLUG_TO_WIKI_OVERRIDES}")
        except Exception as exc:
            report.append(f"[FAIL] Wiki resolve: {exc}")
        for line in report:
            print(line)
        return 0 if not any(l.startswith("[FAIL]") for l in report) else 1

    try:
        wiki_title = resolve_wiki_title(slug)
    except Exception as exc:
        print(f"[FAIL] Could not resolve wiki title for {slug!r}: {exc}")
        print("       Add an entry to SLUG_TO_WIKI_OVERRIDES in wiki_parser.py if needed.")
        return 1

    used_existing_md = md_path.exists() and not args.force

    if used_existing_md:
        md = md_path.read_text(encoding="utf-8")
        report.append(f"[SKIP] Parsed: {md_path} (exists)")
    else:
        wt = fetch_wikitext(wiki_title)
        if "{{IDPage" not in wt:
            print("[FAIL] No {{IDPage}} template in wikitext — page may not be an identity.")
            return 1
        md_path = save_parsed_markdown(wiki_title, wt, stem=slug)
        md = md_path.read_text(encoding="utf-8")
        report.append(f"[OK]   Parsed: {md_path}")
        time.sleep(0.5)

    for w in structural_warnings(md):
        report.append(f"[WARN] {w}")

    if used_existing_md and not args.add_sinner:
        from limbus_guides.ingestion.markdown_loader import parse_identity_markdown

        parsed = parse_identity_markdown(md, slug)
        sinner = parsed.get("sinner") or _infer_sinner(parsed.get("name", ""))
    else:
        wt = fetch_wikitext(wiki_title)
        sinner = infer_sinner_name(wt, wiki_title, args.add_sinner)
    if sinner == "Unknown":
        report.append("[WARN] Sinner: could not infer — update config/sinners.json manually")
    else:
        update_sinners_config(sinner, slug)
        report.append(f"[OK]   Sinner:   {sinner}")

    mech_logs = process_mechanics(md, md_path, confirm=args.confirm_mechanics)
    report.extend(mech_logs)

    guide = run_for_slug(slug, use_ollama=args.ollama)
    guide_path = DATA_DIR / "guides" / f"{slug}.json"
    report.append(f"[OK]   Guide:    {guide_path}")
    if not args.ollama:
        report.append("[NOTE] Guide uses template generator. Pass --ollama for LLM prose.")

    print("\n" + "─" * 66)
    print("  GENERATED GUIDE")
    print(f"  Core idea: {guide.get('core_idea', '')[:200]}...")
    play = guide.get("playstyle_guide", "")
    print(f"  Playstyle: {play[:300]}{'...' if len(play) > 300 else ''}")
    print("─" * 66)

    ref_text: str | None = None
    if not args.skip_ref:
        ref_text = prompt_reference(
            guide.get("identity_name", slug),
            slug,
            md_path,
            args.ref_file,
        )
        if ref_text:
            REF_DIR.mkdir(parents=True, exist_ok=True)
            ref_path = REF_DIR / f"{slug}.txt"
            ref_path.write_text(ref_text + "\n", encoding="utf-8")
            report.append(f"[OK]   Reference: saved ({len(ref_text.split())} words)")
            scores = evaluate_single(slug)
            if scores.get("has_reference"):
                r = scores["rouge_l"]
                report.append(
                    f"[OK]   ROUGE-L:  {r['full']} (full) vs {r['naive']} (naive) vs {r['ablation']} (ablation)"
                )
        else:
            report.append("[SKIP] Ref:  skipped")
            report.append(f"       Add later: {REF_DIR / (slug + '.txt')}")

    if not args.skip_portrait:
        portrait_src = prompt_portrait_path(args.portrait)
        if portrait_src:
            dest = copy_portrait(portrait_src, slug)
            report.append(f"[OK]   Portrait: {dest}")
        else:
            report.append("[SKIP] Portrait: skipped (dashboard uses sinner portrait)")

    print("\n" + "═" * 66)
    print("  QUALITY REPORT")
    for line in report:
        print(f"  {line}")
    print("═" * 66)

    if args.smoke_test:
        code = run_smoke_test(slug)
        if code != 0:
            report.append(f"[WARN] Smoke test exited with code {code}")
        else:
            report.append("[OK]   Smoke test passed")

    return 0 if not any(l.startswith("[FAIL]") for l in report) else 1


if __name__ == "__main__":
    raise SystemExit(main())
