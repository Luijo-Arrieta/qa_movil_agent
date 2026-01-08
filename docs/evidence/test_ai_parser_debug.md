# Ejecución: UIParser AI Debug Test

Test completo que demuestra el flujo de transformación de XML → JSON → TOON para procesamiento de IA.

---

## 📋 Comando Ejecutado

```bash
poetry run pytest tests/specs/unit_test_ui_parser_integration.py::TestUIParserIntegration::test_ai_parser_debug -v
```

---

## 🔧 Setup y Configuración

### Información del Entorno

```bash
Platform:        win32 - Python 3.13.2
Pytest:          8.3.5
Appium:          3.1.1
Session ID:      1fea84b8-0cba-4c61-b5fd-2292709b6676
Device time:     2026-01-08T22:16:46+00:00
Window size:     1080x2400 (Android)
```

### Configuración de Appium

| Propiedad | Valor |
| --- | --- |
| **Platform** | Android |
| **Automation** | UiAutomator2 |
| **Device** | emulator-5554 |
| **App Package** | com.imagineapps.gofixiicliente |
| **Activity** | .MainActivity |
| **Timeout** | 600s (10 min) |

---

## ⏱️ Tiempos de Ejecución

| Fase | Duración |
| --- | --- |
| Setup fixture | 16.59s |
| Espera de app | 12s |
| Test execution | 29.67s **TOTAL** |

---

## 📄 FASE 1: XML Source (Raw Appium)

**Estado:** ✓ XML obtenido (9,304 caracteres)

