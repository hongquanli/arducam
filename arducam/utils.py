import json
import os

import cv2
import numpy as np


def save_capture(filepath: str, frame: np.ndarray, settings: dict) -> None:
    """Save a frame as PNG and write a JSON sidecar with camera settings."""
    base, ext = os.path.splitext(filepath)

    # If no extension, use cv2.imencode to write PNG format directly
    if not ext:
        success, buffer = cv2.imencode(".png", frame)
        if success:
            with open(filepath, "wb") as f:
                f.write(buffer)
    else:
        cv2.imwrite(filepath, frame)

    json_path = base + ".json"
    with open(json_path, "w") as f:
        json.dump(settings, f, indent=2)
