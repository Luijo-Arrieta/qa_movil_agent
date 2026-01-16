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
              F3: Construir StepContext
                  ├─ app_states = AppiumSkills.get_tracked_app_states()
                  ├─ recent_actions = formatear(action_history[-5:])
                  ├─ step_context = StepContext(...)
                  ├─ self.current_context = step_context
                  └─ AIOrchestrator.decide_next_action(ui_elements, context=StepContext)
                      └─ _build_llm_context() serializa StepContext → TOON (borde LLM)
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
   
   Construcción de StepContext (antes de llamar a decide_next_action):
   
   a) Obtener app_states:
      - app_states = AppiumSkills.get_tracked_app_states()  
      - Resultado: dict[package: str -> state_code: int]
      - Estado 4 = FOREGROUND (solo una app puede estar en foreground)
   
   b) Formatear recent_actions desde action_history:
      - recent_actions = [
          {"index": idx, "text": text}
          for idx, text in enumerate(self.action_history[-5:], 1)
        ]
      - Toma las últimas 5 acciones del historial
      - Formato: list[dict] con {"index": int, "text": str}
   
   c) Construir StepContext con todos los datos:
      step_context = StepContext(
          objective=self.objective,              # Opcional, desde __init__
          step_index=step_index,                 # Calculado en run_test_plan
          total_steps=total_steps,               # Calculado en run_test_plan
          current_step=step,                     # Paso actual del loop
          next_step=next_step,                   # Calculado en run_test_plan
          previous_step=previous_step,           # Calculado en run_test_plan
          action_history=recent_actions,         # Formateado arriba (NO TOON)
          ui_elements=ui_elements,               # Desde FASE 2 (formato nativo, NO TOON)
          app_states=app_states,                 # Desde AppiumSkills
      )
   
   d) Asignar a self.current_context para tracking:
      self.current_context = step_context
   
   e) Llamar al orquestador con StepContext:
      ai_decision = AIOrchestrator.decide_next_action(
          ui_elements=ui_elements,  # También se pasa por separado
          context=step_context      # StepContext completo
      )

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

**Importante sobre `StepContext`**:
- Se construye **nuevo en cada iteración** del loop agéntico (FASE 3), reflejando el estado actualizado de la UI y el historial de acciones.
- Todos los datos se mantienen en **formato nativo** (dicts, listas) dentro de `StepContext`.
- Solo se convierte a texto TOON **dentro de `AIOrchestrator._build_llm_context()`** (borde LLM).

Si `ai_decision` no trae `tool_calls`, se interpreta que la IA considera el paso completo y el runner lo marca como tal.

---

## 5. `AIOrchestrator`, `StepContext` y TOON

### 5.1. `StepContext` como estado global

`StepContext` (definido como `@dataclass` en `src/ai_orchestrator.py`) concentra el estado del agente para el paso actual.

**Estructura completa del dataclass**:

```python
@dataclass
class StepContext:
    objective: Optional[str]           # Objetivo general del test (opcional)
    step_index: int                    # Índice del paso actual (1-based)
    total_steps: int                   # Número total de pasos en el plan
    current_step: str                  # Texto del paso actual a ejecutar
    next_step: Optional[str]           # Texto del siguiente paso (None si es el último)
    previous_step: Optional[str]       # Texto del paso anterior (None si es el primero)
    action_history: List[Dict[str, Any]]  # Historial de acciones recientes
    ui_elements: List[Dict[str, Any]]     # Elementos UI en formato nativo del UIParser
    app_states: Dict[str, int]            # Estados de apps (package -> state_code)
    
    def to_dict(self) -> Dict[str, Any]:
        """Helper para logging/debug usando asdict()."""
        return asdict(self)
```

**Descripción de campos**:

- **Plan**:
  - `objective`: Objetivo general del test (se pasa en `AITestRunner.__init__`).
  - `step_index`, `total_steps`: Posición actual en el plan (calculados en `run_test_plan`).
  - `current_step`, `previous_step`, `next_step`: Pasos del plan en texto (calculados en `run_test_plan`).

- **Historial de acciones**: 
  - `action_history: list[dict]` en formato `[{"index": int, "text": str}, ...]`.
  - Contiene las últimas 5 acciones ejecutadas (formateadas desde `self.action_history[-5:]`).
  - Ejemplo: `[{"index": 1, "text": "Acción: touch_element_by_id(...)"}, ...]`.

- **Pantalla actual**:
  - `ui_elements: list[dict]` en formato nativo del `UIParser`.
  - Cada elemento tiene estructura `{"id": int, "attrs": [{"name": str, "value": str}, ...], ...}`.
  - **NO está en formato TOON**; se mantiene como estructura rica durante la ejecución.

- **Apps en uso**:
  - `app_states: dict[str, int]` mapea `package -> state_code`.
  - Códigos Appium: `0=NOT_INSTALLED`, `1=NOT_RUNNING`, `2=BACKGROUND_SUSPENDED`, `3=BACKGROUND`, `4=FOREGROUND`.
  - Solo una app puede estar en `FOREGROUND` (estado 4) a la vez.
  - Se obtiene desde `AppiumSkills.get_tracked_app_states()`.

