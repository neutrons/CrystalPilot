#!/usr/bin/env python3
"""Crawl ORNL beamline documentation and save as Markdown for CrystalPilot RAG.

This is an **offline utility** — run it manually to refresh the knowledge base.
It crawls ORNL instrument pages (1 level deep), extracts text content, and
writes `.md` files to ``src/exphub/agent/knowledge/crawled/``.

Usage::

    python scripts/crawl_ornl_docs.py

After crawling, delete ``src/exphub/agent/knowledge/chroma_db/`` to force
the RAG system to rebuild its index on next startup.

Adapted from NeuDiff-Agent's web_crawler.py.
"""

from __future__ import annotations

import json
import logging
import re
import time
from pathlib import Path
from urllib.parse import urljoin, urlparse

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

ROOT_URLS = [
    "https://single-crystal.ornl.gov/",
    "https://neutrons.ornl.gov/topaz",
    "https://neutrons.ornl.gov/corelli",
    "https://neutrons.ornl.gov/mandi",
]

OUTPUT_DIR = Path(__file__).parent.parent / "src" / "exphub" / "agent" / "knowledge" / "crawled"
MAX_DEPTH = 1          # only follow links one level deep
CRAWL_DELAY = 0.5      # seconds between requests
MAX_RETRIES = 2
REQUEST_TIMEOUT = 15


# ---------------------------------------------------------------------------
# Crawling
# ---------------------------------------------------------------------------

def _fetch_page(url: str) -> str | None:
    """Fetch a URL and return its HTML content, or None on failure."""
    import requests
    for attempt in range(MAX_RETRIES + 1):
        try:
            resp = requests.get(url, timeout=REQUEST_TIMEOUT,
                                headers={"User-Agent": "CrystalPilot-KnowledgeCrawler/1.0"})
            resp.raise_for_status()
            return resp.text
        except Exception as exc:
            if attempt < MAX_RETRIES:
                time.sleep(1)
            else:
                logger.warning("Failed to fetch %s: %s", url, exc)
                return None
    return None


def _extract_text(html: str) -> str:
    """Extract readable text from HTML, removing scripts and styles."""
    import importlib
    BeautifulSoup = importlib.import_module("bs4").BeautifulSoup
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "nav", "footer", "header"]):
        tag.decompose()
    text = soup.get_text(separator="\n")
    # Collapse multiple blank lines
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _extract_links(html: str, base_url: str) -> list[str]:
    """Extract same-domain links from HTML."""
    import importlib
    BeautifulSoup = importlib.import_module("bs4").BeautifulSoup
    soup = BeautifulSoup(html, "html.parser")
    base_domain = urlparse(base_url).netloc
    links = []
    for a in soup.find_all("a", href=True):
        href = urljoin(base_url, a["href"])
        parsed = urlparse(href)
        # Same domain, no fragments, no file downloads
        if (parsed.netloc == base_domain
                and not parsed.fragment
                and not any(href.endswith(ext) for ext in (".pdf", ".zip", ".gz", ".tar", ".png", ".jpg"))):
            links.append(href.split("#")[0].split("?")[0])
    return list(set(links))


def crawl_site(root_url: str) -> list[dict]:
    """Crawl a site up to MAX_DEPTH and return page records."""
    pages: list[dict] = []
    visited: set[str] = set()

    html = _fetch_page(root_url)
    if not html:
        return pages
    visited.add(root_url)
    text = _extract_text(html)
    pages.append({"url": root_url, "text": text, "depth": 0})
    logger.info("  [depth 0] %s (%d chars)", root_url, len(text))

    if MAX_DEPTH >= 1:
        child_links = _extract_links(html, root_url)
        for link in child_links:
            if link in visited:
                continue
            visited.add(link)
            time.sleep(CRAWL_DELAY)
            child_html = _fetch_page(link)
            if child_html:
                child_text = _extract_text(child_html)
                if len(child_text) > 100:  # skip near-empty pages
                    pages.append({"url": link, "text": child_text, "depth": 1})
                    logger.info("  [depth 1] %s (%d chars)", link, len(child_text))

    return pages


def pages_to_markdown(pages: list[dict], domain: str) -> str:
    """Convert crawled pages into a single Markdown document."""
    parts = [f"# Crawled Documentation: {domain}\n"]
    for page in pages:
        title = urlparse(page["url"]).path.strip("/").replace("/", " > ") or "Home"
        parts.append(f"\n## {title}\n\nSource: {page['url']}\n\n{page['text']}")
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    try:
        import importlib
        importlib.import_module("requests")
        importlib.import_module("bs4")
    except ImportError:
        logger.error("Install dependencies: pip install requests beautifulsoup4")
        return

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    for root_url in ROOT_URLS:
        domain = urlparse(root_url).netloc
        path_slug = urlparse(root_url).path.strip("/").replace("/", "_") or "home"
        filename = f"{domain}_{path_slug}.md"

        logger.info("Crawling %s …", root_url)
        pages = crawl_site(root_url)
        if not pages:
            logger.warning("No pages crawled from %s", root_url)
            continue

        md = pages_to_markdown(pages, domain)
        out_path = OUTPUT_DIR / filename
        out_path.write_text(md, encoding="utf-8")
        logger.info("Wrote %d pages → %s", len(pages), out_path)

    logger.info(
        "\nDone! Delete src/exphub/agent/knowledge/chroma_db/ to force RAG rebuild."
    )


if __name__ == "__main__":
    main()
