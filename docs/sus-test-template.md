# Limbus Company Auto Guides — User Test (≈10–15 min)

Hand this to participants or copy into Google Docs / Forms. Aligns with D8 in [`evaluation.md`](evaluation.md).

## What this is

You’re helping evaluate a **wiki-grounded identity guide tool** for *Limbus Company*. You don’t need to be an expert — casual or regular players are welcome.

**What I need from you:** complete 3 short tasks, answer 10 usability questions, and leave brief written feedback.

**Time:** about 10–15 minutes  
**No Limbus knowledge required** for Tasks 1–2 if you can read English; Task 3 is easier if you know the game a little.

---

## Before you start

1. Open the dashboard: `[YOUR URL]` or run locally: `streamlit run src/limbus_guides/dashboard/app.py`
2. Don’t use the wiki or other guides during the test (only this app).
3. Work at your own pace; the researcher may watch silently — they won’t help with game strategy, only with using the app if you’re stuck.
4. Note the time when you finish all tasks: `_______`

---

## Participant info (optional)

| Field | Your answer |
|--------|-------------|
| Name / nickname (or “Anonymous”) | |
| Do you play Limbus Company? | ☐ Never ☐ Sometimes ☐ Regularly |
| Familiar with identity guides / team building? | ☐ No ☐ A little ☐ Yes |

---

## Tasks

**Assign each tester a fixed identity** so results are comparable. Suggested set (pick one row per person):

| Tester | Character | Identity to find |
|--------|-----------|------------------|
| A | Faust | Ring Apprentice Faust |
| B | Yi Sang | Blade Lineage Salsu Yi Sang |
| C | Sinclair | Devyat' Assoc. North Section 3 Sinclair |
| D | Gregor | The Priest of La Manchaland Gregor |
| E | Hong Lu | The Lord of Hongyuan Hong Lu |

---

### Task 1 — Find the guide

**Goal:** Can you locate the right guide in the app?

**Steps:**

1. In the sidebar, select the character: **`[CHARACTER]`**
2. Select the identity: **`[IDENTITY]`**
3. Confirm you see sections such as **Core Idea**, **Playstyle**, and **Team suggestions**.

**Write down:**

- Time to complete (approx.): `_____ min`
- Did you succeed without help? ☐ Yes ☐ No (needed hint: `_______`)

---

### Task 2 — Identify the primary mechanic

**Goal:** Does the guide communicate what the identity is about?

**Steps:**

1. Read **Core Idea** (and skim **Playstyle** if needed).
2. In **one sentence**, state this identity’s **main mechanic or play pattern** (e.g. Bleed stacking, retreat tempo, Poise scaling — whatever *you* understood).

**Your answer:**

`_________________________________________________________________`

**Did you feel confident in your answer?**

☐ Yes ☐ Somewhat ☐ No

**Did you succeed?** ☐ Yes ☐ Partially ☐ No

---

### Task 3 — Team suggestion

**Goal:** Are team recommendations understandable?

**Steps:**

1. Scroll to **Team suggestions**.
2. Name **one suggested teammate** from the list.
3. In **one sentence**, explain **why** the app suggests them (use the text in the guide — you don’t need outside knowledge).

**Teammate named:** `_______________________`

**Why (in your words):**

`_________________________________________________________________`

**Did you succeed?** ☐ Yes ☐ Partially ☐ No

---

## Task summary (for the researcher)

| Task | Success? |
|------|----------|
| 1 — Find guide | ☐ Y ☐ N |
| 2 — Primary mechanic | ☐ Y ☐ Partial ☐ N |
| 3 — Teammate + reason | ☐ Y ☐ Partial ☐ N |

**Overall task success rate:** ___ / 3

---

## System Usability Scale (SUS)

*Rate 1–5: **1 = strongly disagree**, **5 = strongly agree**.*

| # | Statement | 1 | 2 | 3 | 4 | 5 |
|---|-----------|---|---|---|---|---|
| 1 | I think I would like to use this system frequently. | ☐ | ☐ | ☐ | ☐ | ☐ |
| 2 | I found the system unnecessarily complex. | ☐ | ☐ | ☐ | ☐ | ☐ |
| 3 | I thought the system was easy to use. | ☐ | ☐ | ☐ | ☐ | ☐ |
| 4 | I think I would need technical support to use this system. | ☐ | ☐ | ☐ | ☐ | ☐ |
| 5 | I found the various functions were well integrated. | ☐ | ☐ | ☐ | ☐ | ☐ |
| 6 | I thought there was too much inconsistency in the system. | ☐ | ☐ | ☐ | ☐ | ☐ |
| 7 | I imagine most people would learn to use this quickly. | ☐ | ☐ | ☐ | ☐ | ☐ |
| 8 | I found the system cumbersome to use. | ☐ | ☐ | ☐ | ☐ | ☐ |
| 9 | I felt confident using the system. | ☐ | ☐ | ☐ | ☐ | ☐ |
| 10 | I needed to learn a lot before I could get going. | ☐ | ☐ | ☐ | ☐ | ☐ |

### SUS score (researcher calculates)

- Odd items (1, 3, 5, 7, 9): score − 1
- Even items (2, 4, 6, 8, 10): 5 − score
- Sum all 10 → multiply by **2.5** → SUS 0–100

**SUS = ______** (leave blank for testers)

---

## Open feedback

**1. What worked well?**

`_________________________________________________________________`

**2. What was confusing or missing?**

`_________________________________________________________________`

**3. One quote I can use in my presentation** (optional, can be anonymous):

*“_______________________________________________________________”*

**4. Compared to reading the wiki, this tool feels:**

☐ Much worse ☐ Worse ☐ About the same ☐ Better ☐ Much better ☐ N/A (don’t use wiki)

**5. Anything else?**

`_________________________________________________________________`

---

## For the researcher (after each session)

Record in [`evaluation.md`](evaluation.md) and/or `data/evaluation_results.json`:

- Participant ID
- Assigned identity
- Task 1 / 2 / 3: Y / Partial / N
- SUS score
- One quote
- Any observed issues (navigation, wall of text, wrong synergy, etc.)

**Target:** ≥3 participants; aim for 5–8.  
**Aim:** mean SUS **70+** (typical “good” threshold for SUS).

### Session tips

- Don’t coach game strategy — only UI help (“try the sidebar”).
- Mix Limbus players and non-players if possible; note which they are.
- Screen-record optionally (with permission) for the presentation appendix.
- If someone fails Task 1, pre-select their assigned identity and continue so you still collect SUS + qualitative feedback.
