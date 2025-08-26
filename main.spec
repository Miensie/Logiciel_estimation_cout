# -*- mode: python ; coding: utf-8 -*-
import sys
import os
from pathlib import Path

# Configuration pour différentes plateformes
block_cipher = None
is_windows = sys.platform.startswith('win')
is_macos = sys.platform == 'darwin'
is_linux = sys.platform.startswith('linux')

# Définir le chemin vers le fichier source
if os.path.exists('src/main.py'):
    main_script = 'src/main.py'
elif os.path.exists('main.py'):
    main_script = 'main.py'
else:
    raise FileNotFoundError("Impossible de trouver main.py")

# Dépendances cachées (hidden imports)
hiddenimports = [
    # SQLite3 et alternatives
    'pysqlite3',
    'pysqlite3.dbapi2',
    'sqlite3',
    'sqlite3.dbapi2',
    'sqlite3.dump',
    
    # ReportLab complet
    'reportlab',
    'reportlab.pdfgen',
    'reportlab.pdfgen.canvas',
    'reportlab.lib',
    'reportlab.lib.pagesizes',
    'reportlab.lib.styles',
    'reportlab.lib.colors',
    'reportlab.lib.units',
    'reportlab.platypus',
    'reportlab.platypus.doctemplate',
    'reportlab.platypus.tables',
    'reportlab.platypus.paragraph',
    'reportlab.platypus.flowables',
    'reportlab.platypus.frames',
    'reportlab.graphics',
    'reportlab.graphics.shapes',
    'reportlab.graphics.charts',
    
    # PIL/Pillow
    'PIL',
    'PIL.Image',
    'PIL.ImageDraw',
    'PIL.ImageFont',
    'PIL._imaging',
    
    # Flet et ses dépendances
    'flet',
    'flet.core',
    'flet.core.control',
    'flet.core.page',
    
    # Modules standard Python
    'datetime',
    'json',
    'tempfile',
    'os',
    'typing',
]

# Données à inclure (assets, etc.)
datas = []
if os.path.exists('assets'):
    datas.append(('assets', 'assets'))
if os.path.exists('src/assets'):
    datas.append(('src/assets', 'assets'))

# Binaires supplémentaires (DLL sqlite3 sur Windows)
binaries = []
if is_windows:
    # Chercher les DLL sqlite3
    python_dir = Path(sys.executable).parent
    possible_sqlite_dlls = [
        python_dir / "DLLs" / "sqlite3.dll",
        python_dir / "Library" / "bin" / "sqlite3.dll",
        Path(sys.prefix) / "DLLs" / "sqlite3.dll",
    ]
    
    for dll_path in possible_sqlite_dlls:
        if dll_path.exists():
            binaries.append((str(dll_path), '.'))
            print(f"Ajout DLL sqlite3: {dll_path}")

a = Analysis(
    [main_script],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Exclure des modules non nécessaires pour réduire la taille
        'tkinter',
        'matplotlib',
        'numpy',
        'pandas',
        'scipy',
        'jupyter',
        'IPython',
        'test',
        'unittest',
        'pydoc',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

# Filtrer les fichiers Python non nécessaires
a.pure = [x for x in a.pure if not any(exclude in x[0] for exclude in ['test', 'tests', 'testing'])]
a.binaries = [x for x in a.binaries if not any(exclude in x[0] for exclude in ['test', 'tests'])]

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# Configuration de l'exécutable selon la plateforme
if is_windows:
    exe_name = 'EstimationCouts.exe'
    console = False  # Application fenêtrée
    icon_path = 'assets/icon.ico' if os.path.exists('assets/icon.ico') else None
elif is_macos:
    exe_name = 'EstimationCouts'
    console = False
    icon_path = 'assets/icon.icns' if os.path.exists('assets/icon.icns') else None
else:  # Linux
    exe_name = 'EstimationCouts'
    console = False
    icon_path = 'assets/icon.png' if os.path.exists('assets/icon.png') else None

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name=exe_name,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=console,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=icon_path,
)

# Pour macOS, créer un bundle .app
if is_macos:
    app = BUNDLE(
        exe,
        name='EstimationCouts.app',
        icon=icon_path,
        bundle_identifier='com.proseen.estimationcouts',
        info_plist={
            'NSPrincipalClass': 'NSApplication',
            'NSHighResolutionCapable': 'True',
            'CFBundleDisplayName': 'Estimation des Coûts',
            'CFBundleVersion': '1.0.0',
            'CFBundleShortVersionString': '1.0.0',
        },
    )
