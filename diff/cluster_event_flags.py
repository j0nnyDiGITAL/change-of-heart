"""Event-flag clustering for P5R 0x2F200 zone (oracle-designed, 2026-08-13).
5-stage bit signatures: fresh/early/mid/late/oracle. Candidates must be
monotonic 0->1. Output: cluster map + rank-event candidates.
"""
import os
import sys
import struct
from collections import defaultdict

sys.path.insert(0, r"E:\ai-workspace\knowledge-base\projects\p5r-save-editor")
from core.editor import SaveEditor

REAL = r"C:\Users\kufis\AppData\Roaming\SEGA\P5R\Steam\76561197984149929\savedata"
ORACLE = r"C:\Users\kufis\p5r_buff_save"
ZONE = 0x2F200
ZONE_LEN = 0x30700 - 0x2F200  # 5376

STAGES = {
    "fresh": [os.path.join(REAL, f"DATA{i:02d}", "DATA.DAT") for i in (3, 4, 5, 6)],
    "early": [os.path.join(REAL, f"DATA{i:02d}", "DATA.DAT") for i in (1, 2)],
    "mid":   [os.path.join(ORACLE, "DATA16", "DATA.DAT")],
    "late":  [os.path.join(ORACLE, f"DATA{i:02d}", "DATA.DAT") for i in (14, 15)],
    "oracle":[os.path.join(ORACLE, f"DATA{i:02d}", "DATA.DAT") for i in (11, 12, 13)],
}

# Confidant ranks per save for cross-match (arcana order 1-21, Faith 33/36, Councillor 35)
def read_confidants(e):
    d = e.parser.data_payload
    out = {}
    for i in range(23):
        off = 0x136A0 + i * 16
        eid = struct.unpack_from("<H", d, off + 6)[0]
        rank = struct.unpack_from("<H", d, off + 8)[0]
        if eid:
            out[eid] = rank
    return out


def load_zone(path):
    e = SaveEditor(open(path, "rb").read())
    d = e.parser.data_payload
    return bytes(d[ZONE:ZONE + ZONE_LEN]), e


def consensus(paths):
    """Per-byte consensus across saves in a stage: 1 if all 1, 0 if all 0, -1 mixed."""
    zones = []
    for p in paths:
        if os.path.isfile(p):
            zones.append(load_zone(p)[0])
    if not zones:
        return None
    out = []
    for i in range(ZONE_LEN):
        vals = {z[i] for z in zones}
        out.append(vals.pop() if len(vals) == 1 else -1)
    return out


def main():
    stages = {}
    for name, paths in STAGES.items():
        stages[name] = consensus(paths)
        if stages[name] is None:
            print(f"stage {name}: no saves found")
            return

    # Per-bit 5-stage signatures
    sig_map = defaultdict(list)  # signature -> [(byte_offset, bit)]
    for boff in range(ZONE_LEN):
        bits = []
        for sname in ("fresh", "early", "mid", "late", "oracle"):
            b = stages[sname][boff]
            bits.append(b)
        # expand byte to bits
        for bit in range(8):
            sig = tuple((b >> bit) & 1 if b >= 0 else -1 for b in bits)
            sig_map[sig].append((boff, bit))

    print(f"zone bytes: {ZONE_LEN}, distinct signatures: {len(sig_map)}")
    for sig, locs in sorted(sig_map.items(), key=lambda x: -len(x[1]))[:15]:
        print(f"  sig {sig}: {len(locs)} bits (e.g. +0x{locs[0][0]:04X}.{locs[0][1]})")

    # Candidates: monotonic 0->1, all stages clean (no -1), oracle=1, fresh=0
    mono = [(s, l) for s, l in sig_map.items()
            if -1 not in s and s[0] == 0 and s[-1] == 1
            and all(s[i] <= s[i+1] for i in range(4))]
    print(f"\nmonotonic 0->1 candidates: {sum(len(l) for _, l in mono)} bits in {len(mono)} groups")
    for sig, locs in sorted(mono, key=lambda x: -len(x[1]))[:12]:
        off, bit = locs[0]
        print(f"  sig {sig}: {len(locs)} bits (first +0x{off:04X}.{bit})")

    # Cross-match with confidant ranks on the oracle save
    oracle_path = STAGES["oracle"][0]
    _, e = load_zone(oracle_path)
    conf = read_confidants(e)
    print(f"\noracle confidant ranks: {sorted(conf.items())[:8]} ... (Maruki(35)={conf.get(35)}, Faith(33)={conf.get(33)}, Justice(9)={conf.get(9)})")


if __name__ == "__main__":
    main()
