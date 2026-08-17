# local-cli Specification

## Purpose

Provide one installable local entrypoint for capture, training, visual inference, and optional gamepad control.

## Scope boundary

The system MUST remain a local modular monolith. It MUST NOT add 42-feature compatibility, GUI/web services, microservices, DI/plugins, external model registries, MLflow, or feature stores.

## Requirements

### Requirement: Installable command surface

The distribution MUST expose `gesture-vision capture`, `train`, `infer`, and `gamepad` commands.

#### Scenario: Installed command help

- GIVEN the package is installed
- WHEN each command is invoked with help
- THEN each command returns its own usage without starting hardware

### Requirement: Configuration precedence

The CLI MUST load YAML values as defaults and MUST apply explicit command-line overrides after loading them; an explicit override MUST win.

#### Scenario: Default and override resolution

- GIVEN YAML contains value A and the command supplies value B
- WHEN configuration is resolved
- THEN B is used, while A remains the default when no override is supplied

### Requirement: Lazy dispatch and import safety

The entrypoint MUST import and execute only the selected command. Importing the package, showing top-level help, or running an unrelated command MUST NOT access cameras, MediaPipe, OpenCV, TensorFlow, or gamepad hardware.

#### Scenario: Optional dependencies are absent

- GIVEN camera and optional dependencies are unavailable
- WHEN the package is imported or a non-gamepad command is inspected
- THEN no hardware side effect occurs and command dispatch remains safe

### Requirement: Migration wrappers

The existing paths `preprocessing/0_create_dataset.py`, `training/1_train_model.py`, `inference/2_real_time_inference.py`, and `integrations/gamepad/gamepad_simulation.py` MUST remain callable during migration and MUST delegate to the corresponding package workflow without changing their callable entry behavior.

#### Scenario: Direct script invocation

- GIVEN a legacy script is invoked directly
- WHEN its callable entrypoint runs
- THEN the corresponding modular workflow is selected and import-time work remains absent
