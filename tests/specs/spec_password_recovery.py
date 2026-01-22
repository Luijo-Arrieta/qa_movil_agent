"""
Especificación de prueba: Recuperación de contraseña (AC-002).

Cómo ejecutar este archivo completo:
    poetry run pytest tests/specs/spec_password_recovery.py -v

Cómo ejecutar solo esta clase:
    poetry run pytest tests/specs/spec_password_recovery.py::TestPasswordRecoverySpec -v

Cómo ejecutar solo este test:
    poetry run pytest tests/specs/spec_password_recovery.py::TestPasswordRecoverySpec::test_password_recovery_happy_path_ac002 -v
"""

import pytest

from src.test_runner import AITestRunner
from src.config import Config


@pytest.mark.integration
@pytest.mark.usefixtures("driver_setup")
class TestPasswordRecoverySpec:
    """
    Historia de usuario AC-002:

    Como usuario super APP debo poder recuperar mi contraseña para poder acceder
    a la plataforma.

    Criterios de aceptación:
    - Solicitar restablecimiento con correo electrónico registrado
    - Recibir código de verificación de 4 dígitos válido por 1 hora
    - Validar código (error si incorrecto, reenvío después de 30 seg)
    - Ingresar y confirmar nueva contraseña (mínimo 8 caracteres, validación en tiempo real)
    - Correo debe enviarse inmediatamente
    - Contraseña debe actualizarse y permitir login inmediato
    - Manejo de código expirado o múltiples intentos incorrectos
    """

    def test_password_recovery_happy_path_ac002(self, driver_setup):
        """
        Flujo completo de recuperación de contraseña (happy path):
        - Solicitar restablecimiento con correo registrado
        - Ingresar código de verificación recibido por correo
        - Establecer nueva contraseña con validación
        - Verificar que se puede iniciar sesión con la nueva contraseña

        NOTA: Este test asume que en el entorno de prueba:
        - El código de verificación puede obtenerse del correo de prueba
        - O existe un código de prueba conocido/configurado
        - O la app muestra el código en modo desarrollo/prueba
        """
        # Objetivo general del test
        objective = (
            "Validar historia de usuario AC-002: recuperación de contraseña completa "
            "verificando solicitud de código, validación de código de 4 dígitos, "
            "establecimiento de nueva contraseña con validación en tiempo real, "
            "y verificación de que el login funciona con las nuevas credenciales."
        )

# Credenciales de prueba
        test_email = "luis.arrieta+pass-recovery-0@imagineapps.co"
        # Nueva contraseña dinámica que cumple con el mínimo de 8 caracteres
        new_password = Config.get_dynamic_test_password()

        # Crear runner del agente de IA
        runner = AITestRunner(driver=driver_setup, objective=objective)

        # Plan de prueba en lenguaje natural para el agente (happy-path)
        test_plan = [
            # Apertura explícita de la app usando HumanAction (lambda) para mayor velocidad
            lambda tools: tools.activate_app("com.imagineapps.gofixiicliente"),

            # Asegurar que estamos en la pantalla de login
            #"Esperar a ver la pantalla de inicio de sesión del cliente",

            # Iniciar proceso de recuperación de contraseña
            # Prueba de más de una acción por paso
            "Tocar el enlace o botón '¿Olvidaste tu contraseña?' o 'Recuperar contraseña' y Esperar a ver la pantalla de recuperación de contraseña",

            # Solicitar restablecimiento con correo registrado
            f"Ingresar el correo electrónico registrado '{test_email}' en el campo de correo",
            "Tocar el botón 'Enviar código' o 'Solicitar código de verificación'",
            #"Verificar que se muestra un mensaje indicando que el código fue enviado al correo",
            #"Verificar que se muestra la pantalla para ingresar el código de verificación de 4 dígitos",

            # Ingresar código de verificación
            # Obtener el código de confirmación desde el webhook de n8n
            f"Obtener el código de confirmación enviado al correo '{test_email}' usando get_confirmation_code",
            "Ingresar el código de verificación de 4 dígitos obtenido en el campo correspondiente",

            "Verificar que el código es válido y se muestra la pantalla para establecer nueva contraseña",

            # Establecer nueva contraseña con validación
            f"Ingresar la nueva contraseña '{new_password}' en el campo de nueva contraseña",
            f"Confirmar la nueva contraseña '{new_password}' en el campo de confirmación",
            "Verificar que ambos campos de contraseña coinciden y el botón 'Restablecer' está habilitado",
            "Tocar el botón 'Restablecer' o 'Cambiar contraseña'",
            "Verificar que se muestra un popup con mensaje de éxito indicando que la contraseña fue actualizada y Cerrar el popup de éxito usando touch_out_element para continuar con el login",
            f"Ingresar el correo '{test_email}' en el campo de correo electrónico",
            f"Ingresar la nueva contraseña '{new_password}' en el campo de contraseña",
            "Tocar el botón Ingresar o Iniciar sesión",
            "Verificar que se muestra la pantalla principal del cliente, confirmando que el login funciona con la nueva contraseña",
        ]

        # Ejecutar el plan completo con el agente
        success = runner.run_test_plan(test_plan)

        # Verificar que todos los pasos se completaron correctamente
        assert success, "El flujo de recuperación de contraseña (AC-002) no se completó exitosamente"