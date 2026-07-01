# Sprint Plan — Final 5 Days (Jun 28 – Jul 3)

## Status as of Jul 1

**Presentation:** Jul 3, 2026 — 10-min presentation + 5-min professor discussion.

**What is fully built and working:**
- 50 parsed identities across all 12 sinners (`docs/parsed-ids/`)
- Full pipeline: markdown → mechanic extraction → synergy detection → smart guide generation
- Streamlit dashboard: character picker → identity → guide (50 guides in `data/guides/`)
- NER (spaCy EntityRuler + regex), sentence embeddings, rule-based synergy (incl. archetype rules)
- Domain-primer-grounded template generator (`src/limbus_guides/nlp/generation.py`, `skill_parser.py`)
- Evaluation on full 50-ID test set (`data/evaluation_results.json` — ROUGE-L 0.175 full / 0.109 naive)
- Request logger (`src/limbus_guides/monitoring/logger.py`)
- 25+ tests passing (`tests/test_pipeline.py`)

**What is missing for the presentation:**

| Deliverable | Gap |
|-------------|-----|
| D3 UX | No moodboard; no peer feedback note; no UI sketch/screenshot set |
| D4 Agile | No GitHub Projects board screenshot |
| D6 NLP | No "Method + Model + MWE" slide content written up |
| D7 E2E | No architecture diagram; no backup demo clip |
| D8 Evaluation | SUS user study not run (0 participants) |
| D9 Optimization | Embedding swap experiment not run; optimization backlog table incomplete |
| D10 Storytelling | Post-mortem + demo storyboard + slides not finalized |

---

## Day 1 — Sun Jun 29: Data, Eval Setup, Agile Evidence

**Goal:** Unblock D8 (evaluation) and close D4 (agile).

### D8 — Expand evaluation test set to ≥ 20 references

The biggest D8 blocker is having only 3 reference texts. You now have 29 parsed identities.

- [x] Write brief reference texts for 17 more identities in `data/evaluation/references/`
  - Format: 2–4 sentences, same style as the existing 3 — describe the mechanic focus and playstyle in plain terms
  - Suggested picks (diverse archetypes): `Liu_Assoc._South_Section_3_Yi_Sang`, `Blade_Lineage_Mentor_Meursault`, `Kurokumo_Clan_Captain_Ishmael`, `Seven_Assoc._South_Section_4_Faust`, `Tingtang_Gang_Gangleader_Hong_Lu`, `Firefist_Office_Survivor_Gregor`, `The_Barber_of_La_Manchaland_Outis`, `Devyat'_Assoc._North_Section_3_Sinclair` + 9 more
  - Each file: `data/evaluation/references/<slug>.txt`, 2–4 sentences
- [x] Run `python scripts/run_evaluation.py` → saves ROUGE-L scores to `data/evaluation_results.json`

### D4 — GitHub Projects board

- [ ] Create a GitHub Projects board (or Jira) with the 18 user stories from `docs/agile-backlog.md`
  - Add MoSCoW labels; mark completed stories as Done
  - Take a screenshot → save as `docs/assets/agile-board.png`
- [ ] Add acceptance criteria column to the `docs/agile-backlog.md` table for all Must stories (already partially there — verify each one is filled)

---

## Day 2 — Mon Jun 30: Run Evaluations, Baselines, Latency

**Goal:** Complete all quantitative D8 results.

### D8 — Baselines and metrics

- [x] **Naive baseline:** modify `run_evaluation.py` to also score a naive guide (TF-IDF keywords only, no skill data). Add `baseline_naive` column to `data/evaluation_results.json`
- [x] **Ablation baseline:** score the guide generator without synergy context injected. Add `baseline_ablation` column
- [x] Run both baselines over the 50-identity test set → produce 3-column ROUGE-L table (naive 0.109 / ablation 0.176 / full 0.175)
- [x] **Latency table:** time 10 pipeline runs, record mean + worst-case milliseconds per identity (mean 1,061 ms, worst 1,136 ms)
- [x] Document results in `docs/evaluation.md` — replace placeholder rows with real numbers

### D5 — Data Strategy doc

