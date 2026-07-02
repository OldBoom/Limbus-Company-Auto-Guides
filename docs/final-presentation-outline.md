# Final Presentation Outline

**Format:** 10-minute presentation + 5-minute professor discussion (Jul 3, 2026)

**Live URL:** [limbus-company-nlp-guides.streamlit.app](https://limbus-company-nlp-guides.streamlit.app/)

**Main deck:** 10–12 slides, ~600 seconds total. **Appendix:** detail for discussion — not timed.

**Evidence index:** [`evaluation.md`](evaluation.md) · [`sus-user-study-results.md`](sus-user-study-results.md) · [`data/evaluation_results.json`](../data/evaluation_results.json)

---

## Headline numbers (slide 6 / appendix)

| Metric | Value |
|--------|-------|
| Identities guided | **51** (12 sinners) |
| ROUGE-L (full / naive / ablation) | **0.175 / 0.109 / 0.176** |
| Δ vs naive baseline | **+0.066** |
| Pipeline latency (mean / worst) | **1,061 ms / 1,136 ms** per identity |
| Cost per query | **€0** (local template, no API) |
| SUS (n = 7) | **90.4** (range 80.0–97.5; target ≥ 70) |
| Task success | **21 / 21** (100%); **6 / 7** unaided |
| Mean user-study time | **~2.9 min** (all 3 tasks) |
| Unit tests | **55** passing |

---

## Main Deck — Slide Script

| # | Slide | Seconds | Narration notes | Rubric | Repo evidence |
|---|-------|---------|-----------------|--------|---------------|
| 1 | Title + hook | 30 | Persona **Alex** — weekly player prepping for Mirror Dungeon. Problem: wiki pages are dense skill tables; synergy is buried in support passives. | D1, D10 | `lecture-deliverables/deliverable-1-prototype-pitch.md` |
| 2 | Delta vs existing tools | 45 | Not a chatbot — **fixed guide schema** per identity (Core Idea, Playstyle, Team suggestions) with **rule-based synergy**. vs BG3Chat, generic GameWiki, Genshin team builders. | D2 | `lecture-deliverables/deliverable-2-state-of-the-art.md` |
| 3 | Architecture | 60 | wiki.gg wikitext → parse → JSON → NER + embeddings + synergy rules → template generation → pre-built guide JSON → Streamlit. **Structured context, no vector DB.** Diagram: `docs/assets/architecture.png` | D5, D7 | `data-strategy.md`, `project-specification.md` |
| 4 | NLP stack | 60 | spaCy **EntityRuler** for mechanics; **MiniLM** for similarity; **skill_parser** + **archetypes** for playstyle; **synergy.py** rules for teammates; optional Ollama. One before/after: generic keyword guide vs named skills. | D6 | `nlp/`, `poc_evaluation_results.json` |
| 5 | **Live demo** | 210 | Faust → Ring Apprentice → Core Idea → Playstyle → Team suggestions (clickable teammate link). See demo storyboard below. | D3, D7 | Hosted Streamlit or `streamlit run src/limbus_guides/dashboard/app.py` |
| 6 | Evaluation headline | 60 | ROUGE-L **0.175** vs naive **0.109** (+0.066). Ablation ≈ full → synergy shows in team section, not core text. **SUS 90.4**, 100% tasks, ~3 min sessions. | D8 | `evaluation.md`, `sus-user-study-results.md` |
| 7 | Key optimization | 45 | **Offline pipeline:** naive → skill-aware template (+0.066 ROUGE-L). **Archetype tips** replace generic filler. **SUS-driven UI:** colour coding, linked teammates, tab fix — shipped during user study. | D9 | `evaluation.md` § Optimization; `monitoring/logger.py` |
| 8 | Lesson + quote | 30 | Structured-first beats chunk-and-embed for wiki tables. User quote: *"Rapidly navigate through walls of text!"* (P3) or P2 endorsement. | D10 | Post-mortem + quotes below |
| 9 | Summary | 30 | 51 wiki-grounded guides, open pipeline, instant dashboard. Repo + demo URL. | — | GitHub repo |
| — | Buffer | 30 | — | — | — |

**Total:** ~600s (10 min)

### Slide 6 — speaker script (copy to notes)

> "On a held-out set of 50 identities with human reference summaries, our full pipeline scores ROUGE-L 0.175 versus 0.109 for a naive keyword baseline — a 0.066 gap that shows skill parsing matters. Synergy rules barely move ROUGE because teammates live in a separate section; ablation is 0.176 versus 0.175 full. For users, seven participants completed all three tasks in under three minutes on average. Mean SUS is 90.4 — well above the 70 'good' threshold. Only one participant, who never played and needed reading help, received assistance; everyone else worked unaided."

### Slide 7 — speaker script

> "The biggest automatic gain was replacing keyword-only templates with skill-aware generation. The second layer was archetype-specific tips — Poise ramp, retreat kits, Heishou backups — so guides name real skills instead of generic advice. During the user study we also shipped UI fixes users asked for: colour-coded mechanics, clickable teammate names, and stopping duplicate browser tabs."

---

## Demo script (slide 5)

| Step | Screen | Narration (≈) | Latency risk | Backup |
|------|--------|---------------|--------------|--------|
| 1 | Dashboard landing | "Sidebar picks character, then identity — no search box needed." | Low | Pre-open URL |
| 2 | **Faust** → **Ring Apprentice Faust** | "Complex kit — good stress test." | Low | — |
| 3 | **Core Idea** | "Bleed plus Corpus Ingredient resource; Iron Maiden then Flow State transition." | None (JSON) | — |
| 4 | **Playstyle** (scroll) | "Named skills, rotation pressure, when to commit S3 — not a fixed combo string." | None | — |
| 5 | **Team suggestions** | Click one teammate link — "Rule hit: support passive inflicts Bleed for Bleed teams." | Low | Read slug from JSON |
| 6 | (Optional) Mechanic profile | "Extraction layer under the hood — NER tags from wiki text." | Low | Skip if short on time |

**Timing budget:** ~210s total (largest block — rehearse with timer).

**Latency risk:** Dashboard reads pre-generated JSON — **no LLM wait**. Generation runs offline (`python scripts/run_pipeline.py`).

**Backup clip:** 30–60s screen recording → `docs/assets/demo-backup.mp4` (Faust → Ring Apprentice → Core Idea → Playstyle → Team suggestions).

**Narration during any load:** "Guides are pre-generated offline so the UI stays instant."

---

## Presentation quotes (slide 8 / appendix)

| Participant | Quote | Use |
|-------------|-------|-----|
| P2 | *"System is very easy to navigate, the core ideas of each id are easy to understand, even when only skimmed."* | Usability |
| P2 | *"I must insist... that you continue working on this tool."* … *"For that would be most ideal."* | Enthusiasm |
| P3 | *"Rapidly navigate through walls of text!"* | vs wiki |
| P6 | *"TETO NUMBERO UNO!"* | Light closer |
| P7 | Better than wiki **and** in-game | Comparison (wording TBD) |

Full study write-up: [`sus-user-study-results.md`](sus-user-study-results.md)

---

## Appendix Deck — Discussion (5 min)

Flip when the professor asks for depth:

| Slide | Topic | Rubric |
|-------|-------|--------|
| A1 | SMART goals full table | D1 |
| A2 | Competitor comparison (3 examples + limitations) | D2 |
| A3 | User flow + SUS task protocol | D3 |
| A4 | GitHub Projects screenshot + MoSCoW | D4 |
| A5 | Data lineage, legal, EDA stats (51 IDs, 12 sinners) | D5 |
| A6 | MWE code snippets (NER, embed, generate) | D6 |
| A7 | Pipeline hand-off table (wikitext → MD → JSON → guide JSON → UI) | D7 |
| A8 | Full eval: baselines, ablation, error categories, efficiency, SUS table | D8 |
| A9 | Optimization table + monitoring (`requests.jsonl`) | D9 |
| A10 | Failure post-mortem (below) | D10 |
| A11 | Lessons learned matrix (below) | D10 |

### Anticipated discussion topics

1. **Why no vector DB?** — Identity data is structured per wiki page; full JSON + domain primer fits context. Chunking breaks skill tables.
2. **How do you prevent hallucinations?** — Template generation constrained to parsed `raw_markdown` / JSON; no invented skill names in tests.
3. **Evaluation rigor?** — 50-ID held-out references, ROUGE-L + naive/ablation baselines, 7-participant SUS (90.4), 100% task success.
4. **Why does ablation ≈ full on ROUGE-L?** — Synergy output is mostly `team_suggestions`; core/playstyle driven by skill_parser.
5. **Non-players?** — P3/P4/P5 completed tasks; P4 needed reading help; LC terminology remains a ceiling without game context.

---

## Persona (D10)

**Name:** Alex — weekly Limbus player, builds teams for Mirror Dungeon.

**Before:** Spends 20+ minutes reading wiki skill tables; still unsure which teammate passive actually combos.

**After:** Opens Auto Guides, picks identity, reads Core Idea + one team suggestion in **under 2 minutes** (user study mean **~2.9 min** for all three tasks).

**Elevator pitch:** "Limbus Company Auto Guides turns dense wiki pages into consistent, grounded identity guides with explainable team synergy suggestions."

---

## Failure Post-Mortem (D10)

### Primary failure — generic template guides

| Field | Content |
|-------|---------|
| **What failed** | Early guides repeated mechanic keywords ("focused on Bleed, Coin Power, Base Power") for every identity — no skill names, no rotation logic. |
| **When discovered** | Mid-pipeline development, before archetype work |
| **Root cause** | `generation.py` ranked mechanics by frequency counts, not parsed skill/passive text. |
| **Impact on metrics** | Naive baseline ROUGE-L **0.109**; guides unusable for play decisions. |
| **Pivot** | Built `skill_parser.py`, `archetypes.py`, domain-primer rules; full pipeline **0.175** (+0.066). |

### Secondary failure — wiki HTML scraping (early)

| Field | Content |
|-------|---------|
| **What failed** | Fragile HTML selectors on wiki.gg layout changes. |
| **When discovered** | Initial ingestion sprint |
| **Root cause** | Presentation HTML ≠ structured content. |
| **Impact** | Slowed batch ingest; risk of parse drift. |
| **Pivot** | MediaWiki **wikitext** API + `docs/parsed-ids/` gold markdown; `wiki_parser.py` on stable templates. |

---

## Lessons Learned Matrix (D10)

| | Expected | Surprising |
|---|----------|------------|
| **Technical** | Rule-based NER works on game vocabulary (`status-effects.md`). | ROUGE-L insensitive to synergy — ablation 0.176 vs full 0.175; teammate quality needs separate review. |
| **Technical** | Embedding similarity clusters Bleed/Poise archetypes. | **Archetype tips** (stack ramp, retreat, Heishou backups) mattered more than embedding tweaks for guide quality. |
| **Procedural** | Need eval references early for meaningful ROUGE-L. | **10-minute format** forces headline metrics on main deck; full tables live in appendix. |
| **Procedural** | SUS recruitment is the bottleneck. | **7 participants in ~3 min each** — tasks were almost too easy; still valuable quotes and UI feedback. |

**Most valuable lesson:** **Structured-first** (parse wiki → JSON → template) beats chunk-and-embed RAG for tabular skill data — and keeps the dashboard instant with offline generation.

**User-study lesson:** Ship feedback during the study (colour coding, linked teammates, tab behaviour) — participants noticed and improved SUS sentiment.

---

## Optimization summary (D9 — for slide 7 / appendix A9)

| Change | Before | After | Verdict |
|--------|--------|-------|---------|
| Skill-aware template vs naive | ROUGE-L 0.109 | 0.175 | **+0.066** — primary win |
| Remove synergy (ablation) | 0.175 | 0.176 | Neutral on ROUGE; synergy is for teammates |
| Test set 29 → 50 IDs | 0.174 | 0.175 | Stable at scale |
| Archetype-specific playstyle tips | Generic "heavy chain" / deployment fluff | Kit-specific ramp + game-accurate wording | Qualitative; banned in tests |
| SUS-driven UI (colour, links, tabs) | — | Shipped during study | Usability; P3/P5/P7 requests |
| MiniLM → bge-small-en-v1.5 | — | — | **Not run** (deferred post-presentation) |

**Monitoring:** `data/logs/requests.jsonl` — timestamp, slug, latency_ms, generator. Regression: `pytest tests/test_pipeline.py`.

---

## Pre-presentation checklist (Jul 3)

### Must complete before presenting

- [ ] Slide deck exported (main + appendix PDF)
- [ ] `docs/assets/architecture.png` in deck (slide 3)
- [ ] `docs/assets/demo-backup.mp4` on laptop (if live demo fails)
- [ ] Timed rehearsal — **10:00** total once end-to-end
- [ ] Dashboard URL opens: [limbus-company-nlp-guides.streamlit.app](https://limbus-company-nlp-guides.streamlit.app/)
- [ ] Cold start: `pytest tests/ -q` passes
- [ ] Repo URL submitted to professor

### Demo day

- [ ] Browser tab pre-loaded: Faust → Ring Apprentice Faust
- [ ] Disable notifications; close unrelated tabs
- [ ] Have slide 6 numbers visible if demo runs long

### Optional polish

- [ ] GitHub Projects screenshot → `docs/assets/agile-board.png` (appendix A4)
- [ ] 2–3 Streamlit UI screenshots (appendix A3)
- [ ] Sync `data/evaluation_results.json` `sus_study` block with `sus-user-study-results.md`
- [ ] Final P7 presentation quote

---

## Rubric quick map

| Deliverable | Main deck slide | Appendix |
|-------------|-----------------|----------|
| D1 Pitch | 1 | A1 |
| D2 SOTA | 2 | A2 |
| D3 UX | 5 (demo) | A3 |
| D4 Agile | — | A4 |
| D5 Data | 3 | A5 |
| D6 NLP | 4 | A6 |
| D7 E2E | 3, 5 | A7 |
| D8 Eval | 6 | A8 |
| D9 Optimization | 7 | A9 |
| D10 Storytelling | 1, 8 | A10, A11 |
