"""
Test para inspeccionar el comportamiento del UI Parser con XMLs reales.

Este test permite:
1. Pegar XMLs reales en las variables XML_DIALOG y XML_LOGIN
2. Ver el JSON interno generado
3. Ver el TOON que ve el agente
4. Ver información detallada de cada elemento

Uso:
    poetry run pytest tests/unit/test_ui_parser_inspect.py -v -s
"""

import json
import pytest
from src.ui_parser import UIParser
from toon_format import encode as toon_encode


def get_attr_value(element, attr_name, default=""):
    """Helper para obtener valor de un atributo."""
    for attr in element.get("attrs", []):
        if attr.get("name") == attr_name:
            return attr.get("value", default)
    return default


# ============================================================================
# PEGA AQUÍ TUS XMLs
# ============================================================================

XML_DIALOG = """<?xml version='1.0' encoding='UTF-8' standalone='yes' ?>
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

XML_LOGIN = """<?xml version='1.0' encoding='UTF-8' standalone='yes' ?>
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


class TestUIParserInspect:
    """Tests para inspeccionar el comportamiento del UI Parser."""

    def test_inspect_dialog_xml(self):
        """
        Inspecciona el parseo del XML del diálogo de éxito.
        
        Muestra:
        - Elementos encontrados
        - JSON interno
        - TOON que ve el agente
        - Información detallada de cada elemento
        """
        if not XML_DIALOG.strip() or XML_DIALOG.strip().startswith("#"):
            pytest.skip("XML_DIALOG no está configurado. Pega el XML en la variable XML_DIALOG.")
        
        parser = UIParser()
        elements = parser.parse_screen(XML_DIALOG, current_package="com.imagineapps.gofixiicliente")
        
        print("\n" + "█" * 80)
        print("  INSPECCIÓN: Diálogo de éxito (Password Recovery)")
        print("█" * 80)
        print(f"\n✓ Elementos encontrados: {len(elements)}")
        
        # Información detallada
        print("\n" + "=" * 80)
        print("  ELEMENTOS DETALLADOS")
        print("=" * 80)
        for i, element in enumerate(elements):
            print(f"\n[{i}] Elemento ID: {element['id']}")
            print("-" * 80)
            
            class_name = get_attr_value(element, "class")
            content_desc = get_attr_value(element, "content-desc")
            text = get_attr_value(element, "text")
            element_type = get_attr_value(element, "possible_element_type")
            xpath = get_attr_value(element, "xpath")
            clickable = get_attr_value(element, "clickable")
            bounds = get_attr_value(element, "bounds")
            
            print(f"  Tipo detectado: {element_type}")
            print(f"  Clase: {class_name}")
            if content_desc:
                print(f"  Content-desc: {content_desc[:100] + '...' if len(content_desc) > 100 else content_desc}")
            if text:
                print(f"  Text: {text}")
            print(f"  Clickable: {clickable}")
            if bounds:
                print(f"  Bounds: {bounds}")
            print(f"  XPath: {xpath[:80] + '...' if len(xpath) > 80 else xpath}")
            
            print(f"  Todos los atributos ({len(element['attrs'])}):")
            for attr in element['attrs']:
                attr_name = attr.get('name', '')
                attr_value = attr.get('value', '')
                if len(attr_value) > 60:
                    attr_value = attr_value[:57] + "..."
                print(f"    - {attr_name}: {attr_value}")
        
        # JSON interno
        print("\n" + "=" * 80)
        print("  JSON INTERNO (estructura completa)")
        print("=" * 80)
        print(json.dumps(elements, indent=2, ensure_ascii=False))
        
        # TOON (lo que ve el agente)
        print("\n" + "=" * 80)
        print("  TOON - Lo que ve el agente (después del filtrado)")
        print("=" * 80)
        
        # Filtrar propiedades como lo hace el AI Orchestrator
        filtered_elements = []
        properties_to_remove = {"bounds", "clickable", "enabled", "displayed"}
        
        for element in elements:
            filtered_element = element.copy()
            if "attrs" in filtered_element:
                filtered_element["attrs"] = [
                    attr for attr in filtered_element["attrs"]
                    if attr.get("name") not in properties_to_remove
                ]
            filtered_elements.append(filtered_element)
        
        # Convertir a TOON
        toon_elements = toon_encode(filtered_elements, {"delimiter": "|"})
        print(toon_elements)
        
        # Verificaciones básicas
        assert len(elements) > 0, "No se encontraron elementos"
        
        # Verificar que se capturó el ImageView informativo
        image_info_found = False
        for element in elements:
            class_name = get_attr_value(element, "class")
            content_desc = get_attr_value(element, "content-desc")
            element_type = get_attr_value(element, "possible_element_type")
            
            if "ImageView" in class_name and "restablecida" in content_desc:
                image_info_found = True
                assert element_type == "image_info", f"Se esperaba 'image_info', se obtuvo '{element_type}'"
                break
        
        if not image_info_found:
            print("\n⚠️  ADVERTENCIA: No se encontró el ImageView informativo del diálogo")
        else:
            print("\n✓ ImageView informativo encontrado y marcado como 'image_info'")

    def test_inspect_login_xml(self):
        """
        Inspecciona el parseo del XML de la pantalla de login.
        
        Muestra:
        - Elementos encontrados
        - JSON interno
        - TOON que ve el agente
        - Información detallada de cada elemento
        """
        if not XML_LOGIN.strip() or XML_LOGIN.strip().startswith("#"):
            pytest.skip("XML_LOGIN no está configurado. Pega el XML en la variable XML_LOGIN.")
        
        parser = UIParser()
        elements = parser.parse_screen(XML_LOGIN, current_package="com.imagineapps.gofixiicliente")
        
        print("\n" + "█" * 80)
        print("  INSPECCIÓN: Pantalla de Login")
        print("█" * 80)
        print(f"\n✓ Elementos encontrados: {len(elements)}")
        
        # Información detallada
        print("\n" + "=" * 80)
        print("  ELEMENTOS DETALLADOS")
        print("=" * 80)
        for i, element in enumerate(elements):
            print(f"\n[{i}] Elemento ID: {element['id']}")
            print("-" * 80)
            
            class_name = get_attr_value(element, "class")
            content_desc = get_attr_value(element, "content-desc")
            text = get_attr_value(element, "text")
            element_type = get_attr_value(element, "possible_element_type")
            xpath = get_attr_value(element, "xpath")
            clickable = get_attr_value(element, "clickable")
            bounds = get_attr_value(element, "bounds")
            
            print(f"  Tipo detectado: {element_type}")
            print(f"  Clase: {class_name}")
            if content_desc:
                print(f"  Content-desc: {content_desc[:100] + '...' if len(content_desc) > 100 else content_desc}")
            if text:
                print(f"  Text: {text}")
            print(f"  Clickable: {clickable}")
            if bounds:
                print(f"  Bounds: {bounds}")
            print(f"  XPath: {xpath[:80] + '...' if len(xpath) > 80 else xpath}")
            
            print(f"  Todos los atributos ({len(element['attrs'])}):")
            for attr in element['attrs']:
                attr_name = attr.get('name', '')
                attr_value = attr.get('value', '')
                if len(attr_value) > 60:
                    attr_value = attr_value[:57] + "..."
                print(f"    - {attr_name}: {attr_value}")
        
        # JSON interno
        print("\n" + "=" * 80)
        print("  JSON INTERNO (estructura completa)")
        print("=" * 80)
        print(json.dumps(elements, indent=2, ensure_ascii=False))
        
        # TOON (lo que ve el agente)
        print("\n" + "=" * 80)
        print("  TOON - Lo que ve el agente (después del filtrado)")
        print("=" * 80)
        
        # Filtrar propiedades como lo hace el AI Orchestrator
        filtered_elements = []
        properties_to_remove = {"bounds", "clickable", "enabled", "displayed"}
        
        for element in elements:
            filtered_element = element.copy()
            if "attrs" in filtered_element:
                filtered_element["attrs"] = [
                    attr for attr in filtered_element["attrs"]
                    if attr.get("name") not in properties_to_remove
                ]
            filtered_elements.append(filtered_element)
        
        # Convertir a TOON
        toon_elements = toon_encode(filtered_elements, {"delimiter": "|"})
        print(toon_elements)
        
        # Verificaciones básicas
        assert len(elements) > 0, "No se encontraron elementos"
        
        # Contar tipos
        element_types = {}
        for element in elements:
            element_type = get_attr_value(element, "possible_element_type")
            element_types[element_type] = element_types.get(element_type, 0) + 1
        
        print("\n" + "=" * 80)
        print("  RESUMEN DE TIPOS DETECTADOS")
        print("=" * 80)
        for elem_type, count in sorted(element_types.items()):
            print(f"  - {elem_type}: {count} elemento(s)")
        
        # Verificar que hay inputs
        assert element_types.get("input", 0) >= 2, f"Se esperaban al menos 2 inputs, se encontraron {element_types.get('input', 0)}"
        
        # Verificar que hay icon_button (ojo de password)
        if element_types.get("icon_button", 0) == 0:
            print("\n⚠️  ADVERTENCIA: No se encontró ningún icon_button (esperado: icono de password)")
