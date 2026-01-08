"""Tests for the validation engine."""

from envlint.schema import Schema, VarSchema, VarType
from envlint.validator import validate, validate_type, validate_var


class TestValidateType:
    """Tests for type validation."""

    def test_string_accepts_anything(self):
        assert validate_type("hello", VarType.STRING, "VAR") is None
        assert validate_type("123", VarType.STRING, "VAR") is None
        assert validate_type("", VarType.STRING, "VAR") is None

    def test_int_valid(self):
        assert validate_type("123", VarType.INT, "VAR") is None
        assert validate_type("-456", VarType.INT, "VAR") is None
        assert validate_type("0", VarType.INT, "VAR") is None

    def test_int_invalid(self):
        assert validate_type("12.5", VarType.INT, "VAR") is not None
        assert validate_type("abc", VarType.INT, "VAR") is not None
        assert validate_type("", VarType.INT, "VAR") is not None

    def test_float_valid(self):
        assert validate_type("3.14", VarType.FLOAT, "VAR") is None
        assert validate_type("-2.5", VarType.FLOAT, "VAR") is None
        assert validate_type("42", VarType.FLOAT, "VAR") is None

    def test_float_invalid(self):
        assert validate_type("abc", VarType.FLOAT, "VAR") is not None

    def test_bool_valid(self):
        for val in ["true", "false", "True", "FALSE", "1", "0", "yes", "no", "on", "off"]:
            assert validate_type(val, VarType.BOOL, "VAR") is None

    def test_bool_invalid(self):
        assert validate_type("maybe", VarType.BOOL, "VAR") is not None
        assert validate_type("2", VarType.BOOL, "VAR") is not None

    def test_url_valid(self):
        assert validate_type("https://example.com", VarType.URL, "VAR") is None
        assert validate_type("http://localhost:8080/path", VarType.URL, "VAR") is None
        assert validate_type("https://api.example.com/v1", VarType.URL, "VAR") is None

    def test_url_invalid(self):
        assert validate_type("not-a-url", VarType.URL, "VAR") is not None
        assert validate_type("ftp://files.example.com", VarType.URL, "VAR") is None  # ftp is valid
        assert validate_type("://missing-scheme.com", VarType.URL, "VAR") is not None

    def test_email_valid(self):
        assert validate_type("user@example.com", VarType.EMAIL, "VAR") is None
        assert validate_type("test.user+tag@sub.domain.org", VarType.EMAIL, "VAR") is None

    def test_email_invalid(self):
        assert validate_type("not-an-email", VarType.EMAIL, "VAR") is not None
        assert validate_type("@example.com", VarType.EMAIL, "VAR") is not None
        assert validate_type("user@", VarType.EMAIL, "VAR") is not None

    def test_port_valid(self):
        assert validate_type("80", VarType.PORT, "VAR") is None
        assert validate_type("443", VarType.PORT, "VAR") is None
        assert validate_type("8080", VarType.PORT, "VAR") is None
        assert validate_type("0", VarType.PORT, "VAR") is None
        assert validate_type("65535", VarType.PORT, "VAR") is None

    def test_port_invalid(self):
        assert validate_type("-1", VarType.PORT, "VAR") is not None
        assert validate_type("65536", VarType.PORT, "VAR") is not None
        assert validate_type("abc", VarType.PORT, "VAR") is not None


class TestValidateVar:
    """Tests for full variable validation."""

    def test_pattern_matching(self):
        schema = VarSchema(name="API_KEY", pattern=r"^sk_[a-z0-9]{8}$")
        assert validate_var("sk_abc12345", schema) == []
        assert len(validate_var("invalid_key", schema)) > 0

    def test_choices(self):
        schema = VarSchema(name="ENV", choices=["dev", "staging", "prod"])
        assert validate_var("dev", schema) == []
        assert validate_var("staging", schema) == []
        assert len(validate_var("invalid", schema)) > 0

    def test_min_max(self):
        schema = VarSchema(name="COUNT", type=VarType.INT, min_value=1, max_value=100)
        assert validate_var("50", schema) == []
        assert validate_var("1", schema) == []
        assert validate_var("100", schema) == []
        assert len(validate_var("0", schema)) > 0
        assert len(validate_var("101", schema)) > 0


class TestValidate:
    """Tests for the main validate function."""

    def test_all_valid(self):
        schema = Schema(
            variables={
                "DB_HOST": VarSchema(name="DB_HOST"),
                "DB_PORT": VarSchema(name="DB_PORT", type=VarType.PORT),
            }
        )
        env = {"DB_HOST": "localhost", "DB_PORT": "5432"}
        result = validate(env, schema)
        assert result.is_valid
        assert len(result.errors) == 0

    def test_missing_required(self):
        schema = Schema(
            variables={
                "REQUIRED_VAR": VarSchema(name="REQUIRED_VAR", required=True),
            }
        )
        env = {}
        result = validate(env, schema)
        assert not result.is_valid
        assert len(result.errors) == 1
        assert result.errors[0].variable == "REQUIRED_VAR"

    def test_missing_optional(self):
        schema = Schema(
            variables={
                "OPTIONAL_VAR": VarSchema(name="OPTIONAL_VAR", required=False),
            }
        )
        env = {}
        result = validate(env, schema)
        assert result.is_valid

    def test_missing_with_default(self):
        schema = Schema(
            variables={
                "VAR_WITH_DEFAULT": VarSchema(
                    name="VAR_WITH_DEFAULT", required=True, default="fallback"
                ),
            }
        )
        env = {}
        result = validate(env, schema)
        assert result.is_valid  # Has default, so not an error
        assert len(result.warnings) == 1

    def test_type_error(self):
        schema = Schema(
            variables={
                "PORT": VarSchema(name="PORT", type=VarType.INT),
            }
        )
        env = {"PORT": "not_a_number"}
        result = validate(env, schema)
        assert not result.is_valid
        assert len(result.errors) == 1

    def test_strict_mode_extra_vars(self):
        schema = Schema(
            variables={
                "DEFINED_VAR": VarSchema(name="DEFINED_VAR"),
            },
            strict=True,
        )
        env = {"DEFINED_VAR": "value", "EXTRA_VAR": "extra"}
        result = validate(env, schema)
        assert result.is_valid  # Extra vars are warnings, not errors
        assert len(result.warnings) == 1

    def test_multiple_errors(self):
        schema = Schema(
            variables={
                "REQUIRED1": VarSchema(name="REQUIRED1", required=True),
                "REQUIRED2": VarSchema(name="REQUIRED2", required=True),
                "PORT": VarSchema(name="PORT", type=VarType.INT),
            }
        )
        env = {"PORT": "invalid"}
        result = validate(env, schema)
        assert not result.is_valid
        assert len(result.errors) == 3  # 2 missing + 1 invalid type
