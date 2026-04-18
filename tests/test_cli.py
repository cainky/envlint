"""Tests for CLI interface."""

from typer.testing import CliRunner

from envlint.cli import app


class TestCLICheck:
    """Tests for envlint check command."""

    def test_check_valid_env(self, tmp_path, monkeypatch):
        schema_file = tmp_path / ".env.schema"
        schema_file.write_text("KEY:\n  type: string\n")

        env_file = tmp_path / ".env"
        env_file.write_text("KEY=value\n")

        monkeypatch.chdir(tmp_path)
        runner = CliRunner()
        result = runner.invoke(app, ["check", "-e", str(env_file), "-s", str(schema_file)])
        assert result.exit_code == 0
        assert "validated successfully" in result.output

    def test_check_missing_required(self, tmp_path, monkeypatch):
        schema_file = tmp_path / ".env.schema"
        schema_file.write_text("REQUIRED_KEY:\n  type: string\n  required: true\n")

        env_file = tmp_path / ".env"
        env_file.write_text("OTHER=value\n")

        monkeypatch.chdir(tmp_path)
        runner = CliRunner()
        result = runner.invoke(app, ["check", "-e", str(env_file), "-s", str(schema_file)])
        assert result.exit_code == 1
        assert "REQUIRED_KEY" in result.output

    def test_check_invalid_type(self, tmp_path, monkeypatch):
        schema_file = tmp_path / ".env.schema"
        schema_file.write_text("PORT:\n  type: port\n")

        env_file = tmp_path / ".env"
        env_file.write_text("PORT=not_a_port\n")

        monkeypatch.chdir(tmp_path)
        runner = CliRunner()
        result = runner.invoke(app, ["check", "-e", str(env_file), "-s", str(schema_file)])
        assert result.exit_code == 1
        assert "PORT" in result.output

    def test_check_quiet_mode(self, tmp_path, monkeypatch):
        schema_file = tmp_path / ".env.schema"
        schema_file.write_text("KEY:\n  type: string\n")

        env_file = tmp_path / ".env"
        env_file.write_text("KEY=value\n")

        monkeypatch.chdir(tmp_path)
        runner = CliRunner()
        result = runner.invoke(app, ["check", "-e", str(env_file), "-s", str(schema_file), "-q"])
        assert result.exit_code == 0
        assert result.output == ""

    def test_check_verbose_mode(self, tmp_path, monkeypatch):
        schema_file = tmp_path / ".env.schema"
        schema_file.write_text("KEY:\n  type: string\n")

        env_file = tmp_path / ".env"
        env_file.write_text("KEY=value\n")

        monkeypatch.chdir(tmp_path)
        runner = CliRunner()
        result = runner.invoke(app, ["check", "-e", str(env_file), "-s", str(schema_file), "-v"])
        assert "validated successfully" in result.output

    def test_check_expand_vars(self, tmp_path, monkeypatch):
        schema_file = tmp_path / ".env.schema"
        schema_file.write_text("BASE:\n  type: url\nAPI:\n  type: url\n")

        env_file = tmp_path / ".env"
        env_file.write_text("BASE=http://localhost:8080\nAPI=${BASE}/api\n")

        monkeypatch.chdir(tmp_path)
        runner = CliRunner()
        result = runner.invoke(app, ["check", "-e", str(env_file), "-s", str(schema_file), "-x"])
        assert result.exit_code == 0

    def test_check_no_schema(self, tmp_path, monkeypatch):
        env_file = tmp_path / ".env"
        env_file.write_text("KEY=value\n")

        monkeypatch.chdir(tmp_path)
        runner = CliRunner()
        result = runner.invoke(app, ["check", "-e", str(env_file)])
        assert result.exit_code == 1

    def test_check_no_env(self, tmp_path, monkeypatch):
        schema_file = tmp_path / ".env.schema"
        schema_file.write_text("KEY:\n  type: string\n")

        monkeypatch.chdir(tmp_path)
        runner = CliRunner()
        result = runner.invoke(app, ["check", "-s", str(schema_file)])
        assert result.exit_code == 1


class TestCLIInit:
    """Tests for envlint init command."""

    def test_init_creates_file(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()
        result = runner.invoke(app, ["init", "-o", "test.schema"])
        assert result.exit_code == 0
        assert (tmp_path / "test.schema").exists()

    def test_init_from_env(self, tmp_path, monkeypatch):
        env_file = tmp_path / ".env"
        env_file.write_text("KEY=value\n")

        monkeypatch.chdir(tmp_path)
        runner = CliRunner()
        result = runner.invoke(app, ["init", "-f", str(env_file)])
        assert result.exit_code == 0


class TestCLIVersion:
    """Tests for version command."""

    def test_version(self):
        runner = CliRunner()
        result = runner.invoke(app, ["version"])
        assert result.exit_code == 0
        assert "envlint" in result.output
