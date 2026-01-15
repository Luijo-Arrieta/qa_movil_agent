"""
Tests de integración para Agent Tools con apps reales.

Estos tests prueban las herramientas de multi-app management en un entorno real:
- query_app_state
- activate_app
- terminate_app
- switch_to_app
- switch_to_app_keep_background

Requisitos:
- Appium Server corriendo
- Dispositivo Android / Emulador conectado
- App configurada en capabilities (app principal)
- App Settings del sistema Android (siempre disponible)
"""

import logging
import time

import pytest
from src.agent_tools import AppiumSkills
from src.ui_parser import UIParser
from tests.conftest import allure_attach_debug_snapshot, allure_attach_screenshot

logger = logging.getLogger(__name__)


# App de sistema Android que siempre está instalada
SETTINGS_PACKAGE = "com.android.settings"


@pytest.mark.integration
class TestAgentToolsMultiApp:
    """Tests de integración para herramientas de multi-app management."""

    @pytest.mark.usefixtures("driver_setup")
    def test_all_multi_app_tools_deterministic(self, driver_setup):
        """
        Test determinístico que prueba todas las herramientas de multi-app.
        
        Este test NO usa AI, solo llama directamente a las herramientas con decisiones preestablecidas.
        Prueba:
        1. query_app_state - Consultar estado de apps
        2. activate_app - Abrir/activar apps
        3. switch_to_app_keep_background - Cambiar manteniendo app anterior en background
        4. switch_to_app - Cambiar terminando app anterior
        5. terminate_app - Cerrar apps
        6. Verificar tracking de app actual
        
        Ejecutar solo este test:
        poetry run pytest tests/integration/test_agent_tools_integration.py::TestAgentToolsMultiApp::test_all_multi_app_tools_deterministic -v -s
        """
        logger.info("")
        logger.info("=" * 80)
        logger.info("🧪 TEST DETERMINÍSTICO: Todas las herramientas de multi-app")
        logger.info("=" * 80)
        logger.info("")
        
        # ═══════════════════════════════════════════════════════════════════
        # SETUP: Crear instancias
        # ═══════════════════════════════════════════════════════════════════
        logger.info("🔧 Creando instancias de UIParser y AppiumSkills...")
        ui_parser = UIParser()
        agent_tools = AppiumSkills(driver_setup, ui_parser)
        
        # App principal configurada (la que se abre con driver_setup)
        main_app_package = driver_setup.capabilities.get("appPackage") or driver_setup.capabilities.get("appium:appPackage")
        logger.info(f"📱 App principal configurada: {main_app_package}")
        
        allure_attach_screenshot(driver_setup, "01_inicial")
        
        # ═══════════════════════════════════════════════════════════════════
        # TEST 1: query_app_state - Consultar estado de apps
        # ═══════════════════════════════════════════════════════════════════
        logger.info("")
        logger.info("╔" + "═" * 78 + "╗")
        logger.info("║  TEST 1: query_app_state")
        logger.info("╚" + "═" * 78 + "╝")
        logger.info("")
        
        # Consultar estado de Settings (siempre está instalada)
        settings_state, settings_state_name = agent_tools.query_app_state(SETTINGS_PACKAGE)
        logger.info(f"✓ Estado de Settings: {settings_state_name} ({settings_state})")
        assert settings_state >= 0, f"query_app_state debe retornar estado >= 0, obtuvo {settings_state}"
        
        # Consultar estado de la app principal
        if main_app_package:
            main_state, main_state_name = agent_tools.query_app_state(main_app_package)
            logger.info(f"✓ Estado de app principal '{main_app_package}': {main_state_name} ({main_state})")
            assert main_state == 4, f"App principal debe estar en FOREGROUND (4), obtuvo {main_state}"
        
        # Verificar que get_current_app_package funciona
        current_package = agent_tools.get_current_app_package()
        logger.info(f"✓ App actual según tracking: {current_package}")
        
        # ═══════════════════════════════════════════════════════════════════
        # TEST 2: activate_app - Abrir Settings
        # ═══════════════════════════════════════════════════════════════════
        logger.info("")
        logger.info("╔" + "═" * 78 + "╗")
        logger.info("║  TEST 2: activate_app (abrir Settings)")
        logger.info("╚" + "═" * 78 + "╝")
        logger.info("")
        
        result = agent_tools.activate_app(SETTINGS_PACKAGE)
        logger.info(f"📌 Resultado: {result}")
        assert "Success" in result, f"activate_app debe retornar Success, obtuvo: {result}"
        
        # Verificar que la app cambió
        time.sleep(2)  # Esperar a que Settings cargue
        allure_attach_screenshot(driver_setup, "02_after_activate_settings")
        
        settings_state_after, _ = agent_tools.query_app_state(SETTINGS_PACKAGE)
        assert settings_state_after == 4, f"Settings debe estar en FOREGROUND (4), obtuvo {settings_state_after}"
        
        # Verificar tracking
        current_package = agent_tools.get_current_app_package()
        assert current_package == SETTINGS_PACKAGE, f"Tracking debe ser Settings, obtuvo {current_package}"
        logger.info("✓ Settings activada correctamente")
        
        # ═══════════════════════════════════════════════════════════════════
        # TEST 3: switch_to_app_keep_background - Cambiar a app principal (manteniendo Settings en background)
        # ═══════════════════════════════════════════════════════════════════
        logger.info("")
        logger.info("╔" + "═" * 78 + "╗")
        logger.info("║  TEST 3: switch_to_app_keep_background (Settings → App principal)")
        logger.info("╚" + "═" * 78 + "╝")
        logger.info("")
        
        if not main_app_package:
            logger.warning("⚠ App principal no configurada, saltando este test")
        else:
            result = agent_tools.switch_to_app_keep_background(main_app_package)
            logger.info(f"📌 Resultado: {result}")
            assert "Success" in result, f"switch_to_app_keep_background debe retornar Success, obtuvo: {result}"
            
            time.sleep(2)  # Esperar a que la app principal cargue
            allure_attach_screenshot(driver_setup, "03_after_switch_to_main_app")
            
            # Verificar que la app principal está en foreground
            main_state_after, _ = agent_tools.query_app_state(main_app_package)
            assert main_state_after == 4, f"App principal debe estar en FOREGROUND (4), obtuvo {main_state_after}"
            
            # Verificar que Settings sigue en background (no terminada)
            settings_state_background, _ = agent_tools.query_app_state(SETTINGS_PACKAGE)
            assert settings_state_background in [2, 3], f"Settings debe estar en BACKGROUND (2 o 3), obtuvo {settings_state_background}"
            
            # Verificar tracking
            current_package = agent_tools.get_current_app_package()
            assert current_package == main_app_package, f"Tracking debe ser app principal, obtuvo {current_package}"
            logger.info("✓ Cambio a app principal exitoso (Settings en background)")
        
        # ═══════════════════════════════════════════════════════════════════
        # TEST 4: switch_to_app - Cambiar a Settings terminando app principal
        # ═══════════════════════════════════════════════════════════════════
        logger.info("")
        logger.info("╔" + "═" * 78 + "╗")
        logger.info("║  TEST 4: switch_to_app (App principal → Settings, terminando app principal)")
        logger.info("╚" + "═" * 78 + "╝")
        logger.info("")
        
        if not main_app_package:
            logger.warning("⚠ App principal no configurada, saltando este test")
        else:
            result = agent_tools.switch_to_app(SETTINGS_PACKAGE)
            logger.info(f"📌 Resultado: {result}")
            assert "Success" in result, f"switch_to_app debe retornar Success, obtuvo: {result}"
            
            time.sleep(2)  # Esperar a que Settings cargue
            allure_attach_screenshot(driver_setup, "04_after_switch_to_settings")
            
            # Verificar que Settings está en foreground
            settings_state_final, _ = agent_tools.query_app_state(SETTINGS_PACKAGE)
            assert settings_state_final == 4, f"Settings debe estar en FOREGROUND (4), obtuvo {settings_state_final}"
            
            # Verificar que la app principal fue terminada (NOT_RUNNING o BACKGROUND_SUSPENDED)
            main_state_after_switch, _ = agent_tools.query_app_state(main_app_package)
            # Puede estar en NOT_RUNNING (1) o BACKGROUND_SUSPENDED (2) dependiendo del sistema
            assert main_state_after_switch in [1, 2], f"App principal debe estar terminada (1 o 2), obtuvo {main_state_after_switch}"
            
            # Verificar tracking
            current_package = agent_tools.get_current_app_package()
            assert current_package == SETTINGS_PACKAGE, f"Tracking debe ser Settings, obtuvo {current_package}"
            logger.info("✓ Cambio a Settings exitoso (app principal terminada)")
        
        # ═══════════════════════════════════════════════════════════════════
        # TEST 5: activate_app - Volver a app principal (Settings queda en background)
        # ═══════════════════════════════════════════════════════════════════
        logger.info("")
        logger.info("╔" + "═" * 78 + "╗")
        logger.info("║  TEST 5: activate_app (volver a app principal, Settings en background)")
        logger.info("╚" + "═" * 78 + "╝")
        logger.info("")
        
        if not main_app_package:
            logger.warning("⚠ App principal no configurada, saltando este test")
        else:
            result = agent_tools.activate_app(main_app_package)
            logger.info(f"📌 Resultado: {result}")
            assert "Success" in result, f"activate_app debe retornar Success, obtuvo: {result}"
            
            time.sleep(2)  # Esperar a que la app principal cargue
            allure_attach_screenshot(driver_setup, "05_after_activate_main_app")
            
            # Verificar que la app principal está en foreground
            main_state_final, _ = agent_tools.query_app_state(main_app_package)
            assert main_state_final == 4, f"App principal debe estar en FOREGROUND (4), obtuvo {main_state_final}"
            
            # Verificar que Settings está en background
            settings_state_bg, _ = agent_tools.query_app_state(SETTINGS_PACKAGE)
            assert settings_state_bg in [2, 3], f"Settings debe estar en BACKGROUND (2 o 3), obtuvo {settings_state_bg}"
            
            # Verificar tracking
            current_package = agent_tools.get_current_app_package()
            assert current_package == main_app_package, f"Tracking debe ser app principal, obtuvo {current_package}"
            logger.info("✓ App principal reactivada correctamente (Settings en background)")
        
        # ═══════════════════════════════════════════════════════════════════
        # TEST 6: terminate_app - Cerrar Settings
        # ═══════════════════════════════════════════════════════════════════
        logger.info("")
        logger.info("╔" + "═" * 78 + "╗")
        logger.info("║  TEST 6: terminate_app (cerrar Settings)")
        logger.info("╚" + "═" * 78 + "╝")
        logger.info("")
        
        result = agent_tools.terminate_app(SETTINGS_PACKAGE)
        logger.info(f"📌 Resultado: {result}")
        assert "Success" in result, f"terminate_app debe retornar Success, obtuvo: {result}"
        
        time.sleep(1)
        allure_attach_screenshot(driver_setup, "06_after_terminate_settings")
        
        # Verificar que Settings fue terminada
        settings_state_terminated, _ = agent_tools.query_app_state(SETTINGS_PACKAGE)
        assert settings_state_terminated in [1, 2], f"Settings debe estar terminada (1 o 2), obtuvo {settings_state_terminated}"
        
        # Verificar tracking se limpió (si Settings era la app actual, ahora debe ser None)
        # Pero como cambiamos a app principal antes, el tracking debería seguir siendo app principal
        # Verificar tracking - después de terminar Settings, el tracking debería seguir siendo app principal
        # (porque ya cambiamos a app principal en TEST 5)
        current_package = agent_tools.get_current_app_package()
        if current_package == SETTINGS_PACKAGE:
            # Si por alguna razón el tracking no se actualizó, verificar que se limpió
            assert current_package is None, f"Tracking debe ser None después de terminar Settings, obtuvo {current_package}"
        logger.info("✓ Settings terminada correctamente")
        
        # ═══════════════════════════════════════════════════════════════════
        # RESUMEN FINAL
        # ═══════════════════════════════════════════════════════════════════
        logger.info("")
        logger.info("╔" + "═" * 78 + "╗")
        logger.info("║  RESUMEN FINAL")
        logger.info("╚" + "═" * 78 + "╝")
        logger.info("")
        
        stats = agent_tools.get_action_stats()
        logger.info(f"📊 Estadísticas de acciones:")
        logger.info(f"   Total: {stats['total_actions']}")
        logger.info(f"   Exitosas: {stats['successful_actions']}")
        logger.info(f"   Fallidas: {stats['failed_actions']}")
        if 'success_rate' in stats:
            logger.info(f"   Tasa de éxito: {stats['success_rate']}")
        logger.info(f"   Por tipo: {stats['actions_by_type']}")
        
        allure_attach_debug_snapshot(driver_setup, "07_final")
        
        logger.info("")
        logger.info("✅ Test determinístico completado exitosamente")
        logger.info("=" * 80)

    @pytest.mark.usefixtures("driver_setup")
    def test_multi_app_tools_with_ai(self, driver_setup):
        """
        Test con AI que prueba cambiar entre apps usando el Test Runner.
        
        Este test usa AITestRunner para que la IA decida cómo cambiar entre apps.
        Prueba un flujo simple: abrir Settings, verificar, volver a la app principal.
        
        Ejecutar solo este test:
        poetry run pytest tests/integration/test_agent_tools_integration.py::TestAgentToolsMultiApp::test_multi_app_tools_with_ai -v -s
        """
        from src.test_runner import AITestRunner
        
        logger.info("")
        logger.info("=" * 80)
        logger.info("🤖 TEST CON AI: Cambiar entre apps usando AITestRunner")
        logger.info("=" * 80)
        logger.info("")
        
        # App principal configurada
        main_app_package = driver_setup.capabilities.get("appPackage") or driver_setup.capabilities.get("appium:appPackage")
        logger.info(f"📱 App principal: {main_app_package}")
        
        allure_attach_screenshot(driver_setup, "01_inicial_ai")
        
        # Verificar si Settings está disponible
        from src.agent_tools import AppiumSkills
        from src.ui_parser import UIParser
        ui_parser = UIParser()
        agent_tools = AppiumSkills(driver_setup, ui_parser)
        
        settings_state, settings_state_name = agent_tools.query_app_state(SETTINGS_PACKAGE)
        logger.info(f"Estado de Settings: {settings_state_name} ({settings_state})")
        
        if settings_state == 0:  # NOT_INSTALLED
            pytest.skip("Settings no está instalada, no se puede probar cambio de apps")
        
        # ═══════════════════════════════════════════════════════════════════
        # TEST: Usar AI para cambiar a Settings
        # ═══════════════════════════════════════════════════════════════════
        logger.info("")
        logger.info("╔" + "═" * 78 + "╗")
        logger.info("║  TEST: Cambiar a Settings usando AI")
        logger.info("╚" + "═" * 78 + "╝")
        logger.info("")
        
        objective = f"Cambiar a la app Settings ({SETTINGS_PACKAGE}) y verificar que se abrió correctamente"
        
        runner = AITestRunner(driver=driver_setup, objective=objective)
        
        test_plan = [
            f"Abrir la app Settings (package: {SETTINGS_PACKAGE})",
            "Verificar que Settings se abrió correctamente buscando texto 'Settings' o 'Configuración'",
        ]
        
        logger.info(f"🎯 Objetivo: {objective}")
        logger.info(f"📋 Plan de prueba: {test_plan}")
        
        success = runner.run_test_plan(test_plan)
        
        allure_attach_screenshot(driver_setup, "02_after_ai_open_settings")
        
        assert success, "El plan de prueba no se completó exitosamente"
        logger.info("✓ AI logró cambiar a Settings")
        
        # ═══════════════════════════════════════════════════════════════════
        # TEST: Usar AI para volver a la app principal
        # ═══════════════════════════════════════════════════════════════════
        if main_app_package:
            logger.info("")
            logger.info("╔" + "═" * 78 + "╗")
            logger.info("║  TEST: Volver a app principal usando AI")
            logger.info("╚" + "═" * 78 + "╝")
            logger.info("")
            
            objective_return = f"Volver a la app principal (package: {main_app_package})"
            
            runner_return = AITestRunner(driver=driver_setup, objective=objective_return)
            
            test_plan_return = [
                f"Abrir la app principal (package: {main_app_package})",
                "Verificar que la app principal se abrió correctamente",
            ]
            
            logger.info(f"🎯 Objetivo: {objective_return}")
            logger.info(f"📋 Plan de prueba: {test_plan_return}")
            
            success_return = runner_return.run_test_plan(test_plan_return)
            
            allure_attach_screenshot(driver_setup, "03_after_ai_return_main_app")
            
            assert success_return, "El plan de prueba de retorno no se completó exitosamente"
            logger.info("✓ AI logró volver a la app principal")
        
        # ═══════════════════════════════════════════════════════════════════
        # RESUMEN FINAL
        # ═══════════════════════════════════════════════════════════════════
        logger.info("")
        logger.info("╔" + "═" * 78 + "╗")
        logger.info("║  RESUMEN FINAL")
        logger.info("╚" + "═" * 78 + "╝")
        logger.info("")
        
        allure_attach_debug_snapshot(driver_setup, "04_final_ai")
        
        logger.info("✅ Test con AI completado exitosamente")
        logger.info("=" * 80)
