# Crear Pruebas con Live Coding

Esta guía te enseñará cómo escribir tus propias pruebas automáticas paso a paso, siguiendo las mejores prácticas del proyecto.

## Antes de Empezar

Asegúrate de tener:
- [ ] El emulador Android corriendo
- [ ] Appium iniciado (`appium --use-plugins=all`)
- [ ] El proyecto instalado (`poetry install`)
- [ ] El archivo `.env.local` configurado

---

## Dos Formas de Crear Tests

Este proyecto ofrece **dos formas** de crear pruebas:

### 1. **AITestRunner (Recomendado para empezar)** 🚀

La forma más simple: escribes instrucciones en lenguaje natural y el agente de IA las ejecuta automáticamente. **No necesitas escribir selectores XPath ni analizar la UI manualmente.**

**Ventajas:**
- ✅ Muy fácil de escribir y leer
- ✅ No necesitas conocer XPath o estructura de la UI
- ✅ El agente maneja automáticamente los errores y reintentos
- ✅ Ideal para flujos completos de usuario

**Ejemplo rápido:**
```python
from src.test_runner import AITestRunner
from src.config import Config

def test_login(self, driver_setup):
    runner = AITestRunner(driver=driver_setup)
    test_plan = [
        "Esperar a ver la pantalla de login",
        f"Ingresar usuario '{Config.TEST_USER_EMAIL}'",
        f"Ingresar password '{Config.TEST_USER_PASSWORD}'",
        "Tocar botón Ingresar",
        "Verificar que se inició la sesión",
    ]
    success = runner.run_test_plan(test_plan)
    assert success
```

**Ver ejemplo completo:** `tests/specs/examples/test_example.py` ✅

### 2. **UIParser (Para casos avanzados)** 🔧

Para cuando necesitas control total sobre la interacción con la UI. Tú analizas la pantalla y decides qué hacer.

**Ventajas:**
- ✅ Control total sobre cada acción
- ✅ Útil para tests muy específicos o de bajo nivel
- ✅ Puedes inspeccionar exactamente qué elementos hay en pantalla

**Desventajas:**
- ❌ Más código y complejidad
- ❌ Necesitas entender XPath y estructura de la UI
- ❌ Debes manejar errores y esperas manualmente

---

## Método 1: Usando AITestRunner (Recomendado)

### Ejemplo Completo: Test de Login

Crea el archivo `tests/specs/spec_login_ai.py`:

```python
"""
Tests de login usando AITestRunner (método recomendado).
"""

import pytest
from src.test_runner import AITestRunner
from src.config import Config


@pytest.mark.integration
@pytest.mark.usefixtures("driver_setup")
class TestLoginAI:
    """Tests de login usando el agente de IA."""

    def test_login_exitoso(self, driver_setup):
        """
        Verifica que el usuario pueda hacer login exitosamente.
        
        Este test usa AITestRunner que ejecuta las acciones
        automáticamente basándose en instrucciones en lenguaje natural.
        """
        # Definir objetivo general del test
        objective = "Realizar login en la aplicación con credenciales de prueba"
        
        # Obtener credenciales desde variables de entorno
        test_email = Config.TEST_USER_EMAIL
        test_password = Config.TEST_USER_PASSWORD
        
        # Crear el runner con el driver y objetivo
        runner = AITestRunner(driver=driver_setup, objective=objective)
        
        # Definir el plan de prueba en lenguaje natural
        test_plan = [
            "Esperar a ver la pantalla de login",
            f"Ingresar usuario '{test_email}'",
            f"Ingresar password '{test_password}'",
            "Tocar botón Ingresar",
            "Verificar que se inició la sesión correctamente",
        ]
        
        # Ejecutar el plan
        success = runner.run_test_plan(test_plan)
        
        # Verificar que todos los pasos se completaron
        assert success, "El plan de prueba no se completó exitosamente"

    def test_navegacion_menu(self, driver_setup):
        """Ejemplo de navegación simple usando el agente."""
        runner = AITestRunner(driver=driver_setup)
        
        test_plan = [
            "Abrir el menú principal",
            "Seleccionar la opción 'Configuración'",
            "Verificar que se abra la pantalla de configuración",
        ]
        
        success = runner.run_test_plan(test_plan)
        assert success, "La navegación no se completó exitosamente"
```

