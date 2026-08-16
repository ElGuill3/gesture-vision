## Exploration: Modularize GestureVision

### Current State

GestureVision is four procedural programs joined by YAML keys and filesystem artifacts, not by reusable Python modules. Each script defers third-party imports and work to `main()`, which is the one behavior currently protected by a test (`tests/test_safe_imports.py:18-127`). There is no `pyproject.toml`, package directory, or console entrypoint, so the repository is not installable as an application.

#### Verified pipeline and coupling

| Stage | Current flow | Coupling and consequences |
|---|---|---|
| Capture | `preprocessing/0_create_dataset.py:62-119` reads webcam frames, flips them, runs MediaPipe, and flattens landmarks. A keypress appends one in-memory sample; exit overwrites the configured CSV (`:121-141`). | With two detected hands, `features` is overwritten inside the loop and the last hand is saved without handedness (`:76-109`). Capture does not append to an existing dataset. |
| Train | `training/1_train_model.py:46-85` reads the CSV, drops `label`, label-encodes, performs a stratified random row split, and fits `StandardScaler`; `:87-174` trains Keras and writes model, scaler, and encoder separately. | It trusts every non-`label` column as an input feature. Adjacent capture frames can cross the random split because the dataset has no session/group field. A partial three-file write can publish an incompatible artifact set. |
| Visual inference | `inference/2_real_time_inference.py:23-47` loads three independent files, then `:90-125` duplicates landmark extraction, scaling, prediction, thresholding, label decoding, and per-hand smoothing. | No artifact compatibility validation occurs before camera startup beyond file existence. Smoothing buffers retain confident votes across missing-hand or low-confidence gaps. |
| Gamepad | `integrations/gamepad/gamepad_simulation.py:25-52` repeats artifact and hardware setup; `:245-280` repeats the inference path; `:296-343` maps left/right predictions to controls. | Recognition, visualization, and `vgamepad` state mutation share one 397-line function. Controls are released when a hand has no accepted prediction and again in `finally` (`:381-392`), but this safety behavior has no focused test. |

The actual shared feature contract is implicit and copied in capture (`preprocessing/0_create_dataset.py:88-95`), inference (`inference/2_real_time_inference.py:95-103`), and gamepad (`integrations/gamepad/gamepad_simulation.py:250-258`):

- MediaPipe landmark order `0..20`.
- Interleaved `x, y` coordinates only, flattened to 42 values.
- Optional subtraction of landmark `0` (wrist) from every point; current config enables it.
- No handedness in the feature vector or CSV.
- `PREPROCESSING.use_z_coordinate` is configured but unused (`config/config.yaml:20-23`); enabling it currently changes nothing.

The checked-in working artifacts agree on 42 inputs: the CSV has columns `0..41,label` and 800 rows in four contiguous 200-row label runs; the scaler pickle declares `n_features_in_=42`; the Keras archive has input shape 42 and four outputs; and the encoder contains `LB`, `LT`, `RB`, and `RT`. The Keras archive records Keras 3.10.0, but there is no common version, feature schema, checksum manifest, or library compatibility record tying the three files together.

Configuration centralizes values but not behavior. Artifact paths in `config/config.yaml:23,45-55` are relative to the process working directory, while the YAML itself is located from each script. Several keys are currently decorative or partially ignored (`CAMERA.width/height`, `PREPROCESSING.use_z_coordinate`, `VISUALIZATION.show_connections`, and `GAMEPAD.hand_mapping`). The README also claims an `.h5` output while configuration and training use `.keras` (`README.md:101-112`).

#### Boundary that fits this repository

| Boundary | Owns | Must not own |
|---|---|---|
| Recognition core | Landmark-to-feature contract, bundle compatibility checks, scaling/prediction/label decoding, threshold policy, and per-hand smoothing state. | Camera loops, MediaPipe objects, OpenCV drawing, YAML lookup, CLI parsing, or gamepad mutations. |
| Workflows/use cases | Capture session, train run, visual inference loop, and gamepad inference loop; they coordinate core functions and concrete collaborators. | Console argument parsing or framework-specific object construction. |
| CLI entrypoint | One `gesture-vision` command with `capture`, `train`, `infer`, and `gamepad` subcommands; config/path selection, user-facing errors, and lazy command dispatch. | Feature extraction, model decisions, or hardware loops. |
| Adapters | MediaPipe landmark conversion, OpenCV camera/display, Keras/joblib persistence, CSV I/O, and Windows-only `vgamepad` output. | Business decisions such as thresholds, smoothing semantics, or which gesture means which logical action. |

