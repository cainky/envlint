# envlint

**Language-agnostic .env validation. One schema, any stack.**

[![PyPI version](https://badge.fury.io/py/envlint.svg)](https://badge.fury.io/py/envlint)
[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)

Validate your `.env` files in CI before your app even starts. Works with any language.

## Why envlint?

Existing solutions like `pydantic-settings` (Python) or `envalid` (JavaScript) only work within their own language. You need to run your app to validate your config.

**envlint is different:**
- **Language-agnostic**: Define your schema once, validate from any CI pipeline
- **Catches issues at build time**: Before your app crashes in production
- **No code changes**: Just a YAML schema and a CLI command
- **No SDK or runtime dependency**: Your app doesn't need to know envlint exists

```bash
# Your app crashes in production because...
KeyError: 'DATABASE_URL'

# Or silently uses wrong values...
API_URL=htpp://api.example.com  # typo in scheme
PORT=not_a_number               # string where int expected
```

**envlint** catches these in CI, not production.

## Installation

```bash
pip install envlint
```

## Quick Start

**1. Create a schema file** (`.env.schema`):

```yaml
DATABASE_URL:
  type: url
  required: true

API_KEY:
  type: string
  required: true
  pattern: "^sk_[a-zA-Z0-9]{32}$"

PORT:
  type: port
  required: false
  default: "3000"

DEBUG:
  type: bool
  required: false
```

**2. Run envlint:**

```bash
envlint check
```

**3. See results:**

```
┌─────────────────────────────────────────────────┐
│ envlint                                        │
├─────────────────────────────────────────────────┤
│ ✓ All 4 variables validated successfully       │
└─────────────────────────────────────────────────┘
```

Or if there are errors:

```
┌─────────────────────────────────────────────────┐
│ Errors                                          │
├──────────────┬────────────────────┬─────────────┤
│ Variable     │ Error              │ Value       │
├──────────────┼────────────────────┼─────────────┤
│ DATABASE_URL │ required variable  │ -           │
│              │ is missing         │             │
│ API_KEY      │ must match pattern │ invalid_key │
│ PORT         │ must be a port     │ abc         │
│              │ number (0-65535)   │             │
└──────────────┴────────────────────┴─────────────┘
```

Exit code is `1` on errors, `0` on success. Perfect for CI/CD.

## Schema Format

### Supported Types

| Type | Description | Example |
|------|-------------|---------|
| `string` | Any string (default) | `my-value` |
| `int` | Integer | `42` |
| `float` | Decimal number | `3.14` |
| `bool` | Boolean (`true`/`false`, `1`/`0`, `yes`/`no`) | `true` |
| `url` | Valid URL with scheme | `https://api.example.com` |
| `email` | Email address | `user@example.com` |
| `port` | Port number (0-65535) | `8080` |
| `path` | File path | `/var/log/app.log` |
| `jwt` | JWT token (header.payload.signature) | `eyJhbGciOiJIUzI1NiIs...` |
| `secret` | Sensitive value (masked in output) | `sk_live_abc123` |

### Full Schema Options

```yaml
MY_VARIABLE:
  type: string          # Type (see above)
  required: true        # Is this variable required?
  default: "value"      # Default value if missing
  pattern: "^[A-Z]+$"   # Regex pattern to match
  description: "..."    # Documentation
  choices:              # Allowed values
    - option1
    - option2
  min: 0                # Minimum (for numeric types)
  max: 100              # Maximum (for numeric types)
```

### Sensitive Value Masking

Values are automatically masked in error output for:
- Variables with `type: secret` or `type: jwt`
- Variables with sensitive keywords in name (KEY, SECRET, TOKEN, PASSWORD, CREDENTIAL)

```
┌────────────────────┬────────────────────┬──────────────┐
│ Variable           │ Error              │ Value        │
├────────────────────┼────────────────────┼──────────────┤
│ STRIPE_SECRET_KEY  │ must match pattern │ sk_t******..│
└────────────────────┴────────────────────┴──────────────┘
```

This prevents accidental exposure of secrets in CI logs.

### Shorthand Syntax

For simple variables, use shorthand:

```yaml
# These are equivalent:
API_KEY: string
API_KEY:
  type: string
  required: true

# Just the name = required string
SECRET:
```

## CLI Usage

```bash
# Basic validation
envlint check

# Specify files
envlint check --env .env.production --schema env.schema.yml

# Include system environment variables
envlint check --system

# Strict mode (fail on undefined variables)
envlint check --strict

# Verbose output (show warnings)
envlint check --verbose

# Quiet mode (only output on error)
envlint check --quiet

# Generate schema from existing .env
envlint init --from-env .env

# Create template schema
envlint init
```

## CI/CD Integration

### GitHub Actions

```yaml
- name: Validate environment
  run: |
    pip install envlint
    envlint check --env .env.example --schema .env.schema
```

### Pre-commit Hook

```yaml
# .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: envlint
        name: envlint
        entry: envlint check
        language: system
        pass_filenames: false
```

### Docker Build

```dockerfile
FROM python:3.11
RUN pip install envlint
COPY .env.schema .
COPY .env .
RUN envlint check
# ... rest of build
```

## License

GPL v3

## Contributing

Contributions welcome! Please read [CONTRIBUTING.md](CONTRIBUTING.md) first.
