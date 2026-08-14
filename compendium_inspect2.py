#!/usr/bin/env python3
"""Inspect the two hot leads: 0x1B750 record array + 0x17A94 bitmask."""
import sys, struct
sys.path.insert(0, '.')
from core.editor import SaveEditor

FRESH = r'C:\Users\kufis\AppData\Roaming\SEGA\P5R\Steam\76561197984149929\savedata\DATA01\DATA.DAT'
MID = r'C:\Users\kufis\p5r_buff_save\DATA12\DATA.DAT'
ORACLE = r'C:\Users\kufis\p5r_buff_save\DATA11\DATA.DAT'

def payload(path):
    return SaveEditor(open(path, 'rb').read()).parser.data_payload

df, dm, do = payload(FRESH), payload(MID), payload(ORACLE)

print('=== 0x1B750 region: fresh vs oracle (first 128B) ===')
for i in range(0, 128, 16):
    bf = ' '.join(f'{b:02x}' for b in df[0x1B750+i:0x1B750+i+16])
    bo = ' '.join(f'{b:02x}' for b in do[0x1B750+i:0x1B750+i+16])
    mark = '  <-- DIFF' if df[0x1B750+i:0x1B750+i+16] != do[0x1B750+i:0x1B750+i+16] else ''
    print(f'  +{i:04X}  F {bf}')
    print(f'        O {bo}{mark}')

print('\n=== 0x1B750 as u16 persona-ID array (fresh) ===')
ids_f = []
for i in range(0, 0x100, 2):
    v = struct.unpack_from('<H', df, 0x1B750 + i)[0]
    if v:
        ids_f.append((i, hex(v)))
print(f'nonzero u16s in fresh: {len(ids_f)}')
for pos, v in ids_f[:30]:
    print(f'  +{pos:04X} = {v}')

print('\n=== 0x17A94 bitmask: which persona IDs set (oracle)? ===')
def bits_at(base, d, nbytes):
    out = []
    for pid in range(1, 0x1C6 + 1):
        byte = base + (pid - 1) // 8
        bit = (pid - 1) % 8
        if byte < base + nbytes and (d[byte] & (1 << bit)):
            out.append(pid)
    return out

for lbl, base in [('0x17A94', 0x17A94)]:
    o_ids = bits_at(base, do, 32)
    m_ids = bits_at(base, dm, 32)
    f_ids = bits_at(base, df, 32)
    print(f'{lbl}: oracle={len(o_ids)} mid={len(m_ids)} fresh={len(f_ids)}')
    print(f'  oracle first 20: {[hex(x) for x in o_ids[:20]]}')
    print(f'  oracle last 10: {[hex(x) for x in o_ids[-10:]]}')
    print(f'  fresh ids: {[hex(x) for x in f_ids[:15]]}')

# What are the contiguous set ranges in oracle at 0x17A94?
print('\n=== contiguous set-bit ranges at 0x17A94 (oracle) ===')
ranges = []
start = None
prev = None
for pid in range(1, 0x1C6 + 1):
    byte = 0x17A94 + (pid - 1) // 8
    bit = (pid - 1) % 8
    if do[byte] & (1 << bit):
        if start is None:
            start = pid
        prev = pid
    else:
        if start is not None:
            ranges.append((start, prev))
            start = None
if start is not None:
    ranges.append((start, prev))
print(f'{len(ranges)} ranges; first 8: {[(hex(a), hex(b)) for a, b in ranges[:8]]}')
print(f'range sizes: {[b - a + 1 for a, b in ranges]}')
