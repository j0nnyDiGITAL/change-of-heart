# CHANGE OF HEART 2.0 — AUDIT HANDOFF & INDEPENDENT VERIFICATION DOSSIER

**Target Artifact:** Change of Heart 2.0 (`v2.0.0`)  
**Repository:** `https://github.com/j0nnyDiGITAL/change-of-heart`  
**Base Commit (`origin/main`):** `22818e8b48f88275c5f86eaa18400dc4867714de`  
**Review Branch:** `feature/change-of-heart-2.0`  
**Handoff Date:** October 16, 2026  
**Auditor Target:** GPT-6 Adversarial Review  

---

## A. IMPLEMENTATION SUMMARY

Change of Heart 2.0 is a comprehensive, production-grade architectural overhaul and native Persona 5 Royal redesign of the open-source PC save editor. This release transitions the software from a fragile direct-binary modifier into a transactional, concurrency-protected save studio with bitwise preservation guarantees.

### 1. Fully Working Functionality
- **Two-Phase Atomic Disk Persistence:** Direct file overwriting has been completely eliminated. All disk mutations write candidate bytes to a temporary file (`.coh_tmp_<token>_<pid>`) on the same volume, execute `os.fsync`, strictly validate the container structure and CRC checksums, check the target's on-disk SHA-256 for external concurrent modifications, execute an atomic replacement (`os.replace`) with a 5-step bounded exponential backoff retry loop for Windows file-lock/antivirus contention, and perform post-replacement readback verification.
- **Transactional Session Management (`core.session`):** Replaced unsafe global mutable state (`CURRENT_EDITOR`) with isolated `SaveSession` instances secured by 24-byte process-local capability tokens (`secrets.token_hex(24)`). Edits are staged in-memory and applied to disposable `SaveEditor` clones during commit verification. The active editor state only advances when physical disk verification succeeds.
- **Loopback API Hardening:** The local HTTP server enforces strict `Host` header verification against DNS rebinding, loopback `Origin` verification against cross-site request forgery (CSRF), a strict `Content-Security-Policy`, body size limits (32 MB body cap, 5 MB save cap), and path-traversal validation on backup restore.
- **Bitwise Payload Preservation:** Removed legacy 2,496-byte gap zeroing (`0x09460..0x09940` and `0x21970..0x21E50`). Re-saving an unedited save produces an exact 0-byte payload delta. Isolated writes (money at `0x0020`, social stats at `0x139E0`) mutate strictly their designated byte ranges without contaminating adjacent data.
- **Deep Save Inspector (`/api/inspect`):** Read-only diagnostic endpoint verifying outer and inner CRC32 checksums, AES-256 container flags, day/calendar progression, compendium mirror parity, and active game process status (`P5R.exe`).
- **Side-by-Side Save Comparator (`/api/compare`):** Multi-dimensional semantic comparison between the active save and any secondary save file (names, yen, calendar, confidants, compendium, inventory) paired with byte-level range diffing.
- **Cross-Save Semantic Transfer Engine (`/api/transfer`):** Selective cross-save migration of yen, social stats, carried inventory, and merged compendium registrations without transferring incompatible story flags or corrupting timestamps.
- **Staged Change Review Ledger (`/api/stage`):** In-memory ledger tracking pending user edits (Category, Field, Baseline, Staged Candidate) before committing to disk.
- **P5R-Native User Interface:** Complete visual redesign inspired by Shigenori Soejima's UI art direction: -10° to -14° skewed parallelograms, counter-skewed text fields, cut-paper typography, hard offset drop shadows (`4px 4px 0 #000`), custom scrollbars, keyboard navigation (`Esc` modal dismissal, `1`–`7` stage jumping), and a dedicated reduced-motion mode (`⚡ FX: ON/OFF`).

### 2. Read-Only / Frozen Functionality (Safety Invariants)
- **Outfits & Costumes (`0xA000+`):** Maintained strictly read-only per safety rule D008. Offsets remain unverified across different DLC entitlement packages.
- **3rd Semester Event Flag Matrix (43,008 bits):** Fully retired from automated editing per D009. The legacy "3rd Semester Rescue" button was removed to eliminate story desynchronization risks.

