"""
MARUKI EVENT FLAG ISOLATION — Mathematical Cross-Reference
Strategy: Find bits in the event flag region (0x2F200–0x30700) that 
CORRELATE with Maruki's confidant rank across all available saves.
"""
import sys, os
sys.path.insert(0, r'E:\ai-workspace\knowledge-base\projects\p5r-save-editor')
from core.editor import SaveEditor

saves = [
    ('Oracle DATA11', r'C:\Users\kufis\p5r_buff_save\DATA11\DATA.DAT'),
    ('Oracle DATA12', r'C:\Users\kufis\p5r_buff_save\DATA12\DATA.DAT'),
    ('Oracle DATA13', r'C:\Users\kufis\p5r_buff_save\DATA13\DATA.DAT'),
    ('Oracle DATA14', r'C:\Users\kufis\p5r_buff_save\DATA14\DATA.DAT'),
    ('Oracle DATA15', r'C:\Users\kufis\p5r_buff_save\DATA15\DATA.DAT'),
    ('Oracle DATA16', r'C:\Users\kufis\p5r_buff_save\DATA16\DATA.DAT'),
]

# Check all slots on user's machine
user_dir = r'C:\Users\kufis\AppData\Roaming\SEGA\P5R\Steam\76561197984149929\savedata'
if os.path.exists(user_dir):
    for entry in sorted(os.listdir(user_dir)):
        p = os.path.join(user_dir, entry, 'DATA.DAT')
        if os.path.exists(p):
            saves.append(('User ' + entry, p))

# Also check any backup files if present
backup_dir = r'E:\ai-workspace\knowledge-base\projects\p5r-save-editor\backups'
if os.path.exists(backup_dir):
    for entry in sorted(os.listdir(backup_dir)):
        if entry.endswith('.DAT') or entry.endswith('.dat'):
            p = os.path.join(backup_dir, entry)
            saves.append(('Backup ' + entry[:20], p))

MARUKI_ARCANA = 21  # Councillor

EVENT_START = 0x2F200
EVENT_END   = 0x30700
EVENT_SIZE  = EVENT_END - EVENT_START  # 5376 bytes = 43008 bits

print('=' * 72)
print('  MARUKI EVENT FLAG CROSS-REFERENCE ANALYSIS')
print('  Event flag region: 0x{:05X} - 0x{:05X} ({} bytes / {} bits)'.format(
    EVENT_START, EVENT_END, EVENT_SIZE, EVENT_SIZE * 8))
print('=' * 72)

save_data = []
for label, path in saves:
    if not os.path.exists(path):
        continue
    try:
        raw = open(path, 'rb').read()
        e = SaveEditor(raw)
        if not e.is_real_save():
            continue
        d = e.parser.data_payload
        if len(d) < EVENT_END:
            continue
        
        confidants = e.get_confidant_ranks()
        maruki_rank = 0
        maruki_pts = 0
        for name, info in confidants.items():
            if info.get('arcana_id') == MARUKI_ARCANA or 'Councillor' in name or 'Maruki' in name:
                maruki_rank = info.get('rank', 0)
                maruki_pts = info.get('points', 0)
                break
        
        qi = e.get_quick_info()
        day = qi.get('day', '?')
        hdr = e.parser.header
        
        flags = d[EVENT_START:EVENT_END]
        set_bits = sum(bin(b).count('1') for b in flags)
        
        save_data.append({
            'label': label,
            'path': path,
            'maruki_rank': maruki_rank,
            'maruki_pts': maruki_pts,
            'day': day,
            'hdr_day': getattr(hdr, 'day', None),
            'flags': flags,
            'set_bits': set_bits
        })
        
        print('  ' + label.ljust(24) + ' | Maruki Rank: ' + str(maruki_rank).rjust(2) + 
              ' (pts ' + str(maruki_pts).rjust(3) + ') | Day: ' + str(day).ljust(12) + 
              ' | Event bits set: ' + str(set_bits))
    except Exception as ex:
        print('  SKIP ' + label + ': ' + str(ex))

print()

# Group by Maruki rank
from collections import defaultdict
rank_groups = defaultdict(list)
for sd in save_data:
    rank_groups[sd['maruki_rank']].append(sd)

print('MARUKI RANK DISTRIBUTION:')
for rank in sorted(rank_groups.keys()):
    labels = [s['label'] for s in rank_groups[rank]]
    print('  Rank ' + str(rank) + ': ' + str(len(labels)) + ' saves — ' + ', '.join(labels))

print()

if len(rank_groups) < 2:
    print('*** NOT ENOUGH RANK DIVERSITY ***')
else:
    all_ranks = sorted(rank_groups.keys())
    print('=' * 72)
    print('  RANK-CORRELATED FLAG ISOLATION')
    print('=' * 72)
    
    # We want to test correlation for each rank threshold
    for threshold in all_ranks[1:]:
        above = [s for s in save_data if s['maruki_rank'] >= threshold]
        below = [s for s in save_data if s['maruki_rank'] < threshold]
        
        if not above or not below:
            continue
        
        candidate_bits = []
        for byte_idx in range(EVENT_SIZE):
            for bit_idx in range(8):
                all_set_above = all((s['flags'][byte_idx] >> bit_idx) & 1 for s in above)
                all_clear_below = all(not ((s['flags'][byte_idx] >> bit_idx) & 1) for s in below)
                
                if all_set_above and all_clear_below:
                    abs_offset = EVENT_START + byte_idx
                    bit_global = byte_idx * 8 + bit_idx
                    candidate_bits.append((abs_offset, bit_idx, bit_global, byte_idx))
        
        print(f'Threshold Maruki >= Rank {threshold} (Above: {len(above)}, Below: {len(below)}):')
        print(f'  Candidate bits strictly matching: {len(candidate_bits)}')
        if 0 < len(candidate_bits) <= 100:
            for off, bidx, bglobal, byte_idx in candidate_bits:
                print(f'    Offset 0x{off:05X} (relative +0x{byte_idx:04X}), Bit {bidx} (Global Bit #{bglobal})')
        elif len(candidate_bits) > 100:
            print(f'    First 10 candidates:')
            for off, bidx, bglobal, byte_idx in candidate_bits[:10]:
                print(f'      Offset 0x{off:05X} (rel +0x{byte_idx:04X}), Bit {bidx} (Global Bit #{bglobal})')
            print(f'    ... [{len(candidate_bits)-10} more]')
        print()
