# PR review control-plane delta

## ADDED Requirements

### Requirement: exact review subject

The control plane SHALL derive the base commit, head commit, ancestry, and changed paths from trusted Git state.

#### Scenario: contributor declares a smaller diff

- **WHEN** contributor metadata omits an out-of-scope path
- **THEN** review SHALL use the trusted Git diff and return `AWU_SCOPE_VIOLATION`

### Requirement: revision-bound approvals and evidence

The control plane SHALL reject approvals and evidence that do not bind the exact head, specification digest, and contract digest.

#### Scenario: commit follows approval

- **WHEN** a new commit changes the review subject
- **THEN** the earlier approval SHALL be stale until trusted impact analysis or reapproval occurs

### Requirement: independent authority

An implementation author SHALL NOT approve its own protected change, and merge-review eligibility SHALL NOT imply deployment or release authority.
