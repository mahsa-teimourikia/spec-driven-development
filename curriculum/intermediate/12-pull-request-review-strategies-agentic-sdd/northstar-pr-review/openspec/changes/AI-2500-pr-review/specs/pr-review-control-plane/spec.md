# PR review control-plane delta

## ADDED Requirements

### Requirement: exact review subject

The control plane SHALL derive the base commit, head commit, ancestry, and both source and destination paths for renames, copies, and deletions from trusted Git state.

#### Scenario: contributor declares a smaller diff

- **WHEN** contributor metadata omits an out-of-scope path
- **THEN** review SHALL use the trusted Git diff and return `AWU_SCOPE_VIOLATION`

### Requirement: revision-bound approvals and evidence

The control plane SHALL reject approvals and evidence that do not exist in independently maintained registries or do not bind the exact head, authoritative specification digest, and authoritative contract digest.

#### Scenario: commit follows approval

- **WHEN** a new commit changes the review subject
- **THEN** the earlier approval SHALL be stale until trusted impact analysis or reapproval occurs

### Requirement: independent authority

The control plane SHALL resolve work-unit paths, ownership rules, approved artifacts, and reviewer authority from protected stores. Reviewer grants SHALL bind principal, role, resource, and permitted decision. An implementation author SHALL NOT approve its own protected change, and merge-review eligibility SHALL NOT imply deployment or release authority.

### Requirement: independent conformance execution

The protected runner SHALL check out the exact candidate commit, execute an oracle outside the contributor test suite, register the observed result, and block a candidate whose own tests pass while the protected oracle fails.
