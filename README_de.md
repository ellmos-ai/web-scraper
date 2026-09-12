# web-scraper

[English](README.md) | [Deutsch](README_de.md)

[![Ecosystem: ellmos-ai](https://img.shields.io/badge/Ecosystem-ellmos--ai-blue.svg)](https://github.com/ellmos-ai)
[![Umbrella: open-bricks](https://img.shields.io/badge/Umbrella-open--bricks-purple.svg)](https://github.com/open-bricks)
[![CI](https://github.com/ellmos-ai/web-scraper/actions/workflows/tests.yml/badge.svg)](https://github.com/ellmos-ai/web-scraper/actions/workflows/tests.yml)
[![llms.txt](https://img.shields.io/badge/llms.txt-available-blue)](llms.txt)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![Code style: ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![Lizenz: MIT](https://img.shields.io/badge/Lizenz-MIT-yellow.svg)](LICENSE)
[![Pytest Passed](https://img.shields.io/badge/tests-23%20bestanden-brightgreen.svg)](tests/)
[![Sicherheits-SLA](https://img.shields.io/badge/Sicherheits--SLA-48h-blue.svg)](SECURITY.md)
[![SSRF-Schutz](https://img.shields.io/badge/Sicherheit-SSRF%20gesch%C3%BCtzt-green.svg)](#sicherheit)

![web-scraper — Fetch. Extract. Structure.](assets/banner.svg)

Eigenständiger Web-Scraper und leichte Browser-Steuerung, extrahiert aus dem
BACH-System (`web_scrape.py`). Seiten abrufen, Links und Formulare herauslösen,
Response-Headers ansehen, sauberen Haupttext als Markdown extrahieren und
Screenshots erstellen.

> [!NOTE]
> **KI- / Agenten-Integrationshinweis**: `web-scraper` wurde für autonome KI-Agenten-Pipelines entwickelt. Das Modul verarbeitet externe URLs sicher durch integrierten SSRF-Schutz gegen interne Subnetze sowie ein Standard-Download-Limit von 5 MB. Siehe [`llms.txt`](llms.txt) für Spezifikationen zur KI/Agenten-Integration.

- **Keine Pflicht-Abhängigkeiten** — der Kern läuft mit der Standardbibliothek
  (`urllib` + `html.parser`/Regex).
- **Optionale Extras** verbessern das Ergebnis, wenn installiert:
  `requests`, `beautifulsoup4`, `trafilatura`, `selenium`.
- **SSRF-Schutz** — interne/private Ziele sind per Default blockiert.

## Architektur & Pipeline

```mermaid
flowchart TD
    subgraph Client ["Eingabe & Aufrufe"]
        CLI["CLI: web-scraper"]
        LIB["Python-API: WebScraper / extract()"]
        AGENT["KI-Agent / Tool-Runner"]
    end

    subgraph SecurityGate ["Pre-Flight Sicherheits-Gate"]
        SCHEME{"Schema-Prüfung"}
        SSRF{"SSRF-Resolver-Schutz"}
        BLOCK["Anfrage blockiert (SSRF-Sicherheitsfehler)"]
    end

    subgraph FetchPipeline ["Fetch-Engine"]
        HTTP["HTTP-Client (urllib stdlib / requests)"]
        CAP["Größen- & Timeout-Schutz (max. 5 MB)"]
    end

    subgraph Processing ["Extraktion & Verarbeitung"]
        P_GET["get: Status & Body-Vorschau"]
        P_LINKS["links: Absolute URL-Deduplizierung"]
        P_FORMS["forms: Formular-Aktionen & Eingabefelder"]
        P_EXTRACT["extract: Trafilatura / BeautifulSoup4 / Regex"]
        P_SCREENSHOT["screenshot: Headless Selenium WebDriver"]
    end

    CLI --> SCHEME
    LIB --> SCHEME
    AGENT --> SCHEME

    SCHEME -->|"http / https"| SSRF
    SCHEME -->|"andere Schemata"| BLOCK

    SSRF -->|"Private / Loopback-IP (allow_private=False)"| BLOCK
    SSRF -->|"Öffentliche IP / Freigegeben"| HTTP

    HTTP --> CAP
    CAP --> P_GET
    CAP --> P_LINKS
    CAP --> P_FORMS
    CAP --> P_EXTRACT
    CAP --> P_SCREENSHOT

    subgraph Output ["Strukturierte Ausgabe"]
        RESULT["Standardisiertes Python-Dict / JSON (--json)"]
    end

    P_GET --> RESULT
    P_LINKS --> RESULT
    P_FORMS --> RESULT
    P_EXTRACT --> RESULT
    P_SCREENSHOT --> RESULT
```

## Installation

```bash
# nur Kern (stdlib)
pip install .

# empfohlen (robustes HTTP + sauberes Parsing + beste Extraktion)
pip install ".[http,extract]"

# alles inkl. Screenshots
pip install ".[all]"
```

## CLI

```bash
web-scraper get      https://example.com
web-scraper links    https://example.com
web-scraper forms    https://example.com
web-scraper headers  https://example.com
web-scraper extract  https://example.com          # sauberer Haupttext (Markdown)
web-scraper screenshot https://example.com --out shot.png

# rohes dict als JSON
web-scraper extract https://example.com --json

# interne Ziele erlauben (SSRF-Schutz aus) / TLS-Prüfung überspringen
web-scraper get http://127.0.0.1:8080 --allow-private
web-scraper get https://self-signed.example --no-verify-ssl
```

## Als Bibliothek

```python
from web_scraper import WebScraper, extract

scraper = WebScraper(timeout=15, allow_private=False)

print(scraper.get("https://example.com")["status"])
print(scraper.links("https://example.com")["count"])
print(extract("https://example.com")["content"])   # Convenience-Funktion
```

Jede Operation gibt ein einfaches `dict` zurück — leicht programmatisch
weiterzuverarbeiten. Die CLI formatiert es lesbar; `--json` gibt das rohe dict aus.

### KI-Agenten- & Tool-Integration

Für autonome KI-Agenten, die sauberen Seiteninhalt für den LLM-Prompt-Kontext benötigen:

```python
from web_scraper import extract

def fetch_page_context(url: str) -> str:
    """Ruft bereinigten Markdown-Text für den LLM-Kontext ab, geschützt gegen SSRF."""
    result = extract(url)
    if result.get("error"):
        raise RuntimeError(f"Scraping fehlgeschlagen: {result['error']}")
    return result["content"]
```

## Operationen

| Operation | Rückgabe | Hinweis |
|---|---|---|
| `get` | Body (auf 10k Zeichen gekürzt), Status, Content-Type | |
| `links` | deduplizierte absolute Links `{text, href}` | überspringt `javascript:`/`mailto:`/`tel:`/`#` |
| `forms` | Formulare mit `action`, `method`, `fields` | |
| `headers` | vollständige Response-Headers | |
| `extract` | sauberer Haupttext + `method`/`format` | `trafilatura` → `beautifulsoup` → `regex` |
| `screenshot` | Pfad des gespeicherten PNG | braucht `selenium`-Extra + Browser-Driver |

## Sicherheit

- `get`/`extract`/… lösen den Ziel-Host auf und lehnen private, Loopback-,
  Link-Local-, reservierte und Multicast-Adressen ab (außer `allow_private=True`).
- Nur `http`/`https`-Schemata sind erlaubt.
- Downloads sind auf 5 MB begrenzt (`max_bytes`), Redirects folgt das HTTP-Backend.

## Herkunft

Extrahiert aus BACH `system/hub/web_scrape.py` (WebScrapeHandler, Task 996) am
2026-07-05. Das BACH-Regex-Parsing wurde durch `beautifulsoup4`/`trafilatura`
mit Regex-Fallback ersetzt; SSRF-Schutz und Größenlimit kamen hinzu.

## Tests

So führst du die Offline-Unit-Tests lokal aus:

```bash
# Entwicklungs-Abhängigkeiten installieren
pip install -e ".[dev]"

# Tests ausführen
python -m pytest
```

## Lizenz

MIT — siehe [LICENSE](LICENSE).
