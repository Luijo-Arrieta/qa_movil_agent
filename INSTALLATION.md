# Guía de Instalación - QA Mobile Agent

Esta guía te ayudará a instalar y configurar QA Mobile Agent en tu sistema.

## Requisitos Previos

- Python 3.8 o superior
- Poetry (gestor de dependencias de Python)
- Appium Server
- Dispositivo Android o emulador
- API Key de OpenAI, Anthropic o DeepSeek

## Opción 1: Instalación como Paquete Python (Recomendado)

### 1. Instalar desde el código fuente

```bash
# Clonar el repositorio
git clone <repository-url>
cd qa-movil-agent

# Instalar dependencias
poetry install

# Activar el entorno virtual
poetry shell

# Verificar instalación
qa-agent --help
```

### 2. Instalar como paquete pip

```bash
# Si el paquete está publicado en PyPI
pip install qa-movil-agent

# O desde el código fuente
pip install .
```

## Opción 2: Instalación con Docker

### 1. Usar Docker Compose (Backend + Frontend)

```bash
# Clonar el repositorio
git clone <repository-url>
cd qa-movil-agent

# Copiar y configurar variables de entorno
cp .env.example .env
# Editar .env con tus API keys

# Iniciar servicios
docker-compose up -d

# Ver logs
docker-compose logs -f

# Acceder a:
# - Frontend: http://localhost:3000
# - Backend API: http://localhost:8000
# - API Docs: http://localhost:8000/docs
```

### 2. Solo Backend con Docker

```bash
# Construir imagen
docker build -f Dockerfile.backend -t qa-mobile-agent-backend .

# Ejecutar contenedor
docker run -d \
  -p 8000:8000 \
  -e OPENAI_API_KEY=sk-... \
  -e APPIUM_SERVER_URL=http://host.docker.internal:4723 \
  -v $(pwd)/tests:/app/tests \
  qa-mobile-agent-backend
```

## Opción 3: Binario Standalone (CLI)

### Generar binario (desde el código fuente)

```bash
# Instalar PyInstaller
poetry add --group dev pyinstaller

# Ejecutar script de build
./scripts/build_cli.sh

# El binario estará en dist/qa-agent (Linux/Mac) o dist/qa-agent.exe (Windows)
```

### Usar el binario

```bash
# Linux/Mac
./dist/qa-agent --help

# Windows
dist\qa-agent.exe --help
```

## Configuración Inicial

### 1. Crear archivo de configuración

```bash
# Inicializar proyecto
qa-agent init

# Esto creará:
# - tests/specs/examples/ (directorio para tests)
# - .env.example (template de configuración)
# - test_login.yaml (ejemplo)
```

### 2. Configurar variables de entorno

```bash
# Copiar template
cp .env.example .env.local

# Editar con tus valores
nano .env.local
```

**Variables requeridas:**

```env
# Proveedor de IA (openai, anthropic, deepseek)
AI_PROVIDER=openai

# API Key según el proveedor
OPENAI_API_KEY=sk-...
# O
ANTHROPIC_API_KEY=sk-ant-...
# O
DEEPSEEK_API_KEY=sk-...

# Configuración de Appium
APPIUM_SERVER_URL=http://localhost:4723
ANDROID_DEVICE_NAME=emulator-5554
```

### 3. Verificar configuración

```bash
# Verificar estado de dispositivos y Appium
qa-agent status
```

## Primeros Pasos

### 1. Ejecutar un test desde YAML

```bash
# Crear archivo de test
cat > test_example.yaml << EOF
objective: "Realizar login en la aplicación"
test_plan:
  - "Esperar a ver la pantalla de login"
  - "Ingresar usuario 'test@example.com'"
  - "Ingresar password 'password123'"
  - "Tocar botón Ingresar"
  - "Verificar que se inició la sesión"
EOF

# Ejecutar test
qa-agent run test_example.yaml
```

### 2. Modo interactivo

```bash
qa-agent run --interactive
```

### 3. Generar archivo de test

```bash
qa-agent generate "Flujo de login con email y password"
```

## Uso del Backend API

### Iniciar servidor

```bash
# Con Poetry
poetry run uvicorn backend.main:app --host 0.0.0.0 --port 8000

# O con Python directamente
python -m backend.main
```

### Acceder a documentación

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

### Ejemplo de uso de la API

```bash
# Ejecutar test
curl -X POST http://localhost:8000/api/v1/tests/execute \
  -H "Content-Type: application/json" \
  -d '{
    "test_plan": [
      "Ingresar usuario test@example.com",
      "Ingresar password 123456",
      "Tocar botón Ingresar"
    ]
  }'

# Ver resultado
curl http://localhost:8000/api/v1/results/{test_id}
```

## Uso del Frontend Web

### Desarrollo

```bash
cd frontend
npm install
npm run dev

# Acceder a http://localhost:5173
```

### Producción

```bash
cd frontend
npm install
npm run build

# El build estará en frontend/dist/
# Servir con cualquier servidor web estático o usar Docker
```

## Solución de Problemas

### Error: "Appium Server no está disponible"

```bash
# Verificar que Appium esté corriendo
curl http://localhost:4723/status

# Si no está corriendo, iniciarlo:
appium --use-plugins=all
```

### Error: "No hay dispositivos conectados"

```bash
# Verificar dispositivos
adb devices

# Si no hay dispositivos:
# 1. Conecta un dispositivo físico vía USB
# 2. O inicia un emulador Android
emulator -avd <AVD_NAME>
```

### Error: "API_KEY no está configurada"

Verifica que el archivo `.env.local` exista y contenga la API key correcta para el proveedor seleccionado.

## Soporte

Para más información:
- Documentación completa: Ver `README.md`
- Issues: [GitHub Issues](https://github.com/your-repo/issues)
