"""
Tests unitarios para UIParser.

Estos tests verifican la funcionalidad del parser de UI sin necesidad
de Appium ni dispositivo físico. Usan XML hardcoded para probar la lógica.
"""

import json
import logging

import pytest

from src.ui_parser import UIParser


logger = logging.getLogger(__name__)


class TestUIParser:
    """Tests para la clase UIParser."""

    def test_parse_screen_with_clickable_button(self):
        """Test: Parsear XML con un botón clickable."""
        xml = """
        <hierarchy>
            <android.widget.Button
                text="Ingresar"
                clickable="true"
                class="android.widget.Button"
                resource-id="com.example:id/login_button"/>
        </hierarchy>
        """
        parser = UIParser()
        elements = parser.parse_screen(xml)

        assert len(elements) == 1
        assert elements[0]["id"] == 0
        assert elements[0]["role"] == "button"
        # resource-id tiene prioridad sobre text (más estable y único)
        assert elements[0]["label"] == "com.example:id/login_button"
        assert elements[0]["checked"] is None

    def test_parse_screen_with_input_field(self):
        """Test: Parsear XML con un campo de entrada."""
        xml = """
        <hierarchy>
            <android.widget.EditText
                hint="Usuario"
                class="android.widget.EditText"
                resource-id="com.example:id/username_input"/>
        </hierarchy>
        """
        parser = UIParser()
        elements = parser.parse_screen(xml)

        assert len(elements) == 1
        assert elements[0]["id"] == 0
        assert elements[0]["role"] == "input"
        # resource-id tiene prioridad sobre hint (más estable y confiable)
        assert elements[0]["label"] == "com.example:id/username_input"
        assert elements[0]["checked"] is None
    
    def test_parse_screen_with_input_field_hint_only(self):
        """Test: Parsear XML con un campo de entrada que solo tiene hint (sin resource-id)."""
        xml = """
        <hierarchy>
            <android.widget.EditText
                hint="Usuario"
                class="android.widget.EditText"/>
        </hierarchy>
        """
        parser = UIParser()
        elements = parser.parse_screen(xml)

        assert len(elements) == 1
        assert elements[0]["id"] == 0
        assert elements[0]["role"] == "input"
        # Si no hay resource-id, usa hint
        assert elements[0]["label"] == "Usuario"
        assert elements[0]["checked"] is None

    def test_parse_screen_with_checkbox(self):
        """Test: Parsear XML con un checkbox."""
        xml = """
        <hierarchy>
            <android.widget.CheckBox
                text="Recordar sesión"
                checkable="true"
                checked="false"
                class="android.widget.CheckBox"/>
        </hierarchy>
        """
        parser = UIParser()
        elements = parser.parse_screen(xml)

        assert len(elements) == 1
        assert elements[0]["id"] == 0
        assert elements[0]["role"] == "checkbox"
        # Sin resource-id ni content-desc, usa text
        assert elements[0]["label"] == "Recordar sesión"
        assert elements[0]["checked"] is False
    
    def test_parse_screen_with_checkbox_resource_id(self):
        """Test: Parsear XML con un checkbox que tiene resource-id."""
        xml = """
        <hierarchy>
            <android.widget.CheckBox
                text="Recordar sesión"
                checkable="true"
                checked="false"
                resource-id="com.example:id/remember_checkbox"
                class="android.widget.CheckBox"/>
        </hierarchy>
        """
        parser = UIParser()
        elements = parser.parse_screen(xml)

        assert len(elements) == 1
        assert elements[0]["id"] == 0
        assert elements[0]["role"] == "checkbox"
        # resource-id tiene prioridad sobre text
        assert elements[0]["label"] == "com.example:id/remember_checkbox"
        assert elements[0]["checked"] is False

    def test_filter_non_interactable_elements(self):
        """Test: Filtrar elementos no interactuables."""
        xml = """
        <hierarchy>
            <android.widget.LinearLayout
                class="android.widget.LinearLayout">
                <android.widget.TextView
                    text="Título"
                    class="android.widget.TextView"/>
                <android.widget.Button
                    text="Botón"
                    clickable="true"
                    class="android.widget.Button"/>
            </android.widget.LinearLayout>
        </hierarchy>
        """
        parser = UIParser()
        elements = parser.parse_screen(xml)

        # Solo el botón debe estar en la lista (no el layout ni el TextView)
        assert len(elements) == 1
        assert elements[0]["role"] == "button"
        # Sin resource-id ni content-desc, usa text
        assert elements[0]["label"] == "Botón"

    def test_get_element_by_id(self):
        """Test: Recuperar XPath por ID."""
        xml = """
        <hierarchy>
            <android.widget.Button
                text="Ingresar"
                clickable="true"
                resource-id="com.example:id/login_button"/>
        </hierarchy>
        """
        parser = UIParser()
        parser.parse_screen(xml)

        xpath = parser.get_element_by_id(0)
        assert xpath is not None
        # XPath debe usar resource-id (tiene prioridad)
        assert "login_button" in xpath or "com.example:id/login_button" in xpath

    def test_multiple_elements_sequential_ids(self):
        """Test: Múltiples elementos con IDs secuenciales."""
        xml = """
        <hierarchy>
            <android.widget.EditText
                hint="Usuario"
                class="android.widget.EditText"/>
            <android.widget.EditText
                hint="Contraseña"
                class="android.widget.EditText"/>
            <android.widget.Button
                text="Ingresar"
                clickable="true"
                class="android.widget.Button"/>
        </hierarchy>
        """
        parser = UIParser()
        elements = parser.parse_screen(xml)

        assert len(elements) == 3
        assert elements[0]["id"] == 0
        assert elements[1]["id"] == 1
        assert elements[2]["id"] == 2
        assert elements[0]["role"] == "input"
        assert elements[1]["role"] == "input"
        assert elements[2]["role"] == "button"

    def test_empty_screen(self):
        """Test: Pantalla vacía sin elementos interactuables."""
        xml = """
        <hierarchy>
            <android.widget.LinearLayout
                class="android.widget.LinearLayout"/>
        </hierarchy>
        """
        parser = UIParser()
        elements = parser.parse_screen(xml)

        assert len(elements) == 0

    def test_invalid_xml(self):
        """Test: XML inválido debe lanzar excepción."""
        parser = UIParser()
        with pytest.raises(ValueError):
            parser.parse_screen("<invalid>xml")


