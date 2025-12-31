"""
Configuración de pytest y fixtures para Appium.
"""

import pytest
from appium import webdriver
from appium.options.android import UiAutomator2Options

from src.config import Config


@pytest.fixture(scope="function")
def driver_setup():
    """
    Fixture que inicializa y cierra el driver de Appium.

    Yields:
        Driver de Appium configurado
    """
    # Validar configuración
    is_valid, error_msg = Config.validate()
    if not is_valid:
        pytest.skip(f"Configuración inválida: {error_msg}")

    # Configurar capabilities
    capabilities = Config.get_appium_capabilities()

    # Crear opciones de Android
    options = UiAutomator2Options()
    for key, value in capabilities.items():
        options.set_capability(key, value)

    # Inicializar driver
    driver = None
    try:
        driver = webdriver.Remote(
            command_executor=Config.APPIUM_SERVER_URL,
            options=options,
        )
        driver.implicitly_wait(Config.IMPLICIT_WAIT)

        yield driver

    except Exception as e:
        pytest.fail(f"Error inicializando driver de Appium: {str(e)}")

    finally:
        # Cerrar driver
        if driver:
            try:
                driver.quit()
            except Exception:
                pass  # Ignorar errores al cerrar

