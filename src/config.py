"""
Configuración del proyecto - Carga variables de entorno y configuración.
"""

import os
from typing import Optional, Tuple
from dotenv import load_dotenv

# Cargar variables de entorno desde .env y .env.local
# .env.local tiene prioridad (se carga después y sobrescribe valores)
load_dotenv(".env")
load_dotenv(".env.local", override=True)


class Config:
    """Maneja la configuración del proyecto."""

    # API Keys
    OPENAI_API_KEY: Optional[str] = os.getenv("OPENAI_API_KEY")
    ANTHROPIC_API_KEY: Optional[str] = os.getenv("ANTHROPIC_API_KEY")

    # Configuración de modelos
    DEFAULT_AI_PROVIDER: str = os.getenv("AI_PROVIDER", "openai")  # "openai" o "anthropic"
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o")
    ANTHROPIC_MODEL: str = os.getenv("ANTHROPIC_MODEL", "claude-3-5-sonnet-20241022")

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

    @classmethod
    def validate(cls) -> Tuple[bool, Optional[str]]:
        """
        Valida que las configuraciones necesarias estén presentes.

        Returns:
            Tupla (is_valid, error_message)
        """
        # Validar que al menos una API key esté configurada
        if cls.DEFAULT_AI_PROVIDER == "openai" and not cls.OPENAI_API_KEY:
            return False, "OPENAI_API_KEY no está configurada en variables de entorno"
        
        if cls.DEFAULT_AI_PROVIDER == "anthropic" and not cls.ANTHROPIC_API_KEY:
            return False, "ANTHROPIC_API_KEY no está configurada en variables de entorno"

        return True, None

    @classmethod
    def get_appium_capabilities(cls) -> dict:
        """
        Retorna las capabilities de Appium para Android.
        Similar a la configuración de WebdriverIO.

        Returns:
            Diccionario con capabilities
        """
        capabilities = {
            "platformName": cls.ANDROID_PLATFORM_NAME,
            "appium:automationName": cls.ANDROID_AUTOMATION_NAME,
            "appium:deviceName": cls.ANDROID_DEVICE_NAME,
            "appium:newCommandTimeout": cls.DEFAULT_WAIT_TIMEOUT * 60,  # En segundos
        }

        # Agregar UDID si está configurado
        if cls.ANDROID_UDID:
            capabilities["appium:udid"] = cls.ANDROID_UDID
        else:
            # Si no hay UDID, usar deviceName como UDID
            capabilities["appium:udid"] = cls.ANDROID_DEVICE_NAME

        # Agregar ruta del APK si está configurada (prioridad sobre package/activity)
        if cls.ANDROID_APP_PATH:
            capabilities["appium:app"] = cls.ANDROID_APP_PATH

        # Agregar app package y activity si están configurados
        if cls.ANDROID_APP_PACKAGE:
            capabilities["appium:appPackage"] = cls.ANDROID_APP_PACKAGE
        if cls.ANDROID_APP_ACTIVITY:
            capabilities["appium:appActivity"] = cls.ANDROID_APP_ACTIVITY

        # Agregar capabilities opcionales para mejor compatibilidad
        capabilities["appium:autoGrantPermissions"] = cls.ANDROID_AUTO_GRANT_PERMISSIONS
        capabilities["appium:ignoreHiddenApiPolicyError"] = cls.ANDROID_IGNORE_HIDDEN_API_POLICY_ERROR
        capabilities["appium:disableWindowAnimation"] = cls.ANDROID_DISABLE_WINDOW_ANIMATION
        capabilities["appium:skipDeviceInitialization"] = False
        capabilities["appium:disableSuppressAccessibilityService"] = True

        return capabilities