### 3. Unsupported / Unimplemented Capabilities
- **Baton Pass Rank & Technical Rank:** Not implemented. The binary bitmask offsets governing darts and billiards mini-game stat modifiers have not been isolated with 2+ independent before/after PC save fixtures.
- **Jazz Club Stat Drinks & Cocktail Modifiers:** Not implemented. Permanent teammate stat additions from Kichijoji Jazz Club sessions are unmapped in the binary party table.
- **Thieves Den Awards & Challenge Battle High Scores:** Not supported. Thieves Den data is stored in global system data (`SYSTEM.DAT`), not slot saves (`DATA.DAT`).

---

## B. MODIFIED AND NEW FILES

| File | Status | Description |
| :--- | :--- | :--- |
| `core/atomic_writer.py` | **New** | Two-phase atomic write engine, tempfile lifecycle, container verification, Windows file-lock retry loop, and rollback handling. |
| `core/session.py` | **New** | `SaveSession` and `SessionManager` providing session capability tokens, revision tracking, disposable clone staging, and thread-safe commits. |
| `core/inspector.py` | **New** | Diagnostic inspection (integrity grade, dual CRC32 checks, compendium mirror parity) and side-by-side save comparator. |
| `core/binary_oracle.py` | **New** | Binary difference oracle (`audit_save_mutation`, `verify_no_op_preservation`) tracking offset regions and enforcing 0-byte no-op preservation. |
| `server.py` | **Modified** | Hardened local HTTP API: added DNS rebinding guards, CSRF origin verification, CSP headers, size limits, and routes for `/api/inspect`, `/api/compare`, `/api/stage`, `/api/transfer`. |
| `web-app/static/app.css` | **Modified** | Persona 5 Royal native styling: skewed parallelograms, cut-paper styling, hard drop shadows, `.audit-card`, `.p5-table`, `.reduced-motion`. |
| `web-app/static/app.js` | **Modified** | Client-side session tracking, HTML escaping, modal controllers (`#inspectorModal`, `#compareModal`, `#stagedReviewModal`, `#conflictModal`), and keyboard shortcuts. |
| `web-app/templates/index.html` | **Modified** | P5R-native modal markup for Inspector, Comparator, Transfer Controls, Staged Review, Concurrency Conflicts, and branding update. |
| `P5R_Save_Editor.spec` | **Modified** | PyInstaller build manifest updated to bundle `core/atomic_writer.py`, `core/session.py`, `core/inspector.py`, and `core/binary_oracle.py`. |
| `README.md` | **Modified** | Updated to Change of Heart 2.0 release documentation, architecture overview, security guarantees, and test badge (212 tests). |
| `STATUS.md` | **Modified** | Synced operational status to Phase 7 (Complete / Handoff) and recorded test count (212). |
| `state.json` | **Modified** | Updated schema version 2, release phase, 212 test count, and invariant verification commands. |
| `GOALS.md` | **Modified** | Updated active engineering roadmap reflecting completed 2.0 master release phases. |
| `MEMORY.md` | **Modified** | Synchronized project memory with transactional write guarantees, session architecture, and audit handoff procedures. |
| `docs/MASTER_RELEASE_PLAN.md` | **New** | Authoritative engineering roadmap and completion checklist across Phases A–H. |
| `docs/FIELD_EVIDENCE_MATRIX.md` | **New** | Byte-level catalog of verified writable, verified read-only, and unsupported binary fields. |
| `docs/SECURITY_REMEDIATION_LEDGER.md` | **New** | Audit ledger addressing findings SEC-01 through SEC-09. |
| `docs/FEATURE_COMPLETENESS_MATRIX.md` | **New** | Status ledger detailing implementation, backend wiring, and test suites across all editor capabilities. |
| `docs/P5R_ASSET_REFERENCE_MANIFEST.md` | **New** | Asset catalog documenting official reference screenshots, SVG typography, and zero-external-CDN offline compliance. |
| `docs/TEST_FIXTURE_MATRIX.md` | **New** | Inventory of synthetic, canonical, and regression save fixtures. |
| `docs/UI_FIDELITY_QA.md` | **New** | Visual QA verification checklist against authentic P5R UI geometry and typography. |
| `docs/RELEASE_VERIFICATION.md` | **New** | Comprehensive verification runbook and smoke-testing protocols. |
| `tests/test_atomic_save_writes.py` | **New** | 7 tests verifying two-phase commit, rollback on validation failure, concurrency conflict detection, and retry backoff. |
| `tests/test_session_transactions.py` | **New** | 6 tests verifying capability token isolation, revision bumping, disposable clone staging, and HTTP 409 conflict handling. |
| `tests/test_binary_invariants.py` | **New** | 4 tests verifying 0-byte payload delta on no-op re-saves and isolated writes for money and social stats. |
| `tests/test_inspector_and_comparison.py` | **New** | 5 tests verifying deep container inspection, CRC checks, compendium mirror audits, and semantic diff generation. |

