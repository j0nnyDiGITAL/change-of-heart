"""
Apply live modifications directly to real Steam save DATA06 with automatic backup.
"""

import sys
import shutil
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.editor import SaveEditor

def apply_to_real_save():
    save_path = Path(r"C:\Users\kufis\AppData\Roaming\SEGA\P5R\Steam\76561197984149929\savedata\DATA06\DATA.DAT")
    if not save_path.exists():
        print(f"[-] Target save {save_path} not found!")
        return

    # 1. Create safety backup
    backup_dir = save_path.parent / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = backup_dir / f"DATA_pre_edit_{ts}.DAT"
    shutil.copy(save_path, backup_file)
    print(f"[+] Created safety backup at: {backup_file}")

    # 2. Load save
    editor = SaveEditor(save_path.read_bytes())

    # 3. Apply edits
    editor.set_money(9999999)
    editor.set_social_stats(knowledge=5, charm=5, proficiency=5, kindness=5, guts=5)
    editor.unlock_third_semester()
    editor.unlock_compendium_100()

    # 4. Save directly to Steam save file
    out_bytes = editor.save_to_bytes(compress=True, encrypt=True)
    save_path.write_bytes(out_bytes)
    print(f"[+] Successfully wrote {len(out_bytes)} re-signed bytes to: {save_path}")

    # 5. Verify from disk
    verify_ed = SaveEditor(save_path.read_bytes())
    print(f"    - Money: ¥{verify_ed.get_money():,}")
    print(f"    - Social Stats: {verify_ed.get_social_stats()}")
    print(f"    - Registered Compendium Count: {len(verify_ed.get_compendium()['registered'])} / 232")
    print(f"    - Integrity: {verify_ed.integrity_report()}")

if __name__ == "__main__":
    apply_to_real_save()
