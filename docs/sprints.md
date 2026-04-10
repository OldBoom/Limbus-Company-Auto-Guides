# Sprint Plan

## Overview

12 weekly sprints (Mar 27 – Jul 03) aligned with course milestones. Each sprint maps academic deliverables to concrete project tasks for the Limbus Company Auto Guides NLP pipeline.

**Current Sprint:** S2 (Apr 10)

---

## S1 — Introduction & NLP Landscape (Mar 27)

**Focus:** Project ideation, NLP technique survey.

- [x] Identify project domain (Limbus Company identity guides)
- [x] Survey applicable NLP techniques (NER, TF-IDF, embeddings, RAG, LLM prompting)
- [x] Draft initial project concept

---

## S2 — Problem Definition & Relevance (Apr 10)

**Focus:** Formalize the problem statement, define scope and deliverables.

- [x] Write project specification (`docs/project-specification.md`)
- [x] Define architecture (Data Ingestion → NLP Pipeline → Web Dashboard)
- [x] Document identity data format (`docs/Ring_Apprentice_Faust.md` as reference)
- [ ] Set up GitHub repository (README, .gitignore, initial structure)
- [ ] Create sprint plan (this document)

---

## S3 — State of the Art (Apr 17)

**Focus:** Research existing approaches, benchmark tools.

- [ ] Survey game-wiki NLP extraction approaches
- [ ] Evaluate NER frameworks (spaCy custom NER vs. rule-based)
- [ ] Compare embedding models (sentence-transformers variants)
- [ ] Compare LLM options (OpenAI API vs. local HuggingFace models)
- [ ] Document SOTA findings in `docs/sota.md`

---

## S4 — UX Design (Apr 24)

**Focus:** Design the web dashboard user experience.

- [ ] Define user flows (character select → identity list → guide view)
- [ ] Wireframe dashboard views (character selector, identity detail, compare view)
- [ ] Choose frontend framework (Streamlit vs. Gradio vs. Flask)
- [ ] Define guide output format (Core Idea / Playstyle / Team Suggestions)
- [ ] Document UX decisions in `docs/ux-design.md`

---

## S5 — Agile Workflow Planning (May 08)

**Focus:** Finalize development workflow, tooling, CI.

- [ ] Set up Python project structure (`src/`, `data/`, `tests/`)
- [ ] Configure dependency management (`requirements.txt` or `pyproject.toml`)
- [ ] Set up linting/formatting (ruff, black)
- [ ] Define branching strategy and PR workflow
- [ ] Create GitHub Issues for remaining modules

---

## S6 — Data Strategy (May 15)

**Focus:** Implement Module 1 — Data Ingestion.

- [ ] Build wiki.gg scraper (BeautifulSoup + requests)
- [ ] Extract per-identity data: base stats, skills, passives, support passives, sin affinities
- [ ] Design structured JSON schema for identity data
- [ ] Scrape minimum 20 identities across all 12 characters
- [ ] Store output in `data/identities/` as JSON
- [ ] Validate scraped data against manual reference (`Ring_Apprentice_Faust.md`)

---

## S7 — NLP Modeling — Isolated (May 22)

**Focus:** Implement Module 2 — NLP Processing (Tasks A & B).

- [ ] **Task A — Mechanic Extraction:** Build NER / rule-based tagger for game mechanics (Bleed, Burn, Tremor, etc.)
- [ ] **Task A — Keyword Extraction:** Implement TF-IDF or RAKE for dominant mechanic identification per identity
- [ ] **Task A — Output:** Generate per-identity mechanic profiles (primary, secondary, conditional triggers)
- [ ] **Task B — Similarity:** Compute identity similarity via TF-IDF vectors or sentence embeddings
- [ ] **Task B — Clustering:** Cluster identities by mechanic archetype (Bleed team, Burn team, etc.)
- [ ] **Task B — Synergy Detection:** Identify synergy pairs (support passives ↔ mechanic scaling)

---

## S8 — End-to-End System Architecture (Jun 05)

**Focus:** Implement Module 2 Task C + Module 3, connect all modules.

- [ ] **Task C — Text Generation:** Build LLM prompting pipeline with structured context (mechanic profiles + synergy data)
- [ ] **Task C — RAG:** Feed identity JSON as retrieval context for grounded generation
- [ ] **Task C — Output:** Generate Core Idea, Playstyle Guide, Team Suggestions per identity
- [ ] Build web dashboard (character selector → identity detail page)
- [ ] Serve pre-generated guide JSON to dashboard
- [ ] End-to-end pipeline test: scrape → extract → generate → display

---

## S9 — Evaluation & Quality (Jun 12)

**Focus:** Evaluate generated guides, measure quality.

- [ ] Manually write reference guides for 5–10 identities (validation subset)
- [ ] Compute BLEU / ROUGE scores against reference guides
- [ ] Design human evaluation rubric (factual accuracy, usefulness, readability)
- [ ] Run human evaluation on generated guides
- [ ] Identify failure modes (hallucinated mechanics, missing synergies)
- [ ] Document evaluation results in `docs/evaluation.md`

---

## S10 — Optimizing Your System (Jun 19)

**Focus:** Improve pipeline quality based on evaluation.

- [ ] Refine NER rules for missed/incorrect mechanic tags
- [ ] Tune embedding model or similarity thresholds for better synergy detection
- [ ] Iterate on LLM prompts to reduce hallucinations and improve guide quality
- [ ] Optimize scraper for full 172-identity coverage
- [ ] Performance profiling and optimization

---

## S11 — Reflection & Storytelling (Jun 26)

**Focus:** Prepare documentation and narrative.

- [ ] Write project report (methodology, results, lessons learned)
- [ ] Prepare demo script
- [ ] Record demo video (optional)
- [ ] Clean up repository, finalize README
- [ ] Ensure all docs are up to date

---

## S12 — Final Presentation (Jul 03)

**Focus:** Present the completed project.

- [ ] Deliver class presentation / live demo
- [ ] Submit source code repository
- [ ] Submit evaluation report
- [ ] Submit deployable web dashboard
