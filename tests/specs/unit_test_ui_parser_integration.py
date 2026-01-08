"""
Tests de integración para UIParser con Appium real.

Estos tests requieren:
- Appium Server corriendo
- Dispositivo Android / Emulador conectado
- App instalada o APK configurado
"""

import json
import logging
import time
import traceback
import xml.dom.minidom

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
        logger.info("🚀 Iniciando test de parseo de pantalla real...")
        logger.info("📱 Esperando a que la app cargue completamente...")
        
        # Esperar a que la app cargue (multiplicado por 4)
        logger.info("   Esperando 12 segundos para que la app inicie...")
        time.sleep(12)
        
        # Capturar screenshot inicial
        allure_attach_screenshot(driver_setup, "01_parse_test_inicial")
        
        logger.info("📱 Obteniendo XML de la pantalla actual...")
        
        # Obtener el XML real de la pantalla actual
        logger.debug("   Obteniendo page_source del driver...")
        xml_source = driver_setup.page_source
        logger.debug(f"   XML obtenido: {len(xml_source)} caracteres")
        
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
        logger.info("🚀 Iniciando test de validación de XPaths...")
        logger.info("📱 Esperando a que la app cargue completamente...")
        
        # Esperar a que la app cargue (pasar splash screen)
        # Primero, dar tiempo para que la app inicie (multiplicado por 4)
        logger.info("   Esperando 12 segundos para que la app inicie...")
        time.sleep(12)
        
        # Capturar screenshot inicial
        allure_attach_screenshot(driver_setup, "01_xpath_test_inicial")
        
        # Intentar esperar a que aparezcan elementos interactuables
        # Esto indica que la app ya pasó el splash screen
        max_attempts = 10
        elements_found = False
        parser = UIParser()
        
        logger.info("   Buscando elementos interactuables en la pantalla...")
        for attempt in range(max_attempts):
            try:
                logger.debug(f"   Intento {attempt + 1}/{max_attempts}: Obteniendo page_source...")
                xml_source = driver_setup.page_source
                
                logger.debug(f"   Intento {attempt + 1}/{max_attempts}: XML obtenido ({len(xml_source)} caracteres)")
                logger.debug(f"   Intento {attempt + 1}/{max_attempts}: Parseando con UIParser...")
                elements = parser.parse_screen(xml_source)
                
                logger.info(f"   Intento {attempt + 1}/{max_attempts}: Se encontraron {len(elements)} elementos interactuables")
                
                if len(elements) > 0:
                    logger.info(f"   ✓ App cargada! Se encontraron {len(elements)} elementos interactuables (intento {attempt + 1})")
                    elements_found = True
                    break
                else:
                    logger.info(f"   ⏳ Esperando... (intento {attempt + 1}/{max_attempts}) - No hay elementos aún")
                    logger.debug(f"   Intento {attempt + 1}/{max_attempts}: XML sample (primeros 500 chars): {xml_source[:500]}")
                    time.sleep(8)  # Multiplicado por 4 (era 2)
            except Exception as e:
                logger.warning(f"   ⚠ Error en intento {attempt + 1}: {type(e).__name__}: {e}")
                logger.debug(f"   Traceback: {traceback.format_exc()}")
                time.sleep(8)  # Multiplicado por 4 (era 2)
        
        if not elements_found:
            # Capturar evidencia antes de fallar
            logger.error("   ❌ No se encontraron elementos después de esperar")
            logger.error(f"   Se intentó {max_attempts} veces con esperas de 8 segundos")
            allure_attach_debug_snapshot(driver_setup, "error_no_elementos_xpath")
            
            # Intentar obtener el XML final para debugging
            try:
                final_xml = driver_setup.page_source
                logger.error(f"   XML final obtenido: {len(final_xml)} caracteres")
                logger.error(f"   Primeros 1000 caracteres del XML: {final_xml[:1000]}")
            except Exception as e:
                logger.error(f"   No se pudo obtener XML final: {e}")
            
            pytest.fail("No se encontraron elementos interactuables después de esperar. La app puede no haber cargado correctamente.")
        
        # Capturar screenshot y XML de la pantalla cargada
        allure_attach_debug_snapshot(driver_setup, "02_pantalla_cargada_xpath")
        
        logger.info("🔍 Obteniendo XML y parseando elementos...")
        xml_source = driver_setup.page_source
        elements = parser.parse_screen(xml_source)
        
        # Verificar que hay elementos
        if len(elements) == 0:
            logger.error("❌ No se encontraron elementos después de la espera inicial")
            allure_attach_debug_snapshot(driver_setup, "error_sin_elementos")
            pytest.fail("No hay elementos interactuables en la pantalla actual después de esperar a que la app cargue")
        
        logger.info(f"✓ {len(elements)} elementos encontrados, validando XPaths...")
        logger.info(f"\n{'='*60}")
        logger.info(f"📋 ELEMENTOS ENCONTRADOS (primeros 10):")
        logger.info(f"{'='*60}")
        for elem in elements[:10]:
            logger.info(f"   [{elem['id']:3d}] {elem['role']:8s} - '{elem['label'][:50]}'")
        logger.info(f"{'='*60}\n")
        
        # Verificar que podemos obtener XPath para cada elemento
        valid_xpaths = 0
        invalid_xpaths = 0
        
        logger.info(f"🔗 Validando XPaths para {len(elements)} elementos...")
        for idx, element in enumerate(elements):
            element_id = element["id"]
            logger.debug(f"   Procesando elemento {idx + 1}/{len(elements)} (ID: {element_id})...")
            
            xpath = parser.get_element_by_id(element_id)
            
            assert xpath is not None, f"XPath no encontrado para ID {element_id}"
            assert len(xpath) > 0, f"XPath vacío para ID {element_id}"
            assert xpath.startswith("//"), f"XPath inválido: {xpath}"
            
            logger.debug(f"   Elemento ID {element_id}: XPath obtenido = {xpath}")
            
            # Intentar encontrar el elemento usando el XPath
            try:
                logger.debug(f"   Elemento ID {element_id}: Buscando en el driver con XPath...")
                found_elements = driver_setup.find_elements("xpath", xpath)
                logger.debug(f"   Elemento ID {element_id}: Se encontraron {len(found_elements)} elementos con este XPath")
                
                if len(found_elements) > 0:
                    valid_xpaths += 1
                    logger.info(f"   ✓ [{element_id:3d}] XPath válido: {xpath[:80]}...")
                else:
                    invalid_xpaths += 1
                    logger.warning(f"   ⚠ [{element_id:3d}] XPath no encontró elementos: {xpath[:80]}...")
            except Exception as e:
                invalid_xpaths += 1
                logger.warning(f"   ⚠ [{element_id:3d}] Error validando XPath: {xpath[:80]}... - {type(e).__name__}: {e}")
                logger.debug(f"   Traceback completo: {traceback.format_exc()}")
        
        logger.info(f"\n{'='*60}")
        logger.info(f"📊 VALIDACIÓN DE XPATHS:")
        logger.info(f"   ✓ Válidos: {valid_xpaths}/{len(elements)} ({valid_xpaths*100/len(elements):.1f}%)")
        logger.info(f"   ⚠ No válidos: {invalid_xpaths}/{len(elements)} ({invalid_xpaths*100/len(elements):.1f}%)")
        logger.info(f"{'='*60}")

    @pytest.mark.usefixtures("driver_setup")
    def test_parser_handles_complex_real_ui(self, driver_setup):
        """
        Test: Verificar que el parser maneja correctamente UIs complejas reales.
        
        Este test verifica que el parser puede procesar pantallas complejas
        con múltiples elementos, layouts anidados, etc.
        """
        logger.info("🚀 Iniciando test de UI compleja...")
        logger.info("📱 Esperando a que la app cargue completamente...")
        
        # Esperar a que la app cargue (multiplicado por 4)
        logger.info("   Esperando 12 segundos para que la app inicie...")
        time.sleep(12)
        
        # Capturar screenshot inicial
        allure_attach_screenshot(driver_setup, "01_complex_ui_test_inicial")
        
        logger.info("📱 Obteniendo XML de la pantalla actual...")
        logger.debug("   Obteniendo page_source del driver...")
        xml_source = driver_setup.page_source
        logger.debug(f"   XML obtenido: {len(xml_source)} caracteres")
        
        logger.info("🔍 Creando instancia de UIParser...")
        parser = UIParser()
        
        # Parsear múltiples veces para verificar consistencia
        logger.info("🔍 Parseando XML (primera vez)...")
        elements1 = parser.parse_screen(xml_source)
        logger.info(f"   ✓ Primera pasada: {len(elements1)} elementos encontrados")
        
        logger.info("🔍 Limpiando parser y parseando nuevamente...")
        parser.clear()
        elements2 = parser.parse_screen(xml_source)
        logger.info(f"   ✓ Segunda pasada: {len(elements2)} elementos encontrados")
        
        # Verificar que los resultados son consistentes
        logger.info("🔍 Verificando consistencia entre pasadas...")
        assert len(elements1) == len(elements2), f"El parser debe ser determinístico: primera pasada={len(elements1)}, segunda pasada={len(elements2)}"
        logger.info("   ✓ Parser es determinístico")
        
        # Verificar estructura de elementos
        logger.info("🔍 Verificando estructura de elementos...")
        for idx, element in enumerate(elements1):
            logger.debug(f"   Verificando elemento {idx + 1}/{len(elements1)} (ID: {element.get('id', 'N/A')})...")
            
            # Verificar que todos los campos requeridos están presentes
            required_fields = ["id", "role", "label", "checked"]
            for field in required_fields:
                assert field in element, f"Campo '{field}' faltante en elemento {element.get('id', 'N/A')}"
            
            # Verificar tipos de datos
            assert isinstance(element["id"], int), f"ID debe ser int, es {type(element['id'])}"
            assert isinstance(element["role"], str), f"Role debe ser str, es {type(element['role'])}"
            assert isinstance(element["label"], str), f"Label debe ser str, es {type(element['label'])}"
            assert element["checked"] is None or isinstance(element["checked"], bool), f"Checked debe ser None o bool, es {type(element['checked'])}"
        
        logger.info(f"   ✓ Estructura de {len(elements1)} elementos verificada correctamente")
        
        # Verificar que no hay elementos duplicados (mismo ID)
        logger.info("🔍 Verificando que no hay IDs duplicados...")
        ids = [elem["id"] for elem in elements1]
        assert len(ids) == len(set(ids)), f"No debe haber IDs duplicados. IDs encontrados: {ids}"
        logger.info("   ✓ No hay IDs duplicados")
        
        logger.info(f"\n{'='*60}")
        logger.info(f"✅ Parser maneja correctamente UI compleja con {len(elements1)} elementos")
        logger.info(f"{'='*60}")

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
        
        # Primero, dar tiempo para que la app inicie (multiplicado por 4)
        logger.info("   Esperando 12 segundos para que la app inicie...")
        time.sleep(12)

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
                    logger.debug(f"   Intento {attempt + 1}/{max_attempts}: XML sample (primeros 500 chars): {xml_source[:500]}")
                    time.sleep(8)  # Multiplicado por 4 (era 2)
            except Exception as e:
                logger.warning(f"   ⚠ Error en intento {attempt + 1}: {type(e).__name__}: {e}")
                logger.debug(f"   Traceback: {traceback.format_exc()}")
                time.sleep(8)  # Multiplicado por 4 (era 2)
        
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

    @pytest.mark.usefixtures("driver_setup")
    def test_ai_parser_debug(self, driver_setup):
        """
        Test de depuración completo para el parser de IA.
        
        Este test muestra TODO lo que el parser procesa:
        - XML source completo (formateado)
        - JSON de elementos parseados (formateado)
        - JSON de elementos con XPaths (formateado)
        - TOON que le llega a la IA (formato eficiente)
        
        Ejecutar solo este test:
        poetry run pytest tests/specs/unit_test_ui_parser_integration.py::TestUIParserIntegration::test_ai_parser_debug -v -s
        """
        logger.info("")
        logger.info("=" * 80)
        logger.info("🔍 TEST DE DEPURACIÓN COMPLETO PARA PARSER DE IA")
        logger.info("=" * 80)
        logger.info("")
        
        # Esperar a que la app cargue
        logger.info("📱 Esperando a que la app cargue completamente...")
        logger.info("   Esperando 12 segundos para que la app inicie...")
        time.sleep(12)
        
        # Capturar screenshot inicial
        allure_attach_screenshot(driver_setup, "01_ai_parser_debug_inicial")
        
        # ═══════════════════════════════════════════════════════════════════
        # FASE 1: Obtener XML Source
        # ═══════════════════════════════════════════════════════════════════
        logger.info("")
        logger.info("╔" + "═" * 78 + "╗")
        logger.info("║  FASE 1: OBTENER XML SOURCE")
        logger.info("╚" + "═" * 78 + "╝")
        logger.info("")
        
        logger.info("📱 Obteniendo page_source del driver...")
        xml_source = driver_setup.page_source
        
        assert xml_source is not None, "page_source no debe ser None"
        assert len(xml_source) > 0, "page_source no debe estar vacío"
        assert "<hierarchy" in xml_source.lower(), "page_source debe contener <hierarchy>"
        
        logger.info(f"✓ XML obtenido: {len(xml_source)} caracteres")
        
        # Formatear XML para mejor legibilidad
        logger.info("")
        logger.info("📄 XML SOURCE (FORMATEADO):")
        logger.info("─" * 80)
        try:
            # Intentar formatear el XML
            dom = xml.dom.minidom.parseString(xml_source)
            formatted_xml = dom.toprettyxml(indent="  ")
            # Limpiar líneas vacías excesivas
            lines = [line for line in formatted_xml.split('\n') if line.strip()]
            formatted_xml = '\n'.join(lines)
            
            # Mostrar XML completo (puede ser largo, pero el usuario lo pidió)
            logger.info(formatted_xml)
            logger.info("─" * 80)
            logger.info(f"✓ XML formateado: {len(formatted_xml)} caracteres")
        except Exception as e:
            logger.warning(f"⚠ No se pudo formatear XML: {e}")
            logger.info("📄 XML SOURCE (SIN FORMATEAR):")
            logger.info("─" * 80)
            logger.info(xml_source)
            logger.info("─" * 80)
        
        # ═══════════════════════════════════════════════════════════════════
        # FASE 2: Parsear con UIParser
        # ═══════════════════════════════════════════════════════════════════
        logger.info("")
        logger.info("╔" + "═" * 78 + "╗")
        logger.info("║  FASE 2: PARSEAR CON UIPARSER")
        logger.info("╚" + "═" * 78 + "╝")
        logger.info("")
        
        logger.info("🔍 Creando instancia de UIParser...")
        parser = UIParser()
        
        logger.info("🔍 Parseando XML con UIParser...")
        elements = parser.parse_screen(xml_source)
        
        assert isinstance(elements, list), "elements debe ser una lista"
        assert len(elements) > 0, "Debe haber al menos un elemento interactuable"
        
        logger.info(f"✓ Se parsearon {len(elements)} elementos interactuables")
        
        # ═══════════════════════════════════════════════════════════════════
        # FASE 3: Mostrar JSON de elementos (formateado)
        # ═══════════════════════════════════════════════════════════════════
        logger.info("")
        logger.info("╔" + "═" * 78 + "╗")
        logger.info("║  FASE 3: JSON DE ELEMENTOS PARSEADOS (FORMATEADO)")
        logger.info("╚" + "═" * 78 + "╝")
        logger.info("")
        
        # Convertir a JSON formateado
        json_output = json.dumps(elements, indent=2, ensure_ascii=False)
        
        logger.info("📋 JSON COMPLETO DE ELEMENTOS:")
        logger.info("─" * 80)
        logger.info(json_output)
        logger.info("─" * 80)
        logger.info(f"✓ JSON generado: {len(json_output)} caracteres")
        
        # ═══════════════════════════════════════════════════════════════════
        # FASE 4: Mostrar JSON con XPaths
        # ═══════════════════════════════════════════════════════════════════
        logger.info("")
        logger.info("╔" + "═" * 78 + "╗")
        logger.info("║  FASE 4: JSON DE ELEMENTOS CON XPATHS")
        logger.info("╚" + "═" * 78 + "╝")
        logger.info("")
        
        # Crear lista de elementos con XPaths
        elements_with_xpath = []
        for element in elements:
            element_id = element["id"]
            xpath = parser.get_element_by_id(element_id)
            
            element_with_xpath = element.copy()
            element_with_xpath["xpath"] = xpath if xpath else "NOT_FOUND"
            elements_with_xpath.append(element_with_xpath)
        
        # Convertir a JSON formateado
        json_with_xpath = json.dumps(elements_with_xpath, indent=2, ensure_ascii=False)
        
        logger.info("📋 JSON CON XPATHS:")
        logger.info("─" * 80)
        logger.info(json_with_xpath)
        logger.info("─" * 80)
        logger.info(f"✓ JSON con XPaths generado: {len(json_with_xpath)} caracteres")
        
        # Mostrar resumen de XPaths
        logger.info("")
        logger.info("📊 RESUMEN DE XPATHS:")
        logger.info("─" * 80)
        for elem in elements_with_xpath:
            logger.info(f"  [{elem['id']:3d}] {elem['role']:8s} - XPath: {elem['xpath']}")
        logger.info("─" * 80)
        
        # ═══════════════════════════════════════════════════════════════════
        # FASE 5: Mostrar TOON (formato que le llega a la IA)
        # ═══════════════════════════════════════════════════════════════════
        logger.info("")
        logger.info("╔" + "═" * 78 + "╗")
        logger.info("║  FASE 5: TOON (FORMATO QUE LLEGA A LA IA)")
        logger.info("╚" + "═" * 78 + "╝")
        logger.info("")
        
        logger.info("🔍 Convirtiendo elementos a formato TOON...")
        toon_output = parser.elements_to_toon(elements)
        
        logger.info("")
        logger.info("📋 TOON COMPLETO (30-60% menos tokens que JSON):")
        logger.info("─" * 80)
        logger.info(toon_output)
        logger.info("─" * 80)
        logger.info(f"✓ TOON generado: {len(toon_output)} caracteres")
        
        # Comparación de tamaños
        logger.info("")
        logger.info("📊 COMPARACIÓN DE TAMAÑOS:")
        logger.info("─" * 80)
        logger.info(f"  JSON:     {len(json_output):,} caracteres")
        logger.info(f"  TOON:     {len(toon_output):,} caracteres")
        reduction = ((len(json_output) - len(toon_output)) / len(json_output)) * 100 if len(json_output) > 0 else 0
        logger.info(f"  Reducción: {reduction:.1f}% menos caracteres con TOON")
        logger.info("─" * 80)
        
        # ═══════════════════════════════════════════════════════════════════
        # FASE 6: Resumen final
        # ═══════════════════════════════════════════════════════════════════
        logger.info("")
        logger.info("╔" + "═" * 78 + "╗")
        logger.info("║  RESUMEN FINAL")
        logger.info("╚" + "═" * 78 + "╝")
        logger.info("")
        
        # Contar por tipo
        inputs = [e for e in elements if e["role"] == "input"]
        buttons = [e for e in elements if e["role"] == "button"]
        checkboxes = [e for e in elements if e["role"] == "checkbox"]
        
        logger.info(f"📊 ESTADÍSTICAS:")
        logger.info(f"   Total de elementos: {len(elements)}")
        logger.info(f"   📝 Inputs: {len(inputs)}")
        logger.info(f"   🔘 Botones: {len(buttons)}")
        logger.info(f"   ☑️  Checkboxes: {len(checkboxes)}")
        logger.info("")
        logger.info(f"📏 TAMAÑOS:")
        logger.info(f"   XML source: {len(xml_source):,} caracteres")
        logger.info(f"   JSON:       {len(json_output):,} caracteres")
        logger.info(f"   TOON:       {len(toon_output):,} caracteres")
        logger.info(f"   Ahorro:     {reduction:.1f}% con TOON")
        logger.info("")
        logger.info("✅ Test de depuración completado exitosamente")
        logger.info("")
        logger.info("=" * 80)
        
        # Capturar evidencia final
        allure_attach_debug_snapshot(driver_setup, "02_ai_parser_debug_final")
        
        # Assert final
        assert len(elements) > 0, "Debe haber al menos un elemento parseado"
        assert len(toon_output) > 0, "El TOON no debe estar vacío"
