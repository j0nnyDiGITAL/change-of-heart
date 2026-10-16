# FEATURE COMPLETENESS MATRIX — OPERATION CHANGE OF HEART

**Project:** Change of Heart — Persona 5 Royal Save Editor  
**Repository:** https://github.com/j0nnyDiGITAL/change-of-heart  
**Date:** October 16, 2026  
**Status:** Baseline Audited  

---

## 1. Feature Classification Summary

- **Implemented & Verified (Writable):** Core features verified by automated unit tests and multi-save diffs.
- **Implemented (Read-Only Diagnostics):** Displayed safely with zero write capability.
- **Planned for Final Release (Phase D):** Save Inspector, Save Compare, Staged Changes, Recovery Manager, Cross-Save Transfer.
- **Unsupported / Frozen:** Intentionally disabled to protect save integrity (e.g. Outfit `0xA000` writes, arbitrary Event Matrix writes).

---

## 2. Granular Feature Breakdown

| Domain | Feature | Capability State | UI Availability | Backend Endpoint | Test Coverage |
|---|---|---|---|---|---|
| **Save Engine** | AES-256 Decryption & Unpacking | Verified | Active | Internal (`core/crypto.py`) | 190/190 passing |
| **Save Engine** | Dual-Layer CRC32 Calculation | Verified | Active | Internal (`core/crypto.py`) | Tested in `test_editor.py` |
| **Save Engine** | Two-Phase Atomic Save Writes | Planned (Phase A) | In Progress | `/api/save` | Ready for implementation |
| **Save Engine** | Session-Based Transaction State | Planned (Phase A) | In Progress | `/api/load`, `/api/save` | Ready for implementation |
| **Save Engine** | Concurrency Conflict Detection | Planned (Phase A) | In Progress | HTTP 409 Conflict | Ready for implementation |
| **Diagnostics** | Save Inspector | Planned (Phase D1) | In Progress | `/api/inspect` | Read-only structural analysis |
| **Diagnostics** | Save Comparison (Semantic & Binary) | Planned (Phase D2) | In Progress | `/api/compare` | Two-save diff analysis |
| **Diagnostics** | Staged Change Review Drawer | Planned (Phase D3) | In Progress | Frontend Staging Drawer | Revert individual or all |
| **Safety** | Immutable ZIP Backups | Verified | Active | `/api/save`, `/api/restore` | Tested in `test_backup_fix.py` |
| **Safety** | Backup & Recovery Manager | Planned (Phase D4) | In Progress | `/api/backups`, `/api/restore` | Preview before rollback |
| **Portability** | Cross-Save Semantic Transfer | Planned (Phase D5) | In Progress | `/api/transfer` | Validated field transfer |
| **Portability** | Persona Preset Import / Export | Planned (Phase D11)| In Progress | `/api/presets` | Typed JSON presets |
| **Compendium** | 100% Compendium Genuine Unlock | Verified | Active | `/api/save` (`unlock_compendium`) | Dual mask + template preservation |
| **Compendium** | Granular 232-Persona Matrix Toggle | Verified | Active | `/api/save` (`compendium.registered`)| Verified in `test_compendium.py` |
| **Compendium** | DLC & Treasure Demon Batch Filters | Verified | Active | Frontend filter chips | Tested in `test_guardrails_features.py` |
| **Compendium** | Existing Player Custom Build Retention | Verified | Active | `/api/save` | Tested in `test_reddit_bugfixes.py` |
| **Party & Joker** | Protagonist Name Editing (UTF-8) | Verified | Active | `/api/save` (`header.fname`, `lname`)| Glyphs + 0x31 sync verified |
| **Party & Joker** | Phantom Thieves Group Name (0x8090) | Verified | Active | `/api/save` (`header.group_name`) | Glyphs + Atlus wrapper verified |
| **Party & Joker** | Money / Yen (¥) Editing | Verified | Active | `/api/save` (`header.money`) | Isolated from EXP |
| **Party & Joker** | Social Stats Points & Ranks (1-5) | Verified | Active | `/api/save` (`social_stats`) | Carryover preserved |
| **Party & Joker** | Party HP / SP / Level (1-99) | Verified | Active | `/api/save` (`party`) | Cubic EXP curve auto-sync |
| **Party & Joker** | Teammate Persona Evolution Tier (1-3)| Verified | Active | `/api/save` (`party.persona_id`) | Scoped to authentic evolutions |
| **Party & Joker** | 12-Slot Joker Persona Stock Studio | Verified | Active | `/api/save` (`joker_stock`) | PID, stats, traits, 8 skills |
| **Party & Joker** | Tournament God Build Presets | Verified | Active | Frontend Quick Presets | Yoshitsune, Izanagi, Raoul, Alice |
| **Party & Joker** | Elemental Affinity Resistance Matrix | Verified | Active | Frontend Velvet Badge Engine | All 9 elements x 4 tiers |
| **Confidants** | 24 Arcana Rank Editing (0-10) | Verified | Active | `/api/save` (`confidants`) | Story prerequisites enforced |
| **Confidants** | Bond-Points Surplus Preservation | Verified | Active | `/api/save` | Tested in `test_bond_points.py` |
| **Confidants** | Rank 9+ Romance Flag Toggle (0x02) | Verified | Active | `/api/save` (`romance`) | Cutscene skip advisory displayed |
| **Inventory** | In-Game Bag View (Carried Items Only)| Verified | Active | Frontend Item Studio Left Pane | Real-time ownership filter |
| **Inventory** | + ADD ITEM 2,204-Item Catalog Drawer | Verified | Active | Frontend Item Catalog Modal | Search, category chips, +1x/+99x |
| **Inventory** | 10-Pocket Category Tab Bar | Verified | Active | Category tabs | Items, Tools, Cards, Gear, Loot, Key |
| **Inventory** | 338 Consumable Items Offset Engine | Verified | Active | `/api/save` (`inventory_normalized`)| Tested in `test_inventory_s1.py` |
| **Inventory** | Tools, Cards, Gear, Loot Ownership | Verified | Active | `/api/save` (`inventory_normalized`)| Tested in `test_reddit_bugfixes.py` |
| **Inventory** | Outfits Category (`0xA000`) | FROZEN (D008) | Read-Only | Read-only in UI | Writable write blocked safely |
| **Progression** | 3rd Semester Eligibility Diagnostics | Read-Only | Read-Only | `/api/inspect` | Story flag matrix is read-only |
| **Progression** | Baton Pass & Technical Ranks | Research | Diagnostics | Read-Only | Unsupported write |
| **Progression** | Jazz Club Growth Bonuses | Research | Diagnostics | Read-Only | Unsupported write |
