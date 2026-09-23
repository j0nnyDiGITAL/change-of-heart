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
- **Milestone:** Ship v1.1.2 release (stale EXE), then resume Ground-Up Redesign on `redesign/p5r-native-menu`.
- **You are at:** Implementation phase (AGY-OS Tier 2 active; ledger resynced after Antigravity quota death).
- **Last done:** v1.1.2 EXE rebuilt from HEAD (41.7MB, sha256 897e0df5cbf17172, includes reddit bugfixes).
- **Do this next:** User hands-on test of fresh EXE -> D011 process smoke test -> GitHub v1.1.2 release upload.
- **DONE WHEN:** Process smoke test passes (Origin guard 403 + heartbeat ever_seen=true), GitHub release v1.1.2 published with asset, STATUS.md Build/GitHub lines match release.
- **Live caveats (trust, don't re-verify):** Full-bleed redesign preserved on branch `redesign/p5r-native-menu`; Outfits `0xA000+` wiring frozen (D008) until 2-save diff proves offsets; current shipped EXE predates reddit bugfixes.


## Project goals (durable)
- **Authentic P5R Experience:** Deliver a 100% faithful, mouse-driven Persona 5 Royal save editor & compendium studio matching in-game visual aesthetics and layouts.
- **Flawless Binary Fidelity:** Cryptographically verified AES-256-CBC and dual CRC32 re-signing across primary (`0x09973`) and mirror (`0x21E83`) offsets without data corruption.
- **Complete Feature Suite:** Granular compendium (100% genuine unlock), 10-category master inventory, confidant progress & romance toggles, party evolution tiers, and automatic immutable ZIP backups.


## Phase Plan

### PHASE 1 -- AGY-OS Scaffolding Alignment
- [x] Upgrade state.json to Schema v2 with `check_commands`, `banned_patterns`, and `human_gate`.
  - **Gate:** `python scripts/check-invariants.py` validates schema v2.
- [x] Upgrade `scripts/check-invariants.py` with auto-sync, auto-migration, and banned pattern checks.
  - **Gate:** `python scripts/check-invariants.py --sync` executes cleanly.
- [x] Rescaffold `AGENTS.md` and `STATUS.md` to latest AGY-OS Tier 2 standards.
  - **Gate:** Invariant check passes 100% with no missing files or desyncs.


## PHASE 2 -- Ground-Up P5R UI Redesign (`redesign/p5r-native-menu`)
- [ ] Stage 1: Full-Bleed Joker Status Canvas (character cutout on canvas, angled polygonal shards, tactile stat controls).
  - **Gate:** Headless UI capture matches reference `27809.jpg` / `76684.jpg`.
- [ ] Stage 2: Compendium & Velvet Room Register (blue accent theme, 232-record view).
  - **Gate:** Compendium toggle and batch unlock verified against reference `228140.jpg`.
- [ ] Stage 3: Airsoft Shop Inventory Overhaul (Iwai lime theme, 10-pocket layout).
  - **Gate:** Matches reference `89783.jpg` / `26113.jpg`.
- [ ] Stage 4: Confidants & Bond Dossier (gold accent theme, character dossiers).
  - **Gate:** Confidant rank & surplus preservation UI validated.


## Progress Log
- 2026-09-22: v1.1.2 EXE rebuilt from HEAD `174d35a` (PyInstaller 6.22.0 / Python 3.14.6, 28.6s, 41.7MB, sha256 897e0df5cbf17172) — reddit bugfixes now in binary. Ledger synced pre-build per crash-safety rule.
- 2026-09-22: Reddit community bugfixes shipped (RESERVE item filter, Satanael NG+ badge, romance bit 0x02 verify, Yen/EXP isolation, category-table cache ~4ms) + AGY-OS Tier 2 scaffolding committed. 182/182 tests green. Antigravity session died on quota mid-reflex-audit; ledger desyncs repaired + next direction (v1.1.2 EXE rebuild) chosen via reflex.
- 2026-09-02: Rescaffolding project according to AGY-OS Tier 2 standard (GOALS.md initialized).
- 2026-08-26: Fixed save backup ZIP creation bug for uploaded/custom save files (`create_memory_backup_zip` + auto-download on save). Preserved redesign on `redesign/p5r-native-menu` branch and restored stable v1.1.1 baseline to `main`. 178/178 tests green.
- 2026-08-25: Ground-up Native Menu Engine -- eliminated left sidebar, expanded canvas to 100vw full-bleed viewport, wired bottom ribbon navigation ticker (ref: 12558.jpg / 63559.jpg). 176/176 tests green.
- 2026-08-24: Fixed bond-points wipe bug (zamasu2020, r/Persona5Royale). 174/174 tests green.
- 2026-08-24: UI-liveness watchdog shipped. 170/170 tests green.
