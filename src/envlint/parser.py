"""Parser for .env files."""

from __future__ import annotations

import os
import re
from pathlib import Path


class EnvParseError(Exception):
    """Raised when .env parsing fails."""

    pass


def parse_env_line(line: str, line_num: int) -> tuple[str, str] | None:
    """Parse a single line from a .env file.

    Returns (key, value) tuple or None for empty/comment lines.
    """
    line = line.strip()

    # Skip empty lines and comments
    if not line or line.startswith("#"):
        return None

    # Handle export prefix
    if line.startswith("export "):
        line = line[7:].strip()

    # Find the = separator
    if "=" not in line:
        raise EnvParseError(f"Line {line_num}: Missing '=' separator")

    key, _, value = line.partition("=")
    key = key.strip()

    if not key:
        raise EnvParseError(f"Line {line_num}: Empty variable name")

    if not re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", key):
        raise EnvParseError(
            f"Line {line_num}: Invalid variable name '{key}'. "
            "Must start with letter or underscore, contain only alphanumeric and underscore."
        )

    value = value.strip()

    # Handle quoted values
    if len(value) >= 2:
        if (value.startswith('"') and value.endswith('"')) or (
            value.startswith("'") and value.endswith("'")
        ):
            value = value[1:-1]
            # Handle escape sequences in double quotes
            if value.startswith('"'):
                value = value.replace("\\n", "\n")
                value = value.replace("\\t", "\t")
                value = value.replace('\\"', '"')
                value = value.replace("\\\\", "\\")

    return key, value


def parse_env(content: str) -> dict[str, str]:
    """Parse .env file content into a dictionary."""
    env_vars: dict[str, str] = {}

    for line_num, line in enumerate(content.splitlines(), start=1):
        result = parse_env_line(line, line_num)
        if result:
            key, value = result
            env_vars[key] = value

    return env_vars


def load_env(path: Path) -> dict[str, str]:
    """Load and parse a .env file."""
    if not path.exists():
        raise EnvParseError(f".env file not found: {path}")

    content = path.read_text(encoding="utf-8")
    return parse_env(content)


def find_env_file(start_dir: Path | None = None) -> Path | None:
    """Find .env file in current or parent directories."""
    if start_dir is None:
        start_dir = Path.cwd()

    env_names = [".env", ".env.local"]
    current = start_dir.resolve()

    while current != current.parent:
        for name in env_names:
            env_path = current / name
            if env_path.exists():
                return env_path
        current = current.parent

    return None


def get_actual_env(var_names: list[str]) -> dict[str, str]:
    """Get actual environment variables for given names."""
    return {name: os.environ[name] for name in var_names if name in os.environ}
