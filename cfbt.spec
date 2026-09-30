# -*- mode: python ; coding: utf-8 -*-

import shutil
from pathlib import Path

a = Analysis(
    ['cfbt.py'],
    pathex=[],
    binaries=[],
    datas=[('assets', 'assets'), ('lang', 'lang')],
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
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['assets/icon.ico'],
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
shutil.copy('README.md', dist_dir / 'README.md')
shutil.copytree('docs', dist_dir / 'docs', dirs_exist_ok=True)

