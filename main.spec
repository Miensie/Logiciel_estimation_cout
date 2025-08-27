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

# CORRECTION PRINCIPALE : Gestion correcte des assets
def collect_assets():
    """Collecte tous les assets nécessaires"""
    assets_data = []
    
    # Chemins possibles pour les assets
    possible_paths = [
        'src/assets',
        'assets',
        './src/assets',
        './assets'
    ]
    
    for asset_path in possible_paths:
        if os.path.exists(asset_path):
            print(f"Assets trouvés dans : {asset_path}")
            # Ajouter tous les fichiers du dossier assets
            for root, dirs, files in os.walk(asset_path):
                for file in files:
                    src_file = os.path.join(root, file)
                    # Calculer le chemin de destination relatif
                    rel_path = os.path.relpath(root, asset_path)
                    if rel_path == '.':
                        dest_dir = 'assets'
                    else:
                        dest_dir = os.path.join('assets', rel_path)
                    assets_data.append((src_file, dest_dir))
            break
    
    return assets_data

# Collecte des données (assets, etc.)
datas = collect_assets()

# Binaires supplémentaires
binaries = []
if is_windows:
    # Chemin SQLite DLL pour Windows
    sqlite_dll_paths = [
        'D:\\python313\\DLLs\\sqlite3.dll',
        sys.executable.replace('python.exe', 'DLLs\\sqlite3.dll'),
        os.path.join(sys.prefix, 'DLLs', 'sqlite3.dll')
    ]
    
    for dll_path in sqlite_dll_paths:
        if os.path.exists(dll_path):
            binaries.append((dll_path, '.'))
            break

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
def find_icon():
    """Trouve l'icône appropriée pour la plateforme"""
    icon_paths = []
    
    if is_windows:
        icon_paths = ['./src/assets/icon.ico', './assets/icon.ico', 'src/assets/icon.ico', 'assets/icon.ico']
    elif is_macos:
        icon_paths = ['./src/assets/icon.icns', './assets/icon.icns', 'src/assets/icon.icns', 'assets/icon.icns']
    else:  # Linux
        icon_paths = ['./src/assets/icon.png', './assets/icon.png', 'src/assets/icon.png', 'assets/icon.png']
    
    for icon_path in icon_paths:
        if os.path.exists(icon_path):
            return icon_path
    return None

if is_windows:
    exe_name = 'EstimationCouts.exe'
    console = False  # Application fenêtrée
elif is_macos:
    exe_name = 'EstimationCouts'
    console = False
else:  # Linux
    exe_name = 'EstimationCouts'
    console = False

icon_path = find_icon()

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