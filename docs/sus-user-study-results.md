# SUS User Study — Results (7 participants)

Results from the D8 usability study for the Limbus Company Auto Guides dashboard.  
Handout template: [`sus-test-template.md`](sus-test-template.md).

**Dashboard tested:** [limbus-company-nlp-guides.streamlit.app](https://limbus-company-nlp-guides.streamlit.app/)

---

## Executive summary

| Metric | Result | Target |
|--------|--------|--------|
| Participants | **7** | ≥ 3 (aim 5–8) |
| Task 1 — Find guide | **7 / 7** (100%) | — |
| Task 2 — Primary mechanic | **7 / 7** (100%) | — |
| Task 3 — Teammate + reason | **7 / 7** (100%) | — |
| **Mean SUS** | **90.4** | ≥ 70 (“good”) |
| Median SUS | 90.0 | — |
| Mean session time (all tasks) | **~2.9 min** | 10–15 min budget |
| Completed without researcher help | **6 / 7** | — |

All participants completed all three tasks. Only **P4** (never played, weak English) received reading assistance. Mean SUS is well above the usual **70+** “good” threshold and above the industry average (~68).

---

## How SUS is calculated

Participants rate 10 statements **1–5** (1 = strongly disagree, 5 = strongly agree).

| Questions | Wording type | Adjustment |
|-----------|--------------|------------|
| **Odd** (1, 3, 5, 7, 9) | Positive (“easy to use”, “confident”, …) | **score − 1** |
| **Even** (2, 4, 6, 8, 10) | Negative (“unnecessarily complex”, “cumbersome”, …) | **5 − score** |

**SUS = (sum of 10 adjusted values) × 2.5** → range **0–100**.

Example pattern `5151515151` (strong yes on good items, strong no on bad items) → adjusted sum 40 → **SUS 100**.

---

## Aggregate SUS

| Participant | Raw answers (Q1–Q10) | Adjusted sum | SUS |
|-------------|----------------------|--------------|-----|
| P1 | 4 2 5 3 4 2 5 1 5 3 | 32 | **80.0** |
| P2 | 3 1 5 1 5 1 4 1 4 1 | 36 | **90.0** |
| P3 | 5 1 5 1 5 1 4 1 5 1 | 39 | **97.5** |
| P4 | 1 1 5 1 5 1 5 1 4 3 | 33 | **82.5** |
| P5 | 4 2 5 1 3 1 5 1 5 1 | 36 | **90.0** |
| P6 | 4 1 5 1 4 1 5 1 5 1 | 38 | **95.0** |
| P7 | 4 1 5 1 5 1 5 1 5 1 | 39 | **97.5** |
| **Mean** | — | 36.1 | **90.4** |

---

## Task success

| Participant | Task 1 | Task 2 | Task 3 | Time (all tasks) | Notes |
|-------------|--------|--------|--------|------------------|-------|
| P1 | Y | Y | Y | ~3 min | No help needed; low self-confidence, English not first language |
| P2 | Y | Y | Y | ~3 min | Felt confident |
| P3 | Y | Y | Y | ~2.5 min | — |
| P4 | Y | Y | Y | ~4.5 min | **Only participant who needed help** (reading); somewhat confident on Task 2 |
| P5 | Y | Y | Y | ~3.4 min | — |
| P6 | Y | Y | Y | ~1–2 min | — |
| P7 | Y | Y | Y | ~2 min | Enjoyed exploring |

**Overall:** 21 / 21 task completions (**100%**). **Assistance:** 1 / 7 participants (P4 only — never played, weak English; researcher helped with reading).

### Assigned identities (where recorded)

| Participant | Handout | Character | Identity |
|-------------|---------|-----------|----------|
| P1 | `sus-test-1.md` | Faust | Ring Apprentice Faust |
| P2 | `sus-test-2.md` | Sinclair | Devyat' Assoc. North Section 3 Sinclair |
| P3 | `sus-test-3.md` | Gregor | The Priest of La Manchaland Gregor |
| P4 | `sus-test-4.md` | Heathcliff | Kurokumo Clan Wakashu Heathcliff |
| P5–P7 | — | *not recorded* | *not recorded* |

---

## Participant profiles

| P | Plays Limbus | Team-building familiarity | Uses wiki | Player type |
|---|--------------|---------------------------|-----------|-------------|
| 1 | Regularly | Yes | No | Casual |
| 2 | Occasionally | Yes | No | Casual |
| 3 | Never | Yes (other games) | No | — |
| 4 | Never | No | No | — |
| 5 | Never | Yes (other games) | No | — |
| 6 | Regularly | A little | No | — |
| 7 | Regularly | Yes | Sometimes | — |

---

## Qualitative feedback

### What worked well

- **Navigation** — multiple participants called the system easy to navigate or self-explanatory (P2, P6).
- **Core Idea clarity** — mechanics understandable even when skimmed (P2).
- **Speed** — quick lookup vs walls of wiki text (P3, P6).
- **Overall guide quality** — P1 liked the guide despite low confidence in their own answers.

### Pain points

| Issue | Participants | Status |
|-------|--------------|--------|
| In-game terminology confusing (non-player, weak English) | P4 | Documented; expected for LC-specific terms |
| Needed researcher help (reading only) | **P4 only** | All other participants unaided |
| Low confidence in own answers (not app fault) | P1 | Completed without help |
| English difficulty (no help required) | P1 | — |

### Wiki comparison (when asked post-session)

| Participant | Verdict |
|-------------|---------|
| P1, P2, P5, P6 | N/A (don't use wiki) |
| P3 | **Much better** than wiki |
| P4 | **Better** than wiki |
| P7 | **Better** than wiki and in-game |

---

## Feature requests & follow-up

| Feedback | Participant | Status |
|----------|-------------|--------|
| Colour coding in guide text | P3 | **Implemented** during study |
| Clickable teammate names in Team suggestions | P5 | **Implemented** |
| New tab on every identity click | P5 | **Fixed** |
| Rufo and Ring Salt identities | P7 | **Implemented** |
| Wider identity selection | P6 | Planned after academic presentation |
| P7 exploring Wild Hunt etc. | P7 | Ongoing content expansion |

---

## Quotes for presentation

Approved or requested for slides / appendix:

| Participant | Quote | Context |
|-------------|-------|---------|
| **P2** | *"I must insist... that you continue working on this tool."* … *"For that would be most ideal."* | Enthusiastic endorsement |
| **P2** | *"System is very easy to navigate, the core ideas of each id are easy to understand, even when only skimmed."* | General usability |
| **P3** | *"Rapidly navigate through walls of text!"* | vs wiki |
| **P6** | *"TETO NUMBERO UNO!"* | Humorous endorsement |
| **P6** | *"System was relativy easy to use and self explanatory, it was a nice addiction for a dev like to me see how the data was stored :)"* | Dev audience |
| **P7** | *"i should try this on an ID that i still dont understand properly like WildHunt"* | Suggested use case |
| **P7** | Better than wiki **and** in-game | Comparison (quote wording TBD) |

**P7** — still deciding on a final presentation line; comparison note recorded above.

---

## Top usability findings (for slides)

1. **100% task success** across find-guide, mechanic identification, and teammate reasoning — **6 / 7 unaided**; only P4 (never played, weak English) needed reading help.
2. **Mean SUS 90.4** — strong ease-of-use signal; lowest individual score still **80.0** (P1).
3. **Wiki perceived as worse** when shown side-by-side (P3, P4, P7) — main value prop is structured summaries vs raw wiki walls of text.
4. **Terminology barrier** for never-played testers — guides work structurally but LC jargon remains a ceiling without game context.
5. **Iterative fixes during study** (colour coding, linked teammates, tab behaviour) improved live sessions and show responsiveness to feedback.

---

## Per-participant detail

### P1 — SUS 80.0

- **Profile:** Regular player, familiar with team building, casual, no wiki.
- **Time:** ~3 min · **Tasks:** 3/3 · **Help:** None · **Confidence:** Not confident in themselves; English challenges but completed solo.
- **SUS:** `4 2 5 3 4 2 5 1 5 3`
- **Notes:** Everything worked well; liked the guide.

### P2 — SUS 90.0

- **Profile:** Occasional player, familiar with team building, casual, no wiki.
- **Time:** ~3 min · **Tasks:** 3/3 · **Confidence:** Yes.
- **SUS:** `3 1 5 1 5 1 4 1 4 1`
- **Quote:** *"System is very easy to navigate, the core ideas of each id are easy to understand, even when only skimmed."*
- **Presentation:** *"I must insist... that you continue working on this tool."* / *"For that would be most ideal."*

### P3 — SUS 97.5

- **Profile:** Never played Limbus; familiar with team building from other games; no wiki.
- **Time:** ~2.5 min · **Tasks:** 3/3.
- **SUS:** `5 1 5 1 5 1 4 1 5 1`
- **Notes:** Liked how easy and quick character lookup is. After wiki demo: **much better than wiki**.
- **Presentation:** *"Rapidly navigate through walls of text!"*
- **Implemented:** Colour coding.

### P4 — SUS 82.5

- **Profile:** Never played; not familiar with team building; no wiki; struggles with English.
- **Time:** ~4.5 min · **Tasks:** 3/3 · **Help:** Reading assistance (only participant who needed any) · **Confidence:** Somewhat on Task 2.
- **SUS:** `1 1 5 1 5 1 5 1 4 3`
- **Notes:** All worked well; in-game terminology confusing. After wiki: **better than wiki**.

### P5 — SUS 90.0

- **Profile:** Never played; familiar with team building from other games; no wiki.
- **Time:** ~3.4 min · **Tasks:** 3/3.
- **SUS:** `4 2 5 1 3 1 5 1 5 1`
- **Notes:** Liked overall.
- **Implemented:** Clickable names in team suggestions; fixed new-tab-on-every-click.

### P6 — SUS 95.0

- **Profile:** Regular player; a little familiar with team building; no wiki.
- **Time:** ~1–2 min · **Tasks:** 3/3.
- **SUS:** `4 1 5 1 4 1 5 1 5 1`
- **Quote:** *"System was relativy easy to use and self explanatory, it was a nice addiction for a dev like to me see how the data was stored :)"*
- **Presentation:** *"TETO NUMBERO UNO!"*
- **Planned:** Wider ID selection after academic presentation.

### P7 — SUS 97.5

- **Profile:** Regular player; familiar with team building; sometimes uses wiki.
- **Time:** ~2 min · **Tasks:** 3/3 without help; enjoyed exploring.
- **SUS:** `4 1 5 1 5 1 5 1 5 1`
- **Notes:** Wants to try confusing IDs (e.g. Wild Hunt). **Better than wiki and game.**
- **Implemented:** Rufo and Ring Salt identities requested.
- **Presentation:** Quote TBD.

---

## Researcher checklist

- [x] ≥ 3 participants (7)
- [x] SUS calculated per participant
- [x] Task success recorded
- [x] Quotes captured for presentation
- [x] Post-study UI fixes noted
- [ ] Add mean SUS + task rate to `data/evaluation_results.json` if needed for scripts
- [ ] Final P7 presentation quote when confirmed

---

*Recorded: July 2026 · See also [`evaluation.md`](evaluation.md) for ROUGE-L and baseline metrics.*
