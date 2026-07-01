# Limbus Company Auto Guides

An NLP pipeline that scrapes [Limbus Company wiki.gg](https://limbus-company.wiki.gg) identity data and generates playable guide content — core concept summaries, playstyle guides, and team composition suggestions — displayed on a Streamlit dashboard.

## Architecture

```
Wiki / Parsed Markdown → Structured JSON → NLP Pipeline → Guide JSON → Streamlit Dashboard
```

**Scale:** 50 identities across 12 sinners (parsed markdown, JSON, guides, and evaluation references).

**NLP Pipeline:**

1. **Mechanic Extraction** — spaCy EntityRuler + regex
2. **Synergy Analysis** — sentence embeddings + support-passive rules
3. **Text Generation** — template/Ollama with [`domain-primer.md`](docs/domain-primer.md) context via `src/limbus_guides/domain/context.py`

## Project Structure

```
src/limbus_guides/     Pipeline source code
scripts/               run_pipeline.py, run_poc_evaluations.py, run_evaluation.py
data/identities/       Structured identity JSON
data/guides/           Pre-generated guides for dashboard
docs/                  Specs, sprints, evaluation, presentation outline
notebooks/             PoC evaluation notebooks
tests/                 Unit tests
config/sinners.json    Character roster config
```

## Getting Started

**Quick setup (Windows):**

```powershell
.\scripts\setup.ps1
.\.venv\Scripts\Activate.ps1
python scripts/run_pipeline.py
streamlit run src/limbus_guides/dashboard/app.py
```

**Manual setup:**

```bash
python -m venv .venv
.venv\Scripts\activate        # Windows
pip install -r requirements.txt
python -m spacy download en_core_web_sm
```

If `python` is not found, install Python 3.12:

```powershell
winget install Python.Python.3.12
```

Then open a **new terminal** (refreshes PATH) and run `setup.ps1`.

Optional: set `USE_OLLAMA=1` and run [Ollama](https://ollama.com) with `mistral` for LLM-generated guides.

## Documentation

- [Project Specification](docs/project-specification.md)
- [How to Run](docs/how-to-run.md) — add/edit identities and regenerate guides
- [Domain Primer](docs/domain-primer.md) — gameplay overview for the project team
- [Sprint Plan](docs/sprints.md)
- [Course Rubric](docs/course-files/deliverable-requirements.md)
- [Final Presentation Outline](docs/final-presentation-outline.md) — 10 min + 5 min discussion
- [Evaluation Notes](docs/evaluation.md)
- [State of the Art](docs/sota.md)

## Final Presentation (Jul 3)

**10 minutes** covering D1–D10 at headline level (see [final-presentation-outline.md](docs/final-presentation-outline.md)), plus **5 minutes** discussion with the professor. Appendix slides hold agile, full eval tables, and post-mortem detail.

## License

Academic project — IBS Furtwangen University, NLP course 2026.
