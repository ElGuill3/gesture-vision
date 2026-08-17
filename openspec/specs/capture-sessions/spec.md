# capture-sessions Specification

## Purpose

Capture reproducible, attributable hand samples under one immutable session schema.

## Requirements

### Requirement: Canonical 63-feature contract

The extractor MUST use schema identity `mediapipe-xyz-wrist-v1`. For landmarks `L0` through `L20`, it MUST emit exactly 63 finite values in landmark-major, XYZ-interleaved order: `(Li.x-L0.x, Li.y-L0.y, Li.z-L0.z)` for every `i` from 0 through 20. Metadata MUST NOT become model features, and 42-feature output MUST NOT be produced by this capability.

#### Scenario: Valid landmark sample

- GIVEN exactly 21 complete finite MediaPipe landmarks
- WHEN a sample is extracted
- THEN the vector has 63 values in the specified order and carries the schema identity

#### Scenario: Invalid landmark input

- GIVEN a missing, extra, incomplete, or non-finite landmark
- WHEN extraction is requested
- THEN it fails validation and writes no sample

### Requirement: Immutable sessions with correct hand attribution

Each completed capture session MUST create exactly one immutable session file. Each accepted hand in a frame MUST produce its own sample with the detector's unambiguous `left` or `right` attribution; one hand MUST NOT overwrite another.

#### Scenario: Two-hand frame

- GIVEN one frame contains both left and right hands
- WHEN the frame is accepted
- THEN two separately attributed samples are recorded in the same session file

#### Scenario: Session finalization

- GIVEN session S has completed
- WHEN later capture activity occurs
- THEN S's file and samples remain unchanged and a new session uses a new file
