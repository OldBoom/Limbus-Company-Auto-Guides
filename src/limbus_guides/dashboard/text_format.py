"""Render guide prose with in-game status colours and highlighted numbers."""

from __future__ import annotations

import html
import re
from functools import lru_cache

from limbus_guides.ingestion.unique_mechanics_registry import get_all_unique_mechanics
from limbus_guides.nlp.mechanics import STATUS_EFFECTS
from limbus_guides.paths import DOCS_DIR

_STATUS_EFFECTS_MD = DOCS_DIR / "status-effects.md"

_BOLD_RE = re.compile(r"\*\*(.+?)\*\*")
_NUM_RE = re.compile(
    r"(?<![A-Za-z])"
    r"(\+\d+(?:\.\d+)?%?|\d+(?:\.\d+)?%|\d+(?:\.\d+)?)"
    r"(?!\w)"
)

# Core sin keywords — fallback if markdown parse misses them.
_CORE_POSITIVE = {"Poise", "Charge"}
_CORE_NEGATIVE = {"Bleed", "Burn", "Tremor", "Rupture", "Sinking"}
_CORE_NEUTRAL: set[str] = set()

# Standard universal lists (status-effects.md).
_BUFF_NAMES = (
    "Power Up",
    "Attack Power Up",
    "Defense Power Up",
    "Clash Power Up",
    "Base Power Up",
    "Offense Level Up",
    "Defense Level Up",
    "Haste",
    "Damage Up",
    "Protection",
    "Crit DMG Up",
    "Plus Coin Boost",
    "Minus Coin Drop",
    "HP Healing Boost",
    "Weak-resist DMG Boost",
    "E.G.O Resource Amp",
    "Slash DMG Up",
    "Pierce DMG Up",
    "Blunt DMG Up",
    "Wrath DMG Up",
    "Lust DMG Up",
    "Sloth DMG Up",
    "Gluttony DMG Up",
    "Gloom DMG Up",
    "Pride DMG Up",
    "Envy DMG Up",
    "Slash Power Up",
    "Pierce Power Up",
    "Blunt Power Up",
    "Wrath Power Up",
    "Lust Power Up",
    "Sloth Power Up",
    "Gluttony Power Up",
    "Gloom Power Up",
    "Pride Power Up",
    "Envy Power Up",
    "Slash Protection",
    "Pierce Protection",
    "Blunt Protection",
    "Wrath Protection",
    "Lust Protection",
    "Sloth Protection",
    "Gluttony Protection",
    "Gloom Protection",
    "Pride Protection",
    "Envy Protection",
)

_DEBUFF_NAMES = (
    "Power Down",
    "Attack Power Down",
    "Defense Power Down",
    "Clash Power Down",
    "Offense Level Down",
    "Defense Level Down",
    "Bind",
    "Damage Down",
    "Fragile",
    "Paralyze",
    "Plus Coin Drop",
    "Minus Coin Boost",
    "HP Healing Down",
    "Poison",
    "Immobilized",
    "Slash DMG Down",
    "Pierce DMG Down",
    "Blunt DMG Down",
    "Wrath DMG Down",
    "Lust DMG Down",
    "Sloth DMG Down",
    "Gluttony DMG Down",
    "Gloom DMG Down",
    "Pride DMG Down",
    "Envy DMG Down",
    "Slash Power Down",
    "Pierce Power Down",
    "Blunt Power Down",
    "Wrath Power Down",
    "Lust Power Down",
    "Sloth Power Down",
    "Gluttony Power Down",
    "Gloom Power Down",
    "Pride Power Down",
    "Envy Power Down",
    "Slash Fragility",
    "Pierce Fragility",
    "Blunt Fragility",
    "Wrath Fragility",
    "Lust Fragility",
    "Sloth Fragility",
    "Gluttony Fragility",
    "Gloom Fragility",
    "Pride Fragility",
    "Envy Fragility",
    "Slash Resist Down",
    "Pierce Resist Down",
    "Wrath Resist Down",
    "Gloom Resist Down",
    "Envy Resist Down",
    "Fragility",
    "Impending Ruin",
    "Nails",
)

