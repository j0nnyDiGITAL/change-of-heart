# CHANGE OF HEART 2.0 — ADVERSARIAL AUDIT REMEDIATION & OPENDESIGN HANDOFF REPORT
## Comprehensive Engineering, Security, Transaction Integrity and Visual Course-Correction Ledger

**Project:** Change of Heart 2.0 — Persona 5 Royal Save Studio  
**Repository:** `https://github.com/j0nnyDiGITAL/change-of-heart`  
**Working Branch:** `feature/change-of-heart-2.0`  
**Pull Request:** `https://github.com/j0nnyDiGITAL/change-of-heart/pull/7` (Draft)  
**Date:** October 16, 2026  
**Engineering Orchestrator:** Antigravity  
**Visual Design Authority:** OpenDesign  
**Repository Owner / Final Sign-off:** j0nnyDiGITAL  

---

# 1. EXECUTIVE SUMMARY & DUAL MANDATE

This engineering document reports the successful resolution of two concurrent critical developments for Change of Heart 2.0:

1. **Independent Adversarial GPT-6 Security & Integrity Audit:** An independent audit identified several release-blocking vulnerabilities across save corruption validation, capability session authorization, browser origin validation, staged transaction bindings, atomic write recovery, and archive bounds.
2. **Owner Course Correction on Visual Redesign:** The repository owner explicitly rejected the Phase E visual overhaul (characterizing it as a conventional web dashboard styled with Persona-themed colors and heavy typography rather than an authentic in-game Persona 5 Royal menu system). Visual redesign has been formally halted in engineering and reassigned to **OpenDesign**.

Every identified vulnerability has been fully remediated, verified against targeted adversarial regression tests, and gated through AGY-OS invariant checks. All 242 automated tests pass cleanly.

---

# 2. AUDIT FINDINGS & REMEDIATION INVENTORY

### Finding 1 (P0): Corrupted Source Save Write Protection
- **Vulnerability:** `SaveContainer.unpack_raw()` logged `[Warning]` on outer and inner CRC-32 mismatches without raising an exception. Consequently, corrupted or truncated save files could enter writable sessions, allowing preexisting damage to be repackaged and written back to disk, destroying recoverable save data.
- **Root Cause:** Permissive CRC warning-only mode designed for diagnostics leaked into writable save handling pipelines.
- **Remediation:**
  - `core/crypto.py`: Added `strict_crc: bool = False` to `SaveContainer.unpack_raw()`. When `strict_crc=True`, outer file CRC mismatch, inner data CRC mismatch, non-16-byte encrypted payload alignment, and corrupt header lengths raise `ValueError` immediately.
  - `core/editor.py`: Updated `SaveEditor.__init__` and `load_from_bytes` to pass `strict_crc`.
  - `core/session.py`: `SaveSession.__init__` executes `verify_save_bytes(raw, strict_crc=True)` by default and rejects invalid saves with `SaveValidationError`. Added `read_only_diagnostics: bool = False` flag; when set on damaged saves, the session is marked `is_read_only = True`, permitting read inspection while strictly blocking all mutations (`stage_field_change`, `prepare_staged_transaction`, `commit_transaction`).
  - `server.py`: `/api/load` and `/api/load-upload` enforce `verify_save_bytes(..., strict_crc=True)` and return HTTP 400 with `corrupt: True` on damaged files.
- **Verification:** Covered by 5 dedicated tests in `tests/test_audit_remediation.py::TestCorruptedSaveProtection`.

### Finding 2 (P1): Session Capability Authentication & Token Exposure
- **Vulnerability:**
  - `server.py` contained fallback logic `SESSION_MANAGER.get_session_by_token(token) or SESSION_MANAGER.get_session()`. If an active session existed, unauthenticated callers or cross-origin attackers could execute mutating operations (`/api/save`, `/api/restore`, `/api/stage`, `/api/transfer`) without providing a valid capability token.
  - `GET /api/state` returned the active session's secret `capability_token`, allowing any local or cross-context script to steal the token.
