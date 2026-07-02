# Identity Ingestion Rulebook

Operator reference for adding Limbus Company identities to this project. Use
`scripts/add_identity.py` as the primary entry point; this document explains
slug rules, quality checkpoints, and manual fallbacks.

## Quick start

```powershell
python scripts/add_identity.py "https://limbuscompany.wiki.gg/wiki/<Page_Title>"
```

The script: resolves slug → fetches wiki → writes `docs/parsed-ids/<slug>.md` →
updates `config/sinners.json` → patches unknown mechanics → generates
`data/guides/<slug>.json` → prompts for reference text and portrait → prints
ROUGE-L if a reference was saved.

---

## Slug rules

Project slugs are **Windows-safe** filenames derived from wiki page titles.

### Rule 1 — `::` (E.G.O. namespace)

Wiki uses `::` between faction and E.G.O name. Colons are illegal in Windows paths.

| Wiki title | Project slug |
|------------|--------------|
| `Lobotomy_E.G.O::Magic_Bullet_Outis` | `Lobotomy_E.G.O_Magic_Bullet_Outis` |
| `LCE_E.G.O::AEDD_Gregor` | `LCE_E.G.O_AEDD_Gregor` |
| `N_Corp._E.G.O::Contempt,_Awe_Ryōshū` | `N_Corp._E.G.O_Contempt,_Awe_Ryōshū` |

**Reverse:** any slug containing `_E.G.O_` → replace with `_E.G.O::` when calling the wiki API.

### Rule 2 — `:_` (House of Spiders sub-pages)

| Wiki title | Project slug |
|------------|--------------|
| `The_House_of_Spiders:_The_Ring_Nursefather_Hong_Lu` | `The_House_of_Spiders_The_Ring_Nursefather_Hong_Lu` |
| `The_House_of_Spiders:_The_Middle_Nursefather_Outis` | `The_House_of_Spiders_The_Middle_Nursefather_Outis` |

**Reverse:** slug starting with `The_House_of_Spiders_The_` → insert `:` after `Spiders`.

### Rule 3 — `SLUG_TO_WIKI_OVERRIDES`

Some identities use a **shorter project slug** than the wiki page title. Defined in
`src/limbus_guides/ingestion/wiki_parser.py`:

| Project slug | Wiki title |
|--------------|------------|
| `Ring_Apprentice_Faust` | `The_House_of_Spiders:_The_Ring_Apprentice_Faust` |
| `Ring_Pointillist_Student_Yi_Sang` | `The_Ring_Pointillist_Student_Yi_Sang` |

**When to add:** wiki title is long or confusing; add to `SLUG_TO_WIKI_OVERRIDES` and
ensure `filename_to_wiki_title()` returns the correct wiki title.

### Rule 4 — Unicode preserved

Characters like `ō`, `ū`, `Ö`, `'` stay in slugs. Use UTF-8 terminals on Windows
(`add_identity.py` reconfigures stdout when possible).

### Rule 5 — Double underscore collapse

After `::` and `:` → `_` replacement, consecutive `__` are collapsed to `_`.

### Round-trip check

Before fetch, `add_identity.py` verifies:

```text
wiki_title_to_stem(filename_to_wiki_title(slug)) == slug
```

(except entries in `SLUG_TO_WIKI_OVERRIDES`).

---

## UNIQUE_MECHANICS policy

1. Wiki `{{StatusEffect|Name}}` tags are extracted into **Key Status Effects** in parsed markdown.
2. Non-standard effects (not in `STANDARD_EFFECTS` in `wiki_parser.py`) appear as `### Name` headings.
3. `run_pipeline.py` and `add_identity.py` auto-register unknown Key Status Effects in
   `config/unique_mechanics.json` (merged at runtime with `UNIQUE_MECHANICS` in
   `src/limbus_guides/nlp/mechanics.py`).
4. If skill text contains scaling (`per N Name`) or support (`gain N Name`), the script
   also patches `SCALES_OFF_RE` / `SUPPORT_PASSIVE_RE` in `synergy.py`.
5. Pass `--confirm-mechanics` to approve each term interactively.

After patching mechanics at runtime, `clear_mechanics_cache()` reloads the spaCy EntityRuler.

---

## Reference files (evaluation)

- Path: `data/evaluation/references/<slug>.txt`
- Format: 2–4 sentences of plain prose
- Sentence 1: identity name + role + primary mechanic
- Sentences 2–3: resource loop / state transition
- Sentence 4 (optional): passive or synergy note

**Do not** generate references from the pipeline guide output (circular evaluation).
`add_identity.py` prints a wiki excerpt and a suggested LLM prompt; paste the result
at the interactive prompt (same workflow used for the existing 50 references).

Flags: `--ref-file PATH`, `--skip-ref`.

---

## Portrait files (dashboard)

- Path: `src/limbus_guides/dashboard/static/images/identities/<slug>.png`
- Provide at the interactive prompt or via `--portrait PATH`
- If skipped, the dashboard falls back to the sinner story portrait

---

## New sinner checklist

If the wiki `|sinner=` field names a character not yet in `config/sinners.json`,
`add_identity.py` auto-creates:

```json
{ "id": "slugified_name", "name": "Display Name", "identities": ["<slug>"] }
```

Override with `--add-sinner "Name"` when inference fails.

---

## Protected parsed files

These stems are hand-curated; `--force` alone will not overwrite them:

- `Ring_Apprentice_Faust`
- `Blade_Lineage_Salsu_Yi_Sang`
- `Ring_Pointillist_Student_Yi_Sang`
- `The_House_of_Spiders_The_Ring_Apprentice_Faust`

Use `--force-protected` to overwrite.

---

## Audit workflow

After bulk changes, compare stored markdown vs live wiki:

```powershell
python scripts/audit_wiki_parsing.py
```

Output: `data/wiki_audit_report.json` + stdout summary. Look for:

- **FETCH FAILURES** — slug ↔ wiki title mismatch (check Rules 1–3)
- **COIN COUNT MISMATCHES** — skill parsing drift

---

## CLI flags summary

| Flag | Purpose |
|------|---------|
| `--dry-run` | Print slug/wiki title without writing |
| `--force` | Re-fetch and overwrite parsed markdown |
| `--force-protected` | Allow overwriting protected stems |
| `--portrait PATH` | Copy portrait PNG |
| `--skip-portrait` | Skip portrait step |
| `--skip-ref` | Skip reference prompt |
| `--ref-file PATH` | Use pre-written reference |
| `--add-sinner NAME` | Override sinner inference |
| `--confirm-mechanics` | Prompt before each mechanic patch |
| `--ollama` | LLM guide generation (requires Ollama) |
| `--smoke-test` | Run `pytest -k <slug>` after completion |

---

## Batch import (legacy)

For many identities at once:

```powershell
python scripts/fetch_wiki_identities.py "<url1>" "<url2>" --update-config
python scripts/run_pipeline.py
```