_NEUTRAL_NAMES = (
    "Aggro",
    "Unbreakable Coin",
    "Corpus Ingredient",
    "Artwork: Fascia",
    "Bloodfeast",
    "Torn Memory",
    "Discard",
    "Insight",
    "Erudition",
    "Arrow",
    "Magic Bullet",
    "Responsibility",
    "Assist Defense",
)


def _table_effect_names(section: str) -> list[str]:
    return [
        m.group(1).strip()
        for m in re.finditer(r"^\| ([^|]+?) \|", section, re.M)
        if m.group(1).strip() not in ("Effect", "---", "--------")
    ]


@lru_cache(maxsize=1)
def build_status_category_map() -> dict[str, str]:
    """
    Map effect name -> 'positive' | 'neutral' | 'negative'.
    Parsed from docs/status-effects.md with static fallbacks.
    """
    categories: dict[str, str] = {}

    for name in _CORE_POSITIVE:
        categories[name] = "positive"
    for name in _CORE_NEGATIVE:
        categories[name] = "negative"
    for name in _CORE_NEUTRAL:
        categories[name] = "neutral"
    for name in _BUFF_NAMES:
        categories[name] = "positive"
    for name in _DEBUFF_NAMES:
        categories[name] = "negative"
    for name in _NEUTRAL_NAMES:
        categories[name] = "neutral"
    for name in STATUS_EFFECTS:
        if name in ("Poise", "Charge", "Haste", "Protection", "Shield"):
            categories.setdefault(name, "positive")
        elif name in ("Bind",):
            categories.setdefault(name, "negative")

    if _STATUS_EFFECTS_MD.exists():
        md = _STATUS_EFFECTS_MD.read_text(encoding="utf-8")

        for m in re.finditer(
            r"^### (.+?)\s*\n+\*\*Type:\*\* (Positive|Negative)",
            md,
            re.M,
        ):
            kind = "positive" if m.group(2) == "Positive" else "negative"
            categories[m.group(1).strip()] = kind

        sections = re.split(r"^## ", md, flags=re.M)
        current_kind: str | None = None
        for block in sections:
            header, _, body = block.partition("\n")
            title = header.strip()
            if title.startswith("Standard Buffs"):
                current_kind = "positive"
            elif title.startswith("Standard Debuffs"):
                current_kind = "negative"
            elif title.startswith("Neutral Effects"):
                current_kind = "neutral"
            elif title.startswith("Unique "):
                parent = title.replace("Unique ", "").split()[0]
                if parent in ("Burn", "Bleed", "Tremor", "Rupture", "Sinking"):
                    current_kind = "negative"
                elif parent == "Poise":
                    current_kind = "positive"
                elif parent == "Charge":
                    current_kind = "positive"
            elif title in ("Core Keywords", "Typed Modifier Effects", "Deathrite Variants"):
                current_kind = None

            if current_kind and "| Effect |" in body:
                for name in _table_effect_names(body):
                    if name and not name.startswith("---"):
                        categories.setdefault(name, current_kind)

    # Identity-specific resources from the auto-registry (neutral unless already classified).
    for name in get_all_unique_mechanics():
        categories.setdefault(name, "neutral")

    return categories


def _span_status(name: str, kind: str) -> str:
    cls = {"positive": "lc-status-pos", "neutral": "lc-status-neu", "negative": "lc-status-neg"}[kind]
    return f'<span class="{cls}">{html.escape(name)}</span>'


