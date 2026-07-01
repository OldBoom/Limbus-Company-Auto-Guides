"""Fetch wiki.gg identity pages via MediaWiki API and render parsed-ids markdown."""

from __future__ import annotations

import re
import time
import unicodedata
from pathlib import Path
from urllib.parse import unquote

import requests

from limbus_guides.paths import PARSED_IDS_DIR

API_URL = "https://limbuscompany.wiki.gg/api.php"
USER_AGENT = "LimbusCompanyAutoGuides/0.1 (academic NLP project)"
LEVEL = 60

RARITY_MAP = {1: "One", 2: "Two", 3: "World", 4: "E.G.O"}
SEASON_MAP = {0: "Standard Fare"}

# Status effects that are standard game-wide — omit from Key Status Effects section.
STANDARD_EFFECTS = {
    "Bleed", "Burn", "Tremor", "Rupture", "Sinking", "Poise", "Charge",
    "Bind", "Haste", "Protection", "Shield",
    "Defense Level Up", "Defense Level Down", "Offense Level Up", "Offense Level Down",
    "Damage Up", "Damage Down", "Slash DMG Up", "Pierce DMG Up", "Blunt DMG Up",
    "Clash Power", "Coin Power", "Base Power", "Final Power", "Atk Weight",
    "Unbreakable Coin", "Assist Defense",
}


# ---------------------------------------------------------------------------
# Wiki API
# ---------------------------------------------------------------------------


def fetch_wikitext(page_title: str) -> str:
    resp = requests.get(
        API_URL,
        params={"action": "parse", "page": page_title, "prop": "wikitext", "format": "json"},
        headers={"User-Agent": USER_AGENT},
        timeout=45,
    )
    resp.raise_for_status()
    data = resp.json()
    if "error" in data:
        raise ValueError(f"Wiki API error for {page_title!r}: {data['error']}")
    return data["parse"]["wikitext"]["*"]


# ---------------------------------------------------------------------------
# Template parsing helpers
# ---------------------------------------------------------------------------


def _find_template(text: str, start: int = 0) -> tuple[str, str, int] | None:
    """Return (name, inner, end_index) for the first {{...}} at or after start."""
    idx = text.find("{{", start)
    if idx < 0:
        return None
    depth = 0
    i = idx + 2
    while i < len(text) - 1:
        if text[i : i + 2] == "{{":
            depth += 1
            i += 2
        elif text[i : i + 2] == "}}":
            if depth == 0:
                inner = text[idx + 2 : i]
                end = i + 2
                name, _, body = inner.partition("|")
                return name.strip(), body, end
            depth -= 1
            i += 2
        else:
            i += 1
    return None


def _split_params(body: str) -> dict[str, str]:
    """Split template inner body on | at depth 0 (respecting nested {{ }})."""
    params: dict[str, str] = {}
    key: str | None = None
    val_start = 0
    depth = 0
    i = 0
    while i < len(body):
        ch2 = body[i : i + 2]
        if ch2 == "{{":
            depth += 1
            i += 2
            continue
        if ch2 == "}}":
            depth -= 1
            i += 2
            continue
        if body[i] == "|" and depth == 0:
            segment = body[val_start:i].strip()
            if key is None:
                if "=" in segment:
                    k, _, v = segment.partition("=")
                    params[k.strip()] = v.strip()
            else:
                params[key] = segment
            key = None
            val_start = i + 1
            i += 1
            continue
        if key is None and depth == 0 and body[i] == "=":
            key = body[val_start:i].strip()
            val_start = i + 1
        i += 1
    # trailing segment
    segment = body[val_start:].strip()
    if key is not None:
        params[key] = segment
    elif "=" in segment:
        k, _, v = segment.partition("=")
        params[k.strip()] = v.strip()
    return params


def _parse_template_at(text: str, pos: int) -> tuple[str, dict[str, str], int] | None:
    found = _find_template(text, pos)
    if not found:
        return None
    name, body, end = found
    return name, _split_params(body), end


