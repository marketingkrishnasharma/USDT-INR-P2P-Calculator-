# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec for P2P Calc Windows EXE
# Run:  pyinstaller p2pcalc.spec

import sys
from pathlib import Path

# Find customtkinter data files (themes, images)
import customtkinter
ctk_path = Path(customtkinter.__file__).parent

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[
        (str(ctk_path), 'customtkinter'),
    ],
    hiddenimports=[
        'customtkinter',
        'tkinter',
        'tkinter.ttk',
        'PIL',
        'PIL.Image',
        'PIL.ImageTk',
        'requests',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='P2PCalc',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,          # No console window
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    # icon='assets/icon.ico',   # Uncomment and add your .ico file
)
