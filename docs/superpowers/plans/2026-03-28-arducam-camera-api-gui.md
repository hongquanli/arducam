# Arducam IMX586 Camera API & PyQt GUI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a cross-platform Python library and PyQt6 GUI for controlling an Arducam IMX586 48MP USB 3.0 camera with live view, image capture with metadata, and multi-format video recording.

**Architecture:** A dedicated capture thread owns `cv2.VideoCapture` exclusively, storing frames in a locked buffer and accepting control commands via a queue of callables. The GUI polls frames via QTimer, and full-resolution capture runs on a worker thread to avoid blocking the UI. The recorder handles frame skipping and multiple output formats independently of the camera.

**Tech Stack:** Python 3.10+, OpenCV (`cv2`), PyQt6, numpy, threading, queue

**Spec:** `docs/superpowers/specs/2026-03-28-arducam-camera-api-gui-design.md`

---

## File Structure

```
arducam/
├── __init__.py              # Exports: ArducamCamera, VideoRecorder, RecordingFormat, save_capture
├── camera.py                # ArducamCamera class, RESOLUTION_FPS_TABLE, _get_backend()
├── recorder.py              # VideoRecorder class, RecordingFormat enum
├── utils.py                 # save_capture(filepath, frame, settings)
├── gui/
│   ├── __init__.py          # Empty
│   ├── main_window.py       # MainWindow — wires camera, controls, live view, recording
│   ├── live_view.py         # LiveViewWidget(QLabel) — displays numpy frames
│   ├── controls.py          # ControlsPanel(QWidget) — resolution, exposure, ISO, focus
│   └── recording_panel.py   # RecordingPanel(QWidget) — snap, record, timed record
├── main.py                  # Entry point: python main.py
├── requirements.txt         # opencv-python, PyQt6, numpy
└── tests/
    ├── __init__.py          # Empty
    ├── test_camera.py       # Camera API unit tests (mocked cv2)
    ├── test_recorder.py     # Recorder unit tests (mocked cv2.VideoWriter)
    ├── test_utils.py        # save_capture tests (real filesystem, temp dir)
    └── test_integration.py  # Real camera tests (skipped without hardware)
```

---

## Task 1: Project Setup

**Files:**
- Create: `requirements.txt`
- Create: `arducam/__init__.py`
- Create: `arducam/gui/__init__.py`
- Create: `tests/__init__.py`

- [ ] **Step 1: Create requirements.txt**

```
opencv-python>=4.8.0
PyQt6>=6.5.0
numpy>=1.24.0
```

- [ ] **Step 2: Create package init files**

```python
# arducam/__init__.py
```

```python
# arducam/gui/__init__.py
```

```python
# tests/__init__.py
```

- [ ] **Step 3: Install dependencies**

Run: `pip install -r requirements.txt`
Expected: All packages install successfully.

- [ ] **Step 4: Verify imports**

Run: `python -c "import cv2; import PyQt6; import numpy; print('OK')"`
Expected: `OK`

- [ ] **Step 5: Initialize git and commit**

```bash
git init
git add requirements.txt arducam/__init__.py arducam/gui/__init__.py tests/__init__.py
git commit -m "chore: project setup with dependencies and package structure"
```

---

## Task 2: Camera API — Resolution/FPS Table and Backend Selection

**Files:**
- Create: `arducam/camera.py`
- Create: `tests/test_camera.py`

- [ ] **Step 1: Write failing tests for resolution/FPS lookup and backend selection**

```python
# tests/test_camera.py
import pytest
from unittest.mock import patch

from arducam.camera import ArducamCamera, RESOLUTION_FPS_TABLE, _get_backend


class TestResolutionFpsTable:
    def test_table_has_six_entries(self):
        assert len(RESOLUTION_FPS_TABLE) == 6

    def test_known_resolutions(self):
        assert RESOLUTION_FPS_TABLE[(1280, 720)] == 120
        assert RESOLUTION_FPS_TABLE[(1920, 1080)] == 60
        assert RESOLUTION_FPS_TABLE[(2000, 1500)] == 50
        assert RESOLUTION_FPS_TABLE[(3840, 2160)] == 20
        assert RESOLUTION_FPS_TABLE[(4000, 3000)] == 14
        assert RESOLUTION_FPS_TABLE[(8000, 6000)] == 3


class TestGetFpsForResolution:
    def test_known_resolution(self):
        cam = ArducamCamera.__new__(ArducamCamera)
        assert cam.get_fps_for_resolution(1920, 1080) == 60

    def test_unknown_resolution_returns_none(self):
        cam = ArducamCamera.__new__(ArducamCamera)
        assert cam.get_fps_for_resolution(640, 480) is None

    def test_available_resolutions(self):
        cam = ArducamCamera.__new__(ArducamCamera)
        resolutions = cam.get_available_resolutions()
        assert len(resolutions) == 6
        assert (1920, 1080) in resolutions
        assert (8000, 6000) in resolutions


class TestGetBackend:
    @patch("arducam.camera.platform.system", return_value="Linux")
    def test_linux_uses_v4l2(self, _mock):
        import cv2
        assert _get_backend() == cv2.CAP_V4L2

    @patch("arducam.camera.platform.system", return_value="Windows")
    def test_windows_uses_dshow(self, _mock):
        import cv2
        assert _get_backend() == cv2.CAP_DSHOW

    @patch("arducam.camera.platform.system", return_value="Darwin")
    def test_other_uses_cap_any(self, _mock):
        import cv2
        assert _get_backend() == cv2.CAP_ANY
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_camera.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'arducam.camera'`

- [ ] **Step 3: Implement camera module with FPS table and backend selection**