**Método `to_dict()`**:
- Helper para logging/debug que usa `asdict()` del módulo `dataclasses`.
- Convierte el `StepContext` a diccionario plano para inspección.

**Principio clave**: Internamente todo se mantiene en **estructuras ricas (dicts, listas)**; no se convierten a texto hasta el borde LLM (`_build_llm_context()`).

### 5.2. Serialización a texto TOON sólo en el borde LLM

`AIOrchestrator.decide_next_action(ui_elements, context: StepContext)`:

1. Llama a `_build_llm_context(context, ui_elements)`:
   
   **`_build_llm_context()` es el único lugar donde se serializa `StepContext` a texto**. Mantiene `ui_elements` y `action_history` como estructuras ricas durante la ejecución y solo las convierte a TOON justo antes de llamar al LLM.
   
   Construye un texto con **4 bloques principales**:
   
   a) **`[Contexto del plan]`** (texto plano):
      - Objetivo general: `{context.objective}` (si existe).
      - Paso actual: `{context.step_index}/{context.total_steps}: {context.current_step}`.
      - Paso anterior: `{context.previous_step}` (si existe).
      - Próximo paso: `{context.next_step}` (si existe).
   
   b) **`[Historial de acciones recientes (TOON)]`**:
      - Convierte `context.action_history` (list[dict]) a TOON.
      - `toon_encode(context.action_history, delimiter="\t")`.
      - Formato de entrada: `[{"index": 1, "text": "..."}, ...]`.
      - Formato TOON: tabla con columnas `index` y `text`.
   
   c) **`[Apps en uso (TOON)]`**:
      - Convierte `context.app_states` (dict[package -> state_code]) a TOON.
      - Primero expande a filas: `[{"package": pkg, "state_code": code, "state_name": APP_STATE_NAMES[code]}, ...]`.
      - Luego: `toon_encode(app_rows, delimiter="\t")`.
      - Formato TOON: tabla con columnas `package`, `state_code`, `state_name`.
      - Ejemplo: `com.example.app | 4 | FOREGROUND`.
   
   d) **`[Elementos disponibles en la pantalla (formato TOON)]`**:
      - Convierte `ui_elements` (list[dict]) a TOON.
      - `toon_encode(ui_elements, delimiter="|")`.
      - Mantiene estructura `{id, attrs, xpath, ...}` en formato tabular.
      - Formato TOON: tabla con columnas `id`, `content-desc`, `class`, `xpath`, `clickable`, etc.
   
   El texto generado se usa:
   - Para el `messages[1]["content"]` del LLM (OpenAI/Anthropic/DeepSeek).
   - Para el log `"Contexto generado"` (debug).

2. Define la lista de **tools** (function calling):
   - `touch_element_by_id`, `fill_field_by_id`, `scroll`, `go_back`, `assert_screen_contains`.
   - Multi‑app: `activate_app`, `terminate_app`, `switch_to_app`, `switch_to_app_keep_background`.

3. Llama al proveedor configurado:
   - OpenAI / DeepSeek → `_call_openai(llm_context, tools)`.
   - Anthropic → `_call_anthropic(llm_context, tools)`.

4. Devuelve al runner un dict con:
   - `provider`, `message`, `tool_calls`, `raw_response`.

**Importante**: 
- `ui_elements` y `action_history` se guardan como `list[dict]` en `StepContext` durante toda la ejecución.
- El TOON es solo una **vista serializada para el modelo** que se genera únicamente en `_build_llm_context()`.
- Esto permite mantener tipos ricos ideales para testing y depuración dentro del código Python.

**Nota sobre método legacy `_build_context()`**:
- Existe un wrapper de compatibilidad `_build_context()` en `AIOrchestrator` que construye un `StepContext` mínimo.
- Mantiene la firma histórica usada en tests unitarios (parámetros separados).
- Internamente delega a `_build_llm_context()` para mantener consistencia.

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
                            F3: construir StepContext
                                - app_states = AppiumSkills.get_tracked_app_states()
                                - recent_actions = formatear(action_history[-5:])
                                - step_context = StepContext(...)
                                - self.current_context = step_context
                                - AIOrchestrator.decide_next_action(ui_elements, context=StepContext)
                                    └─ _build_llm_context() serializa StepContext → TOON (borde LLM)
                            F4: ejecutar tool_call con AppiumSkills (+ anti‑loops)
                            F5: esperar estabilidad de UI (salvo asserts)
                        - clasificar errores (recuperable / no recuperable)
                    → si todos los pasos OK: screenshot final + resumen
```

Con este modelo:
- El estado del agente (objetivo, paso actual, historial, apps en uso, UI) está centralizado en `StepContext`.
- El contexto que ve la IA es **100% derivado de `StepContext` + `ui_elements`**, y se ve claramente en los logs.
- La conversión a TOON ocurre sólo en el orquestador (borde LLM), manteniendo tipos ricos ideales para testing y depuración dentro del código. 