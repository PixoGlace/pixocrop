from PySide6.QtCore import QSizeF
from PySide6.QtGui import QPageLayout, QPageSize
import pytest

from pixocrop.print_layout import PageOrientation, PaperSpec
from pixocrop.printer_support import (
    apply_printer_settings,
    build_page_layout,
    find_supported_page_size,
    layout_size_mm,
)


class FakePrinter:
    def __init__(
        self,
        default_layout: QPageLayout,
        *,
        refuse_layout: bool = False,
        accepted_dpi: int | None = None,
    ) -> None:
        self._layout = default_layout
        self._dpi = 300
        self.refuse_layout = refuse_layout
        self.accepted_dpi = accepted_dpi

    def setPageLayout(self, layout: QPageLayout) -> bool:
        if self.refuse_layout:
            return False
        self._layout = layout
        return True

    def pageLayout(self) -> QPageLayout:
        return self._layout

    def setResolution(self, dpi: int) -> None:
        self._dpi = self.accepted_dpi if self.accepted_dpi is not None else dpi

    def resolution(self) -> int:
        return self._dpi


@pytest.mark.parametrize(
    ("paper", "orientation", "expected"),
    [
        (PaperSpec("70x50", "70 x 50", 70, 50), PageOrientation.LANDSCAPE, (70, 50)),
        (PaperSpec("50x70", "50 x 70", 50, 70), PageOrientation.PORTRAIT, (50, 70)),
        (PaperSpec("100x150", "100 x 150", 100, 150), PageOrientation.PORTRAIT, (100, 150)),
    ],
)
def test_qt_layout_has_expected_physical_dimensions(
    paper: PaperSpec,
    orientation: PageOrientation,
    expected: tuple[float, float],
) -> None:
    layout = build_page_layout(paper, orientation)

    assert layout_size_mm(layout) == pytest.approx(expected, abs=0.1)


def test_driver_announced_size_is_preferred() -> None:
    announced = QPageSize(QPageSize.PageSizeId.A6)
    size = announced.size(QPageSize.Unit.Millimeter)
    requested = PaperSpec("a6-like", "A6 compatible", size.width(), size.height())

    assert find_supported_page_size([announced], requested) == announced


def test_landscape_driver_size_is_not_inverted_twice() -> None:
    announced = QPageSize(
        QSizeF(70, 50),
        QPageSize.Unit.Millimeter,
        "Driver 70 x 50",
        QPageSize.SizeMatchPolicy.ExactMatch,
    )
    layout = build_page_layout(
        PaperSpec("70x50", "70 x 50", 70, 50),
        PageOrientation.LANDSCAPE,
        supported_page_sizes=[announced],
    )

    assert layout_size_mm(layout) == pytest.approx((70, 50), abs=0.1)


def test_accepted_driver_settings_are_reported() -> None:
    default_layout = build_page_layout(
        PaperSpec("a4", "A4", 210, 297),
        PageOrientation.PORTRAIT,
    )
    requested = build_page_layout(
        PaperSpec("70x50", "70 x 50", 70, 50),
        PageOrientation.LANDSCAPE,
    )
    printer = FakePrinter(default_layout)

    result = apply_printer_settings(printer, requested, 300, fallback_layout=default_layout)

    assert result.ok is True
    assert result.accepted_size_mm == pytest.approx((70, 50), abs=0.1)
    assert result.accepted_dpi == 300
    assert result.used_default_layout is False


def test_refused_paper_uses_default_and_reports_error() -> None:
    default_layout = build_page_layout(
        PaperSpec("a4", "A4", 210, 297),
        PageOrientation.PORTRAIT,
    )
    requested = build_page_layout(
        PaperSpec("70x50", "70 x 50", 70, 50),
        PageOrientation.LANDSCAPE,
    )
    printer = FakePrinter(default_layout, refuse_layout=True)

    result = apply_printer_settings(printer, requested, 300, fallback_layout=default_layout)

    assert result.ok is False
    assert "paper-size-refused" in result.errors
    assert result.used_default_layout is False
    assert result.accepted_size_mm == pytest.approx((210, 297), abs=0.1)


def test_refused_resolution_is_reported() -> None:
    layout = build_page_layout(
        PaperSpec("70x50", "70 x 50", 70, 50),
        PageOrientation.LANDSCAPE,
    )
    printer = FakePrinter(layout, accepted_dpi=203)

    result = apply_printer_settings(printer, layout, 300)

    assert result.resolution_accepted is False
    assert result.accepted_dpi == 203
    assert "resolution-refused" in result.errors
