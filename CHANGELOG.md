# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Fixed
- Normalized German CLI/help strings and offline test fixtures to use real umlauts instead of ASCII transliterations.
- Fixed regex-based fallback form parsing in `_parse_forms` to correctly look for the `action` and `method` attributes inside the `<form>` opening tag rather than the inner form HTML.
- Added extraction support for `<textarea>` and `<select>` fields in the regex-based fallback form parser.

### Added
- Added `llms.txt` file for LLM integration and discovery.
- Added local test instructions to `README.md` and `README_de.md`.

## [0.1.0] - 2026-07-05

### Added
- Initial release of the standalone `web-scraper` module, extracted from BACH system `web_scrape.py`.
- Support for `get`, `links`, `forms`, `headers`, `extract` (Markdown), and `screenshot` (Selenium/Chrome) operations.
- Per-hop Server-Side Request Forgery (SSRF) guard blocking private/loopback/link-local/multicast IP subnets by default.
- Zero-dependency core utilizing standard library `urllib` and `html.parser`, with optional upgrades to `requests`, `beautifulsoup4`, `trafilatura`, and `selenium`.
- 14 offline-only unit tests.
