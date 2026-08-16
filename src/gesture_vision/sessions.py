"""Immutable, schema-versioned capture sessions."""

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from .features import FEATURE_SCHEMA, extract_landmark_features


def _utc_now():
    return datetime.now(timezone.utc).isoformat()


class CaptureSession:
    """Collect samples in memory and publish one JSON file exactly once."""

    def __init__(self, directory):
        self.directory = Path(directory)
        self.session_id = str(uuid4())
        self.started_at = _utc_now()
        self.samples = []
        self._final_path = None

    @property
    def sample_count(self):
        return len(self.samples)

    def add_sample(self, frame_id, hand, label, landmarks):
        if self._final_path is not None:
            raise RuntimeError("A finalized capture session is immutable")
        hand = str(hand).lower()
        if hand not in {"left", "right"}:
            raise ValueError("Hand attribution must be left or right")
        self.samples.append(
            {
                "frame_id": frame_id,
                "hand": hand,
                "label": label,
                "features": list(extract_landmark_features(landmarks)),
            }
        )

    def record_frame(self, frame_id, label, detections):
        accepted = 0
        for hand, landmarks in detections:
            try:
                self.add_sample(frame_id, hand, label, landmarks)
            except ValueError:
                continue
            accepted += 1
        return accepted

    def finalize(self):
        if self._final_path is not None:
            raise RuntimeError("A capture session can only be finalized once")
        if not self.samples:
            return None
        final_path = self.directory / f"{self.session_id}.json"
        if final_path.exists():
            raise FileExistsError(f"Capture session already exists: {final_path}")
        self.directory.mkdir(parents=True, exist_ok=True)
        temporary_path = final_path.with_name(f".{final_path.name}.{uuid4().hex}.tmp")
        payload = {
            "format_version": 1,
            "session_id": self.session_id,
            "schema": FEATURE_SCHEMA,
            "started_at": self.started_at,
            "ended_at": _utc_now(),
            "status": "complete",
            "samples": self.samples,
        }
        try:
            with temporary_path.open("x", encoding="utf-8") as file:
                json.dump(payload, file, ensure_ascii=False)
                file.flush()
                os.fsync(file.fileno())
            os.replace(temporary_path, final_path)
        except BaseException:
            temporary_path.unlink(missing_ok=True)
            raise
        self._final_path = final_path
        return final_path
