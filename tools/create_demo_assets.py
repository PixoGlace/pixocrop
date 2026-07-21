from __future__ import annotations

import io
import os
import tempfile
from pathlib import Path

import fitz
from PIL import Image, ImageDraw, ImageFilter, ImageFont


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
ANONYMIZED_DIR = DATA_DIR / "anonymized"
DOCS_ASSETS_DIR = ROOT / "docs" / "static" / "assets"
RENDER_SCALE = 2.0


def font(size: int, *, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = (
        (
            "/System/Library/Fonts/Supplemental/Arial Bold.ttf"
            if bold
            else "/System/Library/Fonts/Supplemental/Arial.ttf"
        ),
        (
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
            if bold
            else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
        ),
        (
            "C:/Windows/Fonts/arialbd.ttf"
            if bold
            else "C:/Windows/Fonts/arial.ttf"
        ),
    )
    for candidate in candidates:
        if Path(candidate).exists():
            return ImageFont.truetype(candidate, int(size * RENDER_SCALE))
    return ImageFont.load_default()


def box(rect: tuple[float, float, float, float]) -> tuple[int, int, int, int]:
    return tuple(int(value * RENDER_SCALE) for value in rect)


def point(position: tuple[float, float]) -> tuple[int, int]:
    return tuple(int(value * RENDER_SCALE) for value in position)


def draw_demo_barcode(
    draw: ImageDraw.ImageDraw,
    rect: tuple[float, float, float, float],
) -> None:
    left, top, right, bottom = box(rect)
    draw.rectangle((left, top, right, bottom), fill="white")
    x = left + int(4 * RENDER_SCALE)
    index = 0
    while x < right - int(4 * RENDER_SCALE):
        width = (1 + ((index * 7) % 3)) * RENDER_SCALE
        gap = (1 + ((index * 5) % 2)) * RENDER_SCALE
        draw.rectangle((int(x), top, int(min(x + width, right)), bottom), fill="#111827")
        x += width + gap
        index += 1


def draw_demo_stamp(
    draw: ImageDraw.ImageDraw,
    position: tuple[float, float],
    text: str = "DEMO - NON VALIDE",
) -> None:
    x, y = point(position)
    draw.rounded_rectangle(
        (x, y, x + int(126 * RENDER_SCALE), y + int(20 * RENDER_SCALE)),
        radius=int(4 * RENDER_SCALE),
        fill="#0f766e",
    )
    draw.text(
        (x + int(7 * RENDER_SCALE), y + int(4 * RENDER_SCALE)),
        text,
        fill="white",
        font=font(8, bold=True),
    )


def anonymize_landscape(image: Image.Image) -> Image.Image:
    draw = ImageDraw.Draw(image)

    draw.rectangle(box((53, 83, 345, 438)), fill="white")
    draw.rounded_rectangle(
        box((58, 89, 340, 431)),
        radius=int(3 * RENDER_SCALE),
        fill="white",
        outline="#111827",
        width=int(1.3 * RENDER_SCALE),
    )
    draw_demo_stamp(draw, (66, 97))
    draw.text(point((66, 124)), "CLIENT EXEMPLE", fill="#111827", font=font(15, bold=True))
    draw.text(point((66, 145)), "12 RUE DE LA DEMO", fill="#111827", font=font(10, bold=True))
    draw.text(point((66, 160)), "75000 PARIS - FRANCE", fill="#111827", font=font(10))
    draw.line(box((66, 181, 332, 181)), fill="#111827", width=int(1.2 * RENDER_SCALE))
    draw.text(point((66, 191)), "EXPEDITION TEST", fill="#111827", font=font(9, bold=True))
    draw.text(point((262, 191)), "0.25 kg", fill="#111827", font=font(9))
    draw_demo_barcode(draw, (69, 215, 329, 267))
    draw.text(point((119, 273)), "SPECIMEN - NON SCANNABLE", fill="#111827", font=font(8))
    draw.text(point((66, 296)), "DEMO 0000 0000", fill="#111827", font=font(22, bold=True))
    draw.text(point((66, 328)), "PIXOGLACE DEMO", fill="#111827", font=font(11, bold=True))
    draw.text(point((66, 345)), "REFERENCE : EXEMPLE-001", fill="#111827", font=font(9))
    draw_demo_barcode(draw, (69, 370, 329, 411))

    draw.rectangle(box((447, 323, 812, 545)), fill="white")
    draw.rounded_rectangle(
        box((450, 328, 808, 538)),
        radius=int(4 * RENDER_SCALE),
        fill="white",
        outline="#9ca3af",
        width=int(RENDER_SCALE),
    )
    draw_demo_stamp(draw, (458, 336), "DOCUMENT DE DEMO")
    draw.text(point((458, 365)), "EXPEDITEUR", fill="#374151", font=font(8, bold=True))
    draw.text(point((458, 381)), "PIXOGLACE DEMO", fill="#111827", font=font(10, bold=True))
    draw.text(point((458, 397)), "1 AVENUE DES ATELIERS", fill="#111827", font=font(9))
    draw.text(point((458, 411)), "75000 PARIS", fill="#111827", font=font(9))
    draw.line(box((450, 430, 808, 430)), fill="#d1d5db", width=int(RENDER_SCALE))
    draw.text(point((458, 441)), "DESTINATAIRE", fill="#374151", font=font(8, bold=True))
    draw.text(point((458, 457)), "CLIENT EXEMPLE", fill="#111827", font=font(10, bold=True))
    draw.text(point((458, 473)), "12 RUE DE LA DEMO - 75000 PARIS", fill="#111827", font=font(9))
    draw.text(point((458, 501)), "SUIVI : DEMO-000000000", fill="#111827", font=font(10, bold=True))
    draw.text(point((458, 520)), "Informations entierement fictives", fill="#6b7280", font=font(8))
    return image


def anonymize_portrait(image: Image.Image) -> Image.Image:
    draw = ImageDraw.Draw(image)
    draw.rectangle(box((12, 12, 310, 455)), fill="white")
    draw.rectangle(
        box((18, 18, 304, 449)),
        fill="white",
        outline="#9ca3af",
        width=int(RENDER_SCALE),
    )
    draw_demo_stamp(draw, (28, 28))
    draw_demo_barcode(draw, (30, 58, 292, 105))
    draw.text(point((83, 111)), "SPECIMEN - NON SCANNABLE", fill="#111827", font=font(8))
    draw.rectangle(box((28, 132, 170, 292)), outline="#111827", width=int(RENDER_SCALE))
    draw.text(point((34, 140)), "EXPEDITEUR", fill="#374151", font=font(8, bold=True))
    draw.text(point((34, 157)), "PIXOGLACE DEMO", fill="#111827", font=font(10, bold=True))
    draw.text(point((34, 174)), "1 RUE DES ATELIERS", fill="#111827", font=font(8))
    draw.line(box((28, 195, 170, 195)), fill="#111827", width=int(RENDER_SCALE))
    draw.text(point((34, 204)), "DESTINATAIRE", fill="#374151", font=font(8, bold=True))
    draw.text(point((34, 224)), "CLIENT EXEMPLE", fill="#111827", font=font(10, bold=True))
    draw.text(point((34, 242)), "12 RUE DE LA DEMO", fill="#111827", font=font(8))
    draw.text(point((34, 256)), "75000 PARIS", fill="#111827", font=font(8))
    draw.text(point((180, 136)), "FR / DEMO", fill="#111827", font=font(18, bold=True))
    draw.text(point((180, 172)), "N 00-0000", fill="#111827", font=font(15, bold=True))
    draw.text(point((180, 214)), "1 / 1", fill="#111827", font=font(16, bold=True))
    draw.text(point((180, 254)), "PARIS", fill="#111827", font=font(24, bold=True))
    draw.rectangle(box((28, 312, 294, 364)), outline="#111827", width=int(RENDER_SCALE))
    draw.text(point((35, 320)), "REFERENCE", fill="#374151", font=font(8, bold=True))
    draw.text(point((35, 340)), "EXEMPLE-001 / 01-01-2026", fill="#111827", font=font(10))
    draw.line(box((24, 385, 298, 385)), fill="#9ca3af", width=int(RENDER_SCALE))
    draw.text(point((28, 397)), "DOCUMENT DE DEMONSTRATION", fill="#111827", font=font(11, bold=True))
    draw.text(point((28, 418)), "Aucune donnee personnelle", fill="#6b7280", font=font(9))
    return image


def flatten_anonymized_pdf(
    source: Path,
    destination: Path,
    anonymizer,
) -> None:
    source_document = fitz.open(source)
    output_document = fitz.open()
    try:
        for source_page in source_document:
            pixmap = source_page.get_pixmap(
                matrix=fitz.Matrix(RENDER_SCALE, RENDER_SCALE),
                colorspace=fitz.csRGB,
                alpha=False,
            )
            image = Image.frombytes("RGB", (pixmap.width, pixmap.height), pixmap.samples)
            image = anonymizer(image)
            image_bytes = io.BytesIO()
            image.save(image_bytes, format="PNG", optimize=True)

            output_page = output_document.new_page(
                width=source_page.rect.width,
                height=source_page.rect.height,
            )
            output_page.insert_image(output_page.rect, stream=image_bytes.getvalue())

        output_document.set_metadata(
            {
                "title": "PixoCrop anonymized demo document",
                "author": "PixoGlace",
                "subject": "Synthetic shipping label used for the PixoCrop demo",
                "keywords": "demo, anonymized, synthetic",
            }
        )
        destination.parent.mkdir(parents=True, exist_ok=True)
        output_document.save(destination, garbage=4, deflate=True, clean=True)
    finally:
        output_document.close()
        source_document.close()


def create_anonymized_pdfs() -> list[Path]:
    jobs = (
        (
            DATA_DIR / "64574275-7f32-431e-adb5-724693119078.pdf",
            ANONYMIZED_DIR / "colissimo-demo-anonymized.pdf",
            anonymize_landscape,
        ),
        (
            DATA_DIR / "Expedition-01290516.pdf",
            ANONYMIZED_DIR / "expedition-demo-anonymized.pdf",
            anonymize_portrait,
        ),
    )
    outputs = []
    for source, destination, anonymizer in jobs:
        if source.exists():
            flatten_anonymized_pdf(source, destination, anonymizer)
        elif not destination.exists():
            raise FileNotFoundError(
                f"Missing private source and anonymized PDF: {destination}"
            )
        outputs.append(destination)
    return outputs


def add_pointer(frame: Image.Image, position: tuple[int, int]) -> Image.Image:
    result = frame.convert("RGBA")
    draw = ImageDraw.Draw(result)
    x, y = position
    pointer = [(x, y), (x + 5, y + 25), (x + 11, y + 18), (x + 18, y + 30), (x + 24, y + 26), (x + 17, y + 14), (x + 27, y + 12)]
    draw.polygon(pointer, fill="white", outline="#111827")
    draw.line(pointer + [pointer[0]], fill="#111827", width=2, joint="curve")
    return result.convert("RGB")


def add_pdf_chip(frame: Image.Image, position: tuple[int, int]) -> Image.Image:
    result = frame.convert("RGBA")
    draw = ImageDraw.Draw(result)
    x, y = position
    draw.rounded_rectangle((x, y, x + 230, y + 58), radius=8, fill="#ffffff", outline="#0f766e", width=2)
    draw.rounded_rectangle((x + 10, y + 9, x + 48, y + 49), radius=5, fill="#0f766e")
    draw.text((x + 17, y + 20), "PDF", fill="white", font=font(8, bold=True))
    draw.text((x + 60, y + 12), "bordereau-demo.pdf", fill="#111827", font=font(10, bold=True))
    draw.text((x + 60, y + 32), "Document anonymise", fill="#6b7280", font=font(8))
    return result.convert("RGB")


def grab_widget(widget, directory: Path, name: str) -> Image.Image:
    path = directory / f"{name}.png"
    if not widget.grab().save(str(path), "PNG"):
        raise RuntimeError(f"Unable to capture {name}")
    with Image.open(path) as image:
        return image.convert("RGB").copy()


def create_demo_animation(pdf_path: Path) -> tuple[Path, Path]:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from PySide6.QtCore import QPoint, QPointF, Qt
    from PySide6.QtWidgets import QApplication

    from pixocrop.app import MainWindow, PrintOptionsDialog

    application = QApplication.instance() or QApplication([])
    window = MainWindow()
    window.language = "fr"
    window.current_theme = "light"
    window.translate_ui()
    window.apply_theme("light")
    window.resize(1120, 780)
    window.show()
    application.processEvents()

    frames: list[Image.Image] = []
    durations: list[int] = []

    with tempfile.TemporaryDirectory(prefix="pixocrop-demo-") as temporary:
        temporary_dir = Path(temporary)
        blank = grab_widget(window, temporary_dir, "blank")
        preview_origin = window.preview.viewport().mapTo(window, QPoint(0, 0))
        drop_x = preview_origin.x() + max(24, (window.preview.viewport().width() - 230) // 2)
        drop_y = preview_origin.y() + max(36, (window.preview.viewport().height() - 58) // 2)
        start_x = min(blank.width - 245, drop_x + 350)
        start_y = max(76, drop_y - 220)

        frames.append(blank)
        durations.append(650)
        for index in range(7):
            progress = index / 6
            x = int(start_x + (drop_x - start_x) * progress)
            y = int(start_y + (drop_y - start_y) * progress)
            frame = add_pdf_chip(blank, (x, y))
            frame = add_pointer(frame, (x + 206, y + 48))
            frames.append(frame)
            durations.append(110)

        window.open_pdf_path(pdf_path)
        application.processEvents()
        detected = grab_widget(window, temporary_dir, "detected")
        frames.append(detected)
        durations.append(1500)
        window.preview.hide_crop_hint()

        original = window.current_scene_rect()
        if original is None:
            raise RuntimeError("The demo PDF did not produce a crop rectangle")
        center_y = original.center().y()
        target_x = min(original.left() + original.width() * 0.08, original.right() - 12)
        for index in range(7):
            progress = index / 6
            current_x = original.left() + (target_x - original.left()) * progress
            resized = window.preview._resized_crop_rect(
                original,
                QPointF(current_x, center_y),
                "left",
            )
            if window.rect_item is not None:
                window.rect_item.setRect(resized)
            window.preview.viewport().update()
            application.processEvents()
            frame = grab_widget(window, temporary_dir, f"resize-{index}")
            cursor_in_view = window.preview.mapFromScene(QPointF(current_x, center_y))
            cursor_in_window = window.preview.viewport().mapTo(window, cursor_in_view)
            frames.append(add_pointer(frame, (cursor_in_window.x(), cursor_in_window.y())))
            durations.append(115)

        final_rect = window.preview._resized_crop_rect(original, QPointF(target_x, center_y), "left")
        window.set_current_crop_from_scene(final_rect)
        application.processEvents()
        adjusted = grab_widget(window, temporary_dir, "adjusted")
        frames.append(adjusted)
        durations.append(900)

        print_center = window.print_button.mapTo(
            window,
            QPoint(window.print_button.width() // 2, window.print_button.height() // 2),
        )
        frames.append(add_pointer(adjusted, (print_center.x(), print_center.y())))
        durations.append(650)

        dialog = PrintOptionsDialog(
            window,
            window.document,
            window.effective_rects(),
            window.current_page_index(),
        )
        dialog.printer_combo.clear()
        dialog.printer_combo.addItem("Imprimante thermique 7 x 5")
        dialog.resize(920, 680)
        dialog.show()
        application.processEvents()
        dialog_frame = grab_widget(dialog, temporary_dir, "print-dialog")

        background = adjusted.filter(ImageFilter.GaussianBlur(2)).convert("RGBA")
        dim = Image.new("RGBA", background.size, (10, 20, 32, 105))
        background.alpha_composite(dim)
        x = (background.width - dialog_frame.width) // 2
        y = (background.height - dialog_frame.height) // 2
        shadow = Image.new("RGBA", background.size, (0, 0, 0, 0))
        shadow_draw = ImageDraw.Draw(shadow)
        shadow_draw.rounded_rectangle(
            (x - 10, y - 10, x + dialog_frame.width + 10, y + dialog_frame.height + 14),
            radius=16,
            fill=(0, 0, 0, 95),
        )
        shadow = shadow.filter(ImageFilter.GaussianBlur(12))
        background.alpha_composite(shadow)
        background.paste(dialog_frame, (x, y))
        frames.append(background.convert("RGB"))
        durations.append(1900)

        dialog.close()
        window.close()

    target_size = (960, 669)
    frames = [frame.resize(target_size, Image.Resampling.LANCZOS) for frame in frames]
    DOCS_ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    animation_path = DOCS_ASSETS_DIR / "pixocrop-demo.webp"
    poster_path = DOCS_ASSETS_DIR / "pixocrop-demo-poster.webp"
    frames[8].save(poster_path, format="WEBP", quality=86, method=6)
    frames[0].save(
        animation_path,
        format="WEBP",
        save_all=True,
        append_images=frames[1:],
        duration=durations,
        loop=0,
        quality=78,
        method=6,
    )
    return animation_path, poster_path


def validate_anonymized_pdf(path: Path) -> None:
    document = fitz.open(path)
    try:
        if any(page.get_text().strip() for page in document):
            raise RuntimeError(f"Unexpected extractable text in {path}")
        if document.page_count != 1:
            raise RuntimeError(f"Unexpected page count in {path}")
    finally:
        document.close()


def main() -> None:
    anonymized = create_anonymized_pdfs()
    for path in anonymized:
        validate_anonymized_pdf(path)
        print(f"Created anonymized PDF: {path.relative_to(ROOT)}")
    animation, poster = create_demo_animation(anonymized[1])
    print(f"Created animation: {animation.relative_to(ROOT)}")
    print(f"Created poster: {poster.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
