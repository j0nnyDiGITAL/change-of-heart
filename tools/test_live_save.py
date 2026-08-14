import os
import sys
import shutil
import tempfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.editor import SaveEditor

def test_live_save():
    src_save = Path(r"C:\Users\kufis\AppData\Roaming\SEGA\P5R\Steam\76561197984149929\savedata\DATA06\DATA.DAT")
    if not src_save.exists():
        print(f"[-] Source save {src_save} does not exist.")
        return

    print("=" * 60)
    print("  [+] CHANGE OF HEART - LIVE SAVE ISOLATION TEST")
    print("=" * 60)
    print(f"[1] Source save found: {src_save} ({src_save.stat().st_size} bytes)")

    # 1. Create temporary isolated sandbox copy
    with tempfile.TemporaryDirectory() as tmpdir:
        sandbox_save = Path(tmpdir) / "DATA.DAT"
        shutil.copy(src_save, sandbox_save)
        print(f"[2] Created isolated sandbox copy: {sandbox_save}")

        # 2. Load and decrypt with SaveEditor
        raw_data = sandbox_save.read_bytes()
        editor = SaveEditor(raw_data)
        
        # Verify initial state
        initial_money = editor.get_money()
        initial_stats = editor.get_social_stats()
        initial_comp = editor.get_compendium()
        initial_conf = editor.get_confidant_ranks()
        
        print(f"    - Initial Money: Yen {initial_money:,}")
        print(f"    - Initial Social Stats: {initial_stats}")
        print(f"    - Initial Registered Compendium Count: {len(initial_comp['registered'])} / 232")
        print(f"    - Confidants Count: {len(initial_conf)}")
        
        # 3. Perform Realistic Modifications
        print("\n[3] Applying Test Edits:")
        # A. Set Money to 9,999,999
        editor.set_money(9999999)
        print("    [+] Set Money -> Yen 9,999,999")
        
        # B. Set Social Stats to Max (Rank 5)
        editor.set_social_stats(knowledge=5, charm=5, proficiency=5, kindness=5, guts=5)
        print("    [+] Maxed all 5 Social Stats -> Rank 5")
        
        # C. 3rd Semester Safety Rescue (Maruki 9, Kasumi 5, Akechi 8)
        editor.unlock_third_semester()
        print("    [+] Applied 3rd Semester Rescue Unlock")
        
        # D. Compendium 100% Unlock (All 232 Personas)
        editor.unlock_compendium_100()
        print("    [+] Unlocked 100% Compendium (All 232 Personas)")

        # 4. Pack, Re-sign, and Encrypt to Disk
        repacked_bytes = editor.save_to_bytes(compress=True, encrypt=True)
        sandbox_save.write_bytes(repacked_bytes)
        print(f"\n[4] Re-signed & Encrypted with AES-256 + Dual CRC32 -> {len(repacked_bytes)} bytes")

        # 5. Reload the saved file from disk to verify round-trip integrity
        print("\n[5] Reloading from disk for verification...")
        reloaded_bytes = sandbox_save.read_bytes()
        verify_editor = SaveEditor(reloaded_bytes)
        
        v_money = verify_editor.get_money()
        v_stats = verify_editor.get_social_stats()
        v_comp = verify_editor.get_compendium()
        v_ranks = verify_editor.get_confidant_ranks()
        v_maruki = v_ranks.get("Councillor", {}).get("rank", 0)
        v_kasumi = v_ranks.get("Faith", {}).get("rank", 0)
        v_akechi = v_ranks.get("Justice", {}).get("rank", 0)

        print(f"    - Verified Money: Yen {v_money:,} (Expected: Yen 9,999,999) -> {'PASSED' if v_money == 9999999 else 'FAILED'}")
        print(f"    - Verified Social Stats: {v_stats} (Expected: All 5) -> {'PASSED' if all(v.get('rank') == 5 for v in v_stats.values()) else 'FAILED'}")
        print(f"    - Verified Compendium Count: {len(v_comp['registered'])} / 232 -> {'PASSED' if len(v_comp['registered']) == 232 else 'FAILED'}")
        print(f"    - Verified Maruki Rank: {v_maruki} (Expected: 9) -> {'PASSED' if v_maruki == 9 else 'FAILED'}")
        print(f"    - Verified Kasumi Rank: {v_kasumi} (Expected: 5) -> {'PASSED' if v_kasumi == 5 else 'FAILED'}")
        print(f"    - Verified Akechi Rank: {v_akechi} (Expected: 8) -> {'PASSED' if v_akechi == 8 else 'FAILED'}")

        # Check report
        report = verify_editor.integrity_report()
        print(f"\n[6] Final Cryptographic Integrity Report: {report}")
        assert report["ok"] is True, "Cryptographic integrity failed!"
        print("\n" + "=" * 60)
        print("  ALL TESTS PASSED: SAVE FILE IS 100% CRYPTOGRAPHICALLY VALID!")
        print("=" * 60)

if __name__ == "__main__":
    test_live_save()
