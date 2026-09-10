# Security Policy / Sicherheitsrichtlinie

## Supported Versions / Unterstützte Versionen

| Version | Supported / Unterstützt | Status |
| ------- |:-----------------------:| ------ |
| 0.1.x   | :white_check_mark:      | Active support (current) |
| < 0.1.0 | :x:                     | End-of-Life |

---

## English Security Policy

### Core Security Principles & Invariants

`web-scraper` is a standalone, lightweight web extraction engine and browser control utility (extracted from the BACH system). Because it executes network requests against external web endpoints, strict defense-in-depth safeguards are enforced:

1. **SSRF Guard & DNS Hop Re-Validation:**
   - Outbound requests to private, loopback, link-local, and broadcast IP ranges (`127.0.0.0/8`, `10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`, `169.254.0.0/16`, `::1`, `fc00::/7`, `fe80::/10`) are blocked by default via `BlockedTargetError`.
   - **Redirect Verification:** Every redirect hop is independently resolved and verified before following, preventing DNS rebinding and redirect pivot attacks into internal networks.
   - Private endpoints can only be accessed by explicitly passing `allow_private=True` or `--allow-private`.

2. **Scheme Whitelisting:**
   - Only `http` and `https` schemes are permitted. Dangerous schemes (`file://`, `ftp://`, `gopher://`, `javascript:`, `data:`) are rejected immediately.

3. **Bounded Resources & Denial-of-Service Defense:**
   - **Response Size Cap:** Maximum payload size is capped at 5 MB (`max_bytes=5_000_000`) to prevent memory exhaustion and zip-bomb style attacks.
   - **Bounded Redirects:** Redirect chains are strictly limited (`max_redirects=10`).
   - **Configurable Timeouts:** Default network timeout of 15 seconds prevents hanging worker processes.

4. **Zero Credential Persistence:**
   - The module does not store, persist, or leak authentication tokens, API keys, or private session cookies.

### Reporting a Vulnerability

If you discover a security vulnerability or bypass in `web-scraper`, please report it privately:

1. **GitHub Security Advisory (Preferred):** Open a private report at [ellmos-ai/web-scraper Security Advisories](https://github.com/ellmos-ai/web-scraper/security/advisories).
2. **Email Contacts:** Send vulnerability details to `security@open-bricks.org` and `security@ellmos.ai` (CC: `lukas@open-bricks.org`, `support@lukasgeiger.com`).

**Service Level Agreement (SLA):**
- **Acknowledgment:** Within 48 hours.
- **Triage & Status Assessment:** Within 5 business days.
- **Remediation & Release Coordination:** Delivered rapidly with verified automated test suites.

Please do not disclose potential vulnerabilities publicly in issues or pull requests.

---

## Deutsche Sicherheitsrichtlinie (German)

### Sicherheits- und Schutzgrundsätze

`web-scraper` ist ein schlankes, eigenständiges Werkzeug zur Webseiten-Extraktion und Browsersteuerung (portiert aus dem BACH-System). Da das Modul ausgehende Netzwerkanfragen ausführt, gelten strikte Sicherheitsvorkehrungen:

1. **SSRF-Schutz & DNS-Hop-Validierung:**
   - Anfragen an private, Loopback-, Link-Local- oder Broadcast-Adressbereiche (`127.0.0.0/8`, `10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`, `169.254.0.0/16`, `::1`, `fc00::/7`, `fe80::/10`) werden standardmäßig via `BlockedTargetError` blockiert.
   - **Hop-Validierung:** Jeder einzelne Weiterleitungs-Hop (Redirect) wird vor dem Folgen neu aufgelöst und geprüft, um Angriffe über Umleitungen auf interne Systeme zu verhindern.
   - Private Ziele können nur durch explizite Angabe von `allow_private=True` bzw. `--allow-private` angesprochen werden.

2. **Protokoll-Positivliste:**
   - Ausschließlich `http` und `https` sind zugelassen. Potenziell gefährliche Schemata wie `file://`, `ftp://`, `gopher://` oder `data:` werden abgewiesen.

3. **Ressourcenbegrenzung & DoS-Schutz:**
   - **Antwortgrößenbegrenzung:** Die maximale Download-Größe ist standardmäßig auf 5 MB (`max_bytes=5_000_000`) begrenzt.
   - **Weiterleitungsbegrenzung:** Weiterleitungsketten sind auf maximal 10 Hops beschränkt.
   - **Deterministische Timeouts:** Standard-Timeout von 15 Sekunden verhindert blockierte Hintergrundprozesse.

4. **Keine Speicherung von Zugangsdaten:**
   - Das Modul speichert, überträgt oder persistiert keine Benutzer-Credentials, Tokens oder Sitzungsschlüssel.

### Sicherheitslücke melden

Wenn Sie eine Sicherheitslücke oder Schwachstelle in `web-scraper` entdecken, melden Sie diese bitte vertraulich:

1. **GitHub Security Advisory (Bevorzugt):** Erstellen Sie einen privaten Bericht unter [ellmos-ai/web-scraper Security Advisories](https://github.com/ellmos-ai/web-scraper/security/advisories).
2. **E-Mail-Kontakte:** Senden Sie die Details an `security@open-bricks.org` und `security@ellmos.ai` (CC: `lukas@open-bricks.org`, `support@lukasgeiger.com`).

**Service Level Agreement (SLA):**
- **Eingangsbestätigung:** Innerhalb von 48 Stunden.
- **Ersteinschätzung & Triage:** Innerhalb von 5 Werktagen.
- **Behebung & Release:** Schnellstmöglich nach Verifikation durch automatisierte Testläufe.
