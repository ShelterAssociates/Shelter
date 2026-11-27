"""QR images for plates (qrcode 7.3.1, error correction M)."""

import qrcode
from PIL import Image, ImageColor


def matrix(link, quiet_zone=0):
    """Module rows (True = dark), quiet zone included."""
    code = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=1, border=quiet_zone)
    code.add_data(link)
    code.make(fit=True)
    return code.get_matrix()


def qr_image(link, size, fg="#000000", bg="#FFFFFF", quiet_zone=0):
    """Square RGB QR of size x size px; every module is scaled with nearest-neighbour, never blurred."""
    rows = matrix(link, quiet_zone)
    count = len(rows)
    dark, light = ImageColor.getrgb(fg), ImageColor.getrgb(bg)
    small = Image.new("RGB", (count, count))
    small.putdata([dark if cell else light for row in rows for cell in row])
    return small.resize((size, size), Image.NEAREST)


def module_count(link, quiet_zone=0):
    return len(matrix(link, quiet_zone))
