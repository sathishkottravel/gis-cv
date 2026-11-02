import io

import pytest
from PIL import Image

from app import config
from app.errors import InvalidImage
from app.geo import GPS_IFD, extract_gps
from app.images import MAX_BYTES, load_image


def _jpeg_with_gps(lat_ref, lat_dms, lng_ref, lng_dms) -> bytes:
    img = Image.new("RGB", (16, 16), "blue")
    exif = Image.Exif()
    exif[GPS_IFD] = {1: lat_ref, 2: lat_dms, 3: lng_ref, 4: lng_dms}
    buf = io.BytesIO()
    img.save(buf, format="JPEG", exif=exif)
    return buf.getvalue()


def test_text_payload_rejected():
    with pytest.raises(InvalidImage, match="not a supported image"):
        load_image(b"hello, this is not an image")


def test_oversized_payload_rejected():
    with pytest.raises(InvalidImage, match="too large"):
        load_image(b"\0" * (11 * 1024 * 1024))
    assert MAX_BYTES == 10 * 1024 * 1024


def test_unsupported_format_rejected():
    buf = io.BytesIO()
    Image.new("RGB", (4, 4)).save(buf, format="GIF")
    with pytest.raises(InvalidImage):
        load_image(buf.getvalue())


def test_sample_png_accepted():
    data = (config.ROOT / "samples" / "14_stop.png").read_bytes()
    img, content_type = load_image(data)
    assert content_type == "image/png"
    assert img.size[0] >= 128


def test_gps_read_from_exif():
    # Stockholm: 59°19'44.4" N, 18°4'8.4" E
    img, content_type = load_image(_jpeg_with_gps("N", (59, 19, 44.4), "E", (18, 4, 8.4)))
    assert content_type == "image/jpeg"
    lat, lng = extract_gps(img)
    assert lat == pytest.approx(59.329, abs=1e-4)
    assert lng == pytest.approx(18.069, abs=1e-4)


def test_gps_south_west_are_negative():
    img, _ = load_image(_jpeg_with_gps("S", (33, 52, 4.0), "W", (70, 40, 0.0)))
    lat, lng = extract_gps(img)
    assert lat < 0 and lng < 0


def test_no_exif_gives_none():
    img, _ = load_image((config.ROOT / "samples" / "14_stop.png").read_bytes())
    assert extract_gps(img) is None
