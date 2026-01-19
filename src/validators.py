"""
Módulo de validaciones del sistema.

Contiene funciones para validar configuración y estado del sistema antes de ejecutar tests.
"""

import logging
from typing import Optional
from appium.webdriver import Remote

from src.config import Config
from src.middleware_result import MiddlewareResult, MiddlewareStatus

logger = logging.getLogger(__name__)

# Importar excepciones de Selenium/Appium para identificar errores recuperables
try:
    from selenium.common.exceptions import (
        TimeoutException,
        NoSuchElementException,
        ElementNotInteractableException,
        StaleElementReferenceException,
        WebDriverException,
    )
    SELENIUM_EXCEPTIONS_AVAILABLE = True
except ImportError:
    SELENIUM_EXCEPTIONS_AVAILABLE = False


def validate_allowed_apps_installed(driver: Remote) -> None:
    """
    Valida que todas las apps en ALLOWED_APP_PACKAGES estén instaladas en el dispositivo.
    
    Esta validación se ejecuta una vez al inicio, después de crear el driver.
    
    Args:
        driver: Driver de Appium ya inicializado
        
    Raises:
        ValueError: Si alguna app no está instalada o no se puede verificar
    """
    if not Config.ALLOWED_APP_PACKAGES:
        # Ya validado en Config.validate(), pero por seguridad
        raise ValueError("ALLOWED_APP_PACKAGES está vacío. Configura al menos una app permitida.")
    
    logger.info("VALIDATOR: Validando que apps permitidas estén instaladas...")
    
    # Importar AppiumSkills aquí para evitar importación circular
    from src.agent_tools import AppiumSkills
    
    # Crear instancia temporal de AppiumSkills para usar query_app_state
    ui_parser = None  # No se necesita para esta validación
    agent_tools = AppiumSkills(driver, ui_parser)
    
    for app_package in Config.ALLOWED_APP_PACKAGES:
        try:
            state_code, state_name = agent_tools.query_app_state(app_package)
            if state_code == 0:  # NOT_INSTALLED
                raise ValueError(
                    f"App '{app_package}' de ALLOWED_APP_PACKAGES no está instalada en el dispositivo. "
                    f"Estado: {state_name}. Instala la app o actualiza ALLOWED_APP_PACKAGES en .env"
                )
            logger.debug(f"VALIDATOR: ✓ App '{app_package}' instalada (estado: {state_name})")
        except Exception as e:
            if isinstance(e, ValueError):
                raise
            # Si hay error al consultar el estado, asumir que no está instalada
            logger.error(f"VALIDATOR ERROR: No se pudo verificar estado de app '{app_package}': {e}")
            raise ValueError(
                f"No se pudo verificar si la app '{app_package}' está instalada. "
                f"Error: {str(e)}"
            )
    
    logger.info(f"VALIDATOR: ✓ Todas las {len(Config.ALLOWED_APP_PACKAGES)} apps permitidas están instaladas")


def validate_config() -> None:
    """
    Valida la configuración del sistema usando Config.validate().
    
    Raises:
        ValueError: Si la configuración es inválida
    """
    logger.info("VALIDATOR: Validando configuración...")
    is_valid, error_msg = Config.validate()
    if not is_valid:
        logger.error(f"VALIDATOR ERROR: Configuración inválida: {error_msg}")
        raise ValueError(f"Configuración inválida: {error_msg}")
    logger.info("VALIDATOR: ✓ Configuración válida")


def validate_driver(driver: Remote) -> str:
    """
    Verifica que el driver de Appium esté activo y disponible.
    
    Args:
        driver: Instancia del driver de Appium
        
    Returns:
        Session ID del driver si está activo
        
    Raises:
        Exception: Si el driver no está disponible
    """
    logger.debug("VALIDATOR: Verificando driver de Appium...")
    try:
        session_id = driver.session_id
        logger.info(f"VALIDATOR: ✓ Driver activo - Session ID: {session_id}")
        return session_id
    except Exception as e:
        logger.error(f"VALIDATOR ERROR: Driver no disponible: {e}")
        raise