def _extract_idpage(wt: str) -> str:
    m = re.search(r"\{\{IDPage\b", wt)
    if not m:
        raise ValueError("No {{IDPage}} template found")
    _, body, _ = _find_template(wt, m.start())  # type: ignore[misc]
    return body


def _line_value(body: str, key: str) -> str | None:
    m = re.search(rf"^\|{re.escape(key)}=(.+)$", body, re.M)
    return m.group(1).strip() if m else None


def _line_template(body: str, key: str) -> dict[str, str] | None:
    m = re.search(rf"^\|{re.escape(key)}=", body, re.M)
    if not m:
        return None
    pos = m.end()
    # Skip whitespace; value must start with {{
    while pos < len(body) and body[pos] in " \t":
        pos += 1
    if pos >= len(body) or body[pos : pos + 2] != "{{":
        return None
    parsed = _parse_template_at(body, pos)
    if not parsed:
        return None
    name, params, _ = parsed
    if name != "UptieSkills":
        return None
    return params


# ---------------------------------------------------------------------------
# Markup cleaning
# ---------------------------------------------------------------------------


def _clean_status_name(raw: str) -> str:
    raw = raw.strip()
    raw = re.sub(r"\s*\(Ally\)\s*$", "", raw)
    raw = re.sub(r"\s*-\s*", " — ", raw)
    raw = raw.replace("Artwork - Fascia (Faust)", "Artwork: Fascia")
    return raw.strip()


def clean_wiki_markup(text: str) -> str:
    if not text:
        return ""

    def status_repl(m: re.Match) -> str:
        return _clean_status_name(m.group(1))

    text = re.sub(r"\{\{StatusEffect\|([^}|]+)(?:\|[^}]*)?\}\}", status_repl, text)
    text = re.sub(r"\{\{SkillCon\|([^}]+)\}\}", r"[\1]", text)
    text = re.sub(r"\{\{Keyword\|([^}]+)\}\}", r"\1", text)
    text = re.sub(r"\{\{Passive\|([^|]+)\|", "", text)  # strip opening Passive name handled separately
    text = re.sub(r"\[\[:Category:[^\]]+\]\]", "", text)
    text = re.sub(r"\[\[([^|\]]+)\|([^\]]+)\]\]", r"\2", text)
    text = re.sub(r"\[\[([^\]]+)\]\]", r"\1", text)
    text = re.sub(r"<br\s*/?>", "; ", text, flags=re.I)
    text = text.replace("\n", " ")
    text = re.sub(r"\{\{[^}]+\}\}", "", text)
    text = text.replace("'''", "").replace("''", "")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _line_passive_template(body: str, key: str) -> str | None:
    m = re.search(rf"^\|{re.escape(key)}=", body, re.M)
    if not m:
        return None
    pos = m.end()
    while pos < len(body) and body[pos] in " \t":
        pos += 1
    if pos >= len(body) or body[pos : pos + 2] != "{{":
        return None
    found = _find_template(body, pos)
    if not found or found[0] != "Passive":
        return None
    return "{{" + found[0] + "|" + found[1] + "}}"


def _parse_passive_template(raw: str) -> dict:
    found = _find_template(raw, raw.find("{{"))
    if not found or found[0] != "Passive":
        return {"name": "Passive", "body": clean_wiki_markup(raw), "req": ""}
    _, inner, _ = found
    # Passive layout: {{Passive|Name|key=val|...|body text}}
    # First positional segment after Passive| is the name
    parts = []
    depth = 0
    buf: list[str] = []
    i = 0
    while i < len(inner):
        if inner[i : i + 2] == "{{":
            depth += 1
            buf.append("{{")
            i += 2
        elif inner[i : i + 2] == "}}":
            depth -= 1
            buf.append("}}")
            i += 2
        elif inner[i] == "|" and depth == 0:
            parts.append("".join(buf))
            buf = []
            i += 1
        else:
            buf.append(inner[i])
            i += 1
    if buf:
        parts.append("".join(buf))

    name = parts[0].strip() if parts else "Passive"
    req = ""
    body_parts: list[str] = []
    for part in parts[1:]:
        part = part.strip()
        if part.startswith("req=") or part.startswith("req2="):
            if part.startswith("req="):
                req = part[4:].strip()
        elif re.match(r"sin\d*=", part):
            continue
        else:
            body_parts.append(part)
    body = clean_wiki_markup(" ".join(body_parts))
    return {"name": name, "body": body, "req": req}


