# P5R (Steam) — Party Member Persona STOCK Array: LOCATED & DECODED

**Date:** 2026-08-09
**Author:** subagent probe (probe_persona_stock.py / probe_persona_stock2.py)
**Saves used:**
- Oracle (100% NG++, modded): `C:/Users/kufis/p5r_buff_save/DATA11/DATA.DAT`
- Fresh (6/14, Lv22): `E:/ai-workspace/knowledge-base/projects/p5r-save-editor/diff/baseline_DATA02_preprobe.DAT`

---

## 1. CONFIRMED: array base, stride, span

| Property | Value |
| :--- | :--- |
| **Array base (relative to member struct)** | **`+0x38`** |
| **Stride** | **`0x30` (48 bytes)** |
| **Slot count** | **12** |
| **Span (relative)** | `+0x38 .. +0x277` (slot 11 ends at +0x277; `+0x278..` = equipment block, NOT part of array) |
| **Member struct base (absolute)** | `0x2C + slot*0x2B0` (slot 0=Joker … 9=Kasumi) |
| **Equipped persona** | **slot 0** — its id u16 sits at the previously-verified equipped offset `+0x3A`; "equipped" is positional, not a flag |

Absolute examples: Joker array = `0x64..0x2A3`, Ryuji array = `0x314..0x553`.

**This is exactly the PS4 KHSave compendium persona struct, byte-for-byte compatible** (flags u16, id u16, level u8, unk u8, trait u16, exp u32, 8× skill u16, 5× stat u8). Only the array offset differs: PS4 `+0x4C` → PC **`+0x38`** (PS4 member stride 0x2A8 → PC 0x2B0).

## 2. Per-slot field layout (relative to slot base = member + 0x38 + k*0x30)

| Off | Size | Field | Notes |
| :--- | :--- | :--- | :--- |
| `+0x00` | u16 | flags | `0x0001` = owned. `0x1001` = owned + bit `0x1000` (see §5). `0x0000` = empty slot |
| `+0x02` | u16 | persona id | `data/Personas.txt` (1-based hex, e.g. 0x16B=Raoul, 0xF2=William) |
| `+0x04` | u8 | level | 1..99 |
| `+0x05` | u8 | unk | always 0x00 in all samples |
| `+0x06` | u16 | trait id | `data/Traits.txt` |
| `+0x08` | u32 | EXP | |
| `+0x0C` | 8×u16 | skills | `data/Skill ID.txt`; `0x0000` = blank |
| `+0x1C` | 5×u8 | stats | `[St, Ma, En, Ag, Lu]` |
| `+0x21..0x2F` | — | padding | all zero |

**Empty slot = the whole 0x30 bytes are zero.** (Slot 0 id u16 at `+0x3A` == the equipped persona id verified previously: oracle Joker 0x16B=363 Raoul ✓, oracle Ryuji 0xF2=242 William ✓, fresh Ryuji 0xCA Captain Kidd ✓.)

## 3. Decoded samples

### Oracle (NG++) — Joker: 12/12 slots filled
| k | id | Persona | Lv | Trait | EXP | St/Ma/En/Ag/Lu |
| :-- | :-- | :--- | :-- | :--- | --: | :--- |
| 0 | 0x16B | Raoul (equipped) | 85 | Vitality of the Tree | 1,418,647 | 52/55/47/63/45 |
| 1 | 0x0BE | Messiah Picaro | 96 | Hallowed Spirit | 1,763,171 | 57/62/63/56/57 |
| 2 | 0x0C9 | Arsene | 93 | Will of the Sword | 3,033,352 | 53/77/63/86/22 |
| 3 | 0x16E | Izanagi no Okami Picaro | 93 | Country Maker | 1,621,696 | 55/66/59/60/46 |
| 4 | 0x057 | Yoshitsune | 92 | Undying Fury | 1,635,731 | 67/53/55/57/51 |
| 5 | 0x1AB | Fafnir | 92 | Atomic Hellscape | 1,610,938 | 68/59/61/48/47 |
| 6 | 0x0FE | Kohryu | 79 | Chi You's Blessing | 1,114,400 | 44/54/51/54/41 |
| 7 | 0x168 | Izanagi no Okami | 86 | Country Maker | 1,406,124 | 58/60/47/50/50 |
| 8 | 0x0C5 | Asterius Picaro | 97 | Drunken Passion | 2,306,127 | 69/69/58/55/62 |
| 9 | 0x0FC | Satan | 99 | Cocytus | 1,934,271 | 68/61/59/55/61 |
| 10 | 0x0C3 | Kaguya Picaro | 80 | Mighty Gaze | 50,400 | 80/80/80/80/80 |
| 11 | 0x0A6 | Vishnu | 90 | Vahana's Wings | 1,549,473 | 61/57/51/62/46 |

Raw bytes, slot 0 (abs `0x64`): `01 10 | 6B 01 | 55 | 00 | 57 00 | 97 A5 15 00 | 57 01 5C 01 69 01 68 01 CC 02 59 03 | 34 37 2F 3F 2D | 00×15`
Skills slot 0: Thermopylae, Debilitate, Concentrate, Charge, Phantom Show, Ali Dance, Drain Phys, Repel Bless (all resolve in Skill ID.txt ✓)

