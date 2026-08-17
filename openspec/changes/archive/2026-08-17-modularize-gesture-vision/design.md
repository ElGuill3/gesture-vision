# Design: Modularize GestureVision

## Technical Approach

Build a contract-first `src` modular monolith with temporary legacy wrappers. Setuptools declares dependencies in `pyproject.toml`, exposes `gesture-vision = gesture_vision.cli:main`, and makes Windows-only `vgamepad` a `gamepad` extra. `argparse` owns four fixed routes; workflows/adapters import only after help and configuration.

## Architecture Decisions

| Decision | Choice | Alternatives / tradeoff | Rationale |
|---|---|---|---|
| Boundaries | Pure feature/grouping/recognition functions, workflows, concrete adapters | Flat scripts duplicate logic; DI/ports add ceremony | Shared behavior gets one owner without interfaces or factories. |
| Configuration | Packaged defaults, optional YAML overlay, then explicit CLI values via `argparse.SUPPRESS` | Parser defaults overwrite YAML | Omitted flags remain YAML-controlled; `PATHS.root` makes paths CWD-independent. |
| Sessions | One versioned JSON file per UUID4 session | CSV risks metadata becoming features | JSON separates contracts and supports one-time atomic finalization. |
| Publication | Immutable bundle directories and one active/previous selector | Directory swaps/symlinks vary on Windows | Replacing one same-directory file is the cross-platform commit point. |

## Module Map / File Changes

| File | Action | Responsibility |
|---|---|---|
| `pyproject.toml` | Create | Build metadata, console script, gamepad extra |
| `src/gesture_vision/{cli,config,features,sessions,bundles,recognition}.py` | Create | Commands and dependency-light contracts |
| `src/gesture_vision/workflows/{capture,train,inference,gamepad}.py` | Create | Use cases and shared live recognition |
| `src/gesture_vision/adapters/{vision,ml,gamepad}.py` | Create | Concrete third-party integration |
| `src/gesture_vision/defaults.yaml`, `config/config.yaml` | Create/Modify | Installed defaults and repository overlay |
| Four legacy scripts | Modify | Runtime `src` bootstrap and workflow delegation |
| `tests/test_*.py`, `README.md` | Create/Modify | Contracts and user migration |

## Data Flow

```text
CLI -> defaults + YAML + overrides -> workflow
capture -> vision -> 63-feature extractor -> session JSON
train -> validate sessions -> grouped split -> ML adapter -> staged bundle -> validate -> selector
infer/gamepad -> validate active bundle -> vision -> recognize_frame -> display / controls
```

## Interfaces / Contracts

- `mediapipe-xyz-wrist-v1` accepts 21 finite landmarks and emits `(Li.x-L0.x, Li.y-L0.y, Li.z-L0.z)` for `i=0..20`: 63 finite landmark-major/interleaved values. It rejects invalid or 42-value input; metadata never enters ML.
- Session JSON contains `format_version`, UUID4 `session_id`, schema, UTC start/end, `status: complete`, and `{frame_id, hand, label, features}` samples. Each unambiguous lowercase `left|right` hand appends separately. Finalization flushes a sibling temporary file, calls `os.replace` once, and never rewrites the final path.
- Grouping validates all files before ML import/fitting, seed-shuffles sorted IDs, requires non-empty train/validation/test groups, assigns each session once, and records membership.
- Layout: `bundles/<bundle_id>/{model.keras,scaler.joblib,manifest.json}` and `bundles/selection.json`. Required manifest fields: format/bundle IDs, UTC creation, schema, input/output dimensions, ordered labels plus hash, artifact names/SHA-256, split seed/groups, and Python/TensorFlow/scikit-learn/joblib versions. Validation checks hashes, unique labels, schema, scaler/model input 63, and model output count before promotion or camera startup.
- Promotion stages beside the destination, closes and reload-validates files, renames to an immutable ID, then replaces the selector. Failure preserves both slots. Rollback validates `previous` and swaps IDs through the same atomic write.
- `recognize_frame` returns per-hand label/confidence. Missing, invalid, sub-threshold, or previously active-but-absent hands clear their deque and emit no label. Any unsafe event, camera loss, exception, or shutdown makes idempotent `neutralize()` release every tracked button, zero triggers, and update in-cycle and in `finally`.
- The vision adapter applies configured camera dimensions and connection visibility; gamepad validates and honors `hand_mapping`. Schema normalization/Z are fixed, not toggles.

## Failure Handling

Configuration/session/bundle errors precede fitting or camera access. Capture failure finalizes nothing; publication failure preserves selection. Only `gamepad` checks Windows and imports `vgamepad`, before device creation.

## Testing Strategy

| Layer | Hardware-free proof |
|---|---|
| Unit | Feature order, two-hand attribution, disjoint groups, bundle validation/promotion/rollback, resets, neutralization |
| Integration | Help/lazy dispatch, YAML/CLI precedence from another CWD, workflows with fake detector/model/scaler/gamepad, fail-before-fit/open |
| Regression | Extend safe-import barriers; `python -m unittest discover -s tests -v`; `python -m compileall -q .` |

Camera, TensorFlow training, OpenCV windows, and vgamepad remain documented smoke checks.

## Threat Matrix

| Boundary | Applicability | Reason / RED tests |
|---|---|---|
| Documentation-like paths | N/A | No file is classified or executed; routes are fixed argparse tokens. |
| Git repository selection | N/A | No VCS operation exists. |
| Commit state | N/A | No commit operation exists. |
| Push state | N/A | No push operation exists. |
| PR commands | N/A | No PR automation exists. |

## Migration / Rollout

Auto-chain work units capped at 400 changed lines: (1) package/config/features; (2) sessions/capture; (3) grouped split; (4) ML bundles/train; (5) recognition/infer; (6) gamepad safety; (7) docs cleanup. These are scopes, not chain topology; task planning selects topology. Tests travel with each slice. Revert only that slice, keep unsupported legacy 42 artifacts untouched, and retain immutable sessions/bundles. Model rollback swaps validated selector slots.

## Open Questions

None.
