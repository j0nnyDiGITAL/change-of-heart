# 🎭 CHANGE OF HEART — Persona 5 Royal Save Studio
*A modern binary save editor & 100% compendium utility for Persona 5 Royal (PC / Steam)*  
*Engineered by **j0nny DiGITAL***

<p align="center">
  <img src="change_of_heart_logo.jpg" alt="CHANGE OF HEART Logo" width="320" style="border-radius:8px; box-shadow:0 0 25px rgba(230,0,18,0.5);">
</p>

[![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20Steam%20%7C%20Steam%20Deck-red?style=for-the-badge&logo=steam)](https://github.com/j0nnyDiGITAL/change-of-heart)
[![Built With](https://img.shields.io/badge/Built%20With-100%25%20Vibecoded%20⚡-ff007f?style=for-the-badge)](https://github.com/j0nnyDiGITAL/change-of-heart)
[![Tests](https://img.shields.io/badge/Tests-182%2F182%20Passing%20(100%25)-brightgreen?style=for-the-badge)](https://github.com/j0nnyDiGITAL/change-of-heart)
[![License](https://img.shields.io/badge/License-MIT-blue?style=for-the-badge)](LICENSE)
[![Ko-fi](https://img.shields.io/badge/Ko--fi-Support%20j0nny%20DiGITAL-ff5e5b?style=for-the-badge&logo=kofi&logoColor=white)](https://ko-fi.com/j0nnydigital)

**CHANGE OF HEART** is a modern, standalone save editor and binary reverse-engineering studio for **Persona 5 Royal (PC / Steam)**. Built with a full **Phantom Thieves** visual interface, automatic Steam save detection, mathematical bitfield manipulation, and dual-layer CRC32 cryptographic re-signing.

> [!NOTE]
> ⚡ **100% Pure Vibecoded**: This entire application — from the AES-256 binary cryptography and multi-save oracle diffing to the standalone desktop UI and test suite — was built and reverse-engineered collaboratively via AI-driven pair programming sessions between **j0nnyDiGITAL**, **Hermes Agent**, and **Antigravity**.

---

## 📜 The Origin Story & Reverse-Engineering Journey

For years, the PC Steam version of *Persona 5 Royal* lacked a complete, open-source save editor. While basic cheat tables existed for live memory in Cheat Engine, the encrypted binary `.DAT` save format on PC had several unmapped "black box" regions that caused previous community tools to corrupt saves or fail silently.

This project was built across intensive collaborative AI-assisted reverse-engineering sessions:

### Phase 1: Cryptographic Pipeline & Core Memory Mapping (Hermes Agent)
- **Container Decryption & CRC Integrity:** Reverse-engineered Atlus's custom container wrapping, implementing textbook AES-256-CBC decryption alongside dual-layer CRC32 checksum calculation for both the header (`0x00000000`) and data payload (`0x00000020`).
- **Confidant & Social Structs:** Mapped the 16-byte fixed stride at `0x136A0` (`[6 pad][u16 ID][u16 Rank][u16 Points][4 pad]`), uncovering the story-gating point thresholds and romance bitfields.
- **The Dual-Pane Inventory Engine:** Decoded the 298-item master inventory table at `0x13000` spanning all 8 item categories (Melee, Guns, Armor, Accessories, Consumables, Tools, Skill Cards, and Treasure).

### Phase 2: The Compendium Breakthrough (Hermes & Antigravity)
- **The "Unsolvable" Compendium Blob:** Previous modding guides assumed the compendium was stored at `0x20000` (legacy PS4 format) or that it tracked owned stock.
- **Multi-Save Oracle Diffing:** Hermes Agent established a mathematical lattice across 7 independent save files spanning different dates (Early June → December → NG++ February). 
- **The 232-Bit LSB Discovery:** Just before an API connection dropout, Hermes isolated candidate bits at `0x09973`. Antigravity resumed the session, writing `compendium_verify.py` and proving the 5 mathematical proofs:
  1. *Strict Monotonic Growth:* Registrations strictly increased with gameplay ($33 \to 201 \to 217 \to 224$ set bits).
  2. *Party Persona Exclusion:* Party members (*Goemon, Johanna, Milady, etc.*) were naturally absent from the mask because they cannot be registered at the Velvet Room.
  3. *Held $\neq$ Registered:* Stock personas held in inventory but never registered at the Velvet Room did not have their bits set.
  4. *The Synchronized Mirror:* Discovered that the game maintains an authoritative primary mask at `0x09973` and a mirror copy at `0x21E83` (`+0x18510` offset) that must both be synced.

### Phase 3: Desktop Standalone & UI Polish
- Wrapped the entire application in a high-performance, single-executable desktop window (native PyWebView / Edge WebView2 engine hosting a stdlib HTTP backend).
- Integrated official 232-Persona high-res character artwork, instant search filters, and 1-click rescue guardrails.

---

## ✨ Features

### 📖 1. Granular Persona Compendium & 1-Click 100% Unlock
* **Reverse-Engineered Compendium Bitfield:** Full decoding of the 232-persona registration bitmask at `0x09973` and its synchronized mirror at `0x21E83`.
* **Granular Matrix Control:** Search and toggle individual Personas (registered vs locked) with live character portraits.
* **1-Click Smart Batch Unlocks:** 
  * `⚡ Unlock All (100%)`
  * `🎭 Unlock DLC Only` (*Orpheus, Izanagi, Kaguya, Raoul, etc.*)
  * `💎 Unlock Treasure Demons Only` (*Regent, Orlov, Crystal Skull, etc.*)

### 🛡️ 2. "3rd Semester Rescue" & Story Guardrails
* **1-Click 3rd Semester Unlock:** Missed the November 17 deadline? One click safely sets Maruki (Rank 9), Kasumi (Rank 5), and Akechi (Rank 8) to qualify for the Royal 3rd Semester without breaking story logic.
* **Sequence-Breaking Protection:** Built-in validation prevents setting Kasumi past Rank 5 before January or Maruki after his departure deadline.
* Customize Joker's full 12-slot Persona stock: Level (1–99), Core Stats (St, Ma, En, Ag, Lu), Special Traits, and 8 Custom Skill slots.
* **1-Click God-Tier Builds:** Pre-configured tournament-legal movesets for *Yoshitsune (Hassou Tobi)*, *Izanagi-no-Okami Picaro (Myriad Truths)*, *Raoul (Phantom Show)*, *Alice (Die for Me!)*, and *Satanael*.
* Real-time **Elemental Affinity Engine** calculating Phys, Gun, Fire, Ice, Elec, Wind, Psy, Nuke, Bless, Curse resistances based on equipped passive skills.

### 🎒 5. Persona 5 Royal Item Studio
* **In-Game Inventory View:** The left pane shows **only the items you actually carry** in your current save — matching P5R's own bag screen 1:1, sorted in authentic in-game effect priority (HP recovery → SP recovery → Status → Battle items).
* **+ ADD ITEM Catalog Modal:** A dedicated searchable drawer browses the full 2,204-item master catalog (Consumables, Infiltration Tools, Skill Cards, Melee, Guns, Armor, Accessories, Treasure, Key Items) with `+1x` and `+99x` add buttons and real-time `IN BAG` ownership badges.
* **9-Category Tab Bar** with live pocket counts: `🧪 Items`, `🔑 Tools`, `🎴 Cards`, `🗡️ Melee`, `🔫 Guns`, `🛡️ Armor`, `💍 Accs`, `💎 Loot`, `📜 Key`.
* **Inline Quantity Steppers:** `[-]`, `[+]`, `[99x]`, and red `[✕]` discard on every row.
* **Live Item Dossier (Right Pane):** In-game effect text, hex ID, bag quantity counter (`[-10] [-1] [+1] [+10]`), `SET TO 99x (MAX)`, and `DISCARD (REMOVE)`.
* **1-Click Batch Presets:** Max Current Tab, 99x Leblanc Curry & Coffee, Infiltration Kit, Clinic Meds, Reset Bag.

### 🔒 6. Bulletproof Safety & Cryptography
* **100% Native AES-256-CBC Decryption & Encryption** matching Atlus PC standards.
* **Dual-Layer CRC32 Checksum Calculator:** Recalculates both header (`0x00000000`) and data payload (`0x00000020`) checksums on every save.
* **Automated Immutable Backups:** Creates timestamped ZIP snapshots in `savedata/backups/` before writing any changes.
* **Process Conflict Watcher:** Detects if `P5R.exe` is running to prevent Steam Cloud overwrite collisions.

---

## 🚀 Quick Start (Standalone App)

1. Download the latest **`P5R_Save_Editor.exe`** from the [**Releases**](https://github.com/j0nnyDiGITAL/change-of-heart/releases/latest) tab.
2. Double-click to run — it opens a self-contained native window (PyWebView / Edge WebView2 engine) hosting the local studio. Fully self-contained: no Python install required. The bundled backend serves on `127.0.0.1:3000`.
3. Select your Steam save slot from the dropdown and click **LOAD SAVE**.
4. Make your edits and click **★ RE-SIGN & SAVE TO DISK**.

## 📥 Download Standalone Executable

No Python or terminal required! Just grab the latest standalone release:  
👉 **[Download CHANGE_OF_HEART_v1.1.0.zip (Latest Release)](https://github.com/j0nnyDiGITAL/change-of-heart/releases/latest)**

1. Download and extract `CHANGE_OF_HEART_v1.1.0.zip`.
2. Double-click `P5R_Save_Editor.exe`.
3. The editor will automatically detect your Steam saves and open the studio window.

---

## 📋 Changelog

### v1.1.2 — Save Backup ZIP Fix, Reddit Community Fixes & In-Memory Caching
- **🛡️ In-Memory Backup ZIP Creation:** Resolved bug report where saving custom or uploaded save files (`BROWSE...`) failed to create a `.zip` backup archive. The backend now creates an in-memory timestamped `.zip` containing the original baseline save and downloads it automatically to the user's browser alongside the re-signed save.
- **🧹 Atlus Dummy/RESERVE Item Filtering:** Filtered unused table placeholders (`RESERVE`, `BLANK`, `リザーブ`, etc.) from inventory lists and write endpoints while preserving authentic items like `Reserve Ammo` and `Blank Card`.
- **⚡ Category Table Caching (~4ms read):** Added in-memory class caching for master data tables, eliminating per-item disk hits and beating the 100ms virtual scroll SLA.
- **🏷️ Tools & Materials UI Clarity:** Renamed Infiltration tab to "Tools & Mats" with rich in-game descriptions for crafting components (Liquid Mercury, Red Phosphorus, Aluminum Sheet, etc.).
- **🎭 Satanael NG+ Badge & Confidant Safety Warning:** Added clear NG+ badge for Satanael in compendium and cutscene skip advisory for Rank 9 romance flags.
- **🧪 182/182 Unit Tests Passing:** Complete automated test suite coverage with zero regressions.
- **🌿 Redesign Feature Branch:** Full-bleed P5R menu overhaul safely branched to `redesign/p5r-native-menu` for ongoing development.

### v1.1.1 — UI-Liveness Watchdog & Bond Points Preservation
- **🩺 Automated UI Watchdog:** Pings `/api/ui-heartbeat`; if Edge WebView2 fails to check in within 30s, falls back cleanly to the system browser.
- **🛡️ CSRF Hardening:** The local API now validates browser `Origin` headers (loopback only); foreign origins get `403`.
- **🔒 Bond-Points Surplus Preservation:** Rank updates preserve accrued bond point surplus across all confidants.

### v1.1.0 — Party Evolutions, Romance Toggle & Save Discovery Hotfix
- **⚡ Persona Evolution Tiers (1–3)** selector for all party members (Base/Awakened/Royal forms).
- **💖 Romance / Friendship route toggle** for Rank 9+ confidants on PC saves (`0x136A0` bit `0x02`).
- **🔄 Level ↔ EXP auto-sync** using the authentic Atlus cubic curve — prevents post-battle EXP stalls after level edits.
- **🔧 Fixed Haru (Slot 6) / Futaba (Slot 7) party swap.**
- **📂 Multi-location save auto-discovery** (Steam Userdata / LocalAppData / GamePass paths) + manual `📂 BROWSE...` file picker.
- **🔑 Key Items unlockable** via the Cheat Shop catalog (confirm-gated).
- **🖥️ WebView2 bundling hotfix:** EXE rebuilt on Python 3.14.6 + PyInstaller 6.22.0 embedding the full `pywebview` runtime — fixes browser-fallback regression.

### v1.0.10 — Compendium 100% Unlock Fix (Genuine-Save Parity)
> *"Why does it say 96%?"* — fixed, and proven in-game.

- **🐛 The 96% Compendium Bug — Root-Caused & Fixed:** Unlock ALL previously staged a *filtered* persona list; on save, unlisted personas (party Personas, Satanael variants, etc.) had their registration bits **actively cleared** and their Velvet Room records never written. The game's `Completed %` counts Velvet Room **records** (~232 denominator), not the mask — so partial records = 96%.
- **✅ Genuine-Save Parity:** Unlock ALL now triggers the verified backend full unlock: all **224 live registration bits** (party & Satanael bits included — genuine 100% saves set them too) plus all **232 Velvet Room records**, byte-equivalent to a real 100% NG+ save.
- **🧪 157/157 Unit Tests** including 4 new wiring regression tests (`TestCompendiumUnlockAllWiring`).
- **🎮 Verified In-Game** on two independent saves (one surgically repaired, one via the new Unlock ALL flow): both show **Completed 100%**, no greyed Satanael ghost.

### v1.0.9 — In-Game Parity, Master Inventory Overhaul & Full Compendium
- **🗃️ 10-Category Master Inventory:** unique equipment tracked by ownership flags (Melee `0x1B30`, Ranged `0x3430` — all 106 guns mapped, Outfits `0x3230` — all 286 costumes), stackables by count arrays (Armor/Accessories/Consumables/Skill Cards/Tools/Treasure), zero phantom items, engine mirror sync.
- **🖋️ Full-Spectrum Name Editor:** dual UTF-8 + Atlus font-glyph encoding across 8 primary/mirror blocks — names stick in dialogue, status screens, and calling cards.
- **🃏 Clean 100% Compendium:** Satanael ghost bug fixed (`0xD3` mask-only); authentic 232-record structure.
- **🛡️ Guarded Key Items** + dynamic asset packaging. See `docs/RELEASE_NOTES_v1.0.9.md`.

### v1.0.8 — In-Game Parity Fixes: Names, Master Items & Compendium
- **🔤 Names** serialize into the in-game dialogue payload (`0x13840` family + mirrors), not just the header preview.
- **🎒 Item quantities** write to the authoritative master count array (`0x2410..0x2800` sub-bases) — no more 30-slot cap silently dropping items.
- **📖 Compendium math** corrected to the true 224-registerable denominator. See `patch_notes_v1.0.8.md`.

### v1.0.7 — Item Studio Rework: In-Game Inventory Behavior
> *"How would a real human want to use this?"*

- **🎒 In-Game Inventory View (Breaking Change):** The item list now shows **only items you actually carry**, matching P5R's real bag screen behavior. No more cluttered `✕ 0` entries for every unowned item in the database.
- **➕ Add Item Modal:** Click the new `+ ADD ITEM` button to open a searchable catalog of all 2,204 game items filtered to the active category, with `+1x` and `+99x` add buttons and live `IN BAG (✕N)` ownership badges.
- **🗑️ Discard Button:** A red `[✕]` discard button on every row and a `DISCARD (REMOVE)` button in the dossier instantly removes items from the bag (sets quantity to 0 and removes the slot).
- **🎯 Empty Pocket UX:** When a category pocket is empty, the list shows a contextual `+ ADD [CATEGORY] ITEM` shortcut button pointing directly to the catalog modal.
- **🔧 Sort Fix:** Restored missing `P5R_ITEM_SORT_PRIORITY` and `getItemSortRank()` functions that had been accidentally deleted, causing a `ReferenceError` that rendered all item pockets blank.

### v1.0.6 — Standalone Launcher & Audit Hardening
- **🖥️ Audit Hardening & Build Presets:** Compendium safe-unlock, teammate story-locks, and god-tier build ID fixes. The app runs as a native PyWebView (Edge WebView2) window over a bundled stdlib HTTP backend on `127.0.0.1:3000`.
- **⚡ God-Tier Build Presets Fixed:** All persona/skill/trait IDs re-verified against the real `data/` tables (Yoshitsune 365→87, Raoul 333→363, Izanagi-no-Okami Picaro 305→366).
- **📖 Compendium Safe Unlock (224/232):** Unlock-all now registers only the 224 bits the game can legitimately set. 8 dead IDs excluded (Metatron, Anat, Prometheus + 5 P5-legacy duplicates).
- **🛡️ Dummy Skill Rejection:** BLANK/placeholder skill IDs (0x0000–0x0009 + named placeholders) filtered from web dropdowns and rejected in persona writes.
- **🚫 Legacy Persona Filter:** Cut-content entries removed from the persona picker.
- **🔒 Teammate Persona Story-Lock:** Backend + UI refuse changing a teammate's persona identity.
- **⚙️ Teammate LV u8 Fix:** Level written/read as a single byte at +0x3C.
- **🧪 94/94 Unit Tests Passing.**

### v1.0.5 — Joker Level / EXP Collision Fix
- **⚡ Joker MC Level / EXP Collision Fix:** Eliminated the legacy `0x3C` money-mirror write. Yen is now written strictly to `0x35C0`.
- **🧪 80/80 Unit Tests Passing.**

### v1.0.4 — Confidant Slot Zeroing
- **🧹 Active Confidant Slot Zeroing:** Setting a Confidant to Rank 0 now completely zeroes all 16 bytes of the slot.

### v1.0.3 — Spoiler Prevention
- **🔒 Spoiler Prevention / Un-Met Confidants:** Un-met confidants remaining at Rank 0 are no longer allocated save slots.
- **⚡ Save Re-signing Stability:** Hardened payload deserialization across all party members, skills, and stock slots.

### v1.0.2
- **💾 Persona Flags Argument Fix:** Fixed an argument mismatch in `set_equipped_persona()` during `/api/save` re-signing.

### v1.0.1
- **⚡ Socket Readiness Polling:** Added active socket polling in `main.py` to eliminate `127.0.0.1` connection refused race conditions.

---

## 🛠️ Running from Source / Development

```bash
# Clone the repository
git clone https://github.com/j0nnyDiGITAL/change-of-heart.git
cd change-of-heart

# Install dependencies
pip install -r requirements.txt

# Run the desktop app
python main.py

# Run the automated test suite
python -m unittest discover -s tests -v
```

### 🩺 Troubleshooting: app window opens but nothing works
If the editor launches but buttons are dead / saves aren't detected, your **Microsoft Edge WebView2 Runtime** is likely broken (it auto-updates independently of the app and can silently fail after an update):
1. The app now detects this automatically — after ~30 seconds it reopens itself in your default web browser.
2. To fix the native window: Windows Settings → Apps → **Microsoft Edge WebView2 Runtime** → **Modify → Repair**, then relaunch the editor.

---

## 🔬 Memory Map & Technical Breakthroughs

| Offset | Size | Component | Description |
|:---|:---|:---|:---|
| `0x0000` | 32 B | **Save Container Header** | Magic `0x31`, Version, Data CRC32 (`0x00`), Header CRC32 (`0x20`) |
| `0x35C0` | 4 B | **Yen / Wallet** | Little-endian `uint32` (`¥0 .. ¥9,999,999`); `0x3C` (Joker EXP) must NOT be written (v1.0.5 fix) |
| `0x09973` | 29 B | **Compendium Mask (Primary)** | 232-bit LSB-first bitfield (`Bit N` → Persona ID `N+1` registered) |
| `0x21E83` | 29 B | **Compendium Mask (Mirror)** | Synchronized mirror offset (`+0x18510` from primary) |
| `0x13000` | 1,440 B | **Master Inventory** | 30 slots × 8 item categories (`[u16 ID][u16 Qty]`) |
| `0x136A0` | 368 B | **Confidant Block** | 23 Arcanas × 16B stride (`[6 pad][u16 ID][u16 Rank][u16 Points]`) |
| `0x139E0` | 20 B | **Social Stats** | Knowledge, Guts, Proficiency, Kindness, Charm points |
| `0x2F200` | 5,376 B | **Event Flag Matrix** | 43,008-bit game progression, story cutscenes, and dungeon milestones |

---

## ☕ Support the Project

If this tool rescued your 100-hour playthrough or saved you from restarting for 3rd Semester, consider buying me a coffee:

[![Ko-fi](https://img.shields.io/badge/Ko--fi-Support%20on%20Ko--fi-ff5e5b?style=for-the-badge&logo=kofi&logoColor=white)](https://ko-fi.com/j0nnydigital)

---

## 📜 Important Limitations & Disclaimer

### ⚠️ Confidant Ranks & Romance Notes:
- **Story Cutscenes & Calendar Timeline:** Modifying a Confidant's numerical rank modifies the rank stars and stat benefits in your menu. However, *Persona 5 Royal* tracks dialogue progression and romance choices via a permanent 43,000-bit narrative event matrix tied to specific calendar days.
- **Rolling Back Ranks:** Lowering a Confidant's rank (e.g. from Rank 9 to Rank 8) will **not** replay already-completed story cutscenes if the in-game calendar has moved past that day. To redo branching dialogue choices (such as romance flags), always restore a save or automatic backup from before that hangout took place.

### ⚖️ Trademark Disclaimer:
*Persona 5 Royal* is a registered trademark of ATLUS / SEGA. This tool is a non-commercial, open-source community project and is not affiliated with or endorsed by ATLUS or SEGA. Always keep backups of your save files.
