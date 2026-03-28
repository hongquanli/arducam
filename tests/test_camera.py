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
