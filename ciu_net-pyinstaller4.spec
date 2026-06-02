# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['ciu_net.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('config', 'config'),
        ('icon', 'icon'),
    ],
    hiddenimports=[
        'influxpy',
        'sip',
        'PyQt5',
        'PyQt5.sip',
        'PyQt5.QtCore',
        'PyQt5.QtGui',
        'PyQt5.QtNetwork',
        'PyQt5.QtWidgets',
        'pyqtgraph',
        'pymodbus.client',
        'numpy_ringbuffer',
        'scipy._lib.messagestream',
        'validate',
    ],
    hookspath=['.'],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='ciu_net',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    icon='icon/scanner1.ico',
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='ciu_net',
)