### Ejecutar el Test

```bash
# Ejecutar solo este test
poetry run pytest tests/specs/spec_login_ai.py::TestLoginAI::test_login_exitoso -v

# Ejecutar todos los tests de la clase
poetry run pytest tests/specs/spec_login_ai.py -v
```

### Ver Ejemplo Funcional Completo

El archivo `tests/specs/examples/test_example.py` contiene ejemplos funcionales completos que puedes usar como referencia:

```bash
# Ver el archivo de ejemplo
cat tests/specs/examples/test_example.py

# Ejecutar los ejemplos
poetry run pytest tests/specs/examples/test_example.py -v
```

### Ejemplo: Escribir un Test desde una Historia de Usuario (AC-001)

Supongamos la siguiente historia de usuario:

> **AC-001**: Como usuario de la plataforma debo poder iniciar sesión en la APP como cliente y poder cerrar sesión correctamente.

Para convertirla en un test usando `AITestRunner`:

- **1. Define el objetivo del test**:
  - Usa una cadena que resuma la historia y mencione el ID:
  - `objective = "Validar historia de usuario AC-001: inicio y cierre de sesión en la app de cliente..."`
- **2. Usa credenciales de prueba desde `Config`**:
  - `test_email = Config.TEST_USER_EMAIL`
  - `test_password = Config.TEST_USER_PASSWORD`
- **3. Crea un `test_plan` de happy-path** (un paso → una acción/verificación):
  - Abrir la app de cliente usando `activate_app` con el paquete configurado (la app no se abre sola).
  - Esperar a ver la pantalla de inicio de sesión.
  - Ingresar el correo válido del cliente en el campo de correo.
  - Ingresar la contraseña válida en el campo de contraseña.
  - Tocar el botón de iniciar sesión.
  - Verificar que se muestra la pantalla principal del cliente (login exitoso).
  - Abrir el menú de cuenta o perfil.
  - Seleccionar la opción de cerrar sesión.
  - Confirmar el cierre de sesión si aparece un diálogo.
  - Verificar que la app regresa a la pantalla de inicio de sesión.

Este flujo está implementado como ejemplo completo en `tests/specs/spec_login_logout.py` (`TestLoginLogoutSpec::test_login_and_logout_cliente_ac001`). A partir de este patrón puedes crear otros specs para historias como "recuperar contraseña", "actualizar perfil", etc., siempre empezando por el happy-path y luego añadiendo tests separados para validaciones y errores.

---

## Método 2: Usando UIParser (Avanzado)

Si necesitas más control sobre la interacción con la UI, puedes usar `UIParser` directamente.

## Estructura de un Test

Cada prueba en este proyecto tiene una estructura básica:

```python
import pytest
from tests.conftest import allure_attach_debug_snapshot

class TestMiFuncionalidad:
    """Descripción de qué prueba esta clase."""

    @pytest.mark.integration  # Marca que necesita dispositivo
    def test_nombre_descriptivo(self, driver_setup):
        """Descripción de qué hace este test específico."""
        driver = driver_setup

        # 1. Preparar - Configurar el estado inicial
        # 2. Actuar - Ejecutar la acción a probar
        # 3. Verificar - Comprobar que el resultado es correcto
```

### Anatomía de un test

```python
@pytest.mark.integration                    # 1. Markers
def test_login_exitoso(self, driver_setup): # 2. Nombre descriptivo + fixture
    """Usuario puede iniciar sesión."""     # 3. Docstring explicativo
    driver = driver_setup                   # 4. Obtener el driver

    # Preparar
    usuario = "test@example.com"
    password = "123456"

    # Actuar
    # ... código de la prueba ...

    # Verificar
    assert "Bienvenido" in driver.page_source
```

---

## Live Coding: Tu Primera Prueba

Vamos a crear una prueba de login paso a paso. Abre tu editor de código y sigue estos pasos.

