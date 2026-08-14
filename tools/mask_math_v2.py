#!/usr/bin/env python3
"""Corrected math: stock filtered to mask range (1..232) vs mask."""
import sys, struct
sys.path.insert(0, r'E:\ai-workspace\knowledge-base\projects\p5r-save-editor')

BASE = 0x09973
N_BITS = 232
RING = 0x3530
RING_SLOTS = 30

SAVES = {
    'oracle DATA11 (2/3)': r'C:\Users\kufis\p5r_buff_save\DATA11\DATA.DAT',
    'oracle DATA12 (2/2)': r'C:\Users\kufis\p5r_buff_save\DATA12\DATA.DAT',
    'oracle DATA13 (1/31)': r'C:\Users\kufis\p5r_buff_save\DATA13\DATA.DAT',
    'oracle DATA14 (12/24)': r'C:\Users\kufis\p5r_buff_save\DATA14\DATA.DAT',
    'oracle DATA15 (12/24)': r'C:\Users\kufis\p5r_buff_save\DATA15\DATA.DAT',
    'oracle DATA16 (3/20)': r'C:\Users\kufis\p5r_buff_save\DATA16\DATA.DAT',
    'user DATA01 (6/15)': r'C:\Users\kufis\AppData\Roaming\SEGA\P5R\Steam\76561197984149929\savedata\DATA01\DATA.DAT',
}

def mask_set(d):
    return {i+1 for i in range(N_BITS) if (d[BASE + i//8] >> (i%8)) & 1}

def true_stock(d):
    """Full 12-slot stock x 10 members, raw offsets (verified layout)."""
    stock = set()
    for member in range(10):
        base = 0x2C + member * 0x2B0 + 0x38
        for slot in range(12):
            off = base + slot * 0x30
            flags = struct.unpack_from('<H', d, off)[0] if len(d) >= off+2 else 0
            pid = struct.unpack_from('<H', d, off + 2)[0] if len(d) >= off+4 else 0
            if pid and flags & 1:
                stock.add(pid)
    return stock

def ring_ids(d):
    return [struct.unpack_from('<H', d, RING + i*4)[0] for i in range(RING_SLOTS) if struct.unpack_from('<H', d, RING + i*4)[0]]

print('=== Corrected: stock intersect [1..232] subset of mask? ===')
all_ok = True
for label, path in SAVES.items():
    from core.editor import SaveEditor
    e = SaveEditor(open(path, 'rb').read())
    d = e.parser.data_payload
    m = mask_set(d)
    stock = true_stock(d)
    stock_in_range = {p for p in stock if 1 <= p <= N_BITS}
    ring = [r for r in ring_ids(d) if 1 <= r <= N_BITS]
    ok = stock_in_range <= m
    all_ok &= ok
    print(f'{label:22} mask={len(m):3} stock<=232={len(stock_in_range):2} '
          f'subset_of_mask={ok} ring_ids={[hex(r) for r in ring]}')
    if stock_in_range - m:
        print(f'   FAIL: {[hex(x) for x in sorted(stock_in_range - m)]}')
print(f'\nALL SAVES PASS stock intersect mask: {all_ok}')
