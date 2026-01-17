"""
Ejemplo de uso del agente de IA para pruebas móviles.

Este archivo muestra cómo crear tests usando el AITestRunner
para ejecutar flujos completos en apps móviles usando lenguaje natural.

REQUISITOS:
- Appium Server corriendo
- Dispositivo Android / Emulador conectado
- App instalada o APK configurado en .env.local
- Credenciales de prueba configuradas en .env.local (TEST_USER_EMAIL, TEST_USER_PASSWORD)
"""

import pytest

from src import create_qai
from src.config import Config


@pytest.mark.integration
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

        # Obtener credenciales desde variables de entorno
        test_email = Config.TEST_USER_EMAIL
        test_password = Config.TEST_USER_PASSWORD

        # Crear test runner (usa QAI_VERSION de .env)
        runner = create_qai(driver=driver_setup, objective=objective)

        # Definir plan de prueba en lenguaje natural
        test_plan = [
            "Esperar a ver la pantalla de login",
            f"Ingresar usuario '{test_email}'",
            f"Ingresar password '{test_password}'",
            "Tocar botón Ingresar",
            "Verifica que se inició la sesión",
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


@pytest.mark.integration
@pytest.mark.usefixtures("driver_setup")
class TestMultiAppExample:
    """
    Ejemplos de tests que utilizan múltiples aplicaciones.
    
    Estos tests demuestran cómo usar las herramientas de gestión multi-app
    para flujos que requieren cambiar entre aplicaciones.
    """

    @pytest.mark.skip(reason="Ejemplo - requiere dos apps específicas instaladas")
    def test_customer_technical_flow_example(self, driver_setup):
        """
        Ejemplo: Flujo Customer ↔ Technical.
        
        Este test demuestra cómo ejecutar un flujo que involucra
        dos aplicaciones diferentes (Customer y Technical).
        """
        objective = "Flujo completo de solicitud: Cliente crea, Técnico acepta"
        
        runner = AITestRunner(driver=driver_setup, objective=objective)
        
        # Obtener credenciales desde variables de entorno
        test_email = Config.TEST_USER_EMAIL
        test_password = Config.TEST_USER_PASSWORD
        
        test_plan = [
            # FASE 1: Customer crea solicitud
            "Abrir app Customer (com.example.customer)",
            f"Hacer login con email '{test_email}' y password '{test_password}'",
            "Crear una solicitud de servicio",
            
            # FASE 2: Technical acepta (mantener Customer en background)
            "Cambiar a app Technical (com.example.technical) manteniendo Customer en background",
            f"Hacer login como técnico con email 'tecnico@demo.com' y password '{test_password}'",
            "Aceptar la solicitud pendiente",
            
            # FASE 3: Volver a Customer
            "Volver a app Customer",
            "Verificar que la solicitud fue aceptada",
        ]
        
        success = runner.run_test_plan(test_plan)
        assert success, "El flujo multi-app no se completó exitosamente"
