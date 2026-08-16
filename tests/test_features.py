import math
from pathlib import Path
import sys
import unittest
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from gesture_vision.features import FEATURE_DIMENSION, FEATURE_SCHEMA, extract_landmark_features


def landmarks(count=21):
    return [SimpleNamespace(x=index, y=index + 0.5, z=index + 1.0) for index in range(count)]


class FeatureContractTests(unittest.TestCase):
    def test_wrist_normalized_xyz_order_and_dimension(self):
        features = extract_landmark_features(landmarks())
        self.assertEqual(FEATURE_SCHEMA, "mediapipe-xyz-wrist-v1")
        self.assertEqual(len(features), FEATURE_DIMENSION)
        self.assertEqual(features[:6], (0.0, 0.0, 0.0, 1.0, 1.0, 1.0))
        self.assertTrue(all(math.isfinite(value) for value in features))

    def test_invalid_and_legacy_inputs_are_rejected(self):
        invalid = (landmarks(20), landmarks(22), [0.0] * 42, [SimpleNamespace(x=0, y=0, z=float("nan"))] * 21)
        for value in invalid:
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    extract_landmark_features(value)
