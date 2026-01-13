# AutoDroid-AI Agent

Agente de IA autónomo para ejecutar pruebas móviles en Android. Recibe objetivos y pasos en lenguaje natural, analiza la UI de la aplicación y ejecuta acciones automáticamente sin necesidad de escribir selectores manualmente.

## 🎯 Características

- **Autonomía completa**: El agente decide qué acciones ejecutar basándose en el contexto de la pantalla
- **Lenguaje natural**: Define tus pruebas en español (o cualquier idioma) sin código complejo
- **Self-healing**: Sistema de reintentos automáticos cuando algo falla
- **Soporte multi-IA**: Compatible con OpenAI GPT-4o, Anthropic Claude 3.5 Sonnet y DeepSeek
- **UIParser inteligente**: Filtra y simplifica la UI para consumo eficiente por LLMs

## 🏗️ Arquitectura

```
Test Runner → UIParser → AI Orchestrator → Agent Tools → Appium
```

1. **Test Runner**: Orquesta el flujo completo y maneja reintentos
2. **UIParser**: Parsea XML de Appium y extrae propiedades reales de Android para elementos interactuables
3. **AI Orchestrator**: Analiza la UI y decide qué acciones ejecutar (usa formato TOON para eficiencia de tokens)
4. **Agent Tools**: Ejecuta acciones de alto nivel en Appium usando XPath
5. **Appium**: Controla el dispositivo Android

## 📋 Requisitos

- Python 3.8+
- Poetry (gestor de dependencias)
- Appium Server corriendo (puerto 4723 por defecto)
- Dispositivo Android o emulador conectado
- API Key de OpenAI, Anthropic o DeepSeek
- Allure CLI (opcional, para generar reportes HTML)

## 🚀 Instalación

1. Instalar Poetry (si no lo tienes instalado):
```bash
curl -sSL https://install.python-poetry.org | python3 -
```

2. Clonar el repositorio:
```bash
git clone git@github.com:Luijo-Arrieta/qa_movil_agent.git
cd Gofixi_Agent
```

3. Instalar dependencias con Poetry:
```bash
poetry install
```

4. Activar el entorno virtual de Poetry:

**En Linux/Ubuntu:**
```bash
poetry shell
```

**En Windows/PowerShell (Poetry 2.0.0+):**
```powershell
# Opción 1: Usar poetry env activate (recomendado)
poetry env activate
# Copia y ejecuta el comando que muestra (ej: & "C:\...\activate.ps1")

# Opción 2: Instalar el plugin de shell para usar poetry shell
poetry self add poetry-plugin-shell
poetry shell

# Opción 3: Usar poetry run sin activar (más simple)
poetry run pytest  # Ejecuta comandos directamente en el entorno
```

**Verificar que el entorno está activado:**
```bash
# Ver la ruta de Python (debe apuntar al venv)
where python        # Windows
which python        # Linux

# O verificar la variable de entorno
echo $env:VIRTUAL_ENV    # PowerShell
echo $VIRTUAL_ENV        # Linux

# O ver la ruta completa del Python activo
python -c "import sys; print(sys.executable)"
```

5. Configurar variables de entorno:
```bash
cp .env.example .env
# Editar .env con tus API keys y configuración
```

## ⚙️ Configuración

Edita el archivo `.env` con tus valores:

```env
# Proveedor de IA
AI_PROVIDER=openai  # o "anthropic" o "deepseek"

# API Keys
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
DEEPSEEK_API_KEY=sk-...

# Configuración de Appium
APPIUM_SERVER_URL=http://localhost:4723
ANDROID_DEVICE_NAME=emulator-5554
ANDROID_UDID=emulator-5554  # Opcional: UDID del dispositivo (por defecto usa ANDROID_DEVICE_NAME)

# Configuración de la App Android
# Opción 1: Usar ruta al APK (recomendado para instalar la app)
ANDROID_APP_PATH=D:/Imagine/gofixi/utils/apk/2025-12-19-cliente.apk
# Opción 2: Usar package y activity (si la app ya está instalada)
ANDROID_APP_PACKAGE=com.imagineapps.gofixiicliente
ANDROID_APP_ACTIVITY=.MainActivity

# Configuración avanzada de Appium
ANDROID_AUTOMATION_NAME=UiAutomator2
ANDROID_AUTO_GRANT_PERMISSIONS=true
ANDROID_IGNORE_HIDDEN_API_POLICY_ERROR=true
ANDROID_DISABLE_WINDOW_ANIMATION=true

# Timeouts
# DEFAULT_WAIT_TIMEOUT: en MINUTOS (10 = 10 minutos)
# IMPLICIT_WAIT: en SEGUNDOS (5 = 5 segundos)
DEFAULT_WAIT_TIMEOUT=10
IMPLICIT_WAIT=5
```

