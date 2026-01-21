"""
Tests para validar la detección de tipos de elementos y captura de elementos informativos.

Estos tests usan XMLs reales de la aplicación para validar que:
1. Se capturan elementos informativos (como textos de diálogos)
2. Se detecta correctamente el tipo de cada elemento
3. Se identifican correctamente botones, inputs, iconos, etc.
"""

import pytest
from src.ui_parser import UIParser


def get_attr_value(element, attr_name, default=""):
    """Helper para obtener valor de un atributo de un UIElement."""
    for attr in element.get("attrs", []):
        if attr.get("name") == attr_name:
            return attr.get("value", default)
    return default


class TestElementTypeDetection:
    """Tests para la detección de tipos de elementos."""

    def test_dialog_success_message_captured(self):
        """
        Test: Validar que se captura el ImageView informativo del diálogo de éxito.
        
        Este XML contiene un diálogo de éxito con:
        - Un ImageView con content-desc="Contraseña restablecida con éxito\nAhora puedes iniciar sesión con tu nueva contraseña."
        - focusable="true" pero clickable="false"
        - Debe ser capturado como "image_info"
        """
        xml_dialog = """<?xml version='1.0' encoding='UTF-8' standalone='yes' ?>
<hierarchy index="0" class="hierarchy" rotation="0" width="1080" height="2400">
  <android.widget.FrameLayout index="0" package="com.imagineapps.gofixiicliente" class="android.widget.FrameLayout" text="" checkable="false" checked="false" clickable="false" enabled="true" focusable="false" focused="false" long-clickable="false" password="false" scrollable="false" selected="false" bounds="[0,0][1080,2400]" displayed="true">
    <android.widget.LinearLayout index="0" package="com.imagineapps.gofixiicliente" class="android.widget.LinearLayout" text="" checkable="false" checked="false" clickable="false" enabled="true" focusable="false" focused="false" long-clickable="false" password="false" scrollable="false" selected="false" bounds="[0,0][1080,2400]" displayed="true">
      <android.widget.FrameLayout index="0" package="com.imagineapps.gofixiicliente" class="android.widget.FrameLayout" text="" resource-id="android:id/content" checkable="false" checked="false" clickable="false" enabled="true" focusable="false" focused="false" long-clickable="false" password="false" scrollable="false" selected="false" bounds="[0,0][1080,2400]" displayed="true">
        <android.widget.FrameLayout index="0" package="com.imagineapps.gofixiicliente" class="android.widget.FrameLayout" text="" checkable="false" checked="false" clickable="false" enabled="true" focusable="true" focused="true" long-clickable="false" password="false" scrollable="false" selected="false" bounds="[0,0][1080,2400]" displayed="true">
          <android.view.View index="0" package="com.imagineapps.gofixiicliente" class="android.view.View" text="" resource-id="" checkable="false" checked="false" clickable="false" enabled="true" focusable="false" focused="false" long-clickable="false" password="false" scrollable="false" selected="false" bounds="[0,0][1080,2400]" displayed="true">
            <android.view.View index="0" package="com.imagineapps.gofixiicliente" class="android.view.View" text="" content-desc="Cerrar" resource-id="" checkable="false" checked="false" clickable="true" enabled="true" focusable="true" focused="false" long-clickable="false" password="false" scrollable="false" selected="false" bounds="[0,0][1080,2400]" displayed="true">
              <android.view.View index="0" package="com.imagineapps.gofixiicliente" class="android.view.View" text="" resource-id="" checkable="false" checked="false" clickable="false" enabled="true" focusable="false" focused="false" long-clickable="false" password="false" scrollable="false" selected="false" bounds="[0,0][1080,2400]" displayed="true">
                <android.view.View index="0" package="com.imagineapps.gofixiicliente" class="android.view.View" text="" resource-id="" checkable="false" checked="false" clickable="false" enabled="true" focusable="false" focused="false" long-clickable="false" password="false" scrollable="false" selected="false" bounds="[0,63][1080,2337]" displayed="true">
                  <android.view.View index="0" package="com.imagineapps.gofixiicliente" class="android.view.View" text="" resource-id="" checkable="false" checked="false" clickable="false" enabled="true" focusable="false" focused="false" long-clickable="false" password="false" scrollable="false" selected="false" bounds="[137,867][943,1533]" displayed="true">
                    <android.widget.ImageView index="0" package="com.imagineapps.gofixiicliente" class="android.widget.ImageView" text="" content-desc="Contraseña restablecida con éxito&#10;Ahora puedes iniciar sesión con tu nueva contraseña." resource-id="" checkable="false" checked="false" clickable="false" enabled="true" focusable="true" focused="false" long-clickable="false" password="false" scrollable="false" selected="false" bounds="[200,930][880,1481]" displayed="true" />
                  </android.view.View>
                </android.view.View>
              </android.view.View>
            </android.view.View>
          </android.view.View>
        </android.widget.FrameLayout>
      </android.widget.FrameLayout>
    </android.widget.LinearLayout>
  </android.widget.FrameLayout>
</hierarchy>"""

        parser = UIParser()
        elements = parser.parse_screen(xml_dialog, current_package="com.imagineapps.gofixiicliente")

        # Debe capturar al menos 2 elementos: el botón "Cerrar" y el ImageView informativo
        assert len(elements) >= 2, f"Se esperaban al menos 2 elementos, se encontraron {len(elements)}"

        # Buscar el ImageView con el mensaje de éxito
        image_info_found = False
        for element in elements:
            content_desc = get_attr_value(element, "content-desc")
            element_type = get_attr_value(element, "possible_element_type")
            class_name = get_attr_value(element, "class")
            
            if "ImageView" in class_name and "restablecida" in content_desc:
                image_info_found = True
                # Verificar que el tipo sea "image_info"
                assert element_type == "image_info", f"Se esperaba 'image_info', se obtuvo '{element_type}'"
                # Verificar que tiene el content-desc completo
                assert "Contraseña restablecida con éxito" in content_desc
                assert "Ahora puedes iniciar sesión" in content_desc
                break

        assert image_info_found, "No se encontró el ImageView informativo del diálogo de éxito"

        # Verificar que también se capturó el botón "Cerrar"
        cerrar_button_found = False
        for element in elements:
            content_desc = get_attr_value(element, "content-desc")
            element_type = get_attr_value(element, "possible_element_type")
            clickable = get_attr_value(element, "clickable")
            
            if content_desc == "Cerrar" and clickable == "true":
                cerrar_button_found = True
                # Verificar que el tipo sea "button" o "link"
                assert element_type in ["button", "link"], f"Se esperaba 'button' o 'link', se obtuvo '{element_type}'"
                break

        assert cerrar_button_found, "No se encontró el botón 'Cerrar'"

    def test_login_screen_elements_detected(self):
        """
        Test: Validar que se detectan correctamente todos los tipos de elementos en la pantalla de login.
        
        Este XML contiene:
        - EditText (input) para email
        - EditText (input) para password
        - ImageView clickable pequeño (icon_button) para mostrar/ocultar password
        - View clickable (button/link) para "¿Olvidaste tu contraseña?"
        - View clickable (link) para "Crear cuenta"
        - View informativo (text) para labels y descripciones
        """
        xml_login = """<?xml version='1.0' encoding='UTF-8' standalone='yes' ?>
<hierarchy index="0" class="hierarchy" rotation="0" width="1080" height="2400">
  <android.widget.FrameLayout index="0" package="com.imagineapps.gofixiicliente" class="android.widget.FrameLayout" text="" checkable="false" checked="false" clickable="false" enabled="true" focusable="false" focused="false" long-clickable="false" password="false" scrollable="false" selected="false" bounds="[0,0][1080,2400]" displayed="true">
    <android.widget.LinearLayout index="0" package="com.imagineapps.gofixiicliente" class="android.widget.LinearLayout" text="" checkable="false" checked="false" clickable="false" enabled="true" focusable="false" focused="false" long-clickable="false" password="false" scrollable="false" selected="false" bounds="[0,0][1080,2400]" displayed="true">
      <android.widget.FrameLayout index="0" package="com.imagineapps.gofixiicliente" class="android.widget.FrameLayout" text="" resource-id="android:id/content" checkable="false" checked="false" clickable="false" enabled="true" focusable="false" focused="false" long-clickable="false" password="false" scrollable="false" selected="false" bounds="[0,0][1080,2400]" displayed="true">
        <android.widget.FrameLayout index="0" package="com.imagineapps.gofixiicliente" class="android.widget.FrameLayout" text="" checkable="false" checked="false" clickable="false" enabled="true" focusable="true" focused="true" long-clickable="false" password="false" scrollable="false" selected="false" bounds="[0,0][1080,2400]" displayed="true">
          <android.view.View index="0" package="com.imagineapps.gofixiicliente" class="android.view.View" text="" resource-id="" checkable="false" checked="false" clickable="false" enabled="true" focusable="false" focused="false" long-clickable="false" password="false" scrollable="false" selected="false" bounds="[0,0][1080,2400]" displayed="true">
            <android.view.View index="0" package="com.imagineapps.gofixiicliente" class="android.view.View" text="" resource-id="" checkable="false" checked="false" clickable="false" enabled="true" focusable="false" focused="false" long-clickable="false" password="false" scrollable="false" selected="false" bounds="[0,0][1080,2400]" displayed="true">
              <android.view.View index="0" package="com.imagineapps.gofixiicliente" class="android.view.View" text="" resource-id="" checkable="false" checked="false" clickable="false" enabled="true" focusable="false" focused="false" long-clickable="false" password="false" scrollable="false" selected="false" bounds="[0,0][1080,2400]" displayed="true">
                <android.view.View index="0" package="com.imagineapps.gofixiicliente" class="android.view.View" text="" content-desc="Iniciar sesión" resource-id="" checkable="false" checked="false" clickable="true" enabled="true" focusable="true" focused="false" long-clickable="false" password="false" scrollable="false" selected="false" bounds="[0,0][1080,2400]" displayed="true">
                  <android.view.View index="0" package="com.imagineapps.gofixiicliente" class="android.view.View" text="" resource-id="" checkable="false" checked="false" clickable="false" enabled="true" focusable="false" focused="false" long-clickable="false" password="false" scrollable="false" selected="false" bounds="[0,0][1080,210]" displayed="true" />
                  <android.view.View index="1" package="com.imagineapps.gofixiicliente" class="android.view.View" text="" resource-id="" checkable="false" checked="false" clickable="false" enabled="true" focusable="false" focused="false" long-clickable="false" password="false" scrollable="false" selected="false" bounds="[0,210][1080,1457]" displayed="true">
                    <android.widget.ImageView index="0" package="com.imagineapps.gofixiicliente" class="android.widget.ImageView" text="" resource-id="" checkable="false" checked="false" clickable="false" enabled="true" focusable="false" focused="false" long-clickable="false" password="false" scrollable="false" selected="false" bounds="[53,210][373,318]" displayed="true" />
                    <android.view.View index="1" package="com.imagineapps.gofixiicliente" class="android.view.View" text="" content-desc="Inicia sesión" resource-id="" checkable="false" checked="false" clickable="false" enabled="true" focusable="true" focused="false" long-clickable="false" password="false" scrollable="false" selected="false" bounds="[53,402][346,473]" displayed="true" />
                    <android.view.View index="2" package="com.imagineapps.gofixiicliente" class="android.view.View" text="" content-desc="Ingresa a tu cuenta y gestiona tus servicios, agendamientos o cotizaciones de forma fácil y rápida." resource-id="" checkable="false" checked="false" clickable="false" enabled="true" focusable="true" focused="false" long-clickable="false" password="false" scrollable="false" selected="false" bounds="[53,483][1028,672]" displayed="true" />
                    <android.view.View index="3" package="com.imagineapps.gofixiicliente" class="android.view.View" text="" content-desc="Correo electrónico" resource-id="" checkable="false" checked="false" clickable="false" enabled="true" focusable="true" focused="false" long-clickable="false" password="false" scrollable="false" selected="false" bounds="[53,756][418,819]" displayed="true" />
                    <android.widget.EditText index="4" package="com.imagineapps.gofixiicliente" class="android.widget.EditText" text="" resource-id="" checkable="false" checked="false" clickable="true" enabled="true" focusable="true" focused="false" long-clickable="false" password="false" scrollable="false" selected="false" bounds="[53,824][1028,950]" displayed="true" hint="Ejemplo@mail.com" />
                    <android.view.View index="5" package="com.imagineapps.gofixiicliente" class="android.view.View" text="" content-desc="Contraseña" resource-id="" checkable="false" checked="false" clickable="false" enabled="true" focusable="true" focused="false" long-clickable="false" password="false" scrollable="false" selected="false" bounds="[53,1034][280,1097]" displayed="true" />
                    <android.view.View index="6" package="com.imagineapps.gofixiicliente" class="android.view.View" text="" content-desc="**********" resource-id="" checkable="false" checked="false" clickable="true" enabled="true" focusable="true" focused="false" long-clickable="false" password="false" scrollable="false" selected="false" bounds="[53,1103][1028,1229]" displayed="true">
                      <android.widget.EditText index="0" package="com.imagineapps.gofixiicliente" class="android.widget.EditText" text="" resource-id="" checkable="false" checked="false" clickable="false" enabled="true" focusable="true" focused="false" long-clickable="false" password="true" scrollable="false" selected="false" bounds="[84,1134][891,1197]" displayed="true" />
                      <android.widget.ImageView index="1" package="com.imagineapps.gofixiicliente" class="android.widget.ImageView" text="" resource-id="" checkable="false" checked="false" clickable="true" enabled="true" focusable="true" focused="false" long-clickable="false" password="false" scrollable="false" selected="false" bounds="[901,1103][1028,1229]" displayed="true" />
                    </android.view.View>
                    <android.view.View index="7" package="com.imagineapps.gofixiicliente" class="android.view.View" text="" content-desc="¿Olvidaste tu contraseña?" resource-id="" checkable="false" checked="false" clickable="true" enabled="true" focusable="true" focused="false" long-clickable="false" password="false" scrollable="false" selected="false" bounds="[53,1313][574,1373]" displayed="true" />
                  </android.view.View>
                  <android.view.View index="2" package="com.imagineapps.gofixiicliente" class="android.view.View" text="" resource-id="" checkable="false" checked="false" clickable="false" enabled="true" focusable="false" focused="false" long-clickable="false" password="false" scrollable="false" selected="false" bounds="[171,2232][909,2295]" displayed="true">
                    <android.view.View index="0" package="com.imagineapps.gofixiicliente" class="android.view.View" text="" content-desc="¿No tienes una cuenta? " resource-id="" checkable="false" checked="false" clickable="false" enabled="true" focusable="true" focused="false" long-clickable="false" password="false" scrollable="false" selected="false" bounds="[160,2224][657,2303]" displayed="true" />
                    <android.view.View index="1" package="com.imagineapps.gofixiicliente" class="android.view.View" text="" content-desc="Crear cuenta" resource-id="" checkable="false" checked="false" clickable="true" enabled="true" focusable="true" focused="false" long-clickable="false" password="false" scrollable="false" selected="false" bounds="[633,2224][922,2303]" displayed="true" />
                  </android.view.View>
                </android.view.View>
              </android.view.View>
            </android.view.View>
          </android.view.View>
        </android.widget.FrameLayout>
      </android.widget.FrameLayout>
    </android.widget.LinearLayout>
  </android.widget.FrameLayout>
</hierarchy>"""

        parser = UIParser()
        elements = parser.parse_screen(xml_login, current_package="com.imagineapps.gofixiicliente")

        # Verificar que se capturaron múltiples elementos
        assert len(elements) > 5, f"Se esperaban más de 5 elementos, se encontraron {len(elements)}"

        # Verificar tipos específicos
        element_types = {}
        for element in elements:
            element_type = get_attr_value(element, "possible_element_type")
            class_name = get_attr_value(element, "class")
            content_desc = get_attr_value(element, "content-desc")
            clickable = get_attr_value(element, "clickable")
            
            # Contar tipos
            element_types[element_type] = element_types.get(element_type, 0) + 1

        # Debe haber al menos 2 inputs (email y password)
        assert element_types.get("input", 0) >= 2, f"Se esperaban al menos 2 inputs, se encontraron {element_types.get('input', 0)}"

        # Debe haber al menos 1 icon_button (el ojo de password)
        assert element_types.get("icon_button", 0) >= 1, f"Se esperaba al menos 1 icon_button, se encontraron {element_types.get('icon_button', 0)}"

        # Debe haber elementos de tipo "text" (labels informativos)
        assert element_types.get("text", 0) >= 1, f"Se esperaba al menos 1 elemento de tipo 'text', se encontraron {element_types.get('text', 0)}"

        # Debe haber elementos clickables (botones/links)
        clickable_count = element_types.get("button", 0) + element_types.get("link", 0)
        assert clickable_count >= 2, f"Se esperaban al menos 2 elementos clickables, se encontraron {clickable_count}"

        # Verificar específicamente el icono de password (ImageView clickable pequeño)
        password_icon_found = False
        for element in elements:
            class_name = get_attr_value(element, "class")
            clickable = get_attr_value(element, "clickable")
            element_type = get_attr_value(element, "possible_element_type")
            bounds = get_attr_value(element, "bounds")
            
            if "ImageView" in class_name and clickable == "true":
                # Calcular tamaño
                import re
                match = re.match(r'\[(\d+),(\d+)\]\[(\d+),(\d+)\]', bounds)
                if match:
                    x1, y1, x2, y2 = map(int, match.groups())
                    width = x2 - x1
                    height = y2 - y1
                    if width < 200 and height < 200:  # Es pequeño
                        password_icon_found = True
                        assert element_type == "icon_button", f"Se esperaba 'icon_button' para el icono de password, se obtuvo '{element_type}'"
                        break

        assert password_icon_found, "No se encontró el icono de password (ImageView clickable pequeño)"

        # Verificar que se capturó el link "¿Olvidaste tu contraseña?"
        forgot_password_found = False
        for element in elements:
            content_desc = get_attr_value(element, "content-desc")
            element_type = get_attr_value(element, "possible_element_type")
            
            if "Olvidaste" in content_desc:
                forgot_password_found = True
                assert element_type in ["link", "button"], f"Se esperaba 'link' o 'button' para '¿Olvidaste tu contraseña?', se obtuvo '{element_type}'"
                break

        assert forgot_password_found, "No se encontró el link '¿Olvidaste tu contraseña?'"
