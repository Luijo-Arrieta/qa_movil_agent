"""
Configuración de pytest y fixtures para Appium.
Incluye integración con Allure para reportería y screenshots.
"""

import logging
from datetime import datetime
from pathlib import Path

import allure
import pytest
import requests
from appium import webdriver
from appium.options.android import UiAutomator2Options

from src.config import Config

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def check_appium_server():
    """Verifica que el servidor de Appium esté disponible."""
    try:
        response = requests.get(f"{Config.APPIUM_SERVER_URL}/status", timeout=5)
        if response.status_code == 200:
            logger.info(f"✓ Appium Server está disponible en {Config.APPIUM_SERVER_URL}")
            return True
        else:
            logger.warning(f"⚠ Appium Server responde con código {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        logger.error(f"✗ No se puede conectar a Appium Server en {Config.APPIUM_SERVER_URL}: {e}")
        return False


@pytest.fixture(scope="function")
def driver_setup():
    """
    Fixture que inicializa y cierra el driver de Appium.

    Yields:
        Driver de Appium configurado
    """
    # Verificar que Appium Server esté disponible
    if not check_appium_server():
        pytest.skip(f"Appium Server no está disponible en {Config.APPIUM_SERVER_URL}. "
                   f"Asegúrate de iniciar Appium con: appium --use-plugins=all")

    # Configurar capabilities
    capabilities = Config.get_appium_capabilities()
    logger.info(f"📱 Configurando Appium con capabilities:")
    for key, value in capabilities.items():
        logger.info(f"   {key}: {value}")

    # Crear opciones de Android
    options = UiAutomator2Options()
    for key, value in capabilities.items():
        options.set_capability(key, value)

    # Inicializar driver
    driver = None
    try:
        logger.info("🚀 Inicializando driver de Appium...")
        driver = webdriver.Remote(
            command_executor=Config.APPIUM_SERVER_URL,
            options=options,
        )
        driver.implicitly_wait(Config.IMPLICIT_WAIT)
        
        # Obtener información del dispositivo
        try:
            device_info = driver.get_device_time()
            logger.info(f"✓ Driver inicializado correctamente")
            logger.info(f"   Dispositivo: {capabilities.get('appium:deviceName', 'N/A')}")
            logger.info(f"   App Package: {capabilities.get('appium:appPackage', 'N/A')}")
            logger.info(f"   App Path: {capabilities.get('appium:app', 'N/A')}")
        except Exception as e:
            logger.warning(f"⚠ No se pudo obtener información del dispositivo: {e}")

        yield driver

    except Exception as e:
        logger.error(f"✗ Error inicializando driver de Appium: {str(e)}")
        logger.error(f"   Verifica que:")
        logger.error(f"   1. Appium Server esté corriendo")
        logger.error(f"   2. El dispositivo/emulador esté conectado (adb devices)")
        logger.error(f"   3. Las capabilities estén correctamente configuradas")
        pytest.fail(f"Error inicializando driver de Appium: {str(e)}")

    finally:
        # Cerrar driver
        if driver:
            try:
                logger.info("🔒 Cerrando driver de Appium...")
                driver.quit()
                logger.info("✓ Driver cerrado correctamente")
            except Exception as e:
                logger.warning(f"⚠ Error al cerrar driver: {e}")


# =============================================================================
# Funciones Helper para Allure - Uso en cualquier test
# =============================================================================

def allure_attach_screenshot(driver, name: str = None) -> None:
    """
    Captura screenshot y lo adjunta al reporte de Allure.

    Args:
        driver: Instancia del driver de Appium
        name: Nombre opcional para el screenshot (default: timestamp)

    Uso en tests:
        from tests.conftest import allure_attach_screenshot
        allure_attach_screenshot(driver, "login_screen")
    """
    if name is None:
        name = f"screenshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    try:
        screenshot = driver.get_screenshot_as_png()
        allure.attach(
            screenshot,
            name=name,
            attachment_type=allure.attachment_type.PNG
        )
        logger.info(f"📸 Screenshot adjuntado a Allure: {name}")
    except Exception as e:
        logger.warning(f"⚠ No se pudo capturar screenshot: {e}")


def allure_attach_page_source(driver, name: str = None) -> None:
    """
    Captura el XML del page_source y lo adjunta al reporte de Allure.

    Args:
        driver: Instancia del driver de Appium
        name: Nombre opcional para el XML (default: timestamp)

    Uso en tests:
        from tests.conftest import allure_attach_page_source
        allure_attach_page_source(driver, "login_xml")
    """
    if name is None:
        name = f"page_source_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    try:
        page_source = driver.page_source
        allure.attach(
            page_source,
            name=name,
            attachment_type=allure.attachment_type.XML
        )
        logger.info(f"📄 Page source XML adjuntado a Allure: {name}")
    except Exception as e:
        logger.warning(f"⚠ No se pudo capturar page source: {e}")


def allure_attach_debug_snapshot(driver, name: str = None) -> None:
    """
    Captura tanto screenshot como page_source y los adjunta a Allure.
    Función de conveniencia para debugging completo.

    Args:
        driver: Instancia del driver de Appium
        name: Nombre base para los archivos (default: timestamp)

    Uso en tests:
        from tests.conftest import allure_attach_debug_snapshot
        allure_attach_debug_snapshot(driver, "after_login")
    """
    if name is None:
        name = datetime.now().strftime('%Y%m%d_%H%M%S')

    allure_attach_screenshot(driver, f"{name}_screenshot")
    allure_attach_page_source(driver, f"{name}_xml")


# =============================================================================
# Hooks de Allure para screenshots automáticos en fallos
# =============================================================================

@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """
    Hook que captura screenshot automáticamente cuando un test falla.
    Solo aplica a tests que tienen acceso al driver.
    """
    outcome = yield
    report = outcome.get_result()

    # Solo en fase de ejecución (call) y si falló
    if report.when == "call" and report.failed:
        # Intentar obtener el driver del test
        driver = None

        # Buscar driver en fixtures del test
        if hasattr(item, "funcargs"):
            driver = item.funcargs.get("driver_setup")

        if driver:
            try:
                # Adjuntar screenshot del fallo
                screenshot = driver.get_screenshot_as_png()
                allure.attach(
                    screenshot,
                    name="failure_screenshot",
                    attachment_type=allure.attachment_type.PNG
                )

                # Adjuntar page source del fallo
                page_source = driver.page_source
                allure.attach(
                    page_source,
                    name="failure_page_source",
                    attachment_type=allure.attachment_type.XML
                )
                logger.info("📸 Screenshot y XML de fallo adjuntados automáticamente")
            except Exception as e:
                logger.warning(f"⚠ No se pudo capturar evidencia de fallo: {e}")

