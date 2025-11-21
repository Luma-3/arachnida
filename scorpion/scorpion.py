from argparse import ArgumentParser
import os
import struct
from dataclasses import dataclass


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


def read_file(file_path):
    with open(file_path, "rb") as file:
        return file.read()


def match_header_bytes(data):
    if data.startswith(b"\xff\xd8\xff"):
        return "JPEG image"
    elif data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "PNG image"
    elif data.startswith(b"BM"):
        return "BMP image"
    elif data.startswith(b"GIF"):
        return "GIF image"
    else:
        return "Unknown file type"


def jpeg_as_app1(data: bytes) -> bool:
    if data.find(b"\xff\xe1") != -1:
        return True
    return False


def read_directory(file_path: str) -> list[str]:
    try:
        return os.listdir(file_path)
    except Exception as e:
        return [f"Error reading directory: {e}"]


def find_jpeg_files(directory: str) -> list[str]:
    jpeg_files = []
    try:
        for entry in os.listdir(directory):
            if entry.lower().endswith((".jpg", ".jpeg")):
                jpeg_files.append(entry)
    except Exception as e:
        jpeg_files.append(f"Error reading directory: {e}")
    return jpeg_files


@dataclass
class Exif:
    tiff_edian: str
    tiff_version: int
    ifd0: dict[str, any]


def print_exif(data: bytes):
    pos = 0
    while True:
        pos = data.find(b"\xff\xe1", pos)  # APP1 marker
        if pos == -1:
            return
        size = struct.unpack(">H", data[pos + 2 : pos + 4])[0]
        exif_data = data[pos + 4 : pos + 4 + size]

        if exif_data.startswith(b"Exif\x00\x00"):
            print_TIFF(exif_data[6:])
        pos += 2


def print_TIFF(data: bytes):
    if data[0:2] == b"II":
        endian = "little"
    elif data[0:2] == b"MM":
        endian = "big"
    else:
        print("Invalid TIFF header")
        return

    version = int.from_bytes(data[2:4], endian)
    if version != 42:
        print("Invalid TIFF version")
        return

    ifd_offset = int.from_bytes(data[4:8], endian)
    print_ifd(data, ifd_offset, endian)


def print_ifd(data: bytes, offset: int, endian: str):
    idfs = []
    num_entries = int.from_bytes(data[offset : offset + 2], endian)
    print(f"Number of IFD entries: {num_entries}")
    for i in range(num_entries):
        entry_offset = offset + 2 + i * 12
        tag = int.from_bytes(data[entry_offset : entry_offset + 2], endian)
        type_ = int.from_bytes(data[entry_offset + 2 : entry_offset + 4], endian)
        count = int.from_bytes(data[entry_offset + 4 : entry_offset + 8], endian)
        value_offset = data[entry_offset + 8 : entry_offset + 12]
        idfs.append((tag, type_, count, value_offset))
    print_ifd_values(data, idfs, endian)


tag_names = {
    0x010E: "ImageDescription",
    0x010F: "Make",
    0x0110: "Model",
    0x01112: "Orientation",
    0x011A: "XResolution",
    0x011B: "YResolution",
    0x0128: "ResolutionUnit",
    0x0131: "Software",
    0x0132: "DateTime",
    0x013E: "WhitePoint",
    0x013F: "PrimaryChromaticities",
    0x0211: "YCbCrCoefficients",
    0x0213: "YCbCrPositioning",
    0x0214: "ReferenceBlackWhite",
    0x8298: "Copyright",
    0x8769: "ExifIFDPointer",
}


def print_ifd_values(data: bytes, ifds: list[tuple[int, int, int, bytes]], endian: str):
    for tag, type_, count, value_offset in ifds:
        tag_name = tag_names.get(tag, "Unknown")
        if type_ == 2:  # ASCII
            if count <= 4:
                value = value_offset[: count - 1].decode(errors="ignore")
            else:
                offset = int.from_bytes(value_offset, endian)
                value = data[offset : offset + count - 1].decode(errors="ignore")
            print(f"Tag {tag:04x} ({tag_name}) ASCII Value: {value}")
        elif type_ == 3:  # SHORT
            if count <= 2:
                value = int.from_bytes(value_offset[:2], endian)
            else:
                offset = int.from_bytes(value_offset, endian)
                value = int.from_bytes(data[offset : offset + 2], endian)
                print(f"Tag {tag:04x} ({tag_name}) SHORT Value: {value}")
        elif type_ == 4:  # LONG
            if count == 1:
                value = int.from_bytes(value_offset, endian)
            else:
                offset = int.from_bytes(value_offset, endian)
                value = int.from_bytes(data[offset : offset + 4], endian)
            print(f"Tag {tag:04x} ({tag_name}) LONG Value: {value}")
        elif type_ == 5:  # RATIONAL
            offset = int.from_bytes(value_offset, endian)
            numerator = int.from_bytes(data[offset : offset + 4], endian)
            denominator = int.from_bytes(data[offset + 4 : offset + 8], endian)
            print(
                f"Tag {tag:04x} ({tag_name}) RATIONAL Value: {numerator}/{denominator}"
            )
        else:
            print(f"Tag {tag:04x} ({tag_name}) has unsupported type {type_}")


if __name__ == "__main__":
    parser = argument_parser()
    args = parser.parse_args()

    if args.directory:
        files = read_directory(args.files[0])
        for file in files:
            if jpeg_as_app1(read_file(os.path.join(args.files[0], file))):
                print_exif(read_file(os.path.join(args.files[0], file)))
        exit(0)

    # jpeg_files = find_jpeg_files(args.file)
    # for jpeg in jpeg_files:
    #     if jpeg_as_app1(read_file(os.path.join(args.files[0], jpeg))):
    #         print(f"Found JPEG file: {jpeg}")
    #         print(jpeg_read(read_file(os.path.join(args.files[0], jpeg))))
