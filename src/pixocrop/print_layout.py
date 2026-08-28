from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import math


MM_PER_INCH = 25.4
POINTS_PER_INCH = 72.0
DEFAULT_PRINT_DPI = 300
DEFAULT_MAX_RENDER_PIXELS = 12_000_000


class PageOrientation(str, Enum):
    PORTRAIT = "portrait"
    LANDSCAPE = "landscape"
    AUTO = "auto"


@dataclass(frozen=True)
class PaperSpec:
    key: str
    name: str
    width_mm: float
    height_mm: float

    def normalized_size_mm(self) -> tuple[float, float]:
        return min(self.width_mm, self.height_mm), max(self.width_mm, self.height_mm)


@dataclass(frozen=True)
class PixelRect:
    x: int
    y: int
    width: int
    height: int


@dataclass(frozen=True)
class RenderPlan:
    paper_width_mm: float
    paper_height_mm: float
    source_width_mm: float
    source_height_mm: float
    target: PixelRect
    scale_factor: float
    requested_dpi: int
    render_dpi: float
    render_width_px: int
    render_height_px: int
    estimated_bytes: int
    pixel_limit_applied: bool
    warnings: tuple[str, ...]


COMMON_THERMAL_PAPERS = (
    PaperSpec("thermal_70x50_mm", "70 x 50 mm", 70.0, 50.0),
    PaperSpec("thermal_100x150_mm", "100 x 150 mm", 100.0, 150.0),
    PaperSpec("thermal_4x6_in", "4 x 6 in", 4 * MM_PER_INCH, 6 * MM_PER_INCH),
    PaperSpec("thermal_7x5_in", "7 x 5 in", 7 * MM_PER_INCH, 5 * MM_PER_INCH),
)


def resolve_orientation(
    orientation: PageOrientation,
    *,
    source_width: float,
    source_height: float,
) -> PageOrientation:
    if orientation != PageOrientation.AUTO:
        return orientation
    if source_width > source_height:
        return PageOrientation.LANDSCAPE
    return PageOrientation.PORTRAIT


def oriented_paper_size_mm(
    paper: PaperSpec,
    orientation: PageOrientation,
    *,
    source_width: float = 1.0,
    source_height: float = 1.0,
) -> tuple[float, float]:
    resolved = resolve_orientation(
        orientation,
        source_width=source_width,
        source_height=source_height,
    )
    short_edge, long_edge = paper.normalized_size_mm()
    if resolved == PageOrientation.LANDSCAPE:
        return long_edge, short_edge
    return short_edge, long_edge


def compute_target_rect(
    source_width: float,
    source_height: float,
    printable_rect: PixelRect,
    *,
    fit_to_page: bool,
    zoom_factor: float = 1.0,
) -> PixelRect:
    if source_width <= 0 or source_height <= 0:
        raise ValueError("source dimensions must be positive")
    if printable_rect.width <= 0 or printable_rect.height <= 0:
        raise ValueError("printable dimensions must be positive")

    if fit_to_page:
        scale = min(
            printable_rect.width / source_width,
            printable_rect.height / source_height,
        )
    else:
        scale = 1.0

    width = max(1, int(round(source_width * scale * zoom_factor)))
    height = max(1, int(round(source_height * scale * zoom_factor)))

    # Zoom may enlarge the label, but it must never silently crop it.
    containment_scale = min(
        1.0,
        printable_rect.width / width,
        printable_rect.height / height,
    )
    width = max(1, int(round(width * containment_scale)))
    height = max(1, int(round(height * containment_scale)))

    return PixelRect(
        printable_rect.x + (printable_rect.width - width) // 2,
        printable_rect.y + (printable_rect.height - height) // 2,
        width,
        height,
    )


def plan_render(
    *,
    source_width_pt: float,
    source_height_pt: float,
    paper_width_mm: float,
    paper_height_mm: float,
    printable_rect: PixelRect,
    requested_dpi: int = DEFAULT_PRINT_DPI,
    fit_to_page: bool = True,
    zoom_factor: float = 1.0,
    max_render_pixels: int = DEFAULT_MAX_RENDER_PIXELS,
) -> RenderPlan:
    if requested_dpi <= 0:
        raise ValueError("requested DPI must be positive")
    if max_render_pixels <= 0:
        raise ValueError("pixel limit must be positive")

    source_width_mm = source_width_pt / POINTS_PER_INCH * MM_PER_INCH
    source_height_mm = source_height_pt / POINTS_PER_INCH * MM_PER_INCH
    target = compute_target_rect(
        source_width_pt,
        source_height_pt,
        printable_rect,
        fit_to_page=fit_to_page,
        zoom_factor=zoom_factor,
    )

    render_width = target.width
    render_height = target.height
    pixel_limit_applied = render_width * render_height > max_render_pixels
    if pixel_limit_applied:
        reduction = math.sqrt(max_render_pixels / (render_width * render_height))
        render_width = max(1, int(render_width * reduction))
        render_height = max(1, int(render_height * reduction))

    render_dpi = min(
        render_width / max(source_width_pt / POINTS_PER_INCH, 1e-6),
        render_height / max(source_height_pt / POINTS_PER_INCH, 1e-6),
    )
    target_width_mm = target.width / requested_dpi * MM_PER_INCH
    target_height_mm = target.height / requested_dpi * MM_PER_INCH
    scale_factor = min(
        target_width_mm / max(source_width_mm, 1e-6),
        target_height_mm / max(source_height_mm, 1e-6),
    )

    warnings: list[str] = []
    source_area = source_width_mm * source_height_mm
    paper_area = max(paper_width_mm * paper_height_mm, 1e-6)
    if source_area >= paper_area * 3.5 or scale_factor < 0.45:
        warnings.append("large-source-reduction")
    if requested_dpi >= 600 and render_width * render_height >= max_render_pixels * 0.65:
        warnings.append("high-resolution-memory")
    if pixel_limit_applied:
        warnings.append("pixel-limit-applied")

    return RenderPlan(
        paper_width_mm=paper_width_mm,
        paper_height_mm=paper_height_mm,
        source_width_mm=source_width_mm,
        source_height_mm=source_height_mm,
        target=target,
        scale_factor=scale_factor,
        requested_dpi=requested_dpi,
        render_dpi=render_dpi,
        render_width_px=render_width,
        render_height_px=render_height,
        estimated_bytes=render_width * render_height * 4,
        pixel_limit_applied=pixel_limit_applied,
        warnings=tuple(warnings),
    )
