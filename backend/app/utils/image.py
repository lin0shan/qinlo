from PIL import Image
import io
from pathlib import Path
from app.config import settings


def compress_image(file_bytes: bytes, product_id: int, filename: str) -> str:
    """压缩并保存商品图片，返回相对路径"""
    upload_dir = settings.UPLOADS_DIR / "products" / str(product_id)
    upload_dir.mkdir(parents=True, exist_ok=True)

    img = Image.open(io.BytesIO(file_bytes))

    # RGB conversion (handle RGBA/PNG)
    if img.mode in ("RGBA", "P"):
        img = img.convert("RGB")

    # Proportional resize
    if img.width > settings.IMAGE_MAX_WIDTH:
        ratio = settings.IMAGE_MAX_WIDTH / img.width
        new_height = int(img.height * ratio)
        img = img.resize((settings.IMAGE_MAX_WIDTH, new_height), Image.LANCZOS)

    save_path = upload_dir / filename
    img.save(save_path, "JPEG", quality=settings.IMAGE_QUALITY, optimize=True)

    return f"/uploads/products/{product_id}/{filename}"