### Paso 1: Crear el archivo de test

**Para tests del proyecto:** Crea un archivo con prefijo `test_*.py`:
- `tests/test_login.py` - Test del framework/proyecto

**Para tests de usuario:** Crea un archivo con prefijo `spec_*.py`:
- `tests/specs/spec_login.py` - Test de usuario (especificación de funcionalidad)

En este ejemplo, crearemos `tests/specs/spec_login.py` (test de usuario):

```python
"""
Tests de funcionalidad de Login.
"""

import time
import pytest
from src.ui_parser import UIParser
from tests.conftest import (
    allure_attach_screenshot,
    allure_attach_page_source,
    allure_attach_debug_snapshot
)
```

**¿Qué hace cada import?**
- `time` - Para hacer pausas mientras la app carga
- `pytest` - Framework de testing
- `UIParser` - Para analizar la pantalla del celular
- `allure_*` - Para capturar evidencia (screenshots, XML)

### Paso 2: Crear la clase de test

```python
class TestLogin:
    """Tests para la funcionalidad de login de la aplicación."""

    @pytest.mark.integration
    def test_pantalla_login_carga_correctamente(self, driver_setup):
        """Verifica que la pantalla de login muestre los elementos esperados."""
        driver = driver_setup

        # Esperar a que la app cargue
        time.sleep(3)

        # Capturar screenshot para evidencia
        allure_attach_screenshot(driver, "pantalla_login")
```

**Buenas prácticas aplicadas:**
- ✅ Nombre de clase descriptivo: `TestLogin`
- ✅ Docstring explicando qué prueba la clase
- ✅ Marker `@pytest.mark.integration` porque usa dispositivo
- ✅ Nombre de test que describe qué verifica
- ✅ Captura de evidencia con Allure

### Paso 3: Agregar el parser de pantalla

```python
    @pytest.mark.integration
    def test_pantalla_login_carga_correctamente(self, driver_setup):
        """Verifica que la pantalla de login muestre los elementos esperados."""
        driver = driver_setup

        # Esperar a que la app cargue
        time.sleep(3)

        # Capturar screenshot para evidencia
        allure_attach_screenshot(driver, "pantalla_login")

        # Obtener y parsear la pantalla
        xml_source = driver.page_source
        parser = UIParser()
        elementos = parser.parse_screen(xml_source)

        # Mostrar qué elementos encontró (útil para debug)
        print(f"\n📱 Elementos encontrados: {len(elementos)}")
        for elem in elementos[:5]:  # Mostrar solo los primeros 5
            print(f"   resource-id: {elem['resource-id']}")
            print(f"   class: {elem['class']}")
            print(f"   text: {elem['text']}")
```

**¿Qué hace este código?**
1. `driver.page_source` - Obtiene el XML de la pantalla actual
2. `UIParser()` - Crea un analizador de pantalla
3. `parse_screen()` - Convierte el XML complejo en una lista simple de elementos

### Paso 4: Agregar verificaciones (asserts)

```python
    @pytest.mark.integration
    def test_pantalla_login_carga_correctamente(self, driver_setup):
        """Verifica que la pantalla de login muestre los elementos esperados."""
        driver = driver_setup

        # Esperar a que la app cargue
        time.sleep(3)

        # Capturar screenshot para evidencia
        allure_attach_screenshot(driver, "pantalla_login")

        # Obtener y parsear la pantalla
        xml_source = driver.page_source
        parser = UIParser()
        elementos = parser.parse_screen(xml_source)

        # Mostrar qué elementos encontró
        print(f"\n📱 Elementos encontrados: {len(elementos)}")
        for elem in elementos[:5]:
            print(f"   resource-id: {elem['resource-id']}")
            print(f"   class: {elem['class']}")
            print(f"   text: {elem['text']}")

        # VERIFICACIONES
        # 1. Debe haber al menos un elemento
        assert len(elementos) > 0, "La pantalla no tiene elementos interactuables"

        # 2. Debe haber campos de entrada (para usuario y contraseña)
        inputs = [e for e in elementos if 'edittext' in e['class'].lower()]
        assert len(inputs) >= 2, f"Se esperaban al menos 2 inputs, encontrados: {len(inputs)}"

        # 3. Debe haber un botón (para hacer login)
        botones = [e for e in elementos if 'button' in e['class'].lower()]
        assert len(botones) >= 1, f"Se esperaba al menos 1 botón, encontrados: {len(botones)}"
```

