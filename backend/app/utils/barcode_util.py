import barcode
from barcode.writer import ImageWriter
from io import BytesIO
from pathlib import Path


def generate_barcode_image(prefix: str, product_id: int) -> tuple[str, bytes]:
    """
    生成 Code128 店内条码
    返回 (barcode_string, png_bytes)
    """
    barcode_str = f"{prefix}{product_id:08d}"

    # Generate barcode
    code = barcode.get("code128", barcode_str, writer=ImageWriter())
    buffer = BytesIO()
    code.write(buffer, options={"module_width": 0.2, "module_height": 15, "quiet_zone": 6.5})
    buffer.seek(0)

    return barcode_str, buffer.read()
