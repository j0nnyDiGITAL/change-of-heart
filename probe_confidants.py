"""P5R confidant-block fingerprint scanner (Path B, 2026-08-09).

Loads the decrypted payload, then scans for the 23-arcana confidant
block under many layout hypotheses:
  - contiguous u8 ranks (arcana order)
  - strided u8 ranks (rank,progress / rank,pad / larger structs)
  - u8 ranks with value transforms (rank, rank-1, rank*2-1, rank+4, rank+5)
  - u16 LE ranks at stride 2/4/8/16
  - (rank u8, progress u8) pairs
Known ground truth (screenshots, Jun 2026): Fool5 Magician3 Hierophant3
Lovers6 Chariot5 Justice1 Strength1 Death6 Moon3 Faith2 Councillor2
=> multiset {1,1,2,2,3,3,3,5,5,6,6}; other 12 arcana should be 0/1
(locked or rank 1), with tolerance.
"""
import sys
import struct
from collections import Counter

sys.path.insert(0, r"E:\ai-workspace\knowledge-base\projects\p5r-save-editor")
from core.crypto import SaveContainer

SAVE = r"E:\ai-workspace\knowledge-base\projects\p5r-save-editor\diff\baseline_DATA02_preprobe.DAT"

KNOWN = [5, 3, 3, 6, 5, 1, 1, 6, 3, 2, 2]  # 11 known ranks
KNOWN_C = Counter(KNOWN)
UNKNOWN_OK = {0, 1, 2}  # locked or early ranks


def matches(values):
    """23 values: the 11 known ranks present, rest in UNKNOWN_OK."""
    if len(values) != 23:
        return False
    c = Counter(values)
    for k, v in KNOWN_C.items():
        if c.get(k, 0) < v:
            return False
    rem = c - KNOWN_C
    for k in rem:
        if k not in UNKNOWN_OK:
            return False
    return True


def main():
    raw = open(SAVE, "rb").read()
    cont = SaveContainer()
    cont.unpack_raw(raw)
    payload = cont.data_bytes
    print(f"payload {len(payload)} bytes, magic {cont.file_magic}")

    hits = []

    # --- hypothesis 1: strided u8 ranks, base offset = start of block ---
    for stride in (1, 2, 3, 4, 6, 8, 12, 16, 24, 32):
        for base in range(0, min(stride, 64)):
            for start in range(base, len(payload) - stride * 23, stride):
                vals = [payload[start + i * stride] for i in range(23)]
                if matches(vals):
                    hits.append(("u8 stride=%d" % stride, start, vals))

    # --- hypothesis 2: u16 LE ranks ---
    for stride in (2, 4, 8, 16):
        for start in range(0, len(payload) - stride * 23, 2):
            vals = [struct.unpack_from("<H", payload, start + i * stride)[0] for i in range(23)]
            if all(v <= 10 for v in vals) and matches(vals):
                hits.append(("u16 stride=%d" % stride, start, vals))

    # --- hypothesis 3: rank encoded with transforms ---
    for name, fn in (
        ("rank-1", lambda v: v + 1),
        ("rank*2-1", lambda v: (v + 1) // 2),
        ("rank+4", lambda v: v - 4),
        ("rank+5", lambda v: v - 5),
    ):
        for start in range(0, len(payload) - 23):
            vals = [fn(payload[start + i]) for i in range(23)]
            if matches(vals):
                hits.append((name, start, [payload[start + i] for i in range(23)]))

    # --- hypothesis 4: (rank u8, progress u8) pairs, rank at even offset ---
    for start in range(0, len(payload) - 46, 2):
        vals = [payload[start + i * 2] for i in range(23)]
        if matches(vals):
            hits.append(("pair-rank-even", start, vals))

    print(f"\n=== {len(hits)} hits ===")
    seen = set()
    for kind, start, vals in hits:
        key = (kind, start)
        if key in seen:
            continue
        seen.add(key)
        print(f"{kind} @ 0x{start:X}  ranks={vals}")
        if len(seen) > 12:
            break

    # context dump around the strongest contiguous hit
    u8_contig = [h for h in hits if h[0] == "u8 stride=1"]
    if u8_contig:
        start = u8_contig[0][1]
        print(f"\ncontext around 0x{start:X}:")
        lo = max(0, start - 16)
        hi = min(len(payload), start + 23 * 1 + 16)
        for off in range(lo, hi, 16):
            chunk = payload[off:off + 16]
            print(f"0x{off:06X}: " + " ".join(f"{b:02X}" for b in chunk))


if __name__ == "__main__":
    main()
