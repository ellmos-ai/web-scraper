# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Added Mermaid architecture & pipeline flowcharts to `README.md` and `README_de.md` detailing input client triggers, pre-flight security checks (SSRF, scheme validation), fetch engine, and extraction operations with 100% bilingual parity.
- Added GitHub Actions CI workflow status badge and Ruff code style badge to `README.md` and `README_de.md`.
- Added autonomous AI agent context extraction code examples to `README.md` and `README_de.md`.
- Enhanced automated contract test suite (`tests/test_metadata.py`) to verify CI/Ruff badges and Mermaid architecture diagrams across bilingual documentation.

## [0.1.1] - 2026-09-10

### Added
- Restored and hardened GitHub Actions CI matrix (`.github/workflows/tests.yml`) across Python 3.10, 3.11, 3.12, and 3.13 with concurrency cancellation (`cancel-in-progress: true`), `ruff check .`, `compileall -q .`, wheel build & install validation, CLI preflight, and pytest execution.
- Added GitHub Actions issue and PR lifecycle workflow (`.github/workflows/stale.yml`).
- Added executable package entry point `web_scraper/__main__.py` enabling clean `python -m web_scraper` CLI invocation without `runpy` runtime warnings.
- Comprehensive automated contract test suite (`tests/test_metadata.py`) enforcing `.gitignore` exclusions, PEP 621 metadata, version parity, CI/stale workflows, security policy SLAs, and documentation badges.
- Enhanced PEP 621 metadata in `pyproject.toml` with `classifiers`, `[project.urls]` (Homepage, Repository, Documentation, Issues, Changelog, Security, Parent Organization, Umbrella Ecosystem), `[project.optional-dependencies]` (`dev`, `test`), `[tool.pytest.ini_options]`, and `[tool.ruff]`.
- Added bilingual `SECURITY.md` (DE/EN) with supported versions table, 48-hour response SLA, 5 business days triage guarantee, and designated security contact addresses.
- Hardened `.gitignore` against multi-host sync conflicts (`*-conflict-*`, `*.sync-conflict-*`, etc.), multi-agent lock files (`LOCK`, `LOCK.*`, etc.), test caches (`.pytest_cache/`, `.ruff_cache/`, `coverage`), and temporary build artifacts.
- Added `llms.txt` file for LLM integration and discovery (updated for version `0.1.1`).
- Added Ecosystem (`ellmos-ai`) and Umbrella (`open-bricks`) Shields.io discovery badges.

### Fixed
- Skipped same-page anchor links before URL normalization so `links()` matches the documented `#` filtering behavior.
- Normalized German CLI/help strings and offline test fixtures to use real umlauts instead of ASCII transliterations.
- Fixed regex-based fallback form parsing in `_parse_forms` to correctly look for the `action` and `method` attributes inside the `<form>` opening tag rather than the inner form HTML.
- Added extraction support for `<textarea>` and `<select>` fields in the regex-based fallback form parser.
- Synchronized package version to `0.1.1` across `web_scraper/__init__.py`, `pyproject.toml`, and documentation.

## [0.1.0] - 2026-07-05

### Added
- Initial release of the standalone `web-scraper` module, extracted from BACH system `web_scrape.py`.
- Support for `get`, `links`, `forms`, `headers`, `extract` (Markdown), and `screenshot` (Selenium/Chrome) operations.
- Per-hop Server-Side Request Forgery (SSRF) guard blocking private/loopback/link-local/multicast IP subnets by default.
- Zero-dependency core utilizing standard library `urllib` and `html.parser`, with optional upgrades to `requests`, `beautifulsoup4`, `trafilatura`, and `selenium`.
- 14 offline-only unit tests.
