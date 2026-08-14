# 🎭 CHANGE OF HEART — Persona 5 Royal Save Studio
*A modern binary save editor & 100% compendium utility for Persona 5 Royal (PC / Steam)*  
*Engineered by **j0nny DiGITAL***

<p align="center">
  <img src="change_of_heart_logo.jpg" alt="CHANGE OF HEART Logo" width="320" style="border-radius:8px; box-shadow:0 0 25px rgba(230,0,18,0.5);">
</p>

[![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20Steam%20%7C%20Steam%20Deck-red?style=for-the-badge&logo=steam)](https://github.com/j0nnyDiGITAL/change-of-heart)
[![Built With](https://img.shields.io/badge/Built%20With-100%25%20Vibecoded%20⚡-ff007f?style=for-the-badge)](https://github.com/j0nnyDiGITAL/change-of-heart)
[![Tests](https://img.shields.io/badge/Tests-79%2F79%20Passing%20(100%25)-brightgreen?style=for-the-badge)](https://github.com/j0nnyDiGITAL/change-of-heart)
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
- **Multi-Save Oracle Diffing:** Hermes Agent established a mathematical lattice across 7 independent save files spanning different dates (Early June $\to$ December $\to$ NG++ February). 
- **The 232-Bit LSB Discovery:** Just before an API connection dropout, Hermes isolated candidate bits at `0x09973`. Antigravity resumed the session, writing `compendium_verify.py` and proving the 5 mathematical proofs:
  1. *Strict Monotonic Growth:* Registrations strictly increased with gameplay ($33 \to 201 \to 217 \to 224$ set bits).
  2. *Party Persona Exclusion:* Party members (*Goemon, Johanna, Milady, etc.*) were naturally absent from the mask because they cannot be registered at the Velvet Room.
  3. *Held $\neq$ Registered:* Stock personas held in inventory but never registered at the Velvet Room did not have their bits set.
  4. *The Synchronized Mirror:* Discovered that the game maintains an authoritative primary mask at `0x09973` and a mirror copy at `0x21E83` (`+0x18510` offset) that must both be synced.

### Phase 3: Desktop Standalone & UI Polish
- Wrapped the entire application in a high-performance, single-executable desktop window via `pywebview` with zero browser port requirements.
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

### 🃏 3. All 23 Confidant Arcanas
* Edit Confidant ranks (`0–10`) and underlying affinity points at `0x136A0`.
* Human-first character dossiers with official Atlus character art and perk milestones.

### ⚔️ 4. Velvet Room & 12-Slot Persona Deck
* Customize Joker's full 12-slot Persona stock: Level (1–99), Core Stats (St, Ma, En, Ag, Lu), Special Traits, and 8 Custom Skill slots.
* **1-Click God-Tier Builds:** Pre-configured tournament-legal movesets for *Yoshitsune (Hassou Tobi)*, *Izanagi-no-Okami Picaro (Myriad Truths)*, *Raoul (Phantom Show)*, *Alice (Die for Me!)*, and *Satanael*.
* Real-time **Elemental Affinity Engine** calculating Phys, Gun, Fire, Ice, Elec, Wind, Psy, Nuke, Bless, Curse resistances based on equipped passive skills.

### 🎒 5. Dual-Pane Master Inventory Studio
* **Carried Pouch (Left Pane):** Decodes all 298 active inventory items in your save across all 8 pockets with instant `[-]`, `[+]`, and `[99x]` steppers.
* **Item Vault (Right Pane):** Live search and 1-click addition from the complete **2,412 authentic item database** (Consumables, Infiltration Tools, Skill Cards, Accessories, Melee Weapons, Guns, Armor, and Treasure/Key Items).

### 🔒 6. Bulletproof Safety & Cryptography
* **100% Native AES-256-CBC Decryption & Encryption** matching Atlus PC standards.
* **Dual-Layer CRC32 Checksum Calculator:** Recalculates both header (`0x00000000`) and data payload (`0x00000020`) checksums on every save.
* **Automated Immutable Backups:** Creates timestamped ZIP snapshots in `savedata/backups/` before writing any changes.
* **Process Conflict Watcher:** Detects if `P5R.exe` is running to prevent Steam Cloud overwrite collisions.

---

## 🚀 Quick Start (Standalone App)

1. Download the latest **`P5R_Save_Editor.exe`** from the [**Releases**](https://github.com/) tab.
2. Double-click to run (no installation or Python required).
3. Select your Steam save slot from the dropdown and click **LOAD SAVE**.
4. Make your edits and click **★ RE-SIGN & SAVE TO DISK**.

---

## 🛠️ Running from Source / Development

```bash
# Clone the repository
git clone https://github.com/j0nnyDiGITAL/p5r-save-editor.git
cd p5r-save-editor

# Install dependencies
pip install -r requirements.txt

# Run the desktop app
python main.py

# Run the automated test suite (79 tests)
python -m unittest discover -s tests -v
```

---

## 🔬 Memory Map & Technical Breakthroughs

| Offset | Size | Component | Description |
|:---|:---|:---|:---|
| `0x0000` | 32 B | **Save Container Header** | Magic `0x31`, Version, Data CRC32 (`0x00`), Header CRC32 (`0x20`) |
| `0x0114` | 4 B | **Yen / Wallet** | Little-endian `uint32` (`¥0 .. ¥9,999,999`) |
| `0x09973` | 29 B | **Compendium Mask (Primary)** | 232-bit LSB-first bitfield (`Bit N` $\to$ Persona ID `N+1` registered) |
| `0x21E83` | 29 B | **Compendium Mask (Mirror)** | Synchronized mirror offset (`+0x18510` from primary) |
| `0x13000` | 1,440 B | **Master Inventory** | 30 slots $\times$ 8 item categories (`[u16 ID][u16 Qty]`) |
| `0x136A0` | 368 B | **Confidant Block** | 23 Arcanas $\times$ 16B stride (`[6 pad][u16 ID][u16 Rank][u16 Points]`) |
| `0x139E0` | 20 B | **Social Stats** | Knowledge, Guts, Proficiency, Kindness, Charm points |
| `0x2F200` | 5,376 B | **Event Flag Matrix** | 43,008-bit game progression, story cutscenes, and dungeon milestones |

---

## ☕ Support the Project

If this tool rescued your 100-hour playthrough or saved you from restarting for 3rd Semester, consider buying me a coffee:

[![Ko-fi](https://img.shields.io/badge/Ko--fi-Support%20on%20Ko--fi-ff5e5b?style=for-the-badge&logo=kofi&logoColor=white)](https://ko-fi.com/j0nnydigital)

---

## 📜 Disclaimer
*Persona 5 Royal* is a registered trademark of ATLUS / SEGA. This tool is a non-commercial, open-source community project and is not affiliated with or endorsed by ATLUS or SEGA. Always keep backups of your save files.
