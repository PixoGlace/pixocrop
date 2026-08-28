from __future__ import annotations

from dataclasses import dataclass

import fitz
import numpy as np


POINTS_PER_MM = 72 / 25.4
MIN_CANDIDATE_SCORE = 0.58


@dataclass(frozen=True)
class PdfRect:
    x0: float
    y0: float
    x1: float
    y1: float

    @classmethod
    def from_fitz(cls, rect: fitz.Rect) -> "PdfRect":
        return cls(float(rect.x0), float(rect.y0), float(rect.x1), float(rect.y1))

    def to_fitz(self) -> fitz.Rect:
        return fitz.Rect(self.x0, self.y0, self.x1, self.y1)

    def normalized(self) -> "PdfRect":
        return PdfRect(
            min(self.x0, self.x1),
            min(self.y0, self.y1),
            max(self.x0, self.x1),
            max(self.y0, self.y1),
        )

    def clipped(self, bounds: fitz.Rect) -> "PdfRect":
        rect = self.normalized().to_fitz() & bounds
        return PdfRect.from_fitz(rect)

    def expanded(self, margin_pt: float, bounds: fitz.Rect) -> "PdfRect":
        rect = self.to_fitz()
        rect.x0 = max(bounds.x0, rect.x0 - margin_pt)
        rect.y0 = max(bounds.y0, rect.y0 - margin_pt)
        rect.x1 = min(bounds.x1, rect.x1 + margin_pt)
        rect.y1 = min(bounds.y1, rect.y1 + margin_pt)
        return PdfRect.from_fitz(rect)

    @property
    def width(self) -> float:
        return max(0.0, self.x1 - self.x0)

    @property
    def height(self) -> float:
        return max(0.0, self.y1 - self.y0)


@dataclass(frozen=True)
class DetectionCandidate:
    rect: PdfRect
    score: float
    source: str
    reasons: tuple[str, ...] = ()


@dataclass(frozen=True)
class DetectionResult:
    rect: PdfRect
    candidates: tuple[DetectionCandidate, ...]
    used_fallback: bool


@dataclass(frozen=True)
class _PageAnalysis:
    page_rect: fitz.Rect
    mask: np.ndarray
    zoom: float
    blocks: tuple[fitz.Rect, ...]
    image_rects: tuple[fitz.Rect, ...]
    drawings: tuple[fitz.Rect, ...]


def _expanded_rect(rect: fitz.Rect, margin_pt: float, bounds: fitz.Rect) -> fitz.Rect:
    return fitz.Rect(
        max(bounds.x0, rect.x0 - margin_pt),
        max(bounds.y0, rect.y0 - margin_pt),
        min(bounds.x1, rect.x1 + margin_pt),
        min(bounds.y1, rect.y1 + margin_pt),
    )


def _mask_bbox(mask: np.ndarray) -> tuple[int, int, int, int] | None:
    ys, xs = np.where(mask)
    if len(xs) == 0:
        return None
    return int(xs.min()), int(ys.min()), int(xs.max() + 1), int(ys.max() + 1)


def _render_mask(
    page: fitz.Page,
    *,
    zoom: float,
    threshold: int,
    clip: fitz.Rect | None = None,
) -> np.ndarray:
    pixmap = page.get_pixmap(
        matrix=fitz.Matrix(zoom, zoom),
        colorspace=fitz.csGRAY,
        alpha=False,
        clip=clip,
    )
    samples = np.frombuffer(pixmap.samples, dtype=np.uint8)
    return samples.reshape(pixmap.height, pixmap.stride)[:, : pixmap.width] < threshold


def detect_content_rect(
    page: fitz.Page,
    *,
    zoom: float = 1.5,
    threshold: int = 245,
    margin_pt: float = 8,
) -> PdfRect:
    """Return the visible non-white content bounds for the fallback path."""
    mask = _render_mask(page, zoom=zoom, threshold=threshold)
    bbox = _mask_bbox(mask)
    if bbox is None:
        return PdfRect.from_fitz(page.rect)
    x0, y0, x1, y1 = bbox
    rect = fitz.Rect(x0 / zoom, y0 / zoom, x1 / zoom, y1 / zoom)
    return PdfRect.from_fitz(rect).expanded(margin_pt, page.rect)


def _detect_content_rect_in_area(
    page: fitz.Page,
    area: fitz.Rect | None = None,
    *,
    margin_pt: float = 8,
    threshold: int = 245,
    zoom: float = 1.5,
) -> fitz.Rect:
    clip = area or page.rect
    mask = _render_mask(page, zoom=zoom, threshold=threshold, clip=clip)
    bbox = _mask_bbox(mask)
    if bbox is None:
        return fitz.Rect(clip)
    x0, y0, x1, y1 = bbox
    return _expanded_rect(
        fitz.Rect(
            clip.x0 + x0 / zoom,
            clip.y0 + y0 / zoom,
            clip.x0 + x1 / zoom,
            clip.y0 + y1 / zoom,
        ),
        margin_pt,
        page.rect,
    )


