# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AutoDroid-AI Agent: Autonomous AI agent for mobile testing on Android. It receives objectives and steps in natural language, analyzes the app's UI, and executes actions automatically without manually writing selectors.

## Documentation

Extended documentation for non-technical users is available in `docs/`:
- [Quick Start](docs/01-quick-start.md) - Run your first test in 5 minutes
- [Glossary](docs/02-glossary.md) - Technical terms explained simply
- [Windows Installation](docs/03-installation-windows.md) - Step-by-step guide
- [Ubuntu Installation](docs/04-installation-ubuntu.md) - Step-by-step guide
- [Prerequisites](docs/05-prerequisites.md) - Required tools and setup
- [Creating Tests](docs/06-creating-tests.md) - Live coding tutorial

## Architecture

```
Test Runner → UIParser → AI Orchestrator → Agent Tools → Appium
```

**Flow:**
1. Test Runner gets `page_source` (XML) from Appium driver
2. UIParser parses XML and extracts interactable elements with real Android properties
3. AI Orchestrator converts elements to **TOON format** (30-60% fewer tokens) and sends to LLM
4. LLM analyzes elements and constructs selectors using properties (resource-id, content-desc, class, xpath, etc.)
5. Agent Tools executes actions via Appium using the constructed selectors

**Key Components:**
- `src/ui_parser.py` - Transforms raw Appium XML into structured data with real Android properties for LLMs. Generates hierarchical XPaths similar to Appium Inspector (short, readable paths).
- `src/agent_tools.py` - High-level Appium interactions (click, fill, scroll, assert)
- `src/ai_orchestrator.py` - LLM integration (OpenAI/Anthropic/DeepSeek) with function calling. Uses TOON format for token efficiency.
- `src/test_runner.py` - Orchestrates test execution with intelligent retry system (max 3 attempts per step)
- `src/config.py` - Environment configuration. Loads `.env` then `.env.local` (override)

## Error Handling and Retry System

The test runner implements an intelligent error handling system that distinguishes between recoverable and non-recoverable errors.

### Recoverable Errors (Will Retry)

These errors are temporary and may resolve on retry:
- `TimeoutException` - Temporary timeouts
- `NoSuchElementException` - Element not found (may appear later)
- `ElementNotInteractableException` - Element not interactable (state may change)
- `StaleElementReferenceException` - Stale element reference (can be resolved)
- `WebDriverException` - Some temporary driver errors (except session errors)

**Behavior:** The system will retry up to `max_retries` (default: 3) times with a 2-second delay between attempts.

### Non-Recoverable Errors (Fail Immediately)

These errors indicate programming/configuration issues and won't be fixed by retrying:
- `ValueError` - Invalid data or structure
- `KeyError` - Missing dictionary key
- `TypeError` - Incorrect types
- `AttributeError` - Missing attribute
- `SyntaxError` - Syntax errors
- `NameError` - Undefined name
- `ImportError` - Import errors
- `WebDriverException` with session errors (e.g., "session not created", "invalid session id")

**Behavior:** The test fails immediately without retries, providing clear error messages indicating the issue needs to be fixed in code/configuration.

### Implementation

The `_is_recoverable_error()` function in `src/test_runner.py` classifies errors automatically. When a non-recoverable error occurs, the test runner:
1. Logs the error with full traceback
2. Indicates it's a non-recoverable error
3. Fails immediately without wasting time on retries
4. Provides guidance to check configuration, data structure, or code

## Commands

```bash
# Install dependencies
poetry install

# Run all tests
poetry run pytest

# Run only unit tests (fast, no Appium needed)
poetry run pytest tests/unit -v

# Run only E2E/Spec tests (requires Appium + device)
poetry run pytest tests/specs -v

# Run only user specs (spec_*.py files)
poetry run pytest tests/specs/spec_*.py -v

# Run only project tests (test_*.py files)
poetry run pytest tests/unit/test_*.py -v

# Run with verbose output
poetry run pytest -v

# Run by marker
poetry run pytest -m unit
poetry run pytest -m integration
```

## Test Structure

```
tests/
├── conftest.py              # Shared config (markers, logging)
├── unit/                    # Unit tests (no Appium required, uses mocks)
│   ├── conftest.py          # Unit test fixtures
│   ├── test_ui_parser.py    # UIParser unit tests
│   ├── test_agent_tools.py  # AppiumSkills unit tests (mocked driver)
│   ├── test_ai_orchestrator.py  # AIOrchestrator unit tests (mocked LLM APIs)
│   └── test_test_runner.py  # AITestRunner unit tests (mocked components)
└── specs/                   # E2E tests (require Appium + device)
    ├── conftest.py          # E2E fixtures (driver_setup, Allure)
    ├── test_ui_parser_integration.py  # Project integration tests
    └── examples/            # User test examples
        ├── test_example.py  # ✅ Functional examples using AITestRunner
        └── spec_example.py  # User specs (use spec_*.py prefix)
```

