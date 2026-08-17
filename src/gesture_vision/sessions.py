"""Immutable, schema-versioned capture sessions."""

import json
import os
from datetime import datetime, timezone
from math import isfinite
from pathlib import Path
from random import Random
from uuid import UUID, uuid4

from .features import FEATURE_DIMENSION, FEATURE_SCHEMA, extract_landmark_features


def _utc_now():
    return datetime.now(timezone.utc).isoformat()


def _load_complete_session(path):
    path = Path(path)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError(f"Invalid session file {path}: expected valid JSON") from error
    if not isinstance(payload, dict):
        raise ValueError(f"Invalid session file {path}: expected a JSON object")
    required = {"format_version", "session_id", "schema", "started_at", "ended_at", "status", "samples"}
    missing = sorted(required - payload.keys())
    if missing:
        raise ValueError(f"Invalid session file {path}: missing {', '.join(missing)}")
    if payload["format_version"] != 1 or isinstance(payload["format_version"], bool):
        raise ValueError(f"Invalid session file {path}: unsupported format_version")
    try:
        session_id = UUID(payload["session_id"])
    except (AttributeError, TypeError, ValueError) as error:
        raise ValueError(f"Invalid session file {path}: session_id must be a UUID4") from error
    if session_id.version != 4:
        raise ValueError(f"Invalid session file {path}: session_id must be a UUID4")
    if payload["schema"] != FEATURE_SCHEMA:
        raise ValueError(f"Invalid session file {path}: schema must be {FEATURE_SCHEMA!r}")
    if payload["status"] != "complete":
        raise ValueError(f"Invalid session file {path}: status must be 'complete'")
    for field in ("started_at", "ended_at"):
        try:
            timestamp = datetime.fromisoformat(payload[field])
        except (TypeError, ValueError) as error:
            raise ValueError(f"Invalid session file {path}: {field} must be an ISO-8601 timestamp") from error
        if timestamp.tzinfo is None:
            raise ValueError(f"Invalid session file {path}: {field} must include a timezone")
    if not isinstance(payload["samples"], list) or not payload["samples"]:
        raise ValueError(f"Invalid session file {path}: complete sessions need at least one sample")
    for index, sample in enumerate(payload["samples"]):
        if not isinstance(sample, dict) or {"frame_id", "hand", "label", "features"} - sample.keys():
            raise ValueError(f"Invalid session file {path}: sample {index} is malformed")
        if not isinstance(sample["frame_id"], int) or isinstance(sample["frame_id"], bool):
            raise ValueError(f"Invalid session file {path}: sample {index} frame_id must be an integer")
        if sample["hand"] not in {"left", "right"}:
            raise ValueError(f"Invalid session file {path}: sample {index} hand must be left or right")
        if not isinstance(sample["label"], str) or not sample["label"]:
            raise ValueError(f"Invalid session file {path}: sample {index} label must be non-empty")
        features = sample["features"]
        if not isinstance(features, list) or len(features) != FEATURE_DIMENSION or not all(
            isinstance(value, (int, float)) and not isinstance(value, bool) and isfinite(value) for value in features
        ):
            raise ValueError(f"Invalid session file {path}: sample {index} needs {FEATURE_DIMENSION} finite features")
    return payload


def partition_sessions(session_paths, *, seed):
    """Return deterministic train, validation, and test groups of whole sessions."""
    if isinstance(session_paths, (str, Path)):
        session_paths = (session_paths,)
    try:
        session_paths = tuple(session_paths)
    except TypeError as error:
        raise ValueError("Session inputs must be an iterable of session files") from error
    sessions = []
    source_by_id = {}
    for path in session_paths:
        session = _load_complete_session(path)
        session_id = session["session_id"]
        if session_id in source_by_id:
            raise ValueError(f"Duplicate session_id {session_id} in {path} and {source_by_id[session_id]}")
        source_by_id[session_id] = path
        sessions.append(session)
    if len(sessions) < 3:
        raise ValueError("At least three complete session files are required for train, validation, and test groups")
    sessions.sort(key=lambda session: session["session_id"])
    Random(seed).shuffle(sessions)
    groups = {"train": [], "validation": [], "test": []}
    for index, session in enumerate(sessions):
        groups[("train", "validation", "test")[index % 3]].append(session)
    return groups


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