```xml
<?xml version="1.0" ?>
<hierarchy index="0" class="hierarchy" rotation="0" width="1080" height="2400">
  <android.widget.FrameLayout index="0" package="com.imagineapps.gofixiicliente" class="android.widget.FrameLayout" text="" checkable="false" checked="false" clickable="false" enabled="true" focusable="false" focused="false" long-clickable="false" password="false" scrollable="false" selected="false" bounds="[0,0][1080,2400]" displayed="true">
    <android.widget.LinearLayout index="0" package="com.imagineapps.gofixiicliente" class="android.widget.LinearLayout" text="" checkable="false" checked="false" clickable="false" enabled="true" focusable="false" focused="false" long-clickable="false" password="false" scrollable="false" selected="false" bounds="[0,0][1080,2400]" displayed="true">
      <android.widget.FrameLayout index="0" package="com.imagineapps.gofixiicliente" class="android.widget.FrameLayout" text="" resource-id="android:id/content" checkable="false" checked="false" clickable="false" enabled="true" focusable="false" focused="false" long-clickable="false" password="false" scrollable="false" selected="false" bounds="[0,0][1080,2400]" displayed="true">
        <android.widget.FrameLayout index="0" package="com.imagineapps.gofixiicliente" class="android.widget.FrameLayout" text="" checkable="false" checked="false" clickable="false" enabled="true" focusable="true" focused="false" long-clickable="false" password="false" scrollable="false" selected="false" bounds="[0,0][1080,2400]" displayed="true">
          <android.view.View index="0" package="com.imagineapps.gofixiicliente" class="android.view.View" text="" resource-id="" checkable="false" checked="false" clickable="false" enabled="true" focusable="false" focused="false" long-clickable="false" password="false" scrollable="false" selected="false" bounds="[0,0][1080,2400]" displayed="true">
            <android.view.View index="0" package="com.imagineapps.gofixiicliente" class="android.view.View" text="" resource-id="" checkable="false" checked="false" clickable="false" enabled="true" focusable="false" focused="false" long-clickable="false" password="false" scrollable="false" selected="false" bounds="[0,0][1080,2400]" displayed="true">
              <android.view.View index="0" package="com.imagineapps.gofixiicliente" class="android.view.View" text="" resource-id="" checkable="false" checked="false" clickable="false" enabled="true" focusable="false" focused="false" long-clickable="false" password="false" scrollable="false" selected="false" bounds="[0,0][1080,2400]" displayed="true">
                <android.view.View index="0" package="com.imagineapps.gofixiicliente" class="android.view.View" text="" content-desc="Iniciar sesión" resource-id="" checkable="false" checked="false" clickable="true" enabled="true" focusable="true" focused="false" long-clickable="false" password="false" scrollable="false" selected="false" bounds="[0,0][1080,2400]" displayed="true">
                  <android.view.View index="0" package="com.imagineapps.gofixiicliente" class="android.view.View" text="" resource-id="" checkable="false" checked="false" clickable="false" enabled="true" focusable="false" focused="false" long-clickable="false" password="false" scrollable="false" selected="false" bounds="[0,0][1080,210]" displayed="true"/>
                  <android.view.View index="1" package="com.imagineapps.gofixiicliente" class="android.view.View" text="" resource-id="" checkable="false" checked="false" clickable="false" enabled="true" focusable="false" focused="false" long-clickable="false" password="false" scrollable="false" selected="false" bounds="[0,210][1080,1457]" displayed="true">
                    <android.widget.ImageView index="0" package="com.imagineapps.gofixiicliente" class="android.widget.ImageView" text="" resource-id="" checkable="false" checked="false" clickable="false" enabled="true" focusable="false" focused="false" long-clickable="false" password="false" scrollable="false" selected="false" bounds="[53,210][373,318]" displayed="true"/>
                    <android.view.View index="1" package="com.imagineapps.gofixiicliente" class="android.view.View" text="" content-desc="Inicia sesión" resource-id="" checkable="false" checked="false" clickable="false" enabled="true" focusable="true" focused="false" long-clickable="false" password="false" scrollable="false" selected="false" bounds="[53,402][346,473]" displayed="true"/>
                    <android.view.View index="2" package="com.imagineapps.gofixiicliente" class="android.view.View" text="" content-desc="Ingresa a tu cuenta y gestiona tus servicios, agendamientos o cotizaciones de forma fácil y rápida." resource-id="" checkable="false" checked="false" clickable="false" enabled="true" focusable="true" focused="false" long-clickable="false" password="false" scrollable="false" selected="false" bounds="[53,483][1028,672]" displayed="true"/>
                    <android.view.View index="3" package="com.imagineapps.gofixiicliente" class="android.view.View" text="" content-desc="Correo electrónico" resource-id="" checkable="false" checked="false" clickable="false" enabled="true" focusable="true" focused="false" long-clickable="false" password="false" scrollable="false" selected="false" bounds="[53,756][418,819]" displayed="true"/>
                    <android.widget.EditText index="4" package="com.imagineapps.gofixiicliente" class="android.widget.EditText" text="" resource-id="" checkable="false" checked="false" clickable="true" enabled="true" focusable="true" focused="false" long-clickable="false" password="false" scrollable="false" selected="false" bounds="[53,824][1028,950]" displayed="true" hint="Ejemplo@mail.com"/>
                    <android.view.View index="5" package="com.imagineapps.gofixiicliente" class="android.view.View" text="" content-desc="Contraseña" resource-id="" checkable="false" checked="false" clickable="false" enabled="true" focusable="true" focused="false" long-clickable="false" password="false" scrollable="false" selected="false" bounds="[53,1034][280,1097]" displayed="true"/>
                    <android.view.View index="6" package="com.imagineapps.gofixiicliente" class="android.view.View" text="" content-desc="**********" resource-id="" checkable="false" checked="false" clickable="true" enabled="true" focusable="true" focused="false" long-clickable="false" password="false" scrollable="false" selected="false" bounds="[53,1103][1028,1229]" displayed="true">
                      <android.widget.EditText index="0" package="com.imagineapps.gofixiicliente" class="android.widget.EditText" text="" resource-id="" checkable="false" checked="false" clickable="false" enabled="true" focusable="true" focused="false" long-clickable="false" password="true" scrollable="false" selected="false" bounds="[84,1134][891,1197]" displayed="true"/>
                      <android.widget.ImageView index="1" package="com.imagineapps.gofixiicliente" class="android.widget.ImageView" text="" resource-id="" checkable="false" checked="false" clickable="true" enabled="true" focusable="true" focused="false" long-clickable="false" password="false" scrollable="false" selected="false" bounds="[901,1103][1028,1229]" displayed="true"/>
                    </android.view.View>
                    <android.view.View index="7" package="com.imagineapps.gofixiicliente" class="android.view.View" text="" content-desc="¿Olvidaste tu contraseña?" resource-id="" checkable="false" checked="false" clickable="true" enabled="true" focusable="true" focused="false" long-clickable="false" password="false" scrollable="false" selected="false" bounds="[53,1313][574,1373]" displayed="true"/>
                  </android.view.View>
                  <android.view.View index="2" package="com.imagineapps.gofixiicliente" class="android.view.View" text="" resource-id="" checkable="false" checked="false" clickable="false" enabled="true" focusable="false" focused="false" long-clickable="false" password="false" scrollable="false" selected="false" bounds="[171,2232][909,2295]" displayed="true">
                    <android.view.View index="0" package="com.imagineapps.gofixiicliente" class="android.view.View" text="" content-desc="¿No tienes una cuenta? " resource-id="" checkable="false" checked="false" clickable="false" enabled="true" focusable="true" focused="false" long-clickable="false" password="false" scrollable="false" selected="false" bounds="[160,2224][657,2303]" displayed="true"/>
                    <android.view.View index="1" package="com.imagineapps.gofixiicliente" class="android.view.View" text="" content-desc="Crear cuenta" resource-id="" checkable="false" checked="false" clickable="true" enabled="true" focusable="true" focused="false" long-clickable="false" password="false" scrollable="false" selected="false" bounds="[633,2224][922,2303]" displayed="true"/>
                  </android.view.View>
                </android.view.View>
              </android.view.View>
            </android.view.View>
          </android.view.View>
        </android.widget.FrameLayout>
      </android.widget.FrameLayout>
    </android.widget.LinearLayout>
  </android.widget.FrameLayout>
</hierarchy>
```

