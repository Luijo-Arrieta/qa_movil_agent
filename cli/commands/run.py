"""
Comando para ejecutar tests.
"""

import click
import sys
import yaml
from pathlib import Path
from appium import webdriver
from appium.options.android import UiAutomator2Options

from src.test_runner import AITestRunner
from src.config import Config


@click.command()
@click.argument('test_file', type=click.Path(exists=True), required=False)
@click.option('--interactive', '-i', is_flag=True, help='Modo interactivo para definir test plan')
@click.option('--device', '-d', help='Nombre del dispositivo Android')
@click.option('--app-package', help='Package de la app Android')
@click.option('--app-activity', help='Activity principal de la app')
@click.option('--objective', '-o', help='Objetivo general del test')
def run(test_file, interactive, device, app_package, app_activity, objective):
    """
    Ejecuta un test desde un archivo YAML o Python, o en modo interactivo.
    
    TEST_FILE: Ruta al archivo de test (YAML o Python). Si no se proporciona y se usa --interactive, se abre el modo interactivo.
    """
    if not test_file and not interactive:
        click.echo("Error: Debes proporcionar un archivo de test o usar --interactive", err=True)
        sys.exit(1)
    
    # Verificar Appium
    try:
        import requests
        response = requests.get(f"{Config.APPIUM_SERVER_URL}/status", timeout=5)
        if response.status_code != 200:
            click.echo(f"Error: Appium Server no está disponible en {Config.APPIUM_SERVER_URL}", err=True)
            sys.exit(1)
    except Exception as e:
        click.echo(f"Error: No se puede conectar a Appium Server: {e}", err=True)
        click.echo("Asegúrate de que Appium esté corriendo: appium --use-plugins=all", err=True)
        sys.exit(1)
    
    test_plan = None
    
    if interactive:
        # Modo interactivo
        click.echo("=== Modo Interactivo ===")
        if not objective:
            objective = click.prompt("Objetivo del test", default="")
        
        click.echo("\nIngresa los pasos del test (una línea por paso).")
        click.echo("Presiona Enter en una línea vacía para terminar.\n")
        
        test_plan = []
        step_num = 1
        while True:
            step = click.prompt(f"Paso {step_num}", default="", show_default=False)
            if not step:
                break
            test_plan.append(step)
            step_num += 1
        
        if not test_plan:
            click.echo("Error: Debes proporcionar al menos un paso", err=True)
            sys.exit(1)
    else:
        # Leer desde archivo
        file_path = Path(test_file)
        
        if file_path.suffix == '.yaml' or file_path.suffix == '.yml':
            # Leer YAML
            with open(file_path, 'r') as f:
                data = yaml.safe_load(f)
                test_plan = data.get('test_plan', [])
                if not objective:
                    objective = data.get('objective')
        elif file_path.suffix == '.py':
            click.echo("Para ejecutar archivos Python, usa pytest directamente:", err=True)
            click.echo(f"  poetry run pytest {test_file}", err=True)
            sys.exit(1)
        else:
            click.echo(f"Error: Formato de archivo no soportado: {file_path.suffix}", err=True)
            sys.exit(1)
    
    # Crear driver
    click.echo("\n🚀 Iniciando ejecución del test...")
    
    capabilities = Config.get_appium_capabilities()
    
    # Override con parámetros CLI
    if device:
        capabilities["appium:deviceName"] = device
        capabilities["appium:udid"] = device
    
    if app_package:
        capabilities["appium:appPackage"] = app_package
    
    if app_activity:
        capabilities["appium:appActivity"] = app_activity
    
    options = UiAutomator2Options()
    for key, value in capabilities.items():
        options.set_capability(key, value)
    
    driver = None
    try:
        driver = webdriver.Remote(
            command_executor=Config.APPIUM_SERVER_URL,
            options=options
        )
        driver.implicitly_wait(Config.IMPLICIT_WAIT)
        
        # Crear runner
        runner = AITestRunner(driver=driver, objective=objective)
        
        # Ejecutar test
        click.echo(f"📋 Ejecutando {len(test_plan)} pasos...\n")
        success = runner.run_test_plan(test_plan)
        
        if success:
            click.echo("\n✅ Test completado exitosamente!")
            sys.exit(0)
        else:
            click.echo("\n❌ Test falló", err=True)
            sys.exit(1)
            
    except Exception as e:
        click.echo(f"\n❌ Error ejecutando test: {e}", err=True)
        sys.exit(1)
    finally:
        if driver:
            try:
                driver.quit()
            except:
                pass
