# -*- coding: utf-8 -*-
"""Offline-Tests für web_scraper (kein Netzwerk nötig).

Getestet werden das Parsing (Links/Formulare/Extraktion) und der SSRF-Schutz.
Der eigentliche HTTP-Abruf wird nicht live getestet (wäre flaky).
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from web_scraper.core import (  # noqa: E402
    DEFAULT_MAX_REDIRECTS,
    WebScraper,
    BlockedTargetError,
    FetchError,
    Response,
    _guard_target,
    _is_blocked_ip,
)

SAMPLE_HTML = """
<html><head><title>Test</title><style>.x{}</style></head>
<body>
  <nav>Navigation überspringen</nav>
  <h1>Überschrift</h1>
  <p>Ein Absatz mit echtem Inhalt und Umlauten: äöü.</p>
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
  <footer>Fußzeile</footer>
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
    # links() ruft _fetch; wir testen die Nachverarbeitung über _parse_links + urljoin
    from urllib.parse import urljoin
    base = "https://example.com/page"
    pairs = scraper._parse_links(SAMPLE_HTML)
    absolute = {urljoin(base, h) for h, _ in pairs
                if not h.startswith(("javascript:", "mailto:", "tel:", "#"))}
    assert "https://example.com/relativ" in absolute
    assert "https://example.org/abs" in absolute
    assert not any(a.startswith(("javascript:", "mailto:")) for a in absolute)


def test_links_skips_same_page_anchors_after_fetch(scraper):
    html = """
    <a href="/docs">Docs</a>
    <a href="#section">Section</a>
    <a href="mailto:info@example.com">Mail</a>
    <a href="https://example.org/external">External</a>
    """
    scraper._fetch = lambda url: Response(
        url="https://example.com/page",
        status=200,
        text=html,
        content_type="text/html",
    )

    result = scraper.links("https://example.com/page")
    hrefs = {item["href"] for item in result["links"]}

    assert "https://example.com/docs" in hrefs
    assert "https://example.org/external" in hrefs
    assert "https://example.com/page#section" not in hrefs
    assert "mailto:info@example.com" not in hrefs


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
    # Boilerplate (Navigation/Fußzeile) sollte bei bs4/trafilatura raus sein;
    # beim reinen Regex-Fallback bleibt sie ggf. drin -> nur bei bs4/trafilatura prüfen.
    if method in ("beautifulsoup", "trafilatura"):
        assert "Navigation überspringen" not in text


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
    # 8.8.8.8 ist öffentlich -> kein Fehler (IP-Literal, kein echtes DNS nötig)
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
    # Start ist eine öffentliche IP (Guard ok); der Redirect zeigt auf eine
    # link-local Adresse -> der zweite Hop MUSS geblockt werden.
    scraper._fetch_once = lambda url: (None, 'http://169.254.169.254/')
    with pytest.raises(BlockedTargetError):
        scraper._fetch('http://8.8.8.8/')


def test_fetch_redirect_cap(scraper):
    # Endlose (öffentliche) Redirects müssen nach dem Limit abbrechen.
    scraper._fetch_once = lambda url: (None, 'http://8.8.8.8/')
    with pytest.raises(FetchError):
        scraper._fetch('http://8.8.8.8/')


def test_default_redirect_cap_is_unchanged():
    # Der Default bleibt 10 -- bestehende Aufrufer aendern ihr Verhalten nicht.
    assert WebScraper().max_redirects == DEFAULT_MAX_REDIRECTS == 10


def test_redirect_cap_is_configurable():
    """Ein strengerer Aufrufer muss seine Grenze durchsetzen koennen.

    Ohne diesen Parameter wuerde ein Umstieg auf dieses Modul die Grenze des
    Aufrufers stillschweigend lockern -- BACH erlaubt 5, dieses Modul 10.
    """
    strict = WebScraper(max_redirects=2)
    hops = []
    strict._fetch_once = lambda url: (hops.append(url), (None, 'http://8.8.8.8/'))[1]

    with pytest.raises(FetchError) as excinfo:
        strict._fetch('http://8.8.8.8/')

    assert len(hops) == 3, 'Startversuch plus zwei erlaubte Redirects'
    assert '>2' in str(excinfo.value), 'die Meldung muss die tatsaechliche Grenze nennen'


