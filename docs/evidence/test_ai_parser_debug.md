# Ejecución de un test unitario

```bash
USER@DESKTOP-0KP4BHJ MINGW64 /d/Imagine/qa_movil_agent (main)
$ poetry run pytest tests/specs/unit_test_ui_parser_integration.py::TestUIParserIntegration::test_ai_parser_debug -v
================================ test session starts ================================
platform win32 -- Python 3.13.2, pytest-8.3.5, pluggy-1.5.0 -- C:\Users\USER\AppData\Local\pypoetry\Cache\virtualenvs\qa-movil-agent-XcYuopvM-py3.13\Scripts\python.exe
cachedir: .pytest_cache
metadata: {'Python': '3.13.2', 'Platform': 'Windows-11-10.0.26200-SP0', 'Packages': {'pytest': '8.3.5', 'pluggy': '1.5.0'}, 'Plugins': {'allure-pytest': '2.15.3', 'anyio': '4.5.2', 'html': '4.1.1', 'metadata': '3.1.1', 'timeout': '2.4.0'}, 'JAVA_HOME': 'D:\\Programas instalados\\java\\jdk-22'}
rootdir: D:\Imagine\qa_movil_agent
configfile: pytest.ini
plugins: allure-pytest-2.15.3, anyio-4.5.2, html-4.1.1, metadata-3.1.1, timeout-2.4.0
timeout: 300.0s
timeout method: thread
timeout func_only: False
collected 1 item                                                                     

tests/specs/unit_test_ui_parser_integration.py::TestUIParserIntegration::test_ai_parser_debug 
---------------------------------- live log setup -----------------------------------
2026-01-08 16:03:37.180 - tests.specs.conftest - INFO - 
2026-01-08 16:03:37.180 - tests.specs.conftest - INFO - ████████████████████████████████████████████████████████████████████████████████
2026-01-08 16:03:37.180 - tests.specs.conftest - INFO - █  CONFTEST: INICIANDO FIXTURE driver_setup
2026-01-08 16:03:37.181 - tests.specs.conftest - INFO - ████████████████████████████████████████████████████████████████████████████████
2026-01-08 16:03:37.181 - tests.specs.conftest - INFO -
2026-01-08 16:03:37.181 - tests.specs.conftest - INFO - CONFTEST: FASE 1 - Verificando Appium Server...
2026-01-08 16:03:37.181 - tests.specs.conftest - INFO - ======================================================================
2026-01-08 16:03:37.182 - tests.specs.conftest - INFO - CONFTEST: Verificando disponibilidad del servidor Appium...
2026-01-08 16:03:37.182 - tests.specs.conftest - INFO - ======================================================================
2026-01-08 16:03:39.266 - tests.specs.conftest - INFO - CONFTEST: Appium version: 3.1.1
2026-01-08 16:03:39.266 - tests.specs.conftest - INFO - CONFTEST: ✓ Appium Server disponible en http://localhost:4723
2026-01-08 16:03:39.267 - tests.specs.conftest - INFO -
2026-01-08 16:03:39.267 - tests.specs.conftest - INFO - CONFTEST: FASE 2 - Configurando capabilities...
2026-01-08 16:03:39.267 - src.config - INFO - ======================================================================
2026-01-08 16:03:39.267 - src.config - INFO - CONFIG DEBUG: Estado actual de la configuración
2026-01-08 16:03:39.268 - src.config - INFO - ======================================================================
2026-01-08 16:03:39.268 - src.config - INFO -   OPENAI_API_KEY: ✓ Configurada
2026-01-08 16:03:39.268 - src.config - INFO -   ANTHROPIC_API_KEY: ✓ Configurada      
2026-01-08 16:03:39.268 - src.config - INFO -   AI_PROVIDER: openai
2026-01-08 16:03:39.269 - src.config - INFO -   OPENAI_MODEL: gpt-4o
2026-01-08 16:03:39.269 - src.config - INFO -   ANTHROPIC_MODEL: claude-3-5-sonnet-20241022
2026-01-08 16:03:39.269 - src.config - INFO - ----------------------------------------
2026-01-08 16:03:39.269 - src.config - INFO -   APPIUM_SERVER_URL: http://localhost:4723
2026-01-08 16:03:39.269 - src.config - INFO -   ANDROID_PLATFORM_NAME: Android        
2026-01-08 16:03:39.270 - src.config - INFO -   ANDROID_DEVICE_NAME: emulator-5554    
2026-01-08 16:03:39.270 - src.config - INFO -   ANDROID_APP_PACKAGE: com.imagineapps.gofixiicliente
2026-01-08 16:03:39.270 - src.config - INFO -   ANDROID_APP_ACTIVITY: .MainActivity   
2026-01-08 16:03:39.270 - src.config - INFO -   ANDROID_APP_PATH: D:/Imagine/qa_movil_agent/apks/2026-01-05-cliente.apk
2026-01-08 16:03:39.271 - src.config - INFO -   ANDROID_UDID: emulator-5554
2026-01-08 16:03:39.271 - src.config - INFO -   ANDROID_AUTOMATION_NAME: UiAutomator2 
2026-01-08 16:03:39.271 - src.config - INFO - ----------------------------------------
2026-01-08 16:03:39.271 - src.config - INFO -   AUTO_GRANT_PERMISSIONS: True
2026-01-08 16:03:39.271 - src.config - INFO -   IGNORE_HIDDEN_API_ERROR: True
2026-01-08 16:03:39.272 - src.config - INFO -   DISABLE_WINDOW_ANIMATION: True        
2026-01-08 16:03:39.272 - src.config - INFO - ----------------------------------------
2026-01-08 16:03:39.272 - src.config - INFO -   DEFAULT_WAIT_TIMEOUT: 10 minutos (600 segundos)
2026-01-08 16:03:39.272 - src.config - INFO -   IMPLICIT_WAIT: 5 segundos
2026-01-08 16:03:39.272 - src.config - INFO - ----------------------------------------
2026-01-08 16:03:39.272 - src.config - INFO -   UI Stability (pantallas de carga):    
2026-01-08 16:03:39.273 - src.config - INFO -     UI_STABILITY_TIMEOUT: 10.0s
2026-01-08 16:03:39.273 - src.config - INFO -     UI_STABILITY_INTERVAL: 0.3s
2026-01-08 16:03:39.273 - src.config - INFO -     UI_STABILITY_THRESHOLD: 2 checks    
2026-01-08 16:03:39.273 - src.config - INFO - ======================================================================
2026-01-08 16:03:39.275 - tests.specs.conftest - INFO - CONFTEST: 📱 Capabilities configuradas:
2026-01-08 16:03:39.275 - tests.specs.conftest - INFO - CONFTEST:    platformName: Android
2026-01-08 16:03:39.275 - tests.specs.conftest - INFO - CONFTEST:    appium:automationName: UiAutomator2
2026-01-08 16:03:39.275 - tests.specs.conftest - INFO - CONFTEST:    appium:deviceName: emulator-5554
2026-01-08 16:03:39.275 - tests.specs.conftest - INFO - CONFTEST:    appium:newCommandTimeout: 600
2026-01-08 16:03:39.276 - tests.specs.conftest - INFO - CONFTEST:    appium:udid: emulator-5554
2026-01-08 16:03:39.276 - tests.specs.conftest - INFO - CONFTEST:    appium:app: D:/Imagine/qa_movil_agent/apks/2026-01-05-cliente.apk
2026-01-08 16:03:39.276 - tests.specs.conftest - INFO - CONFTEST:    appium:appPackage: com.imagineapps.gofixiicliente
2026-01-08 16:03:39.276 - tests.specs.conftest - INFO - CONFTEST:    appium:appActivity: .MainActivity
2026-01-08 16:03:39.276 - tests.specs.conftest - INFO - CONFTEST:    appium:autoGrantPermissions: True
2026-01-08 16:03:39.276 - tests.specs.conftest - INFO - CONFTEST:    appium:ignoreHiddenApiPolicyError: True
2026-01-08 16:03:39.277 - tests.specs.conftest - INFO - CONFTEST:    appium:disableWindowAnimation: True
2026-01-08 16:03:39.277 - tests.specs.conftest - INFO - CONFTEST:    appium:skipDeviceInitialization: False
2026-01-08 16:03:39.277 - tests.specs.conftest - INFO - CONFTEST:    appium:disableSuppressAccessibilityService: True
2026-01-08 16:03:39.277 - tests.specs.conftest - INFO -
2026-01-08 16:03:39.277 - tests.specs.conftest - INFO - CONFTEST: FASE 3 - Creando UiAutomator2Options...
2026-01-08 16:03:39.278 - tests.specs.conftest - INFO - CONFTEST: ✓ Options creadas   
2026-01-08 16:03:39.278 - tests.specs.conftest - INFO -
2026-01-08 16:03:39.279 - tests.specs.conftest - INFO - CONFTEST: FASE 4 - Inicializando driver de Appium...
2026-01-08 16:03:39.279 - tests.specs.conftest - INFO - CONFTEST: 🚀 Conectando a http://localhost:4723...
2026-01-08 16:03:47.870 - tests.specs.conftest - INFO - CONFTEST: ✓ Driver creado en 8.59s
2026-01-08 16:03:47.870 - tests.specs.conftest - INFO - CONFTEST: Session ID: 5a7a57ce-9f8f-48d3-8877-630e5003b9ce
2026-01-08 16:03:47.875 - tests.specs.conftest - INFO -
2026-01-08 16:03:47.876 - tests.specs.conftest - INFO - CONFTEST: FASE 5 - Obteniendo información del dispositivo...
2026-01-08 16:03:47.948 - tests.specs.conftest - INFO - CONFTEST: Device time: 2026-01-08T21:02:22+00:00
2026-01-08 16:03:47.960 - tests.specs.conftest - INFO - CONFTEST: Window size: 1080x2400
2026-01-08 16:03:47.960 - tests.specs.conftest - INFO - CONFTEST: Platform: Android   
2026-01-08 16:03:47.960 - tests.specs.conftest - INFO - CONFTEST: Platform Version: 16
2026-01-08 16:03:47.960 - tests.specs.conftest - INFO - CONFTEST: Device Name: emulator-5554
2026-01-08 16:03:47.960 - tests.specs.conftest - INFO - CONFTEST: Device UDID: emulator-5554
2026-01-08 16:03:47.961 - tests.specs.conftest - INFO - CONFTEST: App Package: com.imagineapps.gofixiicliente
2026-01-08 16:03:47.961 - tests.specs.conftest - INFO - CONFTEST: App Activity: .MainActivity
2026-01-08 16:03:47.961 - tests.specs.conftest - INFO - CONFTEST: ✓ Driver inicializado correctamente
2026-01-08 16:03:47.961 - tests.specs.conftest - INFO -
2026-01-08 16:03:47.961 - tests.specs.conftest - INFO - CONFTEST: ✅ Fixture setup completado en 10.78s
2026-01-08 16:03:47.962 - tests.specs.conftest - INFO - ================================================================================
2026-01-08 16:03:47.962 - tests.specs.conftest - INFO -
----------------------------------- live log call ----------------------------------- 
2026-01-08 16:03:47.963 - tests.specs.unit_test_ui_parser_integration - INFO -        
2026-01-08 16:03:47.964 - tests.specs.unit_test_ui_parser_integration - INFO - ================================================================================
2026-01-08 16:03:47.964 - tests.specs.unit_test_ui_parser_integration - INFO - 🔍 TEST DE DEPURACIÓN COMPLETO PARA PARSER DE IA
2026-01-08 16:03:47.964 - tests.specs.unit_test_ui_parser_integration - INFO - ================================================================================
2026-01-08 16:03:47.964 - tests.specs.unit_test_ui_parser_integration - INFO -        
2026-01-08 16:03:47.964 - tests.specs.unit_test_ui_parser_integration - INFO - 📱 Esperando a que la app cargue completamente...
2026-01-08 16:03:47.965 - tests.specs.unit_test_ui_parser_integration - INFO -    Esperando 12 segundos para que la app inicie...
2026-01-08 16:04:00.343 - tests.specs.conftest - INFO - 📸 Screenshot adjuntado a Allure: 01_ai_parser_debug_inicial
2026-01-08 16:04:00.343 - tests.specs.unit_test_ui_parser_integration - INFO - 
2026-01-08 16:04:00.343 - tests.specs.unit_test_ui_parser_integration - INFO - ╔══════════════════════════════════════════════════════════════════════════════╗
2026-01-08 16:04:00.343 - tests.specs.unit_test_ui_parser_integration - INFO - ║  FASE 1: OBTENER XML SOURCE
2026-01-08 16:04:00.344 - tests.specs.unit_test_ui_parser_integration - INFO - ╚══════════════════════════════════════════════════════════════════════════════╝
2026-01-08 16:04:00.344 - tests.specs.unit_test_ui_parser_integration - INFO -        
2026-01-08 16:04:00.344 - tests.specs.unit_test_ui_parser_integration - INFO - 📱 Obteniendo page_source del driver...
2026-01-08 16:04:00.401 - tests.specs.unit_test_ui_parser_integration - INFO - ✓ XML obtenido: 9304 caracteres
2026-01-08 16:04:00.401 - tests.specs.unit_test_ui_parser_integration - INFO - 
2026-01-08 16:04:00.402 - tests.specs.unit_test_ui_parser_integration - INFO - 📄 XML SOURCE (FORMATEADO):
2026-01-08 16:04:00.402 - tests.specs.unit_test_ui_parser_integration - INFO - ────────────────────────────────────────────────────────────────────────────────
2026-01-08 16:04:00.435 - tests.specs.unit_test_ui_parser_integration - INFO - 
```

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

