# How to Run — Identity Maintenance

Short operator guide for adding identities, refreshing data, and previewing generated guides.

## Prerequisites (once per machine)

```powershell
.\scripts\setup.ps1
.\.venv\Scripts\Activate.ps1
```

## Add a new identity (recommended)

One command from wiki URL to guide + optional reference + portrait:

```powershell
python scripts/add_identity.py "https://limbuscompany.wiki.gg/wiki/<Page_Title>"
```

The script will:

1. Resolve the project slug and fetch the wiki page
2. Write `docs/parsed-ids/<slug>.md` and update `config/sinners.json`
3. Auto-add unknown Key Status Effects to `UNIQUE_MECHANICS` (and synergy regexes when patterns match)
4. Generate `data/guides/<slug>.json`
5. Print the guide, then prompt for:
   - **Reference text** (2–4 sentences for ROUGE-L evaluation) — wiki excerpt + LLM prompt are printed to help you draft it
   - **Portrait PNG path** (optional; dashboard falls back to sinner portrait if skipped)
6. Print ROUGE-L scores if a reference was saved

Useful flags:

| Flag | Purpose |
|------|---------|
| `--dry-run` | Preview slug/wiki mapping only |
| `--force` | Re-fetch existing parsed markdown |
| `--ref-file path\to\ref.txt` | Skip reference prompt |
| `--skip-ref` | No reference / no ROUGE-L |
| `--portrait path\to\image.png` | Skip portrait prompt |
| `--skip-portrait` | No portrait copy |
| `--ollama` | Use Ollama for guide prose |
| `--smoke-test` | Run pytest for this slug after completion |

See [ingestion-rulebook.md](ingestion-rulebook.md) for slug rules, protected files, and audit workflow.

## Batch import (many identities)

```powershell
python scripts/fetch_wiki_identities.py "https://limbuscompany.wiki.gg/wiki/<Page1>" --update-config
python scripts/run_pipeline.py
```

## Edit an existing identity

| Goal | What to do |
|------|------------|
| Refresh from wiki | `python scripts/add_identity.py "<url>" --force` |
| Fix parsing manually | Edit `docs/parsed-ids/<slug>.md`, then `python scripts/run_pipeline.py` |
| Improve mechanic advice | Add a row to `MECHANIC_SIGNALS` in `src/limbus_guides/nlp/mechanic_signals.py`, then re-run pipeline |
| Update eval reference | Edit `data/evaluation/references/<slug>.txt`, then `python scripts/run_evaluation.py` |

## Sanity checks after changes

- Confirm `data/guides/<slug>.json` exists
- Spot-check in Streamlit: `streamlit run src/limbus_guides/dashboard/app.py`
- `pytest tests/test_pipeline.py` after code changes

## Project scripts reference

| Script | Purpose |
|--------|---------|
| `scripts/setup.ps1` | Create venv, install deps, download spaCy model |
| `scripts/add_identity.py` | **Primary:** wiki URL → parsed MD → guide → reference → eval |
| `scripts/fetch_wiki_identities.py` | Batch wiki → `docs/parsed-ids/*.md` |
| `scripts/run_pipeline.py` | All parsed markdown → `data/identities/` + `data/guides/` |
| `scripts/run_evaluation.py` | Full-roster ROUGE-L and baselines |
| `scripts/audit_wiki_parsing.py` | Compare stored parses vs live wiki |
| `streamlit run src/limbus_guides/dashboard/app.py` | Interactive guide browser |
