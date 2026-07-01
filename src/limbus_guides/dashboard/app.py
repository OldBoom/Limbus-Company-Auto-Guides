"""Streamlit dashboard — landing → sinner grid → identity cards → guide."""

from __future__ import annotations

import base64
import html as html_lib
import json
import sys
from pathlib import Path
from urllib.parse import quote

# Allow `streamlit run src/limbus_guides/dashboard/app.py` without editable install.
_SRC = Path(__file__).resolve().parents[2]
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

import streamlit as st

from limbus_guides.config_io import load_json_config
from limbus_guides.nlp.generation import _embedding_verify_note
from limbus_guides.paths import CONFIG_DIR, GUIDES_DIR

STATIC_DIR = Path(__file__).resolve().parent / "static" / "images"
IDENTITY_PORTRAIT_DIR = STATIC_DIR / "identities"
IDENTITY_PORTRAIT_COLS = [1.5, 7, 1.5]

SINNER_COLS_PER_ROW = 6

# Landing-page dummy content (not loaded from pipeline)
_DUMMY_CORE_IDEA = (
    "A one- or two-sentence summary of how this identity wants to fight — "
    "its role, main resource loop, and win condition."
)
_DUMMY_MECHANICS = "Bleed · Poise · Charge"
_DUMMY_PLAYSTYLE = (
    "- Build your resource with S2, then cash out with S3 once the threshold is met.\n\n"
    "**S1 — Example Skill** (BP 4, CP +3, x2): rolls — low 4, high 10 (Average).\n"
    "- Applies statuses to set up your finisher.\n\n"
    "**S3 — Finisher Skill** (BP 5, CP +4, x3): rolls — low 5, high 17 (High).\n"
    "- Commit when scaling conditions are active."
)
_DUMMY_TEAMS = (
    "- **Teammate Identity A**: inflicts Bleed via support passive — scales your damage.\n"
    "- **Teammate Identity B**: shares faction synergy for passive bonuses."
)

STAGE_LANDING = "landing"
STAGE_SINNER = "sinner"
STAGE_IDENTITY = "identity"
STAGE_GUIDE = "guide"


def _load_config() -> dict:
    path = CONFIG_DIR / "sinners.json"
    if path.exists():
        return load_json_config(path)
    return {"sinners": []}


def _load_guides() -> dict[str, dict]:
    guides: dict[str, dict] = {}
    for p in sorted(GUIDES_DIR.glob("*.json")):
        if p.name == "manifest.json":
            continue
        guides[p.stem] = json.loads(p.read_text(encoding="utf-8"))
    return guides


