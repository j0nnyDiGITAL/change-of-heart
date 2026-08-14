"""P5R party-block scanner v2 — u16 HP/SP pair fingerprints.

Party (from in-game Stats screenshot):
  Joker   Lv22 HP256 SP136
  Ryuji   Lv20 HP246 SP99
  Morgana Lv21 HP208 SP131
  Ann     Lv21 HP221 SP140
  Yusuke  Lv21 HP234 SP108

Try: u16 LE hp/sp pairs with various spacing; lv as u8 or u16 nearby.
"""
import sys
import struct

sys.path.insert(0, r"E:\ai-workspace\knowledge-base\projects\p5r-save-editor")
from core.crypto import SaveContainer

SAVE = r"E:\ai-workspace\knowledge-base\projects\p5r-save-editor\diff\baseline_DATA02_preprobe.DAT"

PARTY = {
    "Joker":   (22, 256, 136),
    "Ryuji":   (20, 246, 99),
    "Morgana": (21, 208, 131),
    "Ann":     (21, 221, 140),
    "Yusuke":  (21, 234, 108),
}
HP_SP = {name: (hp, sp) for name, (lv, hp, sp) in PARTY.items()}


def main():
    raw = open(SAVE, "rb").read()
    cont = SaveContainer()
    cont.unpack_raw(raw)
    p = cont.data_bytes
    n = len(p)
    print(f"payload {n} bytes")

    # ---- scan 1: u16 hp then u16 sp adjacent (hp at +0, sp at +2) ----
    print("\n== u16 hp@+0 sp@+2, stride search ==")
    hits = []  # (offset, name)
    for off in range(0, n - 4, 2):
        hp = struct.unpack_from("<H", p, off)[0]
        sp = struct.unpack_from("<H", p, off + 2)[0]
        for name, (h, s) in HP_SP.items():
            if hp == h and sp == s:
                hits.append((off, name))
    print(f"{len(hits)} pair hits")
    for off, name in hits[:40]:
        print(f"  0x{off:06X} {name} HP{HP_SP[name][0]} SP{HP_SP[name][1]}")

    # ---- scan 2: u16 hp at +0, sp at +4 ----
    print("\n== u16 hp@+0 sp@+4, stride search ==")
    hits2 = []
    for off in range(0, n - 6, 2):
        hp = struct.unpack_from("<H", p, off)[0]
        sp = struct.unpack_from("<H", p, off + 4)[0]
        for name, (h, s) in HP_SP.items():
            if hp == h and sp == s:
                hits2.append((off, name))
    print(f"{len(hits2)} pair hits")
    for off, name in hits2[:40]:
        print(f"  0x{off:06X} {name}")

    # ---- scan 3: u32 hp/sp like Joker summary but check LV u8 near ----
    print("\n== u32 hp@+0 sp@+4 (joker-style), all members ==")
    hits3 = []
    for off in range(0, n - 8, 4):
        hp = struct.unpack_from("<I", p, off)[0]
        sp = struct.unpack_from("<I", p, off + 4)[0]
        for name, (h, s) in HP_SP.items():
            if hp == h and sp == s:
                hits3.append((off, name))
    print(f"{len(hits3)} pair hits")
    for off, name in hits3[:40]:
        print(f"  0x{off:06X} {name}")

    # ---- scan 4: HP/SP as u16 with LV u8 in a 0x10 window ----
    print("\n== u16 hp+sp anywhere within 8 bytes, lv u8 in +0..+15 ==")
    hits4 = []
    for off in range(0, n - 16):
        hp = struct.unpack_from("<H", p, off)[0]
        for name, (lv, h, s) in PARTY.items():
            if hp != h:
                continue
            for sp_off in (2, 4, 6, 8):
                if off + sp_off + 2 > n:
                    continue
                sp = struct.unpack_from("<H", p, off + sp_off)[0]
                if sp != s:
                    continue
                for lv_off in (8, 10, 12, 14):
                    if off + lv_off >= n:
                        continue
                    if p[off + lv_off] == lv:
                        hits4.append((off, name, sp_off, lv_off))
                        break
                break
    print(f"{len(hits4)} hits")
    for off, name, sp_off, lv_off in hits4[:40]:
        print(f"  0x{off:06X} {name} sp@+{sp_off} lv@+{lv_off}")


if __name__ == "__main__":
    main()
