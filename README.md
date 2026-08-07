# Limbus Company Auto Guides

An NLP pipeline that scrapes [Limbus Company wiki.gg](https://limbus-company.wiki.gg) identity data and generates playable guide content — core concept summaries, playstyle guides, and team composition suggestions — displayed on a Streamlit dashboard.

## Architecture

```
Wiki / Parsed Markdown → Structured JSON → NLP Pipeline → Guide JSON → Streamlit Dashboard
```

**Scale:** the full live roster — 184 identities across 12 sinners.

The roster is discovered from the wiki itself (pages transcluding `Template:IDPage`), so new
identities are picked up automatically. `config/sinners.json` is derived output, not a
hand-maintained list:

```bash
python scripts/fetch_wiki_identities.py --dry-run   # what drifted?
python scripts/fetch_wiki_identities.py             # fetch new identities
python scripts/fetch_wiki_identities.py --rebuild-config
python scripts/run_pipeline.py                      # regenerate guides
```

**NLP Pipeline:**

1. **Mechanic Extraction** — spaCy EntityRuler + regex
2. **Synergy Analysis** — support-passive / trait / faction rules, with sentence embeddings
   as a ranked-last fallback (`--no-embeddings` skips them and drops the torch dependency)
3. **Text Generation** — template/Ollama with [`domain-primer.md`](docs/domain-primer.md) context via `src/limbus_guides/domain/context.py`

## Project Structure

```
src/limbus_guides/     Pipeline source code
scripts/               run_pipeline.py, add_identity.py, fetch_wiki_identities.py
data/identities/       Structured identity JSON
data/guides/           Pre-generated guides for dashboard
docs/                  Specs, domain notes, parsed identity markdown
notebooks/             PoC notebooks (historical — from the graded submission)
tests/                 Unit tests
config/sinners.json    Character roster config
```

## Getting Started

**Quick setup (Windows)** — use CMD if PowerShell blocks scripts:

```cmd
scripts\setup.cmd
.venv\Scripts\python.exe scripts\run_pipeline.py
.venv\Scripts\python.exe -m streamlit run src\limbus_guides\dashboard\app.py
```

See [how-to-run.md](docs/how-to-run.md) for troubleshooting (`No module named 'limbus_guides'`,
execution policy, single-slug regen, and full script list).

**PowerShell** (when `.ps1` execution is allowed):

```powershell
.\scripts\setup.ps1
.\.venv\Scripts\python.exe scripts\run_pipeline.py
```

**Manual setup (macOS / Linux):**

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -e .
python -m spacy download en_core_web_sm

python scripts/run_pipeline.py
python -m streamlit run src/limbus_guides/dashboard/app.py
```

On Windows the venv activate script is `.venv\Scripts\activate` instead.
Requires Python 3.10 or newer.

If `python` is not found, install Python 3.12:

```powershell
winget install Python.Python.3.12
```

Then open a **new terminal** (refreshes PATH) and run `scripts\setup.cmd`.

Optional: set `USE_OLLAMA=1` and run [Ollama](https://ollama.com) with `mistral` for LLM-generated guides.

## Documentation

- [Project Specification](docs/project-specification.md)
- [How to Run](docs/how-to-run.md) — setup, add/edit identities, regenerate guides
- [Ingestion Rulebook](docs/ingestion-rulebook.md) — slug rules, mechanics policy, protected files
- [Domain Primer](docs/domain-primer.md) — gameplay overview for the project team
- [State of the Art](docs/sota.md)

Frozen records from the graded submission (not maintained): [Term Paper](docs/term-paper.md),
[Evaluation Notes](docs/evaluation.md), [Course Rubric](docs/course-files/deliverable-requirements.md).

## License

Academic project — IBS Furtwangen University, NLP course 2026.
