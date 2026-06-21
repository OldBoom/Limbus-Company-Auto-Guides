# Deliverable 2 — State of the Art

This project builds an NLP pipeline that parses Limbus Company wiki.gg identity pages into structured data, then generates **easy-to-understand and consistent identity guides** (core concept, playstyle, and **team synergy suggestions**) in a browsable web dashboard.

## 1) Scout the web for similar products/prototypes

This project combines (a) wiki/game-data ingestion, (b) NLP extraction + similarity/synergy analysis, and (c) grounded guide generation + dashboard UI. Similar prototypes exist in adjacent spaces:

- **RAG game-wiki chatbots / assistants** (scrape wiki → vector search → LLM answers)
- **Team builders / recommenders** (compute synergy scores → recommend team comps → explain)

---

## 2) Picture the landscape

### 2.1 Which products/prototypes already exist? (2–3 examples)

#### Example A — RAG wiki chatbot (Baldur’s Gate 3)

- **Project**: `BG3Chat` (GitHub: `SimonB97/BG3Chat`)
- **What it does**: Scrapes `bg3.wiki`, builds a RAG knowledge base, serves a Streamlit UI that answers questions about the game.

#### Example B — Multi-game in-game wiki assistant overlay

- **Project**: `GameWiki` (GitHub: `rimulu030/gamewiki`)
- **What it does**: An in-game assistant overlay for Windows. Uses RAG (Gemini-based) to provide real-time wiki Q&A while playing (multiple supported games).

#### Example C — Team recommendation + explanation (Genshin Impact)

- **Project**: `genshin-team-builder` (GitHub: `syeet06/genshin-team-builder`)
- **What it does**: Scores candidate teams based on elemental reaction/resonance rules and then uses an LLM to generate human-readable explanations for recommended teams.

### 2.2 Limitations / why they don’t fit this use case

#### RAG chatbots (BG3Chat, GameWiki, Soulsborne-RAG)

- **Q&A, not per-identity guides**: They answer questions but do not consistently produce a fixed guide schema per character/identity (Core Idea / Playstyle / Team Suggestions).
- **Weaker grounding**: Many RAG chatbots still hallucinate or miss details.
- **No synergy-first output**: They do not compute synergy recommendations across a roster (embedding similarity + passive/keyword rules).

#### Team builders (Genshin team optimizers/builders)

- **Different mechanics**: They exploit clear reaction math/role constraints; Limbus has status stacks, coin mechanics, multi-state identities, and support passives that require different extraction and reasoning.
- **Not wiki-grounded generation**: Some tools assume curated databases; they don’t solve the “parse wiki.gg pages into structured identity data” problem.

---

## 3) Reverse engineering

### 3.1 Common tech stacks used by others (methods/tools)

Across the projects above, a recurring architecture appears:

- **Ingestion**
  - Scraping: `requests` + HTML parsing (BeautifulSoup / Cheerio)
  - Optional: wiki page indexing via “All pages” endpoints / sitemaps
- **Knowledge representation**
  - Raw documents + chunked passages
  - Structured JSON schemas (when available) for deterministic downstream use
- **Retrieval / similarity**
  - Embeddings (sentence-transformers / provider embeddings)
  - Vector store (FAISS / Chroma / other lightweight local stores)
  - Cosine similarity + top-k retrieval
- **Generation**
  - LLM prompting on retrieved context (RAG)
  - Sometimes a 2-stage pattern: “extract facts” → “write final answer”
- **UI**
  - Streamlit or Gradio for fast prototypes

### 3.2 Which parts can be reused for this project?

Reusable patterns for Limbus Company Auto Guides:

- **RAG scaffolding**: chunking + embedding + top-k retrieval → prompt (from RAG chatbots).
- **Researcher→Actor pattern**: extract verified facts first, then generate prose strictly from those facts (minimizes hallucination).
- **Synergy scoring + explanation**: compute a shortlist (rules + similarity), then let the LLM explain the recommendation (from Genshin team builders).
- **Streamlit prototype UI**: fast browse/search UI for a demo (from BG3Chat).

---

## 4) Your delta / contribution

This project’s contribution is a **guide generator** (not a chatbot) that is **wiki-grounded** and produces a **fixed per-identity output schema** with synergy reasoning.

Key differences:

- **Structured-first pipeline**: scrape wiki.gg → normalize into a consistent identity markdown/JSON schema (`docs/301-wiki-identity-parsing.mdc`, `docs/parsed-ids/`), then run NLP on that structure.
- **Hybrid recommendation**: team suggestions come from both
  - embedding similarity / clustering (archetypes), and
  - explicit synergy rules (support passives + mechanic triggers)
- **Hallucination control**: generated text must be constrained to mechanics present in the structured identity input (RAG grounding + optional post-check).
- **Dashboard UX**: users browse by character → identity → see Core Idea / Playstyle / Team Suggestions (predictable output, not free-form Q&A).
