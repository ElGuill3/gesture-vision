# Tasks: Modularize GestureVision

## Review Workload Forecast

9 PRs; ~2,448 / ~2,475 snapshot lines (`285/259/314/300/180/330/320/300/160`); ~571 pre-U1; <400 each.

Decision needed before apply: No
Chained PRs recommended: Yes
Chain strategy: stacked-to-main
400-line budget risk: High
Delivery strategy: auto-chain

Order `A → B → U1 → U2 → U3 → U4 → U5 → U6 → U7`; stacked-to-main after merge. B U1=[ ]; U1/current U1=[x]+`apply-progress.md`. Reconstruct later; preserve files; no staging.

Review: A/B docs; U1 314 (311 insertions + 3 deletions); U2–U7 160–330; tests/docs together; rollback.

### Delivery PR Ledger

| PR | Scope/prereq/lines | Proof | Rollback |
|---|---|---|---|
| A | `openspec/config.yaml`, exploration/proposal/design; base; 285 | Docs/N/A | A docs |
| B | Five specs + baseline `tasks.md` (U1 unchecked); A; 259 | Spec/N/A | B specs |
| U1 | `pyproject.toml`, `src/`, U1 tests, checkbox, `apply-progress.md`; B; 314 (311 insertions + 3 deletions) | Evidence | U1 files/progress |
| U2 | `sessions.py`, capture/vision paths; U1; 300 | `python -m unittest tests.test_capture_sessions -v`; fake JSON | U2; artifacts |
| U3 | `sessions.partition_sessions`; U2; 180 | `python -m unittest tests.test_grouped_training -v`; seeded split | U3; keep sessions |
| U4 | Bundles/train paths; U3; 330 | `python -m unittest tests.test_bundles tests.test_train_workflow -v`; fake promotion | U4; selector |
| U5 | Recognition/infer paths; U4; 320 | `python -m unittest tests.test_recognition tests.test_inference_workflow -v`; fake camera | U5; retain U2–U4 |
| U6 | Gamepad paths; U5; 300 | `python -m unittest tests.test_gamepad_safety -v`; fake neutralization | U6/config |
| U7 | `README.md`/verification; U1–U6; 160 | Full unittest/compileall/help | Docs only |

## Phase 1: Package and Feature Contract

- [x] 1.1 (U1) Create lazy CLI/config and `extract_landmark_features` for `mediapipe-xyz-wrist-v1`: 63 finite XYZ-interleaved values; reject invalid/42.
- [x] 1.2 (U1) Add defaults, YAML→CLI/rooted paths; test help/safe imports and preserve four wrappers.

## Phase 2: Capture Sessions

- [x] 2.1 (U2) Create UUID4 JSON sessions/capture workflow: per-hand samples, atomic `os.replace`, immutable finalization, no failure file.
- [x] 2.2 (U2) Delegate `preprocessing/0_create_dataset.py`; test invalid landmarks, two-hand attribution, and new-session isolation.

## Phase 3: Grouped Training Foundation

- [x] 3.1 (U3) Add `sessions.partition_sessions`: validate complete/schema-compatible files; seeded, non-empty, disjoint train/validation/test membership.
- [x] 3.2 (U3) Test failure before fitter/import and document the session boundary.

## Phase 4: Bundles and Training

- [x] 4.1 (U4) Add bundle manifest/hash/schema/dimension validation, staged reload, atomic active/previous promotion, and rollback; leave legacy 42 artifacts.
- [x] 4.2 (U4) Add lazy ML/train workflow; update `training/1_train_model.py`/config; test fail-before-fit and unchanged selections.

## Phase 5: Shared Visual Recognition

- [x] 5.1 (U5) Create `recognize_frame`: per-hand smoothing clears on missing/invalid/below-threshold input and emits no stale label.
- [x] 5.2 (U5) Update `inference/2_real_time_inference.py`; test attribution, empty next history, and validation before camera open.

## Phase 6: Safe Gamepad Control

- [x] 6.1 (U6) Add Windows/dependency-gated adapter/workflow honoring `hand_mapping`; idempotent `neutralize` releases every control in-cycle and `finally`.
- [x] 6.2 (U6) Update `integrations/gamepad/gamepad_simulation.py`/config; test non-gamepad availability and loss, low-confidence, error, shutdown release.

## Phase 7: Documentation and Verification

- [x] 7.1 (U7) Rewrite `README.md` for editable install, four commands, 63-feature/session/bundle contracts, wrappers, Windows gamepad, no stale formats.
- [x] 7.2 (U7) Run tests, compileall, CWD help, safe-import; verify rollback.
