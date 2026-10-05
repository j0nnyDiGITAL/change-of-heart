# -*- mode: python ; coding: utf-8 -*-
import os
from pathlib import Path

block_cipher = None

SPEC_DIR = Path(SPECPATH).resolve()

# Complete list of data files - automatically include the whole data directory
data_files = [
    ('data', 'data'),
    ('web-app/templates', 'web-app/templates'),
    ('web-app/static', 'web-app/static'),
]

import site
import sys

user_site = site.getusersitepackages()
search_paths = [str(SPEC_DIR)]
if os.path.exists(user_site):
    search_paths.append(user_site)
for p in sys.path:
    if p and os.path.exists(p) and p not in search_paths:
        search_paths.append(p)

a = Analysis(
    ['main.py'],
    pathex=search_paths,
    binaries=[],
    datas=data_files,
    hiddenimports=[
        'webview',
        'webview.platforms.edgechromium',
        'server',
        'core',
        'core.crypto',
        'core.parser',
        'core.editor',
        'core.consumable_offsets',
        'core.environment',
        'core.instances',
        'http.server',
        'urllib.parse',
        'json',
        'base64',
        'socket',
        'threading',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='P5R_Save_Editor',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