**Naming Convention:**
- `test_*.py` - Tests del proyecto (framework, componentes internos)
- `spec_*.py` - Tests de usuario (especificaciones de funcionalidad de la app)

## Environment Setup

Copy `.env.example` to `.env.local` and configure:

**Required:**
- `AI_PROVIDER`: "openai", "anthropic" or "deepseek"
- `OPENAI_API_KEY` / `ANTHROPIC_API_KEY` / `DEEPSEEK_API_KEY`
- `ANDROID_APP_PATH`: Path to APK (recommended) OR `ANDROID_APP_PACKAGE` + `ANDROID_APP_ACTIVITY`
- `ANDROID_DEVICE_NAME`: Device/emulator ID (check with `adb devices`)

**Optional (for test examples):**
- `TEST_USER_EMAIL`: Test user email for login tests (default: "cliente@demo.com")
- `TEST_USER_PASSWORD`: Test user password for login tests (default: "123456")

### Using Test Credentials in Tests

Test credentials can be accessed via `Config` class:

```python
from src.config import Config

# Get credentials from environment variables
test_email = Config.TEST_USER_EMAIL
test_password = Config.TEST_USER_PASSWORD

# Use in test plan
test_plan = [
    f"Ingresar usuario '{test_email}'",
    f"Ingresar password '{test_password}'",
]
```

This allows you to change credentials without modifying test code - just update `.env.local`.

## Working Examples

A fully functional example file is available at `tests/specs/examples/test_example.py` demonstrating:

### Example 1: Login Flow with AITestRunner

```python
from src.test_runner import AITestRunner
from src.config import Config

def test_login_flow_example(self, driver_setup):
    objective = "Realizar login en la aplicación con credenciales de prueba"
    
    test_email = Config.TEST_USER_EMAIL
    test_password = Config.TEST_USER_PASSWORD
    
    runner = AITestRunner(driver=driver_setup, objective=objective)
    
    test_plan = [
        "Esperar a ver la pantalla de login",
        f"Ingresar usuario '{test_email}'",
        f"Ingresar password '{test_password}'",
        "Tocar botón Ingresar",
        "Verifica que se inició la sesión",
    ]
    
    success = runner.run_test_plan(test_plan)
    assert success, "El plan de prueba no se completó exitosamente"
```

### Example 2: Simple Navigation

```python
def test_simple_navigation_example(self, driver_setup):
    runner = AITestRunner(driver=driver_setup)
    
    test_plan = [
        "Abrir el menú principal",
        "Seleccionar la opción 'Configuración'",
        "Verificar que se abra la pantalla de configuración",
    ]
    
    success = runner.run_test_plan(test_plan)
    assert success, "La navegación no se completó exitosamente"
```

**Key Benefits of AITestRunner:**
- No need to manually parse UI or write XPath selectors
- Natural language test plans are easy to read and maintain
- Automatic retry logic handles transient errors
- Built-in loop detection prevents infinite retries

## Pre-requisites for Integration Tests

```bash
# Terminal 1: Start Android emulator
emulator -avd <AVD_NAME>

# Terminal 2: Start Appium server
appium --use-plugins=all

# Verify device connection
adb devices
```

## Test Markers

- `@pytest.mark.unit` - Unit tests (no Appium required)
- `@pytest.mark.integration` - Integration tests (requires Appium + device)
- `@pytest.mark.slow` - Long-running tests

## UIParser Output Format

### Internal Structure (JSON)
UIParser returns elements with a consistent structure using `{id, attrs}`:

```json
{
  "id": 0,
  "attrs": [
    {"name": "content-desc", "value": "Login Button"},
    {"name": "class", "value": "android.widget.Button"},
    {"name": "xpath", "value": "//android.widget.Button[@content-desc=\"Login Button\"]"},
    {"name": "bounds", "value": "[100,200][300,250]"},
    {"name": "clickable", "value": "true"},
    {"name": "enabled", "value": "true"},
    {"name": "displayed", "value": "true"}
  ]
}
```

**Why this structure?**
- `attrs` is always a list of `{name, value}` objects (consistent schema)
- Only non-empty attributes are included (except booleans)
- Easy to extend without breaking structure

**Inclusion Criteria (focusable="true" is REQUIRED):**
- `clickable="true"` with useful info (text, content-desc, or resource-id)
- `EditText` elements (inputs) - always included
- `ImageView` + clickable (image buttons) - always included

### XPath Generation (Hierarchical)