# ---------------------------------------------------------------------------
# Skill / stat extraction (max uptie tier = tier 4 fields)
# ---------------------------------------------------------------------------


def _offense_level(atkmod: str, slevel: int) -> str:
    mod = int(atkmod.replace("+", "").strip()) if atkmod else 0
    total = LEVEL + mod
    return f"{total} ({LEVEL}+{mod})"


def _coin_power(cpower: str) -> str:
    cpower = cpower.strip().replace(" ", "")
    if not cpower.startswith(("+", "-")):
        cpower = "+" + cpower
    return cpower


def _first_param(params: dict[str, str], *keys: str, default: str = "") -> str:
    for key in keys:
        val = params.get(key)
        if val is not None and str(val).strip():
            return str(val).strip()
    return default


def _resolve_coin_effect(params: dict[str, str], coin_num: int) -> str:
    for prefix in ("4", "3", "2", ""):
        key = f"{prefix}ce{coin_num}" if prefix else f"ce{coin_num}"
        val = params.get(key)
        if val:
            return val
    return ""


def _skill_state_name(se: str) -> str | None:
    raw = se or ""
    if not re.search(r"exclusive\s+skill", raw, re.I):
        return None
    m = re.search(r"\{\{StatusEffect\|([^}|]+)", raw)
    if m:
        return _clean_status_name(m.group(1))
    cleaned = clean_wiki_markup(raw)
    m = re.search(r"^(.+?) exclusive Skill", cleaned, re.I)
    if m:
        return _clean_status_name(m.group(1))
    return None


def _parse_skill_key(key: str) -> tuple[int, bool, bool]:
    """Return (skill_num, is_alternate, is_defense) for skill/defense template keys."""
    if key.startswith("defense"):
        num = _int_or(re.sub(r"\D", "", key) or "1", 1)
        return num, False, True
    m = re.match(r"skill(\d+)(?:-(\d+))?", key)
    if m:
        return int(m.group(1)), m.group(2) is not None, False
    return 1, False, False


def _int_or(value: str | None, default: int = 0) -> int:
    if not value or not str(value).strip():
        return default
    return int(str(value).strip())


def _parse_skill_params(params: dict[str, str]) -> dict:
    slevel = _int_or(params.get("slevel"), 1)
    atkmod = params.get("atkmod", "+0")
    spower = _first_param(params, "spower", "4spower", "3spower", "2spower", default="0")
    cpower = _first_param(params, "cpower", "4cpower", "3cpower", "2cpower", default="+0")
    atk_weight = _int_or(
        _first_param(params, "atkweight", "amt", default="1") or "1",
        1,
    )
    if params.get("coin") is not None and str(params.get("coin")).strip() != "":
        coin_count = _int_or(params.get("coin"), 0)
    else:
        coin_count = 1

    se = clean_wiki_markup(params.get("se", ""))
    state = _skill_state_name(params.get("se", ""))

    on_use_lines = []
    skill_bonuses = []
    for part in re.split(r"(?<=\))\s+(?=\[)|\n|<br>", se):
        part = part.strip()
        if not part:
            continue
        if part.lower().endswith("exclusive skill"):
            continue
        if part.startswith("[On Use]") or part.startswith("[Clash Win]") or part.startswith("[Before"):
            on_use_lines.append(part)
        else:
            skill_bonuses.append(part)

    coins = []
    for n in range(1, coin_count + 1):
        ce = _resolve_coin_effect(params, n)
        effect = clean_wiki_markup(ce) if ce else "—"
        coins.append({"coin": n, "effect": effect})

    return {
        "skill_num": slevel,
        "name": params.get("name", f"Skill {slevel}"),
        "offense_level": _offense_level(atkmod, slevel),
        "base_power": _int_or(spower),
        "coin_power": _coin_power(cpower),
        "atk_weight": atk_weight,
        "on_use": on_use_lines,
        "skill_bonuses": skill_bonuses,
        "coins": coins,
        "state": state or "",
        "is_defense": params.get("name", "").lower() in ("guard", "evade", "counter")
        or "defense" in params.get("icon", "").lower(),
    }


