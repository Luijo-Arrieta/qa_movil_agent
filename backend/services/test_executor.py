"""
Servicio para ejecutar tests.
"""

import uuid
import logging
import threading
from datetime import datetime
from typing import Dict, Optional
from appium import webdriver
from appium.options.android import UiAutomator2Options

from src.test_runner import AITestRunner
from src.config import Config
from backend.config import settings

logger = logging.getLogger(__name__)

# Almacenamiento temporal de resultados (en producción usar DB)
test_results: Dict[str, Dict] = {}


class TestExecutor:
    """Ejecuta tests usando AITestRunner."""
    
    @staticmethod
    def _create_driver(device_name: Optional[str] = None, 
                      app_package: Optional[str] = None,
                      app_activity: Optional[str] = None):
        """Crea un driver de Appium."""
        capabilities = Config.get_appium_capabilities()
        
        # Override con parámetros si se proporcionan
        if device_name:
            capabilities["appium:deviceName"] = device_name
            capabilities["appium:udid"] = device_name
        
        if app_package:
            capabilities["appium:appPackage"] = app_package
        
        if app_activity:
            capabilities["appium:appActivity"] = app_activity
        
        options = UiAutomator2Options()
        for key, value in capabilities.items():
            options.set_capability(key, value)
        
        driver = webdriver.Remote(
            command_executor=Config.APPIUM_SERVER_URL,
            options=options
        )
        
        driver.implicitly_wait(Config.IMPLICIT_WAIT)
        return driver
    
    @staticmethod
    def execute_test_async(test_id: str, test_plan: list, objective: Optional[str],
                           device_name: Optional[str], app_package: Optional[str],
                           app_activity: Optional[str]):
        """
        Ejecuta un test de forma asíncrona en un thread separado.
        
        Args:
            test_id: ID único del test
            test_plan: Lista de pasos del test
            objective: Objetivo del test
            device_name: Nombre del dispositivo
            app_package: Package de la app
            app_activity: Activity de la app
        """
        test_results[test_id] = {
            "test_id": test_id,
            "status": "running",
            "success": False,
            "total_steps": len(test_plan),
            "completed_steps": 0,
            "failed_steps": 0,
            "execution_time": 0.0,
            "error_message": None,
            "execution_stats": None,
            "created_at": datetime.now(),
            "completed_at": None
        }
        
        driver = None
        start_time = datetime.now()
        
        try:
            logger.info(f"TestExecutor: Iniciando test {test_id}")
            
            # Crear driver
            driver = TestExecutor._create_driver(
                device_name=device_name,
                app_package=app_package,
                app_activity=app_activity
            )
            
            # Crear runner
            runner = AITestRunner(driver=driver, objective=objective)
            
            # Ejecutar test
            success = runner.run_test_plan(test_plan)
            
            # Obtener estadísticas
            stats = runner.get_execution_stats()
            
            # Calcular tiempo de ejecución
            execution_time = (datetime.now() - start_time).total_seconds()
            
            # Actualizar resultados
            test_results[test_id].update({
                "status": "completed" if success else "failed",
                "success": success,
                "completed_steps": stats.get("completed_steps", 0),
                "failed_steps": stats.get("failed_steps", 0),
                "execution_time": execution_time,
                "execution_stats": stats,
                "completed_at": datetime.now()
            })
            
            logger.info(f"TestExecutor: Test {test_id} completado - Success: {success}")
            
        except Exception as e:
            logger.error(f"TestExecutor: Error ejecutando test {test_id}: {e}", exc_info=True)
            execution_time = (datetime.now() - start_time).total_seconds()
            
            test_results[test_id].update({
                "status": "failed",
                "success": False,
                "execution_time": execution_time,
                "error_message": str(e),
                "completed_at": datetime.now()
            })
        finally:
            if driver:
                try:
                    driver.quit()
                except:
                    pass
    
    @staticmethod
    def execute_test(test_plan: list, objective: Optional[str] = None,
                    device_name: Optional[str] = None,
                    app_package: Optional[str] = None,
                    app_activity: Optional[str] = None) -> str:
        """
        Inicia la ejecución de un test (no bloqueante).
        
        Returns:
            ID del test iniciado
        """
        test_id = str(uuid.uuid4())
        
        # Ejecutar en thread separado
        thread = threading.Thread(
            target=TestExecutor.execute_test_async,
            args=(test_id, test_plan, objective, device_name, app_package, app_activity)
        )
        thread.daemon = True
        thread.start()
        
        return test_id
    
    @staticmethod
    def get_result(test_id: str) -> Optional[Dict]:
        """Obtiene el resultado de un test."""
        return test_results.get(test_id)