def _page_analysis(
    page: fitz.Page,
    *,
    threshold: int,
    zoom: float = 1.0,
) -> _PageAnalysis:
    blocks: list[fitz.Rect] = []
    image_rects: list[fitz.Rect] = []
    for block in page.get_text("dict").get("blocks", []):
        rect = fitz.Rect(block.get("bbox", (0, 0, 0, 0))) & page.rect
        if rect.is_empty:
            continue
        blocks.append(rect)
        if block.get("type") == 1:
            image_rects.append(rect)

    drawings: list[fitz.Rect] = []
    for drawing in page.get_drawings():
        rect = fitz.Rect(drawing.get("rect", (0, 0, 0, 0))) & page.rect
        if rect.width > 1 and rect.height > 1:
            drawings.append(rect)

    return _PageAnalysis(
        page_rect=fitz.Rect(page.rect),
        mask=_render_mask(page, zoom=zoom, threshold=threshold),
        zoom=zoom,
        blocks=tuple(blocks),
        image_rects=tuple(image_rects),
        drawings=tuple(drawings),
    )


def _rect_iou(left: fitz.Rect, right: fitz.Rect) -> float:
    intersection = left & right
    if intersection.is_empty:
        return 0.0
    union = left.get_area() + right.get_area() - intersection.get_area()
    return intersection.get_area() / max(union, 1.0)


def _rect_contains(container: fitz.Rect, item: fitz.Rect, tolerance: float = 3.0) -> bool:
    expanded = fitz.Rect(
        container.x0 - tolerance,
        container.y0 - tolerance,
        container.x1 + tolerance,
        container.y1 + tolerance,
    )
    return expanded.contains(item)


def _ink_density(analysis: _PageAnalysis, rect: fitz.Rect) -> float:
    page = analysis.page_rect
    clipped = rect & page
    if clipped.is_empty:
        return 0.0
    x0 = max(0, int((clipped.x0 - page.x0) * analysis.zoom))
    y0 = max(0, int((clipped.y0 - page.y0) * analysis.zoom))
    x1 = min(analysis.mask.shape[1], int(np.ceil((clipped.x1 - page.x0) * analysis.zoom)))
    y1 = min(analysis.mask.shape[0], int(np.ceil((clipped.y1 - page.y0) * analysis.zoom)))
    region = analysis.mask[y0:y1, x0:x1]
    return float(region.mean()) if region.size else 0.0


def _looks_like_machine_code(rect: fitz.Rect) -> bool:
    if rect.width <= 0 or rect.height <= 0:
        return False
    ratio = rect.width / rect.height
    return 0.78 <= ratio <= 1.28 or ratio >= 2.7 or ratio <= 0.37


def _candidate_score(
    rect: fitz.Rect,
    analysis: _PageAnalysis,
    *,
    source: str,
) -> tuple[float, tuple[str, ...]]:
    page = analysis.page_rect
    page_area = max(page.get_area(), 1.0)
    area_ratio = rect.get_area() / page_area
    width_ratio = rect.width / max(page.width, 1.0)
    height_ratio = rect.height / max(page.height, 1.0)
    aspect = rect.width / max(rect.height, 1.0)
    density = _ink_density(analysis, rect)
    contained_blocks = sum(_rect_contains(rect, block) for block in analysis.blocks)
    internal_frames = sum(_rect_contains(rect, drawing) for drawing in analysis.drawings)
    code_anchors = sum(
        _rect_contains(rect, image) and _looks_like_machine_code(image)
        for image in analysis.image_rects
    )

    score = 0.0
    reasons: list[str] = []
    if source == "carrier":
        score += 0.72
        reasons.append("carrier rule")
    elif source == "vector-frame":
        score += 0.24
        reasons.append("vector frame")
    elif source == "image-block":
        score += 0.18
        reasons.append("image block")
    elif source == "density-region":
        score += 0.12
        reasons.append("dense region")

    if 0.03 <= area_ratio <= 0.86:
        score += 0.14
        reasons.append("bounded page area")
    if 0.08 <= area_ratio <= 0.78:
        score += 0.08
    if 0.38 <= aspect <= 2.65:
        score += 0.14
        reasons.append("label aspect")
    if 1.0 - area_ratio >= 0.08:
        score += 0.10
        reasons.append("white outer margin")
    if 0.012 <= density <= 0.58:
        score += 0.12
        reasons.append("useful ink density")
    if contained_blocks >= 2:
        score += min(0.16, 0.025 * contained_blocks)
        reasons.append("grouped content")
    if internal_frames >= 2:
        score += min(0.13, 0.018 * internal_frames)
        reasons.append("internal structure")
    if code_anchors:
        score += min(0.28, 0.14 * code_anchors)
        reasons.append("barcode or QR anchor")

    width_mm = rect.width / POINTS_PER_MM
    height_mm = rect.height / POINTS_PER_MM
    if min(width_mm, height_mm) < 25 or max(width_mm, height_mm) < 45:
        score -= 0.35
    if area_ratio > 0.92 or (width_ratio > 0.96 and height_ratio > 0.96):
        score -= 0.65
        reasons.append("near-full-page penalty")
    elif area_ratio > 0.78 and code_anchors == 0:
        score -= 0.25
        reasons.append("large notice penalty")
    if density < 0.004:
        score -= 0.3

    return score, tuple(reasons)


