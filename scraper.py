from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse, urlunparse
from collections import deque
import logging


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class WebsiteCrawler:

    STRIP_TAGS = ["script", "style", "nav", "footer", "header", "aside"]
    CONTENT_TAGS = ["p", "li", "h1", "h2", "h3", "article", "main"]

    def __init__(self, url: str, max_pages: int = 20):
        self.start_url = self.normalize(url)

        self.domain = self._clean_domain(self.start_url)

        self.max_pages = max_pages

        self.visited = set()
        self.queue = deque([self.start_url])

        self.docs = []


    def normalize(self, url: str) -> str:
        url = url.strip()

        if not url.startswith(("http://", "https://")):
            url = "http://" + url

        parsed = urlparse(url)

        netloc = parsed.netloc.lower().replace("www.", "")

        path = parsed.path.rstrip("/") or "/"

        return urlunparse(
            parsed._replace(
                scheme=parsed.scheme.lower(),
                netloc=netloc,
                path=path,
                query="",
                fragment=""
            )
        )

    def _clean_domain(self, url: str) -> str:
        return urlparse(url).netloc.lower().replace("www.", "")
    
    def is_valid(self, url: str) -> bool:
        try:
            p = urlparse(url)
            return (
                p.scheme in ["http", "https"]
                and bool(p.netloc)
                and self._clean_domain(url) == self.domain
            )
        except:
            return False
    def extract(self, soup: BeautifulSoup) -> str:
        for tag in soup(self.STRIP_TAGS):
            tag.decompose()

        texts = []
        for tag in soup.find_all(self.CONTENT_TAGS):
            text = tag.get_text(" ", strip=True)
            if len(text) > 50:
                texts.append(text)

        return "\n".join(texts)

    def crawl(self):
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            ctx = browser.new_context()

            while self.queue and len(self.visited) < self.max_pages:
                url = self.queue.popleft()

                # skip duplicates
                if url in self.visited:
                    continue

                self.visited.add(url)

                logger.info(f"Crawling: {url}")

                page = ctx.new_page()

                try:
                    page.goto(url, timeout=30000)
                    html = page.content()
                except Exception as e:
                    logger.warning(f"Failed: {url} | {e}")
                    continue
                finally:
                    page.close()

                soup = BeautifulSoup(html, "html.parser")
                text = self.extract(soup)

                if len(text) > 200:
                    self.docs.append({
                        "url": url,
                        "content": text
                    })

                # discover links
                for a in soup.find_all("a", href=True):
                    link = self.normalize(urljoin(url, a["href"]))

                    if self.is_valid(link) and link not in self.visited:
                        self.queue.append(link)

            browser.close()

        return self.docs