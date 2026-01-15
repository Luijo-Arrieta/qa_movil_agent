## Arquitectura del agente y flujo de ejecución

Este documento describe en detalle la arquitectura interna del agente de QA móvil y el **flujograma completo**, desde la carga de variables de entorno hasta la ejecución paso a paso de un `spec` por el `AITestRunner`.

Se centra especialmente en:
- **Cómo se cargan y validan las variables de entorno** (`.env` / `.env.local`).
- **Cómo `Config` influye en el flujo** (single‑app vs multi‑app, timeouts, límites de reintentos, etc.).
- **Cuándo y cómo se leen los specs** y se convierten en un plan de prueba.
- **Cómo se crea y se orquesta el agente** (`AITestRunner` + `AIOrchestrator` + `AppiumSkills` + `UIParser`).
- **Cómo se ejecuta cada paso del plan** (loop agéntico con 5 fases).

---

## 1. Visión general de la arquitectura

Arquitectura lógica principal:

```text
Variables de entorno (.env / .env.local)
        │
        ▼
   Config (src/config.py)
        │
        ▼
 pytest + specs (tests/specs/*.py, tests/integration/*.py)
        │               └─ definen: objective + test_plan (lista de pasos en lenguaje natural)
        │
        ▼
 driver_setup (fixture pytest)  ──► Appium Remote Driver (con capabilities de Config)
        │
        ▼
 AITestRunner (src/test_runner.py)
        │   ├─ Valida Config
        │   ├─ Crea UIParser
        │   ├─ Crea AppiumSkills (Agent Tools)
        │   └─ Crea AIOrchestrator (proveedor IA según Config)
        │
        ▼
 run_test_plan(test_plan)
  └─ Para cada paso:
        ▼
    _execute_step(step, step_index)
        └─ Loop agéntico:
           Fase 1: AppiumSkills.get_screen_tree_stable()  → XML estable
           Fase 2: UIParser.parse_screen()                → elementos {id, attrs}
           Fase 3: AIOrchestrator.decide_next_action()    → tool_call o “paso completo”
           Fase 4: _execute_single_tool_call()            → AppiumSkills ejecuta acción
           Fase 5: AppiumSkills.wait_for_ui_stable()      → espera de estabilidad
           + Detección de loops / acciones repetidas
```

Relación entre componentes:

```text
pytest/spec  ──►  AITestRunner  ──►  AIOrchestrator  ──►  LLM (OpenAI / Anthropic / DeepSeek)
   ▲                    │                   │
   │                    ▼                   │
 driver_setup      AppiumSkills  ◄──────────┘
   ▲                    │
   │                    ▼
   └──────────────  UIParser  ◄─ XML desde Appium driver
```

---

## 2. Fase 0 – Variables de entorno y `Config`

### 2.1. Dónde y cómo se cargan las variables

Archivo clave: `src/config.py`.

En cuanto se importa `Config` por primera vez:

- Se ejecuta:
  - `load_dotenv(".env")`
  - `load_dotenv(".env.local", override=True)`
- `.env.local` **sobrescribe** lo que haya en `.env`.
- Se inicializan todos los atributos de clase de `Config` leyendo `os.getenv(...)`.

Esto ocurre típicamente cuando:
- `pytest` importa `tests/...`, que a su vez importan `src.test_runner` o `src.ai_orchestrator`.
- Esas importaciones hacen `from src.config import Config`, activando la carga de `.env` / `.env.local`.

### 2.2. Qué parámetros controla `Config`

Algunos grupos importantes en `Config` (`src/config.py`):

- **Proveedor y modelos de IA**
  - `AI_PROVIDER` → `Config.DEFAULT_AI_PROVIDER` (`"openai"`, `"anthropic"` o `"deepseek"`).
  - `OPENAI_MODEL`, `ANTHROPIC_MODEL`, `DEEPSEEK_MODEL`.

- **Appium / dispositivo**
  - `APPIUM_SERVER_URL`
  - `ANDROID_PLATFORM_NAME`, `ANDROID_DEVICE_NAME`, `ANDROID_UDID`
  - `ANDROID_APP_PACKAGE`, `ANDROID_APP_ACTIVITY`, `ANDROID_APP_PATH`
  - Flags: `ANDROID_AUTO_GRANT_PERMISSIONS`, `ANDROID_IGNORE_HIDDEN_API_POLICY_ERROR`, `ANDROID_DISABLE_WINDOW_ANIMATION`

