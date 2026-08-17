# GestureVision CLI workflow

Capture hand gestures, train a validated local bundle, then run visual inference or optional virtual-gamepad control.

## Install

The package declares Python 3.11+. The lightweight CLI install includes its configuration dependency; live camera and training workflows also need the packages in `requirements.txt`. Use a Python and platform supported by those heavy dependency wheels.

```bash
python -m venv .venv
# Activate .venv for your shell.
python -m pip install -e .
python -m pip install -r requirements.txt  # required for capture, train, and infer runtimes
```

The gamepad workflow is optional and Windows-only. On Windows, install its extra and the ViGEmBus driver required by the virtual Xbox controller stack before using it:

```bash
python -m pip install -e ".[gamepad]"
```

## Discover the CLI

```bash
gesture-vision --help
gesture-vision capture --help
gesture-vision train --help
gesture-vision infer --help
gesture-vision gamepad --help
```

Help and package imports do not open a camera, load MediaPipe or TensorFlow, or create a gamepad. The four commands are `capture`, `train`, `infer`, and `gamepad`.

## Configure paths and camera

Configuration precedence is: packaged defaults, then an optional YAML file supplied with `--config`, then explicit CLI values such as `--camera-index`. `--root` selects `PATHS.root`; relative paths in `PATHS` resolve beneath it.

```bash
gesture-vision capture --config config/config.yaml --camera-index 1 --root .
```

Use `config/config.yaml` as the repository overlay, or supply your own YAML overlay. Set `PATHS.sessions` and `PATHS.bundles` there when the defaults do not match your workspace.

## Capture, train, then run

1. **Capture sessions** — this needs a camera, OpenCV, and MediaPipe. Press a configured `GESTURE_CAPTURE` key while a hand is visible; press Escape to finish.

   ```bash
   gesture-vision capture --config config/config.yaml --root .
   ```

   A non-empty run writes one immutable JSON session under `PATHS.sessions`. Every accepted hand becomes a separately attributed sample with the `mediapipe-xyz-wrist-v1` contract: 63 finite, wrist-relative XYZ values. Do not train the new workflow from legacy 42-feature CSV or model artifacts.

2. **Train a bundle** — this needs the ML packages, including TensorFlow, scikit-learn, and joblib.

   ```bash
   gesture-vision train --config config/config.yaml --root .
   ```

   Training validates complete compatible sessions before fitting, keeps each session wholly in train, validation, or test, and requires enough sessions for all three groups. It stages a validated bundle in `PATHS.bundles`; the selector retains active and immediate previous bundle IDs for rollback.

3. **Run visual inference** — this needs an active validated bundle plus the camera/vision runtime.

   ```bash
   gesture-vision infer --config config/config.yaml --root .
   ```

   The workflow validates the selected bundle before opening the camera and clears a hand's smoothed label when that hand is absent or below the configured confidence threshold.

4. **Run optional gamepad control** — Windows, `vgamepad`, ViGEmBus, an active bundle, and the live camera runtime are required.

   ```bash
   gesture-vision gamepad --config config/config.yaml --root .
   ```

   The command fails before device creation on a non-Windows host or when the optional dependency is missing. It neutralizes supported controls on signal loss, low confidence, errors, and shutdown.

## Migration wrappers

These existing entry points remain callable and delegate to the matching modular workflow:

- `preprocessing/0_create_dataset.py` → `capture`
- `training/1_train_model.py` → `train`
- `inference/2_real_time_inference.py` → `infer`
- `integrations/gamepad/gamepad_simulation.py` → `gamepad`

They are migration paths; use `gesture-vision` for new runs.
