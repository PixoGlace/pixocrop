from __future__ import annotations

from dataclasses import dataclass

import fitz
import numpy as np
from PIL import Image


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


def detect_content_rect(
    page: fitz.Page,
    *,
    zoom: float = 1.5,
    threshold: int = 245,
    margin_pt: float = 8,
) -> PdfRect:
    """Detect the visible non-white content on a PDF page."""
    matrix = fitz.Matrix(zoom, zoom)
    pixmap = page.get_pixmap(matrix=matrix, colorspace=fitz.csGRAY, alpha=False)
    image = Image.frombytes("L", (pixmap.width, pixmap.height), pixmap.samples)
    mask = image.point(lambda pixel: 255 if pixel < threshold else 0, mode="L")
    bbox = mask.getbbox()

    if bbox is None:
        return PdfRect.from_fitz(page.rect)

    x0, y0, x1, y1 = bbox
    rect = fitz.Rect(x0 / zoom, y0 / zoom, x1 / zoom, y1 / zoom)
    return PdfRect.from_fitz(rect).expanded(margin_pt, page.rect)


def _mask_bbox(mask: np.ndarray):

    ys, xs = np.where(mask)

    if len(xs) == 0:

        return None

    return xs.min(), ys.min(), xs.max() + 1, ys.max() + 1


def _detect_content_rect_in_area(
    page: fitz.Page,
    area: fitz.Rect | None = None,
    *,
    margin_pt: float = 8,
    threshold: int = 245,
    zoom: float = 2.0,
) -> fitz.Rect:

    clip = area or page.rect

    pix = page.get_pixmap(
        matrix=fitz.Matrix(zoom, zoom),
        colorspace=fitz.csGRAY,
        alpha=False,
        clip=clip,
    )

    img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width)

    # pixels non blancs / texte / codes-barres / cadres

    mask = img < threshold

    bbox = _mask_bbox(mask)

    if bbox is None:

        return clip

    x0, y0, x1, y1 = bbox

    rect = fitz.Rect(
        clip.x0 + x0 / zoom,
        clip.y0 + y0 / zoom,
        clip.x0 + x1 / zoom,
        clip.y0 + y1 / zoom,
    )

    rect.x0 = max(page.rect.x0, rect.x0 - margin_pt)

    rect.y0 = max(page.rect.y0, rect.y0 - margin_pt)

    rect.x1 = min(page.rect.x1, rect.x1 + margin_pt)

    rect.y1 = min(page.rect.y1, rect.y1 + margin_pt)

    return rect


def _detect_colissimo_label_frame(page: fitz.Page, *, margin_pt: float = 0) -> fitz.Rect | None:
    page_rect = page.rect
    candidates: list[fitz.Rect] = []

    for drawing in page.get_drawings():
        rect = drawing.get("rect")
        if rect is None:
            continue

        rect = fitz.Rect(rect)
        width = rect.width
        height = rect.height

        if rect.x0 > page_rect.x0 + page_rect.width * 0.50:
            continue
        if width < page_rect.width * 0.20 or width > page_rect.width * 0.45:
            continue
        if height < page_rect.height * 0.35 or height > page_rect.height * 0.75:
            continue
        if rect.y0 < page_rect.y0 + page_rect.height * 0.08:
            continue

        candidates.append(rect)

    if not candidates:
        return None

    # Prefer the inner shipping-label frame over the large outer cut/adhesive frame.
    rect = min(candidates, key=lambda candidate: candidate.width * candidate.height)
    rect.x0 = max(page_rect.x0, rect.x0 - margin_pt)
    rect.y0 = max(page_rect.y0, rect.y0 - margin_pt)
    rect.x1 = min(page_rect.x1, rect.x1 + margin_pt)
    rect.y1 = min(page_rect.y1, rect.y1 + margin_pt)
    return rect


def _detect_drawn_label_frame(page: fitz.Page, *, margin_pt: float = 0) -> fitz.Rect | None:
    page_rect = page.rect
    candidates: list[fitz.Rect] = []

    for drawing in page.get_drawings():
        rect = drawing.get("rect")
        if rect is None:
            continue

        rect = fitz.Rect(rect)
        width = rect.width
        height = rect.height
        area_ratio = (width * height) / (page_rect.width * page_rect.height)

        if width < page_rect.width * 0.35:
            continue
        if height < page_rect.height * 0.25:
            continue
        if area_ratio < 0.12 or area_ratio > 0.38:
            continue

        candidates.append(rect)

    if not candidates:
        return None

    rect = max(candidates, key=lambda candidate: candidate.width * candidate.height)
    rect.x0 = max(page_rect.x0, rect.x0 - margin_pt)
    rect.y0 = max(page_rect.y0, rect.y0 - margin_pt)
    rect.x1 = min(page_rect.x1, rect.x1 + margin_pt)
    rect.y1 = min(page_rect.y1, rect.y1 + margin_pt)
    return rect


