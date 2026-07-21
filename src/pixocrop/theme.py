from __future__ import annotations

from dataclasses import dataclass


PIXO_NAVY = "#172B4D"
PIXO_TEAL = "#14B8A6"
PIXO_AMBER = "#F59E0B"
PIXO_DARK = "#0F172A"
PIXO_WHITE = "#FFFFFF"
PIXO_LIGHT_SECONDARY = "#64748B"
PIXO_DARK_SECONDARY = "#CBD5E1"
PIXO_LIGHT_PANEL = "#F8FAFC"
PIXO_DARK_PANEL = "#111827"
PIXO_LIGHT_BORDER = "#D7DEE8"
PIXO_DARK_BORDER = "#253247"


@dataclass(frozen=True)
class ThemeColors:
    background: str
    panel: str
    panel_alt: str
    text: str
    secondary: str
    border: str
    input_background: str
    disabled_background: str
    disabled_text: str
    preview_background: str
    menu_background: str
    menu_selection: str
    menu_selection_text: str
    accent: str
    accent_hover: str
    focus: str
    link: str


def theme_colors(theme: str) -> ThemeColors:
    if theme == "dark":
        return ThemeColors(
            background=PIXO_DARK,
            panel=PIXO_DARK_PANEL,
            panel_alt="#1E293B",
            text=PIXO_WHITE,
            secondary=PIXO_DARK_SECONDARY,
            border=PIXO_DARK_BORDER,
            input_background="#0B1220",
            disabled_background="#1F2937",
            disabled_text="#94A3B8",
            preview_background="#0B1220",
            menu_background="#111827",
            menu_selection="#134E4A",
            menu_selection_text=PIXO_WHITE,
            accent="#0D9488",
            accent_hover="#14B8A6",
            focus="#FBBF24",
            link="#5EEAD4",
        )

    return ThemeColors(
        background=PIXO_WHITE,
        panel=PIXO_LIGHT_PANEL,
        panel_alt=PIXO_WHITE,
        text=PIXO_NAVY,
        secondary=PIXO_LIGHT_SECONDARY,
        border=PIXO_LIGHT_BORDER,
        input_background=PIXO_WHITE,
        disabled_background="#EEF2F7",
        disabled_text="#64748B",
        preview_background="#EEF2F7",
        menu_background=PIXO_WHITE,
        menu_selection="#CCFBF1",
        menu_selection_text=PIXO_NAVY,
        accent="#0F766E",
        accent_hover="#115E59",
        focus="#B45309",
        link="#0F766E",
    )


