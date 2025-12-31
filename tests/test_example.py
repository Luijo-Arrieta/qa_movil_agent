"""
Ejemplo de uso del agente de IA para pruebas móviles.
"""

import pytest
from src.test_runner import AITestRunner


@pytest.mark.usefixtures("driver_setup")
class TestAIAgentExample:
    """Ejemplos de uso del agente de IA."""

    def test_login_flow_example(self, driver_setup):
        """
        Ejemplo: Flujo de login automatizado por IA.

        Este test demuestra cómo usar el agente para ejecutar un flujo
        completo de login sin escribir selectores manualmente.
        """
        # Definir objetivo general
        objective = "Realizar login en la aplicación con credenciales de prueba"

        # Crear test runner
        runner = AITestRunner(driver=driver_setup, objective=objective)

        # Definir plan de prueba en lenguaje natural
        test_plan = [
            "Abrir la app y esperar a ver la pantalla de login",
            "Ingresar usuario 'cliente@demo.com'",
            "Ingresar password '123456'",
            "Tocar botón Ingresar",
            "Verificar que aparezca el texto 'Bienvenido'",
        ]

        # Ejecutar plan
        success = runner.run_test_plan(test_plan)

        # Verificar que todos los pasos se completaron
        assert success, "El plan de prueba no se completó exitosamente"

    def test_simple_navigation_example(self, driver_setup):
        """
        Ejemplo: Navegación simple en la app.

        Este test demuestra cómo el agente puede navegar por la app
        basándose solo en descripciones en lenguaje natural.
        """
        runner = AITestRunner(driver=driver_setup)

        test_plan = [
            "Abrir el menú principal",
            "Seleccionar la opción 'Configuración'",
            "Verificar que se abra la pantalla de configuración",
        ]

        success = runner.run_test_plan(test_plan)
        assert success, "La navegación no se completó exitosamente"

    @pytest.mark.skip(reason="Ejemplo - requiere app específica")
    def test_form_filling_example(self, driver_setup):
        """
        Ejemplo: Llenar un formulario completo.

        Este test muestra cómo el agente puede llenar formularios
        complejos identificando campos por su contexto.
        """
        objective = "Completar formulario de registro con datos de prueba"

        runner = AITestRunner(driver=driver_setup, objective=objective)

        test_plan = [
            "Navegar al formulario de registro",
            "Llenar el campo de nombre con 'Juan Pérez'",
            "Llenar el campo de email con 'juan@example.com'",
            "Llenar el campo de teléfono con '1234567890'",
            "Seleccionar la opción 'Acepto los términos'",
            "Hacer clic en el botón 'Registrarse'",
            "Verificar que aparezca el mensaje de confirmación",
        ]

        success = runner.run_test_plan(test_plan)
        assert success, "El formulario no se completó exitosamente"

