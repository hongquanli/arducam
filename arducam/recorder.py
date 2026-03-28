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
        self._skip_interval: float = 1.0
        self._frame_index: int = 0

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

    def start(
        self,
        filepath: str,
        width: int,
        height: int,
        source_fps: int,
        target_fps: int,
        fmt: RecordingFormat,
    ) -> None:
        self._source_fps = source_fps
        self._target_fps = target_fps
        self._skip_interval = source_fps / target_fps if target_fps > 0 else 1.0
        self._frame_count = 0
        self._frame_index = 0
        self._fmt = fmt
        self._start_time = time.monotonic()

        if fmt == RecordingFormat.IMAGE_SEQUENCE:
            self._seq_dir = filepath
            os.makedirs(self._seq_dir, exist_ok=True)
            self._writer = None
        else:
            if fmt == RecordingFormat.MJPEG_AVI:
                fourcc = cv2.VideoWriter_fourcc(*"MJPG")
            else:
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

        if self._source_fps > self._target_fps:
            self._frame_index += 1
            expected_count = int(self._frame_index / self._skip_interval)
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
