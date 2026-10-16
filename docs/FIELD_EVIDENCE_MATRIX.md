# FIELD EVIDENCE MATRIX — PERSONA 5 ROYAL (PC / STEAM)

**Project:** Change of Heart — Persona 5 Royal Save Editor  
**Repository:** https://github.com/j0nnyDiGITAL/change-of-heart  
**Date:** October 16, 2026  
**Authoritative Reference:** Atlus PC Save Container format, `data/` reference tables, and multi-save oracle diffs.

---

## 1. Classification Definitions

1. **Verified Writable:** Offset, length, endianness, and mirror verified across multiple saves; safe to modify; covered by automated regression tests.
2. **Verified Read-Only:** Verified decoding for display, but writing is not yet safe or requires story flag coordination.
3. **Experimental:** Isolated under explicit developer flag or diagnostics; requires multi-save proof before normal UI enablement.
4. **Unsupported / Frozen:** Unmapped, uncertain, or known to cause game instability if modified.

---

## 2. Master Binary Field Evidence Table

| Category | Field Name | Decrypted Offset | Size / Type | Mirror Offset | Verification Status | Confidence | Source Evidence / Notes |
|---|---|---|---|---|---|---|---|
| **Header** | Outer CRC32 | Container `0x0004` | `u32` (LE) | None | Verified Writable | 100% | CRC32 of container bytes `0x0008` through EOF. Verified across all saves. |
| **Header** | Magic Header | Container `0x0000` | 4 bytes (`b"DATA"`) | None | Verified Read-Only | 100% | Constant Atlus magic. Must never be altered. |
| **Header** | Save Flags / AES | Container `0x000C` | `u32` (LE) | None | Verified Writable | 100% | Bit 31 (`0x80000000`) = AES-256-CBC encrypted payload. |
| **Header** | Container IV | Container `0x0010` | 16 bytes | None | Verified Writable | 100% | Random 16-byte initialization vector generated per save. |
| **Header** | Inner Data CRC32 | Container `0x002C` | `u32` (LE) | None | Verified Writable | 100% | CRC32 of uncompressed decrypted data payload. |
| **Quick Info** | Protagonist First Name | Header `0x0018` | 16 bytes (UTF-8) | `0x13840` (`0x31` PC) | Verified Writable | 100% | Truncated at 15 bytes + null. Synced with PC 0x31 block. |
| **Quick Info** | Protagonist Last Name | Header `0x0028` | 16 bytes (UTF-8) | `0x13864` (`0x31` PC) | Verified Writable | 100% | Truncated at 15 bytes + null. Synced with PC 0x31 block. |
| **Quick Info** | Phantom Thieves Name | Header `0x0038` | 24 bytes (UTF-8) | `0x13888` (`0x31` PC) | Verified Writable | 100% | Truncated at 23 bytes + null. Atlus 2-byte wrapper `0x8090` + glyphs. |
| **Quick Info** | Playtime Counter | Header `0x0008` | `u32` (Seconds) | Data `0x000C` | Verified Read-Only | 95% | None-tolerant parser in v1.1.3; read-only to avoid desyncing Steam stats. |
| **Economy** | Money / Yen (¥) | Data `0x035C0` | `u32` (LE) | None | Verified Writable | 100% | Max ¥9,999,999. Tested isolated from EXP. |
| **Social Stats** | Knowledge / Charm / Proficiency / Guts / Kindness | Data `0x139E0` | 5 x `u16` (LE) | None | Verified Writable | 100% | Stored as points at `0x139E0`; surplus preserved. |
| **Confidants** | Confidant Structs (24 Arcana) | Data `0x136A0` | 16-byte stride | None | Verified Writable | 100% | Stride: `[6 pad][u16 ID][u16 Rank][u16 Points][4 pad]`. Surplus preserved. |
| **Confidants** | Romance Flag | Data `0x136A0 + offset + 0x0A` | Bit 0x02 | None | Verified Writable | 100% | Rank 9+ romance toggle. Warning displayed for cutscene skip. |
| **Party** | Joker / Party Stats (HP/SP/Level) | Data `0x0050` | Fixed stride | None | Verified Writable | 100% | Level (1-99), HP, SP. Cubic EXP curve auto-synced. |
| **Party** | Teammate Persona Evolution Tier | Data `0x0050` party structs | `u16` PID | None | Verified Writable | 100% | Scoped to `TEAMMATE_EVOLUTION_IDS` (Tiers 1, 2, 3 only). Foreign swaps blocked. |
| **Personas** | Joker Persona Stock (12 slots) | Data `0x0110` | 48-byte stride | None | Verified Writable | 100% | PID, Level, Stats (St/Ma/En/Ag/Lu), Trait ID, 8 Skill IDs. |
| **Compendium** | Registration Bitmask (232 Personas) | Data `0x09973` (29 bytes) | 232-bit bitfield | `0x21E83` (`+0x18510`) | Verified Writable | 100% | Strict LSB ordering. Synchronized with mirror offset. |
| **Compendium** | Registered Persona Struct Array | Data `0x04270` | 48-byte stride x 437 | `0x1C780` (`+0x18510`) | Verified Writable | 100% | Existing player builds preserved; starter Arsene template verified. |
| **Inventory** | Consumables (338 items) | Data `0x02534..0x02A80` | `u8` count per slot | None | Verified Writable | 100% | Universal Engine Offset Formula (`addr - 0x0226F024`). |
| **Inventory** | Infiltration Tools & Materials | Data `0x031B0..0x03478` | `u8` count per slot | None | Verified Writable | 100% | Tools & crafting components verified contiguous mapping. |
| **Inventory** | Skill Cards (`0x4000`) | Data `0x13000` block | `u8` count array | None | Verified Writable | 100% | Fixed `+1` BLANK-row offset alignment verified. |
| **Inventory** | Melee Weapons (`0x1000`) | Data `0x02000` block | 1-bit owned flag | None | Verified Writable | 100% | Ownership flag matrix verified across 9 party members. |
| **Inventory** | Ranged Weapons (`0x2000`) | Data `0x02050` block | 1-bit owned flag | None | Verified Writable | 100% | Ownership flag matrix verified. |
| **Inventory** | Protectors / Armor (`0x5000`) | Data `0x13000` block | 1-bit owned flag | None | Verified Writable | 100% | Fixed `+1` BLANK-row offset alignment verified. |
| **Inventory** | Accessories (`0x7000`) | Data `0x13000` block | 1-bit owned flag | None | Verified Writable | 100% | Validated against `Accessories.txt` (filtered dummy `0x3170`). |
| **Inventory** | Treasure / Loot (`0x8000`) | Data `0x13000` block | `u8` count array | None | Verified Writable | 100% | Fixed `+1` BLANK-row offset alignment verified. |
| **Inventory** | Key Items (`0x9000`) | Data `0x02900` block | Bitfield / flag | None | Verified Writable | 95% | Mapped via `core/key_item_offsets.py`. |
| **Inventory** | Outfits (`0xA000`) | Data `0x03530` / unverified | Unknown | None | FROZEN (D008) | 40% | Read-only in UI. Writing blocked until 2-save diff proves PC offsets. |
| **Progression** | 3rd Semester Story Matrix | Event Flag Matrix (`43,008` bits) | Bitfield | Unknown | Read-Only | 95% | Read-only eligibility diagnostics; 1-click write retired (D009). |
| **Progression** | Baton Pass & Technical Ranks | Unknown | Unknown | Unknown | Research Target | 30% | Read-only observation target. No write support without evidence. |
| **Progression** | Jazz Club Growth Bonuses | Party stats block | Unknown | Unknown | Research Target | 30% | Under investigation. |
