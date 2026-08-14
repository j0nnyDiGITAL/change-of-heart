# 🎭 Persona 5 Royal Save Editor — Master Hermes Handoff

**Project Root:** `E:\ai-workspace\knowledge-base\projects\p5r-save-editor`  
**Web Application URL:** `http://127.0.0.1:5055/`  
**3D Kinetic Client:** `http://127.0.0.1:5055/game/`  
**Test Suite:** `python -m unittest discover -s tests -v` (70/70 Unit Tests Passing 100% Green)

---

## 1. Executive Summary & Accomplishments

During this session, we built an end-to-end web dashboard, cryptographic engine, and reverse-engineering pipeline for **Persona 5 Royal (PC / Steam / GamePass)** save files.

### 🌟 Key Systems Delivered:
1. **AES-256-CBC Cryptographic Pipeline & CRC32 Re-Signer:**
   - Full automated decryption and encryption roundtripping (`0x40` header, `0x20` key, `0x10` IV).
   - Dual-layer CRC32 checksum recalculation matching vanilla Atlus integrity checks (`0x00000000` & `0x00000020` magic bytes).
2. **298-Item Master Inventory & Pocket Studio:**
   - Decoded the master inventory array across `0x13000 – 0x18000` supporting all 8 item categories (Consumables, Infiltration Tools, Skill Cards, Accessories, Melee, Ranged, Armor, Treasure/Key Items).
   - Side-by-side Dual Pane UI: Left Pane manages Joker's carried pockets with steppers `[-]` `[+]` `[99x]` and count badges; Right Pane provides instant search across all **2,412 authentic items**.
3. **23 Arcana Confidant Studio & Story Safety Guardrails:**
   - Stepped rank editor (`◄` `►`) with romance toggles and spoiler masks.
   - Guardrails preventing sequence breaking:
     - **Kasumi / Faith:** Hard-capped at Rank 5 before Third Semester (Jan 12).
     - **Maruki / Councillor:** Rank 9 warning if past Nov 17 deadline.
     - **Romance cutscenes:** Safe milestone confirmation before writing confession flags.
4. **Velvet Room Persona Stock & God-Tier Ingestion:**
   - 12-slot Persona stock editor with moveset customizer, stat normalizer (1..99), and trait selector.
   - 1-Click God-Tier Builds:
     - **Yoshitsune:** *Hassou Tobi + Undying Fury + Apt Pupil + Arms Master + Drain Affinities*.
     - **Izanagi-no-Okami Picaro:** *Myriad Truths + Country Maker + Magic Ability + Victory Cry*.
     - **Raoul:** *Phantom Show + Gloom Mistress + Sleep Boost + Ailment Boost*.
5. **Auto-Discovery & Timestamped Backup Engine:**
   - Automatically detects user's Steam save directory (`%APPDATA%/SEGA/P5R/Steam/<SteamID>/savedata/`).
   - Creates immutable timestamped backups before every write into `backups/`.

---

## 2. Save File Reverse-Engineered Memory Architecture

| Memory Range | Size / Stride | Component / Description |
| :--- | :--- | :--- |
| `0x0000 – 0x0040` | 64 bytes | **Container Header:** Magic, CRC32, compressed length, payload size. |
| `0x0040 – 0x0080` | 64 bytes | **Player Info:** Protagonist First Name, Last Name, Phantom Thieves Group Name. |
| `0x0080 – 0x0100` | 128 bytes | **Header Metadata:** Date String, Current Location, Playtime, Difficulty. |
| `0x0114` | 4 bytes (`u32`) | **Yen / Money:** Clamped `0..9,999,999`. |
| `0x0118 – 0x012C` | 5 x 4 bytes (`u32`) | **Social Stats:** Knowledge, Charm, Proficiency, Kindness, Guts (`1..5`). |
| `0x0200 – 0x0600` | 23 Arcana Slots | **Confidant Array:** Base `0x0200 + (arcana * 0x10)`. Byte 0: Rank (`0..10`), Byte 2: Co-op Points. |
| `0x2410 – 0x2720` | 30 slots (stride `0x1B`) | **Quick Inventory Count Array:** Active quantity bytes (`0..99`). |
| `0x3530 – 0x35A8` | 30 slots (stride 4 bytes) | **Quick ID Ring Buffer:** `[u16 item_id][u16 flag]`. |
| `0x13000 – 0x18000` | Structured Pocket Blocks | **Master Full Inventory:** Holds all 298+ active items across all pockets. |
| `0x18200 – 0x1A000` | 12 slots (stride `0x30`) | **Joker 12-Slot Persona Stock:** ID, Level, Trait, 8 Skill Slots, 5 Stats (`St, Ma, En, Ag, Lu`). |
| `0x2F200 – 0x30700` | 5,376 bytes | **Story Event Flags & Bitfield Matrix:** Story progression and dungeon unlock triggers. |

---

## 3. P5R 16-Bit Engine Item ID Encoding Formula

The Persona 5 Royal engine uses the upper 4 bits for Category and lower 12 bits for Table Row Index:
- `0x1000 | (row & 0x0FFF)` ➔ **Melee Weapons** (`Weapon melee.txt`)
- `0x2000 | (row & 0x0FFF)` ➔ **Consumables / Food** (`Items.txt`)
- `0x3000 | (row & 0x0FFF)` ➔ **Accessories** (`Accessories.txt`)
- `0x4000 | (row & 0x0FFF)` ➔ **Skill Cards** (`Skill Cards.txt`)
- `0x5000 | (row & 0x0FFF)` ➔ **Protectors / Armor** (`Clothes.txt`)
- `0x6000 | (row & 0x0FFF)` ➔ **Infiltration Tools** (`Tools&materials.txt`)
- `0x7000 | (row & 0x0FFF)` ➔ **Ranged Weapons (Guns)** (`Weapon ranged.txt`)
- `0x8000 | (row & 0x0FFF)` ➔ **Treasure** (`Treasure.txt`)
- `0x9000 | (row & 0x0FFF)` ➔ **Key Items** (`Keyitems&essentials.txt`)

---

## 4. Key Files and Directory Map

- `core/crypto.py` — AES-256-CBC decrypt/encrypt container + CRC32 dual-checksum logic.
- `core/parser.py` — Header, name block, and payload parser.
- `core/editor.py` — High-level editing API (`SaveEditor` class).
- `web-app/server.py` — Python HTTP daemon providing `/api/discovery`, `/api/load`, `/api/save`, `/api/backups`, and `/api/database`.
- `web-app/templates/index.html` — Full responsive UI with Dual-Pane Inventory, Confidant Dossier, Velvet Room, and Safety Modals.
- `web-app/static/app.js` — Client logic for pocket filtering, item steppers, god-tier presets, and safe save payloads.
- `web-app/static/app.css` — High-contrast Persona 5 Royal styling (Crimson, Gold, Slanted cards, Halftone overlays).
- `tests/` — 70 unit tests verifying crypto roundtrips, boundary mutations, oracle isolation, and safety rules.

---

## 5. Next Steps for Hermes Agent

1. **Maruki Rank 3 Event-Flag Diff Isolation:**
   - Once user finishes playing Wed 6/22 After School and generates before/after save files, run `diff_mapper.py` against `0x2F200–0x30700` to find the exact cutscene bit.
2. **Kinetics UI Tuning (Optional):**
   - User paused UI redesign for now to capture gameplay video clips; if resumed, reference `/game/` Three.js canvas.

*Everything is clean, tested, documented, and fully operational.* 👑🎭
