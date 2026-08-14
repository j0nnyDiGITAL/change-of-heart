# Persona 5 Royal (Steam) Save Format Specification & Project State

**Last Updated:** 2026-08-09 04:45
**Project Path:** `E:\ai-workspace\knowledge-base\projects\p5r-save-editor\`
**Status:** Core engine + GUI + EXE delivered (rebuilt 2026-08-09, item-name tables bundled). **CONFIDANT BLOCK + PARTY BLOCK verified in-game 2026-08-09**, **ITEM ID→NAME BINDING CRACKED via 100% NG++ oracle save** (Buff Joker, gamebanana mod 414406, `C:\Users\kufis\p5r_buff_save\`): ring IDs low-12-bits index into KHSave Royal name tables (data/*.txt, 696 consumables + 256 key items). Verified three ways: Takemi-clinic purchase IDs, endgame ring items, Clear-Data farewell gifts 0x4047-0x4053 → count bytes 0x2784-0x278D byte-for-byte. Remaining: max HP/SP offsets only.

---

## 1. Verified Executable & Delivery Artifacts

- **Desktop Shortcut:** `C:\Users\kufis\Desktop\P5R Save Editor.lnk`
- **Standalone Executable:** `E:\ai-workspace\knowledge-base\projects\p5r-save-editor\P5R_Save_Editor.exe`
- **Batch Launcher:** `E:\ai-workspace\knowledge-base\projects\p5r-save-editor\Launch_P5R_Save_Editor.bat`
- **GUI Entry Point:** `E:\ai-workspace\knowledge-base\projects\p5r-save-editor\gui.py`
- **CLI Entry Point:** `E:\ai-workspace\knowledge-base\projects\p5r-save-editor\cli.py`

---

## 2. In-Game Verified Save Specifications

| Property | Value / Offset | Verification Status |
| :--- | :--- | :--- |
| **Save Magic** | `DATA` (`0x00..0x03`) | Verified |
| **Encryption** | AES-256-CBC (Key: `3lOZS0kYSoOOtkC4c7IDfvNXnxIprUPTlUGVC3yBJF0=`) | **Verified In-Game** |
| **Checksum** | Atlus CRC-32 (Poly: `0x04C11DB7`, Init/Final: `0xFFFFFFFF`) | **Verified In-Game** |
| **Yen / Money** | **Offset `0x35C0`** (`u32` LE) | **VERIFIED IN-GAME** + stable across 2-save diff (¥9,999,999 both) |
| **Quick-info (day/level/playtime/difficulty)** | **Container header text @ `0x93`** — `"{day}({weekday}) {time},{location}\0PLV:{level} K\0PLAY TIME:{h}h {m}m\0DIFFICULTY:{diff}"` | **VERIFIED by 2-save diff** |
| **Daily counter** | `0x3D70` (`u8`, +1/day) | **VERIFIED by 2-save diff** (`0x36`→`0x37`) |
| **Player summary block** | `0x2C` HP (`u32`=256), `0x30` MP (`u32`=136), `0x38` LVL (`u32`=22), `0x3C` money mirror (`u32`=9,999,999) | **VERIFIED vs screenshots** (Lv22 HP256) |

---

## 3. ✅ SOCIAL STATS — FULLY DECODED & VERIFIED (2026-08-08)

**Location: `0x139E0` — 5× `u16` LE POINTS (NOT ranks), order: `[Knowledge, Charm, Proficiency, Guts, Kindness]`**

P5R stores each social stat as an **accumulated point total** (u16 LE), and the displayed rank is derived from per-stat thresholds. **A rank byte does NOT change on every activity** — only when points cross the next threshold. This was the key insight that cracked the format.

### Verified thresholds (Megami Tensei Wiki, P5R section — points required to REACH rank):

| Stat | Rank 2 | Rank 3 | Rank 4 | Rank MAX (5) |
| :--- | :--- | :--- | :--- | :--- |
| Knowledge | 34 | 82 | 126 | 192 |
| Charm | 6 | 52 | 92 | 132 |
| Proficiency | 12 | 34 | 60 | 87 |
| Guts | 11 | 38 | 68 | 113 |
| Kindness | 14 | 47 | 92 | 136 |

Point gains: **1 note = 2 pts, 2 notes = 3 pts, 3 notes = 5 pts** (books can differ).

### Proof (DATA01 → DATA02 diff, matching Jonathan's in-game actions):

| Stat | DATA01 (Mon) | DATA02 (Tue) | Δ | Rank | Screenshot |
| :--- | :--- | :--- | :--- | :--- | :--- |
| Knowledge | 102 | 102 | 0 | 3 | 3 ✓ |
| Charm | 18 | 18 | 0 | 2 | 2 ✓ |
| Proficiency | 34 | **37** | **+3 (craft = 2 notes)** | 3 | 3 ✓ |
| Guts | 39 | 39 | 0 | 3 | 3 ✓ |
| Kindness | 29 | **31** | **+2 (plant = 1 note)** | 2 | 2 ✓ |

The two changed u16 values are EXACTLY the two activities Jonathan performed between saves (workbench craft → +Proficiency, plant feed → +Kindness). No other u16/u8 block in the payload shows this pattern.

### Editor API (updated in `core/editor.py`):
- `get_social_stats()` → `{Name: {points, rank}}`
- `set_social_stats(knowledge=5, charm=5, proficiency=5, kindness=5, guts=5)` → writes the threshold point value for the requested rank (rank 5 = max points).
- Old `PC31_OFFSET_SOCIAL_STATS = 0x437C` and `0x437C` "05 05 05 05 05" theory **RETIRED** (that block is unchanged across saves; not the live stats).

## 4b. ✅ CONFIDANT BLOCK — FULLY DECODED & VERIFIED IN-GAME (2026-08-09)

**Location: `0x136A0` — 23 entries × 16 bytes. Entry layout: `[6 pad][u16 save_id][u16 rank][u16 points][4 pad]`**

- **NOT a flat rank array** — this is why every earlier probe failed (contiguous/strided/64-byte-multiset scans all missed it).
- **Save IDs follow arcana order** (Fool=1 … Judgement=21); Royal additions **Faith=33, Councillor=35**.
- **Verified via rank-ramp probe:** unique ranks 1..10 written to entries 0..9 (entry 10 = untouched control, id=9 rank 1), slot 2 loaded in-game, user read back the confidant menu → every arcana displayed its probe rank, mapping all 11 active IDs. Original ranks re-read perfectly afterward (Fool5 Magician3 Hierophant3 Lovers6 Chariot5 Justice1 Strength1 Death6 Moon3 Faith2 Councillor2) — matches the earlier screenshot ground truth.

### Verified ID map (in-game confirmed)

| save_id | Arcana | probe rank read back |
| :--- | :--- | :--- |
| 1 | Fool | 2 ✓ |
| 2 | Magician | 4 ✓ |
| 6 | Hierophant | 6 ✓ |
| 7 | Lovers | 3 ✓ |
| 8 | Chariot | 1 ✓ |
| 9 | Justice | 1 ✓ (control) |
| 12 | Strength | 9 ✓ |
| 14 | Death | 5 ✓ |
| 19 | Moon | 7 ✓ |
| 33 | Faith | MAX(10) ✓ |
| 35 | Councillor | 8 ✓ |

### Editor API
- `get_confidant_ranks()` / `set_confidant_rank(arcana_id, rank, points=99)` now use the verified block; set writes BOTH rank and points u16s so the game never clamps the displayed rank (confidants carry points, user-confirmed).

---

## 4. Cross-Reference: KingdomSaveEditor (PS4 layout, Xeeynamo)

Source: `KHSave.LibPersona5/Persona5Royal.cs` (fetched 2026-08-08). PS4 Royal = 256 KiB payload (`0x2d000000`), PC = 198,432 B (`0x31`). **Offsets do NOT transfer directly** (money PS4 `0x357C` vs PC `0x35C0`; character array at PS4 `0x48` stride `0x2A8` reads garbage at PC `0x8C`). But structural hints are gold:

- **Character struct**: `+0x14` CurrentHp, `+0x18` CurrentMp, `+0x24` Experience, `+0x4C` Personas[12] stride `0x30`. PC equivalent NOT yet located (stride-0x2A8 probe at 0x18 base gives garbage for slots 2+).
- **Social stat order in Vanilla layout**: `[Knowledge, Charm, Proficiency, Guts, Kindness]` — **confirms our diff-derived order**.
- **InventoryCount**: PS4 `0x2252` count `0x500`; PC probe at `0x2296` = all zeros (wrong offset).
- **Compendium**: PS4 `0x41D8`, Persona stride `0x30` (Flags u16, Id u16, Level u8, Trait, Exp u32, 8 Skills, St/ Ma/En/Ag/Lu).

---

## 4c. ✅ PARTY BLOCK — LOCATED & VERIFIED IN-GAME (2026-08-09)

**Location: `0x2C`, stride `0x2B0` — 10 slots (0=leader, 1..9 members).**

- **HP u16 @+0 · SP u16 @+4** — verified against the in-game Stats screen screenshot (Joker 256/136, Ryuji 246/99, Morgana 208/131, Ann 221/140, Yusuke 234/108).
- **Layout asymmetry:** slot 0 (Joker) is a player struct — LV @+0xC, money mirror @+0x10 (9,999,999). Slots 1+ carry LV @+0x3C with flag 0x1001 @+0x38.
- **Slots 5–9** verified as REAL pre-generated stat blocks: the 6/14 save already carried each future member's join-state block (Makoto Lv21, Futaba Lv36, Haru Lv30, Akechi Lv45, Kasumi Lv43 — their story-arc levels), and the 100% NG++ save reads all 10 slots at Lv99 with per-character distinct HP/SP. **All 10 slots confirmed.**
- **Faith (Kasumi/Sumire) has TWO IDs:** pre-reveal = 33, post-reveal (third semester) = 36. Editor accepts both.
- PS4 reference (Character[10] stride 0x2A8, HP@+0x14) does NOT match PC; PC HP@+0/SP@+4 verified directly.
- Editor `get_party_stats()` labels slots; `set_party_stat()` writes HP/SP/LV at the verified offsets; max_hp/max_sp return `partial` (not yet located).

---

## 5. Item Acquisition List — STRUCTURE DECODED (0x17050)

**Location: `0x17050+`, fixed 16-byte records, newest first. Grew by exactly 2 records between DATA01 and DATA02** (the craft + plant actions). Records are **date-stamped** — this is an acquisition/activity log.

Record layout (16 bytes):

| Offset | Size | Meaning |
| :--- | :--- | :--- |
| +0 | u8 | time slot / type flag (`01`=?, `03`=?) |
| +1 | u8 | month (`06` = June) |
| +2 | u8 | **day of month** (`0E`=14, `0D`=13, `0C`=12…) |
| +3 | u8 | sub-flag (`05`/`04`/`03`…) |
| +4..7 | 4B | zeros |
| +8 | u16 | record sequence id (109, 108, 107… descending) |
| +10 | u16 | `02 00` constant |
| +12 | u16 | `0D 00` constant |
| +14 | u16 | `00 00` |

**Proof:** B's first record `01 06 0E 05` = **June 14** (Tue); second `01 06 0D 05` = **June 13** (Mon) — exactly the two days spanned by the saves. A's first record was `01 06 0C 05` = June 12. IDs `6D`(109) and `6C`(108) are the two new entries; old records shift down.

**Data files note:** `data/Tools&materials.txt` and `data/Keyitems&essentials.txt` use **cheat-engine addresses** (`main+0227156B` = Vanish Ball, `main+022715B8` = Spotlight, `main+022716A4` = Lockpick), NOT save-file item IDs. Save IDs are sequential (108/109 = the two new items); mapping save-ID → item name requires a separate item table (not the CE-address files).

## 5b. PURCHASE DIFF — MONEY RE-VERIFIED + ITEM COUNT BYTES + 0x3530 RING BUFFER (2026-08-08 04:20)

**Diff pair:** `diff/baseline_DATA02.DAT` (pre-purchase, 6/14 Tue Evening 22h47m, Leblanc) vs `DATA01\DATA.DAT` (post-purchase, same day 22h53m, Backstreets). Same day → **clean shopping-only diff** (82 changed bytes total).

### Verified
- **Money `0x35C0` re-verified LIVE**: 9,999,999 → **7,606,999** (spent ¥2,393,000). u32 LE confirmed by an actual transaction, not just save-pair stability.
- **Item count bytes LOCATED** (8 changed bytes in 0x2410–0x2720 region):
  - Four 0 → **0x63 (99)**: `0x2539`, `0x2554`, `0x256F` (stride **0x1B** exactly), `0x2691` — bulk buys (99×4 ≈ ¥2.39M spend; location "Backstreets" = Takemi's clinic / Yongen vending machines → almost certainly SP Adhesives/meds)
  - Four 0 → **1** (new items): `0x25D0`, `0x2605`, `0x26E4`, `0x2715`
  - **NOT a uniform-stride array** (0x2539→0x2554→0x256F is 0x1B but 0x2691 breaks it) → likely ID-indexed sparse counts, not a PS4-style dense table. Mapping count byte → item name still requires an anchor.
- **`0x3530` = 30-slot "recent acquisitions" RING BUFFER** (replaces "secondary ID list — unlabelled" from §6):
  - 4-byte records `[u16 item_id][u16 0x0001]`, **newest at head**, fixed 30 slots (oldest falls off).
  - Shopping trip pushed in **10 new records** at the head; 10 oldest dropped off the end. Exactly the 55-byte run reported in §6.
  - New IDs: `0x20E3, 0x20E0, 0x3024, 0x3161, 0x303F, 0x3009, 0x30A0, 0x31E5, 0x31B4, 0x30D5`. Older (craft/plant era): `0x302C, 0x3064, 0x3067, 0x3065, 0x60B0, 0x60AF, 0x60AE, 0x609C, …` (note consecutive runs like `60B0 60AF 60AE` and `32AC..32A7` — table-adjacent items).
  - ⚠️ **Item-ID space mismatch:** log IDs (0x20xx–0x60xx) do NOT match the CE-address files (`data/*.txt` use `main+0227xxxx`, items 0x1554–0x2553; see §5 note). The log uses a *different* internal numbering. **Next anchor: buy exactly ONE item from a known vending machine, save, diff → one new log record + one count byte → bind ID space.**
- **`0x17050` log did NOT change** on purchase → it is the **activity** log (craft/plant/events), NOT purchases. Purchases go to 0x3530.
- Flags `0x2410`, `0x2413`: 0 → 1 (likely "shopped today" / activity flags).
- Item-table RAM address ranges (from `data/*.txt`): Accessories `0x02271355..02271553`, Items `02271554..02271809`, Keyitems `0227159A..02271A53`, Treasure `02271A54..02271B53`, Skill Cards `02271E54..02271FE4`, Clothes `02272254..02272371`, Ranged `0227245A..02272553`, Compendium `02273240..02275D90`, Melee `02270B55..02270C7B`.

---

## 6. Candidate / Rejected Offsets (2-Save Diff)

| Region | Finding | Verdict |
| :--- | :--- | :--- |
| `0x2556` | `09 03 07 03 05…` identical both saves | **REJECTED** as confidant ranks |
| `0x437C` | `05 05 05 05 05` identical both saves | **REJECTED** as social stats (real block at `0x139E0`) |
| `0x3530` | list grew by 2 (`2C 30 01 00`, `64 30 01 00` prepended) | **DECODED** (see §5b) — 30-slot recent-acquisitions ring buffer |
| `0x17050` | date-stamped acquisition log, grew by 2 | **DECODED** (see §5) |
| `0x3C34–0x3E9C` etc. | flag/counter changes | Kaneshiro-arc event flags; unlabelled |
| Party block | PS4 `0x48` stride `0x2A8` → PC probe garbage | **NOT LOCATED**; player summary at `0x2C–0x44` only |

---

## 8. Remaining Work (updated 2026-08-09)

1. **Persona stock array** (12-slot inventory per member) — hunt in progress (oracle-based, candidate region Joker +0x250).
2. **Baton Pass / Technical ranks / Mementos stamps** — hunt in progress (oracle diff).
3. **Compendium** — PS4 struct known, PC base unknown; per Gemini likely bitfield + sparse overrides, NOT a struct array.
4. **Event-flag pairing for confidant writes** — flag zone located (0x2F200+); mapping specific bits to events is a future enhancement; rank+points writes are the shipped path.
5. Recompile EXE after all offset updates (`pyinstaller P5R_Save_Editor.spec`).

**Diff tooling (reusable):**
```bash
python diff_mapper.py <saveA> <saveB> --out diff/report.md
```


## 7b. EVENT FLAG ZONE — LOCATED (2026-08-09, oracle vs 6/14 diff)

**Location: payload 0x2F200 – 0x30700 (~5,376 B) = set-once event bitfield array.**

- 933 bytes 0->nonzero (flags SET) vs only 29 cleared between the 6/14 save and the 100% oracle — overwhelmingly set-once story/confidant/event state.
- Oracle set-bit density: 4,842 bits vs 1,780 baseline in the same zone.
- Secondary dense zones: 0x017D00–0x018600 and 0x003900–0x003B00.
- IMPORTANT (Gemini oracle review, 2026-08-09): the game's event engine validates state against this flag array; writing confidant ranks/story unlocks WITHOUT their flags can softlock day transitions or cause the game to overwrite written ranks back to flag-consistent values. Rank DISPLAY is independent (probe-proven), but full-rank unlocks (e.g. Councillor 10) ideally pair rank writes with the corresponding flag bitflips.
- Pragmatic editor policy (adopted): rank writes work for display and points; 3rd-semester unlock via confidant ranks is the shipped path; flag-paired writes are a future enhancement (requires mapping specific flag bits to events).


## 4d. ✅ PERSONA STOCK ARRAY — FULLY DECODED & VERIFIED (2026-08-09, subagent + oracle)

**Location: member struct +0x38, stride 0x30, 12 slots. Slot 0 = EQUIPPED (positional, not a flag).**

Per-slot layout (identical to PS4 KHSave persona struct):
| Off | Size | Field |
| :-- | :-- | :-- |
| +0x00 | u16 | flags (0x0001 owned; 0x1000 unverified — preserve) |
| +0x02 | u16 | persona id (Personas.txt) |
| +0x04 | u8 | level 1..99 |
| +0x05 | u8 | unk (always 0) |
| +0x06 | u16 | trait id (Traits.txt) |
| +0x08 | u32 | EXP |
| +0x0C | 8×u16 | skills (Skill ID.txt; 0 = blank) |
| +0x1C | 5×u8 | stats [St,Ma,En,Ag,Lu] |
| +0x21..0x2F | — | zero padding |

- Empty slot = 48 zero bytes. Equip = swap stock slot into slot 0.
- Ground truth: fresh 6/14 Joker stock = Shiisaa(DLC)/Arsene/Jack Frost/Matador/Messiah Picaro(DLC)/Regent/Shiki-Ouji — Arsene skills = exact starting moveset (Eiha, Mabufu, Maeiha...). Oracle Joker = 12/12 (Raoul, Messiah Picaro, Arsene, Izanagi no Okami Picaro, Yoshitsune, Fafnir, Kohryu, Izanagi no Okami, Asterius Picaro, Satan, Kaguya Picaro, Vishnu).
- Flags bit 0x1000 set on slots 0-4 in both saves — semantics unverified; editors preserve it.
- Editor API: get_persona_stock(slot), set_persona_stock_slot(member,k,...), equip_persona(member,k) — all verified.


## 7c. PROGRESSION SYSTEMS — LOCATED, PENDING IN-GAME PROBE (2026-08-09)

Cross-save empirical diff (6 oracle slots + fresh, 2 playthroughs). Full doc: diff/progression_findings.md.

| Block | Offset | Oracle | Mid | Clear | Fresh | Reading |
|---|---|---|---|---|---|---|
| A | 0xA690–0xA780 | 4/3/1 vals | all 1 | 0 | sparse | maxed-progression flag matrix |
| B | 0xB6C0–0xB720 | 04/03 runs | all 1 | 0 | 0 | baton-pass candidate |
| C | 0xC6C0–0xC6EB | 10x04+12x03 | all 1 | 0 | 6x1 | stamps candidate |
| Flowers | 0x17DA8 u16 | — | — | — | — | Subworx-verified ("crashes at FFFF") |

Technical-rank candidates: 0x3D38/0x3D80/0x3EC4/0x4184/0x13B64 (oracle 3/4, mid 1, fresh 0).
Next step REQUIRED (game-as-oracle): write-probe these in a COPY, read back in-game. Block A/B/C + tech candidates all have mirror copies at +0x18510.

## 7d. COMPENDIUM — STATUS: NOT MAPPED (2026-08-09)

Attempted and FAILED: (1) raw 0x30 struct scan (PS4 pattern), (2) bit-per-persona-ID register (0x99D6 candidate, mismatches), (3) bit-per-table-index, (4) sparse-override run (0x6811 = zero padding). AGY dispatch timed out; GitHub code search needs auth.

KEY REFERENCE FINDING: Subworx's P5R editor (subworx.github.io, the leading public save editor) does NOT map the compendium — its feature list covers money/flowers/HP-SP-XP/social stats/item counts only. The compendium is unmapped in ALL public tooling.

Pragmatic status: compendium editing is NOT supported. The editor's Velvet Room surface = equipped persona + 12-slot stock array (verified), which is what fusion/equip actually touches in-save. Compendium registration state remains read-only-by-absence. To crack it: requires either a real reference (CE table with compendium pointers) or a dedicated fingerprint campaign (fresh-save registered-persona set vs oracle — needs the user to report which personas are registered in-game on the 6/14 save).
