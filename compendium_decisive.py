#!/usr/bin/env python3
"""Decisive test: does the 0x17A94 mask exactly cover Personas.txt rows?

If oracle mask bit i = row i of Personas.txt (232 non-DLC personas),
this is the compendium registration. Check both indexings:
  A) bit index = persona ID - 1
  B) bit index = Personas.txt row order
"""
import sys
sys.path.insert(0, '.')
from core.editor import SaveEditor

FRESH = r'C:\Users\kufis\AppData\Roaming\SEGA\P5R\Steam\76561197984149929\savedata\DATA01\DATA.DAT'
MID = r'C:\Users\kufis\p5r_buff_save\DATA12\DATA.DAT'
ORACLE = r'C:\Users\kufis\p5r_buff_save\DATA11\DATA.DAT'

def payload(path):
    return SaveEditor(open(path, 'rb').read()).parser.data_payload

do = payload(ORACLE)
e = SaveEditor(open(ORACLE, 'rb').read())
table = e._load_table('Personas.txt')

# Personas.txt rows in ID order (table is id->name)
ids_in_table = sorted(table.keys())
print(f'Personas.txt: {len(ids_in_table)} ids, first={hex(ids_in_table[0])} last={hex(ids_in_table[-1])}')

# Mask bit states at 0x17A94
def mask_bit(pid):
    byte = 0x17A94 + (pid - 1) // 8
    bit = (pid - 1) % 8
    return bool(do[byte] & (1 << bit))

# A) bit index = persona ID - 1
set_by_id = [pid for pid in ids_in_table if mask_bit(pid)]
missing_by_id = [pid for pid in ids_in_table if not mask_bit(pid)]
print(f'\nA) ID-indexed: {len(set_by_id)}/{len(ids_in_table)} table ids set in oracle')
print(f'   missing table ids: {[hex(x) for x in missing_by_id[:30]]}')

# B) bit index = row order in Personas.txt (0..231)
rows = sorted(table.keys())  # assume ascending = file order
row_bits = [mask_bit(pid) for pid in rows]
print(f'\nB) row-indexed: {sum(row_bits)}/{len(rows)} set')
# are the unset rows contiguous at the end (DLC block)?
unset_rows = [i for i, b in enumerate(row_bits) if not b]
print(f'   unset row indices: {unset_rows[:40]}')
if unset_rows:
    print(f'   unset row span: {min(unset_rows)}..{max(unset_rows)} (contiguous: {unset_rows == list(range(min(unset_rows), max(unset_rows)+1))})')

# What are the set IDs per Personas.txt name for a few unset rows?
print('\n   sample unset personas (row, id, name):')
for i in unset_rows[:12]:
    print(f'   row {i}: 0x{rows[i]:03X} = {table[rows[i]]}')

# Fresh check: does fresh save have ANY mask bits? (editor-injected = 0)
df = payload(FRESH)
fresh_bits = sum(1 for pid in ids_in_table
                 if df[0x17A94 + (pid-1)//8] & (1 << ((pid-1) % 8)))
print(f'\nfresh save mask bits set: {fresh_bits} (0 = editor-injected personas never registered)')
