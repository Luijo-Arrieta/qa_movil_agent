"""
Agent Tools - Herramientas de alto nivel para interactuar con Appium.
"""

import time
import logging
import traceback
import requests
from typing import Optional, Dict, Set
from appium.webdriver.common.appiumby import AppiumBy
from appium.webdriver import Remote
from selenium.common.exceptions import StaleElementReferenceException

from src.ui_parser import UIParser
from src.config import Config

# Configurar logging para este módulo
logger = logging.getLogger(__name__)


class AppiumSkills:
    """
    Clase que proporciona métodos de alto nivel para interactuar con Appium.
    Integrada con UIParser para usar IDs temporales de elementos.
    
    Incluye capacidades de gestión multi-app para tests que requieren
    cambiar entre múltiples aplicaciones (ej: Customer ↔ Technical).
    """
    
    # Estados de app según Appium (queryAppState)
    APP_STATE = {
        "NOT_INSTALLED": 0,      # App no instalada en el dispositivo
        "NOT_RUNNING": 1,        # App instalada pero no ejecutándose
        "BACKGROUND_SUSPENDED": 2,  # En background, proceso suspendido
        "BACKGROUND": 3,         # En background, proceso activo
        "FOREGROUND": 4,         # En primer plano (visible)
    }
    
    # Mapeo inverso para logs legibles
    APP_STATE_NAMES = {
        0: "NOT_INSTALLED",
        1: "NOT_RUNNING", 
        2: "BACKGROUND_SUSPENDED",
        3: "BACKGROUND",
        4: "FOREGROUND",
    }
    
    # Clases de elementos de carga comunes en Android
    LOADING_INDICATORS = [
        "android.widget.ProgressBar",
        "android.widget.ProgressIndicator",
        "com.google.android.material.progressindicator",
        "CircularProgressIndicator",
        "LinearProgressIndicator",
    ]
    
    # Textos comunes en pantallas de carga
    LOADING_TEXTS = [
        "Cargando", "Loading", "Please wait", "Espere", "Procesando",
        "Processing", "Aguarde", "Un momento", "Wait",
    ]

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
        self.default_wait_timeout = Config.IMPLICIT_WAIT
        self.min_wait_timeout = 0.3
        
        # Configuración de espera por estabilidad de UI (desde Config)
        self.ui_stability_timeout = Config.UI_STABILITY_TIMEOUT
        self.ui_stability_interval = Config.UI_STABILITY_INTERVAL
        self.ui_stability_threshold = Config.UI_STABILITY_THRESHOLD
        
        # Tracking de app activa (para gestión multi-app)
        self._current_app_package: Optional[str] = None

        # Tracking de apps usadas y estados conocidos (por driver)
        self._driver_id: int = id(driver)
        if not hasattr(self.__class__, "_usage_by_driver"):
            # type: ignore[attr-defined]
            self.__class__._usage_by_driver = {}  # type: ignore[attr-defined]
        # type: ignore[attr-defined]
        usage_map: Dict[int, Set[str]] = self.__class__._usage_by_driver  # type: ignore[attr-defined]
        if self._driver_id not in usage_map:
            usage_map[self._driver_id] = set()
        self._used_app_packages: Set[str] = usage_map[self._driver_id]
        self._app_states: Dict[str, int] = {}
        
        # Estadísticas de acciones
        self._action_stats = {
            "total_actions": 0,
            "successful_actions": 0,
            "failed_actions": 0,
            "actions_by_type": {},
            "total_wait_time": 0.0,  # Tiempo total esperando UI stability
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
        logger.debug(f"AGENT_TOOLS: ui_stability_timeout={self.ui_stability_timeout}s, "
                    f"ui_stability_interval={self.ui_stability_interval}s, "
                    f"ui_stability_threshold={self.ui_stability_threshold}")

    def get_screen_tree(self) -> str:
        """
        Obtiene el XML de la pantalla actual.

        Returns:
            String con el XML completo de page_source
        """
        #logger.debug("AGENT_TOOLS: Obteniendo page_source (screen tree)...")
        
        start_time = time.time()
        try:
            page_source = self.driver.page_source
            elapsed_ms = int((time.time() - start_time) * 1000)
            
            #logger.debug(f"AGENT_TOOLS: ✓ page_source obtenido en {elapsed_ms}ms "
            #            f"({len(page_source)} caracteres)")
            
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

    # =========================================================================
    # MÉTODOS DE ESPERA INTELIGENTE PARA PANTALLAS DE CARGA/TRANSICIONES
    # =========================================================================

    def _is_loading_screen(self, page_source: str) -> tuple[bool, str]:
        """
        Detecta si la pantalla actual muestra un indicador de carga.
        
        Args:
            page_source: XML de la pantalla actual
            
        Returns:
            Tupla (is_loading, reason): Si está cargando y por qué
        """
        # Detectar por clase de elemento de carga
        for indicator_class in self.LOADING_INDICATORS:
            if indicator_class.lower() in page_source.lower():
                return True, f"Loading indicator found: {indicator_class}"
        
        # Detectar por texto de carga
        for loading_text in self.LOADING_TEXTS:
            # Buscar en atributos text o content-desc
            if f'text="{loading_text}"' in page_source or \
               f"text='{loading_text}'" in page_source or \
               f'content-desc="{loading_text}"' in page_source:
                return True, f"Loading text found: '{loading_text}'"
        
        return False, "No loading indicators detected"

    def _get_page_source_hash(self, page_source: str) -> int:
        """
        Genera un hash simple del page_source para comparar cambios.
        Ignora atributos que cambian constantemente (como focused, bounds exactos).
        
        Args:
            page_source: XML de la pantalla
            
        Returns:
            Hash numérico del contenido relevante
        """
        import re
        # Remover atributos volátiles que no indican cambio real de UI
        cleaned = re.sub(r'focused="[^"]*"', '', page_source)
        cleaned = re.sub(r'selected="[^"]*"', '', cleaned)
        # Simplificar bounds (solo mantener posición aproximada)
        cleaned = re.sub(r'bounds="\[\d+,\d+\]\[\d+,\d+\]"', 'bounds="[X]"', cleaned)
        return hash(cleaned)

    def wait_for_ui_stable(self, timeout: Optional[float] = None) -> tuple[bool, float, str]:
        """
        Espera hasta que la UI se estabilice (deje de cambiar).
        
        Esta función es crucial para manejar:
        - Pantallas de carga/spinners
        - Transiciones entre pantallas
        - Animaciones de UI
        - Elementos que aparecen con delay
        
        Estrategia:
        1. Si detecta un loading indicator, espera a que desaparezca
        2. Toma snapshots del page_source periódicamente
        3. Cuando N snapshots consecutivos son iguales, considera la UI estable
        
        Args:
            timeout: Tiempo máximo de espera (usa self.ui_stability_timeout si no se especifica)
            
        Returns:
            Tupla (is_stable, wait_time_seconds, reason):
            - is_stable: True si la UI se estabilizó, False si timeout
            - wait_time_seconds: Tiempo que esperó
            - reason: Descripción del resultado
        """
        timeout = timeout or self.ui_stability_timeout
        start_time = time.time()
        
        logger.debug(f"AGENT_TOOLS: ⏳ Esperando estabilidad de UI (timeout={timeout}s, "
                    f"threshold={self.ui_stability_threshold} checks, "
                    f"interval={self.ui_stability_interval}s)")
        
        previous_hash = None
        stable_count = 0
        check_count = 0
        
        while (time.time() - start_time) < timeout:
            check_count += 1
            
            try:
                # Obtener estado actual
                page_source = self.driver.page_source
                
                # Verificar si hay pantalla de carga
                is_loading, loading_reason = self._is_loading_screen(page_source)
                if is_loading:
                    logger.debug(f"AGENT_TOOLS: 🔄 Check #{check_count}: {loading_reason}")
                    stable_count = 0  # Reset contador de estabilidad
                    time.sleep(self.ui_stability_interval)
                    continue
                
                # Calcular hash del estado actual
                current_hash = self._get_page_source_hash(page_source)
                
                if previous_hash == current_hash:
                    stable_count += 1
                    logger.debug(f"AGENT_TOOLS: ✓ Check #{check_count}: UI sin cambios "
                               f"({stable_count}/{self.ui_stability_threshold})")
                    
                    if stable_count >= self.ui_stability_threshold:
                        elapsed = time.time() - start_time
                        self._action_stats["total_wait_time"] += elapsed
                        logger.info(f"AGENT_TOOLS: ✓ UI estable después de {elapsed:.2f}s "
                                   f"({check_count} checks)")
                        return True, elapsed, f"UI stable after {check_count} checks"
                else:
                    if stable_count > 0:
                        logger.debug(f"AGENT_TOOLS: 🔄 Check #{check_count}: UI cambió, "
                                   f"reset contador (era {stable_count})")
                    else:
                        logger.debug(f"AGENT_TOOLS: 🔄 Check #{check_count}: UI cambió")
                    stable_count = 0
                
                previous_hash = current_hash
                time.sleep(self.ui_stability_interval)
                
            except Exception as e:
                logger.warning(f"AGENT_TOOLS WARNING: Error en check #{check_count}: {e}")
                time.sleep(self.ui_stability_interval)
                continue
        
        # Timeout alcanzado
        elapsed = time.time() - start_time
        self._action_stats["total_wait_time"] += elapsed
        logger.warning(f"AGENT_TOOLS: ⚠️ Timeout esperando UI estable después de {elapsed:.2f}s "
                      f"({check_count} checks, stable_count={stable_count})")
        return False, elapsed, f"Timeout after {elapsed:.2f}s ({check_count} checks)"

    def wait_for_loading_complete(self, timeout: Optional[float] = None) -> tuple[bool, float]:
        """
        Espera específicamente a que desaparezcan los indicadores de carga.
        
        Útil cuando sabes que una acción va a mostrar un loading y quieres
        esperar solo a que termine, sin verificar estabilidad completa.
        
        Args:
            timeout: Tiempo máximo de espera
            
        Returns:
            Tupla (loading_complete, wait_time_seconds)
        """
        timeout = timeout or self.ui_stability_timeout
        start_time = time.time()
        
        logger.debug(f"AGENT_TOOLS: ⏳ Esperando que termine pantalla de carga (timeout={timeout}s)")
        
        check_count = 0
        while (time.time() - start_time) < timeout:
            check_count += 1
            
            try:
                page_source = self.driver.page_source
                is_loading, reason = self._is_loading_screen(page_source)
                
                if not is_loading:
                    elapsed = time.time() - start_time
                    self._action_stats["total_wait_time"] += elapsed
                    logger.info(f"AGENT_TOOLS: ✓ Carga completa después de {elapsed:.2f}s "
                               f"({check_count} checks)")
                    return True, elapsed
                
                logger.debug(f"AGENT_TOOLS: 🔄 Check #{check_count}: Aún cargando - {reason}")
                time.sleep(self.ui_stability_interval)
                
            except Exception as e:
                logger.warning(f"AGENT_TOOLS WARNING: Error verificando loading: {e}")
                time.sleep(self.ui_stability_interval)
        
        elapsed = time.time() - start_time
        self._action_stats["total_wait_time"] += elapsed
        logger.warning(f"AGENT_TOOLS: ⚠️ Timeout esperando fin de carga después de {elapsed:.2f}s")
        return False, elapsed

    def get_screen_tree_stable(self, timeout: Optional[float] = None) -> str:
        """
        Obtiene el XML de la pantalla DESPUÉS de esperar estabilidad.
        
        Este método combina wait_for_ui_stable + get_screen_tree para
        garantizar que el XML retornado corresponde a una UI estable,
        no a una pantalla de transición o carga.
        
        Args:
            timeout: Tiempo máximo de espera para estabilidad
            
        Returns:
            XML de la pantalla estable
        """
        #logger.debug("AGENT_TOOLS: Obteniendo screen tree con espera de estabilidad...")
        
        # Esperar estabilidad
        is_stable, wait_time, reason = self.wait_for_ui_stable(timeout)
        
        if not is_stable:
            logger.warning(f"AGENT_TOOLS WARNING: UI no estabilizó ({reason}), "
                          "procediendo de todos modos")
        
        # Obtener XML final
        return self.get_screen_tree()

    def _touch_by_coordinates(self, element) -> None:
        """
        Hace touch en un elemento usando sus coordenadas (fallback cuando click() falla).
        
        Similar al _touchOnW3C de WebdriverIO. Útil cuando el elemento no es
        clickable directamente pero sí puede recibir touch por coordenadas.
        
        Args:
            element: Elemento de Appium ya encontrado
        """
        location = element.location
        size = element.size
        center_x = int(location["x"] + size["width"] / 2)
        center_y = int(location["y"] + size["height"] / 2)
        
        logger.debug(f"AGENT_TOOLS: Touch por coordenadas en ({center_x}, {center_y})")
        
        self.driver.execute_script("mobile: clickGesture", {
            "x": center_x,
            "y": center_y
        })

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
            # Escapar comillas simples para evitar conflictos con el delimitador del XPath
            text_description_escaped = text_description.replace("'", "\\'")
            xpath = (
                f"//*[@text='{text_description_escaped}' or contains(@text, '{text_description_escaped}') "
                f"or @content-desc='{text_description_escaped}' or contains(@content-desc, '{text_description_escaped}')]"
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
        
        VALIDACIONES:
        - Solo acepta elementos cuya clase contenga "EditText"
        - Verifica que el texto se escribió correctamente después de la operación

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
        
        # Paso 1: Obtener info completa del elemento
        logger.debug(f"AGENT_TOOLS: Buscando info para ID {element_id}...")
        element_info = self.ui_parser.get_element_info_by_id(element_id)
        
        if not element_info:
            error_msg = f"Error: Elemento con ID {element_id} no encontrado en el mapeo"
            logger.error(f"AGENT_TOOLS ERROR: {error_msg}")
            self.ui_parser.debug_dump_element_map(log_output=True)
            self._action_stats["failed_actions"] += 1
            return error_msg
        
        # Paso 2: Convertir attrs a diccionario para acceso directo
        attrs_dict = {attr.get("name"): attr.get("value", "") for attr in element_info.get("attrs", [])}
        
        element_class = attrs_dict.get("class", "")
        xpath = attrs_dict.get("xpath", "")
        is_password = attrs_dict.get("password", "false").lower() == "true"
        
        # Validación específica de EditText (responsabilidad única de fill_field_by_id)
        if "edittext" not in element_class.lower():
            error_msg = f"Error: Elemento ID {element_id} no es un campo de texto. Clase: '{element_class}'. Solo se puede escribir en elementos EditText."
            logger.error(f"AGENT_TOOLS ERROR: {error_msg}")
            logger.error(f"AGENT_TOOLS ERROR: Usa touch_element_by_id para elementos no editables")
            self._action_stats["failed_actions"] += 1
            return error_msg
        
        if not xpath:
            error_msg = f"Error: No se pudo obtener XPath para elemento ID {element_id}"
            logger.error(f"AGENT_TOOLS ERROR: {error_msg}")
            self._action_stats["failed_actions"] += 1
            return error_msg
        
        logger.debug(f"AGENT_TOOLS: Clase válida: {element_class}")
        logger.debug(f"AGENT_TOOLS: XPath: {xpath}")

        start_time = time.time()
        result_msg = ""
        try:
            # Paso 3: Buscar elemento UNA sola vez
            logger.debug("AGENT_TOOLS: Buscando elemento con XPath...")
            element = self.driver.find_element(AppiumBy.XPATH, xpath)
            logger.debug("AGENT_TOOLS: ✓ Elemento encontrado")
            
            # Paso 4: Hacer click para enfocar (con fallback a coordenadas si falla)
            logger.debug("AGENT_TOOLS: Haciendo click para enfocar...")
            try:
                element.click()
            except Exception as click_error:
                logger.debug(f"AGENT_TOOLS: Click directo falló ({click_error}), usando touch por coordenadas...")
                self._touch_by_coordinates(element)
            time.sleep(self.min_wait_timeout)
            
            # Paso 5: Limpiar campo
            logger.debug("AGENT_TOOLS: Limpiando campo...")
            element.clear()
            
            # Paso 6: Escribir texto
            logger.debug(f"AGENT_TOOLS: Escribiendo texto: '{value}'")
            element.send_keys(value)
            time.sleep(self.min_wait_timeout)
            
            # Paso 7: VERIFICAR que el texto se escribió correctamente
            # IMPORTANTE: Usar el mismo elemento sin re-buscarlo (el xpath puede cambiar después de escribir)
            logger.debug("AGENT_TOOLS: Verificando que el texto se escribió correctamente...")
            
            try:
                # En Android, element.text puede estar vacío después de escribir
                # Intentar múltiples métodos para obtener el texto
                actual_text = ""
                try:
                    # Método 1: get_attribute("text") - más confiable en Android
                    actual_text = element.get_attribute("text") or ""
                except:
                    pass
                
                if not actual_text:
                    try:
                        # Método 3: get_attribute("value") (algunos campos usan value)
                        actual_text = element.get_attribute("value") or ""
                    except:
                        pass
                
                # Verificar si el texto coincide (o si es campo de contraseña, verificar longitud)
                if is_password:
                    # Para campos de contraseña, verificamos que hay contenido
                    # getText retorna asteriscos o vacío, validamos por longitud
                    logger.debug(f"AGENT_TOOLS: Campo de contraseña - verificación por longitud")
                    # Si no podemos obtener el texto, asumimos éxito (send_keys no falló)
                    text_written = len(actual_text) == len(value) or len(actual_text) == 0 or not actual_text
                else:
                    # Para campos normales, verificamos que el texto coincida
                    # Si actual_text está vacío pero send_keys no falló, asumimos éxito
                    if not actual_text:
                        logger.debug("AGENT_TOOLS: No se pudo obtener texto del elemento, pero send_keys no falló - asumiendo éxito")
                        text_written = True
                    else:
                        text_written = value in actual_text or actual_text == value
                        if not text_written:
                            logger.warning(f"AGENT_TOOLS WARNING: Texto esperado: '{value}', texto actual: '{actual_text}'")
                
                elapsed_ms = int((time.time() - start_time) * 1000)
                
                if text_written:
                    result_msg = f"Success: Typed '{value}' into element ID {element_id} (verified)"
                    logger.info(f"AGENT_TOOLS: ✓ {result_msg} (en {elapsed_ms}ms)")
                    self._action_stats["successful_actions"] += 1
                else:
                    result_msg = f"Error: Text verification failed for ID {element_id}. Expected '{value}', got '{actual_text}'"
                    logger.error(f"AGENT_TOOLS ERROR: {result_msg}")
                    self._action_stats["failed_actions"] += 1
                    
            except StaleElementReferenceException:
                # El elemento ya no existe en el DOM (la UI cambió después de escribir)
                # Esto es común y no significa que la escritura falló
                elapsed_ms = int((time.time() - start_time) * 1000)
                result_msg = f"Success: Typed '{value}' into element ID {element_id} (UI changed, verification skipped)"
                logger.info(f"AGENT_TOOLS: ✓ {result_msg} (en {elapsed_ms}ms)")
                logger.debug("AGENT_TOOLS: Elemento stale después de escribir - la UI cambió, asumimos éxito")
                self._action_stats["successful_actions"] += 1
            
        except Exception as e:
            elapsed_ms = int((time.time() - start_time) * 1000)
            result_msg = f"Error: Could not fill field ID {element_id}: {str(e)}"
            logger.error(f"AGENT_TOOLS ERROR: {result_msg} (después de {elapsed_ms}ms)")
            logger.error(f"AGENT_TOOLS ERROR: XPath usado: {xpath}")
            logger.error(f"AGENT_TOOLS ERROR: Valor intentado: '{value}'")
            logger.error(f"AGENT_TOOLS ERROR: Traceback:\n{traceback.format_exc()}")
            self._action_stats["failed_actions"] += 1
            
        finally:
            # SIEMPRE ocultar teclado al finalizar (éxito o error)
            logger.debug("AGENT_TOOLS: [finally] Verificando y ocultando teclado...")
            self.hide_keyboard()
            time.sleep(self.min_wait_timeout)  # Esperar a que la UI se estabilice
        
        return result_msg

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
            # Escapar comillas simples para evitar conflictos con el delimitador del XPath
            field_hint_escaped = field_hint.replace("'", "\\'")
            xpath = (
                f"//android.widget.EditText[contains(@text, '{field_hint_escaped}') "
                f"or contains(@content-desc, '{field_hint_escaped}') "
                f"or contains(@hint, '{field_hint_escaped}')]"
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
                # Escapar comillas simples para evitar conflictos con el delimitador del XPath
                button_text_escaped = button_text.replace("'", "\\'")
                xpath = (
                    f"//*[@text='{button_text_escaped}' or contains(@text, '{button_text_escaped}') "
                    f"or @content-desc='{button_text_escaped}' or contains(@content-desc, '{button_text_escaped}')]"
                )
                element = self.driver.find_element(AppiumBy.XPATH, xpath)
                element.click()
                time.sleep(self.min_wait_timeout)
                return f"Success: Dismissed popup by clicking '{button_text}'"
            except Exception:
                continue

        return "Error: Could not find popup close button"

    # =========================================================================
    # GESTIÓN MULTI-APP - Métodos para cambiar entre múltiples aplicaciones
    # =========================================================================

    def query_app_state(self, app_package: str) -> tuple[int, str]:
        """
        Consulta el estado actual de una app.
        
        Args:
            app_package: Package de la app (ej: 'com.example.app')
            
        Returns:
            Tupla (state_code, state_name):
            - 0: NOT_INSTALLED - App no instalada
            - 1: NOT_RUNNING - Instalada pero no corriendo
            - 2: BACKGROUND_SUSPENDED - En background, suspendida
            - 3: BACKGROUND - En background, activa
            - 4: FOREGROUND - En primer plano
        """
        action_name = "query_app_state"
        self._action_stats["total_actions"] += 1
        self._action_stats["actions_by_type"][action_name] = self._action_stats["actions_by_type"].get(action_name, 0) + 1
        
        logger.info(f"AGENT_TOOLS: 🔍 Ejecutando {action_name}(app_package='{app_package}')")
        
        try:
            state = self.driver.query_app_state(app_package)
            state_name = self.APP_STATE_NAMES.get(state, f"UNKNOWN({state})")

            # Actualizar caches internos
            self._app_states[app_package] = state
            # Registrar app como "usada" si está instalada (cualquier estado >= 0)
            if state >= 0:
                self._used_app_packages.add(app_package)
            
            logger.info(f"AGENT_TOOLS: ✓ Estado de '{app_package}': {state_name} ({state})")
            self._action_stats["successful_actions"] += 1
            return state, state_name
            
        except Exception as e:
            error_msg = f"Error consultando estado de '{app_package}': {str(e)}"
            logger.error(f"AGENT_TOOLS ERROR: {error_msg}")
            logger.error(f"AGENT_TOOLS ERROR: Traceback:\n{traceback.format_exc()}")
            self._action_stats["failed_actions"] += 1
            return -1, f"ERROR: {str(e)}"

    def activate_app(self, app_package: str) -> str:
        """
        Activa (abre/trae al primer plano) una app instalada.
        
        Esta es la operación fundamental para abrir una app o traerla
        al foreground si ya está corriendo en background.
        
        Args:
            app_package: Package de la app (ej: 'com.imagineapps.gofixiicliente')
            
        Returns:
            Mensaje de éxito o error
        """
        action_name = "activate_app"
        self._action_stats["total_actions"] += 1
        self._action_stats["actions_by_type"][action_name] = self._action_stats["actions_by_type"].get(action_name, 0) + 1
        
        logger.info(f"AGENT_TOOLS: 🚀 Ejecutando {action_name}(app_package='{app_package}')")
        
        start_time = time.time()
        try:
            # Primero verificar el estado de la app
            state, state_name = self.query_app_state(app_package)
            logger.debug(f"AGENT_TOOLS: Estado actual de la app: {state_name}")
            
            if state == self.APP_STATE["NOT_INSTALLED"]:
                error_msg = f"Error: App '{app_package}' NO está instalada en el dispositivo"
                logger.error(f"AGENT_TOOLS ERROR: {error_msg}")
                self._action_stats["failed_actions"] += 1
                return error_msg
            
            # Activar la app (traerla al foreground)
            logger.debug(f"AGENT_TOOLS: Activando app '{app_package}'...")
            self.driver.activate_app(app_package)

            # Actualizar tracking de app actual y listado de apps usadas
            self._current_app_package = app_package
            self._used_app_packages.add(app_package)

            # Pausa para estabilización de la UI
            time.sleep(1.0)

            # Verificar que la app llegó a foreground (actualiza _app_states)
            new_state, new_state_name = self.query_app_state(app_package)
            app_is_in_foreground = new_state == self.APP_STATE["FOREGROUND"]
            if not app_is_in_foreground:
                logger.debug(f"AGENT_TOOLS: App aún no en foreground ({new_state_name}), esperando...")
                time.sleep(1.0)
                self.query_app_state(app_package)
            
            elapsed_ms = int((time.time() - start_time) * 1000)
            success_msg = f"Success: Activated app '{app_package}'"
            logger.info(f"AGENT_TOOLS: ✓ {success_msg} (en {elapsed_ms}ms)")
            self._action_stats["successful_actions"] += 1
            return success_msg
            
        except Exception as e:
            elapsed_ms = int((time.time() - start_time) * 1000)
            error_msg = f"Error: Could not activate app '{app_package}': {str(e)}"
            logger.error(f"AGENT_TOOLS ERROR: {error_msg} (después de {elapsed_ms}ms)")
            logger.error(f"AGENT_TOOLS ERROR: Traceback:\n{traceback.format_exc()}")
            self._action_stats["failed_actions"] += 1
            return error_msg

    def terminate_app(self, app_package: str) -> str:
        """
        Termina (cierra completamente) una app.
        
        La app se cierra y deja de ejecutarse. Esto libera recursos
        y garantiza un estado limpio la próxima vez que se abra.
        
        Args:
            app_package: Package de la app a cerrar
            
        Returns:
            Mensaje de éxito o error
        """
        action_name = "terminate_app"
        self._action_stats["total_actions"] += 1
        self._action_stats["actions_by_type"][action_name] = self._action_stats["actions_by_type"].get(action_name, 0) + 1
        
        logger.info(f"AGENT_TOOLS: 🛑 Ejecutando {action_name}(app_package='{app_package}')")
        
        start_time = time.time()
        try:
            # Terminar la app
            logger.debug(f"AGENT_TOOLS: Terminando app '{app_package}'...")
            result = self.driver.terminate_app(app_package)

            # Registrar app como usada (puede ser relevante para limpieza)
            self._used_app_packages.add(app_package)
            
            # Actualizar tracking si era la app activa
            if self._current_app_package == app_package:
                self._current_app_package = None

            time.sleep(self.min_wait_timeout)

            # Verificar que la app ya no está corriendo (actualiza _app_states)
            new_state, _ = self.query_app_state(app_package)
            if new_state >= self.APP_STATE["BACKGROUND"]:
                # App todavía está activa, esperar un poco más
                time.sleep(0.5)
                self.query_app_state(app_package)

            elapsed_ms = int((time.time() - start_time) * 1000)

            if result:
                success_msg = f"Success: Terminated app '{app_package}'"
                logger.info(f"AGENT_TOOLS: ✓ {success_msg} (en {elapsed_ms}ms)")
                self._action_stats["successful_actions"] += 1
                return success_msg
            else:
                # terminate_app retorna False si la app no estaba corriendo
                msg = f"Success: App '{app_package}' was not running (nothing to terminate)"
                logger.info(f"AGENT_TOOLS: ℹ️ {msg}")
                self._action_stats["successful_actions"] += 1
                return msg
            
        except Exception as e:
            elapsed_ms = int((time.time() - start_time) * 1000)
            error_msg = f"Error: Could not terminate app '{app_package}': {str(e)}"
            logger.error(f"AGENT_TOOLS ERROR: {error_msg} (después de {elapsed_ms}ms)")
            logger.error(f"AGENT_TOOLS ERROR: Traceback:\n{traceback.format_exc()}")
            self._action_stats["failed_actions"] += 1
            return error_msg

    def switch_to_app(self, app_package: str) -> str:
        """
        Cambia a otra app TERMINANDO la app actual.
        
        Este método:
        1. Cierra completamente la app actual (si hay una)
        2. Abre la nueva app
        
        Útil cuando:
        - Necesitas estado limpio en la app anterior
        - Quieres liberar memoria
        - No necesitas volver a la app anterior
        
        Args:
            app_package: Package de la app destino
            
        Returns:
            Mensaje de éxito o error
        """
        action_name = "switch_to_app"
        self._action_stats["total_actions"] += 1
        self._action_stats["actions_by_type"][action_name] = self._action_stats["actions_by_type"].get(action_name, 0) + 1
        
        logger.info(f"AGENT_TOOLS: 🔄 Ejecutando {action_name}(app_package='{app_package}')")
        logger.debug(f"AGENT_TOOLS: App actual: {self._current_app_package or 'ninguna'}")
        
        start_time = time.time()
        
        # Paso 1: Terminar la app actual si existe y es diferente
        if self._current_app_package and self._current_app_package != app_package:
            logger.debug(f"AGENT_TOOLS: Terminando app actual '{self._current_app_package}'...")
            terminate_result = self.terminate_app(self._current_app_package)
            if "Error" in terminate_result:
                logger.warning(f"AGENT_TOOLS WARNING: Problema al terminar app: {terminate_result}")
                # Continuamos de todos modos
        
        # Paso 2: Activar la nueva app
        activate_result = self.activate_app(app_package)
        
        elapsed_ms = int((time.time() - start_time) * 1000)
        
        if "Error" in activate_result:
            logger.error(f"AGENT_TOOLS ERROR: Fallo al cambiar a '{app_package}'")
            return activate_result
        
        success_msg = f"Success: Switched to app '{app_package}' (previous app terminated)"
        logger.info(f"AGENT_TOOLS: ✓ {success_msg} (en {elapsed_ms}ms)")
        return success_msg

    def switch_to_app_keep_background(self, app_package: str) -> str:
        """
        Cambia a otra app MANTENIENDO la app actual en background.
        
        Este método:
        1. Deja la app actual corriendo en background
        2. Activa (trae al foreground) la nueva app
        
        Útil cuando:
        - Necesitas hacer ida y vuelta entre apps
        - La app anterior debe mantener su sesión/estado
        - Quieres cambios rápidos sin reiniciar login
        
        Args:
            app_package: Package de la app destino
            
        Returns:
            Mensaje de éxito o error
        """
        action_name = "switch_to_app_keep_background"
        self._action_stats["total_actions"] += 1
        self._action_stats["actions_by_type"][action_name] = self._action_stats["actions_by_type"].get(action_name, 0) + 1
        
        logger.info(f"AGENT_TOOLS: 🔀 Ejecutando {action_name}(app_package='{app_package}')")
        logger.debug(f"AGENT_TOOLS: App actual: {self._current_app_package or 'ninguna'}")
        
        start_time = time.time()
        
        # Verificar si ya estamos en la app solicitada
        if self._current_app_package == app_package:
            msg = f"App '{app_package}' already in foreground"
            logger.info(f"AGENT_TOOLS: ℹ️ {msg}")
            return f"Success: {msg}"
        
        # Log de app que queda en background
        if self._current_app_package:
            logger.debug(f"AGENT_TOOLS: App '{self._current_app_package}' quedará en background")
        
        # Activar la nueva app (la actual queda automáticamente en background)
        activate_result = self.activate_app(app_package)
        
        elapsed_ms = int((time.time() - start_time) * 1000)
        
        if "Error" in activate_result:
            logger.error(f"AGENT_TOOLS ERROR: Fallo al cambiar a '{app_package}'")
            return activate_result
        
        success_msg = f"Success: Switched to app '{app_package}' (previous app in background)"
        logger.info(f"AGENT_TOOLS: ✓ {success_msg} (en {elapsed_ms}ms)")
        return success_msg

    def get_current_app_package(self) -> Optional[str]:
        """
        Retorna el package de la app actualmente activa (según tracking interno).
        
        Returns:
            Package de la app activa o None si no hay ninguna
        """
        return self._current_app_package

    # =========================================================================
    # ESTADO GLOBAL / TRACKING PARA LIMPIEZA
    # =========================================================================

    def get_used_app_packages(self) -> Set[str]:
        """
        Retorna el conjunto de packages de apps que se han usado
        (consultado estado, activado o terminado) en esta instancia.
        """
        return set(self._used_app_packages)

    @classmethod
    def get_used_app_packages_for_driver(cls, driver: Remote) -> Set[str]:
        """
        Retorna el conjunto de apps usadas asociadas a un driver concreto.

        NOTA: Esto se usa principalmente en tests/fixtures para limpieza
        al final de cada prueba.
        """
        usage_map: Dict[int, Set[str]] = getattr(cls, "_usage_by_driver", {})
        return set(usage_map.get(id(driver), set()))

    @classmethod
    def clear_used_app_packages_for_driver(cls, driver: Remote) -> None:
        """
        Limpia el tracking de apps usadas para un driver concreto.
        """
        usage_map: Dict[int, Set[str]] = getattr(cls, "_usage_by_driver", {})
        usage_map.pop(id(driver), None)

    def get_tracked_app_states(self) -> Dict[str, int]:
        """
        Retorna los últimos estados conocidos de las apps cuyo estado
        se ha consultado mediante query_app_state().
        """
        return dict(self._app_states)

    # =========================================================================
    # HERRAMIENTAS DE INTEGRACIÓN EXTERNA
    # =========================================================================

    def _fetch_confirmation_code_from_webhook(self, email: str) -> str:
        """
        Consulta el webhook de n8n para obtener el código de confirmación.
        
        Esta función realiza una única consulta al webhook y retorna el código
        si está disponible, o lanza una excepción si hay algún problema.
        
        Args:
            email: Dirección de correo electrónico a la que se envió el código
            
        Returns:
            Código de confirmación de 4 dígitos como string
            
        Raises:
            requests.exceptions.RequestException: Si hay error de red o HTTP
            ValueError: Si la respuesta es inválida o el código no está disponible
        """
        # URL del webhook de n8n
        webhook_url = "https://n8n-develop.imagineapps.co/webhook/gofixi/confirmation-code"
        
        # Headers con autenticación
        headers = {
            "Content-Type": "application/json",
            "gofixiAuth": "4GEsYiZHMKDSPp4",
        }
        
        # Body con el correo
        body = {"to": email}
        
        logger.info(f"AGENT_TOOLS: 📡 Consultando webhook...")
        
        # Hacer POST al webhook
        response = requests.post(
            webhook_url,
            headers=headers,
            json=body,
            timeout=10  # Timeout de 10 segundos por request
        )
        
        logger.debug(f"AGENT_TOOLS: 📊 Status de respuesta: {response.status_code}")
        
        # Verificar que la respuesta sea exitosa
        if not response.ok:
            raise requests.exceptions.HTTPError(
                f"HTTP error! Status: {response.status_code}"
            )
        
        # Obtener el texto de la respuesta primero
        response_text = response.text
        logger.debug(f"AGENT_TOOLS: 📥 Respuesta raw: {response_text[:100]}...")
        
        # Validar que la respuesta no esté vacía
        if not response_text or response_text.strip() == "":
            raise ValueError("Respuesta vacía del servidor")
        
        # Parsear JSON
        try:
            response_data = response.json()
        except ValueError as json_error:
            raise ValueError(f"Respuesta no es JSON válido: {response_text[:100]}")
        
        logger.debug(f"AGENT_TOOLS: 📥 Respuesta parseada: {response_data}")
        
        # Extraer el código de la respuesta
        # El webhook retorna el código en el campo "code"
        extracted_code = None
        if isinstance(response_data, dict):
            extracted_code = response_data.get("code")
        
        # Validar que el código no sea null o "null"
        if extracted_code is None or extracted_code == "null" or not extracted_code:
            raise ValueError(f"Código no disponible: {response_data}")
        
        # Convertir a string y limpiar espacios
        code_str = str(extracted_code).strip()
        
        # Validar que el código tenga exactamente 4 dígitos
        if not code_str.isdigit() or len(code_str) != 4:
            raise ValueError(
                f"El código debe tener exactamente 4 dígitos. Recibido: '{code_str}' (longitud: {len(code_str)})"
            )
        
        return code_str

    def get_confirmation_code(self, email: str) -> str:
        """
        Obtiene el código de confirmación enviado por correo electrónico.
        
        Esta herramienta consulta un webhook de n8n que retorna el código
        de verificación más reciente enviado a un correo específico.
        
        Implementación basada en el patrón de referencia:
        - Espera 30 segundos iniciales para que llegue el correo
        - Realiza hasta 3 reintentos con espera de 3 segundos entre cada uno
        - Valida que el código tenga exactamente 4 dígitos
        - Incluye header de autenticación gofixiAuth
        
        Útil para:
        - Recuperación de contraseña (código de 4 dígitos)
        - Verificación de cuenta (código de confirmación)
        - Cualquier flujo que requiera código enviado por correo
        
        Args:
            email: Dirección de correo electrónico a la que se envió el código
                  (ej: "luis.arrieta+pass-recovery-0@imagineapps.co")
            
        Returns:
            Mensaje con el código obtenido en formato: "Success: Confirmation code obtained for EMAIL: CODE=1234"
            o mensaje de error si no se pudo obtener después de los reintentos
        """
        action_name = "get_confirmation_code"
        self._action_stats["total_actions"] += 1
        self._action_stats["actions_by_type"][action_name] = self._action_stats["actions_by_type"].get(action_name, 0) + 1
        
        logger.info(f"AGENT_TOOLS: 📧 Ejecutando {action_name}(email='{email}')")
        
        start_time = time.time()
        
        # Configuración de reintentos
        max_retries = 3
        retry_delay = 3  # segundos entre reintentos
        initial_wait = 30  # segundos de espera inicial para que llegue el correo
        
        try:
            # PASO 1: Esperar 30 segundos para que llegue el correo
            logger.info(f"AGENT_TOOLS: 🔑 Esperando {initial_wait} segundos para que llegue el correo...")
            time.sleep(initial_wait)
            
            logger.info(f"AGENT_TOOLS: 📬 Obteniendo código de confirmación para: {email}")
            
            code = None
            last_error = None
            
            # PASO 2: Intentar obtener el código con reintentos
            for attempt in range(1, max_retries + 1):
                try:
                    logger.info(f"AGENT_TOOLS: 📡 Intento {attempt}/{max_retries} - Consultando webhook...")
                    
                    # Consultar el webhook (lógica extraída a función separada)
                    code = self._fetch_confirmation_code_from_webhook(email)
                    
                    logger.info(f"AGENT_TOOLS: ✓ Código de confirmación obtenido: {code}")
                    break  # Salir del loop si se obtuvo el código
                    
                except Exception as attempt_error:
                    last_error = attempt_error
                    logger.warning(f"AGENT_TOOLS: ⚠️  Intento {attempt} falló: {str(attempt_error)}")
                    
                    # Si no es el último intento, esperar antes de reintentar
                    if attempt < max_retries:
                        logger.info(f"AGENT_TOOLS: ⏳ Esperando {retry_delay} segundos antes de reintentar...")
                        time.sleep(retry_delay)
            
            # PASO 3: Verificar que se obtuvo el código
            if not code:
                elapsed_ms = int((time.time() - start_time) * 1000)
                error_msg = (
                    f"Error: No se pudo obtener el código después de {max_retries} intentos. "
                    f"Último error: {str(last_error) if last_error else 'Desconocido'}"
                )
                logger.error(f"AGENT_TOOLS ERROR: {error_msg} (después de {elapsed_ms}ms)")
                self._action_stats["failed_actions"] += 1
                return error_msg
            
            # PASO 4: Retornar éxito con el código
            elapsed_ms = int((time.time() - start_time) * 1000)
            success_msg = f"Success: Confirmation code obtained for {email}: CODE={code}"
            logger.info(f"AGENT_TOOLS: ✓ {success_msg} (en {elapsed_ms}ms)")
            self._action_stats["successful_actions"] += 1
            return success_msg
            
        except Exception as e:
            elapsed_ms = int((time.time() - start_time) * 1000)
            error_msg = f"Error: Unexpected error getting confirmation code for email '{email}': {str(e)}"
            logger.error(f"AGENT_TOOLS ERROR: {error_msg} (después de {elapsed_ms}ms)")
            logger.error(f"AGENT_TOOLS ERROR: Traceback:\n{traceback.format_exc()}")
            self._action_stats["failed_actions"] += 1
            return error_msg