**Buenas prácticas en asserts:**
- ✅ Un concepto por assert (separar verificaciones)
- ✅ Mensaje descriptivo si falla: `"Se esperaban al menos 2 inputs..."`
- ✅ Información útil en el mensaje: `f"encontrados: {len(inputs)}"`

### Paso 5: Ejecutar el test

Guarda el archivo y ejecuta:

```bash
# Si creaste spec_login.py (test de usuario)
poetry run pytest tests/specs/spec_login.py -v

# O si creaste test_login.py (test del proyecto)
poetry run pytest tests/test_login.py -v
```

**Resultado esperado:**
```
tests/specs/spec_login.py::TestLogin::test_pantalla_login_carga_correctamente PASSED

📱 Elementos encontrados: 5
   resource-id: com.app:id/email
   class: android.widget.EditText
   text:
   resource-id: com.app:id/password
   class: android.widget.EditText
   text:
   resource-id: com.app:id/login_button
   class: android.widget.Button
   text: Ingresar
```

---

## Agregar Más Tests

Ahora que tienes el primer test funcionando, agreguemos más:

### Test: Ingresar Credenciales

```python
    @pytest.mark.integration
    def test_ingresar_credenciales(self, driver_setup):
        """Verifica que se puedan ingresar usuario y contraseña."""
        driver = driver_setup

        # Esperar carga inicial
        time.sleep(3)
        allure_attach_screenshot(driver, "01_antes_de_ingresar")

        # Obtener elementos
        parser = UIParser()
        elementos = parser.parse_screen(driver.page_source)

        # Encontrar campos de input
        inputs = [e for e in elementos if 'edittext' in e['class'].lower()]

        # Obtener XPath del primer input (usuario)
        xpath_usuario = inputs[0]['xpath']
        campo_usuario = driver.find_element("xpath", xpath_usuario)

        # Escribir en el campo
        campo_usuario.send_keys("test@example.com")

        # Capturar después de escribir
        time.sleep(0.5)
        allure_attach_screenshot(driver, "02_despues_de_usuario")

        # Verificar que el texto se ingresó
        assert "test@example.com" in driver.page_source or campo_usuario.text == "test@example.com"
```

### Test: Hacer clic en botón

```python
    @pytest.mark.integration
    def test_clic_boton_login(self, driver_setup):
        """Verifica que se pueda hacer clic en el botón de login."""
        driver = driver_setup

        time.sleep(3)

        # Parsear pantalla
        parser = UIParser()
        elementos = parser.parse_screen(driver.page_source)

        # Encontrar botón de login
        botones = [e for e in elementos if 'button' in e['class'].lower()]
        boton_login = None

        for boton in botones:
            # Buscar por text o resource-id que contenga "login", "ingresar", etc.
            texto_boton = boton['text'].lower()
            id_boton = boton['resource-id'].lower()
            if any(palabra in texto_boton or palabra in id_boton for palabra in ['login', 'ingresar', 'entrar', 'sign']):
                boton_login = boton
                break

        assert boton_login is not None, "No se encontró el botón de login"

        # Obtener XPath y hacer clic
        xpath_boton = boton_login['xpath']
        elemento_boton = driver.find_element("xpath", xpath_boton)

        allure_attach_screenshot(driver, "01_antes_del_clic")

        elemento_boton.click()

        time.sleep(2)
        allure_attach_screenshot(driver, "02_despues_del_clic")
```

---

## Mejores Prácticas

### 1. Nombres Descriptivos

```python
# ❌ Malo
def test_1(self):
def test_login(self):

# ✅ Bueno
def test_login_con_credenciales_validas_redirige_a_home(self):
def test_login_con_password_incorrecto_muestra_error(self):
```

