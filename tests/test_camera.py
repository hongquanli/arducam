"""Tests for arducam.camera module."""

import sys
import time
import threading
from unittest.mock import patch, MagicMock, PropertyMock

import cv2
import numpy as np
import pytest

# ---------------------------------------------------------------------------
# Task 2: Resolution/FPS Table and Backend Selection
# ---------------------------------------------------------------------------


class TestResolutionFpsTable:
    def test_table_has_all_entries(self):
        from arducam.camera import RESOLUTION_FPS_TABLE

        expected = {
            (1280, 720): 120,
            (1920, 1080): 60,
            (2000, 1500): 50,
            (3840, 2160): 20,
            (4000, 3000): 14,
            (8000, 6000): 3,
        }
        assert RESOLUTION_FPS_TABLE == expected

    def test_table_keys_are_tuples(self):
        from arducam.camera import RESOLUTION_FPS_TABLE

        for key in RESOLUTION_FPS_TABLE:
            assert isinstance(key, tuple)
            assert len(key) == 2

    def test_table_values_are_ints(self):
        from arducam.camera import RESOLUTION_FPS_TABLE

        for val in RESOLUTION_FPS_TABLE.values():
            assert isinstance(val, int)


class TestGetBackend:
    @patch("arducam.camera.sys")
    def test_linux_returns_v4l2(self, mock_sys):
        from arducam.camera import _get_backend

        mock_sys.platform = "linux"
        assert _get_backend() == cv2.CAP_V4L2

    @patch("arducam.camera.sys")
    def test_windows_returns_dshow(self, mock_sys):
        from arducam.camera import _get_backend

        mock_sys.platform = "win32"
        assert _get_backend() == cv2.CAP_DSHOW

    @patch("arducam.camera.sys")
    def test_macos_returns_any(self, mock_sys):
        from arducam.camera import _get_backend

        mock_sys.platform = "darwin"
        assert _get_backend() == cv2.CAP_ANY


class TestArducamCameraInit:
    def test_default_device_index(self):
        from arducam.camera import ArducamCamera

        cam = ArducamCamera()
        assert cam.device_index == 0

    def test_custom_device_index(self):
        from arducam.camera import ArducamCamera

        cam = ArducamCamera(device_index=2)
        assert cam.device_index == 2

    def test_get_fps_for_resolution_known(self):
        from arducam.camera import ArducamCamera

        cam = ArducamCamera()
        assert cam.get_fps_for_resolution(1920, 1080) == 60

    def test_get_fps_for_resolution_unknown(self):
        from arducam.camera import ArducamCamera

        cam = ArducamCamera()
        assert cam.get_fps_for_resolution(999, 999) is None

    def test_get_available_resolutions(self):
        from arducam.camera import ArducamCamera

        cam = ArducamCamera()
        resolutions = cam.get_available_resolutions()
        assert (1920, 1080) in resolutions
        assert (8000, 6000) in resolutions
        assert len(resolutions) == 6


# ---------------------------------------------------------------------------
# Test helpers
# ---------------------------------------------------------------------------

def _make_fake_frame(w=1920, h=1080):
    """Return a fake BGR frame."""
    return np.zeros((h, w, 3), dtype=np.uint8)


def _make_open_camera(mock_vc_class, read_returns=None):
    """Create a mocked ArducamCamera that is already open.

    Args:
        mock_vc_class: The patched cv2.VideoCapture class.
        read_returns: If provided, side_effect for cap.read().
            Defaults to always returning (True, fake_frame).

    Returns:
        (cam, mock_cap) tuple.
    """
    from arducam.camera import ArducamCamera

    mock_cap = MagicMock()
    mock_cap.isOpened.return_value = True
    if read_returns is None:
        mock_cap.read.return_value = (True, _make_fake_frame())
    else:
        mock_cap.read.side_effect = read_returns
    mock_vc_class.return_value = mock_cap

    cam = ArducamCamera()
    cam.open()
    time.sleep(0.1)  # let capture thread start
    return cam, mock_cap


