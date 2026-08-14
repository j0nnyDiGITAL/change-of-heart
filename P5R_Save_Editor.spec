# -*- mode: python ; coding: utf-8 -*-
import os
from pathlib import Path

block_cipher = None

# Base directory
SPEC_DIR = Path(SPECPATH).resolve()

# Complete list of data files
data_files = [
    ('data/Accessories.txt', 'data'),
    ('data/Clothes.txt', 'data'),
    ('data/Compendium.txt', 'data'),
    ('data/Items.txt', 'data'),
    ('data/Keyitems&essentials.txt', 'data'),
    ('data/Personas.txt', 'data'),
    ('data/Royal_ConsumableItemNames.txt', 'data'),
    ('data/Royal_KeyItemNames.txt', 'data'),
    ('data/Skill Cards.txt', 'data'),
    ('data/Skill ID.txt', 'data'),
    ('data/Tools&materials.txt', 'data'),
    ('data/Traits.txt', 'data'),
    ('data/Treasure.txt', 'data'),
    ('data/Weapon melee.txt', 'data'),
    ('data/Weapon ranged.txt', 'data'),
    ('web-app/templates', 'web-app/templates'),
    ('web-app/static', 'web-app/static'),
]

# Include 3D game client if present
if (SPEC_DIR / 'p5r-game-client').exists():
    data_files.append(('p5r-game-client', 'p5r-game-client'))

a = Analysis(
    ['main.py'],
    pathex=[str(SPEC_DIR)],
    binaries=[],
    datas=data_files,
    hiddenimports=[
        'core',
        'core.crypto',
        'core.parser',
        'core.editor',
        'core.environment',
        'gui',
        'webview',
        'clr_loader',
        'pythonnet',
        'bottle',
        'http.server',
        'urllib.parse',
        'json',
        'base64',
        'webbrowser',
        'threading',
        'tkinter',
        'tkinter.ttk',
        'tkinter.messagebox',
        'tkinter.filedialog',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
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
    console=False,  # Windowed mode: launches clean desktop window without black terminal
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
