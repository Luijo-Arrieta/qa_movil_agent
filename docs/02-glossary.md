# Glosario de Términos

Esta guía explica los términos técnicos que encontrarás en el proyecto, usando un lenguaje sencillo y analogías cotidianas.

## Términos Generales

### API Key (Clave de API)

**¿Qué es?** Una contraseña especial que te permite usar servicios externos como OpenAI o Anthropic.

**Analogía:** Es como la tarjeta de acceso a un edificio. Sin ella, no puedes entrar a usar los servicios.

**Dónde se usa:** En el archivo `.env.local` para configurar el acceso a la inteligencia artificial.

```
OPENAI_API_KEY=sk-abc123...
```

---

### APK (Android Package Kit)

**¿Qué es?** El archivo de instalación de una aplicación Android. Es como el ".exe" de Windows pero para celulares Android.

**Analogía:** Si una app fuera una casa, el APK sería el plano y los materiales empaquetados para construirla.

**Dónde se usa:** Lo necesitas para que el agente pueda instalar y probar tu aplicación.

**Cómo obtenerlo:**
- Desde Android Studio: Build > Build Bundle(s) / APK(s) > Build APK(s)
- El desarrollador de la app te lo puede proporcionar

---

### Driver

**¿Qué es?** Un programa intermediario que permite que tu código "hable" con el celular.

**Analogía:** Es como un traductor en una reunión. Tu código habla en Python, el celular entiende comandos de Android, y el driver traduce entre ambos.

**Dónde se usa:** El `driver_setup` en las pruebas es el driver de Appium que controla el dispositivo.

```python
def test_ejemplo(driver_setup):
    driver = driver_setup  # Este es el driver
    driver.find_element(...)  # Buscar elemento en el celular
```

---

### Emulador

**¿Qué es?** Un celular virtual que corre en tu computadora. Funciona exactamente igual que un celular real, pero es un programa.

**Analogía:** Es como un simulador de vuelo. No estás volando un avión real, pero la experiencia es prácticamente idéntica.

**Ventajas:**
- No necesitas un celular físico
- Puedes tener múltiples "celulares" con diferentes versiones de Android
- Puedes reiniciarlo fácilmente si algo sale mal

**Dónde se usa:** Para ejecutar las pruebas sin necesitar un dispositivo físico.

---

## Herramientas del Proyecto

### Allure

**¿Qué es?** Un sistema para generar reportes visuales de las pruebas, con screenshots y gráficos.

**Analogía:** Es como un informe de laboratorio con fotos. No solo dice "la prueba falló", sino que muestra exactamente qué pasó en cada momento.

**Qué incluye:**
- Screenshots de la pantalla del celular
- XML con la estructura de elementos
- Tiempo de ejecución de cada prueba
- Gráficos de pruebas pasadas vs fallidas

---

### Appium

**¿Qué es?** Una herramienta que permite controlar celulares (Android o iOS) desde código de programación.

**Analogía:** Es como un robot que puede tocar la pantalla del celular siguiendo tus instrucciones. Tú le dices "toca el botón Ingresar" y él lo hace.

**Cómo funciona:**
1. Tú escribes código diciendo qué hacer
2. Appium recibe esas instrucciones
3. Appium las traduce a acciones en el celular
4. El celular responde y Appium te devuelve el resultado

---

### Poetry

**¿Qué es?** Un programa que gestiona las dependencias (librerías) del proyecto Python.

**Analogía:** Es como un chef que tiene la lista de ingredientes de una receta. Si alguien quiere cocinar el mismo plato, Poetry le dice exactamente qué ingredientes necesita y en qué cantidad.

**Comandos principales:**

```bash
poetry install      # Instala todas las dependencias
poetry run pytest   # Ejecuta pytest dentro del entorno
poetry shell        # Activa el entorno virtual
```

---

### pytest

**¿Qué es?** Un framework (herramienta) para escribir y ejecutar pruebas automáticas en Python.

**Analogía:** Es como un supervisor de calidad en una fábrica. Revisa que cada producto (función) funcione correctamente según especificaciones.

**Cómo funciona:**
1. Escribes funciones que empiezan con `test_`
2. Dentro de cada función, verificas que algo sea cierto con `assert`
3. pytest ejecuta todas esas funciones y reporta cuáles pasaron y cuáles fallaron

```python
def test_suma():
    resultado = 2 + 2
    assert resultado == 4  # Si es verdadero, la prueba pasa
```

---

## Términos Técnicos de Android

### XML (Extensible Markup Language)

**¿Qué es?** Un formato de texto que describe la estructura de datos usando etiquetas.

**Analogía:** Es como describir una casa por escrito: "Hay una sala, dentro de la sala hay un sofá, el sofá tiene 3 cojines..."

**Ejemplo de XML de una pantalla Android:**

