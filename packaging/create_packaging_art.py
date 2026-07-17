from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"
OUTPUT = ROOT / "build" / "packaging"

NAVY = (23, 43, 77)
TEAL = (20, 184, 166)
AMBER = (245, 158, 11)
WHITE = (255, 255, 255)
PANEL = (248, 250, 252)
INK = (15, 23, 42)
MUTED = (100, 116, 139)


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
    canvas = Image.new("RGBA", (640, 420), WHITE)
    draw = ImageDraw.Draw(canvas)

    for y in range(canvas.height):
        ratio = y / canvas.height
        color = tuple(int(WHITE[i] * (1 - ratio) + PANEL[i] * ratio) for i in range(3))
        draw.line((0, y, canvas.width, y), fill=color)

    draw.rounded_rectangle((34, 32, 606, 388), radius=28, outline=(215, 226, 236), width=2)
    draw.rectangle((34, 32, 606, 142), fill=NAVY)
    draw.rounded_rectangle((34, 32, 606, 388), radius=28, outline=(215, 226, 236), width=2)

    logo = Image.open(ASSETS / "logo_white.png")
    title = Image.open(ASSETS / "title_white.png")
    paste_contained(canvas, logo, (56, 52, 122, 118))
    paste_contained(canvas, title, (130, 60, 360, 108))

    draw.text((386, 68), "Drag to install", fill=(203, 213, 225), font=font(18, bold=True))
    draw.text((78, 168), "1", fill=TEAL, font=font(24, bold=True))
    draw.text((502, 168), "2", fill=AMBER, font=font(24, bold=True))
    draw.text((82, 318), "pixoCrop.app", fill=INK, font=font(17, bold=True))
    draw.text((466, 318), "Applications", fill=INK, font=font(17, bold=True))
    draw.line((245, 255, 394, 255), fill=TEAL, width=5)
    draw.polygon([(394, 255), (374, 244), (374, 266)], fill=TEAL)

    canvas.save(OUTPUT / "dmg-background.png")


def make_windows_images() -> None:
    wizard = Image.new("RGBA", (164, 314), NAVY)
    draw = ImageDraw.Draw(wizard)
    draw.rectangle((0, 216, 164, 314), fill=(15, 23, 42))
    draw.polygon([(0, 235), (164, 188), (164, 314), (0, 314)], fill=(17, 94, 89))
    draw.ellipse((92, -30, 210, 88), fill=TEAL)
    draw.ellipse((-44, 198, 58, 300), fill=AMBER)
    logo = Image.open(ASSETS / "logo_white.png")
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
    logo = Image.open(ASSETS / "logo_white.png")
    title = Image.open(ASSETS / "title_white.png")
    paste_contained(banner, logo, (44, 34, 92, 82))
    paste_contained(banner, title, (106, 42, 310, 76))
    draw.text((54, 124), "Detect - crop - print PDF shipping labels", fill=INK, font=font(24, bold=True))
    draw.text((54, 164), "Includes desktop launcher, icon, AppStream metadata and Debian package.", fill=MUTED, font=font(17))
    draw.rounded_rectangle((54, 196, 202, 224), radius=14, fill=TEAL)
    draw.text((76, 201), "Linux ready", fill=WHITE, font=font(15, bold=True))
    banner.save(OUTPUT / "linux-banner.png")


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    make_dmg_background()
    make_windows_images()
    make_linux_banner()


if __name__ == "__main__":
    main()
