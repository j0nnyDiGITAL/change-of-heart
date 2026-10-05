# 🎭 Change of Heart — Frequently Asked Questions (FAQ) & Knowledge Base

Welcome to the **Change of Heart (Persona 5 Royal Save Studio)** FAQ! Whether you are looking for where the save button is located, wondering why an unmet confidant displays 0 stars, or curious how our reverse-engineered inventory engine maps consumable items without corruption, this guide has answers.

---

## 📑 Table of Contents

1. [General & Saving](#-1-general--saving)
   - [Where is the "Save Changes" button?](#where-is-the-save-changes-button)
   - [How do I know my save file was actually modified?](#how-do-i-know-my-save-file-was-actually-modified)
   - [What platforms and versions are supported?](#what-platforms-and-versions-are-supported)
   - [Does this work with Steam Cloud saves?](#does-this-work-with-steam-cloud-saves)
2. [Inventory & Items](#-2-inventory--items)
   - [Why did adding an item give me a completely different item (e.g. Homunculus giving Takemedic)?](#why-did-adding-an-item-give-me-a-completely-different-item-eg-homunculus-giving-takemedic)
   - [Why do I only see some items in my bag?](#why-do-i-only-see-some-items-in-my-bag)
   - [Where are crafting materials like Liquid Mercury, Red Phosphorus, and Aluminum Sheet?](#where-are-crafting-materials-like-liquid-mercury-red-phosphorus-and-aluminum-sheet)
   - [Why are some items labeled RESERVE or missing from the list?](#why-are-some-items-labeled-reserve-or-missing-from-the-list)
3. [Confidants & Social Links](#-3-confidants--social-links)
   - [Why do confidants I haven't met yet show 0 stars instead of "???"?](#why-do-confidants-i-havent-met-yet-show-0-stars-instead-of-)
   - [Can I skip directly to Rank 10? What happens to romance and story cutscenes?](#can-i-skip-directly-to-rank-10-what-happens-to-romance-and-story-cutscenes)
   - [How do I unlock the 3rd Semester (Royal Content)?](#how-do-i-unlock-the-3rd-semester-royal-content)
4. [Compendium & Personas](#-4-compendium--personas)
   - [Why did previous editors get stuck at 96% Compendium? How does Change of Heart reach 100%?](#why-did-previous-editors-get-stuck-at-96-compendium-how-does-change-of-heart-reach-100)
   - [Why does Satanael have an "NG+ ONLY" badge?](#why-does-satanael-have-an-ng-only-badge)
   - [Are God-Tier Builds safe for tournament or story play?](#are-god-tier-builds-safe-for-tournament-or-story-play)
5. [Money, EXP & Stats](#-5-money-exp--stats)
   - [Does maxing out Yen (Money) mess up Joker's EXP or Level?](#does-maxing-out-yen-money-mess-up-jokers-exp-or-level)
   - [How does the Level ↔ EXP auto-sync work?](#how-does-the-level--exp-auto-sync-work)
6. [Backups & Safety](#-6-backups--safety)
   - [Where are save backups stored and how do I roll back?](#where-are-save-backups-stored-and-how-do-i-roll-back)
   - [Can save editing get me banned from Steam?](#can-save-editing-get-me-banned-from-steam)
7. [Troubleshooting](#-7-troubleshooting)
   - [The application window opens but buttons don't click or the screen is blank](#the-application-window-opens-but-buttons-dont-click-or-the-screen-is-blank)
   - [My save file isn't detected in the dropdown menu](#my-save-file-isnt-detected-in-the-dropdown-menu)

---

## 💾 1. General & Saving

### Where is the "Save Changes" button?
The primary save button is located in the **persistent floating bottom deck** anchored at the bottom of the window:
> **`[SAVE CHANGES & RE-SIGN (CRC + AES) ★]`**

Whenever you make changes to items, stats, personas, or confidants, an amber **`● STAGED`** badge will appear in the bottom bar. When you are ready:
1. Click **`SAVE CHANGES & RE-SIGN (CRC + AES) ★`**.
2. A timestamped `.zip` backup of your untouched original save is created automatically in `savedata/backups/` (and automatically downloaded if using a web browser).
3. The editor cryptographically recalculates the dual CRC32 checksums (header `0x00` and payload `0x20`) and writes the updated `.DAT` file straight to your save folder.

### How do I know my save file was actually modified?
- The bottom status message turns bright green: `★ Save successfully re-signed and saved to disk!`.
- The timestamp on your `DATA.DAT` file in your Steam userdata folder updates to the current time.
- The **`● STAGED`** badge disappears.

### What platforms and versions are supported?
- **PC Steam:** Full automatic discovery and seamless 1-click loading and saving.
- **PC Game Pass (Windows Store):** Fully supported via the `📂 BROWSE...` button. Select your `data.dat` / `DATA.BIN` file from `AppData/Local/Packages/.../SystemAppData/wgs/`.
- **Steam Deck:** Fully compatible running under Proton.
- **Nintendo Switch / PlayStation:** Change of Heart natively understands decrypted Persona 5 Royal `DATA.DAT` files. If you extract your decrypted raw save using homebrew tools (e.g. Checkpoint/JKSV on Switch or Apollo Save Tool on PS4), you can edit it directly using the `📂 BROWSE...` button and restore it back to your console.

### Does this work with Steam Cloud saves?
Yes! However, make sure that **Persona 5 Royal (`P5R.exe`) is closed** before saving changes. If the game is actively running when you write to disk, Steam Cloud or the game's in-memory state may overwrite your changes when the game exits or autosaves.

---

## 🎒 2. Inventory & Items

### Why did adding an item give me a completely different item (e.g. Homunculus giving Takemedic)?
* **The Root Cause:** In versions prior to v1.1.2, community item databases used piecewise arithmetic offsets (`0x2530 + idx`, `0x25AA + idx`). However, Persona 5 Royal's internal consumable table (`Items.txt`) contains non-contiguous memory gaps (for example, *Vanish Ball* is missing from line 23, and 4 entries are skipped at line 69). This caused linear index arithmetic to desynchronize over 91% of consumable items, writing *Homunculus* (`0x203F`) to `0x256F` (*Life Ointment*) instead of its authentic engine offset `0x2570`.
* **The Fix (v1.1.2):** We reverse-engineered the **Universal Engine Offset Formula**:
  $$\text{save\_offset} = \text{memory\_address} - 0\text{x}0226\text{F}024$$
  All 338 consumable items now map to their exact, authentic save file byte addresses. Adding 99x *Homunculus* writes strictly to `0x2570`, leaving *Takemedic* (`0x2534`) and all other items completely untouched.

### Why do I only see some items in my bag?
Change of Heart implements an authentic **In-Game Inventory View**:
- Unlike legacy cheat tables that flooded your screen with thousands of `x0` empty lines, the main item view displays **only the items Joker is currently carrying in his bag**, sorted in authentic Atlus effect order.
- To add an item you don't currently have:
  1. Click the **`+ ADD ITEM`** button at the top of the inventory stage.
  2. Search for any item across the full 2,204-item master catalog.
  3. Click `+1x` or `+99x`. The item will immediately appear in your bag!

### Where are crafting materials like Liquid Mercury, Red Phosphorus, and Aluminum Sheet?
Crafting materials are located under the **`🔑 Tools & Mats`** tab!
- Atlus engines store infiltration tools and infiltration crafting components in the exact same table partition (`0x6000`).
- To find crafting materials, navigate to **Hideout & Inventory** → **`🔑 Tools & Mats`**, or search for the material name in the `+ ADD ITEM` catalog.

### Why are some items labeled RESERVE or missing from the list?
Atlus developers left hundreds of unused placeholder entries inside `ITEM.TBL` (named `RESERVE`, `BLANK`, or `リザーブ`). In past versions or lesser editors, adding these items would corrupt your bag or create phantom invisible items that crash the game. Change of Heart automatically filters out all non-functional developer placeholders while strictly preserving legitimate items like *Reserve Ammo* and *Blank Card*.

---

## 🎭 3. Confidants & Social Links

### Why do confidants I haven't met yet show 0 stars instead of "???"?
* In unmodded Persona 5 Royal, confidants you have not yet encountered in the story have unallocated save slots. The in-game menu displays them as hidden or masked with `???`.
* When an editor initializes or modifies a confidant (or sets their rank to 0), the save allocates the 16-byte arcana slot (`0x136A0`). The game engine detects that the slot is registered with 0 rank points and displays the character card with **0 stars**.
* **Recommendation:** If you want a character to remain a natural story surprise with `???`, do not touch their rank slider until you encounter them naturally during the story.

### Can I skip directly to Rank 10? What happens to romance and story cutscenes?
* **Stat & Persona Unlocks:** Setting a confidant to Rank 10 immediately grants their in-game combat and fusion perks (such as party member second awakenings, Kawakami's Special Massage, or Hifumi's party switching).
* **Story Cutscenes & Romance Flags:** *Persona 5 Royal* tracks dialogue progression and romance choices through a permanent 43,000-bit event flag matrix tied to specific in-game calendar dates. 
  - Skipping from Rank 1 directly to Rank 10 will **not** retroactively trigger the Rank 9 romance hangout event.
  - If you want the character marked as in a romantic relationship without seeing the cutscene, use the dedicated **`Romance Route Toggle`** (`0x02` bit) in the editor for Rank 9+ confidants.
  - To watch the genuine cutscenes and hear the voiced dialogue, we recommend leveling confidants naturally or restoring a backup from before that hangout.

### How do I unlock the 3rd Semester (Royal Content)?
To unlock the 3rd Semester (January and February content), you must achieve the following story milestones before the in-game date of **November 17**:
1. **Councillor (Takuto Maruki):** Must reach **Rank 9** (Rank 10 occurs automatically during story events).
2. **Faith (Kasumi Yoshizawa):** Must reach **Rank 5** (ranks 6–10 unlock in January).
3. **Justice (Goro Akechi):** Strongly recommended to reach **Rank 8** (ranks 9 and 10 occur through story events in the Cruiser Palace).

You can safely adjust these ranks in Change of Heart to meet the criteria if you are close to the November deadline!

---

## 📖 4. Compendium & Personas

### Why did previous editors get stuck at 96% Compendium? How does Change of Heart reach 100%?
* Legacy tools only modified the 29-byte bitmask at `0x09973`. However, the in-game Velvet Room menu calculates the `Completed %` by counting **Velvet Room Persona records** (232 entries), not the bitmask!
* When other tools did not populate the Velvet Room records for party Personas and special fusions, the game registered only ~223 records, resulting in the infamous **"stuck at 96%"** bug.
* Change of Heart writes both the primary mask (`0x09973`), the synchronized mirror (`0x21E83`), and all **232 Velvet Room records**, matching a genuine 100% New Game Plus save down to the exact byte.

### Why does Satanael have an "NG+ ONLY" badge?
Satanael is hardcoded by Atlus as a New Game Plus exclusive ultimate fusion. In a fresh first-playthrough save, forcing Satanael into your compendium or active party can cause Velvet Room registration glitches. Change of Heart clearly marks Satanael so you can make informed decisions.

### Are God-Tier Builds safe for tournament or story play?
Yes! All presets in the **GOD-TIER BUILDS** tab (*Yoshitsune Hassou Tobi*, *Izanagi-no-Okami Picaro*, *Raoul*, *Alice*, and *Satanael*) use genuine Atlus skill IDs, legal passive combinations, and authentic trait IDs. They will not crash your game or corrupt battle calculations.

---

## 💰 5. Money, EXP & Stats

### Does maxing out Yen (Money) mess up Joker's EXP or Level?
**No.** In early community cheat tables, Joker's EXP (`0x3C`) was accidentally confused with a secondary money mirror offset. In Change of Heart:
- Yen is written strictly to its authentic little-endian `uint32` location at `0x35C0`.
- Joker's EXP is isolated at `0x3C` and party members at `+0x70` increments.
- Modifying your wallet to ¥9,999,999 will never affect your party's level, stats, or EXP.

### How does the Level ↔ EXP auto-sync work?
Persona 5 Royal calculates the EXP required for each level using a cubic mathematical curve:
$$\text{EXP}(\text{Level}) = a \cdot \text{Level}^3 + b \cdot \text{Level}^2 + c \cdot \text{Level} + d$$
If you change a character's numerical level without updating their accumulated EXP, the game can stall after battles or award 0 EXP. Change of Heart automatically calculates and synchronizes the exact cubic EXP whenever you modify any party member's level.

---

## 🛡️ 6. Backups & Safety

### Where are save backups stored and how do I roll back?
Every time you click **`SAVE CHANGES & RE-SIGN`**, Change of Heart creates an immutable ZIP archive in:
```text
savedata/backups/DATA<Slot>_<Timestamp>.zip
```
To roll back:
1. Navigate to the **`BACKUPS & SAFETY`** tab in the sidebar.
2. Select your desired timestamped snapshot from the **REVERSIBLE RESTORE VAULT** dropdown.
3. Click **`RESTORE SELECTED STATE`**. Your save is instantly reverted!

### Can save editing get me banned from Steam?
**No.** Persona 5 Royal is a purely single-player, client-side offline game. While it features an optional "Thieves Guild" network feature (which aggregates daily player choices and fusion stats), Steam VAC (Valve Anti-Cheat) is not enabled on Persona 5 Royal. Save editing will not trigger bans or account strikes.

---

## 🔧 7. Troubleshooting

### The application window opens but buttons don't click or the screen is blank
This occurs when the Windows **Microsoft Edge WebView2 Runtime** crashes or fails to initialize:
1. **Automated Browser Fallback:** Change of Heart includes an automated UI-liveness watchdog. If the native desktop window does not check in within 30 seconds, the editor will automatically launch in your default web browser (Chrome, Edge, Firefox, Brave) and continue working seamlessly.
2. **Permanent Fix:** Open Windows Settings → Apps → Installed Apps → Search for **Microsoft Edge WebView2 Runtime** → Click **Modify** → Select **Repair**. Then relaunch the editor.

### My save file isn't detected in the dropdown menu
1. Make sure you have launched Persona 5 Royal at least once on your PC and created a manual save in Leblanc or a safe room (autosaves alone may not populate all slots).
2. Click the **`REFRESH`** button next to the save selector.
3. If you installed Steam on a non-standard drive or are using PC Game Pass, click the **`📂 BROWSE...`** button and select your `DATA.DAT` or `data.dat` file directly from your disk!

---

*Engineered with 💖 by **j0nny DiGITAL** and powered by **TypeSafe AI**.*