### 2. Un Assert por Concepto

```python
# ❌ Malo - Demasiado en un solo assert
assert len(inputs) >= 2 and len(botones) >= 1 and "login" in page_source.lower()

# ✅ Bueno - Separados y claros
assert len(inputs) >= 2, "Debe haber campos de usuario y contraseña"
assert len(botones) >= 1, "Debe haber un botón de login"
assert "login" in page_source.lower(), "Debe estar en la pantalla de login"
```

### 3. Usar Markers Correctamente

```python
@pytest.mark.unit        # No necesita dispositivo
def test_parser_xml():
    pass

@pytest.mark.integration # Necesita dispositivo + Appium
def test_login_real():
    pass

@pytest.mark.slow        # Tarda más de 30 segundos
def test_flujo_completo():
    pass
```

### 4. Capturar Evidencia en Puntos Clave

```python
def test_flujo_login(self, driver_setup):
    driver = driver_setup

    # Punto clave 1: Estado inicial
    allure_attach_debug_snapshot(driver, "01_inicio")

    # ... hacer acciones ...

    # Punto clave 2: Después de ingresar datos
    allure_attach_debug_snapshot(driver, "02_datos_ingresados")

    # ... más acciones ...

    # Punto clave 3: Resultado final
    allure_attach_debug_snapshot(driver, "03_resultado")
```

### 5. Esperas Inteligentes

```python
# ❌ Malo - Espera fija siempre
time.sleep(10)

# ✅ Mejor - Espera hasta que aparezca algo
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

wait = WebDriverWait(driver, timeout=10)
elemento = wait.until(
    EC.presence_of_element_located(("xpath", "//android.widget.Button"))
)
```

### 6. Manejo de Errores con Evidencia

```python
def test_con_manejo_errores(self, driver_setup):
    driver = driver_setup

    try:
        # Tu código de prueba aquí
        pass
    except Exception as e:
        # Capturar evidencia del error
        allure_attach_debug_snapshot(driver, "ERROR_estado_al_fallar")
        raise  # Re-lanzar la excepción para que el test falle
```

---

## Archivo Completo de Ejemplo

Aquí está el archivo `tests/specs/spec_login.py` completo (test de usuario):

```python
"""
Tests de funcionalidad de Login.

Estos tests verifican que la pantalla de login funcione correctamente,
incluyendo la carga de elementos, ingreso de credenciales y navegación.
"""

import time
import pytest
from src.ui_parser import UIParser
from tests.conftest import (
    allure_attach_screenshot,
    allure_attach_page_source,
    allure_attach_debug_snapshot
)


class TestLogin:
    """Tests para la funcionalidad de login de la aplicación."""

    @pytest.mark.integration
    def test_pantalla_login_carga_correctamente(self, driver_setup):
        """Verifica que la pantalla de login muestre los elementos esperados."""
        driver = driver_setup

        # Esperar a que la app cargue
        time.sleep(3)

        # Capturar evidencia inicial
        allure_attach_debug_snapshot(driver, "pantalla_login")

        # Obtener y parsear la pantalla
        xml_source = driver.page_source
        parser = UIParser()
        elementos = parser.parse_screen(xml_source)

        # Mostrar qué elementos encontró
        print(f"\n📱 Elementos encontrados: {len(elementos)}")
        for elem in elementos[:5]:
            print(f"   resource-id: {elem['resource-id']}")
            print(f"   class: {elem['class']}")
            print(f"   text: {elem['text']}")

        # Verificaciones
        assert len(elementos) > 0, "La pantalla no tiene elementos interactuables"

        inputs = [e for e in elementos if 'edittext' in e['class'].lower()]
        assert len(inputs) >= 1, f"Se esperaba al menos 1 input, encontrados: {len(inputs)}"

        botones = [e for e in elementos if 'button' in e['class'].lower()]
        assert len(botones) >= 1, f"Se esperaba al menos 1 botón, encontrados: {len(botones)}"

    @pytest.mark.integration
    def test_elementos_son_interactuables(self, driver_setup):
        """Verifica que los elementos de login sean interactuables."""
        driver = driver_setup

        time.sleep(3)

        parser = UIParser()
        elementos = parser.parse_screen(driver.page_source)

        # Verificar que hay elementos
        assert len(elementos) > 0, "No hay elementos en la pantalla"

        # Verificar que cada elemento tiene las propiedades requeridas
        required_fields = ['resource-id', 'class', 'xpath', 'clickable', 'text']
        for elem in elementos:
            for field in required_fields:
                assert field in elem, f"Elemento sin {field}"
            assert elem['class'] != "", "Elemento sin class válido"

    @pytest.mark.integration
    @pytest.mark.slow
    def test_flujo_login_completo(self, driver_setup):
        """Test de flujo completo: cargar pantalla, ver elementos, interactuar."""
        driver = driver_setup

        # Paso 1: Esperar carga
        time.sleep(3)
        allure_attach_debug_snapshot(driver, "01_carga_inicial")

        # Paso 2: Parsear pantalla
        parser = UIParser()
        elementos = parser.parse_screen(driver.page_source)

        print(f"\n📱 Elementos en pantalla de login:")
        for elem in elementos[:5]:
            print(f"   resource-id: {elem['resource-id']}")
            print(f"   class: {elem['class']}")
            print(f"   text: {elem['text']}")

        # Paso 3: Verificar estructura
        assert len(elementos) > 0, "Pantalla vacía"

        # Paso 4: Capturar evidencia final
        allure_attach_debug_snapshot(driver, "02_analisis_completo")

        print("\n✅ Flujo de login verificado correctamente")
```

