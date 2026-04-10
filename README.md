# Limbus Company Auto Guides

An NLP pipeline that scrapes [Limbus Company wiki.gg](https://limbus-company.wiki.gg) identity data and generates playable guide content — core concept summaries, playstyle guides, and team composition suggestions — displayed on a web dashboard.

## Architecture

```
Wiki Scraper → Structured JSON → NLP Pipeline → Guide JSON → Web Dashboard
```

**Data Ingestion** — Scrape identity pages, extract stats/skills/passives into structured JSON.

**NLP Pipeline** — Three stages:
1. **Mechanic Extraction** — NER + keyword extraction (TF-IDF / RAKE) to build per-identity mechanic profiles
2. **Synergy Analysis** — Sentence embeddings + clustering to detect team synergies
3. **Text Generation** — LLM prompting with RAG to produce natural-language guides

**Web Dashboard** — Browse by character → identity → read generated guide.

## Tech Stack

- **Language:** Python
- **Scraping:** BeautifulSoup, requests
- **NLP:** spaCy, scikit-learn, sentence-transformers
- **LLM:** OpenAI API / HuggingFace
- **Web:** Streamlit / Gradio
- **Data:** JSON

## Project Structure

```
docs/               Project documentation, specs, sprint plan
src/                Source code (scraper, NLP pipeline, dashboard)
data/               Scraped identity data (JSON)
tests/              Unit and integration tests
```

## Getting Started

```bash
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # macOS/Linux
pip install -r requirements.txt
```

## Documentation

- [Project Specification](docs/project-specification.md)
- [Sprint Plan](docs/sprints.md)

## Deployment (Optional)

This project is designed to run locally. An optional stretch goal is to deploy the web dashboard to **Streamlit Community Cloud** for easy sharing and demoing.

## License

Academic project — Fontys University of Applied Sciences, NLP course 2026.
