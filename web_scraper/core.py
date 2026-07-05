# -*- coding: utf-8 -*-
# SPDX-License-Identifier: MIT
"""
web_scraper.core - Standalone Web-Scraper / Browser-Steuerung
=============================================================
Portiert und erweitert aus BACH ``system/hub/web_scrape.py`` (WebScrapeHandler).

Operationen:
    get         HTTP GET, Body (gekuerzt) zurueckgeben
    links       Alle Links einer Seite extrahieren
    forms       Formular-Felder erkennen
    headers     Response-Headers anzeigen
    extract     Sauberen Haupttext (Markdown/Text) extrahieren
    screenshot  Screenshot rendern (braucht selenium-Extra)

Design:
    - Der Kern laeuft mit der Standardbibliothek (urllib + html.parser/regex).
    - Optionale Extras verbessern das Ergebnis, wenn installiert:
        requests       -> robusterer HTTP-Client (Redirects, SSL-Fallback)
        beautifulsoup4 -> sauberes Link-/Form-/Text-Parsing
        trafilatura    -> beste Haupttext-Extraktion als Markdown
        selenium       -> Screenshots
    - SSRF-Schutz: interne/private Zieladressen sind per Default blockiert.

Rueckgabe je Operation ist ein dict (programmatisch nutzbar). Die CLI
formatiert es lesbar; ``--json`` gibt das rohe dict aus.
"""
from __future__ import annotations

import argparse
import ipaddress
import json
import os
import re
import socket
import sys
from dataclasses import dataclass, field
from typing import Any, Optional
from urllib.parse import urljoin, urlparse

os.environ.setdefault("PYTHONIOENCODING", "utf-8")

__all__ = [
    "WebScraper",
    "FetchError",
    "BlockedTargetError",
    "Response",
    "get",
    "links",
    "forms",
    "headers",
    "extract",
    "screenshot",
    "main",
]

DEFAULT_USER_AGENT = "Mozilla/5.0 (compatible; web-scraper/0.1; +https://github.com/ellmos-ai/web-scraper)"
DEFAULT_TIMEOUT = 20
DEFAULT_MAX_BYTES = 5_000_000  # 5 MB Schutz gegen Riesen-Downloads
DEFAULT_MAX_REDIRECTS = 10
BODY_PREVIEW_CHARS = 10_000


class FetchError(Exception):
    """Netzwerk-/HTTP-Fehler beim Abruf."""


class BlockedTargetError(FetchError):
    """Ziel wurde vom SSRF-Schutz abgelehnt (interne/private Adresse)."""


@dataclass
class Response:
    """Vereinheitlichte HTTP-Antwort, unabhaengig vom Backend."""

    url: str
    status: int
    headers: dict = field(default_factory=dict)
    text: str = ""
    content_type: str = ""


# ---------------------------------------------------------------------------
# SSRF-Schutz
# ---------------------------------------------------------------------------

def _resolve_ips(host: str) -> list[str]:
    """Alle IPs eines Hosts aufloesen (leere Liste bei Fehler)."""
    try:
        infos = socket.getaddrinfo(host, None)
        return list({info[4][0] for info in infos})
    except socket.gaierror:
        return []


def _is_blocked_ip(ip: str) -> bool:
    try:
        addr = ipaddress.ip_address(ip)
    except ValueError:
        return True  # unparsbar -> vorsichtshalber blockieren
    return (
        addr.is_private
        or addr.is_loopback
        or addr.is_link_local
        or addr.is_reserved
        or addr.is_multicast
        or addr.is_unspecified
    )


def _guard_target(url: str, allow_private: bool) -> None:
    """Wirft BlockedTargetError, wenn das Ziel intern/privat ist."""
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise BlockedTargetError(f"Nur http/https erlaubt, nicht: {parsed.scheme!r}")
    if allow_private:
        return
    host = parsed.hostname or ""
    if not host:
        raise BlockedTargetError("Kein Host in URL")
    if host.lower() in ("localhost", "localhost.localdomain"):
        raise BlockedTargetError("localhost ist blockiert (allow_private=True zum Erlauben)")
    ips = _resolve_ips(host)
    if not ips:
        raise BlockedTargetError(f"Host nicht aufloesbar: {host}")
    for ip in ips:
        if _is_blocked_ip(ip):
            raise BlockedTargetError(
                f"Interne/private Zieladresse blockiert: {host} -> {ip} "
                f"(allow_private=True zum Erlauben)"
            )