```python
# arducam/camera.py
import platform
import queue
import threading
from typing import Optional

import cv2
import numpy as np

RESOLUTION_FPS_TABLE: dict[tuple[int, int], int] = {
    (1280, 720): 120,
    (1920, 1080): 60,
    (2000, 1500): 50,
    (3840, 2160): 20,
    (4000, 3000): 14,
    (8000, 6000): 3,
}


def _get_backend() -> int:
    system = platform.system()
    if system == "Linux":
        return cv2.CAP_V4L2
    elif system == "Windows":
        return cv2.CAP_DSHOW
    else:
        return cv2.CAP_ANY


class ArducamCamera:
    def __init__(self, device_index: int = 0):
        self._device_index = device_index
        self._resolution: tuple[int, int] = (1920, 1080)

    def get_fps_for_resolution(self, width: int, height: int) -> Optional[int]:
        return RESOLUTION_FPS_TABLE.get((width, height))

    def get_available_resolutions(self) -> list[tuple[int, int]]:
        return list(RESOLUTION_FPS_TABLE.keys())
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_camera.py -v`
Expected: All 9 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add arducam/camera.py tests/test_camera.py
git commit -m "feat: camera module with resolution/FPS table and backend selection"
```

---

## Task 3: Camera API — Capture Thread and Frame Buffer

**Files:**
- Modify: `arducam/camera.py`
- Modify: `tests/test_camera.py`

- [ ] **Step 1: Write failing tests for open/close, capture thread, and get_frame**

```python
# Add to tests/test_camera.py
import time
import numpy as np
from unittest.mock import MagicMock, patch, call


class TestCameraOpenClose:
    @patch("arducam.camera._get_backend", return_value=cv2.CAP_V4L2)
    @patch("arducam.camera.cv2.VideoCapture")
    def test_open_starts_capture_thread(self, mock_vc_class, _backend):
        mock_cap = MagicMock()
        mock_cap.isOpened.return_value = True
        mock_cap.read.return_value = (True, np.zeros((1080, 1920, 3), dtype=np.uint8))
        mock_vc_class.return_value = mock_cap

        cam = ArducamCamera(device_index=2)
        cam.open()
        try:
            mock_vc_class.assert_called_once_with(2, cv2.CAP_V4L2)
            assert cam.is_open
        finally:
            cam.close()

    @patch("arducam.camera._get_backend", return_value=cv2.CAP_V4L2)
    @patch("arducam.camera.cv2.VideoCapture")
    def test_open_raises_on_failure(self, mock_vc_class, _backend):
        mock_cap = MagicMock()
        mock_cap.isOpened.return_value = False
        mock_vc_class.return_value = mock_cap

        cam = ArducamCamera()
        with pytest.raises(RuntimeError, match="Failed to open camera"):
            cam.open()

    @patch("arducam.camera._get_backend", return_value=cv2.CAP_V4L2)
    @patch("arducam.camera.cv2.VideoCapture")
    def test_close_stops_thread_and_releases(self, mock_vc_class, _backend):
        mock_cap = MagicMock()
        mock_cap.isOpened.return_value = True
        mock_cap.read.return_value = (True, np.zeros((1080, 1920, 3), dtype=np.uint8))
        mock_vc_class.return_value = mock_cap

        cam = ArducamCamera()
        cam.open()
        cam.close()

        assert not cam.is_open
        mock_cap.release.assert_called_once()

    @patch("arducam.camera._get_backend", return_value=cv2.CAP_V4L2)
    @patch("arducam.camera.cv2.VideoCapture")
    def test_context_manager(self, mock_vc_class, _backend):
        mock_cap = MagicMock()
        mock_cap.isOpened.return_value = True
        mock_cap.read.return_value = (True, np.zeros((1080, 1920, 3), dtype=np.uint8))
        mock_vc_class.return_value = mock_cap

        with ArducamCamera() as cam:
            assert cam.is_open
        mock_cap.release.assert_called_once()


class TestGetFrame:
    @patch("arducam.camera._get_backend", return_value=cv2.CAP_V4L2)
    @patch("arducam.camera.cv2.VideoCapture")
    def test_get_frame_returns_latest_frame(self, mock_vc_class, _backend):
        fake_frame = np.full((1080, 1920, 3), 42, dtype=np.uint8)
        mock_cap = MagicMock()
        mock_cap.isOpened.return_value = True
        mock_cap.read.return_value = (True, fake_frame)
        mock_vc_class.return_value = mock_cap

        with ArducamCamera() as cam:
            time.sleep(0.1)  # let capture thread grab a frame
            frame = cam.get_frame()
            assert frame is not None
            assert frame.shape == (1080, 1920, 3)

    @patch("arducam.camera._get_backend", return_value=cv2.CAP_V4L2)
    @patch("arducam.camera.cv2.VideoCapture")
    def test_get_frame_returns_none_before_first_capture(self, mock_vc_class, _backend):
        mock_cap = MagicMock()
        mock_cap.isOpened.return_value = True
        mock_cap.read.return_value = (False, None)
        mock_vc_class.return_value = mock_cap

        with ArducamCamera() as cam:
            frame = cam.get_frame()
            assert frame is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_camera.py::TestCameraOpenClose -v`
Expected: FAIL — `AttributeError: 'ArducamCamera' object has no attribute 'open'`

- [ ] **Step 3: Implement capture thread, open/close, get_frame**

Replace the `ArducamCamera` class in `arducam/camera.py` with:

```python
class ArducamCamera:
    def __init__(self, device_index: int = 0):
        self._device_index = device_index
        self._resolution: tuple[int, int] = (1920, 1080)
        self._cap: Optional[cv2.VideoCapture] = None
        self._frame: Optional[np.ndarray] = None
        self._frame_lock = threading.Lock()
        self._cmd_queue: queue.Queue = queue.Queue()
        self._thread: Optional[threading.Thread] = None
        self._running = False

    # --- Public: lifecycle ---

    def open(self) -> None:
        backend = _get_backend()
        self._cap = cv2.VideoCapture(self._device_index, backend)
        if not self._cap.isOpened():
            self._cap = None
            raise RuntimeError(f"Failed to open camera at index {self._device_index}")
        self._cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))
        self._apply_resolution(self._resolution[0], self._resolution[1])
        self._running = True
        self._thread = threading.Thread(target=self._capture_loop, daemon=True)
        self._thread.start()

    def close(self) -> None:
        self._running = False
        if self._thread is not None:
            self._thread.join(timeout=2.0)
            self._thread = None
        if self._cap is not None:
            self._cap.release()
            self._cap = None
        with self._frame_lock:
            self._frame = None

    def __enter__(self):
        self.open()
        return self

    def __exit__(self, *args):
        self.close()

    @property
    def is_open(self) -> bool:
        return self._cap is not None and self._running

    @property
    def resolution(self) -> tuple[int, int]:
        return self._resolution

    # --- Public: frame access ---

    def get_frame(self) -> Optional[np.ndarray]:
        with self._frame_lock:
            return self._frame.copy() if self._frame is not None else None

    # --- Public: queries ---

    def get_fps_for_resolution(self, width: int, height: int) -> Optional[int]:
        return RESOLUTION_FPS_TABLE.get((width, height))

    def get_available_resolutions(self) -> list[tuple[int, int]]:
        return list(RESOLUTION_FPS_TABLE.keys())

    # --- Internal: capture thread ---

    def _capture_loop(self) -> None:
        while self._running:
            # Process pending commands
            while not self._cmd_queue.empty():
                try:
                    cmd = self._cmd_queue.get_nowait()
                    cmd(self._cap)
                except queue.Empty:
                    break
            # Grab frame
            ret, frame = self._cap.read()
            if ret:
                with self._frame_lock:
                    self._frame = frame

    def _apply_resolution(self, width: int, height: int) -> None:
        """Called on the thread that owns _cap (main thread during open, capture thread via queue)."""
        self._cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
        fps = self.get_fps_for_resolution(width, height)
        if fps is not None:
            self._cap.set(cv2.CAP_PROP_FPS, fps)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_camera.py -v`
Expected: All tests PASS.

- [ ] **Step 5: Commit**

```bash
git add arducam/camera.py tests/test_camera.py
git commit -m "feat: capture thread with frame buffer, open/close lifecycle"
```

---

## Task 4: Camera API — Controls (Exposure, ISO, Focus, Resolution)

**Files:**
- Modify: `arducam/camera.py`
- Modify: `tests/test_camera.py`

- [ ] **Step 1: Write failing tests for camera controls**

```python
# Add to tests/test_camera.py
import cv2