These are module boundaries, not a mandate for an interface per dependency. Plain functions, small stateful objects where state is real, and duck-typed fakes are sufficient.

### Affected Areas

- `preprocessing/0_create_dataset.py` — preserve the direct command while routing feature extraction and later capture orchestration through the package.
- `training/1_train_model.py` — preserve training behavior while moving dataset validation and artifact publication behind shared modules.
- `inference/2_real_time_inference.py` — remove copied extraction/prediction/smoothing after characterization tests exist.
- `integrations/gamepad/gamepad_simulation.py` — share recognition while keeping mapping and release safety in the gamepad workflow/adapter.
- `config/config.yaml` — retain existing keys during migration; add only a bundle path/version selection when its loader exists.
- `data/datasets/dataset_gestos.csv` — legacy schema must remain readable; future schema metadata cannot become accidental model features.
- `data/models/modelo_gestos.keras`, `data/models/scaler.save`, `data/models/label_encoder.save` — support as an explicit legacy bundle rather than silently rewriting them.
- `tests/test_safe_imports.py` — keep the import-safety contract and add discoverable, hardware-free unit tests around extracted logic.
- `README.md` — document installation, subcommands, compatibility scripts, bundle layout, and corrected `.keras` behavior after implementation.
- `pyproject.toml` and `src/gesture_vision/` — new installable package metadata and modular-monolith code, introduced incrementally.

### Approaches

1. **Contract-first strangler migration** — Introduce the package and pure feature/schema contract first, make legacy scripts delegate a seam at a time, then migrate bundles, workflows, and CLI commands in reviewable slices.
   - Pros: Removes training-serving skew at its source; preserves direct scripts; each slice is testable and revertible; supports the 400-line review budget.
   - Cons: Temporary mixed architecture and compatibility adapters; duplicate loop code remains until later slices.
   - Effort: Medium

2. **Workflow-by-workflow migration** — Move capture, then train, infer, and gamepad into the package, extracting common logic only when the second caller moves.
   - Pros: Each migrated command is end-to-end usable; simple delivery narrative.
   - Cons: Shared feature and inference code remains duplicated longer, and early workflow choices can harden the wrong contract.
   - Effort: Medium

3. **CLI facade over existing scripts** — Add packaging and commands that execute the four scripts with minimal internal change.
   - Pros: Fastest path to an installable command and lowest immediate behavior risk.
   - Cons: Hides rather than fixes coupling, leaves numeric script modules and duplicate recognition logic, and provides little testability.
   - Effort: Low

4. **Big-bang layered rewrite** — Replace all scripts at once with ports/adapters, repositories, dependency injection, plugins, and a model registry.
   - Pros: A clean end state can be drawn before migration begins.
   - Cons: High regression and rollback risk, poor reviewability, and abstractions without multiple implementations or operational need.
   - Effort: High

### Recommendation

Use **Approach 1, the contract-first strangler**, and auto-chain implementation into independently revertible slices. Do not combine packaging, all workflow moves, artifact format replacement, and behavior fixes in one PR.

#### Smallest safe first slice

Keep the first implementation slice below the 400-line review budget:

1. Add minimal `pyproject.toml` and `src/gesture_vision/` packaging.
2. Add a dependency-light feature function that accepts 21 `(x, y)` pairs and returns the existing 42-value interleaved vector, with optional wrist normalization and no dtype/schema expansion.
3. Define a legacy CSV schema validator for exactly `0..41,label`; characterize the current dataset contract without changing stored files.
4. Add discoverable standard-library tests for ordering, dimension, normalization, invalid landmark counts, and legacy headers.
5. Route only the three copied extraction blocks through this function, importing from inside `main()` so the current safe-import guarantee remains intact.

This slice removes the highest-risk duplication without moving camera loops, training, or gamepad behavior. Direct scripts remain the compatibility entrypoints while the package is established.

