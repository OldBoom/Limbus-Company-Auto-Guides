# Status Effects Reference

Source: [limbuscompany.wiki.gg/wiki/Status_Effects](https://limbuscompany.wiki.gg/wiki/Status_Effects)

---

## Value Modes

Status effects use up to two values:

| Mode | Values | Notes |
|------|--------|-------|
| Zero-value | Fixed at 1 | No inherent strength scaling |
| Single-value | Count, Stack, or Value | Removed when value reaches 0 |
| Double-value | Potency + Count | Potency = strength, Count = duration. Removed when either reaches 0 |

If both values exist, Potency displays bottom-left, Count displays bottom-right.

Values are consumed before they are gained or inflicted.

**Max Value** default: 99.

---

## Effect Categories

| Category | Color | Gameplay relevance |
|----------|-------|--------------------|
| Positive | Yellow | Counts as positive for conditional effects |
| Neutral | Brown | Neither positive nor negative |
| Negative | Red | Counts as negative for conditional effects (e.g., "deal +X% for every negative effect") |

---

## Core Keywords

Seven keyword status effects tied to sin affinities.

### Burn

**Type:** Negative (Double-value: Potency + Count)

At the end of the turn, take fixed damage by the effect's Potency, then reduce its Count by 1.

### Bleed

**Type:** Negative (Double-value: Potency + Count)

When tossing an attack Coin, take fixed damage by the effect's Potency. Then, reduce its Count by 1.

### Tremor

**Type:** Negative (Double-value: Potency + Count)

When attacked by skills that burst Tremor, raise the Stagger Threshold by the effect's Potency. At the end of the turn, reduce the Count by 1.

**Related:** Tremor Burst — Raise target's Stagger Threshold by Tremor Potency on target.

### Rupture

**Type:** Negative (Double-value: Potency + Count)

When hit by an attack, take fixed damage by the effect's Potency. Then, reduce its Count by 1.

### Sinking

**Type:** Negative (Double-value: Potency + Count)

When hit by an attack, take fixed SP damage by the effect's Potency (applies as Gloom-affinity damage to Abnormalities). Then, reduce its Count by 1.

### Poise

**Type:** Positive (Double-value: Potency + Count)

On hit, gain a Potency-based chance to deal critical damage, reducing the Count by 1 if successful. At the end of the turn, reduce the Count by 1. Critical hits deal 1.2x damage.

### Charge

**Type:** Positive (Single-value: Count, max 20)

Resource used by certain skills for additional effects. Count lowers by 1 at the end of each turn.

---

## Standard Buffs (Universal)

### Power & Level Buffs

| Effect | Description |
|--------|-------------|
| Power Up | All skills gain Final Power by Count for one turn |
| Attack Power Up | Attack skills gain Final Power by Count for one turn |
| Defense Power Up | Defense skills gain Final Power by Count for one turn |
| Clash Power Up | Gain Clash Power by Count for one turn |
| Base Power Up | Raise Base Power of Skills by Count |
| Offense Level Up | Offense Level increases by Potency for one turn |
| Defense Level Up | Defense Level increases by Potency for one turn |

### Speed & Damage Buffs

| Effect | Description |
|--------|-------------|
| Haste | Speed increases by Count for one turn |
| Damage Up | Deal +10% damage with skills per Count for one turn (max 10) |
| Protection | Take -10% damage per Count from attacks for one turn (max 10) |
| Crit DMG Up | Deal +10% damage on Critical Hit per Stack for one turn |

### Coin Modifiers

| Effect | Description |
|--------|-------------|
| Plus Coin Boost | Raise Power of Plus Coins by Count for one turn |
| Minus Coin Drop | Reduce Power of Minus Coins by Count for one turn |

### Other Buffs

| Effect | Description |
|--------|-------------|
| HP Healing Boost | Increase HP healing from Passives, Skills, and Coin effects by +10% per Count (max 5) |
| Weak-resist DMG Boost | Boost damage against Weak resistances by +1% per Count for one turn |
| E.G.O Resource Amp | Increase E.G.O resources earned from skills by Count for one turn |

---

## Standard Debuffs (Universal)

### Power & Level Debuffs

| Effect | Description |
|--------|-------------|
| Power Down | All skills lose Final Power by Potency for one turn |
| Attack Power Down | Attack skills lose Final Power by Potency for one turn |
| Defense Power Down | Defense skills lose Final Power by Potency for one turn |
| Clash Power Down | Lose Clash Power by Potency for one turn |
| Offense Level Down | Offense Level decreases by Potency for one turn |
| Defense Level Down | Defense Level decreases by Potency for one turn |

### Speed & Damage Debuffs

| Effect | Description |
|--------|-------------|
| Bind | Speed decreases by Potency for one turn |
| Damage Down | Deal -10% damage with skills per Count for one turn (max 10) |
| Fragile | Take +10% more damage from skills per Count for one turn (max 10) |

### Coin & Misc Debuffs

| Effect | Description |
|--------|-------------|
| Paralyze | Fix the Power of X Coin(s) to 0 for one turn |
| Plus Coin Drop | Reduce Power of Plus Coins by Count for one turn |
| Minus Coin Boost | Raise Power of Minus Coins by Count for one turn |
| HP Healing Down | Decrease HP healing from Passives, Skills, and Coin effects |
| Poison | Turn End: take fixed damage by Count, then halve Count |
| Immobilized | Does not act for this turn |

---

## Typed Modifier Effects

Effects that scale damage dealt/taken by damage type or sin affinity.

### DMG Up (Positive)

Deal +10% damage per Count with the specified skill type for one turn (max 10).

| Damage Type | Sin Affinity |
|-------------|-------------|
| Slash DMG Up | Wrath DMG Up |
| Pierce DMG Up | Lust DMG Up |
| Blunt DMG Up | Sloth DMG Up |
| | Gluttony DMG Up |
| | Gloom DMG Up |
| | Pride DMG Up |
| | Envy DMG Up |

### Power Up — Typed (Positive)

Skills of the specified type gain Final Power by Count for one turn.

| Damage Type | Sin Affinity |
|-------------|-------------|
| Slash Power Up | Wrath Power Up |
| Pierce Power Up | Lust Power Up |
| Blunt Power Up | Sloth Power Up |
| | Gluttony Power Up |
| | Gloom Power Up |
| | Pride Power Up |
| | Envy Power Up |

### Protection — Typed (Positive)

Take -10% damage per Count from the specified skill type for one turn (max 10).

| Damage Type | Sin Affinity |
|-------------|-------------|
| Slash Protection | Wrath Protection |
| Pierce Protection | Lust Protection |
| Blunt Protection | Sloth Protection |
| | Gluttony Protection |
| | Gloom Protection |
| | Pride Protection |
| | Envy Protection |

### DMG Down (Negative)

Deal -10% damage per Count with the specified skill type for one turn (max 10).

| Damage Type | Sin Affinity |
|-------------|-------------|
| Slash DMG Down | Wrath DMG Down |
| Pierce DMG Down | Lust DMG Down |
| Blunt DMG Down | Sloth DMG Down |
| | Gluttony DMG Down |
| | Gloom DMG Down |
| | Pride DMG Down |
| | Envy DMG Down |

### Power Down — Typed (Negative)

Skills of the specified type lose Final Power by Count for one turn.

| Damage Type | Sin Affinity |
|-------------|-------------|
| Slash Power Down | Wrath Power Down |
| Pierce Power Down | Lust Power Down |
| Blunt Power Down | Sloth Power Down |
| | Gluttony Power Down |
| | Gloom Power Down |
| | Pride Power Down |
| | Envy Power Down |

### Fragility (Negative)

Take +10% damage per Count from the specified skill type for one turn (max 10).

| Damage Type | Sin Affinity |
|-------------|-------------|
| Slash Fragility | Wrath Fragility |
| Pierce Fragility | Lust Fragility |
| Blunt Fragility | Sloth Fragility |
| | Gluttony Fragility |
| | Gloom Fragility |
| | Pride Fragility |
| | Envy Fragility |

### Resist Down (Negative)

Increase resistance value by 0.1 per Count (higher resistance = more damage taken).

| Damage Type | Sin Affinity |
|-------------|-------------|
| Slash Resist Down | Wrath Resist Down |
| Pierce Resist Down | Gloom Resist Down |
| | Envy Resist Down |

---

## Neutral Effects (Universal)

| Effect | Description |
|--------|-------------|
| Aggro | More likely to be targeted by enemies |
| Unbreakable Coin | Coin does not break on Clash Lose. If an Attack Skill has this Coin, attack with it after getting hit. On Clash Lose, fix Coin Power to 1 |

---

## Unique Keyword Variants

Identity-specific variants of core keywords. Each functions as its parent keyword for interaction purposes unless noted otherwise.

### Unique Burn

| Effect | Description | Source |
|--------|-------------|--------|
| Dark Flame | Max 7. Target loses Defense Level equal to value. Turn End: deal (Value x Burn Potency) Pride damage, then expires | Magic Bullet Outis |
| Shattered World | Max 1. Take x1.2 Burn damage. Take +10% from Yi Sang's Wrath/Gloom Base Attacks. Expires Turn End | Great Trichiliocosm Yi Sang E.G.O |
| Spore | Max 15. Turn End: +1 Burn Count per 5 Stack. Gain 1 Bind next turn | Hornet Meursault E.G.O |
| Resident Reg. Microchip | Max 2. Take +10% from Wrath/Envy. On Clash Lose, gain 1 Burn. Lose 1 Stack Turn End | Move-in Reg. Heathcliff E.G.O |
| Searing Birdcage | Max 5. If unit has Burn, Wrath Resistance +0.1 per Stack. Turn End: Bind equal to Stack, halve Stack | Indicant's Trial Rodion E.G.O |

### Unique Bleed

| Effect | Description | Source |
|--------|-------------|--------|
| Nails | Turn Start: apply 1 Bleed, increase Bleed Count by this effect's Count. Turn End: halve Count | N Corp. Fanatics |
| Red Plum Blossom | Max 10. +10% crit chance against this unit. On Critical Hit, gain Bleed and take +(value x 3)% crit damage | Blade Lineage Salsu Faust |
| Needle | When taking Envy damage, +1 Bleed Count. Turn End: gain 1 Bleed. Lose 1 Stack per trigger | Scissors Outis E.G.O |
| Lodged Arrow | Max 4. Turn Start: gain Bleed Potency by Stack, lose Defense Level by Stack | Shi East Section 3 Faust |
| Corpus Theater (Hong Lu) | Base 3. When gaining Bleed from enemy Skills, randomly gain Bleed/Bind/Defense Power Down and lose 1 Stack | Ring Nursefather Hong Lu |
| Sewing Target | Max 1. Take +0.5% more damage per Bleed on self (max 10%). Lose 1 Turn End | Barber of La Manchaland Outis |
| Polydipsic Rose | Max 5. Turn End: at 10+ Bleed Potency, take Lust damage equal to 1% max HP (max 30). Lose 1 Turn End | Yearning-Mircalla Don Quixote E.G.O |
| Rose Wedge | Max Potency 10, Max Count 4. Gain Potency per 10 Bleed damage taken. Amplifies Bleed and reflects to attacker | Yearning-Mircalla Meursault E.G.O |
| Maggots | Turn End: take Gluttony damage by Count, +1 Bleed Count, lose 1 Count | Legerdemain Gregor E.G.O |

### Unique Tremor

| Effect | Description | Source |
|--------|-------------|--------|
| Tremor - Decay | Lose 1 Defense Level per 4 Tremor Potency on self | Oufi South Section 3 Heathcliff |
| Tremor - Fracture | At 20+ (Tremor Potency + Count), raise Stagger Level by 1 | Binds Outis E.G.O |
| Tremor - Reverb | On Tremor Burst, take Sloth damage equal to Tremor Potency | District 20 Yurodivy Hong Lu |
| Tremor - Everlasting | On Tremor Burst, (Tremor Potency)% and (Tremor Count)% chance for additional Tremor Burst (max 50% each) | Everlasting Faust E.G.O |
| Tremor - Chain | Lose 1 Clash Power per 10 Tremor Potency (max 3) | T Corp. Class 3 Don Quixote / Outis |
| Tremor - Scorch | On Tremor Burst, take Wrath damage equal to (Tremor + Burn Potency / 2), lose 1 Burn Count | Thumb East Capo IIII Meursault |
| Tremor - Hemorrhage | On Tremor Burst, take Lust damage equal to (Tremor + Bleed Potency / 2), lose 1 Bleed Count | Night Awls Capitano Gregor |
| Tremor - Superposition | Gained through Amplitude Entanglement. Combines multiple Tremor types | Quantum effects |
| Time Moratorium | Stores all damage; on expiry, triggers Tremor Burst with (100 + Stack x 15)% stored damage as Sloth damage | T Corp. Identities |

### Unique Sinking

| Effect | Description | Source |
|--------|-------------|--------|
| Butterfly | Max 15. "The Living" (Potency) and "The Departed" (Count). On hit, attacker heals SP. At negative SP, takes Gloom damage. Turn End: resets, converts Living to Departed | Solemn Lament Yi Sang E.G.O |
| Sheut Fracture | Max 10. Take +1% from Sloth/Gloom per Stack. At max, gain Gloom Fragility and take Gloom damage equal to Sinking Potency | LCA Udjat Outis |
| Sinking Deluge | Deal SP damage by (Sinking Count x Potency), then remove Sinking. At -45 SP, excess SP damage becomes Gloom HP damage | Spicebush Yi Sang E.G.O |
| Faint Aroma | Max 30. Gain 1 Stack per Sinking damage taken. At max, gain 2 Tremor, trigger Tremor Burst, take Gloom damage | Faint Aroma & Solitude Ryoshu E.G.O |
| The Uninvited | Max 2. On death, attacker heals 3 SP and a random ally gains 2 Stacks. Take +0.5% per Sinking (max 10%) | Bygone Days Ishmael E.G.O |

### Unique Charge

| Effect | Description | Source |
|--------|-------------|--------|
| Photoelectricity | Max 3. When hit, attacker gains Charge Count equal to value. At 5- Charge Count, +3 additional. Expires Turn End | MultiCrack Heathcliff |
| Spark Discharge | When hit, attacker gains +1 Charge Count. When hit with Gloom, gain +1 Rupture Count. Lose 1 Count | AEDD Gregor E.G.O |
| Charged Sting | Max 5. Take +4% damage per Stack from Skills that gain/consume Charge (max 20%). Envy Skills: +8% per Stack (max 40%) | AEDD Gregor E.G.O |

### Unique Rupture

| Effect | Description | Source |
|--------|-------------|--------|
| Lasso | Max 3. Turn End: gain Rupture Potency equal to current Speed (max 5), gain 1 Bind next turn. Lose 1 Turn End | Lasso E.G.Os |
| Concussion | Max 2. Multiply Stagger Threshold raised and Rupture damage by 1.2. Lose 1 Stack Turn End | Wu Branch Yi Sang |
| Open Wound | Max 2. Turn End: gain 1 Bind. At 2 Stack, replace with Deep Wound | Night Awls Capitano Gregor |
| Talisman | Max 6. On Hit, consume 1 Rupture Count to inflict Rupture. When hit, gain Rupture and lose Stack. At 6+ Stack, take fixed damage | Red Sheet Sinclair E.G.O |
| Twisted Curse Talisman | Max 10. At 10+ Stack with 30+ damage: +1 Rupture Count, take Gluttony damage. On expiry, gain Attack Power Down | Red Sheet Don Quixote E.G.O |

---

## Panic-Type Changing Effects

These effects alter a unit's Panic behavior.

| Effect | Source | Key mechanic |
|--------|--------|-------------|
| Echoes of the Manor | Wuthering Heights Outis / Faust | 50% chance +1 Sinking Count. Panic inflicts self to 2 allies |
| Impending Ruin | Wild Hunt Heathcliff | Low Morale: +3 Sinking Turn End, -1 Clash Power. Panic: +5 Sinking, -2 Clash Power |
| Shattermark | Heishou Pack Wei Branch | Take +10% from Gluttony/Gloom. Panic: Clash Power -2, Defense Level -3 |
| Blue Sand | LCA Udjat Outis | On Clash Lose, +1 Sinking Count. Panic: Clash Power -2, Speed -1 |
| Dazzle | Lamp Gregor E.G.O | Take +0.5% per (Sinking + Burn). Panic: Bind and Offense Level Down Turn End |
| Solitude | Faint Aroma & Solitude Ryoshu E.G.O | Take +10% from Gloom. Panic: +3 Sinking Count Turn End |

---

## Keyword-Related Buffs (Identity-Specific)

| Effect | Source | Key mechanic |
|--------|--------|-------------|
| Bloodflame | Heishou Pack You Branch | Max 3. +1 Burn and Rupture Potency with Base Skills |
| Fanatic | N Corp. Fanatics | +Final Power by Count against targets with Nails |
| Blooming Thorn | Princess of La Manchaland Rodion | Max 10. +1 Defense Level per 2 Stack. When hit, inflict Bleed |
| Festive Fever | Princess of La Manchaland Rodion | Max 10. +1.5% damage per Stack against Bleed targets |
| Shimmering (Bloodfiend) | Manager of La Manchaland Don Quixote | Max 50. Converts Shield Bleed damage to Bloodfeast |
| Dark Cloud Blade | Kurokumo Clan Captain Ishmael | Max 1. +1 Slash Power, inflict 1 Bleed On Hit with Slash |
| Battle Ready | Kurokumo Clan Captain Ishmael | Max 1. +1 Bleed Potency/Count, gain Slash Power Up and Slash DMG Up |
| Strider (Wu) | Heishou Pack Wu Branch | Max 3. Turn End: +2 Haste, inflict Tremor before attack |
| Rupture Protection | Molar Boatworks Fixers | Take -1 Rupture damage per Count |
| Burgeoning of Horns | Heishou Pack Wei Branch | Max 3. +1 Rupture and Sinking Potency with Base Skills |
| Wild Hunt | Wild Hunt Heathcliff | Survive with 1 HP, revive at Turn End. On death, inflict 3 Sinking |

---

## Keywordless Buffs (Identity-Specific)

| Effect | Source | Key mechanic |
|--------|--------|-------------|
| Contempt of the Gaze | N Corp. Contempt, Awe Ryoshu | +7% damage per Gaze of Contempt |
| Sword of the Homeland - Rending | Blade Lineage Mentor Meursault | Skill 1 gains Final Power by Count |
| Sword of the Homeland - Penetrating | Blade Lineage Mentor Meursault | Skill 2 gains Final Power by Count |
| Erudition | Dieci South Section 4 Director Meursault | Max 6. Discarding a Skill grants Shield |
| Hardblood Armor | Prince of La Manchaland Meursault | Max 5. Heal 10% of HP damage dealt |
| Focused Performance | Prince of La Manchaland Meursault | Max 3. S1/S2: +1 Final Power, +5% per Stack. S3: +2 Final Power, +10% per Stack |
| Tarnished Blood | Lord of Hongyuan Hong Lu | Max 5. Turn End: take 20% HP damage per Stack |
| Somatic Frisson-inspiring Melody | Ring Nursefather Hong Lu | Speed +1, Base Attack Skills: Clash Power +1, +10% damage |
| Fell Bullet | N Corp. Fell Bullet Yi Sang E.G.O | Max 1. +3% crit damage per Torn Memory. On Hit, inflict 1 Bleed |
| Linebreaker | Wu Branch Yi Sang | Max 5. Turn Start: gain (Stack x 10) Shield. At max: +2 Final Power |
| Iron Maiden | Ring Apprentice Faust | +4 Aggro leftmost Slot. Turn Start: Protection + Defense Level Up + Shield. Reflects Pierce damage on last Coin hit |
| Overcharge | W Corp. L4 CCA Heathcliff | Max 1. Immobilized. Take less damage based on Charge. Gain Charge and Shield |
| Gebura's Blade | Durante (story) | Unbreakable Coins, +100% damage, survive at 10 HP, heal on hit |

---

## Keywordless Debuffs (Identity-Specific)

| Effect | Source | Key mechanic |
|--------|--------|-------------|
| Mark of Decay | Heishou Pack Mao Branch Faust | Max 1. Take +10% from Gluttony Skills and Deathrite |
| Sewing Target | Barber of La Manchaland Outis | Max 1. Take +0.5% more per Bleed (max 10%) |

---

## Neutral Effects (Identity-Specific)

These effects are classified as neither positive nor negative.

| Effect | Source | Key mechanic |
|--------|--------|-------------|
| Corpus Ingredient | Ring Apprentice Faust / Ring identities | Unique Charge. Max Count 20. Lose 1 Count Turn End |
| Artwork: Fascia | Ring Apprentice Faust | Scales Base Power and effects based on Corpus Ingredient Potency |
| Bloodfeast | La Manchaland identities | Resource consumed/gained through Bleed interactions |
| Torn Memory | Fell Bullet E.G.Os | Max 7. Used for certain Skills |
| K Corp Ampule | K Corp. Hong Lu | Turn Start: at less than 4 Count, heal (Count x 5)% max HP. At 4+ Count, unit dies |
| Discard | Dieci identities | Resource mechanic for discarding skills |
| Insight | Dieci identities | Resource interacting with Discard and Erudition |
| Procuration (Hermes) | Index Nursefather Yi Sang | Max 9. At 9 Stack, unlock a powerful Skill |
| Tianjiu Star's Blade | Heishou Pack Mao Branch Faust | Max 20. At 10+ Stack: +1 Haste Turn End |
| Arrow (Shi) | Shi East Section 3 Faust | Max 4. Arrows spent by certain Skills |
| Magic Bullet | Magic Bullet Outis | Max 7. Scales Skill 3 Base Power and Coin Power |
| Responsibility | Manager of La Manchaland Don Quixote | Max 1. Clash Power +1, deal +20%, take +20% |
| Surgery | Screwloose Wallop Meursault E.G.O | Die at Count 5. -20% max HP per Count, +20% damage per Count |

---

## Deathrite Variants

Deathrite effects interact with Rupture and trigger on specific conditions.

| Effect | Source | Trigger |
|--------|--------|---------|
| Deathrite - Haste | Heishou Pack | Rupture triggered by attacker with 10+ Speed |
| Deathrite - Enfeeble | Heishou Pack | Rupture triggered while unit has Attack Power Down or Offense Level Down |
| Deathrite - Fissure | Heishou Pack | Rupture triggered while unit has 15+ Tremor |
| Deathrite - Halt | Heishou Pack | Rupture triggered while unit has Bind |
| Deathrite - Impede | Heishou Pack | Rupture triggered after being hit by a Skill with Clash Power lowering effects |
| Deathrite - Venom | Heishou Pack | On Rupture trigger, take Gluttony damage equal to Rupture Potency |
| Deathrite - Wane | Heishou Pack | Rupture triggered while unit has a debuff that reduces damage dealt |
