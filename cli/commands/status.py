"""
Comando para verificar estado de dispositivos y Appium.
"""

import click
import subprocess
import requests
from src.config import Config


@click.command()
def status():
    """
    Muestra el estado de dispositivos Android conectados y del servidor Appium.
    """
    click.echo("=== Estado de QA Mobile Agent ===\n")
    
    # Verificar Appium
    click.echo("📱 Appium Server:")
    try:
        response = requests.get(f"{Config.APPIUM_SERVER_URL}/status", timeout=5)
        if response.status_code == 200:
            click.echo(f"  ✅ Disponible en {Config.APPIUM_SERVER_URL}")
            try:
                data = response.json()
                if 'value' in data and 'build' in data['value']:
                    version = data['value']['build'].get('version', 'N/A')
                    click.echo(f"  Versión: {version}")
            except:
                pass
        else:
            click.echo(f"  ❌ No responde correctamente (status: {response.status_code})")
    except Exception as e:
        click.echo(f"  ❌ No disponible: {e}")
        click.echo(f"  💡 Inicia Appium con: appium --use-plugins=all")
    
    # Listar dispositivos
    click.echo("\n📱 Dispositivos Android:")
    try:
        result = subprocess.run(
            ["adb", "devices"],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        lines = result.stdout.strip().split('\n')[1:]  # Saltar header
        
        devices = []
        for line in lines:
            if not line.strip():
                continue
            parts = line.split('\t')
            if len(parts) >= 2:
                device_id = parts[0]
                device_status = parts[1]
                devices.append((device_id, device_status))
        
        if devices:
            for device_id, device_status in devices:
                if device_status == "device":
                    click.echo(f"  ✅ {device_id} - Online")
                else:
                    click.echo(f"  ⚠️  {device_id} - {device_status}")
        else:
            click.echo("  ⚠️  No hay dispositivos conectados")
            click.echo("  💡 Conecta un dispositivo o inicia un emulador")
            
    except FileNotFoundError:
        click.echo("  ❌ ADB no encontrado en PATH")
    except subprocess.TimeoutExpired:
        click.echo("  ❌ Timeout ejecutando 'adb devices'")
    except Exception as e:
        click.echo(f"  ❌ Error: {e}")
    
    # Configuración actual
    click.echo("\n⚙️  Configuración:")
    click.echo(f"  AI Provider: {Config.DEFAULT_AI_PROVIDER}")
    click.echo(f"  Device Name: {Config.ANDROID_DEVICE_NAME}")
    if Config.ANDROID_APP_PACKAGE:
        click.echo(f"  App Package: {Config.ANDROID_APP_PACKAGE}")
    if Config.ANDROID_APP_ACTIVITY:
        click.echo(f"  App Activity: {Config.ANDROID_APP_ACTIVITY}")
