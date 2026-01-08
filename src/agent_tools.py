"""
Agent Tools - Herramientas de alto nivel para interactuar con Appium.
"""

import time
import logging
import traceback
from typing import Optional
from appium.webdriver.common.appiumby import AppiumBy
from appium.webdriver import Remote

from src.ui_parser import UIParser

# Configurar logging para este módulo
logger = logging.getLogger(__name__)


class AppiumSkills:
    """
    Clase que proporciona métodos de alto nivel para interactuar con Appium.
    Integrada con UIParser para usar IDs temporales de elementos.
    """

    def __init__(self, driver: Remote, ui_parser: UIParser):
        """
        Inicializa AppiumSkills.

        Args:
            driver: Instancia del driver de Appium
            ui_parser: Instancia de UIParser para mapear IDs a XPath
        """
        logger.info("AGENT_TOOLS: Inicializando AppiumSkills")
        
        self.driver = driver
        self.ui_parser = ui_parser
        self.default_wait_timeout = 5
        self.min_wait_timeout = 0.3
        
        # Estadísticas de acciones
        self._action_stats = {
            "total_actions": 0,
            "successful_actions": 0,
            "failed_actions": 0,
            "actions_by_type": {},
        }
        
        # Verificar que el driver esté activo
        try:
            session_id = self.driver.session_id
            logger.info(f"AGENT_TOOLS: ✓ Driver activo con session_id: {session_id}")
        except Exception as e:
            logger.error(f"AGENT_TOOLS ERROR: Driver no disponible: {e}")
            raise
        
        logger.debug(f"AGENT_TOOLS: default_wait_timeout={self.default_wait_timeout}s, "
                    f"min_wait_timeout={self.min_wait_timeout}s")

    def get_screen_tree(self) -> str:
        """
        Obtiene el XML de la pantalla actual.

        Returns:
            String con el XML completo de page_source
        """
        logger.debug("AGENT_TOOLS: Obteniendo page_source (screen tree)...")
        
        start_time = time.time()
        try:
            page_source = self.driver.page_source
            elapsed_ms = int((time.time() - start_time) * 1000)
            
            logger.debug(f"AGENT_TOOLS: ✓ page_source obtenido en {elapsed_ms}ms "
                        f"({len(page_source)} caracteres)")
            
            # Verificación básica de validez
            if not page_source or len(page_source) < 50:
                logger.warning(f"AGENT_TOOLS WARNING: page_source parece inválido o muy corto: "
                              f"{len(page_source) if page_source else 0} chars")
            
            return page_source
            
        except Exception as e:
            elapsed_ms = int((time.time() - start_time) * 1000)
            logger.error(f"AGENT_TOOLS ERROR: Fallo al obtener page_source después de {elapsed_ms}ms")
            logger.error(f"AGENT_TOOLS ERROR: {type(e).__name__}: {str(e)}")
            logger.error(f"AGENT_TOOLS ERROR: Traceback:\n{traceback.format_exc()}")
            raise

    def touch_element_by_id(self, element_id: int) -> str:
        """
        Hace clic en un elemento usando su ID del UIParser.

        Args:
            element_id: ID del elemento (asignado por UIParser)

        Returns:
            Mensaje de éxito o error
        """
        action_name = "touch_element_by_id"
        self._action_stats["total_actions"] += 1
        self._action_stats["actions_by_type"][action_name] = self._action_stats["actions_by_type"].get(action_name, 0) + 1
        
        logger.info(f"AGENT_TOOLS: 🖱️ Ejecutando {action_name}(element_id={element_id})")
        
        # Paso 1: Obtener XPath del mapeo
        logger.debug(f"AGENT_TOOLS: Buscando XPath para ID {element_id}...")
        xpath = self.ui_parser.get_element_by_id(element_id)
        
        if not xpath:
            error_msg = f"Error: Elemento con ID {element_id} no encontrado en el mapeo"
            logger.error(f"AGENT_TOOLS ERROR: {error_msg}")
            logger.error(f"AGENT_TOOLS ERROR: IDs disponibles: {list(self.ui_parser.element_map.keys())}")
            # DEBUG: Dump completo del mapeo para diagnóstico
            self.ui_parser.debug_dump_element_map(log_output=True)
            self._action_stats["failed_actions"] += 1
            return error_msg
        
        logger.debug(f"AGENT_TOOLS: XPath encontrado: {xpath}")

        # Paso 2: Buscar elemento en la UI
        start_time = time.time()
        try:
            logger.debug(f"AGENT_TOOLS: Buscando elemento con XPath...")
            element = self.driver.find_element(AppiumBy.XPATH, xpath)
            logger.debug(f"AGENT_TOOLS: ✓ Elemento encontrado")
            
            # Log info del elemento
            try:
                elem_text = element.get_attribute("text") or ""
                elem_class = element.get_attribute("class") or ""
                logger.debug(f"AGENT_TOOLS: Elemento - class={elem_class}, text='{elem_text[:50]}'")
            except Exception:
                pass
            
            # Paso 3: Hacer click
            logger.debug("AGENT_TOOLS: Ejecutando click...")
            element.click()
            time.sleep(self.min_wait_timeout)
            
            elapsed_ms = int((time.time() - start_time) * 1000)
            success_msg = f"Success: Clicked on element ID {element_id}"
            logger.info(f"AGENT_TOOLS: ✓ {success_msg} (en {elapsed_ms}ms)")
            self._action_stats["successful_actions"] += 1
            return success_msg
            
        except Exception as e:
            elapsed_ms = int((time.time() - start_time) * 1000)
            error_msg = f"Error: Could not click element ID {element_id}: {str(e)}"
            logger.error(f"AGENT_TOOLS ERROR: {error_msg} (después de {elapsed_ms}ms)")
            logger.error(f"AGENT_TOOLS ERROR: XPath usado: {xpath}")
            logger.error(f"AGENT_TOOLS ERROR: Traceback:\n{traceback.format_exc()}")
            
            # Diagnóstico
            if "NoSuchElement" in str(type(e).__name__):
                logger.error("AGENT_TOOLS DIAGNÓSTICO: El elemento no existe en la pantalla actual. "
                           "Posible causa: la UI cambió después del parseo")
            elif "StaleElement" in str(type(e).__name__):
                logger.error("AGENT_TOOLS DIAGNÓSTICO: Elemento stale - la UI cambió. "
                           "Necesita re-parseo de pantalla")
            
            self._action_stats["failed_actions"] += 1
            return error_msg

    def touch_element_by_text(self, text_description: str) -> str:
        """
        Intenta encontrar un elemento que contenga el texto y hace clic.
        Estrategia: Busca por texto exacto, luego contiene, luego content-desc.

        Args:
            text_description: Texto visible del elemento

        Returns:
            Mensaje de éxito o error
        """
        try:
            # Estrategia: XPath dinámico basado en texto
            xpath = (
                f"//*[@text='{text_description}' or contains(@text, '{text_description}') "
                f"or @content-desc='{text_description}' or contains(@content-desc, '{text_description}')]"
            )
            element = self.driver.find_element(AppiumBy.XPATH, xpath)
            element.click()
            time.sleep(self.min_wait_timeout)
            return f"Success: Clicked on '{text_description}'"
        except Exception as e:
            return f"Error: Could not find element with text '{text_description}': {str(e)}"

    def fill_field_by_id(self, element_id: int, value: str) -> str:
        """
        Escribe texto en un campo usando su ID del UIParser.

        Args:
            element_id: ID del elemento (asignado por UIParser)
            value: Texto a escribir

        Returns:
            Mensaje de éxito o error
        """
        action_name = "fill_field_by_id"
        self._action_stats["total_actions"] += 1
        self._action_stats["actions_by_type"][action_name] = self._action_stats["actions_by_type"].get(action_name, 0) + 1
        
        logger.info(f"AGENT_TOOLS: ⌨️ Ejecutando {action_name}(element_id={element_id}, value='{value}')")
        
        # Paso 1: Obtener XPath del mapeo
        logger.debug(f"AGENT_TOOLS: Buscando XPath para ID {element_id}...")
        xpath = self.ui_parser.get_element_by_id(element_id)
        
        if not xpath:
            error_msg = f"Error: Elemento con ID {element_id} no encontrado en el mapeo"
            logger.error(f"AGENT_TOOLS ERROR: {error_msg}")
            # DEBUG: Dump completo del mapeo para diagnóstico
            self.ui_parser.debug_dump_element_map(log_output=True)
            self._action_stats["failed_actions"] += 1
            return error_msg
        
        logger.debug(f"AGENT_TOOLS: XPath encontrado: {xpath}")

        start_time = time.time()
        try:
            # Paso 2: Buscar elemento
            logger.debug("AGENT_TOOLS: Buscando elemento con XPath...")
            element = self.driver.find_element(AppiumBy.XPATH, xpath)
            logger.debug("AGENT_TOOLS: ✓ Elemento encontrado")
            
            # Paso 3: Click para enfocar
            logger.debug("AGENT_TOOLS: Haciendo click para enfocar...")
            element.click()
            time.sleep(self.min_wait_timeout)
            
            # Paso 4: Limpiar campo
            logger.debug("AGENT_TOOLS: Limpiando campo...")
            element.clear()
            
            # Paso 5: Escribir texto
            logger.debug(f"AGENT_TOOLS: Escribiendo texto: '{value}'")
            element.send_keys(value)
            
            # Paso 6: Ocultar teclado
            logger.debug("AGENT_TOOLS: Ocultando teclado...")
            keyboard_hidden = self.hide_keyboard()
            logger.debug(f"AGENT_TOOLS: Teclado {'ocultado' if keyboard_hidden else 'no estaba visible'}")
            
            elapsed_ms = int((time.time() - start_time) * 1000)
            success_msg = f"Success: Typed '{value}' into element ID {element_id}"
            logger.info(f"AGENT_TOOLS: ✓ {success_msg} (en {elapsed_ms}ms)")
            self._action_stats["successful_actions"] += 1
            return success_msg
            
        except Exception as e:
            elapsed_ms = int((time.time() - start_time) * 1000)
            error_msg = f"Error: Could not fill field ID {element_id}: {str(e)}"
            logger.error(f"AGENT_TOOLS ERROR: {error_msg} (después de {elapsed_ms}ms)")
            logger.error(f"AGENT_TOOLS ERROR: XPath usado: {xpath}")
            logger.error(f"AGENT_TOOLS ERROR: Valor intentado: '{value}'")
            logger.error(f"AGENT_TOOLS ERROR: Traceback:\n{traceback.format_exc()}")
            self._action_stats["failed_actions"] += 1
            return error_msg

    def fill_field(self, field_hint: str, value: str) -> str:
        """
        Encuentra un input y escribe texto.

        Args:
            field_hint: Texto placeholder o etiqueta cercana al input
            value: Valor a escribir

        Returns:
            Mensaje de éxito o error
        """
        try:
            # Busca elementos de tipo EditText o Input
            xpath = (
                f"//android.widget.EditText[contains(@text, '{field_hint}') "
                f"or contains(@content-desc, '{field_hint}') "
                f"or contains(@hint, '{field_hint}')]"
            )
            element = self.driver.find_element(AppiumBy.XPATH, xpath)
            element.click()
            time.sleep(self.min_wait_timeout)
            element.clear()
            element.send_keys(value)
            self.hide_keyboard()
            return f"Success: Typed '{value}' into '{field_hint}'"
        except Exception as e:
            return f"Error: Input field '{field_hint}' not found: {str(e)}"

    def scroll(self, direction: str = "down") -> str:
        """
        Realiza scroll en la dirección especificada.

        Args:
            direction: "up" o "down"

        Returns:
            Mensaje de éxito o error
        """
        action_name = "scroll"
        self._action_stats["total_actions"] += 1
        self._action_stats["actions_by_type"][action_name] = self._action_stats["actions_by_type"].get(action_name, 0) + 1
        
        logger.info(f"AGENT_TOOLS: 📜 Ejecutando scroll(direction='{direction}')")
        
        # Validar dirección
        if direction not in ["up", "down"]:
            error_msg = f"Error: Dirección de scroll inválida: '{direction}'. Debe ser 'up' o 'down'"
            logger.error(f"AGENT_TOOLS ERROR: {error_msg}")
            self._action_stats["failed_actions"] += 1
            return error_msg
        
        start_time = time.time()
        try:
            # Obtener dimensiones de pantalla
            size = self.driver.get_window_size()
            width = size["width"]
            height = size["height"]
            logger.debug(f"AGENT_TOOLS: Dimensiones de pantalla: {width}x{height}")

            # Calcular coordenadas de swipe
            start_x = width // 2
            start_y = height // 2
            end_y = int(height * 0.2) if direction == "down" else int(height * 0.8)
            
            logger.debug(f"AGENT_TOOLS: Swipe desde ({start_x}, {start_y}) hasta ({start_x}, {end_y})")

            self.driver.swipe(start_x, start_y, start_x, end_y, duration=500)
            time.sleep(self.min_wait_timeout)
            
            elapsed_ms = int((time.time() - start_time) * 1000)
            success_msg = f"Success: Scrolled {direction}"
            logger.info(f"AGENT_TOOLS: ✓ {success_msg} (en {elapsed_ms}ms)")
            self._action_stats["successful_actions"] += 1
            return success_msg
            
        except Exception as e:
            elapsed_ms = int((time.time() - start_time) * 1000)
            error_msg = f"Error: Could not scroll {direction}: {str(e)}"
            logger.error(f"AGENT_TOOLS ERROR: {error_msg} (después de {elapsed_ms}ms)")
            logger.error(f"AGENT_TOOLS ERROR: Traceback:\n{traceback.format_exc()}")
            self._action_stats["failed_actions"] += 1
            return error_msg

    def go_back(self) -> str:
        """
        Presiona el botón atrás del dispositivo.

        Returns:
            Mensaje de éxito o error
        """
        action_name = "go_back"
        self._action_stats["total_actions"] += 1
        self._action_stats["actions_by_type"][action_name] = self._action_stats["actions_by_type"].get(action_name, 0) + 1
        
        logger.info("AGENT_TOOLS: ⬅️ Ejecutando go_back()")
        
        start_time = time.time()
        try:
            self.driver.back()
            time.sleep(self.min_wait_timeout)
            
            elapsed_ms = int((time.time() - start_time) * 1000)
            success_msg = "Success: Pressed back button"
            logger.info(f"AGENT_TOOLS: ✓ {success_msg} (en {elapsed_ms}ms)")
            self._action_stats["successful_actions"] += 1
            return success_msg
            
        except Exception as e:
            elapsed_ms = int((time.time() - start_time) * 1000)
            error_msg = f"Error: Could not press back button: {str(e)}"
            logger.error(f"AGENT_TOOLS ERROR: {error_msg} (después de {elapsed_ms}ms)")
            logger.error(f"AGENT_TOOLS ERROR: Traceback:\n{traceback.format_exc()}")
            self._action_stats["failed_actions"] += 1
            return error_msg

    def hide_keyboard(self) -> bool:
        """
        Oculta el teclado si está visible.

        Returns:
            True si se ocultó, False si no estaba visible
        """
        logger.debug("AGENT_TOOLS: Verificando si el teclado está visible...")
        try:
            if self.driver.is_keyboard_shown():
                logger.debug("AGENT_TOOLS: Teclado visible, ocultando...")
                self.driver.hide_keyboard()
                time.sleep(self.min_wait_timeout)
                logger.debug("AGENT_TOOLS: ✓ Teclado ocultado")
                return True
            logger.debug("AGENT_TOOLS: Teclado no estaba visible")
            return False
        except Exception as e:
            logger.warning(f"AGENT_TOOLS WARNING: Error al manejar teclado: {e}")
            return False

    def assert_screen_contains(self, text: str) -> tuple[bool, str]:
        """
        Valida que la pantalla contenga un texto específico.

        Args:
            text: Texto a buscar

        Returns:
            Tupla (is_present, message)
        """
        action_name = "assert_screen_contains"
        self._action_stats["total_actions"] += 1
        self._action_stats["actions_by_type"][action_name] = self._action_stats["actions_by_type"].get(action_name, 0) + 1
        
        logger.info(f"AGENT_TOOLS: 🔍 Ejecutando assert_screen_contains(text='{text}')")
        
        start_time = time.time()
        try:
            page_source = self.driver.page_source
            logger.debug(f"AGENT_TOOLS: page_source obtenido ({len(page_source)} chars)")
            
            # Búsqueda del texto
            if text in page_source:
                elapsed_ms = int((time.time() - start_time) * 1000)
                success_msg = f"Success: Found text '{text}' on screen"
                logger.info(f"AGENT_TOOLS: ✓ {success_msg} (en {elapsed_ms}ms)")
                self._action_stats["successful_actions"] += 1
                return True, success_msg
            else:
                elapsed_ms = int((time.time() - start_time) * 1000)
                error_msg = f"Error: Text '{text}' not found on screen"
                logger.warning(f"AGENT_TOOLS: ✗ {error_msg} (en {elapsed_ms}ms)")
                
                # Debug: mostrar qué textos SÍ están en pantalla
                import re
                all_texts = re.findall(r'text="([^"]+)"', page_source)
                if all_texts:
                    logger.debug(f"AGENT_TOOLS DEBUG: Textos encontrados en pantalla:")
                    for t in all_texts[:20]:  # Limitar a 20 para no saturar logs
                        logger.debug(f"  - '{t}'")
                    if len(all_texts) > 20:
                        logger.debug(f"  ... y {len(all_texts) - 20} más")
                
                self._action_stats["failed_actions"] += 1
                return False, error_msg
                
        except Exception as e:
            elapsed_ms = int((time.time() - start_time) * 1000)
            error_msg = f"Error: Could not check for text '{text}': {str(e)}"
            logger.error(f"AGENT_TOOLS ERROR: {error_msg} (después de {elapsed_ms}ms)")
            logger.error(f"AGENT_TOOLS ERROR: Traceback:\n{traceback.format_exc()}")
            self._action_stats["failed_actions"] += 1
            return False, error_msg
    
    def get_action_stats(self) -> dict:
        """
        DEBUG: Retorna estadísticas de acciones ejecutadas.
        """
        stats = self._action_stats.copy()
        if stats["total_actions"] > 0:
            stats["success_rate"] = f"{(stats['successful_actions'] / stats['total_actions']) * 100:.1f}%"
        return stats

    def dismiss_popup(self) -> str:
        """
        Intenta cerrar popups automáticamente buscando botones de cierre comunes.

        Returns:
            Mensaje de éxito o error
        """
        # Buscar botones comunes de cierre
        close_buttons = ["X", "Cerrar", "Close", "Cancelar", "Cancel", "OK", "Aceptar"]
        
        for button_text in close_buttons:
            try:
                xpath = (
                    f"//*[@text='{button_text}' or contains(@text, '{button_text}') "
                    f"or @content-desc='{button_text}' or contains(@content-desc, '{button_text}')]"
                )
                element = self.driver.find_element(AppiumBy.XPATH, xpath)
                element.click()
                time.sleep(self.min_wait_timeout)
                return f"Success: Dismissed popup by clicking '{button_text}'"
            except Exception:
                continue

        return "Error: Could not find popup close button"

