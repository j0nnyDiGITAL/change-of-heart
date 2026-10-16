# SECURITY REMEDIATION LEDGER — OPERATION CHANGE OF HEART

**Project:** Change of Heart — Persona 5 Royal Save Editor  
**Repository:** https://github.com/j0nnyDiGITAL/change-of-heart  
**Date:** October 16, 2026  
**Status:** Audit Confirmed / Remediation in Progress  

---

## 1. Executive Summary

This ledger tracks the confirmation status, remediation plan, implementation details, test coverage, and remaining risks for each of the 12 core security and reliability findings identified in the master work order.

---

## 2. Findings & Remediation Ledger

| ID | Finding / Vulnerability | Severity | Codebase Confirmation | Target Remediation | Target Files | Verification Tests | Status |
|---|---|---|---|---|---|---|---|
| **SEC-01** | **Direct Non-Atomic Save Writes** | P0 (Critical) | Confirmed (`server.py` line 780: `p.write_bytes(out_bytes)` directly overwrites target file) | Two-phase atomic write sequence: write to `.tmp`, `flush` & `os.fsync`, reparse & verify candidate, check external mtime/hash, atomic `os.replace`, read back persisted bytes | `core/environment.py`, `server.py` | `test_atomic_save_writes.py` (fault injection at every step) | READY |
| **SEC-02** | **Permissive Input & Container Validation** | P0 (Critical) | Confirmed (`core/crypto.py` lines 111, 150 only print `[Warning]` on CRC mismatch; `SaveEditor` allows editing corrupted saves) | Strict integrity gate: reject corrupted/mismatched containers on normal save; surface clear diagnostics in Save Inspector; provide safe isolated recovery export | `core/crypto.py`, `core/editor.py`, `server.py` | `test_container_validation.py` | READY |
| **SEC-03** | **Global Mutable Editor State** | P0 (High) | Confirmed (`server.py` uses module globals `CURRENT_EDITOR`, `CURRENT_FILE_PATH`, `CURRENT_ORIGINAL_BYTES`) | Encapsulate state in `SaveSession` manager with unique session ID, cryptographically secure capability token, immutable baseline bytes, dirty-state revision counter | `server.py`, `core/session.py` | `test_session_transactions.py` | READY |
| **SEC-04** | **Concurrency & Silent Last-Write-Wins** | P1 (High) | Confirmed (`server.py` lines 805-809 only prints a warning notice without blocking concurrent overwrite) | Enforce revision tokens and file lock/mtime check. Return HTTP 409 Conflict if on-disk save or revision changed externally | `server.py`, `core/session.py` | `test_concurrency_conflict.py` | READY |
| **SEC-05** | **Whole-Form Indiscriminate Serialization** | P1 (High) | Confirmed (`server.py` iterates whole form arrays unless normalized payload is supplied) | Staged changes model: track explicit typed patches; validate setters; preserve unedited decrypted payload bytes exactly | `server.py`, `web-app/static/app.js` | `test_staged_changes.py` | READY |
| **SEC-06** | **Loopback Trust Boundary & Missing Auth Token** | P1 (High) | Confirmed (`server.py` has loopback origin check D013, but lacks process-local capability token or Host header binding) | Generate process-local `session_token` on startup via `secrets.token_hex(24)`, validate `X-Session-Token` header on all mutating endpoints (`/api/save`, `/api/restore`), enforce exact Host port match | `server.py`, `main.py`, `web-app/static/app.js` | `test_api_security.py` | READY |
| **SEC-07** | **Unbounded API Payload & Decompression Limits** | P1 (Medium) | Confirmed (`server.py` reads `content_length` without size cap; base64 decode and zlib decompress have no max size guard) | Cap HTTP body at 32 MB; cap save uploads at 5 MB; enforce `max_length` on zlib decompressed output; validate ZIP paths to prevent path traversal (`..`) | `server.py`, `core/crypto.py`, `core/environment.py` | `test_payload_limits.py` | READY |
| **SEC-08** | **DOM Injection / XSS in Frontend Rendering** | P1 (Medium) | Confirmed (`web-app/static/app.js` lines 2431, 2539, 2727 interpolate unescaped strings directly into `innerHTML`) | Replace unsafe `innerHTML` interpolations with safe DOM construction (`textContent`, `createElement`) or robust `escapeHtml()`; configure Content-Security-Policy | `web-app/static/app.js`, `server.py`, `web-app/templates/index.html` | `test_dom_sanitization.py` | READY |
| **SEC-09** | **Error Sanitization & Path Disclosure** | P2 (Medium) | Confirmed (`server.py` lines 555, 572 return `str(e)` which can contain raw local filesystem paths) | Sanitize user-facing API error responses; separate public errors from developer internal diagnostic logs | `server.py` | `test_error_sanitization.py` | READY |
| **SEC-10** | **Broad Compendium Gap Zeroing (2,496 Bytes)** | P1 (High) | Confirmed (`server.py` line 770 zeroes `0x09460..0x09940` and `0x21970..0x21E50` on any compendium edit) | Eliminate blanket gap zeroing; restrict writes strictly to verified 48-byte persona slots and bitmask bytes; preserve all unmapped/unknown bytes | `server.py`, `core/editor.py` | `test_compendium_preservation.py` | READY |
| **SEC-11** | **Inventory Category Mapping & Cache Consistency** | P1 (High) | Confirmed (Historical Reddit bugs fixed, but secondary caches must never desync from master writes) | Re-verify all 10 categories against Universal Engine Offset Formula; guarantee atomic sync between master tables and quick arrays; freeze unverified categories | `core/editor.py`, `core/consumable_offsets.py` | `test_inventory_consistency.py` | READY |
| **SEC-12** | **Binary Mutation Regression & Invariant Verification** | P1 (High) | Confirmed (Unit tests test individual components, but lack unified automated binary-diff invariant oracle) | Build `tools/binary_diff_oracle.py` that verifies exact changed offsets against an approved field map for every mutation | `tools/binary_diff_oracle.py`, `tests/test_binary_invariants.py` | `test_binary_invariants.py` | READY |
