#!/usr/bin/env python3
"""Find same-playthrough save pairs via playtime/day/money progression."""
import sys
sys.path.insert(0, '.')
from core.editor import SaveEditor

BASE = 0x09973
MASK_BITS = 232

SLOTS = {
    'user DATA01': r'C:\Users\kufis\AppData\Roaming\SEGA\P5R\Steam\76561197984149929\savedata\DATA01\DATA.DAT',
}
import glob, os
savedata = r'C:\Users\kufis\AppData\Roaming\SEGA\P5R\Steam\76561197984149929\savedata'
for d in sorted(glob.glob(os.path.join(savedata, 'DATA*'))):
    slot = os.path.basename(d)
    if slot.startswith('DATA'):
        f = os.path.join(d, 'DATA.DAT')
        if os.path.exists(f):
            SLOTS[f'user {slot}'] = f

ORACLE_DIR = r'C:\Users\kufis\p5r_buff_save'
for d in sorted(glob.glob(os.path.join(ORACLE_DIR, 'DATA*'))):
    slot = os.path.basename(d)
    f = os.path.join(d, 'DATA.DAT')
    if os.path.exists(f):
        SLOTS[f'oracle {slot}'] = f

def mask_ids(d, base=BASE, nbits=MASK_BITS):
    out = set()
    for i in range(nbits):
        byte = base + i // 8
        bit = i % 8
        if byte < len(d) and (d[byte] >> bit) & 1:
            out.add(i + 1)
    return out

rows = []
for label, path in SLOTS.items():
    try:
        e = SaveEditor(open(path, 'rb').read())
        d = e.parser.data_payload
        qi = e.get_quick_info()
        hdr = e.parser.header
        money = e.get_money()
        play_sec = qi.get('playtime') or hdr.playtime or 0
        rows.append({
            'label': label, 'day': qi.get('day', '?'),
            'money': money,
            'play_h': play_sec // 3600 if play_sec else 0,
            'play_m': (play_sec % 3600) // 60 if play_sec else 0,
            'level': qi.get('level', '?'),
            'mask': len(mask_ids(d)),
        })
    except Exception as ex:
        print(f'{label}: ERROR {ex}')

print(f'\n{"slot":16} {"day":28} {"money":>10} {"play":>8} {"lvl":>4} {"mask":>5}')
for r in sorted(rows, key=lambda x: (x['play_h'], x['play_m'])):
    print(f"{r['label']:16} {r['day']:28} {r['money']:>10,} {r['play_h']}h{r['play_m']:02d}m {r['level']:>4} {r['mask']:>5}")

print('\n=== Same-playthrough candidates (playtime increases, day advances) ===')
for r in rows:
    print(f"  {r['label']}: day={r['day']} play={r['play_h']}h{r['play_m']:02d}m money={r['money']:,} lvl={r['level']}")
