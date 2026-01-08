# Contributing to envlint

Thanks for your interest in contributing! This document outlines how to get started.

## Development Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/cainky/envlint.git
   cd envlint
   ```

2. **Create a virtual environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install in development mode with dev dependencies:**
   ```bash
   pip install -e ".[dev]"
   ```

## Running Tests

```bash
pytest
```

With coverage:
```bash
pytest --cov=envlint
```

## Code Style

This project uses [Ruff](https://github.com/astral-sh/ruff) for linting and formatting.

```bash
# Check for issues
ruff check .

# Auto-fix issues
ruff check --fix .

# Format code
ruff format .
```

## Submitting Changes

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/my-feature`)
3. Make your changes
4. Run tests and linting
5. Commit with a clear message
6. Push to your fork
7. Open a Pull Request

## Pull Request Guidelines

- Keep PRs focused on a single change
- Include tests for new functionality
- Update documentation if needed
- Ensure CI passes before requesting review

## Reporting Issues

Use the [issue templates](https://github.com/cainky/envlint/issues/new/choose) for bug reports and feature requests.

## License

By contributing, you agree that your contributions will be licensed under the GPL v3 license.
