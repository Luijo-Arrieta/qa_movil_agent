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
        # Nueva contraseña que cumple con el mínimo de 8 caracteres
        new_password = "NuevaPass123"

        # Crear runner del agente de IA
        runner = AITestRunner(driver=driver_setup, objective=objective)

        # Plan de prueba en lenguaje natural para el agente (happy-path)
        test_plan = [
            # Apertura explícita de la app (no se abre por defecto)
            "Abrir la app de cliente usando activate_app con el paquete 'com.imagineapps.gofixiicliente'",

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
            "Verificar que se muestra un mensaje de éxito indicando que la contraseña fue actualizada",

            # Verificar que se puede iniciar sesión con la nueva contraseña
            "Esperar a ver la pantalla de inicio de sesión",
            f"Ingresar el correo '{test_email}' en el campo de correo electrónico",
            f"Ingresar la nueva contraseña '{new_password}' en el campo de contraseña",
            "Tocar el botón Ingresar o Iniciar sesión",
            "Verificar que se muestra la pantalla principal del cliente, confirmando que el login funciona con la nueva contraseña",
        ]

        # Ejecutar el plan completo con el agente
        success = runner.run_test_plan(test_plan)

        # Verificar que todos los pasos se completaron correctamente
        assert success, "El flujo de recuperación de contraseña (AC-002) no se completó exitosamente"

    def test_password_recovery_invalid_code_ac002(self, driver_setup):
        """
        Validación de código incorrecto:
        - Solicitar restablecimiento
        - Ingresar código incorrecto
        - Verificar que se muestra error
        - Verificar que se puede solicitar reenvío después de 30 segundos
        """
        objective = (
            "Validar AC-002: manejo de código de verificación incorrecto en recuperación de contraseña, "
            "verificando que se muestra error y que el reenvío está disponible después de 30 segundos."
        )

        test_email = Config.TEST_USER_EMAIL

        runner = AITestRunner(driver=driver_setup, objective=objective)

        test_plan = [
            # Apertura de la app
            "Abrir la app de cliente usando activate_app con el paquete 'com.imagineapps.gofixiicliente'",
            "Esperar a ver la pantalla de inicio de sesión del cliente",

            # Solicitar restablecimiento
            "Tocar el enlace o botón '¿Olvidaste tu contraseña?' o 'Recuperar contraseña'",
            "Esperar a ver la pantalla de recuperación de contraseña",
            f"Ingresar el correo electrónico '{test_email}' en el campo de correo",
            "Tocar el botón 'Enviar código' o 'Solicitar código de verificación'",
            "Verificar que se muestra la pantalla para ingresar el código de verificación",

            # Intentar con código incorrecto
            "Ingresar un código de verificación incorrecto '0000' en el campo de código",
            "Tocar el botón 'Verificar' o 'Continuar'",
            "Verificar que se muestra un mensaje de error indicando que el código es incorrecto",

            # Verificar opción de reenvío (después de esperar 30 segundos si es necesario)
            "Verificar que existe una opción para solicitar reenvío del código",
            "Si el botón de reenvío está deshabilitado, esperar hasta que esté habilitado (máximo 30 segundos)",
        ]

        success = runner.run_test_plan(test_plan)
        assert success, "La validación de código incorrecto (AC-002) no se completó exitosamente"

    def test_password_recovery_password_validation_ac002(self, driver_setup):
        """
        Validación de nueva contraseña:
        - Verificar que se requiere mínimo 8 caracteres
        - Verificar validación en tiempo real de coincidencia de campos
        - Verificar que el botón se habilita solo cuando ambos campos coinciden
        """
        objective = (
            "Validar AC-002: validación de nueva contraseña en tiempo real, "
            "verificando mínimo de 8 caracteres y coincidencia de campos antes de habilitar el botón."
        )

        test_email = Config.TEST_USER_EMAIL
        short_password = "12345"  # Menos de 8 caracteres
        valid_password = "NuevaPass123"  # 8+ caracteres

        runner = AITestRunner(driver=driver_setup, objective=objective)

        test_plan = [
            # Apertura de la app y navegación hasta pantalla de nueva contraseña
            "Abrir la app de cliente usando activate_app con el paquete 'com.imagineapps.gofixiicliente'",
            "Esperar a ver la pantalla de inicio de sesión del cliente",
            "Tocar el enlace o botón '¿Olvidaste tu contraseña?' o 'Recuperar contraseña'",
            "Esperar a ver la pantalla de recuperación de contraseña",
            f"Ingresar el correo electrónico '{test_email}' en el campo de correo",
            "Tocar el botón 'Enviar código' o 'Solicitar código de verificación'",
            f"Obtener el código de confirmación enviado al correo '{test_email}' usando get_confirmation_code",
            "Ingresar el código de verificación de 4 dígitos obtenido en el campo correspondiente",
            "Tocar el botón 'Verificar' o 'Continuar'",
            "Esperar a ver la pantalla para establecer nueva contraseña",

            # Validar contraseña corta (menos de 8 caracteres)
            f"Intentar ingresar una contraseña corta '{short_password}' en el campo de nueva contraseña",
            "Verificar que se muestra un mensaje de error indicando que la contraseña debe tener mínimo 8 caracteres",
            "Verificar que el botón 'Restablecer' está deshabilitado",

            # Validar contraseña válida pero campos no coinciden
            f"Ingresar la contraseña válida '{valid_password}' en el campo de nueva contraseña",
            f"Ingresar una contraseña diferente '{valid_password}XYZ' en el campo de confirmación",
            "Verificar que se muestra un mensaje indicando que las contraseñas no coinciden",
            "Verificar que el botón 'Restablecer' está deshabilitado",

            # Validar que cuando coinciden, el botón se habilita
            f"Corregir el campo de confirmación para que coincida con '{valid_password}'",
            "Verificar que el mensaje de error desaparece y el botón 'Restablecer' se habilita",
        ]

        success = runner.run_test_plan(test_plan)
        assert success, "La validación de contraseña (AC-002) no se completó exitosamente"