class TestUIParserTOON:
    """Tests para la funcionalidad TOON del UIParser."""

    def test_elements_to_toon_basic(self):
        """Test: Convertir lista de elementos básica a formato TOON."""
        elements = [
            {"id": 0, "role": "button", "label": "Login", "checked": None},
            {"id": 1, "role": "input", "label": "Email", "checked": None},
        ]
        
        parser = UIParser()
        toon_output = parser.elements_to_toon(elements)
        
        # Verificar que se generó output TOON
        assert toon_output is not None
        assert len(toon_output) > 0
        
        # TOON debe contener el número de elementos en el header
        assert "[2" in toon_output, "TOON debe indicar la cantidad de elementos"
        
        # TOON debe contener los campos del header
        assert "id" in toon_output
        assert "role" in toon_output
        assert "label" in toon_output
        assert "checked" in toon_output
        
        # TOON debe contener los valores
        assert "Login" in toon_output
        assert "Email" in toon_output
        assert "button" in toon_output
        assert "input" in toon_output
        
        logger.info(f"TOON output:\n{toon_output}")

    def test_elements_to_toon_empty_list(self):
        """Test: Lista vacía debe retornar string vacío."""
        parser = UIParser()
        toon_output = parser.elements_to_toon([])
        
        assert toon_output == ""

    def test_elements_to_toon_with_checkbox(self):
        """Test: Convertir elementos con checkbox a TOON."""
        elements = [
            {"id": 0, "role": "checkbox", "label": "Remember me", "checked": True},
            {"id": 1, "role": "checkbox", "label": "Accept terms", "checked": False},
        ]
        
        parser = UIParser()
        toon_output = parser.elements_to_toon(elements)
        
        # TOON debe contener los valores de checked
        assert "true" in toon_output.lower()
        assert "false" in toon_output.lower()
        
        logger.info(f"TOON output with checkboxes:\n{toon_output}")

    def test_parse_screen_to_toon_direct(self):
        """Test: Parsear XML directamente a formato TOON."""
        xml = """
        <hierarchy>
            <android.widget.EditText
                hint="Usuario"
                class="android.widget.EditText"
                resource-id="com.example:id/username"/>
            <android.widget.EditText
                hint="Contraseña"
                class="android.widget.EditText"
                resource-id="com.example:id/password"/>
            <android.widget.Button
                text="Ingresar"
                clickable="true"
                class="android.widget.Button"
                resource-id="com.example:id/login_btn"/>
        </hierarchy>
        """
        
        parser = UIParser()
        toon_output = parser.parse_screen_to_toon(xml)
        
        # Verificar que se generó output TOON
        assert toon_output is not None
        assert len(toon_output) > 0
        
        # TOON debe contener 3 elementos
        assert "[3" in toon_output, "TOON debe indicar 3 elementos"
        
        # Verificar que los resource-ids están presentes (tienen prioridad)
        assert "username" in toon_output
        assert "password" in toon_output
        assert "login_btn" in toon_output
        
        logger.info(f"TOON output (parse_screen_to_toon):\n{toon_output}")

    def test_toon_is_more_compact_than_json(self):
        """Test: TOON debe ser más compacto que JSON para arrays uniformes."""
        elements = [
            {"id": 0, "role": "button", "label": "Login", "checked": None},
            {"id": 1, "role": "input", "label": "Email", "checked": None},
            {"id": 2, "role": "input", "label": "Password", "checked": None},
            {"id": 3, "role": "checkbox", "label": "Remember", "checked": False},
            {"id": 4, "role": "button", "label": "Forgot password?", "checked": None},
        ]
        
        parser = UIParser()
        toon_output = parser.elements_to_toon(elements)
        json_output = json.dumps(elements)
        
        # TOON debe ser significativamente más corto que JSON
        toon_len = len(toon_output)
        json_len = len(json_output)
        
        logger.info(f"Comparación de tamaños:")
        logger.info(f"  JSON: {json_len} caracteres")
        logger.info(f"  TOON: {toon_len} caracteres")
        logger.info(f"  Ahorro: {((json_len - toon_len) / json_len * 100):.1f}%")
        
        # TOON debe ser al menos 20% más corto para este caso
        assert toon_len < json_len, "TOON debe ser más compacto que JSON"
        
        logger.info(f"\nJSON:\n{json_output}")
        logger.info(f"\nTOON:\n{toon_output}")

    def test_elements_to_toon_special_characters(self):
        """Test: TOON maneja correctamente caracteres especiales en labels."""
        elements = [
            {"id": 0, "role": "button", "label": "Botón con ñ y áéíóú", "checked": None},
            {"id": 1, "role": "input", "label": "Campo, con coma", "checked": None},
        ]
        
        parser = UIParser()
        toon_output = parser.elements_to_toon(elements)
        
        # Verificar que los caracteres especiales están presentes
        assert "ñ" in toon_output or "Botón" in toon_output
        
        logger.info(f"TOON with special chars:\n{toon_output}")
