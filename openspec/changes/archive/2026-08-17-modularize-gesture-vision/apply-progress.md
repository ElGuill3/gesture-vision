# Apply Progress: Modularize GestureVision

## Status

- Mode: Standard (strict TDD disabled in `openspec/config.yaml`)
- Delivery: `auto-chain`, `stacked-to-main`
- Work units: U1-package-feature-contract, U2-capture-sessions, U3-grouped-session-partition, U4-bundles-training, U5-visual-recognition, U6-safe-gamepad-control, U7-documentation-final-flow
- Completed: 1.1, 1.2, 2.1, 2.2, 3.1, 3.2, 4.1, 4.2, 5.1, 5.2, 6.1, 6.2, 7.1, 7.2
- U2 boundary: immutable JSON capture sessions and the preprocessing migration wrapper only.
- U3 boundary: pure, pre-fitter validation and whole-session partitioning only; U4 owns all ML imports, fitting, bundles, and wrapper changes.
- U4 boundary: validated immutable bundles, one portable active/previous selector, lazy session training, and the training wrapper only; U5–U7 remain untouched.
- U5 boundary: shared per-hand recognition, active-bundle validation before visual camera startup, and the inference wrapper only; U6–U7 remain untouched.
- U6 boundary: optional Windows gamepad adapter/workflow, package defaults, and the gamepad migration wrapper only; U7 remains untouched.
- U7 boundary: concise installable CLI documentation and hardware-free final-flow proof only; U1–U6 implementation paths remain unchanged.

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
- `tests/test_grouped_training.py`
- `openspec/changes/modularize-gesture-vision/apply-progress.md`
- `src/gesture_vision/bundles.py`
- `src/gesture_vision/workflows/train.py`
- `training/1_train_model.py`
- `tests/{test_bundles,test_train_workflow}.py`
- `src/gesture_vision/recognition.py`
- `src/gesture_vision/workflows/inference.py`
- `inference/2_real_time_inference.py`
- `tests/{test_recognition,test_inference_workflow}.py`
- `src/gesture_vision/adapters/{__init__,gamepad}.py`
- `src/gesture_vision/workflows/gamepad.py`
- `integrations/gamepad/gamepad_simulation.py`
- `tests/test_gamepad_safety.py`
- `README.md`

## Work Unit Evidence

