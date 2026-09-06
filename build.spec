# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for OKO БОД Manager.

Build command:
    pyinstaller build.spec

Output: dist/oko_manager/
"""

import os

block_cipher = None

# Add resources (icon, etc.)
resource_dir = os.path.join(os.path.dirname(__file__), 'oko_app', 'resources')
datas = []
if os.path.isdir(resource_dir):
    datas.append((resource_dir, 'oko_app/resources'))

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=[
        'PyQt5.sip',
        'serial',
        'serial.tools',
        'serial.tools.list_ports',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter', 'unittest'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='oko_manager',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # No console window
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=os.path.join(resource_dir, 'icon.ico') if os.path.isdir(resource_dir) else None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='oko_manager',
)
