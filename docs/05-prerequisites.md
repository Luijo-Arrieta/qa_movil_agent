# Prerequisitos

Esta guía detalla todo lo que necesitas tener instalado antes de usar AutoDroid-AI Agent, con enlaces de descarga y comandos de verificación.

## Resumen Rápido

| Herramienta | Versión Mínima | ¿Para qué se usa? |
|-------------|----------------|-------------------|
| Python | 3.8+ | Lenguaje de programación del proyecto |
| Poetry | 1.0+ | Gestiona las dependencias de Python |
| Java JDK | 11+ | Requerido por Android SDK |
| Android SDK | API 30+ | Herramientas para controlar Android |
| Node.js | 18+ | Requerido por Appium |
| Appium | 2.0+ | Controla el dispositivo Android |
| API Key | - | Acceso a OpenAI o Anthropic |

---

## 1. Python 3.8+

### ¿Qué es?
Python es el lenguaje de programación en el que está escrito el proyecto. Necesitas tenerlo instalado para ejecutar las pruebas.

### Descarga

| Sistema | Enlace |
|---------|--------|
| Windows | [Microsoft Store - Python](https://apps.microsoft.com/store/detail/python-311/9NRWMJP3717K) |
| Windows (alternativo) | [python.org/downloads](https://www.python.org/downloads/) |
| Ubuntu/Debian | Ya viene instalado o `sudo apt install python3` |
| macOS | `brew install python` o [python.org](https://www.python.org/downloads/) |

### Verificar instalación

```bash
# Windows
python --version

# Linux/macOS
python3 --version
```

**Resultado esperado:** `Python 3.8.x` o superior

### Solución de problemas

**"python no se reconoce como comando" (Windows)**
- Reinstala Python desde Microsoft Store, o
- Si usaste el instalador de python.org, asegúrate de marcar "Add Python to PATH"

**"command not found" (Linux)**
```bash
sudo apt install python3 python3-pip python3-venv
```

---

## 2. Poetry 1.0+

### ¿Qué es?
Poetry es un gestor de dependencias para Python. Es como npm para Node.js o Maven para Java. Instala y gestiona todas las librerías que necesita el proyecto.

### Descarga

El comando de instalación es el mismo para todos los sistemas:

```bash
# Windows (en PowerShell)
(Invoke-WebRequest -Uri https://install.python-poetry.org -UseBasicParsing).Content | python -

# Linux/macOS
curl -sSL https://install.python-poetry.org | python3 -
```

### Configuración post-instalación

Después de instalar, agrega Poetry al PATH:

**Windows:**
Agrega `%APPDATA%\Python\Scripts` al PATH del sistema.

**Linux/macOS:**
```bash
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
```

### Verificar instalación

```bash
poetry --version
```

**Resultado esperado:** `Poetry (version 1.x.x)`

### Solución de problemas

**"poetry: command not found"**
- Verifica que agregaste Poetry al PATH
- Cierra y vuelve a abrir la terminal

---

## 3. Java JDK 11+

### ¿Qué es?
Java es un lenguaje de programación que Android usa internamente. Aunque no escribirás código Java, el SDK de Android lo necesita para funcionar.

### Descarga

| Sistema | Enlace |
|---------|--------|
| Windows | [Adoptium.net](https://adoptium.net/) - Haz clic en "Latest LTS Release" |
| Ubuntu/Debian | `sudo apt install openjdk-17-jdk` |
| macOS | `brew install openjdk@17` |

### Verificar instalación

```bash
java -version
```

**Resultado esperado:** `openjdk version "17.x.x"` o similar

```bash
# Verificar JAVA_HOME
# Windows
echo %JAVA_HOME%

# Linux/macOS
echo $JAVA_HOME
```

**Resultado esperado:** Una ruta como `/usr/lib/jvm/java-17-openjdk-amd64` o `C:\Program Files\Eclipse Adoptium\jdk-17...`

### Solución de problemas

**"JAVA_HOME is not set"**

Windows:
1. Busca dónde está instalado Java (usualmente `C:\Program Files\Eclipse Adoptium\jdk-17...`)
2. Crea una variable de entorno llamada `JAVA_HOME` con esa ruta

Linux:
```bash
echo 'export JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64' >> ~/.bashrc
source ~/.bashrc
```

---

## 4. Android SDK

### ¿Qué es?
El SDK (Software Development Kit) de Android incluye todas las herramientas para desarrollar y probar aplicaciones Android: el emulador, ADB, y más.

### Descarga

**Opción A: Android Studio (recomendado para Windows)**
- [developer.android.com/studio](https://developer.android.com/studio)
- Incluye el SDK y una interfaz gráfica para crear emuladores

**Opción B: Solo Command Line Tools (recomendado para Linux)**
- [developer.android.com/studio#command-line-tools-only](https://developer.android.com/studio#command-line-tools-only)
- Más ligero, solo las herramientas de línea de comandos

### Configuración

Después de instalar, necesitas configurar `ANDROID_HOME`:

**Windows:**
Variable de entorno `ANDROID_HOME` = `C:\Users\TU_USUARIO\AppData\Local\Android\Sdk`

**Linux:**
```bash
export ANDROID_HOME=$HOME/Android/Sdk
export PATH="$ANDROID_HOME/platform-tools:$PATH"
export PATH="$ANDROID_HOME/emulator:$PATH"
```

### Verificar instalación

```bash
adb --version
```

**Resultado esperado:** `Android Debug Bridge version 1.0.41`

```bash
emulator -list-avds
```

**Resultado esperado:** Lista de emuladores creados (puede estar vacía si no has creado ninguno)

### Crear un emulador

**Con Android Studio:**
1. Abre Android Studio
2. Ve a Tools > Device Manager
3. Clic en "Create device"
4. Selecciona un dispositivo (ej: Pixel 4)
5. Selecciona una imagen del sistema (ej: API 34)
6. Finaliza

**Con Command Line:**
```bash
sdkmanager "system-images;android-34;google_apis;x86_64"
avdmanager create avd -n phone_test -k "system-images;android-34;google_apis;x86_64" -d pixel_4
```

---

## 5. Node.js 18+

### ¿Qué es?
Node.js es un entorno de ejecución de JavaScript. Appium está escrito en JavaScript, por lo que necesita Node.js para funcionar.

### Descarga

| Sistema | Enlace |
|---------|--------|
| Windows | [nodejs.org](https://nodejs.org/) - Descarga la versión LTS |
| Ubuntu/Debian | Ver instrucciones abajo |
| macOS | `brew install node` o [nodejs.org](https://nodejs.org/) |

**Ubuntu/Debian:**
```bash
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt install -y nodejs
```

### Verificar instalación

```bash
node --version
```

**Resultado esperado:** `v18.x.x` o superior

```bash
npm --version
```

**Resultado esperado:** `9.x.x` o superior

---

## 6. Appium 2.0+

### ¿Qué es?
Appium es la herramienta que permite controlar dispositivos móviles (Android/iOS) desde código. Es el puente entre tu código Python y el celular.

### Instalación

Una vez que tienes Node.js instalado:

```bash
# Instalar Appium
npm install -g appium

# Instalar el driver de Android
appium driver install uiautomator2
```

### Verificar instalación

```bash
appium --version
```

**Resultado esperado:** `2.x.x`

```bash
appium driver list --installed
```

**Resultado esperado:**
```
✔ uiautomator2
```

### Solución de problemas

**"appium: command not found"**
- Verifica que Node.js esté instalado correctamente
- Intenta reinstalar: `npm install -g appium`

**El driver no se instaló**
```bash
appium driver install uiautomator2
```

---

## 7. API Key (OpenAI o Anthropic)

### ¿Qué es?
Una API Key es una "contraseña" que te permite usar los servicios de inteligencia artificial de OpenAI (GPT-4) o Anthropic (Claude).

### Obtener API Key de OpenAI

1. Ve a [platform.openai.com](https://platform.openai.com/)
2. Crea una cuenta o inicia sesión
3. Ve a Settings > API Keys
4. Clic en "Create new secret key"
5. Copia la clave (empieza con `sk-...`)

> **Importante:** La clave solo se muestra una vez. Guárdala en un lugar seguro.

### Obtener API Key de Anthropic

1. Ve a [console.anthropic.com](https://console.anthropic.com/)
2. Crea una cuenta o inicia sesión
3. Ve a Settings > API Keys
4. Clic en "Create Key"
5. Copia la clave (empieza con `sk-ant-...`)

### Configurar en el proyecto

Crea o edita el archivo `.env.local` en la raíz del proyecto:

```bash
# Para OpenAI
AI_PROVIDER=openai
OPENAI_API_KEY=sk-tu-clave-aqui

# Para Anthropic
AI_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-tu-clave-aqui
```

### Verificar que funciona

La API Key se verificará automáticamente cuando ejecutes una prueba que use la IA. Si hay un error de autenticación, verifica que:
- Copiaste la clave completa (sin espacios al inicio o final)
- La clave no ha expirado
- Tienes créditos disponibles en tu cuenta

---

## 8. Dispositivo Android

### Opciones

**Opción A: Emulador (recomendado para desarrollo)**
- Celular virtual en tu computadora
- Gratuito
- Fácil de reiniciar si algo sale mal
- Requiere computadora con buena CPU y RAM

**Opción B: Dispositivo físico**
- Celular Android real conectado por USB
- Más rápido que el emulador
- Necesitas habilitar "Depuración USB" en el celular

### Requisitos del emulador

Para que el emulador funcione bien:
- CPU con soporte de virtualización (VT-x o AMD-V)
- Mínimo 8 GB de RAM (16 GB recomendado)
- Virtualización habilitada en BIOS

### Requisitos del dispositivo físico

Para usar un celular real:
1. Android 7.0 o superior
2. Cable USB de datos (no solo de carga)
3. Habilitar Opciones de desarrollador:
   - Ve a Configuración > Acerca del teléfono
   - Toca "Número de compilación" 7 veces
4. Habilitar Depuración USB:
   - Ve a Configuración > Opciones de desarrollador
   - Activa "Depuración USB"
5. Cuando conectes el celular, acepta la autorización de ADB

### Verificar conexión

```bash
adb devices
```

**Resultado esperado:**
```
List of devices attached
emulator-5554   device      # Si es emulador
ABC123XYZ       device      # Si es celular físico
```

Si dice `unauthorized`, acepta la autorización en el celular.

---

## Lista de Verificación Final

Usa esta lista para asegurarte de que todo está instalado:

```
[ ] Python 3.8+          → python --version / python3 --version
[ ] Poetry 1.0+          → poetry --version
[ ] Java JDK 11+         → java -version
[ ] JAVA_HOME configurado → echo $JAVA_HOME / echo %JAVA_HOME%
[ ] Android SDK          → adb --version
[ ] ANDROID_HOME configurado → echo $ANDROID_HOME / echo %ANDROID_HOME%
[ ] Emulador creado      → emulator -list-avds
[ ] Node.js 18+          → node --version
[ ] npm 9+               → npm --version
[ ] Appium 2.0+          → appium --version
[ ] Driver uiautomator2  → appium driver list --installed
[ ] API Key configurada  → Archivo .env.local creado
```

---

## Siguiente Paso

Una vez que tengas todo instalado:

1. Si usas **Windows**: Ve a [Instalación en Windows](03-installation-windows.md) para instrucciones detalladas
2. Si usas **Ubuntu/Linux**: Ve a [Instalación en Ubuntu](04-installation-ubuntu.md) para instrucciones detalladas
3. Si ya instalaste todo: Ve al [Inicio Rápido](01-quick-start.md) para ejecutar tu primera prueba