def _make_open_camera(mock_vc_class):
    """Helper: create an ArducamCamera with mocked capture, opened and ready."""
    fake_frame = np.zeros((1080, 1920, 3), dtype=np.uint8)
    mock_cap = MagicMock()
    mock_cap.isOpened.return_value = True
    mock_cap.read.return_value = (True, fake_frame)
    mock_vc_class.return_value = mock_cap
    cam = ArducamCamera()
    cam.open()
    time.sleep(0.05)  # let capture thread start
    return cam, mock_cap


class TestCameraControls:
    @patch("arducam.camera._get_backend", return_value=cv2.CAP_V4L2)
    @patch("arducam.camera.cv2.VideoCapture")
    def test_set_resolution(self, mock_vc_class, _backend):
        cam, mock_cap = _make_open_camera(mock_vc_class)
        try:
            cam.set_resolution(1280, 720)
            time.sleep(0.1)  # let command be processed
            mock_cap.set.assert_any_call(cv2.CAP_PROP_FRAME_WIDTH, 1280)
            mock_cap.set.assert_any_call(cv2.CAP_PROP_FRAME_HEIGHT, 720)
            mock_cap.set.assert_any_call(cv2.CAP_PROP_FPS, 120)
            assert cam.resolution == (1280, 720)
        finally:
            cam.close()

    @patch("arducam.camera._get_backend", return_value=cv2.CAP_V4L2)
    @patch("arducam.camera.cv2.VideoCapture")
    def test_set_exposure_manual(self, mock_vc_class, _backend):
        cam, mock_cap = _make_open_camera(mock_vc_class)
        try:
            cam.set_exposure(500)
            time.sleep(0.1)
            mock_cap.set.assert_any_call(cv2.CAP_PROP_AUTO_EXPOSURE, 1)
            mock_cap.set.assert_any_call(cv2.CAP_PROP_EXPOSURE, 500)
        finally:
            cam.close()

    @patch("arducam.camera._get_backend", return_value=cv2.CAP_V4L2)
    @patch("arducam.camera.cv2.VideoCapture")
    def test_set_exposure_auto(self, mock_vc_class, _backend):
        cam, mock_cap = _make_open_camera(mock_vc_class)
        try:
            cam.set_exposure_auto()
            time.sleep(0.1)
            mock_cap.set.assert_any_call(cv2.CAP_PROP_AUTO_EXPOSURE, 3)
        finally:
            cam.close()

    @patch("arducam.camera._get_backend", return_value=cv2.CAP_V4L2)
    @patch("arducam.camera.cv2.VideoCapture")
    def test_set_iso(self, mock_vc_class, _backend):
        cam, mock_cap = _make_open_camera(mock_vc_class)
        try:
            cam.set_iso(32)
            time.sleep(0.1)
            mock_cap.set.assert_any_call(cv2.CAP_PROP_GAIN, 32)
        finally:
            cam.close()

    @patch("arducam.camera._get_backend", return_value=cv2.CAP_V4L2)
    @patch("arducam.camera.cv2.VideoCapture")
    def test_set_focus_manual(self, mock_vc_class, _backend):
        cam, mock_cap = _make_open_camera(mock_vc_class)
        try:
            cam.set_focus(150)
            time.sleep(0.1)
            mock_cap.set.assert_any_call(cv2.CAP_PROP_AUTOFOCUS, 0)
            mock_cap.set.assert_any_call(cv2.CAP_PROP_FOCUS, 150)
        finally:
            cam.close()

    @patch("arducam.camera._get_backend", return_value=cv2.CAP_V4L2)
    @patch("arducam.camera.cv2.VideoCapture")
    def test_set_focus_auto(self, mock_vc_class, _backend):
        cam, mock_cap = _make_open_camera(mock_vc_class)
        try:
            cam.set_focus_auto()
            time.sleep(0.1)
            mock_cap.set.assert_any_call(cv2.CAP_PROP_AUTOFOCUS, 1)
        finally:
            cam.close()

    @patch("arducam.camera._get_backend", return_value=cv2.CAP_V4L2)
    @patch("arducam.camera.cv2.VideoCapture")
    def test_get_current_settings(self, mock_vc_class, _backend):
        cam, mock_cap = _make_open_camera(mock_vc_class)
        try:
            cam.set_exposure(500)
            cam.set_iso(32)
            cam.set_focus(150)
            settings = cam.get_current_settings()
            assert settings["exposure"] == 500
            assert settings["gain"] == 32
            assert settings["focus"] == 150
            assert settings["resolution"] == [1920, 1080]
            assert settings["device_index"] == 0
            assert "timestamp" in settings
        finally:
            cam.close()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_camera.py::TestCameraControls -v`
Expected: FAIL — `AttributeError: 'ArducamCamera' object has no attribute 'set_resolution'`

- [ ] **Step 3: Implement controls and settings tracking**

Add to `ArducamCamera.__init__`:

```python
        # Settings state (tracked locally since querying from cap is unreliable cross-platform)
        self._exposure: Optional[int] = None
        self._exposure_auto: bool = True
        self._gain: Optional[int] = None
        self._focus: Optional[int] = None
        self._focus_auto: bool = True