- **Timeouts y estabilidad de UI**
  - `DEFAULT_WAIT_TIMEOUT` (minutos, se transforma a segundos en `newCommandTimeout`).
  - `IMPLICIT_WAIT` (segundos).
  - `UI_STABILITY_TIMEOUT`, `UI_STABILITY_INTERVAL`, `UI_STABILITY_THRESHOLD`
    - Controlan cuánto y cómo espera `AppiumSkills` a que la pantalla deje de “moverse” (pantallas de carga, spinners…).

- **Comportamiento del Test Runner (anti‑loops)**
  - `MAX_RETRIES_PER_STEP` → máximo de reintentos por paso cuando hay errores **recuperables**.
  - `MAX_ACTIONS_PER_STEP` → límite de acciones distintas que se pueden ejecutar dentro de un único paso.
  - `MAX_REPEATED_ACTION_ATTEMPTS` → número máximo de veces que se permite repetir **la misma acción** antes de fallar el paso.

- **Credenciales de prueba**
  - `TEST_USER_EMAIL`, `TEST_USER_PASSWORD` → usados por los specs (`Config.TEST_USER_EMAIL`, `Config.TEST_USER_PASSWORD`).

- **Modo de proyecto (single‑app vs multi‑app)**
  - `ANDROID_APP_PACKAGE` + `AUTO_LAUNCH_MAIN_APP` controlan el modo; ver siguiente sección.

### 2.3. Validación de configuración (`Config.validate`)

Antes de que el runner empiece a trabajar, `AITestRunner.__init__` llama a:

