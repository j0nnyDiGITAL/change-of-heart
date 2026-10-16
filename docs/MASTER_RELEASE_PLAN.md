# MASTER RELEASE PLAN — OPERATION CHANGE OF HEART
## Master Engineering, Security, Feature Completion & P5R-Native Redesign Work Order

**Project:** Change of Heart — Persona 5 Royal Save Editor  
**Repository:** https://github.com/j0nnyDiGITAL/change-of-heart  
**Owner:** j0nnyDiGITAL  
**Date:** October 16, 2026  
**Status:** In Progress — Phase 0 Complete / Advancing to Phase A (Save Integrity & Transactions)  
**Execution Order:** Save Integrity > Correctness > Feature Completeness > Usability > Visual Fidelity > Maintainability

---

## 1. Executive Mission & Autonomy Contract

This master release campaign delivers the final major feature and design release of **Change of Heart**, turning the existing high-performance binary save editor into an established, hardened, safe, visually stunning, and complete desktop studio suitable for long-term use with minimal maintenance.

The workflow operates under strict, evidence-driven gates:
1. **Never fabricate missing data or claim unexecuted tests passed.**
2. **Never mutate real player game saves during tests.**
3. **Never silently overwrite or auto-repair unexplained binary data.**
4. **Preserve all existing cryptographic, inventory, confidant, and compendium reverse-engineering discoveries.**
5. **A successful partial implementation is acceptable; a falsely certified release is not.**

---

## 2. Phase-by-Phase Roadmap & Milestones

| Phase | Milestone | Priority | Gate / Verification Criteria | Status |
|---|---|---|---|---|
| **Phase 0** | **Reconnaissance & Baseline** | P0 | 190/190 tests pass; branch comparison complete; assets inventoried; baseline audit ledgers initialized. | **DONE** |
| **Phase A** | **Save Integrity & Transaction Engine** | P0 | Two-phase atomic writes; session capability tokens; dirty-state revision tracking; fault injection tests pass; zero disk corruption on error. | **READY** |
| **Phase B** | **Local API & Frontend Security** | P1 | Process-local capability token; Host/Origin validation; request bounds; XSS/DOM injection sanitization; sanitized error handling. | PENDING |
| **Phase C** | **Binary Correctness & Historical Protections** | P1 | Compendium zeroing gap eliminated; exact byte preservation verified; 10-category inventory verified; permanent regression suite green. | PENDING |
| **Phase D** | **Final Feature Completion** | P2 (P0 safety) | Save Inspector; Save Comparison (semantic + binary diff); Staged Change Review drawer; Backup/Rollback Manager; Cross-Save Transfer; Preset Portability. | PENDING |
| **Phase E** | **P5R Native-Menu Redesign** | Major | Joker Status 1920x1080 vertical slice; asymmetrical angles; Velvet Room; Airsoft Items; Confidants; Keyboard/Controller navigation; Offline original art fallback. | PENDING |
| **Phase F** | **Comprehensive Testing & Verification** | Gate | Unit + integration + fault injection; multi-save oracle diffs; manual in-game acceptance matrix documented; UI QA across display scaling. | PENDING |
| **Phase G** | **Performance & Maintainability** | P2 | <100ms virtual scroll SLA; in-memory caching verified; comprehensive developer architecture docs. | PENDING |
| **Phase H** | **Packaging & Release Closure** | Gate | Standalone PyInstaller frozen binary (`P5R_Save_Editor.exe`); D011 live process smoke test; SHA256 release checksums; documentation 100% synced. | PENDING |

---

## 3. Active Workstream Decomposition

- **Workstream 1 (Save Engine):** Two-phase atomic writer (`tempfile` -> `fsync` -> reparse -> `os.replace` -> readback verification), `SaveSession` transaction model, write locks.
- **Workstream 2 (Security):** Process-local cryptographically unpredictable token generation (`secrets.token_hex(24)`), Host/Origin strict loopback checking, DOM textContent escaping, Content Security Policy headers.
- **Workstream 3 (Binary Correctness & Features):** Elimination of arbitrary 2,496-byte gap zeroing (`0x09460..0x09940`, `0x21970..0x21E50`), Save Inspector, Save Compare engine, semantic Cross-Save Transfer.
- **Workstream 4 (UI Redesign & Interaction):** 1920x1080 P5R Native UI styling, cut-paper ransom-note typography, asymmetrical angular polygons, accessible keyboard/focus navigation, asset fallback mode.
- **Workstream 5 (QA & Windows Packaging):** Automated test suite expansion, fault injection test harness, PyInstaller freeze, standalone binary smoke testing.
