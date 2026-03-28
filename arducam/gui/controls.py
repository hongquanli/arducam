from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from arducam.camera import RESOLUTION_FPS_TABLE


class ControlsPanel(QWidget):
    resolution_changed = pyqtSignal(int, int)
    exposure_changed = pyqtSignal(int)
    exposure_auto_changed = pyqtSignal(bool)
    iso_changed = pyqtSignal(int)
    focus_changed = pyqtSignal(int)
    focus_auto_changed = pyqtSignal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)

        # --- Resolution ---
        res_group = QGroupBox("Resolution")
        res_layout = QVBoxLayout(res_group)
        self._resolution_combo = QComboBox()
        for (w, h), fps in RESOLUTION_FPS_TABLE.items():
            self._resolution_combo.addItem(f"{w}x{h} @ {fps}fps", (w, h))
        self._resolution_combo.setCurrentIndex(1)  # default 1920x1080
        self._resolution_combo.currentIndexChanged.connect(self._on_resolution_changed)
        res_layout.addWidget(self._resolution_combo)
        layout.addWidget(res_group)

        # --- Exposure ---
        exp_group = QGroupBox("Exposure")
        exp_layout = QVBoxLayout(exp_group)
        self._exposure_auto = QCheckBox("Auto Exposure")
        self._exposure_auto.setChecked(True)
        self._exposure_auto.toggled.connect(self._on_exposure_auto_toggled)
        exp_layout.addWidget(self._exposure_auto)

        exp_slider_layout = QHBoxLayout()
        self._exposure_slider = QSlider(Qt.Orientation.Horizontal)
        self._exposure_slider.setRange(1, 5000)
        self._exposure_slider.setValue(200)
        self._exposure_slider.setEnabled(False)
        self._exposure_slider.valueChanged.connect(self._on_exposure_changed)
        self._exposure_label = QLabel("200")
        self._exposure_label.setMinimumWidth(40)
        exp_slider_layout.addWidget(QLabel("Value:"))
        exp_slider_layout.addWidget(self._exposure_slider)
        exp_slider_layout.addWidget(self._exposure_label)
        exp_layout.addLayout(exp_slider_layout)
        layout.addWidget(exp_group)

        # --- ISO / Gain ---
        iso_group = QGroupBox("ISO / Gain")
        iso_layout = QHBoxLayout(iso_group)
        self._iso_slider = QSlider(Qt.Orientation.Horizontal)
        self._iso_slider.setRange(0, 255)
        self._iso_slider.setValue(32)
        self._iso_slider.valueChanged.connect(self._on_iso_changed)
        self._iso_label = QLabel("32")
        self._iso_label.setMinimumWidth(40)
        iso_layout.addWidget(QLabel("Gain:"))
        iso_layout.addWidget(self._iso_slider)
        iso_layout.addWidget(self._iso_label)
        layout.addWidget(iso_group)

        # --- Focus ---
        focus_group = QGroupBox("Focus")
        focus_layout = QVBoxLayout(focus_group)
        self._focus_auto = QCheckBox("Auto Focus")
        self._focus_auto.setChecked(True)
        self._focus_auto.toggled.connect(self._on_focus_auto_toggled)
        focus_layout.addWidget(self._focus_auto)

        focus_slider_layout = QHBoxLayout()
        self._focus_slider = QSlider(Qt.Orientation.Horizontal)
        self._focus_slider.setRange(0, 1023)
        self._focus_slider.setValue(150)
        self._focus_slider.setEnabled(False)
        self._focus_slider.valueChanged.connect(self._on_focus_changed)
        self._focus_label = QLabel("150")
        self._focus_label.setMinimumWidth(40)
        focus_slider_layout.addWidget(QLabel("Position:"))
        focus_slider_layout.addWidget(self._focus_slider)
        focus_slider_layout.addWidget(self._focus_label)
        focus_layout.addLayout(focus_slider_layout)
        layout.addWidget(focus_group)

        layout.addStretch()

    def _on_resolution_changed(self, index: int):
        data = self._resolution_combo.itemData(index)
        if data:
            self.resolution_changed.emit(data[0], data[1])

    def _on_exposure_auto_toggled(self, checked: bool):
        self._exposure_slider.setEnabled(not checked)
        self.exposure_auto_changed.emit(checked)

    def _on_exposure_changed(self, value: int):
        self._exposure_label.setText(str(value))
        self.exposure_changed.emit(value)

    def _on_iso_changed(self, value: int):
        self._iso_label.setText(str(value))
        self.iso_changed.emit(value)

    def _on_focus_auto_toggled(self, checked: bool):
        self._focus_slider.setEnabled(not checked)
        self.focus_auto_changed.emit(checked)

    def _on_focus_changed(self, value: int):
        self._focus_label.setText(str(value))
        self.focus_changed.emit(value)
