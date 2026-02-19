#!/bin/bash

# Script para generar binario standalone del CLI usando PyInstaller

set -e

echo "🔨 Construyendo CLI standalone con PyInstaller..."

# Crear directorio de build si no existe
mkdir -p dist

# Limpiar builds anteriores
rm -rf build dist/qa-agent*

# Crear spec file para PyInstaller
cat > qa-agent.spec << 'EOF'
# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['cli/main.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=[
        'click',
        'appium',
        'src',
        'src.test_runner',
        'src.ai_orchestrator',
        'src.agent_tools',
        'src.ui_parser',
        'src.config',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='qa-agent',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
EOF

# Ejecutar PyInstaller
poetry run pyinstaller qa-agent.spec --clean --noconfirm

# Verificar que el binario se creó
if [ -f "dist/qa-agent" ] || [ -f "dist/qa-agent.exe" ]; then
    echo "✅ Build exitoso!"
    echo "📦 Binario generado en: dist/"
    
    # Limpiar archivo spec temporal
    rm -f qa-agent.spec
    
    echo ""
    echo "Para usar el binario:"
    if [ -f "dist/qa-agent" ]; then
        echo "  ./dist/qa-agent --help"
    else
        echo "  dist\\qa-agent.exe --help"
    fi
else
    echo "❌ Error: No se generó el binario"
    exit 1
fi
