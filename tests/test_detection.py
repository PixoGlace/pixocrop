from pathlib import Path

import fitz
import pytest

from pixocrop.detection import PdfRect, detect_all_pages, detect_content_rect
from pixocrop.pdf_ops import crop_pdf


def sample_pdf(filename: str) -> Path:
    path = Path("data") / filename
    if not path.exists():
        pytest.skip(f"sample PDF not available: {path}")
    return path


def test_detect_content_rect_finds_drawn_label(tmp_path: Path) -> None:
    pdf_path = tmp_path / "label.pdf"
    with fitz.open() as document:
        page = document.new_page(width=400, height=600)
        page.draw_rect(fitz.Rect(80, 120, 320, 420), color=(0, 0, 0), width=2)
        page.insert_text((110, 180), "EXPEDITION", fontsize=24)
        document.save(pdf_path)

    with fitz.open(pdf_path) as document:
        rect = detect_content_rect(document[0], margin_pt=0)

    assert rect.x0 <= 82
    assert rect.y0 <= 122
    assert rect.x1 >= 318
    assert rect.y1 >= 418


def test_crop_pdf_creates_page_with_clip_size(tmp_path: Path) -> None:
    input_path = tmp_path / "input.pdf"
    output_path = tmp_path / "cropped.pdf"
    with fitz.open() as document:
        page = document.new_page(width=400, height=600)
        page.insert_text((100, 100), "Bordereau")
        document.save(input_path)

    crop_pdf(input_path, output_path, [detect_content_rect(fitz.open(input_path)[0])])

    with fitz.open(output_path) as document:
        assert document.page_count == 1
        assert document[0].rect.width < 400
        assert document[0].rect.height < 600


def test_pdf_rect_normalizes_and_clips_manual_selection() -> None:
    rect = PdfRect(250, 300, 50, -20).clipped(fitz.Rect(0, 0, 200, 250))

    assert rect == PdfRect(50, 0, 200, 250)


def test_detect_colissimo_shipping_label_frame_from_sample() -> None:
    pdf_path = sample_pdf("64574275-7f32-431e-adb5-724693119078.pdf")

    rect = detect_all_pages(str(pdf_path), margin_pt=0)[0]

    assert 50 <= rect.x0 <= 65
    assert 85 <= rect.y0 <= 100
    assert 335 <= rect.x1 <= 345
    assert 425 <= rect.y1 <= 435


def test_detect_bpost_shipping_label_frame_from_sample() -> None:
    pdf_path = sample_pdf("Expedition-01290460.pdf")

    rect = detect_all_pages(str(pdf_path), margin_pt=0)[0]

    assert 15 <= rect.x0 <= 25
    assert 15 <= rect.y0 <= 25
    assert 295 <= rect.x1 <= 310
    assert 440 <= rect.y1 <= 450


def test_detect_vinted_shipping_label_frame_from_sample() -> None:
    pdf_path = sample_pdf("Bordereau-Vinted-19564802373.pdf")

    rect = detect_all_pages(str(pdf_path), margin_pt=0)[0]

    assert 80 <= rect.x0 <= 90
    assert 515 <= rect.y0 <= 530
    assert 505 <= rect.x1 <= 515
    assert 800 <= rect.y1 <= 810


def test_detect_vinted_shop2shop_landscape_label_frame_from_sample() -> None:
    pdf_path = sample_pdf("Bordereau-Vinted-20819411388.pdf")

    rect = detect_all_pages(str(pdf_path), margin_pt=0)[0]

    assert 505 <= rect.x0 <= 520
    assert 85 <= rect.y0 <= 100
    assert 820 <= rect.x1 <= 830
    assert 495 <= rect.y1 <= 505


def test_detect_mondial_relay_composite_label_frame_from_sample() -> None:
    pdf_path = sample_pdf("Expedition-83037404.pdf")

    rect = detect_all_pages(str(pdf_path), margin_pt=0)[0]

    assert 25 <= rect.x0 <= 35
    assert 10 <= rect.y0 <= 20
    assert 585 <= rect.x1 <= 595
    assert 335 <= rect.y1 <= 350

