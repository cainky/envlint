"""Validation engine for envlint."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from urllib.parse import urlparse

from envlint.schema import Schema, VarSchema, VarType


class ErrorLevel(Enum):
    """Severity level for validation errors."""

    ERROR = "error"
    WARNING = "warning"


@dataclass
class ValidationError:
    """A single validation error."""

    variable: str
    message: str
    level: ErrorLevel = ErrorLevel.ERROR
    expected: str | None = None
    actual: str | None = None

    def __str__(self) -> str:
        base = f"{self.variable}: {self.message}"
        if self.expected and self.actual:
            base += f" (expected: {self.expected}, got: {self.actual})"
        elif self.actual:
            base += f" (got: {self.actual})"
        return base


@dataclass
class ValidationResult:
    """Result of validation."""

    errors: list[ValidationError] = field(default_factory=list)
    warnings: list[ValidationError] = field(default_factory=list)
    validated_count: int = 0
    missing_count: int = 0
    extra_count: int = 0

    @property
    def is_valid(self) -> bool:
        """Return True if no errors (warnings are OK)."""
        return len(self.errors) == 0

    def add_error(self, variable: str, message: str, **kwargs):
        """Add an error."""
        self.errors.append(
            ValidationError(variable=variable, message=message, level=ErrorLevel.ERROR, **kwargs)
        )

    def add_warning(self, variable: str, message: str, **kwargs):
        """Add a warning."""
        self.warnings.append(
            ValidationError(variable=variable, message=message, level=ErrorLevel.WARNING, **kwargs)
        )


def validate_type(value: str, var_type: VarType, var_name: str) -> str | None:
    """Validate value matches expected type. Returns error message or None."""
    if var_type == VarType.STRING:
        return None  # Any string is valid

    elif var_type == VarType.INT:
        try:
            int(value)
            return None
        except ValueError:
            return "must be an integer"

    elif var_type == VarType.FLOAT:
        try:
            float(value)
            return None
        except ValueError:
            return "must be a number"

    elif var_type == VarType.BOOL:
        valid_bools = {"true", "false", "1", "0", "yes", "no", "on", "off"}
        if value.lower() not in valid_bools:
            return "must be a boolean (true/false, 1/0, yes/no, on/off)"
        return None

    elif var_type == VarType.URL:
        try:
            result = urlparse(value)
            if not all([result.scheme, result.netloc]):
                return "must be a valid URL with scheme and host"
            if result.scheme not in ("http", "https", "ftp", "ftps"):
                return "must use http/https/ftp scheme"
            return None
        except Exception:
            return "must be a valid URL"

    elif var_type == VarType.EMAIL:
        # Simple email validation
        email_pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        if not re.match(email_pattern, value):
            return "must be a valid email address"
        return None

    elif var_type == VarType.PORT:
        try:
            port = int(value)
            if not (0 <= port <= 65535):
                return "must be a port number (0-65535)"
            return None
        except ValueError:
            return "must be a port number (0-65535)"

    elif var_type == VarType.PATH:
        # Just check it's not empty for now
        if not value:
            return "must be a file path"
        return None

    return None


def validate_var(value: str, var_schema: VarSchema) -> list[str]:
    """Validate a single variable value against its schema. Returns list of errors."""
    errors = []

    # Type validation
    type_error = validate_type(value, var_schema.type, var_schema.name)
    if type_error:
        errors.append(type_error)
        return errors  # Don't continue if type is wrong

    # Pattern validation
    if var_schema.pattern:
        if not re.match(var_schema.pattern, value):
            errors.append(f"must match pattern: {var_schema.pattern}")

    # Choices validation
    if var_schema.choices:
        if value not in var_schema.choices:
            choices_str = ", ".join(var_schema.choices)
            errors.append(f"must be one of: {choices_str}")

    # Range validation (for numeric types)
    if var_schema.type in (VarType.INT, VarType.FLOAT, VarType.PORT):
        try:
            num_value = float(value)
            if var_schema.min_value is not None and num_value < var_schema.min_value:
                errors.append(f"must be >= {var_schema.min_value}")
            if var_schema.max_value is not None and num_value > var_schema.max_value:
                errors.append(f"must be <= {var_schema.max_value}")
        except ValueError:
            pass  # Already caught by type validation

    return errors


def validate(env_vars: dict[str, str], schema: Schema) -> ValidationResult:
    """Validate environment variables against a schema.

    Args:
        env_vars: Dictionary of environment variable names to values
        schema: Schema to validate against

    Returns:
        ValidationResult with any errors/warnings
    """
    result = ValidationResult()

    # Check for missing required variables
    for var_name, var_schema in schema.variables.items():
        if var_name not in env_vars:
            if var_schema.required:
                if var_schema.default is not None:
                    # Has default, so it's OK
                    result.add_warning(
                        var_name,
                        "missing but has default value",
                        expected="value",
                        actual="<default>",
                    )
                else:
                    result.add_error(
                        var_name,
                        "required variable is missing",
                    )
                    result.missing_count += 1
        else:
            # Variable exists, validate it
            value = env_vars[var_name]
            errors = validate_var(value, var_schema)
            for error_msg in errors:
                result.add_error(var_name, error_msg, actual=value)
            if not errors:
                result.validated_count += 1

    # Check for extra variables (if strict mode)
    if schema.strict:
        for var_name in env_vars:
            if var_name not in schema.variables:
                result.add_warning(
                    var_name,
                    "variable not defined in schema (strict mode)",
                )
                result.extra_count += 1

    return result