UIParser generates **short, hierarchical XPaths** similar to Appium Inspector:

**Strategy:**
- When an element has a unique identifier (resource-id, content-desc, or text), the XPath "restarts" with `//` from that point
- Elements without identifiers continue accumulating the path from their parent with `/`
- This generates concise XPaths that match Appium Inspector's output

**Example:**
```
//android.view.View[@content-desc='Iniciar sesión']/android.view.View[2]/android.widget.EditText
```

Instead of long paths from root:
```
//hierarchy/android.widget.FrameLayout/.../android.view.View[@content-desc='Iniciar sesión']/android.view.View[2]/android.widget.EditText
```

**XPath segment priority:**
1. `resource-id` (most reliable): `tag[@resource-id='value']`
2. `content-desc`: `tag[@content-desc='value']`
3. `text`: `tag[@text='value']`
4. Index (fallback): `tag[index]` (position among siblings of same type)

### TOON Format (for LLMs)
For communication with LLMs, elements are flattened and converted to **TOON (Token-Oriented Object Notation)** format, reducing token consumption by 30-60%.

```toon
[2]{id	content-desc	class	xpath	clickable	enabled}:
  0	Login Button	android.widget.Button	//android.widget.Button[@content-desc="Login Button"]	true	true
  1		android.widget.EditText	//android.view.View[@content-desc="Login"]/android.widget.EditText[1]	true	true
```

**Data Flow:**
1. UIParser generates `{id, attrs: [{name, value}]}` internally with hierarchical XPaths
2. AI Orchestrator flattens to `{id, content-desc, class, ...}` for TOON
3. LLM receives TOON format with attributes as columns

**Why TOON?**
- Uses tabular format with headers, reducing repetition
- Tab-separated values for maximum token efficiency
- Maintains full data fidelity (lossless)
- See: https://github.com/toon-format/toon

## AI Tools Available

The LLM can use these tools via function calling:

### UI Interaction Tools
- `touch_element_by_id(element_id)` - Click element
- `fill_field_by_id(element_id, value)` - Type text in input
- `scroll(direction)` - Scroll up/down
- `go_back()` - Press back button
- `assert_screen_contains(text)` - Verify text presence

### Multi-App Management Tools
For tests requiring multiple apps (e.g., Customer ↔ Technical flows):
- `activate_app(app_package)` - Open/bring app to foreground
- `terminate_app(app_package)` - Close app completely
- `switch_to_app(app_package)` - Switch to app, closing current one (clean state)
- `switch_to_app_keep_background(app_package)` - Switch keeping current in background (fast round-trips)

**App States (Appium):**
| Code | State | Description |
|------|-------|-------------|
| 0 | NOT_INSTALLED | App not installed |
| 1 | NOT_RUNNING | Installed but not running |
| 2 | BACKGROUND_SUSPENDED | Background, suspended |
| 3 | BACKGROUND | Background, active |
| 4 | FOREGROUND | In foreground (visible) |

### Multi-App Test Example

```python
from src.config import Config

# Get credentials from environment variables
test_email = Config.TEST_USER_EMAIL
test_password = Config.TEST_USER_PASSWORD

test_plan = [
    "Abrir app Customer (com.example.customer)",
    f"Hacer login con email '{test_email}' y password '{test_password}'",
    "Crear una solicitud de servicio",
    "Cambiar a app Technical (com.example.technical) manteniendo Customer en background",
    f"Hacer login como técnico con email 'tecnico@demo.com' y password '{test_password}'",
    "Aceptar la solicitud",
    "Volver a app Customer",
    "Verificar que la solicitud fue aceptada",
]
```

## Allure Reporting

Tests use Allure for rich HTML reports with screenshots and XML attachments.

### Run Tests and Generate Report

```bash
# Run tests (results saved to reports/allure-results/)
poetry run pytest

# Generate HTML report (100% Python, no external CLI needed)
poetry run python scripts/generate_report.py

# Open reports/allure-report.html in your browser
```

### Debug Functions for Tests

Import from `tests/specs/conftest.py`:

```python
from tests.specs.conftest import (
    allure_attach_screenshot,    # Attach PNG screenshot
    allure_attach_page_source,   # Attach XML page source
    allure_attach_debug_snapshot # Attach both screenshot + XML
)

# Usage in any test
def test_example(driver_setup):
    driver = driver_setup
    allure_attach_screenshot(driver, "initial_screen")
    allure_attach_page_source(driver, "initial_xml")
    # Or use convenience function for both:
    allure_attach_debug_snapshot(driver, "after_action")
```

### Automatic Failure Screenshots

When a test fails, screenshot and page source XML are automatically captured and attached to the Allure report.
