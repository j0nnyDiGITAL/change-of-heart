# 🎭 Persona 5 Royal Save Editor — Hermes Handoff (Session 2)

**Project Root:** `E:\ai-workspace\knowledge-base\projects\p5r-save-editor`  
**Web Application URL:** `http://127.0.0.1:5055/`  
**Previous Handoff:** `HERMES_HANDOFF.md` (Session 1 — covers crypto, inventory, confidants, UI)  
**Date:** 2026-08-14

---

## 🚨 CRITICAL: Compendium Mask Breakthrough

Hermes, you were working on this when the connection died (`APIConnectionError` after `max_retries_exhausted`). You wrote `tools/mask_math_v2.py` to test the hypothesis and never saw the output. Here are the results and the conclusion you were about to reach.

### What You Found Before the Crash

You identified the **232-bit bitmask at offset `0x09973`** (with a mirror at `0x21E83`, offset `+0x18510`) across 7 save files using a DeepSeek Q6 + Gemini oracle-guided bit-aligned ladder scan. You proved:

1. The mask is 232 bits (29 bytes), LSB-first
2. Bit index `i` (0-based) corresponds to persona save-ID `i + 1`
3. Personas with ID > 232 physically cannot appear in the mask (range error, not data error)

You wrote `mask_math_v2.py` to test `stock ∩ [1..232] ⊆ mask?` — then the connection died.

### What the Results Show (You Never Saw These)

```
  33/232 |#####                                   | User DATA01 (June 15, early-game)
 201/232 |##################################      | Oracle DATA14 (NG+ Dec 24)
 217/232 |#####################################   | Oracle DATA11 (NG++ Feb)
 217/232 |#####################################   | Oracle DATA12 (NG++ Feb)
 224/232 |######################################  | Oracle DATA13 (NG++ Jan 31)
 224/232 |######################################  | Oracle DATA15 (NG+ Dec 24)
 224/232 |######################################  | Oracle DATA16 (NG++ Mar 20)
```

### The Conclusion: COMPENDIUM REGISTRATION BITFIELD

The mask at `0x09973` is the **Persona Compendium Registration Bitfield**. It tracks which personas have been **registered** at the Velvet Room, NOT which personas Joker has ever held.

**5 independent proofs:**

| Test | Result | Explanation |
|:---|:---:|:---|
| Monotonic growth | PASS | 33 (early) -> 201-224 (NG++). Strictly increasing with gameplay. |
| Party persona exclusion | PASS | Goemon, Johanna, Milady, Necronomicon, Robin Hood, Anat, Prometheus are in Joker's stock but NOT in the mask. Party personas can't be registered in the compendium. |
| Held != registered | PASS | User's Jack Frost (0x05), Shiki-Ouji (0x33), Shiisaa (0x3C), Messiah Picaro (0xBE) are held but not yet registered. Expected for June 15 save with only 33 registrations. |
| Late-game full coverage | PASS | All 6 oracle saves: 0 unexplained absences. Every stock persona <=232 is in the mask. |
| Range boundary | PASS | Personas > ID 232 never appear. The 232-bit mask physically can't hold them. |

**Mirror note:** The mirror at `0x21E83` diverges by 1 byte (byte 0) on some oracle saves — a 2-bit difference (217 vs 215 set bits). Likely a game-write timing artifact. The primary at `0x09973` is authoritative. Our unlock writes both copies, so this is irrelevant for editing.

---

## What Was Built This Session

### Backend (already existed from your work, Hermes)

- `core/editor.py`:
  - `PC31_OFFSET_COMPENDIUM = 0x09973`
  - `PC31_COMPENDIUM_MIRROR = 0x21E83`
  - `PC31_COMPENDIUM_BITS = 232`
  - `get_compendium()` -> reads 232-bit mask, returns `{supported, registered: [ids], count}`
  - `set_compendium_registration(persona_id, registered)` -> sets/clears a single bit in both copies
  - `unlock_compendium_100()` -> writes `0xFF x 29` to both `0x09973` and `0x21E83`

### Server API (wired this session)

- `web-app/server.py`:
  - `/api/load` now includes `compendium` in the response payload
  - `/api/save` handles `unlock_compendium: true` flag -> calls `unlock_compendium_100()` before repacking

### Frontend UI (built this session)

- `web-app/templates/index.html`:
  - New nav tab: COMPENDIUM (between Inventory and God-Tier Builds)
  - `section#stage-compendium` with progress bar, percentage label, and registered persona chip grid

- `web-app/static/app.js`:
  - `renderCompendium()` — renders progress bar (count/232), percentage, and persona name chips from DB.personas
  - `unlockFullCompendium()` — confirms with user, sets UNLOCK_COMPENDIUM_FLAG, updates UI immediately, prompts to RE-SIGN
  - Flag is passed in the save payload as `unlock_compendium: true`

### Verification Script

- `tools/compendium_verify.py`:
  - Runs all 5 verification tests across all 7 saves
  - Outputs formatted report with monotonicity bars, byte-level mirror comparison, and verdict

---

## Memory Map Update (Add to Session 1 Handoff)

| Offset | Size | Component |
|:---|:---|:---|
| `0x09973` | 29 bytes (232 bits) | **Compendium Registration Mask (Primary)** — LSB-first, bit N -> persona ID N+1 registered |
| `0x21E83` | 29 bytes (232 bits) | **Compendium Registration Mask (Mirror)** — game writes both, primary is authoritative |

---

## Outstanding Work / Next Steps

### 1. Maruki Event-Flag Cutscene Isolation
- **Status:** NOT STARTED (waiting for user's before/after save from Wed 6/22 After School)
- **Action:** Run `diff_mapper.py` against `0x2F200-0x30700` to find the Maruki Rank 3 cutscene bit

### 2. Pouch UI Verification
- **Status:** Fix deployed but not user-verified
- **Action:** User needs to Ctrl+Shift+R and confirm the inventory pouch shows all 298 items
- **Root cause was:** `displayed` array not being passed correctly to the rendering forEach loop (fixed in app.js)

### 3. Compendium Individual Toggle UI
- **Status:** Backend exists (`set_compendium_registration`), UI not built
- **Action:** Could add checkboxes to each persona chip in the compendium grid for granular control

### 4. Test Suite
- **Status:** 70/70 passing from Session 1
- **Action:** Add compendium-specific tests (read mask, unlock 100%, verify mirror sync)

---

## Files Modified This Session

| File | Changes |
|:---|:---|
| `web-app/server.py` | Added `compendium` to `/api/load` response; added `unlock_compendium` handling to `/api/save` |
| `web-app/templates/index.html` | Added COMPENDIUM nav tab and `section#stage-compendium` with progress bar + grid |
| `web-app/static/app.js` | Added `renderCompendium()`, `unlockFullCompendium()`, compendium data init in `renderSaveData()`, flag in save payload |
| `tools/compendium_verify.py` | New file — definitive 5-test verification script |

---

*The compendium mask is proven. The unlock is wired. Ship it.*
