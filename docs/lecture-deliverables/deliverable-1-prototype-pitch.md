# Deliverable 1 — Prototype Pitch

## 1) One-sentence problem statement

Limbus Company players lack consistent, quickly accessible identity guides; manually reading extreamly long wiki pages is slow and most of the time leads to missunderstanding of core mechanics and characters.

## 2) User description

Primary users are Limbus Company players who want to understand what an identity does, how to play it, and which other identities synergize, without decoding what developers wrote in a character kit.

## 3) Why this problem is relevant to the user

- Players need identity understanding for team-building and encounter preparation.
- Wiki pages are information-dense; important mechanics are missleading and increadibly hard to understand.
- Synergy discovery is a thing that many players want and feel curious about.

## 4) Sketch of how to solve the problem (input → NLP task → output)

- **Input**: wiki.gg identity pages (HTML) → extracted structured identity JSON (stats, skills, passives, support passives, sin affinities, referenced mechanics).
- **NLP tasks**:
  - Mechanic extraction (rule-based tagging and/or NER) for mechanics and conditions (e.g., Bleed, Burn, Charge, “on hit”, “at X+ stacks”).
  - Keyword extraction (TF-IDF/RAKE) to identify dominant mechanics per identity.
  - Similarity + synergy analysis (embeddings + clustering + passive-rule matching) to recommend teammates with reasons.
  - LLM-based grounded generation (RAG over extracted JSON) to produce guide text without hallucinating mechanics.
- **Output**:
  - Per-identity guide JSON containing:
    - Core concept summary (2–3 sentences)
    - Playstyle guide (short paragraph)
    - Team suggestions (3–5 bullets with one-line rationale each)
  - Web dashboard to browse by character → identity → view generated guides.

## 5) SMART goals (including sub-goals and non-goals)

### Main SMART goal

By **July 3rd, 2026**, deliver a locally deployable web dashboard that generates and displays **factually grounded** identity guides by scraping wiki.gg, extracting mechanics and synergies, and producing three guide sections per identity (core concept, playstyle, team suggestions), covering **at least 20 identities across all 12 characters**.

### Specific (S)

- Implement an end-to-end pipeline: scrape → structured JSON → mechanic profile → synergy suggestions → grounded guide text → dashboard display.

### Measurable (M)

- **Coverage**: ≥ 20 identities, with ≥ 1 identity per character.
- **Output completeness**: each identity has all 3 sections (core concept, playstyle, team suggestions).
- **Grounding**: 0 hallucinated mechanics in an evaluated subset of 5–10 identities (manual checklist vs wiki extraction).
- **Dashboard performance**: identity page load ≤ 2 seconds locally using pre-generated guide JSON.

### Achievable (A)

- Use standard Python tooling (requests/BeautifulSoup, scikit-learn, sentence-transformers, spaCy optional) and an LLM API or a local HF model with RAG from extracted JSON.

### Relevant (R)

- Demonstrates core NLP competencies: information extraction, keywording, embeddings, clustering, and grounded generation with evaluation.

### Time-bound (T)

- MVP end-to-end demo by **Jun 05, 2026** (architecture milestone).
- Evaluation report completed by **Jun 12, 2026** (evaluation milestone).
- Final polished demo and documentation by **Jul 03, 2026** (final presentation).

### Sub-goals

- Scraper reliably extracts: stats, skills (coins/effects/conditions), passives, support passives, sin affinities.
- Mechanic extractor correctly tags core status effects and triggers (e.g., Bleed/Burn/Charge and common conditional phrasing).
- Synergy module provides teammate names plus a reason grounded in extracted mechanics/support passives.
- Generate guides offline into JSON; dashboard is read-only and displays pre-generated outputs.

### Non-goals

- No mobile app deployment (local web dashboard only).
- No full-scale production reliability/security requirements (academic prototype).
- No model fine-tuning or training from scratch (use prompting + retrieval; optional off-the-shelf embeddings).
- No guarantee of full 172-identity coverage for MVP (beyond the ≥ 20-identity requirement).

### Optional stretch goal

- Deploy the dashboard to **Streamlit Community Cloud** for a shareable demo, while keeping the primary requirement as local deploy.