def _highlight_statuses(text: str, categories: dict[str, str]) -> str:
    """Longest-match-first status highlights."""
    names = sorted(categories.keys(), key=len, reverse=True)
    if not names:
        return text

    out: list[str] = []
    i = 0
    while i < len(text):
        matched = False
        for name in names:
            nlen = len(name)
            chunk = text[i : i + nlen]
            if len(chunk) != nlen or chunk.lower() != name.lower():
                continue
            before_ok = i == 0 or not (text[i - 1].isalnum() or text[i - 1] in ":—-")
            after_ok = (
                i + nlen >= len(text)
                or not (text[i + nlen].isalnum() or text[i + nlen] in ":—-")
            )
            if before_ok and after_ok:
                out.append(_span_status(chunk, categories[name]))
                i += nlen
                matched = True
                break
        if not matched:
            out.append(text[i])
            i += 1
    return "".join(out)


def _highlight_numbers(text: str) -> str:
    def repl(m: re.Match[str]) -> str:
        return f'<span class="lc-num">{m.group(1)}</span>'

    return _NUM_RE.sub(repl, text)


def format_inline_guide_text(text: str) -> str:
    """Escape HTML, apply bold, status colours, and number highlights."""
    escaped = html.escape(text)
    parts: list[str] = []
    last = 0
    for m in _BOLD_RE.finditer(escaped):
        before = escaped[last : m.start()]
        parts.append(_highlight_numbers(_highlight_statuses(before, build_status_category_map())))
        inner = _highlight_numbers(_highlight_statuses(m.group(1), build_status_category_map()))
        parts.append(f"<strong>{inner}</strong>")
        last = m.end()
    tail = escaped[last:]
    parts.append(_highlight_numbers(_highlight_statuses(tail, build_status_category_map())))
    return "".join(parts)


def format_guide_html(text: str) -> str:
    """Convert guide markdown-ish text to HTML paragraphs."""
    if not text:
        return ""
    blocks: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            blocks.append("<br>")
            continue
        inner = format_inline_guide_text(stripped)
        if stripped.startswith("- "):
            blocks.append(f'<p class="lc-guide-line lc-guide-bullet">{inner}</p>')
        elif stripped.startswith("*↳"):
            blocks.append(f'<p class="lc-guide-line lc-guide-alt">{inner}</p>')
        else:
            blocks.append(f'<p class="lc-guide-line">{inner}</p>')
    return "\n".join(blocks)


_CORE_LEAD_RE = re.compile(r"^(.+?) is a (.+?) — (.+)$")
_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")


def _classify_core_detail(sentence: str) -> tuple[str, str]:
    """Return (block_kind, display_text)."""
    if sentence.startswith("Scaling conditions:"):
        return "scaling", sentence[len("Scaling conditions:") :].strip()
    if sentence.lower().startswith("support passive"):
        return "support", sentence
    if "heads-flip dependent" in sentence.lower() or sentence.startswith("Key damage is Heads"):
        return "variance", sentence
    return "detail", sentence


def format_core_idea_html(text: str) -> str:
    """
    Render core idea as a readable card: role tags, hook line, then labeled detail blocks.
    Falls back to formatted prose when the standard lead pattern is missing.
    """
    if not text or not text.strip():
        return ""

    sentences = [s.strip() for s in _SENTENCE_SPLIT_RE.split(text.strip()) if s.strip()]
    if not sentences:
        return ""

    lead = sentences[0]
    extras = sentences[1:]
    match = _CORE_LEAD_RE.match(lead)

    if not match:
        return f'<div class="lc-core-idea">{format_guide_html(text)}</div>'

    roles_raw = match.group(2).strip()
    hook = match.group(3).strip()
    roles = [r.strip() for r in roles_raw.split("/") if r.strip()]
    role_html = "".join(
        f'<span class="lc-core-role">{html.escape(role)}</span>' for role in roles
    )

    blocks: list[str] = [
        '<div class="lc-core-idea">',
        f'<div class="lc-core-roles">{role_html}</div>',
        f'<p class="lc-core-hook">{format_inline_guide_text(hook)}</p>',
    ]

    if extras:
        blocks.append('<div class="lc-core-details">')
        for sentence in extras:
            kind, body = _classify_core_detail(sentence)
            inner = format_inline_guide_text(body)
            if kind == "detail":
                blocks.append(f'<p class="lc-core-detail">{inner}</p>')
            else:
                label = {"scaling": "Scaling", "support": "Support", "variance": "Variance"}[kind]
                blocks.append(
                    f'<div class="lc-core-block lc-core-{kind}">'
                    f'<span class="lc-core-label">{label}</span>'
                    f'<p class="lc-core-block-body">{inner}</p>'
                    f"</div>"
                )
        blocks.append("</div>")

    blocks.append("</div>")
    return "\n".join(blocks)


