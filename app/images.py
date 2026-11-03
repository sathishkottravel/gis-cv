"""Upload validation: decodable JPEG/PNG up to 10 MB."""
import io

from PIL import Image, UnidentifiedImageError

from app.errors import InvalidImage

MAX_BYTES = 10 * 1024 * 1024
CONTENT_TYPES = {"JPEG": "image/jpeg", "PNG": "image/png"}


def load_image(data: bytes) -> tuple[Image.Image, str]:
    """Return the decoded image and its content type, or raise InvalidImage."""
    if len(data) > MAX_BYTES:
        raise InvalidImage("File is too large (maximum 10 MB).")
    try:
        img = Image.open(io.BytesIO(data))
        if img.format not in CONTENT_TYPES:
            raise InvalidImage("File is not a supported image (JPEG or PNG).")
        img.load()
    except (UnidentifiedImageError, OSError, SyntaxError):
        raise InvalidImage("File is not a supported image (JPEG or PNG).") from None
    return img, CONTENT_TYPES[img.format]
