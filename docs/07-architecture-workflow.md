## Arquitectura del agente y flujo de ejecución

Esta guía resume **cómo fluye la información** desde las variables de entorno hasta las acciones en la app, y cómo se estructura el **estado global del agente** con `StepContext`.

Se centra en:
- **`Config`** (variables de entorno, single‑app vs multi‑app, límites y timeouts).
- **Specs + `AITestRunner`** (objetivo + `test_plan`).
- **`StepContext`** como estado global del agente por paso.
- **Loop agéntico de 5 fases** y clasificación de errores.

---

## 1. Visión general (foto de alto nivel)

```text
.env / .env.local
    │  (load_dotenv en src/config.py)
    ▼
Config (API keys, Appium, timeouts, modos, límites)
    │
    ▼
pytest + specs (tests/specs/*.py, tests/integration/*.py)
    │    └─ definen: objective + test_plan (lista de pasos en lenguaje natural)
    │
    ▼
driver_setup (fixture) ──► Appium Remote Driver (capabilities desde Config)
    │
    ▼
AITestRunner (src/test_runner.py)
    ├─ Valida Config
    ├─ Crea UIParser
    ├─ Crea AppiumSkills (Agent Tools)
    └─ Crea AIOrchestrator (proveedor IA según Config)
         │
         ▼
  run_test_plan(test_plan)
    └─ Para cada paso:
         └─ _execute_step(...)  + StepContext
              F1: AppiumSkills.get_screen_tree_stable()  → XML estable
              F2: UIParser.parse_screen()                → ui_elements (list[dict])
              F3: AIOrchestrator.decide_next_action()    → usa StepContext + TOON
              F4: _execute_single_tool_call()            → AppiumSkills ejecuta acción
              F5: AppiumSkills.wait_for_ui_stable()      → espera de estabilidad
              + Detección de loops / acciones repetidas
```

Relación entre componentes:

```text
pytest/spec  ──►  AITestRunner  ──►  StepContext  ──►  AIOrchestrator  ──►  LLM
   ▲                    │                ▲                     │
   │                    ▼                │                     │
driver_setup      AppiumSkills  ◄────────┘                     │
   ▲                    │                                      │
   │                    ▼                                      │
   └──────────────  UIParser  ◄─ XML desde Appium driver  ◄────┘
```

---

## 2. `Config` y modos de proyecto (single‑app / multi‑app)

- **Carga de variables** (`src/config.py`):
  - `load_dotenv(".env")` + `load_dotenv(".env.local", override=True)`.
  - `.env.local` sobreescribe `.env`.
  - Atributos de `Config` se rellenan con `os.getenv(...)` al primer `from src.config import Config`.

- **Grupos clave de configuración**:
  - **Proveedor y modelos de IA**: `AI_PROVIDER`, `OPENAI_MODEL`, `ANTHROPIC_MODEL`, `DEEPSEEK_MODEL`.
  - **Appium / dispositivo**: `APPIUM_SERVER_URL`, `ANDROID_DEVICE_NAME`, `ANDROID_UDID`, `ANDROID_APP_PACKAGE`, `ANDROID_APP_ACTIVITY`, `ANDROID_APP_PATH`, flags de permisos/animaciones.
  - **Timeouts / estabilidad**: `DEFAULT_WAIT_TIMEOUT`, `IMPLICIT_WAIT`, `UI_STABILITY_*`.
  - **Anti‑loops**: `MAX_RETRIES_PER_STEP`, `MAX_ACTIONS_PER_STEP`, `MAX_REPEATED_ACTION_ATTEMPTS`.
  - **Credenciales de prueba**: `TEST_USER_EMAIL`, `TEST_USER_PASSWORD`.
  - **Modo de proyecto**: `ANDROID_APP_PACKAGE` + `AUTO_LAUNCH_MAIN_APP`.

- **Validación (`Config.validate`)**:
  - Verifica proveedor (`openai` / `anthropic` / `deepseek`) y API key correspondiente.
  - Comprueba rangos de timeouts.
  - Devuelve `(False, "mensaje")` si algo crítico falta → `AITestRunner` lanza `ValueError` y el test no arranca.

- **Single‑app vs multi‑app**:
  - **Single‑app**:
    - `ANDROID_APP_PACKAGE` definido; opcionalmente `AUTO_LAUNCH_MAIN_APP=true`.
    - Hay una “app principal” y la mayoría de planes se centran en ella.
  - **Multi‑app**:
    - Sin `ANDROID_APP_PACKAGE` o `AUTO_LAUNCH_MAIN_APP=false`.
    - Los pasos del `test_plan` indican qué app abrir/cambiar:
      - `"Abrir app Customer (com.example.customer)"` → `activate_app(...)`.
      - `"Cambiar a app Technical ... manteniendo Customer en background"` → `switch_to_app_keep_background(...)`.
  - El teardown limpia **solo las apps realmente usadas** (no las de sistema), apoyándose en el tracking de `AppiumSkills`.

---

