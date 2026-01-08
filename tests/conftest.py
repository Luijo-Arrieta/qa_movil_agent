"""
Configuración de pytest y fixtures para Appium.
Incluye integración con Allure para reportería y screenshots.
"""

import logging
import traceback
from datetime import datetime
from pathlib import Path

import allure
import pytest
import requests
from appium import webdriver
from appium.options.android import UiAutomator2Options

from src.config import Config

# Configurar logging con formato detallado
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s.%(msecs)03d - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


def check_appium_server():
    """Verifica que el servidor de Appium esté disponible."""
    logger.info("=" * 70)
    logger.info("CONFTEST: Verificando disponibilidad del servidor Appium...")
    logger.info("=" * 70)
    
    appium_url = Config.APPIUM_SERVER_URL
    status_url = f"{appium_url}/status"
    
    logger.debug(f"CONFTEST: URL del servidor: {appium_url}")
    logger.debug(f"CONFTEST: URL de status: {status_url}")
    
    try:
        logger.debug("CONFTEST: Enviando request GET a /status...")
        response = requests.get(status_url, timeout=5)
        
        logger.debug(f"CONFTEST: Response status code: {response.status_code}")
        logger.debug(f"CONFTEST: Response headers: {dict(response.headers)}")
        
        if response.status_code == 200:
            # Intentar parsear la respuesta JSON para más info
            try:
                status_data = response.json()
                logger.debug(f"CONFTEST: Status response: {status_data}")
                
                # Extraer info del servidor si está disponible
                if 'value' in status_data and 'build' in status_data.get('value', {}):
                    build_info = status_data['value']['build']
                    logger.info(f"CONFTEST: Appium version: {build_info.get('version', 'N/A')}")
            except Exception:
                pass
            
            logger.info(f"CONFTEST: ✓ Appium Server disponible en {appium_url}")
            return True
        else:
            logger.warning(f"CONFTEST: ⚠ Appium Server responde con código {response.status_code}")
            logger.warning(f"CONFTEST: Response body: {response.text[:200]}")
            return False
            
    except requests.exceptions.ConnectionError as e:
        logger.error(f"CONFTEST ERROR: No se puede conectar a Appium Server")
        logger.error(f"CONFTEST ERROR: URL: {appium_url}")
        logger.error(f"CONFTEST ERROR: ConnectionError: {e}")
        logger.error("CONFTEST DIAGNÓSTICO: Verifica que:")
        logger.error("  1. Appium Server esté corriendo")
        logger.error("  2. El puerto (default 4723) esté libre")
        logger.error("  3. El firewall permita conexiones locales")
        logger.error(f"  Comando sugerido: appium --use-plugins=all")
        return False
        
    except requests.exceptions.Timeout as e:
        logger.error(f"CONFTEST ERROR: Timeout conectando a Appium Server")
        logger.error(f"CONFTEST ERROR: URL: {appium_url}")
        logger.error(f"CONFTEST ERROR: {e}")
        return False
        
    except requests.exceptions.RequestException as e:
        logger.error(f"CONFTEST ERROR: Error de request: {type(e).__name__}: {e}")
        return False