# ---------------------------------------------------------------------------
# WebScraper
# ---------------------------------------------------------------------------

class WebScraper:
    """Konfigurierbarer Web-Scraper. Methoden geben je ein dict zurueck."""

    def __init__(
        self,
        timeout: int = DEFAULT_TIMEOUT,
        user_agent: str = DEFAULT_USER_AGENT,
        max_bytes: int = DEFAULT_MAX_BYTES,
        verify_ssl: bool = True,
        allow_private: bool = False,
    ) -> None:
        self.timeout = timeout
        self.user_agent = user_agent
        self.max_bytes = max_bytes
        self.verify_ssl = verify_ssl
        self.allow_private = allow_private

    # -- HTTP ---------------------------------------------------------------

    def _fetch(self, url: str) -> Response:
        """HTTP GET mit per-Hop-SSRF-Guard und begrenztem Redirect-Following.

        Jeder Redirect wird erneut gegen den SSRF-Schutz geprueft, damit eine
        oeffentliche URL nicht auf ein internes Ziel (z. B. Cloud-Metadata,
        127.0.0.1) weiterleiten kann.
        """
        current = url
        for _ in range(DEFAULT_MAX_REDIRECTS + 1):
            _guard_target(current, self.allow_private)
            resp, redirect = self._fetch_once(current)
            if redirect is None:
                assert resp is not None
                return resp
            current = urljoin(current, redirect)
        raise FetchError(f"Zu viele Redirects (>{DEFAULT_MAX_REDIRECTS})")

    def _fetch_once(self, url: str):
        """Ein einzelner HTTP-Hop OHNE Redirect-Following.

        Rueckgabe: (Response, None) bei finaler Antwort,
                   (None, location) bei einem Redirect.
        """
        try:
            import requests  # type: ignore
        except ImportError:
            return self._fetch_once_urllib(url)
        return self._fetch_once_requests(url, requests)

    def _fetch_once_requests(self, url: str, requests: Any):
        headers = {"User-Agent": self.user_agent}
        try:
            try:
                resp = requests.get(
                    url, timeout=self.timeout, headers=headers,
                    allow_redirects=False, stream=True,
                )
            except requests.exceptions.SSLError:
                if self.verify_ssl:
                    raise
                resp = requests.get(
                    url, timeout=self.timeout, headers=headers,
                    allow_redirects=False, stream=True, verify=False,
                )
            if resp.is_redirect and resp.headers.get("location"):
                location = resp.headers["location"]
                resp.close()
                return None, location
            resp.raise_for_status()
            # Groessenlimit beim Streamen durchsetzen
            chunks: list[bytes] = []
            total = 0
            for chunk in resp.iter_content(chunk_size=16_384):
                if not chunk:
                    continue
                total += len(chunk)
                if total > self.max_bytes:
                    break
                chunks.append(chunk)
            raw = b"".join(chunks)
            encoding = resp.encoding or "utf-8"
            text = raw.decode(encoding, errors="replace")
            return Response(
                url=str(resp.url),
                status=resp.status_code,
                headers={k: v for k, v in resp.headers.items()},
                text=text,
                content_type=resp.headers.get("content-type", ""),
            ), None
        except BlockedTargetError:
            raise
        except Exception as exc:  # requests.RequestException u.a.
            raise FetchError(str(exc)) from exc

    def _fetch_once_urllib(self, url: str):
        import ssl
        import urllib.error
        import urllib.request

        class _NoRedirect(urllib.request.HTTPRedirectHandler):
            def redirect_request(self, req, fp, code, msg, hdrs, newurl):
                return None  # Redirects nicht automatisch folgen

        handlers = [_NoRedirect()]
        if not self.verify_ssl:
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            handlers.append(urllib.request.HTTPSHandler(context=ctx))
        opener = urllib.request.build_opener(*handlers)
        req = urllib.request.Request(url, headers={"User-Agent": self.user_agent})
        try:
            with opener.open(req, timeout=self.timeout) as resp:
                raw = resp.read(self.max_bytes + 1)
                if len(raw) > self.max_bytes:
                    raw = raw[: self.max_bytes]
                hdrs = {k: v for k, v in resp.headers.items()}
                ctype = resp.headers.get("content-type", "")
                charset = resp.headers.get_content_charset() or "utf-8"
                return Response(
                    url=resp.geturl(),
                    status=getattr(resp, "status", 200) or 200,
                    headers=hdrs,
                    text=raw.decode(charset, errors="replace"),
                    content_type=ctype,
                ), None
        except urllib.error.HTTPError as exc:
            if exc.code in (301, 302, 303, 307, 308):
                location = exc.headers.get("location")
                if location:
                    return None, location
            raise FetchError(f"HTTP {exc.code}: {exc.reason}") from exc
        except Exception as exc:
            raise FetchError(str(exc)) from exc

    # -- Operationen --------------------------------------------------------

    def get(self, url: str) -> dict:
        """HTTP GET. Body wird auf BODY_PREVIEW_CHARS gekuerzt."""
        resp = self._fetch(url)
        body = resp.text
        truncated = len(body) > BODY_PREVIEW_CHARS
        return {
            "operation": "get",
            "url": resp.url,
            "status": resp.status,
            "content_type": resp.content_type,
            "length": len(body),
            "truncated": truncated,
            "body": body[:BODY_PREVIEW_CHARS] if truncated else body,
        }

    def headers(self, url: str) -> dict:
        """Response-Headers anzeigen."""
        resp = self._fetch(url)
        return {
            "operation": "headers",
            "url": resp.url,
            "status": resp.status,
            "headers": resp.headers,
        }

    def links(self, url: str, limit: int = 200) -> dict:
        """Alle (deduplizierten, absoluten) Links einer Seite."""
        resp = self._fetch(url)
        pairs = self._parse_links(resp.text)
        seen: set[str] = set()
        result: list[dict] = []
        for href, text in pairs:
            absolute = urljoin(resp.url, href)
            if absolute in seen:
                continue
            if absolute.startswith(("javascript:", "mailto:", "tel:", "#")):
                continue
            seen.add(absolute)
            result.append({"text": text.strip()[:120], "href": absolute})
            if len(result) >= limit:
                break
        return {"operation": "links", "url": resp.url, "count": len(result), "links": result}

    def forms(self, url: str) -> dict:
        """Formulare mit Action/Method/Feldern erkennen."""
        resp = self._fetch(url)
        return {"operation": "forms", "url": resp.url, "forms": self._parse_forms(resp.text)}

    def extract(self, url: str) -> dict:
        """Sauberen Haupttext extrahieren (trafilatura > bs4 > regex)."""
        resp = self._fetch(url)
        text, method, fmt = self._extract_content(resp.text, resp.url)
        return {
            "operation": "extract",
            "url": resp.url,
            "method": method,
            "format": fmt,
            "length": len(text),
            "content": text,
        }

    def screenshot(self, url: str, out_path: Optional[str] = None) -> dict:
        """Screenshot via selenium (Extra). out_path default: ~/.web-scraper."""
        _guard_target(url, self.allow_private)
        try:
            from selenium import webdriver
            from selenium.webdriver.chrome.options import Options
        except ImportError as exc:
            raise FetchError(
                "selenium nicht installiert: pip install web-scraper[screenshot]"
            ) from exc

        if out_path is None:
            base = os.environ.get(
                "WEB_SCRAPER_HOME", os.path.join(os.path.expanduser("~"), ".web-scraper")
            )
            os.makedirs(base, exist_ok=True)
            out_path = os.path.join(base, f"screenshot_{abs(hash(url)) & 0xFFFFFF:06x}.png")

        options = Options()
        options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--window-size=1280,1024")
        options.add_argument(f"--user-agent={self.user_agent}")
        driver = webdriver.Chrome(options=options)
        try:
            driver.set_page_load_timeout(self.timeout)
            driver.get(url)
            driver.save_screenshot(out_path)
        finally:
            driver.quit()
        return {"operation": "screenshot", "url": url, "path": out_path}

    # -- Parsing-Hilfen (bs4-bevorzugt, Regex-Fallback) ---------------------

    @staticmethod
    def _soup(html: str):
        try:
            from bs4 import BeautifulSoup  # type: ignore
        except ImportError:
            return None
        return BeautifulSoup(html, "html.parser")

    def _parse_links(self, html: str) -> list[tuple[str, str]]:
        soup = self._soup(html)
        if soup is not None:
            out = []
            for a in soup.find_all("a", href=True):
                out.append((a["href"], a.get_text(" ", strip=True)))
            return out
        # Regex-Fallback
        pairs = re.findall(
            r'<a[^>]*href=["\']([^"\']+)["\'][^>]*>(.*?)</a>',
            html, re.IGNORECASE | re.DOTALL,
        )
        return [(href, re.sub(r"<[^>]+>", "", text)) for href, text in pairs]

    def _parse_forms(self, html: str) -> list[dict]:
        soup = self._soup(html)
        forms: list[dict] = []
        if soup is not None:
            for form in soup.find_all("form"):
                fields = []
                for inp in form.find_all("input"):
                    fields.append({
                        "tag": "input",
                        "type": inp.get("type", "text"),
                        "name": inp.get("name", ""),
                    })
                for ta in form.find_all("textarea"):
                    fields.append({"tag": "textarea", "name": ta.get("name", "")})
                for sel in form.find_all("select"):
                    fields.append({"tag": "select", "name": sel.get("name", "")})
                forms.append({
                    "action": form.get("action", ""),
                    "method": (form.get("method") or "GET").upper(),
                    "fields": fields,
                })
            return forms
        # Regex-Fallback
        for form_html in re.findall(r"<form[^>]*>(.*?)</form>", html, re.DOTALL | re.IGNORECASE):
            action = re.search(r'action=["\']([^"\']*)["\']', form_html, re.IGNORECASE)
            method = re.search(r'method=["\']([^"\']*)["\']', form_html, re.IGNORECASE)
            fields = []
            for inp in re.finditer(r"<input[^>]+>", form_html, re.IGNORECASE):
                tag = inp.group()
                name = re.search(r'name=["\']([^"\']*)["\']', tag)
                itype = re.search(r'type=["\']([^"\']*)["\']', tag)
                fields.append({
                    "tag": "input",
                    "type": itype.group(1) if itype else "text",
                    "name": name.group(1) if name else "",
                })
            forms.append({
                "action": action.group(1) if action else "",
                "method": (method.group(1).upper() if method else "GET"),
                "fields": fields,
            })
        return forms

    def _extract_content(self, html: str, url: str) -> tuple[str, str, str]:
        """Gibt (text, method, format) zurueck."""
        # 1) trafilatura -> bestes Markdown
        try:
            import trafilatura  # type: ignore
            md = trafilatura.extract(
                html, url=url, output_format="markdown",
                include_links=True, include_formatting=True,
            )
            if md:
                return md, "trafilatura", "markdown"
        except ImportError:
            pass
        except Exception:
            pass
        # 2) beautifulsoup4 -> bereinigter Text
        soup = self._soup(html)
        if soup is not None:
            for tag in soup(["script", "style", "nav", "header", "footer", "aside", "noscript"]):
                tag.decompose()
            text = soup.get_text(separator="\n", strip=True)
            text = re.sub(r"\n{3,}", "\n\n", text)
            return text, "beautifulsoup", "text"
        # 3) Regex-Notfall
        stripped = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", "", html)
        stripped = re.sub(r"<[^>]+>", "", stripped)
        stripped = re.sub(r"\n{3,}", "\n\n", stripped).strip()
        return stripped, "regex", "text"


