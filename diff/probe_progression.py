"""Probe: locate Baton Pass ranks, Technical rank, Mementos stamps in P5R PC save.
Compares oracle (100% NG++) vs fresh (6/14) payloads + SYSTEM.DAT + DATA14/15/16.
"""
import sys
sys.path.insert(0, r'E:/ai-workspace/knowledge-base/projects/p5r-save-editor')
from core.crypto import SaveContainer

ORACLE = r'C:/Users/kufis/p5r_buff_save/DATA11/DATA.DAT'
FRESH = r'E:/ai-workspace/knowledge-base/projects/p5r-save-editor/diff/baseline_DATA02_preprobe.DAT'
SYSTEM = r'C:/Users/kufis/p5r_buff_save/SYSTEM/SYSTEM.DAT'
D14 = r'C:/Users/kufis/p5r_buff_save/DATA14/DATA.DAT'
D15 = r'C:/Users/kufis/p5r_buff_save/DATA15/DATA.DAT'
D16 = r'C:/Users/kufis/p5r_buff_save/DATA16/DATA.DAT'


def load(path):
    c = SaveContainer()
    c.unpack_raw(open(path, 'rb').read())
    return c.data_bytes


def diff_runs(a, b):
    """Return list of (start, end) differing runs."""
    runs = []
    i = 0
    n = min(len(a), len(b))
    while i < n:
        if a[i] != b[i]:
            j = i
            while j < n and a[j] != b[j]:
                j += 1
            runs.append((i, j))
            i = j
        else:
            i += 1
    return runs


def summarize_run(a, b, start, end, ctx=8):
    lines = []
    lo = max(0, start - ctx)
    hi = min(len(a), end + ctx)
    lines.append(f"  [{start:#x}..{end:#x}) len={end-start}")
    for off in range(start, end):
        lines.append(f"    {off:#06x}: A={a[off]:02x} B={b[off]:02x}")
    return "\n".join(lines)


def equal_value_runs(buf, val, min_len=5, limit=60):
    """Maximal runs of a single repeated byte value >= min_len."""
    out = []
    i = 0
    n = len(buf)
    while i < n:
        if buf[i] == val:
            j = i
            while j < n and buf[j] == val:
                j += 1
            if j - i >= min_len:
                out.append((i, j))
            i = j
        else:
            i += 1
    return out[:limit]


def find_value_arrays(buf, val, min_len=3, limit=40):
    """Find offsets where buf[off]==val and buf[off+1]==val (2+ consecutive), with context."""
    out = []
    i = 0
    n = len(buf)
    while i < n - 1:
        if buf[i] == val and buf[i + 1] == val:
            j = i
            while j < n and buf[j] == val:
                j += 1
            out.append((i, j))
            i = j
        else:
            i += 1
    return out[:limit]


def main():
    oracle = load(ORACLE)
    fresh = load(FRESH)
    d14 = load(D14)
    d15 = load(D15)
    d16 = load(D16)
    system = load(SYSTEM)
    print(f"oracle={len(oracle)} fresh={len(fresh)} sys={len(system)} d14={len(d14)} d15={len(d15)} d16={len(d16)}")

    # ---- 1. Overall diff oracle vs fresh ----
    runs = diff_runs(oracle, fresh)
    print(f"\n=== DIFF oracle-vs-fresh: {len(runs)} runs ===")
    for s, e in runs:
        print(f"  {s:#06x}..{e:#06x} len={e-s}")

    # ---- 2. Targeted: in diff runs, print small-value clusters ----
    print("\n=== DIFF runs containing small values (<=63) on BOTH sides (candidate arrays) ===")
    for s, e in runs:
        if e - s < 2:
            continue
        # fraction of bytes <= 63 in both
        small = sum(1 for k in range(s, e) if oracle[k] <= 63 and fresh[k] <= 63)
        frac = small / (e - s)
        if frac >= 0.6 and e - s >= 3:
            print(f"\n  RUN {s:#06x}..{e:#06x} len={e-s} smallfrac={frac:.2f}")
            print(summarize_run(oracle, fresh, s, e, ctx=4))

    # ---- 3. Value-3 clusters in oracle payload ----
    print("\n=== RUNS of byte 0x03 (len>=4) in ORACLE payload ===")
    for s, e in equal_value_runs(oracle, 3, 4):
        print(f"  {s:#06x}..{e:#06x} len={e-s}")

    print("\n=== RUNS of byte 0x03 (len>=4) in FRESH payload ===")
    for s, e in equal_value_runs(fresh, 3, 4):
        print(f"  {s:#06x}..{e:#06x} len={e-s}")

    # ---- 4. Runs of other small equal values (2..30) len>=4, oracle only ----
    print("\n=== EQUAL-VALUE runs (len>=5) ORACLE for vals 2..40 ===")
    for v in range(2, 41):
        for s, e in equal_value_runs(oracle, v, 5):
            fv = fresh[s] if s < len(fresh) else -1
            print(f"  val={v:02x} {s:#06x}..{e:#06x} len={e-s} fresh@start={fv:02x}")

    # ---- 5. SYSTEM payload scans ----
    print("\n=== SYSTEM payload: nonzero bytes ===")
    nz = [(i, system[i]) for i in range(len(system)) if system[i] != 0]
    print(f"  nonzero count: {len(nz)}")
    # cluster them
    clusters = []
    for i, v in nz:
        if clusters and i - clusters[-1][1] <= 16:
            clusters[-1][1] = i
            clusters[-1][2].append((i, v))
        else:
            clusters.append([i, i, [(i, v)]])
    for c in clusters:
        print(f"  cluster {c[0]:#06x}..{c[1]:#06x} ({len(c[2])} bytes): {', '.join(f'{o:#06x}={v:02x}' for o, v in c[2][:40])}")

    # ---- 6. Cross-check DATA14/15/16 ----
    print("\n=== DATA14 vs DATA11 diff runs (12/24 Lv91 vs 100% NG++) ===")
    for s, e in diff_runs(d14, oracle):
        if e - s >= 2:
            print(f"  {s:#06x}..{e:#06x} len={e-s}")
    print("\n=== DATA16 (Clear Data) vs DATA11 diff runs ===")
    for s, e in diff_runs(d16, oracle):
        if e - s >= 2:
            print(f"  {s:#06x}..{e:#06x} len={e-s}")
    print("\n=== DATA14 vs DATA15 diff runs (same day, Lv91 vs Lv75) ===")
    for s, e in diff_runs(d14, d15):
        if e - s >= 2:
            print(f"  {s:#06x}..{e:#06x} len={e-s}")

    # ---- 7. Value-3 runs in DATA14/15/16 ----
    for name, buf in (("D14", d14), ("D15", d15), ("D16", d16)):
        print(f"\n=== RUNS of 0x03 (len>=4) in {name} ===")
        for s, e in equal_value_runs(buf, 3, 4):
            print(f"  {s:#06x}..{e:#06x} len={e-s}")

    # ---- 8. Candidate: 10-member baton ranks as contiguous u8 array (10 bytes, vals 0-3) ----
    print("\n=== Windows where 10 consecutive bytes are all in [0..3] (baton candidate), both payloads ===")
    for name, buf in (("oracle", oracle), ("fresh", fresh)):
        hits = []
        for i in range(len(buf) - 9):
            if all(0 <= buf[i + k] <= 3 for k in range(10)):
                hits.append(i)
        print(f"  {name}: {len(hits)} windows")
        for h in hits[:30]:
            print(f"    {h:#06x}: {list(buf[h:h+10])}")


if __name__ == "__main__":
    main()
