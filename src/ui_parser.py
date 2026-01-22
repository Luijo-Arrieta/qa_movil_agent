"""
UIParser - Transforma XML crudo de Appium en representación JSON simplificada
para consumo eficiente por LLMs.

Soporta salida en formato TOON (Token-Oriented Object Notation) para reducir
el consumo de tokens en un 30-60% comparado con JSON.
https://github.com/toon-format/toon
"""

import xml.etree.ElementTree as ET
import logging
import traceback
import time
from typing import List, Dict, Optional, Any, Union
from typing_extensions import TypedDict
import re
import json

from toon_format import encode as toon_encode
from src.middleware_result import MiddlewareResult, MiddlewareStatus
from src.config import Config

# Configurar logging para este módulo
logger = logging.getLogger(__name__)


# TypedDict para representar un atributo de elemento Android
class UIAttribute(TypedDict):
    """
    Representa un atributo de un elemento Android.
    
    Estructura fija {name, value} que permite:
    - Schema consistente (siempre las mismas claves)
    - Flexibilidad (solo incluir atributos con valor)
    - Fácil extensión (agregar/quitar atributos sin romper estructura)
    """
    name: str   # Nombre del atributo Android (ej: "content-desc", "resource-id")
    value: str  # Valor del atributo


class UIElement(TypedDict):
    """
    Representa un elemento de UI extraído del XML de Appium.
    
    Estructura:
    - id: ID único asignado por UIParser (USAR ESTE EN TOOL CALLS como element_id)
    - attrs: Lista de atributos del elemento con estructura fija {name, value}
    
    Ejemplo:
    {
        "id": 0,
        "attrs": [
            {"name": "content-desc", "value": "Botón login"},
            {"name": "class", "value": "android.widget.Button"},
            {"name": "xpath", "value": "//android.view.View[@content-desc='Login']/android.widget.Button"},
            {"name": "clickable", "value": "true"},
            {"name": "enabled", "value": "true"}
        ]
    }
    
    Atributos posibles en attrs:
    - resource-id: ID del recurso Android (para localizar)
    - content-desc: Descripción de accesibilidad (para localizar)
    - text: Texto visible del elemento (para localizar)
    - class: Clase del componente Android
    - xpath: XPath del elemento para localizarlo
    - bounds: Coordenadas [x1,y1][x2,y2]
    - clickable: Si es clickeable ("true"/"false")
    - displayed: Si está visible ("true"/"false")
    - enabled: Si está habilitado ("true"/"false")
    - password: Si es campo de contraseña ("true"/"false")
    - scrollable: Si es scrolleable ("true"/"false")
    - hint: Placeholder del input
    
    NOTA: Solo se incluyen atributos con valor no vacío (excepto booleanos).
    """
    id: int
    attrs: List[UIAttribute]


