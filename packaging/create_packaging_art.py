from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"
OUTPUT = ROOT / "build" / "packaging"
DMG_OUTPUT = ASSETS / "dmg"

NAVY = (16, 21, 34)
TEAL = (20, 184, 166)
BLUE = (77, 157, 209)
SKY = (207, 233, 255)
MINT = (207, 238, 218)
PEACH = (255, 216, 197)
AMBER = (245, 158, 11)
WHITE = (255, 255, 255)
PANEL = (247, 247, 245)
INK = (16, 21, 34)
MUTED = (89, 96, 110)

DMG_SIZE = (660, 420)
DMG_APP_CENTER = (128, 255)
DMG_APPLICATIONS_CENTER = (515, 255)


def font(size: int, *, bold: bool = False) -> ImageFont.ImageFont:
    candidates = [
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf" if bold else "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf",
    ]
    for candidate in candidates:
        path = Path(candidate)
        if path.exists():
            return ImageFont.truetype(str(path), size)
    return ImageFont.load_default()


def serif_font(size: int) -> ImageFont.ImageFont:
    candidates = [
        "/System/Library/Fonts/Supplemental/Georgia Italic.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Italic.ttf",
        "C:/Windows/Fonts/georgiai.ttf",
    ]
    for candidate in candidates:
        path = Path(candidate)
        if path.exists():
            return ImageFont.truetype(str(path), size)
    return font(size)


def centered_text_x(draw: ImageDraw.ImageDraw, text: str, text_font: ImageFont.ImageFont) -> float:
    box = draw.textbbox((0, 0), text, font=text_font)
    return (DMG_SIZE[0] - (box[2] - box[0])) / 2


def paste_contained(canvas: Image.Image, source: Image.Image, box: tuple[int, int, int, int]) -> None:
    source = source.convert("RGBA")
    box_width = box[2] - box[0]
    box_height = box[3] - box[1]
    scale = min(box_width / source.width, box_height / source.height)
    size = (max(1, int(source.width * scale)), max(1, int(source.height * scale)))
    source = source.resize(size, Image.Resampling.LANCZOS)
    x = box[0] + (box_width - source.width) // 2
    y = box[1] + (box_height - source.height) // 2
    canvas.alpha_composite(source, (x, y))


def rounded_rect(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], fill: tuple[int, ...], radius: int = 18) -> None:
    draw.rounded_rectangle(box, radius=radius, fill=fill)