## 3. Specs y construcción del `test_plan`

- Los specs viven en:
  - `tests/specs/*.py` (tests de usuario final).
  - `tests/integration/*.py` (tests de framework).

Patrón típico:

```python
from src.test_runner import AITestRunner
from src.config import Config

def test_login(self, driver_setup):
    objective = "Validar login de cliente"
    test_email = Config.TEST_USER_EMAIL
    test_password = Config.TEST_USER_PASSWORD

    runner = AITestRunner(driver=driver_setup, objective=objective)

    test_plan = [
        "Abrir app Customer (com.imagineapps.gofixiicliente)",
        f"Ingresar usuario '{test_email}'",
        f"Ingresar password '{test_password}'",
        "Tocar botón Ingresar",
        "Verificar que se inició sesión correctamente",
    ]

    success = runner.run_test_plan(test_plan)
    assert success, "El plan de prueba no se completó exitosamente"
```

El spec:
- Traduce la historia de usuario a **objetivo + lista de pasos en texto**.
- Usa `Config` para datos de entorno (no hardcodea credenciales).
- Delega la ejecución real al `AITestRunner`.

---

## 4. `AITestRunner` y `StepContext`

### 4.1. Construcción del agente (`AITestRunner.__init__`)

Al crear `AITestRunner(driver, objective)`:
- Valida configuración con `Config.validate()`.
- Comprueba que el `driver` tenga `session_id`.
- Crea:
  - `UIParser` (parseo de XML → elementos interactuables).
  - `AppiumSkills` (click, scroll, asserts, multi‑app, estabilidad de UI).
  - `AIOrchestrator` (cliente OpenAI / Anthropic / DeepSeek).
- Inicializa:
  - `action_history: list[str]`.
  - `current_context: Optional[StepContext]` (estado global del agente por paso).
  - Contadores de ejecución (`_execution_stats`).

### 4.2. Ejecución del plan (`run_test_plan`)

Para cada paso de `test_plan`:
- Calcula:
  - `step_index`, `total_steps`.
  - `previous_step` y `next_step`.
- Llama a `_execute_step(step, step_index, total_steps, previous_step, next_step)`.
- Si algún paso falla → devuelve `False`.
- Si todos pasan:
  - Captura screenshot final (si Allure está disponible).
  - Imprime resumen y devuelve `True`.

### 4.3. Loop agéntico por paso y `StepContext`

Dentro de `_execute_step`:

- **Parámetros desde `Config`**:
  - `MAX_RETRIES_PER_STEP` → reintentos del paso ante errores recuperables.
  - `MAX_ACTIONS_PER_STEP` → límite de acciones totales por paso.
  - `MAX_REPEATED_ACTION_ATTEMPTS` → límite de **la misma acción** repetida sin progreso.

- **Por cada intento**:

```text
1) FASE 1: XML estable
   - get_screen_tree_stable()  → XML actual de la pantalla (con lógica de estabilidad).

2) FASE 2: Parseo de UI
   - ui_elements = UIParser.parse_screen(xml)  → list[dict] con {id, attrs, xpath, ...}

3) FASE 3: Construcción de StepContext + decisión de IA
   - app_states = AppiumSkills.get_tracked_app_states()  (dict[package -> state_code])
   - recent_actions = [{"index": i, "text": texto}, ...] (últimas 5 acciones)
   - StepContext:
       - objective, step_index, total_steps
       - current_step, previous_step, next_step
       - action_history = recent_actions
       - ui_elements = ui_elements (nativo, NO TOON)
       - app_states = app_states
   - self.current_context = StepContext
   - ai_decision = AIOrchestrator.decide_next_action(ui_elements, context=StepContext)

4) FASE 4: Ejecutar acción (si hay tool_calls)
   - Se toma solo la primera tool_call.
   - Se detectan acciones repetidas (firma = nombre + argumentos):
       - Si supera MAX_REPEATED_ACTION_ATTEMPTS → el paso falla.
   - _execute_single_tool_call(tool_call, step) llama a AppiumSkills.*
   - Registra la acción en self.action_history.

5) FASE 5: Esperar estabilidad post‑acción
   - Para casi todas las tools → wait_for_ui_stable().
   - Para asserts (`assert_screen_contains`) no se espera (no cambian la UI).

6) Optimización de completitud:
   - _check_if_action_completes_step(...) puede marcar el paso como completo
     sin nueva llamada a la IA en pasos simples (verificación, click, input sencillo).
```

Si `ai_decision` no trae `tool_calls`, se interpreta que la IA considera el paso completo y el runner lo marca como tal.

---

## 5. `AIOrchestrator`, `StepContext` y TOON

### 5.1. `StepContext` como estado global

`StepContext` (en `src/ai_orchestrator.py`) concentra el estado del agente para el paso actual:
- **Plan**: `objective`, `step_index`, `total_steps`, `current_step`, `previous_step`, `next_step`.
- **Historial de acciones**: `action_history: list[dict]` (p.ej. `{"index": 1, "text": "Acción X"}`).
- **Pantalla actual**: `ui_elements: list[dict]` en formato nativo del `UIParser`.
- **Apps en uso**: `app_states: dict[str, int]` (códigos Appium; una sola app puede estar en `FOREGROUND`).

