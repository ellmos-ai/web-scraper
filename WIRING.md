# WIRING.md — Anbindung des web-scraper-Moduls

Beschreibt, wie `web-scraper` mit dem Skill `web-reading` und dem MCP-Server
`ellmos-filecommander-mcp` zusammenspielt.

## Überblick

```
                        ┌──────────────────────────────┐
                        │   web-scraper (dieses Modul)  │  ◄── vollwertig:
                        │   WebScraper + CLI            │      get/links/forms/
                        │   (Python, stdlib + Extras)   │      headers/extract/
                        └───────────┬──────────────────┘      screenshot
                                    │ kanonische Implementierung
              ┌─────────────────────┼─────────────────────────┐
              ▼                     ▼                          ▼
   ┌────────────────────┐  ┌──────────────────────┐  ┌─────────────────────┐
   │  Skill web-reading │  │ fc_web_fetch (MCP)   │  │  direkter Import     │
   │  (Router-Wrapper)  │  │ FileCommander, TS,   │  │  from web_scraper    │
   │  erkennt/­verweist  │  │ leichtgewichtig,     │  │  import extract, ... │
   │  auf dieses Modul  │  │ ohne Screenshot      │  │                      │
   └────────────────────┘  └──────────────────────┘  └─────────────────────┘
```

## Rollen

- **web-scraper (Modul):** die *kanonische*, vollwertige Implementierung inkl.
  Screenshot. Wiederverwendbar als CLI (`web-scraper …`) oder Bibliothek
  (`from web_scraper import WebScraper`).
- **Skill `web-reading`:** dokumentiert das Vorgehen (Content vs. Struktur) und
  routet zur *besten auf dem System verfügbaren* Web-Fähigkeit. Findet er nichts,
  empfiehlt er die Installation dieses Moduls.
- **`fc_web_fetch` (FileCommander-MCP):** leichtgewichtige Teilmenge (ohne
  Screenshot) mit Node-`fetch`, damit Datei- und Web-Operationen im selben,
  immer geladenen MCP-Server zusammenliegen. Bewusst als eigene, schlanke
  Implementierung — die vollwertige/konsistente Extraktion lebt hier im Modul.

## Warum FileCommander und nicht Homebase (MCP-Ziel)

Prüfbarer Faktor: FileCommander ist in **allen 7** MCP-Profilen geladen,
Homebase nur in `full` (1/7). Für den Alltags-Workflow „Dateioperationen +
Websuche zusammen" ist der Scraper damit im FileCommander praktisch immer
erreichbar. Der Preis: die Extraktions-Logik existiert doppelt (Python-Modul +
TS-Tool) — bei Änderungen beide Seiten abgleichen (siehe unten).

## Rückangleich-Pflicht

Verbesserungen an der Scraping-/Extraktions-Logik immer **beidseitig**
nachziehen: Python-Modul (`web_scraper/core.py`) ↔ TS-Tool
(`ellmos-filecommander-mcp` `fc_web_fetch`). Das Modul ist die Referenz.

## Nutzungsmuster

```python
# Als Bibliothek (z. B. aus einem anderen Modul/Agenten)
import sys
sys.path.insert(0, "/path/to/web-scraper")   # or simply: pip install the module
from web_scraper import WebScraper

scraper = WebScraper(timeout=15)
article = scraper.extract("https://example.com/post")["content"]
```

## Noch nicht verdrahtet (offen)

- [ ] n8n-Workflow: URL-Liste → extract → KnowledgeDigest-Ingest
- [ ] Optionaler `hb_web_`-Namespace in Homebase (falls dort später gewünscht;
      würde dieses Modul importieren statt neu zu implementieren)