## 🛠️ Preparativos previos (setup local)

Antes de correr las pruebas de la app, asegúrate de tener listos los recursos esenciales en tu máquina local.

### 1. Dispositivos Android

Verifica que tienes conectados (o disponibles en emulador) los dispositivos Android necesarios.

**Para listar los dispositivos disponibles ejecuta:**
```bash
adb devices
```
Esto mostrará los dispositivos/emuladores conectados. Deberías ver una salida como:
```
List of devices attached
emulator-5554   device
```

#### Iniciar un emulador Android
Si no ves ningún emulador activo, puedes lanzar uno manualmente. Para ver los emuladores instalados:
```bash
$ANDROID_HOME/emulator/emulator -list-avds
```
Luego, para iniciarlo:
```bash
$ANDROID_HOME/emulator/emulator -avd NOMBRE_DEL_AVD
```
O en sistemas con AVD Manager en el path:
```bash
emulator -avd NOMBRE_DEL_AVD
```

### 2. Iniciar Appium con todos los plugins habilitados

Asegúrate de tener Appium instalado. Si no lo tienes:
```bash
npm install -g appium
```

Para listar los plugins disponibles (opcional):
```bash
appium plugin list
```

Para instalar (por ejemplo) el plugin de inspector, puedes utilizar:
```bash
appium plugin install --source=npm appium-inspector-plugin
```

**Para iniciar Appium y activar todos los plugins instalados:**
```bash
appium --use-plugins=all
```
En bash/shell, simplemente ejecuta ese comando en una terminal antes de correr tus pruebas.

> **Nota:** Si necesitas activar solo plugins específicos:
```bash
appium --use-plugins=plugin1,plugin2
```

Ya con Appium corriendo y el dispositivo/emulador disponible, puedes comenzar a ejecutar los tests.

## 💻 Uso

### 1. Iniciar el Entorno

```bash
# Terminal 1: Iniciar emulador Android
emulator -avd phone_test -wipe-data -no-snapshot-load

# Terminal 2: Iniciar Appium Server
appium --use-plugins=inspector --allow-cors

# Terminal 3: Verificar conexión
adb devices   # Debe mostrar: emulator-5554   device
```

### Ejemplo básico

**Opción 1: Crear un archivo Python (recomendado)**

Crea un archivo `ejemplo_test.py`:

```python
from appium import webdriver
from src.test_runner import AITestRunner
from src.config import Config

# Configurar el driver de Appium
config = Config()
capabilities = {
    "platformName": "Android",
    "deviceName": config.ANDROID_DEVICE_NAME,
    "appPackage": "com.tu.app",
    "appActivity": ".MainActivity"
}
driver = webdriver.Remote(config.APPIUM_SERVER_URL, capabilities)

# Crear runner
runner = AITestRunner(driver=driver, objective="Realizar login")

# Definir plan de prueba
test_plan = [
    "Abrir la app y esperar a ver la pantalla de login",
    "Ingresar usuario 'cliente@demo.com'",
    "Ingresar password '123456'",
    "Tocar botón Ingresar",
    "Verificar que aparezca el texto 'Bienvenido'",
]

# Ejecutar
success = runner.run_test_plan(test_plan)
print(f"Test {'exitoso' if success else 'falló'}")

# Cerrar driver
driver.quit()
```

Ejecutar el archivo:
```bash
poetry run python ejemplo_test.py
```

**Opción 2: Python interactivo**

Para ejecutar código interactivamente en la terminal:

```bash
# Activar Python con Poetry
poetry run python

# O si ya activaste el entorno virtual:
python
```

Luego dentro de Python:
```python
>>> from src.test_runner import AITestRunner
>>> # ... resto del código
```

### Con pytest

