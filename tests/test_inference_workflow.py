import builtins
from pathlib import Path
import runpy
import sys
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from gesture_vision.bundles import promote_bundle
from gesture_vision.features import FEATURE_DIMENSION
from gesture_vision.workflows.inference import run


def landmarks(offset=0):
    return [SimpleNamespace(x=offset + index, y=index + 0.5, z=index + 1.0) for index in range(21)]


class Scaler:
    n_features_in_ = FEATURE_DIMENSION

    def transform(self, values):
        return values


class Model:
    input_shape = (None, FEATURE_DIMENSION)
    output_shape = (None, 2)

    def __init__(self, predictions=((0.9, 0.1), (0.1, 0.9))):
        self.predictions = iter(predictions)

    def predict(self, values, verbose=0):
        return [next(self.predictions)]


def writer(directory):
    (Path(directory) / "model.keras").write_bytes(b"model")
    (Path(directory) / "scaler.joblib").write_bytes(b"scaler")


def loader(model_path, scaler_path):
    if model_path.read_bytes() != b"model" or scaler_path.read_bytes() != b"scaler":
        raise ValueError("fake artifacts are invalid")
    return Model(), Scaler()


class InferenceWorkflowTests(unittest.TestCase):
    def config(self, root):
        return {"PATHS": {"bundles": root}, "INFERENCE": {"prediction_threshold": 0.7, "smoothing_window": 2}}

    def bundle(self, root):
        return promote_bundle(root, "active", ("left", "right"), 17, {"train": ["a"], "validation": ["b"], "test": ["c"]}, writer, loader, {"python": "3.11", "tensorflow": "fake", "scikit_learn": "fake", "joblib": "fake"})

    def test_validated_bundle_recognizes_fake_hands_without_heavy_imports(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.bundle(root)
            original_import = builtins.__import__

            def no_heavy(name, *args, **kwargs):
                if name.partition(".")[0] in {"cv2", "mediapipe", "tensorflow", "joblib"}:
                    self.fail(f"fake inference imported {name}")
                return original_import(name, *args, **kwargs)

            with patch("builtins.__import__", side_effect=no_heavy):
                results = run(self.config(root), [(("left", landmarks()), ("right", landmarks(10)))], loader)
            self.assertEqual(results[0], {"left": ("left", 0.9), "right": ("right", 0.9)})

    def test_invalid_bundle_fails_before_fake_camera_opens(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.bundle(root)
            opened = []

            def camera(index):
                opened.append(index)
                self.fail("camera opened before bundle validation")

            with self.assertRaisesRegex(ValueError, "dimension-incompatible"):
                run(self.config(root), artifact_loader=lambda *_: (type("BrokenModel", (), {"input_shape": (None, 42), "output_shape": (None, 2)})(), Scaler()), camera_factory=camera)
            self.assertEqual(opened, [])

    def test_legacy_inference_wrapper_delegates(self):
        wrapper = Path(__file__).resolve().parents[1] / "inference" / "2_real_time_inference.py"
        namespace = runpy.run_path(wrapper, run_name="legacy_inference")
        with patch("gesture_vision.config.load_config", return_value={}), patch("gesture_vision.workflows.inference.run", return_value="inferred") as inference:
            self.assertEqual(namespace["main"](), "inferred")
        self.assertTrue(inference.called)


if __name__ == "__main__":
    unittest.main()
