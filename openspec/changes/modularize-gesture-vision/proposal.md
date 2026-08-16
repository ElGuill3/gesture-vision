# Proposal: Modularize GestureVision

## Intent

Create an installable CLI from four procedural scripts while removing feature drift, session leakage, stale smoothing, and gamepad safety gaps. Preserve import safety and scripts as migration wrappers.

## Scope

### In Scope
- Ship `gesture-vision capture|train|infer|gamepad` with YAML defaults and CLI overrides.
- Use 63 ordered MediaPipe X, Y, Z features for every new sample and model.
- Write one file per completed capture session and partition multiple complete sessions across train/validation/test.
- Promote one active model bundle atomically and retain its immediate predecessor.
- Fix two-hand overwrite, ignored supported settings, smoothing reset, and control release.

### Out of Scope
- Preserving or migrating the 42-feature dataset/model; regeneration is allowed.
- Removing migration wrappers.
- GUI, web services, microservices, DI/plugins, model registry services, MLflow, or feature stores.

## Capabilities

### New Capabilities
- `local-cli`: Installable four-command entrypoint with lazy dispatch, merged configuration, and wrappers.
- `capture-sessions`: Per-session files, 63-feature schema, and no two-hand result overwrite.
- `grouped-training`: Session-grouped partitions and atomic active/previous bundles.
- `visual-recognition`: Shared inference with immediate smoothing reset after missing or low-confidence hands.
- `safe-gamepad-control`: Post-inference, optional Windows integration that releases controls on loss or error.

### Modified Capabilities
None.

## Approach

Apply a contract-first strangler as auto-chained, independently reversible slices within 400 changed lines: package/config/features; capture; training/bundles; visual inference; then gamepad. Chain topology remains undecided until task planning. Retain wrappers and lazy imports until parity coverage exists.

## Affected Areas

| Area | Impact | Description |
|---|---|---|
| `pyproject.toml`, `src/gesture_vision/` | New | Package, workflows, adapters, CLI |
| `preprocessing/`, `training/`, `inference/`, `integrations/gamepad/` | Modified | Wrappers |
| `config/config.yaml` | Modified | Defaults and bundle selection |
| `data/datasets/`, `data/models/` | Modified | Sessions and bundles |
| `tests/`, `README.md` | Modified | Contracts and usage |

## Risks

| Risk | Likelihood | Mitigation |
|---|---|---|
| Schema or split mismatch | Medium | Validate features and session disjointness |
| Incompatible bundle | Medium | Stage and validate before promotion |
| Stuck controls | High | Test release on loss, error, and cleanup |

## Rollback Plan

Revert only the failing slice, keep wrappers callable, and select the retained previous bundle. Never overwrite that bundle or completed session files.

## Dependencies

- Existing vision/ML stack; optional Windows-only `vgamepad`.

## Success Criteria

- [ ] Installation exposes four commands without import-time hardware access.
- [ ] Captures have 63 features and separate sessions; partitions share no session.
- [ ] Training retains one active and one previous validated bundle.
- [ ] Missing/low-confidence hands reset smoothing; controls release on loss/error.
- [ ] Each slice is reversible and at most 400 changed lines.