class UIParser:
    """
    Parsea el XML de page_source de Appium y genera una lista JSON simplificada
    de elementos interactuables, asignando IDs temporales y manteniendo mapeo
    a XPath reales.
    """

    def __init__(self, driver: Optional[Any] = None):
        """
        Inicializa el parser con mapeo vacío de elementos.
        
        Args:
            driver: Driver de Appium (opcional). Si se proporciona, el parser puede
                   obtener el XML y current_package por sí mismo.
        """
        logger.debug("UIPARSER: Inicializando UIParser")
        self.driver = driver
        self.element_map: Dict[int, str] = {}  # ID -> XPath
        self.element_info_map: Dict[int, UIElement] = {}  # ID -> Información completa del elemento
        self.current_id = 0
        self._parse_stats = {
            "total_nodes_visited": 0,
            "interactable_found": 0,
            "filtered_out": 0,
        }
        # Tamaño de pantalla (se obtiene del XML root)
        self.screen_width = 0
        self.screen_height = 0

    def _get_current_package(self) -> Optional[str]:
        """
        Obtiene el package de la app actual en foreground.
        
        Returns:
            Package de la app actual o None si no se puede obtener
        """
        if not self.driver:
            return None
        try:
            return self.driver.current_package
        except Exception as e:
            logger.warning(f"UIPARSER: No se pudo obtener current_package: {e}")
            return None

    def _get_screen_tree(self) -> str:
        """
        Obtiene el XML de la pantalla actual desde el driver.
        
        Returns:
            String con el XML completo de page_source
            
        Raises:
            ValueError: Si no hay driver configurado
        """
        if not self.driver:
            raise ValueError("UIPARSER ERROR: No hay driver configurado. Pasa el driver al inicializar UIParser o proporciona xml_source directamente.")
        
        try:
            return self.driver.page_source
        except Exception as e:
            logger.error(f"UIPARSER ERROR: Fallo al obtener page_source: {e}")
            raise

    def _is_loading_screen(self, page_source: str) -> tuple[bool, str]:
        """
        Detecta si la pantalla actual muestra un indicador de carga.
        
        Returns:
            Tupla (is_loading, reason): True si hay loading, False si no
        """
        page_source_lower = page_source.lower()
        
        # Patrones comunes de loading
        loading_patterns = [
            ("loading", "Indicador 'loading' detectado"),
            ("cargando", "Indicador 'cargando' detectado"),
            ("progressbar", "ProgressBar detectado"),
            ("progress_bar", "ProgressBar detectado"),
            ("spinner", "Spinner detectado"),
            ("circularprogressindicator", "CircularProgressIndicator detectado"),
        ]
        
        for pattern, reason in loading_patterns:
            if pattern in page_source_lower:
                return True, reason
        
        return False, "No hay indicadores de carga"

    def _get_page_source_hash(self, page_source: str) -> int:
        """
        Genera un hash simple del page_source para comparar cambios.
        Ignora atributos que cambian constantemente.
        """
        # Remover atributos que cambian frecuentemente
        cleaned = page_source
        # Remover bounds exactos (pueden cambiar ligeramente)
        cleaned = re.sub(r'bounds="\[.*?\]"', '', cleaned)
        # Remover focused (cambia constantemente)
        cleaned = re.sub(r'focused="(true|false)"', '', cleaned)
        # Remover espacios extra
        cleaned = re.sub(r'\s+', ' ', cleaned)
        return hash(cleaned)

    def _wait_for_ui_stable(self, timeout: float = 5.0, stability_threshold: int = 3, interval: float = 0.5) -> tuple[bool, float, str]:
        """
        Espera hasta que la UI se estabilice (deje de cambiar).
        
        Args:
            timeout: Tiempo máximo de espera en segundos
            stability_threshold: Número de checks consecutivos iguales para considerar estable
            interval: Intervalo entre checks en segundos
            
        Returns:
            Tupla (is_stable, wait_time_seconds, reason)
        """
        if not self.driver:
            logger.warning("UIPARSER: No hay driver, saltando espera de estabilidad")
            return True, 0.0, "No driver available"
        
        start_time = time.time()
        previous_hash = None
        stable_count = 0
        check_count = 0
        
        while (time.time() - start_time) < timeout:
            check_count += 1
            try:
                page_source = self.driver.page_source
                
                # Verificar si hay pantalla de carga
                is_loading, loading_reason = self._is_loading_screen(page_source)
                if is_loading:
                    logger.debug(f"UIPARSER: 🔄 Check #{check_count}: {loading_reason}")
                    stable_count = 0
                    time.sleep(interval)
                    continue
                
                # Comparar hash
                current_hash = self._get_page_source_hash(page_source)
                
                if previous_hash == current_hash:
                    stable_count += 1
                    if stable_count >= stability_threshold:
                        elapsed = time.time() - start_time
                        # logger.debug(f"UIPARSER: ✓ UI estable después de {elapsed:.2f}s ({check_count} checks)")
                        return True, elapsed, f"UI estable después de {check_count} checks"
                else:
                    stable_count = 0
                    # logger.debug(f"UIPARSER: 🔄 Check #{check_count}: UI cambió, reiniciando contador")
                
                previous_hash = current_hash
                time.sleep(interval)
                
            except Exception as e:
                logger.warning(f"UIPARSER: Error en check #{check_count}: {e}")
                time.sleep(interval)
        
        elapsed = time.time() - start_time
        logger.warning(f"UIPARSER: ⚠️  Timeout esperando estabilidad después de {elapsed:.2f}s")
        return False, elapsed, f"Timeout después de {check_count} checks"

    def get_ui(self, wait_stable: bool = True, timeout: float = 5.0) -> Union[List[UIElement], MiddlewareResult]:
        """
        Método principal para obtener la UI actual.
        
        Encapsula toda la lógica:
        1. Espera estabilidad de UI (si wait_stable=True)
        2. Obtiene XML y current_package del driver
        3. Ejecuta middleware de validación de scope
        4. Parsea y retorna elementos o MiddlewareResult
        
        Args:
            wait_stable: Si True, espera a que la UI se estabilice antes de parsear
            timeout: Tiempo máximo de espera para estabilidad (solo si wait_stable=True)
            
        Returns:
            List[UIElement] si la app está permitida y hay elementos
            MiddlewareResult si la app no está permitida o hay error de scope
        """
        logger.debug("=" * 70)
        logger.info("UIPARSER: get_ui() - Obteniendo UI actual")
        logger.debug("=" * 70)
        
        # FASE 1: Esperar estabilidad si está habilitado
        if wait_stable and self.driver:
            # logger.debug("UIPARSER: Esperando estabilidad de UI...")
            is_stable, wait_time, reason = self._wait_for_ui_stable(timeout=timeout)
            if not is_stable:
                logger.warning(f"UIPARSER: UI no estabilizó completamente ({reason}), continuando de todos modos")
        
        # FASE 2: Obtener XML y current_package
        # logger.debug("UIPARSER: Obteniendo XML y current_package...")
        xml_source = self._get_screen_tree()
        current_package = self._get_current_package()
        # logger.debug(f"UIPARSER: ✓ XML obtenido ({len(xml_source)} caracteres), current_package = {current_package}")
        
        # FASE 3: Ejecutar parse_screen (que incluye middleware)
        return self.parse_screen(xml_source=xml_source, current_package=current_package)

    def parse_screen(
        self, 
        xml_source: Optional[str] = None, 
        current_package: Optional[str] = None, 
        allowed_packages: Optional[List[str]] = None
    ) -> Union[List[UIElement], MiddlewareResult]:
        """
        Parsea el XML y retorna lista de elementos interactuables.

        Si xml_source no se proporciona, el parser obtiene el XML desde el driver.
        Si current_package no se proporciona, el parser lo obtiene desde el driver.

        Criterios de inclusión:
        - focusable="true" - REQUERIDO
        - clickable="true" (con info útil: text, content-desc o resource-id)
        - Clase contiene "EditText" (inputs) - siempre incluidos
        - Clase contiene "ImageView" + clickable (botones de imagen) - siempre incluidos

        Args:
            xml_source: String con el XML completo de page_source (opcional, se obtiene del driver si no se proporciona)
            current_package: Package de la app actual en foreground (opcional, se obtiene del driver si no se proporciona)
            allowed_packages: Lista de packages permitidos (opcional, usa Config.ALLOWED_APP_PACKAGES si no se proporciona)

        Returns:
            Lista de UIElement o MiddlewareResult si la app actual no está permitida.
            
            Si retorna MiddlewareResult, significa que la app actual no está en allowed_packages
            y el agente debe usar activate_app() para abrir una app permitida.
            
            Si retorna List[UIElement], contiene elementos con estructura:
            {
                "id": int,  # ID para usar en tool calls (touch_element_by_id, fill_field_by_id)
                "attrs": [  # Lista de atributos con estructura fija {name, value}
                    {"name": "content-desc", "value": "Botón login"},
                    {"name": "class", "value": "android.widget.Button"},
                    {"name": "xpath", "value": "//..."},
                    {"name": "clickable", "value": "true"},
                    ...
                ]
            }
            
            Atributos posibles (solo se incluyen si tienen valor):
            - resource-id: ID del recurso Android (para localizar)
            - content-desc: Descripción de accesibilidad (para localizar)
            - text: Texto visible del elemento (para localizar)
            - class: Clase del componente Android (siempre)
            - xpath: XPath jerárquico del elemento (siempre)
            - bounds: Coordenadas [x1,y1][x2,y2]
            - clickable, enabled, displayed: Estados booleanos (siempre)
            - password, scrollable: Solo si son "true"
            - hint: Placeholder del input
        """
        # logger.debug("=" * 70)
        # logger.debug("UIPARSER: Iniciando parseo de pantalla")
        # logger.debug("=" * 70)
        
        # Obtener XML si no se proporciona
        if xml_source is None:
            logger.debug("UIPARSER: Obteniendo XML desde driver...")
            xml_source = self._get_screen_tree()
            logger.debug(f"UIPARSER: ✓ XML obtenido ({len(xml_source)} caracteres)")
        
        # Obtener current_package si no se proporciona
        if current_package is None:
            logger.debug("UIPARSER: Obteniendo current_package desde driver...")
            current_package = self._get_current_package()
            logger.debug(f"UIPARSER: current_package = {current_package}")
        
        # Middleware: Validar scope de app
        # Si allowed_packages no se proporciona pero Config.ALLOWED_APP_PACKAGES está configurado, usarlo
        if allowed_packages is None and Config.ALLOWED_APP_PACKAGES:
            allowed_packages = Config.ALLOWED_APP_PACKAGES
            logger.debug(f"UIPARSER: Usando ALLOWED_APP_PACKAGES de Config: {allowed_packages}")
        
        # Ejecutar validación del middleware si hay allowed_packages
        if allowed_packages:
            if not current_package or current_package not in allowed_packages:
                # App no permitida o launcher/sistema
                allowed_str = ", ".join(allowed_packages)
                logger.warning(
                    f"UIPARSER: ⚠️  MIDDLEWARE DENEGADO - App actual '{current_package}' no está en allowed_packages. "
                    f"Apps permitidas: {allowed_packages}"
                )
                return MiddlewareResult(
                    status=MiddlewareStatus.DENIED,
                    message=f"No hay app permitida en foreground. Apps permitidas: {allowed_str}. Usa activate_app(app_package) para abrir una app permitida.",
                    allowed_apps=allowed_packages,
                    suggested_tool="activate_app"
                )
            else:
                logger.debug(f"UIPARSER: ✓ Middleware permitido - App '{current_package}' está en allowed_packages")
        
        # Reset estadísticas
        self._parse_stats = {
            "total_nodes_visited": 0,
            "interactable_found": 0,
            "filtered_out": 0,
        }
        
        # Validar entrada
        if not xml_source:
            logger.error("UIPARSER ERROR: xml_source está vacío o es None")
            raise ValueError("xml_source no puede estar vacío")
        
        xml_length = len(xml_source)
        logger.debug(f"UIPARSER: Longitud del XML recibido: {xml_length} caracteres")
        
        # Mostrar primeros caracteres para debug
        #preview = xml_source[:200].replace('\n', ' ').replace('\r', '')
        #logger.debug(f"UIPARSER: Preview del XML: {preview}...")
        
        try:
            logger.debug("UIPARSER: Parseando XML con ElementTree...")
            root = ET.fromstring(xml_source)
            logger.debug(f"UIPARSER: ✓ XML parseado correctamente. Tag raíz: {root.tag}")
        except ET.ParseError as e:
            logger.error(f"UIPARSER ERROR: Fallo al parsear XML: {e}")
            logger.error(f"UIPARSER ERROR: Traceback completo:\n{traceback.format_exc()}")
            # Mostrar contexto del error si es posible
            if hasattr(e, 'position'):
                line, col = e.position
                logger.error(f"UIPARSER ERROR: Error en línea {line}, columna {col}")
            raise ValueError(f"Error parsing XML: {e}")

        # Extraer tamaño de pantalla del root (atributos width y height del hierarchy)
        try:
            self.screen_width = int(root.get("width", "0"))
            self.screen_height = int(root.get("height", "0"))
            if self.screen_width > 0 and self.screen_height > 0:
                logger.debug(f"UIPARSER: Tamaño de pantalla detectado: {self.screen_width}x{self.screen_height}")
            else:
                logger.warning("UIPARSER: No se pudo obtener tamaño de pantalla del XML, usando valores por defecto")
                self.screen_width = 1080  # Valores por defecto comunes
                self.screen_height = 2400
        except (ValueError, TypeError) as e:
            logger.warning(f"UIPARSER: Error extrayendo tamaño de pantalla: {e}, usando valores por defecto")
            self.screen_width = 1080
            self.screen_height = 2400

        # Reset para nuevo parseo
        self.element_map = {}
        self.element_info_map = {}
        self.current_id = 0
        elements = []

        # Recorrer árbol recursivamente
        #logger.debug("UIPARSER: Iniciando recorrido del árbol XML...")
        self._traverse_tree(root, "", elements, None)
        
        # Log estadísticas finales
        #logger.info("UIPARSER: Parseo completado")
        #logger.info(f"  - Nodos visitados: {self._parse_stats['total_nodes_visited']}")
        #logger.info(f"  - Elementos interactuables encontrados: {len(elements)}")
        #logger.info(f"  - Elementos filtrados: {self._parse_stats['filtered_out']}")
        #logger.info("UIPARSER: Elementos encontrados:", json.dumps(elements, indent=4))
                
        return elements

    def _traverse_tree(
        self, element: ET.Element, parent_path: str, elements: List[UIElement], parent_element: Optional[ET.Element] = None
    ):
        """
        Recorre el árbol XML recursivamente y filtra elementos interactuables.

        Args:
            element: Elemento XML actual
            parent_path: XPath acumulado del elemento padre (para construir xpath jerárquico)
            elements: Lista donde se acumulan los elementos válidos
            parent_element: Elemento padre (para calcular posición entre hermanos)
        """
        self._parse_stats["total_nodes_visited"] += 1
        
        # Generar XPath jerárquico para este elemento
        current_path = self._generate_xpath(element, parent_path, parent_element)
        
        # Log a nivel TRACE (solo si se activa)
        class_name = element.get("class", "unknown")

        # Verificar si este elemento debe incluirse
        if self._is_interactable_element(element):
            self._parse_stats["interactable_found"] += 1
            # Asignar ID antes de crear el elemento
            element_id = self.current_id
            # Extraer información y agregar a la lista (pasando el ID asignado)
            element_info = self._extract_element_info(element, current_path, element_id)
            if element_info:
                elements.append(element_info)
                # Guardar mapeos ID -> XPath e ID -> Info completa
                self.element_map[element_id] = current_path
                self.element_info_map[element_id] = element_info
                self.current_id += 1
            else:
                self._parse_stats["filtered_out"] += 1
        else:
            self._parse_stats["filtered_out"] += 1

        # Continuar recorriendo hijos
        for child in element:
            self._traverse_tree(child, current_path, elements, element)

    def _is_interactable_element(self, element: ET.Element) -> bool:
        """
        Valida si un elemento debe incluirse en la lista de elementos interactuables.

        Reglas de inclusión:
        - focusable="true" - REQUERIDO (excepto casos especiales)
        - clickable="true" (con info útil: text, content-desc o resource-id)
        - Clase contiene "EditText" (inputs) - se incluyen siempre
        - ImageView clickable - se incluyen siempre (botones de imagen)
        - ImageView no clickable pero con información (content-desc/text) - NUEVO
        - Elementos informativos no clickables con texto significativo - NUEVO

        Reglas de EXCLUSIÓN (NUEVAS):
        - Contenedores grandes (>80% de pantalla) - excluidos
        - Contenedores con hijos interactuables (EditText, ImageView clickable) - excluidos
        - Elementos con content-desc que son solo máscaras (**********, etc.) - excluidos

        Args:
            element: Elemento XML a validar

        Returns:
            True si el elemento debe incluirse, False en caso contrario
        """
        # Obtener atributos relevantes
        focusable = element.get("focusable", "false").lower() == "true"
        clickable = element.get("clickable", "false").lower() == "true"
        class_name = element.get("class", "").lower()
        text = element.get("text", "").strip()
        content_desc = element.get("content-desc", "").strip()
        resource_id = element.get("resource-id", "").strip()
        bounds = element.get("bounds", "").strip()

        # focusable es REQUERIDO para cualquier elemento interactuable
        if not focusable:
            return False

        # ======================================================================
        # REGLAS DE EXCLUSIÓN (aplicar ANTES de las reglas de inclusión)
        # ======================================================================

        # REGLA 1: Detectar contenedores grandes (>80% de pantalla)
        # EXCEPCIÓN: No excluir si es clickable Y tiene información útil (content-desc, text, resource-id)
        # Esto permite incluir botones grandes que cubren toda la pantalla pero son interactuables reales
        if bounds:
            width, height = self._parse_bounds_size(bounds)
            if self.screen_width > 0 and self.screen_height > 0:
                area_element = width * height
                area_screen = self.screen_width * self.screen_height
                coverage = area_element / area_screen if area_screen > 0 else 0
                
                # EXCLUSIÓN ABSOLUTA: Elementos que ocupan ≥95% de la pantalla (sin excepciones)
                # Esta regla debe aplicarse ANTES de cualquier otra verificación
                if coverage >= 0.95:  # 95% o más (casi pantalla completa)
                    # logger.debug(
                    #     f"UIPARSER: Excluyendo elemento que ocupa casi toda la pantalla "
                    #     f"(cobertura: {coverage:.1%}, content-desc: '{content_desc}', class: {class_name})"
                    # )
                    return False
                
                # Si cubre más del 80% pero menos del 95%, aplicar lógica existente
                elif coverage > 0.80:
                    # Verificar si es un elemento interactuable real (clickable con info útil)
                    is_real_interactable = clickable and (content_desc or text or resource_id)
                    
                    if is_real_interactable:
                        # Es un botón grande pero real, no excluir
                        logger.debug(
                            f"UIPARSER: Manteniendo botón grande interactuable "
                            f"(cobertura: {coverage:.1%}, content-desc: '{content_desc}', class: {class_name})"
                        )
                    else:
                        # Es un contenedor grande sin información útil, excluir
                        logger.debug(
                            f"UIPARSER: Excluyendo contenedor grande "
                            f"(cobertura: {coverage:.1%}, bounds: {bounds}, class: {class_name})"
                        )
                        return False

        # REGLA 2: Detectar contenedores con hijos interactuables
        if clickable:
            has_interactable_children = False
            for child in element:
                child_class = child.get("class", "").lower()
                child_clickable = child.get("clickable", "false").lower() == "true"
                child_focusable = child.get("focusable", "false").lower() == "true"
                
                # Si tiene un EditText hijo, es un contenedor (ej: contenedor de password)
                if "edittext" in child_class and child_focusable:
                    has_interactable_children = True
                    logger.debug(
                        f"UIPARSER: Excluyendo contenedor con EditText hijo "
                        f"(content-desc: '{content_desc}', class: {class_name})"
                    )
                    break
                # Si tiene un ImageView clickable hijo, es un contenedor (ej: contenedor con icono)
                if "imageview" in child_class and child_clickable and child_focusable:
                    has_interactable_children = True
                    logger.debug(
                        f"UIPARSER: Excluyendo contenedor con ImageView clickable hijo "
                        f"(content-desc: '{content_desc}', class: {class_name})"
                    )
                    break
            
            if has_interactable_children:
                return False

        # REGLA 3: Excluir elementos con content-desc que son solo máscaras
        if content_desc and clickable:
            # Patrones que indican contenedores, no botones reales
            # Normalizar espacios y caracteres especiales
            content_desc_normalized = content_desc.strip()
            mask_patterns = ["**********", "••••••••", "••••••", "****", "••••"]
            # También detectar patrones repetitivos de asteriscos o puntos
            if content_desc_normalized in mask_patterns:
                logger.debug(
                    f"UIPARSER: Excluyendo contenedor de máscara "
                    f"(content-desc: '{content_desc}', class: {class_name})"
                )
                return False
            # Detectar patrones repetitivos (solo asteriscos o solo puntos)
            if len(content_desc_normalized) > 3:
                if all(c in ['*', '•', '·'] for c in content_desc_normalized):
                    logger.debug(
                        f"UIPARSER: Excluyendo contenedor de máscara (patrón repetitivo) "
                        f"(content-desc: '{content_desc}', class: {class_name})"
                    )
                    return False

        # ======================================================================
        # REGLAS DE INCLUSIÓN (aplicar después de las exclusiones)
        # ======================================================================

        # 1. FORM WIDGETS: Siempre incluidos (EditText, CheckBox, SeekBar)
        is_form_widget = (
            "edittext" in class_name
            or "input" in class_name
            or "checkbox" in class_name
            or "seekbar" in class_name
        )
        if is_form_widget:
            return True

        # 1.5. INPUT SELECTORS: Elementos con hint (date pickers, dropdowns)
        # Solo inputs tienen hint en Android → si tiene hint, es un input selector
        hint = element.get("hint", "").strip()
        if focusable and hint:
            return True

        # 2. IMAGEVIEW: Incluir si:
        #    - Es clickable (botón de imagen o icono)
        #    - O tiene información valiosa (content-desc/text) aunque no sea clickable
        #      Esto captura elementos como el ImageView del diálogo de éxito
        if "imageview" in class_name:
            if clickable:
                return True  # Botón de imagen o icono clickable
            elif content_desc or text:
                # ImageView informativo (como el diálogo de éxito con mensaje)
                # Verificar que el contenido sea significativo (más de 3 caracteres)
                meaningful_content = len(content_desc) > 3 or len(text) > 3
                if meaningful_content:
                    return True
            return False

        # 3. ELEMENTOS CLICKABLES: Incluir si tienen info útil
        if clickable:
            if text or content_desc or resource_id:
                return True

        # 4. ELEMENTOS INFORMATIVOS NO CLICKABLES
        # Incluir si tienen información valiosa (text o content-desc)
        # Esto captura textos de diálogos, labels informativos, etc.
        if text or content_desc:
            # Verificar que el texto sea significativo (más de 3 caracteres)
            meaningful_text = len(text) > 3 or len(content_desc) > 3
            if meaningful_text:
                return True

        return False

    def _extract_element_info(
        self, element: ET.Element, xpath: str, element_id: int
    ) -> Optional[UIElement]:
        """
        Extrae información relevante del elemento para el JSON de salida.

        Genera una lista de atributos con estructura fija {name, value}.
        Solo incluye atributos con valor no vacío (excepto booleanos que siempre se incluyen).

        Args:
            element: Elemento XML
            xpath: XPath jerárquico generado para este elemento
            element_id: ID único asignado por UIParser (USAR ESTE EN TOOL CALLS)

        Returns:
            Diccionario UIElement con id y lista de attrs
        """
        attrs: List[UIAttribute] = []
        
        # === ATRIBUTOS DE LOCALIZACIÓN (solo si tienen valor) ===
        # Estos son los que el LLM puede usar para encontrar el elemento
        
        resource_id = element.get("resource-id", "").strip()
        if resource_id:
            attrs.append({"name": "resource-id", "value": resource_id})
        
        content_desc = element.get("content-desc", "").strip()
        if content_desc:
            attrs.append({"name": "content-desc", "value": content_desc})
        
        text = element.get("text", "").strip()
        if text:
            attrs.append({"name": "text", "value": text})
        
        # === ATRIBUTOS DE IDENTIFICACIÓN (siempre se incluyen) ===
        
        class_name = element.get("class", "")
        attrs.append({"name": "class", "value": class_name})
        
        # XPath del elemento (requerido - ya verificado al inicio)
        attrs.append({"name": "xpath", "value": xpath})
        
        # === ATRIBUTOS DE POSICIÓN (solo si tienen valor) ===
        
        bounds = element.get("bounds", "").strip()
        if bounds:
            attrs.append({"name": "bounds", "value": bounds})
        
        # === ATRIBUTOS DE ESTADO (siempre se incluyen los relevantes) ===
        
        clickable = element.get("clickable", "false")
        attrs.append({"name": "clickable", "value": clickable})
        
        enabled = element.get("enabled", "false")
        attrs.append({"name": "enabled", "value": enabled})
        
        displayed = element.get("displayed", "false")
        attrs.append({"name": "displayed", "value": displayed})
        
        # password y scrollable solo si son "true" (son menos comunes)
        password = element.get("password", "false")
        if password == "true":
            attrs.append({"name": "password", "value": password})
        
        scrollable = element.get("scrollable", "false")
        if scrollable == "true":
            attrs.append({"name": "scrollable", "value": scrollable})
        
        # hint solo si tiene valor (placeholder para inputs)
        hint = element.get("hint", "").strip()
        if hint:
            attrs.append({"name": "hint", "value": hint})

        # checkable y checked solo para checkboxes
        checkable = element.get("checkable", "false")
        if checkable == "true":
            attrs.append({"name": "checkable", "value": checkable})
            checked = element.get("checked", "false")
            attrs.append({"name": "checked", "value": checked})

        # NUEVO: Detectar y agregar tipo de elemento
        element_type = self._detect_element_type(element)
        attrs.append({"name": "possible_element_type", "value": element_type})

        # Retornar estructura UIElement con id y lista de attrs
        return UIElement(
            id=element_id,
            attrs=attrs
        )

    def _parse_bounds_size(self, bounds: str) -> tuple[int, int]:
        """
        Parsea bounds "[x1,y1][x2,y2]" y retorna (width, height).
        
        Args:
            bounds: String con formato "[x1,y1][x2,y2]"
            
        Returns:
            Tupla (width, height) o (0, 0) si no se puede parsear
        """
        if not bounds:
            return (0, 0)
        
        try:
            match = re.match(r'\[(\d+),(\d+)\]\[(\d+),(\d+)\]', bounds)
            if match:
                x1, y1, x2, y2 = map(int, match.groups())
                return (x2 - x1, y2 - y1)
        except Exception as e:
            logger.debug(f"UIPARSER: Error parseando bounds '{bounds}': {e}")
        
        return (0, 0)

    def _detect_element_type(self, element: ET.Element) -> str:
        """
        Detecta el tipo de elemento basado en sus características.
        
        Tipos posibles:
        - "button": Elemento clickable con acción (View, Button, etc.)
        - "input": EditText (campo de entrada)
        - "text": Elemento informativo no clickable (TextView, View con texto)
        - "image_button": ImageView clickable grande (botón de imagen)
        - "image_info": ImageView no clickable pero con información (content-desc/text)
        - "icon_button": ImageView clickable pequeño (iconos como ojo de password)
        - "link": Elemento clickable con texto que parece enlace
        
        Args:
            element: Elemento XML a analizar
            
        Returns:
            String con el tipo detectado
        """
        class_name = element.get("class", "").lower()
        clickable = element.get("clickable", "false").lower() == "true"
        focusable = element.get("focusable", "false").lower() == "true"
        text = element.get("text", "").strip()
        content_desc = element.get("content-desc", "").strip()
        bounds = element.get("bounds", "").strip()
        
        # Calcular tamaño del elemento desde bounds
        width, height = self._parse_bounds_size(bounds)
        is_small = width < 200 and height < 200  # Iconos pequeños (< 200x200)

        # 0. INPUT SELECTOR: Elementos con hint (no EditText)
        # Date pickers, dropdowns, etc. que no aceptan texto directo
        hint = element.get("hint", "").strip()
        if hint and focusable and "edittext" not in class_name:
            return "input_select"

        # 1. INPUT: EditText siempre es input
        if "edittext" in class_name:
            return "input"

        # 1.5. CHECKBOX: CheckBox widget
        if "checkbox" in class_name:
            return "checkbox"

        # 1.6. SEEKBAR/SLIDER: Control deslizante
        if "seekbar" in class_name or "slider" in class_name:
            return "slider"

        # 2. IMAGEVIEW: Diferentes tipos según clickable y tamaño
        if "imageview" in class_name:
            if clickable:
                return "icon_button" if is_small else "image_button"
            elif focusable and (content_desc or text):
                # ImageView con información (como el diálogo de éxito)
                return "image_info"
            else:
                return "image_info"  # Por defecto para ImageView
        
        # 3. BUTTON: Elemento clickable con acción
        if clickable:
            # Si tiene texto descriptivo, puede ser link o button
            if text or content_desc:
                # Links suelen tener texto corto y específico
                link_keywords = ["crear", "olvidaste", "iniciar", "enviar", "cerrar", "salir"]
                text_lower = (text + " " + content_desc).lower()
                if any(keyword in text_lower for keyword in link_keywords):
                    return "link"
            return "button"
        
        # 4. TEXT: Elemento informativo no clickable
        if focusable and (text or content_desc):
            return "text"
        
        # Por defecto
        return "unknown"

    def _generate_xpath(
        self, element: ET.Element, parent_path: str, parent_element: Optional[ET.Element] = None
    ) -> str:
        """
        Genera un XPath corto basado en la estructura del árbol XML.
        
        Similar a Appium Inspector: empieza desde el ancestro más cercano
        que tenga un identificador único, generando xpaths cortos y legibles.

        Estrategia:
        - Si el elemento tiene identificador (resource-id, content-desc, text):
          Reinicia el xpath con // (búsqueda global desde ese punto)
        - Si no tiene identificador:
          Continúa acumulando desde el padre con / (ruta relativa)

        Args:
            element: Elemento XML actual
            parent_path: XPath acumulado del padre
            parent_element: Elemento padre (para calcular índice entre hermanos)

        Returns:
            XPath corto del elemento (similar a Appium Inspector)
        """
        tag = element.tag
        
        # Obtener atributos identificadores
        resource_id = element.get("resource-id", "").strip()
        content_desc = element.get("content-desc", "").strip()
        text = element.get("text", "").strip()
        
        # Determinar si este elemento tiene un identificador único
        has_identifier = bool(resource_id or content_desc or text)
        
        # Construir el segmento xpath para este elemento
        if resource_id:
            resource_id_escaped = resource_id.replace("'", "\\'")
            segment = f"{tag}[@resource-id='{resource_id_escaped}']"
        elif content_desc:
            content_desc_escaped = content_desc.replace("'", "\\'")
            segment = f"{tag}[@content-desc='{content_desc_escaped}']"
        elif text:
            text_escaped = text.replace("'", "\\'")
            segment = f"{tag}[@text='{text_escaped}']"
        else:
            # Sin identificador: usar índice entre hermanos del mismo tipo
            index = self._get_sibling_index(element, parent_element)
            if index > 1:
                segment = f"{tag}[{index}]"
            else:
                segment = tag
        
        # Si tiene identificador, reiniciar el xpath (como Appium Inspector)
        if has_identifier:
            return f"//{segment}"
        
        # Si no tiene identificador, acumular desde el padre
        if parent_path:
            return f"{parent_path}/{segment}"
        else:
            return f"//{segment}"
    
    def _get_sibling_index(self, element: ET.Element, parent_element: Optional[ET.Element]) -> int:
        """
        Calcula el índice (1-based) del elemento entre sus hermanos del mismo tipo.
        
        Args:
            element: Elemento actual
            parent_element: Elemento padre
            
        Returns:
            Índice del elemento (1 si es el primero o único de su tipo)
        """
        if parent_element is None:
            return 1
        
        tag = element.tag
        index = 1
        
        for sibling in parent_element:
            if sibling is element:
                break
            if sibling.tag == tag:
                index += 1
        
        return index

    def get_element_by_id(self, element_id: int) -> Optional[str]:
        """
        Recupera el XPath real de un elemento usando su ID temporal.

        Args:
            element_id: ID del elemento (asignado durante parse_screen)

        Returns:
            XPath del elemento o None si no existe
        """
        logger.debug(f"UIPARSER: Buscando XPath para elemento ID {element_id}")
        
        xpath = self.element_map.get(element_id)
        
        if xpath:
            logger.debug(f"UIPARSER: ✓ XPath encontrado para ID {element_id}: {xpath}")
        else:
            logger.warning(f"UIPARSER WARNING: ID {element_id} NO encontrado en el mapeo")
            logger.warning(f"UIPARSER WARNING: IDs disponibles: {list(self.element_map.keys())}")
            # Diagnóstico adicional
            if not self.element_map:
                logger.error("UIPARSER ERROR: El mapeo de elementos está VACÍO. "
                           "¿Se llamó parse_screen() antes?")
            elif element_id < 0:
                logger.error(f"UIPARSER ERROR: ID inválido (negativo): {element_id}")
            elif element_id >= self.current_id:
                logger.error(f"UIPARSER ERROR: ID {element_id} fuera de rango. "
                           f"Último ID asignado: {self.current_id - 1}")
        
        return xpath

    def get_element_info_by_id(self, element_id: int) -> Optional[UIElement]:
        """
        Recupera la información completa de un elemento usando su ID.

        Args:
            element_id: ID del elemento (asignado durante parse_screen)

        Returns:
            Diccionario UIElement con toda la info del elemento o None si no existe
        """
        logger.debug(f"UIPARSER: Buscando info completa para elemento ID {element_id}")
        
        element_info = self.element_info_map.get(element_id)
        
        if element_info:
            class_name = self._get_attr_value(element_info, "class", "unknown")
            logger.debug(f"UIPARSER: ✓ Info encontrada para ID {element_id}: class={class_name}")
        else:
            logger.warning(f"UIPARSER WARNING: ID {element_id} NO encontrado en element_info_map")
        
        return element_info

    def is_editable_element(self, element_id: int) -> bool:
        """
        Verifica si un elemento es editable (clase contiene 'EditText').

        Args:
            element_id: ID del elemento

        Returns:
            True si el elemento es un campo de texto editable, False en caso contrario
        """
        element_info = self.element_info_map.get(element_id)
        if not element_info:
            return False
        
        # Buscar el atributo "class" en la lista de attrs
        class_name = self._get_attr_value(element_info, "class", "").lower()
        return "edittext" in class_name
    
    def _get_attr_value(self, element: UIElement, attr_name: str, default: str = "") -> str:
        """
        Obtiene el valor de un atributo específico de un UIElement.
        
        Args:
            element: UIElement con lista de attrs
            attr_name: Nombre del atributo a buscar
            default: Valor por defecto si no se encuentra
        
        Returns:
            Valor del atributo o default si no existe
        """
        for attr in element.get("attrs", []):
            if attr.get("name") == attr_name:
                return attr.get("value", default)
        return default

    def clear(self):
        """Limpia el mapeo de elementos (útil para resetear estado)."""
        logger.debug("UIPARSER: Limpiando mapeo de elementos")
        previous_count = len(self.element_map)
        self.element_map = {}
        self.element_info_map = {}
        self.current_id = 0
        logger.debug(f"UIPARSER: Limpiados {previous_count} elementos del mapeo")
    
    def debug_dump_element_map(self, log_output: bool = True) -> str:
        """
        DEBUG: Retorna una representación completa del mapeo actual de elementos.
        Útil para diagnóstico y troubleshooting.
        
        Args:
            log_output: Si True, también imprime el dump al logger (default: True)
        
        Returns:
            String con el dump completo del estado del UIParser
        """
        lines = []
        lines.append("")
        lines.append("╔" + "═" * 70 + "╗")
        lines.append("║  UIPARSER DEBUG: DUMP DEL MAPEO DE ELEMENTOS")
        lines.append("╠" + "═" * 70 + "╣")
        
        # Estadísticas generales
        lines.append("║  ESTADÍSTICAS:")
        lines.append(f"║    • Total elementos mapeados: {len(self.element_map)}")
        lines.append(f"║    • Próximo ID a asignar: {self.current_id}")
        lines.append(f"║    • Rango de IDs válidos: 0 - {self.current_id - 1 if self.current_id > 0 else 'N/A'}")
        lines.append("║")
        
        # Estadísticas del último parseo
        lines.append("║  ÚLTIMO PARSEO:")
        lines.append(f"║    • Nodos visitados: {self._parse_stats.get('total_nodes_visited', 'N/A')}")
        lines.append(f"║    • Interactuables encontrados: {self._parse_stats.get('interactable_found', 'N/A')}")
        lines.append(f"║    • Elementos filtrados: {self._parse_stats.get('filtered_out', 'N/A')}")
        lines.append("║")
        
        # Mapeo de elementos
        lines.append("╠" + "─" * 70 + "╣")
        lines.append("║  MAPEO ID → XPATH:")
        lines.append("╠" + "─" * 70 + "╣")
        
        if not self.element_map:
            lines.append("║  (vacío - no se ha parseado ninguna pantalla)")
        else:
            for elem_id, xpath in sorted(self.element_map.items()):
                # Truncar XPath largo para mejor visualización
                xpath_display = xpath if len(xpath) <= 55 else xpath[:52] + "..."
                lines.append(f"║  ID {elem_id:3d} → {xpath_display}")
        
        lines.append("╚" + "═" * 70 + "╝")
        lines.append("")
        
        output = "\n".join(lines)
        
        # Log si se solicita
        if log_output:
            for line in lines:
                if line.strip():
                    #logger.info(line)
                    pass
        
        return output
    
    def debug_get_element_details(self, element_id: int) -> Optional[Dict[str, Any]]:
        """
        DEBUG: Obtiene detalles completos de un elemento por su ID.
        
        Args:
            element_id: ID del elemento a inspeccionar
        
        Returns:
            Diccionario con detalles del elemento o None si no existe
        """
        xpath = self.element_map.get(element_id)
        
        if xpath is None:
            logger.warning(f"UIPARSER DEBUG: Elemento ID {element_id} no encontrado")
            return None
        
        return {
            "id": element_id,
            "xpath": xpath,
            "is_valid": element_id < self.current_id,
            "total_elements": len(self.element_map),
        }

    def elements_to_json(self, elements: List[UIElement], compact: bool = False) -> str:
        """
        Convierte una lista de elementos UI a formato JSON.

        Args:
            elements: Lista de elementos parseados por parse_screen()
            compact: Si True, genera JSON sin espacios ni indentación

        Returns:
            String JSON con los elementos
        """
        if not elements:
            logger.debug("UIPARSER: elements_to_json() - Lista vacía, retornando '[]'")
            return "[]"
        
        logger.debug(f"UIPARSER: Convirtiendo {len(elements)} elementos a JSON")
        
        if compact:
            json_output = json.dumps(elements, ensure_ascii=False, separators=(',', ':'))
        else:
            json_output = json.dumps(elements, indent=2, ensure_ascii=False)
        
        logger.debug(f"UIPARSER: ✓ Conversión JSON completada ({len(json_output)} caracteres)")
        
        return json_output

    def parse_screen_to_json(self, xml_source: str, compact: bool = False) -> str:
        """
        Parsea el XML y retorna elementos directamente en formato JSON.
        
        Combina parse_screen() y elements_to_json() en una sola operación
        para conveniencia.
        
        Args:
            xml_source: String con el XML completo de page_source
            compact: Si True, genera JSON sin espacios ni indentación
        
        Returns:
            String JSON con los elementos interactuables
        """
        elements = self.parse_screen(xml_source)
        logger.debug(f"UIPARSER: Elementos encontrados: {len(elements)}")
        json_output = self.elements_to_json(elements, compact)
        return json_output
    
    # Métodos TOON deprecados (mantenidos para compatibilidad)
    def elements_to_toon(self, elements: List[UIElement]) -> str:
        """
        DEPRECADO: Convierte elementos a formato TOON.
        
        NOTA: Con la nueva estructura de attrs [{name, value}], TOON no es
        eficiente. Se recomienda usar elements_to_json() en su lugar.
        
        Args:
            elements: Lista de elementos parseados por parse_screen()

        Returns:
            String en formato TOON con los elementos
        """
        if not elements:
            logger.debug("UIPARSER: elements_to_toon() - Lista vacía, retornando string vacío")
            return ""
        
        logger.warning("UIPARSER: elements_to_toon() está deprecado. "
                      "Con la nueva estructura de attrs, se recomienda elements_to_json()")
        
        toon_options = {
            "delimiter": "|",
        }
        
        toon_output = toon_encode(elements, toon_options)
        
        return toon_output

    def parse_screen_to_toon(self, xml_source: str) -> str:
        """
        DEPRECADO: Parsea XML y retorna en formato TOON.
        
        Se recomienda usar parse_screen_to_json() en su lugar.
        """
        elements = self.parse_screen(xml_source)
        return self.elements_to_toon(elements)

