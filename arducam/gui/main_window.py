from datetime import datetime

from PyQt6.QtCore import QObject, QRunnable, QThreadPool, QTimer, pyqtSignal, pyqtSlot
from PyQt6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QMainWindow,
    QMessageBox,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from arducam.camera import ArducamCamera
from arducam.gui.controls import ControlsPanel
from arducam.gui.live_view import LiveViewWidget
from arducam.gui.recording_panel import RecordingPanel
from arducam.gui.styles import PANEL_BG, STATUS_BAR_STYLE
from arducam.recorder import RecordingFormat, VideoRecorder
from arducam.utils import save_capture


class _FullResCaptureSignals(QObject):
    finished = pyqtSignal(object)  # np.ndarray or None


class _FullResCaptureTask(QRunnable):
    """Runs capture_full_resolution() on a worker thread."""

    def __init__(self, camera: ArducamCamera):
        super().__init__()
        self.signals = _FullResCaptureSignals()
        self._camera = camera

    def run(self):
        frame = self._camera.capture_full_resolution()
        self.signals.finished.emit(frame)


class MainWindow(QMainWindow):
    def __init__(self, device_index: int = 0, simulate: bool = False):
        super().__init__()
        title = "Arducam IMX586 Controller"
        if simulate:
            title += " [SIMULATION]"
        self.setWindowTitle(title)
        self.setMinimumSize(1024, 700)

        self._camera = ArducamCamera(device_index, simulate=simulate)
        self._recorder = VideoRecorder()
        self._thread_pool = QThreadPool()

        # --- Layout ---
        central = QWidget()
        central.setStyleSheet(PANEL_BG)
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        main_layout.setSpacing(12)
        main_layout.setContentsMargins(12, 12, 12, 12)

        # Left: live view
        self._live_view = LiveViewWidget()
        main_layout.addWidget(self._live_view, stretch=3)

        # Right: controls + recording in a scroll-friendly column
        right_panel = QVBoxLayout()
        right_panel.setSpacing(0)
        self._controls = ControlsPanel()
        right_panel.addWidget(self._controls)
        self._recording_panel = RecordingPanel()
        right_panel.addWidget(self._recording_panel)
        main_layout.addLayout(right_panel, stretch=1)

        # Status bar
        self._status = QStatusBar()
        self._status.setStyleSheet(STATUS_BAR_STYLE)
        self.setStatusBar(self._status)

        # --- Frame timer ---
        self._frame_timer = QTimer(self)
        self._frame_timer.timeout.connect(self._poll_frame)

        # --- Connect control signals ---
        self._controls.resolution_changed.connect(self._on_resolution_changed)
        self._controls.exposure_changed.connect(self._camera.set_exposure)
        self._controls.exposure_auto_changed.connect(self._on_exposure_auto)
        self._controls.iso_changed.connect(self._camera.set_iso)
        self._controls.focus_changed.connect(self._camera.set_focus)
        self._controls.focus_auto_changed.connect(self._on_focus_auto)

        # --- Connect recording signals ---
        self._recording_panel.snap_requested.connect(self._on_snap)
        self._recording_panel.full_res_snap_requested.connect(self._on_full_res_snap)
        self._recording_panel.record_toggled.connect(self._on_record_toggled)

        # --- Open camera ---
        try:
            self._camera.open()
            fps = self._camera.get_fps_for_resolution(*self._camera.resolution) or 30
            self._frame_timer.start(1000 // fps)
            self._status.showMessage(
                f"Camera opened: {self._camera.resolution[0]}x{self._camera.resolution[1]} "
                f"@ {fps}fps"
            )
        except RuntimeError as e:
            self._status.showMessage(f"Camera error: {e}")

    def _poll_frame(self):
        frame = self._camera.get_frame()
        if frame is not None:
            self._live_view.update_frame(frame)
            if self._recorder.is_recording:
                self._recorder.write_frame(frame)

    # --- Control handlers ---

    def _on_resolution_changed(self, width: int, height: int):
        self._camera.set_resolution(width, height)
        fps = self._camera.get_fps_for_resolution(width, height) or 30
        self._frame_timer.setInterval(1000 // fps)
        self._status.showMessage(f"Resolution: {width}x{height} @ {fps}fps")

    def _on_exposure_auto(self, auto: bool):
        if auto:
            self._camera.set_exposure_auto()

    def _on_focus_auto(self, auto: bool):
        if auto:
            self._camera.set_focus_auto()

    # --- Snap handlers ---

    def _on_snap(self):
        frame = self._camera.get_frame()
        if frame is None:
            self._status.showMessage("Failed to capture frame")
            return
        settings = self._camera.get_current_settings()
        settings["full_resolution_capture"] = False
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filepath, _ = QFileDialog.getSaveFileName(
            self, "Save Image", f"capture_{timestamp}.png", "PNG Images (*.png)"
        )
        if filepath:
            save_capture(filepath, frame, settings)
            self._status.showMessage(f"Saved: {filepath}")

    def _on_full_res_snap(self):
        self._status.showMessage("Capturing full resolution (48MP)...")
        self._recording_panel.set_full_res_enabled(False)

        task = _FullResCaptureTask(self._camera)
        task.setAutoDelete(False)
        self._full_res_task = task  # prevent GC before signal delivery
        task.signals.finished.connect(self._on_full_res_done)
        self._thread_pool.start(task)

    @pyqtSlot(object)
    def _on_full_res_done(self, frame):
        self._recording_panel.set_full_res_enabled(True)
        if frame is None:
            self._status.showMessage("Full resolution capture failed")
            return
        settings = self._camera.get_current_settings()
        settings["full_resolution_capture"] = True
        settings["resolution"] = [8000, 6000]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filepath, _ = QFileDialog.getSaveFileName(
            self,
            "Save Full Resolution Image",
            f"capture_fullres_{timestamp}.png",
            "PNG Images (*.png)",
        )
        if filepath:
            save_capture(filepath, frame, settings)
            self._status.showMessage(f"Saved full-res: {filepath}")

    # --- Recording handlers ---

    def _on_record_toggled(self, start: bool):
        if start:
            w, h = self._camera.resolution
            source_fps = self._camera.get_fps_for_resolution(w, h) or 30
            target_fps = self._recording_panel.target_fps
            fmt = self._recording_panel.selected_format
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

            if fmt == RecordingFormat.IMAGE_SEQUENCE:
                filepath = QFileDialog.getExistingDirectory(
                    self, "Select Directory for Image Sequence", f"recording_{timestamp}"
                )
            else:
                ext = "avi" if fmt == RecordingFormat.MJPEG_AVI else "mp4"
                filepath, _ = QFileDialog.getSaveFileName(
                    self, "Save Video", f"recording_{timestamp}.{ext}", f"Video (*.{ext})"
                )

            if filepath:
                try:
                    self._recorder.start(filepath, w, h, source_fps, target_fps, fmt)
                    self._status.showMessage(f"Recording to: {filepath}")
                except RuntimeError as e:
                    QMessageBox.warning(self, "Recording Error", str(e))
                    self._recording_panel.reset_record_button()
            else:
                self._recording_panel.reset_record_button()
        else:
            count = self._recorder.frame_count
            self._recorder.stop()
            self._status.showMessage(f"Recording stopped ({count} frames)")

    # --- Cleanup ---

    def closeEvent(self, event):
        self._frame_timer.stop()
        self._recorder.stop()
        self._camera.close()
        super().closeEvent(event)
