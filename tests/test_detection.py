from pathlib import Path
import io

import fitz
import pytest
from PIL import Image, ImageDraw

from pixocrop.detection import (
    PdfRect,
    detect_all_pages,
    detect_content_rect,
    detect_label_candidates,
    detect_shipping_label,
)
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


def test_vector_label_is_preferred_over_notice() -> None:
    with fitz.open() as document:
        page = document.new_page(width=595, height=842)
        label = fitz.Rect(30, 40, 315, 465)
        page.draw_rect(label, color=(0, 0, 0), width=2)
        page.draw_rect(fitz.Rect(55, 85, 290, 155), color=(0, 0, 0), width=1)
        page.insert_text((65, 120), "DESTINATION 75000 PARIS", fontsize=16)
        page.insert_text((360, 100), "NOTICE DE DEPOT", fontsize=14)
        page.insert_text((360, 130), "Conservez cette partie.", fontsize=10)

        result = detect_shipping_label(page, margin_pt=0)

    assert result.used_fallback is False
    assert result.rect.x0 == pytest.approx(label.x0, abs=2)
    assert result.rect.y0 == pytest.approx(label.y0, abs=2)
    assert result.rect.x1 == pytest.approx(label.x1, abs=2)
    assert result.rect.y1 == pytest.approx(label.y1, abs=2)


def _label_image(width: int = 400, height: int = 600) -> bytes:
    image = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(image)
    draw.rectangle((2, 2, width - 3, height - 3), outline="black", width=4)
    draw.rectangle((35, 45, width - 35, 150), outline="black", width=3)
    for x in range(35, width - 35, 9):
        draw.rectangle((x, height - 170, x + 4, height - 35), fill="black")
    output = io.BytesIO()
    image.save(output, format="PNG")
    return output.getvalue()


def test_image_only_label_does_not_require_extractable_text() -> None:
    with fitz.open() as document:
        page = document.new_page(width=595, height=842)
        label = fitz.Rect(45, 55, 328, 480)
        page.insert_image(label, stream=_label_image())

        result = detect_shipping_label(page, margin_pt=0)
        extracted_text = page.get_text("text")

    assert extracted_text == ""
    assert result.used_fallback is False
    assert result.rect.x0 == pytest.approx(label.x0, abs=2)
    assert result.rect.y1 == pytest.approx(label.y1, abs=2)


def test_blank_page_uses_safe_page_fallback() -> None:
    with fitz.open() as document:
        page = document.new_page(width=595, height=842)
        result = detect_shipping_label(page, margin_pt=0)

    assert result.used_fallback is True
    assert result.candidates == ()
    assert result.rect == PdfRect(0, 0, 595, 842)


def test_multiple_image_labels_are_returned_as_candidates() -> None:
    with fitz.open() as document:
        page = document.new_page(width=842, height=595)
        first = fitz.Rect(35, 55, 290, 430)
        second = fitz.Rect(520, 55, 775, 430)
        page.insert_image(first, stream=_label_image())
        page.insert_image(second, stream=_label_image())

        candidates = detect_label_candidates(page, margin_pt=0)

    image_candidates = [item for item in candidates if item.source == "image-block"]
    assert len(image_candidates) >= 2
    assert any(item.rect.x0 == pytest.approx(first.x0, abs=3) for item in image_candidates)
    assert any(item.rect.x0 == pytest.approx(second.x0, abs=3) for item in image_candidates)


def test_tiktok_seller_uses_geometric_outer_label_frame() -> None:
    pdf_path = Path(
        "/Users/mohamedchelali/Documents/PixoGlace/Projects/"
        "PixoDocEngine/tests/TikTokSeller.pdf"
    )
    if not pdf_path.exists():
        pytest.skip("TikTokSeller.pdf is not available in the local integration fixtures")

    with fitz.open(pdf_path) as document:
        result = detect_shipping_label(document[0], margin_pt=0)

    assert result.used_fallback is False
    assert result.rect.x0 == pytest.approx(16.96, abs=2)
    assert result.rect.y0 == pytest.approx(0, abs=2)
    assert result.rect.x1 == pytest.approx(578.20, abs=2)
    assert result.rect.y1 == pytest.approx(673.49, abs=2)
    assert result.candidates[0].score >= 0.9


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
