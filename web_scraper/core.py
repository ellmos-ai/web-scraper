# -*- coding: utf-8 -*-
# SPDX-License-Identifier: MIT
"""
web_scraper.core - Standalone Web-Scraper / Browser-Steuerung
=============================================================
Portiert und erweitert aus BACH ``system/hub/web_scrape.py`` (WebScrapeHandler).
Teile aus SentinelFleet, vom alleinigen Rechteinhaber Lukas Geiger am 25.10.2026 unter MIT neu lizenziert.

Operationen:
    get         HTTP GET, Body (gekürzt) zurückgeben
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
import http.client
import ipaddress
import json
import os
import re
import socket
import ssl
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
    """Vereinheitlichte HTTP-Antwort, unabhängig vom Backend."""

    url: str
    status: int
    headers: dict = field(default_factory=dict)
    text: str = ""
    content_type: str = ""


METADATA_HOSTS = frozenset({
    "metadata.google.internal",
    "metadata",
    "instance-data",
})
LOCALHOST_NAMES = frozenset({"localhost", "localhost.localdomain", "ip6-localhost"})


# ---------------------------------------------------------------------------
# SSRF-Schutz & DNS-Pinning
# ---------------------------------------------------------------------------

def _address_block_reason(raw_ip: str) -> Optional[str]:
    """Grund nennen, warum eine Adresse unzulässig ist (oder None, wenn öffentlich)."""
    try:
        address = ipaddress.ip_address(raw_ip.strip("[]"))
    except ValueError:
        return f"'{raw_ip}' ist keine parsbare IP-Adresse"

    mapped = getattr(address, "ipv4_mapped", None)
    if mapped is not None:
        address = mapped

    for predicate, label in (
        (address.is_loopback, "loopback"),
        (address.is_link_local, "link-local"),
        (address.is_unspecified, "unspecified"),
        (address.is_multicast, "multicast"),
        (address.is_reserved, "reserved"),
        (address.is_private, "private"),
    ):
        if predicate:
            return f"{address} ist eine {label}-Adresse"
    return None


def _is_blocked_ip(ip: str) -> bool:
    return _address_block_reason(ip) is not None


def _resolve_ips(host: str) -> list[str]:
    """Alle IPs eines Hosts auflösen (leere Liste bei Fehler)."""
    try:
        infos = socket.getaddrinfo(host, None)
        return sorted({info[4][0] for info in infos})
    except socket.gaierror:
        return []


def _same_address(left: str, right: str) -> bool:
    try:
        addr_left = ipaddress.ip_address(left.strip("[]"))
        addr_right = ipaddress.ip_address(right.strip("[]"))
        mapped_l = getattr(addr_left, "ipv4_mapped", None)
        if mapped_l is not None:
            addr_left = mapped_l
        mapped_r = getattr(addr_right, "ipv4_mapped", None)
        if mapped_r is not None:
            addr_right = mapped_r
        return addr_left == addr_right
    except ValueError:
        return False


class _PinnedHTTPConnection(http.client.HTTPConnection):
    def __init__(self, host: str, port: int, pinned_ip: str, timeout: float = DEFAULT_TIMEOUT):
        super().__init__(host, port, timeout=timeout)
        self.pinned_ip = pinned_ip

    def connect(self) -> None:
        self.sock = socket.create_connection((self.pinned_ip, self.port), self.timeout)
        peer = self.sock.getpeername()[0]
        if not _same_address(peer, self.pinned_ip):
            self.sock.close()
            raise BlockedTargetError(
                f"Connected peer {peer} differs from validated address {self.pinned_ip}"
            )


class _PinnedHTTPSConnection(http.client.HTTPSConnection):
    def __init__(
        self,
        host: str,
        port: int,
        pinned_ip: str,
        timeout: float = DEFAULT_TIMEOUT,
        context: Optional[ssl.SSLContext] = None,
    ):
        ctx = context or ssl.create_default_context()
        super().__init__(host, port, timeout=timeout, context=ctx)
        self.pinned_ip = pinned_ip

    def connect(self) -> None:
        raw = socket.create_connection((self.pinned_ip, self.port), self.timeout)
        peer = raw.getpeername()[0]
        if not _same_address(peer, self.pinned_ip):
            raw.close()
            raise BlockedTargetError(
                f"Connected peer {peer} differs from validated address {self.pinned_ip}"
            )
        server_hostname = self.host.strip("[]")
        self.sock = self._context.wrap_socket(raw, server_hostname=server_hostname)


def _guard_target(url: str, allow_private: bool = False) -> tuple[str, list[str]]:
    """Wirft BlockedTargetError, wenn das Ziel intern/privat ist.
    Gibt (host, resolved_ips) zurück.
    """
    parsed = urlparse(url)
    if parsed.scheme.lower() not in ("http", "https"):
        raise BlockedTargetError(f"Nur http/https erlaubt, nicht: {parsed.scheme!r}")

    host = (parsed.hostname or "").lower()
    if not host:
        raise BlockedTargetError("Kein Host in URL")

    if allow_private:
        try:
            ipaddress.ip_address(host.strip("[]"))
            return host, [host.strip("[]")]
        except ValueError:
            ips = _resolve_ips(host)
            return host, (ips if ips else [host])

    if host in LOCALHOST_NAMES:
        raise BlockedTargetError("localhost ist blockiert (allow_private=True zum Erlauben)")
    if host in METADATA_HOSTS:
        raise BlockedTargetError(f"'{host}' ist ein Cloud-Instance-Metadata-Endpoint")

    # IP-Literal prüfen
    try:
        ipaddress.ip_address(host.strip("[]"))
    except ValueError:
        pass
    else:
        literal = host.strip("[]")
        reason = _address_block_reason(literal)
        if reason:
            raise BlockedTargetError(
                f"Interne/private Zieladresse blockiert ({reason}): {host} -> {literal} "
                f"(allow_private=True zum Erlauben)"
            )
        return host, [literal]

    ips = _resolve_ips(host)
    if not ips:
        raise BlockedTargetError(f"Host nicht auflösbar: {host}")
    for ip in ips:
        reason = _address_block_reason(ip)
        if reason:
            raise BlockedTargetError(
                f"Interne/private Zieladresse blockiert ({reason}): {host} -> {ip} "
                f"(allow_private=True zum Erlauben)"
            )
    return host, ips


# ---------------------------------------------------------------------------
# WebScraper
# ---------------------------------------------------------------------------

class WebScraper:
    """Konfigurierbarer Web-Scraper. Methoden geben je ein dict zurück."""

    def __init__(
        self,
        timeout: int = DEFAULT_TIMEOUT,
        user_agent: str = DEFAULT_USER_AGENT,
        max_bytes: int = DEFAULT_MAX_BYTES,
        verify_ssl: bool = True,
        allow_private: bool = False,
        max_redirects: int = DEFAULT_MAX_REDIRECTS,
    ) -> None:
        self.timeout = timeout
        self.user_agent = user_agent
        self.max_bytes = max_bytes
        self.verify_ssl = verify_ssl
        self.allow_private = allow_private
        if max_redirects < 0:
            raise ValueError("max_redirects darf nicht negativ sein")
        # Eine Redirect-Grenze ist eine Sicherheitsgrenze: Wer strenger ist als der
        # Standard, muss das durchsetzen koennen. Sonst lockert ein Umstieg auf dieses
        # Modul die Grenze des Aufrufers, ohne dass es jemand bemerkt.
        self.max_redirects = max_redirects

    # -- HTTP ---------------------------------------------------------------

    def _fetch(self, url: str) -> Response:
        """HTTP GET mit DNS-Pinning, per-Hop-SSRF-Guard und begrenztem Redirect-Following.

        Jeder Redirect wird erneut aufgelöst und gegen den SSRF-Schutz geprüft,
        damit eine öffentliche URL nicht auf ein internes Ziel (z. B. Cloud-Metadata,
        127.0.0.1) weiterleiten kann. Die geprüfte IP wird für die Verbindung gepinnt,
        um DNS-Rebinding (TOCTOU) auszuschließen.
        """
        current = url
        for _ in range(self.max_redirects + 1):
            host, resolved_ips = _guard_target(current, self.allow_private)
            self._pinned_addresses = resolved_ips
            try:
                resp, redirect = self._fetch_once(current)
            finally:
                self._pinned_addresses = None
            if redirect is None:
                assert resp is not None
                return resp
            current = urljoin(current, redirect)
        raise FetchError(f"Zu viele Redirects (>{self.max_redirects})")

    def _fetch_from_ip(
        self,
        url: str,
        pinned_ip: str,
    ) -> tuple[Optional[Response], Optional[str]]:
        """Einzelner HTTP-Hop, streng an die vorab geprüfte IP gepinnt."""
        parsed = urlparse(url)
        scheme = parsed.scheme.lower()
        host = (parsed.hostname or "").lower()
        port = parsed.port or (443 if scheme == "https" else 80)

        ssl_context: Optional[ssl.SSLContext] = None
        if scheme == "https":
            if self.verify_ssl:
                ssl_context = ssl.create_default_context()
            else:
                ssl_context = ssl.create_default_context()
                ssl_context.check_hostname = False
                ssl_context.verify_mode = ssl.CERT_NONE

        connection_cls = _PinnedHTTPSConnection if scheme == "https" else _PinnedHTTPConnection
        connection = connection_cls(
            host=host,
            port=port,
            pinned_ip=pinned_ip,
            timeout=self.timeout,
            context=ssl_context if scheme == "https" else None,
        )

        target = parsed.path or "/"
        if parsed.query:
            target += f"?{parsed.query}"
        host_header = host if parsed.port is None else f"{host}:{parsed.port}"
        req_headers = {
            "Host": host_header,
            "User-Agent": self.user_agent,
            "Accept": "*/*",
        }

        try:
            connection.request("GET", target, headers=req_headers)
            resp = connection.getresponse()
            if resp.status in (301, 302, 303, 307, 308):
                location = resp.headers.get("location") or resp.headers.get("Location")
                if location:
                    return None, location
            if resp.status >= 400:
                raise FetchError(f"HTTP {resp.status}: {resp.reason}")

            raw = resp.read(self.max_bytes + 1)
            if len(raw) > self.max_bytes:
                raw = raw[: self.max_bytes]

            hdrs = {k: v for k, v in resp.headers.items()}
            ctype = resp.headers.get("content-type", "")
            charset = resp.headers.get_content_charset() or "utf-8"

            return Response(
                url=url,
                status=resp.status,
                headers=hdrs,
                text=raw.decode(charset, errors="replace"),
                content_type=ctype,
            ), None
        finally:
            connection.close()

    def _fetch_once(
        self,
        url: str,
        pinned_ip: Optional[str] = None,
    ) -> tuple[Optional[Response], Optional[str]]:
        """Ein einzelner HTTP-Hop mit DNS-Pinning OHNE automatisches Redirect-Following.

        Rückgabe: (Response, None) bei finaler Antwort,
                  (None, location) bei einem Redirect.
        """
        addresses = [pinned_ip] if pinned_ip else getattr(self, "_pinned_addresses", None)
        if not addresses:
            _, addresses = _guard_target(url, self.allow_private)

        last_error: Optional[Exception] = None
        for candidate_ip in addresses:
            try:
                return self._fetch_from_ip(url, candidate_ip)
            except (OSError, ssl.SSLError, http.client.HTTPException) as exc:
                last_error = exc
                continue
            except (BlockedTargetError, FetchError):
                raise
        if last_error is not None:
            raise FetchError(f"{type(last_error).__name__}: {last_error}") from last_error
        raise FetchError("Keine validierte Adresse für die Verbindung verfügbar")

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
            # Größenlimit beim Streamen durchsetzen
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
        """HTTP GET. Body wird auf BODY_PREVIEW_CHARS gekürzt."""
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
            if href.startswith(("javascript:", "mailto:", "tel:", "#")):
                continue
            absolute = urljoin(resp.url, href)
            if absolute in seen:
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
        for form_match in re.finditer(r"<form([^>]*)\s*>(.*?)</form>", html, re.DOTALL | re.IGNORECASE):
            attrs = form_match.group(1)
            form_html = form_match.group(2)
            action = re.search(r'action=["\']([^"\']*)["\']', attrs, re.IGNORECASE)
            method = re.search(r'method=["\']([^"\']*)["\']', attrs, re.IGNORECASE)
            fields = []
            for inp in re.finditer(r"<input[^>]+>", form_html, re.IGNORECASE):
                tag = inp.group()
                name = re.search(r'name=["\']([^"\']*)["\']', tag, re.IGNORECASE)
                itype = re.search(r'type=["\']([^"\']*)["\']', tag, re.IGNORECASE)
                fields.append({
                    "tag": "input",
                    "type": itype.group(1) if itype else "text",
                    "name": name.group(1) if name else "",
                })
            for ta in re.finditer(r"<textarea[^>]*>", form_html, re.IGNORECASE):
                tag = ta.group()
                name = re.search(r'name=["\']([^"\']*)["\']', tag, re.IGNORECASE)
                fields.append({
                    "tag": "textarea",
                    "name": name.group(1) if name else "",
                })
            for sel in re.finditer(r"<select[^>]*>", form_html, re.IGNORECASE):
                tag = sel.group()
                name = re.search(r'name=["\']([^"\']*)["\']', tag, re.IGNORECASE)
                fields.append({
                    "tag": "select",
                    "name": name.group(1) if name else "",
                })
            forms.append({
                "action": action.group(1) if action else "",
                "method": (method.group(1).upper() if method else "GET"),
                "fields": fields,
            })
        return forms

    def _extract_content(self, html: str, url: str) -> tuple[str, str, str]:
        """Gibt (text, method, format) zurück."""
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
            f"Content-Type: {data['content_type']}\nGröße: {data['length']} Zeichen\n"
            + "=" * 40 + "\n\n"
        )
        body = data["body"]
        if data.get("truncated"):
            body += f"\n\n... (gekürzt auf {BODY_PREVIEW_CHARS} Zeichen)"
        return head + body
    if op == "headers":
        lines = [f"Headers für {data['url']}", f"Status: {data['status']}", "=" * 40]
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
    parser.add_argument("--no-verify-ssl", action="store_true", help="SSL-Zertifikat nicht prüfen")
    parser.add_argument(
        "--allow-private", action="store_true",
        help="Interne/private Zieladressen erlauben (SSRF-Schutz aus)",
    )
    parser.add_argument("--out", help="Ausgabedatei für screenshot")
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
