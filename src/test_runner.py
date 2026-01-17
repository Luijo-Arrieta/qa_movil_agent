"""
Test Runner - Orquesta la ejecución de pruebas usando el agente de IA.

NOTA: Este archivo mantiene compatibilidad hacia atrás.
Para nueva funcionalidad, usar src.v1.test_runner (QAI V1) o src.v2.test_runner (QAI V2).
Para selección automática según QAI_VERSION, usar src.create_qai().
"""

from src import create_qai
from typing import Optional
from appium.webdriver import Remote

# Alias para compatibilidad hacia atrás
def AITestRunner(driver: Remote, objective: Optional[str] = None):
    """
    Alias para compatibilidad hacia atrás.
    
    Usa create_qai() que selecciona V1 o V2 según QAI_VERSION.
    Por defecto usa V1.
    """
    return create_qai(driver, objective)

# Exportar también la clase directamente para tests unitarios que la necesiten
from src.v1.test_runner import QAIV1TestRunner

# Para tests unitarios que necesitan acceso directo a V1
__all__ = ['AITestRunner', 'QAIV1TestRunner']
