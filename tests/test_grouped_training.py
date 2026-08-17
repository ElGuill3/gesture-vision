import builtins
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from gesture_vision.features import FEATURE_DIMENSION, FEATURE_SCHEMA
from gesture_vision.sessions import partition_sessions


def session_payload(session_id, **overrides):
    payload = {
        "format_version": 1,
        "session_id": session_id,
        "schema": FEATURE_SCHEMA,
        "started_at": "2026-08-16T12:00:00+00:00",
        "ended_at": "2026-08-16T12:01:00+00:00",
        "status": "complete",
        "samples": [
            {"frame_id": 1, "hand": "left", "label": "up", "features": [0.0] * FEATURE_DIMENSION},
            {"frame_id": 1, "hand": "right", "label": "up", "features": [1.0] * FEATURE_DIMENSION},
        ],
    }
    payload.update(overrides)
    return payload


def write_session(directory, file_id, **overrides):
    path = Path(directory) / f"{file_id}.json"
    session_id = overrides.pop("session_id", file_id)
    path.write_text(json.dumps(session_payload(session_id, **overrides)), encoding="utf-8")
    return path


class GroupedTrainingTests(unittest.TestCase):
    def test_fixed_seed_keeps_complete_sessions_disjoint_and_repeatable(self):
        with tempfile.TemporaryDirectory() as directory:
            paths = [
                write_session(directory, f"00000000-0000-4000-8000-{index:012d}")
                for index in range(1, 7)
            ]
            first = partition_sessions(reversed(paths), seed=17)
            second = partition_sessions(paths, seed=17)

            membership = {name: [session["session_id"] for session in group] for name, group in first.items()}
            self.assertEqual(membership, {name: [session["session_id"] for session in group] for name, group in second.items()})
            self.assertTrue(all(first[name] for name in ("train", "validation", "test")))
            assigned = [session_id for group in membership.values() for session_id in group]
            self.assertEqual(len(assigned), len(paths))
            self.assertEqual(set(assigned), {path.stem for path in paths})
            self.assertTrue(all(len(session["samples"]) == 2 for group in first.values() for session in group))

    def test_invalid_sessions_fail_before_any_fitter_or_ml_import(self):
        """U3 is the pure pre-fitter validation boundary for U4."""
        with tempfile.TemporaryDirectory() as directory:
            path = write_session(directory, "00000000-0000-4000-8000-000000000001", status="capturing")
            original_import = builtins.__import__

            def block_ml_imports(name, *args, **kwargs):
                if name.partition(".")[0] in {"tensorflow", "sklearn", "pandas"}:
                    self.fail(f"Validation imported ML dependency: {name}")
                return original_import(name, *args, **kwargs)

            with patch("builtins.__import__", side_effect=block_ml_imports):
                with self.assertRaisesRegex(ValueError, "status must be 'complete'"):
                    partition_sessions([path], seed=17)

    def test_rejects_malformed_duplicate_empty_schema_mismatch_and_insufficient_sessions(self):
        with tempfile.TemporaryDirectory() as directory:
            malformed = Path(directory) / "malformed.json"
            malformed.write_text("{not-json", encoding="utf-8")
            empty = write_session(directory, "00000000-0000-4000-8000-000000000002", samples=[])
            mismatched = write_session(directory, "00000000-0000-4000-8000-000000000003", schema="legacy-42")
            first = write_session(directory, "00000000-0000-4000-8000-000000000004")
            duplicate = write_session(directory, "00000000-0000-4000-8000-000000000005", session_id="00000000-0000-4000-8000-000000000004")
            second = write_session(directory, "00000000-0000-4000-8000-000000000006")

            for paths, message in (
                ([malformed], "valid JSON"),
                ([empty], "at least one sample"),
                ([mismatched], "schema"),
                ([first, duplicate], "Duplicate session_id"),
                ([first, second], "At least three complete session files"),
            ):
                with self.subTest(paths=paths):
                    with self.assertRaisesRegex(ValueError, message):
                        partition_sessions(paths, seed=17)


if __name__ == "__main__":
    unittest.main()
