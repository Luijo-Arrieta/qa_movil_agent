"""
Generador de archivos de test.
"""

import os
from pathlib import Path
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class TestGenerator:
    """Genera archivos de test en formato Python."""
    
    @staticmethod
    def generate_test_file(description: str, test_name: Optional[str] = None,
                          output_path: Optional[str] = None) -> str:
        """
        Genera un archivo de test Python desde una descripción.
        
        Args:
            description: Descripción del test en lenguaje natural
            test_name: Nombre del archivo (opcional)
            output_path: Ruta de salida (opcional)
            
        Returns:
            Ruta del archivo generado
        """
        # Generar nombre de archivo
        if not test_name:
            # Extraer nombre de la descripción o usar default
            test_name = "test_generated"
        
        # Asegurar que termine en .py
        if not test_name.endswith('.py'):
            test_name += '.py'
        
        # Determinar ruta de salida
        if output_path:
            file_path = Path(output_path) / test_name
        else:
            # Por defecto, guardar en tests/specs/examples
            output_dir = Path("tests/specs/examples")
            output_dir.mkdir(parents=True, exist_ok=True)
            file_path = output_dir / test_name
        
        # Generar contenido del archivo
        content = f'''"""
Test generado automáticamente.

Descripción: {description}
"""

import pytest
from src.test_runner import AITestRunner
from src.config import Config


@pytest.mark.integration
@pytest.mark.usefixtures("driver_setup")
def test_generated(driver_setup):
    """
    Test generado desde descripción:
    {description}
    """
    objective = "{description}"
    
    runner = AITestRunner(driver=driver_setup, objective=objective)
    
    # TODO: Agregar pasos específicos del test plan
    # Este es un template básico que necesita ser completado
    test_plan = [
        # Agrega los pasos del test aquí
    ]
    
    success = runner.run_test_plan(test_plan)
    assert success, "El test no se completó exitosamente"
'''
        
        # Escribir archivo
        file_path.write_text(content, encoding='utf-8')
        logger.info(f"TestGenerator: Archivo generado en {file_path}")
        
        return str(file_path)
