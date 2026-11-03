"""GPS coordinates from EXIF metadata."""
from PIL import Image

GPS_IFD = 0x8825
LAT_REF, LAT, LNG_REF, LNG = 1, 2, 3, 4


def _to_degrees(dms) -> float:
    d, m, s = (float(x) for x in dms)
    return d + m / 60 + s / 3600


def extract_gps(img: Image.Image) -> tuple[float, float] | None:
    """Return (lat, lng) in decimal degrees, or None if absent or unreadable."""
    try:
        gps = img.getexif().get_ifd(GPS_IFD)
        if not gps or LAT not in gps or LNG not in gps:
            return None
        lat = _to_degrees(gps[LAT])
        lng = _to_degrees(gps[LNG])
        if str(gps.get(LAT_REF, "N")).upper().startswith("S"):
            lat = -lat
        if str(gps.get(LNG_REF, "E")).upper().startswith("W"):
            lng = -lng
        return lat, lng
    except Exception:
        return None