def _interleave_attack_skills(skills: list[dict]) -> list[dict]:
    """Primary skill N, then its alternates (skill N-2), then skill N+1, etc."""
    primaries = sorted(
        [s for s in skills if not s.get("is_alternate")],
        key=lambda s: s["skill_num"],
    )
    alts_by_num: dict[int, list[dict]] = {}
    for s in skills:
        if s.get("is_alternate"):
            alts_by_num.setdefault(s["skill_num"], []).append(s)
    ordered: list[dict] = []
    for sk in primaries:
        ordered.append(sk)
        ordered.extend(alts_by_num.get(sk["skill_num"], []))
    return ordered


def _collect_skills(body: str) -> dict[str, list[dict]]:
    """Group skills by state name. Key '' = default single state."""
    states: dict[str, list[dict]] = {}
    for m in re.finditer(r"^\|(skill\d+(?:-\d+)?|defense\d*)=", body, re.M):
        key = m.group(1)
        params = _line_template(body, key)
        if not params:
            continue
        skill_num, is_alternate, is_defense_key = _parse_skill_key(key)
        skill = _parse_skill_params(params)
        skill["skill_num"] = skill_num
        skill["is_alternate"] = is_alternate
        skill["is_defense"] = is_defense_key or skill.get("is_defense", False)

        state = skill.get("state") or ""
        if skill["is_defense"]:
            skill["defense_type"] = _infer_defense_type(params.get("name", ""), params.get("se", ""))
        states.setdefault(state, []).append(skill)

    for state in states:
        attacks = [s for s in states[state] if not s.get("is_defense")]
        defenses = sorted(
            [s for s in states[state] if s.get("is_defense")],
            key=lambda s: s["skill_num"],
        )
        states[state] = _interleave_attack_skills(attacks) + defenses
    return states


def _infer_defense_type(name: str, se: str) -> str:
    combined = (name + " " + se).lower()
    if "guard" in combined:
        return "Guard"
    if "evade" in combined:
        return "Evade"
    return "Counter"


def _collect_passives(body: str) -> tuple[list[dict], list[dict]]:
    combat: list[dict] = []
    support: list[dict] = []
    for m in re.finditer(r"^\|(passive\d+)=", body, re.M):
        key = m.group(1)
        raw = _line_passive_template(body, key)
        if not raw:
            continue
        p = _parse_passive_template(raw)
        if re.search(r"req=\d+\s*Res", raw):
            support.append(p)
        else:
            combat.append(p)
    return combat, support


def _parse_traits(keyword: str) -> str:
    traits = re.findall(r"\{\{Keyword\|([^}]+)\}\}", keyword or "")
    return ", ".join(traits)


def _display_hp(hp: str, growth: str) -> int:
    return round(float(hp) + float(growth) * LEVEL)


def _display_defense(defmod: str) -> int:
    mod = int(defmod.replace("+", "").strip())
    return LEVEL + mod


