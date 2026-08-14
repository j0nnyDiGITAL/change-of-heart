#!/usr/bin/env python3
"""Bit-aligned 29-byte window scan (DeepSeek Q6, 2026-08-14).

Slide a 232-bit window over the payload at EVERY bit offset (not just byte
offsets), test LSB-first and MSB-first, score by:
  - oracle popcount as close to 232 as possible
  - mid > fresh, fresh low (monotone registration)
  - set bits must be a SUBSET relationship across the ladder
"""
import sys
sys.path.insert(0, '.')
from core.editor import SaveEditor

FRESH = r'C:\Users\kufis\AppData\Roaming\SEGA\P5R\Steam\76561197984149929\savedata\DATA01\DATA.DAT'
MID = r'C:\Users\kufis\p5r_buff_save\DATA12\DATA.DAT'
ORACLE = r'C:\Users\kufis\p5r_buff_save\DATA11\DATA.DAT'

def payload(path):
    return SaveEditor(open(path, 'rb').read()).parser.data_payload

df, dm, do = payload(FRESH), payload(MID), payload(ORACLE)
N = min(len(df), len(dm), len(do))

def bit_sequence(d, start_byte, start_bit, count, msb_first):
    """Extract `count` bits starting at (start_byte, start_bit)."""
    out = []
    idx = start_byte * 8 + start_bit
    total_bits = len(d) * 8
    for i in range(count):
        bi = idx + i
        if bi >= total_bits:
            break
        byte = bi // 8
        bit = bi % 8
        if msb_first:
            bit = 7 - bit
        out.append((d[byte] >> bit) & 1)
    return out

# Known blocks to mask: header region + event flags
KNOWN = [(0x0000, 0x4000), (0x2F200, 0x30700)]

def masked(byte_off, span):
    for s, e in KNOWN:
        if byte_off < e and byte_off + span > s:
            return True
    return False

results = []
for msb in (False, True):
    for byte_off in range(0, N - 30):
        if masked(byte_off, 30):
            continue
        for bit_off in range(8):
            pf = sum(bit_sequence(df, byte_off, bit_off, 232, msb))
            pm = sum(bit_sequence(dm, byte_off, bit_off, 232, msb))
            po = sum(bit_sequence(do, byte_off, bit_off, 232, msb))
            if po < 150 or pf > 50:
                continue
            # monotone: fresh ⊆ mid ⊆ oracle (bit-wise)
            f_seq = bit_sequence(df, byte_off, bit_off, 232, msb)
            m_seq = bit_sequence(dm, byte_off, bit_off, 232, msb)
            o_seq = bit_sequence(do, byte_off, bit_off, 232, msb)
            mono = all(not (f_seq[i] and not m_seq[i]) for i in range(232)) and \
                   all(not (m_seq[i] and not o_seq[i]) for i in range(232))
            if not mono:
                continue
            # score: closeness to 232 oracle popcount + ladder growth
            score = -abs(po - 232) + min(pm - pf, 0) * 0.01
            results.append((score, po, pm, pf, byte_off, bit_off, msb))

results.sort(reverse=True)
print('=== Top 12 bit-aligned 232-bit windows ===')
print('(score, oracle_pop, mid_pop, fresh_pop, byte_off, bit_off, msb_first)')
for r in results[:12]:
    print(f'  score={r[0]:.2f}  O={r[1]} M={r[2]} F={r[3]}  @ byte 0x{r[4]:05X} bit {r[5]} msb={r[6]}')
