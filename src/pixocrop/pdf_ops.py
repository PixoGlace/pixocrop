from __future__ import annotations

from pathlib import Path

import fitz

from .detection import PdfRect


def crop_pdf(
    input_path: str | Path,
    output_path: str | Path,
    rects: list[PdfRect],
    *,
    pages: list[int] | None = None,
) -> Path:
    source_path = Path(input_path)
    target_path = Path(output_path)
    page_indexes = pages if pages is not None else list(range(len(rects)))

    with fitz.open(source_path) as source, fitz.open() as target:
        for page_index in page_indexes:
            page = source[page_index]
            clip = rects[page_index].to_fitz() & page.rect
            new_page = target.new_page(width=clip.width, height=clip.height)
            new_page.show_pdf_page(new_page.rect, source, page_index, clip=clip)

        target.save(target_path, garbage=4, deflate=True)

    return target_path

