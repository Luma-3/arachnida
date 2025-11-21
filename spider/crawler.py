import requests
from urllib.parse import urljoin, urlparse
import os
from html.parser import HTMLParser
import threading
from tqdm import tqdm
from queue import Queue
import hashlib

headers = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:140.0) Gecko/20100101 Firefox/140.0",
    "Connection": "keep-alive",
}


def get_page(current_url):
    r = requests.get(url=current_url, timeout=5, headers=headers, stream=True)
    r.raise_for_status()
    return r


class Parser(HTMLParser):
    def __init__(self, current_url):
        super().__init__()
        self.current_url = current_url
        self.link = []
        self.img = []

    def _handle_img(self, name: str, value: str):
        if name == "src":
            link_parsed = urlparse(value)
            if not link_parsed.path.endswith((".jpg", ".jpeg", ".png", ".gif", ".bmp")):
                return
            url = urljoin(self.current_url, value)
            self.img.append(url)

    def handle_starttag(self, tag, attrs: list[tuple[str, str]]):
        match tag:
            case "a":
                for name, value in attrs:
                    if name == "href" and not value.startswith("#"):
                        url = urljoin(self.current_url, value)
                        self.link.append(url)
            case "img":
                for (
                    name,
                    value,
                ) in attrs:
                    self._handle_img(name, value)


class Spider:
    def __init__(
        self,
        startUrl: str,
        depth: int,
        recursive: bool,
        path: str,
    ):
        self.recursive = recursive
        self.depth = depth
        self.startUrl = startUrl
        self.path = path

        self.visited = set()
        self.dl_img = set()

        self.lock = threading.Lock()
        self.lock_dl = threading.Lock()

        self.queue = Queue()
        self.threads = []

        self.total_downloaded = 0
        self.progess_bar = tqdm(total=0, unit="img", desc="Downloaded Images")

        self.failures = 0

    def download_stream(self, url, path):
        with requests.get(url, timeout=5, headers=headers, stream=True) as r:
            r.raise_for_status()
            with open(path, "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)

    def dl_all_image(self, urls: list[str]):
        for url in urls:
            with self.lock_dl:
                if url in self.dl_img:
                    continue
                self.dl_img.add(url)

            self.total_downloaded += 1
            self.progess_bar.total = self.total_downloaded
            self.progess_bar.refresh()

            try:
                parsed = urlparse(url)
                ext = os.path.splitext(parsed.path)[1]
                hash_name = hashlib.sha1(url.encode()).hexdigest()
                base_name = f"{hash_name}{ext}"
                self.download_stream(url=url, path=os.path.join(self.path, base_name))
                self.progess_bar.update(1)
            except Exception:
                self.failures += 1

    def worker(self):
        while True:
            try:
                url, depth = self.queue.get(timeout=3)
            except Exception:
                return

            if depth >= 0:
                self.process_page(url, depth)

            self.queue.task_done()

    def process_page(self, url, depth):
        try:
            content = get_page(url)
        except Exception:
            return

        content_type = content.headers.get("Content-Type", "")
        if not content_type.startswith("text/html"):
            return

        try:
            parser = Parser(url)
            parser.feed(content.text)
        except Exception:
            return

        self.dl_all_image(parser.img)

        next_depth = depth - 1
        if next_depth < 0:
            return
        for link in parser.link:
            with self.lock:
                if link in self.visited:
                    continue
                self.visited.add(link)

            if self.recursive:
                self.queue.put((link, next_depth))

    def start(self):
        self.visited.add(self.startUrl)
        self.queue.put((self.startUrl, self.depth))

        self.threads = []
        for _ in range(20):
            t = threading.Thread(target=self.worker)
            t.daemon = True
            t.start()
            self.threads.append(t)

    def wait(self):
        self.queue.join()
        for t in self.threads:
            t.join()
        self.progess_bar.close()
        print(
            f"Finished with {self.total_downloaded} images downloaded, {self.failures} failures."
        )
        print("Spider finished.")
