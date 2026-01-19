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
from typing import List, Dict, Optional, Any, Union
from typing_extensions import TypedDict
import re
import json

from toon_format import encode as toon_encode
from src.middleware_result import MiddlewareResult, MiddlewareStatus

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

    def __init__(self):
        """Inicializa el parser con mapeo vacío de elementos."""
        logger.debug("UIPARSER: Inicializando UIParser")
        self.element_map: Dict[int, str] = {}  # ID -> XPath
        self.element_info_map: Dict[int, UIElement] = {}  # ID -> Información completa del elemento
        self.current_id = 0
        self._parse_stats = {
            "total_nodes_visited": 0,
            "interactable_found": 0,
            "filtered_out": 0,
        }

    def parse_screen(
        self, 
        xml_source: str, 
        current_package: Optional[str] = None, 
        allowed_packages: Optional[List[str]] = None
    ) -> Union[List[UIElement], MiddlewareResult]:
        """
        Parsea el XML y retorna lista de elementos interactuables.

        Criterios de inclusión:
        - focusable="true" - REQUERIDO
        - clickable="true" (con info útil: text, content-desc o resource-id)
        - Clase contiene "EditText" (inputs) - siempre incluidos
        - Clase contiene "ImageView" + clickable (botones de imagen) - siempre incluidos

        Args:
            xml_source: String con el XML completo de page_source
            current_package: Package de la app actual en foreground (opcional)
            allowed_packages: Lista de packages permitidos (opcional)

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
        logger.debug("=" * 70)
        logger.debug("UIPARSER: Iniciando parseo de pantalla")
        logger.debug("=" * 70)
        
        # Validar scope de app si se proporcionan allowed_packages
        if allowed_packages:
            if not current_package or current_package not in allowed_packages:
                # App no permitida o launcher/sistema
                allowed_str = ", ".join(allowed_packages)
                logger.warning(
                    f"UIPARSER: App actual '{current_package}' no está en allowed_packages. "
                    f"Apps permitidas: {allowed_packages}"
                )
                return MiddlewareResult(
                    status=MiddlewareStatus.DENIED,
                    message=f"No hay app permitida en foreground. Apps permitidas: {allowed_str}. Usa activate_app(app_package) para abrir una app permitida.",
                    allowed_apps=allowed_packages,
                    suggested_tool="activate_app"
                )
        
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
        - focusable="true" - REQUERIDO
        - clickable="true" (con info útil: text, content-desc o resource-id)
        - Clase contiene "EditText" (inputs) - se incluyen siempre
        - Clase contiene "ImageView" (botones de imagen) - se incluyen siempre

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

        # focusable es REQUERIDO para cualquier elemento interactuable
        if not focusable:
            return False

        # Verificar tipos especiales que siempre se incluyen
        is_input = "edittext" in class_name or "input" in class_name
        is_image_button = "imageview" in class_name and clickable

        # Inputs siempre se incluyen (aunque no tengan info útil)
        if is_input:
            return True

        # ImageView clickables siempre se incluyen (botones de imagen como show/hide password)
        if is_image_button:
            return True

        # Para otros elementos clickables, requieren info útil
        if clickable:
            if text or content_desc or resource_id:
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

        # Retornar estructura UIElement con id y lista de attrs
        return UIElement(
            id=element_id,
            attrs=attrs
        )

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

