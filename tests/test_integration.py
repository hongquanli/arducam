"""
Integration tests — require a real Arducam IMX586 connected.
Run with: python -m pytest tests/test_integration.py -v -p no:napari
Skipped automatically if no camera is detected.
"""
import platform
import time

import pytest
import cv2
import numpy as np
from arducam.camera import ArducamCamera, _get_backend


def camera_available():
    try:
        cap = cv2.VideoCapture(0, _get_backend())
        available = cap.isOpened()
        cap.release()
        return available
    except Exception:
        return False


skip_no_camera = pytest.mark.skipif(
    not camera_available(), reason="No camera connected"
)


@skip_no_camera
class TestCameraIntegration:
    def test_open_and_capture(self):
        with ArducamCamera(0) as cam:
            time.sleep(0.2)
            frame = cam.get_frame()
            assert frame is not None
            assert len(frame.shape) == 3

    def test_set_resolution_1080p(self):
        with ArducamCamera(0) as cam:
            cam.set_resolution(1920, 1080)
            time.sleep(0.5)
            frame = cam.get_frame()
            assert frame is not None
            assert frame.shape[1] == 1920
            assert frame.shape[0] == 1080

    def test_set_exposure(self):
        with ArducamCamera(0) as cam:
            cam.set_exposure(500)
            time.sleep(0.2)
            frame = cam.get_frame()
            assert frame is not None

    def test_set_focus(self):
        with ArducamCamera(0) as cam:
            cam.set_focus(200)
            time.sleep(0.2)
            frame = cam.get_frame()
            assert frame is not None

    def test_full_resolution_capture(self):
        with ArducamCamera(0) as cam:
            time.sleep(0.5)
            frame = cam.capture_full_resolution()
            assert frame is not None
            assert frame.shape[1] == 8000
            assert frame.shape[0] == 6000