def make_dmg_background() -> None:
    canvas = Image.new("RGBA", DMG_SIZE, PANEL + (255,))
    draw = ImageDraw.Draw(canvas)

    logo = Image.open(ASSETS / "logo_white.png")
    paste_contained(canvas, logo, (24, 18, 62, 56))
    draw.text((70, 25), "PixoCrop", fill=INK, font=font(18, bold=True))

    kicker = "MACOS  /  GLISSER  /  INSTALLER"
    kicker_font = font(10, bold=True)
    draw.text((centered_text_x(draw, kicker, kicker_font), 20), kicker, fill=MUTED, font=kicker_font)

    title_regular = "Installez "
    title_accent = "PixoCrop."
    regular_font = font(38, bold=True)
    accent_font = serif_font(40)
    regular_box = draw.textbbox((0, 0), title_regular, font=regular_font)
    accent_box = draw.textbbox((0, 0), title_accent, font=accent_font)
    title_width = regular_box[2] - regular_box[0] + accent_box[2] - accent_box[0]
    title_x = (canvas.width - title_width) / 2
    draw.text((title_x, 57), title_regular, fill=INK, font=regular_font)
    draw.text((title_x + regular_box[2] - regular_box[0], 55), title_accent, fill=BLUE, font=accent_font)

    subtitle = "Glissez l'app vers Applications."
    subtitle_font = font(15)
    draw.text((centered_text_x(draw, subtitle, subtitle_font), 112), subtitle, fill=MUTED, font=subtitle_font)

    # The installation area mirrors the pastel hero composition of the website.
    draw.rounded_rectangle((28, 154, 632, 368), radius=72, fill=SKY)
    draw.rounded_rectangle((48, 169, 612, 353), radius=58, outline=(176, 215, 242), width=2)
    draw.rounded_rectangle((66, 188, 190, 332), radius=28, fill=(255, 255, 255, 205))
    draw.rounded_rectangle((453, 188, 577, 332), radius=28, fill=(255, 255, 255, 205))

    draw.rounded_rectangle((270, 194, 390, 222), radius=14, fill=MINT)
    hint = "GLISSEZ"
    hint_font = font(11, bold=True)
    draw.text((centered_text_x(draw, hint, hint_font), 201), hint, fill=INK, font=hint_font)

    arrow_start = DMG_APP_CENTER[0] + 91
    arrow_end = DMG_APPLICATIONS_CENTER[0] - 91
    arrow_y = DMG_APP_CENTER[1]
    draw.line((arrow_start, arrow_y, arrow_end, arrow_y), fill=INK, width=5)
    draw.polygon(
        [(arrow_end, arrow_y), (arrow_end - 18, arrow_y - 11), (arrow_end - 18, arrow_y + 11)],
        fill=INK,
    )

    draw.rectangle((36, 344, 48, 356), fill=PEACH)
    draw.rectangle((606, 170, 618, 182), fill=MINT)
    footer = "PixoGlace  /  Open source"
    footer_font = font(11, bold=True)
    draw.text((centered_text_x(draw, footer, footer_font), 392), footer, fill=MUTED, font=footer_font)

    DMG_OUTPUT.mkdir(parents=True, exist_ok=True)
    canvas.convert("RGB").save(DMG_OUTPUT / "pixocrop-dmg-background.png", optimize=True)


def make_windows_images() -> None:
    wizard = Image.new("RGBA", (164, 314), NAVY)
    draw = ImageDraw.Draw(wizard)
    draw.rectangle((0, 216, 164, 314), fill=(15, 23, 42))
    draw.polygon([(0, 235), (164, 188), (164, 314), (0, 314)], fill=(17, 94, 89))
    draw.ellipse((92, -30, 210, 88), fill=TEAL)
    draw.ellipse((-44, 198, 58, 300), fill=AMBER)
    logo = Image.open(ASSETS / "logo_dark.png")
    paste_contained(wizard, logo, (42, 36, 122, 116))
    draw.text((24, 150), "pixoCrop", fill=WHITE, font=font(22, bold=True))
    draw.text((24, 184), "PDF labels", fill=(203, 213, 225), font=font(15))
    wizard.convert("RGB").save(OUTPUT / "windows-wizard.bmp")

    small = Image.new("RGBA", (55, 55), NAVY)
    paste_contained(small, logo, (8, 8, 47, 47))
    small.convert("RGB").save(OUTPUT / "windows-small.bmp")


def make_linux_banner() -> None:
    banner = Image.new("RGBA", (720, 260), PANEL)
    draw = ImageDraw.Draw(banner)
    rounded_rect(draw, (22, 22, 698, 238), WHITE, radius=26)
    draw.rectangle((22, 22, 698, 92), fill=NAVY)
    logo = Image.open(ASSETS / "logo_dark.png")
    title = Image.open(ASSETS / "title_dark.png")
    paste_contained(banner, logo, (44, 34, 92, 82))
    paste_contained(banner, title, (106, 42, 310, 76))
    draw.text((54, 124), "Detect - crop - print PDF shipping labels", fill=INK, font=font(24, bold=True))
    draw.text((54, 164), "Includes desktop launcher, icon, AppStream metadata and Debian package.", fill=MUTED, font=font(17))
    draw.rounded_rectangle((54, 196, 202, 224), radius=14, fill=TEAL)
    draw.text((76, 201), "Linux ready", fill=WHITE, font=font(15, bold=True))
    banner.save(OUTPUT / "linux-banner.png")


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    DMG_OUTPUT.mkdir(parents=True, exist_ok=True)
    make_dmg_background()
    make_windows_images()
    make_linux_banner()


if __name__ == "__main__":
    main()
