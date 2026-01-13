# Instalación en Windows

Guía completa paso a paso para instalar todas las herramientas necesarias en Windows 10/11.

**Tiempo estimado:** 30-45 minutos

## Resumen de lo que instalaremos

1. Python 3.8 o superior
2. Poetry (gestor de dependencias)
3. Java JDK 11 o superior
4. Android Studio + SDK
5. Node.js 18 o superior
6. Appium 2.0
7. El proyecto AutoDroid-AI Agent

---

## Paso 1: Instalar Python

### Opción A: Desde Microsoft Store (Recomendado)

1. Abre **Microsoft Store** (búscalo en el menú inicio)
2. Busca **"Python 3.11"** (o la versión más reciente 3.x)
3. Haz clic en **"Obtener"** o **"Instalar"**
4. Espera a que termine la instalación

### Opción B: Desde python.org

1. Ve a [python.org/downloads](https://www.python.org/downloads/)
2. Haz clic en el botón amarillo **"Download Python 3.x.x"**
3. Ejecuta el archivo descargado
4. **MUY IMPORTANTE:** Marca la casilla **"Add Python to PATH"** antes de instalar
5. Haz clic en **"Install Now"**

### Verificar instalación

Abre una terminal (presiona `Windows + R`, escribe `cmd`, presiona Enter) y ejecuta:

```bash
python --version
```

**Resultado esperado:**
```
Python 3.11.x
```

Si ves un error o una versión menor a 3.8, la instalación no fue correcta.

---

## Paso 2: Instalar Poetry

Poetry es el gestor de dependencias que usa el proyecto.

### Instalación

1. Abre **PowerShell como Administrador**:
   - Presiona `Windows + X`
   - Selecciona **"Terminal (Admin)"** o **"Windows PowerShell (Admin)"**

2. Ejecuta este comando:

```powershell
(Invoke-WebRequest -Uri https://install.python-poetry.org -UseBasicParsing).Content | python -
```

3. Espera a que termine. Verás un mensaje indicando dónde se instaló Poetry.

### Agregar Poetry al PATH

1. Presiona `Windows + R`, escribe `sysdm.cpl` y presiona Enter
2. Ve a la pestaña **"Opciones avanzadas"**
3. Haz clic en **"Variables de entorno..."**
4. En "Variables de usuario", busca **"Path"** y haz clic en **"Editar..."**
5. Haz clic en **"Nuevo"** y agrega:
   ```
   %APPDATA%\Python\Scripts
   ```
6. Haz clic en **"Aceptar"** en todas las ventanas

### Verificar instalación

**Cierra todas las terminales** y abre una nueva. Luego ejecuta:

```bash
poetry --version
```

**Resultado esperado:**
```
Poetry (version 1.x.x)
```

---

## Paso 3: Instalar Java JDK

Android necesita Java para funcionar.

### Instalación

1. Ve a [Adoptium.net](https://adoptium.net/)
2. Haz clic en **"Latest LTS Release"** (debería descargar automáticamente)
3. Ejecuta el instalador descargado
4. En el instalador:
   - Acepta los términos
   - **Marca** la opción "Set JAVA_HOME variable"
   - **Marca** la opción "Add to PATH"
5. Haz clic en **"Install"**

### Verificar instalación

Cierra la terminal y abre una nueva:

```bash
java -version
```

**Resultado esperado:**
```
openjdk version "17.x.x" 2024-xx-xx
OpenJDK Runtime Environment Temurin-17...
```

También verifica JAVA_HOME:

```bash
echo %JAVA_HOME%
```

**Resultado esperado:** Una ruta como `C:\Program Files\Eclipse Adoptium\jdk-17...`

---

## Paso 4: Instalar Android Studio y SDK

### Instalar Android Studio

1. Ve a [developer.android.com/studio](https://developer.android.com/studio)
2. Haz clic en **"Download Android Studio"**
3. Acepta los términos y descarga el instalador
4. Ejecuta el instalador:
   - Acepta todas las opciones por defecto
   - Espera a que se descarguen los componentes (puede tardar 10-15 minutos)

### Configurar Android Studio (primera vez)

1. Abre Android Studio
2. Si te pregunta por importar configuración, selecciona **"Do not import settings"**
3. En el asistente de configuración:
   - Selecciona **"Standard"** installation
   - Acepta las licencias
   - Espera a que se descarguen los componentes

### Crear un Emulador (AVD)

1. En Android Studio, haz clic en **"More Actions"** (o el menú de tres puntos)
2. Selecciona **"Virtual Device Manager"**
3. Haz clic en **"Create device"**
4. Selecciona un dispositivo (recomendado: **Pixel 4** o similar)
5. Haz clic en **"Next"**
6. En la lista de imágenes del sistema:
   - Busca una con **"API 30"** o superior
   - Si no está descargada, haz clic en el ícono de descarga junto a ella
   - Espera a que se descargue
7. Selecciona la imagen y haz clic en **"Next"**
8. Dale un nombre al emulador (por ejemplo: `phone_test`)
9. Haz clic en **"Finish"**

### Configurar Variables de Entorno de Android

1. Presiona `Windows + R`, escribe `sysdm.cpl` y presiona Enter
2. Ve a **"Opciones avanzadas"** > **"Variables de entorno..."**
3. En **"Variables de usuario"**, haz clic en **"Nueva..."**:
   - Nombre: `ANDROID_HOME`
   - Valor: `C:\Users\TU_USUARIO\AppData\Local\Android\Sdk`
   - (Reemplaza `TU_USUARIO` con tu nombre de usuario de Windows)

4. Edita la variable **"Path"** y agrega estas líneas:
   ```
   %ANDROID_HOME%\platform-tools
   %ANDROID_HOME%\emulator
   %ANDROID_HOME%\tools
   %ANDROID_HOME%\tools\bin
   ```

### Verificar instalación

Cierra todas las terminales y abre una nueva:

```bash
adb --version
```

**Resultado esperado:**
```
Android Debug Bridge version 1.0.41
```

Verificar que el emulador se puede iniciar:

```bash
emulator -list-avds
```

**Resultado esperado:** El nombre del emulador que creaste (por ejemplo: `phone_test`)

---

## Paso 5: Instalar Node.js

Appium requiere Node.js para funcionar.

### Instalación

1. Ve a [nodejs.org](https://nodejs.org/)
2. Descarga la versión **LTS** (Long Term Support)
3. Ejecuta el instalador:
   - Acepta los términos
   - Usa la ubicación por defecto
   - **Marca** la opción "Automatically install necessary tools"
4. Completa la instalación

### Verificar instalación

Cierra la terminal y abre una nueva:

```bash
node --version
```

**Resultado esperado:**
```
v18.x.x
```

```bash
npm --version
```

**Resultado esperado:**
```
9.x.x
```

---

## Paso 6: Instalar Appium

### Instalar Appium globalmente

Abre una terminal y ejecuta:

```bash
npm install -g appium
```

Espera a que termine (puede tardar 1-2 minutos).

### Instalar el driver de Android

```bash
appium driver install uiautomator2
```

### Verificar instalación

```bash
appium --version
```

**Resultado esperado:**
```
2.x.x
```

```bash
appium driver list --installed
```

**Resultado esperado:**
```
✔ uiautomator2
```

---

## Paso 6.5: Instalar Allure CLI (para reportes)

Allure CLI se usa para generar reportes HTML interactivos de los tests.

### Instalar Allure CLI

1. Descarga Allure desde [GitHub Releases](https://github.com/allure-framework/allure2/releases)
2. Busca el archivo `allure-X.X.X.zip` (última versión, ej: `allure-2.36.0.zip`)
3. Descarga y descomprime en `C:\allure\`
   - Deberías tener: `C:\allure\allure-2.36.0\bin\allure.bat`

### Agregar Allure al PATH

1. Presiona `Windows + R`, escribe `sysdm.cpl` y presiona Enter
2. Ve a **"Opciones avanzadas"** > **"Variables de entorno..."**
3. Edita la variable **"Path"** (en Variables de usuario)
4. Haz clic en **"Nuevo"** y agrega:
   ```
   C:\allure\allure-2.36.0\bin
   ```
5. Haz clic en **"Aceptar"** en todas las ventanas

### Verificar instalación

Cierra todas las terminales y abre una nueva:

```bash
allure --version
```

**Resultado esperado:**
```
2.36.0
```

### Uso de Allure (después de ejecutar tests)

```bash
# Generar y abrir reporte automáticamente
allure serve reports/allure-results

# O generar HTML estático
allure generate reports/allure-results -o reports/allure-report --clean
```

---

## Paso 7: Clonar e Instalar el Proyecto

### Clonar el repositorio

Si tienes Git instalado:

```bash
cd D:\Imagine
git clone https://github.com/tu-organizacion/qa_movil_agent.git
cd qa_movil_agent
```

Si no tienes Git, descarga el proyecto como ZIP y descomprímelo en `D:\Imagine\qa_movil_agent`.

### Instalar dependencias

```bash
poetry install
```

Espera a que se instalen todas las dependencias (puede tardar 2-3 minutos).

### Crear archivo de configuración

1. Copia el archivo de ejemplo:
   ```bash
   copy .env.example .env.local
   ```

2. Abre `.env.local` con el Bloc de notas o tu editor preferido:
   ```bash
   notepad .env.local
   ```

3. Configura al menos estas variables:
   ```
   # Opción 1: OpenAI
   AI_PROVIDER=openai
   OPENAI_API_KEY=sk-tu-api-key-aqui

   # Opción 2: Anthropic
   # AI_PROVIDER=anthropic
   # ANTHROPIC_API_KEY=sk-ant-tu-api-key-aqui

   # Opción 3: DeepSeek
   # AI_PROVIDER=deepseek
   # DEEPSEEK_API_KEY=sk-tu-api-key-aqui

   ANDROID_DEVICE_NAME=emulator-5554
   
   # IMPORTANTE: La app debe estar instalada manualmente en el dispositivo/emulador
   ANDROID_APP_PACKAGE=com.tu.app.package
   ANDROID_APP_ACTIVITY=.MainActivity
   ```

4. Guarda y cierra el archivo.

---

## Paso 8: Verificar que Todo Funciona

### 1. Iniciar el emulador

Abre una terminal y ejecuta:

```bash
emulator -avd phone_test
```

Espera a que el emulador arranque completamente (aparecerá la pantalla de inicio de Android).

### 2. Verificar conexión ADB

En otra terminal:

```bash
adb devices
```

**Resultado esperado:**
```
List of devices attached
emulator-5554   device
```

### 3. Iniciar Appium

En otra terminal:

```bash
appium --use-plugins=all
```

Deja esta terminal abierta.

### 4. Ejecutar una prueba

En otra terminal:

```bash
cd D:\Imagine\qa_movil_agent
# Ejecutar tests unitarios (no requieren Appium)
poetry run pytest tests/unit/ -v
```

**Resultado esperado:** Las pruebas unitarias deberían pasar.

---

## Solución de Problemas

### "python no se reconoce como comando"

**Causa:** Python no está en el PATH.

**Solución:**
1. Reinstala Python desde Microsoft Store, o
2. Agrega manualmente Python al PATH:
   - Busca dónde está instalado Python (normalmente `C:\Users\TU_USUARIO\AppData\Local\Programs\Python\Python311`)
   - Agrega esa ruta al PATH siguiendo los pasos del Paso 2

### "emulator: command not found"

**Causa:** Las herramientas de Android SDK no están en el PATH.

**Solución:** Verifica que agregaste correctamente las rutas de Android al PATH (ver Paso 4).

### El emulador arranca pero no conecta con ADB

**Causa:** El emulador no terminó de iniciar o hay un problema de conexión.

**Solución:**
1. Espera 1-2 minutos a que el emulador cargue completamente
2. Ejecuta `adb kill-server` y luego `adb start-server`
3. Vuelve a ejecutar `adb devices`

### "JAVA_HOME is not set"

**Causa:** La variable de entorno JAVA_HOME no está configurada.

**Solución:** Reinstala Java asegurándote de marcar la opción "Set JAVA_HOME variable".

---

## Siguiente Paso

¡Felicidades! Ya tienes todo instalado. Ahora puedes:

1. Seguir el [Inicio Rápido](01-quick-start.md) para ejecutar tu primera prueba
2. Leer [Crear Pruebas](06-creating-tests.md) para escribir tus propias pruebas
