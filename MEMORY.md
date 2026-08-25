# MEMORY.md — P5R Save Editor (Change of Heart)

> Canonical memory. Read this before any work. Update at end of every session.
> Updated: 2026-08-24

## Project Identity
- **Title:** Change of Heart — P5R Save Editor
- **Goal:** Read and fix Persona 5 Royal (PC/Steam) save files — truthful read + safe lasting write
- **Workspace:** `E:\ai-workspace\knowledge-base\projects\p5r-save-editor`
- **Version:** v1.0.10-dev (153/153 tests passing, NOT pushed to GitHub)
- **Architecture:** Native PyWebView / Edge WebView2 window (`main.py`) over stdlib HTTP backend (`server.py`, binds `127.0.0.1:3000`). Frozen build: `P5R_Save_Editor.spec` (PyInstaller).

## Locked Decisions (Do Not Re-Debate Without User)

| ID | Date | Decision | Reason |
|----|------|----------|--------|
| D001 | 2026-08-14 | ABI: Python 3.14.6, PyInstaller 6.22.0 | Consistent frozen builds |
| D002 | 2026-08-14 | Backend: stdlib HTTP, no Flask/Django | Minimal dependencies, standalone EXE |
| D003 | 2026-08-14 | GUI: PyWebView → Edge WebView2 | Native window, not browser tab |
| D004 | 2026-08-18 | Ground truth: `J:\SteamLibrary\...\P5R\CPK\BASE.CPK` via `tools/cpk_extract.py` | Game data files are authoritative, not web research |
| D005 | 2026-08-18 | PC ≠ PS4: KHSaveEditor offsets are PS4 garbage on PC | Verify via 2-save diff (`tools/diff_mapper.py`) |
| D006 | 2026-08-19 | Inventory taxonomy: 4 storage paradigms (owned-flag, count-array, key-item bitfield, outfit owned-flag) | Oracle-verified (DeepSeek + Gemini agree) |
| D007 | 2026-08-19 | Inventory rebuild spec: `docs/INVENTORY_SPEC.md` is canonical | Oracle-verified, supersedes all prior inventory prose |
| D008 | 2026-08-19 | Outfit `0xA000+` frozen until live diff proves offset | Risk of corruption if wired from inference |
| D009 | 2026-08-21 | 3rd Semester Emergency Rescue button RETIRED | Requires 43,008-bit Event Flag Matrix manipulation |
| D010 | 2026-08-23 | Haru (Slot 6) / Futaba (Slot 7) aligned, Party Evolution Tiers (1-3) exposed, EXP autosync curve activated, PC Romance flags enabled | Solves save migration and post-battle EXP stalling reported by community (`u/Gruphius`) |
| D011 | 2026-08-23 | PyInstaller compilation strictly bound to Python 3.14.6; process smoke test mandatory before release upload | Prevents ambient venv package omission (missing `pywebview` -> browser fallback regression) |
| D012 | 2026-08-23 | Multi-location save discovery across Steam Userdata/LocalAppdata + manual file picker (`📂 BROWSE...`) | Prevents silent empty save lists for non-standard install paths, multi-account setups, or GamePass saves |
| D013 | 2026-08-24 | Local API enforces loopback-only Origin check; no `Access-Control-Allow-Origin: *` | CSRF hardening — a browser page must never drive the local save API |
| D014 | 2026-08-24 | UI-liveness watchdog: native window must heartbeat `/api/ui-heartbeat` within 30s of launch, else main.py auto-falls-back to the system browser | Broken WebView2 Runtimes cause silent dead UIs (r/Persona5Royale u/Gruphius case); app must self-heal with zero user homework |
| D015 | 2026-08-24 | Browser `--app` mode REJECTED as fallback tier — tested in a prior build, rejected in practice: Edge profile bleed (imported-extension config prompts), session-restore nagging, clunky window behavior | Plain default-browser tab is the final fallback tier; do not re-propose app-mode |
| D016 | 2026-08-24 | Point-based fields (confidant bond, social stats) must NEVER be written to bare thresholds on same-rank rewrites — preserve-surplus semantics: max(current, threshold) on raise, untouched on keep, threshold only on explicit lowering | Threshold-exact rewrites wiped players' accrued progress (zamasu2020 bug: one social-stat edit reset every confidant's bond surplus) |