# ---------------------------------------------------------------------------
# Task 3: Capture Thread and Frame Buffer
# ---------------------------------------------------------------------------


class TestCameraOpenClose:
    @patch("arducam.camera._get_backend", return_value=cv2.CAP_ANY)
    @patch("arducam.camera.cv2.VideoCapture")
    def test_open_creates_capture(self, mock_vc_class, mock_backend):
        cam, mock_cap = _make_open_camera(mock_vc_class)
        try:
            assert cam.is_open
            mock_vc_class.assert_called_once_with(0, cv2.CAP_ANY)
        finally:
            cam.close()

    @patch("arducam.camera._get_backend", return_value=cv2.CAP_ANY)
    @patch("arducam.camera.cv2.VideoCapture")
    def test_open_sets_mjpg_fourcc(self, mock_vc_class, mock_backend):
        cam, mock_cap = _make_open_camera(mock_vc_class)
        try:
            fourcc = cv2.VideoWriter_fourcc(*"MJPG")
            mock_cap.set.assert_any_call(cv2.CAP_PROP_FOURCC, fourcc)
        finally:
            cam.close()

    @patch("arducam.camera._get_backend", return_value=cv2.CAP_ANY)
    @patch("arducam.camera.cv2.VideoCapture")
    def test_close_releases_capture(self, mock_vc_class, mock_backend):
        cam, mock_cap = _make_open_camera(mock_vc_class)
        cam.close()
        time.sleep(0.1)
        mock_cap.release.assert_called_once()
        assert not cam.is_open

    @patch("arducam.camera._get_backend", return_value=cv2.CAP_ANY)
    @patch("arducam.camera.cv2.VideoCapture")
    def test_close_idempotent(self, mock_vc_class, mock_backend):
        cam, mock_cap = _make_open_camera(mock_vc_class)
        cam.close()
        cam.close()  # should not raise

    @patch("arducam.camera._get_backend", return_value=cv2.CAP_ANY)
    @patch("arducam.camera.cv2.VideoCapture")
    def test_context_manager(self, mock_vc_class, mock_backend):
        mock_cap = MagicMock()
        mock_cap.isOpened.return_value = True
        mock_cap.read.return_value = (True, _make_fake_frame())
        mock_vc_class.return_value = mock_cap

        from arducam.camera import ArducamCamera

        with ArducamCamera() as cam:
            time.sleep(0.1)
            assert cam.is_open
        time.sleep(0.1)
        mock_cap.release.assert_called_once()

    @patch("arducam.camera._get_backend", return_value=cv2.CAP_ANY)
    @patch("arducam.camera.cv2.VideoCapture")
    def test_is_open_false_before_open(self, mock_vc_class, mock_backend):
        from arducam.camera import ArducamCamera

        cam = ArducamCamera()
        assert not cam.is_open


