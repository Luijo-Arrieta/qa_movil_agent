"""
Configuración base de pytest compartida para todos los tests.

Este archivo contiene:
- Markers personalizados
- Configuración de logging (consola + archivo)
- Plugins compartidos

Los fixtures específicos están en:
- tests/unit/conftest.py     → Fixtures para tests unitarios
- tests/specs/conftest.py    → Fixtures para tests E2E (driver_setup, Allure)
"""

import logging
from datetime import datetime
from pathlib import Path

import pytest


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
