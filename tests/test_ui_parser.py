"""
Tests unitarios para UIParser.
"""

import pytest
from src.ui_parser import UIParser


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
        assert elements[0]["label"] == "Ingresar"
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
        assert elements[0]["label"] == "Recordar sesión"
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
        assert "login_button" in xpath or "Ingresar" in xpath

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