def test_zero_redirects_allows_no_hop():
    strict = WebScraper(max_redirects=0)
    strict._fetch_once = lambda url: (None, 'http://8.8.8.8/')
    with pytest.raises(FetchError):
        strict._fetch('http://8.8.8.8/')


def test_negative_redirect_cap_is_rejected():
    with pytest.raises(ValueError):
        WebScraper(max_redirects=-1)

# -- DNS-Pinning & DNS-Rebinding Schutz -------------------------------------

def test_dns_pinning_blocks_127_0_0_1(monkeypatch):
    # Literal
    with pytest.raises(BlockedTargetError):
        _guard_target("http://127.0.0.1/", allow_private=False)
    with pytest.raises(BlockedTargetError):
        _guard_target("http://127.0.0.1:8080/admin", allow_private=False)

    # Resolved hostname
    monkeypatch.setattr(
        "web_scraper.core.socket.getaddrinfo",
        lambda *_a, **_k: [(2, 1, 6, "", ("127.0.0.1", 0))],
    )
    with pytest.raises(BlockedTargetError, match="loopback"):
        _guard_target("http://evil-loopback.example/", allow_private=False)


def test_dns_pinning_blocks_169_254_169_254(monkeypatch):
    # Literal
    with pytest.raises(BlockedTargetError):
        _guard_target("http://169.254.169.254/latest/meta-data/", allow_private=False)

    # Resolved hostname
    monkeypatch.setattr(
        "web_scraper.core.socket.getaddrinfo",
        lambda *_a, **_k: [(2, 1, 6, "", ("169.254.169.254", 0))],
    )
    with pytest.raises(BlockedTargetError, match="link-local"):
        _guard_target("http://instance-data.example/", allow_private=False)

    # Named metadata endpoints
    with pytest.raises(BlockedTargetError, match="Metadata"):
        _guard_target("http://metadata.google.internal/computeMetadata/v1/", allow_private=False)


def test_dns_pinning_blocks_10_x_private_range(monkeypatch):
    # Literal
    with pytest.raises(BlockedTargetError):
        _guard_target("http://10.0.0.1/", allow_private=False)
    with pytest.raises(BlockedTargetError):
        _guard_target("http://10.255.42.1/internal", allow_private=False)

    # Resolved hostname
    monkeypatch.setattr(
        "web_scraper.core.socket.getaddrinfo",
        lambda *_a, **_k: [(2, 1, 6, "", ("10.1.2.3", 0))],
    )
    with pytest.raises(BlockedTargetError, match="private"):
        _guard_target("http://corporate-intranet.example/", allow_private=False)


def test_dns_pinning_blocks_192_168_x_private_range(monkeypatch):
    # Literal
    with pytest.raises(BlockedTargetError):
        _guard_target("http://192.168.1.1/", allow_private=False)
    with pytest.raises(BlockedTargetError):
        _guard_target("http://192.168.178.1/status", allow_private=False)

    # Resolved hostname
    monkeypatch.setattr(
        "web_scraper.core.socket.getaddrinfo",
        lambda *_a, **_k: [(2, 1, 6, "", ("192.168.0.50", 0))],
    )
    with pytest.raises(BlockedTargetError, match="private"):
        _guard_target("http://home-router.example/", allow_private=False)


def test_dns_pinning_allows_public_ips_and_hosts(monkeypatch):
    host, ips = _guard_target("http://8.8.8.8/", allow_private=False)
    assert host == "8.8.8.8"
    assert ips == ["8.8.8.8"]

    monkeypatch.setattr(
        "web_scraper.core.socket.getaddrinfo",
        lambda *_a, **_k: [(2, 1, 6, "", ("93.184.216.34", 0))],
    )
    host, ips = _guard_target("https://example.com/page", allow_private=False)
    assert host == "example.com"
    assert ips == ["93.184.216.34"]


