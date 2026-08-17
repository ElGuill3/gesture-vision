# visual-recognition Specification

## Purpose

Provide one validated recognition path for visual output and downstream control.

## Requirements

### Requirement: Shared validated recognition

Visual recognition MUST use the canonical 63-feature contract and a compatible validated bundle for extraction, normalization, scaling, thresholding, and label decoding. Compatibility MUST be checked before camera startup.

#### Scenario: Compatible inference

- GIVEN a compatible active bundle and a valid hand observation
- WHEN inference runs
- THEN it returns the attributed label and confidence through the shared recognition result

#### Scenario: Incompatible bundle

- GIVEN a bundle with mismatched schema, dimensions, or labels
- WHEN visual inference is requested
- THEN it fails before opening the camera

### Requirement: Immediate per-hand smoothing reset

Smoothing state MUST be independent per hand and MUST clear immediately when that hand disappears or its confidence is below threshold. The affected frame MUST emit no stale gesture, and the next valid observation MUST start with empty history.

#### Scenario: Hand disappears

- GIVEN a hand has a smoothed gesture
- WHEN that hand is absent in the next frame
- THEN its history is cleared and no prior gesture is emitted

#### Scenario: Confidence drops

- GIVEN a hand is detected below the confidence threshold
- WHEN the frame is processed
- THEN its history is cleared immediately and control receives no accepted gesture
