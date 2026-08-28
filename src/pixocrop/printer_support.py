from __future__ import annotations

from dataclasses import dataclass
import logging

from PySide6.QtCore import QMarginsF, QSizeF
from PySide6.QtGui import QPageLayout, QPageSize

from .print_layout import PageOrientation, PaperSpec


LOGGER = logging.getLogger("pixocrop.printing")
SIZE_TOLERANCE_MM = 1.0


@dataclass(frozen=True)
class PrinterSettingsResult:
    requested_size_mm: tuple[float, float]
    accepted_size_mm: tuple[float, float]
    requested_orientation: PageOrientation
    accepted_orientation: PageOrientation
    requested_dpi: int
    accepted_dpi: int
    layout_accepted: bool
    resolution_accepted: bool
    used_default_layout: bool
    errors: tuple[str, ...]

    @property
    def ok(self) -> bool:
        return not self.errors


def qt_orientation(orientation: PageOrientation) -> QPageLayout.Orientation:
    if orientation == PageOrientation.LANDSCAPE:
        return QPageLayout.Orientation.Landscape
    return QPageLayout.Orientation.Portrait


def page_orientation(value: QPageLayout.Orientation) -> PageOrientation:
    if value == QPageLayout.Orientation.Landscape:
        return PageOrientation.LANDSCAPE
    return PageOrientation.PORTRAIT


def normalized_qpage_size(paper: PaperSpec) -> QPageSize:
    short_edge, long_edge = paper.normalized_size_mm()
    return QPageSize(
        QSizeF(short_edge, long_edge),
        QPageSize.Unit.Millimeter,
        paper.name,
        QPageSize.SizeMatchPolicy.ExactMatch,
    )


def layout_size_mm(layout: QPageLayout) -> tuple[float, float]:
    rect = layout.fullRect(QPageLayout.Unit.Millimeter)
    return float(rect.width()), float(rect.height())


def sizes_match(
    left: tuple[float, float],
    right: tuple[float, float],
    *,
    tolerance_mm: float = SIZE_TOLERANCE_MM,
) -> bool:
    return abs(left[0] - right[0]) <= tolerance_mm and abs(left[1] - right[1]) <= tolerance_mm


def paper_spec_from_qpage_size(page_size: QPageSize, *, key: str = "driver") -> PaperSpec:
    size = page_size.size(QPageSize.Unit.Millimeter)
    return PaperSpec(key, page_size.name() or key, float(size.width()), float(size.height()))


def find_supported_page_size(
    supported: list[QPageSize],
    paper: PaperSpec,
    *,
    tolerance_mm: float = SIZE_TOLERANCE_MM,
) -> QPageSize | None:
    requested = paper.normalized_size_mm()
    for page_size in supported:
        if not page_size.isValid():
            continue
        size = page_size.size(QPageSize.Unit.Millimeter)
        candidate = tuple(sorted((float(size.width()), float(size.height()))))
        if sizes_match(requested, candidate, tolerance_mm=tolerance_mm):
            return page_size
    return None


def build_page_layout(
    paper: PaperSpec,
    orientation: PageOrientation,
    *,
    margins_mm: tuple[float, float, float, float] = (0, 0, 0, 0),
    supported_page_sizes: list[QPageSize] | None = None,
) -> QPageLayout:
    page_size = None
    if supported_page_sizes:
        page_size = find_supported_page_size(supported_page_sizes, paper)
    if page_size is None:
        page_size = normalized_qpage_size(paper)
    left, top, right, bottom = margins_mm
    return QPageLayout(
        page_size,
        qt_orientation(orientation),
        QMarginsF(left, top, right, bottom),
        QPageLayout.Unit.Millimeter,
    )


def apply_printer_settings(
    printer,
    requested_layout: QPageLayout,
    requested_dpi: int,
    *,
    fallback_layout: QPageLayout | None = None,
) -> PrinterSettingsResult:
    requested_size = layout_size_mm(requested_layout)
    requested_orientation = page_orientation(requested_layout.orientation())
    errors: list[str] = []
    used_default_layout = False

    set_layout_result = printer.setPageLayout(requested_layout)
    accepted_layout = printer.pageLayout()
    accepted_size = layout_size_mm(accepted_layout)
    accepted_orientation = page_orientation(accepted_layout.orientation())
    layout_accepted = bool(set_layout_result) and sizes_match(requested_size, accepted_size)
    if accepted_orientation != requested_orientation:
        layout_accepted = False
        errors.append("orientation-refused")
    if not sizes_match(requested_size, accepted_size):
        errors.append("paper-size-refused")
    elif not set_layout_result:
        errors.append("page-layout-refused")

    if not layout_accepted and fallback_layout is not None:
        used_default_layout = bool(printer.setPageLayout(fallback_layout))
        accepted_layout = printer.pageLayout()
        accepted_size = layout_size_mm(accepted_layout)
        accepted_orientation = page_orientation(accepted_layout.orientation())

    printer.setResolution(requested_dpi)
    accepted_dpi = int(printer.resolution())
    resolution_accepted = accepted_dpi == requested_dpi
    if not resolution_accepted:
        errors.append("resolution-refused")

    LOGGER.info(
        "printer settings requested_size_mm=%s accepted_size_mm=%s "
        "requested_orientation=%s accepted_orientation=%s requested_dpi=%s "
        "accepted_dpi=%s fallback=%s errors=%s",
        requested_size,
        accepted_size,
        requested_orientation.value,
        accepted_orientation.value,
        requested_dpi,
        accepted_dpi,
        used_default_layout,
        errors,
    )
    return PrinterSettingsResult(
        requested_size_mm=requested_size,
        accepted_size_mm=accepted_size,
        requested_orientation=requested_orientation,
        accepted_orientation=accepted_orientation,
        requested_dpi=requested_dpi,
        accepted_dpi=accepted_dpi,
        layout_accepted=layout_accepted,
        resolution_accepted=resolution_accepted,
        used_default_layout=used_default_layout,
        errors=tuple(errors),
    )
