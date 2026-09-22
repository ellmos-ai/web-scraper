# Third-Party Software & Licenses (SBOM)

**Repository:** `ellmos-ai/web-scraper`  
**Product:** web-scraper — Standalone SSRF-Guarded Web Scraper & Headless Content Extractor  
**Release Version:** 0.1.1  
**Author / Maintainer:** Lukas Geiger / ellmos-ai / open-bricks  
**Primary License:** MIT License ([LICENSE](LICENSE))  
**SPDX-License-Identifier:** MIT  

---

## 1. Overview & Architectural Isolation

`web-scraper` is engineered as a local-first, lightweight web scraper and content extraction utility tailored for autonomous AI agents, developer tooling, and automated workflows.

By design, the core execution engine runs with **zero required external dependencies**, relying exclusively on the Python standard library. Optional extensions enhance extraction fidelity and enable screenshot capture, using only permissively licensed packages.

### 1.1 Invariant Guarantees (INV-LOCAL-01 through INV-SLA-10)

| Invariant | Category | Description | Status |
|---|---|---|---|
| **INV-LOCAL-01** | Zero External Dependencies | Core operations (`get`, `links`, `forms`, `headers`, `extract`) run 100% on Python Standard Library (`urllib`, `html.parser`, `re`). | **PASS** |
| **INV-LOCAL-02** | Fail-Closed SSRF Guard | All target hosts are resolved and validated against loopback (`127.0.0.0/8`, `::1`), private RFC 1918 (`10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`), link-local (`169.254.0.0/16`), multicast, and reserved subnets before socket connection. | **PASS** |
| **INV-LOCAL-03** | Hop-by-Hop Redirect Guard | HTTP redirects are tracked and re-evaluated through the SSRF resolver gate on every hop up to a strict, configurable cap (`max_redirects`). | **PASS** |
| **INV-LOCAL-04** | Body Cap & Resource Bounds | Response payloads are capped at a strict byte limit (`max_bytes`, default 5 MB) and timeouts (`timeout`, default 15s) to prevent memory exhaustion and DoS. | **PASS** |
| **INV-LOCAL-05** | Headless Content Cascade | Content extraction gracefully falls back through a 3-tier cascade: Trafilatura -> BeautifulSoup4 -> Regex, guaranteeing usable output across environments. | **PASS** |
| **INV-LOCAL-06** | Zero-Egress Air-Gapped Operation | Zero background telemetry, analytics tracking, license checks, or third-party phone-home calls. The only network egress is directed to user-specified target URLs. | **PASS** |
| **INV-LOCAL-07** | Least-Privilege Execution | Runs entirely in standard unprivileged user mode (`RunAsInvoker`). Zero requirement for Windows UAC elevation, root, or sudo privileges. | **PASS** |
| **INV-LOCAL-08** | Level 1 SBOM & Zero-Copyleft Isolation | 100% permissive open-source licensing (MIT, Apache-2.0, PSF-2.0). Zero copyleft contamination (GPL, AGPL, LGPL). | **PASS** |
| **INV-LOCAL-09** | Statutory Disclaimer | German statutory disclaimer under § 521 BGB (Gefälligkeitsrecht) limiting liability for free software to intent and gross negligence. | **PASS** |
| **INV-SLA-10** | 48-Hour Security Response SLA | Vulnerability disclosures acknowledged within 48 hours; initial triage and remediation target within 5 business days. | **PASS** |

### 1.2 Unprivileged RunAsInvoker Non-Elevation Certification

`web-scraper` is certified to operate strictly under unprivileged user execution (`RunAsInvoker`):
- Does not request or require Windows UAC elevation or Linux/macOS root/sudo rights.
- Does not install system-wide services, drivers, or scheduled kernel tasks.
- Confines all disk writes exclusively to caller-designated output paths (e.g., screenshot targets) or temporary working files.

---

## 2. Runtime Dependencies (Level 1 SBOM)

### Core Runtime (Standard Library Only)

When installed without optional extras (`pip install .`), `web-scraper` requires **zero external third-party packages**:

| Component | Standard / Module | License | SPDX Identifier | Functionality |
|---|---|---|---|---|
| Python Standard Library | `>=3.10` | Python Software Foundation | `PSF-2.0` | Core networking (`urllib.request`), HTML parsing (`html.parser`), IP resolution (`ipaddress`, `socket`), regex (`re`), CLI (`argparse`) |

### Optional Runtime Upgrades

Users may install optional extras for enhanced parsing, improved HTTP connection pooling, advanced Markdown extraction, or headless browser screenshot capture:

| Package | Version Range | License | SPDX Identifier | Profile / Extra | Usage / Functionality |
|---|---|---|---|---|---|
| **requests** | `>=2.28` | Apache License 2.0 | `Apache-2.0` | `http`, `all` | Enhanced HTTP client with automatic connection pooling and certificate validation |
| **beautifulsoup4** | `>=4.11` | MIT License | `MIT` | `parse`, `extract`, `all` | Robust DOM navigation and resilient link/form parsing |
| **trafilatura** | `>=1.6` | Apache License 2.0 | `Apache-2.0` | `extract`, `all` | State-of-the-art main text web content extraction to clean Markdown |
| **selenium** | `>=4.10` | Apache License 2.0 | `Apache-2.0` | `screenshot`, `all` | Headless WebDriver automation for high-resolution PNG page screenshots |

---

## 3. Development & Testing Dependencies

| Package | Version Range | License | SPDX Identifier | Purpose |
|---|---|---|---|---|
| **pytest** | `>=7.0.0` | MIT License | `MIT` | Offline automated unit and contract test suite |
| **ruff** | `>=0.4.0` | MIT / Apache-2.0 | `MIT OR Apache-2.0` | High-performance Python linter and code formatter |

---

## 4. Zero-Copyleft Contagion Guarantee

1. **User Freedom & Data Autonomy:** Any web content, extracted Markdown, links, forms, or screenshots retrieved using `web-scraper` remain the sole property and responsibility of the operator. `web-scraper` asserts **zero copyleft claim or licensing obligations** over fetched content or derivative outputs.
2. **Permissive Isolation:** All direct and optional dependencies use exclusively MIT, Apache-2.0, or PSF-2.0 licenses. There is zero viral copyleft contamination affecting downstream proprietary or commercial applications.

---

## 5. Statutory Legal Notice (§ 521 BGB)

Die Bereitstellung dieser Software erfolgt unentgeltlich. Nach deutschem Recht gemäß § 521 BGB (Schenkungs- und Gefälligkeitsrecht) ist die Haftung des Anbieters auf Vorsatz und grobe Fahrlässigkeit beschränkt. Für Mangelfolgeschäden oder leichte Fahrlässigkeit besteht keine Haftung.
