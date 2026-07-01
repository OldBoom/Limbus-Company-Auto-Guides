# Limbus Company — Domain Primer

A high-level gameplay reference for the **Limbus Company Auto Guides** NLP project. This document explains *what the game is* and *how identity kits work*, so you can interpret wiki data, write evaluation references, and understand generated guides.

**Related docs:**

- Mechanic dictionary (NER entity source): [`status-effects.md`](status-effects.md)
- Parsed identity examples: [`parsed-ids/`](parsed-ids/)
- Wiki parsing rules: [`301-wiki-identity-parsing.mdc`](301-wiki-identity-parsing.mdc)

---

## 1. One-paragraph pitch

**Limbus Company** is a turn-based squad battler (Project Moon, 2023–present). You control **12 Sinners** — distinct playable characters — each of whom equips exactly **one Identity** per team. An Identity is a full combat kit: stats, three attack skills, defense options, combat passives, and a **support passive** that affects the whole team. Combat revolves around **clashing** skills, resolving **coins**, applying **status effects** (Bleed, Burn, Poise, etc.), and managing **stagger**. The NLP project reads wiki.gg identity pages, extracts mechanics, infers synergies, and produces short guides: **core concept**, **playstyle**, and **team suggestions**.

---

## 2. Combat loop (high level)

You do not need full damage formulas for this project. These concepts are enough to read skill text and write guides.

### Battle, turn, and rotation

Use these terms consistently — they match in-game wording:

| Term | Meaning |
|------|---------|
| **Battle** | The full encounter — all **turns** from start to finish |
| **Turn** | One cycle in which **every unit** on the field acts once (each uses one skill, in Speed order) |
| **Rotation** | One unit’s shuffled offensive queue (3×S1, 2×S2, 1×S3). Spans many turns until empty, then a **new rotation** is built |

A **turn** is not the same as a **rotation**. Skill 3 appears **once per rotation**, not once per turn.

### Turn structure

Each **turn**, units act one after another in **Speed** order (min–max range per identity). When a unit acts, it selects a skill; when two skills contest the same target, a **clash** resolves who wins. The winner’s skill continues; the loser’s skill may be interrupted or weakened.

### Clash and power

Skills have **Base Power**, **Coin Power**, and often **Clash Power** / **Final Power** modifiers. Conditional lines like `[On Use] Clash Power +1 for every 4 Bleed on target` describe how the identity scales during setup.

#### Offense Level and Defense Level

Every unit has an **Offense Level** and **Defense Level** that scale with character level and per-skill modifiers. The formula is:

```
Level = Unit_Level + Skill_Modifier
```

On wiki skill tables the format is e.g. `63 (60+3)` — the unit is level 60, the skill adds +3.

These levels affect combat in two ways:

1. **Clash power**: The skill with the higher Offense/Defense Level gains +1 Clash Power per 3 levels of difference (e.g. 6 levels ahead = +2 Clash Power).

2. **Damage modifier**: When attacking, the level difference between attacker Offense Level and defender Defense Level modifies damage:
   ```
   M (%) = (Off − Def) / (|Off − Def| + 25) × 100
   ```
   Examples at a typical enemy Defense Level 60:
   - Offense 63 (+3 over enemy): ≈ +10.7% damage
   - Offense 57 (−3 under enemy): ≈ −10.7% damage

   The modifier softens at extremes (the denominator grows), preventing one-shots from pure level gaps.

> **Note on roll estimates in guides:** The `rolls — low N, high N` values shown per skill are **raw rolls** (all Tails for low; all Heads for high) at the base power level, without applying the Offense/Defense Level damage modifier or resistances. They are accurate for **comparing skills and identities relative to each other** — but actual in-game damage will be higher or lower depending on the specific enemy's Defense Level and resistances.

#### Atk Weight — number of targets

`Atk Weight` (written as `x1`, `x2`, `x3` on wiki skill tables) is the **number of targets** the skill hits simultaneously. It is **not** the number of coin flips. The actual coin count is determined by how many numbered rows appear in the skill's **coin effects table**.

| Atk Weight | Meaning |
|-----------|---------|
| x1 | Hits 1 target |
| x2 | Hits 2 targets simultaneously |
| x3 | Hits 3 targets simultaneously (often AoE S1 skills) |

A skill with `x3` and one coin-effect row flips **1 coin** and deals its result to **3 separate targets**.

### Coins

