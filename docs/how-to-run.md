# How to Run — Operator Guide

Short reference for environment setup, adding identities, regenerating guides, and
previewing output in the Streamlit dashboard.

For slug rules, protected files, and ingestion policy, see
[ingestion-rulebook.md](ingestion-rulebook.md).

---

## 1. Environment setup (once per machine)

The package lives under `src/`. You must either **install it in a venv** (`pip install -e .`)
or run the helper scripts in `scripts/` (they add `src/` to `sys.path` automatically).

### Windows — PowerShell blocks `.ps1` scripts (common)

Use the CMD setup script (no execution-policy change):

```cmd
scripts\setup.cmd
```

### Windows — PowerShell allowed

```powershell
.\scripts\setup.ps1
```

Optional: `.\.venv\Scripts\Activate.ps1` — **not required** if you call the venv
interpreter directly (see below).

### macOS / Linux

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/pip install -e .
.venv/bin/python -m spacy download en_core_web_sm
```

### Use the venv Python (recommended daily workflow)

On Windows, prefer **`.venv\Scripts\python.exe`** instead of bare `python` so you never
hit `ModuleNotFoundError: No module named 'limbus_guides'`.

| Task | Windows command |
|------|-----------------|
| Full pipeline | `.venv\Scripts\python.exe scripts\run_pipeline.py` |
| Same (module) | `.venv\Scripts\python.exe -m limbus_guides.pipeline.run` |
| Dashboard | `.venv\Scripts\python.exe -m streamlit run src\limbus_guides\dashboard\app.py` |
| Tests | `.venv\Scripts\python.exe -m pytest tests\test_pipeline.py -q` |
| Add identity | `.venv\Scripts\python.exe scripts\add_identity.py "<wiki url>"` |

Equivalent console entry points after `pip install -e .`: `limbus-pipeline`, `limbus-dashboard`.

### Troubleshooting

| Symptom | Fix |
|---------|-----|
| `No module named 'limbus_guides'` | Use `.venv\Scripts\python.exe`, not system `python`; run `setup.cmd` or `pip install -e .` |
| `Activate.ps1` / `setup.ps1` blocked | Use `scripts\setup.cmd`, or `Set-ExecutionPolicy -Scope Process Bypass` for one session |
| `No module named 'numpy'` / spaCy errors | Re-run setup; dependencies are in `requirements.txt` |
| Dashboard shows old guide text | Re-run pipeline after editing `src/` or `docs/parsed-ids/` |

---

## 2. Regenerate guides

### All identities

```cmd
.venv\Scripts\python.exe scripts\run_pipeline.py
```

Writes `data/identities/*.json`, `data/guides/*.json`, and `data/guides/manifest.json`.
Also syncs new **Key Status Effects** into `config/unique_mechanics.json` before NLP runs.

### One identity (faster)

```cmd
.venv\Scripts\python.exe -c "from limbus_guides.pipeline.run import run_for_slug; run_for_slug('Wild_Hunt_Heathcliff')"
```

Or after `add_identity.py` completes (it calls `run_for_slug` internally for that slug).

### Optional: LLM prose

Set `USE_OLLAMA=1` and run Ollama with `mistral`, then:

```cmd
.venv\Scripts\python.exe scripts\run_pipeline.py
```

(`add_identity.py --ollama` for a single slug.)

---

## 3. Add a new identity (recommended path)

One command from wiki URL to parsed markdown, guide JSON, optional reference, and portrait:

```cmd
.venv\Scripts\python.exe scripts\add_identity.py "https://limbuscompany.wiki.gg/wiki/<Page_Title>"
```

The script will:

1. Resolve the project slug and fetch the wiki page
2. Write `docs/parsed-ids/<slug>.md` and update `config/sinners.json`
3. Register unknown **Key Status Effects** in `config/unique_mechanics.json` (and patch
   synergy regexes when scaling/support patterns match)
4. Generate `data/identities/<slug>.json` and `data/guides/<slug>.json`
5. Prompt for:
   - **Reference text** (2–4 sentences for ROUGE-L) — wiki excerpt + LLM prompt printed
   - **Portrait PNG** (optional; dashboard falls back to sinner portrait)
6. Print ROUGE-L scores if a reference was saved

| Flag | Purpose |
|------|---------|
| `--dry-run` | Preview slug/wiki mapping only |
| `--force` | Re-fetch existing parsed markdown |
| `--force-protected` | Overwrite hand-curated protected stems |
| `--ref-file path\to\ref.txt` | Skip reference prompt |
| `--skip-ref` | No reference / no ROUGE-L |
| `--portrait path\to\image.png` | Skip portrait prompt |
| `--skip-portrait` | No portrait copy |
| `--confirm-mechanics` | Prompt before each mechanic / regex patch |
| `--ollama` | Use Ollama for guide prose |
| `--smoke-test` | Run `pytest -k <slug>` after completion |

---

## 4. Batch import (many identities)

```cmd
.venv\Scripts\python.exe scripts\fetch_wiki_identities.py "https://limbuscompany.wiki.gg/wiki/<Page1>" --update-config
.venv\Scripts\python.exe scripts\run_pipeline.py
```

Pass multiple URLs as separate arguments. Use `--update-config` to append slugs to
`config/sinners.json`.

---

## 5. Edit an existing identity

| Goal | What to do |
|------|------------|
| Refresh from wiki | `add_identity.py "<url>" --force` |
| Fix parsing manually | Edit `docs/parsed-ids/<slug>.md`, then re-run pipeline |
| Tune mechanic blurbs | Edit `MECHANIC_SIGNALS` in `src/limbus_guides/nlp/mechanic_signals.py`, re-run pipeline |
| New identity resource keyword | Usually auto via Key Status Effects → `unique_mechanics.json`; see rulebook |
| Faction synergy exception | `src/limbus_guides/nlp/synergy.py` → `_FACTION_SLUG_OVERRIDES` |
| Update eval reference | Edit `data/evaluation/references/<slug>.txt`, then `run_evaluation.py` |
| Bulk portrait download | `scripts\fetch_identity_portraits.py` (wiki list page → `dashboard/static/images/identities/`) |

---

## 6. Sanity checks after changes

- `data/guides/<slug>.json` exists and `team_suggestion_picks` is populated (new guides)
- Spot-check dashboard: colored status keywords, Core Idea card, clickable team links
- `pytest tests/test_pipeline.py` after code changes
- `.venv\Scripts\python.exe scripts\audit_wiki_parsing.py` after bulk wiki imports

---

## 7. Scripts reference

| Script / command | Purpose |
|------------------|---------|
| `scripts/setup.cmd` | **Windows CMD:** venv + deps + spaCy model (no PowerShell policy) |
| `scripts/setup.ps1` | Same as setup.cmd for PowerShell |
| `scripts/add_identity.py` | **Primary:** wiki URL → parsed MD → guide → reference → eval |
| `scripts/fetch_wiki_identities.py` | Batch wiki → `docs/parsed-ids/*.md` |
| `scripts/run_pipeline.py` | All parsed markdown → identities + guides + manifest |
| `python -m limbus_guides.pipeline.run` | Same as run_pipeline (requires `pip install -e .`) |
| `scripts/run_evaluation.py` | Full-roster ROUGE-L and baselines |
| `scripts/run_poc_evaluations.py` | Early PoC metric scripts |
| `scripts/audit_wiki_parsing.py` | Compare stored parses vs live wiki |
| `scripts/fetch_identity_portraits.py` | Download identity portraits from wiki |
| `streamlit run src/limbus_guides/dashboard/app.py` | Interactive guide browser (use venv Python) |

---

## 8. Key output paths

| Path | Contents |
|------|----------|
| `docs/parsed-ids/<slug>.md` | Wiki-normalized markdown (source of truth for skills) |
| `data/identities/<slug>.json` | Structured skills + `raw_markdown` |
| `data/guides/<slug>.json` | Dashboard guide (`core_idea`, `playstyle_guide`, `team_suggestion_picks`, …) |
| `config/unique_mechanics.json` | Auto-discovered identity resources |
| `config/sinners.json` | Sinner roster and identity slug lists |
| `data/evaluation/references/<slug>.txt` | Human reference prose for ROUGE-L |