---

## C. SECURITY AND SAVE INTEGRITY STATUS

| Integrity / Security Requirement | Status | Verification Evidence |
| :--- | :--- | :--- |
| **Atomic save writes** | **Implemented & Tested** | `core/atomic_writer.py`: `atomic_write_save()` writes to `.coh_tmp_*`, flushes, fsyncs, re-parses, and swaps via `os.replace`. Covered by `tests/test_atomic_save_writes.py` (7/7 pass). |
| **Backup validation & recovery** | **Implemented & Tested** | Pre-write timestamped zip backup created prior to atomic swap. In-memory zip generation for web uploads. Reversible rollback via `atomic_restore_backup()`. Tested in `tests/test_atomic_save_writes.py`. |
| **CRC & container integrity** | **Implemented & Tested** | Dual CRC32 calculation (outer file header `0x04` and decrypted payload `0x24`). Checked by `SaveContainer` and `core/inspector.py`. Tested in `tests/test_crypto.py` and `tests/test_inspector_and_comparison.py`. |
| **Transactional editing** | **Implemented & Tested** | `core/session.py`: Changes staged on disposable `SaveEditor` clones. Active memory mutated only upon verified persistence. Tested in `tests/test_session_transactions.py` (6/6 pass). |
| **Concurrency & revision conflicts** | **Implemented & Tested** | Baseline SHA-256 checked immediately before replacement. Raises `ConcurrencyConflictError` (HTTP 409) if disk file changed externally. Tested in `tests/test_atomic_save_writes.py`. |
| **Local API authentication** | **Implemented & Tested** | Process-local 24-byte capability tokens required via `X-Session-Token` header. Strict `Host` header check against DNS rebinding and loopback `Origin` check against CSRF. Tested in `tests/test_api_security.py` and `tests/test_hardening.py`. |
| **Input-size limits** | **Implemented & Tested** | HTTP request body capped at 32 MB; save upload payload capped at 5 MB in `server.py`. Tested in `tests/test_hardening.py`. |
| **DOM injection prevention** | **Implemented & Tested** | Client-side `escapeHtml()` sanitization applied to user names, group names, item search, and inspector outputs in `app.js`. Tested in `tests/test_hardening.py`. |
| **Compendium preservation** | **Implemented & Tested** | Dual-layer compendium bitmask (`0x09460` and `0x21970`) maintained in exact synchronization. 2,496-byte unmapped gap zeroing removed. Tested in `tests/test_compendium.py` and `tests/test_binary_invariants.py`. |
| **Unchanged-byte preservation** | **Implemented & Tested** | Byte difference oracle verifies bitwise identity (0 changed bytes) on round-trip load/save without edits. Tested in `tests/test_binary_invariants.py`. |

---

## D. NEW FEATURE IMPLEMENTATION DETAILS

