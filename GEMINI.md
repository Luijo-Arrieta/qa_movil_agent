# GEMINI.md

This file provides guidance to Gemini CLI (gemini.ai/code) when working with code in this repository.

## Project Overview

AutoDroid-AI Agent: Autonomous AI agent for mobile testing on Android. It receives objectives and steps in natural language, analyzes the app's UI, and executes actions automatically without manually writing selectors.

## Architecture

```
Test Runner → UIParser → AI Orchestrator → Agent Tools → Appium
```

**Flow:**
1. Test Runner gets `page_source` (XML) from Appium driver
2. UIParser parses XML and generates simplified JSON with interactable elements (assigns temporary IDs)
3. AI Orchestrator sends JSON to LLM, which decides what action to execute
4. LLM selects element by ID and returns tool to use (e.g., `touch_element_by_id(2)`)
5. Agent Tools queries UIParser for real XPath by ID, then executes action via Appium

**Key Components:**
- `src/ui_parser.py` - Transforms raw Appium XML into simplified JSON for LLMs. Maps temporary IDs to XPaths.
- `src/agent_tools.py` - High-level Appium interactions (click, fill, scroll, assert)
- `src/ai_orchestrator.py` - LLM integration (OpenAI/Anthropic) with function calling for action decisions
- `src/test_runner.py` - Orchestrates test execution with retry system (max 3 attempts per step)
- `src/config.py` - Environment configuration. Loads `.env` then `.env.local` (override)

## Commands

```bash
# Install dependencies
poetry install

# Run all tests
poetry run pytest

# Run specific test file
poetry run pytest tests/test_ui_parser.py

# Run with verbose output
poetry run pytest -v

# Run only unit tests
poetry run pytest -m unit

# Run only integration tests (requires Appium + device)
poetry run pytest -m integration
```

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

## UIParser JSON Format

Elements returned by UIParser follow this structure:
```json
{"id": 1, "role": "button|input|checkbox", "label": "text", "checked": null|true|false}
```

Label priority: `resource-id` > `content-desc` > `text` > `hint`

## AI Tools Available

The LLM can use these tools via function calling:
- `touch_element_by_id(element_id)` - Click element
- `fill_field_by_id(element_id, value)` - Type text in input
- `scroll(direction)` - Scroll up/down
- `go_back()` - Press back button
- `assert_screen_contains(text)` - Verify text presence

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

Import from `tests/conftest.py`:

```python
from tests.conftest import (
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