Attack skills are built from one or more **coins** (numbered 1, 2, 3…). Each coin can have effects tagged with triggers such as `[On Hit]`, `[Heads Hit]`, or `[Clash Win]`. Coins may inflict status effects, heal, or modify stats.

#### Coin flip probability and Sanity

The probability of flipping **Heads** depends on Sanity Points (SP):

```
Heads chance (%) = 50 + SP      [SP is clamped to −45 … +45]
```

Examples:
- 0 SP (typical battle start): **50%** Heads
- +27 SP (winning fights): **77%** Heads
- −33 SP (bad morale): **17%** Heads

A unit at **−30 SP or lower** risks Low Morale; at **−45 SP** they Panic or enter E.G.O Corrosion. Units without Sanity (most enemies, Abnormalities) always have a fixed **50% Heads** rate.

> **Implication for guides:** The "high roll" (all Heads) is the *ceiling* but not the average. At 0 SP the expected number of Heads for a 3-coin skill is 1.5; each positive SP point shifts this upward. High-SP windows (after win streaks) are when big coin-power skills are most reliable.

#### Coin variants

| Variant | Behavior |
|---------|---------|
| **Standard coin** | Lost if the clash is lost |
| **Unbreakable Coin** (red) | Survives clash loss as a "Cracked" coin; attacks after being hit with Coin Power fixed to ±1 |
| **Excision Coin** (green) | Same as Unbreakable, and also destroys opposing Unbreakable Coins on clash |

### Offensive skills and rotation

Each identity defines three **offensive skill types** on the wiki — **Skill 1**, **Skill 2**, and **Skill 3** — with different power, coin count, and effects. In combat, those types are not each used once per turn; they appear through a **rotation** queue that lasts across many turns.

#### Skill pool per rotation

When a new **rotation** is built for a unit (typically at battle start, and again after the previous queue is exhausted), the game forms a pool of **six offensive slots**:

| Slot in pool | Skill type |
|--------------|------------|
| 3 slots | Skill 1 |
| 2 slots | Skill 2 |
| 1 slot | Skill 3 |

The six entries are **shuffled randomly** into a queue — that unit’s **rotation** until those slots are consumed or the queue resets.

#### What the player sees

When a unit **acts** (its slot in the current turn), the player is shown **two skills** drawn from the front of that queue and must **choose one** to commit (along with targeting). This is the core offensive decision: you rarely have every skill available at once.

**Preview:** If the player uses the selected offensive skill (see advance rules below), they can also see **one additional skill** — the skill that will enter the two-skill choice on a **future** action (a later turn, when that unit acts again). That preview helps plan ahead but does not let you play it early.

#### When the rotation advances

A chosen skill leaves the rotation and the queue moves forward when any of the following happens:

| # | Condition | What advances |
|---|-----------|----------------|
| 1 | An **offensive skill** was selected and a **clash or attack** resolved with it | The **used** offensive skill is consumed from the rotation |
| 2 | A **defensive skill** (Guard / Evade / Counter) was selected and that unit’s action **started** | Rotation advances; see skip rule below |
| 3 | An **E.G.O** was selected and a **clash or attack** resolved with it | Rotation advances; see skip rule below |

**Skip rule (cases 2 and 3):** When advancement is triggered by a defensive skill or E.G.O — not by using an offensive skill from the pair — only the **bottom** of the two skills currently shown in the rotation is **skipped** (removed without being played). The top skill remains for when that unit acts again.

```
Example (simplified):

  Rotation queue:  [S1] [S2] [S1] [S3] [S1] [S2]
  On screen:        TOP: S1    BOTTOM: S2

  Player picks Guard → action starts → bottom (S2) skipped, queue moves on
  Player picks top S1 → clash resolves → S1 consumed, next pair shown
```

#### Implications for guides

- **Skill 1** appears most often in a rotation (three slots) — usually setup, stacking, or chip damage across several turns.
- **Skill 3** appears **once per rotation** — often the strongest finisher or burst. **Use it only when that attack is likely to land**; wasting the single S3 slot on a lost or dodged clash is a major opportunity cost.
- **When to commit Skill 3** — guides should call out favorable windows, for example:
  - Enemy is **Staggered** (cannot clash back when they next act)
  - Another ally is already **clashing** the same target, improving odds or guaranteeing a hit
  - Target has **status effects** that weaken their clash (e.g. Bind, Defense Level Down) or buff yours (Clash Power from passives, Bleed-based `[On Use]` bonuses)
  - Raw **clash numbers** favor you — higher Clash Power / Final Power, Unbreakable Coin, or identity-specific spike conditions are met
