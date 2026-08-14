"""Rank-bit correlation: shrink the 274 oracle-only flag bits using confidant
ranks extracted from every save (DeepSeek Gate C verdict, 2026-08-13).
"""
import os
import struct
import sys
from collections import defaultdict

sys.path.insert(0, r"E:\ai-workspace\knowledge-base\projects\p5r-save-editor")
from core.editor import SaveEditor

REAL = r"C:\Users\kufis\AppData\Roaming\SEGA\P5R\Steam\76561197984149929\savedata"
ORACLE = r"C:\Users\kufis\p5r_buff_save"
ZONE = 0x2F200
ZONE_LEN = 0x30700 - 0x2F200

# (name, path, playthrough, ngplus, modded)
SAVES = [
    ("DATA01", os.path.join(REAL, "DATA01", "DATA.DAT"), "P1", False, False),
    ("DATA02", os.path.join(REAL, "DATA02", "DATA.DAT"), "P1", False, False),
    ("DATA03", os.path.join(REAL, "DATA03", "DATA.DAT"), "P1", False, False),
    ("DATA04", os.path.join(REAL, "DATA04", "DATA.DAT"), "P1", False, False),
    ("DATA05", os.path.join(REAL, "DATA05", "DATA.DAT"), "P1", False, False),
    ("DATA06", os.path.join(REAL, "DATA06", "DATA.DAT"), "P1", False, False),
    ("DATA11", os.path.join(ORACLE, "DATA11", "DATA.DAT"), "P2", True, True),
    ("DATA12", os.path.join(ORACLE, "DATA12", "DATA.DAT"), "P2", True, True),
    ("DATA13", os.path.join(ORACLE, "DATA13", "DATA.DAT"), "P2", True, True),
    ("DATA14", os.path.join(ORACLE, "DATA14", "DATA.DAT"), "P2", True, False),
    ("DATA15", os.path.join(ORACLE, "DATA15", "DATA.DAT"), "P2", True, False),
    ("DATA16", os.path.join(ORACLE, "DATA16", "DATA.DAT"), "P2", True, False),
]

# Confidant save IDs: Justice=9, Faith=33/36, Councillor=35
TARGETS = {"Justice": [9], "Faith": [33, 36], "Councillor": [35]}


def get_confidant_ranks(e):
    d = e.parser.data_payload
    out = {}
    for i in range(23):
        off = 0x136A0 + i * 16
        eid = struct.unpack_from("<H", d, off + 6)[0]
        rank = struct.unpack_from("<H", d, off + 8)[0]
        if eid:
            out[eid] = rank
    return out


def main():
    data = []
    for name, path, pt, ngp, modded in SAVES:
        if not os.path.isfile(path):
            continue
        e = SaveEditor(open(path, "rb").read())
        d = e.parser.data_payload
        zone = bytes(d[ZONE:ZONE + ZONE_LEN])
        ranks = get_confidant_ranks(e)
        data.append({
            "name": name, "pt": pt, "ngp": ngp, "modded": modded,
            "zone": zone,
            "Justice": ranks.get(9, 0),
            "Faith": max(ranks.get(33, 0), ranks.get(36, 0)),
            "Councillor": ranks.get(35, 0),
        })

    for s in data:
        print(f"{s['name']:8} {s['pt']} ng+={int(s['ngp'])} mod={int(s['modded'])} "
              f"Maruki={s['Councillor']:2} Kasumi={s['Faith']:2} Akechi={s['Justice']:2}")

    # Candidate bits: 0 in all P1 saves, 1 in all P2-modded (oracle) saves
    p1 = [s for s in data if not s["ngp"]]
    p2m = [s for s in data if s["ngp"] and s["modded"]]
    p2c = [s for s in data if s["ngp"] and not s["modded"]]

    cands = []
    for boff in range(ZONE_LEN):
        for bit in range(8):
            mask = 1 << bit
            def bval(s):
                return 1 if s["zone"][boff] & mask else 0
            # candidate: 0 in all P1, 1 in all modded oracle
            if all(bval(s) == 0 for s in p1) and all(bval(s) == 1 for s in p2m):
                cands.append((boff, bit))

    print(f"\ncandidates (0 in P1, 1 in modded oracle): {len(cands)}")

    # Correlate against each target rank
    for target in ("Councillor", "Faith", "Justice"):
        print(f"\n=== {target} correlation ===")
        # For each candidate, check monotonic consistency: bit=0 when rank<thresh, 1 when rank>=thresh
        found = []
        for boff, bit in cands:
            mask = 1 << bit
            series = [1 if s["zone"][boff] & mask else 0 for s in data]
            ranks = [s[target] for s in data]
            best = None
            for thresh in range(1, 11):
                ok = all(
                    (r >= thresh) == (b == 1)
                    for r, b in zip(ranks, series)
                    if r > 0 or True  # include all saves
                )
                # ignore saves where rank is 0 AND bit is 1 (rank unknown but flag set is OK only if threshold 1)
                ok = all(
                    (r >= thresh) == (b == 1)
                    for r, b in zip(ranks, series)
                )
                if ok:
                    best = thresh
                    break
            if best:
                found.append((boff, bit, best))
        print(f"  bits perfectly monotonic with rank threshold: {len(found)}")
        for boff, bit, thresh in found[:15]:
            print(f"    +0x{boff:04X}.{bit} -> set at {target} rank >= {thresh}")


if __name__ == "__main__":
    main()