def _detect_mondial_relay_composite_frame(page: fitz.Page, *, margin_pt: float = 0) -> fitz.Rect | None:
    page_rect = page.rect
    candidates: list[fitz.Rect] = []

    for drawing in page.get_drawings():
        rect = drawing.get("rect")
        if rect is None:
            continue

        rect = fitz.Rect(rect)
        width = rect.width
        height = rect.height
        area_ratio = (width * height) / (page_rect.width * page_rect.height)

        if width < page_rect.width * 0.18:
            continue
        if height < page_rect.height * 0.02:
            continue
        if area_ratio < 0.008 or area_ratio > 0.12:
            continue
        if rect.y0 > page_rect.y0 + page_rect.height * 0.45:
            continue

        candidates.append(rect)

    if len(candidates) < 2:
        return None

    x0 = min(rect.x0 for rect in candidates)
    y0 = min(rect.y0 for rect in candidates)
    x1 = max(rect.x1 for rect in candidates)
    y1 = max(rect.y1 for rect in candidates)
    rect = fitz.Rect(x0, y0, x1, y1)

    if rect.width < page_rect.width * 0.35 or rect.height < page_rect.height * 0.18:
        return None
    if rect.width > page_rect.width * 0.98 or rect.height > page_rect.height * 0.55:
        return None

    rect.x0 = max(page_rect.x0, rect.x0 - margin_pt)
    rect.y0 = max(page_rect.y0, rect.y0 - margin_pt)
    rect.x1 = min(page_rect.x1, rect.x1 + margin_pt)
    rect.y1 = min(page_rect.y1, rect.y1 + margin_pt)
    return rect


def detect_shipping_label_rect(
    page: fitz.Page,
    *,
    margin_pt: float = 8,
    threshold: int = 245,
) -> fitz.Rect:

    text = page.get_text("text").lower()

    page_rect = page.rect

    # Cas Colissimo : la page contient l'étiquette à gauche

    # et la preuve de dépôt / notice à droite.

    if "colissimo" in text and "preuve de dépôt" in text:
        frame = _detect_colissimo_label_frame(page, margin_pt=margin_pt)
        if frame is not None:
            return frame

        left_area = fitz.Rect(
            page_rect.x0,
            page_rect.y0,
            page_rect.x0 + page_rect.width * 0.50,
            page_rect.y1,
        )

        return _detect_content_rect_in_area(
            page,
            left_area,
            margin_pt=margin_pt,
            threshold=threshold,
        )

    # Cas BPOST / Vinted / Mondial Relay : le PDF contient souvent des consignes
    # sur la meme page. Le cadre vectoriel de l'etiquette est plus fiable que
    # la bbox du contenu noir.
    carrier_keywords = (
        "bpost",
        "vinted",
        "mr belgique",
        "mondial relay",
        "shop2shop",
        "chrono relais",
    )
    composite_frame_keywords = ("mondial relay", "shop2shop", "chrono relais")

    if any(keyword in text for keyword in carrier_keywords):
        if any(keyword in text for keyword in composite_frame_keywords):
            frame = _detect_mondial_relay_composite_frame(page, margin_pt=margin_pt)
            if frame is not None:
                return frame

        frame = _detect_drawn_label_frame(page, margin_pt=margin_pt)
        if frame is not None:
            return frame

    # Cas général : BPOST, étiquette seule, ou PDF déjà centré.

    return _detect_content_rect_in_area(
        page,
        None,
        margin_pt=margin_pt,
        threshold=threshold,
    )


def detect_all_pages(
    pdf_path: str,
    *,
    margin_pt: float = 8,
    threshold: int = 245,
) -> list[PdfRect]:

    with fitz.open(pdf_path) as document:

        return [
            PdfRect.from_fitz(
                detect_shipping_label_rect(
                    page,
                    margin_pt=margin_pt,
                    threshold=threshold,
                )
            )
            for page in document
        ]
