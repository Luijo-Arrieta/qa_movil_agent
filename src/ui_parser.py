"""
UIParser - Transforma XML crudo de Appium en representación JSON simplificada
para consumo eficiente por LLMs.
"""

import xml.etree.ElementTree as ET
from typing import List, Dict, Optional, Any
import re


class UIParser:
    """
    Parsea el XML de page_source de Appium y genera una lista JSON simplificada
    de elementos interactuables, asignando IDs temporales y manteniendo mapeo
    a XPath reales.
    """

    def __init__(self):
        """Inicializa el parser con mapeo vacío de elementos."""
        self.element_map: Dict[int, str] = {}  # ID -> XPath
        self.current_id = 0

    def parse_screen(self, xml_source: str) -> List[Dict[str, Any]]:
        """
        Parsea el XML y retorna lista de elementos interactuables en formato JSON.

        Args:
            xml_source: String con el XML completo de page_source

        Returns:
            Lista de diccionarios con formato: [{"id": int, "role": str, "label": str, "checked": bool|None}]
        """
        try:
            root = ET.fromstring(xml_source)
        except ET.ParseError as e:
            raise ValueError(f"Error parsing XML: {e}")

        # Reset para nuevo parseo
        self.element_map = {}
        self.current_id = 0
        elements = []

        # Recorrer árbol recursivamente
        self._traverse_tree(root, "", elements, None)

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
        # Generar XPath para este elemento
        current_path = self._generate_xpath(element, parent_element)

        # Verificar si este elemento debe incluirse
        if self._is_interactable_element(element):
            # Extraer información y agregar a la lista
            element_info = self._extract_element_info(element, self.current_id)
            if element_info:
                elements.append(element_info)
                # Guardar mapeo ID -> XPath
                self.element_map[self.current_id] = current_path
                self.current_id += 1

        # Continuar recorriendo hijos
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

        # Determinar label (prioridad: text > content-desc > resource-id > hint)
        label = text
        if not label:
            label = content_desc
        if not label:
            label = resource_id
        if not label:
            # Para inputs, intentar obtener hint
            hint = element.get("hint", "").strip()
            if hint:
                label = hint

        # Si es input, siempre incluir aunque no tenga label
        is_input = "edittext" in class_name or "input" in class_name
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
        return self.element_map.get(element_id)

    def clear(self):
        """Limpia el mapeo de elementos (útil para resetear estado)."""
        self.element_map = {}
        self.current_id = 0

