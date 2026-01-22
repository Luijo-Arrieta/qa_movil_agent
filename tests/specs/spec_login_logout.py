"""
Especificación de prueba: Inicio y cierre de sesión (AC-001).

Cómo ejecutar este archivo completo:
    poetry run pytest tests/specs/spec_login_logout.py -v

Cómo ejecutar solo esta clase:
    poetry run pytest tests/specs/spec_login_logout.py::TestLoginLogoutSpec -v

Cómo ejecutar solo este test:
    poetry run pytest tests/specs/spec_login_logout.py::TestLoginLogoutSpec::test_login_and_logout_cliente_ac001 -v
"""

import pytest

from src import create_qai
from src.config import Config


@pytest.mark.integration
@pytest.mark.usefixtures("driver_setup")
class TestLoginLogoutSpec:
    """
    Historia de usuario AC-001:

    Como usuario de la plataforma debo poder iniciar sesión en la APP como cliente
    y poder cerrar sesión correctamente.

    Esta especificación está pensada para una app de cliente configurada mediante
    las variables de entorno ANDROID_APP_PACKAGE / ANDROID_APP_ACTIVITY.
    La app NO se abre automáticamente: el plan incluye explícitamente la apertura
    usando la funcionalidad equivalente a activateApp().
    """

    def test_login_and_logout_cliente_ac001(self, driver_setup):
        """
        Flujo completo de autenticación:
        - Validar requisitos de campos obligatorios
        - Validar formato de correo electrónico
        - Validar manejo de credenciales incorrectas
        - Validar login exitoso con credenciales válidas
        - Validar cierre de sesión y retorno a pantalla de login
        """
        # Objetivo general del test
        objective = (
            "Validar historia de usuario AC-001: inicio y cierre de sesión en la app de cliente "
            "verificando campos obligatorios, formato de correo y manejo de credenciales inválidas."
        )

        # Credenciales válidas de prueba, tomadas desde configuración
        test_email = Config.TEST_USER_EMAIL
        test_password = Config.TEST_USER_PASSWORD

        # Crear runner del agente de IA (usa QAI_VERSION de .env)
        runner = create_qai(driver=driver_setup, objective=objective)

        # Plan de prueba en lenguaje natural para el agente (happy-path)
        test_plan = [
            # Apertura explícita de la app usando HumanAction (lambda) para mayor velocidad
            lambda tools: tools.activate_app("com.imagineapps.gofixiicliente"),

            # Asegurar que estamos en la pantalla de login
            "Esperar a ver la pantalla de inicio de sesión del cliente",

            # Login exitoso con credenciales válidas
            f"Ingresar el correo válido '{test_email}' en el campo de correo electrónico",
            f"Ingresar la contraseña válida '{test_password}' en el campo de contraseña",
            "Tocar el botón Ingresar o Iniciar sesión",
            "Verificar que se muestre la pantalla principal del cliente, esto indica que la sesión se inició correctamente",

            # Cierre de sesión
            "Abrir el menú de Cuenta o perfil de usuario de la app",
            "Seleccionar la opción de Cerrar sesión o Logout",
            "Confirmar el cierre de sesión si aparece un cuadro de diálogo de confirmación",
            "Verificar que la app regresa a la pantalla de inicio de sesión del cliente",
        ]

        # Ejecutar el plan completo con el agente
        success = runner.run_test_plan(test_plan)

        # Verificar que todos los pasos se completaron correctamente
        assert success, "El flujo de inicio y cierre de sesión (AC-001) no se completó exitosamente"

