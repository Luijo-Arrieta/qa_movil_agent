# Interfaz Interactiva de Consola - QA Mobile Agent

## Descripción

La interfaz interactiva tipo chat permite interactuar con QA Mobile Agent de forma continua en una sesión interactiva, similar a Bugster, Claude Code, o Gemini CLI.

## Instalación

Las dependencias necesarias ya están en `pyproject.toml`:
- `rich` - Para UI bonita en terminal
- `prompt-toolkit` - Para prompt interactivo con historial

Instalar:
```bash
poetry install
```

## Uso

### Iniciar la consola interactiva

```bash
qa-agent chat
```

O usando Poetry:
```bash
poetry run qa-agent chat
```

### Comandos Disponibles

#### `test <descripción>`
Ejecuta un test desde una descripción en lenguaje natural.

**Ejemplo:**
```
[QA Agent] > test "Login con email test@example.com y password 123456"
```

#### `generate <descripción>` o `gen <descripción>`
Genera un archivo de test Python desde una descripción.

**Ejemplo:**
```
[QA Agent] > generate "Flujo completo de registro de usuario"
```

#### `status`
Muestra el estado actual del sistema:
- Estado de Appium Server
- Dispositivos Android conectados
- Configuración actual (AI Provider, Device Name, App Package)

**Ejemplo:**
```
[QA Agent] > status
```

#### `help` o `?`
Muestra la ayuda con todos los comandos disponibles.

#### `clear` o `cls`
Limpia la pantalla y muestra el mensaje de bienvenida nuevamente.

#### `exit`, `quit` o `q`
Sale de la consola interactiva.

**Ejemplo:**
```
[QA Agent] > exit
```

## Características

### ✨ Interfaz Visual
- Colores y formato bonito usando Rich
- Tablas formateadas para el estado
- Markdown para ayuda

### 📜 Historial de Comandos
- Historial automático de comandos
- Navegar con las flechas ↑↓
- Autocompletado con Tab

### 💬 Sesión Continua
- Puedes ejecutar múltiples comandos en una sola sesión
- El estado se mantiene durante la sesión
- Salir cuando quieras con `exit`

## Ejemplo de Sesión Completa

```
$ qa-agent chat

# 🤖 QA Mobile Agent - Interfaz Interactiva

Bienvenido a la consola interactiva de QA Mobile Agent.

**Comandos disponibles:**
- `test <descripción>` - Ejecutar un test
- `generate <descripción>` - Generar archivo de test
- `status` - Ver estado de dispositivos y Appium
- `help` - Mostrar ayuda
- `exit` o `quit` - Salir

[QA Agent] > status

┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃                  Estado del Sistema                        ┃
┣━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┫
┃ Componente         │ Estado  │ Detalles                    ┃
┣━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┫
┃ Appium Server      │ ✅ Online │ http://localhost:4723     ┃
┃ Dispositivos       │ ✅ 1 conectado(s) │ emulator-5554     ┃
┃ AI Provider        │ OPENAI   │ emulator-5554              ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛

[QA Agent] > generate "Test de login básico"

📝 Generando test: Test de login básico

✅ Archivo generado: tests/specs/examples/test_test_de_login_basico.py

[QA Agent] > help

## 📚 Comandos Disponibles

**`test <descripción>`**
  Ejecuta un test desde una descripción...

[QA Agent] > exit

👋 ¡Hasta luego!
```

## Notas

- El historial se guarda en `.qa-agent-history` (agregado a `.gitignore`)
- Los comandos son case-insensitive
- Puedes usar comillas simples o dobles para descripciones con espacios
- La interfaz es completamente interactiva y responsive
