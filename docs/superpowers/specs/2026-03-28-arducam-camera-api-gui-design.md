# Arducam IMX586 Camera API & PyQt GUI — Design Spec

## Overview

Python library and PyQt6 GUI for controlling an Arducam IMX586 48MP USB 3.0 camera (B0478) in machine vision/inspection workflows. The camera is UVC-compliant and works with OpenCV on both Linux (V4L2) and Windows (DirectShow).

## Requirements

### Camera API (Python library)
- Set exposure time (manual value or auto mode)
- Set ISO/gain
- Capture frames at current resolution
- Capture full-resolution stills (8000x6000) with automatic resolution swap
- Set resolution from supported table
- Query FPS for a given resolution
- Set focus position (motorized) or enable autofocus
- Return current settings as a dict for metadata

### PyQt GUI
- Live view with smooth frame display
- Parameter controls: resolution, exposure, ISO, focus (with auto toggles)
- Snap image at current resolution (PNG + JSON sidecar)
- Snap image at full resolution (pauses live view briefly)
- Start/stop video recording at user-selected FPS (can be lower than camera FPS)
- Fixed-duration timed recording
- Multiple recording formats: MJPEG/AVI, H.264/MP4, PNG image sequence

### Resolution/FPS Table

| Resolution | FPS |
|---|---|
| 1280x720 | 120 |
| 1920x1080 | 60 |
| 2000x1500 | 50 |
| 3840x2160 | 20 |
| 4000x3000 | 14 |
| 8000x6000 | 3 |

### Platform Support
- Linux (V4L2 backend)
- Windows (DirectShow backend)

## Architecture

### Approach: Dedicated Capture Thread

A background thread continuously grabs frames from `cv2.VideoCapture` and stores the latest frame behind a `threading.Lock`. The GUI reads from this buffer via a QTimer. Camera control commands are sent to the capture thread via a `queue.Queue` of callables — only the capture thread touches `VideoCapture`.

**Why this approach:**
- GUI stays responsive at all resolutions
- Full-resolution capture doesn't freeze the UI
- Thread-safe by design — single owner of `VideoCapture`
- Simpler than multiprocessing, sufficient for the use case

### Frame Flow

```
CaptureThread → shared buffer (Lock) → QTimer (main thread) → LiveViewWidget
                                                             → VideoRecorder.write_frame()
```

## Component Design

### 1. Camera API (`arducam/camera.py`)

Wraps `cv2.VideoCapture`. Only this module touches camera hardware.

**Cross-platform backend:**
```python
import platform

def _get_backend():
    if platform.system() == "Linux":
        return cv2.CAP_V4L2
    elif platform.system() == "Windows":
        return cv2.CAP_DSHOW
    else:
        return cv2.CAP_ANY
```

**Capture thread internals:**
- Runs a loop: check command queue for pending commands (set_exposure, set_resolution, etc.), then `cap.read()`, then store frame behind lock.
- `capture_full_resolution()`: signals capture thread to swap to 8000x6000, grab one frame, swap back. Blocks the caller via `threading.Event`. The GUI must call this from a worker thread (e.g. `QThreadPool.start()`) — never from the main thread.
- Commands are queued as callables so the capture thread is the sole accessor of `cap`.

**Public interface:**
```python
class ArducamCamera:
    def __init__(self, device_index: int = 0)
    def open(self) -> None
    def close(self) -> None
    def get_frame(self) -> np.ndarray | None
    def capture_full_resolution(self) -> np.ndarray | None
    def set_resolution(self, width: int, height: int) -> None
    def set_exposure(self, value: int) -> None
    def set_exposure_auto(self) -> None
    def set_iso(self, value: int) -> None
    def set_focus(self, position: int) -> None
    def set_focus_auto(self) -> None
    def get_fps_for_resolution(self, w: int, h: int) -> int | None
    def get_available_resolutions(self) -> list[tuple[int, int]]
    def get_current_settings(self) -> dict
    @property
    def resolution(self) -> tuple[int, int]
    @property
    def is_open(self) -> bool
```

### 2. Video Recorder (`arducam/recorder.py`)

Manages writing frames to disk. Separated from camera — independent lifecycle.

**Format support:**
```python
class RecordingFormat(Enum):
    MJPEG_AVI = "avi"
    H264_MP4 = "mp4"
    IMAGE_SEQUENCE = "png_sequence"
```

**H.264 note:** H.264 support depends on system codecs (`libx264` on Linux, platform codec on Windows). `start()` should attempt to open the writer and raise `RuntimeError` if the codec is unavailable, so the GUI can show an error and suggest MJPEG instead.

