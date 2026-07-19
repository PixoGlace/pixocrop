from __future__ import annotations

import json
import re
import sys
import threading
import urllib.error
import urllib.request
from pathlib import Path

import fitz
from PySide6.QtCore import QEvent, QMarginsF, QObject, QPointF, QRect, QRectF, QSettings, QSize, QSizeF, Qt, QTimer, QUrl, Signal
from PySide6.QtGui import QAction, QBrush, QColor, QDesktopServices, QIcon, QImage, QKeySequence, QPageLayout, QPageSize, QPainter, QPen, QPixmap
from PySide6.QtPrintSupport import QPrinter, QPrinterInfo
from PySide6.QtWidgets import (
    QApplication,
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QGraphicsRectItem,
    QGraphicsScene,
    QGraphicsView,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QSplitter,
    QStatusBar,
    QStyle,
    QStyleOptionSpinBox,
    QSizePolicy,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from pixocrop.detection import PdfRect, detect_all_pages
from pixocrop.pdf_ops import crop_pdf
from pixocrop.config import APP_NAME, DONATION_TEXT, DONATION_URL, KOFI_URL, PROJECT_LICENSE, PROJECT_URL, UPDATE_CHECK_URL, VERSION
from pixocrop.language_config import DEFAULT_LANGUAGE, LANGUAGES, is_rtl, translate
from pixocrop.theme import (
    PIXO_AMBER,
    PIXO_TEAL,
    build_stylesheet,
    theme_colors,
)

POINTS_PER_MM = 72 / 25.4


def app_root() -> Path:
    bundle_root = getattr(sys, "_MEIPASS", None)
    if bundle_root is not None:
        return Path(bundle_root)
    return Path(__file__).resolve().parents[2]


def asset_path(filename: str) -> Path:
    return app_root() / "assets" / filename


def themed_icon(filename: str = "logo_white.png") -> QIcon:
    path = asset_path(filename)
    if path.exists():
        return QIcon(str(path))
    return QIcon()


def app_text(language: str, key: str, **values: object) -> str:
    return translate(language, key, **values)


def normalized_version_parts(version: str) -> tuple[int, ...]:
    cleaned = version.strip().lstrip("vV")
    return tuple(int(part) for part in re.findall(r"\d+", cleaned))


def is_newer_version(latest_version: str, current_version: str) -> bool:
    latest_parts = normalized_version_parts(latest_version)
    current_parts = normalized_version_parts(current_version)
    max_length = max(len(latest_parts), len(current_parts))
    latest_parts = latest_parts + (0,) * (max_length - len(latest_parts))
    current_parts = current_parts + (0,) * (max_length - len(current_parts))
    return latest_parts > current_parts


class UpdateChecker(QObject):
    update_available = Signal(str, str)
    no_update_available = Signal()
    check_failed = Signal()
    check_finished = Signal(bool)

    def check_async(self, *, manual: bool = False) -> None:
        thread = threading.Thread(target=self._check, args=(manual,), daemon=True)
        thread.start()

    def _check(self, manual: bool) -> None:
        try:
            request = urllib.request.Request(
                UPDATE_CHECK_URL,
                headers={
                    "Accept": "application/vnd.github+json",
                    "User-Agent": f"{APP_NAME}/{VERSION}",
                },
            )
            with urllib.request.urlopen(request, timeout=6) as response:
                payload = json.loads(response.read().decode("utf-8"))

            latest_version = str(payload.get("tag_name") or "").strip()
            download_url = str(payload.get("html_url") or PROJECT_URL).strip()
            if latest_version and is_newer_version(latest_version, VERSION):
                self.update_available.emit(latest_version, download_url)
            elif manual:
                self.no_update_available.emit()
        except (OSError, urllib.error.URLError, json.JSONDecodeError, ValueError):
            if manual:
                self.check_failed.emit()
        finally:
            self.check_finished.emit(manual)


class AboutDialog(QDialog):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        language = getattr(parent, "language", DEFAULT_LANGUAGE)
        self.setLayoutDirection(
            Qt.LayoutDirection.RightToLeft
            if is_rtl(language)
            else Qt.LayoutDirection.LeftToRight
        )
        self.setWindowTitle(app_text(language, "about_app", app_name=APP_NAME))
        self.setWindowIcon(themed_icon())
        self.resize(560, 520)

        logo_label = QLabel()
        logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        theme = getattr(parent, "current_theme", "light")
        logo_variant = "dark" if theme == "dark" else "white"
        logo = QPixmap(str(asset_path(f"title_{logo_variant}.png")))
        if not logo.isNull():
            ratio = max(1.0, self.devicePixelRatioF())
            scaled_logo = logo.scaledToHeight(
                int(76 * ratio),
                Qt.TransformationMode.SmoothTransformation,
            )
            scaled_logo.setDevicePixelRatio(ratio)
            logo_label.setPixmap(scaled_logo)
        else:
            logo_label.setText(APP_NAME)

        project_link = (
            f'<a href="{PROJECT_URL}">{PROJECT_URL}</a>'
            if PROJECT_URL
            else "Lien du projet non configuré."
        )
        donation_link = (
            f'<a href="{DONATION_URL}">{DONATION_TEXT}</a>'
            if DONATION_URL
            else "Lien de donation non configuré."
        )

        details = QLabel(
            f"""
            <h2>{APP_NAME} {VERSION}</h2>
            <p>{app_text(language, "about_description")}</p>

            <h3>{app_text(language, "about_license")}</h3>
            <p>{app_text(language, "about_license_text", license=PROJECT_LICENSE)}</p>

            <h3>{app_text(language, "about_donation")}</h3>
            <p>{donation_link}</p>

            <h3>{app_text(language, "about_credits")}</h3>
            <p>
                Interface : PySide6 / Qt<br>
                Lecture et rendu PDF : PyMuPDF<br>
                Traitement image : Pillow, NumPy<br>
                Packaging : PyInstaller
            </p>

            <h3>{app_text(language, "about_project")}</h3>
            <p>{project_link}</p>
            """
        )
        details.setTextFormat(Qt.TextFormat.RichText)
        details.setOpenExternalLinks(True)
        details.setWordWrap(True)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout()
        layout.setContentsMargins(22, 22, 22, 22)
        layout.setSpacing(14)
        layout.addWidget(logo_label)
        layout.addWidget(details)
        layout.addWidget(buttons)
        self.setLayout(layout)


class SettingsDialog(QDialog):
    def __init__(self, parent: "MainWindow") -> None:
        super().__init__(parent)
        self.window = parent
        self.setWindowTitle(parent.t("settings"))
        self.setWindowIcon(themed_icon())
        self.setLayoutDirection(parent.layoutDirection())
        self.resize(420, 180)

        self.language_combo = QComboBox()
        for code, language in LANGUAGES.items():
            self.language_combo.addItem(language["name"], code)
        current_index = self.language_combo.findData(parent.language)
        if current_index >= 0:
            self.language_combo.setCurrentIndex(current_index)

        form = QFormLayout()
        form.addRow(parent.t("settings_language"), self.language_combo)

        self.theme_combo = QComboBox()
        self.theme_combo.addItem(parent.t("theme_light"), "light")
        self.theme_combo.addItem(parent.t("theme_dark"), "dark")
        current_theme_index = self.theme_combo.findData(parent.current_theme)
        if current_theme_index >= 0:
            self.theme_combo.setCurrentIndex(current_theme_index)
        form.addRow(parent.t("theme"), self.theme_combo)

        note = QLabel(parent.t("settings_note"))
        note.setWordWrap(True)

        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)

        layout = QVBoxLayout()
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)
        layout.addLayout(form)
        layout.addWidget(note)
        layout.addWidget(self.button_box)
        self.setLayout(layout)

    def selected_language(self) -> str:
        language = self.language_combo.currentData()
        return language if language in LANGUAGES else DEFAULT_LANGUAGE

    def selected_theme(self) -> str:
        theme = self.theme_combo.currentData()
        return theme if theme in {"light", "dark"} else "light"


