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


def get_attr_value(element, attr_name, default=""):
    """Helper para obtener valor de un atributo de un UIElement."""
    for attr in element.get("attrs", []):
        if attr.get("name") == attr_name:
            return attr.get("value", default)
    return default


class TestUIParser:
    """Tests para la clase UIParser."""

    def test_parse_screen_with_clickable_button(self):
        """Test: Parsear XML con un botón clickable y focusable."""
        xml = """
        <hierarchy>
            <android.widget.Button
                text="Ingresar"
                clickable="true"
                focusable="true"
                enabled="true"
                displayed="true"
                class="android.widget.Button"
                resource-id="com.example:id/login_button"/>
        </hierarchy>
        """
        parser = UIParser()
        elements = parser.parse_screen(xml)

        assert len(elements) == 1
        assert elements[0]["id"] == 0
        
        # Verificar estructura de attrs
        assert "attrs" in elements[0]
        assert isinstance(elements[0]["attrs"], list)
        
        # Verificar atributos específicos
        assert get_attr_value(elements[0], "resource-id") == "com.example:id/login_button"
        assert get_attr_value(elements[0], "text") == "Ingresar"
        assert get_attr_value(elements[0], "class") == "android.widget.Button"
        assert get_attr_value(elements[0], "clickable") == "true"

    def test_parse_screen_with_input_field(self):
        """Test: Parsear XML con un campo de entrada (EditText siempre se incluye si es focusable)."""
        xml = """
        <hierarchy>
            <android.widget.EditText
                hint="Usuario"
                focusable="true"
                enabled="true"
                displayed="true"
                class="android.widget.EditText"
                resource-id="com.example:id/username_input"/>
        </hierarchy>
        """
        parser = UIParser()
        elements = parser.parse_screen(xml)

        assert len(elements) == 1
        assert elements[0]["id"] == 0
        
        # Verificar atributos
        assert get_attr_value(elements[0], "resource-id") == "com.example:id/username_input"
        assert get_attr_value(elements[0], "hint") == "Usuario"
        assert get_attr_value(elements[0], "class") == "android.widget.EditText"
    
    def test_parse_screen_with_input_field_hint_only(self):
        """Test: Parsear XML con un campo de entrada que solo tiene hint (sin resource-id)."""
        xml = """
        <hierarchy>
            <android.widget.EditText
                hint="Usuario"
                focusable="true"
                enabled="true"
                displayed="true"
                class="android.widget.EditText"/>
        </hierarchy>
        """
        parser = UIParser()
        elements = parser.parse_screen(xml)

        assert len(elements) == 1
        assert elements[0]["id"] == 0
        
        # Sin resource-id, solo debe tener hint
        assert get_attr_value(elements[0], "resource-id") == ""
        assert get_attr_value(elements[0], "hint") == "Usuario"

    def test_filter_non_focusable_elements(self):
        """Test: Filtrar elementos no focusables."""
        xml = """
        <hierarchy>
            <android.widget.LinearLayout
                class="android.widget.LinearLayout">
                <android.widget.TextView
                    text="Título"
                    class="android.widget.TextView"
                    focusable="false"/>
                <android.widget.Button
                    text="Botón"
                    clickable="true"
                    focusable="true"
                    enabled="true"
                    displayed="true"
                    class="android.widget.Button"/>
            </android.widget.LinearLayout>
        </hierarchy>
        """
        parser = UIParser()
        elements = parser.parse_screen(xml)

        # Solo el botón debe estar en la lista (focusable=true)
        assert len(elements) == 1
        assert get_attr_value(elements[0], "class") == "android.widget.Button"
        assert get_attr_value(elements[0], "text") == "Botón"

    def test_get_element_by_id(self):
        """Test: Recuperar XPath por ID."""
        xml = """
        <hierarchy>
            <android.widget.Button
                text="Ingresar"
                clickable="true"
                focusable="true"
                enabled="true"
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
                focusable="true"
                enabled="true"
                class="android.widget.EditText"/>
            <android.widget.EditText
                hint="Contraseña"
                focusable="true"
                enabled="true"
                class="android.widget.EditText"/>
            <android.widget.Button
                text="Ingresar"
                clickable="true"
                focusable="true"
                enabled="true"
                class="android.widget.Button"/>
        </hierarchy>
        """
        parser = UIParser()
        elements = parser.parse_screen(xml)

        assert len(elements) == 3
        assert elements[0]["id"] == 0
        assert elements[1]["id"] == 1
        assert elements[2]["id"] == 2
        
        # Verificar clases
        assert "EditText" in get_attr_value(elements[0], "class")
        assert "EditText" in get_attr_value(elements[1], "class")
        assert "Button" in get_attr_value(elements[2], "class")

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

    def test_element_structure_has_id_and_attrs(self):
        """Test: Cada elemento debe tener 'id' y 'attrs'."""
        xml = """
        <hierarchy>
            <android.widget.Button
                text="Click me"
                content-desc="Test button"
                clickable="true"
                focusable="true"
                enabled="true"
                displayed="true"
                class="android.widget.Button"
                resource-id="com.example:id/test_btn"
                bounds="[0,0][100,50]"/>
        </hierarchy>
        """
        parser = UIParser()
        elements = parser.parse_screen(xml)

        assert len(elements) == 1
        element = elements[0]
        
        # Verificar estructura básica
        assert "id" in element
        assert "attrs" in element
        assert isinstance(element["id"], int)
        assert isinstance(element["attrs"], list)
        
        # Verificar estructura de cada attr
        for attr in element["attrs"]:
            assert "name" in attr
            assert "value" in attr
            assert isinstance(attr["name"], str)
            assert isinstance(attr["value"], str)

    def test_attrs_only_include_non_empty_values(self):
        """Test: Solo se incluyen atributos con valor no vacío (excepto booleanos)."""
        xml = """
        <hierarchy>
            <android.widget.Button
                text=""
                content-desc="Accessible button"
                clickable="true"
                focusable="true"
                enabled="true"
                displayed="true"
                class="android.widget.Button"
                resource-id=""
                bounds="[0,0][100,50]"/>
        </hierarchy>
        """
        parser = UIParser()
        elements = parser.parse_screen(xml)

        assert len(elements) == 1
        element = elements[0]
        
        # resource-id y text están vacíos, no deben aparecer
        attr_names = [attr["name"] for attr in element["attrs"]]
        assert "resource-id" not in attr_names  # vacío
        assert "text" not in attr_names  # vacío
        
        # content-desc tiene valor, debe aparecer
        assert "content-desc" in attr_names
        assert get_attr_value(element, "content-desc") == "Accessible button"
        
        # Booleanos siempre aparecen
        assert "clickable" in attr_names
        assert "enabled" in attr_names
        assert "displayed" in attr_names

    def test_is_editable_element(self):
        """Test: Verificar si un elemento es editable."""
        xml = """
        <hierarchy>
            <android.widget.EditText
                hint="Email"
                focusable="true"
                class="android.widget.EditText"/>
            <android.widget.Button
                text="Submit"
                clickable="true"
                focusable="true"
                class="android.widget.Button"/>
        </hierarchy>
        """
        parser = UIParser()
        parser.parse_screen(xml)

        # EditText es editable
        assert parser.is_editable_element(0) is True
        # Button no es editable
        assert parser.is_editable_element(1) is False
        # ID inexistente
        assert parser.is_editable_element(99) is False


