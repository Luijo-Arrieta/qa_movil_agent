# Crear Pruebas con Live Coding

Esta guía te enseñará cómo escribir tus propias pruebas automáticas paso a paso, siguiendo las mejores prácticas del proyecto.

## Antes de Empezar

Asegúrate de tener:
- [ ] El emulador Android corriendo
- [ ] Appium iniciado (`appium --use-plugins=all`)
- [ ] El proyecto instalado (`poetry install`)
- [ ] El archivo `.env.local` configurado

---

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

## Siguiente Paso

Ahora que sabes crear pruebas:

1. Crea tests para otras funcionalidades de tu app
   - Usa `spec_*.py` para tests de usuario (funcionalidades de la app)
   - Usa `test_*.py` para tests del framework/proyecto
2. Explora el código de `tests/unit/test_ui_parser.py` para ver más ejemplos
3. Lee el [Glosario](02-glossary.md) si encuentras términos que no entiendes

**Nota sobre nombres de archivos:**
- Pytest reconoce automáticamente tanto `test_*.py` como `spec_*.py`
- Usa `spec_*.py` para tus tests de usuario (especificaciones de funcionalidad)
- Usa `test_*.py` para tests del proyecto (framework, componentes internos)
