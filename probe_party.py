"""P5R party-block fingerprint scanner (2026-08-09).

Known party state from in-game Stats screen screenshot:
  Joker   Lv22 HP256 SP136   (verified absolute: u32 @0x2C / @0x30 / LV @0x38)
  Ryuji   Lv20 HP246 SP99
  Morgana Lv21 HP208 SP131
  Ann     Lv21 HP221 SP140
  Yusuke  Lv21 HP234 SP108

Scan the payload for 5 blocks (same stride) carrying these (HP,SP,LV)
triplets. Try several candidate relative layouts, since the PC stride
is unknown (PS4 0x2A8 proved wrong).
"""
import sys
import struct

sys.path.insert(0, r"E:\ai-workspace\knowledge-base\projects\p5r-save-editor")
from core.crypto import SaveContainer

SAVE = r"E:\ai-workspace\knowledge-base\projects\p5r-save-editor\diff\baseline_DATA02_preprobe.DAT"

# name -> (lv, hp, sp)
PARTY = {
    "Joker":   (22, 256, 136),
    "Ryuji":   (20, 246, 99),
    "Morgana": (21, 208, 131),
    "Ann":     (21, 221, 140),
    "Yusuke":  (21, 234, 108),
}

# candidate relative layouts: (hp_off, sp_off, lv_off, width)
LAYOUTS = [
    (0x00, 0x04, 0x0C, 0x10),  # matches verified Joker summary (0x2C/0x30/0x38)
    (0x14, 0x18, 0x24, 0x30),  # PS4-relative offsets
    (0x00, 0x04, 0x08, 0x10),
    (0x04, 0x08, 0x0C, 0x10),
    (0x00, 0x04, 0x10, 0x14),
]


def matches_block(p, base, hp_off, sp_off, lv_off):
    try:
        hp = struct.unpack_from("<I", p, base + hp_off)[0]
        sp = struct.unpack_from("<I", p, base + sp_off)[0]
        lv = struct.unpack_from("<I", p, base + lv_off)[0]
    except struct.error:
        return None
    for name, (l, h, s) in PARTY.items():
        if (lv, hp, sp) == (l, h, s):
            return name
    return None


def main():
    raw = open(SAVE, "rb").read()
    cont = SaveContainer()
    cont.unpack_raw(raw)
    p = cont.data_bytes
    print(f"payload {len(p)} bytes")

    for hp_off, sp_off, lv_off, width in LAYOUTS:
        # joker-anchored: the verified block is at 0x2C hp, so base = 0x2C - hp_off
        joker_base = 0x2C - hp_off
        hits = {}
        # scan all bases for any member match, then test stride consistency
        bases = []
        for base in range(0, len(p) - 0x100, 4):
            name = matches_block(p, base, hp_off, sp_off, lv_off)
            if name:
                bases.append((base, name))
        if not bases:
            print(f"layout +{hp_off:#x}/+{sp_off:#x}/+{lv_off:#x}: no hits")
            continue
        print(f"\nlayout +{hp_off:#x}/+{sp_off:#x}/+{lv_off:#x}: {len(bases)} single hits")
        # group hits by stride: try each pair of consecutive hits' delta
        from collections import defaultdict
        strides = defaultdict(list)
        for i in range(len(bases)):
            for j in range(i + 1, min(i + 30, len(bases))):
                delta = bases[j][0] - bases[i][0]
                if 0x20 <= delta <= 0x800 and delta % 4 == 0:
                    strides[delta].append((bases[i], bases[j]))
        # find stride that explains >=4 distinct members from base list
        for stride, pairs in sorted(strides.items(), key=lambda kv: -len(kv[1])):
            # build chain from any base
            bset = {b for b, _ in bases}
            for start_base, _ in bases:
                chain = []
                b = start_base
                seen = set()
                ok = True
                while b in bset and b not in seen and len(chain) < 6:
                    seen.add(b)
                    name = matches_block(p, b, hp_off, sp_off, lv_off)
                    chain.append((b, name))
                    b += stride
                names = [n for _, n in chain]
                if len(set(names)) >= 4 and len(set(names)) == len(names):
                    print(f"  STRIDE 0x{stride:X} chain from 0x{start_base:X}: {names}")
                    for b, n in chain:
                        hp = struct.unpack_from("<I", p, b + hp_off)[0]
                        sp = struct.unpack_from("<I", p, b + sp_off)[0]
                        lv = struct.unpack_from("<I", p, b + lv_off)[0]
                        print(f"    0x{b:06X} {n:8s} LV{lv} HP{hp} SP{sp}")
            break  # only report best stride per layout


if __name__ == "__main__":
    main()