```bash
2026-01-08 16:04:00.436 - tests.specs.unit_test_ui_parser_integration - INFO - ────────────────────────────────────────────────────────────────────────────────
2026-01-08 16:04:00.436 - tests.specs.unit_test_ui_parser_integration - INFO - ✓ XML formateado: 9222 caracteres
2026-01-08 16:04:00.437 - tests.specs.unit_test_ui_parser_integration - INFO -        
2026-01-08 16:04:00.437 - tests.specs.unit_test_ui_parser_integration - INFO - ╔══════════════════════════════════════════════════════════════════════════════╗
2026-01-08 16:04:00.437 - tests.specs.unit_test_ui_parser_integration - INFO - ║  FASE 2: PARSEAR CON UIPARSER
2026-01-08 16:04:00.437 - tests.specs.unit_test_ui_parser_integration - INFO - ╚══════════════════════════════════════════════════════════════════════════════╝
2026-01-08 16:04:00.437 - tests.specs.unit_test_ui_parser_integration - INFO -        
2026-01-08 16:04:00.437 - tests.specs.unit_test_ui_parser_integration - INFO - 🔍 Creando instancia de UIParser...
2026-01-08 16:04:00.438 - tests.specs.unit_test_ui_parser_integration - INFO - 🔍 Parseando XML con UIParser...
2026-01-08 16:04:00.441 - src.ui_parser - INFO - UIPARSER: Parseo completado
2026-01-08 16:04:00.441 - src.ui_parser - INFO -   - Nodos visitados: 24
2026-01-08 16:04:00.441 - src.ui_parser - INFO -   - Elementos interactuables encontrados: 6
2026-01-08 16:04:00.442 - src.ui_parser - INFO -   - Elementos filtrados: 18
2026-01-08 16:04:00.442 - tests.specs.unit_test_ui_parser_integration - INFO - ✓ Se parsearon 6 elementos interactuables
2026-01-08 16:04:00.443 - tests.specs.unit_test_ui_parser_integration - INFO -        
2026-01-08 16:04:00.443 - tests.specs.unit_test_ui_parser_integration - INFO - ╔══════════════════════════════════════════════════════════════════════════════╗
2026-01-08 16:04:00.443 - tests.specs.unit_test_ui_parser_integration - INFO - ║  FASE 3: JSON DE ELEMENTOS PARSEADOS (FORMATEADO)
2026-01-08 16:04:00.443 - tests.specs.unit_test_ui_parser_integration - INFO - ╚══════════════════════════════════════════════════════════════════════════════╝
2026-01-08 16:04:00.443 - tests.specs.unit_test_ui_parser_integration - INFO -        
2026-01-08 16:04:00.444 - tests.specs.unit_test_ui_parser_integration - INFO - 📋 JSON COMPLETO DE ELEMENTOS:
2026-01-08 16:04:00.444 - tests.specs.unit_test_ui_parser_integration - INFO - ────────────────────────────────────────────────────────────────────────────────
2026-01-08 16:04:00.444 - tests.specs.unit_test_ui_parser_integration - INFO - 
```

