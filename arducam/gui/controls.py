from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QPushButton,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from arducam.camera import RESOLUTION_FPS_TABLE
from arducam.gui.styles import (
    COMBO_STYLE_LARGE,
    PANEL_BG,
    PILL_STYLE_ACTIVE,
    PILL_STYLE_INACTIVE,
    SLIDER_STYLE,
    card,
    section_label,
    set_value_label_enabled,
    value_label,
)


class _PillToggle(QWidget):
    """Auto/Manual pill toggle."""

    toggled = pyqtSignal(bool)  # True = auto

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        container = QWidget()
        container.setStyleSheet("background: #f0f0f2; border-radius: 10px;")
        container_layout = QHBoxLayout(container)
        container_layout.setContentsMargins(2, 2, 2, 2)
        container_layout.setSpacing(0)

        self._auto_btn = QPushButton("Auto")
        self._manual_btn = QPushButton("Manual")
        self._auto_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._manual_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._auto_btn.setStyleSheet(PILL_STYLE_ACTIVE)
        self._manual_btn.setStyleSheet(PILL_STYLE_INACTIVE)

        self._auto_btn.clicked.connect(lambda: self._set_auto(True))
        self._manual_btn.clicked.connect(lambda: self._set_auto(False))

        container_layout.addWidget(self._auto_btn)
        container_layout.addWidget(self._manual_btn)
        layout.addWidget(container)

        self._is_auto = True

    def _set_auto(self, auto: bool):
        if auto == self._is_auto:
            return
        self._is_auto = auto
        self._auto_btn.setStyleSheet(PILL_STYLE_ACTIVE if auto else PILL_STYLE_INACTIVE)
        self._manual_btn.setStyleSheet(PILL_STYLE_INACTIVE if auto else PILL_STYLE_ACTIVE)
        self.toggled.emit(auto)

    @property
    def is_auto(self) -> bool:
        return self._is_auto


class ControlsPanel(QWidget):
    resolution_changed = pyqtSignal(int, int)
    exposure_changed = pyqtSignal(int)
    exposure_auto_changed = pyqtSignal(bool)
    iso_changed = pyqtSignal(int)
    focus_changed = pyqtSignal(int)
    focus_auto_changed = pyqtSignal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(PANEL_BG)
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(12, 12, 12, 12)

        # --- Resolution ---
        res_card, res_layout = card()
        res_layout.addWidget(section_label("Resolution"))
        self._resolution_combo = QComboBox()
        self._resolution_combo.setStyleSheet(COMBO_STYLE_LARGE)
        for (w, h), fps in RESOLUTION_FPS_TABLE.items():
            self._resolution_combo.addItem(f"{w} \u00d7 {h}  \u2014  {fps} fps", (w, h))
        self._resolution_combo.setCurrentIndex(1)
        self._resolution_combo.currentIndexChanged.connect(self._on_resolution_changed)
        res_layout.addWidget(self._resolution_combo)
        layout.addWidget(res_card)

        # --- Exposure ---
        exp_card, exp_layout = card()
        exp_header = QHBoxLayout()
        exp_header.addWidget(section_label("Exposure"))
        exp_header.addStretch()
        self._exposure_pill = _PillToggle()
        self._exposure_pill.toggled.connect(self._on_exposure_auto_toggled)
        exp_header.addWidget(self._exposure_pill)
        exp_layout.addLayout(exp_header)

        self._exposure_slider = QSlider(Qt.Orientation.Horizontal)
        self._exposure_slider.setStyleSheet(SLIDER_STYLE)
        self._exposure_slider.setRange(1, 5000)
        self._exposure_slider.setValue(200)
        self._exposure_slider.setEnabled(False)
        self._exposure_slider.valueChanged.connect(self._on_exposure_changed)
        exp_layout.addWidget(self._exposure_slider)

        self._exposure_label = value_label("200", enabled=False)
        exp_layout.addWidget(self._exposure_label, alignment=Qt.AlignmentFlag.AlignRight)
        layout.addWidget(exp_card)

        # --- ISO / Gain ---
        iso_card, iso_layout = card()
        iso_header = QHBoxLayout()
        iso_header.addWidget(section_label("ISO / Gain"))
        iso_header.addStretch()
        self._iso_label = value_label("32")
        iso_header.addWidget(self._iso_label)
        iso_layout.addLayout(iso_header)

        self._iso_slider = QSlider(Qt.Orientation.Horizontal)
        self._iso_slider.setStyleSheet(SLIDER_STYLE)
        self._iso_slider.setRange(0, 255)
        self._iso_slider.setValue(32)
        self._iso_slider.valueChanged.connect(self._on_iso_changed)
        iso_layout.addWidget(self._iso_slider)
        layout.addWidget(iso_card)

        # --- Focus ---
        focus_card, focus_layout = card()
        focus_header = QHBoxLayout()
        focus_header.addWidget(section_label("Focus"))
        focus_header.addStretch()
        self._focus_pill = _PillToggle()
        self._focus_pill.toggled.connect(self._on_focus_auto_toggled)
        focus_header.addWidget(self._focus_pill)
        focus_layout.addLayout(focus_header)

        self._focus_slider = QSlider(Qt.Orientation.Horizontal)
        self._focus_slider.setStyleSheet(SLIDER_STYLE)
        self._focus_slider.setRange(0, 1023)
        self._focus_slider.setValue(150)
        self._focus_slider.setEnabled(False)
        self._focus_slider.valueChanged.connect(self._on_focus_changed)
        focus_layout.addWidget(self._focus_slider)

        self._focus_label = value_label("150", enabled=False)
        focus_layout.addWidget(self._focus_label, alignment=Qt.AlignmentFlag.AlignRight)
        layout.addWidget(focus_card)

        layout.addStretch()

    def _on_resolution_changed(self, index: int):
        data = self._resolution_combo.itemData(index)
        if data:
            self.resolution_changed.emit(data[0], data[1])

    def _on_exposure_auto_toggled(self, auto: bool):
        self._exposure_slider.setEnabled(not auto)
        set_value_label_enabled(self._exposure_label, not auto)
        self.exposure_auto_changed.emit(auto)

    def _on_exposure_changed(self, value: int):
        self._exposure_label.setText(str(value))
        self.exposure_changed.emit(value)

    def _on_iso_changed(self, value: int):
        self._iso_label.setText(str(value))
        self.iso_changed.emit(value)

    def _on_focus_auto_toggled(self, auto: bool):
        self._focus_slider.setEnabled(not auto)
        set_value_label_enabled(self._focus_label, not auto)
        self.focus_auto_changed.emit(auto)

    def _on_focus_changed(self, value: int):
        self._focus_label.setText(str(value))
        self.focus_changed.emit(value)
