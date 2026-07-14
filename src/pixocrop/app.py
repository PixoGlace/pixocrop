from __future__ import annotations

import sys
from pathlib import Path

import fitz
from PySide6.QtCore import QEvent, QMarginsF, QPointF, QRect, QRectF, QSize, QSizeF, Qt
from PySide6.QtGui import QAction, QBrush, QColor, QIcon, QImage, QKeySequence, QPageLayout, QPageSize, QPainter, QPen, QPixmap
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
    QStatusBar,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from pixocrop.detection import PdfRect, detect_all_pages
from pixocrop.pdf_ops import crop_pdf

POINTS_PER_MM = 72 / 25.4
APP_NAME = "pixoCrop"
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

        self.setWindowTitle("Imprimer la zone sélectionnée")
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
        self.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_label.setMinimumSize(520, 520)
        self.preview_label.setStyleSheet(
            f"""
            QLabel {{
                background: {PIXO_LIGHT_PANEL};
                border: 1px solid {PIXO_LIGHT_BORDER};
                border-radius: 12px;
            }}
            """
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

        self.fit_page_check = QCheckBox("Adapter à la page")
        self.fit_page_check.setChecked(True)

        form = QFormLayout()
        form.addRow("Imprimante", self.printer_combo)
        form.addRow("Pages", self.page_combo)
        form.addRow("Aperçu page", self.preview_page_spin)
        form.addRow("Copies", self.copies_spin)
        form.addRow("Couleur", self.color_combo)
        form.addRow("Orientation", self.orientation_buttons)
        form.addRow("Format papier", self.paper_size_combo)
        form.addRow("Qualité", self.resolution_combo)
        form.addRow("Recto-verso", self.duplex_combo)
        form.addRow("Zoom", self.zoom_spin)
        form.addRow("", self.fit_page_check)

        options_group = QGroupBox("Options d'impression")
        options_group.setLayout(form)

        self.button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Cancel)
        self.print_button = self.button_box.addButton(
            "Imprimer",
            QDialogButtonBox.ButtonRole.AcceptRole,
        )
        self.print_button.setEnabled(bool(self.printers) and bool(self.rects))

        right_layout = QVBoxLayout()
        right_layout.addWidget(options_group)
        right_layout.addStretch()
        right_layout.addWidget(self.button_box)

        layout = QHBoxLayout()
        layout.addWidget(self.preview_label, 1)
        layout.addLayout(right_layout)

        self.setLayout(layout)

    def _create_printer_combo(self) -> QComboBox:
        combo = QComboBox()

        if not self.printers:
            combo.addItem("Aucune imprimante détectée")
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
        combo.addItem("Toutes les pages", self.PAGE_ALL)
        combo.addItem("Page courante", self.PAGE_CURRENT)
        return combo

    def _create_preview_page_spin(self) -> QSpinBox:
        spin = QSpinBox()
        spin.setRange(1, max(1, len(self.rects)))
        spin.setValue(self.current_page + 1)
        spin.setEnabled(bool(self.rects))
        return spin

    def _create_copies_spin(self) -> QSpinBox:
        spin = QSpinBox()
        spin.setRange(1, 99)
        spin.setValue(1)
        return spin

    def _create_color_combo(self) -> QComboBox:
        combo = QComboBox()
        combo.addItem("Défaut de l'imprimante", self.PRINTER_DEFAULT)
        combo.addItem("Couleur", QPrinter.ColorMode.Color)
        combo.addItem("Noir et blanc", QPrinter.ColorMode.GrayScale)
        return combo

    def _create_paper_size_combo(self) -> QComboBox:
        combo = QComboBox()
        self._populate_paper_size_combo(combo)
        return combo

    def _populate_paper_size_combo(self, combo: QComboBox | None = None) -> None:
        combo = combo or self.paper_size_combo
        current_name = combo.currentText()
        combo.blockSignals(True)
        combo.clear()
        combo.addItem("Défaut de l'imprimante", self.PRINTER_DEFAULT)

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
        combo.addItem("Défaut de l'imprimante", self.PRINTER_DEFAULT)
        combo.addItem("Brouillon — 150 dpi", 150)
        combo.addItem("Standard — 300 dpi", 300)
        combo.addItem("Haute qualité — 600 dpi", 600)
        return combo

    def _create_duplex_combo(self) -> QComboBox:
        combo = QComboBox()
        combo.addItem("Défaut de l'imprimante", self.PRINTER_DEFAULT)
        combo.addItem("Recto simple", QPrinter.DuplexMode.DuplexNone)
        combo.addItem("Recto-verso bord long", QPrinter.DuplexMode.DuplexLongSide)
        combo.addItem("Recto-verso bord court", QPrinter.DuplexMode.DuplexShortSide)
        return combo

    def _create_zoom_spin(self) -> QSpinBox:
        spin = QSpinBox()
        spin.setRange(25, 300)
        spin.setSingleStep(5)
        spin.setValue(100)
        spin.setSuffix(" %")
        return spin

    def _create_orientation_selector(self) -> tuple[QButtonGroup, QWidget]:
        group = QButtonGroup(self)
        group.setExclusive(True)

        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        buttons = [
            self.create_orientation_button(
                "Défaut", "auto", self.ORIENTATION_DEFAULT
            ),
            self.create_orientation_button("Auto", "auto", self.ORIENTATION_AUTO),
            self.create_orientation_button(
                "Portrait", "portrait", self.ORIENTATION_PORTRAIT
            ),
            self.create_orientation_button(
                "Paysage", "landscape", self.ORIENTATION_LANDSCAPE
            ),
        ]

        for button in buttons:
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
        button.setText(text)
        button.setIcon(self.orientation_icon(icon_kind))
        button.setIconSize(QSize(42, 42))
        button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
        button.setCheckable(True)
        button.setMinimumSize(76, 74)
        button.setProperty("orientation_id", button_id)
        button.setStyleSheet(
            f"""
            QToolButton {{
                border: 1px solid {PIXO_LIGHT_BORDER};
                border-radius: 8px;
                padding: 6px;
                background: {PIXO_WHITE};
                color: {PIXO_NAVY};
            }}
            QToolButton:hover {{
                border-color: {PIXO_TEAL};
                background: #ECFEFF;
            }}
            QToolButton:checked {{
                border: 2px solid {PIXO_TEAL};
                background: #CCFBF1;
                padding: 5px;
            }}
            """
        )
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
            self.preview_label.setText("Aucune zone détectée à imprimer.")
            self.preview_label.setPixmap(QPixmap())
            self._preview_image = None
            return

        page_index = self._current_preview_page_index()

        try:
            self._preview_image = self.render_print_preview(page_index)
        except Exception as error:
            self.preview_label.setText(f"Impossible de générer l'aperçu :\n{error}")
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
        pixmap = QPixmap(64, 64)
        pixmap.fill(Qt.GlobalColor.transparent)

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QPen(QColor(95, 95, 95), 2))
        painter.setBrush(QBrush(Qt.GlobalColor.white))

        if icon_kind == "auto":
            painter.setBrush(QBrush(QColor(248, 248, 248)))
            painter.drawRoundedRect(QRect(12, 18, 26, 34), 3, 3)
            painter.drawRoundedRect(QRect(25, 12, 30, 24), 3, 3)

            painter.setPen(QPen(QColor(36, 116, 216), 3))
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
        painter.setPen(QPen(QColor(120, 120, 120), 2))

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
        self.logo_label.setFixedSize(64, 64)
        self.logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.title_logo_label = QLabel("pixoCrop")
        self.title_logo_label.setObjectName("titleLogoLabel")
        self.title_logo_label.setMinimumSize(220, 64)
        self.title_logo_label.setAlignment(Qt.AlignmentFlag.AlignVCenter)


        self.theme_combo = QComboBox()
        self.theme_combo.setObjectName("themeCombo")
        self.theme_combo.addItem("Thème clair", "light")
        self.theme_combo.addItem("Thème sombre", "dark")

        self.open_button = QPushButton("Ouvrir PDF")
        self.open_button.setObjectName("primaryButton")
        self.detect_button = QPushButton("Auto détecter")
        self.apply_all_button = QPushButton("Appliquer à toutes")
        self.export_button = QPushButton("Exporter cropped")
        self.print_button = QPushButton("Imprimer")
        self.print_button.setObjectName("accentButton")
        self.previous_page_button = QPushButton("◀")
        self.next_page_button = QPushButton("▶")
        self.zoom_out_button = QPushButton("−")
        self.zoom_in_button = QPushButton("+")
        self.fit_view_button = QPushButton("Ajuster")
        for compact_button in (
            self.previous_page_button,
            self.next_page_button,
            self.zoom_out_button,
            self.zoom_in_button,
        ):
            compact_button.setFixedWidth(34)
        self.page_spin = QSpinBox()
        self.page_spin.setFixedWidth(58)
        self.margin_spin = QSpinBox()
        self.margin_spin.setRange(0, 30)
        self.margin_spin.setValue(3)
        self.margin_spin.setSuffix(" mm")
        self.margin_spin.setFixedWidth(76)

        self.page_label = QLabel("/ 0")
        self.status = QStatusBar()
        self.setStatusBar(self.status)

        self.current_theme = "light"
        self.asset_directories = self._candidate_asset_directories()
        self._build_layout()
        self._build_menu()
        self._connect_signals()
        self._set_document_actions_enabled(False)
        self.apply_theme(self.current_theme)
        self.status.showMessage("Ouvrez un PDF ou déposez-le dans l'aperçu.")

    def _toolbar_group(self, title: str, rows: list[list[QWidget]]) -> QWidget:
        group = QWidget()
        group.setObjectName("toolbarGroup")

        layout = QVBoxLayout(group)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        title_label = QLabel(title)
        title_label.setObjectName("toolbarGroupTitle")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_label)

        for row_widgets in rows:
            row = QHBoxLayout()
            row.setContentsMargins(0, 0, 0, 0)
            row.setSpacing(4)
            for widget in row_widgets:
                row.addWidget(widget)
            layout.addLayout(row)

        return group

    def _build_layout(self) -> None:
        brand_text_layout = QVBoxLayout()
        brand_text_layout.setContentsMargins(0, 0, 0, 0)
        brand_text_layout.setSpacing(0)
        brand_text_layout.addWidget(self.title_logo_label)

        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(14, 10, 14, 10)
        header_layout.setSpacing(12)
        header_layout.addWidget(self.logo_label)
        header_layout.addLayout(brand_text_layout)

        self.header_widget = QWidget()
        self.header_widget.setObjectName("headerWidget")

        toolbar = QHBoxLayout()
        toolbar.setContentsMargins(0, 0, 0, 0)
        toolbar.setSpacing(10)

        page_label = QLabel("Page")
        margin_label = QLabel("Marge")

        toolbar.addWidget(self._toolbar_group("Fichier", [[self.open_button], [self.export_button]]))
        toolbar.addWidget(self._toolbar_group("Détection", [[self.detect_button], [self.apply_all_button]]))
        toolbar.addWidget(
            self._toolbar_group(
                "Page",
                [
                    [self.previous_page_button, self.next_page_button],
                    [page_label, self.page_spin, self.page_label],
                ],
            )
        )
        toolbar.addWidget(
            self._toolbar_group(
                "Vue",
                [[self.zoom_out_button, self.zoom_in_button], [self.fit_view_button]],
            )
        )
        toolbar.addWidget(self._toolbar_group("Marge", [[margin_label, self.margin_spin]]))
        toolbar.addWidget(self._toolbar_group("Sortie", [[self.print_button]]))
        toolbar.addWidget(self._toolbar_group("Thème", [[self.theme_combo]]))
        toolbar.addStretch()

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
        file_menu = self.menuBar().addMenu("Fichier")
        self.open_action = QAction("Ouvrir PDF", self)
        self.open_action.setShortcut(QKeySequence.StandardKey.Open)
        self.open_action.triggered.connect(self.open_pdf)
        file_menu.addAction(self.open_action)

        self.export_action = QAction("Exporter cropped", self)
        self.export_action.setShortcut(QKeySequence.StandardKey.SaveAs)
        self.export_action.triggered.connect(self.export_cropped)
        file_menu.addAction(self.export_action)

        self.print_action = QAction("Imprimer", self)
        self.print_action.setShortcut(QKeySequence.StandardKey.Print)
        self.print_action.triggered.connect(self.print_cropped)
        file_menu.addAction(self.print_action)

        file_menu.addSeparator()

        quit_action = QAction("Quitter", self)
        quit_action.setShortcut(QKeySequence.StandardKey.Quit)
        quit_action.triggered.connect(self.close)
        file_menu.addAction(quit_action)

        view_menu = self.menuBar().addMenu("Affichage")
        self.previous_page_action = QAction("Page précédente", self)
        self.previous_page_action.setShortcut(QKeySequence(Qt.Key.Key_PageUp))
        self.previous_page_action.triggered.connect(self.previous_page)
        view_menu.addAction(self.previous_page_action)

        self.next_page_action = QAction("Page suivante", self)
        self.next_page_action.setShortcut(QKeySequence(Qt.Key.Key_PageDown))
        self.next_page_action.triggered.connect(self.next_page)
        view_menu.addAction(self.next_page_action)

        view_menu.addSeparator()

        self.zoom_in_action = QAction("Zoom avant", self)
        self.zoom_in_action.setShortcut(QKeySequence.StandardKey.ZoomIn)
        self.zoom_in_action.triggered.connect(lambda: self.zoom_view(1.15))
        view_menu.addAction(self.zoom_in_action)

        self.zoom_out_action = QAction("Zoom arrière", self)
        self.zoom_out_action.setShortcut(QKeySequence.StandardKey.ZoomOut)
        self.zoom_out_action.triggered.connect(lambda: self.zoom_view(0.87))
        view_menu.addAction(self.zoom_out_action)

        self.fit_view_action = QAction("Ajuster à la fenêtre", self)
        self.fit_view_action.setShortcut(QKeySequence(Qt.Modifier.CTRL | Qt.Key.Key_0))
        self.fit_view_action.triggered.connect(self.fit_current_page)
        view_menu.addAction(self.fit_view_action)

        tools_menu = self.menuBar().addMenu("Outils")
        self.detect_action = QAction("Auto détecter", self)
        self.detect_action.setShortcut(QKeySequence("Ctrl+D"))
        self.detect_action.triggered.connect(self.detect_labels)
        tools_menu.addAction(self.detect_action)

        self.apply_all_action = QAction("Appliquer la zone à toutes les pages", self)
        self.apply_all_action.triggered.connect(self.apply_current_crop_to_all_pages)
        tools_menu.addAction(self.apply_all_action)

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
        self.theme_combo.currentIndexChanged.connect(self.on_theme_changed)

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
            "Choisir un PDF",
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
            QMessageBox.critical(self, "Ouverture impossible", str(exc))
            self.status.showMessage("Impossible d'ouvrir le PDF.")
            return

        if document.page_count == 0:
            document.close()
            QMessageBox.warning(self, "PDF vide", "Ce PDF ne contient aucune page.")
            self.status.showMessage("PDF vide.")
            return

        if document.needs_pass:
            document.close()
            QMessageBox.warning(
                self,
                "PDF protégé",
                "Ce PDF est protégé par mot de passe. L'ouverture n'est pas encore prise en charge.",
            )
            self.status.showMessage("PDF protégé par mot de passe.")
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
        self.status.showMessage(f"PDF ouvert : {self.pdf_path.name}")
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
            self.status.showMessage("Zones détectées automatiquement.")
        except Exception as exc:  # pragma: no cover - GUI guard
            QMessageBox.critical(self, "Detection impossible", str(exc))
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
        self.status.showMessage("Zone corrigée pour la page courante.")
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
        self.status.showMessage("Zone courante appliquée à toutes les pages.")
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
            "Enregistrer le PDF recadré",
            str(default_name),
            "PDF (*.pdf)",
        )
        if not filename:
            return None

        output_path = crop_pdf(self.pdf_path, filename, self.effective_rects())
        self.status.showMessage(f"PDF recadré enregistré : {output_path}")
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
                "Impression impossible",
                "Impossible de démarrer l'impression avec cette imprimante.",
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
                "Impression impossible",
                "Aucune page n'a pu être dessinée pour l'impression.",
            )
            self.status.showMessage("Aucune page imprimable générée.")
            return

        if printer.printerState() == QPrinter.PrinterState.Error:
            QMessageBox.critical(
                self,
                "Impression refusée",
                "Le pilote d'imprimante a refusé le travail. Vérifiez que le format papier sélectionné correspond au rouleau/étiquette installé.",
            )
            self.status.showMessage("Impression refusée par le pilote.")
            return

        self.status.showMessage("Travail transmis au système d'impression.")

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
            title_pixmap = self._pixmap_for_label(title_path, logical_height=56)
            if not title_pixmap.isNull():
                self.title_logo_label.setText("")
                self.title_logo_label.setPixmap(title_pixmap)
                return

        self.title_logo_label.setPixmap(QPixmap())
        self.title_logo_label.setText("pixoCrop")

    def on_theme_changed(self) -> None:
        theme = self.theme_combo.currentData()
        if theme not in {"light", "dark"}:
            theme = "light"
        self.apply_theme(theme)

    def apply_theme(self, theme: str) -> None:
        self.current_theme = theme
        is_dark = theme == "dark"

        background = PIXO_DARK if is_dark else PIXO_WHITE
        panel = PIXO_DARK_PANEL if is_dark else PIXO_LIGHT_PANEL
        panel_alt = "#1E293B" if is_dark else "#FFFFFF"
        text = PIXO_WHITE if is_dark else PIXO_NAVY
        secondary = PIXO_DARK_SECONDARY if is_dark else PIXO_LIGHT_SECONDARY
        border = PIXO_DARK_BORDER if is_dark else PIXO_LIGHT_BORDER
        input_background = "#0B1220" if is_dark else "#FFFFFF"
        disabled_background = "#1F2937" if is_dark else "#EEF2F7"
        disabled_text = "#64748B" if is_dark else "#94A3B8"
        preview_background = "#0B1220" if is_dark else "#EEF2F7"
        menu_background = "#111827" if is_dark else "#FFFFFF"
        menu_selection = "#134E4A" if is_dark else "#CCFBF1"
        menu_selection_text = PIXO_WHITE if is_dark else PIXO_NAVY

        self.setStyleSheet(
            f"""
            QMainWindow {{
                background: {background};
                color: {text};
            }}
            QWidget#rootWidget {{
                background: {background};
                color: {text};
            }}
            QWidget#headerWidget {{
                background: {panel};
                border: 1px solid {border};
                border-radius: 16px;
            }}
            QWidget#toolbarWidget {{
                background: transparent;
                border: 0;
            }}
            QWidget#toolbarGroup {{
                background: transparent;
            }}
            QLabel#toolbarGroupTitle {{
                color: {secondary};
                font-size: 11px;
                font-weight: 700;
                text-transform: uppercase;
            }}
            QLabel {{
                color: {text};
            }}
            QLabel#logoLabel {{
                background: transparent;
                border: 0;
                color: {PIXO_TEAL};
                font-size: 24px;
                font-weight: 800;
            }}
            QLabel#titleLogoLabel {{
                color: {text};
                font-size: 26px;
                font-weight: 800;
                letter-spacing: .4px;
            }}
            QLabel#subtitleLabel {{
                color: {secondary};
                font-size: 12px;
            }}
            QGraphicsView {{
                background: {preview_background};
                border: 1px solid {border};
                border-radius: 16px;
            }}
            QPushButton {{
                background: {panel_alt};
                color: {text};
                border: 1px solid {border};
                border-radius: 8px;
                padding: 6px 10px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                border-color: {PIXO_TEAL};
                color: {PIXO_TEAL};
            }}
            QPushButton:pressed {{
                background: {menu_selection};
            }}
            QPushButton:disabled {{
                background: {disabled_background};
                color: {disabled_text};
                border-color: {border};
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
                background: {PIXO_TEAL};
                color: {PIXO_WHITE};
                border-color: {PIXO_TEAL};
            }}
            QPushButton#accentButton:hover {{
                background: #0F9F91;
                border-color: {PIXO_AMBER};
                color: {PIXO_WHITE};
            }}
            QComboBox, QSpinBox {{
                background: {input_background};
                color: {text};
                border: 1px solid {border};
                border-radius: 8px;
                padding: 6px 8px;
                selection-background-color: {PIXO_TEAL};
                selection-color: {PIXO_WHITE};
            }}
            QComboBox:focus, QSpinBox:focus {{
                border: 1px solid {PIXO_AMBER};
            }}
            QComboBox::drop-down {{
                border: 0;
                width: 22px;
            }}
            QComboBox QAbstractItemView {{
                background: {menu_background};
                color: {text};
                border: 1px solid {border};
                border-radius: 6px;
                outline: 0;
                padding: 4px;
                selection-background-color: {menu_selection};
                selection-color: {menu_selection_text};
            }}
            QComboBox QAbstractItemView::item {{
                min-height: 26px;
                padding: 4px 8px;
            }}
            QComboBox QAbstractItemView::item:selected {{
                background: {menu_selection};
                color: {menu_selection_text};
            }}
            QComboBox QAbstractItemView::item:disabled {{
                color: {disabled_text};
                background: {disabled_background};
            }}
            QMenuBar {{
                background: {background};
                color: {text};
            }}
            QMenuBar::item:selected {{
                background: {menu_selection};
                color: {text};
            }}
            QMenu {{
                background: {menu_background};
                color: {text};
                border: 1px solid {border};
            }}
            QMenu::item:selected {{
                background: {menu_selection};
                color: {text};
            }}
            QStatusBar {{
                background: {panel};
                color: {secondary};
                border-top: 1px solid {border};
            }}
            QDialog {{
                background: {background};
                color: {text};
            }}
            QGroupBox {{
                color: {text};
                border: 1px solid {border};
                border-radius: 12px;
                margin-top: 12px;
                padding: 10px;
                font-weight: 700;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 6px;
                color: {PIXO_TEAL};
            }}
            QCheckBox {{
                color: {text};
                spacing: 8px;
            }}
            QCheckBox::indicator:checked {{
                background: {PIXO_TEAL};
                border: 1px solid {PIXO_TEAL};
            }}
            QCheckBox::indicator:unchecked {{
                background: {input_background};
                border: 1px solid {border};
            }}
            """
        )
        self._load_brand_assets()
        
    def _refresh_theme_assets_after_show(self) -> None:
        self._load_brand_assets()

    def closeEvent(self, event) -> None:  # type: ignore[no-untyped-def]
        self.close_document()
        super().closeEvent(event)


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setWindowIcon(themed_icon())
    window = MainWindow()
    window.show()
    window._refresh_theme_assets_after_show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
