#!/usr/bin/env python3
"""Decisive mathematical tests for the 0x09973 mask semantics.

Test 1: true persona stock (all 12 slots x 10 members) subset of mask.
Test 2: acquisition ring (0x3530) persona IDs subset of mask.
Test 3: NG+ cycle carry-over analysis from mask counts + playtime.
"""
import sys, struct
sys.path.insert(0, '.')
from core.editor import SaveEditor

BASE = 0x09973
N_BITS = 232
RING = 0x3530
RING_SLOTS = 30

SAVES = {
    'user DATA01 (6/15)': r'C:\Users\kufis\AppData\Roaming\SEGA\P5R\Steam\76561197984149929\savedata\DATA01\DATA.DAT',
    'user DATA02 (6/14)': r'C:\Users\kufis\AppData\Roaming\SEGA\P5R\Steam\76561197984149929\savedata\DATA02\DATA.DAT',
    'oracle DATA11 (2/3)': r'C:\Users\kufis\p5r_buff_save\DATA11\DATA.DAT',
    'oracle DATA12 (2/2)': r'C:\Users\kufis\p5r_buff_save\DATA12\DATA.DAT',
    'oracle DATA13 (1/31)': r'C:\Users\kufis\p5r_buff_save\DATA13\DATA.DAT',
    'oracle DATA14 (12/24)': r'C:\Users\kufis\p5r_buff_save\DATA14\DATA.DAT',
    'oracle DATA15 (12/24)': r'C:\Users\kufis\p5r_buff_save\DATA15\DATA.DAT',
    'oracle DATA16 (3/20)': r'C:\Users\kufis\p5r_buff_save\DATA16\DATA.DAT',
}

def mask_set(d):
    out = set()
    for i in range(N_BITS):
        if (d[BASE + i//8] >> (i%8)) & 1:
            out.add(i + 1)
    return out

def ring_ids(d):
    """Decode the acquisition ring at 0x3530: 30 x [u16 id][u16 flag]."""
    ids = []
    for i in range(RING_SLOTS):
        off = RING + i*4
        rid = struct.unpack_from('<H', d, off)[0]
        if rid:
            ids.append(rid)
    return ids

print('=== Test 1+2: stock/ring vs mask ===')
for label, path in SAVES.items():
    e = SaveEditor(open(path, 'rb').read())
    d = e.parser.data_payload
    m = mask_set(d)
    # TRUE full stock: all 12 slots x all members, raw offsets
    stock = set()
    for member in range(10):
        base = 0x2C + member * 0x2B0 + 0x38
        for slot in range(12):
            off = base + slot * 0x30
            pid = struct.unpack_from('<H', d, off + 2)[0] if len(d) >= off + 4 else 0
            flags = struct.unpack_from('<H', d, off)[0] if len(d) >= off + 2 else 0
            if pid and flags & 1:
                stock.add(pid)
    ring = [r for r in ring_ids(d) if r <= N_BITS]  # persona-range ring ids
    ring_set = set(ring)
    print(f'{label:22} mask={len(m):3} stock={len(stock):2} '
          f'stock⊆mask={stock <= m} ring⊆mask={ring_set <= m} '
          f'ring_in_mask={len(ring_set & m)}/{len(ring_set)}')
    if stock - m:
        print(f'   stock NOT in mask: {[hex(x) for x in sorted(stock-m)]}')
