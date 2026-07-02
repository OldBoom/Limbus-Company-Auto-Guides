# Evaluation — Working Notes (D8)

Results for the final presentation appendix. Regenerate with `python scripts/run_evaluation.py` after pipeline runs.

## Test set

- **Held-out references:** `data/evaluation/references/*.txt` (50 files, one per guided identity)
- **Current test set:** 50 identities, 50 reference texts (human-authored, 2–4 sentences each)
- **Plausibility rubric:** [`domain-primer.md`](domain-primer.md) §7 worked examples + §2 rotation / Skill 3 rules

## Metrics

| Metric | Purpose | Target |
|--------|---------|--------|
| ROUGE-L | Generative guide overlap vs reference | Report mean on test set |
| Mechanic-tag F1 | Extraction accuracy | See `data/poc_evaluation_results.json` |
| SUS (0–100) | Usability | ≥ 3 participants, aim for 70+ |

## Baselines

| System | Description | ROUGE-L mean | vs Full |
|--------|-------------|--------------|---------|
| **Naive** | Mechanic keywords only — no skill parsing, no synergy | 0.109 | −0.066 |
| **Ablation** | Smart-template, no synergy context injected | 0.176 | +0.001 |
| **Full** | Smart-template + skill parsing + synergy rules | 0.175 | — |

> The naive baseline's −0.066 gap confirms that keyword-only generation produces noticeably less relevant text. Ablation ≈ Full because the smart-template body is driven by skill parsing; synergy mainly affects `team_suggestions`, which ROUGE-L weights lightly.

Regenerate with: `python scripts/run_evaluation.py` (all three columns) or `--baseline naive` / `--baseline ablation`.

Raw results: `data/evaluation_results.json` (last run: 50 identities).

## Efficiency

Measured over 10 runs × 50 identities (generation only, ingest excluded). Run with `python scripts/run_evaluation.py`.

| Metric | Value |
|--------|-------|
| Mean latency per identity | 1,061 ms |
| Worst-case latency per identity | 1,136 ms |
| Mean total pipeline time (50 ids) | 53,025 ms |
| Cost per query | €0 (local template, no LLM API) |
| Projected monthly @ 100 queries | €0 |
| Projected monthly @ 1,000 queries | €0 |

> The dominant cost is spaCy NER + embedding similarity in `synergy.py`. Generation itself is <1 ms per identity (pure Python string templating).

## Error categories

1. **Hallucination** — mechanic not in source JSON
2. **Synergy miss** — teammate rule not triggered
3. **Retrieval miss** — N/A (structured context, no vector DB)
4. **Formatting** — guide sections missing or malformed

## SUS user study (template)

**Results (7 participants):** [`sus-user-study-results.md`](sus-user-study-results.md)

| Metric | Result |
|--------|--------|
| Participants | 7 |
| Task success (all 3 tasks) | **21 / 21** (100%) |
| Mean SUS | **90.4** (range 80.0–97.5) |
| vs target (70+) | ✅ Exceeded |

**Tasks:**

1. Find a guide for a specific character and identity.
2. Identify the identity's primary mechanic from the guide.
3. Name one suggested teammate and explain why.

**Collect per participant:** task success (Y/N each), SUS questionnaire, one quote.

**Recruitment:** classmates or Limbus Discord — minimum 3, target 5–8.

**Participant handout:** [`sus-test-template.md`](sus-test-template.md) (tasks, SUS questionnaire, open feedback).

## Optimization experiments (D9)

| Change | Metric before | Metric after | Verdict |
|--------|---------------|--------------|---------|
| Add skill-aware template (vs naive) | ROUGE-L 0.109 (naive) | 0.175 (full) | +0.066 vs naive |
| Ablation: remove synergy from full | ROUGE-L 0.175 (full) | 0.176 (ablation) | No ROUGE impact; synergy lives in team_suggestions only |
| Expand test set 29 → 50 IDs | ROUGE-L 0.174 (29 ids) | 0.175 (50 ids) | Stable at scale |
| Swap MiniLM → bge-small-en-v1.5 | — | — | Not yet run |

## Monitoring

Logged fields (`data/logs/requests.jsonl`): timestamp, input_slug, latency_ms, token_count, cost_eur, generator.

Golden-set regression: re-run `tests/test_pipeline.py` on CI; extend with fixed guide snapshots.