| Work unit | Focused test command and exact result | Runtime harness command/scenario and exact result | Rollback boundary |
|---|---|---|---|
| U1-package-feature-contract | `python -m unittest tests.test_cli tests.test_features tests.test_safe_imports -v` → exit 0, 6 tests passed | `repo_root="$(git rev-parse --show-toplevel)"` at repository root; from `/tmp/opencode`, `"$repo_root/venv/bin/gesture-vision" {capture,train,infer,gamepad} --help` → exit 0; all four command-specific help screens rendered without hardware access | Revert U1's package, defaults, and U1 tests; legacy wrappers and data remain untouched |
| U2-capture-sessions | `python -m unittest tests.test_capture_sessions -v` → exit 0, 4 tests passed | `python -m unittest tests.test_capture_sessions.CaptureSessionTests.test_runs_are_isolated_and_need_no_hardware_imports -v` → exit 0, 1 test passed; fake workflow finalized left and right samples in one JSON session, created a distinct second session, and observed no `cv2` or `mediapipe` import | Revert `sessions.py`, `workflows/`, `test_capture_sessions.py`, and the wrapper delegation; keep U1 package/config/features intact |
| U3-grouped-session-partition | Fixed-seed test command: `python -m unittest tests.test_grouped_training -v` → exit 0, 3 tests passed | Fixed-seed temporary six-session JSON harness with `seed=17` → exit 0; stdout exactly `groups=2/2/2 repeatable=True complete_sessions=True ml_imports=[]` | Revert `sessions.partition_sessions` and `tests/test_grouped_training.py`; U1/U2 capture contracts and U4–U7 wrappers remain intact |
| U4-bundles-training | `python -m unittest tests.test_bundles tests.test_train_workflow -v` → exit 0, 4 tests passed | `python -m unittest tests.test_bundles.BundleTests.test_manifest_promotion_failure_and_rollback_keep_selector_safe tests.test_train_workflow.TrainWorkflowTests.test_fake_fit_promotes_only_after_complete_sessions_without_ml_imports tests.test_train_workflow.TrainWorkflowTests.test_invalid_sessions_fail_before_fitter_and_keep_selection -v` → exit 0, 3 tests passed; fake writer/loader staged, reloaded, validated, promoted, rolled back, rejected a partial candidate without selector mutation, and blocked all ML imports | Revert `bundles.py`, `workflows/train.py`, training defaults/wrapper, and U4 tests; selection then returns to its prior implementation while U1–U3 sessions/features and legacy 42 artifacts remain untouched |
| U5-visual-recognition | `python -m unittest tests.test_recognition tests.test_inference_workflow -v` → exit 0, 5 tests passed | `python -m unittest tests.test_inference_workflow.InferenceWorkflowTests.test_validated_bundle_recognizes_fake_hands_without_heavy_imports tests.test_inference_workflow.InferenceWorkflowTests.test_invalid_bundle_fails_before_fake_camera_opens -v` → exit 0, 2 tests passed; fake active bundle/model/scaler and left/right hand frames produced attributed labels without heavy imports, while a dimension-invalid bundle raised before the fake camera factory ran | Revert `recognition.py`, `workflows/inference.py`, the active-bundle loader, inference wrapper, and U5 tests; retain U1–U4 feature/session/bundle/training behavior and immutable bundle data |
| U6-safe-gamepad-control | `python -m unittest tests.test_gamepad_safety -v` → exit 0, 3 tests passed | `python -m unittest tests.test_gamepad_safety.GamepadSafetyTests.test_workflow_releases_on_loss_low_confidence_error_and_shutdown -v` → exit 0, 1 test passed; fake pad released on loss, low confidence, adapter error, and normal shutdown without camera, ViGEm, MediaPipe, TensorFlow, or vgamepad | Revert `adapters/gamepad.py`, `workflows/gamepad.py`, package gamepad defaults, wrapper delegation, and `test_gamepad_safety.py`; U1–U5 contracts remain intact |
| U7-documentation-final-flow | `python -c '<README required-statement assertion>'` → exit 0, `README contract readback: 16 required statements present` | From `/tmp/opencode`, project `venv/bin/gesture-vision` with `--help`, `capture --help`, `train --help`, `infer --help`, and `gamepad --help` → exit 0; all five help screens rendered without camera, ML, ViGEm, or gamepad access | Revert `README.md`, the two U7 task checkboxes, and U7 progress evidence; U1–U6 source, config, wrappers, tests, sessions, and bundles remain intact |

## Additional Verification

