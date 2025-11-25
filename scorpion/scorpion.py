from PIL.ExifTags import TAGS, GPSTAGS
from PIL import Image, ExifTags
from argparse import ArgumentParser
import os

import piexif


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


def get_exif(img):
    return img.getexif()


def get_exif_data(exif):
    exif_data = {}
    print(exif)
    for tag_id in exif:
        tag = TAGS.get(tag_id, tag_id)
        exif_data[tag] = exif.get(tag_id)
    return exif_data


def get_gps(exif):
    gps_ifd = exif.get_ifd(ExifTags.IFD.GPSInfo)
    if not gps_ifd:
        return None

    gps_data = {}
    for key, val in gps_ifd.items():
        decoded_key = GPSTAGS.get(key, key)
        gps_data[decoded_key] = val
    return gps_data


def get_metadata(file_path: str) -> dict:
    with Image.open(file_path) as img:
        info = img.info
        for key, value in info.items():
            print(f"{key}: {value}")
        exif = get_exif(img)
        exif_data = get_exif_data(exif)
        gps_data = get_gps(exif)
        # thumbnail = get_thumbnail(exif)
        xmp_data = get_xmp(img)
        return {"exif_data": exif_data, "gps_data": gps_data, "xmp_data": xmp_data}


# def get_thumbnail(exif):
#     thumbnail = exif.get_thumbnail()
#     return thumbnail


def get_xmp(img):
    for segment, content in img.applist:
        if segment == "APP1" and b"http://ns.adobe.com/xap/1.0/" in content:
            return content


def extract_metadata(path):
    metadata = {
        "exif": None,
        "gps": None,
        "maker_notes": None,
        "iptc": None,
        "xmp": None,
        "icc_profile": None,
    }

    img = Image.open(path)

    # --- EXIF ---
    try:
        exif_dict = piexif.load(path)
        metadata["exif"] = exif_dict
    except:
        metadata["exif"] = None

    # --- GPS ---
    if "GPS" in exif_dict:
        gps = exif_dict["GPS"]
        metadata["gps"] = gps

    # --- Maker Notes (Canon, Nikon, Sony) ---
    if "Exif" in exif_dict and 0x927C in exif_dict["Exif"]:
        maker = exif_dict["Exif"][0x927C]
        metadata["maker_notes"] = maker

    # --- ICC Profile (APP2) ---
    if "icc_profile" in img.info:
        metadata["icc_profile"] = img.info["icc_profile"]

    # --- XMP (APP1 second blob) ---
    metadata["xmp"] = None
    if hasattr(img, "applist"):
        for seg, content in img.applist:
            if seg == "APP1" and b"http://ns.adobe.com/xap/1.0/" in content:
                metadata["xmp"] = content

    # --- IPTC (APP13) ---
    metadata["iptc"] = None
    if hasattr(img, "applist"):
        for seg, content in img.applist:
            if seg == "APP13":
                metadata["iptc"] = content

    return metadata


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
            metadata = extract_metadata(file_path)
            print(f"Metadata for {file_path}:")
            # print(metadata)
            for key, value in metadata.items():
                if key == "exif" and value is not None:
                    print("EXIF Data:")
                    for ifd in value:
                        print(f"  {ifd}:")
                        for tag in value[ifd]:
                            tag_name = piexif.TAGS[ifd].get(tag, {"name": tag})["name"]
                            tag_value = value[ifd][tag]
                            if isinstance(tag_value, bytes):
                                try:
                                    tag_value = tag_value.decode(errors="ignore")
                                except:
                                    pass
                            print(f"    {tag_name}: {tag_value}")
                if isinstance(value, bytes):
                    print(f"{key}: {value.decode(errors='ignore')}")
                else:
                    print(f"{key}: {value}")
        except Exception as e:
            print(f"Error processing {file_path}: {e}")