def _stagger_line(body: str, hp: int) -> str:
    parts = []
    for key, pct_key in [("stagger1", 1), ("stagger2", 2), ("stagger3", 3)]:
        val = _line_value(body, key)
        if not val:
            continue
        pct = int(float(val))
        abs_val = round(hp * pct / 100)
        parts.append(f"{pct}% ({abs_val})")
    return " — ".join(parts)


def _season_label(body: str) -> str:
    season = _line_value(body, "season") or "0"
    try:
        n = int(season)
    except ValueError:
        return season
    if n == 0:
        return SEASON_MAP[0]
    world = _line_value(body, "world") or ""
    if world:
        return f"Season {n} — {world}"
    return f"Season {n}"


def _rarity_label(body: str) -> str:
    raw = _line_value(body, "rarity") or "3"
    try:
        return RARITY_MAP.get(int(raw), raw)
    except ValueError:
        return raw


def _full_title(prefix: str, sinner: str) -> str:
    prefix = prefix.strip()
    if sinner and sinner not in prefix:
        return f"{prefix} {sinner}"
    return prefix


def _unique_effects_from_text(text: str) -> dict[str, str]:
    """Extract non-standard status effect names mentioned in kit text."""
    found: dict[str, str] = {}
    for m in re.finditer(r"\{\{StatusEffect\|([^}|]+)", text):
        name = _clean_status_name(m.group(1))
        if name not in STANDARD_EFFECTS and name not in found:
            found[name] = ""
    return found


# ---------------------------------------------------------------------------
# Markdown rendering
# ---------------------------------------------------------------------------


def _render_skill(skill: dict) -> list[str]:
    lines = [
        f"### Skill {skill['skill_num']}: {skill['name']}",
        "",
        "| Offense Level | Base Power | Coin Power | Atk Weight |",
        "|---------------|------------|------------|------------|",
        f"| {skill['offense_level']} | {skill['base_power']} | {skill['coin_power']} | x{skill['atk_weight']} |",
        "",
    ]
    for bonus in skill.get("skill_bonuses", []):
        lines.append(f"**{bonus}**  ")
    for ou in skill.get("on_use", []):
        lines.append(f"**{ou}**  ")
    if skill.get("coins"):
        lines.append("")
        lines.append("| Coin | Effects |")
        lines.append("|------|---------|")
        for c in skill["coins"]:
            lines.append(f"| {c['coin']} | {c['effect']} |")
    lines.append("")
    lines.append("---")
    lines.append("")
    return lines


def _render_defense(skill: dict) -> list[str]:
    state_note = f" ({skill['state']})" if skill.get("state") else ""
    dtype = skill.get("defense_type", "Counter")
    lines = [
        f"### {dtype}{state_note}: {skill['name']}",
        "",
        "| Offense Level | Base Power | Coin Power |",
        "|---------------|------------|------------|",
        f"| {skill['offense_level']} | {skill['base_power']} | {skill['coin_power']} |",
        "",
    ]
    for bonus in skill.get("skill_bonuses", []):
        lines.append(f"**{bonus}**  ")
    for ou in skill.get("on_use", []):
        lines.append(f"**{ou}**  ")
    if skill.get("coins"):
        lines.append("")
        lines.append("| Coin | Effects |")
        lines.append("|------|---------|")
        for c in skill["coins"]:
            lines.append(f"| {c['coin']} | {c['effect']} |")
    lines.append("")
    lines.append("---")
    lines.append("")
    return lines