```

Add these methods to `ArducamCamera`:

```python
    # --- Public: controls (queued to capture thread) ---

    def set_resolution(self, width: int, height: int) -> None:
        self._resolution = (width, height)
        self._cmd_queue.put(lambda cap: self._apply_resolution(width, height))

    def set_exposure(self, value: int) -> None:
        self._exposure = value
        self._exposure_auto = False
        def _cmd(cap):
            cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 1)  # manual
            cap.set(cv2.CAP_PROP_EXPOSURE, value)
        self._cmd_queue.put(_cmd)

    def set_exposure_auto(self) -> None:
        self._exposure_auto = True
        self._cmd_queue.put(lambda cap: cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 3))

    def set_iso(self, value: int) -> None:
        self._gain = value
        self._cmd_queue.put(lambda cap: cap.set(cv2.CAP_PROP_GAIN, value))

    def set_focus(self, position: int) -> None:
        self._focus = position
        self._focus_auto = False
        def _cmd(cap):
            cap.set(cv2.CAP_PROP_AUTOFOCUS, 0)
            cap.set(cv2.CAP_PROP_FOCUS, position)
        self._cmd_queue.put(_cmd)

    def set_focus_auto(self) -> None:
        self._focus_auto = True
        self._cmd_queue.put(lambda cap: cap.set(cv2.CAP_PROP_AUTOFOCUS, 1))

    def get_current_settings(self) -> dict:
        from datetime import datetime
        return {
            "timestamp": datetime.now().isoformat(),
            "resolution": list(self._resolution),
            "exposure": self._exposure,
            "exposure_auto": self._exposure_auto,
            "gain": self._gain,
            "focus": self._focus,
            "focus_auto": self._focus_auto,
            "camera_fps": self.get_fps_for_resolution(*self._resolution),
            "device_index": self._device_index,
        }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_camera.py -v`
Expected: All tests PASS.

- [ ] **Step 5: Commit**

```bash
git add arducam/camera.py tests/test_camera.py
git commit -m "feat: camera controls — exposure, ISO, focus, resolution via command queue"
```

---

## Task 5: Camera API — Full-Resolution Capture

**Files:**
- Modify: `arducam/camera.py`
- Modify: `tests/test_camera.py`

- [ ] **Step 1: Write failing test for full-resolution capture**

```python
# Add to tests/test_camera.py

class TestFullResCapture:
    @patch("arducam.camera._get_backend", return_value=cv2.CAP_V4L2)
    @patch("arducam.camera.cv2.VideoCapture")
    def test_capture_full_resolution_returns_frame(self, mock_vc_class, _backend):
        full_res_frame = np.full((6000, 8000, 3), 99, dtype=np.uint8)
        normal_frame = np.zeros((1080, 1920, 3), dtype=np.uint8)

        mock_cap = MagicMock()
        mock_cap.isOpened.return_value = True
        # read() returns normal frames, then full-res when resolution changes
        mock_cap.read.return_value = (True, normal_frame)
        mock_vc_class.return_value = mock_cap

        # Override read to return full-res frame after resolution is set to 8000x6000
        original_set = mock_cap.set
        def _set_side_effect(prop, val):
            if prop == cv2.CAP_PROP_FRAME_WIDTH and val == 8000:
                mock_cap.read.return_value = (True, full_res_frame)
            elif prop == cv2.CAP_PROP_FRAME_WIDTH and val == 1920:
                mock_cap.read.return_value = (True, normal_frame)
        mock_cap.set.side_effect = _set_side_effect

        cam = ArducamCamera()
        cam.open()
        try:
            time.sleep(0.05)
            frame = cam.capture_full_resolution()
            assert frame is not None
            assert frame.shape == (6000, 8000, 3)
            # Should have restored original resolution
            assert cam.resolution == (1920, 1080)
        finally:
            cam.close()

    @patch("arducam.camera._get_backend", return_value=cv2.CAP_V4L2)
    @patch("arducam.camera.cv2.VideoCapture")
    def test_capture_full_resolution_settings_include_flag(self, mock_vc_class, _backend):
        cam, mock_cap = _make_open_camera(mock_vc_class)
        try:
            settings = cam.get_current_settings()
            assert "full_resolution_capture" not in settings or settings.get("full_resolution_capture") is False
        finally:
            cam.close()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_camera.py::TestFullResCapture -v`
Expected: FAIL — `AttributeError: 'ArducamCamera' object has no attribute 'capture_full_resolution'`

- [ ] **Step 3: Implement capture_full_resolution**

Add to `ArducamCamera`:

```python
    def capture_full_resolution(self) -> Optional[np.ndarray]:
        """Capture a single frame at 8000x6000. Blocks caller. Thread-safe."""
        result_frame: list[Optional[np.ndarray]] = [None]
        done_event = threading.Event()
        original_res = self._resolution

        def _cmd(cap):
            # Switch to full resolution
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, 8000)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 6000)
            fps = self.get_fps_for_resolution(8000, 6000)
            if fps is not None:
                cap.set(cv2.CAP_PROP_FPS, fps)
            # Grab frame
            ret, frame = cap.read()
            if ret:
                result_frame[0] = frame
            # Restore original resolution
            self._apply_resolution(original_res[0], original_res[1])
            done_event.set()

        self._cmd_queue.put(_cmd)
        done_event.wait(timeout=10.0)
        return result_frame[0]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_camera.py -v`
Expected: All tests PASS.

- [ ] **Step 5: Commit**

```bash
git add arducam/camera.py tests/test_camera.py
git commit -m "feat: full-resolution capture with resolution swap and restore"
```

---

## Task 6: Utilities — save_capture with JSON Sidecar

**Files:**
- Create: `arducam/utils.py`
- Create: `tests/test_utils.py`

- [ ] **Step 1: Write failing tests for save_capture**

```python
# tests/test_utils.py
import json
import os
import tempfile

import cv2
import numpy as np
import pytest

