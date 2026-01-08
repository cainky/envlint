"""Tests for schema parsing."""

import pytest

from envlint.schema import Schema, SchemaParseError, VarSchema, VarType, parse_schema


class TestParseSchema:
    """Tests for schema parsing."""

    def test_basic_schema(self):
        content = """
DATABASE_URL:
  type: url
  required: true
"""
        schema = parse_schema(content)
        assert "DATABASE_URL" in schema.variables
        assert schema.variables["DATABASE_URL"].type == VarType.URL
        assert schema.variables["DATABASE_URL"].required is True

    def test_shorthand_type(self):
        content = """
API_KEY: string
PORT: int
DEBUG: bool
"""
        schema = parse_schema(content)
        assert schema.variables["API_KEY"].type == VarType.STRING
        assert schema.variables["PORT"].type == VarType.INT
        assert schema.variables["DEBUG"].type == VarType.BOOL

    def test_shorthand_name_only(self):
        content = """
SECRET_KEY:
"""
        schema = parse_schema(content)
        assert "SECRET_KEY" in schema.variables
        assert schema.variables["SECRET_KEY"].type == VarType.STRING
        assert schema.variables["SECRET_KEY"].required is True

    def test_all_types(self):
        content = """
VAR_STRING: string
VAR_INT: int
VAR_FLOAT: float
VAR_BOOL: bool
VAR_URL: url
VAR_EMAIL: email
VAR_PORT: port
VAR_PATH: path
"""
        schema = parse_schema(content)
        assert schema.variables["VAR_STRING"].type == VarType.STRING
        assert schema.variables["VAR_INT"].type == VarType.INT
        assert schema.variables["VAR_FLOAT"].type == VarType.FLOAT
        assert schema.variables["VAR_BOOL"].type == VarType.BOOL
        assert schema.variables["VAR_URL"].type == VarType.URL
        assert schema.variables["VAR_EMAIL"].type == VarType.EMAIL
        assert schema.variables["VAR_PORT"].type == VarType.PORT
        assert schema.variables["VAR_PATH"].type == VarType.PATH

    def test_full_definition(self):
        content = """
COMPLEX_VAR:
  type: string
  required: false
  default: "default_value"
  pattern: "^[a-z]+$"
  description: "A complex variable"
  choices:
    - option1
    - option2
"""
        schema = parse_schema(content)
        var = schema.variables["COMPLEX_VAR"]
        assert var.type == VarType.STRING
        assert var.required is False
        assert var.default == "default_value"
        assert var.pattern == "^[a-z]+$"
        assert var.description == "A complex variable"
        assert var.choices == ["option1", "option2"]

    def test_min_max(self):
        content = """
COUNT:
  type: int
  min: 1
  max: 100
"""
        schema = parse_schema(content)
        var = schema.variables["COUNT"]
        assert var.min_value == 1
        assert var.max_value == 100

    def test_strict_mode(self):
        content = """
strict: true

DATABASE_URL:
  type: url
"""
        schema = parse_schema(content)
        assert schema.strict is True

    def test_variables_key(self):
        content = """
variables:
  VAR1: string
  VAR2: int
"""
        schema = parse_schema(content)
        assert "VAR1" in schema.variables
        assert "VAR2" in schema.variables

    def test_invalid_yaml(self):
        content = "invalid: yaml: content:"
        with pytest.raises(SchemaParseError):
            parse_schema(content)

    def test_empty_schema(self):
        content = ""
        with pytest.raises(SchemaParseError):
            parse_schema(content)

    def test_unknown_type(self):
        content = """
VAR: unknown_type
"""
        with pytest.raises(SchemaParseError):
            parse_schema(content)

    def test_invalid_regex(self):
        content = """
VAR:
  type: string
  pattern: "[invalid(regex"
"""
        with pytest.raises(ValueError):
            parse_schema(content)


class TestSchemaHelpers:
    """Tests for schema helper methods."""

    def test_get_required_vars(self):
        schema = Schema(
            variables={
                "REQUIRED1": VarSchema(name="REQUIRED1", required=True),
                "REQUIRED2": VarSchema(name="REQUIRED2", required=True),
                "OPTIONAL1": VarSchema(name="OPTIONAL1", required=False),
            }
        )
        required = schema.get_required_vars()
        assert "REQUIRED1" in required
        assert "REQUIRED2" in required
        assert "OPTIONAL1" not in required

    def test_get_optional_vars(self):
        schema = Schema(
            variables={
                "REQUIRED1": VarSchema(name="REQUIRED1", required=True),
                "OPTIONAL1": VarSchema(name="OPTIONAL1", required=False),
                "OPTIONAL2": VarSchema(name="OPTIONAL2", required=False),
            }
        )
        optional = schema.get_optional_vars()
        assert "OPTIONAL1" in optional
        assert "OPTIONAL2" in optional
        assert "REQUIRED1" not in optional
