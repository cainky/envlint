"""CLI interface for envlint."""

from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from envlint import __version__
from envlint.parser import EnvParseError, find_env_file, get_actual_env, load_env
from envlint.schema import SchemaParseError, find_schema_file, load_schema
from envlint.validator import ValidationResult, validate

app = typer.Typer(
    name="envlint",
    help="Validate .env files against a schema. Never deploy with missing env vars again.",
    add_completion=False,
)

console = Console()
error_console = Console(stderr=True)


def print_result(result: ValidationResult, verbose: bool = False):
    """Print validation result with nice formatting."""
    if result.is_valid and not result.warnings:
        console.print(
            Panel(
                f"[green]All {result.validated_count} variables validated successfully[/green]",
                title="envlint",
                border_style="green",
            )
        )
        return

    # Print errors
    if result.errors:
        table = Table(title="Errors", border_style="red", title_style="bold red")
        table.add_column("Variable", style="cyan")
        table.add_column("Error", style="red")
        table.add_column("Value", style="dim")

        for error in result.errors:
            actual = error.actual if error.actual else "-"
            if len(actual) > 30:
                actual = actual[:27] + "..."
            table.add_row(error.variable, error.message, actual)

        console.print(table)
        console.print()

    # Print warnings
    if result.warnings and verbose:
        table = Table(title="Warnings", border_style="yellow", title_style="bold yellow")
        table.add_column("Variable", style="cyan")
        table.add_column("Warning", style="yellow")

        for warning in result.warnings:
            table.add_row(warning.variable, warning.message)

        console.print(table)
        console.print()

    # Summary
    summary_parts = []
    if result.errors:
        summary_parts.append(f"[red]{len(result.errors)} error(s)[/red]")
    if result.warnings:
        summary_parts.append(f"[yellow]{len(result.warnings)} warning(s)[/yellow]")
    if result.validated_count:
        summary_parts.append(f"[green]{result.validated_count} valid[/green]")

    summary = " | ".join(summary_parts)

    if result.is_valid:
        console.print(Panel(summary, title="envlint", border_style="yellow"))
    else:
        console.print(Panel(summary, title="envlint", border_style="red"))


@app.command()
def check(
    env_file: Path | None = typer.Option(
        None,
        "--env",
        "-e",
        help="Path to .env file (auto-detected if not specified)",
    ),
    schema_file: Path | None = typer.Option(
        None,
        "--schema",
        "-s",
        help="Path to schema file (auto-detected if not specified)",
    ),
    use_system_env: bool = typer.Option(
        False,
        "--system",
        "-S",
        help="Also check system environment variables",
    ),
    strict: bool = typer.Option(
        False,
        "--strict",
        help="Fail on undefined variables in .env",
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="Show warnings and detailed output",
    ),
    quiet: bool = typer.Option(
        False,
        "--quiet",
        "-q",
        help="Only output on error",
    ),
):
    """Validate .env file against schema.

    Exits with code 0 if valid, 1 if errors found.
    """
    # Find schema file
    if schema_file is None:
        schema_file = find_schema_file()
        if schema_file is None:
            error_console.print(
                "[red]Error:[/red] No schema file found. "
                "Create .env.schema or specify with --schema"
            )
            raise typer.Exit(1)
        if verbose:
            console.print(f"[dim]Using schema: {schema_file}[/dim]")

    # Load schema
    try:
        schema = load_schema(schema_file)
    except SchemaParseError as e:
        error_console.print(f"[red]Schema error:[/red] {e}")
        raise typer.Exit(1)

    if strict:
        schema.strict = True

    # Find and load env file
    env_vars: dict[str, str] = {}

    if env_file is None:
        env_file = find_env_file()

    if env_file is not None:
        try:
            env_vars = load_env(env_file)
            if verbose:
                console.print(f"[dim]Using env file: {env_file}[/dim]")
        except EnvParseError as e:
            error_console.print(f"[red]Env file error:[/red] {e}")
            raise typer.Exit(1)

    # Optionally include system env vars
    if use_system_env:
        system_vars = get_actual_env(list(schema.variables.keys()))
        # System env vars take precedence
        env_vars = {**env_vars, **system_vars}
        if verbose:
            console.print(f"[dim]Loaded {len(system_vars)} system env vars[/dim]")

    if not env_vars and not use_system_env:
        error_console.print("[red]Error:[/red] No .env file found and --system not specified")
        raise typer.Exit(1)

    # Validate
    result = validate(env_vars, schema)

    if not quiet or not result.is_valid:
        print_result(result, verbose=verbose)

    raise typer.Exit(0 if result.is_valid else 1)


@app.command()
def init(
    output: Path = typer.Option(
        Path(".env.schema"),
        "--output",
        "-o",
        help="Output file path",
    ),
    from_env: Path | None = typer.Option(
        None,
        "--from-env",
        "-f",
        help="Generate schema from existing .env file",
    ),
):
    """Initialize a new schema file.

    Creates a .env.schema template or generates one from an existing .env file.
    """
    if output.exists():
        overwrite = typer.confirm(f"{output} already exists. Overwrite?")
        if not overwrite:
            raise typer.Exit(0)

    if from_env:
        # Generate schema from .env file
        try:
            env_vars = load_env(from_env)
        except EnvParseError as e:
            error_console.print(f"[red]Error:[/red] {e}")
            raise typer.Exit(1)

        lines = ["# Generated schema from " + str(from_env), ""]
        for var_name, value in env_vars.items():
            # Try to infer type
            inferred_type = "string"
            if value.lower() in ("true", "false", "yes", "no", "on", "off", "1", "0"):
                inferred_type = "bool"
            elif value.isdigit() or (value.startswith("-") and value[1:].isdigit()):
                inferred_type = "int"
            elif "@" in value and "." in value.split("@")[-1]:
                inferred_type = "email"
            elif value.startswith(("http://", "https://")):
                inferred_type = "url"

            lines.append(f"{var_name}:")
            lines.append(f"  type: {inferred_type}")
            lines.append("  required: true")
            lines.append("")

        content = "\n".join(lines)
    else:
        # Create template
        content = """# envlint schema file
# Documentation: https://github.com/cainky/envlint

# Example variable definitions:

DATABASE_URL:
  type: url
  required: true
  description: PostgreSQL connection string

API_KEY:
  type: string
  required: true
  pattern: "^[a-zA-Z0-9]{32}$"
  description: API key for external service

PORT:
  type: port
  required: false
  default: "3000"
  description: Server port

DEBUG:
  type: bool
  required: false
  default: "false"

NODE_ENV:
  type: string
  required: true
  choices:
    - development
    - staging
    - production

# Shorthand syntax examples:
# SECRET_KEY: string
# MAX_RETRIES: int
# ADMIN_EMAIL: email
"""

    output.write_text(content)
    console.print(f"[green]Created schema file:[/green] {output}")


@app.command()
def version():
    """Show version information."""
    console.print(f"envlint {__version__}")


def main():
    """Entry point."""
    app()


if __name__ == "__main__":
    main()