```json
[      
  {
    "id": 0,
    "role": "button",
    "label": "Iniciar sesión",
    "checked": null
  },
  {
    "id": 1,
    "role": "input",
    "label": "Ejemplo@mail.com",
    "checked": null
  },
  {
    "id": 2,
    "role": "button",
    "label": "**********",
    "checked": null
  },
  {
    "id": 3,
    "role": "input",
    "label": "Input field",
    "checked": null
  },
  {
    "id": 4,
    "role": "button",
    "label": "¿Olvidaste tu contraseña?",
    "checked": null
  },
  {
    "id": 5,
    "role": "button",
    "label": "Crear cuenta",
    "checked": null
  }
]
```

```bash
2026-01-08 16:04:00.444 - tests.specs.unit_test_ui_parser_integration - INFO - ────────────────────────────────────────────────────────────────────────────────
2026-01-08 16:04:00.445 - tests.specs.unit_test_ui_parser_integration - INFO - ✓ JSON generado: 574 caracteres
2026-01-08 16:04:00.445 - tests.specs.unit_test_ui_parser_integration - INFO -        
2026-01-08 16:04:00.445 - tests.specs.unit_test_ui_parser_integration - INFO - ╔══════════════════════════════════════════════════════════════════════════════╗
2026-01-08 16:04:00.445 - tests.specs.unit_test_ui_parser_integration - INFO - ║  FASE 4: JSON DE ELEMENTOS CON XPATHS
2026-01-08 16:04:00.445 - tests.specs.unit_test_ui_parser_integration - INFO - ╚══════════════════════════════════════════════════════════════════════════════╝
2026-01-08 16:04:00.445 - tests.specs.unit_test_ui_parser_integration - INFO -        
2026-01-08 16:04:00.446 - tests.specs.unit_test_ui_parser_integration - INFO - 📋 JSON CON XPATHS:
2026-01-08 16:04:00.446 - tests.specs.unit_test_ui_parser_integration - INFO - ────────────────────────────────────────────────────────────────────────────────
2026-01-08 16:04:00.447 - tests.specs.unit_test_ui_parser_integration - INFO - 
```

