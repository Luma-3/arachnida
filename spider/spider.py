import argparse
import os
from crawler import Spider
import multiprocessing


def create_parser():
    parser = argparse.ArgumentParser(
        prog="spider", description="A simple web spider to download images."
    )
    parser.add_argument(
        "url", type=str, help="The starting URL for the spider.")
    parser.add_argument(
        "-r", "--recursive", action="store_true", help="Enable recursive crawling."
    )
    parser.add_argument(
        "-l", "--depth", type=int, default=5, help="Set the maximum crawl depth."
    )
    parser.add_argument(
        "-p",
        "--path",
        type=str,
        default="./data",
        help="Set the download path for images.",
    )

    parser.add_argument(
        "-t",
        "--threads",
        type=int,
        default=min(20, (multiprocessing.cpu_count() * 2) + 1),
        help="Set the number of concurrent threads.",
    )
    return parser


if __name__ == "__main__":
    parser = create_parser()
    args = parser.parse_args()

    os.makedirs(args.path, exist_ok=True)
    print("""\
Starting spider with the following settings:
Start URL: {}
Recursive: {}
Depth: {}
Download Path: {}
Number of Threads: {}
Warning: Program may freeze sometimes due number of links to crawl.
""".format(args.url, args.recursive, args.depth, args.path, args.threads)
          )

    spider = Spider(
        startUrl=args.url,
        depth=args.depth,
        recursive=args.recursive,
        path=args.path,
        num_threads=args.threads,
    )
    spider.start()
