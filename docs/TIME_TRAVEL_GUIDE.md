# TIME TRAVEL GUIDE — Calendar Stage

The **TIME TRAVEL PLANNER** stage gives the editor full control over the
in-game calendar: a read-only planner, two time-warp engines, a deadline
escape hatch, and a palace skip catalog. This guide explains what each card
does, what it writes, and when to use it.

> Every write path takes a **timestamped backup** before touching disk and
> **refuses to run while P5R is open**. Save integrity (AES + dual CRC32) is
> re-signed on every write.

---

## 1. CALENDAR (read-only planner)

A month grid of the fixed P5R schedule with:

- Current save date and weekday
- Free / story / exam / locked day classification
- Every remaining **Palace deadline** and **confidant gate**, with
  days-until-deadline and met/at-risk badges

Nothing here ever writes to the save. Use it to plan before you warp.

## 2. ⏩ TIME WARP (safe route)

**Forward-only** date advance that moves the clock and — when the
destination requires it — a minimal set of story flags.

- Every skipped day is validated against the bundled calendar model
  (`chronos_model.json`). Quiet days pass; story days are refused **or**
  resolved through verified branch bits (shown to you as explicit choice
  cards before anything is written).
- Writes: header date fields, the payload day counter mirror
  (`0x3D70`), and only flags whose save locations are empirically
  verified.
- Envelope: April 1 → December 24 of the current in-game year.

Use this when you want the smallest possible change and an explicit
explanation of every skipped story day.

## 3. 🌀 FULL TIME WARP (any date, forward or backward)

The complete time machine. It rewrites the save so it is **a legitimate
save from the destination date**:

1. Clock fields (header date, payload day counter, engine day fields)
2. **All palace guard + discovery bits** for the destination date
3. **All daily event flags** the calendar model attributes to the
   destination date
4. Re-sign + backup

- **Forward and backward** both work: warping backward clears flags that
  should not exist yet.
- The plan view shows **only the bits that actually change on your save**
  (untouched palaces are omitted), so "7/26 → 8/2" correctly reports one
  palace flag and a handful of daily event flags — not seven palaces.

Use this when you want to land on any calendar date without walking the
story window by window.

## 4. 🚪 DEADLINE ESCAPE HATCH

For the classic tragedy: missing a confidant story gate (Councillor R9 by
11/18, Justice R8 by 11/17). It restores a pre-deadline backup from the
safety vault, applies the missing rank with point-surplus-preserving
semantics, and re-signs — so the game's own gate evaluates true.

The Faith gate (1/12) is deliberately not supported.

## 5. 🏛 PALACE SKIP — two modes

Marks a palace cleared without playing its infiltration or boss fight.
**You choose what happens to the calendar:**

### ⚔ Mode 1 — SKIP GRIND, KEEP CALENDAR (recommended)

For the "Kamoshida in 4 days" playstyle: you did the work early and want
the reward — the rest of the arc as free time.

- Sets the cleared flags; **the clock does not move**.
- The in-game objective becomes "wait for the change of heart" — the
  Thieves' group-chat scenes reflect the claimed clear day by day.
- **Every day between now and the deadline stays playable** (confidants,
  summer events, stat boosts — the Kamoshida arc leaves ~16 of its ~20
  days free; Futaba's leaves ~26).
- The palace's outcome scenes play on their scripted days: change-of-heart
  on the deadline, and for Futaba the awakening window on 8/21–22 — the
  game's own schedule, untouched.

### ⏭ Mode 2 — JUMP TO DEADLINE (one-day compression)

For getting past the entire arc right now.

- Sets the cleared flags **and** warps the clock to the deadline day.
- On arrival the engine takes the cleared branch and plays the
  post-clearance scenes; later pinned scenes play on their days.
- All intervening calendar days are skipped (their events, confidant
  windows and deadlines are gone).

### Which mode do I want?

| You want… | Mode |
|---|---|
| Skip only the dungeon + boss, keep all free days | **Skip Grind** |
| Be done with the arc immediately, don't care about skipped days | Jump to Deadline |
| Maximum story preservation | Skip Grind — nothing is skipped except the palace itself |

Both modes: timestamped backup first, verified flag writes only,
P5R must be closed. The deadline jump cannot be run at/after the deadline
(use the Time Warp cards instead); Grind-skip likewise targets the window
between a palace's earliest entry and its deadline.

---

## Safety model (what the engines will never do)

- **No scene fabrication.** The engines never invent cutscene state; they
  set the state bits the game checks and let the game play its own scenes.
- **No unverified writes.** Every flag write maps to a save location that
  has been verified against a corpus of legitimate saves; unknown bit
  tables hard-fail instead of guessing.
- **Fail-closed planning.** A plan that cannot be fully validated is
  refused with the exact blocking dates — never half-applied.
- **Informed consent.** Story-window warps show which branch will be
  taken and why before you can execute them.

## Format notes (for maintainers)

- Header `day` = 0-based day index from April 1 (verified across the
  whole save corpus, including January saves).
- Payload `0x3D70` = `max(0, hdr.day − 52)` through 12/31; the rule
  breaks across New Year, so warps stay inside the verified envelope.
- Event-flag matrix at `0x2F200`: 12 tables × 3072 bits, no `+0x18510`
  mirror (single copy). Table-2 flat transform: `0x1C700 + index`.
- The engine reads the calendar from the save and runs that date's
  schedule regardless of story history; mismatched flags surface as
  in-game overlay warnings, which is why full-sync warps work in both
  directions.