- **Root Cause:** Convenience fallback for single-session desktop use combined with overly broad state serialization.
- **Remediation:**
  - `server.py`: Removed all `or SESSION_MANAGER.get_session()` fallbacks on mutating endpoints. Requests missing a valid token in the `X-Session-Token` header (or JSON body) return HTTP 401 Unauthorized (`Authentication failed: Valid session capability token required`).
  - `server.py`: Removed `"token"` and `"capability_token"` from `GET /api/state`. Returns only public process metadata (`pid`, `save`, `session_id`, `revision`).
  - `core/session.py`: Added `SessionManager.revoke_token(token)` and `SessionManager.revoke_session(session_id)`. Tokens are validated with `secrets.compare_digest`.
- **Verification:** Covered by `tests/test_audit_remediation.py::TestSessionCapabilitySecurity` and `TestServerSecurityAndCORS`.

### Finding 3 (P1): Host, Exact-Port Origin Filtering & CORS Enforcement
- **Vulnerability:**
  - `_origin_allowed()` validated only that the scheme was `http` and the host was loopback, but ignored the port number. A malicious local process on an unrelated port (e.g. `http://localhost:3000` or `http://127.0.0.1:8080`) could execute cross-origin fetch calls against the Change of Heart API.
  - CORS preflight (`OPTIONS`) was unhandled, causing standard browser preflights to fail or behave unpredictably.
  - Server responses lacked cache-busting and anti-framing headers.
- **Root Cause:** Origin validation omitted port binding to the active HTTP listener.
- **Remediation:**
  - `server.py`: `_origin_allowed()` parses incoming Origin headers and strictly validates that scheme is `http`, hostname is loopback (`127.0.0.1`, `localhost`, `::1`), AND port strictly equals `self.server.server_port` (or `self.server.server_address[1]`). Mismatched ports return HTTP 403 Forbidden.
  - `server.py`: Implemented `do_OPTIONS()` handling CORS preflight with `Access-Control-Allow-Methods: GET, POST, OPTIONS`, `Access-Control-Allow-Headers: Content-Type, X-Session-Token`, and `Cache-Control: no-store`.
  - `server.py`: All HTML and JSON responses enforce `Cache-Control: no-store, no-cache, must-revalidate, max-age=0`, `Pragma: no-cache`, and Content-Security-Policy anti-framing (`frame-ancestors 'none'`).
- **Verification:** Covered by `tests/test_audit_remediation.py::TestServerSecurityAndCORS`.

### Finding 4 (P1): Authoritative Staged Transactions & Tamper Revocation
- **Vulnerability:** Staged edits were held loosely in an in-memory dictionary. Clients could prepare staged changes, modify them out-of-band without re-review, and commit changes that were never inspected in the review modal. Furthermore, committed stage tokens could be replayed.
- **Root Cause:** Lack of cryptographic binding between the reviewed patch set, baseline revision, and commit execution.
- **Remediation:**
  - `core/session.py`: Introduced `AuthoritativeTransaction` with `stage_token`, `baseline_revision`, `baseline_sha256`, `patch_set`, deterministic canonical `patch_digest` (SHA-256), and `confirmed` state.
  - `SaveSession.stage_field_change()`: Any mutation executed after confirmation automatically invalidates the prepared transaction (`self.current_transaction = None`), requiring a fresh review cycle.
  - `SaveSession.commit_transaction()`: Enforces that commits with `stage_token` match the confirmed transaction, verified baseline revision, and baseline SHA-256. Replay attacks are blocked via `self.committed_stage_tokens` tracking. Unreviewed direct commits are rejected when unconfirmed staged changes exist.
  - `server.py`: `/api/stage` routes `prepare`, `confirm`, and `clear` actions.
- **Verification:** Covered by `tests/test_audit_remediation.py::TestAuthoritativeStagedTransactions`.

