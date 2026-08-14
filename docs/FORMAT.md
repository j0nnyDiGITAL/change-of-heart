# P5R Steam Save Format — Verified Map

Complete, in-game-verified layout of the Persona 5 Royal (Steam) save format.
Native PC saves use payload version `0x31`. All offsets are relative to the
decrypted payload, verified against a 100% NG++ oracle save + 7-save ladder.

## Container envelope

| Field | Layout |
|---|---|
| Magic | `DATA` (4 bytes) |
| Outer CRC | u32 @ 0x04 (CRC-32/MPEG-2 over bytes from 0x08) |
| Timestamp / flags | u32 @ 0x08 / 0x0C |
| IV | 16 bytes @ 0x10 |
| Payload | AES-256-CBC from 0x20; inner header + zlib data blocks |
| Inner data CRC | u32 in meta block (over decompressed data bytes) |

Re-sign = recompute inner CRC, repack, re-encrypt, recompute outer CRC.
Both CRCs use the Atlus CRC-32 engine (poly `0x04C11DB7`).

## Core fields (all verified)

| Field | Offset | Type | Notes |
|---|---|---|---|
| Money | `0x35C0` | u32 | + mirror u32 @ `0x3C` in Joker's party struct |
| Social stats | `0x139E0` | 5× u16 | Knowledge, Charm, Proficiency, Guts, Kindness — **points**, not ranks |
| Day counter | `0x3D70` | u16 | +1 per in-game day |
| Event flags | `0x2F200–0x30700` | bitfield | set-once story/confidant/event state |
| Activity log | `0x17050` | text | high-level calendar/history log |

## Confidants @ `0x136A0`

23 entries × 16 bytes:

```
[6 pad][u16 save_id @+6][u16 rank @+8][u16 points @+10][4 pad]
```

- Arcana IDs: 1–21 in arcana order; Faith = 33 (pre-reveal) / 36 (post-reveal); Councillor = 35
- Verified in-game via rank-ramp probe (rank writes display correctly)
- Story-locked confidants (Fool, Magician, Moon, Sun, Strength, Judgement) follow plot — ranks are display-only there

## Party @ `0x2C`

10 members × stride `0x2B0`:

| Member | HP | SP | Level |
|---|---|---|---|
| Slot 0 (Joker) | u16 @ +0 | u16 @ +4 | u8 @ +0xC |
| Slots 1+ | u16 @ +0 | u16 @ +4 | u8 @ +0x3C (flag `0x1001` @ +0x38) |

Verified against in-game screenshots + the 100% oracle save.
Max HP/SP are **derived** from level + persona — proven NOT stored (series scan).

## Persona stock

Per member: 12 slots × stride `0x30`, base = member + `0x38`. Slot 0 = equipped (positional, not flag-based).

```
[flags u16 @+0][id u16 @+2][level u8 @+4][unk u8 @+5][trait u16 @+6]
[EXP u32 @+8][8× skill u16 @+0xC][5× stat u8 @+0x1C]
```

## Compendium registration bitmask — `0x09973` (+ mirror `0x21E83`)

**The last unmapped block in the format, solved 2026-08-14.**

- 232-bit LSB-first bitmask; bit index `i` = persona save-ID `(i + 1)` (0x001..0x0E8)
- Mirror copy at `+0x18510` — **write both**
- Verified across 7 saves: 0 (April) → 33 (June 15) → 217 (oracle) → 224 (clear data)
- Strictly monotone within a playthrough; resets per NG+ cycle
- 217/217 set bits map to valid Personas.txt IDs
- Editor persona-stock writes do NOT touch this mask (registration is scene-written)

## Items

- Item ID encoding: upper 4 bits = category, lower 12 = table row
  (`0x1000` melee … `0x9000` key items)
- Name tables in `data/` (2,400+ entries across 9 categories)
- Acquisition ring buffer @ `0x3530` (30 × [u16 id][u16 flag], head = newest)
- Item count bytes are sparse, ID-indexed — not a uniform array

## Known NOT stored

| Field | Proof |
|---|---|
| Max HP / SP | value-series scan: only current-HP offset matches across saves |
| Baton pass / technical / stamp ranks | oracle-vs-baseline byte-identical; the "3"s are static member IDs |

## Safety rules for writers

1. Never edit a live save while the game runs (Steam Cloud race).
2. Always re-sign both CRCs after mutation.
3. Unknown format ⇒ preserve verbatim + honest `unsupported` — never fabricate records over unmapped regions.
4. Write both mirror copies (compendium, money, event flags at `+0x18500/0x18510` family).
