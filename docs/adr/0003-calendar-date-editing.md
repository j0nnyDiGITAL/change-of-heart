# ADR 0003 — Calendar / in-game date editing (tiered risk model)

- Status: **Accepted (shipped)** — 2026-09-21
- Extends SAFETY.md rule 10 and state.json frozen-offset D008.

## Context

The editor can tweak stats, money, skills, levels, and inventory in a
`.DAT` but cannot change the in-game date (e.g. 7/26 → 8/22). Community
evidence:

1. **Live mod menus CAN date-travel safely** (in-game "warp to date" /
   calendar features). They do it **inside the engine** by calling the
   game's own calendar functions, which correctly process the transition
   (booked cutscenes, exams, weather, confidant gates).
2. **Raw value edits fail** (community field reports): changing the
   displayed date + Maruki rank on 11/18 → "when I go to sleep it jumps to
   the 19th and starts the infiltration." The scheduler had already
   evaluated the 11/18 gate and booked 11/19.
3. **Story = fixed calendar + set-once event flags.** Every date Apr 1 →
   Mar 31 is pre-scripted: school/exam/story/free/locked slots. Palace
   deadlines are fixed fail-dates. The event-flag matrix records what
   already happened.

Save-space fields (verified in this repo): day counter `0x3D70` (u16,
+1/day), header quick-info text (~0x93, cosmetic), event flags
`0x2F200–0x30700`, activity log `0x17050`.

## Decision

Build date editing as **guarded tiers**, shipping only what can be made
safe with verified offsets:

### Tier 0 — Time Travel Planner (read-only; shipped)
Renders the current date, the fixed master calendar (free/locked/story
days), every remaining Palace/confidant deadline, days-until-deadline, and
gate status. Pure reads + UI. Zero corruption risk.

### Tier 1 — Forward date advance with flag sync (shipped as TIME WARP)
Advance the calendar only when the skip window is provably safe against
the bundled calendar model, or when the crossed story window has verified
branch bits (ADR 0004). Writes: header day fields + `0x3D70` + verified
bits only, re-sign both CRCs, timestamped backup first. UI shows skipped-
date consequences; refuses otherwise.

### Tier 2 — Deadline escape hatch (shipped)
Guided rollback for the classic failure (missed Maruki Rank 9 by 11/18):
restore a pre-deadline backup save, then apply the missing confidant rank
with D016 preserve-surplus semantics, so the game's own scheduled gate
evaluates true legitimately. Reuses the existing backup vault + confidant
write machinery. No event-flag fabrication.

### Tier 3 — Full time warp (shipped as FULL TIME WARP, ADR 0004)
Any-date warp in either direction by syncing clock + palace + event flags
to the destination date in one pass.

### Rejected (do not build)
- **Arbitrary date sets with no flag consistency** — fabricated story
  state risks permanent dead-ends that no checksum will catch.
- **Faith-gate (1/12) escape hatch** — block renumbering 33→36 plus
  third-semester entry flags are entangled with the event matrix (D018).

## Consequences

- Users gain deadline rescue and free calendar movement without the repo
  claiming unsafe powers.
- `0x3D70` semantics across the New Year boundary remain unverified —
  warps stay inside the April–December envelope.
- SAFETY.md rule 10 is amended: day-counter *reads* and guarded writes are
  allowed; blind day-counter writes remain forbidden.

## Verification gate

1. Format rules verified against a corpus of legitimate saves spanning the
   full story (multi-slot chapter saves).
2. Unit tests: skip-window validator vs every calendar day; refuse cases
   (exam/scene/deadline); CRC re-sign roundtrip.
3. In-game load verification of warped saves before release.
