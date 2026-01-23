"""
Spec for User Story AC-003: Sign Up Flow

This spec validates the complete user registration flow including:
- Required fields validation (email, password, confirmation, birth date)
- Email uniqueness validation
- Terms and conditions acceptance
- Email verification code
- Profile completion (name, surname)
- Successful account creation and session start

How to run:
    # Run entire file
    poetry run pytest tests/specs/spec_sign_up.py -v

    # Run specific test class
    poetry run pytest tests/specs/spec_sign_up.py::TestSignUpSpec -v

    # Run individual test
    poetry run pytest tests/specs/spec_sign_up.py::TestSignUpSpec::test_sign_up_happy_path -v
"""

import pytest
from src.v2.test_runner import QAIV2TestRunner
from src.config import Config


@pytest.mark.integration
class TestSignUpSpec:
    """
    Test class for AC-003: User Registration

    Validates the complete sign-up flow from initial registration
    to profile completion and successful login.
    """

    def test_sign_up_happy_path(self, driver_setup):
        """
        AC-003 - Happy Path: Complete user registration flow

        Covers acceptance criteria:
        1. Complete all required fields with real-time validation
        2. (Email uniqueness - tested separately to avoid duplicate registrations)
        3. Accept terms and conditions checkbox
        4. Email verification code flow
        5. Complete profile with name and surname
        6. Successful account creation and redirect to home

        Note: Uses unique timestamp-based email to avoid conflicts.
        """
        objective = (
            "Validar historia de usuario AC-003: registro completo de nuevo usuario "
            "verificando campos obligatorios, aceptación de términos, verificación de email "
            "y completado de perfil"
        )

        runner = QAIV2TestRunner(driver=driver_setup, objective=objective)

        # Generate unique email to avoid duplicates
        import time
        timestamp = int(time.time())
        test_email = f"test.user.{timestamp}@demo.com"
        test_password = Config.TEST_USER_PASSWORD or "Test123!"

        test_plan = [
            # Step 1: Open customer app and navigate to sign-up
            # Step 1: Open customer app using HumanAction (lambda) for faster startup
            lambda tools: tools.activate_app("com.imagineapps.gofixiicliente"),
            "Esperar a ver la pantalla de inicio de sesión",
            "Tocar el enlace o botón para crear una cuenta nueva",

            # Step 2-3: Fill registration form (AC-003.1 & AC-003.3)
            "Tocar el campo de entrada de fecha de nacimiento para abrir el selector de fecha",
            "En el selector de fecha, cambiar el año hasta que sea 2006 o menor usando touch y scroll según sea necesario",
            "Seleccionar el día 1 y mes enero en el selector de fecha",
            "Tocar el botón de confirmar/aceptar la fecha en el selector (debe estar habilitado si los pasos anteriores fueron exitosos)",
            
            f"Ingresar el correo '{test_email}' en el campo de email",
            f"Ingresar la contraseña '{test_password}' en el campo de contraseña",
            f"Ingresar nuevamente '{test_password}' en el campo de confirmación de contraseña",

            "Marcar el checkbox de aceptación de términos y condiciones, si no está visible puedes hacer scroll down",

            ## Step 4: Submit and verify email sent
            "Envía el formulario desde una opción de crear cuenta o similar",
            "Verificar que se muestra la pantalla para ingresar el código de verificación",

            ## Step 5: Email verification (AC-003.4)
            f"Obtener el código de verificación del correo '{test_email}' usando get_confirmation_code",
            "Ingresar el código de verificación de 4 dígitos en el campo correspondiente",
            "Envía el formulario para validar el código tocando el botón de confirmar o validar código",
#
            ## Step 6: Complete profile (AC-003.5)
            "Esperar a ver la pantalla para completar el perfil",
            "Ingresar nombre 'TestUser' en el campo de nombre",
            "Ingresar apellido 'Demo' en el campo de apellido",
            "Envía el formulario Tocando el botón de completar registro o finalizar",
#
            ## Step 7: Verify successful registration (AC-003.6)
            "Verificar que se muestra la pantalla principal del cliente (home)",
            "Verificar que la sesión está iniciada correctamente",
        ]#

        success = runner.run_test_plan(test_plan)
        assert success, "El flujo de registro no se completó exitosamente"


