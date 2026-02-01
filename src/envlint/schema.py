"""Schema parsing and definitions for envlint."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

import yaml


class VarType(Enum):
    """Supported variable types."""

    STRING = "string"
    INT = "int"
    FLOAT = "float"
    BOOL = "bool"
    URL = "url"
    EMAIL = "email"
    PORT = "port"
    PATH = "path"
    JWT = "jwt"
    SECRET = "secret"


@dataclass
class VarSchema:
    """Schema definition for a single environment variable."""

    name: str
    type: VarType = VarType.STRING
    required: bool = True
    default: str | None = None
    pattern: str | None = None
    description: str | None = None
    choices: list[str] = field(default_factory=list)
    min_value: float | None = None
    max_value: float | None = None

    def __post_init__(self):
        if self.pattern:
            try:
                re.compile(self.pattern)
            except re.error as e:
                raise ValueError(f"Invalid regex pattern for {self.name}: {e}")


@dataclass
class Schema:
    """Complete schema for environment validation."""

    variables: dict[str, VarSchema] = field(default_factory=dict)
    strict: bool = False  # If True, fail on undefined variables

    def get_required_vars(self) -> list[str]:
        """Return list of required variable names."""
        return [name for name, var in self.variables.items() if var.required]

    def get_optional_vars(self) -> list[str]:
        """Return list of optional variable names."""
        return [name for name, var in self.variables.items() if not var.required]


class SchemaParseError(Exception):
    """Raised when schema parsing fails."""

    pass


def parse_schema(content: str) -> Schema:
    """Parse YAML schema content into a Schema object."""
    try:
        data = yaml.safe_load(content)
    except yaml.YAMLError as e:
        raise SchemaParseError(f"Invalid YAML: {e}")

    if not data:
        raise SchemaParseError("Schema file is empty")

    if not isinstance(data, dict):
        raise SchemaParseError("Schema must be a YAML mapping")

    variables: dict[str, VarSchema] = {}
    strict = data.get("strict", False)

    vars_data = data.get("variables", data.get("vars", data))

    # If top-level has 'strict' key, remove it before processing vars
    if "strict" in vars_data:
        vars_data = {k: v for k, v in vars_data.items() if k != "strict"}
    if "variables" in vars_data or "vars" in vars_data:
        vars_data = vars_data.get("variables", vars_data.get("vars", {}))

    for name, var_def in vars_data.items():
        if name in ("strict", "variables", "vars"):
            continue

        if var_def is None:
            # Shorthand: VAR_NAME: (just the name, defaults to required string)
            variables[name] = VarSchema(name=name)
            continue

        if isinstance(var_def, str):
            # Shorthand: VAR_NAME: string
            try:
                var_type = VarType(var_def.lower())
            except ValueError:
                raise SchemaParseError(f"Unknown type '{var_def}' for variable {name}")
            variables[name] = VarSchema(name=name, type=var_type)
            continue

        if not isinstance(var_def, dict):
            raise SchemaParseError(f"Invalid definition for variable {name}")

        # Full definition
        type_str = var_def.get("type", "string")
        try:
            var_type = VarType(type_str.lower())
        except ValueError:
            raise SchemaParseError(f"Unknown type '{type_str}' for variable {name}")

        variables[name] = VarSchema(
            name=name,
            type=var_type,
            required=var_def.get("required", True),
            default=var_def.get("default"),
            pattern=var_def.get("pattern"),
            description=var_def.get("description"),
            choices=var_def.get("choices", []),
            min_value=var_def.get("min"),
            max_value=var_def.get("max"),
        )

    return Schema(variables=variables, strict=strict)


def load_schema(path: Path) -> Schema:
    """Load and parse a schema file."""
    if not path.exists():
        raise SchemaParseError(f"Schema file not found: {path}")

    content = path.read_text(encoding="utf-8")
    return parse_schema(content)


def find_schema_file(start_dir: Path | None = None) -> Path | None:
    """Find schema file in current or parent directories.

    Looks for: .env.schema, .env.schema.yml, .env.schema.yaml, env.schema.yml
    """
    if start_dir is None:
        start_dir = Path.cwd()

    schema_names = [
        ".env.schema",
        ".env.schema.yml",
        ".env.schema.yaml",
        "env.schema.yml",
        "env.schema.yaml",
    ]

    current = start_dir.resolve()

    while current != current.parent:
        for name in schema_names:
            schema_path = current / name
            if schema_path.exists():
                return schema_path
        current = current.parent

    return None
