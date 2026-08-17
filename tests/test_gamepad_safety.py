import builtins
from pathlib import Path
import runpy
import sys
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from gesture_vision.adapters.gamepad import GamepadAdapter, open_gamepad
from gesture_vision.bundles import promote_bundle
from gesture_vision.features import FEATURE_DIMENSION
from gesture_vision.workflows.gamepad import run


BUTTONS = ("XUSB_GAMEPAD_DPAD_UP", "XUSB_GAMEPAD_DPAD_DOWN", "XUSB_GAMEPAD_DPAD_LEFT", "XUSB_GAMEPAD_DPAD_RIGHT", "XUSB_GAMEPAD_A", "XUSB_GAMEPAD_B", "XUSB_GAMEPAD_X", "XUSB_GAMEPAD_Y", "XUSB_GAMEPAD_LEFT_SHOULDER", "XUSB_GAMEPAD_RIGHT_SHOULDER")
VG = SimpleNamespace(XUSB_BUTTON=SimpleNamespace(**{name: name for name in BUTTONS}))


def landmarks():
    return [SimpleNamespace(x=index, y=index + 0.5, z=index + 1.0) for index in range(21)]


class Pad:
    def __init__(self, fail=False):
        self.active, self.released, self.released_active, self.snapshots, self.fail = set(), set(), set(), [], fail
        self.left = self.right = 0

    def press_button(self, button):
        self.active.add(button)
        if self.fail:
            raise RuntimeError("fake gamepad failure")

    def release_button(self, button):
        if button in self.active:
            self.released_active.add(button)
        self.active.discard(button)
        self.released.add(button)

    def left_trigger(self, *, value):
        self.left = value

    def right_trigger(self, *, value):
        self.right = value

    def update(self):
        self.snapshots.append((set(self.active), self.left, self.right))


class Scaler:
    n_features_in_ = FEATURE_DIMENSION

    def transform(self, values):
        return values


class Model:
    input_shape, output_shape = (None, FEATURE_DIMENSION), (None, 2)

    def __init__(self, predictions):
        self.predictions = iter(predictions)

    def predict(self, values, verbose=0):
        return [next(self.predictions)]


def config(root):
    return {
        "PATHS": {"bundles": root}, "INFERENCE": {"prediction_threshold": 0.7, "smoothing_window": 2},
        "GAMEPAD": {"trigger_value": 123, "hand_mapping": {"left_hand": {"controls": ["dpad", "LB", "LT"]}, "right_hand": {"controls": ["A", "B", "X", "Y", "RB", "RT"]}}, "gesture_to_dpad": {"up": "XUSB_GAMEPAD_DPAD_UP"}, "gesture_to_action_buttons": {"A": "XUSB_GAMEPAD_A"}, "gesture_to_shoulder_buttons": {"LB": "XUSB_GAMEPAD_LEFT_SHOULDER"}, "gesture_to_triggers": {"LT": "left_trigger"}},
    }


class GamepadSafetyTests(unittest.TestCase):
    def test_adapter_honors_hand_mapping_and_neutralizes_idempotently(self):
        pad, settings = Pad(), config(Path("."))["GAMEPAD"]
        adapter = GamepadAdapter(pad, VG, settings)
        adapter.apply({"left": ("up", 0.9), "right": ("A", 0.9)})
        self.assertEqual(pad.snapshots[-1][0], {"XUSB_GAMEPAD_DPAD_UP", "XUSB_GAMEPAD_A"})
        adapter.apply({"left": ("LT", 0.9), "right": (None, 0.0)})
        self.assertEqual(pad.snapshots[-1], (set(), 123, 0))
        adapter.neutralize()
        adapter.neutralize()
        self.assertEqual((pad.active, pad.left, pad.right, pad.released), (set(), 0, 0, set(BUTTONS)))

    def test_workflow_releases_on_loss_low_confidence_error_and_shutdown(self):
        cases = (("loss", ((0.9, 0.1),), ((("left", landmarks()),), ())), ("low", ((0.9, 0.1), (0.6, 0.4)), ((("left", landmarks()),), (("left", landmarks()),))), ("shutdown", ((0.9, 0.1),), ((("left", landmarks()),),)), ("error", ((0.9, 0.1),), ((("left", landmarks()),),)))
        for name, predictions, inputs in cases:
            with self.subTest(name=name), tempfile.TemporaryDirectory() as directory:
                root, pad = Path(directory), Pad(fail=name == "error")
                writer = lambda path: ((path / "model.keras").write_bytes(b"m"), (path / "scaler.joblib").write_bytes(b"s"))
                loader = lambda *_: (Model(predictions), Scaler())
                promote_bundle(root, "active", ("up", "A"), 1, {"train": ["a"], "validation": ["b"], "test": ["c"]}, writer, loader, {"python": "x", "tensorflow": "x", "scikit_learn": "x", "joblib": "x"})
                adapter = GamepadAdapter(pad, VG, config(root)["GAMEPAD"])
                if name == "error":
                    with self.assertRaisesRegex(RuntimeError, "fake gamepad failure"):
                        run(config(root), inputs, loader, lambda _: adapter)
                else:
                    results = run(config(root), inputs, loader, lambda _: adapter)
                    if name == "low":
                        self.assertEqual(results[-1]["left"], (None, 0.6))
                if name != "error":
                    self.assertIn(({"XUSB_GAMEPAD_DPAD_UP"}, 0, 0), pad.snapshots)
                else:
                    self.assertEqual(pad.released_active, {"XUSB_GAMEPAD_DPAD_UP"})
                self.assertEqual((pad.active, pad.left, pad.right), (set(), 0, 0))

    def test_unavailable_support_and_legacy_wrapper_are_safe(self):
        original_import = builtins.__import__
        with patch("gesture_vision.adapters.gamepad.sys.platform", "linux"), patch("builtins.__import__", side_effect=lambda name, *args, **kwargs: self.fail("vgamepad imported") if name == "vgamepad" else original_import(name, *args, **kwargs)):
            with self.assertRaisesRegex(RuntimeError, "Windows"):
                open_gamepad(config(Path(".")))
        with patch("gesture_vision.adapters.gamepad.sys.platform", "win32"), patch("builtins.__import__", side_effect=lambda name, *args, **kwargs: (_ for _ in ()).throw(ImportError("missing")) if name == "vgamepad" else original_import(name, *args, **kwargs)):
            with self.assertRaisesRegex(RuntimeError, r"gesture-vision\[gamepad\]"):
                open_gamepad(config(Path(".")))
        namespace = runpy.run_path(Path(__file__).resolve().parents[1] / "integrations/gamepad/gamepad_simulation.py", run_name="legacy_gamepad")
        with patch("gesture_vision.workflows.gamepad.run", return_value="controlled") as workflow:
            self.assertEqual(namespace["main"](), "controlled")
        self.assertTrue(workflow.called)


if __name__ == "__main__":
    unittest.main()
