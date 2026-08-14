#!/usr/bin/env python3
"""Cross-check compendium bitmask @0x09953 against verified persona stock.

The fresh save's OWNED personas are in the party member stock arrays
(member+0x38, stride 0x30, slot 0 = equipped). If the bitmask's set bits
match the owned persona IDs exactly, the bitmask is confirmed as the
compendium registration — no gameplay needed.
"""
import sys
sys.path.insert(0, '.')
from core.editor import SaveEditor

FRESH = r'C:\Users\kufis\AppData\Roaming\SEGA\P5R\Steam\76561197984149929\savedata\DATA01\DATA.DAT'

e = SaveEditor(open(FRESH, 'rb').read())
d = e.parser.data_payload
print('is_pc:', e.is_real_save())

# 1. Bitmask set bits at 0x09953
base = 0x09953
mask_ids = set()
for pid in range(1, 0x1C6 + 1):
    byte = base + (pid - 1) // 8
    bit = (pid - 1) % 8
    if d[byte] & (1 << bit):
        mask_ids.add(pid)

# 2. Owned personas from party stock (10 members, 12 slots each)
party = e.get_party_stats()
owned = set()
for entry in party:
    slot = entry['slot']
    stock = e.get_persona_stock(slot)
    for s in stock:
        pid = s.get('id')
        if pid and pid not in (0, None):
            owned.add(pid)
    # also equipped persona
    eq = e.get_equipped_persona(slot)
    if eq.get('persona_id'):
        owned.add(eq['persona_id'])

print(f'bitmask ids: {len(mask_ids)}')
print(f'stock owned ids: {len(owned)}')
print(f'owned subset of bitmask: {owned <= mask_ids}')
print(f'bitmask NOT owned (should be personas seen/fused but released): {len(mask_ids - owned)}')
print(f'owned NOT in bitmask (should be 0): {sorted(owned - mask_ids)}')

# show a few owned ids and their bitmask status
for pid in sorted(owned)[:15]:
    print(f'  persona 0x{pid:03X} in_bitmask={pid in mask_ids}')
