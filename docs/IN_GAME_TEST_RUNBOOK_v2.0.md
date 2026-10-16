# Change of Heart 2.0 — In-Game Verification Runbook

**Target:** Persona 5 Royal (PC / Steam / GamePass)  
**Branch:** `feature/change-of-heart-2.0` (PR #7 Draft)  
**Safety Status:** Dual-CRC32 + AES-256 + Atomic Replacement + Automated Pre-Replacement Rollback  

---

## 1. Quick Start (How to Launch)

From the project root (`E:\ai-workspace\knowledge-base\projects\p5r-save-editor`):

```powershell
# Option A: Run native Python app (WebView2 desktop window with browser fallback)
python main.py

# Option B: Run headless server and open in your default browser
python server.py
# Then open http://127.0.0.1:3000 in your browser
```

> [!NOTE]
> **Safety Guard:** The editor automatically detects if `P5R.exe` is running and will block save writes with an `HTTP 409` conflict warning. Always save while in Leblanc or safe rooms, and close or pause to title screen before committing save writes.

---

## 2. In-Game Testing Checklist

Follow this workflow with your actual save files to verify 2.0 features end-to-end:

### Test 1: Save Loading & Diagnostic Inspector
- [ ] Launch editor and click **📂 BROWSE...** or select your discovered Steam save (`DATA01/DATA.DAT`).
- [ ] Click **🔍 INSPECT SAVE**:
  - Container status should show **Grade A (CLEAN)**.
  - Outer File CRC32 and Inner Data CRC32 should both show `MATCH / VALID`.
  - Compendium mirror status should show `IN SYNC`.

### Test 2: Leader & Daily Life Edits
- [ ] Edit **Yen Balance** (e.g. set to `7,777,777`).
- [ ] Edit **Social Stats** (e.g. increase Knowledge or Guts by 1 rank).
- [ ] Click **💾 SAVE CHANGES & RE-SIGN**:
  - Verify popup confirms atomic write and timestamped backup creation (`backups/*.zip`).
- [ ] **Load in Game:** Boot P5R, load the modified slot:
  - Check that Yen reflects exact amount.
  - Check that Social Stat progress meter is updated and dialogue reflects new rank.

### Test 3: Staged Review & Tamper Invalidation
- [ ] Make 2 changes (e.g. change calling card group name, adjust an item quantity).
- [ ] Click **📋 REVIEW STAGED**:
  - Verify the Before/After diff accurately displays only the modified fields.
- [ ] Confirm the staged review.
- [ ] Edit a third field before saving:
  - Verify that the previous confirmation is automatically invalidated, requiring you to re-review the final diff before disk commit.

### Test 4: Inventory & Consumable Offsets
- [ ] Open **Inventory** tab.
- [ ] Adjust quantities of standard items (*Lockpick, Takemedic, Homunculus, Life Ointment*).
- [ ] Click Save and boot in game:
  - Verify that item counts match exactly in the Infiltration / Item menu.
  - Verify that no adjacent items shifted or changed (Universal Engine Offset Formula check).

### Test 5: Velvet Room & Compendium Unlock
- [ ] Open **Velvet Room / Compendium** tab.
- [ ] If desired, test the **Unlock 100% Compendium** button.
- [ ] Click Save and boot in game:
  - Visit the Velvet Room and check the Compendium registry.
  - In-game registration percentage should display 100% (224 summonable personas registered).
  - Verify that existing custom persona builds in your stock were NOT overwritten.

### Test 6: Cross-Save Semantic Transfer
- [ ] Open **Save Comparator & Transfer** (`/api/transfer`).
- [ ] Select a secondary donor save (e.g. an endgame or NG+ save).
- [ ] Check **Compendium** or **Money** transfer.
- [ ] Verify that the modal generates a typed preview diff before confirmation.
- [ ] Confirm and check that the destination save atomically adopts the donor items/records.

### Test 7: Safety Vault & 1-Click Rollback
- [ ] Open **Backups & Safety Vault** tab.
- [ ] Select a recent timestamped backup from the dropdown.
- [ ] Click **Restore Backup**:
  - Verify editor reloads original pre-edit state.
  - Boot game and confirm the save restored to the exact prior snapshot.

---

## 3. Reporting Issues

If any in-game check exhibits unexpected behavior:
1. Note the save slot (`DATA01`, `DATA02`, etc.) and game calendar date.
2. Check the `backups/` folder for the automatic pre-edit ZIP snapshot.
3. Note the exact field or item ID that diverged.
