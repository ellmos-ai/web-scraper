# TODO — web-scraper

Erledigte Aufgaben gehören nach `DONE.md`.

## Status

| Feld | Wert |
|---|---|
| Status | development |
| Version | 0.1.0 |
| Sichtbarkeit | public-fähig (kein PII), noch nicht released |
| Release-Gate | offen |

## Offen

- [ ] `RELEASE_GATE.md` erzeugen + Final Gate Check laufen lassen (`_scripts/final_gate_check.py`) vor Public-Release
- [ ] `SECURITY.md` ergänzen (vor Public-Release Pflicht)
- [ ] Optional: englische README ist bereits Primär (`README.md`); DE-Fassung `README_de.md` vorhanden
- [ ] Mehrsprachige CLI-/Fehlermeldungen (DE/EN/ZH/JA/ES/RU) — projektweites Ziel, noch offen
- [ ] Optional: `robots.txt`-Beachtung als Opt-in-Flag
- [ ] Optional: einfaches Rate-Limiting / Retry-Backoff

## Bekannte Grenzen

- Screenshot braucht `selenium` + Chrome/Chromedriver (Extra `[screenshot]`).
- Ohne Extras nutzt der Kern nur stdlib (urllib + Regex) — Extraktion ist dann gröber.
- SSRF-Schutz ist per Default an; interne Ziele nur mit `--allow-private`.
