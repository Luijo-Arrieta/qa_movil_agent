"""
Comando para inicializar un proyecto de tests.
"""

import click
from pathlib import Path


@click.command()
@click.option('--directory', '-d', type=click.Path(), default='.', help='Directorio donde inicializar (default: actual)')
def init(directory):
    """
    Inicializa un nuevo proyecto de tests de QA Mobile Agent.
    
    Crea la estructura de directorios y archivos de configuración necesarios.
    """
    project_dir = Path(directory)
    
    click.echo(f"Inicializando proyecto en: {project_dir.absolute()}\n")
    
    # Crear estructura de directorios
    dirs = [
        "tests/specs/examples",
        "tests/unit",
        "results"
    ]
    
    for dir_path in dirs:
        full_path = project_dir / dir_path
        full_path.mkdir(parents=True, exist_ok=True)
        click.echo(f"✅ Creado: {dir_path}/")
    
    # Crear archivo .env.example si no existe
    env_example = project_dir / ".env.example"
    if not env_example.exists():
        env_content = """# Configuración de QA Mobile Agent

# Proveedor de IA
AI_PROVIDER=openai  # o "anthropic" o "deepseek"

# API Keys
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
DEEPSEEK_API_KEY=sk-...

# Configuración de Appium
APPIUM_SERVER_URL=http://localhost:4723
ANDROID_DEVICE_NAME=emulator-5554
ANDROID_UDID=emulator-5554

# Configuración de la App Android
ANDROID_APP_PACKAGE=com.example.app
ANDROID_APP_ACTIVITY=.MainActivity

# Credenciales de prueba (opcional)
TEST_USER_EMAIL=test@example.com
TEST_USER_PASSWORD=password123
"""
        env_example.write_text(env_content)
        click.echo(f"✅ Creado: .env.example")
        click.echo("  💡 Copia este archivo a .env.local y configura tus valores")
    
    # Crear archivo de ejemplo test_login.yaml
    example_yaml = project_dir / "tests" / "specs" / "examples" / "test_login.yaml"
    if not example_yaml.exists():
        yaml_content = """objective: "Realizar login en la aplicación"
test_plan:
  - "Esperar a ver la pantalla de login"
  - "Ingresar usuario 'test@example.com'"
  - "Ingresar password 'password123'"
  - "Tocar botón Ingresar"
  - "Verificar que se inició la sesión"
"""
        example_yaml.write_text(yaml_content)
        click.echo(f"✅ Creado: tests/specs/examples/test_login.yaml")
    
    click.echo("\n✅ Proyecto inicializado exitosamente!")
    click.echo("\nPróximos pasos:")
    click.echo("  1. Copia .env.example a .env.local y configura tus API keys")
    click.echo("  2. Asegúrate de tener Appium corriendo: appium --use-plugins=all")
    click.echo("  3. Conecta un dispositivo Android o inicia un emulador")
    click.echo("  4. Ejecuta un test: qa-agent run tests/specs/examples/test_login.yaml")