**Frame skipping:** Takes `source_fps` and `target_fps`. Computes skip interval internally. Caller calls `write_frame()` on every frame; recorder decides whether to write.

**Image sequence mode:** Creates a directory, writes `frame_000001.png`, `frame_000002.png`, etc.

**Public interface:**
```python
class VideoRecorder:
    def __init__(self)
    def start(self, filepath: str, width: int, height: int,
              source_fps: int, target_fps: int,
              fmt: RecordingFormat) -> None
    def write_frame(self, frame: np.ndarray) -> None
    def stop(self) -> None
    @property
    def is_recording(self) -> bool
    @property
    def frame_count(self) -> int
    @property
    def elapsed_seconds(self) -> float
```

### 3. Utilities (`arducam/utils.py`)

**`save_capture(filepath, frame, settings)`** — writes a PNG and a JSON sidecar with matching base name.

**Sidecar format:**
```json
{
    "timestamp": "2026-03-28T14:30:22.456789",
    "resolution": [1920, 1080],
    "exposure": 500,
    "exposure_auto": false,
    "gain": 32,
    "focus": 150,
    "focus_auto": false,
    "camera_fps": 60,
    "device_index": 0,
    "full_resolution_capture": false
}
```

### 4. GUI Widgets

#### `gui/live_view.py` — LiveViewWidget(QLabel)
Receives numpy frames, converts BGR→RGB, scales to fit with aspect ratio. Shows "No Camera Feed" placeholder.

#### `gui/controls.py` — ControlsPanel(QWidget)
- Resolution dropdown (from RESOLUTION_FPS_TABLE)
- Exposure slider + auto checkbox (slider disabled when auto)
- ISO/gain slider
- Focus slider + auto checkbox (slider disabled when auto)
- Emits signals: `resolution_changed`, `exposure_changed`, `exposure_auto_changed`, `iso_changed`, `focus_changed`, `focus_auto_changed`

#### `gui/recording_panel.py` — RecordingPanel(QWidget)
- Snap button (current resolution)
- Full-res snap button
- Format dropdown (AVI/MP4/image sequence)
- Recording FPS spinbox
- Start/stop toggle button
- Duration spinbox + timed record button
- Emits signals: `snap_requested`, `full_res_snap_requested`, `record_toggled(bool)`, `timed_record_requested(int)`

#### `gui/main_window.py` — MainWindow(QMainWindow)
- Opens camera on startup
- QTimer polls `camera.get_frame()`, pushes to live view and recorder
- Connects control panel signals to camera methods
- Snap: saves PNG + JSON sidecar via file dialog
- Full-res snap: calls `capture_full_resolution()`, saves PNG + JSON
- Recording: prompts for filepath, creates recorder with selected format/FPS
- Status bar shows resolution, FPS, recording state

**Layout:**
```
+-------------------------------------------+
|  [Live View - 70%]         | [Controls]   |
|                            | Resolution ▼  |
|                            | Exposure ——○  |
|                            | ISO ———————○  |
|                            | Focus ————○   |
|                            | [x] Auto Exp  |
|                            | [x] Auto Focus|
|                            |               |
|                            | --- Capture --|
|                            | [Snap]        |
|                            | [Full Res Snap]|
|                            |               |
|                            | --- Record ---|
|                            | Format: ▼     |
|                            | Rec FPS: [30] |
|                            | [Start/Stop]  |
|                            | Duration: [10]|
|                            | [Timed Record]|
+-------------------------------------------+
| Status: 1920x1080 @ 60fps | Recording: 5s |
+-------------------------------------------+
```

## File Structure

```
arducam/
├── __init__.py              # exports ArducamCamera, VideoRecorder, RecordingFormat
├── camera.py                # ArducamCamera class + RESOLUTION_FPS_TABLE
├── recorder.py              # VideoRecorder + RecordingFormat enum
├── utils.py                 # save_capture()
├── gui/
│   ├── __init__.py
│   ├── main_window.py       # MainWindow
│   ├── live_view.py         # LiveViewWidget
│   ├── controls.py          # ControlsPanel
│   └── recording_panel.py   # RecordingPanel
├── main.py                  # Entry point
├── requirements.txt
└── tests/
    ├── __init__.py
    ├── test_camera.py        # Unit tests (mocked cv2)
    ├── test_recorder.py      # Recorder tests
    ├── test_utils.py         # Sidecar save tests
    └── test_integration.py   # Real camera tests (skipped without hardware)
```

## Dependencies

- `opencv-python>=4.8.0`
- `PyQt6>=6.5.0`
- `numpy>=1.24.0`
