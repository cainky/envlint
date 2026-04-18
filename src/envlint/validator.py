"""Validation engine for envlint."""

from __future__ import annotations

import base64
import json
import re
from dataclasses import dataclass, field
from enum import Enum
from urllib.parse import urlparse

from envlint.schema import Schema, VarSchema, VarType


def _mask_value(value: str, visible_chars: int = 4) -> str:
    """Mask a sensitive value, showing only first few characters."""
    if len(value) <= visible_chars:
        return "*" * len(value)
    return value[:visible_chars] + "*" * min(8, len(value) - visible_chars) + "..."


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
        return None

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

            if not result.scheme:
                return "must have a scheme (http:// or https://)"

            if result.scheme not in ("http", "https"):
                return "must use http:// or https:// scheme"

            if not result.netloc:
                return "must have a hostname"

            hostname = result.netloc.split(":")[0]

            if hostname.startswith("["):
                if result.netloc.endswith("]"):
                    pass
                else:
                    return "invalid IPv6 address format"
            elif hostname.replace(".", "").replace(":", "").isdigit():
                pass
            else:
                hostname_pattern = (
                    r"^[a-zA-Z0-9]([a-zA-Z0-9\-]*[a-zA-Z0-9])?"
                    r"(\.[a-zA-Z0-9]([a-zA-Z0-9\-]*[a-zA-Z0-9])?)*$"
                )
                if not re.match(hostname_pattern, hostname):
                    return "invalid hostname format"

            return None
        except Exception:
            return "must be a valid URL"

    elif var_type == VarType.EMAIL:
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
        if not value:
            return "must be a file path"
        return None

    elif var_type == VarType.JWT:
        parts = value.split(".")
        if len(parts) != 3:
            return "must be a valid JWT token (header.payload.signature)"

        try:
            header_part = parts[0] + "=" * (4 - len(parts[0]) % 4)
            header_decoded = base64.urlsafe_b64decode(header_part)
            header = json.loads(header_decoded)

            if not isinstance(header, dict):
                return "JWT header must be a JSON object"

            if "alg" not in header:
                return "JWT header must contain 'alg' field"

            return None
        except json.JSONDecodeError:
            return "JWT header must be valid JSON"
        except Exception:
            return "must be a valid JWT token (invalid base64 encoding)"

    elif var_type == VarType.SECRET:
        if not value:
            return "must not be empty"
        return None

    return None


def validate_var(value: str, var_schema: VarSchema) -> list[str]:
    """Validate a single variable value against its schema. Returns list of errors."""
    errors = []

    type_error = validate_type(value, var_schema.type, var_schema.name)
    if type_error:
        errors.append(type_error)
        return errors

    if var_schema.pattern:
        if not re.match(var_schema.pattern, value):
            errors.append(f"must match pattern: {var_schema.pattern}")

    if var_schema.choices:
        if value not in var_schema.choices:
            choices_str = ", ".join(var_schema.choices)
            errors.append(f"must be one of: {choices_str}")

    if var_schema.type in (VarType.INT, VarType.FLOAT, VarType.PORT):
        try:
            num_value = float(value)
            if var_schema.min_value is not None and num_value < var_schema.min_value:
                errors.append(f"must be >= {var_schema.min_value}")
            if var_schema.max_value is not None and num_value > var_schema.max_value:
                errors.append(f"must be <= {var_schema.max_value}")
        except ValueError:
            pass

    return errors


def validate(env_vars: dict[str, str], schema: Schema) -> ValidationResult:
    """Validate environment variables against a schema."""

    result = ValidationResult()

    for var_name, var_schema in schema.variables.items():
        if var_name not in env_vars:
            if var_schema.required:
                if var_schema.default is not None:
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
            value = env_vars[var_name]
            errors = validate_var(value, var_schema)
            for error_msg in errors:
                display_value = value
                if var_schema.type in (VarType.SECRET, VarType.JWT):
                    display_value = _mask_value(value)
                elif any(
                    kw in var_name.upper()
                    for kw in ("KEY", "SECRET", "TOKEN", "PASSWORD", "CREDENTIAL")
                ):
                    display_value = _mask_value(value)
                result.add_error(var_name, error_msg, actual=display_value)
            if not errors:
                result.validated_count += 1

    if schema.strict:
        for var_name in env_vars:
            if var_name not in schema.variables:
                result.add_warning(
                    var_name,
                    "variable not defined in schema (strict mode)",
                )
                result.extra_count += 1

    return result