### Oracle (NG++) — Ryuji: 1/12 filled
| k | id | Persona | Lv | Trait | EXP | St/Ma/En/Ag/Lu |
| :-- | :-- | :--- | :-- | :--- | --: | :--- |
| 0 | 0x0F2 | William (equipped) | 99 | Eccentric Temper | 2,183,232 | 73/43/81/54/53 |
| 1..11 | 0x000 | empty (all-zero) | 0 | — | 0 | 0/0/0/0/0 |

### Fresh (6/14) — Joker: 7/12 filled
| k | id | Persona | Lv | Trait | EXP | St/Ma/En/Ag/Lu |
| :-- | :-- | :--- | :-- | :--- | --: | :--- |
| 0 | 0x03C | Shiisaa (equipped, DLC) | 16 | Atomic Bloodline | 14,496 | 11/12/11/11/10 |
| 1 | 0x0C9 | Arsene | 6 | Mighty Gaze | 971 | 3/5/4/11/2 |
| 2 | 0x005 | Jack Frost | 11 | Frigid Bloodline | 4,841 | 8/9/7/9/7 |
| 3 | 0x11D | Matador | 18 | Mighty Gaze | 22,090 | 13/13/10/16/9 |
| 4 | 0x0BE | Messiah Picaro (DLC) | 90 | Hallowed Spirit | 1,452,446 | 56/56/55/55/55 |
| 5 | 0x06A | Regent | 10 | Ultimate Vessel | 3,520 | 10/10/10/10/10 |
| 6 | 0x033 | Shiki-Ouji | 18 | Psychic Bloodline | 19,593 | 16/14/12/9/10 |
| 7..11 | 0x000 | empty | 0 | — | 0 | — |

Fresh Arsene skills = exact starting moveset (Eiha, Mabufu, Maeiha, Mafrei, Mapsi, Cleave, Sukunda, Dream Needle) — strong ground-truth confirmation of the skill field.

### All 10 members, slot 0 (equipped) — oracle vs fresh
Oracle: Joker=Raoul, Ryuji=William, Morgana=Diego, Ann=Celestine, Yusuke=Gorokichi, Makoto=Agnes, Futaba=Lucy, Haru=Al Azif, Akechi=Hereward, Kasumi=Ella (all third-tier ultimates 0xF2..0xFA, Lv99).
Fresh: Captain Kidd, Zorro, Carmen, Goemon, Johanna, Milady(Lv36), Necronomicon(Lv30), Robin Hood(Lv45), Cendrillon(Lv43) — initial personas at the documented story join levels ✓. **Array present for all 10 member slots on both saves.**

## 4. Reconciliation of prior clues

1. **Region `+0x250..+0x2AF` nonzero (oracle) / zero (fresh):** it's the tail of the stock array — slots 10-11 occupy `+0x248..+0x277`, so `+0x250..+0x277` is slot 10's stat/pad + slot 11 (zero in the fresh save because Joker only has 7 personas). `+0x278..+0x2AF` is a separate per-member equipment block (nonzero in both saves; not persona data).
2. **Earlier scatter "persona IDs near +0x6A..+0x88":** misaligned reads, now fully explained:
   - `0xBE @ +0x6A` = REAL (slot 1 id, Messiah Picaro)
   - `0x60 @ +0x6C` = **level byte 96** (false "Jatayu" hit)
   - `0x1A @ +0x72` = **EXP low word** (false "High Pixie")
   - `0x13E @ +0x76`, `0xD6 @ +0x78` = **skill ids** (false "Bugs"/"Hecate")
   - `0x39 @ +0x88` = **Lu stat byte** (0x39) + pad zero (false "Queen Mab")
   - **Pitfall:** persona id space (0x001..0x1C6) overlaps level bytes (1..99), skill ids, stat bytes, and even the byte pair `00 01` (flags + pad) which reads as persona 0x0100 "Norn" — a naive u16 scatter across this block is pure noise. The reliable signature is the full 0x30-strided struct: id@+2 valid + level@+4 ∈ 1..99 + trait@+6 valid + exp@+8 > 0 + stats@+0x1C ≤ 99.
3. **PS4 reference confirmed:** identical 0x30 struct; PC array offset is `+0x38` (not PS4 `+0x4C`).

## 5. Open question — flags bit 0x1000

`0x1000` is set on slots 0..4 and clear on slots 5+ in BOTH saves (oracle: slots 0-4 set; fresh: slots 0-4 set). It is **NOT** the equipped marker (Ryuji's equipped William has flags 0x0001; equipped = slot position). Semantics unverified — candidate meanings (registered/first-five/acquired-via-fusion) all have counterexamples. Editors should preserve it as-is.

## 6. Editor implications

- Read/write stock = read/write 12×0x30 at `member_base + 0x38`.
- Equipped persona = slot 0 (id at `+0x3A` — the offset the editor already uses).
- Empty slot = all 48 bytes zero; removing a persona = zero the slot.
- To "equip" a stock persona, swap it into slot 0 (flags of the old slot 0 keep 0x0001/0x1001 as-is; do not clear bit 0x1000 blindly).
- Skill ids 0x0000 = blank; unknown/out-of-table ids should be treated as blank when writing.

## 7. Probe scripts (kept per instructions)

- `probe_persona_stock.py` — scatter, stride scoring, hex dumps, decode.
- `probe_persona_stock2.py` — all-member slot-0 verification + skill-name sample decode.