def is_recoverable_error(exception: Exception) -> bool:
    """
    Determina si un error es recuperable (debe reintentarse) o no recuperable.
    
    Errores NO recuperables (no deben reintentarse):
    - ValueError: Datos inválidos, estructura incorrecta
    - KeyError: Clave faltante en diccionario
    - TypeError: Tipos incorrectos
    - AttributeError: Atributo faltante
    - SyntaxError: Error de sintaxis
    - NameError: Nombre no definido
    - ImportError: Error de importación
    - ConfigurationError: Errores de configuración
    
    Errores SÍ recuperables (deben reintentarse):
    - TimeoutException: Timeouts temporales
    - NoSuchElementException: Elemento no encontrado (puede aparecer después)
    - ElementNotInteractableException: Elemento no interactuable (puede cambiar)
    - StaleElementReferenceException: Referencia obsoleta (puede resolverse)
    - WebDriverException: Algunos errores temporales del driver
    
    Args:
        exception: Excepción a evaluar
        
    Returns:
        True si el error es recuperable (debe reintentarse), False si no
    """
    # Errores NO recuperables - errores de programación/configuración
    non_recoverable_errors = (
        ValueError,
        KeyError,
        TypeError,
        AttributeError,
        SyntaxError,
        NameError,
        ImportError,
        IndentationError,
        UnicodeError,
    )
    
    # Verificar si es un error no recuperable
    if isinstance(exception, non_recoverable_errors):
        return False
    
    # Errores recuperables - errores temporales de Appium/Selenium
    if SELENIUM_EXCEPTIONS_AVAILABLE:
        recoverable_errors = (
            TimeoutException,
            NoSuchElementException,
            ElementNotInteractableException,
            StaleElementReferenceException,
        )
        
        if isinstance(exception, recoverable_errors):
            return True
        
        # WebDriverException puede ser recuperable o no, depende del caso
        # Por defecto, lo consideramos recuperable (puede ser temporal)
        if isinstance(exception, WebDriverException):
            # Algunos WebDriverException son no recuperables (ej: driver desconectado)
            error_msg = str(exception).lower()
            non_recoverable_patterns = [
                "session not created",
                "invalid session id",
                "no such session",
                "session deleted",
            ]
            if any(pattern in error_msg for pattern in non_recoverable_patterns):
                return False
            return True
    
    # Por defecto, si no podemos determinar, asumimos que NO es recuperable
    # para evitar loops infinitos con errores desconocidos
    return False


def validate_app_scope(app_package: str) -> Optional[MiddlewareResult]:
    """
    Valida si el app_package está en la lista de apps permitidas (ALLOWED_APP_PACKAGES).
    
    Esta validación se ejecuta antes de ejecutar acciones que requieren un app_package
    (activate_app, switch_to_app, terminate_app, etc.) para prevenir que el agente
    interactúe con apps fuera del scope configurado.
    
    Args:
        app_package: Package de la app a validar (ej: 'com.imagineapps.gofixiicliente')
        
    Returns:
        None si el package está permitido
        MiddlewareResult con status DENIED si el package no está permitido
    """
    if not Config.ALLOWED_APP_PACKAGES:
        # Si no hay apps permitidas configuradas, no hay restricción de scope
        return None
    
    if app_package not in Config.ALLOWED_APP_PACKAGES:
        allowed_str = ", ".join(Config.ALLOWED_APP_PACKAGES)
        logger.warning(
            f"VALIDATOR: ⚠️  Package '{app_package}' no está en ALLOWED_APP_PACKAGES. "
            f"Apps permitidas: {allowed_str}"
        )
        return MiddlewareResult(
            status=MiddlewareStatus.DENIED,
            message=f"Advertencia: El package '{app_package}' no está en ALLOWED_APP_PACKAGES. Apps permitidas: {allowed_str}",
            allowed_apps=Config.ALLOWED_APP_PACKAGES
        )
    
    return None
