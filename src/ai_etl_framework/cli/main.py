import click
from .commands.test_load import test_load

@click.group()
def cli():
    """AI ETL Framework CLI - Tools for ETL pipeline management."""
    pass

# Register commands
cli.add_command(test_load)

if __name__ == '__main__':
    cli()