```python
import pytest
from src.test_runner import AITestRunner

@pytest.mark.usefixtures("driver_setup")
def test_login(driver_setup):
    runner = AITestRunner(driver=driver_setup)
    test_plan = [
        "Ingresar usuario 'test@example.com'",
        "Ingresar password 'password123'",
        "Tocar botón Ingresar",
    ]
    assert runner.run_test_plan(test_plan)
```

## 🧪 Ejecutar Tests

### Estructura de Tests

```
tests/
├── conftest.py              # Configuración compartida (markers, logging)
├── unit/                    # Tests UNITARIOS (no requieren Appium)
│   ├── conftest.py          # Fixtures para tests unitarios
│   ├── test_ui_parser.py    # Tests de UIParser
│   ├── test_agent_tools.py  # Tests de AppiumSkills (con mocks)
│   ├── test_ai_orchestrator.py  # Tests de AIOrchestrator (con mocks)
│   └── test_test_runner.py  # Tests de AITestRunner (con mocks)
└── specs/                   # Tests E2E/INTEGRACIÓN (requieren Appium + dispositivo)
    ├── conftest.py          # Fixtures E2E (driver_setup, Allure)
    ├── test_ui_parser_integration.py  # Tests del proyecto
    └── examples/
        └── spec_example.py  # Tests de usuario (usar prefijo spec_*.py)
```

**Convención de Nombres:**
- `test_*.py` - Tests del proyecto (framework, componentes internos)
- `spec_*.py` - Tests de usuario (especificaciones de funcionalidad de la app)

### Comandos de Test

```bash
# ═══════════════════════════════════════════════════════════════
# TESTS UNITARIOS (rápidos, no requieren Appium ni dispositivo)
# ═══════════════════════════════════════════════════════════════
poetry run pytest tests/unit/ -v

# Test unitario específico
poetry run pytest tests/unit/test_agent_tools.py -v

# ═══════════════════════════════════════════════════════════════
# TESTS DE INTEGRACIÓN (requieren Appium + emulador/dispositivo)
# ═══════════════════════════════════════════════════════════════
poetry run pytest tests/specs/ -v

# Solo tests de usuario (spec_*.py)
poetry run pytest tests/specs/spec_*.py -v

# Solo tests del proyecto (test_*.py)
poetry run pytest tests/specs/test_*.py -v

# ═══════════════════════════════════════════════════════════════
# TODOS LOS TESTS
# ═══════════════════════════════════════════════════════════════
poetry run pytest -v

# Con cobertura de código
poetry run pytest tests/unit/ --cov=src --cov-report=html

# Con timeout (para tests largos)
poetry run pytest --timeout=300
```

### Diferencia entre Unit y Specs

| Característica | `tests/unit/` | `tests/specs/` |
|---------------|---------------|----------------|
| Requiere Appium | ❌ No | ✅ Sí |
| Requiere dispositivo | ❌ No | ✅ Sí |
| Velocidad | ⚡ Muy rápido | 🐢 Lento |
| Usa mocks | ✅ Sí | ❌ No (real) |
| Ideal para | CI/CD, desarrollo | Validación E2E |

> **Nota:** En Windows con Poetry 2.0.0+, es más simple usar `poetry run` antes de cada comando en lugar de activar el entorno manualmente.

## 📊 Reportes con Allure

El proyecto usa Allure para generar reportes HTML interactivos con screenshots y logs detallados.

### Configurar Allure CLI

**Windows:** Agrega Allure al PATH del sistema o usa la ruta completa:

```powershell
# Opción 1: Agregar al PATH temporalmente (solo esta sesión)
$env:Path += ";D:\Imagine\allure-2.36.0\allure-2.36.0\bin"

# Opción 2: Agregar permanentemente al PATH del sistema
# Ve a: Panel de Control > Sistema > Configuración avanzada > Variables de entorno
# Agrega: D:\Imagine\allure-2.36.0\allure-2.36.0\bin al PATH del Usuario o del Sistema
```

**Verificar instalación:**
```bash
allure --version
```

**Si agregaste Allure al PATH pero no funciona en tu terminal:**

Las terminales abiertas antes de agregar la ruta no recargan el PATH automáticamente. Soluciones:

```powershell
# Opción 1: Recargar PATH manualmente (en la terminal actual)
$env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
allure --version

# Opción 2: Cerrar y reabrir la terminal (recomendado)
# Esto carga automáticamente el PATH actualizado

# Opción 3: Usar el script helper
.\scripts\reload_path.ps1
```

