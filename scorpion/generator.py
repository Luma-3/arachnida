from PIL import Image, ImageDraw
import piexif


def create_image_with_metadata(output_path="image_metadata.jpg"):
    # 1) créer l'image
    img = Image.new("RGB", (600, 400), color=(230, 230, 230))
    draw = ImageDraw.Draw(img)
    draw.text((20, 20), "Image générée avec EXIF", fill=(0, 0, 0))
    img.save(output_path, "jpeg")

    # 2) métadonnées EXIF
    user_comment_text = "Ceci est un commentaire EXIF ajouté par un script Python."

    # Format officiel EXIF :
    #   - Préfixe "UNICODE\0"
    #   - Texte encodé en UTF-16-BE
    user_comment_bytes = b"UNICODE\0" + user_comment_text.encode("utf-16-be")

    exif_dict = {
        "0th": {
            piexif.ImageIFD.Make: "ChatGPT Camera Company",
            piexif.ImageIFD.Model: "Model-X",
            piexif.ImageIFD.Software: "Python & Piexif",
        },
        "Exif": {piexif.ExifIFD.UserComment: user_comment_bytes},
        "GPS": {
            piexif.GPSIFD.GPSLatitudeRef: "N",
            piexif.GPSIFD.GPSLatitude: [(48, 1), (51, 1), (0, 1)],
            piexif.GPSIFD.GPSLongitudeRef: "E",
            piexif.GPSIFD.GPSLongitude: [(2, 1), (21, 1), (0, 1)],
        },
    }

    exif_bytes = piexif.dump(exif_dict)

    # 3) insérer les métadonnées dans l’image
    piexif.insert(exif_bytes, output_path)

    print(f"[OK] Image générée avec métadonnées : {output_path}")


if __name__ == "__main__":
    create_image_with_metadata()
