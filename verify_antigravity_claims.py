#!/usr/bin/env python3
"""Verify Antigravity's compendium + Councillor-ID claims against the oracle save.

Oracle = 100% NG++ save (all 232 personas registered, all confidants rank 10).
Claim 1: compendium @0x20000, 896 slots x 64B, [u16 flags][u16 pid][u16 lvl]...
Claim 2: Councillor save_id flips 35 -> 20 at rank 10.
"""
import struct, sys
sys.path.insert(0, '.')
from core.editor import SaveEditor

ORACLE = r'C:\Users\kufis\p5r_buff_save\DATA11\DATA.DAT'

e = SaveEditor(open(ORACLE, 'rb').read())
d = e.parser.data_payload
print('payload len:', hex(len(d)))
print('is_pc_0x31:', e.is_real_save())

# ---- Claim 1: compendium @0x20000 ----
base = 0x20000
slots = 896
stride = 64
print('\n=== COMPENDIUM CLAIM @0x20000 ===')
registered = 0
valid_pid = 0
nonzero = 0
sample_pids = []
for i in range(slots):
    off = base + i * stride
    if off + stride > len(d):
        break
    flags = struct.unpack_from('<H', d, off)[0]
    pid = struct.unpack_from('<H', d, off + 2)[0]
    lvl = struct.unpack_from('<H', d, off + 4)[0]
    if flags & 0x0001:
        registered += 1
    if pid != 0:
        valid_pid += 1
        if len(sample_pids) < 12:
            sample_pids.append((i, hex(pid), lvl, hex(flags)))
    if any(d[off:off+stride]):
        nonzero += 1

print(f'slots scanned: {slots}, registered(flag1): {registered}, nonzero pid: {valid_pid}, nonzero slots: {nonzero}')
print('sample (slot, pid, lvl, flags):', sample_pids)

# ---- Claim 2: Councillor id flip at rank 10 ----
print('\n=== COUNCILLOR ID CLAIM ===')
conf_base = 0x136A0
for i in range(23):
    ent = d[conf_base + i*16 : conf_base + (i+1)*16]
    cid = struct.unpack_from('<H', ent, 6)[0]
    rank = struct.unpack_from('<H', ent, 8)[0]
    if cid in (35, 20) or rank == 10:
        print(f'[slot {i}] id={cid} rank={rank} pts={struct.unpack_from("<H", ent, 10)[0]}')
