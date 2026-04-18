# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.4.0] - 2026-04-18

### Fixed

- JWT validation now properly decodes base64 and verifies JSON structure
- URL validation now enforces https-only and validates hostname format

### Added

- Variable expansion for ${VAR} and $VAR references (--expand flag)
- Python API documentation

## [0.3.0] - 2026-02-08

### Added

- Example schema file (.env.schema.example)
- CHANGELOG.md
- CODE_OF_CONDUCT.md

## [0.1.0] - 2026-01-08

### Added

- Initial release
- Type validation: string, int, float, bool, url, email, port, path
- Pattern matching with regex
- Required/optional fields with default values
- Choices validation
- Min/max constraints for numeric types
- Strict mode for undefined variables
- Schema generation from existing .env files
- CI/CD friendly exit codes