def _init_session_state() -> None:
    defaults = {
        "stage": STAGE_LANDING,
        "selected_sinner": None,
        "selected_slug": None,
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val


def _set_stage(stage: str) -> None:
    st.session_state.stage = stage


def _go_to_sinner_grid() -> None:
    st.query_params.clear()
    st.session_state.selected_sinner = None
    st.session_state.selected_slug = None
    _set_stage(STAGE_SINNER)
    st.rerun()


def _handle_portrait_pick_query(sinners: list[dict]) -> None:
    """Portrait / name links set ?pick=<name>; consume it once and open identity cards."""
    pick = st.query_params.get("pick")
    if not pick:
        return
    st.query_params.clear()
    valid = {s["name"] for s in sinners}
    if pick in valid:
        _select_sinner(pick)


def _handle_identity_pick_query(guides: dict[str, dict]) -> None:
    """Identity portrait links set ?identity=<slug>; consume once and open the guide."""
    slug = st.query_params.get("identity")
    if not slug:
        return
    st.query_params.clear()
    guide = guides.get(slug)
    if guide:
        st.session_state.selected_slug = slug
        st.session_state.selected_sinner = guide.get("sinner")
        _set_stage(STAGE_GUIDE)
        st.rerun()


def _sinner_pick_url(sinner_name: str) -> str:
    return f"?pick={quote(sinner_name)}"


def _identity_pick_url(slug: str) -> str:
    return f"?identity={quote(slug)}"


def _portrait_path(sinner_name: str) -> Path | None:
    stem = sinner_name.replace(" ", "_")
    path = STATIC_DIR / f"{stem}_StoryLog.png"
    return path if path.exists() else None


@st.cache_data
def _identity_portrait_filenames() -> dict[str, str]:
    manifest_path = IDENTITY_PORTRAIT_DIR / "manifest.json"
    if not manifest_path.exists():
        return {}
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    return {
        slug: entry["filename"]
        for slug, entry in data.get("identities", {}).items()
    }


def _identity_portrait_path(slug: str) -> Path | None:
    filename = _identity_portrait_filenames().get(slug)
    if filename:
        path = IDENTITY_PORTRAIT_DIR / filename
        if path.exists():
            return path
    fallback = IDENTITY_PORTRAIT_DIR / f"{slug}.png"
    return fallback if fallback.exists() else None


def _render_identity_portrait_image(slug: str, *, sinner_name: str) -> None:
    """Identity artwork at the same 70% width used on the selection cards."""
    path = _identity_portrait_path(slug) or _portrait_path(sinner_name)
    _, img_col, _ = st.columns(IDENTITY_PORTRAIT_COLS)
    with img_col:
        if path:
            st.image(str(path), use_container_width=True)
        else:
            st.markdown(f"**{sinner_name}**")


def _shorten(text: str, max_len: int = 40) -> str:
    if len(text) <= max_len:
        return text
    return text[: max_len - 1].rstrip() + "…"


def _guides_for_sinner(sinner_name: str, guides: dict[str, dict]) -> dict[str, dict]:
    return {slug: g for slug, g in guides.items() if g.get("sinner") == sinner_name}


def _format_synergy_row(entry: dict) -> str:
    name = entry.get("teammate_name") or entry.get("teammate_slug", "Unknown")
    reason = entry.get("reason", "")
    score = entry.get("score")
    source = entry.get("source", "")
    tags: list[str] = []
    if source:
        tags.append(source)
    if entry.get("faction_match"):
        tags.append("faction")
    if entry.get("unique_tremor_match"):
        tags.append("tremor subtype")
    tag_str = f" ({', '.join(tags)})" if tags else ""
    score_str = f" — score {score:.2f}" if isinstance(score, (int, float)) else ""
    return f"**{name}**{score_str}{tag_str}: {reason}"


def _render_team_suggestions(guide: dict, guides: dict[str, dict]) -> None:
    """Render team suggestions with clickable teammate names when picks are available."""
    picks = guide.get("team_suggestion_picks")
    lines = guide.get("team_suggestions", [])

    if picks:
        intro = guide.get("team_suggestion_intro")
        if intro:
            st.markdown(intro)
        else:
            # Legacy guides: infer intro from lines before teammate bullets.
            intro_lines = lines[: len(lines) - len(picks)] if len(lines) >= len(picks) else []
            for legacy_intro in intro_lines:
                st.markdown(legacy_intro)
        for pick in picks:
            name = pick.get("teammate_name", "")
            reason = pick.get("reason", "")
            slug = pick.get("teammate_slug", "")
            suffix = f"{reason}{_embedding_verify_note(pick.get('source', ''))}"
            if slug and slug in guides:
                href = html_lib.escape(_identity_pick_url(slug), quote=True)
                name_esc = html_lib.escape(name)
                suffix_esc = html_lib.escape(suffix)
                title_esc = html_lib.escape(f"Open guide: {name}")
                st.markdown(
                    f'- <a href="{href}" class="lc-inline-link" title="{title_esc}">'
                    f"<strong>{name_esc}</strong></a>: {suffix_esc}",
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(f"- **{name}**: {suffix}")
        return

    for line in lines:
        st.markdown(line)


def _render_methodology(guide: dict) -> None:
    st.markdown(
        "Guides are generated from parsed wiki skill data and constrained by gameplay rules in "
        "`docs/domain-primer.md` (turn vs rotation, Skill 3 timing, synergy patterns). "
        "Team suggestions below the playstyle section are the player-facing output; "
        "this panel shows how they were ranked."
    )
    if guide.get("domain_context"):
        st.caption(f"Domain context: `{guide['domain_context']}`")
    if guide.get("generator"):
        st.caption(f"Generator: `{guide['generator']}`")

    synergies = guide.get("synergies") or []
    if synergies:
        st.markdown("**Ranked teammate matches**")
        for entry in synergies[:8]:
            st.markdown(f"- {_format_synergy_row(entry)}")
    else:
        st.caption("No synergy records for this identity.")


def _render_landing() -> None:
    st.title("Limbus Company Auto Guides")
    st.caption("Wiki-grounded identity guides — core idea, playstyle, team suggestions")

    _, center, _ = st.columns([1, 2, 1])
    with center:
        st.info("Preview below — pick a character to load a real guide.")

        st.markdown("### ① Core Idea")
        st.caption("*What this section tells you: the identity's role and overall gameplan in 1–2 sentences.*")
        st.write(_DUMMY_CORE_IDEA)

        st.markdown("### ② Primary Mechanics")
        st.caption("*Keywords for the main systems this kit revolves around (statuses, resources, passives).*")
        st.write(_DUMMY_MECHANICS)

        st.markdown("### ③ Playstyle Guide")
        st.caption("*Rotation tips, per-skill breakdowns, roll estimates, and passive notes.*")
        st.markdown(_DUMMY_PLAYSTYLE)

        st.markdown("### ④ Team Suggestions")
        st.caption("*Recommended teammates and why they synergize — ranked by mechanic overlap.*")
        st.markdown(_DUMMY_TEAMS)

        st.markdown("")
        if st.button("→ Pick a character", type="primary", use_container_width=True):
            _go_to_sinner_grid()


def _select_sinner(sinner_name: str) -> None:
    st.session_state.selected_sinner = sinner_name
    st.session_state.selected_slug = None
    _set_stage(STAGE_IDENTITY)
    st.rerun()


def _render_query_link(label: str, href: str, *, title: str = "") -> None:
    """Same-window navigation via query params (matches portrait pickers)."""
    label_esc = html_lib.escape(label)
    href_esc = html_lib.escape(href, quote=True)
    title_attr = f' title="{html_lib.escape(title)}"' if title else ""
    st.markdown(
        f'<a href="{href_esc}" class="lc-pick-link"{title_attr}>{label_esc}</a>',
        unsafe_allow_html=True,
    )


def _render_portrait_picker(path: Path, *, sinner_name: str) -> None:
    """Clickable portrait — each cell is its own link (no shared element ids)."""
    b64 = base64.b64encode(path.read_bytes()).decode()
    href = html_lib.escape(_sinner_pick_url(sinner_name), quote=True)
    name_esc = html_lib.escape(sinner_name)
    st.html(
        f"""
        <a href="{href}" style="display:block;line-height:0;text-decoration:none"
           title="Select {name_esc}">
          <img src="data:image/png;base64,{b64}" alt="{name_esc}"
               style="width:100%;height:auto;display:block;cursor:pointer;border-radius:4px" />
        </a>
        """,
        width="stretch",
    )


def _render_identity_portrait_picker(path: Path, *, slug: str, title: str) -> None:
    """Clickable identity artwork on the identity selection cards."""
    b64 = base64.b64encode(path.read_bytes()).decode()
    href = html_lib.escape(_identity_pick_url(slug), quote=True)
    title_esc = html_lib.escape(title)
    st.html(
        f"""
        <a href="{href}" style="display:block;line-height:0;text-decoration:none"
           title="Open guide: {title_esc}">
          <img src="data:image/png;base64,{b64}" alt="{title_esc}"
               style="width:100%;height:auto;display:block;cursor:pointer;border-radius:4px" />
        </a>
        """,
        width="stretch",
    )


def _render_portrait_image(sinner_name: str) -> None:
    """Portrait at the same visual size as the choose-character grid."""
    _, mid, _ = st.columns([1, 5, 1])
    with mid:
        portrait = _portrait_path(sinner_name)
        if portrait:
            st.image(str(portrait), use_container_width=True)
        else:
            st.markdown(f"**{sinner_name}**")


def _render_dashboard_styles() -> None:
    """Shared CSS for sinner grid and portrait slots."""
    st.markdown(
        """
        <style>
        /* Six-column sinner rows: wrap to 3 per row on phones */
        @media (max-width: 640px) {
            [data-testid="stHorizontalBlock"]:has(> [data-testid="column"]:nth-child(6)):not(:has(:nth-child(7))) {
                flex-wrap: wrap !important;
            }
            [data-testid="stHorizontalBlock"]:has(> [data-testid="column"]:nth-child(6)):not(:has(:nth-child(7)))
            > [data-testid="column"] {
                flex: 0 0 33.333% !important;
                max-width: 33.333% !important;
            }
        }
        /* Text pick links styled like Streamlit secondary buttons */
        a.lc-pick-link {
            display: block;
            width: 100%;
            text-align: center;
            padding: 0.35rem 0.2rem;
            font-size: 0.72rem;
            line-height: 1.2;
            text-decoration: none;
            color: rgb(250, 250, 250);
            border: 1px solid rgba(250, 250, 250, 0.2);
            border-radius: 0.5rem;
            background: rgba(255, 255, 255, 0.05);
            cursor: pointer;
            box-sizing: border-box;
        }
        a.lc-pick-link:hover {
            border-color: rgb(255, 75, 75);
            color: rgb(255, 75, 75);
        }
        /* Inline teammate links in Team Suggestions */
        a.lc-inline-link {
            color: inherit;
            text-decoration: none;
        }
        a.lc-inline-link:hover {
            color: rgb(255, 75, 75);
            text-decoration: underline;
        }
        a.lc-inline-link strong {
            font-weight: 600;
        }
        /* Sinner name link width inside grid cells */
        [data-testid="stHorizontalBlock"]:has(> [data-testid="column"]:nth-child(6)):not(:has(:nth-child(7)))
        [data-testid="column"] a.lc-pick-link {
            width: 100% !important;
            font-size: 0.72rem !important;
        }
        /* Sinner portrait on identity-picker header */
        .lc-portrait-slot [data-testid="stVerticalBlock"] .stImage img {
            width: 100% !important;
            height: auto !important;
            display: block !important;
            border-radius: 4px !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _render_sinner_cell(sinner: dict) -> None:
    """Clickable portrait and name link in a shared narrow column."""
    _, mid, _ = st.columns([1, 5, 1])
    with mid:
        pick_url = _sinner_pick_url(sinner["name"])
        portrait = _portrait_path(sinner["name"])
        if portrait:
            _render_portrait_picker(portrait, sinner_name=sinner["name"])
        else:
            st.markdown(f"**{sinner['name']}**")
        _render_query_link(
            sinner["name"],
            pick_url,
            title=f"Select {sinner['name']}",
        )


def _render_sinner_grid(sinners: list[dict], guides: dict[str, dict]) -> None:
    if st.button("← Back to intro"):
        st.query_params.clear()
        st.session_state.selected_sinner = None
        st.session_state.selected_slug = None
        _set_stage(STAGE_LANDING)
        st.rerun()

    st.title("Choose a character")
    st.caption("Select one of the twelve Sinners to browse their identity guides.")

    available = [s for s in sinners if _guides_for_sinner(s["name"], guides)]
    if not available:
        st.warning("No guides found for any sinner. Run: `python scripts/run_pipeline.py`")
        return

    for row_start in range(0, len(available), SINNER_COLS_PER_ROW):
        row = available[row_start : row_start + SINNER_COLS_PER_ROW]
        cols = st.columns(SINNER_COLS_PER_ROW)
        for col, sinner in zip(cols, row):
            with col:
                _render_sinner_cell(sinner)


def _render_identity_cards(sinner_name: str, guides: dict[str, dict]) -> None:
    if st.button("← Back to characters"):
        _go_to_sinner_grid()

    sinner_guides = _guides_for_sinner(sinner_name, guides)
    if not sinner_guides:
        st.warning(f"No guides for {sinner_name}.")
        if st.button("← Back to characters"):
            _go_to_sinner_grid()
        return

    header_cols = st.columns([1, 5])
    with header_cols[0]:
        st.markdown('<div class="lc-portrait-slot">', unsafe_allow_html=True)
        _render_portrait_image(sinner_name)
        st.markdown("</div>", unsafe_allow_html=True)
    with header_cols[1]:
        st.title(sinner_name)
        st.caption("Choose an identity to open its guide.")

    slugs = sorted(sinner_guides.keys(), key=lambda s: sinner_guides[s].get("identity_name", s))
    cols = st.columns(len(slugs))
    for col, slug in zip(cols, slugs):
        guide = sinner_guides[slug]
        name = guide.get("identity_name", slug.replace("_", " "))
        profile = guide.get("mechanic_profile", {})
        mechanics = profile.get("primary_mechanics", [])
        mech_str = " · ".join(mechanics[:4]) if mechanics else "—"

        with col:
            with st.container(border=True):
                portrait = _identity_portrait_path(slug) or _portrait_path(sinner_name)
                if portrait:
                    _render_identity_portrait_picker(portrait, slug=slug, title=name)
                    st.markdown(f"**{_shorten(name)}**")
                else:
                    st.markdown(f"**{_shorten(name)}**")
                st.caption(mech_str)
                _render_query_link(
                    "Select",
                    _identity_pick_url(slug),
                    title=f"Open guide: {name}",
                )


def _render_guide(
    guide: dict,
    sinner_name: str,
    *,
    slug: str,
    guides: dict[str, dict],
) -> None:
    profile = guide.get("mechanic_profile", {})

    nav_cols = st.columns([1, 1, 4])
    with nav_cols[0]:
        if st.button("← Change character"):
            _go_to_sinner_grid()
    with nav_cols[1]:
        if st.button("← Other identities"):
            _set_stage(STAGE_IDENTITY)
            st.rerun()

    header_cols = st.columns([2, 5])
    with header_cols[0]:
        _render_identity_portrait_image(slug, sinner_name=sinner_name)
    with header_cols[1]:
        st.header(guide.get("identity_name", "—"))
        st.caption(f"Character: {sinner_name}")
        st.markdown("### Core Idea")
        st.write(guide.get("core_idea", ""))
        st.markdown("### Primary Mechanics")
        st.write(", ".join(profile.get("primary_mechanics", [])) or "—")

    st.markdown("### Playstyle Guide")
    st.markdown(guide.get("playstyle_guide", ""))

    st.markdown("### Team Suggestions")
    _render_team_suggestions(guide, guides)

    with st.expander("How this guide was built"):
        _render_methodology(guide)

    with st.expander("Pipeline JSON (dev)"):
        st.markdown("**Mechanic profile**")
        st.json(profile)
        st.markdown("**Synergies (raw)**")
        st.json(guide.get("synergies", []))


def main() -> None:
    st.set_page_config(page_title="Limbus Company Auto Guides", layout="wide")
    _init_session_state()

    config = _load_config()
    guides = _load_guides()

    if not guides:
        st.warning("No guides found. Run: `python scripts/run_pipeline.py`")
        st.stop()

    _render_dashboard_styles()

    sinners = config.get("sinners", [])
    _handle_portrait_pick_query(sinners)
    _handle_identity_pick_query(guides)
    stage = st.session_state.stage

    if stage == STAGE_LANDING:
        _render_landing()
    elif stage == STAGE_SINNER:
        _render_sinner_grid(sinners, guides)
    elif stage == STAGE_IDENTITY:
        sinner_name = st.session_state.selected_sinner
        if not sinner_name:
            _set_stage(STAGE_SINNER)
            st.rerun()
        _render_identity_cards(sinner_name, guides)
    elif stage == STAGE_GUIDE:
        slug = st.session_state.selected_slug
        sinner_name = st.session_state.selected_sinner
        if not slug or not sinner_name:
            _set_stage(STAGE_SINNER)
            st.rerun()
        guide = guides.get(slug)
        if not guide:
            st.error("Guide not found.")
            _set_stage(STAGE_IDENTITY)
            st.rerun()
        _render_guide(guide, sinner_name, slug=slug, guides=guides)
    else:
        _set_stage(STAGE_LANDING)
        st.rerun()


if __name__ == "__main__":
    main()