### Generar reportes

Después de ejecutar tests:

```bash
# Opción 1: Usar el script (recomendado)
poetry run python scripts/generate_report.py

# Opción 2: Usar el CLI directamente
allure generate reports/allure-results -o reports/allure-report --clean

# Opción 3: Servir el reporte interactivo (se abre en el navegador)
allure serve reports/allure-results
```

El reporte se genera en `reports/allure-report/index.html` - ábrelo en tu navegador para ver los resultados.

El reporte incluye:

- Screenshots automáticos en fallos
- Page source XML adjunto
- Logs detallados de cada paso
- Tiempos de ejecución
- Historial de tests

---

## 📚 Componentes Principales

### UIParser (`src/ui_parser.py`)

Parsea el XML de `page_source` y extrae propiedades reales de Android para elementos interactuables:

```python
from src.ui_parser import UIParser

parser = UIParser()
elements = parser.parse_screen(xml_source)
# Retorna: [{"resource-id": "com.app:id/btn", "content-desc": "", "class": "android.widget.Button",
#           "index": "0", "xpath": "//android.widget.Button[@index='0']", "bounds": "[0,100][720,200]",
#           "clickable": "true", "displayed": "true", "enabled": "true", "password": "false",
#           "scrollable": "false", "text": "Ingresar", "hint": ""}]

# Criterios de inclusión (focusable="true" es REQUERIDO):
# - clickable="true" con información útil (text, content-desc, o resource-id)
# - Elementos EditText (inputs) - siempre incluidos
# - ImageView + clickable (botones de imagen) - siempre incluidos
```

### Agent Tools (`src/agent_tools.py`)

Herramientas de alto nivel para interactuar con Appium:

```python
from src.agent_tools import AppiumSkills

skills = AppiumSkills(driver, ui_parser)
skills.touch_element_by_xpath(xpath)  # Clic por XPath
skills.fill_field_by_xpath(xpath, "texto")  # Escribir por XPath
skills.scroll("down")  # Scroll
skills.go_back()  # Botón atrás
skills.assert_screen_contains("Bienvenido")  # Verificar texto
```

### AI Orchestrator (`src/ai_orchestrator.py`)

Orquesta las decisiones de IA:

```python
from src.ai_orchestrator import AIOrchestrator

orchestrator = AIOrchestrator()
decision = orchestrator.decide_next_action(
    ui_elements=elements,
    current_step="Ingresar usuario",
    action_history=[],
)
```

## 🔧 Troubleshooting

### Error: "API_KEY no está configurada"
- Verifica que el archivo `.env` existe y contiene la API key correcta para el proveedor seleccionado
- Para OpenAI: `OPENAI_API_KEY`
- Para Anthropic: `ANTHROPIC_API_KEY`
- Para DeepSeek: `DEEPSEEK_API_KEY`

### Error: "No se puede conectar a Appium"
- Asegúrate de que Appium Server está corriendo: `appium`
- Verifica la URL en `.env`: `APPIUM_SERVER_URL=http://localhost:4723`

### Error: "Dispositivo no encontrado"
- Lista dispositivos: `adb devices`
- Actualiza `ANDROID_DEVICE_NAME` en `.env`

### El agente no encuentra elementos
- Verifica que la app está abierta y visible
- Revisa los logs para ver qué elementos detectó el UIParser
- Intenta hacer scroll si el elemento está fuera de la pantalla

## 📝 Notas

- El agente funciona mejor con apps que tienen texto descriptivo en los elementos
- Para elementos sin texto, el agente usa `content-desc` o `resource-id`
- El sistema de reintentos intenta hasta 3 veces cada paso antes de fallar
- Los logs detallados ayudan a entender qué decisiones toma la IA

## 🤝 Contribuir

Las contribuciones son bienvenidas. Por favor:

1. Fork el proyecto
2. Crea una rama para tu feature (`git checkout -b feature/AmazingFeature`)
3. Commit tus cambios (`git commit -m 'Add some AmazingFeature'`)
4. Push a la rama (`git push origin feature/AmazingFeature`)
5. Abre un Pull Request

## 📄 Licencia

Este proyecto está bajo la Licencia MIT.

## 🙏 Agradecimientos

- Appium por la infraestructura de automatización móvil
- OpenAI, Anthropic y DeepSeek por los modelos de IA
- La comunidad de testing automatizado

