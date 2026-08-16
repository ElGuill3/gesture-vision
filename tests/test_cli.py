import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = PROJECT_ROOT / "src"
sys.path.insert(0, str(SOURCE_ROOT))

from gesture_vision.cli import build_parser, load_command_config


class CliTests(unittest.TestCase):
    def test_yaml_values_yield_to_cli_and_paths_are_rooted(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            config_path = root / "config" / "config.yaml"
            config_path.parent.mkdir()
            config_path.write_text("PATHS:\n  root: .\n  sessions: captures\nCAMERA:\n  camera_index: 2\n", encoding="utf-8")
            parser = build_parser()
            default_config = load_command_config(parser.parse_args(["capture", "--config", str(config_path)]))
            override_config = load_command_config(parser.parse_args(["capture", "--config", str(config_path), "--camera-index", "7"]))
            self.assertEqual(default_config["CAMERA"]["camera_index"], 2)
            self.assertEqual(override_config["CAMERA"]["camera_index"], 7)
            self.assertEqual(override_config["PATHS"]["sessions"], root / "captures")

    def test_help_is_safe_from_another_working_directory(self):
        environment = {**os.environ, "PYTHONPATH": str(SOURCE_ROOT)}
        with tempfile.TemporaryDirectory() as directory:
            for command in ("capture", "train", "infer", "gamepad"):
                result = subprocess.run([sys.executable, "-m", "gesture_vision.cli", command, "--help"], cwd=directory, env=environment, text=True, capture_output=True, check=False)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn("usage: gesture-vision", result.stdout)

    def test_package_import_needs_no_optional_dependencies(self):
        probe = "import sys; sys.path.insert(0, sys.argv[1]); import gesture_vision.cli; assert not {'cv2', 'mediapipe', 'tensorflow', 'vgamepad', 'yaml'} & set(sys.modules)"
        result = subprocess.run([sys.executable, "-I", "-S", "-c", probe, str(SOURCE_ROOT)], text=True, capture_output=True, check=False)
        self.assertEqual(result.returncode, 0, result.stderr)