class PreviewView(QGraphicsView):
    def __init__(self, window: "MainWindow") -> None:
        super().__init__()
        self.window = window
        self.interaction_mode: str | None = None
        self.selection_start: QPointF | None = None
        self.selection_item: QGraphicsRectItem | None = None
        self.move_start: QPointF | None = None
        self.move_original: QRectF | None = None
        self.setRenderHint(QPainter.Antialiasing)
        self.setDragMode(QGraphicsView.NoDrag)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setAcceptDrops(True)
        self.viewport().setAcceptDrops(True)
        self.viewport().installEventFilter(self)

    def dragEnterEvent(self, event) -> None:  # type: ignore[no-untyped-def]
        if self.window.pdf_path_from_drop(event.mimeData()) is not None:
            event.acceptProposedAction()
            return
        super().dragEnterEvent(event)

    def dragMoveEvent(self, event) -> None:  # type: ignore[no-untyped-def]
        if self.window.pdf_path_from_drop(event.mimeData()) is not None:
            event.acceptProposedAction()
            return
        super().dragMoveEvent(event)

    def dropEvent(self, event) -> None:  # type: ignore[no-untyped-def]
        path = self.window.pdf_path_from_drop(event.mimeData())
        if path is not None:
            self.window.open_pdf_path(path)
            event.acceptProposedAction()
            return
        super().dropEvent(event)

    def eventFilter(self, watched, event) -> bool:  # type: ignore[no-untyped-def]
        if watched is self.viewport() and event.type() in {
            QEvent.DragEnter,
            QEvent.DragMove,
            QEvent.Drop,
        }:
            path = self.window.pdf_path_from_drop(event.mimeData())
            if path is None:
                return False
            event.acceptProposedAction()
            if event.type() == QEvent.Drop:
                self.window.open_pdf_path(path)
            return True
        return super().eventFilter(watched, event)

    def mousePressEvent(self, event) -> None:  # type: ignore[no-untyped-def]
        if event.button() == Qt.LeftButton and self.window.document is not None:
            scene_pos = self.mapToScene(event.position().toPoint())
            current_rect = self.window.current_scene_rect()
            if current_rect is not None and current_rect.contains(scene_pos):
                self.interaction_mode = "move"
                self.move_start = scene_pos
                self.move_original = current_rect
                self.setCursor(Qt.ClosedHandCursor)
                return

            self.interaction_mode = "draw"
            self.selection_start = scene_pos
            self.selection_item = self.scene().addRect(
                QRectF(self.selection_start, self.selection_start),
                QPen(QColor(PIXO_AMBER), 2, Qt.PenStyle.DashLine),
                QBrush(QColor(245, 158, 11, 45)),
            )
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:  # type: ignore[no-untyped-def]
        if self.interaction_mode == "draw" and self.selection_start is not None and self.selection_item is not None:
            current = self.mapToScene(event.position().toPoint())
            rect = QRectF(self.selection_start, current).normalized()
            self.selection_item.setRect(self.window.clamp_scene_rect(rect))
            return

        if self.interaction_mode == "move" and self.move_start is not None and self.move_original is not None:
            current = self.mapToScene(event.position().toPoint())
            delta = current - self.move_start
            moved = self.window.clamp_scene_rect(self.move_original.translated(delta))
            if self.window.rect_item is not None:
                self.window.rect_item.setRect(moved)
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:  # type: ignore[no-untyped-def]
        if self.interaction_mode == "draw" and self.selection_start is not None and self.selection_item is not None:
            rect = self.selection_item.rect()
            self.scene().removeItem(self.selection_item)
            self.interaction_mode = None
            self.selection_start = None
            self.selection_item = None
            if rect.width() >= 8 and rect.height() >= 8:
                self.window.set_current_crop_from_scene(rect)
            return

        if self.interaction_mode == "move" and self.move_start is not None and self.move_original is not None:
            current = self.mapToScene(event.position().toPoint())
            delta = current - self.move_start
            rect = self.window.clamp_scene_rect(self.move_original.translated(delta))
            self.interaction_mode = None
            self.move_start = None
            self.move_original = None
            self.unsetCursor()
            self.window.set_current_crop_from_scene(rect)
            return
        super().mouseReleaseEvent(event)

    def wheelEvent(self, event) -> None:  # type: ignore[no-untyped-def]
        if event.modifiers() & Qt.ControlModifier:
            factor = 1.15 if event.angleDelta().y() > 0 else 0.87
            self.window.zoom_view(factor)
            event.accept()
            return
        super().wheelEvent(event)


class StyledSpinBox(QSpinBox):
    """Spin box with high-contrast chevrons independent of the platform style."""

    def paintEvent(self, event) -> None:  # type: ignore[no-untyped-def]
        super().paintEvent(event)

        option = QStyleOptionSpinBox()
        self.initStyleOption(option)
        colors = theme_colors(self._theme_name())
        glyph_color = colors.text if self.isEnabled() else colors.disabled_text

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        pen = QPen(QColor(glyph_color), 1.8)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)

        for subcontrol, points_up in (
            (QStyle.SubControl.SC_SpinBoxUp, True),
            (QStyle.SubControl.SC_SpinBoxDown, False),
        ):
            rect = self.style().subControlRect(
                QStyle.ComplexControl.CC_SpinBox,
                option,
                subcontrol,
                self,
            )
            if not rect.isValid() or rect.width() < 6 or rect.height() < 4:
                continue

            center = rect.center()
            half_width = min(4.0, max(2.5, (rect.width() - 8) / 2))
            rise = min(2.5, max(1.5, (rect.height() - 4) / 2))
            base_y = center.y() + (rise / 2 if points_up else -rise / 2)
            tip_y = center.y() + (-rise if points_up else rise)
            painter.drawLine(
                QPointF(center.x() - half_width, base_y),
                QPointF(center.x(), tip_y),
            )
            painter.drawLine(
                QPointF(center.x(), tip_y),
                QPointF(center.x() + half_width, base_y),
            )

        painter.end()

    def _theme_name(self) -> str:
        parent: QWidget | None = self
        while parent is not None:
            theme = getattr(parent, "current_theme", None)
            if theme in {"light", "dark"}:
                return theme
            parent = parent.parentWidget()
        return "light"


