"""
Image processing service - applies operations in memory using Pillow.
Stateless, no disk I/O.
"""

import io
import logging
from typing import Optional

from PIL import Image, ImageOps

logger = logging.getLogger(__name__)

SUPPORTED_OPERATIONS = frozenset({
    "flip_horizontal",
    "flip_vertical",
    "rotate_degrees",
    "rotate_left",
    "rotate_right",
    "resize",
    "grayscale",
    "generate_thumbnail",
})


class ImageProcessingError(Exception):
    """Raised when image processing fails."""

    pass


def _validate_operation(op_type: str, angle: int, width: int, height: int) -> None:
    """Validate operation parameters."""
    if op_type not in SUPPORTED_OPERATIONS:
        raise ImageProcessingError(f"Unknown operation: {op_type}")

    if op_type == "rotate_degrees" and angle == 0:
        raise ImageProcessingError("rotate_degrees requires non-zero angle")

    if op_type == "resize":
        if width <= 0 or height <= 0:
            raise ImageProcessingError("resize requires positive width and height")

    if op_type == "generate_thumbnail":
        if width <= 0 or height <= 0:
            raise ImageProcessingError("generate_thumbnail requires positive width and height")


def _apply_operation(
    image: Image.Image,
    op_type: str,
    angle: int = 0,
    width: int = 0,
    height: int = 0,
) -> Image.Image:
    """Apply a single operation to the image. Returns new image."""
    _validate_operation(op_type, angle, width, height)

    if op_type == "flip_horizontal":
        return ImageOps.mirror(image)

    if op_type == "flip_vertical":
        return ImageOps.flip(image)

    if op_type == "rotate_degrees":
        return image.rotate(-angle, expand=True)  # PIL uses counter-clockwise

    if op_type == "rotate_left":
        return image.rotate(90, expand=True)

    if op_type == "rotate_right":
        return image.rotate(-90, expand=True)

    if op_type == "resize":
        return image.resize((width, height), Image.Resampling.LANCZOS)

    if op_type == "grayscale":
        return image.convert("L")

    if op_type == "generate_thumbnail":
        thumb = image.copy()
        thumb.thumbnail((width, height), Image.Resampling.LANCZOS)
        return thumb

    raise ImageProcessingError(f"Unhandled operation: {op_type}")


def process_image(
    image_data: bytes,
    operations: list,
    generate_thumbnail: bool = False,
    thumbnail_width: int = 128,
    thumbnail_height: int = 128,
) -> tuple[bytes, Optional[bytes]]:
    """
    Process image in memory. Returns (processed_image_bytes, thumbnail_bytes or None).

    Args:
        image_data: Raw image bytes
        operations: List of Operation-like objects with type, angle, width, height
        generate_thumbnail: Whether to generate thumbnail from final image
        thumbnail_width: Thumbnail width when generate_thumbnail=True
        thumbnail_height: Thumbnail height when generate_thumbnail=True

    Returns:
        Tuple of (processed_image_bytes, thumbnail_bytes or None)
    """
    if not image_data:
        raise ImageProcessingError("Empty image data")

    with io.BytesIO(image_data) as buf:
        try:
            image = Image.open(buf).convert("RGB")
        except Exception as e:
            raise ImageProcessingError(f"Invalid image data: {e}") from e

    # Separate thumbnail from main pipeline - thumbnail is a post-processing step
    main_ops = []
    thumbnail_op = None

    for op in operations:
        op_type = getattr(op, "type", op.get("type", "")).strip().lower()
        angle = int(getattr(op, "angle", op.get("angle", 0)))
        width = int(getattr(op, "width", op.get("width", 0)))
        height = int(getattr(op, "height", op.get("height", 0)))

        if op_type == "generate_thumbnail":
            thumbnail_op = (width or thumbnail_width, height or thumbnail_height)
        else:
            main_ops.append((op_type, angle, width, height))

    # Apply main operations in order
    for op_type, angle, width, height in main_ops:
        image = _apply_operation(image, op_type, angle, width, height)

    # Serialize processed image to bytes
    out_buf = io.BytesIO()
    image.save(out_buf, format="PNG")
    processed_bytes = out_buf.getvalue()

    # Generate thumbnail from final image if requested
    thumbnail_bytes = None
    if generate_thumbnail or thumbnail_op:
        thumb_size = thumbnail_op or (thumbnail_width, thumbnail_height)
        thumb = image.copy()
        thumb.thumbnail(thumb_size, Image.Resampling.LANCZOS)
        thumb_buf = io.BytesIO()
        thumb.save(thumb_buf, format="PNG")
        thumbnail_bytes = thumb_buf.getvalue()

    return processed_bytes, thumbnail_bytes
