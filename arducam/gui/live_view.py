import numpy as np
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QImage, QPixmap
from PyQt6.QtWidgets import QLabel, QSizePolicy


class LiveViewWidget(QLabel):
    """Displays camera frames. Call update_frame(ndarray) to refresh."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMinimumSize(640, 480)
        self.setStyleSheet("background-color: black; color: white;")
        self.setText("No Camera Feed")

    def update_frame(self, frame: np.ndarray) -> None:
        # Keep reference to prevent GC before QImage is painted
        self._current_rgb = np.ascontiguousarray(frame[:, :, ::-1])  # BGR -> RGB
        h, w = self._current_rgb.shape[:2]
        bytes_per_line = 3 * w
        qimg = QImage(self._current_rgb.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
        scaled = qimg.scaled(
            self.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self.setPixmap(QPixmap.fromImage(scaled))