**Análisis:**

- Nodos visitados: 24
- Elementos filtrados: 18

---

## 🔍 FASE 2: Parseo UIParser

**Estado:** ✓ Se parsearon 6 elementos interactuables

| Métrica | Valor |
| --- | --- |
| Nodos visitados | 24 |
| Elementos interactuables | 6 |
| Elementos filtrados | 18 |

---

## 📋 FASE 3: JSON (Formato Interno)

**Estado:** ✓ JSON generado (2,264 caracteres)

```json
[
  {
    "resource-id": "",
    "content-desc": "Iniciar sesión",
    "class": "android.view.View",
    "index": "0",
    "xpath": "//android.view.View[@content-desc=\"Iniciar sesión\"]",
    "bounds": "[0,0][1080,2400]",
    "clickable": "true",
    "displayed": "true",
    "enabled": "true",
    "password": "false",
    "scrollable": "false",
    "text": "",
    "hint": ""
  },
  {
    "resource-id": "",
    "content-desc": "",
    "class": "android.widget.EditText",
    "index": "4",
    "xpath": "//android.widget.EditText",
    "bounds": "[53,824][1028,950]",
    "clickable": "true",
    "displayed": "true",
    "enabled": "true",
    "password": "false",
    "scrollable": "false",
    "text": "",
    "hint": "Ejemplo@mail.com"
  },
  {
    "resource-id": "",
    "content-desc": "**********",
    "class": "android.view.View",
    "index": "6",
    "xpath": "//android.view.View[@content-desc=\"**********\"]",
    "bounds": "[53,1103][1028,1229]",
    "clickable": "true",
    "displayed": "true",
    "enabled": "true",
    "password": "false",
    "scrollable": "false",
    "text": "",
    "hint": ""
  },
  {
    "resource-id": "",
    "content-desc": "",
    "class": "android.widget.EditText",
    "index": "0",
    "xpath": "//android.widget.EditText",
    "bounds": "[84,1134][891,1197]",
    "clickable": "false",
    "displayed": "true",
    "enabled": "true",
    "password": "true",
    "scrollable": "false",
    "text": "",
    "hint": ""
  },
  {
    "resource-id": "",
    "content-desc": "¿Olvidaste tu contraseña?",
    "class": "android.view.View",
    "index": "7",
    "xpath": "//android.view.View[@content-desc=\"¿Olvidaste tu contraseña?\"]",
    "bounds": "[53,1313][574,1373]",
    "clickable": "true",
    "displayed": "true",
    "enabled": "true",
    "password": "false",
    "scrollable": "false",
    "text": "",
    "hint": ""
  },
  {
    "resource-id": "",
    "content-desc": "Crear cuenta",
    "class": "android.view.View",
    "index": "1",
    "xpath": "//android.view.View[@content-desc=\"Crear cuenta\"]",
    "bounds": "[633,2224][922,2303]",
    "clickable": "true",
    "displayed": "true",
    "enabled": "true",
    "password": "false",
    "scrollable": "false",
    "text": "",
    "hint": ""
  }
]
```

