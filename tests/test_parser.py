"""Tests for .env file parsing."""

import pytest

from envlint.parser import EnvParseError, parse_env, parse_env_line


class TestParseEnvLine:
    """Tests for parsing individual lines."""

    def test_simple_assignment(self):
        assert parse_env_line("KEY=value", 1) == ("KEY", "value")

    def test_with_spaces(self):
        assert parse_env_line("  KEY = value  ", 1) == ("KEY", "value")

    def test_empty_value(self):
        assert parse_env_line("KEY=", 1) == ("KEY", "")

    def test_quoted_value_double(self):
        assert parse_env_line('KEY="quoted value"', 1) == ("KEY", "quoted value")

    def test_quoted_value_single(self):
        assert parse_env_line("KEY='quoted value'", 1) == ("KEY", "quoted value")

    def test_export_prefix(self):
        assert parse_env_line("export KEY=value", 1) == ("KEY", "value")

    def test_comment_line(self):
        assert parse_env_line("# this is a comment", 1) is None

    def test_empty_line(self):
        assert parse_env_line("", 1) is None
        assert parse_env_line("   ", 1) is None

    def test_value_with_equals(self):
        assert parse_env_line("KEY=value=with=equals", 1) == ("KEY", "value=with=equals")

    def test_value_with_hash(self):
        assert parse_env_line("KEY=value#notcomment", 1) == ("KEY", "value#notcomment")

    def test_missing_equals(self):
        with pytest.raises(EnvParseError):
            parse_env_line("NOEQUALS", 1)

    def test_invalid_key_starts_with_number(self):
        with pytest.raises(EnvParseError):
            parse_env_line("123KEY=value", 1)

    def test_invalid_key_special_chars(self):
        with pytest.raises(EnvParseError):
            parse_env_line("KEY-NAME=value", 1)

    def test_underscore_in_key(self):
        assert parse_env_line("MY_KEY_NAME=value", 1) == ("MY_KEY_NAME", "value")

    def test_key_starts_with_underscore(self):
        assert parse_env_line("_PRIVATE=value", 1) == ("_PRIVATE", "value")


class TestParseEnv:
    """Tests for parsing full .env content."""

    def test_multiple_lines(self):
        content = """
KEY1=value1
KEY2=value2
KEY3=value3
"""
        result = parse_env(content)
        assert result == {"KEY1": "value1", "KEY2": "value2", "KEY3": "value3"}

    def test_with_comments(self):
        content = """
# Database config
DB_HOST=localhost
DB_PORT=5432

# API config
API_KEY=secret
"""
        result = parse_env(content)
        assert result == {"DB_HOST": "localhost", "DB_PORT": "5432", "API_KEY": "secret"}

    def test_mixed_quotes(self):
        content = """
SINGLE='single quoted'
DOUBLE="double quoted"
NONE=no quotes
"""
        result = parse_env(content)
        assert result == {
            "SINGLE": "single quoted",
            "DOUBLE": "double quoted",
            "NONE": "no quotes",
        }

    def test_overwrite_duplicate(self):
        content = """
KEY=first
KEY=second
"""
        result = parse_env(content)
        assert result == {"KEY": "second"}

    def test_empty_content(self):
        result = parse_env("")
        assert result == {}

    def test_only_comments(self):
        content = """
# comment 1
# comment 2
"""
        result = parse_env(content)
        assert result == {}


class TestExpandVars:
    """Tests for variable expansion."""

    def test_brace_syntax(self):
        from envlint.parser import expand_vars

        result = expand_vars("${FOO}", {"FOO": "bar"})
        assert result == "bar"

    def test_simple_syntax(self):
        from envlint.parser import expand_vars

        result = expand_vars("$FOO", {"FOO": "bar"})
        assert result == "bar"

    def test_multiple_vars(self):
        from envlint.parser import expand_vars

        result = expand_vars("${BASE}/api", {"BASE": "http://localhost:8080"})
        assert result == "http://localhost:8080/api"

    def test_mixed_syntax(self):
        from envlint.parser import expand_vars

        result = expand_vars("$BASE_URL/api", {"BASE_URL": "http://localhost"})
        assert result == "http://localhost/api"

    def test_unknown_var_unchanged(self):
        from envlint.parser import expand_vars

        result = expand_vars("$UNKNOWN", {"FOO": "bar"})
        assert result == "$UNKNOWN"

    def test_no_expand_in_content(self):
        result = parse_env("FOO=bar\nBAR=$FOO", expand=False)
        assert result == {"FOO": "bar", "BAR": "$FOO"}

    def test_expand_in_content(self):
        result = parse_env("FOO=true\nBAR=$FOO", expand=True)
        assert result == {"FOO": "true", "BAR": "true"}
