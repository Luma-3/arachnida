from io import BytesIO
from PIL import Image, ExifTags
from JPGParser import JPGParser


class PngReader:
    """
    PngReader is a class for reading and extracting metadata from PNG image files.
    Attributes:
            path_file (str): Path to the PNG file.
            data (bytes): Raw image data in bytes.
            img (PIL.Image.Image): Opened image object.
            img_info (dict): Dictionary containing extracted image information.
    Methods:
            __init__(data=None, path_file=None):
                    Initializes the PngReader with image data or a file path.
            _open_img():
                    Opens the image from the provided data or path. Raises ValueError if the image is not a valid PNG.
            _extract_infos():
                    Extracts metadata and information from the opened image, including signature, format, size, byte size, mode, info, and EXIF data.
            run():
                    Opens the image and returns the dictionary of extracted information if successful.
    """

    def __init__(self, path: str):
        self.path = path

        self.img = None
        self.img_info = dict()

    def _open_img(self):
        try:
            img = Image.open(self.path)
            if img.format != "PNG":
                raise ValueError("Not a valid PNG file")
            self.img = img
        except Exception as e:
            print(f"Error opening image {self.path}: {e}")

    def _extract_infos(self) -> dict:
        # Taille du fichier complet en bytes (avec Pillow)
        buf = BytesIO()
        self.img.save(buf, format=self.img.format)
        data = buf.getvalue()

        self.img_info.update(
            {
                "Format": self.img.format,
                "Taille": self.img.size,
                "Poids (bytes)": len(data),
                "Mode": self.img.mode,
                "Info": self.img.info,
                "EXIF": JPGParser.extract_exif(img=self.img),
                "XMP": parse_xmp(self.img.info.get("xmp")),
            }
        )

        return self.img_info

    def run(self) -> dict:
        self._open_img()
        if self.img:
            return self._extract_infos()

    def print(data):
        for key, value in data.items():
            if key == "Info":
                print(f"{key}:")
                for info_key, info_value in value.items():
                    print(f"  {info_key}: {info_value}")
            elif key == "EXIF":
                print("EXIF Data:")
                JPGParser.print_exif(value)
            else:
                print(f"{key}: {value}")


def parse_xmp(xmp_data: str) -> dict:
    import xml.etree.ElementTree as ET

    """
    Parses XMP data from a string and returns it as a dictionary.
    Args:
        xmp_data (str): The XMP data as a string.
    Returns:
        dict: A dictionary representation of the XMP data.
    """
    root = ET.fromstring(xmp_data)

    ns = {
        "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
    }

    metadata = {}

    for desc in root.findall(".//rdf:Description", ns):
        for k, v in desc.attrib.items():
            tag = k.split("}")[1] if "}" in k else k
            metadata[tag] = v
    return metadata