class PrintOptionsDialog(QDialog):
    PRINTER_DEFAULT = "printer_default"

    PREVIEW_ZOOM = 2.0
    PREVIEW_CANVAS_HEIGHT = 1000
    PREVIEW_MARGIN = 28
    PREVIEW_PRINTABLE_MARGIN = 36

    ORIENTATION_AUTO = 0
    ORIENTATION_PORTRAIT = 1
    ORIENTATION_LANDSCAPE = 2
    ORIENTATION_DEFAULT = 3

    PAGE_ALL = "all"
    PAGE_CURRENT = "current"

    def __init__(
        self,
        parent: "MainWindow",
        document: fitz.Document,
        rects: list[PdfRect],
        current_page: int,
    ) -> None:
        super().__init__(parent)

        self.window = parent
        self.document = document
        self.rects = rects
        self.current_page = self._clamp_page_index(current_page)
        self.printers = QPrinterInfo.availablePrinters()
        self._preview_image: QImage | None = None
        self.t = parent.t
        self.setLayoutDirection(parent.layoutDirection())

        self.setWindowTitle(self.t("print_title"))
        self.setWindowIcon(themed_icon())
        self.resize(920, 680)

        self._build_ui()
        self._connect_signals()
        self.update_page_controls()
        self.update_preview()

    # ---------------------------------------------------------------------
    # UI
    # ---------------------------------------------------------------------

    def _build_ui(self) -> None:
        self.preview_label = QLabel()
        self.preview_label.setObjectName("printPreview")
        self.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_label.setMinimumSize(360, 360)
        self.preview_label.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding,
        )

        self.printer_combo = self._create_printer_combo()
        self.page_combo = self._create_page_combo()
        self.preview_page_spin = self._create_preview_page_spin()
        self.copies_spin = self._create_copies_spin()
        self.color_combo = self._create_color_combo()
        self.orientation_group, self.orientation_buttons = (
            self._create_orientation_selector()
        )
        self.paper_size_combo = self._create_paper_size_combo()
        self.resolution_combo = self._create_resolution_combo()
        self.duplex_combo = self._create_duplex_combo()
        self.zoom_spin = self._create_zoom_spin()

        self.fit_page_check = QCheckBox(self.t("fit_to_page"))
        self.fit_page_check.setChecked(True)

        form = QFormLayout()
        form.addRow(self.t("printer"), self.printer_combo)
        form.addRow(self.t("page"), self.page_combo)
        form.addRow(self.t("preview_page"), self.preview_page_spin)
        form.addRow(self.t("copies"), self.copies_spin)
        form.addRow(self.t("color"), self.color_combo)
        form.addRow(self.t("orientation"), self.orientation_buttons)
        form.addRow(self.t("paper_size"), self.paper_size_combo)
        form.addRow(self.t("quality"), self.resolution_combo)
        form.addRow(self.t("duplex"), self.duplex_combo)
        form.addRow(self.t("zoom"), self.zoom_spin)
        form.addRow("", self.fit_page_check)

        options_group = QGroupBox(self.t("print_options"))
        options_group.setLayout(form)

        self.button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Cancel)
        self.print_button = self.button_box.addButton(
            self.t("print"),
            QDialogButtonBox.ButtonRole.AcceptRole,
        )
        self.print_button.setObjectName("accentButton")
        self.print_button.setEnabled(bool(self.printers) and bool(self.rects))

        right_layout = QVBoxLayout()
        right_layout.addWidget(options_group)
        right_layout.addStretch()
        right_layout.addWidget(self.button_box)

        options_widget = QWidget()
        options_widget.setLayout(right_layout)
        options_widget.setMinimumWidth(330)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(self.preview_label)
        splitter.addWidget(options_widget)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 0)
        splitter.setCollapsible(0, False)
        splitter.setCollapsible(1, False)
        splitter.setSizes([560, 340])

        layout = QHBoxLayout()
        layout.setContentsMargins(14, 14, 14, 14)
        layout.addWidget(splitter)

        self.setLayout(layout)

    def _create_printer_combo(self) -> QComboBox:
        combo = QComboBox()
        self._configure_combo(combo, minimum_contents=24)

        if not self.printers:
            combo.addItem(self.t("no_printer"))
            combo.setEnabled(False)
            return combo

        for printer in self.printers:
            combo.addItem(printer.printerName(), printer)

        default_printer = QPrinterInfo.defaultPrinter()
        if default_printer and default_printer.printerName():
            index = combo.findText(default_printer.printerName())
            if index >= 0:
                combo.setCurrentIndex(index)

        return combo

    def _create_page_combo(self) -> QComboBox:
        combo = QComboBox()
        self._configure_combo(combo)
        combo.addItem(self.t("all_pages"), self.PAGE_ALL)
        combo.addItem(self.t("current_page"), self.PAGE_CURRENT)
        return combo

    def _create_preview_page_spin(self) -> QSpinBox:
        spin = StyledSpinBox()
        spin.setRange(1, max(1, len(self.rects)))
        spin.setValue(self.current_page + 1)
        spin.setEnabled(bool(self.rects))
        return spin

    def _create_copies_spin(self) -> QSpinBox:
        spin = StyledSpinBox()
        spin.setRange(1, 99)
        spin.setValue(1)
        return spin

    def _create_color_combo(self) -> QComboBox:
        combo = QComboBox()
        self._configure_combo(combo)
        combo.addItem(self.t("printer_default"), self.PRINTER_DEFAULT)
        combo.addItem(self.t("color"), QPrinter.ColorMode.Color)
        combo.addItem(self.t("black_white"), QPrinter.ColorMode.GrayScale)
        return combo

    def _create_paper_size_combo(self) -> QComboBox:
        combo = QComboBox()
        self._configure_combo(combo, minimum_contents=22)
        self._populate_paper_size_combo(combo)
        return combo

    def _populate_paper_size_combo(self, combo: QComboBox | None = None) -> None:
        combo = combo or self.paper_size_combo
        current_name = combo.currentText()
        combo.blockSignals(True)
        combo.clear()
        combo.addItem(self.t("printer_default"), self.PRINTER_DEFAULT)

        seen: set[str] = {self.PRINTER_DEFAULT}
        printer_info = self.selected_printer_info()
        if printer_info is not None:
            for page_size in printer_info.supportedPageSizes():
                if not page_size.isValid():
                    continue
                key = page_size.key() or page_size.name()
                if key in seen:
                    continue
                seen.add(key)
                size_mm = page_size.size(QPageSize.Unit.Millimeter)
                label = f"{page_size.name()} ({size_mm.width():.0f} × {size_mm.height():.0f} mm)"
                combo.addItem(label, page_size)

        for label, value in (
            ("A4", QPageSize.PageSizeId.A4),
            ("A5", QPageSize.PageSizeId.A5),
            ("Letter", QPageSize.PageSizeId.Letter),
            ("10 × 15 cm", QPageSize.PageSizeId.A6),
            ("Thermique 7 × 5 cm", ("custom_mm", 70.0, 50.0, "Thermique 7 x 5 cm")),
            ("Thermique 7 × 5 in", ("custom_in", 7.0, 5.0, "Thermique 7 x 5 in")),
        ):
            if label not in seen:
                combo.addItem(label, value)
                seen.add(label)

        if current_name:
            index = combo.findText(current_name)
            if index >= 0:
                combo.setCurrentIndex(index)

        combo.blockSignals(False)

    def _create_resolution_combo(self) -> QComboBox:
        combo = QComboBox()
        self._configure_combo(combo)
        combo.addItem(self.t("printer_default"), self.PRINTER_DEFAULT)
        combo.addItem(self.t("quality_draft"), 150)
        combo.addItem(self.t("quality_standard"), 300)
        combo.addItem(self.t("quality_high"), 600)
        return combo

    def _create_duplex_combo(self) -> QComboBox:
        combo = QComboBox()
        self._configure_combo(combo)
        combo.addItem(self.t("printer_default"), self.PRINTER_DEFAULT)
        combo.addItem(self.t("duplex_none"), QPrinter.DuplexMode.DuplexNone)
        combo.addItem(self.t("duplex_long"), QPrinter.DuplexMode.DuplexLongSide)
        combo.addItem(self.t("duplex_short"), QPrinter.DuplexMode.DuplexShortSide)
        return combo

    def _create_zoom_spin(self) -> QSpinBox:
        spin = StyledSpinBox()
        spin.setRange(25, 300)
        spin.setSingleStep(5)
        spin.setValue(100)
        spin.setSuffix(" %")
        return spin

    @staticmethod
    def _configure_combo(combo: QComboBox, *, minimum_contents: int = 18) -> None:
        combo.setSizeAdjustPolicy(
            QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon
        )
        combo.setMinimumContentsLength(minimum_contents)

    def _create_orientation_selector(self) -> tuple[QButtonGroup, QWidget]:
        group = QButtonGroup(self)
        group.setExclusive(True)

        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        buttons = [
            self.create_orientation_button(
                self.t("orientation_default"), "default", self.ORIENTATION_DEFAULT
            ),
            self.create_orientation_button(self.t("orientation_auto"), "auto", self.ORIENTATION_AUTO),
            self.create_orientation_button(
                self.t("orientation_portrait"), "portrait", self.ORIENTATION_PORTRAIT
            ),
            self.create_orientation_button(
                self.t("orientation_landscape"), "landscape", self.ORIENTATION_LANDSCAPE
            ),
        ]

        for index, button in enumerate(buttons):
            if index == 0:
                button.setProperty("segmentPosition", "first")
            elif index == len(buttons) - 1:
                button.setProperty("segmentPosition", "last")
            else:
                button.setProperty("segmentPosition", "middle")
            group.addButton(button, button.property("orientation_id"))
            layout.addWidget(button)

        buttons[0].setChecked(True)

        return group, container

    def create_orientation_button(
        self,
        text: str,
        icon_kind: str,
        button_id: int,
    ) -> QToolButton:
        button = QToolButton()
        button.setObjectName("orientationButton")
        button.setText(text)
        button.setToolTip(text)
        button.setAccessibleName(text)
        button.setIcon(self.orientation_icon(icon_kind))
        button.setIconSize(QSize(30, 30))
        button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
        button.setCheckable(True)
        button.setMinimumSize(44, 44)
        button.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Fixed,
        )
        button.setProperty("orientation_id", button_id)
        return button

    # ---------------------------------------------------------------------
    # Signals
    # ---------------------------------------------------------------------

    def _connect_signals(self) -> None:
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)

        self.preview_page_spin.valueChanged.connect(self.update_preview)
        self.printer_combo.currentIndexChanged.connect(self.update_printer_paper_sizes)
        self.page_combo.currentIndexChanged.connect(self.update_page_controls)
        self.color_combo.currentIndexChanged.connect(self.update_preview)
        self.orientation_group.idClicked.connect(lambda _: self.update_preview())
        self.paper_size_combo.currentIndexChanged.connect(self.update_preview)
        self.resolution_combo.currentIndexChanged.connect(self.update_preview)
        self.zoom_spin.valueChanged.connect(self.update_preview)
        self.fit_page_check.toggled.connect(self.update_preview)

    # ---------------------------------------------------------------------
    # Preview
    # ---------------------------------------------------------------------

    def update_page_controls(self) -> None:
        show_all_pages = self.page_combo.currentData() == self.PAGE_ALL

        self.preview_page_spin.setEnabled(show_all_pages and bool(self.rects))

        if not show_all_pages:
            self.preview_page_spin.blockSignals(True)
            self.preview_page_spin.setValue(self.current_page + 1)
            self.preview_page_spin.blockSignals(False)

        self.update_preview()

    def update_printer_paper_sizes(self) -> None:
        self._populate_paper_size_combo()
        self.update_preview()

    def update_preview(self) -> None:
        if not self.rects:
            self.preview_label.setText(self.t("empty_preview"))
            self.preview_label.setPixmap(QPixmap())
            self._preview_image = None
            return

        page_index = self._current_preview_page_index()

        try:
            self._preview_image = self.render_print_preview(page_index)
        except Exception as error:
            self.preview_label.setText(self.t("preview_error", error=error))
            self.preview_label.setPixmap(QPixmap())
            self._preview_image = None
            return

        self._refresh_preview_pixmap()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._refresh_preview_pixmap()

    def _refresh_preview_pixmap(self) -> None:
        if self._preview_image is None or self._preview_image.isNull():
            return

        pixmap = QPixmap.fromImage(self._preview_image)
        self.preview_label.setPixmap(
            pixmap.scaled(
                self.preview_label.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        )

    def render_print_preview(self, page_index: int) -> QImage:
        page_index = self._clamp_page_index(page_index)
        rect = self.rects[page_index]

        clip_image = self.window.render_clip_image(
            page_index,
            rect,
            zoom=self.PREVIEW_ZOOM,
        )

        if clip_image.isNull():
            raise RuntimeError("image de découpe vide")

        if self.effective_color_mode() == QPrinter.ColorMode.GrayScale:
            clip_image = clip_image.convertToFormat(QImage.Format.Format_Grayscale8)

        page_width, page_height = self._paper_dimensions_points()
        canvas = self._create_preview_canvas(page_width, page_height)

        painter = QPainter(canvas)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        paper_rect = self._paper_rect(canvas)
        printable_rect = paper_rect.adjusted(
            self.PREVIEW_PRINTABLE_MARGIN,
            self.PREVIEW_PRINTABLE_MARGIN,
            -self.PREVIEW_PRINTABLE_MARGIN,
            -self.PREVIEW_PRINTABLE_MARGIN,
        )

        painter.fillRect(paper_rect, Qt.GlobalColor.white)
        painter.setPen(QPen(QColor(190, 190, 190), 2))
        painter.drawRect(paper_rect)

        target_rect = self._compute_image_target_rect(
            clip_image=clip_image,
            source_rect=rect,
            paper_rect=paper_rect,
            printable_rect=printable_rect,
            page_width=page_width,
            page_height=page_height,
        )

        painter.drawImage(target_rect, clip_image)
        painter.end()

        return canvas

    def _create_preview_canvas(self, page_width: float, page_height: float) -> QImage:
        canvas_height = self.PREVIEW_CANVAS_HEIGHT
        canvas_width = max(1, int(canvas_height * page_width / page_height))

        canvas = QImage(
            canvas_width,
            canvas_height,
            QImage.Format.Format_RGB32,
        )
        canvas.fill(QColor(238, 238, 238))

        return canvas

    def _paper_rect(self, canvas: QImage) -> QRect:
        margin = self.PREVIEW_MARGIN

        return QRect(
            margin,
            margin,
            max(1, canvas.width() - margin * 2),
            max(1, canvas.height() - margin * 2),
        )

    def _compute_image_target_rect(
        self,
        *,
        clip_image: QImage,
        source_rect: PdfRect,
        paper_rect: QRect,
        printable_rect: QRect,
        page_width: float,
        page_height: float,
    ) -> QRect:
        if self.fit_to_page():
            scale = min(
                printable_rect.width() / clip_image.width(),
                printable_rect.height() / clip_image.height(),
            )
            image_width = max(1, int(clip_image.width() * scale))
            image_height = max(1, int(clip_image.height() * scale))
        else:
            source_width = max(1.0, float(source_rect.x1 - source_rect.x0))
            source_height = max(1.0, float(source_rect.y1 - source_rect.y0))

            image_width = max(1, int(source_width / page_width * paper_rect.width()))
            image_height = max(
                1, int(source_height / page_height * paper_rect.height())
            )

            if (
                image_width > printable_rect.width()
                or image_height > printable_rect.height()
            ):
                scale = min(
                    printable_rect.width() / image_width,
                    printable_rect.height() / image_height,
                )
                image_width = max(1, int(image_width * scale))
            image_height = max(1, int(image_height * scale))

        zoom = self.zoom_factor()
        image_width = max(1, int(image_width * zoom))
        image_height = max(1, int(image_height * zoom))

        return QRect(
            printable_rect.x() + (printable_rect.width() - image_width) // 2,
            printable_rect.y() + (printable_rect.height() - image_height) // 2,
            image_width,
            image_height,
        )

    # ---------------------------------------------------------------------
    # Icons
    # ---------------------------------------------------------------------

    def orientation_icon(self, icon_kind: str) -> QIcon:
        colors = theme_colors(self.window.current_theme)
        pixmap = QPixmap(64, 64)
        pixmap.fill(Qt.GlobalColor.transparent)

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QPen(QColor(colors.secondary), 2))
        painter.setBrush(QBrush(QColor(colors.input_background)))

        if icon_kind == "default":
            painter.drawRoundedRect(QRect(12, 22, 40, 25), 3, 3)
            painter.drawRect(QRect(20, 9, 24, 20))
            painter.drawRect(QRect(20, 38, 24, 16))
            painter.setBrush(QBrush(QColor(colors.accent)))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(QPointF(45, 30), 2.5, 2.5)
            painter.end()
            return QIcon(pixmap)

        if icon_kind == "auto":
            painter.drawRoundedRect(QRect(12, 18, 26, 34), 3, 3)
            painter.drawRoundedRect(QRect(25, 12, 30, 24), 3, 3)

            painter.setPen(QPen(QColor(colors.accent), 3))
            painter.drawLine(24, 44, 42, 26)
            painter.drawLine(42, 26, 42, 36)
            painter.drawLine(42, 26, 32, 26)

            painter.end()
            return QIcon(pixmap)

        if icon_kind == "landscape":
            page_rect = QRect(9, 17, 46, 30)
            line_y_values = (26, 34, 42)
        else:
            page_rect = QRect(17, 9, 30, 46)
            line_y_values = (22, 31, 40)

        painter.drawRoundedRect(page_rect, 3, 3)
        painter.setPen(QPen(QColor(colors.secondary), 2))

        for line_y in line_y_values:
            painter.drawLine(
                page_rect.left() + 7,
                line_y,
                page_rect.right() - 7,
                line_y,
            )

        painter.end()
        return QIcon(pixmap)

    # ---------------------------------------------------------------------
    # Public getters
    # ---------------------------------------------------------------------

    def selected_pages(self) -> list[int]:
        if not self.rects:
            return []

        if self.page_combo.currentData() == self.PAGE_CURRENT:
            return [self.current_page]

        return list(range(len(self.rects)))

    def printer_name(self) -> str:
        return self.printer_combo.currentText()

    def selected_printer_info(self) -> QPrinterInfo | None:
        data = self.printer_combo.currentData()
        if isinstance(data, QPrinterInfo):
            return data

        name = self.printer_name()
        for printer in self.printers:
            if printer.printerName() == name:
                return printer
        return None

    def color_mode(self) -> QPrinter.ColorMode | None:
        value = self.color_combo.currentData()
        if value == self.PRINTER_DEFAULT:
            return None
        return value

    def orientation(self) -> QPageLayout.Orientation | None:
        selected_orientation = self.orientation_group.checkedId()

        if selected_orientation == self.ORIENTATION_DEFAULT:
            return None

        if selected_orientation == self.ORIENTATION_LANDSCAPE:
            return QPageLayout.Orientation.Landscape

        if selected_orientation == self.ORIENTATION_PORTRAIT:
            return QPageLayout.Orientation.Portrait

        return self._auto_orientation()

    def duplex_mode(self) -> QPrinter.DuplexMode | None:
        value = self.duplex_combo.currentData()
        if value == self.PRINTER_DEFAULT:
            return None
        return value

    def paper_size(self) -> QPageSize | None:
        value = self.paper_size_combo.currentData()
        if value == self.PRINTER_DEFAULT:
            return None
        if isinstance(value, QPageSize):
            return value
        if isinstance(value, tuple):
            kind, width, height, name = value
            unit = QPageSize.Unit.Millimeter if kind == "custom_mm" else QPageSize.Unit.Inch
            return QPageSize(QSizeF(width, height), unit, name)
        return QPageSize(value)

    def is_thermal_paper(self) -> bool:
        return isinstance(self.paper_size_combo.currentData(), tuple)

    def resolution(self) -> int | None:
        value = self.resolution_combo.currentData()
        if value == self.PRINTER_DEFAULT:
            return None
        return value

    def copies(self) -> int:
        return self.copies_spin.value()

    def fit_to_page(self) -> bool:
        return self.fit_page_check.isChecked()

    def zoom_factor(self) -> float:
        return self.zoom_spin.value() / 100

    def default_printer(self) -> QPrinter:
        printer_info = self.selected_printer_info()
        if printer_info is not None:
            return QPrinter(printer_info, QPrinter.PrinterMode.HighResolution)

        printer = QPrinter(QPrinter.PrinterMode.HighResolution)
        printer_name = self.printer_name()
        if printer_name:
            printer.setPrinterName(printer_name)
        return printer

    def effective_color_mode(self) -> QPrinter.ColorMode:
        return self.color_mode() or self.default_printer().colorMode()

    def effective_orientation(self) -> QPageLayout.Orientation:
        orientation = self.orientation()
        if orientation is not None:
            return orientation
        return self.default_printer().pageLayout().orientation()

    def effective_paper_size(self) -> QPageSize:
        paper_size = self.paper_size()
        if paper_size is not None:
            return paper_size

        page_size = self.default_printer().pageLayout().pageSize()
        if page_size.isValid():
            return page_size
        return QPageSize(QPageSize.PageSizeId.A4)

    def effective_resolution(self) -> int:
        resolution = self.resolution()
        if resolution is not None:
            return resolution
        return self.default_printer().resolution()

    # ---------------------------------------------------------------------
    # Helpers
    # ---------------------------------------------------------------------

    def _current_preview_page_index(self) -> int:
        if self.page_combo.currentData() == self.PAGE_CURRENT:
            return self.current_page

        return self._clamp_page_index(self.preview_page_spin.value() - 1)

    def _clamp_page_index(self, page_index: int) -> int:
        if not self.rects:
            return 0

        return max(0, min(page_index, len(self.rects) - 1))

    def _auto_orientation(self) -> QPageLayout.Orientation:
        pages = self.selected_pages()

        if not pages:
            return QPageLayout.Orientation.Portrait

        rect = self.rects[pages[0]]
        width = float(rect.x1 - rect.x0)
        height = float(rect.y1 - rect.y0)

        if width > height:
            return QPageLayout.Orientation.Landscape

        return QPageLayout.Orientation.Portrait

    def _paper_dimensions_points(self) -> tuple[float, float]:
        page_size = self.effective_paper_size().size(QPageSize.Unit.Point)

        width = float(page_size.width())
        height = float(page_size.height())

        if self.effective_orientation() == QPageLayout.Orientation.Landscape:
            return max(width, height), min(width, height)

        return min(width, height), max(width, height)


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(APP_NAME)
        self.setWindowIcon(themed_icon())
        self.resize(1100, 780)
        self.settings = QSettings("PixoGlace", APP_NAME)
        self.language = self._load_language()
        self.current_theme = self._load_theme()
        self.translatable_group_labels: list[tuple[QLabel, str]] = []
        self.update_checker: UpdateChecker | None = None

        self.pdf_path: Path | None = None
        self.document: fitz.Document | None = None
        self.detected_rects: list[PdfRect] = []
        self.render_zoom = 1.6
        self.auto_fit_view = True

        self.scene = QGraphicsScene(self)
        self.preview = PreviewView(self)
        self.preview.setScene(self.scene)
        self.rect_item: QGraphicsRectItem | None = None

        self.logo_label = QLabel()
        self.logo_label.setObjectName("logoLabel")
        self.logo_label.setFixedSize(48, 48)
        self.logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.title_logo_label = QLabel("pixoCrop")
        self.title_logo_label.setObjectName("titleLogoLabel")
        self.title_logo_label.setFixedSize(176, 48)
        self.title_logo_label.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        self.open_button = QPushButton()
        self.open_button.setObjectName("primaryButton")
        self.detect_button = QPushButton()
        self.apply_all_button = QPushButton()
        self.export_button = QPushButton()
        self.print_button = QPushButton()
        self.print_button.setObjectName("accentButton")
        self.previous_page_button = self._compact_tool_button()
        self.next_page_button = self._compact_tool_button()
        self.zoom_out_button = self._compact_tool_button()
        self.zoom_in_button = self._compact_tool_button()
        self.fit_view_button = self._compact_tool_button()
        for compact_button in (
            self.previous_page_button,
            self.next_page_button,
            self.zoom_out_button,
            self.zoom_in_button,
            self.fit_view_button,
        ):
            compact_button.setFixedSize(34, 34)
            compact_button.setIconSize(QSize(20, 20))
        self.page_spin = StyledSpinBox()
        self.page_spin.setMinimumWidth(72)
        self.page_spin.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.margin_spin = StyledSpinBox()
        self.margin_spin.setRange(0, 30)
        self.margin_spin.setValue(3)
        self.margin_spin.setSuffix(" mm")
        self.margin_spin.setMinimumWidth(92)
        self.margin_spin.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.page_label = QLabel("/ 0")
        self.status = QStatusBar()
        self.kofi_label = QLabel()
        self.kofi_label.setObjectName("kofiSponsorLabel")
        self.kofi_label.setOpenExternalLinks(True)
        self.setStatusBar(self.status)
        self.status.addPermanentWidget(self.kofi_label)

        self.asset_directories = self._candidate_asset_directories()
        self._build_layout()
        self._build_menu()
        self._connect_signals()
        self._set_document_actions_enabled(False)
        self.translate_ui()
        self.apply_theme(self.current_theme)
        self.status.showMessage(self.t("app_ready"))

    def t(self, key: str, **values: object) -> str:
        return app_text(self.language, key, **values)

    def _load_language(self) -> str:
        language = self.settings.value("language", DEFAULT_LANGUAGE, str)
        return language if language in LANGUAGES else DEFAULT_LANGUAGE

    def _load_theme(self) -> str:
        theme = self.settings.value("theme", "light", str)
        return theme if theme in {"light", "dark"} else "light"

    def _toolbar_group(self, title_key: str, rows: list[list[QWidget]]) -> QWidget:
        group = QWidget()
        group.setObjectName("toolbarGroup")

        layout = QVBoxLayout(group)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        title_label = QLabel(self.t(title_key))
        title_label.setObjectName("toolbarGroupTitle")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.translatable_group_labels.append((title_label, title_key))
        layout.addWidget(title_label)

        for row_widgets in rows:
            row = QHBoxLayout()
            row.setContentsMargins(0, 0, 0, 0)
            row.setSpacing(4)
            for widget in row_widgets:
                row.addWidget(widget)
            layout.addLayout(row)

        return group

    @staticmethod
    def _compact_tool_button() -> QToolButton:
        button = QToolButton()
        button.setObjectName("compactToolButton")
        button.setAutoRaise(False)
        return button

    def _build_layout(self) -> None:
        brand_text_layout = QVBoxLayout()
        brand_text_layout.setContentsMargins(0, 0, 0, 0)
        brand_text_layout.setSpacing(0)
        brand_text_layout.addWidget(self.title_logo_label)

        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(10, 8, 10, 8)
        header_layout.setSpacing(10)
        header_layout.addWidget(self.logo_label)
        header_layout.addLayout(brand_text_layout)

        self.header_widget = QWidget()
        self.header_widget.setObjectName("headerWidget")

        toolbar = QHBoxLayout()
        toolbar.setContentsMargins(0, 0, 0, 0)
        toolbar.setSpacing(8)

        toolbar.addStretch(1)
        toolbar.addWidget(self._toolbar_group("toolbar_file", [[self.open_button], [self.export_button]]))
        toolbar.addWidget(self._toolbar_group("toolbar_detection", [[self.detect_button], [self.apply_all_button]]))
        toolbar.addWidget(
            self._toolbar_group(
                "toolbar_page",
                [
                    [self.previous_page_button, self.next_page_button],
                    [self.page_spin, self.page_label],
                ],
            )
        )
        toolbar.addWidget(
            self._toolbar_group(
                "toolbar_view",
                [[self.zoom_out_button, self.fit_view_button, self.zoom_in_button]],
            )
        )
        toolbar.addWidget(self._toolbar_group("margin", [[self.margin_spin]]))
        toolbar.addWidget(self._toolbar_group("toolbar_output", [[self.print_button]]))
        toolbar.addStretch(1)

        self.toolbar_widget = QWidget()
        self.toolbar_widget.setObjectName("toolbarWidget")
        self.toolbar_widget.setLayout(toolbar)
        header_layout.addWidget(self.toolbar_widget, 1)
        self.header_widget.setLayout(header_layout)

        layout = QVBoxLayout()
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)
        layout.addWidget(self.header_widget)
        layout.addWidget(self.preview)

        root = QWidget()
        root.setObjectName("rootWidget")
        root.setLayout(layout)
        self.setCentralWidget(root)

    def _build_menu(self) -> None:
        menu_bar = self.menuBar()
        if sys.platform == "darwin":
            menu_bar.setNativeMenuBar(True)

        self.file_menu = menu_bar.addMenu(self.t("file_menu"))
        self.open_action = QAction(self.t("open"), self)
        self.open_action.setShortcut(QKeySequence.StandardKey.Open)
        self.open_action.triggered.connect(self.open_pdf)
        self.file_menu.addAction(self.open_action)

        self.export_action = QAction(self.t("export"), self)
        self.export_action.setShortcut(QKeySequence.StandardKey.SaveAs)
        self.export_action.triggered.connect(self.export_cropped)
        self.file_menu.addAction(self.export_action)

        self.print_action = QAction(self.t("print"), self)
        self.print_action.setShortcut(QKeySequence.StandardKey.Print)
        self.print_action.triggered.connect(self.print_cropped)
        self.file_menu.addAction(self.print_action)

        if sys.platform != "darwin":
            self.file_menu.addSeparator()

        self.quit_action = QAction(self.t("quit"), self)
        self.quit_action.setObjectName("quitAction")
        self.quit_action.setMenuRole(QAction.MenuRole.QuitRole)
        self.quit_action.setShortcut(QKeySequence.StandardKey.Quit)
        self.quit_action.triggered.connect(self.close)
        self.file_menu.addAction(self.quit_action)

        self.view_menu = menu_bar.addMenu(self.t("menu_view"))
        self.previous_page_action = QAction(self.t("view_previous"), self)
        self.previous_page_action.setShortcut(QKeySequence(Qt.Key.Key_PageUp))
        self.previous_page_action.triggered.connect(self.previous_page)
        self.view_menu.addAction(self.previous_page_action)

        self.next_page_action = QAction(self.t("view_next"), self)
        self.next_page_action.setShortcut(QKeySequence(Qt.Key.Key_PageDown))
        self.next_page_action.triggered.connect(self.next_page)
        self.view_menu.addAction(self.next_page_action)

        self.view_menu.addSeparator()

        self.zoom_in_action = QAction(self.t("zoom_in"), self)
        self.zoom_in_action.setShortcut(QKeySequence.StandardKey.ZoomIn)
        self.zoom_in_action.triggered.connect(lambda: self.zoom_view(1.15))
        self.view_menu.addAction(self.zoom_in_action)

        self.zoom_out_action = QAction(self.t("zoom_out"), self)
        self.zoom_out_action.setShortcut(QKeySequence.StandardKey.ZoomOut)
        self.zoom_out_action.triggered.connect(lambda: self.zoom_view(0.87))
        self.view_menu.addAction(self.zoom_out_action)

        self.fit_view_action = QAction(self.t("view_fit"), self)
        self.fit_view_action.setShortcut(QKeySequence(Qt.Modifier.CTRL | Qt.Key.Key_0))
        self.fit_view_action.triggered.connect(self.fit_current_page)
        self.view_menu.addAction(self.fit_view_action)

        self.tools_menu = menu_bar.addMenu(self.t("menu_tools"))
        self.detect_action = QAction(self.t("auto_detect"), self)
        self.detect_action.setShortcut(QKeySequence("Ctrl+D"))
        self.detect_action.triggered.connect(self.detect_labels)
        self.tools_menu.addAction(self.detect_action)

        self.apply_all_action = QAction(self.t("apply_all_action"), self)
        self.apply_all_action.triggered.connect(self.apply_current_crop_to_all_pages)
        self.tools_menu.addAction(self.apply_all_action)

        if sys.platform != "darwin":
            self.tools_menu.addSeparator()
        self.settings_action = QAction(self.t("menu_settings"), self)
        self.settings_action.setObjectName("settingsAction")
        self.settings_action.setMenuRole(QAction.MenuRole.PreferencesRole)
        self.settings_action.setShortcut(QKeySequence("Ctrl+,"))
        self.settings_action.triggered.connect(self.show_settings_dialog)
        self.tools_menu.addAction(self.settings_action)

        self.help_menu = menu_bar.addMenu(self.t("help_menu"))
        self.check_updates_action = QAction(self.t("check_updates"), self)
        self.check_updates_action.triggered.connect(self.check_for_updates_manually)
        self.help_menu.addAction(self.check_updates_action)

        if sys.platform != "darwin":
            self.help_menu.addSeparator()
        self.about_action = QAction(
            self.t("about_app", app_name=APP_NAME),
            self,
        )
        self.about_action.setObjectName("aboutAction")
        self.about_action.setMenuRole(QAction.MenuRole.AboutRole)
        self.about_action.triggered.connect(self.show_about_dialog)
        self.help_menu.addAction(self.about_action)

    def _connect_signals(self) -> None:
        self.open_button.clicked.connect(self.open_pdf)
        self.detect_button.clicked.connect(self.detect_labels)
        self.apply_all_button.clicked.connect(self.apply_current_crop_to_all_pages)
        self.export_button.clicked.connect(self.export_cropped)
        self.print_button.clicked.connect(self.print_cropped)
        self.previous_page_button.clicked.connect(self.previous_page)
        self.next_page_button.clicked.connect(self.next_page)
        self.zoom_out_button.clicked.connect(lambda: self.zoom_view(0.87))
        self.zoom_in_button.clicked.connect(lambda: self.zoom_view(1.15))
        self.fit_view_button.clicked.connect(self.fit_current_page)
        self.page_spin.valueChanged.connect(self._page_changed)
        self.margin_spin.valueChanged.connect(self.render_current_page)

    def show_about_dialog(self) -> None:
        AboutDialog(self).exec()

    def show_settings_dialog(self) -> None:
        dialog = SettingsDialog(self)
        if dialog.exec() != QDialog.Accepted:
            return
        self.set_language(dialog.selected_language())
        self.set_theme(dialog.selected_theme())

    def check_for_updates_on_startup(self) -> None:
        self.start_update_check(manual=False)

    def check_for_updates_manually(self) -> None:
        self.start_update_check(manual=True)

    def start_update_check(self, *, manual: bool) -> None:
        if self.update_checker is not None:
            return
        self.update_checker = UpdateChecker(self)
        self.update_checker.update_available.connect(self.show_update_available_dialog)
        self.update_checker.no_update_available.connect(self.show_no_update_dialog)
        self.update_checker.check_failed.connect(self.show_update_check_failed_dialog)
        self.update_checker.check_finished.connect(self._clear_update_checker)
        if manual:
            self.status.showMessage(self.t("update_checking"))
        self.update_checker.check_async(manual=manual)

    def _clear_update_checker(self, manual: bool) -> None:
        self.update_checker = None
        if manual and self.document is None:
            self.status.showMessage(self.t("app_ready"))

    def show_update_available_dialog(self, latest_version: str, download_url: str) -> None:
        message = QMessageBox(self)
        message.setIcon(QMessageBox.Icon.Information)
        message.setWindowTitle(self.t("update_available"))
        message.setText(
            self.t(
                "update_available_message",
                app_name=APP_NAME,
                current_version=VERSION,
                latest_version=latest_version,
            )
        )
        download_button = message.addButton(
            self.t("download_update"),
            QMessageBox.ButtonRole.AcceptRole,
        )
        message.addButton(self.t("update_later"), QMessageBox.ButtonRole.RejectRole)
        message.exec()

        if message.clickedButton() is download_button:
            QDesktopServices.openUrl(QUrl(download_url))

    def show_no_update_dialog(self) -> None:
        QMessageBox.information(
            self,
            self.t("update_current"),
            self.t("update_current_message", app_name=APP_NAME, current_version=VERSION),
        )

    def show_update_check_failed_dialog(self) -> None:
        QMessageBox.warning(
            self,
            self.t("update_check_failed"),
            self.t("update_check_failed_message"),
        )

    def set_language(self, language: str) -> None:
        if language not in LANGUAGES:
            language = DEFAULT_LANGUAGE
        if language == self.language:
            return
        self.language = language
        self.settings.setValue("language", language)
        self.translate_ui()

    def set_theme(self, theme: str) -> None:
        if theme not in {"light", "dark"}:
            theme = "light"
        if theme == self.current_theme:
            return
        self.current_theme = theme
        self.settings.setValue("theme", theme)
        self.apply_theme(theme)

    def translate_ui(self) -> None:
        direction = (
            Qt.LayoutDirection.RightToLeft
            if is_rtl(self.language)
            else Qt.LayoutDirection.LeftToRight
        )
        self.setLayoutDirection(direction)
        self.setWindowTitle(APP_NAME)

        self.open_button.setText(self.t("open"))
        self.detect_button.setText(self.t("auto_detect"))
        self.apply_all_button.setText(self.t("apply_all"))
        self.export_button.setText(self.t("export"))
        self.print_button.setText(self.t("print"))
        self.previous_page_button.setToolTip(self.t("view_previous"))
        self.next_page_button.setToolTip(self.t("view_next"))
        self.zoom_out_button.setToolTip(self.t("zoom_out"))
        self.zoom_in_button.setToolTip(self.t("zoom_in"))
        self.fit_view_button.setToolTip(self.t("view_fit"))
        self.margin_spin.setToolTip(self.t("margin"))
        self.margin_spin.setAccessibleName(self.t("margin"))
        self._update_kofi_label()
        self._refresh_toolbar_icons()

        for label, key in self.translatable_group_labels:
            label.setText(self.t(key))

        self.file_menu.setTitle(self.t("file_menu"))
        self.open_action.setText(self.t("open"))
        self.export_action.setText(self.t("export"))
        self.print_action.setText(self.t("print"))
        self.quit_action.setText(self.t("quit"))
        self.view_menu.setTitle(self.t("menu_view"))
        self.previous_page_action.setText(self.t("view_previous"))
        self.next_page_action.setText(self.t("view_next"))
        self.zoom_in_action.setText(self.t("zoom_in"))
        self.zoom_out_action.setText(self.t("zoom_out"))
        self.fit_view_action.setText(self.t("view_fit"))
        self.tools_menu.setTitle(self.t("menu_tools"))
        self.detect_action.setText(self.t("auto_detect"))
        self.apply_all_action.setText(self.t("apply_all_action"))
        self.settings_action.setText(self.t("menu_settings"))
        self.help_menu.setTitle(self.t("help_menu"))
        self.check_updates_action.setText(self.t("check_updates"))
        self.about_action.setText(self.t("about_app", app_name=APP_NAME))
        if self.document is None:
            self.status.showMessage(self.t("app_ready"))

    def _set_document_actions_enabled(self, enabled: bool) -> None:
        self.detect_button.setEnabled(enabled)
        self.apply_all_button.setEnabled(enabled)
        self.export_button.setEnabled(enabled)
        self.print_button.setEnabled(enabled)
        self.previous_page_button.setEnabled(enabled)
        self.next_page_button.setEnabled(enabled)
        self.zoom_out_button.setEnabled(enabled)
        self.zoom_in_button.setEnabled(enabled)
        self.fit_view_button.setEnabled(enabled)
        self.page_spin.setEnabled(enabled)
        self.margin_spin.setEnabled(enabled)
        for action_name in (
            "detect_action",
            "apply_all_action",
            "export_action",
            "print_action",
            "previous_page_action",
            "next_page_action",
            "zoom_in_action",
            "zoom_out_action",
            "fit_view_action",
        ):
            action = getattr(self, action_name, None)
            if action is not None:
                action.setEnabled(enabled)
        self._update_navigation_buttons()

    def open_pdf(self) -> None:
        filename, _ = QFileDialog.getOpenFileName(
            self,
            self.t("open"),
            str(Path.home()),
            "PDF (*.pdf)",
        )
        if not filename:
            return

        self.open_pdf_path(Path(filename))

    def open_pdf_path(self, path: Path) -> None:
        self.close_document()
        try:
            document = fitz.open(path)
        except Exception as exc:  # pragma: no cover - GUI guard
            QMessageBox.critical(self, self.t("open_failed"), str(exc))
            self.status.showMessage(self.t("open_failed"))
            return

        if document.page_count == 0:
            document.close()
            QMessageBox.warning(self, self.t("empty_pdf"), self.t("empty_pdf_message"))
            self.status.showMessage(self.t("empty_pdf_status"))
            return

        if document.needs_pass:
            document.close()
            QMessageBox.warning(
                self,
                self.t("password_pdf"),
                self.t("password_pdf_message"),
            )
            self.status.showMessage(self.t("password_pdf_status"))
            return

        self.pdf_path = path
        self.document = document
        self.detected_rects = [PdfRect.from_fitz(page.rect) for page in self.document]
        self.auto_fit_view = True

        self.page_spin.blockSignals(True)
        self.page_spin.setRange(1, self.document.page_count)
        self.page_spin.setValue(1)
        self.page_spin.blockSignals(False)
        self.page_label.setText(f"/ {self.document.page_count}")
        self._set_document_actions_enabled(True)
        self._update_navigation_buttons()
        self.status.showMessage(self.t("opened_status", name=self.pdf_path.name))
        self.detect_labels()

    def close_document(self) -> None:
        if self.document is not None:
            self.document.close()
        self.document = None
        self.pdf_path = None
        self.detected_rects = []
        self.auto_fit_view = True
        self.scene.clear()
        self.rect_item = None

    def pdf_path_from_drop(self, mime_data) -> Path | None:  # type: ignore[no-untyped-def]
        if not mime_data.hasUrls():
            return None
        for url in mime_data.urls():
            if url.isLocalFile():
                path = Path(url.toLocalFile())
                if path.suffix.lower() == ".pdf":
                    return path
        return None

    def detect_labels(self) -> None:
        if self.pdf_path is None:
            return
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            self.detected_rects = detect_all_pages(str(self.pdf_path), margin_pt=0)
            self.status.showMessage(self.t("detected"))
        except Exception as exc:  # pragma: no cover - GUI guard
            QMessageBox.critical(self, self.t("detect_failed"), str(exc))
        finally:
            QApplication.restoreOverrideCursor()
        self.render_current_page()

    def set_current_crop_from_scene(self, scene_rect: QRectF) -> None:
        if self.document is None:
            return
        index = self.current_page_index()
        margin = self.margin_spin.value() * POINTS_PER_MM
        page_rect = PdfRect(
            scene_rect.left() / self.render_zoom,
            scene_rect.top() / self.render_zoom,
            scene_rect.right() / self.render_zoom,
            scene_rect.bottom() / self.render_zoom,
        ).clipped(self.document[index].rect)
        if (
            margin > 0
            and (page_rect.x1 - page_rect.x0) > margin * 2
            and (page_rect.y1 - page_rect.y0) > margin * 2
        ):
            page_rect = PdfRect(
                page_rect.x0 + margin,
                page_rect.y0 + margin,
                page_rect.x1 - margin,
                page_rect.y1 - margin,
            ).clipped(self.document[index].rect)
        self.detected_rects[index] = page_rect
        self.status.showMessage(self.t("zone_fixed_status"))
        self.render_current_page()

    def apply_current_crop_to_all_pages(self) -> None:
        if self.document is None:
            return
        index = self.current_page_index()
        if not self.detected_rects or index >= len(self.detected_rects):
            return
        current = self.detected_rects[index]
        self.detected_rects = [
            current.clipped(self.document[index].rect)
            for index in range(self.document.page_count)
        ]
        self.status.showMessage(self.t("zone_all_status"))
        self.render_current_page()

    def current_page_index(self) -> int:
        return max(0, self.page_spin.value() - 1)

    def current_rect(self) -> PdfRect | None:
        index = self.current_page_index()
        if not self.detected_rects or index >= len(self.detected_rects):
            return None
        if self.document is None:
            return None
        extra_margin = self.margin_spin.value() * POINTS_PER_MM
        return self.detected_rects[index].expanded(extra_margin, self.document[index].rect)

    def current_scene_rect(self) -> QRectF | None:
        rect = self.current_rect()
        if rect is None:
            return None
        return QRectF(
            rect.x0 * self.render_zoom,
            rect.y0 * self.render_zoom,
            (rect.x1 - rect.x0) * self.render_zoom,
            (rect.y1 - rect.y0) * self.render_zoom,
        )

    def page_scene_rect(self) -> QRectF:
        if self.document is None:
            return QRectF()
        page = self.document[self.current_page_index()]
        return QRectF(
            page.rect.x0 * self.render_zoom,
            page.rect.y0 * self.render_zoom,
            page.rect.width * self.render_zoom,
            page.rect.height * self.render_zoom,
        )

    def clamp_scene_rect(self, rect: QRectF) -> QRectF:
        bounds = self.page_scene_rect()
        if bounds.isNull():
            return rect.normalized()

        rect = rect.normalized()
        width = min(rect.width(), bounds.width())
        height = min(rect.height(), bounds.height())
        left = min(max(rect.left(), bounds.left()), bounds.right() - width)
        top = min(max(rect.top(), bounds.top()), bounds.bottom() - height)
        return QRectF(left, top, width, height)

    def _page_changed(self) -> None:
        self.auto_fit_view = True
        self.render_current_page()

    def previous_page(self) -> None:
        if self.document is None:
            return
        if self.page_spin.value() > self.page_spin.minimum():
            self.auto_fit_view = True
            self.page_spin.setValue(self.page_spin.value() - 1)

    def next_page(self) -> None:
        if self.document is None:
            return
        if self.page_spin.value() < self.page_spin.maximum():
            self.auto_fit_view = True
            self.page_spin.setValue(self.page_spin.value() + 1)

    def zoom_view(self, factor: float) -> None:
        if self.document is None:
            return
        self.auto_fit_view = False
        self.preview.scale(factor, factor)

    def fit_current_page(self) -> None:
        if self.document is None:
            return
        self.auto_fit_view = True
        self.preview.fitInView(
            self.scene.sceneRect(),
            Qt.AspectRatioMode.KeepAspectRatio,
        )

    def _update_navigation_buttons(self) -> None:
        has_document = self.document is not None
        can_go_previous = has_document and self.page_spin.value() > self.page_spin.minimum()
        can_go_next = has_document and self.page_spin.value() < self.page_spin.maximum()

        self.previous_page_button.setEnabled(can_go_previous)
        self.next_page_button.setEnabled(can_go_next)

        if hasattr(self, "previous_page_action"):
            self.previous_page_action.setEnabled(can_go_previous)
        if hasattr(self, "next_page_action"):
            self.next_page_action.setEnabled(can_go_next)

    def render_current_page(self) -> None:
        if self.document is None:
            return
        index = self.current_page_index()
        page = self.document[index]
        pixmap = page.get_pixmap(
            matrix=fitz.Matrix(self.render_zoom, self.render_zoom),
            alpha=False,
        )
        image = QImage.fromData(pixmap.tobytes("png"))

        self.scene.clear()
        self.scene.addPixmap(QPixmap.fromImage(image))
        self.rect_item = None
        rect = self.current_rect()
        if rect is not None:
            pen = QPen(QColor(PIXO_TEAL), 3)
            pen.setCosmetic(True)
            brush = QBrush(QColor(20, 184, 166, 55))
            scene_rect = self.current_scene_rect()
            if scene_rect is not None:
                self.rect_item = self.scene.addRect(scene_rect, pen, brush)
        self.scene.setSceneRect(self.scene.itemsBoundingRect())
        if self.auto_fit_view:
            self.preview.fitInView(
                self.scene.sceneRect(),
                Qt.AspectRatioMode.KeepAspectRatio,
            )
        self._update_navigation_buttons()

    def effective_rects(self) -> list[PdfRect]:
        if self.document is None:
            return []
        extra_margin = self.margin_spin.value() * POINTS_PER_MM
        return [
            rect.expanded(extra_margin, self.document[index].rect)
            for index, rect in enumerate(self.detected_rects)
        ]

    def export_cropped(self) -> Path | None:
        if self.pdf_path is None:
            return None
        default_name = self.pdf_path.with_name(f"{self.pdf_path.stem}_cropped.pdf")
        filename, _ = QFileDialog.getSaveFileName(
            self,
            self.t("export_title"),
            str(default_name),
            "PDF (*.pdf)",
        )
        if not filename:
            return None

        output_path = crop_pdf(self.pdf_path, filename, self.effective_rects())
        self.status.showMessage(self.t("exported_status", path=output_path))
        return output_path

    def print_cropped(self) -> None:
        if self.document is None:
            return
        rects = self.effective_rects()
        dialog = PrintOptionsDialog(self, self.document, rects, self.current_page_index())
        if dialog.exec() != QDialog.Accepted:
            return
        self.print_with_options(dialog)

    def render_clip_image(self, page_index: int, rect: PdfRect, *, zoom: float = 4.0) -> QImage:
        if self.document is None:
            return QImage()
        page = self.document[page_index]
        pixmap = page.get_pixmap(
            matrix=fitz.Matrix(zoom, zoom),
            alpha=False,
            clip=rect.to_fitz(),
        )
        return QImage.fromData(pixmap.tobytes("png"))

    def print_with_options(self, options: PrintOptionsDialog) -> None:
        printer_info = options.selected_printer_info()
        if printer_info is not None:
            printer = QPrinter(printer_info, QPrinter.PrinterMode.HighResolution)
        else:
            printer = QPrinter(QPrinter.PrinterMode.HighResolution)
        printer.setOutputFormat(QPrinter.OutputFormat.NativeFormat)
        printer.setPrinterName(options.printer_name())
        printer.setCopyCount(options.copies())

        color_mode = options.color_mode()
        if color_mode is not None:
            printer.setColorMode(color_mode)

        paper_size = options.paper_size()
        orientation = options.orientation()
        if paper_size is not None or orientation is not None or options.is_thermal_paper():
            current_layout = printer.pageLayout()
            margins = (
                QMarginsF(0, 0, 0, 0)
                if options.is_thermal_paper()
                else current_layout.margins(QPageLayout.Unit.Millimeter)
            )
            page_layout = QPageLayout(
                paper_size or current_layout.pageSize(),
                orientation or current_layout.orientation(),
                margins,
                QPageLayout.Unit.Millimeter,
            )
            printer.setPageLayout(page_layout)

        resolution = options.resolution()
        if resolution is not None:
            printer.setResolution(resolution)

        if options.is_thermal_paper():
            printer.setFullPage(True)
            printer.setDuplex(QPrinter.DuplexMode.DuplexNone)
        else:
            duplex_mode = options.duplex_mode()
            if duplex_mode is not None:
                printer.setDuplex(duplex_mode)
        printer.setDocName(self.pdf_path.stem if self.pdf_path is not None else "pixoCrop")

        painter = QPainter()
        if not painter.begin(printer):
            QMessageBox.critical(
                self,
                self.t("print_failed"),
                self.t("print_failed_start"),
            )
            return

        try:
            painted_pages = 0
            pages = options.selected_pages()
            for output_index, page_index in enumerate(pages):
                if output_index > 0:
                    if not printer.newPage():
                        break
                if self.paint_print_page(
                    painter,
                    printer,
                    page_index,
                    options.rects[page_index],
                    fit_to_page=options.fit_to_page(),
                    color_mode=options.effective_color_mode(),
                    zoom_factor=options.zoom_factor(),
                ):
                    painted_pages += 1
        finally:
            painter.end()

        if painted_pages == 0:
            QMessageBox.critical(
                self,
                self.t("print_failed"),
                self.t("print_no_pages"),
            )
            self.status.showMessage(self.t("print_no_pages_status"))
            return

        if printer.printerState() == QPrinter.PrinterState.Error:
            QMessageBox.critical(
                self,
                self.t("print_refused"),
                self.t("print_refused_message"),
            )
            self.status.showMessage(self.t("print_refused_status"))
            return

        self.status.showMessage(self.t("print_status"))

    def paint_print_page(
        self,
        painter: QPainter,
        printer: QPrinter,
        page_index: int,
        rect: PdfRect,
        *,
        fit_to_page: bool,
        color_mode: QPrinter.ColorMode,
        zoom_factor: float,
    ) -> bool:
        image = self.render_clip_image(page_index, rect, zoom=printer.resolution() / 72)
        if image.isNull():
            return False

        if color_mode == QPrinter.ColorMode.GrayScale:
            image = image.convertToFormat(QImage.Format.Format_Grayscale8)

        page_rect = printer.pageRect(QPrinter.Unit.DevicePixel)
        if page_rect.isEmpty():
            return False

        if fit_to_page:
            scale = min(
                page_rect.width() / image.width(),
                page_rect.height() / image.height(),
            )
            image_width = max(1, int(image.width() * scale))
            image_height = max(1, int(image.height() * scale))
        else:
            image_width = min(image.width(), page_rect.width())
            image_height = min(image.height(), page_rect.height())

        image_width = max(1, int(image_width * zoom_factor))
        image_height = max(1, int(image_height * zoom_factor))

        target_rect = QRect(
            page_rect.x() + (page_rect.width() - image_width) // 2,
            page_rect.y() + (page_rect.height() - image_height) // 2,
            image_width,
            image_height,
        )

        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        painter.drawImage(target_rect, image)
        return True

    def _candidate_asset_directories(self) -> list[Path]:
        app_file = Path(__file__).resolve()
        candidates = [
            app_file.parent / "asset",
            app_file.parent / "assets",
            app_file.parent.parent / "asset",
            app_file.parent.parent / "assets",
            app_file.parent.parent.parent / "asset",
            app_file.parent.parent.parent / "assets",
        ]
        return [path for path in candidates if path.exists() and path.is_dir()]

    def _find_asset(self, keywords: tuple[str, ...], theme: str | None = None) -> Path | None:
        suffixes = {".png", ".jpg", ".jpeg", ".webp", ".svg"}
        theme_keywords = (theme,) if theme else ()

        for directory in self.asset_directories:
            files = [path for path in directory.iterdir() if path.suffix.lower() in suffixes]
            preferred_files = files
            if theme_keywords:
                themed = [
                    path
                    for path in files
                    if all(keyword.lower() in path.stem.lower() for keyword in theme_keywords)
                ]
                if themed:
                    preferred_files = themed

            for path in preferred_files:
                stem = path.stem.lower()
                if all(keyword.lower() in stem for keyword in keywords):
                    return path

        return None

    def _pixmap_for_label(
        self,
        path: Path,
        logical_size: QSize | None = None,
        *,
        logical_height: int | None = None,
    ) -> QPixmap:
        pixmap = QPixmap(str(path))
        if pixmap.isNull():
            return pixmap

        ratio = max(1.0, self.devicePixelRatioF())
        if logical_height is not None:
            physical_height = max(1, int(logical_height * ratio))
            scaled = pixmap.scaledToHeight(
                physical_height,
                Qt.TransformationMode.SmoothTransformation,
            )
        elif logical_size is not None:
            physical_size = QSize(
                max(1, int(logical_size.width() * ratio)),
                max(1, int(logical_size.height() * ratio)),
            )
            scaled = pixmap.scaled(
                physical_size,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        else:
            scaled = pixmap

        scaled.setDevicePixelRatio(ratio)
        return scaled

    def _themed_brand_asset(self, kind: str) -> Path | None:
        variant = "dark" if self.current_theme == "dark" else "white"
        path = asset_path(f"{kind}_{variant}.png")
        if path.exists():
            return path
        return self._find_asset((kind,), self.current_theme) or self._find_asset((kind,))

    def _load_brand_assets(self) -> None:
        logo_path = self._themed_brand_asset("logo")
        title_path = self._themed_brand_asset("title")

        if logo_path is not None:
            logo_pixmap = self._pixmap_for_label(logo_path, self.logo_label.size())
            if not logo_pixmap.isNull():
                self.logo_label.setPixmap(logo_pixmap)
            else:
                self.logo_label.setText("P")
        else:
            self.logo_label.setText("P")

        if title_path is not None:
            title_pixmap = self._pixmap_for_label(title_path, logical_height=42)
            if not title_pixmap.isNull():
                self.title_logo_label.setText("")
                self.title_logo_label.setPixmap(title_pixmap)
                return

        self.title_logo_label.setPixmap(QPixmap())
        self.title_logo_label.setText("pixoCrop")

    def _paint_toolbar_icon(self, icon_kind: str) -> QIcon:
        colors = theme_colors(self.current_theme)
        pixmap = QPixmap(48, 48)
        pixmap.fill(Qt.GlobalColor.transparent)

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        pen = QPen(QColor(colors.text), 3)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)

        if icon_kind in {"zoom_in", "zoom_out"}:
            painter.drawEllipse(QRect(8, 8, 25, 25))
            painter.drawLine(30, 30, 41, 41)
            painter.drawLine(14, 20, 27, 20)
            if icon_kind == "zoom_in":
                painter.drawLine(20, 14, 20, 27)
        elif icon_kind == "fit":
            for first, second in (
                ((8, 18), (8, 8)),
                ((8, 8), (18, 8)),
                ((30, 8), (40, 8)),
                ((40, 8), (40, 18)),
                ((40, 30), (40, 40)),
                ((40, 40), (30, 40)),
                ((18, 40), (8, 40)),
                ((8, 40), (8, 30)),
            ):
                painter.drawLine(*first, *second)

        painter.end()
        return QIcon(pixmap)

    def _update_kofi_label(self) -> None:
        link_color = theme_colors(self.current_theme).link
        self.kofi_label.setText(
            f'<a href="{KOFI_URL}" style="color:{link_color}; '
            f'text-decoration:none">{self.t("sponsor_kofi")}</a>'
        )

    def _refresh_toolbar_icons(self) -> None:
        rtl = self.layoutDirection() == Qt.LayoutDirection.RightToLeft
        previous_icon = (
            QStyle.StandardPixmap.SP_ArrowRight
            if rtl
            else QStyle.StandardPixmap.SP_ArrowLeft
        )
        next_icon = (
            QStyle.StandardPixmap.SP_ArrowLeft
            if rtl
            else QStyle.StandardPixmap.SP_ArrowRight
        )
        self.previous_page_button.setIcon(self.style().standardIcon(previous_icon))
        self.next_page_button.setIcon(self.style().standardIcon(next_icon))
        self.zoom_out_button.setIcon(self._paint_toolbar_icon("zoom_out"))
        self.zoom_in_button.setIcon(self._paint_toolbar_icon("zoom_in"))
        self.fit_view_button.setIcon(self._paint_toolbar_icon("fit"))
        self.open_button.setIcon(
            self.style().standardIcon(QStyle.StandardPixmap.SP_DialogOpenButton)
        )
        self.export_button.setIcon(
            self.style().standardIcon(QStyle.StandardPixmap.SP_DialogSaveButton)
        )

    def apply_theme(self, theme: str) -> None:
        self.current_theme = theme
        self.setStyleSheet(build_stylesheet(theme))
        self._refresh_toolbar_icons()
        self._update_kofi_label()
        self._load_brand_assets()

    def _refresh_theme_assets_after_show(self) -> None:
        self._load_brand_assets()

    def closeEvent(self, event) -> None:  # type: ignore[no-untyped-def]
        self.close_document()
        super().closeEvent(event)


def main() -> int:
    app = QApplication(sys.argv)
    app.setOrganizationName("PixoGlace")
    app.setApplicationName(APP_NAME)
    app.setApplicationDisplayName(APP_NAME)
    app.setWindowIcon(themed_icon())
    window = MainWindow()
    window.show()
    window._refresh_theme_assets_after_show()
    QTimer.singleShot(1200, window.check_for_updates_on_startup)
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