- Playstyle text should describe **rotation pressure** and **hit confidence**, not a fixed S1→S2→S3 sequence every time a unit acts.
- Identity kits that change skills mid-battle (e.g. new Skill set in **Flow State**) replace the skill definitions; the same rotation rules still apply to whichever offensive skills are active.

### Stagger

Units have **Stagger Thresholds** at HP percentages (e.g. 65% / 35% / 15%). When damage pushes HP below a threshold the unit becomes **Staggered** — it cannot act for the current and next turn, and all physical resistances change to **Fatal [×2]** for that turn.

If multiple thresholds are crossed in the same turn, the **Stagger Level** rises:

| Stagger Level | Physical resistance multiplier |
|--------------|-------------------------------|
| Stagger | ×2 |
| Stagger+ | ×2.5 |
| Stagger++ | ×3 (maximum) |

Additional ways to trigger stagger: **Tremor Burst** raises a threshold above current HP; being hit while HP is already below an untriggered threshold (even at 0 damage) also staggers.



### Defense skills

In addition to the offensive rotation above, identities have separate **Guard**, **Evade**, and/or **Counter** skills (not part of the 3×S1 / 2×S2 / 1×S3 pool). Choosing a defensive skill can advance the offensive rotation via the skip rule in §2. **Support passives** often interact with defense (e.g. allies who used Guard when they acted trigger an effect).

### What guides should emphasize

For playstyle text, focus on:

- Which skill to prioritize when it **appears in the rotation** (two-choice + preview)
- Whether to spend the lone **Skill 3** slot — only when the attack is **likely to connect** (staggered foe, ally clash, favorable statuses, winning clash stats)
- Which status effects or resources to stack
- State changes (e.g. entering a new mode mid-fight)
- Conditions that gate power spikes (`at 10+ Count`, `if target has 6+ Bleed`)

---

## 3. Identity anatomy

Every wiki identity page maps to the same structural parts. The pipeline extracts these into JSON/markdown.

| Section | What it contains | Guide relevance |
|---------|------------------|-----------------|
| **Header** | Name, rarity, season, traits | Context only |
| **Base stats** | HP, Speed range, Defense Level, stagger thresholds | Survivability, turn order |
| **Key status effects** | Identity-specific mechanics (may replace or augment standard statuses) | **Core concept** — what makes this kit unique |
| **Skills 1–3** | Attack skills with tables and coin effects | **Playstyle** — rotation and conditions |
| **Defense skills** | Guard / Evade / Counter | Defensive role, counterplay |
| **Combat passives** | Always-on or encounter-start rules on this unit | Resource loops, state transitions |
| **Support passive** | Team-wide effect while this identity is deployed | **Team suggestions** — synergy with allies |
| **Sin affinities** | Which sin types this identity uses | Team comp constraints (optional for prototype) |

### On-field roles

Every identity fills one or more **on-field roles** that describe how it participates in combat. Guides should state the role in the opening sentence so experienced players immediately know how to use the identity.

| Role | Description | Examples |
|------|-------------|---------|
| **Damage Dealer** | Primary attacker — skills deal high damage through a resource loop, status cash-out, or strong clash stats | Blade Lineage Salsu Yi Sang (Poise crit), Ring Apprentice Faust (Corpus Ingredient cash-out) |
| **Status Specialist** | Applies or amplifies status effects (Bleed, Burn, Tremor, etc.) to enable teammates who scale off those effects | Magic Bullet Outis (Dark Flame / Burn), Ring Pointillist Student Yi Sang (Bleed + multi-debuff spread) |
| **Support** | The identity's primary value is its **Support Passive** — a team-wide buff active while the identity is deployed. May participate in combat or may spend most turns on Guard/Evade to preserve HP. | Liu Assoc. South Section 3 Yi Sang (SP healing for Burn allies), Ring Nursefather Hong Lu (faction buff + Bleed infliction) |
| **Tank** | Built to absorb hits — high HP, strong Guard/Counter, passives that protect allies (Assist Defense, aggro draw) | Ring Apprentice Faust in Iron Maiden state, identities with Assist Defense |

**Important:** Many identities hold **two roles simultaneously** (e.g. Ring Nursefather Hong Lu is both Support and Damage Dealer). When writing guides, list both, and explain which role the player is prioritising in a given team.

