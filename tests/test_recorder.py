import os
import tempfile
import time

import cv2
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
        rec.write_frame(frame)

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
            loaded = cv2.imread(os.path.join(seq_dir, "frame_000001.png"))
            assert loaded is not None
            assert loaded.shape == (100, 100, 3)