---

## 📊 FASE 4: Resumen XPaths

**Estado:** ✓ XPaths mapeados (incluidos en JSON)

| ID | Elemento | XPath |
| --- | --- | --- |
| [0] | Iniciar sesión | `//android.view.View[@content-desc="Iniciar sesión"]` |
| [1] | sin-id | `//android.widget.EditText` |
| [2] | ********** | `//android.view.View[@content-desc="**********"]` |
| [3] | sin-id | `//android.widget.EditText` |
| [4] | ¿Olvidaste tu contraseña? | `//android.view.View[@content-desc="¿Olvidaste tu contraseña?"]` |
| [5] | Crear cuenta | `//android.view.View[@content-desc="Crear cuenta"]` |

---

## 🎯 FASE 5: TOON (Token-Oriented Object Notation)

**Estado:** ✓ TOON generado (1,046 caracteres) — **53.8% menos caracteres que JSON**

```toon
[6       ]{resource-id  content-desc  class  index  xpath  bounds  clickable  displayed  enabled  password  scrollable  text  hint}:
""       Iniciar sesión  android.view.View  "0"  "//android.view.View[@content-desc=\"Iniciar sesión\"]"  "[0,0][1080,2400]"  "true"  "true"  "true"  "false"  "false"  ""  ""
""       ""  android.widget.EditText  "4"  //android.widget.EditText  "[53,824][1028,950]"  "true"  "true"  "true"  "false"  "false"  ""  Ejemplo@mail.com
""       **********  android.view.View  "6"  "//android.view.View[@content-desc=\"**********\"]"  "[53,1103][1028,1229]"  "true"  "true"  "true"  "false"  "false"  ""  ""
""       ""  android.widget.EditText  "0"  //android.widget.EditText  "[84,1134][891,1197]"  "false"  "true"  "true"  "true"  "false"  ""  ""
""       ¿Olvidaste tu contraseña?  android.view.View  "7"  "//android.view.View[@content-desc=\"¿Olvidaste tu contraseña?\"]"  "[53,1313][574,1373]"  "true"  "true"  "true"  "false"  "false"  ""  ""
""       Crear cuenta  android.view.View  "1"  "//android.view.View[@content-desc=\"Crear cuenta\"]"  "[633,2224][922,2303]"  "true"  "true"  "true"  "false"  "false"  ""  ""
```

**Ventajas del TOON:**

- Formato tabular con headers (reduce repetición)
- Tab-separated values
- Mantiene fidelidad completa de datos
- 30-60% menos tokens que JSON

---

## 📈 Comparación de Tamaños

| Formato | Caracteres | Reducción |
| --- | --- | --- |
| XML source | 9,304 | - |
| JSON | 2,264 | 75.7% vs XML |
| TOON | 1,046 | 53.8% vs JSON |
| **TOON vs XML** | **1,046** | **88.8%** |

---

## ✅ Resumen Final

### Estadísticas de Elementos

| Tipo | Cantidad |
| --- | --- |
| **Total de elementos** | 6 |
| 📝 Inputs (EditText) | 2 |
| 🔘 Clickeables | 5 |

### Ahorro de Tokens

- **TOON vs JSON:** 53.8% reducción
- **TOON vs XML:** 88.8% reducción

### Estado

```text
✅ Test de depuración completado exitosamente
📸 Screenshots y XML adjuntados a Allure
⏱️ Tiempo total: 29.67s
```

---

## 🔗 Referencias

- **UIParser:** `src/ui_parser.py` - Transforma XML en JSON/TOON simplificado
- **TOON Format:** Especificación en [github.com/toon-format/toon](https://github.com/toon-format/toon)
- **Allure Reports:** `scripts/generate_report.py`
