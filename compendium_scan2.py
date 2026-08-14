#!/usr/bin/env python3
"""DeepSeek-prescribed compendium scan (2026-08-14).

Q6 method: slide 29-byte (232-bit) and 32-byte (256-bit) windows; test
bit orderings; score by oracle popcount ~232, mid > fresh, fresh low.
Q2 method: fixed-stride records (0x16, 0x18, 0x20, 0x28, 0x30) with
valid persona-ID tuples + monotone registration flag.
"""
import sys, struct
sys.path.insert(0, '.')
from core.editor import SaveEditor

FRESH = r'C:\Users\kufis\AppData\Roaming\SEGA\P5R\Steam\76561197984149929\savedata\DATA01\DATA.DAT'
MID = r'C:\Users\kufis\p5r_buff_save\DATA12\DATA.DAT'
ORACLE = r'C:\Users\kufis\p5r_buff_save\DATA11\DATA.DAT'

def payload(path):
    return SaveEditor(open(path, 'rb').read()).parser.data_payload

df, dm, do = payload(FRESH), payload(MID), payload(ORACLE)
N = min(len(df), len(dm), len(do))

# Known blocks to mask out (already mapped)
KNOWN = [(0x0000, 0x4000), (0x2F200, 0x30700)]  # header+early, event flags

def masked(off, span):
    for s, e in KNOWN:
        if off < e and off + span > s:
            return True
    return False

# ---- Scan 1: bitmask windows (DeepSeek Q6) ------------------------------
print('=== Bitmask scan: 29B and 32B windows ===')
cands = []
for wlen in (29, 32):
    for off in range(0, N - wlen):
        if masked(off, wlen):
            continue
        # popcounts
        pf = sum(bin(b).count('1') for b in df[off:off+wlen])
        pm = sum(bin(b).count('1') for b in dm[off:off+wlen])
        po = sum(bin(b).count('1') for b in do[off:off+wlen])
        # monotone: mid superset fresh, oracle superset mid
        mono = all(((dm[off+i] | df[off+i]) == dm[off+i]) and
                   ((do[off+i] | dm[off+i]) == do[off+i]) for i in range(wlen))
        if mono and po >= 180 and pm > pf and po > pm:
            cands.append((po, pm, pf, off, wlen))

cands.sort(reverse=True)
print(f'top 12 candidates (oracle_pop, mid_pop, fresh_pop, off, wlen):')
for c in cands[:12]:
    print(f'  popcounts O={c[0]} M={c[1]} F={c[2]}  @ 0x{c[3]:05X}  wlen={c[4]}')

# ---- Scan 2: fixed-stride records (DeepSeek Q2) -------------------------
print('\n=== Stride scan: valid persona-ID tuples + monotone flags ===')
ID_SET = set(range(1, 0x1C6 + 1))
best = []
for stride in (0x16, 0x18, 0x20, 0x28, 0x30):
    for base in range(0, N - stride * 4, 2):
        if masked(base, stride * 4):
            continue
        score = 0
        for slot in range(4):  # check 4 consecutive records
            off = base + slot * stride
            if off + stride > N:
                break
            pid = struct.unpack_from('<H', df, off)[0] if stride >= 2 else df[off]
            pid_o = struct.unpack_from('<H', do, off)[0] if stride >= 2 else do[off]
            # flag byte near start of record
            fl = df[off + 2] if stride >= 4 else 0
            fl_o = do[off + 2] if stride >= 4 else 0
            if pid in ID_SET and pid_o in ID_SET:
                score += 2
            if fl_o and not fl:  # flag turned on across ladder
                score += 1
            if pid == pid_o:
                score += 1
        if score >= 8:
            best.append((score, base, stride))
best.sort(reverse=True)
print(f'top 10 stride candidates (score, base, stride):')
for s, b, st in best[:10]:
    print(f'  score={s}  @ 0x{b:05X}  stride=0x{st:02X}')
