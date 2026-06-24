"""Build side-by-side comparison images for original and FEA-ready views."""

from __future__ import annotations

import logging
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

logger = logging.getLogger(__name__)

_VIEW_NAMES = ("front", "side", "top", "iso")


def build_side_by_side_comparison(
    original_views_dir: Path,
    fea_views_dir: Path,
    output_path: Path,
    force: bool = False,
) -> Path:
    """Build a side-by-side comparison PNG from two rendered view directories."""

    logger.info(
        "build_side_by_side_comparison | start | original_views_dir=%s | fea_views_dir=%s | output_path=%s | force=%s",
        original_views_dir,
        fea_views_dir,
        output_path,
        force,
    )
    try:
        output_path = Path(output_path)
        if output_path.exists() and not force:
            raise FileExistsError(f"Existing comparison image found at {output_path}. Use force=True to overwrite.")

        original_views_dir = Path(original_views_dir)
        fea_views_dir = Path(fea_views_dir)
        comparison = _compose_comparison_image(original_views_dir, fea_views_dir)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        comparison.save(output_path)
        logger.info(
            "build_side_by_side_comparison | done | output_path=%s | size=%s",
            output_path,
            comparison.size,
        )
        return output_path
    except Exception:
        logger.exception(
            "build_side_by_side_comparison | failed | original_views_dir=%s | fea_views_dir=%s | output_path=%s | force=%s",
            original_views_dir,
            fea_views_dir,
            output_path,
            force,
        )
        raise


def _compose_comparison_image(original_views_dir: Path, fea_views_dir: Path) -> Image.Image:
    """Compose one grid image from the expected original and FEA-ready views."""

    original_images = [_load_view_image(original_views_dir / f"{view_name}.png") for view_name in _VIEW_NAMES]
    fea_images = [_load_view_image(fea_views_dir / f"{view_name}.png") for view_name in _VIEW_NAMES]
    cell_width = max(image.width for image in original_images + fea_images)
    cell_height = max(image.height for image in original_images + fea_images)
    label_width = 120
    header_height = 72
    gap = 16
    width = label_width + 2 * cell_width + 3 * gap
    height = header_height + len(_VIEW_NAMES) * cell_height + (len(_VIEW_NAMES) + 1) * gap
    canvas = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(canvas)
    title_font = ImageFont.load_default()
    label_font = ImageFont.load_default()

    draw.text((label_width + gap + cell_width // 2 - 36, 20), "original", fill="black", font=title_font)
    draw.text((label_width + 2 * gap + 3 * cell_width // 2 - 30, 20), "fea-ready", fill="black", font=title_font)

    for row_index, view_name in enumerate(_VIEW_NAMES):
        top = header_height + gap + row_index * (cell_height + gap)
        draw.text((10, top + cell_height // 2 - 6), view_name, fill="black", font=label_font)
        original_image = _fit_image(original_images[row_index], cell_width, cell_height)
        fea_image = _fit_image(fea_images[row_index], cell_width, cell_height)
        canvas.paste(original_image, (label_width + gap, top))
        canvas.paste(fea_image, (label_width + 2 * gap + cell_width, top))
    return canvas


def _load_view_image(image_path: Path) -> Image.Image:
    """Open a rendered PNG and normalize it to RGB."""

    if not image_path.exists():
        raise FileNotFoundError(f"Missing rendered view: {image_path}")
    with Image.open(image_path) as image:
        return image.convert("RGB")


def _fit_image(image: Image.Image, width: int, height: int) -> Image.Image:
    """Fit an image into a fixed cell size."""

    fitted = image.copy()
    fitted.thumbnail((width, height), Image.Resampling.LANCZOS)
    canvas = Image.new("RGB", (width, height), "white")
    left = (width - fitted.width) // 2
    top = (height - fitted.height) // 2
    canvas.paste(fitted, (left, top))
    return canvas
