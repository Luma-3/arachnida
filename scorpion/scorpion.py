from PNGParser import PngReader

# from BMPParser import BmpReader
# from GIFParser import GifReader
from JPGParser import JPGParser

from argparse import ArgumentParser
import os


def argument_parser():
    parser = ArgumentParser(
        prog="scorpion", description="A tool to analyze metadata in images files."
    )
    parser.add_argument("files", nargs="+", help="Files to analyze")
    parser.add_argument(
        "-d",
        "--directory",
        action="store_true",
        help="to indicate directory (replace files with directory path)",
    )
    return parser


def read_directory(file_path: str) -> list[str]:
    try:
        return os.listdir(file_path)
    except Exception as e:
        return [f"Error reading directory: {e}"]


def get_exif(raw: bytes, path: str):
    if raw.startswith(b"\xff\xd8"):
        data = JPGParser(path).run()
        JPGParser.print_exif(data)
    elif raw.startswith(b"\x89PNG\r\n\x1a\n"):
        data = PngReader(path).run()
        PngReader.print(data)
    elif raw.startswith(b"BM"):
        # data = BmpReader(path).run()
        pass
    elif raw.startswith(b"GIF87a") or raw.startswith(b"GIF89a"):
        # data = GifReader(path).run()
        pass
    else:
        print(f"Unsupported file format for file: {path}")


if __name__ == "__main__":
    parser = argument_parser()
    args = parser.parse_args()

    if args.directory:
        all_files = []
        for dir_path in args.files:
            files_in_dir = read_directory(dir_path)
            all_files.extend([os.path.join(dir_path, f) for f in files_in_dir])
        args.files = all_files
    else:
        all_files = args.files
    for file_path in all_files:
        try:
            with open(file_path, "rb") as f:
                raw = f.read()
                get_exif(raw, file_path)
        except Exception as e:
            print(f"Error reading file {file_path}: {e}")