## Core Domain Rules
- Save is 4 paradigms + mirror `+0x18510`: Gear owned-flag, Stacks count-array, Key Items owned-flag/bitfield, Outfits owned-flag
- Quick-array `0x3530` (30×[u16 id][u16 flag]) is NEVER merged — surface as `conflicts` where count-region wins
- Write primary + mirror, read must warn on mismatch
- AES-256-CBC + dual CRC32 (header `0x00`, payload `0x20`) — integrity is critical
- `0xA000+` Outfits (286 rows) — DO NOT wire save offset until diff proves
- **Compendium % (in-game) counts Velvet Room struct records (~232 denominator), NOT the mask.** Verified 2026-08-21: save with 171-bit mask + 225 records showed 96%; oracle parity = 224 live bits + 232 records = 100%
- **Genuine 100% sets ALL live mask bits** — including party personas (0xCA-0xD3), Satanael (0xAA/0xC7/0xD3), RESERVE-named bits (e.g. 0x47). Old belief "game never registers party personas" is WRONG (oracle DATA13/15/16 prove). Metatron slot 0x01: bit dead but record present in genuine saves

## Item Storage Map (Verified)

| Prefix | Item type | Save storage | Status |
|--------|-----------|-------------|--------|
| 0x1000 | Melee weapon | OWNED-FLAG `0x1B30+idx` | ✅ VERIFIED |
| 0x2000 | Consumable | COUNT-ARRAY `0x2410..0x2800` | ✅ VERIFIED |
| 0x3000 | Accessory | COUNT-ARRAY `0x2330+idx` | ✅ VERIFIED |
| 0x4000 | Skill card | COUNT-ARRAY `0x2E30+idx` | ✅ VERIFIED |
| 0x5000 | Protector/Armor | COUNT-ARRAY `0x1F30+idx` | ✅ VERIFIED |
| 0x6000 | Infiltration tool | COUNT-ARRAY `TOOL_OFFSET_BY_DB_ID` | ✅ VERIFIED |
| 0x7000 | Ranged weapon | OWNED-FLAG `0x3430+save-idx` | ✅ VERIFIED (2 mapped) |
| 0x8000 | Treasure/material | COUNT-ARRAY `0x2A30+idx` | ✅ VERIFIED |
| 0x9000 | Key item | COUNT-ARRAY `KEY_ITEM_OFFSET_BY_DB_ID` | ✅ VERIFIED (583 mapped) |
| 0xA000 | Outfits & Costumes | OWNED-FLAG `0x3230+idx` | ✅ VERIFIED (286, frozen) |

## Key Verified Offsets
- **Yen** = `0x35C0` (v1.0.5 fix). `0x3C` is Joker EXP — MUST NOT be written.
- **Player Names** = `0x13840` (full), `0x138A8` (last), `0x138DC` (first) + mirror `0x2BD50`
- **Master Item Counts** = `0x2410..0x2800` — multi-base layout (see item map)
- **Compendium masks:** primary `0x09973`, mirror `0x21E83` (+0x18510)
- **Compendium struct array:** primary `0x04270`, mirror `0x1C780` (48B stride, 437 slots)
- **Confidant block** = `0x136A0` (23 arcanas, 16B stride)
- **Event Flag Matrix** = `0x2F200`–`0x30700` (43,008-bit progression)

## Toolchain Fixes Applied
- DSH ACL sandbox `STATUS_DLL_INIT_FAILED` fixed via `settings.yaml` `danger-full-access`
- SDK cmake `3.22.1`→`3.31.6` via `sdkmanager`
- Research: Hound MCP primary, Exa secondary, gh CLI, Jina curl
- Mcporter: 3 servers healthy (mcp-hound 6 tools, exa 2, agentmail 26)

## User Preferences
- Uses pwsh 7.6.5 (not 5.1) for shell commands
- No DeepSeek API key — pure `dsh web`
- Uses Hermes in parallel for research/oracle
- When DSH broken, prefers fix not workaround
- Push to GitHub only after in-game verification

