from __future__ import annotations

import os
import platform
import subprocess
from pathlib import Path


def open_for_printing(pdf_path: str | Path) -> None:
    path = Path(pdf_path).resolve()
    system = platform.system()

    if system == "Darwin":
        subprocess.Popen(["open", str(path)])
        return

    if system == "Windows":
        os.startfile(str(path))  # type: ignore[attr-defined]
        return

    subprocess.Popen(["xdg-open", str(path)])