def _contiguous_ranges(values: np.ndarray, *, max_gap: int) -> list[tuple[int, int]]:
    indexes = np.flatnonzero(values)
    if indexes.size == 0:
        return []
    ranges: list[tuple[int, int]] = []
    start = previous = int(indexes[0])
    for index_value in indexes[1:]:
        index = int(index_value)
        if index - previous > max_gap:
            ranges.append((start, previous + 1))
            start = index
        previous = index
    ranges.append((start, previous + 1))
    return ranges


def _density_regions(analysis: _PageAnalysis) -> list[fitz.Rect]:
    mask = analysis.mask
    row_active = mask.sum(axis=1) >= max(2, int(mask.shape[1] * 0.0025))
    row_ranges = _contiguous_ranges(row_active, max_gap=max(8, int(mask.shape[0] * 0.11)))
    regions: list[fitz.Rect] = []
    for y0, y1 in row_ranges:
        strip = mask[y0:y1]
        column_active = strip.sum(axis=0) >= max(2, int((y1 - y0) * 0.0025))
        for x0, x1 in _contiguous_ranges(
            column_active,
            max_gap=max(8, int(mask.shape[1] * 0.08)),
        ):
            rect = fitz.Rect(
                analysis.page_rect.x0 + x0 / analysis.zoom,
                analysis.page_rect.y0 + y0 / analysis.zoom,
                analysis.page_rect.x0 + x1 / analysis.zoom,
                analysis.page_rect.y0 + y1 / analysis.zoom,
            )
            if rect.width >= 35 * POINTS_PER_MM and rect.height >= 25 * POINTS_PER_MM:
                regions.append(rect)
    return regions


def _detect_colissimo_label_frame(page: fitz.Page, *, margin_pt: float = 0) -> fitz.Rect | None:
    page_rect = page.rect
    candidates: list[fitz.Rect] = []
    for drawing in page.get_drawings():
        rect = fitz.Rect(drawing.get("rect", (0, 0, 0, 0)))
        if rect.x0 > page_rect.x0 + page_rect.width * 0.50:
            continue
        if not page_rect.width * 0.20 <= rect.width <= page_rect.width * 0.45:
            continue
        if not page_rect.height * 0.35 <= rect.height <= page_rect.height * 0.75:
            continue
        if rect.y0 < page_rect.y0 + page_rect.height * 0.08:
            continue
        candidates.append(rect)
    if not candidates:
        return None
    return _expanded_rect(
        min(candidates, key=lambda candidate: candidate.get_area()),
        margin_pt,
        page_rect,
    )


def _detect_drawn_label_frame(page: fitz.Page, *, margin_pt: float = 0) -> fitz.Rect | None:
    page_rect = page.rect
    candidates: list[fitz.Rect] = []
    for drawing in page.get_drawings():
        rect = fitz.Rect(drawing.get("rect", (0, 0, 0, 0)))
        area_ratio = rect.get_area() / max(page_rect.get_area(), 1.0)
        if rect.width < page_rect.width * 0.35 or rect.height < page_rect.height * 0.25:
            continue
        if 0.12 <= area_ratio <= 0.82:
            candidates.append(rect)
    if not candidates:
        return None
    return _expanded_rect(max(candidates, key=lambda item: item.get_area()), margin_pt, page_rect)


def _detect_mondial_relay_composite_frame(page: fitz.Page, *, margin_pt: float = 0) -> fitz.Rect | None:
    page_rect = page.rect
    candidates: list[fitz.Rect] = []
    for drawing in page.get_drawings():
        rect = fitz.Rect(drawing.get("rect", (0, 0, 0, 0)))
        area_ratio = rect.get_area() / max(page_rect.get_area(), 1.0)
        if rect.width < page_rect.width * 0.18 or rect.height < page_rect.height * 0.02:
            continue
        if not 0.008 <= area_ratio <= 0.12:
            continue
        if rect.y0 <= page_rect.y0 + page_rect.height * 0.45:
            candidates.append(rect)
    if len(candidates) < 2:
        return None
    rect = fitz.Rect(
        min(item.x0 for item in candidates),
        min(item.y0 for item in candidates),
        max(item.x1 for item in candidates),
        max(item.y1 for item in candidates),
    )
    if rect.width < page_rect.width * 0.35 or rect.height < page_rect.height * 0.18:
        return None
    if rect.width > page_rect.width * 0.98 or rect.height > page_rect.height * 0.55:
        return None
    return _expanded_rect(rect, margin_pt, page_rect)


