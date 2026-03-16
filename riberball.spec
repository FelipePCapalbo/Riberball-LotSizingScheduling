# -*- mode: python ; coding: utf-8 -*-
#
# Arquivo de configuração do PyInstaller para o executável Riberball Lot Sizing.
#
# Como usar:
#   pyinstaller riberball.spec
#
# O .exe gerado em dist/RiverballLotSizing.exe contém apenas o launcher.
# Os demais módulos Python (app/) permanecem como arquivos .py ao lado do .exe.
#
# Estratégia onedir (--onedir):
#   - Menor risco de falso positivo em antivírus (não descompacta em %TEMP%).
#   - Inicialização mais rápida.
#   - Distribuir a pasta inteira de dist/RiverbállLotSizing/.

import sys
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

# ---------------------------------------------------------------------------
# Coleta de dados estáticos do Flask (templates + arquivos estáticos)
# ---------------------------------------------------------------------------
flask_datas = collect_data_files('flask')

# Arquivos da aplicação que devem ser incluídos no bundle
app_datas = [
    # Templates HTML
    ('app/templates', 'app/templates'),
    # CSS e JS
    ('app/static',    'app/static'),
]

# ---------------------------------------------------------------------------
# Módulos ocultos que o PyInstaller não detecta automaticamente
# ---------------------------------------------------------------------------
hidden_imports = [
    # Flask e extensões internas
    'flask',
    'flask.templating',
    'jinja2',
    'jinja2.ext',
    'werkzeug',
    'werkzeug.serving',
    'werkzeug.routing',
    'werkzeug.middleware.proxy_fix',
    'click',
    # Pandas e dependências
    'pandas',
    'pandas._libs.tslibs.timestamps',
    'pandas._libs.tslibs.np_datetime',
    'pandas._libs.tslibs.nattype',
    'pandas._libs.tslibs.timezones',
    'pandas._libs.tslibs.offsets',
    'pandas._libs.missing',
    'pandas._libs.hashtable',
    'pandas._libs.lib',
    'pandas._libs.index',
    'pandas._libs.algos',
    'pandas._libs.join',
    'pandas._libs.parsers',
    'pandas._libs.writers',
    'pandas._libs.groupby',
    'pandas._libs.reshape',
    'pandas._libs.interval',
    'pandas._libs.testing',
    # openpyxl
    'openpyxl',
    'openpyxl.cell._writer',
    # PuLP
    'pulp',
    'pulp.apis',
    'pulp.apis.coin_api',
    'pulp.apis.glpk_api',
    # Módulos da própria aplicação
    'app',
    'app.main',
    'app.config',
    'app.utils',
    'app.services.data_service',
    'app.modules.etl.loader',
    'app.modules.optimization.solver',
    # Utilitários padrão
    'threading',
    'webbrowser',
    'traceback',
]

# Coleta submodulos do PuLP automaticamente
hidden_imports += collect_submodules('pulp')

a = Analysis(
    ['launcher.py'],
    pathex=['.'],
    binaries=[],
    datas=flask_datas + app_datas,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Exclui módulos desnecessários para reduzir tamanho e falsos positivos
        'tkinter',
        'matplotlib',
        'scipy',
        'sklearn',
        'IPython',
        'jupyter',
        'notebook',
        'pytest',
        'PIL',
        'cv2',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=None)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,  # onedir: mantém DLLs separadas
    name='RiverballLotSizing',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,          # UPX comprime o binário e causa falso positivo em AV — desabilitado
    console=True,       # Mostra console com logs (útil para diagnóstico)
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,          # Substitua por 'icon.ico' se tiver um ícone
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='RiverballLotSizing',
)
