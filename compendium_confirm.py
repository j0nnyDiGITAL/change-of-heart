#!/usr/bin/env python3
"""Zero-gameplay compendium confirmation at corrected alignment 0x09973.

Check 1: owned-stock ⊆ mask on ALL legit oracle saves (DATA11-16).
Check 2: full 7-save ladder monotonicity (DATA01 + DATA11-16).
Check 3: bit-position -> Personas.txt row mapping (set bits = obtainable).
"""
import sys, struct
sys.path.insert(0, '.')
from core.editor import SaveEditor

BASE = 0x09973
MASK_BITS = 232

SAVES = {
    'fresh DATA01': r'C:\Users\kufis\AppData\Roaming\SEGA\P5R\Steam\76561197984149929\savedata\DATA01\DATA.DAT',
    'DATA11': r'C:\Users\kufis\p5r_buff_save\DATA11\DATA.DAT',
    'DATA12': r'C:\Users\kufis\p5r_buff_save\DATA12\DATA.DAT',
    'DATA13': r'C:\Users\kufis\p5r_buff_save\DATA13\DATA.DAT',
    'DATA14': r'C:\Users\kufis\p5r_buff_save\DATA14\DATA.DAT',
    'DATA15': r'C:\Users\kufis\p5r_buff_save\DATA15\DATA.DAT',
    'DATA16': r'C:\Users\kufis\p5r_buff_save\DATA16\DATA.DAT',
}

def mask_ids(d, base=BASE, nbits=MASK_BITS, msb=False):
    out = set()
    for i in range(nbits):
        byte = base + i // 8
        bit = i % 8
        if msb:
            bit = 7 - bit
        if byte < len(d) and (d[byte] >> bit) & 1:
            out.add(i + 1)  # 1-based bit position
    return out

def owned_ids(e):
    owned = set()
    for entry in e.get_party_stats():
        slot = entry['slot']
        for s in e.get_persona_stock(slot):
            pid = s.get('id')
            if pid and pid != 0:
                owned.add(pid)
        eq = e.get_equipped_persona(slot)
        if eq.get('persona_id'):
            owned.add(eq['persona_id'])
    return owned

# ---- Check 1 + 2: load all saves, compute masks + owned + date ----------
print('=== Check 1+2: mask popcount, owned-subset, ladder ===')
rows = []
for label, path in SAVES.items():
    e = SaveEditor(open(path, 'rb').read())
    d = e.parser.data_payload
    qi = e.get_quick_info()
    day = qi.get('day', '?')
    mask = mask_ids(d)
    owned = owned_ids(e)
    subset = owned <= mask
    rows.append((day, label, len(mask), len(owned), subset, mask, owned))
    print(f'  {label:12} day={day:24} mask={len(mask):3} owned={len(owned):3} owned⊆mask={subset}')

# ladder monotonicity by day order
rows.sort(key=lambda r: r[0])
print('\n=== Check 2: ladder monotonicity (sorted by in-game day) ===')
prev = None
ok = True
for day, label, mcnt, ocnt, subset, mask, owned in rows:
    if prev is not None and not (prev <= mask):
        ok = False
        print(f'  BREAK: {label} mask is NOT a superset of previous')
    prev = mask
print(f'  ladder monotone: {ok}')

# ---- Check 3: bit position -> Personas.txt row mapping ------------------
print('\n=== Check 3: persona-ID mapping for the 218-bit oracle mask ===')
e = SaveEditor(open(SAVES['DATA11'], 'rb').read())
table = e._load_table('Personas.txt')  # id -> name
oracle_mask = mask_ids(e.parser.data_payload)

# Hypothesis A: bit position i (1-based) == persona id i
id_hits = sum(1 for i in oracle_mask if i in table)
print(f'  A) bit pos == persona id: {id_hits}/{len(oracle_mask)} set bits are valid persona IDs')

# Hypothesis B: bit position == row index into Personas.txt (id-sorted)
ids_sorted = sorted(table.keys())
row_of_id = {pid: idx for idx, pid in enumerate(ids_sorted)}
# map mask positions to persona ids via row index
mapped = {ids_sorted[i-1] for i in oracle_mask if i-1 < len(ids_sorted)}
print(f'  B) bit pos == table row: {len(mapped)} distinct personas mapped')
print(f'  B) mapped ⊆ table: {mapped <= set(ids_sorted)}')

# show unset positions in oracle (the ~14 missing) -> what personas?
unset = set(range(1, 233)) - oracle_mask
unset_names = []
for i in sorted(unset):
    if i in table:
        unset_names.append(f'{table[i]}(0x{i:03X})')
    elif i-1 < len(ids_sorted):
        unset_names.append(f'{table[ids_sorted[i-1]]}(row{i})')
print(f'  unset bits ({len(unset)}): {unset_names[:20]}')
