# TEST FIXTURE & VERIFICATION MATRIX — OPERATION CHANGE OF HEART

**Project:** Change of Heart — Persona 5 Royal Save Editor  
**Repository:** https://github.com/j0nnyDiGITAL/change-of-heart  
**Date:** October 16, 2026  
**Status:** 190/190 Automated Unit Tests Green  

---

## 1. Test Fixtures

| Fixture Name | Location | Size (Bytes) | SHA-256 Checksum | Purpose / Description |
|---|---|---|---|---|
| **Canonical Save** | `tests/fixtures/canonical_save.dat` | 26,336 | `a492167d4f9b87b7a2d04a6e8105cb79da8366e612809e3e3b08e5c2cf1d4aa8` | Standard synthetic encrypted PC save container used across all unit tests. |
| **Audit Save** | `scratch_audit/DATA.DAT` | 26,336 | `3d681141dfa9d8eb6d4be0e58fa26bfa5882e3bf4a92c42d38515082f42a92e1` | Reference save for compendium gap and flag audit. |
| **User Oracle Save (Local)** | `C:\Users\kufis\p5r_buff_save\DATA11\DATA.DAT` | 26,336 | Dynamic | Live user save fixture used conditionally when present (auto-skipped on clean clone). |

---

## 2. Test Suite Breakdown (190 Tests Across 16 Modules)

| Test Module | Test Count | Test Domain / Coverage |
|---|---|---|
| `tests/test_editor.py` | 26 | Core SaveEditor parsing, money, stats, confidants, and packaging |
| `tests/test_hardening.py` | 46 | Security hardening, input validation, origin protection, and API bounds |
| `tests/test_reddit_bugfixes.py` | 10 | Reddit community bug fixes (Homunculus, compendium builds, passive affinity skills, teammate evolutions) |
| `tests/test_inventory_s1.py` | 19 | Normalized inventory engine, stacks, owned gear, 338 consumable offsets |
| `tests/test_roundtrip_oracle.py` | 18 | Binary roundtrip preservation, AES-256 decryption/encryption fidelity |
| `tests/test_compendium.py` | 9 | Compendium dual bitmask manipulation, mirror synchronization, and 100% unlock |
| `tests/test_guardrails_features.py` | 13 | Calendar deadlines, Maruki/Kasumi caps, party slot bounds |
| `tests/test_audit_fixes.py` | 18 | 2026-08-13 and 2026-08-24 external audit fixes |
| `tests/test_instances_registry.py` | 5 | Concurrent instance discovery, registry lifecycle, and loopback ports |
| `tests/test_ingame_parity.py` | 6 | In-game parity checks, item name consistency |
| `tests/test_backup_fix.py` | 2 | Timestamped ZIP backup creation for local and uploaded save files |
| `tests/test_github_issues.py` | 2 | GitHub issue #4 playtime NoneType crash prevention |
| `tests/test_bond_points_preservation.py` | 4 | Confidant bond-points surplus preservation across rank rewrites |
| `tests/test_deadbit_prune.py` | 3 | Compendium dead-bit pruning (Satanael mask-only bit, unsummonable IDs) |
| `tests/test_kasumi_prejoin.py` | 2 | Kasumi pre-join state and Rank 5 story cap |
| `tests/test_ui_heartbeat.py` | 2 | WebView2 liveness watchdog and browser fallback |
| **Total** | **190** | **100% Passing (0 failures, 0 errors)** |

---

## 3. Required Test Additions (Phases A through F)

- [ ] `tests/test_atomic_save_writes.py`: Two-phase atomic write sequence, rollback on error, fault injection at 6 write checkpoints.
- [ ] `tests/test_session_transactions.py`: Session capability token, revision tracking, dirty state, conflict detection (HTTP 409).
- [ ] `tests/test_container_validation.py`: Strict CRC rejection, magic check, truncated payload rejection, decompression bomb defense.
- [ ] `tests/test_api_security.py`: Token validation, Origin/Host loopback enforcement, path traversal defense in ZIP and file loaders.
- [ ] `tests/test_binary_invariants.py`: Automated byte-delta oracle proving zero unintended mutations on every save operation.
