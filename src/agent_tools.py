"""
Agent Tools - Herramientas de alto nivel para interactuar con Appium.
"""

import time
from typing import Optional
from appium.webdriver.common.appiumby import AppiumBy
from appium.webdriver import Remote

from src.ui_parser import UIParser


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
        self.driver = driver
        self.ui_parser = ui_parser
        self.default_wait_timeout = 5
        self.min_wait_timeout = 0.3

    def get_screen_tree(self) -> str:
        """
        Obtiene el XML de la pantalla actual.

        Returns:
            String con el XML completo de page_source
        """
        return self.driver.page_source

    def touch_element_by_id(self, element_id: int) -> str:
        """
        Hace clic en un elemento usando su ID del UIParser.

        Args:
            element_id: ID del elemento (asignado por UIParser)

        Returns:
            Mensaje de éxito o error
        """
        xpath = self.ui_parser.get_element_by_id(element_id)
        if not xpath:
            return f"Error: Elemento con ID {element_id} no encontrado en el mapeo"

        try:
            element = self.driver.find_element(AppiumBy.XPATH, xpath)
            element.click()
            time.sleep(self.min_wait_timeout)
            return f"Success: Clicked on element ID {element_id}"
        except Exception as e:
            return f"Error: Could not click element ID {element_id}: {str(e)}"

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
        xpath = self.ui_parser.get_element_by_id(element_id)
        if not xpath:
            return f"Error: Elemento con ID {element_id} no encontrado en el mapeo"

        try:
            element = self.driver.find_element(AppiumBy.XPATH, xpath)
            element.click()
            time.sleep(self.min_wait_timeout)
            element.clear()
            element.send_keys(value)
            self.hide_keyboard()
            return f"Success: Typed '{value}' into element ID {element_id}"
        except Exception as e:
            return f"Error: Could not fill field ID {element_id}: {str(e)}"

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
        try:
            size = self.driver.get_window_size()
            width = size["width"]
            height = size["height"]

            start_x = width // 2
            start_y = height // 2
            end_y = int(height * 0.2) if direction == "down" else int(height * 0.8)

            self.driver.swipe(start_x, start_y, start_x, end_y, duration=500)
            time.sleep(self.min_wait_timeout)
            return f"Success: Scrolled {direction}"
        except Exception as e:
            return f"Error: Could not scroll {direction}: {str(e)}"

    def go_back(self) -> str:
        """
        Presiona el botón atrás del dispositivo.

        Returns:
            Mensaje de éxito o error
        """
        try:
            self.driver.back()
            time.sleep(self.min_wait_timeout)
            return "Success: Pressed back button"
        except Exception as e:
            return f"Error: Could not press back button: {str(e)}"

    def hide_keyboard(self) -> bool:
        """
        Oculta el teclado si está visible.

        Returns:
            True si se ocultó, False si no estaba visible
        """
        try:
            if self.driver.is_keyboard_shown():
                self.driver.hide_keyboard()
                time.sleep(self.min_wait_timeout)
                return True
            return False
        except Exception:
            return False

    def assert_screen_contains(self, text: str) -> tuple[bool, str]:
        """
        Valida que la pantalla contenga un texto específico.

        Args:
            text: Texto a buscar

        Returns:
            Tupla (is_present, message)
        """
        try:
            page_source = self.driver.page_source
            if text in page_source:
                return True, f"Success: Found text '{text}' on screen"
            else:
                return False, f"Error: Text '{text}' not found on screen"
        except Exception as e:
            return False, f"Error: Could not check for text '{text}': {str(e)}"

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

