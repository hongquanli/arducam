import numpy as np
from PyQt6.QtCore import QPointF, Qt
from PyQt6.QtGui import QImage, QMouseEvent, QPixmap, QWheelEvent
from PyQt6.QtWidgets import QLabel, QSizePolicy


class LiveViewWidget(QLabel):
    """Displays camera frames with mouse wheel zoom and click-drag pan."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMinimumSize(640, 480)
        self.setStyleSheet("background-color: black; color: white;")
        self.setText("No Camera Feed")
        self.setMouseTracking(True)

        self._zoom = 1.0
        self._pan = QPointF(0.0, 0.0)
        self._drag_start = None
        self._pan_start = None
        self._last_frame = None

    def update_frame(self, frame: np.ndarray) -> None:
        self._last_frame = frame
        self._render()

    def reset_view(self) -> None:
        """Reset zoom and pan to default."""
        self._zoom = 1.0
        self._pan = QPointF(0.0, 0.0)
        if self._last_frame is not None:
            self._render()

    def _display_bgr(self, bgr: np.ndarray) -> None:
        """Convert BGR frame to RGB, scale to widget, and display."""
        # Keep reference — QImage doesn't copy, so numpy must outlive the paint
        self._current_rgb = np.ascontiguousarray(bgr[:, :, ::-1])
        h, w = self._current_rgb.shape[:2]
        qimg = QImage(self._current_rgb.data, w, h, 3 * w, QImage.Format.Format_RGB888)
        scaled = qimg.scaled(
            self.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self.setPixmap(QPixmap.fromImage(scaled))

    def _render(self) -> None:
        frame = self._last_frame
        if frame is None:
            return

        if self._zoom <= 1.0:
            self._display_bgr(frame)
        else:
            h, w = frame.shape[:2]
            crop_w = max(1, int(w / self._zoom))
            crop_h = max(1, int(h / self._zoom))

            cx = w / 2 + self._pan.x()
            cy = h / 2 + self._pan.y()

            x1 = int(max(0, min(cx - crop_w / 2, w - crop_w)))
            y1 = int(max(0, min(cy - crop_h / 2, h - crop_h)))

            self._display_bgr(frame[y1 : y1 + crop_h, x1 : x1 + crop_w])

    def wheelEvent(self, event: QWheelEvent) -> None:
        delta = event.angleDelta().y()
        if delta > 0:
            self._zoom = min(self._zoom * 1.2, 20.0)
        elif delta < 0:
            self._zoom = max(self._zoom / 1.2, 1.0)
            if self._zoom <= 1.0:
                self._pan = QPointF(0.0, 0.0)
        if self._last_frame is not None:
            self._render()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton and self._zoom > 1.0:
            self._drag_start = event.position()
            self._pan_start = QPointF(self._pan)
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
        elif event.button() == Qt.MouseButton.MiddleButton:
            self.reset_view()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._drag_start is not None and self._last_frame is not None:
            delta = event.position() - self._drag_start
            w = self._last_frame.shape[1]
            widget_w = self.width()
            if widget_w == 0:
                return
            scale = w / (widget_w * self._zoom)
            self._pan = QPointF(
                self._pan_start.x() - delta.x() * scale,
                self._pan_start.y() - delta.y() * scale,
            )
            self._render()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_start = None
            self._pan_start = None
            if self._zoom > 1.0:
                self.setCursor(Qt.CursorShape.OpenHandCursor)
            else:
                self.setCursor(Qt.CursorShape.ArrowCursor)

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:
        self.reset_view()
