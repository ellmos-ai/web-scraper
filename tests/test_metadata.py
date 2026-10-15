# -*- coding: utf-8 -*-
# SPDX-License-Identifier: MIT
"""Automatisierte Vertragstestsuite (Hygiene, PEP 621, CI-Matrix, Sicherheit, Versionen, SBOM, 18-Punkte-Navigation)."""

import pathlib
try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib

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
        ".pytest_temp/",
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
    assert project.get("license-files") == ["LICENSE", "NOTICE", "THIRD_PARTY_LICENSES.md"]

    urls = project.get("urls", {})
    required_urls = [
        "Homepage",
        "Repository",
        "Documentation",
        "Issues",
        "Changelog",
        "Security",
        "Notice",
        "Third-Party Licenses",
        "Marketing Log",
        "LLM Ready",
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

    keywords = project.get("keywords", [])
    assert len(keywords) == 20, f"keywords muss genau 20 gesaettigte Begriffe enthalten, erhalten: {len(keywords)}"
    for kw in ["web-scraping", "scraper", "zero-dependencies", "ssrf-protection", "zero-egress", "fail-closed"]:
        assert kw in keywords, f"Keyword '{kw}' fehlt in pyproject.toml"

    pytest_cfg = data.get("tool", {}).get("pytest", {}).get("ini_options", {})
    assert pytest_cfg.get("testpaths") == ["tests"]
    assert "." in pytest_cfg.get("pythonpath", [])
    assert "--basetemp=.pytest_temp" in pytest_cfg.get("addopts", "")

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
    assert "Last-checked: 2026-09-22" in llms_text

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
    assert "§ 521 BGB" in content

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

def test_notice_attribution_file():
    """Prueft die kanonische root NOTICE-Datei auf Urheberangaben und Invarianten."""
    notice_path = ROOT_DIR / "NOTICE"
    assert notice_path.is_file(), "NOTICE-Datei muss im Root existieren"
    content = notice_path.read_text(encoding="utf-8")
    assert "web-scraper" in content
    assert "Lukas Geiger" in content
    assert "ellmos-ai" in content
    assert "open-bricks" in content
    assert "BACH" in content
    assert "INV-LOCAL-01" in content
    assert "INV-SLA-10" in content
    assert "§ 521 BGB" in content

def test_sbom_third_party_licenses():
    """Prueft THIRD_PARTY_LICENSES.md auf Level 1 SBOM und Invarianten."""
    sbom_path = ROOT_DIR / "THIRD_PARTY_LICENSES.md"
    assert sbom_path.is_file(), "THIRD_PARTY_LICENSES.md muss existieren"
    content = sbom_path.read_text(encoding="utf-8")
    assert "SPDX-License-Identifier" in content
    assert "INV-LOCAL-01" in content
    assert "INV-SLA-10" in content
    assert "RunAsInvoker" in content
    assert "Zero-Copyleft" in content
    assert "§ 521 BGB" in content

def test_readme_bilingual_navigation_parity_18_points():
    """Prueft README.md und README_de.md auf vollstaendige 18-Punkte-Navigationsparitaet."""
    readme_en = (ROOT_DIR / "README.md").read_text(encoding="utf-8")
    readme_de = (ROOT_DIR / "README_de.md").read_text(encoding="utf-8")

    for num in range(1, 19):
        anchor = f'id="sec-{num:02d}"'
        assert anchor in readme_en, f"Anchor {anchor} fehlt in README.md"
        assert anchor in readme_de, f"Anchor {anchor} fehlt in README_de.md"

    for readme in [readme_en, readme_de]:
        assert "[English](README.md)" in readme
        assert "[Deutsch](README_de.md)" in readme
        assert "https://github.com/ellmos-ai" in readme
        assert "https://github.com/open-bricks" in readme
        assert "actions/workflows/tests.yml/badge.svg" in readme
        assert "astral-sh/ruff" in readme
        assert "llms.txt" in readme
        assert "NOTICE" in readme
        assert "THIRD_PARTY_LICENSES.md" in readme
        assert "[PERSONA-01]" in readme
        assert "[PERSONA-02]" in readme
        assert "[PERSONA-03]" in readme
        assert "[PERSONA-04]" in readme
        assert "§ 521 BGB" in readme

def test_mermaid_diagrams_syntax_and_guards():
    """Prueft README.md und README_de.md auf Flowchart und SequenceDiagram ohne unquotierte Semikolons."""
    readme_en = (ROOT_DIR / "README.md").read_text(encoding="utf-8")
    readme_de = (ROOT_DIR / "README_de.md").read_text(encoding="utf-8")

    for readme in [readme_en, readme_de]:
        assert "flowchart TD" in readme
        assert "sequenceDiagram" in readme
        assert "autonumber" in readme
        # Sequenzdiagramm darf keine Statement-Terminator-Semikolons enthalten
        lines = readme.splitlines()
        in_sequence = False
        for line in lines:
            if "sequenceDiagram" in line:
                in_sequence = True
            elif in_sequence and line.startswith("```"):
                in_sequence = False
            elif in_sequence:
                assert ";" not in line, f"Semikolon im sequenceDiagram nicht erlaubt: {line}"

def test_marketing_log_recency():
    """Prueft MARKETING-LOG.txt auf Aktualitaet und Vollstaendigkeit."""
    log_path = ROOT_DIR / "MARKETING-LOG.txt"
    assert log_path.is_file(), "MARKETING-LOG.txt muss existieren"
    content = log_path.read_text(encoding="utf-8")
    assert "Pfad B" in content
    assert "2026-09-22" in content
    assert "[PERSONA-01]" in content
    assert "Competitive Matrix" in content or "Vergleichsmatrix" in content