class TestUIParserAttrStructure:
    """Tests específicos para la estructura de atributos {name, value}."""

    def test_attr_structure_consistency(self):
        """Test: La estructura de attrs siempre es [{name, value}]."""
        xml = """
        <hierarchy>
            <android.widget.EditText
                hint="Usuario"
                text="test@email.com"
                focusable="true"
                enabled="true"
                displayed="true"
                class="android.widget.EditText"
                resource-id="com.example:id/email"
                bounds="[0,100][720,200]"/>
        </hierarchy>
        """
        parser = UIParser()
        elements = parser.parse_screen(xml)

        element = elements[0]
        
        # Cada atributo debe tener exactamente 'name' y 'value'
        for attr in element["attrs"]:
            assert set(attr.keys()) == {"name", "value"}, \
                f"Attr debe tener solo 'name' y 'value', tiene: {attr.keys()}"

    def test_json_serializable(self):
        """Test: Los elementos deben ser serializables a JSON."""
        xml = """
        <hierarchy>
            <android.widget.Button
                text="Botón con ñ y áéíóú"
                content-desc="Descripción"
                clickable="true"
                focusable="true"
                enabled="true"
                class="android.widget.Button"/>
        </hierarchy>
        """
        parser = UIParser()
        elements = parser.parse_screen(xml)

        # Debe poder serializar a JSON sin errores
        json_str = json.dumps(elements, ensure_ascii=False)
        assert "Botón con ñ y áéíóú" in json_str
        
        # Debe poder deserializar de vuelta
        parsed = json.loads(json_str)
        assert len(parsed) == 1
        assert parsed[0]["id"] == 0

    def test_element_with_all_locators(self):
        """Test: Elemento con todos los atributos de localización."""
        xml = """
        <hierarchy>
            <android.widget.Button
                resource-id="com.example:id/btn"
                content-desc="Login button"
                text="Login"
                clickable="true"
                focusable="true"
                enabled="true"
                displayed="true"
                class="android.widget.Button"
                bounds="[0,0][100,50]"/>
        </hierarchy>
        """
        parser = UIParser()
        elements = parser.parse_screen(xml)

        element = elements[0]
        
        # Verificar que todos los locators están presentes
        assert get_attr_value(element, "resource-id") == "com.example:id/btn"
        assert get_attr_value(element, "content-desc") == "Login button"
        assert get_attr_value(element, "text") == "Login"
        assert get_attr_value(element, "xpath") != ""  # Siempre debe tener xpath


class TestUIParserHelperMethods:
    """Tests para métodos helper del UIParser."""

    def test_get_attr_value_helper(self):
        """Test: El método _get_attr_value funciona correctamente."""
        xml = """
        <hierarchy>
            <android.widget.Button
                text="Test"
                clickable="true"
                focusable="true"
                class="android.widget.Button"/>
        </hierarchy>
        """
        parser = UIParser()
        elements = parser.parse_screen(xml)
        element = elements[0]

        # Usar el método helper interno
        assert parser._get_attr_value(element, "text") == "Test"
        assert parser._get_attr_value(element, "class") == "android.widget.Button"
        assert parser._get_attr_value(element, "nonexistent") == ""
        assert parser._get_attr_value(element, "nonexistent", "default") == "default"

    def test_clear_resets_state(self):
        """Test: clear() resetea el estado del parser."""
        xml = """
        <hierarchy>
            <android.widget.Button
                text="Test"
                clickable="true"
                focusable="true"
                class="android.widget.Button"/>
        </hierarchy>
        """
        parser = UIParser()
        parser.parse_screen(xml)
        
        assert len(parser.element_map) == 1
        assert parser.current_id == 1
        
        parser.clear()
        
        assert len(parser.element_map) == 0
        assert parser.current_id == 0
