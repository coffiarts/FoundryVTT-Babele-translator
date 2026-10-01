# -*- mode: python ; coding: utf-8 -*-

import os
import shutil
from pathlib import Path

PROJECT_ROOT = os.path.join(SPECPATH, "..")

a = Analysis(
    [os.path.join(PROJECT_ROOT, 'cfbt.py')],
    pathex=[],
    binaries=[],
    datas=[
        (os.path.join(PROJECT_ROOT, 'assets'), 'assets'),
        (os.path.join(PROJECT_ROOT, 'lang'), 'lang')
    ],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='cfbt',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=[os.path.join(PROJECT_ROOT, 'assets', 'icon.ico')],
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='cfbt',
)

dist_dir = Path(DISTPATH) / coll.name
shutil.copy(os.path.join(PROJECT_ROOT, 'README.md'), dist_dir / 'README.md')
shutil.copy(os.path.join(PROJECT_ROOT, 'CHANGELOG.md'), dist_dir / 'CHANGELOG.md')
shutil.copytree(os.path.join(PROJECT_ROOT, 'docs'), dist_dir / 'docs', dirs_exist_ok=True)
