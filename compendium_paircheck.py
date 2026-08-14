#!/usr/bin/env python3
"""Bit-level monotonicity on the two clean same-playthrough pairs."""
import sys
sys.path.insert(0, '.')
from core.editor import SaveEditor

BASE = 0x09973
N = 232

def payload(path):
    return SaveEditor(open(path, 'rb').read()).parser.data_payload

def mask_bits(d):
    return [ (d[BASE + i//8] >> (i%8)) & 1 for i in range(N) ]

pairs = [
    ('user 6/14->6/15', r'C:\Users\kufis\AppData\Roaming\SEGA\P5R\Steam\76561197984149929\savedata\DATA02\DATA.DAT',
                        r'C:\Users\kufis\AppData\Roaming\SEGA\P5R\Steam\76561197984149929\savedata\DATA01\DATA.DAT'),
    ('oracle 2/2->2/3', r'C:\Users\kufis\p5r_buff_save\DATA12\DATA.DAT',
                        r'C:\Users\kufis\p5r_buff_save\DATA11\DATA.DAT'),
]

for label, p1, p2 in pairs:
    b1 = mask_bits(payload(p1))
    b2 = mask_bits(payload(p2))
    turned_on = sum(1 for i in range(N) if b1[i] == 0 and b2[i] == 1)
    turned_off = sum(1 for i in range(N) if b1[i] == 1 and b2[i] == 0)
    print(f'{label}: bits_on={sum(b1)} -> {sum(b2)} | turned_on={turned_on} turned_off={turned_off}')
    if turned_on:
        new_ids = [i+1 for i in range(N) if b1[i] == 0 and b2[i] == 1]
        print(f'   new persona bits: {[hex(x) for x in new_ids]}')

# April saves: check mask == 0 exactly
print()
for d in ['DATA03', 'DATA04', 'DATA05', 'DATA06']:
    p = rf'C:\Users\kufis\AppData\Roaming\SEGA\P5R\Steam\76561197984149929\savedata\{d}\DATA.DAT'
    b = mask_bits(payload(p))
    print(f'{d}: bits={sum(b)}')
