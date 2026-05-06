# -*- mode: python ; coding: utf-8 -*-
import os
import sys
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None

# Collect all necessary data and submodules
markdown_datas = collect_data_files('markdown')
pygments_datas = collect_data_files('pygments')

a = Analysis(
    ['main.py'],
    pathex=['/Users/zhuangzheyun/mkdown'],
    binaries=[],
    datas=markdown_datas + pygments_datas,
    hiddenimports=[
        # App modules
        'theme', 'editor', 'preview', 'window', 'highlighter',
        # PyQt5
        'PyQt5', 'PyQt5.QtCore', 'PyQt5.QtGui', 'PyQt5.QtWidgets',
        'PyQt5.QtPrintSupport', 'PyQt5.sip',
        # Markdown extensions
        'markdown', 'markdown.extensions', 'markdown.extensions.extra',
        'markdown.extensions.fenced_code', 'markdown.extensions.tables',
        'markdown.extensions.codehilite', 'markdown.extensions.toc',
        'markdown.extensions.nl2br', 'markdown.extensions.sane_lists',
        'markdown.extensions.meta', 'markdown.extensions.admonition',
        'markdown.extensions.attr_list', 'markdown.extensions.def_list',
        'markdown.extensions.footnotes', 'markdown.extensions.abbr',
        # Pygments
        'pygments', 'pygments.lexers', 'pygments.formatters',
        'pygments.formatters.html', 'pygments.styles',
        'pygments.styles.friendly', 'pygments.styles.monokai',
    ] + collect_submodules('pygments.lexers')
      + collect_submodules('pygments.styles'),
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter', 'PyQt5.QtWebEngineWidgets', 'PyQt5.QtWebEngineCore'],
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
    name='MkDown',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='MkDown',
)

app = BUNDLE(
    coll,
    name='MkDown.app',
    icon='MkDown.icns',
    bundle_identifier='com.mkdown.app',
    info_plist={
        'CFBundleName': 'MkDown',
        'CFBundleDisplayName': 'MkDown',
        'CFBundleVersion': '1.1.1',
        'CFBundleShortVersionString': '1.1.1',
        'NSHighResolutionCapable': True,
        'NSRequiresAquaSystemAppearance': False,  # support dark mode
        'LSMinimumSystemVersion': '11.0',
        'CFBundleDocumentTypes': [
            {
                'CFBundleTypeName': 'Markdown Document',
                'CFBundleTypeExtensions': ['md', 'markdown'],
                'CFBundleTypeRole': 'Editor',
                'LSItemContentTypes': [
                    'net.daringfireball.markdown',
                    'public.markdown',
                    'public.plain-text',
                ],
                'LSHandlerRank': 'Owner',
            }
        ],
        'UTImportedTypeDeclarations': [
            {
                'UTTypeIdentifier': 'net.daringfireball.markdown',
                'UTTypeDescription': 'Markdown Document',
                'UTTypeConformsTo': ['public.plain-text'],
                'UTTypeTagSpecification': {
                    'public.filename-extension': ['md', 'markdown'],
                    'public.mime-type': ['text/markdown', 'text/x-markdown'],
                },
            }
        ],
        'UTExportedTypeDeclarations': [],
    },
)