### Finding 5 (P1): Two-Phase Cross-Save Semantic Transfer
- **Vulnerability:** Semantic transfers from donor saves could execute in a single unreviewed step without verifying that destination save revision remained unchanged between preview and application, risking race conditions and silent overwrites.
- **Root Cause:** Lack of an explicit, bound preview-and-confirm transaction workflow for cross-save transfers.
- **Remediation:**
  - `core/session.py`: Implemented two-phase transfer workflow:
    1. `build_transfer_preview(donor_bytes, categories)`: Validates donor and destination saves, builds typed diffs, generates safety warnings, identifies non-transferable safety invariants (Outfits, 3rd Semester Event Flag Matrix), and generates single-use `transfer_token` with 300s TTL.
    2. `confirm_and_commit_transfer(transfer_token, donor_bytes)`: Verifies destination revision, destination baseline SHA-256, donor SHA-256, and immediately consumes `transfer_token` before atomic commit.
  - `web-app/static/app.js`: Updated `executeSemanticTransfer()` to execute two-phase preview and confirmation.
- **Verification:** Covered by `tests/test_audit_remediation.py::TestTwoPhaseTransferIntegrity`.

### Finding 6 (P1/P2): Atomic Writer Post-Replacement Recovery & Rollback
- **Vulnerability:** If candidate verification failed after file replacement on disk (e.g. readback corruption or disk controller fault), the file on disk was left in a corrupted or indeterminate state without automated rollback.
- **Root Cause:** Exception handling in atomic writer lacked automated pre-replacement backup byte restoration.
- **Remediation:**
  - `core/atomic_writer.py`: Introduced structured error hierarchy: `SaveValidationError`, `PreReplacementError`, `PostReplacementError` (with `backup_path` and `recovery_status`), and `ConcurrencyConflictError`.
  - `atomic_write_save()`: Caches pre-replacement baseline bytes. If post-replacement readback or container integrity verification fails, it immediately restores original bytes to the target path and raises `PostReplacementError(recovery_status="recovered_from_backup")`.
- **Verification:** Covered by `tests/test_audit_remediation.py::TestAtomicWriterRollbackAndRecovery`.

### Finding 7 (P1): Bounded ZIP Extraction & Zip-Bomb Mitigation
- **Vulnerability:** Backup restore unzipped archive members without explicit member count ceilings, uncompressed size ceilings, streaming chunk limits, or path traversal validation.
- **Root Cause:** Standard library `zipfile.extract` vulnerability to crafted archives.
- **Remediation:**
  - `core/atomic_writer.py`: Implemented `safe_extract_zip_member(zip_path, target_name)`:
    - Path traversal rejection (`..`, absolute paths, leading slashes, drive letters).
    - Maximum 50 archive members (`MAX_ZIP_MEMBERS = 50`).
    - 16 MB maximum uncompressed member size (`MAX_SAVE_MEMBER_SIZE = 16 * 1024 * 1024`).
    - 32 MB total archive decompression limit (`MAX_TOTAL_ARCHIVE_BYTES = 32 * 1024 * 1024`).
    - 64 KB streaming chunk reads to abort compression bombs with misleading headers.
  - `core/environment.py`: Updated `restore_backup()` to delegate to `atomic_restore_backup()`.
- **Verification:** Covered by `tests/test_audit_remediation.py::TestBoundedZipExtraction`.

---

# 3. VERIFICATION & REGRESSION TEST MATRIX

All changes have been comprehensively tested against the complete test suite.

