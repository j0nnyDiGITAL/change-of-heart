#!/usr/bin/env python3
"""Decode confidant block + day counter in both saves for the Maruki probe check."""
import struct, sys
sys.path.insert(0, '.')
from core.editor import SaveEditor

BASE = r'diff/pre_maruki_20260813.DAT'
CURR = r'C:/Users/kufis/AppData/Roaming/SEGA/P5R/Steam/76561197984149929/savedata/DATA01/DATA.DAT'

def decode(path, label):
    e = SaveEditor(open(path, 'rb').read())
    d = e.parser.data_payload
    # day counter @0x3D70 (u8), money @0x35C0 (u32)
    day = struct.unpack_from('<H', d, 0x3D70)[0]
    money = struct.unpack_from('<I', d, 0x35C0)[0]
    print(f"=== {label}: day(u16@3D70)={day}  money={money} ===")
    # confidant block @0x136A0, 23 x 16B entries: [6 pad][u16 id @+6][u16 rank @+8][u16 pts @+10][4 pad]
    base = 0x136A0
    for i in range(23):
        ent = d[base + i*16 : base + (i+1)*16]
        cid = struct.unpack_from('<H', ent, 6)[0]
        rank = struct.unpack_from('<H', ent, 8)[0]
        pts = struct.unpack_from('<H', ent, 10)[0]
        if cid != 0 or rank != 0:
            print(f"  [{i:2}] id={cid:3} rank={rank:2} pts={pts:3}")

decode(BASE, 'BASELINE pre_maruki')
print()
decode(CURR, 'CURRENT DATA.DAT')
