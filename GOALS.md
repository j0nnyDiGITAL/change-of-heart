# GOALS -- P5R Save Editor (Change of Heart): goals + current plan (realign here)

> **Realign here** -- after compression or a fresh session, re-sync with: (1) project **goals**,
> (2) the **current plan** (Phases below), (3) *where I am right now / do-this-next**.

> **THE LOOP (you are mid-loop -- re-enter here):**
> 1. Read **CURRENT POSITION** -> 'do this next'.
> 2. Do that one step.
> 3. Hit its gate (empirical pass/fail).
> 4. **Update this file IMMEDIATELY after each completed item** -- mark `[x]`, advance **CURRENT POSITION**, append to **Progress Log**. Do NOT batch updates to phase end.
> 5. **Sync the state ledger after EVERY completed item:** update `state.json` (`phase`, `gate`, `next_action`, `updated_at`) + `STATUS.md`. Never let the ledger lag more than one item.
> 6. **Crash-safety rule:** before starting ANY long-running operation (capture, build, benchmark), the ledger must already reflect the COMPLETED prior state. If the process dies mid-operation, on-disk ledger = last completed item, never the in-flight one.
> 7. Phase gates all green? -> run the next planning phase -> loop into the next phase.


## CURRENT POSITION -- realign here, then act
- **Milestone:** Scaffolding upgrade to AIY-OS standards (Schema v2, GOALS.md, Invariant Guardian) & resume Ground-Up Redesign.
- **You are at:** Implementation phase (Scaffolding alignment active on main).
- **Last done:** Save backup ZIP generation fix verified across local and uploaded saves (178/178 tests green, v1.1.2 baseline).
- **Do this next:** Complete AGY-OS scaffolding sync (scripts/check-invariants.py, state.json schema v2, STATUS.md auto-sync header, AGENTS.md update).
- **DONE WHEN:** `python scripts/check-invariants.py` passes with all 4 gates green, schema v2 active, and 178/178 unit tests pass.
- **Live caveats (trust, don't re-verify):** Full-bleed redesign work is safely preserved on branch `redesign/p5r-native-menu`; `main` maintains the stable v1.1.2 release baseline.


## Project goals (durable)
- **Authentic P5R Experience:** Deliver a 100% faithful, mouse-driven Persona 5 Royal save editor & compendium studio matching in-game visual aesthetics and layouts.
- **Flawless Binary Fidelity:** Cryptographically verified AES-256-CBC and dual CRC32 re-signing across primary (`0x09973`) and mirror (`0x21E83`) offsets without data corruption.
- **Complete Feature Suite:** Granular compendium (100% genuine unlock), 10-category master inventory, confidant progress & romance toggles, party evolution tiers, and automatic immutable ZIP backups.


## Phase Plan

### PHASE 1 -- AGY-OS Scaffolding Alignment
- [ ] Upgrade state.json to Schema v2 with `check_commands`, `banned_patterns`, and `human_gate`.
  - **Gate:** `python scripts/check-invariants.py` validates schema v2.
- [ ] Upgrade `scripts/check-invariants.py` with auto-sync, auto-migration, and banned pattern checks.
  - **Gate:** `python scripts/check-invariants.py --sync` executes cleanly.
- [ ] Rescaffold `AGENTS.md` and `STATUS.md` to latest AGY-OS Tier 2 standards.
  - **Gate:** Invariant check passes 100% with no missing files or desyncs.


3## PHASE 2 -- Ground-Up P5R UI Redesign (`redesign/p5r-native-menu`)
- [ ] Stage 1: Full-Bleed Joker Status Canvas (character cutout on canvas, angled polygonal shards, tactile stat controls).
  - **Gate:** Headless UI capture matches reference `27809.jpg` / `76684.jpg`.
- [ ] Stage 2: Compendium & Velvet Room Register (blue accent theme, 232-record view).
  - **Gate:** Compendium toggle and batch unlock verified against reference `228140.jpg`.
- [ ] Stage 3: Airsoft Shop Inventory Overhaul (Iwai lime theme, 10-pocket layout).
  - **Gate:** Matches reference `89783.jpg` / `26113.jpg`.
- [ ] Stage 4: Confidants & Bond Dossier (gold accent theme, character dossiers).
  - **Gate:** Confidant rank & surplus preservation UI validated.


## Progress Log
- 2026-09-02: Rescaffolding project according to AGY-OS Tier 2 standard (GOALS.md initialized).
- 2026-08-26: Fixed save backup ZIP creation bug for uploaded/custom save files (`create_memory_backup_zip` + auto-download on save). Preserved redesign on `redesign/p5r-native-menu` branch and restored stable v1.1.1 baseline to `main`. 178/178 tests green.
- 2026-08-25: Ground-up Native Menu Engine -- eliminated left sidebar, expanded canvas to 100vw full-bleed viewport, wired bottom ribbon navigation ticker (ref: 12558.jpg / 63559.jpg). 176/176 tests green.
- 2026-08-24: Fixed bond-points wipe bug +zamasu2020, r/Persona5Royale). 174/174 tests green.
- 2026-08-24: UI-liveness watchdog shipped. 170/170 tests green.
