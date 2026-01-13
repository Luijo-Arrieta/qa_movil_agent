# Inicio Rápido

Esta guía te permitirá ejecutar tu primera prueba automática en **5 minutos** (asumiendo que ya tienes todo instalado).

> **¿No tienes todo instalado?** Ve primero a [Prerequisitos](05-prerequisites.md) y luego a la guía de instalación de tu sistema operativo.

## Paso 1: Abrir la Terminal

### En Windows

1. Presiona las teclas `Windows + R` al mismo tiempo
2. Escribe `cmd` y presiona Enter
3. Navega a la carpeta del proyecto escribiendo:

```bash
cd D:\Imagine\qa_movil_agent
```

### En Ubuntu/Linux

1. Presiona `Ctrl + Alt + T` para abrir la terminal
2. Navega a la carpeta del proyecto:

```bash
cd ~/qa_movil_agent
```

## Paso 2: Verificar que el Entorno está Activo

Escribe este comando y presiona Enter:

```bash
poetry env info
```

**Resultado esperado:** Deberías ver información sobre el entorno virtual de Python. Si ves un error, ejecuta:

```bash
poetry install
```

## Paso 3: Iniciar el Emulador Android

Abre una **nueva terminal** (deja la anterior abierta) y ejecuta:

```bash
emulator -avd nombre_de_tu_emulador
```

> **¿No sabes el nombre de tu emulador?** Ejecuta `emulator -list-avds` para ver los disponibles.

**Resultado esperado:** Se abrirá una ventana con un celular Android virtual. Espera a que cargue completamente (aparecerá la pantalla de inicio).

## Paso 4: Iniciar Appium

Abre **otra terminal nueva** y ejecuta:

```bash
appium --use-plugins=all
```

**Resultado esperado:** Verás mensajes como:

```
[Appium] Welcome to Appium v2.x.x
[Appium] Appium REST http interface listener started on http://0.0.0.0:4723
```

> **Importante:** No cierres esta terminal. Appium debe seguir corriendo.

## Paso 5: Ejecutar la Prueba

Vuelve a la **primera terminal** (donde estás en la carpeta del proyecto) y ejecuta:

```bash
# Ejecutar ejemplo funcional con AITestRunner (recomendado para empezar)
poetry run pytest tests/specs/examples/test_example.py::TestAIAgentExample::test_login_flow_example -v

# O ejecutar todos los ejemplos funcionales
poetry run pytest tests/specs/examples/test_example.py -v

# O ejecutar test de integración del proyecto
poetry run pytest tests/specs/test_ui_parser_integration.py::TestUIParserIntegration::test_parse_login_screen_from_real_app -v

# O ejecutar todos los tests de specs
poetry run pytest tests/specs/ -v
```

**Resultado esperado:**

```
tests/specs/test_ui_parser_integration.py::TestUIParserIntegration::test_parse_login_screen_from_real_app PASSED

========================= 1 passed in 15.62s =========================
```

## Paso 6: Ver el Reporte

Genera el reporte visual ejecutando:

```bash
poetry run python scripts/generate_report.py
```

Luego abre el archivo `reports/allure-report.html` en tu navegador. Verás:

- Screenshots de la pantalla del celular
- XML con la estructura de la pantalla
- Resultado de cada paso de la prueba

## ¿Algo salió mal?

### Error: "No se puede conectar a Appium"

**Causa:** Appium no está corriendo o está en otro puerto.

**Solución:**
1. Verifica que la terminal de Appium siga abierta
2. Verifica que diga "listener started on http://0.0.0.0:4723"

### Error: "Dispositivo no encontrado"

**Causa:** El emulador no está corriendo o no está conectado.

**Solución:**
1. Verifica que el emulador esté abierto y haya cargado completamente
2. Ejecuta `adb devices` - deberías ver algo como:

```
List of devices attached
emulator-5554   device
```

### Error: "App Package: N/A"

**Causa:** No está configurada la aplicación a probar.

**Solución:**
1. Abre el archivo `.env.local` (o créalo si no existe)
2. Agrega la ruta a tu APK:

```
ANDROID_APP_PATH=D:/ruta/a/tu/app.apk
```

### Error: "poetry: command not found"

**Causa:** Poetry no está instalado o no está en el PATH.

**Solución:** Ve a [Prerequisitos](05-prerequisites.md) y sigue las instrucciones de instalación de Poetry.

## Siguiente Paso

Ahora que ejecutaste tu primera prueba, puedes:

1. [Aprender los términos técnicos](02-glossary.md) - Entender qué significa cada cosa
2. [Crear tus propias pruebas](06-creating-tests.md) - Escribir pruebas para tu aplicación
