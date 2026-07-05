# -*- coding: utf-8 -*-
"""Offline-Tests fuer web_scraper (kein Netzwerk noetig).

Getestet werden das Parsing (Links/Formulare/Extraktion) und der SSRF-Schutz.
Der eigentliche HTTP-Abruf wird nicht live getestet (waere flaky).
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from web_scraper.core import (  # noqa: E402
    WebScraper,
    BlockedTargetError,
    FetchError,
    _guard_target,
    _is_blocked_ip,
)

SAMPLE_HTML = """
<html><head><title>Test</title><style>.x{}</style></head>
<body>
  <nav>Navigation ueberspringen</nav>
  <h1>Ueberschrift</h1>
  <p>Ein Absatz mit echtem Inhalt und Umlauten: aeoeue.</p>
  <a href="/relativ">Relativer Link</a>
  <a href="https://example.org/abs">Absoluter Link</a>
  <a href="mailto:x@y.z">Mail</a>
  <a href="javascript:void(0)">JS</a>
  <form action="/submit" method="post">
    <input type="text" name="user">
    <input type="password" name="pw">
    <textarea name="comment"></textarea>
    <select name="choice"></select>
  </form>
  <footer>Fusszeile</footer>
</body></html>
"""


@pytest.fixture
def scraper():
    return WebScraper()


def test_parse_links_finds_and_filters(scraper):
    pairs = scraper._parse_links(SAMPLE_HTML)
    hrefs = [h for h, _ in pairs]
    assert "/relativ" in hrefs
    assert "https://example.org/abs" in hrefs


def test_links_dedup_absolutizes_and_skips_schemes(scraper):
    # links() ruft _fetch; wir testen die Nachverarbeitung ueber _parse_links + urljoin
    from urllib.parse import urljoin
    base = "https://example.com/page"
    pairs = scraper._parse_links(SAMPLE_HTML)
    absolute = {urljoin(base, h) for h, _ in pairs
                if not h.startswith(("javascript:", "mailto:", "tel:", "#"))}
    assert "https://example.com/relativ" in absolute
    assert "https://example.org/abs" in absolute
    assert not any(a.startswith(("javascript:", "mailto:")) for a in absolute)


def test_parse_forms(scraper):
    forms = scraper._parse_forms(SAMPLE_HTML)
    assert len(forms) == 1
    form = forms[0]
    assert form["action"] == "/submit"
    assert form["method"] == "POST"
    names = {f["name"] for f in form["fields"]}
    assert {"user", "pw", "comment", "choice"} <= names


def test_extract_content_returns_text(scraper):
    text, method, fmt = scraper._extract_content(SAMPLE_HTML, "https://example.com")
    assert "Inhalt" in text
    assert method in ("trafilatura", "beautifulsoup", "regex")
    # Boilerplate (Navigation/Fusszeile) sollte bei bs4/trafilatura raus sein;
    # beim reinen Regex-Fallback bleibt sie ggf. drin -> nur bei bs4/trafilatura pruefen.
    if method in ("beautifulsoup", "trafilatura"):
        assert "Navigation ueberspringen" not in text


# -- SSRF-Schutz -----------------------------------------------------------

def test_guard_blocks_loopback():
    with pytest.raises(BlockedTargetError):
        _guard_target("http://127.0.0.1/", allow_private=False)


def test_guard_blocks_localhost_name():
    with pytest.raises(BlockedTargetError):
        _guard_target("http://localhost/", allow_private=False)


def test_guard_blocks_private_range():
    with pytest.raises(BlockedTargetError):
        _guard_target("http://10.0.0.5/", allow_private=False)


def test_guard_blocks_link_local():
    with pytest.raises(BlockedTargetError):
        _guard_target("http://169.254.10.10/", allow_private=False)


def test_guard_blocks_non_http_scheme():
    with pytest.raises(BlockedTargetError):
        _guard_target("ftp://example.com/", allow_private=False)


def test_guard_allows_public_ip():
    # 8.8.8.8 ist oeffentlich -> kein Fehler (IP-Literal, kein echtes DNS noetig)
    _guard_target("http://8.8.8.8/", allow_private=False)


def test_guard_allow_private_bypass():
    _guard_target("http://127.0.0.1/", allow_private=True)


def test_is_blocked_ip():
    assert _is_blocked_ip("127.0.0.1")
    assert _is_blocked_ip("10.1.2.3")
    assert _is_blocked_ip("192.168.1.1")
    assert _is_blocked_ip("169.254.1.1")
    assert not _is_blocked_ip("8.8.8.8")
    assert not _is_blocked_ip("1.1.1.1")


# -- Redirect-SSRF (per-Hop-Guard) -----------------------------------------

def test_fetch_redirect_to_internal_is_blocked(scraper):
    # Start ist eine oeffentliche IP (Guard ok); der Redirect zeigt auf eine
    # link-local Adresse -> der zweite Hop MUSS geblockt werden.
    scraper._fetch_once = lambda url: (None, 'http://169.254.169.254/')
    with pytest.raises(BlockedTargetError):
        scraper._fetch('http://8.8.8.8/')


def test_fetch_redirect_cap(scraper):
    # Endlose (oeffentliche) Redirects muessen nach dem Limit abbrechen.
    scraper._fetch_once = lambda url: (None, 'http://8.8.8.8/')
    with pytest.raises(FetchError):
        scraper._fetch('http://8.8.8.8/')
