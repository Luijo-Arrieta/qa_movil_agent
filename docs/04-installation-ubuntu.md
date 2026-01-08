# Instalación en Ubuntu/Linux

Guía completa paso a paso para instalar todas las herramientas necesarias en Ubuntu 20.04/22.04 o derivados de Debian.

**Tiempo estimado:** 30-45 minutos

## Resumen de lo que instalaremos

1. Python 3.8 o superior
2. Poetry (gestor de dependencias)
3. Java JDK 11 o superior
4. Android SDK (sin Android Studio)
5. Node.js 18 o superior
6. Appium 2.0
7. El proyecto AutoDroid-AI Agent

---

## Paso 1: Actualizar el Sistema

Antes de empezar, actualicemos el sistema. Abre una terminal (`Ctrl + Alt + T`) y ejecuta:

```bash
sudo apt update && sudo apt upgrade -y
```

Espera a que termine (puede pedir tu contraseña).

---

## Paso 2: Instalar Python

Ubuntu generalmente viene con Python, pero verificaremos y/o instalaremos la versión correcta.

### Verificar si ya tienes Python

```bash
python3 --version
```

Si ves `Python 3.8.x` o superior, puedes saltar al siguiente paso.

### Instalar Python (si es necesario)

```bash
sudo apt install python3 python3-pip python3-venv -y
```

### Verificar instalación

```bash
python3 --version
```

**Resultado esperado:**
```
Python 3.10.x
```

---

## Paso 3: Instalar Poetry

Poetry es el gestor de dependencias que usa el proyecto.

### Instalación

```bash
curl -sSL https://install.python-poetry.org | python3 -
```

### Agregar Poetry al PATH

Agrega esta línea al final de tu archivo `~/.bashrc`:

```bash
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
```

Recarga la configuración:

```bash
source ~/.bashrc
```

### Verificar instalación

```bash
poetry --version
```

**Resultado esperado:**
```
Poetry (version 1.x.x)
```

---

## Paso 4: Instalar Java JDK

Android requiere Java para funcionar.

### Instalación

```bash
sudo apt install openjdk-17-jdk -y
```

### Configurar JAVA_HOME

Agrega estas líneas al final de `~/.bashrc`:

```bash
echo 'export JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64' >> ~/.bashrc
echo 'export PATH="$JAVA_HOME/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
```

> **Nota:** Si tienes un procesador ARM (como en algunas laptops nuevas), reemplaza `amd64` por `arm64`.

### Verificar instalación

```bash
java -version
```

**Resultado esperado:**
```
openjdk version "17.0.x" 2024-xx-xx
OpenJDK Runtime Environment (build 17.0.x...)
```

```bash
echo $JAVA_HOME
```

**Resultado esperado:**
```
/usr/lib/jvm/java-17-openjdk-amd64
```

---

## Paso 5: Instalar Android SDK (sin Android Studio)

En Linux podemos instalar solo el SDK sin necesidad del IDE completo.

### Crear directorio para Android SDK

```bash
mkdir -p ~/Android/Sdk
cd ~/Android/Sdk
```

### Descargar Command Line Tools

```bash
wget https://dl.google.com/android/repository/commandlinetools-linux-11076708_latest.zip
unzip commandlinetools-linux-11076708_latest.zip
mkdir -p cmdline-tools/latest
mv cmdline-tools/* cmdline-tools/latest/ 2>/dev/null || true
rm commandlinetools-linux-11076708_latest.zip
```

### Configurar variables de entorno

Agrega estas líneas al final de `~/.bashrc`:

```bash
cat << 'EOF' >> ~/.bashrc

# Android SDK
export ANDROID_HOME=$HOME/Android/Sdk
export ANDROID_SDK_ROOT=$ANDROID_HOME
export PATH="$ANDROID_HOME/cmdline-tools/latest/bin:$PATH"
export PATH="$ANDROID_HOME/platform-tools:$PATH"
export PATH="$ANDROID_HOME/emulator:$PATH"
EOF

source ~/.bashrc
```

### Instalar componentes del SDK

Primero, acepta las licencias:

```bash
yes | sdkmanager --licenses
```

Luego, instala los componentes necesarios:

```bash
sdkmanager "platform-tools" "platforms;android-34" "build-tools;34.0.0" "emulator" "system-images;android-34;google_apis;x86_64"
```

> **Nota:** Este paso descargará varios GB. Puede tardar 10-20 minutos dependiendo de tu conexión.

### Crear un Emulador (AVD)

```bash
avdmanager create avd -n phone_test -k "system-images;android-34;google_apis;x86_64" -d pixel_4
```

Cuando pregunte si quieres personalizar la configuración, escribe `no` y presiona Enter.

### Verificar instalación

```bash
adb --version
```

**Resultado esperado:**
```
Android Debug Bridge version 1.0.41
```

```bash
emulator -list-avds
```

**Resultado esperado:**
```
phone_test
```

---

## Paso 6: Instalar Node.js

Appium requiere Node.js para funcionar.

### Instalación usando NodeSource

```bash
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt install -y nodejs
```

### Verificar instalación

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

## Paso 7: Instalar Appium

### Instalar Appium globalmente

```bash
sudo npm install -g appium
```

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

## Paso 8: Clonar e Instalar el Proyecto

### Instalar Git (si no lo tienes)

```bash
sudo apt install git -y
```

