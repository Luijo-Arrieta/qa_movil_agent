"""
Configuración base de pytest compartida para todos los tests.

Este archivo contiene:
- Markers personalizados
- Configuración de logging
- Plugins compartidos

Los fixtures específicos están en:
- tests/unit/conftest.py     → Fixtures para tests unitarios
- tests/specs/conftest.py    → Fixtures para tests E2E (driver_setup, Allure)
"""

import logging

import pytest


# Configurar logging con formato detallado
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s.%(msecs)03d - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# Silenciar loggers ruidosos que imprimen datos base64 de screenshots
logging.getLogger("selenium.webdriver.remote.remote_connection").setLevel(logging.WARNING)
logging.getLogger("urllib3.connectionpool").setLevel(logging.WARNING)


def pytest_configure(config):
    """Registrar markers personalizados."""
    config.addinivalue_line(
        "markers", "unit: Tests unitarios (sin Appium, rápidos)"
    )
    config.addinivalue_line(
        "markers", "integration: Tests de integración (requieren Appium + dispositivo)"
    )
    config.addinivalue_line(
        "markers", "slow: Tests lentos o de larga duración"
    )
