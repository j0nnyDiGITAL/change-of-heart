# RELEASE VERIFICATION — OPERATION CHANGE OF HEART

**Project:** Change of Heart — Persona 5 Royal Save Editor  
**Repository:** https://github.com/j0nnyDiGITAL/change-of-heart  
**Date:** October 16, 2026  
**Target Release:** Final Major Release  
**Status:** In Progress — Phase 0 Baselines Verified  

---

## 1. Hard Release Gates Checklist

### A. Save Safety & Data Integrity (P0)
- [ ] Source corruption detected and ordinary writes blocked.
- [ ] Normal saves and restores use two-phase atomic write sequence (`.tmp` -> `fsync` -> reparse -> `os.replace` -> readback).
- [ ] Backups created and validated before replacement.
- [ ] Concurrent sessions cannot silently overwrite data (HTTP 409 Conflict).
- [ ] Unknown / unmapped bytes preserved bitwise.
- [ ] Arbitrary 2,496-byte compendium gap zeroing eliminated.
- [ ] All 10 inventory categories verified against Universal Engine Offset Formula.
- [ ] All historical regression tests green.

### B. Security & Trust Boundary (P1)
- [ ] Process-local capability token enforced on all mutating API endpoints (`X-Session-Token`).
- [ ] Strict loopback Origin and exact Host port validation.
- [ ] Payload bounds enforced (32 MB body cap, 5 MB save cap, max zlib expansion).
- [ ] ZIP path traversal defense verified.
- [ ] DOM injection / XSS sanitized in frontend catalog and search rendering.
- [ ] API error responses sanitized (no raw local filesystem paths or token leakage).

### C. Feature Completeness (P2 / P0 Safety)
- [ ] Save Inspector screen operational with structural integrity diagnostics.
- [ ] Save Comparison (semantic + binary diff) operational.
- [ ] Staged Change Review drawer with individual / all revert operational.
- [ ] Backup & Recovery Manager operational.
- [ ] Semantic Cross-Save Transfer operational for verified fields.
- [ ] All existing editing capabilities (compendium, inventory, confidants, party, god presets) fully functional.
- [ ] Progression diagnostics accurately describe their limitations (no false promises).

### D. P5R Native UI Redesign
- [ ] 1920x1080 Joker Status screen matching official reference composition.
- [ ] Velvet Room, Untouchable Inventory, Confidant Dossier screens styled authentically.
- [ ] Keyboard navigation verified across all screens.
- [ ] Reduced-motion mode available and verified.
- [ ] Offline original-art / SVG fallback mode verified without proprietary assets.

### E. Packaging & Verification
- [ ] 100% automated test suite passing (baseline 190 tests + new security/atomic tests).
- [ ] Fault injection tests pass at all write checkpoints.
- [ ] Standalone Windows binary (`dist/P5R_Save_Editor.exe`) built via PyInstaller.
- [ ] D011 live process smoke test passed on packaged binary.
- [ ] Release archive (`CHANGE_OF_HEART_v1.2.0_WINDOWS.zip`) packaged with verified SHA-256.
- [ ] Documentation (`README.md`, `CHANGELOG`, `docs/FAQ.md`, `STATUS.md`, `state.json`) 100% synchronized.
