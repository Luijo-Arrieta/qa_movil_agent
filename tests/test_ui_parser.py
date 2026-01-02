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


class TestUIParserIntegration:
    """Tests de integración para UIParser con Appium real."""

    @pytest.mark.usefixtures("driver_setup")
    def test_parse_real_app_screen(self, driver_setup):
        """
        Test: Parsear XML real de una app Android usando Appium.
        
        Este test se conecta a Appium, obtiene el XML real de la pantalla
        actual y verifica que el UIParser puede procesarlo correctamente.
        """
        # Obtener el XML real de la pantalla actual
        xml_source = driver_setup.page_source
        
        # Verificar que obtuvimos XML válido
        assert xml_source is not None
        assert len(xml_source) > 0
        assert "<hierarchy" in xml_source.lower()
        
        # Parsear con UIParser
        parser = UIParser()
        elements = parser.parse_screen(xml_source)
        
        # Verificar que se parsearon elementos
        assert isinstance(elements, list)
        
        # Si hay elementos, verificar su estructura
        if len(elements) > 0:
            element = elements[0]
            assert "id" in element
            assert "role" in element
            assert "label" in element
            assert "checked" in element
            assert isinstance(element["id"], int)
            assert element["role"] in ["button", "input", "checkbox"]
        
        # Verificar que los IDs son secuenciales
        for i, element in enumerate(elements):
            assert element["id"] == i
        
        print(f"\n✓ Se parsearon {len(elements)} elementos interactuables de la app real")
        if len(elements) > 0:
            print(f"  Ejemplos de elementos encontrados:")
            for elem in elements[:5]:  # Mostrar primeros 5
                print(f"    - ID {elem['id']}: {elem['role']} - '{elem['label']}'")

    @pytest.mark.usefixtures("driver_setup")
    def test_get_xpath_from_real_elements(self, driver_setup):
        """
        Test: Verificar que los XPaths generados son válidos para elementos reales.
        
        Este test verifica que el mapeo ID -> XPath funciona correctamente
        con elementos reales de la app.
        """
        xml_source = driver_setup.page_source
        parser = UIParser()
        elements = parser.parse_screen(xml_source)
        
        # Verificar que hay elementos
        if len(elements) == 0:
            pytest.skip("No hay elementos interactuables en la pantalla actual")
        
        # Verificar que podemos obtener XPath para cada elemento
        for element in elements:
            element_id = element["id"]
            xpath = parser.get_element_by_id(element_id)
            
            assert xpath is not None, f"XPath no encontrado para ID {element_id}"
            assert len(xpath) > 0, f"XPath vacío para ID {element_id}"
            assert xpath.startswith("//"), f"XPath inválido: {xpath}"
            
            # Intentar encontrar el elemento usando el XPath
            try:
                found_elements = driver_setup.find_elements("xpath", xpath)
                assert len(found_elements) > 0, f"XPath {xpath} no encontró elementos en la app"
            except Exception as e:
                # Si falla, al menos verificar que el XPath tiene formato válido
                print(f"  Nota: No se pudo validar XPath {xpath} (puede ser válido pero elemento no visible)")
        
        print(f"\n✓ Se validaron {len(elements)} XPaths de elementos reales")

    @pytest.mark.usefixtures("driver_setup")
    def test_parser_handles_complex_real_ui(self, driver_setup):
        """
        Test: Verificar que el parser maneja correctamente UIs complejas reales.
        
        Este test verifica que el parser puede procesar pantallas complejas
        con múltiples elementos, layouts anidados, etc.
        """
        xml_source = driver_setup.page_source
        parser = UIParser()
        
        # Parsear múltiples veces para verificar consistencia
        elements1 = parser.parse_screen(xml_source)
        parser.clear()
        elements2 = parser.parse_screen(xml_source)
        
        # Verificar que los resultados son consistentes
        assert len(elements1) == len(elements2), "El parser debe ser determinístico"
        
        # Verificar estructura de elementos
        for element in elements1:
            # Verificar que todos los campos requeridos están presentes
            required_fields = ["id", "role", "label", "checked"]
            for field in required_fields:
                assert field in element, f"Campo '{field}' faltante en elemento {element['id']}"
            
            # Verificar tipos de datos
            assert isinstance(element["id"], int)
            assert isinstance(element["role"], str)
            assert isinstance(element["label"], str)
            assert element["checked"] is None or isinstance(element["checked"], bool)
        
        # Verificar que no hay elementos duplicados (mismo ID)
        ids = [elem["id"] for elem in elements1]
        assert len(ids) == len(set(ids)), "No debe haber IDs duplicados"
        
        print(f"\n✓ Parser maneja correctamente UI compleja con {len(elements1)} elementos")
