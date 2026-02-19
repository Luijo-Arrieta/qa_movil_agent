"""
Configuración del backend.
"""

import os
from typing import List
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()


class Settings:
    """Configuración de la aplicación."""
    
    # API Configuration
    API_V1_PREFIX: str = "/api/v1"
    
    # CORS
    CORS_ORIGINS: List[str] = os.getenv(
        "CORS_ORIGINS",
        "http://localhost:3000,http://localhost:5173"
    ).split(",")
    
    # Appium
    APPIUM_SERVER_URL: str = os.getenv("APPIUM_SERVER_URL", "http://localhost:4723")
    
    # Test execution
    MAX_TEST_TIMEOUT: int = int(os.getenv("MAX_TEST_TIMEOUT", "600"))  # 10 minutos
    
    # Results storage
    RESULTS_DIR: str = os.getenv("RESULTS_DIR", "./results")
    
    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")


settings = Settings()
