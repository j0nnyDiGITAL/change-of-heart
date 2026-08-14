#!/usr/bin/env python3
"""Test the starter-persona counter-signal on the April saves.

Claim to test: mask @0x09973 == 0 on April saves, but the player owns
Arsene (0x0DC) from day 1. If TRUE, the mask is NOT compendium
registration (starters would have their bits set from the first save).
"""
import sys, os
sys.path.insert(0, '.')
from core.editor import SaveEditor

BASE = 0x09973
N = 232
SAVEDATA = r'C:\Users\kufis\AppData\Roaming\SEGA\P5R\Steam\76561197984149929\savedata'

def mask_ids(d):
    out = set()
    for i in range(N):
        byte = d[BASE + i//8]
        bit = i % 8
        if (byte >> bit) & 1:
            out.add(i + 1)
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

print('=== April saves: mask vs owned personas ===')
for slot in ('DATA03', 'DATA04', 'DATA05', 'DATA06'):
    p = os.path.join(SAVEDATA, slot, 'DATA.DAT')
    if not os.path.exists(p):
        continue
    e = SaveEditor(open(p, 'rb').read())
    d = e.parser.data_payload
    reg_ids = mask_ids(d)
    owned = owned_ids(e)
    has_arsene = 0x0DC in owned
    print(f'{slot}: mask={len(reg_ids):3}  owned={len(owned):2}  '
          f'arsene_owned={has_arsene}  arsene_IN_MASK={0x0DC in reg_ids}')

print('\n=== Also: what IS at 0x09973 in these saves? (first 8 bytes) ===')
for slot in ('DATA03', 'DATA06'):
    p = os.path.join(SAVEDATA, slot, 'DATA.DAT')
    e = SaveEditor(open(p, 'rb').read())
    d = e.parser.data_payload
    print(f'  {slot}: {" ".join(f"{b:02x}" for b in d[BASE:BASE+8])}')
