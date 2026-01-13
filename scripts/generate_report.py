#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script para generar reporte HTML de Allure usando el CLI directamente.
Este script agrega la ruta de Allure al PATH y ejecuta los comandos necesarios.
"""

import sys
import subprocess
import os
from pathlib import Path

# Agregar el directorio raíz al path
ROOT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT_DIR))

REPORTS_DIR = ROOT_DIR / "reports"
ALLURE_RESULTS_DIR = REPORTS_DIR / "allure-results"
ALLURE_REPORT_DIR = REPORTS_DIR / "allure-report"

# Ruta al CLI de Allure (Windows)
ALLURE_BIN_DIR = Path("D:/Imagine/allure-2.36.0/allure-2.36.0/bin")


def generate_report():
    """Genera el reporte HTML de Allure usando el CLI."""
    
    # Crear carpeta reports si no existe
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    # Verificar que existan resultados
    if not ALLURE_RESULTS_DIR.exists():
        print(f"[ERROR] No se encontro el directorio de resultados: {ALLURE_RESULTS_DIR}")
        print("   Ejecuta primero: poetry run pytest")
        sys.exit(1)

    json_files = list(ALLURE_RESULTS_DIR.glob("*-result.json"))
    if not json_files:
        print(f"[ERROR] No hay resultados de tests en: {ALLURE_RESULTS_DIR}")
        print("   Ejecuta primero: poetry run pytest")
        sys.exit(1)

    # Agregar Allure al PATH si existe
    if ALLURE_BIN_DIR.exists():
        allure_bin = str(ALLURE_BIN_DIR)
        if allure_bin not in os.environ.get("PATH", ""):
            os.environ["PATH"] = f"{allure_bin};{os.environ.get('PATH', '')}"
    else:
        print(f"[WARNING] No se encontro Allure en: {ALLURE_BIN_DIR}")
        print("   Intentando usar 'allure' del PATH del sistema...")

    print(f"[INFO] Generando reporte Allure...")
    print(f"   Resultados: {ALLURE_RESULTS_DIR}")
    print(f"   Salida: {ALLURE_REPORT_DIR}")

    # Generar reporte con Allure CLI
    try:
        # En Windows, usar allure.bat directamente
        if sys.platform == 'win32' and ALLURE_BIN_DIR.exists():
            allure_cmd = str(ALLURE_BIN_DIR / "allure.bat")
        else:
            allure_cmd = "allure"
        
        result = subprocess.run(
            [
                allure_cmd,
                "generate",
                str(ALLURE_RESULTS_DIR),
                "-o",
                str(ALLURE_REPORT_DIR),
                "--clean"
            ],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding='utf-8',
            errors='replace'
        )
        
        if result.stdout:
            print(result.stdout)
        
        print(f"[OK] Reporte generado en: {ALLURE_REPORT_DIR}")
        print(f"   Para ver el reporte:")
        print(f"   allure serve {ALLURE_RESULTS_DIR}")
        print(f"   O abre: {ALLURE_REPORT_DIR / 'index.html'}")
        
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] Error al generar reporte con Allure CLI:")
        if e.stdout:
            print(e.stdout)
        if e.stderr:
            print(e.stderr)
        sys.exit(1)
    except FileNotFoundError:
        print(f"[ERROR] No se encontro el comando 'allure'")
        print(f"   Asegurate de que Allure este instalado en: {ALLURE_BIN_DIR}")
        print(f"   O agregalo al PATH del sistema")
        sys.exit(1)

    return str(ALLURE_REPORT_DIR)


if __name__ == "__main__":
    generate_report()
