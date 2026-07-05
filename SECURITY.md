# Security Policy

## Reporting a Vulnerability

Please report security vulnerabilities via GitHub's **Private Vulnerability Reporting**
("Report a vulnerability" under the repository's *Security* tab). Please do not open
public issues for security problems. We aim to acknowledge reports promptly.

## Security Notes

`web-scraper` performs outbound HTTP(S) requests, so a few safeguards apply:

- **SSRF guard (default on):** internal/private/loopback/link-local targets are blocked,
  and **every redirect hop is re-checked** so a public URL cannot redirect into an
  internal target. It can be disabled with `allow_private=True` / `--allow-private` —
  use this only for trusted internal targets.
- **Only `http`/`https`** schemes are allowed.
- **Size cap:** responses are limited to 5 MB.
- **Redirect cap:** redirect chains are bounded.
- The module does not store or transmit credentials of its own.

## Supported Versions

The latest released version receives security fixes.