def render_markdown(page_title: str, wt: str) -> str:
    body = _extract_idpage(wt)
    prefix = _line_value(body, "prefix") or page_title.replace("_", " ")
    sinner = _line_value(body, "sinner") or ""
    quote = _line_value(body, "quote") or ""
    title = _full_title(prefix, sinner)
    hp = _display_hp(_line_value(body, "hp") or "66", _line_value(body, "hpgrowth") or "2")
    speed = _line_value(body, "speed") or "3~7"
    deflvl = _display_defense(_line_value(body, "defmod") or "0")
    traits = _parse_traits(_line_value(body, "keyword") or "")
    release = _line_value(body, "releasedate") or ""

    skill_states = _collect_skills(body)
    combat_passives, support_passives = _collect_passives(body)
    unique_fx = _unique_effects_from_text(wt)

    lines: list[str] = [
        f"# {title}",
        "",
        f'> *"{quote}"*',
        "",
        f"**Rarity:** {_rarity_label(body)}  ",
        f"**Season:** {_season_label(body)}  ",
        f"**Release:** {release}  ",
        f"**Traits:** {traits}",
        "",
        "---",
        "",
        "## Base Stats",
        "",
        "| HP | Speed | Defense Level |",
        "|----|-------|---------------|",
        f"| {hp} | {speed} | {deflvl} |",
        "",
        f"**Stagger Thresholds:** {_stagger_line(body, hp)}",
        "",
        "---",
        "",
    ]

    # Key status effects (unique only, brief placeholder bullets)
    non_standard = {k: v for k, v in unique_fx.items() if k not in STANDARD_EFFECTS}
    key_fx = list(non_standard.keys())
    if key_fx:
        lines += ["## Key Status Effects", ""]
        for fx in key_fx[:6]:
            lines += [f"### {fx}", f"- Identity-specific mechanic — see skills and passives.", ""]
        lines += ["---", ""]

    # Attack skills by state
    state_names = list(skill_states.keys())
    multi_state = len([s for s in state_names if s]) > 1 or (
        len(state_names) == 2 and "" in state_names
    )
    for state in state_names:
        attacks = [s for s in skill_states[state] if not s.get("is_defense")]
        defenses = [s for s in skill_states[state] if s.get("is_defense")]
        if not attacks and not defenses:
            continue
        section = f"## Skills — {state}" if state else "## Skills"
        lines += [section, ""]
        for sk in attacks:
            lines.extend(_render_skill(sk))
        if defenses:
            lines += ["## Defense Skills", ""]
            for sk in defenses:
                lines.extend(_render_defense(sk))

    # If defenses ended up in default bucket after attacks
    if not any("## Defense Skills" in ln for ln in lines):
        all_def = []
        for state in skill_states:
            all_def.extend(s for s in skill_states[state] if s.get("is_defense"))
        if all_def:
            lines += ["## Defense Skills", ""]
            for sk in all_def:
                lines.extend(_render_defense(sk))

    if combat_passives:
        lines += ["## Combat Passives", ""]
        for p in combat_passives:
            lines.append(f"### {p['name']}")
            lines.append("")
            if p.get("req"):
                req = p["req"].replace("Owned", "Owned").replace("Res", "Res")
                if not req.startswith("×"):
                    req = f"×{req}"
                lines.append(f"**({req})**")
                lines.append("")
            lines.append(p["body"])
            lines.append("")
            lines.append("---")
            lines.append("")

    if support_passives:
        lines += ["## Support Passive", ""]
        for p in support_passives:
            lines.append(f"### {p['name']}")
            lines.append("")
            if p.get("req"):
                req = p["req"].replace("Owned", "Owned").replace("Res", "Res")
                if not req.startswith("×"):
                    req = f"×{req}"
                lines.append(f"**({req})**")
                lines.append("")
            lines.append(p["body"])
            lines.append("")
            lines.append("---")
            lines.append("")

    return "\n".join(lines).rstrip() + "\n"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


SLUG_TO_WIKI_OVERRIDES: dict[str, str] = {
    "Ring_Apprentice_Faust": "The_House_of_Spiders:_The_Ring_Apprentice_Faust",
    "Ring_Pointillist_Student_Yi_Sang": "The_Ring_Pointillist_Student_Yi_Sang",
}


def page_title_to_filename(page_title: str) -> str:
    """Convert wiki page title to parsed-ids filename stem (Windows-safe)."""
    title = unquote(page_title)
    title = title.replace(" ", "_")
    # Windows forbids : in filenames — E.G.O pages use ::
    title = title.replace("::", "_")
    title = title.replace(":", "_")
    while "__" in title:
        title = title.replace("__", "_")
    return title


