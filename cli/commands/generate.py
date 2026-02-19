"""
Comando para generar archivos de test.
"""

import click
import sys
from pathlib import Path
from cli.utils.test_writer import TestWriter


@click.command()
@click.argument('description')
@click.option('--name', '-n', help='Nombre del archivo de test (sin extensión)')
@click.option('--output', '-o', type=click.Path(), help='Directorio de salida (default: tests/specs/examples)')
@click.option('--from-file', '-f', type=click.Path(exists=True), help='Generar desde archivo de texto con descripción')
def generate(description, name, output, from_file):
    """
    Genera un archivo de test Python desde una descripción en lenguaje natural.
    
    DESCRIPTION: Descripción del test en lenguaje natural (ej: "Flujo de login con email y password")
    """
    # Si se proporciona archivo, leer la descripción desde ahí
    if from_file:
        try:
            with open(from_file, 'r', encoding='utf-8') as f:
                description = f.read().strip()
        except Exception as e:
            click.echo(f"Error leyendo archivo: {e}", err=True)
            sys.exit(1)
    
    # Determinar nombre del archivo
    if not name:
        # Generar nombre desde descripción
        name = "test_" + description.lower().replace(" ", "_").replace(".", "").replace(",", "")[:50]
        if not name.endswith('.py'):
            name += '.py'
    elif not name.endswith('.py'):
        name += '.py'
    
    # Determinar directorio de salida
    if output:
        output_dir = Path(output)
    else:
        output_dir = Path("tests/specs/examples")
    
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / name
    
    # Verificar si el archivo ya existe
    if output_path.exists():
        if not click.confirm(f"El archivo {output_path} ya existe. ¿Sobrescribir?"):
            click.echo("Operación cancelada.")
            sys.exit(0)
    
    # Generar archivo
    try:
        TestWriter.write_test_file(
            description=description,
            file_path=output_path
        )
        click.echo(f"✅ Archivo de test generado: {output_path}")
    except Exception as e:
        click.echo(f"❌ Error generando archivo: {e}", err=True)
        sys.exit(1)