- `venv/bin/python -m pip install --no-deps --no-build-isolation -e .` → exit 0 after installing build-only `setuptools>=68` into the project-local ignored venv.
- `python -m unittest discover -s tests -v` → exit 0, 6 tests passed.
- `python -m compileall -q src tests` and `git diff --check` → exit 0.
- The four legacy wrapper SHA-256 values match their pre-U1 baseline.
- `python -m unittest tests.test_safe_imports -v` → exit 0, 1 test passed; all wrappers remain import-safe.
- `python -m unittest discover -s tests -v` → exit 0, 10 tests passed, including U1 feature-contract regression tests.
- `python -m compileall -q src tests preprocessing/0_create_dataset.py` and `git diff --check` → exit 0.
- `git diff --quiet -- training/1_train_model.py inference/2_real_time_inference.py integrations/gamepad/gamepad_simulation.py src/gesture_vision/features.py` → exit 0; U1 features and U3–U6 wrappers are unchanged.
- `python -m unittest tests.test_capture_sessions tests.test_features tests.test_safe_imports -v` → exit 0, 7 tests passed.
- `python -m unittest discover -s tests -v` → exit 0, 13 tests passed.
- `python -m compileall -q src tests` and `git diff --check` → exit 0.
- `git diff --quiet -- training/1_train_model.py inference/2_real_time_inference.py integrations/gamepad/gamepad_simulation.py` → exit 0; training, inference, and gamepad wrappers are unchanged.
- `python -m unittest tests.test_grouped_training tests.test_capture_sessions tests.test_features tests.test_safe_imports -v` → exit 0, 10 tests passed.
- `python -m unittest discover -s tests -v` → exit 0, 17 tests passed.
- `python -m compileall -q .` and `git diff --check` → exit 0.
- `git diff --quiet -- inference/2_real_time_inference.py integrations/gamepad/gamepad_simulation.py` → exit 0; inference and gamepad wrappers are unchanged.
- `python -m unittest tests.test_cli tests.test_features tests.test_capture_sessions tests.test_grouped_training tests.test_bundles tests.test_train_workflow tests.test_safe_imports -v` → exit 0, 17 tests passed; U1–U4 and safe-import regressions remain green.
- `python -m unittest discover -s tests -v` → exit 0, 22 tests passed.
- `python -m compileall -q .`, `git diff --check`, and `git diff --quiet -- integrations/gamepad/gamepad_simulation.py` → exit 0; bytecode compilation, whitespace validation, and the untouched gamepad wrapper all passed.
- `python -m unittest tests.test_cli tests.test_features tests.test_capture_sessions tests.test_grouped_training tests.test_bundles tests.test_train_workflow tests.test_recognition tests.test_inference_workflow tests.test_safe_imports -v` → exit 0, 22 tests passed; U1–U5, safe imports, inference, and training behavior remain green.
- `python -m unittest discover -s tests -v` → exit 0, 25 tests passed.
- `python -m compileall -q .`, `git diff --check`, and `git diff --quiet -- training/1_train_model.py inference/2_real_time_inference.py src/gesture_vision/recognition.py` → exit 0; compilation, whitespace validation, and the U4/U5 runtime paths are unchanged.
- `python -m unittest discover -s tests -v` → exit 0, 25 tests passed: CLI/config, features, capture, grouped split, bundle/training, inference, gamepad, and wrapper/import safety coverage all passed with fakes only.
- `python -m unittest tests.test_safe_imports -v` → exit 0, 1 test passed; all six guarded scripts remain import-safe.
- `python -m unittest tests.test_bundles.BundleTests.test_manifest_promotion_failure_and_rollback_keep_selector_safe -v` → exit 0, 1 test passed.
- From `/tmp/opencode`, project `venv/bin/gesture-vision` top-level and four subcommand help screens → exit 0 without runtime hardware access.
- `python -m compileall -q .`, `git diff --check`, and `git diff --quiet -- pyproject.toml config/config.yaml src/gesture_vision preprocessing/0_create_dataset.py training/1_train_model.py inference/2_real_time_inference.py integrations/gamepad/gamepad_simulation.py tests` → exit 0; U1–U6 bytes remain unchanged.

## Bounded Warning Remediation

- `VISUALIZATION.show_connections` now passes no MediaPipe hand connections when false and preserves connections when omitted or true; landmark visibility and colors are unchanged.
- Focused regression: `PYTHONDONTWRITEBYTECODE=1 venv/bin/python -m unittest tests.test_inference_workflow.InferenceWorkflowTests.test_connection_visibility_uses_only_fake_vision_runtime -v` → exit 0, 1 test passed; the complete inference workflow suite passed 4 tests.
- Full safe suite: `PYTHONDONTWRITEBYTECODE=1 venv/bin/python -m unittest discover -s tests -v` → exit 0, 26 tests passed. External-pycache compileall and `git diff --check` also exited 0.
- The regression substitutes fake OpenCV and MediaPipe modules, injects a fake camera, and uses fake GUI functions; TensorFlow/joblib imports and the real camera path fail the test.
- U1 evidence is corrected from 318 to 314 authored changed lines (`311 insertions + 3 deletions`), with dependent forecast aggregates corrected from ~2,452/~2,479 to ~2,448/~2,475.
- Accepted design deviation: vision and ML integration intentionally remains workflow-owned; no `adapters/vision.py` or `adapters/ml.py` is added.
- Rollback boundary: revert the connection argument in `workflows/inference.py`, remove the named regression, restore the three U1 ledger estimates in `tasks.md`, and remove this section. Keep the stale `verify-report.md` absent pending independent re-verification.

## Deviations from Design

Accepted — vision and ML integrations remain workflow-owned rather than using separate adapter files. U2 uses the shared extractor, lazily imports vision dependencies inside the live frame source, and finalizes complete sessions via `os.replace`; U3 adds only standard-library validation and whole-session grouping; U4 preserves the Spanish legacy training copy behind an import-safe delegating entrypoint; U5 retains the Spanish visual runtime copy while its wrapper delegates to the validated shared workflow; U6 preserves the Spanish gamepad runtime copy behind an import-safe delegating entrypoint and uses the existing optional `vgamepad` extra; U7 documents the shipped contracts without changing their implementation.

## Remaining Tasks

- None — all 14 tasks are complete; next recommended phase is `sdd-verify`.
