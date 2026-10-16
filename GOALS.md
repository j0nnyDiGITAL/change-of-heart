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
- **Milestone:** v1.1.3 released; redesign PARKED — next: functional perfection pass.
- **You are at:** Release complete; redesign parked per user — functionality first.
- **Last done:** GitHub issue triage complete (#1, #3 closed as already-implemented in v1.1.2; #2 needs-info; #4 ready-for-agent with agent brief) + #4 Load-Save playtime `NoneType` crash fixed (server.py None-tolerant playtime → "Unknown") with 2 regression tests. 190/190 green.
- **Do this next:** Functional perfection pass (user to pick target: issue #2 close-out, NFKC name edge, D008 outfits, PR #5/#6 review, or load-path hardening).
- **DONE WHEN:** Chosen functional target verified (tests green + ledger synced).
- **Live caveats (trust, don't re-verify):** Full-bleed redesign preserved on branch `redesign/p5r-native-menu`; Outfits `0xA000+` wiring frozen (D008) until 2-save diff proves offsets.


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
- 2026-10-14: Redesign PARKED by user decision — functionality to be perfected first. Grill-with-docs Round 1 shelved before answers; fact-finding banked (redesign was merged then reverted by `650d3b9`; main is sidebar layout; references + capture tool ready).
- 2026-10-14: v1.1.3 patch release cut — rebuilt EXE from main HEAD (issue #4 playtime fix included), headless smoke test PASSED (/api/build → 200), published to GitHub Releases (zip + EXE), closed issue #4 as fixed. 190/190 tests green.
- 2026-10-14: GitHub issue triage (`/triage`): 4 open issues verified against HEAD 22818e8 via changelog cross-reference + read-only code verifier. #1 (group name overflow) and #3 (compendium pollution / Satanael) closed as already-implemented in v1.1.2 (83cefdf, 191fe0d); #2 (rank 10 romance) → needs-info (fixed-in-head, awaiting reporter confirm); #4 (Load Save `NoneType // int`) → ready-for-agent with agent brief. Shipped the #4 fix: None-tolerant playtime in `server.py` (undeterminable → "Unknown"; header-u32 fallback accepted only when 0 < v <= 500000) + `tests/test_github_issues.py` (2 regression tests). 190/190 tests green.
- 2026-10-11: Resolved `u/Thelonlierface` report (*"added all the wrong items and also gave me curse build arsene"*): preserved existing player-registered Velvet Room Compendium builds on save/unlock, replaced template `201` with canonical Lv 1 starter Arsene, fixed `+1` BLANK-row offset shift across Skill Cards (`0x4000`), Protectors (`0x5000`), Treasure (`0x8000`), and Outfits (`0xA000`), and prevented empty normalized inventory fallback (D020); 185/185 tests passing.
- 2026-10-05: Critical consumable offset desync fixed (u/Party-Consequence-71: Homunculus->Takemedic bug) via Universal Engine Offset Formula (`core/consumable_offsets.py`, D019); full FAQ knowledge base published (`docs/FAQ.md`) with in-app `❓ FAQ & HELP` modal and full inline README FAQ (u/Aslanyiyenkedi save button, u/Antiwis- unmet confidants 0 stars vs ???); 183/183 tests passing; invariants verified 4/4.
- 2026-09-22: v1.1.2 EXE rebuilt from HEAD `174d35a` (PyInstaller 6.22.0 / Python 3.14.6, 28.6s, 41.7MB, sha256 897e0df5cbf17172) — reddit bugfixes now in binary. Ledger synced pre-build per crash-safety rule.
- 2026-09-22: Reddit community bugfixes shipped (RESERVE item filter, Satanael NG+ badge, romance bit 0x02 verify, Yen/EXP isolation, category-table cache ~4ms) + AGY-OS Tier 2 scaffolding committed. 182/182 tests green. Antigravity session died on quota mid-reflex-audit; ledger desyncs repaired + next direction (v1.1.2 EXE rebuild) chosen via reflex.
- 2026-09-02: Rescaffolding project according to AGY-OS Tier 2 standard (GOALS.md initialized).
- 2026-08-26: Fixed save backup ZIP creation bug for uploaded/custom save files (`create_memory_backup_zip` + auto-download on save). Preserved redesign on `redesign/p5r-native-menu` branch and restored stable v1.1.1 baseline to `main`. 178/178 tests green.
- 2026-08-25: Ground-up Native Menu Engine -- eliminated left sidebar, expanded canvas to 100vw full-bleed viewport, wired bottom ribbon navigation ticker (ref: 12558.jpg / 63559.jpg). 176/176 tests green.
- 2026-08-24: Fixed bond-points wipe bug (zamasu2020, r/Persona5Royale). 174/174 tests green.
- 2026-08-24: UI-liveness watchdog shipped. 170/170 tests green.
