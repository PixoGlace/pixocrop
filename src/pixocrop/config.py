import os


def _positive_int_from_env(name: str, default: int) -> int:
    try:
        return max(1, int(os.getenv(name, str(default))))
    except ValueError:
        return default


APP_NAME = "pixoCrop"
VERSION = "0.3.2"
MAX_RENDER_PIXELS = _positive_int_from_env("PIXO_MAX_RENDER_PIXELS", 12_000_000)

PROJECT_LICENSE = "GNU GPL v3"
PROJECT_URL = "https://github.com/PixoGlace/pixoCrop"
UPDATE_CHECK_URL = "https://api.github.com/repos/PixoGlace/pixoCrop/releases/latest"
DONATION_URL = "https://ko-fi.com/pixoglace"
DONATION_TEXT = "Soutenir le développement de pixoCrop"
KOFI_URL = "https://ko-fi.com/pixoglace"
