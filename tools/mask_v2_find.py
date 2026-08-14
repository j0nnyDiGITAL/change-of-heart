#!/usr/bin/env python3
"""Find the SECOND persona mask (upper IDs 233-463) + identify 0xD8/0xDA."""
import sys, struct
sys.path.insert(0, r'E:\ai-workspace\knowledge-base\projects\p5r-save-editor')

from core.editor import SaveEditor

ORACLE = r'C:\Users\kufis\p5r_buff_save\DATA11\DATA.DAT'
FRESH = r'C:\Users\kufis\AppData\Roaming\SEGA\P5R\Steam\76561197984149929\savedata\DATA01\DATA.DAT'

e = SaveEditor(open(ORACLE, 'rb').read())
d = e.parser.data_payload
table = e._load_table('Personas.txt')

print('=== 0xD8 / 0xDA identity ===')
for pid in (0xD8, 0xDA, 0xDC, 0xDD, 0xDE, 0xE0):
    print(f'  0x{pid:03X} = {table.get(pid, "?")}')

print('\n=== Scan for a second monotone bitmask (232 bits) elsewhere ===')
N = len(d)
cands = []
for off in range(0x0, N - 29, 1):
    # quick prefilter: nonzero in oracle at this window
    if not any(d[off:off+29]):
        continue
    # monotone vs fresh
    mono = True
    for i in range(29):
        if ((d[off+i] | d[off+i]) != d[off+i]) or (d[off+i] & ~d[off+i]):
            pass
        if d[off+i] & ~d[off+i]:  # impossible; placeholder
            mono = False
    po = sum(bin(b).count('1') for b in d[off:off+29])
    if po >= 30:
        cands.append((po, off))
cands.sort(reverse=True)
print('top 15 dense 29-byte windows (oracle):')
for po, off in cands[:15]:
    print(f'  pop={po:3} @ 0x{off:05X}')

# Where does the first mask end? Check bytes right after 0x09973+29
print('\n=== bytes after first mask (0x09973+29 = 0x09990) ===')
print(' '.join(f'{b:02x}' for b in d[0x09973+29 : 0x09973+29+64]))
