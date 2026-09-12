# Pre-Release TODO: web-scraper

**Audit Date:** 2026-07-05
**Auditor:** Claude (claude-code)
**Target Repo:** `ellmos-ai/web-scraper`
**Last Care Check:** 2026-07-17 (Codex/GPT) — Same-page anchor filtering in `links()` fixed and regression-tested.

Erledigte Aufgaben gehören nach `DONE.md`.

## Offen (nach Release)

- [ ] Per-Hop-SSRF-Fix nach BACH `web_scrape.py` zurückportieren (BACH-Task 1139)
- [ ] Mehrsprachige CLI-/Fehlermeldungen (DE/EN/ZH/JA/ES/RU) — projektweites Ziel
- [ ] Optional: `robots.txt`-Beachtung als Opt-in-Flag
- [ ] Optional: einfaches Rate-Limiting / Retry-Backoff
- [ ] Release-Tag fuer den aktuellen Stand setzen (z. B. `v0.1.2` auf 3078116, der Commit mit
      `max_redirects`). BACH pinnt dieses Modul seit T-20260913-920596893 per vollem SHA, weil es
      hier keinen Tag gibt; mit Tag kann der Eintrag auf die lesbarere Form wie `accounts-core@v0.1.1`
      umgestellt werden. Angeregt im Zweitmodell-Review zu ellmos-ai/bach#42.

## Bekannte Grenzen

- Screenshot braucht `selenium` + Chrome/Chromedriver (Extra `[screenshot]`).
- Ohne Extras nutzt der Kern nur stdlib (urllib + Regex) — Extraktion ist dann gröber.
- SSRF-Schutz ist per Default an; interne Ziele nur mit `--allow-private`.

## STATUS

| Category | Status | Notes |
|----------|--------|-------|
| Secrets | :green_circle: | keine Secrets in tracked files |
| Private Data (PII) | :green_circle: | nur Autorname in LICENSE/pyproject |
| .gitignore | :green_circle: | minimum entries vorhanden |
| Language (English) | :green_circle: | README.md EN (primär), README_de zusätzlich |
| BACH Internals | :green_circle: | nur Provenance-Verweis, keine internen Dokumente |
| Database Files | :green_circle: | keine |
| README.md | :green_circle: | vorhanden, Englisch |
| LICENSE | :green_circle: | MIT |
| **Overall** | **READY** | |

**Gate Check Exit Code:** `0` (siehe `RELEASE_GATE.md`)
