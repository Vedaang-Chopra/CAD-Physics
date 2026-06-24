# Copied from CAD Design: /Users/vedaangchopra/all_data/complete_technical_work/all_projects_implemented/CAD Design/code_base/agentic_closed_loop/modules/visual_analysis/rendering/grid_export.py
from __future__ import annotations

import base64
import html
from pathlib import Path
from typing import Iterable, List, Optional, Sequence

import pandas as pd
from PIL import Image, ImageDraw, ImageFont


DEFAULT_SOURCE_ORDER = ("ground_truth", "generated_expert", "generated_non_expert")


def render_grid_html(
    results_df: pd.DataFrame,
    *,
    view_order: Sequence[str],
    max_samples: int = 3,
    source_order: Sequence[str] = DEFAULT_SOURCE_ORDER,
    artifact_type: str = "shaded",
    image_size: int = 96,
) -> str:
    """Build an inline HTML grid for notebook inspection."""
    if results_df is None or results_df.empty:
        return "<p>No rendered results to display.</p>"

    shown_ids = _shown_dataset_ids(results_df, max_samples=max_samples)
    template_columns = f"120px repeat({len(view_order)}, {image_size}px)"
    parts = [
        "<style>",
        ".render-sample{margin:18px 0 28px 0;font-family:Arial,sans-serif}",
        f".render-grid{{display:grid;grid-template-columns:{template_columns};gap:6px;align-items:center}}",
        ".render-head{font-weight:600;font-size:12px;text-align:center}",
        ".render-source{font-weight:600;font-size:12px}",
        (
            f".render-grid img{{width:{image_size}px;height:{image_size}px;"
            "object-fit:contain;border:1px solid #ddd;background:white}}"
        ),
        "</style>",
    ]
    for dataset_id in shown_ids:
        subset = results_df[results_df["dataset_id"].astype(str) == dataset_id]
        parts.append(f'<div class="render-sample"><h3>Dataset {html.escape(dataset_id)}</h3><div class="render-grid">')
        parts.append("<div></div>")
        for view_name in view_order:
            parts.append(f'<div class="render-head">{html.escape(view_name)}</div>')
        for source_type in source_order:
            parts.append(f'<div class="render-source">{html.escape(source_type)}</div>')
            for view_name in view_order:
                image_path = _find_image_path(
                    subset,
                    source_type=source_type,
                    artifact_type=artifact_type,
                    view_name=view_name,
                )
                if image_path is None:
                    parts.append('<div class="render-head">missing</div>')
                    continue
                title = html.escape(f"{source_type} {artifact_type} {view_name}")
                parts.append(f'<img src="{_image_data_uri(image_path)}" title="{title}">')
        parts.append("</div></div>")
    return "".join(parts)


def export_render_grids_png(
    results_df: pd.DataFrame,
    *,
    output_dir: Path,
    view_order: Sequence[str],
    max_samples: int = 3,
    source_order: Sequence[str] = DEFAULT_SOURCE_ORDER,
    artifact_type: str = "shaded",
    cell_size: int = 260,
    label_width: int = 300,
    header_height: int = 86,
    title_height: int = 72,
    gap: int = 10,
    background: str = "white",
) -> List[Path]:
    """Export one high-resolution grid PNG per dataset for slides.

    The export uses explicit pixel dimensions instead of notebook CSS or
    Matplotlib auto-layout so the resulting PNGs stay consistent when pasted
    into PowerPoint.
    """
    if results_df is None or results_df.empty:
        return []
    if not view_order:
        raise ValueError("view_order must contain at least one view.")
    if not source_order:
        raise ValueError("source_order must contain at least one source type.")

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    saved_paths: List[Path] = []
    for dataset_id in _shown_dataset_ids(results_df, max_samples=max_samples):
        subset = results_df[results_df["dataset_id"].astype(str) == dataset_id]
        output_path = output_dir / f"dataset_{dataset_id}_{artifact_type}_grid.png"
        export_render_grid_png(
            subset,
            output_path=output_path,
            dataset_id=dataset_id,
            view_order=view_order,
            source_order=source_order,
            artifact_type=artifact_type,
            cell_size=cell_size,
            label_width=label_width,
            header_height=header_height,
            title_height=title_height,
            gap=gap,
            background=background,
        )
        saved_paths.append(output_path)

    _write_manifest(
        saved_paths,
        output_dir=output_dir,
        artifact_type=artifact_type,
        view_order=view_order,
        source_order=source_order,
    )
    return saved_paths


def export_render_grid_png(
    results_df: pd.DataFrame,
    *,
    output_path: str | Path,
    view_order: Sequence[str],
    source_order: Sequence[str] = DEFAULT_SOURCE_ORDER,
    artifact_type: str = "shaded",
    dataset_id: str | None = None,
    title: str | None = None,
    cell_size: int = 260,
    label_width: int = 300,
    header_height: int = 86,
    title_height: int = 72,
    gap: int = 10,
    background: str = "white",
) -> Path:
    """Export one grid PNG to an exact output path."""

    if results_df is None or results_df.empty:
        raise ValueError("results_df must contain at least one rendered result.")
    if not view_order:
        raise ValueError("view_order must contain at least one view.")
    if not source_order:
        raise ValueError("source_order must contain at least one source type.")

    resolved_dataset_id = str(dataset_id or results_df.iloc[0]["dataset_id"])
    subset = results_df[results_df["dataset_id"].astype(str) == resolved_dataset_id]
    if subset.empty:
        raise ValueError(f"dataset_id={resolved_dataset_id!r} is not present in results_df.")

    image = _compose_grid_image(
        subset,
        dataset_id=resolved_dataset_id,
        title=title,
        view_order=view_order,
        source_order=source_order,
        artifact_type=artifact_type,
        cell_size=cell_size,
        label_width=label_width,
        header_height=header_height,
        title_height=title_height,
        gap=gap,
        background=background,
    )
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    image.save(output)
    return output