@pytest.fixture(scope="function")
def driver_setup():
    """
    Fixture que inicializa y cierra el driver de Appium.

    Yields:
        Driver de Appium configurado
    """
    fixture_start_time = datetime.now()
    
    logger.info("")
    logger.info("█" * 80)
    logger.info("█  CONFTEST: INICIANDO FIXTURE driver_setup")
    logger.info("█" * 80)
    logger.info("")
    
    # ══════════════════════════════════════════════════════════════════════════
    # FASE 1: Verificar Appium Server
    # ══════════════════════════════════════════════════════════════════════════
    logger.info("CONFTEST: FASE 1 - Verificando Appium Server...")
    if not check_appium_server():
        skip_msg = (f"Appium Server no está disponible en {Config.APPIUM_SERVER_URL}. "
                   f"Asegúrate de iniciar Appium con: appium --use-plugins=all")
        logger.error(f"CONFTEST: {skip_msg}")
        pytest.skip(skip_msg)

    # ══════════════════════════════════════════════════════════════════════════
    # FASE 2: Configurar capabilities
    # ══════════════════════════════════════════════════════════════════════════
    logger.info("")
    logger.info("CONFTEST: FASE 2 - Configurando capabilities...")
    
    # Imprimir configuración completa
    Config.debug_print_config()
    
    capabilities = Config.get_appium_capabilities()
    logger.info(f"CONFTEST: 📱 Capabilities configuradas:")
    for key, value in capabilities.items():
        # Ocultar información sensible
        display_value = value
        if "key" in key.lower() or "password" in key.lower():
            display_value = "***HIDDEN***"
        logger.info(f"CONFTEST:    {key}: {display_value}")

    # ══════════════════════════════════════════════════════════════════════════
    # FASE 3: Crear opciones de Android
    # ══════════════════════════════════════════════════════════════════════════
    logger.info("")
    logger.info("CONFTEST: FASE 3 - Creando UiAutomator2Options...")
    options = UiAutomator2Options()
    for key, value in capabilities.items():
        logger.debug(f"CONFTEST: Seteando capability: {key}={value}")
        options.set_capability(key, value)
    logger.info("CONFTEST: ✓ Options creadas")

    # ══════════════════════════════════════════════════════════════════════════
    # FASE 4: Inicializar driver
    # ══════════════════════════════════════════════════════════════════════════
    logger.info("")
    logger.info("CONFTEST: FASE 4 - Inicializando driver de Appium...")
    driver = None
    driver_init_start = datetime.now()
    
    try:
        logger.info(f"CONFTEST: 🚀 Conectando a {Config.APPIUM_SERVER_URL}...")
        driver = webdriver.Remote(
            command_executor=Config.APPIUM_SERVER_URL,
            options=options,
        )
        
        driver_init_elapsed = (datetime.now() - driver_init_start).total_seconds()
        logger.info(f"CONFTEST: ✓ Driver creado en {driver_init_elapsed:.2f}s")
        logger.info(f"CONFTEST: Session ID: {driver.session_id}")
        
        # Configurar implicit wait
        logger.debug(f"CONFTEST: Configurando implicit_wait={Config.IMPLICIT_WAIT}s...")
        driver.implicitly_wait(Config.IMPLICIT_WAIT)
        logger.debug("CONFTEST: ✓ Implicit wait configurado")
        
        # ══════════════════════════════════════════════════════════════════════
        # FASE 5: Obtener información del dispositivo/app
        # ══════════════════════════════════════════════════════════════════════
        logger.info("")
        logger.info("CONFTEST: FASE 5 - Obteniendo información del dispositivo...")
        try:
            # Intentar obtener info del dispositivo
            device_time = driver.get_device_time()
            logger.info(f"CONFTEST: Device time: {device_time}")
            
            # Obtener dimensiones de pantalla
            window_size = driver.get_window_size()
            logger.info(f"CONFTEST: Window size: {window_size['width']}x{window_size['height']}")
            
            # Obtener info de la sesión
            if hasattr(driver, 'capabilities'):
                caps = driver.capabilities
                logger.info(f"CONFTEST: Platform: {caps.get('platformName', 'N/A')}")
                logger.info(f"CONFTEST: Platform Version: {caps.get('platformVersion', 'N/A')}")
                logger.info(f"CONFTEST: Device Name: {caps.get('deviceName', 'N/A')}")
                logger.info(f"CONFTEST: Device UDID: {caps.get('deviceUDID', 'N/A')}")
                logger.info(f"CONFTEST: App Package: {caps.get('appPackage', 'N/A')}")
                logger.info(f"CONFTEST: App Activity: {caps.get('appActivity', 'N/A')}")
            
            logger.info(f"CONFTEST: ✓ Driver inicializado correctamente")
            
        except Exception as e:
            logger.warning(f"CONFTEST WARNING: No se pudo obtener toda la información del dispositivo: {e}")
            logger.debug(f"CONFTEST: Traceback:\n{traceback.format_exc()}")
            # No es crítico, el driver puede estar bien aunque falle esto

        fixture_setup_elapsed = (datetime.now() - fixture_start_time).total_seconds()
        logger.info("")
        logger.info(f"CONFTEST: ✅ Fixture setup completado en {fixture_setup_elapsed:.2f}s")
        logger.info("=" * 80)
        logger.info("")
        
        yield driver

    except Exception as e:
        driver_init_elapsed = (datetime.now() - driver_init_start).total_seconds()
        logger.error("")
        logger.error("╔" + "═" * 78 + "╗")
        logger.error("║  CONFTEST ERROR: Fallo al inicializar driver de Appium")
        logger.error("╚" + "═" * 78 + "╝")
        logger.error(f"CONFTEST ERROR: {type(e).__name__}: {str(e)}")
        logger.error(f"CONFTEST ERROR: Tiempo transcurrido: {driver_init_elapsed:.2f}s")
        logger.error(f"CONFTEST ERROR: Traceback:\n{traceback.format_exc()}")
        
        # Diagnóstico detallado
        logger.error("")
        logger.error("CONFTEST DIAGNÓSTICO: Posibles causas y soluciones:")
        logger.error("  1. Appium Server no está corriendo")
        logger.error("     → Ejecuta: appium --use-plugins=all")
        logger.error("")
        logger.error("  2. Dispositivo/emulador no conectado")
        logger.error("     → Ejecuta: adb devices")
        logger.error("     → Debe mostrar tu dispositivo como 'device' (no 'offline')")
        logger.error("")
        logger.error("  3. App no encontrada o no instalada")
        logger.error(f"     → APK Path: {capabilities.get('appium:app', 'NO CONFIGURADO')}")
        logger.error(f"     → Package: {capabilities.get('appium:appPackage', 'NO CONFIGURADO')}")
        logger.error("")
        logger.error("  4. Capabilities incorrectas")
        logger.error(f"     → Device Name: {capabilities.get('appium:deviceName', 'NO CONFIGURADO')}")
        logger.error(f"     → UDID: {capabilities.get('appium:udid', 'NO CONFIGURADO')}")
        logger.error("")
        logger.error("  5. UiAutomator2 no instalado correctamente")
        logger.error("     → Ejecuta: appium driver install uiautomator2")
        
        pytest.fail(f"Error inicializando driver de Appium: {str(e)}")

    finally:
        # ══════════════════════════════════════════════════════════════════════
        # FASE FINAL: Cerrar driver
        # ══════════════════════════════════════════════════════════════════════
        if driver:
            logger.info("")
            logger.info("CONFTEST: FASE FINAL - Cerrando driver...")
            try:
                logger.info(f"CONFTEST: 🔒 Cerrando session: {driver.session_id}")
                driver.quit()
                logger.info("CONFTEST: ✓ Driver cerrado correctamente")
            except Exception as e:
                logger.warning(f"CONFTEST WARNING: Error al cerrar driver: {e}")
                logger.debug(f"CONFTEST: Traceback:\n{traceback.format_exc()}")
        
        total_elapsed = (datetime.now() - fixture_start_time).total_seconds()
        logger.info(f"CONFTEST: Tiempo total del fixture: {total_elapsed:.2f}s")
        logger.info("")


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

