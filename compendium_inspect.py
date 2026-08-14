#!/usr/bin/env python3
"""Inspect the two mirror-pair candidates: bitmask vs u16 ID array."""
import sys, struct
sys.path.insert(0, '.')
from core.editor import SaveEditor

FRESH = r'C:\Users\kufis\AppData\Roaming\SEGA\P5R\Steam\76561197984149929\savedata\DATA01\DATA.DAT'
ORACLE = r'C:\Users\kufis\p5r_buff_save\DATA11\DATA.DAT'

def payload(path):
    return SaveEditor(open(path, 'rb').read()).parser.data_payload

df = payload(FRESH)
do = payload(ORACLE)

def dump(off, n, label):
    print(f'\n=== {label} @ 0x{off:05X} (fresh vs oracle, {n}B) ===')
    for i in range(0, n, 16):
        bf = ' '.join(f'{b:02x}' for b in df[off+i:off+i+16])
        bo = ' '.join(f'{b:02x}' for b in do[off+i:off+i+16])
        mark = '  <-- DIFF' if df[off+i:off+i+16] != do[off+i:off+i+16] else ''
        print(f'  +{i:04X}  F {bf}')
        print(f'        O {bo}{mark}')

# Candidate 1: dense bitmask 0x09953 (57 bytes = 456 bits, 454 personas)
dump(0x09953, 64, 'BITMASK candidate 0x09953 (mirror 0x21E63)')

# Candidate 2: u16 ID array 0x0324E (first 64 bytes)
dump(0x0324E, 64, 'U16-ID-ARRAY candidate 0x0324E (mirror 0x1B75E)')

# Also check the other mirror start 0x0398C (128B window hit)
dump(0x0398C, 64, 'WINDOW-128 candidate 0x0398C (mirror 0x1BE9C)')

# Decode bitmask: which persona IDs are set in fresh vs oracle at 0x09953
print('\n=== BITMASK decode @0x09953: persona IDs set ===')
def bits_at(base, path, label):
    d = payload(path)
    ids = []
    for pid in range(1, 0x1C6 + 1):
        byte = base + (pid - 1) // 8
        bit = (pid - 1) % 8
        if d[byte] & (1 << bit):
            ids.append(pid)
    return ids

fresh_ids = bits_at(0x09953, FRESH, 'fresh')
oracle_ids = bits_at(0x09953, ORACLE, 'oracle')
print(f'fresh: {len(fresh_ids)} ids set: {[hex(x) for x in fresh_ids[:20]]}...')
print(f'oracle: {len(oracle_ids)} ids set: {[hex(x) for x in oracle_ids[:20]]}...')
print(f'fresh subset of oracle: {set(fresh_ids) <= set(oracle_ids)}')
