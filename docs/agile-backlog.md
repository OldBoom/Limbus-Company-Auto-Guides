# Agile Backlog (D4 — appendix evidence)

Lightweight backlog for GitHub Issues/Projects. Tag each story **Must / Should / Could / Won't**.

## User stories (18)

| ID | Story | MoSCoW | Points | Acceptance criteria |
|----|-------|--------|--------|---------------------|
| US-01 | As a player, I select a character so I see their identities | Must | 2 | Sidebar lists 12 sinners |
| US-02 | As a player, I pick an identity and read its guide | Must | 3 | 3 sections render from JSON |
| US-03 | As a developer, I ingest parsed markdown to JSON | Must | 5 | 3 IDs in `data/identities/` |
| US-04 | As a developer, I scrape wiki.gg pages | Should | 8 | ≥20 IDs across 12 characters |
| US-05 | As a developer, I extract game mechanics via NER | Must | 5 | F1 ≥ 0.85 on pilot set |
| US-06 | As a developer, I compute identity similarity | Must | 5 | Bleed pair > Poise pair |
| US-07 | As a developer, I detect synergy teammates | Must | 5 | Named teammates + reason |
| US-08 | As a developer, I generate grounded guide text | Must | 8 | No hallucinated mechanics |
| US-09 | As a developer, I run the end-to-end pipeline | Must | 5 | One CLI command |
| US-10 | As a developer, I launch the Streamlit dashboard | Must | 3 | `streamlit run` works |
| US-11 | As a researcher, I compare NER approaches | Should | 3 | PoC results in `sota.md` |
| US-12 | As a researcher, I compare embedding models | Should | 3 | 3 models benchmarked |
| US-13 | As a researcher, I evaluate LLM grounding | Should | 5 | Grounding score reported |
| US-14 | As a researcher, I run ROUGE-L on test set | Must | 5 | Mean score in eval JSON |
| US-15 | As a researcher, I run SUS user study | Must | 5 | ≥3 participants |
| US-16 | As a developer, I log request latency | Could | 3 | JSONL log file |
| US-17 | As a presenter, I deliver a 10-min demo | Must | 5 | Timed rehearsal |
| US-18 | As a presenter, I prepare appendix for discussion | Must | 3 | D4–D10 detail slides |

## Next two weeks (example)

**Week 1:** US-04 (scrape), US-14 (eval expansion)  
**Week 2:** US-15 (SUS), US-17 (rehearsal)

Screenshot GitHub Projects board for final presentation appendix.
