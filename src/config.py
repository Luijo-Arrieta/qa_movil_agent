"""
Configuración del proyecto - Carga variables de entorno y configuración.
"""

import os
import logging
from datetime import datetime
from typing import Optional, Tuple, List
from dotenv import load_dotenv

# Configurar logging para este módulo
logger = logging.getLogger(__name__)

# ============================================================================
# DEBUG: Inicio de carga de configuración
# ============================================================================
logger.debug("=" * 70)
logger.debug("CONFIG: Iniciando carga de configuración del proyecto")
logger.debug("=" * 70)

# Cargar variables de entorno desde .env y .env.local
# .env.local tiene prioridad (se carga después y sobrescribe valores)
env_loaded = load_dotenv(".env")
logger.debug(f"CONFIG: .env cargado: {env_loaded}")

env_local_loaded = load_dotenv(".env.local", override=True)
logger.debug(f"CONFIG: .env.local cargado: {env_local_loaded}")


class Config:
    """Maneja la configuración del proyecto."""

    # API Keys
    OPENAI_API_KEY: Optional[str] = os.getenv("OPENAI_API_KEY")
    ANTHROPIC_API_KEY: Optional[str] = os.getenv("ANTHROPIC_API_KEY")
    DEEPSEEK_API_KEY: Optional[str] = os.getenv("DEEPSEEK_API_KEY")

    # Configuración de modelos
    DEFAULT_AI_PROVIDER: str = os.getenv("AI_PROVIDER", "openai")  # "openai", "anthropic" o "deepseek"
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o")
    ANTHROPIC_MODEL: str = os.getenv("ANTHROPIC_MODEL", "claude-3-5-sonnet-20241022")
    DEEPSEEK_MODEL: str = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")

    # Configuración de Appium
    APPIUM_SERVER_URL: str = os.getenv("APPIUM_SERVER_URL", "http://localhost:4723")
    ANDROID_PLATFORM_NAME: str = os.getenv("ANDROID_PLATFORM_NAME", "Android")
    ANDROID_DEVICE_NAME: str = os.getenv("ANDROID_DEVICE_NAME", "emulator-5554")
    ANDROID_APP_PACKAGE: Optional[str] = os.getenv("ANDROID_APP_PACKAGE")
    ANDROID_APP_ACTIVITY: Optional[str] = os.getenv("ANDROID_APP_ACTIVITY")
    ANDROID_APP_PATH: Optional[str] = os.getenv("ANDROID_APP_PATH")  # Ruta al APK
    ANDROID_UDID: Optional[str] = os.getenv("ANDROID_UDID")  # UDID del dispositivo
    ANDROID_AUTOMATION_NAME: str = os.getenv("ANDROID_AUTOMATION_NAME", "UiAutomator2")
    ANDROID_AUTO_GRANT_PERMISSIONS: bool = os.getenv("ANDROID_AUTO_GRANT_PERMISSIONS", "true").lower() == "true"
    ANDROID_IGNORE_HIDDEN_API_POLICY_ERROR: bool = os.getenv("ANDROID_IGNORE_HIDDEN_API_POLICY_ERROR", "true").lower() == "true"
    ANDROID_DISABLE_WINDOW_ANIMATION: bool = os.getenv("ANDROID_DISABLE_WINDOW_ANIMATION", "true").lower() == "true"

    # Timeouts
    # DEFAULT_WAIT_TIMEOUT: en MINUTOS (se convierte a segundos para newCommandTimeout)
    DEFAULT_WAIT_TIMEOUT: int = int(os.getenv("DEFAULT_WAIT_TIMEOUT", "10"))
    # IMPLICIT_WAIT: en SEGUNDOS (se usa directamente con driver.implicitly_wait())
    IMPLICIT_WAIT: int = int(os.getenv("IMPLICIT_WAIT", "5"))
    
    # Configuración de espera por estabilidad de UI (manejo de pantallas de carga)
    # UI_STABILITY_TIMEOUT: Máximo tiempo de espera para que la UI se estabilice (segundos)
    UI_STABILITY_TIMEOUT: float = float(os.getenv("UI_STABILITY_TIMEOUT", "10.0"))
    # UI_STABILITY_INTERVAL: Intervalo entre verificaciones de estabilidad (segundos)
    UI_STABILITY_INTERVAL: float = float(os.getenv("UI_STABILITY_INTERVAL", "0.3"))
    # UI_STABILITY_THRESHOLD: Número de verificaciones consecutivas sin cambios requeridas
    UI_STABILITY_THRESHOLD: int = int(os.getenv("UI_STABILITY_THRESHOLD", "2"))
    
    # Configuración del Test Runner (prevención de loops infinitos)
    # MAX_RETRIES_PER_STEP: Máximo de reintentos por paso cuando hay errores recuperables
    MAX_RETRIES_PER_STEP: int = int(os.getenv("MAX_RETRIES_PER_STEP", "1"))
    # MAX_ACTIONS_PER_STEP: Máximo de acciones diferentes permitidas por paso
    MAX_ACTIONS_PER_STEP: int = int(os.getenv("MAX_ACTIONS_PER_STEP", "10"))
    # MAX_REPEATED_ACTION_ATTEMPTS: Máximo de intentos de la MISMA acción antes de fallar
    # (detecta cuando la IA está atascada repitiendo una acción sin progreso)
    MAX_REPEATED_ACTION_ATTEMPTS: int = int(os.getenv("MAX_REPEATED_ACTION_ATTEMPTS", "3"))
    
    # Credenciales de prueba para tests
    TEST_USER_EMAIL: str = os.getenv("TEST_USER_EMAIL", "cliente@demo.com")
    TEST_USER_PASSWORD: str = os.getenv("TEST_USER_PASSWORD", "123456")
    
    @classmethod
    def get_dynamic_test_password(cls, prefix: str = "NuevaClave") -> str:
        """
        Genera una contraseña dinámica simple usando timestamp.
        
        Args:
            prefix: Prefijo para la contraseña (default: "NuevaClave")
            
        Returns:
            Contraseña dinámica con formato: {prefix}{timestamp}
        """
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        return f"{prefix}{timestamp}"

    # Modo de proyecto / comportamiento de app principal
    # Si ANDROID_APP_PACKAGE está definido, se considera un proyecto "single-app"
    # (hay una app principal). Si no, se asume proyecto multi-app.
    AUTO_LAUNCH_MAIN_APP: bool = os.getenv("AUTO_LAUNCH_MAIN_APP", "false").lower() == "true"
    
    # QAI Version
    QAI_VERSION: str = os.getenv("QAI_VERSION", "v1")  # "v1" o "v2"

    # =========================================================================
    # AI API Configuration (timeout, retries)
    # =========================================================================
    # Timeout en segundos para llamadas a la API de IA
    AI_API_TIMEOUT: float = float(os.getenv("AI_API_TIMEOUT", "120.0"))
    # Número de reintentos (1 = intento inicial + 1 reintento = 2 oportunidades)
    AI_API_MAX_RETRIES: int = int(os.getenv("AI_API_MAX_RETRIES", "1"))
    # Segundos de espera entre reintentos
    AI_API_RETRY_DELAY: float = float(os.getenv("AI_API_RETRY_DELAY", "3.0"))

    # =========================================================================
    # AI Provider Fallback Configuration
    # =========================================================================
    # Habilita fallback automático a otro proveedor si el primario falla
    AI_FALLBACK_ENABLED: bool = os.getenv("AI_FALLBACK_ENABLED", "false").lower() == "true"
    # Lista ordenada de proveedores de fallback (separados por coma)
    # Ejemplo: "anthropic,openai" - si el primario falla, intenta anthropic, luego openai
    _AI_FALLBACK_PROVIDERS_STR: Optional[str] = os.getenv("AI_FALLBACK_PROVIDERS")
    AI_FALLBACK_PROVIDERS: List[str] = (
        [p.strip() for p in _AI_FALLBACK_PROVIDERS_STR.split(",") if p.strip()]
        if _AI_FALLBACK_PROVIDERS_STR
        else []
    )

    # Apps permitidas (scope del agente)
    # Lista de packages de apps que el agente puede ver e interactuar
    # Separadas por comas, sin espacios (ej: "com.app1,com.app2")
    _ALLOWED_APP_PACKAGES_STR: Optional[str] = os.getenv("ALLOWED_APP_PACKAGES")
    ALLOWED_APP_PACKAGES: List[str] = (
        [pkg.strip() for pkg in _ALLOWED_APP_PACKAGES_STR.split(",") if pkg.strip()]
        if _ALLOWED_APP_PACKAGES_STR
        else []
    )

    @classmethod
    def debug_print_config(cls) -> None:
        """
        DEBUG: Imprime toda la configuración actual (ocultando API keys).
        Útil para diagnóstico de problemas de configuración.
        """
        logger.info("=" * 70)
        logger.info("CONFIG DEBUG: Estado actual de la configuración")
        logger.info("=" * 70)
        
        # API Keys (ocultar valor real)
        openai_key_status = "✓ Configurada" if cls.OPENAI_API_KEY else "✗ NO configurada"
        anthropic_key_status = "✓ Configurada" if cls.ANTHROPIC_API_KEY else "✗ NO configurada"
        deepseek_key_status = "✓ Configurada" if cls.DEEPSEEK_API_KEY else "✗ NO configurada"
        logger.info(f"  OPENAI_API_KEY: {openai_key_status}")
        logger.info(f"  ANTHROPIC_API_KEY: {anthropic_key_status}")
        logger.info(f"  DEEPSEEK_API_KEY: {deepseek_key_status}")
        
        # Configuración de AI
        logger.info(f"  AI_PROVIDER: {cls.DEFAULT_AI_PROVIDER}")
        logger.info(f"  OPENAI_MODEL: {cls.OPENAI_MODEL}")
        logger.info(f"  ANTHROPIC_MODEL: {cls.ANTHROPIC_MODEL}")
        logger.info(f"  DEEPSEEK_MODEL: {cls.DEEPSEEK_MODEL}")
        
        # Configuración de Appium
        logger.info("-" * 40)
        logger.info("  APPIUM_SERVER_URL: " + cls.APPIUM_SERVER_URL)
        logger.info(f"  ANDROID_PLATFORM_NAME: {cls.ANDROID_PLATFORM_NAME}")
        logger.info(f"  ANDROID_DEVICE_NAME: {cls.ANDROID_DEVICE_NAME}")
        logger.info(f"  ANDROID_APP_PACKAGE: {cls.ANDROID_APP_PACKAGE or 'NO configurado'}")
        logger.info(f"  ANDROID_APP_ACTIVITY: {cls.ANDROID_APP_ACTIVITY or 'NO configurado'}")
        logger.info(f"  ANDROID_APP_PATH: {cls.ANDROID_APP_PATH or 'NO configurado'}")
        logger.info(f"  ANDROID_UDID: {cls.ANDROID_UDID or 'NO configurado'}")
        logger.info(f"  ANDROID_AUTOMATION_NAME: {cls.ANDROID_AUTOMATION_NAME}")
        
        # Flags
        logger.info("-" * 40)
        logger.info(f"  AUTO_GRANT_PERMISSIONS: {cls.ANDROID_AUTO_GRANT_PERMISSIONS}")
        logger.info(f"  IGNORE_HIDDEN_API_ERROR: {cls.ANDROID_IGNORE_HIDDEN_API_POLICY_ERROR}")
        logger.info(f"  DISABLE_WINDOW_ANIMATION: {cls.ANDROID_DISABLE_WINDOW_ANIMATION}")
        logger.info(f"  AUTO_LAUNCH_MAIN_APP (single-app only): {cls.AUTO_LAUNCH_MAIN_APP}")
        
        # Timeouts
        logger.info("-" * 40)
        logger.info(f"  DEFAULT_WAIT_TIMEOUT: {cls.DEFAULT_WAIT_TIMEOUT} minutos ({cls.DEFAULT_WAIT_TIMEOUT * 60} segundos)")
        logger.info(f"  IMPLICIT_WAIT: {cls.IMPLICIT_WAIT} segundos")
        
        # UI Stability (manejo de pantallas de carga)
        logger.info("-" * 40)
        logger.info("  UI Stability (pantallas de carga):")
        logger.info(f"    UI_STABILITY_TIMEOUT: {cls.UI_STABILITY_TIMEOUT}s")
        logger.info(f"    UI_STABILITY_INTERVAL: {cls.UI_STABILITY_INTERVAL}s")
        logger.info(f"    UI_STABILITY_THRESHOLD: {cls.UI_STABILITY_THRESHOLD} checks")
        
        # Test Runner (prevención de loops)
        logger.info("-" * 40)
        logger.info("  Test Runner:")
        logger.info(f"    MAX_RETRIES_PER_STEP: {cls.MAX_RETRIES_PER_STEP} reintentos")
        logger.info(f"    MAX_ACTIONS_PER_STEP: {cls.MAX_ACTIONS_PER_STEP} acciones")
        logger.info(f"    MAX_REPEATED_ACTION_ATTEMPTS: {cls.MAX_REPEATED_ACTION_ATTEMPTS} intentos")
        
        logger.info("=" * 70)

    @classmethod
    def validate(cls) -> Tuple[bool, Optional[str]]:
        """
        Valida que las configuraciones necesarias estén presentes.

        Returns:
            Tupla (is_valid, error_message)
        """
        logger.debug("CONFIG: Iniciando validación de configuración...")
        errors = []
        warnings = []
        
        # Validar proveedor de IA
        logger.debug(f"CONFIG: Validando proveedor de IA: {cls.DEFAULT_AI_PROVIDER}")
        if cls.DEFAULT_AI_PROVIDER not in ["openai", "anthropic", "deepseek"]:
            errors.append(f"AI_PROVIDER inválido: '{cls.DEFAULT_AI_PROVIDER}'. Debe ser 'openai', 'anthropic' o 'deepseek'")
        
        # Validar API keys según el proveedor
        if cls.DEFAULT_AI_PROVIDER == "openai":
            if not cls.OPENAI_API_KEY:
                errors.append("OPENAI_API_KEY no está configurada en variables de entorno")
            else:
                logger.debug("CONFIG: ✓ OPENAI_API_KEY presente")
        
        if cls.DEFAULT_AI_PROVIDER == "anthropic":
            if not cls.ANTHROPIC_API_KEY:
                errors.append("ANTHROPIC_API_KEY no está configurada en variables de entorno")
            else:
                logger.debug("CONFIG: ✓ ANTHROPIC_API_KEY presente")
        
        if cls.DEFAULT_AI_PROVIDER == "deepseek":
            if not cls.DEEPSEEK_API_KEY:
                errors.append("DEEPSEEK_API_KEY no está configurada en variables de entorno")
            else:
                logger.debug("CONFIG: ✓ DEEPSEEK_API_KEY presente")
        
        # Validar configuración de Appium
        logger.debug("CONFIG: Validando configuración de Appium...")
        
        if not cls.ANDROID_APP_PATH and not cls.ANDROID_APP_PACKAGE:
            warnings.append("Ni ANDROID_APP_PATH ni ANDROID_APP_PACKAGE están configurados. "
                          "Debes configurar al menos uno para iniciar la app.")
        
        if cls.ANDROID_APP_PACKAGE and not cls.ANDROID_APP_ACTIVITY:
            warnings.append("ANDROID_APP_PACKAGE está configurado pero ANDROID_APP_ACTIVITY no. "
                          "Puede ser necesario para algunas apps.")
        
        # Validar timeouts
        if cls.DEFAULT_WAIT_TIMEOUT <= 0:
            errors.append(f"DEFAULT_WAIT_TIMEOUT debe ser > 0, actual: {cls.DEFAULT_WAIT_TIMEOUT}")
        
        if cls.IMPLICIT_WAIT < 0:
            errors.append(f"IMPLICIT_WAIT debe ser >= 0, actual: {cls.IMPLICIT_WAIT}")
        
        # Validar ALLOWED_APP_PACKAGES
        logger.debug("CONFIG: Validando ALLOWED_APP_PACKAGES...")
        if not cls.ALLOWED_APP_PACKAGES:
            errors.append("ALLOWED_APP_PACKAGES no está configurado o está vacío. Debe contener al menos una app permitida (separadas por comas).")
        else:
            logger.debug(f"CONFIG: ✓ ALLOWED_APP_PACKAGES configurado con {len(cls.ALLOWED_APP_PACKAGES)} app(s): {cls.ALLOWED_APP_PACKAGES}")
        
        # Log warnings
        for warning in warnings:
            logger.warning(f"CONFIG WARNING: {warning}")
        
        # Log errors y retornar
        if errors:
            for error in errors:
                logger.error(f"CONFIG ERROR: {error}")
            return False, "; ".join(errors)
        
        logger.debug("CONFIG: ✓ Validación completada sin errores")
        return True, None

    @classmethod
    def get_appium_capabilities(cls) -> dict:
        """
        Retorna las capabilities de Appium para Android.
        Similar a la configuración de WebdriverIO.

        Returns:
            Diccionario con capabilities
        """
        logger.debug("CONFIG: Construyendo capabilities de Appium...")
        
        capabilities = {
            "platformName": cls.ANDROID_PLATFORM_NAME,
            "appium:automationName": cls.ANDROID_AUTOMATION_NAME,
            "appium:deviceName": cls.ANDROID_DEVICE_NAME,
            "appium:newCommandTimeout": cls.DEFAULT_WAIT_TIMEOUT * 60,  # En segundos
        }
        #logger.debug(f"CONFIG: Capabilities base: platformName={cls.ANDROID_PLATFORM_NAME}, "
        #            f"automationName={cls.ANDROID_AUTOMATION_NAME}, deviceName={cls.ANDROID_DEVICE_NAME}")

        # Agregar UDID si está configurado
        if cls.ANDROID_UDID:
            capabilities["appium:udid"] = cls.ANDROID_UDID
            #logger.debug(f"CONFIG: Usando UDID configurado: {cls.ANDROID_UDID}")
        else:
            # Si no hay UDID, usar deviceName como UDID
            capabilities["appium:udid"] = cls.ANDROID_DEVICE_NAME
            #logger.debug(f"CONFIG: Usando deviceName como UDID: {cls.ANDROID_DEVICE_NAME}")

        # NOTA: NO agregar appPackage, appActivity, o app a capabilities.
        # El driver se crea sin abrir ninguna app automáticamente.
        # El usuario final debe usar activate_app() de agent_tools.py para abrir la app que necesite.

        # Agregar capabilities opcionales para mejor compatibilidad
        capabilities["appium:autoGrantPermissions"] = cls.ANDROID_AUTO_GRANT_PERMISSIONS
        capabilities["appium:ignoreHiddenApiPolicyError"] = cls.ANDROID_IGNORE_HIDDEN_API_POLICY_ERROR
        capabilities["appium:disableWindowAnimation"] = cls.ANDROID_DISABLE_WINDOW_ANIMATION
        capabilities["appium:skipDeviceInitialization"] = False
        capabilities["appium:disableSuppressAccessibilityService"] = True

        #logger.debug(f"CONFIG: Total de capabilities construidas: {len(capabilities)}")
        #logger.debug("CONFIG: Capabilities finales:")
        #for key, value in capabilities.items():
        #    logger.debug(f"  {key}: {value}")
        
        return capabilities