- [x] Add a brief `docs/data-strategy.md` (or expand `docs/evaluation.md`) covering:
  - Source: wiki.gg MediaWiki API (no scraping, structured wikitext)
  - Lineage: public wiki, academic use, no PII
  - Pre-processing: `wiki_parser.py` → markdown → `markdown_loader.py` → JSON
  - EDA stats: identity count (50), sinner count (12), avg skill count, mechanic frequency table
  - Run: `python -c "import json, pathlib; guides = [json.loads(p.read_text()) for p in pathlib.Path('data/guides').glob('*.json') if p.name != 'manifest.json']; print(len(guides))"` for quick stats

---

## Day 3 — Tue Jul 1: SUS Study + D9 Experiments

**Goal:** Get SUS data (the one thing that can't be generated) and run optimization experiments.

### D8 — SUS user study (recruit today, run tonight)

- [ ] Recruit 3–5 people (classmates, Limbus Discord, friends) — give them the dashboard URL or run it locally
- [ ] Define 3 tasks (already written in `docs/evaluation.md`):
  1. Find a guide for a specific character and identity
  2. Identify the identity's primary mechanic from the guide
  3. Name one suggested teammate and explain why
- [ ] Collect: SUS questionnaire (10 items, 1–5 scale), task success (Y/N), one quote per person
- [ ] Calculate SUS score: `(sum of adjusted scores) × 2.5` — aim for 70+
- [ ] Record results in `docs/evaluation.md` under SUS section

### D9 — Optimization experiments

Run 2 controlled experiments with measured delta on ROUGE-L:

- [ ] **Experiment 1 — Skill name prominence:** Current guides put skill names in bold. Test: move skill name to the first word of the sentence (e.g. "Striker's Stance builds Poise Count..."). Re-run eval → record delta
- [ ] **Experiment 2 — Synergy specificity:** Current: synergy reason references passive name. Test: also add the scaling condition ("scales off Bleed potency → S2 Final Power scales off 6+ Bleed"). Re-run eval → record delta
- [ ] Fill in the optimization experiment table in `docs/evaluation.md`
- [ ] **Optimization backlog table** (D9 component 1): 5–8 items, Impact/Effort/Priority/Acceptance Criterion — write in `docs/agile-backlog.md` or a new `docs/optimization-backlog.md`

---

## Day 4 — Wed Jul 2: Architecture Diagram + Slides + Storytelling

**Goal:** All presentation content exists in rough form.

### D7 — Architecture diagram

- [ ] Draw a block diagram (draw.io, Excalidraw, or PowerPoint SmartArt) showing:
  - **Build:** wiki.gg → MediaWiki API → `wiki_parser.py` → `docs/parsed-ids/*.md` → `markdown_loader.py` → `data/identities/*.json`
  - **Run:** `mechanics.py` → `similarity.py` / `synergy.py` → `generation.py` (template + optional Ollama) → `data/guides/*.json`
  - **Deploy:** `dashboard/app.py` (Streamlit) → browser
  - Data formats at each hand-off: wikitext → structured MD → JSON → guide JSON → rendered UI
- [ ] Export as `docs/assets/architecture.png`
- [ ] Record a 30–60 second backup demo clip (screen recording: open dashboard → select Yi Sang → pick Blade Lineage Salsu → show guide) → save as `docs/assets/demo-backup.mp4`

### D3 — UX evidence

- [ ] Collect 3–4 moodboard screenshots (existing game wikis or guide sites with good UX: Fextralife, Genshin wiki, Slay the Spire card DB)
- [ ] Capture 2–3 screenshots of your actual Streamlit UI
- [ ] Write a one-paragraph note on any peer feedback received (even informal)

### D10 — Storytelling content (write these sections for the slides)

- [ ] **Persona card:** one named player (e.g. "Mia, 22, casual Limbus player, owns 30+ identities, can't remember which ones combo")
- [ ] **Before/After scenario:** Before: opens wiki, reads 3 pages, still unsure who to pair. After: opens guide → reads playstyle → sees team suggestion with reason.
- [ ] **Failure post-mortem:** Biggest technical failure = generic template guide ("focused on Bleed, Coin Power, Base Power" for every identity). Root cause: generation.py used mechanic frequency counts, not skill data. Pivot: built `skill_parser.py`. Measure: guide now names real skill names and conditions.
- [ ] **Lessons learned matrix:** 2×2 (Technical / Procedural × Expected / Surprising) — 2 entries per cell
- [ ] **Demo storyboard table:** Step / Screen State / Narration Script / Latency Risk / Backup → minimum 6 steps covering full demo arc

### Slides — first draft

Build a 10–12 slide deck using the outline in `docs/final-presentation-outline.md`:

- [ ] Slide 1: Hook — persona + problem
- [ ] Slide 2: SMART goals + scope
- [ ] Slide 3: SOTA delta — what exists vs what we built
- [ ] Slide 4: Architecture diagram (use `docs/assets/architecture.png`)
- [ ] Slide 5: NLP stack — method/model table + MWE code snippet
- [ ] Slide 6: Guide output example — before (generic) vs after (smart template)
- [ ] Slide 7: Evaluation results — ROUGE-L table (naive / ablation / full)
- [ ] Slide 8: SUS score + top 3 usability findings + 1 quote
- [ ] Slide 9: D9 optimization — before/after experiment table
- [ ] Slide 10: Post-mortem + lessons learned
- [ ] Slide 11: Demo intro + live hand-off
- [ ] Appendix: D4 agile board, D5 EDA, D6 MWE, D8 full tables, monitoring plan

---

## Day 5 — Thu Jul 3: Rehearsal + Final Checks

**Goal:** 10-minute timed run-through, repo submitted.

- [ ] Full timed rehearsal — 10 minutes exactly (set a timer)
  - Slides: ~6 min
  - Live demo: ~3 min (follow demo storyboard from D10)
  - Buffer: 1 min
- [ ] Verify dashboard runs cleanly from cold start: `python scripts/run_pipeline.py` → `streamlit run src/limbus_guides/dashboard/app.py`
- [ ] Check that backup demo clip is accessible if live demo fails
- [ ] Final repo state:
  - All guide files regenerated and committed
  - `docs/` has architecture diagram, evaluation results, agile screenshot
  - `README.md` accurate (setup instructions work)
  - Tests pass: `python -m pytest tests/ -q`
- [ ] Submit repository URL to professor

---

## Rubric Coverage Checklist

| Deliverable | Status | Evidence location |
|-------------|--------|-------------------|
| D1 — Prototype Pitch | ✅ done | `docs/lecture-deliverables/deliverable-1-prototype-pitch.md` |
| D2 — State of the Art | ✅ done | `docs/lecture-deliverables/deliverable-2-state-of-the-art.md`, `docs/sota.md` |
| D3 — UX | 🔲 Day 4 | Moodboard screenshots + Streamlit UI screenshots + peer note |
| D4 — Agile | 🔲 Day 1 | GitHub Projects screenshot + `docs/agile-backlog.md` |
| D5 — Data Strategy | ✅ done | `docs/data-strategy.md` (50-ID EDA + lineage) |
| D6 — NLP Modeling | ✅ built, 🔲 slide content | `docs/sota.md` + method/model table for slides |
| D7 — E2E System | ✅ built, 🔲 artifacts | Architecture diagram + backup demo clip |
| D8 — Evaluation | 🔲 partial | 50 references + ROUGE-L + baselines + latency ✅; SUS study pending |
| D9 — Optimization | 🔲 Days 3–4 | 2 experiments + optimization backlog + monitoring plan |
| D10 — Storytelling | 🔲 Day 4 | Persona + post-mortem + demo storyboard + lessons matrix |

---

## Priority order if time runs short

1. **D8 eval references + ROUGE-L** — a quantitative score is required; without it D8 is empty
2. **D7 architecture diagram** — professors always ask to see the system structure
3. **SUS study** — even 3 users is enough; recruit aggressively on Day 3
4. **Slides** — needed to present; every other artifact feeds into them
5. **D10 storyboard** — prevents dead air during demo; scripting saves you
6. **D9 experiments** — can be minimal (2 runs with delta recorded)
7. **D3/D4/D5** — supporting evidence; professors may not drill these if the above are strong
