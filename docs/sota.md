# State of the Art — NLP Tools for Game-Wiki Guide Generation

Survey and evaluation of NLP techniques and tools applicable to the Limbus Company Auto Guides pipeline. Each section provides a short narrative, a comparison table, and a verdict.

**Evaluation data:** 3 parsed identity examples in `docs/parsed-ids/` — Ring Apprentice Faust (complex, multi-state, Bleed + Corpus Ingredient), Blade Lineage Salsu Yi Sang (simple, Poise-focused), and Ring Pointillist Student Yi Sang (Bleed + multi-status randomizer).

**PoC notebooks:** `notebooks/ner_evaluation.ipynb`, `notebooks/embedding_evaluation.ipynb`, `notebooks/llm_evaluation.ipynb`

---

## 1. Game-Wiki NLP Extraction Approaches

Extracting structured data from game wikis is a well-explored problem. The dominant patterns fall into three categories: HTML table/infobox parsing, MediaWiki template extraction, and LLM-assisted extraction.

For Limbus Company specifically, a few community projects exist:

- **meatpnppet/limbus_data_analysis** (JS) — builds datasets of sinner IDs, skills, and passives from game JSON files, generates wiki page content. Relies on datamined game files rather than wiki scraping.
- **SyxP/ObiterDicta.jl** (Julia) — REPL-based query tool for identity/skill/passive data, also sourced from game files.
- **GOLEM-lab/fandom-wiki** (Python) — general Fandom wiki scraper using WikiText parsing with relation extraction via NLP and LLM prompting.

wiki.gg pages for Limbus Company use standard HTML tables and tooltip blocks rather than MediaWiki templates, making BeautifulSoup-based parsing the most direct approach. The project's parsing conventions are documented in `docs/301-wiki-identity-parsing.mdc`.

| Approach | Pros | Cons | Applicable? |
|----------|------|------|-------------|
| HTML table parsing (BeautifulSoup) | Direct, no API dependency, works on wiki.gg | Fragile to layout changes | **Yes — primary approach** |
| MediaWiki API / WikiText parsing | Structured access to templates | wiki.gg doesn't expose rich templates for identity data | Partially |
| Game file datamining | Most accurate raw data | Requires reverse-engineering, legal concerns, no flavor text | No — out of scope |
| LLM-assisted extraction | Handles unstructured text well | Expensive, overkill for structured tables | No — tables are already structured |

**Verdict:** BeautifulSoup HTML parsing is the right tool. wiki.gg identity pages are well-structured with consistent table layouts. The parsing rule (`docs/301-wiki-identity-parsing.mdc`) already defines the extraction schema. No need for MediaWiki API or LLM-based extraction.

---

## 2. NER Framework Evaluation

Game mechanic extraction (tagging terms like "Bleed", "Corpus Ingredient", "[On Hit]") can be approached with either a trained statistical NER model or a rule-based system. For a controlled-vocabulary domain like Limbus Company, the vocabulary of mechanics is finite and well-defined.

**PoC notebook:** `notebooks/ner_evaluation.ipynb`

Two approaches were implemented and tested against a manually annotated gold standard for 3 identities:

- **Rule-based (regex + spaCy PhraseMatcher):** A dictionary of known mechanic terms is matched against identity text using spaCy's PhraseMatcher (case-insensitive). Regex patterns capture triggers (`[On Hit]`, `[On Use]`, etc.) and conditional expressions (`at X+ count`).
- **spaCy EntityRuler:** A pattern-based NER component that assigns typed entity labels (STATUS_EFFECT, STAT_MODIFIER, UNIQUE_MECHANIC) to matched spans. Functionally similar to PhraseMatcher but produces labeled entities compatible with spaCy's NER pipeline.

| Framework | Precision | Recall | Training data needed | Setup effort | Extensibility |
|-----------|-----------|--------|----------------------|--------------|---------------|
| Rule-based (PhraseMatcher + regex) | High | High | None — dictionary only | Low | Add terms to list |
| spaCy EntityRuler | High | High | None — pattern rules | Low | Add patterns |
| spaCy trained NER (statistical) | Medium-High | Medium | 50-100+ annotated examples | High | Retrain on new data |

