# AutoDroid-AI Agent

Agente de IA autónomo para ejecutar pruebas móviles en Android. Recibe objetivos y pasos en lenguaje natural, analiza la UI de la aplicación y ejecuta acciones automáticamente sin necesidad de escribir selectores manualmente.

## 🎯 Características

- **Autonomía completa**: El agente decide qué acciones ejecutar basándose en el contexto de la pantalla
- **Lenguaje natural**: Define tus pruebas en español (o cualquier idioma) sin código complejo
- **Self-healing**: Sistema de reintentos automáticos cuando algo falla
- **Soporte multi-IA**: Compatible con OpenAI GPT-4o y Anthropic Claude 3.5 Sonnet
- **UIParser inteligente**: Filtra y simplifica la UI para consumo eficiente por LLMs

## 🏗️ Arquitectura

```
Test Runner → UIParser → AI Orchestrator → Agent Tools → Appium
```

1. **Test Runner**: Orquesta el flujo completo y maneja reintentos
2. **UIParser**: Parsea XML de Appium y genera representación JSON simplificada
3. **AI Orchestrator**: Analiza la UI y decide qué acciones ejecutar
4. **Agent Tools**: Ejecuta acciones de alto nivel en Appium
5. **Appium**: Controla el dispositivo Android

## 📋 Requisitos

- Python 3.8+
- Poetry (gestor de dependencias)
- Appium Server corriendo (puerto 4723 por defecto)
- Dispositivo Android o emulador conectado
- API Key de OpenAI o Anthropic

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
```bash
poetry shell
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
AI_PROVIDER=openai  # o "anthropic"

# API Keys
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...

# Configuración de Appium
APPIUM_SERVER_URL=http://localhost:4723
ANDROID_DEVICE_NAME=emulator-5554

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

### Ejemplo básico

```python
from src.test_runner import AITestRunner

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

```bash
# Todos los tests (dentro del entorno de Poetry)
poetry run pytest

# O si ya estás en el shell de Poetry:
pytest

# Tests específicos
poetry run pytest tests/test_example.py

# Con verbose
poetry run pytest -v

# Con timeout
poetry run pytest --timeout=300
```

## 📚 Componentes Principales

### UIParser (`src/ui_parser.py`)

Parsea el XML de `page_source` y genera una lista JSON simplificada de elementos interactuables:

```python
from src.ui_parser import UIParser

parser = UIParser()
elements = parser.parse_screen(xml_source)
# Retorna: [{"id": 1, "role": "button", "label": "Ingresar", ...}]
```

### Agent Tools (`src/agent_tools.py`)

Herramientas de alto nivel para interactuar con Appium:

```python
from src.agent_tools import AppiumSkills

skills = AppiumSkills(driver, ui_parser)
skills.touch_element_by_id(1)  # Clic por ID
skills.fill_field_by_id(2, "texto")  # Escribir por ID
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

### Error: "OPENAI_API_KEY no está configurada"
- Verifica que el archivo `.env` existe y contiene la API key correcta

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
- OpenAI y Anthropic por los modelos de IA
- La comunidad de testing automatizado