def build_stylesheet(theme: str) -> str:
    colors = theme_colors(theme)
    return f"""
        QMainWindow {{
            background: {colors.background};
            color: {colors.text};
        }}
        QWidget#rootWidget {{
            background: {colors.background};
            color: {colors.text};
        }}
        QWidget#headerWidget {{
            background: {PIXO_NAVY if theme == "dark" else PIXO_WHITE};
            border: 1px solid {colors.border};
            border-radius: 8px;
        }}
        QWidget#toolbarWidget, QWidget#toolbarGroup {{
            background: transparent;
            border: 0;
        }}
        QLabel#toolbarGroupTitle {{
            color: {colors.secondary};
            font-size: 11px;
            font-weight: 700;
        }}
        QLabel {{
            color: {colors.text};
        }}
        QLabel#aboutNote {{
            color: {colors.secondary};
            font-size: 12px;
        }}
        QLabel#logoLabel {{
            background: transparent;
            border: 0;
            color: {PIXO_TEAL};
            font-size: 24px;
            font-weight: 800;
        }}
        QLabel#titleLogoLabel {{
            color: {colors.text};
            font-size: 24px;
            font-weight: 800;
        }}
        QLabel#printPreview {{
            background: {colors.panel};
            border: 1px solid {colors.border};
            border-radius: 8px;
        }}
        QFrame#cropHint {{
            background: {colors.panel_alt};
            border: 1px solid {colors.accent};
            border-radius: 7px;
        }}
        QLabel#cropHintIcon {{
            background: transparent;
            border: 0;
        }}
        QLabel#cropHintText {{
            background: transparent;
            color: {colors.text};
            font-weight: 600;
        }}
        QGraphicsView {{
            background: {colors.preview_background};
            border: 1px solid {colors.border};
            border-radius: 8px;
        }}
        QPushButton {{
            background: {colors.panel_alt};
            color: {colors.text};
            border: 1px solid {colors.border};
            border-radius: 6px;
            padding: 6px 10px;
            font-weight: 600;
        }}
        QPushButton:hover {{
            border-color: {PIXO_TEAL};
            color: {colors.link};
        }}
        QPushButton:focus {{
            border: 2px solid {colors.focus};
            padding: 5px 9px;
        }}
        QPushButton:pressed {{
            background: {colors.menu_selection};
        }}
        QPushButton:disabled {{
            background: {colors.disabled_background};
            color: {colors.disabled_text};
            border-color: {colors.border};
        }}
        QPushButton#primaryButton {{
            background: {PIXO_NAVY};
            color: {PIXO_WHITE};
            border-color: {PIXO_NAVY};
        }}
        QPushButton#primaryButton:hover {{
            background: #1D3A66;
            border-color: {PIXO_TEAL};
            color: {PIXO_WHITE};
        }}
        QPushButton#accentButton {{
            background: {colors.accent};
            color: {PIXO_WHITE};
            border-color: {colors.accent};
        }}
        QPushButton#accentButton:hover {{
            background: {colors.accent_hover};
            border-color: {colors.focus};
            color: {PIXO_WHITE};
        }}
        QToolButton#compactToolButton {{
            background: {colors.panel_alt};
            color: {colors.text};
            border: 1px solid {colors.border};
            border-radius: 6px;
            padding: 4px;
        }}
        QToolButton#compactToolButton:hover {{
            border-color: {PIXO_TEAL};
            background: {colors.menu_selection};
        }}
        QToolButton#compactToolButton:focus {{
            border: 2px solid {colors.focus};
            padding: 3px;
        }}
        QToolButton#compactToolButton:disabled {{
            background: {colors.disabled_background};
            border-color: {colors.border};
        }}
        QToolButton#orientationButton {{
            background: {colors.panel_alt};
            color: {colors.text};
            border: 1px solid {colors.border};
            border-radius: 0;
            padding: 5px;
        }}
        QToolButton#orientationButton[segmentPosition="first"] {{
            border-top-left-radius: 6px;
            border-bottom-left-radius: 6px;
        }}
        QToolButton#orientationButton[segmentPosition="last"] {{
            border-top-right-radius: 6px;
            border-bottom-right-radius: 6px;
        }}
        QToolButton#orientationButton:hover {{
            border-color: {PIXO_TEAL};
            background: {colors.menu_selection};
        }}
        QToolButton#orientationButton:checked {{
            background: {colors.menu_selection};
            color: {colors.menu_selection_text};
            border: 2px solid {colors.accent};
            padding: 4px;
        }}
        QComboBox {{
            background: {colors.input_background};
            color: {colors.text};
            border: 1px solid {colors.border};
            border-radius: 6px;
            padding: 5px 8px;
            selection-background-color: {colors.accent};
            selection-color: {PIXO_WHITE};
        }}
        QSpinBox {{
            background: {colors.input_background};
            color: {colors.text};
            border: 1px solid {colors.border};
            border-radius: 6px;
            min-height: 20px;
            padding: 5px 26px 5px 10px;
            selection-background-color: {colors.accent};
            selection-color: {PIXO_WHITE};
        }}
        QSpinBox:hover {{
            border-color: {PIXO_TEAL};
        }}
        QComboBox:focus, QSpinBox:focus {{
            border: 2px solid {colors.focus};
        }}
        QSpinBox::up-button, QSpinBox::down-button {{
            subcontrol-origin: border;
            width: 24px;
            background: {colors.panel_alt};
            border-left: 1px solid {colors.border};
        }}
        QSpinBox::up-button {{
            subcontrol-position: top right;
            border-bottom: 1px solid {colors.border};
            border-top-right-radius: 5px;
        }}
        QSpinBox::down-button {{
            subcontrol-position: bottom right;
            border-bottom-right-radius: 5px;
        }}
        QSpinBox::up-button:hover, QSpinBox::down-button:hover {{
            background: {colors.menu_selection};
            border-left-color: {PIXO_TEAL};
        }}
        QSpinBox::up-button:pressed, QSpinBox::down-button:pressed {{
            background: {colors.accent};
        }}
        QSpinBox::up-button:disabled, QSpinBox::down-button:disabled {{
            background: {colors.disabled_background};
            border-left-color: {colors.border};
        }}
        QSpinBox::up-arrow, QSpinBox::down-arrow {{
            image: none;
            width: 0;
            height: 0;
        }}
        QComboBox QAbstractItemView {{
            background: {colors.menu_background};
            color: {colors.text};
            border: 1px solid {colors.border};
            outline: 0;
            padding: 4px;
            selection-background-color: {colors.menu_selection};
            selection-color: {colors.menu_selection_text};
        }}
        QComboBox QAbstractItemView::item {{
            min-height: 26px;
            padding: 4px 8px;
        }}
        QComboBox QAbstractItemView::item:selected {{
            background: {colors.menu_selection};
            color: {colors.menu_selection_text};
        }}
        QComboBox QAbstractItemView::item:disabled {{
            color: {colors.disabled_text};
            background: {colors.disabled_background};
        }}
        QStatusBar {{
            background: {colors.panel};
            color: {colors.secondary};
            border-top: 1px solid {colors.border};
        }}
        QLabel#kofiSponsorLabel {{
            color: {colors.link};
            padding: 0 8px;
            font-weight: 700;
        }}
        QLabel#kofiSponsorLabel a {{
            color: {colors.link};
            text-decoration: none;
        }}
        QDialog {{
            background: {colors.background};
            color: {colors.text};
        }}
        QGroupBox {{
            color: {colors.text};
            border: 1px solid {colors.border};
            border-radius: 8px;
            margin-top: 12px;
            padding: 10px;
            font-weight: 700;
        }}
        QGroupBox::title {{
            subcontrol-origin: margin;
            left: 12px;
            padding: 0 6px;
            color: {colors.link};
        }}
        QCheckBox {{
            color: {colors.text};
            spacing: 8px;
        }}
        QSplitter::handle {{
            background: transparent;
            width: 8px;
        }}
        QToolTip {{
            background: {colors.menu_background};
            color: {colors.text};
            border: 1px solid {colors.border};
            padding: 4px 6px;
        }}
    """
