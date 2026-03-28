"""Arducam IMX586 48MP USB 3.0 camera control module."""

import queue
import sys
import threading
import time
from datetime import datetime
from typing import Optional

import cv2
import numpy as np

# ---------------------------------------------------------------------------
# Resolution / FPS table for the Arducam IMX586
# ---------------------------------------------------------------------------

RESOLUTION_FPS_TABLE: dict[tuple[int, int], int] = {
    (1280, 720): 120,
    (1920, 1080): 60,
    (2000, 1500): 50,
    (3840, 2160): 20,
    (4000, 3000): 14,
    (8000, 6000): 3,
}

_DEFAULT_RESOLUTION = (1920, 1080)


def _get_backend() -> int:
    """Return the appropriate OpenCV VideoCapture backend for the current OS."""
    if sys.platform.startswith("linux"):
        return cv2.CAP_V4L2
    elif sys.platform == "win32":
        return cv2.CAP_DSHOW
    return cv2.CAP_ANY


class ArducamCamera:
    """High-level API for the Arducam IMX586 camera."""

    def __init__(self, device_index: int = 0) -> None:
        self.device_index = device_index
        self._cap: Optional[cv2.VideoCapture] = None
        self._capture_thread: Optional[threading.Thread] = None
        self._running = False
        self._frame: Optional[np.ndarray] = None
        self._frame_lock = threading.Lock()
        self._cmd_queue: queue.Queue = queue.Queue()
        self._resolution: tuple[int, int] = _DEFAULT_RESOLUTION

        # Locally tracked settings (cross-platform reliable state)
        self._exposure: Optional[float] = None
        self._exposure_auto: bool = True
        self._gain: Optional[float] = None
        self._focus: Optional[float] = None
        self._focus_auto: bool = True

    # ------------------------------------------------------------------
    # Resolution helpers
    # ------------------------------------------------------------------

    def get_fps_for_resolution(self, w: int, h: int) -> Optional[int]:
        """Return the FPS for a known resolution, or None."""
        return RESOLUTION_FPS_TABLE.get((w, h))

    def get_available_resolutions(self) -> list[tuple[int, int]]:
        """Return a list of supported (width, height) tuples."""
        return list(RESOLUTION_FPS_TABLE.keys())

    # ------------------------------------------------------------------
    # Open / close
    # ------------------------------------------------------------------

    def open(self) -> None:
        """Open the camera and start the capture thread."""
        if self._running:
            return
        backend = _get_backend()
        self._cap = cv2.VideoCapture(self.device_index, backend)
        fourcc = cv2.VideoWriter_fourcc(*"MJPG")
        self._cap.set(cv2.CAP_PROP_FOURCC, fourcc)
        self._apply_resolution(self._resolution[0], self._resolution[1])
        self._running = True
        self._capture_thread = threading.Thread(target=self._capture_loop, daemon=True)
        self._capture_thread.start()

    def close(self) -> None:
        """Stop the capture thread and release the camera."""
        if not self._running:
            return
        self._running = False
        if self._capture_thread is not None:
            self._capture_thread.join(timeout=2.0)
            self._capture_thread = None
        if self._cap is not None:
            self._cap.release()
            self._cap = None
        with self._frame_lock:
            self._frame = None

    # ------------------------------------------------------------------
    # Context manager
    # ------------------------------------------------------------------

    def __enter__(self) -> "ArducamCamera":
        self.open()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def is_open(self) -> bool:
        return self._running

    @property
    def resolution(self) -> tuple[int, int]:
        return self._resolution

    # ------------------------------------------------------------------
    # Frame access
    # ------------------------------------------------------------------

    def get_frame(self) -> Optional[np.ndarray]:
        """Return a copy of the latest frame, or None."""
        if not self._running:
            return None
        with self._frame_lock:
            if self._frame is None:
                return None
            return self._frame.copy()

    # ------------------------------------------------------------------
    # Controls — queue commands to capture thread
    # ------------------------------------------------------------------

    def set_resolution(self, w: int, h: int) -> None:
        """Queue a resolution change."""
        self._cmd_queue.put(("set_resolution", (w, h)))

    def set_exposure(self, value: float) -> None:
        """Queue manual exposure setting."""
        self._exposure = value
        self._exposure_auto = False
        self._cmd_queue.put(("set_exposure", value))

    def set_exposure_auto(self) -> None:
        """Queue auto-exposure."""
        self._exposure_auto = True
        self._cmd_queue.put(("set_exposure_auto", None))

    def set_iso(self, value: float) -> None:
        """Queue gain/ISO setting."""
        self._gain = value
        self._cmd_queue.put(("set_iso", value))

    def set_focus(self, position: float) -> None:
        """Queue manual focus setting."""
        self._focus = position
        self._focus_auto = False
        self._cmd_queue.put(("set_focus", position))

    def set_focus_auto(self) -> None:
        """Queue autofocus enable."""
        self._focus_auto = True
        self._cmd_queue.put(("set_focus_auto", None))

    def get_current_settings(self) -> dict:
        """Return a dict of locally tracked settings."""
        return {
            "timestamp": datetime.now().isoformat(),
            "resolution": self._resolution,
            "exposure": self._exposure,
            "exposure_auto": self._exposure_auto,
            "gain": self._gain,
            "focus": self._focus,
            "focus_auto": self._focus_auto,
            "camera_fps": self.get_fps_for_resolution(*self._resolution),
            "device_index": self.device_index,
        }

    # ------------------------------------------------------------------
    # Full-resolution capture
    # ------------------------------------------------------------------

    def capture_full_resolution(self) -> Optional[np.ndarray]:
        """Capture a single frame at 8000x6000 then restore resolution.

        Blocks the caller up to 10 seconds.
        Returns the captured frame or None on timeout.
        """
        if not self._running:
            return None
        event = threading.Event()
        result: list[Optional[np.ndarray]] = [None]
        self._cmd_queue.put(("capture_full_res", (event, result)))
        if not event.wait(timeout=10.0):
            return None
        return result[0]

    # ------------------------------------------------------------------
    # Internal — capture loop (runs on daemon thread)
    # ------------------------------------------------------------------

    def _capture_loop(self) -> None:
        """Continuously read frames and process commands."""
        while self._running:
            # Process pending commands
            try:
                while True:
                    cmd, arg = self._cmd_queue.get_nowait()
                    self._handle_command(cmd, arg)
            except queue.Empty:
                pass

            # Read frame — cap.read() blocks until a frame is available,
            # but if read fails (no camera / error), sleep to avoid busy-wait
            if self._cap is not None:
                ret, frame = self._cap.read()
                if ret and frame is not None:
                    with self._frame_lock:
                        self._frame = frame
                else:
                    time.sleep(0.001)

    def _handle_command(self, cmd: str, arg) -> None:
        """Execute a command on the capture thread."""
        if cmd == "set_resolution":
            w, h = arg
            self._apply_resolution(w, h)
        elif cmd == "set_exposure":
            self._cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 1)
            self._cap.set(cv2.CAP_PROP_EXPOSURE, arg)
        elif cmd == "set_exposure_auto":
            self._cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 3)
        elif cmd == "set_iso":
            self._cap.set(cv2.CAP_PROP_GAIN, arg)
        elif cmd == "set_focus":
            self._cap.set(cv2.CAP_PROP_AUTOFOCUS, 0)
            self._cap.set(cv2.CAP_PROP_FOCUS, arg)
        elif cmd == "set_focus_auto":
            self._cap.set(cv2.CAP_PROP_AUTOFOCUS, 1)
        elif cmd == "capture_full_res":
            event, result = arg
            original = self._resolution
            self._apply_resolution(8000, 6000)
            ret, frame = self._cap.read()
            if ret and frame is not None:
                result[0] = frame
            self._apply_resolution(original[0], original[1])
            event.set()

    def _apply_resolution(self, w: int, h: int) -> None:
        """Set width, height, and FPS on the capture device."""
        if self._cap is None:
            return
        self._cap.set(cv2.CAP_PROP_FRAME_WIDTH, w)
        self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, h)
        fps = self.get_fps_for_resolution(w, h)
        if fps is not None:
            self._cap.set(cv2.CAP_PROP_FPS, fps)
        self._resolution = (w, h)