**Support-passive-primary identities:** Some identities are slotted purely to provide their Support Passive and are intentionally kept off the front line. Guides for these identities should note this explicitly and describe when to choose Guard or Evade instead of attacking.

---

### Multi-state identities

Some identities change mid-fight: they gain a new status (e.g. **Flow State**), unlock different skills, or lose an earlier form (e.g. leaving **Iron Maiden**). Guides should call out **when** the transition happens and **how** play changes after it.

### Traits

Traits (e.g. The Ring, Blade Lineage) are tags for factions or archetypes. They matter for passive conditions (“for every The Ring ally on the field”) but are secondary to status-effect synergies for the NLP prototype.

---

## 4. Status effects and triggers

Full definitions live in [`status-effects.md`](status-effects.md). This section covers what the NLP pipeline needs to recognize in text.

### Potency and Count

Many statuses are **double-value**:

- **Potency** — strength of the effect (e.g. Bleed damage per proc)
- **Count** — duration or remaining stacks; often ticks down each turn or each hit

Some effects use a single **Count** or **Stack** only (e.g. **Charge**). Wiki and skill text may say `Inflict 4 Bleed` (both values), `+2 Bleed Count` (duration), or `2 Bleed Potency`.

### Categories

| Category | Examples | Used for |
|----------|----------|----------|
| **Negative** | Bleed, Burn, Tremor, Rupture, Sinking, Bind | “Deal +X% per negative effect on target” |
| **Positive** | Poise, Charge, Protection, Haste | Self-buff scaling, crit setups |
| **Neutral** | Some unique mechanics | Identity-specific rules |

The seven **sin-keyword** statuses (Burn, Bleed, Tremor, Rupture, Sinking, Poise, Charge) are the main archetype labels for clustering and team themes.

### Trigger tags

Skill lines use bracket tags. The NER layer should detect these:

**Before / after the combat phase**

| Tag | Activates |
|-----|-----------|
| `[Turn Start]` | Start of turn, before chaining phase |
| `[Combat Start]` | Start of the combat phase (even if the skill is not used) |
| `[Turn End]` | End of combat phase (even if skill was not used) |

**During the combat phase**

| Tag | Activates |
|-----|-----------|
| `[Before Use]` | Immediately before the skill is used; often replaces it with another |
| `[On Use]` | As soon as the skill engages in a clash or attacks a target |
| `[Clash Start]` | Start of a clash (only if clashing occurred) |
| `[Clash Win]` | When all opponent coins are destroyed |
| `[Clash Lose]` | When all own coins are lost (Unbreakable Coins "crack" instead) |

**During coin usage**

| Tag | Activates |
|-----|-----------|
| `[Coin Start]` | Immediately before this coin is tossed |
| `[On Hit]` | When this coin lands a hit |
| `[Heads Hit]` | When this coin lands a Heads hit |
| `[Tails Hit]` | When this coin lands a Tails hit |
| `[Hit after Clash Win]` | Coin hits after the clash was won |
| `[Hit after Clash Lose]` | Unbreakable/Excision coins only; hits after clash loss |
| `[On Crit]` | Critical hit (from Poise stacks) |
| `[On Kill]` | Any coin defeats a target |
| `[Attack End]` | After all coins have been used |
| `[Current Coin Attack End]` | After this individual coin is used |
| `[Reuse - ■■■]` | Prefixes another tag; **activates only on reused coin flips** |

**Skill property tags**

| Tag | Meaning |
|-----|---------|
| `[Unclashable]` | Cannot be clashed; Defense Skills can still activate against it |
| `[Indiscriminate]` | Can target allies or enemies |
| `[Target Fixed]` | Main target cannot be changed |
| `[Clashable Counter]` | This Defense Skill can initiate a clash |

Conditional phrasing **without brackets** is also common: `at 10+ Corpus Ingredient Count`, `if target has 6+ Bleed`, `for every 4 Bleed on target (max 3)`. These are dynamic checks evaluated each time the condition is tested.

### Unique mechanics

Identities may define custom statuses (e.g. **Corpus Ingredient**, **Iron Maiden**, **Artwork: Fascia**). Treat them like named entities — they are not in the generic Burn/Bleed list but are critical for that identity’s guide.


### Resistances

Every unit has resistance multipliers to the three physical damage types (**Slash**, **Pierce**, **Blunt**) and seven sin affinities (**Wrath**, **Lust**, **Sloth**, **Gluttony**, **Gloom**, **Pride**, **Envy**).