@pytest.mark.integration
class TestSignUpValidations:
    """
    Test class for AC-003: Field validations

    Tests negative scenarios and validation rules.
    """

    def test_sign_up_duplicate_email(self, driver_setup):
        """
        AC-003.2: Validate duplicate email detection

        Verifies that the system shows an error when attempting
        to register with an already registered email.
        """
        objective = (
            "Validar AC-003.2: verificar que el sistema detecta y muestra error "
            "cuando se intenta registrar con un correo electrónico ya existente"
        )

        runner = QAIV2TestRunner(driver=driver_setup, objective=objective)

        # Use the default test email which should already exist
        test_email = Config.TEST_USER_EMAIL
        test_password = Config.TEST_USER_PASSWORD or "Test123!"

        test_plan = [
            # Navigate to sign-up
            # Navigate to sign-up using HumanAction (lambda) for faster startup
            lambda tools: tools.activate_app("com.imagineapps.gofixiicliente"),
            "Esperar a ver la pantalla de inicio de sesión",
            "Tocar el enlace o botón para crear una cuenta nueva",

            # Attempt registration with existing email
            "Esperar a ver la pantalla de registro",
            f"Ingresar el correo '{test_email}' en el campo de email",
            f"Ingresar la contraseña '{test_password}' en el campo de contraseña",
            f"Ingresar nuevamente '{test_password}' en el campo de confirmación de contraseña",
            "Hacer scroll down si es necesario para ver el campo de fecha de nacimiento",
            "Tocar el campo de entrada de fecha de nacimiento (el input EditText, NO el label) para abrir el selector de fecha",
            "En el selector de fecha, cambiar el año hasta que sea 2006 o menor usando touch y scroll según sea necesario",
            "Seleccionar el día 1 y mes enero en el selector de fecha",
            "Tocar el botón de confirmar/aceptar la fecha en el selector (debe estar habilitado si los pasos anteriores fueron exitosos)",
            "Hacer scroll down si es necesario para ver el checkbox de términos",
            "Marcar el checkbox de aceptación de términos y condiciones",
            "Tocar el botón 'Crea una cuenta' o similar",

            # Verify error message
            "Verificar que se muestra el mensaje 'El correo electrónico ya se encuentra registrado' o similar",
        ]

        success = runner.run_test_plan(test_plan)
        assert success, "La validación de email duplicado no funcionó correctamente"

    def test_sign_up_password_mismatch(self, driver_setup):
        """
        AC-003.1: Validate password confirmation mismatch

        Verifies that the system detects when password and
        confirmation don't match.
        """
        objective = (
            "Validar AC-003.1: verificar que el sistema detecta cuando "
            "la contraseña y su confirmación no coinciden"
        )

        runner = QAIV2TestRunner(driver=driver_setup, objective=objective)

        import time
        timestamp = int(time.time())
        test_email = f"test.mismatch.{timestamp}@demo.com"

        test_plan = [
            # Navigate to sign-up
            # Navigate to sign-up using HumanAction (lambda) for faster startup
            lambda tools: tools.activate_app("com.imagineapps.gofixiicliente"),
            "Esperar a ver la pantalla de inicio de sesión",
            "Tocar el enlace o botón para crear una cuenta nueva",

            # Fill form with mismatched passwords
            "Esperar a ver la pantalla de registro",
            f"Ingresar el correo '{test_email}' en el campo de email",
            "Ingresar la contraseña 'Password123' en el campo de contraseña",
            "Ingresar 'DifferentPass456' en el campo de confirmación de contraseña",

            # Verify validation error appears
            "Verificar que se muestra un mensaje de error indicando que las contraseñas no coinciden",
            "Verificar que el botón 'Crea una cuenta' está deshabilitado o no permite continuar",
        ]

        success = runner.run_test_plan(test_plan)
        assert success, "La validación de coincidencia de contraseñas no funcionó correctamente"

    def test_sign_up_terms_required(self, driver_setup):
        """
        AC-003.3: Validate terms acceptance is mandatory

        Verifies that the "Create Account" button is disabled
        until terms and conditions are accepted.
        """
        objective = (
            "Validar AC-003.3: verificar que el checkbox de términos y condiciones "
            "es obligatorio para habilitar el botón de crear cuenta"
        )

        runner = QAIV2TestRunner(driver=driver_setup, objective=objective)

        import time
        timestamp = int(time.time())
        test_email = f"test.terms.{timestamp}@demo.com"
        test_password = Config.TEST_USER_PASSWORD or "Test123!"

        test_plan = [
            # Navigate to sign-up
            # Navigate to sign-up using HumanAction (lambda) for faster startup
            lambda tools: tools.activate_app("com.imagineapps.gofixiicliente"),
            "Esperar a ver la pantalla de inicio de sesión",
            "Tocar el enlace o botón para crear una cuenta nueva",

            # Fill all fields EXCEPT terms checkbox
            "Esperar a ver la pantalla de registro",
            f"Ingresar el correo '{test_email}' en el campo de email",
            f"Ingresar la contraseña '{test_password}' en el campo de contraseña",
            f"Ingresar nuevamente '{test_password}' en el campo de confirmación de contraseña",
            "Tocar el campo de fecha de nacimiento para abrir el selector",
            "Seleccionar la fecha '01/01/1990' en el selector de fecha (día 1, mes enero, año 1990)",
            "Confirmar la selección de fecha",

            # Verify button is disabled without terms acceptance
            "Verificar que el botón 'Crea una cuenta' está deshabilitado o no permite continuar sin marcar términos",

            # Now accept terms and verify button becomes enabled
            "Marcar el checkbox de aceptación de términos y condiciones",
            "Verificar que el botón 'Crea una cuenta' ahora está habilitado",
        ]

        success = runner.run_test_plan(test_plan)
        assert success, "La validación de términos obligatorios no funcionó correctamente"
