# -*- coding: utf-8 -*-
# SPDX-License-Identifier: MIT
"""web_scraper - Standalone Web-Scraper (portiert aus BACH web_scrape.py).

Beispiel::

    from web_scraper import WebScraper, extract

    scraper = WebScraper(timeout=15)
    print(scraper.get("https://example.com")["status"])
    print(extract("https://example.com")["content"])
"""
from .core import (
    WebScraper,
    Response,
    FetchError,
    BlockedTargetError,
    get,
    links,
    forms,
    headers,
    extract,
    screenshot,
    main,
)

__version__ = "0.1.0"

__all__ = [
    "WebScraper",
    "Response",
    "FetchError",
    "BlockedTargetError",
    "get",
    "links",
    "forms",
    "headers",
    "extract",
    "screenshot",
    "main",
    "__version__",
]
