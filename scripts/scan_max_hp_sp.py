"""Max HP/SP offset scan across the P5R save corpus (2026-08-13).

Strategy: for each party member slot, scan the 0x2B0-byte struct for u16
candidates that (a) appear in EVERY save, (b) are >= the verified current
HP/SP, (c) are non-decreasing with level. Characters are usually saved at
full health, so max-HP candidates often EQUAL current HP on at least one
save.

Usage: env -u PYTHONPATH python scripts/scan_max_hp_sp.py
"""

import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.editor import SaveEditor

REAL_DIR = r"C:\Users\kufis\AppData\Roaming\SEGA\P5R\Steam\76561197984149929\savedata"
ORACLE_DIR = r"C:\Users\kufis\p5r_buff_save"

SAVES = [os.path.join(REAL_DIR, f"DATA{i:02d}", "DATA.DAT") for i in range(1, 7)] + \
        [os.path.join(ORACLE_DIR, f"DATA{i:02d}", "DATA.DAT") for i in range(11, 17)]

PARTY_BASE = 0x2C
STRIDE = 0x2B0
LV_OFF_LEADER = 0x0C
LV_OFF_MEMBER = 0x3C


def load_levels_hp_sp(editor):
    d = editor.parser.data_payload
    rows = []
    for slot in range(10):
        base = PARTY_BASE + slot * STRIDE
        if base + 0x40 > len(d):
            break
        hp = struct.unpack_from("<H", d, base)[0]
        sp = struct.unpack_from("<H", d, base + 4)[0]
        lv_off = LV_OFF_LEADER if slot == 0 else LV_OFF_MEMBER
        lv = struct.unpack_from("<H", d, base + lv_off)[0]
        rows.append({"slot": slot, "lv": lv, "hp": hp, "sp": sp})
    return rows


def main():
    editors = []
    for path in SAVES:
        if not os.path.isfile(path):
            print(f"MISSING: {path}")
            continue
        e = SaveEditor(open(path, "rb").read())
        if not e.is_real_save():
            print(f"NOT 0x31: {path}")
            continue
        editors.append((os.path.basename(os.path.dirname(path)), e))

    if len(editors) < 2:
        print("Need >= 2 usable saves.")
        return

    print(f"Loaded {len(editors)} saves:")
    for name, e in editors:
        rows = load_levels_hp_sp(e)
        lv = [r["lv"] for r in rows[:6]]
        print(f"  {name}: levels {lv}")

    # Build per-slot u16 value tables across saves (every byte offset —
    # the PC struct may misalign u16 fields).
    for slot in range(10):
        vals = []  # per save: dict offset->value
        buffed = []  # True when the save has force-edited 999 HP/SP
        for _, e in editors:
            d = e.parser.data_payload
            base = PARTY_BASE + slot * STRIDE
            if base + 0x2B0 > len(d):
                vals = None
                break
            row = {off: struct.unpack_from("<H", d, base + off)[0]
                   for off in range(0, 0x2B0)}
            vals.append(row)
        if vals is None:
            continue
        levels = [load_levels_hp_sp(e)[slot]["lv"] for _, e in editors]
        cur_hp = [load_levels_hp_sp(e)[slot]["hp"] for _, e in editors]
        cur_sp = [load_levels_hp_sp(e)[slot]["sp"] for _, e in editors]
        buffed = [hp == 999 or sp == 999 for hp, sp in zip(cur_hp, cur_sp)]
        clean = [not b for b in buffed]

        hp_cands = []
        sp_cands = []
        for off in range(0, 0x2B0):
            series = [v[off] for v in vals]
            if any(x == 0 for x in series):
                continue  # must be present in every save
            if min(series) < 40:
                continue  # below plausible max ranges
            if max(series) > 9999:
                continue
            # non-decreasing with level (levels sorted by save order?)
            mono = all(series[i] >= series[i - 1] for i in range(1, len(series)))
            # >= current hp in every NON-buffed save
            ge_hp = all(series[i] >= cur_hp[i] for i in range(len(series)) if clean[i])
            ge_sp = all(series[i] >= cur_sp[i] for i in range(len(series)) if clean[i])
            eq_hp = any(series[i] == cur_hp[i] for i in range(len(series)) if clean[i])
            eq_sp = any(series[i] == cur_sp[i] for i in range(len(series)) if clean[i])
            if ge_hp and mono and eq_hp:
                hp_cands.append((off, series, levels))
            if ge_sp and mono and eq_sp:
                sp_cands.append((off, series, levels))

        print(f"\n=== slot {slot} (levels {levels}) ===")
        print(f"  cur HP: {cur_hp}")
        print(f"  cur SP: {cur_sp}")
        if hp_cands:
            for off, series, lv in hp_cands[:6]:
                print(f"  MAX-HP candidate +0x{off:03X}: {series}")
        else:
            print("  MAX-HP: no candidate (relax criteria?)")
        if sp_cands:
            for off, series, lv in sp_cands[:6]:
                print(f"  MAX-SP candidate +0x{off:03X}: {series}")
        else:
            print("  MAX-SP: no candidate (relax criteria?)")


if __name__ == "__main__":
    main()