```json
[      
  {
    "id": 0,
    "role": "button",
    "label": "Iniciar sesión",
    "checked": null,
    "xpath": "//android.view.View[@content-desc=\"Iniciar sesión\"]"
  },
  {
    "id": 1,
    "role": "input",
    "label": "Ejemplo@mail.com",
    "checked": null,
    "xpath": "//android.widget.EditText"
  },
  {
    "id": 2,
    "role": "button",
    "label": "**********",
    "checked": null,
    "xpath": "//android.view.View[@content-desc=\"**********\"]"
  },
  {
    "id": 3,
    "role": "input",
    "label": "Input field",
    "checked": null,
    "xpath": "//android.widget.EditText"
  },
  {
    "id": 4,
    "role": "button",
    "label": "¿Olvidaste tu contraseña?",
    "checked": null,
    "xpath": "//android.view.View[@content-desc=\"¿Olvidaste tu contraseña?\"]"       
  },
  {
    "id": 5,
    "role": "button",
    "label": "Crear cuenta",
    "checked": null,
    "xpath": "//android.view.View[@content-desc=\"Crear cuenta\"]"
  }
]
```

```bash
2026-01-08 16:04:00.447 - tests.specs.unit_test_ui_parser_integration - INFO - ────────────────────────────────────────────────────────────────────────────────
2026-01-08 16:04:00.447 - tests.specs.unit_test_ui_parser_integration - INFO - ✓ JSON con XPaths generado: 943 caracteres
2026-01-08 16:04:00.447 - tests.specs.unit_test_ui_parser_integration - INFO -        
2026-01-08 16:04:00.448 - tests.specs.unit_test_ui_parser_integration - INFO - 📊 RESUMEN DE XPATHS:
2026-01-08 16:04:00.448 - tests.specs.unit_test_ui_parser_integration - INFO - ────────────────────────────────────────────────────────────────────────────────
2026-01-08 16:04:00.448 - tests.specs.unit_test_ui_parser_integration - INFO -   [  0] button   - XPath: //android.view.View[@content-desc="Iniciar sesión"]
2026-01-08 16:04:00.448 - tests.specs.unit_test_ui_parser_integration - INFO -   [  1] input    - XPath: //android.widget.EditText
2026-01-08 16:04:00.448 - tests.specs.unit_test_ui_parser_integration - INFO -   [  2] button   - XPath: //android.view.View[@content-desc="**********"]
2026-01-08 16:04:00.448 - tests.specs.unit_test_ui_parser_integration - INFO -   [  3] input    - XPath: //android.widget.EditText
2026-01-08 16:04:00.449 - tests.specs.unit_test_ui_parser_integration - INFO -   [  4] button   - XPath: //android.view.View[@content-desc="¿Olvidaste tu contraseña?"]     
2026-01-08 16:04:00.449 - tests.specs.unit_test_ui_parser_integration - INFO -   [  5] button   - XPath: //android.view.View[@content-desc="Crear cuenta"]
2026-01-08 16:04:00.449 - tests.specs.unit_test_ui_parser_integration - INFO - ────────────────────────────────────────────────────────────────────────────────
2026-01-08 16:04:00.449 - tests.specs.unit_test_ui_parser_integration - INFO -        
2026-01-08 16:04:00.449 - tests.specs.unit_test_ui_parser_integration - INFO - ╔══════════════════════════════════════════════════════════════════════════════╗
2026-01-08 16:04:00.449 - tests.specs.unit_test_ui_parser_integration - INFO - ║  FASE 5: TOON (FORMATO QUE LLEGA A LA IA)
2026-01-08 16:04:00.449 - tests.specs.unit_test_ui_parser_integration - INFO - ╚══════════════════════════════════════════════════════════════════════════════╝
2026-01-08 16:04:00.450 - tests.specs.unit_test_ui_parser_integration - INFO -        
2026-01-08 16:04:00.450 - tests.specs.unit_test_ui_parser_integration - INFO - 🔍 Convirtiendo elementos a formato TOON...
2026-01-08 16:04:00.450 - tests.specs.unit_test_ui_parser_integration - INFO -        
2026-01-08 16:04:00.450 - tests.specs.unit_test_ui_parser_integration - INFO - 📋 TOON COMPLETO (30-60% menos tokens que JSON):
2026-01-08 16:04:00.450 - tests.specs.unit_test_ui_parser_integration - INFO - ────────────────────────────────────────────────────────────────────────────────
2026-01-08 16:04:00.451 - tests.specs.unit_test_ui_parser_integration - INFO - 
```