```xml
<android.widget.LinearLayout>
    <android.widget.EditText text="Usuario" />
    <android.widget.Button text="Ingresar" />
</android.widget.LinearLayout>
```

**Dónde se usa:** Appium obtiene la pantalla del celular en formato XML, y el UIParser lo convierte a algo más simple.

---

### XPath

**¿Qué es?** Una forma de indicar la ubicación exacta de un elemento en una estructura XML.

**Analogía:** Es como dar una dirección: "La casa azul en la calle Principal, tercer piso, apartamento 301". El XPath es la "dirección" de un botón o campo de texto en la pantalla.

**Ejemplo:**

```
//android.widget.Button[@text='Ingresar']
```

Esto significa: "Busca un botón de Android cuyo texto sea 'Ingresar'".

**¿Por qué es importante?** AutoDroid-AI Agent te evita escribir XPaths manualmente - la IA lo hace por ti.

---

### page_source

**¿Qué es?** El XML completo de la pantalla actual del celular.

**Analogía:** Es como una "radiografía" de la pantalla. Muestra todos los elementos, incluso los que no se ven a simple vista.

**Cómo se obtiene:**

```python
xml_pantalla = driver.page_source
```

---

## Términos de Pruebas

### Fixture

**¿Qué es?** Código que se ejecuta automáticamente antes (y/o después) de cada prueba para preparar el ambiente.

**Analogía:** Es como el personal de limpieza en un hotel. Antes de que llegue cada huésped (prueba), preparan la habitación (ambiente). Después de que se va, la limpian para el siguiente.

**Ejemplo:** El fixture `driver_setup` abre la app antes de cada prueba y la cierra después.

```python
def test_login(driver_setup):  # driver_setup es un fixture
    driver = driver_setup      # Ya está listo para usar
    # ... tu prueba aquí
```

---

### Marker (Marcador)

**¿Qué es?** Una etiqueta que le pones a una prueba para categorizarla.

**Analogía:** Es como poner stickers de colores en documentos: "Urgente", "Revisar", "Aprobado". Los markers te permiten filtrar y ejecutar solo ciertos grupos de pruebas.

**Markers disponibles en este proyecto:**

```python
@pytest.mark.unit         # Pruebas que no necesitan celular
@pytest.mark.integration  # Pruebas que sí necesitan celular
@pytest.mark.slow         # Pruebas que tardan mucho
```

**Cómo ejecutar solo pruebas de integración:**

```bash
poetry run pytest -m integration
```

---

### Assert (Aserción)

**¿Qué es?** Una verificación de que algo es verdadero. Si es falso, la prueba falla.

**Analogía:** Es como un inspector que verifica que un producto cumple especificaciones. Si el producto tiene 98 gramos y debería tener 100, el inspector lo rechaza.

**Ejemplos:**

```python
assert resultado == 4           # Verifica que resultado sea 4
assert "Bienvenido" in texto    # Verifica que el texto contenga "Bienvenido"
assert len(lista) > 0           # Verifica que la lista no esté vacía
```

---

## Componentes del Proyecto

### UIParser

**¿Qué es?** El componente que convierte el XML complicado de Android en un JSON simple que la IA puede entender.

**Analogía:** Es como un resumen ejecutivo. Toma un documento de 100 páginas (XML) y lo convierte en una lista de puntos clave (JSON).

**Entrada (XML complejo):**
```xml
<android.widget.LinearLayout class="..." bounds="[0,0][1080,2400]">
  <android.widget.EditText hint="Usuario" resource-id="com.app:id/username" />
</android.widget.LinearLayout>
```

**Salida (JSON simple):**
```json
[{"id": 0, "role": "input", "label": "com.app:id/username"}]
```

---

### Agent Tools

**¿Qué es?** El componente que ejecuta las acciones físicas en el celular (tocar, escribir, hacer scroll).

**Analogía:** Son las "manos" del robot. La IA (cerebro) decide qué hacer, y los Agent Tools lo ejecutan.

**Acciones disponibles:**
- `touch_element_by_id(id)` - Tocar un elemento
- `fill_field_by_id(id, texto)` - Escribir texto en un campo
- `scroll(direccion)` - Hacer scroll arriba/abajo
- `go_back()` - Presionar botón atrás
- `assert_screen_contains(texto)` - Verificar que hay cierto texto

---

### AI Orchestrator

**¿Qué es?** El componente que se comunica con la inteligencia artificial (OpenAI/Anthropic) para decidir qué hacer.

**Analogía:** Es el "cerebro" del sistema. Recibe la información de la pantalla, piensa qué acción tomar, y da las instrucciones.

**Flujo:**
1. Recibe: JSON de elementos en pantalla + paso a ejecutar
2. Envía todo a GPT-4 o Claude
3. La IA responde: "Toca el elemento con ID 2"
4. Devuelve esa decisión al sistema
