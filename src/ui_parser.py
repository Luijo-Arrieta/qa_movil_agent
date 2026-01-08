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
import re

from toon_format import encode as toon_encode

# Configurar logging para este módulo
logger = logging.getLogger(__name__)


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

    def parse_screen(self, xml_source: str) -> List[Dict[str, Any]]:
        """
        Parsea el XML y retorna lista de elementos interactuables en formato JSON.

        Args:
            xml_source: String con el XML completo de page_source

        Returns:
            Lista de diccionarios con formato: [{"id": int, "role": str, "label": str, "checked": bool|None}]
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
        preview = xml_source[:200].replace('\n', ' ').replace('\r', '')
        logger.debug(f"UIPARSER: Preview del XML: {preview}...")
        
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
                logger.debug(f"  ID {elem['id']}: [{elem['role']}] '{elem['label']}' "
                           f"{'(checked)' if elem.get('checked') else ''}")
        else:
            logger.warning("UIPARSER WARNING: No se encontraron elementos interactuables en la pantalla")
        
        return elements

    def _traverse_tree(
        self, element: ET.Element, parent_path: str, elements: List[Dict[str, Any]], parent_element: Optional[ET.Element] = None
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
            element_info = self._extract_element_info(element, self.current_id)
            if element_info:
                elements.append(element_info)
                # Guardar mapeo ID -> XPath
                self.element_map[self.current_id] = current_path
                logger.debug(f"UIPARSER: ✓ Elemento ID {self.current_id} agregado: "
                           f"[{element_info['role']}] '{element_info['label']}' -> XPath: {current_path}")
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
        - clickable="true"
        - checkable="true"
        - Clase contiene "EditText" o "Input"
        - Tiene text o content-desc (excepto inputs que se incluyen siempre)

        Args:
            element: Elemento XML a validar

        Returns:
            True si el elemento debe incluirse, False en caso contrario
        """
        # Obtener atributos relevantes
        clickable = element.get("clickable", "false").lower() == "true"
        checkable = element.get("checkable", "false").lower() == "true"
        class_name = element.get("class", "").lower()
        text = element.get("text", "").strip()
        content_desc = element.get("content-desc", "").strip()
        resource_id = element.get("resource-id", "").strip()

        # Verificar si es un input (EditText, Input, etc.)
        is_input = "edittext" in class_name or "input" in class_name

        # Si es input, siempre incluirlo
        if is_input:
            return True

        # Si es clickable o checkable, incluir
        if clickable or checkable:
            # Debe tener información útil (text, content-desc, o resource-id)
            if text or content_desc or resource_id:
                return True

        return False

    def _extract_element_info(
        self, element: ET.Element, element_id: int
    ) -> Optional[Dict[str, Any]]:
        """
        Extrae información relevante del elemento para el JSON de salida.

        Args:
            element: Elemento XML
            element_id: ID asignado al elemento

        Returns:
            Diccionario con información del elemento o None si no tiene label útil
        """
        # Obtener atributos
        class_name = element.get("class", "").lower()
        text = element.get("text", "").strip()
        content_desc = element.get("content-desc", "").strip()
        resource_id = element.get("resource-id", "").strip()
        checked = element.get("checked", "").lower()
        clickable = element.get("clickable", "false").lower() == "true"
        checkable = element.get("checkable", "false").lower() == "true"

        # Determinar role
        role = self._determine_role(class_name, clickable, checkable)

        # Determinar si es input
        is_input = "edittext" in class_name or "input" in class_name
        
        # Determinar label (prioridad lógica: resource-id > content-desc > text > hint)
        # resource-id es el más estable y único, luego content-desc, luego text, y hint como último recurso
        label = resource_id
        if not label:
            label = content_desc
        if not label:
            label = text
        if not label:
            # Último recurso: hint (puede ser volátil o no estar presente)
            hint = element.get("hint", "").strip()
            if hint:
                label = hint

        # Si es input, siempre incluir aunque no tenga label
        if is_input and not label:
            label = "Input field"  # Label por defecto para inputs sin texto

        # Si no hay label y no es input, descartar
        if not label and not is_input:
            return None

        # Determinar checked (solo para checkboxes)
        checked_value = None
        if checkable:
            checked_value = checked == "true"

        return {
            "id": element_id,
            "role": role,
            "label": label,
            "checked": checked_value,
        }

    def _determine_role(self, class_name: str, clickable: bool, checkable: bool) -> str:
        """
        Determina el role del elemento basado en sus atributos.

        Args:
            class_name: Nombre de la clase del elemento
            clickable: Si el elemento es clickable
            checkable: Si el elemento es checkable

        Returns:
            "button", "input", o "checkbox"
        """
        if "edittext" in class_name or "input" in class_name:
            return "input"
        elif checkable:
            return "checkbox"
        elif clickable:
            return "button"
        else:
            # Fallback: si llegó aquí es porque pasó el filtro, asumir button
            return "button"

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

    def elements_to_toon(self, elements: List[Dict[str, Any]]) -> str:
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
            [{"id": 0, "role": "button", "label": "Login", "checked": null},
             {"id": 1, "role": "input", "label": "Email", "checked": null}]
            
            TOON (menos tokens):
            [2,]{id,role,label,checked}:
              0,button,Login,null
              1,input,Email,null
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

