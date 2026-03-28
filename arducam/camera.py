"""Arducam IMX586 48MP USB 3.0 camera control module."""

import sys
import time
import threading
import queue
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

    def get_fps_for_resolution(self, w: int, h: int) -> Optional[int]:
        """Return the FPS for a known resolution, or None."""
        return RESOLUTION_FPS_TABLE.get((w, h))

    def get_available_resolutions(self) -> list[tuple[int, int]]:
        """Return a list of supported (width, height) tuples."""
        return list(RESOLUTION_FPS_TABLE.keys())
