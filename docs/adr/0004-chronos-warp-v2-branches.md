# ADR 0004 — CHRONOS warp v2/v3: branch-bit selection & full flag sync

- Status: **Accepted (shipped)** — 2026-09-21/22
- Extends: ADR 0003 (tiered risk model)
- Empirical basis: bundled calendar model (`web-app/static/chronos_model.json`)
  + a multi-slot corpus of legitimate saves spanning the full story.

## Context

CHRONOS v1 refuses any warp whose skip window contains a day whose schedule
fires non-ambient story events. That makes 8/21+ unwarpable from 7/26: the
Futaba awakening window begins. Warp v2 instead **resolves the branches the
skipped story days would have evaluated**, lets the user acknowledge the
outcome the game itself branches on, and lets the engine play the rest live
on arrival. Warp v3 generalizes this into a full time machine (any date,
both directions) by syncing all palace + event flags in one pass.

Key facts (calendar model + save corpus):

- The deadline day for Futaba's Palace (8/21) branches on a single
  persistent bit — table-2 index 1400, "Palace secured". Set: cleared branch
  (decision scenes + join chain). Unset: failure branch. The engine never
  re-evaluates history — only current bits.
- The 8/22 awakening ceremony chain is **unconditional** in the calendar
  model — the engine plays it live on arrival; nothing needs fabricating.
- Table-2 bit transform (verified across the whole corpus): flat bit =
  `0x1C700 + index`, LSB0. The guard bits are era-perfect: 0 in every
  pre-window save, 1 in every post-window save.
- Table-2 index 1410 is written by the game (never cleared by the schedule);
  a warp that claims the palace cleared must set it, or morning bookkeeping
  misclassifies the era.
- The event-matrix region has **no** `+0x18510` mirror — single copy,
  primary writes only, then re-sign.

## Decision

1. **WINDOW catalog** (code constants, each with verified bit ids and
   branch semantics). Exactly one window ships verified: Futaba awakening
   (7/26–8/31, resolution bits T2+1400 + T2+1410). Windows with unverified
   branch bits (Okumura, Niijima, Shido, Maruki gate) stay in the catalog as
   `verified: false` so the UI can honestly say "not yet warpable" instead
   of silently refusing.
2. **Plan v2** (`build_time_travel_plan_v2`): walk the skip window exactly as
   v1. v1-blocked days inside a *known* window resolve to
   `status: "blocked_resolvable"` + a list of `branch_choices`:
   - `kind: "implied"` — forced by the destination (crossing 8/21 to reach
     8/22+ implies the palace cleared; no user decision exists).
   - `kind: "user"` — real game branches with verified bits, offered to the
     user with their consequences.
   Unknown story days outside any window remain hard-refused (v1 behavior).
3. **Apply v2** (`apply_time_travel_v2`): writes ONLY the clock fields
   (header day + desc date token, `0x3D70` mirror) plus branch bits from the
   user-confirmed resolution — each via the verified transform, hard-failing
   on any bit lacking verification data (BANK RULE). The caller re-signs
   (dual CRC + AES) with backup-before-write.
4. **Warp v3** (`apply_full_time_warp`): the FULL TIME WARP card. Sets clock
   fields + ALL palace guard/discovery bits + all daily event flags for the
   destination date, supporting **backward** warps (pre-target flags are
   cleared). Plan output reports only bits that actually change on the
   current save (`plan_full_time_warp_changes`).

## Rejected alternatives

- **Emulating event side effects into the save**: the arrival-day scheduler
  re-triggers the same chain; double-application risk with zero upside. The
  engine plays scenes natively — we only pre-set the bits it *checks*.
- **Writing unverified bits**: violates the BANK RULE — only bits with
  corpus-verified save locations may be written.
- **Keeping v1's refusal for cross-window destinations**: users needs
  destinations *past* a window, not just up to it; refusing there made the
  feature useless for its primary use case.

## Consequences

- 7/26 → 8/21 and beyond become warpable with explicit user consent on the
  implied branch ("Futaba's Palace counts as secured — awakening plays on
  arrival").
- Every future window is a data-only addition: window bounds, branch bits,
  corpus verification. No new write machinery.
- User-facing behavior of both engines is documented in
  `docs/TIME_TRAVEL_GUIDE.md`.
