import json
from pathlib import Path
import runpy
import sys
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from gesture_vision.sessions import CaptureSession
from gesture_vision.workflows.capture import run


def landmarks(offset=0):
    return [SimpleNamespace(x=offset + index, y=index + 0.5, z=index + 1.0) for index in range(21)]


class CaptureSessionTests(unittest.TestCase):
    def test_finalizes_two_hands_with_schema_and_attribution(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            session = CaptureSession(temporary_directory)
            self.assertEqual(session.record_frame(7, "up", (("left", landmarks()), ("right", landmarks(10)))), 2)
            result = session.finalize()
            payload = json.loads(result.read_text(encoding="utf-8"))
            self.assertEqual(payload["schema"], "mediapipe-xyz-wrist-v1")
            self.assertEqual(payload["status"], "complete")
            self.assertEqual([(sample["frame_id"], sample["hand"], sample["label"]) for sample in payload["samples"]], [(7, "left", "up"), (7, "right", "up")])
            self.assertTrue(all(len(sample["features"]) == 63 for sample in payload["samples"]))
            with self.assertRaises(RuntimeError):
                session.finalize()
            with self.assertRaises(RuntimeError):
                session.add_sample(8, "left", "up", landmarks())

    def test_invalid_or_failed_capture_publishes_no_session(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            config = {"PATHS": {"sessions": Path(temporary_directory)}}
            self.assertIsNone(run(config, [(1, "up", (("left", landmarks()[:-1]),))]))
            self.assertEqual(list(Path(temporary_directory).iterdir()), [])

            def failed_frames():
                yield 2, "up", (("left", landmarks()),)
                raise RuntimeError("simulated capture failure")

            with self.assertRaises(RuntimeError):
                run(config, failed_frames())
            self.assertEqual(list(Path(temporary_directory).iterdir()), [])

            def cancelled_frames():
                yield 3, "up", (("left", landmarks()),)
                raise KeyboardInterrupt

            self.assertIsNone(run(config, cancelled_frames()))
            self.assertEqual(list(Path(temporary_directory).iterdir()), [])

            session = CaptureSession(temporary_directory)
            session.add_sample(4, "left", "up", landmarks())
            with patch("gesture_vision.sessions.os.replace", side_effect=OSError("simulated finalization failure")):
                with self.assertRaises(OSError):
                    session.finalize()
            self.assertEqual(list(Path(temporary_directory).iterdir()), [])

    def test_runs_are_isolated_and_need_no_hardware_imports(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            config = {"PATHS": {"sessions": Path(temporary_directory)}}
            first = run(config, [(1, "left", (("left", landmarks()), ("right", landmarks(10))))])
            second = run(config, [(2, "right", (("right", landmarks(20)),))])
            self.assertNotEqual(first, second)
            self.assertEqual(len(list(Path(temporary_directory).glob("*.json"))), 2)
            self.assertEqual([sample["hand"] for sample in json.loads(first.read_text())["samples"]], ["left", "right"])
            self.assertFalse({"cv2", "mediapipe"} & set(sys.modules))

    def test_legacy_wrapper_delegates_to_capture_workflow(self):
        wrapper = Path(__file__).resolve().parents[1] / "preprocessing" / "0_create_dataset.py"
        namespace = runpy.run_path(wrapper, run_name="legacy_capture")
        with patch("gesture_vision.workflows.capture.run", return_value="captured") as capture:
            self.assertEqual(namespace["main"](), "captured")
        self.assertTrue(capture.called)


if __name__ == "__main__":
    unittest.main()