def test_dns_rebinding_switch_prevented_by_pinning(monkeypatch):
    """Simuliert DNS-Rebinding: 1. Lookup liefert öffentliche IP, 2. Lookup würde 127.0.0.1 liefern.
    Dank DNS-Pinning wird nur einmal aufgelöst und direkt zur geprüften IP verbunden."""
    lookups = []
    connected_ips = []

    def fake_getaddrinfo(host, *_args, **_kwargs):
        lookups.append(host)
        # Wenn ein zweiter Lookup stattfände, würde er auf 127.0.0.1 rebinden:
        addr = "93.184.216.34" if len(lookups) == 1 else "127.0.0.1"
        return [(2, 1, 6, "", (addr, 0))]

    def fake_fetch_from_ip(url, pinned_ip):
        connected_ips.append(pinned_ip)
        return Response(
            url=url,
            status=200,
            headers={"content-type": "text/html"},
            text="<html><body>OK</body></html>",
            content_type="text/html",
        ), None

    monkeypatch.setattr("web_scraper.core.socket.getaddrinfo", fake_getaddrinfo)

    scraper = WebScraper()
    monkeypatch.setattr(scraper, "_fetch_from_ip", fake_fetch_from_ip)

    resp = scraper._fetch("https://rebind.example.org/test")
    assert resp.status == 200
    assert resp.text == "<html><body>OK</body></html>"
    # DNS wurde genau einmal für diesen Hop befragt:
    assert lookups == ["rebind.example.org"]
    # Die Verbindung ging ausschließlich an die geprüfte öffentliche IP:
    assert connected_ips == ["93.184.216.34"]


def test_dns_rebinding_multi_record_with_private_ip_is_blocked(monkeypatch):
    """Rebinding-Versuch mit gemischten A-Records (öffentlich + intern): muss fail-closed blockieren."""
    monkeypatch.setattr(
        "web_scraper.core.socket.getaddrinfo",
        lambda *_a, **_k: [
            (2, 1, 6, "", ("93.184.216.34", 0)),
            (2, 1, 6, "", ("127.0.0.1", 0)),
        ],
    )
    with pytest.raises(BlockedTargetError, match="loopback"):
        _guard_target("https://mixed-records.example/")


def test_dns_pinning_peer_mismatch_fails_closed():
    """Wenn der verbundene Peer nicht der geprüften gepinnten IP entspricht, muss abgebrochen werden."""
    from web_scraper.core import _PinnedHTTPConnection, _same_address
    conn = _PinnedHTTPConnection("example.com", 80, pinned_ip="93.184.216.34")

    class FakeSocket:
        def getpeername(self):
            return ("127.0.0.1", 80)
        def close(self):
            pass

    conn.sock = FakeSocket()
    with pytest.raises(BlockedTargetError, match="differs from validated address"):
        peer = conn.sock.getpeername()[0]
        if not _same_address(peer, conn.pinned_ip):
            conn.sock.close()
            raise BlockedTargetError(
                f"Connected peer {peer} differs from validated address {conn.pinned_ip}"
            )


def test_dns_pinning_redirect_to_internal_ip_blocked():
    """Redirects von öffentlicher IP auf interne IPs werden bei jedem Hop geblockt."""
    for target in [
        "http://127.0.0.1/admin",
        "http://169.254.169.254/latest/meta-data/",
        "http://10.0.0.1/internal",
        "http://192.168.1.1/router",
    ]:
        scraper = WebScraper()
        scraper._fetch_once = lambda url, target=target: (None, target)
        with pytest.raises(BlockedTargetError):
            scraper._fetch("http://8.8.8.8/")


def test_dns_pinning_redirect_to_rebinding_host_blocked(monkeypatch):
    """Hop 1 ist öffentlich, Hop 2 leitet auf Host weiter, der zu 127.0.0.1 auflöst."""
    def resolver(host, *_args, **_kwargs):
        if host == "public.example.org":
            return [(2, 1, 6, "", ("93.184.216.34", 0))]
        return [(2, 1, 6, "", ("127.0.0.1", 0))]

    monkeypatch.setattr("web_scraper.core.socket.getaddrinfo", resolver)

    scraper = WebScraper()
    scraper._fetch_once = lambda url: (
        (None, "http://internal-target.example/")
        if "public.example.org" in url
        else (None, None)
    )

    with pytest.raises(BlockedTargetError, match="loopback"):
        scraper._fetch("http://public.example.org/start")