---

## Ejecutar los Tests

### Todos los tests de login

```bash
# Si usaste spec_*.py (tests de usuario)
poetry run pytest tests/specs/spec_login.py -v

# Si usaste test_*.py (tests del proyecto)
poetry run pytest tests/test_login.py -v
```

### Solo tests de integración

```bash
# Tests de usuario
poetry run pytest tests/specs/spec_login.py -v -m integration

# Tests del proyecto
poetry run pytest tests/test_login.py -v -m integration
```

### Ejecutar todos los specs de usuario

```bash
# Todos los tests de usuario (spec_*.py)
poetry run pytest tests/specs/spec_*.py -v

# Todos los tests del proyecto (test_*.py)
poetry run pytest tests/specs/test_*.py -v
```

### Con reporte de Allure

```bash
# Ejecutar tests
poetry run pytest tests/specs/spec_login.py -v

# Generar reporte
poetry run python scripts/generate_report.py

# Abrir reports/allure-report.html en el navegador
```

---

## ¿Cuál Método Usar?

### Usa AITestRunner cuando:
- ✅ Quieres escribir tests rápidamente
- ✅ Necesitas flujos completos de usuario
- ✅ No quieres preocuparte por selectores XPath
- ✅ Prefieres instrucciones en lenguaje natural

### Usa UIParser cuando:
- ✅ Necesitas control total sobre cada acción
- ✅ Quieres inspeccionar exactamente qué hay en pantalla
- ✅ Necesitas hacer verificaciones muy específicas
- ✅ Estás depurando problemas de UI

## Siguiente Paso

Ahora que sabes crear pruebas:

1. **Empieza con AITestRunner**: Revisa `tests/specs/examples/test_example.py` para ver ejemplos funcionales completos
2. Crea tests para otras funcionalidades de tu app
   - Usa `spec_*.py` para tests de usuario (funcionalidades de la app)
   - Usa `test_*.py` para tests del framework/proyecto
3. Explora el código de `tests/unit/test_ui_parser.py` para ver más ejemplos avanzados
4. Lee el [Glosario](02-glossary.md) si encuentras términos que no entiendes

**Nota sobre nombres de archivos:**
- Pytest reconoce automáticamente tanto `test_*.py` como `spec_*.py`
- Usa `spec_*.py` para tus tests de usuario (especificaciones de funcionalidad)
- Usa `test_*.py` para tests del proyecto (framework, componentes internos)
