"""
Comando para interfaz interactiva tipo chat.
"""

import click
import sys
import subprocess
import requests
from typing import List, Optional
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.live import Live
from rich.layout import Layout
from rich.prompt import Prompt
from rich.table import Table
from prompt_toolkit import prompt as ptk_prompt
from prompt_toolkit.styles import Style
from prompt_toolkit.history import FileHistory
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory

from src.config import Config

console = Console()
history_file = ".qa-agent-history"


def print_welcome():
    """Muestra mensaje de bienvenida."""
    welcome_text = """
# 🤖 QA Mobile Agent - Interfaz Interactiva

Bienvenido a la consola interactiva de QA Mobile Agent.

**Comandos disponibles:**
- `test <descripción>` - Ejecutar un test (ej: `test "Login con email y password"`)
- `generate <descripción>` - Generar archivo de test
- `status` - Ver estado de dispositivos y Appium
- `help` - Mostrar ayuda
- `exit` o `quit` - Salir

Escribe tu comando o pregunta:
"""
    console.print(Markdown(welcome_text))


def print_status():
    """Muestra el estado del sistema."""
    status_table = Table(title="Estado del Sistema")
    status_table.add_column("Componente", style="cyan")
    status_table.add_column("Estado", style="magenta")
    status_table.add_column("Detalles", style="green")
    
    # Verificar Appium
    try:
        response = requests.get(f"{Config.APPIUM_SERVER_URL}/status", timeout=5)
        if response.status_code == 200:
            status_table.add_row("Appium Server", "✅ Online", Config.APPIUM_SERVER_URL)
        else:
            status_table.add_row("Appium Server", "❌ Error", f"Status: {response.status_code}")
    except Exception as e:
        status_table.add_row("Appium Server", "❌ Offline", str(e)[:50])
    
    # Verificar dispositivos
    try:
        result = subprocess.run(
            ["adb", "devices"],
            capture_output=True,
            text=True,
            timeout=5
        )
        lines = result.stdout.strip().split('\n')[1:]
        devices = [line for line in lines if line.strip() and '\tdevice' in line]
        device_count = len(devices)
        if device_count > 0:
            status_table.add_row("Dispositivos Android", f"✅ {device_count} conectado(s)", ", ".join([d.split('\t')[0] for d in devices[:3]]))
        else:
            status_table.add_row("Dispositivos Android", "⚠️ Ninguno", "Conecta un dispositivo o inicia un emulador")
    except Exception as e:
        status_table.add_row("Dispositivos Android", "❌ Error", str(e)[:50])
    
    # Configuración
    status_table.add_row("AI Provider", Config.DEFAULT_AI_PROVIDER.upper(), Config.ANDROID_DEVICE_NAME)
    if Config.ANDROID_APP_PACKAGE:
        status_table.add_row("App Package", Config.ANDROID_APP_PACKAGE, Config.ANDROID_APP_ACTIVITY or "")
    
    console.print(status_table)


def execute_test_command(description: str):
    """Ejecuta un test desde descripción."""
    console.print(f"\n[cyan]🚀 Ejecutando test:[/cyan] [yellow]{description}[/yellow]\n")
    
    # Aquí podrías integrar con el test runner
    # Por ahora, mostramos un mensaje
    console.print("[yellow]⚠️ Ejecución de test desde chat aún no implementada completamente.[/yellow]")
    console.print("[yellow]Usa 'qa-agent run' para ejecutar tests.[/yellow]\n")


def generate_test_command(description: str):
    """Genera un archivo de test."""
    console.print(f"\n[cyan]📝 Generando test:[/cyan] [yellow]{description}[/yellow]\n")
    
    # Usar el generador existente
    from cli.utils.test_writer import TestWriter
    from pathlib import Path
    
    try:
        output_dir = Path("tests/specs/examples")
        output_dir.mkdir(parents=True, exist_ok=True)
        
        name = "test_" + description.lower().replace(" ", "_").replace(".", "").replace(",", "")[:50] + ".py"
        output_path = output_dir / name
        
        TestWriter.write_test_file(description, output_path)
        console.print(f"[green]✅ Archivo generado:[/green] {output_path}\n")
    except Exception as e:
        console.print(f"[red]❌ Error:[/red] {e}\n")


def print_help():
    """Muestra ayuda."""
    help_text = """
## 📚 Comandos Disponibles

**`test <descripción>`**
  Ejecuta un test desde una descripción en lenguaje natural
  Ejemplo: `test "Login con email test@example.com y password 123456"`

**`generate <descripción>`**
  Genera un archivo de test Python
  Ejemplo: `generate "Flujo completo de registro de usuario"`

**`status`**
  Muestra el estado actual de dispositivos y Appium

**`clear`**
  Limpia la pantalla

**`help`**
  Muestra esta ayuda

**`exit` o `quit`**
  Sale de la consola interactiva

## 💡 Tips

- Puedes usar el historial con las flechas ↑↓
- Usa Tab para autocompletar
- Los comandos son case-insensitive
"""
    console.print(Markdown(help_text))


def interactive_chat():
    """Loop principal de la interfaz interactiva."""
    print_welcome()
    
    # Crear estilo para prompt
    style = Style.from_dict({
        'prompt': 'bold cyan',
        'input': 'white',
    })
    
    while True:
        try:
            # Prompt con historial y autosugerencia
            user_input = ptk_prompt(
                "\n[QA Agent] > ",
                style=style,
                history=FileHistory(history_file),
                auto_suggest=AutoSuggestFromHistory(),
            ).strip()
            
            if not user_input:
                continue
            
            # Parsear comando
            parts = user_input.split(maxsplit=1)
            command = parts[0].lower()
            args = parts[1] if len(parts) > 1 else ""
            
            if command in ['exit', 'quit', 'q']:
                console.print("\n[cyan]👋 ¡Hasta luego![/cyan]\n")
                break
            elif command == 'clear' or command == 'cls':
                console.clear()
                print_welcome()
            elif command == 'help' or command == '?':
                print_help()
            elif command == 'status':
                print_status()
            elif command == 'test':
                if args:
                    execute_test_command(args)
                else:
                    console.print("[red]❌ Error:[/red] Debes proporcionar una descripción del test\n")
            elif command == 'generate' or command == 'gen':
                if args:
                    generate_test_command(args)
                else:
                    console.print("[red]❌ Error:[/red] Debes proporcionar una descripción\n")
            else:
                console.print(f"[yellow]⚠️ Comando desconocido:[/yellow] {command}")
                console.print("[yellow]Escribe 'help' para ver los comandos disponibles[/yellow]\n")
                
        except KeyboardInterrupt:
            console.print("\n\n[cyan]👋 ¡Hasta luego![/cyan]\n")
            break
        except EOFError:
            console.print("\n\n[cyan]👋 ¡Hasta luego![/cyan]\n")
            break
        except Exception as e:
            console.print(f"\n[red]❌ Error:[/red] {e}\n")


@click.command()
def chat():
    """
    Inicia la interfaz interactiva tipo chat.
    
    Una consola interactiva donde puedes conversar con el agente,
    ejecutar tests, generar archivos y más, todo en una sesión continua.
    """
    try:
        interactive_chat()
    except KeyboardInterrupt:
        console.print("\n\n[cyan]👋 ¡Hasta luego![/cyan]\n")
        sys.exit(0)
    except Exception as e:
        console.print(f"\n[red]❌ Error fatal:[/red] {e}\n")
        sys.exit(1)
