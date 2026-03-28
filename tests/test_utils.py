import json
import os
import tempfile

import cv2
import numpy as np

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

            assert os.path.exists(filepath)
            loaded = cv2.imread(filepath)
            assert loaded is not None
            assert loaded.shape == (100, 200, 3)

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
            assert os.path.exists(filepath)
            json_path = os.path.join(tmpdir, "image.json")
            assert os.path.exists(json_path)