from arducam.utils import save_capture


class TestSaveCapture:
    def test_saves_png_and_json(self):
        frame = np.full((100, 200, 3), 128, dtype=np.uint8)
        settings = {
            "timestamp": "2026-03-28T14:30:22.456789",
            "resolution": [200, 100],
            "exposure": 500,
            "exposure_auto": False,
            "gain": 32,
            "focus": 150,
            "focus_auto": False,
            "camera_fps": 60,
            "device_index": 0,
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = os.path.join(tmpdir, "capture.png")
            save_capture(filepath, frame, settings)

            # PNG exists and is readable
            assert os.path.exists(filepath)
            loaded = cv2.imread(filepath)
            assert loaded is not None
            assert loaded.shape == (100, 200, 3)

            # JSON sidecar exists with correct content
            json_path = os.path.join(tmpdir, "capture.json")
            assert os.path.exists(json_path)
            with open(json_path) as f:
                meta = json.load(f)
            assert meta["exposure"] == 500
            assert meta["gain"] == 32
            assert meta["timestamp"] == "2026-03-28T14:30:22.456789"

    def test_handles_path_without_extension(self):
        frame = np.full((50, 50, 3), 0, dtype=np.uint8)
        settings = {"timestamp": "2026-01-01T00:00:00"}

        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = os.path.join(tmpdir, "image")
            save_capture(filepath, frame, settings)
            assert os.path.exists(filepath)  # saved as given
            json_path = os.path.join(tmpdir, "image.json")
            assert os.path.exists(json_path)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_utils.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'arducam.utils'`

- [ ] **Step 3: Implement save_capture**

```python
# arducam/utils.py
import json
import os

import cv2
import numpy as np


def save_capture(filepath: str, frame: np.ndarray, settings: dict) -> None:
    """Save a frame as PNG and write a JSON sidecar with camera settings."""
    cv2.imwrite(filepath, frame)

    base, _ = os.path.splitext(filepath)
    json_path = base + ".json"
    with open(json_path, "w") as f:
        json.dump(settings, f, indent=2)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_utils.py -v`
Expected: All 2 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add arducam/utils.py tests/test_utils.py
git commit -m "feat: save_capture utility with PNG and JSON sidecar"
```

---

## Task 7: Video Recorder — Core Lifecycle and MJPEG

**Files:**
- Create: `arducam/recorder.py`
- Create: `tests/test_recorder.py`

- [ ] **Step 1: Write failing tests for recorder lifecycle and MJPEG**

```python
# tests/test_recorder.py
import os
import tempfile
import time

import numpy as np
import pytest
from unittest.mock import MagicMock, patch

from arducam.recorder import VideoRecorder, RecordingFormat


class TestRecorderLifecycle:
    @patch("arducam.recorder.cv2.VideoWriter")
    def test_start_creates_writer(self, mock_writer_class):
        mock_writer = MagicMock()
        mock_writer.isOpened.return_value = True
        mock_writer_class.return_value = mock_writer

        rec = VideoRecorder()
        rec.start("output.avi", 1920, 1080, source_fps=60, target_fps=60, fmt=RecordingFormat.MJPEG_AVI)

        assert rec.is_recording
        mock_writer_class.assert_called_once()

    @patch("arducam.recorder.cv2.VideoWriter")
    def test_stop_releases_writer(self, mock_writer_class):
        mock_writer = MagicMock()
        mock_writer.isOpened.return_value = True
        mock_writer_class.return_value = mock_writer

        rec = VideoRecorder()
        rec.start("output.avi", 1920, 1080, source_fps=60, target_fps=60, fmt=RecordingFormat.MJPEG_AVI)
        rec.stop()

        assert not rec.is_recording
        mock_writer.release.assert_called_once()

    @patch("arducam.recorder.cv2.VideoWriter")
    def test_write_frame_increments_count(self, mock_writer_class):
        mock_writer = MagicMock()
        mock_writer.isOpened.return_value = True
        mock_writer_class.return_value = mock_writer

        rec = VideoRecorder()
        rec.start("output.avi", 1920, 1080, source_fps=60, target_fps=60, fmt=RecordingFormat.MJPEG_AVI)

        frame = np.zeros((1080, 1920, 3), dtype=np.uint8)
        rec.write_frame(frame)
        rec.write_frame(frame)

        assert rec.frame_count == 2
        assert mock_writer.write.call_count == 2

    def test_write_frame_when_not_recording_is_noop(self):
        rec = VideoRecorder()
        frame = np.zeros((100, 100, 3), dtype=np.uint8)
        rec.write_frame(frame)  # should not raise

    @patch("arducam.recorder.cv2.VideoWriter")
    def test_start_raises_on_writer_failure(self, mock_writer_class):
        mock_writer = MagicMock()
        mock_writer.isOpened.return_value = False
        mock_writer_class.return_value = mock_writer

        rec = VideoRecorder()
        with pytest.raises(RuntimeError, match="Failed to create video writer"):
            rec.start("output.avi", 1920, 1080, source_fps=60, target_fps=60, fmt=RecordingFormat.MJPEG_AVI)

    @patch("arducam.recorder.cv2.VideoWriter")
    def test_elapsed_seconds(self, mock_writer_class):
        mock_writer = MagicMock()
        mock_writer.isOpened.return_value = True
        mock_writer_class.return_value = mock_writer

        rec = VideoRecorder()
        rec.start("output.avi", 1920, 1080, source_fps=60, target_fps=60, fmt=RecordingFormat.MJPEG_AVI)
        time.sleep(0.2)
        assert rec.elapsed_seconds >= 0.1
        rec.stop()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_recorder.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'arducam.recorder'`

- [ ] **Step 3: Implement VideoRecorder with MJPEG support**

```python
# arducam/recorder.py
import os
import time
from enum import Enum
from typing import Optional

import cv2
import numpy as np


class RecordingFormat(Enum):
    MJPEG_AVI = "avi"
    H264_MP4 = "mp4"
    IMAGE_SEQUENCE = "png_sequence"


class VideoRecorder:
    def __init__(self):
        self._writer: Optional[cv2.VideoWriter] = None
        self._frame_count: int = 0
        self._start_time: Optional[float] = None
        self._fmt: Optional[RecordingFormat] = None
        self._seq_dir: Optional[str] = None
        self._source_fps: int = 30
        self._target_fps: int = 30
        self._frame_index: int = 0  # total frames received (for skip calc)

    @property
    def is_recording(self) -> bool:
        if self._fmt == RecordingFormat.IMAGE_SEQUENCE:
            return self._seq_dir is not None
        return self._writer is not None and self._writer.isOpened()

    @property
    def frame_count(self) -> int:
        return self._frame_count

    @property
    def elapsed_seconds(self) -> float:
        if self._start_time is None:
            return 0.0
        return time.monotonic() - self._start_time

    def start(self, filepath: str, width: int, height: int,
              source_fps: int, target_fps: int,
              fmt: RecordingFormat) -> None:
        self._source_fps = source_fps
        self._target_fps = target_fps
        self._frame_count = 0
        self._frame_index = 0
        self._fmt = fmt
        self._start_time = time.monotonic()

        if fmt == RecordingFormat.IMAGE_SEQUENCE:
            self._seq_dir = filepath  # filepath is a directory
            os.makedirs(self._seq_dir, exist_ok=True)
            self._writer = None
        else:
            if fmt == RecordingFormat.MJPEG_AVI:
                fourcc = cv2.VideoWriter_fourcc(*"MJPG")
            else:  # H264_MP4
                fourcc = cv2.VideoWriter_fourcc(*"mp4v")

            self._writer = cv2.VideoWriter(filepath, fourcc, target_fps, (width, height))
            if not self._writer.isOpened():
                self._writer = None
                self._fmt = None
                self._start_time = None
                raise RuntimeError(f"Failed to create video writer for {filepath}")

    def write_frame(self, frame: np.ndarray) -> None:
        if not self.is_recording:
            return

        # Frame skipping: decide whether to keep this frame
        if self._source_fps > self._target_fps:
            skip_interval = self._source_fps / self._target_fps
            self._frame_index += 1
            expected_count = int(self._frame_index / skip_interval)
            if expected_count <= self._frame_count:
                return

        if self._fmt == RecordingFormat.IMAGE_SEQUENCE:
            self._frame_count += 1
            filename = os.path.join(self._seq_dir, f"frame_{self._frame_count:06d}.png")
            cv2.imwrite(filename, frame)
        else:
            self._writer.write(frame)
            self._frame_count += 1

    def stop(self) -> None:
        if self._writer is not None:
            self._writer.release()
            self._writer = None
        self._seq_dir = None
        self._fmt = None
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_recorder.py -v`
Expected: All 6 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add arducam/recorder.py tests/test_recorder.py
git commit -m "feat: video recorder with MJPEG/H264/image-sequence and frame skipping"
```

---

## Task 8: Video Recorder — Frame Skipping and Image Sequence

**Files:**
- Modify: `tests/test_recorder.py`

- [ ] **Step 1: Write tests for frame skipping and image sequence**

```python
# Add to tests/test_recorder.py

class TestFrameSkipping:
    @patch("arducam.recorder.cv2.VideoWriter")
    def test_half_fps_skips_every_other_frame(self, mock_writer_class):
        mock_writer = MagicMock()
        mock_writer.isOpened.return_value = True
        mock_writer_class.return_value = mock_writer

        rec = VideoRecorder()
        rec.start("output.avi", 1920, 1080, source_fps=60, target_fps=30, fmt=RecordingFormat.MJPEG_AVI)

        frame = np.zeros((1080, 1920, 3), dtype=np.uint8)
        for _ in range(60):
            rec.write_frame(frame)

        # Should have written ~30 frames (half of 60)
        assert 28 <= rec.frame_count <= 32
        rec.stop()

    @patch("arducam.recorder.cv2.VideoWriter")
    def test_same_fps_writes_all_frames(self, mock_writer_class):
        mock_writer = MagicMock()
        mock_writer.isOpened.return_value = True
        mock_writer_class.return_value = mock_writer

        rec = VideoRecorder()
        rec.start("output.avi", 1920, 1080, source_fps=60, target_fps=60, fmt=RecordingFormat.MJPEG_AVI)

        frame = np.zeros((1080, 1920, 3), dtype=np.uint8)
        for _ in range(60):
            rec.write_frame(frame)

        assert rec.frame_count == 60
        rec.stop()


class TestImageSequence:
    def test_writes_numbered_pngs(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            seq_dir = os.path.join(tmpdir, "sequence")
            rec = VideoRecorder()
            rec.start(seq_dir, 100, 100, source_fps=10, target_fps=10, fmt=RecordingFormat.IMAGE_SEQUENCE)

            frame = np.full((100, 100, 3), 42, dtype=np.uint8)
            rec.write_frame(frame)
            rec.write_frame(frame)
            rec.write_frame(frame)
            rec.stop()

            assert rec.frame_count == 3
            assert os.path.exists(os.path.join(seq_dir, "frame_000001.png"))
            assert os.path.exists(os.path.join(seq_dir, "frame_000002.png"))
            assert os.path.exists(os.path.join(seq_dir, "frame_000003.png"))

            # Verify content
            loaded = cv2.imread(os.path.join(seq_dir, "frame_000001.png"))
            assert loaded is not None
            assert loaded.shape == (100, 100, 3)
```

- [ ] **Step 2: Run tests to verify they pass** (implementation already supports this)

Run: `python -m pytest tests/test_recorder.py -v`
Expected: All 9 tests PASS.

- [ ] **Step 3: Commit**

```bash
git add tests/test_recorder.py
git commit -m "test: frame skipping and image sequence recorder tests"
```

---

## Task 9: Package Exports

**Files:**
- Modify: `arducam/__init__.py`

- [ ] **Step 1: Add exports**

```python
# arducam/__init__.py
from arducam.camera import ArducamCamera, RESOLUTION_FPS_TABLE
from arducam.recorder import VideoRecorder, RecordingFormat
from arducam.utils import save_capture

__all__ = [
    "ArducamCamera",
    "RESOLUTION_FPS_TABLE",
    "VideoRecorder",
    "RecordingFormat",
    "save_capture",
]
```

- [ ] **Step 2: Verify imports work**

Run: `python -c "from arducam import ArducamCamera, VideoRecorder, RecordingFormat, save_capture; print('OK')"`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add arducam/__init__.py
git commit -m "feat: package exports for library usage"
```

---

## Task 10: GUI — Live View Widget

**Files:**
- Create: `arducam/gui/live_view.py`

- [ ] **Step 1: Implement LiveViewWidget**

```python
# arducam/gui/live_view.py
from PyQt6.QtWidgets import QLabel, QSizePolicy
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QImage, QPixmap
import numpy as np


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
```

- [ ] **Step 2: Commit**

```bash
git add arducam/gui/live_view.py
git commit -m "feat: live view widget for displaying camera frames"
```

---

## Task 11: GUI — Controls Panel

**Files:**
- Create: `arducam/gui/controls.py`

- [ ] **Step 1: Implement ControlsPanel**

```python
# arducam/gui/controls.py
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QSlider, QComboBox, QCheckBox, QGroupBox,
)
from PyQt6.QtCore import Qt, pyqtSignal

from arducam.camera import RESOLUTION_FPS_TABLE


class ControlsPanel(QWidget):
    resolution_changed = pyqtSignal(int, int)
    exposure_changed = pyqtSignal(int)
    exposure_auto_changed = pyqtSignal(bool)
    iso_changed = pyqtSignal(int)
    focus_changed = pyqtSignal(int)
    focus_auto_changed = pyqtSignal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)

        # --- Resolution ---
        res_group = QGroupBox("Resolution")
        res_layout = QVBoxLayout(res_group)
        self._resolution_combo = QComboBox()
        for (w, h), fps in RESOLUTION_FPS_TABLE.items():
            self._resolution_combo.addItem(f"{w}x{h} @ {fps}fps", (w, h))
        self._resolution_combo.setCurrentIndex(1)  # default 1920x1080
        self._resolution_combo.currentIndexChanged.connect(self._on_resolution_changed)
        res_layout.addWidget(self._resolution_combo)
        layout.addWidget(res_group)

        # --- Exposure ---
        exp_group = QGroupBox("Exposure")
        exp_layout = QVBoxLayout(exp_group)
        self._exposure_auto = QCheckBox("Auto Exposure")
        self._exposure_auto.setChecked(True)
        self._exposure_auto.toggled.connect(self._on_exposure_auto_toggled)
        exp_layout.addWidget(self._exposure_auto)

        exp_slider_layout = QHBoxLayout()
        self._exposure_slider = QSlider(Qt.Orientation.Horizontal)
        self._exposure_slider.setRange(1, 5000)
        self._exposure_slider.setValue(200)
        self._exposure_slider.setEnabled(False)
        self._exposure_slider.valueChanged.connect(self._on_exposure_changed)
        self._exposure_label = QLabel("200")
        self._exposure_label.setMinimumWidth(40)
        exp_slider_layout.addWidget(QLabel("Value:"))
        exp_slider_layout.addWidget(self._exposure_slider)
        exp_slider_layout.addWidget(self._exposure_label)
        exp_layout.addLayout(exp_slider_layout)
        layout.addWidget(exp_group)

        # --- ISO / Gain ---
        iso_group = QGroupBox("ISO / Gain")
        iso_layout = QHBoxLayout(iso_group)
        self._iso_slider = QSlider(Qt.Orientation.Horizontal)
        self._iso_slider.setRange(0, 255)
        self._iso_slider.setValue(32)
        self._iso_slider.valueChanged.connect(self._on_iso_changed)
        self._iso_label = QLabel("32")
        self._iso_label.setMinimumWidth(40)
        iso_layout.addWidget(QLabel("Gain:"))
        iso_layout.addWidget(self._iso_slider)
        iso_layout.addWidget(self._iso_label)
        layout.addWidget(iso_group)

        # --- Focus ---
        focus_group = QGroupBox("Focus")
        focus_layout = QVBoxLayout(focus_group)
        self._focus_auto = QCheckBox("Auto Focus")
        self._focus_auto.setChecked(True)
        self._focus_auto.toggled.connect(self._on_focus_auto_toggled)
        focus_layout.addWidget(self._focus_auto)

        focus_slider_layout = QHBoxLayout()
        self._focus_slider = QSlider(Qt.Orientation.Horizontal)
        self._focus_slider.setRange(0, 1023)
        self._focus_slider.setValue(150)
        self._focus_slider.setEnabled(False)
        self._focus_slider.valueChanged.connect(self._on_focus_changed)
        self._focus_label = QLabel("150")
        self._focus_label.setMinimumWidth(40)
        focus_slider_layout.addWidget(QLabel("Position:"))
        focus_slider_layout.addWidget(self._focus_slider)
        focus_slider_layout.addWidget(self._focus_label)
        focus_layout.addLayout(focus_slider_layout)
        layout.addWidget(focus_group)

        layout.addStretch()

    def _on_resolution_changed(self, index: int):
        data = self._resolution_combo.itemData(index)
        if data:
            self.resolution_changed.emit(data[0], data[1])

    def _on_exposure_auto_toggled(self, checked: bool):
        self._exposure_slider.setEnabled(not checked)
        self.exposure_auto_changed.emit(checked)

    def _on_exposure_changed(self, value: int):
        self._exposure_label.setText(str(value))
        self.exposure_changed.emit(value)

    def _on_iso_changed(self, value: int):
        self._iso_label.setText(str(value))
        self.iso_changed.emit(value)

    def _on_focus_auto_toggled(self, checked: bool):
        self._focus_slider.setEnabled(not checked)
        self.focus_auto_changed.emit(checked)

    def _on_focus_changed(self, value: int):
        self._focus_label.setText(str(value))
        self.focus_changed.emit(value)
```

- [ ] **Step 2: Commit**

```bash
git add arducam/gui/controls.py
git commit -m "feat: controls panel with resolution, exposure, ISO, focus"
```

---

## Task 12: GUI — Recording Panel

**Files:**
- Create: `arducam/gui/recording_panel.py`

- [ ] **Step 1: Implement RecordingPanel**

```python
# arducam/gui/recording_panel.py
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QSpinBox, QComboBox, QGroupBox,
)
from PyQt6.QtCore import pyqtSignal, QTimer

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
```

- [ ] **Step 2: Commit**

```bash
git add arducam/gui/recording_panel.py
git commit -m "feat: recording panel with snap, format selection, and timed recording"
```

---

## Task 13: GUI — Main Window

**Files:**
- Create: `arducam/gui/main_window.py`
- Create: `main.py`

- [ ] **Step 1: Implement MainWindow**

```python
# arducam/gui/main_window.py
from datetime import datetime

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QStatusBar, QFileDialog, QMessageBox,
)
from PyQt6.QtCore import QTimer, QRunnable, QThreadPool, pyqtSlot, QObject, pyqtSignal
import cv2
import numpy as np

from arducam.camera import ArducamCamera
from arducam.recorder import VideoRecorder, RecordingFormat
from arducam.utils import save_capture
from arducam.gui.live_view import LiveViewWidget
from arducam.gui.controls import ControlsPanel
from arducam.gui.recording_panel import RecordingPanel


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
    def __init__(self, device_index: int = 0):
        super().__init__()
        self.setWindowTitle("Arducam IMX586 Controller")
        self.setMinimumSize(1024, 700)

        self._camera = ArducamCamera(device_index)
        self._recorder = VideoRecorder()
        self._thread_pool = QThreadPool()

        # --- Layout ---
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)

        # Left: live view
        self._live_view = LiveViewWidget()
        main_layout.addWidget(self._live_view, stretch=3)

        # Right: controls + recording
        right_panel = QVBoxLayout()
        self._controls = ControlsPanel()
        right_panel.addWidget(self._controls)
        self._recording_panel = RecordingPanel()
        right_panel.addWidget(self._recording_panel)
        main_layout.addLayout(right_panel, stretch=1)

        # Status bar
        self._status = QStatusBar()
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
            self, "Save Image", f"capture_{timestamp}.png",
            "PNG Images (*.png)"
        )
        if filepath:
            save_capture(filepath, frame, settings)
            self._status.showMessage(f"Saved: {filepath}")

    def _on_full_res_snap(self):
        self._status.showMessage("Capturing full resolution (48MP)...")
        self._recording_panel._full_res_btn.setEnabled(False)

        task = _FullResCaptureTask(self._camera)
        task.signals.finished.connect(self._on_full_res_done)
        self._thread_pool.start(task)

    @pyqtSlot(object)
    def _on_full_res_done(self, frame):
        self._recording_panel._full_res_btn.setEnabled(True)
        if frame is None:
            self._status.showMessage("Full resolution capture failed")
            return
        settings = self._camera.get_current_settings()
        settings["full_resolution_capture"] = True
        settings["resolution"] = [8000, 6000]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filepath, _ = QFileDialog.getSaveFileName(
            self, "Save Full Resolution Image", f"capture_fullres_{timestamp}.png",
            "PNG Images (*.png)"
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
                    self, "Select Directory for Image Sequence",
                    f"recording_{timestamp}"
                )
            else:
                ext = "avi" if fmt == RecordingFormat.MJPEG_AVI else "mp4"
                filepath, _ = QFileDialog.getSaveFileName(
                    self, "Save Video", f"recording_{timestamp}.{ext}",
                    f"Video (*.{ext})"
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
```

- [ ] **Step 2: Implement main.py entry point**

```python
# main.py
import sys
from PyQt6.QtWidgets import QApplication
from arducam.gui.main_window import MainWindow


def main():
    app = QApplication(sys.argv)
    window = MainWindow(device_index=0)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
```

- [ ] **Step 3: Run the application to verify it launches**

Run: `python main.py`
Expected: Window opens. If no camera is connected, status bar shows error message but GUI is fully functional with all widgets visible.

- [ ] **Step 4: Commit**

```bash
git add arducam/gui/main_window.py main.py
git commit -m "feat: main window wiring camera, controls, live view, and recording"
```

---

## Task 14: Integration Tests

**Files:**
- Create: `tests/test_integration.py`

- [ ] **Step 1: Write integration tests (skipped without camera)**

```python
# tests/test_integration.py
"""
Integration tests — require a real Arducam IMX586 connected.
Run with: python -m pytest tests/test_integration.py -v
Skipped automatically if no camera is detected.
"""
import platform
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
            import time
            time.sleep(0.2)
            frame = cam.get_frame()
            assert frame is not None
            assert len(frame.shape) == 3

    def test_set_resolution_1080p(self):
        with ArducamCamera(0) as cam:
            cam.set_resolution(1920, 1080)
            import time
            time.sleep(0.5)
            frame = cam.get_frame()
            assert frame is not None
            assert frame.shape[1] == 1920
            assert frame.shape[0] == 1080

    def test_set_exposure(self):
        with ArducamCamera(0) as cam:
            cam.set_exposure(500)
            import time
            time.sleep(0.2)
            frame = cam.get_frame()
            assert frame is not None

    def test_set_focus(self):
        with ArducamCamera(0) as cam:
            cam.set_focus(200)
            import time
            time.sleep(0.2)
            frame = cam.get_frame()
            assert frame is not None

    def test_full_resolution_capture(self):
        with ArducamCamera(0) as cam:
            import time
            time.sleep(0.5)
            frame = cam.capture_full_resolution()
            assert frame is not None
            assert frame.shape[1] == 8000
            assert frame.shape[0] == 6000
```

- [ ] **Step 2: Run all tests**

Run: `python -m pytest tests/ -v`
Expected: Unit tests PASS, integration tests SKIP (no camera).

- [ ] **Step 3: Commit**

```bash
git add tests/test_integration.py
git commit -m "test: integration tests for real camera (skipped without hardware)"
```

---

## Summary

| Task | What it builds | Key files |
|------|---------------|-----------|
| 1 | Project setup | `requirements.txt`, package inits |
| 2 | FPS table + backend selection | `arducam/camera.py` |
| 3 | Capture thread + frame buffer | `arducam/camera.py` |
| 4 | Exposure, ISO, focus, resolution controls | `arducam/camera.py` |
| 5 | Full-resolution capture | `arducam/camera.py` |
| 6 | save_capture with JSON sidecar | `arducam/utils.py` |
| 7 | Recorder lifecycle + MJPEG | `arducam/recorder.py` |
| 8 | Frame skipping + image sequence tests | `tests/test_recorder.py` |
| 9 | Package exports | `arducam/__init__.py` |
| 10 | Live view widget | `arducam/gui/live_view.py` |
| 11 | Controls panel | `arducam/gui/controls.py` |
| 12 | Recording panel | `arducam/gui/recording_panel.py` |
| 13 | Main window + entry point | `arducam/gui/main_window.py`, `main.py` |
| 14 | Integration tests | `tests/test_integration.py` |