| Name | Multiplier range | Effect |
|------|-----------------|--------|
| **Fatal** | (×1.5, ×2] | +50–100% damage taken |
| **Weak** | (×1, ×1.5] | +1–50% damage taken |
| **Normal** | ×1 | No modifier |
| **Endure** | [×0.75, ×1) | −25% to 0% damage taken |
| **Ineffective** | (×0, ×0.75) | < −25% damage taken |
| **Immune** | ×0 | No damage |

Resistances cannot exceed ×2 without Stagger Levels and cannot fall below ×0.

**Sinner sin resistances** are based on the last E.G.O used that encounter. If no E.G.O has been used, resistances match their equipped ZAYIN E.G.O.

> **Implication for guides:** Attack sin affinity matters when enemies are **Fatal** or **Immune** to specific sin types. For routine encounters, focus on coin count and Coin Power rather than sin matching.
---

## 5. Team-building logic (why synergy matters)

A team in Limbus Company is **7 identities** — one per Sinner slot. Identities do not share a single class role; synergy comes from **mechanic overlap** and **support passives**.

### Common synergy patterns

1. **Inflict → scale** — Ally A’s support passive inflicts **Bleed**; Ally B’s skills deal more damage `for every 4 Bleed on target`.
2. **Same archetype** — Multiple Bleed or Burn identities benefit from shared stagger setups or team passives that reward a sin type.
3. **Resource feeding** — One identity generates **Charge** or a unique resource; another spends or converts it.
4. **Defense coordination** — Support passive triggers when allies use **Guard**; tanky identity draws aggro while others scale.
5. **Speed / stagger** — Slow enemies or staggered enemies enable bonus damage clauses (`enemies whose Speed is slower`, `if Staggered`).

### What the pipeline does

- **Mechanic extraction** — tags statuses and triggers per identity
- **Embedding similarity** — finds kits with similar skill/passive text (same archetype)
- **Rule matching** — links support passives that inflict X to allies that scale off X
- **Guide generation** — names specific teammate **identities** with a one-line rationale (not vague “use a Bleed support”)

### Limits of automated synergy

The prototype does not simulate full teams of 7 or compute exact DPS. Synergy suggestions are **heuristic** — good for demos and direction, not optimal meta rankings.

---

## 6. Out of scope for this project

The following are **not** required to model, scrape, or explain in generated guides:

| Topic | Why out of scope |
|-------|------------------|
| Full damage / clash math per encounter | Offense/Defense Level formulas are documented in §2 above, but computing exact damage requires per-enemy Defense Levels not available at guide-generation time |
| **E.G.O** gear and gacha progression | Separate system from identity kits |
| **Mirror Dungeon** / **Railway** routing | Mode-specific rules, not per-identity |
| **Uptie** / **Synchro** investment | Progression vertical, not kit behavior |
| **Abnormality** fight rules | PvE exceptions; identity pages are Sinner-focused |
| **Sanity / panic** boilerplate | Stripped from parsed pages (shared across identities) |
| Optimal 7-man meta comps | Requires simulation and meta context beyond wiki text |
| PvP or future balance patches | Academic prototype uses static wiki snapshot |

If a guide mentions numbers, they should come **verbatim from extracted wiki data**, not invented math.

---

## 7. Worked examples

These match the three reference identities in [`parsed-ids/`](parsed-ids/). Use them to sanity-check generated guides.

### Example A — Ring Apprentice Faust (complex, multi-state, Bleed + resource)

**Archetype:** Bleed + **Corpus Ingredient** (unique Charge-like resource) + defensive **Iron Maiden** form → offensive **Flow State**.

**State flow:**

```
Encounter start
    → Gain Iron Maiden (tanky, counter-Bleed, Protection)
    → Build Corpus Ingredient via skills / passive (Fascia, My Precious Artwork)
    → Gain Artwork: Fascia at sufficient Corpus Ingredient Potency
    → Turn End: lose Iron Maiden, enter The Self Unbound — Flow State (once)
    → New faster skills; bonus damage vs slower enemies
```

**Playstyle in one paragraph:** Start in Iron Maiden to absorb pressure and reflect Bleed. Stack Corpus Ingredient with Skill 2/3 and passives; at 10+ Count, spend it on Skill 2/3 spikes. After transitioning to Flow State, capitalize on higher Speed and the new skill set against slow targets. Skills scale with Bleed on enemies — pair with allies that help stack Bleed.

