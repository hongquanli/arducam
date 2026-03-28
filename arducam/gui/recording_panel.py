from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from arducam.gui.styles import (
    BTN_PRIMARY,
    BTN_RECORD,
    BTN_RECORD_STOP,
    BTN_SECONDARY,
    COMBO_STYLE,
    PANEL_BG,
    REC_STATUS_ACTIVE,
    REC_STATUS_IDLE,
    SPIN_STYLE,
    card,
    section_label,
    small_label,
)
from arducam.recorder import RecordingFormat


class RecordingPanel(QWidget):
    snap_requested = pyqtSignal()
    full_res_snap_requested = pyqtSignal()
    record_toggled = pyqtSignal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(PANEL_BG)
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(12, 12, 12, 12)

        # --- Capture buttons ---
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)
        self._snap_btn = QPushButton("Snap")
        self._snap_btn.setStyleSheet(BTN_PRIMARY)
        self._snap_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._snap_btn.clicked.connect(self.snap_requested.emit)
        btn_row.addWidget(self._snap_btn)

        self._full_res_btn = QPushButton("Full Res Snap")
        self._full_res_btn.setStyleSheet(BTN_SECONDARY)
        self._full_res_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._full_res_btn.clicked.connect(self.full_res_snap_requested.emit)
        btn_row.addWidget(self._full_res_btn)
        layout.addLayout(btn_row)

        # --- Recording card ---
        rec_card, rec_layout = card()
        rec_layout.setSpacing(10)

        rec_layout.addWidget(section_label("Recording"))

        # Format + FPS row
        settings_row = QHBoxLayout()
        settings_row.setSpacing(8)
        settings_row.addWidget(small_label("Format"))
        self._format_combo = QComboBox()
        self._format_combo.setStyleSheet(COMBO_STYLE)
        self._format_combo.addItem("MJPEG (.avi)", RecordingFormat.MJPEG_AVI)
        self._format_combo.addItem("H.264 (.mp4)", RecordingFormat.H264_MP4)
        self._format_combo.addItem("Sequence (.png)", RecordingFormat.IMAGE_SEQUENCE)
        settings_row.addWidget(self._format_combo, stretch=1)
        settings_row.addWidget(small_label("FPS"))
        self._fps_spin = QSpinBox()
        self._fps_spin.setStyleSheet(SPIN_STYLE)
        self._fps_spin.setRange(1, 120)
        self._fps_spin.setValue(30)
        settings_row.addWidget(self._fps_spin)
        rec_layout.addLayout(settings_row)

        # Record button
        self._record_btn = QPushButton("\u23fa Start Recording")
        self._record_btn.setStyleSheet(BTN_RECORD)
        self._record_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._record_btn.setCheckable(True)
        self._record_btn.toggled.connect(self._on_record_toggled)
        rec_layout.addWidget(self._record_btn)

        # Timed recording row
        timed_row = QHBoxLayout()
        timed_row.setSpacing(8)
        timed_row.addWidget(small_label("Duration"))
        self._duration_spin = QSpinBox()
        self._duration_spin.setStyleSheet(SPIN_STYLE)
        self._duration_spin.setRange(1, 3600)
        self._duration_spin.setValue(10)
        self._duration_spin.setSuffix("s")
        timed_row.addWidget(self._duration_spin)
        self._timed_btn = QPushButton("Timed Record")
        self._timed_btn.setStyleSheet(BTN_SECONDARY)
        self._timed_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._timed_btn.clicked.connect(self._on_timed_record)
        timed_row.addWidget(self._timed_btn, stretch=1)
        rec_layout.addLayout(timed_row)

        # Status
        self._rec_status = QLabel("Not recording")
        self._rec_status.setStyleSheet(REC_STATUS_IDLE)
        rec_layout.addWidget(self._rec_status)

        layout.addWidget(rec_card)
        layout.addStretch()

        # Timer
        self._rec_timer = QTimer(self)
        self._rec_timer.timeout.connect(self._update_rec_time)
        self._elapsed = 0
        self._timed_duration: int | None = None

    @property
    def selected_format(self) -> RecordingFormat:
        return self._format_combo.currentData()

    @property
    def target_fps(self) -> int:
        return self._fps_spin.value()

    def reset_record_button(self):
        self._record_btn.setChecked(False)

    def set_full_res_enabled(self, enabled: bool):
        self._full_res_btn.setEnabled(enabled)

    def _on_record_toggled(self, checked: bool):
        if checked:
            self._record_btn.setText("\u25a0 Stop Recording")
            self._record_btn.setStyleSheet(BTN_RECORD_STOP)
            self._rec_status.setText("Recording: 0s")
            self._rec_status.setStyleSheet(REC_STATUS_ACTIVE)
            self._elapsed = 0
            self._rec_timer.start(1000)
            self.record_toggled.emit(True)
        else:
            self._rec_timer.stop()
            self._record_btn.setText("\u23fa Start Recording")
            self._record_btn.setStyleSheet(BTN_RECORD)
            self._rec_status.setText("Not recording")
            self._rec_status.setStyleSheet(REC_STATUS_IDLE)
            self._timed_duration = None
            self.record_toggled.emit(False)

    def _on_timed_record(self):
        if self._record_btn.isChecked():
            return
        self._timed_duration = self._duration_spin.value()
        self._record_btn.setChecked(True)

    def _update_rec_time(self):
        self._elapsed += 1
        self._rec_status.setText(f"Recording: {self._elapsed}s")
        if self._timed_duration is not None and self._elapsed >= self._timed_duration:
            self._record_btn.setChecked(False)
