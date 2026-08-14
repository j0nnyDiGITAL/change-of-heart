"""P5R quick-win hunt: Baton Pass / Technical ranks / Mementos stamps.

Oracle (Buff Joker DATA11, 3rd-semester 100%): baton pass maxed on
everyone (rank 3 per member), technical rank maxed (3), all stamps.
Baseline (6/14 save): those systems at/near zero.

Strategy: find byte windows where the ORACLE reads a compact cluster of
small values (0..3 for ranks, repeated) and the BASELINE reads 0/1 at the
same offsets. Baton: 10 members -> look for runs of 3s. Stamps: per-area
counts -> look for equal nonzero clusters (all maxed = same value).
"""
import sys
import struct
from collections import Counter

sys.path.insert(0, r"E:\ai-workspace\knowledge-base\projects\p5r-save-editor")
from core.crypto import SaveContainer

ORACLE = r"C:/Users/kufis/p5r_buff_save/DATA11/DATA.DAT"
BASELINE = r"E:\ai-workspace\knowledge-base\projects\p5r-save-editor\diff\baseline_DATA02_preprobe.DAT"


def payload(path):
    c = SaveContainer()
    c.unpack_raw(open(path, "rb").read())
    return c.data_bytes


def main():
    o = payload(ORACLE)
    b = payload(BASELINE)
    n = len(o)
    print(f"oracle {n}B, baseline {len(b)}B")

    candidates = []

    # --- hunt 1: consecutive runs of u8 in {1,2,3} length 6..12, oracle all >= baseline ---
    for start in range(n - 16):
        window = o[start:start + 12]
        if all(v in (1, 2, 3) for v in window):
            base = b[start:start + 12]
            # oracle should dominate baseline (maxed vs fresh)
            if all(base[i] <= window[i] for i in range(12)) and any(base[i] < window[i] for i in range(12)):
                candidates.append((start, "run123", list(window), list(base)))

    # --- hunt 2: 10-byte spread at stride (baton ranks per member) ---
    for stride in (1, 2, 4, 8, 16):
        for start in range(n - stride * 10):
            vals = [o[start + i * stride] for i in range(10)]
            if all(v in (1, 2, 3) for v in vals):
                base = [b[start + i * stride] for i in range(10)]
                if all(base[i] <= vals[i] for i in range(10)) and any(base[i] < vals[i] for i in range(10)):
                    candidates.append((start, f"stride{stride}", vals, base))

    # --- hunt 3: stamp counts — 7ish equal small ints (all sections maxed) ---
    for start in range(n - 16):
        window = o[start:start + 12]
        if all(v in range(1, 40) for v in window):
            c = Counter(window)
            top = c.most_common(1)[0]
            if top[1] >= 6 and top[0] > 1:  # 6+ identical values >1
                base = b[start:start + 12]
                if all(base[i] <= window[i] for i in range(12)) and any(base[i] < window[i] for i in range(12)):
                    candidates.append((start, "stamps", list(window), list(base)))

    # dedupe + sort by interestingness (baseline mostly zeros)
    seen = set()
    out = []
    for start, kind, ov, bv in candidates:
        key = (start // 8) * 8
        if key in seen:
            continue
        seen.add(key)
        zeros = sum(1 for v in bv if v == 0)
        out.append((start, kind, ov, bv, zeros))
    out.sort(key=lambda x: -x[4])

    print(f"\n=== top candidates ({len(out)} unique) ===")
    for start, kind, ov, bv, zeros in out[:25]:
        print(f"0x{start:06X} [{kind}] oracle={ov}  baseline={bv}  (base zeros={zeros})")


if __name__ == "__main__":
    main()
