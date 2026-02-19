"""
CLI principal para QA Mobile Agent.
"""

import click
import sys
from cli.commands import run, generate, status, init, chat

CONTEXT_SETTINGS = dict(help_option_names=['-h', '--help'])


@click.group(context_settings=CONTEXT_SETTINGS)
@click.version_option(version='0.1.0')
def cli():
    """
    QA Mobile Agent - Agente de IA autónomo para ejecutar pruebas móviles en Android.
    
    Ejecuta tests, genera archivos de test y gestiona dispositivos Android usando IA.
    """
    pass


# Registrar comandos
cli.add_command(run.run)
cli.add_command(generate.generate)
cli.add_command(status.status)
cli.add_command(init.init)
cli.add_command(chat.chat)


def main():
    """Punto de entrada del CLI."""
    try:
        cli()
    except KeyboardInterrupt:
        click.echo('\n\nOperación cancelada por el usuario.', err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f'\n\nError: {e}', err=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
