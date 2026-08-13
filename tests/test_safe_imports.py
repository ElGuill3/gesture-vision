from pathlib import Path
import subprocess
import sys
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = (
    "preprocessing/0_create_dataset.py",
    "training/1_train_model.py",
    "inference/2_real_time_inference.py",
    "integrations/gamepad/gamepad_simulation.py",
    "hand_detection.py",
    "utils/list_cameras.py",
)
TIMEOUT_SECONDS = 2

PROBE = r'''
import builtins
import contextlib
import importlib.abc
import io
import os
import sys

BLOCKED_DEPENDENCIES = {
    "cv2", "mediapipe", "numpy", "pandas", "yaml", "tensorflow",
    "sklearn", "joblib", "matplotlib", "vgamepad",
}


class SafetyBarrier(RuntimeError):
    pass


class DependencyBarrier(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.partition(".")[0] in BLOCKED_DEPENDENCIES:
            raise SafetyBarrier(f"module-level dependency import reached: {fullname}")
        return None


def block_open(file, mode="r", *args, **kwargs):
    raise SafetyBarrier(f"module-level filesystem open reached: {file!r} ({mode})")


def block_operation(name):
    def blocked(*args, **kwargs):
        target = args[0] if args else "<unknown>"
        raise SafetyBarrier(f"module-level filesystem operation reached: {name}({target!r})")
    return blocked


source = sys.stdin.read()
script_path = sys.argv[1]

# Safety barriers are installed only after the probe has loaded its own source.
sys.meta_path.insert(0, DependencyBarrier())
builtins.open = block_open
io.open = block_open
os.open = block_open
for operation in ("mkdir", "makedirs", "remove", "rename", "replace", "unlink"):
    if hasattr(os, operation):
        setattr(os, operation, block_operation(operation))

stdout = io.StringIO()
stderr = io.StringIO()
namespace = {
    "__name__": "safe_import_probe",
    "__file__": script_path,
    "__package__": None,
    "__cached__": None,
    "__builtins__": builtins,
}

try:
    with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
        exec(compile(source, script_path, "exec"), namespace)
except SafetyBarrier as error:
    sys.__stderr__.write(f"{error}\n")
    status = 86
except BaseException as error:
    sys.__stderr__.write(
        f"module-level exception reached: {type(error).__name__}: {error}\n"
    )
    status = 87
else:
    status = 0

if stdout.getvalue():
    sys.__stderr__.write(f"module-level stdout reached: {stdout.getvalue()!r}\n")
    status = status or 88
if stderr.getvalue():
    sys.__stderr__.write(f"module-level stderr reached: {stderr.getvalue()!r}\n")
    status = status or 89

raise SystemExit(status)
'''


class SafeImportTests(unittest.TestCase):
    def test_scripts_import_without_side_effects(self):
        for relative_path in SCRIPTS:
            with self.subTest(script=relative_path):
                script = PROJECT_ROOT / relative_path
                try:
                    result = subprocess.run(
                        [sys.executable, "-I", "-S", "-c", PROBE, str(script)],
                        input=script.read_text(encoding="utf-8"),
                        text=True,
                        capture_output=True,
                        timeout=TIMEOUT_SECONDS,
                        check=False,
                    )
                except subprocess.TimeoutExpired:
                    self.fail(
                        f"{relative_path}: timed out after {TIMEOUT_SECONDS}s; "
                        "module-level work may have blocked"
                    )

                details = result.stderr.strip() or "no diagnostic was produced"
                self.assertEqual(
                    (result.returncode, result.stdout, result.stderr),
                    (0, "", ""),
                    f"{relative_path}: import was not clean (exit {result.returncode}): "
                    f"{details}",
                )


if __name__ == "__main__":
    unittest.main()
