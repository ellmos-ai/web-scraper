# -*- coding: utf-8 -*-
# SPDX-License-Identifier: MIT
"""Automatisierte Vertragstestsuite (Hygiene, PEP 621, CI-Matrix, Sicherheit, Versionen)."""

import pathlib
import tomllib

ROOT_DIR = pathlib.Path(__file__).resolve().parent.parent

def test_gitignore_hygiene_patterns():
    """Prueft .gitignore auf Multi-Host Sync-Konflikte, Locks und Caches."""
    gitignore_path = ROOT_DIR / ".gitignore"
    assert gitignore_path.is_file(), ".gitignore muss existieren"
    content = gitignore_path.read_text(encoding="utf-8")
    lines = {line.strip() for line in content.splitlines() if line.strip() and not line.startswith("#")}

    required_patterns = [
        "*-conflict-*",
        "*.sync-conflict-*",
        "*.conflict",
        "*-CONFLIT-*",
        "*.sync-temp-*",
        "*-ASUS-GEI.*",
        "*-WORKSTATION-LG.*",
        "LOCK",
        "LOCK.*",
        "*.lock",
        "LOCK*.txt",
        "LOCK.permissions.json",
        ".pytest_cache/",
        ".ruff_cache/",
        "wheelhouse/",
        ".wheel-smoke/",
        "build/",
        "dist/",
    ]
    for pattern in required_patterns:
        assert pattern in lines, f".gitignore muss das Muster '{pattern}' enthalten"

def test_pyproject_pep621_metadata():
    """Prueft pyproject.toml auf PEP 621 URLs, Classifiers und Standard-Optionen."""
    pyproject_path = ROOT_DIR / "pyproject.toml"
    assert pyproject_path.is_file(), "pyproject.toml muss existieren"
    data = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))

    project = data.get("project", {})
    assert project.get("name") == "web-scraper"
    assert project.get("version") == "0.1.1"
    assert project.get("requires-python") == ">=3.10"
    assert project.get("license") == "MIT"

    urls = project.get("urls", {})
    required_urls = [
        "Homepage",
        "Repository",
        "Documentation",
        "Issues",
        "Changelog",
        "Security",
        "Parent Organization",
        "Umbrella Ecosystem",
    ]
    for key in required_urls:
        assert key in urls, f"pyproject.toml project.urls muss '{key}' enthalten"
        assert urls[key].startswith("https://github.com/"), f"URL fuer {key} ungueltig: {urls[key]}"

    classifiers = project.get("classifiers", [])
    assert "Operating System :: OS Independent" in classifiers
    assert "Programming Language :: Python :: 3.10" in classifiers
    assert "Programming Language :: Python :: 3.13" in classifiers

    pytest_cfg = data.get("tool", {}).get("pytest", {}).get("ini_options", {})
    assert pytest_cfg.get("testpaths") == ["tests"]
    assert "." in pytest_cfg.get("pythonpath", [])

def test_version_parity():
    """Stellt sicher, dass __version__, pyproject.toml, CHANGELOG und llms.txt synchron sind."""
    import web_scraper
    assert web_scraper.__version__ == "0.1.1"

    pyproject_path = ROOT_DIR / "pyproject.toml"
    pyproject_data = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))
    assert pyproject_data["project"]["version"] == web_scraper.__version__

    changelog_text = (ROOT_DIR / "CHANGELOG.md").read_text(encoding="utf-8")
    assert f"## [{web_scraper.__version__}] - 2026-09-10" in changelog_text

    llms_text = (ROOT_DIR / "llms.txt").read_text(encoding="utf-8")
    assert f"Version: {web_scraper.__version__}" in llms_text
    assert "Last-checked: 2026-09-11" in llms_text

def test_ci_matrix_workflow_definition():
    """Prueft .github/workflows/tests.yml auf Matrix, Concurrency und Steps."""
    ci_path = ROOT_DIR / ".github" / "workflows" / "tests.yml"
    assert ci_path.is_file(), "tests.yml CI-Workflow muss existieren"
    content = ci_path.read_text(encoding="utf-8")

    assert "cancel-in-progress: true" in content
    for v in ["3.10", "3.11", "3.12", "3.13"]:
        assert f'"{v}"' in content or f"'{v}'" in content, f"Python Version {v} fehlt in CI-Matrix"
    assert "ruff check ." in content
    assert "python -m compileall -q ." in content
    assert "pytest" in content

def test_stale_workflow_definition():
    """Prueft .github/workflows/stale.yml auf Standardvorgaben."""
    stale_path = ROOT_DIR / ".github" / "workflows" / "stale.yml"
    assert stale_path.is_file(), "stale.yml muss existieren"
    content = stale_path.read_text(encoding="utf-8")
    assert "actions/stale@v9" in content
    assert "days-before-stale: 30" in content
    assert "days-before-close: 7" in content

def test_security_policy_slas_and_contacts():
    """Prueft SECURITY.md auf zweisprachige SLAs, Versionstabelle und Kontakte."""
    sec_path = ROOT_DIR / "SECURITY.md"
    assert sec_path.is_file(), "SECURITY.md muss existieren"
    content = sec_path.read_text(encoding="utf-8")

    assert "48 hours" in content or "48 Stunden" in content
    assert "5 business days" in content or "5 Werktagen" in content
    assert "security@open-bricks.org" in content
    assert "security@ellmos.ai" in content
    assert "0.1.x" in content
    assert "SSRF" in content

def test_cli_executable_and_main_entrypoint():
    """Prueft __main__.py und den CLI-Einstiegspunkt."""
    main_py = ROOT_DIR / "web_scraper" / "__main__.py"
    assert main_py.is_file(), "web_scraper/__main__.py muss existieren"

    from web_scraper.core import main, WebScraper, get, links, forms, headers, extract, screenshot
    assert callable(main)
    assert callable(WebScraper)
    assert callable(get)
    assert callable(links)
    assert callable(forms)
    assert callable(headers)
    assert callable(extract)
    assert callable(screenshot)

def test_readme_bilingual_parity_and_badges():
    """Prueft README.md und README_de.md auf Badges und Paritaet."""
    readme_en = (ROOT_DIR / "README.md").read_text(encoding="utf-8")
    readme_de = (ROOT_DIR / "README_de.md").read_text(encoding="utf-8")

    for readme in [readme_en, readme_de]:
        assert "[English](README.md)" in readme
        assert "[Deutsch](README_de.md)" in readme
        assert "https://github.com/ellmos-ai" in readme
        assert "https://github.com/open-bricks" in readme
        assert "actions/workflows/tests.yml/badge.svg" in readme
        assert "astral-sh/ruff" in readme
        assert "llms.txt" in readme
        assert "```mermaid" in readme
        assert "flowchart TD" in readme
