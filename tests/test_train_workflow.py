import builtins
import json
from pathlib import Path
import runpy
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from gesture_vision.bundles import promote_bundle
from gesture_vision.features import FEATURE_DIMENSION, FEATURE_SCHEMA
from gesture_vision.workflows.train import run
from tests.test_bundles import GROUPS, VERSIONS, loader, writer


def session(directory, index, status="complete"):
    path = Path(directory) / f"00000000-0000-4000-8000-{index:012d}.json"
    path.write_text(json.dumps({"format_version": 1, "session_id": path.stem, "schema": FEATURE_SCHEMA, "started_at": "2026-08-16T12:00:00+00:00", "ended_at": "2026-08-16T12:01:00+00:00", "status": status, "samples": [{"frame_id": 1, "hand": "left", "label": "left", "features": [0.0] * FEATURE_DIMENSION}]}), encoding="utf-8")
    return path


class TrainWorkflowTests(unittest.TestCase):
    def test_fake_fit_promotes_only_after_complete_sessions_without_ml_imports(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config = {"PATHS": {"sessions": root, "bundles": root / "bundles"}, "TRAINING": {"split_seed": 17}}
            paths = [session(root, index) for index in range(1, 4)]
            calls = []

            def fitter(groups, unused_config):
                calls.append(groups)
                return ("left", "right"), writer, VERSIONS

            original_import = builtins.__import__

            def no_ml(name, *args, **kwargs):
                if name.partition(".")[0] in {"tensorflow", "sklearn", "joblib", "pandas"}:
                    self.fail(f"fake workflow imported {name}")
                return original_import(name, *args, **kwargs)

            with patch("builtins.__import__", side_effect=no_ml):
                result = run(config, paths, fitter, loader)
            self.assertTrue(calls)
            self.assertEqual(json.loads((config["PATHS"]["bundles"] / "selection.json").read_text())["active"], result.name)

    def test_invalid_sessions_fail_before_fitter_and_keep_selection(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            bundles = root / "bundles"
            promote_bundle(bundles, "active", ("left", "right"), 17, GROUPS, writer, loader, VERSIONS)
            before = (bundles / "selection.json").read_bytes()
            config = {"PATHS": {"sessions": root, "bundles": bundles}, "TRAINING": {"split_seed": 17}}
            with self.assertRaisesRegex(ValueError, "status must be 'complete'"):
                run(config, [session(root, 1, "capturing")], lambda *_: self.fail("fitter ran"), loader)
            self.assertEqual((bundles / "selection.json").read_bytes(), before)

    def test_legacy_training_wrapper_delegates(self):
        wrapper = Path(__file__).resolve().parents[1] / "training" / "1_train_model.py"
        namespace = runpy.run_path(wrapper, run_name="legacy_train")
        with patch("gesture_vision.config.load_config", return_value={}), patch("gesture_vision.workflows.train.run", return_value="trained") as train:
            self.assertEqual(namespace["main"](), "trained")
        self.assertTrue(train.called)


if __name__ == "__main__":
    unittest.main()