## Known Pitfalls
- PC save ≠ PS4 save — never trust PS4 offsets from KHSaveEditor
- Cheat save (GameBanana) uses DIFFERENT layout — only live diffs count
- `slotIdx < 30` cap was silently dropping items (fixed v1.0.8)
- Quick-array at `0x3530` is a TEMPORARY buffer — never merge with master counts
- PyInstaller sandbox blocks Temp perms — use `python -m unittest discover -s tests` (filtered 134/153)
- UI staged-list saves: server per-pid compendium loop CLEARS any pid missing from the payload list — batch unlocks must arm the backend flag (`unlock_compendium`), never stage a filtered list (fixed 2026-08-21, guarded by `TestCompendiumUnlockAllWiring`)
- JSON template keys are strings — `pid in json.loads(...)` is always False for int pids; use the editor's `_load_compendium_templates()`
- **Point-based fields (confidant bond pts, social stat pts) store PROGRESS, not just rank** — never write bare rank thresholds on same-rank rewrites; preserve surplus (D016, fixed 2026-08-24, guarded by `test_bond_points_preservation.py`)
- Confidant block stores SAVE_ID (Death=14), but `set_confidant_rank()` takes ARCANA_ID (Death=13) — mixing them up silently no-ops

## Long-Term Vision
- **UI North Star:** `docs/UI_NORTH_STAR.md` — executable 1:1 P5R fidelity spec. Ground truth = 146 official screenshots (pixel-sampled palette: red #FD1700, cyan selection #00C4FE, per-context accents lime/blue/gold; black canvas, white text, parallelograms, no gradients/emoji/rounded pills). Reference corpus local at `design/reference/` (79MB, gitignored), contact sheets tracked. Phase roadmap P2-P6 inside; every UI change must cite a reference screenshot + spec rule.

## Session History
- 2026-08-25: UI P2 pass — stage accent theming, emoji purge, kinetic motion, search consolidation; 176/176 tests green, 10/10 captures, ledger .unlazy/ui-p2/GATES.md (8/9 gates met). See memory/2026-08-25-ui-p2-stage-accents.md
- 2026-08-21: Inventory UX pass R1-R9 (memory/2026-08-21-inventory-ux-pass.md)
- 2026-08-15: v1.0.7 EXE build, safety hardening
- 2026-08-16: v1.0.8 prep, master item count rewrite, compendium fixes
- 2026-08-17: Equipment ownership probe (melee verified, others WIP)
- 2026-08-18: v1.0.8 shipped (names, item counts, compendium, 122 tests → 126 tests)
- 2026-08-19 AM: Equipment ownership ALL 4 categories verified (126 tests)
- 2026-08-19 PM: Compendium phantom pid-211 fixed (123→153 tests), oracle taxonomy consult, inventory web-app rebuild spec (`docs/INVENTORY_SPEC.md`), Cheat Shop Phase A-D implemented (153 tests), rebuild plan speedrunner review, v1.0.9-dev EXE built
- 2026-08-20: Metroid Prime conventions audit, oracle SOP consult, P5R hygiene upgrade (this session)
- 2026-08-21: Compendium 96% in-game bug — root cause UI Unlock ALL filtering + server per-pid clear; rewired to backend `unlock_compendium_100()`; user save DATA02 surgically patched to 100% parity; 157 tests; EXE rebuilt
- 2026-08-23: Party evolution tiers, Haru/Futaba slot fix, EXP auto-sync, romance toggle, key-item catalog unlock, save auto-discovery + manual browse (165→168 tests); hotfix v1.1.0 EXE rebuilt + GitHub asset updated
- 2026-08-24: External audit fixes — tracked roundtrip harness + lint shim (fresh-clone breakage), CSRF Origin guard, personal paths scrubbed from tests, deps pruned, HANDOFF.md archived, state/docs resync
- 2026-08-24 (later): UI-liveness watchdog shipped after r/Persona5Royale field report (u/Gruphius: all versions silently dead on his machine = broken WebView2 runtime) — heartbeat + auto browser fallback; 170 tests; EXE rebuilt (520a1c5a)
- 2026-08-24 (evening): UI Atlus-fidelity pass R1+R1.9 — screenshot audit vs official game screenshots (gameuidatabase.com, pixel-sampled): rainbow gradient → flat white bar, green/yellow slabs → authentic red/white/black/cyan palette (D016-adjacent), hex IDs removed from persona cards, star ladder → horizontal meters, sidebar emoji → flat SVGs, type hierarchy demoted; v1.1.1 released with watchdog build
- 2026-08-24 (night): Bond-points wipe bug FIXED (zamasu2020) — social-stat edits reset all confidants' surplus via full-confidant re-save loop; preserve-surplus semantics in set_confidant_rank + set_social_stats (D016); 4 regression tests (174/174); EXE rebuilt
