#!/usr/bin/env python3
"""List CPK TOC without extracting — find the event-script (.bf) paths."""
import struct, sys, os

CPK = r'J:\SteamLibrary\steamapps\common\P5R\CPK\BASE.CPK'

with open(CPK, 'rb') as f:
    head = f.read(0x800)
    # CRI CPK header: magic 'CPK ' at 0
    magic = head[0:4]
    print('magic:', magic)
    # TOC offset: u32 @ 0x10 (relative to 0x800 header area per spec), 
    # TOC size u32 @ 0x14; content offset @ 0x18, content size @ 0x1C
    toc_off, toc_size = struct.unpack_from('<II', head, 0x10)
    content_off, content_size = struct.unpack_from('<II', head, 0x18)
    print(f'TOC: off={toc_off} size={toc_size} | content off={content_off} size={content_size}')

    f.seek(toc_off)
    toc = f.read(min(toc_size, 0x400000))  # cap 4MB read
    print('toc head:', toc[:64].hex())

# The TOC is itself a mini-CPK with entries; parse first-level strings
# Try locating file path strings in the TOC bytes
paths = []
for marker in (b'.bf\x00', b'.flow\x00', b'event', b'script', b'field'):
    idx = 0
    while True:
        i = toc.find(marker, idx)
        if i == -1:
            break
        # extract surrounding printable string
        s = i
        while s > 0 and 32 <= toc[s-1] < 127:
            s -= 1
        e = i + len(marker)
        while e < len(toc) and 32 <= toc[e] < 127:
            e += 1
        p = toc[s:e].decode('ascii', errors='replace')
        if p not in paths:
            paths.append(p)
        idx = i + 1
print('\npaths found in TOC (first 40):')
for p in paths[:40]:
    print(' ', p)
print(f'total unique path strings: {len(paths)}')