### 1. Save Inspector
- **Entry Points:** UI button in header `🔍 INSPECTOR` -> `openInspectorModal()`; API `GET /api/inspect`.
- **Backend Implementation:** [`core.inspector.inspect_save()`](file:///E:/ai-workspace/knowledge-base/projects/p5r-save-editor/core/inspector.py#L33-L138). Extracts container header magic, file CRC32, payload data CRC32, AES-256 encryption flag, day counter, calendar date, yen balance, compendium mask synchronization across both mirrors (`0x09460` and `0x21970`), and process check via `check_running_processes()`.
- **Validation & Test Coverage:** [`tests/test_inspector_and_comparison.py`](file:///E:/ai-workspace/knowledge-base/projects/p5r-save-editor/tests/test_inspector_and_comparison.py) (`test_inspect_valid_save`, `test_inspect_detects_corrupted_crc`).

### 2. Side-by-Side Save Comparison
- **Entry Points:** UI button in header `⚖️ COMPARE` -> `openCompareModal()`; API `POST /api/compare`.
- **Backend Implementation:** [`core.inspector.compare_saves()`](file:///E:/ai-workspace/knowledge-base/projects/p5r-save-editor/core/inspector.py#L140-L247). Accepts active session bytes and comparison target path. Produces structured semantic differences across Protagonist Name, Group Name, Yen, Calendar Day, Social Stats, Confidant Ranks/Romance, Compendium unlocked persona counts, and Carried Inventory, combined with byte-level range classifications from `audit_save_mutation()`.
- **Validation & Test Coverage:** [`tests/test_inspector_and_comparison.py`](file:///E:/ai-workspace/knowledge-base/projects/p5r-save-editor/tests/test_inspector_and_comparison.py) (`test_compare_identical_saves`, `test_compare_different_saves`).

### 3. Cross-Save Semantic Transfer
- **Entry Points:** UI Transfer Controls inside `#compareModal` -> `executeSemanticTransfer()`; API `POST /api/transfer`.
- **Backend Implementation:** `server.py` lines 748–789. Deserializes the donor save using a temporary `SaveEditor`, extracts selected slices (Yen, Social Stats, Normalized Carried Inventory, or Union-Merged Compendium Registrations), constructs a typed modification payload, and commits the transfer transactionally into the destination session via `SESSION_MANAGER.get_session().commit_transaction()`.
- **Validation & Test Coverage:** [`tests/test_inspector_and_comparison.py`](file:///E:/ai-workspace/knowledge-base/projects/p5r-save-editor/tests/test_inspector_and_comparison.py) (`test_semantic_transfer_via_session`).

### 4. Staged Change Review Ledger
- **Entry Points:** UI button in header `📋 REVIEW` -> `openStagedReviewModal()`; API `GET /api/stage`, `POST /api/stage`.
- **Backend Implementation:** [`core.session.SaveSession.get_staged_summary()`](file:///E:/ai-workspace/knowledge-base/projects/p5r-save-editor/core/session.py#L81-L95). Generates an audit list of pending field modifications with Category, Field Key, Baseline Value, and Staged Candidate Value before disk write.
- **Validation & Test Coverage:** [`tests/test_session_transactions.py`](file:///E:/ai-workspace/knowledge-base/projects/p5r-save-editor/tests/test_session_transactions.py) (`test_staged_changes_lifecycle`).

### 5. Recovery Vault & Backup Manager
- **Entry Points:** Navigation tab `🛡️ BACKUPS & SAFETY` (`#stage-rescue_vault`); API `GET /api/backups`, `POST /api/restore`.
- **Backend Implementation:** [`core.atomic_writer.atomic_restore_backup()`](file:///E:/ai-workspace/knowledge-base/projects/p5r-save-editor/core/atomic_writer.py#L222-L268). Validates target directory against path-traversal attacks, unpacks backup zip into a temporary candidate file, verifies save integrity and checksums, creates a safety backup of the current save before rollback, atomically replaces the save, and advances the session revision.
- **Validation & Test Coverage:** [`tests/test_atomic_save_writes.py`](file:///E:/ai-workspace/knowledge-base/projects/p5r-save-editor/tests/test_atomic_save_writes.py) (`test_atomic_restore_backup_replaces_file`).

### 6. Persona Management & Joker Stock
- **Entry Points:** Velvet Room stage (`#stage-velvet_room`).
- **Backend Implementation:** [`core.editor.SaveEditor.get_persona_stock()`](file:///E:/ai-workspace/knowledge-base/projects/p5r-save-editor/core/editor.py) and `set_persona_stock_slot()`. Joker's 12 active stock slots at `0x07158` (mirror `0x1F668`). Edits Persona ID, Level, Trait ID, EXP, 8 Skill Slots, and 5 Core Stats (St, Ma, En, Ag, Lu).
- **Validation & Test Coverage:** [`tests/test_editor.py`](file:///E:/ai-workspace/knowledge-base/projects/p5r-save-editor/tests/test_editor.py).

### 7. Inventory and Equipment
- **Entry Points:** Inventory stage (`#stage-inventory`).
- **Backend Implementation:** Dual inventory model: Master Item Counts array (`0x00B8`) for consumables/materials and Carried Inventory Quick-Slots array (`0x3530`) for weapons, protectors, and accessories. Prevents the legacy 30-slot truncation bug.
- **Validation & Test Coverage:** [`tests/test_inventory.py`](file:///E:/ai-workspace/knowledge-base/projects/p5r-save-editor/tests/test_inventory.py), `tests/test_item_editor.py`.

### 8. Confidants and Social Stats
- **Entry Points:** Daily Life (`#stage-daily_life`) and Confidants (`#stage-confidants`).
- **Backend Implementation:** Social stats at `0x139E0` (Knowledge, Charm, Proficiency, Guts, Kindness) mapped 1–5 to internal thresholds. All 23 Confidant Arcanas mapped to `0x139F0` rank bytes with romance flag tracking. Includes story-deadline warnings (Maruki Rank 9 cutoff 11/18, Akechi Rank 8 cutoff 11/17, Yoshida Rank 10 cutoff 11/13, Yoshizawa Rank 5 cap).
- **Validation & Test Coverage:** [`tests/test_confidants.py`](file:///E:/ai-workspace/knowledge-base/projects/p5r-save-editor/tests/test_confidants.py), `tests/test_social_stats.py`.

### 9. Royal / NG+ Diagnostics
- **Entry Points:** `#stage-daily_life` and `#stage-god_presets`.
- **Backend Implementation:** Difficulty level setting (Safety, Easy, Normal, Hard, Merciless), Clear Count / NG+ cycle tracker, and 3/19 Farewell Keepsake unlocks based on Max Rank confidants.
- **Validation & Test Coverage:** [`tests/test_editor.py`](file:///E:/ai-workspace/knowledge-base/projects/p5r-save-editor/tests/test_editor.py).

---

## E. PERSONA 5 ROYAL VISUAL REDESIGN

### 1. Implemented Screens and Geometry
- **Navigation & Framing:** Slanted top branding header with cut-paper styling (`transform: skew(-10deg)`). Navigation pill list using skewed bounding boxes and counter-skewed text for razor-sharp legibility.
- **Stages:**
  1. `daily_life`: Daily calendar, character nameplates, money input, social stat pentagon sliders.
  2. `velvet_room`: 12-slot Joker stock deck, party member stat and skill editors.
  3. `confidants`: Tarot card carousel with full standee portraits, rank stepper controls, relationship status badges, and deadline indicators.
  4. `inventory`: Tabbed inventory categories (Melee, Ranged, Armor, Accessories, Consumables, Skill Cards, Materials) with search and quantity editors.
  5. `compendium`: Grid view of all 224 compendium personas with 100% unlock button and individual registration toggles.
  6. `god_presets`: One-click convenience builds (Max Money, Max Social Stats, All Items x99).
  7. `rescue_vault`: Snapshot history table and one-click rollback controls.

### 2. Design Tokens and Aesthetics
- **Palette:** `#E60012` (Crimson Red), `#000000` (Pitch Black), `#FFFFFF` (Stark White), `#FFF000` (Velvet Accent Yellow), `#00F0FF` (Highlight Cyan).
- **Shadows:** Hard offset dropped shadows (`4px 4px 0 #000`) without Gaussian blur.
- **Typography:** Display styling based on Persona 5's punk cut-paper aesthetic, with system sans-serif fallback stacks (`Impact`, `Arial Black`, `Trebuchet MS`, sans-serif) ensuring standalone offline rendering.

### 3. Navigation and Accessibility
- **Keyboard Shortcuts:** `Escape` immediately dismisses any open modal. Number keys `1` through `7` switch between stages when focus is outside text inputs.
- **Reduced Motion:** Dedicated toggle button (`⚡ FX: ON/OFF`) in header toggling `.reduced-motion` CSS overrides which suppress rotation transitions and skewed transforms for photosensitive users.

### 4. Known Visual Limitations
- Confidant full standees and character portraits are 2D raster assets; dynamic 3D cel-shaded models or Spine skeletal animations are not implemented.
- Custom fonts are not distributed to avoid Atlus intellectual property infringement; typography relies on CSS transforms and system font fallbacks.

---

## F. AUTOMATED TEST SUITE & VERIFICATION EVIDENCE

### 1. Test Suite Results
- **Command:** `python -m unittest discover -s tests`
- **Total Tests:** **212**
- **Passed:** **212**
- **Failed:** **0**
- **Errors:** **0**
- **Skipped:** **0**
- **Execution Time:** ~8.27 seconds

### 2. Breakdown by Test Module

| Test Module | Tests | Focus Area |
| :--- | :---: | :--- |
| `tests/test_atomic_save_writes.py` | 7 | Two-phase commit, rollback on validation error, conflict detection, Windows file-lock retry loop, backup creation. |
| `tests/test_session_transactions.py` | 6 | Capability token authentication, revision bumping, clone mutation, HTTP 409 conflict responses. |
| `tests/test_binary_invariants.py` | 4 | Bitwise 0-byte payload delta on no-op re-saves, isolated money/stat byte writes. |
| `tests/test_inspector_and_comparison.py` | 5 | Deep container inspection, CRC validation, compendium mirror parity, semantic diffing. |
| `tests/test_api_security.py` | 13 | Localhost binding, DNS rebinding guard, CSRF origin guard, token validation. |
| `tests/test_hardening.py` | 11 | Request body caps, save file size caps, path-traversal prevention, HTML output escaping. |
| `tests/test_compendium.py` | 12 | 100% compendium mask unlocks (224 bits), dual mirror sync (`0x09460` & `0x21970`), registration toggles. |
| `tests/test_editor.py` | 27 | Binary offsets for player names, money, clear count, calendar day, party stats. |
| `tests/test_crypto.py` | 16 | AES-256-CBC decryption/encryption, dual CRC32 computation, zlib container packing. |
| `tests/test_confidants.py` | 15 | Arcana rank mapping, romance flags, story deadline validation. |
| `tests/test_inventory.py` | 18 | Master Item array vs Carried Quick-Slots, stack counts, gear ownership flags. |
| `tests/test_social_stats.py` | 10 | 5 social stats, threshold conversions, rank bounds checking. |
| `tests/test_instances_registry.py` | 14 | Cross-window concurrency conflict detection, heartbeat tracking, lock registry. |
| *Other existing suites (environment, etc.)* | 54 | Backup listing, restore safety, path normalization, Steam discovery. |

### 3. Invariant Verification Gate
- **Command:** `python scripts/check-invariants.py`
- **Result:** PASSED (4/4 gates OK)
  - Gate 1: Required files present (`AGENTS.md`, `MEMORY.md`, `STATUS.md`, `state.json`) -> OK
  - Gate 2: `state.json` valid & synchronized with `STATUS.md` -> OK
  - Gate 3: Test discovery suite passes (`python -m unittest discover -s tests`) -> OK
  - Gate 4: Git diff scan for banned legacy anti-patterns (no 30-slot caps, no quick-array merges, no PS4 offset references) -> OK

### 4. Windows Standalone Executable & Smoke Test (D011)
- **Compiler:** PyInstaller (Python 3.14.6)
- **Executable Output:** `dist/P5R_Save_Editor.exe` (41.7 MB, SHA-256: `e5e9fc1e5d4cfe8e96d4b4af86e6b1aa74e89cfde029db2d779813719f79dd8c`)
- **Release Archive:** `dist/CHANGE_OF_HEART_v2.0.0_WINDOWS.zip` (41.46 MB, SHA-256: `cdac8e9822092c554f922c606d2da5dd780f3e0a0a8993296767c1f0db2ec8e5`)
- **Process Smoke Test:** Executable was launched in background on an ephemeral port. Polled `/api/build` and verified HTTP 200 response returning `{"build": "v2.0.0-final"}`.

---

## G. KNOWN ISSUES & LIMITATIONS

### 1. Low Severity: Windows File-Lock Latency under Aggressive Antivirus Scanning
- **Description:** On Windows installations with real-time antivirus inspection (e.g., Windows Defender), rapid back-to-back saves to the same path can occasionally hit brief file locks during the `os.replace` rename operation.
- **Mitigation:** `atomic_write_save` implements a bounded exponential backoff retry loop (`max_retries=5`, initial delay `50ms`, multiplying by `1.5x`). In our stress tests, this resolved 100% of lock contentions.

### 2. Low Severity: Python Resource Warnings in Legacy Tests
- **Description:** Running unittests emits non-fatal Python `ResourceWarning: unclosed file` warnings in older test files (`test_compendium.py`, `test_editor.py`, `test_instances_registry.py`) where file handles used `open().read()` without a `with` context manager.
- **Impact:** Harmless in test runners; all file handles are reclaimed upon test process exit.

### 3. Environmental: Optional User Oracle Save Fixture
- **Description:** `test_compendium.py` conditionally tests against a live user save if present at `C:\Users\kufis\p5r_buff_save\DATA11\DATA.DAT`. On clean environments or CI where this path does not exist, the test gracefully falls back to synthetic fixtures without error.

---

## H. TOP 5 AUDIT PRIORITIES FOR ADVERSARIAL REVIEW

For the GPT-6 adversarial review, prioritize these five critical components:

### 1. Two-Phase Atomic Disk Persistence & Rollback Engine
- **File:** [`core/atomic_writer.py`](file:///E:/ai-workspace/knowledge-base/projects/p5r-save-editor/core/atomic_writer.py)
- **Functions:** `atomic_write_save()` (lines 120–225), `verify_save_bytes()` (lines 42–118)
- **Review Question:** Does `os.replace` on Windows guarantee atomicity across NTFS boundaries, and does the exception handler cleanly unlink the temporary file without leaving orphan `.coh_tmp_*` files on physical write failure?

### 2. Transactional Session Commits & Concurrency Conflict Isolation
- **File:** [`core/session.py`](file:///E:/ai-workspace/knowledge-base/projects/p5r-save-editor/core/session.py)
- **Functions:** `SaveSession.commit_transaction()` (lines 269–340), `apply_modifications_to_editor()` (lines 96–268)
- **Review Question:** Does cloning `SaveEditor(self.baseline_bytes)` guarantee complete isolation against partial mutation if candidate packing throws an exception mid-transaction?

### 3. Compendium Gap Zeroing Removal & Dual Mirror Parity
- **File:** [`core/editor.py`](file:///E:/ai-workspace/knowledge-base/projects/p5r-save-editor/core/editor.py) & [`core/binary_oracle.py`](file:///E:/ai-workspace/knowledge-base/projects/p5r-save-editor/core/binary_oracle.py)
- **Functions:** `SaveEditor.set_compendium_registration()`, `SaveEditor.unlock_compendium_100()`, `audit_save_mutation()`
- **Review Question:** Does preserving the 2,496-byte gaps at `0x09460` and `0x21970` bitwise match official game-saved states, and does 100% compendium unlocking accurately write exactly 224 live mask bits across both mirrors?

### 4. Local API Security & Origin/Host Header Enforcement
- **File:** [`server.py`](file:///E:/ai-workspace/knowledge-base/projects/p5r-save-editor/server.py)
- **Functions:** `P5RWebHandler._host_allowed()` (lines 416–423), `_origin_allowed()` (lines 424–440), `/api/restore` path verification (lines 676–710)
- **Review Question:** Can a malicious browser tab executing JavaScript trigger an unauthorized save write or arbitrary file overwrite via DNS rebinding or path traversal?

### 5. Cross-Save Semantic Transfer Logic
- **File:** [`server.py`](file:///E:/ai-workspace/knowledge-base/projects/p5r-save-editor/server.py)
- **Functions:** Route `/api/transfer` (lines 748–789)
- **Review Question:** Does transferring compendium or inventory data from an external donor save preserve internal IDs without causing state desynchronization in the destination save?

---

## I. REPOSITORY STATE

- **Base Branch:** `origin/main` (`https://github.com/j0nnyDiGITAL/change-of-heart`)
- **Base Commit SHA:** `22818e8b48f88275c5f86eaa18400dc4867714de`
- **Review Branch:** `feature/change-of-heart-2.0`
- **Committed Changes Ahead of Base:** 7 commits
- **Working Tree Status:** Clean (zero uncommitted or untracked modifications)
- **Publication Risks:** Zero. No proprietary Atlus game assets (ROMs, audio, video, custom fonts) or credentials have been committed. All release binaries remain in `dist/` which is ignored by `.gitignore`.