### Clonar el repositorio

```bash
cd ~
git clone https://github.com/tu-organizacion/qa_movil_agent.git
cd qa_movil_agent
```

### Instalar dependencias

```bash
poetry install
```

Espera a que se instalen todas las dependencias (puede tardar 2-3 minutos).

### Crear archivo de configuración

1. Copia el archivo de ejemplo:
   ```bash
   cp .env.example .env.local
   ```

2. Abre `.env.local` con nano o tu editor preferido:
   ```bash
   nano .env.local
   ```

3. Configura al menos estas variables:
   ```
   AI_PROVIDER=openai
   OPENAI_API_KEY=sk-tu-api-key-aqui

   ANDROID_DEVICE_NAME=emulator-5554
   ANDROID_APP_PATH=/home/tu_usuario/ruta/a/tu/app.apk
   ```

4. Guarda con `Ctrl + O`, Enter, y cierra con `Ctrl + X`.

---

## Paso 9: Verificar que Todo Funciona

### 1. Habilitar KVM (para acelerar el emulador)

El emulador de Android necesita virtualización por hardware:

```bash
sudo apt install qemu-kvm -y
sudo adduser $USER kvm
```

**Importante:** Cierra sesión y vuelve a iniciar sesión para que el cambio surta efecto.

### 2. Iniciar el emulador

Abre una terminal y ejecuta:

```bash
emulator -avd phone_test
```

> **Primera vez:** La primera ejecución puede tardar varios minutos. Verás una ventana con el emulador de Android.

### 3. Verificar conexión ADB

En otra terminal:

```bash
adb devices
```

**Resultado esperado:**
```
List of devices attached
emulator-5554   device
```

### 4. Iniciar Appium

En otra terminal:

```bash
appium --use-plugins=all
```

Deja esta terminal abierta.

### 5. Ejecutar una prueba

En otra terminal:

```bash
cd ~/qa_movil_agent
# Ejecutar tests unitarios (no requieren Appium)
poetry run pytest tests/unit/ -v
```

**Resultado esperado:** Las pruebas unitarias deberían pasar.

---

## Solución de Problemas

### "emulator: command not found"

**Causa:** El emulador no está en el PATH.

**Solución:** Verifica que `~/.bashrc` tenga las variables de Android correctamente configuradas y ejecuta `source ~/.bashrc`.

### Error de KVM: "KVM is required to run this AVD"

**Causa:** La virtualización KVM no está habilitada o configurada.

**Solución:**
1. Verifica que KVM esté instalado: `ls -la /dev/kvm`
2. Si no existe, tu CPU puede no soportar virtualización o está deshabilitada en BIOS
3. Asegúrate de haber agregado tu usuario al grupo kvm y reiniciado sesión

### El emulador inicia pero está muy lento

**Causa:** No está usando aceleración por hardware.

**Solución:**
1. Verifica que KVM funcione: `kvm-ok`
2. Si dice "KVM acceleration can be used", está bien
3. Si no, revisa la configuración de tu BIOS (habilita VT-x o AMD-V)

### "JAVA_HOME is not set"

**Causa:** La variable de entorno no está configurada.

**Solución:**
```bash
echo 'export JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64' >> ~/.bashrc
source ~/.bashrc
```

### Error: "Unable to locate package nodejs"

**Causa:** El repositorio de NodeSource no se agregó correctamente.

**Solución:** Vuelve a ejecutar el comando de instalación de NodeSource del Paso 6.

### adb devices muestra "unauthorized"

**Causa:** El emulador no autorizó la conexión ADB.

**Solución:**
1. En el emulador, ve a Configuración > Opciones de desarrollador
2. Habilita "Depuración USB"
3. Si aparece un diálogo pidiendo autorización, acepta
4. Ejecuta de nuevo `adb devices`

---

## Script de Verificación Completa

Puedes crear este script para verificar que todo esté instalado:

```bash
#!/bin/bash
echo "=== Verificación de Instalación ==="
echo ""
echo "Python: $(python3 --version 2>/dev/null || echo 'NO INSTALADO')"
echo "Poetry: $(poetry --version 2>/dev/null || echo 'NO INSTALADO')"
echo "Java: $(java -version 2>&1 | head -1 || echo 'NO INSTALADO')"
echo "Node: $(node --version 2>/dev/null || echo 'NO INSTALADO')"
echo "npm: $(npm --version 2>/dev/null || echo 'NO INSTALADO')"
echo "Appium: $(appium --version 2>/dev/null || echo 'NO INSTALADO')"
echo "ADB: $(adb --version 2>/dev/null | head -1 || echo 'NO INSTALADO')"
echo ""
echo "JAVA_HOME: ${JAVA_HOME:-'NO CONFIGURADO'}"
echo "ANDROID_HOME: ${ANDROID_HOME:-'NO CONFIGURADO'}"
echo ""
echo "Emuladores disponibles:"
emulator -list-avds 2>/dev/null || echo "NO HAY EMULADORES"
```

Guárdalo como `check_install.sh`, dale permisos (`chmod +x check_install.sh`) y ejecútalo.

---

## Siguiente Paso

¡Felicidades! Ya tienes todo instalado. Ahora puedes:

1. Seguir el [Inicio Rápido](01-quick-start.md) para ejecutar tu primera prueba
2. Leer [Crear Pruebas](06-creating-tests.md) para escribir tus propias pruebas
