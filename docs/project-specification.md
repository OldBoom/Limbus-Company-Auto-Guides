---
name: NLP Project Specification
overview: Write a project specification document for a Limbus Company identity guide generator — an NLP system that parses wiki.gg pages and produces identity summaries, playstyle guides, and team suggestions, presented via a web dashboard.
---

## Project Goal

Build an NLP pipeline that ingests structured character identity data from Limbus Company wiki.gg pages and generates three outputs per identity:
1. Core concept summary (what the identity does, in natural language)
2. Playstyle guide (how to use the identity effectively)
3. Team composition suggestions (which identities synergize)

Results MUST be displayed on a web-based dashboard where users browse by character and identity.

---

## Domain Context

- **Game:** Limbus Company (Project Moon, 2023–present)
- **Characters (Sinners):** 12 playable characters
- **Identities:** 172 total; each character equips exactly one identity per team
- **Core mechanics:** Status effects (Bleed, Burn, Tremor, Rupture, Sinking, Poise, Charge), skill coins, offense/defense levels, passives, support passives, sin affinities
- **Data source:** [limbus-company.wiki.gg](https://limbus-company.wiki.gg)

---

## Architecture

```mermaid
flowchart LR
    subgraph dataIngestion [Data Ingestion]
        WikiScraper["Wiki Scraper"]
        StructuredStore["Structured JSON Store"]
    end

    subgraph nlpPipeline [NLP Pipeline]
        MechanicNER["Mechanic NER / Keyword Extraction"]
        SynergyAnalysis["Synergy Analysis via TF-IDF + Embeddings"]
        TextGen["Text Generation (LLM-based)"]
    end

    subgraph output [Output Layer]
        GuidesJSON["Guides JSON"]
        WebDashboard["Web Dashboard"]
    end

    WikiScraper --> StructuredStore
    StructuredStore --> MechanicNER
    MechanicNER --> SynergyAnalysis
    MechanicNER --> TextGen
    SynergyAnalysis --> TextGen
    TextGen --> GuidesJSON
    GuidesJSON --> WebDashboard
```

---

## Module Breakdown

### Module 1 — Data Ingestion

- Scrape identity pages from wiki.gg (HTML parsing via BeautifulSoup or similar)
- Extract per-identity: base stats, skills (coins, effects, conditions), passives, support passives, sin affinities, status effects referenced
- Store as structured JSON (one file per identity or single consolidated file)
- Reference format: `Ring_Apprentice_Faust.md` shows the target structure

### Module 2 — NLP Processing (Core of the Project)

Three NLP tasks, mixing traditional and LLM-based techniques:

**Task A: Mechanic Extraction (Traditional NLP)**
- Named Entity Recognition or rule-based extraction to tag game mechanics in skill/passive text (e.g., "Bleed", "Corpus Ingredient", "Unbreakable Coin", "Bind")
- Keyword extraction (TF-IDF or RAKE) to identify the dominant mechanics per identity
- Output: per-identity mechanic profile (primary mechanics, secondary mechanics, conditional triggers)

**Task B: Identity Similarity and Team Synergy (Traditional + Embeddings)**
- Compute identity similarity using TF-IDF vectors or sentence embeddings over skill/passive descriptions
- Cluster identities by mechanic archetype (Bleed team, Burn team, Charge team, etc.)
- Detect synergy pairs: identities whose support passives benefit another identity's mechanics (e.g., support passive inflicts Bleed -> pairs with identity that scales off Bleed)
- Output: per-identity list of suggested teammates with synergy reasoning

**Task C: Guide Text Generation (LLM-based)**
- Use extracted mechanic profiles + synergy data as context
- Prompt an LLM (or fine-tuned model) to generate:
  - **Core Idea** (~2-3 sentences): What this identity fundamentally does
  - **Playstyle Guide** (~1 short paragraph): Key decision points, skill priorities, state transitions
  - **Team Suggestions** (~3-5 bullet points): Recommended partners with one-line rationale
- RAG approach: feed structured identity data as retrieval context to improve generation accuracy
- Evaluate output against manually written guides for a validation subset

### Module 3 — Web Dashboard

- Framework: Streamlit, Gradio, or lightweight Flask app
- Views:
  - Character selector (12 characters) -> identity list for selected character
  - Identity detail page: core idea, playstyle guide, team suggestions
  - (Optional) Compare view: side-by-side identity comparison
- Data served from pre-generated JSON (guides generated offline, dashboard is read-only display)

---

## NLP Techniques Summary

| Technique | Category | Usage |
|-----------|----------|-------|
| HTML parsing + structured extraction | Preprocessing | Wiki page ingestion |
| Named Entity Recognition (custom entities) | Traditional NLP | Game mechanic tagging |
| TF-IDF / RAKE keyword extraction | Traditional NLP | Dominant mechanic identification |
| Sentence embeddings (e.g., sentence-transformers) | Embeddings | Identity similarity computation |
| Clustering (k-means or similar) | Traditional ML | Archetype grouping |
| LLM prompting with structured context | LLM-based | Guide text generation |
| RAG (Retrieval-Augmented Generation) | LLM-based | Grounding generation in wiki data |

---

## Scope Constraints

- Prototype MUST cover a minimum of 20 identities across all 12 characters (at least 1 per character) for demonstration
- Prototype SHOULD support all 172 identities if pipeline is automated
- Team suggestions MUST reference specific identity names, not generic advice
- Generated text MUST be factually grounded in wiki data (no hallucinated mechanics)

---

## Deliverables

1. Source code repository with documented pipeline
2. Web dashboard (deployable locally)
3. Evaluation report: compare generated guides against 5-10 manually written guides (BLEU/ROUGE scores or human evaluation rubric)
4. Class presentation / demo

---

## Tech Stack (Suggested)

- **Language:** Python
- **Scraping:** BeautifulSoup / requests
- **NLP:** spaCy (NER), scikit-learn (TF-IDF, clustering), sentence-transformers (embeddings)
- **LLM:** OpenAI API / local model via Hugging Face
- **Web:** Streamlit or Gradio
- **Data format:** JSON