```toon
# Usa tabs para separar los elementos

[6    ]{id     role    label   checked}:
  0     button  Iniciar sesión  null
  1     input   Ejemplo@mail.com        null
  2     button  **********      null
  3     input   Input field     null
  4     button  ¿Olvidaste tu contraseña?       null
  5     button  Crear cuenta    null
```

```bash
2026-01-08 16:04:00.451 - tests.specs.unit_test_ui_parser_integration - INFO - ────────────────────────────────────────────────────────────────────────────────
2026-01-08 16:04:00.451 - tests.specs.unit_test_ui_parser_integration - INFO - ✓ TOON generado: 216 caracteres
2026-01-08 16:04:00.451 - tests.specs.unit_test_ui_parser_integration - INFO -        
2026-01-08 16:04:00.451 - tests.specs.unit_test_ui_parser_integration - INFO - 📊 COMPARACIÓN DE TAMAÑOS:
2026-01-08 16:04:00.452 - tests.specs.unit_test_ui_parser_integration - INFO - ────────────────────────────────────────────────────────────────────────────────
2026-01-08 16:04:00.452 - tests.specs.unit_test_ui_parser_integration - INFO -   JSON:     574 caracteres
2026-01-08 16:04:00.452 - tests.specs.unit_test_ui_parser_integration - INFO -   TOON:     216 caracteres
2026-01-08 16:04:00.452 - tests.specs.unit_test_ui_parser_integration - INFO -   Reducción: 62.4% menos caracteres con TOON
2026-01-08 16:04:00.452 - tests.specs.unit_test_ui_parser_integration - INFO - ────────────────────────────────────────────────────────────────────────────────
2026-01-08 16:04:00.453 - tests.specs.unit_test_ui_parser_integration - INFO -        
2026-01-08 16:04:00.453 - tests.specs.unit_test_ui_parser_integration - INFO - ╔══════════════════════════════════════════════════════════════════════════════╗
2026-01-08 16:04:00.453 - tests.specs.unit_test_ui_parser_integration - INFO - ║  RESUMEN FINAL
2026-01-08 16:04:00.453 - tests.specs.unit_test_ui_parser_integration - INFO - ╚══════════════════════════════════════════════════════════════════════════════╝
2026-01-08 16:04:00.453 - tests.specs.unit_test_ui_parser_integration - INFO -        
2026-01-08 16:04:00.453 - tests.specs.unit_test_ui_parser_integration - INFO - 📊 ESTADÍSTICAS:
2026-01-08 16:04:00.454 - tests.specs.unit_test_ui_parser_integration - INFO -    Total de elementos: 6
2026-01-08 16:04:00.454 - tests.specs.unit_test_ui_parser_integration - INFO -    📝 Inputs: 2
2026-01-08 16:04:00.454 - tests.specs.unit_test_ui_parser_integration - INFO -    🔘 Botones: 4
2026-01-08 16:04:00.454 - tests.specs.unit_test_ui_parser_integration - INFO -    ☑️   Checkboxes: 0
2026-01-08 16:04:00.455 - tests.specs.unit_test_ui_parser_integration - INFO -        
2026-01-08 16:04:00.455 - tests.specs.unit_test_ui_parser_integration - INFO - 📏 TAMAÑOS:
2026-01-08 16:04:00.455 - tests.specs.unit_test_ui_parser_integration - INFO -    XML source: 9,304 caracteres
2026-01-08 16:04:00.455 - tests.specs.unit_test_ui_parser_integration - INFO -    JSON:       574 caracteres
2026-01-08 16:04:00.455 - tests.specs.unit_test_ui_parser_integration - INFO -    TOON:       216 caracteres
2026-01-08 16:04:00.455 - tests.specs.unit_test_ui_parser_integration - INFO -    Ahorro:     62.4% con TOON
2026-01-08 16:04:00.456 - tests.specs.unit_test_ui_parser_integration - INFO -
2026-01-08 16:04:00.456 - tests.specs.unit_test_ui_parser_integration - INFO - ================================================================================
2026-01-08 16:04:00.709 - tests.specs.conftest - INFO - 📸 Screenshot adjuntado a Allure: 02_ai_parser_debug_final_screenshot
2026-01-08 16:04:00.737 - tests.specs.conftest - INFO - 📄 Page source XML adjuntado a Allure: 02_ai_parser_debug_final_xml
PASSED                                                                         [100%]
--------------------------------- live log teardown ---------------------------------
2026-01-08 16:04:00.740 - tests.specs.conftest - INFO -
2026-01-08 16:04:00.740 - tests.specs.conftest - INFO - CONFTEST: FASE FINAL - Cerrando driver...
2026-01-08 16:04:00.740 - tests.specs.conftest - INFO - CONFTEST: 🔒 Cerrando session: 5a7a57ce-9f8f-48d3-8877-630e5003b9ce
2026-01-08 16:04:01.173 - tests.specs.conftest - INFO - CONFTEST: ✓ Driver cerrado correctamente
2026-01-08 16:04:01.174 - tests.specs.conftest - INFO - CONFTEST: Tiempo total del fixture: 23.99s
2026-01-08 16:04:01.174 - tests.specs.conftest - INFO -


================================ 1 passed in 24.06s =================================
```