def _compose_grid_image(
    subset: pd.DataFrame,
    *,
    dataset_id: str,
    title: str | None,
    view_order: Sequence[str],
    source_order: Sequence[str],
    artifact_type: str,
    cell_size: int,
    label_width: int,
    header_height: int,
    title_height: int,
    gap: int,
    background: str,
) -> Image.Image:
    bg = _background_color(background)
    width = label_width + len(view_order) * cell_size + (len(view_order) + 1) * gap
    height = title_height + header_height + len(source_order) * cell_size + (len(source_order) + 1) * gap
    image = Image.new("RGB", (width, height), bg)
    draw = ImageDraw.Draw(image)
    title_font = _font(size=32, bold=True)
    header_font = _font(size=20, bold=True)
    label_font = _font(size=22, bold=True)
    small_font = _font(size=18, bold=False)

    _draw_text_center(
        draw,
        (0, 0, width, title_height),
        title or f"Dataset {dataset_id} | {artifact_type}",
        font=title_font,
        fill=(20, 20, 20),
    )

    x0 = label_width + gap
    y0 = title_height
    for col_index, view_name in enumerate(view_order):
        left = x0 + col_index * (cell_size + gap)
        _draw_text_center(
            draw,
            (left, y0, left + cell_size, y0 + header_height),
            view_name,
            font=header_font,
            fill=(35, 35, 35),
        )

    grid_y = title_height + header_height + gap
    for row_index, source_type in enumerate(source_order):
        top = grid_y + row_index * (cell_size + gap)
        _draw_text_center(
            draw,
            (0, top, label_width, top + cell_size),
            source_type,
            font=label_font,
            fill=(35, 35, 35),
        )
        for col_index, view_name in enumerate(view_order):
            left = x0 + col_index * (cell_size + gap)
            box = (left, top, left + cell_size, top + cell_size)
            draw.rectangle(box, fill=(255, 255, 255), outline=(210, 210, 210), width=2)
            image_path = _find_image_path(
                subset,
                source_type=source_type,
                artifact_type=artifact_type,
                view_name=view_name,
            )
            if image_path is None:
                _draw_text_center(draw, box, "missing", font=small_font, fill=(120, 120, 120))
                continue
            with Image.open(image_path) as tile:
                tile = tile.convert("RGB")
                tile.thumbnail((cell_size - 16, cell_size - 16), Image.Resampling.LANCZOS)
                paste_left = left + (cell_size - tile.width) // 2
                paste_top = top + (cell_size - tile.height) // 2
                image.paste(tile, (paste_left, paste_top))
    return image


def _shown_dataset_ids(results_df: pd.DataFrame, *, max_samples: int) -> List[str]:
    if max_samples <= 0:
        return []
    return list(dict.fromkeys(results_df["dataset_id"].astype(str)))[:max_samples]


def _find_image_path(
    frame: pd.DataFrame,
    *,
    source_type: str,
    artifact_type: str,
    view_name: str,
) -> Optional[Path]:
    row = frame[
        (frame["source_type"].astype(str) == source_type)
        & (frame["artifact_type"].astype(str) == artifact_type)
        & (frame["view_name"].astype(str) == view_name)
    ]
    if row.empty or str(row.iloc[0].get("status")) == "failed":
        return None
    image_path = Path(row.iloc[0]["image_path"])
    return image_path if image_path.exists() else None


def _image_data_uri(path: Path) -> str:
    data = Path(path).read_bytes()
    return "data:image/png;base64," + base64.b64encode(data).decode("ascii")


def _background_color(background: str) -> tuple[int, int, int]:
    if background == "transparent":
        return (255, 255, 255)
    return (255, 255, 255)


def _font(*, size: int, bold: bool) -> ImageFont.ImageFont:
    candidates: Iterable[str]
    if bold:
        candidates = (
            "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
            "/Library/Fonts/Arial Bold.ttf",
        )
    else:
        candidates = (
            "/System/Library/Fonts/Supplemental/Arial.ttf",
            "/Library/Fonts/Arial.ttf",
        )
    for path in candidates:
        if Path(path).exists():
            return ImageFont.truetype(path, size=size)
    return ImageFont.load_default()


def _draw_text_center(
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    text: str,
    *,
    font: ImageFont.ImageFont,
    fill: tuple[int, int, int],
) -> None:
    text = str(text)
    bbox = draw.multiline_textbbox((0, 0), text, font=font, spacing=4, align="center")
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    x = box[0] + (box[2] - box[0] - text_width) / 2
    y = box[1] + (box[3] - box[1] - text_height) / 2
    draw.multiline_text((x, y), text, font=font, fill=fill, align="center", spacing=4)


def _write_manifest(
    paths: Sequence[Path],
    *,
    output_dir: Path,
    artifact_type: str,
    view_order: Sequence[str],
    source_order: Sequence[str],
) -> None:
    manifest_path = output_dir / "manifest.csv"
    rows = [
        {
            "file_path": str(path),
            "dataset_id": path.name.split("_")[1],
            "artifact_type": artifact_type,
            "view_order": "|".join(view_order),
            "source_order": "|".join(source_order),
        }
        for path in paths
    ]
    pd.DataFrame(rows).to_csv(manifest_path, index=False)
