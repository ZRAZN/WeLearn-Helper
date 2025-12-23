# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[('ZR.ico', '.\\'), ('ZR.png', '.\\')],
    hiddenimports=['ui.account_view', 'core.account_manager', 'core.api', 'core.batch_manager', 'core.config', 'core.logger', 'ui.main_window', 'ui.account_detail', 'ui.workers', 'PyQt5', 'requests', 'bs4', 'lxml', 'psutil'],
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
    a.binaries,
    a.datas,
    [],
    name='WeLearn学习助手V4.6.6',
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
    version='version_info.txt',
    icon=['ZR.ico'],
)
