import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import fitz
from PySide6.QtCore import QRect
from PySide6.QtGui import QColor, QImage, QPainter
from PySide6.QtPrintSupport import QPrinter
from PySide6.QtWidgets import QApplication
import pytest

from pixocrop.detection import detect_shipping_label
from pixocrop.print_layout import PageOrientation, PaperSpec, PixelRect, plan_render
from pixocrop.printer_support import apply_printer_settings, build_page_layout


@pytest.fixture(scope="module", autouse=True)
def qt_application() -> QApplication:
    application = QApplication.instance() or QApplication([])
    yield application


@pytest.mark.parametrize(
    ("paper", "orientation", "expected_mm"),
    [
        (PaperSpec("70x50", "70 x 50 mm", 70, 50), PageOrientation.LANDSCAPE, (70, 50)),
        (PaperSpec("100x150", "100 x 150 mm", 100, 150), PageOrientation.PORTRAIT, (100, 150)),
        (PaperSpec("4x6", "4 x 6 in", 101.6, 152.4), PageOrientation.PORTRAIT, (101.6, 152.4)),
    ],
)
def test_virtual_pdf_print_has_requested_physical_size_and_contained_image(
    tmp_path: Path,
    paper: PaperSpec,
    orientation: PageOrientation,
    expected_mm: tuple[float, float],
) -> None:
    output_path = tmp_path / f"{paper.key}.pdf"
    printer = QPrinter(QPrinter.PrinterMode.HighResolution)
    printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
    printer.setOutputFileName(str(output_path))
    printer.setFullPage(True)

    layout = build_page_layout(paper, orientation)
    settings = apply_printer_settings(printer, layout, 300)
    assert settings.ok

    page_rect = printer.pageRect(QPrinter.Unit.DevicePixel)
    plan = plan_render(
        source_width_pt=400,
        source_height_pt=600,
        paper_width_mm=expected_mm[0],
        paper_height_mm=expected_mm[1],
        printable_rect=PixelRect(
            page_rect.x(), page_rect.y(), page_rect.width(), page_rect.height()
        ),
        requested_dpi=printer.resolution(),
    )
    assert plan.target.x >= page_rect.x()
    assert plan.target.y >= page_rect.y()
    assert plan.target.x + plan.target.width <= page_rect.x() + page_rect.width()
    assert plan.target.y + plan.target.height <= page_rect.y() + page_rect.height()

    image = QImage(
        plan.render_width_px,
        plan.render_height_px,
        QImage.Format.Format_RGB32,
    )
    image.fill(QColor("black"))
    painter = QPainter()
    assert painter.begin(printer)
    painter.drawImage(
        QRect(
            plan.target.x,
            plan.target.y,
            plan.target.width,
            plan.target.height,
        ),
        image,
    )
    assert painter.end()

    with fitz.open(output_path) as document:
        assert document.page_count == 1
        page = document[0]
        final_mm = (page.rect.width / 72 * 25.4, page.rect.height / 72 * 25.4)
        # Qt's PDF engine quantizes custom page dimensions to PDF points.
        assert final_mm == pytest.approx(expected_mm, abs=0.2)
        assert page.get_images(full=True)


def test_tiktok_seller_prints_to_70x50_pdf_at_300_dpi(tmp_path: Path) -> None:
    source_path = Path(
        "/Users/mohamedchelali/Documents/PixoGlace/Projects/"
        "PixoDocEngine/tests/TikTokSeller.pdf"
    )
    if not source_path.exists():
        pytest.skip("TikTokSeller.pdf is not available in the local integration fixtures")

    output_path = tmp_path / "tiktok-70x50.pdf"
    printer = QPrinter(QPrinter.PrinterMode.HighResolution)
    printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
    printer.setOutputFileName(str(output_path))
    printer.setFullPage(True)
    layout = build_page_layout(
        PaperSpec("70x50", "70 x 50 mm", 70, 50),
        PageOrientation.LANDSCAPE,
    )
    assert apply_printer_settings(printer, layout, 300).ok

    with fitz.open(source_path) as document:
        detection = detect_shipping_label(document[0], margin_pt=0)
        assert not detection.used_fallback

        page_rect = printer.pageRect(QPrinter.Unit.DevicePixel)
        plan = plan_render(
            source_width_pt=detection.rect.width,
            source_height_pt=detection.rect.height,
            paper_width_mm=70,
            paper_height_mm=50,
            printable_rect=PixelRect(
                page_rect.x(), page_rect.y(), page_rect.width(), page_rect.height()
            ),
            requested_dpi=printer.resolution(),
        )
        zoom = min(
            plan.render_width_px / detection.rect.width,
            plan.render_height_px / detection.rect.height,
        )
        pixmap = document[0].get_pixmap(
            matrix=fitz.Matrix(zoom, zoom),
            colorspace=fitz.csRGB,
            alpha=False,
            clip=detection.rect.to_fitz(),
        )
        image = QImage(
            pixmap.samples,
            pixmap.width,
            pixmap.height,
            pixmap.stride,
            QImage.Format.Format_RGB888,
        ).copy()

    assert image.width() * image.height() <= 12_000_000
    painter = QPainter()
    assert painter.begin(printer)
    painter.drawImage(
        QRect(
            plan.target.x,
            plan.target.y,
            plan.target.width,
            plan.target.height,
        ),
        image,
    )
    assert painter.end()

    with fitz.open(output_path) as printed:
        final_mm = (
            printed[0].rect.width / 72 * 25.4,
            printed[0].rect.height / 72 * 25.4,
        )
        assert final_mm == pytest.approx((70, 50), abs=0.2)


def test_virtual_printer_creates_each_requested_page(tmp_path: Path) -> None:
    output_path = tmp_path / "two-pages.pdf"
    printer = QPrinter(QPrinter.PrinterMode.HighResolution)
    printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
    printer.setOutputFileName(str(output_path))
    printer.setPageLayout(
        build_page_layout(
            PaperSpec("70x50", "70 x 50 mm", 70, 50),
            PageOrientation.LANDSCAPE,
        )
    )

    painter = QPainter()
    assert painter.begin(printer)
    painter.fillRect(QRect(20, 20, 100, 100), QColor("black"))
    assert printer.newPage()
    painter.fillRect(QRect(20, 20, 100, 100), QColor("black"))
    assert painter.end()

    with fitz.open(output_path) as document:
        assert document.page_count == 2
