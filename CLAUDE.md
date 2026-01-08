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
2. UIParser parses XML and generates simplified JSON with interactable elements (assigns temporary IDs)
3. AI Orchestrator converts elements to **TOON format** (30-60% fewer tokens) and sends to LLM
4. LLM selects element by ID and returns tool to use (e.g., `touch_element_by_id(2)`)
5. Agent Tools queries UIParser for real XPath by ID, then executes action via Appium

**Key Components:**
- `src/ui_parser.py` - Transforms raw Appium XML into simplified JSON/TOON for LLMs. Maps temporary IDs to XPaths.
- `src/agent_tools.py` - High-level Appium interactions (click, fill, scroll, assert)
- `src/ai_orchestrator.py` - LLM integration (OpenAI/Anthropic) with function calling. Uses TOON format for token efficiency.
- `src/test_runner.py` - Orchestrates test execution with retry system (max 3 attempts per step)
- `src/config.py` - Environment configuration. Loads `.env` then `.env.local` (override)

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
        └── spec_example.py  # User specs (use spec_*.py prefix)
```

**Naming Convention:**
- `test_*.py` - Tests del proyecto (framework, componentes internos)
- `spec_*.py` - Tests de usuario (especificaciones de funcionalidad de la app)

## Environment Setup

Copy `.env.example` to `.env.local` and configure:
- `AI_PROVIDER`: "openai" or "anthropic"
- `OPENAI_API_KEY` / `ANTHROPIC_API_KEY`
- `ANDROID_APP_PATH`: Path to APK (recommended) OR `ANDROID_APP_PACKAGE` + `ANDROID_APP_ACTIVITY`
- `ANDROID_DEVICE_NAME`: Device/emulator ID (check with `adb devices`)

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

### JSON Format (internal)
Elements returned by UIParser follow this structure:
```json
{"id": 1, "role": "button|input|checkbox", "label": "text", "checked": null|true|false}
```

Label priority: `resource-id` > `content-desc` > `text` > `hint`

### TOON Format (for LLMs)
For communication with LLMs, UIParser can output in **TOON (Token-Oriented Object Notation)** format, which reduces token consumption by 30-60% compared to JSON.

```toon
[3	]{id	role	label	checked}:
  0	button	Login	null
  1	input	Email	null
  2	input	Password	null
```

**Why TOON?**
- Uses tabular format with headers, reducing repetition
- Tab-separated values for maximum token efficiency
- Maintains full data fidelity (lossless)
- See: https://github.com/toon-format/toon

**Methods:**
- `parser.elements_to_toon(elements)` - Convert element list to TOON
- `parser.parse_screen_to_toon(xml)` - Parse XML directly to TOON

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
test_plan = [
    "Abrir app Customer (com.example.customer)",
    "Hacer login con email 'user@test.com' y password '123456'",
    "Crear una solicitud de servicio",
    "Cambiar a app Technical (com.example.technical) manteniendo Customer en background",
    "Hacer login como técnico",
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
