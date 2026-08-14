#!/usr/bin/env python3
"""Compendium bitmask hunt — Gemini oracle verdict #6 (2026-08-14).

Hypothesis: compendium registration = dense contiguous bitfield over persona
IDs 0x001..0x1C6 (454 bits = 56.75 bytes, likely padded to 57/64/128).

Method: for every byte offset, compute the bitwise delta across the save
ladder (fresh -> mid -> 100% oracle). A registration bitmask is:
  - CONTIGUOUS (~57-128 bytes)
  - DENSE (most of the 454 persona bits are set in the oracle)
  - MONOTONIC (bits only turn on as the game progresses, never off)
  - positioned so oracle bits are a superset of fresh bits

Scan all offsets, score regions, report the top candidates.
"""
import sys, struct
sys.path.insert(0, '.')
from core.editor import SaveEditor

FRESH = r'C:\Users\kufis\AppData\Roaming\SEGA\P5R\Steam\76561197984149929\savedata\DATA01\DATA.DAT'
ORACLE = r'C:\Users\kufis\p5r_buff_save\DATA11\DATA.DAT'
MID = r'C:\Users\kufis\p5r_buff_save\DATA12\DATA.DAT'  # second NG+ slot

def payload(path):
    e = SaveEditor(open(path, 'rb').read())
    return e.parser.data_payload

print('loading ladder...')
df = payload(FRESH)
do = payload(ORACLE)
dm = payload(MID)
N = min(len(df), len(do), len(dm))
print(f'payload sizes: fresh={len(df)} oracle={len(do)} mid={len(dm)}')

# Persona ID set (0x001..0x1C6 = 1..454)
P_IDS = set(range(1, 0x1C6 + 1))

# ---- Scan 1: bitwise delta density -------------------------------------
# For each offset, count bits set in oracle but not fresh (new bits).
# Registration bits are monotonic: fresh bits ⊆ mid bits ⊆ oracle bits.
results = []
for off in range(0, N - 128):
    new_bits = 0
    mono_ok = True
    for i in range(128):
        bf, bm, bo = df[off+i], dm[off+i], do[off+i]
        # monotonic: mid must be superset of fresh, oracle superset of mid
        if (bm | bf) != bm or (bo | bm) != bo:
            mono_ok = False
            break
        new_bits += bin(bo & ~bf).count('1')
    if mono_ok and new_bits >= 32:  # at least 32 new bits in 128B window
        results.append((new_bits, off))

results.sort(reverse=True)
print(f'\n=== Top 15 monotonic bitmask windows (128B, >=32 new bits) ===')
for nb, off in results[:15]:
    print(f'  offset 0x{off:05X}  new_bits={nb}')

# ---- Scan 2: 57-byte exact-dense window (454 bits) ----------------------
best57 = []
for off in range(0, N - 64):
    # count bytes that are purely additive (oracle superset fresh)
    add = sum(1 for i in range(57) if (do[off+i] & ~df[off+i]) == (do[off+i] - (do[off+i] & df[off+i])) or True)
    # simpler: total set bits in oracle window that are new vs fresh
    new_bits = sum(bin(do[off+i] & ~df[off+i]).count('1') for i in range(57))
    oracle_set = sum(bin(do[off+i]).count('1') for i in range(57))
    if oracle_set >= 200 and new_bits >= 100:
        best57.append((oracle_set, new_bits, off))
best57.sort(reverse=True)
print(f'\n=== Top 10 dense 57B windows (oracle_set>=200, new>=100) ===')
for os_, nb, off in best57[:10]:
    print(f'  offset 0x{off:05X}  oracle_set={os_}  new_bits={nb}')

# ---- Scan 3: u16 ID-set density (per-entry struct hypothesis) -----------
# regions where many u16 values are valid persona IDs and grow across ladder
best16 = []
for off in range(0, N - 256, 2):
    hit = 0
    grow = 0
    for i in range(0, 256, 2):
        vf = struct.unpack_from('<H', df, off+i)[0]
        vo = struct.unpack_from('<H', do, off+i)[0]
        if vo in P_IDS:
            hit += 1
            if vf == 0:
                grow += 1
    if hit >= 20:
        best16.append((hit, grow, off))
best16.sort(reverse=True)
print(f'\n=== Top 10 u16 persona-ID dense windows (256B, >=20 hits) ===')
for hit, grow, off in best16[:10]:
    print(f'  offset 0x{off:05X}  valid_ids={hit}  grown_from_zero={grow}')
