import base64
import io
from pathlib import Path
from typing import Any

from PIL import Image


SUPPORTED_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tiff"}


def file_to_base64(file_path: str) -> str:
    with open(file_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def bytes_to_base64(image_bytes: bytes) -> str:
    return base64.b64encode(image_bytes).decode("utf-8")


def base64_to_bytes(base64_str: str) -> bytes:
    return base64.b64decode(base64_str)


def base64_to_pil_image(base64_str: str) -> Image.Image:
    return Image.open(io.BytesIO(base64_to_bytes(base64_str)))


def pil_image_to_base64(image: Image.Image, format_name: str = "PNG") -> str:
    buffer = io.BytesIO()
    image.save(buffer, format=format_name)
    return base64.b64encode(buffer.getvalue()).decode("utf-8")


def get_image_metadata_from_base64(base64_str: str) -> dict[str, Any]:
    try:
        image = base64_to_pil_image(base64_str)
        return {
            "width": image.width,
            "height": image.height,
            "mode": image.mode,
            "format": image.format,
        }
    except Exception:
        return {}


def guess_mime_type_from_suffix(file_path: str) -> str:
    suffix = Path(file_path).suffix.lower()

    if suffix == ".png":
        return "image/png"
    if suffix in {".jpg", ".jpeg"}:
        return "image/jpeg"
    if suffix == ".webp":
        return "image/webp"
    if suffix == ".bmp":
        return "image/bmp"
    if suffix in {".tif", ".tiff"}:
        return "image/tiff"

    return "application/octet-stream"
