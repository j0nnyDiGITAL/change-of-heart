#!/usr/bin/env python3
"""Test row-order indexing: bit i = i-th row in Personas.txt, not persona ID."""
import sys
sys.path.insert(0, '.')
from core.editor import SaveEditor

FRESH = r'C:\Users\kufis\AppData\Roaming\SEGA\P5R\Steam\76561197984149929\savedata\DATA01\DATA.DAT'

e = SaveEditor(open(FRESH, 'rb').read())
d = e.parser.data_payload

# Load Personas.txt: row index -> persona ID
table = e._load_table('Personas.txt')  # {id: name}
ids_by_row = []
for pid in range(0, 0x1C6 + 1):
    if pid in table:
        ids_by_row.append(pid)
print(f'Personas.txt rows: {len(ids_by_row)}')

# Owned personas from stock
party = e.get_party_stats()
owned = set()
for entry in party:
    slot = entry['slot']
    for s in e.get_persona_stock(slot):
        pid = s.get('id')
        if pid and pid not in (0, None):
            owned.add(pid)
    eq = e.get_equipped_persona(slot)
    if eq.get('persona_id'):
        owned.add(eq['persona_id'])
print(f'owned ids: {sorted(owned)}')

# Hypothesis A: bit index = persona ID (tested, failed)
# Hypothesis B: bit index = row index in Personas.txt
# Hypothesis C: bit index = ID - 1 but bit order reversed / different base

# Build row-index map
row_of_id = {pid: i for i, pid in enumerate(ids_by_row)}

for base_name, base in [('0x09953', 0x09953), ('0x21E63 (mirror)', 0x21E63), ('0x09950', 0x09950), ('0x09954', 0x09954)]:
    mask_ids = set()
    for pid in owned:
        # try row index
        if pid in row_of_id:
            ri = row_of_id[pid]
            byte = base + ri // 8
            bit = ri % 8
            if byte < len(d) and (d[byte] & (1 << bit)):
                mask_ids.add(pid)
    print(f'{base_name}: owned personas set under ROW indexing: {sorted(mask_ids)} ({len(mask_ids)}/{len(owned)})')

# Also dump raw bytes around each owned persona's row position to eyeball
print('\n-- raw bytes at row positions for owned ids (base 0x09953) --')
for pid in sorted(owned):
    if pid in row_of_id:
        ri = row_of_id[pid]
        byte = 0x09953 + ri // 8
        bit = ri % 8
        val = d[byte]
        print(f'  id 0x{pid:03X} row {ri:3} byte 0x{byte:05X} = 0x{val:02X} bit{bit}={ (val>>bit)&1 }')