**Verdict:** Rule-based extraction (PhraseMatcher + regex) or EntityRuler is the recommended approach. The game mechanic vocabulary is controlled and finite — statistical NER offers no advantage and requires significant annotation effort. EntityRuler is preferred over raw PhraseMatcher because it produces typed entity labels, which simplifies downstream processing.

---

## 3. Embedding Model Comparison

Identity similarity computation (for synergy detection and archetype clustering) requires encoding skill/passive descriptions into vector space. Three lightweight, free, locally-runnable models were compared.

**PoC notebook:** `notebooks/embedding_evaluation.ipynb`

Each model encodes the extracted description text from all 3 test identities. Cosine similarity is computed pairwise. The key test: do two Bleed-focused identities (Ring Apprentice Faust, Ring Pointillist Student Yi Sang) score higher similarity than a Bleed vs. Poise pair (Ring Apprentice Faust vs. Blade Lineage Salsu Yi Sang)?

| Model | Params | Dim | MTEB Score | Throughput (req/s) | Retrieval-optimized |
|-------|--------|-----|------------|--------------------|--------------------|
| `all-MiniLM-L6-v2` | 22M | 384 | 56.3 | ~220 | No |
| `all-mpnet-base-v2` | 110M | 768 | — | ~50 | No |
| `bge-small-en-v1.5` | 33M | 384 | — | ~132 | Yes |

**Verdict:** Start with `all-MiniLM-L6-v2` for development speed (fastest, smallest, good enough for prototype). If similarity quality is insufficient at 172 identities, upgrade to `bge-small-en-v1.5` (better retrieval quality, still fast) or `all-mpnet-base-v2` (highest semantic quality, 5x slower). All three are free, local, and require no API key.

---

## 4. LLM Options for Guide Generation

The text generation stage (Task C) requires an LLM to produce natural-language guide sections from structured mechanic profiles and synergy data. The project prioritizes free/local models.

**PoC notebook:** `notebooks/llm_evaluation.ipynb`

Each model receives the full structured identity markdown as context and is prompted to generate Core Idea + Playstyle Guide sections. A grounding check verifies that referenced mechanics exist in the source data.

| Model | Params | VRAM | License | Quality | Grounding |
|-------|--------|------|---------|---------|-----------|
| Mistral 7B (Ollama) | 7B | ~5 GB | Apache 2.0 | Good | Good with RAG context |
| Llama 3 8B (Ollama) | 8B | ~5 GB | Llama Community | Good+ | Good with RAG context |
| Phi-4 (Ollama) | 14B | ~9 GB | MIT | Very good | Very good with RAG context |
| Mistral 7B (HF Inference) | 7B | — (hosted) | Apache 2.0 | Good | Good |
| flan-t5-xl (HF Inference) | 3B | — (hosted) | Apache 2.0 | Moderate | Moderate — short context |

**Inference options:**

| Platform | Pros | Cons |
|----------|------|------|
| Ollama (local) | Free, offline, fast on GPU, no rate limits | Requires local GPU (5-9 GB VRAM) |
| HuggingFace Inference API | No local GPU needed, easy setup | Rate-limited on free tier, variable latency |

**Verdict:** **Ollama with Mistral 7B** is the recommended primary option — free, fast, Apache 2.0 licensed, offline-capable, and produces good quality output when structured identity data is provided as context (RAG approach). **Phi-4** is the upgrade path if quality is insufficient (better reasoning, MIT license, but needs more VRAM). HuggingFace Inference API serves as a fallback for environments without a local GPU.

RAG grounding is critical: without feeding structured identity data as context, all models hallucinate game mechanics. The pipeline must always provide the identity JSON/markdown as retrieval context.

---

## Summary of Recommendations

| Pipeline Stage | Recommended Tool | Alternative |
|----------------|-----------------|-------------|
| Data Ingestion (scraping) | BeautifulSoup + requests | — |
| Mechanic Extraction (NER) | spaCy EntityRuler (pattern-based) | PhraseMatcher + regex |
| Keyword Extraction | TF-IDF (scikit-learn) | RAKE |
| Identity Similarity | `all-MiniLM-L6-v2` (sentence-transformers) | `bge-small-en-v1.5` |
| Clustering | k-means (scikit-learn) | — |
| Guide Generation (LLM) | Ollama + Mistral 7B | Phi-4, HF Inference API |
| RAG Context | Structured identity markdown/JSON | — |
| Web Dashboard | Streamlit | Gradio |