| Test Suite | File | Tests | Status |
| :--- | :--- | :--- | :--- |
| **Audit Remediation Suite** | `tests/test_audit_remediation.py` | 30 | **PASSED** |
| **Atomic Save Writes** | `tests/test_atomic_save_writes.py` | 13 | **PASSED** |
| **Session Transactions** | `tests/test_session_transactions.py` | 7 | **PASSED** |
| **Inspector & Comparison** | `tests/test_inspector_and_comparison.py` | 8 | **PASSED** |
| **Binary Invariants** | `tests/test_binary_invariants.py` | 5 | **PASSED** |
| **Hardening & Security** | `tests/test_hardening.py` | 54 | **PASSED** |
| **Save Editor Core** | `tests/test_editor.py` | 32 | **PASSED** |
| **Audit Fixes (Dual-Oracle)**| `tests/test_audit_fixes.py` | 17 | **PASSED** |
| **Roundtrip Oracle** | `tests/test_roundtrip_oracle.py` | 13 | **PASSED** |
| **Compendium Preservation** | `tests/test_compendium.py` | 7 | **PASSED** |
| **Inventory & Gear S1** | `tests/test_inventory_s1.py` | 14 | **PASSED** |
| **In-Game Parity** | `tests/test_ingame_parity.py` | 10 | **PASSED** |
| **Reddit Bugfixes** | `tests/test_reddit_bugfixes.py` | 13 | **PASSED** |
| **Guardrails & Backups** | `tests/test_guardrails_features.py` | 8 | **PASSED** |
| **Instance Registry** | `tests/test_instances_registry.py` | 5 | **PASSED** |
| **UI Heartbeat Watchdog** | `tests/test_ui_heartbeat.py` | 2 | **PASSED** |
| **Kasumi & Deadbit Safety** | `tests/test_kasumi_prejoin.py`, etc. | 4 | **PASSED** |
| **Total Automated Tests** | | **242** | **100% PASSED** |

### Additional Gates Passed:
- **AGY-OS Invariant Gate (`scripts/check-invariants.py`):** PASSED (All required files present, state.json/STATUS.md synchronized, zero banned diff patterns).
- **JavaScript Syntax Check (`node --check web-app/static/app.js`):** PASSED.

---

# 4. DESIGN REJECTION & OPENDESIGN HANDOFF

### Owner Decision
The owner rejected the Phase E redesign on aesthetic and interaction grounds:
- Conventional dashboard layout (permanent left nav + top toolbar).
- Monotonous rectangular cards and generic grid containers.
- Heavy uppercase typography and dark red theme that looked like an admin panel rather than Persona 5 Royal.

### Engineering Action Taken
1. **Autonomous Redesign Halted:** No further UI redesign work has been or will be attempted in engineering.
2. **OpenDesign Interface Contract Established:** Authoritative specification delivered in `docs/design/OPENDESIGN_HANDOFF.md`.
3. **Reference Implementation Preserved:** Existing client code in `web-app/static/app.js` and `web-app/templates/index.html` remains functional and serves as an integration reference.
4. **Dedicated Design Branch:** OpenDesign exploration will proceed on `design/p5r-native-overhaul`.

---

# 5. INVARIANT COMPLIANCE LEDGER

| Invariant | Requirement | Status |
| :--- | :--- | :--- |
| **D008: Outfits** | Outfits (`0xA000+`) must remain strictly read-only. | **Compliant** — Excluded in transfer, masked in inventory. |
| **D009: 3rd Semester Flags** | 43,008-bit event flag matrix must remain untouched. | **Compliant** — Event flag matrix byte regions preserved. |
| **D010: Process Conflict** | Saving blocked when `P5R.exe` is running. | **Compliant** — Process check returns HTTP 409 before writes. |
| **D011: Save Integrity** | Save integrity > Correctness > Feature completeness. | **Compliant** — Dual CRC32 check, atomic swap, and rollback. |

---

# 6. PULL REQUEST STATUS & CLOSURE

- **Branch:** `feature/change-of-heart-2.0`
- **Draft PR:** `#7: Change of Heart 2.0 — Final Overhaul (Independent Audit)`
- **PR Status:** Maintained in **Draft** status.
- **Prohibitions Respected:** No squash commits, no rebase of published history, no merge into `main`, and no release tagging (`v2.0.0`) until OpenDesign completes the visual overhaul and the repository owner grants final sign-off.

---
*Signed by Antigravity — Engineering Orchestrator*  
*October 16, 2026*
