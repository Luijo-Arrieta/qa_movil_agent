#!/usr/bin/env python
"""
Script para generar reporte HTML de Allure sin necesidad de Allure CLI.
Usa allure-combine para generar un HTML autocontenido.
"""

import sys
from pathlib import Path

# Agregar el directorio raíz al path
ROOT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT_DIR))

REPORTS_DIR = ROOT_DIR / "reports"
ALLURE_RESULTS_DIR = REPORTS_DIR / "allure-results"
OUTPUT_FILE = REPORTS_DIR / "allure-report.html"


def generate_report():
    """Genera el reporte HTML combinado de Allure."""
    from allure_combine import combine_allure

    # Crear carpeta reports si no existe
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    # Verificar que existan resultados
    if not ALLURE_RESULTS_DIR.exists():
        print(f"❌ No se encontró el directorio de resultados: {ALLURE_RESULTS_DIR}")
        print("   Ejecuta primero: poetry run pytest")
        sys.exit(1)

    json_files = list(ALLURE_RESULTS_DIR.glob("*-result.json"))
    if not json_files:
        print(f"❌ No hay resultados de tests en: {ALLURE_RESULTS_DIR}")
        print("   Ejecuta primero: poetry run pytest")
        sys.exit(1)

    print(f"📊 Generando reporte Allure...")
    print(f"   Resultados: {ALLURE_RESULTS_DIR}")
    print(f"   Salida: {OUTPUT_FILE}")

    # Generar reporte combinado
    combine_allure(
        str(ALLURE_RESULTS_DIR),
        str(OUTPUT_FILE),
        remove_temp_files=True,
        auto_create_folders=True
    )

    print(f"✅ Reporte generado: {OUTPUT_FILE}")
    print(f"   Abre el archivo en tu navegador para ver los resultados.")

    return str(OUTPUT_FILE)


if __name__ == "__main__":
    generate_report()
