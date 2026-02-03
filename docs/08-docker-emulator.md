# Emulador Android en Docker (Guía de Portabilidad y Persistencia)

Esta guía explica cómo ejecutar un emulador de Android y un servidor de Appium totalmente funcionales usando Docker. Esta es la opción recomendada para equipos que no desean instalar Android Studio o el SDK de Android completo.

## Beneficios

- **Portabilidad**: El entorno es idéntico para todos los miembros del equipo.
- **Ligero**: Consume significativamente menos recursos que Android Studio.
- **Zero Install**: No requiere instalar SDKs, Platform Tools o Node.js en el sistema host.
- **Persistencia**: Gracias a los Volúmenes Nombrados de Docker, tus apps y configuraciones se mantienen incluso tras apagar el contenedor.

## Pre-requisitos

1. **Docker Desktop**: Instalado y configurado para usar el motor **WSL 2**.
2. **Virtualización (BIOS)**: Asegúrate de que `Intel VT-x` o `AMD-V` esté habilitado en la BIOS de tu PC.
3. **KVM en WSL2**:
   - Abre tu terminal (PowerShell o CMD) y escribe `wsl` para entrar a tu distribución de Linux.
   - Una vez dentro de Linux, ejecuta: `ls -l /dev/kvm`.
   - Deberías ver una salida similar a esta: `crw-rw---- 1 root kvm 10, 232 Feb  2 14:57 /dev/kvm`.
   - **Nota**: Si el archivo no existe o no tienes permisos, sal de WSL (`exit`) y ejecuta `wsl --update` en PowerShell como administrador.

## Configuración del `docker-compose.yml`

Asegúrate de tener esta estructura para garantizar la persistencia de datos:

```yaml
version: "3"
services:
  android-emulator:
    image: budtmo/docker-android:emulator_11.0
    container_name: android-container
    privileged: true
    ports:
      - "6080:6080"
      - "5555:5555"
      - "4723:4723"
    environment:
      - EMULATOR_DEVICE=Samsung Galaxy S10
      - WEB_VNC=true
      - APPIUM=true
    devices:
      - /dev/kvm
    volumes:
      - android_data:/home/androidusr

volumes:
  android_data: {}
```

## Uso Rápido

### 1. Iniciar el Emulador

En la raíz del proyecto, ejecuta:

```bash
docker compose up -d
```

### 2. Ver el Celular (Interfaz Gráfica)

Abre tu navegador y entra a:
👉 **[http://localhost:6080](http://localhost:6080)**

### 3. Verificar Conexión

No necesitas tener `adb` instalado en tu Windows. Puedes usar el que está dentro del contenedor:

```bash
docker exec android-container adb devices
```

## Gestión de Aplicaciones (Instalación)

Para instalar tus archivos APK sin tener herramientas de Android en Windows, usa estos dos pasos:

1. **Copiar el archivo al contenedor:**
   Los archivos APK deben estar en la carpeta `apks/` a nivel de raíz (según el estándar del proyecto).

   ```bash
   docker cp apks/tu-app.apk android-container:/tmp/
   ```

2. **Instalar el APK:**
   Si usas **Git Bash**, recuerda usar la doble barra `//` para evitar errores de ruta:
   ```bash
   docker exec android-container adb install //tmp/tu-app.apk
   ```

## Conexión con el Agente (Appium)

El contenedor ya incluye un servidor de Appium escuchando en el puerto `4723`. Configura tu archivo `.env.local` de la siguiente manera:

```ini
APPIUM_SERVER_URL=http://localhost:4723
ANDROID_DEVICE_NAME=emulator-5554
```

## Persistencia de Datos

Al usar **Volúmenes Nombrados** (`android_data`):

- Puedes hacer `docker compose down` y `docker compose up -d` sin perder tus apps instaladas.
- Los datos se guardan en un volumen gestionado por Docker, lo que evita problemas de permisos comunes entre Windows y Linux.

## Comandos Útiles

- **Reiniciar el celular (soft reboot):**
  ```bash
  docker exec android-container adb reboot
  ```
- **Ver logs del sistema:**
  ```bash
  docker logs -f android-container
  ```