Internamente todo se mantiene en **estructuras ricas (dicts, listas)**; no se convierten a texto hasta el borde LLM.

### 5.2. Serialización a texto TOON sólo en el borde LLM

`AIOrchestrator.decide_next_action(ui_elements, context: StepContext)`:

1. Llama a `_build_llm_context(context, ui_elements)`:
   - Construye un texto con bloques:
     - `[Contexto del plan]`: objetivo, paso actual, anterior, siguiente.
     - `[Historial de acciones recientes (TOON)]`: `toon_encode(context.action_history, delimiter="\t")`.
     - `[Apps en uso (TOON)]`: de `app_states` a filas `{package, state_code, state_name}` y `toon_encode`.
     - `[Elementos en pantalla (TOON)]`: `toon_encode(ui_elements, delimiter="|")` manteniendo `{id, attrs, xpath, ...}`.
   - Este mismo bloque se usa:
     - Para el `messages[1]["content"]` del LLM.
     - Para el log `"Contexto generado"` (debug).

2. Define la lista de **tools** (function calling):
   - `touch_element_by_id`, `fill_field_by_id`, `scroll`, `go_back`, `assert_screen_contains`.
   - Multi‑app: `activate_app`, `terminate_app`, `switch_to_app`, `switch_to_app_keep_background`.

3. Llama al proveedor configurado:
   - OpenAI / DeepSeek → `_call_openai(llm_context, tools)`.
   - Anthropic → `_call_anthropic(llm_context, tools)`.

4. Devuelve al runner un dict con:
   - `provider`, `message`, `tool_calls`, `raw_response`.

**Importante**: `ui_elements` y `action_history` se guardan como `list[dict]` en `StepContext`; el TOON es sólo una **vista serializada para el modelo**.

---

## 6. Errores recuperables, no recuperables y anti‑loops

- **Errores NO recuperables** (no se reintentan):
  - Errores de código/configuración: `ValueError`, `KeyError`, `TypeError`, `AttributeError`, `SyntaxError`, `NameError`, `ImportError`, `IndentationError`, `UnicodeError`.
  - Algunos `WebDriverException` que implican sesión rota:
    - `"session not created"`, `"invalid session id"`, `"no such session"`, `"session deleted"`.

- **Errores recuperables** (se reintentan hasta `MAX_RETRIES_PER_STEP`):
  - `TimeoutException`, `NoSuchElementException`, `ElementNotInteractableException`, `StaleElementReferenceException`.
  - Otros `WebDriverException` que no coinciden con los patrones anteriores.

Integración en `_execute_step`:
- Si el error es no recuperable → se loguea y el paso falla sin reintentos.
- Si es recuperable:
  - Si quedan intentos → espera 2s y reintenta el paso.
  - Si no quedan → el paso falla.

**Anti‑loops**:
- Límite de acciones totales por paso (`MAX_ACTIONS_PER_STEP`).
- Límite de repeticiones exactas de la misma tool + argumentos (`MAX_REPEATED_ACTION_ATTEMPTS`).
- Si la IA insiste en la misma acción sin progreso, el paso falla con un mensaje explicativo.

---

## 7. Resumen rápido del flujo completo

```text
.env / .env.local
    → Config (proveedor IA, API keys, Appium, timeouts, modos)
    → pytest recoge specs (tests/specs, tests/integration)
        → cada spec:
            - lee Config (credenciales, paquetes de apps, etc.)
            - define objective
            - construye test_plan = ["paso 1", "paso 2", ...]
            - recibe driver_setup (Appium Remote)
            - crea AITestRunner(driver, objective)
                → valida Config
                → verifica driver.session_id
                → crea UIParser, AppiumSkills, AIOrchestrator
                → run_test_plan(test_plan)
                    para cada paso:
                        - calcula previous_step / current_step / next_step
                        - _execute_step(...)
                            F1: XML estable (get_screen_tree_stable)
                            F2: ui_elements = UIParser.parse_screen(XML)
                            F3: construir StepContext (plan + historial + ui_elements + app_states)
                                y pasar a AIOrchestrator.decide_next_action(...)
                            F4: ejecutar tool_call con AppiumSkills (+ anti‑loops)
                            F5: esperar estabilidad de UI (salvo asserts)
                        - clasificar errores (recuperable / no recuperable)
                    → si todos los pasos OK: screenshot final + resumen
```

Con este modelo:
- El estado del agente (objetivo, paso actual, historial, apps en uso, UI) está centralizado en `StepContext`.
- El contexto que ve la IA es **100% derivado de `StepContext` + `ui_elements`**, y se ve claramente en los logs.
- La conversión a TOON ocurre sólo en el orquestador (borde LLM), manteniendo tipos ricos ideales para testing y depuración dentro del código. 