def filename_to_wiki_title(stem: str) -> str:
    """Map parsed-ids filename stem back to wiki page title."""
    if stem in SLUG_TO_WIKI_OVERRIDES:
        return SLUG_TO_WIKI_OVERRIDES[stem]
    if "_E.G.O_" in stem:
        return stem.replace("_E.G.O_", "_E.G.O::", 1)
    if stem.startswith("The_House_of_Spiders_The_"):
        return stem.replace("The_House_of_Spiders_", "The_House_of_Spiders:_", 1)
    return stem


def wiki_title_to_stem(page_title: str) -> str:
    """Map wiki page title to parsed-ids filename stem (respects project slug overrides)."""
    title = unquote(page_title)
    for stem, wiki_title in SLUG_TO_WIKI_OVERRIDES.items():
        if wiki_title == title:
            return stem
    return page_title_to_filename(title)


def fetch_and_save(
    page_title: str,
    out_dir: Path | None = None,
    delay_s: float = 0.5,
    *,
    stem: str | None = None,
) -> Path:
    dest_dir = out_dir or PARSED_IDS_DIR
    dest_dir.mkdir(parents=True, exist_ok=True)
    wt = fetch_wikitext(page_title)
    md = render_markdown(page_title, wt)
    out_stem = stem or wiki_title_to_stem(page_title)
    path = dest_dir / f"{out_stem}.md"
    path.write_text(md, encoding="utf-8")
    time.sleep(delay_s)
    return path


def fetch_batch(page_titles: list[str], out_dir: Path | None = None) -> list[tuple[str, str | Path]]:
    """Return list of (title, path_or_error). Skips files that already exist with _manual suffix."""
    results = []
    for title in page_titles:
        try:
            path = fetch_and_save(title, out_dir=out_dir)
            results.append((title, path))
        except Exception as exc:
            results.append((title, f"ERROR: {exc}"))
    return results


def infer_sinner_from_wikitext(page_title: str) -> str:
    wt = fetch_wikitext(page_title)
    return infer_sinner_from_body(wt)


def infer_sinner_from_body(wt: str) -> str:
    body = _extract_idpage(wt)
    return _line_value(body, "sinner") or "Unknown"


def save_parsed_markdown(
    page_title: str,
    wt: str,
    out_dir: Path | None = None,
    *,
    stem: str | None = None,
) -> Path:
    """Render wikitext to markdown and write to parsed-ids (no network fetch)."""
    dest_dir = out_dir or PARSED_IDS_DIR
    dest_dir.mkdir(parents=True, exist_ok=True)
    md = render_markdown(page_title, wt)
    out_stem = stem or wiki_title_to_stem(page_title)
    path = dest_dir / f"{out_stem}.md"
    path.write_text(md, encoding="utf-8")
    return path


def resolve_wiki_title(stem: str) -> str:
    """Map project slug to live wiki page title (probes API with retry candidates)."""
    candidates: list[str] = []
    seen: set[str] = set()

    def add(title: str) -> None:
        if title not in seen:
            seen.add(title)
            candidates.append(title)

    add(filename_to_wiki_title(stem))
    if stem in SLUG_TO_WIKI_OVERRIDES:
        add(SLUG_TO_WIKI_OVERRIDES[stem])
    if "_E.G.O_" in stem:
        add(stem.replace("_E.G.O_", "_E.G.O::", 1))
    if stem.startswith("The_House_of_Spiders_The_"):
        add(stem.replace("The_House_of_Spiders_", "The_House_of_Spiders:_", 1))
    add(stem)

    last_err: Exception | None = None
    for title in candidates:
        try:
            fetch_wikitext(title)
            return title
        except Exception as exc:
            last_err = exc
    raise ValueError(f"Could not resolve wiki title for slug {stem!r}: {last_err}")