# ---------------------------------------------------------------------------
# Modul-Level Convenience-Funktionen
# ---------------------------------------------------------------------------

def _scraper(**kwargs: Any) -> WebScraper:
    return WebScraper(**kwargs)


def get(url: str, **kwargs: Any) -> dict:
    return _scraper(**kwargs).get(url)


def links(url: str, **kwargs: Any) -> dict:
    return _scraper(**kwargs).links(url)


def forms(url: str, **kwargs: Any) -> dict:
    return _scraper(**kwargs).forms(url)


def headers(url: str, **kwargs: Any) -> dict:
    return _scraper(**kwargs).headers(url)


def extract(url: str, **kwargs: Any) -> dict:
    return _scraper(**kwargs).extract(url)


def screenshot(url: str, out_path: Optional[str] = None, **kwargs: Any) -> dict:
    return _scraper(**kwargs).screenshot(url, out_path)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _format_human(data: dict) -> str:
    op = data.get("operation")
    if op == "get":
        head = (
            f"URL: {data['url']}\nStatus: {data['status']}\n"
            f"Content-Type: {data['content_type']}\nGroesse: {data['length']} Zeichen\n"
            + "=" * 40 + "\n\n"
        )
        body = data["body"]
        if data.get("truncated"):
            body += f"\n\n... (gekuerzt auf {BODY_PREVIEW_CHARS} Zeichen)"
        return head + body
    if op == "headers":
        lines = [f"Headers fuer {data['url']}", f"Status: {data['status']}", "=" * 40]
        for k, v in data["headers"].items():
            lines.append(f"  {k}: {v}")
        return "\n".join(lines)
    if op == "links":
        lines = [f"Links auf {data['url']} ({data['count']} gefunden)", "=" * 40]
        for item in data["links"]:
            lines.append(f"  {item['text'] or '(kein Text)'}\n    {item['href']}")
        return "\n".join(lines)
    if op == "forms":
        forms_ = data["forms"]
        if not forms_:
            return f"Keine Formulare auf {data['url']}"
        lines = [f"Formulare auf {data['url']} ({len(forms_)} gefunden)", "=" * 40]
        for i, form in enumerate(forms_, 1):
            lines.append(f"  Form #{i}: action={form['action'] or '?'} method={form['method']}")
            for fld in form["fields"]:
                if fld["tag"] == "input":
                    lines.append(f"    input[{fld['type']}] name={fld['name'] or '?'}")
                else:
                    lines.append(f"    {fld['tag']} name={fld['name'] or '?'}")
        return "\n".join(lines)
    if op == "extract":
        head = (
            f"Extrakt von {data['url']} (Methode: {data['method']}, "
            f"Format: {data['format']}, {data['length']} Zeichen)\n" + "=" * 40 + "\n\n"
        )
        return head + data["content"]
    if op == "screenshot":
        return f"Screenshot gespeichert: {data['path']}"
    return json.dumps(data, ensure_ascii=False, indent=2)


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="web-scraper",
        description="Standalone Web-Scraper (get/links/forms/headers/extract/screenshot)",
    )
    parser.add_argument(
        "operation",
        choices=["get", "links", "forms", "headers", "extract", "screenshot"],
    )
    parser.add_argument("url")
    parser.add_argument("--json", action="store_true", help="Rohes dict als JSON ausgeben")
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT)
    parser.add_argument("--no-verify-ssl", action="store_true", help="SSL-Zertifikat nicht pruefen")
    parser.add_argument(
        "--allow-private", action="store_true",
        help="Interne/private Zieladressen erlauben (SSRF-Schutz aus)",
    )
    parser.add_argument("--out", help="Ausgabedatei fuer screenshot")
    args = parser.parse_args(argv)

    scraper = WebScraper(
        timeout=args.timeout,
        verify_ssl=not args.no_verify_ssl,
        allow_private=args.allow_private,
    )
    try:
        if args.operation == "screenshot":
            data = scraper.screenshot(args.url, args.out)
        else:
            data = getattr(scraper, args.operation)(args.url)
    except (FetchError, BlockedTargetError) as exc:
        print(f"Fehler: {exc}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(data, ensure_ascii=False, indent=2))
    else:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        print(_format_human(data))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
