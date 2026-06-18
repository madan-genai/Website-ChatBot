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
        self.domain = urlparse(self.start_url).netloc
        self.max_pages = max_pages

        self.visited = set()
        self.queue = deque([self.start_url])

        self.docs = []

    def normalize(self, url):
        p = urlparse(url)
        path = p.path.rstrip("/") or "/"
        return urlunparse(p._replace(path=path, query="", fragment=""))

    def is_valid(self, url):
        p = urlparse(url)
        return p.scheme in ["http", "https"] and p.netloc == self.domain

    def extract(self, soup):
        for t in soup(self.STRIP_TAGS):
            t.decompose()

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
                if url in self.visited:
                    continue

                self.visited.add(url)

                page = ctx.new_page()
                try:
                    page.goto(url, timeout=30000)
                    html = page.content()
                except:
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

                for a in soup.find_all("a", href=True):
                    link = self.normalize(urljoin(url, a["href"]))
                    if self.is_valid(link) and link not in self.visited:
                        self.queue.append(link)

            browser.close()

        return self.docs