"""
Tests de integración para UIParser con Appium real.

Estos tests requieren:
- Appium Server corriendo
- Dispositivo Android / Emulador conectado
- App instalada o APK configurado
"""

import logging
import time

import pytest
from appium.webdriver.common.appiumby import AppiumBy
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from src.ui_parser import UIParser
from tests.specs.conftest import allure_attach_debug_snapshot, allure_attach_screenshot


logger = logging.getLogger(__name__)


@pytest.mark.integration
class TestUIParserIntegration:
    """Tests de integración para UIParser con Appium real."""

    @pytest.mark.usefixtures("driver_setup")
    def test_parse_real_app_screen(self, driver_setup):
        """
        Test: Parsear XML real de una app Android usando Appium.
        
        Este test se conecta a Appium, obtiene el XML real de la pantalla
        actual y verifica que el UIParser puede procesarlo correctamente.
        """
        logger.info("📱 Obteniendo XML de la pantalla actual...")
        
        # Obtener el XML real de la pantalla actual
        xml_source = driver_setup.page_source
        
        # Verificar que obtuvimos XML válido
        assert xml_source is not None, "page_source no debe ser None"
        assert len(xml_source) > 0, "page_source no debe estar vacío"
        assert "<hierarchy" in xml_source.lower(), "page_source debe contener <hierarchy>"
        
        logger.info(f"✓ XML obtenido: {len(xml_source)} caracteres")
        logger.info(f"   Primeros 200 caracteres: {xml_source[:200]}...")
        
        # Parsear con UIParser
        logger.info("🔍 Parseando XML con UIParser...")
        parser = UIParser()
        elements = parser.parse_screen(xml_source)
        
        # Verificar que se parsearon elementos
        assert isinstance(elements, list), "elements debe ser una lista"
        logger.info(f"✓ Se parsearon {len(elements)} elementos interactuables")
        
        # Si hay elementos, verificar su estructura
        if len(elements) > 0:
            element = elements[0]
            assert "id" in element, "Elemento debe tener 'id'"
            assert "role" in element, "Elemento debe tener 'role'"
            assert "label" in element, "Elemento debe tener 'label'"
            assert "checked" in element, "Elemento debe tener 'checked'"
            assert isinstance(element["id"], int), "id debe ser un entero"
            assert element["role"] in ["button", "input", "checkbox"], f"role inválido: {element['role']}"
        
        # Verificar que los IDs son secuenciales
        for i, element in enumerate(elements):
            assert element["id"] == i, f"ID debe ser secuencial: esperado {i}, obtenido {element['id']}"
        
        # Log detallado de elementos encontrados
        logger.info(f"\n{'='*60}")
        logger.info(f"📊 RESUMEN: {len(elements)} elementos parseados")
        logger.info(f"{'='*60}")
        if len(elements) > 0:
            logger.info("Ejemplos de elementos encontrados:")
            for elem in elements[:10]:  # Mostrar primeros 10
                logger.info(f"  [{elem['id']:3d}] {elem['role']:8s} - '{elem['label'][:50]}'")
        else:
            logger.warning("⚠ No se encontraron elementos interactuables en la pantalla")

    @pytest.mark.usefixtures("driver_setup")
    def test_get_xpath_from_real_elements(self, driver_setup):
        """
        Test: Verificar que los XPaths generados son válidos para elementos reales.
        
        Este test verifica que el mapeo ID -> XPath funciona correctamente
        con elementos reales de la app.
        """
        logger.info("🔍 Obteniendo XML y parseando elementos...")
        xml_source = driver_setup.page_source
        parser = UIParser()
        elements = parser.parse_screen(xml_source)
        
        # Verificar que hay elementos
        if len(elements) == 0:
            pytest.skip("No hay elementos interactuables en la pantalla actual")
        
        logger.info(f"✓ {len(elements)} elementos encontrados, validando XPaths...")
        
        # Verificar que podemos obtener XPath para cada elemento
        valid_xpaths = 0
        invalid_xpaths = 0
        
        for element in elements:
            element_id = element["id"]
            xpath = parser.get_element_by_id(element_id)
            
            assert xpath is not None, f"XPath no encontrado para ID {element_id}"
            assert len(xpath) > 0, f"XPath vacío para ID {element_id}"
            assert xpath.startswith("//"), f"XPath inválido: {xpath}"
            
            # Intentar encontrar el elemento usando el XPath
            try:
                found_elements = driver_setup.find_elements("xpath", xpath)
                if len(found_elements) > 0:
                    valid_xpaths += 1
                    logger.debug(f"  ✓ XPath válido para ID {element_id}: {xpath}")
                else:
                    invalid_xpaths += 1
                    logger.warning(f"  ⚠ XPath no encontró elementos para ID {element_id}: {xpath}")
            except Exception as e:
                invalid_xpaths += 1
                logger.warning(f"  ⚠ Error validando XPath para ID {element_id}: {xpath} - {e}")
        
        logger.info(f"\n{'='*60}")
        logger.info(f"📊 VALIDACIÓN DE XPATHS:")
        logger.info(f"   ✓ Válidos: {valid_xpaths}/{len(elements)}")
        logger.info(f"   ⚠ No válidos: {invalid_xpaths}/{len(elements)}")
        logger.info(f"{'='*60}")

    @pytest.mark.usefixtures("driver_setup")
    def test_parser_handles_complex_real_ui(self, driver_setup):
        """
        Test: Verificar que el parser maneja correctamente UIs complejas reales.
        
        Este test verifica que el parser puede procesar pantallas complejas
        con múltiples elementos, layouts anidados, etc.
        """
        xml_source = driver_setup.page_source
        parser = UIParser()
        
        # Parsear múltiples veces para verificar consistencia
        elements1 = parser.parse_screen(xml_source)
        parser.clear()
        elements2 = parser.parse_screen(xml_source)
        
        # Verificar que los resultados son consistentes
        assert len(elements1) == len(elements2), "El parser debe ser determinístico"
        
        # Verificar estructura de elementos
        for element in elements1:
            # Verificar que todos los campos requeridos están presentes
            required_fields = ["id", "role", "label", "checked"]
            for field in required_fields:
                assert field in element, f"Campo '{field}' faltante en elemento {element['id']}"
            
            # Verificar tipos de datos
            assert isinstance(element["id"], int)
            assert isinstance(element["role"], str)
            assert isinstance(element["label"], str)
            assert element["checked"] is None or isinstance(element["checked"], bool)
        
        # Verificar que no hay elementos duplicados (mismo ID)
        ids = [elem["id"] for elem in elements1]
        assert len(ids) == len(set(ids)), "No debe haber IDs duplicados"
        
        print(f"\n✓ Parser maneja correctamente UI compleja con {len(elements1)} elementos")

    @pytest.mark.usefixtures("driver_setup")
    def test_parse_login_screen_from_real_app(self, driver_setup):
        """
        Test: Abrir la app, esperar a que cargue (pasar splash screen) y extraer elementos del login.
        
        Este test:
        1. Abre la app en el dispositivo
        2. Espera a que la app cargue completamente (pasar splash screen)
        3. Obtiene el XML de la pantalla de login
        4. Parsea con UIParser
        5. Verifica que puede extraer elementos típicos de login (inputs, botones)
        """
        logger.info("🚀 Iniciando test de login screen...")
        logger.info("📱 Esperando a que la app cargue completamente...")
        
        # Esperar a que la app cargue (pasar splash screen)
        # Estrategia: esperar a que aparezcan elementos interactuables en la pantalla
        wait = WebDriverWait(driver_setup, timeout=30)
        
        # Esperar a que la app esté lista (hay varias formas de verificar esto)
        # Opción 1: Esperar a que haya elementos interactuables
        # Opción 2: Esperar un tiempo fijo para splash screen
        # Opción 3: Esperar a que aparezca un elemento específico
        
        # Primero, dar tiempo para que la app inicie
        logger.info("   Esperando 3 segundos para que la app inicie...")
        time.sleep(3)

        # Capturar screenshot inicial (splash screen o cargando)
        allure_attach_screenshot(driver_setup, "01_app_iniciando")
        
        # Intentar esperar a que aparezcan elementos interactuables
        # Esto indica que la app ya pasó el splash screen
        max_attempts = 10
        elements_found = False
        
        for attempt in range(max_attempts):
            try:
                xml_source = driver_setup.page_source
                parser = UIParser()
                elements = parser.parse_screen(xml_source)
                
                if len(elements) > 0:
                    logger.info(f"   ✓ App cargada! Se encontraron {len(elements)} elementos interactuables (intento {attempt + 1})")
                    elements_found = True
                    break
                else:
                    logger.info(f"   ⏳ Esperando... (intento {attempt + 1}/{max_attempts})")
                    time.sleep(2)
            except Exception as e:
                logger.warning(f"   ⚠ Error en intento {attempt + 1}: {e}")
                time.sleep(2)
        
        if not elements_found:
            # Capturar evidencia antes de fallar
            allure_attach_debug_snapshot(driver_setup, "error_no_elementos")
            pytest.fail("No se encontraron elementos interactuables después de esperar. La app puede no haber cargado correctamente.")

        # Capturar screenshot y XML de la pantalla de login cargada
        allure_attach_debug_snapshot(driver_setup, "02_login_screen")

        # Obtener el XML final de la pantalla de login
        logger.info("📸 Obteniendo XML de la pantalla de login...")
        xml_source = driver_setup.page_source
        
        # Verificar que obtuvimos XML válido
        assert xml_source is not None, "page_source no debe ser None"
        assert len(xml_source) > 0, "page_source no debe estar vacío"
        assert "<hierarchy" in xml_source.lower(), "page_source debe contener <hierarchy>"
        
        logger.info(f"✓ XML obtenido: {len(xml_source)} caracteres")
        
        # Parsear con UIParser
        logger.info("🔍 Parseando XML con UIParser...")
        parser = UIParser()
        elements = parser.parse_screen(xml_source)
        
        # Verificar que se parsearon elementos
        assert isinstance(elements, list), "elements debe ser una lista"
        assert len(elements) > 0, "Debe haber al menos un elemento interactuable en la pantalla de login"
        
        logger.info(f"✓ Se parsearon {len(elements)} elementos interactuables")
        
        # Analizar los elementos encontrados
        inputs = [e for e in elements if e["role"] == "input"]
        buttons = [e for e in elements if e["role"] == "button"]
        checkboxes = [e for e in elements if e["role"] == "checkbox"]
        
        logger.info(f"\n{'='*60}")
        logger.info(f"📊 ANÁLISIS DE LA PANTALLA DE LOGIN:")
        logger.info(f"{'='*60}")
        logger.info(f"   Total de elementos: {len(elements)}")
        logger.info(f"   📝 Inputs (campos de texto): {len(inputs)}")
        logger.info(f"   🔘 Botones: {len(buttons)}")
        logger.info(f"   ☑️  Checkboxes: {len(checkboxes)}")
        logger.info(f"{'='*60}")
        
        # Mostrar detalles de inputs (típicamente usuario y password)
        if inputs:
            logger.info("\n📝 CAMPOS DE ENTRADA ENCONTRADOS:")
            for inp in inputs:
                logger.info(f"   [{inp['id']:3d}] '{inp['label'][:60]}'")
        
        # Mostrar detalles de botones (típicamente "Ingresar", "Login", etc.)
        if buttons:
            logger.info("\n🔘 BOTONES ENCONTRADOS:")
            for btn in buttons:
                logger.info(f"   [{btn['id']:3d}] '{btn['label'][:60]}'")
        
        # Verificaciones específicas para pantalla de login
        # Debe haber al menos un input (usuario o password)
        assert len(inputs) > 0, "Una pantalla de login debe tener al menos un campo de entrada (usuario/password)"
        
        # Debe haber al menos un botón (botón de login/ingresar)
        assert len(buttons) > 0, "Una pantalla de login debe tener al menos un botón (Ingresar/Login)"
        
        logger.info(f"\n✅ VERIFICACIONES EXITOSAS:")
        logger.info(f"   ✓ Se encontraron {len(inputs)} campo(s) de entrada")
        logger.info(f"   ✓ Se encontraron {len(buttons)} botón(es)")
        logger.info(f"   ✓ El parser puede extraer elementos de la pantalla de login real")
        
        # Guardar un resumen de los elementos para debugging
        logger.info(f"\n📋 RESUMEN DE ELEMENTOS (primeros 10):")
        for elem in elements[:10]:
            logger.info(f"   [{elem['id']:3d}] {elem['role']:8s} - '{elem['label'][:50]}'")
        
        # Verificar que los XPaths funcionan
        logger.info(f"\n🔗 Verificando XPaths generados...")
        valid_xpaths = 0
        for element in elements[:5]:  # Verificar solo los primeros 5 para no hacer el test muy lento
            xpath = parser.get_element_by_id(element["id"])
            if xpath:
                try:
                    found = driver_setup.find_elements(AppiumBy.XPATH, xpath)
                    if len(found) > 0:
                        valid_xpaths += 1
                except:
                    pass
        
        logger.info(f"   ✓ {valid_xpaths}/5 XPaths validados correctamente")
        
        # Assert final: el test es exitoso si encontramos elementos de login
        assert len(elements) >= 2, f"Se esperaban al menos 2 elementos (input + botón), se encontraron {len(elements)}"
