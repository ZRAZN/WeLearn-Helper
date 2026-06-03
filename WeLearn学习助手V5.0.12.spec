# -*- mode: python ; coding: utf-8 -*-

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[('ZR.ico', '.'), ('ZR.png', '.'), ('accounts.json', '.'), ('ui\\network_fix_dialog.py', 'ui'), ('ui\\__init__.py', 'ui'), ('core\\network_fixer.py', 'core'), ('core\\__init__.py', 'core')],
    hiddenimports=['ui.network_fix_dialog', 'core.network_fixer'],
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
    name='WeLearn学习助手V5.0.12',
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
    icon=['ZR.ico'],
    uac_admin=True,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='WeLearn学习助手V5.0.12',
)
