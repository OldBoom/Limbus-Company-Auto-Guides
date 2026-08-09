# Wiki mechanic reference

Raw wikitext of the Limbus Company wiki's own mechanic pages. Refresh with
`python scripts/fetch_wiki_reference.py` (`--list` shows what is tracked and why).

## What these are for

**These pages define what a mechanic does. They are the ground truth for any rules claim a
generated guide makes.**

`docs/parsed-ids/*.md` is a different kind of source. It is per-identity skill text, and it
answers only *which identities have mechanic X* — never *what X does*.

That distinction is not academic. An audit of the guide templates once concluded "Nails is a
Tremor mechanic" because N Corp. kits apply Nails and Tremor on the same coins. It is not:

> `Bleed.wiki` — "Bleed has several related effects, most notably Nails and Bloodfeast.
> Nails is a source of Bleed."

Co-occurrence in a skill means one kit applies both. It says nothing about the mechanics'
relationship. The same mistake produced "Paralyze ... they cannot clash back", when the page
says:

> `Paralyze.wiki` — "a debuff that fixes the value of Coins to 0 (effectively fixing Tails
> chance to 100%), regardless of Sanity. One Stack of Paralyze is spent for each Coin"

A Paralyzed unit still acts and still clashes — with dead coins.

## Rule of thumb

Before writing or reviewing any sentence in `src/limbus_guides/nlp/` that names a game
mechanic, check that mechanic's page here. If the claim is not supported by one of these
pages or by `docs/status-effects.md`, do not make it.

Identity-specific mechanics deserve particular care: a name appearing in one identity's kit
(Gambit, Blessing, Courier Trunk) must never be phrased as general advice.