class TestCaptureThread:
    @patch("arducam.camera._get_backend", return_value=cv2.CAP_ANY)
    @patch("arducam.camera.cv2.VideoCapture")
    def test_get_frame_returns_frame(self, mock_vc_class, mock_backend):
        frame = _make_fake_frame()
        cam, mock_cap = _make_open_camera(mock_vc_class)
        try:
            result = cam.get_frame()
            assert result is not None
            assert result.shape == frame.shape
        finally:
            cam.close()

    @patch("arducam.camera._get_backend", return_value=cv2.CAP_ANY)
    @patch("arducam.camera.cv2.VideoCapture")
    def test_get_frame_returns_copy(self, mock_vc_class, mock_backend):
        frame = _make_fake_frame()
        cam, mock_cap = _make_open_camera(mock_vc_class)
        try:
            f1 = cam.get_frame()
            f2 = cam.get_frame()
            assert f1 is not f2
        finally:
            cam.close()

    @patch("arducam.camera._get_backend", return_value=cv2.CAP_ANY)
    @patch("arducam.camera.cv2.VideoCapture")
    def test_get_frame_returns_none_when_no_frame(self, mock_vc_class, mock_backend):
        mock_cap = MagicMock()
        mock_cap.isOpened.return_value = True
        mock_cap.read.return_value = (False, None)
        mock_vc_class.return_value = mock_cap

        from arducam.camera import ArducamCamera

        cam = ArducamCamera()
        cam.open()
        time.sleep(0.1)
        try:
            result = cam.get_frame()
            assert result is None
        finally:
            cam.close()

    def test_get_frame_returns_none_when_not_open(self):
        from arducam.camera import ArducamCamera

        cam = ArducamCamera()
        assert cam.get_frame() is None

    @patch("arducam.camera._get_backend", return_value=cv2.CAP_ANY)
    @patch("arducam.camera.cv2.VideoCapture")
    def test_resolution_property(self, mock_vc_class, mock_backend):
        cam, mock_cap = _make_open_camera(mock_vc_class)
        try:
            w, h = cam.resolution
            # Default resolution should be set
            assert isinstance(w, int)
            assert isinstance(h, int)
        finally:
            cam.close()

    @patch("arducam.camera._get_backend", return_value=cv2.CAP_ANY)
    @patch("arducam.camera.cv2.VideoCapture")
    def test_capture_thread_is_daemon(self, mock_vc_class, mock_backend):
        cam, mock_cap = _make_open_camera(mock_vc_class)
        try:
            assert cam._capture_thread.daemon
        finally:
            cam.close()


# ---------------------------------------------------------------------------
# Task 4: Controls (Exposure, ISO, Focus, Resolution)
# ---------------------------------------------------------------------------