def _carrier_candidate(page: fitz.Page, *, margin_pt: float, threshold: int) -> fitz.Rect | None:
    text = page.get_text("text").lower()
    page_rect = page.rect
    if "colissimo" in text and "preuve de dépôt" in text:
        frame = _detect_colissimo_label_frame(page, margin_pt=margin_pt)
        if frame is not None:
            return frame
        left_area = fitz.Rect(page_rect.x0, page_rect.y0, page_rect.x0 + page_rect.width * 0.5, page_rect.y1)
        return _detect_content_rect_in_area(
            page,
            left_area,
            margin_pt=margin_pt,
            threshold=threshold,
        )

    carrier_keywords = ("bpost", "vinted", "mr belgique", "mondial relay", "shop2shop", "chrono relais")
    composite_keywords = ("mondial relay", "shop2shop", "chrono relais")
    if any(keyword in text for keyword in carrier_keywords):
        if any(keyword in text for keyword in composite_keywords):
            frame = _detect_mondial_relay_composite_frame(page, margin_pt=margin_pt)
            if frame is not None:
                return frame
        return _detect_drawn_label_frame(page, margin_pt=margin_pt)
    return None


def detect_label_candidates(
    page: fitz.Page,
    *,
    margin_pt: float = 8,
    threshold: int = 245,
) -> list[DetectionCandidate]:
    """Return credible label regions ordered by an explainable geometric score."""
    analysis = _page_analysis(page, threshold=threshold)
    raw: list[tuple[fitz.Rect, str]] = []

    carrier = _carrier_candidate(page, margin_pt=0, threshold=threshold)
    if carrier is not None:
        raw.append((carrier, "carrier"))

    for rect in analysis.drawings:
        area_ratio = rect.get_area() / max(page.rect.get_area(), 1.0)
        if rect.width >= 35 * POINTS_PER_MM and rect.height >= 25 * POINTS_PER_MM and area_ratio <= 0.93:
            raw.append((rect, "vector-frame"))

    for rect in analysis.image_rects:
        if rect.width >= 35 * POINTS_PER_MM and rect.height >= 25 * POINTS_PER_MM:
            raw.append((rect, "image-block"))

    raw.extend((rect, "density-region") for rect in _density_regions(analysis))

    candidates: list[DetectionCandidate] = []
    for rect, source in raw:
        clipped = rect & page.rect
        if clipped.is_empty:
            continue
        score, reasons = _candidate_score(clipped, analysis, source=source)
        if score < MIN_CANDIDATE_SCORE:
            continue
        expanded = _expanded_rect(clipped, margin_pt, page.rect)
        candidate = DetectionCandidate(PdfRect.from_fitz(expanded), score, source, reasons)
        duplicate_index = next(
            (
                index
                for index, existing in enumerate(candidates)
                if _rect_iou(existing.rect.to_fitz(), candidate.rect.to_fitz()) >= 0.88
            ),
            None,
        )
        if duplicate_index is None:
            candidates.append(candidate)
        elif candidate.score > candidates[duplicate_index].score:
            candidates[duplicate_index] = candidate

    candidates.sort(key=lambda item: item.score, reverse=True)
    return candidates


def detect_shipping_label(
    page: fitz.Page,
    *,
    margin_pt: float = 8,
    threshold: int = 245,
) -> DetectionResult:
    candidates = detect_label_candidates(page, margin_pt=margin_pt, threshold=threshold)
    if candidates:
        return DetectionResult(candidates[0].rect, tuple(candidates), False)
    fallback = detect_content_rect(page, margin_pt=margin_pt, threshold=threshold)
    return DetectionResult(fallback, (), True)


def detect_shipping_label_rect(
    page: fitz.Page,
    *,
    margin_pt: float = 8,
    threshold: int = 245,
) -> fitz.Rect:
    return detect_shipping_label(page, margin_pt=margin_pt, threshold=threshold).rect.to_fitz()


def detect_all_pages(
    pdf_path: str,
    *,
    margin_pt: float = 8,
    threshold: int = 245,
) -> list[PdfRect]:
    with fitz.open(pdf_path) as document:
        return [
            detect_shipping_label(page, margin_pt=margin_pt, threshold=threshold).rect
            for page in document
        ]
