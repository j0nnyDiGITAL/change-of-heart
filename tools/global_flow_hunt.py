#!/usr/bin/env python3
"""Global FLW0 hunt: scan every CPK file for CRILAYLA -> FLW0 flowscripts."""
import sys, os, subprocess
sys.path.insert(0, '.')
from cpk_extract_files import get_toc
from cri_layla import decompress

OUT = r'E:\ai-workspace\knowledge-base\projects\p5r-save-editor\tools\cpk_out'
ASC = r'E:\ai-workspace\knowledge-base\projects\p5r-save-editor\tools\Atlus-Script-Tools-Bin\AtlusScriptCompiler.exe'
CPK = r'J:\SteamLibrary\steamapps\common\P5R\CPK\BASE.CPK'
DEC = os.path.join(OUT, 'decompiled')
os.makedirs(DEC, exist_ok=True)

files = get_toc()
print(f'TOC total: {len(files)}')

# Phase 1: find CRILAYLA-compressed files (fast magic check)
candidates = []
with open(CPK, 'rb') as src:
    for i, f in enumerate(files):
        if i % 5000 == 0:
            print(f'  magic-scan {i}/{len(files)}...')
        src.seek(f['off'])
        magic = src.read(8)
        if magic == b'CRILAYLA':
            candidates.append(f)

print(f'CRILAYLA files: {len(candidates)}')

# Phase 2: decompress and check for FLW0
flow_files = []
for i, f in enumerate(candidates):
    if i % 500 == 0:
        print(f'  decompress {i}/{len(candidates)}...')
    with open(CPK, 'rb') as src:
        src.seek(f['off'])
        data = src.read(f['size'])
    try:
        out = decompress(data)
    except Exception:
        continue
    if b'FLW0' in out[:32]:
        flow_files.append((f, out))

print(f'\nFLW0 flowscripts found: {len(flow_files)}')
with open(os.path.join(OUT, 'flowscripts.txt'), 'w') as lst:
    for f, out in flow_files:
        lst.write(f"{f['path']}\t{len(out)}\n")
        print(f"  {f['path']} ({len(out)}B)")
