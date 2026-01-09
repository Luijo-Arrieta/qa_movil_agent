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
from typing import List, Dict, Optional, Any
from typing_extensions import TypedDict
import re

from toon_format import encode as toon_encode

# Configurar logging para este módulo
logger = logging.getLogger(__name__)


# TypedDict con claves que contienen guiones (usando sintaxis funcional)
# Esto permite usar los mismos nombres que el XML de Appium
UIElement = TypedDict(
    "UIElement",
    {
        "resource-id": str,  # ID del recurso Android
        "content-desc": str,  # Descripción de accesibilidad
        "class": str,  # Clase del componente Android
        "index": str,  # Índice del elemento en su padre
        "xpath": str,  # XPath generado para localizar el elemento
        "bounds": str,  # Coordenadas [x1,y1][x2,y2]
        "clickable": str,  # "true" o "false"
        "displayed": str,  # "true" o "false"
        "enabled": str,  # "true" o "false"
        "password": str,  # "true" o "false"
        "scrollable": str,  # "true" o "false"
        "text": str,  # Texto visible del elemento
        "hint": str,  # Placeholder del input
    },
)
"""
UIElement - Representa un elemento de UI extraído del XML de Appium.

Las propiedades están ordenadas por prioridad para construir selectores:
1. resource-id (más estable y único)
2. content-desc (accesibilidad)
3. class (tipo de elemento)
4. index (posición en padre)
5. xpath (selector generado)
6. bounds (coordenadas)
7-11. Propiedades booleanas (clickable, displayed, enabled, password, scrollable)
12. text (texto visible)
13. hint (placeholder para inputs)
"""


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
        self.current_id = 0
        self._parse_stats = {
            "total_nodes_visited": 0,
            "interactable_found": 0,
            "filtered_out": 0,
        }

    def parse_screen(self, xml_source: str) -> List[UIElement]:
        """
        Parsea el XML y retorna lista de elementos interactuables con propiedades reales.

        Criterios de inclusión (focusable="true" es REQUERIDO):
        - clickable="true" (con info útil: text, content-desc o resource-id)
        - Clase contiene "EditText" (inputs) - siempre incluidos
        - Clase contiene "ImageView" + clickable (botones de imagen) - siempre incluidos

        Args:
            xml_source: String con el XML completo de page_source

        Returns:
            Lista de diccionarios con propiedades del XML en este orden (prioridad para selectores):
            - resource-id: ID del recurso Android
            - content-desc: Descripción de accesibilidad
            - class: Clase del componente Android
            - index: Índice del elemento en su padre
            - xpath: XPath generado para localizar el elemento
            - bounds: Coordenadas del elemento [x1,y1][x2,y2]
            - clickable: Si es clickeable ("true"/"false")
            - displayed: Si está visible ("true"/"false")
            - enabled: Si está habilitado ("true"/"false")
            - password: Si es campo de contraseña ("true"/"false")
            - scrollable: Si es scrolleable ("true"/"false")
            - text: Texto visible del elemento
            - hint: Placeholder del input (solo para EditText)
        """
        logger.debug("=" * 70)
        logger.debug("UIPARSER: Iniciando parseo de pantalla")
        logger.debug("=" * 70)
        
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
        self.current_id = 0
        elements = []

        # Recorrer árbol recursivamente
        logger.debug("UIPARSER: Iniciando recorrido del árbol XML...")
        self._traverse_tree(root, "", elements, None)
        
        # Log estadísticas finales
        logger.info("UIPARSER: Parseo completado")
        logger.info(f"  - Nodos visitados: {self._parse_stats['total_nodes_visited']}")
        logger.info(f"  - Elementos interactuables encontrados: {len(elements)}")
        logger.info(f"  - Elementos filtrados: {self._parse_stats['filtered_out']}")
        
        # Mostrar elementos encontrados
        if elements:
            logger.debug("UIPARSER: Elementos encontrados:")
            for elem in elements:
                # Mostrar identificador más relevante
                identifier = elem.get('resource-id') or elem.get('content-desc') or elem.get('text') or 'sin-id'
                logger.debug(f"  [{elem['class']}] '{identifier}' clickable={elem['clickable']}")
        else:
            logger.warning("UIPARSER WARNING: No se encontraron elementos interactuables en la pantalla")
        
        return elements

    def _traverse_tree(
        self, element: ET.Element, parent_path: str, elements: List[UIElement], parent_element: Optional[ET.Element] = None
    ):
        """
        Recorre el árbol XML recursivamente y filtra elementos interactuables.

        Args:
            element: Elemento XML actual
            parent_path: XPath del elemento padre
            elements: Lista donde se acumulan los elementos válidos
            parent_element: Elemento padre (para calcular posición)
        """
        self._parse_stats["total_nodes_visited"] += 1
        
        # Generar XPath para este elemento
        current_path = self._generate_xpath(element, parent_element)
        
        # Log a nivel TRACE (solo si se activa)
        class_name = element.get("class", "unknown")
        logger.debug(f"UIPARSER TRACE: Visitando nodo {self._parse_stats['total_nodes_visited']}: "
                    f"{element.tag} class={class_name}")

        # Verificar si este elemento debe incluirse
        if self._is_interactable_element(element):
            self._parse_stats["interactable_found"] += 1
            # Extraer información y agregar a la lista
            element_info = self._extract_element_info(element, current_path)
            if element_info:
                elements.append(element_info)
                # Guardar mapeo index -> XPath para compatibilidad
                self.element_map[self.current_id] = current_path
                logger.debug(f"UIPARSER: ✓ Elemento agregado: "
                           f"class={element_info['class']} content-desc='{element_info['content-desc']}' "
                           f"resource-id='{element_info['resource-id']}' -> XPath: {current_path}")
                self.current_id += 1
            else:
                self._parse_stats["filtered_out"] += 1
                logger.debug(f"UIPARSER: Elemento interactuable sin info útil descartado: {class_name}")
        else:
            self._parse_stats["filtered_out"] += 1

        # Continuar recorriendo hijos
        children_count = len(list(element))
        if children_count > 0:
            logger.debug(f"UIPARSER TRACE: Procesando {children_count} hijos de {element.tag}")
        
        for child in element:
            self._traverse_tree(child, current_path, elements, element)

    def _is_interactable_element(self, element: ET.Element) -> bool:
        """
        Valida si un elemento debe incluirse en la lista de elementos interactuables.

        Reglas de inclusión:
        - focusable="true" es REQUERIDO para cualquier elemento
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
        self, element: ET.Element, xpath: str
    ) -> Optional[UIElement]:
        """
        Extrae información relevante del elemento para el JSON de salida.

        Extrae propiedades reales del XML tal cual están, para que el agente
        pueda construir selectores adecuados.

        Args:
            element: Elemento XML
            xpath: XPath generado para este elemento

        Returns:
            Diccionario con propiedades reales del elemento XML o None si no es válido
        """
        # Obtener atributos tal cual están en el XML
        resource_id = element.get("resource-id", "")
        content_desc = element.get("content-desc", "")
        class_name = element.get("class", "")
        index = element.get("index", "")
        bounds = element.get("bounds", "")
        clickable = element.get("clickable", "false")
        displayed = element.get("displayed", "false")
        enabled = element.get("enabled", "false")
        password = element.get("password", "false")
        scrollable = element.get("scrollable", "false")
        text = element.get("text", "")
        hint = element.get("hint", "")

        # Retornar propiedades usando UIElement TypedDict
        # La validación de inclusión ya se hizo en _is_interactable_element
        return UIElement(
            **{
                "resource-id": resource_id,
                "content-desc": content_desc,
                "class": class_name,
                "index": index,
                "xpath": xpath,
                "bounds": bounds,
                "clickable": clickable,
                "displayed": displayed,
                "enabled": enabled,
                "password": password,
                "scrollable": scrollable,
                "text": text,
                "hint": hint,
            }
        )

    def _generate_xpath(self, element: ET.Element, parent_element: Optional[ET.Element] = None) -> str:
        """
        Genera un XPath único para el elemento.

        Estrategia:
        1. Intentar usar resource-id si es único
        2. Usar texto si es único
        3. Usar content-desc si es único
        4. Fallback a posición con índice

        Args:
            element: Elemento XML
            parent_element: Elemento padre (para calcular posición entre hermanos)

        Returns:
            XPath completo del elemento
        """
        tag = element.tag
        resource_id = element.get("resource-id", "")
        text = element.get("text", "")
        content_desc = element.get("content-desc", "")

        # Construir XPath
        xpath = None

        # Estrategia 1: Usar resource-id si está disponible (más confiable)
        if resource_id:
            # Escapar comillas y caracteres especiales
            resource_id_escaped = resource_id.replace('"', '\\"')
            xpath = f'//{tag}[@resource-id="{resource_id_escaped}"]'
        # Estrategia 2: Usar texto si está disponible
        elif text:
            # Escapar comillas en el texto
            text_escaped = text.replace('"', '\\"').replace("'", "\\'")
            xpath = f'//{tag}[@text="{text_escaped}"]'
        # Estrategia 3: Usar content-desc
        elif content_desc:
            content_desc_escaped = content_desc.replace('"', '\\"').replace("'", "\\'")
            xpath = f'//{tag}[@content-desc="{content_desc_escaped}"]'
        # Estrategia 4: Usar clase con índice (fallback)
        else:
            # Contar posición entre hermanos del mismo tipo
            if parent_element is not None:
                siblings = [e for e in parent_element if e.tag == tag]
                if len(siblings) > 1:
                    index = siblings.index(element) + 1
                    xpath = f"//{tag}[{index}]"
                else:
                    xpath = f"//{tag}"
            else:
                xpath = f"//{tag}"

        return xpath

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

    def clear(self):
        """Limpia el mapeo de elementos (útil para resetear estado)."""
        logger.debug("UIPARSER: Limpiando mapeo de elementos")
        previous_count = len(self.element_map)
        self.element_map = {}
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
                    logger.info(line)
        
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

    def elements_to_toon(self, elements: List[UIElement]) -> str:
        """
        Convierte una lista de elementos UI a formato TOON.

        TOON (Token-Oriented Object Notation) reduce el consumo de tokens
        en un 30-60% comparado con JSON, ideal para arrays uniformes de objetos.

        Args:
            elements: Lista de elementos parseados por parse_screen()

        Returns:
            String en formato TOON con los elementos

        Example:
            JSON (más tokens):
            [{"resource-id": "btn_login", "content-desc": "Iniciar sesión", "class": "android.widget.Button", ..., "hint": ""}]

            TOON (menos tokens):
            [1\t]{resource-id\tcontent-desc\tclass\tindex\txpath\tbounds\tclickable\tdisplayed\tenabled\tpassword\tscrollable\ttext\thint}:
              btn_login\tIniciar sesión\tandroid.widget.Button\t0\t//...\t[0,0][100,50]\ttrue\ttrue\ttrue\tfalse\tfalse\tLogin\t
        """
        if not elements:
            logger.debug("UIPARSER: elements_to_toon() - Lista vacía, retornando string vacío")
            return ""
        
        logger.debug(f"UIPARSER: Convirtiendo {len(elements)} elementos a formato TOON")
        
        # Usar tabs como delimitador para mayor eficiencia de tokens
        toon_options = {
            "delimiter": "\t",
        }
        
        toon_output = toon_encode(elements, toon_options)
        
        logger.debug(f"UIPARSER: ✓ Conversión TOON completada ({len(toon_output)} caracteres)")
        
        return toon_output

    def parse_screen_to_toon(self, xml_source: str) -> str:
        """
        Parsea el XML y retorna elementos directamente en formato TOON.
        
        Combina parse_screen() y elements_to_toon() en una sola operación
        para conveniencia.
        
        Args:
            xml_source: String con el XML completo de page_source
        
        Returns:
            String en formato TOON con los elementos interactuables
        """
        elements = self.parse_screen(xml_source)
        return self.elements_to_toon(elements)