def guide_format_css() -> str:
    """CSS for status categories and numeric highlights."""
    return """
    .lc-status-pos {
        background: rgba(255, 214, 0, 0.38);
        color: inherit;
        padding: 0 0.15em;
        border-radius: 2px;
    }
    .lc-status-neu {
        background: rgba(160, 110, 60, 0.38);
        color: inherit;
        padding: 0 0.15em;
        border-radius: 2px;
    }
    .lc-status-neg {
        background: rgba(255, 75, 75, 0.28);
        color: inherit;
        padding: 0 0.15em;
        border-radius: 2px;
    }
    .lc-num {
        color: #2dd4bf;
        font-weight: 600;
    }
    .lc-guide-line {
        margin: 0.25rem 0;
        line-height: 1.45;
    }
    .lc-guide-bullet {
        margin-left: 0.25rem;
        padding-left: 0.5rem;
    }
    .lc-guide-alt {
        margin-left: 1rem;
        opacity: 0.92;
    }
    .lc-formatted-prose p {
        margin: 0.35rem 0;
        line-height: 1.45;
    }
    .lc-core-idea {
        margin: 0.5rem 0 0.75rem;
        padding: 0.85rem 1rem 0.95rem;
        border-radius: 8px;
        border: 1px solid rgba(255, 255, 255, 0.1);
        background: rgba(255, 255, 255, 0.03);
    }
    .lc-core-roles {
        display: flex;
        flex-wrap: wrap;
        gap: 0.35rem;
        margin-bottom: 0.55rem;
    }
    .lc-core-role {
        font-size: 0.72rem;
        font-weight: 600;
        letter-spacing: 0.03em;
        text-transform: uppercase;
        padding: 0.15rem 0.45rem;
        border-radius: 4px;
        background: rgba(255, 255, 255, 0.08);
        color: rgba(255, 255, 255, 0.78);
    }
    .lc-core-hook {
        margin: 0;
        font-size: 1.05rem;
        line-height: 1.55;
        font-weight: 500;
    }
    .lc-core-details {
        margin-top: 0.75rem;
        padding-top: 0.65rem;
        border-top: 1px solid rgba(255, 255, 255, 0.08);
        display: flex;
        flex-direction: column;
        gap: 0.55rem;
    }
    .lc-core-detail {
        margin: 0;
        padding-left: 0.65rem;
        border-left: 2px solid rgba(255, 255, 255, 0.12);
        line-height: 1.5;
        opacity: 0.95;
    }
    .lc-core-block {
        display: grid;
        grid-template-columns: auto 1fr;
        gap: 0.45rem 0.65rem;
        align-items: start;
    }
    .lc-core-label {
        font-size: 0.68rem;
        font-weight: 700;
        letter-spacing: 0.04em;
        text-transform: uppercase;
        padding: 0.2rem 0.4rem;
        border-radius: 4px;
        white-space: nowrap;
        margin-top: 0.1rem;
    }
    .lc-core-scaling .lc-core-label {
        background: rgba(45, 212, 191, 0.15);
        color: #5eead4;
    }
    .lc-core-support .lc-core-label {
        background: rgba(255, 214, 0, 0.15);
        color: #fde68a;
    }
    .lc-core-variance .lc-core-label {
        background: rgba(255, 75, 75, 0.15);
        color: #fca5a5;
    }
    .lc-core-block-body {
        margin: 0;
        line-height: 1.5;
    }
    """
