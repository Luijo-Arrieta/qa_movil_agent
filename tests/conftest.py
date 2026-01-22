"""
Configuración base de pytest compartida para todos los tests.

Este archivo contiene:
- Markers personalizados
- Configuración de logging (consola + archivo)
- Plugins compartidos
- Fixtures compartidas de Appium (driver_setup, Allure helpers) - para tests de integración y specs

Los fixtures específicos están en:
- tests/unit/conftest.py        → Fixtures para tests unitarios (NO usan fixtures de Appium - todo mockeado)
- tests/specs/conftest.py       → Solo para re-exportar fixtures compartidas (legacy, puede eliminarse)
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
from src.agent_tools import AppiumSkills
from src.ui_parser import UIParser
from src.validators import validate_allowed_apps_installed


# Directorio base para logs
LOGS_DIR = Path(__file__).parent.parent / "reports" / "logs"


class SafeFileHandler(logging.FileHandler):
    """
    Handler de logging que ignora errores cuando el archivo está cerrado.
    Esto previene errores cuando objetos intentan escribir logs después
    de que pytest ya cerró los handlers (ej: destructores de httpx/openai).
    También maneja correctamente el encoding UTF-8 para emojis y caracteres especiales.
    """
    def emit(self, record):
        try:
            # Verificar si el stream está disponible y abierto
            if self.stream is None or self.stream.closed:
                return
            
            # Usar el método padre que ya maneja el encoding correctamente
            super().emit(record)
        except (ValueError, OSError, UnicodeEncodeError, AttributeError, RuntimeError):
            # Ignorar errores de I/O cuando el archivo está cerrado
            # o problemas de encoding, o cuando el stream no está disponible
            # RuntimeError puede ocurrir cuando el handler está siendo cerrado
            pass
        except Exception:
            # Capturar cualquier otro error inesperado para evitar que se propague
            # Esto previene que errores de logging rompan la ejecución del test
            pass


def _setup_file_logging():
    """
    Configura logging a archivo con timestamp.
    
    Los logs se almacenan en reports/logs/ con formato:
    - pytest_YYYYMMDD_HHMMSS.log (log completo de cada ejecución)
    - latest.log (symlink/copia del último log para fácil acceso)
    """
    # Crear directorio de logs si no existe
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    
    # Generar nombre de archivo con timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_filename = f"pytest_{timestamp}.log"
    log_filepath = LOGS_DIR / log_filename
    latest_log_path = LOGS_DIR / "latest.log"
    
    # Configurar el root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    
    # Crear handler para archivo con encoding UTF-8
    # Usar SafeFileHandler para ignorar errores cuando el archivo está cerrado
    # y manejar correctamente emojis y caracteres especiales
    file_handler = SafeFileHandler(
        log_filepath, 
        mode='w', 
        encoding='utf-8',
        errors='replace'  # Reemplazar caracteres problemáticos en lugar de fallar
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s.%(msecs)03d - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    ))
    root_logger.addHandler(file_handler)
    
    # Crear/actualizar latest.log como copia del archivo actual
    # (En Windows los symlinks requieren permisos especiales)
    try:
        if latest_log_path.exists():
            latest_log_path.unlink()
        # En lugar de symlink, guardamos la referencia al archivo actual
        latest_log_path.write_text(f"# Latest log: {log_filename}\n# Full path: {log_filepath}\n", encoding='utf-8')
    except Exception:
        pass  # No es crítico si falla
    
    return log_filepath


# Variable global para almacenar la ruta del log actual
_current_log_file = None


# Configurar logging con formato detallado (consola)
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s.%(msecs)03d - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# Silenciar loggers ruidosos que imprimen datos base64 de screenshots
logging.getLogger("selenium.webdriver.remote.remote_connection").setLevel(logging.WARNING)
logging.getLogger("urllib3.connectionpool").setLevel(logging.WARNING)

# Silenciar logs verbosos del cliente OpenAI (requests/responses HTTP)
logging.getLogger("openai._base_client").setLevel(logging.WARNING)

# Silenciar loggers de httpcore/httpx que intentan escribir después del cierre
# Estos loggers causan errores cuando intentan escribir después de que pytest cierra los handlers
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore.trace").setLevel(logging.WARNING)
logging.getLogger("httpcore.connection").setLevel(logging.WARNING)
logging.getLogger("httpcore.connection_pool").setLevel(logging.WARNING)

# Silenciar loggers de httpcore/httpx que intentan escribir después del cierre
# Estos loggers causan errores cuando intentan escribir después de que pytest cierra los handlers
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore.trace").setLevel(logging.WARNING)
logging.getLogger("httpcore.connection").setLevel(logging.WARNING)
logging.getLogger("httpcore.connection_pool").setLevel(logging.WARNING)


def pytest_configure(config):
    """
    Registrar markers personalizados y configurar logging a archivo.
    
    Los logs se almacenan en: reports/logs/pytest_YYYYMMDD_HHMMSS.log
    """
    global _current_log_file
    
    # Configurar logging a archivo
    _current_log_file = _setup_file_logging()
    
    # Log inicial con información de la sesión
    logger = logging.getLogger(__name__)
    logger.info("=" * 70)
    logger.info("PYTEST SESSION STARTED")
    logger.info(f"Log file: {_current_log_file}")
    logger.info("=" * 70)
    
    # Registrar markers
    config.addinivalue_line(
        "markers", "unit: Tests unitarios (sin Appium, rápidos)"
    )
    config.addinivalue_line(
        "markers", "integration: Tests de integración (requieren Appium + dispositivo)"
    )
    config.addinivalue_line(
        "markers", "slow: Tests lentos o de larga duración"
    )


def pytest_unconfigure(config):
    """
    Log al finalizar la sesión de pytest.
    Los handlers se cierran automáticamente al salir del proceso.
    SafeFileHandler ignora errores si objetos intentan escribir después.
    """
    # Silenciar completamente los loggers problemáticos antes de cerrar
    # Esto previene que intenten escribir después del cierre
    problem_loggers = [
        "httpcore",
        "httpx", 
        "httpcore.trace",
        "httpcore.connection",
        "httpcore.connection_pool",
        "openai",
    ]
    for logger_name in problem_loggers:
        logger_obj = logging.getLogger(logger_name)
        logger_obj.setLevel(logging.CRITICAL)  # Solo errores críticos
        logger_obj.disabled = True  # Deshabilitar completamente
    
    logger = logging.getLogger(__name__)
    try:
        logger.info("=" * 70)
        logger.info("PYTEST SESSION FINISHED")
        if _current_log_file:
            logger.info(f"Log saved to: {_current_log_file}")
        logger.info("=" * 70)
    except Exception:
        pass  # Ignorar errores si el handler ya está cerrado
    
    # Los handlers se cerrarán automáticamente cuando el proceso termine
    # SafeFileHandler previene errores si objetos intentan escribir después


@pytest.fixture(scope="session")
def log_file_path():
    """
    Fixture que retorna la ruta del archivo de log actual.
    Útil para tests que necesitan adjuntar el log al reporte.
    """
    return _current_log_file


# =============================================================================
# Fixtures compartidas de Appium (para tests de integración y specs)
# =============================================================================
# NOTA: Los tests unitarios NO deben usar estas fixtures - todo está mockeado
# =============================================================================

logger_appium = logging.getLogger(__name__)


def check_appium_server():
    """Verifica que el servidor de Appium esté disponible."""
    logger_appium.info("=" * 70)
    logger_appium.info("CONFTEST: Verificando disponibilidad del servidor Appium...")
    logger_appium.info("=" * 70)
    
    appium_url = Config.APPIUM_SERVER_URL
    status_url = f"{appium_url}/status"
    
    try:
        response = requests.get(status_url, timeout=5)
        
        if response.status_code == 200:
            try:
                status_data = response.json()
                if 'value' in status_data and 'build' in status_data.get('value', {}):
                    build_info = status_data['value']['build']
            except Exception:
                pass
            
            logger_appium.info(f"CONFTEST: ✓ Appium Server disponible en {appium_url}")
            return True
        else:
            logger_appium.warning(f"CONFTEST: ⚠ Appium Server responde con código {response.status_code}")
            logger_appium.warning(f"CONFTEST: Response body: {response.text[:200]}")
            return False
            
    except requests.exceptions.ConnectionError as e:
        logger_appium.error(f"CONFTEST ERROR: No se puede conectar a Appium Server")
        logger_appium.error(f"CONFTEST ERROR: URL: {appium_url}")
        logger_appium.error(f"CONFTEST ERROR: ConnectionError: {e}")
        logger_appium.error("CONFTEST DIAGNÓSTICO: Verifica que:")
        logger_appium.error("  1. Appium Server esté corriendo")
        logger_appium.error("  2. El puerto (default 4723) esté libre")
        logger_appium.error("  3. El firewall permita conexiones locales")
        logger_appium.error(f"  Comando sugerido: appium --use-plugins=all")
        return False
        
    except requests.exceptions.Timeout as e:
        logger_appium.error(f"CONFTEST ERROR: Timeout conectando a Appium Server")
        logger_appium.error(f"CONFTEST ERROR: URL: {appium_url}")
        logger_appium.error(f"CONFTEST ERROR: {e}")
        return False
        
    except requests.exceptions.RequestException as e:
        logger_appium.error(f"CONFTEST ERROR: Error de request: {type(e).__name__}: {e}")
        return False


@pytest.fixture(scope="function")
def driver_setup():
    """
    Fixture que inicializa y cierra el driver de Appium.
    
    Comportamiento según configuración:
    - Si Config.ANDROID_APP_PACKAGE está definido y AUTO_LAUNCH_MAIN_APP=true →
      se considera un proyecto single-app y se abre automáticamente la app
      principal al inicio (modo cómodo).
    - En otros casos (multi-app o AUTO_LAUNCH_MAIN_APP=false) →
      el usuario/test debe usar explícitamente activate_app() de AppiumSkills.

    Yields:
        Driver de Appium configurado
    """
    fixture_start_time = datetime.now()
    
    logger_appium.info("")
    logger_appium.info("█" * 80)
    logger_appium.info("█  CONFTEST: INICIANDO FIXTURE driver_setup")
    logger_appium.info("█" * 80)
    logger_appium.info("")
    
    # ══════════════════════════════════════════════════════════════════════════
    # FASE 1: Verificar Appium Server
    # ══════════════════════════════════════════════════════════════════════════
    logger_appium.info("CONFTEST: FASE 1 - Verificando Appium Server...")
    if not check_appium_server():
        skip_msg = (f"Appium Server no está disponible en {Config.APPIUM_SERVER_URL}. "
                   f"Asegúrate de iniciar Appium con: appium --use-plugins=all")
        logger_appium.error(f"CONFTEST: {skip_msg}")
        pytest.skip(skip_msg)

    # ══════════════════════════════════════════════════════════════════════════
    # FASE 2: Configurar capabilities
    # ══════════════════════════════════════════════════════════════════════════
    logger_appium.info("")
    logger_appium.info("CONFTEST: FASE 2 - Configurando capabilities...")
    
    # Imprimir configuración completa
    Config.debug_print_config()
    
    capabilities = Config.get_appium_capabilities()

    # ══════════════════════════════════════════════════════════════════════════
    # FASE 3: Crear opciones de Android
    # ══════════════════════════════════════════════════════════════════════════
    logger_appium.info("")
    logger_appium.info("CONFTEST: FASE 3 - Creando UiAutomator2Options...")
    options = UiAutomator2Options()
    for key, value in capabilities.items():
        options.set_capability(key, value)
    logger_appium.info("CONFTEST: ✓ Options creadas")

    # ══════════════════════════════════════════════════════════════════════════
    # FASE 4: Inicializar driver
    # ══════════════════════════════════════════════════════════════════════════
    logger_appium.info("")
    logger_appium.info("CONFTEST: FASE 4 - Inicializando driver de Appium...")
    driver = None
    driver_init_start = datetime.now()
    
    try:
        logger_appium.info(f"CONFTEST: 🚀 Conectando a {Config.APPIUM_SERVER_URL}...")
        driver = webdriver.Remote(
            command_executor=Config.APPIUM_SERVER_URL,
            options=options,
        )
        
        driver_init_elapsed = (datetime.now() - driver_init_start).total_seconds()
        logger_appium.info(f"CONFTEST: ✓ Driver creado en {driver_init_elapsed:.2f}s")
        logger_appium.info(f"CONFTEST: Session ID: {driver.session_id}")
        
        # Configurar implicit wait
        logger_appium.debug(f"CONFTEST: Configurando implicit_wait={Config.IMPLICIT_WAIT}s...")
        driver.implicitly_wait(Config.IMPLICIT_WAIT)
        logger_appium.debug("CONFTEST: ✓ Implicit wait configurado")
        
        # ══════════════════════════════════════════════════════════════════════
        # FASE 5: Obtener información del dispositivo
        # ══════════════════════════════════════════════════════════════════════
        logger_appium.info("")
        logger_appium.info("CONFTEST: FASE 5 - Obteniendo información del dispositivo...")
        try:
            # Intentar obtener info del dispositivo
            device_time = driver.get_device_time()
            logger_appium.info(f"CONFTEST: Device time: {device_time}")
            
            # Obtener dimensiones de pantalla
            window_size = driver.get_window_size()
            logger_appium.info(f"CONFTEST: Window size: {window_size['width']}x{window_size['height']}")
            
            # Obtener info de la sesión
            if hasattr(driver, 'capabilities'):
                caps = driver.capabilities
                logger_appium.info(f"CONFTEST: Platform: {caps.get('platformName', 'N/A')}")
                logger_appium.info(f"CONFTEST: Platform Version: {caps.get('platformVersion', 'N/A')}")
                logger_appium.info(f"CONFTEST: Device Name: {caps.get('deviceName', 'N/A')}")
                logger_appium.info(f"CONFTEST: Device UDID: {caps.get('deviceUDID', 'N/A')}")
            
            logger_appium.info(f"CONFTEST: ✓ Driver inicializado correctamente")
            
        except Exception as e:
            logger_appium.warning(f"CONFTEST WARNING: No se pudo obtener toda la información del dispositivo: {e}")
            logger_appium.debug(f"CONFTEST: Traceback:\n{traceback.format_exc()}")
            # No es crítico, el driver puede estar bien aunque falle esto

        # ══════════════════════════════════════════════════════════════════════
        # FASE 6: Validar que apps permitidas estén instaladas
        # ══════════════════════════════════════════════════════════════════════
        logger_appium.info("")
        logger_appium.info("CONFTEST: FASE 6 - Validando apps permitidas...")
        try:
            validate_allowed_apps_installed(driver)
            logger_appium.info("CONFTEST: ✓ Validación de apps completada")
        except ValueError as e:
            logger_appium.error(f"CONFTEST ERROR: Validación de apps falló: {e}")
            raise
        except Exception as e:
            logger_appium.error(f"CONFTEST ERROR: Error inesperado en validación de apps: {e}")
            logger_appium.debug(f"CONFTEST: Traceback:\n{traceback.format_exc()}")
            raise

        # ══════════════════════════════════════════════════════════════════════
        # FASE 7 (opcional): Abrir app principal en modo single-app
        # ══════════════════════════════════════════════════════════════════════
        if Config.ANDROID_APP_PACKAGE and Config.AUTO_LAUNCH_MAIN_APP:
            logger_appium.info("")
            logger_appium.info("CONFTEST: FASE 7 - AUTO_LAUNCH_MAIN_APP activo, abriendo app principal...")
            try:
                ui_parser = UIParser()
                app_tools = AppiumSkills(driver, ui_parser)
                result = app_tools.activate_app(Config.ANDROID_APP_PACKAGE)
                logger_appium.info(f"CONFTEST: Resultado auto-launch app principal: {result}")
            except Exception as e:
                logger_appium.warning(f"CONFTEST WARNING: No se pudo auto-lanzar app principal '{Config.ANDROID_APP_PACKAGE}': {e}")
                logger_appium.debug(f"CONFTEST: Traceback:\n{traceback.format_exc()}")

        fixture_setup_elapsed = (datetime.now() - fixture_start_time).total_seconds()
        logger_appium.info("")
        logger_appium.info(f"CONFTEST: ✅ Fixture setup completado en {fixture_setup_elapsed:.2f}s")
        logger_appium.info("=" * 80)
        logger_appium.info("")
        
        yield driver

    except Exception as e:
        driver_init_elapsed = (datetime.now() - driver_init_start).total_seconds()
        logger_appium.error("")
        logger_appium.error("╔" + "═" * 78 + "╗")
        logger_appium.error("║  CONFTEST ERROR: Fallo al inicializar driver de Appium")
        logger_appium.error("╚" + "═" * 78 + "╝")
        logger_appium.error(f"CONFTEST ERROR: {type(e).__name__}: {str(e)}")
        logger_appium.error(f"CONFTEST ERROR: Tiempo transcurrido: {driver_init_elapsed:.2f}s")
        logger_appium.error(f"CONFTEST ERROR: Traceback:\n{traceback.format_exc()}")
        
        # Diagnóstico detallado
        logger_appium.error("")
        logger_appium.error("CONFTEST DIAGNÓSTICO: Posibles causas y soluciones:")
        logger_appium.error("  1. Appium Server no está corriendo")
        logger_appium.error("     → Ejecuta: appium --use-plugins=all")
        logger_appium.error("")
        logger_appium.error("  2. Dispositivo/emulador no conectado")
        logger_appium.error("     → Ejecuta: adb devices")
        logger_appium.error("     → Debe mostrar tu dispositivo como 'device' (no 'offline')")
        logger_appium.error("")
        logger_appium.error("  3. Capabilities incorrectas")
        logger_appium.error(f"     → Device Name: {capabilities.get('appium:deviceName', 'NO CONFIGURADO')}")
        logger_appium.error(f"     → UDID: {capabilities.get('appium:udid', 'NO CONFIGURADO')}")
        logger_appium.error("")
        logger_appium.error("  4. UiAutomator2 no instalado correctamente")
        logger_appium.error("     → Ejecuta: appium driver install uiautomator2")
        
        pytest.fail(f"Error inicializando driver de Appium: {str(e)}")

    finally:
        # ══════════════════════════════════════════════════════════════════════
        # FASE FINAL: Limpieza de apps usadas y cierre de driver
        # ══════════════════════════════════════════════════════════════════════
        if driver:
            logger_appium.info("")
            logger_appium.info("CONFTEST: FASE FINAL - Limpiando apps usadas y cerrando driver...")

            # 1) Determinar apps usadas durante la prueba (tracking en AppiumSkills)
            used_packages = AppiumSkills.get_used_app_packages_for_driver(driver)

            # Si no se registró nada pero hay app principal configurada, asumir single-app
            if not used_packages and Config.ANDROID_APP_PACKAGE:
                used_packages.add(Config.ANDROID_APP_PACKAGE)

            # 2) Limpiar storage de cada app de negocio (evitar system apps)
            if used_packages:
                device_udid = Config.ANDROID_UDID or Config.ANDROID_DEVICE_NAME
                logger_appium.info(f"CONFTEST: Apps usadas a limpiar: {used_packages}")
                for app_package in used_packages:
                    # No tocar system apps Android
                    if app_package.startswith("com.android"):
                        logger_appium.info(f"CONFTEST: Saltando limpieza de system app: {app_package}")
                        continue

                    try:
                        logger_appium.info(f"CONFTEST: Reseteando storage de la app: {app_package}...")
                        import subprocess
                        cmd = ["adb", "-s", device_udid, "shell", "pm", "clear", app_package]
                        result = subprocess.run(
                            cmd,
                            capture_output=True,
                            text=True,
                            timeout=15,
                        )
                        if result.returncode == 0:
                            logger_appium.info(f"CONFTEST: Storage reseteado para: {app_package}")
                        else:
                            logger_appium.warning(
                                f"CONFTEST: Error al resetear storage para {app_package}: {result.stderr}"
                            )
                    except subprocess.TimeoutExpired:
                        logger_appium.warning(f"CONFTEST: Timeout al resetear storage para {app_package}")
                    except FileNotFoundError:
                        logger_appium.warning(
                            "CONFTEST: ADB no encontrado en PATH, no se puede resetear storage"
                        )
                    except Exception as e:
                        logger_appium.warning(f"CONFTEST: Error ejecutando ADB para {app_package}: {e}")

            # Limpiar tracking de apps usadas para este driver
            AppiumSkills.clear_used_app_packages_for_driver(driver)

            # 3) Cerrar driver
            try:
                session_id = driver.session_id
                logger_appium.info(f"CONFTEST: Cerrando session: {session_id}")
                driver.quit()
                logger_appium.info("CONFTEST: Driver cerrado correctamente")
            except Exception as e:
                logger_appium.warning(f"CONFTEST WARNING: Error al cerrar driver: {e}")
                logger_appium.debug(f"CONFTEST: Traceback:\n{traceback.format_exc()}")
        
        total_elapsed = (datetime.now() - fixture_start_time).total_seconds()
        logger_appium.info(f"CONFTEST: Tiempo total del fixture: {total_elapsed:.2f}s")
        logger_appium.info("")


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
        logger_appium.info(f"📸 Screenshot adjuntado a Allure: {name}")
    except Exception as e:
        logger_appium.warning(f"⚠ No se pudo capturar screenshot: {e}")


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
        logger_appium.info(f"📄 Page source XML adjuntado a Allure: {name}")
    except Exception as e:
        logger_appium.warning(f"⚠ No se pudo capturar page source: {e}")


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
                logger_appium.info("📸 Screenshot y XML de fallo adjuntados automáticamente")
            except Exception as e:
                logger_appium.warning(f"⚠ No se pudo capturar evidencia de fallo: {e}")
