from PIL import Image, ExifTags


class JPGParser:
    def __init__(self, path):
        self.path = path

        self.img = self._open_image()

    def run(self):
        """
        Extract metadata from an image file.
        Args:
            path (str): Path to the image file.
        Returns:
            dict: A dictionary containing the extracted metadata.
                Warning - this may contain nested dictionaries for different IFDs.

            Example:
            {
                '0th': {
                    'ImageWidth': 1024,
                    'ImageLength': 768,
                    ...
                },
                'Exif': {
                    'ExposureTime': (1, 60),
                    'FNumber': (28, 10),
                    ...
                },
                'GPS': {
                    'GPSLatitudeRef': 'N',
                    'GPSLatitude': ((34, 1), (3, 1), (30, 1)),
                    ...
                },
                ...
            }
        """
        if not self.img:
            return {}
        return self.extract_exif(self.img)

    def _decode_bytes(value: bytes) -> str:
        charset = value[:8]
        text = value[8:]

        if b"ASCII" in charset:
            return text.decode("ascii", errors="ignore")
        elif b"JIS" in charset:
            return text.decode("shift_jis", errors="ignore")
        elif b"Unicode" in charset:
            return text.decode("utf-16", errors="ignore")
        else:
            return text.decode("utf-8", errors="ignore")

    def _open_image(self):
        try:
            img = Image.open(self.path)
            if img.format != "JPEG":
                raise ValueError("Not a valid JPEG file")
            return img
        except Exception as e:
            print(f"Error opening image {self.path}: {e}")
            return None

    def extract_exif(img) -> dict:
        exif_data = img.getexif()

        metadata = {}

        IFD_CODE_LOOKUP = {i.value: i.name for i in ExifTags.IFD}

        for tag, value in exif_data.items():
            if tag in IFD_CODE_LOOKUP:
                ifd_name = IFD_CODE_LOOKUP[tag]
                ifd_data = exif_data.get_ifd(tag).items()
                if ifd_name not in metadata:
                    metadata[ifd_name] = {}
                for sub_tag, sub_value in ifd_data:
                    sub_tag_name = (
                        ExifTags.TAGS.get(sub_tag, None)
                        or ExifTags.GPSTAGS.get(sub_tag, None)
                        or sub_tag
                    )

                    if isinstance(sub_value, bytes):
                        try:
                            sub_value = JPGParser._decode_bytes(sub_value)
                        except UnicodeDecodeError:
                            sub_value = sub_value.hex()
                    metadata[ifd_name][sub_tag_name] = sub_value
        return metadata

    def print_exif(exifs):
        print("EXIF Data:")
        for ifd in exifs:
            print(f"  {ifd}:")
            for tag in exifs[ifd]:
                print(f"    {tag}: {exifs[ifd][tag]}")
