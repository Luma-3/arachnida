import requests
from urllib.parse import urljoin, urlparse
import os
from html.parser import HTMLParser
import threading
from queue import Queue
import hashlib
import logging
import time
import random
from tqdm import tqdm


headers = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:140.0) Gecko/20100101 Firefox/140.0",
    "Connection": "keep-alive",
}


class Parser(HTMLParser):
    SUPPORTED_IMG_EXT = [".jpg", ".jpeg", ".png", ".gif", ".bmp"]

    def __init__(self, current_url):
        super().__init__()
        self.current_url = current_url
        self.link = []
        self.img = []

    def _normalize_link(self, link: str) -> str:
        parsed = urlparse(link)
        link_no_fragment = parsed._replace(fragment="")
        link_no_query = link_no_fragment._replace(query="")
        return link_no_query.geturl()

    def _handle_img(self, name: str, value: str):
        if not name == "src":
            return
        link_parsed = urlparse(value)
        ext = os.path.splitext(link_parsed.path)[1].lower()

        if ext not in self.SUPPORTED_IMG_EXT:
            return

        link_cleaned = self._normalize_link(value)
        url = urljoin(self.current_url, link_cleaned)
        self.img.append(url)

    def handle_starttag(self, tag, attrs: list[tuple[str, str]]):
        if tag == "a":
            for name, value in attrs:
                if name == "href" and not value.startswith("#"):
                    url = urljoin(self.current_url, value)
                    self.link.append(url)
        elif tag == "img":
            for name, value in attrs:
                self._handle_img(name, value)


class Spider:
    def __init__(
        self,
        startUrl: str,
        depth: int,
        recursive: bool,
        path: str,
        num_threads: int,
    ):
        self.recursive = recursive
        self.depth = depth
        self.startUrl = startUrl
        self.path = path

        # Utility Set
        self.visited_pages = set()
        self.found_images = set()

        # Threading
        self.num_threads = num_threads
        self.queue = Queue()
        self.dl_queue = Queue()
        self.lock = threading.Lock()

        self.download_pbar = None

        # Statistics
        self.failures = 0
        self.pages_crawled = 0
        self.total_downloaded = 0
        self.fetch_failures = 0

        # Setup logging

        logging.basicConfig(
            filename="spider.log",
            filemode="w",
            level=logging.INFO,
            format="%(asctime)s - %(levelname)s - %(message)s",
        )

        self.logger = logging.getLogger("SpiderLogger")

        # Configure HTTP adapter with connection pooling
        self.session = requests.Session()
        self.session.headers.update(headers)

        adpter = requests.adapters.HTTPAdapter(
            pool_connections=100,
            pool_maxsize=100,
            max_retries=3,
        )

        self.session.mount("http://", adpter)
        self.session.mount("https://", adpter)

    # =================== DOWNLOAD WORKER ==================#

    def download_stream(self, url, path):
        with self.session.get(url, timeout=5, headers=headers) as r:
            r.raise_for_status()
            with open(path, "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)

    def get_img_names(self, url):
        parsed = urlparse(url)
        ext = os.path.splitext(parsed.path)[1]
        hash_name = hashlib.sha1(url.encode()).hexdigest()
        base_name = f"{hash_name}{ext}"
        return base_name

    def dl_image(self, url):
        self.total_downloaded += 1

        try:
            base_name = self.get_img_names(url)
            self.download_stream(url=url, path=os.path.join(self.path, base_name))
        except Exception:
            self.failures += 1

    def dowload_worker(self):
        while True:
            try:
                url = self.dl_queue.get(timeout=3)
            except Exception:
                return

            self.dl_image(url)
            if self.download_pbar:
                self.download_pbar.update(1)
            self.dl_queue.task_done()

    def start_download(self):
        if not os.path.exists(self.path):
            os.makedirs(self.path)

        for img_url in self.found_images:
            self.dl_queue.put(img_url)

        self.download_pbar = tqdm(
            total=len(self.found_images), desc="Downloading Images", unit="img"
        )
        self.dl_threads = []

        for _ in range(self.num_threads):
            t = threading.Thread(target=self.dowload_worker)
            t.daemon = True
            t.start()
            self.dl_threads.append(t)

        self.dl_queue.join()
        for t in self.dl_threads:
            t.join()

        self.download_pbar.close()

    # =================== CRAWLER WORKER ==================#

    def crawl_worker(self):
        while True:
            try:
                url, depth = self.queue.get(timeout=3)
            except Exception:
                return

            if depth >= 0:
                self.process_page(url, depth)

            self.queue.task_done()

    def fetch(self, url):
        try:
            resp = self.session.get(url, timeout=5)
            resp.raise_for_status()
            return resp
        except Exception as e:
            self.logger.error(f"Failed to fetch {url}: {e}")
        return None

    def process_page(self, url, depth):
        content = self.fetch(url)
        if content is None:
            with self.lock:
                self.fetch_failures += 1
            return

        content_type = content.headers.get("Content-Type", "")
        if not content_type.startswith("text/html"):
            return

        with self.lock:
            self.pages_crawled += 1

        try:
            parser = Parser(url)
            parser.feed(content.text)
        except Exception as e:
            self.logger.error(f"Failed to parse {url}: {e}")
            return

        with self.lock:
            self.pages_crawled += 1
            self.found_images.update(parser.img)

        next_depth = depth - 1
        if next_depth < 0 or not self.recursive:
            return

        for link in parser.link:
            with self.lock:
                if link in self.visited_pages:
                    continue
                self.visited_pages.add(link)

            self.queue.put((link, next_depth))

    def _display_crawl_status(self, stop_event):
        while not stop_event.is_set():
            print(
                f"Pages explorées: {self.pages_crawled} | Images trouvées: {len(self.found_images)}",
                end="\r",
            )
            time.sleep(0.1)
        print()

    def start_crawl(self):
        self.logger.info(f"Starting crawl form {self.startUrl}(depth={self.depth})")
        print(f"Crawling started from {self.startUrl} with depth {self.depth}")

        self.visited_pages.add(self.startUrl)
        self.queue.put((self.startUrl, self.depth))

        stop_display_event = threading.Event()
        display_thread = threading.Thread(
            target=self._display_crawl_status, args=(stop_display_event,)
        )
        display_thread.daemon = True
        display_thread.start()

        self.threads = []

        for _ in range(self.num_threads):
            t = threading.Thread(target=self.crawl_worker)
            t.daemon = True
            t.start()
            self.threads.append(t)

        self.queue.join()
        for t in self.threads:
            t.join()

        stop_display_event.set()
        display_thread.join()

        self.logger.info(
            f"Crawling finished: {self.pages_crawled} pages, {len(self.found_images)} unique images found."
        )

        print(f"""\
Crawling finished.
Pages crawled: {self.pages_crawled}
Unique images found: {len(self.found_images)}
""")

    # =================== SPIDER CONTROL ==================#

    def start(self):
        self.start_crawl()

        if len(self.found_images) == 0:
            print("No images found to download.")
            return

        print("Do you want to download the images? (y/n): ", end="")
        choice = input().strip().lower()
        if choice != "y":
            print("Download cancelled.")
            return
        print("Starting image download...")
        self.start_download()
        print(
            f"Download finished. Total images downloaded: {self.total_downloaded}, Failures: {self.failures}"
        )
