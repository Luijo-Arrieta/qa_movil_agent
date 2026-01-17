"""
AutoDroid-AI Agent - Agente de IA para Pruebas Móviles Autónomas
"""

__version__ = "1.0.0"

from typing import Optional
from appium.webdriver import Remote
from src.config import Config


def create_qai(driver: Remote, objective: Optional[str] = None):
    """
    Factory para crear QAI V1 o V2 según configuración.
    
    Args:
        driver: Instancia del driver de Appium
        objective: Objetivo general del test (opcional)
        
    Returns:
        Instancia de QAIV1TestRunner o QAIV2TestRunner según QAI_VERSION
    """
    version = Config.QAI_VERSION  # "v1" o "v2" (default: "v1")
    
    if version == "v2":
        from src.v2.test_runner import QAIV2TestRunner
        return QAIV2TestRunner(driver, objective)
    else:
        from src.v1.test_runner import QAIV1TestRunner
        return QAIV1TestRunner(driver, objective)
