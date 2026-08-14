#!/usr/bin/env python3
"""Batch: extract all SCRIPT/*.BF + EVENT dirs, decompress, decompile, grep BIT_ON."""
import sys, os, subprocess, glob
sys.path.insert(0, '.')
from cpk_extract_files import get_toc
from cri_layla import decompress

OUT = r'E:\ai-workspace\knowledge-base\projects\p5r-save-editor\tools\cpk_out'
ASC = r'E:\ai-workspace\knowledge-base\projects\p5r-save-editor\tools\Atlus-Script-Tools-Bin\AtlusScriptCompiler.exe'
CPK = r'J:\SteamLibrary\steamapps\common\P5R\CPK\BASE.CPK'

files = get_toc()
os.makedirs(OUT, exist_ok=True)

# Target: all .BF under SCRIPT/ (field scripts) + EVENT_DATA/SCRIPT
targets = [f for f in files if f['path'].startswith('SCRIPT/') and f['path'].endswith('.BF')]
print(f'targeting {len(targets)} SCRIPT .BF files')

decompiled_dir = os.path.join(OUT, 'decompiled')
os.makedirs(decompiled_dir, exist_ok=True)

count = 0
bit_hits = []
with open(CPK, 'rb') as src:
    for f in targets:
        src.seek(f['off'])
        data = src.read(f['size'])
        out = decompress(data)
        if out[:8] != b'CRILAYLA' and b'FLW0' not in out[:16]:
            continue  # not a flowscript
        base = os.path.basename(f['path'])
        raw_path = os.path.join(decompiled_dir, base + '.raw')
        open(raw_path, 'wb').write(out)
        flow_path = os.path.join(decompiled_dir, base + '.flow')
        r = subprocess.run(
            [ASC, '-Decompile', '-InFormat', 'FlowScriptBinary', '-Library', 'P5R',
             '-Encoding', 'P5', '-OutFormat', 'V3', '-In', raw_path, '-Out', flow_path],
            capture_output=True, text=True, timeout=60,
        )
        count += 1
        if os.path.exists(flow_path):
            text = open(flow_path, encoding='utf-8', errors='replace').read()
            if 'BIT_ON' in text or 'BIT_OFF' in text:
                bit_hits.append((f['path'], len(text)))
                print(f'  BIT HIT: {f["path"]}')
            else:
                pass
        if count % 10 == 0:
            print(f'  ...{count}/{len(targets)}')

print(f'\ndone: {count} processed, {len(bit_hits)} with BIT_ON/BIT_OFF')
for p, n in bit_hits:
    print(f'  {p} ({n} chars)')
