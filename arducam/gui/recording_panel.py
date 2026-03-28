from PyQt6.QtCore import QTimer, pyqtSignal
from PyQt6.QtWidgets import (
    QComboBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from arducam.recorder import RecordingFormat


class RecordingPanel(QWidget):
    snap_requested = pyqtSignal()
    full_res_snap_requested = pyqtSignal()
    record_toggled = pyqtSignal(bool)  # True=start, False=stop

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)

        # --- Capture ---
        snap_group = QGroupBox("Capture")
        snap_layout = QVBoxLayout(snap_group)
        self._snap_btn = QPushButton("Snap Image")
        self._snap_btn.clicked.connect(self.snap_requested.emit)
        snap_layout.addWidget(self._snap_btn)
        self._full_res_btn = QPushButton("Full Res Snap (48MP)")
        self._full_res_btn.clicked.connect(self.full_res_snap_requested.emit)
        snap_layout.addWidget(self._full_res_btn)
        layout.addWidget(snap_group)

        # --- Recording ---
        rec_group = QGroupBox("Recording")
        rec_layout = QVBoxLayout(rec_group)

        # Format selector
        fmt_layout = QHBoxLayout()
        fmt_layout.addWidget(QLabel("Format:"))
        self._format_combo = QComboBox()
        self._format_combo.addItem("MJPEG (.avi)", RecordingFormat.MJPEG_AVI)
        self._format_combo.addItem("H.264 (.mp4)", RecordingFormat.H264_MP4)
        self._format_combo.addItem("Image Sequence (.png)", RecordingFormat.IMAGE_SEQUENCE)
        fmt_layout.addWidget(self._format_combo)
        rec_layout.addLayout(fmt_layout)

        # Recording FPS
        fps_layout = QHBoxLayout()
        fps_layout.addWidget(QLabel("Rec FPS:"))
        self._fps_spin = QSpinBox()
        self._fps_spin.setRange(1, 120)
        self._fps_spin.setValue(30)
        fps_layout.addWidget(self._fps_spin)
        rec_layout.addLayout(fps_layout)

        # Start/Stop button
        self._record_btn = QPushButton("Start Recording")
        self._record_btn.setCheckable(True)
        self._record_btn.toggled.connect(self._on_record_toggled)
        rec_layout.addWidget(self._record_btn)

        # Timed recording
        timed_layout = QHBoxLayout()
        timed_layout.addWidget(QLabel("Duration (s):"))
        self._duration_spin = QSpinBox()
        self._duration_spin.setRange(1, 3600)
        self._duration_spin.setValue(10)
        timed_layout.addWidget(self._duration_spin)
        self._timed_btn = QPushButton("Timed Record")
        self._timed_btn.clicked.connect(self._on_timed_record)
        timed_layout.addWidget(self._timed_btn)
        rec_layout.addLayout(timed_layout)

        # Status
        self._rec_status = QLabel("Not recording")
        rec_layout.addWidget(self._rec_status)

        layout.addWidget(rec_group)
        layout.addStretch()

        # Timer for recording duration display
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

    def _on_record_toggled(self, checked: bool):
        if checked:
            self._record_btn.setText("Stop Recording")
            self._rec_status.setText("Recording: 0s")
            self._elapsed = 0
            self._rec_timer.start(1000)
            self.record_toggled.emit(True)
        else:
            self._rec_timer.stop()
            self._record_btn.setText("Start Recording")
            self._rec_status.setText("Not recording")
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
