#!/usr/bin/env python3
"""What IS at 0x20000 in the oracle vs a fresh mid-game save? + full Councillor/Sun check."""
import struct, sys
sys.path.insert(0, '.')
from core.editor import SaveEditor

ORACLE = r'C:\Users\kufis\p5r_buff_save\DATA11\DATA.DAT'
FRESH = r'C:\Users\kufis\AppData\Roaming\SEGA\P5R\Steam\76561197984149929\savedata\DATA01\DATA.DAT'

eo = SaveEditor(open(ORACLE, 'rb').read())
ef = SaveEditor(open(FRESH, 'rb').read())
do, df = eo.parser.data_payload, ef.parser.data_payload

# What does the 0x20000 region look like? Dump first 0x80 bytes of oracle.
print('=== ORACLE 0x20000 head (64B) ===')
row = do[0x20000:0x20040]
print(' '.join(f'{b:02x}' for b in row[:32]))
print(' '.join(f'{b:02x}' for b in row[32:]))

# Same region in fresh mid-game save
print('\n=== FRESH 6/15 0x20000 head (64B) ===')
rowf = df[0x20000:0x20040]
print(' '.join(f'{b:02x}' for b in rowf[:32]))
print(' '.join(f'{b:02x}' for b in rowf[32:]))

# Is 0x20000 region different between oracle and fresh? (event-flag-like?)
diffs = sum(1 for i in range(0x20000, 0x2E000) if do[i] != df[i])
print(f'\nbytes differing 0x20000-0x2E000: {diffs} / {0xE000}')

# Councillor + Sun + Judgement IDs at rank 10 in oracle (full confidant dump)
print('\n=== ORACLE FULL CONFIDANT DUMP (id, rank) ===')
conf_base = 0x136A0
for i in range(23):
    ent = do[conf_base + i*16 : conf_base + (i+1)*16]
    cid = struct.unpack_from('<H', ent, 6)[0]
    rank = struct.unpack_from('<H', ent, 8)[0]
    print(f'  slot {i:2}: id={cid:3} rank={rank:2}')
