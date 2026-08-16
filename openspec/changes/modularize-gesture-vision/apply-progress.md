# Apply Progress: Modularize GestureVision

## Status

- Mode: Standard (strict TDD disabled in `openspec/config.yaml`)
- Delivery: `auto-chain`, `stacked-to-main`
- Work units: U1-package-feature-contract, U2-capture-sessions
- Completed: 1.1, 1.2, 2.1, 2.2
- U2 boundary: immutable JSON capture sessions and the preprocessing migration wrapper only.

## Changed Paths

- `pyproject.toml`
- `src/gesture_vision/__init__.py`
- `src/gesture_vision/{cli,config,features}.py`
- `src/gesture_vision/defaults.yaml`
- `tests/{__init__,test_cli,test_features}.py`
- `openspec/changes/modularize-gesture-vision/tasks.md`
- `src/gesture_vision/sessions.py`
- `src/gesture_vision/workflows/{__init__,capture}.py`
- `preprocessing/0_create_dataset.py`
- `tests/test_capture_sessions.py`
- `openspec/changes/modularize-gesture-vision/apply-progress.md`

## Work Unit Evidence

| Work unit | Focused test command and exact result | Runtime harness command/scenario and exact result | Rollback boundary |
|---|---|---|---|
| U1-package-feature-contract | `python -m unittest tests.test_cli tests.test_features tests.test_safe_imports -v` → exit 0, 6 tests passed | From `/tmp/opencode`, `"/home/guill3/Documents/Side Projects/Vision Computacional/gesture-vision/venv/bin/gesture-vision" {capture,train,infer,gamepad} --help` → exit 0; all four command-specific help screens rendered without hardware access | Revert U1's package, defaults, and U1 tests; legacy wrappers and data remain untouched |
| U2-capture-sessions | `python -m unittest tests.test_capture_sessions -v` → exit 0, 4 tests passed | `python -m unittest tests.test_capture_sessions.CaptureSessionTests.test_runs_are_isolated_and_need_no_hardware_imports -v` → exit 0, 1 test passed; fake workflow finalized left and right samples in one JSON session, created a distinct second session, and observed no `cv2` or `mediapipe` import | Revert `sessions.py`, `workflows/`, `test_capture_sessions.py`, and the wrapper delegation; keep U1 package/config/features intact |

## Additional Verification

- `venv/bin/python -m pip install --no-deps --no-build-isolation -e .` → exit 0 after installing build-only `setuptools>=68` into the project-local ignored venv.
- `python -m unittest discover -s tests -v` → exit 0, 6 tests passed.
- `python -m compileall -q src tests` and `git diff --check` → exit 0.
- The four legacy wrapper SHA-256 values match their pre-U1 baseline.
- `python -m unittest tests.test_safe_imports -v` → exit 0, 1 test passed; all wrappers remain import-safe.
- `python -m unittest discover -s tests -v` → exit 0, 10 tests passed, including U1 feature-contract regression tests.
- `python -m compileall -q src tests preprocessing/0_create_dataset.py` and `git diff --check` → exit 0.
- `git diff --quiet -- training/1_train_model.py inference/2_real_time_inference.py integrations/gamepad/gamepad_simulation.py src/gesture_vision/features.py` → exit 0; U1 features and U3–U6 wrappers are unchanged.

## Deviations from Design

None — U2 uses the shared extractor, lazily imports vision dependencies inside the live frame source, and finalizes complete sessions via `os.replace`.

## Remaining Tasks

- U3: 3.1–3.2 grouped training foundation.
- U4: 4.1–4.2 bundles and training.
- U5: 5.1–5.2 visual recognition.
- U6: 6.1–6.2 safe gamepad control.
- U7: 7.1–7.2 documentation and final verification.
