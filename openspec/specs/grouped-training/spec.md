# grouped-training Specification

## Purpose

Train only on compatible session data and publish complete model artifacts safely.

## Requirements

### Requirement: Complete-session disjoint partitions

Training MUST assign each completed session ID wholly to exactly one of train, validation, or test. No session, including either hand's samples, MAY occur in more than one partition; incomplete or invalid sessions MUST be rejected before training.

#### Scenario: Multiple completed sessions

- GIVEN multiple valid session files and a deterministic split seed
- WHEN partitions are created
- THEN every session is assigned once, partitions are session-disjoint, and all samples from a session stay together

#### Scenario: Incomplete session input

- GIVEN a session file is incomplete or schema-incompatible
- WHEN training starts
- THEN training fails before fitting or publishing artifacts

### Requirement: Validated active and previous bundles

The system MUST validate a staged bundle's model, scaler, labels, dimensions, checksums, and feature schema before promotion. Promotion MUST be atomic. After a successful replacement, one validated bundle MUST be active and the immediately previous active bundle MUST be retained as the previous backup.

#### Scenario: Successful promotion

- GIVEN a valid candidate and active bundle A
- WHEN the candidate is promoted
- THEN the candidate becomes active and A is retained as previous

#### Scenario: Promotion failure

- GIVEN candidate validation or publication fails
- WHEN promotion is attempted
- THEN active and previous selections remain unchanged and no partial bundle is visible
