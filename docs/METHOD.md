# Method: How the P5R save format was reverse-engineered

The story of how every offset in this project was mapped — and why the
receipts matter more than the findings.

## The core discipline

**A field is "confirmed" only when a probe or calibration matches in-game
reality.** Until then it's a candidate. This one rule caught every mistake
in the project, including two that would have corrupted saves.

## The toolchain that cracked it

1. **The oracle save.** A 100% NG++ GameBanana save (all confidants rank 10,
   full compendium, third-semester state) became the universal key: one decode
   confirms every previously-inferred offset in minutes instead of weeks of play.
2. **The save ladder.** Fresh (April) → mid (June 15) → oracle (100%) →
   clear data. Monotonic fields reveal themselves across the ladder:
   registration masks only ever gain bits, never lose them.
3. **Replay-save diffs.** Do ONE in-game action → manual save → diff before/after.
   This cracked money, social stats, items, and the confidant block.
4. **The rank-ramp probe.** Write a DIFFERENT distinctive value per entry,
   load once, screenshot — maps every entry ID in one round-trip.
5. **Bit-aligned ladder scans.** For bitmask-shaped data, slide a window at
   every bit offset (not just byte offsets) and score by monotonicity +
   popcount. This is what found the compendium.

## The compendium: a worked example

The compendium was the last unmapped block — **no public tooling maps it**,
and four earlier structural hypotheses failed (including a fabricated
"896-slot × 64-byte array" claim that would have corrupted saves).

The winning scan:
- Consulted two independent AI reviewers (DeepSeek + Gemini) on the *method*
  before scanning — both predicted a persona-ID-indexed bitmask, one
  correctly sized it at 232 bits
- Slid a 232-bit window over the whole payload at every bit offset, both
  endiannesses, scored by "oracle popcount ≈ 232, mid > fresh, monotone"
- Result: `0x09973`, mirror `0x21E83` — 217 set bits in the oracle, all
  mapping to valid persona IDs, monotone across the 7-save ladder

## What the oracles caught (and what they got wrong)

- **Caught:** a claimed compendium layout that decoded to impossible levels
  (302, 861) and junk IDs — rejected against the oracle before any save risk
- **Caught:** a "Maruki flips to Sun's ID at rank 10" claim — the oracle save
  showed id 35 stays 35; id 20 was simply Sun (Yoshida)
- **Wrong (both):** one oracle sized the mask at 454 bits; the other's 232
  was correct. Ground truth — the actual bytes — adjudicates oracle disputes.

## Why AI-assisted RE works here

- The oracles are **cheap second opinions on method**, not sources of truth
- Every claim, from every model, is verified against the executable truth:
  the oracle save, the test suite, the in-game probe
- The fast background relay + thread continuity mean slow reasoning runs
  don't block the workflow

## Ship discipline

- 79/79 tests, including oracle-ladder fixtures that would fail if an offset
  regressed
- Headless GUI smoke test drives every handler against a real save copy
- Exe rebuilds are hash-verified (root = dist)
- Unknown format ⇒ honest `unsupported`, never fabricated writes