**Support passive (team):** **Iron Maiden — Spikes** — allies who used Defense Skills inflict Bleed on attackers → rewards defensive teammates and Bleed teams.

**Synergy hint:** **Ring Pointillist Student Yi Sang** — also Bleed-focused; similar archetype and Bleed stacking.

---

### Example B — Blade Lineage Salsu Yi Sang (simple, Poise-focused)

**Archetype:** Self-contained **Poise** stacking for crit damage.

**Loop:**

```
[On Use] / [On Hit] / [Clash Win] → gain Poise Count
    → Skills and Counter gain +70% damage on Critical Hit
    → Combat passive Poised maintains the crit identity
```

**Playstyle in one paragraph:** Repeatedly use Skill 1 and Skill 2 to build Poise, then cash out with Skill 3 or Counter for critical hits. Little team dependency — guide should not overstate support requirements.

**Synergy hint:** Other Poise identities or generic buffers; no strong inflict→scale link in the parsed kit.

---

### Example C — Ring Pointillist Student Yi Sang (Bleed + random multi-status)

**Archetype:** **Bleed** primary, with random infliction of Burn / Rupture / Tremor / Sinking on coins.

**Scaling:**

- Clash Power and Coin Power scale with **Bleed on target**
- Skill 3 rewards **many negative effect types** on one target (`3+ types`, `every type of negative effect`)

**Playstyle in one paragraph:** Stack Bleed first to unlock clash bonuses. Use Skill 2/3 when the enemy already carries several debuff types. Expect variance from random status infliction — guide can note “wide debuff spread” rather than one fixed combo.

**Synergy hint:** Allies that apply consistent negative effects (not only Bleed) amplify Skill 3; **Ring Apprentice Faust** shares Bleed archetype.

---

## 8. How this primer feeds the NLP pipeline

| Pipeline stage | Uses this primer for | Code / doc |
|----------------|----------------------|------------|
| **Scraping / parsing** | Knowing which sections exist on a wiki page | `docs/301-wiki-identity-parsing.mdc` |
| **NER / mechanics** | Vocabulary in §4 + full list in `status-effects.md` | `src/limbus_guides/nlp/mechanics.py` |
| **Synergy** | Patterns in §5 (inflict → scale, archetype similarity) | `src/limbus_guides/nlp/synergy.py` |
| **Guide generation** | §2–3 playstyle rules, rotation, Skill 3 timing | `src/limbus_guides/domain/context.py` → `nlp/generation.py` |
| **Evaluation** | Human reviewers compare guides to §7 narratives | `docs/evaluation.md`, `data/evaluation/references/` |
| **Presentation** | §1 for professor-facing hook | `docs/final-presentation-outline.md` |

**Runtime:** `GUIDE_WRITING_RULES` in `domain/context.py` is a condensed copy of this doc for LLM prompts. When `USE_OLLAMA=1`, the full primer (truncated) is included as RAG context. Regenerate guides after primer edits: `python scripts/run_pipeline.py`.

---

## 9. Glossary (quick reference)

| Term | Meaning |
|------|---------|
| **Battle** | Full encounter; sequence of all turns |
| **Turn** | Every unit acts once (one skill each, Speed order) |
| **Rotation** | Per-rotation queue: 3×S1, 2×S2, 1×S3, shuffled; player picks 1 of 2 shown when the unit acts |
| **Sinner** | Playable character (12 total) |
| **Identity** | Equippable kit for one Sinner (~172 in game) |
| **Clash** | Skill contest resolved by power stats |
| **Coin** | Sub-segment of an attack skill with its own effects |
| **Support passive** | Team-wide passive while identity is deployed |
| **Stagger** | Break state when HP crosses threshold; levels: ×2 / ×2.5 / ×3 physical resistance |
| **Atk Weight** | Number of targets the skill hits simultaneously (x1/x2/x3); NOT the coin count |
| **Coin count** | Number of numbered rows in a skill's coin-effects table (determines flip count) |
| **Potency / Count** | Strength and duration of many statuses |
| **Sin affinity** | Resource type tied to skills (Wrath, Lust, etc.) |

---

*Edit freely — this is a living doc for the project team. For wiki-accurate effect text, always prefer [`status-effects.md`](status-effects.md) and the official [limbus-company.wiki.gg](https://limbus-company.wiki.gg) pages.*
