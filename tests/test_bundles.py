import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from gesture_vision.bundles import promote_bundle, rollback_bundle, validate_bundle
from gesture_vision.features import FEATURE_DIMENSION, FEATURE_SCHEMA


class Model:
    input_shape = (None, FEATURE_DIMENSION)
    output_shape = (None, 2)


class Scaler:
    n_features_in_ = FEATURE_DIMENSION


def loader(model_path, scaler_path):
    if model_path.read_bytes() != b"model" or scaler_path.read_bytes() != b"scaler":
        raise ValueError("fake artifacts are invalid")
    return Model(), Scaler()


def writer(directory):
    (Path(directory) / "model.keras").write_bytes(b"model")
    (Path(directory) / "scaler.joblib").write_bytes(b"scaler")


GROUPS = {"train": ["a"], "validation": ["b"], "test": ["c"]}
VERSIONS = {"python": "3.11", "tensorflow": "fake", "scikit_learn": "fake", "joblib": "fake"}


class BundleTests(unittest.TestCase):
    def test_manifest_promotion_failure_and_rollback_keep_selector_safe(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            first = promote_bundle(root, "first", ("left", "right"), 17, GROUPS, writer, loader, VERSIONS)
            model, scaler, manifest = validate_bundle(first, loader, "first")
            self.assertEqual((manifest["feature_schema"], manifest["input_dimension"], manifest["output_dimension"]), (FEATURE_SCHEMA, FEATURE_DIMENSION, 2))
            self.assertEqual((model.input_shape[-1], scaler.n_features_in_), (FEATURE_DIMENSION, FEATURE_DIMENSION))
            second = promote_bundle(root, "second", ("left", "right"), 17, GROUPS, writer, loader, VERSIONS)
            self.assertEqual(json.loads((root / "selection.json").read_text())["active"], second.name)
            self.assertEqual(rollback_bundle(root, loader), first)
            before = (root / "selection.json").read_bytes()

            def incomplete(directory):
                (Path(directory) / "model.keras").write_bytes(b"model")

            with self.assertRaisesRegex(ValueError, "incomplete"):
                promote_bundle(root, "broken", ("left", "right"), 17, GROUPS, incomplete, loader, VERSIONS)
            self.assertEqual((root / "selection.json").read_bytes(), before)
            self.assertFalse(any(path.name.startswith(".") for path in root.iterdir()))


if __name__ == "__main__":
    unittest.main()