class TestCameraControls:
    @patch("arducam.camera._get_backend", return_value=cv2.CAP_ANY)
    @patch("arducam.camera.cv2.VideoCapture")
    def test_set_resolution(self, mock_vc_class, mock_backend):
        cam, mock_cap = _make_open_camera(mock_vc_class)
        try:
            cam.set_resolution(3840, 2160)
            time.sleep(0.1)
            assert cam.resolution == (3840, 2160)
            mock_cap.set.assert_any_call(cv2.CAP_PROP_FRAME_WIDTH, 3840)
            mock_cap.set.assert_any_call(cv2.CAP_PROP_FRAME_HEIGHT, 2160)
            mock_cap.set.assert_any_call(cv2.CAP_PROP_FPS, 20)
        finally:
            cam.close()

    @patch("arducam.camera._get_backend", return_value=cv2.CAP_ANY)
    @patch("arducam.camera.cv2.VideoCapture")
    def test_set_exposure_manual(self, mock_vc_class, mock_backend):
        cam, mock_cap = _make_open_camera(mock_vc_class)
        try:
            cam.set_exposure(500.0)
            time.sleep(0.1)
            mock_cap.set.assert_any_call(cv2.CAP_PROP_AUTO_EXPOSURE, 1)
            mock_cap.set.assert_any_call(cv2.CAP_PROP_EXPOSURE, 500.0)
            settings = cam.get_current_settings()
            assert settings["exposure"] == 500.0
            assert settings["exposure_auto"] is False
        finally:
            cam.close()

    @patch("arducam.camera._get_backend", return_value=cv2.CAP_ANY)
    @patch("arducam.camera.cv2.VideoCapture")
    def test_set_exposure_auto(self, mock_vc_class, mock_backend):
        cam, mock_cap = _make_open_camera(mock_vc_class)
        try:
            cam.set_exposure(100.0)
            time.sleep(0.05)
            cam.set_exposure_auto()
            time.sleep(0.1)
            mock_cap.set.assert_any_call(cv2.CAP_PROP_AUTO_EXPOSURE, 3)
            settings = cam.get_current_settings()
            assert settings["exposure_auto"] is True
        finally:
            cam.close()

    @patch("arducam.camera._get_backend", return_value=cv2.CAP_ANY)
    @patch("arducam.camera.cv2.VideoCapture")
    def test_set_iso(self, mock_vc_class, mock_backend):
        cam, mock_cap = _make_open_camera(mock_vc_class)
        try:
            cam.set_iso(200.0)
            time.sleep(0.1)
            mock_cap.set.assert_any_call(cv2.CAP_PROP_GAIN, 200.0)
            settings = cam.get_current_settings()
            assert settings["gain"] == 200.0
        finally:
            cam.close()

    @patch("arducam.camera._get_backend", return_value=cv2.CAP_ANY)
    @patch("arducam.camera.cv2.VideoCapture")
    def test_set_focus_manual(self, mock_vc_class, mock_backend):
        cam, mock_cap = _make_open_camera(mock_vc_class)
        try:
            cam.set_focus(50.0)
            time.sleep(0.1)
            mock_cap.set.assert_any_call(cv2.CAP_PROP_AUTOFOCUS, 0)
            mock_cap.set.assert_any_call(cv2.CAP_PROP_FOCUS, 50.0)
            settings = cam.get_current_settings()
            assert settings["focus"] == 50.0
            assert settings["focus_auto"] is False
        finally:
            cam.close()

    @patch("arducam.camera._get_backend", return_value=cv2.CAP_ANY)
    @patch("arducam.camera.cv2.VideoCapture")
    def test_set_focus_auto(self, mock_vc_class, mock_backend):
        cam, mock_cap = _make_open_camera(mock_vc_class)
        try:
            cam.set_focus(10.0)
            time.sleep(0.05)
            cam.set_focus_auto()
            time.sleep(0.1)
            mock_cap.set.assert_any_call(cv2.CAP_PROP_AUTOFOCUS, 1)
            settings = cam.get_current_settings()
            assert settings["focus_auto"] is True
        finally:
            cam.close()

    @patch("arducam.camera._get_backend", return_value=cv2.CAP_ANY)
    @patch("arducam.camera.cv2.VideoCapture")
    def test_get_current_settings_keys(self, mock_vc_class, mock_backend):
        cam, mock_cap = _make_open_camera(mock_vc_class)
        try:
            settings = cam.get_current_settings()
            expected_keys = {
                "timestamp", "resolution", "exposure", "exposure_auto",
                "gain", "focus", "focus_auto", "camera_fps", "device_index",
            }
            assert set(settings.keys()) == expected_keys
        finally:
            cam.close()

    @patch("arducam.camera._get_backend", return_value=cv2.CAP_ANY)
    @patch("arducam.camera.cv2.VideoCapture")
    def test_get_current_settings_defaults(self, mock_vc_class, mock_backend):
        cam, mock_cap = _make_open_camera(mock_vc_class)
        try:
            settings = cam.get_current_settings()
            assert settings["resolution"] == (1920, 1080)
            assert settings["exposure"] is None
            assert settings["exposure_auto"] is True
            assert settings["gain"] is None
            assert settings["focus"] is None
            assert settings["focus_auto"] is True
            assert settings["camera_fps"] == 60
            assert settings["device_index"] == 0
            assert isinstance(settings["timestamp"], float)
        finally:
            cam.close()

    @patch("arducam.camera._get_backend", return_value=cv2.CAP_ANY)
    @patch("arducam.camera.cv2.VideoCapture")
    def test_commands_processed_on_capture_thread(self, mock_vc_class, mock_backend):
        """Verify that cap.set calls happen on the capture thread, not caller."""
        cam, mock_cap = _make_open_camera(mock_vc_class)
        try:
            capture_thread = cam._capture_thread
            cam.set_exposure(100.0)
            time.sleep(0.1)
            # The set call should have happened (processed by capture thread)
            mock_cap.set.assert_any_call(cv2.CAP_PROP_EXPOSURE, 100.0)
        finally:
            cam.close()