- `Config.validate()`:
  - Verifica que `AI_PROVIDER` sea uno de `["openai", "anthropic", "deepseek"]`.
  - Exige la API key correcta según el proveedor (`OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `DEEPSEEK_API_KEY`).
  - Emite **warnings** si faltan:
    - `ANDROID_APP_PATH` **y** `ANDROID_APP_PACKAGE` (no hay app que abrir).
    - `ANDROID_APP_PACKAGE` sin `ANDROID_APP_ACTIVITY` (posible problema en ciertas apps).
  - Valida rangos de `DEFAULT_WAIT_TIMEOUT` e `IMPLICIT_WAIT`.
  - Si hay errores críticos, devuelve `(False, "mensaje...")` y `AITestRunner` lanza `ValueError` → el test falla inmediatamente.

De esta forma, **ningún test** arranca si la configuración básica de IA o Appium es inválida.

---

## 3. Single‑app vs Multi‑app – Cómo `Config` cambia el flujo

Aunque las `capabilities` que construye `Config.get_appium_capabilities()` **no** incluyen `appPackage` / `appActivity` (el driver se crea “vacío”), el modo de proyecto afecta:

- Cómo configuras tu `.env.local`.
- Cómo se escriben los **planes de prueba** (uso de `activate_app`, `switch_to_app*`, etc.).
- Cómo se comportan los fixtures de tests (p.ej. si auto‑lanzan o no la app principal).

### 3.1. Modo single‑app

- **Condición lógica**:
  - `ANDROID_APP_PACKAGE` está configurado (y opcionalmente `ANDROID_APP_ACTIVITY`).
  - Opcionalmente `AUTO_LAUNCH_MAIN_APP=true`.

- **Consecuencias típicas**:
  - El proyecto se entiende como “una app principal”.
  - En muchos flujos **basta con una sola app**, y los planes de prueba se centran en esa app.
  - Según el fixture `driver_setup` (ver docs del proyecto), se puede:
    - No abrir nada por defecto (requiere que los pasos usen `activate_app`).
    - O auto‑abrir la app principal si `AUTO_LAUNCH_MAIN_APP=true`.

### 3.2. Modo multi‑app

- **Condición lógica**:
  - `ANDROID_APP_PACKAGE` está vacío o `AUTO_LAUNCH_MAIN_APP=false`.

- **Consecuencias típicas**:
  - Se asume que hay **varias apps** involucradas (Customer, Technical, Admin, etc.).
  - Los planes de prueba deben ser explícitos:
    - `"Abrir app Customer (com.example.customer)"` → se traduce en una llamada a `activate_app(...)`.
    - `"Cambiar a app Technical (com.example.technical) manteniendo Customer en background"` → `switch_to_app_keep_background(...)`.
  - El teardown limpia solo las apps realmente usadas (no las de sistema).

### 3.3. Resumen de impacto en el flujo

- **Config**, mediante `ANDROID_APP_PACKAGE` y `AUTO_LAUNCH_MAIN_APP`, **no cambia el código del runner**, pero sí:
  - Cambia cómo se monta el `driver` en los fixtures.
  - Cambia cómo se espera que el usuario escriba los `test_plan` (más explícito en multi‑app).
  - Afecta la lógica de limpieza de apps al final del test.

---

## 4. Fase 1 – Specs, pytest y construcción del plan de prueba

### 4.1. Dónde se define el spec

Ejemplos clave:

- `tests/specs/spec_login_logout.py`
- `tests/specs/examples/test_example.py`

Patrón general:

```python
from src.test_runner import AITestRunner
from src.config import Config

def test_lo_que_sea(self, driver_setup):
    objective = "Descripción de alto nivel del objetivo del test"

    # Datos de entorno (no hardcodear credenciales)
    test_email = Config.TEST_USER_EMAIL
    test_password = Config.TEST_USER_PASSWORD

    # 1) Construir el runner
    runner = AITestRunner(driver=driver_setup, objective=objective)

    # 2) Construir el plan de prueba (lista de strings)
    test_plan = [
        "Paso 1 en lenguaje natural...",
        "Paso 2 en lenguaje natural...",
        # ...
    ]

    # 3) Ejecutar el plan
    success = runner.run_test_plan(test_plan)
    assert success, "Mensaje si el plan falla"
```

**Cuándo se “lee” el spec**:
- Durante la **fase de colección** de pytest, Python importa el archivo de test y define la clase y los métodos.
- El plan (`test_plan`) se **construye en tiempo de ejecución** dentro del propio método de test, justo antes de llamar a `run_test_plan`.

### 4.2. Ejemplo concreto: `spec_login_logout.py`

En `tests/specs/spec_login_logout.py`:

- Se define el objetivo:
  - `"Validar historia de usuario AC-001: inicio y cierre de sesión ..."`
- Se leen credenciales desde `Config`:
  - `test_email = Config.TEST_USER_EMAIL`
  - `test_password = Config.TEST_USER_PASSWORD`
- Se crea el runner:
  - `runner = AITestRunner(driver=driver_setup, objective=objective)`
- Se crea el plan:
  - `"Abrir la app de cliente usando activate_app con el paquete 'com.imagineapps.gofixiicliente'"`
  - `"Esperar a ver la pantalla de inicio de sesión del cliente"`
  - ...
- Finalmente se llama:
  - `success = runner.run_test_plan(test_plan)`

Es decir, el **spec** se encarga de:
- Traducir la historia de usuario / criterio de aceptación a **objetivo** + **lista de pasos**.
- Reutilizar `Config` para cualquier dato de entorno.
- Delegar toda la lógica de decisión y ejecución en el `AITestRunner`.

---

## 5. Fase 2 – Construcción del agente (`AITestRunner.__init__`)

Archivo: `src/test_runner.py`, clase `AITestRunner`.

Cuando el spec hace:

```python
runner = AITestRunner(driver=driver_setup, objective=objective)
```

Ocurre lo siguiente, en orden:

1. **Logging de inicio**
   - Muestra banners en logs indicando que se está inicializando el runner.

2. **Validación de configuración**
   - Llama a `Config.validate()`.
   - Si la configuración es inválida → `ValueError` y el test termina.

3. **Verificación del driver**
   - Intenta leer `driver.session_id`.
   - Si falla, lanza una excepción y el test no continúa.

4. **Creación de componentes internos**
   - `self.ui_parser = UIParser()`
   - `self.agent_tools = AppiumSkills(driver, self.ui_parser)`
   - `self.ai_orchestrator = AIOrchestrator()`
     - Dentro del orquestador:
       - Lee `Config.DEFAULT_AI_PROVIDER`.
       - Configura `OpenAI`, `Anthropic` o `DeepSeek` según corresponda.
       - Valida que la API key del proveedor elegido exista.

5. **Inicialización de estado interno del runner**
   - `self.action_history` → lista vacía para ir registrando acciones.
   - `self.max_retries = Config.MAX_RETRIES_PER_STEP`
   - `_execution_stats` → diccionario con contadores de pasos, acciones, llamadas a IA, etc.

En este punto el “agente” está listo para recibir un `test_plan`.

---

## 6. Fase 3 – Ejecución del plan: `run_test_plan(test_plan)`

Método principal: `AITestRunner.run_test_plan(self, test_plan: List[str])`.

### 6.1. Estructura general

1. Registra inicio y muestra:
   - Número total de pasos.
   - Valor de `max_retries`.
   - El `objective` si está definido.

2. Itera sobre cada paso:

```python
for step_index, step in enumerate(test_plan, 1):
    success = self._execute_step(step, step_index)
    if not success:
        # Marca como fallo, imprime resumen, devuelve False
```

3. Si **todos** los pasos devuelven `True`:
   - Captura screenshot final (si Allure está disponible).
   - Imprime resumen de ejecución.
   - Devuelve `True` al test de pytest.

---

## 7. Fase 4 – Loop agéntico por paso: `_execute_step`

Método clave: `AITestRunner._execute_step(self, step: str, step_index: int)`.

Esta es la parte central del “agente”. Para **cada paso** del plan:

### 7.1. Parámetros controlados por `Config`

- `max_actions_per_step = Config.MAX_ACTIONS_PER_STEP`
- `max_repeated_action_attempts = Config.MAX_REPEATED_ACTION_ATTEMPTS`
- `self.max_retries = Config.MAX_RETRIES_PER_STEP`

Estos valores definen:
- Cuántas veces se puede intentar el mismo paso.
- Cuántas acciones distintas se pueden ejecutar dentro de un paso.
- Cuántas veces se tolera repetir la **misma** acción sin progreso.

### 7.2. Flujograma dentro de `_execute_step`

Pseudoflujo (por intento):

```text
_execute_step(step):
    inicializar contadores y tracking de acciones repetidas

    para attempt en 1..MAX_RETRIES_PER_STEP:
        ┌────────────────────────────────────────────┐
        │ INTENTO attempt del paso actual           │
        └────────────────────────────────────────────┘

        intentar:
            loop agéntico (mientras actions_executed < MAX_ACTIONS_PER_STEP):

                FASE 1: obtener XML estable de la pantalla
                    xml_source = agent_tools.get_screen_tree_stable()

                FASE 2: parsear UI con UIParser
                    ui_elements = ui_parser.parse_screen(xml_source)

                FASE 3: pedir decisión a la IA
                    ai_decision = ai_orchestrator.decide_next_action(
                        ui_elements, step, últimas acciones, objective
                    )

                FASE 4: ejecutar acción o terminar paso
                    si ai_decision.tool_calls existe:
                        tool_call = primera tool_call
                        detectar si es acción repetida
                        ejecutar _execute_single_tool_call(tool_call, step)
                        registrar en historial

                        FASE 5: esperar estabilización de UI
                            (salvo en asserts, que no modifican UI)

                        optimización: _check_if_action_completes_step(...)
                            si devuelve True → marcar paso como completo
                            return True

                        continuar loop (nueva iteración → nueva observación de UI)
                    si NO hay tool_calls:
                        la IA indica que el paso ya está completo
                        registrar mensaje
                        return True

            si se alcanzó MAX_ACTIONS_PER_STEP:
                fallo del paso por posible loop infinito
                return False

        excepto Exception e:
            si e es NO recuperable (ValueError, TypeError, errores de sesión, etc.):
                return False (no se reintenta)
            si e es recuperable (TimeoutException, NoSuchElementException, etc.):
                si quedan reintentos → esperar 2s y volver al `for attempt`
                si no quedan reintentos → return False

    si se agotan todos los intentos:
        return False
```

### 7.3. Fase 1 – Obtención de XML estable

- Llama a `self.agent_tools.get_screen_tree_stable()`.
- Esta función:
  - Reintenta leer el `page_source` del driver.
  - Usa los parámetros de `Config`:
    - `UI_STABILITY_TIMEOUT`
    - `UI_STABILITY_INTERVAL`
    - `UI_STABILITY_THRESHOLD`
  - Hasta que detecta que la UI “deja de cambiar” (por ejemplo, se fue una pantalla de carga).

Resultado: **XML estable** de la pantalla actual.

### 7.4. Fase 2 – Parseo de UI con `UIParser`

- `ui_elements = self.ui_parser.parse_screen(xml_source)`
- `UIParser`:
  - Convierte el XML en una lista de elementos internos con la forma:
    - `{ "id": <int>, "attrs": [{ "name": "...", "value": "..." }, ...] }`
  - Genera XPaths jerárquicos cortos y legibles.
  - Mantiene un mapa `id → xpath` para uso posterior por `AppiumSkills`.

Resultado: lista de elementos **interactuables** sobre los que la IA puede razonar.

### 7.5. Fase 3 – Decisión de IA con `AIOrchestrator`

- Llama a:

```python
ai_decision = self.ai_orchestrator.decide_next_action(
    ui_elements=ui_elements,
    current_step=step,
    action_history=self.action_history[-5:],
    objective=self.objective,
)
```

Dentro de `AIOrchestrator` (`src/ai_orchestrator.py`):

1. **Construcción del contexto** (`_build_context`) en formato TOON:
   - Incluye:
     - Objetivo general (si existe).
     - Paso actual.
     - Historial de acciones recientes.
     - Lista de elementos en formato TOON, manteniendo `{id, attrs}`.

2. **Configuración de herramientas** (`_get_tools_definition`):
   - Define las tools disponibles para function calling:
     - `touch_element_by_id(element_id)`
     - `fill_field_by_id(element_id, value)`
     - `scroll(direction)`
     - `go_back()`
     - `assert_screen_contains(text)`
     - `activate_app(app_package)`
     - `terminate_app(app_package)`
     - `switch_to_app(app_package)`
     - `switch_to_app_keep_background(app_package)`

3. **Llamada al proveedor de IA**:
   - Si `AI_PROVIDER=openai` o `deepseek`:
     - Usa `_call_openai(...)`.
   - Si `AI_PROVIDER=anthropic`:
     - Usa `_call_anthropic(...)`.

4. **Resultado devuelto a `AITestRunner`**:
   - Diccionario con:
     - `provider`
     - `message` → texto libre de la IA.
     - `tool_calls` → lista de tool calls (cada una con `name`, `arguments`, `id`).

### 7.6. Fase 4 – Ejecución de la acción: `_execute_single_tool_call`

Si la decisión de la IA incluye `tool_calls`:

- Se toma **solo la primera** por iteración del loop.
- `_execute_single_tool_call(tool_call, step)`:
  - Desempaqueta `tool_name` y `tool_args`.
  - Hace un `if`/`elif` según el nombre:
    - `touch_element_by_id` → `AppiumSkills.touch_element_by_id(element_id)`
    - `fill_field_by_id` → `AppiumSkills.fill_field_by_id(element_id, value)`
    - `scroll` → `AppiumSkills.scroll(direction)`
    - `go_back` → `AppiumSkills.go_back()`
    - `assert_screen_contains` → `AppiumSkills.assert_screen_contains(text)`
    - `activate_app` / `terminate_app` / `switch_to_app` / `switch_to_app_keep_background`
      → llaman a las funciones multi‑app de `AppiumSkills`.
  - Si el resultado contiene `"Error"` → se considera fallo y se rompe el loop para reintentar el paso.

#### 7.6.1. Detección de acciones repetidas

Antes de ejecutar la tool:

- Se construye una “firma” de la acción:
  - `current_action_signature = f"{tool_name}:{json.dumps(tool_args, sort_keys=True)}"`
- Se compara con `last_action_signature`:
  - Si es igual, incrementa `repeated_action_count`.
  - Si `repeated_action_count >= MAX_REPEATED_ACTION_ATTEMPTS`:
    - El paso falla inmediatamente con un mensaje explicativo en logs.
  - Si es diferente:
    - Reinicia el contador a 1 y actualiza `last_action_signature`.

Esto evita que la IA se quede atascada repitiendo exactamente la misma acción sin progreso.

### 7.7. Fase 5 – Espera de estabilidad post‑acción

Después de ejecutar la tool:

- Si la tool es **`assert_screen_contains`**:
  - No se espera estabilidad porque la acción no modifica la UI.
- Para todas las demás:
  - Se llama a `self.agent_tools.wait_for_ui_stable()`.
  - Esta función usa los parámetros:
    - `UI_STABILITY_TIMEOUT`
    - `UI_STABILITY_INTERVAL`
    - `UI_STABILITY_THRESHOLD`
  - Permite absorber transiciones, animaciones y pantallas de carga antes de la próxima observación de UI.

### 7.8. Optimización: `_check_if_action_completes_step`

Después de una acción exitosa, se llama a:

```python
step_completed = self._check_if_action_completes_step(
    tool_call['name'], tool_call.get('arguments', {}), step
)
```

- Si devuelve `True`:
  - El runner marca el paso como completo **sin hacer una segunda llamada a la IA**.
  - Esto reduce coste y latencia en pasos simples (por ejemplo, un paso que solo pide “verificar” algo ya verificado por un assert exitoso).
- La función utiliza principalmente:
  - Palabras clave en el texto del paso (esperar, verificar, tocar, ingresar, etc.).
  - El tipo de acción (`assert_screen_contains`, `fill_field_by_id`, `touch_element_by_id`).
  - En el caso de inputs, que el valor ingresado coincida con el texto del paso.
- Es un área marcada en el código como **“OPTIMIZACIÓN – ÁREA DE MEJORA POTENCIAL”**.

### 7.9. Caso en que la IA no devuelve tool calls

Si `ai_decision` no contiene `tool_calls`:

- Se interpreta como que la IA considera que el paso **ya está completo**.
- El runner:
  - Registra un resumen (“Paso completado: …”) en el historial.
  - Devuelve `True` para ese paso.

---

## 8. Errores recuperables vs no recuperables

Función clave: `_is_recoverable_error(exception: Exception)`.

- **Errores NO recuperables** (no se reintentan, fallan inmediatamente):
  - `ValueError`, `KeyError`, `TypeError`, `AttributeError`, `SyntaxError`, `NameError`, `ImportError`, `IndentationError`, `UnicodeError`.
  - Algunos `WebDriverException` con patrones como:
    - `"session not created"`, `"invalid session id"`, `"no such session"`, `"session deleted"`.

- **Errores recuperables** (se reintentan hasta `MAX_RETRIES_PER_STEP`):
  - `TimeoutException`
  - `NoSuchElementException`
  - `ElementNotInteractableException`
  - `StaleElementReferenceException`
  - Otros `WebDriverException` que no coinciden con los patrones de sesión rota.

Integración en el flujo:

- Dentro del `try/except` de `_execute_step`:
  - Si el error es **no recuperable**:
    - Se loguea como tal.
    - Se devuelve `False` sin más reintentos.
  - Si es **recuperable**:
    - Si quedan intentos:
      - Espera 2 segundos.
      - Vuelve al inicio del loop de intentos.
    - Si no quedan:
      - Marca el paso como fallido.

---

## 9. Resumen rápido del flujograma completo

En una sola vista, desde las variables de entorno hasta la acción en pantalla:

```text
.env / .env.local
    │  (load_dotenv en src/config.py)
    ▼
Config (atributos estáticos: API keys, Appium, timeouts, modos, límites)
    │
    ▼
pytest recoge specs (tests/specs/*.py, tests/integration/*.py)
    │
    ├─ Cada spec:
    │     - lee Config (ej: credenciales)
    │     - construye objective
    │     - construye test_plan = [paso1, paso2, ...]
    │     - recibe driver_setup (Appium Remote)
    │
    └─ Llama a:
          runner = AITestRunner(driver=driver_setup, objective=objective)
              │
              ├─ Config.validate()
              ├─ Verifica driver.session_id
              ├─ Crea UIParser
              ├─ Crea AppiumSkills(driver, ui_parser)
              └─ Crea AIOrchestrator (según AI_PROVIDER)
              │
              └─ run_test_plan(test_plan)
                    │
                    └─ para cada step:
                           _execute_step(step)
                               │
                               ├─ para attempt en 1..MAX_RETRIES_PER_STEP:
                               │      ├─ loop agéntico (mientras actions_executed < MAX_ACTIONS_PER_STEP):
                               │      │      FASE 1: get_screen_tree_stable() → XML (usa parámetros de estabilidad de Config)
                               │      │      FASE 2: UIParser.parse_screen() → elementos {id, attrs}
                               │      │      FASE 3: AIOrchestrator.decide_next_action() → tool_call(s) / mensaje
                               │      │      FASE 4: _execute_single_tool_call() → AppiumSkills.* (incluye multi‑app)
                               │      │      FASE 5: wait_for_ui_stable() (salvo asserts)
                               │      │      + detección de acción repetida
                               │      │      + optimización de completitud de paso
                               │      │
                               │      └─ si excepción:
                               │             - _is_recoverable_error(e) decide si reintentar o fallar
                               │
                               └─ si todos los intentos fallan → paso fallido
```

Con este esquema puedes:
- Ver con claridad **dónde toca cada pieza** (`Config`, specs, runner, orquestador, tools).
- Entender **qué parámetros de entorno afectan a qué fases** (especialmente estabilidad de UI y anti‑loops).
- Rastrear fácilmente en qué parte del flujo se está produciendo un problema leyendo los logs generados por `test_runner.py` y `ai_orchestrator.py`.

