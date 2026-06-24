import io
import time
import logging
import requests as http_requests

from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse, urlunparse
from collections import deque

# PDF extraction
try:
    import pdfplumber
    PDF_SUPPORT = True
except ImportError:
    PDF_SUPPORT = False

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class WebsiteCrawler:
    STRIP_TAGS   = ["script", "style", "nav", "footer", "header", "aside"]
    CONTENT_TAGS = ["p", "li", "h1", "h2", "h3", "article", "main", "section"]

    def __init__(self, url, max_pages: int = 20):
        self.start_url = self.normalize(url)
        self.domain    = self._clean_domain(self.start_url)
        self.max_pages = max_pages
        self.visited   = set()
        self.queue     = deque([self.start_url])
        self.docs      = []

    # ── Normalization ──────────────────────────────────────────────────────
    def normalize(self, url) -> str:
        url = str(url).strip()
        if not url.startswith(("http://", "https://")):
            url = "http://" + url
        parsed = urlparse(url)
        netloc = parsed.netloc.lower().replace("www.", "")
        path   = parsed.path.rstrip("/") or "/"
        cleaned = parsed._replace(
            scheme=parsed.scheme.lower(),
            netloc=netloc,
            path=path,
            query="",
            fragment=""
        )
        return urlunparse(cleaned)

    def _clean_domain(self, url: str) -> str:
        return urlparse(url).netloc.lower().replace("www.", "")

    def is_valid(self, url: str) -> bool:
        try:
            p      = urlparse(url)
            domain = p.netloc.lower().replace("www.", "")
            return (
                p.scheme in ["http", "https"]
                and bool(p.netloc)
                and domain == self.domain
            )
        except Exception:
            return False

    # ── HTML extraction ────────────────────────────────────────────────────
    def extract_html(self, soup: BeautifulSoup) -> str:
        for tag in soup(self.STRIP_TAGS):
            tag.decompose()
        texts = []
        for tag in soup.find_all(self.CONTENT_TAGS):
            text = tag.get_text(" ", strip=True)
            if text and len(text) > 30:
                texts.append(text)
        return "\n".join(texts)

    # ── PDF extraction ─────────────────────────────────────────────────────
    def extract_pdf(self, url: str) -> str | None:
        if not PDF_SUPPORT:
            logger.warning("pdfplumber not installed — skipping PDF")
            return None
        try:
            resp = http_requests.get(url, timeout=20)
            resp.raise_for_status()
            with pdfplumber.open(io.BytesIO(resp.content)) as pdf:
                pages_text = []
                for page in pdf.pages:
                    t = page.extract_text()
                    if t:
                        pages_text.append(t.strip())
            text = "\n".join(pages_text)
            logger.info(f"PDF extracted: {url} ({len(text)} chars)")
            return text[:8000]
        except Exception as e:
            logger.warning(f"PDF extraction failed [{url}]: {e}")
            return None

    # ── Sitemap parsing ────────────────────────────────────────────────────
    def fetch_sitemap_urls(self) -> list[str]:
        candidates = [
            self.start_url.rstrip("/") + "/sitemap.xml",
            self.start_url.rstrip("/") + "/sitemap_index.xml",
            self.start_url.rstrip("/") + "/robots.txt",
        ]
        found_urls = []

        for candidate in candidates:
            try:
                resp = http_requests.get(candidate, timeout=10)
                if resp.status_code != 200:
                    continue

                if "robots.txt" in candidate:
                    # Parse Sitemap: lines from robots.txt
                    for line in resp.text.splitlines():
                        if line.lower().startswith("sitemap:"):
                            sitemap_url = line.split(":", 1)[1].strip()
                            found_urls += self._parse_sitemap(sitemap_url)
                else:
                    found_urls += self._parse_sitemap(candidate)

            except Exception as e:
                logger.debug(f"Sitemap fetch failed [{candidate}]: {e}")

        # Normalize + filter to same domain
        valid = []
        for u in found_urls:
            n = self.normalize(u)
            if self.is_valid(n) and n not in valid:
                valid.append(n)

        logger.info(f"Sitemap URLs found: {len(valid)}")
        return valid

    def _parse_sitemap(self, url: str) -> list[str]:
        try:
            resp = http_requests.get(url, timeout=10)
            soup = BeautifulSoup(resp.content, "xml")
            # sitemap index → recurse
            sitemaps = soup.find_all("sitemap")
            if sitemaps:
                urls = []
                for sm in sitemaps:
                    loc = sm.find("loc")
                    if loc:
                        urls += self._parse_sitemap(loc.text.strip())
                return urls
            # regular sitemap
            return [
                loc.text.strip()
                for loc in soup.find_all("loc")
                if loc.text.strip()
            ]
        except Exception as e:
            logger.debug(f"Sitemap parse failed [{url}]: {e}")
            return []

    # ── Main crawl ─────────────────────────────────────────────────────────
    def crawl(self) -> list[dict]:
        # 1. Seed queue with sitemap URLs
        sitemap_urls = self.fetch_sitemap_urls()
        for u in sitemap_urls:
            if u not in self.visited:
                self.queue.appendleft(u)   # prioritize sitemap links

        # 2. Playwright crawl
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            ctx     = browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0 Safari/537.36"
                )
            )

            while self.queue and len(self.visited) < self.max_pages:
                url = self.queue.popleft()

                if url in self.visited:
                    continue
                self.visited.add(url)

                # ── PDF ──────────────────────────────────────────────────
                if url.lower().endswith(".pdf"):
                    text = self.extract_pdf(url)
                    if text:
                        self.docs.append({"url": url, "content": text, "type": "pdf"})
                    continue

                # ── HTML ─────────────────────────────────────────────────
                logger.info(f"Crawling: {url}")
                page = ctx.new_page()
                try:
                    page.goto(url, timeout=30000, wait_until="domcontentloaded")
                    page.wait_for_load_state("networkidle", timeout=10000)
                    html = page.content()
                except Exception as e:
                    logger.warning(f"Failed: {url} | {e}")
                    continue
                finally:
                    page.close()

                soup = BeautifulSoup(html, "html.parser")
                text = self.extract_html(soup)

                if text.strip():
                    self.docs.append({
                        "url":     url,
                        "content": text[:5000],
                        "type":    "html"
                    })

                # Discover links
                for a in soup.find_all("a", href=True):
                    href = a["href"].strip()

                    # PDF links
                    if href.lower().endswith(".pdf"):
                        full = self.normalize(urljoin(url, href))
                        if full not in self.visited:
                            self.queue.append(full)
                        continue

                    if any(x in href for x in ["#", "mailto:", "tel:", "javascript:"]):
                        continue

                    link = self.normalize(urljoin(url, href))
                    if self.is_valid(link) and link not in self.visited:
                        self.queue.append(link)

                time.sleep(0.2)

            browser.close()

        logger.info(f"Crawl complete: {len(self.docs)} pages, {len(self.visited)} visited")
        return self.docs