#### Subsequent migration slices

- **Bundle slice:** Treat the current three configured paths as `legacy-v0`. Add a bundle directory containing the unchanged Keras/joblib formats plus `manifest.json`; record bundle schema, feature schema (`mediapipe-xy-wrist-v1`), input/output dimensions, ordered labels, relevant library versions, and checksums. Stage and validate the directory before atomic promotion. A new loader may prefer a configured bundle path and fall back to the legacy triple.
- **Recognition slice:** Centralize scaling, prediction, thresholding, label decoding, and per-hand smoother state. Define and test whether missing/low-confidence observations clear smoothing; changing the current stale-buffer behavior should be an explicit behavior decision, not an accidental refactor.
- **Workflow/CLI slices:** Move one workflow at a time, starting with capture or visual inference, then training, then the Windows-only gamepad path. Add one console script with subcommands and lazy imports. Convert the corresponding direct script into a thin wrapper only after parity tests exist.
- **Cleanup slice:** Remove compatibility code only after the documented deprecation window and after all direct paths invoke the same workflows.

#### Dataset compatibility

The 42-column CSV remains schema v1. A sidecar metadata file may record feature schema and capture settings without adding columns that training would mistake for model inputs. If metadata is absent, the exact `0..41,label` header identifies legacy v1. Adding Z coordinates, handedness, session IDs, or semantic column names is a new dataset schema and requires explicit migration/retraining. Group-aware validation splitting also requires capture-session data and should not be smuggled into this behavior-preserving architecture change.

#### Compatibility and rollback

- Keep `python preprocessing/0_create_dataset.py`, `python training/1_train_model.py`, `python inference/2_real_time_inference.py`, and `python integrations/gamepad/gamepad_simulation.py` working as wrappers during migration.
- Preserve current YAML keys and the legacy CSV/triple-artifact readers; warn on legacy loading only after the new path is proven.
- Publish new bundles beside, never over, the current three artifacts. Rollback is then a config change or PR revert, not artifact reconstruction.
- Preserve gamepad fail-safe release in every exit/error path before refactoring control updates.
- Avoid a permanent runtime feature-flag framework; the chained PR boundaries and legacy loader are enough rollback surface.

#### What can be proven without hardware

The explicit safe-import test passed during this exploration. Hardware-free tests can also prove feature-vector parity, dataset schema validation, path resolution, manifest checks, model/scaler/label dimension agreement, thresholding, label decoding, smoothing/reset policy, CLI dispatch, gesture-to-logical-control mapping, and release-all transitions using synthetic landmarks and fakes. They cannot prove camera enumeration/frame behavior, MediaPipe tracking quality, TensorFlow training quality/performance, real serialized loading in an environment missing those dependencies, OpenCV windows, or ViGEm/`vgamepad`; those remain environment-specific smoke tests.

Do not introduce microservices, an event bus, a DI container, a repository layer for local files, a plugin system, MLflow/feature stores, a database-backed model registry, or one-implementation interfaces. The application needs a small package with explicit seams, not enterprise infrastructure.

### Risks

- Refactoring all three consumers before freezing the 42-feature contract could silently invalidate existing datasets and models.
- Loading independently updated legacy artifacts can produce dimension or label-order mismatches; validation must happen before camera/gamepad activation.
- Changing smoothing reset semantics or two-hand capture selection during structural migration would violate behavior preservation unless separately specified.
- Path resolution changes can break users who currently rely on launching from the repository root; compatibility tests must cover direct scripts and installed commands.
- Gamepad regressions can leave controls pressed; release-all behavior needs a fake-adapter test and must stay in `finally`.
- The current Python environment passes only dependency-blocked safe-import tests and lacks `joblib`, so framework-backed bundle loading cannot be claimed here.
- The full change will likely exceed 400 authored lines; auto-chained slices are required to keep review and rollback bounded.

### Ready for Proposal

Yes. The proposal should commit to a contract-first, chained migration; preserve the 42-value legacy feature/CSV contract and direct scripts; introduce manifest-backed bundles without replacing legacy artifacts in place; and explicitly defer Z/handedness schema changes, split-quality changes, and enterprise infrastructure. The next phase is `sdd-propose`; no proposal was authored during this exploration.
