# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Pfad B Discoverability & Architecture: Implemented 18-point bilingual quick navigation architecture (`<a id="sec-01"></a>` through `<a id="sec-18"></a>`) with reciprocal section parity across `README.md` and `README_de.md`.
- Dual Mermaid diagram specifications: Added End-to-End Request & Content Lifecycle sequence diagram (`sequenceDiagram` with `autonumber` and zero unquoted statement terminators) alongside the Architecture & Security Gate Topology flowchart (`flowchart TD`).
- Canonical root `NOTICE` attribution file establishing lineage to Lukas Geiger, ellmos-ai, and open-bricks umbrella ecosystem.
- Level 1 Software Bill of Materials (SBOM) in `THIRD_PARTY_LICENSES.md` certifying zero required external dependencies for core runtime, permissive licensing (MIT / Apache-2.0 / PSF-2.0), unprivileged `RunAsInvoker` non-elevation, and Zero-Copyleft isolation.
- Structured Discoverability & Persona mapping in `MARKETING-LOG.txt` detailing Target Personas `[PERSONA-01]` through `[PERSONA-04]` and a 10-dimension 5-way comparative matrix vs. raw HTTP clients, Scrapy, Playwright, and Cloud Scraping SaaS.
- Saturated GitHub repository topics to 20/20 and harmonized PEP 621 keywords and repository URLs in `pyproject.toml` (license-files, Notice, Third-Party Licenses, Marketing Log, LLM Ready).
- Explicit German statutory notice (§ 521 BGB Gefälligkeitsrecht) and binding 48-hour Security Response SLA harmonized across `README.md`, `README_de.md`, and `SECURITY.md`.
- Expanded contract test suite in `tests/test_metadata.py` locking in NOTICE attribution, Level 1 SBOM, 18-point navigation parity, Mermaid syntax hygiene, and § 521 BGB compliance.
- `WebScraper(max_redirects=...)` makes the redirect limit configurable. The default stays 10, so no existing caller changes behaviour. Negative values are rejected.

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
