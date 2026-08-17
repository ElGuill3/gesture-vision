# safe-gamepad-control Specification

## Purpose

Connect recognized gestures to an optional Windows gamepad without allowing stale input to remain active.

## Requirements

### Requirement: Optional Windows integration

The gamepad command MUST treat the Windows gamepad dependency as optional. Importing the package and using capture, train, or infer MUST work without it; the gamepad command MUST report an actionable unsupported-platform or missing-dependency error before hardware access.

#### Scenario: Non-gamepad environment

- GIVEN a non-Windows host or no gamepad dependency
- WHEN a non-gamepad command is used
- THEN it remains available without importing or initializing gamepad hardware

### Requirement: Immediate neutralization on unsafe state

The gamepad workflow MUST release and neutralize every control immediately on signal loss, low confidence, inference/control error, and normal shutdown. Neutralization MUST be safe to repeat.

#### Scenario: Signal loss or low confidence

- GIVEN controls are active
- WHEN the hand signal disappears or falls below threshold
- THEN all controls are released in the same processing cycle

#### Scenario: Error or shutdown

- GIVEN controls are active
- WHEN inference raises an error or the workflow shuts down
- THEN all controls are released before the command exits
