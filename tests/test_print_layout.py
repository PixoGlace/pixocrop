import pytest

from pixocrop.print_layout import (
    COMMON_THERMAL_PAPERS,
    PageOrientation,
    PaperSpec,
    PixelRect,
    compute_target_rect,
    oriented_paper_size_mm,
    plan_render,
)


@pytest.mark.parametrize(
    ("paper", "orientation", "expected"),
    [
        (PaperSpec("70x50", "70 x 50 mm", 70, 50), PageOrientation.LANDSCAPE, (70, 50)),
        (PaperSpec("50x70", "50 x 70 mm", 50, 70), PageOrientation.PORTRAIT, (50, 70)),
        (PaperSpec("100x150", "100 x 150 mm", 100, 150), PageOrientation.PORTRAIT, (100, 150)),
        (PaperSpec("4x6", "4 x 6 in", 101.6, 152.4), PageOrientation.LANDSCAPE, (152.4, 101.6)),
    ],
)
def test_paper_and_orientation_are_not_double_inverted(
    paper: PaperSpec,
    orientation: PageOrientation,
    expected: tuple[float, float],
) -> None:
    assert oriented_paper_size_mm(paper, orientation) == pytest.approx(expected)


def test_auto_orientation_follows_selected_label() -> None:
    paper = PaperSpec("70x50", "70 x 50 mm", 70, 50)

    assert oriented_paper_size_mm(
        paper,
        PageOrientation.AUTO,
        source_width=200,
        source_height=100,
    ) == (70, 50)
    assert oriented_paper_size_mm(
        paper,
        PageOrientation.AUTO,
        source_width=100,
        source_height=200,
    ) == (50, 70)


def test_all_requested_thermal_formats_are_available() -> None:
    assert {paper.key for paper in COMMON_THERMAL_PAPERS} == {
        "thermal_70x50_mm",
        "thermal_100x150_mm",
        "thermal_4x6_in",
        "thermal_7x5_in",
    }


@pytest.mark.parametrize("dpi", [150, 300, 600])
def test_render_plan_uses_output_pixels_instead_of_source_page_pixels(dpi: int) -> None:
    printable = PixelRect(0, 0, round(70 / 25.4 * dpi), round(50 / 25.4 * dpi))
    plan = plan_render(
        source_width_pt=578 - 17,
        source_height_pt=673,
        paper_width_mm=70,
        paper_height_mm=50,
        printable_rect=printable,
        requested_dpi=dpi,
    )

    assert plan.render_width_px * plan.render_height_px <= printable.width * printable.height
    assert plan.render_width_px < 2000 or dpi == 600
    assert plan.scale_factor < 0.5
    assert "large-source-reduction" in plan.warnings


def test_pixel_limit_caps_memory_with_preserved_ratio() -> None:
    plan = plan_render(
        source_width_pt=400,
        source_height_pt=600,
        paper_width_mm=100,
        paper_height_mm=150,
        printable_rect=PixelRect(0, 0, 4000, 6000),
        requested_dpi=600,
        max_render_pixels=2_000_000,
    )

    assert plan.pixel_limit_applied is True
    assert plan.render_width_px * plan.render_height_px <= 2_000_000
    assert plan.render_width_px / plan.render_height_px == pytest.approx(2 / 3, rel=0.01)
    assert plan.estimated_bytes <= 8_000_000


def test_no_fit_preserves_source_physical_size_at_100_percent() -> None:
    plan = plan_render(
        source_width_pt=72,
        source_height_pt=144,
        paper_width_mm=100,
        paper_height_mm=150,
        printable_rect=PixelRect(0, 0, 1181, 1772),
        requested_dpi=300,
        fit_to_page=False,
    )

    assert (plan.target.width, plan.target.height) == (300, 600)
    assert plan.scale_factor == pytest.approx(1.0, abs=0.01)


def test_target_rectangle_never_crops_after_zoom() -> None:
    printable = PixelRect(20, 30, 700, 500)
    target = compute_target_rect(
        400,
        600,
        printable,
        fit_to_page=True,
        zoom_factor=3.0,
    )

    assert target.x >= printable.x
    assert target.y >= printable.y
    assert target.x + target.width <= printable.x + printable.width
    assert target.y + target.height <= printable.y + printable.height
    assert target.width / target.height == pytest.approx(2 / 3, rel=0.01)
