# Final Presentation Outline

**Format:** 10-minute presentation + 5-minute professor discussion (Jul 3, 2026)

**Main deck:** 10–12 slides, ~600 seconds total. **Appendix:** detail for discussion — not timed.

---

## Main Deck — Slide Script

| # | Slide | Seconds | Narration notes | Rubric | Repo evidence |
|---|-------|---------|-----------------|--------|---------------|
| 1 | Title + hook | 30 | Persona: Limbus player prepping for a fight. Problem: wiki pages are dense and misleading. | D1, D10 | `deliverable-1-prototype-pitch.md` |
| 2 | Delta vs existing tools | 45 | Not a chatbot — fixed guide schema per identity with synergy reasoning. vs BG3Chat, GameWiki, Genshin team builder. | D2 | `deliverable-2-state-of-the-art.md` |
| 3 | Architecture | 60 | Scrape/parse → JSON → NER + embeddings + synergy → RAG generation → Streamlit. Structured context, no vector DB. | D5, D7 | `project-specification.md` diagram |
| 4 | NLP stack | 60 | EntityRuler for mechanics, MiniLM for similarity, template/Ollama for guides. Show 1 input→output pair. | D6 | `poc_evaluation_results.json`, `nlp/` |
| 5 | **Live demo** | 210 | Select Faust → Ring Apprentice → read Core Idea, Playstyle, Team Suggestions. Pre-generated JSON. | D3, D7 | `streamlit run src/limbus_guides/dashboard/app.py` |
| 6 | Evaluation headline | 60 | ROUGE-L mean, mechanic F1, SUS score (when available). | D8 | `evaluation.md` |
| 7 | Key optimization | 45 | Example: synergy rules improved teammate relevance vs embedding-only. | D9 | `monitoring/logger.py` |
| 8 | Lesson learned | 30 | e.g. RAG grounding eliminated hallucinations vs raw LLM. | D10 | Post-mortem appendix |
| 9 | Summary | 30 | Recap: wiki-grounded guides for 50 identities, open pipeline. | — | GitHub repo |
| — | Buffer | 30 | — | — | — |

**Total:** ~600s (10 min)

### Demo script (slide 5)

1. Open dashboard — character sidebar visible (5s)
2. Select **Faust** → **Ring Apprentice Faust** (10s)
3. Read **Core Idea** aloud — mention Bleed + Corpus Ingredient (30s)
4. Scroll **Playstyle** — Iron Maiden → Flow State transition (45s)
5. **Team suggestions** — explain one synergy rule hit (40s)
6. Optional: show mechanic profile expander (20s)

**Latency risk:** Dashboard reads JSON — no LLM wait. **Backup:** 30s screen recording in `docs/demo-backup.mp4`.

**Narration during waits:** "Guides are pre-generated offline so the UI stays instant."

---

## Appendix Deck — Discussion (5 min)

Flip to these when the professor asks for depth:

| Slide | Topic | Rubric |
|-------|-------|--------|
| A1 | SMART goals full table | D1 |
| A2 | Competitor comparison (3 examples + limitations) | D2 |
| A3 | User flow diagram (character → identity → guide) | D3 |
| A4 | GitHub Projects screenshot + MoSCoW | D4 |
| A5 | Data lineage, legal, EDA stats | D5 |
| A6 | MWE code snippets (NER, embed, generate) | D6 |
| A7 | Pipeline hand-off table (format at each junction) | D7 |
| A8 | Full eval: baselines, ablation, error categories, efficiency table | D8 |
| A9 | Monitoring plan + prompt experiments | D9 |
| A10 | Failure post-mortem (5-field table) | D10 |
| A11 | Lessons learned 2×2 matrix | D10 |

### Anticipated discussion topics

1. **Why no vector DB?** — Identity data is structured per page; full JSON fits context window.
2. **How do you prevent hallucinations?** — Template/Ollama constrained to `raw_markdown`; grounding check in PoC.
3. **Evaluation rigor?** — 50-ID held-out test set with ROUGE-L + baselines; SUS study before Jul 3.

---

## Persona (D10)

**Name:** Alex — weekly Limbus player, builds teams for Mirror Dungeon.

**Before:** Spends 20+ minutes reading wiki skill tables; still unsure about synergies.

**After:** Opens Auto Guides, picks identity, gets Core Idea + teammates in under 2 minutes.

**Elevator pitch:** "Limbus Company Auto Guides turns dense wiki pages into consistent, grounded identity guides with team synergy suggestions."

---

## Failure Post-Mortem (template — fill before presentation)

| Field | Content |
|-------|---------|
| What failed | (e.g. wiki scraper fragility on first attempt) |
| When discovered | S6 |
| Root cause | HTML layout differs from parsed markdown reference |
| Impact on metrics | Delayed 20-identity coverage |
| Pivot | Use `docs/parsed-ids/` as gold reference; scraper as incremental add-on |

---

## Lessons Learned Matrix (template)

| | Expected | Surprising |
|---|----------|------------|
| **Technical** | Rule-based NER works on game vocabulary | Bleed identities cluster well even with MiniLM |
| **Procedural** | Sprint plan needs eval tasks early | 10-min format forces appendix for D8 detail |

**Most valuable lesson:** Structured-first RAG beats chunk-and-embed for wiki tables.
