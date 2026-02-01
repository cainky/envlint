"""envlint - Validate .env files against a schema."""

__version__ = "0.3.0"

from envlint.validator import ValidationError, ValidationResult, validate

__all__ = ["validate", "ValidationError", "ValidationResult", "__version__"]
